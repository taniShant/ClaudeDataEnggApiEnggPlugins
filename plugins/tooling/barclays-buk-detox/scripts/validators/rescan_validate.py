#!/usr/bin/env python3
"""Run Semgrep rescan on a remediated file and compare before/after findings.

Input (JSON stdin):
    {
        "file_path": "/path/to/fixed_file.py",
        "cwe_id": "CWE-89",
        "baseline_findings": {"total_count": 3, "findings": [...]},
        "semgrep_config": "auto",
        "repo_root": "/path/to/repo"
    }

Output (JSON stdout):
    {"status": "success", "verdict": "PASS|PARTIAL|FAIL|ERROR", ...}
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output, run_cmd, log, progress, progress_done
from scripts.core.errors import error_exit


LINE_SHIFT_TOLERANCE = 10


def normalize_cwe_for_match(cwe: str) -> str:
    """Normalize CWE string for comparison."""
    m = re.match(r"(?i)cwe-?0*(\d+)", cwe)
    if m:
        return f"CWE-{m.group(1)}"
    return cwe.upper()


def finding_matches_cwe(finding: dict, target_cwe: str) -> bool:
    """Check if a semgrep finding matches the target CWE."""
    target_norm = normalize_cwe_for_match(target_cwe)

    metadata = finding.get("extra", {}).get("metadata", {})
    cwe_list = metadata.get("cwe", [])
    if isinstance(cwe_list, str):
        cwe_list = [cwe_list]

    for cwe_entry in cwe_list:
        if isinstance(cwe_entry, str):
            # Handle patterns like "CWE-89: SQL Injection"
            norm = normalize_cwe_for_match(cwe_entry.split(":")[0].strip())
            if norm == target_norm:
                return True
    return False


def compare_findings(
    baseline: list[dict], post_fix: list[dict], target_cwe: str
) -> dict:
    """Compare baseline vs post-fix findings with shift tolerance."""
    resolved = []
    persistent = []
    shifted = []
    new_findings = []

    # Track which post-fix findings have been matched
    matched_post = set()

    for b_finding in baseline:
        b_rule = b_finding.get("rule_id", "")
        b_line = b_finding.get("line", 0)
        found_match = False

        for i, p_finding in enumerate(post_fix):
            if i in matched_post:
                continue
            p_rule = p_finding.get("check_id", "")
            p_line = p_finding.get("start", {}).get("line", 0)

            if b_rule == p_rule:
                line_diff = abs(b_line - p_line)
                if line_diff == 0:
                    # Exact match — persistent
                    persistent.append({
                        "rule_id": b_rule,
                        "baseline_line": b_line,
                        "post_fix_line": p_line,
                        "status": "persistent",
                    })
                    matched_post.add(i)
                    found_match = True
                    break
                elif line_diff <= LINE_SHIFT_TOLERANCE:
                    # Shifted
                    shifted.append({
                        "rule_id": b_rule,
                        "baseline_line": b_line,
                        "post_fix_line": p_line,
                        "shift": line_diff,
                        "status": "shifted",
                    })
                    matched_post.add(i)
                    found_match = True
                    break

        if not found_match:
            resolved.append({
                "rule_id": b_rule,
                "baseline_line": b_line,
                "status": "resolved",
            })

    # Any unmatched post-fix findings are new
    for i, p_finding in enumerate(post_fix):
        if i not in matched_post:
            new_findings.append({
                "rule_id": p_finding.get("check_id", ""),
                "line": p_finding.get("start", {}).get("line", 0),
                "message": p_finding.get("extra", {}).get("message", ""),
                "status": "new",
            })

    return {
        "resolved_count": len(resolved),
        "persistent_count": len(persistent),
        "shifted_count": len(shifted),
        "new_count": len(new_findings),
        "resolved": resolved,
        "persistent": persistent,
        "shifted": shifted,
        "new": new_findings,
    }


def determine_verdict(comparison: dict, baseline_count: int) -> str:
    """Determine PASS/PARTIAL/FAIL/ERROR verdict."""
    resolved = comparison["resolved_count"]
    persistent = comparison["persistent_count"]
    new_count = comparison["new_count"]

    # All resolved, no new findings
    if resolved == baseline_count and new_count == 0:
        return "PASS"

    # Some resolved but some persist or new ones introduced
    if resolved > 0 and (persistent > 0 or new_count > 0):
        return "PARTIAL"

    # More findings after fix than before
    post_total = persistent + comparison["shifted_count"] + new_count
    if post_total >= baseline_count:
        return "FAIL"

    # Some resolved, no new
    if resolved > 0:
        return "PARTIAL"

    return "FAIL"


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    file_path = input_data.get("file_path", "")
    cwe_id = input_data.get("cwe_id", "")
    baseline_findings = input_data.get("baseline_findings", {})
    semgrep_config = input_data.get("semgrep_config", "auto")
    repo_root = input_data.get("repo_root")

    # --- Validate ---
    if not file_path:
        error_exit("file_path is required", "input_validation")
    if not Path(file_path).exists():
        error_exit(f"File not found: {file_path}", "file_check")

    if not cwe_id:
        error_exit("cwe_id is required", "input_validation")
    cwe_id = normalize_cwe_for_match(cwe_id)

    baseline_count = baseline_findings.get("total_count", 0)
    baseline_list = baseline_findings.get("findings", [])
    if not isinstance(baseline_list, list):
        error_exit("baseline_findings.findings must be a list", "input_validation")

    progress(f"Rescanning {file_path} for {cwe_id}...")

    # --- Verify semgrep ---
    result = run_cmd(["semgrep", "--version"])
    if result["exit_code"] != 0:
        error_exit(
            "Semgrep is not installed or not on PATH. Install with: pip install semgrep",
            "semgrep_check",
        )
    semgrep_version = result["stdout"].strip()

    # --- Run semgrep (list-form: injection-safe) ---
    log(f"Running semgrep rescan on {file_path} for {cwe_id}")
    cmd = ["semgrep", "--config", semgrep_config, "--json", file_path]
    result = run_cmd(cmd, cwd=repo_root, timeout=120)

    if result["exit_code"] != 0 and not result["stdout"].strip():
        stderr = result["stderr"]
        if "syntax" in stderr.lower() or "parse" in stderr.lower():
            write_json_output({
                "status": "success",
                "verdict": "FAIL",
                "cwe_id": cwe_id,
                "file_path": file_path,
                "error_detail": "Fix introduced syntax errors in the file.",
                "baseline": baseline_findings,
                "post_fix": {"total_count": 0, "findings": []},
                "comparison": {},
                "semgrep_metadata": {"version": semgrep_version, "error": stderr[:500]},
            }, start_time=start_time)
            return
        error_exit(f"Semgrep scan failed: {stderr[:500]}", "semgrep_run")

    # --- Parse output ---
    try:
        semgrep_output = json.loads(result["stdout"])
    except json.JSONDecodeError:
        error_exit(
            f"Semgrep output is not valid JSON. First 500 chars: {result['stdout'][:500]}",
            "semgrep_parse",
        )

    all_results = semgrep_output.get("results", [])
    total_all_cwes = len(all_results)

    # --- Filter to target CWE ---
    cwe_findings = [f for f in all_results if finding_matches_cwe(f, cwe_id)]
    post_fix_count = len(cwe_findings)

    # --- Compare ---
    comparison = compare_findings(baseline_list, cwe_findings, cwe_id)

    # --- Verdict ---
    if baseline_count == 0:
        # Edge case: baseline was empty
        verdict = "PASS" if post_fix_count == 0 else "FAIL"
    else:
        verdict = determine_verdict(comparison, baseline_count)

    progress_done(f"Rescan {verdict} — {cwe_id} ({post_fix_count} findings post-fix)")

    # Build post-fix findings summary
    post_fix_summary = []
    for f in cwe_findings[:100]:  # Truncate at 100
        post_fix_summary.append({
            "rule_id": f.get("check_id", ""),
            "line": f.get("start", {}).get("line", 0),
            "message": f.get("extra", {}).get("message", "")[:200],
        })

    write_json_output({
        "status": "success",
        "verdict": verdict,
        "cwe_id": cwe_id,
        "file_path": file_path,
        "baseline": {
            "total_count": baseline_count,
            "findings": baseline_list,
        },
        "post_fix": {
            "total_count": post_fix_count,
            "findings": post_fix_summary,
        },
        "comparison": comparison,
        "semgrep_metadata": {
            "version": semgrep_version,
            "config_used": semgrep_config,
            "total_findings_all_cwes": total_all_cwes,
        },
    }, start_time=start_time)


if __name__ == "__main__":
    main()
