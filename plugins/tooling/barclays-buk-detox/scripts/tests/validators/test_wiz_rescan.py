"""Tests for wiz_rescan.py."""

import json
import sys
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch, mock_open

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.validators.wiz_rescan import (
    check_wizcli_installed,
    check_wizcli_auth,
    run_wiz_scan,
    parse_wiz_scan_output,
)

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

_SAMPLE_OUTPUT_PATH = str(FIXTURES_DIR / "sample_wiz_scan_output.json")
_SAMPLE_EMPTY_PATH = str(FIXTURES_DIR / "sample_wiz_scan_empty.json")

with open(_SAMPLE_OUTPUT_PATH) as _f:
    _SAMPLE_WIZ_SCAN_OUTPUT = json.load(_f)

with open(_SAMPLE_EMPTY_PATH) as _f:
    _SAMPLE_WIZ_SCAN_EMPTY = json.load(_f)


def _cmd_result(exit_code: int = 0, stdout: str = "", stderr: str = "") -> dict:
    """Build a run_cmd-style result dict."""
    return {"exit_code": exit_code, "stdout": stdout, "stderr": stderr}


# ---------------------------------------------------------------------------
# TestCheckWizCliInstalled
# ---------------------------------------------------------------------------

class TestCheckWizCliInstalled(TestCase):

    @patch("scripts.validators.wiz_rescan.run_cmd")
    def test_installed(self, mock_run_cmd):
        """wizcli present — installed=True and version extracted."""
        mock_run_cmd.return_value = _cmd_result(
            exit_code=0,
            stdout="Wiz CLI v0.105.0-c9f6a22, built 2025-11-19T12:35:08Z",
        )
        result = check_wizcli_installed()
        self.assertTrue(result["installed"])
        self.assertEqual(result["version"], "v0.105.0-c9f6a22")

    @patch("scripts.validators.wiz_rescan.run_cmd")
    def test_not_installed(self, mock_run_cmd):
        """wizcli absent — installed=False and empty version."""
        mock_run_cmd.return_value = _cmd_result(
            exit_code=-1,
            stderr="Command not found: wizcli",
        )
        result = check_wizcli_installed()
        self.assertFalse(result["installed"])
        self.assertEqual(result["version"], "")

    @patch("scripts.validators.wiz_rescan.run_cmd")
    def test_version_parsing(self, mock_run_cmd):
        """Version token is extracted correctly from multi-word stdout."""
        mock_run_cmd.return_value = _cmd_result(
            exit_code=0,
            stdout="Wiz CLI v1.2.3-abc1234, built 2026-01-01T00:00:00Z",
        )
        result = check_wizcli_installed()
        self.assertEqual(result["version"], "v1.2.3-abc1234")

    @patch("scripts.validators.wiz_rescan.run_cmd")
    def test_non_zero_exit_code_returns_not_installed(self, mock_run_cmd):
        """Non-zero exit even with stdout output — treat as not installed."""
        mock_run_cmd.return_value = _cmd_result(
            exit_code=1,
            stdout="some noise",
            stderr="error",
        )
        result = check_wizcli_installed()
        self.assertFalse(result["installed"])

    @patch("scripts.validators.wiz_rescan.run_cmd")
    def test_run_cmd_called_with_list(self, mock_run_cmd):
        """run_cmd must be called with a list, not a string."""
        mock_run_cmd.return_value = _cmd_result(exit_code=0, stdout="Wiz CLI v0.1.0,")
        check_wizcli_installed()
        args, _ = mock_run_cmd.call_args
        self.assertIsInstance(args[0], list)
        self.assertEqual(args[0], ["wizcli", "version"])


# ---------------------------------------------------------------------------
# TestCheckWizCliAuth
# ---------------------------------------------------------------------------

class TestCheckWizCliAuth(TestCase):

    @patch("scripts.validators.wiz_rescan.run_cmd")
    def test_authenticated(self, mock_run_cmd):
        """Valid auth output — authenticated=True with correct fields."""
        mock_run_cmd.return_value = _cmd_result(
            exit_code=0,
            stdout=(
                "Access token: eyJhbGciOiJSUzI1NiJ9.PAYLOAD.SIGNATURE\n"
                "Client email: user@barclays.com\n"
                "Expires at: 2026-09-23\n"
            ),
        )
        result = check_wizcli_auth()
        self.assertTrue(result["authenticated"])
        self.assertEqual(result["client_email"], "user@barclays.com")
        self.assertEqual(result["expires_at"], "2026-09-23")

    @patch("scripts.validators.wiz_rescan.run_cmd")
    def test_not_authenticated(self, mock_run_cmd):
        """Non-zero exit code — authenticated=False."""
        mock_run_cmd.return_value = _cmd_result(
            exit_code=1,
            stderr="Error: not authenticated",
        )
        result = check_wizcli_auth()
        self.assertFalse(result["authenticated"])
        self.assertEqual(result["client_email"], "")
        self.assertEqual(result["expires_at"], "")

    @patch("scripts.validators.wiz_rescan.run_cmd")
    def test_token_not_in_output(self, mock_run_cmd):
        """The returned dict must NOT contain any access token value."""
        raw_token = "eyJhbGciOiJSUzI1NiJ9.PAYLOAD.SIGNATURE"
        mock_run_cmd.return_value = _cmd_result(
            exit_code=0,
            stdout=(
                f"Access token: {raw_token}\n"
                "Client email: svc@barclays.com\n"
                "Expires at: 2026-12-31\n"
            ),
        )
        result = check_wizcli_auth()
        # Serialise the entire result to a string and check the token is absent
        result_str = json.dumps(result)
        self.assertNotIn(raw_token, result_str,
                         "Access token must not appear anywhere in the returned dict")

    @patch("scripts.validators.wiz_rescan.run_cmd")
    def test_auth_command_is_list(self, mock_run_cmd):
        """run_cmd must be called with the correct list-form command."""
        mock_run_cmd.return_value = _cmd_result(
            exit_code=0,
            stdout="Client email: x@x.com\nExpires at: 2026-01-01\n",
        )
        check_wizcli_auth()
        args, _ = mock_run_cmd.call_args
        self.assertEqual(args[0], ["wizcli", "auth", "--print-token"])

    @patch("scripts.validators.wiz_rescan.run_cmd")
    def test_missing_fields_gracefully_empty(self, mock_run_cmd):
        """Auth stdout without expected lines returns empty strings, not KeyError."""
        mock_run_cmd.return_value = _cmd_result(
            exit_code=0,
            stdout="Some unexpected output\n",
        )
        result = check_wizcli_auth()
        self.assertTrue(result["authenticated"])
        self.assertEqual(result["client_email"], "")
        self.assertEqual(result["expires_at"], "")


# ---------------------------------------------------------------------------
# TestRunWizScan
# ---------------------------------------------------------------------------

class TestRunWizScan(TestCase):

    @patch("scripts.validators.wiz_rescan.parse_wiz_scan_output")
    @patch("scripts.validators.wiz_rescan.run_cmd")
    def test_success(self, mock_run_cmd, mock_parse):
        """Successful scan — status=success with findings count."""
        mock_run_cmd.return_value = _cmd_result(exit_code=0)
        mock_parse.return_value = {
            "findings": _SAMPLE_WIZ_SCAN_OUTPUT["extraDetails"]["sastDetails"]["findings"],
            "libraries": _SAMPLE_WIZ_SCAN_OUTPUT["extraDetails"]["vulnerabilityDetails"]["libraries"],
            "metadata": {"scan_id": "006a6c39-d90b-88f3-8049-834991d18001"},
        }

        result = run_wiz_scan(
            repo_dir="/repo",
            output_path="/tmp/wiz-out.json",
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["findings_count"], 4)
        self.assertEqual(result["scan_path"], "/tmp/wiz-out.json")

    @patch("scripts.validators.wiz_rescan.run_cmd")
    def test_scan_failure(self, mock_run_cmd):
        """Non-zero exit code — status=error, reason=scan_failed."""
        mock_run_cmd.return_value = _cmd_result(
            exit_code=1,
            stderr="wizcli: authentication error",
        )
        result = run_wiz_scan(repo_dir="/repo", output_path="/tmp/wiz-out.json")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["reason"], "scan_failed")
        self.assertIn("detail", result)

    @patch("scripts.validators.wiz_rescan.run_cmd")
    def test_timeout(self, mock_run_cmd):
        """Timed-out command — status=error, reason=scan_timeout."""
        mock_run_cmd.return_value = _cmd_result(
            exit_code=-1,
            stderr="Command timed out after 600 seconds",
        )
        result = run_wiz_scan(repo_dir="/repo", output_path="/tmp/wiz-out.json")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["reason"], "scan_timeout")

    @patch("scripts.validators.wiz_rescan.parse_wiz_scan_output")
    @patch("scripts.validators.wiz_rescan.run_cmd")
    def test_no_publish_flag_included(self, mock_run_cmd, mock_parse):
        """--no-publish must be in the command when no_publish=True."""
        mock_run_cmd.return_value = _cmd_result(exit_code=0)
        mock_parse.return_value = {"findings": [], "libraries": [], "metadata": {}}

        run_wiz_scan(repo_dir="/repo", output_path="/tmp/out.json", no_publish=True)

        args, _ = mock_run_cmd.call_args
        cmd = args[0]
        self.assertIn("--no-publish", cmd)

    @patch("scripts.validators.wiz_rescan.parse_wiz_scan_output")
    @patch("scripts.validators.wiz_rescan.run_cmd")
    def test_no_publish_flag_omitted_when_false(self, mock_run_cmd, mock_parse):
        """--no-publish must NOT be in the command when no_publish=False."""
        mock_run_cmd.return_value = _cmd_result(exit_code=0)
        mock_parse.return_value = {"findings": [], "libraries": [], "metadata": {}}

        run_wiz_scan(repo_dir="/repo", output_path="/tmp/out.json", no_publish=False)

        args, _ = mock_run_cmd.call_args
        cmd = args[0]
        self.assertNotIn("--no-publish", cmd)

    @patch("scripts.validators.wiz_rescan.parse_wiz_scan_output")
    @patch("scripts.validators.wiz_rescan.run_cmd")
    def test_command_is_list_form(self, mock_run_cmd, mock_parse):
        """run_cmd must always receive a list, never a string (injection safety)."""
        mock_run_cmd.return_value = _cmd_result(exit_code=0)
        mock_parse.return_value = {"findings": [], "libraries": [], "metadata": {}}

        run_wiz_scan(repo_dir="/repo", output_path="/tmp/out.json")

        args, _ = mock_run_cmd.call_args
        self.assertIsInstance(args[0], list)

    @patch("scripts.validators.wiz_rescan.run_cmd")
    def test_detail_truncated_to_500_chars(self, mock_run_cmd):
        """Failure detail must be at most 500 characters."""
        mock_run_cmd.return_value = _cmd_result(
            exit_code=1,
            stderr="x" * 1000,
        )
        result = run_wiz_scan(repo_dir="/repo", output_path="/tmp/out.json")
        self.assertLessEqual(len(result.get("detail", "")), 500)


# ---------------------------------------------------------------------------
# TestParseWizScanOutput
# ---------------------------------------------------------------------------

class TestParseWizScanOutput(TestCase):

    def test_valid_output(self):
        """Fixture with findings — correct findings and libraries extracted."""
        result = parse_wiz_scan_output(_SAMPLE_OUTPUT_PATH)

        self.assertIn("findings", result)
        self.assertIn("libraries", result)
        self.assertIn("metadata", result)

        self.assertEqual(len(result["findings"]), 4)
        self.assertEqual(len(result["libraries"]), 1)

        # Spot-check first finding (real WIZ schema uses compound ID)
        first = result["findings"][0]
        self.assertIn("WS-SQL-INJECT-001", first["id"])
        self.assertEqual(first["severity"], "CRITICAL")

        # Metadata keys present
        self.assertEqual(result["metadata"]["scan_id"], "006a6c39-d90b-88f3-8049-834991d18001")
        self.assertEqual(result["metadata"]["scan_status"], "SUCCESS")

    def test_empty_scan(self):
        """Fixture with no findings — empty lists returned."""
        result = parse_wiz_scan_output(_SAMPLE_EMPTY_PATH)

        self.assertEqual(result["findings"], [])
        self.assertEqual(result["libraries"], [])
        self.assertEqual(result["metadata"]["scan_id"], "empty-scan-456")
        self.assertEqual(result["metadata"]["scan_status"], "SUCCESS")

    def test_file_not_found(self):
        """Non-existent path — graceful empty result, no exception raised."""
        result = parse_wiz_scan_output("/nonexistent/path/wiz-scan.json")

        self.assertEqual(result["findings"], [])
        self.assertEqual(result["libraries"], [])
        self.assertEqual(result["metadata"], {})

    def test_invalid_json(self):
        """Malformed JSON file — graceful empty result, no exception raised."""
        bad_json_path = str(
            Path(__file__).resolve().parent.parent / "fixtures" / "_bad_json_tmp.json"
        )
        Path(bad_json_path).write_text("{not valid json", encoding="utf-8")
        try:
            result = parse_wiz_scan_output(bad_json_path)
            self.assertEqual(result["findings"], [])
        finally:
            Path(bad_json_path).unlink(missing_ok=True)

    def test_missing_result_block(self):
        """JSON missing 'result' key — returns empty findings without KeyError."""
        minimal_json = json.dumps({"id": "x", "status": "COMPLETED"})
        tmp_path = str(
            Path(__file__).resolve().parent.parent / "fixtures" / "_minimal_tmp.json"
        )
        Path(tmp_path).write_text(minimal_json, encoding="utf-8")
        try:
            result = parse_wiz_scan_output(tmp_path)
            self.assertEqual(result["findings"], [])
            self.assertEqual(result["libraries"], [])
        finally:
            Path(tmp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
