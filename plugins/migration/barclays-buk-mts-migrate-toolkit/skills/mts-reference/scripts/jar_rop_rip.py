#!/usr/bin/env python3
"""
Tier 2: ROP/RIP File Parser for EGS compiled JARs.

Usage:
    python jar_rop_rip.py <jar_path> [--json]

EGS compiled JARs embed structured diagnostic report files at riprop/*.ROP and
riprop/*.RIP that define the exact request/response field contracts:

  RIP (Request Input Parse)  — WMID request parameters with type and byte length
  ROP (Response Output Parse) — WMOD response fields with type and byte length

These files are authoritative — they come from the CICS program's COPYBOOKS and
are more reliable than constant pool extraction when available.

Confidence tag produced: "verified-from-rop-rip"
No external dependencies — stdlib only.
"""

import zipfile, re, json, argparse, sys
from pathlib import Path

# Matches diagnostic report field lines such as:
#    57   42              WMID-CUST-PRM picX width 1.
#    20    9              WMOD-HDR-RTR-ERR-CDE picX width 6.
_FIELD_RE = re.compile(
    r'^\s*\d+\s+\d+\s+\d*\s*(WMID-[\w-]+|WMOD-[\w-]+)\s+(pic\w*)\s+width\s+(\d+)',
    re.IGNORECASE,
)


def extract_rop_rip(jar_path):
    """Extract and parse ROP/RIP files from a compiled EGS JAR.

    Returns:
      {
        "rip_files":   list[str],                          — filenames of RIP files found
        "rop_files":   list[str],                          — filenames of ROP files found
        "wmid_params": list[{"field": str, "type": str, "length": int}],
        "wmod_fields": list[{"field": str, "type": str, "length": int}],
        "confidence":  "verified-from-rop-rip" | "not-available",
      }
    """
    result = {
        'rip_files':   [],
        'rop_files':   [],
        'wmid_params': [],
        'wmod_fields': [],
        'confidence':  'not-available',
    }

    with zipfile.ZipFile(jar_path) as zf:
        riprop_entries = [n for n in zf.namelist() if n.startswith('riprop/')]
        if not riprop_entries:
            return result

        for name in riprop_entries:
            upper = name.upper()
            try:
                content = zf.read(name).decode('utf-8', errors='replace')
            except Exception:
                continue

            if upper.endswith('.RIP'):
                result['rip_files'].append(name)
                for line in content.splitlines():
                    m = _FIELD_RE.match(line)
                    if m and m.group(1).upper().startswith('WMID-'):
                        result['wmid_params'].append({
                            'field':  m.group(1).upper(),
                            'type':   m.group(2),
                            'length': int(m.group(3)),
                        })

            elif upper.endswith('.ROP'):
                result['rop_files'].append(name)
                for line in content.splitlines():
                    m = _FIELD_RE.match(line)
                    if m and m.group(1).upper().startswith('WMOD-'):
                        result['wmod_fields'].append({
                            'field':  m.group(1).upper(),
                            'type':   m.group(2),
                            'length': int(m.group(3)),
                        })

    if result['wmid_params'] or result['wmod_fields']:
        result['confidence'] = 'verified-from-rop-rip'

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for entry in result['wmid_params']:
        if entry['field'] not in seen:
            seen.add(entry['field'])
            deduped.append(entry)
    result['wmid_params'] = deduped

    seen = set()
    deduped = []
    for entry in result['wmod_fields']:
        if entry['field'] not in seen:
            seen.add(entry['field'])
            deduped.append(entry)
    result['wmod_fields'] = deduped

    return result


def _print_text(data, jar_path):
    print(f"JAR: {jar_path}")
    if data['confidence'] == 'not-available':
        print("No riprop/ directory found — ROP/RIP extraction not available for this JAR.")
        return

    print(f"Confidence: {data['confidence']}")
    print(f"\nRIP files found ({len(data['rip_files'])}):")
    for f in data['rip_files']:
        print(f"  {f}")
    print(f"\nROP files found ({len(data['rop_files'])}):")
    for f in data['rop_files']:
        print(f"  {f}")

    if data['wmid_params']:
        print(f"\nWMID parameters ({len(data['wmid_params'])}):")
        for p in data['wmid_params']:
            print(f"  {p['field']:<40} {p['type']:<8} width {p['length']}")
    else:
        print("\nWMID parameters: none extracted")

    if data['wmod_fields']:
        print(f"\nWMOD fields ({len(data['wmod_fields'])}):")
        for f in data['wmod_fields']:
            print(f"  {f['field']:<40} {f['type']:<8} width {f['length']}")
    else:
        print("\nWMOD fields: none extracted")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('jar_path', help='Path to the compiled EGS JAR file')
    parser.add_argument('--json', action='store_true', help='Output JSON instead of human-readable text')
    args = parser.parse_args()

    data = extract_rop_rip(args.jar_path)

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        _print_text(data, args.jar_path)


if __name__ == '__main__':
    main()
