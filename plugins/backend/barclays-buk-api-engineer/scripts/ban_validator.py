#!/usr/bin/env python3
"""
Barclays API Network (BAN) OAS Validator

Validates OpenAPI specifications by uploading to the Barclays API Network service.
Authenticates automatically via Kerberos (Windows domain / enrolled Mac) or
Basic auth (set BAN_USERNAME + BAN_PASSWORD env vars on Linux/CI).

Usage:
    python3 ban_validator.py <spec_path> [options]

Options:
    --all-files              Validate all YAML/JSON files in the OAS directory (creates zip)
    --format json|text       Output format (default: text)
    -o, --output             Output file path
    --type auto|internal|external  API type (default: auto-detect)
    --verify-response-fields       Include response field verification (for gateway APIs)
    --is-daf                       Flag if DAF specification included
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    print("ERROR: requests library required. Install with: pip3 install requests", file=sys.stderr)
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml library required. Install with: pip3 install pyyaml", file=sys.stderr)
    sys.exit(1)

# BAN service URLs — no credentials in source
BAM_AUTH_URL = "https://bam-auth.client.barclayscorp.com/authn/authenticate/sso/api?appName=BarclaysAPINetwork"
BAN_BASE_URL = "https://barclays-api-network-26915.pr2.apaas4.barclays.intranet"
BAN_UPLOAD_URL = f"{BAN_BASE_URL}/gateway/apispecverify?urlSuffix=specifications/verification"
BAN_SESSION_URL = f"{BAN_BASE_URL}/"

MAX_RETRIES = 3
RETRY_DELAY = 2

# Proxy bypass required for Barclays internal services
_NO_PROXY = "localhost,127.0.0.1,.elb.amazonaws.com,.barclays.intranet,.aws.intranet,.barclayscorp.com"
_CURL_ENV = {**os.environ, "NO_PROXY": _NO_PROXY, "no_proxy": _NO_PROXY}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _curl_candidates() -> list:
    """
    Return curl executables to try, in priority order.
    On Windows, Git Bash puts /mingw64/bin/curl first in PATH — that build
    lacks SPNEGO/Kerberos support and returns empty stdout for --negotiate.
    Always try the Windows system curl.exe explicitly as a fallback.
    """
    candidates = ['curl']
    if sys.platform == 'win32' or os.environ.get('MSYSTEM'):
        # Running under Windows or Git Bash — add system curl.exe explicitly
        candidates.append(r'C:\Windows\System32\curl.exe')
    return candidates


def get_bam_token() -> Optional[str]:
    """
    Obtain a BAM JWT token. Tries Kerberos (--negotiate) first across all curl
    candidates, then Basic auth via BAN_USERNAME + BAN_PASSWORD env vars.
    Returns the token string or None. Credentials are never logged.
    """
    curl_bins = _curl_candidates()

    # Attempt 0: pre-fetched BAM token passed via env var BAN_BAM_TOKEN
    # Use this when running under Git Bash where curl --negotiate fails in subprocess.
    # Fetch the token in bash first:
    #   export BAN_BAM_TOKEN=$(curl --negotiate -u: -sk \
    #     https://bam-auth.client.barclayscorp.com/authn/authenticate/sso/api?appName=BarclaysAPINetwork \
    #     | python3 -c "import json,sys; print(json.load(sys.stdin)['bamToken'])")
    pre_token = os.environ.get('BAN_BAM_TOKEN', '').strip()
    if pre_token:
        print("Auth: using pre-fetched BAM token from BAN_BAM_TOKEN env var", file=sys.stderr)
        return pre_token

    # Attempt 1: Kerberos (Windows domain SSPI / enrolled Mac with kinit)
    # Try each curl candidate — Git Bash curl lacks SPNEGO so we fall through
    # to C:\Windows\System32\curl.exe which uses Windows SSPI natively.
    for curl_bin in curl_bins:
        try:
            result = subprocess.run(
                [curl_bin, '--negotiate', '-u', ':', '-sk', '--max-time', '15', BAM_AUTH_URL],
                capture_output=True, text=True, timeout=20, env=_CURL_ENV
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                if data.get('code') == 'SUCCESS' and data.get('bamToken'):
                    print(f"Auth: Kerberos succeeded ({curl_bin})", file=sys.stderr)
                    return data['bamToken']
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            pass

    # Attempt 2: Basic auth via env vars (tried with each curl candidate)
    ban_user = os.environ.get('BAN_USERNAME', '').strip()
    ban_pass = os.environ.get('BAN_PASSWORD', '').strip()
    if ban_user and ban_pass:
        for curl_bin in curl_bins:
            try:
                result = subprocess.run(
                    [curl_bin, '-u', f'{ban_user}:{ban_pass}', '-sk', '--max-time', '15', BAM_AUTH_URL],
                    capture_output=True, text=True, timeout=20, env=_CURL_ENV
                )
                if result.returncode == 0 and result.stdout.strip():
                    data = json.loads(result.stdout)
                    if data.get('code') == 'SUCCESS' and data.get('bamToken'):
                        print(f"Auth: Basic auth succeeded ({curl_bin})", file=sys.stderr)
                        return data['bamToken']
                    else:
                        print(f"Auth: Basic auth failed ({curl_bin}) — {data.get('message', 'unknown error')}", file=sys.stderr)
            except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
                pass
    elif ban_user or ban_pass:
        print("Auth: BAN_USERNAME or BAN_PASSWORD is set but the other is missing", file=sys.stderr)

    return None


def get_session(bam_token: str) -> Optional[requests.Session]:
    """
    Exchange BAM token for a requests Session with active cookies.
    Uses session-level proxy bypass to avoid mutating os.environ globally.
    Returns a configured Session or None on failure.
    """
    try:
        session = requests.Session()
        session.proxies = {'no_proxy': _NO_PROXY, 'NO_PROXY': _NO_PROXY}
        resp = session.get(
            f'{BAN_SESSION_URL}?bamToken={bam_token}',
            verify=False, timeout=15
        )
        if resp.status_code == 200 and session.cookies:
            return session
    except requests.exceptions.RequestException:
        pass
    return None


# ---------------------------------------------------------------------------
# ZIP creation
# ---------------------------------------------------------------------------

def create_oas_zip(spec_path: str, all_files: bool = True) -> str:
    """
    Create a zip file containing OAS files for BAN validation.
    openapi.yaml is placed at the root of the zip (required by BAN).
    """
    spec_path = Path(spec_path)
    oas_dir = spec_path.parent
    fd, zip_path = tempfile.mkstemp(suffix='.zip')
    os.close(fd)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        if all_files:
            for ext in ['*.yaml', '*.yml', '*.json']:
                for file_path in oas_dir.rglob(ext):
                    if any(part.startswith('.') or part == 'node_modules' for part in file_path.parts):
                        continue
                    arcname = file_path.relative_to(oas_dir)
                    zf.write(file_path, arcname)
        else:
            zf.write(spec_path, spec_path.name)

    return zip_path


# ---------------------------------------------------------------------------
# Spec metadata
# ---------------------------------------------------------------------------

def read_spec_metadata(spec_path: str) -> Dict:
    """
    Read API metadata from openapi.yaml info block.
    Returns a dict with title, version, risk_classification, technical_owner, business_owner.
    """
    defaults = {
        'title': 'Unknown API',
        'version': '1.0.0',
        'risk_classification': 'LIMITED',
        'technical_owner': '',
        'business_owner': '',
    }
    try:
        with open(spec_path) as f:
            spec = yaml.safe_load(f)
        info = spec.get('info', {})
        defaults['title'] = info.get('title', defaults['title'])
        defaults['version'] = str(info.get('version', defaults['version']))
        # x- extension fields written by design-oas from api-config.yaml
        defaults['risk_classification'] = info.get('x-risk-classification', defaults['risk_classification'])
        defaults['technical_owner'] = info.get('x-technical-owner', defaults['technical_owner'])
        defaults['business_owner'] = info.get('x-business-owner', defaults['business_owner'])
        # fallback: contact block
        contact = info.get('contact', {})
        if not defaults['technical_owner']:
            defaults['technical_owner'] = contact.get('email', '')
        if not defaults['business_owner']:
            defaults['business_owner'] = contact.get('email', '')
    except Exception:
        pass
    return defaults


def detect_api_type(spec_path: str) -> str:
    """Auto-detect API type (internal/external) from spec or doc-api.md."""
    spec_dir = Path(spec_path).parent
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
            except Exception:
                pass
    try:
        with open(spec_path) as f:
            spec = yaml.safe_load(f)
        description = spec.get('info', {}).get('description', '')
        if 'internal' in description.lower():
            return 'internal'
        elif 'external' in description.lower():
            return 'external'
    except Exception:
        pass
    return 'internal'


# ---------------------------------------------------------------------------
# BAN upload
# ---------------------------------------------------------------------------

def verify_oas(
    spec_path: str,
    all_files: bool = True,
    api_type: str = 'internal',
    verify_response_fields: bool = False,
    is_daf: bool = False,
) -> Dict:
    """
    Upload OAS to BAN and return the validation response dict.
    Returns { "error": True, "message": "..." } on auth/connection failure.
    Never logs credentials.
    """
    # Auth
    bam_token = get_bam_token()
    if not bam_token:
        return {
            "error": True,
            "skipped": True,
            "message": (
                "BAN validation skipped — could not authenticate. "
                "On Windows: ensure you are on the Barclays domain. "
                "On Mac/Linux: set BAN_USERNAME and BAN_PASSWORD env vars."
            )
        }

    session = get_session(bam_token)
    if not session:
        return {
            "error": True,
            "skipped": True,
            "message": "BAN validation skipped — could not obtain session after auth."
        }

    # Read metadata
    meta = read_spec_metadata(spec_path)
    spec_type = 'RAML' if any(
        p.suffix == '.raml' for p in Path(spec_path).parent.rglob('*.raml')
    ) else 'OAS'

    data_payload = {
        "apiLongName": meta['title'],
        "apiVersion": meta['version'],
        "specificationType": spec_type,
        "apiType": "Internal" if api_type == 'internal' else "External",
        "verificationType": "ZipFile",
        "verifyResponseFields": verify_response_fields,
        "isDAF": is_daf,
        "apiRiskClassification": meta['risk_classification'],
        "apiOwnerTechnical": meta['technical_owner'],
        "apiOwnerBusiness": meta['business_owner'],
    }

    zip_path = create_oas_zip(spec_path, all_files)

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'X-usercontext': bam_token,
        'x-fapi-interaction-id': str(uuid.uuid4()),
    }

    last_error = None
    try:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                with open(zip_path, 'rb') as zf:
                    import io
                    data_blob = io.BytesIO(json.dumps(data_payload).encode('utf-8'))
                    files = {
                        'specificationZipFile': ('oas.zip', zf, 'application/zip'),
                        'data': ('data', data_blob, 'application/json'),
                    }
                    response = session.post(
                        BAN_UPLOAD_URL,
                        headers=headers,
                        files=files,
                        timeout=60,
                        verify=False,
                    )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code in (401, 403):
                    return {
                        "error": True,
                        "skipped": True,
                        "message": f"BAN validation skipped — HTTP {response.status_code}: session expired or access denied."
                    }
                else:
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                    print(f"Attempt {attempt}/{MAX_RETRIES} failed: {last_error}", file=sys.stderr)

            except requests.exceptions.ConnectionError as e:
                last_error = f"Connection error: {e}"
                print(f"Attempt {attempt}/{MAX_RETRIES} failed: {last_error}", file=sys.stderr)
            except requests.exceptions.Timeout:
                last_error = "Timeout (60s)"
                print(f"Attempt {attempt}/{MAX_RETRIES} failed: {last_error}", file=sys.stderr)
            except requests.exceptions.RequestException as e:
                last_error = f"Request error: {e}"
                print(f"Attempt {attempt}/{MAX_RETRIES} failed: {last_error}", file=sys.stderr)

            if attempt < MAX_RETRIES:
                print(f"Retrying in {RETRY_DELAY}s...", file=sys.stderr)
                time.sleep(RETRY_DELAY)

        return {
            "error": True,
            "skipped": True,
            "message": f"BAN validation skipped — failed after {MAX_RETRIES} attempts. Last error: {last_error}"
        }

    finally:
        try:
            os.unlink(zip_path)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def format_output(result: Dict, format_type: str = 'text') -> str:
    if format_type == 'json':
        return json.dumps(result, indent=2)

    if result.get('error'):
        prefix = "SKIPPED" if result.get('skipped') else "ERROR"
        return f"{prefix}: {result.get('message', 'Unknown error')}"

    output = []
    data = result.get('data', {})
    issues = data.get('issues', [])
    passed = data.get('specificationPassed', False)

    output.append("=" * 70)
    output.append("Barclays API Network (BAN) OAS Validation Results")
    output.append("=" * 70)
    output.append(f"API: {data.get('apiLongName', 'N/A')} v{data.get('apiVersion', 'N/A')}")
    output.append(f"Result: {'PASSED' if passed else 'FAILED'}")
    output.append("")

    severity_names = {'0': 'CRITICAL', '1': 'HIGH', '2': 'MEDIUM', '3': 'LOW'}
    issues_by_severity: Dict[str, list] = {}
    for issue in issues:
        sev = str(issue.get('severity', '1'))
        issues_by_severity.setdefault(sev, []).append(issue)

    output.append(f"Total Issues: {len(issues)}")
    for sev in sorted(issues_by_severity.keys()):
        name = severity_names.get(sev, f'SEVERITY-{sev}')
        output.append(f"  {name}: {len(issues_by_severity[sev])}")

    output.append("")
    output.append("-" * 70)

    for sev in sorted(issues_by_severity.keys()):
        name = severity_names.get(sev, f'SEVERITY-{sev}')
        output.append(f"\n{name} Issues:")
        output.append("-" * 40)
        for issue in issues_by_severity[sev]:
            output.append(f"  [{issue.get('code')}] {issue.get('message', '')}")
            if issue.get('source'):
                rng = issue.get('range', {})
                start = rng.get('start', {})
                loc = f"line {start.get('line', '?')}" if start else ""
                output.append(f"    Source: {issue['source']}" + (f" ({loc})" if loc else ""))
            output.append("")

    return '\n'.join(output)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Barclays API Network (BAN) OAS Validator'
    )
    parser.add_argument('spec', help='Path to OpenAPI specification file')
    parser.add_argument('--all-files', action='store_true',
                        help='Validate all YAML/JSON files in the OAS directory')
    parser.add_argument('--format', choices=['json', 'text'], default='text',
                        help='Output format (default: text)')
    parser.add_argument('-o', '--output', help='Output file path')
    parser.add_argument('--type', choices=['internal', 'external', 'auto'], default='auto',
                        help='API type (default: auto-detect)')
    parser.add_argument('--verify-response-fields', action='store_true',
                        help='Include response field verification (for internal gateway APIs)')
    parser.add_argument('--is-daf', action='store_true',
                        help='Flag if DAF specification is included')

    args = parser.parse_args()

    if not os.path.exists(args.spec):
        print(f"ERROR: File not found: {args.spec}", file=sys.stderr)
        sys.exit(1)

    api_type = args.type
    if api_type == 'auto':
        api_type = detect_api_type(args.spec)
    print(f"API type: {api_type.upper()}", file=sys.stderr)

    if args.all_files:
        print("Validating all OAS files in directory...", file=sys.stderr)
    else:
        print(f"Validating: {args.spec}", file=sys.stderr)

    result = verify_oas(
        args.spec,
        all_files=args.all_files,
        api_type=api_type,
        verify_response_fields=args.verify_response_fields,
        is_daf=args.is_daf,
    )

    output = format_output(result, args.format)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Results written to: {args.output}", file=sys.stderr)
    else:
        print(output)

    # Exit codes: 0=passed, 1=failed/critical issues, 2=auth failure/skipped
    if result.get('error'):
        if result.get('skipped'):
            print(f"\nAUTH-FAILURE: {result.get('message', '')}", file=sys.stderr)
            sys.exit(2)  # Non-zero so skill can detect auth failure
        sys.exit(1)

    issues = result.get('data', {}).get('issues', [])
    critical_count = sum(1 for i in issues if str(i.get('severity')) == '0')
    high_count = sum(1 for i in issues if str(i.get('severity')) == '1')
    passed = result.get('data', {}).get('specificationPassed', True)

    if critical_count > 0:
        print(f"\nWARNING: {critical_count} critical issues found", file=sys.stderr)
        sys.exit(1)

    if not passed or high_count > 0:
        # Spec failed or has HIGH issues — exit 1 so skill can detect and prompt user
        print(f"\nWARNING: {high_count} HIGH issues found", file=sys.stderr)
        sys.exit(1)

    print("\nValidation complete", file=sys.stderr)
    sys.exit(0)


if __name__ == '__main__':
    main()
