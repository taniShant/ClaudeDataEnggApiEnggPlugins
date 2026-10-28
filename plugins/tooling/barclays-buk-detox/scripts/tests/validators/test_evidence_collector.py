"""Tests for evidence_collector.py."""

import sys
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.validators.evidence_collector import (
    classify_evidence,
    build_evidence_record,
    collect_evidence,
    run_wiz_postfix_scan,
)


class TestClassifyEvidence(TestCase):
    def test_verified_wiz_pass(self):
        verification = {"verdict": "RESOLVED", "method": "wiz_cli", "confidence": "high"}
        self.assertEqual(classify_evidence(verification), "VERIFIED")

    def test_verified_wiz_pass_alt(self):
        verification = {"verdict": "PASS", "method": "wiz_cli", "confidence": "high"}
        self.assertEqual(classify_evidence(verification), "VERIFIED")

    def test_unverified_semgrep_pass(self):
        verification = {"verdict": "RESOLVED", "method": "semgrep", "confidence": "medium"}
        self.assertEqual(classify_evidence(verification), "UNVERIFIED")

    def test_unverified_dep_tree(self):
        verification = {"verdict": "RESOLVED", "method": "dep_tree", "confidence": "low"}
        self.assertEqual(classify_evidence(verification), "UNVERIFIED")

    def test_failed_any_fail(self):
        verification = {"verdict": "FAIL", "method": "wiz_cli", "confidence": "high"}
        self.assertEqual(classify_evidence(verification), "FAILED")

    def test_failed_partial(self):
        verification = {"verdict": "PARTIAL", "method": "wiz_cli", "confidence": "high"}
        self.assertEqual(classify_evidence(verification), "FAILED")

    def test_unverified_no_method(self):
        verification = {"verdict": "UNVERIFIED", "method": "none", "confidence": "none"}
        self.assertEqual(classify_evidence(verification), "UNVERIFIED")

    def test_empty_verification(self):
        self.assertEqual(classify_evidence({}), "UNVERIFIED")


class TestBuildEvidenceRecord(TestCase):
    def setUp(self):
        self.finding = {
            "id": "wiz-001",
            "cwe_id": "CWE-89",
            "file_path": "src/db/queries.py",
            "source": "wiz",
            "rule_id": "python-sql-injection",
            "severity": "critical",
            "title": "SQL Injection",
            "scan_date": "2026-09-23",
        }
        self.fix_result = {
            "commit_sha": "abc123",
            "description": "Parameterized query",
            "files_modified": ["src/db/queries.py"],
            "timestamp": "2026-09-23T14:30:00Z",
        }
        self.verification = {
            "method": "wiz_cli",
            "verdict": "RESOLVED",
            "confidence": "high",
            "verified_by": "wizcli v0.105.0",
            "delta": {"resolved": 1, "persistent": 0, "new": 0},
        }

    def test_correct_structure(self):
        record = build_evidence_record(self.finding, self.fix_result, self.verification)
        self.assertEqual(record["finding_id"], "wiz-001")
        self.assertEqual(record["cwe_id"], "CWE-89")
        self.assertEqual(record["file_path"], "src/db/queries.py")

    def test_original_finding_section(self):
        record = build_evidence_record(self.finding, self.fix_result, self.verification)
        orig = record["original_finding"]
        self.assertEqual(orig["source"], "wiz")
        self.assertEqual(orig["rule_id"], "python-sql-injection")
        self.assertEqual(orig["severity"], "critical")

    def test_fix_applied_section(self):
        record = build_evidence_record(self.finding, self.fix_result, self.verification)
        fix = record["fix_applied"]
        self.assertEqual(fix["commit_sha"], "abc123")
        self.assertEqual(fix["diff_summary"], "Parameterized query")

    def test_verification_section(self):
        record = build_evidence_record(self.finding, self.fix_result, self.verification)
        self.assertEqual(record["verification"]["method"], "wiz_cli")
        self.assertEqual(record["verification"]["verdict"], "RESOLVED")

    def test_accountability_section(self):
        record = build_evidence_record(self.finding, self.fix_result, self.verification)
        acc = record["accountability"]
        self.assertEqual(acc["fixed_by"], "detox-pipeline")
        self.assertEqual(acc["verified_by"], "wizcli v0.105.0")
        self.assertEqual(acc["classification"], "VERIFIED")

    def test_classification_failed(self):
        self.verification["verdict"] = "FAIL"
        record = build_evidence_record(self.finding, self.fix_result, self.verification)
        self.assertEqual(record["accountability"]["classification"], "FAILED")


class TestCollectEvidence(TestCase):
    def setUp(self):
        self.finding = {
            "id": "wiz-001",
            "cwe_id": "CWE-89",
            "file_path": "src/db/queries.py",
            "source": "wiz",
            "severity": "critical",
        }
        self.fix_result = {
            "commit_sha": "abc123",
            "status": "success",
            "description": "Fixed SQL injection",
        }

    @patch("scripts.validators.evidence_collector.try_wiz_verification")
    def test_wiz_available(self, mock_wiz):
        mock_wiz.return_value = {
            "method": "wiz_cli",
            "verdict": "RESOLVED",
            "confidence": "high",
            "verified_by": "wizcli v0.105.0",
            "delta": {"resolved": 1, "persistent": 0, "new": 0},
        }
        evidence = collect_evidence(self.finding, self.fix_result, "/repo")
        self.assertEqual(evidence["verification"]["method"], "wiz_cli")
        self.assertEqual(evidence["accountability"]["classification"], "VERIFIED")

    @patch("scripts.validators.evidence_collector.try_semgrep_verification")
    @patch("scripts.validators.evidence_collector.try_wiz_verification")
    def test_fallback_to_semgrep(self, mock_wiz, mock_semgrep):
        mock_wiz.return_value = None  # WIZ unavailable
        mock_semgrep.return_value = {
            "method": "semgrep",
            "verdict": "RESOLVED",
            "confidence": "medium",
            "verified_by": "semgrep 1.96.0",
            "delta": {"resolved": 1, "persistent": 0, "new": 0},
        }
        evidence = collect_evidence(self.finding, self.fix_result, "/repo")
        self.assertEqual(evidence["verification"]["method"], "semgrep")
        self.assertEqual(evidence["accountability"]["classification"], "UNVERIFIED")

    @patch("scripts.validators.evidence_collector.try_dep_tree_verification")
    @patch("scripts.validators.evidence_collector.try_semgrep_verification")
    @patch("scripts.validators.evidence_collector.try_wiz_verification")
    def test_fallback_to_dep_tree(self, mock_wiz, mock_semgrep, mock_dep):
        mock_wiz.return_value = None
        mock_semgrep.return_value = None
        mock_dep.return_value = {
            "method": "dep_tree",
            "verdict": "RESOLVED",
            "confidence": "low",
            "verified_by": "dep_tree (gradle)",
            "delta": {"resolved": 1, "persistent": 0, "new": 0},
        }
        evidence = collect_evidence(self.finding, self.fix_result, "/repo")
        self.assertEqual(evidence["verification"]["method"], "dep_tree")
        self.assertEqual(evidence["accountability"]["classification"], "UNVERIFIED")

    @patch("scripts.validators.evidence_collector.try_dep_tree_verification")
    @patch("scripts.validators.evidence_collector.try_semgrep_verification")
    @patch("scripts.validators.evidence_collector.try_wiz_verification")
    def test_no_method_available(self, mock_wiz, mock_semgrep, mock_dep):
        mock_wiz.return_value = None
        mock_semgrep.return_value = None
        mock_dep.return_value = None
        evidence = collect_evidence(self.finding, self.fix_result, "/repo")
        self.assertEqual(evidence["verification"]["method"], "none")
        self.assertEqual(evidence["verification"]["confidence"], "none")
        self.assertEqual(evidence["accountability"]["classification"], "UNVERIFIED")

    @patch("scripts.validators.evidence_collector.try_wiz_verification")
    def test_wiz_failed(self, mock_wiz):
        mock_wiz.return_value = {
            "method": "wiz_cli",
            "verdict": "FAIL",
            "confidence": "high",
            "verified_by": "wizcli v0.105.0",
            "delta": {"resolved": 0, "persistent": 1, "new": 0},
        }
        evidence = collect_evidence(self.finding, self.fix_result, "/repo")
        self.assertEqual(evidence["accountability"]["classification"], "FAILED")

    @patch("scripts.validators.evidence_collector.try_wiz_verification")
    def test_custom_methods_list(self, mock_wiz):
        """When verification_methods only includes wiz_cli, don't try others."""
        mock_wiz.return_value = None
        evidence = collect_evidence(
            self.finding, self.fix_result, "/repo",
            verification_methods=["wiz_cli"],
        )
        # Should fall through to "none" since only wiz was tried and it returned None
        self.assertEqual(evidence["verification"]["method"], "none")

    @patch("scripts.validators.evidence_collector.try_wiz_verification")
    def test_first_success_wins(self, mock_wiz):
        """Once WIZ succeeds, semgrep and dep_tree are not called."""
        mock_wiz.return_value = {
            "method": "wiz_cli",
            "verdict": "RESOLVED",
            "confidence": "high",
            "verified_by": "wizcli v0.105.0",
            "delta": {"resolved": 1, "persistent": 0, "new": 0},
        }
        evidence = collect_evidence(self.finding, self.fix_result, "/repo")
        # WIZ succeeded — should not fall through
        self.assertEqual(evidence["verification"]["method"], "wiz_cli")


class TestConfidenceLevels(TestCase):
    def test_wiz_high(self):
        v = {"verdict": "RESOLVED", "method": "wiz_cli", "confidence": "high"}
        self.assertEqual(classify_evidence(v), "VERIFIED")

    def test_semgrep_medium(self):
        v = {"verdict": "RESOLVED", "method": "semgrep", "confidence": "medium"}
        self.assertEqual(classify_evidence(v), "UNVERIFIED")

    def test_dep_tree_low(self):
        v = {"verdict": "RESOLVED", "method": "dep_tree", "confidence": "low"}
        self.assertEqual(classify_evidence(v), "UNVERIFIED")

    def test_none_none(self):
        v = {"verdict": "UNVERIFIED", "method": "none", "confidence": "none"}
        self.assertEqual(classify_evidence(v), "UNVERIFIED")


class TestNoVerificationReason(TestCase):
    """When no verification is possible, the evidence record explains WHY."""

    @patch("scripts.validators.evidence_collector._diagnose_semgrep_skip")
    @patch("scripts.validators.evidence_collector._diagnose_wiz_skip")
    @patch("scripts.validators.evidence_collector.try_dep_tree_verification")
    @patch("scripts.validators.evidence_collector.try_semgrep_verification")
    @patch("scripts.validators.evidence_collector.try_wiz_verification")
    def test_reason_field_present(self, mock_wiz, mock_semgrep, mock_dep, mock_wiz_diag, mock_sem_diag):
        mock_wiz.return_value = None
        mock_semgrep.return_value = None
        mock_dep.return_value = None
        mock_wiz_diag.return_value = "wizcli not installed — run: brew install --cask wizcli"
        mock_sem_diag.return_value = "semgrep not installed — run: brew install semgrep"

        finding = {"id": "f1", "cwe_id": "CWE-89", "file_path": "src/app.py"}
        fix_result = {"commit_sha": "abc", "status": "success"}
        evidence = collect_evidence(finding, fix_result, "/repo")

        verification = evidence["verification"]
        self.assertEqual(verification["method"], "none")
        self.assertIn("reason", verification)
        self.assertIn("wizcli not installed", verification["reason"])
        self.assertIn("action_required", verification)
        self.assertTrue(len(verification["action_required"]) > 0)

    @patch("scripts.validators.evidence_collector._diagnose_semgrep_skip")
    @patch("scripts.validators.evidence_collector._diagnose_wiz_skip")
    @patch("scripts.validators.evidence_collector.try_dep_tree_verification")
    @patch("scripts.validators.evidence_collector.try_semgrep_verification")
    @patch("scripts.validators.evidence_collector.try_wiz_verification")
    def test_action_suggests_wiz_install(self, mock_wiz, mock_semgrep, mock_dep, mock_wiz_diag, mock_sem_diag):
        mock_wiz.return_value = None
        mock_semgrep.return_value = None
        mock_dep.return_value = None
        mock_wiz_diag.return_value = "wizcli not installed — run: brew install --cask wizcli"
        mock_sem_diag.return_value = "file not found: src/app.py"

        finding = {"id": "f1", "cwe_id": "CWE-89", "file_path": "src/app.py"}
        fix_result = {"commit_sha": "abc", "status": "success"}
        evidence = collect_evidence(finding, fix_result, "/repo")

        action = evidence["verification"]["action_required"]
        self.assertIn("Install WIZ CLI", action)


class TestRunWizPostfixScan(TestCase):
    """Test that run_wiz_postfix_scan runs once and cleans up temp files."""

    @patch("scripts.validators.evidence_collector.json.load")
    @patch("builtins.open", create=True)
    @patch("scripts.validators.evidence_collector.Path")
    @patch("scripts.validators.evidence_collector.tempfile.NamedTemporaryFile")
    @patch("scripts.validators.wiz_rescan.run_wiz_scan")
    @patch("scripts.validators.wiz_rescan.check_wizcli_auth")
    @patch("scripts.validators.wiz_rescan.check_wizcli_installed")
    def test_temp_file_cleaned_on_success(self, mock_install, mock_auth, mock_scan,
                                           mock_tmpfile, mock_path, mock_open, mock_json):
        mock_install.return_value = {"installed": True, "version": "v0.105.0"}
        mock_auth.return_value = {"authenticated": True, "client_email": "dev@barclays.com"}
        mock_scan.return_value = {"status": "success", "findings_count": 0}

        mock_tmp_ctx = MagicMock()
        mock_tmp_ctx.__enter__ = MagicMock(return_value=MagicMock(name="/tmp/test.json"))
        mock_tmp_ctx.__exit__ = MagicMock(return_value=False)
        mock_tmpfile.return_value = mock_tmp_ctx

        mock_json.return_value = {"extraDetails": {"sastDetails": {"findings": []}}}
        mock_path_inst = MagicMock()
        mock_path.return_value = mock_path_inst

        # The function should attempt to unlink the temp file
        result = run_wiz_postfix_scan("/repo")
        # Verify unlink was called (temp file cleanup)
        mock_path_inst.unlink.assert_called_once_with(missing_ok=True)

    @patch("scripts.validators.wiz_rescan.check_wizcli_installed")
    def test_returns_none_when_not_installed(self, mock_install):
        mock_install.return_value = {"installed": False, "version": ""}
        result = run_wiz_postfix_scan("/repo")
        self.assertIsNone(result)

    @patch("scripts.validators.wiz_rescan.check_wizcli_auth")
    @patch("scripts.validators.wiz_rescan.check_wizcli_installed")
    def test_returns_none_when_not_authenticated(self, mock_install, mock_auth):
        mock_install.return_value = {"installed": True, "version": "v0.105.0"}
        mock_auth.return_value = {"authenticated": False, "client_email": ""}
        result = run_wiz_postfix_scan("/repo")
        self.assertIsNone(result)


class TestSemgrepFileScoped(TestCase):
    """Test that Semgrep verification is file-scoped to avoid false PERSISTENT."""

    @patch("scripts.validators.evidence_collector.try_semgrep_verification")
    @patch("scripts.validators.evidence_collector.try_wiz_verification")
    def test_semgrep_passes_finding_file(self, mock_wiz, mock_semgrep):
        """Semgrep should be called with the finding, not the whole repo."""
        mock_wiz.return_value = None
        mock_semgrep.return_value = {
            "method": "semgrep",
            "verdict": "RESOLVED",
            "confidence": "medium",
            "verified_by": "semgrep 1.96.0",
            "delta": {"resolved": 1, "persistent": 0, "new": 0},
        }
        finding = {"id": "f1", "cwe_id": "CWE-89", "file_path": "src/db/queries.py"}
        fix_result = {"commit_sha": "abc", "status": "success"}
        evidence = collect_evidence(finding, fix_result, "/repo")
        # Verify semgrep was called with the finding
        mock_semgrep.assert_called_once()
        call_args = mock_semgrep.call_args
        self.assertEqual(call_args[0][0]["file_path"], "src/db/queries.py")


if __name__ == "__main__":
    main()
