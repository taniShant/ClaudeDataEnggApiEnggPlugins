#!/usr/bin/env python3
"""Parse Wiz SAST JSON report into normalized Vulnerability array.

Input (JSON stdin):
    {"report_path": "/path/to/wiz-report.json", "repo_root": "/path/to/repo"}

Output (JSON stdout):
    {"status": "success", "vulnerabilities": [...], "summary": {...}}
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any

# Allow running as standalone script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output, progress, progress_done
from scripts.core.errors import error_exit


# Severity mapping (Wiz -> canonical)
SEVERITY_MAP = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "informational": "info",
    "info": "info",
}

# File extension -> remediation_type
INFRA_PATH_PATTERNS = re.compile(
    r"(\.tf|\.tfvars|Dockerfile|docker-compose|"
    r"k8s|kubernetes|helm|deploy|infra|terraform|"
    r"\.github/workflows|cloudformation)",
    re.IGNORECASE,
)

DEPENDENCY_FILES = {
    "requirements.txt", "package.json", "gemfile", "pom.xml",
    "go.mod", "cargo.toml", "poetry.lock", "package-lock.json",
    "yarn.lock", "pipfile.lock", "go.sum", "cargo.lock",
    "gemfile.lock", "composer.json", "composer.lock",
}

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rb",
    ".cs", ".c", ".cpp", ".rs", ".php", ".kt", ".swift", ".scala",
}


def extract_findings_array(data: Any) -> list[dict] | None:
    """Probe JSON structure for the findings array."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("result", "results"):
            if key in data and isinstance(data[key], list):
                return data[key]
        if "data" in data and isinstance(data["data"], dict):
            for key in ("results", "result"):
                if key in data["data"] and isinstance(data["data"][key], list):
                    return data["data"][key]
        for key in ("findings", "issues", "vulnerabilities"):
            if key in data and isinstance(data[key], list):
                return data[key]
        # Wiz CloudEvent envelope: {"specversion": ..., "vulnerabilityFindings": {"findings": [...]}}
        vf = data.get("vulnerabilityFindings")
        if isinstance(vf, dict) and isinstance(vf.get("findings"), list):
            return vf["findings"]
    return None


def normalize_cwe(raw: Any) -> str | None:
    """Normalize a CWE value to CWE-### format."""
    if raw is None:
        return None
    if isinstance(raw, int):
        return f"CWE-{raw}" if raw > 0 else None
    if isinstance(raw, str):
        raw = raw.strip()
        # Match CWE-### pattern (possibly with name suffix like "CWE-89: SQL Injection")
        m = re.match(r"(?i)cwe-?(\d+)", raw)
        if m:
            return f"CWE-{int(m.group(1))}"
        # Bare number
        if raw.isdigit() and int(raw) > 0:
            return f"CWE-{int(raw)}"
    return None


def extract_cwe(finding: dict) -> str | None:
    """Extract CWE ID from a Wiz finding using priority-ordered lookups."""
    for field_name in ("cwe", "cweId", "cwe_id"):
        val = finding.get(field_name)
        if val is not None:
            result = normalize_cwe(val)
            if result:
                return result

    # Check nested rule.cwe
    rule = finding.get("rule", {})
    if isinstance(rule, dict):
        val = rule.get("cwe")
        if val is not None:
            result = normalize_cwe(val)
            if result:
                return result

    # Check tags/labels for CWE pattern
    for field_name in ("tags", "labels"):
        tags = finding.get(field_name)
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, str):
                    result = normalize_cwe(tag)
                    if result:
                        return result

    # Check ruleId for embedded CWE
    rule_id = finding.get("ruleId", "") or ""
    result = normalize_cwe(rule_id)
    if result:
        return result

    return None


def extract_field(finding: dict, *field_paths: str) -> Any:
    """Extract a value from a finding checking multiple field paths."""
    for path in field_paths:
        parts = path.split(".")
        obj = finding
        for part in parts:
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                obj = None
                break
        if obj is not None:
            return obj
    return None


def normalize_severity(raw: Any) -> str:
    """Map Wiz severity to canonical value."""
    if raw is None:
        return "medium"
    val = str(raw).strip().lower()
    return SEVERITY_MAP.get(val, "medium")


def classify_remediation_type(file_path: str | None, rule_id: str | None, tags: list | None, affected_package: str | None = None) -> str:
    """Classify finding remediation type by file extension, metadata, and SCA package indicators."""
    # Check tags/rule/package for dependency indicators
    check_text = " ".join([
        rule_id or "",
        " ".join(tags) if tags else "",
        affected_package or "",
    ]).lower()
    if any(kw in check_text for kw in ("dependency", "cve-", "outdated", "vulnerable-package")):
        return "dependency"

    # SCA findings often have no file_path but do have affected_package coordinate (group:artifact:version)
    # If we see a Maven/Gradle coordinate pattern, classify as dependency
    if affected_package and ":" in affected_package:
        return "dependency"

    if file_path is None:
        return "manual"

    # Check dependency file names
    fname = Path(file_path).name.lower()
    if fname in DEPENDENCY_FILES:
        return "dependency"

    # Check infra paths
    if INFRA_PATH_PATTERNS.search(file_path):
        return "infra_config"

    # Check code extensions
    ext = Path(file_path).suffix.lower()
    if ext in CODE_EXTENSIONS:
        return "code_fix"

    # Check for YAML/YML in infra-related paths
    if ext in (".yaml", ".yml"):
        if INFRA_PATH_PATTERNS.search(file_path):
            return "infra_config"
        return "code_fix"

    return "code_fix"


def parse_finding(finding: dict, index: int, repo_root: str | None) -> dict:
    """Parse a single Wiz finding into the Vulnerability model."""
    # ID
    wiz_id = extract_field(finding, "id", "finding_id", "ruleId")
    vuln_id = f"wiz-{wiz_id}" if wiz_id else f"wiz-{index}"

    # CWE
    cwe_id = extract_cwe(finding)

    # Title
    title = extract_field(finding, "title", "name", "rule.name", "rule.title", "summary")
    if not title:
        rule_id = extract_field(finding, "ruleId", "rule.id", "ruleID", "checkId")
        title = f"Wiz finding: {rule_id}" if rule_id else f"Wiz finding #{index}"

    # Description
    description = extract_field(finding, "description", "details", "rule.description", "message") or ""
    remediation_text = extract_field(finding, "remediation", "recommendation")
    if remediation_text:
        description = f"{description}\n{remediation_text}" if description else remediation_text

    # Severity
    raw_severity = extract_field(finding, "severity", "risk", "priority", "rule.severity")
    severity = normalize_severity(raw_severity)

    # File path
    file_path = extract_field(
        finding, "filePath", "file", "location.path",
        "resource.filePath", "sourceLocation.file"
    )
    if file_path and repo_root:
        try:
            fp = Path(file_path)
            rr = Path(repo_root)
            if fp.is_absolute() and str(fp).startswith(str(rr)):
                file_path = str(fp.relative_to(rr))
        except (ValueError, TypeError):
            pass

    # Line number
    line_raw = extract_field(
        finding, "lineNumber", "line", "location.startLine",
        "sourceLocation.line", "location.line"
    )
    line_number = None
    if line_raw is not None:
        try:
            line_number = int(line_raw)
            if line_number <= 0:
                line_number = None
        except (ValueError, TypeError):
            line_number = None

    # Code snippet
    code_snippet = extract_field(finding, "codeSnippet", "snippet", "code", "sourceLocation.snippet")

    # Rule ID
    rule_id = extract_field(finding, "ruleId", "rule.id", "ruleID", "checkId")

    # Tags
    tags = finding.get("tags") or finding.get("labels") or []
    if not isinstance(tags, list):
        tags = []

    # SCA fields (CWE-937 dependency findings) — extract early for classification
    fixed_version = extract_field(
        finding,
        "fixedVersion", "fixed_version", "version.fixed",
        "patchedVersion", "remediation.fixedVersion",
        "vulnerablePackage.fixedVersion",
    )
    if fixed_version is not None:
        fixed_version = str(fixed_version).strip()
        if not fixed_version:
            fixed_version = None

    affected_package = extract_field(
        finding,
        "vulnerablePackage.name", "packageName", "affectedPackage",
        "package.name", "component.name", "library.name",
        "details.vulnerable_package.value",
    )
    if affected_package is not None:
        affected_package = str(affected_package).strip()
        if not affected_package:
            affected_package = None

    current_version = extract_field(
        finding,
        "vulnerablePackage.version", "packageVersion",
        "version.current", "installedVersion",
        "component.version", "library.version",
    )
    if current_version is not None:
        current_version = str(current_version).strip()
        if not current_version:
            current_version = None

    # Remediation type (uses affected_package to detect SCA findings)
    remediation_type = classify_remediation_type(file_path, rule_id, tags, affected_package)

    # Confidence
    confidence = extract_field(finding, "confidence", "certainty")
    if confidence is not None:
        if isinstance(confidence, str):
            conf_map = {"high": 0.9, "medium": 0.7, "low": 0.5}
            confidence = conf_map.get(confidence.lower(), 0.8)
        elif isinstance(confidence, (int, float)):
            if confidence > 1.0:
                confidence = confidence / 100.0
            confidence = max(0.0, min(1.0, float(confidence)))
        else:
            confidence = 0.8
    else:
        confidence = 0.8

    return {
        "id": vuln_id,
        "cwe_id": cwe_id,
        "title": title,
        "description": description,
        "severity": severity,
        "source": "sast",
        "file_path": file_path,
        "line_number": line_number,
        "code_snippet": code_snippet,
        "remediation_type": remediation_type,
        "tool_name": "wiz",
        "rule_id": rule_id,
        "confidence": confidence,
        "affected_package": affected_package,
        "current_version": current_version,
        "fixed_version": fixed_version,
    }


def ensure_unique_ids(vulnerabilities: list[dict]) -> list[dict]:
    """Ensure all vulnerability IDs are unique."""
    seen: dict[str, int] = {}
    for vuln in vulnerabilities:
        vid = vuln["id"]
        if vid in seen:
            seen[vid] += 1
            vuln["id"] = f"{vid}-{seen[vid]}"
        else:
            seen[vid] = 1
    return vulnerabilities


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    report_path = input_data.get("report_path")
    repo_root = input_data.get("repo_root")
    progress(f"Parsing Wiz report — {report_path}")

    if not report_path:
        error_exit("report_path is required", "input_validation")

    report_file = Path(report_path)
    if not report_file.exists():
        error_exit(f"Report file not found: {report_path}", "file_read")
    if not report_file.suffix == ".json":
        error_exit(f"Report file must be .json, got: {report_file.suffix}", "file_read")

    try:
        with open(report_file, "r") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as e:
        error_exit(f"Report file is not valid JSON: {e}", "json_parse")

    findings_array = extract_findings_array(raw_data)
    if findings_array is None:
        # Return empty with warning
        write_json_output({
            "status": "success",
            "vulnerabilities": [],
            "summary": {
                "total_findings": 0,
                "warnings": ["Report structure not recognized. Top-level keys: "
                             + ", ".join(raw_data.keys() if isinstance(raw_data, dict) else ["<array>"])],
            },
        }, start_time=start_time)
        return

    vulnerabilities = []
    skipped = 0
    for i, finding in enumerate(findings_array, start=1):
        if not isinstance(finding, dict):
            skipped += 1
            continue
        # Skip findings with no identifiable content
        has_content = any(
            finding.get(f) for f in ("title", "name", "description", "ruleId", "rule")
        )
        if not has_content:
            skipped += 1
            continue
        vuln = parse_finding(finding, i, repo_root)
        vulnerabilities.append(vuln)

    vulnerabilities = ensure_unique_ids(vulnerabilities)
    progress_done(f"Parsed {len(vulnerabilities)} findings ({skipped} skipped)")

    # Summary counts
    severity_counts = {}
    type_counts = {}
    for v in vulnerabilities:
        severity_counts[v["severity"]] = severity_counts.get(v["severity"], 0) + 1
        type_counts[v["remediation_type"]] = type_counts.get(v["remediation_type"], 0) + 1

    write_json_output({
        "status": "success",
        "vulnerabilities": vulnerabilities,
        "summary": {
            "total_findings": len(vulnerabilities),
            "skipped": skipped,
            "by_severity": severity_counts,
            "by_remediation_type": type_counts,
        },
    }, start_time=start_time)


if __name__ == "__main__":
    main()
