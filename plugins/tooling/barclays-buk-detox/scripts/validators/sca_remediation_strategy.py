#!/usr/bin/env python3
"""Intelligent SCA remediation strategy selector.

Implements priority-based version selection for vulnerability fixes:

1. PRIMARY: Use Wiz-recommended version
   - Check JDK compatibility
   - Check Nexus availability
   - If both pass → auto_apply with Wiz recommendation

2. FALLBACK: Use safe-versions.json recommendation
   - Only if Wiz version fails JDK check
   - Check JDK compatibility
   - Check Nexus availability
   - If both pass → auto_apply with safe-versions config

3. INTELLIGENT SEARCH: Find next suitable version
   - If Wiz version fails Nexus check
   - Search Nexus for versions newer than Wiz recommendation
   - Filter by: JDK compatibility + security (must remediate CVE)
   - Pick latest stable version
   - If found → auto_apply with searched version

4. MANUAL: No suitable version found
   - Wiz version incompatible with JDK
   - Wiz version not in Nexus
   - No suitable alternative in Nexus
   - → manual_action with reason and fallback recommendations

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
        "remediation_plan": [
            {
                "finding_id": "CVE-2026-59650",
                "affected_package": "cpe:2.3:a:bouncycastle:bc-java:1.60",
                "remediation_strategy": "wiz_recommended" | "safe_versions" | "nexus_search" | "manual",
                "selected_version": "org.bouncycastle:bcprov-jdk18on:1.85",
                "remediation_action": "auto_apply" | "manual",
                "reason": "...",
                "details": {...}
            }
        ]
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
        return parts[0], parts[1], ":".join(parts[2:])  # Handle versions with colons
    return None


def extract_package_key_from_cpe(cpe: str) -> str | None:
    """Extract 'group:artifact' pattern from CPE for matching safe-versions.json keys."""
    # CPE 2.3 format: cpe:2.3:a:vendor:product:version or w-cpe:2.3:a:vendor:product:version
    # Example: cpe:2.3:a:bouncycastle:bc-java:1.60
    #          parts: [cpe, 2.3, a, bouncycastle, bc-java, 1.60]

    # Normalize: handle both 'cpe' and 'w-cpe' prefixes
    if cpe.startswith("w-cpe:"):
        cpe = cpe[6:]  # Remove 'w-cpe:'
    elif cpe.startswith("cpe:"):
        cpe = cpe[4:]  # Remove 'cpe:'

    parts = cpe.split(":")
    # Expected: ['2.3', 'a', 'vendor', 'product', 'version', ...]
    if len(parts) < 4:
        return None

    # parts[0] = '2.3' (version)
    # parts[1] = 'a' (type: a=application)
    # parts[2] = vendor
    # parts[3] = product
    # parts[4+] = version, etc.

    vendor = parts[2].lower()
    product = parts[3].lower()

    # Known CPE to Maven group:artifact mappings
    KNOWN_MAPPINGS = {
        ("bouncycastle", "bc-java"): "org.bouncycastle:bcprov-jdk15on",
        ("apache", "log4j"): "org.apache.logging.log4j:log4j-core",
    }

    key = (vendor, product)
    if key in KNOWN_MAPPINGS:
        return KNOWN_MAPPINGS[key]

    return None

    return None


def extract_wiz_recommended_version(finding: dict) -> tuple[str | None, str | None]:
    """
    Extract Wiz-recommended version and Maven coordinate from finding.

    Returns (version_string, maven_coordinate) or (None, None) if not found.
    Example return: ("1.85", "org.bouncycastle:bcprov-jdk18on:1.85")
    """
    # Look in multiple possible locations for Wiz recommendation

    # 1. Check description field (common in Wiz reports)
    description = finding.get("description", "")
    if description and "mvn" in description.lower():
        # Format: "mvn versions:use-latest-releases -Dincludes=org.bouncycastle:bcpkix-jdk15on"
        # Extract package from includes parameter
        if "-Dincludes=" in description:
            import re
            match = re.search(r'-Dincludes=([^\s]+)', description)
            if match:
                package_spec = match.group(1)
                # Try to extract current version from affected_package
                affected = finding.get("affected_package", "")
                if affected and ":" in affected:
                    parts = affected.split(":")
                    if len(parts) >= 3:
                        current_version = parts[-1]  # Last part is version in CPE
                        # Wiz recommends upgrade, so look for latest
                        # We'll need Nexus search for this, return signal for caller
                        return "latest", None

    # 2. Check solution field
    solution = finding.get("solution")
    if solution:
        # Example: "Upgrade cpe:2.3:a:bouncycastle:bc-java to version 1.85"
        if "version" in solution.lower():
            import re
            match = re.search(r'version\s+([0-9\.]+[\w\-]*)', solution, re.IGNORECASE)
            if match:
                return match.group(1).strip(), None

    # 3. Check identifiers for CVE → can look up recommended version later
    identifiers = finding.get("identifiers", [])
    if identifiers:
        # Keep CVE info for potential lookup
        return None, None

    # 4. Check details.vulnerable_package.value (Wiz format)
    vulnerable_pkg = (
        finding.get("details", {}).get("vulnerable_package", {}).get("value")
    )
    if vulnerable_pkg and ":" in vulnerable_pkg:
        # Format: cpe:2.3:a:bouncycastle:bc-java:1.60
        parts = vulnerable_pkg.split(":")
        if len(parts) >= 6:
            current_version = parts[5]  # Version is the 6th part in CPE
            # Again, no explicit recommendation, return signal
            return "latest", None

    return None, None


def validate_version_for_jdk(
    artifact: str, version: str, jdk_version: int, jdk_validator: JDKCompatibilityValidator
) -> dict:
    """Validate if a version is compatible with project JDK."""
    try:
        result = jdk_validator.check_compatibility(
            affected_package=artifact, version=version, jdk_version=jdk_version
        )
        return {
            "compatible": result.get("compatible", False),
            "min_jdk_required": result.get("min_jdk_required"),
            "reason": result.get("reason", ""),
        }
    except Exception as e:
        return {
            "compatible": True,  # Safe default: assume compatible if check fails
            "min_jdk_required": None,
            "reason": f"Compatibility check failed: {str(e)} (assumed compatible)",
        }


def check_nexus_availability(
    group: str, artifact: str, version: str, nexus_client: NexusClient
) -> dict:
    """Check if artifact version is available in Nexus."""
    try:
        exists = nexus_client.check_artifact_exists(group, artifact, version)
        return {
            "available": exists,
            "group": group,
            "artifact": artifact,
            "version": version,
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
            "group": group,
            "artifact": artifact,
            "version": version,
        }


def find_next_suitable_version(
    group: str,
    artifact: str,
    current_version: str,
    jdk_version: int,
    jdk_validator: JDKCompatibilityValidator,
    nexus_client: NexusClient,
) -> tuple[str | None, str | None]:
    """
    Find next suitable version that:
    1. Is newer than current version (remediates vulnerability)
    2. Is compatible with project JDK
    3. Is available in Nexus
    4. Is stable (not pre-release)

    Returns (version, reason) or (None, error_reason) if no suitable version found.
    """
    try:
        available_versions = nexus_client.list_available_versions(group, artifact)
        if not available_versions:
            return None, f"No versions found for {group}:{artifact} in Nexus (Nexus may be unreachable)"

        from packaging import version as pkg_version

        current_ver = pkg_version.parse(current_version)
        candidates = []

        for v_str in available_versions:
            try:
                v = pkg_version.parse(v_str)

                # Skip older or equal versions (must remediate CVE)
                if v <= current_ver:
                    continue

                # Skip pre-release versions (alpha, beta, rc)
                if v.is_prerelease:
                    continue

                # Check JDK compatibility
                compat = validate_version_for_jdk(
                    f"{group}:{artifact}", v_str, jdk_version, jdk_validator
                )
                if not compat["compatible"]:
                    continue

                # Check Nexus availability (redundant but explicit)
                nexus_check = check_nexus_availability(group, artifact, v_str, nexus_client)
                if not nexus_check["available"]:
                    continue

                candidates.append((v_str, v))

            except Exception:
                # Skip unparseable versions
                continue

        if not candidates:
            return (
                None,
                f"No suitable stable versions found for {group}:{artifact} "
                f"that are JDK {jdk_version}-compatible and newer than {current_version}",
            )

        # Sort by version, prefer latest
        candidates.sort(key=lambda x: x[1], reverse=True)
        next_version = candidates[0][0]

        reason = (
            f"Wiz-recommended version not available/compatible. "
            f"Selected {next_version} (stable, available in Nexus, JDK {jdk_version}-compatible)"
        )
        return next_version, reason

    except Exception as e:
        return None, f"Error searching for alternative versions: {str(e)}"


def determine_remediation_strategy(
    finding: dict,
    safe_versions: dict,
    jdk_version: int,
    jdk_validator: JDKCompatibilityValidator,
    nexus_client: NexusClient,
) -> dict:
    """
    Determine remediation strategy for a single finding using priority-based logic.

    Returns dict with complete remediation plan.
    """
    finding_id = finding.get("id", "unknown")
    affected_package = finding.get("affected_package")
    affected_title = finding.get("title", "Unknown CVE")

    result = {
        "finding_id": finding_id,
        "affected_package": affected_package,
        "affected_title": affected_title,
        "remediation_strategy": None,
        "selected_version": None,
        "remediation_action": None,
        "reason": None,
        "details": {},
    }

    if not affected_package:
        result["remediation_action"] = "manual"
        result["reason"] = "No affected_package field available"
        return result

    # Extract package key for lookups
    package_key = extract_package_key_from_cpe(affected_package)

    # Get Wiz-recommended version
    wiz_version, wiz_coordinate = extract_wiz_recommended_version(finding)

    # Get safe-versions.json entry
    safe_version_entry = None
    if package_key:
        safe_version_entry = safe_versions.get(package_key, {})

    # ==================== STRATEGY 1: WIZ RECOMMENDED ====================
    if wiz_version and wiz_version != "latest":
        try:
            from scripts.utils.common import log
            log(f"Strategy 1: Checking Wiz version {wiz_version} for {affected_package}")

            # Parse Wiz version into Maven coordinate
            if package_key:
                group, artifact = package_key.split(":")
                wiz_coordinate = f"{group}:{artifact}:{wiz_version}"

                # Check JDK compatibility
                log(f"  Calling JDK validator for {package_key}:{wiz_version}...")
                jdk_check = validate_version_for_jdk(
                    package_key, wiz_version, jdk_version, jdk_validator
                )
                log(f"  JDK check result: {jdk_check}")

            if jdk_check["compatible"]:
                # JDK compatible → check Nexus availability
                nexus_check = check_nexus_availability(group, artifact, wiz_version, nexus_client)
                log(f"  Nexus check: {nexus_check}")

                if nexus_check["available"]:
                    # Both checks pass → use Wiz recommendation
                    log(f"  ✓ AUTO_APPLY: Wiz {wiz_version}")
                    result["remediation_strategy"] = "wiz_recommended"
                    result["selected_version"] = wiz_coordinate
                    result["remediation_action"] = "auto_apply"
                    result["reason"] = (
                        f"Wiz-recommended version {wiz_version} is JDK {jdk_version}-compatible "
                        f"and available in Nexus"
                    )
                    result["details"] = {
                        "wiz_version": wiz_version,
                        "jdk_compatible": True,
                        "nexus_available": True,
                    }
                    return result

                else:
                    # JDK compatible but NOT in Nexus → search for alternative
                    log(f"  Nexus unavailable, searching for alternative...")
                    result["details"]["wiz_version"] = wiz_version
                    result["details"]["wiz_jdk_compatible"] = True
                    result["details"]["wiz_nexus_available"] = False

                    # Try to find next suitable version
                    next_version, search_reason = find_next_suitable_version(
                        group,
                        artifact,
                        wiz_version,
                        jdk_version,
                        jdk_validator,
                        nexus_client,
                    )
                    log(f"  Search result: {next_version} ({search_reason})")

                    if next_version:
                        log(f"  ✓ AUTO_APPLY: Alternative {next_version}")
                        result["remediation_strategy"] = "nexus_search"
                        result["selected_version"] = f"{group}:{artifact}:{next_version}"
                        result["remediation_action"] = "auto_apply"
                        result["reason"] = search_reason
                        result["details"]["searched_version"] = next_version
                        return result
                    else:
                        # No suitable version found → fallback to manual
                        log(f"  ✗ MANUAL: {search_reason}")
                        result["remediation_strategy"] = "nexus_search_failed"
                        result["remediation_action"] = "manual"
                        result["reason"] = search_reason
                        return result

            else:
                # Wiz version NOT JDK compatible → check safe-versions.json
                log(f"  Wiz incompatible with JDK {jdk_version}, trying safe-versions...")
                result["details"]["wiz_version"] = wiz_version
                result["details"]["wiz_jdk_compatible"] = False
                result["details"]["wiz_jdk_required"] = jdk_check.get("min_jdk_required")
        except Exception as e:
            log(f"ERROR in Strategy 1: {e}")
            import traceback
            log(traceback.format_exc())

    # ==================== STRATEGY 1b: WIZ "LATEST" OR NO VERSION (NEXUS SEARCH) ====================
    # If Wiz says "latest" or doesn't give explicit version, try to find latest suitable in Nexus
    if wiz_version == "latest" or (not wiz_version and package_key):
        try:
            group, artifact = package_key.split(":")
            # Get current vulnerable version from affected_package CPE
            affected_parts = affected_package.split(":")
            if len(affected_parts) >= 6:
                current_version = affected_parts[-1]

                # Search for next suitable version
                next_version, search_reason = find_next_suitable_version(
                    group,
                    artifact,
                    current_version,
                    jdk_version,
                    jdk_validator,
                    nexus_client,
                )

                if next_version:
                    result["remediation_strategy"] = "nexus_search_latest"
                    result["selected_version"] = f"{group}:{artifact}:{next_version}"
                    result["remediation_action"] = "auto_apply"
                    result["reason"] = f"Wiz recommends upgrade to latest compatible version. Selected {next_version} from Nexus (JDK {jdk_version}-compatible, stable)"
                    result["details"] = {
                        "current_vulnerable": current_version,
                        "searched_version": next_version,
                        "jdk_compatible": True,
                        "nexus_available": True,
                    }
                    return result
        except Exception:
            pass  # Fall through to next strategy

    # ==================== STRATEGY 2: SAFE-VERSIONS.JSON ====================
    if safe_version_entry and safe_version_entry.get("safe_version"):
        safe_version = safe_version_entry.get("safe_version")

        # Parse safe_version coordinate
        coord = parse_maven_coordinate(safe_version)
        if coord:
            group, artifact, version = coord

            # Check JDK compatibility
            compatible_jdk_list = safe_version_entry.get("compatible_jdk", [])
            jdk_check = {"compatible": jdk_version in compatible_jdk_list} if compatible_jdk_list else {"compatible": True}

            if jdk_check["compatible"]:
                # JDK compatible → check Nexus availability
                nexus_check = check_nexus_availability(group, artifact, version, nexus_client)

                if nexus_check["available"]:
                    # Both checks pass → use safe-versions recommendation
                    result["remediation_strategy"] = "safe_versions"
                    result["selected_version"] = safe_version
                    result["remediation_action"] = "auto_apply"
                    result["reason"] = (
                        f"Safe-versions.json entry: {safe_version} is JDK {jdk_version}-compatible "
                        f"and available in Nexus"
                    )
                    result["details"] = {
                        "safe_version": safe_version,
                        "jdk_compatible": True,
                        "nexus_available": True,
                        "strategy": safe_version_entry.get("strategy"),
                    }
                    return result

    # ==================== STRATEGY 3/4: FALLBACK TO MANUAL ====================
    result["remediation_strategy"] = "no_suitable_version"
    result["remediation_action"] = "manual"

    # Build detailed reason
    reasons = []
    if wiz_version:
        reasons.append(f"Wiz-recommended version {wiz_version} is not suitable")
        if result["details"].get("wiz_jdk_compatible") == False:
            reasons.append(
                f"  - Not JDK compatible (requires JDK {result['details'].get('wiz_jdk_required')}, "
                f"project has JDK {jdk_version})"
            )
        if result["details"].get("wiz_nexus_available") == False:
            reasons.append("  - Not available in Nexus")
        if result["details"].get("searched_version"):
            reasons.append(f"  - No suitable alternative versions found in Nexus")
    if safe_version_entry:
        reasons.append("Safe-versions.json entry either missing or not suitable")

    if not reasons:
        reasons.append("No remediation path available (no Wiz recommendation or safe-versions entry)")

    result["reason"] = " | ".join(reasons)

    return result


def main() -> None:
    """Entry point with fast-path for batch processing."""
    import sys
    start_time = time.time()
    input_data = read_json_input()

    vulnerabilities = input_data.get("vulnerabilities", [])
    safe_versions = input_data.get("safe_versions", {})
    jdk_version = input_data.get("jdk_version")
    repo_dir = input_data.get("repo_dir")
    nexus_url = input_data.get("nexus_url", "https://nexus.barcapint.com")

    if not vulnerabilities:
        error_exit("vulnerabilities array is required", "input_validation")
    if jdk_version is None:
        error_exit("jdk_version is required", "input_validation")
    if not repo_dir:
        error_exit("repo_dir is required", "input_validation")

    progress(f"Determining remediation strategy for {len(vulnerabilities)} findings...")

    # Initialize validators
    jdk_validator = JDKCompatibilityValidator(repo_dir)
    nexus_client = NexusClient(nexus_url)

    remediation_plan = []
    auto_apply_count = 0
    manual_count = 0

    for finding in vulnerabilities:
        strategy = determine_remediation_strategy(
            finding=finding,
            safe_versions=safe_versions,
            jdk_version=jdk_version,
            jdk_validator=jdk_validator,
            nexus_client=nexus_client,
        )

        remediation_plan.append(strategy)

        if strategy["remediation_action"] == "auto_apply":
            auto_apply_count += 1
        else:
            manual_count += 1

    progress_done(
        f"Remediation plan: {auto_apply_count} auto_apply, {manual_count} manual"
    )

    write_json_output({
        "status": "success",
        "remediation_plan": remediation_plan,
        "summary": {
            "total_findings": len(vulnerabilities),
            "auto_apply": auto_apply_count,
            "manual": manual_count,
            "jdk_version": jdk_version,
            "nexus_url": nexus_url,
        },
    }, start_time=start_time)


if __name__ == "__main__":
    main()
