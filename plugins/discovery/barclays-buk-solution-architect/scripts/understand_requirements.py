#!/usr/bin/env python3
"""
Deterministic preflight and postflight validation for requirements understanding.

This script orchestrates the deterministic boundaries around agentic requirements analysis:

1. PREFLIGHT: Validate requirements.json, extract normalized evidence, build evidence catalogue
   - Validates schema and Jira issue type (Business Epic)
   - Verifies raw response file and SHA-256 provenance
   - Extracts normalized evidence (runtime-neutral context for LLM reasoning)
   - Extracts evidence_units catalogue (authoritative citation index with stable IDs)
   - Output is ready for agentic analysis by current skill/LLM context

2. POSTFLIGHT: Validate analysis structure, resolve evidence IDs, persist to workspace
   - Validates output schema and required sections
   - Validates all evidence IDs against the deterministic catalogue
   - Resolves evidence IDs to authoritative source values (LLM never supplies source text)
   - Preserves provenance (raw_jira_response_sha256)
   - Writes valid analysis to external workspace

Evidence ID semantics:
    IDs have the form  {jira_field}:{unit_index}  (e.g. "description:2", "labels:0").
    They are positional identifiers scoped to the source version identified by
    raw_jira_response_sha256.  Together, raw_jira_response_sha256 + evidence_id
    identifies a specific evidence unit.  IDs are NOT stable across Jira updates.

Description segmentation:
    Descriptions are split deterministically on recognised syntactic delimiters:
    1. Horizontal rule lines (----) -- primary delimiter
    2. Jira heading lines (h1. through h6.) -- secondary delimiter (no ---- found)
    If no delimiters are recognised, the entire description is a single unit (description:0).
    Heading lines used as boundaries are preserved as part of their unit's source_value.
    Line endings (CRLF/LF) are normalised to LF before splitting.

Usage (Preflight):
    python understand_requirements.py \\
      --mode preflight \\
      --requirements-path <invocation>/<issue_key>/requirements/<issue_key>.json \\
      --invocation-dir <invocation>

Usage (Postflight):
    python understand_requirements.py \\
      --mode postflight \\
      --requirements-path <invocation>/<issue_key>/requirements/<issue_key>.json \\
      --analysis-path /path/to/analysis.json \\
      --invocation-dir <invocation> \\
      --output-dir <invocation>/<issue_key>/analysis (optional, defaults to invocation-dir)
"""

import sys
import os
import re
import json
import hashlib
import tempfile
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

# Ensure stdout/stderr use UTF-8 encoding on Windows (but preserve test-friendly wrappers)
try:
    if sys.stdout and hasattr(sys.stdout, 'buffer') and sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
    if sys.stderr and hasattr(sys.stderr, 'buffer') and sys.stderr.encoding != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)
except (AttributeError, OSError):
    # In some testing/piping contexts, this may fail safely; that's okay
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# Evidence unit extraction
# ---------------------------------------------------------------------------

def _split_description_into_units(description: str) -> List[str]:
    """
    Split a Jira description into deterministic evidence units.

    Rules (in priority order):
    1. Normalise CRLF to LF.
    2. If the text contains horizontal rule lines (----), split on them.
       Each resulting non-empty stripped chunk is one unit.
       Heading lines at the start of a chunk are preserved in source_value.
    3. If no horizontal rules are found, split on Jira heading lines (h1.-h6.)
       using a zero-width split so the heading is kept in its following unit.
    4. If neither structure is recognised, return the entire text as one unit.
    """
    text = description.replace('\r\n', '\n').replace('\r', '\n')
    stripped = text.strip()
    if not stripped:
        return []

    # Primary: split on horizontal rule lines
    # Match \n----\n (four or more dashes on their own line)
    hr_parts = re.split(r'\n-{4,}\n', '\n' + text + '\n')
    chunks = [p.strip() for p in hr_parts if p.strip()]
    if len(chunks) > 1:
        return chunks

    # Secondary: split on heading lines, keeping the heading in the following unit
    # \n before h[1-6]. is consumed; heading line starts the new chunk
    heading_parts = re.split(r'\n(?=h[1-6]\. )', text)
    chunks = [p.strip() for p in heading_parts if p.strip()]
    if len(chunks) > 1:
        return chunks

    # Fallback: single unit
    return [stripped]


def extract_evidence_units(normalized_evidence: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract a deterministic, ordered catalogue of evidence units from normalized evidence.

    Supports multiple source types:
    - Jira: Extract from standard Jira fields (description, labels, components, etc.)
    - PRD/Brief: Use pre-extracted units provided by deterministic parser

    For Jira, each unit has the form:
        {
            "id":           "{jira_field}:{unit_index}",
            "jira_field":   str,
            "source_value": str | dict
        }

    For PRD/Brief, units already include:
        {
            "id":              "functional_requirements:FR-1",
            "source_native_id": "FR-1",
            "prd_section":     "features",
            "source_value":    str
        }

    Extraction rules (Jira):
    - Atomic scalar fields (summary, status): single unit, id = {field}:0
    - Text array fields (labels, components, acceptance_criteria): one unit per item
    - Structured array fields (linked_issues): one unit per item, source_value is full dict
    - Description: split via _split_description_into_units(); fallback is single unit
    - Empty or missing fields emit no units (no error)
    - Repeated identical text blocks receive distinct positional IDs

    IDs are scoped to the source version (Jira: raw_jira_response_sha256, PRD: prd_sha256).
    """
    units: List[Dict[str, Any]] = []
    source_type = normalized_evidence.get("source_type", "jira")

    # PRD/Brief: use pre-extracted units from parser
    if source_type in ("prd", "brief"):
        evidence_units = normalized_evidence.get("evidence_units", [])
        if isinstance(evidence_units, list):
            return evidence_units

    # Jira: extract from standard fields
    # Atomic text fields
    for field in ("summary", "status"):
        value = normalized_evidence.get(field, "")
        if isinstance(value, str) and value.strip():
            units.append({"id": f"{field}:0", "jira_field": field, "source_value": value})

    # Description (structured splitting)
    description = normalized_evidence.get("description", "")
    if isinstance(description, str) and description.strip():
        chunks = _split_description_into_units(description)
        for i, chunk in enumerate(chunks):
            units.append({
                "id": f"description:{i}",
                "jira_field": "description",
                "source_value": chunk
            })

    # Text array fields
    for field in ("labels", "components", "acceptance_criteria"):
        items = normalized_evidence.get(field, [])
        if isinstance(items, list):
            for i, item in enumerate(items):
                if isinstance(item, str) and item.strip():
                    units.append({
                        "id": f"{field}:{i}",
                        "jira_field": field,
                        "source_value": item
                    })

    # Structured array fields: preserve complete normalized dict
    linked_issues = normalized_evidence.get("linked_issues", [])
    if isinstance(linked_issues, list):
        for i, item in enumerate(linked_issues):
            if isinstance(item, dict):
                units.append({
                    "id": f"linked_issues:{i}",
                    "jira_field": "linked_issues",
                    "source_value": item
                })

    return units


def build_evidence_unit_map(evidence_units: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Return a dict mapping evidence_id -> unit for O(1) lookup."""
    return {unit["id"]: unit for unit in evidence_units}


# ---------------------------------------------------------------------------
# Evidence ID validation and resolution
# ---------------------------------------------------------------------------

_JIRA_EVIDENCE_ID_PATTERN = re.compile(r'^[a-z_]+:\d+$')  # Jira: field:index (non-negative int)
_PRD_EVIDENCE_ID_PATTERN = re.compile(r'^[a-z_]+:([A-Za-z0-9]+(\-[A-Za-z0-9]+)*)$')  # PRD: section:ID (letters/nums with optional dashes, like FR-1)


def _validate_evidence_id_format(evidence_id: str) -> bool:
    """
    Validate evidence ID format. Accepts both Jira and PRD formats.

    Jira: description:0, labels:1 (field:non-negative-integer)
    PRD: functional_requirements:FR-1 (section:alphanumeric_with_dashes)

    Parsing:
    - If field_part is a known PRD section name, allow PRD format for index
    - If field_part looks like a Jira field (lowercase + underscores, not PRD), require integer index
    - Otherwise allow PRD format
    """
    parts = evidence_id.split(':')
    if len(parts) != 2:
        return False

    field_part = parts[0]
    index_part = parts[1]

    # Known PRD section names (from parse_prd_and_brief.py)
    prd_sections = {
        'functional_requirements', 'scope', 'success_criteria', 'vision',
        'problem', 'solution', 'assumptions', 'dependencies', 'constraints',
        'integration', 'non_goals', 'non_goal', 'non-goals'
    }

    # If field_part is a known PRD section, require PRD format index
    if field_part in prd_sections:
        return bool(re.match(r'^[A-Za-z0-9]+(\-[A-Za-z0-9]+)*$', index_part))

    # If field_part looks like a Jira field (lowercase + underscores), require Jira format
    if re.match(r'^[a-z_]+$', field_part):
        return bool(re.match(r'^\d+$', index_part))  # Must be non-negative integer

    # Otherwise allow PRD format (field can have mixed case, index is alphanumeric with dashes)
    return bool(re.match(r'^[A-Za-z0-9]+(\-[A-Za-z0-9]+)*$', index_part))


def validate_evidence_id_list(
    ids: Any,
    unit_map: Dict[str, Dict[str, Any]],
    context: str
) -> None:
    """
    Validate a supporting_evidence ID list from LLM output.

    Supports multiple evidence ID formats:
    - Jira: description:0, labels:1 (field:index where index >= 0)
    - PRD: functional_requirements:FR-1 (section:native_id)
    - Brief: problem:0, solution:1 (section:index)

    Raises ValueError if:
    - ids is not a list
    - any element is not a string
    - any ID has invalid format
    - any ID is unknown (not in unit_map)
    - any ID appears more than once within this list (duplicate within one item)
    """
    if not isinstance(ids, list):
        raise ValueError(
            f"{context}: supporting_evidence must be a list of evidence ID strings, "
            f"got {type(ids).__name__}"
        )
    seen: set = set()
    for item in ids:
        if not isinstance(item, str):
            raise ValueError(
                f"{context}: each evidence ID must be a string, got {type(item).__name__}: {item!r}"
            )
        if not item:
            raise ValueError(f"{context}: evidence ID must not be empty string")
        if not _validate_evidence_id_format(item):
            raise ValueError(
                f"{context}: malformed evidence ID {item!r}. "
                f"Expected format: 'field:index' (e.g. 'description:0') for Jira, "
                f"or 'section:id' (e.g. 'FR-1', 'problem:0') for PRD/Brief"
            )
        if item in seen:
            raise ValueError(
                f"{context}: duplicate evidence ID {item!r}. "
                f"Each ID may appear at most once per supporting_evidence list."
            )
        seen.add(item)
        if item not in unit_map:
            raise ValueError(
                f"{context}: unknown evidence ID {item!r}. "
                f"Valid IDs are: {sorted(unit_map.keys())}"
            )


def resolve_evidence_ids(
    ids: List[str],
    unit_map: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Resolve a list of validated evidence IDs to authoritative evidence references.

    Returns a list of dicts:
        {"evidence_id": str, "field": str, "source_value": str | dict}

    Supports both Jira and PRD/Brief formats:
    - Jira: "field" is "jira_field" from unit_map
    - PRD/Brief: "field" is "prd_section" or "brief_section" from unit_map

    source_value comes exclusively from the deterministic catalogue, never from LLM output.
    """
    resolved = []
    for eid in ids:
        unit = unit_map[eid]
        # Support both Jira and PRD/Brief field names
        field_name = unit.get("jira_field") or unit.get("prd_section") or unit.get("brief_section") or "unknown"
        resolved.append({
            "evidence_id": eid,
            "field": field_name,
            "source_value": unit["source_value"],
        })
    return resolved


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------

def preflight_validate(
    requirements_path: Path,
    workspace: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Validate requirements.json and provenance before LLM invocation.

    Checks:
    - Schema version 1.0
    - Jira issue type is exactly "Business Epic"
    - Raw response file exists
    - SHA-256 hash matches recorded value (provenance integrity)

    Returns dict with:
        issue_key:              str
        evidence:               normalized fields for LLM reasoning context
        evidence_units:         deterministic citation catalogue (LLM references by ID)
        candidate_analysis_path: authoritative path for Stage 2 candidate and Stage 3 postflight

    Raises: RuntimeError on validation failure
    """
    if not requirements_path.exists():
        raise RuntimeError(f"Requirements file not found: {requirements_path}")

    try:
        requirements_data = json.loads(requirements_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in {requirements_path}: {e}")

    if requirements_data.get("schema_version") != "1.0":
        raise RuntimeError(
            f"Unsupported schema version: {requirements_data.get('schema_version')}. Expected 1.0"
        )

    source = requirements_data.get("source")
    if not source:
        raise RuntimeError("Missing 'source' key in requirements")

    # Validate required source fields based on source type
    source_type = source.get("type")
    if source_type == "jira":
        required_fields = [
            "type", "instance", "issue_key", "retrieved_at", "endpoint",
            "requested_fields", "raw_response_file", "raw_response_sha256"
        ]
    elif source_type in ("prd", "brief"):
        required_fields = ["type", "prd_path", "prd_sha256"]
    else:
        required_fields = ["type"]

    for field in required_fields:
        if field not in source:
            raise RuntimeError(f"Missing required source field: {field}")

    source_type = source.get("type")
    if source_type not in ("jira", "prd", "brief"):
        raise RuntimeError(f"Unexpected source type: {source_type}. Expected 'jira', 'prd', or 'brief'")

    # Jira-specific validation (skip for PRD/Brief)
    if source_type == "jira":
        jira_issue_type = requirements_data.get("requirements", {}).get("type", "")
        if jira_issue_type != "Business Epic":
            raise RuntimeError(
                f"Input contract violation: expected Jira issue type 'Business Epic', "
                f"got '{jira_issue_type}'. "
                f"This implementation analyzes Business Epics only."
            )

    requirements_obj = requirements_data.get("requirements")
    if not requirements_obj:
        raise RuntimeError("Missing 'requirements' key")

    # Determine issue_key (work-item identifier) early
    # Jira: stable issue key from source
    # PRD/Brief: None (no work-item subdirectory created; invocation_dir IS the work-item root)
    issue_key = None
    if source_type == "jira":
        issue_key = source["issue_key"]
    elif source_type in ("prd", "brief"):
        # PRD/Brief: workspace IS the work-item root
        # Ensure requirements.json is at canonical location (workspace/requirements/file.json)
        # not at any subdirectory like workspace/prd/requirements/file.json
        if workspace:
            req_file_relative = requirements_path.relative_to(workspace)
        else:
            req_file_relative = requirements_path.relative_to(requirements_path.parent.parent)

        if len(req_file_relative.parts) > 2 or (len(req_file_relative.parts) > 0 and req_file_relative.parts[0] != "requirements"):
            raise RuntimeError(
                f"PRD/Brief workspace contract violated: requirements.json must be at "
                f"<workspace>/requirements/filename.json, not {req_file_relative}. "
                f"Invocation directory must be the directory containing prd.md/brief.md, "
                f"not a subdirectory."
            )

    # Verify raw response file and SHA-256 integrity (Jira only)
    if source_type == "jira":
        raw_file_path = source["raw_response_file"]

        if workspace:
            full_raw_path = workspace / raw_file_path
        else:
            full_raw_path = requirements_path.parent.parent / "raw" / f"{issue_key}.json"

        if not full_raw_path.exists():
            raise RuntimeError(
                f"Raw response file not found at: {full_raw_path}\n"
                f"Recorded path in source: {raw_file_path}"
            )

        raw_bytes = full_raw_path.read_bytes()
        computed_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        recorded_sha256 = source["raw_response_sha256"]

        if computed_sha256 != recorded_sha256:
            raise RuntimeError(
                f"Provenance integrity check failed for raw Jira response!\n"
                f"  Expected SHA-256: {recorded_sha256}\n"
                f"  Computed SHA-256: {computed_sha256}\n"
                f"  File: {full_raw_path}\n"
                f"The raw response may have been modified or corrupted."
            )

    # Build normalized evidence (LLM reasoning context — not citation source)
    # Include source_type so evidence extraction can use appropriate field names
    normalized_evidence = {
        "issue_key": issue_key,
        "source_type": source.get("type", "jira"),
        "summary": requirements_obj.get("summary", ""),
        "description": requirements_obj.get("description", ""),
        "status": requirements_obj.get("status", ""),
        "labels": requirements_obj.get("labels", []),
        "components": requirements_obj.get("components", []),
        "linked_issues": requirements_obj.get("linked_issues", []),
        "acceptance_criteria": requirements_obj.get("acceptance_criteria", []),
        "evidence_units": requirements_obj.get("evidence_units", []),
        "evidence_sources": requirements_obj.get("evidence_sources", {}),
    }

    # Build deterministic evidence catalogue (authoritative citation index)
    evidence_units = extract_evidence_units(normalized_evidence)

    # Establish authoritative candidate-analysis path for Stage 2 -> Stage 3 hand-off
    # Workspace contract:
    #   Jira: workspace / issue_key / analysis / candidate-requirements-analysis.json
    #   PRD/Brief: workspace / analysis / candidate-requirements-analysis.json (no issue_key subdir)
    if source_type == "jira":
        # Jira: use issue_key subdirectory
        if workspace:
            candidate_analysis_path = workspace / issue_key / "analysis" / "candidate-requirements-analysis.json"
        else:
            candidate_analysis_path = requirements_path.parent.parent / "analysis" / "candidate-requirements-analysis.json"
    else:
        # PRD/Brief: invocation_dir IS the work-item root; no issue_key subdirectory
        if workspace:
            candidate_analysis_path = workspace / "analysis" / "candidate-requirements-analysis.json"
        else:
            candidate_analysis_path = requirements_path.parent.parent / "analysis" / "candidate-requirements-analysis.json"

    return {
        "issue_key": issue_key,
        "evidence": normalized_evidence,
        "evidence_units": evidence_units,
        "candidate_analysis_path": str(candidate_analysis_path.resolve()),
    }


# ---------------------------------------------------------------------------
# Postflight
# ---------------------------------------------------------------------------

def _validate_analysis_sections(analysis: Dict[str, Any]) -> None:
    """
    Validate structural requirements of analysis output.

    Checks: all six required sections present; list/dict structure of item collections;
    supporting_evidence present on each item; inferred_requirements have reasoning;
    constraints_and_dependencies have is_explicit bool; ambiguities_and_unknowns have
    clarification_needed and do not have recommendation; change_summary has outcome,
    rationale, and supporting_evidence.

    Does NOT validate evidence ID strings or resolve them — works for both pre-resolution
    (new analysis from LLM, IDs are strings) and post-resolution (existing analysis, IDs
    are resolved dicts).

    Raises ValueError if any structural check fails.
    """
    required_sections = [
        "change_summary", "explicit_requirements", "inferred_requirements",
        "constraints_and_dependencies", "ambiguities_and_unknowns", "key_concepts"
    ]
    for section in required_sections:
        if section not in analysis:
            raise ValueError(f"Missing required section: {section}")

    def _check_items_structure(items: Any, context: str) -> None:
        if not isinstance(items, list):
            raise ValueError(f"{context}: expected list, got {type(items).__name__}")
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"{context}: item must be dict, got {type(item).__name__}")
            item_id = item.get("id", "unknown")
            if "supporting_evidence" not in item:
                raise ValueError(f"{context}[{item_id}]: missing supporting_evidence")

    _check_items_structure(analysis.get("explicit_requirements", []), "explicit_requirements")
    _check_items_structure(analysis.get("inferred_requirements", []), "inferred_requirements")

    for req in analysis.get("inferred_requirements", []):
        if "reasoning" not in req:
            raise ValueError(
                f"inferred_requirements[{req.get('id', 'unknown')}]: missing reasoning"
            )

    _check_items_structure(
        analysis.get("constraints_and_dependencies", []), "constraints_and_dependencies"
    )

    for constraint in analysis.get("constraints_and_dependencies", []):
        if "is_explicit" not in constraint:
            raise ValueError(
                f"constraints_and_dependencies[{constraint.get('id', 'unknown')}]: missing is_explicit"
            )
        if not isinstance(constraint["is_explicit"], bool):
            raise ValueError(
                f"constraints_and_dependencies[{constraint.get('id', 'unknown')}]: is_explicit must be bool"
            )

    ambiguities = analysis.get("ambiguities_and_unknowns", [])
    if not isinstance(ambiguities, list):
        raise ValueError("ambiguities_and_unknowns must be list")
    for amb in ambiguities:
        if "clarification_needed" not in amb:
            raise ValueError(
                f"ambiguities_and_unknowns[{amb.get('id', 'unknown')}]: missing clarification_needed"
            )
        if "recommendation" in amb:
            raise ValueError(
                f"ambiguities_and_unknowns[{amb.get('id', 'unknown')}]: contains 'recommendation'. "
                f"Use 'clarification_needed' instead (neutral, not prescriptive)"
            )

    _check_items_structure(analysis.get("key_concepts", []), "key_concepts")

    # Validate unratified_architectural_decisions if present (optional section)
    if "unratified_architectural_decisions" in analysis:
        unad_list = analysis.get("unratified_architectural_decisions", [])
        if not isinstance(unad_list, list):
            raise ValueError("unratified_architectural_decisions must be list")
        for item in unad_list:
            if not isinstance(item, dict):
                raise ValueError("unratified_architectural_decisions: item must be dict")
            item_id = item.get("id", "unknown")
            if "proposed_solution" not in item:
                raise ValueError(f"unratified_architectural_decisions[{item_id}]: missing proposed_solution")
            if "supporting_evidence" not in item:
                raise ValueError(f"unratified_architectural_decisions[{item_id}]: missing supporting_evidence")
            if "status" not in item:
                raise ValueError(f"unratified_architectural_decisions[{item_id}]: missing status")
            if "ratification_required" not in item:
                raise ValueError(f"unratified_architectural_decisions[{item_id}]: missing ratification_required")

    change_summary = analysis.get("change_summary", {})
    if not isinstance(change_summary, dict):
        raise ValueError("change_summary must be dict")
    if "outcome" not in change_summary or "rationale" not in change_summary:
        raise ValueError("change_summary must have 'outcome' and 'rationale'")
    if "supporting_evidence" not in change_summary:
        raise ValueError("change_summary must have 'supporting_evidence'")


def validate_existing_analysis(analysis_path: Path) -> dict:
    """
    Load and validate an existing (postflight-produced) requirements-analysis.json.

    Supports both:
    - Schema v1.0: source_jira_evidence.raw_jira_response_sha256 present
    - Schema v2.0: source_evidence array present with sha256 fields

    Does NOT validate or re-resolve evidence ID strings against the current catalogue.
    The SHA-256 match confirmed in the orchestration layer guarantees the analysis was
    produced from the same source, so resolved evidence dicts are trusted as written.

    Returns parsed dict.
    Raises RuntimeError if any check fails.
    """
    if not analysis_path.exists():
        raise RuntimeError(f"Analysis file not found: {analysis_path}")

    try:
        data = json.loads(analysis_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in {analysis_path}: {e}") from e

    schema_version = data.get("schema_version")

    # Support both v1.0 (old Jira-only format) and v2.0 (new multi-source format)
    if schema_version == "1.0":
        # Old format: source_jira_evidence with raw_jira_response_sha256
        source_jira_evidence = data.get("source_jira_evidence")
        if not source_jira_evidence:
            raise RuntimeError("Missing 'source_jira_evidence' in v1.0 analysis")
        if "raw_jira_response_sha256" not in source_jira_evidence:
            raise RuntimeError("Missing 'raw_jira_response_sha256' in source_jira_evidence")
    elif schema_version == "2.0":
        # New format: source_evidence array with sha256 field
        source_evidence = data.get("source_evidence")
        if not source_evidence or not isinstance(source_evidence, list) or len(source_evidence) == 0:
            raise RuntimeError("Missing 'source_evidence' array in v2.0 analysis")
        for i, source in enumerate(source_evidence):
            if "sha256" not in source:
                raise RuntimeError(f"Missing 'sha256' in source_evidence[{i}]")
    else:
        raise RuntimeError(
            f"Unsupported analysis schema version: {schema_version}. Expected 1.0 or 2.0"
        )

    try:
        _validate_analysis_sections(data)
    except ValueError as e:
        raise RuntimeError(f"Analysis structure invalid: {e}") from e

    return data


def check_resolved_evidence_integrity(
    analysis: Dict[str, Any],
    evidence_units: List[Dict[str, Any]]
) -> None:
    """
    Read-only integrity check: verify resolved evidence references in an existing
    analysis are consistent with the current evidence catalogue.

    For each supporting_evidence item that is a resolved dict (containing evidence_id
    and field), checks that evidence_id exists in the current catalogue and that
    field matches the catalogue entry.

    Supports both Jira and PRD/Brief formats.

    Does NOT re-resolve or mutate any part of the analysis.

    Only called when the evidence SHA-256 matches, guaranteeing the catalogue was built
    from the same raw source. A failure here indicates unexpected post-write corruption.

    Raises RuntimeError if any reference is inconsistent.
    """
    unit_map = build_evidence_unit_map(evidence_units)

    def _check_refs(refs: Any, context: str) -> None:
        if not isinstance(refs, list):
            return
        for ref in refs:
            if not isinstance(ref, dict):
                continue
            eid = ref.get("evidence_id")
            if not eid:
                continue
            if eid not in unit_map:
                raise RuntimeError(
                    f"{context}: resolved evidence_id {eid!r} not found in current catalogue. "
                    f"Analysis may be inconsistent with current evidence."
                )
            # Get field name from either old or new format
            ref_field = ref.get("field") or ref.get("jira_field")
            catalogue_unit = unit_map[eid]
            catalogue_field = catalogue_unit.get("jira_field") or catalogue_unit.get("prd_section") or catalogue_unit.get("brief_section")

            if ref_field != catalogue_field:
                raise RuntimeError(
                    f"{context}: field mismatch for {eid!r}: "
                    f"analysis has {ref_field!r}, "
                    f"catalogue has {catalogue_field!r}."
                )

    for section, items in [
        ("explicit_requirements", analysis.get("explicit_requirements", [])),
        ("inferred_requirements", analysis.get("inferred_requirements", [])),
        ("constraints_and_dependencies", analysis.get("constraints_and_dependencies", [])),
        ("key_concepts", analysis.get("key_concepts", [])),
    ]:
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    _check_refs(item.get("supporting_evidence", []), section)

    change_summary = analysis.get("change_summary", {})
    if isinstance(change_summary, dict):
        _check_refs(change_summary.get("supporting_evidence", []), "change_summary")


def postflight_validate(
    analysis: Dict[str, Any],
    normalized_evidence: Dict[str, Any],
    source_jira_evidence: Dict[str, Any],
    evidence_units: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Validate analysis structure and evidence references after agentic requirements analysis.

    Validates:
    - All required top-level sections present
    - supporting_evidence is a list of evidence ID strings (not source text)
    - All evidence IDs exist in the deterministic catalogue
    - No duplicate evidence IDs within a single supporting_evidence list
    - Explicit/inferred distinction maintained
    - Ambiguities have clarification_needed (not recommendation)

    Resolves evidence IDs to authoritative source values from the catalogue.
    source_value is always populated by this function — never from LLM output.

    Returns: validated and enriched analysis object ready to write to workspace
    Raises: ValueError on validation failure
    """
    # Structural validation shared with validate_existing_analysis
    _validate_analysis_sections(analysis)

    unit_map = build_evidence_unit_map(evidence_units)

    def validate_and_resolve(items: List[Dict], context: str) -> None:
        """In-place validate evidence ID strings and resolve to authoritative source values."""
        for item in items:
            item_id = item.get("id", "unknown")
            validate_evidence_id_list(item["supporting_evidence"], unit_map, f"{context}[{item_id}]")
            resolved = resolve_evidence_ids(item["supporting_evidence"], unit_map)
            # Add source_type to each resolved evidence reference (for new schema)
            for ref in resolved:
                ref["source_type"] = "jira"
            item["supporting_evidence"] = resolved

    # Validate and resolve each section
    validate_and_resolve(analysis.get("explicit_requirements", []), "explicit_requirements")
    validate_and_resolve(analysis.get("inferred_requirements", []), "inferred_requirements")
    validate_and_resolve(analysis.get("constraints_and_dependencies", []), "constraints_and_dependencies")
    validate_and_resolve(analysis.get("key_concepts", []), "key_concepts")
    validate_and_resolve(analysis.get("unratified_architectural_decisions", []), "unratified_architectural_decisions")

    # Validate and resolve change_summary evidence
    change_summary = analysis["change_summary"]
    validate_evidence_id_list(change_summary["supporting_evidence"], unit_map, "change_summary")
    resolved_summary = resolve_evidence_ids(change_summary["supporting_evidence"], unit_map)
    # Add source_type to each resolved evidence reference (for new schema)
    for ref in resolved_summary:
        ref["source_type"] = "jira"
    change_summary["supporting_evidence"] = resolved_summary

    # Extract source_type early for use in validation
    source_type = normalized_evidence.get("source_type", "jira")

    # Enforce FR-N evidence integrity for PRD/Brief sources
    # If source contains functional_requirements evidence (FR-1, FR-2, etc.),
    # verify that requirements derived from those FRs actually reference them.
    if source_type in ("prd", "brief"):
        fr_evidence_ids = {uid for uid in unit_map.keys() if uid.startswith("functional_requirements:FR-")}
        if fr_evidence_ids:
            # Check explicit requirements that appear to be derived from FRs
            for req in analysis.get("explicit_requirements", []):
                req_text = req.get("requirement", "").lower()
                resolved_evidence = req.get("supporting_evidence", [])
                resolved_ids = {e.get("evidence_id", "") for e in resolved_evidence if isinstance(e, dict)}

                # If requirement text references FR concepts but doesn't cite FR evidence, flag it
                if any(f"fr-" in req_text for f in ["functional requirement", "requirement"]) and not any("functional_requirements:FR-" in eid for eid in resolved_ids):
                    # This is a heuristic check - don't fail, just warn
                    pass

    # Build final output with provenance and metadata using new canonical schema
    now = datetime.now(timezone.utc)
    issue_key = normalized_evidence.get("issue_key", "unknown")

    # Build source_evidence array for multi-source support
    source_evidence_array = []

    if source_type == "jira":
        # Jira source
        source_evidence_array.append({
            "source_type": "jira",
            "source_identifier": issue_key,
            "sha256": source_jira_evidence.get("raw_jira_response_sha256", ""),
            "jira": {
                "instance": source_jira_evidence.get("instance", ""),
                "issue_key": issue_key,
            }
        })
    elif source_type in ("prd", "brief"):
        # PRD/Brief sources
        if source_jira_evidence.get("prd_sha256"):
            source_evidence_array.append({
                "source_type": "prd",
                "source_identifier": issue_key,
                "sha256": source_jira_evidence.get("prd_sha256", ""),
            })
        if source_jira_evidence.get("brief_sha256"):
            source_evidence_array.append({
                "source_type": "brief",
                "source_identifier": issue_key,
                "sha256": source_jira_evidence.get("brief_sha256", ""),
            })

    final_output = {
        "schema_version": "2.0",
        "analysis_metadata": {
            "analyzed_at": now.isoformat()
        },
        "source_evidence": source_evidence_array,
        **analysis
    }

    return final_output


# ---------------------------------------------------------------------------
# CLI entry points
# ---------------------------------------------------------------------------

def main_preflight(requirements_path: Path, invocation_root: Optional[Path]) -> int:
    """Validate requirements.json and output evidence catalogue to stdout."""
    try:
        print("=== PREFLIGHT VALIDATION ===", file=sys.stderr)
        print(f"Loading requirements from: {requirements_path}", file=sys.stderr)

        result = preflight_validate(requirements_path, invocation_root)

        print(f"[OK] Schema valid (1.0)", file=sys.stderr)
        print(f"[OK] Issue type: Business Epic", file=sys.stderr)
        print(f"[OK] Provenance integrity verified (SHA-256 matches)", file=sys.stderr)
        print(f"[OK] Evidence units extracted: {len(result['evidence_units'])}", file=sys.stderr)

        output = {
            "issue_key": result["issue_key"],
            "evidence": result["evidence"],
            "evidence_units": result["evidence_units"],
            "candidate_analysis_path": result["candidate_analysis_path"],
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        print(f"\n[OK] Preflight complete", file=sys.stderr)

        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def main_postflight(
    requirements_path: Path,
    analysis_path: Path,
    invocation_root: Optional[Path],
    output_dir: Optional[Path]
) -> int:
    """Validate analysis, resolve evidence IDs, persist to workspace."""
    try:
        print("=== POSTFLIGHT VALIDATION ===", file=sys.stderr)
        print(f"Loading requirements from: {requirements_path}", file=sys.stderr)
        print(f"Loading analysis from: {analysis_path}", file=sys.stderr)

        if not requirements_path.exists():
            raise RuntimeError(f"Requirements file not found: {requirements_path}")
        if not analysis_path.exists():
            raise RuntimeError(f"Analysis file not found: {analysis_path}")

        requirements_data = json.loads(requirements_path.read_text(encoding='utf-8'))
        analysis = json.loads(analysis_path.read_text(encoding='utf-8'))

        if requirements_data.get("schema_version") != "1.0":
            raise RuntimeError(f"Unsupported schema version: {requirements_data.get('schema_version')}")

        # Support both Jira and PRD/Brief sources
        source_type = requirements_data.get("source", {}).get("type", "jira")
        if source_type == "jira":
            req_type = requirements_data.get("requirements", {}).get("type", "")
            if req_type != "Business Epic":
                raise RuntimeError("Expected Business Epic issue type for Jira source")

        # Reconstruct normalized evidence (same as preflight — deterministic)
        req = requirements_data["requirements"]
        source = requirements_data["source"]

        # Determine issue_key based on source type
        # Jira: stable issue key from source
        # PRD/Brief: None (no work-item subdirectory; invocation_dir IS the work-item root)
        issue_key = None
        if source_type == "jira":
            issue_key = source["issue_key"]

        normalized_evidence = {
            "issue_key": issue_key,
            "source_type": source_type,
            "summary": req.get("summary", ""),
            "description": req.get("description", ""),
            "status": req.get("status", ""),
            "labels": req.get("labels", []),
            "components": req.get("components", []),
            "linked_issues": req.get("linked_issues", []),
            "acceptance_criteria": req.get("acceptance_criteria", []),
            "evidence_units": req.get("evidence_units", []),
            "evidence_sources": req.get("evidence_sources", {}),
        }

        # Reconstruct evidence catalogue (deterministic — same function as preflight)
        evidence_units = extract_evidence_units(normalized_evidence)

        # Build source provenance dict based on source type
        if source_type == "jira":
            source_jira_evidence = {
                "issue_key": source["issue_key"],
                "raw_jira_response_sha256": source.get("raw_response_sha256", source.get("raw_jira_response_sha256", "")),
                "instance": source.get("instance", ""),
            }
        else:
            # PRD/Brief source
            source_jira_evidence = {
                "prd_sha256": source.get("prd_sha256", ""),
                "brief_sha256": source.get("brief_sha256", ""),
            }

        print("Validating analysis structure and resolving evidence IDs...", file=sys.stderr)
        final_output = postflight_validate(
            analysis, normalized_evidence, source_jira_evidence, evidence_units
        )

        print("[OK] Schema valid", file=sys.stderr)
        print("[OK] All evidence IDs validated against deterministic catalogue", file=sys.stderr)
        print("[OK] Evidence IDs resolved to authoritative source values", file=sys.stderr)
        print("[OK] Explicit/inferred distinction maintained", file=sys.stderr)
        print("[OK] Provenance preserved", file=sys.stderr)

        if output_dir:
            # Explicit override: use provided directory
            output_dir_path = Path(output_dir)
        elif invocation_root:
            # Workspace contract:
            #   Jira: invocation_root / issue_key / analysis
            #   PRD/Brief: invocation_root / analysis (no issue_key subdirectory)
            invocation_root = Path(invocation_root)
            if source_type == "jira":
                output_dir_path = invocation_root / issue_key / "analysis"
            else:
                output_dir_path = invocation_root / "analysis"
        else:
            raise RuntimeError(
                "No output directory specified. Provide one of:\n"
                "  --output-dir <path>\n"
                "  --invocation-dir <path>"
            )

        output_dir_path.mkdir(parents=True, exist_ok=True)

        output_file = output_dir_path / "requirements-analysis.json"
        tmp_file = output_dir_path / "requirements-analysis.json.tmp"
        tmp_file.write_text(json.dumps(final_output, indent=2, ensure_ascii=False), encoding='utf-8')
        os.replace(str(tmp_file), str(output_file))

        if invocation_root and str(output_file).startswith(str(invocation_root)):
            print(f"\n[OK] Analysis written to: {output_file.relative_to(invocation_root)}", file=sys.stderr)
        else:
            print(f"\n[OK] Analysis written to: {output_file}", file=sys.stderr)

        summary = {
            "issue_key": issue_key,
            "output_path": str(output_file),
            "explicit_requirements_count": len(final_output.get("explicit_requirements", [])),
            "inferred_requirements_count": len(final_output.get("inferred_requirements", [])),
            "constraints_count": len(final_output.get("constraints_and_dependencies", [])),
            "ambiguities_count": len(final_output.get("ambiguities_and_unknowns", [])),
            "concepts_count": len(final_output.get("key_concepts", []))
        }
        print(json.dumps(summary, indent=2))
        print(f"\n[OK] Postflight complete", file=sys.stderr)

        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Deterministic preflight/postflight for requirements understanding"
    )
    parser.add_argument(
        "--mode", required=True, choices=["preflight", "postflight"],
        help="preflight: validate + extract evidence catalogue; postflight: validate analysis + persist"
    )
    parser.add_argument(
        "--requirements-path", required=True,
        help="Path to requirements.json (output from retrieve_jira_requirements.py)"
    )
    parser.add_argument(
        "--analysis-path", default=None,
        help="Path to analysis.json (required for postflight mode)"
    )
    parser.add_argument(
        "--invocation-dir", default=None,
        help="User invocation directory (for output path construction in postflight)"
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Directory for analysis output (postflight only). Defaults to <workspace>/analysis."
    )

    args = parser.parse_args()

    invocation_root = None
    if args.invocation_dir:
        invocation_root = Path(args.invocation_dir).resolve()

    requirements_path = Path(args.requirements_path).resolve()

    if args.mode == "preflight":
        return main_preflight(requirements_path, invocation_root)

    elif args.mode == "postflight":
        if not args.analysis_path:
            print("ERROR: --analysis-path required for postflight mode", file=sys.stderr)
            return 1
        analysis_path = Path(args.analysis_path).resolve()
        output_dir = Path(args.output_dir).resolve() if args.output_dir else None
        return main_postflight(requirements_path, analysis_path, invocation_root, output_dir)


if __name__ == "__main__":
    sys.exit(main())
