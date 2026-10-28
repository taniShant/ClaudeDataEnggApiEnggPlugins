#!/usr/bin/env python3
"""
validator/spec-check.py - Post-write validation hook for Claude Code.

Validates any .spec or .spec.yaml file that was just written or edited.
Called automatically by the Claude Code hook system after Write/Edit tool use,
or manually from the command line.

Usage (CLI)::

    python validator/spec-check.py path/to/file.spec
    python validator/spec-check.py file1.spec file2.spec

Exit codes:
    0  All files are valid.
    1  One or more files are invalid or could not be read.
    2  Usage error (no arguments supplied).

Claude Code hook context:
    The hook runner passes the file path as a command-line argument.
    All output goes to stdout so it appears in the Claude Code UI.
"""

import sys
import os

# ---------------------------------------------------------------------------
# Path resolution — allow imports from both the project root and the src/
# directory regardless of where the hook is invoked from.
# ---------------------------------------------------------------------------

_HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_HOOK_DIR)
_SRC_DIR = os.path.join(_PROJECT_ROOT, "src")

for _path in (_SRC_DIR, _PROJECT_ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)


# ---------------------------------------------------------------------------
# Import validator
# ---------------------------------------------------------------------------

def _import_validator():
    """
    Import spec_validator, handling path edge cases.

    Returns:
        The spec_validator module.

    Raises:
        ImportError: If the module cannot be found.
    """
    try:
        import spec_validator
        return spec_validator
    except ImportError:
        # Last-resort: try sibling of this file
        hook_src = os.path.join(_HOOK_DIR, "..", "src")
        sys.path.insert(0, os.path.abspath(hook_src))
        import spec_validator
        return spec_validator


# ---------------------------------------------------------------------------
# File filtering
# ---------------------------------------------------------------------------

def _is_spec_file(path: str) -> bool:
    """
    Return True if the file extension matches .spec or .spec.yaml.

    Args:
        path: File path string to test.

    Returns:
        True if the file should be validated, False otherwise.
    """
    lower = path.lower()
    return lower.endswith(".spec") or lower.endswith(".spec.yaml")


# ---------------------------------------------------------------------------
# Validation runner
# ---------------------------------------------------------------------------

def validate_file(path: str, validator) -> bool:
    """
    Validate a single spec file and print results.

    Args:
        path: Path to the .spec file.
        validator: The spec_validator module (already imported).

    Returns:
        True if the file is valid, False otherwise.
    """
    result = validator.validate_spec_file(path)

    if result.valid and not result.warnings:
        print(f"OK  {path}")
        return True

    print(result)
    return result.valid


def run(argv: list) -> int:
    """
    Main entry point for the hook.

    Args:
        argv: sys.argv[1:] — list of file paths to validate.

    Returns:
        Exit code: 0 (all valid), 1 (errors found), 2 (usage error).
    """
    if not argv:
        print(
            "Usage: python validator/spec-check.py <file.spec> [file2.spec ...]",
            file=sys.stdout,
        )
        return 2

    # Filter to spec files only (the hook may be called with any file path)
    spec_files = [p for p in argv if _is_spec_file(p)]

    if not spec_files:
        # Nothing to validate — not an error
        return 0

    try:
        validator = _import_validator()
    except ImportError as exc:
        print(
            f"ERROR: Could not import spec_validator: {exc}\n"
            f"       Make sure src/ is on the Python path.",
            file=sys.stdout,
        )
        return 1

    all_valid = True
    for path in spec_files:
        if not os.path.exists(path):
            print(f"ERROR: File not found: {path}")
            all_valid = False
            continue
        valid = validate_file(path, validator)
        if not valid:
            all_valid = False

    return 0 if all_valid else 1


# ---------------------------------------------------------------------------
# Hook entrypoint — also supports Claude Code's JSON envelope when called
# with a single JSON argument containing a "tool_input" key.
# ---------------------------------------------------------------------------

def _extract_paths_from_hook_input(argv: list) -> list:
    """
    Extract file paths from either direct CLI args or a Claude Code hook
    JSON envelope.

    Claude Code may call hooks with a single JSON string argument of the form::

        {"tool_use_id": "...", "tool_name": "Write",
         "tool_input": {"file_path": "some/file.spec", ...}}

    Args:
        argv: Raw sys.argv[1:].

    Returns:
        List of file paths to validate.
    """
    if not argv:
        return []

    # Try to parse the first argument as JSON (hook envelope)
    if len(argv) == 1:
        import json
        try:
            data = json.loads(argv[0])
            if isinstance(data, dict):
                # Claude Code hook envelope
                tool_input = data.get("tool_input", {})
                if isinstance(tool_input, dict):
                    file_path = tool_input.get("file_path") or tool_input.get("path")
                    if file_path:
                        return [file_path]
            return argv  # Not an envelope, treat as plain path
        except (json.JSONDecodeError, ValueError):
            pass  # Not JSON — treat as plain file paths

    return argv


if __name__ == "__main__":
    paths = _extract_paths_from_hook_input(sys.argv[1:])
    sys.exit(run(paths))
