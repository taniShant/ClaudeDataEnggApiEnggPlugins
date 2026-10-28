#!/usr/bin/env python3
"""
Barclays OAS Validator - HTTP API Client

Validates OpenAPI specifications by calling the Barclays OAS Validator HTTP endpoint.
Uses Python requests library with retry logic.

Usage:
    python3 oas-validator.py <spec_path> [options]

Options:
    --all-files       Validate all YAML files in the OAS directory (creates zip)
    --format json     Output format (json or text)
    -o, --output      Output file path
    --type            API type (internal/external) - for display only
"""

import argparse
import json
import os
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

try:
    import requests
    import urllib3
    # Suppress SSL certificate verification warnings
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    print("ERROR: requests library required. Install with: pip3 install requests", file=sys.stderr)
    sys.exit(1)

# Barclays OAS Validator endpoint
VALIDATOR_URL = "https://oasvalidator.barclays.intranet/v1.0/open-apis/validate"

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def detect_api_type(spec_path: str) -> str:
    """Auto-detect API type from spec file or doc-api.md."""
    spec_dir = Path(spec_path).parent

    # Check doc-api.md
    doc_api_paths = [
        spec_dir.parent / 'raml' / 'docs' / 'doc-api.md',
        spec_dir / 'docs' / 'doc-api.md',
        spec_dir.parent / 'docs' / 'doc-api.md',
    ]

    for doc_path in doc_api_paths:
        if doc_path.exists():
            try:
                content = doc_path.read_text()
                if 'Internal Process API' in content or 'internal' in content.lower():
                    return 'internal'
                elif 'External' in content:
                    return 'external'
            except:
                pass

    # Check openapi.yaml description
    try:
        import yaml
        with open(spec_path) as f:
            spec = yaml.safe_load(f)
        description = spec.get('info', {}).get('description', '')
        if 'internal' in description.lower():
            return 'internal'
        elif 'external' in description.lower():
            return 'external'
    except:
        pass

    return 'internal'  # Default


def create_oas_zip(spec_path: str, all_files: bool = True) -> str:
    """
    Create a zip file containing OAS files for validation.

    Args:
        spec_path: Path to the main OpenAPI spec file
        all_files: If True, include all YAML/JSON files in directory; else just the spec file

    Returns:
        Path to the temporary zip file
    """
    spec_path = Path(spec_path)
    oas_dir = spec_path.parent

    # Create temporary zip file
    zip_path = tempfile.mktemp(suffix='.zip')

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        if all_files:
            # Add all YAML and JSON files from the OAS directory
            for ext in ['*.yaml', '*.yml', '*.json']:
                for file_path in oas_dir.rglob(ext):
                    # Skip node_modules, .git, etc.
                    if any(part.startswith('.') or part == 'node_modules' for part in file_path.parts):
                        continue
                    arcname = file_path.relative_to(oas_dir)
                    zf.write(file_path, arcname)
        else:
            # Just add the single spec file
            zf.write(spec_path, spec_path.name)

    return zip_path


def validate_oas(spec_path: str, all_files: bool = True) -> Dict:
    """
    Validate OAS specification by calling Barclays HTTP endpoint.
    Always sends a zip file as required by the endpoint.

    Args:
        spec_path: Path to the main OpenAPI spec file
        all_files: If True, zip all files in OAS directory; else zip just the spec file

    Returns:
        Validation response as dictionary
    """
    # Create zip file (endpoint requires zip format)
    zip_path = create_oas_zip(spec_path, all_files)

    # Prepare the multipart form data
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'Origin': 'https://oasvalidator.barclays.intranet',
        'Referer': 'https://oasvalidator.barclays.intranet/validator/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    }

    try:
        # Retry logic
        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                with open(zip_path, 'rb') as f:
                    files = {
                        'file': ('oas.zip', f, 'application/zip')
                    }
                    data = {
                        'requestId': ''
                    }

                    response = requests.post(
                        VALIDATOR_URL,
                        headers=headers,
                        files=files,
                        data=data,
                        timeout=60,
                        verify=False  # Bypass SSL certificate verification for internal certs
                    )

                if response.status_code == 200:
                    return response.json()
                else:
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                    print(f"Attempt {attempt}/{MAX_RETRIES} failed: {last_error}", file=sys.stderr)

            except requests.exceptions.ConnectionError as e:
                last_error = f"Connection error: {e}"
                print(f"Attempt {attempt}/{MAX_RETRIES} failed: {last_error}", file=sys.stderr)
            except requests.exceptions.Timeout as e:
                last_error = f"Timeout: {e}"
                print(f"Attempt {attempt}/{MAX_RETRIES} failed: {last_error}", file=sys.stderr)
            except requests.exceptions.RequestException as e:
                last_error = f"Request error: {e}"
                print(f"Attempt {attempt}/{MAX_RETRIES} failed: {last_error}", file=sys.stderr)

            # Wait before retry (except on last attempt)
            if attempt < MAX_RETRIES:
                print(f"Retrying in {RETRY_DELAY} seconds...", file=sys.stderr)
                time.sleep(RETRY_DELAY)

        # All retries failed
        return {
            "error": True,
            "message": f"Validation failed after {MAX_RETRIES} attempts. Last error: {last_error}"
        }

    finally:
        # Clean up temp zip file
        try:
            os.unlink(zip_path)
        except:
            pass


def format_output(result: Dict, format_type: str = 'text') -> str:
    """Format validation result for output."""
    if format_type == 'json':
        return json.dumps(result, indent=2)

    # Text format
    if 'error' in result and result['error']:
        return f"ERROR: {result.get('message', 'Unknown error')}"

    output = []
    data = result.get('data', {})
    info = data.get('info', {})
    issues = data.get('issues', [])

    output.append("=" * 70)
    output.append("Barclays OAS Validation Results")
    output.append("=" * 70)
    output.append(f"Title: {info.get('title', 'N/A')}")
    output.append(f"Version: {info.get('version', 'N/A')}")
    output.append(f"Type: {info.get('type', 'N/A')}")
    output.append(f"Timestamp: {info.get('timestamp', 'N/A')}")
    output.append("")

    # Group issues by severity
    severity_names = {0: 'CRITICAL', 1: 'HIGH', 2: 'MEDIUM', 3: 'LOW'}
    issues_by_severity = {}
    for issue in issues:
        sev = issue.get('severity', 1)
        if sev not in issues_by_severity:
            issues_by_severity[sev] = []
        issues_by_severity[sev].append(issue)

    output.append(f"Total Issues: {len(issues)}")
    for sev in sorted(issues_by_severity.keys()):
        count = len(issues_by_severity[sev])
        name = severity_names.get(sev, f'SEVERITY-{sev}')
        output.append(f"  {name}: {count}")

    output.append("")
    output.append("-" * 70)

    # Show issues grouped by severity
    for sev in sorted(issues_by_severity.keys()):
        name = severity_names.get(sev, f'SEVERITY-{sev}')
        output.append(f"\n{name} Issues:")
        output.append("-" * 40)
        for issue in issues_by_severity[sev]:
            output.append(f"  [{issue.get('code')}] {issue.get('message')}")
            output.append(f"    Source: {issue.get('source')}")
            path = issue.get('path', [])
            if path:
                output.append(f"    Path: {'/'.join(str(p) for p in path)}")
            output.append("")

    return '\n'.join(output)


def main():
    parser = argparse.ArgumentParser(
        description='Barclays OAS Validator - Validates OpenAPI specs using HTTP endpoint'
    )
    parser.add_argument('spec', help='Path to OpenAPI specification file')
    parser.add_argument('--all-files', action='store_true',
                        help='Validate all YAML/JSON files in the OAS directory')
    parser.add_argument('--format', choices=['json', 'text'], default='text',
                        help='Output format (default: text)')
    parser.add_argument('-o', '--output', help='Output file path')
    parser.add_argument('--type', choices=['internal', 'external', 'auto'], default='auto',
                        help='API type (default: auto-detect)')

    args = parser.parse_args()

    # Validate spec file exists
    if not os.path.exists(args.spec):
        print(f"ERROR: File not found: {args.spec}", file=sys.stderr)
        sys.exit(1)

    # Detect API type
    api_type = args.type
    if api_type == 'auto':
        api_type = detect_api_type(args.spec)
    print(f"API type: {api_type.upper()}", file=sys.stderr)

    # Show what we're validating
    if args.all_files:
        print("Validating all OAS files in directory...", file=sys.stderr)
    else:
        print(f"Validating: {args.spec}", file=sys.stderr)

    # Call validator
    result = validate_oas(args.spec, args.all_files)

    # Format output
    output = format_output(result, args.format)

    # Write output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Results written to: {args.output}", file=sys.stderr)
    else:
        print(output)

    # Exit with error code if there are critical issues
    if 'error' in result and result['error']:
        sys.exit(1)

    issues = result.get('data', {}).get('issues', [])
    critical_count = sum(1 for i in issues if i.get('severity') == 0)
    if critical_count > 0:
        print(f"\n⚠️  {critical_count} critical issues found", file=sys.stderr)
        sys.exit(1)

    print("\n✅ Validation complete", file=sys.stderr)
    sys.exit(0)


if __name__ == '__main__':
    main()
