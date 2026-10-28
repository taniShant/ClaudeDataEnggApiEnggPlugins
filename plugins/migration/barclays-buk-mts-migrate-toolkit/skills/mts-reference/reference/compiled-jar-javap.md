# Tier 3: javap Bytecode Disassembly

Uses the JDK `javap` tool to extract exact values from compiled bytecode. Only used when `javap` is available on the system.

### `find_javap()` Function

Cross-platform function to locate `javap`:

```python
"""Find javap executable cross-platform."""
import os, platform, glob

def find_javap():
    """Locate javap. Returns path string or 'NOT_AVAILABLE'."""
    plat = platform.system()

    # 1. Check PATH
    for p in os.environ.get('PATH', '').split(os.pathsep):
        candidate = os.path.join(p, 'javap.exe' if plat == 'Windows' else 'javap')
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    # 2. Check JAVA_HOME/bin
    java_home = os.environ.get('JAVA_HOME', '')
    if java_home:
        candidate = os.path.join(java_home, 'bin', 'javap.exe' if plat == 'Windows' else 'javap')
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    # 3. Platform-specific search
    if plat == 'Darwin':
        for d in sorted(glob.glob('/Library/Java/JavaVirtualMachines/*/Contents/Home/bin/javap'), reverse=True):
            if os.path.isfile(d) and os.access(d, os.X_OK):
                return d
    elif plat == 'Linux':
        for d in sorted(glob.glob('/usr/lib/jvm/*/bin/javap'), reverse=True):
            if os.path.isfile(d) and os.access(d, os.X_OK):
                return d
    elif plat == 'Windows':
        for d in sorted(glob.glob(r'C:\Program Files\Java\*\bin\javap.exe'), reverse=True):
            if os.path.isfile(d):
                return d

    return 'NOT_AVAILABLE'
```

### javap Constructor Parser

Extracts DataGroup-to-WMID conditional mappings from Transaction class constructors by parsing `javap -c -p` output.

**Bytecode pattern to match:**
1. `getstatic CustomerDataGroup.<ENUM>` — identifies which DataGroup is being checked
2. `invokevirtual isRequested` — checks if this DataGroup was requested
3. `ifeq <label>` — branch if NOT requested
4. `ldc "WMID-*-PRM"` + `invokevirtual addField` — field registration

```python
"""Parse javap -c -p output to extract DataGroup->WMID conditional mappings."""
import subprocess, re, tempfile, zipfile, os

def extract_datagroup_wmid_from_javap(javap_path, jar_path, class_entry):
    """Run javap on a .class file inside a JAR and parse DataGroup->WMID mappings.
    class_entry: path inside JAR (e.g., 'com/barclays/gs/customer/gateway/CustomerAllRetrieveTransaction.class')
    Returns list of (datagroup_enum, wmid_param) tuples.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(jar_path) as zf:
            zf.extract(class_entry, tmpdir)
        class_name = class_entry.replace('/', '.').replace('.class', '')

        try:
            result = subprocess.run(
                [javap_path, '-c', '-p', '-classpath', tmpdir, class_name],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return []
        except Exception:
            return []

    mappings = []
    current_datagroup = None
    for line in result.stdout.splitlines():
        # Detect DataGroup enum reference
        dg_match = re.search(r'getstatic\s+#\d+\s+//\s+Field\s+\w*DataGroup\.(\w+)', line)
        if dg_match:
            current_datagroup = dg_match.group(1)
            continue

        # Detect WMID parameter string load
        wmid_match = re.search(r'ldc\s+#\d+\s+//\s+String\s+(WMID-\w+-PRM)', line)
        if wmid_match and current_datagroup:
            mappings.append((current_datagroup, wmid_match.group(1)))
            # Don't reset current_datagroup — compound conditions may have multiple WMIDs

    return mappings
```

### javap Identity Method Parser

Extracts exact `getProgramCode()` and `getVersionCode()` return values by looking for `ldc STRING` followed by `areturn`:

```python
import re

def parse_identity_methods(javap_output):
    """Parse javap output to extract getProgramCode() and getVersionCode() return values.
    Returns dict with 'program_code' and 'version_code' (or None if not found)."""
    result = {'program_code': None, 'version_code': None}
    lines = javap_output.splitlines()

    in_method = None
    last_ldc = None

    for line in lines:
        stripped = line.strip()

        # Detect method start
        if 'getProgramCode()' in stripped:
            in_method = 'program_code'
            last_ldc = None
        elif 'getVersionCode()' in stripped:
            in_method = 'version_code'
            last_ldc = None
        elif in_method and re.match(r'\w.*\(', stripped) and 'Code:' not in stripped:
            # New method started — stop tracking
            in_method = None
            last_ldc = None

        if in_method:
            # Look for ldc (string constant load)
            ldc_match = re.search(r'ldc\s+#\d+\s+//\s+String\s+(.+)', stripped)
            if ldc_match:
                last_ldc = ldc_match.group(1).strip()

            # areturn = return reference (the string loaded by ldc)
            if 'areturn' in stripped and last_ldc:
                result[in_method] = last_ldc
                in_method = None
                last_ldc = None

    return result
```
