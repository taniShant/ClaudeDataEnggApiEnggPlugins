#!/usr/bin/env python3
"""Run recorder — writes a denormalized run summary to ~/.detox/telemetry/runs.jsonl.

Called at pipeline end (success or failure) to record one complete run summary line
that powers the /barclays-buk-detox:usage dashboard.

Input (JSON stdin):
  {"action": "record", "job_id": "...", "state_path": "{project_path}/.detox/state.json",
   "state": {...optional overrides...}, "identity": {...}, "ended_at": "ISO8601",
   "report_path": "optional — defaults to state.report_path"}

Counts come from the state file written by prepare_pipeline.py / pipeline_state.py
(state_path, else {state.project_path}/.detox/state.json); a file whose job_id doesn't
match this run's `job_id` (another run in the same folder) is ignored. A pasted `state` only fills
fields the file leaves empty, so a hand-built summary can't zero out the counts. A run
whose counts can't be right (PR created but no findings recorded) is flagged
`state_incomplete` and reported with ⚠️ rather than ✅.

Output (JSON stdout):
  {"status": "success", "run_path": "~/.detox/telemetry/runs.jsonl", "job_id": "...",
   "telemetry_message": "...", "report_telemetry": {"updated": true, "reason": "updated"}}

After recording, the DETOX-REMEDIATION-REPORT `**Telemetry:**` line is backfilled
deterministically with telemetry_message (see backfill_report_telemetry).
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output, log, locked_append, sanitize_pat
from scripts.core.errors import error_exit
from scripts.parsers.classify_findings import SEVERITY_SETS
from scripts.telemetry.version import PLUGIN_VERSION
from scripts.state.pipeline_state import default_state_path, load_state

# Constants
TELEMETRY_DIR = Path.home() / ".detox" / "telemetry"
RUNS_FILE = TELEMETRY_DIR / "runs.jsonl"


def compute_duration_ms(started_at: str | None, ended_at: str | None) -> int | None:
    """Compute duration in milliseconds between two ISO8601 timestamps."""
    if not started_at or not ended_at:
        return None
    try:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(ended_at)
        return int((end - start).total_seconds() * 1000)
    except (ValueError, TypeError):
        return None


def extract_repo_name(project_path: str | None, identity: dict[str, Any] | None) -> str:
    """Extract repo name from identity (preferred) or project_path fallback."""
    if identity and identity.get("repo_name"):
        return identity["repo_name"]
    if project_path:
        return Path(project_path).name
    return "unknown"


def vuln_cwe_id(vuln: dict[str, Any]) -> str | None:
    """CWE ID for a vulnerability. WIZ SCA findings carry CVEs but no CWE, so a
    dependency finding without one is reported as CWE-937 (vulnerable components),
    matching how the fix/evidence stages label it."""
    cwe_id = vuln.get("cwe_id")
    if not cwe_id and vuln.get("remediation_type") == "dependency":
        return "CWE-937"
    return cwe_id


def extract_cwes_targeted(
    vulnerabilities: list[dict[str, Any]],
    fix_results: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Extract unique CWE IDs from vulnerability list.

    Falls back to the fix result's cwe_id when the report gave a finding no CWE
    but the fix agent assigned one.
    """
    fix_cwes = {f.get("vulnerability_id"): f.get("cwe_id") for f in fix_results or []
                if isinstance(f, dict) and f.get("vulnerability_id")}
    cwes = set()
    for vuln in vulnerabilities:
        cwe_id = vuln_cwe_id(vuln) or fix_cwes.get(vuln.get("id"))
        if cwe_id:
            cwes.add(cwe_id)
    return sorted(cwes)


def count_by_field(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    """Count items grouped by a field value."""
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(field, "unknown"))
        counts[value] = counts.get(value, 0) + 1
    return counts


def _unresolved_by_reason(unresolved_items: list[Any]) -> dict[str, int]:
    """Count Stage 8 unresolved_items by remediation_type ("unspecified" if absent).

    Not reconciled to vulns_deferred: unresolved_items also includes attempted fixes
    (hybrid, needs_manual_review), and is empty if the run aborts before Stage 8.
    """
    reasons: dict[str, int] = {}
    for item in unresolved_items:
        reason = item.get("remediation_type") if isinstance(item, dict) else None
        reason = str(reason) if reason else "unspecified"
        reasons[reason] = reasons.get(reason, 0) + 1
    return reasons


def _unverified_by_reason(fix_results: list[dict[str, Any]]) -> dict[str, int]:
    """Bucket attempted fixes that are NOT validated-clean, by a status/validation reason.

    Reconciles to (fixes_attempted − fixes_validated_clean):
      - status == success AND validation_passed is True  -> validated clean (NOT counted here)
      - status == success AND validation_passed is False  -> "still_detected"
      - status == success AND validation_passed is None    -> "not_validated"
      - status == failed                                   -> "fix_failed"
      - status == skipped                                  -> "skipped"
      - any other / missing status                         -> "unknown_status"
    """
    reasons: dict[str, int] = {}
    for f in fix_results:
        status = f.get("status")
        validated = f.get("validation_passed")
        if status == "success" and validated is True:
            continue  # validated clean — not unverified
        if status == "success" and validated is False:
            reason = "still_detected"
        elif status == "success":  # validated is None/absent
            reason = "not_validated"
        elif status == "failed":
            reason = "fix_failed"
        elif status == "skipped":
            reason = "skipped"
        else:
            reason = "unknown_status"
        reasons[reason] = reasons.get(reason, 0) + 1
    return reasons


NO_LLM_REASON = "LLM didn't give a reason for not fixing this"

# State arrays where the orchestrator may record an LLM-supplied `unfixed_reason`, in lookup order.
_REASON_SOURCES = ("unresolved_items", "infra_findings", "manual_findings",
                   "hybrid_findings", "unexploitable_findings")


def _is_unfixed(fix: dict[str, Any] | None) -> bool:
    """Never attempted, attempt didn't succeed, or re-scan still detects it."""
    return fix is None or fix.get("status") != "success" or fix.get("validation_passed") is False


def _llm_reason(*sources: dict[str, Any]) -> str:
    """First non-empty `unfixed_reason` from the given records, verbatim (credentials redacted)."""
    for src in sources:
        reason = src.get("unfixed_reason")
        if isinstance(reason, str) and reason.strip():
            return sanitize_pat(reason)
    return NO_LLM_REASON


def build_unresolved_vulns(state: dict[str, Any]) -> list[dict[str, Any]]:
    """One record per in-scope finding not fixed, with the LLM's reason exactly as given.

    Severity-filtered findings and dry runs are excluded.
    """
    if state.get("dry_run"):
        return []

    allowed = SEVERITY_SETS.get(str(state.get("severity_filter") or "all").lower(), SEVERITY_SETS["all"])
    fixes = {f.get("vulnerability_id"): f for f in state.get("fix_results") or []
             if isinstance(f, dict) and f.get("vulnerability_id")}
    by_source = {
        key: {e.get("id"): e for e in state.get(key) or [] if isinstance(e, dict) and e.get("id")}
        for key in _REASON_SOURCES
    }
    unresolved = by_source["unresolved_items"]

    def sources_for(vid: Any, vuln: dict[str, Any]) -> list[dict[str, Any]]:
        # Stage 8 summary first, then the fix attempt, then Stage 3/7 buckets, then the vuln itself.
        found = [unresolved.get(vid, {}), fixes.get(vid, {})]
        found += [by_source[key].get(vid, {}) for key in _REASON_SOURCES[1:]]
        return found + [vuln]

    records: list[dict[str, Any]] = []
    seen: set[Any] = set()
    for vuln in state.get("vulnerabilities") or []:
        if not isinstance(vuln, dict):
            continue
        if (vuln.get("severity") or "medium").lower() not in allowed:
            continue
        vid = vuln.get("id")
        if vid not in unresolved and not _is_unfixed(fixes.get(vid)):
            continue
        seen.add(vid)
        records.append(_unresolved_record(vuln, unresolved.get(vid, {}), _llm_reason(*sources_for(vid, vuln))))

    # Unresolved items not in vulnerabilities (e.g. threat-model attack paths).
    for vid, item in unresolved.items():
        if vid not in seen:
            records.append(_unresolved_record({}, item, _llm_reason(item)))
    return records


def _unresolved_record(vuln: dict[str, Any], item: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "vuln_id": vuln.get("id") or item.get("id"),
        "cwe_id": vuln_cwe_id(vuln) or vuln_cwe_id(item),
        "severity": vuln.get("severity") or item.get("severity"),
        "remediation_type": vuln.get("remediation_type") or item.get("remediation_type"),
        "reason": reason,
    }


def compute_phase_durations(phases: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Compute duration for each phase from its timestamps."""
    result = {}
    for phase_key, phase_data in phases.items():
        if not isinstance(phase_data, dict):
            continue
        phase_info: dict[str, Any] = {
            "status": phase_data.get("status", "unknown"),
        }
        started = phase_data.get("started_at")
        ended = phase_data.get("ended_at")
        if started:
            phase_info["started_at"] = started
        if ended:
            phase_info["ended_at"] = ended
        duration = compute_duration_ms(started, ended)
        if duration is not None:
            phase_info["duration_ms"] = duration
        result[phase_key] = phase_info
    return result


FLAG_STATE_INCOMPLETE = "state_incomplete"
FLAG_STATE_FILE_MISSING = "state_file_missing"


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def merge_state(file_state: dict[str, Any], pasted: dict[str, Any]) -> dict[str, Any]:
    """File state wins; pasted values only fill fields the file leaves empty.

    Phases merge per phase: a pasted status replaces one the file still has as pending
    (the orchestrator may not have pushed every late phase update to the file).
    """
    merged = dict(file_state)
    for key, value in pasted.items():
        if key == "phases" and isinstance(value, dict):
            phases = dict(file_state.get("phases") or {})
            for phase, data in value.items():
                current = phases.get(str(phase))
                if not isinstance(current, dict) or current.get("status") in (None, "pending"):
                    phases[str(phase)] = data
            merged["phases"] = phases
        elif _is_empty(merged.get(key)) and not _is_empty(value):
            merged[key] = value
    return merged


def resolve_state(input_data: dict[str, Any]) -> dict[str, Any]:
    """Return input_data with `state` resolved from the state file.

    Adds FLAG_STATE_FILE_MISSING to flags_raised when no state file could be read.
    """
    pasted = input_data.get("state") or {}
    state_path = input_data.get("state_path")
    if not state_path and pasted.get("project_path"):
        state_path = default_state_path(pasted["project_path"])

    file_state = load_state(state_path)
    expected_job = input_data.get("job_id") or pasted.get("job_id")
    if file_state and expected_job and file_state.get("job_id") != expected_job:
        # Left over from another run in the same repo — never record its counts.
        log(f"State file {state_path} is for job {file_state.get('job_id')}, "
            f"not {expected_job} — ignoring it")
        file_state = None
    resolved = dict(input_data)
    if file_state is None:
        log(f"State file not readable ({state_path}) — using the state passed in")
        resolved["flags_raised"] = list(input_data.get("flags_raised") or []) + [FLAG_STATE_FILE_MISSING]
        return resolved

    resolved["state"] = merge_state(file_state, pasted)
    return resolved


def build_run_record(input_data: dict[str, Any]) -> dict[str, Any]:
    """Build a denormalized run summary from pipeline state and identity."""
    state = input_data.get("state", {})
    identity = input_data.get("identity", {})
    ended_at = input_data.get("ended_at") or datetime.now(timezone.utc).isoformat()

    started_at = state.get("started_at")
    total_duration_ms = compute_duration_ms(started_at, ended_at)

    project_path = state.get("project_path", "")
    repo_name = extract_repo_name(project_path, identity)

    # Extract vulnerability metrics
    vulnerabilities = state.get("vulnerabilities", [])
    fix_results = state.get("fix_results", [])
    test_results = state.get("test_results", [])

    # Count fix outcomes
    fixes_succeeded = sum(1 for f in fix_results if f.get("status") == "success")
    fixes_failed = sum(1 for f in fix_results if f.get("status") == "failed")
    fixes_skipped = sum(1 for f in fix_results if f.get("status") == "skipped")
    retries_total = sum(f.get("retry_count", 0) for f in fix_results)

    # Count validation results
    validation_pass = sum(1 for f in fix_results if f.get("validation_passed") is True)
    validation_fail = sum(1 for f in fix_results if f.get("validation_passed") is False)
    validation_total = validation_pass + validation_fail
    validation_pass_rate = (validation_pass / validation_total) if validation_total > 0 else None

    # Count test results
    tests_generated = len(test_results)
    tests_passed = sum(1 for t in test_results if t.get("status") == "success")
    tests_failed = sum(1 for t in test_results if t.get("status") in ("failed", "error"))

    # Fixes that passed BOTH stages: the edit applied (Stage 4 status=success)
    # AND the post-fix re-scan confirmed the vuln is gone (Stage 5 validation_passed=True).
    # This is the honest "verified fixed" count — distinct from fixes_succeeded, which
    # only means the edit was applied, not that validation later confirmed it.
    fixes_validated_clean = sum(
        1 for f in fix_results
        if f.get("status") == "success" and f.get("validation_passed") is True
    )

    # Full accounting so counts reconcile to vulns_total:
    #   vulns_total = fixes_attempted + vulns_deferred
    # vulns_deferred = vulns found but never entered the fix pipeline (deferred to
    # manual review / major upgrade / out of auto-remediation scope).
    vulns_count = len(vulnerabilities)
    fixes_attempted = len(fix_results)
    vulns_deferred = max(vulns_count - fixes_attempted, 0)

    vulns_deferred_by_reason = _unresolved_by_reason(state.get("unresolved_items") or [])

    # WHY attempted fixes aren't verified-clean — reconciles to (attempted − validated_clean).
    fixes_unverified_by_reason = _unverified_by_reason(fix_results)

    # Derived technical rates (ratio in [0,1], or None when the denominator is 0).
    # Same ratio-or-None idiom as validation_pass_rate above; the exporter's
    # _flatten_value drops None labels so a rate is only emitted when meaningful.
    #   remediation_rate         = edits applied / vulns found     (Stage 4 view)
    #   verified_remediation_rate = BOTH-stage verified / vulns found (strictest, truest)
    remediation_rate = (fixes_succeeded / vulns_count) if vulns_count > 0 else None
    verified_remediation_rate = (fixes_validated_clean / vulns_count) if vulns_count > 0 else None
    fix_success_rate = (fixes_succeeded / fixes_attempted) if fixes_attempted > 0 else None
    fix_failure_rate = (fixes_failed / fixes_attempted) if fixes_attempted > 0 else None
    deferral_rate = (vulns_deferred / vulns_count) if vulns_count > 0 else None
    tests_run = tests_passed + tests_failed
    test_pass_rate = (tests_passed / tests_run) if tests_run > 0 else None

    # Severity distribution
    vulns_by_severity = count_by_field(vulnerabilities, "severity")

    # Type distribution
    vulns_by_type = count_by_field(vulnerabilities, "remediation_type")

    # Phase durations
    phases = state.get("phases", {})
    phase_durations = compute_phase_durations(phases)

    # Determine pipeline status
    pipeline_status = "completed"
    errors: list[dict[str, Any]] = []
    for phase_key, phase_data in phases.items():
        if isinstance(phase_data, dict) and phase_data.get("status") == "failed":
            pipeline_status = "failed"
            error_info = phase_data.get("error")
            if error_info:
                errors.append({"phase": phase_key, "error": error_info})

    # Override with explicit status if provided
    if input_data.get("status"):
        pipeline_status = input_data["status"]

    # Sanity check: a PR or fix results with no findings means the counts were lost.
    flags_raised = list(input_data.get("flags_raised") or [])
    if not vulnerabilities and (state.get("pr_url") or fix_results):
        flags_raised.append(FLAG_STATE_INCOMPLETE)

    run_record = {
        "job_id": state.get("job_id", "unknown"),
        "command": input_data.get("command", "remediate"),
        "started_at": started_at,
        "ended_at": ended_at,
        "total_duration_ms": total_duration_ms,
        "status": pipeline_status,
        "user_name": identity.get("user_name", "unknown"),
        "user_email": identity.get("user_email", ""),
        "cio": identity.get("cio"),
        "ci_job_id": identity.get("ci_job_id"),
        "model": state.get("model", "sonnet"),
        "project_path": project_path,
        "repo_name": repo_name,
        "severity_filter": state.get("severity_filter", "all"),
        "dry_run": state.get("dry_run", False),
        "vulns_total": vulns_count,
        "vulns_by_severity": vulns_by_severity,
        "vulns_by_type": vulns_by_type,
        "cwes_targeted": extract_cwes_targeted(vulnerabilities, fix_results),
        "fixes_attempted": fixes_attempted,
        "fixes_succeeded": fixes_succeeded,
        "fixes_failed": fixes_failed,
        "fixes_skipped": fixes_skipped,
        "fixes_validated_clean": fixes_validated_clean,
        "vulns_deferred": vulns_deferred,
        "vulns_deferred_by_reason": vulns_deferred_by_reason,
        "fixes_unverified_by_reason": fixes_unverified_by_reason,
        "unresolved_vulns": build_unresolved_vulns(state),
        "retries_total": retries_total,
        "remediation_rate": remediation_rate,
        "verified_remediation_rate": verified_remediation_rate,
        "fix_success_rate": fix_success_rate,
        "fix_failure_rate": fix_failure_rate,
        "deferral_rate": deferral_rate,
        "validation_pass_count": validation_pass,
        "validation_fail_count": validation_fail,
        "validation_pass_rate": validation_pass_rate,
        "tests_generated": tests_generated,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "test_pass_rate": test_pass_rate,
        "pr_created": bool(state.get("pr_url")),
        "pr_url": state.get("pr_url"),
        "agent_invocations": input_data.get("agent_invocations", 0),
        "flags_raised": flags_raised,
        "self_check_passed": input_data.get("self_check_passed", True),
        "phases": phase_durations,
        "errors": errors,
        "plugin_version": PLUGIN_VERSION,
    }

    return run_record


def _telemetry_status_message(export_result: dict[str, Any]) -> str:
    """Build a user-visible status message from the Observe export result."""
    status = export_result.get("status", "unknown")
    if status == "success":
        job_id = export_result.get("job_id", "")
        events_export = export_result.get("events_export") or {}
        if events_export.get("status") == "success" and events_export.get("exported_count"):
            n = events_export["exported_count"]
            return f"📊 Telemetry exported to Observe ({job_id}, {n} events)"
        return f"📊 Telemetry exported to Observe ({job_id})"
    # error (fire-and-forget — never blocks the pipeline)
    error = export_result.get("error", "unknown error")
    return f"⚠️  Telemetry export failed — {error}"


def export_to_otel(run_record: dict[str, Any]) -> dict[str, Any] | None:
    """Fire-and-forget: at run end, send the whole run to Observe in ONE batch.

    Emits the denormalized run summary (`detox.pipeline_run`) AND every granular
    per-phase event for this job_id — all in a single gRPC OTLP round-trip to
    Barclays Observe (full parity with the old per-event export, one flush). The
    barclays_* identity rides on each record.

    Returns the export result (with an 'events_export' count) or None if export
    was skipped/failed. This must NEVER block or raise — telemetry is optional.
    """
    try:
        from scripts.telemetry.otel_exporter import export_run_and_events

        job_id = run_record.get("job_id", "")
        events = []
        if job_id and job_id != "unknown":
            from scripts.telemetry.telemetry import read_events_for_job
            events = read_events_for_job(job_id)

        result = export_run_and_events(run_record, events)

        print(_telemetry_status_message(result), file=sys.stderr)
        log(f"Telemetry export: {result.get('status', 'unknown')} "
            f"({result.get('exported_count', 0)} records)")
        return result
    except Exception as e:
        print(f"⚠️  Telemetry export failed (non-fatal): {e}", file=sys.stderr)
        log(f"Telemetry export failed (non-fatal): {e}")
        return None


def _job_already_recorded(job_id: str) -> bool:
    """Check if a job_id already exists in runs.jsonl.

    Scans the last 50 lines for performance.  This is an idempotency guard
    so that defense-in-depth telemetry calls (orchestrator + command layer)
    do not produce duplicate records.
    """
    if not RUNS_FILE.exists():
        return False
    try:
        lines = RUNS_FILE.read_text().strip().split("\n")
        for line in lines[-50:]:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if record.get("job_id") == job_id:
                    return True
            except json.JSONDecodeError:
                continue
    except OSError:
        pass
    return False


def _build_telemetry_message(
    local_status: str,
    export_result: dict[str, Any] | None,
    incomplete: bool = False,
) -> str:
    """Build a one-line telemetry status message for the pipeline completion banner.

    ✅ only when Observe actually accepted a complete run; ⚠️ whenever it did not.
    Returns a short human-readable string like:
      "✅ Exported to Observe"
      "⚠️  Exported to Observe (incomplete counts)"
      "⚠️  Saved locally (Observe export failed)"
      "⚠️  Saved locally"
      "⚠️  Local write failed — telemetry not recorded"
    """
    if local_status != "success":
        return "⚠️  Local write failed — telemetry not recorded"

    if not export_result:
        # Export never ran (or crashed) — the run is only on disk.
        return "⚠️  Saved locally"

    export_status = export_result.get("status", "unknown")
    if export_status == "success":
        if incomplete:
            return "⚠️  Exported to Observe (incomplete counts)"
        return "✅ Exported to Observe"
    # error (fire-and-forget — local write already succeeded)
    return "⚠️  Saved locally (Observe export failed)"


REPORT_TELEMETRY_PENDING = "pending (recorded at pipeline completion)"
_REPORT_TELEMETRY_LINE = re.compile(r"^\*\*Telemetry:\*\*[^\n]*$", re.MULTILINE)
_REPORT_JOB_ID = re.compile(r"Job ID:\**\s*`?([A-Za-z0-9._-]+)")


def backfill_report_telemetry(
    report_path: str | None,
    job_id: str,
    message: str,
    only_if_pending: bool = False,
) -> dict[str, Any]:
    """Replace the report's `**Telemetry:**` header line with the real outcome.

    Stage 8 writes the line as "pending" because telemetry runs later, at
    Pipeline Completion. Doing the replacement here (not by the LLM) guarantees
    the report never stays stale. Stale-report guard: the report's footer
    `Job ID` must match this run, so a report left over from an earlier run is
    never stamped with this run's outcome. With only_if_pending, a line that
    already holds a real outcome is left alone (dedup calls must not overwrite
    the authoritative first result).

    Returns {"updated": bool, "reason": str}. Never raises.
    """
    if not report_path:
        return {"updated": False, "reason": "no report_path"}
    path = Path(report_path)
    try:
        if not path.is_file():
            return {"updated": False, "reason": "report not found"}
        text = path.read_text(encoding="utf-8")

        ids = _REPORT_JOB_ID.findall(text)
        if not ids:
            return {"updated": False, "reason": "job id not found in report"}
        if job_id not in ids:
            return {"updated": False, "reason": f"job id mismatch (report is for {ids[-1]}) — stale report"}

        line = _REPORT_TELEMETRY_LINE.search(text)
        if not line:
            return {"updated": False, "reason": "telemetry line not found"}
        if only_if_pending and REPORT_TELEMETRY_PENDING not in line.group(0):
            return {"updated": False, "reason": "already resolved"}

        new_line = f"**Telemetry:** {message}"
        if line.group(0) != new_line:
            path.write_text(text[:line.start()] + new_line + text[line.end():], encoding="utf-8")
        return {"updated": True, "reason": "updated"}
    except (OSError, UnicodeError) as e:
        log(f"Report telemetry backfill failed (non-fatal): {e}")
        return {"updated": False, "reason": f"error: {e}"}


def _report_path(input_data: dict[str, Any]) -> str | None:
    """Report path: explicit input wins, else state.report_path set at Stage 8."""
    return input_data.get("report_path") or (input_data.get("state") or {}).get("report_path")


def record_run(input_data: dict[str, Any]) -> dict[str, Any]:
    """Record a pipeline run to the runs.jsonl file, then backfill the report."""
    input_data = resolve_state(input_data)
    result = _record_run(input_data)
    job_id = str(result.get("job_id") or "unknown")
    result["report_telemetry"] = backfill_report_telemetry(
        _report_path(input_data),
        job_id,
        result["telemetry_message"],
        only_if_pending=bool(result.get("deduplicated")),
    )
    return result


def _record_run(input_data: dict[str, Any]) -> dict[str, Any]:
    TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)

    run_record = build_run_record(input_data)
    job_id = run_record.get("job_id", "unknown")

    # Idempotency guard: if this job_id was already recorded, skip BOTH the
    # local write and the OTel export. The first caller (the orchestrator, with
    # full identity + vulnerability data) already exported the authoritative
    # record. Re-exporting here would push a SECOND OTLP/S3 record for the same
    # job — and a defense-in-depth fallback caller (e.g. the remediate command)
    # often passes an identity-less, empty record, producing bogus
    # cio=null / 0-vuln duplicates on the dashboard. One job_id -> one export.
    if _job_already_recorded(job_id):
        log(f"Job {job_id} already recorded — skipping duplicate write and export")
        print(f"📊 Telemetry already recorded for job {job_id}", file=sys.stderr)
        return {
            "status": "success",
            "run_path": str(RUNS_FILE),
            "job_id": job_id,
            "deduplicated": True,
            "telemetry_message": "✅ Telemetry already recorded (deduplicated)",
        }

    try:
        with locked_append(RUNS_FILE) as f:
            f.write(json.dumps(run_record, default=str) + "\n")
        print(f"📊 Telemetry recorded locally → {RUNS_FILE}", file=sys.stderr)
    except OSError as e:
        print(f"⚠️  Failed to write telemetry run record: {e}", file=sys.stderr)
        log(f"Failed to write run record (non-fatal): {e}")
        return {
            "status": "error",
            "error": f"Write failed: {e}",
            "job_id": run_record.get("job_id"),
            "telemetry_message": _build_telemetry_message("error", None),
        }

    # Fire-and-forget: export to the Observe platform for dashboard visibility
    export_result = export_to_otel(run_record)

    incomplete = FLAG_STATE_INCOMPLETE in run_record["flags_raised"]
    if incomplete:
        print("⚠️  Run counts look incomplete (PR/fixes recorded but no findings) — "
              "flagged state_incomplete", file=sys.stderr)
    result = {
        "status": "success",
        "run_path": str(RUNS_FILE),
        "job_id": run_record.get("job_id"),
        "telemetry_message": _build_telemetry_message("success", export_result, incomplete),
    }
    if export_result:
        result["export"] = export_result
    if run_record["flags_raised"]:
        result["flags_raised"] = run_record["flags_raised"]

    return result


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    action = input_data.get("action")
    if not action:
        error_exit("action is required (record)", "input_validation")

    if action == "record":
        result = record_run(input_data)
    else:
        error_exit(f"Unknown action: {action}. Must be 'record'", "input_validation")

    write_json_output(result, start_time=start_time)


if __name__ == "__main__":
    main()
