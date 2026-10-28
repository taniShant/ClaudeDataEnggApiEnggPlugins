#!/usr/bin/env python3
"""Classify and partition vulnerability findings by remediation type and severity.

Input (JSON stdin):
    {"vulnerabilities": [...], "severity_filter": "critical+high"}

Output (JSON stdout):
    {"status": "success", "code_fix": [...], "hybrid": [...], "infra_config": [...],
     "dependency": [...], "manual": [...], "filtered_out": [...], "counts": {...}}
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output, progress, progress_done
from scripts.core.errors import error_exit


VALID_SEVERITY_FILTERS = {"critical", "high", "medium", "critical+high", "all"}

SEVERITY_SETS = {
    "critical": {"critical"},
    "high": {"high"},
    "medium": {"medium"},
    "critical+high": {"critical", "high"},
    "all": {"critical", "high", "medium", "low", "info"},
}


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    vulnerabilities = input_data.get("vulnerabilities")
    if vulnerabilities is None:
        error_exit("vulnerabilities array is required", "input_validation")
    if not isinstance(vulnerabilities, list):
        error_exit("vulnerabilities must be a list", "input_validation")

    severity_filter = input_data.get("severity_filter", "all").lower().strip()
    if severity_filter not in VALID_SEVERITY_FILTERS:
        error_exit(
            f"Invalid severity_filter: {severity_filter}. Must be one of: {', '.join(VALID_SEVERITY_FILTERS)}",
            "input_validation",
        )

    allowed_severities = SEVERITY_SETS[severity_filter]
    progress(f"Classifying {len(vulnerabilities)} findings (filter: {severity_filter})...")

    # Partition
    code_fix = []
    hybrid = []
    infra_config = []
    dependency = []
    manual = []
    filtered_out = []

    for vuln in vulnerabilities:
        sev = (vuln.get("severity") or "medium").lower()
        if sev not in allowed_severities:
            filtered_out.append(vuln)
            continue

        rtype = (vuln.get("remediation_type") or "code_fix").lower()
        if rtype == "code_fix":
            code_fix.append(vuln)
        elif rtype == "hybrid":
            hybrid.append(vuln)
        elif rtype == "infra_config":
            infra_config.append(vuln)
        elif rtype == "dependency":
            dependency.append(vuln)
        elif rtype == "manual":
            manual.append(vuln)
        else:
            # Default unknown types to code_fix
            code_fix.append(vuln)

    total_actionable = len(code_fix) + len(hybrid)
    progress_done(f"{total_actionable} actionable (code_fix={len(code_fix)}, hybrid={len(hybrid)}, infra={len(infra_config)}, dep={len(dependency)}, manual={len(manual)})")

    write_json_output({
        "status": "success",
        "code_fix": code_fix,
        "hybrid": hybrid,
        "infra_config": infra_config,
        "dependency": dependency,
        "manual": manual,
        "filtered_out": filtered_out,
        "counts": {
            "code_fix": len(code_fix),
            "hybrid": len(hybrid),
            "infra_config": len(infra_config),
            "dependency": len(dependency),
            "manual": len(manual),
            "filtered_out": len(filtered_out),
            "total_actionable": total_actionable,
        },
    }, start_time=start_time)


if __name__ == "__main__":
    main()
