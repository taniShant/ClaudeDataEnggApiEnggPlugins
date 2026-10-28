"""Tests for classify_findings.py."""

import json
import sys
from io import StringIO
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))


def run_classify(input_data: dict) -> dict:
    """Helper to run classify_findings.main() with mocked stdin/stdout."""
    from scripts.parsers.classify_findings import main as classify_main

    stdin_data = json.dumps(input_data)
    captured_output = StringIO()

    with patch("sys.stdin", StringIO(stdin_data)), \
         patch("sys.stdout", captured_output):
        try:
            classify_main()
        except SystemExit:
            pass

    return json.loads(captured_output.getvalue())


class TestClassifyFindings(TestCase):
    def setUp(self):
        self.vulns = [
            {"id": "1", "severity": "critical", "remediation_type": "code_fix"},
            {"id": "2", "severity": "high", "remediation_type": "code_fix"},
            {"id": "3", "severity": "medium", "remediation_type": "infra_config"},
            {"id": "4", "severity": "low", "remediation_type": "dependency"},
            {"id": "5", "severity": "high", "remediation_type": "manual"},
            {"id": "6", "severity": "critical", "remediation_type": "hybrid"},
        ]

    def test_filter_all(self):
        result = run_classify({"vulnerabilities": self.vulns, "severity_filter": "all"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["counts"]["code_fix"], 2)
        self.assertEqual(result["counts"]["hybrid"], 1)
        self.assertEqual(result["counts"]["infra_config"], 1)
        self.assertEqual(result["counts"]["dependency"], 1)
        self.assertEqual(result["counts"]["manual"], 1)
        self.assertEqual(result["counts"]["filtered_out"], 0)

    def test_filter_critical(self):
        result = run_classify({"vulnerabilities": self.vulns, "severity_filter": "critical"})
        self.assertEqual(result["counts"]["code_fix"], 1)
        self.assertEqual(result["counts"]["hybrid"], 1)
        self.assertEqual(result["counts"]["filtered_out"], 4)

    def test_filter_critical_plus_high(self):
        result = run_classify({"vulnerabilities": self.vulns, "severity_filter": "critical+high"})
        self.assertEqual(result["counts"]["code_fix"], 2)
        self.assertEqual(result["counts"]["manual"], 1)
        self.assertEqual(result["counts"]["filtered_out"], 2)

    def test_empty_input(self):
        result = run_classify({"vulnerabilities": [], "severity_filter": "all"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["counts"]["total_actionable"], 0)

    def test_unknown_type_defaults_to_code_fix(self):
        vulns = [{"id": "1", "severity": "high", "remediation_type": "unknown_type"}]
        result = run_classify({"vulnerabilities": vulns, "severity_filter": "all"})
        self.assertEqual(result["counts"]["code_fix"], 1)

    def test_output_includes_duration_ms(self):
        result = run_classify({"vulnerabilities": self.vulns, "severity_filter": "all"})
        self.assertIn("duration_ms", result)
        self.assertIsInstance(result["duration_ms"], int)
        self.assertGreaterEqual(result["duration_ms"], 0)


if __name__ == "__main__":
    main()
