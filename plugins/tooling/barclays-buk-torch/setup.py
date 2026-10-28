#!/usr/bin/env python3
"""
Torch — unified installer.

Works identically from three locations:
  1. DG repo checkout     (plugins/torch/setup.py)
  2. BUK marketplace cache (~/.claude/plugins/cache/...)
  3. Stable runtime copy   (~/.claude/hooks/torch/setup.py)

Copies the runtime subset (hooks, router, index) to a stable location at
~/.claude/hooks/torch/ so hook paths in settings.json never point at a
volatile cache directory that changes on plugin update.

Usage:
  python3 setup.py                   install (wire hooks, copy runtime, venv)
  python3 setup.py --marketplace     also register marketplace + install plugin (DG repo only)
  python3 setup.py --cue             also inject assisted-mode cue (DG repo only)
  python3 setup.py --verify          health check — exit 0 if OK, 1 if issues
  python3 setup.py --uninstall       remove hooks, runtime copy, venv, data
  python3 setup.py --uninstall --cue also remove cue from ~/.claude/CLAUDE.md
  python3 setup.py --dry-run         preview changes, no writes (any mode)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import signal as _signal
import subprocess
import sys
import tempfile
import time
import venv as _venv_mod
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# §1  Constants
# ─────────────────────────────────────────────────────────────────────────────

_IS_WINDOWS = sys.platform == "win32"
_PY_CMD = "python" if _IS_WINDOWS else "python3"

_CLAUDE_DIR     = Path.home() / ".claude"
_SETTINGS       = _CLAUDE_DIR / "settings.json"
_RUNTIME_DIR    = _CLAUDE_DIR / "hooks" / "torch"
_USER_DATA_DIR  = _CLAUDE_DIR / "torch" / "data"
_VENV_DIR       = _CLAUDE_DIR / "torch" / "venv"

_PLUGIN_REFS = ("torch@torch", "barclays-buk-torch@barclays-cio-buk")
_MARKETPLACE_KEY = "torch"

_HOOK_SENTINEL      = "on-prompt-submit.py"
_TOOL_HOOK_SENTINEL = "on-tool-use.py"
_STOP_HOOK_SENTINEL = "on-stop.py"

_CUE_SENTINEL    = "## Torch"
_CUE_FULL_MARKER = "# Managed Discovery Cue"

# Files copied to ~/.claude/hooks/torch/ (relative to plugin root)
_RUNTIME_FILES = [
    "hooks/on-prompt-submit.py",
    "hooks/on-tool-use.py",
    "hooks/on-stop.py",
    "bin/router.py",
    "bin/router-daemon.py",
    "skills/on/catalog/landscape/routing-index.json",
    "skills/on/catalog/landscape/graph-data.json",
]

_MARKETPLACE_URL_SSH   = "git@app.gitlab.barcapint.com:barclays/claude/marketplace/cio/buk.git"
_MARKETPLACE_URL_HTTPS = "https://app.gitlab.barcapint.com/barclays/claude/marketplace/cio/buk.git"

# ─────────────────────────────────────────────────────────────────────────────
# §2  Logging helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ok(msg: str)   -> None: print(f"  [ok]   {msg}")
def _skip(msg: str) -> None: print(f"  [skip] {msg}")
def _warn(msg: str) -> None: print(f"  [warn] {msg}")
def _fail(msg: str) -> None: print(f"  [FAIL] {msg}", file=sys.stderr)
def _step(msg: str) -> None: print(f"\n── {msg}")

# ─────────────────────────────────────────────────────────────────────────────
# §3  Settings read / write (atomic tempfile + os.replace)
# ─────────────────────────────────────────────────────────────────────────────

def _read_settings() -> dict:
    try:
        return json.loads(_SETTINGS.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        _fail(
            f"settings.json contains invalid JSON and cannot be parsed safely.\n"
            f"  File: {_SETTINGS}\n"
            f"  Error: {e}\n"
            f"  Fix: open the file, correct the syntax error, then re-run."
        )
        sys.exit(1)


def _write_settings(data: dict) -> None:
    content = json.dumps(data, indent=2) + "\n"
    _SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=_SETTINGS.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp, _SETTINGS)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

# ─────────────────────────────────────────────────────────────────────────────
# §4  Plugin root resolution (2-tier — handles both plugin refs)
# ─────────────────────────────────────────────────────────────────────────────

def _find_plugin_root() -> Path:
    """Resolve the source plugin root directory.

    Tier 1: installed_plugins.json registry (for any known plugin ref).
    Tier 2: __file__ parent (dev mode / running from cache or runtime copy).
    Validates hooks/on-prompt-submit.py exists at resolved path.
    """
    registry = _CLAUDE_DIR / "plugins" / "installed_plugins.json"
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
        for ref in _PLUGIN_REFS:
            for entry in data.get("plugins", {}).get(ref, []):
                if entry.get("scope") == "user":
                    p = Path(entry["installPath"])
                    if (p / "hooks" / "on-prompt-submit.py").exists():
                        return p
    except Exception:
        pass

    here = Path(__file__).parent.resolve()
    if (here / "hooks" / "on-prompt-submit.py").exists():
        return here

    _fail(
        "Cannot locate plugin root.\n"
        "  Expected to find hooks/on-prompt-submit.py inside the install directory.\n"
        "  Install the plugin first, or run from the repository checkout."
    )
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# §5  Venv management
# ─────────────────────────────────────────────────────────────────────────────

def _venv_python() -> Path:
    if _IS_WINDOWS:
        return _VENV_DIR / "Scripts" / "python.exe"
    return _VENV_DIR / "bin" / "python3"


def step_ensure_venv(dry_run: bool = False) -> bool:
    """Create or verify the managed runtime venv at ~/.claude/torch/venv/."""
    python_path = _venv_python()

    needs_recreate = False
    if python_path.exists():
        try:
            r = subprocess.run(
                [str(python_path), "-c",
                 "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"],
                capture_output=True, check=False, timeout=10,
            )
            if r.returncode == 0:
                _skip(f"Runtime venv already healthy ({python_path})")
                return True
        except Exception:
            pass
        _warn(f"Runtime venv unhealthy — will recreate: {_VENV_DIR}")
        needs_recreate = True
        if not dry_run:
            shutil.rmtree(_VENV_DIR, ignore_errors=True)

    if dry_run:
        action = "recreate (existing venv is unhealthy)" if needs_recreate else "create"
        _ok(f"[dry-run] Would {action} runtime venv: {_VENV_DIR}")
        return True

    _ok(f"Creating runtime venv: {_VENV_DIR}")
    try:
        _VENV_DIR.parent.mkdir(parents=True, exist_ok=True)
        _venv_mod.create(str(_VENV_DIR), with_pip=False)
    except Exception as exc:
        _fail(f"Failed to create runtime venv: {exc}")
        if not _IS_WINDOWS:
            _warn("On Debian/Ubuntu, install: sudo apt install python3-venv")
        return False

    if not python_path.exists():
        _fail(f"Venv created but Python not found at expected path: {python_path}")
        return False

    _ok(f"Runtime venv created: {python_path}")
    return True

# ─────────────────────────────────────────────────────────────────────────────
# §6  Socket / daemon cleanup
# ─────────────────────────────────────────────────────────────────────────────

def step_clear_sockets(dry_run: bool) -> None:
    """Stop daemons and remove socket / PID files."""
    if _IS_WINDOWS:
        _skip("Unix daemon sockets not used on Windows")
        return

    socks = list(_CLAUDE_DIR.glob("torch-router-*.sock"))
    pids = list(_CLAUDE_DIR.glob("torch-router-*.pid"))

    if not socks and not pids:
        _ok("No stale daemon sockets or PID files")
        return

    for pid_file in pids:
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
            print(f"  Sending SIGTERM to daemon PID {pid} ({pid_file.name})")
            if not dry_run:
                os.kill(pid, _signal.SIGTERM)
        except (ValueError, OSError, ProcessLookupError):
            pass
        if not dry_run:
            try:
                pid_file.unlink(missing_ok=True)
            except OSError:
                pass

    for s in socks:
        print(f"  Removing socket: {s.name}")
        if not dry_run:
            try:
                s.unlink(missing_ok=True)
            except OSError:
                pass

    _ok(f"Stopped {len(pids)} daemon(s), cleared {len(socks)} socket(s)")

# ─────────────────────────────────────────────────────────────────────────────
# §7  Runtime copy
# ─────────────────────────────────────────────────────────────────────────────

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def step_copy_runtime(plugin_root: Path, dry_run: bool) -> bool:
    """Copy the runtime subset to ~/.claude/hooks/torch/."""
    copied = []
    missing = []

    for rel in _RUNTIME_FILES:
        src = plugin_root / rel
        dst = _RUNTIME_DIR / rel
        if not src.exists():
            missing.append(rel)
            continue
        if dry_run:
            copied.append(rel)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))
        copied.append(rel)

    # Copy setup.py itself so verify/uninstall works from the runtime dir
    setup_src = Path(__file__).resolve()
    setup_dst = _RUNTIME_DIR / "setup.py"
    if not dry_run:
        setup_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(setup_src), str(setup_dst))

    if missing:
        _fail(f"Missing source files: {', '.join(missing)}")
        return False

    if dry_run:
        _ok(f"[dry-run] Would copy {len(copied)} runtime files → {_RUNTIME_DIR}")
        return True

    # Write manifest
    manifest = {"files": {}, "source": str(plugin_root), "timestamp": time.time()}
    # Read version from plugin.json if available
    pjson = plugin_root / ".claude-plugin" / "plugin.json"
    if pjson.exists():
        try:
            manifest["version"] = json.loads(pjson.read_text(encoding="utf-8")).get("version", "?")
        except Exception:
            pass
    for rel in _RUNTIME_FILES:
        dst = _RUNTIME_DIR / rel
        manifest["files"][rel] = _sha256(dst)
    manifest["files"]["setup.py"] = _sha256(setup_dst)

    manifest_path = _RUNTIME_DIR / ".manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    # macOS: clear quarantine
    if platform.system() == "Darwin":
        cleared = []
        for rel in _RUNTIME_FILES + ["setup.py"]:
            f = _RUNTIME_DIR / rel
            if not f.exists():
                continue
            r = subprocess.run(
                ["xattr", "-l", str(f)],
                capture_output=True, check=False,
            )
            if b"com.apple.quarantine" in r.stdout:
                subprocess.run(
                    ["xattr", "-d", "com.apple.quarantine", str(f)],
                    capture_output=True, check=False,
                )
                cleared.append(rel)
        if cleared:
            _ok(f"Cleared quarantine from: {', '.join(cleared)}")

    _ok(f"Copied {len(copied)} runtime files → {_RUNTIME_DIR}")
    return True

# ─────────────────────────────────────────────────────────────────────────────
# §8  Hook wiring
# ─────────────────────────────────────────────────────────────────────────────

def _hook_cmd_for(script_name: str) -> str:
    """Build the settings.json command string pointing at the stable runtime dir."""
    venv_py = _venv_python()
    py = str(venv_py).replace("\\", "/") if venv_py.exists() else sys.executable.replace("\\", "/")
    hook = (_RUNTIME_DIR / "hooks" / script_name).as_posix()
    if " " in py:   py   = f'"{py}"'
    if " " in hook: hook = f'"{hook}"'
    return f"{py} {hook}"


def _wire_or_upgrade(
    hooks: dict, event: str, new_entry: dict, sentinel: str, cmd: str
) -> bool:
    """Wire a hook entry or upgrade its command if stale. Returns True if modified."""
    for entry in hooks.get(event, []):
        for h in entry.get("hooks", []):
            if sentinel in h.get("command", ""):
                if h["command"] == cmd:
                    return False
                h["command"] = cmd
                return True
    hooks.setdefault(event, []).insert(0, new_entry)
    return True


def wire_hooks(dry_run: bool = False) -> int:
    """Wire or upgrade all 4 torch hooks in settings.json."""
    settings = _read_settings()
    changed  = False
    env      = settings.setdefault("env", {})

    # Pin data directory
    data_dir_str = _USER_DATA_DIR.as_posix()
    if env.get("CLAUDE_PLUGIN_DATA") != data_dir_str:
        env["CLAUDE_PLUGIN_DATA"] = data_dir_str
        _ok(f"Set CLAUDE_PLUGIN_DATA → {_USER_DATA_DIR}")
        changed = True
    else:
        _skip("CLAUDE_PLUGIN_DATA already correct")

    # Remove stale env var
    if "CLAUDE_PLUGIN_ROOT" in env:
        del env["CLAUDE_PLUGIN_ROOT"]
        _ok("Removed stale CLAUDE_PLUGIN_ROOT")
        changed = True

    hooks = settings.setdefault("hooks", {})

    # Wire each hook pointing at stable runtime dir
    cmd      = _hook_cmd_for("on-prompt-submit.py")
    tool_cmd = _hook_cmd_for("on-tool-use.py")
    stop_cmd = _hook_cmd_for("on-stop.py")

    for event, entry, sentinel, hook_cmd, label in [
        (
            "UserPromptSubmit",
            {"hooks": [{"type": "command", "command": cmd}]},
            _HOOK_SENTINEL, cmd, "UserPromptSubmit",
        ),
        (
            "SubagentStart",
            {"hooks": [{"type": "command", "command": cmd}]},
            _HOOK_SENTINEL, cmd, "SubagentStart",
        ),
        (
            "PostToolUse",
            {"matcher": "Skill", "hooks": [{"type": "command", "command": tool_cmd}]},
            _TOOL_HOOK_SENTINEL, tool_cmd, "PostToolUse (Skill)",
        ),
        (
            "Stop",
            {"hooks": [{"type": "command", "command": stop_cmd}]},
            _STOP_HOOK_SENTINEL, stop_cmd, "Stop",
        ),
    ]:
        if _wire_or_upgrade(hooks, event, entry, sentinel, hook_cmd):
            _ok(f"Wired/upgraded {label} → {hook_cmd}")
            changed = True
        else:
            _skip(f"{label} hook already correct")

    if changed and not dry_run:
        _write_settings(settings)

    if dry_run:
        print("\n[dry-run] No changes written.")
        return 0

    # Post-write verification
    fresh  = _read_settings()
    issues = _verify_hooks(fresh)
    if issues:
        _fail(f"Post-write verification found {issues} issue(s)")
    return issues

# ─────────────────────────────────────────────────────────────────────────────
# §9  Hook removal
# ─────────────────────────────────────────────────────────────────────────────

def remove_hooks(dry_run: bool = False) -> int:
    """Remove all 4 torch hook entries and env vars from settings.json."""
    settings = _read_settings()
    changed  = False
    hooks    = settings.get("hooks", {})

    for event, sentinel, label in [
        ("UserPromptSubmit", _HOOK_SENTINEL,      "UserPromptSubmit"),
        ("SubagentStart",    _HOOK_SENTINEL,      "SubagentStart"),
        ("PostToolUse",      _TOOL_HOOK_SENTINEL, "PostToolUse"),
        ("Stop",             _STOP_HOOK_SENTINEL, "Stop"),
    ]:
        before = hooks.get(event, [])
        after  = [
            e for e in before
            if not any(sentinel in h.get("command", "") for h in e.get("hooks", []))
        ]
        if len(after) < len(before):
            if after:
                hooks[event] = after
            else:
                hooks.pop(event, None)
            _ok(f"Removed {label} hook")
            changed = True
        else:
            _skip(f"{label} hook not present")

    env = settings.get("env", {})
    for var in ("CLAUDE_PLUGIN_DATA", "CLAUDE_PLUGIN_ROOT"):
        if var in env:
            del env[var]
            _ok(f"Removed {var} env var")
            changed = True

    marketplaces = settings.get("extraKnownMarketplaces", {})
    if _MARKETPLACE_KEY in marketplaces:
        del marketplaces[_MARKETPLACE_KEY]
        if not marketplaces:
            settings.pop("extraKnownMarketplaces", None)
        _ok(f"Removed marketplace registration '{_MARKETPLACE_KEY}'")
        changed = True

    if changed and not dry_run:
        _write_settings(settings)
        print("\n✓ Hooks removed.")
    elif not changed:
        print("\n✓ Nothing to remove.")

    return 0

# ─────────────────────────────────────────────────────────────────────────────
# §10  Verification
# ─────────────────────────────────────────────────────────────────────────────

def _verify_hooks(settings: dict) -> int:
    """Check all 4 hooks are wired correctly. Returns issue count."""
    cmd      = _hook_cmd_for("on-prompt-submit.py")
    tool_cmd = _hook_cmd_for("on-tool-use.py")
    stop_cmd = _hook_cmd_for("on-stop.py")
    issues   = 0

    venv_py = _venv_python()
    venv_ok = venv_py.exists()
    if venv_ok:
        _ok(f"Runtime venv: {venv_py}")
    else:
        _fail(f"Runtime venv missing: {_VENV_DIR} — run: {_PY_CMD} setup.py")
        issues += 1

    for event, sentinel, expected_cmd, label in [
        ("UserPromptSubmit", _HOOK_SENTINEL,      cmd,      "UserPromptSubmit hook"),
        ("SubagentStart",    _HOOK_SENTINEL,      cmd,      "SubagentStart hook"),
        ("PostToolUse",      _TOOL_HOOK_SENTINEL, tool_cmd, "PostToolUse hook"),
        ("Stop",             _STOP_HOOK_SENTINEL, stop_cmd, "Stop hook"),
    ]:
        found = correct = False
        for entry in settings.get("hooks", {}).get(event, []):
            for h in entry.get("hooks", []):
                if sentinel in h.get("command", ""):
                    found = True
                    correct = (h["command"] == expected_cmd)
        if not found:
            _fail(f"{label} NOT wired in settings.json")
            issues += 1
        elif not correct:
            if not venv_ok:
                _warn(f"{label} wired (command will update when venv is recreated)")
            else:
                actual = next(
                    (h["command"]
                     for e in settings.get("hooks", {}).get(event, [])
                     for h in e.get("hooks", [])
                     if sentinel in h.get("command", "")),
                    "?",
                )
                _warn(f"{label} wired but command differs\n"
                      f"    expected: {expected_cmd}\n"
                      f"    actual:   {actual}")
                issues += 1
        else:
            _ok(f"{label}: {expected_cmd}")

    env = settings.get("env", {})
    if env.get("CLAUDE_PLUGIN_DATA") != _USER_DATA_DIR.as_posix():
        _fail(f"CLAUDE_PLUGIN_DATA not set correctly (expected {_USER_DATA_DIR})")
        issues += 1
    else:
        _ok(f"CLAUDE_PLUGIN_DATA → {_USER_DATA_DIR}")

    return issues


def verify_all() -> int:
    """Full 14-check verification. Returns issue count."""
    print("\n=== Torch — installation health check ===\n")
    issues = 0

    # 1. Python version
    if sys.version_info >= (3, 10):
        _ok(f"Python {sys.version.split()[0]}")
    else:
        _fail(f"Python 3.10+ required — got {sys.version.split()[0]}")
        issues += 1

    # 2. Claude CLI
    try:
        r = subprocess.run(
            ["claude", "--version"], capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=False,
        )
        if r.returncode == 0:
            _ok(f"Claude Code: {(r.stdout or r.stderr).strip().splitlines()[0]}")
        else:
            _fail("'claude' CLI not found")
            issues += 1
    except FileNotFoundError:
        _fail("'claude' CLI not found")
        issues += 1

    # 3. Venv health
    venv_py = _venv_python()
    if venv_py.exists():
        try:
            r = subprocess.run(
                [str(venv_py), "-c",
                 "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"],
                capture_output=True, check=False, timeout=10,
            )
            if r.returncode == 0:
                _ok(f"Runtime venv: {venv_py}")
            else:
                _fail(f"Runtime venv unhealthy: {venv_py}")
                issues += 1
        except Exception:
            _fail(f"Runtime venv unreachable: {venv_py}")
            issues += 1
    else:
        _fail(f"Runtime venv missing: {_VENV_DIR}")
        issues += 1

    # 4. Runtime dir exists
    if _RUNTIME_DIR.is_dir():
        _ok(f"Runtime dir: {_RUNTIME_DIR}")
    else:
        _fail(f"Runtime dir missing: {_RUNTIME_DIR}")
        issues += 1

    # 5. All runtime files present
    manifest_path = _RUNTIME_DIR / ".manifest.json"
    manifest = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    all_present = True
    for rel in _RUNTIME_FILES:
        f = _RUNTIME_DIR / rel
        if not f.exists():
            _fail(f"Missing runtime file: {rel}")
            issues += 1
            all_present = False
    if all_present:
        _ok(f"All {len(_RUNTIME_FILES)} runtime files present")

    # 6. Staleness check (SHA256 vs manifest)
    if manifest.get("files") and all_present:
        stale = []
        for rel, expected_hash in manifest["files"].items():
            f = _RUNTIME_DIR / rel
            if f.exists() and _sha256(f) != expected_hash:
                stale.append(rel)
        if stale:
            _warn(f"Modified since install: {', '.join(stale)}")
        else:
            _ok("Runtime files match manifest checksums")

        # Compare against source if resolvable
        try:
            source_root = _find_plugin_root()
            outdated = []
            for rel in _RUNTIME_FILES:
                src = source_root / rel
                dst = _RUNTIME_DIR / rel
                if src.exists() and dst.exists():
                    if _sha256(src) != _sha256(dst):
                        outdated.append(rel)
            if outdated:
                _warn(f"Outdated vs source: {', '.join(outdated)} — re-run setup.py")
            else:
                _ok("Runtime files up to date with source")
        except SystemExit:
            _skip("Source plugin root not resolvable — cannot compare")

    # 7–9. Settings checks
    settings = _read_settings()
    try:
        json.loads(_SETTINGS.read_text(encoding="utf-8"))
        _ok("settings.json parseable")
    except FileNotFoundError:
        _fail("settings.json not found")
        issues += 1
    except json.JSONDecodeError:
        _fail("settings.json is invalid JSON")
        issues += 1

    issues += _verify_hooks(settings)

    # 10. No stale CLAUDE_PLUGIN_ROOT
    if "CLAUDE_PLUGIN_ROOT" in settings.get("env", {}):
        _warn("Stale CLAUDE_PLUGIN_ROOT in settings.json — re-run setup.py")
    else:
        _ok("No stale CLAUDE_PLUGIN_ROOT")

    # 11–12. Daemon socket / PID health
    if not _IS_WINDOWS:
        socks = list(_CLAUDE_DIR.glob("torch-router-*.sock"))
        if socks:
            alive = False
            try:
                import socket as _sock
                with _sock.socket(_sock.AF_UNIX, _sock.SOCK_STREAM) as s:
                    s.settimeout(0.5)
                    s.connect(str(socks[0]))
                    alive = True
            except Exception:
                pass
            if alive:
                _ok(f"Daemon socket LIVE ({socks[0].name})")
            else:
                _warn(f"Daemon socket STALE ({socks[0].name}) — self-heals on next prompt")
        else:
            _ok("No daemon socket — will auto-start on first prompt")

        pid_files = list(_CLAUDE_DIR.glob("torch-router-*.pid"))
        for pf in pid_files:
            try:
                pid = int(pf.read_text(encoding="utf-8").strip())
                os.kill(pid, 0)
                _ok(f"Daemon PID {pid} alive ({pf.name})")
            except (ValueError, OSError, ProcessLookupError):
                _warn(f"Stale PID file: {pf.name}")

    # 13. Smoke test
    issues += 0 if step_smoke_test() else 1

    # 14. macOS quarantine
    if platform.system() == "Darwin":
        quarantined = []
        for rel in _RUNTIME_FILES:
            f = _RUNTIME_DIR / rel
            if not f.exists():
                continue
            r = subprocess.run(["xattr", "-l", str(f)], capture_output=True, check=False)
            if b"com.apple.quarantine" in r.stdout:
                quarantined.append(rel)
        if quarantined:
            _warn(f"Quarantine attribute on: {', '.join(quarantined)}")
        else:
            _ok("No quarantine attributes on runtime files")

    return issues

# ─────────────────────────────────────────────────────────────────────────────
# §11  Smoke test
# ─────────────────────────────────────────────────────────────────────────────

def step_smoke_test() -> bool:
    """Pipe a test prompt through the hook and verify JSON output."""
    hook = _RUNTIME_DIR / "hooks" / "on-prompt-submit.py"
    if not hook.exists():
        _warn(f"Cannot smoke-test — hook not at: {hook}")
        return False

    venv_py = _venv_python()
    interpreter = str(venv_py) if venv_py.exists() else sys.executable

    payload = json.dumps({
        "session_id": "install-smoke-test",
        "prompt": "scan my codebase for security vulnerabilities",
    })

    try:
        r = subprocess.run(
            [interpreter, str(hook)],
            input=payload,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
        )
    except subprocess.TimeoutExpired:
        _fail("Smoke test timed out after 15 s")
        return False

    if r.returncode != 0:
        _fail(f"Hook process exited {r.returncode}")
        if r.stderr.strip():
            print(f"  stderr: {r.stderr.strip()[:400]}")
        return False

    try:
        out = json.loads(r.stdout)
    except json.JSONDecodeError:
        _fail(f"Hook returned non-JSON:\n  {r.stdout[:400]}")
        return False

    specific = out.get("hookSpecificOutput", {})
    if specific.get("hookEventName") == "UserPromptSubmit":
        hint = specific.get("additionalContext", "")
        _ok(f"Smoke test passed → {hint.splitlines()[0] if hint else '(empty hint)'}")
        return True

    if out == {}:
        _ok("Smoke test passed — prompt matched no capability above threshold")
        return True

    _fail(f"Unexpected hook output:\n  {r.stdout[:400]}")
    return False

# ─────────────────────────────────────────────────────────────────────────────
# §12  DG-repo-only features (marketplace, cue, SSH probe)
# ─────────────────────────────────────────────────────────────────────────────

def _is_dg_repo() -> bool:
    """Return True if running from the DG repo checkout (docs/managed-cue-inject.md exists)."""
    # __file__ is at plugins/torch/setup.py → repo root is ../../
    candidate = Path(__file__).resolve().parent.parent.parent / "docs" / "managed-cue-inject.md"
    return candidate.exists()


def _dg_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _probe_ssh() -> bool:
    if _IS_WINDOWS:
        return False
    try:
        if subprocess.run(["which", "ssh"], capture_output=True, check=False).returncode != 0:
            return False
        r = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
             "-o", "StrictHostKeyChecking=accept-new",
             "-T", "git@app.gitlab.barcapint.com"],
            capture_output=True, timeout=10, check=False,
        )
        return r.returncode in (0, 1)
    except Exception:
        return False


def _pick_marketplace_url() -> str:
    if "DISCOVERY_MARKETPLACE_URL" in os.environ:
        return os.environ["DISCOVERY_MARKETPLACE_URL"]
    if _probe_ssh():
        _ok("SSH probe: success — using SSH URL")
        return _MARKETPLACE_URL_SSH
    _ok("SSH probe: unavailable — using HTTPS URL")
    return _MARKETPLACE_URL_HTTPS


def step_register_marketplace(dry_run: bool, url: str) -> None:
    settings = _read_settings()
    registered_url = (
        settings.get("extraKnownMarketplaces", {})
                .get(_MARKETPLACE_KEY, {})
                .get("source", {})
                .get("url", "")
    )
    if registered_url == url:
        _skip(f"Marketplace '{_MARKETPLACE_KEY}' already registered ({url})")
        return
    if registered_url and registered_url != url:
        _ok(f"Updating marketplace URL: {registered_url} → {url}")

    settings.setdefault("extraKnownMarketplaces", {})[_MARKETPLACE_KEY] = {
        "source": {
            "source": "git",
            "url": url,
            "sparsePaths": [".claude-plugin", "plugins"],
        }
    }
    _ok(f"Registered marketplace '{_MARKETPLACE_KEY}' → {url}")
    if not dry_run:
        _write_settings(settings)


def _plugin_installed() -> bool:
    r = subprocess.run(
        ["claude", "plugins", "list"], capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )
    return "torch" in (r.stdout or "")


def step_install_plugin(dry_run: bool) -> bool:
    if not dry_run and _plugin_installed():
        _skip("torch already installed")
        return True
    cmd = ["claude", "plugins", "install", "torch@torch"]
    print(f"  $ {' '.join(cmd)}")
    if dry_run:
        return True
    r = subprocess.run(cmd, check=False)
    if r.returncode != 0:
        _fail(f"Plugin install failed (rc={r.returncode})")
        return False
    _ok("Installed: torch@torch")
    return True

# ─────────────────────────────────────────────────────────────────────────────
# §13  Cue helpers
# ─────────────────────────────────────────────────────────────────────────────

def _remove_dg_section(text: str) -> str:
    return re.sub(
        r'\n*## Torch\n.*?(?=\n## |\Z)', '', text, flags=re.DOTALL
    ).rstrip()


def _read_cue_block() -> str:
    if not _is_dg_repo():
        return ""
    path = _dg_repo_root() / "docs" / "managed-cue-inject.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def step_append_cue(claude_md: Path, dry_run: bool) -> None:
    cue_block = _read_cue_block()
    if not cue_block:
        _warn("Managed cue source not found or empty")
        return

    try:
        existing = claude_md.read_text(encoding="utf-8")
    except FileNotFoundError:
        existing = ""

    if _CUE_FULL_MARKER in existing:
        idx = existing.find("\n\n" + _CUE_FULL_MARKER)
        if idx == -1:
            idx = existing.find(_CUE_FULL_MARKER)
        cleaned = existing[:idx].rstrip() if idx != -1 else existing
        print(f"  Replacing bloated cue injection in {claude_md}")
        if not dry_run:
            claude_md.parent.mkdir(parents=True, exist_ok=True)
            claude_md.write_text(cleaned + "\n\n" + cue_block + "\n", encoding="utf-8")
        _ok("Replaced bloated cue with slim version")
        return

    if _CUE_SENTINEL in existing:
        if cue_block in existing:
            _skip(f"Cue already up to date in {claude_md}")
            return
        cleaned = _remove_dg_section(existing)
        print(f"  Updating managed cue in {claude_md}")
        if not dry_run:
            claude_md.write_text(cleaned + "\n\n" + cue_block + "\n", encoding="utf-8")
        _ok("Managed cue updated")
        return

    print(f"  Appending managed cue to {claude_md}")
    if not dry_run:
        claude_md.parent.mkdir(parents=True, exist_ok=True)
        with claude_md.open("a", encoding="utf-8") as fh:
            fh.write("\n\n" + cue_block + "\n")
    _ok("Managed cue appended")


def _remove_cue(claude_md: Path, dry_run: bool) -> None:
    try:
        text = claude_md.read_text(encoding="utf-8")
    except FileNotFoundError:
        _skip("CLAUDE.md not found")
        return

    if _CUE_SENTINEL not in text:
        _skip("Cue not present in CLAUDE.md")
        return

    if _CUE_FULL_MARKER in text:
        idx = text.find("\n\n" + _CUE_FULL_MARKER)
        if idx == -1:
            idx = text.find(_CUE_FULL_MARKER)
        cleaned = text[:idx].rstrip() if idx != -1 else text
    else:
        cleaned = _remove_dg_section(text)

    if not dry_run:
        claude_md.write_text(cleaned + "\n", encoding="utf-8")
    _ok("Managed cue removed")

# ─────────────────────────────────────────────────────────────────────────────
# §14  Top-level commands
# ─────────────────────────────────────────────────────────────────────────────

def cmd_install(args: argparse.Namespace) -> int:
    dry_run = args.dry_run
    do_marketplace = args.marketplace
    do_cue = args.cue
    claude_md = Path(args.claude_md)

    _step("1/7  Preconditions")
    ok = True
    if sys.version_info < (3, 10):
        _fail(f"Python 3.10+ required — got {sys.version.split()[0]}")
        ok = False
    else:
        _ok(f"Python {sys.version.split()[0]}")
    try:
        r = subprocess.run(
            ["claude", "--version"], capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=False,
        )
        if r.returncode != 0:
            _fail("'claude' CLI not found")
            ok = False
        else:
            _ok(f"Claude Code: {(r.stdout or r.stderr).strip().splitlines()[0]}")
    except FileNotFoundError:
        _fail("'claude' CLI not found")
        ok = False
    if not ok and not dry_run:
        return 1

    _step("2/7  Resolve source + copy runtime")
    plugin_root = _find_plugin_root()
    _ok(f"Source plugin root: {plugin_root}")
    if not step_copy_runtime(plugin_root, dry_run):
        if not dry_run:
            return 1

    _step("3/7  Runtime venv")
    venv_ok = step_ensure_venv(dry_run)
    if not venv_ok and not dry_run:
        _warn("Runtime venv creation failed — hooks will use system Python (no isolation)")
        print()
        print("  " + "=" * 56)
        print("  WARNING: No venv isolation.")
        print("  Hooks will run under system Python.")
        print("  Fix: install python3-venv (Debian/Ubuntu)")
        print("         or ensure Python 3.10+ venv module works.")
        print("  " + "=" * 56)
        print()

    _step("4/7  Wire hooks")
    wire_hooks(dry_run)

    _step("5/7  Stop stale daemons")
    step_clear_sockets(dry_run)

    # DG-repo-only features
    if do_marketplace:
        if _is_dg_repo():
            _step("(DG) Marketplace registration")
            url = _pick_marketplace_url()
            step_register_marketplace(dry_run, url)

            _step("(DG) Plugin install")
            if not step_install_plugin(dry_run):
                if url != _MARKETPLACE_URL_HTTPS and not dry_run:
                    _warn("Plugin install failed — retrying with HTTPS URL")
                    step_register_marketplace(dry_run, _MARKETPLACE_URL_HTTPS)
                    step_install_plugin(dry_run)
        else:
            _skip("--marketplace: not running from DG repo — flag ignored")

    if do_cue:
        if _is_dg_repo():
            _step("(DG) Managed cue")
            step_append_cue(claude_md, dry_run)
        else:
            _skip("--cue: not running from DG repo — flag ignored")

    _step("6/7  Smoke test")
    if not dry_run:
        if not step_smoke_test():
            _fail("Smoke test failed — installation may be incomplete")
            print(f"  Diagnose with: {_PY_CMD} setup.py --verify", file=sys.stderr)
            return 1
    else:
        _skip("[dry-run] Smoke test skipped")

    _step("7/7  Done")
    print()
    print("=" * 60)
    if dry_run:
        print("  Dry-run complete — no changes made.")
    else:
        print("  Install complete.")
        print()
        print("  ACTION REQUIRED: restart Claude Code.")
        print("  The UserPromptSubmit hook takes effect on the next")
        print("  session start only.")
    print("=" * 60)
    return 0


def cmd_verify() -> int:
    issues = verify_all()
    print()
    print("=" * 60)
    if issues == 0:
        print("  All checks passed — installation is healthy.")
    else:
        print(f"  {issues} issue(s) found.")
        print(f"  Fix with: {_PY_CMD} setup.py")
    print("=" * 60)
    return 0 if issues == 0 else 1


def cmd_uninstall(args: argparse.Namespace) -> int:
    dry_run = args.dry_run
    do_cue = args.cue
    claude_md = Path(args.claude_md)

    _step("1/5  Stop daemons + clear sockets")
    step_clear_sockets(dry_run)

    _step("2/5  Remove hook wiring + marketplace registration")
    remove_hooks(dry_run)

    _step("3/5  Remove runtime copy")
    if _RUNTIME_DIR.exists():
        print(f"  Removing: {_RUNTIME_DIR}")
        if not dry_run:
            shutil.rmtree(_RUNTIME_DIR, ignore_errors=True)
        _ok(f"Removed {_RUNTIME_DIR}")
    else:
        _skip(f"Runtime dir not found: {_RUNTIME_DIR}")

    _step("4/5  Remove data + venv")
    torch_dir = _CLAUDE_DIR / "torch"
    if torch_dir.exists():
        print(f"  Removing: {torch_dir}")
        if not dry_run:
            shutil.rmtree(torch_dir, ignore_errors=True)
        _ok(f"Removed {torch_dir}")
    else:
        _skip(f"Data dir not found: {torch_dir}")

    _step("5/5  Managed cue")
    if do_cue:
        _remove_cue(claude_md, dry_run)
    else:
        _skip("Pass --cue to also remove the managed cue from CLAUDE.md")

    print()
    print("=" * 60)
    if dry_run:
        print("  Dry-run complete — no changes made.")
    else:
        print("  Uninstall complete.")
        print("  Restart Claude Code to deactivate the push channel.")
    print("=" * 60)
    return 0

# ─────────────────────────────────────────────────────────────────────────────
# §15  CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(
        prog="setup.py",
        description="Torch — unified installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--verify", action="store_true",
        help="Check installation health and run smoke test",
    )
    mode.add_argument(
        "--uninstall", action="store_true",
        help="Remove hooks, runtime copy, venv, data",
    )
    p.add_argument(
        "--marketplace", action="store_true",
        help="(DG repo only) Register marketplace + install plugin",
    )
    p.add_argument(
        "--cue", action="store_true",
        help="(DG repo only) Manage assisted-mode cue in CLAUDE.md",
    )
    p.add_argument(
        "--claude-md", default=str(_CLAUDE_DIR / "CLAUDE.md"),
        help="Path to CLAUDE.md (default: ~/.claude/CLAUDE.md)",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Preview all actions, make no changes",
    )
    args = p.parse_args()

    if args.dry_run:
        print("[dry-run — no changes will be made]\n")

    if args.verify:
        sys.exit(cmd_verify())
    elif args.uninstall:
        sys.exit(cmd_uninstall(args))
    else:
        sys.exit(cmd_install(args))


if __name__ == "__main__":
    main()
