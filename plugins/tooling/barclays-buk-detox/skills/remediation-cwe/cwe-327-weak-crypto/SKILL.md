---
name: cwe-327-weak-crypto
description: "CWE-327: Use of Broken Cryptographic Algorithm Remediation — Remediate the use of broken or weak cryptographic algorithms by replacing them with modern, secure alternatives. This skill transforms code that uses "
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-327: Use of Broken Cryptographic Algorithm Remediation
## Quick Start

This skill provides the fix pattern for CWE-327. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-327 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-327
- **CWE Name**: Use of a Broken or Risky Cryptographic Algorithm
- **Severity**: High
- **OWASP Category**: A02:2021 — Cryptographic Failures

## Purpose

Remediate the use of broken or weak cryptographic algorithms by replacing them with modern, secure alternatives. This skill transforms code that uses MD5, SHA-1, DES, RC4, or other deprecated algorithms for security-sensitive purposes into code that uses SHA-256+ for hashing, AES-256 for encryption, and bcrypt/argon2 for password hashing. It distinguishes between security-sensitive uses (authentication, integrity verification, password storage) and non-security uses (checksums, cache keys) to avoid unnecessary changes.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the affected file.
  - `line_number` (integer, required): Line where the weak cryptographic algorithm was detected.
  - `code_snippet` (string, optional): The vulnerable code flagged by the scanner.
  - `cwe_id` (string, required): Must be `CWE-327`.
- **code_context** (required, JSON object): Output from the `code_context_analyzer` skill.
- **repo_root** (optional, string): Absolute path to the repository root.

## Vulnerable Pattern

Weak cryptographic algorithms are used when code employs deprecated or broken algorithms (MD5, SHA-1, DES, 3DES, RC4, Blowfish) for security-critical operations such as password hashing, digital signatures, message authentication, or data encryption. These algorithms have known practical attacks that undermine their security guarantees.

### Detection Patterns

**General indicators:**
- Use of MD5 or SHA-1 for password hashing, token generation, or integrity verification.
- Use of DES, 3DES, RC4, or Blowfish for encryption.
- Direct hashing of passwords without a salt or work factor.
- Use of ECB mode for block ciphers.

**Regex patterns for detection:**
```
# Python hashlib weak algorithms
hashlib\.(md5|sha1)\s*\(
hashlib\.new\s*\(\s*['"](?:md5|sha1|sha-1|MD5|SHA1)['"]\s*\)
# Python DES/RC4
DES\.(new|encrypt)|ARC4\.new|Blowfish\.new
# Java MessageDigest weak algorithms
MessageDigest\.getInstance\s*\(\s*['"](?:MD5|SHA-1|SHA1)['"]\s*\)
# Java weak ciphers
Cipher\.getInstance\s*\(\s*['"](?:DES|DESede|RC4|Blowfish|AES/ECB)['"]\s*\)
# Node.js crypto weak algorithms
crypto\.createHash\s*\(\s*['"](?:md5|sha1)['"]\s*\)
crypto\.createCipher\s*\(\s*['"](?:des|des-ede3|rc4|bf)['"]\s*\)
```

**Important distinction**: MD5 and SHA-1 used for non-security purposes (e.g., generating cache keys, checksums for data deduplication, ETag generation) may not need to be changed. Analyze the context before applying fixes.

## Fix Pattern

### General Approach

1. **For general-purpose hashing** (integrity checks, signatures): Replace MD5/SHA-1 with SHA-256 or SHA-3.
2. **For password hashing**: Replace any direct hash (MD5, SHA-1, SHA-256) with bcrypt, argon2, or scrypt. These are designed for password storage with built-in salting and configurable work factors.
3. **For encryption**: Replace DES/3DES/RC4/Blowfish with AES-256-GCM or AES-256-CBC with HMAC. Never use ECB mode.
4. **For HMAC/MAC**: Replace HMAC-MD5 or HMAC-SHA1 with HMAC-SHA256.

### Step-by-Step Transformation

1. Identify the cryptographic operation (hashing, password hashing, encryption, HMAC).
2. Determine the security context (is this for authentication, integrity, password storage, or a non-security use?).
3. Choose the appropriate modern algorithm.
4. Replace the algorithm call, preserving the input/output interface as much as possible.
5. For password hashing changes, plan a migration strategy for existing stored hashes.

## Language-Specific Examples

### Python (hashlib — general hashing)

**Before (vulnerable):**
```python
import hashlib

def compute_hash(data: str) -> str:
    return hashlib.md5(data.encode()).hexdigest()

def verify_integrity(data: str, expected_hash: str) -> bool:
    return hashlib.sha1(data.encode()).hexdigest() == expected_hash
```

**After (fixed):**
```python
import hashlib

def compute_hash(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()

def verify_integrity(data: str, expected_hash: str) -> bool:
    return hashlib.sha256(data.encode()).hexdigest() == expected_hash
```

**Explanation:** Replace `hashlib.md5` and `hashlib.sha1` with `hashlib.sha256`. SHA-256 provides 128-bit collision resistance and has no known practical attacks. The interface remains identical (both return hex digest strings), though the output length changes (64 hex characters for SHA-256 vs. 32 for MD5 or 40 for SHA-1).

### Python (bcrypt — password hashing)

**Before (vulnerable):**
```python
import hashlib

def hash_password(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()

def verify_password(password: str, stored_hash: str) -> bool:
    return hashlib.md5(password.encode()).hexdigest() == stored_hash
```

**After (fixed):**
```python
import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(password: str, stored_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
```

**Explanation:** Replace MD5 password hashing with bcrypt. Bcrypt includes automatic salting and a configurable work factor (`rounds=12` is a reasonable default as of 2024). `bcrypt.checkpw` handles the salt extraction and comparison. Add `bcrypt` to project dependencies.

### Python (argon2 — password hashing, preferred)

**Before (vulnerable):**
```python
import hashlib

def hash_password(password: str, salt: str) -> str:
    return hashlib.sha1((salt + password).encode()).hexdigest()
```

**After (fixed):**
```python
from argon2 import PasswordHasher

ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
)

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        return ph.verify(stored_hash, password)
    except Exception:
        return False
```

**Explanation:** Argon2 is the winner of the Password Hashing Competition and is the recommended algorithm for new projects. It provides resistance against GPU-based and memory-hard attacks. The salt is generated and embedded automatically. Add `argon2-cffi` to project dependencies.

### Java (MessageDigest — general hashing)

**Before (vulnerable):**
```java
import java.security.MessageDigest;

public String computeHash(String data) throws Exception {
    MessageDigest md = MessageDigest.getInstance("MD5");
    byte[] digest = md.digest(data.getBytes("UTF-8"));
    StringBuilder sb = new StringBuilder();
    for (byte b : digest) {
        sb.append(String.format("%02x", b));
    }
    return sb.toString();
}
```

**After (fixed):**
```java
import java.security.MessageDigest;

public String computeHash(String data) throws Exception {
    MessageDigest md = MessageDigest.getInstance("SHA-256");
    byte[] digest = md.digest(data.getBytes("UTF-8"));
    StringBuilder sb = new StringBuilder();
    for (byte b : digest) {
        sb.append(String.format("%02x", b));
    }
    return sb.toString();
}
```

**Explanation:** Replace `"MD5"` with `"SHA-256"` in the `MessageDigest.getInstance` call. The rest of the code remains identical. SHA-256 is available in all modern Java runtimes.

### Java (BCrypt — password hashing)

**Before (vulnerable):**
```java
import java.security.MessageDigest;

public String hashPassword(String password) throws Exception {
    MessageDigest md = MessageDigest.getInstance("SHA-1");
    byte[] digest = md.digest(password.getBytes("UTF-8"));
    StringBuilder sb = new StringBuilder();
    for (byte b : digest) {
        sb.append(String.format("%02x", b));
    }
    return sb.toString();
}
```

**After (fixed):**
```java
import org.mindrot.jbcrypt.BCrypt;

public String hashPassword(String password) {
    return BCrypt.hashpw(password, BCrypt.gensalt(12));
}

public boolean verifyPassword(String password, String storedHash) {
    return BCrypt.checkpw(password, storedHash);
}
```

**Explanation:** Replace `MessageDigest` with `BCrypt` from the `jBCrypt` library. BCrypt handles salting automatically and uses a work factor of 12. Add `org.mindrot:jbcrypt` to Maven/Gradle dependencies.

### Node.js (crypto — general hashing)

**Before (vulnerable):**
```javascript
const crypto = require('crypto');

function computeHash(data) {
    return crypto.createHash('md5').update(data).digest('hex');
}

function verifyToken(token, expectedHash) {
    const hash = crypto.createHash('sha1').update(token).digest('hex');
    return hash === expectedHash;
}
```

**After (fixed):**
```javascript
const crypto = require('crypto');

function computeHash(data) {
    return crypto.createHash('sha256').update(data).digest('hex');
}

function verifyToken(token, expectedHash) {
    const hash = crypto.createHash('sha256').update(token).digest('hex');
    return crypto.timingSafeEqual(
        Buffer.from(hash, 'hex'),
        Buffer.from(expectedHash, 'hex')
    );
}
```

**Explanation:** Replace `'md5'` and `'sha1'` with `'sha256'` in `crypto.createHash`. Also replace direct string comparison with `crypto.timingSafeEqual` for constant-time comparison to prevent timing attacks.

### Node.js (bcrypt — password hashing)

**Before (vulnerable):**
```javascript
const crypto = require('crypto');

function hashPassword(password) {
    return crypto.createHash('md5').update(password).digest('hex');
}

function verifyPassword(password, storedHash) {
    const hash = crypto.createHash('md5').update(password).digest('hex');
    return hash === storedHash;
}
```

**After (fixed):**
```javascript
const bcrypt = require('bcrypt');

const SALT_ROUNDS = 12;

async function hashPassword(password) {
    return bcrypt.hash(password, SALT_ROUNDS);
}

async function verifyPassword(password, storedHash) {
    return bcrypt.compare(password, storedHash);
}
```

**Explanation:** Replace MD5 hashing with bcrypt. The `bcrypt` npm package provides automatic salting and configurable work factor. Functions become async because bcrypt operations are computationally expensive and should not block the event loop. Add `bcrypt` to `package.json`.

## Testing Guidance

### Verifying the Fix Eliminates the Vulnerability

1. **Algorithm verification**: Confirm the output length matches the new algorithm (SHA-256 produces 64 hex characters, bcrypt produces a 60-character string starting with `$2b$`).
2. **Grep for remnants**: Search the entire project for remaining uses of `md5`, `sha1`, `DES`, `RC4`, `Blowfish`, `ECB` in a security context.
3. **Hash consistency**: If the hash is used for verification (e.g., API signatures), ensure both the producer and consumer use the new algorithm.

### Verifying Existing Functionality Is Preserved

1. **Non-password hashing**: Compute hashes of known inputs and verify the output format is compatible with downstream consumers (databases, APIs, etc.).
2. **Password verification**: Ensure existing stored password hashes can still be verified during a migration period (see Common Mistakes).
3. **Performance**: bcrypt and argon2 are intentionally slow. Verify that the increased computation time is acceptable for the use case (especially in high-throughput scenarios).

### Semgrep Rules

After the fix, the following Semgrep patterns should no longer match:
```yaml
rules:
  - id: weak-hash-md5
    patterns:
      - pattern-either:
          - pattern: hashlib.md5(...)
          - pattern: MessageDigest.getInstance("MD5")
          - pattern: crypto.createHash('md5')
    message: "MD5 is cryptographically broken"
    severity: ERROR
  - id: weak-hash-sha1
    patterns:
      - pattern-either:
          - pattern: hashlib.sha1(...)
          - pattern: MessageDigest.getInstance("SHA-1")
          - pattern: crypto.createHash('sha1')
    message: "SHA-1 is cryptographically weak"
    severity: WARNING
  - id: password-hash-without-bcrypt
    patterns:
      - pattern-either:
          - pattern: hashlib.$FUNC($PASSWORD.encode())
          - pattern: MessageDigest.getInstance($ALG).digest($PASSWORD.getBytes(...))
          - pattern: crypto.createHash($ALG).update($PASSWORD)
    message: "Passwords should be hashed with bcrypt or argon2"
    severity: ERROR
```

## Common Mistakes

1. **Replacing MD5 with SHA-256 for password hashing**: SHA-256 is a fast hash and is not suitable for password storage. Use bcrypt or argon2 for passwords. SHA-256 is fine for general-purpose integrity hashing.
2. **Breaking existing hash verification**: If stored hashes exist (e.g., in a database), changing the algorithm will invalidate all existing hashes. Implement a migration strategy: verify with the old algorithm, then re-hash with the new algorithm on successful login.
3. **Not updating both producer and consumer**: If one service produces hashes and another verifies them, both must be updated simultaneously.
4. **Using a fixed salt for bcrypt**: `bcrypt.gensalt()` generates a random salt each time. Never use a hardcoded salt.
5. **Setting bcrypt work factor too low**: A work factor below 10 is too fast for modern hardware. Use 12 as a minimum.
6. **Replacing non-security MD5/SHA-1**: If MD5 is used for cache keys or file deduplication (not security), the fix may be unnecessary and could cause cache invalidation. Analyze the context first.
7. **Using `createCipher` instead of `createCipheriv` in Node.js**: `crypto.createCipher` derives the key from a password using MD5 internally. Use `crypto.createCipheriv` with a properly derived key.
8. **Not using constant-time comparison**: When comparing hashes for authentication, use `hmac.compare_digest` (Python), `MessageDigest.isEqual` (Java), or `crypto.timingSafeEqual` (Node.js) to prevent timing attacks.

## Steps

1. Use `Read` to open the file at `vulnerability.file_path` and examine the `code_context` to identify the cryptographic operation and its purpose.
2. Determine the security context: is this password hashing, general integrity hashing, encryption, HMAC, or a non-security use?
3. If the purpose is unclear, use `Grep` to trace how the hash output is used (stored in a database password field? compared in an auth check? used as a cache key?).
4. Choose the appropriate replacement algorithm based on the use case.
5. Use `Edit` to replace the weak algorithm with the secure alternative.
6. If switching to bcrypt/argon2 for passwords, check whether a migration strategy is needed for existing stored hashes and note it in the output.
7. Use `Grep` to check for other instances of the same weak algorithm in the project.
8. Verify that the new algorithm's output format is compatible with any downstream consumers (database column size, API response format, etc.).

## Output Format

Return a JSON object:

```json
{
  "status": "fixed | failed | needs_review",
  "file_path": "<string: absolute path to the modified file>",
  "changes": [
    {
      "line_number": "<integer: line where the change was made>",
      "description": "<string: what was changed and why>"
    }
  ],
  "original_algorithm": "<string: the weak algorithm that was replaced>",
  "replacement_algorithm": "<string: the secure algorithm used>",
  "use_case": "<string: 'password_hashing' | 'integrity_hashing' | 'encryption' | 'hmac' | 'non_security'>",
  "migration_needed": "<boolean: whether existing stored hashes need migration>",
  "notes": "<string: any additional context, migration notes, or recommendations>"
}
```

### Success Indicator

The `status` field is `"fixed"` and the weak cryptographic algorithm has been replaced with a secure modern alternative appropriate for the use case.

### Failure Indicator

The `status` field is `"failed"` with a description of what prevented the fix.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **File not found** | Return `{"status": "failed", "reason": "File not found"}`. Do not retry. |
| **Cannot determine security context** | Default to treating the use as security-sensitive and apply the stronger fix. Set `status` to `"needs_review"`. |
| **Password hashing with existing stored hashes** | Apply the fix but set `status` to `"needs_review"` with detailed migration notes. |
| **Non-security use confirmed** | Set `status` to `"needs_review"` with a note that the use appears non-security-related. Let the reviewer decide. |
| **Third-party library enforces weak algorithm** | Note the constraint and recommend upgrading the library. Set `status` to `"needs_review"`. |

## Constraints

- **Preserve functionality**: The fix must not break hash verification, encryption/decryption, or authentication flows.
- **Context-aware**: Do not blindly replace all MD5/SHA-1 usage. Analyze whether the use is security-sensitive.
- **Password migration**: For password hashing changes, document the migration strategy. Do not delete the old verification code if existing hashes need to be supported during transition.
- **Minimal diff**: Change only the cryptographic algorithm and directly related code. Do not refactor unrelated logic.
- **Dependency management**: If adding bcrypt, argon2-cffi, or other dependencies, note them in the output for the pipeline to add to the project manifest.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Edit` for code modifications.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
