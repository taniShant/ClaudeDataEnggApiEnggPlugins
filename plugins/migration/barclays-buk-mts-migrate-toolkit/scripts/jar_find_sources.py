"""S.4 — Find source JARs for an artifact in Gradle cache."""
import os, glob, sys

artifact = sys.argv[1]
home = os.environ.get('USERPROFILE', os.path.expanduser('~'))
base = os.path.join(home, '.gradle', 'caches', 'modules-2', 'files-2.1', '')
for f in sorted(glob.glob(base + f'**/{artifact}*/**/*-sources.jar', recursive=True)):
    print(f'SOURCE: {f}')
