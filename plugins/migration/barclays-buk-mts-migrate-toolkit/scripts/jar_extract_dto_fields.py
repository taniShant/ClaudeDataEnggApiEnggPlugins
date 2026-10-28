"""S.7d-post — Extract Gateway DTO class field declarations from EGS source JAR."""
import zipfile, re, sys

jar = sys.argv[1]
target = sys.argv[2]  # PRIMARY_TRANSACTION_CLASS

# Step 1: Find DTO class names from parseResponse/parseArrayResponse
dto_classes = set()
with zipfile.ZipFile(jar) as zf:
    for name in zf.namelist():
        if target in name and name.endswith('.java'):
            src = zf.read(name).decode('utf-8', errors='replace')
            for m in re.finditer(r'new\s+(\w+Data)\s*\(', src):
                dto_classes.add(m.group(1))
            for m in re.finditer(r'(\w+Data)\s+\w+\s*=', src):
                dto_classes.add(m.group(1))

print(f'DTO_CLASSES: {sorted(dto_classes)}')

# Step 2: Extract field declarations from each DTO class
with zipfile.ZipFile(jar) as zf:
    for dto in sorted(dto_classes):
        for name in zf.namelist():
            if dto in name and name.endswith('.java'):
                src = zf.read(name).decode('utf-8', errors='replace')
                print(f'\n=== {dto} (from {name}) ===')
                for line in src.splitlines():
                    line_s = line.strip()
                    if re.match(r'(private|protected|public)\s+\w', line_s) and not line_s.startswith('//'):
                        if '(' not in line_s:
                            print(f'  FIELD: {line_s}')
                    if re.match(r'public\s+\w.*get\w+\s*\(', line_s):
                        print(f'  GETTER: {line_s}')
                break
