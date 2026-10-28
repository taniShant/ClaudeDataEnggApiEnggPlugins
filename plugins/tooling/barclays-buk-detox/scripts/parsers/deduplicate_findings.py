#!/usr/bin/env python3
"""Deduplicate vulnerability findings by composite key.

Input (JSON stdin):
    {"vulnerabilities": [...], "merge_strategy": "highest_severity"}

Output (JSON stdout):
    {"status": "success", "vulnerabilities": [...], "summary": {...}}
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output, SEVERITY_ORDER, progress, progress_done
from scripts.core.errors import error_exit


def make_key(vuln: dict) -> tuple | None:
    """Create composite dedup key: (file_path, line_number, cwe_id).

    Returns None if any component is missing (finding cannot be deduped).
    """
    file_path = vuln.get("file_path")
    line_number = vuln.get("line_number")
    cwe_id = vuln.get("cwe_id")

    if file_path is None or line_number is None or cwe_id is None:
        return None
    return (file_path, line_number, cwe_id)


def merge_vulnerabilities(existing: dict, incoming: dict, strategy: str) -> dict:
    """Merge two vulnerability dicts using the specified strategy."""
    merged = existing.copy()

    if strategy == "highest_severity":
        existing_sev = SEVERITY_ORDER.get(existing.get("severity", "medium"), 2)
        incoming_sev = SEVERITY_ORDER.get(incoming.get("severity", "medium"), 2)
        if incoming_sev > existing_sev:
            merged["severity"] = incoming["severity"]

    # Always take the longer description
    if len(incoming.get("description", "")) > len(merged.get("description", "")):
        merged["description"] = incoming["description"]

    # Always take code_snippet if existing is empty
    if not merged.get("code_snippet") and incoming.get("code_snippet"):
        merged["code_snippet"] = incoming["code_snippet"]

    # Take higher confidence
    if (incoming.get("confidence") or 0) > (merged.get("confidence") or 0):
        merged["confidence"] = incoming["confidence"]

    return merged


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    vulnerabilities = input_data.get("vulnerabilities")
    if vulnerabilities is None:
        error_exit("vulnerabilities array is required", "input_validation")
    if not isinstance(vulnerabilities, list):
        error_exit("vulnerabilities must be a list", "input_validation")

    strategy = input_data.get("merge_strategy", "highest_severity")
    if strategy not in ("highest_severity", "most_complete", "first_seen"):
        strategy = "highest_severity"

    progress(f"Deduplicating {len(vulnerabilities)} findings (strategy: {strategy})...")

    # Dedup using composite key, preserving first-seen order
    seen: dict[tuple, int] = {}  # key -> index in output list
    output: list[dict] = []
    duplicates_removed = 0
    merge_groups: list[dict[str, Any]] = []

    for vuln in vulnerabilities:
        key = make_key(vuln)
        if key is None:
            # Cannot dedup — always include
            output.append(vuln)
            continue

        if key in seen:
            # Merge into existing
            idx = seen[key]
            output[idx] = merge_vulnerabilities(output[idx], vuln, strategy)
            duplicates_removed += 1
            # Track merge
            merge_groups.append({
                "kept_id": output[idx]["id"],
                "merged_id": vuln["id"],
                "key": {"file_path": key[0], "line_number": key[1], "cwe_id": key[2]},
            })
        else:
            seen[key] = len(output)
            output.append(vuln)

    progress_done(f"{len(output)} unique findings ({duplicates_removed} duplicates removed)")

    write_json_output({
        "status": "success",
        "vulnerabilities": output,
        "summary": {
            "input_count": len(vulnerabilities),
            "output_count": len(output),
            "duplicates_removed": duplicates_removed,
            "merge_groups": merge_groups,
        },
    }, start_time=start_time)


if __name__ == "__main__":
    main()
