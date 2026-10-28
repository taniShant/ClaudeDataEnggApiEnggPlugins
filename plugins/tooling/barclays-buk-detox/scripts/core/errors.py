"""Structured JSON error handling for detox pipeline scripts."""

from __future__ import annotations

import json
import sys
from typing import NoReturn


def error_exit(message: str, stage: str, script: str | None = None) -> NoReturn:
    """Print structured JSON error to stdout and exit with code 1."""
    output = {
        "status": "error",
        "error": message,
        "stage": stage,
    }
    if script:
        output["script"] = script
    json.dump(output, sys.stdout)
    sys.stdout.write("\n")
    sys.exit(1)


def error_response(message: str, stage: str, **extra) -> dict:
    """Return a structured error dict (for use when not exiting immediately)."""
    result = {
        "status": "error",
        "error": message,
        "stage": stage,
    }
    result.update(extra)
    return result
