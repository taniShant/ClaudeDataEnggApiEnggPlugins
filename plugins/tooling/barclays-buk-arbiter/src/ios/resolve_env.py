#!/usr/bin/env python3
"""Resolve the environment the Arbiter iOS scripts must run with.

Agents run this first, by its absolute path:

    python3 "${CLAUDE_PLUGIN_ROOT}/src/ios/resolve_env.py"

(Claude Code substitutes ${CLAUDE_PLUGIN_ROOT} in agent content when it loads the
agent; the variable is not exported to the Bash tool.)

Prints JSON with:
- pluginRoot / iosSrc / pluginVersion — taken from this script's own location, so
  they always describe the copy that is actually running
- python — the interpreter to use for every other script: the first candidate that
  is 3.10+ and can import tree_sitter, tree_sitter_swift and tree_sitter_objc.
  Different shells resolve `python3` differently (pyenv vs Homebrew vs /usr/bin), so
  agents must use this interpreter, not whatever `python3` is on PATH.
- installs / warnings — what the Claude Code plugin registry says about installed
  copies of barclays-buk-arbiter (several versions installed, this copy not the most
  recently updated one, registry missing or unreadable). Warnings don't fail the run.

Exit code 1 (with "ok": false and a "fix" line) if the plugin's scripts are
incomplete or no suitable interpreter exists.
Deliberately compatible with old Python 3 so any `python3` can run it.
"""

import json
import os
import shutil
import subprocess
import sys

PLUGIN_NAME = "barclays-buk-arbiter"
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(os.path.dirname(SRC_DIR))
PLUGIN_JSON = os.path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json")
REGISTRY = os.path.expanduser("~/.claude/plugins/installed_plugins.json")
REQUIRED_SCRIPTS = ("ios_call_graph_analyzer.py", "ios_confidence_engine.py",
                    "ios_planner.py", "ios_removal_executor.py")
PROBE = ("import sys, tree_sitter, tree_sitter_swift, tree_sitter_objc; "
         "assert sys.version_info >= (3, 10); print(sys.version.split()[0])")


def plugin_version():
    try:
        with open(PLUGIN_JSON) as f:
            return json.load(f).get("version", "unknown")
    except (IOError, OSError, ValueError):
        return "unknown"


def registry_check():
    """Installed copies of the plugin per the registry, and any warnings about them."""
    warnings = []
    try:
        with open(REGISTRY) as f:
            plugins = json.load(f).get("plugins", {})
    except (IOError, OSError):
        return [], ["Plugin registry not found (%s) — running from %s" % (REGISTRY, PLUGIN_ROOT)]
    except ValueError:
        return [], ["Plugin registry unreadable (%s) — running from %s" % (REGISTRY, PLUGIN_ROOT)]

    installs = []
    for key, entries in plugins.items():
        if not key.startswith(PLUGIN_NAME + "@"):
            continue
        for e in entries if isinstance(entries, list) else []:
            installs.append({
                "id": key, "scope": e.get("scope"), "version": e.get("version"),
                "installPath": e.get("installPath"), "lastUpdated": e.get("lastUpdated", ""),
                "projectPath": e.get("projectPath"),
                "running": os.path.realpath(e.get("installPath") or "") == os.path.realpath(PLUGIN_ROOT),
            })

    if not installs:
        warnings.append("%s is not in the plugin registry — running from %s "
                        "(e.g. --plugin-dir)" % (PLUGIN_NAME, PLUGIN_ROOT))
        return installs, warnings
    versions = sorted({i["version"] for i in installs if i["version"]})
    if len(versions) > 1:
        warnings.append("Several versions installed (%s); this run uses %s"
                        % (", ".join(versions), plugin_version()))
    if not any(i["running"] for i in installs):
        warnings.append("This copy (%s, %s) is not a registered install — e.g. --plugin-dir or a "
                        "development checkout" % (plugin_version(), PLUGIN_ROOT))
    newest = max(installs, key=lambda i: i["lastUpdated"])
    if not newest["running"] and any(i["running"] for i in installs):
        warnings.append("This copy (%s) is not the most recently updated install (%s, %s scope) — "
                        "restart Claude Code if you just updated the plugin"
                        % (plugin_version(), newest["version"], newest["scope"]))
    return installs, warnings


def candidates():
    seen = []
    found = [sys.executable]
    for name in ("python3", "python3.14", "python3.13", "python3.12", "python3.11", "python3.10"):
        path = shutil.which(name)
        if path:
            found.append(path)
    found += [os.path.expanduser("~/.pyenv/shims/python3"), "/opt/homebrew/bin/python3",
              "/usr/local/bin/python3", "/usr/bin/python3"]
    for path in found:
        real = os.path.realpath(path) if path else None
        if path and os.path.exists(path) and real not in seen:
            seen.append(real)
            yield path


def main():
    result = {"pluginRoot": PLUGIN_ROOT, "iosSrc": SRC_DIR, "pluginVersion": plugin_version()}
    result["installs"], result["warnings"] = registry_check()

    missing = [s for s in REQUIRED_SCRIPTS if not os.path.isfile(os.path.join(SRC_DIR, s))]
    if missing:
        result.update({"ok": False, "missingScripts": missing,
                       "fix": "Arbiter plugin scripts incomplete — reinstall %s" % PLUGIN_NAME})
        print(json.dumps(result, indent=2))
        return 1

    tried = []
    for python in candidates():
        try:
            out = subprocess.run([python, "-c", PROBE], capture_output=True, text=True, timeout=60)
        except Exception as e:
            tried.append({"python": python, "error": str(e)})
            continue
        if out.returncode == 0:
            result.update({"ok": True, "python": python, "pythonVersion": out.stdout.strip()})
            print(json.dumps(result, indent=2))
            return 0
        tried.append({"python": python, "error": (out.stderr.strip().splitlines() or ["failed"])[-1]})

    result.update({
        "ok": False, "tried": tried,
        "fix": "pip install tree-sitter tree-sitter-swift tree-sitter-objc  (with a Python 3.10+ interpreter)",
    })
    print(json.dumps(result, indent=2))
    return 1


if __name__ == "__main__":
    sys.exit(main())
