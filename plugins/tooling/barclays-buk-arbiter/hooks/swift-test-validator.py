#!/usr/bin/env python3
"""Post-removal Swift test validation hook.

Runs xctest/swift test after removal and validates no regressions.
"""

import subprocess
import sys
import json
from pathlib import Path
from typing import Tuple, Dict, Any


def validate_swift_tests(repo_path: str = ".", category: str = "LIKELY",
                         scheme: str = None, verbose: bool = False) -> Tuple[bool, Dict[str, Any]]:
    """Run tests after removal and check for regressions.

    Args:
        repo_path: Path to iOS project
        category: Confidence category (determines test scope)
        scheme: Xcode scheme
        verbose: Print detailed output

    Returns:
        Tuple of (success, results dict)
    """
    repo_path = Path(repo_path)
    results = {
        "test_status": "unknown",
        "category": category,
        "scheme": scheme,
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "error_message": None,
    }

    try:
        # Build test command
        xcworkspaces = list(repo_path.glob("*.xcworkspace"))
        xcprojects = list(repo_path.glob("*.xcodeproj"))

        if xcworkspaces:
            cmd = ["xcodebuild", "test", "-workspace", str(xcworkspaces[0])]
        elif xcprojects:
            cmd = ["xcodebuild", "test", "-project", str(xcprojects[0])]
        elif (repo_path / "Package.swift").exists():
            cmd = ["swift", "test"]
        else:
            results["test_status"] = "skipped"
            results["error_message"] = "No test-capable build system"
            return True, results

        if scheme:
            cmd.extend(["-scheme", scheme])

        # For UNCERTAIN, run integration/UI tests too
        if category == "UNCERTAIN":
            cmd.extend(["-destination", "platform=iOS Simulator,name=iPhone 15"])

        if verbose:
            print(f"🧪 Running tests (category: {category})")

        # Longer timeout for tests
        timeout = 1800 if category == "UNCERTAIN" else 900

        result = subprocess.run(
            cmd, cwd=str(repo_path),
            capture_output=True, text=True, timeout=timeout,
        )

        if result.returncode == 0:
            results["test_status"] = "success"
            if verbose:
                print("✅ All tests passed")
            return True, results
        else:
            results["test_status"] = "failure"
            results["error_message"] = result.stderr[:500] if result.stderr else "Tests failed"
            if verbose:
                print(f"❌ Tests failed:\n{result.stderr[:200]}")
            return False, results

    except subprocess.TimeoutExpired:
        results["test_status"] = "timeout"
        results["error_message"] = f"Tests timed out (>{timeout}s)"
        return False, results
    except Exception as e:
        results["test_status"] = "error"
        results["error_message"] = str(e)
        return False, results


if __name__ == "__main__":
    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    category = sys.argv[2] if len(sys.argv) > 2 else "LIKELY"
    scheme = None
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    for i, arg in enumerate(sys.argv):
        if arg == "--scheme" and i + 1 < len(sys.argv):
            scheme = sys.argv[i + 1]

    success, results = validate_swift_tests(repo, category=category, scheme=scheme, verbose=verbose)

    if "--json" in sys.argv:
        print(json.dumps(results, indent=2))
    elif not verbose:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: Swift tests {results['test_status']}")

    sys.exit(0 if success else 1)
