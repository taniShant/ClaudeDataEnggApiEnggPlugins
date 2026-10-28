---
name: remediation-standard-doc
description: "Remediation skill extensions — CWE information, vulnerable patterns, fix patterns, language examples, testing, and common mistakes"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/standards/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Remediation Skill Standard

Extension of the Skills Standard for CWE-specific remediation skills.
## Quick Start

This skill defines the quality and compliance standards applied to all detox remediations and documentation.

```
# Loaded by detox-report-agent and detox-fix-agent to validate output quality.
```



## Required Sections

Every remediation skill MUST include all sections from SKILLS_STANDARD.md PLUS:

### CWE Information
- **CWE ID**: The numeric CWE identifier (e.g., CWE-89)
- **CWE Name**: Official CWE name
- **Severity**: Typical severity (Critical/High/Medium/Low)
- **OWASP Category**: Related OWASP Top 10 category if applicable

### Vulnerable Pattern
- Code patterns that indicate this vulnerability
- Language-specific examples of the vulnerable pattern
- Regex or AST patterns for detection

### Fix Pattern
- The general fix approach (e.g., parameterized queries for SQL injection)
- Step-by-step transformation from vulnerable to secure code
- Preserve existing functionality while eliminating the vulnerability

### Language-Specific Examples
For each supported language, provide:
- Before (vulnerable) code
- After (fixed) code
- Explanation of the fix

### Testing Guidance
- How to verify the fix eliminates the vulnerability
- How to verify the fix doesn't break existing functionality
- Semgrep rules that should pass after fix

### Common Mistakes
- Anti-patterns to avoid during remediation
- Incomplete fixes that still leave the vulnerability
- Over-engineering traps

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
