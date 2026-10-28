# What is MCA2? — A Consolidated Guide

> **Version:** 1.0 | **Last Updated:** March 2026
> **Sources:** Code-harvested analysis of `mca-java-common` codebase + Confluence-derived framework documentation, cross-validated against source code.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Architecture Overview](#2-architecture-overview)
3. [Core Components](#3-core-components)
4. [Cross-Cutting Concerns](#4-cross-cutting-concerns)
5. [Design Patterns](#5-design-patterns)
6. [Technology Stack](#6-technology-stack)
7. [Module Catalog](#7-module-catalog)
8. [Getting Started](#8-getting-started)
9. [Appendix A: Cross-Validation Log](#appendix-a-cross-validation-log)

---

## 1. Introduction

### What is MCA?

**MCA** stands for **Multi Channel Applications** — Barclays' strategic framework for building services that can be delivered across all customer and colleague channels (web, mobile, IVR, branch, partner APIs) from a single codebase.

### What is MCA2?

MCA2 is the second major generation of the MCA framework, rebuilt on modern foundations:

- **Spring Boot 3.x** with Jakarta EE (replacing Spring Boot 2 / javax)
- **Java 21** (replacing Java 8/17)
- **Gradle 8.5** multi-module build
- **AspectJ compile-time weaving** for zero-overhead logging

The `mca-java-common` repository is a Gradle monorepo containing **60+ shared library modules** that provide the runtime infrastructure for MCA2 applications.

### MCA2 vs MCA1

| Aspect | MCA1 | MCA2 |
|--------|------|------|
| Java version | 8 / 17 | 21 |
| Spring Boot | 2.x | 3.5.10 |
| Servlet API | javax.servlet | jakarta.servlet |
| Module system | Maven | Gradle 8.5 |
| Auto-config | Legacy `spring.factories` | `AutoConfiguration.imports` |
| Context classes | Hand-written | Generated from `IOL_schema.json` |

MCA2 maintains backward compatibility with MCA1 services through the `legacy-common` extension module.

---

## 2. Architecture Overview

MCA2's architecture can be understood from two complementary perspectives: how it is **deployed** (4-tier model) and how its **internal modules** are organized (dependency tiers).

### 2.1 Deployment Architecture (4-Tier Model)

MCA2 applications are deployed in a layered topology where each tier has distinct responsibilities:

```
┌─────────────────────────────────────────────────────┐
│                 CLIENT / CHANNEL LAYER               │
│   Web (React/Angular)  ·  Mobile  ·  IVR  ·  Branch │
└──────────────────────────┬──────────────────────────┘
                           │ HTTPS
┌──────────────────────────▼──────────────────────────┐
│                    GATEWAY LAYER                     │
│              Secure Proxy / Secure Gateway            │
│  Authentication · Session · URI Obfuscation · DDoS   │
│  18 security/session filters · Request processors    │
└──────────────────────────┬──────────────────────────┘
                           │ HTTP (internal)
┌──────────────────────────▼──────────────────────────┐
│               EPS (EXPERIENCE) LAYER                 │
│          Business logic orchestration tier            │
│  @EnableExperienceAPI · 10 ordered filters           │
│  IOL context extraction · OAS validation             │
│  Response assembly · Exception handling              │
└──────────────────────────┬──────────────────────────┘
                           │ HTTP / JMS
┌──────────────────────────▼──────────────────────────┐
│              SYSTEMS OF RECORD LAYER                 │
│   Backend host services · Databases · MIS · BEM      │
└─────────────────────────────────────────────────────┘
```

**Two primary deployment patterns:**

- **FullServe** (colleague-facing): Synchronous flows, shared Secure Proxy instance serving multiple EPS applications
- **Digital** (customer-facing): Per-channel segregation, dedicated Secure Gateway per proposition

### 2.2 Internal Module Architecture (Dependency Tiers)

Within `mca-java-common`, modules are organized by dependency depth. Higher tiers depend on lower tiers; dependencies flow strictly downward.

```
TIER 1: FOUNDATIONAL
  common-utils · response-handling-core · exception-handling-core
  masking · router-api
  (No MCA dependencies — only external frameworks)

TIER 2: CONTEXT & INFRASTRUCTURE
  context · context-utils · web-utils · spring-context-utils · filter-core
  (Depend on Tier 1)

TIER 3: LOGGING & PERFORMANCE
  logging-aspects · logging-performance · logging-config-*
  (Depend on Tiers 1–2)

TIER 4: SERVICE CLIENTS & ROUTING
  service-client · service-client-starter · router-http
  (Depend on Tiers 1–3)

TIER 5: SECURE PROXY & GATEWAY
  secure-proxy-api · secure-proxy-core · secure-proxy-routing-gateway
  (Depend on Tiers 1–4)

TIER 6: SESSION STORAGE
  context-store-ehcache · context-store-mongo · context-store-rdb
  (Depend on Tiers 1–5)

TIER 7: EXPERIENCE API & APPLICATIONS
  eps-core · process · process-lib · referencedata · i18n
  (Depend on appropriate lower tiers)

EXTENSION TIER: OPTIONAL INTEGRATION
  bem-client · mis-client · legacy-common · service-locator
  jceks-spring-properties-processor · spring-boot-ssl · refresh-utils
```

### 2.3 Layered Module Pattern (API / Core / Starter)

Many features follow a three-part separation:

| Layer | Responsibility | Example |
|-------|---------------|---------|
| **API** | Interfaces, DTOs, no implementation | `secure-proxy-api` |
| **Core** | Business logic, algorithms | `secure-proxy-core` |
| **Starter** | Spring Boot auto-configuration, default beans | `service-client-starter` |

This pattern allows consuming applications to depend on interfaces only (API), use the implementation directly (Core), or get full auto-configuration (Starter).

---

## 3. Core Components

### 3.1 Secure Proxy (Gateway Tier)

The Secure Proxy is the gateway layer that sits between clients and EPS services. It handles security, session management, and request transformation.

**Module:** `mca-libraries/secure-proxy-core`
**Enable:** `@EnableSecureProxy`

#### Secure Proxy Filter Chain (11 filters)

The Secure Proxy uses relative ordering from `Ordered.HIGHEST_PRECEDENCE` (`Integer.MIN_VALUE`):

| Offset | Filter | Purpose | Conditional |
|--------|--------|---------|-------------|
| +0 | **CorrelationIdFilter** | Generate/extract correlation IDs | Always |
| +1 | **ExceptionFilter** | Catch unhandled exceptions, return JSON | Always |
| +10 | **BAMAuthFilterWrapper** | SSO authentication via BAM | `secure-proxy.sso.bam.enabled` |
| +25 | **SessionIdFilter** | Extract/validate session IDs from cookies | Always |
| +50 | **CookieFilter** | Add secure cookies to responses | Always |
| +100 | **AuthenticationFilter** | Validate auth, create IOL, manage tokens | Always |
| +105 | **OneTimeServiceFilter** | Validate one-time access tokens | `one-time-service.enabled` |
| +115 | **DdosFilter** | Rate limiting via `DdosPreventor` strategy | `ddos.filter.enabled` (opt-in) |
| +125 | **DynamicLoggingFilter** | Runtime log level adjustment | `allowDynamicLogging` |
| +150 | **SecurityHeaderFilter** | Add security headers to responses | Always |
| +250 | **RequestWhiteListingFilter** | Allow only whitelisted methods/URLs | `whitelist.enabled` (opt-in) |

#### URI Obfuscation

The Secure Proxy hides real backend paths behind UUID-based proxy URIs:

```
Real path:       /servicing/jserv/cardcontrol/cardpolicy
Obfuscated path: /mcaservice/cardControlDash_v1/getCardPolicy/a1b2c3d4-...
```

At runtime, `DeobfuscateUriPreProcessor` reverses this mapping using the endpoint registry stored in `ContextData`.

#### Request Processor Pipeline

When a client calls the router with an obfuscated URI, the request flows through ordered processors:

1. **ContextHeadersPreProcessor** — Inject IOL context headers from endpoint definition
2. **ValidationRequestPreProcessor** — Validate against OAS spec or inline JSON schema
3. **DeobfuscateUriPreProcessor** — Resolve obfuscated URI to real backend path
4. **HostResolverPreProcessor** — Resolve backend service host from `ServiceDefinition`
5. **DynamicLoggingProviderPreProcessor** — Apply dynamic log level headers

### 3.2 Experience Presentation Services (EPS Tier)

The EPS layer is where business logic lives. It provides the core framework for building microservices.

**Module:** `mca-libraries/eps-core`
**Enable:** `@EnableExperienceAPI`

#### EPS Filter Chain (10 filters)

EPS filters use absolute integer ordering:

| Order | Filter | Purpose | Required |
|-------|--------|---------|----------|
| **0** | **CorrelationIdFilter** | Generate/extract correlation IDs, request duration logging | Yes |
| **1** | **ExceptionFilter** | Wrap chain in try-catch, convert exceptions to `Response<T>` | Yes |
| **2** | **DisableSessionFilter** | Prevent HTTP session creation (enforce stateless) | Yes |
| **3** | **MultiReadRequestFilter** | Cache request body for multiple reads | Yes |
| **5** | **OAuthValidatorFilter** | Validate JWT/OAuth tokens | Conditional |
| **100** | **ContextFilter** | Extract IOL context from HTTP headers into request scope | Yes |
| **150** | **DdosFilter** | Rate limiting via `DdosPreventor` strategy | Conditional |
| **200** | **DynamicLoggingFilter** | Runtime log level changes via headers | Conditional |
| **300** | **ValidationFilter** | OpenAPI 3.0 request validation | Conditional |
| **550** | **PerfLogExclusionFilter** | Mark requests for perf-log exclusion | Conditional |

**Filter chain flow:**
```
HTTP Request
  → CorrelationIdFilter (set correlation ID in MDC)
    → ExceptionFilter (wrap in try-catch)
      → DisableSessionFilter (prevent sessions)
        → MultiReadRequestFilter (cache body)
          → OAuthValidatorFilter (validate JWT)
            → ContextFilter (extract IOL from headers)
              → DdosFilter (rate limit)
                → DynamicLoggingFilter (adjust log levels)
                  → ValidationFilter (OAS validation)
                    → PerfLogExclusionFilter
                      → DispatcherServlet → Controller
```

#### Shared vs Chain-Specific Filters

Both EPS and Secure Proxy chains share filter implementations from `mca-libraries/filter-core`:

| Filter | EPS | Secure Proxy | Notes |
|--------|-----|-------------|-------|
| CorrelationIdFilter | Order 0 | Offset +0 | Both; duration logging defaults differ |
| ExceptionFilter | Order 1 | Offset +1 | Both; same implementation |
| DdosFilter | Order 150 | Offset +115 | Both; different default enablement |
| DynamicLoggingFilter | Order 200 | Offset +125 | Both |
| DisableSessionFilter | Order 2 | — | EPS only |
| MultiReadRequestFilter | Order 3 | — | EPS only |
| OAuthValidatorFilter | Order 5 | — | EPS only |
| ContextFilter | Order 100 | — | EPS only |
| ValidationFilter | Order 300 | — | EPS only |
| SessionIdFilter | — | Offset +25 | Proxy only |
| AuthenticationFilter | — | Offset +100 | Proxy only |
| SecurityHeaderFilter | — | Offset +150 | Proxy only |

### 3.3 IOL Context System

The **Interoperability Language (IOL)** is a JSON-based context schema that propagates user, customer, account, device, process, and system information across MCA services via HTTP headers.

**Schema version:** 0.22 (JSON Schema Draft 04)
**Core module:** `mca-libraries/context`

#### Context Classes (~25 POJOs)

All context classes:
- Live in `com.barclays.global.mca.libs.context.data`
- Implement `Serializable`
- Use Jackson annotations for JSON mapping
- Include Jakarta validation annotations with regex patterns for security

**Root container:** `IOLSchema` aggregates all context sub-objects:

| Field | Type | Required | HTTP Header |
|-------|------|----------|-------------|
| `AID` | String | Yes | `X-AID` |
| `CORID` | String | No | `Correlation-ID` |
| `userContext` | UserContext | Yes | `X-UserContext` |
| `customerContext` | CustomerContext | No | `X-CustomerContext` |
| `accountContext` | AccountContext | No | `X-AccountContext` |
| `accountList` | AccountList | No | `X-AccountList` |
| `processContext` | List\<ProcessContext\> | No | `X-ProcessContext` |
| `systemContext` | SystemContext | Yes | `X-SystemContext` |
| `deviceContext` | DeviceContext | No | `X-DeviceContext` |
| `callerContext` | CallerContext | No | `X-CallerContext` |
| `caseContext` | CaseContext | No | `X-CaseContext` |
| `localeContext` | LocaleContext | No | `X-LocaleContext` |
| `secureContext` | SecureContext | No | `X-SecureContext` |
| `multipleCustomerContext` | MultipleCustomerContext | No | `X-MultipleCustomerContext` |
| `multipleAccountsContext` | MultipleAccountsContext | No | `X-MultipleAccountsContext` |
| `tokenIdentifiers` | List\<TokenIdentifier\> | No | (embedded) |

#### ProcessContext — Intentionally Simple

A common misconception is that `ProcessContext` is a rich domain object. In the actual code it is a flat key-value pair:

```java
public class ProcessContext implements Serializable {
    @NotNull @Pattern(regexp = "^[a-zA-Z0-9-]*$")
    private String key;

    @NotNull @Pattern(regexp = "^[a-zA-Z0-9 '.&/,-]*$")
    private String value;
}
```

Used as `List<ProcessContext>` in `IOLSchema`. Example: `[{"key":"workflow-id","value":"WF123"}, {"key":"step","value":"2"}]`

#### Context Propagation Flow

```
1. Client includes IOL as JSON in HTTP headers (X-UserContext, X-CustomerContext, etc.)
        ↓
2. ContextFilter extracts headers via ContextFilterHelper → WebUtils.getIOLSchema()
        ↓
3. IOLContextValidator validates against IOL_schema.json
        ↓
4. WebUtils stores in request attributes (request-scoped)
        ↓
5. Controllers access via @IOLContext annotation (argument resolver injection)
   or services access via WebUtils.getIOLSchema()
        ↓
6. Downstream propagation: serialize back to X-* headers for service-to-service calls
        ↓
7. Cleanup: ContextFilter finally-block clears thread-local (prevents memory leaks)
```

#### Context Access Patterns

**Pattern 1: `@IOLContext` annotation injection (recommended for controllers)**

```java
@RestController
@RequestMapping("/api/cards")
public class CardController {
    @GetMapping("/{cardId}")
    public ResponseEntity<CardDetails> getCard(
            @IOLContext IOLSchema context,
            @PathVariable String cardId) {
        UserContext user = context.getUserContext();
        // ...
    }
}
```

**Pattern 2: `WebUtils` access (for service-layer code)**

```java
@Service
public class CardService {
    public CardDetails getCard(String cardId) {
        IOLSchema context = WebUtils.getIOLSchema();
        // ...
    }
}
```

#### Pluggable Session Storage

The `ContextStore` interface enables persisting IOL context across requests:

```java
public interface ContextStore {
    <T> T get(String key, Class<T> contextClass);
    void set(String key, Object context);
    void remove(String key, Class<?> contextClass);
}
```

Key format: `{sessionKey}{className}` (e.g., `abc123IOLSchema`)

| Implementation | Module | Enable Annotation | Use Case |
|---------------|--------|-------------------|----------|
| **EHCacheContextStore** | context-store-ehcache | `@EnableEHCacheContextStore` | Single-instance, in-memory (deep-copy via serialization) |
| **MongoContextStore** | context-store-mongo | `@EnableMongoContextStore` | Distributed, TTL support, retry logic |
| **RDBContextStore** | context-store-rdb | `@EnableRDBContextStore` | RDBMS-backed (Oracle, H2) |

### 3.4 Process System

The Process System defines how user journeys are structured and how backend endpoints are exposed, validated, and routed.

**Modules:** `mca-libraries/process-lib` (loading), `mca-libraries/process` (REST endpoint), `mca-libraries/secure-proxy-core` (bootstrap orchestration)

#### process.json — Single Source of Truth

Each MCA journey is defined by a `process.json` file loaded from `classpath:processes/{processId}.json`:

```json
{
  "process": {
    "id": "cardControlDash_v1",
    "uiModuleName": "card_control_dashboard",
    "endpoints": {
      "getCardPolicy": {
        "uri": "/servicing/cardcontrol/policy",
        "method": "GET",
        "contexts": ["CustomerContext", "AccountContext"]
      }
    },
    "tasks": [
      {
        "id": "CARD_CONTROL_DASHBOARD",
        "name": "Card Control Dashboard",
        "view": { "src": "/dashboard" },
        "events": [
          {
            "name": "loadCards",
            "action": {
              "services": ["getCardPolicy"],
              "transition": { "task-id": "CARD_DETAIL" }
            }
          }
        ]
      }
    ],
    "apiDefinition": {
      "oas": {
        "path": "oas/openapi.yaml",
        "version": "1.0.0",
        "oasEnabled": "true"
      }
    }
  },
  "mandatoryContext": "CustomerContext,AccountContext"
}
```

**Key concepts:**
- **endpoints** — Map of named backend service endpoints with URI, method, and required contexts
- **tasks** — Ordered list of UI screens/steps with events that trigger service calls or transitions
- **apiDefinition** — OAS, RAML, or inline JSON schemas for request validation
- **mandatoryContext** — IOL context types required for this journey

#### Bootstrap Flow

When a client launches a journey:

```
1. Client → POST /launchProcess { "launchId": "cardControlDash_v1" }
2. BootstrapController → BootstrapService.createBootstrapContext()
3. Generate processId, clone IOL schema, validate, check entitlements
4. ProcessDiscovery resolves and fetches process.json
5. MCAV1ProcessDefinition transforms:
   - Parse endpoints
   - Generate obfuscated URIs: /mcaservice/{launchId}/{name}/{uuid}
   - Extract OAS spec
   - Remove apiDefinition from client-facing JSON
6. Store ContextData (endpoint map, IOL, OAS) in ContextStore keyed by processId
7. Return BootstrapContext to client (processId, tasks, obfuscated endpoints)
```

#### Process Chaining

Parent-child journey composition with shared IOL context:

```
Parent process (processId="proc-parent-123") running
  → Client calls POST /chainProcess with currentProcessId
  → BootstrapService loads parent ContextData
  → Resolves child launchId, creates child process with new processId
  → Child inherits parent's IOL context
  → On completion: GET /ProcessComplete?processId=proc-parent-123 resumes parent
```

#### Request Processor Architecture

The `Router` interface orchestrates request processing through four phases:

```java
public interface RequestProcessor extends Comparable<RequestProcessor> {
    String type();              // "PRE", "ROUTE", "POST", "ERROR"
    int order();                // Execution order within phase
    void run(RequestData data); // Processor logic
    boolean shouldExecute(RequestData data); // Conditional execution
}
```

`DefaultRouter` chains processors: **PRE** → **ROUTE** → **POST** (or **ERROR** on failure).

### 3.5 Response & Exception Handling

#### Response\<T\> Envelope

All MCA2 responses use a standardized envelope:

```java
public class Response<T> {
    public ResponseHttpStatus httpStatus;
    public T data;                          // Payload (mutually exclusive with errors)
    public List<Message> errors;            // Error messages
    public Map<String, String> headers;     // Custom response headers
}
```

**Message** carries structured error/info data:

```java
public class Message {
    private String id;          // UUID or correlation ID
    private String code;        // Machine-readable (e.g., "ACC_NOT_FOUND")
    private String title;       // Human-readable message
    private String detail;      // Additional context
    private String severity;    // INFO, WARN, ERROR
}
```

#### ResponseAssembler Fluent API

```java
// Success
Response.<CardPolicy>assemble()
    .build(ResponseHttpStatus.OK, cardPolicy);

// Error
Response.<CardPolicy>assemble()
    .addErrorMessage(Message.create("NOT_FOUND", "Card not found"))
    .build(ResponseHttpStatus.NOT_FOUND);
```

#### Exception Hierarchy

All MCA exceptions extend `GenericException` (which extends `RuntimeException`):

```
GenericException (abstract)
  ├── ApplicationException  → 500 Internal Server Error
  ├── ServerException       → 500/502 Server Error
  ├── RequestException      → 400 Bad Request
  ├── NotFoundException     → 404 Not Found
  └── AuthorizationException → 401/403 Unauthorized/Forbidden
```

Each exception carries a `List<Message>` and maps to a `ResponseHttpStatus` via `getStatus()`.

**ExceptionFilter** (order 1) catches all exceptions in the filter chain and converts them to `Response<T>` JSON envelopes. **ExceptionControllerAdvice** (`@RestControllerAdvice`) handles exceptions in Spring MVC controllers via `CoreExceptionHandler`.

#### HTTP Status Mapping

| Exception | HTTP Status | Use Case |
|-----------|-------------|----------|
| `ApplicationException` | 500 | Generic application errors |
| `ServerException` | 500/502 | Server-side failures |
| `RequestException` | 400 | Invalid client input |
| `NotFoundException` | 404 | Resource not found |
| `AuthorizationException` | 401/403 | Insufficient permissions |

---

## 4. Cross-Cutting Concerns

### 4.1 Logging

MCA2 uses **AspectJ compile-time weaving** for automatic logging — no explicit logging calls required in application code.

**Module:** `mca-libraries/logging-aspects`

**How it works:**
1. At build time, AspectJ weaves logging advice into bytecode around SLF4J calls
2. Method entry/exit, parameters, return values, and exceptions are logged automatically
3. Sensitive data is masked before logging via the masking framework

**Why compile-time weaving (not runtime):**
- Zero runtime reflection overhead
- Deterministic performance characteristics
- No AspectJ runtime framework loaded
- Cleaner stack traces for debugging

**Backend selection** (choose one):

| Module | Backend | Use Case |
|--------|---------|----------|
| `logging-config-log4j` | Log4j 2 | High-throughput production (async) |
| `logging-config-logback` | Logback | Spring Boot default |
| `logging-config-log4j-json` | Log4j 2 + JSON | Log aggregation (ELK, Splunk) |
| `logging-config-logback-json` | Logback + JSON | Log aggregation (ELK, Splunk) |

**Correlation ID propagation:** `CorrelationIdFilter` generates a UUID per request, stores it in `CorrelationIdContext` (ThreadLocal), and injects it into MDC. All log output includes the correlation ID for distributed tracing.

**Performance logging:** `@PerfLogRecordedOperation` and `@PerfLogParam` annotations (from `logging-performance`) automatically record method timing with trace context. Enabled via `logging.performance.enabled=true`.

### 4.2 Security

#### Authentication
- **JWT/OAuth2**: `OAuthValidatorFilter` validates tokens from `Authorization: Bearer` header (EPS chain)
- **SSO**: `BAMAuthFilterWrapper` integrates BEST Access Manager for colleague-facing apps (Secure Proxy chain)
- **mTLS**: `@EnableSpringBootSSL` provides X.509 certificate-based mutual TLS with CN whitelisting
- **Token management**: `JwtTokenService` in Secure Proxy for JWT creation and refresh

#### Authorization
- **RBAC**: `UserContext.role` provides role-based access control
- **Entitlements**: `EntitlementProvider` checks during process bootstrap
- **Per-request authorization**: `ContextAuthorizationPreProcessor` validates context access

#### Secrets Management
- **JCEKS keystores**: `JCEKeyStorePropertyPlaceholderProcessor` resolves `JCEKS::secret-name` placeholders
- **HashiCorp Vault**: `JbossVaultResolvablePlaceHolderProvider` for Vault-backed secrets
- **Spring properties**: Standard Spring property source resolution as fallback

### 4.3 Data Masking

**Module:** `mca-libraries/masking`

The `Mask<T>` functional interface provides composable data redaction:

```java
public interface Mask<T> {
    T apply(T input);
    default Mask<T> compose(Mask<T> before);
}
```

**Implementations:**
- `StringMasker` — Regex-based string masking (e.g., credit card: `4111****1111`)
- `JsonStringMasker` — Depth-first JSON tree traversal, masking leaf nodes by key or value pattern
- `HeaderMasker` — HTTP header redaction by key matching

**Predefined PCI-DSS masks** (from `MaskFactory.commonMasks()`):
- Credit card numbers → last 4 visible
- Social Security Numbers → last 4 visible
- Passwords → fully masked
- Card verification numbers → fully masked
- PINs → fully masked

**Redactor strategies** (from `Redactors` utility class):
- `LAST_FOUR_VISIBLE`, `FIRST_FOUR_VISIBLE`, `MASK_EVERYTHING`
- `TWO_STARS_FIRST`, `TWO_STARS_END`, `TWO_STARS_EITHER_SIDE`
- `CRLF_REPLACER` (injection prevention)

### 4.4 Property Resolution

**Modules:** `placeholder-resolvers`, `placeholder-converter`, `placeholder-vault-resolver`, `placeholder-starter`

Property values pass through a `PropertyPlaceholderProcessorChain` — each processor in the chain can transform or resolve the value:

```
Input value: "JCEKS::db-password"
  → JCEKeyStorePropertyPlaceholderProcessor (detects JCEKS:: prefix, resolves from keystore)
  → VaultPropertyPlaceholderProcessor (no match, passes through)
  → StandardPropertyProcessor (no match, passes through)
Output value: "actual-password-from-keystore"
```

The chain runs all processors sequentially (output of one becomes input to next), so a single value can contain multiple placeholder types.

**Configuration:** Auto-enabled via `placeholder-starter`; disable with `placeholder.resolver.enabled=false`.

### 4.5 OAS Validation

**Modules:** `oas-validation`, `filter-core` (`ValidationFilter`)

MCA2 validates HTTP requests against OpenAPI 3.0 specifications at two levels:

1. **EPS-level** (ValidationFilter, order 300): Validates all incoming requests against a global OAS spec
2. **Per-process** (ValidationRequestPreProcessor): Validates requests against the OAS spec embedded in `process.json`

**Modes:**
- **Blocking**: Returns 400 Bad Request on validation failure
- **Reporting**: Logs warnings, allows request through

**Configuration:**
```properties
core.default.oas.enabled=true
core.default.oas.path=classpath:openapi/api-spec.yaml
core.default.oas.blockingMode=true
core.default.validation-filter.exclude.paths=/actuator/**,/process/**
```

---

## 5. Design Patterns

### Chain of Responsibility

**Where:** Filter chains (EPS and Secure Proxy), `PropertyPlaceholderProcessorChain`, `RequestProcessor` pipeline, `ReferenceDataProcessorChain`

Ordered processing steps where each element can process, modify, or short-circuit the chain. Filters extend Spring's `OncePerRequestFilter` (guaranteeing single execution per request).

### Strategy

**Where:** Pluggable implementations selected via configuration or `@ConditionalOnProperty`

| Interface | Implementations | Selection |
|-----------|----------------|-----------|
| `ContextStore` | EHCache, Mongo, RDB | `@Enable*ContextStore` |
| `DdosPreventor` | `DefaultAllowAllRequestDdosPreventor`, `ChannelPropositionBasedDdosPreventor` | Property config |
| `Mask<T>` | `StringMasker`, `JsonStringMasker`, `HeaderMasker` | Factory/composition |
| `PropertyPlaceholderProcessor` | JCEKS, Vault, Standard | Chain configuration |
| `OasProvider` | `SimpleOasProvider`, `EmptyOasProvider` | Property config |
| `Redactor<I,O>` | Multiple predefined in `Redactors` | Factory selection |

### Enable Annotation

**Where:** Feature activation via `@Enable*` annotations that `@Import` Spring `@Configuration` classes

17 `@Enable*` annotations across the framework:

| Annotation | Module |
|-----------|--------|
| `@EnableExperienceAPI` | eps-core |
| `@EnableSecureProxy` | secure-proxy-core |
| `@EnableSecureProxyGateway` | secure-proxy-routing-gateway |
| `@EnableEHCacheContextStore` | context-store-ehcache |
| `@EnableMongoContextStore` | context-store-mongo |
| `@EnableRDBContextStore` | context-store-rdb |
| `@EnableReferenceData` | referencedata |
| `@EnableMCAI18N` | i18n |
| `@EnableBAMSSO` | sso-bam |
| `@EnableConsul` | consul-process-discovery |
| `@EnableBemServiceClient` | bem-client |
| `@EnableMisServiceClient` | mis-client |
| `@EnableSpringBootSSL` | spring-boot-ssl |
| `@EnableSpringServiceLocator` | service-locator |
| `@EnableRefreshEndPoint` | refresh-utils |
| `@EnableEndpointRestriction` | refresh-utils |
| `@EnableLegacyMCA` | legacy-common |

### Template Method

**Where:** `OncePerRequestFilter` defines the template (single-execution guard), subclasses implement `doFilterInternal()`.

### Factory

**Where:** `MaskFactory` creates predefined PCI-DSS mask sets; `TraceBeanFactory` creates performance trace beans; `RestClientFactory` creates configured REST clients.

### Layered Module (API / Core / Starter)

**Where:** `secure-proxy-api` / `secure-proxy-core`, `service-client` / `service-client-starter`, `placeholder-resolvers` / `placeholder-starter`

Separates contracts from implementations from auto-configuration, enabling partial adoption.

---

## 6. Technology Stack

| Category | Technology | Version |
|----------|-----------|---------|
| Language | Java | 21 LTS |
| Framework | Spring Boot | 3.5.10 |
| Cloud | Spring Cloud | 2025.0.1 |
| Servlet API | Jakarta EE | 10 |
| Build | Gradle | 8.5 (parallel builds) |
| AOP | AspectJ | 1.9.25.1 (compile-time weaving) |
| JSON | Jackson | 2.15+ |
| Logging | SLF4J | 2.x (facade) |
| HTTP Client | Apache HttpClient | 5 |
| Code Quality | Checkstyle | 9.3 (Sun conventions base) |
| Code Analysis | SonarQube | Zero blocker/critical/major |
| Security Scan | Veracode | Required for new code |
| Testing | JUnit 5 + Mockito + AssertJ | Current |
| HTTP Mocking | WireMock | Integration tests |
| Coverage | JaCoCo | 100% incremental required |

---

## 7. Module Catalog

### mca-libraries/ (47 modules)

#### Context & Infrastructure
| Module | Purpose |
|--------|---------|
| `context` | IOL data model — ~25 context POJOs (`IOLSchema`, `UserContext`, etc.) |
| `context-utils` | IOL context validation against JSON schema |
| `web-utils` | IOL header serialization/deserialization via `WebUtils` |
| `spring-context-utils` | Thread-local request context access for Spring |
| `filter-core` | Shared servlet filters (CorrelationId, Exception, Context, DDoS, Validation, etc.) |
| `common-utils` | Log injection prevention (CWE-117) and shared utilities |

#### Response & Exception Handling
| Module | Purpose |
|--------|---------|
| `response-handling-core` | `Response<T>` envelope, `ResponseAssembler`, `Message`, `ResponseHttpStatus` |
| `exception-handling-core` | `GenericException` hierarchy (Application, Request, NotFound, Authorization, Server) |
| `exception-handling-spring` | Spring MVC integration (`ExceptionControllerAdvice`, `CoreExceptionHandler`) |

#### Logging & Performance
| Module | Purpose |
|--------|---------|
| `logging-aspects` | AspectJ compile-time weaving on SLF4J calls |
| `logging-performance` | `@PerfLogRecordedOperation` / `@PerfLogParam` annotations |
| `logging-config-log4j` | Log4j 2 backend configuration |
| `logging-config-log4j-json` | Log4j 2 with JSON output |
| `logging-config-logback` | Logback backend configuration |
| `logging-config-logback-json` | Logback with JSON output |
| `logging-config-dynamic` | Dynamic log level support |
| `logging-config-test` | Test-specific logging config |
| `logging-spy` | Test utility for log output verification |
| `ecrime-logging` | eCrime compliance logging |
| `activity-logging` | Activity/audit trail logging |

#### Data Masking
| Module | Purpose |
|--------|---------|
| `masking` | `Mask<T>` interface, `StringMasker`, `JsonStringMasker`, `MaskFactory`, `Redactors` |

#### Routing & HTTP
| Module | Purpose |
|--------|---------|
| `router-api` | `Router`, `RequestProcessor`, `RequestData` abstractions |
| `router-http` | Apache HttpClient 5 routing implementation, `RouterServlet` |

#### Secure Proxy & Gateway
| Module | Purpose |
|--------|---------|
| `secure-proxy-api` | `ContextStore`, `ProcessDiscovery`, `TokenService` interfaces |
| `secure-proxy-core` | Full Secure Proxy implementation (80+ source files) |
| `secure-proxy-routing-gateway` | Pattern-based HTTP routing gateway |

#### Session Storage
| Module | Purpose |
|--------|---------|
| `context-store-ehcache` | EHCache in-memory `ContextStore` with deep-copy |
| `context-store-mongo` | MongoDB `ContextStore` with TTL, retry, query timeout |
| `context-store-rdb` | JPA/Hibernate `ContextStore` (Oracle, H2) |

#### Experience API
| Module | Purpose |
|--------|---------|
| `eps-core` | `@EnableExperienceAPI`, filter config, `@IOLContext` resolver |

#### Process Management
| Module | Purpose |
|--------|---------|
| `process` | REST endpoint exposing process.json (`/process/{id}`) |
| `process-lib` | Classpath process.json loading, OAS/RAML enrichment |
| `consul-process-discovery` | Consul KV-backed process and service discovery |
| `remote-discovery` | Remote service discovery abstractions |

#### Property Resolution
| Module | Purpose |
|--------|---------|
| `placeholder-resolvers` | `PropertyPlaceholderProcessor` interface and chain; JCEKS resolver |
| `placeholder-converter` | `ResolvablePropertyConverter` for `@ConfigurationProperties` binding |
| `placeholder-vault-resolver` | HashiCorp Vault placeholder resolution |
| `placeholder-starter` | Spring Boot auto-configuration for placeholder pipeline |

#### Validation & Schema
| Module | Purpose |
|--------|---------|
| `schema-validation` | JSON schema validation infrastructure |
| `oas-validation` | OpenAPI specification validation, `OasProvider` interface |

#### Service Clients
| Module | Purpose |
|--------|---------|
| `service-client` | Generic REST client with correlation ID and perf logging |
| `service-client-starter` | Spring Boot auto-configuration for REST clients |

#### Security & Auth
| Module | Purpose |
|--------|---------|
| `oauth-validator-core` | OAuth token validation |
| `sso` | General SSO framework |
| `sso-bam` | BAM (BEST Access Manager) SSO integration |
| `entitlement` | Entitlement/authorization framework |

#### Data & Content
| Module | Purpose |
|--------|---------|
| `referencedata` | CSV-based reference data loading (`@EnableReferenceData`) |
| `i18n` | Internationalization from IOL locale context (`@EnableMCAI18N`) |
| `cms` | Content management integration |
| `external-resources` | External static resource resolution |
| `bcag` | BCAG cryptographic signing |
| `tiaaas-client` | TiaaS client integration |

### mca-extension-libraries/ (8 modules)

| Module | Purpose | Enable |
|--------|---------|--------|
| `bem-client` | Barclays Event Management notification client | `@EnableBemServiceClient` |
| `mis-client` | MIS backend client (JMS/SOAP via IBM MQ) | `@EnableMisServiceClient` |
| `jceks-spring-properties-processor` | JCEKS/PKCS12 keystore to Spring env; `mcaHealth` endpoint | Auto-registered |
| `service-locator` | Runtime service discovery (Spring, LDAP, reflective) | `@EnableSpringServiceLocator` |
| `spring-boot-ssl` | X.509 mTLS with CN whitelisting | `@EnableSpringBootSSL` |
| `refresh-utils` | Secure property refresh, request restriction | `@EnableRefreshEndPoint` |
| `legacy-common` | MCA1 backward compatibility (70+ source files) | `@EnableLegacyMCA` |
| `test-common` | JUnit 5 extension for mocked ApplicationContext | `@RegisterExtension` |

### mca-examples/ (4 reference apps)

| Application | Purpose |
|-------------|---------|
| `experience-api-cardcontrol-reference-app` | Card control EPS reference app |
| `secure-proxy-reference-app` | Secure Proxy reference app |
| `host-reference-app` | Static UI asset packaging (tar) |
| `config-server-app` | Spring Cloud Config Server |

### mca-java-common-bom/

Bill of Materials providing centralized dependency version management. Inherits from Spring Boot BOM (`3.5.10`).

**Usage:**
```gradle
implementation platform("com.barclays.global.mca:mca-dependencies:${version}")
```

---

## 8. Getting Started

### Minimum EPS Application

**build.gradle:**
```gradle
plugins {
    id 'org.springframework.boot' version '3.5.10'
}

dependencies {
    implementation platform("com.barclays.global.mca:mca-dependencies:${mcaVersion}")

    implementation 'com.barclays.global.mca:mca-eps-core'
    implementation 'com.barclays.global.mca:mca-context'
    implementation 'com.barclays.global.mca:mca-filter-core'
    implementation 'com.barclays.global.mca:mca-response-handling-core'
    implementation 'com.barclays.global.mca:mca-exception-handling-core'

    // Logging backend (choose one)
    runtimeOnly 'com.barclays.global.mca:mca-logging-config-logback'
}
```

**Application class:**
```java
@SpringBootApplication
@EnableExperienceAPI
public class MyApplication {
    public static void main(String[] args) {
        SpringApplication.run(MyApplication.class, args);
    }
}
```

**Controller:**
```java
@RestController
@RequestMapping("/api/v1/customers")
public class CustomerController {

    private final CustomerService customerService;

    public CustomerController(CustomerService customerService) {
        this.customerService = customerService;
    }

    @GetMapping("/{customerId}")
    public Response<Customer> getCustomer(
            @IOLContext IOLSchema context,
            @PathVariable String customerId) {

        Customer customer = customerService.findById(customerId);
        return Response.<Customer>assemble()
            .build(ResponseHttpStatus.OK, customer);
    }
}
```

### Key Configuration Properties

```properties
# Core EPS
mca.eps.enabled=true

# Correlation ID
core.default.log-request-duration.enabled=true
core.default.log-request-duration.application-type=EPS

# Context validation
eps.iolschema.validation.enabled=true
eps.context.filter.exclude.paths=/actuator/**,/static/**

# OAuth (optional)
core.default.oauth-filter.enabled=false
core.default.oauth-filter.exclude.paths=/actuator/**

# DDoS (optional)
eps.ddos.filter.enabled=false

# OAS validation (optional)
core.default.oas.enabled=false
core.default.oas.path=classpath:openapi/api-spec.yaml
core.default.oas.blockingMode=true

# Performance logging
logging.performance.enabled=true

# Logging
logging.level.root=INFO
logging.level.com.barclays.global.mca=DEBUG
```

### Build Commands

```bash
# Full build with tests
./gradlew build

# Build without tests
./gradlew build -x test -x integrationTest

# Build a specific module
./gradlew :mca-libraries:mca-context:build

# Run all unit tests
./gradlew test

# Run a single test class
./gradlew :mca-libraries:mca-context:test --tests com.barclays.global.mca.context.SomeTest

# Run integration tests
./gradlew :mca-examples:mca-experience-api-cardcontrol-reference-app:integrationTest

# Run checkstyle
./gradlew allCheckstyle
```

---

## Appendix A: Cross-Validation Log

This appendix documents the findings from cross-validating two independent documentation sources against the actual `mca-java-common` source code.

### Sources Compared

1. **MCA2-EPS-Guide** — 43 files of code-harvested documentation from codebase analysis
2. **Confluence-derived framework docs** — 87+ files covering deployment and operational concerns

### Key Discrepancies and Resolutions

| # | Topic | EPS-Guide Claim | Confluence Claim | Code Verification | Resolution |
|---|-------|-----------------|------------------|-------------------|------------|
| 1 | **Architecture model** | 5-layer internal module model | 4-tier deployment model | Both perspectives exist | **Both valid** — different lenses (internal vs deployment) |
| 2 | **EPS filter count** | "13 core filters" | 10 EPS filters | Code has **10 registered filters** in EPS FilterConfig | **Confluence correct** — EPS has 10, not 13 |
| 3 | **DdosFilter order** | "5+" in table, "150" in diagram | 150 in EPS chain | Code: `order = 150` in FilterConfig | **Confluence correct** — Order 150; EPS-Guide self-contradictory |
| 4 | **ContextFilter** | Omitted from filter list | Listed at Order 100 | Code: registered at order 100 in FilterConfig | **Confluence correct** — exists in code |
| 5 | **MlsFilter** | Not mentioned | Listed at Order 4 | No `MlsFilter` class exists. MLS headers validated via configuration properties | **Neither fully correct** — MLS is config-based, not a separate filter |
| 6 | **ProcessContext** | Rich object with processId/status/steps | Not detailed | Code: simple `{key, value}` pair with regex validation | **EPS-Guide error** — actual code is a flat key-value pair |
| 7 | **Context class generation** | Implies hand-written | Auto-generated from IOL_schema.json | `IOL_schema.json` exists in resources; classes use `@JsonProperty` annotations | **Confluence correct** — schema-driven generation |
| 8 | **URI obfuscation term** | "URL obfuscation" | "Process encryption" (legacy) | Code: `DeobfuscateUriPreProcessor` | **EPS-Guide preferred** — matches code naming |
| 9 | **Request processors** | 5 MCA2-specific | 20+ pre, 5 route, 11 post | Code: PRE/ROUTE/POST/ERROR phases with multiple implementations | **Both useful** — different scope/detail level |
| 10 | **GenericException type** | Extends `Exception` | Not detailed | Code: extends `RuntimeException` | **EPS-Guide error** — it's `RuntimeException`, not checked `Exception` |
| 11 | **ApplicationException HTTP status** | 200 OK (business error) | Not detailed | Code: maps to `INTERNAL_SERVER_ERROR` (500) | **EPS-Guide error** — actual mapping is 500, not 200 |
| 12 | **@IOLContext annotation** | Custom annotation for injection | Not mentioned | Code: exists in eps-core as parameter annotation | **EPS-Guide correct** — annotation exists |
| 13 | **Secure Proxy filters** | Not covered in detail | 18 security/session filters | Code: 11 filters in Secure Proxy FilterConfig | **Neither precise** — actual count is 11 (10 core + 1 optional BAM) |

### Errors Corrected from EPS-Guide

1. `ProcessContext` is NOT a rich domain object — it's a flat `{key, value}` pair
2. EPS filter count is 10, not 13
3. DdosFilter order is 150, not "5+"
4. ContextFilter was missing from filter documentation
5. `GenericException` extends `RuntimeException`, not `Exception`
6. `ApplicationException` maps to 500 (INTERNAL_SERVER_ERROR), not 200 (OK)
7. Several code examples appear to be fabricated (e.g., `IOLContextValidator` implementation details don't match actual code)

### Errors Corrected from Confluence Docs

1. No `MlsFilter` class exists — MLS is handled through configuration properties, not a dedicated filter
2. Secure Proxy filter count is 11, not 18
3. "Process encryption" terminology doesn't match code; `DeobfuscateUriPreProcessor` uses "URI obfuscation"

### Coverage Gaps Filled

**From EPS-Guide (not in Confluence):**
- Detailed filter implementation code and ordering
- `ResponseAssembler` fluent API details
- `@IOLContext` injection mechanism
- `process.json` schema reference
- Property resolution chain internals
- Data masking (`Mask<T>` interface and implementations)
- Performance monitoring annotations

**From Confluence (not in EPS-Guide):**
- 4-tier deployment topology (FullServe vs Digital)
- Secure Proxy as gateway tier
- Session management architecture
- Security overview (IAM, SSO, mTLS)
- Operational concerns (monitoring, scaling)

---

*This guide was generated by cross-validating two independent documentation sources against the `mca-java-common` source code on branch `release/2.3`.*
