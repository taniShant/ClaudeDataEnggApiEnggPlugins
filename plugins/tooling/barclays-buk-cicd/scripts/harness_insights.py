#!/usr/bin/env python3
"""Fetch Harness inventory and analytics data to answer a free-text question.

Inspects the question to determine which CLI commands to run, fetches the data,
and writes JSON files to the current directory for the harness-query-agent to read.

Usage:
  python harness_insights.py --question "how many pipelines failed in last 24 hours" --profile prod
  python harness_insights.py --question "what orgs exist" --profile nonprod

Exit codes:
  0  success
  1  CLI error
  3  unexpected error
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


HARNESS = "harness"

# ---------------------------------------------------------------------------
# Question classifier — maps keywords to required data fetches
# ---------------------------------------------------------------------------

FETCH_MAP = {
    "orgs":       ["org", "organisation", "organization"],
    "projects":   ["project", "projects"],
    "pipelines":  ["pipeline", "pipelines"],
    "executions": ["execution", "executions", "ran", "run", "failed", "success",
                   "succeeded", "aborted", "status", "last 24", "last 7", "last 30",
                   "how many", "count"],
    "delegates":  ["delegate", "delegates"],
    "connectors": ["connector", "connectors"],
}


def classify(question: str) -> set:
    q = question.lower()
    needed = set()
    for key, keywords in FETCH_MAP.items():
        if any(kw in q for kw in keywords):
            needed.add(key)
    # execution questions always need projects to scope correctly
    if "executions" in needed and "projects" not in needed:
        needed.add("projects")
    # if nothing matched, fetch everything for a general overview
    if not needed:
        needed = {"orgs", "projects", "pipelines", "delegates"}
    return needed


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

def _run_list(args: list, label: str) -> list:
    cmd_str = " ".join([HARNESS] + args + ["--json", "--all"])
    result = subprocess.run(["bash", "-lc", cmd_str], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"CLI error ({label}): {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(f"JSON parse error ({label}): {exc}", file=sys.stderr)
        sys.exit(3)


def _run_list_limited(args: list, label: str, limit: int = 500) -> list:
    cmd_str = " ".join([HARNESS] + args + ["--json", "--limit", str(limit)])
    result = subprocess.run(["bash", "-lc", cmd_str], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"CLI error ({label}): {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(f"JSON parse error ({label}): {exc}", file=sys.stderr)
        sys.exit(3)


# ---------------------------------------------------------------------------
# Data fetchers
# ---------------------------------------------------------------------------

def fetch_orgs(profile: str) -> list:
    print("Fetching orgs...", file=sys.stderr)
    return _run_list(["list", "organization", "--profile", profile], "list organization")


def fetch_projects(profile: str) -> list:
    print("Fetching projects...", file=sys.stderr)
    return _run_list(["list", "project", "--profile", profile], "list project")


def fetch_executions(profile: str, projects: list) -> list:
    """Fetch recent executions across all projects."""
    print(f"Fetching executions across {len(projects)} project(s)...", file=sys.stderr)
    all_execs = []
    for proj in projects:
        proj_inner = proj.get("project") or proj
        org_id = proj_inner.get("orgIdentifier") or proj_inner.get("org", "")
        proj_id = proj_inner.get("identifier", "")
        if not proj_id:
            continue
        execs = _run_list_limited(
            ["list", "execution",
             "--profile", profile,
             "--org", org_id,
             "--project", proj_id],
            f"list execution {proj_id}",
            limit=200
        )
        if len(execs) == 200:
            print(f"  Warning: execution fetch for {proj_id} hit the 200-record cap — "
                  "counts may be understated", file=sys.stderr)
        for e in execs:
            e["_org"] = org_id
            e["_project"] = proj_id
        all_execs.extend(execs)
    return all_execs


def fetch_delegates(profile: str) -> list:
    print("Fetching delegates...", file=sys.stderr)
    return _run_list(["list", "delegate", "--profile", profile], "list delegate")


def fetch_connectors(profile: str) -> list:
    print("Fetching connectors...", file=sys.stderr)
    return _run_list(["list", "connector", "--profile", profile], "list connector")


def fetch_pipelines(profile: str, projects: list) -> list:
    """Note: harness list pipeline returns 500 on this account (v1 endpoint broken).
    We return an empty list and note this in the summary."""
    print("Note: harness list pipeline unavailable (v1 endpoint returns 500) — skipping", file=sys.stderr)
    return []


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Harness data to answer a question")
    parser.add_argument("--question", required=True, help="Free-text question")
    parser.add_argument("--profile",  required=True, help="prod or nonprod")
    args = parser.parse_args()

    needed = classify(args.question)
    print(f"Question classified — fetching: {', '.join(sorted(needed))}", file=sys.stderr)

    data_files = []
    data_summary = {"profile": args.profile, "fetched": list(sorted(needed))}

    # Always fetch orgs and projects first (other fetches depend on them)
    orgs = []
    projects = []

    if "orgs" in needed or "projects" in needed or "executions" in needed or "pipelines" in needed:
        orgs = fetch_orgs(args.profile)
        Path("harness_insights_orgs.json").write_text(json.dumps(orgs, indent=2))
        data_files.append("harness_insights_orgs.json")
        data_summary["orgs_count"] = len(orgs)
        data_summary["orgs"] = [
            {"id": o.get("organization", {}).get("identifier") or o.get("identifier"),
             "name": o.get("organization", {}).get("name") or o.get("name")}
            for o in orgs
        ]

        projects = fetch_projects(args.profile)
        Path("harness_insights_projects.json").write_text(json.dumps(projects, indent=2))
        data_files.append("harness_insights_projects.json")
        data_summary["projects_count"] = len(projects)
        data_summary["projects_by_org"] = {}
        for p in projects:
            org = p.get("project", {}).get("orgIdentifier") or p.get("org", "unknown")
            name = p.get("project", {}).get("name") or p.get("name", "?")
            pid = p.get("project", {}).get("identifier") or p.get("identifier", "?")
            data_summary["projects_by_org"].setdefault(org, []).append({"id": pid, "name": name})

    if "executions" in needed:
        executions = fetch_executions(args.profile, projects)
        Path("harness_insights_executions.json").write_text(json.dumps(executions, indent=2))
        data_files.append("harness_insights_executions.json")
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        ms_24h = 24 * 60 * 60 * 1000
        ms_7d  = 7 * ms_24h
        ms_30d = 30 * ms_24h
        for window_name, window_ms in [("24h", ms_24h), ("7d", ms_7d), ("30d", ms_30d)]:
            window_execs = [e for e in executions if (e.get("startTs") or 0) >= now_ms - window_ms]
            by_status = {}
            for e in window_execs:
                s = e.get("status", "Unknown")
                by_status[s] = by_status.get(s, 0) + 1
            data_summary[f"executions_{window_name}"] = {
                "total": len(window_execs),
                "by_status": by_status,
            }
        data_summary["executions_total_fetched"] = len(executions)

    if "delegates" in needed:
        delegates = fetch_delegates(args.profile)
        Path("harness_insights_delegates.json").write_text(json.dumps(delegates, indent=2))
        data_files.append("harness_insights_delegates.json")
        data_summary["delegates_count"] = len(delegates)
        by_status = {}
        for d in delegates:
            s = d.get("activelyConnected", False)
            key = "connected" if s else "disconnected"
            by_status[key] = by_status.get(key, 0) + 1
        data_summary["delegates_by_status"] = by_status

    if "connectors" in needed:
        connectors = fetch_connectors(args.profile)
        Path("harness_insights_connectors.json").write_text(json.dumps(connectors, indent=2))
        data_files.append("harness_insights_connectors.json")
        data_summary["connectors_count"] = len(connectors)

    if "pipelines" in needed:
        # list pipeline is broken — note it
        data_summary["pipelines_note"] = (
            "harness list pipeline unavailable (v1 endpoint returns 500 on this account). "
            "Use execution data for pipeline-level analysis."
        )

    # emit summary to stdout for the command to pass to the agent
    print(json.dumps({
        "profile": args.profile,
        "question": args.question,
        "data_files": data_files,
        "data_summary": data_summary,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }))

    return 0


if __name__ == "__main__":
    sys.exit(main())
