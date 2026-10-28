#!/usr/bin/env python3
"""Pipeline state management — init, update, and gate-check operations.

Input (JSON stdin):
    Mode 1 - Init (writes the state file, default {project_path}/.detox/state.json):
    {"action": "init", "project_path": "...", "model": "...", "state_path": "optional", ...}

    Mode 2 - Update:
    {"action": "update", "state_path": "...", "updates": {"phases.1.status": "completed", ...}}

    Mode 3 - Append to list fields:
    {"action": "append", "state_path": "...", "items": {"fix_results": [{...}], "test_results": {...}}}

    Mode 4 - Gate check:
    {"action": "check_gate", "state_path": "...", "phase": 4, "required_phases": [1, 2, 3]}

Output (JSON stdout):
    The full state JSON (init/update/append) or gate check result.

The state file is the source of truth for run telemetry: run_recorder.py reads its
counts from it. Every phase status change made through update emits a phase.* event
to the local telemetry log, exported with the run at pipeline end.
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Cross-platform file locking
try:
    import fcntl

    def _lock_exclusive(f):  # type: ignore[no-untyped-def]
        fcntl.flock(f, fcntl.LOCK_EX)

    def _lock_shared(f):  # type: ignore[no-untyped-def]
        fcntl.flock(f, fcntl.LOCK_SH)
except ImportError:
    import msvcrt

    def _lock_exclusive(f):  # type: ignore[no-untyped-def]
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)

    def _lock_shared(f):  # type: ignore[no-untyped-def]
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output, log
from scripts.core.errors import error_exit

STATE_DIRNAME = ".detox"
STATE_FILENAME = "state.json"

# Phase status -> telemetry event type (see detox:telemetry-contract).
_PHASE_EVENT_TYPES = {
    "in_progress": "phase.started",
    "completed": "phase.completed",
    "failed": "phase.failed",
    "skipped": "phase.skipped",
}
_PHASE_END_STATUSES = ("completed", "failed", "skipped")


def default_state_path(project_path: str | Path) -> Path:
    """Canonical state file location for a project."""
    return Path(project_path) / STATE_DIRNAME / STATE_FILENAME


def write_state(path: str | Path, state: dict[str, Any]) -> None:
    """Write the state file under an exclusive lock (creates parent dirs)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+") as f:
        _lock_exclusive(f)
        f.seek(0)
        f.truncate()
        json.dump(state, f, indent=2, default=str)


def load_state(path: str | Path | None) -> dict[str, Any] | None:
    """Read the state file, or None if it is missing, empty or not valid JSON."""
    if not path:
        return None
    path = Path(path)
    try:
        if not path.is_file() or path.stat().st_size == 0:
            return None
        with open(path, "r") as f:
            _lock_shared(f)
            state = json.load(f)
        return state if isinstance(state, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def emit_phase_event(job_id: str, phase: str, phase_data: dict[str, Any]) -> None:
    """Record a phase status change in the local telemetry log. Never raises."""
    status = phase_data.get("status")
    event_type = _PHASE_EVENT_TYPES.get(status)
    if not event_type or not job_id:
        return
    event: dict[str, Any] = {
        "event_type": event_type,
        "job_id": job_id,
        "phase": phase,
        "status": status,
        "severity": "ERROR" if status == "failed" else "INFO",
    }
    for key in ("started_at", "ended_at", "error"):
        if phase_data.get(key):
            event[key] = phase_data[key]
    try:
        from scripts.telemetry.telemetry import emit_event
        emit_event({"event": event})
    except Exception as e:  # telemetry must never break state management
        log(f"Phase event emit failed (non-fatal): {e}")


def _phase_statuses(state: dict[str, Any]) -> dict[str, Any]:
    phases = state.get("phases") or {}
    return {k: v.get("status") for k, v in phases.items() if isinstance(v, dict)}


def _stamp_and_emit_phase_changes(state: dict[str, Any], before: dict[str, Any]) -> None:
    """Timestamp phases whose status changed and emit one event per change."""
    now = datetime.now(timezone.utc).isoformat()
    for phase, phase_data in (state.get("phases") or {}).items():
        if not isinstance(phase_data, dict):
            continue
        status = phase_data.get("status")
        if status == before.get(phase):
            continue
        if status == "in_progress":
            phase_data.setdefault("started_at", now)
        elif status in _PHASE_END_STATUSES:
            phase_data.setdefault("ended_at", now)
        emit_phase_event(str(state.get("job_id") or ""), phase, phase_data)


def generate_job_id() -> str:
    """Generate a short unique job ID."""
    return uuid.uuid4().hex[:8]


def init_state(input_data: dict[str, Any]) -> dict[str, Any]:
    """Initialize a new pipeline state."""
    project_path = input_data.get("project_path")
    if not project_path:
        error_exit("project_path is required for init", "input_validation")

    state = {
        "version": 2,
        "job_id": generate_job_id(),
        "project_path": project_path,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "jira_id": input_data.get("jira_id"),
        "model": input_data.get("model", "sonnet"),
        "severity_filter": input_data.get("severity_filter", "all"),
        "dry_run": input_data.get("dry_run", False),
        "generate_tests": input_data.get("generate_tests", True),
        "test_mode": input_data.get("test_mode", "fast"),
        "branch_name": None,
        "phases": {str(i): {"status": "pending"} for i in range(1, 10)},
        "vulnerabilities": [],
        "fix_results": [],
        "test_results": [],
        "infra_findings": [],
        "hybrid_findings": [],
        "manual_findings": [],
        "unresolved_items": [],
        "unexploitable_findings": [],
        "report_path": None,
        "pr_url": None,
        # JDK version detection (for CWE-937 version source routing)
        "jdk_version": input_data.get("jdk_version"),
        "is_java_project": input_data.get("is_java_project", False),
        "jdk_detection_source": input_data.get("jdk_detection_source"),
        "report_path": None,
        "pr_url": None,
        # Evidence & Accountability Framework (v2)
        "evidence_records": [],
        "verification_manifest_path": None,
        "wiz_baseline_scan_path": None,
        "wiz_available": None,
    }

    state_path = input_data.get("state_path") or default_state_path(project_path)
    try:
        write_state(state_path, state)
    except OSError as e:
        # Non-fatal: the caller still gets the state, but telemetry falls back to it.
        log(f"Failed to write state file {state_path} (non-fatal): {e}")
        return {"status": "success", "state": state, "state_path": None,
                "warning": f"state file not written: {e}"}

    return {"status": "success", "state": state, "state_path": str(state_path)}


def set_nested(obj: dict, dot_path: str, value: Any) -> None:
    """Set a value at a dot-separated path in a nested dict."""
    parts = dot_path.split(".")
    current = obj
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def update_state(input_data: dict[str, Any]) -> dict[str, Any]:
    """Update an existing pipeline state with dot-path updates.

    Uses file locking (fcntl.flock) to prevent concurrent write corruption.
    """
    state_path = input_data.get("state_path")
    updates = input_data.get("updates")

    if not state_path:
        error_exit("state_path is required for update", "input_validation")
    if not updates or not isinstance(updates, dict):
        error_exit("updates dict is required for update", "input_validation")

    path = Path(state_path)
    if not path.exists():
        error_exit(f"State file not found: {state_path}", "file_read")
    if path.stat().st_size == 0:
        error_exit(f"State file is empty (possibly corrupted): {state_path}", "file_read")

    # Use exclusive file lock to prevent concurrent write corruption
    with open(path, "r+") as f:
        try:
            _lock_exclusive(f)
        except OSError as e:
            error_exit(f"Failed to acquire file lock: {e}", "file_lock")

        try:
            state = json.load(f)
        except json.JSONDecodeError as e:
            error_exit(f"State file is not valid JSON: {e}", "json_parse")

        before = _phase_statuses(state)
        for dot_path, value in updates.items():
            set_nested(state, dot_path, value)
        _stamp_and_emit_phase_changes(state, before)

        # Write back atomically within lock
        f.seek(0)
        f.truncate()
        json.dump(state, f, indent=2, default=str)

    return {"status": "success", "state": state}


def append_state(input_data: dict[str, Any]) -> dict[str, Any]:
    """Append items to list fields (e.g. fix_results) without rewriting the state."""
    state_path = input_data.get("state_path")
    items = input_data.get("items")

    if not state_path:
        error_exit("state_path is required for append", "input_validation")
    if not items or not isinstance(items, dict):
        error_exit("items dict is required for append", "input_validation")

    path = Path(state_path)
    if not path.exists():
        error_exit(f"State file not found: {state_path}", "file_read")
    if path.stat().st_size == 0:
        error_exit(f"State file is empty (possibly corrupted): {state_path}", "file_read")

    with open(path, "r+") as f:
        try:
            _lock_exclusive(f)
        except OSError as e:
            error_exit(f"Failed to acquire file lock: {e}", "file_lock")

        try:
            state = json.load(f)
        except json.JSONDecodeError as e:
            error_exit(f"State file is not valid JSON: {e}", "json_parse")

        counts = {}
        for key, value in items.items():
            current = state.setdefault(key, [])
            if not isinstance(current, list):
                error_exit(f"State field {key} is not a list", "input_validation")
            new_items = value if isinstance(value, list) else [value]
            current.extend(new_items)
            counts[key] = len(current)

        f.seek(0)
        f.truncate()
        json.dump(state, f, indent=2, default=str)

    return {"status": "success", "state_path": str(path), "counts": counts}


def check_gate(input_data: dict[str, Any]) -> dict[str, Any]:
    """Check whether required phases are completed before entering a new phase."""
    state_path = input_data.get("state_path")
    phase = input_data.get("phase")
    required_phases = input_data.get("required_phases", [])

    if not state_path:
        error_exit("state_path is required for check_gate", "input_validation")
    if phase is None:
        error_exit("phase is required for check_gate", "input_validation")

    path = Path(state_path)
    if not path.exists():
        error_exit(f"State file not found: {state_path}", "file_read")
    if path.stat().st_size == 0:
        error_exit(f"State file is empty (possibly corrupted): {state_path}", "file_read")

    try:
        with open(path, "r") as f:
            _lock_shared(f)
            state = json.load(f)
    except json.JSONDecodeError as e:
        error_exit(f"State file is not valid JSON: {e}", "json_parse")

    phases = state.get("phases", {})
    failed_gates = []

    for req in required_phases:
        phase_data = phases.get(str(req), {})
        if phase_data.get("status") != "completed":
            failed_gates.append(req)

    if failed_gates:
        return {
            "status": "gate_failed",
            "phase": phase,
            "failed_prerequisites": failed_gates,
            "message": f"Phase {phase} cannot start: phases {failed_gates} not completed",
        }

    return {
        "status": "gate_passed",
        "phase": phase,
        "message": f"Phase {phase} gate check passed. All prerequisites completed.",
    }


def check_evidence_gate(input_data: dict[str, Any]) -> dict[str, Any]:
    """Check that evidence was collected for all successful fixes.

    Returns gate_passed if every successful fix has an evidence record,
    or gate_failed with the list of fix results missing evidence.
    """
    state_path = input_data.get("state_path")
    if not state_path:
        error_exit("state_path is required for check_evidence_gate", "input_validation")

    path = Path(state_path)
    if not path.exists():
        error_exit(f"State file not found: {state_path}", "file_read")
    if path.stat().st_size == 0:
        error_exit(f"State file is empty: {state_path}", "file_read")

    try:
        with open(path, "r") as f:
            _lock_shared(f)
            state = json.load(f)
    except json.JSONDecodeError as e:
        error_exit(f"State file is not valid JSON: {e}", "json_parse")

    fix_results = state.get("fix_results", [])
    evidence_records = state.get("evidence_records", [])

    # Build set of finding IDs that have evidence
    evidenced_ids = {
        r.get("finding_id", "") for r in evidence_records if r.get("finding_id")
    }

    # Check each successful fix has evidence
    missing_evidence = []
    for fix in fix_results:
        if fix.get("status") == "success":
            vuln_id = fix.get("vulnerability_id", "")
            if vuln_id and vuln_id not in evidenced_ids:
                missing_evidence.append(vuln_id)

    if missing_evidence:
        return {
            "status": "gate_failed",
            "message": f"Evidence missing for {len(missing_evidence)} successful fix(es)",
            "missing_evidence_for": missing_evidence,
        }

    return {
        "status": "gate_passed",
        "message": f"Evidence gate passed. {len(evidence_records)} evidence records for {len([f for f in fix_results if f.get('status') == 'success'])} successful fixes.",
    }


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    action = input_data.get("action")
    if not action:
        error_exit("action is required (init, update, append, check_gate, or check_evidence_gate)", "input_validation")

    if action == "init":
        result = init_state(input_data)
    elif action == "update":
        result = update_state(input_data)
    elif action == "append":
        result = append_state(input_data)
    elif action == "check_gate":
        result = check_gate(input_data)
    elif action == "check_evidence_gate":
        result = check_evidence_gate(input_data)
    else:
        error_exit(f"Unknown action: {action}. Must be init, update, append, check_gate, or check_evidence_gate", "input_validation")

    write_json_output(result, start_time=start_time)


if __name__ == "__main__":
    main()
