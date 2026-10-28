---
name: remediation-standard
description: CWE remediation standards, skill structure requirements, and fix quality guidelines for the detox pipeline
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_standard/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE Remediation Standard
## Quick Start

This skill defines the quality and compliance standards applied to all detox remediations and documentation.

```
# Loaded by detox-report-agent and detox-fix-agent to validate output quality.
```



## Purpose

Defines the quality standards, structure requirements, and fix patterns that all CWE remediation skills must follow. This document serves as the reference for how vulnerability fixes should be applied, validated, and documented.

## Skill Structure Standard

Every CWE remediation skill MUST include:

### CWE Information
- **CWE ID**: The numeric identifier (e.g., CWE-89)
- **CWE Name**: Official CWE name
- **Severity**: Typical severity (Critical/High/Medium/Low)
- **OWASP Category**: Related OWASP Top 10 category

### Vulnerable Pattern
- Code patterns indicating the vulnerability
- Language-specific detection patterns
- Indicators of user-controlled input

### Fix Pattern
- General fix approach
- Step-by-step transformation from vulnerable to secure
- Preserve existing functionality

### Language-Specific Examples
For each supported language:
- Before (vulnerable) code
- After (fixed) code
- Explanation of the fix

### Testing Guidance
- How to verify the fix eliminates the vulnerability
- How to verify no functional regression
- Semgrep rules that should pass after fix

### Common Mistakes
- Anti-patterns to avoid during remediation
- Incomplete fixes that leave residual risk
- Over-engineering traps

## Fix Quality Principles

1. **Minimal Diff**: Change only what is needed. Do not refactor surrounding code.
2. **Preserve Logic**: Fixed code must produce identical results for valid inputs.
3. **No Execution**: Never execute code or queries to test fixes.
4. **No Schema Changes**: Never alter databases, APIs, or infrastructure.
5. **Atomic Fixes**: One vulnerability per fix operation.
6. **Framework-Native**: Use the framework's built-in security mechanisms first.
7. **Fail-Safe**: When unsure, choose the more restrictive option.

## Fix Workflow Standard

1. **Read Context** — Read file + surrounding 50 lines
2. **Detect Stack** — Language, framework, library versions
3. **Identify Pattern** — Match vulnerable code to known pattern
4. **Apply Fix** — Edit with the secure equivalent
5. **Scan Similar** — Grep for same pattern in file
6. **Verify Syntax** — Re-read to confirm no syntax errors
7. **Report Result** — Return structured JSON

## Severity Mapping

| Source Value | Canonical | Auto-Fix | Priority |
|---|---|---|---|
| CRITICAL | critical | Yes | 1 (highest) |
| HIGH | high | Yes | 2 |
| MEDIUM | medium | Yes | 3 |
| LOW | low | Configurable | 4 |
| INFORMATIONAL | info | No | 5 |

## Remediation Type Classification

| Type | Description | Action |
|---|---|---|
| `code_fix` | Can be fixed in source code | Auto-remediate |
| `infra_config` | Requires infra/config change | Generate corrective action doc |
| `dependency` | Requires dependency upgrade | Log for ticket creation |
| `manual` | Requires human judgment | Flag for manual review |

## Output Format Standard

All fix operations return:
```json
{
  "status": "success|partial|error",
  "cwe_id": "CWE-XXX",
  "file_path": "/path/to/file",
  "changes": [
    {
      "line_number": 42,
      "original_code": "vulnerable code here",
      "fixed_code": "secure code here",
      "fix_type": "parameterized_query|encoding|validation|etc"
    }
  ],
  "similar_patterns_fixed": 0,
  "imports_added": [],
  "warnings": [],
  "error": null
}
```

## Error Handling Standard

| Failure Mode | Handling |
|---|---|
| File not found | Return error, do not retry |
| Language not recognized | Return error, flag for manual review |
| Cannot determine fix | Flag for manual review with guidance |
| Fix breaks compilation | Attempt simpler fix; if impossible, return error |
| Multiple interleaved vulns | Fix only assigned one, note others |
| ORM usage (safe) | Mark as false positive if framework handles sanitization |

## Constraints

- Never introduce new vulnerabilities while fixing existing ones
- Never remove existing security controls
- Never bypass authentication or authorization checks
- Never expose sensitive data in fix code or logs
- Always prefer established library functions over custom implementations
- Always validate at system boundaries (user input, external APIs)

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
