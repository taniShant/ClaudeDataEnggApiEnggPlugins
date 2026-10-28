#!/usr/bin/env python3
"""Detox batch send to Barclays Observe — one gRPC round-trip for a whole run.

``plugin_observability.py`` is the shared Barclays Observe library, copied
VERBATIM from astral — never edit it. It only offers single-event sends
(send_to_observe), so detox's batch extension lives here instead, reusing the
library's transport helpers (deps gate, CA trust, endpoint, resource attrs).
Re-syncing the library is then just a file copy.

The library raises at IMPORT when OTEL_EXPORTER_OTLP_ENDPOINT is unset (it has
no hardcoded fallback). Detox keeps its documented default endpoint by calling
apply_endpoint_default() before every library import — a value already set in
settings.json always wins. The library is imported lazily inside
send_many_to_observe so any remaining failure surfaces as a False return (with
the real message on stderr), never as an exception.
"""

import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

DEFAULT_OBSERVE_ENDPOINT = "https://metrics.dev-ai-tooling.barclays.intranet"


def apply_endpoint_default() -> None:
    """Set OTEL_EXPORTER_OTLP_ENDPOINT to detox's default if unset/blank.

    Must run BEFORE importing plugin_observability, which resolves the endpoint
    at import time. Never overrides an explicit value.
    """
    if not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip():
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = DEFAULT_OBSERVE_ENDPOINT


def _parse_identity_attrs() -> Dict[str, str]:
    """Barclays identity (barclays_*) from OTEL_RESOURCE_ATTRIBUTES, for log-record labels.

    The collector pipeline replaces resource attrs with its own, so identity must
    ride on each log record. Falls back to the OS username when the env var is absent.
    """
    identity: Dict[str, str] = {}
    for part in os.environ.get("OTEL_RESOURCE_ATTRIBUTES", "").split(","):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            identity[k.strip()] = v.strip()
    if not identity:
        uid = os.environ.get("USERNAME") or os.environ.get("USER", "")
        if uid:
            identity["barclays_user_id"] = uid
    return identity


class _RecordingExporter:
    """Delegating log exporter that remembers each export() result.

    The OTel SDK's batch processor only LOGS export failures (connection refused,
    TLS error, collector rejection) — it never reports them to the caller. Wrapping
    the exporter lets send_many_to_observe return the collector's real answer.
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.results: List[str] = []

    def export(self, batch: Any) -> Any:
        result = self._inner.export(batch)
        # Enum is LogExportResult (older SDKs) or LogRecordExportResult — compare by name.
        self.results.append(getattr(result, "name", str(result)))
        return result

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    def delivered(self) -> bool:
        return bool(self.results) and all(r == "SUCCESS" for r in self.results)


def send_many_to_observe(
    events: List[Dict[str, Any]],
    session_id: str = "",
) -> bool:
    """Send MANY events to Observe in a SINGLE gRPC round-trip (one force_flush).

    Each event is a dict:
        {"event_name": "detox.pipeline_run" | "detox.event",
         "value": "<str>",
         "extra_attrs": {<flat str->str labels>}}

    All records share one LoggerProvider/OTLPLogExporter and are flushed together.
    Record attrs mirror the library's send_to_observe (user.id, trace.id, identity
    labels). Returns True only when the collector ACCEPTED every exported batch;
    False on any failure, including an unreachable endpoint, TLS failure, or a
    flush timeout (never raises). A no-op empty list returns True.
    """
    if not events:
        return True

    try:
        apply_endpoint_default()
        from scripts.telemetry import plugin_observability as po

        if not po._ensure_observe_deps():
            return False

        from opentelemetry.sdk.resources import Resource
        try:
            from opentelemetry.sdk.logs import LoggerProvider, LoggingHandler
            from opentelemetry.sdk.logs.export import BatchLogRecordProcessor
        except ImportError:
            from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler  # type: ignore[no-redef]
            from opentelemetry.sdk._logs.export import BatchLogRecordProcessor  # type: ignore[no-redef]
        try:
            from opentelemetry.exporter.otlp.proto.grpc.log_exporter import OTLPLogExporter
        except ImportError:
            from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter  # type: ignore[no-redef]

        credentials = po._get_grpc_credentials()
        resource = Resource.create(po._build_resource_attrs())
        exporter = _RecordingExporter(
            OTLPLogExporter(endpoint=po._OBSERVE_ENDPOINT, credentials=credentials, insecure=False)
        )
        provider = LoggerProvider(resource=resource)
        provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

        handler = LoggingHandler(level=logging.INFO, logger_provider=provider)
        # Suppress Python source-location fields from leaking into Observe labels
        handler.addFilter(lambda r: (
            setattr(r, "pathname", "") or
            setattr(r, "filename", "") or
            setattr(r, "funcName", "") or
            setattr(r, "lineno", 0) or
            True
        ))

        logger = logging.getLogger(f"jarvis.plugin.detox.batch.{uuid.uuid4().hex[:8]}")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        logger.handlers = [handler]

        identity = _parse_identity_attrs()
        sid = session_id or os.environ.get("CLAUDE_CODE_SESSION_ID", "") or os.environ.get("CLAUDE_SESSION_ID", "")
        tid = sid or po._PROCESS_TRACE_ID
        uid = po._resolve_claude_user_id() or identity.get(
            "barclays_user_id", os.environ.get("USERNAME") or os.environ.get("USER", "")
        )
        app_version = os.environ.get("OTEL_SERVICE_VERSION", "")

        for seq, ev in enumerate(events, start=1):
            event_name = str(ev.get("event_name", "detox.event"))
            value = str(ev.get("value", ""))
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            attrs: Dict[str, Any] = {
                "event.name":      event_name,
                "event.timestamp": now_iso,
                "event.sequence":  seq,
                "session.id":      sid,
                "user.id":         uid,
                "trace.id":        tid,
                "app.version":     app_version,
                "terminal.type":   "cli",
                "plugin_metric":   event_name,
                "plugin_value":    value,
                **identity,
            }
            for k, v in (ev.get("extra_attrs") or {}).items():
                attrs[k] = str(v)
            logger.info(event_name, extra=attrs)

        flushed = provider.force_flush(timeout_millis=10000)
        provider.shutdown()
        if flushed is not False and exporter.delivered():
            return True
        print(
            f"[observe_batch] Observe did not accept the batch "
            f"(flushed={flushed}, export results={exporter.results or 'none'}) — "
            f"endpoint {po._OBSERVE_ENDPOINT} unreachable, TLS failure, or rejected",
            file=sys.stderr,
        )
        return False

    except Exception as e:
        print(f"[observe_batch] send_many_to_observe failed: {e}", file=sys.stderr)
        return False
