---
name: cwe-532-sensitive-log
description: "CWE-532: Insertion of Sensitive Information into Log File Remediation — Remediate sensitive information being logged by adding sanitization filters to remove or mask passwords, API keys, tokens, and personal data before lo"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-532: Insertion of Sensitive Information into Log File Remediation
## Quick Start

This skill provides the fix pattern for CWE-532. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-532 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-532
- **CWE Name**: Insertion of Sensitive Information into Log File
- **Severity**: Medium
- **OWASP Category**: A09:2021 - Security Logging and Monitoring Failures

## Purpose

Remediate sensitive information being logged by adding sanitization filters to remove or mask passwords, API keys, tokens, and personal data before logging.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file.
  - `line_number` (integer, required): The 1-based line number.
  - `cwe_id` (string, required): Must be `CWE-532`.

## Steps

1. **Identify sensitive data** being logged.
   - Passwords, API keys, tokens, credit cards, SSN, etc.

2. **Add sanitization** before logging.
   - Mask sensitive fields (e.g., password: `***`).
   - Or exclude sensitive fields from logs.

3. **Apply the edit.**
   - Use `Edit` to add sanitization logic.

## Output Format

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "sensitive_field": "<string: field being masked>",
      "sanitization_method": "mask | exclude | truncate"
    }
  ],
  "log_statements_fixed": "<integer>",
  "warnings": ["<string: manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

## Vulnerable Pattern

```python
logger.info(f"Login attempt: username={username}, password={password}")
logger.debug(f"API key: {api_key}")
logger.error(f"User {user_id} with SSN {ssn} failed validation")
```

## Fix Pattern

1. Create a sanitization function.
2. Apply it to objects before logging.
3. Mask sensitive fields.

## Language-Specific Examples

### Python

**Before (vulnerable):**
```python
import logging

logger = logging.getLogger(__name__)

def login(username, password):
    logger.info(f"Login attempt: {username}, {password}")  # VULNERABLE!
    # ... authenticate ...

def process_payment(card_number, cvv):
    logger.debug(f"Processing card: {card_number}, CVV: {cvv}")  # VULNERABLE!
```

**After (fixed):**
```python
import logging
import json

logger = logging.getLogger(__name__)

def sanitize_for_logging(data):
    """Remove sensitive fields from data before logging."""
    sensitive_fields = {'password', 'api_key', 'token', 'cvv', 'ssn', 'credit_card'}
    if isinstance(data, dict):
        sanitized = data.copy()
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = '***'
        return sanitized
    return data

def login(username, password):
    log_data = sanitize_for_logging({'username': username, 'password': password})
    logger.info(f"Login attempt: {log_data}")
    # ... authenticate ...

def process_payment(card_number, cvv):
    log_data = sanitize_for_logging({'card_number': card_number, 'cvv': cvv})
    logger.debug(f"Processing payment: {log_data}")
```

### Java

**Before (vulnerable):**
```java
public void login(String username, String password) {
    logger.info("Login: " + username + " / " + password);  // VULNERABLE!
}

public void processPayment(String cardNumber, String cvv) {
    logger.debug("Card: " + cardNumber + ", CVV: " + cvv);  // VULNERABLE!
}
```

**After (fixed):**
```java
import org.apache.commons.lang3.StringUtils;

public class LogSanitizer {
    private static final Set<String> SENSITIVE_FIELDS = new HashSet<>(
        Arrays.asList("password", "apiKey", "token", "cvv", "ssn", "creditCard")
    );

    public static String sanitize(String fieldName, String value) {
        if (SENSITIVE_FIELDS.contains(fieldName)) {
            return "***";
        }
        return value;
    }

    public static Map<String, Object> sanitizeMap(Map<String, Object> data) {
        Map<String, Object> sanitized = new HashMap<>(data);
        for (String field : SENSITIVE_FIELDS) {
            if (sanitized.containsKey(field)) {
                sanitized.put(field, "***");
            }
        }
        return sanitized;
    }
}

public void login(String username, String password) {
    String logPassword = LogSanitizer.sanitize("password", password);
    logger.info("Login: " + username + " / " + logPassword);
}

public void processPayment(String cardNumber, String cvv) {
    Map<String, Object> logData = new HashMap<>();
    logData.put("cardNumber", cardNumber);
    logData.put("cvv", cvv);
    logger.debug("Payment: " + LogSanitizer.sanitizeMap(logData));
}
```

### JavaScript

**Before (vulnerable):**
```javascript
function login(username, password) {
    console.log(`Login: ${username} / ${password}`);  // VULNERABLE!
}

function processPayment(cardNumber, cvv) {
    logger.debug(`Card: ${cardNumber}, CVV: ${cvv}`);  // VULNERABLE!
}
```

**After (fixed):**
```javascript
const SENSITIVE_FIELDS = new Set(['password', 'apiKey', 'token', 'cvv', 'ssn', 'creditCard']);

function sanitizeForLogging(data) {
    if (typeof data === 'object' && data !== null) {
        const sanitized = { ...data };
        for (const key in sanitized) {
            if (SENSITIVE_FIELDS.has(key)) {
                sanitized[key] = '***';
            }
        }
        return sanitized;
    }
    return data;
}

function login(username, password) {
    const logData = sanitizeForLogging({ username, password });
    console.log(`Login: ${JSON.stringify(logData)}`);
}

function processPayment(cardNumber, cvv) {
    const logData = sanitizeForLogging({ cardNumber, cvv });
    logger.debug(`Payment: ${JSON.stringify(logData)}`);
}
```

## Testing Guidance

1. **Verify sensitive data is masked** in logs.
2. **Verify non-sensitive data is still logged** completely.
3. **Verify logs don't contain actual passwords/keys/tokens**.

## Common Mistakes

1. **Partial masking** (e.g., only first char) - should be completely masked.
2. **Forgetting some sensitive fields** - need comprehensive list.
3. **Logging before sanitization** - sanitize early.
4. **Only sanitizing in some places** - apply consistently.

## Constraints

- Sensitive data must be completely masked (not just first char).
- Non-sensitive logging should not be affected.
- Sanitization should be applied consistently across all loggers.
## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
