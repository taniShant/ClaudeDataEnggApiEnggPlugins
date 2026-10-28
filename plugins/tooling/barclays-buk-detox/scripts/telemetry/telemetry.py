#!/usr/bin/env python3
"""Telemetry collector for the Detox pipeline.

Provides three actions:
  emit     — Append an OTel-native event to the JSONL log
  query    — Read and filter events from the log
  summarize — Aggregate metrics over a time period

Input (JSON stdin):
  {"action": "emit", "event": {...}}
  {"action": "query", "filters": {...}, "limit": 100}
  {"action": "summarize", "period": "30d", "group_by": "user"}

Output (JSON stdout):
  Structured JSON with status field.

Storage: ~/.detox/telemetry/events.jsonl (append-only, auto-rotated at 50MB)
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output, log, locked_append, _lock_file
from scripts.core.errors import error_exit
from scripts.telemetry.version import PLUGIN_VERSION

# Constants
TELEMETRY_DIR = Path.home() / ".detox" / "telemetry"
EVENTS_FILE = TELEMETRY_DIR / "events.jsonl"
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB rotation threshold


def ensure_telemetry_dir() -> None:
    """Create the telemetry directory if it doesn't exist."""
    TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)


def generate_trace_id(job_id: str) -> str:
    """Derive a valid 32-hex-char OTLP TraceId from job_id.

    OTLP requires TraceId to be 16 bytes rendered as 32 lowercase hex chars.
    Standard job_ids are 8 hex chars (uuid4().hex[:8]), which zero-pad to a
    valid 32-hex ID. A non-hex job_id would otherwise produce an invalid ID,
    so hash it to a stable 32-hex digest. The TraceId is stored on each event
    for local correlation; the strategic Observe exporter folds events into the
    single run event rather than emitting a separate trace.
    """
    if job_id:
        candidate = job_id.strip().lower()
        padded = candidate.ljust(32, "0")[:32]
        try:
            int(padded, 16)  # valid hex (incl. the common 8-hex job_id) -> keep padded form
            return padded
        except ValueError:
            return hashlib.md5(job_id.encode("utf-8")).hexdigest()
    return "0" * 32


def generate_span_id(job_id: str, phase: int | str | None = None) -> str:
    """Generate a 16-char SpanId from job_id and optional phase."""
    seed = f"{job_id}-phase-{phase}" if phase is not None else f"{job_id}-root"
    return hashlib.md5(seed.encode()).hexdigest()[:16]


def build_event(event_data: dict[str, Any]) -> dict[str, Any]:
    """Construct a full OTel-native telemetry event from input data."""
    job_id = event_data.get("job_id", "unknown")
    phase = event_data.get("phase")
    event_type = event_data.get("event_type", "unknown")
    severity = event_data.get("severity", "INFO").upper()

    severity_map = {
        "TRACE": 1, "DEBUG": 5, "INFO": 9,
        "WARN": 13, "ERROR": 17, "FATAL": 21,
    }

    # Determine environment
    is_ci = any(os.environ.get(v) for v in (
        "CI", "CI_JOB_ID", "BUILD_NUMBER", "GITHUB_ACTIONS"
    ))

    # Build the full event
    event = {
        "Timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "SeverityText": severity,
        "SeverityNumber": severity_map.get(severity, 9),
        "Body": event_data.get("body", f"Event: {event_type}"),
        "TraceId": generate_trace_id(job_id),
        "SpanId": generate_span_id(job_id, phase),
        "Resource": {
            "service.name": "detox",
            "service.version": PLUGIN_VERSION,
            "deployment.environment": "ci" if is_ci else "local",
        },
        "Attributes": {
            "detox.event_type": event_type,
            "detox.job_id": job_id,
        },
    }

    # Merge additional attributes from input
    for key, value in event_data.items():
        if key not in ("event_type", "job_id", "phase", "severity", "body"):
            event["Attributes"][f"detox.{key}"] = value

    # Add phase to attributes if present
    if phase is not None:
        event["Attributes"]["detox.phase"] = phase

    return event


def rotate_if_needed() -> None:
    """Rotate the events file if it exceeds the size threshold."""
    if not EVENTS_FILE.exists():
        return
    try:
        if EVENTS_FILE.stat().st_size > MAX_FILE_SIZE_BYTES:
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            rotated = TELEMETRY_DIR / f"events.{ts}.jsonl"
            EVENTS_FILE.rename(rotated)
            log(f"Rotated events log to {rotated}")
    except OSError as e:
        log(f"Rotation check failed (non-fatal): {e}")


def emit_event(input_data: dict[str, Any]) -> dict[str, Any]:
    """Append an event to the JSONL log. Fire-and-forget semantics."""
    event_data = input_data.get("event", {})
    if not event_data:
        error_exit("event dict is required for emit action", "input_validation")

    ensure_telemetry_dir()
    rotate_if_needed()

    event = build_event(event_data)
    event_id = uuid.uuid4().hex[:12]
    event["Attributes"]["detox.event_id"] = event_id

    try:
        with locked_append(EVENTS_FILE) as f:
            f.write(json.dumps(event, default=str) + "\n")
    except OSError as e:
        # Fire-and-forget: log error but don't fail the pipeline
        log(f"Failed to write telemetry event (non-fatal): {e}")
        return {
            "status": "error",
            "error": f"Write failed: {e}",
            "event_id": event_id,
        }

    return {
        "status": "success",
        "event_id": event_id,
        "log_path": str(EVENTS_FILE),
    }


def parse_period(period_str: str) -> datetime:
    """Parse a period string (e.g., '7d', '30d', '90d') into a start datetime."""
    period_str = period_str.strip().lower()
    if period_str == "all":
        return datetime.min.replace(tzinfo=timezone.utc)

    unit = period_str[-1]
    try:
        value = int(period_str[:-1])
    except (ValueError, IndexError):
        error_exit(f"Invalid period format: {period_str}. Use Nd (e.g., 7d, 30d)", "input_validation")

    now = datetime.now(timezone.utc)
    if unit == "d":
        return now - timedelta(days=value)
    elif unit == "h":
        return now - timedelta(hours=value)
    else:
        error_exit(f"Unknown period unit: {unit}. Use 'd' for days or 'h' for hours", "input_validation")

    return now  # pragma: no cover


def read_events(after: datetime | None = None, limit: int = 1000) -> list[dict[str, Any]]:
    """Read events from the JSONL log, optionally filtered by time."""
    if not EVENTS_FILE.exists():
        return []

    events = []
    try:
        with open(EVENTS_FILE, "r") as f:
            _lock_file(f)
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if after:
                    ts_str = event.get("Timestamp", "")
                    try:
                        ts = datetime.fromisoformat(ts_str)
                        if ts < after:
                            continue
                    except (ValueError, TypeError):
                        continue

                events.append(event)
                if len(events) >= limit:
                    break
    except OSError as e:
        log(f"Failed to read events (non-fatal): {e}")

    return events


def read_events_for_job(job_id: str, limit: int = 100000) -> list[dict[str, Any]]:
    """Return all events whose Attributes.detox.job_id matches job_id.

    Used at pipeline end to export this run's detailed events to the OTel
    Collector alongside the run summary. Reuses read_events() for the
    locked, decode-safe read; filters in memory by job_id.
    """
    if not job_id:
        return []
    return [
        e for e in read_events(limit=limit)
        if e.get("Attributes", {}).get("detox.job_id") == job_id
    ]


def query_events(input_data: dict[str, Any]) -> dict[str, Any]:
    """Query and filter events from the log."""
    filters = input_data.get("filters", {})
    limit = input_data.get("limit", 100)

    # Time filter
    after = None
    if "after" in filters:
        try:
            after = datetime.fromisoformat(filters["after"])
        except (ValueError, TypeError):
            pass
    elif "period" in filters:
        after = parse_period(filters["period"])

    events = read_events(after=after, limit=limit * 10)  # Read more to allow filtering

    # Apply attribute filters
    event_type = filters.get("event_type")
    job_id = filters.get("job_id")
    user_name = filters.get("user_name")

    filtered = []
    for event in events:
        attrs = event.get("Attributes", {})
        if event_type and attrs.get("detox.event_type") != event_type:
            continue
        if job_id and attrs.get("detox.job_id") != job_id:
            continue
        if user_name and attrs.get("detox.user.name") != user_name:
            continue
        filtered.append(event)
        if len(filtered) >= limit:
            break

    return {
        "status": "success",
        "events": filtered,
        "count": len(filtered),
        "total_available": len(filtered),
    }


def summarize_events(input_data: dict[str, Any]) -> dict[str, Any]:
    """Aggregate metrics over a time period."""
    period_str = input_data.get("period", "30d")
    group_by = input_data.get("group_by")

    after = parse_period(period_str)
    events = read_events(after=after, limit=100000)

    # Basic counts by event type
    type_counts: dict[str, int] = {}
    severity_counts: dict[str, int] = {}
    users: set[str] = set()
    jobs: set[str] = set()

    for event in events:
        attrs = event.get("Attributes", {})
        event_type = attrs.get("detox.event_type", "unknown")
        type_counts[event_type] = type_counts.get(event_type, 0) + 1

        severity = event.get("SeverityText", "INFO")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

        user = attrs.get("detox.user.name")
        if user:
            users.add(user)

        job = attrs.get("detox.job_id")
        if job:
            jobs.add(job)

    summary: dict[str, Any] = {
        "period": period_str,
        "total_events": len(events),
        "unique_users": len(users),
        "unique_jobs": len(jobs),
        "by_event_type": type_counts,
        "by_severity": severity_counts,
    }

    # Group-by aggregation
    if group_by == "user":
        by_user: dict[str, int] = {}
        for event in events:
            user = event.get("Attributes", {}).get("detox.user.name", "unknown")
            by_user[user] = by_user.get(user, 0) + 1
        summary["by_user"] = by_user
    elif group_by == "project":
        by_project: dict[str, int] = {}
        for event in events:
            project = event.get("Attributes", {}).get("detox.repo_name", "unknown")
            by_project[project] = by_project.get(project, 0) + 1
        summary["by_project"] = by_project

    return {"status": "success", "summary": summary}


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    action = input_data.get("action")
    if not action:
        error_exit("action is required (emit, query, or summarize)", "input_validation")

    if action == "emit":
        result = emit_event(input_data)
    elif action == "query":
        result = query_events(input_data)
    elif action == "summarize":
        result = summarize_events(input_data)
    else:
        error_exit(
            f"Unknown action: {action}. Must be emit, query, or summarize",
            "input_validation",
        )

    write_json_output(result, start_time=start_time)


if __name__ == "__main__":
    main()
