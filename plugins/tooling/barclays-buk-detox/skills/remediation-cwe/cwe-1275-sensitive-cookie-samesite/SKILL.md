---
name: cwe-1275-sensitive-cookie-samesite
description: "CWE-1275: Sensitive Cookie with Improper SameSite Attribute — "
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-1275: Sensitive Cookie with Improper SameSite Attribute
## Quick Start

This skill provides the fix pattern for CWE-1275. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-1275 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## Overview
Cookies containing sensitive data (session IDs, auth tokens) lack a proper SameSite attribute, allowing them to be sent in cross-site requests. This enables CSRF attacks and cross-site data theft.

## Vulnerability Pattern
```java
// VULNERABLE: No SameSite attribute
Cookie cookie = new Cookie("sessionId", sessionId);
cookie.setPath("/");
cookie.setHttpOnly(true);
response.addCookie(cookie);
// ERROR: SameSite not set, defaults to "None" (no protection)

// VULNERABLE: SameSite=None without Secure
Cookie cookie = new Cookie("authToken", token);
cookie.setAttribute("SameSite", "None");  // Without Secure, this is ineffective
// Must set Secure=true with SameSite=None

// VULNERABLE: SameSite=None on all cookies
// Even non-sensitive cookies may leak data in cross-site context
```

## Fix Strategy

1. **Set SameSite=Strict** on sensitive session/auth cookies (most secure)
2. **Set SameSite=Lax** on cookies that need cross-site reads (balanced)
3. **If SameSite=None is required** (rare), must pair with Secure=true + HTTPS
4. **Use HttpOnly + Secure + SameSite together** for defense-in-depth
5. **Configure globally in servlet container** when possible

## Remediation Examples

### Option A: SameSite=Strict for sensitive cookies
```java
// FIXED: Strict SameSite for session/auth cookies
Cookie cookie = new Cookie("sessionId", sessionId);
cookie.setPath("/");
cookie.setHttpOnly(true);
cookie.setSecure(true);
cookie.setAttribute("SameSite", "Strict");  // Prevents all cross-site requests
response.addCookie(cookie);
```

### Option B: SameSite=Lax for less sensitive cookies
```java
// FIXED: Lax SameSite for analytics or non-auth cookies
Cookie cookie = new Cookie("preferences", userPreferences);
cookie.setPath("/");
cookie.setHttpOnly(true);
cookie.setSecure(true);
cookie.setAttribute("SameSite", "Lax");  // Allows cross-site GET (but not POST)
response.addCookie(cookie);
```

### Option C: Spring Security configuration
```java
// FIXED: Spring Security with SameSite
@Configuration
@EnableWebSecurity
public class SecurityConfig extends WebSecurityConfigurerAdapter {
    @Override
    protected void configure(HttpSecurity http) throws Exception {
        http.sessionManagement()
            .sessionCookieConfig(cookie -> {
                cookie.setSecure(true);
                cookie.setHttpOnly(true);
                cookie.setSameSite("Strict");  // Strict protection
            });
    }
}
```

### Option D: Global servlet config
```java
// FIXED: Configure SameSite globally via web.xml
@WebListener
public class ServletConfig implements ServletContextListener {
    @Override
    public void contextInitialized(ServletContextEvent sce) {
        ServletContext context = sce.getServletContext();
        SessionCookieConfig config = context.getSessionCookieConfig();
        config.setSecure(true);
        config.setHttpOnly(true);
        config.setSameSite("Strict");  // All session cookies
    }
}
```

## SameSite Attribute Values

| Value | Behavior | Use Case |
|-------|----------|----------|
| **Strict** | Never sent in cross-site requests | Session IDs, auth tokens (most secure) |
| **Lax** | Sent in top-level navigation (GET) but not POST/AJAX | Tracking cookies, preferences (balanced) |
| **None** | Sent in all contexts (cross-site included) | Requires Secure=true, rare use case |

## Implementation Checklist
- [ ] Identify all Cookie creation code
- [ ] Set SameSite="Strict" on session/auth cookies
- [ ] Set SameSite="Lax" on non-sensitive cookies (if needed for cross-site reads)
- [ ] Never use SameSite="None" unless absolutely required
- [ ] If SameSite="None" is used, verify Secure=true is set
- [ ] Set HttpOnly=true and Secure=true on all sensitive cookies
- [ ] Test: verify cookies are not sent in cross-site form submissions

## Key Points
- **SameSite=Strict prevents CSRF** — cookies not sent in cross-site requests
- **SameSite=Lax is compromise** — allows cross-site GET (navigation), blocks POST
- **SameSite=None requires Secure** — must use HTTPS, otherwise the attribute is ignored
- **Defense-in-depth** — use SameSite + HttpOnly + Secure + CSRF tokens together
- **Severity**: High — enables CSRF and cross-site cookie theft

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
