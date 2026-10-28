---
name: cwe-522-insufficiently-protected-creds
description: "CWE-522: Insufficiently Protected Credentials — "
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-522: Insufficiently Protected Credentials
## Quick Start

This skill provides the fix pattern for CWE-522. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-522 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## Overview
Credentials (passwords, API keys, tokens) are not protected adequately, making them accessible to attackers through logs, memory, environment variables, or configuration files.

## Vulnerability Pattern
```java
// VULNERABLE: Credentials in logs
logger.info("User password: " + password);

// VULNERABLE: Credentials in environment/system properties
System.setProperty("db.password", dbPassword);

// VULNERABLE: Credentials in code
String apiKey = "sk-abc123def456";

// VULNERABLE: Credentials not masked in memory
char[] password = userInput.toCharArray();  // Won't be zeroed after use
```

## Fix Strategy

1. **Never log credentials** — log only non-sensitive identifiers
2. **Use secure credential storage** — key vaults, encrypted config
3. **Keep credentials in memory only as long as needed** — zero out after use
4. **Use character arrays** (char[]) instead of Strings for passwords (they can be garbage-collected)
5. **Mask credentials in logs** — if part of structured data, redact values

## Remediation Examples

### Option A: Vault/SecureStore for credentials
```java
// FIXED: Store credentials in secure vault
VaultClient vault = new VaultClient();
String dbPassword = vault.getSecret("db/production/password");
// Use password
// Password is not stored in code or logs
```

### Option B: Use char[] for passwords
```java
// FIXED: Use char[] instead of String for sensitive data
char[] password = new char[length];
readPasswordFromSecureSource(password);

try {
    if (authenticate(username, password)) {
        // Process
    }
} finally {
    // Zero out password from memory
    Arrays.fill(password, '\0');
}
```

### Option C: Externalize configuration
```java
// FIXED: Store credentials in environment variables or encrypted config file
// application.properties (external, not in repo):
# db.password=${DB_PASSWORD}

// Java code:
@Value("${db.password}")
private String dbPassword;

// Set via environment: export DB_PASSWORD=secret
// Or via config file (encrypted, external to repo)
```

### Option D: Mask in logs
```java
// FIXED: Redact credentials from structured logs
String safeLog = String.format(
    "Auth attempt: user=%s, mfa=%s, password=%s",
    username,
    mfaMethod,
    "***REDACTED***"
);
logger.info(safeLog);
```

## Implementation Checklist
- [ ] Search logs for credentials (grep for "password", "token", "key", "secret")
- [ ] Search code for hardcoded credentials
- [ ] Verify credentials are not in environment variables visible to logs
- [ ] Check System.setProperty() calls — credentials should not be stored
- [ ] Verify password handling uses char[] where appropriate
- [ ] Test: credentials should not appear in application logs or error messages

## Key Points
- **Logs are a security boundary** — treat like public data
- **Char arrays + Arrays.fill()** — proper password handling in memory
- **Vaults are the right solution** — Hashicorp Vault, AWS Secrets Manager, etc.
- **Environment variables are OK if process isolation exists** — but not in logs
- **Severity**: Critical — direct path to credential theft

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
