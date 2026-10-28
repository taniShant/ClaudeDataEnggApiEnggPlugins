#!/usr/bin/env python3
"""
Review and validate requirements.json.

Verifies schema, checks raw response hash, and prints provenance.
Never calls Jira or any LLM.

Usage:
    python review_requirements.py --requirements-path <workspace>/requirements/BUKL2CUSX-173655.json
"""

import sys
import os
import json
import hashlib
import io
from pathlib import Path

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


def validate_requirements(requirements_path: Path) -> dict:
    """
    Load and validate requirements.json.

    Returns: parsed requirements object
    Raises: RuntimeError on validation failure
    """
    if not requirements_path.exists():
        raise RuntimeError(f"Requirements file not found: {requirements_path}")

    try:
        requirements_data = json.loads(requirements_path.read_text())
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in {requirements_path}: {e}")

    # Validate schema
    if requirements_data.get("schema_version") != "1.0":
        raise RuntimeError(
            f"Unsupported schema version: {requirements_data.get('schema_version')}"
        )

    source = requirements_data.get("source")
    if not source:
        raise RuntimeError("Missing 'source' key in requirements")

    required_source_fields = [
        "type", "instance", "issue_key", "retrieved_at", "endpoint",
        "requested_fields", "raw_response_file", "raw_response_sha256"
    ]
    for field in required_source_fields:
        if field not in source:
            raise RuntimeError(f"Missing required source field: {field}")

    if source.get("type") != "jira":
        raise RuntimeError(f"Unexpected source type: {source.get('type')}")

    if not requirements_data.get("requirements"):
        raise RuntimeError("Missing 'requirements' key")

    return requirements_data


def verify_raw_response_hash(requirements_data: dict, requirements_path: Path, workspace_dir: Path = None) -> bool:
    """
    Verify that the raw response file matches the recorded SHA-256.

    Returns: True if hash matches
    Raises: RuntimeError if hash mismatch or file not found

    workspace_dir: if provided, raw file is located here; otherwise inferred from requirements_path
    """
    source = requirements_data["source"]

    # Determine where to look for raw response
    if workspace_dir:
        raw_file_path = workspace_dir / source["raw_response_file"]
    else:
        # Infer from requirements_path (assume structure: workspace/requirements/issue_key.json)
        raw_file_path = requirements_path.parent.parent / "raw" / f"{source['issue_key']}.json"

    if not raw_file_path.exists():
        raise RuntimeError(f"Raw response file not found: {raw_file_path}")

    raw_bytes = raw_file_path.read_bytes()
    computed_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    recorded_sha256 = source["raw_response_sha256"]

    if computed_sha256 != recorded_sha256:
        raise RuntimeError(
            f"Hash mismatch for raw response!\n"
            f"  Expected: {recorded_sha256}\n"
            f"  Computed: {computed_sha256}\n"
            f"  File: {raw_file_path}\n"
            f"The raw response may have been modified."
        )

    return True


def print_provenance(requirements_data: dict):
    """Print provenance information."""
    source = requirements_data["source"]
    print("\n=== PROVENANCE ===")
    print(f"Jira Instance: {source['instance']}")
    print(f"Issue Key: {source['issue_key']}")
    print(f"Retrieved: {source['retrieved_at']}")
    print(f"Endpoint: {source['endpoint']}")
    print(f"Requested Fields: {', '.join(source['requested_fields'])}")
    print(f"Raw Response SHA256: {source['raw_response_sha256']} ✓ verified")
    print(f"Raw File: {source['raw_response_file']}")


def print_requirements_summary(requirements_data: dict):
    """Print a summary of normalized requirements."""
    req = requirements_data["requirements"]
    print("\n=== NORMALIZED REQUIREMENTS ===")
    print(f"Title: {req.get('summary', '(empty)')}")
    print(f"Description: {req.get('description', '(empty)')[:100]}")
    if len(req.get('description', '')) > 100:
        print("  ...")
    print(f"Type: {req.get('type', '(empty)')}")
    print(f"Status: {req.get('status', '(empty)')}")
    labels = req.get("labels", [])
    print(f"Labels: {labels if labels else '(none)'}")
    components = req.get("components", [])
    print(f"Components: {components if components else '(none)'}")
    linked = req.get("linked_issues", [])
    if linked:
        print(f"Linked Issues: {', '.join([l['issue_key'] for l in linked])}")
    else:
        print("Linked Issues: (none)")
    ac = req.get("acceptance_criteria", [])
    if ac:
        print(f"Acceptance Criteria: {len(ac)} item(s)")
        for i, criterion in enumerate(ac[:3], 1):
            print(f"  {i}. {criterion[:80]}")
        if len(ac) > 3:
            print(f"  ... and {len(ac) - 3} more")
    else:
        print("Acceptance Criteria: (none)")


def print_warnings(requirements_data: dict):
    """Print any warnings from normalization."""
    warnings = requirements_data.get("warnings", [])
    if warnings:
        print("\n=== WARNINGS ===")
        for warn in warnings:
            print(f"⚠ {warn}")


def main():
    """Main entry point."""
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="Review and validate requirements.json"
    )
    parser.add_argument(
        "--requirements-path",
        required=True,
        help="Path to requirements.json"
    )
    parser.add_argument(
        "--invocation-dir",
        default=None,
        help="User invocation directory (optional, for hash verification)"
    )

    args = parser.parse_args()

    try:
        requirements_path = Path(args.requirements_path).resolve()

        # Determine invocation root (optional, for hash verification)
        invocation_root = None
        if args.invocation_dir:
            invocation_root = Path(args.invocation_dir).resolve()

        # Validate schema
        print(f"Loading requirements from: {requirements_path}", file=sys.stderr)
        requirements_data = validate_requirements(requirements_path)
        print("✓ Schema valid", file=sys.stderr)

        # Verify hash
        print("Verifying raw response hash...", file=sys.stderr)
        verify_raw_response_hash(requirements_data, requirements_path, invocation_root)
        print("✓ Raw response hash verified", file=sys.stderr)

        # Print provenance and summary
        print_provenance(requirements_data)
        print_requirements_summary(requirements_data)
        print_warnings(requirements_data)

        print("\n✓ Ready for architecture review.", file=sys.stderr)
        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
