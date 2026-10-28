"""S.7d — Extract WMOD response fields from Transaction class in EGS source JAR."""
import zipfile, re, sys

jar = sys.argv[1]
target = sys.argv[2]  # PRIMARY_TRANSACTION_CLASS
with zipfile.ZipFile(jar) as zf:
    for name in zf.namelist():
        if target in name and name.endswith('.java'):
            src = zf.read(name).decode('utf-8', errors='replace')
            for line in src.splitlines():
                if re.search(r'getField.*WMOD|getIntField.*WMOD|getDateField.*WMOD|getLongField.*WMOD', line):
                    print(line.strip())
