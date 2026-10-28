"""Tests for detect_build.py."""

import json
import sys
import tempfile
from pathlib import Path
from unittest import TestCase, main

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.validators.detect_build import (
    detect_build_system,
    check_npm_has_build,
    BUILD_SYSTEMS,
)


class TestDetectBuildSystem(TestCase):
    """Test build system detection via indicator files."""

    def test_gradle(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "build.gradle").touch()
            result = detect_build_system(Path(tmp))
            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "gradle")

    def test_gradle_kts(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "build.gradle.kts").touch()
            result = detect_build_system(Path(tmp))
            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "gradle")

    def test_maven(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "pom.xml").touch()
            result = detect_build_system(Path(tmp))
            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "maven")

    def test_npm(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "package.json").write_text("{}")
            result = detect_build_system(Path(tmp))
            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "npm")

    def test_go(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "go.mod").touch()
            result = detect_build_system(Path(tmp))
            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "go")

    def test_cargo(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Cargo.toml").touch()
            result = detect_build_system(Path(tmp))
            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "cargo")

    def test_dotnet_csproj(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "MyApp.csproj").touch()
            result = detect_build_system(Path(tmp))
            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "dotnet")

    def test_dotnet_sln(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Solution.sln").touch()
            result = detect_build_system(Path(tmp))
            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "dotnet")

    def test_no_build_system(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = detect_build_system(Path(tmp))
            self.assertIsNone(result)

    def test_priority_gradle_over_npm(self):
        """Gradle should win if both are present (higher priority)."""
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "build.gradle").touch()
            (Path(tmp) / "package.json").write_text("{}")
            result = detect_build_system(Path(tmp))
            self.assertEqual(result["name"], "gradle")


class TestCheckNpmHasBuild(TestCase):
    def test_has_build_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "package.json"
            pkg.write_text(json.dumps({"scripts": {"build": "tsc"}}))
            self.assertTrue(check_npm_has_build(Path(tmp)))

    def test_no_build_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "package.json"
            pkg.write_text(json.dumps({"scripts": {"test": "jest"}}))
            self.assertFalse(check_npm_has_build(Path(tmp)))

    def test_no_scripts(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "package.json"
            pkg.write_text(json.dumps({"name": "my-app"}))
            self.assertFalse(check_npm_has_build(Path(tmp)))

    def test_no_package_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(check_npm_has_build(Path(tmp)))

    def test_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "package.json"
            pkg.write_text("not valid json{")
            self.assertFalse(check_npm_has_build(Path(tmp)))


class TestBuildSystemsConfig(TestCase):
    """Verify BUILD_SYSTEMS configuration integrity."""

    def test_all_have_required_keys(self):
        required_keys = {"name", "indicators", "command_with_wrapper", "command_without_wrapper", "wrapper_file"}
        for bs in BUILD_SYSTEMS:
            for key in required_keys:
                self.assertIn(key, bs, f"Missing key '{key}' in build system '{bs.get('name', '?')}'")

    def test_all_have_non_empty_name(self):
        for bs in BUILD_SYSTEMS:
            self.assertTrue(bs["name"], "Build system has empty name")

    def test_all_have_indicators(self):
        for bs in BUILD_SYSTEMS:
            self.assertGreater(len(bs["indicators"]), 0, f"{bs['name']} has no indicators")


if __name__ == "__main__":
    main()
