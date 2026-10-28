---
name: sdk-integration-guide
description: Barclays SDK3 integration — 9 modules, API initialization, controllers, RestClient, filters, request contexts
color: purple
---

> **Source:** Barclays SDK3 integration guide — 9 modules, API initialisation, controllers, RestClient, filters, request contexts.
> **Owner:** BUK
> **Review trigger:** On SDK3 module catalogue update or new integration pattern approved by the platform team.
> **Status:** Reviewed

# Skill: SDK Integration Guide — Barclays SDK3 (Production Patterns)

## When to Use This Skill

Use this skill when:
- Generating controllers that use SDK patterns
- Implementing gateways with RestClient
- Configuring API initialization (external vs. internal)
- Generating configuration classes for SDK integration
- Understanding SDK filter hierarchy and request context injection
- Implementing request/response handling per Barclays standard

## Quick Start

Apply SDK3 patterns to generated code:

1. Controllers: Use `Request<T>` / `Response<T>` wrappers with `@RequestContext`
2. Gateways: Wrap all downstream calls with `PerfLogger.start()` / `perfEvent.stop()`
3. Logging: Use `LogFactory.getLogger(Class)` — never `@Slf4j`
4. Config: Import `bap-bld-lib-restapi` in `build.gradle`

---

## Critical Rules — MANDATORY

**1. SDK3 is MANDATORY for all generated projects**
   - Embedded in `build.gradle` via `implementation 'com.barclays.api:bap-bld-lib-restapi'`
   - Provides automatic filters, request context resolution, response formatting
   - Generators MUST use SDK patterns, not vanilla Spring

**2. PerfLogger MANDATORY for all downstream API calls**
   - All gateway methods wrap downstream calls in try-finally blocks
   - PerfLogger.start() before call, PerfLogger.stop() in finally
   - Performance timing automatically recorded for SLA tracking

**3. LogFactory MANDATORY, @Slf4j FORBIDDEN**
   - Use: `LogFactory.getLogger(Class)` in services, gateways, controllers
   - Forbidden: `@Slf4j`, `LoggerFactory`, direct log4j imports
   - All logging goes through SDK3 LogFactory

**4. Request/Response Abstraction MANDATORY**
   - Controllers use SDK3 Request<T> / Response<T> wrappers
   - RequestContext injected via @RequestContext parameter
   - Responses wrapped in RestResponse or Resource<T>

**5. No Validation Annotations in DTOs**
   - DTOs are plain POJOs (no @Valid, @NotNull, @Email, etc.)
   - Validation is app-wide via RequestValidationFilter
   - Validation runs against OpenAPI 3.x spec

**6. Mesh Token & Eureka MANDATORY for production**
   - ServiceMeshRequestInterceptor injects X-MeshToken header
   - EurekaJWTAuthRequestDecorator handles JWT auth with Eureka
   - Properties: eureka.meshToken, eureka.vinzServiceId, eureka.client.enabled

---

## SDK3 Architecture: 9 Modules

| Module | Version | Purpose | Auto-included |
|--------|---------|---------|---|
| **bap-bld-lib-restapi** | 1.5 | Main entry point — REST API framework | YES (import this) |
| **bap-bld-lib-common** | 1.5 | Interfaces: Request, Response, handlers | YES (transitive) |
| **bap-bld-lib-payload** | 1.5 | Default Request/Response impls, contexts | YES (transitive) |
| **bap-bld-lib-logging** | 1.4 | Log4j2 + SLF4j, filters, context | YES (transitive) |
| **bap-bld-lib-restclient** | 1.5 | REST client with pooling, downstream calls | YES (transitive) |
| **bap-bld-lib-health** | 1.6 | Health checks, metrics, actuator | YES (transitive) |
| **bap-bld-lib-request-validator** | 1.3 | OAS 3.x request validation | NO (add if needed) |
| **bap-bld-lib-meshconnector** | 1.6 | Eureka + service mesh discovery | NO (add if needed) |
| **bap-bld-lib-kotlin-int-test-gradle-plugin** | 1.5 | Karate BDD testing plugin | NO (add if needed) |

**Import strategy:** All generated projects import only `bap-bld-lib-restapi` — this pulls 6 transitive modules automatically.

---

## 1. API Initialization & SecureFields — MANDATORY (ApplicationConfig)

**Every generated project MUST have a single ApplicationConfig bean.** This consolidates API initialization (Internal or External) and SecureFields configuration for sensitive data masking.

**File:** `src/main/java/{basePackage}/config/ApplicationConfig.java`

```java
package {basePackage}.config;

import com.barclays.api.bap.bld.lib.logging.beans.SecureFields;
import com.barclays.api.bap.bld.lib.restapi.bootstrap.ExternalApiInitializer;
// OR use InternalApiInitializer for internal APIs
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class ApplicationConfig {

    // Choose ONE: ExternalApiInitializer (customer-facing) or InternalApiInitializer (internal)
    @Bean
    public ExternalApiInitializer externalApiInitializer() {
        return new ExternalApiInitializer();
    }

    @Bean
    public SecureFields secureFields() {
        SecureFields secureFields = new SecureFields();
        // NOLOG: fields excluded completely from logs
        secureFields.addNoLogSecureField("Authorization");
        secureFields.addNoLogSecureField("password");
        // MASK: fields replaced with asterisks
        secureFields.addMaskSecureField("token", "*");
        secureFields.addMaskSecureField("accountNumber", "*");
        secureFields.addMaskSecureField("email", "*");
        return secureFields;
    }
}
```

### API Type Selection

- **ExternalApiInitializer**: Use for customer-facing / public APIs
  - Sets up 3 default SDK filters: exceptionFilter, performanceLoggingFilter, requestResponseLoggingFilter
  - Does NOT mandate Correlation-ID
  - Optional: supports `x-fapiinteraction-id` header for external tracing

- **InternalApiInitializer**: Use for organization-internal APIs
  - Registers `mandatoryHeaderValidationFilter` — validates `Correlation-ID` header present
  - Registers `internalApiLoggingContextFilter` — adds Correlation-ID to MDC for tracing
  - Sets up all 3 default SDK filters: exceptionFilter, performanceLoggingFilter, requestResponseLoggingFilter

---

## 2. Filter Hierarchy & Precedence

SDK defines a **strict filter precedence chain.** Do NOT deviate from this.

```
Precedence     Layer         Usage
────────────────────────────────────────────────────────────
HIGHEST        0             ExceptionFilter (SDK reserved)
               <50           Security filters (JWT, OAuth, etc.)
               50-100        SDK filters (logging, context, perf)
               >100          Application filters (custom business logic)
LOWEST         ~999          Last resort
```

**Example: Adding a Security Filter (must run BEFORE SDK)**

```java
@Bean
@Order(Ordered.HIGHEST_PRECEDENCE + 10)  // Runs before SDK (50-100)
public Filter securityFilter() {
    return new SecurityFilter();
}
```

**Example: Adding Custom Application Filter (runs AFTER SDK)**

```java
@Bean
public FilterRegistrationBean customApplicationFilter() {
    FilterRegistrationBean bean = new FilterRegistrationBean();
    bean.setFilter(new MyCustomFilter());
    bean.setOrder(Ordered.HIGHEST_PRECEDENCE + 55);  // SDK will adjust this down if needed
    return bean;
}
```

---

## 3. Request Context Injection (MANDATORY Pattern)

SDK provides automatic Spring argument injection for RequestContext subclasses. Use this in ALL controller methods.

### InternalRequestContext

For internal APIs — provides `getCorrelationId()`:

**Controller example:**

```java
@RestController
@RequestMapping("/api/v1/resources")
@RequiredArgsConstructor
public class ResourceController {
    private static final Logger LOGGER = LogFactory.getLogger(ResourceController.class);
    
    private final ResourceService resourceService;
    
    @GetMapping("/{id}")
    public Response findResource(
        @PathVariable String id,
        InternalRequestContext context) {
        
        String correlationId = context.getCorrelationId();
        LOGGER.info("Finding resource {} with correlation-id: {}", id, correlationId);
        
        // ... business logic
        return RestResponse.assemble()
            .build(ResponseHttpStatus.OK, resourceService.findById(id));
    }
}
```

### ExternalRequestContext

For external APIs — provides `getScenarioId()`, `getClientId()`:

```java
@GetMapping("/{id}")
public Response findResource(
    @PathVariable String id,
    ExternalRequestContext context) {
    
    String clientId = context.get("x-client-id");
    String scenarioId = context.get("X-Scenario");
    
    // ... business logic
}
```

### ApiContext (MANDATORY — Standard Request Context for ALL Generated Projects)

All generated projects MUST use `ApiContext extends InternalRequestContext`. It carries HTTP headers and query parameters through the Controller → Service → Gateway call chain.

**File:** `src/main/java/{basePackage}/context/ApiContext.java`

```java
package {basePackage}.context;

import com.barclays.api.bap.bld.lib.payload.request.InternalRequestContext;
import org.springframework.web.context.request.WebRequest;

import java.util.HashMap;
import java.util.Map;

public class ApiContext extends InternalRequestContext {

    private WebRequest webRequest;

    public ApiContext(WebRequest request) {
        super(request);
        this.webRequest = request;
    }

    @Override
    public String getCorrelationId() {
        return get("Correlation-ID");
    }

    public String getAuthorization() {
        return get("authorization");
    }

    public String getHeader(String key) {
        return super.get(key);
    }

    public Map<String, String> getHeaders() {
        Map<String, String> headers = new HashMap<>();
        this.webRequest.getHeaderNames()
                .forEachRemaining(key -> headers.put(key, this.webRequest.getHeader(key)));
        return headers;
    }

    public String getParameter(String paramName) {
        return this.webRequest.getParameter(paramName);
    }

    public String[] getParameterValues(String paramName) {
        return this.webRequest.getParameterValues(paramName);
    }

    public Map<String, String[]> getParameterMap() {
        return this.webRequest.getParameterMap();
    }
}
```

**Flow — ApiContext propagates through all layers:**

```
Controller (Spring injects ApiContext) → Service (receives ApiContext) → Gateway (uses ApiContext to assemble headers)
```

**Controller** — Spring resolves `ApiContext` automatically as a method parameter:
```java
@PostMapping("/queries")
public Response queryHistory(ApiContext apiContext, @RequestBody HistoryRequest request) {
    return RestResponse.assemble().build(ResponseHttpStatus.CREATED,
            historyService.queryHistory(apiContext, request));
}
```

**Service** — receives and passes ApiContext to gateway:
```java
@Override
public HistoryResponse queryHistory(ApiContext apiContext, HistoryRequest request) {
    return historyGateway.fetchHistory(apiContext, request);
}
```

**Gateway** — uses ApiContext to assemble downstream headers:
```java
@Override
public HistoryResponse fetchHistory(ApiContext apiContext, HistoryRequest request) {
    HttpHeaders httpHeaders = assembleHeaders(apiContext);
    // ... restApiClient.call(...)
}

private HttpHeaders assembleHeaders(ApiContext apiContext) {
    HttpHeaders httpHeaders = new HttpHeaders();
    httpHeaders.add("Correlation-ID", apiContext.getCorrelationId());
    httpHeaders.add("Authorization", apiContext.getAuthorization());
    return httpHeaders;
}
```

---

## 4. Controller Pattern — SDK Response Format

Controllers MUST use `RestResponse.assemble()` for all responses. SDK handles wrapping in Barclays standard format.

**CORRECT (using SDK with ApiContext):**

```java
import {basePackage}.context.ApiContext;

@RestController
@RequestMapping("/api/v1/customers")
@RequiredArgsConstructor
public class CustomerController {
    private final CustomerService customerService;
    
    @PostMapping
    public Response createCustomer(ApiContext apiContext, @RequestBody CreateCustomerRequest req) {
        Customer created = customerService.create(apiContext, req);
        return RestResponse.assemble()
            .build(ResponseHttpStatus.CREATED, created);
    }
    
    @GetMapping("/{id}")
    public Response getCustomer(ApiContext apiContext, @PathVariable String id) {
        Customer found = customerService.findById(apiContext, id);
        return RestResponse.assemble()
            .build(ResponseHttpStatus.OK, found);
    }
    
    @PutMapping("/{id}")
    public Response updateCustomer(
        ApiContext apiContext,
        @PathVariable String id,
        @RequestBody UpdateCustomerRequest req) {
        Customer updated = customerService.update(apiContext, id, req);
        return RestResponse.assemble()
            .build(ResponseHttpStatus.OK, updated);
    }
}
```

**Response format (auto-wrapped by SDK):**

```json
{
  "response": {
    "payload": { "id": "123", "name": "John Doe" },
    "meta": { "timestamp": "2026-06-16T10:30:00Z", "recordCount": 1 },
    "status": {
      "code": "SUCCESS",
      "severity": "INFO"
    }
  }
}
```

---

## 5. Service Layer Pattern

Services are plain POJO layers — no SDK dependency. Implement business logic here.

```java
import {basePackage}.context.ApiContext;

public interface CustomerService {
    Customer create(ApiContext apiContext, CreateCustomerRequest req);
    Customer findById(ApiContext apiContext, String id);
    Customer update(ApiContext apiContext, String id, UpdateCustomerRequest req);
}

@Service
@RequiredArgsConstructor
public class CustomerServiceImpl implements CustomerService {
    private final CustomerRepository repository;
    private final CustomerGateway customerGateway;  // if downstream call needed
    
    @Override
    public Customer create(ApiContext apiContext, CreateCustomerRequest req) {
        Customer entity = new Customer();
        entity.setName(req.getName());
        entity.setEmail(req.getEmail());
        // Pass apiContext to gateway if downstream call needed:
        // return customerGateway.createCustomer(apiContext, req);
        return repository.save(entity);
    }
    
    @Override
    public Customer findById(ApiContext apiContext, String id) {
        return repository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("Customer not found: " + id));
    }
    
    @Override
    public Customer update(ApiContext apiContext, String id, UpdateCustomerRequest req) {
        Customer entity = findById(apiContext, id);
        entity.setName(req.getName());
        entity.setEmail(req.getEmail());
        return repository.save(entity);
    }
}
```

---

## 6. Gateway Pattern — RestApiClient for Downstream Calls

Gateways call downstream APIs using RestApiClient (auto-wired by SDK3). SDK handles header forwarding automatically.

**File:** `src/main/java/{basePackage}/gateway/PaymentGateway.java`

```java
import {basePackage}.context.ApiContext;

public interface PaymentGateway {
    PaymentResponse processPayment(ApiContext apiContext, PaymentRequest req);
}
```

**File:** `src/main/java/{basePackage}/gateway/impl/PaymentGatewayImpl.java`

```java
package {basePackage}.gateway.impl;

import com.barclays.api.bap.bld.lib.logging.LogFactory;
import com.barclays.api.bap.bld.lib.logging.Logger;
import com.barclays.api.bap.bld.lib.logging.PerfEvent;
import com.barclays.api.bap.bld.lib.logging.PerfLogger;
import com.barclays.api.bap.bld.lib.restclient.RestApiClient;
import com.barclays.api.bap.bld.lib.restclient.http.RestClientHttpMethod;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.util.UriComponentsBuilder;
import org.springframework.stereotype.Component;
import {basePackage}.context.ApiContext;
import java.net.URI;
import java.util.HashMap;

@Component
public class PaymentGatewayImpl implements PaymentGateway {

    @Value("${downstream.payment.base-url:https://payment-api.internal}")
    private String baseUrl;

    private final RestApiClient restApiClient;
    
    private static final Logger LOGGER = LogFactory.getLogger(PaymentGatewayImpl.class);
    private static final PerfLogger PERFORMANCE_LOGGER = LogFactory.getPerfLogger(PaymentGatewayImpl.class);

    public PaymentGatewayImpl(RestApiClient restApiClient) {
        this.restApiClient = restApiClient;
    }
    
    @Override
    public PaymentResponse processPayment(ApiContext apiContext, PaymentRequest req) {
        LOGGER.debug("Start - Gateway call for processPayment");
        PerfEvent perfEvent = PERFORMANCE_LOGGER.start("Invoking Payment API Call");
        HttpHeaders httpHeaders = assembleHeaders(apiContext);
        URI uri = UriComponentsBuilder.fromUriString(baseUrl + "/v1/process")
                .build()
                .toUri();
        try {
            PaymentResponse paymentResponse = restApiClient
                    .call(RestClientHttpMethod.POST, uri, req, httpHeaders, PaymentResponse.class)
                    .getBody();
            return paymentResponse;
        } catch (Exception e) {
            LOGGER.error("Error calling Payment API at {}: {}", uri, e.getMessage(), e);
            throw new GatewayException("Failed to process payment: " + e.getMessage(), HttpStatus.BAD_GATEWAY, e);
        } finally {
            LOGGER.debug("End - Gateway call for processPayment");
            perfEvent.stop();
        }
    }

    private HttpHeaders assembleHeaders(ApiContext apiContext) {
        HttpHeaders httpHeaders = new HttpHeaders();
        httpHeaders.add("Correlation-ID", apiContext.getCorrelationId());
        httpHeaders.add("Authorization", apiContext.getAuthorization());
        return httpHeaders;
    }
}
```

**How RestApiClient works:**
1. Handles response deserialization per SDK standards
2. Uses PerfLogger to measure downstream API call timing (wrap in try-finally with perfEvent.stop())

---

## 7. Gateway Pattern — Direct RestApiClient Injection (NO Configuration Required)

**DO NOT create RestClientConfiguration.** RestApiClient is auto-configured by SDK3 and available for direct injection into gateway implementations.

Gateways inject RestApiClient via constructor and use it for downstream REST calls. SDK3 handles header forwarding automatically (Correlation-ID, Authorization, X-Scenario, clientId).

---

## 8. Request/Response DTO Pattern (Barclays Standard)

Request and response DTOs use Barclays wrapper format with `data`, `meta`, `type`, `attributes`.

**Request DTO:**

```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CreateCustomerRequest {
    @NotNull(message = "Name is required")
    private String name;
    
    @Email(message = "Email must be valid")
    private String email;
}
```

**Response DTO:**

```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CustomerResponse {
    private String id;
    
    @JsonFormat(pattern = "yyyy-MM-dd")
    private LocalDate createdDate;
    
    private String name;
    private String email;
}
```

**JavaTime Serialization (SDK Standard):**
- `LocalDate` → `yyyy-MM-dd`
- `LocalTime` → `hh:mm:ss`
- `LocalDateTime` → `yyyy-MM-dd'T'HH:mm:ss.SSS`

---

## 9. Error Handling with SDK

All exceptions must be caught by `GlobalExceptionHandler` and wrapped in SDK response format.

**File:** `src/main/java/{basePackage}/exception/GlobalExceptionHandler.java`

```java
package {basePackage}.exception;

import com.barclays.api.bap.bld.lib.payload.response.RestResponse;
import com.barclays.api.bap.bld.lib.payload.response.Response;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<Response<Void>> handleNotFound(ResourceNotFoundException ex) {
        return ResponseEntity
            .status(HttpStatus.NOT_FOUND)
            .body(RestResponse.assemble()
                .build(HttpStatus.NOT_FOUND, null, ex.getMessage()));
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<Response<Void>> handleBadRequest(IllegalArgumentException ex) {
        return ResponseEntity
            .status(HttpStatus.BAD_REQUEST)
            .body(RestResponse.assemble()
                .build(HttpStatus.BAD_REQUEST, null, ex.getMessage()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Response<Void>> handleGeneral(Exception ex) {
        return ResponseEntity
            .status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(RestResponse.assemble()
                .build(HttpStatus.INTERNAL_SERVER_ERROR, null, "Internal server error"));
    }
}
```

---

## 10. Configuration: application.properties

**Minimum required configuration (SDK auto-configures most):**

```properties
# Application Identity
spring.application.name={artifact}
spring.jpa.hibernate.ddl-auto=validate
spring.datasource.url=jdbc:h2:mem:testdb
spring.datasource.driver-class-name=org.h2.Driver

# Server Configuration
server.port=8080

# Management / Actuator
management.endpoints.web.exposure.include=health,info,metrics
management.endpoint.health.show-details=always

# Logging Levels
logging.level.root=INFO
logging.level.com.barclays.api.bap.bld=DEBUG
logging.level.{basePackage}=DEBUG

# Logging Pattern (includes Correlation-ID from MDC)
logging.pattern.console=%d{ISO8601} [%thread] %level %logger{36} - %msg [%X{correlationId}] %n

# SDK3 Logging Configuration
api.core.perf.log.blacklisted.uris=/health,/healthcheck,/metrics
api.request.payload.max-size=524288
logging.sanitizer.enabled=true

# Auto-forward headers to downstream APIs (optional)
api.core.request.auto-headers=X-Scenario,clientId,Authorization,Correlation-ID
```

---

## 11. Logging Best Practices — SDK3 LogFactory Pattern

🔴 **MANDATORY**: Use SDK3 LogFactory for ALL logging. NEVER use @Slf4j or LoggerFactory.

### Service Layer Logging

```java
@Service
@RequiredArgsConstructor
public class UserServiceImpl implements UserService {
    private static final Logger LOGGER = LogFactory.getLogger(UserServiceImpl.class);
    
    private final UserRepository repository;
    private final UserGateway userGateway;
    
    @Override
    public UserResponse create(CreateUserRequest request) {
        LOGGER.info("Creating user: {}", request.getName());
        UserResponse response = new UserResponse();
        // ... business logic
        LOGGER.debug("User created successfully with ID: {}", response.getId());
        return response;
    }
}
```

### Gateway Layer Logging with PerfLogger

```java
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
            LOGGER.debug("Payment API response received successfully");
            return response;
        } catch (Exception e) {
            LOGGER.error("Error calling Payment API at {}: {}", uri, e.getMessage(), e);
            throw new GatewayException("Failed to process payment", HttpStatus.BAD_GATEWAY, e);
        } finally {
            LOGGER.debug("End - Gateway call for processPayment");
            perfEvent.stop();  // MANDATORY: Always stop performance event
        }
    }

    private HttpHeaders assembleHeaders(ApiContext apiContext) {
        HttpHeaders httpHeaders = new HttpHeaders();
        httpHeaders.add("Correlation-ID", apiContext.getCorrelationId());
        httpHeaders.add("Authorization", apiContext.getAuthorization());
        return httpHeaders;
    }
}
```

### Correct vs Incorrect Logging

```java
// ✅ CORRECT: Use LogFactory
import com.barclays.api.bap.bld.lib.logging.LogFactory;
import com.barclays.api.bap.bld.lib.logging.Logger;

@Service
public class UserServiceImpl {
    private static final Logger LOGGER = LogFactory.getLogger(UserServiceImpl.class);
    
    public void create() {
        LOGGER.info("Creating user");
    }
}

// ❌ WRONG: Use @Slf4j
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
public class UserServiceImpl {
    public void create() {
        log.info("Creating user");  // ❌ WRONG
    }
}

// ❌ WRONG: Use LoggerFactory
import org.slf4j.LoggerFactory;

@Service
public class UserServiceImpl {
    private static final Logger LOGGER = LoggerFactory.getLogger(UserServiceImpl.class);  // ❌ WRONG
    
    public void create() {
        LOGGER.info("Creating user");
    }
}
```

### PerfLogger Usage Rules

1. **ALWAYS wrap downstream API calls:**
   ```java
   PerfEvent perfEvent = PERFORMANCE_LOGGER.start("Operation Name");
   try {
       // Downstream call
   } finally {
       perfEvent.stop();  // MANDATORY
   }
   ```

2. **Use meaningful operation names:**
   ```java
   // ✅ CORRECT
   perfEvent = PERFORMANCE_LOGGER.start("Invoking Payment API Call");
   
   // ❌ WRONG
   perfEvent = PERFORMANCE_LOGGER.start("API Call");  // Too vague
   ```

3. **Log entry and exit points:**
   ```java
   LOGGER.debug("Start - Gateway call for processPayment");
   // ... operation
   LOGGER.debug("End - Gateway call for processPayment");
   ```

---

## Mandatory SDK Integration Checklist

🔴 **Generators MUST verify EVERY item. This is a hard gate for code generation:**

### Configuration & Dependencies
- ✅ `ApplicationConfig` bean exists (SINGLE configuration class) with ExternalApiInitializer or InternalApiInitializer
- ✅ `ApplicationConfig` includes SecureFields bean with NOLOG/MASK rules for sensitive fields (Authorization, password, token, accountNumber, email)
- ✅ NO `RestClientConfiguration`, `SecurityConfig`, or `MeshConnectorConfig` generated
- ✅ `build.gradle` contains EXACTLY these 3 explicit SDK3 dependencies (no more, no less):
  ```
  implementation(platform("com.barclays.api:sdk3:${SDK3_VERSION}"))
  implementation 'com.barclays.api:bap-bld-lib-request-validator'
  implementation 'com.barclays.api:bap-bld-lib-restapi'
  implementation 'com.barclays.api:bap-bld-lib-meshconnector'
  ```
- 🔴 `build.gradle` MUST NOT contain these — they are transitive and adding them explicitly causes version conflicts:
  - `com.barclays.api:bap-bld-lib-logging`
  - `com.barclays.api:bap-bld-lib-common`
  - `com.barclays.api:bap-bld-lib-payload`
  - `com.barclays.api:bap-bld-lib-restclient`
  - `com.barclays.api:bap-bld-lib-health`
- ✅ `build.gradle` does NOT contain: `jakarta.validation:jakarta.validation-api`, resilience4j jars
- ✅ `build.gradle` SDK3_VERSION=1.12.007 (or later)

### Logging (CRITICAL)
- 🔴 **NO @Slf4j annotation anywhere** — use LogFactory instead
- 🔴 **NO import of lombok.extern.slf4j.Slf4j** — forbidden
- 🔴 **NO import of org.slf4j.LoggerFactory** — forbidden
- ✅ All services use: `private static final Logger LOGGER = LogFactory.getLogger(ClassName.class);`
- ✅ All gateways use: `private static final Logger LOGGER = LogFactory.getLogger(ClassName.class);`
- ✅ All gateways use: `private static final PerfLogger PERFORMANCE_LOGGER = LogFactory.getPerfLogger(ClassName.class);`
- ✅ All gateway methods wrap downstream calls in try-finally with `perfEvent.stop()` — MANDATORY

### DTOs (CRITICAL)
- 🔴 **NO jakarta.validation imports** — forbidden
- 🔴 **NO @Valid, @NotNull, @NotBlank, @Email, @Min, @Max, @Pattern, @Size annotations** — forbidden
- ✅ All DTOs are plain POJOs with only Lombok annotations (@Data, @Builder, @NoArgsConstructor, @AllArgsConstructor)
- ✅ Request/Response DTOs match OpenAPI spec structure exactly
- ✅ DTOs contain only fields from spec — no validation logic

### Gradle & Properties
- ✅ `gradle/wrapper/gradle-wrapper.properties` distributionUrl: `https://nexus.barcapint.com/nexus/content/groups/barclays/gradle-8.13-bin.zip`
- ✅ `application.properties` (NOT YAML) contains logging levels: root=INFO, com.barclays.api.bap.bld=DEBUG, PERF=INFO
- ✅ `application.properties` includes SDK3 config: `api.core.perf.log.blacklisted.uris=/health,/healthcheck,/metrics`, `api.request.payload.max-size=524288`, `logging.sanitizer.enabled=true`
- ✅ Logging pattern: `logging.pattern.console=%d{ISO8601} [%thread] %level %logger{36} - %msg [%X{correlationId}] %n`

### Controllers & Gateways
- ✅ All controllers return `com.barclays.api.bap.bld.lib.common.response.Response` — NEVER `ResponseEntity`
- ✅ All controllers use `RestResponse.assemble().build(ResponseHttpStatus.STATUS, data)` — NEVER `ResponseEntity.status(...).body(...)`
- ✅ All controllers accept `ApiContext apiContext` as first parameter (extends InternalRequestContext)
- ✅ All service interface methods carry `ApiContext apiContext` as first parameter
- ✅ All gateway interface methods carry `ApiContext apiContext` as first parameter
- ✅ All gateways use `RestApiClient` (auto-wired by SDK3) — NOT `RestTemplate`, `WebClient`, or Apache HttpClient
- ✅ All gateways import: LogFactory, Logger, PerfLogger, PerfEvent, RestApiClient, RestClientHttpMethod, UriComponentsBuilder, ApiContext
- ✅ All gateways use `assembleHeaders(ApiContext apiContext)` private method — NEVER `headerMap.forEach(httpHeaders::add)`
- ✅ All gateways use `UriComponentsBuilder` for URI construction — NEVER `URI.create()`
- ✅ All gateways inject `baseUrl` via `@Value("${downstream.{service}.base-url:...}")`
- ✅ All gateways wrap downstream calls in `try { } catch { } finally { perfEvent.stop(); }` — MANDATORY

### Logging (applies to ALL generated Java classes)
- 🔴 **NO `@Slf4j` annotation anywhere** — use LogFactory instead
- 🔴 **NO `import org.slf4j.*`** — forbidden
- 🔴 **NO `import org.apache.logging.*`** — forbidden
- 🔴 **NO `import java.util.logging.*`** — forbidden
- ✅ Controllers: `private static final Logger LOGGER = LogFactory.getLogger(ControllerName.class)`
- ✅ Services: `private static final Logger LOGGER = LogFactory.getLogger(ServiceName.class)`
- ✅ Gateways: `private static final Logger LOGGER = LogFactory.getLogger(GatewayName.class)`
- ✅ Gateways: `private static final PerfLogger PERFORMANCE_LOGGER = LogFactory.getPerfLogger(GatewayName.class)`
- ✅ GlobalExceptionHandler: `private static final Logger LOGGER = LogFactory.getLogger(GlobalExceptionHandler.class)`

### Exception Handler (CRITICAL)
- ✅ `GlobalExceptionHandler` return type: `Response` — NEVER `ResponseEntity`
- ✅ Single error: `RestResponse.assemble().addErrorMessage(Message.create("CODE", "Title", "Detail")).build(ResponseHttpStatus.STATUS)`
- ✅ Multiple errors: `RestResponse.assemble().addErrorMessages(List<Message>).build(ResponseHttpStatus.STATUS)`
- 🔴 **NO `ResponseEntity` in `GlobalExceptionHandler`** — use `com.barclays.api.bap.bld.lib.common.response.Response`
- ✅ Catch `ApiException` from `com.barclays.api.bap.bld.lib.payload.exceptions.ApiException` for SDK3 REST errors
- ✅ Status extraction from `ApiException`: `apiException.getStatus()` — NOT `.getHttpStatus()`
- 🔴 **NEVER reference `RestApiException`** — that class must not be used
- ✅ `GlobalExceptionHandler` imports: `ApiException`, `Message`, `RestResponse`, `ResponseHttpStatus`, `Response`, `LogFactory`, `Logger`

### Import Compliance (CRITICAL — these old packages must NEVER appear in generated code)
- 🔴 **NEVER**: `com.barclays.api.rest.commons.response.*` → use `com.barclays.api.bap.bld.lib.*`
- 🔴 **NEVER**: `com.barclays.api.rest.commons.message.Message` → use `com.barclays.api.bap.bld.lib.payload.response.Message`
- 🔴 **NEVER**: `com.barclays.api.bap.bld.lib.restapi.exception.RestApiException` → use `com.barclays.api.bap.bld.lib.payload.exceptions.ApiException`

**Mandatory SDK3 Import Mapping:**

| Type | Correct Package |
|---|---|
| Response wrapper | `com.barclays.api.bap.bld.lib.common.response.Response` |
| RestResponse builder | `com.barclays.api.bap.bld.lib.payload.response.RestResponse` |
| ResponseHttpStatus | `com.barclays.api.bap.bld.lib.payload.response.ResponseHttpStatus` |
| Message | `com.barclays.api.bap.bld.lib.payload.response.Message` |
| ApiException | `com.barclays.api.bap.bld.lib.payload.exceptions.ApiException` |
| Logger | `com.barclays.api.bap.bld.lib.logging.Logger` |
| LogFactory | `com.barclays.api.bap.bld.lib.logging.LogFactory` |
| PerfLogger | `com.barclays.api.bap.bld.lib.logging.PerfLogger` |
| PerfEvent | `com.barclays.api.bap.bld.lib.logging.PerfEvent` |
| RestApiClient | `com.barclays.api.bap.bld.lib.restclient.RestApiClient` |
| RestClientHttpMethod | `com.barclays.api.bap.bld.lib.restclient.http.RestClientHttpMethod` |

### Config Package (CRITICAL)
- ✅ `config/` package contains EXACTLY ONE file: `ApplicationConfig.java`
- 🔴 **NO other `*Config.java` or `*Configuration.java` files** — SDK3 auto-configures everything
- 🔴 **NO `*Filter.java` classes** — SDK3 registers all required filters automatically
- 🔴 **NO `*Interceptor.java` classes** — SDK3 provides ServiceMeshRequestInterceptor automatically
- 🔴 **NO SDK3-infrastructure `*Handler.java` classes** — only `GlobalExceptionHandler.java` in `exception/` is allowed

---

**Reference:** SDK3 repository at `https://app.gitlab.barcapint.com/barclays/bap-sm/source-code/java/sdk` contains 9 modules with complete source and documentation.

## Source Attribution

**Primary sources:**
- Barclays SDK3 repository (`https://app.gitlab.barcapint.com/barclays/bap-sm/source-code/java/sdk`) — 9 modules with source and documentation reviewed directly
- `sdk-integration-guide` internal documentation from BUK API Engineering team — `InternalApiInitializer`, `ExternalApiInitializer`, `RequestContext`, `PerfLogger`, `LogFactory` API contracts
- Production Barclays SDK3 services reviewed — patterns for `@RequestContext` injection, `RestClient` connection pooling, `ServiceMeshRequestInterceptor`

**Training knowledge applied:**
- Spring Boot 3 filter chain and `OncePerRequestFilter` patterns
- `RestClient` (Spring 6) vs. `RestTemplate` trade-offs; SDK3 mandates `RestClient` with connection pool
- Java 21 record types and sealed interfaces (not used in SDK3 patterns but referenced in comparisons)

**Known limitations:**
- SDK3 module count documented as 9; the broader SDK has more modules not covered by this skill (only integration-relevant modules are included)
- `RequestContext` injection pattern assumes the SDK3 filter is registered in the filter chain; misconfigured `ApplicationConfig` will cause injection to fail silently
- All patterns are pinned to the SDK version present in `https://app.gitlab.barcapint.com/barclays/bap-sm/source-code/java/sdk` at the last review date — production upgrades require re-verification

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] Is the correct ApiInitializer type selected (InternalApiInitializer for internal APIs, ExternalApiInitializer for external)?
- [ ] Are SDK3 RestClient properties (connection pool, timeout) configured in application.properties?
- [ ] Is the RequestValidationFilter configured to validate against the OpenAPI/RAML spec?
- [ ] Does the ApplicationConfig declare SecureFields for PII masking in logs?
- [ ] Are all SDK3 filter beans ordered correctly (mesh token injection before request validation)?
