---
name: cwe-328-weak-random
description: "CWE-328: Use of Insufficiently Random Values Remediation — Remediate weak random number generation by using cryptographically secure random sources instead of weak PRNGs (like `random()`, `Math.random()`, etc."
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-328: Use of Insufficiently Random Values Remediation
## Quick Start

This skill provides the fix pattern for CWE-328. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-328 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-328
- **CWE Name**: Use of Insufficiently Random Values
- **Severity**: High
- **OWASP Category**: A02:2021 - Cryptographic Failures

## Purpose

Remediate weak random number generation by using cryptographically secure random sources instead of weak PRNGs (like `random()`, `Math.random()`, etc.). Weak randomness can lead to predictable tokens, IDs, and keys.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file.
  - `line_number` (integer, required): The 1-based line number.
  - `cwe_id` (string, required): Must be `CWE-328`.

## Steps

1. **Identify weak random** generators (Math.random(), random.random(), etc.).
2. **Replace with crypto** random (os.urandom(), crypto.getRandomBytes(), etc.).
3. **Apply the edit.**

## Output Format

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "changes": [
    {
      "line_number": "<integer>",
      "weak_rng": "string",
      "strong_rng": "string"
    }
  ],
  "weak_rngs_fixed": "<integer>",
  "error": "null or string"
}
```

## Vulnerable Pattern

```python
import random
token = random.randint(0, 999999)  # Predictable!

import secrets
```

## Fix Pattern

Replace with cryptographically secure random:
- Python: `secrets.token_hex()`, `secrets.randbelow()`
- Java: `java.security.SecureRandom`
- JavaScript: `crypto.getRandomValues()`

## Language-Specific Examples

### Python

**Before (vulnerable):**
```python
import random

def generate_session_token():
    return str(random.randint(100000, 999999))  # Weak!
```

**After (fixed):**
```python
import secrets

def generate_session_token():
    return secrets.token_hex(16)  # Cryptographically secure
```

### Java

**Before (vulnerable):**
```java
Random rand = new Random();
String token = String.valueOf(rand.nextInt(999999));  // Weak!
```

**After (fixed):**
```java
import java.security.SecureRandom;

SecureRandom rand = new SecureRandom();
byte[] tokenBytes = new byte[16];
rand.nextBytes(tokenBytes);
String token = Base64.getEncoder().encodeToString(tokenBytes);  // Secure
```

### JavaScript

**Before (vulnerable):**
```javascript
function generateToken() {
    return Math.floor(Math.random() * 999999).toString();  // Weak!
}
```

**After (fixed):**
```javascript
function generateToken() {
    const buffer = new Uint8Array(16);
    crypto.getRandomValues(buffer);
    return Array.from(buffer, (b) => b.toString(16).padStart(2, '0')).join('');
}
```

## Testing Guidance

1. **Verify randomness**: Check tokens are different each call.
2. **Verify unpredictability**: Tokens should not follow patterns.
3. **Verify sufficient entropy**: Ensure sufficient random bits used.

## Constraints

- Always use cryptographically secure RNG for security purposes.
- Use adequate bit length (minimum 128 bits for tokens).
- Never use Math.random() or similar for security.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
