---
name: cwe-295-improper-cert-validation
description: "CWE-295: Improper Certificate Validation Remediation — Remediate improper certificate validation vulnerabilities by re-enabling SSL/TLS certificate verification, removing `verify=False` and equivalent sett"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-295: Improper Certificate Validation Remediation
## Quick Start

This skill provides the fix pattern for CWE-295. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-295 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-295
- **CWE Name**: Improper Certificate Validation
- **Severity**: High
- **OWASP Category**: A07:2021 - Identification and Authentication Failures

## Purpose

Remediate improper certificate validation vulnerabilities by re-enabling SSL/TLS certificate verification, removing `verify=False` and equivalent settings, and configuring proper CA certificate bundles. This skill identifies code patterns where SSL certificate validation is disabled or weakened, which exposes the application to man-in-the-middle (MITM) attacks, and restores proper certificate chain verification. It covers Python (requests, urllib3, httplib2, aiohttp), JavaScript/Node.js (https, axios, node-fetch), and Java (HttpsURLConnection, HttpClient, OkHttp).

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file containing the certificate validation vulnerability.
  - `line_number` (integer, required): The 1-based line number of the vulnerable code.
  - `cwe_id` (string, required): Must be `CWE-295`.
  - `code_snippet` (string, optional): The flagged code snippet.
  - `context` (object, optional): Output from the `code_context_analyzer` skill.
- **repo_root** (optional, string): Absolute path to the repository root. Defaults to the current working directory.
- **language** (optional, string): Programming language (`python`, `java`, `javascript`). Auto-detected if not provided.
- **library** (optional, string): HTTP library in use. Auto-detected if not provided.

## Steps

1. **Read the vulnerable file and surrounding context.**
   - Use `Read` to open the file at `vulnerability.file_path`.
   - If `vulnerability.context` is provided, use it. Otherwise, read +/- 50 lines around `vulnerability.line_number`.

2. **Detect the language, HTTP library, and the specific certificate bypass pattern.**
   - Examine import statements and the HTTP client configuration.
   - Identify the exact mechanism used to disable verification: `verify=False`, `rejectUnauthorized: false`, custom `TrustManager`, `InsecureRequestWarning` suppression, etc.

3. **Determine if the bypass was intentional (development/testing) or accidental.**
   - Check for comments indicating the reason (e.g., `# TODO: re-enable in production`, `// self-signed cert in dev`).
   - Check for environment-conditional logic (e.g., `if DEBUG: verify=False`).
   - Even if intentional for development, the fix should ensure verification is enabled in production.

4. **Apply the fix.**
   - Remove the `verify=False` or equivalent setting to restore default certificate verification.
   - If the application uses a self-signed certificate or internal CA, configure the custom CA bundle instead of disabling verification.
   - Remove any warning suppression (e.g., `urllib3.disable_warnings(InsecureRequestWarning)`).
   - If environment-conditional bypass is needed, ensure it defaults to enabled and requires an explicit opt-out.

5. **Apply the edit.**
   - Use `Edit` to remove or modify the insecure certificate configuration.
   - Add any necessary CA bundle configuration.
   - Preserve code formatting, indentation, and surrounding logic.

6. **Scan for similar patterns in the same file and related files.**
   - Use `Grep` to find other instances of disabled certificate verification.
   - Apply the same fix to all instances.

7. **Verify the fix.**
   - Use `Read` to re-read the modified file and confirm certificate verification is enabled.
   - Confirm no warning suppression remains.

## Output Format

Return a JSON object:

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "original_code": "<string: the insecure code>",
      "fixed_code": "<string: the secure replacement>",
      "fix_type": "remove_verify_false | enable_verification | configure_ca_bundle | remove_warning_suppression"
    }
  ],
  "similar_patterns_fixed": "<integer: count of additional similar patterns fixed>",
  "imports_added": ["<string: any new import statements added>"],
  "warnings": ["<string: any warnings about manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

### Success Indicator

`status` is `"success"` and all certificate verification bypasses have been removed.

### Failure Indicator

`status` is `"error"` with a description in the `error` field.

## Vulnerable Pattern

Improper certificate validation occurs when an application disables or weakens SSL/TLS certificate verification when making outbound HTTPS connections. This allows man-in-the-middle attackers to intercept, read, and modify encrypted traffic between the application and the remote server.

### Detection Patterns

**Python -- requests library:**
```
# verify=False:           requests.get(url, verify=False)
# Session level:          session.verify = False
# Warning suppression:    urllib3.disable_warnings(InsecureRequestWarning)
# requests.packages:      requests.packages.urllib3.disable_warnings()
```

**Python -- urllib3:**
```
# disable_warnings:       urllib3.disable_warnings()
# CERT_NONE:             http = urllib3.PoolManager(cert_reqs='CERT_NONE')
```

**Python -- aiohttp:**
```
# ssl=False:             aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False))
# verify_ssl=False:      session.get(url, verify_ssl=False)
```

**Python -- httplib2:**
```
# disable_ssl:           httplib2.Http(disable_ssl_certificate_validation=True)
```

**JavaScript/Node.js:**
```
# rejectUnauthorized:    https.request({rejectUnauthorized: false})
# NODE_TLS env:          process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0'
# axios:                 axios.create({httpsAgent: new https.Agent({rejectUnauthorized: false})})
```

**Java:**
```
# TrustAllCerts:         X509TrustManager that returns empty in checkServerTrusted
# HostnameVerifier:      HostnameVerifier that always returns true
# SSLContext:            SSLContext with custom TrustManager that accepts all
```

**Regex detection patterns:**
```
# Python verify=False:    verify\s*=\s*False
# Python CERT_NONE:       cert_reqs\s*=\s*['"]?CERT_NONE
# Python ssl=False:       ssl\s*=\s*False
# Python warning:         disable_warnings.*InsecureRequestWarning
# JS rejectUnauthorized:  rejectUnauthorized\s*:\s*false
# JS NODE_TLS:            NODE_TLS_REJECT_UNAUTHORIZED.*['"]0['"]
# Java TrustAll:          checkServerTrusted.*\{\s*(return|)\s*\}
```

## Fix Pattern

The general fix is to remove the certificate verification bypass and restore the default behavior, which validates the server's certificate chain against the system's trusted CA bundle.

**Transformation steps:**
1. Remove `verify=False` or equivalent settings.
2. Remove warning suppression for insecure requests.
3. If a custom CA is needed, configure the CA bundle path instead of disabling verification.
4. If the bypass was environment-conditional, ensure the default is secure (verification enabled).

## Language-Specific Examples

### Python -- requests Library

**Before (vulnerable):**
```python
import requests
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def fetch_data(url):
    response = requests.get(url, verify=False)
    return response.json()

def post_data(url, data):
    session = requests.Session()
    session.verify = False
    return session.post(url, json=data)
```

**After (fixed):**
```python
import requests

def fetch_data(url):
    response = requests.get(url)
    return response.json()

def post_data(url, data):
    session = requests.Session()
    return session.post(url, json=data)
```

**Explanation:** The `verify=False` parameter and `session.verify = False` are removed, restoring the default behavior of verifying SSL certificates against the system's CA bundle. The `InsecureRequestWarning` suppression is also removed.

### Python -- Custom CA Bundle

**After (fixed, with custom CA for internal services):**
```python
import os
import requests

CA_BUNDLE = os.environ.get('REQUESTS_CA_BUNDLE', '/etc/ssl/certs/ca-certificates.crt')

def fetch_internal_data(url):
    response = requests.get(url, verify=CA_BUNDLE)
    return response.json()
```

**Explanation:** When connecting to services that use certificates signed by an internal CA, the CA bundle path is configured explicitly rather than disabling verification. The CA bundle path can be overridden via an environment variable.

### Python -- aiohttp

**Before (vulnerable):**
```python
import aiohttp

async def fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, ssl=False) as response:
            return await response.json()
```

**After (fixed):**
```python
import aiohttp
import ssl

async def fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# For custom CA:
async def fetch_internal(url, ca_path='/etc/ssl/certs/internal-ca.pem'):
    ssl_context = ssl.create_default_context(cafile=ca_path)
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(url) as response:
            return await response.json()
```

**Explanation:** The `ssl=False` parameter is removed, restoring default certificate validation. For internal CAs, an SSL context with the custom CA file is created instead of disabling verification.

### JavaScript/Node.js -- https and axios

**Before (vulnerable):**
```javascript
const https = require('https');
const axios = require('axios');

// Global disable (extremely dangerous)
process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';

// Per-request disable
const agent = new https.Agent({ rejectUnauthorized: false });
const client = axios.create({ httpsAgent: agent });

async function fetchData(url) {
  const response = await client.get(url);
  return response.data;
}
```

**After (fixed):**
```javascript
const https = require('https');
const axios = require('axios');

const client = axios.create();

async function fetchData(url) {
  const response = await client.get(url);
  return response.data;
}

// For custom CA:
const fs = require('fs');

function createSecureClient(caPath) {
  const ca = fs.readFileSync(caPath);
  const agent = new https.Agent({ ca });
  return axios.create({ httpsAgent: agent });
}
```

**Explanation:** The `process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0'` global disable and the `rejectUnauthorized: false` per-agent disable are removed. For services using internal CAs, the CA certificate is loaded and passed to the `https.Agent` via the `ca` option, which enables verification against the custom CA.

### Java -- Custom TrustManager

**Before (vulnerable):**
```java
import javax.net.ssl.*;
import java.security.cert.X509Certificate;

// Trust-all TrustManager (disables certificate validation)
TrustManager[] trustAllCerts = new TrustManager[]{
    new X509TrustManager() {
        public X509Certificate[] getAcceptedIssuers() { return null; }
        public void checkClientTrusted(X509Certificate[] certs, String authType) { }
        public void checkServerTrusted(X509Certificate[] certs, String authType) { }
    }
};

SSLContext sc = SSLContext.getInstance("TLS");
sc.init(null, trustAllCerts, new java.security.SecureRandom());
HttpsURLConnection.setDefaultSSLSocketFactory(sc.getSocketFactory());

// Trust-all HostnameVerifier
HttpsURLConnection.setDefaultHostnameVerifier((hostname, session) -> true);
```

**After (fixed):**
```java
import javax.net.ssl.*;
import java.security.KeyStore;
import java.io.FileInputStream;

// Use the default SSLContext (validates against system CA store)
// No custom TrustManager or HostnameVerifier needed for standard CAs.

// For custom CA bundle:
public static SSLContext createSSLContext(String trustStorePath, String trustStorePassword)
        throws Exception {
    KeyStore trustStore = KeyStore.getInstance(KeyStore.getDefaultType());
    try (FileInputStream fis = new FileInputStream(trustStorePath)) {
        trustStore.load(fis, trustStorePassword.toCharArray());
    }
    TrustManagerFactory tmf = TrustManagerFactory.getInstance(
        TrustManagerFactory.getDefaultAlgorithm());
    tmf.init(trustStore);

    SSLContext sslContext = SSLContext.getInstance("TLS");
    sslContext.init(null, tmf.getTrustManagers(), null);
    return sslContext;
}
```

**Explanation:** The trust-all `TrustManager` and always-true `HostnameVerifier` are removed entirely. The default `SSLContext` validates certificates against the JVM's trusted CA store (`cacerts`). For services with custom CAs, a `KeyStore` is loaded with the custom CA certificate and used to create a proper `TrustManagerFactory`.

### Java -- OkHttp

**Before (vulnerable):**
```java
OkHttpClient client = new OkHttpClient.Builder()
    .sslSocketFactory(trustAllSslSocketFactory, (X509TrustManager) trustAllCerts[0])
    .hostnameVerifier((hostname, session) -> true)
    .build();
```

**After (fixed):**
```java
OkHttpClient client = new OkHttpClient.Builder()
    .build();
// OkHttp uses the system default SSLContext and HostnameVerifier by default

// For custom CA:
OkHttpClient client = new OkHttpClient.Builder()
    .sslSocketFactory(customSslContext.getSocketFactory(), customTrustManager)
    .build();
```

**Explanation:** The `sslSocketFactory` with a trust-all trust manager and the always-true `hostnameVerifier` are removed. OkHttp's default configuration validates certificates properly.

## Testing Guidance

### Verifying the Fix Eliminates the Vulnerability

1. **Self-signed certificate test**: Make a request to a server with a self-signed certificate. Verify the request fails with a certificate validation error.
2. **Expired certificate test**: Make a request to a server with an expired certificate. Verify the request fails.
3. **Wrong hostname test**: Make a request to a server where the certificate CN/SAN does not match the hostname. Verify the request fails.
4. **Valid certificate test**: Make a request to a server with a valid, trusted certificate (e.g., `https://google.com`). Verify the request succeeds.

### Automated Test Pattern

```python
import pytest
import requests

def test_ssl_verification_enabled():
    """Verify that SSL verification is active by testing against a known-bad cert."""
    with pytest.raises(requests.exceptions.SSLError):
        requests.get('https://expired.badssl.com/')

def test_valid_ssl_works():
    """Verify that valid SSL connections still work."""
    response = requests.get('https://www.google.com')
    assert response.status_code == 200
```

### Semgrep Rules That Should Pass After Fix

```yaml
rules:
  - id: python-verify-false
    patterns:
      - pattern-either:
          - pattern: requests.get(..., verify=False, ...)
          - pattern: requests.post(..., verify=False, ...)
          - pattern: $SESSION.verify = False
    message: "SSL certificate verification is disabled"
    languages: [python]
    severity: ERROR
  - id: python-insecure-warning-suppressed
    pattern: "urllib3.disable_warnings(InsecureRequestWarning)"
    message: "Insecure request warnings are suppressed"
    languages: [python]
    severity: WARNING
  - id: js-reject-unauthorized
    pattern: "rejectUnauthorized: false"
    message: "TLS certificate verification is disabled"
    languages: [javascript]
    severity: ERROR
```

### Verifying Functionality is Preserved

- Verify that all HTTPS requests to services with valid certificates still succeed.
- If connecting to services with internal CAs, verify the custom CA bundle is correctly configured and connections succeed.
- Test in all environments (development, staging, production) to ensure the CA configuration is correct.

## Common Mistakes

1. **Disabling verification globally.** Setting `process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0'` or `HttpsURLConnection.setDefaultSSLSocketFactory(trustAllFactory)` disables verification for all connections in the process, not just the intended one. Always configure per-connection or per-client.

2. **Using verify=False for self-signed certificates.** Instead of disabling verification, add the self-signed certificate to the trusted CA bundle. This enables certificate validation while trusting the specific certificate.

3. **Suppressing warnings instead of fixing the issue.** Calling `urllib3.disable_warnings(InsecureRequestWarning)` hides the symptom without fixing the vulnerability. Remove the suppression and enable verification.

4. **Conditional bypass that defaults to insecure.** Code like `verify = os.environ.get('VERIFY_SSL', 'false').lower() == 'true'` defaults to `False` if the environment variable is not set. The default must be secure: `verify = os.environ.get('VERIFY_SSL', 'true').lower() != 'false'`.

5. **Not configuring CA bundles for internal services.** When connecting to services behind an internal CA, the correct fix is to add the CA certificate to the trust store, not to disable verification.

6. **Using `CERT_OPTIONAL` instead of `CERT_REQUIRED`.** In Python's `ssl` module, `CERT_OPTIONAL` requests but does not require a certificate. Always use `CERT_REQUIRED` for server certificate validation.

7. **Leaving test-environment bypasses in production code.** Comments like `# TODO: fix before production` are not enforced. Use environment-based configuration with secure defaults.

8. **Not verifying the hostname.** Some configurations disable hostname verification separately from certificate chain validation. Both must be enabled: the certificate must be valid AND match the hostname being connected to.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **File not found** | Return error JSON with `"error": "File not found: <path>"`. Do not retry. |
| **Cannot determine the HTTP library** | Apply the general principle (remove any `verify=False` equivalent) and flag for review. |
| **Application connects to services with self-signed certs** | Do not disable verification. Configure the custom CA bundle and document it. Flag for review if the CA bundle path is not known. |
| **Global SSL configuration change** | If the bypass is global (`setDefaultSSLSocketFactory`, `NODE_TLS_REJECT_UNAUTHORIZED`), remove it and configure per-client instead. Flag for manual review to audit all outbound connections. |
| **Third-party library disables verification internally** | Note the library and version. Check for configuration options to enable verification. Flag for review. |
| **SSL bypass is in a test file** | Verify it is only used in test configuration. If in production code paths, fix it. If test-only, flag for review but lower severity. |

## Constraints

- **Preserve connectivity**: The fix must not break connections to services with valid certificates.
- **No execution**: Do not make any HTTP requests or test SSL connections.
- **Secure defaults**: The default behavior must be to verify certificates. Any bypass must be explicit, environment-based, and documented.
- **Minimal diff**: Remove only the insecure configuration. Do not refactor the HTTP client or change unrelated settings.
- **CA bundle management**: If a custom CA bundle is needed, configure it properly. Do not include CA certificates in the code; reference them by file path or environment variable.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Glob` for file discovery, `Edit` for applying fixes. Do not use `Bash` to run code or tests.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
