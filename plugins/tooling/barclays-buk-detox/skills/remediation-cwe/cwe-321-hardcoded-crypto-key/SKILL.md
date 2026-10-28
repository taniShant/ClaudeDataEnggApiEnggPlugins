---
name: cwe-321-hardcoded-crypto-key
description: "CWE-321: Use of Hard-coded Cryptographic Key Remediation — Remediate hard-coded cryptographic keys by moving them to secure external storage (environment variables, secrets vaults, configuration servers). Hard"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-321: Use of Hard-coded Cryptographic Key Remediation
## Quick Start

This skill provides the fix pattern for CWE-321. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-321 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-321
- **CWE Name**: Use of Hard-coded Cryptographic Key
- **Severity**: High
- **OWASP Category**: A02:2021 - Cryptographic Failures

## Purpose

Remediate hard-coded cryptographic keys by moving them to secure external storage (environment variables, secrets vaults, configuration servers). Hard-coded keys can be exposed through source code leaks, reverse engineering, or supply chain attacks, compromising all data encrypted with those keys.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file with hard-coded keys.
  - `line_number` (integer, required): The 1-based line number.
  - `cwe_id` (string, required): Must be `CWE-321`.

## Steps

1. **Identify hard-coded keys** in the source code.
   - Strings that look like encryption keys, API keys, or credentials.
   - Common patterns: `SECRET_KEY = "..."`, `API_KEY = "..."`, `PASSWORD = "..."`.

2. **Replace with environment variable or secrets loader.**
   - For development: Use environment variables.
   - For production: Use secrets management (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault).

3. **Add key rotation capability.**
   - Ensure the application can load new keys without code changes.

4. **Audit for key exposure.**
   - Check git history for leaked keys.
   - Invalidate and rotate any exposed keys.

5. **Apply the edit.**
   - Use `Edit` to replace hard-coded keys with environment variable references.

## Output Format

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "original_code": "<string: hard-coded key>",
      "fixed_code": "<string: environment variable reference>",
      "key_name": "<string: environment variable name>"
    }
  ],
  "exposed_keys": ["<string: potentially exposed key hashes>"],
  "environment_variables_needed": ["<string: env var names>"],
  "warnings": ["<string: manual steps needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

## Vulnerable Pattern

Hard-coded cryptographic keys appear directly in source code:

```python
SECRET_KEY = "my-secret-key-12345"
encryption_key = b'0123456789abcdef'
api_key = "sk_live_abc123xyz"

cipher = AES.new(encryption_key)
```

## Fix Pattern

1. Extract the key to an environment variable.
2. Load the key at runtime from the environment.
3. Use secure key storage for production.
4. Rotate keys periodically.

## Language-Specific Examples

### Python

**Before (vulnerable):**
```python
from cryptography.fernet import Fernet

SECRET_KEY = "my-secret-encryption-key-12345"

def encrypt_data(data):
    cipher = Fernet(SECRET_KEY.encode())
    return cipher.encrypt(data)
```

**After (fixed):**
```python
import os
from cryptography.fernet import Fernet

def get_secret_key():
    key = os.environ.get('ENCRYPTION_KEY')
    if not key:
        raise ValueError("ENCRYPTION_KEY environment variable not set")
    return key.encode()

def encrypt_data(data):
    key = get_secret_key()
    cipher = Fernet(key)
    return cipher.encrypt(data)
```

### Java

**Before (vulnerable):**
```java
public class CryptoUtil {
    private static final String SECRET_KEY = "my-secret-key-12345";

    public static byte[] encrypt(byte[] data) throws Exception {
        SecretKey key = new SecretKeySpec(SECRET_KEY.getBytes(), 0, SECRET_KEY.getBytes().length, "AES");
        Cipher cipher = Cipher.getInstance("AES");
        cipher.init(Cipher.ENCRYPT_MODE, key);
        return cipher.doFinal(data);
    }
}
```

**After (fixed):**
```java
public class CryptoUtil {
    private static String getSecretKey() {
        String key = System.getenv("ENCRYPTION_KEY");
        if (key == null) {
            throw new RuntimeException("ENCRYPTION_KEY environment variable not set");
        }
        return key;
    }

    public static byte[] encrypt(byte[] data) throws Exception {
        String keyStr = getSecretKey();
        SecretKey key = new SecretKeySpec(keyStr.getBytes(), 0, keyStr.getBytes().length, "AES");
        Cipher cipher = Cipher.getInstance("AES");
        cipher.init(Cipher.ENCRYPT_MODE, key);
        return cipher.doFinal(data);
    }
}
```

### JavaScript

**Before (vulnerable):**
```javascript
const crypto = require('crypto');

const SECRET_KEY = 'my-secret-key-12345';

function encryptData(data) {
    const cipher = crypto.createCipher('aes-256-cbc', SECRET_KEY);
    let encrypted = cipher.update(data, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    return encrypted;
}
```

**After (fixed):**
```javascript
const crypto = require('crypto');

function getSecretKey() {
    const key = process.env.ENCRYPTION_KEY;
    if (!key) {
        throw new Error('ENCRYPTION_KEY environment variable not set');
    }
    return key;
}

function encryptData(data) {
    const key = getSecretKey();
    const cipher = crypto.createCipher('aes-256-cbc', key);
    let encrypted = cipher.update(data, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    return encrypted;
}
```

## Testing Guidance

1. **Verify environment variable is read correctly** when set.
2. **Verify error when environment variable is not set**.
3. **Test with different key values** to ensure the key loading mechanism works.
4. **Verify encrypted data can be decrypted** after the fix.

## Common Mistakes

1. **Hard-coding the environment variable default.** Don't do: `key = os.environ.get('KEY', 'default-key')`.
2. **Leaving comments with the key.** Remove any comments that reveal the key.
3. **Not rotating keys.** Implement key rotation policy.
4. **Key in configuration files.** Configuration files can be exposed. Use environment-only storage.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **Environment variable not set** | Raise an error early, don't proceed |
| **Invalid key format** | Validate key format and length |
| **Multiple hard-coded keys** | Replace all with environment variables |

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
