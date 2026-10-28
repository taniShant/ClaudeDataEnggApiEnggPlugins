"""Tests for parse_wiz_report.py."""

import json
import sys
from io import StringIO
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.parsers.parse_wiz_report import (
    extract_findings_array,
    normalize_cwe,
    extract_cwe,
    normalize_severity,
    classify_remediation_type,
    parse_finding,
    ensure_unique_ids,
)


class TestNormalizeCWE(TestCase):
    def test_standard_format(self):
        self.assertEqual(normalize_cwe("CWE-89"), "CWE-89")

    def test_lowercase(self):
        self.assertEqual(normalize_cwe("cwe-89"), "CWE-89")

    def test_bare_number_string(self):
        self.assertEqual(normalize_cwe("89"), "CWE-89")

    def test_bare_number_int(self):
        self.assertEqual(normalize_cwe(89), "CWE-89")

    def test_with_name(self):
        self.assertEqual(normalize_cwe("CWE-89: SQL Injection"), "CWE-89")

    def test_zero(self):
        self.assertIsNone(normalize_cwe(0))

    def test_none(self):
        self.assertIsNone(normalize_cwe(None))

    def test_invalid_string(self):
        self.assertIsNone(normalize_cwe("ABC"))

    def test_no_hyphen(self):
        self.assertEqual(normalize_cwe("CWE89"), "CWE-89")


class TestExtractCWE(TestCase):
    def test_cwe_field(self):
        self.assertEqual(extract_cwe({"cwe": "CWE-89"}), "CWE-89")

    def test_cweId_field(self):
        self.assertEqual(extract_cwe({"cweId": "79"}), "CWE-79")

    def test_rule_cwe(self):
        self.assertEqual(extract_cwe({"rule": {"cwe": "CWE-502"}}), "CWE-502")

    def test_tags_with_cwe(self):
        self.assertEqual(extract_cwe({"tags": ["CWE-798", "secrets"]}), "CWE-798")

    def test_no_cwe(self):
        self.assertIsNone(extract_cwe({"title": "Something"}))


class TestNormalizeSeverity(TestCase):
    def test_critical(self):
        self.assertEqual(normalize_severity("CRITICAL"), "critical")

    def test_high_mixed_case(self):
        self.assertEqual(normalize_severity("High"), "high")

    def test_unknown_defaults_medium(self):
        self.assertEqual(normalize_severity("IMPORTANT"), "medium")

    def test_none_defaults_medium(self):
        self.assertEqual(normalize_severity(None), "medium")


class TestClassifyRemediationType(TestCase):
    def test_python_file(self):
        self.assertEqual(classify_remediation_type("src/foo.py", None, None), "code_fix")

    def test_terraform_file(self):
        self.assertEqual(classify_remediation_type("infra/main.tf", None, None), "infra_config")

    def test_package_json(self):
        self.assertEqual(classify_remediation_type("package.json", None, None), "dependency")

    def test_dependency_tag(self):
        self.assertEqual(classify_remediation_type("src/app.py", None, ["dependency"]), "dependency")

    def test_no_file_path(self):
        self.assertEqual(classify_remediation_type(None, None, None), "manual")

    def test_dockerfile(self):
        self.assertEqual(classify_remediation_type("Dockerfile", None, None), "infra_config")


class TestExtractFindingsArray(TestCase):
    def test_results_key(self):
        data = {"results": [{"id": 1}]}
        self.assertEqual(extract_findings_array(data), [{"id": 1}])

    def test_top_level_array(self):
        data = [{"id": 1}]
        self.assertEqual(extract_findings_array(data), [{"id": 1}])

    def test_data_results(self):
        data = {"data": {"results": [{"id": 1}]}}
        self.assertEqual(extract_findings_array(data), [{"id": 1}])

    def test_findings_key(self):
        data = {"findings": [{"id": 1}]}
        self.assertEqual(extract_findings_array(data), [{"id": 1}])

    def test_vulnerabilities_key(self):
        data = {"vulnerabilities": [{"id": 1}, {"id": 2}]}
        self.assertEqual(extract_findings_array(data), [{"id": 1}, {"id": 2}])

    def test_no_match(self):
        data = {"meta": "data"}
        self.assertIsNone(extract_findings_array(data))

    def test_cloud_event_format(self):
        data = {
            "vulnerabilityFindings": {
                "findings": [{"id": 1}, {"id": 2}]
            }
        }
        self.assertEqual(extract_findings_array(data), [{"id": 1}, {"id": 2}])


class TestParseFinding(TestCase):
    def test_standard_finding(self):
        finding = {
            "id": "abc123",
            "title": "SQL Injection",
            "severity": "HIGH",
            "cwe": "CWE-89",
            "filePath": "src/db.py",
            "lineNumber": 42,
            "codeSnippet": "query = f\"SELECT...\"",
            "ruleId": "python-sqli",
            "confidence": "high",
        }
        result = parse_finding(finding, 1, "/repo")
        self.assertEqual(result["id"], "wiz-abc123")
        self.assertEqual(result["cwe_id"], "CWE-89")
        self.assertEqual(result["severity"], "high")
        self.assertEqual(result["file_path"], "src/db.py")
        self.assertEqual(result["line_number"], 42)
        self.assertEqual(result["remediation_type"], "code_fix")
        self.assertEqual(result["confidence"], 0.9)

    def test_missing_optional_fields(self):
        finding = {"title": "Something", "severity": "LOW"}
        result = parse_finding(finding, 5, None)
        self.assertEqual(result["id"], "wiz-5")
        self.assertIsNone(result["cwe_id"])
        self.assertIsNone(result["file_path"])
        self.assertIsNone(result["line_number"])


class TestEnsureUniqueIds(TestCase):
    def test_duplicates_get_suffix(self):
        vulns = [
            {"id": "wiz-1", "title": "a"},
            {"id": "wiz-1", "title": "b"},
            {"id": "wiz-1", "title": "c"},
        ]
        result = ensure_unique_ids(vulns)
        ids = [v["id"] for v in result]
        self.assertEqual(ids, ["wiz-1", "wiz-1-2", "wiz-1-3"])


class TestSCAFieldExtraction(TestCase):
    """Tests for SCA-specific field extraction (affected_package, current_version, fixed_version)."""

    def test_fixed_version_from_top_level_field(self):
        finding = {
            "id": "sca1", "title": "Vuln Dep", "severity": "HIGH",
            "cwe": "CWE-937", "filePath": "build.gradle",
            "fixedVersion": "2.17.0", "ruleId": "java-vuln-dep",
        }
        result = parse_finding(finding, 1, "/repo")
        self.assertEqual(result["fixed_version"], "2.17.0")

    def test_fixed_version_from_nested_version_fixed(self):
        finding = {
            "id": "sca2", "title": "Vuln Dep", "severity": "MEDIUM",
            "cwe": "CWE-937", "filePath": "pom.xml",
            "version": {"fixed": "5.3.39"}, "ruleId": "java-vuln-dep",
        }
        result = parse_finding(finding, 1, "/repo")
        self.assertEqual(result["fixed_version"], "5.3.39")

    def test_affected_package_from_vulnerable_package(self):
        finding = {
            "id": "sca3", "title": "Vuln Dep", "severity": "HIGH",
            "cwe": "CWE-937", "filePath": "build.gradle",
            "vulnerablePackage": {"name": "com.fasterxml.jackson.core:jackson-databind", "version": "2.15.2"},
            "ruleId": "java-vuln-dep",
        }
        result = parse_finding(finding, 1, "/repo")
        self.assertEqual(result["affected_package"], "com.fasterxml.jackson.core:jackson-databind")
        self.assertEqual(result["current_version"], "2.15.2")

    def test_affected_package_from_package_name(self):
        finding = {
            "id": "sca4", "title": "Vuln Dep", "severity": "LOW",
            "filePath": "package.json", "packageName": "lodash",
            "packageVersion": "4.17.19", "ruleId": "js-vuln-dep",
        }
        result = parse_finding(finding, 1, "/repo")
        self.assertEqual(result["affected_package"], "lodash")
        self.assertEqual(result["current_version"], "4.17.19")

    def test_no_sca_fields_returns_none(self):
        finding = {
            "id": "code1", "title": "SQL Injection", "severity": "HIGH",
            "cwe": "CWE-89", "filePath": "src/db.py", "ruleId": "python-sqli",
        }
        result = parse_finding(finding, 1, "/repo")
        self.assertIsNone(result["fixed_version"])
        self.assertIsNone(result["affected_package"])
        self.assertIsNone(result["current_version"])

    def test_empty_string_fields_return_none(self):
        finding = {
            "id": "sca5", "title": "Vuln", "severity": "LOW",
            "filePath": "build.gradle", "fixedVersion": "", "packageName": "  ",
            "ruleId": "dep",
        }
        result = parse_finding(finding, 1, "/repo")
        self.assertIsNone(result["fixed_version"])
        self.assertIsNone(result["affected_package"])


class TestFullPipeline(TestCase):
    def test_sample_report(self):
        fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_wiz_report.json"
        with open(fixture_path) as f:
            report = json.load(f)

        findings = extract_findings_array(report)
        self.assertEqual(len(findings), 6)

        results = []
        for i, f in enumerate(findings, 1):
            results.append(parse_finding(f, i, "/repo"))

        results = ensure_unique_ids(results)
        self.assertEqual(len(results), 6)

        # Check first finding
        self.assertEqual(results[0]["cwe_id"], "CWE-89")
        self.assertEqual(results[0]["severity"], "high")
        self.assertEqual(results[0]["remediation_type"], "code_fix")

        # Check terraform finding -> infra_config
        self.assertEqual(results[2]["remediation_type"], "infra_config")

        # Check package.json -> dependency
        self.assertEqual(results[3]["remediation_type"], "dependency")

        # Check SCA finding (6th entry) with fixedVersion
        self.assertEqual(results[5]["cwe_id"], "CWE-937")
        self.assertEqual(results[5]["remediation_type"], "dependency")
        self.assertEqual(results[5]["fixed_version"], "2.17.0")
        self.assertEqual(results[5]["affected_package"], "com.fasterxml.jackson.core:jackson-databind")
        self.assertEqual(results[5]["current_version"], "2.15.2")


if __name__ == "__main__":
    main()
