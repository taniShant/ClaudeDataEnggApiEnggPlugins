"""Tests for wiz_delta_comparator.py — uses real WIZ CloudEvent JSON schema."""

import json
import sys
from pathlib import Path
from unittest import TestCase, main

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.validators.wiz_delta_comparator import (
    normalize_cwe,
    extract_findings,
    normalize_wiz_finding,
    compare_wiz_findings,
    determine_verdict,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


class TestNormalizeCwe(TestCase):
    def test_standard(self):
        self.assertEqual(normalize_cwe("CWE-89"), "CWE-89")

    def test_lowercase(self):
        self.assertEqual(normalize_cwe("cwe-89"), "CWE-89")

    def test_leading_zeros(self):
        self.assertEqual(normalize_cwe("CWE-089"), "CWE-89")

    def test_no_hyphen(self):
        self.assertEqual(normalize_cwe("CWE89"), "CWE-89")


class TestExtractFindings(TestCase):
    """Tests use real WIZ CloudEvent schema: extraDetails.sastDetails.findings[]"""

    def setUp(self):
        self.scan = _load_fixture("sample_wiz_scan_output.json")
        self.empty_scan = _load_fixture("sample_wiz_scan_empty.json")

    def test_all_findings(self):
        findings = extract_findings(self.scan)
        self.assertEqual(len(findings), 4)

    def test_filter_by_cwe(self):
        findings = extract_findings(self.scan, target_cwe="CWE-89")
        self.assertEqual(len(findings), 2)
        for f in findings:
            cwe_ids = [w["id"] for w in f["weaknesses"]]
            self.assertIn("CWE-89", cwe_ids)

    def test_filter_by_file(self):
        findings = extract_findings(self.scan, target_file="src/db/queries.py")
        self.assertEqual(len(findings), 2)
        for f in findings:
            self.assertEqual(f["filePath"], "src/db/queries.py")

    def test_filter_by_both(self):
        findings = extract_findings(self.scan, target_cwe="CWE-89", target_file="src/db/queries.py")
        self.assertEqual(len(findings), 2)

    def test_no_match(self):
        findings = extract_findings(self.scan, target_cwe="CWE-999")
        self.assertEqual(len(findings), 0)

    def test_empty_scan(self):
        findings = extract_findings(self.empty_scan)
        self.assertEqual(len(findings), 0)


class TestNormalizeWizFinding(TestCase):
    """Uses real WIZ schema: rule.id and weaknesses[].id"""

    def test_basic(self):
        finding = {
            "filePath": "src/db/queries.py",
            "rule": {"id": "WS-SQL-INJECT-001", "name": "WS-SQL-INJECT-001"},
            "weaknesses": [{"__typename": "Weakness", "id": "CWE-89", "name": "CWE-89: SQL Injection"}],
        }
        key = normalize_wiz_finding(finding)
        self.assertIsInstance(key, tuple)
        self.assertEqual(len(key), 3)
        self.assertEqual(key, ("src/db/queries.py", "WS-SQL-INJECT-001", "CWE-89"))

    def test_empty_cwe(self):
        finding = {
            "filePath": "src/app.py",
            "rule": {"id": "some-rule"},
            "weaknesses": [],
        }
        key = normalize_wiz_finding(finding)
        self.assertEqual(key, ("src/app.py", "some-rule", ""))


def _make_finding(finding_id: str, rule_id: str, file_path: str, cwe: str) -> dict:
    """Helper to create a WIZ finding dict in real schema format."""
    return {
        "id": finding_id,
        "rule": {"__typename": "SASTRule", "id": rule_id, "name": rule_id},
        "filePath": file_path,
        "weaknesses": [{"__typename": "Weakness", "id": cwe, "name": f"{cwe}: Test"}],
        "startLine": 10,
        "severity": "HIGH",
    }


class TestCompareWizFindings(TestCase):
    def test_all_resolved(self):
        baseline = [
            _make_finding("f1", "rule-sqli", "src/db.py", "CWE-89"),
            _make_finding("f2", "rule-xss", "src/views.py", "CWE-79"),
        ]
        result = compare_wiz_findings(baseline, [])
        self.assertEqual(result["resolved_count"], 2)
        self.assertEqual(result["persistent_count"], 0)
        self.assertEqual(result["new_count"], 0)

    def test_all_persistent(self):
        baseline = [
            _make_finding("f1", "rule-sqli", "src/db.py", "CWE-89"),
            _make_finding("f2", "rule-xss", "src/views.py", "CWE-79"),
        ]
        postfix = [
            _make_finding("f1-post", "rule-sqli", "src/db.py", "CWE-89"),
            _make_finding("f2-post", "rule-xss", "src/views.py", "CWE-79"),
        ]
        result = compare_wiz_findings(baseline, postfix)
        self.assertEqual(result["persistent_count"], 2)
        self.assertEqual(result["resolved_count"], 0)

    def test_mixed(self):
        baseline = [
            _make_finding("f1", "rule-sqli", "src/db.py", "CWE-89"),
            _make_finding("f2", "rule-xss", "src/views.py", "CWE-79"),
        ]
        postfix = [
            _make_finding("f2-post", "rule-xss", "src/views.py", "CWE-79"),
        ]
        result = compare_wiz_findings(baseline, postfix)
        self.assertEqual(result["resolved_count"], 1)
        self.assertEqual(result["persistent_count"], 1)

    def test_new_finding(self):
        baseline = [_make_finding("f1", "rule-sqli", "src/db.py", "CWE-89")]
        postfix = [_make_finding("f2", "rule-hardcoded", "src/config.py", "CWE-798")]
        result = compare_wiz_findings(baseline, postfix)
        self.assertEqual(result["resolved_count"], 1)
        self.assertEqual(result["new_count"], 1)

    def test_empty_baseline(self):
        postfix = [
            _make_finding("f1", "rule-sqli", "src/db.py", "CWE-89"),
            _make_finding("f2", "rule-xss", "src/views.py", "CWE-79"),
        ]
        result = compare_wiz_findings([], postfix)
        self.assertEqual(result["new_count"], 2)
        self.assertEqual(result["resolved_count"], 0)


class TestDetermineVerdict(TestCase):
    def test_pass(self):
        comparison = {"resolved_count": 2, "persistent_count": 0, "new_count": 0}
        self.assertEqual(determine_verdict(comparison, 2), "PASS")

    def test_partial_some_persist(self):
        comparison = {"resolved_count": 1, "persistent_count": 1, "new_count": 0}
        self.assertEqual(determine_verdict(comparison, 2), "PARTIAL")

    def test_partial_with_new(self):
        comparison = {"resolved_count": 1, "persistent_count": 0, "new_count": 1}
        self.assertEqual(determine_verdict(comparison, 1), "PARTIAL")

    def test_fail_nothing_resolved(self):
        comparison = {"resolved_count": 0, "persistent_count": 3, "new_count": 0}
        self.assertEqual(determine_verdict(comparison, 3), "FAIL")


if __name__ == "__main__":
    main()
