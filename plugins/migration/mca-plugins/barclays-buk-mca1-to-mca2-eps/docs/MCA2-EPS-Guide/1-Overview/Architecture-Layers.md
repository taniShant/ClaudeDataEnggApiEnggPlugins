# MCA2 Architecture Layers: How EPS Fits the Platform

## Executive Summary

The MCA2 platform implements a **5-layer architecture** where the EPS (Enterprise Presentation Services) framework occupies the central **Service Layer** and **Config Layer**, providing the foundation for distributed context propagation, request processing, and response standardization across all microservices.

This document explains each layer and where EPS components reside.

---

## The 5-Layer Architecture

```
┌──────────────────────────────────────────────────────────────┐
│ Layer 5: APPLICATION LAYER                                   │
│ ├─ Consuming applications (card-control-ref-app, etc.)      │
│ ├─ Business logic (controllers, services, repositories)     │
│ ├─ Application-specific configuration                       │
│ └─ Uses: All lower layers                                   │
└──────────────────────────────────────────────────────────────┘
                           ▲
                           │
┌──────────────────────────┼──────────────────────────────────┐
│ Layer 4: INTEGRATION LAYER                                   │
│ ├─ Specialized frameworks (Router, SecureProxy)             │
│ ├─ External integrations (BEM, MIS clients)                 │
│ ├─ Service location & discovery                             │
│ ├─ Advanced property resolution (Vault)                     │
│ └─ Uses: Layer 3 + common utilities                         │
└──────────────────────────┼──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│ Layer 3: CONFIGURATION LAYER                                 │
│                                                              │
│ Spring Boot Auto-Configuration & Initialization:            │
│                                                              │
│ ┌─ EPS Auto-Configuration ─────────────────────────────┐   │
│ │ • ExperienceAPIConfig (mca-eps-core)                │   │
│ │ • CoreFilterConfig (filter registration)            │   │
│ │ • IOLContextHandlerMethodArgumentResolver          │   │
│ │ • SchemaController                                  │   │
│ └────────────────────────────────────────────────────┘   │
│                                                              │
│ ┌─ Feature Enablement ──────────────────────────────────┐   │
│ │ • @EnableExperienceAPI                              │   │
│ │ • @EnableSecureProxy, @EnableRouter                 │   │
│ │ • @EnableMasking                                    │   │
│ │ • @ConditionalOnProperty for feature toggles        │   │
│ └────────────────────────────────────────────────────┘   │
│                                                              │
│ ┌─ Service Configuration ───────────────────────────────┐   │
│ │ • mca-service-client-starter                         │   │
│ │ • mca-placeholder-starter                            │   │
│ │ • Logging configuration (Log4j / Logback)           │   │
│ └────────────────────────────────────────────────────┘   │
│                                                              │
│ Uses: Layer 2 frameworks                                    │
└──────────────────────────┼──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│ Layer 2: SERVICE LAYER (Core EPS Frameworks)                │
│                                                              │
│ ┌─ Context System ──────────────────────────────────────┐   │
│ │ • IOLSchema (25+ context classes)                   │   │
│ │ • Context propagation via HTTP headers              │   │
│ │ • Context serialization/validation (mca-context)    │   │
│ └────────────────────────────────────────────────────┘   │
│                                                              │
│ ┌─ Request Processing (Filter Chain) ──────────────────┐   │
│ │ • CorrelationIdFilter (request tracing)             │   │
│ │ • ExceptionFilter (global error handling)           │   │
│ │ • DisableSessionFilter, MultiReadRequestFilter      │   │
│ │ • OAuthValidator, DdosFilter, etc. (13 total)       │   │
│ │ • Chain of Responsibility pattern                   │   │
│ └────────────────────────────────────────────────────┘   │
│                                                              │
│ ┌─ Response & Exception Handling ───────────────────────┐   │
│ │ • Exception hierarchy (GenericException →...)        │   │
│ │ • HTTP status mapping                               │   │
│ │ • Response<T> envelope                              │   │
│ │ • ResponseAssembler fluent API                      │   │
│ └────────────────────────────────────────────────────┘   │
│                                                              │
│ ┌─ Logging & Cross-Cutting Concerns ────────────────────┐   │
│ │ • AspectJ compile-time weaving (mca-logging-aspects)│   │
│ │ • SLF4J integration                                  │   │
│ │ • Data masking/redaction                            │   │
│ │ • Performance monitoring                            │   │
│ └────────────────────────────────────────────────────┘   │
│                                                              │
│ Uses: Layer 1 utilities                                    │
└──────────────────────────┼──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│ Layer 1: FOUNDATION LAYER (Utilities & Utilities)           │
│                                                              │
│ ┌─ Common Utilities ────────────────────────────────────┐   │
│ │ • mca-common-utils (general utilities)              │   │
│ │ • mca-web-utils (servlet/request utilities)         │   │
│ │ • Date/time helpers, string utilities                │   │
│ └────────────────────────────────────────────────────┘   │
│                                                              │
│ ┌─ Validation ──────────────────────────────────────────┐   │
│ │ • mca-schema-validation (JSON schema)                │   │
│ │ • mca-oas-validation (OpenAPI schema)                │   │
│ │ • Jakarta Validation support                        │   │
│ └────────────────────────────────────────────────────┘   │
│                                                              │
│ ┌─ External Dependencies ───────────────────────────────┐   │
│ │ • Java 21 standard library                           │   │
│ │ • Spring Boot 3.5.10 core                            │   │
│ │ • Jakarta EE 10                                      │   │
│ │ • AspectJ 1.9.25.1                                   │   │
│ └────────────────────────────────────────────────────┘   │
│                                                              │
│ Uses: None - Foundation level                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Foundation Layer

**Purpose:** Provide essential utilities and external frameworks that all higher layers depend on.

**Components:**

### Common Utilities (mca-common-utils)
- General utility functions (string manipulation, collections, etc.)
- Date/time helpers
- Encoding/decoding utilities
- No business logic

### Web Utilities (mca-web-utils)
- Servlet/request utilities
- `WebUtils.setIOLSchemaInScope()` — Stores IOLSchema in request scope
- `WebUtils.getIOLSchema()` — Retrieves IOLSchema from request scope
- Response writers, content negotiation helpers

### Schema Validation (mca-schema-validation)
- JSON schema validation engine
- Schema loading and caching
- Validation error reporting

### External Frameworks
- Java 21 standard library
- Spring Boot 3.5.10
- Jakarta EE 10
- AspectJ 1.9.25.1

**Key Principle:** Foundation layers have **NO dependencies on higher layers**. This ensures stability and prevents circular dependencies.

---

## Layer 2: Service Layer (Core EPS Frameworks)

**Purpose:** Implement core EPS functionality that all applications use.

**This is where EPS lives.** The Service Layer provides the fundamental framework components:

### Context System (mca-context + mca-context-utils)

**Responsibility:** Represent and propagate distributed request context across services.

**Components:**
```
mca-context/
├── data/
│   ├── IOLSchema (root context container)
│   ├── UserContext (user identity)
│   ├── CustomerContext (customer info)
│   ├── AccountContext (account details)
│   ├── ProcessContext (workflow state)
│   ├── DeviceContext (client fingerprint)
│   ├── CaseContext (case tracking)
│   ├── Channel (communication channel)
│   ├── Identifier (ID types)
│   ├── TokenIdentifier (token info)
│   └── [13+ total context types]
└── utils/
    └── Serialization/deserialization utilities
```

**Flow:**
```
HTTP Request
  ↓
HTTP Headers (X-UserContext, X-CustomerContext, ...)
  ↓
ContextFilter (mca-filter-core)
  ↓
IOLSchema (deserialized from headers)
  ↓
WebUtils.setIOLSchemaInScope(iolSchema)
  ↓
Request-scoped attribute (accessible throughout request lifecycle)
```

### Request Processing: Filter Chain (mca-filter-core)

**Responsibility:** Execute ordered filters for systematic request processing using Chain of Responsibility pattern.

**13 Core Filters:**

| Filter | Order | Purpose |
|--------|-------|---------|
| CorrelationIdFilter | 0 | Generate request IDs, add to thread context |
| ExceptionFilter | 1 | Wrap request processing, handle exceptions |
| DisableSessionFilter | 2 | Prevent unwanted session creation |
| MultiReadRequestFilter | 3 | Enable request body re-reading |
| OAuthValidatorFilter | 4+ | Validate JWT tokens (if enabled) |
| DdosFilter | 5+ | DDoS prevention (if enabled) |
| ValidationFilter | 300 | Input validation (if enabled) |
| RequestWhiteListingFilter | 7+ | Endpoint whitelist (if enabled) |
| DynamicLoggingFilter | 8+ | Dynamic log level (if enabled) |
| PerfLogExclusionFilter | 9+ | Performance logging exclusions |
| [Custom app filters] | 10+ | Application-specific filters |

**Execution Model:**
```
Request → CoreFilterConfig registers all filters
            ↓
        CorrelationIdFilter (Order 0)
            ↓
        ExceptionFilter (Order 1)
            ↓
        [Other ordered filters]
            ↓
        DispatcherServlet → Controller/Handler
            ↓
        Response → ExceptionFilter (wraps, catches exceptions)
            ↓
        HTTP Response
```

**Extension Points:**
- Custom filters registered via FilterRegistrationBean
- Conditional enablement via @ConditionalOnProperty
- Reusable MCAOncePerRequestFilter base class

### Response & Exception Handling

**Response Envelope (mca-response-handling-core):**

```java
@Data
public class Response<T> {
    private T data;                      // Successful data
    private List<Message> messages;      // Status/error messages
    private String status;               // SUCCESS, ERROR, WARNING
    private String statusCode;           // HTTP status
    @JsonInclude(Include.NON_NULL)
    private Map<String, Object> metadata;
}
```

**ResponseAssembler Pattern:**
```java
// Success
Response.<CardPolicy>assemble()
    .build(cardPolicy)
    .withStatusCode(200)

// Error
Response.<CardPolicy>assemble()
    .error(List.of(message1, message2))
    .withStatusCode(400)
```

**Exception Hierarchy:**
```
GenericException (abstract)
├── ApplicationException (business error)
├── ServerException (500 errors)
├── RequestException (4xx errors)
├── NotFoundException (404)
└── AuthorizationException (403)
```

### Logging & Cross-Cutting Concerns

**AspectJ Compile-Time Weaving (mca-logging-aspects):**

Intercepts all SLF4J logging calls at compile time to:
- Add masking/redaction (credit cards, email, CRLF injection)
- Integrate with performance monitoring
- Add correlation IDs to logs
- Support multiple backends (Log4j, Logback)

**Data Masking (mca-masking):**
```
Credit Card:   4111-1111-1111-1111  →  4111-****-****-1111
Email:         user@example.com      →  user@***
Phone:         555-123-4567          →  555-***-4567
```

---

## Layer 3: Configuration Layer

**Purpose:** Provide Spring Boot auto-configuration and feature enablement mechanisms.

**Components:**

### EPS Auto-Configuration (mca-eps-core)

**Master configuration class:** `ExperienceAPIConfig`

```java
@Configuration
@EnableWebMvc
public class ExperienceAPIConfig {
    // Auto-configures:
    // 1. Filter registration via CoreFilterConfig
    // 2. IOLContextHandlerMethodArgumentResolver for @IOLContext
    // 3. Response interceptors (ApiResponseInterceptor)
    // 4. Schema endpoints
}
```

**What it registers:**
1. All 13 core filters with correct ordering
2. Custom argument resolvers for @IOLContext annotation
3. Response interceptors
4. Schema introspection endpoints

**Trigger:** `@EnableExperienceAPI` annotation

```java
@SpringBootApplication
@EnableExperienceAPI  // Imports ExperienceAPIConfig
public class CardControlApplication {
    public static void main(String[] args) {
        SpringApplication.run(CardControlApplication.class, args);
    }
}
```

### Feature Enablement (@Enable* Annotations)

**Pattern:** Each major framework feature has an @Enable* annotation:

```java
@EnableExperienceAPI          // Core EPS
@EnableSecureProxy           // Optional secure proxy
@EnableRouter                // Optional routing
@EnableMasking               // Data redaction
@EnableMisServiceClient      // MIS integration (optional)
@EnableReferenceData         // Reference data (optional)
@EnableSpringServiceLocator  // Service locator (optional)
public class Application {
    // ...
}
```

### Conditional Configuration (@ConditionalOn*)

Spring Conditionals enable feature toggles:

```java
// Feature toggling via property
@Configuration
@ConditionalOnProperty(name = "masking.enabled", havingValue = "true")
public class MaskingConfig { ... }

@Configuration
@ConditionalOnProperty(name = "ddos.prevention.enabled", havingValue = "true")
public class DdosFilterConfig { ... }

// Optional bean overrides
@Bean
@ConditionalOnMissingBean(DdosPreventor.class)
public DdosPreventor defaultDdosPreventor() { ... }

// Classpath detection
@Configuration
@ConditionalOnClass(name = "org.springframework.security.oauth2.jwt.JwtDecoder")
public class OAuthValidatorAutoConfiguration { ... }
```

### Service Configuration

**Starter modules provide Spring Boot auto-configuration:**

- **mca-service-client-starter** — REST client configuration
  - Registers RestTemplate bean
  - Configures RestTemplateFactory
  - Provides converters for context propagation

- **mca-placeholder-starter** — Property resolution
  - Registers PropertyPlaceholderProcessorChain
  - Enables custom property sources (Vault, JCEKS)
  - Property conversion and validation

### Logging Configuration Selection

Applications select logging backend:

```properties
# application.properties
logging.config=classpath:log4j2.xml           # Use Log4j 2
# OR
# classpath:logback.xml (automatic Spring Boot default)
```

```gradle
// build.gradle - Choose ONE
runtimeOnly 'com.barclays.global.mca:mca-logging-config-log4j'
// OR
runtimeOnly 'com.barclays.global.mca:mca-logging-config-logback'
```

---

## Layer 4: Integration Layer

**Purpose:** Provide specialized frameworks and external integrations.

**Components:**

### Advanced Frameworks

**Router Framework (mca-router-http):**
- Dynamic request routing
- Circuit breaking
- Service discovery integration
- Optional, for advanced routing scenarios

**Secure Proxy (mca-secure-proxy-core):**
- Request transformation
- Protocol adaptation
- Security headers injection
- Optional, for API gateway deployments

### External System Integrations

**Business Entity Management (bem-client):**
- Integrates with BEM service
- Optional, for specific legacy integrations

**Management Information System (mis-client):**
- Integrates with MIS service
- Optional, for specific legacy integrations

**Other Integrations:**
- BCAG encryption
- TIAA service
- Content Management Service (CMS)
- etc.

### Advanced Property Resolution

**HashiCorp Vault (mca-placeholder-vault-resolver):**
- Secrets management
- Dynamic property resolution
- Optional, for Vault-based deployments

**JCEKS Keystore (jceks-spring-properties-processor):**
- Encrypted property files
- Optional, for secure property storage

### Service Discovery

**Consul (mca-consul-process-discovery):**
- Service registration/discovery
- Optional, for Consul-based deployments

---

## Layer 5: Application Layer

**Purpose:** Implement business logic specific to the application.

**Components:**

### Consuming Applications

**Example: experience-api-cardcontrol-reference-app**

```java
@SpringBootApplication
@EnableExperienceAPI                    // Layer 3: Enable EPS
@EnableMisServiceClient                 // Layer 4: Enable MIS integration
@EnableReferenceData                    // Layer 4: Enable reference data
public class CardControlApplication {
    public static void main(String[] args) {
        SpringApplication.run(CardControlApplication.class, args);
    }
}

@RestController
@RequestMapping("/api/card-control")
public class CardControlController {

    @PostMapping("/lock")
    public Response<LockResult> lockCard(
        @IOLContext IOLSchema context,   // Layer 2: Context injection
        @RequestBody LockRequest request
    ) {
        // Business logic
        CardPolicy policy = cardControlService.lockCard(
            context.getCustomerContext(),
            request
        );

        // Layer 2: Response assembly
        return Response.assemble()
            .build(policy)
            .withStatusCode(200);
    }
}
```

**Responsibilities:**
- Business logic (CardControlService, etc.)
- REST endpoints (controllers)
- Data persistence (repositories)
- Application-specific configuration
- Integration with Layer 4 services as needed

**Uses all layers:**
- Layer 1: Utilities
- Layer 2: EPS frameworks (Context, Filters, Response)
- Layer 3: Auto-configuration, feature enablement
- Layer 4: Optional integrations (MIS client, Reference data, etc.)

---

## Request Lifecycle: How Layers Interact

**Complete request flow through all layers:**

```
1. HTTP Request arrives
   │
   └─→ Layer 1: Web utilities receive request

2. Filter Chain (Layer 2) processes request
   │
   ├─→ CorrelationIdFilter: Generate request ID
   ├─→ ContextFilter: Extract IOL from headers
   │   └─→ Layer 1: WebUtils.setIOLSchemaInScope()
   ├─→ ExceptionFilter: Wrap remainder of chain
   ├─→ Other filters: Auth, validation, etc.
   │
   └─→ Request forwarded to DispatcherServlet

3. DispatcherServlet routes to controller
   │
   └─→ Layer 5: Application controller

4. Layer 3: Argument resolver processes @IOLContext
   │
   ├─→ Layer 1: WebUtils.getIOLSchema() retrieves context
   └─→ Injects IOLSchema into controller method parameter

5. Layer 5: Business logic executes
   │
   ├─→ Access context via @IOLContext parameter
   ├─→ Call Layer 4 services (MIS client, etc.) as needed
   ├─→ Layer 2: Call business services
   └─→ Execute database operations

6. Response building (Layer 2)
   │
   └─→ ResponseAssembler builds Response<T> envelope

7. Layer 3: Response interceptor processes response
   │
   └─→ Serialize to JSON

8. Layer 2: ExceptionFilter handles any exceptions
   │
   └─→ Convert to error Response<T>

9. HTTP Response returned to client
   │
   ├─→ Layer 1: Web utilities write response
   └─→ JSON with status codes, messages, data
```

---

## Layering Patterns: Best Practices

### ✅ Good: Proper Layering

```
Application (Layer 5)
    ↓
EPS Frameworks (Layer 2)
    ↓
Foundation (Layer 1)
```

Direct dependencies only:
- Layer 5 imports from Layers 4, 3, 2, 1
- Layer 4 imports from Layers 3, 2, 1
- Layer 3 imports from Layer 2, 1
- Layer 2 imports from Layer 1
- Layer 1 imports only external libraries

### ✅ Good: Using @Enable* Annotations

```java
@SpringBootApplication
@EnableExperienceAPI                    // Explicitly enable features
@EnableMasking
public class Application { }
```

Benefits:
- Clear feature activation
- Conditional auto-configuration
- Easy feature toggling
- Testability

### ❌ Bad: Circular Dependencies

```
Layer 3
  ↑ imports ↓
Layer 2
  ↑ imports ↓
Layer 1  ← VIOLATES LAYERING
```

Risks:
- Difficult to understand dependency chain
- Hard to test in isolation
- Fragile to changes
- Complex version management

### ❌ Bad: Skipping Layers

```
Application directly imports Foundation
↓ (skips EPS frameworks)
Misses logging, context, exception handling
```

Risks:
- Inconsistent error handling
- Missing observability
- Incompatible with framework patterns
- Technical debt

---

## Module Dependencies per Layer

### Layer 1: Foundation
```
mca-common-utils
mca-web-utils
mca-schema-validation
mca-oas-validation
(external: Java 21, Spring Boot, Jakarta EE, AspectJ)
```

### Layer 2: Service (Core EPS)
```
mca-context
mca-context-utils
mca-spring-context-utils
mca-filter-core
mca-eps-core
mca-exception-handling-core
mca-response-handling-core
mca-logging-aspects
mca-logging-config-log4j / mca-logging-config-logback
mca-masking
```

### Layer 3: Configuration
```
(Spring Boot auto-configs)
mca-service-client-starter
mca-placeholder-starter
(Spring boot starter dependencies)
```

### Layer 4: Integration
```
mca-router-http (optional)
mca-secure-proxy-core (optional)
bem-client (optional)
mis-client (optional)
mca-placeholder-vault-resolver (optional)
jceks-spring-properties-processor (optional)
mca-consul-process-discovery (optional)
(other external integrations)
```

### Layer 5: Application
```
(Depends on all lower layers based on requirements)
```

---

## Dependency Isolation: Avoiding Coupling

### Principle: Depend Downward, Not Upward

**Correct:**
```
Application → Layer 3 config → Layer 2 services → Layer 1 utils
(downward dependencies only)
```

**Incorrect:**
```
Layer 1 imports Layer 2 (or higher) ← WRONG
Layer 2 imports Layer 4 ← WRONG
```

### Module Packaging: Clear Boundaries

Each module has clear responsibility:

**mca-context (Layer 2):**
```
com.barclays.global.mca.libs.context
├── data/           ← Data model (IOLSchema)
└── utils/          ← Utilities (imports nothing from eps-core)
```

**mca-eps-core (Layer 3 configuration):**
```
com.barclays.global.mca.libs.eps
├── config/         ← Auto-configuration
├── annotations/    ← @EnableExperienceAPI, @IOLContext
└── interceptors/   ← Response interception
```

**mca-filter-core (Layer 2):**
```
com.barclays.global.mca.libs.filters
├── base/          ← MCAOncePerRequestFilter base class
├── [individual filter implementations]
└── providers/     ← Strategy implementations (DdosPreventor, etc.)
```

---

## Configuration by Layer

### Layer 1: No Configuration
- Framework defaults only
- No application settings

### Layer 2: Framework Defaults
- Filter ordering constants
- Exception-to-status mappings
- Default context validation rules

### Layer 3: Feature Enablement
- @EnableExperienceAPI
- @EnableMasking, @EnableSecureProxy
- logging.config backend selection

### Layer 4: Integration Configuration
- OAuth token validation URLs
- External service endpoints
- Secret vault URLs
- Service discovery registries

### Layer 5: Application Configuration
- Business logic settings
- Application-specific endpoints
- Custom masking patterns
- Performance tuning parameters

---

## Scaling Architecture Across Organization

**Small Team (1-5 developers):**
- Use Layers 1-3 only (EPS core)
- Optional: Some Layer 4 as needed

**Medium Team (5-20 developers):**
- All Layers 1-4
- Shared frameworks (Router, Proxy)
- Multiple applications (Layer 5)

**Large Organization (20+ developers):**
- Full 5-layer architecture
- Custom Layer 4 modules
- Shared Layer 2 extensions
- Multiple applications with specialized features

---

## Next Steps

1. **Understand Your Layer:** Identify which layer your code belongs in
2. **Review Layer 2 Components:** Study EPS frameworks (Context System, Filter Chain)
3. **Study Auto-Configuration:** Learn @Enable* patterns in Layer 3
4. **Check Dependencies:** Verify your module follows correct dependency direction
5. **Reference Applications:** Study how example apps use all layers

---

## Quick Reference: Architecture Summary

| Layer | Purpose | Key Modules | Status |
|-------|---------|-----------|--------|
| **5** | Business logic | Your app controllers/services | ✅ Custom |
| **4** | Integrations | Router, SecureProxy, MIS, Vault | ⚠️ Optional |
| **3** | Configuration | ExperienceAPIConfig, @Enable* | ✅ Required |
| **2** | EPS Services | Context, Filter, Response, Logging | ✅ Required |
| **1** | Utilities | Common utils, Web utils | ✅ Required |

**Every application requires Layers 1-3 and Layer 5.**
**Layers 4 are optional based on requirements.**

---

## Architecture Validation Checklist

- [ ] Layer 1 modules have no dependencies on Layers 2-5
- [ ] Layer 2 modules depend only on Layer 1
- [ ] Layer 3 auto-configs depend only on Layers 1-2
- [ ] Layer 4 modules depend only on Layers 1-3
- [ ] Layer 5 application imports @EnableExperienceAPI from Layer 3
- [ ] No circular dependencies exist
- [ ] Context propagation follows Layer 2 patterns
- [ ] Exception handling uses Layer 2 hierarchy
- [ ] Logging uses AspectJ from Layer 2
- [ ] Response building uses Layer 2 assemblers
