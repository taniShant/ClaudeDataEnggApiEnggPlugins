---
description: Run a Semgrep SAST scan on a directory and display findings by CWE and severity
argument-hint: [DIRECTORY]
---

You are the main Claude Code agent.

When the user runs `/barclays-buk-detox:scan`, they want to **run a SAST scan** on a directory using Semgrep and see a summary of findings.

## Step 1: Parse Arguments

```
FORMAT: [DIRECTORY]

POSITIONAL (optional):
  DIRECTORY    Path to scan (defaults to current working directory)
```

- If no argument provided, use the current working directory
- If argument is `.`, resolve to current working directory
- If argument is an absolute path, use as-is

## Step 2: Validate Arguments

- Directory must exist
- Directory must be readable

**On failure:** Report "Directory not found: {path}" and STOP.

## Step 3: Delegate to detox-scan-agent

**Delegate to Subagent**: Use the Task tool with `subagent_type: "barclays-buk-detox:detox-scan-agent"`:

```
Run Semgrep SAST scan on directory:
- scan_directory: {directory}
```

**Fallback Behavior**: If the `detox-scan-agent` subagent is unavailable, run the scan directly:
1. Execute `semgrep --config auto --json {directory}`
2. Parse the JSON output
3. Summarize findings by severity and CWE
4. Display a table: File | Line | CWE | Severity | Rule | Message

## Example Output

```
✅ SEMGREP SCAN COMPLETED

Scan directory: ./src
Total findings: 8

| File | Line | CWE | Severity | Rule | Message |
|------|------|-----|----------|------|---------|
| db/queries.py | 42 | CWE-89 | HIGH | sql-injection | Possible SQL injection detected in query construction |
| api/handlers.py | 156 | CWE-79 | MEDIUM | cross-site-scripting | Unsafe HTML construction without escaping |
| auth/login.py | 78 | CWE-937 | HIGH | vulnerable-dependency | log4j:log4j:1.2.17 (CVE-2021-4104) |
| utils/crypto.py | 23 | CWE-327 | HIGH | weak-crypto | Use of MD5 for password hashing |
| config/database.py | 12 | CWE-798 | MEDIUM | hardcoded-credential | Hardcoded database password in source |

Summary by severity:
  CRITICAL: 0
  HIGH: 3
  MEDIUM: 2
  LOW: 3

Summary by CWE:
  CWE-89 (SQL Injection): 1
  CWE-79 (XSS): 1
  CWE-937 (Vulnerable Components): 1
  CWE-327 (Weak Crypto): 1
  CWE-798 (Hardcoded Credentials): 1
  Other: 3
```

## Usage Examples

### Example 1: Scan Current Directory
```bash
/barclays-buk-detox:scan
```

### Example 2: Scan Specific Directory
```bash
/barclays-buk-detox:scan /path/to/project/src
```

### Example 3: Scan Relative Path
```bash
/barclays-buk-detox:scan ./src/main
```
