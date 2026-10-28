# Tier 1: Constant Pool Parser

Reads `.class` bytes directly from a compiled JAR via `zipfile` + `struct`. Extracts class name, superclass, all string constants, method references, and field references. No external dependencies.

### Python Code

```python
"""
Constant Pool Parser — extract strings, class hierarchy, and method refs from .class bytecode.
Usage: called inline from discovery steps. ~80 lines, zero external deps.
"""
import zipfile, struct, sys, re

# Constant pool tag types
CONSTANT_Utf8 = 1
CONSTANT_Integer = 3
CONSTANT_Float = 4
CONSTANT_Long = 5
CONSTANT_Double = 6
CONSTANT_Class = 7
CONSTANT_String = 8
CONSTANT_Fieldref = 9
CONSTANT_Methodref = 10
CONSTANT_InterfaceMethodref = 11
CONSTANT_NameAndType = 12
CONSTANT_MethodHandle = 15
CONSTANT_MethodType = 16
CONSTANT_InvokeDynamic = 18

def parse_constant_pool(class_bytes):
    """Parse a .class file's constant pool.
    Returns (utf8_strings, class_refs, method_refs, field_refs, this_class, super_class).
    - utf8_strings: all UTF-8 string constants
    - class_refs: all referenced class names
    - method_refs: list of (class_name, method_name) tuples
    - field_refs: list of (class_name, field_name) tuples
    - this_class: FQN of this class
    - super_class: FQN of superclass
    """
    if class_bytes[:4] != b'\xca\xfe\xba\xbe':
        return [], [], [], [], None, None
    _minor, _major, cp_count = struct.unpack_from('>HHH', class_bytes, 4)
    offset = 10
    cp = [None]  # index 0 is unused
    i = 1
    while i < cp_count:
        tag = class_bytes[offset]
        offset += 1
        if tag == CONSTANT_Utf8:
            length = struct.unpack_from('>H', class_bytes, offset)[0]
            offset += 2
            cp.append(('utf8', class_bytes[offset:offset+length].decode('utf-8', errors='replace')))
            offset += length
        elif tag == CONSTANT_Integer or tag == CONSTANT_Float:
            cp.append(('num', struct.unpack_from('>I', class_bytes, offset)[0]))
            offset += 4
        elif tag == CONSTANT_Long or tag == CONSTANT_Double:
            cp.append(('wide', None))
            offset += 8
            i += 1
            cp.append(None)  # long/double take two slots
        elif tag == CONSTANT_Class:
            cp.append(('class', struct.unpack_from('>H', class_bytes, offset)[0]))
            offset += 2
        elif tag == CONSTANT_String:
            cp.append(('string', struct.unpack_from('>H', class_bytes, offset)[0]))
            offset += 2
        elif tag in (CONSTANT_Fieldref, CONSTANT_Methodref, CONSTANT_InterfaceMethodref):
            cls_idx, nat_idx = struct.unpack_from('>HH', class_bytes, offset)
            cp.append(('ref', tag, cls_idx, nat_idx))
            offset += 4
        elif tag == CONSTANT_NameAndType:
            name_idx, desc_idx = struct.unpack_from('>HH', class_bytes, offset)
            cp.append(('nat', name_idx, desc_idx))
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
            offset += 2  # best-effort skip
        i += 1

    # access_flags(2) + this_class(2) + super_class(2) immediately after constant pool
    this_class_idx = struct.unpack_from('>H', class_bytes, offset + 2)[0]
    super_class_idx = struct.unpack_from('>H', class_bytes, offset + 4)[0]

    def resolve_utf8(idx):
        if idx and idx < len(cp) and cp[idx] and cp[idx][0] == 'utf8':
            return cp[idx][1]
        return None

    def resolve_class(idx):
        if idx and idx < len(cp) and cp[idx] and cp[idx][0] == 'class':
            return resolve_utf8(cp[idx][1])
        return None

    utf8_strings = [e[1] for e in cp if e and e[0] == 'utf8']
    class_refs = [resolve_class(j) for j in range(len(cp)) if cp[j] and cp[j][0] == 'class']
    class_refs = [c for c in class_refs if c]

    method_refs = []
    field_refs = []
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

    this_class = resolve_class(this_class_idx)
    super_class = resolve_class(super_class_idx)

    return utf8_strings, class_refs, method_refs, field_refs, this_class, super_class
```

### Tier 1 Extraction Patterns

Use the parser above to extract from compiled `.class` files inside JARs:

**Transaction class identification:**
```python
# Find Transaction classes by superclass chain
for name in zf.namelist():
    if name.endswith('.class') and 'Transaction' in name:
        data = zf.read(name)
        strings, classes, methods, fields, this_cls, super_cls = parse_constant_pool(data)
        if super_cls and 'Transaction' in super_cls:
            print(f'Transaction: {this_cls} extends {super_cls}')
            wmids = [s for s in strings if 'WMID-' in s and '-PRM' in s]
            wmods = [s for s in strings if 'WMOD-' in s]
            codes = [s for s in strings if len(s) <= 3 and s.isalpha() and s.isupper()]
            print(f'  WMID params: {wmids}')
            print(f'  WMOD fields ({len(wmods)}): {wmods[:10]}...')
            print(f'  Code candidates: {codes}')
```

**DataGroup enum references (from field_refs):**
```python
# Identify DataGroup references from field refs
dg_refs = [(cls, name) for cls, name in fields if 'DataGroup' in cls]
for cls, name in dg_refs:
    print(f'  DataGroup ref: {cls}.{name}')
```

**Gateway method references:**
```python
# Identify gateway calls from method references
for cls_name, meth_name in methods:
    if cls_name and 'Gateway' in cls_name:
        print(f'  Gateway call: {cls_name}.{meth_name}()')
```

**Command class identification:**
```python
# Find Command classes
for name in zf.namelist():
    if name.endswith('.class') and 'Command' in name:
        data = zf.read(name)
        strings, classes, methods, fields, this_cls, super_cls = parse_constant_pool(data)
        if super_cls and 'Command' in super_cls:
            print(f'Command: {this_cls} extends {super_cls}')
            dg_refs = [(c, n) for c, n in fields if 'DataGroup' in c]
            gw_refs = [(c, n) for c, n in methods if 'Gateway' in c]
            print(f'  DataGroups: {dg_refs}')
            print(f'  Gateway calls: {gw_refs}')
```

### What Tier 1 Extracts

| Data Item | How | Exact? |
|-----------|-----|--------|
| Class hierarchy | `this_class` / `super_class` from class header | Exact |
| WMID parameters | All `WMID-*-PRM` strings from constant pool | Exact (all strings present in class) |
| WMOD fields | All `WMOD-*` strings from constant pool | Exact (all strings present in class) |
| DataGroup enum refs | `CustomerDataGroup.<ENUM>` field refs | Exact |
| Gateway method refs | `gateway.findByPrimaryKey` method refs | Exact |
| Program/version code | Short string heuristic (1-3 char uppercase strings) | Heuristic — use Tier 3 for exact values |

### Program/Version Code Heuristic

From the constant pool string list, identify `getProgramCode()` / `getVersionCode()` candidates:
- Filter strings of length 1-3 that match `[A-Z][A-Z0-9]*`
- Exclude known non-code strings: `UTF`, `PRM`, `CNT`, `TMR`, etc.
- Cross-reference against known CICS program code patterns from the WMID-TDL Quick Reference

This is a heuristic — Tier 3 (`javap`) provides the definitive answer.
