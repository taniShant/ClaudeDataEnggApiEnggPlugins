"""Pre-flight Step 0.2 — Check Gradle cache for EBS/EGS source artifacts."""
import os, glob

home = os.environ.get('USERPROFILE', os.path.expanduser('~'))  # USERPROFILE for Windows
base = os.path.join(home, '.gradle', 'caches', 'modules-2', 'files-2.1', '')
found = []
for pattern in ['**/ebs_*sources*.jar', '**/egs_*sources*.jar', '**/cgs_*sources*.jar']:
    found.extend(glob.glob(base + pattern, recursive=True))

print(f'GRADLE_CACHE_STATUS={"POPULATED" if found else "EMPTY"}')
print(f'SOURCE_JARS_FOUND={len(found)}')
for f in found[:10]:
    print(f'  JAR: {f}')
