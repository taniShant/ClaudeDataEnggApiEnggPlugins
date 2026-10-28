#!/usr/bin/env python3
"""Post-removal validation: comprehensive testing and regression detection."""

import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Tuple
import xml.etree.ElementTree as ET
from datetime import datetime

def validate_removal(repo_path: str = ".", compare_baseline: str = None, verbose: bool = False) -> Dict[str, Any]:
    """
    Comprehensive validation after dead code removal.

    Args:
        repo_path: Repository path
        compare_baseline: Path to baseline results for regression detection
        verbose: Print detailed output

    Returns:
        Validation report with test results, compilation status, and regression analysis
    """
    repo_path = Path(repo_path)
    report = {
        "timestamp": datetime.now().isoformat(),
        "repo_path": str(repo_path),
        "compilation": None,
        "unit_tests": None,
        "integration_tests": None,
        "regression_detected": False,
        "validation_status": "unknown",
        "metrics": {},
    }

    # Step 1: Compilation check
    if verbose:
        print("🔨 Checking compilation...")
    compile_result = _check_compilation(repo_path, verbose)
    report["compilation"] = compile_result

    if not compile_result["success"]:
        report["validation_status"] = "failed"
        if verbose:
            print(f"❌ Compilation failed: {compile_result['error']}")
        return report

    # Step 2: Unit tests
    if verbose:
        print("🧪 Running unit tests...")
    unit_test_result = _run_unit_tests(repo_path, verbose)
    report["unit_tests"] = unit_test_result

    if not unit_test_result["success"]:
        report["validation_status"] = "failed"
        if verbose:
            print(f"❌ Unit tests failed: {unit_test_result['passed']}/{unit_test_result['total']} passed")
        return report

    # Step 3: Regression detection
    if compare_baseline:
        if verbose:
            print("📊 Comparing against baseline...")
        regression = _detect_regressions(unit_test_result, compare_baseline, verbose)
        report["regression_detected"] = regression["detected"]
        report["regression_analysis"] = regression

        if regression["detected"]:
            report["validation_status"] = "regression"
            if verbose:
                print(f"⚠️ Regression detected: {regression['new_failures']} new failures")
            return report

    # Step 4: Calculate metrics
    if verbose:
        print("📈 Calculating metrics...")
    report["metrics"] = _calculate_metrics(unit_test_result)
    report["validation_status"] = "passed"

    if verbose:
        print(f"✅ Validation passed: {unit_test_result['passed']}/{unit_test_result['total']} tests")

    return report

def _check_compilation(repo_path: Path, verbose: bool) -> Dict[str, Any]:
    """Check compilation with Gradle or Maven."""
    result = {
        "success": False,
        "build_system": None,
        "error": None,
    }

    try:
        # Try Gradle
        if (repo_path / "gradlew").exists():
            result["build_system"] = "gradle"
            proc = subprocess.run(
                ["./gradlew", "clean", "build", "-x", "test"],
                cwd=repo_path,
                capture_output=True,
                timeout=600
            )
            result["success"] = proc.returncode == 0
            if not result["success"]:
                result["error"] = "Gradle build failed"
            return result

        # Try Maven
        if (repo_path / "pom.xml").exists():
            result["build_system"] = "maven"
            proc = subprocess.run(
                ["mvn", "clean", "package", "-DskipTests", "-q"],
                cwd=repo_path,
                capture_output=True,
                timeout=600
            )
            result["success"] = proc.returncode == 0
            if not result["success"]:
                result["error"] = "Maven build failed"
            return result

        result["success"] = True  # No build system = skip
        result["error"] = "No build system detected"

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)

    return result

def _run_unit_tests(repo_path: Path, verbose: bool) -> Dict[str, Any]:
    """Run unit tests and parse results."""
    result = {
        "success": False,
        "total": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
    }

    try:
        # Run tests
        if (repo_path / "gradlew").exists():
            proc = subprocess.run(
                ["./gradlew", "test", "--no-build-cache"],
                cwd=repo_path,
                capture_output=True,
                timeout=900
            )
        elif (repo_path / "pom.xml").exists():
            proc = subprocess.run(
                ["mvn", "test", "-q"],
                cwd=repo_path,
                capture_output=True,
                timeout=900
            )
        else:
            result["success"] = True  # No tests to run
            return result

        # Parse test results
        test_results = _parse_test_results(repo_path)
        result.update(test_results)
        result["success"] = proc.returncode == 0

    except Exception as e:
        result["success"] = False

    return result

def _parse_test_results(repo_path: Path) -> Dict[str, int]:
    """Parse JUnit XML test results."""
    results = {"total": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0}

    test_dirs = [
        repo_path / "build" / "test-results" / "test",
        repo_path / "target" / "surefire-reports",
    ]

    for test_dir in test_dirs:
        if not test_dir.exists():
            continue

        for xml_file in test_dir.glob("*.xml"):
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()

                if root.tag == "testsuite":
                    tests = int(root.get("tests", 0))
                    failures = int(root.get("failures", 0))
                    errors = int(root.get("errors", 0))
                    skipped = int(root.get("skipped", 0))

                    results["total"] += tests
                    results["failed"] += failures
                    results["errors"] += errors
                    results["skipped"] += skipped
                    results["passed"] += tests - failures - errors - skipped

            except Exception:
                pass

    return results

def _detect_regressions(current: Dict, baseline_path: str, verbose: bool) -> Dict[str, Any]:
    """Detect regressions by comparing against baseline."""
    result = {
        "detected": False,
        "baseline_path": baseline_path,
        "new_failures": 0,
        "fixed_issues": 0,
    }

    try:
        with open(baseline_path) as f:
            baseline = json.load(f)

        # Check if any tests that were passing now fail
        if current["failed"] > baseline.get("failed", 0):
            result["detected"] = True
            result["new_failures"] = current["failed"] - baseline.get("failed", 0)

        # Check for fixed tests
        if current["passed"] > baseline.get("passed", 0):
            result["fixed_issues"] = current["passed"] - baseline.get("passed", 0)

    except Exception:
        # Baseline not found or invalid; skip regression detection
        pass

    return result

def _calculate_metrics(test_result: Dict) -> Dict[str, Any]:
    """Calculate confidence metrics."""
    total = test_result["total"]
    passed = test_result["passed"]
    failed = test_result["failed"]

    accuracy = (passed / total * 100) if total > 0 else 0

    return {
        "accuracy_percent": round(accuracy, 2),
        "pass_rate": round(passed / total, 3) if total > 0 else 0,
        "failure_rate": round(failed / total, 3) if total > 0 else 0,
        "test_count": total,
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Validate dead code removal")
    parser.add_argument("--repo", default=".", help="Repository path")
    parser.add_argument("--baseline", help="Baseline results for regression detection")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()
    result = validate_removal(args.repo, args.baseline, args.verbose)
    print(json.dumps(result, indent=2))
