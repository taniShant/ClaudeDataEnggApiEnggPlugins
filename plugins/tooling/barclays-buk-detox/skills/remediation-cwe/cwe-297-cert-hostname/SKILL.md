---
name: cwe-297-cert-hostname
description: "CWE-297: Improper Validation of Certificate with Host Mismatch — "
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-297: Improper Validation of Certificate with Host Mismatch
## Quick Start

This skill provides the fix pattern for CWE-297. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-297 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## Overview
HTTPS certificate validation fails when the certificate's hostname (CN or SAN) does not match the server being connected to. This enables man-in-the-middle (MITM) attacks.

## Vulnerability Pattern
```java
// VULNERABLE: Disabled hostname verification
SSLContext sslContext = SSLContext.getInstance("TLS");
sslContext.init(null, new TrustManager[] { new TrustAllTrustManager() }, null);
HttpClient client = HttpClientBuilder.create()
    .setSSLContext(sslContext)
    .build();  // No hostname verification

// VULNERABLE: Custom verifier that always returns true
HostnameVerifier verifier = (hostname, session) -> true;
```

## Fix Strategy

1. **Enable hostname verification** — use default verifier or implement properly
2. **Match certificate CN or SAN** against the hostname being connected to
3. **Reject wildcards in invalid positions** — `*.example.com` should not match `a.b.example.com`
4. **Use framework defaults** — don't disable verification unless absolutely necessary
5. **Validate certificate chain** — trust store should contain only trusted CAs

## Remediation Examples

### Option A: Use framework defaults (Java HttpClient)
```java
// FIXED: Java 11+ HttpClient uses proper hostname verification by default
HttpClient client = HttpClient.newHttpClient();
HttpRequest request = HttpRequest.newBuilder()
    .uri(URI.create("https://api.example.com/data"))
    .build();
```

### Option B: Spring RestTemplate with proper SSL
```java
// FIXED: Spring RestTemplate with default SSL validation
RestTemplate restTemplate = new RestTemplate();
ResponseEntity<String> response = restTemplate.getForEntity("https://api.example.com", String.class);
```

### Option C: Apache HttpClient with verification
```java
// FIXED: Explicit hostname verification
SSLContext sslContext = SSLContexts.createDefault();  // Uses default trust store
CloseableHttpClient client = HttpClients.custom()
    .setSSLContext(sslContext)
    .setSSLHostnameVerifier(HttpClientBuilder.create().getSSLHostnameVerifier())
    .build();
```

### Option D: Custom hostname verifier (if required)
```java
// FIXED: Proper custom hostname verifier
HostnameVerifier verifier = new HostnameVerifier() {
    @Override
    public boolean verify(String hostname, SSLSession session) {
        try {
            Certificate[] certs = session.getPeerCertificates();
            if (certs.length == 0) return false;
            
            X509Certificate cert = (X509Certificate) certs[0];
            // Verify hostname matches certificate CN or SAN
            // Use HttpClientBuilder.DEFAULT_HOSTNAME_VERIFIER or similar
            return new HttpClientBuilder().build().getDefaultHostnameVerifier()
                .verify(hostname, session);
        } catch (Exception e) {
            return false;
        }
    }
};
```

## Implementation Checklist
- [ ] Search for `SSLContext`, `TrustManager`, `HostnameVerifier` in code
- [ ] Verify no custom trust managers that ignore certificates
- [ ] Verify no custom hostname verifiers that return `true` unconditionally
- [ ] Test: attempt MITM with mismatched certificate (should fail)
- [ ] Test: attempt MITM with wildcard bypass (should fail)

## Key Points
- **Hostname verification is not optional** — it's essential for HTTPS security
- **Wildcard certificates have rules** — `*.example.com` matches `api.example.com` but not `a.b.example.com`
- **Trust store matters** — verify it contains only trusted CAs, not all CAs
- **Severity**: Critical — enables MITM attacks

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
