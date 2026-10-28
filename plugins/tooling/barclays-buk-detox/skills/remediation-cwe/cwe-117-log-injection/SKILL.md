---
name: cwe-117-log-injection
description: "CWE-117: Improper Output Neutralization for Logs — "
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-117: Improper Output Neutralization for Logs
## Quick Start

This skill provides the fix pattern for CWE-117. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-117 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## Overview
Log injection occurs when user-controlled data is written to log files without proper encoding or filtering. Attackers can inject newlines and false log entries to obscure attack trails or create misleading audit records.

## Vulnerability Pattern
```java
// VULNERABLE: Direct log output with untrusted input
logger.info("User action: " + userInput);
logger.warn("Request from IP: " + request.getRemoteAddr());
```

## Fix Strategy

1. **Never log raw user input** — always sanitize or encode
2. **Replace line breaks and control characters** in log output
3. **Use structured logging** with parameter binding (not string concatenation)
4. **Validate log entries** before writing

## Remediation Examples

### Option A: Strip line breaks (simple)
```java
// FIXED: Remove newlines from user input before logging
String sanitized = userInput.replaceAll("[\n\r]", "");
logger.info("User action: " + sanitized);
```

### Option B: Use parameterized logging
```java
// FIXED: Use SLF4J/Log4j parameter binding
logger.info("User action: {}", userInput);  // Framework handles escaping
```

### Option C: URL encode for display
```java
// FIXED: Encode user input for safe logging
String encoded = URLEncoder.encode(userInput, "UTF-8");
logger.info("User action: " + encoded);
```

## Implementation Checklist
- [ ] Identify all logger calls in the affected file
- [ ] Check if any logger arguments contain user-controlled data
- [ ] Apply sanitization (strip `\n`, `\r`, other control chars) OR use parameterized logging
- [ ] Test: verify malicious log entries are neutralized
- [ ] Verify: log output is still human-readable and includes necessary context

## Key Points
- **Parameterized logging is preferred** — it's safer and clearer
- **Control characters matter** — newlines (`\n`, `\r`), tabs (`\t`), null bytes
- **Not just user input** — also sanitize request headers, URLs, database values
- **Severity**: Medium — enables log tampering and attack obfuscation, not direct code execution

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
