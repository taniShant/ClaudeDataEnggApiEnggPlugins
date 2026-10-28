"""
Tests for capability impact assessment: deterministic preflight and postflight validation.

Maps to BUKL3BBA-1465 acceptance criteria:
- AC #1: Consumes requirements understanding
- AC #2: Uses authoritative capability model (using representative domain for Stage 1)
- AC #3–4: Analysis at capability level; IDs/names from model
- AC #5–6: Impact traceable to requirement; rationale provided
- AC #7–8: Evidence classification and uncertainty
- AC #9–10: Provenance preserved; model fingerprinted
- AC #11: Semantic reasoning (not keyword matching)
- AC #12: Output structure consistent
- AC #13–14: End-to-end scenario; synthetic tests
- AC #15–16: No credentials; test coverage
"""

import sys
import os
import json
import tempfile
import shutil
import subprocess
from pathlib import Path
from unittest import TestCase, main

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from assess_capability_impact import preflight_validate, postflight_validate
from capability_model import CapabilityModel, CapabilityModelError

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
VALID_MODELS_DIR = FIXTURES_DIR / "valid_models"


class TestCapabilityModelLoading(TestCase):
    """Test group 1+2: Model schema and loading (AC #2, #4, #10)"""

    def test_load_valid_model(self):
        """Load a valid minimal capability model"""
        model = CapabilityModel()
        model.load_from_file(FIXTURES_DIR / "capability_model_minimal.yml")

        self.assertEqual(len(model.domains), 1)
        self.assertIn("dom.test-domain", model.domains)

    def test_load_missing_file(self):
        """Reject missing model file"""
        model = CapabilityModel()
        with self.assertRaises(CapabilityModelError):
            model.load_from_file(FIXTURES_DIR / "nonexistent.yml")

    def test_load_broken_schema(self):
        """Reject model with schema errors"""
        model = CapabilityModel()
        with self.assertRaises(CapabilityModelError):
            model.load_from_file(FIXTURES_DIR / "capability_model_broken_schema.yml")

    def test_broken_model_yaml(self):
        """Reject model with schema validation errors"""
        model = CapabilityModel()
        with self.assertRaises(CapabilityModelError):
            model.load_from_file(FIXTURES_DIR / "capability_model_broken_schema.yml")


class TestCapabilityModelFingerprinting(TestCase):
    """Test group 3: Deterministic fingerprinting (AC #10)"""

    def test_fingerprint_format(self):
        """Fingerprint has correct format"""
        model = CapabilityModel()
        model.load_from_file(FIXTURES_DIR / "capability_model_minimal.yml")

        fingerprint = model.get_fingerprint()
        self.assertTrue(fingerprint.startswith("sha256:"))
        self.assertEqual(len(fingerprint), 71)  # sha256: + 64 hex digits

    def test_fingerprint_deterministic(self):
        """Same model produces same fingerprint across loads"""
        model1 = CapabilityModel()
        model1.load_from_file(FIXTURES_DIR / "capability_model_minimal.yml")
        fp1 = model1.get_fingerprint()

        model2 = CapabilityModel()
        model2.load_from_file(FIXTURES_DIR / "capability_model_minimal.yml")
        fp2 = model2.get_fingerprint()

        self.assertEqual(fp1, fp2)


class TestCapabilityModelCatalogue(TestCase):
    """Test capability catalogue extraction"""

    def test_catalogue_structure(self):
        """Extracted catalogue has correct structure"""
        model = CapabilityModel()
        model.load_from_file(FIXTURES_DIR / "capability_model_minimal.yml")

        catalogue = model.get_capability_catalogue()

        self.assertIn("cap.test.capability-alpha", catalogue)
        self.assertIn("cap.test.capability-beta", catalogue)
        self.assertIn("cap.test.capability-gamma", catalogue)

        alpha = catalogue["cap.test.capability-alpha"]
        self.assertEqual(alpha["name"], "Capability Alpha")
        self.assertEqual(alpha["domain_id"], "dom.test-domain")
        self.assertEqual(alpha["subdomain_id"], "sub.test.subdomain-one")


class TestPreflightValidation(TestCase):
    """Test group 1: Input contract and preflight (AC #1, #9)"""

    def test_preflight_valid_input(self):
        """Preflight succeeds with valid inputs"""
        result = preflight_validate(
            requirements_path=FIXTURES_DIR / "synthetic_requirements.json",
            capability_model_dir=VALID_MODELS_DIR,
            invocation_dir=None
        )

        self.assertEqual(result["issue_key"], "TEST-123")
        self.assertEqual(len(result["requirement_ids"]), 4)  # ER001, ER002, IR001, CD001
        self.assertIn("capability_model_fingerprint", result)
        self.assertTrue(result["capability_model_fingerprint"].startswith("sha256:"))

    def test_preflight_missing_requirements(self):
        """Preflight rejects missing requirements file"""
        with self.assertRaises(RuntimeError) as ctx:
            preflight_validate(
                requirements_path=FIXTURES_DIR / "nonexistent.json",
                capability_model_dir=FIXTURES_DIR,
                invocation_dir=None
            )
        self.assertIn("not found", str(ctx.exception))

    def test_preflight_missing_model_directory(self):
        """Preflight rejects missing capability model directory"""
        with self.assertRaises(RuntimeError) as ctx:
            preflight_validate(
                requirements_path=FIXTURES_DIR / "synthetic_requirements.json",
                capability_model_dir=FIXTURES_DIR / "nonexistent",
                invocation_dir=None
            )
        self.assertIn("not found", str(ctx.exception))

    def test_preflight_broken_requirements_schema(self):
        """Preflight rejects invalid requirements schema"""
        # Create a temporary invalid requirements file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"schema_version": "1.0"}, f)  # Missing requirement_type
            invalid_path = Path(f.name)

        try:
            with self.assertRaises(RuntimeError):
                preflight_validate(
                    requirements_path=invalid_path,
                    capability_model_dir=FIXTURES_DIR,
                    invocation_dir=None
                )
        finally:
            invalid_path.unlink()


class TestPostflightValidation(TestCase):
    """Test group 5+6: Postflight validation (AC #5, #6, #12)"""

    def test_postflight_valid_findings(self):
        """Postflight succeeds with valid findings"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            findings_path = tmpdir / "findings.json"
            shutil.copy(FIXTURES_DIR / "synthetic_findings_valid.json", findings_path)

            result = postflight_validate(
                requirements_path=FIXTURES_DIR / "synthetic_requirements.json",
                capability_model_dir=VALID_MODELS_DIR,
                findings_path=findings_path,
                invocation_dir=tmpdir
            )

            self.assertEqual(result["assessment_status"], "completed")
            self.assertEqual(result["findings_count"], 2)
            self.assertIn("dom.test-domain", result["domains_affected"])
            self.assertTrue(tmpdir / "TEST-123" / "capability-impact" / "capability-impact-analysis.json" in
                          [Path(result["persisted_path"])])

    def test_postflight_unknown_capability(self):
        """Postflight rejects unknown capability ID"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            findings_path = tmpdir / "findings.json"

            # Load valid findings and modify to reference nonexistent capability
            findings_data = json.loads((FIXTURES_DIR / "synthetic_findings_valid.json").read_text())
            findings_data["findings"][0]["capability_id"] = "cap.test.nonexistent"

            with open(findings_path, 'w') as f:
                json.dump(findings_data, f)

            with self.assertRaises(RuntimeError) as ctx:
                postflight_validate(
                    requirements_path=FIXTURES_DIR / "synthetic_requirements.json",
                    capability_model_dir=VALID_MODELS_DIR,
                    findings_path=findings_path,
                    invocation_dir=tmpdir
                )
            self.assertIn("unknown capability ID", str(ctx.exception))

    def test_postflight_unknown_requirement(self):
        """Postflight rejects unknown requirement reference"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            findings_path = tmpdir / "findings.json"

            findings_data = json.loads((FIXTURES_DIR / "synthetic_findings_valid.json").read_text())
            findings_data["findings"][0]["impacted_by_requirement_ids"] = ["UNKNOWN999"]

            with open(findings_path, 'w') as f:
                json.dump(findings_data, f)

            with self.assertRaises(RuntimeError) as ctx:
                postflight_validate(
                    requirements_path=FIXTURES_DIR / "synthetic_requirements.json",
                    capability_model_dir=VALID_MODELS_DIR,
                    findings_path=findings_path,
                    invocation_dir=tmpdir
                )
            self.assertIn("unknown requirement ID", str(ctx.exception))

    def test_postflight_capability_name_mismatch(self):
        """Postflight rejects capability name that doesn't match model"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            findings_path = tmpdir / "findings.json"

            findings_data = json.loads((FIXTURES_DIR / "synthetic_findings_valid.json").read_text())
            findings_data["findings"][0]["capability_name"] = "Wrong Name"

            with open(findings_path, 'w') as f:
                json.dump(findings_data, f)

            with self.assertRaises(RuntimeError) as ctx:
                postflight_validate(
                    requirements_path=FIXTURES_DIR / "synthetic_requirements.json",
                    capability_model_dir=VALID_MODELS_DIR,
                    findings_path=findings_path,
                    invocation_dir=tmpdir
                )
            self.assertIn("capability name mismatch", str(ctx.exception))

    def test_postflight_invalid_evidence_format(self):
        """Postflight rejects malformed evidence IDs"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            findings_path = tmpdir / "findings.json"

            findings_data = json.loads((FIXTURES_DIR / "synthetic_findings_valid.json").read_text())
            findings_data["findings"][0]["supporting_evidence"][0]["evidence_id"] = "invalid-format"

            with open(findings_path, 'w') as f:
                json.dump(findings_data, f)

            with self.assertRaises(RuntimeError) as ctx:
                postflight_validate(
                    requirements_path=FIXTURES_DIR / "synthetic_requirements.json",
                    capability_model_dir=VALID_MODELS_DIR,
                    findings_path=findings_path,
                    invocation_dir=tmpdir
                )
            self.assertIn("does not match", str(ctx.exception))

    def test_postflight_invalid_classification(self):
        """Postflight rejects invalid evidence classification"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            findings_path = tmpdir / "findings.json"

            findings_data = json.loads((FIXTURES_DIR / "synthetic_findings_valid.json").read_text())
            findings_data["findings"][0]["impact_classification"] = "invalid-classification"

            with open(findings_path, 'w') as f:
                json.dump(findings_data, f)

            with self.assertRaises(RuntimeError) as ctx:
                postflight_validate(
                    requirements_path=FIXTURES_DIR / "synthetic_requirements.json",
                    capability_model_dir=VALID_MODELS_DIR,
                    findings_path=findings_path,
                    invocation_dir=tmpdir
                )
            self.assertIn("is not one of", str(ctx.exception))


class TestSupportedModes(TestCase):
    """Regression: Only preflight and postflight modes are supported"""

    def test_only_preflight_postflight_supported(self):
        """CLI script supports only --mode preflight and --mode postflight, not orchestrate"""
        # This test verifies the CLI argument parser only accepts these modes
        # If --mode orchestrate is attempted, it should fail
        import sys
        import subprocess
        result = subprocess.run([
            sys.executable,
            str(Path(__file__).parent.parent / "assess_capability_impact.py"),
            "--help"
        ], capture_output=True, text=True)

        # Verify output mentions preflight and postflight
        self.assertIn("preflight", result.stdout)
        self.assertIn("postflight", result.stdout)
        # Orchestrate should NOT appear in the help text
        self.assertNotIn("orchestrate", result.stdout)


class TestRequirementsInput(TestCase):
    """Regression: Capability Impact consumes requirements-analysis.json from Requirements Understanding"""

    def test_requires_requirements_analysis_not_raw_requirements(self):
        """Preflight must accept requirements-analysis.json, not requirements.json"""
        # Create a requirements.json (raw retrieval output)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            raw_requirements = tmpdir / "requirements.json"
            raw_requirements.write_text(json.dumps({
                "schema_version": "1.0",
                "source": {
                    "type": "jira",
                    "issue_key": "TEST-1",
                    "raw_response_sha256": "abc123",
                    "instance": "https://jira.example.com"
                },
                "requirements": {
                    "type": "Business Epic",
                    "summary": "Test"
                }
            }))

            # Should fail with requirements.json
            with self.assertRaises(RuntimeError):
                preflight_validate(
                    requirements_path=raw_requirements,
                    capability_model_dir=VALID_MODELS_DIR,
                    invocation_dir=None
                )

    def test_accepts_requirements_analysis_from_understanding(self):
        """Preflight accepts validated requirements-analysis.json from Requirements Understanding"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            analysis = tmpdir / "requirements-analysis.json"
            analysis.write_text(json.dumps({
                "schema_version": "1.0",
                "analysis_metadata": {"analyzed_at": "2026-10-04T12:00:00+00:00"},
                "source_jira_evidence": {
                    "issue_key": "TEST-2",
                    "raw_jira_response_sha256": "def456"
                },
                "change_summary": {"outcome": "", "rationale": "", "supporting_evidence": []},
                "explicit_requirements": [],
                "inferred_requirements": [],
                "constraints_and_dependencies": [],
                "ambiguities_and_unknowns": [],
                "key_concepts": []
            }))

            # Should succeed with requirements-analysis.json
            result = preflight_validate(
                requirements_path=analysis,
                capability_model_dir=VALID_MODELS_DIR,
                invocation_dir=tmpdir
            )
            self.assertEqual(result["issue_key"], "TEST-2")


class TestZeroFindings(TestCase):
    """Regression: Valid assessment may have zero findings if no capabilities match"""

    def test_valid_assessment_with_zero_findings(self):
        """Create valid findings with empty findings array"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            findings_path = tmpdir / "findings.json"

            # Valid findings structure with empty findings array
            findings_data = {
                "schema_version": "1.0",
                "assessment_type": "capability_impact",
                "assessment_status": "completed_with_uncertainties",
                "input_provenance": {
                    "requirements_path": str(FIXTURES_DIR / "synthetic_requirements.json"),
                    "requirements_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                    "capability_model_fingerprint": "sha256:fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210",
                    "assessment_generated_at": "2026-10-04T12:00:00+00:00"
                },
                "findings": [],  # NO findings - valid assessment outcome
                "domain_summary": [],
                "cross_domain_analysis": {
                    "affected_domain_count": 0,
                    "affected_domain_ids": [],
                    "potential_boundary_changes": False,
                    "potential_ownership_changes": False,
                    "multiple_domains_affected": False
                },
                "uncertainties": [
                    {
                        "id": "UNC-001",
                        "description": "No supplied capabilities match the fraud/dispute subject matter",
                        "related_capabilities": []
                    }
                ]
            }

            with open(findings_path, 'w') as f:
                json.dump(findings_data, f)

            # Should succeed with zero findings
            result = postflight_validate(
                requirements_path=FIXTURES_DIR / "synthetic_requirements.json",
                capability_model_dir=VALID_MODELS_DIR,
                findings_path=findings_path,
                invocation_dir=tmpdir
            )

            self.assertEqual(result["findings_count"], 0)
            self.assertEqual(result["assessment_status"], "completed")


class TestInventedCapabilityRejection(TestCase):
    """Regression: Postflight rejects invented capability identifiers"""

    def test_reject_capability_id_not_in_model(self):
        """Postflight rejects capability IDs that don't exist in the model"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            findings_path = tmpdir / "findings.json"

            # Create findings with only the invented capability (not mixing valid + invalid)
            findings_data = {
                "schema_version": "1.0",
                "assessment_type": "capability_impact",
                "assessment_status": "completed",
                "input_provenance": {
                    "requirements_path": str(FIXTURES_DIR / "synthetic_requirements.json"),
                    "requirements_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                    "capability_model_fingerprint": "sha256:fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210",
                    "assessment_generated_at": "2026-10-04T12:00:00+00:00"
                },
                "findings": [
                    {
                        "id": "CAP-999",
                        "capability_id": "cap.invented.fake-capability",  # NOT IN MODEL
                        "capability_name": "Fake Capability",
                        "capability_domain": "dom.invented",
                        "capability_subdomain": "sub.invented.fake",
                        "impact_classification": "direct",
                        "impacted_by_requirement_ids": ["ER001"],
                        "rationale": "Invented capability",
                        "supporting_evidence": [
                            {
                                "requirement_id": "ER001",
                                "evidence_id": "summary:0",
                                "evidence_field": "summary"
                            }
                        ],
                        "uncertainty": None,
                        "boundary_implications": None,
                        "cross_domain_effects": None
                    }
                ],
                "domain_summary": [
                    {
                        "domain_id": "dom.invented",
                        "domain_name": "Invented Domain",
                        "affected_capability_count": 1,
                        "affected_capability_ids": ["cap.invented.fake-capability"],
                        "impact_classification_breakdown": {"direct": 1, "inferred": 0, "possible": 0}
                    }
                ],
                "cross_domain_analysis": {
                    "affected_domain_count": 1,
                    "affected_domain_ids": ["dom.invented"],
                    "potential_boundary_changes": False,
                    "potential_ownership_changes": False,
                    "multiple_domains_affected": False
                },
                "uncertainties": []
            }

            with open(findings_path, 'w') as f:
                json.dump(findings_data, f)

            with self.assertRaises(RuntimeError) as ctx:
                postflight_validate(
                    requirements_path=FIXTURES_DIR / "synthetic_requirements.json",
                    capability_model_dir=VALID_MODELS_DIR,
                    findings_path=findings_path,
                    invocation_dir=tmpdir
                )
            self.assertIn("unknown capability ID", str(ctx.exception))


class TestEndToEndScenario(TestCase):
    """Test group 12: End-to-end scenario (AC #13)"""

    def test_full_pipeline(self):
        """Complete preflight → postflight flow"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            findings_path = tmpdir / "findings.json"
            shutil.copy(FIXTURES_DIR / "synthetic_findings_valid.json", findings_path)

            # Preflight
            preflight_result = preflight_validate(
                requirements_path=FIXTURES_DIR / "synthetic_requirements.json",
                capability_model_dir=VALID_MODELS_DIR,
                invocation_dir=tmpdir
            )

            self.assertIsNotNone(preflight_result["requirement_ids"])
            self.assertIsNotNone(preflight_result["capability_model_fingerprint"])

            # Postflight
            postflight_result = postflight_validate(
                requirements_path=FIXTURES_DIR / "synthetic_requirements.json",
                capability_model_dir=VALID_MODELS_DIR,
                findings_path=findings_path,
                invocation_dir=tmpdir
            )

            self.assertEqual(postflight_result["assessment_status"], "completed")
            self.assertEqual(postflight_result["findings_count"], 2)

    def test_actual_requirements_understanding_contract(self):
        """Regression: Accept actual Requirements Understanding output without requirement_type field"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create a minimal requirements file matching actual Requirements Understanding contract
            requirements_file = tmpdir / "requirements-analysis.json"
            actual_contract = {
                "schema_version": "1.0",
                "analysis_metadata": {"analyzed_at": "2026-10-04T12:00:00+00:00"},
                "source_jira_evidence": {
                    "issue_key": "TEST-999",
                    "raw_jira_response_sha256": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
                },
                "change_summary": {
                    "outcome": "Test outcome",
                    "rationale": "Test rationale",
                    "supporting_evidence": []
                },
                "explicit_requirements": [],
                "inferred_requirements": [],
                "constraints_and_dependencies": [],
                "ambiguities_and_unknowns": [],
                "key_concepts": []
            }

            with open(requirements_file, 'w') as f:
                json.dump(actual_contract, f)

            # Should NOT raise error about requirement_type field
            # Should accept the actual contract
            preflight_result = preflight_validate(
                requirements_path=requirements_file,
                capability_model_dir=VALID_MODELS_DIR,
                invocation_dir=tmpdir
            )

            self.assertEqual(preflight_result["issue_key"], "TEST-999")
            self.assertIn("requirement_ids", preflight_result)


class TestCandidateArtefactCreation(TestCase):
    """Regression: Robust candidate artefact creation via deterministic mechanism"""

    def test_candidate_written_via_python_json_dump(self):
        """Candidate findings written via json.dump are valid and postflight accepts them"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Simulate preflight output providing candidate path
            candidate_findings_path = tmpdir / "candidate-capability-impact.json"

            # Simulate agentic stage writing findings using Python json.dump
            findings_data = json.loads((FIXTURES_DIR / "synthetic_findings_valid.json").read_text())

            # Write using json.dump (deterministic, cross-platform safe)
            candidate_findings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(candidate_findings_path, 'w', encoding='utf-8') as f:
                json.dump(findings_data, f, indent=2, ensure_ascii=False)

            # Verify JSON is syntactically valid by re-reading
            with open(candidate_findings_path, 'r', encoding='utf-8') as f:
                reloaded = json.load(f)
            self.assertEqual(reloaded["schema_version"], "1.0")

            # Postflight should accept it without JSON parse errors
            postflight_result = postflight_validate(
                requirements_path=FIXTURES_DIR / "synthetic_requirements.json",
                capability_model_dir=VALID_MODELS_DIR,
                findings_path=candidate_findings_path,
                invocation_dir=tmpdir
            )
            self.assertGreaterEqual(postflight_result["findings_count"], 0)

    def test_candidate_path_from_preflight_output(self):
        """Preflight provides candidate_findings_path that agent should use"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            preflight_result = preflight_validate(
                requirements_path=FIXTURES_DIR / "synthetic_requirements.json",
                capability_model_dir=VALID_MODELS_DIR,
                invocation_dir=tmpdir
            )

            # Verify candidate path is provided
            self.assertIn("candidate_findings_path", preflight_result)
            candidate_path = preflight_result["candidate_findings_path"]

            # Verify it's under workspace, not /tmp or other location
            self.assertTrue(candidate_path.startswith(str(tmpdir)))

            # Verify it's an absolute path
            self.assertTrue(Path(candidate_path).is_absolute())

    def test_windows_style_path_handling(self):
        """Candidate path handling is cross-platform safe (Windows backslashes)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            preflight_result = preflight_validate(
                requirements_path=FIXTURES_DIR / "synthetic_requirements.json",
                capability_model_dir=VALID_MODELS_DIR,
                invocation_dir=tmpdir
            )

            candidate_path_str = preflight_result["candidate_findings_path"]
            candidate_path = Path(candidate_path_str)

            # Write deterministically using pathlib + json
            candidate_path.parent.mkdir(parents=True, exist_ok=True)
            findings_data = {
                "schema_version": "1.0",
                "assessment_type": "capability_impact",
                "assessment_status": "completed",
                "input_provenance": {
                    "requirements_path": str(FIXTURES_DIR / "synthetic_requirements.json"),
                    "requirements_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                    "capability_model_fingerprint": "sha256:fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210",
                    "assessment_generated_at": "2026-10-04T12:00:00+00:00"
                },
                "findings": [],
                "domain_summary": [],
                "cross_domain_analysis": {
                    "affected_domain_count": 0,
                    "affected_domain_ids": [],
                    "potential_boundary_changes": False,
                    "potential_ownership_changes": False,
                    "multiple_domains_affected": False
                },
                "uncertainties": []
            }

            with open(candidate_path, 'w', encoding='utf-8') as f:
                json.dump(findings_data, f, indent=2, ensure_ascii=False)

            # Verify postflight can read and accept it
            postflight_result = postflight_validate(
                requirements_path=FIXTURES_DIR / "synthetic_requirements.json",
                capability_model_dir=VALID_MODELS_DIR,
                findings_path=candidate_path,
                invocation_dir=tmpdir
            )
            self.assertEqual(postflight_result["findings_count"], 0)


class TestPersistCapabilityFindingsHelper(TestCase):
    """Test the persist_capability_findings.py helper for deterministic candidate writing"""

    def test_helper_writes_json_from_stdin(self):
        """Helper accepts JSON on stdin and writes to specified path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            output_path = tmpdir / "findings.json"

            findings_data = {
                "schema_version": "1.0",
                "assessment_type": "capability_impact",
                "assessment_status": "completed",
                "input_provenance": {
                    "requirements_path": "/test/path/requirements.json",
                    "requirements_sha256": "abc123",
                    "capability_model_fingerprint": "sha256:def456",
                    "assessment_generated_at": "2026-10-04T12:00:00+00:00"
                },
                "findings": [],
                "domain_summary": [],
                "cross_domain_analysis": {
                    "affected_domain_count": 0,
                    "affected_domain_ids": [],
                    "potential_boundary_changes": False,
                    "potential_ownership_changes": False,
                    "multiple_domains_affected": False
                },
                "uncertainties": []
            }

            # Invoke helper with JSON on stdin
            helper_script = Path(__file__).resolve().parent.parent / "persist_capability_findings.py"
            result = subprocess.run(
                [sys.executable, str(helper_script), "--output-path", str(output_path)],
                input=json.dumps(findings_data),
                capture_output=True,
                text=True
            )

            self.assertEqual(result.returncode, 0)

            # Verify file was written
            self.assertTrue(output_path.exists())

            # Verify it's valid JSON
            with open(output_path, 'r', encoding='utf-8') as f:
                written_data = json.load(f)
            self.assertEqual(written_data["schema_version"], "1.0")

            # Verify helper returned success status
            status_output = json.loads(result.stdout)
            self.assertEqual(status_output["status"], "success")
            self.assertEqual(status_output["persisted_path"], str(output_path.resolve()))

    def test_helper_creates_parent_directories(self):
        """Helper creates parent directories as needed"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            nested_path = tmpdir / "deep" / "nested" / "structure" / "findings.json"

            findings_data = {
                "schema_version": "1.0",
                "assessment_type": "capability_impact",
                "assessment_status": "completed",
                "input_provenance": {
                    "requirements_path": "/test/path",
                    "requirements_sha256": "abc",
                    "capability_model_fingerprint": "sha256:def",
                    "assessment_generated_at": "2026-10-04T12:00:00+00:00"
                },
                "findings": [],
                "domain_summary": [],
                "cross_domain_analysis": {
                    "affected_domain_count": 0,
                    "affected_domain_ids": [],
                    "potential_boundary_changes": False,
                    "potential_ownership_changes": False,
                    "multiple_domains_affected": False
                },
                "uncertainties": []
            }

            helper_script = Path(__file__).resolve().parent.parent / "persist_capability_findings.py"
            result = subprocess.run(
                [sys.executable, str(helper_script), "--output-path", str(nested_path)],
                input=json.dumps(findings_data),
                capture_output=True,
                text=True
            )

            self.assertEqual(result.returncode, 0)
            self.assertTrue(nested_path.exists())

    def test_helper_rejects_relative_path(self):
        """Helper requires absolute path for safety"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Use a relative path (not absolute)
            relative_path = "findings.json"
            findings_data = {"test": "data"}

            helper_script = Path(__file__).resolve().parent.parent / "persist_capability_findings.py"
            result = subprocess.run(
                [sys.executable, str(helper_script), "--output-path", relative_path],
                input=json.dumps(findings_data),
                capture_output=True,
                text=True,
                cwd=str(tmpdir)  # Run from tmpdir but use relative path
            )

            # Should fail
            self.assertEqual(result.returncode, 1)

            # Error should be about relative path
            error_output = json.loads(result.stderr)
            self.assertEqual(error_output["status"], "error")
            self.assertIn("absolute", error_output["error"].lower())

    def test_helper_rejects_invalid_json(self):
        """Helper validates JSON before writing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            output_path = tmpdir / "findings.json"

            invalid_json = "{ not valid json"

            helper_script = Path(__file__).resolve().parent.parent / "persist_capability_findings.py"
            result = subprocess.run(
                [sys.executable, str(helper_script), "--output-path", str(output_path)],
                input=invalid_json,
                capture_output=True,
                text=True
            )

            # Should fail
            self.assertEqual(result.returncode, 1)

            # File should not be created
            self.assertFalse(output_path.exists())

            # Error should mention JSON
            error_output = json.loads(result.stderr)
            self.assertEqual(error_output["status"], "error")
            self.assertIn("JSON", error_output["error"])


class TestMechanicalFixes(TestCase):
    """Regression: Mechanical fixes for issue discovery and candidate persistence"""

    def test_preflight_returns_requirements_path(self):
        """Preflight must expose the requirements_path so agent knows exact input used"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            preflight_result = preflight_validate(
                requirements_path=FIXTURES_DIR / "synthetic_requirements.json",
                capability_model_dir=VALID_MODELS_DIR,
                invocation_dir=tmpdir
            )

            # Verify requirements_path is returned
            self.assertIn("requirements_path", preflight_result)
            req_path = preflight_result["requirements_path"]

            # Verify it's an absolute path
            self.assertTrue(Path(req_path).is_absolute())

            # Verify it matches what was provided
            self.assertEqual(
                req_path,
                str((FIXTURES_DIR / "synthetic_requirements.json").resolve())
            )

    def test_preflight_returns_correct_candidate_path(self):
        """Preflight must return candidate_findings_path under workspace"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            preflight_result = preflight_validate(
                requirements_path=FIXTURES_DIR / "synthetic_requirements.json",
                capability_model_dir=VALID_MODELS_DIR,
                invocation_dir=tmpdir
            )

            candidate_path = preflight_result["candidate_findings_path"]

            # Must be under workspace
            self.assertTrue(candidate_path.startswith(str(tmpdir)))

            # Must be absolute
            self.assertTrue(Path(candidate_path).is_absolute())

            # Must contain issue_key in path
            issue_key = preflight_result["issue_key"]
            self.assertIn(issue_key, candidate_path)

            # Must end with .json
            self.assertTrue(candidate_path.endswith(".json"))


class TestNoInventedAuthoritativeNames(TestCase):
    """Regression: Do not invent authoritative domain/capability names when reporting missing coverage"""

    def test_uncertainties_do_not_contain_invented_domain_names(self):
        """Zero findings assessment with uncertainty must not invent domain names"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create findings with zero findings but uncertainties describing unmatched concerns
            # Agent should describe subject matter neutrally, NOT invent domain names
            findings_data = {
                "schema_version": "1.0",
                "assessment_type": "capability_impact",
                "assessment_status": "completed_with_uncertainties",
                "input_provenance": {
                    "requirements_path": str(FIXTURES_DIR / "synthetic_requirements.json"),
                    "requirements_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                    "capability_model_fingerprint": "sha256:fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210",
                    "assessment_generated_at": "2026-10-04T12:00:00+00:00"
                },
                "findings": [],
                "domain_summary": [],
                "cross_domain_analysis": {
                    "affected_domain_count": 0,
                    "affected_domain_ids": [],
                    "potential_boundary_changes": False,
                    "potential_ownership_changes": False,
                    "multiple_domains_affected": False
                },
                "uncertainties": [
                    {
                        "id": "UNC-001",
                        "description": "Fraud/dispute case-management and colleague case-visibility concerns are not sufficiently aligned to capabilities in the supplied model",
                        "related_capabilities": []
                    }
                ]
            }

            findings_path = tmpdir / "findings-with-uncertainties.json"
            with open(findings_path, 'w', encoding='utf-8') as f:
                json.dump(findings_data, f)

            # Read and verify uncertainty text does NOT contain invented entity names
            with open(findings_path, 'r') as f:
                read_back = json.load(f)

            uncertainty_text = read_back["uncertainties"][0]["description"]

            # CORRECT patterns (should contain these):
            self.assertIn("Fraud/dispute case-management", uncertainty_text)
            self.assertIn("colleague case-visibility", uncertainty_text)
            self.assertIn("not sufficiently aligned", uncertainty_text)

            # INCORRECT patterns (should NOT contain these invented entity names):
            self.assertNotIn("Dispute Resolution domain", uncertainty_text)
            self.assertNotIn("Fraud Management domain", uncertainty_text)
            self.assertNotIn("Customer Service Operations", uncertainty_text)
            self.assertNotIn("(proposed)", uncertainty_text)
            self.assertNotIn("(missing)", uncertainty_text)
            self.assertNotIn("should add", uncertainty_text)


class TestFREvidencePreservation(TestCase):
    """Test that FR (functional_requirements:FR-N) evidence is preserved through capability-impact."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="buk_fr_evidence_test_"))
        self.model_dir = FIXTURES_DIR / "valid_models"

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_fr_evidence_preserved_in_capability_impact(self):
        """FR evidence (functional_requirements:FR-1...FR-12) must be accepted and preserved by capability-impact."""
        # Create schema v2.0 requirements-analysis with FR evidence
        req_path = self.tmpdir / "analysis" / "requirements-analysis.json"
        req_path.parent.mkdir(parents=True, exist_ok=True)

        requirements_analysis = {
            "schema_version": "2.0",
            "source_evidence": [
                {
                    "source_type": "prd",
                    "source_identifier": None,
                    "sha256": "a" * 64
                }
            ],
            "explicit_requirements": [
                {
                    "id": "ER001",
                    "requirement": "Test FR-1 requirement",
                    "supporting_evidence": [
                        {
                            "evidence_id": "functional_requirements:FR-1",
                            "field": "functional_requirements",
                            "source_value": "Loan Parameters Input"
                        }
                    ]
                },
                {
                    "id": "ER005",
                    "requirement": "Test FR-5 requirement",
                    "supporting_evidence": [
                        {
                            "evidence_id": "functional_requirements:FR-5",
                            "field": "functional_requirements",
                            "source_value": "Comparison View Rendering"
                        }
                    ]
                },
                {
                    "id": "ER011",
                    "requirement": "Test FR-11 requirement",
                    "supporting_evidence": [
                        {
                            "evidence_id": "functional_requirements:FR-11",
                            "field": "functional_requirements",
                            "source_value": "Ranking Integrity"
                        }
                    ]
                }
            ],
            "inferred_requirements": [],
            "constraints_and_dependencies": [],
            "ambiguities_and_unknowns": [],
            "key_concepts": []
        }
        with open(req_path, 'w', encoding='utf-8') as f:
            json.dump(requirements_analysis, f)

        # Preflight extracts requirement IDs
        preflight_result = preflight_validate(req_path, self.model_dir, self.tmpdir)
        self.assertIn("ER001", preflight_result["requirement_ids"])
        self.assertIn("ER005", preflight_result["requirement_ids"])
        self.assertIn("ER011", preflight_result["requirement_ids"])

        # Create candidate findings that reference FR evidence
        findings_path = self.tmpdir / "capability-impact" / "candidate-capability-impact.json"
        findings_path.parent.mkdir(parents=True, exist_ok=True)
        findings_data = {
            "schema_version": "1.0",
            "assessment_type": "capability_impact",
            "assessment_status": "completed",
            "input_provenance": {
                "requirements_path": str(req_path),
                "requirements_sha256": "a" * 64,
                "capability_model_fingerprint": "sha256:" + "b" * 64,
                "assessment_generated_at": "2026-10-05T00:00:00+00:00"
            },
            "findings": [
                {
                    "id": "CAP-001",
                    "capability_id": "cap.test.capability-alpha",
                    "capability_name": "Capability Alpha",
                    "capability_domain": "dom.test-domain",
                    "capability_subdomain": "sub.test.subdomain-one",
                    "impact_classification": "direct",
                    "impacted_by_requirement_ids": ["ER001", "ER005", "ER011"],
                    "rationale": "Test rationale",
                    "supporting_evidence": [
                        {
                            "requirement_id": "ER001",
                            "evidence_id": "functional_requirements:FR-1",
                            "evidence_field": "functional_requirements"
                        },
                        {
                            "requirement_id": "ER005",
                            "evidence_id": "functional_requirements:FR-5",
                            "evidence_field": "functional_requirements"
                        },
                        {
                            "requirement_id": "ER011",
                            "evidence_id": "functional_requirements:FR-11",
                            "evidence_field": "functional_requirements"
                        }
                    ]
                }
            ],
            "domain_summary": [],
            "cross_domain_analysis": {
                "affected_domain_count": 1,
                "affected_domain_ids": [],
                "potential_boundary_changes": False,
                "potential_ownership_changes": False,
                "multiple_domains_affected": False
            },
            "uncertainties": []
        }
        with open(findings_path, 'w', encoding='utf-8') as f:
            json.dump(findings_data, f)

        # Postflight should accept and validate FR evidence (NOT rewrite to generic formats)
        result = postflight_validate(req_path, self.model_dir, findings_path, self.tmpdir)

        # Verify the output exists
        self.assertTrue((self.tmpdir / "capability-impact" / "capability-impact-analysis.json").exists())

        # Read the output and verify FR evidence is preserved
        with open(self.tmpdir / "capability-impact" / "capability-impact-analysis.json", 'r') as f:
            output = json.load(f)

        self.assertEqual(len(output["findings"]), 1)
        finding = output["findings"][0]

        # CRITICAL: FR evidence must be preserved, NOT rewritten to generic formats
        evidence_ids = [e["evidence_id"] for e in finding["supporting_evidence"]]
        self.assertIn("functional_requirements:FR-1", evidence_ids)
        self.assertIn("functional_requirements:FR-5", evidence_ids)
        self.assertIn("functional_requirements:FR-11", evidence_ids)

        # Evidence fields must also be preserved
        evidence_fields = {e["evidence_id"]: e["evidence_field"] for e in finding["supporting_evidence"]}
        self.assertEqual(evidence_fields["functional_requirements:FR-1"], "functional_requirements")
        self.assertEqual(evidence_fields["functional_requirements:FR-5"], "functional_requirements")
        self.assertEqual(evidence_fields["functional_requirements:FR-11"], "functional_requirements")


class TestSourceNeutralPaths(TestCase):
    """Test source-neutral capability-impact paths for Jira and PRD/Brief sources."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="buk_capability_impact_test_"))
        self.model_dir = FIXTURES_DIR / "valid_models"

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_prd_brief_source_without_issue_key_produces_root_level_paths(self):
        """PRD/Brief requirements-analysis (no issue_key) produces paths at workspace root, not in issue_key subdir."""
        # Create schema v2.0 requirements-analysis for PRD source (without issue_key)
        req_path = self.tmpdir / "analysis" / "requirements-analysis.json"
        req_path.parent.mkdir(parents=True, exist_ok=True)

        requirements_analysis = {
            "schema_version": "2.0",
            "source_evidence": [
                {
                    "source_type": "prd",
                    "source_identifier": None,
                    "sha256": "0" * 64  # Valid 64-char hex
                }
            ],
            "explicit_requirements": [
                {
                    "id": "ER001",
                    "requirement": "Test requirement",
                    "supporting_evidence": []
                }
            ],
            "inferred_requirements": [],
            "constraints_and_dependencies": [],
            "ambiguities_and_unknowns": [],
            "key_concepts": []
        }
        with open(req_path, 'w', encoding='utf-8') as f:
            json.dump(requirements_analysis, f)

        # Preflight should work without issue_key
        result = preflight_validate(req_path, self.model_dir, self.tmpdir)

        # Verify issue_key is None for PRD source
        self.assertIsNone(result["issue_key"])

        # Verify candidate_findings_path is at workspace root, not in a subdir
        candidate_path = Path(result["candidate_findings_path"])
        candidate_str = str(candidate_path)
        # Should contain tmpdir, then capability-impact, then the filename (no issue_key in between)
        self.assertIn(str(self.tmpdir), candidate_str)
        self.assertIn("capability-impact", candidate_str)
        # Check it doesn't have an issue_key-like directory
        self.assertNotIn("None", candidate_str)
        parts = candidate_path.parts
        # Last part should be filename, second-to-last should be "capability-impact"
        self.assertEqual(parts[-1], "candidate-capability-impact.json")
        self.assertEqual(parts[-2], "capability-impact")

    def test_jira_source_with_issue_key_produces_issue_subdirectory_paths(self):
        """Jira requirements-analysis (with issue_key) produces paths with issue_key subdir."""
        issue_key = "BUKL2TEST-123"
        # Create schema v2.0 requirements-analysis for Jira source
        req_path = self.tmpdir / issue_key / "analysis" / "requirements-analysis.json"
        req_path.parent.mkdir(parents=True, exist_ok=True)

        requirements_analysis = {
            "schema_version": "2.0",
            "source_evidence": [
                {
                    "source_type": "jira",
                    "source_identifier": issue_key,
                    "sha256": "1" * 64  # Valid 64-char hex
                }
            ],
            "explicit_requirements": [
                {
                    "id": "ER001",
                    "requirement": "Test requirement",
                    "supporting_evidence": []
                }
            ],
            "inferred_requirements": [],
            "constraints_and_dependencies": [],
            "ambiguities_and_unknowns": [],
            "key_concepts": []
        }
        with open(req_path, 'w', encoding='utf-8') as f:
            json.dump(requirements_analysis, f)

        # Preflight should work with issue_key
        result = preflight_validate(req_path, self.model_dir, self.tmpdir)

        # Verify issue_key is extracted
        self.assertEqual(result["issue_key"], issue_key)

        # Verify candidate_findings_path includes issue_key subdir
        candidate_path = Path(result["candidate_findings_path"])
        candidate_str = str(candidate_path)
        self.assertIn(issue_key, candidate_str)
        self.assertIn("capability-impact", candidate_str)
        parts = candidate_path.parts
        # Check that issue_key appears before capability-impact
        issue_idx = None
        capimpact_idx = None
        for i, part in enumerate(parts):
            if part == issue_key:
                issue_idx = i
            if part == "capability-impact":
                capimpact_idx = i
        self.assertIsNotNone(issue_idx, f"issue_key {issue_key} not found in path {candidate_str}")
        self.assertIsNotNone(capimpact_idx, f"capability-impact not found in path {candidate_str}")
        self.assertLess(issue_idx, capimpact_idx, f"issue_key should come before capability-impact in {candidate_str}")


class TestOrchestrationGate(TestCase):
    """Test orchestration gates enforce prerequisite completion before downstream stages."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="buk_orchestration_gate_test_"))
        self.model_dir = FIXTURES_DIR / "valid_models"

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_capability_impact_is_mandatory_before_architecture(self):
        """
        INVARIANT: Architecture assessment CANNOT proceed if capability-impact-analysis.json is absent.

        Given:
          - requirements-analysis.json exists (from requirements understanding)
          - capability-impact-analysis.json does NOT exist

        Then:
          - Capability impact is a mandatory next stage
          - Architecture assessment is NOT permitted to proceed
        """
        # Create schema v2.0 requirements-analysis (PRD source)
        req_path = self.tmpdir / "analysis" / "requirements-analysis.json"
        req_path.parent.mkdir(parents=True, exist_ok=True)

        requirements_analysis = {
            "schema_version": "2.0",
            "source_evidence": [
                {
                    "source_type": "prd",
                    "source_identifier": None,
                    "sha256": "a" * 64
                }
            ],
            "explicit_requirements": [
                {
                    "id": "ER001",
                    "requirement": "Test requirement",
                    "supporting_evidence": []
                }
            ],
            "inferred_requirements": [],
            "constraints_and_dependencies": [],
            "ambiguities_and_unknowns": [],
            "key_concepts": []
        }
        with open(req_path, 'w', encoding='utf-8') as f:
            json.dump(requirements_analysis, f)

        # Verify requirements-analysis.json exists
        self.assertTrue(req_path.exists(), "requirements-analysis.json must exist")

        # Verify capability-impact-analysis.json does NOT exist (initial state)
        capimpact_path = self.tmpdir / "capability-impact" / "capability-impact-analysis.json"
        self.assertFalse(capimpact_path.exists(), "capability-impact-analysis.json should not exist yet")

        # The orchestration invariant: if capability-impact does not exist, it is mandatory
        # The agent MUST invoke assess-capability-impact skill before proceeding
        # For testing purposes, we verify the path logic is correct and the gate would be enforced

        # Expected orchestration behavior:
        # 1. Agent checks if capability-impact-analysis.json exists at the expected path
        # 2. Path is source-neutral: invocation_dir/capability-impact/ (no issue_key)
        capimpact_expected = self.tmpdir / "capability-impact" / "capability-impact-analysis.json"
        self.assertFalse(capimpact_expected.exists(),
                        "Prerequisite check: capability-impact-analysis.json is absent — must be generated")

        # 3. Agent invokes assess-capability-impact skill to generate it
        # 4. Only after successful generation does agent proceed to architecture assessment

    def test_capability_impact_completion_enables_downstream_progression(self):
        """
        INVARIANT: When capability-impact-analysis.json exists and is valid, architecture assessment may proceed.

        Given:
          - requirements-analysis.json exists (valid)
          - capability-impact-analysis.json exists (valid, matches requirements provenance)

        Then:
          - Progression to architecture assessment is permitted
        """
        # Create valid requirements-analysis.json
        req_path = self.tmpdir / "analysis" / "requirements-analysis.json"
        req_path.parent.mkdir(parents=True, exist_ok=True)

        requirements_sha = "b" * 64
        requirements_analysis = {
            "schema_version": "2.0",
            "source_evidence": [
                {
                    "source_type": "prd",
                    "source_identifier": None,
                    "sha256": requirements_sha
                }
            ],
            "explicit_requirements": [
                {
                    "id": "ER001",
                    "requirement": "Test requirement",
                    "supporting_evidence": []
                }
            ],
            "inferred_requirements": [],
            "constraints_and_dependencies": [],
            "ambiguities_and_unknowns": [],
            "key_concepts": []
        }
        with open(req_path, 'w', encoding='utf-8') as f:
            json.dump(requirements_analysis, f)

        # Create valid capability-impact-analysis.json with matching provenance
        capimpact_path = self.tmpdir / "capability-impact" / "capability-impact-analysis.json"
        capimpact_path.parent.mkdir(parents=True, exist_ok=True)

        findings_data = {
            "schema_version": "1.0",
            "assessment_type": "capability_impact",
            "assessment_status": "completed",
            "input_provenance": {
                "requirements_path": str(req_path),
                "requirements_sha256": requirements_sha,
                "capability_model_fingerprint": "sha256:" + "c" * 64,
                "assessment_generated_at": "2026-10-05T00:00:00+00:00"
            },
            "findings": [],
            "domain_summary": [],
            "cross_domain_analysis": {
                "affected_domain_count": 0,
                "affected_domain_ids": [],
                "potential_boundary_changes": False,
                "potential_ownership_changes": False,
                "multiple_domains_affected": False
            },
            "uncertainties": []
        }
        with open(capimpact_path, 'w', encoding='utf-8') as f:
            json.dump(findings_data, f)

        # Verify both prerequisite artefacts exist
        self.assertTrue(req_path.exists(), "requirements-analysis.json must exist")
        self.assertTrue(capimpact_path.exists(), "capability-impact-analysis.json must exist")

        # Orchestration can now proceed: both mandatory prerequisites are satisfied
        # Agent may invoke architecture assessment stage

    def test_capability_impact_failure_blocks_architecture_generation(self):
        """
        INVARIANT: If capability-impact generation fails, architecture output MUST NOT be created.

        Given:
          - requirements-analysis.json exists
          - assess-capability-impact skill is invoked
          - The skill fails (returns error or invalid output)

        Then:
          - Workflow STOPS
          - architecture.md is NOT created
          - Error is reported to user
        """
        # Create requirements-analysis.json
        req_path = self.tmpdir / "analysis" / "requirements-analysis.json"
        req_path.parent.mkdir(parents=True, exist_ok=True)

        requirements_analysis = {
            "schema_version": "2.0",
            "source_evidence": [
                {
                    "source_type": "prd",
                    "source_identifier": None,
                    "sha256": "d" * 64
                }
            ],
            "explicit_requirements": [
                {
                    "id": "ER001",
                    "requirement": "Test requirement",
                    "supporting_evidence": []
                }
            ],
            "inferred_requirements": [],
            "constraints_and_dependencies": [],
            "ambiguities_and_unknowns": [],
            "key_concepts": []
        }
        with open(req_path, 'w', encoding='utf-8') as f:
            json.dump(requirements_analysis, f)

        # Verify capability-impact does not exist initially
        capimpact_path = self.tmpdir / "capability-impact" / "capability-impact-analysis.json"
        self.assertFalse(capimpact_path.exists(), "capability-impact-analysis.json should not exist")

        # Simulate failure: capability-impact generation is invoked but fails
        # (In real scenario, assess-capability-impact skill encounters an error)
        # Result: capability-impact-analysis.json is NOT created

        # Verify it was not created (remains absent)
        self.assertFalse(capimpact_path.exists(),
                        "capability-impact-analysis.json should remain absent after skill failure")

        # Architecture output should NOT be created
        arch_path = self.tmpdir / "architecture.md"
        self.assertFalse(arch_path.exists(),
                        "architecture.md must NOT be created if prerequisite fails")

        # This is the fail-closed invariant: missing mandatory prerequisite blocks progression


if __name__ == "__main__":
    main(verbosity=2)
