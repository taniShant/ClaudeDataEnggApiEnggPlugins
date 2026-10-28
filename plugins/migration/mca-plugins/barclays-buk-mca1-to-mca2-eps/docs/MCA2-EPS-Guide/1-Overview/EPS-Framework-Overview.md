# EPS Framework Overview

## Executive Summary

The **Enterprise Presentation Services (EPS)** framework is the core orchestration layer of the MCA Java Common platform, providing distributed context propagation, request processing chains, and standardized response/exception handling for Spring Boot microservices.

The EPS framework enables:
- **Distributed Context Propagation** — IOL (Interoperability Language) schema propagation through HTTP headers
- **Ordered Request Processing** — Chain of Responsibility pattern with 13+ configurable filters
- **Standardized Exception Handling** — Hierarchical exception model with HTTP status mapping
- **Unified Response Envelopes** — Fluent API for consistent response building
- **Cross-Cutting Concerns** — Logging, masking, performance monitoring via AspectJ weaving

---

## Core EPS Components

### 1. **Context System (IOL - Interoperability Language)**
The foundation of distributed request processing in MCA2.

**Key Modules:**
- `mca-context` — 25+ context data classes representing request state (UserContext, CustomerContext, AccountContext, etc.)
- `mca-context-utils` — Serialization, deserialization, and validation utilities

**Responsibility:**
- Define and manage request-scoped context across service boundaries
- Propagate context through HTTP headers (X-UserContext, X-CustomerContext, etc.)
- Validate context schema integrity

**Key Classes:**
```
IOLSchema
├── UserContext (user identity, roles, permissions)
├── CustomerContext (customer info, account associations)
├── AccountContext (account details, business relationships)
├── ProcessContext (process/workflow state)
├── DeviceContext (client device fingerprint)
├── CaseContext (case/incident tracking)
├── Channel (communication channel)
└── [13+ total context types]
```

---

### 2. **Filter Chain (Request Processing Pipeline)**
Implements the Chain of Responsibility pattern for systematic request processing.

**Key Module:** `mca-filter-core`

**Responsibility:**
- Execute ordered filters on each HTTP request
- Provide extension points for custom request processing
- Handle cross-cutting concerns (correlation IDs, exceptions, session management)
- Enable per-request filtering configuration

**Filter Execution Order:**
```
1. CorrelationIdFilter (Order 0)      — Request ID generation and tracing
2. ExceptionFilter (Order 1)           — Global exception handling
3. DisableSessionFilter (Order 2)      — Prevent unwanted session creation
4. MultiReadRequestFilter (Order 3)    — Enable request body re-reading
5. [Custom app filters registered here]
6. [Conditional filters: OAuthValidator, DdosFilter, etc.]
```

**13 Core Filters Implemented:**
- CorrelationIdFilter, ExceptionFilter, DisableSessionFilter, MultiReadRequestFilter
- OAuthValidatorFilter, DdosFilter, ValidationFilter, RequestWhiteListingFilter
- DynamicLoggingFilter, PerfLogExclusionFilter
- [3+ more framework filters]

---

### 3. **EPS-Core Framework**
Central orchestration and Spring Boot integration layer.

**Key Module:** `mca-eps-core`

**Responsibility:**
- Enable EPS framework via `@EnableExperienceAPI` annotation
- Provide `@IOLContext` annotation for automatic context injection
- Register core filters with Spring
- Integrate context resolution into Spring MVC argument resolution
- Provide schema introspection endpoints

**Key Components:**
- `ExperienceAPIConfig` — Master auto-configuration class
- `CoreFilterConfig` — Filter registration and ordering
- `IOLContextHandlerMethodArgumentResolver` — Spring MVC custom argument resolver
- `SchemaController` — Runtime schema introspection

---

### 4. **Response & Exception Handling**
Standardized response envelopes and exception-to-HTTP-status mapping.

**Key Modules:**
- `mca-response-handling-core` — Response<T> entity, ResponseAssembler fluent API
- `mca-exception-handling-core` — Exception hierarchy with HTTP status mapping

**Responsibility:**
- Build standardized response envelopes (success/error)
- Map Java exceptions to HTTP status codes
- Provide clear error messages and severity indicators

**Exception Hierarchy:**
```
GenericException (abstract base)
├── ApplicationException (business logic errors)
├── ServerException (5xx HTTP errors)
├── RequestException (4xx HTTP errors)
├── NotFoundException (404)
└── AuthorizationException (403)
```

**Response Pattern:**
```java
Response.<CardPolicy>assemble()
    .build(cardPolicy)  // Success response
    .error(messages)    // Error response
    .withStatusCode(200)
    .withMessages(List)
```

---

### 5. **Logging Architecture**
Cross-cutting concern for observability via AspectJ compile-time weaving.

**Key Modules:**
- `mca-logging-aspects` — AspectJ compile-time weaving on SLF4J calls
- `mca-logging-config-log4j/logback` — Backend implementations
- `mca-logging-config-log4j-json/logback-json` — JSON output variants

**Responsibility:**
- Intercept all logging calls at compile time
- Add masking/redaction (e.g., credit card numbers)
- Integrate with performance monitoring
- Support multiple logging backends and output formats

---

### 6. **Process System (Journey Definitions)**
Defines and serves MCA journey structures via process.json files.

**Key Modules:**
- `mca-process-lib` (process-lib) -- Loads and serves process.json definitions
- `mca-secure-proxy-api` -- Defines ProcessDiscovery, ProcessDefinition, and related interfaces
- `mca-secure-proxy-core` -- BootstrapService orchestrates process initialization

**Responsibility:**
- Define MCA journeys as process.json files containing tasks, events, and endpoint routing
- Load process definitions from the classpath (`processes/{processName}_v{versionNumber}.json`)
- Serve process definitions via REST endpoints (`/process/{processId}`, `/process/{version}/{processId}`)
- Resolve launchId to a specific process instance via ProcessDiscovery
- Integrate per-process OAS validation via the `apiDefinition` field in process.json
- Support process chaining (parent-child) for multi-step journeys

**Key Classes:**
```
ProcessService (interface)
├── ClasspathResourceProcessService (classpath loader)
ProcessController (REST /process/{processId})

ProcessDiscovery (launchId resolution)
├── BootstrapService (orchestration)
├── LaunchProcess (launch request)
├── BootstrapContext (initialization context)
├── ProcessDefinition (loaded definition)
├── EndPoint (backend URI, contexts, HTTP method, OAS schema)
└── ContextData (context requirements per endpoint)
```

**Integration Points:**
- IOL Context -- Endpoints in process.json specify required contexts (e.g., SystemContext, UserContext)
- OAS Validation -- Each process can reference an apiDefinition for per-endpoint request validation
- Secure Proxy Routing -- Process endpoints define the backend service URIs that the router dispatches to
- URL Obfuscation -- Process URLs can be obfuscated for security

---

## Framework Dependencies & Integration Points

### Consuming Applications Typically Use:

1. **Direct Dependencies:**
   - `mca-context` — Context data model
   - `mca-context-utils` — Context utilities
   - `mca-filter-core` — Filter implementations
   - `mca-eps-core` — Framework orchestration
   - `mca-response-handling-core` — Response building
   - `mca-exception-handling-core` — Exception handling

2. **Auto-Configured via Starter Dependencies:**
   - `mca-logging-config-*` — Logging backend (transitive)
   - `mca-masking` — Redaction utilities (transitive)
   - `mca-service-client-starter` — REST client factories (optional)

3. **Optional Integrations:**
   - `mca-router-http` — HTTP-based request routing
   - `mca-secure-proxy-core` — Request proxying/transformation
   - `mca-placeholder-starter` — Advanced property resolution

---

## Request Flow Through EPS

```
┌─────────────────────────────────────────────────────────┐
│ HTTP Request arrives with IOL headers                   │
│ (X-UserContext, X-CustomerContext, etc.)                │
└────────────────┬────────────────────────────────────────┘
                 │
        ┌────────▼─────────┐
        │ CorrelationId    │  Generates Correlation-ID
        │ Filter           │  Adds request tracing
        │ (Order 0)        │
        └────────┬─────────┘
                 │
        ┌────────▼─────────┐
        │ Context Filter   │  Extracts IOL headers
        │                  │  Validates IOLSchema
        │                  │  Stores in request scope
        └────────┬─────────┘
                 │
        ┌────────▼─────────┐
        │ Exception Filter │  Wraps filter chain
        │ (Order 1)        │  Handles exceptions
        │                  │  Converts to Response<T>
        └────────┬─────────┘
                 │
        ┌────────▼─────────┐
        │ Other Filters    │  DdosFilter, ValidationFilter
        │ (Order 2-N)      │  RequestWhitelistingFilter, etc.
        └────────┬─────────┘
                 │
        ┌────────▼─────────────────────────┐
        │ Controller/Handler Method         │
        │                                   │
        │  @IOLContext IOLSchema context   │  Context injected via
        │  public ResponseEntity<?> api(   │  argument resolver
        │    IOLSchema context             │
        │  ) { ... }                        │
        └────────┬─────────────────────────┘
                 │
        ┌────────▼─────────────────────────┐
        │ Service Logic                     │
        │ - Access context via WebUtils    │
        │ - Build response via Assembler   │
        │ - Throw typed exceptions         │
        └────────┬─────────────────────────┘
                 │
        ┌────────▼─────────────────────────┐
        │ ResponseAssembler                 │
        │ - Builds Response<T> envelope    │
        │ - Adds messages, status codes    │
        │ - Integrates exception handling  │
        └────────┬─────────────────────────┘
                 │
        ┌────────▼─────────────────────────┐
        │ JSON Response                     │
        │ {                                 │
        │   "data": { ... },               │
        │   "messages": [...],             │
        │   "status": "SUCCESS"            │
        │ }                                 │
        └─────────────────────────────────┘
```

---

## Key Design Principles

### 1. **Layered Architecture**
Framework components follow **API → Core → Starter** separation:
- **API Modules** (e.g., `context`, `filter-core`) — Define contracts
- **Core Modules** (e.g., `context-utils`, `filter-core` implementations)  — Implement contracts
- **Starter Modules** (e.g., `service-client-starter`) — Provide Spring Boot auto-configuration

### 2. **Strategy Pattern**
Pluggable implementations for cross-cutting concerns:
- DdosPreventor implementations
- PropertyPlaceholderProcessor chain
- Mask<T> implementations (StringMasker, JsonStringMasker)

### 3. **Enable Annotations**
Fine-grained feature activation via `@Enable*` annotations:
- `@EnableExperienceAPI` — Core EPS framework
- `@EnableSecureProxy` — Secure proxy service
- `@EnableMasking` — Data masking/redaction
- Allows applications to opt-in to specific frameworks

### 4. **Conditional Beans**
Spring `@Conditional*` annotations for feature toggles:
- `@ConditionalOnProperty` — Enable based on configuration
- `@ConditionalOnMissingBean` — Allow application overrides
- `@ConditionalOnClass` — Enable if dependency is on classpath

---

## Module Scope: Focus Areas vs. De-Emphasized

### **FOCUS AREAS** (Priority in this documentation)

✅ **Context System**
- Modules: mca-context, mca-context-utils
- Why: Central to all EPS request processing, required for all consuming apps

✅ **Filter Chain**
- Modules: mca-filter-core, mca-eps-core filter registration
- Why: Fundamental request processing model, primary extension point for applications

✅ **EPS-Core**
- Module: mca-eps-core
- Why: Framework orchestration, Spring integration, annotation processing

✅ **Exception & Response Handling**
- Modules: mca-exception-handling-core, mca-response-handling-core
- Why: Standardized error/success response model, used across all apps

✅ **Logging**
- Modules: mca-logging-aspects, mca-logging-config-*
- Why: Cross-cutting observability, masking integration, widely used

### **DE-EMPHASIZED** (Secondary focus, specialized use cases)

⚠️ **Routing Framework** (mca-router-api, mca-router-http)
- Why: Optional service, not required for basic EPS
- When used: Advanced request routing scenarios

⚠️ **Secure Proxy** (mca-secure-proxy-core)
- Why: Optional advanced feature, not required for basic EPS
- When used: Request transformation, protocol adaptation

⚠️ **Service Client** (mca-service-client-starter)
- Why: Optional convenience utility, apps can use standard RestTemplate
- When used: Standardized REST client configuration

⚠️ **Legacy Integration** (bem-client, mis-client, legacy-common)
- Why: Integration with legacy systems, not core EPS
- When used: Specific legacy service integration scenarios

---

## Target Audience

This documentation is designed for:

1. **New MCA2 Developers**
   - Learning the EPS framework architecture
   - Building applications on MCA2
   - Understanding context propagation and filter chains

2. **Architecture Teams**
   - Evaluating MCA2 adoption
   - Assessing architectural fit for microservices
   - Planning framework integration strategies

3. **DevOps/Platform Teams**
   - Deploying MCA2-based applications
   - Monitoring and troubleshooting EPS behavior

4. **Existing MCA Users**
   - Migrating from MCA1 to MCA2
   - Understanding new patterns and capabilities
   - Planning incremental adoption strategies

---

## Next Steps

1. **Understand the Context System** → Read `IOL-Context-System.md`
2. **Learn Filter Chain Architecture** → Read `Filter-Chain-Architecture.md`
3. **Explore Design Patterns** → Read `3-Design-Patterns/` section
4. **See Reference Implementations** → Read `8-Implementation-Examples/Reference-App-Analysis.md`
5. **Configure Your Application** → Read `4-Configuration/` section

---

## Document Structure

This comprehensive guide is organized into 9 major sections:

1. **Overview** — This document
2. **Core Frameworks** — Context System, Filter Chain, Exception Handling, Logging
3. **Design Patterns** — Strategy, Chain of Responsibility, Template Method, Enable Annotations, Layering
4. **Configuration** — Spring Boot integration, property resolution, filter configuration
5. **Detection Patterns** — Grep/glob patterns for framework discovery
6. **Coupling Analysis** — Scoring system, dependency matrix, risk assessment
7. **Application Integration** — Best practices, integration scenarios, troubleshooting
8. **Implementation Examples** — Complete runnable examples
9. **Appendices** — Reference materials, module catalog, filter reference, context classes

---

## Project Information

- **Repository:** MCA Java Common (mca-java-common)
- **Build Tool:** Gradle 8.5
- **Java Version:** 21
- **Spring Boot:** 3.5.10
- **Spring Cloud:** 2025.0.1
- **Jakarta EE:** Yes (not javax)
- **Total Modules:** 60+
- **Documentation Scope:** 52 mca-libraries + 4 reference apps

---

## License & Usage

This documentation is maintained as part of the MCA Java Common project. All code examples are extracted from the authoritative source (mca-java-common repository).

For questions or corrections, refer to the project's CONTRIBUTING.md guidelines.
