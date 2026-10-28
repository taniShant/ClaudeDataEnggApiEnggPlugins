#!/usr/bin/env python3
"""
Torch — UserPromptSubmit and SubagentStart hook handler.

Reads Claude Code hook JSON payload from stdin.
Writes hook response JSON to stdout.

Environment:
  CLAUDE_PLUGIN_ROOT — base directory of the plugin (default: ".")
"""
import datetime
import hashlib
import json
import os
import platform
import re
import socket as _socket
import subprocess
import sys
import tempfile
import time

DISMISSAL_PHRASES = frozenset({
    "no thanks",
    "not helpful",
    "not relevant",
    "not useful",
    "suppress suggestion",
    "dismiss suggestion",
    "don't suggest",
    "stop suggesting",
})

PERSISTENT_SUPPRESSIONS_FILE = "persistent-suppressions.json"
PERSISTENT_SUPPRESSIONS_MAX = 50

_DAEMON_CONNECT_TIMEOUT = 0.3   # seconds — fast path (daemon already running)
_DAEMON_RETRY_TIMEOUT   = 1.0   # seconds — after spawn attempt, give daemon more headroom
_DAEMON_STARTUP_WAIT    = 1.0   # max seconds to wait for socket to appear after Popen
_DAEMON_PROBE_TIMEOUT   = 0.2   # seconds — liveness check (connect-only, no data)

# Platform capability flags — computed once at import time
_HAS_UNIX_SOCKET = hasattr(_socket, "AF_UNIX")   # False on Windows <10 1803 / Python <3.9
_IS_WINDOWS      = platform.system() == "Windows"


def _daemon_socket(plugin_root: str) -> str:
    """Return a unique socket path per plugin_root (mirrors router-daemon.py logic)."""
    tag = hashlib.sha256(os.path.abspath(plugin_root).encode()).hexdigest()[:8]
    return os.path.join(os.path.expanduser("~"), ".claude", f"torch-router-{tag}.sock")


def _probe_daemon_alive(sock_path: str) -> bool:
    """Return True if a process is actively listening on sock_path.

    Performs a connect-only probe — no data is sent.  The daemon-side
    _handle_client handles the resulting empty connection via its
    ``if not data`` early-return guard, so this is zero-cost to the daemon.
    Only called when the socket file already exists but a prior Tier-1 connect
    failed, so probe overhead is O(1) per stale-socket recovery event.
    """
    if not _HAS_UNIX_SOCKET:
        return False
    try:
        with _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM) as s:
            s.settimeout(_DAEMON_PROBE_TIMEOUT)
            s.connect(sock_path)
        return True
    except Exception:
        return False


def _popen_daemon(daemon_path: str, plugin_root: str) -> None:
    """Spawn the router daemon as a fully detached background process.

    On Windows the DETACHED_PROCESS flag is required so the daemon survives
    parent-process exit even inside a Windows Job Object (VS Code integrated
    terminal, CI runners using job objects).  CREATE_NEW_PROCESS_GROUP gives
    independent signal handling.  start_new_session=True is the POSIX equivalent
    and calls setsid() to detach from the controlling terminal.
    """
    kwargs: dict = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if _IS_WINDOWS:
        DETACHED_PROCESS         = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        kwargs["creationflags"]  = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(
        [sys.executable, daemon_path, "--plugin-root", plugin_root],
        **kwargs,
    )


def _try_socket_request(sock_path: str, router_input: str, timeout: float) -> dict | None:
    """Send router_input to the daemon socket.  Returns None on any failure (fail-open)."""
    if not _HAS_UNIX_SOCKET:
        return None  # Platform does not support AF_UNIX — subprocess fallback only
    try:
        with _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect(sock_path)
            s.sendall((router_input + "\n").encode())
            data = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b"\n" in data:
                    break
        return json.loads(data.split(b"\n", 1)[0])
    except Exception:
        return None


def _start_daemon_if_absent(sock_path: str, daemon_path: str, plugin_root: str) -> None:
    """Ensure a healthy daemon is running, spawning one if needed.

    Three cases handled:
    1. No socket file          → spawn daemon, poll up to _DAEMON_STARTUP_WAIT.
    2. Socket file exists + daemon alive  → nothing to do (another session is serving).
    3. Socket file exists + daemon dead   → stale socket; remove it then spawn fresh.

    Case 3 (stale socket after crash or hard kill) was the primary source of
    permanent 200ms-per-prompt degradation: the old existence-only check
    prevented a new daemon from ever being spawned.
    """
    if not _HAS_UNIX_SOCKET:
        return  # AF_UNIX not available — subprocess fallback is the only path

    if os.path.exists(sock_path):
        if _probe_daemon_alive(sock_path):
            return  # Healthy daemon already serving — nothing to do
        # Stale socket (daemon crashed / was killed without cleanup)
        try:
            os.unlink(sock_path)
        except OSError:
            pass
        # Fall through to spawn

    if not os.path.isfile(daemon_path):
        return

    try:
        _popen_daemon(daemon_path, plugin_root)
        deadline = time.monotonic() + _DAEMON_STARTUP_WAIT
        while time.monotonic() < deadline:
            if os.path.exists(sock_path):
                break
            time.sleep(0.05)
    except Exception:
        pass


def _fail_open() -> None:
    """Write empty response and exit cleanly."""
    sys.stdout.write("{}")
    sys.stdout.flush()
    sys.exit(0)


def sanitize_error(raw: str) -> str:
    """Strip sensitive content (paths, IPs, tokens, stacks) from error strings."""
    s = str(raw)
    s = re.sub(r"\n?\s+at\s+.*", "", s)
    s = re.sub(r'File ".*?", line \d+.*', "", s)
    s = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?\b", "[host]", s)
    s = re.sub(r"\b[a-z0-9\-]+\.(intranet|internal|local|corp|uk\.net)(:\d+)?\b", "[host]", s)
    s = re.sub(r"(?:/[\w\-./]+)+\.\w+", "[path]", s)
    s = re.sub(r"Bearer\s+\S+", "Bearer [redacted]", s, flags=re.I)
    s = re.sub(r"(token|key|password|secret)[:=]\s*\S+", r"\1=[redacted]", s, flags=re.I)
    s = re.sub(r"\b(glpat-|APIKEY-)[A-Za-z0-9\-_]{10,}", "[redacted]", s)
    return s[:300] + ("..." if len(s) > 300 else "")


def _write_json_atomic(path: str, data) -> None:
    """Write JSON atomically via temp file + rename.

    On POSIX, os.replace is guaranteed atomic.  On Windows it raises
    PermissionError when another process briefly holds the destination file
    open (e.g. a concurrent session reading session-state.json).  A short
    retry loop handles that without data loss.
    """
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except OSError:
        return
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    os.close(fd)
    for attempt in range(5):
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            os.replace(tmp, path)
            return
        except PermissionError:
            # Windows file-lock contention — exponential backoff for AV/DLP holds
            if attempt < 4:
                time.sleep(0.03 * (2 ** attempt))
        except OSError:
            break
    try:
        os.unlink(tmp)
    except OSError:
        pass


def _load_session_state(data_dir: str) -> dict:
    """Load session-state.json; return empty dict on missing or error."""
    path = os.path.join(data_dir, "session-state.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        return state if isinstance(state, dict) else {}
    except Exception:
        return {}


def _save_session_state(data_dir: str, state: dict) -> None:
    """Persist session-state.json atomically; silently ignore errors."""
    path = os.path.join(data_dir, "session-state.json")
    _write_json_atomic(path, state)


def _load_persistent_suppressions(data_dir: str) -> list:
    """Load persistent-suppressions.json; return empty list on missing or error."""
    path = os.path.join(data_dir, PERSISTENT_SUPPRESSIONS_FILE)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_persistent_suppressions(data_dir: str, suppressed: list) -> None:
    """Persist the last PERSISTENT_SUPPRESSIONS_MAX entries atomically; silently ignore errors."""
    path = os.path.join(data_dir, PERSISTENT_SUPPRESSIONS_FILE)
    _write_json_atomic(path, suppressed[-PERSISTENT_SUPPRESSIONS_MAX:])


def _maybe_rotate_attribution(path: str, max_bytes: int = 10 * 1024 * 1024) -> None:
    """Shift-rotate attribution.jsonl when it exceeds max_bytes."""
    try:
        if not os.path.exists(path) or os.path.getsize(path) < max_bytes:
            return
        p1 = path + ".1"
        p2 = path + ".2"
        if os.path.exists(p1):
            os.replace(p1, p2)
        os.replace(path, p1)
    except OSError:
        pass


def _append_attribution(data_dir: str, records: list) -> None:
    """Append JSONL attribution records with advisory lock; silently ignore errors."""
    path = os.path.join(data_dir, "attribution.jsonl")
    try:
        _maybe_rotate_attribution(path)
        with open(path, "a", encoding="utf-8") as fh:
            try:
                import fcntl
                fcntl.flock(fh, fcntl.LOCK_EX)
                try:
                    for rec in records:
                        fh.write(json.dumps(rec) + "\n")
                finally:
                    fcntl.flock(fh, fcntl.LOCK_UN)
            except ImportError:
                # Windows: fcntl unavailable — best-effort write without advisory lock.
                # Each json.dumps()+"\n" is a single str.write(); cross-process
                # interleaving remains possible but is non-fatal for analytics.
                for rec in records:
                    fh.write(json.dumps(rec) + "\n")
    except Exception:
        pass


_DISMISSAL_MAX_LEN = 80   # characters — dismissals are short standalone responses


def _is_dismissal(text: str) -> bool:
    """Return True if the prompt is dismissing the last capability suggestion."""
    lower = text.lower().strip()
    if len(lower) > _DISMISSAL_MAX_LEN:
        return False
    return any(
        re.search(r'\b' + re.escape(phrase) + r'\b', lower)
        for phrase in DISMISSAL_PHRASES
    )


def main() -> None:
    # Ensure UTF-8 for stdin/stdout on Windows (default encoding is cp1252 there)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")

    try:
        # 1. Parse stdin
        try:
            raw = sys.stdin.read()
            payload = json.loads(raw)
        except Exception:
            _fail_open()

        # 2. Extract required fields
        prompt = payload.get("prompt")
        if not prompt or not isinstance(prompt, str):
            _fail_open()

        session_id = payload.get("session_id", "")

        plugin_root = os.environ.get(
            "CLAUDE_PLUGIN_ROOT",
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        data_dir = os.environ.get(
            "CLAUDE_PLUGIN_DATA",
            os.path.join(plugin_root, "data")
        )

        # Ensure data directory exists
        try:
            os.makedirs(data_dir, exist_ok=True)
        except Exception:
            _fail_open()

        # 3. Load session state and merge persistent suppressions
        session_state = _load_session_state(data_dir)
        persistent_suppressed = _load_persistent_suppressions(data_dir)
        session_suppressed = session_state.get("suppressed", [])
        # Merge: persistent first (older), session second (newer); deduplicate preserving order
        merged_suppressed = list(dict.fromkeys(persistent_suppressed + session_suppressed))
        session_state["suppressed"] = merged_suppressed

        # 3b. Handle dismissal signal — suppress last-suggested capability, return no-inject
        if _is_dismissal(prompt):
            recent = session_state.get("recent", [])
            if recent:
                last_suggested = recent[-1]
                suppressed = session_state.get("suppressed", [])
                if last_suggested not in suppressed:
                    suppressed.append(last_suggested)
                if len(suppressed) > 20:
                    suppressed = suppressed[-20:]
                session_state["suppressed"] = suppressed
                _save_session_state(data_dir, session_state)
                _save_persistent_suppressions(data_dir, suppressed)
            _fail_open()

        # 4. Route — daemon socket (fast path) with subprocess fallback
        router_path = os.path.join(plugin_root, "bin", "router.py")
        daemon_path = os.path.join(plugin_root, "bin", "router-daemon.py")
        sock_path = _daemon_socket(plugin_root)
        router_input = json.dumps({
            "prompt": prompt,
            "session_state": session_state,
        })

        # Fast path: try existing daemon
        router_output = _try_socket_request(sock_path, router_input, _DAEMON_CONNECT_TIMEOUT)

        # Start daemon if socket absent, then retry once
        if router_output is None:
            _start_daemon_if_absent(sock_path, daemon_path, plugin_root)
            router_output = _try_socket_request(sock_path, router_input, _DAEMON_RETRY_TIMEOUT)

        # Subprocess fallback (daemon unavailable or not installed)
        if router_output is None:
            _subprocess_result = None
            try:
                _subprocess_result = subprocess.run(
                    [sys.executable, router_path],
                    input=router_input,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                router_output = json.loads(_subprocess_result.stdout)
            except Exception:
                if _subprocess_result is not None and _subprocess_result.stderr:
                    sys.stderr.write(sanitize_error(_subprocess_result.stderr) + "\n")
                _fail_open()

        # 5. No match → pass through
        if not router_output.get("match", False):
            _fail_open()

        candidates = router_output.get("candidates", [])
        if not candidates:
            _fail_open()

        # 6. Format suggestion for top candidate
        top = candidates[0]
        cap_id = top.get("capability_id", "")
        command = top.get("command", "")
        one_liner = top.get("one_liner", "")
        install_info = top.get("install_info", "")
        chain = top.get("chain", "")
        when_short = top.get("when_to_use_short", "")
        not_for = top.get("not_for", "")
        requires = top.get("requires", "")
        suffix = f" → then: {chain}" if chain else ""

        # Build enriched inject: multi-line when context available, 1-line fallback
        if when_short or not_for:
            lines = [f"[Capability: {command}{suffix}"]
            if when_short:
                lines.append(f" Use when: {when_short}")
            if not_for:
                lines.append(f" Not for: {not_for}")
            if requires:
                lines.append(f" Requires first: {requires}")
            if install_info:
                lines.append(f" Install: {install_info}]")
            else:
                lines[-1] += "]"
            suggestion = "\n".join(lines)
        else:
            # Fallback to original format if no enriched data
            req_suffix = f" | Requires first: {requires}" if requires else ""
            if install_info:
                suggestion = f"[Capability available: {command} — {one_liner}{suffix}{req_suffix} | Install: {install_info}]"
            else:
                suggestion = f"[Capability available: {command} — {one_liner}{suffix}{req_suffix}]"

        # Write hook response
        response = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": suggestion,
            }
        }
        sys.stdout.write(json.dumps(response))
        sys.stdout.flush()

        # 6c. Update session state — add cap_id to recent (keep last 5)
        recent = session_state.get("recent", [])
        if cap_id and cap_id not in recent:
            recent.append(cap_id)
        if len(recent) > 5:
            recent = recent[-5:]
        session_state["recent"] = recent
        _save_session_state(data_dir, session_state)

        # 6d. Append attribution records — NO prompt text
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        records = [
            {
                "ts": ts,
                "session_id": session_id,
                "event": "suggested",
                "capability_id": c.get("capability_id", ""),
                "score": c.get("score", 0.0),
            }
            for c in candidates
        ]
        _append_attribution(data_dir, records)

        sys.exit(0)

    except Exception:
        _fail_open()


if __name__ == "__main__":
    main()
