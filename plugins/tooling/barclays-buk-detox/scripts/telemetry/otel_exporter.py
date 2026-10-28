#!/usr/bin/env python3
"""Export detox telemetry to the Barclays Observe platform via gRPC OTLP.

STRATEGIC PATH (replaces the old OTLP/HTTP → ad-hoc Collector → S3 path):

    detox run record → send_to_observe() → gRPC OTLP logs
      → Barclays Collector (metrics.dev-ai-tooling.barclays.intranet:443)
      → FluentBit → CloudWatch → Observe (dataset: claude_code_client)

This module is a THIN ADAPTER. All transport, TLS/CA trust, dependency
bootstrap and endpoint resolution live in the copied, upstream-faithful
``plugin_observability.py`` (ported verbatim from the astral plugin). Here we
only shape detox's denormalized run record into the ``send_to_observe``
contract and set detox identity at the call site.

Mapping — full parity with the old OTLP export:
  * the denormalized run summary → one `detox.pipeline_run` event
    (send_to_observe, value=<fixes_succeeded>, all detox.* fields as labels)
  * the run's granular per-phase events → one `detox.<event_type>` event each,
    all sent together in a SINGLE gRPC batch (observe_batch.send_many_to_observe,
    detox's extension kept outside the verbatim library) so latency
    stays ~one round-trip regardless of event count.
  * each run_record["unresolved_vulns"] entry → one `detox.vuln_unresolved`
    event (same batch), carrying the LLM's detox.unresolved.reason verbatim.

The barclays_* identity (user id, cio, team, email) is injected automatically
from OTEL_RESOURCE_ATTRIBUTES, landing as labels.* — the collector overwrites
resource attrs, so identity MUST live in record attrs.

Fire-and-forget — if deps are missing, the endpoint is unreachable, or TLS
fails, this returns an error status and NEVER raises. Telemetry export must
never block the pipeline.

Input (JSON stdin):
  {"action": "push_run", "run_record": {...denormalized run summary...}}
  {"action": "push_events", "events": [...]}        # batched to Observe
  {"action": "push_all", "run_record": {...}, "events": [...]}

Output (JSON stdout):
  {"status": "success", "exported_count": 1}
  {"status": "error", "error": "..."}
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import log, read_json_input, write_json_output, sanitize_pat, get_barclays_cio
from scripts.core.errors import error_exit
from scripts.telemetry.version import PLUGIN_VERSION

# The strategic Observe event name — one event per detox pipeline run.
RUN_EVENT_NAME = "detox.pipeline_run"
# One event per unfixed finding in a run; aggregate on detox.unresolved.reason.
UNRESOLVED_EVENT_NAME = "detox.vuln_unresolved"


def _load_org_cio() -> str | None:
    """Read the Barclays CIO (barclays_cio) for adoption attribution.

    Best-effort — never raises. send_to_observe also injects barclays_cio from
    OTEL_RESOURCE_ATTRIBUTES; this is kept so the attribute is present even when
    the run record already carries a cio value from identity resolution.
    """
    return get_barclays_cio()


def _flatten_value(value: Any) -> str:
    """Coerce an attribute value to a string label (Observe labels are strings)."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, dict)):
        return json.dumps(value, default=str)
    return str(value)


def run_record_to_attrs(run_record: dict[str, Any]) -> dict[str, str]:
    """Flatten a denormalized run record into Observe label attributes.

    Mirrors the detox.* attribute surface the old OTLP exporter emitted, but as
    a flat str->str dict suitable for send_to_observe's extra_attrs. Identity
    (barclays_*) is added by send_to_observe itself from OTEL_RESOURCE_ATTRIBUTES.
    """
    status = run_record.get("status", "completed")
    cio = run_record.get("cio") or _load_org_cio()

    raw = {
        "service.name": "detox",
        "service.version": run_record.get("plugin_version", PLUGIN_VERSION),
        "deployment.environment": "ci" if _is_ci() else "local",
        "detox.record_type": "pipeline_run",
        "detox.job_id": run_record.get("job_id", "unknown"),
        "detox.command": run_record.get("command", "remediate"),
        "detox.repo_name": run_record.get("repo_name", "unknown"),
        "detox.user.name": run_record.get("user_name", "unknown"),
        "detox.user.email": run_record.get("user_email", ""),
        "detox.cio": cio,
        "detox.model": run_record.get("model", "sonnet"),
        "detox.status": status,
        "detox.severity_filter": run_record.get("severity_filter", "all"),
        "detox.dry_run": run_record.get("dry_run", False),
        "detox.vulns_total": run_record.get("vulns_total", 0),
        "detox.fixes_attempted": run_record.get("fixes_attempted", 0),
        "detox.fixes_succeeded": run_record.get("fixes_succeeded", 0),
        "detox.fixes_failed": run_record.get("fixes_failed", 0),
        "detox.fixes_skipped": run_record.get("fixes_skipped", 0),
        "detox.fixes_validated_clean": run_record.get("fixes_validated_clean", 0),
        "detox.vulns_deferred": run_record.get("vulns_deferred", 0),
        "detox.vulns_deferred_by_reason": run_record.get("vulns_deferred_by_reason", {}),
        "detox.fixes_unverified_by_reason": run_record.get("fixes_unverified_by_reason", {}),
        # Also emitted per finding as detox.vuln_unresolved; inlined here so the run row is self-contained.
        "detox.unresolved_vulns": run_record.get("unresolved_vulns") or [],
        "detox.unresolved_vulns_count": len(run_record.get("unresolved_vulns") or []),
        "detox.remediation_rate": run_record.get("remediation_rate"),
        "detox.verified_remediation_rate": run_record.get("verified_remediation_rate"),
        "detox.fix_success_rate": run_record.get("fix_success_rate"),
        "detox.fix_failure_rate": run_record.get("fix_failure_rate"),
        "detox.deferral_rate": run_record.get("deferral_rate"),
        "detox.validation_pass_count": run_record.get("validation_pass_count", 0),
        "detox.validation_fail_count": run_record.get("validation_fail_count", 0),
        "detox.validation_pass_rate": run_record.get("validation_pass_rate"),
        "detox.tests_generated": run_record.get("tests_generated", 0),
        "detox.tests_passed": run_record.get("tests_passed", 0),
        "detox.tests_failed": run_record.get("tests_failed", 0),
        "detox.test_pass_rate": run_record.get("test_pass_rate"),
        "detox.pr_created": run_record.get("pr_created", False),
        "detox.pr_url": run_record.get("pr_url"),
        "detox.total_duration_ms": run_record.get("total_duration_ms"),
        "detox.agent_invocations": run_record.get("agent_invocations", 0),
        "detox.self_check_passed": run_record.get("self_check_passed", True),
        "detox.plugin_version": run_record.get("plugin_version", PLUGIN_VERSION),
        "detox.cwes_targeted": run_record.get("cwes_targeted", []),
        "detox.vulns_by_severity": run_record.get("vulns_by_severity", {}),
        "detox.vulns_by_type": run_record.get("vulns_by_type", {}),
        "detox.phases": run_record.get("phases", {}),
        "detox.errors": run_record.get("errors", []),
        "detox.flags_raised": run_record.get("flags_raised", []),
    }
    # Drop None values; coerce the rest to string labels.
    return {k: _flatten_value(v) for k, v in raw.items() if v is not None}


def _is_ci() -> bool:
    return any(os.environ.get(v) for v in ("CI", "CI_JOB_ID", "BUILD_NUMBER", "GITHUB_ACTIONS"))


def run_record_to_batch_item(run_record: dict[str, Any]) -> dict[str, Any]:
    """Map the denormalized run record to a `detox.pipeline_run` batch item."""
    return {
        "event_name": RUN_EVENT_NAME,
        "value": str(run_record.get("fixes_succeeded", 0)),
        "extra_attrs": run_record_to_attrs(run_record),
    }


def unresolved_vuln_to_batch_item(run_record: dict[str, Any], vuln: dict[str, Any]) -> dict[str, Any]:
    """Map one run_record["unresolved_vulns"] entry to a `detox.vuln_unresolved` batch item.

    vuln_id is deliberately not exported (unbounded label cardinality); it stays in runs.jsonl.
    """
    raw = {
        "service.name": "detox",
        "service.version": run_record.get("plugin_version", PLUGIN_VERSION),
        "detox.record_type": "vuln_unresolved",
        "detox.job_id": run_record.get("job_id", "unknown"),
        "detox.repo_name": run_record.get("repo_name", "unknown"),
        "detox.cio": run_record.get("cio") or _load_org_cio(),
        "detox.model": run_record.get("model", "sonnet"),
        "detox.status": run_record.get("status", "completed"),
        "detox.plugin_version": run_record.get("plugin_version", PLUGIN_VERSION),
        "detox.vuln.cwe_id": vuln.get("cwe_id"),
        "detox.vuln.severity": vuln.get("severity"),
        "detox.vuln.remediation_type": vuln.get("remediation_type"),
        "detox.unresolved.reason": vuln.get("reason", ""),
    }
    return {
        "event_name": UNRESOLVED_EVENT_NAME,
        "value": "1",
        "extra_attrs": {k: _flatten_value(v) for k, v in raw.items() if v is not None},
    }


def export_run_and_events(
    run_record: dict[str, Any],
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Send the whole run — summary event + all per-phase events — in ONE batch.

    This is the end-of-run entry point: it combines the `detox.pipeline_run`
    event and every granular event into a single send_many_to_observe call, so
    the entire run is exported to Observe in one gRPC round-trip. Fire-and-forget:
    returns an error status (never raises) on any failure.
    """
    try:
        from scripts.telemetry.observe_batch import send_many_to_observe
    except Exception as e:
        return {"status": "error", "error": f"observability library unavailable: {sanitize_pat(str(e))}"}

    events = events or []
    unresolved = run_record.get("unresolved_vulns") or []
    batch = [run_record_to_batch_item(run_record)]
    batch.extend(otel_event_to_batch_item(e) for e in events)
    batch.extend(unresolved_vuln_to_batch_item(run_record, v) for v in unresolved if isinstance(v, dict))
    session_id = run_record.get("session_id", "") or os.environ.get("CLAUDE_SESSION_ID", "")

    try:
        ok = send_many_to_observe(batch, session_id=session_id)
    except Exception as e:  # defensive — send_many_to_observe already never raises
        return {"status": "error", "error": f"Unexpected error: {sanitize_pat(str(e))}"}

    job_id = run_record.get("job_id")
    event_count = len(events)
    unresolved_count = len(batch) - 1 - event_count
    if ok:
        log(f"Exported run + {event_count} events + {unresolved_count} unresolved vulns "
            f"to Observe (one batch): {job_id}")
        return {
            "status": "success",
            "exported_count": len(batch),
            "job_id": job_id,
            "events_export": {"status": "success", "exported_count": event_count},
            "unresolved_export": {"status": "success", "exported_count": unresolved_count},
        }
    return {"status": "error", "error": "send_many_to_observe returned false (deps/endpoint/TLS)"}


def export_single(run_record: dict[str, Any]) -> dict[str, Any]:
    """Export just the run summary as one `detox.pipeline_run` event.

    Used by the `push_run` stdin action. The end-of-run pipeline path uses
    export_run_and_events (run + events in one batch) instead. Fire-and-forget.
    """
    try:
        from scripts.telemetry.observe_batch import apply_endpoint_default
        apply_endpoint_default()
        from scripts.telemetry.plugin_observability import send_to_observe
    except Exception as e:  # import of the adapter itself failing is non-fatal
        return {"status": "error", "error": f"observability library unavailable: {sanitize_pat(str(e))}"}

    attrs = run_record_to_attrs(run_record)
    # Primary metric value: fixes succeeded this run (string per the contract).
    value = str(run_record.get("fixes_succeeded", 0))
    session_id = run_record.get("session_id", "") or os.environ.get("CLAUDE_SESSION_ID", "")

    try:
        ok = send_to_observe(
            event_name=RUN_EVENT_NAME,
            value=value,
            session_id=session_id,
            extra_attrs=attrs,
        )
    except Exception as e:  # defensive — send_to_observe already never raises
        return {"status": "error", "error": f"Unexpected error: {sanitize_pat(str(e))}"}

    if ok:
        job_id = run_record.get("job_id")
        log(f"Exported run record to Observe: {job_id}")
        return {"status": "success", "exported_count": 1, "job_id": job_id}
    return {"status": "error", "error": "send_to_observe returned false (deps/endpoint/TLS)"}


def otel_event_to_batch_item(event: dict[str, Any]) -> dict[str, Any]:
    """Map a stored OTel-native detox event to a send_many_to_observe item.

    Stored events (from events.jsonl via telemetry.read_events_for_job) carry
    Body / SeverityText / Attributes (detox.event_type, detox.job_id, detox.phase,
    …). We flatten Attributes into labels and surface severity + body so each
    event lands in Observe as its own queryable record — full parity with the
    old per-event OTLP export.
    """
    attrs_in = event.get("Attributes", {}) or {}
    flat = {k: _flatten_value(v) for k, v in attrs_in.items() if v is not None}
    # Surface the severity + human body as labels too.
    flat["severity"] = event.get("SeverityText", "INFO")
    body = event.get("Body")
    if body:
        flat["event.body"] = _flatten_value(body)
    trace_id = event.get("TraceId")
    if trace_id:
        flat["trace_id"] = _flatten_value(trace_id)

    event_type = attrs_in.get("detox.event_type", "event")
    return {
        "event_name": f"detox.{event_type}",
        "value": "1",  # one occurrence of this event
        "extra_attrs": flat,
    }


def export_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Export this run's granular per-phase events to Observe in ONE gRPC batch.

    Full parity with the old per-event OTLP export: every event in events.jsonl
    for the run is sent as its own Observe record, but all are flushed together
    over a single gRPC round-trip (via send_many_to_observe) so pipeline latency
    stays ~one send regardless of event count. Fire-and-forget — never raises.
    """
    if not events:
        return {"status": "success", "exported_count": 0}

    try:
        from scripts.telemetry.observe_batch import send_many_to_observe
    except Exception as e:
        return {"status": "error", "error": f"observability library unavailable: {sanitize_pat(str(e))}"}

    batch = [otel_event_to_batch_item(e) for e in events]

    try:
        ok = send_many_to_observe(batch)
    except Exception as e:  # defensive — send_many_to_observe already never raises
        return {"status": "error", "error": f"Unexpected error: {sanitize_pat(str(e))}"}

    if ok:
        log(f"Exported {len(batch)} events to Observe (batched)")
        return {"status": "success", "exported_count": len(batch)}
    return {"status": "error", "error": "send_many_to_observe returned false (deps/endpoint/TLS)"}


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    action = input_data.get("action")
    if not action:
        error_exit("action is required (push_run, push_events, push_all)", "input_validation")

    if action == "push_run":
        run_record = input_data.get("run_record")
        if not run_record:
            error_exit("run_record is required for push_run action", "input_validation")
        result = export_single(run_record)

    elif action == "push_events":
        events = input_data.get("events", [])
        result = export_events(events)

    elif action == "push_all":
        run_record = input_data.get("run_record")
        events = input_data.get("events", [])
        if run_record:
            # Run summary + all events in ONE gRPC batch (end-of-run path).
            result = export_run_and_events(run_record, events)
        elif events:
            result = export_events(events)
        else:
            result = {"status": "success", "exported_count": 0}

    else:
        error_exit(
            f"Unknown action: {action}. Must be push_run, push_events, or push_all",
            "input_validation",
        )

    write_json_output(result, start_time=start_time)


if __name__ == "__main__":
    main()
