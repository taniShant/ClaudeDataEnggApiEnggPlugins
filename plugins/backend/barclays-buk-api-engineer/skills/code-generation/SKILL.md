---
name: code-generation
description: Spring Boot 3 + Java 21 code generation patterns for models, controllers, services, gateways, and tests from OpenAPI 3.x specifications
color: green
---

> **Source:** Barclays BUK DAF SDK3 implementation patterns and Spring Boot 3 best practices.
> **Owner:** BUK
> **Review trigger:** On DAF SDK3 major/minor release or Spring Boot 3 major version bump.
> **Status:** Reviewed

# Skill: Code Generation

## Critical SDK3 Integration Rules (MANDATORY)

**All generated code must follow these rules — they are NON-NEGOTIABLE:**

1. **LogFactory Mandatory** — Use `LogFactory.getLogger(this.getClass())` in all services and gateways
   - **FORBIDDEN:** `@Slf4j`, `LoggerFactory.getLogger()`, or `log4j` direct imports
   - All logging goes through SDK3 LogFactory

2. **PerfLogger Required in Gateways Only** — All gateway/downstream API calls MUST be wrapped in try-finally blocks
   ```java
   private static final PerfLogger PERFORMANCE_LOGGER = LogFactory.getPerfLogger(this.getClass());
   
   PerfEvent perfEvent = PERFORMANCE_LOGGER.start("payment-service-call");
   try {
       result = restApiClient.call(...);
   } finally {
       perfEvent.stop();  // Always executes
   }
   ```
   **Note:** Controllers do NOT use PerfLogger — only gateways that call downstream APIs

3. **No Jakarta Validation Annotations in DTOs** — Models are plain POJOs
   - **FORBIDDEN:** `@NotNull`, `@Valid`, `@Email`, `@Pattern`, `@Size`, `@Min`, `@Max`
   - Request validation happens via RequestValidationFilter (app-wide, not per-DTO)

4. **Controller Responses — RestResponse.assemble().build() MANDATORY**
   - **MANDATORY:** Use `RestResponse.assemble().build(ResponseHttpStatus.STATUS, data)` for ALL controller responses
   - ResponseHttpStatus: `OK` (200), `CREATED` (201), `NO_CONTENT` (204), `BAD_REQUEST` (400), `NOT_FOUND` (404), `INTERNAL_SERVER_ERROR` (500)
   - All responses automatically wrapped with metadata and correlation ID by SDK3
   - Example:
     ```java
     return RestResponse.assemble().build(ResponseHttpStatus.OK, result);
     ```

5. **RestApiClient for Gateway Calls (NOT RestTemplate or RestClient)**
   - **FORBIDDEN:** RestTemplate, RestClient fluent API, or other HTTP clients
   - **MANDATORY:** Use `RestApiClient.call(HttpMethod, URI, requestBody, headers)` for all downstream API calls
   - RestApiClient is auto-wired by SDK3 and handles connection pooling, mesh tokens, and tracing

6. **Health Check Endpoints** — SDK3 (`bap-bld-lib-health` transitive module) auto-provides `/health` and `/actuator/health`
   - **DO NOT generate `HealthController` or `HealthCheckController`** — SDK3 handles these automatically
   - Endpoints are active as soon as `ApplicationConfig` declares the `ApiInitializer` bean

7. **Only ApplicationConfig.java in config/ package**
   - **MANDATORY:** Generate ONLY `ApplicationConfig.java` with ExternalApiInitializer (or InternalApiInitializer) + SecureFields beans
   - **FORBIDDEN:** SecurityConfig, RestClientConfig, MeshConnectorConfig, HealthCheckConfig, SdkFilterConfig, or any other configuration classes
   - SDK3 auto-configures everything else

## When to Use This Skill

Use this skill when:
- Generating Java POJO models from specification schemas
- Creating Spring Boot 3 REST controllers from endpoints
- Implementing service layer classes
- Creating gateway/client classes for downstream APIs (with PerfLogger wrapping)
- Generating unit and integration tests

## Quick Start

### Generation Order

1. **Models First** (request/response DTOs from spec)
2. **Controllers** (REST endpoints)
3. **Services** (business logic interfaces)
4. **Gateways** (downstream API clients)
5. **Tests** (controller, service, gateway tests)
6. **Configuration** (Security, RestClient, exception handlers)

### Model Generation (Java Records — No Lombok, No Validation Annotations)

```java
// ✅ CORRECT: Java Record — no Lombok, immutable, Java 21 standard
public record UserResponse(
    Integer id,
    String email,
    String name
) {}

public record CreateUserRequest(
    String name,
    String email,
    Integer age
) {}
```

**Note:** DTOs are Java Records — immutable plain data carriers. Validation is handled app-wide by RequestValidationFilter against the OpenAPI spec. No Lombok annotations (`@Data`, `@Builder`, etc.) on DTOs. No jakarta.validation annotations.

**Accessor syntax:** Record components are accessed via `user.id()`, `user.email()` — NOT `user.getId()`.

### Controller Generation (SDK3 Style)

```java
import com.barclays.api.bap.bld.lib.common.response.Response;
import com.barclays.api.bap.bld.lib.common.response.RestResponse;
import com.barclays.api.bap.bld.lib.common.response.ResponseHttpStatus;
import com.barclays.api.bap.bld.lib.logging.LogFactory;
import com.barclays.api.bap.bld.lib.logging.Logger;
import {basePackage}.context.ApiContext;

@RestController
@RequestMapping("/api/v1/users")
@RequiredArgsConstructor
public class UserController {
    private final UserService userService;
    private static final Logger LOGGER = LogFactory.getLogger(UserController.class);
    
    @PostMapping
    public Response createUser(ApiContext apiContext, @RequestBody User request) {
        LOGGER.info("Creating user from request");
        User created = userService.create(apiContext, request);
        return RestResponse.assemble().build(ResponseHttpStatus.CREATED, created);
    }
    
    @GetMapping("/{id}")
    public Response getUser(ApiContext apiContext, @PathVariable Integer id) {
        LOGGER.info("Fetching user with id: {}", id);
        User user = userService.findById(apiContext, id);
        return RestResponse.assemble().build(ResponseHttpStatus.OK, user);
    }
}
```

**Key patterns:**
- `ApiContext apiContext` MUST be the first parameter on every controller method — Spring resolves it automatically
- Use `RestResponse.assemble().build(ResponseHttpStatus.STATUS, data)` for ALL responses
- ResponseHttpStatus: `OK` (200), `CREATED` (201), `NO_CONTENT` (204), `BAD_REQUEST` (400), etc.
- Use LogFactory.getLogger() instead of PerfLogger (PerfLogger is for gateways/downstream calls only)
- All responses automatically wrapped with metadata and correlation ID
- Import: `com.barclays.api.bap.bld.lib.common.response.RestResponse`
- Import: `com.barclays.api.bap.bld.lib.common.response.ResponseHttpStatus`
- Import: `com.barclays.api.bap.bld.lib.common.response.Response`
- Import: `{basePackage}.context.ApiContext`

### Service Layer

```java
import {basePackage}.context.ApiContext;

public interface UserService {
    User create(ApiContext apiContext, User user);
    User findById(ApiContext apiContext, Integer id);
}

@Service
@RequiredArgsConstructor
public class UserServiceImpl implements UserService {
    private final UserRepository repository;
    private static final Logger LOGGER = LogFactory.getLogger(UserServiceImpl.class);
    
    @Override
    public User create(ApiContext apiContext, User user) {
        LOGGER.info("Creating user: {}", user.name());  // record accessor — no "get" prefix
        // Implementation — pass apiContext to gateway calls if needed
    }

    @Override
    public User findById(ApiContext apiContext, Integer id) {
        LOGGER.info("Fetching user with id: {}", id);
        // Implementation
    }
}
```

### Gateway Pattern (Downstream APIs with Mandatory PerfLogger + RestApiClient + ApiContext + Spring Retry)

```java
import com.barclays.api.bap.bld.lib.logging.LogFactory;
import com.barclays.api.bap.bld.lib.logging.Logger;
import com.barclays.api.bap.bld.lib.logging.PerfLogger;
import com.barclays.api.bap.bld.lib.logging.PerfEvent;
import com.barclays.api.bap.bld.lib.payload.exceptions.ApiException;
import com.barclays.api.bap.bld.lib.restclient.RestApiClient;
import com.barclays.api.bap.bld.lib.restclient.http.RestClientHttpMethod;
import com.barclays.api.bap.bld.lib.common.response.Response;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.retry.annotation.Backoff;
import org.springframework.retry.annotation.Recover;
import org.springframework.retry.annotation.Retryable;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.util.UriComponentsBuilder;
import {basePackage}.context.ApiContext;
import java.net.URI;
import java.util.HashMap;

public interface PaymentGateway {
    PaymentResponse processPayment(ApiContext apiContext, PaymentRequest request);
}

@Component
public class PaymentGatewayImpl implements PaymentGateway {
    private static final Logger LOGGER = LogFactory.getLogger(PaymentGatewayImpl.class);
    private static final PerfLogger PERFORMANCE_LOGGER = LogFactory.getPerfLogger(PaymentGatewayImpl.class);

    @Value("${downstream.payment.base-url:https://payment-api.internal}")
    private String baseUrl;

    private final RestApiClient restApiClient;

    public PaymentGatewayImpl(RestApiClient restApiClient) {
        this.restApiClient = restApiClient;
    }

    @Override
    @Retryable(
        retryFor = GatewayException.class,
        maxAttemptsExpression = "${retry.gateway.max-attempts:3}",
        backoff = @Backoff(
            delayExpression = "${retry.gateway.delay:500}",
            multiplierExpression = "${retry.gateway.multiplier:2}",
            random = true
        )
    )
    public PaymentResponse processPayment(ApiContext apiContext, PaymentRequest request) {
        LOGGER.info("Calling external Payment API");
        PerfEvent perfEvent = PERFORMANCE_LOGGER.start("Invoking Payment API Call");
        HttpHeaders httpHeaders = assembleHeaders(apiContext);
        URI uri = UriComponentsBuilder.fromUriString(baseUrl + "/v1/process")
                .build()
                .toUri();
        try {
            PaymentResponse response = restApiClient.call(
                    RestClientHttpMethod.POST,
                    uri,
                    request,
                    httpHeaders,
                    PaymentResponse.class
            ).getBody();
            LOGGER.debug("Payment API call successful");
            return response;
        } catch (ApiException apiException) {
            LOGGER.error("Payment API error [status={}]: {}",
                    apiException.getStatus(), apiException.getMessage(), apiException);
            if (isRetryable(apiException)) {
                throw new GatewayException(
                        "Retryable error calling Payment API: " + apiException.getMessage(),
                        apiException.getStatus() != null
                                ? apiException.getStatus() : HttpStatus.INTERNAL_SERVER_ERROR,
                        apiException);
            }
            throw new GatewayException(
                    "Non-retryable error calling Payment API: " + apiException.getMessage(),
                    apiException.getStatus() != null
                            ? apiException.getStatus() : HttpStatus.INTERNAL_SERVER_ERROR,
                    apiException);
        } catch (Exception e) {
            LOGGER.error("Unexpected error calling Payment API at {}: {}", uri, e.getMessage(), e);
            throw new GatewayException(
                    "Unexpected error calling Payment API: " + e.getMessage(),
                    HttpStatus.INTERNAL_SERVER_ERROR, e);
        } finally {
            LOGGER.debug("End - Gateway call for processPayment");
            perfEvent.stop();  // MANDATORY: Always stops performance timer
        }
    }

    @Recover
    public PaymentResponse recoverProcessPayment(
            GatewayException ex, ApiContext apiContext, PaymentRequest request) {
        LOGGER.error("Payment API exhausted all retries. Last error: {}", ex.getMessage(), ex);
        throw ex;
    }

    private boolean isRetryable(ApiException e) {
        if (e.getStatus() == null) {
            return true;
        }
        int code = e.getStatus().value();
        return code == 502 || code == 503 || code == 504 || code == 429;
    }

    private HttpHeaders assembleHeaders(ApiContext apiContext) {
        HttpHeaders httpHeaders = new HttpHeaders();
        httpHeaders.add("Correlation-ID", apiContext.getCorrelationId());
        httpHeaders.add("Authorization", apiContext.getAuthorization());
        return httpHeaders;
    }
}
```

**MANDATORY Rules:**
1. Every downstream API call MUST be wrapped in try-finally with PerfLogger
2. Use `RestApiClient.call(HttpMethod, URI, requestBody, headers)` instead of RestTemplate
3. Always call `perfEvent.stop()` in finally block
4. Use LogFactory for both Logger and PerfLogger
5. Constructor injection only (never @Autowired)
6. Use `ApiContext apiContext` instead of `Map<String, String> headerMap` — assemble headers via `assembleHeaders()` private method
7. Use `UriComponentsBuilder` for URI construction — NEVER `URI.create()`
8. Every gateway method MUST carry `@Retryable` — retries on `GatewayException` for transient failures (502, 503, 504, 429)
9. Every `@Retryable` method MUST have a paired `@Recover` method with the same return type and parameters prefixed by the exception type
10. Catch `ApiException` (SDK3) before `Exception` to distinguish retryable vs non-retryable HTTP status codes
11. `@EnableRetry` is declared on `ApplicationConfig` (via template) — do NOT add it to individual gateway classes

## Core Concepts

### Annotations Used (APPROVED)

- `@RequiredArgsConstructor` (Lombok) — Constructor injection on controllers/services/gateways (non-DTO classes only)
- `@Data`, `@NoArgsConstructor`, `@AllArgsConstructor` (Lombok) — **JPA entities ONLY** — never on DTO records
- `@RestController` - Spring MVC REST endpoint
- `@RequestMapping` - URL mapping
- `@PostMapping`, `@GetMapping`, etc. - HTTP method mapping
- `@RequestBody` - Parse request body
- `@RequestContext` - SDK3 header context injection
- `@Service` - Service layer component
- `@Component` - Generic Spring component
- `@Repository` - Data access layer
- `@JsonProperty` — On record components when JSON key differs from field name
- `@Retryable` (Spring Retry) — On every gateway method to enable automatic retry for transient failures
- `@Recover` (Spring Retry) — Paired fallback method for each `@Retryable` method; same return type, exception as first param
- `@Backoff` (Spring Retry) — Configures exponential backoff strategy inside `@Retryable`
- `@EnableRetry` (Spring Retry) — On `ApplicationConfig` only; activates retry proxy infrastructure for the whole application

### Annotations FORBIDDEN on DTOs

- ❌ `@Data`, `@Builder`, `@NoArgsConstructor`, `@AllArgsConstructor` on DTO classes — **use Java Records instead**
- ❌ `@Valid`, `@NotNull`, `@NotBlank`, `@Email`, `@Pattern`, `@Size`, `@Min`, `@Max` - Validation constraints (validation is app-wide via RequestValidationFilter)
- ❌ `@Slf4j` - Use LogFactory.getLogger() instead
- ❌ `javax.validation.*` or `jakarta.validation.*` imports

### Package Structure

```
com.example.api/
├── context/             # Request context (ApiContext extends InternalRequestContext)
├── controller/          # REST endpoints
├── service/
│   └── impl/            # Service implementations
├── gateway/
│   └── impl/            # Gateway implementations
├── model/
│   ├── request/         # Request DTOs
│   ├── response/        # Response DTOs
│   ├── client/          # Downstream API DTOs
│   └── entity/          # JPA entities (if DB)
├── repository/          # Data access (if DB)
├── exception/           # Exception classes
└── config/              # Configuration classes
```

### Validation

Standard Spring validation annotations:
- `@NotNull` - Required, allows empty string
- `@NotBlank` - Required, non-empty string
- `@Email` - Email format
- `@Min(0)` - Minimum value
- `@Max(100)` - Maximum value
- `@Pattern` - Regex pattern

### Exception Handling

```java
@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handle(MethodArgumentNotValidException ex) {
        // Return error response
    }
}
```

## Hexagonal Layer Contracts

All generated code must enforce hexagonal (port-and-adapters) layer boundaries. The full layer model and dependency rules are defined in `barclays-buk-api-engineer:project-structure`. The following rules summarise the constraints that apply at code generation time.

### Dependency direction (strict)

```
Controller → Service interface
Service impl → Gateway interface
Gateway impl → external system
```

No layer may skip or bypass an adjacent layer. No layer may depend on a layer below its direct neighbour.

### Anti-pattern: controller bypassing service, importing gateway impl

```java
// WRONG — controller imports a gateway impl class directly
import com.barclays.api.payments.gateway.impl.CustomerEnquiryGatewayImpl;

@RestController
public class CustomerController {
    private final CustomerEnquiryGatewayImpl gatewayImpl;  // violation
```

```java
// CORRECT — controller depends on service interface only
import com.barclays.api.payments.service.CustomerEnquiryService;

@RestController
public class CustomerController {
    private final CustomerEnquiryService customerEnquiryService;  // correct
```

### Anti-pattern: service instantiating concrete gateway adapter

```java
// WRONG — service creates a concrete gateway adapter inline
public class CustomerEnquiryServiceImpl implements CustomerEnquiryService {
    private final CustomerEnquiryGateway gateway = new CustomerEnquiryGatewayImpl(restTemplate);  // violation
```

```java
// CORRECT — service accepts gateway interface via constructor injection
public class CustomerEnquiryServiceImpl implements CustomerEnquiryService {
    private final CustomerEnquiryGateway customerEnquiryGateway;

    public CustomerEnquiryServiceImpl(CustomerEnquiryGateway customerEnquiryGateway) {
        this.customerEnquiryGateway = customerEnquiryGateway;
    }
```

These violations are checked at validation time by `daf-validation-agent` Red Flag #20 and `project-generation-agent` Phase 5b.

---

## Reference Documentation

- **code-generation-rules.md**: Detailed generation rules for all components
- **java-type-mapping.md**: Specification type to Java type mapping
- **spring-patterns.md**: Spring Boot 3 design patterns

## Advanced Topics

- **generation-validation.md**: Validating generated code
- **edge-cases.md**: Complex scenarios (circular refs, inheritance, etc.)

## Lessons Learned

- **generated-project-patterns.md**: Real project examples
- **quick-reference.md**: Common generation patterns

---

See `references/code-generation/` (reference/ and advanced/ subdirectories) for detailed documentation.

## Source Attribution

**Primary sources:**
- Barclays DAF SDK3 BOM 1.6.001 — canonical import paths for `LoggerSlf4jImpl`, `RestResponse`, `Request`, `Response`, `ResponseHttpStatus`
- DAF template repository (`git@app.gitlab.barcapint.com:vishal.khare1/daf-template.git`) — reference implementation of controller, service, gateway, and aspect patterns
- Barclays DAF plugin documentation — `@HeaderContract`, `@HeaderObject`, `DafSessionClient` API

**Training knowledge applied:**
- Spring Boot 3 / Java 21 patterns: constructor injection, `@RestController`, `@Service`, `@Component`
- Spring AOP: `@Aspect`, `@Around`, `ProceedingJoinPoint` pattern
- Spring Data: `CrudRepository` interface conventions
- Hexagonal architecture: port/adapter layer separation rules

**Known limitations:**
- Import paths are pinned to SDK3 BOM 1.6.001; a BOM upgrade may change canonical package locations — always re-verify against the domain-reference SKILL.md version table
- Code patterns reflect the DAF template as of 2026-07-17; template changes after that date are not automatically reflected here

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] Are all request/response DTOs generated as Java Records (`public record Foo(...){}`) — NOT Lombok POJOs?
- [ ] Is Lombok (`@Data`, `@Builder`, `@NoArgsConstructor`, `@AllArgsConstructor`) used ONLY on JPA entities, never on DTOs?
- [ ] Do all code references to DTO fields use record accessor syntax (`request.name()`, `response.id()`) — NOT getter syntax (`request.getName()`)?
- [ ] Are DTOs free of jakarta.validation annotations (`@NotNull`, `@Valid`, etc.)?
- [ ] Does the generated code use LogFactory.getLogger() (never @Slf4j or LoggerFactory directly)?
- [ ] Are all gateway downstream calls wrapped in PerfLogger try-finally blocks?
- [ ] Do controllers return RestResponse.assemble().build() and never ResponseEntity?
- [ ] Are all HTTP calls made via RestApiClient (never RestTemplate, WebClient, or RestClient)?
- [ ] Does ApplicationConfig.java declare only the ApiInitializer and SecureFields beans — no other config classes?
- [ ] Are hexagonal layer boundary rules respected (controller → service interface, service → gateway interface)?
- [ ] Does every `*GatewayImpl` method carry `@Retryable` with `retryFor = GatewayException.class`?
- [ ] Does every `@Retryable` gateway method have a paired `@Recover` method with matching signature (exception first)?
- [ ] Is `@EnableRetry` present on `ApplicationConfig` (via template)?
- [ ] Are Spring Retry imports (`org.springframework.retry.annotation.*`) present in all gateway impl files?
