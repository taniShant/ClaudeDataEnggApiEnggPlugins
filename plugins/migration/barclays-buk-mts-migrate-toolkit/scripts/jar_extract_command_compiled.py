#!/usr/bin/env python3
"""S.7c — Extract Command class gateway calls from compiled EBS JAR.

Usage:
    python jar_extract_command_compiled.py <compiled-ebs-jar>

Uses Tier 1 (constant pool) extraction to find Command classes with their
DataGroup enum refs and gateway method calls.

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
    print("Usage: python jar_extract_command_compiled.py <compiled-ebs-jar>", file=sys.stderr)
    sys.exit(1)

jar = sys.argv[1]
results = extract_from_jar(jar, class_filter='Command')

for r in results:
    print(f"COMMAND: {r['class']}")
    print(f"DATAGROUPS: {r['datagroup_refs']}")
    print(f"GATEWAY_CALLS: {r['gateway_calls']}")
