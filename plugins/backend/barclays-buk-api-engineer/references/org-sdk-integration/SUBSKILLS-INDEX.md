# Module Sub-Skills Index

**Delivery Date:** 2026-05-25  
**Status:** Complete - All 7 module sub-skills implemented  
**Location:** `org-sdk-integration/*/SKILL.md`

---

## Overview

This document indexes all 7 module sub-skills that are orchestrated by the `org-sdk-integration` umbrella skill. Each sub-skill is a standalone SKILL.md file that can be registered in the system independently.

---

## Sub-Skills Directory Structure

```
org-sdk-integration/
├── SKILL.md                              ← Umbrella orchestrator
├── MODULE-SUBSKILL-TEMPLATE.md           ← Template pattern
├── README.md                             ← Implementation guide
│
├── standard-rest-api-integration/
│   └── SKILL.md                          ← Module 7 (CALLED FIRST)
│
├── logging-framework-integration/
│   └── SKILL.md                          ← Module 1
│
├── common-functionalities-integration/
│   └── SKILL.md                          ← Module 2
│
├── payload-structure-integration/
│   └── SKILL.md                          ← Module 3
│
├── rest-client-integration/
│   └── SKILL.md                          ← Module 4
│
├── health-check-integration/
│   └── SKILL.md                          ← Module 5
│
├── request-validator-integration/
│   └── SKILL.md                          ← Module 6
│
└── SUBSKILLS-INDEX.md                    ← This file
```

---

## Module Sub-Skills Summary

### Module 7: Standard REST API (Foundation)

**File:** `standard-rest-api-integration/SKILL.md`

**Purpose:** Establishes REST API framework foundation for all other modules

**Key Responsibility:** Called FIRST by umbrella skill

**Generates:**
- Application.java (entry point)
- RestApiConfiguration.java
- SecurityConfiguration.java (JWT/OAuth2)
- GlobalExceptionHandler.java
- RequestResponseFilter.java
- CorrelationIdFilter.java
- ApiDocumentationConfiguration.java (Swagger)

**Input Context:**
- `basePackage` (required)
- `appName` (required)
- `apiVersion` (optional)
- `securityType` (optional, default: JWT)
- `enableSwagger` (optional, default: true)

**Output:**
- 8 generated files (Java classes)
- YAML config updates (all profiles)
- Gradle dependencies (Spring Boot, Security, SpringDoc)

**Merge Strategy:** Non-destructive YAML merge, adds Spring Boot plugins and dependencies

---

### Module 1: Logging Framework

**File:** `logging-framework-integration/SKILL.md`

**Purpose:** Adds comprehensive logging with secure field masking

**Generates:**
- LoggingConfiguration.java
- LoggingConfigurationTest.java

**Input Context:**
- `basePackage` (required)
- `appName` (required)
- `secureFields` (required, array of field names to mask)
- `loggingLevel` (optional, default: ERROR)
- `logPath` (optional, default: /var/log/{appName})

**Output:**
- 2 generated files
- YAML config for logging profiles (dev/prod specific)
- Gradle dependencies (implicit via restapi)

**Key Features:**
- MDC (Mapped Diagnostic Context) support
- Mask/obfuscate/no-log field rules
- Profile-specific logging levels
- Secure field configuration bean

---

### Module 2: Common Functionalities

**File:** `common-functionalities-integration/SKILL.md`

**Purpose:** Provides RestClient factory and HTTP client configuration

**Generates:**
- CommonRestClientConfiguration.java
- RestClientFactory.java
- CommonRestClientConfigurationTest.java
- RestClientFactoryTest.java

**Input Context:**
- `basePackage` (required)
- `appName` (required)
- `producerApis` (optional, list of downstream services)
- `httpConnectTimeout` (optional, default: 5000ms)
- `httpReadTimeout` (optional, default: 10000ms)
- `httpPoolSize` (optional, default: 20)

**Output:**
- 4 generated files
- YAML config for HTTP client settings
- Profile-specific timeouts (dev/prod)
- Gradle dependencies (implicit via restapi)

**Key Features:**
- RestTemplate bean factory
- Connection pooling configuration
- Timeout management
- HTTP interceptor support

---

### Module 3: Payload Structure

**File:** `payload-structure-integration/SKILL.md`

**Purpose:** Generates standard response envelope and data models

**Generates:**
- RestResponse.java (model)
- Message.java (model)
- Resource.java (model)
- ResponseContext.java (utility)
- PayloadStructureConfiguration.java
- Test classes (4 tests)

**Input Context:**
- `basePackage` (required)
- `appName` (required)
- `apiVersion` (optional)

**Output:**
- 8 generated files
- YAML config for API response structure
- Gradle dependencies (implicit via restapi)

**Key Features:**
- Standard RestResponse envelope
- Message model for errors/warnings
- Resource wrapper for domain objects
- Context injection infrastructure
- Response builder utilities

**Note:** Controllers (Module 7) use this envelope for all responses

---

### Module 4: RestClient (CoreRestApiClient)

**File:** `rest-client-integration/SKILL.md`

**Purpose:** Generates gateway classes for calling downstream microservices

**Generates:**
- Gateway interfaces (one per producer API)
- GatewayImpl classes (one per producer API)
- Client model classes (DTOs from producer specs)
- RestClientConfiguration.java
- Test classes (3+ tests)

**Input Context:**
- `basePackage` (required)
- `appName` (required)
- `producerApis` (optional, array of downstream API specs)
- `httpPoolSize` (optional, default: 20)
- `circuitBreakerEnabled` (optional, default: true)

**Output:**
- Variable number of files (depends on producer APIs)
- YAML config for each producer API base URL
- Profile-specific URLs (dev/prod)
- Gradle dependencies (implicit via restapi)

**Key Features:**
- Gateway pattern for downstream calls
- CoreRestApiClient integration
- Circuit breaker support
- HTTP connection pooling
- Environment-based URL configuration

**Dependencies:** Uses Module 2 (Common Functionalities) RestClient factory

---

### Module 5: Health Check

**File:** `health-check-integration/SKILL.md`

**Purpose:** Adds health check endpoints and downstream health verification

**Generates:**
- HealthIndicator.java
- DownstreamHealthChecker.java
- HealthCheckConfiguration.java
- HealthController.java (endpoints)
- Test classes (3 tests)

**Input Context:**
- `basePackage` (required)
- `appName` (required)
- `healthCheckUrls` (optional, list of downstream health endpoints)
- `healthCheckInterval` (optional, default: 30000ms)
- `healthCheckTimeout` (optional, default: 5000ms)
- `kubernetesEnabled` (optional, default: true)

**Output:**
- 5 generated files
- YAML config for Actuator endpoints
- YAML config for downstream health checks
- Profile-specific settings (dev/prod)
- Gradle dependency: spring-boot-starter-actuator

**Endpoints Generated:**
- `GET /api/health` — Overall health status
- `GET /api/health/live` — Kubernetes liveness probe
- `GET /api/health/ready` — Kubernetes readiness probe

**Key Features:**
- Kubernetes probe support (liveness/readiness)
- Downstream service health checks
- Actuator endpoints configuration
- Custom health indicators

---

### Module 6: Request Validator

**File:** `request-validator-integration/SKILL.md`

**Purpose:** Validates incoming requests against OpenAPI/RAML specifications

**Generates:**
- RequestValidationFilter.java
- SpecificationValidator.java
- ValidationConfiguration.java
- ValidationErrorHandler.java
- SpecCache.java
- Test classes (3 tests)

**Input Context:**
- `basePackage` (required)
- `appName` (required)
- `specFiles` (required, object with consumer and producers)
- `specFormat` (optional, "openapi" or "raml", auto-detected)
- `validationMode` (optional, "local" or "production", default: production)
- `enableLocalSpecCache` (optional, default: true)

**Output:**
- 6 generated files
- YAML config for validation settings
- YAML config for spec file locations
- Profile-specific settings (dev/prod)
- Gradle dependency: swagger-parser or raml-parser

**Key Features:**
- OpenAPI 3.x and RAML 1.0 support
- Local or production spec mode
- Specification caching
- Request validation filtering
- Validation error handling
- Security: details hidden in production

**Note:** Specs must be provided by user; validator ensures compliance

---

## Execution Order (Critical)

The umbrella skill **MUST** call sub-skills in this order:

```
1. Module 7 (Standard REST API) ← FOUNDATION - CALLED FIRST
2. Module 1 (Logging Framework)
3. Module 2 (Common Functionalities)
4. Module 4 (RestClient)
5. Module 3 (Payload Structure)
6. Module 5 (Health Check)
7. Module 6 (Request Validator)
```

**Why this order?**
- Module 7 establishes the Spring Boot application context
- Module 1-2 configure base infrastructure (logging, HTTP clients)
- Module 4 adds gateway support for microservice calls
- Module 3 standardizes response payloads
- Module 5 adds operational monitoring
- Module 6 adds contract validation

---

## No Blocking Dependencies

**Important:** Each sub-skill is independent and does NOT block others. The sequential order above is recommended for clarity, but logically:
- No module requires another to be complete
- All modules can be called in any sequence after Module 7
- Umbrella handles merge conflicts

---

## Registration Instructions

To register each sub-skill in the system:

1. **Standard REST API (Module 7):**
   ```
   Register: org-sdk-integration/standard-rest-api-integration/SKILL.md
   Name: standard-rest-api-integration
   Type: subskill
   Parent: org-sdk-integration
   ```

2. **Logging Framework (Module 1):**
   ```
   Register: org-sdk-integration/logging-framework-integration/SKILL.md
   Name: logging-framework-integration
   Type: subskill
   Parent: org-sdk-integration
   ```

3. **Common Functionalities (Module 2):**
   ```
   Register: org-sdk-integration/common-functionalities-integration/SKILL.md
   Name: common-functionalities-integration
   Type: subskill
   Parent: org-sdk-integration
   ```

4. **Payload Structure (Module 3):**
   ```
   Register: org-sdk-integration/payload-structure-integration/SKILL.md
   Name: payload-structure-integration
   Type: subskill
   Parent: org-sdk-integration
   ```

5. **RestClient (Module 4):**
   ```
   Register: org-sdk-integration/rest-client-integration/SKILL.md
   Name: rest-client-integration
   Type: subskill
   Parent: org-sdk-integration
   ```

6. **Health Check (Module 5):**
   ```
   Register: org-sdk-integration/health-check-integration/SKILL.md
   Name: health-check-integration
   Type: subskill
   Parent: org-sdk-integration
   ```

7. **Request Validator (Module 6):**
   ```
   Register: org-sdk-integration/request-validator-integration/SKILL.md
   Name: request-validator-integration
   Type: subskill
   Parent: org-sdk-integration
   ```

---

## Integration Testing Checklist

After registering all 7 sub-skills:

- [ ] Umbrella skill can call Module 7 first
- [ ] Module 7 returns Application.java and base configuration
- [ ] Umbrella skill can call Modules 1-6 sequentially
- [ ] Each module receives context from umbrella
- [ ] Each module returns correct file bundle
- [ ] YAML files merge without conflicts
- [ ] Gradle dependencies accumulate correctly
- [ ] All files end up in correct package structure
- [ ] Generated code compiles without errors
- [ ] Tests pass (unit tests for each module)

---

## Files Cross-Reference

### Reference Module Files
```
references/sdk-modules/
├── 1-logging-framework.md
├── 2-common-functionalities.md
├── 3-payload-structure.md
├── 4-rest-client.md
├── 5-health.md
├── 6-request-validator.md
├── 7-standard-rest-api.md
└── INTEGRATION-SUMMARY.md
```

### Umbrella Coordination
```
org-sdk-integration/
├── SKILL.md                          ← Orchestrates all 7 sub-skills
├── README.md                         ← Complete implementation guide
├── MODULE-SUBSKILL-TEMPLATE.md       ← Pattern reference
└── SUBSKILLS-INDEX.md                ← This file
```

### Integration with spec-to-springboot
```
SKILL.md
  │
  ├─ Line 23-29:     References to reference files (including org-gradle-files)
  ├─ Line 74-93:     Clarification questions (includes org-sdk-integration choice)
  ├─ Line 97-106:    Reference file reading instructions
  ├─ Line 189-238:   STEP 5 structure (base + SDK integration paths)
  └─ Line 259-301:   Companion Skill section (org-sdk-integration)
```

---

## Next Steps

1. **Register all 7 sub-skills** in the system using instructions above
2. **Test umbrella orchestration** — Call org-sdk-integration from spec-to-springboot
3. **End-to-end testing** — Generate complete project with all 7 modules
4. **Production deployment** — Make org-sdk-integration available to users

---

## Summary Stats

| Aspect | Count |
|---|---|
| **Module Sub-Skills** | 7 |
| **SKILL.md Files** | 7 |
| **Reference Files** | 8 (including INTEGRATION-SUMMARY) |
| **Total Lines (Sub-Skills)** | ~2,800+ |
| **Average per Module** | ~400 lines |
| **Generated Classes per Module** | 4-8 |
| **Test Classes per Module** | 2-4 |

---

## Version Information

- **SDK Version:** 3.2.1
- **Spring Boot:** 3.3.0
- **Java:** 21
- **Status:** Complete - Ready for Registration
- **Date Created:** 2026-05-25
- **Last Updated:** 2026-05-25

---

**All 7 module sub-skills are complete and ready for system registration.** ✅

