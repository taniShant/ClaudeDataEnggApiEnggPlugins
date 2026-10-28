---
name: cwe-352-csrf
description: "CWE-352: Cross-Site Request Forgery (CSRF) Remediation — Remediate Cross-Site Request Forgery vulnerabilities by implementing CSRF tokens in forms, configuring SameSite cookie attributes, and adding origin/r"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-352: Cross-Site Request Forgery (CSRF) Remediation
## Quick Start

This skill provides the fix pattern for CWE-352. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-352 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-352
- **CWE Name**: Cross-Site Request Forgery (CSRF)
- **Severity**: High
- **OWASP Category**: A01:2021 - Broken Access Control

## Purpose

Remediate Cross-Site Request Forgery vulnerabilities by implementing CSRF tokens in forms, configuring SameSite cookie attributes, and adding origin/referer validation. This skill identifies state-changing endpoints (POST, PUT, DELETE) that lack CSRF protection and applies the appropriate defense mechanism based on the framework and architecture (server-rendered forms vs. SPA with API backend). It covers Python (Flask, Django), Java (Spring Security), and JavaScript/Node.js (Express with csurf or alternatives).

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file containing the CSRF vulnerability.
  - `line_number` (integer, required): The 1-based line number of the vulnerable code.
  - `cwe_id` (string, required): Must be `CWE-352`.
  - `code_snippet` (string, optional): The flagged code snippet.
  - `endpoint_type` (string, optional): `form_based`, `api_based`, or `mixed`. Auto-detected if not provided.
  - `context` (object, optional): Output from the `code_context_analyzer` skill.
- **repo_root** (optional, string): Absolute path to the repository root. Defaults to the current working directory.
- **language** (optional, string): Programming language (`python`, `java`, `javascript`). Auto-detected if not provided.
- **framework** (optional, string): Framework in use (`flask`, `django`, `spring`, `express`). Auto-detected if not provided.

## Steps

1. **Read the vulnerable file and surrounding context.**
   - Use `Read` to open the file at `vulnerability.file_path`.
   - If `vulnerability.context` is provided, use it. Otherwise, read +/- 50 lines around `vulnerability.line_number`.

2. **Detect the language, framework, and application type.**
   - Determine if the application uses server-rendered forms (HTML templates), a SPA with an API backend, or a mix.
   - Identify the session/cookie configuration.

3. **Identify the state-changing operation.**
   - Locate the endpoint handler for POST, PUT, PATCH, or DELETE requests.
   - Determine if it modifies server-side state (database writes, file changes, configuration updates, sending emails, etc.).

4. **Apply the appropriate CSRF protection.**
   - **Server-rendered forms**: Add a CSRF token to each form and validate it on the server side.
   - **SPA with API backend**: Use the double-submit cookie pattern or custom header pattern (`X-CSRF-Token`). Configure SameSite cookies.
   - **Both**: Enable framework-level CSRF middleware and configure SameSite cookies.

5. **Configure SameSite cookies.**
   - Set the `SameSite` attribute to `Lax` (default) or `Strict` on session cookies.
   - Set `Secure` and `HttpOnly` flags on session cookies.

6. **Apply the edit.**
   - Use `Edit` to add CSRF tokens to templates and validation middleware to the application.
   - Add necessary imports and middleware configuration.
   - Preserve code formatting, indentation, and surrounding logic.

7. **Scan for similar patterns in the same file and related files.**
   - Use `Grep` to find other state-changing endpoints without CSRF protection.
   - Apply the same fix to all instances.

8. **Verify the fix.**
   - Use `Read` to re-read the modified file and confirm the CSRF protection is correctly implemented.
   - Confirm tokens are present in forms and validated on submission.

## Output Format

Return a JSON object:

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "endpoint_type": "<string: form_based | api_based | mixed>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "original_code": "<string: the vulnerable code>",
      "fixed_code": "<string: the code with CSRF protection>",
      "fix_type": "csrf_token | samesite_cookie | origin_validation | double_submit | custom_header"
    }
  ],
  "similar_patterns_fixed": "<integer: count of additional similar patterns fixed>",
  "imports_added": ["<string: any new import statements added>"],
  "middleware_added": ["<string: any middleware additions>"],
  "templates_modified": ["<string: any template files that need CSRF tokens>"],
  "warnings": ["<string: any warnings about manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

### Success Indicator

`status` is `"success"` and all state-changing endpoints have CSRF protection.

### Failure Indicator

`status` is `"error"` with a description in the `error` field.

## Vulnerable Pattern

CSRF occurs when an attacker tricks a user's browser into making an unintended request to a web application where the user is authenticated. The browser automatically includes cookies (including session cookies) with the request, so the server cannot distinguish the forged request from a legitimate one.

### Detection Patterns

**State-changing endpoints without CSRF protection:**
```
# Flask:          @app.route('/transfer', methods=['POST']) without CSRF token check
# Django:         @csrf_exempt decorator on a view
# Express:        app.post('/transfer', handler) without CSRF middleware
# Spring:         http.csrf().disable() in security configuration
```

**Forms without CSRF tokens:**
```
# Django:         <form method="post"> without {% csrf_token %}
# Flask/Jinja2:   <form method="post"> without {{ csrf_token() }}
# Spring/Thymeleaf: <form method="post"> without th:action (which auto-adds tokens)
# EJS/Express:    <form method="post"> without CSRF token hidden input
```

**CSRF protection explicitly disabled:**
```
# Django:         @csrf_exempt
# Spring:         http.csrf().disable()
# Express:        // CSRF middleware not configured
```

**Regex detection patterns:**
```
# Django exempt:      @csrf_exempt
# Spring disable:     \.csrf\(\)\.disable\(\)
# Missing token:      <form.*method=["']post["'](?!.*csrf)
# POST without CSRF:  app\.(post|put|delete)\(.*(?!csrf)
```

## Fix Pattern

The general fix is to ensure that every state-changing request includes a secret token that the attacker cannot predict or obtain. The server validates this token before processing the request.

**Transformation steps:**
1. Enable CSRF middleware at the application level.
2. Generate a unique CSRF token per session (or per request for high-security applications).
3. Include the token in forms (as a hidden field) or in request headers (for AJAX/API requests).
4. Validate the token on the server before processing any state-changing request.
5. Configure SameSite cookies as defense-in-depth.

## Language-Specific Examples

### Python/Flask -- Flask-WTF CSRF Protection

**Before (vulnerable):**
```python
from flask import Flask, request, redirect

app = Flask(__name__)

@app.route('/transfer', methods=['POST'])
def transfer():
    amount = request.form['amount']
    to_account = request.form['to_account']
    perform_transfer(current_user, to_account, amount)
    return redirect('/dashboard')
```

**After (fixed):**
```python
from flask import Flask, request, redirect, render_template
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ['FLASK_SECRET_KEY']
csrf = CSRFProtect(app)

@app.route('/transfer', methods=['POST'])
def transfer():
    amount = request.form['amount']
    to_account = request.form['to_account']
    perform_transfer(current_user, to_account, amount)
    return redirect('/dashboard')
```

**Template (transfer.html):**
```html
<form method="post" action="/transfer">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <input type="text" name="to_account" placeholder="Account number">
    <input type="number" name="amount" placeholder="Amount">
    <button type="submit">Transfer</button>
</form>
```

**Explanation:** `Flask-WTF` provides CSRF protection by generating a unique token per session and validating it on every POST request. The `CSRFProtect(app)` call enables global protection. The template includes the token as a hidden form field via `{{ csrf_token() }}`. No changes are needed to the view function itself.

### Python/Django -- Built-in CSRF Protection

**Before (vulnerable):**
```python
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

@csrf_exempt
def update_profile(request):
    if request.method == 'POST':
        user = request.user
        user.email = request.POST['email']
        user.save()
        return JsonResponse({'status': 'updated'})
```

**After (fixed):**
```python
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

@login_required
def update_profile(request):
    if request.method == 'POST':
        user = request.user
        user.email = request.POST['email']
        user.save()
        return JsonResponse({'status': 'updated'})
```

**Template:**
```html
<form method="post" action="{% url 'update_profile' %}">
    {% csrf_token %}
    <input type="email" name="email" value="{{ user.email }}">
    <button type="submit">Update</button>
</form>
```

**Explanation:** The `@csrf_exempt` decorator is removed, re-enabling Django's built-in CSRF middleware (which is enabled by default via `django.middleware.csrf.CsrfViewMiddleware`). The template includes `{% csrf_token %}`, which renders a hidden input with the CSRF token.

### Python/Django -- AJAX Requests

**After (fixed, for AJAX):**
```javascript
// In the frontend JavaScript, read the CSRF token from the cookie and include it in headers
function getCsrfToken() {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        cookie = cookie.trim();
        if (cookie.startsWith(name + '=')) {
            return cookie.substring(name.length + 1);
        }
    }
    return null;
}

fetch('/api/update-profile', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify({ email: newEmail })
});
```

**Explanation:** For AJAX requests in Django, the CSRF token is read from the `csrftoken` cookie and sent in the `X-CSRFToken` header. Django's CSRF middleware accepts the token in this header by default.

### Java/Spring -- Re-enable CSRF Protection

**Before (vulnerable):**
```java
@Configuration
@EnableWebSecurity
public class SecurityConfig extends WebSecurityConfigurerAdapter {
    @Override
    protected void configure(HttpSecurity http) throws Exception {
        http
            .csrf().disable()
            .authorizeRequests()
                .anyRequest().authenticated();
    }
}
```

**After (fixed):**
```java
@Configuration
@EnableWebSecurity
public class SecurityConfig extends WebSecurityConfigurerAdapter {
    @Override
    protected void configure(HttpSecurity http) throws Exception {
        http
            .csrf()
                .csrfTokenRepository(CookieCsrfTokenRepository.withHttpOnlyFalse())
            .and()
            .authorizeRequests()
                .anyRequest().authenticated();
    }
}
```

**Explanation:** The `.csrf().disable()` is removed and replaced with a `CookieCsrfTokenRepository`. The `withHttpOnlyFalse()` allows the frontend JavaScript to read the CSRF token from the cookie and include it in requests. Spring Security automatically validates the token on state-changing requests.

**Thymeleaf Template:**
```html
<form th:action="@{/transfer}" method="post">
    <!-- Thymeleaf with th:action automatically includes the CSRF token -->
    <input type="text" name="toAccount" placeholder="Account number"/>
    <input type="number" name="amount" placeholder="Amount"/>
    <button type="submit">Transfer</button>
</form>
```

### JavaScript/Express -- CSRF Token Middleware

**Before (vulnerable):**
```javascript
const express = require('express');
const app = express();

app.post('/transfer', (req, res) => {
  const { toAccount, amount } = req.body;
  performTransfer(req.user, toAccount, amount);
  res.redirect('/dashboard');
});
```

**After (fixed):**
```javascript
const express = require('express');
const csrf = require('csrf');
const tokens = new csrf();
const app = express();

// Generate CSRF secret per session
app.use((req, res, next) => {
  if (!req.session.csrfSecret) {
    req.session.csrfSecret = tokens.secretSync();
  }
  next();
});

// Middleware to validate CSRF token on state-changing requests
function csrfProtection(req, res, next) {
  if (['GET', 'HEAD', 'OPTIONS'].includes(req.method)) {
    return next();
  }
  const token = req.body._csrf || req.headers['x-csrf-token'];
  if (!tokens.verify(req.session.csrfSecret, token)) {
    return res.status(403).json({ error: 'Invalid CSRF token' });
  }
  next();
}

app.use(csrfProtection);

// Make token available to templates
app.use((req, res, next) => {
  res.locals.csrfToken = tokens.create(req.session.csrfSecret);
  next();
});

app.post('/transfer', (req, res) => {
  const { toAccount, amount } = req.body;
  performTransfer(req.user, toAccount, amount);
  res.redirect('/dashboard');
});
```

**Template (EJS):**
```html
<form method="post" action="/transfer">
    <input type="hidden" name="_csrf" value="<%= csrfToken %>">
    <input type="text" name="toAccount" placeholder="Account number">
    <input type="number" name="amount" placeholder="Amount">
    <button type="submit">Transfer</button>
</form>
```

**Explanation:** A CSRF secret is generated per session and stored server-side. For each form render, a token is created from the secret and embedded as a hidden field. On state-changing requests, the middleware verifies the submitted token against the session secret.

### SameSite Cookie Configuration (All Frameworks)

**Express:**
```javascript
app.use(session({
  secret: process.env.SESSION_SECRET,
  cookie: {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    maxAge: 30 * 60 * 1000
  }
}));
```

**Flask:**
```python
app.config.update(
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
)
```

**Spring (application.properties):**
```properties
server.servlet.session.cookie.same-site=lax
server.servlet.session.cookie.secure=true
server.servlet.session.cookie.http-only=true
```

**Explanation:** The `SameSite=Lax` attribute prevents the browser from sending cookies with cross-site requests initiated by third-party websites (e.g., form submissions, POST redirects). This is defense-in-depth and should be combined with CSRF tokens, not used as a replacement.

## Testing Guidance

### Verifying the Fix Eliminates the Vulnerability

1. **Missing token test**: Submit a state-changing request without a CSRF token. Verify a 403 Forbidden response.
2. **Invalid token test**: Submit a request with an incorrect or expired CSRF token. Verify a 403 Forbidden response.
3. **Cross-origin test**: Create an HTML page on a different origin that submits a form to the protected endpoint. Verify the request is rejected.
4. **Token reuse test**: Submit the same CSRF token multiple times (if per-request tokens are used). Verify the second submission is rejected.

### Automated Test Pattern

```python
def test_csrf_token_required(client):
    response = client.post('/transfer', data={'to_account': '12345', 'amount': '100'})
    assert response.status_code == 403 or response.status_code == 400

def test_csrf_token_valid(client):
    # Get a page with a form to obtain a CSRF token
    get_response = client.get('/transfer')
    csrf_token = extract_csrf_token(get_response.data)
    response = client.post('/transfer', data={
        'to_account': '12345',
        'amount': '100',
        'csrf_token': csrf_token
    })
    assert response.status_code in (200, 302)
```

### Semgrep Rules That Should Pass After Fix

```yaml
rules:
  - id: csrf-exempt-django
    pattern: "@csrf_exempt"
    message: "CSRF protection is disabled for this view"
    languages: [python]
    severity: ERROR
  - id: csrf-disabled-spring
    pattern: ".csrf().disable()"
    message: "CSRF protection is disabled in Spring Security"
    languages: [java]
    severity: ERROR
```

### Verifying Functionality is Preserved

- Verify that forms still submit successfully when the CSRF token is included.
- Verify that AJAX requests work when the CSRF token is included in the header.
- Verify that GET requests are not affected by CSRF protection.
- Test multi-tab scenarios to ensure tokens remain valid across browser tabs.

## Common Mistakes

1. **Using CSRF protection only on some endpoints.** All state-changing endpoints must be protected, not just the most sensitive ones. An attacker could use an unprotected endpoint to change a user's email address, then use the password reset flow.

2. **Using GET requests for state-changing operations.** CSRF protection typically applies to POST/PUT/DELETE. If a GET request performs a state-changing operation (`/transfer?to=attacker&amount=1000`), CSRF tokens do not help. Change the endpoint to use POST.

3. **Disabling CSRF for API endpoints that use cookie authentication.** If an API uses session cookies for authentication, it needs CSRF protection regardless of whether it is called from a SPA. Only APIs using non-cookie authentication (e.g., Bearer tokens in the Authorization header) can safely skip CSRF protection.

4. **Token-per-request without handling concurrent tabs.** If tokens are single-use and per-request, opening multiple tabs will invalidate tokens in previously opened tabs. Use session-based tokens or a token bucket approach.

5. **Not including the CSRF token in AJAX requests.** When migrating from form submissions to AJAX, developers often forget to include the CSRF token in the request headers.

6. **Relying solely on SameSite cookies.** While `SameSite=Lax` provides good CSRF protection, it is not supported by all browsers and does not protect against subdomain attacks. Use CSRF tokens as the primary defense and SameSite as defense-in-depth.

7. **Storing the CSRF token in localStorage.** The CSRF token should be tied to the session and transmitted via cookies or rendered into the HTML page. Storing it in localStorage makes it accessible to XSS attacks.

8. **Exempting JSON APIs from CSRF protection.** The assumption that only forms can be CSRF-attacked is incorrect. While browsers restrict cross-origin JSON requests, there are bypass techniques. Protect JSON APIs that use cookie authentication.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **File not found** | Return error JSON with `"error": "File not found: <path>"`. Do not retry. |
| **Framework CSRF middleware not available** | Implement a manual CSRF token pattern using the framework's session system. Flag for review. |
| **Template engine not identified** | Identify templates by file extension and `Grep` for form tags. Provide the general CSRF token pattern and flag for manual insertion. |
| **API uses both cookie and token authentication** | Protect cookie-authenticated routes with CSRF tokens. Token-authenticated routes (Bearer header) do not need CSRF protection. Flag for review if mixed. |
| **Single-page application with no server-rendered forms** | Use the double-submit cookie pattern or synchronizer token pattern with AJAX headers. Flag for architectural review if the SPA framework is not identified. |
| **CSRF protection conflicts with CORS** | CORS and CSRF are complementary. Ensure CORS is properly configured to restrict cross-origin requests. Flag for manual review if CORS is permissive (`Access-Control-Allow-Origin: *`). |

## Constraints

- **Preserve form functionality**: Forms must continue to work correctly when CSRF tokens are included.
- **No execution**: Do not run the application or submit any forms.
- **No breaking GET requests**: CSRF validation should not apply to GET, HEAD, or OPTIONS requests.
- **Minimal diff**: Add only the CSRF middleware, token generation, and token insertion into forms. Do not refactor unrelated code.
- **Defense-in-depth**: Always recommend SameSite cookies in addition to CSRF tokens, but the primary fix must be CSRF tokens.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Glob` for file discovery, `Edit` for applying fixes. Do not use `Bash` to run code or tests.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
