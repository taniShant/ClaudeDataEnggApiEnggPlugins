# Tier 2: ROP/RIP File Parser

EGS compiled JARs contain structured diagnostic report files at `riprop/*.ROP` and `riprop/*.RIP` that define WMOD response fields and WMID request parameters respectively.

**Key distinction:**
- **ROP** (Response Output Parse) = WMOD response fields
- **RIP** (Request Input Parse) = WMID request parameters

### File Format

ROP/RIP files are diagnostic reports of control tables with a structured parse-tree format. Field definitions appear as indented lines:
```
   57   42              WMID-CUST-PRM picX width 1.
   20    9              WMOD-HDR-RTR-ERR-CDE picX width 6.
```

### Python Code

```python
"""Extract ROP/RIP files from compiled EGS JARs — parse diagnostic report format."""
import zipfile, re

def extract_rop_rip(jar_path):
    """Extract and parse ROP/RIP files from a compiled EGS JAR.
    Returns dict with:
      'rop_entries': list of {field, type, length} dicts (WMOD response fields from ROP files)
      'rip_entries': list of {field, type, length} dicts (WMID request params from RIP files)
      'rop_files': list of ROP filenames found
      'rip_files': list of RIP filenames found
    """
    result = {'rop_entries': [], 'rip_entries': [], 'rop_files': [], 'rip_files': []}
    # Pattern matches diagnostic report field lines like:
    #    57   42              WMID-CUST-PRM picX width 1.
    #    20    9              WMOD-HDR-RTR-ERR-CDE picX width 6.
    field_pattern = re.compile(
        r'^\s*\d+\s+\d+\s+\d*\s*(WMID-[\w-]+|WMOD-[\w-]+)\s+(pic\w*)\s+width\s+(\d+)'
    )

    with zipfile.ZipFile(jar_path) as zf:
        for name in zf.namelist():
            if not name.startswith('riprop/'):
                continue
            content = zf.read(name).decode('utf-8', errors='replace')

            if name.upper().endswith('.ROP'):
                result['rop_files'].append(name)
                # ROP = Response Output Parse — contains WMOD response fields
                for line in content.splitlines():
                    m = field_pattern.match(line)
                    if m and m.group(1).startswith('WMOD-'):
                        result['rop_entries'].append({
                            'field': m.group(1),
                            'type': m.group(2),
                            'length': int(m.group(3))
                        })

            elif name.upper().endswith('.RIP'):
                result['rip_files'].append(name)
                # RIP = Request Input Parse — contains WMID input parameters
                for line in content.splitlines():
                    m = field_pattern.match(line)
                    if m and m.group(1).startswith('WMID-'):
                        result['rip_entries'].append({
                            'field': m.group(1),
                            'type': m.group(2),
                            'length': int(m.group(3))
                        })
    return result
```

### What Tier 2 Extracts

| Data Item | Source | Definitive? |
|-----------|--------|------------|
| Complete WMID parameter list | `riprop/*.RIP` diagnostic reports | Yes — definitive list with data types |
| WMOD response fields with types | `riprop/*.ROP` diagnostic reports | Yes — definitive with data types and lengths |

### Cross-validation

When both Tier 1 and Tier 2 data are available, cross-validate:
- Every WMID from RIP must appear in Tier 1 constant pool strings (if the class references it)
- Any WMOD field in ROP that doesn't appear in Tier 1 strings may be from a different Transaction class in the same JAR
