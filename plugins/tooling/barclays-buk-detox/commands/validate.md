---
description: Re-scan files after a fix to verify the CWE vulnerability is resolved
argument-hint: FILE_PATH [--cwe CWE_ID]
---

You are the main Claude Code agent.

When the user runs `/barclays-buk-detox:validate`, they want to **re-scan a file** after a manual or automated fix to verify the vulnerability has been eliminated.

## Options

| Option | Required | Description |
|---|---|---|
| `FILE_PATH` | Yes | Path to the file to validate |
| `--cwe CWE_ID` | No | Filter results to a specific CWE (e.g., CWE-89, CWE-79) |

## Step 1: Parse Arguments

```
FORMAT: FILE_PATH [--cwe CWE_ID]

POSITIONAL (required):
  FILE_PATH    Path to the file to validate

FLAGS (optional):
  --cwe CWE_ID    Filter results to a specific CWE (e.g., CWE-89, CWE-79)
```

## Step 2: Validate Arguments

### 2.1 Validate file_path
- File must exist
- Must be a source code file (not binary)

**On failure:** Report "File not found: {path}" and STOP.

### 2.2 Validate cwe_id (if provided)
- Must match pattern: `^CWE-\d+$` (case-insensitive)
- Normalize to uppercase: `CWE-89`

**On failure:** Report "Invalid CWE format. Expected: CWE-XXX (e.g., CWE-89)" and STOP.

## Step 3: Delegate to detox-validator-agent

**Delegate to Subagent**: Use the Task tool with `subagent_type: "barclays-buk-detox:detox-validator-agent"`:

```
Validate file after fix:
- file_path: {file_path}
- cwe_filter: {cwe_id or "None"}
- mode: single_file_validation
```

**Fallback Behavior**: If the `detox-validator-agent` subagent is unavailable, run validation directly:
1. Run `semgrep --config auto --json {file_path}`
2. If `--cwe` provided, filter results to that CWE only
3. Report whether the vulnerability was successfully eliminated
4. If findings remain, list what is still vulnerable with line numbers

## Step 4: Report Results

Display:
```
✅ VALIDATION PASSED — No CWE-{id} findings remain in {file_path}
```
or
```
❌ VALIDATION FAILED — {count} finding(s) remain:

| Line | CWE | Severity | Rule | Message |
|------|-----|----------|------|---------|
| ...  | ... | ...      | ...  | ...     |

Suggested: Review the flagged lines and re-apply the fix.
```

## Usage Examples

### Example 1: Validate a Fixed File
```bash
/barclays-buk-detox:validate src/db/queries.py
```

### Example 2: Validate Specific CWE
```bash
/barclays-buk-detox:validate src/api/handlers.py --cwe CWE-89
```

### Example 3: Validate After XSS Fix
```bash
/barclays-buk-detox:validate src/views/render.js --cwe CWE-79
```
