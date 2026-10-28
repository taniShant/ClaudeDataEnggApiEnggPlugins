---
name: cwe-1268-policy-priv-mismatch
description: "CWE-1268: Policy Uses Permissions That Are Incorrectly Mapped to the Intended Control — "
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-1268: Policy Uses Permissions That Are Incorrectly Mapped to the Intended Control
## Quick Start

This skill provides the fix pattern for CWE-1268. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-1268 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## Overview
Access control policies grant incorrect permissions, either too permissive or with mismatched intent (e.g., a policy intended to grant read-only access actually allows writes).

## Vulnerability Pattern
```java
// VULNERABLE: Policy grants all permissions
@Bean
public SecurityContext permissivePolicy() {
    return SecurityContextBuilder.create()
        .role("user")
        .grantAllPermissions()  // ERROR: Grants everything
        .build();
}

// VULNERABLE: Policy mismatches intent
public boolean canEdit(User user, Document doc) {
    if (user.hasRole("viewer")) {
        return true;  // ERROR: Viewers shouldn't edit
    }
    return false;
}

// VULNERABLE: Wildcard permissions
policy.grantPermission("user", "admin.*");  // Matches admin.read, admin.write, admin.delete
```

## Fix Strategy

1. **Principle of least privilege** — grant only necessary permissions
2. **Explicit permission checks** — not wildcard grants
3. **Map permissions to roles correctly** — viewer ≠ editor
4. **Validate policy logic** — ensure grants match intent
5. **Test permission boundaries** — verify each role can/cannot do expected actions

## Remediation Examples

### Option A: Explicit permission mapping
```java
// VULNERABLE: Policy too permissive
policy.grantPermission("user", "*");

// FIXED: Explicit permissions
policy.grantPermission("viewer", "document.read");
policy.grantPermission("editor", "document.read");
policy.grantPermission("editor", "document.write");
policy.grantPermission("admin", "document.read");
policy.grantPermission("admin", "document.write");
policy.grantPermission("admin", "document.delete");
policy.grantPermission("admin", "policy.manage");
```

### Option B: Role-based access control
```java
// FIXED: Clear role definitions
public enum Role {
    VIEWER("document.read"),
    EDITOR("document.read", "document.write"),
    ADMIN("document.read", "document.write", "document.delete", "policy.manage");
    
    private final Set<String> permissions;
    
    Role(String... perms) {
        this.permissions = Set.of(perms);
    }
    
    public boolean hasPermission(String perm) {
        return permissions.contains(perm);
    }
}
```

### Option C: Annotated permission checks
```java
// FIXED: Explicit permission checks on methods
@GetMapping("/document/{id}")
@RequirePermission("document.read")
public Document getDocument(@PathVariable String id) {
    return documentService.getDocument(id);
}

@PostMapping("/document/{id}")
@RequirePermission("document.write")
public Document updateDocument(@PathVariable String id, @RequestBody Document doc) {
    return documentService.update(id, doc);
}
```

### Option D: Deny-list for sensitive operations
```java
// FIXED: Explicit checks for dangerous operations
public void deleteDocument(String id) {
    User user = getCurrentUser();
    
    // Only admins can delete
    if (!user.hasRole("admin")) {
        throw new AccessDeniedException("Only admins can delete");
    }
    
    // Additional check: user must be owner or higher
    if (!user.hasPermission("document.delete")) {
        throw new AccessDeniedException("No delete permission");
    }
    
    documentService.delete(id);
}
```

## Implementation Checklist
- [ ] Review all role definitions and their permissions
- [ ] Verify each role has only necessary permissions
- [ ] Check for wildcard permissions (they often indicate over-granting)
- [ ] Test: each role should be able to do expected actions
- [ ] Test: each role should NOT be able to do unexpected actions
- [ ] Verify admin role is truly restricted (not everyone has it)

## Key Points
- **Least privilege principle** — less is better, can always add more
- **Explicit over implicit** — "user can read" is clearer than "admin.*"
- **Deny-by-default** — if not explicitly allowed, deny
- **Role separation** — viewer, editor, admin should have clear boundaries
- **Severity**: High — incorrect permissions directly enable unauthorized access

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
