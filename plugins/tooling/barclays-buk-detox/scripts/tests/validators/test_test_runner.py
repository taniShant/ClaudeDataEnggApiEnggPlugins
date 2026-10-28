"""Tests for test_runner.py."""

import json
import sys
import tempfile
from pathlib import Path
from unittest import TestCase, main

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.validators.test_runner import (
    detect_python_framework,
    detect_js_framework,
    detect_java_framework,
    detect_go_framework,
    detect_dotnet_framework,
    detect_rust_framework,
    detect_framework,
    derive_test_path,
    build_targeted_command,
    parse_pytest_output,
    parse_jest_output,
    parse_go_output,
    parse_maven_output,
    parse_results,
    extract_failures,
    FRAMEWORK_VERBOSE_FLAGS,
)


class TestDetectPythonFramework(TestCase):
    def test_conftest(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "conftest.py").touch()
            result = detect_python_framework(Path(tmp))
            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "pytest")

    def test_pytest_ini(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "pytest.ini").touch()
            result = detect_python_framework(Path(tmp))
            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "pytest")

    def test_pyproject_with_pytest(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "pyproject.toml").write_text("[tool.pytest.ini_options]\nminversion = '6.0'")
            result = detect_python_framework(Path(tmp))
            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "pytest")

    def test_tox(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "tox.ini").touch()
            result = detect_python_framework(Path(tmp))
            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "tox")

    def test_test_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = Path(tmp) / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_main.py").touch()
            result = detect_python_framework(Path(tmp))
            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "pytest")

    def test_no_python_tests(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = detect_python_framework(Path(tmp))
            self.assertIsNone(result)


class TestDetectJsFramework(TestCase):
    def test_vitest(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "package.json"
            pkg.write_text(json.dumps({"devDependencies": {"vitest": "^1.0.0"}}))
            result = detect_js_framework(Path(tmp))
            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "vitest")

    def test_jest(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "package.json"
            pkg.write_text(json.dumps({"devDependencies": {"jest": "^29.0.0"}}))
            result = detect_js_framework(Path(tmp))
            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "jest")

    def test_mocha(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "package.json"
            pkg.write_text(json.dumps({"devDependencies": {"mocha": "^10.0.0"}}))
            result = detect_js_framework(Path(tmp))
            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "mocha")

    def test_npm_test_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "package.json"
            pkg.write_text(json.dumps({"scripts": {"test": "tap"}}))
            result = detect_js_framework(Path(tmp))
            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "npm-test")

    def test_no_package_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = detect_js_framework(Path(tmp))
            self.assertIsNone(result)


class TestDetectJavaFramework(TestCase):
    def test_gradle_with_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "build.gradle").touch()
            (Path(tmp) / "gradlew").touch()
            result = detect_java_framework(Path(tmp))
            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "gradle")
            self.assertIn("./gradlew", result["command"])

    def test_maven(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "pom.xml").touch()
            result = detect_java_framework(Path(tmp))
            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "maven")


class TestDetectGoFramework(TestCase):
    def test_go_mod(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "go.mod").touch()
            result = detect_go_framework(Path(tmp))
            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "go-test")


class TestDetectDotnetFramework(TestCase):
    def test_csproj(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "MyApp.csproj").touch()
            result = detect_dotnet_framework(Path(tmp))
            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "dotnet-test")


class TestDetectRustFramework(TestCase):
    def test_cargo(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Cargo.toml").touch()
            result = detect_rust_framework(Path(tmp))
            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "cargo-test")


class TestDeriveTestPath(TestCase):
    def test_python_test_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            tests_dir = repo / "tests"
            tests_dir.mkdir()
            test_file = tests_dir / "test_user_repo.py"
            test_file.touch()
            framework = {"name": "pytest", "language": "Python"}
            result = derive_test_path(str(repo / "user_repo.py"), repo, framework)
            self.assertEqual(result, str(test_file))

    def test_js_test_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            src = repo / "src"
            src.mkdir()
            test_file = src / "utils.test.js"
            test_file.touch()
            framework = {"name": "jest", "language": "JavaScript"}
            result = derive_test_path(str(src / "utils.js"), repo, framework)
            self.assertEqual(result, str(test_file))

    def test_no_test_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            framework = {"name": "pytest", "language": "Python"}
            result = derive_test_path(str(repo / "main.py"), repo, framework)
            self.assertIsNone(result)


class TestBuildTargetedCommand(TestCase):
    def test_pytest(self):
        cmd = build_targeted_command("python -m pytest", "tests/test_main.py", {"name": "pytest"})
        self.assertIn("tests/test_main.py", cmd)
        self.assertIn("-v", cmd)

    def test_jest(self):
        cmd = build_targeted_command("npx jest", "src/main.test.js", {"name": "jest"})
        self.assertIn("src/main.test.js", cmd)
        self.assertIn("--verbose", cmd)

    def test_vitest(self):
        cmd = build_targeted_command("npx vitest run", "src/main.test.ts", {"name": "vitest"})
        self.assertIn("src/main.test.ts", cmd)

    def test_go(self):
        cmd = build_targeted_command("go test ./...", "pkg/handler_test.go", {"name": "go-test"})
        self.assertIn("pkg", cmd)


class TestParsePytestOutput(TestCase):
    def test_all_pass(self):
        output = "======== 5 passed in 0.3s ========"
        results = parse_pytest_output(output)
        self.assertEqual(results["passed"], 5)
        self.assertEqual(results["failed"], 0)
        self.assertEqual(results["total"], 5)

    def test_mixed(self):
        output = "======== 3 passed, 2 failed, 1 skipped in 1.2s ========"
        results = parse_pytest_output(output)
        self.assertEqual(results["passed"], 3)
        self.assertEqual(results["failed"], 2)
        self.assertEqual(results["skipped"], 1)
        self.assertEqual(results["total"], 6)

    def test_with_errors(self):
        output = "======== 1 passed, 1 error in 0.5s ========"
        results = parse_pytest_output(output)
        self.assertEqual(results["passed"], 1)
        self.assertEqual(results["errored"], 1)


class TestParseJestOutput(TestCase):
    def test_basic(self):
        output = "Tests:  3 passed, 3 total\nTime:   0.5s"
        results = parse_jest_output(output)
        self.assertEqual(results["passed"], 3)

    def test_failures(self):
        output = "Tests:  2 failed, 3 passed, 5 total"
        results = parse_jest_output(output)
        self.assertEqual(results["failed"], 2)


class TestParseGoOutput(TestCase):
    def test_pass(self):
        output = "--- PASS: TestFoo (0.01s)\n--- PASS: TestBar (0.02s)\nPASS"
        results = parse_go_output(output)
        self.assertEqual(results["passed"], 2)
        self.assertEqual(results["failed"], 0)

    def test_fail(self):
        output = "--- FAIL: TestFoo (0.01s)\n--- PASS: TestBar (0.02s)"
        results = parse_go_output(output)
        self.assertEqual(results["passed"], 1)
        self.assertEqual(results["failed"], 1)


class TestParseMavenOutput(TestCase):
    def test_basic(self):
        output = "Tests run: 10, Failures: 1, Errors: 0, Skipped: 2"
        results = parse_maven_output(output)
        self.assertEqual(results["total"], 10)
        self.assertEqual(results["failed"], 1)
        self.assertEqual(results["errored"], 0)
        self.assertEqual(results["skipped"], 2)
        self.assertEqual(results["passed"], 7)


class TestParseResults(TestCase):
    def test_pass_exit_code(self):
        results = parse_results("5 passed", "pytest", 0)
        self.assertEqual(results["overall"], "PASS")

    def test_fail_exit_code(self):
        results = parse_results("1 failed", "pytest", 1)
        self.assertEqual(results["overall"], "FAIL")

    def test_unknown_framework(self):
        results = parse_results("output", "unknown", 0)
        self.assertEqual(results["overall"], "PASS")
        self.assertIsNone(results["total"])


class TestExtractFailures(TestCase):
    def test_pytest_failures(self):
        output = "FAILED tests/test_main.py::test_login\nFAILED tests/test_main.py::test_logout"
        failures = extract_failures(output, "pytest")
        self.assertEqual(len(failures), 2)
        self.assertEqual(failures[0]["test_name"], "test_login")

    def test_jest_failures(self):
        output = "● Auth > should reject invalid tokens\n● Auth > should timeout"
        failures = extract_failures(output, "jest")
        self.assertEqual(len(failures), 2)

    def test_truncates_at_20(self):
        output = "\n".join(f"FAILED test_{i}.py::test_func" for i in range(30))
        failures = extract_failures(output, "pytest")
        self.assertLessEqual(len(failures), 20)


class TestFrameworkVerboseFlags(TestCase):
    """Verify the DRY FRAMEWORK_VERBOSE_FLAGS constant is consistent."""

    def test_pytest_flags_exist(self):
        self.assertIn("pytest", FRAMEWORK_VERBOSE_FLAGS)
        self.assertIn("-v", FRAMEWORK_VERBOSE_FLAGS["pytest"])
        self.assertIn("--tb=short", FRAMEWORK_VERBOSE_FLAGS["pytest"])

    def test_jest_flags_exist(self):
        self.assertIn("jest", FRAMEWORK_VERBOSE_FLAGS)
        self.assertIn("--verbose", FRAMEWORK_VERBOSE_FLAGS["jest"])

    def test_vitest_flags_exist(self):
        self.assertIn("vitest", FRAMEWORK_VERBOSE_FLAGS)

    def test_go_flags_exist(self):
        self.assertIn("go-test", FRAMEWORK_VERBOSE_FLAGS)
        self.assertIn("-v", FRAMEWORK_VERBOSE_FLAGS["go-test"])

    def test_build_targeted_uses_flags(self):
        """Targeted command should incorporate the same flags as full-suite."""
        cmd = build_targeted_command("python -m pytest", "tests/test_x.py", {"name": "pytest"})
        for flag in FRAMEWORK_VERBOSE_FLAGS["pytest"].split():
            self.assertIn(flag, cmd)


if __name__ == "__main__":
    main()
