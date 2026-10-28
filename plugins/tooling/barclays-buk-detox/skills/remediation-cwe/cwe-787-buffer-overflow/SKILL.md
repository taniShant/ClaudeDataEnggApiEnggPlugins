---
name: cwe-787-buffer-overflow
description: "CWE-787: Out-of-bounds Write Remediation — Remediate buffer overflow and out-of-bounds write vulnerabilities by using safe memory operations, bounds checking, and modern languages with automati"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-787: Out-of-bounds Write Remediation
## Quick Start

This skill provides the fix pattern for CWE-787. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-787 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-787
- **CWE Name**: Out-of-bounds Write
- **Severity**: Critical
- **OWASP Category**: A04:2021 - Insecure Design

## Purpose

Remediate buffer overflow and out-of-bounds write vulnerabilities by using safe memory operations, bounds checking, and modern languages with automatic memory management.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file.
  - `line_number` (integer, required): The 1-based line number.
  - `cwe_id` (string, required): Must be `CWE-787`.

## Steps

1. **Identify dangerous functions** (strcpy, sprintf, memcpy without bounds).
2. **Replace with safe alternatives** (strncpy, snprintf, bounds-checked copy).
3. **Add bounds checking** before write operations.

## Output Format

```json
{
  "status": "success | partial | error",
  "file_path": "<string>",
  "changes": [
    {
      "line_number": "<integer>",
      "dangerous_function": "<string>",
      "safe_alternative": "<string>"
    }
  ],
  "error": "null or string"
}
```

## Vulnerable Pattern

```c
char buffer[10];
strcpy(buffer, user_input);  // VULNERABLE: no bounds check
```

## Fix Pattern

Use safe functions with bounds checking or automatic memory management.

## Language-Specific Examples

### C

**Before (vulnerable):**
```c
void process_name(char *user_name) {
    char buffer[20];
    strcpy(buffer, user_name);  // Buffer overflow!
}
```

**After (fixed):**
```c
void process_name(const char *user_name) {
    char buffer[20];
    if (user_name != NULL) {
        strncpy(buffer, user_name, sizeof(buffer) - 1);
        buffer[sizeof(buffer) - 1] = '\0';
    }
}
```

## Constraints

- Always check buffer bounds before write.
- Use null-termination for strings.
- Use snprintf instead of sprintf.
- Consider using higher-level languages with automatic memory management.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
