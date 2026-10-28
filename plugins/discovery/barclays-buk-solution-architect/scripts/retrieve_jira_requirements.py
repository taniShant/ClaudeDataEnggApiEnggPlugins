#!/usr/bin/env python3
"""
Deterministic Jira requirements retrieval.

Fetches raw Jira issue via REST API, saves the exact HTTP response bytes,
and normalises into requirements.json with embedded provenance.

Usage:
    python retrieve_jira_requirements.py \
      --issue-key BUKL2CUSX-173655 \
      --invocation-dir /path/to/work \
      --allowed-fields summary,description,labels,components,status,issuetype,issuelinks \
      --acceptance-criteria-field customfield_12345

Output (beneath invocation directory):
    <invocation-dir>/{issue_key}/raw/{issue_key}.json           — exact HTTP response bytes
    <invocation-dir>/{issue_key}/requirements/{issue_key}.json  — normalised with provenance
"""

import sys
import os
import json
import hashlib
import subprocess
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

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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


def get_git_root() -> Path:
    """Return the git repository root directory."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError("Could not determine git root. Ensure you are in a git repository.")




def fetch_jira_raw(
    issue_key: str,
    allowed_fields: List[str],
    clock: Optional[datetime] = None,
    ssl_no_revoke: bool = False
) -> tuple[bytes, str, str]:
    """
    Fetch raw Jira issue via curl, preserving exact HTTP response bytes.

    Returns: (raw_bytes, timestamp_iso, http_status_reason)
    Raises: RuntimeError on auth failure or API error

    ssl_no_revoke: If True, pass --ssl-no-revoke to curl (Windows Schannel workaround)
    """
    auth_token = os.environ.get("JIRA_AUTH_TOKEN")
    if not auth_token:
        raise RuntimeError(
            "JIRA_AUTH_TOKEN is not set.\n"
            "To generate a Personal Access Token:\n"
            "  1. Visit: https://estjira.barcapint.com/secure/ViewProfile.jspa\n"
            "  2. Click Personal Access Tokens\n"
            "  3. Create a new token and copy it\n"
            "To set it:\n"
            "  export JIRA_AUTH_TOKEN='<token>'"
        )

    # Record retrieval timestamp
    now = clock or datetime.now(timezone.utc)
    timestamp_iso = now.isoformat()

    # Build Jira API URL with requested fields
    fields_param = ",".join(sorted(allowed_fields)) if allowed_fields else ""
    url = f"https://estjira.barcapint.com/rest/api/2/issue/{issue_key}"
    if fields_param:
        url += f"?fields={fields_param}"

    # Call curl, capturing raw response
    try:
        curl_cmd = [
            "curl",
            "-s",
            "-w", "\n%{http_code}",
            "-H", f"Authorization: Bearer {auth_token}",
            "-H", "Content-Type: application/json",
        ]
        if ssl_no_revoke:
            curl_cmd.append("--ssl-no-revoke")
        curl_cmd.append(url)

        result = subprocess.run(
            curl_cmd,
            capture_output=True,
            text=False,  # Binary mode to preserve exact bytes
            check=False
        )
    except FileNotFoundError:
        raise RuntimeError("curl is not installed or not in PATH")

    # Split response and status code
    output_bytes = result.stdout
    lines = output_bytes.split(b"\n")
    http_code_str = lines[-1].decode("utf-8", errors="replace").strip()
    body_bytes = b"\n".join(lines[:-1])

    try:
        http_code = int(http_code_str)
    except ValueError:
        stderr_msg = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
        raise RuntimeError(
            f"Unexpected curl output: could not parse HTTP code from {http_code_str}. "
            f"curl stderr: {stderr_msg[:200]}"
        )

    if http_code != 200:
        stderr_msg = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
        try:
            error_body = json.loads(body_bytes.decode("utf-8"))
            error_msg = error_body.get("errorMessages", [str(error_body)])
            raise RuntimeError(f"Jira API returned HTTP {http_code}: {error_msg}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            stderr_suffix = f". curl stderr: {stderr_msg[:200]}" if stderr_msg else ""
            raise RuntimeError(
                f"Jira API returned HTTP {http_code}. "
                f"Response: {body_bytes.decode('utf-8', errors='replace')[:200]}"
                f"{stderr_suffix}"
            )

    return body_bytes, timestamp_iso, "OK"


def normalize_requirements(
    raw_jira_json: Dict[str, Any],
    allowed_fields: List[str],
    acceptance_criteria_field_id: Optional[str],
    timestamp_iso: str,
    instance: str,
    issue_key: str,
    raw_file_path: Path,
    raw_response_sha256: str,
    output_dir: Path
) -> Dict[str, Any]:
    """
    Deterministically normalize raw Jira response into requirements.json.

    Only touches fields explicitly in allowed_fields.
    Uses empty arrays for absent fields, populates warnings for unconfigured fields.
    Fails explicitly on structurally invalid values (missing field paths don't coerce to empty).

    raw_file_path is made relative to output_dir for portability.
    """
    if not isinstance(raw_jira_json, dict):
        raise ValueError(f"Expected Jira response to be a dict, got {type(raw_jira_json).__name__}")

    fields = raw_jira_json.get("fields", {})
    if not isinstance(fields, dict):
        raise ValueError(f"Expected 'fields' to be a dict, got {type(fields).__name__}")
    warnings = []

    # Extract allowed fields with fallback to empty/None
    summary = fields.get("summary", "")
    description = fields.get("description", "")
    status = (fields.get("status") or {}).get("name", "")
    issue_type = (fields.get("issuetype") or {}).get("name", "")

    # Labels: extract and sort (must be list if present)
    labels = fields.get("labels", [])
    if labels and not isinstance(labels, list):
        raise ValueError(f"Expected 'labels' to be a list, got {type(labels).__name__}")
    labels = sorted(labels) if labels else []

    # Components: extract names and sort (must be list if present)
    components = fields.get("components", [])
    if components and not isinstance(components, list):
        raise ValueError(f"Expected 'components' to be a list, got {type(components).__name__}")
    if components:
        components = sorted([c.get("name", "") for c in components if c])
    else:
        components = []

    # Issue links: extract and sort (must be list if present)
    linked_issues = []
    issuelinks = fields.get("issuelinks", [])
    if issuelinks and not isinstance(issuelinks, list):
        raise ValueError(f"Expected 'issuelinks' to be a list, got {type(issuelinks).__name__}")
    if issuelinks:
        for link in issuelinks:
            link_type = (link.get("type") or {}).get("name", "")
            direction = "outward" if "outwardIssue" in link else "inward"
            issue = (link.get("outwardIssue") or link.get("inwardIssue") or {}).get("key", "")
            if issue:
                linked_issues.append({
                    "issue_key": issue,
                    "link_type": link_type,
                    "direction": direction
                })

    # Sort linked issues by issue_key
    linked_issues = sorted(linked_issues, key=lambda x: x["issue_key"])

    # Acceptance criteria: use configured field or warn
    acceptance_criteria = []
    if acceptance_criteria_field_id:
        ac_value = fields.get(acceptance_criteria_field_id, "")
        if ac_value:
            if isinstance(ac_value, str):
                acceptance_criteria = [ac_value] if ac_value else []
            elif isinstance(ac_value, list):
                acceptance_criteria = ac_value
    else:
        warnings.append(
            "Acceptance criteria field not configured. "
            "Pass --acceptance-criteria-field to extract custom field."
        )

    # Build requirements object
    requirements_obj = {
        "summary": summary,
        "description": description,
        "type": issue_type,
        "status": status,
        "labels": labels,
        "components": components,
        "linked_issues": linked_issues,
        "acceptance_criteria": acceptance_criteria
    }

    # Build source/provenance (raw_file_path relative to output_dir for portability)
    raw_file_display = str(Path(raw_file_path).relative_to(output_dir))

    source_obj = {
        "type": "jira",
        "instance": instance,
        "issue_key": issue_key,
        "retrieved_at": timestamp_iso,
        "endpoint": "/rest/api/2/issue/{issue_key}",
        "requested_fields": sorted(allowed_fields),
        "raw_response_file": raw_file_display,
        "raw_response_sha256": raw_response_sha256
    }

    return {
        "schema_version": "1.0",
        "source": source_obj,
        "requirements": requirements_obj,
        "warnings": warnings
    }


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Retrieve Jira issue and normalise into requirements.json"
    )
    parser.add_argument("--issue-key", required=True, help="Jira issue key (e.g. BUKL2CUSX-173655)")
    parser.add_argument(
        "--invocation-dir",
        required=True,
        help="User invocation directory (where work-item subdirectories are created)"
    )
    parser.add_argument(
        "--allowed-fields",
        required=True,
        help="Comma-separated list of Jira fields to retrieve"
    )
    parser.add_argument(
        "--acceptance-criteria-field",
        default=None,
        help="Jira custom field ID for acceptance criteria (e.g. customfield_12345)"
    )
    parser.add_argument(
        "--clock",
        default=None,
        help="Override current timestamp for testing (ISO-8601 format)"
    )
    parser.add_argument(
        "--ssl-no-revoke",
        action="store_true",
        help="Pass --ssl-no-revoke to curl (Windows Schannel workaround for revocation check failures)"
    )

    args = parser.parse_args()

    try:
        # Parse arguments
        issue_key = args.issue_key.strip()
        allowed_fields = [f.strip() for f in args.allowed_fields.split(",")]
        acceptance_criteria_field = args.acceptance_criteria_field

        # Parse clock if provided (for deterministic tests)
        clock = None
        if args.clock:
            try:
                clock = datetime.fromisoformat(args.clock.replace("Z", "+00:00"))
            except ValueError:
                raise RuntimeError(f"Invalid clock format: {args.clock}. Use ISO-8601.")

        # Determine SSL no-revoke flag (precedence: CLI flag > BUK_SA_SSL_NO_REVOKE env var > default False)
        # Env var values: 1, true, yes (case-insensitive) = enabled; 0, false, no = disabled
        ssl_no_revoke = args.ssl_no_revoke or _parse_bool(os.environ.get("BUK_SA_SSL_NO_REVOKE", ""))

        # Resolve invocation directory to work-item root
        invocation_dir = Path(args.invocation_dir).resolve()
        work_item_root = invocation_dir / issue_key

        raw_dir = work_item_root / "raw"
        req_dir = work_item_root / "requirements"
        raw_dir.mkdir(parents=True, exist_ok=True)
        req_dir.mkdir(parents=True, exist_ok=True)

        # Fetch raw Jira response
        raw_bytes, timestamp_iso, _ = fetch_jira_raw(issue_key, allowed_fields, clock, ssl_no_revoke=ssl_no_revoke)

        # Save raw response
        raw_file = raw_dir / f"{issue_key}.json"
        raw_file.write_bytes(raw_bytes)
        print(f"✓ Raw response saved to: {raw_file.relative_to(invocation_dir)}", file=sys.stderr)

        # Calculate SHA-256 of raw bytes
        raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()

        # Parse and normalize
        raw_jira_json = json.loads(raw_bytes.decode("utf-8"))
        requirements_data = normalize_requirements(
            raw_jira_json=raw_jira_json,
            allowed_fields=allowed_fields,
            acceptance_criteria_field_id=acceptance_criteria_field,
            timestamp_iso=timestamp_iso,
            instance="estjira.barcapint.com",
            issue_key=issue_key,
            raw_file_path=raw_file,
            raw_response_sha256=raw_sha256,
            output_dir=work_item_root
        )

        # Save requirements
        req_file = req_dir / f"{issue_key}.json"
        req_file.write_text(json.dumps(requirements_data, indent=2))
        print(f"✓ Requirements saved to: {req_file.relative_to(invocation_dir)}", file=sys.stderr)

        # Print provenance summary
        source = requirements_data["source"]
        print("\n=== PROVENANCE ===", file=sys.stderr)
        print(f"Jira Instance: {source['instance']}", file=sys.stderr)
        print(f"Issue Key: {source['issue_key']}", file=sys.stderr)
        print(f"Retrieved: {source['retrieved_at']}", file=sys.stderr)
        print(f"Endpoint: {source['endpoint']}", file=sys.stderr)
        print(f"Requested Fields: {', '.join(source['requested_fields'])}", file=sys.stderr)
        print(f"Raw Response SHA256: {source['raw_response_sha256']}", file=sys.stderr)
        print(f"Raw File: {source['raw_response_file']}", file=sys.stderr)

        if requirements_data.get("warnings"):
            print("\n=== WARNINGS ===", file=sys.stderr)
            for warn in requirements_data["warnings"]:
                print(f"⚠ {warn}", file=sys.stderr)

        print("\n✓ Success", file=sys.stderr)
        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
