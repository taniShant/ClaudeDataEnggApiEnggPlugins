"""Tests for scan_metadata.py — uses real WIZ CloudEvent JSON schema."""

import json
import sys
from pathlib import Path
from unittest import TestCase, main

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.validators.scan_metadata import (
    extract_metadata,
    extract_finding_summary,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestExtractMetadata(TestCase):
    def setUp(self):
        with open(FIXTURES_DIR / "sample_wiz_scan_output.json") as f:
            self.scan_data = json.load(f)

    def test_scan_id(self):
        meta = extract_metadata(self.scan_data)
        self.assertEqual(meta["scan_id"], "006a6c39-d90b-88f3-8049-834991d18001")

    def test_scan_status(self):
        meta = extract_metadata(self.scan_data)
        self.assertEqual(meta["scan_status"], "SUCCESS")

    def test_started_at(self):
        meta = extract_metadata(self.scan_data)
        self.assertTrue(meta["started_at"].startswith("2026-"))

    def test_completed_at(self):
        meta = extract_metadata(self.scan_data)
        self.assertTrue(meta["completed_at"].startswith("2026-"))

    def test_policy_result_failed(self):
        meta = extract_metadata(self.scan_data)
        self.assertEqual(meta["policy_result"], "FAILED")

    def test_policies_list(self):
        meta = extract_metadata(self.scan_data)
        # 1 failed + 1 passed = 2 policies
        self.assertEqual(len(meta["policies"]), 2)
        names = {p["name"] for p in meta["policies"]}
        self.assertIn("Barclays vulnerabilities policy", names)

    def test_empty_scan(self):
        meta = extract_metadata({})
        self.assertEqual(meta["scan_id"], "")
        self.assertEqual(meta["scan_status"], "UNKNOWN")
        self.assertEqual(meta["policy_result"], "PASSED")  # no failed policies = passed
        self.assertEqual(meta["policies"], [])

    def test_empty_scan_from_fixture(self):
        with open(FIXTURES_DIR / "sample_wiz_scan_empty.json") as f:
            empty_data = json.load(f)
        meta = extract_metadata(empty_data)
        self.assertEqual(meta["policy_result"], "PASSED")  # no failed policies


class TestExtractFindingSummary(TestCase):
    def setUp(self):
        with open(FIXTURES_DIR / "sample_wiz_scan_output.json") as f:
            self.scan_data = json.load(f)

    def test_total_count(self):
        summary = extract_finding_summary(self.scan_data)
        # 4 SAST + 1 library = 5
        self.assertEqual(summary["total_findings"], 5)
        self.assertEqual(summary["code_findings"], 4)
        self.assertEqual(summary["library_findings"], 1)

    def test_by_severity(self):
        summary = extract_finding_summary(self.scan_data)
        self.assertEqual(summary["by_severity"]["CRITICAL"], 1)
        self.assertEqual(summary["by_severity"]["HIGH"], 2)
        self.assertEqual(summary["by_severity"]["MEDIUM"], 1)

    def test_by_cwe_from_weaknesses(self):
        """CWE extracted from finding.weaknesses[].id — the real WIZ schema."""
        summary = extract_finding_summary(self.scan_data)
        self.assertEqual(summary["by_cwe"]["CWE-89"], 2)
        self.assertEqual(summary["by_cwe"]["CWE-79"], 1)
        self.assertEqual(summary["by_cwe"]["CWE-798"], 1)

    def test_by_file(self):
        summary = extract_finding_summary(self.scan_data)
        self.assertEqual(summary["by_file"]["src/db/queries.py"], 2)
        self.assertEqual(summary["by_file"]["src/web/views.py"], 1)

    def test_empty_scan(self):
        summary = extract_finding_summary({})
        self.assertEqual(summary["total_findings"], 0)
        self.assertEqual(summary["code_findings"], 0)
        self.assertEqual(summary["by_severity"], {})
        self.assertEqual(summary["by_cwe"], {})

    def test_empty_scan_from_fixture(self):
        with open(FIXTURES_DIR / "sample_wiz_scan_empty.json") as f:
            empty_data = json.load(f)
        summary = extract_finding_summary(empty_data)
        self.assertEqual(summary["total_findings"], 0)
        self.assertEqual(summary["code_findings"], 0)


if __name__ == "__main__":
    main()
