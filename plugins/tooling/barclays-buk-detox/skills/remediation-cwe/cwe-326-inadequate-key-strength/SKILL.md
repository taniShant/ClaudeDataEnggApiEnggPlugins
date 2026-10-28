---
name: cwe-326-inadequate-key-strength
description: "CWE-326: Inadequate Encryption Strength — "
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-326: Inadequate Encryption Strength
## Quick Start

This skill provides the fix pattern for CWE-326. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-326 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## Overview
Encryption keys are too weak to provide adequate security. Examples include RSA keys < 2048 bits, symmetric keys < 128 bits, or outdated algorithms like DES.

## Vulnerability Pattern
```java
// VULNERABLE: 1024-bit RSA (insufficient)
KeyPairGenerator keyGen = KeyPairGenerator.getInstance("RSA");
keyGen.initialize(1024);  // Too weak
KeyPair keyPair = keyGen.generateKeyPair();

// VULNERABLE: DES encryption (broken)
Cipher cipher = Cipher.getInstance("DES");
SecretKey key = new SecretKeySpec(keyBytes, 0, 8, "DES");

// VULNERABLE: MD5 for key derivation
MessageDigest md = MessageDigest.getInstance("MD5");
byte[] key = md.digest(password.getBytes());
```

## Fix Strategy

1. **Use strong key sizes** — RSA >= 2048 bits, ECC >= 256 bits, symmetric >= 256 bits
2. **Use modern algorithms** — AES, SHA-256+, modern TLS
3. **Avoid deprecated algorithms** — DES, 3DES, MD5, SHA-1
4. **Use PBKDF2, bcrypt, or scrypt** for password-based keys (not MD5/SHA-1)
5. **Verify crypto library versions** are up-to-date

## Remediation Examples

### Option A: Strong RSA key
```java
// FIXED: 2048-bit RSA
KeyPairGenerator keyGen = KeyPairGenerator.getInstance("RSA");
keyGen.initialize(2048);  // Industry standard minimum
KeyPair keyPair = keyGen.generateKeyPair();
```

### Option B: AES encryption
```java
// FIXED: AES-256 with proper IV
KeyGenerator keyGen = KeyGenerator.getInstance("AES");
keyGen.init(256);  // 256-bit key
SecretKey key = keyGen.generateKey();

Cipher cipher = Cipher.getInstance("AES/CBC/PKCS5Padding");
SecureRandom random = new SecureRandom();
byte[] iv = new byte[16];
random.nextBytes(iv);
IvParameterSpec ivSpec = new IvParameterSpec(iv);
cipher.init(Cipher.ENCRYPT_MODE, key, ivSpec);
```

### Option C: Password-based encryption
```java
// FIXED: PBKDF2 with salt
PBEKeySpec keySpec = new PBEKeySpec(password.toCharArray(), salt, 65536, 256);
SecretKeyFactory factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256");
SecretKey key = factory.generateSecret(keySpec);
```

## Implementation Checklist
- [ ] Identify all encryption/key generation code
- [ ] Verify RSA keys are >= 2048 bits (or >= 4096 for long-term)
- [ ] Verify symmetric keys are >= 256 bits
- [ ] Replace DES, 3DES with AES
- [ ] Replace MD5, SHA-1 with SHA-256 or better
- [ ] Use PBKDF2/bcrypt/scrypt for password-derived keys
- [ ] Test: verify strong ciphers are negotiated in TLS

## Key Points
- **2048-bit RSA is minimum** — use 4096 for long-term security
- **256-bit AES is strong** — 128-bit is acceptable but 256 preferred
- **Deprecated algorithms must go** — DES, 3DES, MD5, SHA-1
- **Key derivation from passwords is risky** — use PBKDF2+ with high iteration counts
- **Severity**: High — directly undermines encryption security

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
