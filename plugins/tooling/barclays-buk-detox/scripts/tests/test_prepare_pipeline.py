"""Tests for prepare_pipeline.py."""

import json
import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import scripts.prepare_pipeline as pp
from scripts.prepare_pipeline import _run_script, main as prepare_main


class TestRunScript(TestCase):
    def test_returns_parsed_json(self):
        fake_result = MagicMock()
        fake_result.stdout = '{"status": "success", "data": 42}'
        fake_result.stderr = ""
        fake_result.returncode = 0

        with patch("scripts.prepare_pipeline.subprocess.run", return_value=fake_result):
            result = _run_script("validators/preflight_check.py", {"key": "val"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"], 42)

    def test_error_on_empty_stdout(self):
        fake_result = MagicMock()
        fake_result.stdout = ""
        fake_result.stderr = "some error"
        fake_result.returncode = 1

        with patch("scripts.prepare_pipeline.subprocess.run", return_value=fake_result):
            with self.assertRaises(SystemExit):
                _run_script("validators/preflight_check.py", {})

    def test_error_on_invalid_json(self):
        fake_result = MagicMock()
        fake_result.stdout = "not json at all"
        fake_result.stderr = ""
        fake_result.returncode = 0

        with patch("scripts.prepare_pipeline.subprocess.run", return_value=fake_result):
            with self.assertRaises(SystemExit):
                _run_script("validators/preflight_check.py", {})

    def test_error_on_missing_script(self):
        with self.assertRaises(SystemExit):
            _run_script("nonexistent/script.py", {})


class TestPreparePipelineProgress(TestCase):
    """Verify that prepare_pipeline writes progress to stderr."""

    def setUp(self):
        # Redirect the state file away from the fake clone_dir (/tmp/repo).
        self.tmpdir = Path(tempfile.mkdtemp())
        self.state_file = self.tmpdir / "state.json"
        patcher = patch("scripts.state.pipeline_state.default_state_path",
                        return_value=self.state_file)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _make_run_script_side_effect(self, responses):
        """Create a side effect function that returns responses in order."""
        call_count = [0]
        def side_effect(rel_path, input_data, timeout=120):
            idx = min(call_count[0], len(responses) - 1)
            call_count[0] += 1
            return responses[idx]
        return side_effect

    def test_progress_output_stages_0_through_3(self):
        preflight_ok = {
            "status": "success",
            "tools": {
                "git": {"found": True, "version": "2.45.0"},
                "semgrep": {"found": True, "version": "1.96.0"},
            },
        }
        repo_ok = {
            "status": "success",
            "clone_dir": "/tmp/repo",
            "branch_name": "remediate-cwe-79-20260904",
            "base_branch": "main",
        }
        parse_ok = {
            "status": "success",
            "vulnerabilities": [{"id": "v1"}, {"id": "v2"}],
        }
        dedup_ok = {
            "status": "success",
            "vulnerabilities": [{"id": "v1"}],
        }
        classify_ok = {
            "status": "success",
            "categories": {
                "code_fix": [{"id": "v1"}],
                "dependency": [],
                "hybrid": [],
                "infra_config": [],
                "manual": [],
            },
            "filtered_out_count": 0,
        }

        responses = [preflight_ok, repo_ok, parse_ok, dedup_ok, classify_ok]

        input_json = json.dumps({
            "project_path": "/tmp/repo",
            "sast_report_path": "/tmp/wiz.json",
            "severity_filter": "all",
        })

        stderr_capture = StringIO()
        stdout_capture = StringIO()

        with patch("scripts.prepare_pipeline._run_script", side_effect=self._make_run_script_side_effect(responses)):
            with patch("sys.stdin", StringIO(input_json)):
                with patch("sys.stderr", stderr_capture):
                    with patch("sys.stdout", stdout_capture):
                        prepare_main()

        stderr_output = stderr_capture.getvalue()
        self.assertIn("Stage 0/9", stderr_output)
        self.assertIn("Preflight passed", stderr_output)
        self.assertIn("Stage 1/9", stderr_output)
        self.assertIn("Repository ready", stderr_output)
        self.assertIn("Stage 2/9", stderr_output)
        self.assertIn("Wiz report", stderr_output)
        self.assertIn("Stage 3/9", stderr_output)

        stdout_output = stdout_capture.getvalue()
        result = json.loads(stdout_output)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["branch_name"], "remediate-cwe-79-20260904")

    def test_threat_model_flagged_as_pending(self):
        preflight_ok = {"status": "success", "tools": {}}
        repo_ok = {
            "status": "success",
            "clone_dir": "/tmp/repo",
            "branch_name": "remediate-test",
            "base_branch": "main",
        }
        classify_ok = {
            "status": "success",
            "categories": {"code_fix": [], "dependency": [], "hybrid": [], "infra_config": [], "manual": []},
            "filtered_out_count": 0,
        }

        responses = [preflight_ok, repo_ok, classify_ok]

        input_json = json.dumps({
            "project_path": "/tmp/repo",
            "threat_model_path": "/tmp/threat.md",
            "severity_filter": "all",
        })

        stderr_capture = StringIO()
        stdout_capture = StringIO()

        with patch("scripts.prepare_pipeline._run_script", side_effect=self._make_run_script_side_effect(responses)):
            with patch("sys.stdin", StringIO(input_json)):
                with patch("sys.stderr", stderr_capture):
                    with patch("sys.stdout", stdout_capture):
                        prepare_main()

        result = json.loads(stdout_capture.getvalue())
        self.assertTrue(result["threat_model_pending"])
        self.assertIn("deferred", stderr_capture.getvalue().lower())

    def test_state_file_holds_findings_and_phases(self):
        """Counts must live in the state file, not depend on the orchestrator copying them."""
        from scripts.telemetry import telemetry

        preflight_ok = {"status": "success", "tools": {}}
        repo_ok = {"status": "success", "clone_dir": "/tmp/repo",
                   "branch_name": "dev/x", "base_branch": "main"}
        jdk_ok = {"status": "success", "jdk_version": None, "is_java_project": False}
        vulns = [
            {"id": "v1", "severity": "high", "remediation_type": "code_fix"},
            {"id": "v2", "severity": "low", "remediation_type": "manual"},
            {"id": "v3", "severity": "critical", "remediation_type": "infra_config"},
        ]
        parse_ok = {"status": "success", "vulnerabilities": vulns}
        dedup_ok = {"status": "success", "vulnerabilities": vulns}
        classify_ok = {"status": "success", "code_fix": [vulns[0]], "hybrid": [],
                       "infra_config": [vulns[2]], "dependency": [], "manual": [vulns[1]],
                       "filtered_out": []}
        responses = [preflight_ok, repo_ok, jdk_ok, parse_ok, dedup_ok, classify_ok]

        input_json = json.dumps({"project_path": "/tmp/repo", "sast_report_path": "/tmp/wiz.json",
                                 "severity_filter": "all", "model": "haiku", "jira_id": "PROJ-1"})
        stdout_capture = StringIO()
        with patch("scripts.prepare_pipeline._run_script",
                   side_effect=self._make_run_script_side_effect(responses)), \
             patch("sys.stdin", StringIO(input_json)), \
             patch("sys.stderr", StringIO()), \
             patch("sys.stdout", stdout_capture):
            prepare_main()

        result = json.loads(stdout_capture.getvalue())
        self.assertEqual(result["state_path"], str(self.state_file))
        state = json.loads(self.state_file.read_text())
        self.assertEqual(state["job_id"], result["job_id"])
        self.assertEqual([v["id"] for v in state["vulnerabilities"]], ["v1", "v2", "v3"])
        self.assertEqual([v["id"] for v in state["manual_findings"]], ["v2"])
        self.assertEqual([v["id"] for v in state["infra_findings"]], ["v3"])
        self.assertEqual((state["model"], state["jira_id"], state["branch_name"]),
                         ("haiku", "PROJ-1", "dev/x"))
        for phase in ("1", "2", "3"):
            self.assertEqual(state["phases"][phase]["status"], "completed")
            self.assertIn("ended_at", state["phases"][phase])
        self.assertEqual(state["phases"]["4"]["status"], "pending")

        events = [json.loads(line) for line in telemetry.EVENTS_FILE.read_text().splitlines()]
        self.assertEqual([e["Attributes"]["detox.phase"] for e in events], ["1", "2", "3"])
        self.assertTrue(all(e["Attributes"]["detox.job_id"] == result["job_id"] for e in events))

    def test_preflight_failure_exits(self):
        preflight_fail = {
            "status": "missing_tools",
            "missing": ["semgrep"],
        }

        input_json = json.dumps({"project_path": "/tmp/repo", "severity_filter": "all"})

        with patch("scripts.prepare_pipeline._run_script", return_value=preflight_fail):
            with patch("sys.stdin", StringIO(input_json)):
                with self.assertRaises(SystemExit):
                    prepare_main()


def _run_prepare(dep_count):
    """Run prepare_pipeline.main with stage stubs; return (captured calls, stderr)."""
    deps = [{"id": f"v{i}", "affected_package": "com.google.code.gson:gson:2.8.9"} for i in range(dep_count)]
    calls = {}

    def fake(rel, data, timeout=300):
        calls[rel] = data
        return {
            "validators/preflight_check.py": {"status": "success", "tools": {
                "git": {"available": True, "version": "2.45.0"},
                "semgrep": {"available": True, "version": "1.96.0"}}},
            "git/repo_setup.py": {"status": "success", "clone_dir": "/tmp/r", "branch_name": "b",
                                  "base_branch": "release/1.3.1"},
            "validators/detect_jdk_version.py": {"jdk_version": 8, "is_java_project": True},
            "parsers/parse_wiz_report.py": {"status": "success", "vulnerabilities": deps},
            "parsers/deduplicate_findings.py": {"status": "success", "vulnerabilities": deps},
            "parsers/classify_findings.py": {"status": "success", "categories": {
                "dependency": deps, "code_fix": [], "infra_config": [], "manual": []}},
            "validators/sca_remediation_strategy.py": {"status": "success", "remediation_plan": [],
                                                        "summary": {"auto_apply": 0, "manual": 0}},
        }[rel]

    err = StringIO()
    with patch.object(pp, "_run_script", side_effect=fake), \
         patch("sys.stdin", StringIO(json.dumps({"project_path": "/tmp/r", "sast_report_path": "/dev/null"}))), \
         patch("sys.stdout", StringIO()), patch("sys.stderr", err):
        try:
            pp.main()
        except SystemExit:
            pass
    return calls, err.getvalue()


class TestPreparePipelineFixes(TestCase):
    def test_strategy_runs_for_large_batches(self):  # D2
        calls, _ = _run_prepare(57)
        self.assertIn("validators/sca_remediation_strategy.py", calls)
        self.assertEqual(len(calls["validators/sca_remediation_strategy.py"]["vulnerabilities"]), 57)

    def test_preflight_line_lists_available_tools(self):  # G1
        _, err = _run_prepare(1)
        self.assertIn("Preflight passed — git 2.45.0, semgrep 1.96.0", err)

    def test_base_branch_not_hardcoded(self):  # base_branch
        calls, _ = _run_prepare(1)
        self.assertIsNone(calls["git/repo_setup.py"]["base_branch"])


if __name__ == "__main__":
    main()
