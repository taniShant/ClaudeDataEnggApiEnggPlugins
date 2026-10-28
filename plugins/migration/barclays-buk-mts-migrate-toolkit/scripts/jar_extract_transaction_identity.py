"""S.7a — Extract Transaction class identity from EGS source JAR."""
import zipfile, re, sys

jar = sys.argv[1]
target = sys.argv[2]  # PRIMARY_TRANSACTION_CLASS
with zipfile.ZipFile(jar) as zf:
    for name in zf.namelist():
        if target in name and name.endswith('.java'):
            print(f'FOUND: {name}')
            src = zf.read(name).decode('utf-8', errors='replace')
            for line in src.splitlines():
                if re.search(r'getProgramCode|getVersionCode|getName|class.*extends', line):
                    print(line.strip())
