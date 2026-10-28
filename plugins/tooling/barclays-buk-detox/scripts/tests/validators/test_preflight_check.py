"""Tests for preflight_check.py."""

import sys
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.validators.preflight_check import (
    get_platform,
    check_python,
    get_install_instruction,
    INSTALL_INSTRUCTIONS,
    check_observe_deps,
    check_semgrep,
    OBSERVE_DEPS,
)


class TestCheckObserveDeps(TestCase):
    """OTel/gRPC telemetry deps are a CHECK-ONLY prerequisite (never installed here)."""

    def test_shape(self):
        result = check_observe_deps()
        self.assertEqual(result["name"], "observe_deps")
        self.assertIn("available", result)
        self.assertIn("missing_packages", result)

    def test_required_packages(self):
        pkgs = [pkg for _mod, pkg in OBSERVE_DEPS]
        self.assertIn("grpcio", pkgs)
        self.assertIn("opentelemetry-sdk", pkgs)
        self.assertIn("opentelemetry-exporter-otlp-proto-grpc", pkgs)

    def test_reports_missing_when_absent(self):
        # Force all import probes to report missing -> available False, all listed.
        with patch("importlib.util.find_spec", return_value=None):
            result = check_observe_deps()
        self.assertFalse(result["available"])
        self.assertEqual(len(result["missing_packages"]), len(OBSERVE_DEPS))

    def test_does_not_install(self):
        # check_observe_deps must never shell out to pip / create a venv.
        with patch("subprocess.run") as m_run, patch("subprocess.check_call") as m_call:
            check_observe_deps()
        m_run.assert_not_called()
        m_call.assert_not_called()


class TestCheckSemgrep(TestCase):
    """semgrep's online version lookup can hang past the 30s preflight timeout."""

    OK = {"exit_code": 0, "stdout": "1.144.0\n", "stderr": ""}
    MISSING = {"exit_code": -1, "stdout": "", "stderr": "not found"}

    def test_disables_online_version_check(self):
        with patch("scripts.validators.preflight_check.run_cmd", return_value=self.OK) as m_run:
            result = check_semgrep()
        self.assertTrue(result["available"])
        self.assertEqual(result["version"], "1.144.0")
        self.assertEqual(m_run.call_args.kwargs["env"], {"SEMGREP_ENABLE_VERSION_CHECK": "0"})

    def test_fallback_paths_also_disable_version_check(self):
        with patch("scripts.validators.preflight_check.run_cmd",
                   side_effect=[self.MISSING, self.MISSING, self.MISSING, self.OK]) as m_run:
            result = check_semgrep()
        self.assertTrue(result["available"])
        for call in m_run.call_args_list:
            self.assertEqual(call.kwargs["env"], {"SEMGREP_ENABLE_VERSION_CHECK": "0"})

    def test_reports_missing_when_not_installed(self):
        with patch("scripts.validators.preflight_check.run_cmd", return_value=self.MISSING):
            result = check_semgrep()
        self.assertFalse(result["available"])


class TestGetPlatform(TestCase):
    def test_returns_string(self):
        result = get_platform()
        self.assertIsInstance(result, str)
        self.assertIn(result, ("darwin", "linux", "win32"))


class TestCheckPython(TestCase):
    def test_python_returns_dict(self):
        result = check_python()
        self.assertEqual(result["name"], "python")
        self.assertIn(".", result["version"])  # e.g., "3.12.0" or "3.9.6"
        self.assertIsNotNone(result["path"])

    def test_python_min_version_field(self):
        result = check_python()
        self.assertEqual(result["min_version"], "3.10")

    def test_python_available_reflects_version(self):
        result = check_python()
        expected = sys.version_info >= (3, 10)
        self.assertEqual(result["available"], expected)


class TestGetInstallInstruction(TestCase):
    def test_darwin_git(self):
        instruction = get_install_instruction("git", "darwin")
        self.assertIn("xcode-select", instruction)

    def test_win32_git(self):
        instruction = get_install_instruction("git", "win32")
        self.assertIn("Dev CLI", instruction)

    def test_darwin_semgrep(self):
        instruction = get_install_instruction("semgrep", "darwin")
        self.assertIn("brew install semgrep", instruction)

    def test_win32_semgrep(self):
        instruction = get_install_instruction("semgrep", "win32")
        self.assertIn("pip install semgrep", instruction)

    def test_darwin_glab(self):
        instruction = get_install_instruction("glab", "darwin")
        self.assertIn("brew install glab", instruction)
        self.assertIn("app.gitlab.barcapint.com", instruction)

    def test_win32_glab(self):
        instruction = get_install_instruction("glab", "win32")
        self.assertIn("GITLAB_TOKEN", instruction)

    def test_linux_falls_back_to_darwin(self):
        # Linux should use darwin instructions as fallback
        instruction = get_install_instruction("git", "linux")
        self.assertIn("xcode-select", instruction)

    def test_unknown_tool(self):
        instruction = get_install_instruction("unknown-tool", "darwin")
        self.assertIn("Contact your team", instruction)


class TestInstallInstructionsCompleteness(TestCase):
    """Verify all tools have instructions for both platforms."""

    def test_all_tools_have_darwin(self):
        for tool, platforms in INSTALL_INSTRUCTIONS.items():
            self.assertIn("darwin", platforms, f"Missing darwin instructions for {tool}")

    def test_all_tools_have_win32(self):
        for tool, platforms in INSTALL_INSTRUCTIONS.items():
            self.assertIn("win32", platforms, f"Missing win32 instructions for {tool}")


if __name__ == "__main__":
    main()
