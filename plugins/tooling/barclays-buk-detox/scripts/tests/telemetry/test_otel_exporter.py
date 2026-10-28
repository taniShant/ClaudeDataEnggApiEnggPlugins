"""Tests for scripts/telemetry/otel_exporter.py — the Observe gRPC adapter.

The exporter is now a thin adapter over plugin_observability.send_to_observe
(strategic Barclays Observe path). These tests mock send_to_observe so they run
with no network and no grpc/opentelemetry deps.
"""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.telemetry.otel_exporter import (
    RUN_EVENT_NAME,
    UNRESOLVED_EVENT_NAME,
    unresolved_vuln_to_batch_item,
    _flatten_value,
    _is_ci,
    run_record_to_attrs,
    run_record_to_batch_item,
    otel_event_to_batch_item,
    export_single,
    export_events,
    export_run_and_events,
)


class TestFlattenValue(unittest.TestCase):

    def test_none_becomes_empty(self):
        self.assertEqual(_flatten_value(None), "")

    def test_bool_true(self):
        self.assertEqual(_flatten_value(True), "true")

    def test_bool_false(self):
        self.assertEqual(_flatten_value(False), "false")

    def test_int(self):
        self.assertEqual(_flatten_value(5), "5")

    def test_float(self):
        self.assertEqual(_flatten_value(0.91), "0.91")

    def test_list_serialized_json(self):
        self.assertEqual(_flatten_value(["CWE-89", "CWE-79"]), '["CWE-89", "CWE-79"]')

    def test_dict_serialized_json(self):
        self.assertEqual(_flatten_value({"fix": 1}), '{"fix": 1}')

    def test_string_passthrough(self):
        self.assertEqual(_flatten_value("remediate"), "remediate")


class TestRunRecordToAttrs(unittest.TestCase):

    def _record(self, **overrides):
        rec = {
            "job_id": "abc12345",
            "command": "remediate",
            "repo_name": "my-repo",
            "status": "completed",
            "fixes_succeeded": 3,
            "dry_run": False,
            "cwes_targeted": ["CWE-89"],
            "phases": {"fix": {"ok": 1}},
        }
        rec.update(overrides)
        return rec

    def test_service_name_is_detox(self):
        attrs = run_record_to_attrs(self._record())
        self.assertEqual(attrs["service.name"], "detox")

    def test_all_values_are_strings(self):
        attrs = run_record_to_attrs(self._record())
        self.assertTrue(all(isinstance(v, str) for v in attrs.values()))

    def test_job_id_preserved(self):
        attrs = run_record_to_attrs(self._record(job_id="deadbeef"))
        self.assertEqual(attrs["detox.job_id"], "deadbeef")

    def test_bool_flattened(self):
        attrs = run_record_to_attrs(self._record(dry_run=True))
        self.assertEqual(attrs["detox.dry_run"], "true")

    def test_list_flattened_to_json(self):
        attrs = run_record_to_attrs(self._record(cwes_targeted=["CWE-89", "CWE-22"]))
        self.assertEqual(attrs["detox.cwes_targeted"], '["CWE-89", "CWE-22"]')

    def test_dict_flattened_to_json(self):
        attrs = run_record_to_attrs(self._record(phases={"scan": {"n": 2}}))
        self.assertEqual(attrs["detox.phases"], '{"scan": {"n": 2}}')

    def test_none_values_dropped(self):
        attrs = run_record_to_attrs(self._record(validation_pass_rate=None, pr_url=None))
        self.assertNotIn("detox.validation_pass_rate", attrs)
        self.assertNotIn("detox.pr_url", attrs)

    def test_unresolved_vulns_inlined_with_count(self):
        vulns = [{"vuln_id": "v1", "cwe_id": "CWE-937", "reason": "No safe version"}]
        attrs = run_record_to_attrs(self._record(unresolved_vulns=vulns))
        self.assertEqual(json.loads(attrs["detox.unresolved_vulns"]), vulns)
        self.assertEqual(attrs["detox.unresolved_vulns_count"], "1")

    def test_unresolved_vulns_default_empty(self):
        attrs = run_record_to_attrs(self._record())
        self.assertEqual(attrs["detox.unresolved_vulns"], "[]")
        self.assertEqual(attrs["detox.unresolved_vulns_count"], "0")

    def test_record_type_tag(self):
        attrs = run_record_to_attrs(self._record())
        self.assertEqual(attrs["detox.record_type"], "pipeline_run")

    def test_cio_from_record_preferred(self):
        attrs = run_record_to_attrs(self._record(cio="DIGITAL"))
        self.assertEqual(attrs["detox.cio"], "DIGITAL")


class TestIsCi(unittest.TestCase):

    def test_local_when_no_ci_vars(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(_is_ci())

    def test_ci_when_gitlab_job(self):
        with patch.dict(os.environ, {"CI_JOB_ID": "123"}, clear=True):
            self.assertTrue(_is_ci())


class TestExportSingle(unittest.TestCase):

    def test_success_calls_send_to_observe(self):
        with patch("scripts.telemetry.plugin_observability.send_to_observe", return_value=True) as mock_send:
            result = export_single({"job_id": "j1", "fixes_succeeded": 4})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["exported_count"], 1)
        self.assertEqual(result["job_id"], "j1")
        # Called with the run event name + a flat attrs dict
        args, kwargs = mock_send.call_args
        self.assertEqual(kwargs["event_name"], RUN_EVENT_NAME)
        self.assertEqual(kwargs["value"], "4")  # fixes_succeeded as the primary value
        self.assertEqual(kwargs["extra_attrs"]["service.name"], "detox")
        self.assertEqual(kwargs["extra_attrs"]["detox.job_id"], "j1")

    def test_false_return_is_error_status(self):
        with patch("scripts.telemetry.plugin_observability.send_to_observe", return_value=False):
            result = export_single({"job_id": "j2"})
        self.assertEqual(result["status"], "error")
        self.assertIn("send_to_observe", result["error"])

    def test_exception_is_caught_never_raises(self):
        with patch("scripts.telemetry.plugin_observability.send_to_observe", side_effect=RuntimeError("boom")):
            result = export_single({"job_id": "j3"})
        self.assertEqual(result["status"], "error")
        self.assertIn("boom", result["error"])

    def test_value_defaults_to_zero(self):
        with patch("scripts.telemetry.plugin_observability.send_to_observe", return_value=True) as mock_send:
            export_single({"job_id": "j4"})
        self.assertEqual(mock_send.call_args.kwargs["value"], "0")


class TestOtelEventToBatchItem(unittest.TestCase):

    def test_maps_event_type_to_name(self):
        item = otel_event_to_batch_item({"Attributes": {"detox.event_type": "fix_applied", "detox.job_id": "j1"}})
        self.assertEqual(item["event_name"], "detox.fix_applied")

    def test_default_event_name_when_type_missing(self):
        item = otel_event_to_batch_item({"Attributes": {}})
        self.assertEqual(item["event_name"], "detox.event")

    def test_attributes_flattened_as_labels(self):
        item = otel_event_to_batch_item({"Attributes": {"detox.phase": "scan", "detox.n": 3}})
        self.assertEqual(item["extra_attrs"]["detox.phase"], "scan")
        self.assertEqual(item["extra_attrs"]["detox.n"], "3")

    def test_severity_and_body_surfaced(self):
        item = otel_event_to_batch_item({"SeverityText": "WARN", "Body": "oops", "Attributes": {}})
        self.assertEqual(item["extra_attrs"]["severity"], "WARN")
        self.assertEqual(item["extra_attrs"]["event.body"], "oops")


class TestRunRecordToBatchItem(unittest.TestCase):

    def test_run_event_name_and_value(self):
        item = run_record_to_batch_item({"job_id": "j1", "fixes_succeeded": 7})
        self.assertEqual(item["event_name"], RUN_EVENT_NAME)
        self.assertEqual(item["value"], "7")
        self.assertEqual(item["extra_attrs"]["service.name"], "detox")


class TestExportEvents(unittest.TestCase):

    def test_empty_is_success_noop(self):
        self.assertEqual(export_events([]), {"status": "success", "exported_count": 0})

    def test_batches_all_events(self):
        events = [{"Attributes": {"detox.event_type": "a"}}, {"Attributes": {"detox.event_type": "b"}}]
        with patch("scripts.telemetry.observe_batch.send_many_to_observe", return_value=True) as m:
            result = export_events(events)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["exported_count"], 2)
        self.assertEqual(len(m.call_args.args[0]), 2)

    def test_false_return_is_error(self):
        with patch("scripts.telemetry.observe_batch.send_many_to_observe", return_value=False):
            result = export_events([{"Attributes": {"detox.event_type": "a"}}])
        self.assertEqual(result["status"], "error")


class TestExportRunAndEvents(unittest.TestCase):
    """The end-of-run path: run summary + all events in ONE batch / one gRPC send."""

    def test_single_batch_contains_run_plus_events(self):
        events = [{"Attributes": {"detox.event_type": "phase_start"}}, {"Attributes": {"detox.event_type": "fix"}}]
        with patch("scripts.telemetry.observe_batch.send_many_to_observe", return_value=True) as m:
            result = export_run_and_events({"job_id": "j1", "fixes_succeeded": 2}, events)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["exported_count"], 3)  # 1 run + 2 events
        self.assertEqual(result["events_export"]["exported_count"], 2)
        # Exactly one gRPC batch call for the whole run
        m.assert_called_once()
        batch = m.call_args.args[0]
        self.assertEqual(len(batch), 3)
        self.assertEqual(batch[0]["event_name"], RUN_EVENT_NAME)

    def test_no_events_sends_just_run(self):
        with patch("scripts.telemetry.observe_batch.send_many_to_observe", return_value=True) as m:
            result = export_run_and_events({"job_id": "j1"}, [])
        self.assertEqual(result["exported_count"], 1)
        self.assertEqual(len(m.call_args.args[0]), 1)

    def test_false_return_is_error_never_raises(self):
        with patch("scripts.telemetry.observe_batch.send_many_to_observe", return_value=False):
            result = export_run_and_events({"job_id": "j1"}, [{"Attributes": {}}])
        self.assertEqual(result["status"], "error")

    def test_unresolved_vulns_emitted_one_event_each(self):
        run = {"job_id": "j1", "repo_name": "svc", "cio": "DIGITAL", "unresolved_vulns": [
            {"vuln_id": "v1", "cwe_id": "CWE-89", "severity": "high", "remediation_type": "code_fix",
             "reason": "Query built in a stored procedure outside this repo"},
            {"vuln_id": "v2", "cwe_id": "CWE-937", "severity": None, "remediation_type": "dependency",
             "reason": "No safe version"},
        ]}
        events = [{"Attributes": {"detox.event_type": "phase_start"}}]
        with patch("scripts.telemetry.observe_batch.send_many_to_observe", return_value=True) as m:
            result = export_run_and_events(run, events)
        self.assertEqual(result["exported_count"], 4)
        self.assertEqual(result["events_export"]["exported_count"], 1)
        self.assertEqual(result["unresolved_export"]["exported_count"], 2)
        batch = m.call_args.args[0]
        unresolved = [b for b in batch if b["event_name"] == UNRESOLVED_EVENT_NAME]
        self.assertEqual(len(unresolved), 2)
        attrs = unresolved[0]["extra_attrs"]
        self.assertEqual(attrs["detox.job_id"], "j1")
        self.assertEqual(attrs["detox.repo_name"], "svc")
        self.assertEqual(attrs["detox.record_type"], "vuln_unresolved")
        self.assertEqual(attrs["detox.vuln.cwe_id"], "CWE-89")
        self.assertEqual(attrs["detox.unresolved.reason"], "Query built in a stored procedure outside this repo")
        self.assertNotIn("detox.unresolved.reason_code", attrs)
        self.assertNotIn("detox.vuln.id", attrs)  # high-cardinality, kept local only
        self.assertEqual(unresolved[0]["value"], "1")
        self.assertNotIn("detox.vuln.severity", unresolved[1]["extra_attrs"])  # None dropped


class TestUnresolvedVulnToBatchItem(unittest.TestCase):
    def test_all_attrs_are_strings(self):
        item = unresolved_vuln_to_batch_item(
            {"job_id": "j"}, {"vuln_id": "v", "reason": "Requires manual remediation"})
        self.assertEqual(item["event_name"], UNRESOLVED_EVENT_NAME)
        self.assertTrue(all(isinstance(v, str) for v in item["extra_attrs"].values()))
        self.assertEqual(item["extra_attrs"]["detox.unresolved.reason"], "Requires manual remediation")


if __name__ == "__main__":
    unittest.main()
