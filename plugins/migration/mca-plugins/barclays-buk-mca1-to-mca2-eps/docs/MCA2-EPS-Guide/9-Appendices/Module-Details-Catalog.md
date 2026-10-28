# Module Details Catalog: Complete Reference

## Executive Summary

Comprehensive catalog of all 52 core modules and 8 extension libraries in MCA2, organized by layer, tier, and functionality. Includes descriptions, dependencies, and usage patterns for each module.

---

## Module Organization

### Layer Model
```
Layer 1 (Foundation): 3 modules - No internal imports allowed
Layer 2 (Core Service): 6 modules - Import Layer 1 only
Layer 3 (Configuration): 3 modules - Import Layer 1-2
Layer 4 (Integration): 11 modules - Import Layer 1-3
Layer 5 (Extension): 8 modules - Optional specialization
Layer 6 (Examples): 4 modules - Reference implementations
```

### Total Module Count
```
Core Modules (mca-libraries/):     52 modules
Extension Modules (mca-extension-libraries/): 8 modules
Example Applications (mca-examples/): 4 modules
Bill of Materials (mca-java-common-bom): 1 module
─────────────────────────────────────────────────
TOTAL:                               65 modules
```

---

## LAYER 1: FOUNDATION MODULES (No imports)

### Module 1: mca-context

| Attribute | Value |
|-----------|-------|
| Group | `com.barclays.global.mca.libs` |
| Artifact | `mca-context` |
| Version | From BOM (`2.2.x`) |
| Location | `mca-libraries/mca-context/` |

**Category:** Data Model / Core Foundation

**Purpose:** Root context data structure (IOLSchema) and 25+ context classes

**Classes:**
- `IOLSchema.java` - Root container for all context data
- `CustomerContext.java` - Customer/account information
- `UserContext.java` - User identity and permissions
- `AccountContext.java` - Account details
- `ProcessContext.java` - Transaction process data
- `DeviceContext.java` - Device information
- `CallerContext.java` - Caller/API consumer info
- `CaseContext.java` - Case/ticket information
- `LocaleContext.java` - Locale/language preferences
- `SecureContext.java` - Security/encryption context
- `ChannelContext.java` - Channel (web/mobile/ATM)
- `GeoLocationContext.java` - Geographic information
- Plus 13+ additional context types

**Key Methods:**
```java
IOLSchema schema = new IOLSchema();
schema.put("customer", new CustomerContext());
CustomerContext ctx = schema.get(CustomerContext.class);
```

**Exports:**
- Interfaces: `IContext`, `IContextType`
- Annotations: `@Context`, `@Required`
- Utilities: `ContextMapper`, `ContextValidator`

**Imports:** None (Foundation)

**Coupling Strength:** CRITICAL (used by 99% of modules)

**Replacement Cost:** EXTREME - Cannot be changed

---

### Module 2: mca-exception-handling-core

| Attribute | Value |
|-----------|-------|
| Group | `com.barclays.global.mca.libs` |
| Artifact | `mca-exception-handling-core` |
| Version | From BOM (`2.2.x`) |
| Location | `mca-libraries/mca-exception-handling-core/` |

**Category:** Exception Hierarchy

**Purpose:** Standardized exception model mapping to HTTP status codes

**Exception Hierarchy:**
```
GenericException (base)
├─ ApplicationException (200 OK - app error)
├─ RequestException (400 Bad Request)
├─ NotFoundException (404 Not Found)
├─ AuthorizationException (403 Forbidden)
└─ ServerException (500 Internal Server Error)
```

**Key Classes:**
- `GenericException.java` - Base class with HTTP status mapping
- `ErrorCode.java` - Standardized error codes
- `ResponseHttpStatus.java` - HTTP status enum
- `ErrorDetails.java` - Error information container

**Usage:**
```java
throw new RequestException("Invalid input", ErrorCode.VALIDATION_ERROR);
throw new NotFoundException("User not found: " + userId);
throw new AuthorizationException("Insufficient permissions");
throw new ServerException("Database connection failed");
```

**Imports:** None (Foundation)

**Coupling Strength:** CRITICAL (exception contract)

**Replacement Cost:** EXTREME - Cannot break

---

### Module 3: mca-logging-aspects

| Attribute | Value |
|-----------|-------|
| Group | `com.barclays.global.mca.libs` |
| Artifact | `mca-logging-aspects` |
| Version | From BOM (`2.2.x`) |
| Location | `mca-libraries/mca-logging-aspects/` |

**Category:** Cross-Cutting Concerns / AspectJ

**Purpose:** Compile-time AspectJ weaving for SLF4J interception

**Capabilities:**
- Intercept all SLF4J.getLogger() calls
- Automatic performance logging via @PerfLogParam
- Data masking via @Masked annotation
- Correlation ID propagation through MDC
- ThreadLocal context tracking

**Key Aspects:**
- `LoggingAspect` - Main logging interception
- `MaskingAspect` - Field-level masking
- `PerformanceAspect` - Execution time tracking
- `CorrelationAspect` - Correlation ID management

**Usage:**
```java
// Automatic masking
@Masked(pattern = MaskingPattern.CREDIT_CARD)
private String cardNumber;

// Automatic performance logging
@PerfLogRecordedOperation(name = "processOrder")
public void processOrder(Order order) { }
```

**Imports:** None (AspectJ weaves at compile time)

**Coupling Strength:** CRITICAL (all modules use SLF4J)

**Replacement Cost:** EXTREME - Cannot change

---

## LAYER 2: CORE SERVICE MODULES

### Module 3a: mca-oas-validation

| Attribute | Value |
|-----------|-------|
| Group | `com.barclays.global.mca.libs` |
| Artifact | `mca-oas-validation` |
| Version | From BOM (`2.2.x`) |
| Location | `mca-libraries/mca-oas-validation/` |

**Category:** Request Validation / OpenAPI

**Purpose:** OpenAPI 3.0 request validation engine. Provides the core validation logic for validating HTTP requests against OpenAPI specifications, used by the `ValidationFilter` in `mca-filter-core` and by `mca-secure-proxy-core`.

**Key Classes:**
- `OASRequestValidation.java` - Core validation engine that validates HTTP requests against an OpenAPI 3.0 spec using the Atlassian swagger-request-validator library
- `OasProvider.java` - Strategy interface for loading OpenAPI specifications
- `SimpleOasProvider.java` - Loads OAS from a Spring Resource (classpath or file path)
- `EmptyOasProvider.java` - No-op implementation when validation is disabled
- `OasValidationResult.java` - Contains validation status, error flags, and a list of validation messages
- `OasValidationMessage.java` - Individual validation message with title, detail, and severity

**Exception Types:**
- `OASValidationException` - Thrown when OAS validation encounters an unrecoverable error
- `OASResourceNotFoundException` - Thrown when the specified OpenAPI spec resource cannot be loaded

**Design Patterns:**
- **Strategy**: `OasProvider` interface with `SimpleOasProvider` and `EmptyOasProvider` implementations
- Decouples spec loading from validation logic

**Usage:**
```java
// OasProvider loads the OpenAPI spec
OasProvider provider = new SimpleOasProvider(oasResource);

// OASRequestValidation performs validation
OASRequestValidation validator = new OASRequestValidation(provider);
OasValidationResult result = validator.validate(httpServletRequest);

if (result.hasErrors()) {
    // Handle validation failures
    List<OasValidationMessage> messages = result.getMessages();
}
```

**External Dependency:** `com.atlassian.oai:swagger-request-validator-spring-webmvc:2.45.1`

**Imports:** mca-exception-handling-core

**Coupling Strength:** MEDIUM (used by mca-filter-core and mca-secure-proxy-core)

**Replacement Cost:** MEDIUM - Validation engine can be swapped if OasProvider interface is preserved

---

### Module 4: mca-context-utils

| Attribute | Value |
|-----------|-------|
| Group | `com.barclays.global.mca.libs` |
| Artifact | `mca-context-utils` |
| Version | From BOM (`2.2.x`) |
| Location | `mca-libraries/mca-context-utils/` |

**Category:** Utilities / Data Manipulation

**Purpose:** Serialization, deserialization, and manipulation utilities for IOLSchema

**Key Classes:**
- `ContextMapper.java` - Map context to/from JSON
- `ContextValidator.java` - Validate context schema
- `ContextSerializer.java` - Serialize for HTTP headers
- `ContextDeserializer.java` - Deserialize from headers

**Key Methods:**
```java
// Serialize context for HTTP headers
String jsonContext = ContextMapper.toJson(schema);

// Deserialize from HTTP headers
IOLSchema schema = ContextMapper.fromJson(jsonHeader);

// Validate context integrity
ContextValidator.validate(schema);
```

**Imports:** mca-context

**Coupling Strength:** HIGH (8+ modules depend)

**Replacement Cost:** HIGH - Changes need careful planning

---

### Module 5: mca-filter-core

| Attribute | Value |
|-----------|-------|
| Group | `com.barclays.global.mca.libs` |
| Artifact | `mca-filter-core` |
| Version | From BOM (`2.2.x`) |
| Location | `mca-libraries/mca-filter-core/` |

**Category:** Filter Chain / Request Processing

**Purpose:** 13 core and optional filters for request processing

**Core Filters (always in chain):**
- `CorrelationIdFilter` (Order 0) - Generate/extract correlation ID
- `ExceptionFilter` (Order 1) - Global exception handling
- `DisableSessionFilter` (Order 2) - Prevent session creation
- `MultiReadRequestFilter` (Order 3) - Allow multiple body reads

**Optional Filters (conditional):**
- `ContextFilter` (Order 100) - Propagate context from headers
- `DdosFilter` (Order 150) - Rate limiting
- `DynamicLoggingFilter` (Order 200) - Dynamic log level control
- `ValidationFilter` (Order 300) - OAS request validation (uses mca-oas-validation)
- `PerfLogExclusionFilter` (Order 550) - Performance log exclusions
- `OAuthValidatorFilter` - OAuth token validation
- `RequestWhitelistingFilter` - Allow list checking
- Plus additional optional filters

**Key Interfaces:**
```java
public abstract class OncePerRequestFilter extends Filter {
  protected abstract void doFilterInternal(
    HttpServletRequest request,
    HttpServletResponse response,
    FilterChain chain
  ) throws ServletException, IOException;
}
```

**Imports:** mca-context, mca-context-utils, mca-logging-aspects

**Coupling Strength:** HIGH (6+ modules depend)

**Replacement Cost:** HIGH - Core request processing

---

### Module 6: mca-eps-core

| Attribute | Value |
|-----------|-------|
| Group | `com.barclays.global.mca.libs` |
| Artifact | `mca-eps-core` |
| Version | From BOM (`2.2.x`) |
| Location | `mca-libraries/mca-eps-core/` |

**Category:** Framework Core / Orchestration

**Purpose:** Main EPS framework orchestration and initialization

**Key Classes:**
- `ExperienceAPIConfig.java` - Auto-configuration
- `ExperienceAPIAutoConfiguration.java` - Spring Boot config
- `ExperienceAPI.java` - Main API interface
- `ExperienceAPIEnablement.java` - Feature toggles

**Key Annotation:**
```java
@EnableExperienceAPI
public class MyApplication { }
```

**Imports:** mca-context, mca-context-utils, mca-filter-core, mca-logging-aspects, mca-response-handling-core

**Coupling Strength:** HIGH (5+ modules depend, orchestrates framework)

**Replacement Cost:** HIGH - Framework initialization

---

### Module 7: mca-response-handling-core

| Attribute | Value |
|-----------|-------|
| Group | `com.barclays.global.mca.libs` |
| Artifact | `mca-response-handling-core` |
| Version | From BOM (`2.2.x`) |
| Location | `mca-libraries/mca-response-handling-core/` |

**Category:** Response Envelope / Standardization

**Purpose:** Response<T> envelope and assembly patterns

**Key Classes:**
- `Response<T>` - Generic response envelope
- `ResponseAssembler<T>` - Fluent builder for responses
- `ResponseHttpStatus.java` - HTTP status mapping
- `ResponseMetadata.java` - Response metadata container

**Key Pattern:**
```java
Response.assemble()
  .status("SUCCESS")
  .data(payload)
  .metadata(meta)
  .build()
```

**Imports:** mca-exception-handling-core

**Coupling Strength:** HIGH (6+ modules depend)

**Replacement Cost:** HIGH - Response contract

---

## LAYER 3: CONFIGURATION MODULES

### Module 8-13: mca-logging-config-* (3 variants)

| Attribute | mca-logging-config-log4j | mca-logging-config-logback | mca-logging-config-log4j-json |
|-----------|--------------------------|----------------------------|-------------------------------|
| Group | `com.barclays.global.mca.libs` | `com.barclays.global.mca.libs` | `com.barclays.global.mca.libs` |
| Artifact | `mca-logging-config-log4j` | `mca-logging-config-logback` | `mca-logging-config-log4j-json` |
| Version | From BOM (`2.2.x`) | From BOM (`2.2.x`) | From BOM (`2.2.x`) |
| Location | `mca-libraries/mca-logging-config-log4j/` | `mca-libraries/mca-logging-config-logback/` | `mca-libraries/mca-logging-config-log4j-json/` |

**Category:** Logging Backend Configuration

**Variants:**
1. **mca-logging-config-log4j** - Log4j2 configuration
2. **mca-logging-config-logback** - Logback configuration (Spring default)
3. **mca-logging-config-log4j-json** - JSON output for Log4j2

**Key Features:**
- Async logging for performance
- JSON output support
- Rolling file policies
- Correlation ID pattern configuration

**Selection:**
```
Choose ONE:
├─ Logback: Spring Boot default, recommended for most apps
├─ Log4j2: Async-first, high-performance alternative
└─ Log4j2-JSON: Structured logging for log aggregation
```

**Imports:** mca-logging-aspects

**Coupling Strength:** MEDIUM (optional, mutually exclusive)

**Replacement Cost:** MEDIUM - Can switch between variants

---

## LAYER 4: OPTIONAL FRAMEWORKS

### Module 17: mca-service-client-starter

| Attribute | Value |
|-----------|-------|
| Group | `com.barclays.global.mca.libs` |
| Artifact | `mca-service-client-starter` |
| Version | From BOM (`2.2.x`) |
| Location | `mca-libraries/mca-service-client-starter/` |

**Category:** REST Client / Service Discovery

**Purpose:** Auto-configured RestTemplate with context propagation and circuit breaking

**Key Features:**
- `RestClientFactory` - Creates context-aware RestTemplate
- Automatic correlation ID propagation
- Service discovery support
- Circuit breaker integration

**Usage:**
```java
@Autowired
private RestClientFactory clientFactory;

RestTemplate template = clientFactory.createRestTemplate();
// Correlation ID + context automatically included in headers
```

**Imports:** mca-exception-handling-core, mca-response-handling-core, mca-logging-aspects

**Coupling Strength:** MEDIUM

---

### Module 18: mca-router-http

| Attribute | Value |
|-----------|-------|
| Group | `com.barclays.global.mca.libs` |
| Artifact | `mca-router-http` |
| Version | From BOM (`2.2.x`) |
| Location | `mca-libraries/mca-router-http/` |

**Category:** Request Routing / Request Processing

**Purpose:** Advanced request routing based on URL patterns and custom rules

**Features:**
- Pattern-based routing
- Chain of Responsibility for OrderedRequestProcessor
- Dynamic routing decisions

**Imports:** mca-context, mca-exception-handling-core, mca-response-handling-core

**Coupling Strength:** MEDIUM

---

### Module 19: mca-secure-proxy-core

| Attribute | Value |
|-----------|-------|
| Group | `com.barclays.global.mca.libs` |
| Artifact | `mca-secure-proxy-core` |
| Version | From BOM (`2.2.x`) |
| Location | `mca-libraries/mca-secure-proxy-core/` |

**Category:** Proxy Integration / Session Management

**Purpose:** Session management and proxy authentication

**Features:**
- Proxy session validation
- Session storage (configurable backend)
- Trusted header handling

**Imports:** mca-context, mca-filter-core

**Coupling Strength:** MEDIUM

---

### Module 19a-19c: mca-context-store-* (3 variants) -- Secure Proxy

| Attribute | mca-context-store-rdb | mca-context-store-mongo | mca-context-store-ehcache |
|-----------|----------------------|------------------------|--------------------------|
| Group | `com.barclays.global.mca.libs` | `com.barclays.global.mca.libs` | `com.barclays.global.mca.libs` |
| Artifact | `mca-context-store-rdb` | `mca-context-store-mongo` | `mca-context-store-ehcache` |
| Version | From BOM (`2.2.x`) | From BOM (`2.2.x`) | From BOM (`2.2.x`) |
| Location | `mca-libraries/mca-context-store-rdb/` | `mca-libraries/mca-context-store-mongo/` | `mca-libraries/mca-context-store-ehcache/` |

**Category:** Secure Proxy / Context Storage Backend

**Purpose:** Pluggable context storage backends used by the Secure Proxy module for session persistence. These are **not** EPS core modules.

**Variants:**
1. **mca-context-store-rdb** - PostgreSQL/Oracle/MySQL
2. **mca-context-store-mongo** - MongoDB
3. **mca-context-store-ehcache** - EHCache in-memory

**Selection Guide:**
```
RDB: ACID, persistent, scalable with replication
MongoDB: Scalable, flexible schema, eventually consistent
EHCache: Fast, in-memory, single-instance only
```

**Imports:** mca-context, mca-context-utils, mca-exception-handling-core

**Coupling Strength:** MEDIUM (choose exactly one when using Secure Proxy)

**Replacement Cost:** MEDIUM - Can migrate between backends

---

### Module 19d: mca-process-lib

| Attribute | Value |
|-----------|-------|
| Group | `com.barclays.global.mca.libs` |
| Artifact | `mca-process-lib` |
| Version | From BOM (`2.2.x`) |
| Location | `mca-libraries/mca-process-lib/` |

**Category:** Process / Journey Definition

**Purpose:** Load and serve process.json definitions that define MCA journey structure, including tasks, events, endpoint routing, context requirements, and OAS references.

**Key Classes:**
- `ProcessService.java` - Interface for loading process definitions
- `ClasspathResourceProcessService.java` - Default implementation that loads process JSON from the classpath
- `ProcessController.java` - REST controller serving process definitions at `/process/{processId}` and `/process/{version}/{processId}`

**Process File Convention:**
```
processes/{processName}_v{versionNumber}.json
```

**REST Endpoints:**
```
GET /process/{processId}
GET /process/{version}/{processId}
```

**Usage:**
```java
// ProcessService loads process definitions from classpath
@Autowired
private ProcessService processService;

// ProcessController exposes them via REST
// Auto-configured when process-lib is on classpath
```

**Imports:** None (standalone)

**Coupling Strength:** MEDIUM (used by secure-proxy-core and consuming apps)

**Replacement Cost:** MEDIUM - ProcessService interface allows alternative implementations

**Related:** The `mca-secure-proxy-api` module defines process-related interfaces and models used during process bootstrap and routing:
- `ProcessDiscovery` - Interface to resolve a launchId to a process JSON definition
- `ProcessDefinition` - Model representing a loaded process definition
- `ProcessMetadata` - Metadata associated with a process
- `LaunchProcess` - Request model for process launch
- `BootstrapContext` - Context used during process initialization
- `ContextData` - Context data container for process endpoints
- `EndPoint` - Model defining backend service URIs, required contexts, HTTP methods, and OAS schemas

These classes are consumed by `BootstrapService` in `mca-secure-proxy-core`, which orchestrates the full process initialization lifecycle.

---

### Module 20: mca-masking

| Attribute | Value |
|-----------|-------|
| Group | `com.barclays.global.mca.libs` |
| Artifact | `mca-masking` |
| Version | From BOM (`2.2.x`) |
| Location | `mca-libraries/mca-masking/` |

**Category:** Data Protection / Security

**Purpose:** Field-level and request/response data masking

**Patterns Supported:**
- Credit cards (last 4 visible)
- Email addresses (user@ visible)
- Phone numbers (last 4 visible)
- SSN (last 4 visible)
- Custom patterns via regex

**Usage:**
```java
@Masked(pattern = MaskingPattern.CREDIT_CARD)
private String cardNumber;

@Masked(pattern = MaskingPattern.EMAIL)
private String email;
```

**Imports:** mca-logging-aspects

**Coupling Strength:** MEDIUM

---

### Module 21: mca-placeholder-starter

| Attribute | Value |
|-----------|-------|
| Group | `com.barclays.global.mca.libs` |
| Artifact | `mca-placeholder-starter` |
| Version | From BOM (`2.2.x`) |
| Location | `mca-libraries/mca-placeholder-starter/` |

**Category:** Property Resolution / Configuration

**Purpose:** Chained property placeholder resolution (JCEKS → Vault → Spring)

**Features:**
- JCEKS keystore support for encrypted properties
- HashiCorp Vault integration
- Standard Spring properties resolution
- Property chain ordering

**Imports:** mca-logging-aspects

**Coupling Strength:** LOW

---

### Module 22: mca-oauth-validator-core

| Attribute | Value |
|-----------|-------|
| Group | `com.barclays.global.mca.libs` |
| Artifact | `mca-oauth-validator-core` |
| Version | From BOM (`2.2.x`) |
| Location | `mca-libraries/mca-oauth-validator-core/` |

**Category:** Security / OAuth

**Purpose:** OAuth2 token validation and caching

**Features:**
- Token validation against provider
- Token caching for performance
- Refresh token handling

**Imports:** mca-exception-handling-core

**Coupling Strength:** LOW

---

## LAYER 5: EXTENSION MODULES

### Module 23: mca-jceks-spring-properties-processor

| Attribute | Value |
|-----------|-------|
| Group | `com.barclays.global.mca` |
| Artifact | `jceks-spring-properties-processor` |
| Version | From BOM (`2.2.x`) |
| Location | `mca-extension-libraries/jceks-spring-properties-processor/` |

**Category:** Secrets / Encryption

**Purpose:** Property decryption from JCEKS keystores

**Usage:**
```properties
# application.properties
app.secret={JCEKS}secrets.jceks:secret-key:keystorepass
```

**Imports:** None (optional post-processor)

**Coupling Strength:** LOW

---

### Module 24: mca-service-locator

| Attribute | Value |
|-----------|-------|
| Group | `com.barclays.global.mca` |
| Artifact | `service-locator` |
| Version | From BOM (`2.2.x`) |
| Location | `mca-extension-libraries/service-locator/` |

**Category:** Service Discovery / LDAP

**Purpose:** LDAP-based service discovery (legacy)

**Note:** Deprecated - use Spring Cloud Consul instead

**Imports:** None (legacy standalone)

**Coupling Strength:** LOW

---

### Module 25-27: bem-client, mis-client, mca-spring-boot-ssl

| Attribute | bem-client | mis-client | spring-boot-ssl |
|-----------|-----------|-----------|-----------------|
| Group | `com.barclays.global.mca` | `com.barclays.global.mca` | `com.barclays.global.mca` |
| Artifact | `bem-client` | `mis-client` | `spring-boot-ssl` |
| Version | From BOM (`2.2.x`) | From BOM (`2.2.x`) | From BOM (`2.2.x`) |
| Location | `mca-extension-libraries/bem-client/` | `mca-extension-libraries/mis-client/` | `mca-extension-libraries/spring-boot-ssl/` |

**Category:** Integration / Legacy / Infrastructure

**Purpose:** Legacy system integration (BEM/MIS) and SSL certificate management

**Imports:** mca-context (for context propagation)

**Coupling Strength:** LOW

---

### Module 28-30: mca-reference-data, mca-entitlement, mca-sso

| Attribute | mca-reference-data | mca-entitlement | mca-sso |
|-----------|-------------------|-----------------|---------|
| Group | `com.barclays.global.mca.libs` | `com.barclays.global.mca.libs` | `com.barclays.global.mca.libs` |
| Artifact | `mca-referencedata` | `mca-entitlement` | `mca-sso` |
| Version | From BOM (`2.2.x`) | From BOM (`2.2.x`) | From BOM (`2.2.x`) |
| Location | `mca-libraries/mca-referencedata/` | `mca-libraries/mca-entitlement/` | `mca-libraries/mca-sso/` |

**Category:** Domain Features / Authorization

**Purpose:** Reference data access, role-based authorization, Single Sign-On

**Imports:** mca-context (optionally)

**Coupling Strength:** LOW

---

## LAYER 6: EXAMPLE APPLICATIONS

### Module 31: mca-experience-api-host-reference-app

| Attribute | Value |
|-----------|-------|
| Published Artifact | None (reference application) |
| Location | `mca-examples/mca-experience-api-host-reference-app/` |

**Type:** Simple REST API

**Demonstrates:** Basic @EnableExperienceAPI, filter chain, response handling

**Learning Path:** START HERE for beginners

---

### Module 32: mca-experience-api-cardcontrol-reference-app

| Attribute | Value |
|-----------|-------|
| Published Artifact | None (reference application) |
| Location | `mca-examples/mca-experience-api-cardcontrol-reference-app/` |

**Type:** Secure Proxy Integration

**Demonstrates:** Advanced framework, service-to-service, masking, events

**Learning Path:** SECOND (after Host Reference)

---

### Module 33: mca-experience-api-secureproxy-reference-app

| Attribute | Value |
|-----------|-------|
| Published Artifact | None (reference application) |
| Location | `mca-examples/mca-experience-api-secureproxy-reference-app/` |

**Type:** API Gateway

**Demonstrates:** Routing, request transformation, proxy patterns

**Learning Path:** THIRD (for gateway builders)

---

### Module 34: mca-config-server-reference-app

| Attribute | Value |
|-----------|-------|
| Published Artifact | None (reference application) |
| Location | `mca-examples/mca-config-server-reference-app/` |

**Type:** Configuration Server

**Demonstrates:** Centralized config, property resolution, encryption

**Learning Path:** OPTIONAL (if using distributed config)

---

## Bill of Materials

### Module 35: mca-java-common-bom

| Attribute | Value |
|-----------|-------|
| Group | `com.barclays.global.mca.libs` (also published as `com.barclays.global.mca:mca-dependencies`) |
| Artifact | `mca-java-common-bom` |
| Version | `2.2.x` |
| Location | `mca-java-common-bom/` |

**Purpose:** Centralized dependency version management

**Key Managed Dependencies:**
- Spring Boot 3.5.10
- Spring Cloud 2025.0.1
- Jakarta EE 10.0.0
- Java 21
- AspectJ 1.9.25.1

**Usage:**
```gradle
dependencyManagement {
  imports {
    mavenBom "com.barclays.global.mca:mca-java-common-bom:2.2.020"
  }
}
```

---

## Dependency Impact Analysis

### High Impact Modules (Change requires broad coordination)

1. **mca-context** - Changes break virtually all modules
2. **mca-logging-aspects** - Changes affect logging everywhere
3. **mca-exception-handling-core** - Changes affect error handling

### Medium Impact (Careful coordination needed)

4. **mca-filter-core** - Request processing pattern changes
5. **mca-eps-core** - Framework initialization changes
6. **mca-response-handling-core** - Response contract changes

### Low Impact (Generally safe to change)

- Optional frameworks (router, secure-proxy, etc.)
- Integration modules (bem-client, sso, etc.)
- Configuration modules (if not breaking Spring auto-config)

---

## Module Selection Matrix

**For Simple REST API:**
- ✅ mca-context
- ✅ mca-filter-core
- ✅ mca-eps-core
- ✅ mca-exception-handling-core
- ✅ mca-response-handling-core
- ✅ mca-logging-config-logback

**For Microservice with Service Calls:**
- Add: mca-service-client-starter
- Add: mca-masking (optional)
- Add: mca-logging-aspects (recommended)

**For Multi-Tenant SaaS:**
- Add: mca-masking
- Add: custom tenant routing logic
- If using Secure Proxy: select context store backend (mca-context-store-rdb or mca-context-store-mongo)

**For API Gateway:**
- Add: mca-router-http
- Add: mca-secure-proxy-core
- Add: mca-context-store-* (select backend for Secure Proxy session storage)
- Keep optional filters minimal

---

## Next Steps

1. **Identify Your Use Case** — Which modules do you need?
2. **Review Dependencies** — Ensure no circular imports
3. **Configure Logging** — Choose logging backend
4. **If Using Secure Proxy** — Select a context store backend (RDB, MongoDB, or EHCache)
5. **Integrate Gradually** — Add optional frameworks incrementally

**Module Details Catalog provides complete framework inventory.**

