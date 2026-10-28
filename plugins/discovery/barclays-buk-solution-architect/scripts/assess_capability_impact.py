#!/usr/bin/env python3
"""
Deterministic preflight and postflight validation for capability impact assessment.

This script orchestrates the deterministic boundaries around agentic capability analysis:

1. PREFLIGHT: Validate requirements understanding output, load capability model
   - Validates requirements-analysis.json schema and provenance
   - Loads all capability model YAML files from knowledge/domains/
   - Validates model schema, identifiers, hierarchy
   - Extracts authoritative capability catalogue
   - Output is ready for agentic assessment

2. POSTFLIGHT: Validate findings, verify references, persist to workspace
   - Validates findings schema
   - Verifies all requirement IDs exist in requirements-analysis.json
   - Verifies all capability IDs exist in capability model
   - Verifies capability names and hierarchy match model
   - Persists validated findings to workspace

Usage (Preflight):
    python assess_capability_impact.py \\
      --mode preflight \\
      --requirements-path <invocation>/<issue_key>/analysis/requirements-analysis.json \\
      --capability-model-dir plugins/discovery/barclays-buk-solution-architect/knowledge/domains \\
      --invocation-dir <invocation>

Usage (Postflight):
    python assess_capability_impact.py \\
      --mode postflight \\
      --requirements-path <invocation>/<issue_key>/analysis/requirements-analysis.json \\
      --capability-model-dir plugins/discovery/barclays-buk-solution-architect/knowledge/domains \\
      --findings-path /path/to/candidate-capability-impact.json \\
      --invocation-dir <invocation>
"""

import sys
import os
import json
import argparse
import hashlib
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

try:
    import jsonschema
except ImportError:
    jsonschema = None

# Ensure UTF-8 output on Windows
try:
    if sys.stdout and hasattr(sys.stdout, 'buffer') and sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
    if sys.stderr and hasattr(sys.stderr, 'buffer') and sys.stderr.encoding != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)
except (AttributeError, OSError):
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from capability_model import CapabilityModel, CapabilityModelError


def _load_schema(schema_name: str) -> Dict[str, Any]:
    """Load a JSON schema file."""
    schema_path = Path(__file__).parent / "schemas" / schema_name
    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _validate_requirements_analysis(requirements_path: Path) -> Tuple[Dict[str, Any], str, Optional[str]]:
    """
    Validate requirements-analysis.json structure and return it.

    Supports both:
    - schema_version v1.0: source_jira_evidence with raw_jira_response_sha256
    - schema_version v2.0: source_evidence array with sha256 fields

    Returns (data, requirements_sha256, issue_key):
    - requirements_sha256: SHA-256 hash from first source
    - issue_key: Jira issue key if this is a Jira source, None for PRD/Brief
    """
    if not requirements_path.exists():
        raise RuntimeError(f"Requirements file not found: {requirements_path}")

    try:
        with open(requirements_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in {requirements_path}: {e}")

    schema_version = data.get("schema_version")
    requirements_sha256 = ""
    issue_key = None

    if schema_version == "1.0":
        # Old format: source_jira_evidence with raw_jira_response_sha256
        source = data.get("source_jira_evidence")
        if not source:
            raise RuntimeError("Missing source_jira_evidence in v1.0 requirements-analysis.json")
        requirements_sha256 = source.get("raw_jira_response_sha256", "")
        issue_key = source.get("issue_key")
    elif schema_version == "2.0":
        # New format: source_evidence array with sha256 field
        source_evidence = data.get("source_evidence")
        if not source_evidence or not isinstance(source_evidence, list) or len(source_evidence) == 0:
            raise RuntimeError("Missing source_evidence array in v2.0 requirements-analysis.json")
        # Use first source's hash and issue_key (for multi-source, primary is first)
        requirements_sha256 = source_evidence[0].get("sha256", "")
        # issue_key only exists for Jira sources; PRD/Brief sources won't have it
        issue_key = source_evidence[0].get("source_identifier") if source_evidence[0].get("source_type") == "jira" else None
    else:
        raise RuntimeError(f"Unsupported schema version: {schema_version}. Expected 1.0 or 2.0")
    if not requirements_sha256:
        raise RuntimeError("Missing requirements_sha256 in source evidence")

    # Validate required sections exist
    required_sections = ["explicit_requirements", "inferred_requirements", "constraints_and_dependencies", "ambiguities_and_unknowns", "key_concepts"]
    for section in required_sections:
        if section not in data:
            raise RuntimeError(f"Missing required section: {section}")
        if not isinstance(data[section], list):
            raise RuntimeError(f"Section {section} must be a list")

    return data, requirements_sha256, issue_key


def _extract_requirement_ids(requirements_data: Dict[str, Any]) -> set:
    """Extract all requirement IDs from requirements-analysis.json."""
    req_ids = set()

    for req in requirements_data.get("explicit_requirements", []):
        req_id = req.get("id", "")
        if req_id:
            req_ids.add(req_id)

    for req in requirements_data.get("inferred_requirements", []):
        req_id = req.get("id", "")
        if req_id:
            req_ids.add(req_id)

    for constraint in requirements_data.get("constraints_and_dependencies", []):
        constraint_id = constraint.get("id", "")
        if constraint_id:
            req_ids.add(constraint_id)

    return req_ids


def preflight_validate(
    requirements_path: Path,
    capability_model_dir: Path,
    invocation_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Validate requirements-analysis.json and capability model before LLM invocation.

    Supports both Jira (with issue_key) and PRD/Brief (without issue_key) sources.

    Returns dict with:
        issue_key: str or None (None for PRD/Brief sources without Jira mapping)
        requirements_path: absolute path to validated requirements-analysis.json
        requirements_sha256: str
        capability_model_fingerprint: str
        requirement_ids: set of valid requirement IDs
        capability_catalogue: dict of {capability_id -> {name, hierarchy, ...}}
        candidate_findings_path: authoritative path for Stage 2 candidate and Stage 3 postflight
        output_schema_path: path to capability_impact.schema.json for agentic reference

    Raises: RuntimeError on validation failure
    """
    # Load and validate requirements
    requirements_data, requirements_sha256, issue_key = _validate_requirements_analysis(requirements_path)

    # Load and validate capability model
    if not capability_model_dir.is_dir():
        raise RuntimeError(f"Capability model directory not found: {capability_model_dir}")

    try:
        model = CapabilityModel()
        model.load_from_directory(capability_model_dir)
    except CapabilityModelError as e:
        raise RuntimeError(f"Capability model validation failed: {e}")

    requirement_ids = _extract_requirement_ids(requirements_data)
    capability_catalogue = model.get_capability_catalogue()

    # Determine candidate findings path
    # For Jira (with issue_key): <invocation_dir>/<issue_key>/capability-impact/candidate-capability-impact.json
    # For PRD/Brief (no issue_key): <invocation_dir>/capability-impact/candidate-capability-impact.json
    if invocation_dir:
        if issue_key:
            # Jira source with issue_key
            candidate_findings_path = invocation_dir / issue_key / "capability-impact" / "candidate-capability-impact.json"
        else:
            # PRD/Brief source: invocation_dir is the work-item root
            candidate_findings_path = invocation_dir / "capability-impact" / "candidate-capability-impact.json"
    else:
        # Fallback: derive from requirements_path
        if issue_key:
            candidate_findings_path = requirements_path.parent.parent / issue_key / "capability-impact" / "candidate-capability-impact.json"
        else:
            candidate_findings_path = requirements_path.parent.parent / "capability-impact" / "candidate-capability-impact.json"

    # Determine schema path for agent reference
    schema_path = Path(__file__).parent / "schemas" / "capability_impact.schema.json"

    return {
        "issue_key": issue_key,
        "requirements_path": str(requirements_path.resolve()),
        "requirements_sha256": requirements_sha256,
        "capability_model_fingerprint": model.get_fingerprint(),
        "requirement_ids": requirement_ids,
        "capability_catalogue": capability_catalogue,
        "candidate_findings_path": str(candidate_findings_path),
        "output_schema_path": str(schema_path.resolve())
    }


def _validate_evidence_id_format(evidence_id: str) -> bool:
    """
    Validate evidence ID format. Supports both Jira and PRD/Brief formats.

    Jira: field:index (e.g., description:0, labels:1 — index must be digit)
    PRD/Brief: section:id (e.g., functional_requirements:FR-5, scope:0)
    """
    import re
    parts = evidence_id.split(":")
    if len(parts) != 2:
        return False

    field, index = parts
    if not field or not index:
        return False

    # Known PRD/Brief section names
    prd_sections = {
        'functional_requirements', 'scope', 'success_criteria', 'vision',
        'problem', 'solution', 'assumptions', 'dependencies', 'constraints',
        'integration', 'non_goals', 'non_goal', 'non-goals', 'features'
    }

    # If field is a known PRD section, allow alphanumeric index with dashes (FR-5, scope:0)
    if field in prd_sections:
        return bool(re.match(r'^[A-Za-z0-9]+(\-[A-Za-z0-9]+)*$', index))

    # If field looks like a Jira field (lowercase + underscores), require digit index
    if re.match(r'^[a-z_]+$', field):
        return bool(re.match(r'^\d+$', index))

    # Otherwise allow PRD format
    return bool(re.match(r'^[A-Za-z0-9]+(\-[A-Za-z0-9]+)*$', index))


def _validate_evidence_field(field: str) -> bool:
    """
    Validate that evidence field is recognized.
    Supports both Jira fields and PRD/Brief section names.
    """
    jira_fields = {"summary", "description", "status", "labels", "components", "linked_issues", "acceptance_criteria"}
    prd_sections = {
        'functional_requirements', 'scope', 'success_criteria', 'vision',
        'problem', 'solution', 'assumptions', 'dependencies', 'constraints',
        'integration', 'non_goals', 'non_goal', 'non-goals', 'features'
    }
    return field in jira_fields or field in prd_sections


def postflight_validate(
    requirements_path: Path,
    capability_model_dir: Path,
    findings_path: Path,
    invocation_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Validate findings structure, references, and provenance, then persist.

    Returns dict with:
        schema_version: str
        assessment_status: str
        findings_count: int
        domains_affected: set of domain IDs
        persisted_path: path where findings were written

    Raises: RuntimeError on validation failure
    """
    # Load preflight context
    preflight_result = preflight_validate(requirements_path, capability_model_dir, invocation_dir)

    requirement_ids = preflight_result["requirement_ids"]
    capability_catalogue = preflight_result["capability_catalogue"]
    requirements_sha256 = preflight_result["requirements_sha256"]
    capability_model_fingerprint = preflight_result["capability_model_fingerprint"]
    issue_key = preflight_result["issue_key"]

    # Load findings
    if not findings_path.exists():
        raise RuntimeError(f"Findings file not found: {findings_path}")

    try:
        with open(findings_path, 'r', encoding='utf-8') as f:
            findings_data = json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in findings file: {e}")

    # Validate against schema
    findings_schema = _load_schema("capability_impact.schema.json")
    if jsonschema:
        try:
            jsonschema.validate(instance=findings_data, schema=findings_schema)
        except jsonschema.ValidationError as e:
            raise RuntimeError(f"Findings schema validation failed: {e.message}")

    findings = findings_data.get("findings", [])
    domains_affected = set()

    # Validate each finding
    for i, finding in enumerate(findings):
        finding_id = finding.get("id", f"[finding {i}]")

        # Validate requirement references
        req_ids = finding.get("impacted_by_requirement_ids", [])
        for req_id in req_ids:
            if req_id not in requirement_ids:
                raise RuntimeError(
                    f"Finding {finding_id}: unknown requirement ID '{req_id}'. "
                    f"Valid IDs: {sorted(requirement_ids)}"
                )

        # Validate capability reference
        cap_id = finding.get("capability_id", "")
        if cap_id not in capability_catalogue:
            raise RuntimeError(
                f"Finding {finding_id}: unknown capability ID '{cap_id}'. "
                f"Valid IDs: {sorted(capability_catalogue.keys())}"
            )

        cap_info = capability_catalogue[cap_id]

        # Validate capability name matches model
        reported_name = finding.get("capability_name", "")
        model_name = cap_info.get("name", "")
        if reported_name != model_name:
            raise RuntimeError(
                f"Finding {finding_id}: capability name mismatch. "
                f"Reported '{reported_name}' but model says '{model_name}'"
            )

        # Validate hierarchy
        reported_domain = finding.get("capability_domain", "")
        model_domain = cap_info.get("domain_id", "")
        if reported_domain != model_domain:
            raise RuntimeError(
                f"Finding {finding_id}: domain mismatch. "
                f"Reported '{reported_domain}' but model says '{model_domain}'"
            )

        reported_subdomain = finding.get("capability_subdomain", "")
        model_subdomain = cap_info.get("subdomain_id", "")
        if reported_subdomain != model_subdomain:
            raise RuntimeError(
                f"Finding {finding_id}: sub-domain mismatch. "
                f"Reported '{reported_subdomain}' but model says '{model_subdomain}'"
            )

        domains_affected.add(model_domain)

        # Validate evidence citations
        supporting_evidence = finding.get("supporting_evidence", [])
        for evidence_item in supporting_evidence:
            evidence_id = evidence_item.get("evidence_id", "")
            if not _validate_evidence_id_format(evidence_id):
                raise RuntimeError(
                    f"Finding {finding_id}: malformed evidence ID '{evidence_id}'. "
                    f"Expected format 'field:index'"
                )

            evidence_field = evidence_item.get("evidence_field", "")
            if not _validate_evidence_field(evidence_field):
                raise RuntimeError(
                    f"Finding {finding_id}: unknown evidence field '{evidence_field}'"
                )

        # Validate evidence classification
        classification = finding.get("impact_classification", "")
        valid_classifications = {"direct", "inferred", "possible"}
        if classification not in valid_classifications:
            raise RuntimeError(
                f"Finding {finding_id}: invalid classification '{classification}'. "
                f"Must be one of: {valid_classifications}"
            )

    # Update provenance and persist
    findings_data["input_provenance"]["requirements_sha256"] = requirements_sha256
    findings_data["input_provenance"]["capability_model_fingerprint"] = capability_model_fingerprint
    findings_data["input_provenance"]["assessment_generated_at"] = datetime.now(timezone.utc).isoformat()

    # Determine output path
    # For Jira (with issue_key): <invocation_dir>/<issue_key>/capability-impact/
    # For PRD/Brief (no issue_key): <invocation_dir>/capability-impact/
    if invocation_dir:
        if issue_key:
            output_dir = invocation_dir / issue_key / "capability-impact"
        else:
            output_dir = invocation_dir / "capability-impact"
    else:
        output_dir = findings_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "capability-impact-analysis.json"

    # Write validated findings
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(findings_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise RuntimeError(f"Failed to write findings to {output_path}: {e}")

    return {
        "schema_version": "1.0",
        "assessment_status": "completed",
        "findings_count": len(findings),
        "domains_affected": sorted(domains_affected),
        "persisted_path": str(output_path)
    }


def main():
    parser = argparse.ArgumentParser(
        description="Capability Impact Assessment: Deterministic preflight and postflight validation"
    )
    parser.add_argument(
        "--mode",
        choices=["preflight", "postflight"],
        required=True,
        help="Validation mode"
    )
    parser.add_argument(
        "--requirements-path",
        type=Path,
        required=True,
        help="Path to requirements-analysis.json"
    )
    parser.add_argument(
        "--capability-model-dir",
        type=Path,
        required=True,
        help="Path to knowledge/domains/ directory"
    )
    parser.add_argument(
        "--findings-path",
        type=Path,
        help="Path to candidate capability-impact findings (required for postflight)"
    )
    parser.add_argument(
        "--invocation-dir",
        type=Path,
        help="User invocation directory (optional, used for output path construction)"
    )

    args = parser.parse_args()

    try:
        if args.mode == "preflight":
            result = preflight_validate(args.requirements_path, args.capability_model_dir, args.invocation_dir)
            result["requirement_ids"] = sorted(result["requirement_ids"])
            result.pop("capability_catalogue", None)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        else:  # postflight
            if not args.findings_path:
                raise RuntimeError("--findings-path is required for postflight mode")
            result = postflight_validate(
                args.requirements_path,
                args.capability_model_dir,
                args.findings_path,
                args.invocation_dir
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
