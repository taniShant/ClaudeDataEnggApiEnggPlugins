#!/usr/bin/env python3
"""
MTS JAR Extraction Orchestrator — runs all 3 tiers and merges results.

Usage:
    python extract_jar.py <jar_path> [--filter <class_substring>] [--json]

Tier 1: Constant pool parser   (always runs — no external deps)
Tier 2: ROP/RIP file parser    (runs if riprop/ directory is present in JAR)
Tier 3: javap disassembly      (runs if javap is available on the system)

Results are merged per-class with confidence tags assigned per the rules in
reference/compiled_jar_extraction.md:

  verified-from-rop-rip    — ROP/RIP files were authoritative (Tier 2)
  verified-from-bytecode   — Tier 1 + Tier 3 javap confirmation
  partial-from-bytecode    — Tier 1 only (DataGroup conditionals unavailable)
  inferred-from-convention — No compiled JAR data (not produced by this script)

Output schema (JSON):
  {
    "jar": str,
    "tiers_used": list[str],
    "classes": [
      {
        "class": str,
        "super_class": str | null,
        "type": "transaction" | "command",
        "wmid_params": [{"field": str, "type"?: str, "length"?: int, "confidence": str}],
        "wmod_fields": [{"field": str, "type"?: str, "length"?: int, "confidence": str}],
        "datagroup_refs": list[str],
        "gateway_calls": list[str],
        "program_code": str | null,
        "version_code": str | null,
        "dg_wmid_mappings": [{"datagroup": str, "wmid": str}],
        "code_candidates": list[str],
        "overall_confidence": str,
      }
    ]
  }
"""

import json, argparse, sys
from pathlib import Path

# Sibling scripts
_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))

import jar_constant_pool as tier1
import jar_rop_rip       as tier2
import jar_javap         as tier3


def _merge(jar_path, class_filter=None):
    """Run all three tiers and merge their output into unified per-class records."""
    tiers_used = ['tier1-constant-pool']

    # --- Tier 1 ---
    t1_results = tier1.extract_from_jar(jar_path, class_filter=class_filter)
    t1_by_cls  = {r['class']: r for r in t1_results}

    # --- Tier 2 ---
    t2_data    = tier2.extract_rop_rip(jar_path)
    t2_wmid    = {e['field']: e for e in t2_data.get('wmid_params', [])}
    t2_wmod    = {e['field']: e for e in t2_data.get('wmod_fields', [])}
    has_tier2  = t2_data['confidence'] == 'verified-from-rop-rip'
    if has_tier2:
        tiers_used.append('tier2-rop-rip')

    # --- Tier 3 ---
    javap_path = tier3.find_javap()
    t3_results = []
    if javap_path:
        tiers_used.append('tier3-javap')
        t3_results = tier3.extract_from_jar(jar_path, javap_path, class_filter=class_filter)
    t3_by_cls = {r['class']: r for r in t3_results}

    # --- Merge ---
    merged = []
    for cls, t1 in t1_by_cls.items():
        t3  = t3_by_cls.get(cls, {})
        rec = {
            'class':            cls,
            'super_class':      t1['super_class'],
            'type':             t1['type'],
            'datagroup_refs':   t1['datagroup_refs'],
            'gateway_calls':    t1['gateway_calls'],
            'code_candidates':  t1['code_candidates'],
            # Tier 3 enrichment
            'program_code':     t3.get('program_code'),
            'version_code':     t3.get('version_code'),
            'dg_wmid_mappings': t3.get('dg_wmid_mappings', []),
        }

        # Build WMID list with per-item confidence
        wmid_enriched = []
        for field in t1['wmid_params']:
            entry = {'field': field}
            if field in t2_wmid:
                entry.update({'type': t2_wmid[field]['type'], 'length': t2_wmid[field]['length']})
                entry['confidence'] = 'verified-from-rop-rip'
            elif javap_path:
                entry['confidence'] = 'verified-from-bytecode'
            else:
                entry['confidence'] = 'partial-from-bytecode'
            wmid_enriched.append(entry)

        # Add ROP/RIP entries not found in Tier 1 (different Transaction class in same JAR)
        for field, details in t2_wmid.items():
            if not any(e['field'] == field for e in wmid_enriched):
                wmid_enriched.append({
                    'field':      field,
                    'type':       details['type'],
                    'length':     details['length'],
                    'confidence': 'verified-from-rop-rip',
                })

        # Build WMOD list with per-item confidence
        wmod_enriched = []
        for field in t1['wmod_fields']:
            entry = {'field': field}
            if field in t2_wmod:
                entry.update({'type': t2_wmod[field]['type'], 'length': t2_wmod[field]['length']})
                entry['confidence'] = 'verified-from-rop-rip'
            elif javap_path:
                entry['confidence'] = 'verified-from-bytecode'
            else:
                entry['confidence'] = 'partial-from-bytecode'
            wmod_enriched.append(entry)

        for field, details in t2_wmod.items():
            if not any(e['field'] == field for e in wmod_enriched):
                wmod_enriched.append({
                    'field':      field,
                    'type':       details['type'],
                    'length':     details['length'],
                    'confidence': 'verified-from-rop-rip',
                })

        rec['wmid_params']  = wmid_enriched
        rec['wmod_fields']  = wmod_enriched

        # Overall confidence = best confidence achieved across all items
        all_conf = [e['confidence'] for e in wmid_enriched + wmod_enriched]
        if 'verified-from-rop-rip'  in all_conf:
            rec['overall_confidence'] = 'verified-from-rop-rip'
        elif 'verified-from-bytecode' in all_conf:
            rec['overall_confidence'] = 'verified-from-bytecode'
        else:
            rec['overall_confidence'] = 'partial-from-bytecode'

        merged.append(rec)

    return {'jar': jar_path, 'tiers_used': tiers_used, 'classes': merged}


def _print_text(data):
    print(f"JAR:        {data['jar']}")
    print(f"Tiers used: {', '.join(data['tiers_used'])}")
    print(f"Classes:    {len(data['classes'])}")

    for cls in data['classes']:
        if cls['type'] not in ('transaction', 'command') and not cls['wmid_params']:
            continue
        print(f"\n  [{cls['type'].upper()}] {cls['class']}")
        if cls.get('program_code'):
            print(f"    program_code = \"{cls['program_code']}\"  version_code = \"{cls.get('version_code', '?')}\"")
        if cls['wmid_params']:
            print(f"    WMID params ({len(cls['wmid_params'])}):")
            for p in cls['wmid_params']:
                extra = f"  {p.get('type',''):<8} width {p.get('length','?')}" if 'type' in p else ''
                print(f"      {p['field']:<40}{extra}  [{p['confidence']}]")
        if cls['wmod_fields']:
            print(f"    WMOD fields ({len(cls['wmod_fields'])}):")
            for f in cls['wmod_fields'][:10]:
                extra = f"  {f.get('type',''):<8} width {f.get('length','?')}" if 'type' in f else ''
                print(f"      {f['field']:<40}{extra}  [{f['confidence']}]")
            if len(cls['wmod_fields']) > 10:
                print(f"      ... and {len(cls['wmod_fields']) - 10} more")
        if cls['dg_wmid_mappings']:
            print(f"    DataGroup → WMID ({len(cls['dg_wmid_mappings'])}):")
            for m in cls['dg_wmid_mappings']:
                print(f"      {m['datagroup']:<40} → {m['wmid']}")
        print(f"    Overall confidence: {cls['overall_confidence']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('jar_path', help='Path to the compiled EBS/EGS JAR file')
    parser.add_argument('--filter', metavar='SUBSTRING', help='Only process .class files whose path contains SUBSTRING')
    parser.add_argument('--json',   action='store_true', help='Output JSON instead of human-readable text')
    args = parser.parse_args()

    data = _merge(args.jar_path, class_filter=args.filter)

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        _print_text(data)


if __name__ == '__main__':
    main()
