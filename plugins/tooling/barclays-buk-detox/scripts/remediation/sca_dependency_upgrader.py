#!/usr/bin/env python3
"""SCA dependency upgrader with Nexus availability and JDK compatibility checks."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    from packaging import version as pkg_version
except ImportError:
    raise ImportError(
        "The 'packaging' library is required for version comparison. "
        "Install it with: pip install packaging"
    )

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output, progress, progress_done
from scripts.core.errors import error_exit
from scripts.nexus.nexus_client import NexusClient
from scripts.validators.jdk_compatibility import JDKCompatibilityValidator


def find_next_suitable_version(
    nexus_client: NexusClient,
    group: str,
    artifact: str,
    current_version: str,
    wiz_version: str,
    jdk_version: int,
    validator: JDKCompatibilityValidator,
    affected_package: str,
) -> tuple[str | None, str | None]:
    """
    Find the next suitable version that remediates CVEs and is available in Nexus.

    Returns (next_version, reason) or (None, error_msg) if no suitable version found.
    """
    progress(f"Searching for alternative versions to {wiz_version}...")

    try:
        available_versions = nexus_client.list_available_versions(group, artifact)
        if not available_versions:
            return None, f"No versions found for {affected_package} in Nexus"

        # Filter versions that are:
        # 1. Newer than current version (remediate CVEs)
        # 2. Not the Wiz version (already checked)
        # 3. Stable (not alpha, beta, rc for alpha like 3.0.0-alpha1)
        # 4. Prefer patch/minor updates over major downgrades
        current_ver = pkg_version.parse(current_version)
        wiz_ver = pkg_version.parse(wiz_version)

        candidates = []
        for v_str in available_versions:
            try:
                v = pkg_version.parse(v_str)

                # Skip older versions
                if v <= current_ver:
                    continue

                # Skip the Wiz version (we know it has issues)
                if v == wiz_ver:
                    continue

                # Skip pre-release versions (alpha, beta, rc)
                if v.is_prerelease:
                    continue

                # Check JDK compatibility
                compatibility = validator.check_compatibility(affected_package, v_str, jdk_version)
                if not compatibility["compatible"]:
                    continue

                candidates.append((v_str, v))

            except Exception:
                # Skip unparseable versions
                continue

        if not candidates:
            return None, f"No suitable stable versions found that remediate CVEs and are JDK {jdk_version}-compatible"

        # Sort by version, prefer latest
        candidates.sort(key=lambda x: x[1], reverse=True)
        next_version = candidates[0][0]

        reason = f"Wiz-recommended {wiz_version} unavailable/incompatible. Selected {next_version} (stable, available in Nexus, JDK {jdk_version}-compatible)"
        return next_version, reason

    except Exception as e:
        return None, f"Error searching for alternative versions: {str(e)}"


def _run_script(rel_path: str, input_data: dict, timeout: int = 120) -> dict:
    """Run a Python script and return parsed JSON output."""
    script = Path(__file__).resolve().parent.parent / rel_path
    if not script.exists():
        error_exit(f"Script not found: {script}", "remediation")

    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if not result.stdout.strip():
        stderr_hint = result.stderr[:500] if result.stderr else "(no stderr)"
        error_exit(
            f"Script {rel_path} produced no output. stderr: {stderr_hint}",
            "remediation",
        )

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        error_exit(f"Script {rel_path} returned invalid JSON: {result.stdout[:300]}", "remediation")


def main() -> None:
    """Orchestrate SCA dependency upgrade with all checks."""
    start_time = time.time()
    inp = read_json_input()

    repo_root = inp.get("repo_root")
    affected_package = inp.get("affected_package")  # group:artifact
    current_version = inp.get("current_version")
    safe_version = inp.get("safe_version")
    nexus_url = inp.get("nexus_url", "https://nexus.barclays.local")
    nexus_user = inp.get("nexus_user", "")
    nexus_pass = inp.get("nexus_pass", "")

    if not all([repo_root, affected_package, current_version, safe_version]):
        error_exit(
            "repo_root, affected_package, current_version, and safe_version are required",
            "input_validation",
        )

    progress("Stage 1/3: Checking Nexus availability...")

    # Parse group:artifact
    if ":" not in affected_package:
        error_exit(f"Invalid package format: {affected_package}. Expected group:artifact", "input_validation")

    group, artifact = affected_package.split(":", 1)

    # Check Nexus
    nexus_client = NexusClient(nexus_url, nexus_user, nexus_pass)
    nexus_exists = nexus_client.check_artifact_exists(group, artifact, safe_version)

    # Start JDK validation early to use in version search
    progress("Detecting JDK version...")
    validator = JDKCompatibilityValidator(repo_root)
    jdk_info = validator.detect_jdk_version()
    jdk_version = jdk_info["detected_version"]

    selected_version = safe_version
    version_selection_reason = None

    if not nexus_exists:
        progress_done(f"Wiz version {safe_version} not found in Nexus. Searching for alternatives...")

        # Try to find a suitable alternative version
        alt_version, alt_reason = find_next_suitable_version(
            nexus_client, group, artifact, current_version, safe_version, jdk_version, validator, affected_package
        )

        if alt_version:
            progress_done(f"Found alternative: {alt_version}")
            selected_version = alt_version
            version_selection_reason = alt_reason
        else:
            # No alternative found
            write_json_output({
                "status": "needs_review",
                "reason": "nexus_unavailable_no_alternative",
                "affected_package": affected_package,
                "current_version": current_version,
                "safe_version": safe_version,
                "nexus_available": False,
                "jdk_compatible": None,
                "message": f"Safe version {safe_version} is not available in Nexus, and no suitable alternative found.",
                "corrective_action": alt_reason or f"Verify that {affected_package}:{safe_version} is deployed to internal Nexus. Check with DevOps/Security team.",
            }, start_time=start_time)
            return
    else:
        progress_done(f"Found {safe_version} in Nexus")

    # Stage 2: Check JDK compatibility
    progress("Stage 2/3: Checking JDK compatibility...")

    compatibility = validator.check_compatibility(affected_package, selected_version, jdk_version)

    if not compatibility["compatible"]:
        progress_done(f"ERROR: Not compatible with JDK {jdk_version}")

        # Try to find an alternative that IS JDK compatible
        if selected_version != safe_version:
            # Already tried alternatives in Nexus phase, this is the best we found but it's incompatible
            corrective_action = f"Selected version {selected_version} is incompatible with JDK {jdk_version}. Options: 1) Upgrade JDK to {compatibility['min_jdk_required']}+, 2) Wait for SDK3 BOM update with older-compatible jackson version."
        else:
            corrective_action = f"Option 1: Upgrade repository JDK to {compatibility['min_jdk_required']}+. Option 2: Find alternative safe version compatible with JDK {jdk_version}."

        write_json_output({
            "status": "needs_review",
            "reason": "jdk_incompatible",
            "affected_package": affected_package,
            "current_version": current_version,
            "safe_version": safe_version,
            "selected_version": selected_version,
            "version_selection_reason": version_selection_reason,
            "nexus_available": True,
            "jdk_compatible": False,
            "jdk_info": jdk_info,
            "compatibility": compatibility,
            "message": f"Selected version {selected_version} requires JDK {compatibility['min_jdk_required']} but repository uses JDK {jdk_version}",
            "corrective_action": corrective_action,
        }, start_time=start_time)
        return

    progress_done(f"Compatible with JDK {jdk_version}")

    # Stage 3: Apply fix
    progress("Stage 3/3: All checks passed — proceeding with upgrade...")

    write_json_output({
        "status": "approved",
        "affected_package": affected_package,
        "current_version": current_version,
        "safe_version": safe_version,
        "selected_version": selected_version,
        "version_selection_reason": version_selection_reason,
        "nexus_available": True,
        "jdk_compatible": True,
        "jdk_info": jdk_info,
        "compatibility": compatibility,
        "message": f"Version {selected_version} is available in Nexus and compatible with JDK {jdk_version}. Ready for build file remediation.",
        "next_step": "Trigger build file remediation agent (detox-build-remediation-agent)",
    }, start_time=start_time)


if __name__ == "__main__":
    main()
