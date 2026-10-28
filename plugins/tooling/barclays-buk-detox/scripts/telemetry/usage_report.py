#!/usr/bin/env python3
"""Usage report generator for the Detox pipeline.

Reads ~/.detox/telemetry/runs.jsonl, applies time filters, computes aggregates,
and outputs in table/json/html format.

Input (JSON stdin):
  {"period": "30d", "group_by": "user|project|cwe|repo", "format": "table|json|html",
   "output": "/optional/path/to/write/report"}

Output (JSON stdout):
  {"status": "success", "report": {...aggregated metrics...}, "rendered": "...formatted output..."}
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from string import Template
from typing import Any

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output, log
from scripts.core.errors import error_exit
from scripts.telemetry.version import PLUGIN_VERSION

# Constants
TELEMETRY_DIR = Path.home() / ".detox" / "telemetry"
RUNS_FILE = TELEMETRY_DIR / "runs.jsonl"
REPORTS_DIR = TELEMETRY_DIR / "reports"


def parse_period(period_str: str) -> tuple[datetime, datetime]:
    """Parse period string into (start, end) datetimes."""
    end = datetime.now(timezone.utc)
    period_str = period_str.strip().lower()

    if period_str == "all":
        start = datetime.min.replace(tzinfo=timezone.utc)
        return start, end

    unit = period_str[-1]
    try:
        value = int(period_str[:-1])
    except (ValueError, IndexError):
        error_exit(f"Invalid period: {period_str}. Use Nd (e.g., 7d, 30d)", "input_validation")

    if unit == "d":
        start = end - timedelta(days=value)
    else:
        error_exit(f"Unknown unit: {unit}. Use 'd' for days", "input_validation")

    return start, end


def load_runs(after: datetime) -> list[dict[str, Any]]:
    """Load run records from JSONL, filtered by time and deduplicated by job_id."""
    if not RUNS_FILE.exists():
        return []

    runs = []
    try:
        with open(RUNS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    run = json.loads(line)
                except json.JSONDecodeError:
                    continue
                # Time filter
                started = run.get("started_at", "")
                try:
                    ts = datetime.fromisoformat(started)
                    if ts < after:
                        continue
                except (ValueError, TypeError):
                    continue
                runs.append(run)
    except OSError as e:
        log(f"Failed to read runs file: {e}")

    # Deduplicate by job_id — keep last occurrence (most complete data).
    # Records without a job_id are always preserved.
    seen: dict[str, int] = {}
    has_dupes = False
    for i, run in enumerate(runs):
        jid = run.get("job_id", "")
        if jid:
            if jid in seen:
                has_dupes = True
            seen[jid] = i
    if has_dupes:
        keep = set(seen.values())
        runs = [r for i, r in enumerate(runs)
                if i in keep or not r.get("job_id")]

    return runs


def compute_aggregates(runs: list[dict[str, Any]], period_str: str, start: datetime, end: datetime) -> dict[str, Any]:
    """Compute all aggregate metrics from run records."""
    if not runs:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "period": {"start": start.isoformat(), "end": end.isoformat(), "label": period_str, "days": (end - start).days},
            "usage": {"total_runs": 0, "unique_users": 0, "unique_repos": 0, "runs_per_day_avg": 0},
            "performance": {},
            "effectiveness": {},
            "security_posture": {},
            "cost": {},
            "onboarding": {"total_repos_onboarded": 0, "newly_onboarded_this_period": 0, "repos_with_first_run": []},
            "errors": {},
            "repos": [],
            "users": [],
            "contributing_step5": {"invocation_count": 0, "flag_frequency": 0, "self_check_pass_rate": 0},
        }

    total_runs = len(runs)
    days = max((end - start).days, 1)

    # Usage
    users = set(r.get("user_name", "unknown") for r in runs)
    repos = set(r.get("repo_name", "unknown") for r in runs)

    # Most active
    user_counts = Counter(r.get("user_name", "unknown") for r in runs)
    repo_counts = Counter(r.get("repo_name", "unknown") for r in runs)
    most_active_user = user_counts.most_common(1)[0] if user_counts else ("unknown", 0)
    most_active_repo = repo_counts.most_common(1)[0] if repo_counts else ("unknown", 0)

    # Performance
    durations = [r["total_duration_ms"] for r in runs if r.get("total_duration_ms") is not None]
    phase_durations: dict[str, list[int]] = {}
    for run in runs:
        phases = run.get("phases", {})
        for phase_key, phase_data in phases.items():
            if isinstance(phase_data, dict) and phase_data.get("duration_ms") is not None:
                phase_durations.setdefault(phase_key, []).append(phase_data["duration_ms"])

    performance: dict[str, Any] = {}
    if durations:
        performance = {
            "avg_duration_ms": int(statistics.mean(durations)),
            "median_duration_ms": int(statistics.median(durations)),
            "p95_duration_ms": int(sorted(durations)[int(len(durations) * 0.95)] if len(durations) > 1 else durations[0]),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "by_phase": {k: {"median_ms": int(statistics.median(v))} for k, v in phase_durations.items() if v},
        }

    # Effectiveness
    total_cwes = sum(r.get("vulns_total", 0) for r in runs)
    total_fixes_attempted = sum(r.get("fixes_attempted", 0) for r in runs)
    total_fixes_succeeded = sum(r.get("fixes_succeeded", 0) for r in runs)
    total_validation_pass = sum(r.get("validation_pass_count", 0) for r in runs)
    total_validation_fail = sum(r.get("validation_fail_count", 0) for r in runs)
    total_tests_generated = sum(r.get("tests_generated", 0) for r in runs)
    total_tests_passed = sum(r.get("tests_passed", 0) for r in runs)
    total_tests_failed = sum(r.get("tests_failed", 0) for r in runs)

    total_fixes_failed = sum(r.get("fixes_failed", 0) for r in runs)
    validation_total = total_validation_pass + total_validation_fail
    effectiveness = {
        "cwes_remediated": total_fixes_succeeded,
        "vulns_found_total": total_cwes,
        "remediation_rate": round(total_fixes_succeeded / total_cwes, 3) if total_cwes else 0,
        "fix_success_rate": round(total_fixes_succeeded / total_fixes_attempted, 3) if total_fixes_attempted else 0,
        "fix_failure_rate": round(total_fixes_failed / total_fixes_attempted, 3) if total_fixes_attempted else 0,
        "deferral_rate": round((total_cwes - total_fixes_attempted) / total_cwes, 3) if total_cwes else 0,
        "validation_pass_rate": round(total_validation_pass / validation_total, 3) if validation_total else 0,
        "test_pass_rate": round(total_tests_passed / (total_tests_passed + total_tests_failed), 3) if (total_tests_passed + total_tests_failed) else 0,
        "tests_generated": total_tests_generated,
    }

    # Security posture — CWE frequency
    cwe_counter: Counter[str] = Counter()
    severity_counter: Counter[str] = Counter()
    deferred_reason_counter: Counter[str] = Counter()
    unverified_reason_counter: Counter[str] = Counter()
    for run in runs:
        for cwe in run.get("cwes_targeted", []):
            cwe_counter[cwe] += 1
        for sev, count in run.get("vulns_by_severity", {}).items():
            severity_counter[sev] += count
        for reason, count in run.get("vulns_deferred_by_reason", {}).items():
            deferred_reason_counter[reason] += count
        for reason, count in run.get("fixes_unverified_by_reason", {}).items():
            unverified_reason_counter[reason] += count

    security_posture = {
        "top_cwes": [{"cwe": cwe, "count": count} for cwe, count in cwe_counter.most_common(10)],
        "severity_distribution": dict(severity_counter),
        "deferred_by_reason": dict(deferred_reason_counter),
        "unverified_by_reason": dict(unverified_reason_counter),
    }

    # Cost
    total_invocations = sum(r.get("agent_invocations", 0) for r in runs)
    model_counter = Counter(r.get("model", "sonnet") for r in runs)
    cost = {
        "total_agent_invocations": total_invocations,
        "model_distribution": dict(model_counter),
    }

    # Errors
    failure_runs = [r for r in runs if r.get("status") == "failed"]
    error_reasons: Counter[str] = Counter()
    for run in failure_runs:
        for err in run.get("errors", []):
            reason = err.get("error", "unknown")[:50]
            error_reasons[reason] += 1
    total_retries = sum(r.get("retries_total", 0) for r in runs)

    errors = {
        "failure_count": len(failure_runs),
        "failure_rate": round(len(failure_runs) / total_runs, 3) if total_runs else 0,
        "by_reason": dict(error_reasons.most_common(5)),
        "total_retries": total_retries,
    }

    # Per-repo breakdown
    repo_data: dict[str, dict[str, Any]] = {}
    for run in runs:
        name = run.get("repo_name", "unknown")
        if name not in repo_data:
            repo_data[name] = {"name": name, "runs": 0, "success": 0, "cwes_fixed": 0, "users": set()}
        repo_data[name]["runs"] += 1
        if run.get("status") == "completed":
            repo_data[name]["success"] += 1
        repo_data[name]["cwes_fixed"] += run.get("fixes_succeeded", 0)
        repo_data[name]["users"].add(run.get("user_name", "unknown"))

    repos_list = []
    for rd in sorted(repo_data.values(), key=lambda x: x["runs"], reverse=True):
        repos_list.append({
            "name": rd["name"],
            "runs": rd["runs"],
            "success_rate": round(rd["success"] / rd["runs"], 3) if rd["runs"] else 0,
            "cwes_fixed": rd["cwes_fixed"],
            "unique_users": len(rd["users"]),
        })

    # Per-user breakdown
    user_data: dict[str, dict[str, Any]] = {}
    for run in runs:
        name = run.get("user_name", "unknown")
        if name not in user_data:
            user_data[name] = {"name": name, "runs": 0, "success": 0, "repos": set(), "durations": []}
        user_data[name]["runs"] += 1
        if run.get("status") == "completed":
            user_data[name]["success"] += 1
        user_data[name]["repos"].add(run.get("repo_name", "unknown"))
        if run.get("total_duration_ms"):
            user_data[name]["durations"].append(run["total_duration_ms"])

    users_list = []
    for ud in sorted(user_data.values(), key=lambda x: x["runs"], reverse=True):
        avg_dur = int(statistics.mean(ud["durations"])) if ud["durations"] else 0
        users_list.append({
            "name": ud["name"],
            "runs": ud["runs"],
            "success_rate": round(ud["success"] / ud["runs"], 3) if ud["runs"] else 0,
            "unique_repos": len(ud["repos"]),
            "avg_duration_ms": avg_dur,
        })

    # CONTRIBUTING Step 5
    flag_runs = sum(1 for r in runs if r.get("flags_raised"))
    self_check_pass = sum(1 for r in runs if r.get("self_check_passed", True))

    contributing = {
        "invocation_count": total_runs,
        "flag_frequency": round(flag_runs / total_runs, 3) if total_runs else 0,
        "self_check_pass_rate": round(self_check_pass / total_runs, 3) if total_runs else 0,
    }

    # Onboarding — first-seen date per repo (across ALL runs, not just filtered period)
    # Use the already-loaded runs for efficiency (they cover the period); for total onboarded
    # we look at the full repo_data which comes from the period-filtered set.
    # To get all-time onboarding, we also check the full file.
    all_time_runs = load_runs(after=datetime.min.replace(tzinfo=timezone.utc))
    repo_first_seen: dict[str, str] = {}
    for run in all_time_runs:
        name = run.get("repo_name", "unknown")
        started = run.get("started_at", "")
        if name and name != "unknown":
            if name not in repo_first_seen or started < repo_first_seen[name]:
                repo_first_seen[name] = started

    total_repos_onboarded = len(repo_first_seen)
    newly_onboarded = sum(
        1 for name, date in repo_first_seen.items()
        if date >= start.isoformat()
    )

    onboarding = {
        "total_repos_onboarded": total_repos_onboarded,
        "newly_onboarded_this_period": newly_onboarded,
        "repos_with_first_run": [
            {"name": name, "first_run": date}
            for name, date in sorted(repo_first_seen.items(), key=lambda x: x[1], reverse=True)
        ][:15],
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": {"start": start.isoformat(), "end": end.isoformat(), "label": period_str, "days": days},
        "usage": {
            "total_runs": total_runs,
            "unique_users": len(users),
            "unique_repos": len(repos),
            "runs_per_day_avg": round(total_runs / days, 1),
            "most_active_user": {"name": most_active_user[0], "runs": most_active_user[1]},
            "most_active_repo": {"name": most_active_repo[0], "runs": most_active_repo[1]},
        },
        "performance": performance,
        "effectiveness": effectiveness,
        "security_posture": security_posture,
        "cost": cost,
        "onboarding": onboarding,
        "errors": errors,
        "repos": repos_list[:10],
        "users": users_list[:10],
        "contributing_step5": contributing,
    }


def format_duration(ms: int | None) -> str:
    """Format milliseconds as human-readable duration."""
    if ms is None or ms == 0:
        return "—"
    seconds = ms / 1000
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes < 60:
        return f"{minutes}m {secs:02d}s"
    hours = int(minutes // 60)
    mins = minutes % 60
    return f"{hours}h {mins:02d}m"


def render_bar(value: float, width: int = 10) -> str:
    """Render a simple progress bar."""
    filled = int(value * width)
    return "▓" * filled + "░" * (width - filled)


def render_table(report: dict[str, Any]) -> str:
    """Render the report as a terminal-friendly ASCII table."""
    usage = report.get("usage", {})
    perf = report.get("performance", {})
    eff = report.get("effectiveness", {})
    sec = report.get("security_posture", {})
    cost = report.get("cost", {})
    errs = report.get("errors", {})
    repos = report.get("repos", [])
    period = report.get("period", {})
    step5 = report.get("contributing_step5", {})
    onboarding = report.get("onboarding", {})

    lines = []
    lines.append("╔══════════════════════════════════════════════════════════════════════╗")
    lines.append("║               🛡️  DETOX USAGE DASHBOARD                              ║")
    lines.append(f"║               Period: {period.get('label', '30d')} ({period.get('days', 0)} days)                              ║")
    lines.append("╠══════════════════════════════════════════════════════════════════════╣")
    lines.append("║                                                                      ║")
    lines.append("║  📊 USAGE OVERVIEW                                                   ║")
    lines.append("║  ──────────────────────────────────────────────────────────────────  ║")
    lines.append(f"║  Total Runs:     {usage.get('total_runs', 0):<8}  Unique Users:    {usage.get('unique_users', 0):<8}       ║")
    lines.append(f"║  Unique Repos:   {usage.get('unique_repos', 0):<8}  Avg Runs/Day:   {usage.get('runs_per_day_avg', 0):<8}       ║")

    most_repo = usage.get("most_active_repo", {})
    most_user = usage.get("most_active_user", {})
    lines.append(f"║  Most Active Repo: {most_repo.get('name', '—')[:30]} ({most_repo.get('runs', 0)} runs)        ║")
    lines.append(f"║  Most Active User: {most_user.get('name', '—')[:30]} ({most_user.get('runs', 0)} runs)        ║")
    lines.append("║                                                                      ║")

    # Performance
    lines.append("║  ⏱️  PERFORMANCE                                                      ║")
    lines.append("║  ──────────────────────────────────────────────────────────────────  ║")
    lines.append(f"║  Avg Total Duration:    {format_duration(perf.get('avg_duration_ms')):<12}                             ║")
    lines.append(f"║  Median Total Duration: {format_duration(perf.get('median_duration_ms')):<12}                             ║")
    lines.append(f"║  Fastest Run:           {format_duration(perf.get('min_duration_ms')):<12}                             ║")
    lines.append(f"║  Slowest Run:           {format_duration(perf.get('max_duration_ms')):<12}                             ║")

    # Phase breakdown
    by_phase = perf.get("by_phase", {})
    if by_phase:
        lines.append("║                                                                      ║")
        lines.append("║  Per-Phase Median:                                                   ║")
        phase_names = {
            "1": "Setup", "2": "Parse", "3": "Classify", "4": "Fix",
            "5": "Validate", "6": "Tests", "7": "Docs", "8": "Report", "9": "PR"
        }
        max_phase_ms = max((p.get("median_ms", 0) for p in by_phase.values()), default=1) or 1
        for pk in sorted(by_phase.keys()):
            pd = by_phase[pk]
            name = phase_names.get(pk, f"Phase {pk}")
            med = pd.get("median_ms", 0)
            bar = render_bar(med / max_phase_ms)
            lines.append(f"║    Phase {pk} ({name:<8}): {format_duration(med):<7} {bar}                       ║")

    lines.append("║                                                                      ║")

    # Effectiveness
    lines.append("║  🎯 EFFECTIVENESS                                                    ║")
    lines.append("║  ──────────────────────────────────────────────────────────────────  ║")
    lines.append(f"║  CWEs Remediated:       {eff.get('cwes_remediated', 0):<8}                                   ║")
    rem_rate = eff.get("remediation_rate", 0)
    fix_rate = eff.get("fix_success_rate", 0)
    def_rate = eff.get("deferral_rate", 0)
    val_rate = eff.get("validation_pass_rate", 0)
    test_rate = eff.get("test_pass_rate", 0)
    lines.append(f"║  Remediation Rate:      {rem_rate*100:.1f}%  {render_bar(rem_rate)}                       ║")
    lines.append(f"║  Fix Success Rate:      {fix_rate*100:.1f}%  {render_bar(fix_rate)}                       ║")
    lines.append(f"║  Deferral Rate:         {def_rate*100:.1f}%  {render_bar(def_rate)}                       ║")
    lines.append(f"║  Validation Pass Rate:  {val_rate*100:.1f}%  {render_bar(val_rate)}                       ║")
    lines.append(f"║  Test Pass Rate:        {test_rate*100:.1f}%  {render_bar(test_rate)}                       ║")
    deferred_reasons = sec.get("deferred_by_reason", {})
    if deferred_reasons:
        dr = ", ".join(f"{k}: {v}" for k, v in sorted(deferred_reasons.items(), key=lambda x: -x[1]))
        lines.append(f"║  Deferred (why):        {dr[:44]:<44}   ║")
    unverified_reasons = sec.get("unverified_by_reason", {})
    if unverified_reasons:
        ur = ", ".join(f"{k}: {v}" for k, v in sorted(unverified_reasons.items(), key=lambda x: -x[1]))
        lines.append(f"║  Unverified (why):      {ur[:44]:<44}   ║")
    lines.append("║                                                                      ║")

    # Security posture
    top_cwes = sec.get("top_cwes", [])
    if top_cwes:
        lines.append("║  🔒 SECURITY POSTURE (Top CWEs Fixed)                                ║")
        lines.append("║  ──────────────────────────────────────────────────────────────────  ║")
        max_cwe_count = top_cwes[0]["count"] if top_cwes else 1
        for cwe_item in top_cwes[:5]:
            cwe_id = cwe_item["cwe"]
            count = cwe_item["count"]
            bar_width = int((count / max_cwe_count) * 20)
            bar = "█" * bar_width + "░" * (20 - bar_width)
            lines.append(f"║  {cwe_id:<10} {bar} {count:<5}                           ║")
        sev = sec.get("severity_distribution", {})
        lines.append(f"║  Severity: Critical: {sev.get('critical', 0)}  High: {sev.get('high', 0)}  Medium: {sev.get('medium', 0)}  Low: {sev.get('low', 0)}     ║")
        lines.append("║                                                                      ║")

    # Usage profile
    lines.append("║  🧩 USAGE PROFILE                                                    ║")
    lines.append("║  ──────────────────────────────────────────────────────────────────  ║")
    lines.append(f"║  Total Agent Invocations: {cost.get('total_agent_invocations', 0):<8}                               ║")
    model_dist = cost.get("model_distribution", {})
    model_str = ", ".join(f"{k}: {v}" for k, v in model_dist.items())
    lines.append(f"║  Model Distribution:      {model_str[:40]:<40}   ║")
    lines.append("║                                                                      ║")

    # Errors
    lines.append("║  ❌ ERRORS                                                            ║")
    lines.append("║  ──────────────────────────────────────────────────────────────────  ║")
    lines.append(f"║  Pipeline Failures:     {errs.get('failure_count', 0)} / {usage.get('total_runs', 0)} ({errs.get('failure_rate', 0)*100:.1f}%)                          ║")
    lines.append(f"║  Total Retries:         {errs.get('total_retries', 0):<8}                                   ║")
    lines.append("║                                                                      ║")

    # Repos
    if repos:
        lines.append("║  📋 REPOS COVERED                                                    ║")
        lines.append("║  ──────────────────────────────────────────────────────────────────  ║")
        for repo in repos[:5]:
            name = repo["name"][:25]
            lines.append(f"║  {name:<25} {repo['runs']:>3} runs │ {repo['success_rate']*100:.0f}% success │ {repo['cwes_fixed']:>3} CWEs  ║")
        if len(repos) > 5:
            lines.append(f"║  ... ({len(repos) - 5} more repos)                                             ║")
        lines.append("║                                                                      ║")

    # Onboarding
    lines.append("║  📈 ONBOARDING                                                       ║")
    lines.append("║  ──────────────────────────────────────────────────────────────────  ║")
    lines.append(f"║  Total Repos Onboarded: {onboarding.get('total_repos_onboarded', 0):<8}                                 ║")
    lines.append(f"║  New This Period:       {onboarding.get('newly_onboarded_this_period', 0):<8}                                 ║")
    lines.append("║                                                                      ║")

    lines.append("╚══════════════════════════════════════════════════════════════════════╝")
    return "\n".join(lines)


def render_html(report: dict[str, Any]) -> str:
    """Render the report as a standalone HTML page with inline SVG charts."""
    usage = report.get("usage", {})
    perf = report.get("performance", {})
    eff = report.get("effectiveness", {})
    sec = report.get("security_posture", {})
    cost = report.get("cost", {})
    errs = report.get("errors", {})
    repos = report.get("repos", [])
    period = report.get("period", {})
    onboarding = report.get("onboarding", {})

    # Reason breakdowns (why deferred / why unverified) as inline strings
    _dr = sec.get("deferred_by_reason", {})
    _ur = sec.get("unverified_by_reason", {})
    deferred_html = (" &middot; ".join(f"{k}: {v}" for k, v in sorted(_dr.items(), key=lambda x: -x[1]))
                     or "none")
    unverified_html = (" &middot; ".join(f"{k}: {v}" for k, v in sorted(_ur.items(), key=lambda x: -x[1]))
                       or "none")

    # Build SVG bar chart for top CWEs
    top_cwes = sec.get("top_cwes", [])
    cwe_bars = ""
    if top_cwes:
        max_count = top_cwes[0]["count"] if top_cwes else 1
        for i, item in enumerate(top_cwes[:8]):
            width = int((item["count"] / max_count) * 300)
            y = i * 30
            cwe_bars += f'<rect x="100" y="{y}" width="{width}" height="22" fill="#00395d" rx="3"/>'
            cwe_bars += f'<text x="5" y="{y + 16}" font-size="12" fill="#333">{item["cwe"]}</text>'
            cwe_bars += f'<text x="{105 + width}" y="{y + 16}" font-size="12" fill="#333">{item["count"]}</text>'

    cwe_chart_height = len(top_cwes[:8]) * 30 + 10

    # Repo table rows
    repo_rows = ""
    for repo in repos[:10]:
        repo_rows += f"""<tr>
            <td>{repo['name']}</td>
            <td>{repo['runs']}</td>
            <td>{repo['success_rate']*100:.0f}%</td>
            <td>{repo['cwes_fixed']}</td>
            <td>{repo['unique_users']}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Detox Usage Report — {period.get('label', '30d')}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f7fa; color: #1a1a2e; padding: 24px; }}
  .header {{ background: #00395d; color: white; padding: 24px 32px; border-radius: 8px; margin-bottom: 24px; }}
  .header h1 {{ font-size: 24px; margin-bottom: 4px; }}
  .header p {{ opacity: 0.8; font-size: 14px; }}
  .kpi-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 24px; }}
  .kpi {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; }}
  .kpi .value {{ font-size: 32px; font-weight: 700; color: #00395d; }}
  .kpi .label {{ font-size: 12px; color: #666; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}
  .section {{ background: white; padding: 24px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 16px; }}
  .section h2 {{ font-size: 16px; color: #00395d; margin-bottom: 16px; border-bottom: 2px solid #e8ecf0; padding-bottom: 8px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; padding: 8px 12px; background: #f0f4f8; color: #00395d; font-weight: 600; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #e8ecf0; }}
  tr:hover td {{ background: #f8fafc; }}
  .gauge {{ display: inline-block; width: 100px; height: 8px; background: #e8ecf0; border-radius: 4px; overflow: hidden; margin-left: 8px; vertical-align: middle; }}
  .gauge-fill {{ height: 100%; background: #00843d; border-radius: 4px; }}
  .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 24px; padding-top: 16px; border-top: 1px solid #e8ecf0; }}
  @media print {{ body {{ background: white; padding: 0; }} .section {{ box-shadow: none; border: 1px solid #ddd; }} }}
</style>
</head>
<body>
<div class="header">
  <h1>🛡️ Detox Usage Report</h1>
  <p>Period: {period.get('label', '30d')} ({period.get('days', 0)} days) • Generated: {report.get('generated_at', '')[:19]}</p>
</div>

<div class="kpi-row">
  <div class="kpi"><div class="value">{usage.get('total_runs', 0)}</div><div class="label">Total Runs</div></div>
  <div class="kpi"><div class="value">{onboarding.get('total_repos_onboarded', 0)}</div><div class="label">Repos Onboarded</div></div>
  <div class="kpi"><div class="value">{eff.get('remediation_rate', 0)*100:.0f}%</div><div class="label">Remediation Rate</div></div>
  <div class="kpi"><div class="value">{eff.get('fix_success_rate', 0)*100:.0f}%</div><div class="label">Fix Rate</div></div>
  <div class="kpi"><div class="value">{eff.get('cwes_remediated', 0)}</div><div class="label">CWEs Fixed</div></div>
  <div class="kpi"><div class="value">{eff.get('deferral_rate', 0)*100:.0f}%</div><div class="label">Deferral Rate</div></div>
  <div class="kpi"><div class="value">{eff.get('test_pass_rate', 0)*100:.0f}%</div><div class="label">Test Pass Rate</div></div>
  <div class="kpi"><div class="value">{usage.get('unique_users', 0)}</div><div class="label">Users</div></div>
</div>

<div class="section">
  <h2>🎯 Effectiveness</h2>
  <p>Remediation Rate: <strong>{eff.get('remediation_rate', 0)*100:.1f}%</strong> <span class="gauge"><span class="gauge-fill" style="width:{eff.get('remediation_rate', 0)*100}%"></span></span></p>
  <p>Fix Success Rate: <strong>{eff.get('fix_success_rate', 0)*100:.1f}%</strong> <span class="gauge"><span class="gauge-fill" style="width:{eff.get('fix_success_rate', 0)*100}%"></span></span></p>
  <p>Deferral Rate: <strong>{eff.get('deferral_rate', 0)*100:.1f}%</strong> <span class="gauge"><span class="gauge-fill" style="width:{eff.get('deferral_rate', 0)*100}%"></span></span></p>
  <p>Validation Pass Rate: <strong>{eff.get('validation_pass_rate', 0)*100:.1f}%</strong> <span class="gauge"><span class="gauge-fill" style="width:{eff.get('validation_pass_rate', 0)*100}%"></span></span></p>
  <p>Test Pass Rate: <strong>{eff.get('test_pass_rate', 0)*100:.1f}%</strong> <span class="gauge"><span class="gauge-fill" style="width:{eff.get('test_pass_rate', 0)*100}%"></span></span></p>
  <p style="margin-top:10px;">Deferred — why: <strong>{deferred_html}</strong></p>
  <p>Unverified fixes — why: <strong>{unverified_html}</strong></p>
</div>

<div class="section">
  <h2>🔒 Top CWEs Remediated</h2>
  <svg width="450" height="{cwe_chart_height}" xmlns="http://www.w3.org/2000/svg">{cwe_bars}</svg>
</div>

<div class="section">
  <h2>📋 Repos Covered</h2>
  <table>
    <thead><tr><th>Repository</th><th>Runs</th><th>Success Rate</th><th>CWEs Fixed</th><th>Users</th></tr></thead>
    <tbody>{repo_rows}</tbody>
  </table>
</div>

<div class="section">
  <h2>❌ Errors</h2>
  <p>Pipeline Failures: <strong>{errs.get('failure_count', 0)}</strong> / {usage.get('total_runs', 0)} ({errs.get('failure_rate', 0)*100:.1f}%)</p>
  <p>Total Retries: <strong>{errs.get('total_retries', 0)}</strong></p>
</div>

<div class="section">
  <h2>📈 Onboarding</h2>
  <p>Total Repos Onboarded: <strong>{onboarding.get('total_repos_onboarded', 0)}</strong></p>
  <p>New This Period: <strong>{onboarding.get('newly_onboarded_this_period', 0)}</strong></p>
</div>

<div class="section">
  <h2>🧩 Usage Profile</h2>
  <p>Total Agent Invocations: <strong>{cost.get('total_agent_invocations', 0)}</strong></p>
</div>

<div class="footer">Generated by Detox v{report.get('plugin_version', PLUGIN_VERSION)} • {report.get('generated_at', '')}</div>
</body>
</html>"""
    return html


def generate_report(input_data: dict[str, Any]) -> dict[str, Any]:
    """Generate the usage report in the requested format."""
    period_str = input_data.get("period", "30d")
    output_format = input_data.get("format", "json")
    group_by = input_data.get("group_by")
    output_path = input_data.get("output")

    start, end = parse_period(period_str)
    runs = load_runs(after=start)
    report = compute_aggregates(runs, period_str, start, end)
    report["plugin_version"] = PLUGIN_VERSION

    # Render in requested format
    rendered = ""
    if output_format == "table":
        rendered = render_table(report)
    elif output_format == "html":
        rendered = render_html(report)
        # Write HTML to file
        if output_path:
            html_path = Path(output_path)
        else:
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            html_path = REPORTS_DIR / f"usage-{date_str}.html"
        try:
            html_path.write_text(rendered, encoding="utf-8")
            report["html_path"] = str(html_path)
        except OSError as e:
            log(f"Failed to write HTML report: {e}")
    elif output_format == "json":
        rendered = json.dumps(report, indent=2, default=str)

    return {
        "status": "success",
        "report": report,
        "rendered": rendered if output_format != "html" else f"HTML report written to: {report.get('html_path', 'stdout')}",
        "format": output_format,
    }


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    result = generate_report(input_data)
    write_json_output(result, start_time=start_time)


if __name__ == "__main__":
    main()
