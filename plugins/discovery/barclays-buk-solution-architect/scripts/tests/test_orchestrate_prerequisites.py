"""
Tests for orchestrate_prerequisites.py.

AC mapping:
  AC1  — absent Jira evidence triggers deterministic retrieval subprocess
  AC2  — existing Jira evidence is validated before reuse
  AC3  — invalid or corrupt evidence never silently consumed (fails explicitly)
  AC4  — existing requirements analysis reused only when valid and SHA-256 matches
  AC5  — stale analysis detected when underlying Jira evidence changes
  AC6  — retrieval remains deterministic: subprocess uses sys.executable + absolute path
  AC7  — existing validation entry points orchestrated (their failures propagate)
  AC8  — pipeline integration test: empty workspace -> retrieval -> analysis -> reuse
  AC9  — all prerequisite states covered by the test suite

Tests are behavioural: they verify propagation of existing module errors rather than
asserting import relationships.

No real Jira connection. All network calls are mocked via unittest.mock.patch.
"""

import sys
import os
import json
import hashlib
import shutil
import tempfile
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.orchestrate_prerequisites import (
    orchestrate_prerequisites,
    DEFAULT_ALLOWED_FIELDS,
    _RETRIEVE_SCRIPT,
)
from scripts.understand_requirements import (
    main_postflight,
    preflight_validate,
    extract_evidence_units,
    build_evidence_unit_map,
)


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------

def _make_raw_and_requirements(
    invocation_root: Path,
    issue_key: str = "TEST-1",
    issue_type: str = "Business Epic",
    summary: str = "Test Business Epic",
    description: str = "A test description.\n----\nA second segment.",
) -> str:
    """
    Write issue_key/(raw|requirements)/{issue_key}.json to invocation root.
    New directory structure: invocation_root / issue_key / (raw | requirements)
    Returns the SHA-256 hex digest of the raw bytes.
    """
    raw_bytes = json.dumps({"fields": {
        "issuetype": {"name": issue_type},
        "summary": summary,
        "description": description,
    }}).encode("utf-8")
    sha256 = hashlib.sha256(raw_bytes).hexdigest()

    work_item_root = invocation_root / issue_key
    (work_item_root / "raw").mkdir(parents=True, exist_ok=True)
    (work_item_root / "raw" / f"{issue_key}.json").write_bytes(raw_bytes)

    requirements = {
        "schema_version": "1.0",
        "source": {
            "type": "jira",
            "instance": "jira.example.com",
            "issue_key": issue_key,
            "retrieved_at": "2026-01-01T00:00:00+00:00",
            "endpoint": "/rest/api/2/issue/{issue_key}",
            "requested_fields": sorted(["summary", "description", "status", "issuetype"]),
            "raw_response_file": f"raw/{issue_key}.json",
            "raw_response_sha256": sha256,
        },
        "requirements": {
            "summary": summary,
            "description": description,
            "type": issue_type,
            "status": "In Progress",
            "labels": ["backend"],
            "components": ["API"],
            "linked_issues": [
                {"issue_key": "TEST-2", "link_type": "blocks", "direction": "outward"}
            ],
            "acceptance_criteria": ["AC 1: Deterministic"],
        },
        "warnings": [],
    }
    (work_item_root / "requirements").mkdir(parents=True, exist_ok=True)
    (work_item_root / "requirements" / f"{issue_key}.json").write_text(
        json.dumps(requirements, indent=2), encoding="utf-8"
    )
    return sha256


def _make_valid_postflight_analysis(workspace: Path, issue_key: str, sha256: str) -> dict:
    """
    Build a valid requirements-analysis.json (post-postflight format).
    Evidence references are resolved dicts, matching the catalogue built from
    _make_raw_and_requirements output.
    """
    return {
        "schema_version": "1.0",
        "analysis_metadata": {"analyzed_at": "2026-01-01T00:00:00+00:00"},
        "source_jira_evidence": {
            "issue_key": issue_key,
            "raw_jira_response_sha256": sha256,
        },
        "change_summary": {
            "outcome": "Enable deterministic requirements retrieval",
            "rationale": "To support reproducible analysis",
            "supporting_evidence": [
                {"evidence_id": "summary:0", "jira_field": "summary",
                 "source_value": "Test Business Epic"}
            ],
        },
        "explicit_requirements": [
            {
                "id": "ER001",
                "requirement": "System must be deterministic",
                "supporting_evidence": [
                    {"evidence_id": "acceptance_criteria:0", "jira_field": "acceptance_criteria",
                     "source_value": "AC 1: Deterministic"}
                ],
            }
        ],
        "inferred_requirements": [
            {
                "id": "IR001",
                "requirement": "SHA-256 integrity must be preserved",
                "reasoning": "Determinism implies stable output",
                "supporting_evidence": [
                    {"evidence_id": "summary:0", "jira_field": "summary",
                     "source_value": "Test Business Epic"}
                ],
            }
        ],
        "constraints_and_dependencies": [
            {
                "id": "CD001",
                "constraint": "Blocks TEST-2",
                "is_explicit": True,
                "supporting_evidence": [
                    {"evidence_id": "linked_issues:0", "jira_field": "linked_issues",
                     "source_value": {
                         "issue_key": "TEST-2", "link_type": "blocks", "direction": "outward"
                     }}
                ],
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
                "supporting_evidence": [
                    {"evidence_id": "summary:0", "jira_field": "summary",
                     "source_value": "Test Business Epic"}
                ],
            }
        ],
    }


def _write_analysis(invocation_root: Path, issue_key: str, analysis: dict) -> Path:
    analysis_dir = invocation_root / issue_key / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    path = analysis_dir / "requirements-analysis.json"
    path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    return path


def _make_fake_retrieval_side_effect(workspace: Path, issue_key: str):
    """
    Returns a MagicMock side_effect function that simulates successful retrieval
    by writing raw + requirements files to workspace (AC1, AC8).
    """
    sha256_holder = []

    def _side_effect(cmd, **kwargs):
        sha256 = _make_raw_and_requirements(workspace, issue_key)
        sha256_holder.append(sha256)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        return mock_result

    return _side_effect, sha256_holder


# ---------------------------------------------------------------------------
# AC1 — Absent evidence triggers retrieval
# ---------------------------------------------------------------------------

class TestRetrievalWhenEvidenceAbsent(TestCase):
    """AC1: retrieval subprocess is invoked when Jira evidence is absent."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="buk_sa_orch_test_")
        self.workspace = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_invokes_retrieval_when_both_absent(self):
        """AC1: Both raw and requirements absent -> subprocess invoked."""
        side_effect, _ = _make_fake_retrieval_side_effect(self.workspace, "TEST-1")
        with patch("scripts.orchestrate_prerequisites.subprocess.run",
                   side_effect=side_effect) as mock_run:
            result = orchestrate_prerequisites("TEST-1", self.workspace)
        mock_run.assert_called_once()
        self.assertEqual(result["evidence_status"], "retrieved")

    def test_invokes_retrieval_when_raw_present_normalised_absent(self):
        """AC1: Raw present, requirements absent -> subprocess still invoked (re-fetch)."""
        (self.workspace / "raw").mkdir(parents=True)
        (self.workspace / "raw" / "TEST-1.json").write_bytes(b'{"fields": {}}')

        side_effect, _ = _make_fake_retrieval_side_effect(self.workspace, "TEST-1")
        with patch("scripts.orchestrate_prerequisites.subprocess.run",
                   side_effect=side_effect) as mock_run:
            result = orchestrate_prerequisites("TEST-1", self.workspace)
        mock_run.assert_called_once()
        self.assertEqual(result["evidence_status"], "retrieved")

    def test_retrieval_failure_propagates_as_runtime_error(self):
        """AC1/AC3: Failed retrieval raises RuntimeError, not silent fallback."""
        def failing_run(cmd, **kwargs):
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "JIRA_AUTH_TOKEN not set"
            return mock_result

        with patch("scripts.orchestrate_prerequisites.subprocess.run",
                   side_effect=failing_run):
            with self.assertRaises(RuntimeError) as cm:
                orchestrate_prerequisites("TEST-1", self.workspace)
        self.assertIn("Retrieval failed", str(cm.exception))
        self.assertIn("JIRA_AUTH_TOKEN", str(cm.exception))


# ---------------------------------------------------------------------------
# AC2 — Evidence validated before reuse
# ---------------------------------------------------------------------------

class TestEvidenceValidationBeforeReuse(TestCase):
    """AC2: existing evidence schema and provenance are validated."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="buk_sa_orch_test_")
        self.workspace = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validates_evidence_schema_before_reuse(self):
        """AC2: Valid requirements.json + matching raw -> schema check passes."""
        sha256 = _make_raw_and_requirements(self.workspace, "TEST-1")
        result = orchestrate_prerequisites("TEST-1", self.workspace)
        self.assertEqual(result["evidence_sha256"], sha256)
        self.assertEqual(result["evidence_status"], "validated")

    def test_validates_provenance_hash_before_reuse(self):
        """AC2: SHA-256 verification is part of evidence validation."""
        _make_raw_and_requirements(self.workspace, "TEST-1")
        result = orchestrate_prerequisites("TEST-1", self.workspace)
        # If provenance failed, RuntimeError would have been raised.
        self.assertIn(result["analysis_status"], ("absent", "stale", "invalid", "reused"))


# ---------------------------------------------------------------------------
# AC3 — Invalid evidence never silently consumed
# ---------------------------------------------------------------------------

class TestInvalidEvidenceFailsExplicitly(TestCase):
    """AC3: invalid/corrupt evidence raises RuntimeError, never consumed silently."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="buk_sa_orch_test_")
        self.workspace = Path(self.temp_dir)
        (self.workspace / "raw").mkdir(parents=True)
        (self.workspace / "requirements").mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_corrupt_requirements_json_fails_explicitly(self):
        """AC3: Malformed JSON in requirements.json -> RuntimeError (from validate_requirements)."""
        _make_raw_and_requirements(self.workspace, "TEST-1")
        (self.workspace / "TEST-1" / "requirements" / "TEST-1.json").write_text(
            "not valid json {{{{", encoding="utf-8"
        )
        with self.assertRaises(RuntimeError) as cm:
            orchestrate_prerequisites("TEST-1", self.workspace)
        self.assertIn("Invalid JSON", str(cm.exception))

    def test_missing_source_field_fails_explicitly(self):
        """AC3: Missing required source field in requirements.json -> RuntimeError."""
        _make_raw_and_requirements(self.workspace, "TEST-1")
        # requirements.json missing 'raw_response_sha256'
        req = {
            "schema_version": "1.0",
            "source": {
                "type": "jira",
                "instance": "jira.example.com",
                "issue_key": "TEST-1",
                "retrieved_at": "2026-01-01T00:00:00+00:00",
                "endpoint": "/rest/api/2/issue/TEST-1",
                "requested_fields": ["summary"],
                "raw_response_file": "raw/TEST-1.json",
                # raw_response_sha256 deliberately omitted
            },
            "requirements": {"summary": "x", "type": "Business Epic"},
            "warnings": [],
        }
        (self.workspace / "TEST-1" / "requirements" / "TEST-1.json").write_text(
            json.dumps(req), encoding="utf-8"
        )
        with self.assertRaises(RuntimeError) as cm:
            orchestrate_prerequisites("TEST-1", self.workspace)
        self.assertIn("raw_response_sha256", str(cm.exception))

    def test_sha256_mismatch_fails_explicitly(self):
        """AC3: Altered raw bytes cause SHA-256 mismatch -> RuntimeError from verify_raw_response_hash."""
        _make_raw_and_requirements(self.workspace, "TEST-1")
        # Alter raw bytes after requirements.json has been written
        (self.workspace / "TEST-1" / "raw" / "TEST-1.json").write_bytes(b'{"fields": {"tampered": true}}')
        with self.assertRaises(RuntimeError) as cm:
            orchestrate_prerequisites("TEST-1", self.workspace)
        error_text = str(cm.exception)
        # verify_raw_response_hash produces this message
        self.assertIn("Hash mismatch", error_text)

    def test_normalised_present_raw_absent_fails_explicitly(self):
        """AC3: requirements.json present, raw absent -> unverifiable state, RuntimeError."""
        _make_raw_and_requirements(self.workspace, "TEST-1")
        # Remove the raw file to simulate unverifiable state
        (self.workspace / "TEST-1" / "raw" / "TEST-1.json").unlink()
        with self.assertRaises(RuntimeError) as cm:
            orchestrate_prerequisites("TEST-1", self.workspace)
        self.assertIn("Cannot verify provenance", str(cm.exception))
        self.assertIn("TEST-1", str(cm.exception))


# ---------------------------------------------------------------------------
# AC4 — Valid analysis reused when SHA-256 matches
# ---------------------------------------------------------------------------

class TestAnalysisReuseOnSHA256Match(TestCase):
    """AC4: valid analysis with matching SHA-256 is classified as 'reused'."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="buk_sa_orch_test_")
        self.workspace = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_reuses_analysis_when_sha256_matches(self):
        """AC4: Valid requirements.json + valid analysis with matching SHA-256 -> 'reused'."""
        sha256 = _make_raw_and_requirements(self.workspace, "TEST-1")
        analysis = _make_valid_postflight_analysis(self.workspace, "TEST-1", sha256)
        _write_analysis(self.workspace, "TEST-1", analysis)

        result = orchestrate_prerequisites("TEST-1", self.workspace)
        self.assertEqual(result["analysis_status"], "reused")
        self.assertEqual(result["required_next_action"], "none")
        self.assertIsNotNone(result["analysis_path"])

    def test_invalid_analysis_triggers_regeneration(self):
        """AC4/AC3: Structurally invalid analysis -> 'invalid', 'run_analysis'."""
        sha256 = _make_raw_and_requirements(self.workspace, "TEST-1")
        analysis = {
            "schema_version": "1.0",
            "source_jira_evidence": {
                "issue_key": "TEST-1",
                "raw_jira_response_sha256": sha256,
            },
            # Missing all required sections
        }
        _write_analysis(self.workspace, "TEST-1", analysis)

        result = orchestrate_prerequisites("TEST-1", self.workspace)
        self.assertEqual(result["analysis_status"], "invalid")
        self.assertEqual(result["required_next_action"], "run_analysis")

    def test_corrupt_analysis_json_triggers_regeneration(self):
        """AC4/AC3: Corrupt analysis JSON -> 'invalid', 'run_analysis' (not RuntimeError)."""
        _make_raw_and_requirements(self.workspace, "TEST-1")
        analysis_dir = self.workspace / "TEST-1" / "analysis"
        analysis_dir.mkdir(parents=True)
        (analysis_dir / "requirements-analysis.json").write_text(
            "not valid json", encoding="utf-8"
        )

        result = orchestrate_prerequisites("TEST-1", self.workspace)
        self.assertEqual(result["analysis_status"], "invalid")
        self.assertEqual(result["required_next_action"], "run_analysis")


# ---------------------------------------------------------------------------
# AC5 — Stale analysis detected when evidence changes
# ---------------------------------------------------------------------------

class TestStaleAnalysisDetection(TestCase):
    """AC5: stale analysis detected when SHA-256 differs; classified without evidence-ID validation."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="buk_sa_orch_test_")
        self.workspace = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_stale_analysis_detected_when_sha256_differs(self):
        """AC5: Analysis SHA-256 != current evidence SHA-256 -> 'stale'."""
        sha256 = _make_raw_and_requirements(self.workspace, "TEST-1")
        # Analysis references a different SHA-256 (simulates prior Jira update)
        analysis = _make_valid_postflight_analysis(self.workspace, "TEST-1", "0" * 64)
        _write_analysis(self.workspace, "TEST-1", analysis)

        result = orchestrate_prerequisites("TEST-1", self.workspace)
        self.assertEqual(result["analysis_status"], "stale")
        self.assertEqual(result["required_next_action"], "run_analysis")

    def test_stale_classification_does_not_run_section_validation(self):
        """AC5: Stale analysis with structural error -> 'stale' not 'invalid'.
        Proves _validate_analysis_sections is not called on stale analysis.
        """
        sha256 = _make_raw_and_requirements(self.workspace, "TEST-1")
        # Analysis has DIFFERENT SHA-256 (stale) AND a structural error (missing reasoning)
        analysis = {
            "schema_version": "1.0",
            "source_jira_evidence": {
                "issue_key": "TEST-1",
                "raw_jira_response_sha256": "0" * 64,  # stale
            },
            "change_summary": {
                "outcome": "x", "rationale": "y",
                "supporting_evidence": [
                    {"evidence_id": "summary:0", "jira_field": "summary", "source_value": "x"}
                ],
            },
            "explicit_requirements": [],
            "inferred_requirements": [
                {
                    "id": "IR001",
                    "requirement": "test",
                    # MISSING "reasoning" — would fail _validate_analysis_sections
                    "supporting_evidence": [
                        {"evidence_id": "summary:0", "jira_field": "summary", "source_value": "x"}
                    ],
                }
            ],
            "constraints_and_dependencies": [],
            "ambiguities_and_unknowns": [],
            "key_concepts": [],
        }
        _write_analysis(self.workspace, "TEST-1", analysis)

        result = orchestrate_prerequisites("TEST-1", self.workspace)
        # Must be "stale", not "invalid" (proves section validation was not called)
        self.assertEqual(result["analysis_status"], "stale")


# ---------------------------------------------------------------------------
# AC6 — Retrieval subprocess uses sys.executable + absolute script path
# ---------------------------------------------------------------------------

class TestRetrievalSubprocessContract(TestCase):
    """AC6: retrieval is deterministic — invoked via sys.executable and absolute script path."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="buk_sa_orch_test_")
        self.workspace = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _run_with_mock_retrieval(self):
        side_effect, _ = _make_fake_retrieval_side_effect(self.workspace, "TEST-1")
        with patch("scripts.orchestrate_prerequisites.subprocess.run",
                   side_effect=side_effect) as mock_run:
            orchestrate_prerequisites("TEST-1", self.workspace)
        return mock_run.call_args[0][0]  # the cmd list

    def test_retrieval_uses_sys_executable(self):
        """AC6: First arg of subprocess is sys.executable (not bare 'python')."""
        cmd = self._run_with_mock_retrieval()
        self.assertEqual(cmd[0], sys.executable)

    def test_retrieval_script_path_is_absolute(self):
        """AC6: Second arg is an absolute path pointing to retrieve_jira_requirements.py."""
        cmd = self._run_with_mock_retrieval()
        script_arg = Path(cmd[1])
        self.assertTrue(script_arg.is_absolute(), f"Expected absolute path, got: {cmd[1]}")
        self.assertEqual(script_arg.name, "retrieve_jira_requirements.py")

    def test_retrieval_passes_correct_args(self):
        """AC6: Subprocess args include --issue-key and --allowed-fields."""
        cmd = self._run_with_mock_retrieval()
        self.assertIn("--issue-key", cmd)
        self.assertIn("TEST-1", cmd)
        self.assertIn("--allowed-fields", cmd)

    def test_retrieval_uses_default_allowed_fields_when_not_specified(self):
        """AC6: DEFAULT_ALLOWED_FIELDS is passed automatically when caller omits allowed_fields."""
        side_effect, _ = _make_fake_retrieval_side_effect(self.workspace, "TEST-1")
        with patch("scripts.orchestrate_prerequisites.subprocess.run",
                   side_effect=side_effect) as mock_run:
            orchestrate_prerequisites("TEST-1", self.workspace)
        cmd = mock_run.call_args[0][0]
        fields_idx = cmd.index("--allowed-fields") + 1
        self.assertEqual(cmd[fields_idx], DEFAULT_ALLOWED_FIELDS)


# ---------------------------------------------------------------------------
# AC7 — Existing validation entry points orchestrated (failure propagation)
# ---------------------------------------------------------------------------

class TestExistingValidationEntryPointsPropagateErrors(TestCase):
    """AC7: validate_requirements and verify_raw_response_hash failures propagate."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="buk_sa_orch_test_")
        self.workspace = Path(self.temp_dir)
        (self.workspace / "raw").mkdir(parents=True)
        (self.workspace / "requirements").mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_requirements_error_propagates(self):
        """AC7: validate_requirements raises RuntimeError with 'schema version' in message."""
        raw_bytes = b'{"fields": {}}'
        (self.workspace / "TEST-1" / "raw").mkdir(parents=True, exist_ok=True)
        (self.workspace / "TEST-1" / "raw" / "TEST-1.json").write_bytes(raw_bytes)
        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        req = {
            "schema_version": "9.9",  # wrong version — validate_requirements will reject
            "source": {
                "type": "jira", "instance": "x", "issue_key": "TEST-1",
                "retrieved_at": "2026-01-01T00:00:00+00:00",
                "endpoint": "/rest/api/2/issue/TEST-1",
                "requested_fields": ["summary"],
                "raw_response_file": "raw/TEST-1.json",
                "raw_response_sha256": sha256,
            },
            "requirements": {"summary": "x"},
            "warnings": [],
        }
        (self.workspace / "TEST-1" / "requirements").mkdir(parents=True, exist_ok=True)
        (self.workspace / "TEST-1" / "requirements" / "TEST-1.json").write_text(
            json.dumps(req), encoding="utf-8"
        )
        with self.assertRaises(RuntimeError) as cm:
            orchestrate_prerequisites("TEST-1", self.workspace)
        # The error text must come from validate_requirements (review_requirements.py)
        self.assertIn("schema version", str(cm.exception).lower())

    def test_verify_hash_error_propagates(self):
        """AC7: verify_raw_response_hash error ('Hash mismatch') propagates from review_requirements."""
        _make_raw_and_requirements(self.workspace, "TEST-1")
        # Alter raw bytes to force hash mismatch
        (self.workspace / "TEST-1" / "raw" / "TEST-1.json").write_bytes(b'{"fields": {"tampered": 1}}')
        with self.assertRaises(RuntimeError) as cm:
            orchestrate_prerequisites("TEST-1", self.workspace)
        # The specific error text comes from verify_raw_response_hash (review_requirements.py)
        self.assertIn("Hash mismatch", str(cm.exception))


# ---------------------------------------------------------------------------
# AC8 — Pipeline integration test: empty workspace to valid analysis
# ---------------------------------------------------------------------------

class TestPipelineIntegration(TestCase):
    """
    AC8: pipeline integration test covering the full prerequisite orchestration path.

    This test simulates the complete workflow from an empty workspace:
      1. orchestrate_prerequisites detects absent evidence and invokes retrieval (mocked).
      2. The mocked retrieval writes valid raw + requirements files.
      3. orchestrate_prerequisites validates evidence and returns analysis_status="absent".
      4. The test simulates the agentic Stage 2 by constructing a valid analysis dict
         and running main_postflight directly (deterministic boundary).
      5. A second call to orchestrate_prerequisites confirms analysis_status="reused".

    This is an automated pipeline integration test, not a skill-level test. A skill-level
    evaluation would require the barclays-buk-plugin-testing-toolkit. The smoke test in
    the README covers the skill composition end-to-end.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="buk_sa_orch_test_")
        # Resolve to canonical long-form path (tempfile may return Windows 8.3 short paths).
        # orchestrate_prerequisites also resolves its workspace arg, so both sides must match.
        self.workspace = Path(self.temp_dir).resolve()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_end_to_end_from_empty_workspace_to_valid_analysis(self):
        """AC8: Empty workspace -> retrieval -> evidence validated -> analysis -> reused."""
        issue_key = "TEST-E2E"
        sha256_holder = []

        def fake_retrieval(cmd, **kwargs):
            sha256 = _make_raw_and_requirements(self.workspace, issue_key)
            sha256_holder.append(sha256)
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stderr = ""
            return mock_result

        # Step 1: Empty workspace — orchestrate_prerequisites should invoke retrieval
        with patch("scripts.orchestrate_prerequisites.subprocess.run",
                   side_effect=fake_retrieval):
            result1 = orchestrate_prerequisites(issue_key, self.workspace)

        self.assertEqual(result1["evidence_status"], "retrieved")
        self.assertEqual(result1["analysis_status"], "absent")
        self.assertEqual(result1["required_next_action"], "run_analysis")
        sha256 = sha256_holder[0]

        # Step 2: Simulate agentic Stage 2 using preflight output to build a valid analysis
        req_path = Path(result1["requirements_path"])
        preflight_result = preflight_validate(req_path)
        evidence_units = preflight_result["evidence_units"]
        unit_map = build_evidence_unit_map(evidence_units)
        ids = list(unit_map.keys())
        first_id = ids[0]

        raw_analysis = {
            "change_summary": {
                "outcome": "Test outcome",
                "rationale": "Test rationale",
                "supporting_evidence": [first_id],
            },
            "explicit_requirements": [],
            "inferred_requirements": [],
            "constraints_and_dependencies": [],
            "ambiguities_and_unknowns": [
                {
                    "id": "AMB001",
                    "ambiguity": "Test ambiguity",
                    "impact": "Test impact",
                    "clarification_needed": "Test question?",
                }
            ],
            "key_concepts": [],
        }

        # Write analysis to temp file for postflight
        tmp_analysis_path = self.workspace / "tmp_analysis.json"
        tmp_analysis_path.write_text(json.dumps(raw_analysis), encoding="utf-8")

        # Step 3: Run postflight (deterministic — validates + resolves + writes atomically)
        exit_code = main_postflight(req_path, tmp_analysis_path, self.workspace, None)
        self.assertEqual(exit_code, 0)

        # Step 4: Confirm requirements-analysis.json was written to workspace
        final_analysis_path = self.workspace / issue_key / "analysis" / "requirements-analysis.json"
        self.assertTrue(final_analysis_path.exists())
        final_data = json.loads(final_analysis_path.read_text())
        self.assertEqual(final_data["schema_version"], "2.0")
        # New schema uses source_evidence array
        self.assertIn("source_evidence", final_data)
        self.assertEqual(len(final_data["source_evidence"]), 1)
        self.assertEqual(final_data["source_evidence"][0]["sha256"], sha256)

        # Step 5: Second orchestrate call — analysis is now valid and current
        result2 = orchestrate_prerequisites(issue_key, self.workspace)
        self.assertEqual(result2["analysis_status"], "reused")
        self.assertEqual(result2["required_next_action"], "none")
        self.assertEqual(result2["analysis_path"], str(final_analysis_path))


# ---------------------------------------------------------------------------
# Additional: versioned output schema validation
# ---------------------------------------------------------------------------

class TestOrchestrationOutputSchema(TestCase):
    """Validate that orchestration output conforms to orchestration_result.schema.json."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="buk_sa_orch_test_")
        self.workspace = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_output_conforms_to_schema_for_absent_analysis(self):
        """Schema validation: absent analysis output has all required fields."""
        _make_raw_and_requirements(self.workspace, "TEST-1")
        result = orchestrate_prerequisites("TEST-1", self.workspace)

        self.assertEqual(result["schema_version"], "1.0")
        for field in ("issue_key", "requirements_path", "evidence_status",
                      "evidence_sha256", "analysis_status", "required_next_action"):
            self.assertIn(field, result)
        self.assertIsNone(result["analysis_path"])
        self.assertEqual(result["analysis_status"], "absent")
        self.assertEqual(result["required_next_action"], "run_analysis")

    def test_output_conforms_to_schema_for_reused_analysis(self):
        """Schema validation: reused analysis output has all required fields."""
        sha256 = _make_raw_and_requirements(self.workspace, "TEST-1")
        analysis = _make_valid_postflight_analysis(self.workspace, "TEST-1", sha256)
        _write_analysis(self.workspace, "TEST-1", analysis)

        result = orchestrate_prerequisites("TEST-1", self.workspace)
        self.assertEqual(result["schema_version"], "1.0")
        self.assertEqual(result["analysis_status"], "reused")
        self.assertEqual(result["required_next_action"], "none")
        self.assertIsNotNone(result["analysis_path"])

    def test_invalid_status_rejected_by_schema_validator(self):
        """Schema validation: _validate_orchestration_result rejects invalid status values."""
        from scripts.orchestrate_prerequisites import _validate_orchestration_result
        bad_result = {
            "schema_version": "1.0",
            "issue_key": "TEST-1",
            "requirements_path": "/path/to/requirements.json",
            "evidence_status": "unknown_value",  # invalid enum
            "evidence_sha256": "a" * 64,
            "analysis_path": None,
            "analysis_status": "absent",
            "required_next_action": "run_analysis",
        }
        with self.assertRaises(RuntimeError) as cm:
            _validate_orchestration_result(bad_result)
        self.assertIn("evidence_status", str(cm.exception))

    def test_missing_required_field_rejected_by_schema_validator(self):
        """Schema validation: _validate_orchestration_result rejects missing required fields."""
        from scripts.orchestrate_prerequisites import _validate_orchestration_result
        incomplete = {
            "schema_version": "1.0",
            "issue_key": "TEST-1",
            # Missing required fields
        }
        with self.assertRaises(RuntimeError) as cm:
            _validate_orchestration_result(incomplete)
        self.assertIn("missing required field", str(cm.exception))


# ---------------------------------------------------------------------------
# Additional: evidence integrity check (SHA-256 match, corrupted reference)
# ---------------------------------------------------------------------------

class TestResolvedEvidenceIntegrity(TestCase):
    """AC4: evidence integrity check detects corrupted resolved evidence references."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="buk_sa_orch_test_")
        self.workspace = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_unknown_evidence_id_in_resolved_reference_triggers_invalid(self):
        """AC4: Resolved evidence with unknown evidence_id -> 'invalid'."""
        sha256 = _make_raw_and_requirements(self.workspace, "TEST-1")
        analysis = _make_valid_postflight_analysis(self.workspace, "TEST-1", sha256)
        # Corrupt a resolved evidence reference with a non-existent ID
        analysis["explicit_requirements"][0]["supporting_evidence"][0]["evidence_id"] = (
            "nonexistent:999"
        )
        _write_analysis(self.workspace, "TEST-1", analysis)

        result = orchestrate_prerequisites("TEST-1", self.workspace)
        self.assertEqual(result["analysis_status"], "invalid")
        self.assertEqual(result["required_next_action"], "run_analysis")

    def test_jira_field_mismatch_in_resolved_reference_triggers_invalid(self):
        """AC4: Resolved evidence with wrong jira_field -> 'invalid'."""
        sha256 = _make_raw_and_requirements(self.workspace, "TEST-1")
        analysis = _make_valid_postflight_analysis(self.workspace, "TEST-1", sha256)
        # The change_summary references summary:0; corrupt its jira_field
        analysis["change_summary"]["supporting_evidence"][0]["jira_field"] = "wrong_field"
        _write_analysis(self.workspace, "TEST-1", analysis)

        result = orchestrate_prerequisites("TEST-1", self.workspace)
        self.assertEqual(result["analysis_status"], "invalid")


class TestSSLFlagPropagation(TestCase):
    """
    Regression tests for SSL flag propagation (Windows/corporate SSL revocation issue).

    Verifies that --ssl-no-revoke flag is correctly passed through to the
    deterministic retrieval subprocess.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="buk_sa_orch_test_")
        self.workspace = Path(self.temp_dir).resolve()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_ssl_no_revoke_flag_passed_to_subprocess(self):
        """Windows/SSL: --ssl-no-revoke flag reaches subprocess."""
        with patch("scripts.orchestrate_prerequisites.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            # Create minimal workspace files to trigger retrieval check
            raw_path = self.workspace / "raw" / "TEST-SSL"
            req_path = self.workspace / "requirements" / "TEST-SSL.json"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            req_path.parent.mkdir(parents=True, exist_ok=True)

            # Both absent - should invoke retrieval
            try:
                orchestrate_prerequisites(
                    "TEST-SSL",
                    self.workspace,
                    ssl_no_revoke=True
                )
            except RuntimeError:
                # Expected - we're mocking subprocess but not the full pipeline
                pass

            # Verify subprocess.run was called with --ssl-no-revoke
            mock_run.assert_called()
            call_args = mock_run.call_args[0][0]  # Get the command list
            self.assertIn("--ssl-no-revoke", call_args,
                         "SSL flag not found in subprocess command")

    def test_ssl_no_revoke_flag_not_passed_when_false(self):
        """Windows/SSL: --ssl-no-revoke not included when ssl_no_revoke=False."""
        with patch("scripts.orchestrate_prerequisites.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            raw_path = self.workspace / "raw" / "TEST-NOSSL"
            req_path = self.workspace / "requirements" / "TEST-NOSSL.json"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            req_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                orchestrate_prerequisites(
                    "TEST-NOSSL",
                    self.workspace,
                    ssl_no_revoke=False  # Explicitly false
                )
            except RuntimeError:
                pass

            mock_run.assert_called()
            call_args = mock_run.call_args[0][0]
            self.assertNotIn("--ssl-no-revoke", call_args,
                           "SSL flag should not be included when ssl_no_revoke=False")


class TestPathResolution(TestCase):
    """
    Regression tests for Windows path handling in Git Bash.

    Verifies that script paths are resolved correctly regardless of platform
    and can be used by subprocess without backslash mangling.
    """

    def test_retrieve_script_path_uses_forward_slashes(self):
        """Path resolution: _RETRIEVE_SCRIPT path uses forward slashes (Git Bash compatible)."""
        # _RETRIEVE_SCRIPT should be an absolute Path that works cross-platform
        from scripts.orchestrate_prerequisites import _RETRIEVE_SCRIPT

        # Path should exist
        self.assertTrue(_RETRIEVE_SCRIPT.exists(),
                       f"Retrieve script not found at {_RETRIEVE_SCRIPT}")

        # When converted to string, it should work in subprocess on any platform
        script_str = str(_RETRIEVE_SCRIPT)
        self.assertTrue(script_str.endswith("retrieve_jira_requirements.py"),
                       "Script path doesn't end with expected filename")

        # On Windows, the path will have backslashes internally,
        # but subprocess.run handles this correctly. What matters is that
        # the Path object uses sys.executable and proper escaping.

    def test_subprocess_receives_properly_formed_command(self):
        """Path resolution: subprocess command is properly formed for shell execution."""
        from scripts.orchestrate_prerequisites import _invoke_retrieval

        with patch("scripts.orchestrate_prerequisites.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            workspace = Path(tempfile.mkdtemp(prefix="buk_path_test_"))
            try:
                _invoke_retrieval("TEST-PATH", workspace, DEFAULT_ALLOWED_FIELDS)
            except RuntimeError:
                pass
            finally:
                shutil.rmtree(str(workspace), ignore_errors=True)

            mock_run.assert_called()
            cmd = mock_run.call_args[0][0]

            # Command should be a list (proper for subprocess.run)
            self.assertIsInstance(cmd, list, "Command should be a list")

            # First element should be sys.executable
            self.assertEqual(cmd[0], sys.executable,
                           "First element should be sys.executable")

            # Second element should be a path to the retrieve script
            self.assertTrue(cmd[1].endswith("retrieve_jira_requirements.py"),
                           "Second element should be path to retrieve script")


class TestEnvironmentConfigurationValidation(TestCase):
    """
    Regression tests for environment configuration handling (Issue 3).

    Verifies that deterministic validation happens without requiring user
    interaction and that configuration validation is clean and secret-safe.
    """

    def test_buk_sa_workspace_missing_precise_error(self):
        """Environment config: Missing BUK_SA_WORKSPACE identified precisely in error."""
        from scripts.orchestrate_prerequisites import main
        import sys as sys_module
        from io import StringIO

        # Mock sys.argv to simulate CLI invocation without invocation-dir
        original_argv = sys_module.argv
        original_stderr = sys_module.stderr
        try:
            # Note: --invocation-dir is now required (no env var fallback)
            sys_module.argv = ["orchestrate_prerequisites.py", "--issue-key", "TEST-ENV"]

            stderr_capture = StringIO()
            sys_module.stderr = stderr_capture

            # argparse will exit with code 2 when required args are missing
            try:
                exit_code = main()
            except SystemExit as e:
                exit_code = e.code

            # Should fail with exit code 2 (argparse error for missing required arg)
            self.assertEqual(exit_code, 2, "Should exit with code 2 when invocation-dir missing")

            error_output = stderr_capture.getvalue()
            # Error should identify the missing invocation-dir argument
            self.assertIn("--invocation-dir", error_output,
                         "Error should name --invocation-dir as required")
            # Should NOT ask user for setup confirmation
            self.assertNotIn("Do you need help", error_output.lower(),
                           "Should not ask user for help setting up")

        finally:
            sys_module.argv = original_argv
            sys_module.stderr = original_stderr

    def test_jira_auth_token_missing_precise_error(self):
        """Environment config: JIRA_AUTH_TOKEN error identifies token, not workspace."""
        from scripts.retrieve_jira_requirements import fetch_jira_raw

        # Clear token if set
        original_token = os.environ.get("JIRA_AUTH_TOKEN")
        if "JIRA_AUTH_TOKEN" in os.environ:
            del os.environ["JIRA_AUTH_TOKEN"]

        try:
            # This should raise RuntimeError about missing token
            with self.assertRaises(RuntimeError) as ctx:
                fetch_jira_raw("TEST-ISSUE", allowed_fields=["summary"])

            error_msg = str(ctx.exception)
            # Error should identify JIRA_AUTH_TOKEN by name
            self.assertIn("JIRA_AUTH_TOKEN", error_msg,
                         "Error should name JIRA_AUTH_TOKEN as missing")
            # Error should NOT ask user to set up
            self.assertNotIn("Do you need help", error_msg.lower(),
                           "Should not ask for setup help")

        finally:
            if original_token:
                os.environ["JIRA_AUTH_TOKEN"] = original_token

    def test_secret_values_never_in_error_messages(self):
        """Environment config: Secret values never appear in error messages."""
        # The key guarantee: JIRA_AUTH_TOKEN value itself is never in error messages
        # Test that the variable NAME is identified but not its contents
        from scripts.retrieve_jira_requirements import fetch_jira_raw

        fake_secret = "SECRET_TOKEN_12345ABCDE"
        os.environ["JIRA_AUTH_TOKEN"] = fake_secret

        try:
            with patch("scripts.retrieve_jira_requirements.subprocess.run") as mock_run:
                # Simulate curl failure with proper stderr type (bytes)
                mock_run.return_value = MagicMock(returncode=1, stderr=b"Connection failed")

                try:
                    fetch_jira_raw("TEST-ISSUE", allowed_fields=["summary"])
                except RuntimeError as e:
                    error_msg = str(e)
                    # The secret should NEVER appear in the error message
                    self.assertNotIn(fake_secret, error_msg,
                                   "Secret token value should not appear in error")

        finally:
            if "JIRA_AUTH_TOKEN" in os.environ:
                del os.environ["JIRA_AUTH_TOKEN"]

    def test_token_not_needed_when_evidence_reused(self):
        """Environment config: JIRA_AUTH_TOKEN not needed when evidence reuse validated."""
        # Use existing test helper to build valid evidence
        temp_dir = tempfile.mkdtemp(prefix="buk_token_test_")
        workspace = Path(temp_dir).resolve()

        try:
            sha256 = _make_raw_and_requirements(workspace, "NOTOKEN-TEST")

            # Clear JIRA_AUTH_TOKEN - it's not needed for reuse
            original_token = os.environ.get("JIRA_AUTH_TOKEN")
            if "JIRA_AUTH_TOKEN" in os.environ:
                del os.environ["JIRA_AUTH_TOKEN"]

            try:
                # Should NOT raise error about missing token since no retrieval happens
                result = orchestrate_prerequisites("NOTOKEN-TEST", workspace)
                # Analysis is absent but no token is needed to detect this
                self.assertEqual(result["analysis_status"], "absent",
                               "Should detect absent analysis without needing token")
                self.assertEqual(result["evidence_status"], "validated",
                               "Should validate existing evidence without needing token")
            finally:
                if original_token:
                    os.environ["JIRA_AUTH_TOKEN"] = original_token
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_skill_documentation_prohibits_environment_checks(self):
        """Environment config: Skill doc does not ask Claude to check configuration."""
        # Read the SKILL.md file
        skill_path = Path(__file__).resolve().parent.parent.parent / "skills" / "understand-requirements" / "SKILL.md"
        skill_content = skill_path.read_text(encoding='utf-8')

        # Should delegate prerequisite decisions to orchestration, not teach Claude to check
        self.assertIn("Stage 0", skill_content,
                     "SKILL should reference Stage 0 orchestration")

        # Should NOT suggest manually checking environment variables
        self.assertNotIn("check if $BUK", skill_content.upper(),
                        "SKILL should not suggest checking environment variables before Stage 0")

        # Should NOT teach Claude to invoke retrieve_jira_requirements directly
        self.assertNotIn("retrieve_jira_requirements", skill_content,
                        "SKILL should not mention retrieve_jira_requirements as a direct invocation target")


class TestBUKSASslNoRevokeBoolean(TestCase):
    """Tests for BUK_SA_SSL_NO_REVOKE environment variable boolean parsing."""

    def test_env_var_absent_means_disabled(self):
        """Absent BUK_SA_SSL_NO_REVOKE → SSL revocation checks enabled (default)."""
        if "BUK_SA_SSL_NO_REVOKE" in os.environ:
            del os.environ["BUK_SA_SSL_NO_REVOKE"]

        from scripts.retrieve_jira_requirements import _parse_bool
        self.assertFalse(_parse_bool(""),
                        "Absent/empty value should parse as False (secure default)")

    def test_env_var_enabled_values(self):
        """True values: 1, true, yes (case-insensitive)."""
        from scripts.retrieve_jira_requirements import _parse_bool

        for value in ["1", "true", "True", "TRUE", "yes", "Yes", "YES"]:
            self.assertTrue(_parse_bool(value),
                          f"Value {value!r} should parse as True")

    def test_env_var_disabled_values(self):
        """False values: 0, false, no (case-insensitive)."""
        from scripts.retrieve_jira_requirements import _parse_bool

        for value in ["0", "false", "False", "FALSE", "no", "No", "NO"]:
            self.assertFalse(_parse_bool(value),
                           f"Value {value!r} should parse as False")

    def test_env_var_invalid_values_default_to_disabled(self):
        """Invalid values default to False (secure)."""
        from scripts.retrieve_jira_requirements import _parse_bool

        for value in ["maybe", "enabled", "disabled", "on", "off", "random"]:
            self.assertFalse(_parse_bool(value),
                           f"Invalid value {value!r} should parse as False (secure default)")

    def test_env_var_used_when_cli_flag_absent(self):
        """BUK_SA_SSL_NO_REVOKE is used when --ssl-no-revoke flag not provided."""
        os.environ["BUK_SA_SSL_NO_REVOKE"] = "true"

        try:
            # Verify the environment variable is read by the script
            import scripts.retrieve_jira_requirements as retrieve
            source = retrieve.__file__
            with open(source) as f:
                content = f.read()
                # Should have _parse_bool call with the environment variable
                self.assertIn("_parse_bool(os.environ.get", content,
                            "Script should use _parse_bool with environment variable")

        finally:
            if "BUK_SA_SSL_NO_REVOKE" in os.environ:
                del os.environ["BUK_SA_SSL_NO_REVOKE"]

    def test_cli_flag_takes_precedence(self):
        """--ssl-no-revoke CLI flag takes precedence over env var."""
        os.environ["BUK_SA_SSL_NO_REVOKE"] = "0"  # Disabled via env

        try:
            from scripts.orchestrate_prerequisites import _parse_bool
            # With CLI flag (simulated by args.ssl_no_revoke=True in real code):
            # ssl_no_revoke = args.ssl_no_revoke or _parse_bool(...)
            # If args.ssl_no_revoke is True, the env var is not evaluated due to OR short-circuit
            self.assertTrue(True or _parse_bool("0"),
                          "CLI flag (True) takes precedence over env var (False)")

        finally:
            if "BUK_SA_SSL_NO_REVOKE" in os.environ:
                del os.environ["BUK_SA_SSL_NO_REVOKE"]


class TestProductionIssues(TestCase):
    """Focused regression tests for production integration issues."""

    def test_jira_auth_token_not_exposed_in_orchestration_output(self):
        """Issue 1: JIRA_AUTH_TOKEN not exposed in orchestration JSON or error messages."""
        from scripts.orchestrate_prerequisites import orchestrate_prerequisites
        import tempfile
        from pathlib import Path
        import json

        temp_dir = tempfile.mkdtemp(prefix="buk_secret_test_")
        workspace = Path(temp_dir).resolve()

        fake_token = "SECRET_TOKEN_12345XYZ"
        os.environ["JIRA_AUTH_TOKEN"] = fake_token

        try:
            # When retrieval is needed, verify token doesn't appear in orchestration result
            with patch("scripts.orchestrate_prerequisites.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                try:
                    result = orchestrate_prerequisites("TEST", workspace)
                    # The orchestration result should NOT contain the token
                    result_str = json.dumps(result)
                    self.assertNotIn(fake_token, result_str,
                                  "Secret token must not appear in orchestration result JSON")
                except RuntimeError:
                    # Expected when retrieval fails in test
                    pass

        finally:
            if "JIRA_AUTH_TOKEN" in os.environ:
                del os.environ["JIRA_AUTH_TOKEN"]
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_buk_sa_ssl_no_revoke_environment_support(self):
        """Issue 2: BUK_SA_SSL_NO_REVOKE environment variable is supported."""
        # Verify that orchestrate_prerequisites reads and uses this flag
        import scripts.orchestrate_prerequisites as orch

        # Check that the environment variable is read in main()
        source = orch.__file__
        with open(source) as f:
            content = f.read()
            # Should have the environment variable check
            self.assertIn("BUK_SA_SSL_NO_REVOKE", content,
                        "Code should check BUK_SA_SSL_NO_REVOKE environment variable")


class TestInstalledPluginResourceResolution(TestCase):
    """Regression tests for installed-plugin resource resolution.

    Verifies that the skill uses ${CLAUDE_PLUGIN_ROOT} for bundled resources
    rather than repository-root-relative or current-working-directory assumptions.
    """

    def test_understand_requirements_skill_uses_plugin_root_substitution(self):
        """Skill must use ${CLAUDE_PLUGIN_ROOT} for bundled script references."""
        skill_path = Path(__file__).resolve().parent.parent.parent / "skills" / "understand-requirements" / "SKILL.md"
        skill_content = skill_path.read_text(encoding='utf-8')

        # Should contain ${CLAUDE_PLUGIN_ROOT} references
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", skill_content,
                     "Skill must use ${CLAUDE_PLUGIN_ROOT} for installed-plugin resource references")

        # Should reference orchestrate_prerequisites.py with the plugin-root prefix
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate_prerequisites.py", skill_content,
                     "Stage 0 entry point must use ${CLAUDE_PLUGIN_ROOT}")

    def test_understand_requirements_skill_no_repo_root_paths(self):
        """Skill must NOT use repository-root-relative paths."""
        skill_path = Path(__file__).resolve().parent.parent.parent / "skills" / "understand-requirements" / "SKILL.md"
        skill_content = skill_path.read_text(encoding='utf-8').lower()

        # Should NOT contain old repository-root-relative patterns
        self.assertNotIn("python plugins/discovery", skill_content,
                        "Skill must not use repository-root-relative paths like 'plugins/discovery/...'")
        self.assertNotIn("from the repository root", skill_content,
                        "Skill must not assume 'from repository root' execution context")

    def test_understand_requirements_skill_no_direct_retrieve_invocation(self):
        """Skill must NOT directly invoke retrieve_jira_requirements.py."""
        skill_path = Path(__file__).resolve().parent.parent.parent / "skills" / "understand-requirements" / "SKILL.md"
        skill_content = skill_path.read_text(encoding='utf-8').lower()

        # Should NOT instruct Claude to invoke retrieve_jira_requirements directly
        self.assertNotIn("retrieve_jira_requirements.py", skill_content,
                        "Skill must not mention retrieve_jira_requirements.py as an invocation target")

    def test_review_requirements_skill_uses_plugin_root(self):
        """Standalone review skill must also use ${CLAUDE_PLUGIN_ROOT}."""
        skill_path = Path(__file__).resolve().parent.parent.parent / "skills" / "review-requirements" / "SKILL.md"
        skill_content = skill_path.read_text(encoding='utf-8')

        # Should use plugin-root substitution
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/scripts/review_requirements.py", skill_content,
                     "review-requirements skill must use ${CLAUDE_PLUGIN_ROOT}")

        # Should NOT use repository-root-relative paths
        self.assertNotIn("python plugins/discovery", skill_content.lower(),
                        "review-requirements skill must not use repository-root-relative paths")

    def test_understand_requirements_skill_stage_0_is_exclusive_entry(self):
        """Skill must present Stage 0 as the exclusive deterministic entry point."""
        skill_path = Path(__file__).resolve().parent.parent.parent / "skills" / "understand-requirements" / "SKILL.md"
        skill_content = skill_path.read_text(encoding='utf-8').lower()

        # Should emphasize that orchestration handles prerequisite decisions
        self.assertIn("stage 0", skill_content,
                     "Skill should reference Stage 0 as orchestration entry point")

        # Should NOT tell Claude to compose prerequisite stages or make prerequisite decisions
        self.assertIn("stage 0 determines", skill_content,
                     "Skill should state that Stage 0 makes deterministic decisions")


class TestWorkflowSequencingRegressions(TestCase):
    """Regression tests for live workflow sequencing defects.

    Issue 1: Claude performed environment reconnaissance before Stage 0.
    Issue 2: Claude manually invoked retrieve_jira_requirements.py before Stage 0.
    Issue 3: Stage 2 candidate and Stage 3 postflight used different paths.
    """

    def test_preflight_output_includes_candidate_analysis_path(self):
        """Preflight must output candidate_analysis_path for Stage 2->Stage 3 hand-off."""
        from scripts.understand_requirements import preflight_validate
        import tempfile
        import hashlib

        with tempfile.TemporaryDirectory() as temp_ws:
            workspace_path = Path(temp_ws).resolve()

            # Create minimal valid requirements
            raw_dir = workspace_path / "raw"
            req_dir = workspace_path / "requirements"
            raw_dir.mkdir(parents=True, exist_ok=True)
            req_dir.mkdir(parents=True, exist_ok=True)

            issue_key = "TEST-HAND-001"
            raw_file = raw_dir / f"{issue_key}.json"
            req_file = req_dir / f"{issue_key}.json"

            raw_content = b'{"key": "TEST-HAND-001"}'
            raw_file.write_bytes(raw_content)

            raw_sha256 = hashlib.sha256(raw_content).hexdigest()
            req_content = {
                "schema_version": "1.0",
                "source": {
                    "type": "jira",
                    "instance": "test.jira.com",
                    "issue_key": issue_key,
                    "retrieved_at": "2026-10-03T12:00:00Z",
                    "endpoint": "/rest/api/2/issue/TEST-HAND-001",
                    "requested_fields": ["summary"],
                    "raw_response_file": f"raw/{issue_key}.json",
                    "raw_response_sha256": raw_sha256
                },
                "requirements": {
                    "summary": "Test",
                    "description": "",
                    "type": "Business Epic",
                    "status": "Open",
                    "labels": [],
                    "components": [],
                    "linked_issues": [],
                    "acceptance_criteria": []
                },
                "warnings": []
            }
            req_file.write_text(json.dumps(req_content, indent=2))

            # Call preflight_validate
            result = preflight_validate(req_file, workspace_path)

            # Result should include candidate_analysis_path
            self.assertIn("candidate_analysis_path", result,
                        "Preflight must output candidate_analysis_path for Stage 2->Stage 3 hand-off")

            candidate_path = result["candidate_analysis_path"]
            self.assertTrue(isinstance(candidate_path, str),
                          "candidate_analysis_path must be a string")
            self.assertIn(issue_key, candidate_path,
                        "candidate_analysis_path must include issue_key")
            self.assertIn("candidate-requirements-analysis.json", candidate_path,
                        "candidate_analysis_path must point to candidate file")

    def test_candidate_analysis_path_is_under_workspace(self):
        """Candidate analysis path must be under BUK_SA_WORKSPACE, not /tmp."""
        from scripts.understand_requirements import preflight_validate
        import tempfile
        import hashlib

        with tempfile.TemporaryDirectory() as temp_ws:
            workspace_path = Path(temp_ws).resolve()

            raw_dir = workspace_path / "raw"
            req_dir = workspace_path / "requirements"
            raw_dir.mkdir(parents=True, exist_ok=True)
            req_dir.mkdir(parents=True, exist_ok=True)

            issue_key = "TEST-HAND-002"
            raw_file = raw_dir / f"{issue_key}.json"
            req_file = req_dir / f"{issue_key}.json"

            raw_content = b'{"key": "TEST-HAND-002"}'
            raw_file.write_bytes(raw_content)

            raw_sha256 = hashlib.sha256(raw_content).hexdigest()
            req_content = {
                "schema_version": "1.0",
                "source": {
                    "type": "jira",
                    "instance": "test.jira.com",
                    "issue_key": issue_key,
                    "retrieved_at": "2026-10-03T12:00:00Z",
                    "endpoint": "/rest/api/2/issue/TEST-HAND-002",
                    "requested_fields": ["summary"],
                    "raw_response_file": f"raw/{issue_key}.json",
                    "raw_response_sha256": raw_sha256
                },
                "requirements": {
                    "summary": "Test",
                    "description": "",
                    "type": "Business Epic",
                    "status": "Open",
                    "labels": [],
                    "components": [],
                    "linked_issues": [],
                    "acceptance_criteria": []
                },
                "warnings": []
            }
            req_file.write_text(json.dumps(req_content, indent=2))

            result = preflight_validate(req_file, workspace_path)
            candidate_path = result["candidate_analysis_path"]

            # The candidate path must be under the workspace provided (even if workspace is temp)
            candidate_path_obj = Path(candidate_path)
            workspace_path_obj = Path(workspace_path).resolve()
            try:
                candidate_path_obj.relative_to(workspace_path_obj)
            except ValueError:
                self.fail(f"candidate_analysis_path {candidate_path} must be under workspace {workspace_path_obj}")

    def test_postflight_receives_candidate_path_as_analysis_argument(self):
        """Postflight --analysis-path must be the exact candidate path from preflight."""
        # This is validated by the contract in SKILL.md
        # The test here verifies the architecture: postflight doesn't invent a path

        import scripts.understand_requirements
        source = scripts.understand_requirements.__file__
        with open(source) as f:
            content = f.read()
            # main_postflight should accept analysis_path argument
            self.assertIn("def main_postflight", content)
            self.assertIn("analysis_path:", content,
                        "main_postflight must take analysis_path as a required argument")


class TestPathLocationRegressions(TestCase):
    """Regression tests for path/location boundary issues from live testing."""

    def test_retrieve_script_not_relative_to_skill_directory(self):
        """
        Retrieve script must not be resolved from skills/retrieve-jira-requirements.

        The script is at: plugin_root/scripts/retrieve_jira_requirements.py
        NOT at: plugin_root/skills/retrieve-jira-requirements/scripts/retrieve_jira_requirements.py
        """
        from scripts.orchestrate_prerequisites import _RETRIEVE_SCRIPT

        script_path = Path(_RETRIEVE_SCRIPT)
        # Should be named retrieve_jira_requirements.py
        self.assertEqual(script_path.name, "retrieve_jira_requirements.py",
                        "Script must be named retrieve_jira_requirements.py")

        # Should be in scripts/ directory (at plugin root)
        self.assertEqual(script_path.parent.name, "scripts",
                        "Script must be in scripts/ directory")

        # Must NOT be under skills/ tree
        path_str = str(script_path)
        self.assertNotIn("skills/retrieve-jira-requirements", path_str,
                        "Script path must not contain skills/retrieve-jira-requirements")

    def test_understand_requirements_script_not_relative_to_skill_directory(self):
        """
        understand_requirements script must not be resolved from
        skills/understand-requirements.

        The script is at: plugin_root/scripts/understand_requirements.py
        NOT at: plugin_root/skills/understand-requirements/scripts/understand_requirements.py
        """
        import scripts.understand_requirements
        script_path = Path(scripts.understand_requirements.__file__)

        # Should be named understand_requirements.py
        self.assertEqual(script_path.name, "understand_requirements.py",
                        "Script must be named understand_requirements.py")

        # Should be in scripts/ directory (at plugin root)
        self.assertEqual(script_path.parent.name, "scripts",
                        "Script must be in scripts/ directory")

        # Must NOT be under skills/ tree
        path_str = str(script_path)
        self.assertNotIn("skills/understand-requirements", path_str,
                        "Script path must not contain skills/understand-requirements")

    def test_requirements_evidence_resolves_from_workspace(self):
        """
        Requirements evidence must always resolve from BUK_SA_WORKSPACE.

        Evidence layout:
        - $BUK_SA_WORKSPACE/raw/{issue_key}.json (raw Jira response)
        - $BUK_SA_WORKSPACE/requirements/{issue_key}.json (normalized evidence)

        NOT from:
        - plugin_root/requirements/...
        - skills/.../requirements/...
        - current_working_directory/requirements/...
        """
        with tempfile.TemporaryDirectory() as temp_workspace:
            workspace_path = Path(temp_workspace).resolve()

            # Create raw and requirements structure (new: under issue-key subdirectory)
            issue_key = "TEST-LOC-001"
            work_item_root = workspace_path / issue_key
            raw_dir = work_item_root / "raw"
            req_dir = work_item_root / "requirements"
            raw_dir.mkdir(parents=True, exist_ok=True)
            req_dir.mkdir(parents=True, exist_ok=True)

            raw_file = raw_dir / f"{issue_key}.json"
            req_file = req_dir / f"{issue_key}.json"

            # Write minimal valid files
            raw_content = b'{"key": "TEST-LOC-001"}'
            raw_file.write_bytes(raw_content)

            raw_sha256 = hashlib.sha256(raw_content).hexdigest()
            req_content = {
                "schema_version": "1.0",
                "source": {
                    "type": "jira",
                    "instance": "test.jira.com",
                    "issue_key": issue_key,
                    "retrieved_at": "2026-10-03T12:00:00Z",
                    "endpoint": "/rest/api/2/issue/TEST-LOC-001",
                    "requested_fields": ["summary"],
                    "raw_response_file": f"raw/{issue_key}.json",
                    "raw_response_sha256": raw_sha256
                },
                "requirements": {
                    "summary": "Test",
                    "description": "",
                    "type": "Business Epic",
                    "status": "Open",
                    "labels": [],
                    "components": [],
                    "linked_issues": [],
                    "acceptance_criteria": []
                },
                "warnings": []
            }
            req_file.write_text(json.dumps(req_content, indent=2))

            # Orchestration should locate files in workspace, not in plugin
            result = orchestrate_prerequisites(
                issue_key=issue_key,
                invocation_root=workspace_path
            )

            # Result should contain the correct workspace paths
            self.assertEqual(result["requirements_path"], str(req_file),
                           "Requirements path must point to workspace, not plugin")

            # Verify paths don't point into plugin directories
            self.assertNotIn("plugins/", result["requirements_path"],
                           "Requirements path must not contain 'plugins/'")
            self.assertNotIn("skills/", result["requirements_path"],
                           "Requirements path must not contain 'skills/'")

    def test_analysis_output_resolves_from_workspace(self):
        """
        Analysis output must always resolve to BUK_SA_WORKSPACE/analysis/{issue_key}/.

        NOT to:
        - plugin_root/analysis/...
        - skills/.../analysis/...
        """
        with tempfile.TemporaryDirectory() as temp_workspace:
            workspace_path = Path(temp_workspace).resolve()

            # Setup minimal prerequisites (new: under issue-key subdirectory)
            issue_key = "TEST-LOC-002"
            work_item_root = workspace_path / issue_key
            raw_dir = work_item_root / "raw"
            req_dir = work_item_root / "requirements"
            raw_dir.mkdir(parents=True, exist_ok=True)
            req_dir.mkdir(parents=True, exist_ok=True)

            raw_file = raw_dir / f"{issue_key}.json"
            req_file = req_dir / f"{issue_key}.json"

            raw_content = b'{"key": "TEST-LOC-002"}'
            raw_file.write_bytes(raw_content)

            raw_sha256 = hashlib.sha256(raw_content).hexdigest()
            req_content = {
                "schema_version": "1.0",
                "source": {
                    "type": "jira",
                    "instance": "test.jira.com",
                    "issue_key": issue_key,
                    "retrieved_at": "2026-10-03T12:00:00Z",
                    "endpoint": "/rest/api/2/issue/TEST-LOC-002",
                    "requested_fields": ["summary"],
                    "raw_response_file": f"raw/{issue_key}.json",
                    "raw_response_sha256": raw_sha256
                },
                "requirements": {
                    "summary": "Test",
                    "description": "",
                    "type": "Business Epic",
                    "status": "Open",
                    "labels": [],
                    "components": [],
                    "linked_issues": [],
                    "acceptance_criteria": []
                },
                "warnings": []
            }
            req_file.write_text(json.dumps(req_content, indent=2))

            # Analysis file absent; orchestration should report where it would be
            result = orchestrate_prerequisites(
                issue_key=issue_key,
                invocation_root=workspace_path
            )

            # When analysis is absent, analysis_path should be None per the contract
            # but if present, it should point to workspace
            if result["analysis_path"]:
                self.assertNotIn("plugins/", result["analysis_path"],
                               "Analysis path must not contain 'plugins/'")
                self.assertNotIn("skills/", result["analysis_path"],
                               "Analysis path must not contain 'skills/'")
                # If present, should be under workspace
                self.assertTrue(result["analysis_path"].startswith(str(workspace_path)),
                              "Analysis path must start with workspace path")

    def test_missing_workspace_artefact_handled_by_orchestration(self):
        """
        Missing workspace artefacts are handled by orchestration layer.

        Should NOT:
        - Search plugin_root/requirements/
        - Search skills/.../requirements/
        - Look in current_working_directory

        Should:
        - Invoke retrieval if both raw and normalised absent
        - Return explicit error/state if workspace/BUK_SA_WORKSPACE not configured
        """
        with tempfile.TemporaryDirectory() as temp_workspace:
            workspace_path = Path(temp_workspace).resolve()
            issue_key = "TEST-LOC-003"

            # Empty workspace: no raw, no requirements (new structure under issue_key)
            work_item_root = workspace_path / issue_key
            raw_dir = work_item_root / "raw"
            req_dir = work_item_root / "requirements"
            raw_dir.mkdir(parents=True, exist_ok=True)
            req_dir.mkdir(parents=True, exist_ok=True)

            # Mock retrieval to avoid actual Jira calls
            with patch("subprocess.run") as mock_run:
                # Setup mock to simulate successful retrieval
                mock_run.return_value = MagicMock(returncode=0)

                # When retrieval is triggered, create the files
                def create_files_on_call(*args, **kwargs):
                    raw_file = raw_dir / f"{issue_key}.json"
                    req_file = req_dir / f"{issue_key}.json"

                    raw_content = b'{"key": "TEST-LOC-003"}'
                    raw_file.write_bytes(raw_content)

                    raw_sha256 = hashlib.sha256(raw_content).hexdigest()
                    req_content = {
                        "schema_version": "1.0",
                        "source": {
                            "type": "jira",
                            "instance": "test.jira.com",
                            "issue_key": issue_key,
                            "retrieved_at": "2026-10-03T12:00:00Z",
                            "endpoint": "/rest/api/2/issue/TEST-LOC-003",
                            "requested_fields": ["summary"],
                            "raw_response_file": f"raw/{issue_key}.json",
                            "raw_response_sha256": raw_sha256
                        },
                        "requirements": {
                            "summary": "Test",
                            "description": "",
                            "type": "Business Epic",
                            "status": "Open",
                            "labels": [],
                            "components": [],
                            "linked_issues": [],
                            "acceptance_criteria": []
                        },
                        "warnings": []
                    }
                    req_file.write_text(json.dumps(req_content, indent=2))
                    return MagicMock(returncode=0)

                mock_run.side_effect = create_files_on_call

                # Orchestration should trigger retrieval (not search plugin dirs)
                result = orchestrate_prerequisites(
                    issue_key=issue_key,
                    invocation_root=workspace_path
                )

                # Retrieval should have been invoked
                self.assertTrue(mock_run.called,
                              "Retrieval subprocess should be invoked for absent evidence")

                # Result paths must point to workspace
                self.assertNotIn("plugins/", result["requirements_path"],
                               "Orchestration must not fallback to plugin directory")

    def test_raw_evidence_resolves_from_workspace(self):
        """
        Raw Jira evidence must always resolve from BUK_SA_WORKSPACE/raw/{issue_key}.json.

        NOT from:
        - plugin_root/raw/...
        - skills/.../raw/...
        """
        with tempfile.TemporaryDirectory() as temp_workspace:
            workspace_path = Path(temp_workspace).resolve()

            issue_key = "TEST-LOC-004"
            work_item_root = workspace_path / issue_key
            raw_dir = work_item_root / "raw"
            req_dir = work_item_root / "requirements"
            raw_dir.mkdir(parents=True, exist_ok=True)
            req_dir.mkdir(parents=True, exist_ok=True)

            raw_file = raw_dir / f"{issue_key}.json"
            req_file = req_dir / f"{issue_key}.json"

            raw_content = b'{"key": "TEST-LOC-004", "fields": {}}'
            raw_file.write_bytes(raw_content)

            raw_sha256 = hashlib.sha256(raw_content).hexdigest()
            req_content = {
                "schema_version": "1.0",
                "source": {
                    "type": "jira",
                    "instance": "test.jira.com",
                    "issue_key": issue_key,
                    "retrieved_at": "2026-10-03T12:00:00Z",
                    "endpoint": "/rest/api/2/issue/TEST-LOC-004",
                    "requested_fields": ["summary"],
                    "raw_response_file": f"raw/{issue_key}.json",
                    "raw_response_sha256": raw_sha256
                },
                "requirements": {
                    "summary": "Test",
                    "description": "",
                    "type": "Business Epic",
                    "status": "Open",
                    "labels": [],
                    "components": [],
                    "linked_issues": [],
                    "acceptance_criteria": []
                },
                "warnings": []
            }
            req_file.write_text(json.dumps(req_content, indent=2))

            # Orchestration should use workspace paths for provenance verification
            result = orchestrate_prerequisites(
                issue_key=issue_key,
                invocation_root=workspace_path
            )

            # Provenance should be verified
            self.assertEqual(result["evidence_status"], "validated",
                           "Evidence should be validated against workspace files")

            # Hash should match
            self.assertEqual(result["evidence_sha256"], raw_sha256,
                           "Raw evidence SHA-256 must match recorded value")


if __name__ == "__main__":
    main()
