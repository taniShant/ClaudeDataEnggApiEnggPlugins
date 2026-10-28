#!/usr/bin/env python3
"""
Tier 3: javap Bytecode Disassembly Parser for EBS/EGS compiled JARs.

Usage:
    python jar_javap.py <jar_path> [--filter <class_substring>] [--json]

Uses the JDK javap tool to extract exact values from compiled bytecode:
  - Exact getProgramCode() return value (transaction program code e.g. "CU")
  - Exact getVersionCode() return value (transaction version code e.g. "Q")
  - DataGroup-to-WMID conditional mappings from Transaction constructors

Requires javap on the system PATH, in JAVA_HOME/bin, or at standard OS locations.
Falls back gracefully if javap is not available — prints a warning and exits 0.

Confidence tag produced: "verified-from-bytecode"
No external dependencies — stdlib only.
"""

import os, platform, glob, subprocess, re, json, argparse, tempfile, zipfile, sys
from pathlib import Path


# ---------------------------------------------------------------------------
# javap discovery
# ---------------------------------------------------------------------------

def find_javap():
    """Locate the javap executable. Returns path string or None."""
    plat = platform.system()
    exe  = 'javap.exe' if plat == 'Windows' else 'javap'

    # 1. Check PATH
    for p in os.environ.get('PATH', '').split(os.pathsep):
        candidate = os.path.join(p, exe)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    # 2. Check JAVA_HOME
    java_home = os.environ.get('JAVA_HOME', '')
    if java_home:
        candidate = os.path.join(java_home, 'bin', exe)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    # 3. Platform-specific well-known locations
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

    return None


# ---------------------------------------------------------------------------
# javap output parsers
# ---------------------------------------------------------------------------

def parse_identity_methods(javap_output):
    """Parse javap -c -p output to extract getProgramCode() and getVersionCode() return values.

    Looks for the pattern:  ldc "VALUE" ... areturn  inside each identity method.
    Returns dict: {"program_code": str|None, "version_code": str|None}
    """
    result  = {'program_code': None, 'version_code': None}
    lines   = javap_output.splitlines()
    in_meth = None
    last_ldc = None

    for line in lines:
        stripped = line.strip()

        if 'getProgramCode()' in stripped:
            in_meth, last_ldc = 'program_code', None
        elif 'getVersionCode()' in stripped:
            in_meth, last_ldc = 'version_code', None
        elif in_meth and re.match(r'\w.*\(', stripped) and 'Code:' not in stripped:
            in_meth, last_ldc = None, None

        if in_meth:
            m = re.search(r'ldc\s+#\d+\s+//\s+String\s+(.+)', stripped)
            if m:
                last_ldc = m.group(1).strip()
            if 'areturn' in stripped and last_ldc:
                result[in_meth] = last_ldc
                in_meth, last_ldc = None, None

    return result


def parse_datagroup_wmid_mappings(javap_output):
    """Parse javap -c -p output to extract DataGroup-to-WMID conditional mappings.

    Bytecode pattern:
      getstatic  CustomerDataGroup.ENUM   (which DataGroup is gated)
      invokevirtual isRequested           (check if requested)
      ifeq <skip>                         (branch if NOT requested)
      ldc "WMID-*-PRM"                   (field to register)
      invokevirtual addField

    Returns list of {"datagroup": str, "wmid": str} dicts.
    """
    mappings = []
    current_dg = None

    for line in javap_output.splitlines():
        dg_m = re.search(r'getstatic\s+#\d+\s+//\s+Field\s+\w*DataGroup\.(\w+)', line)
        if dg_m:
            current_dg = dg_m.group(1)
            continue

        wmid_m = re.search(r'ldc\s+#\d+\s+//\s+String\s+(WMID-[\w-]+-PRM)', line)
        if wmid_m and current_dg:
            mappings.append({'datagroup': current_dg, 'wmid': wmid_m.group(1)})
            # don't reset — one DataGroup can gate multiple WMIDs

    return mappings


# ---------------------------------------------------------------------------
# Per-class extraction
# ---------------------------------------------------------------------------

def _run_javap(javap_path, jar_path, class_entry):
    """Run javap on a single .class entry extracted from a JAR.

    Returns stdout string or None on failure.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(jar_path) as zf:
            try:
                zf.extract(class_entry, tmpdir)
            except Exception:
                return None

        class_name = class_entry.replace('/', '.').replace('.class', '')
        try:
            proc = subprocess.run(
                [javap_path, '-c', '-p', '-classpath', tmpdir, class_name],
                capture_output=True, text=True, timeout=30,
            )
            if proc.returncode != 0:
                return None
            return proc.stdout
        except Exception:
            return None


def extract_from_jar(jar_path, javap_path, class_filter=None):
    """Run Tier 3 extraction on all matching Transaction/Command classes.

    Returns list of dicts:
      {
        "class":       str,
        "type":        "transaction" | "command",
        "program_code": str | None,
        "version_code": str | None,
        "dg_wmid_mappings": list[{"datagroup": str, "wmid": str}],
        "confidence":  "verified-from-bytecode",
      }
    """
    results = []
    with zipfile.ZipFile(jar_path) as zf:
        entries = zf.namelist()

    for entry in entries:
        if not entry.endswith('.class'):
            continue
        if class_filter and class_filter.lower() not in entry.lower():
            continue

        is_transaction = 'Transaction' in entry
        is_command     = 'Command' in entry
        if not (is_transaction or is_command):
            continue

        cls_type = 'transaction' if is_transaction else 'command'
        javap_out = _run_javap(javap_path, jar_path, entry)
        if not javap_out:
            continue

        identity = parse_identity_methods(javap_out) if is_transaction else {}
        mappings = parse_datagroup_wmid_mappings(javap_out) if is_transaction else []
        class_name = entry.replace('/', '.').replace('.class', '')

        results.append({
            'class':            class_name,
            'type':             cls_type,
            'program_code':     identity.get('program_code'),
            'version_code':     identity.get('version_code'),
            'dg_wmid_mappings': mappings,
            'confidence':       'verified-from-bytecode',
        })

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_text(results, jar_path, javap_path):
    print(f"JAR:   {jar_path}")
    print(f"javap: {javap_path}")
    if not results:
        print("No Transaction/Command classes found.")
        return
    for r in results:
        print(f"\n[{r['type'].upper()}] {r['class']}")
        if r.get('program_code'):
            print(f"  getProgramCode() = \"{r['program_code']}\"  (confidence: {r['confidence']})")
        if r.get('version_code'):
            print(f"  getVersionCode() = \"{r['version_code']}\"  (confidence: {r['confidence']})")
        if r['dg_wmid_mappings']:
            print(f"  DataGroup → WMID mappings ({len(r['dg_wmid_mappings'])}):")
            for m in r['dg_wmid_mappings']:
                print(f"    {m['datagroup']:<40} → {m['wmid']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('jar_path', help='Path to the compiled EBS/EGS JAR file')
    parser.add_argument('--filter', metavar='SUBSTRING', help='Only process .class files whose path contains SUBSTRING')
    parser.add_argument('--json', action='store_true', help='Output JSON instead of human-readable text')
    args = parser.parse_args()

    javap = find_javap()
    if not javap:
        msg = ("javap not found — Tier 3 extraction unavailable. "
               "Install a JDK and ensure javap is on PATH or set JAVA_HOME.")
        if args.json:
            print(json.dumps({'error': msg, 'results': []}))
        else:
            print(f"WARNING: {msg}")
        sys.exit(0)

    results = extract_from_jar(args.jar_path, javap, class_filter=args.filter)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        _print_text(results, args.jar_path, javap)
        print(f"\nTotal classes processed: {len(results)}")


if __name__ == '__main__':
    main()
