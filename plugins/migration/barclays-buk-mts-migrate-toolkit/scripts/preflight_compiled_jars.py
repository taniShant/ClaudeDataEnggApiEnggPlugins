"""Pre-flight Step 0.2b — Detect compiled JAR fallback capability."""
import os, glob, platform

home = os.environ.get('USERPROFILE', os.path.expanduser('~'))
base = os.path.join(home, '.gradle', 'caches', 'modules-2', 'files-2.1', '')

# Find all EBS/EGS compiled JARs (non-sources)
compiled = set()
sources = set()
for pattern in ['**/ebs_*/**/*.jar', '**/egs_*/**/*.jar', '**/cgs_*/**/*.jar']:
    for f in glob.glob(base + pattern, recursive=True):
        if '-sources' in os.path.basename(f):
            parts = f.replace(base, '').split(os.sep)
            if len(parts) >= 1:
                sources.add(parts[0])
        elif f.endswith('.jar') and not f.endswith('-javadoc.jar'):
            parts = f.replace(base, '').split(os.sep)
            if len(parts) >= 1:
                compiled.add(parts[0])

compiled_only = compiled - sources
print(f'COMPILED_JARS_FOUND={len(compiled_only)}')


def find_javap():
    plat = platform.system()
    for p in os.environ.get('PATH', '').split(os.pathsep):
        candidate = os.path.join(p, 'javap.exe' if plat == 'Windows' else 'javap')
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    java_home = os.environ.get('JAVA_HOME', '')
    if java_home:
        candidate = os.path.join(java_home, 'bin', 'javap.exe' if plat == 'Windows' else 'javap')
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
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


javap_path = find_javap()
print(f'JAVAP_PATH={javap_path}')

if len(compiled_only) == 0:
    print('COMPILED_JAR_FALLBACK=NONE')
elif javap_path != 'NOT_AVAILABLE':
    print('COMPILED_JAR_FALLBACK=FULL')
else:
    print('COMPILED_JAR_FALLBACK=PARTIAL')
