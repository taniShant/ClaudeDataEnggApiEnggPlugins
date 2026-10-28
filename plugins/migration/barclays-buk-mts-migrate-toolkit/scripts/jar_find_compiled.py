"""S.4 — Find compiled JARs for an artifact in Gradle cache."""
import os, glob, sys

artifact = sys.argv[1]
home = os.environ.get('USERPROFILE', os.path.expanduser('~'))
base = os.path.join(home, '.gradle', 'caches', 'modules-2', 'files-2.1', '')
for f in sorted(glob.glob(base + f'**/{artifact}*/**/*.jar', recursive=True)):
    bn = os.path.basename(f)
    if '-sources' not in bn and '-javadoc' not in bn:
        print(f'COMPILED: {f}')
