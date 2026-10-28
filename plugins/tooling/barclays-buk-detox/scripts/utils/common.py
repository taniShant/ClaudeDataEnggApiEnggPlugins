"""Shared utilities for detox pipeline scripts."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import re as _re

from scripts.core.errors import error_exit

# Maximum stdin payload size (10 MB)
MAX_STDIN_BYTES = 10 * 1024 * 1024


# --- Cross-platform advisory file locking -----------------------------------
# fcntl is POSIX-only; importing/using it on Windows raises and previously broke
# ALL telemetry/state writes on Windows ("fcntl not available on Windows"). This
# shim locks with fcntl on POSIX, msvcrt on Windows, and degrades to a no-op if
# neither is usable — single-line append writes are effectively atomic, so a
# missing lock is safe (worst case: interleaving under heavy concurrency), far
# better than failing the write entirely.
try:
    import fcntl as _fcntl  # POSIX
except ImportError:  # Windows
    _fcntl = None
try:
    import msvcrt as _msvcrt  # Windows
except ImportError:  # POSIX
    _msvcrt = None


def _lock_file(f) -> None:
    """Best-effort exclusive lock on an open file handle. Never raises."""
    try:
        if _fcntl is not None:
            _fcntl.flock(f, _fcntl.LOCK_EX)
        elif _msvcrt is not None:
            _msvcrt.locking(f.fileno(), _msvcrt.LK_LOCK, 1)
    except (OSError, ValueError):
        pass  # lock unavailable — proceed unlocked (append writes stay atomic)


def _unlock_file(f) -> None:
    """Release a lock taken by _lock_file. Never raises."""
    try:
        if _fcntl is not None:
            _fcntl.flock(f, _fcntl.LOCK_UN)
        elif _msvcrt is not None:
            _msvcrt.locking(f.fileno(), _msvcrt.LK_UNLCK, 1)
    except (OSError, ValueError):
        pass


from contextlib import contextmanager as _contextmanager


@_contextmanager
def locked_append(path, mode: str = "a", encoding: str = "utf-8"):
    """Open `path` and hold a cross-platform advisory lock for the duration.

    Usage:
        with locked_append(RUNS_FILE) as f:
            f.write(line)

    Works on POSIX (fcntl) and Windows (msvcrt); if locking is unavailable it
    proceeds without a lock rather than failing the write.
    """
    f = open(path, mode, encoding=encoding) if "b" not in mode else open(path, mode)
    try:
        _lock_file(f)
        yield f
    finally:
        try:
            _unlock_file(f)
        finally:
            f.close()

# Severity hierarchy (shared across scripts)
SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
SEVERITY_LEVELS = {"critical", "high", "medium", "low", "info"}


def log(message: str) -> None:
    """Write a structured log line to stderr (diagnostics only, not JSON output)."""
    if os.environ.get("DETOX_VERBOSE", ""):
        ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        print(f"[{ts}] [DETOX] {message}", file=sys.stderr)


def progress(message: str) -> None:
    """Write a user-facing progress line to stderr (always visible)."""
    print(f"[DETOX] ▸ {message}", file=sys.stderr, flush=True)


def progress_done(message: str) -> None:
    """Write a user-facing completion line to stderr (always visible)."""
    print(f"[DETOX]   ✓ {message}", file=sys.stderr, flush=True)


def read_json_input() -> dict[str, Any]:
    """Read JSON input from stdin or --input file argument.

    Returns parsed JSON dict. Exits with structured error on failure.
    """
    input_path: str | None = None
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--input" and i + 1 < len(args):
            input_path = args[i + 1]
            break

    try:
        if input_path:
            file_size = Path(input_path).stat().st_size
            if file_size > MAX_STDIN_BYTES:
                error_exit(
                    f"Input file too large ({file_size} bytes, max {MAX_STDIN_BYTES})",
                    "input_read",
                )
            with open(input_path, "r") as f:
                return json.load(f)
        else:
            data = sys.stdin.read(MAX_STDIN_BYTES + 1)
            if len(data) > MAX_STDIN_BYTES:
                error_exit(
                    f"Stdin payload too large (max {MAX_STDIN_BYTES} bytes)",
                    "input_read",
                )
            if not data.strip():
                error_exit("No input provided on stdin", "input_read")
            return json.loads(data)
    except json.JSONDecodeError as e:
        error_exit(f"Invalid JSON input: {e}", "input_parse")
    except FileNotFoundError:
        error_exit(f"Input file not found: {input_path}", "input_read")
    except Exception as e:
        error_exit(f"Failed to read input: {e}", "input_read")

    # Unreachable — error_exit is NoReturn — but satisfies type checkers
    raise SystemExit(1)  # pragma: no cover


def write_json_output(data: Any, start_time: float | None = None) -> None:
    """Write JSON output to stdout.

    If start_time is provided, injects duration_ms into the output dict.
    """
    if start_time is not None and isinstance(data, dict):
        data["duration_ms"] = round((time.time() - start_time) * 1000)
    json.dump(data, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")


def run_cmd(
    cmd: list[str],
    cwd: str | Path | None = None,
    timeout: int = 120,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run a command and return structured result.

    Only accepts list-form commands (no shell interpretation, safe from injection).

    Returns:
        {"exit_code": int, "stdout": str, "stderr": str}
    """
    if not isinstance(cmd, list):
        raise TypeError("run_cmd requires a list[str] command. String commands are not allowed.")

    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    # Sanitize command representation before logging to prevent PAT leakage
    cmd_repr = repr(cmd)
    cmd_repr = sanitize_pat(cmd_repr)
    log(f"run_cmd: {cmd_repr} cwd={cwd}")

    try:
        result = subprocess.run(
            cmd,
            shell=False,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=run_env,
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds",
        }
    except FileNotFoundError as e:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command not found: {e}",
        }
    except Exception as e:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command execution failed: {e}",
        }


def shell_quote(value: str) -> str:
    """Shell-quote a value for safe interpolation into shell command strings.

    This MUST be used for any user-controlled value passed into a shell string.
    Prefer list-form commands via run_cmd(["git", "arg", ...]) where possible.
    """
    return shlex.quote(value)


def resolve_path(path: str, root: str | None = None) -> str:
    """Resolve a path to absolute form.

    If path is relative and root is provided, resolve relative to root.
    """
    p = Path(path)
    if p.is_absolute():
        return str(p)
    if root:
        return str(Path(root) / p)
    return str(p.resolve())


# Environment variables that may contain credentials (checked by sanitize_pat)
_CREDENTIAL_ENV_VARS = ("GIT_PAT", "GITLAB_TOKEN", "GITHUB_TOKEN", "GH_TOKEN")

# Pre-compiled patterns for common token formats (min 20 chars to avoid false positives)
_TOKEN_PATTERNS = (
    _re.compile(r"glpat-[A-Za-z0-9_\-]{20,}"),
    _re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    _re.compile(r"gho_[A-Za-z0-9]{20,}"),
    _re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
)


def sanitize_pat(text: str, pat_env_var: str | None = "GIT_PAT") -> str:
    """Remove credential values from text to prevent leakage.

    Checks:
    1. The specified pat_env_var (for backwards compatibility).
    2. All vars in _CREDENTIAL_ENV_VARS.
    3. Common token prefixes (glpat-, ghp_, gho_, github_pat_).

    Any match is replaced with ***REDACTED***.
    """
    # Collect all env-var-based secrets to redact
    env_vars_to_check = set(_CREDENTIAL_ENV_VARS)
    if pat_env_var:
        env_vars_to_check.add(pat_env_var)

    for var in env_vars_to_check:
        secret = os.environ.get(var, "")
        if secret and secret in text:
            text = text.replace(secret, "***REDACTED***")

    # Pattern-based redaction using pre-compiled regexes
    for pattern in _TOKEN_PATTERNS:
        text = pattern.sub("***REDACTED***", text)

    return text


# The mandatory setup-claude-user script writes barclays_user_id / barclays_cio
# / barclays_team / barclays_user_email into ~/.claude/settings.json under
# env.OTEL_RESOURCE_ATTRIBUTES. That value configures Claude Code's own
# telemetry; detox reads it from the same source so its telemetry is attributed
# consistently (and so preflight can verify the setup is complete).

BARCLAYS_SETUP_KEYS = (
    "barclays_user_id",
    "barclays_cio",
    "barclays_team",
    "barclays_user_email",
)


def claude_config_dir() -> Path:
    """Claude Code's config dir — honours CLAUDE_CONFIG_DIR, defaults to ~/.claude."""
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude")).expanduser()


def load_barclays_attributes() -> dict[str, str]:
    """Return all barclays_* attributes from OTEL_RESOURCE_ATTRIBUTES.

    Source of truth is <claude_config_dir>/settings.json (where the setup script writes
    it); falls back to the OTEL_RESOURCE_ATTRIBUTES env var if exported. The var
    is not normally in a detox subprocess env, so the file read is primary.
    Best-effort — any read/parse error returns an empty dict, never raises.
    """
    raw = os.environ.get("OTEL_RESOURCE_ATTRIBUTES", "")
    # The setup script writes to ~/.claude/settings.json regardless of CLAUDE_CONFIG_DIR,
    # so check the active config dir first, then fall back to ~/.claude.
    candidates = dict.fromkeys([claude_config_dir() / "settings.json",
                                Path.home() / ".claude" / "settings.json"])
    for settings_file in candidates if not raw else ():
        try:
            settings = json.loads(settings_file.read_text())
            raw = settings.get("env", {}).get("OTEL_RESOURCE_ATTRIBUTES", "")
        except Exception:
            raw = ""
        if raw:
            break

    attrs: dict[str, str] = {}
    for pair in raw.split(","):
        if "=" in pair:
            key, value = pair.split("=", 1)
            key = key.strip()
            if key.startswith("barclays_"):
                attrs[key] = value.strip()
    return attrs


def get_barclays_cio() -> str | None:
    """Return the Barclays CIO (barclays_cio) only, or None if unset."""
    return load_barclays_attributes().get("barclays_cio") or None


# Mandatory Barclays Claude Code user setup — platform-independent instruction
# shown whenever the setup is incomplete. Kept here (not in preflight_check.py)
# so BOTH the preflight check and the pipeline-entry hard gate in repo_setup.py
# share one source of truth.
BARCLAYS_SETUP_INSTRUCTION = (
    "Barclays Claude Code user setup is incomplete — detox cannot run until your\n"
    "identity (barclays_user_id / barclays_cio / barclays_team / barclays_user_email)\n"
    "is configured in ~/.claude/settings.json.\n"
    "\n"
    "Run the one-time setup:\n"
    "  git clone https://app.gitlab.barcapint.com/senthilnathan.thiyagasundaramumashankar/setup-claude-user.git\n"
    "  cd setup-claude-user && bash setup-claude-user.sh\n"
    "\n"
    "Then restart all active Claude Code sessions (OTEL_RESOURCE_ATTRIBUTES is read at startup).\n"
    "Do NOT set another person's identity."
)


def check_barclays_setup() -> dict:
    """Verify the mandatory Barclays Claude Code user setup is complete.

    The setup-claude-user script writes barclays_user_id / barclays_cio /
    barclays_team / barclays_user_email into ~/.claude/settings.json
    (OTEL_RESOURCE_ATTRIBUTES). If ANY of the four is missing or empty, detox
    must refuse to run (telemetry would otherwise arrive unattributed).

    Returns a dict with `available` (True only when all four keys are present
    and non-empty), plus `missing_keys` / `present_keys` for reporting.
    """
    attrs = load_barclays_attributes()
    missing_keys = [k for k in BARCLAYS_SETUP_KEYS if not attrs.get(k)]
    return {
        "name": "barclays_setup",
        "available": not missing_keys,
        "missing_keys": missing_keys,
        "present_keys": [k for k in BARCLAYS_SETUP_KEYS if attrs.get(k)],
    }
