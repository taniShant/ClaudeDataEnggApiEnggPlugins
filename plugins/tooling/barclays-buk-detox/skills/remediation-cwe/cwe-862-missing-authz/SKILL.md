---
name: cwe-862-missing-authz
description: "CWE-862: Missing Authorization Remediation — Remediate missing authorization vulnerabilities by adding role-based access control (RBAC) checks before sensitive operations. This skill identifies e"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-862: Missing Authorization Remediation
## Quick Start

This skill provides the fix pattern for CWE-862. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-862 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-862
- **CWE Name**: Missing Authorization
- **Severity**: High
- **OWASP Category**: A01:2021 - Broken Access Control

## Purpose

Remediate missing authorization vulnerabilities by adding role-based access control (RBAC) checks before sensitive operations. This skill identifies endpoints and functions that perform privileged actions without verifying that the authenticated user has the required permissions, and adds authorization checks that enforce the principle of least privilege. It covers Python (Flask, Django), Java (Spring Security), and JavaScript/Node.js (Express) frameworks, applying decorator-based, middleware-based, and annotation-based authorization patterns.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file containing the missing authorization check.
  - `line_number` (integer, required): The 1-based line number of the vulnerable code.
  - `cwe_id` (string, required): Must be `CWE-862`.
  - `code_snippet` (string, optional): The flagged code snippet.
  - `resource_type` (string, optional): The type of resource being accessed without authorization (e.g., `user_data`, `admin_function`, `financial_record`).
  - `context` (object, optional): Output from the `code_context_analyzer` skill.
- **repo_root** (optional, string): Absolute path to the repository root. Defaults to the current working directory.
- **language** (optional, string): Programming language (`python`, `java`, `javascript`). Auto-detected if not provided.
- **framework** (optional, string): Framework in use (`flask`, `django`, `spring`, `express`). Auto-detected if not provided.

## Steps

1. **Read the vulnerable file and surrounding context.**
   - Use `Read` to open the file at `vulnerability.file_path`.
   - If `vulnerability.context` is provided, use it. Otherwise, read +/- 50 lines around `vulnerability.line_number`.

2. **Detect the language, framework, and existing authorization patterns.**
   - Examine import statements, decorators, middleware, and configuration.
   - Use `Grep` to search for existing authorization patterns in the codebase (e.g., `@login_required`, `@permission_required`, `@PreAuthorize`, `authorize` middleware) to follow established conventions.

3. **Identify the sensitive operation and required permissions.**
   - Determine what resource or action the endpoint/function provides access to.
   - Determine what role or permission should be required (e.g., `admin`, `manager`, `owner`, or resource-specific permissions).
   - Check for Insecure Direct Object Reference (IDOR) patterns where a user can access another user's resources by changing an ID parameter.

4. **Apply the authorization check.**
   - **Decorator/annotation-based**: Add a role or permission check decorator before the function.
   - **Middleware-based**: Add authorization middleware to the route definition.
   - **Inline check**: Add an explicit permission check at the beginning of the function body (when decorators are not available or appropriate).
   - **Object-level authorization**: For IDOR patterns, verify that the authenticated user owns or has permission to access the specific resource.

5. **Apply the edit.**
   - Use `Edit` to add the authorization check.
   - Add necessary imports (e.g., `from django.contrib.auth.decorators import permission_required`).
   - Preserve code formatting, indentation, and surrounding logic.

6. **Scan for similar patterns in the same file and related files.**
   - Use `Grep` to find other endpoints or functions that access the same resource type without authorization.
   - Apply the same fix to all instances.

7. **Verify the fix.**
   - Use `Read` to re-read the modified file and confirm the authorization check is syntactically correct.
   - Confirm that the authorization check runs before any sensitive operation.

## Output Format

Return a JSON object:

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "resource_type": "<string: type of resource that was unprotected>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "original_code": "<string: the code without authorization>",
      "fixed_code": "<string: the code with authorization check added>",
      "fix_type": "decorator | middleware | inline_check | object_level_check"
    }
  ],
  "similar_patterns_fixed": "<integer: count of additional similar patterns fixed>",
  "imports_added": ["<string: any new import statements added>"],
  "permissions_required": ["<string: permissions that are now enforced>"],
  "warnings": ["<string: any warnings about manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

### Success Indicator

`status` is `"success"` and all unprotected operations now have authorization checks.

### Failure Indicator

`status` is `"error"` with a description in the `error` field.

## Vulnerable Pattern

Missing authorization occurs when an application performs a sensitive operation without checking whether the authenticated user has the necessary permissions. Even if the user is authenticated, they may not be authorized to access the specific resource or perform the specific action.

### Detection Patterns

**Endpoints without authorization checks:**
```
# Flask:        @app.route('/admin/...') with @login_required but no role check
# Django:       @login_required without @permission_required
# Express:      router.delete('/users/:id', authMiddleware, handler) without role check
# Spring:       @RequestMapping without @PreAuthorize or @Secured
```

**IDOR patterns (accessing resources by ID without ownership check):**
```
# Python:       user = User.query.get(request.args['user_id'])  # No ownership check
# JavaScript:   const order = await Order.findById(req.params.id)  # No ownership check
# Java:         User user = userRepo.findById(id)  // No ownership check
```

**Missing object-level authorization:**
```
# Python:       @app.route('/users/<id>/profile')  without checking current_user.id == id
# JavaScript:   app.put('/users/:id', ...) without req.user.id === req.params.id
# Java:         @PutMapping("/users/{id}") without principal.getId().equals(id)
```

**Regex detection patterns:**
```
# Admin routes without role check:  @app\.route\(.*admin.*\)(?!.*admin_required|permission_required)
# Delete without authz:             \.delete\(|DELETE.*(?!.*authorize|permission|role)
# IDOR candidates:                  (findById|query\.get|findOne)\(.*req\.(params|args|query)
```

## Fix Pattern

The general fix is to add an authorization check that verifies the user's permissions before executing the sensitive operation. The check should follow the principle of least privilege: grant only the minimum permissions required for the operation.

**Transformation steps:**
1. Identify the sensitive operation and the required permission level.
2. Determine the best authorization pattern for the framework (decorator, middleware, annotation, or inline).
3. Add the authorization check before the operation executes.
4. For IDOR patterns, add object-level ownership verification.
5. Return a 403 Forbidden response when authorization fails.

## Language-Specific Examples

### Python/Flask -- Role-Based Access Control

**Before (vulnerable):**
```python
from flask import Flask, jsonify, request
from flask_login import login_required, current_user

@app.route('/admin/users', methods=['GET'])
@login_required
def list_all_users():
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])

@app.route('/admin/users/<int:uid>', methods=['DELETE'])
@login_required
def delete_user(uid):
    user = User.query.get_or_404(uid)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"status": "deleted"})
```

**After (fixed):**
```python
from flask import Flask, jsonify, request, abort
from flask_login import login_required, current_user
from functools import wraps

def role_required(role):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            if not current_user.has_role(role):
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator

@app.route('/admin/users', methods=['GET'])
@role_required('admin')
def list_all_users():
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])

@app.route('/admin/users/<int:uid>', methods=['DELETE'])
@role_required('admin')
def delete_user(uid):
    user = User.query.get_or_404(uid)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"status": "deleted"})
```

**Explanation:** The `@login_required` decorator only verifies authentication, not authorization. A `role_required` decorator is added that checks whether the current user has the required role. Both admin endpoints now require the `admin` role. A 403 Forbidden response is returned if the role check fails.

### Python/Flask -- Object-Level Authorization (IDOR Prevention)

**Before (vulnerable):**
```python
@app.route('/users/<int:uid>/orders', methods=['GET'])
@login_required
def get_user_orders(uid):
    orders = Order.query.filter_by(user_id=uid).all()
    return jsonify([o.to_dict() for o in orders])

@app.route('/orders/<int:oid>', methods=['PUT'])
@login_required
def update_order(oid):
    order = Order.query.get_or_404(oid)
    order.status = request.json.get('status', order.status)
    db.session.commit()
    return jsonify(order.to_dict())
```

**After (fixed):**
```python
@app.route('/users/<int:uid>/orders', methods=['GET'])
@login_required
def get_user_orders(uid):
    if current_user.id != uid and not current_user.has_role('admin'):
        abort(403)
    orders = Order.query.filter_by(user_id=uid).all()
    return jsonify([o.to_dict() for o in orders])

@app.route('/orders/<int:oid>', methods=['PUT'])
@login_required
def update_order(oid):
    order = Order.query.get_or_404(oid)
    if order.user_id != current_user.id and not current_user.has_role('admin'):
        abort(403)
    order.status = request.json.get('status', order.status)
    db.session.commit()
    return jsonify(order.to_dict())
```

**Explanation:** Object-level authorization checks are added to verify that the current user owns the requested resource or has an admin role. Without these checks, any authenticated user could access or modify any other user's orders by changing the ID in the URL (IDOR vulnerability).

### Django -- Permission-Based Access Control

**Before (vulnerable):**
```python
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

@login_required
def manage_products(request):
    if request.method == 'POST':
        product = Product.objects.create(
            name=request.POST['name'],
            price=request.POST['price']
        )
        return JsonResponse({'id': product.id})
    products = Product.objects.all()
    return JsonResponse({'products': list(products.values())})
```

**After (fixed):**
```python
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse

@login_required
@permission_required('products.add_product', raise_exception=True)
def manage_products(request):
    if request.method == 'POST':
        product = Product.objects.create(
            name=request.POST['name'],
            price=request.POST['price']
        )
        return JsonResponse({'id': product.id})
    products = Product.objects.all()
    return JsonResponse({'products': list(products.values())})
```

**Explanation:** Django's `@permission_required` decorator is added to check that the user has the `products.add_product` permission. The `raise_exception=True` parameter returns a 403 Forbidden response instead of redirecting to the login page (which would be confusing for an already-authenticated user).

### Java/Spring -- Annotation-Based Authorization

**Before (vulnerable):**
```java
@RestController
@RequestMapping("/api")
public class UserController {

    @DeleteMapping("/users/{id}")
    public ResponseEntity<?> deleteUser(@PathVariable Long id) {
        userService.deleteUser(id);
        return ResponseEntity.ok(Map.of("status", "deleted"));
    }

    @PutMapping("/users/{id}/role")
    public ResponseEntity<?> updateUserRole(@PathVariable Long id,
                                             @RequestBody RoleUpdate update) {
        userService.updateRole(id, update.getRole());
        return ResponseEntity.ok(Map.of("status", "updated"));
    }
}
```

**After (fixed):**
```java
@RestController
@RequestMapping("/api")
public class UserController {

    @DeleteMapping("/users/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<?> deleteUser(@PathVariable Long id) {
        userService.deleteUser(id);
        return ResponseEntity.ok(Map.of("status", "deleted"));
    }

    @PutMapping("/users/{id}/role")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<?> updateUserRole(@PathVariable Long id,
                                             @RequestBody RoleUpdate update) {
        userService.updateRole(id, update.getRole());
        return ResponseEntity.ok(Map.of("status", "updated"));
    }
}
```

**Explanation:** Spring Security's `@PreAuthorize` annotation is added to enforce that only users with the `ADMIN` role can delete users or modify roles. This requires `@EnableGlobalMethodSecurity(prePostEnabled = true)` in the security configuration.

### Java/Spring -- Object-Level Authorization

**Before (vulnerable):**
```java
@GetMapping("/users/{id}/profile")
public ResponseEntity<?> getUserProfile(@PathVariable Long id) {
    UserProfile profile = profileService.findByUserId(id);
    return ResponseEntity.ok(profile);
}
```

**After (fixed):**
```java
@GetMapping("/users/{id}/profile")
@PreAuthorize("hasRole('ADMIN') or #id == authentication.principal.id")
public ResponseEntity<?> getUserProfile(@PathVariable Long id) {
    UserProfile profile = profileService.findByUserId(id);
    return ResponseEntity.ok(profile);
}
```

**Explanation:** The `@PreAuthorize` expression checks that the requesting user is either an admin or is requesting their own profile. Spring Expression Language (SpEL) is used to compare the path variable `id` with the authenticated principal's ID.

### JavaScript/Express -- Middleware-Based Authorization

**Before (vulnerable):**
```javascript
const authMiddleware = require('./middleware/auth');

router.get('/admin/reports', authMiddleware, async (req, res) => {
  const reports = await Report.find();
  res.json(reports);
});

router.delete('/admin/users/:id', authMiddleware, async (req, res) => {
  await User.findByIdAndDelete(req.params.id);
  res.json({ status: 'deleted' });
});
```

**After (fixed):**
```javascript
const authMiddleware = require('./middleware/auth');

function authorize(...roles) {
  return (req, res, next) => {
    if (!req.user || !roles.includes(req.user.role)) {
      return res.status(403).json({ error: 'Forbidden: insufficient permissions' });
    }
    next();
  };
}

router.get('/admin/reports', authMiddleware, authorize('admin'), async (req, res) => {
  const reports = await Report.find();
  res.json(reports);
});

router.delete('/admin/users/:id', authMiddleware, authorize('admin'), async (req, res) => {
  await User.findByIdAndDelete(req.params.id);
  res.json({ status: 'deleted' });
});
```

**Explanation:** An `authorize` middleware is added that checks whether the authenticated user's role is in the list of allowed roles. It is applied after the authentication middleware to ensure `req.user` is populated. Both admin routes now require the `admin` role.

### JavaScript/Express -- Object-Level Authorization (IDOR Prevention)

**Before (vulnerable):**
```javascript
router.get('/users/:id/documents', authMiddleware, async (req, res) => {
  const docs = await Document.find({ userId: req.params.id });
  res.json(docs);
});
```

**After (fixed):**
```javascript
router.get('/users/:id/documents', authMiddleware, async (req, res) => {
  if (req.user.id !== req.params.id && req.user.role !== 'admin') {
    return res.status(403).json({ error: 'Forbidden: access denied' });
  }
  const docs = await Document.find({ userId: req.params.id });
  res.json(docs);
});
```

**Explanation:** An object-level authorization check verifies that the authenticated user is requesting their own documents or has admin privileges. Without this check, any authenticated user could access any other user's documents by changing the ID in the URL.

## Testing Guidance

### Verifying the Fix Eliminates the Vulnerability

1. **Role-based access test**: Authenticate as a non-admin user and attempt to access admin-only endpoints. Verify a 403 Forbidden response is returned.
2. **IDOR test**: Authenticate as user A and attempt to access user B's resources by changing the user ID in the URL. Verify a 403 Forbidden response.
3. **Privilege escalation test**: Attempt to perform operations above the user's permission level (e.g., a regular user trying to delete other users).
4. **Unauthenticated test**: Attempt to access protected endpoints without authentication. Verify a 401 Unauthorized response.

### Automated Test Pattern

```python
def test_admin_endpoint_forbidden_for_regular_user(client, regular_user_token):
    response = client.get('/admin/users', headers={'Authorization': f'Bearer {regular_user_token}'})
    assert response.status_code == 403

def test_idor_prevention(client, user_a_token, user_b_id):
    response = client.get(f'/users/{user_b_id}/orders',
                          headers={'Authorization': f'Bearer {user_a_token}'})
    assert response.status_code == 403

def test_admin_can_access_admin_endpoint(client, admin_token):
    response = client.get('/admin/users', headers={'Authorization': f'Bearer {admin_token}'})
    assert response.status_code == 200
```

### Semgrep Rules That Should Pass After Fix

```yaml
rules:
  - id: missing-authorization-flask
    patterns:
      - pattern: |
          @app.route('/admin/...', ...)
          @login_required
          def $FUNC(...):
              ...
      - pattern-not: |
          @app.route('/admin/...', ...)
          @role_required(...)
          def $FUNC(...):
              ...
    message: "Admin endpoint missing role authorization check"
    languages: [python]
    severity: ERROR
```

### Verifying Functionality is Preserved

- Verify that authorized users can still perform all their permitted operations.
- Verify that admin users can access admin endpoints.
- Verify that users can access their own resources.
- Test with different roles to confirm each role has appropriate access levels.

## Common Mistakes

1. **Confusing authentication with authorization.** Adding `@login_required` checks who the user is but not what they are allowed to do. Authorization requires a separate role/permission check.

2. **Checking authorization on the client side only.** Hiding buttons or menu items in the UI does not prevent direct API access. Authorization must be enforced server-side.

3. **Using role checks instead of permission checks.** Hard-coding role names (e.g., `if role == 'admin'`) is fragile. Prefer permission-based checks (e.g., `has_permission('delete_user')`) that can be assigned to multiple roles.

4. **Missing object-level authorization.** Checking that a user has the `view_orders` permission is not enough if they can view any user's orders. Add ownership checks for resource-specific operations.

5. **Inconsistent authorization across equivalent endpoints.** If `/api/v1/users` is protected but `/api/v2/users` is not, the authorization is bypassed. Audit all routes that access the same resources.

6. **Applying authorization after the sensitive operation.** The authorization check must execute before the sensitive action. Placing it after (e.g., checking ownership after modifying a record) still allows unauthorized modifications.

7. **Not handling the 403 response properly.** Returning a 200 with an empty body instead of a proper 403 status code does not properly communicate the authorization failure and may confuse API consumers.

8. **Forgetting batch/bulk operation endpoints.** If a single-resource endpoint is protected but a bulk endpoint (`/api/users/bulk-delete`) is not, attackers can use the bulk endpoint to bypass authorization.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **File not found** | Return error JSON with `"error": "File not found: <path>"`. Do not retry. |
| **Cannot determine required permissions** | Flag for manual review. The developer must specify what roles/permissions should be required for each operation. |
| **No existing RBAC system in the codebase** | Recommend implementing one. Provide inline authorization checks as a temporary fix and flag for architectural review. |
| **Authorization logic in a separate service** | If authorization decisions are made by an external service (e.g., OPA, Casbin), verify the integration and flag for manual review. |
| **Complex multi-tenant authorization** | Multi-tenant systems require tenant isolation checks in addition to role checks. Flag for manual review if the tenant model is unclear. |
| **Framework not recognized** | Apply inline authorization checks (if/else at the top of the function) as a baseline and flag for framework-specific review. |

## Constraints

- **Preserve access for authorized users**: The fix must not prevent legitimate authorized users from performing their permitted operations.
- **No execution**: Do not run the application or attempt to access any endpoints.
- **Follow existing patterns**: If the codebase already has an authorization pattern (decorators, middleware, annotations), use the same pattern for consistency.
- **Minimal diff**: Add only the authorization check and required imports. Do not refactor unrelated code.
- **Default deny**: When in doubt, deny access. It is safer to temporarily block a legitimate operation than to leave a resource unprotected.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Glob` for file discovery, `Edit` for applying fixes. Do not use `Bash` to run code or tests.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
