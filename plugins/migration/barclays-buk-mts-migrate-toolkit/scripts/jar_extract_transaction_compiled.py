#!/usr/bin/env python3
"""S.7a — Extract Transaction class identity from compiled EGS JAR.

Usage:
    python jar_extract_transaction_compiled.py <compiled-egs-jar>

Uses Tier 1 (constant pool) extraction to find Transaction classes and their
WMID/WMOD strings, DataGroup refs, gateway calls, and code candidates.

Delegates to jar_constant_pool.py's extract_from_jar() — same directory.
"""
import sys, os

# Import from skills script directory (sibling to scripts/)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_skills_scripts = os.path.join(_script_dir, '..', 'skills', 'mts-reference', 'scripts')
sys.path.insert(0, _skills_scripts)
sys.path.insert(0, _script_dir)
from jar_constant_pool import extract_from_jar

if len(sys.argv) < 2:
    print("Usage: python jar_extract_transaction_compiled.py <compiled-egs-jar>", file=sys.stderr)
    sys.exit(1)

jar = sys.argv[1]
results = extract_from_jar(jar, class_filter='Transaction')

for r in results:
    print(f"CLASS: {r['class']}  SUPER: {r['super_class']}")
    print(f"WMID: {r['wmid_params']}")
    print(f"WMOD: {r['wmod_fields']}")
    if r['datagroup_refs']:
        print(f"DATAGROUPS: {r['datagroup_refs']}")
    if r['gateway_calls']:
        print(f"GATEWAY_CALLS: {r['gateway_calls']}")
    if r['code_candidates']:
        print(f"CODE_CANDIDATES: {r['code_candidates']}")
    print(f"CONFIDENCE: {r['confidence']}")
