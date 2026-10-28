#!/usr/bin/env python3
"""Extract metadata and finding summaries from WIZ CLI scan JSON output.

Input (JSON stdin):
    {
        "scan_output_path": "/tmp/wiz-scan.json"
    }

    OR (inline scan data):

    {
        "scan_data": { ... }
    }

Output (JSON stdout):
    {
        "status": "success",
        "metadata": {
            "scan_id": "scan-abc123",
            "scan_status": "COMPLETED",
            "started_at": "...",
            "completed_at": "...",
            "policy_result": "FAILED",
            "policies": [{"name": "...", "result": "..."}]
        },
        "summary": {
            "total_findings": 4,
            "code_findings": 4,
            "library_findings": 1,
            "secret_findings": 0,
            "iac_findings": 0,
            "by_severity": {"CRITICAL": 2, "HIGH": 2},
            "by_cwe": {"CWE-89": 2, "CWE-79": 1, "CWE-798": 1},
            "by_file": {"src/db/queries.py": 2, "src/web/views.py": 1, ...}
        }
    }
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output, log
from scripts.core.errors import error_exit


def extract_metadata(scan_data: dict[str, Any]) -> dict[str, Any]:
    """Extract scan-level metadata from WIZ CloudEvent JSON.

    Real WIZ schema (from CI/CD scan export):
      .id                                  — scan UUID
      .status                              — SUCCESS / FAILED
      .timestamp                           — scan timestamp
      .rawAuditLogRecord.startedAt         — scan start time
      .rawAuditLogRecord.createdAt         — scan end time
      .rawAuditLogRecord.failedPolicies[]  — policies that failed
      .rawAuditLogRecord.passedPolicies[]  — policies that passed
    """
    raw = scan_data.get("rawAuditLogRecord", {})
    failed = raw.get("failedPolicies", [])
    passed = raw.get("passedPolicies", [])

    policy_result = "PASSED" if not failed else "FAILED"

    all_policies = [
        {"name": p.get("name", ""), "result": "FAILED"}
        for p in failed
    ] + [
        {"name": p.get("name", ""), "result": "PASSED"}
        for p in passed
    ]

    return {
        "scan_id": scan_data.get("id", ""),
        "scan_status": scan_data.get("status", "UNKNOWN"),
        "started_at": raw.get("startedAt", scan_data.get("timestamp", "")),
        "completed_at": raw.get("createdAt", ""),
        "policy_result": policy_result,
        "policies": all_policies,
    }


def extract_finding_summary(scan_data: dict[str, Any]) -> dict[str, Any]:
    """Extract counts by severity, CWE, and file from WIZ scan results.

    Real WIZ schema (from CI/CD scan export):
      .extraDetails.sastDetails.findings[]                     — SAST findings
        .severity, .filePath, .weaknesses[].id                — per-finding fields
      .extraDetails.vulnerabilityDetails.libraries[]           — SCA libraries
      .extraDetails.secretDetails.findings[]                   — secret findings
    """
    extra = scan_data.get("extraDetails", {})

    sast_details = extra.get("sastDetails", {})
    code_findings = sast_details.get("findings", [])

    vuln_details = extra.get("vulnerabilityDetails", {})
    library_findings = vuln_details.get("libraries", [])

    secret_details = extra.get("secretDetails", {})
    secret_findings = secret_details.get("findings", [])

    iac_details = extra.get("iacDetails", {})
    iac_findings = iac_details.get("findings", []) if isinstance(iac_details, dict) else []

    by_severity: dict[str, int] = {}
    by_cwe: dict[str, int] = {}
    by_file: dict[str, int] = {}

    for finding in code_findings:
        # Severity
        sev = finding.get("severity", "UNKNOWN")
        by_severity[sev] = by_severity.get(sev, 0) + 1

        # CWE — real WIZ uses weaknesses[].id (e.g., "CWE-89")
        weaknesses = finding.get("weaknesses", [])
        for w in weaknesses:
            cwe_id = w.get("id", "") if isinstance(w, dict) else str(w)
            if cwe_id:
                by_cwe[cwe_id] = by_cwe.get(cwe_id, 0) + 1

        # File
        fp = finding.get("filePath", "UNKNOWN")
        by_file[fp] = by_file.get(fp, 0) + 1

    return {
        "total_findings": len(code_findings) + len(library_findings),
        "code_findings": len(code_findings),
        "library_findings": len(library_findings),
        "secret_findings": len(secret_findings),
        "iac_findings": len(iac_findings),
        "by_severity": by_severity,
        "by_cwe": by_cwe,
        "by_file": by_file,
    }


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    # Load scan data from file or inline
    scan_data: dict[str, Any]
    if "scan_data" in input_data:
        scan_data = input_data["scan_data"]
    elif "scan_output_path" in input_data:
        scan_path = Path(input_data["scan_output_path"])
        if not scan_path.exists():
            error_exit(f"Scan output file not found: {scan_path}", "file_check")
        try:
            with open(scan_path) as f:
                scan_data = json.load(f)
        except json.JSONDecodeError as e:
            error_exit(f"Invalid JSON in scan output: {e}", "json_parse")
    else:
        error_exit(
            "Either scan_output_path or scan_data is required", "input_validation"
        )

    log("Extracting WIZ scan metadata")

    metadata = extract_metadata(scan_data)
    summary = extract_finding_summary(scan_data)

    write_json_output({
        "status": "success",
        "metadata": metadata,
        "summary": summary,
    }, start_time=start_time)


if __name__ == "__main__":
    main()
