#!/usr/bin/env python3
"""
Torch — persistent router daemon.

Loads routing-index.json once, then serves scoring requests over a Unix
domain socket (~/.claude/torch-router.sock).  Each request is a
newline-terminated JSON object; each response is a newline-terminated
JSON object.  Handles concurrent clients via daemon threads.

Reduces per-prompt latency from ~200 ms (subprocess) to ~5 ms (socket).

Start:   python router-daemon.py  [--plugin-root <path>]
Stop:    SIGTERM (socket file removed on exit)
"""
import argparse
import errno
import hashlib
import json
import os
import signal
import socket
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def _socket_path_for(plugin_root: str) -> Path:
    """Return a unique socket path per plugin_root (avoids cross-instance collisions)."""
    tag = hashlib.sha256(os.path.abspath(plugin_root).encode()).hexdigest()[:8]
    return Path.home() / ".claude" / f"torch-router-{tag}.sock"

# ---------------------------------------------------------------------------
# Router import — resolve relative to this file
# ---------------------------------------------------------------------------

_BIN_DIR = Path(__file__).parent
sys.path.insert(0, str(_BIN_DIR))
import router as _router  # noqa: E402  (inserted path required first)

_INDEX: dict = {}
_GRAPH_CHAINS: dict = {}
# RLock guards both globals during hot-reload; _handle_client snapshots under
# the lock then releases before scoring to avoid blocking concurrent requests.
_INDEX_LOCK = threading.RLock()


def _load(plugin_root: str) -> None:
    global _INDEX, _GRAPH_CHAINS
    _INDEX = _router._load_index(plugin_root)
    _GRAPH_CHAINS = _router._load_graph_chains(plugin_root)


def _pid_path_for(sock_path: Path) -> Path:
    """Return the .pid file path that shadows a given .sock path."""
    return sock_path.with_suffix(".pid")


def _watch_index(plugin_root: str, index_path: str, interval: int = 30) -> None:
    """Background thread: reload routing index when its mtime changes.

    Captures the mtime immediately after startup (so the first check at T+interval
    only reloads if the file genuinely changed, not on every daemon start).
    Both globals are replaced atomically under _INDEX_LOCK to prevent a scoring
    request from seeing _INDEX=new but _GRAPH_CHAINS=old mid-reload.
    """
    global _INDEX, _GRAPH_CHAINS
    try:
        last_mtime = os.path.getmtime(index_path)
    except Exception:
        last_mtime = 0.0

    while True:
        time.sleep(interval)
        try:
            mtime = os.path.getmtime(index_path)
            if mtime != last_mtime:
                new_index  = _router._load_index(plugin_root)
                new_chains = _router._load_graph_chains(plugin_root)
                if new_index.get("capabilities"):
                    with _INDEX_LOCK:
                        _INDEX        = new_index
                        _GRAPH_CHAINS = new_chains
                    last_mtime = mtime  # Only advance cursor on successful reload
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------

def _handle_client(conn: socket.socket) -> None:
    """Read one newline-terminated JSON request, write one JSON response."""
    try:
        conn.settimeout(2.0)  # prevent hung clients from holding threads indefinitely
        data = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\n" in data:
                break
        if not data:
            conn.sendall(b'{"match":false,"candidates":[]}\n')
            return
        request = json.loads(data.split(b"\n", 1)[0])
        prompt = request.get("prompt", "")
        session_state = request.get("session_state", {})
        if not isinstance(session_state, dict):
            session_state = {}
        # Snapshot both globals under the lock so a concurrent hot-reload cannot
        # produce a torn read (new _INDEX / old _GRAPH_CHAINS).  Scoring itself
        # runs outside the lock — it is CPU-bound and must not block other clients.
        with _INDEX_LOCK:
            index_snapshot  = _INDEX
            chains_snapshot = _GRAPH_CHAINS
        candidates = _router.score_candidates(prompt, session_state, index_snapshot, chains_snapshot)
        result = {"match": len(candidates) > 0, "candidates": candidates}
        conn.sendall((json.dumps(result) + "\n").encode())
    except Exception:
        try:
            conn.sendall(b'{"match":false,"candidates":[]}\n')
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

def main() -> None:
    # AF_UNIX guard — exit cleanly on platforms that do not support Unix sockets
    # (Windows <10 build 1803, Python <3.9).  The hook falls back to subprocess.
    if not hasattr(socket, "AF_UNIX"):
        sys.exit(0)

    parser = argparse.ArgumentParser(description="Torch router daemon")
    parser.add_argument(
        "--plugin-root",
        default=os.environ.get("CLAUDE_PLUGIN_ROOT", str(_BIN_DIR.parent)),
        help="Base directory of the plugin",
    )
    args = parser.parse_args()

    sock_path = _socket_path_for(args.plugin_root)
    pid_path  = _pid_path_for(sock_path)

    _load(args.plugin_root)
    if not _INDEX.get("capabilities"):
        # Nothing to serve — exit silently (hook will fall back to subprocess)
        sys.exit(0)

    def _cleanup(signum=None, frame=None) -> None:  # noqa: ANN001
        for p in (sock_path, pid_path):
            try:
                if p.exists():
                    p.unlink()
            except OSError:
                pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, _cleanup)
    signal.signal(signal.SIGINT, _cleanup)

    sock_path.parent.mkdir(parents=True, exist_ok=True)

    # --- Concurrent-spawn guard (F2) ---
    # Check whether a healthy daemon is already serving before touching the socket.
    # Old behaviour: unconditionally unlink + bind → if two sessions raced, daemon-B
    # would wipe daemon-A's socket file, leaving daemon-A orphaned and daemon-B
    # taking over.  Repeat over a workday → dozens of orphan Python processes.
    #
    # New behaviour: probe first.  If alive → exit cleanly (let the existing daemon
    # serve all sessions).  If dead (stale socket) → unlink then bind.  A final
    # try/except on bind catches the narrow TOCTOU window where two daemons both
    # see a dead socket simultaneously and race to bind.
    if sock_path.exists():
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
                probe.settimeout(0.3)
                probe.connect(str(sock_path))
            # Another healthy daemon is already serving — exit without disrupting it
            sys.exit(0)
        except Exception:
            # Dead / stale socket — clean it up and bind a fresh one
            try:
                sock_path.unlink()
            except OSError:
                pass

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            srv.bind(str(sock_path))
        except OSError as exc:
            # TOCTOU: another daemon raced us and bound first — exit cleanly.
            # Any other OSError is unexpected; re-raise for visibility.
            if exc.errno in (errno.EADDRINUSE, errno.EEXIST):
                sys.exit(0)
            raise

        os.chmod(str(sock_path), 0o600)  # owner-only: prevents cross-user socket injection

        # Write PID file after successful bind so install --verify and
        # step_clear_sockets can terminate the daemon cleanly by PID.
        try:
            pid_path.write_text(str(os.getpid()), encoding="utf-8")
        except OSError:
            pass  # Non-fatal: cleanup just won't have a PID to send SIGTERM to

        # Start hot-reload watcher (F3) — reloads routing-index.json within
        # 30 s of a build completing, covering weeks-long session scenarios.
        index_path = os.path.join(
            args.plugin_root,
            "skills", "on", "catalog", "landscape", "routing-index.json",
        )
        watcher = threading.Thread(
            target=_watch_index,
            args=(args.plugin_root, index_path),
            daemon=True,
        )
        watcher.start()

        srv.listen(16)
        with ThreadPoolExecutor(max_workers=8) as pool:
            while True:
                try:
                    conn, _ = srv.accept()
                except OSError:
                    break
                pool.submit(_handle_client, conn)


if __name__ == "__main__":
    main()
