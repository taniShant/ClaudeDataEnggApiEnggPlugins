"""Tests for wiz_setup.py."""

import os
import sys
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.validators.wiz_setup import (
    get_platform,
    is_ci_environment,
    check_installed,
    check_authenticated,
    find_install_method,
    get_install_instructions,
    get_auth_instructions,
    INSTALL_COMMANDS,
)


class TestGetPlatform(TestCase):
    def test_returns_string(self):
        plat = get_platform()
        self.assertIn(plat, ("darwin", "win32", "linux"))


class TestIsCiEnvironment(TestCase):
    @patch.dict(os.environ, {"CI": "true"})
    def test_ci_true(self):
        self.assertTrue(is_ci_environment())

    @patch.dict(os.environ, {"GITLAB_CI": "true"})
    def test_gitlab_ci(self):
        self.assertTrue(is_ci_environment())

    @patch.dict(os.environ, {}, clear=True)
    def test_not_ci(self):
        # Remove all CI vars
        for var in ["CI", "GITLAB_CI", "JENKINS_URL", "TEAMCITY_VERSION", "GITHUB_ACTIONS"]:
            os.environ.pop(var, None)
        self.assertFalse(is_ci_environment())


class TestCheckInstalled(TestCase):
    @patch("scripts.validators.wiz_setup.run_cmd")
    def test_installed(self, mock_cmd):
        mock_cmd.return_value = {
            "exit_code": 0,
            "stdout": "Wiz CLI v0.105.0-c9f6a22, built 2025-11-19T12:35:08Z",
            "stderr": "",
        }
        result = check_installed()
        self.assertTrue(result["installed"])
        self.assertEqual(result["version"], "v0.105.0-c9f6a22")

    @patch("scripts.validators.wiz_setup.run_cmd")
    def test_not_installed(self, mock_cmd):
        mock_cmd.return_value = {"exit_code": -1, "stdout": "", "stderr": "not found"}
        result = check_installed()
        self.assertFalse(result["installed"])
        self.assertEqual(result["version"], "")


class TestCheckAuthenticated(TestCase):
    @patch("scripts.validators.wiz_setup.run_cmd")
    def test_authenticated(self, mock_cmd):
        mock_cmd.return_value = {
            "exit_code": 0,
            "stdout": "Client email: dev@barclays.com\nExpires at: 2026-10-01\nAccess token: eyJ...\n",
            "stderr": "",
        }
        result = check_authenticated()
        self.assertTrue(result["authenticated"])
        self.assertEqual(result["client_email"], "dev@barclays.com")

    @patch("scripts.validators.wiz_setup.run_cmd")
    def test_not_authenticated(self, mock_cmd):
        mock_cmd.return_value = {"exit_code": 1, "stdout": "", "stderr": "not authenticated"}
        result = check_authenticated()
        self.assertFalse(result["authenticated"])

    @patch("scripts.validators.wiz_setup.run_cmd")
    def test_expired_token_in_stderr(self, mock_cmd):
        """wizcli returns exit 0 with 'No stored authentication data' in stderr when token expired."""
        mock_cmd.return_value = {
            "exit_code": 0,
            "stdout": "",
            "stderr": "No stored authentication data found. Please run 'wizcli auth' to authenticate.",
        }
        result = check_authenticated()
        self.assertFalse(result["authenticated"])
        self.assertTrue(result.get("expired", False))

    @patch("scripts.validators.wiz_setup.run_cmd")
    def test_expired_token_in_stdout(self, mock_cmd):
        """Also catch the message if it appears in stdout."""
        mock_cmd.return_value = {
            "exit_code": 0,
            "stdout": "No stored authentication data found.",
            "stderr": "",
        }
        result = check_authenticated()
        self.assertFalse(result["authenticated"])


class TestFindInstallMethod(TestCase):
    @patch("scripts.validators.wiz_setup.run_cmd")
    def test_darwin_brew_available(self, mock_cmd):
        mock_cmd.return_value = {"exit_code": 0, "stdout": "Homebrew 4.0", "stderr": ""}
        method = find_install_method("darwin")
        self.assertIsNotNone(method)
        self.assertEqual(method["name"], "brew")

    @patch("scripts.validators.wiz_setup.run_cmd")
    def test_no_method_available(self, mock_cmd):
        mock_cmd.return_value = {"exit_code": -1, "stdout": "", "stderr": "not found"}
        method = find_install_method("darwin")
        self.assertIsNone(method)

    @patch("scripts.validators.wiz_setup.run_cmd")
    def test_linux_dev_cli_available(self, mock_cmd):
        mock_cmd.return_value = {"exit_code": 0, "stdout": "dev v1.0", "stderr": ""}
        method = find_install_method("linux")
        self.assertIsNotNone(method)
        self.assertEqual(method["name"], "dev_cli")

    @patch("scripts.validators.wiz_setup.run_cmd")
    def test_linux_falls_back_to_curl(self, mock_cmd):
        def side_effect(cmd, **kwargs):
            if cmd[0] == "dev":
                return {"exit_code": -1, "stdout": "", "stderr": "not found"}
            if cmd[0] == "curl":
                return {"exit_code": 0, "stdout": "curl 8.0", "stderr": ""}
            return {"exit_code": -1, "stdout": "", "stderr": ""}
        mock_cmd.side_effect = side_effect
        method = find_install_method("linux")
        self.assertIsNotNone(method)
        self.assertEqual(method["name"], "curl")

    @patch("scripts.validators.wiz_setup.run_cmd")
    def test_win32_dev_cli(self, mock_cmd):
        mock_cmd.return_value = {"exit_code": 0, "stdout": "dev v1.0", "stderr": ""}
        method = find_install_method("win32")
        self.assertIsNotNone(method)
        self.assertEqual(method["name"], "dev_cli")

    @patch("scripts.validators.wiz_setup.run_cmd")
    def test_win32_falls_back_to_winget(self, mock_cmd):
        def side_effect(cmd, **kwargs):
            if cmd[0] == "dev":
                return {"exit_code": -1, "stdout": "", "stderr": "not found"}
            if cmd[0] == "winget":
                return {"exit_code": 0, "stdout": "v1.7", "stderr": ""}
            return {"exit_code": -1, "stdout": "", "stderr": ""}
        mock_cmd.side_effect = side_effect
        method = find_install_method("win32")
        self.assertIsNotNone(method)
        self.assertEqual(method["name"], "winget")


class TestInstallCommands(TestCase):
    def test_all_platforms_have_methods(self):
        for plat in ("darwin", "linux", "win32"):
            self.assertIn(plat, INSTALL_COMMANDS)
            self.assertTrue(len(INSTALL_COMMANDS[plat]) > 0)

    def test_all_methods_have_required_keys(self):
        for plat, methods in INSTALL_COMMANDS.items():
            for method in methods:
                self.assertIn("name", method)
                self.assertIn("check", method)
                self.assertIn("install", method)
                self.assertIn("description", method)
                # All commands must be list form (injection-safe)
                self.assertIsInstance(method["check"], list)
                self.assertIsInstance(method["install"], list)


class TestGetInstallInstructions(TestCase):
    def test_darwin(self):
        instructions = get_install_instructions("darwin")
        self.assertIn("brew install --cask wizcli", instructions)

    def test_win32(self):
        instructions = get_install_instructions("win32")
        self.assertIn("dev tool install wizcli", instructions)
        self.assertIn("winget", instructions)

    def test_linux(self):
        instructions = get_install_instructions("linux")
        self.assertIn("dev tool install wizcli", instructions)
        self.assertIn("curl", instructions)


class TestGetAuthInstructions(TestCase):
    def test_device_code(self):
        instructions = get_auth_instructions()
        self.assertIn("wizcli auth --use-device-code", instructions)

    def test_service_account(self):
        instructions = get_auth_instructions()
        self.assertIn("WIZ_CLIENT_ID", instructions)
        self.assertIn("WIZ_CLIENT_SECRET", instructions)


if __name__ == "__main__":
    main()
