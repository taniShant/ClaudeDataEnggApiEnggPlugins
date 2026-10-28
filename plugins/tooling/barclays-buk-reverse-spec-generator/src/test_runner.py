"""
test_runner.py — test execution and result mapping for the verification loop.

Detects the test framework, runs tests, parses results, and maps failures
back to spec behaviors by naming convention.

Naming convention for test-to-behavior mapping:
    Java  : test method "testGetMessages"       → behavior "get_messages"
            class name  "GetMessagesTest"        → behavior "get_messages"
    Python: function    "test_get_messages"      → behavior "get_messages"
    JS    : describe/it "get messages"           → behavior "get_messages"

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class TestResult:
    """Result for one test case."""

    test_name: str
    behavior_name: Optional[str]  # mapped spec behavior, or None
    status: str                   # "passing" | "failing" | "error"
    error_message: str = ""


@dataclass
class TestResults:
    """Aggregate results from one test run."""

    framework: str
    total: int = 0
    passing: int = 0
    failing: int = 0
    error: int = 0
    results: List[TestResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.failing == 0 and self.error == 0


# ---------------------------------------------------------------------------
# Framework detection
# ---------------------------------------------------------------------------

_FRAMEWORK_UNKNOWN = "unknown"
_FRAMEWORK_JUNIT5 = "junit5"
_FRAMEWORK_PYTEST = "pytest"
_FRAMEWORK_JEST = "jest"


def detect_framework(project_root) -> str:
    """
    Detect the test framework from project build files.

    Checks (in order):
    1. build.gradle / build.gradle.kts — junit-jupiter, testng
    2. pom.xml — junit-jupiter, junit5
    3. pyproject.toml / setup.py / requirements*.txt — pytest
    4. package.json — jest, vitest, mocha

    Returns one of: "junit5", "pytest", "jest", "unknown"
    """
    root = Path(project_root)

    # Gradle (most common in Barclays stack)
    for gradle_file in ("build.gradle", "build.gradle.kts"):
        gradle_path = root / gradle_file
        if gradle_path.exists():
            content = gradle_path.read_text(encoding="utf-8", errors="replace").lower()
            if "junit-jupiter" in content or "junit5" in content or "junit.jupiter" in content:
                return _FRAMEWORK_JUNIT5

    # Maven
    pom = root / "pom.xml"
    if pom.exists():
        content = pom.read_text(encoding="utf-8", errors="replace").lower()
        if "junit-jupiter" in content or "junit5" in content:
            return _FRAMEWORK_JUNIT5

    # Python
    for py_file in ("pyproject.toml", "setup.py", "setup.cfg"):
        py_path = root / py_file
        if py_path.exists():
            content = py_path.read_text(encoding="utf-8", errors="replace").lower()
            if "pytest" in content:
                return _FRAMEWORK_PYTEST

    for req_file in root.glob("requirements*.txt"):
        content = req_file.read_text(encoding="utf-8", errors="replace").lower()
        if "pytest" in content:
            return _FRAMEWORK_PYTEST

    # JavaScript / Node
    pkg = root / "package.json"
    if pkg.exists():
        content = pkg.read_text(encoding="utf-8", errors="replace").lower()
        if '"jest"' in content or "'jest'" in content:
            return _FRAMEWORK_JEST
        if '"vitest"' in content:
            return _FRAMEWORK_JEST  # treat vitest as jest-compatible

    return _FRAMEWORK_UNKNOWN


# ---------------------------------------------------------------------------
# Test execution
# ---------------------------------------------------------------------------


def run_tests(project_root, framework: Optional[str] = None, spec=None) -> TestResults:
    """
    Run the test suite and return results.

    Parameters
    ----------
    project_root : path to project root
    framework    : override framework detection (optional)
    spec         : parsed spec dict for behavior mapping (optional)
    """
    root = Path(project_root)
    if framework is None:
        framework = detect_framework(root)

    if framework == _FRAMEWORK_JUNIT5:
        return _run_junit5(root, spec)
    elif framework == _FRAMEWORK_PYTEST:
        return _run_pytest(root, spec)
    elif framework == _FRAMEWORK_JEST:
        return _run_jest(root, spec)
    else:
        return TestResults(framework="unknown", total=0)


def _run_junit5(root: Path, spec) -> TestResults:
    """Run Gradle test task and parse XML Surefire/Gradle reports."""
    gradle_cmd = "./gradlew" if (root / "gradlew").exists() else "gradle"
    cmd = [gradle_cmd, "test", "--continue", "--no-daemon"]
    _run_subprocess(cmd, cwd=root)

    # Find XML report files
    xml_dirs = list(root.rglob("TEST-*.xml")) + list(root.rglob("test-results/**/*.xml"))
    if not xml_dirs:
        # Try build/test-results
        xml_dirs = list(root.glob("**/build/test-results/**/*.xml"))

    all_results: List[TestResult] = []
    for xml_file in xml_dirs:
        all_results.extend(_parse_junit_xml(xml_file, spec))

    return _aggregate(all_results, _FRAMEWORK_JUNIT5)


def _run_pytest(root: Path, spec) -> TestResults:
    """Run pytest with JUnit XML output (built-in, no plugins required) and parse results."""
    xml_output = root / ".pytest_results.xml"
    cmd = [
        sys.executable, "-m", "pytest",
        "--tb=no", "-q",
        f"--junit-xml={xml_output}",
    ]
    _run_subprocess(cmd, cwd=root)

    results: List[TestResult] = []
    if xml_output.exists():
        results = _parse_junit_xml(xml_output, spec)
        xml_output.unlink(missing_ok=True)

    return _aggregate(results, _FRAMEWORK_PYTEST)


def _run_jest(root: Path, spec) -> TestResults:
    """Run Jest with JSON output and parse results."""
    json_output = root / ".jest_results.json"
    cmd = ["npx", "jest", "--json", f"--outputFile={json_output}", "--no-coverage"]
    _run_subprocess(cmd, cwd=root)

    results: List[TestResult] = []
    if json_output.exists():
        results = _parse_jest_json(json_output.read_text(encoding="utf-8"), spec)
        json_output.unlink(missing_ok=True)

    return _aggregate(results, _FRAMEWORK_JEST)


def _run_subprocess(cmd: list, cwd: Path) -> None:
    """Run a subprocess, ignoring non-zero exit (tests may fail)."""
    try:
        subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            timeout=300,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass


# ---------------------------------------------------------------------------
# XML / JSON parsers
# ---------------------------------------------------------------------------


def _parse_junit_xml(xml_path: Path, spec) -> List[TestResult]:
    """Parse a JUnit XML report file (Surefire/Gradle format)."""
    results: List[TestResult] = []
    try:
        tree = ET.parse(str(xml_path))
        root = tree.getroot()
        # Handle both <testsuite> and <testsuites> roots
        if root.tag == "testsuites":
            suites = root.findall("testsuite")
        elif root.tag == "testsuite":
            suites = [root]
        else:
            return results

        for suite in suites:
            for tc in suite.findall("testcase"):
                name = tc.get("name", "")
                failure = tc.find("failure")
                error = tc.find("error")
                skipped = tc.find("skipped")
                if skipped is not None:
                    continue
                if failure is not None:
                    status = "failing"
                    msg = (failure.get("message") or "")[:200]
                elif error is not None:
                    status = "error"
                    msg = (error.get("message") or "")[:200]
                else:
                    status = "passing"
                    msg = ""
                behavior = map_test_to_behavior(name, spec)
                results.append(TestResult(
                    test_name=name,
                    behavior_name=behavior,
                    status=status,
                    error_message=msg,
                ))
    except ET.ParseError:
        pass
    return results



def _parse_jest_json(json_text: str, spec) -> List[TestResult]:
    """Parse Jest --json output."""
    import json as _json
    results: List[TestResult] = []
    try:
        data = _json.loads(json_text)
        for suite in data.get("testResults", []):
            for test in suite.get("testResults", []):
                name = test.get("fullName", test.get("title", ""))
                status_raw = test.get("status", "")
                status = "passing" if status_raw == "passed" else (
                    "failing" if status_raw == "failed" else "error"
                )
                msg = " ".join(test.get("failureMessages", []))[:200]
                behavior = map_test_to_behavior(name, spec)
                results.append(TestResult(
                    test_name=name,
                    behavior_name=behavior,
                    status=status,
                    error_message=msg,
                ))
    except (ValueError, KeyError):
        pass
    return results


# ---------------------------------------------------------------------------
# Test-to-behavior name mapping
# ---------------------------------------------------------------------------


def map_test_to_behavior(test_name: str, spec) -> Optional[str]:
    """
    Map a test name to a spec behavior name.

    Strategy:
    1. Normalise test name to snake_case
    2. Strip common prefixes/suffixes (test_, Test, _test, Test_)
    3. Look for an exact or substring match in spec behaviors

    Returns the matched behavior name, or None if no match found.
    """
    if not test_name or spec is None:
        return None

    behavior_names = [b.get("name", "") for b in spec.get("behaviors", [])]
    if not behavior_names:
        return None

    normalised = _normalise_test_name(test_name)

    # 1. Exact match
    if normalised in behavior_names:
        return normalised

    # 2. Substring: spec behavior is contained in the test name
    for bname in behavior_names:
        if bname in normalised:
            return bname

    # 3. Prefix match (test covers a prefix of the behavior name)
    for bname in behavior_names:
        bparts = set(bname.split("_"))
        nparts = set(normalised.split("_"))
        if len(bparts & nparts) >= max(1, len(bparts) - 1):
            return bname

    return None


def _normalise_test_name(raw: str) -> str:
    """
    Convert a test method/function name to snake_case for matching.

    Examples:
        "testGetMessages"           → "get_messages"
        "test_get_messages"         → "get_messages"
        "GetMessagesTest"           → "get_messages"
        "should get messages"       → "get_messages"
        "com.foo.MessagingTest#testDeleteEventLog" → "delete_event_log"
    """
    # Strip package/class prefix (Java fully-qualified)
    if "#" in raw:
        raw = raw.split("#")[-1]
    if "." in raw:
        raw = raw.split(".")[-1]
    # Strip path prefix (pytest nodeid: path/test_foo.py::test_bar)
    if "::" in raw:
        raw = raw.split("::")[-1]

    # camelCase → snake_case
    raw = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", raw)
    raw = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", raw)
    raw = raw.lower()

    # Remove common prefixes/suffixes
    for prefix in ("test_", "test", "should_", "should", "check_", "verify_", "given_", "when_", "then_"):
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
            break
    for suffix in ("_test", "_tests", "_spec", "_should", "_check"):
        if raw.endswith(suffix):
            raw = raw[:-len(suffix)]
            break

    # Replace spaces and hyphens with underscores
    raw = re.sub(r"[\s\-]+", "_", raw)
    # Remove non-identifier characters
    raw = re.sub(r"[^a-z0-9_]", "", raw)
    # Collapse multiple underscores
    raw = re.sub(r"_+", "_", raw).strip("_")
    return raw


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _aggregate(results: List[TestResult], framework: str) -> TestResults:
    total = len(results)
    passing = sum(1 for r in results if r.status == "passing")
    failing = sum(1 for r in results if r.status == "failing")
    error = sum(1 for r in results if r.status == "error")
    return TestResults(
        framework=framework,
        total=total,
        passing=passing,
        failing=failing,
        error=error,
        results=results,
    )
