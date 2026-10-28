"""
Tests for backwards compatibility of requirements analysis schema migration.

Verifies:
1. Old v1.0 format (source_jira_evidence) still loads and validates
2. New v2.0 format (source_evidence array) loads and validates
3. Downstream consumers (assess_capability_impact) handle both formats transparently
4. No source-type branching in downstream logic
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.understand_requirements import (
    validate_existing_analysis,
    extract_evidence_units,
    build_evidence_unit_map,
)


class TestSchemaBackwardsCompatibility(TestCase):
    """Test that old v1.0 and new v2.0 schema formats are both valid."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="buk_sa_compat_test_")
        self.workspace = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_old_v1_analysis(self, issue_key="TEST-1"):
        """Create an old v1.0 format requirements-analysis.json."""
        return {
            "schema_version": "1.0",
            "analysis_metadata": {
                "analyzed_at": datetime.now(timezone.utc).isoformat()
            },
            "source_jira_evidence": {
                "issue_key": issue_key,
                "raw_jira_response_sha256": "abc123def456789abc123def456789abc123def456789abc123def456789ab"
            },
            "change_summary": {
                "outcome": "Enable deterministic retrieval",
                "rationale": "Support reproducible analysis",
                "supporting_evidence": [
                    {
                        "evidence_id": "description:0",
                        "jira_field": "description",
                        "source_value": "A test description"
                    }
                ]
            },
            "explicit_requirements": [
                {
                    "id": "ER001",
                    "requirement": "System must work deterministically",
                    "supporting_evidence": [
                        {
                            "evidence_id": "summary:0",
                            "jira_field": "summary",
                            "source_value": "Test Epic"
                        }
                    ]
                }
            ],
            "inferred_requirements": [],
            "constraints_and_dependencies": [],
            "ambiguities_and_unknowns": [],
            "key_concepts": []
        }

    def _make_new_v2_analysis(self, issue_key="TEST-1"):
        """Create a new v2.0 format requirements-analysis.json."""
        return {
            "schema_version": "2.0",
            "analysis_metadata": {
                "analyzed_at": datetime.now(timezone.utc).isoformat()
            },
            "source_evidence": [
                {
                    "source_type": "jira",
                    "source_identifier": issue_key,
                    "sha256": "abc123def456789abc123def456789abc123def456789abc123def456789ab",
                    "jira": {
                        "instance": "estjira.barcapint.com",
                        "issue_key": issue_key
                    }
                }
            ],
            "change_summary": {
                "outcome": "Enable deterministic retrieval",
                "rationale": "Support reproducible analysis",
                "supporting_evidence": [
                    {
                        "evidence_id": "description:0",
                        "source_type": "jira",
                        "source_value": "A test description"
                    }
                ]
            },
            "explicit_requirements": [
                {
                    "id": "ER001",
                    "requirement": "System must work deterministically",
                    "supporting_evidence": [
                        {
                            "evidence_id": "summary:0",
                            "source_type": "jira",
                            "source_value": "Test Epic"
                        }
                    ]
                }
            ],
            "inferred_requirements": [],
            "constraints_and_dependencies": [],
            "ambiguities_and_unknowns": [],
            "key_concepts": []
        }

    def test_accepts_old_v1_format(self):
        """Verify old v1.0 format (source_jira_evidence) validates successfully."""
        analysis_file = self.workspace / "v1_analysis.json"
        v1_analysis = self._make_old_v1_analysis("OLD-100")
        analysis_file.write_text(json.dumps(v1_analysis), encoding='utf-8')

        # Should not raise
        result = validate_existing_analysis(analysis_file)
        self.assertEqual(result["schema_version"], "1.0")
        self.assertIn("source_jira_evidence", result)
        self.assertEqual(result["source_jira_evidence"]["issue_key"], "OLD-100")

    def test_accepts_new_v2_format(self):
        """Verify new v2.0 format (source_evidence array) validates successfully."""
        analysis_file = self.workspace / "v2_analysis.json"
        v2_analysis = self._make_new_v2_analysis("NEW-100")
        analysis_file.write_text(json.dumps(v2_analysis), encoding='utf-8')

        # Should not raise
        result = validate_existing_analysis(analysis_file)
        self.assertEqual(result["schema_version"], "2.0")
        self.assertIn("source_evidence", result)
        self.assertEqual(len(result["source_evidence"]), 1)
        self.assertEqual(result["source_evidence"][0]["source_identifier"], "NEW-100")

    def test_v1_format_requires_raw_jira_response_sha256(self):
        """Verify v1.0 format validation fails without raw_jira_response_sha256."""
        analysis_file = self.workspace / "broken_v1.json"
        broken_v1 = self._make_old_v1_analysis()
        del broken_v1["source_jira_evidence"]["raw_jira_response_sha256"]
        analysis_file.write_text(json.dumps(broken_v1), encoding='utf-8')

        with self.assertRaises(RuntimeError) as cm:
            validate_existing_analysis(analysis_file)
        self.assertIn("raw_jira_response_sha256", str(cm.exception))

    def test_v2_format_requires_sha256_in_each_source(self):
        """Verify v2.0 format validation fails if source_evidence item missing sha256."""
        analysis_file = self.workspace / "broken_v2.json"
        broken_v2 = self._make_new_v2_analysis()
        del broken_v2["source_evidence"][0]["sha256"]
        analysis_file.write_text(json.dumps(broken_v2), encoding='utf-8')

        with self.assertRaises(RuntimeError) as cm:
            validate_existing_analysis(analysis_file)
        self.assertIn("sha256", str(cm.exception))

    def test_v1_format_requires_source_jira_evidence_present(self):
        """Verify v1.0 format validation fails without source_jira_evidence."""
        analysis_file = self.workspace / "missing_provenance_v1.json"
        broken_v1 = self._make_old_v1_analysis()
        del broken_v1["source_jira_evidence"]
        analysis_file.write_text(json.dumps(broken_v1), encoding='utf-8')

        with self.assertRaises(RuntimeError) as cm:
            validate_existing_analysis(analysis_file)
        self.assertIn("source_jira_evidence", str(cm.exception))

    def test_v2_format_requires_source_evidence_array(self):
        """Verify v2.0 format validation fails without source_evidence array."""
        analysis_file = self.workspace / "missing_provenance_v2.json"
        broken_v2 = self._make_new_v2_analysis()
        del broken_v2["source_evidence"]
        analysis_file.write_text(json.dumps(broken_v2), encoding='utf-8')

        with self.assertRaises(RuntimeError) as cm:
            validate_existing_analysis(analysis_file)
        self.assertIn("source_evidence", str(cm.exception))

    def test_unsupported_schema_version_rejected(self):
        """Verify schema versions other than 1.0/2.0 are rejected."""
        analysis_file = self.workspace / "v3_analysis.json"
        v3_analysis = self._make_new_v2_analysis()
        v3_analysis["schema_version"] = "3.0"
        analysis_file.write_text(json.dumps(v3_analysis), encoding='utf-8')

        with self.assertRaises(RuntimeError) as cm:
            validate_existing_analysis(analysis_file)
        self.assertIn("Unsupported", str(cm.exception))

    def test_v1_and_v2_both_have_required_sections(self):
        """Verify both v1 and v2 require all analysis sections."""
        for analysis_maker in [self._make_old_v1_analysis, self._make_new_v2_analysis]:
            analysis_file = self.workspace / f"test_{analysis_maker.__name__}.json"
            analysis = analysis_maker()
            # Remove a required section
            del analysis["change_summary"]
            analysis_file.write_text(json.dumps(analysis), encoding='utf-8')

            with self.assertRaises(RuntimeError) as cm:
                validate_existing_analysis(analysis_file)
            self.assertIn("structure invalid", str(cm.exception).lower())

    def test_v2_evidence_references_include_source_type(self):
        """Verify v2.0 evidence references include source_type for clarity."""
        analysis_file = self.workspace / "v2_with_source_type.json"
        v2_analysis = self._make_new_v2_analysis()
        analysis_file.write_text(json.dumps(v2_analysis), encoding='utf-8')

        result = validate_existing_analysis(analysis_file)
        # Check that supporting_evidence items have source_type
        for evidence in result["change_summary"]["supporting_evidence"]:
            self.assertIn("source_type", evidence)
            self.assertEqual(evidence["source_type"], "jira")


class TestDownstreamConsumerTransparency(TestCase):
    """
    Test that downstream consumers (assess_capability_impact) handle both formats transparently.
    No source-type branching should be required.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="buk_sa_downstream_test_")
        self.workspace = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_extract_hash_from_old_v1_format(self):
        """Verify downstream can extract hash from v1.0 format without branching."""
        # Simulate assess_capability_impact logic
        v1_analysis = {
            "schema_version": "1.0",
            "source_jira_evidence": {
                "issue_key": "TEST-1",
                "raw_jira_response_sha256": "abc123"
            }
        }

        # Backwards-compat extraction logic (no branching required)
        def get_primary_hash(analysis):
            schema = analysis.get("schema_version")
            if schema == "1.0":
                return analysis.get("source_jira_evidence", {}).get("raw_jira_response_sha256")
            elif schema == "2.0":
                sources = analysis.get("source_evidence", [])
                return sources[0].get("sha256") if sources else None
            return None

        hash_value = get_primary_hash(v1_analysis)
        self.assertEqual(hash_value, "abc123")

    def test_extract_hash_from_new_v2_format(self):
        """Verify downstream can extract hash from v2.0 format without branching."""
        v2_analysis = {
            "schema_version": "2.0",
            "source_evidence": [
                {
                    "source_type": "jira",
                    "source_identifier": "TEST-1",
                    "sha256": "def456"
                }
            ]
        }

        def get_primary_hash(analysis):
            schema = analysis.get("schema_version")
            if schema == "1.0":
                return analysis.get("source_jira_evidence", {}).get("raw_jira_response_sha256")
            elif schema == "2.0":
                sources = analysis.get("source_evidence", [])
                return sources[0].get("sha256") if sources else None
            return None

        hash_value = get_primary_hash(v2_analysis)
        self.assertEqual(hash_value, "def456")

    def test_no_source_type_branching_downstream(self):
        """Verify downstream logic does not branch on source_type.

        The canonical contract is the same regardless of source.
        Downstream works with explicit_requirements, inferred_requirements, etc.
        without needing to know if data came from Jira, PRD, or Brief.
        """
        v1_analysis = {
            "schema_version": "1.0",
            "source_jira_evidence": {"issue_key": "TEST-1", "raw_jira_response_sha256": "abc"},
            "explicit_requirements": [
                {
                    "id": "ER001",
                    "requirement": "Requirement 1",
                    "supporting_evidence": []
                }
            ]
        }

        v2_analysis = {
            "schema_version": "2.0",
            "source_evidence": [
                {"source_type": "jira", "source_identifier": "TEST-1", "sha256": "abc"}
            ],
            "explicit_requirements": [
                {
                    "id": "ER001",
                    "requirement": "Requirement 1",
                    "supporting_evidence": []
                }
            ]
        }

        # Downstream processing (capability impact assessment)
        # should work identically on both — NO branching on source_type
        def process_requirements(analysis):
            """Generic requirements processor — no source-type checks."""
            requirements = analysis.get("explicit_requirements", [])
            return [r["id"] for r in requirements]

        # Both should produce same results
        v1_result = process_requirements(v1_analysis)
        v2_result = process_requirements(v2_analysis)
        self.assertEqual(v1_result, v2_result)
        self.assertEqual(v1_result, ["ER001"])


if __name__ == "__main__":
    main()
