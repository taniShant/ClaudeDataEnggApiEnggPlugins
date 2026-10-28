#!/usr/bin/env python3
"""Post-removal test validation hook.

Executes test suite after dead code removal and validates results.
Used as mandatory gate before committing removal task.
"""

import subprocess
import sys
import json
from pathlib import Path
from typing import Tuple, Dict, Any
import xml.etree.ElementTree as ET

def run_tests(repo_path: str = ".") -> Tuple[int, str]:
    """
    Run test suite (Gradle or Maven).

    Returns:
        Tuple of (exit_code, build_system)
    """
    repo_path = Path(repo_path)

    # Try Gradle first
    gradle_wrapper = repo_path / "gradlew"
    if gradle_wrapper.exists() or (repo_path / "build.gradle").exists():
        result = subprocess.run(
            ["./gradlew", "test", "--no-build-cache"],
            cwd=repo_path,
            capture_output=True,
            timeout=900,
            text=True
        )
        return result.returncode, "gradle"

    # Try Maven fallback
    pom = repo_path / "pom.xml"
    if pom.exists():
        result = subprocess.run(
            ["mvn", "test", "-q"],
            cwd=repo_path,
            capture_output=True,
            timeout=900,
            text=True
        )
        return result.returncode, "maven"

    return 1, "unknown"

def parse_test_results(repo_path: str = ".") -> Dict[str, Any]:
    """
    Parse test results from JUnit XML files.

    Returns:
        Dictionary with test statistics
    """
    repo_path = Path(repo_path)
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "test_files": 0,
    }

    # Gradle location: build/test-results/test/*.xml
    # Maven location: target/surefire-reports/*.xml
    test_xml_paths = [
        repo_path / "build" / "test-results" / "test",
        repo_path / "target" / "surefire-reports",
    ]

    for test_dir in test_xml_paths:
        if not test_dir.exists():
            continue

        for xml_file in test_dir.glob("*.xml"):
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()

                if root.tag == "testsuite":
                    results["test_files"] += 1
                    tests = int(root.get("tests", 0))
                    failures = int(root.get("failures", 0))
                    errors = int(root.get("errors", 0))
                    skipped = int(root.get("skipped", 0))

                    results["total"] += tests
                    results["failed"] += failures
                    results["errors"] += errors
                    results["skipped"] += skipped
                    results["passed"] += tests - failures - errors - skipped

            except Exception as e:
                # Skip malformed XML files
                pass

    return results

def validate_tests(repo_path: str = ".", verbose: bool = False) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate that all tests pass after removal.

    Args:
        repo_path: Path to repository
        verbose: Print detailed output

    Returns:
        Tuple of (success: bool, results: dict with details)
    """
    repo_path_obj = Path(repo_path)
    results = {
        "test_status": "unknown",
        "build_system": None,
        "test_results": None,
        "error_message": None,
    }

    try:
        if verbose:
            print("🧪 Running test suite...")

        exit_code, build_system = run_tests(repo_path)
        results["build_system"] = build_system

        if build_system == "unknown":
            results["test_status"] = "skipped"
            results["error_message"] = "No build system detected"
            if verbose:
                print("⚠️ No build system found; skipping test validation")
            return True, results

        if exit_code != 0:
            results["test_status"] = "failure"
            results["error_message"] = f"{build_system} test suite failed"
            if verbose:
                print(f"❌ Test suite failed with exit code {exit_code}")
            test_results = parse_test_results(repo_path)
            results["test_results"] = test_results
            return False, results

        # Parse results
        test_results = parse_test_results(repo_path)
        results["test_results"] = test_results
        results["test_status"] = "success"

        if verbose:
            print(f"✅ All tests passed ({test_results['total']} tests)")

        return True, results

    except subprocess.TimeoutExpired:
        results["test_status"] = "timeout"
        results["error_message"] = "Test suite timed out (>15min)"
        if verbose:
            print("⏱️ Test validation timed out")
        return False, results
    except Exception as e:
        results["test_status"] = "error"
        results["error_message"] = str(e)
        if verbose:
            print(f"💥 Unexpected error: {e}")
        return False, results

if __name__ == "__main__":
    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    json_output = "--json" in sys.argv

    success, results = validate_tests(repo, verbose=verbose)

    if json_output:
        print(json.dumps(results, indent=2))
    elif not verbose:
        status = "✅ PASS" if success else "❌ FAIL"
        if results["test_results"]:
            tr = results["test_results"]
            print(f"{status}: {tr['passed']}/{tr['total']} tests passed")
        else:
            print(f"{status}: Test validation {results['test_status']}")

    sys.exit(0 if success else 1)
