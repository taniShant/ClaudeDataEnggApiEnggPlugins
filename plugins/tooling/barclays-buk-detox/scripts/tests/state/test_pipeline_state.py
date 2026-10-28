"""Tests for pipeline_state.py."""

import json
import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))


def run_state(input_data: dict) -> dict:
    """Helper to run pipeline_state.main() with mocked stdin/stdout."""
    from scripts.state.pipeline_state import main as state_main

    if input_data.get("action") == "init" and "state_path" not in input_data:
        # Keep the state file init writes out of the (fake) project_path.
        input_data = {**input_data, "state_path": str(Path(tempfile.mkdtemp()) / "state.json")}
    stdin_data = json.dumps(input_data)
    captured_output = StringIO()

    with patch("sys.stdin", StringIO(stdin_data)), \
         patch("sys.stdout", captured_output):
        try:
            state_main()
        except SystemExit:
            pass

    return json.loads(captured_output.getvalue())


class TestInitState(TestCase):
    def test_basic_init(self):
        result = run_state({
            "action": "init",
            "project_path": "/tmp/test-repo",
            "model": "opus",
            "severity_filter": "critical+high",
            "jira_id": "PROJ-1234",
        })
        self.assertEqual(result["status"], "success")
        state = result["state"]
        self.assertEqual(state["project_path"], "/tmp/test-repo")
        self.assertEqual(state["model"], "opus")
        self.assertEqual(state["severity_filter"], "critical+high")
        self.assertEqual(state["jira_id"], "PROJ-1234")
        self.assertEqual(len(state["job_id"]), 8)
        self.assertEqual(state["phases"]["1"]["status"], "pending")
        self.assertEqual(state["phases"]["9"]["status"], "pending")

    def test_defaults(self):
        result = run_state({
            "action": "init",
            "project_path": "/tmp/repo",
        })
        state = result["state"]
        self.assertEqual(state["model"], "sonnet")
        self.assertEqual(state["severity_filter"], "all")
        self.assertFalse(state["dry_run"])
        self.assertTrue(state["generate_tests"])
        self.assertEqual(state["test_mode"], "fast")


class TestUpdateState(TestCase):
    def test_update_phase(self):
        # Create temp state file
        fixture = Path(__file__).parent.parent / "fixtures" / "sample_state.json"
        with open(fixture) as f:
            state = json.load(f)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump(state, tmp)
            tmp_path = tmp.name

        try:
            result = run_state({
                "action": "update",
                "state_path": tmp_path,
                "updates": {
                    "phases.4.status": "completed",
                    "branch_name": "new-branch-name",
                },
            })
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["state"]["phases"]["4"]["status"], "completed")
            self.assertEqual(result["state"]["branch_name"], "new-branch-name")

            # Verify file was updated
            with open(tmp_path) as f:
                saved = json.load(f)
            self.assertEqual(saved["phases"]["4"]["status"], "completed")
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestCheckGate(TestCase):
    def test_gate_passes(self):
        fixture = Path(__file__).parent.parent / "fixtures" / "sample_state.json"
        result = run_state({
            "action": "check_gate",
            "state_path": str(fixture),
            "phase": 4,
            "required_phases": [1, 2, 3],
        })
        self.assertEqual(result["status"], "gate_passed")

    def test_gate_fails(self):
        fixture = Path(__file__).parent.parent / "fixtures" / "sample_state.json"
        result = run_state({
            "action": "check_gate",
            "state_path": str(fixture),
            "phase": 5,
            "required_phases": [1, 2, 3, 4],
        })
        self.assertEqual(result["status"], "gate_failed")
        self.assertIn(4, result["failed_prerequisites"])


class TestEmptyFileGuard(TestCase):
    def test_update_on_empty_file_gives_error(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name
            # Write nothing — 0 bytes

        try:
            result = run_state({
                "action": "update",
                "state_path": tmp_path,
                "updates": {"phases.1.status": "completed"},
            })
            self.assertEqual(result["status"], "error")
            self.assertIn("empty", result["error"])
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_check_gate_on_empty_file_gives_error(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = run_state({
                "action": "check_gate",
                "state_path": tmp_path,
                "phase": 2,
                "required_phases": [1],
            })
            self.assertEqual(result["status"], "error")
            self.assertIn("empty", result["error"])
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestDurationMs(TestCase):
    def test_init_includes_duration_ms(self):
        result = run_state({"action": "init", "project_path": "/tmp/repo"})
        self.assertIn("duration_ms", result)
        self.assertIsInstance(result["duration_ms"], int)
        self.assertGreaterEqual(result["duration_ms"], 0)


class TestV2EvidenceFields(TestCase):
    """Test Evidence & Accountability Framework fields added in state v2."""

    def test_init_has_evidence_fields(self):
        result = run_state({"action": "init", "project_path": "/tmp/repo"})
        state = result["state"]
        self.assertEqual(state["version"], 2)
        self.assertEqual(state["evidence_records"], [])
        self.assertIsNone(state["verification_manifest_path"])
        self.assertIsNone(state["wiz_baseline_scan_path"])
        self.assertIsNone(state["wiz_available"])

    def test_update_evidence_records(self):
        fixture = Path(__file__).parent.parent / "fixtures" / "sample_state.json"
        with open(fixture) as f:
            state = json.load(f)
        # Ensure v2 fields exist for the update
        state["evidence_records"] = []
        state["wiz_available"] = None

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump(state, tmp)
            tmp_path = tmp.name

        try:
            result = run_state({
                "action": "update",
                "state_path": tmp_path,
                "updates": {
                    "wiz_available": True,
                    "wiz_baseline_scan_path": "/tmp/baseline.json",
                },
            })
            self.assertEqual(result["status"], "success")
            self.assertTrue(result["state"]["wiz_available"])
            self.assertEqual(result["state"]["wiz_baseline_scan_path"], "/tmp/baseline.json")
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestCheckEvidenceGate(TestCase):
    """Test evidence gate — verifies every successful fix has an evidence record."""

    def _make_state_file(self, fix_results, evidence_records):
        state = {
            "version": 2,
            "fix_results": fix_results,
            "evidence_records": evidence_records,
        }
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(state, tmp)
        tmp.close()
        return tmp.name

    def test_gate_passes_all_evidenced(self):
        path = self._make_state_file(
            [{"vulnerability_id": "v1", "status": "success"}],
            [{"finding_id": "v1"}],
        )
        try:
            result = run_state({
                "action": "check_evidence_gate",
                "state_path": path,
            })
            self.assertEqual(result["status"], "gate_passed")
        finally:
            Path(path).unlink(missing_ok=True)

    def test_gate_fails_missing_evidence(self):
        path = self._make_state_file(
            [
                {"vulnerability_id": "v1", "status": "success"},
                {"vulnerability_id": "v2", "status": "success"},
            ],
            [{"finding_id": "v1"}],  # v2 missing
        )
        try:
            result = run_state({
                "action": "check_evidence_gate",
                "state_path": path,
            })
            self.assertEqual(result["status"], "gate_failed")
            self.assertIn("v2", result["missing_evidence_for"])
        finally:
            Path(path).unlink(missing_ok=True)

    def test_gate_passes_failed_fixes_ignored(self):
        """Failed fixes don't need evidence."""
        path = self._make_state_file(
            [{"vulnerability_id": "v1", "status": "failed"}],
            [],
        )
        try:
            result = run_state({
                "action": "check_evidence_gate",
                "state_path": path,
            })
            self.assertEqual(result["status"], "gate_passed")
        finally:
            Path(path).unlink(missing_ok=True)

    def test_gate_passes_empty_state(self):
        path = self._make_state_file([], [])
        try:
            result = run_state({
                "action": "check_evidence_gate",
                "state_path": path,
            })
            self.assertEqual(result["status"], "gate_passed")
        finally:
            Path(path).unlink(missing_ok=True)



def _read_events(events_file: Path) -> list[dict]:
    if not events_file.exists():
        return []
    return [json.loads(line) for line in events_file.read_text().splitlines() if line.strip()]


class TestStateFile(TestCase):
    """init writes the state file; update/append keep it current; phase changes emit events."""

    def setUp(self):
        from scripts.telemetry import telemetry
        self.tmpdir = Path(tempfile.mkdtemp())
        self.events_file = telemetry.EVENTS_FILE  # redirected per-test by conftest

    def _init(self) -> tuple[dict, Path]:
        result = run_state({"action": "init", "project_path": str(self.tmpdir)})
        return result["state"], Path(result["state_path"])

    def test_init_writes_default_state_path(self):
        from scripts.state.pipeline_state import init_state
        result = init_state({"project_path": str(self.tmpdir)})
        path = self.tmpdir / ".detox" / "state.json"
        self.assertEqual(result["state_path"], str(path))
        self.assertEqual(json.loads(path.read_text())["job_id"], result["state"]["job_id"])

    def test_init_unwritable_path_is_non_fatal(self):
        blocker = self.tmpdir / "not-a-dir"
        blocker.write_text("x")
        result = run_state({"action": "init", "project_path": str(self.tmpdir),
                            "state_path": str(blocker / "state.json")})
        self.assertEqual(result["status"], "success")
        self.assertIsNone(result["state_path"])
        self.assertIn("warning", result)

    def test_append_extends_lists(self):
        _, path = self._init()
        run_state({"action": "append", "state_path": str(path),
                   "items": {"fix_results": [{"vulnerability_id": "v1", "status": "success"}]}})
        result = run_state({"action": "append", "state_path": str(path),
                            "items": {"fix_results": {"vulnerability_id": "v2", "status": "failed"},
                                      "test_results": [{"status": "success"}]}})
        self.assertEqual(result["counts"], {"fix_results": 2, "test_results": 1})
        saved = json.loads(path.read_text())
        self.assertEqual([f["vulnerability_id"] for f in saved["fix_results"]], ["v1", "v2"])

    def test_append_rejects_non_list_field(self):
        _, path = self._init()
        result = run_state({"action": "append", "state_path": str(path),
                            "items": {"job_id": ["x"]}})
        self.assertEqual(result["status"], "error")

    def test_phase_change_emits_event_and_timestamps(self):
        state, path = self._init()
        run_state({"action": "update", "state_path": str(path),
                   "updates": {"phases.4.status": "in_progress"}})
        result = run_state({"action": "update", "state_path": str(path),
                            "updates": {"phases.4.status": "completed",
                                        "phases.5.status": "skipped"}})
        phase4 = result["state"]["phases"]["4"]
        self.assertIn("started_at", phase4)
        self.assertIn("ended_at", phase4)

        events = _read_events(self.events_file)
        types = [(e["Attributes"]["detox.event_type"], e["Attributes"]["detox.phase"]) for e in events]
        self.assertEqual(types, [("phase.started", "4"), ("phase.completed", "4"), ("phase.skipped", "5")])
        self.assertTrue(all(e["Attributes"]["detox.job_id"] == state["job_id"] for e in events))

    def test_unchanged_status_and_other_updates_emit_nothing(self):
        _, path = self._init()
        run_state({"action": "update", "state_path": str(path),
                   "updates": {"phases.1.status": "pending", "pr_url": "https://mr/1"}})
        self.assertEqual(_read_events(self.events_file), [])


if __name__ == "__main__":
    main()
