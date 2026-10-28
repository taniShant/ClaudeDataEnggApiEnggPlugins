#!/usr/bin/env python3
"""Compare pre-fix vs post-fix WIZ scan JSON outputs to determine remediation verdict.

Input (JSON stdin) — file paths:
    {
        "baseline_scan_path": "/tmp/baseline.json",
        "postfix_scan_path": "/tmp/postfix.json",
        "target_cwe": "CWE-89",
        "target_file": "src/db/queries.py"
    }

Input (JSON stdin) — inline data:
    {
        "baseline_scan": { ... WIZ scan JSON ... },
        "postfix_scan": { ... WIZ scan JSON ... },
        "target_cwe": "CWE-89",
        "target_file": "src/db/queries.py"
    }

Output (JSON stdout):
    {
        "status": "success",
        "verdict": "PASS",
        "target_cwe": "CWE-89",
        "target_file": "src/db/queries.py",
        "baseline_count": 2,
        "postfix_count": 0,
        "delta": {
            "resolved": [...],
            "persistent": [...],
            "new": [...],
            "resolved_count": 2,
            "persistent_count": 0,
            "new_count": 0
        }
    }
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output, log, progress, progress_done
from scripts.core.errors import error_exit


def normalize_cwe(cwe: str) -> str:
    """Normalize CWE string for comparison (e.g., 'cwe-089' -> 'CWE-89')."""
    m = re.match(r"(?i)cwe-?0*(\d+)", cwe)
    if m:
        return f"CWE-{m.group(1)}"
    return cwe.upper()


def extract_findings(scan_data: dict, target_cwe: str | None = None, target_file: str | None = None) -> list[dict]:
    """Extract SAST findings from WIZ CloudEvent JSON, optionally filtered by CWE and file.

    Real WIZ schema:
      scan_data["extraDetails"]["sastDetails"]["findings"][]
      Each finding has:
        .id, .name, .filePath, .startLine, .severity,
        .weaknesses[].id (e.g., "CWE-89"),
        .rule.id (e.g., "WS-SQL-INJECT-001")

    If target_cwe is provided, only return findings whose weaknesses list contains the target.
    If target_file is provided, only return findings for that file path.
    """
    extra = scan_data.get("extraDetails", {})
    sast = extra.get("sastDetails", {})
    findings = sast.get("findings", [])

    if not findings:
        return []

    filtered = []
    for finding in findings:
        if target_cwe is not None:
            weaknesses = finding.get("weaknesses", [])
            normalized_target = normalize_cwe(target_cwe)
            cwe_ids = [
                w.get("id", "") if isinstance(w, dict) else str(w)
                for w in weaknesses
            ]
            if not any(normalize_cwe(c) == normalized_target for c in cwe_ids):
                continue

        if target_file is not None:
            if finding.get("filePath", "") != target_file:
                continue

        filtered.append(finding)

    return filtered


def get_finding_group_key(finding: dict) -> tuple[str, str, str]:
    """Extract a group key from a WIZ finding: (file_path, rule_id, first_cwe).

    Real WIZ schema:
      .filePath, .rule.id, .weaknesses[0].id

    Used to group findings — NOT for 1:1 matching. Multiple findings
    can share a group key (same rule hitting same file multiple times).
    """
    file_path = finding.get("filePath", "")
    rule = finding.get("rule", {})
    rule_id = rule.get("id", "") if isinstance(rule, dict) else str(rule)
    weaknesses = finding.get("weaknesses", [])
    first_cwe = ""
    if weaknesses and isinstance(weaknesses[0], dict):
        first_cwe = normalize_cwe(weaknesses[0].get("id", ""))
    elif weaknesses:
        first_cwe = normalize_cwe(str(weaknesses[0]))
    return (file_path, rule_id, first_cwe)


# Keep for backward compatibility (tests import this name)
normalize_wiz_finding = get_finding_group_key


def _summarise(finding: dict) -> dict:
    """Extract a summary dict from a WIZ finding for reporting."""
    weaknesses = finding.get("weaknesses", [])
    first_cwe = ""
    if weaknesses and isinstance(weaknesses[0], dict):
        first_cwe = normalize_cwe(weaknesses[0].get("id", ""))
    elif weaknesses:
        first_cwe = normalize_cwe(str(weaknesses[0]))
    rule = finding.get("rule", {})
    rule_id = rule.get("id", "") if isinstance(rule, dict) else str(rule)
    return {
        "finding_id": finding.get("id", ""),
        "rule_id": rule_id,
        "file_path": finding.get("filePath", ""),
        "cwe": first_cwe,
    }


def compare_wiz_findings(baseline: list[dict], postfix: list[dict]) -> dict:
    """Compare baseline vs post-fix WIZ findings using count-based comparison.

    Groups findings by (file_path, rule_id, cwe). For each group, compares
    the COUNT in baseline vs postfix. This handles multiple findings with the
    same rule in the same file (e.g., 3 XSS findings in dashboard.js).

    Returns:
    {
        "resolved": [{"finding_id": "...", "rule_id": "...", "file_path": "...", "cwe": "..."}],
        "persistent": [...],
        "new": [...],
        "resolved_count": int,
        "persistent_count": int,
        "new_count": int
    }
    """
    # Group findings by key, preserving all findings per group
    def _group(findings: list[dict]) -> dict[tuple, list[dict]]:
        groups: dict[tuple, list[dict]] = {}
        for f in findings:
            key = get_finding_group_key(f)
            groups.setdefault(key, []).append(f)
        return groups

    baseline_groups = _group(baseline)
    postfix_groups = _group(postfix)

    all_keys = set(baseline_groups.keys()) | set(postfix_groups.keys())

    resolved = []
    persistent = []
    new_findings = []

    for key in all_keys:
        b_list = baseline_groups.get(key, [])
        p_list = postfix_groups.get(key, [])
        b_count = len(b_list)
        p_count = len(p_list)

        if b_count > 0 and p_count == 0:
            # All findings in this group were resolved
            resolved.extend(_summarise(f) for f in b_list)
        elif b_count == 0 and p_count > 0:
            # All findings in this group are new
            new_findings.extend(_summarise(f) for f in p_list)
        else:
            # Some persist — min(b, p) are persistent, rest are resolved or new
            persist_count = min(b_count, p_count)
            persistent.extend(_summarise(f) for f in p_list[:persist_count])
            if b_count > p_count:
                # Extra baseline findings were resolved
                resolved.extend(_summarise(f) for f in b_list[p_count:])
            elif p_count > b_count:
                # Extra postfix findings are new
                new_findings.extend(_summarise(f) for f in p_list[b_count:])

    return {
        "resolved": resolved,
        "persistent": persistent,
        "new": new_findings,
        "resolved_count": len(resolved),
        "persistent_count": len(persistent),
        "new_count": len(new_findings),
    }


def determine_verdict(comparison: dict, baseline_count: int) -> str:
    """Determine PASS/PARTIAL/FAIL verdict.

    - PASS: all resolved, no new
    - PARTIAL: some resolved but some persist or new ones appeared
    - FAIL: nothing resolved or more findings after fix
    """
    resolved = comparison["resolved_count"]
    persistent = comparison["persistent_count"]
    new_count = comparison["new_count"]

    # All resolved, no new findings
    if resolved == baseline_count and new_count == 0:
        return "PASS"

    # Some resolved but some persist or new ones introduced
    if resolved > 0 and (persistent > 0 or new_count > 0):
        return "PARTIAL"

    # More findings after fix than before, or nothing resolved
    post_total = persistent + new_count
    if post_total >= baseline_count:
        return "FAIL"

    # Some resolved, no new
    if resolved > 0:
        return "PARTIAL"

    return "FAIL"


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    target_cwe = input_data.get("target_cwe")
    target_file = input_data.get("target_file")

    # Normalise target CWE if provided
    if target_cwe:
        target_cwe = normalize_cwe(target_cwe)

    # Load baseline scan — either inline or from file path
    baseline_scan = input_data.get("baseline_scan")
    if baseline_scan is None:
        baseline_scan_path = input_data.get("baseline_scan_path", "")
        if not baseline_scan_path:
            error_exit("Either baseline_scan or baseline_scan_path is required", "input_validation")
        p = Path(baseline_scan_path)
        if not p.exists():
            error_exit(f"baseline_scan_path not found: {baseline_scan_path}", "file_check")
        try:
            baseline_scan = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            error_exit(f"baseline_scan_path is not valid JSON: {exc}", "json_parse")

    # Load postfix scan — either inline or from file path
    postfix_scan = input_data.get("postfix_scan")
    if postfix_scan is None:
        postfix_scan_path = input_data.get("postfix_scan_path", "")
        if not postfix_scan_path:
            error_exit("Either postfix_scan or postfix_scan_path is required", "input_validation")
        p = Path(postfix_scan_path)
        if not p.exists():
            error_exit(f"postfix_scan_path not found: {postfix_scan_path}", "file_check")
        try:
            postfix_scan = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            error_exit(f"postfix_scan_path is not valid JSON: {exc}", "json_parse")

    filter_desc = target_cwe or "all CWEs"
    if target_file:
        filter_desc += f" in {target_file}"
    progress(f"Comparing WIZ scans for {filter_desc}...")

    # Extract findings filtered by CWE and file
    log(f"Extracting baseline findings (target_cwe={target_cwe}, target_file={target_file})")
    baseline_findings = extract_findings(baseline_scan, target_cwe=target_cwe, target_file=target_file)
    baseline_count = len(baseline_findings)

    log("Extracting post-fix findings")
    postfix_findings = extract_findings(postfix_scan, target_cwe=target_cwe, target_file=target_file)
    postfix_count = len(postfix_findings)

    # Compare
    comparison = compare_wiz_findings(baseline_findings, postfix_findings)

    # Verdict
    if baseline_count == 0:
        verdict = "PASS" if postfix_count == 0 else "FAIL"
    else:
        verdict = determine_verdict(comparison, baseline_count)

    progress_done(f"WIZ delta {verdict} — baseline={baseline_count}, post-fix={postfix_count}")

    write_json_output({
        "status": "success",
        "verdict": verdict,
        "target_cwe": target_cwe,
        "target_file": target_file,
        "baseline_count": baseline_count,
        "postfix_count": postfix_count,
        "delta": comparison,
    }, start_time=start_time)


if __name__ == "__main__":
    main()
