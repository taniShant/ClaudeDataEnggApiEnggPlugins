---
name: cwe-reference
description: Comprehensive CWE vulnerability remediation reference covering 40+ CWEs with fix patterns, language examples, and validation guidance
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/cwe_reference/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE Vulnerability Remediation Reference
## Quick Start

This skill provides the CWE reference database used by the detox classifier to map vulnerability findings to specific CWE IDs.

```
# Loaded by detox-orchestrator-agent during the Classify Findings phase.
# Maps SAST findings → CWE ID → remediation skill routing.
```



## Purpose

Provides CWE-specific fix patterns, vulnerable code detection, and secure replacements for 40+ Common Weakness Enumerations. Used by the detox-fix-agent to apply the correct remediation strategy for each vulnerability type.

---

## CWE-89: SQL Injection

**Severity**: Critical | **OWASP**: A03:2021 - Injection

### Vulnerable Pattern
String concatenation/interpolation of user input into SQL queries:
- Python: `f"SELECT * FROM users WHERE name = '{name}'"`, `"SELECT..." + var`, `"SELECT..." % var`
- Java: `"SELECT * FROM users WHERE name = '" + username + "'"`
- JavaScript: `` `SELECT * FROM users WHERE name = '${name}'` ``

### Fix Pattern
Replace with parameterized queries (prepared statements):
- **Python psycopg2**: `cursor.execute("SELECT * FROM users WHERE name = %s", (name,))`
- **Python SQLAlchemy**: `conn.execute(text("SELECT * FROM users WHERE name = :name"), {"name": name})`
- **Java JDBC**: `PreparedStatement pstmt = conn.prepareStatement("SELECT * FROM users WHERE name = ?"); pstmt.setString(1, username);`
- **Node.js pg**: `pool.query('SELECT * FROM users WHERE name = $1', [name])`
- **Node.js mysql2**: `connection.execute('SELECT * FROM users WHERE name = ?', [name])`

### Dynamic Identifiers (table/column names)
Cannot be parameterized — use allowlist validation:
```python
ALLOWED_TABLES = {"users", "orders", "products"}
if table_name not in ALLOWED_TABLES:
    raise ValueError(f"Invalid table: {table_name}")
```

### Common Mistakes
- Parameterizing only some inputs (all must be parameterized)
- Using escaping instead of parameterization
- Wrapping placeholders in quotes (`'%s'` → wrong, `%s` → correct)
- Forgetting trailing comma for single-element tuple in Python: `(value,)`

---

## CWE-79: Cross-Site Scripting (XSS)

**Severity**: High | **OWASP**: A03:2021 - Injection

### Vulnerable Pattern
Untrusted data inserted into HTML without encoding:
- Template: `<div>{{ user_input | safe }}</div>` (Django), `<%- user_input %>` (EJS)
- JavaScript: `element.innerHTML = userInput`
- React: `dangerouslySetInnerHTML={{__html: userInput}}`

### Fix Pattern (by context)

**HTML body**: HTML entity encode (`<`, `>`, `&`, `"`, `'`)
- Python/Django: Remove `| safe` filter, use default autoescape
- Python/Flask: Use `markupsafe.escape()` or Jinja2 autoescape
- JavaScript: Use `textContent` instead of `innerHTML`
- React: Remove `dangerouslySetInnerHTML`, use JSX interpolation

**HTML attribute**: Attribute encode + ensure value is quoted
- `<input value="{{ user_input | escape }}">`

**JavaScript context**: JSON serialize or avoid embedding in `<script>`
- `<script>var data = JSON.parse('{{ data | tojson }}');</script>`

**URL context**: URL encode + validate scheme allowlist
- `encodeURIComponent(userInput)`, validate starts with `http://` or `https://`

### Common Mistakes
- Encoding in wrong context (HTML encode in JS context doesn't help)
- Using `sanitize` but allowing `<a href="javascript:...">`
- Only encoding on display, not on storage (stored XSS)

---

## CWE-22: Path Traversal

**Severity**: High | **OWASP**: A01:2021 - Broken Access Control

### Vulnerable Pattern
User input used directly in file paths without validation:
```python
file_path = os.path.join(base_dir, user_input)
open(file_path)  # user_input = "../../etc/passwd"
```

### Fix Pattern
1. Canonicalize path and verify it's within allowed directory:
```python
import os
base_dir = os.path.realpath("/safe/base/dir")
requested = os.path.realpath(os.path.join(base_dir, user_input))
if not requested.startswith(base_dir + os.sep):
    raise ValueError("Path traversal detected")
```

2. Java equivalent:
```java
Path base = Paths.get("/safe/base").toRealPath();
Path requested = base.resolve(userInput).toRealPath();
if (!requested.startsWith(base)) {
    throw new SecurityException("Path traversal detected");
}
```

### Common Mistakes
- Checking for `..` but not `%2e%2e` (URL-encoded)
- Using `startswith` on non-canonicalized paths
- Forgetting trailing separator in prefix check

---

## CWE-78: OS Command Injection

**Severity**: Critical | **OWASP**: A03:2021 - Injection

### Vulnerable Pattern
User input passed to shell commands:
```python
os.system(f"ping {host}")
subprocess.call(f"ls {directory}", shell=True)
```

### Fix Pattern
1. Use array form (no shell interpretation):
```python
subprocess.run(["ping", "-c", "1", host], shell=False, check=True)
```
2. Use `shlex.quote()` if shell is unavoidable:
```python
import shlex
subprocess.run(f"ping -c 1 {shlex.quote(host)}", shell=True)
```
3. Java: Use `ProcessBuilder` with argument array, never `Runtime.exec(String)`

### Common Mistakes
- Using `shell=True` with user input
- Quoting only some arguments
- Using allowlist for characters but missing edge cases

---

## CWE-798: Hardcoded Credentials

**Severity**: Critical | **OWASP**: A07:2021 - Identification and Authentication Failures

### Vulnerable Pattern
```python
password = "SuperSecret123!"
api_key = "sk-abc123..."
connection_string = "postgres://user:password@host/db"
```

### Fix Pattern
Replace with environment variables or secrets manager:
```python
import os
password = os.environ["DB_PASSWORD"]
api_key = os.environ["API_KEY"]
```
Or vault integration:
```python
from vault_client import get_secret
password = get_secret("db/password")
```

---

## CWE-918: Server-Side Request Forgery (SSRF)

**Severity**: High | **OWASP**: A10:2021 - SSRF

### Vulnerable Pattern
```python
url = request.args.get("url")
response = requests.get(url)  # User controls destination
```

### Fix Pattern
1. URL allowlist validation:
```python
from urllib.parse import urlparse
ALLOWED_HOSTS = {"api.example.com", "cdn.example.com"}
parsed = urlparse(url)
if parsed.hostname not in ALLOWED_HOSTS:
    raise ValueError("URL not in allowlist")
if parsed.scheme not in ("http", "https"):
    raise ValueError("Invalid scheme")
```
2. Block internal/private IPs (RFC 1918, loopback, link-local)

---

## CWE-611: XML External Entity (XXE)

**Severity**: High | **OWASP**: A05:2021 - Security Misconfiguration

### Vulnerable Pattern
```python
from xml.etree.ElementTree import parse
tree = parse(user_uploaded_xml)
```

### Fix Pattern
Disable external entity processing:
```python
# Python - defusedxml
from defusedxml.ElementTree import parse
tree = parse(user_uploaded_xml)

# Java
DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
dbf.setFeature("http://xml.org/sax/features/external-general-entities", false);
dbf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
```

---

## CWE-502: Insecure Deserialization

**Severity**: Critical | **OWASP**: A08:2021 - Software and Data Integrity Failures

### Vulnerable Pattern
```python
import pickle
data = pickle.loads(user_input)  # Remote code execution!
```

### Fix Pattern
1. Replace with safe formats (JSON):
```python
import json
data = json.loads(user_input)
```
2. If pickle is required, use hmac signature verification:
```python
import hmac, hashlib
expected_sig = hmac.new(SECRET_KEY, payload, hashlib.sha256).hexdigest()
if not hmac.compare_digest(received_sig, expected_sig):
    raise ValueError("Invalid signature")
```
3. Java: Use serialization filters (JEP 290)

---

## CWE-327: Weak Cryptographic Algorithm

**Severity**: High | **OWASP**: A02:2021 - Cryptographic Failures

### Vulnerable Pattern
```python
import hashlib
h = hashlib.md5(password.encode())  # MD5 is broken
h = hashlib.sha1(data)  # SHA-1 is deprecated
```

### Fix Pattern
Replace with strong algorithms:
```python
# For password hashing:
import bcrypt
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

# For data integrity:
import hashlib
h = hashlib.sha256(data)

# For encryption:
from cryptography.fernet import Fernet
# Replace DES/3DES/RC4 with AES-256-GCM
```

---

## CWE-200: Information Exposure

**Severity**: Medium | **OWASP**: A01:2021 - Broken Access Control

### Fix Pattern
- Remove stack traces from error responses
- Replace detailed errors with generic messages for end users
- Log details server-side only

```python
# Before
return {"error": str(exception), "traceback": traceback.format_exc()}

# After
logger.error("Operation failed", exc_info=True)
return {"error": "An internal error occurred. Please contact support."}
```

---

## CWE-287: Improper Authentication

**Severity**: Critical | **OWASP**: A07:2021

### Fix Pattern
- Add authentication check before protected operations
- Use framework authentication decorators
- Validate tokens/sessions before granting access

```python
# Django
from django.contrib.auth.decorators import login_required

@login_required
def protected_view(request):
    ...
```

---

## CWE-862: Missing Authorization

**Severity**: High | **OWASP**: A01:2021

### Fix Pattern
- Add authorization/permission checks
- Verify user has access to the specific resource

```python
# Before
def get_document(request, doc_id):
    return Document.objects.get(id=doc_id)

# After
def get_document(request, doc_id):
    doc = Document.objects.get(id=doc_id)
    if doc.owner != request.user:
        raise PermissionDenied()
    return doc
```

---

## CWE-352: Cross-Site Request Forgery

**Severity**: High | **OWASP**: A01:2021

### Fix Pattern
- Enable CSRF middleware
- Add CSRF tokens to forms
- Validate Origin/Referer headers for API endpoints

```python
# Django: Ensure CsrfViewMiddleware is in MIDDLEWARE
# Templates: {% csrf_token %} in forms
# AJAX: Include X-CSRFToken header
```

---

## CWE-434: Unrestricted File Upload

**Severity**: High | **OWASP**: A04:2021

### Fix Pattern
1. Validate file extension against allowlist
2. Validate MIME type (don't trust Content-Type header alone)
3. Limit file size
4. Store outside web root with random names
5. Scan for malware if possible

```python
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".docx"}
if not Path(filename).suffix.lower() in ALLOWED_EXTENSIONS:
    raise ValueError("File type not allowed")
```

---

## CWE-94: Code Injection

**Severity**: Critical | **OWASP**: A03:2021

### Fix Pattern
- Never use `eval()`, `exec()`, or equivalent with user input
- Replace dynamic code execution with data-driven approaches
- Use AST-based safe evaluation if mathematical expressions needed

```python
# Before
result = eval(user_expression)

# After (for math only)
import ast
tree = ast.parse(user_expression, mode='eval')
# Validate only contains safe nodes (numbers, operators)
for node in ast.walk(tree):
    if not isinstance(node, (ast.Expression, ast.BinOp, ast.Num, ast.Add, ast.Sub, ast.Mult, ast.Div)):
        raise ValueError("Unsafe expression")
result = eval(compile(tree, '<string>', 'eval'))
```

---

## CWE-295: Improper Certificate Validation

**Severity**: High | **OWASP**: A07:2021

### Fix Pattern
- Never disable SSL verification
- Remove `verify=False` from requests calls
- Remove `NODE_TLS_REJECT_UNAUTHORIZED=0`

```python
# Before
requests.get(url, verify=False)

# After
requests.get(url, verify=True)  # or just requests.get(url)
```

---

## CWE-311: Missing Encryption of Sensitive Data

**Severity**: High | **OWASP**: A02:2021

### Fix Pattern
- Encrypt sensitive data at rest using AES-256-GCM
- Use TLS for data in transit
- Use framework-provided encryption helpers

---

## CWE-400: Uncontrolled Resource Consumption

**Severity**: Medium | **OWASP**: A04:2021 (if DoS-applicable)

### Fix Pattern
- Add size limits on input
- Add rate limiting
- Add timeouts on operations
- Limit loop iterations

```python
# Before
data = request.body  # Unbounded

# After
MAX_SIZE = 10 * 1024 * 1024  # 10MB
if request.content_length > MAX_SIZE:
    raise ValueError("Request too large")
```

---

## CWE-770: Allocation Without Limits

**Severity**: Medium | **OWASP**: A04:2021

### Fix Pattern
- Set maximum allocation sizes
- Use bounded collections
- Implement pagination

---

## CWE-20: Improper Input Validation

**Severity**: High | **OWASP**: A03:2021

### Fix Pattern
- Validate input type, length, format, and range
- Use schema validation (Pydantic, JSON Schema, Bean Validation)
- Apply allowlist over blocklist

---

## CWE-601: Open Redirect

**Severity**: Medium | **OWASP**: A01:2021

### Fix Pattern
- Validate redirect URLs against allowlist of domains
- Only allow relative paths for redirects
- Block `javascript:` and `data:` schemes

```python
from urllib.parse import urlparse
ALLOWED_DOMAINS = {"example.com", "app.example.com"}
parsed = urlparse(redirect_url)
if parsed.hostname and parsed.hostname not in ALLOWED_DOMAINS:
    redirect_url = "/"
```

---

## CWE-532: Sensitive Data in Log Files

**Severity**: Medium | **OWASP**: A09:2021

### Fix Pattern
- Remove sensitive data from log statements
- Mask/redact PII, passwords, tokens, card numbers
- Use structured logging with field-level redaction

```python
# Before
logger.info(f"User login: {username} with password {password}")

# After
logger.info(f"User login: {username}")
```

---

## CWE-209: Error Message Information Exposure

**Severity**: Medium | **OWASP**: A04:2021

### Fix Pattern
- Return generic error messages to clients
- Log detailed errors server-side
- Never expose stack traces in production responses

---

## CWE-312: Cleartext Storage of Sensitive Information

**Severity**: High | **OWASP**: A02:2021

### Fix Pattern
- Encrypt sensitive data before storage
- Use password hashing (bcrypt/argon2) for passwords
- Use envelope encryption for secrets at rest

---

## CWE-319: Cleartext Transmission of Sensitive Information

**Severity**: High | **OWASP**: A02:2021

### Fix Pattern
- Enforce HTTPS for all sensitive communications
- Add HSTS headers
- Reject HTTP connections for sensitive endpoints

---

## CWE-321: Hardcoded Cryptographic Key

**Severity**: Critical | **OWASP**: A02:2021

### Fix Pattern
- Move keys to environment variables or KMS
- Use key rotation mechanisms
- Never commit keys to source control

---

## CWE-326: Inadequate Encryption Strength

**Severity**: High | **OWASP**: A02:2021

### Fix Pattern
- RSA: minimum 2048 bits (prefer 4096)
- AES: minimum 128 bits (prefer 256)
- Remove DES, 3DES, RC4, Blowfish with small keys

---

## CWE-328: Use of Weak Hash

**Severity**: High | **OWASP**: A02:2021

### Fix Pattern
- Replace MD5/SHA1 with SHA-256 or SHA-3 for integrity
- Replace MD5/SHA1 with bcrypt/argon2 for passwords

---

## CWE-347: Improper Verification of Cryptographic Signature

**Severity**: High | **OWASP**: A02:2021

### Fix Pattern
- Always verify signatures before trusting data
- Use constant-time comparison for signature verification
- Validate certificate chains completely

---

## CWE-348: IP Address Spoofing via X-Forwarded-For

**Severity**: Medium

### Fix Pattern
- Don't trust X-Forwarded-For for security decisions
- Use trusted proxy configuration
- Validate client IP from the connection, not headers

---

## CWE-384: Session Fixation

**Severity**: High | **OWASP**: A07:2021

### Fix Pattern
- Regenerate session ID after authentication
- Invalidate old session on login
- Use framework session management

---

## CWE-614: Sensitive Cookie Without Secure Flag

**Severity**: Medium | **OWASP**: A05:2021

### Fix Pattern
Set all security cookie flags:
```python
response.set_cookie("session", value, secure=True, httponly=True, samesite="Strict")
```

---

## CWE-639: Authorization Bypass Through User-Controlled Key (IDOR)

**Severity**: High | **OWASP**: A01:2021

### Fix Pattern
- Verify resource ownership before access
- Use indirect references (UUIDs mapped server-side)
- Add authorization checks on every data access

---

## CWE-942: Permissive CORS Policy

**Severity**: Medium | **OWASP**: A05:2021

### Fix Pattern
- Never use `Access-Control-Allow-Origin: *` for authenticated endpoints
- Allowlist specific origins
- Don't reflect Origin header without validation

---

## CWE-1275: Sensitive Cookie Without SameSite

**Severity**: Medium

### Fix Pattern
- Set `SameSite=Strict` or `SameSite=Lax` on sensitive cookies
- Combined with Secure and HttpOnly flags

---

## CWE-117: Log Injection

**Severity**: Medium | **OWASP**: A09:2021

### Fix Pattern
- Sanitize newlines and control characters from log input
- Use structured logging frameworks
- Never interpolate user input directly into log format strings

---

## CWE-183: Permissive Allowlist

**Severity**: Medium

### Fix Pattern
- Narrow allowlists to minimum required entries
- Use exact matches over patterns where possible
- Review allowlists regularly

---

## CWE-290: Authentication Bypass by Spoofing

**Severity**: High | **OWASP**: A07:2021

### Fix Pattern
- Don't trust client-supplied identity without verification
- Use cryptographic authentication (tokens, certificates)
- Validate at the server, never client-side only

---

## CWE-297: Improper Validation of Certificate with Host Mismatch

**Severity**: High

### Fix Pattern
- Enable hostname verification on TLS connections
- Don't override hostname verifiers
- Use standard TLS libraries with defaults

---

## CWE-306: Missing Authentication for Critical Function

**Severity**: Critical | **OWASP**: A07:2021

### Fix Pattern
- Add authentication requirement to unprotected endpoints
- Use framework auth middleware/decorators
- Apply defense in depth (auth at multiple layers)

---

## CWE-522: Insufficiently Protected Credentials

**Severity**: High | **OWASP**: A07:2021

### Fix Pattern
- Hash passwords with bcrypt/argon2id (never SHA/MD5)
- Use secure credential storage (vault, KMS)
- Implement credential rotation

---

## CWE-670: Always-Incorrect Control Flow

**Severity**: Medium

### Fix Pattern
- Fix logic errors in security checks
- Ensure authentication/authorization paths are correct
- Test both success and failure paths

---

## CWE-693: Protection Mechanism Failure

**Severity**: Medium | **OWASP**: A04:2021

### Fix Pattern
- Ensure security headers are present (CSP, X-Frame-Options, etc.)
- Verify protection mechanisms are correctly configured
- Don't disable security features for convenience

---

## CWE-787: Out-of-bounds Write (Buffer Overflow)

**Severity**: Critical | **OWASP**: A04:2021

### Fix Pattern
- Use bounds-checked array access
- Use safe string functions (strncpy instead of strcpy)
- Prefer managed languages/libraries with bounds checking

---

## CWE-90: LDAP Injection

**Severity**: High | **OWASP**: A03:2021

### Fix Pattern
- Escape special LDAP characters: `*`, `(`, `)`, `\`, NUL
- Use parameterized LDAP queries where supported
- Validate input format before query construction

---

## CWE-95: Eval Injection

**Severity**: Critical | **OWASP**: A03:2021

### Fix Pattern
Same as CWE-94 — never eval user input. Use safe alternatives.

---

## CWE-917: Expression Language Injection

**Severity**: High | **OWASP**: A03:2021

### Fix Pattern
- Never evaluate user-controlled strings as expression language (OGNL, EL, SpEL)
- Use parameterized/typed APIs instead of dynamic expression evaluation
- If evaluation is unavoidable, restrict the context (sandbox) and allowlist expressions
- Distinct from CWE-90 (LDAP Injection) — EL/OGNL/SpEL findings route here

---

## CWE-1188: Insecure Default Initialization

**Severity**: Medium | **OWASP**: A05:2021

### Fix Pattern
- Change insecure defaults to secure values
- Require explicit opt-in for insecure options
- Document security implications of configuration

---

## CWE-1268: Policy/Privilege Mismatch

**Severity**: High

### Fix Pattern
- Align declared policy with actual enforcement
- Review privilege assignments against least-privilege principle
- Add tests verifying access control enforcement

---

## Generic Fallback (Unmapped CWEs)

For CWEs not explicitly covered above:

1. Read the vulnerability description carefully
2. Identify the root cause (injection, missing validation, weak crypto, etc.)
3. Apply the closest matching fix pattern from the categories above
4. If no pattern matches, flag for manual review with:
   - Detailed description of the vulnerability
   - Suggested approach based on CWE documentation
   - Links to relevant CWE entry for human reviewer

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
