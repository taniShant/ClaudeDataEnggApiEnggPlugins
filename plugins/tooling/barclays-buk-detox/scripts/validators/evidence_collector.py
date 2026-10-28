#!/usr/bin/env python3
"""Collect verification evidence for a remediated CWE finding.

Uses a fallback chain: WIZ CLI rescan → Semgrep rescan → dependency tree → none.
Produces a structured evidence record with accountability classification.

Input (JSON stdin):
    {
        "finding": {"id": "...", "cwe_id": "CWE-89", "file_path": "...", ...},
        "fix_result": {"commit_sha": "...", "status": "success", ...},
        "repo_dir": "/path/to/repo",
        "wiz_baseline_scan_path": "/tmp/baseline.json",
        "verification_methods": ["wiz_cli", "semgrep", "dep_tree"]
    }

Output (JSON stdout):
    {
        "status": "success",
        "evidence": {
            "finding_id": "...",
            "cwe_id": "CWE-89",
            "file_path": "...",
            "original_finding": {...},
            "fix_applied": {...},
            "verification": {"method": "wiz_cli", "verdict": "RESOLVED", "confidence": "high", ...},
            "accountability": {"fixed_by": "detox-pipeline", "verified_by": "wizcli v0.105.0", "classification": "VERIFIED"}
        }
    }
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output, log, progress, progress_done
from scripts.core.errors import error_exit


# --- Confidence levels by verification method ---
CONFIDENCE_MAP = {
    "wiz_cli": "high",
    "semgrep": "medium",
    "dep_tree": "low",
    "none": "none",
}


# --- Classification logic ---

def classify_evidence(verification: dict[str, Any]) -> str:
    """Determine VERIFIED/UNVERIFIED/FAILED from verification result.

    - VERIFIED: WIZ CLI confirms finding resolved (confidence high).
    - FAILED: Any verifier says finding persists or new findings introduced.
    - UNVERIFIED: Semgrep/dep_tree/none — cannot definitively confirm with WIZ.
    """
    verdict = verification.get("verdict", "")
    method = verification.get("method", "none")
    confidence = verification.get("confidence", "none")

    if verdict in ("FAIL", "PARTIAL"):
        return "FAILED"
    if verdict in ("PASS", "RESOLVED") and confidence == "high":
        return "VERIFIED"
    if verdict in ("PASS", "RESOLVED") and confidence in ("medium", "low"):
        return "UNVERIFIED"
    return "UNVERIFIED"


def build_evidence_record(
    finding: dict[str, Any],
    fix_result: dict[str, Any],
    verification: dict[str, Any],
) -> dict[str, Any]:
    """Assemble the canonical evidence record."""
    classification = classify_evidence(verification)

    return {
        "finding_id": finding.get("id", ""),
        "cwe_id": finding.get("cwe_id", ""),
        "file_path": finding.get("file_path", ""),
        "original_finding": {
            "source": finding.get("source", finding.get("tool_name", "unknown")),
            "rule_id": finding.get("rule_id", ""),
            "severity": finding.get("severity", ""),
            "title": finding.get("title", ""),
            "scan_date": finding.get("scan_date", ""),
        },
        "fix_applied": {
            "commit_sha": fix_result.get("commit_sha", ""),
            "diff_summary": fix_result.get("description", fix_result.get("title", "")),
            "files_modified": fix_result.get("files_modified", []),
            "timestamp": fix_result.get("timestamp", datetime.now(timezone.utc).isoformat()),
        },
        "verification": verification,
        "accountability": {
            "fixed_by": "detox-pipeline",
            "verified_by": verification.get("verified_by", verification.get("method", "none")),
            "classification": classification,
        },
    }


# --- Verification methods ---

def run_wiz_postfix_scan(repo_dir: str) -> dict[str, Any] | None:
    """Run a single WIZ CLI post-fix scan and return the parsed scan data.

    Call ONCE for the whole repo, then pass the result to try_wiz_verification()
    for each finding. This avoids O(n) scans for n findings.

    Returns parsed scan data dict, or None if WIZ is unavailable/failed.
    """
    try:
        from scripts.validators.wiz_rescan import check_wizcli_installed, check_wizcli_auth, run_wiz_scan
    except ImportError:
        log("WIZ verification modules not available")
        return None

    install_check = check_wizcli_installed()
    if not install_check.get("installed"):
        log("wizcli not installed — skipping WIZ verification")
        return None

    auth_check = check_wizcli_auth()
    if not auth_check.get("authenticated"):
        log("wizcli not authenticated — skipping WIZ verification")
        return None

    # Use a temp file for scan output, always cleaned up
    postfix_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            postfix_path = tmp.name

        scan_result = run_wiz_scan(repo_dir, postfix_path)
        if scan_result.get("status") != "success":
            log(f"WIZ post-fix scan failed: {scan_result.get('reason', 'unknown')}")
            return None

        with open(postfix_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log(f"Failed to read post-fix scan: {e}")
        return None
    finally:
        if postfix_path:
            try:
                Path(postfix_path).unlink(missing_ok=True)
            except OSError:
                pass


def try_wiz_verification(
    finding: dict[str, Any],
    baseline_scan_data: dict[str, Any] | None,
    postfix_scan_data: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Compare a single finding against pre-scanned WIZ baseline and postfix data.

    Both baseline_scan_data and postfix_scan_data should be loaded ONCE and
    passed in for each finding — no per-finding scanning.

    Returns verification dict or None if data is unavailable.
    """
    try:
        from scripts.validators.wiz_rescan import check_wizcli_installed
        from scripts.validators.wiz_delta_comparator import extract_findings, compare_wiz_findings, determine_verdict
        from scripts.validators.scan_metadata import extract_metadata
    except ImportError:
        log("WIZ verification modules not available")
        return None

    if baseline_scan_data is None or postfix_scan_data is None:
        return None

    # Extract and compare for this specific finding
    target_cwe = finding.get("cwe_id")
    target_file = finding.get("file_path")

    baseline_findings = extract_findings(baseline_scan_data, target_cwe, target_file)
    postfix_findings = extract_findings(postfix_scan_data, target_cwe, target_file)

    comparison = compare_wiz_findings(baseline_findings, postfix_findings)
    verdict = determine_verdict(comparison, len(baseline_findings))

    # Map verdict
    verdict_map = {"PASS": "RESOLVED", "PARTIAL": "PARTIAL", "FAIL": "PERSISTENT"}
    mapped_verdict = verdict_map.get(verdict, verdict)

    # Get version info
    try:
        install_check = check_wizcli_installed()
        wizcli_version = install_check.get("version", "unknown")
    except Exception:
        wizcli_version = "unknown"

    metadata = extract_metadata(postfix_scan_data)

    return {
        "method": "wiz_cli",
        "verdict": mapped_verdict,
        "confidence": "high",
        "verified_by": f"wizcli {wizcli_version}",
        "pre_scan": {
            "finding_count": len(baseline_findings),
            "scan_id": extract_metadata(baseline_scan_data).get("scan_id", ""),
        },
        "post_scan": {
            "finding_count": len(postfix_findings),
            "scan_id": metadata.get("scan_id", ""),
        },
        "delta": {
            "resolved": comparison.get("resolved_count", 0),
            "persistent": comparison.get("persistent_count", 0),
            "new": comparison.get("new_count", 0),
        },
    }


def try_semgrep_verification(
    finding: dict[str, Any],
    repo_dir: str,
    baseline_semgrep_count: int | None = None,
) -> dict[str, Any] | None:
    """Attempt Semgrep rescan verification. Returns verification dict or None if unavailable.

    Scans the SPECIFIC file (not the whole repo) to avoid false PERSISTENT
    verdicts caused by the same CWE in unrelated files.

    Args:
        finding: The vulnerability finding being verified.
        repo_dir: Path to the repository root.
        baseline_semgrep_count: If provided, the number of Semgrep findings for this
            CWE in this file BEFORE the fix. If None, defaults to 1 (we know the
            finding existed since we're verifying it).
    """
    try:
        from scripts.validators.rescan_validate import (
            normalize_cwe_for_match,
        )
    except ImportError:
        log("Semgrep verification module not available")
        return None

    from scripts.utils.common import run_cmd

    # Check semgrep installed
    result = run_cmd(["semgrep", "--version"])
    if result["exit_code"] != 0:
        log("semgrep not installed — skipping Semgrep verification")
        return None

    semgrep_version = result["stdout"].strip()
    file_path = finding.get("file_path", "")

    if not file_path or not Path(file_path).exists():
        # Try relative to repo_dir
        if file_path and Path(repo_dir, file_path).exists():
            file_path = str(Path(repo_dir, file_path))
        else:
            log(f"File not found for Semgrep verification: {file_path}")
            return None

    # Run semgrep on the SPECIFIC file only — not the whole repo
    cmd = ["semgrep", "--config", "auto", "--json", file_path]
    result = run_cmd(cmd, cwd=repo_dir, timeout=120)

    if result["exit_code"] != 0 and not result["stdout"].strip():
        log(f"Semgrep scan failed: {result['stderr'][:200]}")
        return None

    try:
        output = json.loads(result["stdout"])
    except json.JSONDecodeError:
        log("Semgrep output not valid JSON")
        return None

    cwe_id = finding.get("cwe_id", "")
    all_results = output.get("results", [])

    # Count findings for the target CWE in this specific file only
    cwe_norm = normalize_cwe_for_match(cwe_id)
    postfix_count = 0
    for r in all_results:
        # Only count findings in the target file (Semgrep can sometimes resolve paths differently)
        result_path = r.get("path", "")
        if result_path and not (result_path == file_path or result_path.endswith(file_path) or file_path.endswith(result_path)):
            continue

        meta = r.get("extra", {}).get("metadata", {})
        cwe_list = meta.get("cwe", [])
        if isinstance(cwe_list, str):
            cwe_list = [cwe_list]
        for c in cwe_list:
            if normalize_cwe_for_match(c.split(":")[0].strip()) == cwe_norm:
                postfix_count += 1
                break

    # Use provided baseline count, or default to 1 (we know at least 1 existed)
    pre_count = baseline_semgrep_count if baseline_semgrep_count is not None else 1

    # Compare: if post-fix has fewer findings for this CWE in this file, it's progress
    if postfix_count == 0:
        verdict = "RESOLVED"
        resolved = pre_count
        persistent = 0
    elif postfix_count < pre_count:
        verdict = "PARTIAL"
        resolved = pre_count - postfix_count
        persistent = postfix_count
    else:
        verdict = "PERSISTENT"
        resolved = 0
        persistent = postfix_count

    return {
        "method": "semgrep",
        "verdict": verdict,
        "confidence": "medium",
        "verified_by": f"semgrep {semgrep_version}",
        "pre_scan": {
            "finding_count": pre_count,
        },
        "post_scan": {
            "finding_count": postfix_count,
        },
        "delta": {
            "resolved": resolved,
            "persistent": persistent,
            "new": max(0, postfix_count - pre_count),
        },
    }


def try_dep_tree_verification(
    finding: dict[str, Any],
    fix_result: dict[str, Any],
    repo_dir: str,
) -> dict[str, Any] | None:
    """Attempt dependency tree verification for CWE-937 findings."""
    cwe_id = finding.get("cwe_id", "")
    if cwe_id != "CWE-937":
        return None

    try:
        from scripts.validators.dependency_verifier import (
            detect_ecosystem,
            resolve_dep_tree,
            check_version_absent,
            check_version_present,
        )
    except ImportError:
        log("Dependency verifier module not available")
        return None

    package_name = finding.get("affected_package", finding.get("package_name", ""))
    vulnerable_version = finding.get("current_version", finding.get("vulnerable_version", ""))
    safe_version = finding.get("safe_version", "")

    if not package_name or not vulnerable_version:
        log("Missing package_name or vulnerable_version for dep tree verification")
        return None

    ecosystem = detect_ecosystem(repo_dir)
    if not ecosystem:
        log("Could not detect build ecosystem")
        return None

    dep_result = resolve_dep_tree(repo_dir, ecosystem, package_name)
    if dep_result.get("status") != "success":
        log(f"Dependency tree resolution failed: {dep_result.get('error', 'unknown')}")
        return None

    dep_output = dep_result.get("output", "")
    vuln_absent = check_version_absent(dep_output, package_name, vulnerable_version)
    safe_present = check_version_present(dep_output, package_name, safe_version) if safe_version else None

    if vuln_absent:
        verdict = "RESOLVED"
    else:
        verdict = "PERSISTENT"

    return {
        "method": "dep_tree",
        "verdict": verdict,
        "confidence": "low",
        "verified_by": f"dep_tree ({ecosystem})",
        "ecosystem": ecosystem,
        "vulnerable_version_found": not vuln_absent,
        "safe_version_found": safe_present,
        "delta": {
            "resolved": 1 if vuln_absent else 0,
            "persistent": 0 if vuln_absent else 1,
            "new": 0,
        },
    }


def collect_evidence(
    finding: dict[str, Any],
    fix_result: dict[str, Any],
    repo_dir: str,
    wiz_baseline_scan_path: str | None = None,
    wiz_baseline_scan_data: dict[str, Any] | None = None,
    wiz_postfix_scan_data: dict[str, Any] | None = None,
    verification_methods: list[str] | None = None,
) -> dict[str, Any]:
    """Run the fallback verification chain and build an evidence record.

    Priority order: wiz_cli → semgrep → dep_tree.
    Every method that fails logs WHY. If all fail, the reason is captured
    in the evidence record so the developer knows exactly what to fix.

    For WIZ verification, pass pre-loaded scan data (wiz_baseline_scan_data and
    wiz_postfix_scan_data). This avoids running O(n) WIZ scans for n findings.
    If scan data is not pre-loaded but wiz_baseline_scan_path is given, the
    baseline will be loaded from file (but no post-fix scan will be run here —
    use run_wiz_postfix_scan() beforehand).
    """
    if verification_methods is None:
        verification_methods = ["wiz_cli", "semgrep", "dep_tree"]

    # Load baseline from file if not passed as data
    if wiz_baseline_scan_data is None and wiz_baseline_scan_path:
        try:
            with open(wiz_baseline_scan_path) as f:
                wiz_baseline_scan_data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log(f"Failed to read baseline scan: {e}")

    verification: dict[str, Any] | None = None
    skip_reasons: list[str] = []

    # Try each method in priority order, track why each one was skipped
    for method in verification_methods:
        if method == "wiz_cli" and verification is None:
            verification = try_wiz_verification(finding, wiz_baseline_scan_data, wiz_postfix_scan_data)
            if verification:
                log(f"Evidence collected via WIZ CLI: {verification['verdict']}")
            else:
                reason = _diagnose_wiz_skip(wiz_baseline_scan_path, wiz_baseline_scan_data, wiz_postfix_scan_data)
                skip_reasons.append(f"wiz_cli: {reason}")

        elif method == "semgrep" and verification is None:
            verification = try_semgrep_verification(finding, repo_dir)
            if verification:
                log(f"Evidence collected via Semgrep: {verification['verdict']}")
            else:
                reason = _diagnose_semgrep_skip(finding, repo_dir)
                skip_reasons.append(f"semgrep: {reason}")

        elif method == "dep_tree" and verification is None:
            verification = try_dep_tree_verification(finding, fix_result, repo_dir)
            if verification:
                log(f"Evidence collected via dep tree: {verification['verdict']}")
            else:
                cwe_id = finding.get("cwe_id", "")
                if cwe_id != "CWE-937":
                    skip_reasons.append("dep_tree: only applies to CWE-937 (dependency fixes)")
                else:
                    skip_reasons.append("dep_tree: build tool not found or dep resolution failed")

    # Fallback: no verification was possible — explain WHY
    if verification is None:
        reason_text = "; ".join(skip_reasons) if skip_reasons else "no verification methods configured"
        log(f"No verification succeeded — {reason_text}")

        verification = {
            "method": "none",
            "verdict": "UNVERIFIED",
            "confidence": "none",
            "verified_by": "none",
            "reason": reason_text,
            "action_required": _suggest_action(skip_reasons),
            "delta": {"resolved": 0, "persistent": 0, "new": 0},
        }

    return build_evidence_record(finding, fix_result, verification)


def _diagnose_wiz_skip(
    baseline_path: str | None,
    baseline_data: dict[str, Any] | None = None,
    postfix_data: dict[str, Any] | None = None,
) -> str:
    """Diagnose why WIZ verification was skipped."""
    try:
        from scripts.validators.wiz_rescan import check_wizcli_installed, check_wizcli_auth
    except ImportError:
        return "wiz_rescan module not available"

    install = check_wizcli_installed()
    if not install.get("installed"):
        return "wizcli not installed — run: brew install --cask wizcli"

    auth = check_wizcli_auth()
    if not auth.get("authenticated"):
        return "wizcli not authenticated — run: wizcli auth --use-device-code"

    if baseline_data is None:
        if not baseline_path:
            return "no baseline scan available (WIZ baseline scan was not captured in Stage 0b)"
        if not Path(baseline_path).exists():
            return f"baseline scan file missing: {baseline_path}"
        return "baseline scan file could not be parsed as JSON"

    if postfix_data is None:
        return "WIZ post-fix scan failed or was not run (call run_wiz_postfix_scan() first)"

    return "WIZ comparison returned no result (unexpected — check scan data format)"


def _diagnose_semgrep_skip(finding: dict[str, Any], repo_dir: str) -> str:
    """Diagnose why Semgrep verification was skipped."""
    from scripts.utils.common import run_cmd

    result = run_cmd(["semgrep", "--version"])
    if result["exit_code"] != 0:
        return "semgrep not installed — run: brew install semgrep"

    file_path = finding.get("file_path", "")
    if not file_path:
        return "finding has no file_path (may be an infra/manual finding, not a code fix)"

    if not Path(file_path).exists() and not Path(repo_dir, file_path).exists():
        return f"file not found: {file_path}"

    return "semgrep scan failed on this file (check for syntax errors in the fix)"


def _suggest_action(skip_reasons: list[str]) -> str:
    """Suggest what the developer should do to get verification."""
    if any("wizcli not installed" in r for r in skip_reasons):
        return "Install WIZ CLI: brew install --cask wizcli && wizcli auth --use-device-code"
    if any("wizcli not authenticated" in r for r in skip_reasons):
        return "Authenticate WIZ CLI: wizcli auth --use-device-code"
    if any("no file_path" in r for r in skip_reasons):
        return "This is an infrastructure/manual finding — no code verification applies. See corrective action docs."
    if any("semgrep" in r and "not installed" in r for r in skip_reasons):
        return "Install Semgrep: brew install semgrep"
    if any("file not found" in r for r in skip_reasons):
        return "The source file was not found — check that the fix was applied to the correct path."
    return "Re-run the pipeline with WIZ CLI installed and authenticated for VERIFIED evidence."


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    finding = input_data.get("finding")
    fix_result = input_data.get("fix_result")
    repo_dir = input_data.get("repo_dir", "")
    wiz_baseline_scan_path = input_data.get("wiz_baseline_scan_path")
    wiz_postfix_scan_path = input_data.get("wiz_postfix_scan_path")
    verification_methods = input_data.get("verification_methods", ["wiz_cli", "semgrep", "dep_tree"])

    if not finding:
        error_exit("finding is required", "input_validation")
    if not fix_result:
        error_exit("fix_result is required", "input_validation")

    progress(f"Collecting evidence for {finding.get('cwe_id', 'unknown')} in {finding.get('file_path', 'unknown')}...")

    # Load pre-scanned data if paths provided (scan once, compare per finding)
    wiz_baseline_scan_data = None
    wiz_postfix_scan_data = None

    if wiz_baseline_scan_path:
        try:
            with open(wiz_baseline_scan_path) as f:
                wiz_baseline_scan_data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log(f"Failed to read baseline scan: {e}")

    if wiz_postfix_scan_path:
        try:
            with open(wiz_postfix_scan_path) as f:
                wiz_postfix_scan_data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log(f"Failed to read post-fix scan: {e}")

    evidence = collect_evidence(
        finding=finding,
        fix_result=fix_result,
        repo_dir=repo_dir,
        wiz_baseline_scan_path=wiz_baseline_scan_path,
        wiz_baseline_scan_data=wiz_baseline_scan_data,
        wiz_postfix_scan_data=wiz_postfix_scan_data,
        verification_methods=verification_methods,
    )

    classification = evidence.get("accountability", {}).get("classification", "UNVERIFIED")
    progress_done(f"Evidence: {classification} (method: {evidence.get('verification', {}).get('method', 'none')})")

    write_json_output({
        "status": "success",
        "evidence": evidence,
    }, start_time=start_time)


if __name__ == "__main__":
    main()
