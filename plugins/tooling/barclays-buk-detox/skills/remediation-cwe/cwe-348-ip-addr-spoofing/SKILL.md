---
name: cwe-348-ip-addr-spoofing
description: "CWE-348: Use of Less Trusted Source (IP Address from Request) — "
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-348: Use of Less Trusted Source (IP Address from Request)
## Quick Start

This skill provides the fix pattern for CWE-348. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-348 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## Overview
Security decisions are made based on IP addresses extracted from untrusted sources like `X-Forwarded-For` headers or `getRemoteAddr()`, which can be spoofed by clients.

## Vulnerability Pattern
```java
// VULNERABLE: Using X-Forwarded-For from untrusted client
String clientIp = request.getHeader("X-Forwarded-For");
if (isIpBlacklisted(clientIp)) {
    denyRequest();
}

// VULNERABLE: Trusting getRemoteAddr() through proxy
String ip = request.getRemoteAddr();
if (ip.startsWith("10.")) {
    grantInternalAccess();
}
```

## Fix Strategy

1. **Don't trust client IP headers** — clients can forge these
2. **Use network-layer verification** if IP-based decisions are needed
3. **Rely on TLS client certificates** or network-level authentication instead
4. **Validate IP headers only if from trusted proxies** (reverse proxy you control)
5. **Never use IP alone for security decisions** — combine with other auth factors

## Remediation Examples

### Option A: Remove IP-based checks (recommended)
```java
// FIXED: Don't make security decisions based on IP
// Use proper authentication instead
if (!isAuthenticated(request)) {
    sendUnauthorized();
}
```

### Option B: Validate IP only from trusted proxies
```java
// FIXED: Only trust X-Forwarded-For from known reverse proxy
String clientIp = request.getRemoteAddr();  // Get proxy IP first
if (TRUSTED_PROXY_IPS.contains(clientIp)) {
    clientIp = request.getHeader("X-Forwarded-For");  // Trust it only from proxy
}
auditLog(clientIp);  // Logging is OK; security decisions are not
```

### Option C: Use network-level IP filtering + auth
```java
// FIXED: IP filtering at network level, auth at application level
// Network: configure firewall/WAF to block IPs
// Application: always require proper authentication
if (!isUserAuthenticated(request)) {
    throw new AuthenticationException("No valid credentials");
}
```

## Implementation Checklist
- [ ] Find all code reading `X-Forwarded-For`, `CF-Connecting-IP`, or similar headers
- [ ] Find all code reading `request.getRemoteAddr()`
- [ ] Remove IP-based access control decisions (whitelist/blacklist)
- [ ] If IP logging is needed, document that it's for audit only, not security
- [ ] Verify all sensitive operations require proper authentication

## Key Points
- **IP spoofing is trivial** — any client can set `X-Forwarded-For: 1.2.3.4`
- **Proxies add headers** — but the client can forge them before reaching proxy
- **Network-level filtering is better** — firewall blocks before app sees traffic
- **Authentication is essential** — don't rely on IP for security decisions
- **Severity**: High — enables IP spoofing attacks

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
