#!/usr/bin/env python3
"""
Persist candidate capability impact findings to workspace.

This helper accepts JSON findings content and writes it safely to the specified path.
It handles cross-platform path handling, directory creation, and proper JSON encoding.

Usage:
    cat findings.json | python persist_capability_findings.py --output-path /path/to/candidate-capability-impact.json

    Or with JSON content directly:
    python persist_capability_findings.py --output-path /path/to/output.json < input.json
"""

import sys
import json
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Persist capability impact findings JSON to workspace"
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        required=True,
        help="Absolute path where findings JSON will be written"
    )

    args = parser.parse_args()

    try:
        # Validate path is absolute
        if not args.output_path.is_absolute():
            raise ValueError(f"Output path must be absolute: {args.output_path}")

        # Read JSON from stdin
        input_data = sys.stdin.read()
        if not input_data.strip():
            raise ValueError("No JSON input provided on stdin")

        findings_data = json.loads(input_data)

        # Create directory structure
        args.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write with proper encoding (cross-platform safe)
        with open(args.output_path, 'w', encoding='utf-8') as f:
            json.dump(findings_data, f, indent=2, ensure_ascii=False)

        # Report success
        result = {
            "status": "success",
            "persisted_path": str(args.output_path.resolve())
        }
        print(json.dumps(result, indent=2))
        return 0

    except json.JSONDecodeError as e:
        print(json.dumps({
            "status": "error",
            "error": f"Invalid JSON input: {e}"
        }), file=sys.stderr)
        return 1
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": str(e)
        }), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
