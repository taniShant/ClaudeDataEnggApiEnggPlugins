#!/usr/bin/env python3
"""
Tier 1: Constant Pool Parser for EBS/EGS compiled JARs.

Usage:
    python jar_constant_pool.py <jar_path> [--filter <class_substring>] [--json]

Extracts from compiled .class files inside a JAR (no external dependencies):
  - Transaction class hierarchy (this_class / super_class)
  - WMID request parameters  (WMID-*-PRM strings from constant pool)
  - WMOD response fields      (WMOD-* strings from constant pool)
  - DataGroup enum references (CustomerDataGroup.<ENUM> field refs)
  - Gateway method references (gateway.findByPrimaryKey, etc.)
  - Program/version code candidates (heuristic — use jar_javap.py for exact values)

Confidence tag produced: "verified-from-bytecode" when WMID list is complete,
"partial-from-bytecode" when DataGroup conditional attribution is unavailable.
"""

import zipfile, struct, sys, re, json, argparse

# ---------------------------------------------------------------------------
# Constant pool tag constants
# ---------------------------------------------------------------------------
CONSTANT_Utf8               = 1
CONSTANT_Integer            = 3
CONSTANT_Float              = 4
CONSTANT_Long               = 5
CONSTANT_Double             = 6
CONSTANT_Class              = 7
CONSTANT_String             = 8
CONSTANT_Fieldref           = 9
CONSTANT_Methodref          = 10
CONSTANT_InterfaceMethodref = 11
CONSTANT_NameAndType        = 12
CONSTANT_MethodHandle       = 15
CONSTANT_MethodType         = 16
CONSTANT_InvokeDynamic      = 18

# Short uppercase strings that are NOT program/version codes
_CODE_EXCLUSIONS = {
    'UTF', 'PRM', 'CNT', 'TMR', 'GRP', 'REF', 'ERR', 'CDE', 'IND',
    'TYP', 'LEN', 'KEY', 'NUM', 'STR', 'DAT', 'FLG', 'HDR', 'MSG',
    'RTR', 'STS', 'RSP', 'REQ', 'ACT', 'OBJ', 'COD', 'NME', 'AMT',
}


def parse_constant_pool(class_bytes):
    """Parse a .class file's constant pool.

    Returns (utf8_strings, class_refs, method_refs, field_refs, this_class, super_class).
      utf8_strings : list[str]  — all UTF-8 string constants
      class_refs   : list[str]  — all referenced class names
      method_refs  : list[tuple[str, str]]  — (class_name, method_name)
      field_refs   : list[tuple[str, str]]  — (class_name, field_name)
      this_class   : str | None — FQN of this class
      super_class  : str | None — FQN of superclass
    """
    if len(class_bytes) < 10 or class_bytes[:4] != b'\xca\xfe\xba\xbe':
        return [], [], [], [], None, None

    _minor, _major, cp_count = struct.unpack_from('>HHH', class_bytes, 4)
    offset = 10
    cp = [None]   # index 0 unused per JVM spec

    i = 1
    while i < cp_count:
        tag = class_bytes[offset]
        offset += 1
        if tag == CONSTANT_Utf8:
            length = struct.unpack_from('>H', class_bytes, offset)[0]
            offset += 2
            try:
                text = class_bytes[offset:offset + length].decode('utf-8', errors='replace')
            except Exception:
                text = ''
            cp.append(('utf8', text))
            offset += length
        elif tag in (CONSTANT_Integer, CONSTANT_Float):
            cp.append(('num', None))
            offset += 4
        elif tag in (CONSTANT_Long, CONSTANT_Double):
            cp.append(('wide', None))
            offset += 8
            i += 1
            cp.append(None)   # long/double occupy two slots
        elif tag == CONSTANT_Class:
            idx = struct.unpack_from('>H', class_bytes, offset)[0]
            cp.append(('class', idx))
            offset += 2
        elif tag == CONSTANT_String:
            idx = struct.unpack_from('>H', class_bytes, offset)[0]
            cp.append(('string', idx))
            offset += 2
        elif tag in (CONSTANT_Fieldref, CONSTANT_Methodref, CONSTANT_InterfaceMethodref):
            cls_idx, nat_idx = struct.unpack_from('>HH', class_bytes, offset)
            cp.append(('ref', tag, cls_idx, nat_idx))
            offset += 4
        elif tag == CONSTANT_NameAndType:
            name_idx, _desc_idx = struct.unpack_from('>HH', class_bytes, offset)
            cp.append(('nat', name_idx))
            offset += 4
        elif tag == CONSTANT_MethodHandle:
            cp.append(('mh', None))
            offset += 3
        elif tag == CONSTANT_MethodType:
            cp.append(('mt', None))
            offset += 2
        elif tag == CONSTANT_InvokeDynamic:
            cp.append(('id', None))
            offset += 4
        else:
            cp.append(('unknown', None))
            offset += 2
        i += 1

    def resolve_utf8(idx):
        if idx and 0 < idx < len(cp) and cp[idx] and cp[idx][0] == 'utf8':
            return cp[idx][1]
        return None

    def resolve_class(idx):
        if idx and 0 < idx < len(cp) and cp[idx] and cp[idx][0] == 'class':
            return resolve_utf8(cp[idx][1])
        return None

    # access_flags(2) + this_class(2) + super_class(2) immediately after cp
    this_class_idx  = struct.unpack_from('>H', class_bytes, offset + 2)[0]
    super_class_idx = struct.unpack_from('>H', class_bytes, offset + 4)[0]

    utf8_strings = [e[1] for e in cp if e and e[0] == 'utf8']
    class_refs   = [c for c in (resolve_class(j) for j in range(len(cp))
                                if cp[j] and cp[j][0] == 'class') if c]

    method_refs, field_refs = [], []
    for e in cp:
        if not e or e[0] != 'ref':
            continue
        cls_name = resolve_class(e[2])
        nat = cp[e[3]] if e[3] < len(cp) else None
        if nat and nat[0] == 'nat':
            ref_name = resolve_utf8(nat[1])
            if cls_name and ref_name:
                if e[1] in (CONSTANT_Methodref, CONSTANT_InterfaceMethodref):
                    method_refs.append((cls_name, ref_name))
                elif e[1] == CONSTANT_Fieldref:
                    field_refs.append((cls_name, ref_name))

    return (utf8_strings, class_refs, method_refs, field_refs,
            resolve_class(this_class_idx), resolve_class(super_class_idx))


def _code_candidates(strings):
    """Heuristic: short uppercase strings that look like program/version codes."""
    return [
        s for s in strings
        if 1 <= len(s) <= 3
        and re.fullmatch(r'[A-Z][A-Z0-9]*', s)
        and s not in _CODE_EXCLUSIONS
    ]


def extract_from_jar(jar_path, class_filter=None):
    """Extract MTS-relevant data from all matching .class files in a compiled JAR.

    Returns a list of dicts, one per matching class:
      {
        "class": str,
        "super_class": str,
        "type": "transaction" | "command" | "other",
        "wmid_params": list[str],
        "wmod_fields": list[str],
        "datagroup_refs": list[str],
        "gateway_calls": list[str],
        "code_candidates": list[str],
        "confidence": str,
      }
    """
    results = []
    with zipfile.ZipFile(jar_path) as zf:
        for name in zf.namelist():
            if not name.endswith('.class'):
                continue
            if class_filter and class_filter.lower() not in name.lower():
                continue
            try:
                data = zf.read(name)
            except Exception:
                continue

            strings, classes, methods, fields, this_cls, super_cls = parse_constant_pool(data)
            if not this_cls:
                continue

            # Classify by superclass / name patterns
            is_transaction = (super_cls and 'Transaction' in super_cls) or 'Transaction' in (this_cls or '')
            is_command      = (super_cls and 'Command'     in super_cls) or 'Command'     in (this_cls or '')
            cls_type = 'transaction' if is_transaction else ('command' if is_command else 'other')

            wmid_params    = sorted({s for s in strings if 'WMID-' in s and '-PRM' in s})
            wmod_fields    = sorted({s for s in strings if s.startswith('WMOD-')})
            dg_refs        = sorted({name_ for _, name_ in fields if 'DataGroup' in _})
            gw_calls       = sorted({f"{c}.{m}()" for c, m in methods if 'Gateway' in c})
            code_cands     = _code_candidates(strings)

            # Assign confidence at this tier
            confidence = 'partial-from-bytecode'  # DataGroup conditional attribution not available without javap

            results.append({
                'class':          this_cls,
                'super_class':    super_cls,
                'type':           cls_type,
                'wmid_params':    wmid_params,
                'wmod_fields':    wmod_fields,
                'datagroup_refs': dg_refs,
                'gateway_calls':  gw_calls,
                'code_candidates': code_cands,
                'confidence':     confidence,
            })
    return results


def _print_text(results):
    for r in results:
        if r['type'] not in ('transaction', 'command') and not r['wmid_params']:
            continue
        print(f"\n[{r['type'].upper()}] {r['class']}")
        if r['super_class']:
            print(f"  extends: {r['super_class']}")
        if r['wmid_params']:
            print(f"  WMID params ({len(r['wmid_params'])}): {', '.join(r['wmid_params'])}")
        if r['wmod_fields']:
            print(f"  WMOD fields ({len(r['wmod_fields'])}): {', '.join(r['wmod_fields'][:10])}" +
                  (' ...' if len(r['wmod_fields']) > 10 else ''))
        if r['datagroup_refs']:
            print(f"  DataGroup refs: {', '.join(r['datagroup_refs'])}")
        if r['gateway_calls']:
            print(f"  Gateway calls: {', '.join(r['gateway_calls'])}")
        if r['code_candidates']:
            print(f"  Code candidates (heuristic): {', '.join(r['code_candidates'])}")
        print(f"  Confidence: {r['confidence']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('jar_path', help='Path to the compiled EBS/EGS JAR file')
    parser.add_argument('--filter', metavar='SUBSTRING', help='Only process .class files whose path contains SUBSTRING')
    parser.add_argument('--json', action='store_true', help='Output JSON instead of human-readable text')
    args = parser.parse_args()

    results = extract_from_jar(args.jar_path, class_filter=args.filter)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        if not results:
            print('No matching classes found.')
        else:
            _print_text(results)
        print(f'\nTotal classes parsed: {len(results)}')


if __name__ == '__main__':
    main()
