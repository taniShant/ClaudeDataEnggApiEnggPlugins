---
name: cwe-319-cleartext-transmission
description: "CWE-319: Cleartext Transmission of Sensitive Information Remediation — Remediate cleartext transmission of sensitive information by enforcing HTTPS/TLS for all connections that carry sensitive data (passwords, tokens, PII"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-319: Cleartext Transmission of Sensitive Information Remediation
## Quick Start

This skill provides the fix pattern for CWE-319. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-319 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-319
- **CWE Name**: Cleartext Transmission of Sensitive Information
- **Severity**: High
- **OWASP Category**: A02:2021 - Cryptographic Failures

## Purpose

Remediate cleartext transmission of sensitive information by enforcing HTTPS/TLS for all connections that carry sensitive data (passwords, tokens, PII, credit cards).

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file.
  - `line_number` (integer, required): The 1-based line number.
  - `cwe_id` (string, required): Must be `CWE-319`.

## Steps

1. **Identify cleartext HTTP usage** with sensitive data.
   - Replace `http://` with `https://`.
   - Add HSTS headers.
   - Enforce TLS version.

2. **Add middleware/configuration** to enforce HTTPS.

3. **Apply the edit.**
   - Use `Edit` to add HTTPS enforcement.

## Output Format

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "http_upgraded_to_https": true,
      "hsts_added": boolean
    }
  ],
  "cleartext_urls_fixed": "<integer>",
  "warnings": ["<string: manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

## Vulnerable Pattern

```python
requests.get('http://api.example.com/users')  # Cleartext!
requests.post('http://api.example.com/login', data=credentials)  # Cleartext!
```

## Fix Pattern

1. Use `https://` instead of `http://`.
2. Add HSTS headers.
3. Enforce minimum TLS version (1.2+).

## Language-Specific Examples

### Python

**Before (vulnerable):**
```python
import requests

response = requests.get('http://api.example.com/user')  # Cleartext!
response = requests.post('http://api.example.com/login',
                        json={'username': u, 'password': p})  # Cleartext!
```

**After (fixed):**
```python
import requests

response = requests.get('https://api.example.com/user')  # Encrypted
response = requests.post('https://api.example.com/login',
                        json={'username': u, 'password': p})  # Encrypted
```

### Java - Spring Boot

**Before (vulnerable):**
```java
@Configuration
public class SecurityConfig {
    // No HTTPS enforcement
}
```

**After (fixed):**
```java
@Configuration
public class SecurityConfig extends WebSecurityConfigurerAdapter {
    @Override
    protected void configure(HttpSecurity http) throws Exception {
        http.requiresChannel()
            .anyRequest()
            .requiresSecure()
            .and()
            .headers()
            .httpStrictTransportSecurity()
            .maxAgeInSeconds(31536000)
            .includeSubDomains(true);
    }
}
```

### JavaScript - Express

**Before (vulnerable):**
```javascript
const http = require('http');

http.createServer((req, res) => {
    res.writeHead(200, {'Content-Type': 'text/plain'});
    res.end('Hello World');
}).listen(8080);
```

**After (fixed):**
```javascript
const https = require('https');
const fs = require('fs');
const helmet = require('helmet');
const express = require('express');

const app = express();
app.use(helmet.hsts({
    maxAge: 31536000,
    includeSubDomains: true,
    preload: true
}));

const options = {
    key: fs.readFileSync('private-key.pem'),
    cert: fs.readFileSync('certificate.pem')
};

https.createServer(options, app).listen(443);
```

## Testing Guidance

1. **Verify HTTPS is used**: Check URLs use `https://`.
2. **Verify HSTS header**: Check `Strict-Transport-Security` header in responses.
3. **Verify TLS version**: Ensure TLS 1.2+ is used.
4. **Test HTTP fallback**: Verify HTTP requests are redirected or rejected.

## Common Mistakes

1. **Only encrypting login**, not subsequent requests with tokens.
2. **Weak TLS version** (TLS 1.0, 1.1).
3. **Not setting HSTS header** - browser may not upgrade next time.
4. **Self-signed certificates** - users may bypass warnings.

## Constraints

- All sensitive data transmission must use HTTPS.
- Minimum TLS 1.2.
- HSTS header with sufficient max-age and includeSubDomains.
- Valid certificate from trusted CA.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
