"""S.7c — Extract Command class gateway calls from EBS source JAR."""
import zipfile, re, sys

jar = sys.argv[1]
with zipfile.ZipFile(jar) as zf:
    for name in zf.namelist():
        if name.endswith('Command.java'):
            src = zf.read(name).decode('utf-8', errors='replace')
            for line in src.splitlines():
                if re.search(r'Gateway|DataGroup|doExecute', line):
                    print(line.strip())
