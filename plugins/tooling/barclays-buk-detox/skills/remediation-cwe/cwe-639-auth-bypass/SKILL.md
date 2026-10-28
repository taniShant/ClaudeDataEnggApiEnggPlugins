---
name: cwe-639-auth-bypass
description: "CWE-639: Authorization Bypass Through User-Controlled Key Remediation — Remediate authorization bypass vulnerabilities where users can modify authorization checks by controlling keys/parameters. For example, allowing users"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-639: Authorization Bypass Through User-Controlled Key Remediation
## Quick Start

This skill provides the fix pattern for CWE-639. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-639 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-639
- **CWE Name**: Authorization Bypass Through User-Controlled Key
- **Severity**: High
- **OWASP Category**: A01:2021 - Broken Access Control

## Purpose

Remediate authorization bypass vulnerabilities where users can modify authorization checks by controlling keys/parameters. For example, allowing users to change their own role or permissions by modifying request parameters.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file.
  - `line_number` (integer, required): The 1-based line number.
  - `cwe_id` (string, required): Must be `CWE-639`.

## Steps

1. **Identify user-controlled authorization checks.**
   - Look for code that uses user input to determine permissions.

2. **Fix by using server-side authorization.**
   - Determine permissions from authenticated user session, not user input.

3. **Apply the edit.**
   - Use `Edit` to replace user-controlled checks with server-side session.

## Output Format

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "fix_type": "session_based | database_lookup | role_verification"
    }
  ],
  "functions_fixed": "<integer>",
  "warnings": ["<string: manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

## Vulnerable Pattern

```python
# VULNERABLE: Role comes from user input!
role = request.args.get('role')
if role == 'admin':
    do_privileged_operation()

# VULNERABLE: User can change their own role!
user.role = request.form.get('role')
db.save(user)
```

## Fix Pattern

1. Get user identity from authenticated session, not user input.
2. Look up user permissions from database/session.
3. Use server-side role/permission store, never trust user input for authz.

## Language-Specific Examples

### Python - Flask

**Before (vulnerable):**
```python
@app.route('/admin/delete', methods=['POST'])
def delete_resource():
    role = request.form.get('role')  # VULNERABLE!
    if role == 'admin':
        resource_id = request.form.get('id')
        db.delete_resource(resource_id)
        return {"status": "deleted"}
    return {"error": "unauthorized"}, 403
```

**After (fixed):**
```python
from flask_login import login_required, current_user

@app.route('/admin/delete', methods=['POST'])
@login_required
def delete_resource():
    # Get role from authenticated session, not user input
    if current_user.role != 'admin':
        return {"error": "unauthorized"}, 403

    resource_id = request.form.get('id')
    db.delete_resource(resource_id)
    return {"status": "deleted"}
```

### Java - Spring Boot

**Before (vulnerable):**
```java
@PostMapping("/admin/delete")
public ResponseEntity<?> delete(@RequestParam String id,
                                @RequestParam String role) {
    if ("admin".equals(role)) {  // VULNERABLE!
        resourceService.delete(id);
        return ResponseEntity.ok("Deleted");
    }
    return ResponseEntity.status(HttpStatus.FORBIDDEN).build();
}
```

**After (fixed):**
```java
@PostMapping("/admin/delete")
@PreAuthorize("hasRole('ADMIN')")
public ResponseEntity<?> delete(@RequestParam String id,
                                Authentication authentication) {
    // Get role from Spring Security context, not user input
    if (!authentication.getAuthorities().stream()
            .anyMatch(a -> a.getAuthority().equals("ROLE_ADMIN"))) {
        return ResponseEntity.status(HttpStatus.FORBIDDEN).build();
    }

    resourceService.delete(id);
    return ResponseEntity.ok("Deleted");
}
```

### JavaScript - Express

**Before (vulnerable):**
```javascript
app.post('/admin/delete', (req, res) => {
    const role = req.body.role;  // VULNERABLE!
    if (role === 'admin') {
        db.deleteResource(req.body.id);
        res.json({ status: 'deleted' });
    } else {
        res.status(403).json({ error: 'unauthorized' });
    }
});
```

**After (fixed):**
```javascript
app.post('/admin/delete', (req, res) => {
    // Get role from authenticated session, not user input
    const user = req.session.user;
    if (!user || user.role !== 'admin') {
        return res.status(403).json({ error: 'unauthorized' });
    }

    db.deleteResource(req.body.id);
    res.json({ status: 'deleted' });
});
```

## Testing Guidance

1. **Test as non-admin user**: Ensure non-admin cannot delete resources.
2. **Test role parameter tampering**: Verify changing role parameter has no effect.
3. **Test session-based authz**: Verify only actual admin role in session can delete.

## Common Mistakes

1. **Trusting role from request parameters.**
2. **Allowing users to set their own role.**
3. **Not verifying role on every request.**
4. **Using client-side role checks only.**

## Constraints

- Server-side role/permission checks only.
- Never trust user input for authorization decisions.
- Always verify permissions from authenticated session/database.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
