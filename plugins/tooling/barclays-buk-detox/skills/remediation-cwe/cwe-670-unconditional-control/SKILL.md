---
name: cwe-670-unconditional-control
description: "CWE-670: Always-Incorrect Control Flow Implementation — "
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-670: Always-Incorrect Control Flow Implementation
## Quick Start

This skill provides the fix pattern for CWE-670. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-670 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## Overview
Control flow logic is implemented in a way that always produces incorrect behavior, such as unreachable code, always-true/always-false conditions, or inverted logic.

## Vulnerability Pattern
```java
// VULNERABLE: Inverted boolean logic
if (!isValidUser) {  // Negation!
    grantAdminAccess();  // ERROR: Grants access to INVALID users
}

// VULNERABLE: Always-true condition
if (true || isAuthorized) {
    processRequest();  // Always executes, even if not authorized
}

// VULNERABLE: Unreachable code
if (condition) {
    return true;
} else {
    return true;  // Same as above, always true
}
```

## Fix Strategy

1. **Review boolean logic carefully** — check for inverted conditions (`!`)
2. **Test branch conditions** — ensure both paths are reachable
3. **Use debugger or logging** to verify logic flow
4. **Simplify complex conditions** into readable statements
5. **Use code review** to catch logic errors before deploy

## Remediation Examples

### Option A: Fix inverted logic
```java
// VULNERABLE: Inverted
if (!isAuthorized) {
    grantAccess();
}

// FIXED: Correct logic
if (isAuthorized) {
    grantAccess();
}
```

### Option B: Fix always-true condition
```java
// VULNERABLE: Always true
if (true || isValidUser) {
    processRequest();
}

// FIXED: Proper condition
if (isValidUser) {
    processRequest();
}
```

### Option C: Fix unreachable code
```java
// VULNERABLE: Second condition unreachable
if (condition) {
    logger.info("Branch A");
} else {
    logger.info("Branch A again");  // Unreachable difference
}

// FIXED: Both branches reachable
if (condition) {
    logger.info("Branch A");
} else {
    logger.info("Branch B");  // Now reachable
}
```

### Option D: Simplify complex conditions
```java
// VULNERABLE: Complex, hard to verify
if (!(user == null || user.getRole() == null || !user.getRole().equals("admin"))) {
    grantAccess();
}

// FIXED: Clear logic
if (user != null && "admin".equals(user.getRole())) {
    grantAccess();
}
```

## Implementation Checklist
- [ ] Review security-critical control flow (auth checks, access control)
- [ ] Identify any negation operators (`!`) and verify intent
- [ ] Identify any always-true/always-false conditions
- [ ] Identify any unreachable code
- [ ] Add test cases for both branches of conditions
- [ ] Use debugger to step through logic
- [ ] Add logging to verify flow at runtime

## Key Points
- **Logic inversions are subtle but deadly** — easy to miss, hard to catch
- **Test coverage matters** — unreachable code won't be caught without testing
- **Code review is essential** — especially for security-critical logic
- **Readable code prevents errors** — complex nested conditions hide bugs
- **Severity**: High — can completely bypass security controls

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
