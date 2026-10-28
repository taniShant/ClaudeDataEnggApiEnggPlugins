---
name: cwe-311-missing-encryption
description: "CWE-311: Missing Encryption of Sensitive Data Remediation — Remediate missing encryption vulnerabilities by adding encryption for sensitive data at rest and in transit. This skill identifies code paths where se"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-311: Missing Encryption of Sensitive Data Remediation
## Quick Start

This skill provides the fix pattern for CWE-311. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-311 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-311
- **CWE Name**: Missing Encryption of Sensitive Data
- **Severity**: High
- **OWASP Category**: A02:2021 - Cryptographic Failures

## Purpose

Remediate missing encryption vulnerabilities by adding encryption for sensitive data at rest and in transit. This skill identifies code paths where sensitive data (credentials, PII, financial information, health records) is stored, transmitted, or processed without encryption, and applies appropriate encryption mechanisms including TLS for data in transit, AES-256 (or equivalent) for data at rest, and field-level encryption for sensitive database columns. It covers Python (cryptography, Fernet), Java (javax.crypto, JCA), and JavaScript/Node.js (crypto module).

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file containing the missing encryption vulnerability.
  - `line_number` (integer, required): The 1-based line number of the vulnerable code.
  - `cwe_id` (string, required): Must be `CWE-311`.
  - `code_snippet` (string, optional): The flagged code snippet.
  - `data_type` (string, optional): Type of sensitive data (`pii`, `credentials`, `financial`, `health`, `session`, `generic`). Auto-detected if not provided.
  - `encryption_context` (string, optional): `at_rest`, `in_transit`, or `both`. Auto-detected if not provided.
  - `context` (object, optional): Output from the `code_context_analyzer` skill.
- **repo_root** (optional, string): Absolute path to the repository root. Defaults to the current working directory.
- **language** (optional, string): Programming language (`python`, `java`, `javascript`). Auto-detected if not provided.

## Steps

1. **Read the vulnerable file and surrounding context.**
   - Use `Read` to open the file at `vulnerability.file_path`.
   - If `vulnerability.context` is provided, use it. Otherwise, read +/- 50 lines around `vulnerability.line_number`.

2. **Detect the language and identify the sensitive data.**
   - Determine what sensitive data is being stored or transmitted without encryption.
   - Classify the data: PII (names, SSNs, addresses), credentials, financial data (credit card numbers, bank accounts), health data, session tokens, etc.

3. **Determine the encryption context.**
   - **At rest**: Data stored in files, databases, caches, or logs without encryption.
   - **In transit**: Data transmitted over unencrypted channels (HTTP instead of HTTPS, unencrypted database connections, plain TCP sockets).
   - **Both**: Data that needs encryption in storage and during transmission.

4. **Apply the appropriate encryption fix.**
   - **Data at rest (field-level)**: Encrypt sensitive fields before storage and decrypt after retrieval using AES-256-GCM or an equivalent authenticated encryption scheme.
   - **Data at rest (file-level)**: Encrypt files containing sensitive data using a symmetric key stored securely.
   - **Data in transit**: Enforce TLS for all connections carrying sensitive data. Use HTTPS instead of HTTP, TLS-enabled database connections, encrypted message queues.
   - **Key management**: Use environment variables or a key management service for encryption keys. Never hardcode keys.

5. **Apply the edit.**
   - Use `Edit` to add encryption/decryption logic.
   - Add necessary imports (e.g., `from cryptography.fernet import Fernet`, `javax.crypto.Cipher`).
   - Preserve code formatting, indentation, and surrounding logic.

6. **Scan for similar patterns in the same file and related files.**
   - Use `Grep` to find other instances where the same type of sensitive data is stored or transmitted without encryption.
   - Apply the same fix to all instances.

7. **Verify the fix.**
   - Use `Read` to re-read the modified file and confirm encryption is applied correctly.
   - Confirm encryption keys are not hardcoded.

## Output Format

Return a JSON object:

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "data_type": "<string: pii | credentials | financial | health | session | generic>",
  "encryption_context": "<string: at_rest | in_transit | both>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "original_code": "<string: the unencrypted code>",
      "fixed_code": "<string: the encrypted replacement>",
      "fix_type": "field_encryption | file_encryption | tls_enforcement | connection_encryption"
    }
  ],
  "similar_patterns_fixed": "<integer: count of additional similar patterns fixed>",
  "imports_added": ["<string: any new import statements added>"],
  "key_management": "<string: description of how encryption keys are managed>",
  "warnings": ["<string: any warnings about manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

### Success Indicator

`status` is `"success"` and all sensitive data is encrypted at rest and/or in transit.

### Failure Indicator

`status` is `"error"` with a description in the `error` field.

## Vulnerable Pattern

Missing encryption occurs when sensitive data is stored in plaintext in databases, files, or caches, or transmitted over unencrypted channels. This allows anyone with access to the storage medium or network to read the sensitive data.

### Detection Patterns

**Plaintext storage of sensitive data:**
```
# Database:         INSERT INTO users (ssn, credit_card) VALUES (%s, %s)  -- unencrypted fields
# File:             with open('users.csv', 'w') as f: f.write(f'{ssn},{cc_number}')
# Cache:            redis.set(f'user:{uid}:ssn', ssn)  -- plaintext in Redis
# Logs:             logger.info(f"Processing payment for card {card_number}")
```

**Unencrypted network connections:**
```
# HTTP:             requests.post('http://api.example.com/data', json=sensitive_data)
# Database:         psycopg2.connect(host='db.example.com', sslmode='disable')
# SMTP:             smtplib.SMTP('mail.example.com', 25)  -- no STARTTLS
# Socket:           socket.connect(('api.example.com', 80))  -- plain TCP
```

**Configuration without encryption:**
```
# Connection string: DATABASE_URL=postgresql://user:pass@host:5432/db  (no sslmode=require)
# Redis:            REDIS_URL=redis://host:6379  (no TLS)
# MQTT:             mqtt.connect('mqtt://broker:1883')  (no TLS)
```

**Regex detection patterns:**
```
# HTTP URLs:         http://(?!localhost|127\.0\.0\.1)
# No SSL DB:         sslmode\s*=\s*['"]?disable
# Plaintext fields:  (ssn|social_security|credit_card|card_number|account_number)\s*=
# Cache plaintext:   (redis|memcache)\.(set|hset)\(.*?(ssn|credit_card|password)
```

## Fix Pattern

The general fix depends on the encryption context:

**Data at rest:**
1. Identify all sensitive fields that need encryption.
2. Implement field-level encryption using AES-256-GCM (authenticated encryption).
3. Store the encryption key securely (environment variable, KMS).
4. Encrypt before writing, decrypt after reading.

**Data in transit:**
1. Replace HTTP with HTTPS for all API calls.
2. Enable TLS on database connections.
3. Use STARTTLS or TLS for email.
4. Use TLS-enabled protocols for all network communication.

**Transformation steps:**
1. Identify the sensitive data and its storage/transmission path.
2. Add an encryption utility module with encrypt/decrypt functions.
3. Encrypt data before storage and decrypt after retrieval.
4. Enforce TLS for network connections.
5. Store encryption keys securely, never in source code.

## Language-Specific Examples

### Python -- Field-Level Encryption with Fernet

**Before (vulnerable):**
```python
import psycopg2

def store_user_data(conn, user_id, ssn, credit_card):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (id, ssn, credit_card) VALUES (%s, %s, %s)",
        (user_id, ssn, credit_card)
    )
    conn.commit()

def get_user_data(conn, user_id):
    cursor = conn.cursor()
    cursor.execute("SELECT ssn, credit_card FROM users WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    return {'ssn': row[0], 'credit_card': row[1]}
```

**After (fixed):**
```python
import os
import psycopg2
from cryptography.fernet import Fernet

# Load encryption key from environment (generate with Fernet.generate_key())
ENCRYPTION_KEY = os.environ['DATA_ENCRYPTION_KEY']
cipher = Fernet(ENCRYPTION_KEY)

def encrypt_field(plaintext):
    """Encrypt a sensitive field."""
    if plaintext is None:
        return None
    return cipher.encrypt(plaintext.encode('utf-8')).decode('utf-8')

def decrypt_field(ciphertext):
    """Decrypt a sensitive field."""
    if ciphertext is None:
        return None
    return cipher.decrypt(ciphertext.encode('utf-8')).decode('utf-8')

def store_user_data(conn, user_id, ssn, credit_card):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (id, ssn, credit_card) VALUES (%s, %s, %s)",
        (user_id, encrypt_field(ssn), encrypt_field(credit_card))
    )
    conn.commit()

def get_user_data(conn, user_id):
    cursor = conn.cursor()
    cursor.execute("SELECT ssn, credit_card FROM users WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    return {'ssn': decrypt_field(row[0]), 'credit_card': decrypt_field(row[1])}
```

**Explanation:** Fernet (built on AES-128-CBC with HMAC-SHA256) provides authenticated encryption. Sensitive fields (SSN, credit card) are encrypted before being stored in the database and decrypted when retrieved. The encryption key is loaded from an environment variable, never hardcoded. Database columns for encrypted fields should be `TEXT` or `BYTEA` type to accommodate the ciphertext.

### Python -- AES-256-GCM Encryption

**After (fixed, using AES-256-GCM for stronger encryption):**
```python
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ENCRYPTION_KEY = bytes.fromhex(os.environ['DATA_ENCRYPTION_KEY'])  # 32-byte hex key

def encrypt_field(plaintext):
    if plaintext is None:
        return None
    nonce = os.urandom(12)  # 96-bit nonce for GCM
    aesgcm = AESGCM(ENCRYPTION_KEY)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
    return (nonce + ciphertext).hex()

def decrypt_field(hex_data):
    if hex_data is None:
        return None
    data = bytes.fromhex(hex_data)
    nonce = data[:12]
    ciphertext = data[12:]
    aesgcm = AESGCM(ENCRYPTION_KEY)
    return aesgcm.decrypt(nonce, ciphertext, None).decode('utf-8')
```

**Explanation:** AES-256-GCM provides authenticated encryption with a 256-bit key. The nonce (initialization vector) is generated randomly for each encryption and prepended to the ciphertext for storage. GCM mode provides both confidentiality and integrity.

### Python -- Enforcing TLS on Database Connection

**Before (vulnerable):**
```python
import psycopg2

conn = psycopg2.connect(
    host='db.example.com',
    database='myapp',
    user='appuser',
    password=os.environ['DB_PASSWORD']
)
```

**After (fixed):**
```python
import psycopg2

conn = psycopg2.connect(
    host='db.example.com',
    database='myapp',
    user='appuser',
    password=os.environ['DB_PASSWORD'],
    sslmode='require',
    sslrootcert='/etc/ssl/certs/db-ca.pem'
)
```

**Explanation:** The `sslmode='require'` parameter enforces TLS encryption for the database connection. The `sslrootcert` parameter specifies the CA certificate for verifying the database server's identity. Use `sslmode='verify-full'` for the strongest verification (validates both the certificate and the hostname).

### Python -- HTTP to HTTPS

**Before (vulnerable):**
```python
import requests

def send_payment(card_number, amount):
    response = requests.post('http://payment-api.example.com/charge', json={
        'card': card_number,
        'amount': amount
    })
    return response.json()
```

**After (fixed):**
```python
import requests

def send_payment(card_number, amount):
    response = requests.post('https://payment-api.example.com/charge', json={
        'card': card_number,
        'amount': amount
    })
    return response.json()
```

**Explanation:** The URL scheme is changed from `http://` to `https://` to encrypt data in transit with TLS. All API calls transmitting sensitive data must use HTTPS.

### Java -- Field-Level Encryption with AES-GCM

**Before (vulnerable):**
```java
public void storeUserData(Connection conn, String userId, String ssn) throws SQLException {
    PreparedStatement pstmt = conn.prepareStatement(
        "INSERT INTO users (id, ssn) VALUES (?, ?)");
    pstmt.setString(1, userId);
    pstmt.setString(2, ssn);
    pstmt.executeUpdate();
}
```

**After (fixed):**
```java
import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.security.SecureRandom;
import java.util.Base64;

public class FieldEncryption {
    private static final int GCM_TAG_LENGTH = 128;
    private static final int GCM_NONCE_LENGTH = 12;
    private final SecretKey secretKey;

    public FieldEncryption() {
        byte[] keyBytes = Base64.getDecoder().decode(System.getenv("DATA_ENCRYPTION_KEY"));
        this.secretKey = new SecretKeySpec(keyBytes, "AES");
    }

    public String encrypt(String plaintext) throws Exception {
        byte[] nonce = new byte[GCM_NONCE_LENGTH];
        new SecureRandom().nextBytes(nonce);

        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, secretKey, new GCMParameterSpec(GCM_TAG_LENGTH, nonce));
        byte[] ciphertext = cipher.doFinal(plaintext.getBytes("UTF-8"));

        byte[] combined = new byte[nonce.length + ciphertext.length];
        System.arraycopy(nonce, 0, combined, 0, nonce.length);
        System.arraycopy(ciphertext, 0, combined, nonce.length, ciphertext.length);

        return Base64.getEncoder().encodeToString(combined);
    }

    public String decrypt(String encoded) throws Exception {
        byte[] combined = Base64.getDecoder().decode(encoded);
        byte[] nonce = new byte[GCM_NONCE_LENGTH];
        byte[] ciphertext = new byte[combined.length - GCM_NONCE_LENGTH];
        System.arraycopy(combined, 0, nonce, 0, GCM_NONCE_LENGTH);
        System.arraycopy(combined, GCM_NONCE_LENGTH, ciphertext, 0, ciphertext.length);

        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE, secretKey, new GCMParameterSpec(GCM_TAG_LENGTH, nonce));
        return new String(cipher.doFinal(ciphertext), "UTF-8");
    }
}

// Usage:
FieldEncryption encryption = new FieldEncryption();

public void storeUserData(Connection conn, String userId, String ssn) throws Exception {
    PreparedStatement pstmt = conn.prepareStatement(
        "INSERT INTO users (id, ssn) VALUES (?, ?)");
    pstmt.setString(1, userId);
    pstmt.setString(2, encryption.encrypt(ssn));
    pstmt.executeUpdate();
}
```

**Explanation:** A `FieldEncryption` utility class provides AES-256-GCM encryption and decryption. The key is loaded from an environment variable. A random nonce is generated for each encryption operation and prepended to the ciphertext for storage. GCM mode provides authenticated encryption.

### JavaScript/Node.js -- Field-Level Encryption

**Before (vulnerable):**
```javascript
async function storeUserData(db, userId, ssn, creditCard) {
  await db.query(
    'INSERT INTO users (id, ssn, credit_card) VALUES ($1, $2, $3)',
    [userId, ssn, creditCard]
  );
}
```

**After (fixed):**
```javascript
const crypto = require('crypto');

const ENCRYPTION_KEY = Buffer.from(process.env.DATA_ENCRYPTION_KEY, 'hex'); // 32 bytes
const ALGORITHM = 'aes-256-gcm';

function encryptField(plaintext) {
  if (!plaintext) return null;
  const nonce = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv(ALGORITHM, ENCRYPTION_KEY, nonce);
  let encrypted = cipher.update(plaintext, 'utf8', 'hex');
  encrypted += cipher.final('hex');
  const tag = cipher.getAuthTag();
  return nonce.toString('hex') + ':' + tag.toString('hex') + ':' + encrypted;
}

function decryptField(data) {
  if (!data) return null;
  const [nonceHex, tagHex, ciphertext] = data.split(':');
  const nonce = Buffer.from(nonceHex, 'hex');
  const tag = Buffer.from(tagHex, 'hex');
  const decipher = crypto.createDecipheriv(ALGORITHM, ENCRYPTION_KEY, nonce);
  decipher.setAuthTag(tag);
  let decrypted = decipher.update(ciphertext, 'hex', 'utf8');
  decrypted += decipher.final('utf8');
  return decrypted;
}

async function storeUserData(db, userId, ssn, creditCard) {
  await db.query(
    'INSERT INTO users (id, ssn, credit_card) VALUES ($1, $2, $3)',
    [userId, encryptField(ssn), encryptField(creditCard)]
  );
}

async function getUserData(db, userId) {
  const result = await db.query(
    'SELECT ssn, credit_card FROM users WHERE id = $1', [userId]
  );
  const row = result.rows[0];
  return { ssn: decryptField(row.ssn), creditCard: decryptField(row.credit_card) };
}
```

**Explanation:** Node.js's built-in `crypto` module provides AES-256-GCM encryption. The nonce and authentication tag are stored alongside the ciphertext. The encryption key is loaded from an environment variable as a 32-byte hex string.

### JavaScript/Node.js -- Enforcing HTTPS

**Before (vulnerable):**
```javascript
const express = require('express');
const app = express();

app.listen(3000);
```

**After (fixed):**
```javascript
const express = require('express');
const helmet = require('helmet');
const app = express();

// Force HTTPS via HSTS header
app.use(helmet.hsts({
  maxAge: 31536000,  // 1 year
  includeSubDomains: true,
  preload: true
}));

// Redirect HTTP to HTTPS
app.use((req, res, next) => {
  if (req.headers['x-forwarded-proto'] !== 'https' && process.env.NODE_ENV === 'production') {
    return res.redirect(301, `https://${req.headers.host}${req.url}`);
  }
  next();
});

app.listen(3000);
```

**Explanation:** The Helmet middleware adds the HSTS (HTTP Strict Transport Security) header, which tells browsers to always use HTTPS. An HTTP-to-HTTPS redirect is added for production environments. In production, TLS termination is typically handled by a reverse proxy (nginx, CloudFront) in front of the Express server.

## Testing Guidance

### Verifying the Fix Eliminates the Vulnerability

1. **Encryption at rest test**: Store sensitive data and inspect the database directly. Verify the stored value is encrypted (not plaintext).
2. **Decryption test**: Retrieve the encrypted data and verify it decrypts to the original value.
3. **TLS enforcement test**: Attempt to connect to the service over HTTP. Verify it redirects to HTTPS or returns an error.
4. **Database TLS test**: Check the database connection to verify TLS is in use (`SELECT ssl_is_used()` in PostgreSQL).
5. **Key rotation test**: Verify that the application can decrypt data encrypted with a previous key (if key rotation is supported).

### Automated Test Pattern

```python
def test_field_encryption():
    plaintext = "123-45-6789"
    encrypted = encrypt_field(plaintext)
    assert encrypted != plaintext
    assert decrypt_field(encrypted) == plaintext

def test_encrypted_data_in_database(db_connection):
    store_user_data(db_connection, "user1", "123-45-6789", "4111111111111111")
    # Read directly from database without decryption
    cursor = db_connection.cursor()
    cursor.execute("SELECT ssn FROM users WHERE id = 'user1'")
    raw_ssn = cursor.fetchone()[0]
    assert raw_ssn != "123-45-6789"  # Stored value must be encrypted
```

### Semgrep Rules That Should Pass After Fix

```yaml
rules:
  - id: plaintext-sensitive-storage
    patterns:
      - pattern: |
          $CURSOR.execute("INSERT INTO $TABLE (..., $COL, ...) VALUES (...)", (..., $VAR, ...))
      - metavariable-regex:
          metavariable: $COL
          regex: (ssn|social_security|credit_card|card_number)
      - pattern-not: |
          $CURSOR.execute("INSERT INTO $TABLE (..., $COL, ...) VALUES (...)", (..., encrypt_field($VAR), ...))
    message: "Sensitive data stored without encryption"
    languages: [python]
    severity: ERROR
```

### Verifying Functionality is Preserved

- Verify that encrypted data can be correctly decrypted to its original value.
- Test with special characters, Unicode, empty strings, and null values.
- Verify that encryption does not break database queries that need to search encrypted fields (note: encrypted fields cannot be searched with SQL LIKE; consider searchable encryption or hash-based indexing).
- Verify TLS connections work with all client libraries.

## Common Mistakes

1. **Hardcoding the encryption key.** The encryption key must be stored securely (environment variable, KMS, Vault), never in source code. A hardcoded key provides no security if the source code is accessible.

2. **Using ECB mode.** AES in ECB (Electronic Codebook) mode is insecure because identical plaintext blocks produce identical ciphertext blocks, revealing patterns. Use GCM, CBC with HMAC, or another authenticated encryption mode.

3. **Reusing nonces/IVs.** Each encryption operation must use a unique nonce (IV). Reusing a nonce with the same key completely breaks GCM security. Always generate a random nonce for each encryption.

4. **Encrypting without authentication.** Using AES-CBC without HMAC allows attackers to modify ciphertext without detection (padding oracle attacks). Use authenticated encryption (AES-GCM, ChaCha20-Poly1305) or AES-CBC + HMAC (encrypt-then-MAC).

5. **Not encrypting all sensitive fields.** If SSN is encrypted but credit card number is not, the fix is incomplete. Identify all sensitive fields and encrypt all of them.

6. **Breaking search functionality.** Encrypted fields cannot be searched with SQL queries. If searching is required, use techniques like blind indexing (store a keyed hash of the field for lookups) or searchable encryption schemes.

7. **Not planning for key rotation.** If the encryption key is compromised, all data encrypted with it is exposed. Implement a key rotation strategy that can re-encrypt data with a new key.

8. **Using base64 instead of encryption.** Base64 is an encoding, not encryption. It provides no security. `base64.b64encode(ssn)` is trivially reversible by anyone.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **File not found** | Return error JSON with `"error": "File not found: <path>"`. Do not retry. |
| **Cannot determine which data is sensitive** | Apply encryption to fields whose names suggest sensitivity (ssn, credit_card, password, etc.) and flag for manual review. |
| **Database schema change required** | Encrypted fields are longer than plaintext. Note that the database column type may need to be changed (e.g., from `VARCHAR(11)` to `TEXT`) and flag for review. |
| **Encryption library not available** | Recommend adding the encryption library to dependencies. Flag for review. |
| **Key management infrastructure not in place** | Recommend setting up key management (KMS, Vault, or environment variables as minimum). Apply the code changes and flag for infrastructure review. |
| **Existing data needs migration** | Note that existing plaintext data needs to be encrypted via a migration script. The code fix only handles new data. Flag for review. |

## Constraints

- **Preserve data access patterns**: The fix must not break the application's ability to read and write sensitive data.
- **No execution**: Do not run the application, connect to databases, or make network requests.
- **No hardcoded keys**: Encryption keys must be loaded from environment variables or a key management service.
- **Authenticated encryption**: Always use authenticated encryption (GCM, Poly1305) to prevent ciphertext manipulation.
- **Minimal diff**: Add encryption/decryption around the existing data flow. Do not refactor unrelated code.
- **Key management guidance**: If the codebase has no key management, recommend a secure approach in warnings.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Glob` for file discovery, `Edit` for applying fixes. Do not use `Bash` to run code or tests.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
