---
name: daf
description: DAF service implementation standards. Covers SDK3 logger, response types, no-Lombok rule, thin controllers, gateway layer, AOP with @Around, constructor injection, ErrorCodes enum, canonical import paths, module catalog, and technology versions. Use when generating or reviewing any DAF Java service implementation.
user-invocable: false
---

# DAF Service Implementation Standards

> **Source:** DAF Service Constitution v1.0.0, ratified 2026-06-02
> **Owner:** BUK Platform Engineering
> **Review trigger:** On DAF Gradle Plugin major version bump, or SDK3 BOM major version bump
> **Status:** Reviewed
> Source documents are Restricted — Internal.

These rules apply to every Java class generated or reviewed in a DAF service. They complement the architectural rules in `barclays-buk-standards:api-design`, which covers headers, authorization layers, OpenAPI, and versioning. Do not duplicate content from that skill — reference it instead.

---

## Quick Start

When generating a DAF service, apply every section in order:

1. Add the SDK3 logger to every class (Section 1)
2. Return `Response` from controllers, `RestResponse` from services (Section 2)
3. Write all DTOs by hand — no Lombok (Section 3)
4. Keep controllers thin pass-throughs (Section 4)
5. Put every downstream call behind a gateway interface (Section 5)
6. Use `@Around` for all AOP advice (Section 6)
7. Inject all dependencies via constructor (Section 7)
8. Handle all errors through `ErrorCodes` enum (Section 8)
9. Use only the canonical imports from Section 9
10. Uncomment only the DAF modules you need (Section 10)
11. Pin all technology versions to those in Section 11

---

## 1. SDK3 Logger (NON-NEGOTIABLE)

Every class MUST use the Barclays SDK3 logger. The standard `org.slf4j` API is prohibited — DAF hooks into its own logging infrastructure for structured log correlation.

```java
// CORRECT
import com.barclays.api.bap.bld.lib.logging.Logger;
import com.barclays.api.bap.bld.lib.logging.LoggerSlf4jImpl;

private static final Logger log = new LoggerSlf4jImpl(ClassName.class);
```

| Rule | Detail |
|---|---|
| Field name | MUST be `log` (lowercase) |
| `org.slf4j.Logger` | FORBIDDEN |
| `org.slf4j.LoggerFactory` / `LoggerFactory.getLogger()` | FORBIDDEN |
| `@Slf4j` (Lombok) | FORBIDDEN |

---

## 2. Response Types (NON-NEGOTIABLE)

Controllers and services MUST use DAF SDK3 response wrappers. `ResponseEntity<T>` is prohibited — DAF wraps all responses in a standard envelope.

**Controllers** return `Response`:

```java
import com.barclays.api.bap.bld.lib.common.response.Response;

public Response methodName(DafHeadersContext apiHeadersContext, @RequestBody Request request) {
    return someService.someMethod(request);
}
```

**Services** return `RestResponse` (non-generic — no type parameter):

```java
import com.barclays.api.bap.bld.lib.payload.response.RestResponse;
import com.barclays.api.bap.bld.lib.payload.response.ResponseHttpStatus;

// Success
return RestResponse.assemble().build(ResponseHttpStatus.OK, responseDto);

// Created
return RestResponse.assemble().build(ResponseHttpStatus.CREATED, responseDto);

// Error — always via ErrorCodes (see Section 8)
return ErrorCodes.SOME_ERROR.buildErrorResponse(param);
```

| Location | Return type | Notes |
|---|---|---|
| Controller method | `Response` | Import from `com.barclays.api.bap.bld.lib.common.response` |
| Service method | `RestResponse` | Import from `com.barclays.api.bap.bld.lib.payload.response`; no type parameter |
| Gateway impl | `ResponseEntity<T>` | Permitted only where `RestTemplate.exchange()` / `RestClient` returns it internally |

`ResponseEntity<T>` is FORBIDDEN in controllers and services.

---

## 3. No Lombok (NON-NEGOTIABLE)

Lombok annotations are prohibited due to DAF Jackson compatibility issues. All boilerplate must be hand-written.

| FORBIDDEN | Correct alternative |
|---|---|
| `@Builder` | Hand-written static inner `{Name}Builder` class |
| `@Data` | Hand-written getters/setters |
| `@AllArgsConstructor` | Hand-written constructor |
| `@NoArgsConstructor` | Hand-written no-arg constructor |
| `@Slf4j` | `new LoggerSlf4jImpl(ClassName.class)` |
| `@Value` | Hand-written final fields + constructor |

**DTO builder pattern — use this exact structure:**

```java
public class EligibilityResponse {
    private final String customerId;
    private final boolean eligible;

    private EligibilityResponse(Builder builder) {
        this.customerId = builder.customerId;
        this.eligible = builder.eligible;
    }

    public static Builder builder() { return new Builder(); }
    public String getCustomerId() { return customerId; }
    public boolean isEligible() { return eligible; }

    public static final class Builder {
        private String customerId;
        private boolean eligible;

        public Builder customerId(String customerId) { this.customerId = customerId; return this; }
        public Builder eligible(boolean eligible) { this.eligible = eligible; return this; }
        public EligibilityResponse build() { return new EligibilityResponse(this); }
    }
}
```

---

## 4. Thin Controllers

Controllers are pure pass-throughs. They MUST NOT contain business logic, try/catch blocks, conditional logic, or typed request bodies.

```java
@RestController
public class EligibilityController {

    private static final Logger log = new LoggerSlf4jImpl(EligibilityController.class);
    private final EligibilityService eligibilityService;

    public EligibilityController(EligibilityService eligibilityService) {
        this.eligibilityService = eligibilityService;
    }

    @PostMapping("/eligibility")
    public Response checkEligibility(DafHeadersContext apiHeadersContext,
                                     @RequestBody Request request) {
        log.info("checkEligibility called");
        return eligibilityService.checkEligibility(request);
    }
}
```

| Rule | Requirement |
|---|---|
| First parameter | MUST be `DafHeadersContext apiHeadersContext` (DAF auto-injects) |
| Request body | MUST be `@RequestBody Request request` (generic) — NEVER a typed DTO |
| Business logic | FORBIDDEN — delegate entirely to the service |
| try/catch | FORBIDDEN in controllers |
| Dependency injection | Constructor injection only (see Section 7) |
| `DafHeadersContext` | MUST have `@HeaderContract` and `@HeaderObject` annotations on the class |

---

## 5. Gateway Layer

Every downstream API MUST have a dedicated gateway interface and implementation. Services MUST call gateways — never `RestTemplate` or `RestClient` directly.

```java
// Interface
public interface CustomerEnquiryGateway {
    CustomerData getCustomerData(String customerId);
}

// Implementation
@Component
public class CustomerEnquiryGatewayImpl implements CustomerEnquiryGateway {

    private static final Logger log = new LoggerSlf4jImpl(CustomerEnquiryGatewayImpl.class);
    private final RestClient restClient;

    public CustomerEnquiryGatewayImpl(RestClient restClient) {
        this.restClient = restClient;
    }

    @Override
    public CustomerData getCustomerData(String customerId) {
        log.info("Calling customer enquiry API for: {}", customerId);
        // ... RestClient call
    }
}
```

| Rule | Requirement |
|---|---|
| One gateway per downstream API | Each downstream service gets its own interface + impl pair |
| Services call gateways | Services MUST NOT call `RestTemplate` or `RestClient` directly |
| `ResponseEntity<T>` | Permitted inside gateway impl only, where the HTTP client returns it |

---

## 6. AOP with @Around (NON-NEGOTIABLE)

AOP interceptors MUST use `@Around` with `ProceedingJoinPoint`. `@Before` advice is prohibited — `@Around` enables short-circuiting and return value modification which `@Before` cannot do.

```java
@Aspect
@Component
public class RequestInterceptorAspect {

    @Around("@annotation(com.barclays.daf.api.interceptors.annotations.DafInterceptor)")
    public Object intercept(ProceedingJoinPoint joinPoint) throws Throwable {
        // pre-processing
        Object result = joinPoint.proceed();
        // post-processing
        return result;
    }
}
```

| Rule | Requirement |
|---|---|
| Advice type | `@Around` with `ProceedingJoinPoint` — MANDATORY |
| `@Before` advice | FORBIDDEN |
| Session state | MUST use `DafSessionClient` or `DafSessionManagementService` |
| `ThreadLocal<T>` for session | FORBIDDEN |

---

## 7. Constructor Injection

All dependencies MUST be injected via constructor. `@Autowired` field injection is prohibited.

```java
// CORRECT
@Service
public class EligibilityServiceImpl implements EligibilityService {
    private final CustomerEnquiryGateway customerEnquiryGateway;
    private final EligibilityMapper eligibilityMapper;

    public EligibilityServiceImpl(CustomerEnquiryGateway customerEnquiryGateway,
                                  EligibilityMapper eligibilityMapper) {
        this.customerEnquiryGateway = customerEnquiryGateway;
        this.eligibilityMapper = eligibilityMapper;
    }
}
```

`@Autowired` on fields or setter methods is FORBIDDEN in all classes.

---

## 8. ErrorCodes Enum

Error handling MUST use a standalone `ErrorCodes` enum in `error/ErrorCodes.java`. Services return errors via `ErrorCodes.X.buildErrorResponse(param)` — NEVER throw exceptions to the caller.

```java
package com.barclays.api.{domain}.error;

import com.barclays.api.bap.bld.lib.logging.Logger;
import com.barclays.api.bap.bld.lib.logging.LoggerSlf4jImpl;
import com.barclays.api.bap.bld.lib.payload.response.Message;
import com.barclays.api.bap.bld.lib.payload.response.ResponseHttpStatus;
import com.barclays.api.bap.bld.lib.payload.response.RestResponse;

public enum ErrorCodes {
    ERROR_CALLING_DOWNSTREAM_API("BDDF01", "Failure calling downstream service", "Unable to retrieve data for: XX"),
    GENERAL_ERROR("BDDF99", "A Technical error has occurred", "Sorry, a technical error has occurred, please try again.");

    private static final Logger log = new LoggerSlf4jImpl(ErrorCodes.class);
    private final String code;
    private final String title;
    private final String detail;

    ErrorCodes(String code, String title, String detail) {
        this.code = code;
        this.title = title;
        this.detail = detail;
    }

    public RestResponse buildErrorResponse() {
        log.error("{} {} {}", this.name(), this.code, this.detail);
        return RestResponse.assemble()
                .addErrorMessage(Message.create(this.code, this.title, this.detail))
                .build(ResponseHttpStatus.INTERNAL_SERVER_ERROR);
    }

    public RestResponse buildErrorResponse(String param) {
        String resolvedDetail = this.detail.replace("XX", param != null ? param : "unknown");
        log.error("{} {} {}", this.name(), this.code, resolvedDetail);
        return RestResponse.assemble()
                .addErrorMessage(Message.create(this.code, this.title, resolvedDetail))
                .build(ResponseHttpStatus.INTERNAL_SERVER_ERROR);
    }
}
```

| Rule | Requirement |
|---|---|
| Type | MUST be an enum — never a class, never an inner type |
| Location | `error/ErrorCodes.java` in the service package |
| Methods | MUST implement both `buildErrorResponse()` and `buildErrorResponse(String param)` |
| Usage | Services MUST call `ErrorCodes.X.buildErrorResponse(param)` for all error paths |
| Throwing exceptions | NEVER throw exceptions to the caller — return the error response instead |

The `XX` placeholder in the `detail` string is replaced by the `param` argument. Use `null`-safe replacement as shown above.

---

## 9. Canonical Import Paths

Use exactly these fully-qualified class names. Abbreviated or wrong-package variants cause compile failures.

| Class | Import |
|---|---|
| `Logger` | `com.barclays.api.bap.bld.lib.logging.Logger` |
| `LoggerSlf4jImpl` | `com.barclays.api.bap.bld.lib.logging.LoggerSlf4jImpl` |
| `RestResponse` | `com.barclays.api.bap.bld.lib.payload.response.RestResponse` |
| `Response` | `com.barclays.api.bap.bld.lib.common.response.Response` |
| `Request` | `com.barclays.api.bap.bld.lib.payload.beans.Request` |
| `ResponseHttpStatus` | `com.barclays.api.bap.bld.lib.payload.response.ResponseHttpStatus` |
| `Message` | `com.barclays.api.bap.bld.lib.payload.response.Message` |
| `HeaderContract` | `com.barclays.daf.api.header.annotations.HeaderContract` |
| `HeaderObject` | `com.barclays.daf.api.header.annotations.HeaderObject` |
| `ExperienceApiException` | `com.barclays.daf.exceptions.ExperienceApiException` |

---

## 10. DAF Module Catalog

Modules are declared in `daf-dependencies.gradle`.

**Core modules** — always uncommented:

| Module | Purpose |
|---|---|
| `daf-api-interceptors` | Request/response interceptor pipeline |
| `daf-error-handling` | Standardised error response formatting |
| `daf-exceptions` | Base exception classes (`ExperienceApiException`) |
| `daf-logging` | Structured logging with correlation ID propagation |

**Optional modules** — uncomment only when explicitly needed:

| Module | Purpose |
|---|---|
| `daf-jwt` | JWT token management for TIAA auth |
| `daf-session-client` | Distributed session management (requires `DafSessionManagementService`) |
| `daf-session-common` | Session support classes |
| `daf-authorization` | Role-based authorisation |
| `daf-aem-cache` | AEM content caching |
| `daf-bcag` | Barclays Cryptographic Application Gateway |
| `daf-datasourcerouter` | Database routing |
| `daf-testbedrouter` | Test bed environment routing |

Do not uncomment optional modules speculatively. Only add them when the feature that requires them is being implemented.

---

## 11. Technology Versions

Pin all versions to these values. Do not upgrade without an explicit request.

| Technology | Version |
|---|---|
| Spring Boot | `3.4.5` (via DAF Gradle Plugin) |
| DAF Gradle Plugin (`com.barclays.digital.daf.starter`) | `5.0.1853` |
| SDK3 BOM (`com.barclays.api:sdk3`) | `1.6.001` |
| Java (`sourceCompatibility`) | `21` |
| Groovy (test) | `4.0.24` |
| Spock | `2.4-M1-groovy-4.0` |
| Jackson | `2.15.2` |

---

## 12. Quick Reference: Prohibited vs Correct

| FORBIDDEN | CORRECT |
|---|---|
| `ResponseEntity<T>` return type | `Response` (controller) / `RestResponse` (service) |
| `org.slf4j.LoggerFactory.getLogger()` | `new LoggerSlf4jImpl(ClassName.class)` |
| `@Builder`, `@Data`, `@Slf4j` (Lombok) | Hand-written builders, getters, SDK3 logger |
| `ThreadLocal<T>` for session | `DafSessionClient` / `DafSessionManagementService` |
| `@Before` AOP advice | `@Around` with `ProceedingJoinPoint` |
| `@RequestBody TypedDto dto` in controller | `@RequestBody Request request` |
| Typed service return `SomeDto method()` | `RestResponse method(Request request)` |
| `@Autowired` field injection | Constructor injection |
| `ErrorCodes` as a class | `ErrorCodes` as a standalone enum |
| Throwing exceptions to callers | `return ErrorCodes.X.buildErrorResponse(param)` |

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] Every class uses `new LoggerSlf4jImpl(ClassName.class)` with field name `log` — no `@Slf4j`, no `org.slf4j`
- [ ] Controllers return `Response`; services return `RestResponse`; no `ResponseEntity<T>` outside gateway impls
- [ ] No Lombok annotations anywhere — all DTOs use the hand-written static inner `Builder` pattern
- [ ] Controllers have `DafHeadersContext` as first param and `@RequestBody Request request` — no typed DTOs, no try/catch
- [ ] Every downstream API has a dedicated gateway interface + impl; services never call `RestTemplate` directly
- [ ] All AOP uses `@Around` with `ProceedingJoinPoint`; no `@Before`; no `ThreadLocal` for session
- [ ] All dependencies injected via constructor; no `@Autowired` field injection
- [ ] `ErrorCodes` is a standalone enum in `error/ErrorCodes.java` with both `buildErrorResponse()` overloads; no exceptions thrown to callers
- [ ] All imports match the canonical paths table exactly
- [ ] Only core DAF modules are always-on; optional modules only added when needed
- [ ] Technology versions match Section 11 exactly

---

## Areas for Specialist Extension

This skill covers the DAF service implementation baseline. The following areas need extension by the relevant teams:

- **API squad leads** — add domain-specific `ErrorCodes` entries and error code prefix conventions per domain
- **Platform Engineering** — add gateway circuit-breaker configuration patterns when DAF module support is confirmed
- **Security team** — extend Section 6 (AOP) with BOLA/IDOR check patterns for the `@Around` interceptor
