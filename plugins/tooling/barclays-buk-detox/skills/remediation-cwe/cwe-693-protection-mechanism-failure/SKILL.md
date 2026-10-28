---
name: cwe-693-protection-mechanism-failure
description: "CWE-693: Protection Mechanism Failure — "
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-693: Protection Mechanism Failure
## Quick Start

This skill provides the fix pattern for CWE-693. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-693 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## Overview
A security mechanism (filter, firewall rule, authentication check) fails to function as intended, allowing attacks to bypass security controls.

## Vulnerability Pattern
```java
// VULNERABLE: Security filter is ineffective
@Override
public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
        throws IOException, ServletException {
    logger.info("Security check: " + request.getRequestURI());  // Logs but doesn't block
    chain.doFilter(request, response);  // Always continues
}

// VULNERABLE: Whitelist fails when config is missing
List<String> allowedIps = config.getList("allowed.ips");
if (allowedIps != null && allowedIps.contains(clientIp)) {
    grantAccess();
}
// If config is missing, allowedIps is null, check fails open
```

## Fix Strategy

1. **Verify protection mechanism actually blocks** — not just logs
2. **Fail-closed logic** — if security check fails, deny by default
3. **Test mechanism is active** — verify it's enabled in all environments
4. **Monitor/alert on bypasses** — log when security checks fire
5. **Have fallback protection** — defense-in-depth (multiple layers)

## Remediation Examples

### Option A: Fix ineffective filter
```java
// VULNERABLE: Filter only logs
public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
        throws IOException, ServletException {
    if (isMalicious(request)) {
        logger.warn("Blocked: " + request);
        return;  // Block, not just log
    }
    chain.doFilter(request, response);
}

// FIXED: Filter actually blocks
public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
        throws IOException, ServletException {
    if (isMalicious(request)) {
        logger.warn("Blocked: " + request);
        ((HttpServletResponse) response).sendError(HttpServletResponse.SC_FORBIDDEN);
        return;  // Block the request
    }
    chain.doFilter(request, response);
}
```

### Option B: Fail-closed whitelist
```java
// VULNERABLE: Fails open if config missing
List<String> allowedIps = config.getList("allowed.ips");
if (allowedIps != null && allowedIps.contains(clientIp)) {
    grantAccess();
}
// No else clause, continues if config is null

// FIXED: Fail-closed
List<String> allowedIps = config.getList("allowed.ips");
if (allowedIps == null || allowedIps.isEmpty()) {
    logger.error("No allowed IPs configured, denying all");
    denyAccess();
    return;
}
if (allowedIps.contains(clientIp)) {
    grantAccess();
} else {
    denyAccess();
}
```

### Option C: Verify protection is enabled
```java
// FIXED: Assert protection mechanism is active
if (!securityConfig.isFilterEnabled("XssFilter")) {
    throw new IllegalStateException("XssFilter must be enabled");
}

// Or, add to startup checks
@Component
public class SecurityCheck implements ApplicationContextAware {
    @PostConstruct
    public void verify() {
        FilterRegistry registry = context.getBean(FilterRegistry.class);
        if (!registry.isRegistered(XssFilter.class)) {
            throw new IllegalStateException("XssFilter not registered");
        }
    }
}
```

## Implementation Checklist
- [ ] Review all security filters and checks
- [ ] Verify each one actually blocks/denies, not just logs
- [ ] Verify fail-closed logic (deny by default if config missing)
- [ ] Test each protection mechanism is active in all environments
- [ ] Add alerts/logging when protection mechanisms trigger
- [ ] Implement defense-in-depth (multiple layers)

## Key Points
- **A protection mechanism that doesn't block is useless** — logging alone doesn't protect
- **Fail-closed is critical** — if you can't verify a check, deny
- **Configuration matters** — verify security settings are loaded correctly
- **Defense-in-depth** — multiple independent protection layers
- **Severity**: High — directly undermines security architecture

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
