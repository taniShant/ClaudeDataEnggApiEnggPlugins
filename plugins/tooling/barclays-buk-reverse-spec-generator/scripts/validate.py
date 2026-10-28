#!/usr/bin/env python3
"""
Batch validation script for .spec files.

Validates one or more .spec files and generates a summary report.
Usage:
    python scripts/validate.py *.spec
    python scripts/validate.py dir/
    python scripts/validate.py file1.spec file2.spec
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.spec_validator import validate_spec_file, ValidationResult


def find_spec_files(patterns: list) -> list:
    """Find all .spec files matching given patterns or directories."""
    spec_files = []

    for pattern in patterns:
        path = Path(pattern)

        if path.is_file():
            if path.suffix in ['.spec', '.yaml'] or path.name.endswith('.spec'):
                spec_files.append(path)
        elif path.is_dir():
            # Recursively find all .spec files in directory
            spec_files.extend(path.glob('**/*.spec'))
            spec_files.extend(path.glob('**/*.spec.yaml'))

    return sorted(set(spec_files))


def validate_files(spec_files: list) -> tuple:
    """Validate multiple spec files and return results."""
    results = []

    for spec_file in spec_files:
        result = validate_spec_file(str(spec_file))
        results.append(result)

    return results


def print_summary(results: list):
    """Print validation summary report."""
    if not results:
        print("No .spec files found.")
        return

    total = len(results)
    valid = sum(1 for r in results if r.valid)
    invalid = total - valid

    print(f"\n{'='*60}")
    print(f"Validation Summary")
    print(f"{'='*60}")
    print(f"Total files:   {total}")
    print(f"Valid:         {valid}")
    print(f"Invalid:       {invalid}")
    print(f"{'='*60}\n")

    # Print details for each file
    for result in results:
        status = "✓ VALID" if result.valid else "✗ INVALID"
        print(f"{status}: {result.path}")

        if not result.valid:
            # Print errors
            for error in result.errors:
                print(f"  ERROR: {error}")

            # Print warnings if any
            for warning in result.warnings:
                print(f"  WARNING: {warning}")

        print()

    # Exit code
    return 0 if invalid == 0 else 1


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate.py <file_or_directory> [<file_or_directory> ...]")
        print("Example: python scripts/validate.py *.spec")
        sys.exit(2)

    patterns = sys.argv[1:]
    spec_files = find_spec_files(patterns)

    if not spec_files:
        print("No .spec files found matching the given patterns.")
        sys.exit(1)

    results = validate_files(spec_files)
    exit_code = print_summary(results)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
