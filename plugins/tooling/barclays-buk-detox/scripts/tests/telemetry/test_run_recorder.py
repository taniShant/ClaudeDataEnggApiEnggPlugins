"""Tests for run_recorder.py — run summary writer."""

import json
import sys
import tempfile
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.telemetry.run_recorder import (
    compute_duration_ms,
    extract_repo_name,
    extract_cwes_targeted,
    count_by_field,
    compute_phase_durations,
    build_run_record,
    build_unresolved_vulns,
    NO_LLM_REASON,
    record_run,
    export_to_otel,
    _job_already_recorded,
    _build_telemetry_message,
    _telemetry_status_message,
    backfill_report_telemetry,
    REPORT_TELEMETRY_PENDING,
    merge_state,
    FLAG_STATE_INCOMPLETE,
    FLAG_STATE_FILE_MISSING,
)


class TestComputeDurationMs(TestCase):
    def test_valid_timestamps(self):
        result = compute_duration_ms(
            "2026-08-20T10:00:00.000Z",
            "2026-08-20T10:05:30.000Z"
        )
        self.assertEqual(result, 330000)

    def test_subsecond_precision(self):
        result = compute_duration_ms(
            "2026-08-20T10:00:00.000Z",
            "2026-08-20T10:00:01.500Z"
        )
        self.assertEqual(result, 1500)

    def test_none_started_at(self):
        result = compute_duration_ms(None, "2026-08-20T10:00:00Z")
        self.assertIsNone(result)

    def test_none_ended_at(self):
        result = compute_duration_ms("2026-08-20T10:00:00Z", None)
        self.assertIsNone(result)

    def test_invalid_timestamp(self):
        result = compute_duration_ms("not-a-date", "also-not-a-date")
        self.assertIsNone(result)


class TestExtractRepoName(TestCase):
    def test_from_identity(self):
        result = extract_repo_name("/repos/something", {"repo_name": "my-service"})
        self.assertEqual(result, "my-service")

    def test_falls_back_to_path_basename(self):
        result = extract_repo_name("/repos/fallback-repo", {})
        self.assertEqual(result, "fallback-repo")

    def test_handles_none(self):
        result = extract_repo_name(None, None)
        self.assertEqual(result, "unknown")


class TestExtractCwesTargeted(TestCase):
    def test_extracts_unique_cwes(self):
        vulns = [
            {"cwe_id": "CWE-79"},
            {"cwe_id": "CWE-89"},
            {"cwe_id": "CWE-79"},  # duplicate
            {"cwe_id": "CWE-798"},
        ]
        result = extract_cwes_targeted(vulns)
        self.assertEqual(result, ["CWE-79", "CWE-798", "CWE-89"])

    def test_skips_none_cwe_id(self):
        vulns = [{"cwe_id": "CWE-79"}, {"cwe_id": None}, {"title": "no cwe"}]
        result = extract_cwes_targeted(vulns)
        self.assertEqual(result, ["CWE-79"])

    def test_empty_list(self):
        result = extract_cwes_targeted([])
        self.assertEqual(result, [])

    def test_dependency_without_cwe_is_cwe_937(self):
        vulns = [
            {"cwe_id": None, "remediation_type": "dependency"},
            {"remediation_type": "dependency"},
            {"cwe_id": None, "remediation_type": "code_fix"},
        ]
        self.assertEqual(extract_cwes_targeted(vulns), ["CWE-937"])

    def test_dependency_keeps_explicit_cwe(self):
        vulns = [{"cwe_id": "CWE-502", "remediation_type": "dependency"}]
        self.assertEqual(extract_cwes_targeted(vulns), ["CWE-502"])

    def test_falls_back_to_fix_result_cwe(self):
        vulns = [{"id": "v1", "cwe_id": None, "remediation_type": "code_fix"}, {"id": "v2"}]
        fixes = [{"vulnerability_id": "v1", "cwe_id": "CWE-89"}]
        self.assertEqual(extract_cwes_targeted(vulns, fixes), ["CWE-89"])

    def test_report_cwe_wins_over_fix_result(self):
        vulns = [{"id": "v1", "cwe_id": "CWE-79"}]
        fixes = [{"vulnerability_id": "v1", "cwe_id": "CWE-89"}]
        self.assertEqual(extract_cwes_targeted(vulns, fixes), ["CWE-79"])


class TestCountByField(TestCase):
    def test_counts_correctly(self):
        items = [
            {"severity": "high"},
            {"severity": "high"},
            {"severity": "medium"},
            {"severity": "low"},
        ]
        result = count_by_field(items, "severity")
        self.assertEqual(result, {"high": 2, "medium": 1, "low": 1})

    def test_missing_field(self):
        items = [{"other": "value"}, {"severity": "high"}]
        result = count_by_field(items, "severity")
        self.assertIn("unknown", result)
        self.assertEqual(result["high"], 1)


class TestComputePhaseDurations(TestCase):
    def test_computes_from_timestamps(self):
        phases = {
            "1": {
                "status": "completed",
                "started_at": "2026-08-20T10:00:00.000Z",
                "ended_at": "2026-08-20T10:00:07.100Z",
            },
            "2": {"status": "pending"},
        }
        result = compute_phase_durations(phases)
        self.assertEqual(result["1"]["status"], "completed")
        self.assertEqual(result["1"]["duration_ms"], 7100)
        self.assertEqual(result["2"]["status"], "pending")
        self.assertNotIn("duration_ms", result["2"])

    def test_handles_missing_timestamps(self):
        phases = {"1": {"status": "completed"}}
        result = compute_phase_durations(phases)
        self.assertNotIn("duration_ms", result["1"])


class TestBuildRunRecord(TestCase):
    def test_builds_complete_record(self):
        input_data = {
            "state": {
                "job_id": "abc12345",
                "project_path": "/repos/my-svc",
                "started_at": "2026-08-20T10:00:00.000Z",
                "model": "opus",
                "severity_filter": "critical+high",
                "dry_run": False,
                "phases": {
                    "1": {"status": "completed", "started_at": "2026-08-20T10:00:01Z", "ended_at": "2026-08-20T10:00:08Z"},
                },
                "vulnerabilities": [
                    {"cwe_id": "CWE-79", "severity": "high", "remediation_type": "code_fix"},
                    {"cwe_id": "CWE-89", "severity": "critical", "remediation_type": "code_fix"},
                ],
                "fix_results": [
                    {"status": "success", "validation_passed": True, "retry_count": 0},
                    {"status": "failed", "validation_passed": False, "retry_count": 1},
                ],
                "test_results": [{"status": "success"}],
                "pr_url": "https://gitlab.com/merge/1",
            },
            "identity": {
                "user_name": "testuser",
                "user_email": "test@barclays.com",
                "repo_name": "my-svc",
                "cio": "DIGITAL",
            },
            "ended_at": "2026-08-20T10:05:00.000Z",
            "agent_invocations": 10,
            "flags_raised": [],
            "self_check_passed": True,
        }

        record = build_run_record(input_data)

        self.assertEqual(record["job_id"], "abc12345")
        self.assertEqual(record["repo_name"], "my-svc")
        self.assertEqual(record["cio"], "DIGITAL")
        self.assertEqual(record["total_duration_ms"], 300000)
        self.assertEqual(record["vulns_total"], 2)
        self.assertEqual(record["fixes_succeeded"], 1)
        self.assertEqual(record["fixes_failed"], 1)
        self.assertEqual(record["retries_total"], 1)
        self.assertEqual(record["validation_pass_count"], 1)
        self.assertEqual(record["validation_fail_count"], 1)
        self.assertEqual(record["tests_generated"], 1)
        self.assertTrue(record["pr_created"])
        self.assertEqual(record["agent_invocations"], 10)
        self.assertNotIn("estimated_budget_cap_usd", record)  # financial field removed
        # Derived pure-tech rates: 1 succeeded of 2 vulns / 2 attempted
        self.assertEqual(record["remediation_rate"], 0.5)
        self.assertEqual(record["fix_success_rate"], 0.5)
        self.assertEqual(record["fix_failure_rate"], 0.5)
        self.assertEqual(record["deferral_rate"], 0.0)
        self.assertIn("CWE-79", record["cwes_targeted"])
        self.assertIn("CWE-89", record["cwes_targeted"])


class TestReasonMaps(TestCase):
    """vulns_deferred_by_reason comes from unresolved_items; fixes_unverified_by_reason reconciles."""

    def _record(self, vulns, fix_results, unresolved_items=None):
        state = {"job_id": "j", "vulnerabilities": vulns, "fix_results": fix_results,
                 "test_results": [], "phases": {}}
        if unresolved_items is not None:
            state["unresolved_items"] = unresolved_items
        return build_run_record({
            "state": state,
            "identity": {}, "agent_invocations": len(fix_results),
        })

    def test_deferred_by_reason_from_unresolved_items(self):
        unresolved = [
            {"id": "v1", "remediation_type": "manual"},
            {"id": "v2", "remediation_type": "manual"},
            {"id": "v3", "remediation_type": "hybrid"},
            {"id": "v4", "remediation_type": "out_of_repo"},
            {"id": "v5", "remediation_type": "likely_unexploitable"},
        ]
        r = self._record([], [], unresolved)
        self.assertEqual(r["vulns_deferred_by_reason"],
                         {"manual": 2, "hybrid": 1, "out_of_repo": 1, "likely_unexploitable": 1})

    def test_deferred_by_reason_ignores_vulnerabilities(self):
        # Never-attempted vulns no longer feed the map — only unresolved_items does.
        vulns = [{"id": f"v{i}", "remediation_type": "manual"} for i in range(5)]
        r = self._record(vulns, [])
        self.assertEqual(r["vulns_deferred"], 5)
        self.assertEqual(r["vulns_deferred_by_reason"], {})

    def test_deferred_by_reason_unspecified_for_malformed_items(self):
        unresolved = ["corrective_actions_output/CA-1.md", {"id": "v1"}, {"remediation_type": ""}]
        r = self._record([], [], unresolved)
        self.assertEqual(r["vulns_deferred_by_reason"], {"unspecified": 3})

    def test_deferred_by_reason_handles_null_unresolved_items(self):
        r = self._record([], [], None)
        self.assertEqual(r["vulns_deferred_by_reason"], {})
        r = build_run_record({"state": {"unresolved_items": None}, "identity": {}})
        self.assertEqual(r["vulns_deferred_by_reason"], {})

    def test_unverified_by_reason_reconciles(self):
        vulns = [{"id": f"v{i}", "remediation_type": "dependency"} for i in range(3)]
        fr = [
            {"vulnerability_id": "v0", "status": "success", "validation_passed": True},   # clean
            {"vulnerability_id": "v1", "status": "success", "validation_passed": False},  # still_detected
            {"vulnerability_id": "v2", "status": "failed"},                               # fix_failed
        ]
        r = self._record(vulns, fr)
        self.assertEqual(r["fixes_validated_clean"], 1)
        by = r["fixes_unverified_by_reason"]
        self.assertEqual(sum(by.values()), r["fixes_attempted"] - r["fixes_validated_clean"])  # == 2
        self.assertEqual(by.get("still_detected"), 1)
        self.assertEqual(by.get("fix_failed"), 1)

    def test_no_deferred_no_unverified_when_all_clean(self):
        vulns = [{"id": "v0", "remediation_type": "dependency"}]
        fr = [{"vulnerability_id": "v0", "status": "success", "validation_passed": True}]
        r = self._record(vulns, fr)
        self.assertEqual(r["vulns_deferred_by_reason"], {})
        self.assertEqual(r["fixes_unverified_by_reason"], {})


class TestBuildUnresolvedVulns(TestCase):
    def _by_id(self, state):
        return {r["vuln_id"]: r for r in build_unresolved_vulns(state)}

    def test_which_findings_are_unfixed(self):
        vulns = [{"id": f"v{i}", "severity": "high"} for i in range(5)]
        state = {"vulnerabilities": vulns, "fix_results": [
            {"vulnerability_id": "v0", "status": "success", "validation_passed": True},
            {"vulnerability_id": "v1", "status": "success"},  # applied, not validated -> fixed
            {"vulnerability_id": "v2", "status": "success", "validation_passed": False},
            {"vulnerability_id": "v3", "status": "failed"},
        ]}  # v4 never attempted
        self.assertEqual(sorted(self._by_id(state)), ["v2", "v3", "v4"])

    def test_llm_reason_used_verbatim(self):
        reason = "Upgrade to 2.17 breaks the Spring 4 BOM;\n  needs a coordinated platform bump"
        state = {"vulnerabilities": [{"id": "v1", "severity": "high"}],
                 "fix_results": [{"vulnerability_id": "v1", "status": "failed", "unfixed_reason": reason}]}
        self.assertEqual(build_unresolved_vulns(state)[0]["reason"], reason)

    def test_no_llm_reason_no_fallback(self):
        state = {"vulnerabilities": [{"id": "v1", "severity": "high", "remediation_type": "infra_config"},
                                     {"id": "v2", "severity": "high"}],
                 "fix_results": [{"vulnerability_id": "v2", "status": "failed", "unfixed_reason": "  "}]}
        by = self._by_id(state)
        self.assertEqual(by["v1"]["reason"], NO_LLM_REASON)
        self.assertEqual(by["v2"]["reason"], NO_LLM_REASON)
        self.assertNotIn("reason_code", by["v1"])

    def test_reason_lookup_order(self):
        state = {
            "vulnerabilities": [{"id": "v1", "severity": "high"}, {"id": "v2", "severity": "high"},
                                {"id": "v3", "severity": "high"}],
            "fix_results": [{"vulnerability_id": "v1", "status": "failed", "unfixed_reason": "from fix"},
                            {"vulnerability_id": "v2", "status": "failed", "unfixed_reason": "from fix"}],
            "unresolved_items": [{"id": "v1", "unfixed_reason": "from stage 8"}],
            "infra_findings": [{"id": "v3", "unfixed_reason": "from infra bucket"}],
        }
        by = self._by_id(state)
        self.assertEqual(by["v1"]["reason"], "from stage 8")
        self.assertEqual(by["v2"]["reason"], "from fix")
        self.assertEqual(by["v3"]["reason"], "from infra bucket")

    def test_unresolved_items_add_entries_and_ignore_non_dicts(self):
        state = {
            "vulnerabilities": [],
            "unresolved_items": [
                {"id": "ATK-3", "cwe_id": "CWE-287", "remediation_type": "partially_addressed",
                 "unfixed_reason": "Session fixation fix needs gateway change"},
                {"id": "ATK-4"},
                "corrective_actions_output/CA-x.md",
            ],
        }
        by = self._by_id(state)
        self.assertEqual(by["ATK-3"]["reason"], "Session fixation fix needs gateway change")
        self.assertEqual(by["ATK-3"]["cwe_id"], "CWE-287")
        self.assertEqual(by["ATK-4"]["reason"], NO_LLM_REASON)
        self.assertEqual(len(by), 2)

    def test_credentials_redacted(self):
        state = {"vulnerabilities": [{"id": "v1", "severity": "high"}],
                 "fix_results": [{"vulnerability_id": "v1", "status": "failed",
                                  "unfixed_reason": "clone failed with glpat-abcdefghij1234567890"}]}
        reason = build_unresolved_vulns(state)[0]["reason"]
        self.assertNotIn("glpat-abcdefghij1234567890", reason)
        self.assertTrue(reason.startswith("clone failed with "))

    def test_severity_filtered_and_dry_run_excluded(self):
        vulns = [{"id": "v1", "severity": "low", "remediation_type": "code_fix"},
                 {"id": "v2", "severity": "critical", "remediation_type": "manual"}]
        by = self._by_id({"severity_filter": "critical+high", "vulnerabilities": vulns})
        self.assertEqual(list(by), ["v2"])
        self.assertEqual(build_unresolved_vulns({"dry_run": True, "vulnerabilities": vulns}), [])

    def test_included_in_run_record(self):
        r = build_run_record({"state": {"vulnerabilities": [{"id": "v1", "remediation_type": "manual"}]},
                              "identity": {}})
        self.assertEqual(r["unresolved_vulns"][0]["reason"], NO_LLM_REASON)


class TestRecordRun(TestCase):
    def setUp(self):
        # OTel export is now always-on (hardcoded endpoint). Stub it so these
        # record_run unit tests never make a real network call to the Collector.
        self._otel_patcher = patch(
            "scripts.telemetry.run_recorder.export_to_otel",
            return_value={"status": "success", "job_id": "test"},
        )
        self._otel_patcher.start()

    def tearDown(self):
        self._otel_patcher.stop()

    def test_appends_to_runs_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runs_file = Path(tmpdir) / "runs.jsonl"
            with patch("scripts.telemetry.run_recorder.RUNS_FILE", runs_file), \
                 patch("scripts.telemetry.run_recorder.TELEMETRY_DIR", Path(tmpdir)):
                input_data = {
                    "action": "record",
                    "state": {
                        "job_id": "test1234",
                        "project_path": "/repos/test",
                        "started_at": "2026-08-20T10:00:00Z",
                        "model": "sonnet",
                        "severity_filter": "all",
                        "dry_run": False,
                        "phases": {},
                        "vulnerabilities": [],
                        "fix_results": [],
                        "test_results": [],
                    },
                    "identity": {"user_name": "dev", "repo_name": "test"},
                    "ended_at": "2026-08-20T10:01:00Z",
                }
                result = record_run(input_data)
                self.assertEqual(result["status"], "success")
                self.assertEqual(result["job_id"], "test1234")

                # Verify file content
                lines = runs_file.read_text().strip().split("\n")
                self.assertEqual(len(lines), 1)
                record = json.loads(lines[0])
                self.assertEqual(record["job_id"], "test1234")
                self.assertEqual(record["repo_name"], "test")

    def test_creates_directory_if_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = Path(tmpdir) / "new" / "path"
            runs_file = nested_dir / "runs.jsonl"
            with patch("scripts.telemetry.run_recorder.RUNS_FILE", runs_file), \
                 patch("scripts.telemetry.run_recorder.TELEMETRY_DIR", nested_dir):
                result = record_run({
                    "action": "record",
                    "state": {"job_id": "x", "project_path": "/r", "started_at": "2026-08-20T10:00:00Z",
                              "model": "s", "phases": {}, "vulnerabilities": [], "fix_results": [], "test_results": []},
                    "identity": {"user_name": "u", "repo_name": "r"},
                    "ended_at": "2026-08-20T10:01:00Z",
                })
                self.assertEqual(result["status"], "success")
                self.assertTrue(runs_file.exists())


class TestJobAlreadyRecorded(TestCase):
    """Unit tests for the _job_already_recorded helper."""

    def test_returns_false_when_file_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("scripts.telemetry.run_recorder.RUNS_FILE", Path(tmpdir) / "nope.jsonl"):
                self.assertFalse(_job_already_recorded("abc123"))

    def test_returns_true_when_job_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runs_file = Path(tmpdir) / "runs.jsonl"
            runs_file.write_text('{"job_id": "abc123", "status": "completed"}\n')
            with patch("scripts.telemetry.run_recorder.RUNS_FILE", runs_file):
                self.assertTrue(_job_already_recorded("abc123"))

    def test_returns_false_when_job_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runs_file = Path(tmpdir) / "runs.jsonl"
            runs_file.write_text('{"job_id": "other", "status": "completed"}\n')
            with patch("scripts.telemetry.run_recorder.RUNS_FILE", runs_file):
                self.assertFalse(_job_already_recorded("abc123"))


class TestIdempotencyGuard(TestCase):
    """Integration tests for the idempotency guard in record_run."""

    def setUp(self):
        # Stub always-on OTel export so these tests never hit the network.
        self._otel_patcher = patch(
            "scripts.telemetry.run_recorder.export_to_otel",
            return_value={"status": "success", "job_id": "test"},
        )
        self._otel_patcher.start()

    def tearDown(self):
        self._otel_patcher.stop()

    def _make_input(self, job_id: str) -> dict:
        return {
            "action": "record",
            "state": {
                "job_id": job_id,
                "project_path": "/repos/test",
                "started_at": "2026-08-20T10:00:00Z",
                "model": "sonnet",
                "severity_filter": "all",
                "dry_run": False,
                "phases": {},
                "vulnerabilities": [],
                "fix_results": [],
                "test_results": [],
            },
            "identity": {"user_name": "dev", "repo_name": "test"},
            "ended_at": "2026-08-20T10:01:00Z",
        }

    def test_skips_duplicate_job_id(self):
        """Second call with same job_id should not produce a duplicate record."""
        with tempfile.TemporaryDirectory() as tmpdir:
            runs_file = Path(tmpdir) / "runs.jsonl"
            with patch("scripts.telemetry.run_recorder.RUNS_FILE", runs_file), \
                 patch("scripts.telemetry.run_recorder.TELEMETRY_DIR", Path(tmpdir)):
                input_data = self._make_input("dedup123")

                # First call — should write
                result1 = record_run(input_data)
                self.assertEqual(result1["status"], "success")
                self.assertNotIn("deduplicated", result1)

                # Second call — should skip write
                result2 = record_run(input_data)
                self.assertEqual(result2["status"], "success")
                self.assertTrue(result2.get("deduplicated"))

                # Verify only one record in file
                lines = runs_file.read_text().strip().split("\n")
                self.assertEqual(len(lines), 1)

    def test_dedup_hit_does_not_re_export(self):
        """On a dedup hit, record_run must NOT re-export to OTel — re-exporting
        would push a duplicate (often identity-less/empty) OTLP record to S3."""
        with tempfile.TemporaryDirectory() as tmpdir:
            runs_file = Path(tmpdir) / "runs.jsonl"
            with patch("scripts.telemetry.run_recorder.RUNS_FILE", runs_file), \
                 patch("scripts.telemetry.run_recorder.TELEMETRY_DIR", Path(tmpdir)), \
                 patch("scripts.telemetry.run_recorder.export_to_otel") as mock_export:
                mock_export.return_value = {"status": "success", "job_id": "dedup456"}
                input_data = self._make_input("dedup456")

                record_run(input_data)                 # first: records + exports once
                self.assertEqual(mock_export.call_count, 1)

                result2 = record_run(input_data)        # second: dedup hit
                self.assertTrue(result2.get("deduplicated"))
                # export must NOT be called again on the dedup hit
                self.assertEqual(mock_export.call_count, 1)
                self.assertNotIn("export", result2)

    def test_allows_different_job_ids(self):
        """Different job_ids should both be written."""
        with tempfile.TemporaryDirectory() as tmpdir:
            runs_file = Path(tmpdir) / "runs.jsonl"
            with patch("scripts.telemetry.run_recorder.RUNS_FILE", runs_file), \
                 patch("scripts.telemetry.run_recorder.TELEMETRY_DIR", Path(tmpdir)):
                record_run(self._make_input("aaa11111"))
                record_run(self._make_input("bbb22222"))

                lines = runs_file.read_text().strip().split("\n")
                self.assertEqual(len(lines), 2)


# What the haiku orchestrator actually sent for job 05551011 (PLATENG-9457): invented
# summary keys, no vulnerabilities / fix_results lists, a PR created.
HAIKU_05551011_STATE = {
    "version": 1, "job_id": "05551011",
    "project_path": "/repos/rkycapplicantDetails",
    "started_at": "2026-10-19T15:42:28Z",
    "jira_id": "PLATENG-9457", "model": "haiku", "severity_filter": "all",
    "vulnerabilities_found": 57, "vulnerabilities_auto_fixed": 46,
    "vulnerabilities_manual_review": 11, "packages_remediated": 5,
    "pr_url": "https://gitlab/merge_requests/62",
    "phases": {"1": {"status": "completed"}, "2": {"status": "completed"},
               "3": {"status": "completed"}, "4": {"status": "completed"},
               "5": {"status": "skipped"}, "6": {"status": "skipped"},
               "7": {"status": "completed"}, "8": {"status": "completed"},
               "9": {"status": "completed"}},
}


class TestStateFileResolution(TestCase):
    """record_run takes its counts from the state file, not the pasted state."""

    def setUp(self):
        self._otel_patcher = patch(
            "scripts.telemetry.run_recorder.export_to_otel",
            return_value={"status": "success", "job_id": "test"},
        )
        self._otel_patcher.start()
        self.addCleanup(self._otel_patcher.stop)
        self.tmpdir = Path(tempfile.mkdtemp())
        runs_file = self.tmpdir / "runs.jsonl"
        for target, value in (("RUNS_FILE", runs_file), ("TELEMETRY_DIR", self.tmpdir)):
            patcher = patch(f"scripts.telemetry.run_recorder.{target}", value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.runs_file = runs_file

    def _write_state_file(self, project: Path, n_vulns: int, n_fixes: int) -> Path:
        from scripts.state.pipeline_state import init_state
        out = init_state({"project_path": str(project), "model": "haiku"})
        state = out["state"]
        state["job_id"] = "05551011"
        state["vulnerabilities"] = [
            {"id": f"v{i}", "severity": "high", "remediation_type": "dependency"}
            for i in range(n_vulns)
        ]
        state["fix_results"] = [
            {"vulnerability_id": f"v{i}", "status": "success"} for i in range(n_fixes)
        ]
        state["phases"].update({str(p): {"status": "completed"} for p in (1, 2, 3, 4)})
        path = Path(out["state_path"])
        path.write_text(json.dumps(state))
        return path

    def _last_record(self) -> dict:
        return json.loads(self.runs_file.read_text().strip().split("\n")[-1])

    def test_haiku_payload_without_state_file_is_flagged(self):
        result = record_run({"action": "record", "state": HAIKU_05551011_STATE,
                             "identity": {}, "ended_at": "2026-10-19T15:49:36+00:00"})
        record = self._last_record()
        self.assertEqual(record["vulns_total"], 0)
        self.assertIn(FLAG_STATE_INCOMPLETE, record["flags_raised"])
        self.assertIn(FLAG_STATE_FILE_MISSING, record["flags_raised"])
        self.assertEqual(result["telemetry_message"], "⚠️  Exported to Observe (incomplete counts)")

    def test_haiku_payload_with_state_file_gets_real_counts(self):
        project = self.tmpdir / "rkycapplicantDetails"
        self._write_state_file(project, n_vulns=57, n_fixes=46)
        pasted = {**HAIKU_05551011_STATE, "project_path": str(project)}

        result = record_run({"action": "record", "state": pasted,
                             "identity": {}, "ended_at": "2026-10-19T15:49:36+00:00"})
        record = self._last_record()
        self.assertEqual(record["vulns_total"], 57)
        self.assertEqual(record["fixes_attempted"], 46)
        self.assertEqual(record["vulns_deferred"], 11)
        self.assertEqual(record["cwes_targeted"], ["CWE-937"])
        # pasted fields the file left empty still come through
        self.assertEqual(record["pr_url"], "https://gitlab/merge_requests/62")
        self.assertEqual(record["phases"]["5"]["status"], "skipped")
        self.assertEqual(record["flags_raised"], [])
        self.assertEqual(result["telemetry_message"], "✅ Exported to Observe")

    def test_explicit_state_path_without_pasted_state(self):
        path = self._write_state_file(self.tmpdir / "repo", n_vulns=3, n_fixes=2)
        record_run({"action": "record", "state_path": str(path), "identity": {}})
        record = self._last_record()
        self.assertEqual((record["job_id"], record["vulns_total"], record["fixes_attempted"]),
                         ("05551011", 3, 2))

    def test_state_file_from_another_job_is_ignored(self):
        project = self.tmpdir / "repo"
        self._write_state_file(project, n_vulns=57, n_fixes=46)  # job 05551011
        result = record_run({"action": "record", "identity": {},
                             "state": {"job_id": "newjob01", "project_path": str(project)}})
        record = self._last_record()
        self.assertEqual(result["job_id"], "newjob01")
        self.assertEqual(record["vulns_total"], 0)
        self.assertIn(FLAG_STATE_FILE_MISSING, record["flags_raised"])

    def test_top_level_job_id_rejects_other_runs_file(self):
        path = self._write_state_file(self.tmpdir / "repo", n_vulns=57, n_fixes=46)  # job 05551011
        record_run({"action": "record", "job_id": "newjob02", "state_path": str(path),
                    "identity": {}})
        record = self._last_record()
        self.assertEqual((record["vulns_total"], record["job_id"]), (0, "unknown"))
        self.assertIn(FLAG_STATE_FILE_MISSING, record["flags_raised"])

    def test_clean_run_with_no_findings_is_not_flagged(self):
        self._write_state_file(self.tmpdir / "clean", n_vulns=0, n_fixes=0)
        record_run({"action": "record", "state": {"project_path": str(self.tmpdir / "clean")},
                    "identity": {}})
        self.assertEqual(self._last_record()["flags_raised"], [])


class TestMergeState(TestCase):
    def test_file_wins_and_pasted_fills_gaps(self):
        file_state = {"job_id": "file", "vulnerabilities": [{"id": "v1"}], "pr_url": None,
                      "phases": {"4": {"status": "completed"}, "9": {"status": "pending"}}}
        pasted = {"job_id": "pasted", "vulnerabilities": [], "pr_url": "https://mr/1",
                  "phases": {"4": {"status": "failed"}, "9": {"status": "completed"}}}
        merged = merge_state(file_state, pasted)
        self.assertEqual(merged["job_id"], "file")
        self.assertEqual(merged["vulnerabilities"], [{"id": "v1"}])
        self.assertEqual(merged["pr_url"], "https://mr/1")
        self.assertEqual(merged["phases"]["4"]["status"], "completed")
        self.assertEqual(merged["phases"]["9"]["status"], "completed")


class TestBuildTelemetryMessage(TestCase):
    """Tests for the _build_telemetry_message helper."""

    def test_incomplete_counts_never_green(self):
        msg = _build_telemetry_message("success", {"status": "success"}, incomplete=True)
        self.assertEqual(msg, "⚠️  Exported to Observe (incomplete counts)")

    def test_otel_success(self):
        msg = _build_telemetry_message("success", {"status": "success"})
        self.assertEqual(msg, "✅ Exported to Observe")

    def test_otel_export_failed(self):
        msg = _build_telemetry_message("success", {"status": "error", "error": "connection refused"})
        self.assertEqual(msg, "⚠️  Saved locally (Observe export failed)")

    def test_no_sync_result(self):
        msg = _build_telemetry_message("success", None)
        self.assertEqual(msg, "⚠️  Saved locally")

    def test_local_write_failed(self):
        msg = _build_telemetry_message("error", None)
        self.assertEqual(msg, "⚠️  Local write failed — telemetry not recorded")


class TestExportToOtelEvents(TestCase):
    """export_to_otel must send the run summary AND its events in ONE batch at run end."""

    def _run_record(self, job_id="a1b2c3d4"):
        return {"job_id": job_id, "status": "completed"}

    def test_exports_run_and_events_in_one_batch(self):
        events = [{"Attributes": {"detox.job_id": "a1b2c3d4"}}, {"Attributes": {"detox.job_id": "a1b2c3d4"}}]
        with patch("scripts.telemetry.otel_exporter.export_run_and_events",
                   return_value={"status": "success", "exported_count": 3, "job_id": "a1b2c3d4",
                                 "events_export": {"status": "success", "exported_count": 2}}) as m_all, \
             patch("scripts.telemetry.telemetry.read_events_for_job", return_value=events) as m_read:
            result = export_to_otel(self._run_record())
            m_read.assert_called_once_with("a1b2c3d4")
            # Called once with the run record + its events (single batch send).
            m_all.assert_called_once()
            self.assertEqual(m_all.call_args.args[0], self._run_record())
            self.assertEqual(m_all.call_args.args[1], events)
            self.assertEqual(result["events_export"]["exported_count"], 2)

    def test_no_events_still_sends_run(self):
        with patch("scripts.telemetry.otel_exporter.export_run_and_events",
                   return_value={"status": "success", "exported_count": 1, "job_id": "a1b2c3d4"}) as m_all, \
             patch("scripts.telemetry.telemetry.read_events_for_job", return_value=[]):
            result = export_to_otel(self._run_record())
            m_all.assert_called_once()
            self.assertEqual(m_all.call_args.args[1], [])  # empty events list
            self.assertEqual(result["exported_count"], 1)

    def test_unknown_job_id_skips_event_read(self):
        with patch("scripts.telemetry.otel_exporter.export_run_and_events",
                   return_value={"status": "success", "exported_count": 1, "job_id": "unknown"}) as m_all, \
             patch("scripts.telemetry.telemetry.read_events_for_job") as m_read:
            export_to_otel(self._run_record(job_id="unknown"))
            m_read.assert_not_called()
            m_all.assert_called_once()
            self.assertEqual(m_all.call_args.args[1], [])  # no events read for unknown job

    def test_event_read_failure_is_non_fatal(self):
        # read_events_for_job raising must not raise out of export_to_otel.
        with patch("scripts.telemetry.telemetry.read_events_for_job", side_effect=RuntimeError("boom")):
            result = export_to_otel(self._run_record())
            self.assertIsNone(result)  # swallowed, returns None, never raises


class TestTelemetryStatusMessageWithEvents(TestCase):
    """_telemetry_status_message should surface the event count when events were exported."""

    def test_success_with_events(self):
        msg = _telemetry_status_message({
            "status": "success", "job_id": "a1b2c3d4",
            "events_export": {"status": "success", "exported_count": 5},
        })
        self.assertEqual(msg, "📊 Telemetry exported to Observe (a1b2c3d4, 5 events)")

    def test_success_without_events_unchanged(self):
        msg = _telemetry_status_message({"status": "success", "job_id": "a1b2c3d4"})
        self.assertEqual(msg, "📊 Telemetry exported to Observe (a1b2c3d4)")

    def test_success_with_failed_event_export_omits_count(self):
        msg = _telemetry_status_message({
            "status": "success", "job_id": "a1b2c3d4",
            "events_export": {"status": "error", "error": "x"},
        })
        self.assertEqual(msg, "📊 Telemetry exported to Observe (a1b2c3d4)")


def _report(job_id: str, telemetry: str = REPORT_TELEMETRY_PENDING) -> str:
    return (
        "# DETOX CWE Remediation Report\n\n"
        "**Project:** svc\n"
        "**Detox Version:** 2.6.2\n"
        f"**Telemetry:** {telemetry}\n"
        "**Threat Model:** N/A\n\n---\n\nbody\n\n---\n\n"
        "*Generated by Detox CWE Remediation Pipeline*\n"
        f"*Job ID: {job_id} | Threat Model: tm.md (3 attack paths, 2 CWEs)*\n"
    )


class TestBackfillReportTelemetry(TestCase):
    """Deterministic replacement of the report's pending Telemetry line."""

    def _write(self, tmpdir, text):
        p = Path(tmpdir) / "DETOX-REMEDIATION-REPORT.md"
        p.write_text(text, encoding="utf-8")
        return p

    def test_replaces_pending_line(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = self._write(tmpdir, _report("abc12345"))
            res = backfill_report_telemetry(str(p), "abc12345", "✅ Exported to Observe")
            self.assertEqual(res, {"updated": True, "reason": "updated"})
            text = p.read_text(encoding="utf-8")
            self.assertIn("**Telemetry:** ✅ Exported to Observe\n", text)
            self.assertNotIn(REPORT_TELEMETRY_PENDING, text)
            # Only the Telemetry line changed
            self.assertIn("**Threat Model:** N/A", text)
            self.assertIn("*Job ID: abc12345 |", text)

    def test_warning_message_written(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = self._write(tmpdir, _report("abc12345"))
            backfill_report_telemetry(str(p), "abc12345", "⚠️  Saved locally (Observe export failed)")
            self.assertIn("**Telemetry:** ⚠️  Saved locally (Observe export failed)", p.read_text(encoding="utf-8"))

    def test_stale_report_job_id_mismatch_untouched(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = _report("old00001")
            p = self._write(tmpdir, original)
            res = backfill_report_telemetry(str(p), "new00002", "✅ Exported to Observe")
            self.assertFalse(res["updated"])
            self.assertIn("stale report", res["reason"])
            self.assertEqual(p.read_text(encoding="utf-8"), original)

    def test_no_job_id_in_report_untouched(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = "# Report\n**Telemetry:** pending (recorded at pipeline completion)\n"
            p = self._write(tmpdir, original)
            res = backfill_report_telemetry(str(p), "abc12345", "✅ Exported to Observe")
            self.assertEqual(res, {"updated": False, "reason": "job id not found in report"})
            self.assertEqual(p.read_text(encoding="utf-8"), original)

    def test_missing_report(self):
        res = backfill_report_telemetry("/nonexistent/DETOX-REMEDIATION-REPORT.md", "j", "✅")
        self.assertEqual(res, {"updated": False, "reason": "report not found"})

    def test_no_report_path(self):
        self.assertEqual(backfill_report_telemetry(None, "j", "✅"),
                         {"updated": False, "reason": "no report_path"})

    def test_missing_telemetry_line(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = self._write(tmpdir, "# Report\n*Job ID: abc12345 | x*\n")
            res = backfill_report_telemetry(str(p), "abc12345", "✅")
            self.assertEqual(res, {"updated": False, "reason": "telemetry line not found"})

    def test_only_if_pending_keeps_resolved_outcome(self):
        # Dedup call must not overwrite the authoritative first result.
        with tempfile.TemporaryDirectory() as tmpdir:
            p = self._write(tmpdir, _report("abc12345", telemetry="✅ Exported to Observe"))
            res = backfill_report_telemetry(str(p), "abc12345", "✅ Telemetry already recorded (deduplicated)",
                                            only_if_pending=True)
            self.assertEqual(res, {"updated": False, "reason": "already resolved"})
            self.assertIn("**Telemetry:** ✅ Exported to Observe", p.read_text(encoding="utf-8"))

    def test_only_if_pending_fills_pending(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = self._write(tmpdir, _report("abc12345"))
            res = backfill_report_telemetry(str(p), "abc12345", "✅ Telemetry already recorded (deduplicated)",
                                            only_if_pending=True)
            self.assertTrue(res["updated"])


class TestRecordRunBackfillsReport(TestCase):
    """record_run backfills the report from state.report_path end-to-end."""

    def test_record_run_updates_report_from_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report = Path(tmpdir) / "DETOX-REMEDIATION-REPORT.md"
            report.write_text(_report("job00042"), encoding="utf-8")
            runs_file = Path(tmpdir) / "runs.jsonl"
            with patch("scripts.telemetry.run_recorder.RUNS_FILE", runs_file), \
                 patch("scripts.telemetry.run_recorder.TELEMETRY_DIR", Path(tmpdir)), \
                 patch("scripts.telemetry.run_recorder.export_to_otel", return_value={"status": "error", "error": "x"}):
                result = record_run({
                    "action": "record",
                    "state": {"job_id": "job00042", "status": "completed", "report_path": str(report)},
                    "identity": {},
                    "ended_at": "2026-10-19T12:00:00Z",
                })
            self.assertEqual(result["telemetry_message"], "⚠️  Saved locally (Observe export failed)")
            self.assertEqual(result["report_telemetry"], {"updated": True, "reason": "updated"})
            self.assertIn("**Telemetry:** ⚠️  Saved locally (Observe export failed)",
                          report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
