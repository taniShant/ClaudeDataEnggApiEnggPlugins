---
name: cwe-384-session-fixation
description: "CWE-384: Session Fixation — "
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-384: Session Fixation
## Quick Start

This skill provides the fix pattern for CWE-384. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-384 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## Overview
Session fixation occurs when an attacker sets a user's session ID before authentication, then hijacks that session after the user authenticates. If session IDs are not regenerated after login, the attacker retains access.

## Vulnerability Pattern
```java
// VULNERABLE: Session ID not regenerated after authentication
HttpSession session = request.getSession();
String sessionId = session.getId();  // Get current session ID

if (authenticate(username, password)) {
    session.setAttribute("userId", userId);  // Reuse same session
    // ERROR: Session ID has not changed, attacker retains access
}

// VULNERABLE: Session attributes not cleared
session.setAttribute("authenticated", true);
// Attacker can set this before auth, then user logs in with same session
```

## Fix Strategy

1. **Regenerate session ID after authentication** — create new session, copy safe attributes
2. **Clear old session** after auth
3. **Set secure session flags** — HttpOnly, Secure, SameSite
4. **Invalidate sessions on logout** — don't reuse sessions
5. **Use framework mechanisms** (Spring Security handles this automatically)

## Remediation Examples

### Option A: Spring Security (automatic)
```java
// FIXED: Spring Security automatically regenerates sessions
@Configuration
@EnableWebSecurity
public class SecurityConfig extends WebSecurityConfigurerAdapter {
    @Override
    protected void configure(HttpSecurity http) throws Exception {
        http.sessionManagement()
            .sessionFixationProtection(SessionFixationProtectionStrategy.MIGRATE_SESSION);
            // "MIGRATE_SESSION" = default, regenerates after login
    }
}
```

### Option B: Manual session regeneration
```java
// FIXED: Manually regenerate session after authentication
if (authenticate(username, password)) {
    // Create new session
    HttpSession oldSession = request.getSession();
    HttpSession newSession = request.getSession(true);  // Force new session
    
    // Copy safe attributes (not auth state)
    Object[] attrs = oldSession.getAttributeNames();
    for (String attr : attrs) {
        if (!attr.equals("authenticated")) {  // Don't copy auth flags
            newSession.setAttribute(attr, oldSession.getAttribute(attr));
        }
    }
    
    // Set user ID and flags on NEW session
    newSession.setAttribute("userId", userId);
    newSession.setAttribute("authenticated", true);
    
    // Optional: invalidate old session
    oldSession.invalidate();
}
```

### Option C: Complete session reset
```java
// FIXED: Complete logout and re-authentication
public void logout(HttpServletRequest request) {
    HttpSession session = request.getSession(false);
    if (session != null) {
        session.invalidate();  // Destroy session
    }
    // Client must re-authenticate, gets new session ID
}

public void login(HttpServletRequest request, String userId) {
    HttpSession newSession = request.getSession(true);  // New session
    newSession.setAttribute("userId", userId);
    newSession.setAttribute("authenticated", true);
}
```

## Implementation Checklist
- [ ] Verify session ID is regenerated after authentication
- [ ] Verify old session is invalidated after auth
- [ ] Verify session flags are set: HttpOnly=true, Secure=true
- [ ] Verify SameSite attribute is set (Strict or Lax)
- [ ] Test: pre-set session ID before login, verify it changes after auth
- [ ] Test: cannot access authenticated resources with old session ID

## Key Points
- **Regenerate = generate new ID and destroy old** — not just clear attributes
- **Frameworks do this automatically** — Spring Security, Shiro handle it
- **Session flags matter** — HttpOnly prevents JavaScript theft, Secure prevents HTTP interception
- **SameSite=Lax/Strict** — prevents cross-site session fixation via XSS
- **Severity**: High — enables session hijacking

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
