---
name: cwe-312-cleartext-storage
description: "CWE-312: Cleartext Storage of Sensitive Information Remediation — Remediate cleartext storage of sensitive information by encrypting all sensitive data at rest (database, files, caches). Sensitive data includes passw"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-312: Cleartext Storage of Sensitive Information Remediation
## Quick Start

This skill provides the fix pattern for CWE-312. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-312 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-312
- **CWE Name**: Cleartext Storage of Sensitive Information
- **Severity**: High
- **OWASP Category**: A02:2021 - Cryptographic Failures

## Purpose

Remediate cleartext storage of sensitive information by encrypting all sensitive data at rest (database, files, caches). Sensitive data includes passwords, API keys, credit card numbers, tokens, and personal information.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file.
  - `line_number` (integer, required): The 1-based line number.
  - `cwe_id` (string, required): Must be `CWE-312`.

## Steps

1. **Identify sensitive data** being stored in cleartext.
   - Passwords, API keys, tokens, PII, credit cards.

2. **Add encryption** before storage.
   - Use strong encryption (AES-256).
   - Store encryption key securely (not in the cleartext data).

3. **Add decryption** when reading.
   - Decrypt only when necessary.

4. **Apply the edit.**
   - Use `Edit` to add encryption/decryption calls.

## Output Format

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "data_field": "<string: field being encrypted>",
      "encryption_method": "<string: e.g., AES-256>",
      "key_storage": "<string: how key is stored>"
    }
  ],
  "functions_modified": "<integer>",
  "warnings": ["<string: manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

## Vulnerable Pattern

```python
# Storing password in cleartext
user = {
    'username': username,
    'password': password,  # VULNERABLE!
    'api_key': api_key     # VULNERABLE!
}
db.save_user(user)
```

## Fix Pattern

1. Hash passwords using bcrypt/argon2.
2. Encrypt other sensitive data using AES-256.
3. Never store encryption keys with the data.

## Language-Specific Examples

### Python

**Before (vulnerable):**
```python
def save_user(username, password, api_key):
    user = {
        'username': username,
        'password': password,  # Stored in cleartext!
        'api_key': api_key     # Stored in cleartext!
    }
    db.save(user)
```

**After (fixed):**
```python
import bcrypt
from cryptography.fernet import Fernet
import os

def get_encryption_key():
    key = os.environ.get('ENCRYPTION_KEY')
    if not key:
        raise ValueError("ENCRYPTION_KEY not set")
    return key.encode()

def save_user(username, password, api_key):
    # Hash password with bcrypt
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    # Encrypt API key
    cipher = Fernet(get_encryption_key())
    encrypted_api_key = cipher.encrypt(api_key.encode()).decode()

    user = {
        'username': username,
        'password_hash': password_hash,
        'api_key_encrypted': encrypted_api_key
    }
    db.save(user)

def verify_user_password(username, password):
    user = db.get_user(username)
    return bcrypt.checkpw(password.encode(), user['password_hash'].encode())

def get_user_api_key(username):
    user = db.get_user(username)
    cipher = Fernet(get_encryption_key())
    return cipher.decrypt(user['api_key_encrypted'].encode()).decode()
```

### Java

**Before (vulnerable):**
```java
public void saveUser(String username, String password, String apiKey) {
    User user = new User();
    user.setUsername(username);
    user.setPassword(password);  // Stored in cleartext!
    user.setApiKey(apiKey);      // Stored in cleartext!
    userRepository.save(user);
}
```

**After (fixed):**
```java
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;
import org.apache.commons.codec.binary.Base64;

public class UserService {
    private BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    public void saveUser(String username, String password, String apiKey) {
        String passwordHash = passwordEncoder.encode(password);
        String encryptedApiKey = encryptApiKey(apiKey);

        User user = new User();
        user.setUsername(username);
        user.setPasswordHash(passwordHash);
        user.setApiKeyEncrypted(encryptedApiKey);
        userRepository.save(user);
    }

    private String encryptApiKey(String apiKey) throws Exception {
        String key = System.getenv("ENCRYPTION_KEY");
        if (key == null) throw new RuntimeException("ENCRYPTION_KEY not set");

        SecretKeySpec keySpec = new SecretKeySpec(key.getBytes(), 0, key.getBytes().length, "AES");
        Cipher cipher = Cipher.getInstance("AES");
        cipher.init(Cipher.ENCRYPT_MODE, keySpec);
        byte[] encrypted = cipher.doFinal(apiKey.getBytes());
        return Base64.encodeBase64String(encrypted);
    }

    public boolean verifyPassword(String username, String password) {
        User user = userRepository.findByUsername(username);
        return passwordEncoder.matches(password, user.getPasswordHash());
    }
}
```

### JavaScript

**Before (vulnerable):**
```javascript
async function saveUser(username, password, apiKey) {
    const user = {
        username,
        password,  // Stored in cleartext!
        apiKey     // Stored in cleartext!
    };
    await db.save(user);
}
```

**After (fixed):**
```javascript
const crypto = require('crypto');
const bcrypt = require('bcrypt');

function getEncryptionKey() {
    const key = process.env.ENCRYPTION_KEY;
    if (!key) throw new Error('ENCRYPTION_KEY not set');
    return key;
}

async function saveUser(username, password, apiKey) {
    const passwordHash = await bcrypt.hash(password, 10);
    const encryptedApiKey = encryptApiKey(apiKey);

    const user = {
        username,
        passwordHash,
        apiKeyEncrypted: encryptedApiKey
    };
    await db.save(user);
}

function encryptApiKey(apiKey) {
    const key = getEncryptionKey();
    const cipher = crypto.createCipher('aes-256-cbc', key);
    let encrypted = cipher.update(apiKey, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    return encrypted;
}

async function verifyPassword(username, password) {
    const user = await db.getUser(username);
    return bcrypt.compare(password, user.passwordHash);
}
```

## Testing Guidance

1. **Verify password hashing**: Check database that passwords are hashed, not stored in cleartext.
2. **Verify encryption**: Check database that API keys are encrypted.
3. **Verify decryption works**: Test that encrypted data can be decrypted correctly.
4. **Verify password validation**: Test password verification against hash.

## Common Mistakes

1. **Using weak encryption** (DES, MD5).
2. **Storing encryption key with the data.**
3. **Using encryption instead of hashing for passwords** (use bcrypt/argon2 for passwords).
4. **Not rotating encryption keys.**
5. **Encrypting cleartext backups** - ensure backups are also encrypted.

## Constraints

- Passwords must be hashed, not encrypted.
- API keys and tokens must be encrypted.
- Encryption keys must be managed securely and not stored in code.
- All sensitive data at rest must be encrypted or hashed.
## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
