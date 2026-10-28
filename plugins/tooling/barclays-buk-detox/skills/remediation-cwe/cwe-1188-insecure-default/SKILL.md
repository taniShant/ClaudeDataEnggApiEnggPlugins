---
name: cwe-1188-insecure-default
description: "CWE-1188: Initialization with Hard-Coded Network Resource Configuration Data — "
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-1188: Initialization with Hard-Coded Network Resource Configuration Data
## Quick Start

This skill provides the fix pattern for CWE-1188. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-1188 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## Overview
A component is initialized with hard-coded default values (credentials, URLs, encryption keys) that are insecure or intended only for development, creating a security weakness in production.

## Vulnerability Pattern
```java
// VULNERABLE: Hardcoded default credentials
public class DatabaseConfig {
    private static final String DEFAULT_PASSWORD = "admin123";  // Hardcoded!
    
    public void init() {
        if (System.getProperty("db.password") == null) {
            System.setProperty("db.password", DEFAULT_PASSWORD);  // Falls back to weak default
        }
    }
}

// VULNERABLE: Hardcoded encryption key
private static final String ENCRYPTION_KEY = "mykey";  // CONSTANT

// VULNERABLE: Development settings shipped to production
public class OtpConfig {
    public static final String OTP_KEY = "DSS_IS_BEST";  // Hardcoded, visible in code
}
```

## Fix Strategy

1. **Remove all hardcoded defaults** — require explicit configuration
2. **Use environment variables** for defaults (loaded at runtime, not compile time)
3. **Use secure credential storage** (vaults) instead of constants
4. **Fail-fast if required config is missing** — don't silently use weak defaults
5. **Separate dev/prod configuration** — never ship dev defaults to production

## Remediation Examples

### Option A: Environment-based defaults
```java
// FIXED: Read from environment variable, no hardcoded default
public class DatabaseConfig {
    public void init() {
        String password = System.getenv("DB_PASSWORD");
        if (password == null) {
            throw new IllegalStateException("DB_PASSWORD environment variable must be set");
        }
        System.setProperty("db.password", password);
    }
}
```

### Option B: External configuration file
```java
// FIXED: Load from external config file (not in code)
@Configuration
@PropertySource("file:/etc/app/config.properties")
public class AppConfig {
    @Value("${db.password}")
    private String dbPassword;
    
    @PostConstruct
    public void validate() {
        if (dbPassword == null || dbPassword.isEmpty()) {
            throw new IllegalStateException("db.password must be configured");
        }
    }
}
```

### Option C: Vault for sensitive values
```java
// FIXED: Fetch encryption key from vault at runtime
public class CryptoConfig {
    public String getEncryptionKey() {
        VaultClient vault = new VaultClient();
        return vault.getSecret("app/encryption-key");  // No hardcoded value
    }
}
```

### Option D: Profile-specific defaults
```java
// FIXED: Different defaults per environment
@Configuration
@Profile("!production")
public class DevConfig {
    @Bean
    public String encryptionKey() {
        return "dev-key-only";  // OK for dev, not shipped to prod
    }
}

@Configuration
@Profile("production")
public class ProdConfig {
    @Bean
    public String encryptionKey() {
        return System.getenv("ENCRYPTION_KEY");  // Must be set in prod
    }
}
```

## Implementation Checklist
- [ ] Search for static final String assignments of sensitive data
- [ ] Identify any hardcoded passwords, keys, API endpoints
- [ ] Replace with environment variables or vault lookups
- [ ] Add startup validation to ensure required configs are provided
- [ ] Test: production build should fail if required env vars are not set
- [ ] Verify dev defaults are not shipped to production

## Key Points
- **Hardcoded values in code are visible to anyone with repo access** — source code is not a secret store
- **Fail-fast is better than failing silently** — invalid config should crash at startup
- **Environment variables work at deployment time** — not compile time
- **Vaults are the right choice** for secrets — Hashicorp Vault, AWS Secrets Manager
- **Severity**: High — weak defaults directly compromise security

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
