"""Single source of truth for the Detox plugin version.

Reads from .claude-plugin/plugin.json at import time so that every
script emits the same version without hardcoding it.
"""

from __future__ import annotations

import json
from pathlib import Path

# scripts/telemetry/version.py → three parents up reaches the plugin root.
_PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent
_PLUGIN_JSON = _PLUGIN_ROOT / ".claude-plugin" / "plugin.json"

try:
    PLUGIN_VERSION: str = json.loads(_PLUGIN_JSON.read_text())["version"]
except (OSError, KeyError, json.JSONDecodeError):
    PLUGIN_VERSION = "unknown"
