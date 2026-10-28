#!/usr/bin/env python3
"""
Orchestrate prerequisite artefacts for requirements analysis.

Ensures normalised Jira evidence and requirements analysis are valid and current
before the agentic analysis stage proceeds.

Flow:
  1. Workspace state check:
       Both absent                  -> invoke retrieval subprocess (fetch + normalise)
       Raw present, normalised absent -> invoke retrieval subprocess (re-fetch)
       Normalised present, raw absent -> fail explicitly (provenance unverifiable)
       Both present                 -> proceed to validation
  2. Validate requirements.json schema + provenance (fail explicitly on any error).
  3. If requirements-analysis.json absent: return {analysis_status: "absent"}.
  4. Parse analysis; check schema_version + hash field (v1.0: source_jira_evidence.raw_jira_response_sha256, v2.0: source_evidence[0].sha256).
     If either missing or version unsupported: return {analysis_status: "invalid"}.
  5. Compare analysis SHA-256 with current evidence SHA-256.
     If different: return {analysis_status: "stale"} — stop here, do not validate
     evidence IDs against a different catalogue.
  6. SHA-256 equal: run _validate_analysis_sections + check_resolved_evidence_integrity.
     If invalid: return {analysis_status: "invalid"}.
  7. All checks pass: return {analysis_status: "reused"}.

Output to stdout: versioned JSON contract (orchestration_result.schema.json, version 1.0).
Exit 0 on success (including absent/stale/invalid analysis states).
Exit 1 on evidence failures only (invalid requirements.json, provenance mismatch, failed retrieval).

Never duplicates retrieval, normalisation, or validation logic:
- Retrieval:   subprocess via sys.executable (deterministic, no LLM)
- Validation:  imports from review_requirements and understand_requirements
"""

import sys
import os
import json
import subprocess
import io
from pathlib import Path
from typing import Optional, List, Dict, Any

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

from scripts.review_requirements import validate_requirements, verify_raw_response_hash
from scripts.understand_requirements import (
    validate_existing_analysis,
    check_resolved_evidence_integrity,
    extract_evidence_units,
)

_SCRIPT_DIR = Path(__file__).resolve().parent
_RETRIEVE_SCRIPT = _SCRIPT_DIR / "retrieve_jira_requirements.py"
_SCHEMA_PATH = _SCRIPT_DIR / "schemas" / "orchestration_result.schema.json"

ORCHESTRATION_SCHEMA_VERSION = "1.0"

# Default Jira fields for retrieval when --allowed-fields is not specified.
# retrieve_jira_requirements.py requires explicit --allowed-fields; this constant
# defines the canonical default so it is set in one place and propagated automatically.
DEFAULT_ALLOWED_FIELDS = "summary,description,labels,components,status,issuetype,issuelinks"


def _parse_bool(value: str) -> bool:
    """
    Parse a boolean environment variable value.

    Accepted true values (case-insensitive): "1", "true", "yes"
    Accepted false values (case-insensitive): "0", "false", "no"
    Invalid or absent values return False (secure default).
    """
    if not value:
        return False
    return value.lower() in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _requirements_path(invocation_root: Path, issue_key: str) -> Path:
    return invocation_root / issue_key / "requirements" / f"{issue_key}.json"


def _raw_path(invocation_root: Path, issue_key: str) -> Path:
    return invocation_root / issue_key / "raw" / f"{issue_key}.json"


def _analysis_path(invocation_root: Path, issue_key: str) -> Path:
    return invocation_root / issue_key / "analysis" / "requirements-analysis.json"


def _invoke_retrieval(
    issue_key: str,
    invocation_root: Path,
    allowed_fields: str,
    acceptance_criteria_field: Optional[str] = None,
    ssl_no_revoke: bool = False,
    clock: Optional[str] = None,
) -> None:
    """
    Invoke retrieve_jira_requirements.py as a subprocess.

    Uses sys.executable so the same Python interpreter and virtual environment are used
    regardless of PATH. The script path is resolved relative to this file so the
    invocation is independent of the current working directory.

    retrieve_jira_requirements.main() calls sys.exit() on error; subprocess isolation
    ensures that failure terminates the child process, not the orchestration process.

    Raises RuntimeError if the subprocess exits non-zero.
    """
    cmd = [
        sys.executable,
        str(_RETRIEVE_SCRIPT),
        "--issue-key", issue_key,
        "--invocation-dir", str(invocation_root),
        "--allowed-fields", allowed_fields,
    ]
    if acceptance_criteria_field:
        cmd += ["--acceptance-criteria-field", acceptance_criteria_field]
    if ssl_no_revoke:
        cmd.append("--ssl-no-revoke")
    if clock:
        cmd += ["--clock", clock]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Retrieval failed for {issue_key} (exit {result.returncode}):\n{result.stderr}"
        )


def _validate_orchestration_result(result: dict) -> None:
    """
    Validate an orchestration result dict against orchestration_result.schema.json.

    Checks all required fields are present and that enum/const constraints hold.
    Uses manual validation consistent with the repository's existing convention
    (no external jsonschema library dependency).

    Raises RuntimeError if validation fails.
    """
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))

    for field in schema.get("required", []):
        if field not in result:
            raise RuntimeError(f"Orchestration result missing required field: {field!r}")

    properties = schema.get("properties", {})
    for field, spec in properties.items():
        if field not in result:
            continue
        value = result[field]
        if "const" in spec and value != spec["const"]:
            raise RuntimeError(
                f"Orchestration result field {field!r} must be {spec['const']!r}, got {value!r}"
            )
        if "enum" in spec and value not in spec["enum"]:
            raise RuntimeError(
                f"Orchestration result field {field!r} has invalid value {value!r}. "
                f"Allowed: {spec['enum']}"
            )


def _build_result(
    issue_key: str,
    req_path: Path,
    evidence_status: str,
    current_sha256: str,
    analysis_path: Optional[Path],
    analysis_status: str,
    required_next_action: str,
) -> dict:
    result = {
        "schema_version": ORCHESTRATION_SCHEMA_VERSION,
        "issue_key": issue_key,
        "requirements_path": str(req_path),
        "evidence_status": evidence_status,
        "evidence_sha256": current_sha256,
        "analysis_path": str(analysis_path) if analysis_path else None,
        "analysis_status": analysis_status,
        "required_next_action": required_next_action,
    }
    _validate_orchestration_result(result)
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def orchestrate_prerequisites(
    issue_key: str,
    invocation_root: Path,
    allowed_fields: str = DEFAULT_ALLOWED_FIELDS,
    acceptance_criteria_field: Optional[str] = None,
    ssl_no_revoke: bool = False,
    clock: Optional[str] = None,
) -> dict:
    """
    Ensure normalised Jira evidence and requirements analysis are valid and current.

    Work-item state handling:
      Both absent                  -> invoke retrieval (fetch + normalise)
      Raw present, normalised absent -> invoke retrieval (re-fetch for consistency)
      Normalised present, raw absent -> RuntimeError (provenance unverifiable)
      Both present                 -> validate schema + provenance; proceed

    Returns:
        dict conforming to orchestration_result.schema.json (schema_version 1.0).
        See _build_result for field definitions.

    Raises:
        RuntimeError for fatal evidence failures: invalid schema, provenance mismatch,
        unverifiable work-item state, or retrieval subprocess failure.
        These must never be silently consumed.
    """
    invocation_root = Path(invocation_root).resolve()
    work_item_root = invocation_root / issue_key
    req_path = _requirements_path(invocation_root, issue_key)
    raw_path = _raw_path(invocation_root, issue_key)
    analysis_path = _analysis_path(invocation_root, issue_key)

    raw_present = raw_path.exists()
    normalised_present = req_path.exists()

    # --- Workspace state matrix ---

    if not raw_present and not normalised_present:
        _invoke_retrieval(
            issue_key, invocation_root, allowed_fields,
            acceptance_criteria_field, ssl_no_revoke, clock
        )
        evidence_status = "retrieved"

    elif raw_present and not normalised_present:
        # Re-fetch rather than normalise-only: reuses a single entry point, avoids
        # logic for reconstructing a normalisation call, and is safe + deterministic.
        _invoke_retrieval(
            issue_key, invocation_root, allowed_fields,
            acceptance_criteria_field, ssl_no_revoke, clock
        )
        evidence_status = "retrieved"

    elif not raw_present and normalised_present:
        raise RuntimeError(
            f"Cannot verify provenance: raw response file missing for {issue_key} "
            f"({raw_path}). "
            f"requirements.json exists but cannot be trusted without its source file. "
            f"Re-run the retrieve-jira-requirements skill to restore both files."
        )

    else:
        evidence_status = "validated"

    # --- Validate evidence schema and provenance integrity ---
    requirements_data = validate_requirements(req_path)
    verify_raw_response_hash(requirements_data, req_path, work_item_root)

    current_sha256 = requirements_data["source"]["raw_response_sha256"]

    # --- Analysis absent ---
    if not analysis_path.exists():
        return _build_result(
            issue_key, req_path, evidence_status, current_sha256,
            None, "absent", "run_analysis"
        )

    # --- Minimal parse to read provenance before full validation ---
    try:
        analysis_data = json.loads(analysis_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _build_result(
            issue_key, req_path, evidence_status, current_sha256,
            analysis_path, "invalid", "run_analysis"
        )

    schema_version = analysis_data.get("schema_version")
    analysis_sha256 = None

    # Support both v1.0 (source_jira_evidence) and v2.0 (source_evidence array)
    if schema_version == "1.0":
        source_jira_evidence = analysis_data.get("source_jira_evidence")
        if not source_jira_evidence or "raw_jira_response_sha256" not in source_jira_evidence:
            return _build_result(
                issue_key, req_path, evidence_status, current_sha256,
                analysis_path, "invalid", "run_analysis"
            )
        analysis_sha256 = source_jira_evidence["raw_jira_response_sha256"]
    elif schema_version == "2.0":
        source_evidence = analysis_data.get("source_evidence")
        if not source_evidence or not isinstance(source_evidence, list) or len(source_evidence) == 0:
            return _build_result(
                issue_key, req_path, evidence_status, current_sha256,
                analysis_path, "invalid", "run_analysis"
            )
        # Extract hash from first source (primary)
        analysis_sha256 = source_evidence[0].get("sha256")
        if not analysis_sha256:
            return _build_result(
                issue_key, req_path, evidence_status, current_sha256,
                analysis_path, "invalid", "run_analysis"
            )
    else:
        return _build_result(
            issue_key, req_path, evidence_status, current_sha256,
            analysis_path, "invalid", "run_analysis"
        )

    # --- Stale detection: stop before evidence-ID validation against a different catalogue ---
    if analysis_sha256 != current_sha256:
        return _build_result(
            issue_key, req_path, evidence_status, current_sha256,
            analysis_path, "stale", "run_analysis"
        )

    # --- SHA-256 equal: full structural + read-only evidence integrity validation ---
    try:
        validate_existing_analysis(analysis_path)

        req_obj = requirements_data.get("requirements", {})
        normalized_evidence = {
            "issue_key": requirements_data["source"]["issue_key"],
            "summary": req_obj.get("summary", ""),
            "description": req_obj.get("description", ""),
            "status": req_obj.get("status", ""),
            "labels": req_obj.get("labels", []),
            "components": req_obj.get("components", []),
            "linked_issues": req_obj.get("linked_issues", []),
            "acceptance_criteria": req_obj.get("acceptance_criteria", []),
        }
        evidence_units = extract_evidence_units(normalized_evidence)
        check_resolved_evidence_integrity(analysis_data, evidence_units)

    except (RuntimeError, ValueError):
        return _build_result(
            issue_key, req_path, evidence_status, current_sha256,
            analysis_path, "invalid", "run_analysis"
        )

    return _build_result(
        issue_key, req_path, evidence_status, current_sha256,
        analysis_path, "reused", "none"
    )


def main() -> int:
    """CLI entry point. Prints versioned JSON contract to stdout."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Orchestrate prerequisite artefacts for requirements analysis"
    )
    parser.add_argument("--issue-key", required=True, help="Jira issue key")
    parser.add_argument(
        "--invocation-dir", required=True,
        help="User invocation directory (where work-item subdirectories are created)"
    )
    parser.add_argument(
        "--allowed-fields", default=None,
        help=f"Comma-separated Jira fields for retrieval. Defaults to: {DEFAULT_ALLOWED_FIELDS}"
    )
    parser.add_argument(
        "--acceptance-criteria-field", default=None,
        help="Custom field ID for acceptance criteria (e.g. customfield_12345)"
    )
    parser.add_argument(
        "--ssl-no-revoke", action="store_true",
        help="Pass --ssl-no-revoke to curl (Windows Schannel workaround)"
    )
    parser.add_argument(
        "--clock", default=None,
        help="Override retrieval timestamp (testing only, ISO-8601)"
    )

    args = parser.parse_args()

    invocation_root = Path(args.invocation_dir).resolve()
    allowed_fields = args.allowed_fields or DEFAULT_ALLOWED_FIELDS

    # Determine SSL no-revoke flag (precedence: CLI flag > BUK_SA_SSL_NO_REVOKE env var > default False)
    # Env var values: 1, true, yes (case-insensitive) = enabled; 0, false, no = disabled
    ssl_no_revoke = args.ssl_no_revoke or _parse_bool(os.environ.get("BUK_SA_SSL_NO_REVOKE", ""))

    try:
        result = orchestrate_prerequisites(
            issue_key=args.issue_key,
            invocation_root=invocation_root,
            allowed_fields=allowed_fields,
            acceptance_criteria_field=args.acceptance_criteria_field,
            ssl_no_revoke=ssl_no_revoke,
            clock=args.clock,
        )
        print(json.dumps(result, indent=2))
        return 0
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
