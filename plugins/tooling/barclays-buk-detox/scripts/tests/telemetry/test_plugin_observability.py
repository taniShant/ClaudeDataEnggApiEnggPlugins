"""Tests for scripts/telemetry/plugin_observability.py.

This module is a faithful copy of astral's strategic Observe telemetry library.
These tests exercise the pieces detox relies on WITHOUT any network or
grpc/opentelemetry deps: endpoint resolution, user-id resolution, resource
attribute building, the deps-gate fallback, and the file-based MetricsClient.

Mirrors astral's own test approach — patch the module's dependency gate
(_ensure_observe_deps) rather than mocking grpc, and assert the public contract
(never raises, returns False) when deps are unavailable.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

# The library requires the endpoint at import time (no hardcoded fallback).
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "https://metrics.dev-ai-tooling.barclays.intranet")

from scripts.telemetry import plugin_observability as po


class TestResolveEndpoint(unittest.TestCase):

    def test_env_override_appends_443(self):
        with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "https://host.example.com"}, clear=True):
            self.assertEqual(po._resolve_endpoint(), "host.example.com:443")

    def test_env_override_keeps_explicit_port(self):
        with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "https://host.example.com:4317"}, clear=True):
            self.assertEqual(po._resolve_endpoint(), "host.example.com:4317")

    def test_missing_endpoint_raises(self):
        # Library 1.1.0 has no hardcoded fallback — the env var is required.
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(EnvironmentError):
                po._resolve_endpoint()

    def test_strips_trailing_slash(self):
        with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "https://host.example.com/"}, clear=True):
            self.assertEqual(po._resolve_endpoint(), "host.example.com:443")


class TestResolveUserId(unittest.TestCase):

    def test_from_otel_resource_attributes(self):
        with patch.dict(os.environ, {"OTEL_RESOURCE_ATTRIBUTES": "barclays_cio=DIGITAL,barclays_user_id=g12345"}, clear=True):
            self.assertEqual(po._resolve_user_id(), "g12345")

    def test_falls_back_to_username(self):
        with patch.dict(os.environ, {"USERNAME": "G0131"}, clear=True):
            self.assertEqual(po._resolve_user_id(), "G0131")


class TestBuildResourceAttrs(unittest.TestCase):

    def test_service_attrs_from_env(self):
        with patch.dict(os.environ, {"OTEL_SERVICE_NAME": "claude-code", "OTEL_SERVICE_VERSION": "2.1.185"}, clear=True):
            attrs = po._build_resource_attrs()
        self.assertEqual(attrs["service.name"], "claude-code")
        self.assertEqual(attrs["service.version"], "2.1.185")

    def test_omits_empty_service_attrs(self):
        with patch.dict(os.environ, {}, clear=True):
            attrs = po._build_resource_attrs()
        self.assertNotIn("service.name", attrs)
        self.assertNotIn("service.version", attrs)

    def test_parses_resource_attributes_env(self):
        with patch.dict(os.environ, {"OTEL_RESOURCE_ATTRIBUTES": "barclays_cio=DIGITAL,barclays_team=OB"}, clear=True):
            attrs = po._build_resource_attrs()
        self.assertEqual(attrs["barclays_cio"], "DIGITAL")
        self.assertEqual(attrs["barclays_team"], "OB")


class TestSendToObserveDepsGate(unittest.TestCase):
    """When deps can't be installed, send must return False and never raise."""

    def test_returns_false_when_deps_unavailable(self):
        with patch.object(po, "_ensure_observe_deps", return_value=False):
            result = po.send_to_observe("detox.pipeline_run", "1", extra_attrs={"k": "v"})
        self.assertFalse(result)


class TestMetricsClientFileBased(unittest.TestCase):
    """The file-based metrics path is stdlib-only — works without grpc."""

    def test_counter_key_no_labels(self):
        m = po.MetricsClient(plugin_name="t_counter", flush_interval_s=9999)
        try:
            m.increment_counter("detox_runs")
            self.assertEqual(m.get_state()["counters"]["detox_runs|||"], 1)
        finally:
            m._stop_event.set()
            m._thread.join(timeout=2)

    def test_counter_key_sorted_labels(self):
        m = po.MetricsClient(plugin_name="t_labels", flush_interval_s=9999)
        try:
            m.increment_counter("c", labels={"env": "prod", "app": "detox"})
            self.assertIn("c|||app=detox,env=prod", m.get_state()["counters"])
        finally:
            m._stop_event.set()
            m._thread.join(timeout=2)

    def test_flush_writes_valid_otlp_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = po.MetricsClient(plugin_name="t_flush", flush_interval_s=9999)
            try:
                m._metrics_file = Path(tmp) / "metrics.json"
                m.increment_counter("c", 2)
                m.flush()
                import json
                data = json.loads(m._metrics_file.read_text())
                self.assertIn("resourceMetrics", data)
            finally:
                m._stop_event.set()
                m._thread.join(timeout=2)

    def test_reset_clears_state(self):
        m = po.MetricsClient(plugin_name="t_reset", flush_interval_s=9999)
        try:
            m.increment_counter("c")
            m.set_gauge("g", 1.0)
            m.reset()
            st = m.get_state()
            self.assertEqual(st["counters"], {})
            self.assertEqual(st["gauges"], {})
        finally:
            m._stop_event.set()
            m._thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
