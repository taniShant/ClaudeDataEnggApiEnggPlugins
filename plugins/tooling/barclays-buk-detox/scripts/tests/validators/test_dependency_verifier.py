"""Tests for dependency_verifier.py."""

import json
import sys
import tempfile
from pathlib import Path
from unittest import TestCase, main

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.validators.dependency_verifier import (
    detect_ecosystem,
    get_dep_command,
    check_version_absent,
    check_version_present,
    parse_sbom_for_package,
)

# Path to the shared fixtures directory (one level up from validators/)
_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


class TestDetectEcosystem(TestCase):
    """detect_ecosystem returns the correct ecosystem from indicator files."""

    def test_gradle(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "build.gradle").touch()
            self.assertEqual(detect_ecosystem(tmp), "gradle")

    def test_maven(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "pom.xml").touch()
            self.assertEqual(detect_ecosystem(tmp), "maven")

    def test_npm(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "package.json").write_text("{}")
            self.assertEqual(detect_ecosystem(tmp), "npm")

    def test_pip(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "requirements.txt").touch()
            self.assertEqual(detect_ecosystem(tmp), "pip")

    def test_go(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "go.mod").touch()
            self.assertEqual(detect_ecosystem(tmp), "go")

    def test_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(detect_ecosystem(tmp))

    def test_gradle_wins_over_npm(self):
        """gradle has higher priority than npm when both are present."""
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "build.gradle").touch()
            (Path(tmp) / "package.json").write_text("{}")
            self.assertEqual(detect_ecosystem(tmp), "gradle")

    def test_gradle_kts(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "build.gradle.kts").touch()
            self.assertEqual(detect_ecosystem(tmp), "gradle")

    def test_dotnet_csproj(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "MyApp.csproj").touch()
            self.assertEqual(detect_ecosystem(tmp), "dotnet")

    def test_cargo(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Cargo.toml").touch()
            self.assertEqual(detect_ecosystem(tmp), "cargo")


class TestGetDepCommand(TestCase):
    """get_dep_command returns the correct list-form command for each ecosystem."""

    def test_gradle_with_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "gradlew").touch()
            cmd = get_dep_command("gradle", tmp)
            self.assertEqual(cmd[0], "./gradlew")
            self.assertIn("dependencies", cmd)

    def test_gradle_without_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            cmd = get_dep_command("gradle", tmp)
            self.assertEqual(cmd[0], "gradle")
            self.assertIn("dependencies", cmd)

    def test_maven(self):
        with tempfile.TemporaryDirectory() as tmp:
            cmd = get_dep_command("maven", tmp)
            self.assertEqual(cmd[0], "mvn")
            self.assertIn("dependency:tree", cmd)

    def test_pip_with_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            cmd = get_dep_command("pip", tmp, package_name="requests")
            self.assertEqual(cmd[0], "pip")
            self.assertEqual(cmd[-1], "requests")

    def test_npm_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            cmd = get_dep_command("npm", tmp)
            self.assertEqual(cmd[0], "npm")
            self.assertIn("ls", cmd)

    def test_go_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            cmd = get_dep_command("go", tmp)
            self.assertEqual(cmd[0], "go")
            self.assertIn("list", cmd)

    def test_unknown_ecosystem_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            cmd = get_dep_command("unknown_eco", tmp)
            self.assertEqual(cmd, [])

    def test_pip_without_package_has_no_trailing_none(self):
        """pip command without package_name must not append None."""
        with tempfile.TemporaryDirectory() as tmp:
            cmd = get_dep_command("pip", tmp)
            self.assertNotIn(None, cmd)

    def test_gradle_command_is_list_not_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            cmd = get_dep_command("gradle", tmp)
            self.assertIsInstance(cmd, list)
            for part in cmd:
                self.assertIsInstance(part, str)


class TestCheckVersionAbsent(TestCase):
    """check_version_absent returns True when the vulnerable version is NOT in output."""

    def test_gradle_absent(self):
        output = "ch.qos.reload4j:reload4j:1.2.26\norg.springframework:spring-core:5.3.39"
        self.assertTrue(check_version_absent(output, "log4j:log4j", "1.2.17"))

    def test_gradle_present(self):
        output = "log4j:log4j:1.2.17\norg.springframework:spring-core:5.3.39"
        self.assertFalse(check_version_absent(output, "log4j:log4j", "1.2.17"))

    def test_maven_absent(self):
        output = (
            "[INFO] +- ch.qos.reload4j:reload4j:jar:1.2.26:compile\n"
            "[INFO] +- org.springframework:spring-core:jar:5.3.39:compile"
        )
        self.assertTrue(check_version_absent(output, "log4j:log4j", "1.2.17"))

    def test_maven_present(self):
        output = "[INFO] +- log4j:log4j:jar:1.2.17:compile"
        self.assertFalse(check_version_absent(output, "log4j:log4j", "1.2.17"))

    def test_npm_json_absent(self):
        npm_output = json.dumps({
            "name": "my-app",
            "version": "1.0.0",
            "dependencies": {
                "lodash": {"version": "4.17.21"},
                "express": {"version": "4.18.2"},
            },
        })
        self.assertTrue(check_version_absent(npm_output, "lodash", "3.10.1"))

    def test_npm_json_present(self):
        npm_output = json.dumps({
            "name": "my-app",
            "version": "1.0.0",
            "dependencies": {
                "lodash": {"version": "3.10.1"},
            },
        })
        self.assertFalse(check_version_absent(npm_output, "lodash", "3.10.1"))

    def test_go_absent(self):
        output = "github.com/some/module v1.2.0\ngolang.org/x/text v0.13.0"
        self.assertTrue(check_version_absent(output, "module", "1.0.0"))

    def test_go_present(self):
        output = "github.com/some/module v1.0.0\ngolang.org/x/text v0.13.0"
        self.assertFalse(check_version_absent(output, "module", "1.0.0"))

    def test_pip_absent(self):
        output = "Name: requests\nVersion: 2.31.0\nSummary: Python HTTP for Humans."
        self.assertTrue(check_version_absent(output, "requests", "2.28.0"))

    def test_pip_present(self):
        output = "Name: requests\nVersion: 2.28.0\nSummary: Python HTTP for Humans."
        self.assertFalse(check_version_absent(output, "requests", "2.28.0"))

    def test_dotnet_absent(self):
        output = "> Newtonsoft.Json  13.0.3\n> System.Text.Json  7.0.0"
        self.assertTrue(check_version_absent(output, "Newtonsoft.Json", "12.0.3"))

    def test_cargo_absent(self):
        output = "my-crate v0.2.0\nserde v1.0.195"
        self.assertTrue(check_version_absent(output, "serde", "0.9.0"))


class TestCheckVersionPresent(TestCase):
    """check_version_present returns True when the safe version IS in output."""

    def test_gradle_present(self):
        output = "ch.qos.reload4j:reload4j:1.2.26\norg.springframework:spring-core:5.3.39"
        self.assertTrue(check_version_present(output, "reload4j:reload4j", "1.2.26"))

    def test_gradle_absent(self):
        output = "ch.qos.reload4j:reload4j:1.2.24\norg.springframework:spring-core:5.3.39"
        self.assertFalse(check_version_present(output, "reload4j:reload4j", "1.2.26"))

    def test_npm_present(self):
        npm_output = json.dumps({
            "name": "my-app",
            "version": "1.0.0",
            "dependencies": {
                "lodash": {"version": "4.17.21"},
            },
        })
        self.assertTrue(check_version_present(npm_output, "lodash", "4.17.21"))

    def test_npm_absent(self):
        npm_output = json.dumps({
            "name": "my-app",
            "version": "1.0.0",
            "dependencies": {
                "lodash": {"version": "3.10.1"},
            },
        })
        self.assertFalse(check_version_present(npm_output, "lodash", "4.17.21"))

    def test_maven_present(self):
        output = "[INFO] +- log4j:log4j:jar:1.2.26:compile"
        self.assertTrue(check_version_present(output, "log4j:log4j", "1.2.26"))

    def test_pip_present(self):
        output = "Name: requests\nVersion: 2.31.0\nSummary: Python HTTP for Humans."
        self.assertTrue(check_version_present(output, "requests", "2.31.0"))

    def test_go_present(self):
        output = "github.com/some/module v1.2.0\ngolang.org/x/text v0.13.0"
        self.assertTrue(check_version_present(output, "module", "1.2.0"))

    def test_dotnet_present(self):
        output = "> Newtonsoft.Json  13.0.3\n> System.Text.Json  7.0.0"
        self.assertTrue(check_version_present(output, "Newtonsoft.Json", "13.0.3"))

    def test_cargo_present(self):
        output = "my-crate v0.2.0\nserde v1.0.195"
        self.assertTrue(check_version_present(output, "serde", "1.0.195"))


class TestParseSbomForPackage(TestCase):
    """parse_sbom_for_package correctly reads the CycloneDX fixture."""

    @classmethod
    def setUpClass(cls):
        fixture_path = _FIXTURES_DIR / "sample_sbom_cyclonedx.json"
        with open(fixture_path) as fh:
            cls.sbom = json.load(fh)

    def test_found_maven(self):
        result = parse_sbom_for_package(self.sbom, "ch.qos.reload4j:reload4j")
        self.assertIsNotNone(result)
        self.assertEqual(result["version"], "1.2.26")
        self.assertEqual(result["name"], "reload4j")
        self.assertIn("pkg:maven", result["purl"])

    def test_not_found(self):
        result = parse_sbom_for_package(self.sbom, "nonexistent:package")
        self.assertIsNone(result)

    def test_simple_name(self):
        """Matching by name-only (no group prefix) returns the component."""
        result = parse_sbom_for_package(self.sbom, "jackson-databind")
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "jackson-databind")
        self.assertEqual(result["version"], "2.18.2")

    def test_full_group_and_name_spring(self):
        result = parse_sbom_for_package(self.sbom, "org.springframework:spring-core")
        self.assertIsNotNone(result)
        self.assertEqual(result["version"], "5.3.39")

    def test_empty_components(self):
        result = parse_sbom_for_package({"components": []}, "log4j:log4j")
        self.assertIsNone(result)

    def test_missing_components_key(self):
        result = parse_sbom_for_package({}, "log4j:log4j")
        self.assertIsNone(result)

    def test_returns_dict_with_required_keys(self):
        result = parse_sbom_for_package(self.sbom, "ch.qos.reload4j:reload4j")
        self.assertIn("name", result)
        self.assertIn("version", result)
        self.assertIn("purl", result)

    def test_wrong_group_returns_none(self):
        """Correct name but wrong group must not match."""
        result = parse_sbom_for_package(self.sbom, "wrong.group:reload4j")
        self.assertIsNone(result)


if __name__ == "__main__":
    main()
