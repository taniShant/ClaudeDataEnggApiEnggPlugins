---
name: cwe-614-secure-cookie
description: "CWE-614: Sensitive Cookie Without Secure Attribute — "
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-614: Sensitive Cookie Without Secure Attribute
## Quick Start

This skill provides the fix pattern for CWE-614. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-614 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## Overview
Cookies containing sensitive data (session IDs, auth tokens) are transmitted over insecure HTTP, allowing network eavesdropping. The Secure flag forces cookies to only be sent over HTTPS.

## Vulnerability Pattern
```java
// VULNERABLE: Cookie without Secure flag
Cookie cookie = new Cookie("sessionId", sessionId);
cookie.setPath("/");
response.addCookie(cookie);  // Can be sent over HTTP

// VULNERABLE: Explicitly set Secure=false
Cookie cookie = new Cookie("authToken", token);
cookie.setSecure(false);  // ERROR: Explicitly insecure
```

## Fix Strategy

1. **Set Secure flag on sensitive cookies** — forces HTTPS-only transmission
2. **Set HttpOnly flag** — prevents JavaScript from accessing the cookie
3. **Set SameSite attribute** — prevents cross-site request forgery
4. **Enforce HTTPS globally** — configure server to use HTTPS only
5. **Redirect HTTP to HTTPS** — ensure clients always use secure channel

## Remediation Examples

### Option A: Java Servlet Cookie
```java
// FIXED: Secure + HttpOnly + SameSite
Cookie cookie = new Cookie("sessionId", sessionId);
cookie.setPath("/");
cookie.setSecure(true);        // HTTPS only
cookie.setHttpOnly(true);      // JS cannot access
cookie.setAttribute("SameSite", "Strict");  // No cross-site requests
response.addCookie(cookie);
```

### Option B: Spring Security
```java
// FIXED: Spring Security cookie configuration
@Configuration
@EnableWebSecurity
public class SecurityConfig extends WebSecurityConfigurerAdapter {
    @Override
    protected void configure(HttpSecurity http) throws Exception {
        http.sessionManagement()
            .sessionCookieConfig(cookie -> {
                cookie.setSecure(true);
                cookie.setHttpOnly(true);
                cookie.setMaxAge(-1);  // Session cookie
                // SameSite is configured at server level
            });
    }
}
```

### Option C: Servlet configuration (web.xml or annotation)
```java
// FIXED: Configure session cookies globally
@WebListener
public class ServletConfig implements ServletContextListener {
    @Override
    public void contextInitialized(ServletContextEvent sce) {
        ServletContext context = sce.getServletContext();
        SessionCookieConfig config = context.getSessionCookieConfig();
        config.setSecure(true);
        config.setHttpOnly(true);
        config.setSameSite("Strict");
    }
}
```

## Implementation Checklist
- [ ] Identify all Cookie creation code
- [ ] Set Secure=true on all sensitive cookies (sessionId, auth tokens)
- [ ] Set HttpOnly=true on all sensitive cookies
- [ ] Set SameSite="Strict" or "Lax" on all cookies
- [ ] Verify server enforces HTTPS (redirect HTTP → HTTPS)
- [ ] Test: verify cookies are not sent over HTTP
- [ ] Test: verify JavaScript cannot access sensitive cookies

## Key Points
- **Secure flag prevents HTTP transmission** — only HTTPS
- **HttpOnly prevents JavaScript access** — mitigates XSS cookie theft
- **SameSite prevents cross-site requests** — stops CSRF attacks
- **HTTPS enforcement is global** — not just per-cookie
- **Severity**: High — enables session hijacking and credential theft

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
