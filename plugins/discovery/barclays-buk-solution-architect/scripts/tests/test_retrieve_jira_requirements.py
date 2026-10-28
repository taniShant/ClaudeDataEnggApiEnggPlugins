"""
Tests for deterministic Jira requirements retrieval.

Uses static fixtures — no real Jira connection required.
"""

import sys
import os
import json
import hashlib
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone
from unittest import TestCase, main
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.retrieve_jira_requirements import normalize_requirements, fetch_jira_raw


class TestNormalizeRequirements(TestCase):
    """Test deterministic normalization of Jira responses."""

    def setUp(self):
        """Load fixtures and create temporary output directory."""
        fixtures_dir = Path(__file__).parent / "fixtures"
        with open(fixtures_dir / "sample_jira_issue.json") as f:
            self.sample_jira = json.load(f)
        with open(fixtures_dir / "expected_requirements.json") as f:
            self.expected_requirements = json.load(f)
        # Use temp directory for output (not git repo)
        self.temp_dir = tempfile.mkdtemp(prefix="buk_sa_test_")
        self.output_dir = Path(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_deterministic_normalization(self):
        """Same input produces same output (determinism)."""
        output1 = normalize_requirements(
            raw_jira_json=self.sample_jira,
            allowed_fields=["summary", "description", "labels", "components", "status", "issuetype", "issuelinks"],
            acceptance_criteria_field_id=None,
            timestamp_iso="2026-10-01T15:30:45.123456+00:00",
            instance="estjira.barcapint.com",
            issue_key="BUKL2CUSX-173655",
            raw_file_path=self.output_dir / "raw" / "BUKL2CUSX-173655.json",
            raw_response_sha256="abc123def456789",
            output_dir=self.output_dir
        )
        output2 = normalize_requirements(
            raw_jira_json=self.sample_jira,
            allowed_fields=["summary", "description", "labels", "components", "status", "issuetype", "issuelinks"],
            acceptance_criteria_field_id=None,
            timestamp_iso="2026-10-01T15:30:45.123456+00:00",
            instance="estjira.barcapint.com",
            issue_key="BUKL2CUSX-173655",
            raw_file_path=self.output_dir / "raw" / "BUKL2CUSX-173655.json",
            raw_response_sha256="abc123def456789",
            output_dir=self.output_dir
        )
        self.assertEqual(output1, output2)

    def test_produces_expected_structure(self):
        """Output matches expected requirements schema."""
        output = normalize_requirements(
            raw_jira_json=self.sample_jira,
            allowed_fields=["summary", "description", "labels", "components", "status", "issuetype", "issuelinks"],
            acceptance_criteria_field_id=None,
            timestamp_iso="2026-10-01T15:30:45.123456+00:00",
            instance="estjira.barcapint.com",
            issue_key="BUKL2CUSX-173655",
            raw_file_path=self.output_dir / "raw" / "BUKL2CUSX-173655.json",
            raw_response_sha256="abc123def456789",
            output_dir=self.output_dir
        )

        # Check schema_version
        self.assertEqual(output["schema_version"], "1.0")

        # Check source structure
        self.assertIn("source", output)
        source = output["source"]
        self.assertEqual(source["type"], "jira")
        self.assertEqual(source["instance"], "estjira.barcapint.com")
        self.assertEqual(source["issue_key"], "BUKL2CUSX-173655")
        self.assertEqual(source["endpoint"], "/rest/api/2/issue/{issue_key}")
        self.assertIn("retrieved_at", source)
        self.assertIn("requested_fields", source)
        self.assertIn("raw_response_file", source)
        self.assertIn("raw_response_sha256", source)

        # Check requirements structure
        self.assertIn("requirements", output)
        req = output["requirements"]
        self.assertIn("summary", req)
        self.assertIn("description", req)
        self.assertIn("type", req)
        self.assertIn("status", req)
        self.assertIn("labels", req)
        self.assertIn("components", req)
        self.assertIn("linked_issues", req)
        self.assertIn("acceptance_criteria", req)

    def test_no_inference_missing_fields(self):
        """Missing fields in raw Jira remain missing in requirements."""
        jira_minimal = {
            "fields": {
                "summary": "Test issue"
            }
        }
        output = normalize_requirements(
            raw_jira_json=jira_minimal,
            allowed_fields=["summary"],
            acceptance_criteria_field_id=None,
            timestamp_iso="2026-10-01T15:30:45.123456+00:00",
            instance="estjira.barcapint.com",
            issue_key="TEST-1",
            raw_file_path=self.output_dir / "raw" / "TEST-1.json",
            raw_response_sha256="test123",
            output_dir=self.output_dir
        )

        req = output["requirements"]
        self.assertEqual(req["summary"], "Test issue")
        self.assertEqual(req["description"], "")
        self.assertEqual(req["type"], "")
        self.assertEqual(req["status"], "")
        self.assertEqual(req["labels"], [])
        self.assertEqual(req["components"], [])
        self.assertEqual(req["linked_issues"], [])
        self.assertEqual(req["acceptance_criteria"], [])

    def test_sorted_fields(self):
        """Labels, components, and linked issues are sorted."""
        output = normalize_requirements(
            raw_jira_json=self.sample_jira,
            allowed_fields=["summary", "description", "labels", "components", "status", "issuetype", "issuelinks"],
            acceptance_criteria_field_id=None,
            timestamp_iso="2026-10-01T15:30:45.123456+00:00",
            instance="estjira.barcapint.com",
            issue_key="BUKL2CUSX-173655",
            raw_file_path=self.output_dir / "raw" / "BUKL2CUSX-173655.json",
            raw_response_sha256="abc123def456789",
            output_dir=self.output_dir
        )

        req = output["requirements"]
        # Labels should be sorted
        self.assertEqual(req["labels"], sorted(req["labels"]))
        # Components should be sorted
        self.assertEqual(req["components"], sorted(req["components"]))
        # Linked issues should be sorted by issue_key
        issue_keys = [li["issue_key"] for li in req["linked_issues"]]
        self.assertEqual(issue_keys, sorted(issue_keys))

    def test_acceptance_criteria_not_configured(self):
        """When acceptance criteria field not configured, warning is added."""
        output = normalize_requirements(
            raw_jira_json=self.sample_jira,
            allowed_fields=["summary"],
            acceptance_criteria_field_id=None,
            timestamp_iso="2026-10-01T15:30:45.123456+00:00",
            instance="estjira.barcapint.com",
            issue_key="BUKL2CUSX-173655",
            raw_file_path=self.output_dir / "raw" / "BUKL2CUSX-173655.json",
            raw_response_sha256="abc123def456789",
            output_dir=self.output_dir
        )

        warnings = output["warnings"]
        self.assertGreater(len(warnings), 0)
        self.assertTrue(any("Acceptance criteria" in w for w in warnings))

    def test_acceptance_criteria_extracted(self):
        """When acceptance criteria field is configured, it is extracted."""
        output = normalize_requirements(
            raw_jira_json=self.sample_jira,
            allowed_fields=["summary"],
            acceptance_criteria_field_id="customfield_12345",
            timestamp_iso="2026-10-01T15:30:45.123456+00:00",
            instance="estjira.barcapint.com",
            issue_key="BUKL2CUSX-173655",
            raw_file_path=self.output_dir / "raw" / "BUKL2CUSX-173655.json",
            raw_response_sha256="abc123def456789",
            output_dir=self.output_dir
        )

        req = output["requirements"]
        # customfield_12345 in fixture contains multiline text
        ac = req["acceptance_criteria"]
        self.assertEqual(len(ac), 1)
        self.assertIn("Acceptance criteria", ac[0])

    def test_requested_fields_sorted(self):
        """Requested fields are sorted in provenance."""
        output = normalize_requirements(
            raw_jira_json=self.sample_jira,
            allowed_fields=["summary", "labels", "description"],
            acceptance_criteria_field_id=None,
            timestamp_iso="2026-10-01T15:30:45.123456+00:00",
            instance="estjira.barcapint.com",
            issue_key="BUKL2CUSX-173655",
            raw_file_path=self.output_dir / "raw" / "BUKL2CUSX-173655.json",
            raw_response_sha256="abc123def456789",
            output_dir=self.output_dir
        )

        fields = output["source"]["requested_fields"]
        self.assertEqual(fields, sorted(fields))

    def test_empty_issuelinks_handled(self):
        """Empty or malformed issuelinks don't crash."""
        jira_no_links = dict(self.sample_jira)
        jira_no_links["fields"] = dict(self.sample_jira["fields"])
        jira_no_links["fields"]["issuelinks"] = []

        output = normalize_requirements(
            raw_jira_json=jira_no_links,
            allowed_fields=["issuelinks"],
            acceptance_criteria_field_id=None,
            timestamp_iso="2026-10-01T15:30:45.123456+00:00",
            instance="estjira.barcapint.com",
            issue_key="BUKL2CUSX-173655",
            raw_file_path=self.output_dir / "raw" / "BUKL2CUSX-173655.json",
            raw_response_sha256="abc123def456789",
            output_dir=self.output_dir
        )

        self.assertEqual(output["requirements"]["linked_issues"], [])

    def test_malformed_labels_fails_explicitly(self):
        """If labels is not a list, normalization fails explicitly."""
        jira_bad_labels = dict(self.sample_jira)
        jira_bad_labels["fields"] = dict(self.sample_jira["fields"])
        jira_bad_labels["fields"]["labels"] = "not-a-list"

        with self.assertRaises(ValueError) as cm:
            normalize_requirements(
                raw_jira_json=jira_bad_labels,
                allowed_fields=["labels"],
                acceptance_criteria_field_id=None,
                timestamp_iso="2026-10-01T15:30:45.123456+00:00",
                instance="estjira.barcapint.com",
                issue_key="BUKL2CUSX-173655",
                raw_file_path=self.output_dir / "raw" / "BUKL2CUSX-173655.json",
                raw_response_sha256="abc123def456789",
                output_dir=self.output_dir
            )
        self.assertIn("labels", str(cm.exception))

    def test_malformed_components_fails_explicitly(self):
        """If components is not a list, normalization fails explicitly."""
        jira_bad_components = dict(self.sample_jira)
        jira_bad_components["fields"] = dict(self.sample_jira["fields"])
        jira_bad_components["fields"]["components"] = "not-a-list"

        with self.assertRaises(ValueError) as cm:
            normalize_requirements(
                raw_jira_json=jira_bad_components,
                allowed_fields=["components"],
                acceptance_criteria_field_id=None,
                timestamp_iso="2026-10-01T15:30:45.123456+00:00",
                instance="estjira.barcapint.com",
                issue_key="BUKL2CUSX-173655",
                raw_file_path=self.output_dir / "raw" / "BUKL2CUSX-173655.json",
                raw_response_sha256="abc123def456789",
                output_dir=self.output_dir
            )
        self.assertIn("components", str(cm.exception))

    def test_raw_response_sha256_preserved(self):
        """SHA-256 is exactly as provided."""
        sha256_value = "deadbeef" * 8  # 64-char hex string

        output = normalize_requirements(
            raw_jira_json=self.sample_jira,
            allowed_fields=["summary"],
            acceptance_criteria_field_id=None,
            timestamp_iso="2026-10-01T15:30:45.123456+00:00",
            instance="estjira.barcapint.com",
            issue_key="BUKL2CUSX-173655",
            raw_file_path=self.output_dir / "raw" / "BUKL2CUSX-173655.json",
            raw_response_sha256=sha256_value,
            output_dir=self.output_dir
        )

        self.assertEqual(output["source"]["raw_response_sha256"], sha256_value)

    def test_provenance_immutable_across_calls(self):
        """Provenance fields are always present and consistent."""
        for i in range(3):
            output = normalize_requirements(
                raw_jira_json=self.sample_jira,
                allowed_fields=["summary"],
                acceptance_criteria_field_id=None,
                timestamp_iso="2026-10-01T15:30:45.123456+00:00",
                instance="estjira.barcapint.com",
                issue_key="BUKL2CUSX-173655",
                raw_file_path=self.output_dir / "raw" / "BUKL2CUSX-173655.json",
                raw_response_sha256="abc123def456789",
                output_dir=self.output_dir
            )

            source = output["source"]
            self.assertEqual(source["instance"], "estjira.barcapint.com")
            self.assertEqual(source["issue_key"], "BUKL2CUSX-173655")
            self.assertEqual(source["endpoint"], "/rest/api/2/issue/{issue_key}")

    def test_invalid_jira_response_structure_fails(self):
        """If raw response is not a dict, normalization fails explicitly."""
        with self.assertRaises(ValueError) as cm:
            normalize_requirements(
                raw_jira_json="not a dict",
                allowed_fields=["summary"],
                acceptance_criteria_field_id=None,
                timestamp_iso="2026-10-01T15:30:45.123456+00:00",
                instance="estjira.barcapint.com",
                issue_key="TEST-1",
                raw_file_path=self.output_dir / "raw" / "TEST-1.json",
                raw_response_sha256="test123",
                output_dir=self.output_dir
            )
        self.assertIn("dict", str(cm.exception))

    def test_invalid_fields_dict_fails(self):
        """If 'fields' key is not a dict, normalization fails explicitly."""
        with self.assertRaises(ValueError) as cm:
            normalize_requirements(
                raw_jira_json={"fields": "not a dict"},
                allowed_fields=["summary"],
                acceptance_criteria_field_id=None,
                timestamp_iso="2026-10-01T15:30:45.123456+00:00",
                instance="estjira.barcapint.com",
                issue_key="TEST-1",
                raw_file_path=self.output_dir / "raw" / "TEST-1.json",
                raw_response_sha256="test123",
                output_dir=self.output_dir
            )
        self.assertIn("fields", str(cm.exception))


class TestFetchJiraRawSSL(TestCase):
    """Test SSL and transport error handling in fetch_jira_raw."""

    @patch("scripts.retrieve_jira_requirements.subprocess.run")
    def test_ssl_no_revoke_flag_passed_to_curl(self, mock_run):
        """Verify --ssl-no-revoke is passed to curl when ssl_no_revoke=True."""
        # Mock a successful curl response
        mock_result = MagicMock()
        mock_result.stdout = b'{"fields":{}}\n200'
        mock_result.stderr = b""
        mock_run.return_value = mock_result

        os.environ["JIRA_AUTH_TOKEN"] = "test-token"
        try:
            fetch_jira_raw("TEST-1", ["summary"], ssl_no_revoke=True)
        except Exception:
            pass  # We only care about the curl command, not the result

        # Verify curl was called with --ssl-no-revoke
        mock_run.assert_called_once()
        curl_cmd = mock_run.call_args[0][0]
        self.assertIn("--ssl-no-revoke", curl_cmd)

    @patch("scripts.retrieve_jira_requirements.subprocess.run")
    def test_ssl_no_revoke_defaults_to_false(self, mock_run):
        """Verify --ssl-no-revoke is NOT passed by default."""
        # Mock a successful curl response
        mock_result = MagicMock()
        mock_result.stdout = b'{"fields":{}}\n200'
        mock_result.stderr = b""
        mock_run.return_value = mock_result

        os.environ["JIRA_AUTH_TOKEN"] = "test-token"
        try:
            fetch_jira_raw("TEST-1", ["summary"])  # ssl_no_revoke not provided (defaults to False)
        except Exception:
            pass

        # Verify curl was called WITHOUT --ssl-no-revoke
        mock_run.assert_called_once()
        curl_cmd = mock_run.call_args[0][0]
        self.assertNotIn("--ssl-no-revoke", curl_cmd)

    @patch("scripts.retrieve_jira_requirements.subprocess.run")
    def test_curl_stderr_reported_on_transport_failure(self, mock_run):
        """Verify curl stderr is reported when HTTP code cannot be parsed (transport error)."""
        # Mock curl failure: stderr contains Schannel error, stdout is invalid
        schannel_error = b"schannel: next InitializeSecurityContext failed: CRYPT_E_NO_REVOCATION_CHECK"
        mock_result = MagicMock()
        mock_result.stdout = b"garbage output"  # Invalid HTTP code
        mock_result.stderr = schannel_error
        mock_run.return_value = mock_result

        os.environ["JIRA_AUTH_TOKEN"] = "test-token"
        with self.assertRaises(RuntimeError) as cm:
            fetch_jira_raw("TEST-1", ["summary"], ssl_no_revoke=False)

        # Verify error message includes curl stderr
        error_msg = str(cm.exception)
        self.assertIn("curl stderr", error_msg)
        self.assertIn("CRYPT_E_NO_REVOCATION_CHECK", error_msg)


class TestMainIntegration(TestCase):
    """Integration test: verify main() doesn't crash and uses correct workspace paths."""

    def setUp(self):
        """Create temporary output directory."""
        self.temp_dir = tempfile.mkdtemp(prefix="buk_sa_main_test_")
        self.output_dir = Path(self.temp_dir)

        # Load fixture
        fixtures_dir = Path(__file__).parent / "fixtures"
        with open(fixtures_dir / "sample_jira_issue.json") as f:
            self.sample_jira_json = json.dumps(json.load(f)).encode("utf-8")

    def tearDown(self):
        """Clean up temporary directory."""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch("scripts.retrieve_jira_requirements.fetch_jira_raw")
    def test_main_uses_output_dir_not_git_root(self, mock_fetch):
        """Regression test: main() should use output_dir, not git_root."""
        # Mock fetch_jira_raw to return sample data
        mock_fetch.return_value = (
            self.sample_jira_json,
            "2026-10-01T15:30:45.123456+00:00",
            "OK"
        )

        os.environ["JIRA_AUTH_TOKEN"] = "test-token"

        # Import here to avoid import-time side effects
        from scripts.retrieve_jira_requirements import main as retrieve_main

        # Capture stderr to verify no NameError about git_root
        from io import StringIO
        old_stderr = sys.stderr
        sys.stderr = StringIO()

        try:
            # Call main with explicit invocation-dir
            test_args = [
                "retrieve_jira_requirements.py",
                "--issue-key", "TEST-123",
                "--invocation-dir", str(self.output_dir),
                "--allowed-fields", "summary,description",
            ]
            with patch("sys.argv", test_args):
                exit_code = retrieve_main()

            # Should succeed (exit code 0)
            self.assertEqual(exit_code, 0)

            # Verify output files were created in issue-key subdirectories
            raw_file = self.output_dir / "TEST-123" / "raw" / "TEST-123.json"
            req_file = self.output_dir / "TEST-123" / "requirements" / "TEST-123.json"
            self.assertTrue(raw_file.exists(), f"Raw file not created: {raw_file}")
            self.assertTrue(req_file.exists(), f"Requirements file not created: {req_file}")

            # Verify stderr contains workspace-relative paths (not git_root error)
            stderr_output = sys.stderr.getvalue()
            self.assertNotIn("NameError", stderr_output)
            self.assertNotIn("git_root", stderr_output)
            self.assertIn("✓ Raw response saved to", stderr_output)
            self.assertIn("✓ Requirements saved to", stderr_output)

        finally:
            sys.stderr = old_stderr
            if "JIRA_AUTH_TOKEN" in os.environ:
                del os.environ["JIRA_AUTH_TOKEN"]


if __name__ == "__main__":
    main()
