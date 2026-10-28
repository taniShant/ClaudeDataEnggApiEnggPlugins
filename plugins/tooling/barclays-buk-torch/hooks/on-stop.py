#!/usr/bin/env python3
"""Stop hook — shuts down the router daemon when Claude Code session ends.

On POSIX: sends SIGTERM so the daemon's cleanup handler removes socket + PID files.
On Windows: os.kill with SIGTERM calls TerminateProcess() which bypasses Python's
signal handlers, so the cleanup handler never fires. Instead we remove socket and
PID files directly after terminating the process.
"""
import hashlib
import os
import platform
import signal
import sys
from pathlib import Path

_IS_WINDOWS = platform.system() == "Windows"


def _fail_open() -> None:
    sys.stdout.write("{}")
    sys.stdout.flush()
    sys.exit(0)


def _sock_path(plugin_root: str) -> Path:
    """Mirror the daemon's socket-path formula exactly."""
    tag = hashlib.sha256(os.path.abspath(plugin_root).encode()).hexdigest()[:8]
    return Path.home() / ".claude" / f"torch-router-{tag}.sock"


def _pid_path(plugin_root: str) -> Path:
    """Mirror the daemon's PID-path formula exactly."""
    tag = hashlib.sha256(os.path.abspath(plugin_root).encode()).hexdigest()[:8]
    return Path.home() / ".claude" / f"torch-router-{tag}.pid"


def main() -> None:
    plugin_root = os.environ.get(
        "CLAUDE_PLUGIN_ROOT",
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    pid_path  = _pid_path(plugin_root)
    sock_path = _sock_path(plugin_root)

    if not pid_path.exists():
        _fail_open()  # daemon already gone or never started

    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
        if _IS_WINDOWS:
            # SIGTERM on Windows calls TerminateProcess(), which skips Python's
            # signal handlers — the daemon's _cleanup never runs.  Terminate the
            # process first, then remove the files ourselves.
            os.kill(pid, signal.SIGTERM)
            pid_path.unlink(missing_ok=True)
            sock_path.unlink(missing_ok=True)
        else:
            # POSIX: SIGTERM triggers the daemon's _cleanup handler, which removes
            # both files.  No manual cleanup needed here.
            os.kill(pid, signal.SIGTERM)
    except (OSError, ValueError, ProcessLookupError):
        # Process already dead, PID reuse, or parse error — clean up files anyway.
        pid_path.unlink(missing_ok=True)
        sock_path.unlink(missing_ok=True)

    _fail_open()


if __name__ == "__main__":
    main()
