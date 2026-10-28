"""Tests for verification_manifest.py — evidence section embedded in the remediation report."""

import sys
from pathlib import Path
from unittest import TestCase, main

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.validators.verification_manifest import (
    compute_summary,
    generate_rescan_instructions,
    build_accountability_matrix,
    build_evidence_section,
    embed_section,
    EVIDENCE_PLACEHOLDER,
    SECTION_BEGIN,
    SECTION_END,
    render_evidence_table,
    render_finding_details,
    SCHEMA_VERSION,
)


def _make_record(classification="VERIFIED", method="wiz_cli", verified_by="wizcli v0.105.0",
                 cwe="CWE-89", file_path="src/db/queries.py", severity="CRITICAL",
                 commit_sha="abc1234"):
    return {
        "finding_id": "wiz-001",
        "cwe_id": cwe,
        "file_path": file_path,
        "original_finding": {
            "source": "wiz",
            "rule_id": "WS-SQL-INJECT-001",
            "severity": severity,
            "title": "SQL Injection",
        },
        "fix_applied": {
            "commit_sha": commit_sha,
            "diff_summary": "Parameterized query",
        },
        "verification": {
            "method": method,
            "verdict": "RESOLVED",
            "confidence": "high" if method == "wiz_cli" else "medium",
            "verified_by": verified_by,
            "delta": {"resolved": 1, "persistent": 0, "new": 0},
        },
        "accountability": {
            "fixed_by": "detox-pipeline",
            "verified_by": verified_by,
            "classification": classification,
        },
    }


class TestComputeSummary(TestCase):
    def test_all_verified(self):
        records = [_make_record("VERIFIED"), _make_record("VERIFIED")]
        s = compute_summary(records)
        self.assertEqual(s["total_findings"], 2)
        self.assertEqual(s["verified"], 2)
        self.assertEqual(s["unverified"], 0)
        self.assertEqual(s["failed"], 0)

    def test_mixed(self):
        records = [
            _make_record("VERIFIED"),
            _make_record("UNVERIFIED", "semgrep", "semgrep 1.96.0"),
            _make_record("FAILED"),
        ]
        s = compute_summary(records)
        self.assertEqual(s["verified"], 1)
        self.assertEqual(s["unverified"], 1)
        self.assertEqual(s["failed"], 1)

    def test_empty(self):
        s = compute_summary([])
        self.assertEqual(s["total_findings"], 0)

    def test_all_failed(self):
        records = [_make_record("FAILED"), _make_record("FAILED")]
        s = compute_summary(records)
        self.assertEqual(s["failed"], 2)
        self.assertEqual(s["verified"], 0)

    def test_missing_classification_defaults_unverified(self):
        record = {"accountability": {}}
        s = compute_summary([record])
        self.assertEqual(s["unverified"], 1)


class TestGenerateRescanInstructions(TestCase):
    def test_wiz_command_present(self):
        instructions = generate_rescan_instructions()
        self.assertIn("wizcli", instructions["wiz_cli"])
        self.assertIn("--no-publish", instructions["wiz_cli"])

    def test_semgrep_command_present(self):
        instructions = generate_rescan_instructions()
        self.assertIn("semgrep", instructions["semgrep"])


class TestBuildAccountabilityMatrix(TestCase):
    def test_single_method(self):
        records = [_make_record("VERIFIED", "wiz_cli")]
        matrix = build_accountability_matrix(records)
        self.assertEqual(matrix["pipeline_tool"], "detox")
        self.assertEqual(matrix["primary_verifier"], "wiz_cli")

    def test_mixed_methods(self):
        records = [
            _make_record("VERIFIED", "wiz_cli"),
            _make_record("UNVERIFIED", "semgrep", "semgrep 1.96.0"),
        ]
        matrix = build_accountability_matrix(records)
        self.assertEqual(matrix["primary_verifier"], "wiz_cli")
        self.assertEqual(matrix["fallback_verifier"], "semgrep")

    def test_no_records(self):
        matrix = build_accountability_matrix([])
        self.assertEqual(matrix["primary_verifier"], "none")


class TestRenderEvidenceTable(TestCase):
    def test_table_has_header(self):
        records = [_make_record()]
        table = render_evidence_table(records)
        self.assertIn("| # | CWE | File |", table)
        self.assertIn("Verified/Rejected By", table)
        self.assertIn("Proof", table)

    def test_verified_shows_verifier_and_proof(self):
        records = [_make_record()]
        table = render_evidence_table(records)
        self.assertIn("CWE-89", table)
        self.assertIn("wizcli v0.105.0", table)
        self.assertIn("resolved", table)

    def test_failed_shows_persistent(self):
        records = [_make_record("FAILED")]
        table = render_evidence_table(records)
        self.assertIn("FAILED", table)
        self.assertIn("still present", table)

    def test_unverified_shows_reason(self):
        record = _make_record("UNVERIFIED", "none", "none")
        record["verification"]["reason"] = "wizcli not installed"
        record["verification"]["confidence"] = "none"
        records = [record]
        table = render_evidence_table(records)
        self.assertIn("wizcli not installed", table)

    def test_empty_records(self):
        table = render_evidence_table([])
        self.assertIn("No evidence records", table)

    def test_commit_sha_truncated(self):
        records = [_make_record(commit_sha="abcdef1234567890")]
        table = render_evidence_table(records)
        self.assertIn("`abcdef1`", table)


class TestRenderFindingDetails(TestCase):
    def test_verified_shows_proof(self):
        record = _make_record("VERIFIED")
        record["verification"]["pre_scan"] = {"finding_count": 2}
        record["verification"]["post_scan"] = {"finding_count": 0}
        details = render_finding_details([record])
        self.assertIn("### Finding 1:", details)
        self.assertIn("Proof of fix", details)
        self.assertIn("wizcli v0.105.0", details)
        self.assertIn("Baseline findings (before fix)", details)
        self.assertIn("Post-fix findings (after fix)", details)

    def test_failed_shows_what_persists(self):
        record = _make_record("FAILED")
        record["verification"]["verdict"] = "PERSISTENT"
        record["verification"]["delta"] = {"resolved": 0, "persistent": 1, "new": 0}
        record["verification"]["pre_scan"] = {"finding_count": 1}
        record["verification"]["post_scan"] = {"finding_count": 1}
        details = render_finding_details([record])
        self.assertIn("Fix did not work", details)
        self.assertIn("confirmed by wizcli", details)
        self.assertIn("Manual review needed", details)

    def test_unverified_with_semgrep_explains_why_not_verified(self):
        record = _make_record("UNVERIFIED", "semgrep", "semgrep 1.96.0")
        record["verification"]["confidence"] = "medium"
        details = render_finding_details([record])
        self.assertIn("Partially checked", details)
        self.assertIn("WIZ has not confirmed", details)
        self.assertIn("not authoritative", details)

    def test_unverified_none_shows_reason_and_action(self):
        record = _make_record("UNVERIFIED", "none", "none")
        record["verification"]["confidence"] = "none"
        record["verification"]["reason"] = "wiz_cli: wizcli not installed; semgrep: file not found"
        record["verification"]["action_required"] = "Install WIZ CLI: brew install --cask wizcli"
        details = render_finding_details([record])
        self.assertIn("Not verified", details)
        self.assertIn("wizcli not installed", details)
        self.assertIn("Install WIZ CLI", details)

    def test_empty(self):
        details = render_finding_details([])
        self.assertEqual(details, "")


class TestBuildEvidenceSection(TestCase):
    def test_wrapped_in_markers(self):
        md = build_evidence_section("job-1", [])
        self.assertTrue(md.startswith(SECTION_BEGIN))
        self.assertTrue(md.endswith(SECTION_END))

    def test_has_heading(self):
        md = build_evidence_section("job-1", [])
        self.assertIn("## Evidence & Verification", md)

    def test_has_job_id(self):
        md = build_evidence_section("abc123", [])
        self.assertIn("abc123", md)

    def test_has_summary_table(self):
        records = [_make_record("VERIFIED"), _make_record("FAILED")]
        md = build_evidence_section("job-1", records)
        self.assertIn("| **Total Findings** | **2** |", md)

    def test_has_evidence_table(self):
        md = build_evidence_section("job-1", [_make_record()])
        self.assertIn("### Evidence Table", md)
        self.assertIn("CWE-89", md)

    def test_finding_details_nested_under_section(self):
        md = build_evidence_section("job-1", [_make_record()])
        self.assertIn("#### Finding 1: CWE-89", md)

    def test_has_rescan_instructions(self):
        md = build_evidence_section("job-1", [])
        self.assertIn("wizcli dir scan", md)
        self.assertIn("semgrep --config auto", md)

    def test_has_classification_legend(self):
        md = build_evidence_section("job-1", [])
        self.assertIn("✅ VERIFIED", md)
        self.assertIn("⚠️ UNVERIFIED", md)
        self.assertIn("❌ FAILED", md)

    def test_has_accountability_matrix(self):
        md = build_evidence_section("job-1", [_make_record()])
        self.assertIn("### Accountability Matrix", md)
        self.assertIn("detox", md)

    def test_portal_note(self):
        md = build_evidence_section("job-1", [])
        self.assertIn("WIZ portal updates", md)


class TestEmbedSection(TestCase):
    SECTION = f"{SECTION_BEGIN}\nnew evidence\n{SECTION_END}"

    def test_replaces_placeholder(self):
        report = f"# Report\n\n{EVIDENCE_PLACEHOLDER}\n\n## Fixes Applied\n"
        out = embed_section(report, self.SECTION)
        self.assertNotIn(EVIDENCE_PLACEHOLDER, out)
        self.assertLess(out.index("new evidence"), out.index("## Fixes Applied"))

    def test_rerun_replaces_previous_embed(self):
        report = f"# Report\n\n{SECTION_BEGIN}\nold evidence\n{SECTION_END}\n\n## Fixes Applied\n"
        out = embed_section(report, self.SECTION)
        self.assertNotIn("old evidence", out)
        self.assertEqual(out.count(SECTION_BEGIN), 1)
        self.assertIn("## Fixes Applied", out)

    def test_appends_when_no_placeholder(self):
        out = embed_section("# Report\n", self.SECTION)
        self.assertTrue(out.startswith("# Report"))
        self.assertTrue(out.rstrip().endswith(SECTION_END))


if __name__ == "__main__":
    main()
