"""Tests for telemetry.py — core telemetry collector."""

import json
import os
import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.telemetry.telemetry import (
    generate_trace_id,
    generate_span_id,
    build_event,
    emit_event,
    query_events,
    read_events_for_job,
    summarize_events,
    parse_period,
    TELEMETRY_DIR,
)


class TestGenerateTraceId(TestCase):
    def test_pads_short_job_id(self):
        result = generate_trace_id("a1b2c3d4")
        self.assertEqual(len(result), 32)
        self.assertTrue(result.startswith("a1b2c3d4"))
        self.assertTrue(result.endswith("0" * 24))

    def test_truncates_long_job_id(self):
        result = generate_trace_id("a" * 64)
        self.assertEqual(len(result), 32)
        self.assertEqual(result, "a" * 32)

    def test_handles_empty_job_id(self):
        result = generate_trace_id("")
        self.assertEqual(len(result), 32)
        self.assertEqual(result, "0" * 32)


class TestGenerateSpanId(TestCase):
    def test_produces_16_chars(self):
        result = generate_span_id("abc123", phase=1)
        self.assertEqual(len(result), 16)

    def test_different_phases_different_spans(self):
        span1 = generate_span_id("abc123", phase=1)
        span2 = generate_span_id("abc123", phase=2)
        self.assertNotEqual(span1, span2)

    def test_same_input_same_output(self):
        span1 = generate_span_id("abc123", phase=3)
        span2 = generate_span_id("abc123", phase=3)
        self.assertEqual(span1, span2)

    def test_no_phase_uses_root(self):
        result = generate_span_id("abc123")
        self.assertEqual(len(result), 16)


class TestBuildEvent(TestCase):
    def test_creates_valid_event_structure(self):
        event = build_event({
            "event_type": "pipeline.started",
            "job_id": "abc12345",
            "phase": 1,
            "severity": "INFO",
        })
        self.assertIn("Timestamp", event)
        self.assertEqual(event["SeverityText"], "INFO")
        self.assertEqual(event["SeverityNumber"], 9)
        self.assertEqual(event["Resource"]["service.name"], "detox")
        self.assertEqual(event["Attributes"]["detox.event_type"], "pipeline.started")
        self.assertEqual(event["Attributes"]["detox.job_id"], "abc12345")
        self.assertEqual(event["Attributes"]["detox.phase"], 1)
        self.assertEqual(len(event["TraceId"]), 32)
        self.assertEqual(len(event["SpanId"]), 16)

    def test_maps_severity_correctly(self):
        event = build_event({"event_type": "error.occurred", "job_id": "x", "severity": "ERROR"})
        self.assertEqual(event["SeverityText"], "ERROR")
        self.assertEqual(event["SeverityNumber"], 17)

    def test_adds_extra_attributes(self):
        event = build_event({
            "event_type": "fix.applied",
            "job_id": "x",
            "cwe_id": "CWE-79",
            "file_path": "src/app.py",
        })
        self.assertEqual(event["Attributes"]["detox.cwe_id"], "CWE-79")
        self.assertEqual(event["Attributes"]["detox.file_path"], "src/app.py")

    def test_detects_ci_environment(self):
        with patch.dict(os.environ, {"CI": "true"}):
            event = build_event({"event_type": "test", "job_id": "x"})
            self.assertEqual(event["Resource"]["deployment.environment"], "ci")

    def test_local_environment_when_no_ci(self):
        env = {k: "" for k in ("CI", "CI_JOB_ID", "BUILD_NUMBER", "GITHUB_ACTIONS")}
        with patch.dict(os.environ, env, clear=False):
            event = build_event({"event_type": "test", "job_id": "x"})
            self.assertEqual(event["Resource"]["deployment.environment"], "local")


class TestEmitEvent(TestCase):
    def test_appends_to_jsonl_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            events_file = Path(tmpdir) / "events.jsonl"
            with patch("scripts.telemetry.telemetry.EVENTS_FILE", events_file), \
                 patch("scripts.telemetry.telemetry.TELEMETRY_DIR", Path(tmpdir)):
                result = emit_event({"event": {
                    "event_type": "pipeline.started",
                    "job_id": "test123",
                }})
                self.assertEqual(result["status"], "success")
                self.assertIn("event_id", result)

                # Verify file content
                lines = events_file.read_text().strip().split("\n")
                self.assertEqual(len(lines), 1)
                event = json.loads(lines[0])
                self.assertEqual(event["Attributes"]["detox.event_type"], "pipeline.started")

    def test_handles_missing_event_data(self):
        """Should error when event dict is empty."""
        captured = StringIO()
        with self.assertRaises(SystemExit):
            with patch("sys.stdout", captured):
                emit_event({"event": {}})

    def test_handles_write_error_gracefully(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            events_file = Path(tmpdir) / "readonly" / "events.jsonl"
            with patch("scripts.telemetry.telemetry.EVENTS_FILE", events_file), \
                 patch("scripts.telemetry.telemetry.TELEMETRY_DIR", Path(tmpdir)):
                # Make directory read-only so write fails
                readonly_dir = Path(tmpdir) / "readonly"
                readonly_dir.mkdir()
                readonly_dir.chmod(0o444)
                try:
                    result = emit_event({"event": {
                        "event_type": "test",
                        "job_id": "x",
                    }})
                    self.assertEqual(result["status"], "error")
                finally:
                    readonly_dir.chmod(0o755)


class TestReadEventsForJob(TestCase):
    """read_events_for_job filters events.jsonl by Attributes.detox.job_id."""

    def _write_events(self, path, rows):
        with open(path, "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")

    def test_returns_only_matching_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            ev = Path(tmp) / "events.jsonl"
            self._write_events(ev, [
                {"Body": "a", "Attributes": {"detox.job_id": "aaa11111"}},
                {"Body": "b", "Attributes": {"detox.job_id": "bbb22222"}},
                {"Body": "c", "Attributes": {"detox.job_id": "aaa11111"}},
            ])
            with patch("scripts.telemetry.telemetry.EVENTS_FILE", ev):
                result = read_events_for_job("aaa11111")
            self.assertEqual(len(result), 2)
            self.assertTrue(all(e["Attributes"]["detox.job_id"] == "aaa11111" for e in result))

    def test_no_match_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            ev = Path(tmp) / "events.jsonl"
            self._write_events(ev, [{"Body": "a", "Attributes": {"detox.job_id": "aaa11111"}}])
            with patch("scripts.telemetry.telemetry.EVENTS_FILE", ev):
                self.assertEqual(read_events_for_job("zzz99999"), [])

    def test_handles_missing_attributes(self):
        with tempfile.TemporaryDirectory() as tmp:
            ev = Path(tmp) / "events.jsonl"
            self._write_events(ev, [{"Body": "a"}, {"Body": "b", "Attributes": {}}])
            with patch("scripts.telemetry.telemetry.EVENTS_FILE", ev):
                self.assertEqual(read_events_for_job("aaa11111"), [])

    def test_empty_job_id_returns_empty(self):
        self.assertEqual(read_events_for_job(""), [])


class TestQueryEvents(TestCase):
    def test_filters_by_event_type(self):
        fixture_path = Path(__file__).parent / "fixtures" / "sample_events.jsonl"
        with patch("scripts.telemetry.telemetry.EVENTS_FILE", fixture_path):
            result = query_events({
                "filters": {"event_type": "pipeline.started"},
                "limit": 100,
            })
            self.assertEqual(result["status"], "success")
            self.assertGreater(result["count"], 0)
            for event in result["events"]:
                self.assertEqual(event["Attributes"]["detox.event_type"], "pipeline.started")

    def test_filters_by_user(self):
        fixture_path = Path(__file__).parent / "fixtures" / "sample_events.jsonl"
        with patch("scripts.telemetry.telemetry.EVENTS_FILE", fixture_path):
            result = query_events({
                "filters": {"user_name": "shilpa.d"},
                "limit": 100,
            })
            self.assertEqual(result["status"], "success")
            for event in result["events"]:
                self.assertEqual(event["Attributes"]["detox.user.name"], "shilpa.d")

    def test_respects_limit(self):
        fixture_path = Path(__file__).parent / "fixtures" / "sample_events.jsonl"
        with patch("scripts.telemetry.telemetry.EVENTS_FILE", fixture_path):
            result = query_events({"filters": {}, "limit": 2})
            self.assertLessEqual(result["count"], 2)

    def test_returns_empty_when_no_file(self):
        with patch("scripts.telemetry.telemetry.EVENTS_FILE", Path("/nonexistent/events.jsonl")):
            result = query_events({"filters": {}, "limit": 10})
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["count"], 0)


class TestSummarizeEvents(TestCase):
    def test_summarizes_fixture_data(self):
        fixture_path = Path(__file__).parent / "fixtures" / "sample_events.jsonl"
        with patch("scripts.telemetry.telemetry.EVENTS_FILE", fixture_path):
            result = summarize_events({"period": "all"})
            self.assertEqual(result["status"], "success")
            summary = result["summary"]
            self.assertGreater(summary["total_events"], 0)
            self.assertIn("by_event_type", summary)
            self.assertIn("pipeline.started", summary["by_event_type"])

    def test_group_by_user(self):
        fixture_path = Path(__file__).parent / "fixtures" / "sample_events.jsonl"
        with patch("scripts.telemetry.telemetry.EVENTS_FILE", fixture_path):
            result = summarize_events({"period": "all", "group_by": "user"})
            summary = result["summary"]
            self.assertIn("by_user", summary)
            self.assertIn("deveshkumar", summary["by_user"])


class TestParsePeriod(TestCase):
    def test_parses_7d(self):
        from datetime import datetime, timezone
        result = parse_period("7d")
        now = datetime.now(timezone.utc)
        diff = now - result
        self.assertAlmostEqual(diff.days, 7, delta=1)

    def test_parses_30d(self):
        from datetime import datetime, timezone
        result = parse_period("30d")
        now = datetime.now(timezone.utc)
        diff = now - result
        self.assertAlmostEqual(diff.days, 30, delta=1)

    def test_all_returns_min_date(self):
        from datetime import datetime
        result = parse_period("all")
        self.assertEqual(result, datetime.min.replace(tzinfo=result.tzinfo))


if __name__ == "__main__":
    main()
