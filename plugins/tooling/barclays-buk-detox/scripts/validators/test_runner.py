#!/usr/bin/env python3
"""Detect test framework, run tests, and parse results.

Input (JSON stdin):
    {
        "repo_dir": "/path/to/repo",
        "target_file": "/path/to/modified_file.py",  (optional)
        "timeout_seconds": 300,
        "run_full_suite": false
    }

Output (JSON stdout):
    {"status": "success", "test_framework": {...}, "results": {...}, ...}
"""

from __future__ import annotations

import json
import re
import shlex
import sys
import time
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output, run_cmd, log, progress, progress_done
from scripts.core.errors import error_exit


def detect_python_framework(repo_dir: Path) -> dict | None:
    """Detect Python test framework."""
    # pytest indicators
    for f in ("conftest.py", "pytest.ini", "setup.cfg"):
        if (repo_dir / f).exists():
            return {"name": "pytest", "language": "Python", "command": "python -m pytest"}
    pyproject = repo_dir / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text()
        if "[tool.pytest" in content:
            return {"name": "pytest", "language": "Python", "command": "python -m pytest"}
    # tox
    if (repo_dir / "tox.ini").exists():
        return {"name": "tox", "language": "Python", "command": "python -m pytest"}
    # Look for test directories
    if list(repo_dir.glob("tests/test_*.py")) or list(repo_dir.glob("test_*.py")):
        return {"name": "pytest", "language": "Python", "command": "python -m pytest"}
    return None


def detect_js_framework(repo_dir: Path) -> dict | None:
    """Detect JavaScript/TypeScript test framework."""
    pkg_path = repo_dir / "package.json"
    if not pkg_path.exists():
        return None
    try:
        with open(pkg_path) as f:
            pkg = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    dev_deps = pkg.get("devDependencies", {})
    scripts = pkg.get("scripts", {})
    test_script = scripts.get("test", "")

    # Vitest
    if "vitest" in dev_deps or list(repo_dir.glob("vitest.config.*")):
        return {"name": "vitest", "language": "TypeScript", "command": "npx vitest run"}
    # Jest
    if "jest" in dev_deps or list(repo_dir.glob("jest.config.*")) or "jest" in test_script:
        return {"name": "jest", "language": "JavaScript", "command": "npx jest"}
    # Mocha
    if "mocha" in dev_deps or list(repo_dir.glob(".mocharc.*")) or "mocha" in test_script:
        return {"name": "mocha", "language": "JavaScript", "command": "npx mocha"}
    # Generic npm test
    if "test" in scripts:
        return {"name": "npm-test", "language": "JavaScript", "command": "npm test"}
    return None


def detect_java_framework(repo_dir: Path) -> dict | None:
    """Detect Java/Kotlin test framework."""
    if (repo_dir / "build.gradle").exists() or (repo_dir / "build.gradle.kts").exists():
        wrapper = "./gradlew" if (repo_dir / "gradlew").exists() else "gradle"
        return {"name": "gradle", "language": "Java", "command": f"{wrapper} test"}
    if (repo_dir / "pom.xml").exists():
        wrapper = "./mvnw" if (repo_dir / "mvnw").exists() else "mvn"
        return {"name": "maven", "language": "Java", "command": f"{wrapper} test"}
    return None


def detect_go_framework(repo_dir: Path) -> dict | None:
    """Detect Go test framework."""
    if (repo_dir / "go.mod").exists():
        return {"name": "go-test", "language": "Go", "command": "go test ./..."}
    return None


def detect_dotnet_framework(repo_dir: Path) -> dict | None:
    """Detect .NET test framework."""
    if list(repo_dir.glob("*.csproj")) or list(repo_dir.glob("*.sln")):
        return {"name": "dotnet-test", "language": "C#", "command": "dotnet test"}
    return None


def detect_rust_framework(repo_dir: Path) -> dict | None:
    """Detect Rust test framework."""
    if (repo_dir / "Cargo.toml").exists():
        return {"name": "cargo-test", "language": "Rust", "command": "cargo test"}
    return None


def detect_framework(repo_dir: Path) -> dict | None:
    """Detect test framework by probing for config files."""
    detectors = [
        detect_python_framework,
        detect_js_framework,
        detect_java_framework,
        detect_go_framework,
        detect_dotnet_framework,
        detect_rust_framework,
    ]
    for detector in detectors:
        result = detector(repo_dir)
        if result:
            result["detection_confidence"] = "high"
            return result
    return None


def derive_test_path(target_file: str, repo_dir: Path, framework: dict) -> str | None:
    """Derive test file path from source file path using naming conventions."""
    target = Path(target_file)
    lang = framework.get("language", "")
    stem = target.stem
    suffix = target.suffix

    candidates = []

    if lang == "Python":
        candidates = [
            repo_dir / "tests" / f"test_{stem}.py",
            repo_dir / "tests" / target.parent.name / f"test_{stem}.py",
            repo_dir / f"test_{stem}.py",
        ]
    elif lang in ("JavaScript", "TypeScript"):
        ext = ".ts" if suffix in (".ts", ".tsx") else ".js"
        candidates = [
            repo_dir / "__tests__" / f"{stem}.test{ext}",
            target.parent / f"{stem}.test{ext}",
            target.parent / f"{stem}.spec{ext}",
            repo_dir / "test" / f"{stem}.test{ext}",
        ]
    elif lang == "Java":
        # src/main/java/... -> src/test/java/...Test.java
        rel = str(target.relative_to(repo_dir)) if target.is_relative_to(repo_dir) else str(target)
        test_path = rel.replace("src/main/", "src/test/").replace(f"{stem}.java", f"{stem}Test.java")
        candidates = [repo_dir / test_path]
    elif lang == "Go":
        candidates = [target.parent / f"{stem}_test.go"]
    elif lang == "C#":
        candidates = [
            repo_dir / "test" / f"{stem}Tests.cs",
            repo_dir / "tests" / f"{stem}Test.cs",
        ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


# Framework-specific verbose/output flags (DRY: used by both targeted and full-suite commands)
FRAMEWORK_VERBOSE_FLAGS = {
    "pytest": "-v --tb=short --no-header -q",
    "jest": "--verbose --no-coverage",
    "vitest": "--reporter=verbose",
    "go-test": "-v",
}


def build_targeted_command(base_cmd: str, test_path: str, framework: dict) -> str:
    """Build a targeted test command for a specific test file."""
    name = framework.get("name", "")
    flags = FRAMEWORK_VERBOSE_FLAGS.get(name, "")
    if name == "go-test":
        # Go: run tests in the package containing the test file
        pkg_dir = str(Path(test_path).parent)
        return f"go test {pkg_dir} {flags}".strip()
    return f"{base_cmd} {test_path} {flags}".strip() if flags else f"{base_cmd} {test_path}"


def parse_pytest_output(output: str) -> dict:
    """Parse pytest summary output."""
    results = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errored": 0}
    # Look for summary line like "5 passed, 2 failed, 1 skipped"
    m = re.search(r"(\d+) passed", output)
    if m:
        results["passed"] = int(m.group(1))
    m = re.search(r"(\d+) failed", output)
    if m:
        results["failed"] = int(m.group(1))
    m = re.search(r"(\d+) error", output)
    if m:
        results["errored"] = int(m.group(1))
    m = re.search(r"(\d+) skipped", output)
    if m:
        results["skipped"] = int(m.group(1))
    results["total"] = results["passed"] + results["failed"] + results["errored"] + results["skipped"]
    return results


def parse_jest_output(output: str) -> dict:
    """Parse Jest summary output."""
    results = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errored": 0}
    m = re.search(r"Tests:\s+(\d+) passed", output)
    if m:
        results["passed"] = int(m.group(1))
    m = re.search(r"Tests:\s+(\d+) failed", output)
    if m:
        results["failed"] = int(m.group(1))
    m = re.search(r"Tests:\s+\d+ \w+,\s+(\d+) total", output)
    if m:
        results["total"] = int(m.group(1))
    if results["total"] == 0:
        results["total"] = results["passed"] + results["failed"]
    return results


def parse_go_output(output: str) -> dict:
    """Parse go test output."""
    results = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errored": 0}
    results["passed"] = len(re.findall(r"--- PASS:", output))
    results["failed"] = len(re.findall(r"--- FAIL:", output))
    results["skipped"] = len(re.findall(r"--- SKIP:", output))
    results["total"] = results["passed"] + results["failed"] + results["skipped"]
    return results


def parse_maven_output(output: str) -> dict:
    """Parse Maven/Gradle test output."""
    results = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errored": 0}
    m = re.search(r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)", output)
    if m:
        results["total"] = int(m.group(1))
        results["failed"] = int(m.group(2))
        results["errored"] = int(m.group(3))
        results["skipped"] = int(m.group(4))
        results["passed"] = results["total"] - results["failed"] - results["errored"] - results["skipped"]
    return results


def parse_results(output: str, framework_name: str, exit_code: int) -> dict:
    """Parse test results based on framework."""
    parsers = {
        "pytest": parse_pytest_output,
        "jest": parse_jest_output,
        "vitest": parse_jest_output,  # Similar format
        "go-test": parse_go_output,
        "maven": parse_maven_output,
        "gradle": parse_maven_output,
    }

    parser = parsers.get(framework_name)
    if parser:
        results = parser(output)
    else:
        # Fallback: use exit code
        results = {"total": None, "passed": None, "failed": None, "skipped": None, "errored": None}

    results["exit_code"] = exit_code
    results["overall"] = "PASS" if exit_code == 0 else "FAIL"
    return results


def extract_failures(output: str, framework_name: str) -> list[dict]:
    """Extract failure details from test output."""
    failures = []
    if framework_name == "pytest":
        # Look for FAILED lines
        for m in re.finditer(r"FAILED\s+([\w/\.]+)::(\w+)", output):
            failures.append({
                "file": m.group(1),
                "test_name": m.group(2),
                "message": "",
            })
    elif framework_name in ("jest", "vitest"):
        for m in re.finditer(r"●\s+(.+)", output):
            failures.append({"test_name": m.group(1), "message": ""})
    return failures[:20]  # Limit to 20


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    repo_dir = input_data.get("repo_dir", "")
    target_file = input_data.get("target_file")
    timeout = input_data.get("timeout_seconds", 300)
    run_full_suite = input_data.get("run_full_suite", False)

    if not repo_dir:
        error_exit("repo_dir is required", "input_validation")

    repo_path = Path(repo_dir)
    if not repo_path.is_dir():
        write_json_output({
            "status": "error",
            "error": f"Repository directory not found: {repo_dir}",
            "repo_dir": repo_dir,
            "test_framework": None,
            "results": None,
        }, start_time=start_time)
        return

    # Detect framework
    progress("Detecting test framework...")
    framework = detect_framework(repo_path)
    if framework is None:
        write_json_output({
            "status": "error",
            "error": "No test framework detected. The repository may not have tests.",
            "repo_dir": repo_dir,
            "test_framework": None,
            "results": None,
        }, start_time=start_time)
        return

    # Determine test command
    base_cmd = framework["command"]
    targeted = False
    target_test_file = None
    warnings = []

    if target_file and not run_full_suite:
        test_path = derive_test_path(target_file, repo_path, framework)
        if test_path:
            cmd = build_targeted_command(base_cmd, test_path, framework)
            targeted = True
            target_test_file = test_path
        else:
            flags = FRAMEWORK_VERBOSE_FLAGS.get(framework["name"], "")
            cmd = f"{base_cmd} {flags}".strip() if flags else base_cmd
            warnings.append(f"Could not find targeted test for {target_file}. Running full suite.")
    else:
        flags = FRAMEWORK_VERBOSE_FLAGS.get(framework["name"], "")
        cmd = f"{base_cmd} {flags}".strip() if flags else base_cmd

    # Check prerequisites
    if framework["language"] == "JavaScript" and not (repo_path / "node_modules").is_dir():
        warnings.append("node_modules not found. Tests may fail due to missing dependencies.")

    # Run tests (list-form: injection-safe, no shell interpretation)
    cmd_parts = shlex.split(cmd)
    progress(f"Running tests — {framework['name']} ({cmd})...")
    log(f"Running tests: {cmd}")
    result = run_cmd(cmd_parts, cwd=repo_path, timeout=timeout)
    full_output = result["stdout"] + result["stderr"]

    # Parse results
    results = parse_results(full_output, framework["name"], result["exit_code"])

    # Extract failures
    failures = []
    if result["exit_code"] != 0:
        failures = extract_failures(full_output, framework["name"])

    # Truncate output
    output_lines = full_output.splitlines()
    raw_tail = "\n".join(output_lines[-50:])

    if result["exit_code"] == -1 and "timed out" in result["stderr"]:
        results["overall"] = "ERROR"
        warnings.append(f"Test suite timed out after {timeout} seconds.")

    framework["command_executed"] = cmd
    progress_done(f"Tests {results['overall']} — {results.get('passed', '?')} passed, {results.get('failed', '?')} failed")

    write_json_output({
        "status": "success",
        "repo_dir": repo_dir,
        "test_framework": framework,
        "targeted": targeted,
        "target_test_file": target_test_file,
        "results": results,
        "failures": failures,
        "warnings": warnings,
        "raw_output_tail": raw_tail,
    }, start_time=start_time)


if __name__ == "__main__":
    main()
