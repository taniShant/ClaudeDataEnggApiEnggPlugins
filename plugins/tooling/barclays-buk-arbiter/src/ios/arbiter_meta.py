#!/usr/bin/env python3
"""Provenance stamps for Arbiter iOS artifacts.

Every JSON artifact the plugin writes carries a `generatedBy` block with the plugin
version and a hash of each script that produced it. Downstream steps (planner,
executor) refuse input without a stamp, so results can't silently come from
ad-hoc scripts written outside the plugin.
"""

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable

PLUGIN_NAME = "barclays-buk-arbiter"
_SRC_DIR = Path(__file__).resolve().parent
_PLUGIN_JSON = _SRC_DIR.parent.parent / ".claude-plugin" / "plugin.json"


def plugin_version() -> str:
    try:
        return json.loads(_PLUGIN_JSON.read_text()).get("version", "unknown")
    except (IOError, OSError, ValueError):
        return "unknown"


def _sha(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    except (IOError, OSError):
        return "missing"


def stamp(scripts: Iterable[str]) -> Dict[str, Any]:
    """`generatedBy` block: plugin version, interpreter and script hashes."""
    return {
        "plugin": PLUGIN_NAME,
        "version": plugin_version(),
        "pluginPath": str(_SRC_DIR),
        "python": sys.executable,
        "scripts": {name: _sha(_SRC_DIR / name) for name in scripts},
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
    }


def require_stamp(data: Dict[str, Any], artifact: str, allow_unstamped: bool = False) -> None:
    """Stop if an artifact wasn't produced by this plugin's scripts."""
    meta = data.get("generatedBy") if isinstance(data, dict) else None
    if meta and meta.get("plugin") == PLUGIN_NAME:
        return
    message = (f"{artifact} has no `generatedBy` stamp from {PLUGIN_NAME} — it was not produced "
               "by the plugin's scripts. Re-run the analysis with the installed plugin.")
    if allow_unstamped:
        print(f"⚠ {message} (continuing: --allow-unstamped)", file=sys.stderr)
        return
    raise SystemExit(f"❌ {message}")


def write_json(path: str, data: Dict[str, Any], compact: bool = False) -> None:
    """Write JSON; compact for large artifacts (ENTITIES/CONFIDENCE run to 100+ MB indented)."""
    with open(path, "w") as f:
        if compact:
            json.dump(data, f, separators=(",", ":"))
        else:
            json.dump(data, f, indent=2)


def usage_data_problem(entities_data: Dict[str, Any], usage_data: Dict[str, Any]) -> str:
    """Why usage data can't be trusted, or "" if it can.

    Scoring without usages marks everything SAFE, so a missing `usages` key is an
    error, and so is an empty list for a codebase of any real size.
    """
    entities = entities_data.get("entities", []) if isinstance(entities_data, dict) else []
    if not entities:
        return ""
    if "usages" not in usage_data:
        return "No usage data: the entities/usage file has no `usages` key"
    if not usage_data["usages"] and len(entities) > 100:
        return f"No usage data: `usages` is empty for {len(entities)} entities"
    return ""
