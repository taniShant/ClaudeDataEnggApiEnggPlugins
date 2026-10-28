"""S.7b — Extract WMID-TDL chain from Transaction class constructor."""
import zipfile, re, sys

jar = sys.argv[1]
target = sys.argv[2]  # PRIMARY_TRANSACTION_CLASS
with zipfile.ZipFile(jar) as zf:
    for name in zf.namelist():
        if target in name and name.endswith('.java'):
            src = zf.read(name).decode('utf-8', errors='replace')
            lines = src.splitlines()
            for i, line in enumerate(lines):
                if re.search(r'addField.*WMID.*PRM', line):
                    start = max(0, i - 3)
                    end = min(len(lines), i + 6)
                    for j in range(start, end):
                        print(f'{j+1}: {lines[j]}')
                    print('---')
