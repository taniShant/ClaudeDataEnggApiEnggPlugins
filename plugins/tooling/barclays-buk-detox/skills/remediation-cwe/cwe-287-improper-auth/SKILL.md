---
name: cwe-287-improper-auth
description: "CWE-287: Improper Authentication Remediation — Remediate improper authentication vulnerabilities by replacing weak, missing, or bypassable authentication mechanisms with proper credential validatio"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-287: Improper Authentication Remediation
## Quick Start

This skill provides the fix pattern for CWE-287. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-287 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-287
- **CWE Name**: Improper Authentication
- **Severity**: Critical
- **OWASP Category**: A07:2021 - Identification and Authentication Failures

## Purpose

Remediate improper authentication vulnerabilities by replacing weak, missing, or bypassable authentication mechanisms with proper credential validation, secure session management, and multi-factor authentication support. This skill identifies code paths where authentication can be bypassed, credentials are improperly validated, sessions are poorly managed, or authentication decisions rely on client-controlled data, and transforms them into secure authentication flows using industry-standard practices. It covers Python (Flask, Django), Java (Spring Security), and JavaScript/Node.js (Express, Passport.js).

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file containing the authentication vulnerability.
  - `line_number` (integer, required): The 1-based line number of the vulnerable code.
  - `cwe_id` (string, required): Must be `CWE-287`.
  - `code_snippet` (string, optional): The flagged code snippet.
  - `auth_type` (string, optional): Type of authentication issue (`missing_auth`, `weak_validation`, `bypassable`, `broken_session`, `insecure_password_storage`). Auto-detected if not provided.
  - `context` (object, optional): Output from the `code_context_analyzer` skill.
- **repo_root** (optional, string): Absolute path to the repository root. Defaults to the current working directory.
- **language** (optional, string): Programming language (`python`, `java`, `javascript`). Auto-detected if not provided.
- **framework** (optional, string): Framework in use (`flask`, `django`, `spring`, `express`, `passport`). Auto-detected if not provided.

## Steps

1. **Read the vulnerable file and surrounding context.**
   - Use `Read` to open the file at `vulnerability.file_path`.
   - If `vulnerability.context` is provided, use it. Otherwise, read +/- 50 lines around `vulnerability.line_number`.

2. **Detect the language, framework, and authentication mechanism.**
   - Examine import statements, decorators, middleware, and configuration patterns.
   - Identify the authentication approach: session-based, token-based (JWT), API key, OAuth, basic auth, or custom.

3. **Classify the authentication vulnerability.**
   - **Missing authentication**: Sensitive endpoint lacks any authentication check.
   - **Weak credential validation**: Password comparison is insecure (plaintext comparison, weak hashing, timing-vulnerable comparison).
   - **Bypassable authentication**: Authentication logic can be circumvented through parameter manipulation, forced browsing, or logic flaws.
   - **Broken session management**: Sessions are predictable, do not expire, or are not invalidated on logout.
   - **Insecure password storage**: Passwords stored in plaintext or with weak/deprecated hashing algorithms.

4. **Apply the appropriate fix based on the vulnerability type.**
   - **Missing authentication**: Add authentication middleware or decorators to the unprotected endpoint.
   - **Weak credential validation**: Replace with constant-time comparison using bcrypt, argon2, or scrypt for password hashing and verification.
   - **Bypassable authentication**: Fix logic flaws, ensure server-side validation, remove client-side trust.
   - **Broken session management**: Configure secure session settings (httpOnly, secure, SameSite, expiration), regenerate session IDs after login, invalidate sessions on logout.
   - **Insecure password storage**: Migrate to bcrypt/argon2 hashing with proper salt.

5. **Apply the edit.**
   - Use `Edit` to replace the vulnerable code with the secure authentication pattern.
   - Add necessary imports (e.g., `from werkzeug.security import check_password_hash`, `import bcrypt`).
   - Preserve code formatting, indentation, and surrounding logic.

6. **Scan for similar patterns in the same file and related files.**
   - Use `Grep` to find other endpoints or functions with the same authentication weakness.
   - Apply the same fix to all instances.

7. **Verify the fix.**
   - Use `Read` to re-read the modified file and confirm the fix is syntactically correct.
   - Confirm that the authentication check cannot be bypassed and that credential validation is secure.

## Output Format

Return a JSON object:

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "auth_type": "<string: missing_auth | weak_validation | bypassable | broken_session | insecure_password_storage>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "original_code": "<string: the vulnerable code>",
      "fixed_code": "<string: the secure replacement>",
      "fix_type": "add_auth_check | secure_password_hash | constant_time_compare | session_hardening | logic_fix"
    }
  ],
  "similar_patterns_fixed": "<integer: count of additional similar patterns fixed>",
  "imports_added": ["<string: any new import statements added>"],
  "warnings": ["<string: any warnings about manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

### Success Indicator

`status` is `"success"` and all authentication weaknesses are resolved with secure patterns.

### Failure Indicator

`status` is `"error"` with a description in the `error` field.

## Vulnerable Pattern

Improper authentication occurs when an application does not adequately verify the identity of a user or system before granting access to protected resources. This includes missing authentication entirely, using weak credential validation, accepting client-side authentication decisions, or improperly managing sessions.

### Detection Patterns

**Missing authentication on sensitive endpoints:**
```
# Python Flask:       @app.route('/admin/...') without @login_required
# Django:             def admin_view(request): without @login_required or permission check
# Express:            app.get('/admin/...', handler) without auth middleware
# Spring:             @RequestMapping without @PreAuthorize or security config
```

**Weak password validation:**
```
# Plaintext compare:  if password == stored_password:
# MD5/SHA1 hashing:   hashlib.md5(password.encode()).hexdigest()
# No salt:            hashlib.sha256(password.encode()).hexdigest()
# Timing-vulnerable:  if user_token == expected_token:
```

**Bypassable authentication:**
```
# Client-side trust:  if request.headers.get('X-Is-Admin') == 'true':
# Parameter tampering: if request.args.get('authenticated') == 'true':
# Logic flaws:        if username == 'admin' or check_password(password):
```

**Broken session management:**
```
# No httpOnly:        session.cookie_httponly = False
# No secure flag:     session.cookie_secure = False
# No expiration:      session.permanent = True (without timeout)
# No regeneration:    (login without session ID regeneration)
```

**Regex detection patterns:**
```
# Plaintext compare:    if\s+.*password\s*==\s*.*:
# Weak hash:            (md5|sha1)\s*\(.*password
# Missing decorator:    @app\.route\(.*admin.*\)\s*\n\s*def\s+\w+\(
# Client trust:         request\.(headers|args|form)\.get\(.*(admin|auth|role)
```

## Fix Pattern

The general fix depends on the vulnerability subtype:

1. **Missing authentication**: Add an authentication check (decorator, middleware, or guard) that runs before the handler logic. The check must verify server-side session state or token validity.
2. **Weak credential validation**: Use bcrypt, argon2, or scrypt for password hashing and verification, with constant-time comparison.
3. **Bypassable authentication**: Remove trust in client-controlled data for authentication decisions. All authentication state must be verified server-side.
4. **Broken session management**: Configure sessions with httpOnly, Secure, SameSite attributes; set reasonable timeouts; regenerate session IDs after login; invalidate sessions on logout.

**Transformation steps:**
1. Identify the authentication weakness and its context.
2. Apply the appropriate secure pattern for the framework.
3. Ensure all authentication state is verified server-side.
4. Harden session configuration.
5. Add proper imports and middleware.

## Language-Specific Examples

### Python/Flask -- Missing Authentication

**Before (vulnerable):**
```python
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/admin/users', methods=['GET'])
def list_users():
    users = db.query(User).all()
    return jsonify([u.to_dict() for u in users])

@app.route('/admin/users/<int:uid>', methods=['DELETE'])
def delete_user(uid):
    user = db.query(User).get(uid)
    db.delete(user)
    db.commit()
    return jsonify({"status": "deleted"})
```

**After (fixed):**
```python
from flask import Flask, jsonify, request
from flask_login import login_required, current_user
from functools import wraps

app = Flask(__name__)

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            return jsonify({"error": "Forbidden"}), 403
        return f(*args, **kwargs)
    return decorated

@app.route('/admin/users', methods=['GET'])
@admin_required
def list_users():
    users = db.query(User).all()
    return jsonify([u.to_dict() for u in users])

@app.route('/admin/users/<int:uid>', methods=['DELETE'])
@admin_required
def delete_user(uid):
    user = db.query(User).get(uid)
    db.delete(user)
    db.commit()
    return jsonify({"status": "deleted"})
```

**Explanation:** An `admin_required` decorator is added that checks both authentication (via `@login_required`) and authorization (via `current_user.is_admin`). Both admin endpoints are now protected.

### Python -- Weak Password Validation

**Before (vulnerable):**
```python
import hashlib

def authenticate(username, password):
    user = db.get_user(username)
    if user and user.password == hashlib.md5(password.encode()).hexdigest():
        return user
    return None
```

**After (fixed):**
```python
import bcrypt

def authenticate(username, password):
    user = db.get_user(username)
    if user and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return user
    return None

def hash_password(password):
    """Hash a password for storage. Use when creating or updating user passwords."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
```

**Explanation:** MD5 is replaced with bcrypt, which is designed for password hashing. `bcrypt.checkpw()` performs constant-time comparison to prevent timing attacks. A `hash_password` helper is provided for creating new password hashes. Note: existing MD5 hashes must be migrated; a common strategy is to re-hash passwords on next successful login.

### Python/Flask -- Broken Session Management

**Before (vulnerable):**
```python
from flask import Flask, session, request, redirect

app = Flask(__name__)
app.secret_key = 'dev'

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = authenticate(username, password)
    if user:
        session['user_id'] = user.id
        return redirect('/dashboard')
    return redirect('/login')
```

**After (fixed):**
```python
import os
from flask import Flask, session, request, redirect

app = Flask(__name__)
app.secret_key = os.environ['FLASK_SECRET_KEY']
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=1800,  # 30 minutes
)

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = authenticate(username, password)
    if user:
        session.clear()  # Prevent session fixation
        session.regenerate()  # Regenerate session ID
        session['user_id'] = user.id
        session.permanent = True
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect('/login')
```

**Explanation:** The secret key is moved to an environment variable. Session cookies are configured with `httpOnly`, `Secure`, and `SameSite` attributes. The session is cleared and regenerated after login to prevent session fixation. A session lifetime is configured. The logout endpoint clears the session.

### Java/Spring -- Missing Authentication Configuration

**Before (vulnerable):**
```java
@Configuration
public class SecurityConfig extends WebSecurityConfigurerAdapter {
    @Override
    protected void configure(HttpSecurity http) throws Exception {
        http.authorizeRequests()
            .anyRequest().permitAll();
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
            .authorizeRequests()
                .antMatchers("/public/**", "/login", "/register").permitAll()
                .antMatchers("/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            .and()
            .formLogin()
                .loginPage("/login")
                .defaultSuccessUrl("/dashboard")
            .and()
            .sessionManagement()
                .maximumSessions(1)
                .and()
                .sessionFixation().migrateSession()
            .and()
            .logout()
                .logoutUrl("/logout")
                .invalidateHttpSession(true)
                .deleteCookies("JSESSIONID");
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
```

**Explanation:** The permissive `anyRequest().permitAll()` is replaced with a security configuration that requires authentication for most endpoints and admin role for admin endpoints. Session management is hardened with session fixation protection and a single-session limit. BCrypt is configured as the password encoder.

### JavaScript/Express -- Weak Token Comparison

**Before (vulnerable):**
```javascript
app.use('/api', (req, res, next) => {
  const token = req.headers['authorization'];
  if (token === 'Bearer secret-api-token-12345') {
    next();
  } else {
    res.status(401).json({ error: 'Unauthorized' });
  }
});
```

**After (fixed):**
```javascript
const crypto = require('crypto');

function constantTimeCompare(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string') return false;
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(Buffer.from(a), Buffer.from(b));
}

app.use('/api', (req, res, next) => {
  const authHeader = req.headers['authorization'];
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  const token = authHeader.slice(7);
  const expectedToken = process.env.API_TOKEN;
  if (!expectedToken) {
    console.error('API_TOKEN environment variable is not set');
    return res.status(500).json({ error: 'Internal server error' });
  }
  if (constantTimeCompare(token, expectedToken)) {
    next();
  } else {
    res.status(401).json({ error: 'Unauthorized' });
  }
});
```

**Explanation:** The hardcoded token is moved to an environment variable. String comparison is replaced with `crypto.timingSafeEqual()` to prevent timing attacks. The `Bearer ` prefix is properly parsed. A check ensures the environment variable is set.

### JavaScript/Express -- Session Hardening

**Before (vulnerable):**
```javascript
const session = require('express-session');

app.use(session({
  secret: 'keyboard cat',
  resave: false,
  saveUninitialized: true
}));
```

**After (fixed):**
```javascript
const session = require('express-session');

app.use(session({
  secret: process.env.SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  cookie: {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 30 * 60 * 1000  // 30 minutes
  },
  name: '__session',  // Custom name to avoid fingerprinting
  rolling: true  // Reset expiration on activity
}));
```

**Explanation:** The session secret is externalized to an environment variable. `saveUninitialized` is set to `false` to prevent creating sessions for unauthenticated users. Cookie attributes are hardened: `httpOnly` prevents JavaScript access, `secure` ensures HTTPS-only transmission in production, `sameSite` prevents CSRF, and `maxAge` enforces session expiration.

## Testing Guidance

### Verifying the Fix Eliminates the Vulnerability

1. **Missing authentication test**: Attempt to access the protected endpoint without authentication credentials. Verify a 401 or 403 response is returned.
2. **Credential validation test**: Attempt login with incorrect credentials and verify access is denied. Verify timing does not differ between valid and invalid usernames.
3. **Session fixation test**: Capture the session ID before login, authenticate, and verify the session ID changes after login.
4. **Session expiration test**: Wait for the session timeout period and verify the session is invalidated.
5. **Logout test**: After logout, verify the session is invalidated and cannot be reused.

### Automated Test Pattern

```python
def test_admin_endpoint_requires_auth(client):
    response = client.get('/admin/users')
    assert response.status_code in (401, 403)

def test_login_with_wrong_password(client):
    response = client.post('/login', data={'username': 'admin', 'password': 'wrong'})
    assert response.status_code in (401, 302)  # 302 redirect to login page

def test_session_regeneration(client):
    # Login and check session ID changes
    with client.session_transaction() as sess:
        old_sid = sess.sid if hasattr(sess, 'sid') else None
    client.post('/login', data={'username': 'admin', 'password': 'correct'})
    with client.session_transaction() as sess:
        new_sid = sess.sid if hasattr(sess, 'sid') else None
    assert old_sid != new_sid
```

### Semgrep Rules That Should Pass After Fix

```yaml
rules:
  - id: plaintext-password-comparison
    patterns:
      - pattern: |
          if $PASSWORD == $OTHER:
              ...
    message: "Plaintext password comparison detected"
    languages: [python]
    severity: ERROR
  - id: weak-password-hash
    patterns:
      - pattern-either:
          - pattern: hashlib.md5(...)
          - pattern: hashlib.sha1(...)
    message: "Weak hash algorithm used for password"
    languages: [python]
    severity: ERROR
```

### Verifying Functionality is Preserved

- Verify that legitimate users can still authenticate with correct credentials.
- Verify that session persistence works correctly for active users.
- Verify that password reset and account recovery flows still function.
- Test with various password characters (unicode, special characters, long passwords).

## Common Mistakes

1. **Adding authentication to the endpoint but not to related API calls.** If `/admin/users` is protected but `/api/users` is not, the attacker simply uses the API endpoint. Audit all endpoints that access the same resources.

2. **Using MD5 or SHA-256 for password hashing.** General-purpose hash functions are too fast for password hashing. Use bcrypt, argon2, or scrypt, which are designed to be computationally expensive and include salting.

3. **Rolling your own session management.** Custom session ID generation using `random.random()` or predictable patterns is insecure. Use framework-provided session management with cryptographically secure random number generators.

4. **Trusting client-side authentication state.** Checking `localStorage.getItem('isAdmin')` or a client-set cookie for authorization decisions is trivially bypassable. All authentication and authorization checks must be server-side.

5. **Not regenerating session IDs after login.** Without session regeneration, an attacker who knows the pre-authentication session ID can hijack the session after the user logs in (session fixation).

6. **Using the same response for "user not found" and "wrong password" separately.** Different error messages for invalid username versus invalid password allow username enumeration. Use a single generic message like "Invalid credentials."

7. **Implementing "remember me" by storing passwords in cookies.** Use a secure, random token stored server-side with an association to the user account instead.

8. **Not enforcing account lockout or rate limiting on login.** Without brute-force protection, attackers can attempt unlimited password guesses. Implement account lockout after N failed attempts or use rate limiting.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **File not found** | Return error JSON with `"error": "File not found: <path>"`. Do not retry. |
| **Cannot determine authentication framework** | Flag for manual review. Provide the general secure authentication pattern as guidance but do not apply an edit. |
| **Custom authentication protocol** | Analyze the custom logic and apply generic fixes (constant-time comparison, secure hashing). Flag for security review of the overall protocol. |
| **Authentication logic spans multiple files** | Trace the authentication flow across files using `Grep`. Apply fixes to each file individually. If the flow is too complex, flag for manual review. |
| **Password hashing migration required** | Note that existing password hashes must be migrated. Recommend a gradual migration strategy (re-hash on next login) rather than a bulk migration. |
| **Third-party SSO or OAuth** | Verify the integration follows the provider's security best practices. If misconfigured, flag for manual review. |

## Constraints

- **Preserve authentication flow**: The fix must not break the ability of legitimate users to authenticate.
- **No execution**: Do not run the application or attempt authentication against any system.
- **No credential exposure**: Do not output, log, or store actual credentials in the fix output.
- **Minimal diff**: Change only the authentication-related code. Do not refactor unrelated logic.
- **Backward compatibility**: If migrating password hashing, recommend a gradual migration strategy rather than breaking existing users' ability to log in.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Glob` for file discovery, `Edit` for applying fixes. Do not use `Bash` to run code or tests.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
