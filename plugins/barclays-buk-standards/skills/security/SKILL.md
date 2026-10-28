---
name: security
description: BUK secure coding standards for SDF (Android/iOS React Native) and API layers. Derived from Barclays Secure Coding Practices v1.2.6. Covers data storage, transport security, authentication, API design, and mobile platform controls. Use when generating or reviewing code that handles sensitive data, authentication, network calls, or API endpoints.
user-invocable: false
---

# BUK Secure Coding Standards

> **Strawman — owned by BUK Principal Engineers.**
> Derived from Barclays Secure Coding Practices v1.2.6 (08/05/2026).
> Platform specialists (iOS, Android, web, API) should extend this with area-specific rules.
> Source document is Restricted — Internal. Do not reproduce verbatim in public artefacts.

---

## 1. Core Security Principles

These principles underpin all secure coding at Barclays. Apply them before writing any code that handles sensitive data, authentication, or network communication.

| Principle | What it means in practice |
|---|---|
| **Least Privilege** | Grant only the access actually needed — minimum permissions, ports, scopes |
| **Defence in Depth** | Layer controls — don't assume another part of the system has made data safe |
| **Don't Trust User Input** | Validate all input; canonicalise first, then validate, then use |
| **Allowlists, not Denylists** | Deny by default; explicitly permit what is allowed |
| **No Hard-coded Credentials** | Never put secrets, keys, or passwords in source code or config files |
| **Secure by Default** | Disable unused features, services, and APIs; use secure default configurations |
| **Minimise Attack Surface** | Only expose what is absolutely necessary; remove unused dependencies |
| **Assume Breach** | Log and monitor; encrypt at rest and in transit; enforce rate limiting |
| **Separation of Duties** | Separate auth, authorisation, and business logic; use different keys per environment |
| **Open Design** | Never rely on obscurity; use well-vetted algorithms and open standards |

---

## 2. Data Storage

### 2.1 Android

- **Never store sensitive data on external storage (SD card)** — use internal app storage only
- **Use AndroidKeyStore** for cryptographic keys — AES/CBC with `setUserAuthenticationRequired(true)`
- **File permissions**: use `MODE_PRIVATE`; never `MODE_WORLD_READABLE` or `MODE_WORLD_WRITEABLE`
- **SharedPreferences**: never store sensitive data here; it is plain-text XML
- **SQLite**: use parameterised queries; never concatenate user input into SQL strings
- **Sensitive data in memory**: use `char[]` or `byte[]`, not `String`; overwrite with random values when done

```kotlin
// ✅ Correct — parameterised query
val cursor = db.rawQuery("SELECT * FROM accounts WHERE id = ?", arrayOf(accountId))

// ❌ Wrong — SQL injection risk
val cursor = db.rawQuery("SELECT * FROM accounts WHERE id = '$accountId'", null)
```

### 2.2 iOS

- **Data Protection API**: apply `NSFileProtectionComplete` to all files containing sensitive data; never use `NSFileProtectionNone`
- **Keychain**: store small sensitive items (tokens, passwords, keys) in the iOS Keychain with `kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly`; remove all Keychain entries on app uninstall
- **NSUserDefaults**: never store sensitive data — it is plain-text `.plist`
- **Disable caching** wherever possible; disable screenshot capture in `applicationDidEnterBackground`

```swift
// ✅ Correct — file written with complete protection
data.write(to: fileURL, options: .completeFileProtection)

// ✅ Correct — Keychain with strict access control
let access = SecAccessControlCreateWithFlags(
    nil,
    kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly,
    .biometryCurrentSet,
    nil
)
```

---

## 3. Transport Security

### 3.1 Android

- **Use `HttpsUrlConnection`** for network calls; never manually construct `SSLSocket` — it requires manual certificate validation
- **Certificate pinning** is required for all sensitive network connections
- **Network Security Configuration**: trust system CAs only; do not allow user-installed CAs
- **Never allow HTTP** — redirect to HTTPS, or reject HTTP at the gateway
- **Disable request/response caching** in network clients

### 3.2 iOS

- **App Transport Security (ATS)**: leave default settings unchanged; always explicitly set `NSAllowsArbitraryLoads` to `false`; never set it globally
- **TLS minimum**: TLS 1.2 — enforced by ATS by default
- **Certificate pinning**: implement using `TrustKit` or equivalent; reject connections where certificate hashes do not match
- **Never weaken certificate validation** — do not override `allowsAnyHTTPSCertificateForHost`
- **WebViews**: use `WKWebView` for controlled content sources; use `SFSafariViewController` for general web pages; `UIWebView` is deprecated and must not be used

### 3.3 General (applies to all platforms)

- TLS 1.2 minimum; TLS 1.0, TLS 1.1, SSL v2/v3 are prohibited
- Prohibited cipher suites: RC4, DES, 3DES, MD5, export-grade
- TLS certificates: RSA 2048-bit minimum or ECDSA 256-bit
- mTLS required for service-to-service communication in sensitive environments

---

## 4. Authentication and Authorisation

### 4.1 Mobile — Biometrics

**Android:**
- Protect all sensitive application data with a KeyStore key that requires biometric unlock
- Key must be `setInvalidatedByBiometricEnrollment(true)` — invalidated if new biometrics added
- Never use `FingerprintManager` directly; use `BiometricPrompt` API

**iOS:**
- Never use `LAContext.evaluatePolicy` alone — it can be bypassed by runtime hooking
- Use a Keychain item protected by `kSecAccessControlBiometryCurrentSet` + `kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly`
- Verify that no new biometric credentials were enrolled since last successful authentication

### 4.2 API Authentication

- **OAuth 2.0 / OIDC with signed JWT** is the required authentication mechanism for all Barclays APIs
- JWT signing: **RS256 or ES256 only** — HS256 (symmetric) is prohibited; `alg:none` must be explicitly rejected
- JWT access token expiry: **15 minutes maximum**
- Refresh tokens must be rotated on each use
- MFA is required for all privileged or administrative API access
- **Never put tokens in URL query parameters** — pass via `Authorization: Bearer` header only
- Validate `iss`, `aud`, `exp`, `nbf`, and `sub` claims on every request

```
// ✅ Correct
GET /api/v1/accounts
Authorization: Bearer eyJhbGciOiJSUzI1NiJ9...

// ❌ Wrong — token in URL appears in logs and browser history
GET /api/v1/accounts?access_token=eyJhbGciOiJSUzI1NiJ9...
```

### 4.3 API Authorisation

- **BOLA / IDOR**: every endpoint accessing a resource by client-supplied ID must verify the requesting consumer owns or is authorised to access that specific object — on every request, server-side
- **BFLA**: enforce RBAC/ABAC at every endpoint and for every HTTP method; deny-by-default
- Resource identifiers exposed in responses must be non-predictable; use UUID v4 for customer-facing APIs
- **Never return internal object models directly** — use explicit DTO/response schemas (allowlist properties); automatic binding of request payloads to internal models is prohibited (mass assignment)

---

## 5. API Security

### 5.1 Input Validation

- Every API must have a complete, accurate OpenAPI 3.x specification maintained in sync with the implementation
- Schema validation must be enforced on all inbound requests — path parameters, query parameters, headers, and body
- Reject malformed requests with HTTP 400 and a generic error (do not expose schema details)
- Validate and sanitise all user-supplied URLs, hostnames, and IP addresses before use

### 5.2 SSRF Prevention

- Maintain a strict allowlist of permitted external domains and IP ranges
- Explicitly block requests to internal RFC 1918 ranges, loopback (`127.0.0.1`), and cloud metadata endpoints (`169.254.169.254`)
- Disable dangerous URL schemes: `file://`, `dict://`, `gopher://`, `ftp://`
- All outbound HTTP calls must route through the Barclays Egress Proxy
- Never return raw error responses from server-side HTTP calls to consumers

### 5.3 Security Headers

All API responses must include:

| Header | Required value |
|---|---|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `X-Content-Type-Options` | `nosniff` |
| `Cache-Control` | `no-store` (responses containing sensitive data) |
| `Content-Type` | Explicit media type + charset (e.g. `application/json; charset=utf-8`) |

The `Server` response header must not disclose server version or technology details.

### 5.4 Rate Limiting

- Apply rate limiting at multiple dimensions: per IP, per consumer token/API key, per endpoint, per product tier
- Use distributed rate limiting in multi-instance deployments — per-instance limiting is insufficient
- Return `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` headers on all responses
- Return HTTP 429 with `Retry-After` when limits are exceeded
- Authentication endpoints: implement exponential backoff and lockout after maximum 5 failed attempts
- Return identical responses (and timing) for invalid username vs. wrong password — prevent account enumeration

### 5.5 CORS

- Configure CORS to an explicit server-side allowlist of permitted origins
- The `Access-Control-Allow-Origin: *` wildcard combined with `Access-Control-Allow-Credentials: true` is prohibited

### 5.6 API Lifecycle

- Maximum two concurrent API versions — decommission older versions with deprecation headers (`Deprecation`, `Sunset`, `Link: rel="successor-version"`)
- Debug endpoints, Swagger UI, and diagnostic endpoints must be disabled in production
- HTTP TRACE must always be disabled
- API gateway administration interfaces must not be accessible from the internet; MFA is mandatory for admin access

---

## 6. Logging and Monitoring

- **Never log sensitive data**: passwords, tokens, full payment card numbers, session IDs, PII
- Log authentication and authorisation events with: user ID, resource, action, timestamp, result, failure reason
- Tag security events (`authFailure`, `validationFailure`, `rateLimitHit`) with a `securityEventType` field for SIEM filtering
- Propagate correlation IDs (`X-Correlation-ID`) across all service calls for distributed tracing
- Logs must be retained for minimum 12 months online, 12 months offline — or longer if PCI DSS scope applies
- Logs must be encrypted at rest (AES-256 minimum) and in transit (TLS 1.2+)
- Mobile: remove all logging from production builds — disable `Log.d`, `NSLog`, `print` in release configurations

---

## 7. Mobile Platform Controls (Android and iOS)

These controls apply to both Android and iOS unless stated otherwise.

### 7.1 Build Configuration

- **Never distribute a debug build** — production builds must use release configuration with debug flags disabled
- **Code obfuscation** is required for all production builds; strip symbol tables
- **Android**: set `debuggable=false` and `allowBackup=false` in `AndroidManifest.xml`; use ProGuard/R8 for obfuscation
- **iOS**: ensure "Release" build configuration in Xcode; anti-debugging via `PT_DENY_ATTACH`

### 7.2 Device Integrity Detection

**Android:**
- Implement root detection — terminate the application if the device is rooted
- Implement runtime hooking detection — terminate if Frida, Substrate, or other hooking frameworks are detected

**iOS:**
- Implement jailbreak detection (check for Cydia, SSH daemons, sandbox escape, `fork()` return value) — delete app data and terminate if jailbroken
- Implement anti-debugging via `PT_DENY_ATTACH`
- Detect runtime hooking by enumerating loaded dylibs for `MobileSubstrate.dylib`, `libcycript.dylib`, `FridaGadget.dylib`

### 7.3 Data Leakage

- **iOS**: use `applicationDidEnterBackground` to obscure all sensitive screen content before the system takes an automatic screenshot for the app switcher
- **Android/iOS**: disable clipboard access for sensitive fields (passwords, card numbers)
- **Both**: disable analytics collection of PII, screen touch events, or sensitive application data

### 7.4 Dynamic Code Loading

- **Android**: dynamic code loading (DexClassLoader) is strongly discouraged
- If required, code must come from a trusted source, be transmitted over HTTPS only, be stored in internal app storage only, and have integrity verified using SHA-256 before execution

### 7.5 URL Schemes and Deep Links

- Prefer **Universal Links (iOS)** / **App Links (Android)** over custom URL schemes
- All URL parameters must be validated; malformed or unexpected URLs must be discarded
- Never use URL schemes to trigger sensitive actions (password reset, payment initiation)

---

## 8. Secrets and Key Management

- **No hard-coded secrets** anywhere — not in source code, config files, scripts, or build files
- API keys and secrets must be stored in approved secrets management (CSM — Barclays Central Secrets Manager)
- Retrieve secrets programmatically at runtime; never inject at build time into artefacts committed to version control
- Use separate API keys for each environment (dev, test, prod)
- Rotate API keys on a defined schedule (3–6 months) and immediately on suspected compromise
- Implement automated secret scanning in the CI/CD pipeline (GitLab credential scanning is the Barclays standard)

---

## 9. Security Checklist

Use this when reviewing generated or written code:

### Data Storage
- [ ] No sensitive data on SD card / NSUserDefaults / SharedPreferences
- [ ] Android KeyStore / iOS Keychain used for credentials and keys
- [ ] iOS files use `NSFileProtectionComplete`; `NSFileProtectionNone` never used
- [ ] SQLite uses parameterised queries only

### Transport
- [ ] TLS 1.2+ enforced; `NSAllowsArbitraryLoads = false` on iOS
- [ ] Certificate pinning implemented for sensitive connections
- [ ] No HTTP connections allowed; caching disabled

### Authentication and Authorisation
- [ ] OAuth 2.0/OIDC with RS256 or ES256 JWTs
- [ ] JWT passed in `Authorization: Bearer` header only (never in URL)
- [ ] BOLA check: every resource access validates ownership server-side
- [ ] Response uses explicit DTO schema, not raw internal model

### API
- [ ] OpenAPI 3.x spec exists and is in sync with implementation
- [ ] Schema validation enforced on all inbound request fields
- [ ] Required security headers present on all responses
- [ ] Rate limiting configured; HTTP 429 returned on limit breach

### Logging
- [ ] No passwords, tokens, or PII in logs
- [ ] Security events tagged with `securityEventType`
- [ ] Correlation ID propagated across service calls
- [ ] Mobile production builds have all logging removed

### Mobile Build
- [ ] Release build; debug flag disabled; symbol tables stripped
- [ ] Code obfuscation applied
- [ ] Root/jailbreak detection implemented
- [ ] No hard-coded secrets; CI/CD secret scanning enabled

---

## 10. Barclays-Specific Tooling

| Control | Barclays tooling |
|---|---|
| Secrets management | CSM (Central Secrets Manager) |
| Secret scanning in CI/CD | GitLab credential scanning |
| Outbound HTTP from APIs | Barclays Egress Proxy |
| IAM / token issuance | Barclays IAM platform |
| SAST | Checkmarx (integrated in GitLab pipeline) |
| SCA (dependency scanning) | Nexus / Prisma |

---

## 11. Areas for Specialist Extension

This skill covers the cross-platform baseline. The following areas need platform-specific rules added by the relevant teams:

- **Android** — ProGuard/R8 configuration, `network_security_config.xml` specifics, Play Integrity API integration
- **iOS** — TrustKit pinning configuration, App Attest / DeviceCheck integration, Xcode build settings
- **Web/MCA** — Content Security Policy directives, CSRF protection, session management headers
- **API** — GraphQL-specific controls (introspection, query depth/complexity limits), mTLS certificate management, API gateway configuration specifics
