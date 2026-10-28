#!/usr/bin/env python3
"""S.7d — Extract WMOD fields from ROP/RIP files in compiled EGS JAR.

Usage:
    python jar_extract_wmod_rip.py <compiled-egs-jar>

Uses Tier 2 (ROP/RIP) extraction to parse riprop/*.ROP and riprop/*.RIP files
for authoritative WMID parameter and WMOD field lists with types and lengths.

Delegates to jar_rop_rip.py's extract_rop_rip() — located in skills directory.
Falls back to inline implementation if import fails (standalone execution).
"""
import sys, os

# Try importing from sibling skills script directory
_script_dir = os.path.dirname(os.path.abspath(__file__))
_skills_scripts = os.path.join(_script_dir, '..', 'skills', 'mts-reference', 'scripts')
sys.path.insert(0, _skills_scripts)
sys.path.insert(0, _script_dir)

try:
    from jar_rop_rip import extract_rop_rip
except ImportError:
    # Inline fallback — same implementation as jar_rop_rip.py
    import zipfile, re

    _FIELD_RE = re.compile(
        r'^\s*\d+\s+\d+\s+\d*\s*(WMID-[\w-]+|WMOD-[\w-]+)\s+(pic\w*)\s+width\s+(\d+)',
        re.IGNORECASE,
    )

    def extract_rop_rip(jar_path):
        result = {'rip_files': [], 'rop_files': [], 'wmid_params': [], 'wmod_fields': [], 'confidence': 'not-available'}
        with zipfile.ZipFile(jar_path) as zf:
            for name in [n for n in zf.namelist() if n.startswith('riprop/')]:
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
                            result['wmid_params'].append({'field': m.group(1).upper(), 'type': m.group(2), 'length': int(m.group(3))})
                elif upper.endswith('.ROP'):
                    result['rop_files'].append(name)
                    for line in content.splitlines():
                        m = _FIELD_RE.match(line)
                        if m and m.group(1).upper().startswith('WMOD-'):
                            result['wmod_fields'].append({'field': m.group(1).upper(), 'type': m.group(2), 'length': int(m.group(3))})
        if result['wmid_params'] or result['wmod_fields']:
            result['confidence'] = 'verified-from-rop-rip'
        return result

if len(sys.argv) < 2:
    print("Usage: python jar_extract_wmod_rip.py <compiled-egs-jar>", file=sys.stderr)
    sys.exit(1)

jar = sys.argv[1]
result = extract_rop_rip(jar)
print(f"RIP files: {result['rip_files']}")
print(f"ROP files: {result['rop_files']}")
print(f"Confidence: {result['confidence']}")
for entry in result['wmid_params']:
    print(f"  WMID: {entry['field']}  {entry['type']}  width {entry['length']}")
for entry in result['wmod_fields']:
    print(f"  WMOD: {entry['field']}  {entry['type']}  width {entry['length']}")
