#!/usr/bin/env python3
"""Export telemetry data as a website-consumable JSON file.

Generates a comprehensive usage report JSON that the detoxWebsite
can fetch at runtime from the GitLab raw file URL.

Input (JSON stdin):
  {"output_path": "/path/to/output.json", "period": "all"}

Output (JSON stdout):
  {"status": "success", "output_path": "...", "generated_at": "..."}

The exported JSON is designed to be consumed by the detoxWebsite dashboard
via a GitLab raw file fetch:
  https://app.gitlab.barcapint.com/<group>/<project>/-/raw/main/telemetry/usage-report.json
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output, log
from scripts.core.errors import error_exit
from scripts.telemetry.usage_report import parse_period, load_runs, compute_aggregates
from scripts.telemetry.version import PLUGIN_VERSION

# Default output location (committed to the Detox plugin repo)
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent.parent / "telemetry" / "usage-report.json"


def export_for_website(input_data: dict[str, Any]) -> dict[str, Any]:
    """Generate the website-consumable telemetry export."""
    period_str = input_data.get("period", "all")
    output_path = Path(input_data.get("output_path", str(DEFAULT_OUTPUT)))

    start, end = parse_period(period_str)
    runs = load_runs(after=start)
    report = compute_aggregates(runs, period_str, start, end)

    # Add website-specific metadata
    export_data = {
        "_meta": {
            "schema_version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "generated_by": "detox-telemetry-export",
            "plugin_version": PLUGIN_VERSION,
            "period": period_str,
            "source": "~/.detox/telemetry/runs.jsonl",
            "description": "Detox plugin usage telemetry for the detoxWebsite dashboard. "
                           "Fetched at runtime from GitLab raw file URL.",
        },
        "summary": {
            "total_runs": report["usage"]["total_runs"],
            "total_repos_onboarded": report["onboarding"]["total_repos_onboarded"],
            "newly_onboarded_this_period": report["onboarding"]["newly_onboarded_this_period"],
            "unique_users": report["usage"]["unique_users"],
            "cwes_remediated": report["effectiveness"]["cwes_remediated"],
            "remediation_rate": report["effectiveness"]["remediation_rate"],
            "fix_success_rate": report["effectiveness"]["fix_success_rate"],
            "deferral_rate": report["effectiveness"]["deferral_rate"],
            "validation_pass_rate": report["effectiveness"]["validation_pass_rate"],
            "test_pass_rate": report["effectiveness"]["test_pass_rate"],
        },
        "repos": report["repos"],
        "onboarding": report["onboarding"],
        "effectiveness": report["effectiveness"],
        "security_posture": report["security_posture"],
        "performance": report["performance"],
        "usage": report["usage"],
        "errors": report["errors"],
        "period": report["period"],
    }

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        output_path.write_text(
            json.dumps(export_data, indent=2, default=str),
            encoding="utf-8",
        )
    except OSError as e:
        error_exit(f"Failed to write export file: {e}", "file_write")

    return {
        "status": "success",
        "output_path": str(output_path),
        "generated_at": export_data["_meta"]["generated_at"],
        "total_runs": export_data["summary"]["total_runs"],
        "total_repos": export_data["summary"]["total_repos_onboarded"],
    }


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()
    result = export_for_website(input_data)
    write_json_output(result, start_time=start_time)


if __name__ == "__main__":
    main()
