#!/usr/bin/env python3
"""Pipeline preparation — execute deterministic stages 0-3.

Runs preflight check, repository setup, Wiz report parsing, deduplication,
and classification in sequence. Returns classified findings for the
orchestrator agent to continue from Stage 4.

Threat model parsing is deferred (requires LLM) and flagged in the output.

Input (JSON stdin):
    {
        "project_path": "/path/to/repo",
        "sast_report_path": "/path/to/wiz.json",
        "threat_model_path": null,
        "severity_filter": "all",
        "checkout_branch": null,
        "new_branch": null,
        "jira_id": null,
        "dry_run": false,
        "model": "opus",
        "generate_tests": true,
        "test_mode": "fast"
    }

Output (JSON stdout):
    {
        "status": "success",
        "job_id": "...",
        "state_path": "{project_path}/.detox/state.json",
        "project_path": "...",
        "branch_name": "...",
        "base_branch": "...",
        "classified": {...},
        "threat_model_pending": true/false,
        "summary": {...}
    }

Progress lines are written to stderr (always visible).

The pipeline state file is initialised here with every parsed finding in
`vulnerabilities` and phases 1-3 completed, so run telemetry counts never depend
on the orchestrator copying findings by hand.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.utils.common import read_json_input, write_json_output, progress, progress_done
from scripts.core.errors import error_exit
from scripts.state.pipeline_state import emit_phase_event, init_state, write_state

SCRIPTS_DIR = Path(__file__).resolve().parent


def _run_script(rel_path: str, input_data: dict, timeout: int = 300) -> dict:
    script = SCRIPTS_DIR / rel_path
    if not script.exists():
        error_exit(f"Script not found: {script}", "prepare")

    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if not result.stdout.strip():
        stderr_hint = result.stderr[:500] if result.stderr else "(no stderr)"
        error_exit(f"Script {rel_path} produced no output. stderr: {stderr_hint}", "prepare")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        error_exit(f"Script {rel_path} returned invalid JSON: {result.stdout[:300]}", "prepare")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _init_state_file(
    inp: dict,
    started_at: str,
    phase_times: dict[str, dict[str, str]],
    project_path: str,
    branch_name: str,
    jdk: dict,
    vulnerabilities: list[dict],
    cats: dict,
) -> tuple[str | None, str | None]:
    """Write the pipeline state file and emit phase 1-3 events.

    Returns (job_id, state_path); state_path is None if the file couldn't be written.
    """
    out = init_state({
        "project_path": project_path,
        "jira_id": inp.get("jira_id"),
        "model": inp.get("model", "opus"),
        "severity_filter": inp.get("severity_filter", "all"),
        "dry_run": inp.get("dry_run", False),
        "generate_tests": inp.get("generate_tests", True),
        "test_mode": inp.get("test_mode", "fast"),
        **jdk,
    })
    state = out["state"]
    state_path = out.get("state_path")
    state["started_at"] = started_at
    state["branch_name"] = branch_name
    state["vulnerabilities"] = vulnerabilities
    state["hybrid_findings"] = list(cats.get("hybrid", []))
    state["infra_findings"] = list(cats.get("infra_config", []))
    state["manual_findings"] = list(cats.get("manual", []))
    for phase, times in phase_times.items():
        state["phases"][phase] = {"status": "completed", **times}

    if state_path:
        try:
            write_state(state_path, state)
        except OSError as e:
            progress_done(f"Warning: could not write pipeline state file: {e}")
            state_path = None

    for phase in phase_times:
        emit_phase_event(state["job_id"], phase, state["phases"][phase])
    return state["job_id"], state_path


def main() -> None:
    start_time = time.time()
    started_at = _now()
    inp = read_json_input()

    project_path = inp.get("project_path", "")
    sast_report_path = inp.get("sast_report_path")
    threat_model_path = inp.get("threat_model_path")
    severity_filter = inp.get("severity_filter", "all")
    checkout_branch = inp.get("checkout_branch")
    new_branch = inp.get("new_branch")
    jira_id = inp.get("jira_id")
    dry_run = inp.get("dry_run", False)

    # ── Stage 0: Preflight ─────────────────────────────────────
    progress("Stage 0/9 — Preflight check...")
    out = _run_script("validators/preflight_check.py", {
        "require_semgrep": True,
        "require_glab": False,
        "require_git": True,
        # Telemetry gRPC/OTLP deps are a mandatory CHECK-ONLY gate (no auto-install).
        "require_telemetry_deps": True,
        # Mandatory Barclays user setup is a HARD GATE: if the 4 barclays_* keys
        # are missing from ~/.claude/settings.json, preflight returns
        # missing_tools and the pipeline aborts here, before the orchestrator is
        # ever delegated. (Also enforced in git/repo_setup.py as a backstop.)
        "require_barclays_setup": True,
    })

    if out.get("status") == "missing_tools":
        missing = out.get("missing", [])
        # Surface the full setup banner when the Barclays identity is missing.
        # If other tools are missing too, name them alongside so nothing is hidden.
        if "barclays_setup" in missing:
            banner = (out.get("install_instructions", {}) or {}).get("barclays_setup", "")
            others = [m for m in missing if m != "barclays_setup"]
            msg = banner or f"Missing required tools: {missing}"
            if others:
                msg = f"{msg}\n\nAlso missing: {', '.join(others)}"
            error_exit(msg, "barclays_setup")
        # Telemetry gRPC/OTLP deps hard-stop — surface the detailed install instruction.
        if "observe_deps" in missing:
            instr = (out.get("install_instructions", {}) or {}).get("observe_deps", "")
            others = [m for m in missing if m != "observe_deps"]
            msg = instr or f"Missing required tools: {missing}"
            if others:
                msg = f"{msg}\n\nAlso missing: {', '.join(others)}"
            error_exit(msg, "observe_deps")
        error_exit(f"Missing required tools: {missing}", "preflight")

    tools = out.get("tools", {})
    found = [
        f"{k} {v.get('version', '?')}"
        for k, v in tools.items()
        # preflight_check.py reports "available"; "found" kept for older callers/tests
        if isinstance(v, dict) and (v.get("available") or v.get("found"))
    ]
    progress_done(f"Preflight passed — {', '.join(found) or 'all tools found'}")

    # ── Stage 1: Repository Setup ──────────────────────────────
    phase_times: dict[str, dict[str, str]] = {"1": {"started_at": _now()}}
    progress("Stage 1/9 — Setting up repository...")
    out = _run_script("git/repo_setup.py", {
        "repo_url": project_path,
        "cwe_ids": [],
        # None → repo_setup uses the branch actually checked out (MR target), not a guessed "main"
        "base_branch": inp.get("base_branch"),
        "git_pat_env_var": "GIT_PAT",
        "checkout_branch": checkout_branch,
        "new_branch": new_branch,
        "jira_id": jira_id,
    }, timeout=180)

    if out.get("status") == "error":
        error_exit(f"Repo setup failed: {out.get('error', 'unknown')}", "repo_setup")

    project_path = out.get("clone_dir", project_path)
    branch_name = out.get("branch_name", "")
    base_branch = out.get("base_branch", "main")
    progress_done(f"Repository ready — branch {branch_name}")

    # ── Stage 1b: Detect JDK Version ──────────────────────────
    progress("Stage 1b — Detecting JDK version...")
    jdk_out = _run_script("validators/detect_jdk_version.py", {
        "repo_dir": project_path,
    })
    jdk_version = jdk_out.get("jdk_version")  # int or None
    is_java_project = jdk_out.get("is_java_project", False)
    jdk_detection_source = jdk_out.get("detection_source")
    if jdk_version is not None:
        progress_done(f"JDK {jdk_version} detected (source: {jdk_detection_source})")
    elif is_java_project:
        progress_done("Java project detected but JDK version unknown — defaulting to safe-versions.json path")
    else:
        progress_done("Non-Java project — JDK detection not applicable")

    phase_times["1"]["ended_at"] = _now()

    # ── Stage 2: Parse Reports ─────────────────────────────────
    phase_times["2"] = {"started_at": _now()}
    progress("Stage 2/9 — Parsing reports...")
    all_vulns: list[dict] = []
    threat_model_pending = False

    if sast_report_path:
        out = _run_script("parsers/parse_wiz_report.py", {
            "report_path": sast_report_path,
            "repo_root": project_path,
        })
        if out.get("status") == "error":
            error_exit(f"Wiz report parsing failed: {out.get('error', 'unknown')}", "parse")

        vulns = out.get("vulnerabilities", [])
        all_vulns.extend(vulns)
        progress_done(f"Wiz report — {len(vulns)} findings")

    if threat_model_path:
        threat_model_pending = True
        progress_done("Threat model parsing deferred (requires LLM)")

    if all_vulns:
        out = _run_script("parsers/deduplicate_findings.py", {
            "vulnerabilities": all_vulns,
            "merge_strategy": "highest_severity",
        })
        if out.get("status") == "error":
            error_exit(f"Deduplication failed: {out.get('error', 'unknown')}", "dedup")

        deduped = out.get("vulnerabilities", all_vulns)
        removed = len(all_vulns) - len(deduped)
        progress_done(f"{len(deduped)} unique findings ({removed} duplicates removed)")
    else:
        deduped = []
        if not threat_model_pending:
            progress_done("No findings to process")

    phase_times["2"]["ended_at"] = _now()

    # ── Stage 3: Classify ──────────────────────────────────────
    phase_times["3"] = {"started_at": _now()}
    progress("Stage 3/9 — Classifying findings...")

    if deduped:
        out = _run_script("parsers/classify_findings.py", {
            "vulnerabilities": deduped,
            "severity_filter": severity_filter,
        })
        if out.get("status") == "error":
            error_exit(f"Classification failed: {out.get('error', 'unknown')}", "classify")
        classified = out
    else:
        classified = {
            "status": "success",
            "categories": {
                "code_fix": [], "dependency": [], "hybrid": [],
                "infra_config": [], "manual": [],
            },
            "filtered_out_count": 0,
        }

    # Handle both output formats: old (categories dict) and new (direct fields)
    cats = classified.get("categories", {})
    code_n = len(cats.get("code_fix", [])) if cats else len(classified.get("code_fix", []))
    dep_n = len(cats.get("dependency", [])) if cats else len(classified.get("dependency", []))
    infra_n = len(cats.get("infra_config", [])) if cats else len(classified.get("infra_config", []))
    manual_n = len(cats.get("manual", [])) if cats else len(classified.get("manual", []))
    filtered_n = classified.get("filtered_out_count", 0) or len(classified.get("filtered_out", []))
    progress_done(
        f"Code: {code_n} | Dependency: {dep_n} | Infra: {infra_n} "
        f"| Manual: {manual_n} | Filtered: {filtered_n}"
    )

    # ── Stage 3b: Remediation Strategy Selection ─────────────────
    remediation_plan = None
    if dep_n > 0 and is_java_project and jdk_version is not None:
        progress("Stage 3b/9 — Selecting remediation strategies...")

        # Always select here: the orchestrator consumes remediation_plan and has no
        # selection logic of its own. NexusClient caches per URL, so large batches
        # cost one lookup set per package, not per finding.
        safe_versions_path = (SCRIPTS_DIR.parent / "config" / "safe-versions.json")
        safe_versions = {}
        if safe_versions_path.exists():
            try:
                full_config = json.loads(safe_versions_path.read_text())
                # Extract just the "versions" dict (remediation strategy selector expects this format)
                safe_versions = full_config.get("versions", {})
            except Exception as e:
                progress_done(f"Warning: Could not load safe-versions.json: {e}")

        dependency_findings = cats.get("dependency", []) if cats else classified.get("dependency", [])
        out = _run_script("validators/sca_remediation_strategy.py", {
            "vulnerabilities": dependency_findings,
            "safe_versions": safe_versions,
            "jdk_version": jdk_version,
            "repo_dir": project_path,
            "nexus_url": "https://nexus.barcapint.com",
        }, timeout=600)

        if out.get("status") == "success":
            remediation_plan = out.get("remediation_plan", [])
            summary = out.get("summary", {})
            auto_apply = summary.get("auto_apply", 0)
            manual = summary.get("manual", 0)
            progress_done(f"Remediation plan: {auto_apply} auto_apply, {manual} manual")
        else:
            progress_done(f"Warning: Strategy selection failed: {out.get('error', 'unknown')}")
    elif dep_n > 0:
        progress("Stage 3b/9 — Skipping remediation strategy (not a Java project or JDK unknown)")
        progress_done("Dependency findings will be escalated to manual review")
    else:
        progress("Stage 3b/9 — No dependency findings to process")

    phase_times["3"]["ended_at"] = _now()

    # ── Pipeline state (source of truth for run telemetry) ──────
    job_id, state_path = _init_state_file(
        inp, started_at, phase_times, project_path, branch_name,
        {"jdk_version": jdk_version, "is_java_project": is_java_project,
         "jdk_detection_source": jdk_detection_source},
        deduped, cats or classified,
    )
    if state_path:
        progress_done(f"Pipeline state written — {state_path} (job {job_id})")

    # ── Output ─────────────────────────────────────────────────
    write_json_output({
        "status": "success",
        "job_id": job_id,
        "state_path": state_path,
        "project_path": project_path,
        "branch_name": branch_name,
        "base_branch": base_branch,
        "jdk_version": jdk_version,
        "is_java_project": is_java_project,
        "jdk_detection_source": jdk_detection_source,
        "classified": classified,
        "remediation_plan": remediation_plan,
        "threat_model_pending": threat_model_pending,
        "summary": {
            "total": len(deduped),
            "code_fix": code_n,
            "dependency": dep_n,
            "infra_config": infra_n,
            "manual": manual_n,
            "filtered_out": filtered_n,
        },
    }, start_time=start_time)


if __name__ == "__main__":
    main()
