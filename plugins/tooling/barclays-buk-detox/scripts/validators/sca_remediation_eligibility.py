#!/usr/bin/env python3
"""Pre-remediation validation: Check if SCA findings can be auto-remediated.

Validates each dependency finding against:
1. JDK compatibility of safe_version
2. Nexus availability of safe_version

Input (JSON stdin):
    {
        "vulnerabilities": [...],
        "safe_versions": {...},
        "jdk_version": 17,
        "repo_dir": "/path/to/repo",
        "nexus_url": "https://nexus.barcapint.com"
    }

Output (JSON stdout):
    {
        "status": "success",
        "eligible_for_remediation": [...],
        "manual_action_required": [...],
        "validation_summary": {...}
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

from scripts.utils.common import read_json_input, write_json_output, progress, progress_done
from scripts.core.errors import error_exit
from scripts.validators.jdk_compatibility import JDKCompatibilityValidator
from scripts.nexus.nexus_client import NexusClient


def parse_maven_coordinate(coordinate: str) -> tuple[str, str, str] | None:
    """Parse Maven coordinate 'group:artifact:version' into (group, artifact, version)."""
    parts = coordinate.split(":")
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]
    return None


def extract_cpe_to_maven(cpe: str) -> str | None:
    """
    Convert CPE (cpe:2.3:a:vendor:product:version) to Maven coordinate.

    Examples:
        cpe:2.3:a:bouncycastle:bc-java:1.60 → org.bouncycastle:bcprov-jdk15on:1.60
        cpe:2.3:a:apache:log4j:2.17.2 → org.apache.logging.log4j:log4j-core:2.17.2

    Note: This is a best-effort conversion. For real-world use, maintain a mapping.
    """
    parts = cpe.split(":")
    if len(parts) < 5:
        return None

    vendor = parts[3]
    product = parts[4]
    version = parts[5] if len(parts) > 5 else None

    if not version:
        return None

    # Known mappings (in production, use a database or config)
    KNOWN_MAPPINGS = {
        ("bouncycastle", "bc-java"): ("org.bouncycastle", "bcprov-jdk15on"),
        ("apache", "log4j"): ("org.apache.logging.log4j", "log4j-core"),
    }

    key = (vendor.lower(), product.lower().replace("-", ""))
    if key in KNOWN_MAPPINGS:
        group, artifact = KNOWN_MAPPINGS[key]
        return f"{group}:{artifact}:{version}"

    return None


def validate_finding_for_remediation(
    finding: dict,
    safe_version: str,
    jdk_version: int,
    jdk_validator: JDKCompatibilityValidator,
    nexus_client: NexusClient,
) -> dict:
    """
    Validate if a single finding can be auto-remediated.

    Returns dict with:
    {
        "finding_id": "wiz-xxx",
        "affected_package": "cpe:2.3:...",
        "safe_version": "group:artifact:version",
        "eligible": true/false,
        "reason": "why eligible or not",
        "jdk_compatible": true/false/unknown,
        "nexus_available": true/false/unknown,
        "remediation_action": "auto_apply" | "manual" | "blocked"
    }
    """
    finding_id = finding.get("id", "unknown")
    affected_package = finding.get("affected_package")

    result = {
        "finding_id": finding_id,
        "affected_package": affected_package,
        "safe_version": safe_version,
        "eligible": False,
        "reason": "Unknown",
        "jdk_compatible": None,
        "nexus_available": None,
        "remediation_action": "manual",
    }

    # Step 1: Check JDK compatibility
    try:
        # Extract Maven coordinate from safe_version
        coord = parse_maven_coordinate(safe_version)
        if coord:
            group, artifact, version = coord

            # Check compatibility
            compat_result = jdk_validator.check_compatibility(
                affected_package=f"{group}:{artifact}",
                version=version,
                jdk_version=jdk_version,
            )

            result["jdk_compatible"] = compat_result.get("compatible", False)

            if not result["jdk_compatible"]:
                result["reason"] = (
                    f"JDK incompatible: requires JDK {compat_result.get('min_jdk_required', '?')}, "
                    f"project has JDK {jdk_version}"
                )
                result["remediation_action"] = "manual"
                return result
        else:
            result["reason"] = f"Could not parse safe_version coordinate: {safe_version}"
            result["remediation_action"] = "manual"
            return result
    except Exception as e:
        result["reason"] = f"JDK compatibility check failed: {str(e)}"
        result["remediation_action"] = "manual"
        return result

    # Step 2: Check Nexus availability
    try:
        coord = parse_maven_coordinate(safe_version)
        if coord:
            group, artifact, version = coord

            # Check if version exists in Nexus
            exists = nexus_client.check_artifact_exists(group, artifact, version)
            result["nexus_available"] = exists

            if not exists:
                result["reason"] = (
                    f"Safe version not available in Nexus: {safe_version}. "
                    f"Manual review required to find alternative or confirm availability."
                )
                result["remediation_action"] = "manual"
                return result
        else:
            result["reason"] = f"Could not parse safe_version for Nexus check: {safe_version}"
            result["remediation_action"] = "manual"
            return result
    except Exception as e:
        result["reason"] = f"Nexus availability check failed: {str(e)}. Treating as unavailable."
        result["nexus_available"] = False
        result["remediation_action"] = "manual"
        return result

    # Step 3: All validations passed → eligible for auto-remediation
    result["eligible"] = True
    result["reason"] = (
        f"Safe version {safe_version} is JDK {jdk_version}-compatible and available in Nexus"
    )
    result["remediation_action"] = "auto_apply"

    return result


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    vulnerabilities = input_data.get("vulnerabilities", [])
    safe_versions = input_data.get("safe_versions", {})
    jdk_version = input_data.get("jdk_version")
    repo_dir = input_data.get("repo_dir")
    nexus_url = input_data.get("nexus_url", "https://nexus.barcapint.com")

    if not vulnerabilities:
        error_exit("vulnerabilities array is required", "input_validation")
    if not safe_versions:
        error_exit("safe_versions object is required", "input_validation")
    if jdk_version is None:
        error_exit("jdk_version is required", "input_validation")
    if not repo_dir:
        error_exit("repo_dir is required", "input_validation")

    progress(f"Validating {len(vulnerabilities)} findings for auto-remediation eligibility...")

    # Initialize validators
    jdk_validator = JDKCompatibilityValidator(repo_dir)
    nexus_client = NexusClient(nexus_url)

    eligible_for_remediation = []
    manual_action_required = []

    for finding in vulnerabilities:
        affected_pkg = finding.get("affected_package")

        if not affected_pkg:
            manual_action_required.append({
                "finding_id": finding.get("id"),
                "affected_package": affected_pkg,
                "reason": "No affected_package field",
                "remediation_action": "manual",
            })
            continue

        # Extract group:artifact from affected_package (CPE or Maven coordinate)
        # For CPE: cpe:2.3:a:bouncycastle:bc-java:1.60
        # Try to find matching safe_version entry

        safe_version_key = None
        safe_version_value = None

        # Check if affected_package matches a safe_versions key
        for key, config in safe_versions.items():
            if key in affected_pkg or affected_pkg in key:
                safe_version_key = key
                safe_version_value = config.get("safe_version")
                break

        if not safe_version_value:
            manual_action_required.append({
                "finding_id": finding.get("id"),
                "affected_package": affected_pkg,
                "reason": f"No safe_version configured for {affected_pkg}",
                "remediation_action": "manual",
            })
            continue

        # Validate the safe_version
        validation = validate_finding_for_remediation(
            finding=finding,
            safe_version=safe_version_value,
            jdk_version=jdk_version,
            jdk_validator=jdk_validator,
            nexus_client=nexus_client,
        )

        if validation["eligible"]:
            eligible_for_remediation.append(validation)
        else:
            manual_action_required.append(validation)

    progress_done(
        f"{len(eligible_for_remediation)} eligible for auto-remediation, "
        f"{len(manual_action_required)} require manual action"
    )

    write_json_output({
        "status": "success",
        "eligible_for_remediation": eligible_for_remediation,
        "manual_action_required": manual_action_required,
        "validation_summary": {
            "total_findings": len(vulnerabilities),
            "eligible": len(eligible_for_remediation),
            "manual": len(manual_action_required),
            "jdk_version": jdk_version,
            "nexus_url": nexus_url,
        },
    }, start_time=start_time)


if __name__ == "__main__":
    main()
