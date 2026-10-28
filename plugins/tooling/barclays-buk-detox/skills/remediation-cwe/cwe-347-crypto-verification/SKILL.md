---
name: cwe-347-crypto-verification
description: "CWE-347: Improper Verification of Cryptographic Signature Remediation — Remediate improper cryptographic signature verification by ensuring all cryptographic signatures are properly verified before accepting signed data. F"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-347: Improper Verification of Cryptographic Signature Remediation
## Quick Start

This skill provides the fix pattern for CWE-347. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-347 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-347
- **CWE Name**: Improper Verification of Cryptographic Signature
- **Severity**: High
- **OWASP Category**: A02:2021 - Cryptographic Failures

## Purpose

Remediate improper cryptographic signature verification by ensuring all cryptographic signatures are properly verified before accepting signed data. Failure to verify signatures allows data tampering and forgery.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file.
  - `line_number` (integer, required): The 1-based line number.
  - `cwe_id` (string, required): Must be `CWE-347`.

## Steps

1. **Identify signature verification** code.
2. **Ensure verification is always performed** before trusting signed data.
3. **Check that verification uses correct algorithm** and key.
4. **Apply the edit.**

## Output Format

```json
{
  "status": "success | partial | error",
  "file_path": "<string>",
  "changes": [
    {
      "line_number": "<integer>",
      "verification_added": true,
      "algorithm": "<string>"
    }
  ],
  "error": "null or string"
}
```

## Vulnerable Pattern

```python
# Signature not verified
jwt_data = jwt.decode(token, options={"verify_signature": False})
```

## Fix Pattern

Always verify signatures with proper algorithm and key.

## Language-Specific Examples

### Python - JWT

**Before (vulnerable):**
```python
import jwt

token = request.headers.get('Authorization')
payload = jwt.decode(token, options={"verify_signature": False})  # VULNERABLE!
```

**After (fixed):**
```python
import jwt

SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
token = request.headers.get('Authorization').replace('Bearer ', '')

try:
    payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
except jwt.InvalidSignatureError:
    return {"error": "Invalid signature"}, 401
```

## Constraints

- Always verify signatures with proper key.
- Use secure algorithms (SHA-256 or better).
- Reject signatures that don't verify.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
