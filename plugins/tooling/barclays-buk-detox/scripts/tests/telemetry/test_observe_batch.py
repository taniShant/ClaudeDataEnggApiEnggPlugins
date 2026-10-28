"""Tests for scripts/telemetry/observe_batch.py — detox's batch send extension.

Like test_plugin_observability, no network or grpc/opentelemetry deps: patch the
library's dependency gate and assert the contract (never raises, returns bool).
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

# The library requires the endpoint at import time (no hardcoded fallback).
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "https://metrics.dev-ai-tooling.barclays.intranet")

from scripts.telemetry import observe_batch as ob
from scripts.telemetry import plugin_observability as po


class TestSendManyToObserve(unittest.TestCase):

    def test_empty_is_true_noop(self):
        # No deps needed for an empty batch — returns True without touching the gate.
        self.assertTrue(ob.send_many_to_observe([]))

    def test_returns_false_when_deps_unavailable(self):
        with patch.object(po, "_ensure_observe_deps", return_value=False):
            result = ob.send_many_to_observe([{"event_name": "detox.event", "value": "1"}])
        self.assertFalse(result)

    def test_library_import_failure_returns_false_never_raises(self):
        # e.g. OTEL_EXPORTER_OTLP_ENDPOINT unset → the library raises at import.
        real_import = __import__

        def failing_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "scripts.telemetry" and "plugin_observability" in (fromlist or ()):
                raise OSError("OTEL_EXPORTER_OTLP_ENDPOINT is not set")
            return real_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=failing_import):
            result = ob.send_many_to_observe([{"event_name": "detox.event", "value": "1"}])
        self.assertFalse(result)


class _Result:
    def __init__(self, name):
        self.name = name


class _FakeExporter:
    def __init__(self, *names):
        self._names = list(names)
        self.shut = False

    def export(self, batch):
        return _Result(self._names.pop(0))

    def shutdown(self):
        self.shut = True


class TestRecordingExporter(unittest.TestCase):
    """Delivery is judged by the collector's real export() answer, not the flush."""

    def test_delivered_when_all_exports_succeed(self):
        rec = ob._RecordingExporter(_FakeExporter("SUCCESS", "SUCCESS"))
        rec.export([1]); rec.export([2])
        self.assertTrue(rec.delivered())

    def test_not_delivered_when_any_export_fails(self):
        rec = ob._RecordingExporter(_FakeExporter("SUCCESS", "FAILURE"))
        rec.export([1]); rec.export([2])
        self.assertFalse(rec.delivered())
        self.assertEqual(rec.results, ["SUCCESS", "FAILURE"])

    def test_not_delivered_when_nothing_exported(self):
        # e.g. flush timed out before the batch was ever sent
        self.assertFalse(ob._RecordingExporter(_FakeExporter()).delivered())

    def test_delegates_other_calls(self):
        inner = _FakeExporter()
        ob._RecordingExporter(inner).shutdown()
        self.assertTrue(inner.shut)


class TestApplyEndpointDefault(unittest.TestCase):

    def test_sets_default_when_unset(self):
        with patch.dict(os.environ, {}, clear=True):
            ob.apply_endpoint_default()
            self.assertEqual(os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"], ob.DEFAULT_OBSERVE_ENDPOINT)

    def test_sets_default_when_blank(self):
        with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "  "}, clear=True):
            ob.apply_endpoint_default()
            self.assertEqual(os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"], ob.DEFAULT_OBSERVE_ENDPOINT)

    def test_never_overrides_explicit_value(self):
        with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "https://other.example.com"}, clear=True):
            ob.apply_endpoint_default()
            self.assertEqual(os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"], "https://other.example.com")

    def test_default_resolves_to_observe_grpc_host(self):
        with patch.dict(os.environ, {}, clear=True):
            ob.apply_endpoint_default()
            self.assertEqual(po._resolve_endpoint(), "metrics.dev-ai-tooling.barclays.intranet:443")


class TestParseIdentityAttrs(unittest.TestCase):

    def test_parses_barclays_keys(self):
        with patch.dict(os.environ, {"OTEL_RESOURCE_ATTRIBUTES": "barclays_cio=DIGITAL,barclays_user_id=g1"}, clear=True):
            ident = ob._parse_identity_attrs()
        self.assertEqual(ident["barclays_cio"], "DIGITAL")
        self.assertEqual(ident["barclays_user_id"], "g1")

    def test_falls_back_to_username(self):
        with patch.dict(os.environ, {"USER": "g999"}, clear=True):
            ident = ob._parse_identity_attrs()
        self.assertEqual(ident["barclays_user_id"], "g999")


if __name__ == "__main__":
    unittest.main()
