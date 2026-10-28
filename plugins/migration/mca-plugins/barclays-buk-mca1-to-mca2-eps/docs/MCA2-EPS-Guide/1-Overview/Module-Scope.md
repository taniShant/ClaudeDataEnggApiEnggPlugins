# MCA2 Module Scope: Focus Areas & Dependencies

## Module Classification

The MCA Java Common repository contains 60+ modules organized into three categories. This documentation focuses on core EPS (Enterprise Presentation Services) framework modules while acknowledging supporting and specialized modules.

---

## TIER 1: CORE EPS FRAMEWORK (Primary Focus)

These modules are **essential** for all EPS-based applications. Understanding these is mandatory for MCA2 development.

### Context System Modules

| Module | Package | Purpose | Status |
|--------|---------|---------|--------|
| **mca-context** | `com.barclays.global.mca.libs.context.data` | IOL data model (25+ context classes: UserContext, CustomerContext, AccountContext, ProcessContext, DeviceContext, etc.) | ✅ CORE |
| | | Core to all request processing and context propagation | |
| **mca-context-utils** | `com.barclays.global.mca.libs.context.utils` | Context serialization, deserialization, validation | ✅ CORE |
| | | Provides utilities for manipulating IOLSchema objects | |
| **mca-spring-context-utils** | `com.barclays.global.mca.libs` | Spring-specific context utilities and request scope management | ✅ CORE |
| | | Integrates context into Spring request lifecycle | |

### Filter Chain Modules

| Module | Package | Purpose | Status |
|--------|---------|---------|--------|
| **mca-filter-core** | `com.barclays.global.mca.libs.filters` | 13 servlet filters implementing request processing chain | ✅ CORE |
| | | CorrelationIdFilter, ExceptionFilter, DisableSessionFilter, MultiReadRequestFilter, OAuthValidatorFilter, DdosFilter, ValidationFilter, RequestWhiteListingFilter, DynamicLoggingFilter, PerfLogExclusionFilter, + more | |
| | `com.barclays.global.mca.libs.filters.providers` | DdosPreventor strategy implementations | ✅ CORE |

### EPS-Core Framework Modules

| Module | Package | Purpose | Status |
|--------|---------|---------|--------|
| **mca-eps-core** | `com.barclays.global.mca.libs.eps` | Master EPS framework orchestration | ✅ CORE |
| | | @EnableExperienceAPI annotation and auto-configuration | |
| | | ExperienceAPIConfig, CoreFilterConfig, IOLContextHandlerMethodArgumentResolver | |
| | `com.barclays.global.mca.libs.eps.annotations` | @IOLContext annotation for automatic context injection | ✅ CORE |

### Exception & Response Handling Modules

| Module | Package | Purpose | Status |
|--------|---------|---------|--------|
| **mca-exception-handling-core** | `com.barclays.global.mca.libs.core.exceptions` | Exception hierarchy: GenericException, ApplicationException, ServerException, RequestException, NotFoundException, AuthorizationException | ✅ CORE |
| | | HTTP status mapping for exceptions | |
| **mca-response-handling-core** | `com.barclays.global.mca.libs.core.response` | Response<T> envelope, ResponseAssembler fluent API | ✅ CORE |
| | `com.barclays.global.mca.libs.core.response.assemblers` | SuccessResponseAssembler, ErrorResponseAssembler patterns | ✅ CORE |

### Logging & Observability Modules

| Module | Package | Purpose | Status |
|--------|---------|---------|--------|
| **mca-logging-aspects** | `com.barclays.global.mca.aspecting` | AspectJ compile-time weaving for SLF4J calls | ✅ CORE |
| | | Masking integration, performance logging | |
| **mca-logging-config-log4j** | | Log4j 2 backend with JSON support | ✅ CORE |
| **mca-logging-config-logback** | | Logback backend with JSON support | ✅ CORE |
| **mca-masking** | `com.barclays.global.mca.masking` | Data redaction/masking framework | ✅ CORE |
| | | StringMasker, JsonStringMasker, Redactor implementations | |

### Utilities & Support Modules (Core)

| Module | Purpose | Status |
|--------|---------|--------|
| **mca-common-utils** | General utility functions | ✅ CORE |
| **mca-web-utils** | Web/servlet utilities (WebUtils.setIOLSchemaInScope) | ✅ CORE |
| **mca-schema-validation** | JSON schema validation | ✅ CORE |

---

## TIER 2: OPTIONAL MAJOR FRAMEWORKS (Conditional Use)

These modules add significant capabilities but are **optional** depending on application requirements.

### Routing Framework

| Module | Purpose | Use Case | Status |
|--------|---------|----------|--------|
| **mca-router-api** | Routing contract interfaces | Custom routing implementations | ⚠️ OPTIONAL |
| **mca-router-http** | HTTP-based routing implementation | Request routing to backend services | ⚠️ OPTIONAL |

**When to use:** Applications that need dynamic request routing, circuit breaking, or protocol adaptation.

### Secure Proxy Framework

| Module | Purpose | Use Case | Status |
|--------|---------|----------|--------|
| **mca-secure-proxy-api** | Secure proxy service contracts | Custom proxy implementations | ⚠️ OPTIONAL |
| **mca-secure-proxy-core** | Comprehensive proxy implementation | Request transformation, protocol bridging | ⚠️ OPTIONAL |
| **mca-secure-proxy-routing-gateway** | Gateway-specific routing | API gateway deployments | ⚠️ OPTIONAL |

**When to use:** Applications that need request transformation, protocol adaptation, or centralized gateway functionality.

### Service Client Framework

| Module | Purpose | Use Case | Status |
|--------|---------|----------|--------|
| **mca-service-client** | REST client core | Low-level HTTP client control | ⚠️ OPTIONAL |
| **mca-service-client-starter** | Spring Boot auto-configuration starter | Standardized REST client configuration | ⚠️ OPTIONAL |

**When to use:** Applications making REST calls to external services (optional; standard Spring RestTemplate works fine).

### Property Resolution Framework

| Module | Purpose | Use Case | Status |
|--------|---------|----------|--------|
| **mca-placeholder-resolvers** | Chained placeholder processor pattern | Custom property source integration | ⚠️ OPTIONAL |
| **mca-placeholder-converter** | Property value conversion | Type conversion utilities | ⚠️ OPTIONAL |
| **mca-placeholder-starter** | Spring Boot auto-configuration | Advanced property resolution | ⚠️ OPTIONAL |
| **mca-placeholder-vault-resolver** | HashiCorp Vault integration | Secrets management from Vault | ⚠️ OPTIONAL |

**When to use:** Applications with complex property resolution needs or Vault-based secrets management.

### Security & OAuth

| Module | Purpose | Use Case | Status |
|--------|---------|----------|--------|
| **mca-oauth-validator-core** | JWT token validation | OAuth/JWT-based security | ⚠️ OPTIONAL |

**When to use:** Applications using OAuth2/JWT token-based authentication.

---

## TIER 3: INTEGRATION & EXTENSION LIBRARIES (Specialized)

These modules integrate with specific external systems or provide specialized functionality.

### External System Clients

| Module | Purpose | Use Case | Status |
|--------|---------|----------|--------|
| **bem-client** (extension) | BEM (Business Entity Management) system client | Legacy BEM integration | 🔴 SPECIALIZED |
| **mis-client** (extension) | MIS (Management Information System) client | MIS data integration | 🔴 SPECIALIZED |
| **tiaaas-client** | TIAA service client | TIAA integration | 🔴 SPECIALIZED |
| **cms** | Content Management Service client | CMS integration | 🔴 SPECIALIZED |

### Security & Encryption

| Module | Purpose | Use Case | Status |
|--------|---------|----------|--------|
| **jceks-spring-properties-processor** (extension) | JCEKS keystore property processor | Encrypted property management | 🔴 SPECIALIZED |
| **bcag** | BCAG encryption client | Barclays encryption service | 🔴 SPECIALIZED |
| **spring-boot-ssl** (extension) | SSL/TLS configuration | Custom SSL configuration | 🔴 SPECIALIZED |

### Service Discovery & Configuration

| Module | Purpose | Use Case | Status |
|--------|---------|----------|--------|
| **service-locator** (extension) | Spring Service Locator integration | Service discovery | 🔴 SPECIALIZED |
| **consul-process-discovery** | Consul-based service discovery | HashiCorp Consul integration | 🔴 SPECIALIZED |
| **remote-discovery** | Remote service discovery | Dynamic service endpoint resolution | 🔴 SPECIALIZED |

### Other Specialized Modules

| Module | Purpose | Status |
|--------|---------|--------|
| **mca-entitlement** | Authorization/entitlement checks | 🔴 SPECIALIZED |
| **mca-sso**, **mca-sso-bam** | Single Sign-On integration | 🔴 SPECIALIZED |
| **mca-referencedata** | Reference data management with caching | 🔴 SPECIALIZED |
| **mca-process**, **mca-process-lib** | Process/workflow context | 🔴 SPECIALIZED |
| **mca-i18n** | Internationalization support | 🔴 SPECIALIZED |
| **mca-activity-logging** | Activity trail logging | 🔴 SPECIALIZED |
| **mca-ecrime-logging** | E-crime reporting | 🔴 SPECIALIZED |
| **mca-external-resources** | External resource management | 🔴 SPECIALIZED |
| **mca-refresh-utils** | Property refresh utilities | 🔴 SPECIALIZED |
| **mca-legacy-common** (extension) | Legacy MCA compatibility | 🔴 SPECIALIZED |
| **test-common** (extension) | Shared test utilities (MCAApplicationContextRule) | 🔴 TESTING |

---

## TIER 4: BILL OF MATERIALS & PLATFORM

| Module | Purpose | Status |
|--------|---------|--------|
| **mca-java-common-bom** | Bill of Materials for dependency management | ✅ PLATFORM |

---

## Reference Applications

The repository includes 4 reference example applications demonstrating EPS usage patterns:

### **experience-api-cardcontrol-reference-app** (PRIMARY EXAMPLE)
- **Location:** `mca-examples/mca-experience-api-cardcontrol-reference-app`
- **Java Files:** 119 files
- **Focus:** Card control operations via REST API
- **Key Patterns:**
  - @EnableExperienceAPI for EPS framework
  - @IOLContext injection for context propagation
  - CardControlService and CardControlController
  - File upload handling
  - Integration tests with WireMock mocking
  - MisServiceClient integration
  - Reference data repository
  - Masking configuration (CCN, email, CRLF)
- **Integration Tests:** 15+ test classes in src/it/java/
- **Usage:** Primary reference for learning EPS patterns

### **secure-proxy-reference-app**
- **Location:** `mca-examples/mca-secure-proxy-reference-app`
- **Focus:** Secure proxy framework demonstration
- **Key Patterns:**
  - Context storage backends (part of the Secure Proxy module, not core EPS)
  - JWT token service integration
  - HTTP client connection testing
  - Authentication validator patterns
- **Usage:** Reference for proxy and security patterns

### **config-server-app**
- **Location:** `mca-examples/mca-config-server-app`
- **Focus:** Spring Cloud Config Server
- **Usage:** Configuration server reference

### **host-reference-app**
- **Location:** `mca-examples/mca-host-reference-app`
- **Focus:** Generic host/container reference
- **Usage:** Minimal skeleton application reference

---

## Module Dependency Graph

### Core EPS Request Processing Stack

```
┌──────────────────────────────────────────────────────┐
│ Consuming Application                                │
│ (@EnableExperienceAPI, @IOLContext injections)      │
└────────────────────┬─────────────────────────────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
    │                │                │
    v                v                v
┌─────────────────────────────────────────────────────┐
│ EPS-Core (mca-eps-core)                            │
│ - ExperienceAPIConfig (auto-config)                 │
│ - CoreFilterConfig (filter registration)            │
│ - IOLContextHandlerMethodArgumentResolver           │
└──┬──────────────────────────────────────────────────┘
   │
   ├─→ mca-context (IOLSchema data model)
   │   └─→ mca-context-utils (serialization)
   │
   ├─→ mca-filter-core (13 filters)
   │   └─→ mca-web-utils (request scope mgmt)
   │
   ├─→ mca-exception-handling-core (exception mapping)
   │
   ├─→ mca-response-handling-core (Response<T>)
   │
   ├─→ mca-logging-aspects (AspectJ weaving)
   │   └─→ mca-logging-config-* (backend)
   │
   └─→ mca-masking (redaction)
```

> **Note:** Context storage backends (mca-context-store-rdb, mca-context-store-mongo, mca-context-store-ehcache) are part of the Secure Proxy module, not the core EPS framework.

### Optional Framework Layers

```
        Application Layer
              │
    ┌─────────┼─────────┐
    │         │         │
    v         v         v
[Router]  [SecureProxy] [ServiceClient]
    │         │         │
    └─────────┼─────────┘
              │
       [EPS Core Stack]
```

---

## Module Selection Quick Guide

### For Basic EPS Applications

**Required:**
- mca-context, mca-context-utils, mca-spring-context-utils
- mca-filter-core, mca-eps-core
- mca-exception-handling-core, mca-response-handling-core
- mca-logging-aspects + one of: mca-logging-config-log4j or mca-logging-config-logback
- mca-masking

**Gradle dependency (via BOM):**
```gradle
dependencyManagement {
    imports {
        mavenBom "com.barclays.global.mca:mca-java-common-bom:X.X.X"
    }
}

dependencies {
    implementation 'com.barclays.global.mca:mca-context'
    implementation 'com.barclays.global.mca:mca-eps-core'
    runtimeOnly 'com.barclays.global.mca:mca-logging-config-log4j'  // Pick one logging
}
```

### For Applications with REST Clients

Add to basic stack:
- mca-service-client-starter (optional; RestTemplate works fine)

### For Applications with Routing

Add to basic stack:
- mca-router-http

### For Applications with Proxy Requirements

Add to basic stack:
- mca-secure-proxy-core
- (includes: mca-router-http internally)

### For Applications with Vault Integration

Add to basic stack:
- mca-placeholder-vault-resolver

---

## Scope Rationale: Why We De-Emphasize Certain Modules

### Router Framework (mca-router-*)
**Rationale:** Optional advanced feature
- Not required for basic EPS
- Adds complexity for conditional routing
- Most applications use straightforward Spring routing
- Documented in Tier 3 for reference

### Secure Proxy (mca-secure-proxy-*)
**Rationale:** Specialized infrastructure component
- Not required for basic EPS
- Used primarily for protocol adaptation/bridging
- Often deployed as separate service (API Gateway)
- Advanced feature for gateway deployments

### Legacy Integration Modules (bem-client, mis-client)
**Rationale:** Integration with legacy systems
- Not part of core EPS framework
- Required only for specific legacy service integrations
- Would dilute documentation focus
- Covered briefly in integration scenarios

### Specialized Clients (bcag, tiaaas-client, cms)
**Rationale:** External system integrations
- Not part of core EPS
- Used only by specific applications
- Each deserves standalone documentation
- Covered in integration scenarios as needed

---

## Next Steps

1. **Understand Core Stack:** Study modules in Tier 1
2. **Review Reference App:** Study experience-api-cardcontrol-reference-app
3. **Read Core Frameworks:** Review Context System & Filter Chain documentation
4. **Explore Design Patterns:** Understand Strategy, Chain of Responsibility, etc.
5. **Build Your Application:** Follow integration examples

---

## Documentation Cross-References

- **Framework Details:** See `2-Core-Frameworks/` section
- **Design Patterns:** See `3-Design-Patterns/` section
- **Configuration:** See `4-Configuration/` section
- **Implementation Examples:** See `8-Implementation-Examples/` section
- **Module Catalog:** See `9-Appendices/Module-Details-Catalog.md`
- **Filter Reference:** See `9-Appendices/Filter-Configuration-Reference.md`
- **Context Classes:** See `9-Appendices/Context-Classes-Reference.md`
