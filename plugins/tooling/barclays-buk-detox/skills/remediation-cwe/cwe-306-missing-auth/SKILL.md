---
name: cwe-306-missing-auth
description: "CWE-306: Missing Authentication for Critical Function Remediation — Remediate missing authentication on critical functions by adding authentication checks before sensitive operations. Functions that modify data, access"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-306: Missing Authentication for Critical Function Remediation
## Quick Start

This skill provides the fix pattern for CWE-306. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-306 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-306
- **CWE Name**: Missing Authentication for Critical Function
- **Severity**: Critical
- **OWASP Category**: A07:2021 - Identification and Authentication Failures

## Purpose

Remediate missing authentication on critical functions by adding authentication checks before sensitive operations. Functions that modify data, access sensitive information, or change system state must authenticate the user and verify they have authorization.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the unauthenticated function.
  - `line_number` (integer, required): The 1-based line number.
  - `cwe_id` (string, required): Must be `CWE-306`.

## Steps

1. **Identify the critical function** that lacks authentication.
   - Look for endpoint/function names that suggest administrative or sensitive operations.
   - Check for missing auth decorators or auth checks.

2. **Add authentication check.**
   - Verify user is authenticated.
   - Verify user has necessary permissions.

3. **Add proper error responses.**
   - Return 401 Unauthorized if not authenticated.
   - Return 403 Forbidden if authenticated but lacks permissions.

4. **Apply the edit.**
   - Use `Edit` to add authentication decorators or checks.

## Output Format

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "function_name": "<string: function name>",
      "auth_added": "decorator | guard_clause | middleware",
      "authorization_level": "authenticated | admin | custom_role"
    }
  ],
  "functions_secured": "<integer: count of functions with auth added>",
  "warnings": ["<string: manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

## Vulnerable Pattern

```python
@app.route('/admin/users', methods=['GET'])
def list_users():
    # No authentication check!
    return jsonify(db.get_all_users())

@app.route('/admin/config', methods=['POST'])
def update_config():
    # Missing auth - allows anyone to modify config
    config = request.json
    save_config(config)
    return {"status": "ok"}
```

## Fix Pattern

1. Add authentication decorator or middleware.
2. Add authorization check for required role/permission.
3. Return proper HTTP status codes.
4. Log authentication failures.

## Language-Specific Examples

### Python - Flask

**Before (vulnerable):**
```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/admin/delete_user/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    # No authentication!
    db.delete_user(user_id)
    return {"status": "deleted"}
```

**After (fixed):**
```python
from flask import Flask, request, jsonify
from functools import wraps

app = Flask(__name__)

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return {"error": "Missing authentication"}, 401

        # Verify token
        token = auth_header.replace('Bearer ', '')
        user = verify_token(token)
        if not user:
            return {"error": "Invalid token"}, 401

        if user['role'] != 'admin':
            return {"error": "Insufficient permissions"}, 403

        request.user = user
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/delete_user/<user_id>', methods=['DELETE'])
@require_auth
def delete_user(user_id):
    db.delete_user(user_id)
    return {"status": "deleted"}
```

### Java - Spring Boot

**Before (vulnerable):**
```java
@RestController
@RequestMapping("/api/admin")
public class AdminController {

    @DeleteMapping("/users/{userId}")
    public ResponseEntity<?> deleteUser(@PathVariable String userId) {
        userService.deleteUser(userId);
        return ResponseEntity.ok("Deleted");
    }
}
```

**After (fixed):**
```java
@RestController
@RequestMapping("/api/admin")
public class AdminController {

    @DeleteMapping("/users/{userId}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<?> deleteUser(@PathVariable String userId,
                                        Authentication authentication) {
        if (authentication == null || !authentication.isAuthenticated()) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        userService.deleteUser(userId);
        return ResponseEntity.ok("Deleted");
    }
}
```

### JavaScript - Express

**Before (vulnerable):**
```javascript
app.delete('/api/admin/users/:userId', (req, res) => {
    db.deleteUser(req.params.userId);
    res.json({ status: 'deleted' });
});
```

**After (fixed):**
```javascript
function requireAuth(req, res, next) {
    const token = req.headers.authorization?.replace('Bearer ', '');
    if (!token) {
        return res.status(401).json({ error: 'Missing authentication' });
    }

    const user = verifyToken(token);
    if (!user) {
        return res.status(401).json({ error: 'Invalid token' });
    }

    if (user.role !== 'admin') {
        return res.status(403).json({ error: 'Insufficient permissions' });
    }

    req.user = user;
    next();
}

app.delete('/api/admin/users/:userId', requireAuth, (req, res) => {
    db.deleteUser(req.params.userId);
    res.json({ status: 'deleted' });
});
```

## Testing Guidance

1. **Test without authentication**: Verify requests without auth header/token are rejected with 401.
2. **Test with invalid authentication**: Verify invalid tokens are rejected.
3. **Test with insufficient permissions**: Verify non-admin users get 403.
4. **Test with valid authentication**: Verify authenticated admin users can call the function.

## Common Mistakes

1. **Relying on client-side security checks only.**
2. **Not checking user permissions, only authentication.**
3. **Weak or missing token validation.**
4. **Auth check in the wrong location** (e.g., after the sensitive operation).
5. **Not logging authentication failures.**

## Constraints

- Always verify authentication on the server side.
- Fail closed (deny by default, allow only if authenticated and authorized).
- Log all authentication attempts and failures.
## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
