---
name: cwe-183-permissive-list
description: "CWE-183: Permissive List of Allowed Inputs — "
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-183: Permissive List of Allowed Inputs
## Quick Start

This skill provides the fix pattern for CWE-183. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-183 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## Overview
A permissive allowlist accepts too many values or patterns, defeating the purpose of whitelisting. This includes overly broad regex patterns, incomplete character sets, or default-allow logic that bypasses the list.

## Vulnerability Pattern
```java
// VULNERABLE: Permissive regex allows injection
if (filename.matches(".*\\.txt")) { // Allows "malicious.php.txt"
    processFile(filename);
}

// VULNERABLE: Whitelist is incomplete
List<String> allowed = Arrays.asList("jpg", "png");
if (allowed.contains(extension)) { // "JPG" not in list, bypasses check
    uploadFile(file);
}
```

## Fix Strategy

1. **Make regex patterns strict** — use anchors (`^`, `$`), specific character classes
2. **Use explicit enum values** instead of strings when possible
3. **Normalize input first** (lowercase, trim) before checking allowlist
4. **Case-insensitive comparison** if needed
5. **Deny-by-default logic** — reject unless explicitly in whitelist

## Remediation Examples

### Option A: Fix regex pattern
```java
// FIXED: Strict pattern with anchors
if (filename.matches("^[a-zA-Z0-9_-]+\\.txt$")) {
    processFile(filename);
}
```

### Option B: Normalize and compare
```java
// FIXED: Case-insensitive check with normalized input
String normExt = extension.toLowerCase().trim();
List<String> allowed = Arrays.asList("jpg", "png", "gif");
if (allowed.contains(normExt)) {
    uploadFile(file);
}
```

### Option C: Use enum for values
```java
// FIXED: Type-safe allowlist
enum FileType { JPG, PNG, GIF }
FileType type = FileType.valueOf(extension.toUpperCase());
uploadFile(file);
```

## Implementation Checklist
- [ ] Find all allowlist/whitelist validation logic
- [ ] Verify regex patterns use anchors (`^` and `$`)
- [ ] Ensure case sensitivity is handled correctly (normalize if needed)
- [ ] Test with edge cases: mixed case, special chars, null values
- [ ] Confirm deny-by-default (reject unless in list)

## Key Points
- **Anchors are critical** — `.*\\.txt` != `^[a-zA-Z0-9_-]+\\.txt$`
- **Case sensitivity matters** — most file extensions should be case-insensitive
- **Test bypasses** — try uppercase, mixed case, adding extra dots, null bytes
- **Severity**: Medium to High — depends on what is being bypassed

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
