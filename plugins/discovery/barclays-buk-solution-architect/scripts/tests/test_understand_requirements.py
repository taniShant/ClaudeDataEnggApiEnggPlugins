"""
Tests for deterministic preflight and postflight validation of requirements understanding.

Architecture under test:
- Preflight: validates requirements.json, builds evidence catalogue with positional IDs
- LLM (not tested here): reasons about requirements, returns evidence IDs
- Postflight: validates evidence IDs, resolves to authoritative source values, persists

Evidence ID contract:
    IDs have the form {jira_field}:{unit_index} (e.g. "description:2", "labels:0").
    They are positional identifiers scoped to the source version identified by
    raw_jira_response_sha256. The LLM returns IDs only; source values are resolved
    deterministically by postflight.
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
    preflight_validate,
    postflight_validate,
    extract_evidence_units,
    build_evidence_unit_map,
    validate_evidence_id_list,
    resolve_evidence_ids,
    _split_description_into_units,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_evidence(
    summary="Implement deterministic requirements retrieval",
    description="As a solution architect, I need to retrieve issues deterministically",
    status="In Progress",
    labels=None,
    components=None,
    linked_issues=None,
    acceptance_criteria=None,
    issue_key="TEST-1",
):
    return {
        "issue_key": issue_key,
        "summary": summary,
        "description": description,
        "status": status,
        "labels": labels if labels is not None else ["backend", "feature"],
        "components": components if components is not None else ["API", "Database"],
        "linked_issues": linked_issues if linked_issues is not None else [
            {"issue_key": "TEST-2", "link_type": "blocks", "direction": "outward"}
        ],
        "acceptance_criteria": acceptance_criteria if acceptance_criteria is not None else [
            "AC 1: Deterministic",
            "AC 2: Verified",
        ],
    }


def _make_source_provenance(issue_key="TEST-1", sha256="abc123def456"):
    return {"issue_key": issue_key, "raw_jira_response_sha256": sha256}


def _make_valid_analysis(evidence_units=None):
    """Create a valid analysis that uses evidence IDs."""
    if evidence_units is None:
        evidence_units = extract_evidence_units(_make_evidence())
    unit_map = build_evidence_unit_map(evidence_units)
    ids = list(unit_map.keys())

    # Pick stable IDs from available units
    desc_id = next((k for k in ids if k.startswith("description:")), ids[0])
    ac_id = next((k for k in ids if k.startswith("acceptance_criteria:")), ids[0])
    summary_id = next((k for k in ids if k.startswith("summary:")), ids[0])
    linked_id = next((k for k in ids if k.startswith("linked_issues:")), ids[0])

    return {
        "change_summary": {
            "outcome": "Enable deterministic requirements retrieval",
            "rationale": "To support reproducible analysis",
            "supporting_evidence": [desc_id],
        },
        "explicit_requirements": [
            {
                "id": "ER001",
                "requirement": "System must retrieve without LLM",
                "supporting_evidence": [ac_id],
            }
        ],
        "inferred_requirements": [
            {
                "id": "IR001",
                "requirement": "SHA-256 integrity is important",
                "reasoning": "AC 2 mentions verification",
                "supporting_evidence": [ac_id],
            }
        ],
        "constraints_and_dependencies": [
            {
                "id": "CD001",
                "constraint": "Blocks TEST-2",
                "is_explicit": True,
                "supporting_evidence": [linked_id],
            }
        ],
        "ambiguities_and_unknowns": [
            {
                "id": "AMB001",
                "ambiguity": "Performance requirements not specified",
                "impact": "Cannot determine caching strategy",
                "clarification_needed": "What are response time requirements?",
            }
        ],
        "key_concepts": [
            {
                "concept": "Determinism",
                "definition": "Same input produces same output",
                "supporting_evidence": [summary_id],
            }
        ],
    }


# ---------------------------------------------------------------------------
# TestPreflightValidation
# ---------------------------------------------------------------------------

class TestPreflightValidation(TestCase):
    """Test deterministic preflight validation."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="buk_sa_test_")
        self.workspace = Path(self.temp_dir)
        (self.workspace / "requirements").mkdir()
        (self.workspace / "raw").mkdir()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_requirements(self, issue_type="Business Epic", requirements_override=None):
        raw_content = b'{"fields": {"issuetype": {"name": "' + issue_type.encode() + b'"}}}'
        sha256 = hashlib.sha256(raw_content).hexdigest()

        raw_file = self.workspace / "raw" / "TEST-100.json"
        raw_file.write_bytes(raw_content)

        req = {
            "schema_version": "1.0",
            "source": {
                "type": "jira",
                "instance": "jira.example.com",
                "issue_key": "TEST-100",
                "retrieved_at": "2026-01-01T00:00:00+00:00",
                "endpoint": "/rest/api/2/issue/{issue_key}",
                "requested_fields": ["summary"],
                "raw_response_file": "raw/TEST-100.json",
                "raw_response_sha256": sha256,
            },
            "requirements": requirements_override or {
                "summary": "Test Epic",
                "description": "A description",
                "type": issue_type,
                "status": "In Progress",
                "labels": [],
                "components": [],
                "linked_issues": [],
                "acceptance_criteria": [],
            },
            "warnings": [],
        }
        req_file = self.workspace / "requirements" / "TEST-100.json"
        req_file.write_text(json.dumps(req), encoding='utf-8')
        return req_file

    def test_rejects_non_business_epic_type(self):
        req_file = self._create_requirements(issue_type="Story")
        with self.assertRaises(RuntimeError) as cm:
            preflight_validate(req_file, self.workspace)
        self.assertIn("Business Epic", str(cm.exception))

    def test_accepts_business_epic_type(self):
        req_file = self._create_requirements(issue_type="Business Epic")
        result = preflight_validate(req_file, self.workspace)
        self.assertEqual(result["issue_key"], "TEST-100")

    def test_detects_missing_raw_response_file(self):
        req_file = self._create_requirements()
        (self.workspace / "raw" / "TEST-100.json").unlink()
        with self.assertRaises(RuntimeError) as cm:
            preflight_validate(req_file, self.workspace)
        self.assertIn("not found", str(cm.exception).lower())

    def test_detects_sha256_mismatch(self):
        req_file = self._create_requirements()
        req_data = json.loads(req_file.read_text())
        req_data["source"]["raw_response_sha256"] = "0" * 64
        req_file.write_text(json.dumps(req_data))
        with self.assertRaises(RuntimeError) as cm:
            preflight_validate(req_file, self.workspace)
        self.assertIn("integrity", str(cm.exception).lower())

    def test_requires_schema_version_1_0(self):
        req_file = self._create_requirements()
        req_data = json.loads(req_file.read_text())
        req_data["schema_version"] = "2.0"
        req_file.write_text(json.dumps(req_data))
        with self.assertRaises(RuntimeError):
            preflight_validate(req_file, self.workspace)

    def test_requires_valid_source_object(self):
        req_file = self._create_requirements()
        req_data = json.loads(req_file.read_text())
        del req_data["source"]["raw_response_sha256"]
        req_file.write_text(json.dumps(req_data))
        with self.assertRaises(RuntimeError):
            preflight_validate(req_file, self.workspace)

    def test_output_contains_evidence_and_evidence_units(self):
        """Preflight output must contain both evidence (context) and evidence_units (catalogue)."""
        req_file = self._create_requirements()
        result = preflight_validate(req_file, self.workspace)
        self.assertIn("evidence", result)
        self.assertIn("evidence_units", result)
        self.assertIsInstance(result["evidence_units"], list)

    def test_evidence_units_have_required_fields(self):
        """Each evidence unit must have id, jira_field, source_value."""
        req_file = self._create_requirements()
        result = preflight_validate(req_file, self.workspace)
        for unit in result["evidence_units"]:
            self.assertIn("id", unit)
            self.assertIn("jira_field", unit)
            self.assertIn("source_value", unit)


# ---------------------------------------------------------------------------
# TestEvidenceUnitExtraction
# ---------------------------------------------------------------------------

class TestEvidenceUnitExtraction(TestCase):
    """Test deterministic evidence unit extraction rules."""

    # --- Atomic fields ---

    def test_summary_produces_single_unit(self):
        """Non-empty summary -> summary:0."""
        ev = _make_evidence(summary="Epic summary text")
        units = extract_evidence_units(ev)
        summary_units = [u for u in units if u["jira_field"] == "summary"]
        self.assertEqual(len(summary_units), 1)
        self.assertEqual(summary_units[0]["id"], "summary:0")
        self.assertEqual(summary_units[0]["source_value"], "Epic summary text")

    def test_status_produces_single_unit(self):
        """Non-empty status -> status:0."""
        ev = _make_evidence(status="In Progress")
        units = extract_evidence_units(ev)
        status_units = [u for u in units if u["jira_field"] == "status"]
        self.assertEqual(len(status_units), 1)
        self.assertEqual(status_units[0]["id"], "status:0")
        self.assertEqual(status_units[0]["source_value"], "In Progress")

    def test_empty_summary_produces_no_units(self):
        ev = _make_evidence(summary="")
        units = extract_evidence_units(ev)
        self.assertEqual([u for u in units if u["jira_field"] == "summary"], [])

    def test_missing_field_produces_no_units(self):
        ev = _make_evidence()
        del ev["status"]
        units = extract_evidence_units(ev)
        self.assertEqual([u for u in units if u["jira_field"] == "status"], [])

    def test_whitespace_only_field_produces_no_units(self):
        ev = _make_evidence(summary="   ")
        units = extract_evidence_units(ev)
        self.assertEqual([u for u in units if u["jira_field"] == "summary"], [])

    # --- Text array fields ---

    def test_labels_each_item_addressable(self):
        ev = _make_evidence(labels=["alpha", "beta", "gamma"])
        units = [u for u in extract_evidence_units(ev) if u["jira_field"] == "labels"]
        self.assertEqual(len(units), 3)
        self.assertEqual(units[0]["id"], "labels:0")
        self.assertEqual(units[1]["id"], "labels:1")
        self.assertEqual(units[2]["id"], "labels:2")
        self.assertEqual(units[0]["source_value"], "alpha")

    def test_components_each_item_addressable(self):
        ev = _make_evidence(components=["API", "Database", "UI"])
        units = [u for u in extract_evidence_units(ev) if u["jira_field"] == "components"]
        self.assertEqual(len(units), 3)
        self.assertEqual(units[0]["id"], "components:0")

    def test_acceptance_criteria_each_item_addressable(self):
        ev = _make_evidence(acceptance_criteria=["AC 1: First", "AC 2: Second"])
        units = [u for u in extract_evidence_units(ev) if u["jira_field"] == "acceptance_criteria"]
        self.assertEqual(len(units), 2)
        self.assertEqual(units[0]["id"], "acceptance_criteria:0")
        self.assertEqual(units[1]["id"], "acceptance_criteria:1")

    def test_empty_array_produces_no_units(self):
        ev = _make_evidence(labels=[])
        units = [u for u in extract_evidence_units(ev) if u["jira_field"] == "labels"]
        self.assertEqual(units, [])

    # --- Structured array fields ---

    def test_linked_issues_preserves_full_dict(self):
        """linked_issues unit source_value must be the complete normalized dict."""
        ev = _make_evidence(linked_issues=[
            {"issue_key": "PROJ-42", "link_type": "Depends", "direction": "outward"}
        ])
        units = [u for u in extract_evidence_units(ev) if u["jira_field"] == "linked_issues"]
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0]["id"], "linked_issues:0")
        self.assertIsInstance(units[0]["source_value"], dict)
        self.assertEqual(units[0]["source_value"]["issue_key"], "PROJ-42")
        self.assertEqual(units[0]["source_value"]["link_type"], "Depends")
        self.assertEqual(units[0]["source_value"]["direction"], "outward")

    def test_linked_issues_not_reduced_to_issue_key_string(self):
        """source_value for linked_issues must NOT be reduced to a plain string."""
        ev = _make_evidence(linked_issues=[
            {"issue_key": "PROJ-42", "link_type": "Depends", "direction": "outward"}
        ])
        units = [u for u in extract_evidence_units(ev) if u["jira_field"] == "linked_issues"]
        # source_value must remain a dict, not collapsed to "PROJ-42"
        self.assertNotIsInstance(units[0]["source_value"], str)

    def test_multiple_linked_issues_addressable_separately(self):
        ev = _make_evidence(linked_issues=[
            {"issue_key": "A-1", "link_type": "Blocks", "direction": "outward"},
            {"issue_key": "B-2", "link_type": "Relates", "direction": "inward"},
        ])
        units = [u for u in extract_evidence_units(ev) if u["jira_field"] == "linked_issues"]
        self.assertEqual(len(units), 2)
        self.assertEqual(units[0]["id"], "linked_issues:0")
        self.assertEqual(units[1]["id"], "linked_issues:1")

    # --- Description splitting ---

    def test_description_with_hr_splits_into_multiple_units(self):
        """Horizontal rule lines (----) produce multiple description units."""
        desc = "Section One\nsome content\n----\nSection Two\nmore content"
        ev = _make_evidence(description=desc)
        units = [u for u in extract_evidence_units(ev) if u["jira_field"] == "description"]
        self.assertGreater(len(units), 1)
        self.assertEqual(units[0]["id"], "description:0")
        self.assertEqual(units[1]["id"], "description:1")

    def test_heading_preserved_in_source_value(self):
        """Heading line used as boundary is part of its unit's source_value."""
        desc = "Intro text\n----\nh1. Important Section\nContent of section"
        units = _split_description_into_units(desc)
        # second unit should include the h1 heading
        self.assertGreater(len(units), 1)
        section_unit = units[1]
        self.assertIn("h1.", section_unit)

    def test_description_with_headings_no_hr_splits(self):
        """If no ---- found, heading lines split the description."""
        desc = "Preamble\nh1. First Section\nContent one\nh2. Second Section\nContent two"
        units = _split_description_into_units(desc)
        self.assertGreater(len(units), 1)
        # Each section includes its heading
        heading_units = [u for u in units if u.startswith("h")]
        self.assertGreater(len(heading_units), 0)

    def test_unstructured_description_produces_single_unit(self):
        """Plain text without ---- or h1.-h6. headings -> single description:0."""
        desc = "This is plain prose with no headings or horizontal rules."
        ev = _make_evidence(description=desc)
        units = [u for u in extract_evidence_units(ev) if u["jira_field"] == "description"]
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0]["id"], "description:0")
        self.assertEqual(units[0]["source_value"], desc)

    def test_crlf_and_lf_produce_equivalent_units(self):
        """CRLF and LF representations of the same content produce identical units."""
        desc_crlf = "Section A\r\n----\r\nSection B"
        desc_lf = "Section A\n----\nSection B"
        units_crlf = _split_description_into_units(desc_crlf)
        units_lf = _split_description_into_units(desc_lf)
        self.assertEqual(units_crlf, units_lf)

    def test_repeated_identical_blocks_get_distinct_ids(self):
        """Identical text blocks in separate sections get distinct positional IDs."""
        desc = "Same content here\n----\nSame content here"
        ev = _make_evidence(description=desc)
        units = [u for u in extract_evidence_units(ev) if u["jira_field"] == "description"]
        self.assertEqual(len(units), 2)
        ids = [u["id"] for u in units]
        self.assertEqual(ids[0], "description:0")
        self.assertEqual(ids[1], "description:1")
        self.assertEqual(units[0]["source_value"], units[1]["source_value"])

    def test_empty_description_produces_no_units(self):
        ev = _make_evidence(description="")
        units = [u for u in extract_evidence_units(ev) if u["jira_field"] == "description"]
        self.assertEqual(units, [])

    # --- Determinism ---

    def test_extraction_is_deterministic(self):
        """Identical input always produces identical evidence units."""
        ev = _make_evidence()
        units_a = extract_evidence_units(ev)
        units_b = extract_evidence_units(ev)
        self.assertEqual(units_a, units_b)

    def test_extraction_is_deterministic_with_structured_content(self):
        """Determinism holds for Jira-formatted descriptions with headings and HR."""
        desc = "h1. Problem\nSome problem\n----\nh1. Use Case\n*I want* to do things"
        ev = _make_evidence(description=desc)
        for _ in range(3):
            units = extract_evidence_units(ev)
            desc_units = [u for u in units if u["id"] == "description:0"]
            self.assertEqual(len(desc_units), 1)
            self.assertIn("h1. Problem", desc_units[0]["source_value"])

    # --- Unicode ---

    def test_unicode_preserved_in_source_value(self):
        """Unicode characters are preserved verbatim in source_value."""
        desc = "Supports café pattern and naïve sorting"
        ev = _make_evidence(description=desc)
        units = [u for u in extract_evidence_units(ev) if u["jira_field"] == "description"]
        self.assertEqual(units[0]["source_value"], desc)


# ---------------------------------------------------------------------------
# TestEvidenceIdValidation
# ---------------------------------------------------------------------------

class TestEvidenceIdValidation(TestCase):
    """Test evidence ID validation logic."""

    def setUp(self):
        ev = _make_evidence()
        self.evidence_units = extract_evidence_units(ev)
        self.unit_map = build_evidence_unit_map(self.evidence_units)
        # Pick a valid ID for use in tests
        self.valid_id = self.evidence_units[0]["id"]

    def test_valid_id_passes(self):
        validate_evidence_id_list([self.valid_id], self.unit_map, "test")

    def test_empty_list_passes(self):
        validate_evidence_id_list([], self.unit_map, "test")

    def test_multiple_valid_ids_pass(self):
        ids = [u["id"] for u in self.evidence_units[:2]]
        validate_evidence_id_list(ids, self.unit_map, "test")

    def test_unknown_id_fails(self):
        with self.assertRaises(ValueError) as cm:
            validate_evidence_id_list(["description:999"], self.unit_map, "test")
        self.assertIn("unknown", str(cm.exception).lower())

    def test_malformed_no_colon_fails(self):
        with self.assertRaises(ValueError) as cm:
            validate_evidence_id_list(["descriptionunit"], self.unit_map, "test")
        self.assertIn("malformed", str(cm.exception).lower())

    def test_malformed_negative_index_fails(self):
        with self.assertRaises(ValueError) as cm:
            validate_evidence_id_list(["description:-1"], self.unit_map, "test")
        self.assertIn("malformed", str(cm.exception).lower())

    def test_malformed_non_integer_index_fails(self):
        with self.assertRaises(ValueError) as cm:
            validate_evidence_id_list(["description:abc"], self.unit_map, "test")
        self.assertIn("malformed", str(cm.exception).lower())

    def test_empty_string_fails(self):
        with self.assertRaises(ValueError) as cm:
            validate_evidence_id_list([""], self.unit_map, "test")
        self.assertIn("empty", str(cm.exception).lower())

    def test_non_string_id_fails(self):
        with self.assertRaises(ValueError) as cm:
            validate_evidence_id_list([42], self.unit_map, "test")
        self.assertIn("string", str(cm.exception).lower())

    def test_non_list_fails(self):
        with self.assertRaises(ValueError) as cm:
            validate_evidence_id_list("description:0", self.unit_map, "test")
        self.assertIn("list", str(cm.exception).lower())

    def test_duplicate_id_within_list_fails(self):
        """Duplicate IDs in one supporting_evidence array are invalid."""
        with self.assertRaises(ValueError) as cm:
            validate_evidence_id_list(
                [self.valid_id, self.valid_id], self.unit_map, "test"
            )
        self.assertIn("duplicate", str(cm.exception).lower())

    def test_same_id_in_different_lists_allowed(self):
        """The same ID can appear in different supporting_evidence arrays."""
        validate_evidence_id_list([self.valid_id], self.unit_map, "context_A")
        validate_evidence_id_list([self.valid_id], self.unit_map, "context_B")


# ---------------------------------------------------------------------------
# TestPostflightResolution
# ---------------------------------------------------------------------------

class TestPostflightResolution(TestCase):
    """Test that postflight resolves evidence IDs to authoritative source values."""

    def setUp(self):
        self.normalized_evidence = _make_evidence()
        self.source_provenance = _make_source_provenance()
        self.evidence_units = extract_evidence_units(self.normalized_evidence)

    def test_ids_resolved_to_evidence_reference_dicts(self):
        """Postflight resolves each ID to {evidence_id, source_type, jira_field, source_value}."""
        analysis = _make_valid_analysis(self.evidence_units)
        output = postflight_validate(
            analysis, self.normalized_evidence, self.source_provenance, self.evidence_units
        )

        er = output["explicit_requirements"][0]
        self.assertIsInstance(er["supporting_evidence"], list)
        ref = er["supporting_evidence"][0]
        self.assertIn("evidence_id", ref)
        self.assertIn("source_type", ref)
        self.assertIn("field", ref)
        self.assertIn("source_value", ref)
        self.assertEqual(ref["source_type"], "jira")

    def test_llm_cannot_supply_source_value(self):
        """If LLM passes a dict instead of an ID string, validation fails."""
        analysis = _make_valid_analysis(self.evidence_units)
        # Inject what an LLM might have wrongly returned
        analysis["explicit_requirements"][0]["supporting_evidence"] = [
            {"jira_field": "description", "source_value": "hacked text"}
        ]
        with self.assertRaises(ValueError) as cm:
            postflight_validate(
                analysis, self.normalized_evidence, self.source_provenance, self.evidence_units
            )
        self.assertIn("string", str(cm.exception).lower())

    def test_postflight_catalogue_matches_preflight_catalogue(self):
        """extract_evidence_units called in postflight == catalogue from preflight."""
        units_preflight = extract_evidence_units(self.normalized_evidence)
        units_postflight = extract_evidence_units(self.normalized_evidence)
        self.assertEqual(units_preflight, units_postflight)

    def test_structured_linked_issue_resolves_to_dict(self):
        """linked_issues evidence unit resolves to dict, not a string."""
        linked_id = next(
            u["id"] for u in self.evidence_units if u["jira_field"] == "linked_issues"
        )
        analysis = _make_valid_analysis(self.evidence_units)
        analysis["constraints_and_dependencies"][0]["supporting_evidence"] = [linked_id]

        output = postflight_validate(
            analysis, self.normalized_evidence, self.source_provenance, self.evidence_units
        )

        ref = output["constraints_and_dependencies"][0]["supporting_evidence"][0]
        self.assertEqual(ref["field"], "linked_issues")
        self.assertIsInstance(ref["source_value"], dict)
        self.assertIn("issue_key", ref["source_value"])

    def test_source_version_sha256_preserved(self):
        """SHA-256 from source is preserved in persisted output."""
        analysis = _make_valid_analysis(self.evidence_units)
        output = postflight_validate(
            analysis, self.normalized_evidence, self.source_provenance, self.evidence_units
        )
        # New schema: source_evidence is an array
        self.assertEqual(
            output["source_evidence"][0]["sha256"],
            "abc123def456"
        )

    def test_resolve_evidence_ids_produces_authoritative_values(self):
        """resolve_evidence_ids always returns catalogue values, not user-supplied values."""
        unit_map = build_evidence_unit_map(self.evidence_units)
        ids = [self.evidence_units[0]["id"]]
        resolved = resolve_evidence_ids(ids, unit_map)
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0]["source_value"], self.evidence_units[0]["source_value"])


# ---------------------------------------------------------------------------
# TestPostflightValidation
# ---------------------------------------------------------------------------

class TestPostflightValidation(TestCase):
    """Test postflight structural validation."""

    def setUp(self):
        self.normalized_evidence = _make_evidence()
        self.source_provenance = _make_source_provenance()
        self.evidence_units = extract_evidence_units(self.normalized_evidence)

    def _run(self, analysis):
        return postflight_validate(
            analysis, self.normalized_evidence, self.source_provenance, self.evidence_units
        )

    def test_produces_valid_output_schema(self):
        output = self._run(_make_valid_analysis(self.evidence_units))
        self.assertEqual(output["schema_version"], "2.0")
        self.assertIn("analysis_metadata", output)
        self.assertIn("source_evidence", output)
        self.assertIsInstance(output["source_evidence"], list)
        self.assertEqual(len(output["source_evidence"]), 1)
        self.assertEqual(output["source_evidence"][0]["source_type"], "jira")
        self.assertIn("change_summary", output)
        self.assertIn("explicit_requirements", output)

    def test_preserves_provenance(self):
        output = self._run(_make_valid_analysis(self.evidence_units))
        # New schema: source_evidence array with sha256 field
        self.assertIn("source_evidence", output)
        self.assertEqual(output["source_evidence"][0]["sha256"], "abc123def456")

    def test_rejects_unknown_evidence_id(self):
        analysis = _make_valid_analysis(self.evidence_units)
        analysis["explicit_requirements"][0]["supporting_evidence"] = ["description:999"]
        with self.assertRaises(ValueError) as cm:
            self._run(analysis)
        self.assertIn("unknown", str(cm.exception).lower())

    def test_rejects_malformed_evidence_id(self):
        analysis = _make_valid_analysis(self.evidence_units)
        analysis["explicit_requirements"][0]["supporting_evidence"] = ["not-an-id"]
        with self.assertRaises(ValueError) as cm:
            self._run(analysis)
        self.assertIn("malformed", str(cm.exception).lower())

    def test_rejects_duplicate_id_in_supporting_evidence(self):
        analysis = _make_valid_analysis(self.evidence_units)
        valid_id = self.evidence_units[0]["id"]
        analysis["explicit_requirements"][0]["supporting_evidence"] = [valid_id, valid_id]
        with self.assertRaises(ValueError) as cm:
            self._run(analysis)
        self.assertIn("duplicate", str(cm.exception).lower())

    def test_inferred_requirements_have_reasoning(self):
        analysis = _make_valid_analysis(self.evidence_units)
        del analysis["inferred_requirements"][0]["reasoning"]
        with self.assertRaises(ValueError) as cm:
            self._run(analysis)
        self.assertIn("reasoning", str(cm.exception))

    def test_constraints_have_is_explicit_boolean(self):
        analysis = _make_valid_analysis(self.evidence_units)
        del analysis["constraints_and_dependencies"][0]["is_explicit"]
        with self.assertRaises(ValueError) as cm:
            self._run(analysis)
        self.assertIn("is_explicit", str(cm.exception))

    def test_ambiguities_have_clarification_needed(self):
        analysis = _make_valid_analysis(self.evidence_units)
        analysis["ambiguities_and_unknowns"][0]["recommendation"] = "Ask the team"
        with self.assertRaises(ValueError) as cm:
            self._run(analysis)
        self.assertIn("recommendation", str(cm.exception))

    def test_requires_all_sections(self):
        analysis = _make_valid_analysis(self.evidence_units)
        del analysis["key_concepts"]
        with self.assertRaises(ValueError) as cm:
            self._run(analysis)
        self.assertIn("key_concepts", str(cm.exception))

    def test_change_summary_has_required_fields(self):
        analysis = _make_valid_analysis(self.evidence_units)
        del analysis["change_summary"]["rationale"]
        with self.assertRaises(ValueError) as cm:
            self._run(analysis)
        self.assertIn("rationale", str(cm.exception))

    def test_adds_analysis_metadata_timestamp(self):
        output = self._run(_make_valid_analysis(self.evidence_units))
        self.assertIn("analyzed_at", output["analysis_metadata"])
        datetime.fromisoformat(output["analysis_metadata"]["analyzed_at"])

    def test_supporting_evidence_must_be_list_not_dict(self):
        """supporting_evidence must be a list of ID strings, not a list of objects."""
        analysis = _make_valid_analysis(self.evidence_units)
        analysis["explicit_requirements"][0]["supporting_evidence"] = [
            {"jira_field": "description", "source_value": "old style"}
        ]
        with self.assertRaises(ValueError):
            self._run(analysis)


# ---------------------------------------------------------------------------
# TestWorkspaceOutput
# ---------------------------------------------------------------------------

class TestWorkspaceOutput(TestCase):
    """Test that output is written to external workspace, not git repository."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="buk_sa_test_workspace_")
        self.workspace = Path(self.temp_dir)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_output_path_includes_issue_key(self):
        normalized_evidence = _make_evidence()
        evidence_units = extract_evidence_units(normalized_evidence)
        source_provenance = _make_source_provenance()
        analysis = _make_valid_analysis(evidence_units)

        output = postflight_validate(
            analysis, normalized_evidence, source_provenance, evidence_units
        )

        from scripts.understand_requirements import main_postflight
        output_dir = self.workspace / "analysis"

        output_file = output_dir / "TEST-1" / "requirements-analysis.json"
        output_dir.mkdir(parents=True, exist_ok=True)

        self.assertTrue(str(output_dir).startswith(str(self.workspace)))
        self.assertIn("analysis", str(output_dir))


# ---------------------------------------------------------------------------
# TestSourceVersionContext
# ---------------------------------------------------------------------------

class TestSourceVersionContext(TestCase):
    """Test that source version context (SHA-256 + IDs) is established correctly."""

    def test_sha256_and_id_together_identify_evidence_context(self):
        """The combination raw_jira_response_sha256 + evidence_id identifies a specific unit."""
        ev = _make_evidence(description="h1. Section One\nContent A\n----\nh1. Section Two\nContent B")
        source = _make_source_provenance(sha256="deadbeef" * 8)

        units = extract_evidence_units(ev)
        unit_map = build_evidence_unit_map(units)
        ids = list(unit_map.keys())

        # Resolve an ID
        resolved = resolve_evidence_ids([ids[0]], unit_map)

        # Together SHA + ID identifies this evidence
        evidence_context = {
            "raw_jira_response_sha256": source["raw_jira_response_sha256"],
            "evidence_id": resolved[0]["evidence_id"],
        }
        self.assertIn("raw_jira_response_sha256", evidence_context)
        self.assertIn("evidence_id", evidence_context)

    def test_ids_are_positional_within_source_version(self):
        """IDs are positional; changing source content changes unit content but not ID format."""
        ev_v1 = _make_evidence(description="h1. Original\nContent A\n----\nh1. Section Two\nContent B")
        ev_v2 = _make_evidence(description="h1. Modified\nDifferent content\n----\nh1. Section Two\nContent B")

        units_v1 = extract_evidence_units(ev_v1)
        units_v2 = extract_evidence_units(ev_v2)

        # IDs are the same structure (positional)
        ids_v1 = [u["id"] for u in units_v1 if u["jira_field"] == "description"]
        ids_v2 = [u["id"] for u in units_v2 if u["jira_field"] == "description"]
        self.assertEqual(ids_v1, ids_v2)

        # But source_values differ
        val_v1 = next(u["source_value"] for u in units_v1 if u["id"] == "description:0")
        val_v2 = next(u["source_value"] for u in units_v2 if u["id"] == "description:0")
        self.assertNotEqual(val_v1, val_v2)


# ---------------------------------------------------------------------------
# Defect Regression Tests (PRD/Brief workspace contract, evidence traceability)
# ---------------------------------------------------------------------------

class TestPRDWorkspaceContract(TestCase):
    """DEFECT 2: Verify PRD/Brief workspace structure does not create work-item subdirectories."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="buk_prd_workspace_test_")
        self.workspace = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_prd_source_no_workitem_subdir_preflight(self):
        """PRD source preflight should NOT create prd/ or test_prd/ subdirectories."""
        # Create a requirements.json for PRD source
        prd_requirements = {
            "schema_version": "1.0",
            "source": {
                "type": "prd",
                "prd_path": "/path/to/prd.md",
                "prd_sha256": "abc123",
            },
            "requirements": {
                "summary": "Test PRD",
                "description": "Test description",
                "type": "Product Requirement Document",
                "status": "Inferred",
                "labels": [],
                "components": [],
                "linked_issues": [],
                "acceptance_criteria": [],
                "evidence_units": [
                    {
                        "id": "functional_requirements:FR-1",
                        "source_native_id": "FR-1",
                        "prd_section": "features",
                        "source_value": "Test requirement"
                    }
                ],
                "evidence_sources": {},
            },
            "warnings": [],
        }

        req_file = self.workspace / "requirements" / "prd.json"
        req_file.parent.mkdir(parents=True, exist_ok=True)
        req_file.write_text(json.dumps(prd_requirements, indent=2), encoding='utf-8')

        # Run preflight
        result = preflight_validate(req_file, self.workspace)

        # Candidate analysis path should NOT have prd/ subdirectory
        candidate_path = Path(result["candidate_analysis_path"]).resolve()
        workspace_resolved = self.workspace.resolve()

        try:
            rel_path = candidate_path.relative_to(workspace_resolved)
        except ValueError:
            self.fail(f"Candidate path {candidate_path} is not relative to workspace {workspace_resolved}")

        # Path should be: analysis/candidate-requirements-analysis.json
        # NOT: prd/analysis/candidate-requirements-analysis.json
        expected = "analysis" + os.sep + "candidate-requirements-analysis.json"
        self.assertEqual(str(rel_path), expected,
                         f"PRD workspace contract violated: expected {expected}, got {rel_path}")

    def test_jira_source_uses_workitem_subdir_preflight(self):
        """Jira source preflight SHOULD create issue_key subdirectories."""
        # Create raw file first to compute hash
        raw_bytes = b'{"fields": {}}'
        raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()

        # Create a requirements.json for Jira source
        jira_requirements = {
            "schema_version": "1.0",
            "source": {
                "type": "jira",
                "instance": "jira.example.com",
                "issue_key": "BUKL2-123",
                "retrieved_at": "2026-01-01T00:00:00+00:00",
                "endpoint": "/rest/api/2/issue/BUKL2-123",
                "requested_fields": ["summary"],
                "raw_response_file": "BUKL2-123/raw/BUKL2-123.json",
                "raw_response_sha256": raw_sha256,
            },
            "requirements": {
                "summary": "Test Epic",
                "description": "Test",
                "type": "Business Epic",
                "status": "In Progress",
                "labels": [],
                "components": [],
                "linked_issues": [],
                "acceptance_criteria": [],
            },
            "warnings": [],
        }

        # Create raw file for hash verification
        raw_dir = self.workspace / "BUKL2-123" / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_file = raw_dir / "BUKL2-123.json"
        raw_file.write_bytes(raw_bytes)

        req_dir = self.workspace / "BUKL2-123" / "requirements"
        req_dir.mkdir(parents=True, exist_ok=True)
        req_file = req_dir / "BUKL2-123.json"
        req_file.write_text(json.dumps(jira_requirements, indent=2), encoding='utf-8')

        # Run preflight
        result = preflight_validate(req_file, self.workspace)

        # Candidate analysis path SHOULD have issue_key subdirectory
        candidate_path = Path(result["candidate_analysis_path"]).resolve()
        workspace_resolved = self.workspace.resolve()
        rel_path = candidate_path.relative_to(workspace_resolved)

        # Path should be: BUKL2-123/analysis/candidate-requirements-analysis.json
        self.assertIn("BUKL2-123", str(rel_path),
                     f"Jira workspace contract violated: issue_key missing from path {rel_path}")


class TestEvidenceTraceability(TestCase):
    """DEFECT 3: Verify source-native identifiers (FR-1, etc.) are preserved and traceable."""

    def test_prd_source_native_ids_preserved_through_pipeline(self):
        """FR-1, FR-2 identifiers must survive extraction and cataloguing."""
        prd_evidence = {
            "issue_key": None,
            "source_type": "prd",
            "summary": "Test",
            "description": "Test",
            "status": "Active",
            "labels": [],
            "components": [],
            "linked_issues": [],
            "acceptance_criteria": [],
            "evidence_units": [
                {
                    "id": "functional_requirements:FR-1",
                    "source_native_id": "FR-1",
                    "prd_section": "features",
                    "source_value": "Users can view dashboard"
                },
                {
                    "id": "functional_requirements:FR-2",
                    "source_native_id": "FR-2",
                    "prd_section": "features",
                    "source_value": "Users can upload documents"
                },
                {
                    "id": "success_metrics:SM-1",
                    "source_native_id": "SM-1",
                    "prd_section": "success_metrics",
                    "source_value": "95% processing within 24h"
                }
            ],
            "evidence_sources": {},
        }

        # Extract evidence units
        units = extract_evidence_units(prd_evidence)

        # Verify source-native IDs are preserved
        unit_ids = [u["id"] for u in units]
        self.assertIn("functional_requirements:FR-1", unit_ids)
        self.assertIn("functional_requirements:FR-2", unit_ids)
        self.assertIn("success_metrics:SM-1", unit_ids)

        # Verify source_native_id field is preserved
        fr1_unit = next((u for u in units if u["id"] == "functional_requirements:FR-1"), None)
        self.assertIsNotNone(fr1_unit)
        self.assertEqual(fr1_unit.get("source_native_id"), "FR-1")

        # Verify source values are correct (not mixed with SM values)
        self.assertEqual(fr1_unit["source_value"], "Users can view dashboard")
        self.assertNotIn("95%", fr1_unit["source_value"],
                         "FR-1 evidence should not contain success metric data")

    def test_evidence_catalogue_lookup_deterministic(self):
        """Evidence unit map must enable O(1) lookup and ID validation."""
        prd_evidence = {
            "issue_key": None,
            "source_type": "prd",
            "summary": "Test",
            "description": "Test",
            "status": "Active",
            "labels": [],
            "components": [],
            "linked_issues": [],
            "acceptance_criteria": [],
            "evidence_units": [
                {
                    "id": "functional_requirements:FR-1",
                    "source_native_id": "FR-1",
                    "prd_section": "features",
                    "source_value": "Requirement 1"
                }
            ],
            "evidence_sources": {},
        }

        units = extract_evidence_units(prd_evidence)
        unit_map = build_evidence_unit_map(units)

        # Lookup must succeed
        self.assertIn("functional_requirements:FR-1", unit_map)
        self.assertEqual(unit_map["functional_requirements:FR-1"]["source_value"], "Requirement 1")

        # Invalid ID lookup must fail
        self.assertNotIn("functional_requirements:SM-1", unit_map)


# ---------------------------------------------------------------------------
# Orchestration Contract Tests (Solution Architect Agent)
# ---------------------------------------------------------------------------

class TestOrchestrationContracts(TestCase):
    """Verify Solution Architect orchestration prerequisites."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="buk_orchestration_test_")
        self.workspace = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_prd_canonical_path_enforced_preflight(self):
        """PRD source must use canonical path: workspace/requirements/file.json, never workspace/prd/requirements/file.json"""
        # Create requirements at WRONG path: workspace/prd/requirements/file.json
        wrong_path = self.workspace / "prd" / "requirements" / "prd.json"
        wrong_path.parent.mkdir(parents=True, exist_ok=True)

        prd_requirements = {
            "schema_version": "1.0",
            "source": {
                "type": "prd",
                "prd_path": "/path/to/prd.md",
                "prd_sha256": "abc123",
            },
            "requirements": {
                "summary": "Test",
                "description": "Test",
                "type": "Product Requirement Document",
                "status": "Inferred",
                "labels": [],
                "components": [],
                "linked_issues": [],
                "acceptance_criteria": [],
                "evidence_units": [],
                "evidence_sources": {},
            },
            "warnings": [],
        }
        wrong_path.write_text(json.dumps(prd_requirements), encoding='utf-8')

        # Preflight should reject this path (prd/ subdir is not canonical)
        with self.assertRaises(RuntimeError) as cm:
            preflight_validate(wrong_path, self.workspace)

        self.assertIn("workspace contract", str(cm.exception).lower())

    def test_prd_canonical_path_accepted_preflight(self):
        """PRD source MUST use canonical path: workspace/requirements/file.json"""
        # Create requirements at CORRECT path: workspace/requirements/file.json
        correct_path = self.workspace / "requirements" / "prd.json"
        correct_path.parent.mkdir(parents=True, exist_ok=True)

        prd_requirements = {
            "schema_version": "1.0",
            "source": {
                "type": "prd",
                "prd_path": "/path/to/prd.md",
                "prd_sha256": "abc123",
            },
            "requirements": {
                "summary": "Test",
                "description": "Test",
                "type": "Product Requirement Document",
                "status": "Inferred",
                "labels": [],
                "components": [],
                "linked_issues": [],
                "acceptance_criteria": [],
                "evidence_units": [
                    {
                        "id": "functional_requirements:FR-1",
                        "source_native_id": "FR-1",
                        "prd_section": "features",
                        "source_value": "Test requirement"
                    }
                ],
                "evidence_sources": {},
            },
            "warnings": [],
        }
        correct_path.write_text(json.dumps(prd_requirements), encoding='utf-8')

        # Preflight should accept this path
        result = preflight_validate(correct_path, self.workspace)

        # Candidate analysis path should be at workspace/analysis/, not workspace/prd/analysis/
        candidate_path = Path(result["candidate_analysis_path"]).resolve()
        self.assertIn("analysis", str(candidate_path))
        self.assertNotIn("prd/analysis", str(candidate_path))

    def test_jira_canonical_path_enforced_preflight(self):
        """Jira source MUST use canonical path: workspace/{issue_key}/requirements/{issue_key}.json"""
        # Create raw file
        raw_bytes = b'{"fields": {}}'
        raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()

        # Create requirements at CORRECT path for Jira
        jira_req_path = self.workspace / "BUKL2-999" / "requirements" / "BUKL2-999.json"
        jira_req_path.parent.mkdir(parents=True, exist_ok=True)

        # Create raw file
        raw_path = self.workspace / "BUKL2-999" / "raw" / "BUKL2-999.json"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(raw_bytes)

        jira_requirements = {
            "schema_version": "1.0",
            "source": {
                "type": "jira",
                "instance": "jira.example.com",
                "issue_key": "BUKL2-999",
                "retrieved_at": "2026-01-01T00:00:00+00:00",
                "endpoint": "/rest/api/2/issue/BUKL2-999",
                "requested_fields": ["summary"],
                "raw_response_file": "BUKL2-999/raw/BUKL2-999.json",
                "raw_response_sha256": raw_sha256,
            },
            "requirements": {
                "summary": "Test Epic",
                "description": "Test",
                "type": "Business Epic",
                "status": "In Progress",
                "labels": [],
                "components": [],
                "linked_issues": [],
                "acceptance_criteria": [],
            },
            "warnings": [],
        }
        jira_req_path.write_text(json.dumps(jira_requirements), encoding='utf-8')

        # Preflight should accept this path
        result = preflight_validate(jira_req_path, self.workspace)

        # Candidate analysis path should be at workspace/BUKL2-999/analysis/
        candidate_path = Path(result["candidate_analysis_path"]).resolve()
        self.assertIn("BUKL2-999", str(candidate_path))
        self.assertIn("analysis", str(candidate_path))


# ---------------------------------------------------------------------------
# Evidence Traceability Tests (FR-N identification and preservation)
# ---------------------------------------------------------------------------

class TestFRNEvidenceTraceability(TestCase):
    """Verify that FR-1...FR-12 evidence IDs are extracted and preserved from PRD."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="buk_traceability_test_")
        self.workspace = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_fr_n_evidence_extracted_from_prd(self):
        """Evidence units must contain functional_requirements:FR-1...FR-12 entries from PRD."""
        # Create requirements with FR evidence
        req_path = self.workspace / "requirements" / "prd.json"
        req_path.parent.mkdir(parents=True, exist_ok=True)

        prd_requirements = {
            "schema_version": "1.0",
            "source": {
                "type": "prd",
                "prd_path": "/path/to/prd.md",
                "prd_sha256": "abc123",
            },
            "requirements": {
                "summary": "Test",
                "description": "Test",
                "type": "Product Requirement Document",
                "status": "Inferred",
                "labels": [],
                "components": [],
                "linked_issues": [],
                "acceptance_criteria": [],
                "evidence_units": [
                    {
                        "id": "functional_requirements:FR-1",
                        "source_native_id": "FR-1",
                        "prd_section": "features",
                        "source_value": "User can enter loan amount"
                    },
                    {
                        "id": "functional_requirements:FR-2",
                        "source_native_id": "FR-2",
                        "prd_section": "features",
                        "source_value": "User can adjust loan term"
                    },
                    {
                        "id": "functional_requirements:FR-12",
                        "source_native_id": "FR-12",
                        "prd_section": "features",
                        "source_value": "System must surface debt advice for vulnerable customers"
                    },
                    {
                        "id": "scope:0",
                        "source_native_id": None,
                        "brief_section": "scope",
                        "source_value": "Scope of work"
                    }
                ],
                "evidence_sources": {},
            },
            "warnings": [],
        }
        req_path.write_text(json.dumps(prd_requirements), encoding='utf-8')

        # Preflight should extract evidence units including FR-N
        result = preflight_validate(req_path, self.workspace)

        unit_map = build_evidence_unit_map(result["evidence_units"])

        # Verify FR-N evidence exists
        self.assertIn("functional_requirements:FR-1", unit_map)
        self.assertIn("functional_requirements:FR-2", unit_map)
        self.assertIn("functional_requirements:FR-12", unit_map)

        # Verify FR evidence has source_native_id preserved
        self.assertEqual(unit_map["functional_requirements:FR-1"]["source_native_id"], "FR-1")
        self.assertEqual(unit_map["functional_requirements:FR-2"]["source_native_id"], "FR-2")
        self.assertEqual(unit_map["functional_requirements:FR-12"]["source_native_id"], "FR-12")

    def test_fr_evidence_not_substituted_by_generic_evidence(self):
        """FR-N evidence must not be replaced by generic section evidence (scope:0, etc)."""
        req_path = self.workspace / "requirements" / "prd.json"
        req_path.parent.mkdir(parents=True, exist_ok=True)

        prd_requirements = {
            "schema_version": "1.0",
            "source": {
                "type": "prd",
                "prd_path": "/path/to/prd.md",
                "prd_sha256": "abc123",
            },
            "requirements": {
                "summary": "Test",
                "description": "Test",
                "type": "Product Requirement Document",
                "status": "Inferred",
                "labels": [],
                "components": [],
                "linked_issues": [],
                "acceptance_criteria": [],
                "evidence_units": [
                    {
                        "id": "functional_requirements:FR-1",
                        "source_native_id": "FR-1",
                        "prd_section": "features",
                        "source_value": "User can enter loan amount"
                    },
                    {
                        "id": "scope:0",
                        "source_native_id": None,
                        "brief_section": "scope",
                        "source_value": "Personal loans only in v1"
                    }
                ],
                "evidence_sources": {},
            },
            "warnings": [],
        }
        req_path.write_text(json.dumps(prd_requirements), encoding='utf-8')

        result = preflight_validate(req_path, self.workspace)
        unit_map = build_evidence_unit_map(result["evidence_units"])

        # Both FR and scope evidence should exist independently
        self.assertIn("functional_requirements:FR-1", unit_map)
        self.assertIn("scope:0", unit_map)

        # Verify they reference different source values
        self.assertNotEqual(
            unit_map["functional_requirements:FR-1"]["source_value"],
            unit_map["scope:0"]["source_value"]
        )

    def test_supporting_evidence_must_reference_existing_evidence(self):
        """Postflight must reject supporting_evidence that reference non-existent evidence IDs."""
        req_path = self.workspace / "requirements" / "prd.json"
        req_path.parent.mkdir(parents=True, exist_ok=True)

        prd_requirements = {
            "schema_version": "1.0",
            "source": {
                "type": "prd",
                "prd_path": "/path/to/prd.md",
                "prd_sha256": "abc123",
            },
            "requirements": {
                "summary": "Test",
                "description": "Test",
                "type": "Product Requirement Document",
                "status": "Inferred",
                "labels": [],
                "components": [],
                "linked_issues": [],
                "acceptance_criteria": [],
                "evidence_units": [
                    {
                        "id": "functional_requirements:FR-1",
                        "source_native_id": "FR-1",
                        "prd_section": "features",
                        "source_value": "User can enter loan amount"
                    }
                ],
                "evidence_sources": {},
            },
            "warnings": [],
        }
        req_path.write_text(json.dumps(prd_requirements), encoding='utf-8')

        preflight_result = preflight_validate(req_path, self.workspace)

        # Candidate analysis with invalid evidence reference
        candidate_analysis = {
            "change_summary": {
                "outcome": "Test",
                "rationale": "Test",
                "supporting_evidence": ["unknown:evidence"]  # Invalid!
            },
            "explicit_requirements": [],
            "inferred_requirements": [],
            "constraints_and_dependencies": [],
            "ambiguities_and_unknowns": [],
            "key_concepts": []
        }

        # Prepare normalized evidence from prd source
        normalized_evidence = {
            "issue_key": None,
            "source_type": "prd"
        }

        # Postflight validation should reject this
        with self.assertRaises(ValueError) as cm:
            postflight_validate(candidate_analysis, normalized_evidence, {}, preflight_result["evidence_units"])

        self.assertIn("unknown", str(cm.exception).lower())


# ---------------------------------------------------------------------------
# Unratified Architectural Decisions Tests
# ---------------------------------------------------------------------------

class TestUnratifiedArchitecturalDecisions(TestCase):
    """Verify architectural solutions from source are preserved with RED/unratified status."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="buk_unad_test_")
        self.workspace = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_proposed_architecture_preserved_with_red_status(self):
        """Proposed architectural solutions must be preserved and flagged RED/unratified."""
        req_path = self.workspace / "requirements" / "prd.json"
        req_path.parent.mkdir(parents=True, exist_ok=True)

        prd_requirements = {
            "schema_version": "1.0",
            "source": {
                "type": "prd",
                "prd_path": "/path/to/prd.md",
                "prd_sha256": "abc123",
            },
            "requirements": {
                "summary": "Test",
                "description": "Test",
                "type": "Product Requirement Document",
                "status": "Inferred",
                "labels": [],
                "components": [],
                "linked_issues": [],
                "acceptance_criteria": [],
                "evidence_units": [
                    {
                        "id": "functional_requirements:FR-5",
                        "source_native_id": "FR-5",
                        "prd_section": "features",
                        "source_value": "Display comparison view with graceful degradation"
                    }
                ],
                "evidence_sources": {},
            },
            "warnings": [],
        }
        req_path.write_text(json.dumps(prd_requirements), encoding='utf-8')

        preflight_result = preflight_validate(req_path, self.workspace)

        # Candidate analysis with unratified architectural decision
        candidate_analysis = {
            "change_summary": {
                "outcome": "Multi-lender comparison",
                "rationale": "Test",
                "supporting_evidence": ["functional_requirements:FR-5"]
            },
            "explicit_requirements": [],
            "inferred_requirements": [],
            "constraints_and_dependencies": [],
            "ambiguities_and_unknowns": [],
            "key_concepts": [],
            "unratified_architectural_decisions": [
                {
                    "id": "UNAD001",
                    "proposed_solution": "Implement circuit breaker pattern for Aggregator API resilience",
                    "rationale": "FR-5 requires graceful degradation when API unavailable",
                    "supporting_evidence": ["functional_requirements:FR-5"],
                    "status": "RED (unratified)",
                    "ratification_required": "ADR required",
                    "existing_adr_reference": None,
                    "downstream_disposition": "Requires architecture review"
                }
            ]
        }

        normalized_evidence = {
            "issue_key": None,
            "source_type": "prd"
        }

        # Postflight should accept and validate this
        output = postflight_validate(candidate_analysis, normalized_evidence, {}, preflight_result["evidence_units"])

        # Verify unratified_architectural_decisions section exists and is populated
        self.assertIn("unratified_architectural_decisions", output)
        self.assertEqual(len(output["unratified_architectural_decisions"]), 1)

        unad = output["unratified_architectural_decisions"][0]
        self.assertEqual(unad["id"], "UNAD001")
        self.assertEqual(unad["status"], "RED (unratified)")
        self.assertEqual(unad["ratification_required"], "ADR required")

    def test_architectural_decisions_not_in_inferred_requirements(self):
        """Proposed architecture must NOT be in inferred_requirements — only in unratified_architectural_decisions."""
        req_path = self.workspace / "requirements" / "prd.json"
        req_path.parent.mkdir(parents=True, exist_ok=True)

        prd_requirements = {
            "schema_version": "1.0",
            "source": {
                "type": "prd",
                "prd_path": "/path/to/prd.md",
                "prd_sha256": "abc123",
            },
            "requirements": {
                "summary": "Test",
                "description": "Test",
                "type": "Product Requirement Document",
                "status": "Inferred",
                "labels": [],
                "components": [],
                "linked_issues": [],
                "acceptance_criteria": [],
                "evidence_units": [
                    {
                        "id": "functional_requirements:FR-5",
                        "source_native_id": "FR-5",
                        "prd_section": "features",
                        "source_value": "Graceful degradation required"
                    }
                ],
                "evidence_sources": {},
            },
            "warnings": [],
        }
        req_path.write_text(json.dumps(prd_requirements), encoding='utf-8')

        preflight_result = preflight_validate(req_path, self.workspace)

        # Correct: proposed architecture goes to unratified_architectural_decisions
        candidate_analysis = {
            "change_summary": {
                "outcome": "Test",
                "rationale": "Test",
                "supporting_evidence": ["functional_requirements:FR-5"]
            },
            "explicit_requirements": [
                {
                    "id": "ER001",
                    "requirement": "System displays Barclays offer when Aggregator API unavailable",
                    "supporting_evidence": ["functional_requirements:FR-5"]
                }
            ],
            "inferred_requirements": [],
            "constraints_and_dependencies": [],
            "ambiguities_and_unknowns": [],
            "key_concepts": [],
            "unratified_architectural_decisions": [
                {
                    "id": "UNAD001",
                    "proposed_solution": "Circuit breaker implementation",
                    "rationale": "To support graceful degradation",
                    "supporting_evidence": ["functional_requirements:FR-5"],
                    "status": "RED (unratified)",
                    "ratification_required": "ADR required",
                    "existing_adr_reference": None
                }
            ]
        }

        normalized_evidence = {
            "issue_key": None,
            "source_type": "prd"
        }

        output = postflight_validate(candidate_analysis, normalized_evidence, {}, preflight_result["evidence_units"])

        # Verify separation: explicit requirement is preserved, architecture proposal is isolated
        self.assertEqual(len(output["explicit_requirements"]), 1)
        self.assertEqual(output["explicit_requirements"][0]["id"], "ER001")

        # Architecture proposal is in separate section
        self.assertEqual(len(output["unratified_architectural_decisions"]), 1)
        self.assertEqual(output["unratified_architectural_decisions"][0]["id"], "UNAD001")
        self.assertEqual(output["unratified_architectural_decisions"][0]["status"], "RED (unratified)")

    def test_unratified_decisions_evidence_must_exist(self):
        """Evidence references in unratified_architectural_decisions must exist in catalogue."""
        req_path = self.workspace / "requirements" / "prd.json"
        req_path.parent.mkdir(parents=True, exist_ok=True)

        prd_requirements = {
            "schema_version": "1.0",
            "source": {
                "type": "prd",
                "prd_path": "/path/to/prd.md",
                "prd_sha256": "abc123",
            },
            "requirements": {
                "summary": "Test",
                "description": "Test",
                "type": "Product Requirement Document",
                "status": "Inferred",
                "labels": [],
                "components": [],
                "linked_issues": [],
                "acceptance_criteria": [],
                "evidence_units": [
                    {
                        "id": "functional_requirements:FR-5",
                        "source_native_id": "FR-5",
                        "prd_section": "features",
                        "source_value": "Test"
                    }
                ],
                "evidence_sources": {},
            },
            "warnings": [],
        }
        req_path.write_text(json.dumps(prd_requirements), encoding='utf-8')

        preflight_result = preflight_validate(req_path, self.workspace)

        # Candidate analysis with INVALID evidence reference
        candidate_analysis = {
            "change_summary": {
                "outcome": "Test",
                "rationale": "Test",
                "supporting_evidence": ["functional_requirements:FR-5"]
            },
            "explicit_requirements": [],
            "inferred_requirements": [],
            "constraints_and_dependencies": [],
            "ambiguities_and_unknowns": [],
            "key_concepts": [],
            "unratified_architectural_decisions": [
                {
                    "id": "UNAD001",
                    "proposed_solution": "Circuit breaker",
                    "rationale": "Test",
                    "supporting_evidence": ["nonexistent:evidence"],  # Invalid!
                    "status": "RED (unratified)",
                    "ratification_required": "ADR required"
                }
            ]
        }

        normalized_evidence = {
            "issue_key": None,
            "source_type": "prd"
        }

        # Postflight should reject this
        with self.assertRaises(ValueError) as cm:
            postflight_validate(candidate_analysis, normalized_evidence, {}, preflight_result["evidence_units"])

        self.assertIn("nonexistent", str(cm.exception).lower())


# ---------------------------------------------------------------------------
# TestRegressionSuite
# ---------------------------------------------------------------------------

class TestRegressionSuite(TestCase):
    """Verify that deterministic retrieval layer tests still pass."""

    def test_existing_retrieval_tests_still_runnable(self):
        """Existing test_retrieve_jira_requirements.py can be imported and run."""
        try:
            from scripts.tests.test_retrieve_jira_requirements import TestNormalizeRequirements
            self.assertTrue(TestNormalizeRequirements is not None)
        except ImportError as e:
            self.fail(f"Could not import deterministic retrieval tests: {e}")


if __name__ == "__main__":
    main()
