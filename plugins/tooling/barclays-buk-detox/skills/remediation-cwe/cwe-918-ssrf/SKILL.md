---
name: cwe-918-ssrf
description: "CWE-918: Server-Side Request Forgery (SSRF) Remediation — Remediate Server-Side Request Forgery vulnerabilities by enforcing strict URL validation, scheme allowlisting, and private IP range blocking. This ski"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-918: Server-Side Request Forgery (SSRF) Remediation
## Quick Start

This skill provides the fix pattern for CWE-918. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-918 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-918
- **CWE Name**: Server-Side Request Forgery (SSRF)
- **Severity**: High
- **OWASP Category**: A10:2021 — Server-Side Request Forgery (SSRF)

## Purpose

Remediate Server-Side Request Forgery vulnerabilities by enforcing strict URL validation, scheme allowlisting, and private IP range blocking. This skill transforms code that passes user-controlled URLs directly to HTTP clients into code that validates the destination against an allowlist of safe hosts and schemes, and rejects requests targeting internal/private network addresses.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the affected file.
  - `line_number` (integer, required): Line where the SSRF vulnerability was detected.
  - `code_snippet` (string, optional): The vulnerable code flagged by the scanner.
  - `cwe_id` (string, required): Must be `CWE-918`.
- **code_context** (required, JSON object): Output from the `code_context_analyzer` skill.
- **repo_root** (optional, string): Absolute path to the repository root.

## Vulnerable Pattern

SSRF occurs when an application fetches a remote resource using a URL that is fully or partially controlled by user input, without validating that the URL points to an expected and safe destination.

### Detection Patterns

**General indicators:**
- User-supplied data (query parameters, POST body, headers) used directly as a URL argument to an HTTP client.
- URL string concatenation or f-string formatting with user input.
- No validation of the URL scheme, host, or resolved IP address before making the request.

**Regex patterns for detection:**
```
# Python requests
requests\.(get|post|put|delete|patch|head|options)\s*\(.*?(request\.|params\[|args\[|form\[|input)
# Python urllib
urllib\.request\.urlopen\s*\(.*?(request\.|params\[|args\[|form\[|input)
# Java HttpClient
HttpClient.*\.send\(.*?(request\.getParameter|getHeader|getQueryString)
# Node.js axios
axios\.(get|post|put|delete|patch)\s*\(.*?(req\.(body|query|params)\[|req\.(body|query|params)\.)
# Node.js node-fetch
fetch\s*\(.*?(req\.(body|query|params)\[|req\.(body|query|params)\.)
```

## Fix Pattern

### General Approach

1. **Validate the URL scheme**: Only allow `https` (and `http` only if explicitly required). Block `file://`, `ftp://`, `gopher://`, `dict://`, `data://`, and other dangerous schemes.
2. **Validate the host against an allowlist**: Maintain a strict list of permitted destination hosts or domains. If an allowlist is not practical, use a denylist of private/reserved IP ranges as a minimum.
3. **Resolve the hostname and validate the IP**: DNS resolution can be used to bypass host-based checks (DNS rebinding). Resolve the hostname before making the request and verify the resolved IP is not in a private range.
4. **Block private and reserved IP ranges**: Reject any request targeting `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `0.0.0.0/8`, `::1`, `fc00::/7`, and other reserved ranges.
5. **Disable redirects or re-validate after redirect**: HTTP redirects can be used to bypass URL validation. Either disable automatic redirect following or re-validate the redirect target.

### Step-by-Step Transformation

1. Identify the HTTP call that uses a user-controlled URL.
2. Extract the URL into a variable if it is inline.
3. Add a URL validation function (or import a shared one) that checks scheme, host allowlist, and resolved IP.
4. Call the validation function before the HTTP request; raise an error or return an error response if validation fails.
5. Configure the HTTP client to disable automatic redirects (or add a redirect hook that re-validates).
6. Verify the fix preserves the original functionality for legitimate URLs.

## Language-Specific Examples

### Python (requests)

**Before (vulnerable):**
```python
import requests
from flask import request

@app.route("/fetch")
def fetch_url():
    url = request.args.get("url")
    response = requests.get(url)
    return response.text
```

**After (fixed):**
```python
import ipaddress
import requests
from flask import request, abort
from urllib.parse import urlparse
import socket

ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_HOSTS = {"api.example.com", "cdn.example.com"}

def validate_url(url: str) -> str:
    """Validate that a URL is safe to fetch."""
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"Disallowed URL scheme: {parsed.scheme}")
    if not parsed.hostname:
        raise ValueError("URL has no hostname")
    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"Host not in allowlist: {parsed.hostname}")
    # Resolve and check IP to prevent DNS rebinding
    resolved_ip = socket.getaddrinfo(parsed.hostname, parsed.port or 443)[0][4][0]
    ip = ipaddress.ip_address(resolved_ip)
    if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
        raise ValueError(f"Resolved IP is in a private/reserved range: {resolved_ip}")
    return url

@app.route("/fetch")
def fetch_url():
    url = request.args.get("url")
    if not url:
        abort(400, description="Missing url parameter")
    try:
        validated_url = validate_url(url)
    except ValueError as e:
        abort(403, description=str(e))
    response = requests.get(validated_url, allow_redirects=False, timeout=10)
    return response.text
```

**Explanation:** The URL is parsed and validated against an allowlist of schemes and hosts. The hostname is resolved to an IP address that is checked against private ranges. Redirects are disabled to prevent bypass via redirect. A timeout is added to prevent hanging.

### Python (urllib)

**Before (vulnerable):**
```python
from urllib.request import urlopen

def fetch_data(user_url: str) -> bytes:
    response = urlopen(user_url)
    return response.read()
```

**After (fixed):**
```python
import ipaddress
import socket
from urllib.parse import urlparse
from urllib.request import urlopen, Request

ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_HOSTS = {"api.example.com", "data.example.com"}

def validate_url(url: str) -> str:
    """Validate that a URL is safe to fetch."""
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"Disallowed URL scheme: {parsed.scheme}")
    if not parsed.hostname:
        raise ValueError("URL has no hostname")
    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"Host not in allowlist: {parsed.hostname}")
    resolved_ip = socket.getaddrinfo(parsed.hostname, parsed.port or 443)[0][4][0]
    ip = ipaddress.ip_address(resolved_ip)
    if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
        raise ValueError(f"Resolved IP is in a private/reserved range: {resolved_ip}")
    return url

def fetch_data(user_url: str) -> bytes:
    validated_url = validate_url(user_url)
    req = Request(validated_url)
    response = urlopen(req, timeout=10)
    return response.read()
```

**Explanation:** Same validation approach applied to `urllib`. The `validate_url` function is reusable across the project.

### Java (HttpClient)

**Before (vulnerable):**
```java
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.URI;

public String fetchUrl(String userUrl) throws Exception {
    HttpClient client = HttpClient.newHttpClient();
    HttpRequest request = HttpRequest.newBuilder()
        .uri(URI.create(userUrl))
        .build();
    HttpResponse<String> response = client.send(request,
        HttpResponse.BodyHandlers.ofString());
    return response.body();
}
```

**After (fixed):**
```java
import java.net.InetAddress;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Set;

public class SafeHttpFetcher {

    private static final Set<String> ALLOWED_SCHEMES = Set.of("http", "https");
    private static final Set<String> ALLOWED_HOSTS = Set.of("api.example.com", "cdn.example.com");

    public static void validateUrl(String url) throws SecurityException {
        URI uri = URI.create(url);
        if (!ALLOWED_SCHEMES.contains(uri.getScheme())) {
            throw new SecurityException("Disallowed URL scheme: " + uri.getScheme());
        }
        String host = uri.getHost();
        if (host == null || host.isEmpty()) {
            throw new SecurityException("URL has no hostname");
        }
        if (!ALLOWED_HOSTS.contains(host)) {
            throw new SecurityException("Host not in allowlist: " + host);
        }
        try {
            InetAddress resolved = InetAddress.getByName(host);
            if (resolved.isLoopbackAddress() || resolved.isSiteLocalAddress()
                    || resolved.isLinkLocalAddress() || resolved.isAnyLocalAddress()) {
                throw new SecurityException("Resolved IP is private/reserved: " + resolved.getHostAddress());
            }
        } catch (java.net.UnknownHostException e) {
            throw new SecurityException("Cannot resolve hostname: " + host, e);
        }
    }

    public String fetchUrl(String userUrl) throws Exception {
        validateUrl(userUrl);
        HttpClient client = HttpClient.newBuilder()
            .followRedirects(HttpClient.Redirect.NEVER)
            .connectTimeout(Duration.ofSeconds(10))
            .build();
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(userUrl))
            .timeout(Duration.ofSeconds(10))
            .build();
        HttpResponse<String> response = client.send(request,
            HttpResponse.BodyHandlers.ofString());
        return response.body();
    }
}
```

**Explanation:** URL scheme and host are validated against allowlists. The hostname is resolved and the resulting IP is checked for private/reserved ranges. Redirects are disabled and timeouts are set.

### Node.js (axios)

**Before (vulnerable):**
```javascript
const axios = require('axios');

app.get('/fetch', async (req, res) => {
    const url = req.query.url;
    const response = await axios.get(url);
    res.send(response.data);
});
```

**After (fixed):**
```javascript
const axios = require('axios');
const { URL } = require('url');
const dns = require('dns').promises;
const net = require('net');

const ALLOWED_SCHEMES = new Set(['http:', 'https:']);
const ALLOWED_HOSTS = new Set(['api.example.com', 'cdn.example.com']);

const PRIVATE_RANGES = [
    /^127\./,
    /^10\./,
    /^172\.(1[6-9]|2[0-9]|3[01])\./,
    /^192\.168\./,
    /^169\.254\./,
    /^0\./,
    /^::1$/,
    /^fc00:/i,
    /^fd/i,
    /^fe80:/i,
];

function isPrivateIp(ip) {
    return PRIVATE_RANGES.some(pattern => pattern.test(ip));
}

async function validateUrl(urlString) {
    let parsed;
    try {
        parsed = new URL(urlString);
    } catch {
        throw new Error('Invalid URL');
    }
    if (!ALLOWED_SCHEMES.has(parsed.protocol)) {
        throw new Error(`Disallowed URL scheme: ${parsed.protocol}`);
    }
    if (!parsed.hostname) {
        throw new Error('URL has no hostname');
    }
    if (!ALLOWED_HOSTS.has(parsed.hostname)) {
        throw new Error(`Host not in allowlist: ${parsed.hostname}`);
    }
    const { address } = await dns.lookup(parsed.hostname);
    if (isPrivateIp(address)) {
        throw new Error(`Resolved IP is in a private range: ${address}`);
    }
    return urlString;
}

app.get('/fetch', async (req, res) => {
    const url = req.query.url;
    if (!url) {
        return res.status(400).json({ error: 'Missing url parameter' });
    }
    try {
        const validatedUrl = await validateUrl(url);
        const response = await axios.get(validatedUrl, {
            maxRedirects: 0,
            timeout: 10000,
        });
        res.send(response.data);
    } catch (err) {
        res.status(403).json({ error: err.message });
    }
});
```

**Explanation:** The URL is parsed and validated against scheme and host allowlists. DNS resolution is performed and the resolved IP is checked against private ranges. Axios is configured with `maxRedirects: 0` and a timeout.

### Node.js (node-fetch)

**Before (vulnerable):**
```javascript
const fetch = require('node-fetch');

app.post('/proxy', async (req, res) => {
    const { targetUrl } = req.body;
    const response = await fetch(targetUrl);
    const data = await response.text();
    res.send(data);
});
```

**After (fixed):**
```javascript
const fetch = require('node-fetch');
const { URL } = require('url');
const dns = require('dns').promises;

const ALLOWED_SCHEMES = new Set(['http:', 'https:']);
const ALLOWED_HOSTS = new Set(['api.example.com', 'cdn.example.com']);

// Reuse isPrivateIp and validateUrl from the axios example above,
// or extract into a shared utility module.

app.post('/proxy', async (req, res) => {
    const { targetUrl } = req.body;
    if (!targetUrl) {
        return res.status(400).json({ error: 'Missing targetUrl' });
    }
    try {
        const validatedUrl = await validateUrl(targetUrl);
        const response = await fetch(validatedUrl, {
            redirect: 'error',
            timeout: 10000,
        });
        const data = await response.text();
        res.send(data);
    } catch (err) {
        res.status(403).json({ error: err.message });
    }
});
```

**Explanation:** Same validation pattern. `node-fetch` is configured with `redirect: 'error'` to reject redirects and a timeout to prevent hanging.

## Testing Guidance

### Verifying the Fix Eliminates the Vulnerability

1. **Internal IP test**: Send a request with `url=http://127.0.0.1/admin` or `url=http://169.254.169.254/latest/meta-data/` (AWS metadata endpoint). The application must return a 403 or similar error.
2. **Scheme bypass test**: Send `url=file:///etc/passwd` or `url=gopher://internal-host`. Must be rejected.
3. **DNS rebinding test**: Use a domain that resolves to `127.0.0.1`. Must be rejected after DNS resolution.
4. **Redirect bypass test**: Use an allowed host that returns a 302 redirect to an internal IP. Must be rejected (redirects should be disabled or re-validated).
5. **Non-allowlisted host test**: Send a request to a valid external host not on the allowlist. Must be rejected.

### Verifying Existing Functionality Is Preserved

1. Send a request with a URL pointing to an allowlisted host over HTTPS. The request should succeed and return the expected data.
2. Verify that error messages do not leak internal IP addresses or infrastructure details.

### Semgrep Rules

After the fix, the following Semgrep rules should no longer trigger:
```yaml
rules:
  - id: ssrf-user-input-to-request
    patterns:
      - pattern-either:
          - pattern: requests.get($URL, ...)
          - pattern: requests.post($URL, ...)
          - pattern: urllib.request.urlopen($URL, ...)
          - pattern: axios.get($URL, ...)
          - pattern: fetch($URL, ...)
      - pattern-either:
          - pattern: $URL = request.args.get(...)
          - pattern: $URL = req.query.$PARAM
          - pattern: $URL = req.body.$PARAM
    message: "User input passed directly to HTTP client without validation"
    severity: ERROR
```

## Common Mistakes

1. **Validating only the scheme but not the host**: An attacker can still target internal hosts with `https://internal-server/`.
2. **Not resolving DNS before checking the IP**: A hostname like `evil.attacker.com` can resolve to `127.0.0.1` and bypass host-based checks.
3. **Allowing redirects**: Even if the initial URL is validated, a redirect can point to an internal resource. Always disable redirects or re-validate the redirect target.
4. **Using a denylist instead of an allowlist**: Denylist approaches inevitably miss edge cases (e.g., IPv6 mapped addresses, decimal IP encoding `http://2130706433/`). Always prefer an allowlist when possible.
5. **Not setting timeouts**: Without a timeout, a malicious URL can cause the server to hang indefinitely. Always set connect and read timeouts.
6. **Validating the URL string with regex only**: URL parsing is complex and regex-based validation is easily bypassed with URL encoding, case variations, or unusual syntax. Always use the language's built-in URL parser.
7. **Forgetting IPv6**: Private ranges exist in IPv6 too (`::1`, `fc00::/7`, `fe80::/10`). Ensure validation covers both IPv4 and IPv6.

## Steps

1. Use `Read` to open the file at `vulnerability.file_path` and review the `code_context` to understand how the URL reaches the HTTP client call.
2. Identify the HTTP client library in use (requests, urllib, HttpClient, axios, node-fetch, etc.).
3. Determine whether a `validate_url` utility already exists in the project by using `Grep` to search for URL validation patterns (e.g., `validate_url`, `is_safe_url`, `allowlist`, `ALLOWED_HOSTS`).
4. If no shared validation utility exists, create one in an appropriate shared module, or add the validation inline if the project is small.
5. Use `Edit` to add the URL validation call before the HTTP request.
6. Use `Edit` to configure the HTTP client to disable redirects and set a timeout.
7. Verify the fix compiles / parses correctly by checking syntax.
8. Confirm no other instances of the same vulnerable pattern exist in the file using `Grep`.

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
  "validation_added": "<string: description of the URL validation logic>",
  "notes": "<string: any additional context or recommendations>"
}
```

### Success Indicator

The `status` field is `"fixed"` and the HTTP client call is guarded by URL validation that checks scheme, host allowlist, and resolved IP.

### Failure Indicator

The `status` field is `"failed"` with a description of what prevented the fix.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **File not found** | Return `{"status": "failed", "reason": "File not found"}`. Do not retry. |
| **Cannot determine HTTP library** | Apply a generic validation pattern using the language's URL parser. Note in `notes` that the specific library was not identified. |
| **Allowlist not determinable** | Add a TODO comment with a placeholder allowlist and set `status` to `"needs_review"`. |
| **Multiple HTTP calls in the same function** | Fix all calls in the function. Report each in the `changes` array. |
| **Existing validation is partial** | Augment the existing validation rather than replacing it. Note the augmentation in `notes`. |

## Constraints

- **Preserve functionality**: The fix must not break legitimate HTTP requests to expected destinations.
- **No hardcoded secrets**: Do not embed API keys, tokens, or credentials in the validation logic.
- **Allowlist should be configurable**: Prefer reading allowed hosts from configuration (environment variable, config file) rather than hardcoding, unless the project has no config pattern.
- **Do not introduce new dependencies** unless absolutely necessary. Prefer standard library functions for URL parsing and IP validation.
- **Minimal diff**: Change only what is necessary to eliminate the vulnerability. Do not refactor unrelated code.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Edit` for code modifications. Use `Bash` only for syntax validation if needed.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
