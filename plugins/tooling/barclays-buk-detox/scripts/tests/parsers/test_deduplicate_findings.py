"""Tests for deduplicate_findings.py."""

import sys
from pathlib import Path
from unittest import TestCase, main

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.parsers.deduplicate_findings import make_key, merge_vulnerabilities


class TestMakeKey(TestCase):
    def test_valid_key(self):
        vuln = {"file_path": "src/app.py", "line_number": 42, "cwe_id": "CWE-89"}
        self.assertEqual(make_key(vuln), ("src/app.py", 42, "CWE-89"))

    def test_missing_file_path(self):
        vuln = {"file_path": None, "line_number": 42, "cwe_id": "CWE-89"}
        self.assertIsNone(make_key(vuln))

    def test_missing_line_number(self):
        vuln = {"file_path": "src/app.py", "line_number": None, "cwe_id": "CWE-89"}
        self.assertIsNone(make_key(vuln))

    def test_missing_cwe(self):
        vuln = {"file_path": "src/app.py", "line_number": 42, "cwe_id": None}
        self.assertIsNone(make_key(vuln))


class TestMergeVulnerabilities(TestCase):
    def test_highest_severity_upgrade(self):
        existing = {"severity": "medium", "description": "short", "confidence": 0.7}
        incoming = {"severity": "critical", "description": "longer description", "confidence": 0.9}
        result = merge_vulnerabilities(existing, incoming, "highest_severity")
        self.assertEqual(result["severity"], "critical")
        self.assertEqual(result["description"], "longer description")
        self.assertEqual(result["confidence"], 0.9)

    def test_no_downgrade(self):
        existing = {"severity": "high", "description": "good description", "confidence": 0.9}
        incoming = {"severity": "low", "description": "short", "confidence": 0.5}
        result = merge_vulnerabilities(existing, incoming, "highest_severity")
        self.assertEqual(result["severity"], "high")
        self.assertEqual(result["description"], "good description")
        self.assertEqual(result["confidence"], 0.9)

    def test_code_snippet_fill(self):
        existing = {"severity": "high", "code_snippet": None, "description": ""}
        incoming = {"severity": "high", "code_snippet": "x = 1", "description": ""}
        result = merge_vulnerabilities(existing, incoming, "highest_severity")
        self.assertEqual(result["code_snippet"], "x = 1")


if __name__ == "__main__":
    main()
