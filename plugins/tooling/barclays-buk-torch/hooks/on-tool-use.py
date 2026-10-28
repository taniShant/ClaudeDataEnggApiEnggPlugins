#!/usr/bin/env python3
"""
Torch — PostToolUse attribution hook handler.

Reads Claude Code hook JSON payload from stdin.
Writes hook response JSON to stdout.

Environment:
  CLAUDE_PLUGIN_ROOT — base directory of the plugin (default: ".")
"""
import datetime
import json
import os
import sys


def _fail_open() -> None:
    """Write empty response and exit cleanly."""
    sys.stdout.write("{}")
    sys.stdout.flush()
    sys.exit(0)


def _load_session_state(data_dir: str) -> dict:
    """Load session-state.json; return empty dict on missing or error."""
    path = os.path.join(data_dir, "session-state.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        return state if isinstance(state, dict) else {}
    except Exception:
        return {}


def _append_attribution(data_dir: str, record: dict) -> None:
    """Append a single JSONL attribution record with advisory lock; silently ignore errors."""
    path = os.path.join(data_dir, "attribution.jsonl")
    try:
        os.makedirs(data_dir, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            try:
                import fcntl
                fcntl.flock(fh, fcntl.LOCK_EX)
                try:
                    fh.write(json.dumps(record) + "\n")
                finally:
                    fcntl.flock(fh, fcntl.LOCK_UN)
            except ImportError:
                # Windows: fcntl unavailable — best-effort write without advisory lock.
                fh.write(json.dumps(record) + "\n")
    except Exception:
        pass


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

        session_id = payload.get("session_id", "")
        tool_name = payload.get("tool_name", "")

        plugin_root = os.environ.get(
            "CLAUDE_PLUGIN_ROOT",
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        data_dir = os.environ.get(
            "CLAUDE_PLUGIN_DATA",
            os.path.join(plugin_root, "data")
        )

        # 2. Load session state — if missing, nothing to attribute
        session_state = _load_session_state(data_dir)
        if not session_state:
            _fail_open()

        # 3. Check recent list
        recent = session_state.get("recent", [])
        if not recent:
            _fail_open()

        # 3a. Append attribution record — NO tool_input/tool_response content
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        record = {
            "ts": ts,
            "session_id": session_id,
            "event": "tool_used",
            "tool_name": tool_name,
            "recent_caps": recent,
        }
        _append_attribution(data_dir, record)

        # 4. Write empty response
        sys.stdout.write("{}")
        sys.stdout.flush()
        sys.exit(0)

    except Exception:
        _fail_open()


if __name__ == "__main__":
    main()
