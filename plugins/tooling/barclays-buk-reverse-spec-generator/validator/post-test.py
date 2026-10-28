"""
post-test.py — PostToolUse hook for test file modifications.

Fires after a test file is written or edited. Finds the nearest .spec and
.convergence.yaml, runs the test suite, and updates convergence state.

Prints a one-line status summary so the developer sees immediate feedback
on how test changes affect loop progress.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Allow imports from src/ regardless of CWD
_PLUGIN_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PLUGIN_ROOT))

from src.convergence_state import load_state, save_state, update_from_test_results
from src.test_runner import detect_framework, run_tests
from src.spec_serializer import load_spec


def _find_spec_for_test_file(test_file: Path) -> Path | None:
    """
    Walk up from the test file's directory looking for a .spec file.
    Stops at the project root (build.gradle / pom.xml / package.json).
    """
    current = test_file.parent
    for _ in range(8):  # max 8 levels up
        # Project root indicators — stop searching
        if any((current / marker).exists() for marker in ("build.gradle", "pom.xml", "package.json")):
            spec_files = list(current.glob("*.spec")) + list(current.glob("**/*.spec"))
            if spec_files:
                return spec_files[0]
            return None
        # Look for .spec files in this directory
        spec_files = list(current.glob("*.spec"))
        if spec_files:
            return spec_files[0]
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def _find_project_root(test_file: Path) -> Path:
    """Walk up to find the project root (build.gradle / pom.xml / package.json)."""
    current = test_file.parent
    for _ in range(8):
        if any((current / marker).exists() for marker in ("build.gradle", "pom.xml", "package.json")):
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return test_file.parent


def _extract_test_path_from_argv(argv: list) -> str | None:
    """
    Claude Code passes hook input as JSON on stdin or as argv.
    Try to extract the file path that was written/edited.
    """
    # Try JSON envelope from stdin
    if not sys.stdin.isatty():
        try:
            data = json.load(sys.stdin)
            path = (
                data.get("tool_input", {}).get("file_path")
                or data.get("file_path")
            )
            if path:
                return path
        except (json.JSONDecodeError, AttributeError):
            pass

    # Fall back to argv
    for arg in argv[1:]:
        if arg and not arg.startswith("-"):
            return arg
    return None


def run(argv: list) -> int:
    test_path_raw = _extract_test_path_from_argv(argv)
    if not test_path_raw:
        print("[post-test] No test file path provided — skipping", file=sys.stderr)
        return 0

    test_file = Path(test_path_raw).resolve()
    if not test_file.exists():
        return 0

    spec_path = _find_spec_for_test_file(test_file)
    if spec_path is None:
        print(f"[post-test] No .spec file found near {test_file.name} — skipping", file=sys.stderr)
        return 0

    project_root = _find_project_root(test_file)
    framework = detect_framework(project_root)

    if framework == "unknown":
        print(f"[post-test] Unknown test framework in {project_root} — skipping", file=sys.stderr)
        return 0

    print(f"[post-test] Running {framework} tests for {spec_path.name} ...", file=sys.stderr)

    try:
        spec = load_spec(str(spec_path))
    except Exception:
        spec = None

    try:
        results = run_tests(project_root, framework, spec)
    except Exception as exc:
        print(f"[post-test] Test run failed: {exc}", file=sys.stderr)
        return 0

    # Update convergence state
    state = load_state(spec_path)
    update_from_test_results(state, results)
    save_state(state, spec_path)

    # Status line
    status_icon = "✓" if results.success else "✗"
    print(
        f"[post-test] {status_icon} {results.passing}/{results.total} passing"
        f"  |  convergence: {state.convergence_pct:.1f}%"
        f"  ({spec_path.name})"
    )

    return 0 if results.success else 1


if __name__ == "__main__":
    sys.exit(run(sys.argv))
