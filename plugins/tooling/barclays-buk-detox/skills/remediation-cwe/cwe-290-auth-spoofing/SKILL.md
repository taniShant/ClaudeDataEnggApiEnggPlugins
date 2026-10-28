---
name: cwe-290-auth-spoofing
description: "CWE-290: Authentication Bypass by Spoofing — "
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-290: Authentication Bypass by Spoofing
## Quick Start

This skill provides the fix pattern for CWE-290. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-290 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## Overview
Authentication spoofing allows an attacker to bypass authentication by mimicking a legitimate user or session. This includes forging request parameters, spoofing network addresses, or bypassing auth checks with crafted headers.

## Vulnerability Pattern
```java
// VULNERABLE: Auth check via header only (can be spoofed)
if (request.getHeader("X-Auth-Token").equals("known-token")) {
    processAdminRequest();
}

// VULNERABLE: Auth check via request parameter
if ("admin".equals(request.getParameter("role"))) {
    grantAdminAccess();
}

// VULNERABLE: No real authentication, just presence check
if (request.getSession().getAttribute("user") != null) {
    processRequest();
}
```

## Fix Strategy

1. **Use cryptographic tokens** (JWT, session IDs) instead of custom headers
2. **Verify tokens server-side** — never trust client-provided role/auth status
3. **Tie auth to session identity** — authenticate once, bind to server-side session
4. **Reject spoofed auth parameters** — auth should never come from request params
5. **Use framework auth mechanisms** (Spring Security, Shiro) instead of custom logic

## Remediation Examples

### Option A: Use framework authentication
```java
// FIXED: Spring Security handles token verification
@GetMapping("/admin")
@PreAuthorize("hasRole('ADMIN')")
public void adminEndpoint() {
    // Spring Security verified the user and role
    processAdminRequest();
}
```

### Option B: Server-side session validation
```java
// FIXED: Validate session against server-side data
HttpSession session = request.getSession(false);
if (session == null) return false;

String userId = (String) session.getAttribute("authenticatedUserId");
if (userId == null) return false;

// Verify user role from database, not session attr
User user = database.getUser(userId);
return user.hasRole("ADMIN");
```

### Option C: JWT signature validation
```java
// FIXED: Verify JWT signature before trusting claims
String token = request.getHeader("Authorization").substring("Bearer ".length());
try {
    Claims claims = Jwts.parserBuilder()
        .setSigningKey(secretKey)
        .build()
        .parseClaimsJws(token)
        .getBody();
    String role = claims.get("role", String.class);
    // Use role, but verify it matches DB
} catch (JwtException e) {
    return false; // Invalid token
}
```

## Implementation Checklist
- [ ] Find all custom authentication checks (header, param, attribute)
- [ ] Replace with framework-based auth or proper session validation
- [ ] Verify all auth roles/permissions come from server-side data, not client
- [ ] Test: attempt to inject/modify auth headers and params
- [ ] Confirm: unauthenticated requests are rejected

## Key Points
- **Never trust client input for auth** — always verify server-side
- **Frameworks exist for a reason** — Spring Security, Shiro are battle-tested
- **Session fixation risk** — if sessions are not regenerated after auth, attackers can hijack
- **Severity**: Critical — direct auth bypass

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
