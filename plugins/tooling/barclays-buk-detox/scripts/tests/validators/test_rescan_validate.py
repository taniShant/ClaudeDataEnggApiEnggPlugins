"""Tests for rescan_validate.py."""

import sys
from pathlib import Path
from unittest import TestCase, main

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.validators.rescan_validate import (
    normalize_cwe_for_match,
    finding_matches_cwe,
    compare_findings,
    determine_verdict,
)


class TestNormalizeCWEForMatch(TestCase):
    def test_standard(self):
        self.assertEqual(normalize_cwe_for_match("CWE-89"), "CWE-89")

    def test_leading_zeros(self):
        self.assertEqual(normalize_cwe_for_match("CWE-089"), "CWE-89")

    def test_lowercase(self):
        self.assertEqual(normalize_cwe_for_match("cwe-89"), "CWE-89")

    def test_no_hyphen(self):
        self.assertEqual(normalize_cwe_for_match("CWE89"), "CWE-89")


class TestFindingMatchesCWE(TestCase):
    def test_match(self):
        finding = {
            "extra": {"metadata": {"cwe": ["CWE-89: SQL Injection"]}}
        }
        self.assertTrue(finding_matches_cwe(finding, "CWE-89"))

    def test_no_match(self):
        finding = {
            "extra": {"metadata": {"cwe": ["CWE-79: XSS"]}}
        }
        self.assertFalse(finding_matches_cwe(finding, "CWE-89"))

    def test_empty_cwe(self):
        finding = {"extra": {"metadata": {"cwe": []}}}
        self.assertFalse(finding_matches_cwe(finding, "CWE-89"))

    def test_missing_metadata(self):
        finding = {"extra": {}}
        self.assertFalse(finding_matches_cwe(finding, "CWE-89"))


class TestCompareFindings(TestCase):
    def test_all_resolved(self):
        baseline = [
            {"rule_id": "rule1", "line": 42},
            {"rule_id": "rule1", "line": 55},
        ]
        post_fix = []
        result = compare_findings(baseline, post_fix, "CWE-89")
        self.assertEqual(result["resolved_count"], 2)
        self.assertEqual(result["persistent_count"], 0)

    def test_one_persistent(self):
        baseline = [{"rule_id": "rule1", "line": 42}]
        post_fix = [{"check_id": "rule1", "start": {"line": 42}}]
        result = compare_findings(baseline, post_fix, "CWE-89")
        self.assertEqual(result["resolved_count"], 0)
        self.assertEqual(result["persistent_count"], 1)

    def test_shifted(self):
        baseline = [{"rule_id": "rule1", "line": 42}]
        post_fix = [{"check_id": "rule1", "start": {"line": 45}}]  # Shifted by 3
        result = compare_findings(baseline, post_fix, "CWE-89")
        self.assertEqual(result["shifted_count"], 1)
        self.assertEqual(result["resolved_count"], 0)

    def test_new_finding(self):
        baseline = [{"rule_id": "rule1", "line": 42}]
        post_fix = [
            {"check_id": "rule2", "start": {"line": 100}, "extra": {"message": "new"}}
        ]
        result = compare_findings(baseline, post_fix, "CWE-89")
        self.assertEqual(result["resolved_count"], 1)
        self.assertEqual(result["new_count"], 1)


class TestDetermineVerdict(TestCase):
    def test_all_resolved_no_new(self):
        comparison = {"resolved_count": 3, "persistent_count": 0, "shifted_count": 0, "new_count": 0}
        self.assertEqual(determine_verdict(comparison, 3), "PASS")

    def test_partial(self):
        comparison = {"resolved_count": 2, "persistent_count": 1, "shifted_count": 0, "new_count": 0}
        self.assertEqual(determine_verdict(comparison, 3), "PARTIAL")

    def test_fail_nothing_resolved(self):
        comparison = {"resolved_count": 0, "persistent_count": 3, "shifted_count": 0, "new_count": 0}
        self.assertEqual(determine_verdict(comparison, 3), "FAIL")

    def test_partial_with_new(self):
        comparison = {"resolved_count": 2, "persistent_count": 0, "shifted_count": 0, "new_count": 1}
        self.assertEqual(determine_verdict(comparison, 2), "PARTIAL")


if __name__ == "__main__":
    main()
