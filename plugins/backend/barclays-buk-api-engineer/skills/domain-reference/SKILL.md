---
name: domain-reference
description: "DAF framework domain knowledge: version tables, module catalog, code patterns, spec file template, and lessons learned. All agents MUST reference this file for versions, patterns, and configuration — never use training data."
---

> **Source:** Barclays DAF Plugin documentation, SDK3 BOM 1.6.001 release notes, and DAF template repository.
> **Owner:** BUK
> **Review trigger:** On any DAF plugin major/minor version release, or SDK3 BOM upgrade. Version table last verified: 2026-07-17.
> **Status:** Reviewed

# DAF Engineer Domain Reference

This is the single source of truth for the DAF Engineer plugin. All agents MUST load the relevant sections of this file before performing any work. Never rely on training data for versions, module names, code patterns, or configuration values.

## Quick Start

Reference this skill for DAF versions and patterns:

1. **Version lookup:** Check Section 1 for exact library versions
2. **Anti-patterns:** Check the FORBIDDEN table before generating code
3. **Module catalog:** Check Section 2 for available DAF modules
4. **Code patterns:** Check Section 3 for implementation templates

Never hardcode versions from training data — always use the values in Section 1.

---

## Section 1: Version Table

| Library | Version | Notes |
|---|---|---|
| DAF Gradle Plugin | (from template) | com.barclays.digital.daf.starter — version is in cloned template's `gradle.properties` as `DAF_PLUGIN_VERSION`. Do NOT hardcode; preserve the value from the template. |
| SDK3 BOM | 1.6.001 | com.barclays.api:sdk3 |
| Spring Boot | 3.4.5 | Via DAF plugin |
| Java | 21 | sourceCompatibility |
| Groovy | 4.0.24 | For Spock tests |
| Spock | 2.4-M1-groovy-4.0 | BDD test framework |
| Jackson | 2.15.2 | JSON processing |
| Google Java Format | 1.26.0 | Spotless formatting |

> **IMPORTANT:** For libraries with fixed versions above, agents MUST use these values exactly. Do not substitute versions from training data or any other source. For `DAF Gradle Plugin`, the version comes from the cloned template's `gradle.properties` — agents MUST preserve it as-is and never overwrite it.

### CRITICAL: Anti-Patterns (NEVER use these)

The following patterns are FORBIDDEN in all DAF services. AI models default to these — you MUST actively avoid them:

| FORBIDDEN Pattern | CORRECT Alternative | Why |
|---|---|---|
| `ResponseEntity<T>` | `RestResponse.assemble().build(status, data)` | DAF uses SDK3 response envelope |
| `org.slf4j.LoggerFactory.getLogger()` | `new LoggerSlf4jImpl(MyClass.class)` | DAF uses SDK3 logging |
| `ThreadLocal<T>` for session | `DafSessionClient` → `DafSessionManagementService` | DAF uses distributed sessions |
| `@Before` advice | `@Around` with `ProceedingJoinPoint` | Must be able to short-circuit/modify returns |
| `@Slf4j` (Lombok) | SDK3 Logger field | No Lombok annotations |
| `@Builder` (Lombok) | Hand-written static builder class | DAF Jackson compatibility |
| `request.getBody()` | `request.getData(TypedClass.class)` | SDK3 Request wrapper pattern |
| Typed return from controller | `Response` return type | Controller is thin pass-through |
| Gateway method without `@Retryable` | Add `@Retryable` + `@Recover` pair | All downstream calls must retry on transient failures |
| `@EnableRetry` on gateway class | Move to `ApplicationConfig` only | Activating retry proxy in the wrong place breaks bean proxying |

---

## Section 2: DAF Module Catalog

### Core Modules (always included — uncommented in daf-dependencies.gradle)

- **daf-api-interceptors** — Request/response interceptor pipeline
- **daf-error-handling** — Standardized error response formatting
- **daf-exceptions** — Base exception classes (ExperienceApiException)
- **daf-logging** — Structured logging with correlation ID propagation

### Optional Modules (uncomment as needed in daf-dependencies.gradle)

- **daf-jwt** — JWT token management for TIAA auth
- **daf-session-client** — Distributed session management
- **daf-session-common** — Session support classes
- **daf-authorization** — Role-based authorization
- **daf-aem-cache** — Adobe Experience Manager content caching
- **daf-bcag** — Barclays Cryptographic Application Gateway
- **daf-bcag-autoconfiguration** — BCAG auto-config
- **daf-datasourcerouter** — Database routing
- **daf-testbedrouter** — Test bed environment routing
- **daf-env-config** — Environment configuration
- **daf-bootstrap** — Bootstrap configuration

### SDK3 Libraries (via BOM — no version needed)

- **bap-bld-lib-restclient** — REST client with retry and circuit breaker
- **bap-bld-lib-common** — Common utilities and response wrappers
- **bap-bld-lib-logging** — SDK3 logging extensions
- **bap-bld-lib-payload** — Request/response payload builders
- **bap-bld-lib-restapi** — REST API base classes
- **bap-bld-lib-request-validator** — Request validation framework
- **bap-bld-lib-meshconnector** — Service mesh connector

---

## Section 3: Code Patterns

All patterns below are derived from the daf-example-api reference implementation. Agents MUST use these patterns as the basis for generated code.

### Pattern 3.1: Application.java

```java
package com.barclays.api;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.web.servlet.support.SpringBootServletInitializer;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@ComponentScan(basePackages = {"com.barclays.api", "com.barclays.api.bap.bld"})
public class Application extends SpringBootServletInitializer {

  public static void main(String[] args) {
    SpringApplication.run(Application.class, args);
  }

  @Override
  protected SpringApplicationBuilder configure(SpringApplicationBuilder applicationBuilder) {
    return applicationBuilder.sources(Application.class);
  }
}
```

### Pattern 3.2: DafHeadersContext.java

```java
package com.barclays.api.{domain}.controller.header;

import com.barclays.daf.api.header.annotations.HeaderContract;
import com.barclays.daf.api.header.annotations.HeaderObject;
import com.barclays.daf.api.header.pojo.v3.*;

@HeaderContract
public class DafHeadersContext {

  @HeaderObject(value = "Correlation-ID", required = true)
  private String correlationId;

  @HeaderObject(required = false)
  private CustomerContext customerContext;

  // ... other headers as specified in spec

  // Getters and setters for each field (hand-written, NOT Lombok)
}
```

### Pattern 3.3: Controller

```java
package com.barclays.api.{domain}.controller;

import com.barclays.api.bap.bld.lib.common.response.Response;
import com.barclays.api.bap.bld.lib.logging.Logger;
import com.barclays.api.bap.bld.lib.logging.LoggerSlf4jImpl;
import com.barclays.api.bap.bld.lib.payload.response.RestResponse;
import com.barclays.api.{domain}.controller.header.DafHeadersContext;
// ... service imports

@RestController
public class {Name}Controller {

  private static final Logger log = new LoggerSlf4jImpl({Name}Controller.class);

  private final {Name}Service {name}Service;

  public {Name}Controller(final {Name}Service {name}Service) {
    this.{name}Service = {name}Service;
  }

  @GetMapping("/{path}")
  public Response get{Entity}(DafHeadersContext apiHeadersContext, @PathVariable String id) {
    // Business logic via service
    var result = {name}Service.find{Entity}(id);
    return RestResponse.assemble().build(result);
  }
}
```

### Pattern 3.4: Service Interface + Impl

```java
// Interface
package com.barclays.api.{domain}.service;
public interface {Name}Service {
  {ReturnType} find{Entity}(String id);
}

// Implementation
package com.barclays.api.{domain}.service.impl;

import com.barclays.api.bap.bld.lib.logging.Logger;
import com.barclays.api.bap.bld.lib.logging.LoggerSlf4jImpl;
import com.barclays.api.{domain}.gateway.{Name}Gateway;
import org.springframework.stereotype.Service;

@Service
public class {Name}ServiceImpl implements {Name}Service {
  private static final Logger log = new LoggerSlf4jImpl({Name}ServiceImpl.class);

  private final {Name}Gateway {name}Gateway;  // Use gateway, NOT RestTemplate directly

  public {Name}ServiceImpl(final {Name}Gateway {name}Gateway) {
    this.{name}Gateway = {name}Gateway;
  }

  @Override
  public {ReturnType} find{Entity}(String id) {
    // Implementation using gateway for downstream calls
    // Business logic stays in service; HTTP calls go through gateway
  }
}
```

### Pattern 3.5: Custom Exception

```java
package com.barclays.api.{domain}.exception;

import com.barclays.api.bap.bld.lib.payload.response.ResponseHttpStatus;
import com.barclays.daf.exceptions.ExperienceApiException;

public class {Name}ApiException extends ExperienceApiException {
  private static final long serialVersionUID = 1L;

  public enum ERROR_CODE {
    // Each entry: name(code, httpStatus, returnToClient)
    EXAMPLE_ERROR("001", ResponseHttpStatus.BAD_REQUEST, true);

    private final String code;
    private final ResponseHttpStatus responseHttpStatus;
    private final boolean returnToClient;

    ERROR_CODE(String code, ResponseHttpStatus responseHttpStatus, boolean returnToClient) {
      this.code = code;
      this.responseHttpStatus = responseHttpStatus;
      this.returnToClient = returnToClient;
    }

    public String getCode() { return this.code; }
    public ResponseHttpStatus getResponseHttpStatus() { return this.responseHttpStatus; }
    public boolean isReturnToClient() { return this.returnToClient; }
  }

  public {Name}ApiException(ERROR_CODE code) {
    super(code.getCode(), code.getResponseHttpStatus(), null, null, code.isReturnToClient());
  }
}
```

### Pattern 3.6: Downstream API Config

```java
// Config class
@Configuration
@ConfigurationProperties(prefix = "api.{name}")
public class {Name}ApiConfig extends ApiConfig {
  private TiaaConfig tiaa;
  // getters/setters for tiaa (if TIAA auth)
}

// Beans class
@Configuration
public class {Name}ApiBeans {
  private final {Name}ApiConfig config;
  public {Name}ApiBeans({Name}ApiConfig config) { this.config = config; }
  // Bean definitions for JwtTokenManager, TiaaJwtTokenService (if TIAA auth)
}
```

### Pattern 3.7: DTO with Builder (hand-written, NOT Lombok)

```java
package com.barclays.api.{domain}.dto;

public class {Name} {
  private String field1;
  private String field2;

  public {Name}() {}
  {Name}(final String field1, final String field2) {
    this.field1 = field1;
    this.field2 = field2;
  }

  public static class {Name}Builder {
    private String field1;
    private String field2;
    {Name}Builder() {}
    public {Name}Builder field1(final String field1) { this.field1 = field1; return this; }
    public {Name}Builder field2(final String field2) { this.field2 = field2; return this; }
    public {Name} build() { return new {Name}(this.field1, this.field2); }
  }

  public static {Name}Builder builder() { return new {Name}Builder(); }
  // getters, setters, equals, hashCode, toString
}
```

### Pattern 3.8: Spock @WebMvcTest Controller Test

```groovy
package com.barclays.api.{domain}.controller

import org.spockframework.spring.SpringBean
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest
import org.springframework.context.annotation.ComponentScan
import org.springframework.test.context.ActiveProfiles
import org.springframework.test.util.ReflectionTestUtils
import org.springframework.test.web.servlet.MockMvc
import com.barclays.daf.exception.handler.DefaultExceptionHandlers
import com.barclays.daf.exception.messages.ErrorMessagesService
import spock.lang.Specification
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*

@ActiveProfiles("Test")
@WebMvcTest(controllers = {Name}Controller)
@AutoConfigureMockMvc
@ComponentScan(["com.barclays.api.bap.bld.*"])
class {Name}ControllerTest extends Specification {

  @Autowired
  private MockMvc mvc

  @SpringBean
  private {Name}Service {name}Service = Mock()

  @SpringBean
  private ErrorMessagesService messagesService = Mock()

  @SpringBean
  private DefaultExceptionHandlers defaultExceptionHandlers = new DefaultExceptionHandlers()

  def setup() {
    ReflectionTestUtils.setField(defaultExceptionHandlers, "messagesService", messagesService)
  }

  def "should return 200 for GET /{path}"() {
    given:
    def expected = // setup mock return
    {name}Service.find{Entity}(_) >> expected

    when:
    def result = mvc.perform(get("/{path}")).andReturn()

    then:
    result.response.status == 200
  }
}
```

### Pattern 3.9: build.gradle (simplified DAF template)

```gradle
plugins {
    id 'com.barclays.digital.daf.starter' version "${DAF_PLUGIN_VERSION}"
}
group = "${GROUP_ID}"
version = "${VERSION}"
apply from: 'daf-dependencies.gradle'
```

### Pattern 3.10: RestClientInterceptorConfig

```java
package com.barclays.api.config;
import com.barclays.daf.api.interceptors.*;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RestClientInterceptorConfig {
  @Bean
  public DafExceptionHandlerInterceptor dafExceptionHandlerInterceptor() { return new DafExceptionHandlerInterceptor(); }
  @Bean
  public DafLoggerInterceptor dafLoggerInterceptor() { return new DafLoggerInterceptor(); }
  @Bean
  public DafHeaderInterceptor dafHeaderInterceptor(HeaderForwardingConfig config) { return new DafHeaderInterceptor(config.getToForward()); }
}
```

### Pattern 3.18: ErrorCodes Enum (Structured Error Handling)

When spec defines error cases, generate an `ErrorCodes` enum that builds `RestResponse` directly (NOT exception-based):

```java
package com.barclays.api.{domain}.error;

import com.barclays.api.bap.bld.lib.logging.Logger;
import com.barclays.api.bap.bld.lib.logging.LoggerSlf4jImpl;
import com.barclays.api.bap.bld.lib.payload.response.Message;
import com.barclays.api.bap.bld.lib.payload.response.ResponseHttpStatus;
import com.barclays.api.bap.bld.lib.payload.response.RestResponse;
import com.barclays.daf.exception.ExperienceApiException;

public enum ErrorCodes {
  ERROR_CALLING_CUSTOMER_ENQUIRY_API("BDDF01", "Failure to get Customer data", "Unable to find Customer Enquiry data for given customer : XX"),
  INVALID_SESSION("BDDF02", "Failure to get session data", "Unable to find session data for given session ID : XX."),
  ERROR_CALLING_CONTENT_API("BDDF03", "Failure to get content", "Unable to find content for given content ID : XX"),
  ERROR_CALLING_FORMS_API("BDDF04", "Failure to get form data", "Unable to find form data for given form ID : XX"),
  ERROR_CALLING_SUBMIT_API("BDDF05", "Failure to submit form data", "Unable to submit form data for given form ID : XX"),
  GENERAL_ERROR("BDDF06", "A Technical error has occurred", "Sorry, a technical error has occurred, please try again.");

  private static final Logger log = new LoggerSlf4jImpl(ErrorCodes.class);
  private final String code;
  private final String title;
  private final String detail;

  ErrorCodes(String code, String title, String detail) {
    this.code = code; this.title = title; this.detail = detail;
  }

  public RestResponse buildErrorResponse() {
    log.error("{} {} {}", this.name(), this.code, this.detail);
    return RestResponse.assemble()
        .addErrorMessage(Message.create(this.code, this.title, this.detail))
        .build(ResponseHttpStatus.INTERNAL_SERVER_ERROR);
  }

  public RestResponse buildErrorResponse(String param) {
    log.error("{} {} {}", this.name(), this.code, this.detail.replace("XX", param));
    return RestResponse.assemble()
        .addErrorMessage(Message.create(this.code, this.title, this.detail.replace("XX", param)))
        .build(ResponseHttpStatus.INTERNAL_SERVER_ERROR);
  }

  public ExperienceApiException buildException(String param) {
    return new ExperienceApiException(this.code, this.detail.replace("XX", param));
  }
}
```

**KEY:** Services return `RestResponse` from `ErrorCodes.X.buildErrorResponse(param)` instead of throwing exceptions. This keeps error responses in the normal response flow.

### Pattern 3.19: Unified Response Wrapper (DynamicFormsResponse)

When spec has multiple endpoints sharing a response structure, generate a unified response wrapper:

```java
package com.barclays.api.{domain}.bean;

import com.fasterxml.jackson.annotation.JsonInclude;

@JsonInclude(JsonInclude.Include.NON_EMPTY)
public class {Domain}Response {
  private ResponseAttributes attributes;
  // builder pattern (hand-written)

  public static class ResponseAttributes {
    private Object aemContent;          // for content endpoint
    private BusinessContext businessContext;  // shared across endpoints
    private EligibilityStatus eligibilityStatus;  // for eligibility endpoint
    private Object form;                 // for forms endpoint
    private Object submitStatus;         // for submit endpoint
    private NavigationContextResponse navigationContext;  // shared
    // builder pattern (hand-written)
  }
}
```

**Service methods return `RestResponse`** (from `com.barclays.api.bap.bld.lib.payload.response`):
```java
return RestResponse.assemble().build(ResponseHttpStatus.OK, dynamicFormsResponse);
```

### Pattern 3.20: Mutation Testing (PIT/pitest)

Configure pitest for mutation testing coverage analysis. This is configured during build setup (Wave 0) but NOT run during generation — it's too slow for the pipeline. Users run `./gradlew pitest` manually afterward.

**build.gradle plugin:**
```groovy
plugins {
    id 'com.barclays.digital.daf.starter' version "${DAF_PLUGIN_VERSION}"
    id 'info.solidsoft.pitest' version '1.15.0'
}
```

**build.gradle configuration block:**
```groovy
pitest {
    targetClasses = ['com.barclays.api.*']
    mutators = ['DEFAULTS']
    outputFormats = ['HTML', 'XML']
    timestampedReports = false
    junit5PluginVersion = '1.2.1'
    mutationThreshold = 90
}
```

**daf-dependencies.gradle:**
```groovy
testImplementation 'org.pitest:pitest-junit5-plugin:1.2.1'
```

**afterEvaluate override (MANDATORY — DAF plugin disables pitest by default):**
```groovy
afterEvaluate {
    tasks.named('pitest').configure {
        enabled = true
    }
    tasks.named('jacocoTestCoverageVerification').configure {
        enabled = true
    }
}
```

**Key concepts:**
- `targetClasses`: Scope of mutation — only your service code, not framework
- `mutators = ['DEFAULTS']`: Standard set (conditionals, math, returns, void calls)
- `mutationThreshold = 90`: 90% killed mutations required to pass
- Reports generated in `build/reports/pitest/`

### Pattern 3.21: Performance Smoke Tests

Generate performance smoke tests that run as part of the standard `./gradlew test` suite. These are NOT load tests — they verify basic response time SLAs and sequential stability.

```groovy
package com.barclays.api.{domain}.controller

import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.test.context.ActiveProfiles
import org.springframework.test.web.servlet.MockMvc
import spock.lang.Specification
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*

@ActiveProfiles("Test")
@SpringBootTest
@AutoConfigureMockMvc
class PerformanceSmokeTest extends Specification {

  @Autowired
  private MockMvc mvc

  def "should respond within SLA for GET #endpoint"() {
    when:
    long start = System.currentTimeMillis()
    def result = mvc.perform(get(endpoint)).andReturn()
    long elapsed = System.currentTimeMillis() - start

    then:
    elapsed < 2000  // 2 second SLA

    where:
    endpoint << ["/endpoint1", "/endpoint2", "/endpoint3"]
  }

  def "should maintain stability under sequential load for #endpoint"() {
    given:
    List<Long> responseTimes = []

    when:
    10.times {
      long start = System.currentTimeMillis()
      mvc.perform(get(endpoint)).andReturn()
      responseTimes << (System.currentTimeMillis() - start)
    }

    then: "no response time degrades beyond 3x the first response"
    def baseline = responseTimes[0] ?: 1
    responseTimes.every { it < baseline * 3 }

    where:
    endpoint << ["/endpoint1", "/endpoint2"]
  }
}
```

**Key points:**
- Uses `@SpringBootTest` (full context) NOT `@WebMvcTest` — tests actual wiring
- SLA threshold: 2000ms per endpoint (generous, accounts for cold start)
- Sequential stability: 10 requests, none > 3x baseline
- Replace endpoint placeholders with actual paths from spec
- Mock downstream APIs with `@SpringBean` or WireMock to avoid network dependencies

### Pattern 3.12: Gateway Layer (Interface + Impl)

Every downstream API call MUST go through a dedicated gateway class. Gateways abstract external API communication from service logic, improving testability and separation of concerns.

```java
// Interface
package com.barclays.api.{domain}.gateway;

public interface {Name}Gateway {
  {ResponseType} {method}({params});
}

// Implementation
package com.barclays.api.{domain}.gateway.impl;

import com.barclays.api.bap.bld.lib.logging.Logger;
import com.barclays.api.bap.bld.lib.logging.LoggerSlf4jImpl;
import com.barclays.daf.exceptions.ExperienceApiException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpMethod;
import org.springframework.retry.annotation.Backoff;
import org.springframework.retry.annotation.Recover;
import org.springframework.retry.annotation.Retryable;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

@Component
public class {Name}GatewayImpl implements {Name}Gateway {
  private static final Logger log = new LoggerSlf4jImpl({Name}GatewayImpl.class);

  private final RestTemplate restTemplate;

  @Value("${api.{name}.url}")
  private String apiUrl;

  @Value("${api.{name}.method}")
  private String apiMethod;

  public {Name}GatewayImpl(RestTemplate restTemplate) {
    this.restTemplate = restTemplate;
  }

  @Override
  @Retryable(
    retryFor = ExperienceApiException.class,
    maxAttemptsExpression = "${retry.gateway.max-attempts:3}",
    backoff = @Backoff(
      delayExpression = "${retry.gateway.delay:500}",
      multiplierExpression = "${retry.gateway.multiplier:2}",
      random = true
    )
  )
  public {ResponseType} {method}({params}) {
    log.info("Calling {Name} API with url: {}", apiUrl);
    try {
      // Build headers, set path params, call API via restTemplate.exchange(...)
      // Return deserialized response
    } catch (Exception e) {
      log.error("Error calling {Name} API: {}", e.getMessage(), e);
      throw new ExperienceApiException(e.getMessage());
    }
  }

  @Recover
  public {ResponseType} recover{Method}(ExperienceApiException ex, {params}) {
    log.error("{Name} API exhausted all retries. Last error: {}", ex.getMessage(), ex);
    throw ex;
  }
}
```

**Key Rules:**
- One gateway per downstream API
- Gateway handles ONLY HTTP communication (headers, URL building, RestTemplate call, response deserialization)
- Service layer handles business logic; gateway handles transport
- Use `@Value` for URL and method injection from properties
- Use SDK3 Logger (LoggerSlf4jImpl), NOT standard SLF4J
- Every gateway method MUST carry `@Retryable` — retries on transient failures automatically
- Every `@Retryable` method MUST have a `@Recover` method — same return type, exception first param
- `@EnableRetry` is on `ApplicationConfig` only — do NOT add it to gateway classes

### Pattern 3.13: SDK3 Logging (MANDATORY)

ALL generated classes MUST use SDK3 logging, NOT standard SLF4J:

```java
import com.barclays.api.bap.bld.lib.logging.Logger;
import com.barclays.api.bap.bld.lib.logging.LoggerSlf4jImpl;

public class MyClass {
  private static final Logger log = new LoggerSlf4jImpl(MyClass.class);

  // Usage is same as SLF4J:
  log.info("Message with param: {}", value);
  log.error("Error occurred", exception);
  log.debug("Debug info: {}", data);
}
```

**NEVER use:**
- `org.slf4j.LoggerFactory.getLogger()` — use `LoggerSlf4jImpl` instead
- `lombok.extern.slf4j.Slf4j` — use explicit SDK3 logger

### Pattern 3.14: Utility Class (EncoderDecoderUtil)

When spec mentions Base64 encoding/decoding or data masking, generate a utility class:

```java
package com.barclays.api.{domain}.util;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.Base64;

public class EncoderDecoderUtil {

  private EncoderDecoderUtil() {} // Utility class — private constructor

  private static final ObjectMapper mapper = new ObjectMapper();

  public static <T> T getDecodedData(String requestPayload, Class<T> clazz) throws IOException {
    String decodedString = new String(Base64.getDecoder().decode(requestPayload));
    return mapper.readValue(decodedString, clazz);
  }

  public static String getEncodedData(Object data) throws JsonProcessingException {
    String jsonPayload = mapper.writeValueAsString(data);
    return Base64.getEncoder().encodeToString(jsonPayload.getBytes());
  }

  public static String getMaskedData(String data) {
    if (data == null || data.length() <= 5) return "*****";
    return "*****" + data.substring(5);
  }
}
```

### Pattern 3.15: AOP Interceptor Aspects

When spec mentions custom interceptors (e.g., @BusinessDetailsInterceptor, @DynamicFormsInterceptor, @SaveCustomerDetailsInterceptor), generate:

1. **Custom Annotation:**
```java
package com.barclays.api.{domain}.aspect;

import java.lang.annotation.*;

@Documented
@Retention(RetentionPolicy.RUNTIME)
@Target({ElementType.METHOD})
public @interface {Name}Interceptor {}
```

2. **Aspect Implementation:**
```java
package com.barclays.api.{domain}.aspect;

import com.barclays.api.bap.bld.lib.logging.Logger;
import com.barclays.api.bap.bld.lib.logging.LoggerSlf4jImpl;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.context.annotation.Configuration;

@Aspect
@Configuration
public class {Name}InterceptorImpl {
  private static final Logger log = new LoggerSlf4jImpl({Name}InterceptorImpl.class);

  // Injected dependencies (session service, mappers, etc.)

  @Around(value = "@annotation({name}Interceptor)", argNames = "joinPoint,{name}Interceptor")
  public Object {name}Interceptor(ProceedingJoinPoint joinPoint, {Name}Interceptor {name}Interceptor)
      throws Throwable {
    Object[] args = joinPoint.getArgs();
    // Pre-processing: validate session, enrich request, etc.
    Object result = joinPoint.proceed(args);
    // Post-processing: update session, log, etc.
    return result;
  }
}
```

3. **Usage in Controller:**
```java
@{Name}Interceptor
@PostMapping("/path")
public Response method(DafHeadersContext headers, @RequestBody Request request) {
  // Method body — interceptor handles cross-cutting concerns
}
```

### Pattern 3.16: Session Management Service

When `daf-session-client` is selected and spec describes session-based flows, generate a dedicated session management service:

```java
// Session Key Enum
package com.barclays.api.{domain}.service.session;

public enum SessionKey {
  CUSTOMER("ServicingCustomerDetails");  // Key name matches daf-attributes.properties

  private final String name;
  SessionKey(String s) { name = s; }
  @Override public String toString() { return name; }
}

// Session Bean (Serializable DTO stored in session)
package com.barclays.api.{domain}.service.session.bean;

import java.io.Serializable;

public class {Domain}Session implements Serializable {
  private {BusinessContext} businessDetails;
  // getters, setters, builder
}

// Session Service Interface
package com.barclays.api.{domain}.service.session;

public interface DafSessionManagementService {
  {Domain}Session get({HeaderContextType} apiRequestContext);
  void addBusinessDetails({BusinessContext} businessDetails, {HeaderContextType} apiRequestContext);
}

// Session Service Implementation
package com.barclays.api.{domain}.service.session;

import com.barclays.api.bap.bld.lib.logging.Logger;
import com.barclays.api.bap.bld.lib.logging.LoggerSlf4jImpl;
import com.barclays.api.daf.session.client.DafSessionClient;
import com.barclays.api.daf.session.common.DafSession;
import com.barclays.api.daf.session.common.exception.DafSessionException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.retry.annotation.Backoff;
import org.springframework.retry.annotation.Retryable;
import org.springframework.stereotype.Service;

@Service
public class DafSessionManagementServiceImpl implements DafSessionManagementService {
  private static final Logger log = new LoggerSlf4jImpl(DafSessionManagementServiceImpl.class);

  private final DafSessionClient client;

  @Value("${daf.session.api-id}")
  private String dafApiId;

  public DafSessionManagementServiceImpl(DafSessionClient client) {
    this.client = client;
  }

  @Override
  public {Domain}Session get({HeaderContextType} apiRequestContext) {
    try {
      DafSession session = client.getDafSession(dafApiId, Boolean.TRUE);
      session.preFetchAttributes(SessionKey.CUSTOMER.toString());
      return session.getAttribute(SessionKey.CUSTOMER.toString(), {Domain}Session.class);
    } catch (DafSessionException e) {
      log.error("Error retrieving session data", e);
      return null;
    }
  }

  @Override
  @Retryable(value = DafSessionException.class, maxAttemptsExpression = "${config.session.api.retry.count:3}",
      backoff = @Backoff(delayExpression = "0"))
  public void addBusinessDetails({BusinessContext} businessDetails, {HeaderContextType} apiRequestContext) {
    try {
      DafSession session = client.getDafSession(dafApiId, Boolean.TRUE);
      {Domain}Session domainSession = new {Domain}Session();
      domainSession.setBusinessDetails(businessDetails);
      session.setAttribute(SessionKey.CUSTOMER.toString(), domainSession, false, false);
      session.commit();
    } catch (DafSessionException e) {
      log.error("Error writing session data", e);
      throw e;
    }
  }
}
```

**daf-attributes.properties** must declare the session class and max size:
```properties
{SessionKey.name}.classes={full.qualified.SessionBeanClass}
{SessionKey.name}.maxsize=10240
```

### Pattern 3.17: ApiRequestContext (Request-Scoped Bean)

When session management or AOP interceptors need request-scoped state sharing:

```java
package com.barclays.api.{domain}.context;

import com.barclays.api.{domain}.controller.header.DafHeadersContext;
import org.springframework.context.annotation.Scope;
import org.springframework.context.annotation.ScopedProxyMode;
import org.springframework.stereotype.Component;
import org.springframework.web.context.WebApplicationContext;

@Component
@Scope(value = WebApplicationContext.SCOPE_REQUEST, proxyMode = ScopedProxyMode.TARGET_CLASS)
public class ApiRequestContext {
  private DafHeadersContext apiHeadersContext;
  private String sessionId;

  public DafHeadersContext getApiHeadersContext() { return apiHeadersContext; }
  public void setApiHeadersContext(DafHeadersContext apiHeadersContext) { this.apiHeadersContext = apiHeadersContext; }
  public String getSessionId() { return sessionId; }
  public void setSessionId(String sessionId) { this.sessionId = sessionId; }
}
```

### Pattern 3.11: OAS 3.0.3 Structure

```yaml
openapi: 3.0.3
info:
  title: {Service-Name}
  description: |-
    -**API Type:** Internal
    -**API Risk Classification:** LOW
    -**API Owner (business):** {team}
    -**API Owner (technical):** {owner}
    -**API Overview:** {description}
  contact:
    name: '{team name}'
    email: '{team email}'
  version: 'v{version}'
servers:
  - url: 'https://zuul-gateway-{env}.np2.apaas4.barclays.intranet/{service-name}/'
    description: SIT Server URL
tags:
  - name: {tag}
    description: {description}
security:
  - InternalTiaaUsRopcAuth: []
components:
  securitySchemes:
    InternalTiaaUsRopcAuth:
      $ref: './common-libraries/security/security-schemes.yaml#/InternalTiaaUsRopcAuth'
  schemas:
    # $ref to ./lib/types.yaml and ./lib/request-types.yaml
  responses:
    InternalServerError:
      $ref: './common-libraries/components/responses.yaml#/InternalServerError'
    # ... standard error responses
paths:
  /{resource}/{id}:
    get:
      tags: [{tag}]
      summary: {summary}
      operationId: {operationId}
      parameters:
        - name: {param}
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/{ResponseType}'
        '400':
          $ref: '#/components/responses/BadRequest'
        '500':
          $ref: '#/components/responses/InternalServerError'
```

---

## Section 3b: Reference Implementation Examples

These are COMPLETE reference implementations from production DAF services. When generating service code, use these as templates for the LEVEL OF IMPLEMENTATION DETAIL required.

### Example 3b.1: EligibilityServiceImpl (Complete Pattern)

```java
@Service
public class EligibilityServiceImpl implements EligibilityService {
  private static final Logger log = new LoggerSlf4jImpl(EligibilityServiceImpl.class);
  private final EligibilityServiceMapper eligibilityServiceMapper;
  private final CustomerEnquiryGateway customerEnquiryGateway;
  private final ProductHoldingGateway productHoldingGateway;

  @Autowired
  public EligibilityServiceImpl(EligibilityServiceMapper mapper, CustomerEnquiryGateway ceGateway, ProductHoldingGateway phGateway) {
    this.eligibilityServiceMapper = mapper;
    this.customerEnquiryGateway = ceGateway;
    this.productHoldingGateway = phGateway;
  }

  @Override
  public RestResponse eligibility(Request request) {
    DynamicFormsRequest dynamicFormsRequest = request.getData(DynamicFormsRequest.class);
    try {
      DynamicFormsResponse response = processCustomerEligibility(dynamicFormsRequest);
      if (Boolean.TRUE.equals(response.getAttributes().getEligibilityStatus().getIsEligible())) {
        enrichWithProductDetails(dynamicFormsRequest, response);
      }
      return RestResponse.assemble().build(ResponseHttpStatus.OK, response);
    } catch (Exception e) {
      log.error("Error processing eligibility for customer: {}", EncoderDecoderUtil.getMaskedData(dynamicFormsRequest.getBusinessCustomerId()), e);
      return ErrorCodes.ERROR_CALLING_CUSTOMER_ENQUIRY_API.buildErrorResponse(EncoderDecoderUtil.getMaskedData(dynamicFormsRequest.getBusinessCustomerId()));
    }
  }

  private DynamicFormsResponse processCustomerEligibility(DynamicFormsRequest request) {
    CustomerEnquiryAPIResponse ceResponse = customerEnquiryGateway.getCustomerDetails(request.getBusinessCustomerId());
    return eligibilityServiceMapper.mapCustomerEnquiryGatewayResponseToModel(ceResponse, request.getAccountDetails());
  }

  private void enrichWithProductDetails(DynamicFormsRequest request, DynamicFormsResponse response) {
    try {
      ProductHoldingAPIResponse phResponse = productHoldingGateway.getCustomerDetails(request.getBusinessCustomerId());
      BusinessContext enriched = eligibilityServiceMapper.mapProductHoldingGatewayResponseToModel(phResponse, response.getAttributes().getBusinessContext(), request.getAccountDetails());
      response.getAttributes().setBusinessContext(enriched);
    } catch (Exception e) {
      log.error("Error enriching with product holding details, continuing without: {}", e.getMessage());
    }
  }
}
```

### Example 3b.2: SubmitServiceImpl (Complete Pattern)

```java
@Service
public class SubmitServiceImpl implements SubmitService {
  private static final Logger log = new LoggerSlf4jImpl(SubmitServiceImpl.class);
  private final SubmitGateway submitGateway;
  private final ApiRequestContext apiRequestContext;

  @Override
  public RestResponse submitData(Request request) {
    DynamicFormsRequest dynamicFormsRequest = request.getData(DynamicFormsRequest.class);
    try {
      SaveDataResponse response = submitGateway.submitData(mapRequestBean(dynamicFormsRequest));
      return RestResponse.assemble().build(ResponseHttpStatus.CREATED, mapResponseBean(response));
    } catch (ExperienceApiException | IOException e) {
      log.error("Error calling submit API", e);
      return ErrorCodes.ERROR_CALLING_SUBMIT_API.buildErrorResponse(dynamicFormsRequest.getSubmitData().getFormId());
    }
  }

  private SaveDataAPIRequest mapRequestBean(DynamicFormsRequest request) throws IOException {
    SubmitData submitData = EncoderDecoderUtil.getDecodedData(request.getFormData(), SubmitData.class);
    request.setSubmitData(submitData);
    // Build fields by iterating and REPLACING values by fieldId
    List<FieldDetails> fields = buildFields(request, submitData.getFields());
    List<AdditionalAttributes> attrs = buildAdditionalAttributes(request, submitData);
    SaveForm.SaveFormData formData = SaveForm.SaveFormData.builder()
        .formId(submitData.getFormId()).additionalAttributes(attrs).fields(fields).build();
    SaveForm saveForm = SaveForm.builder().form(formData).build();
    return SaveDataAPIRequest.builder().formData(EncoderDecoderUtil.getEncodedData(saveForm)).build();
  }

  private List<FieldDetails> buildFields(DynamicFormsRequest request, List<FieldDetails> fields) {
    if (fields == null || fields.isEmpty()) return List.of();
    for (FieldDetails field : fields) {
      switch (field.getFieldId()) {
        case SubmitConstants.MCC_BUSINESS_NAME -> field.setFieldValue(request.getAccountDetails().getAccountName());
        case SubmitConstants.MCC_ACCOUNT_NUMBER -> field.setFieldValue(request.getAccountDetails().getAccountNumber());
        case SubmitConstants.MCC_SORT_CODE -> field.setFieldValue(request.getAccountDetails().getSortCode().replaceAll("-", ""));
        case SubmitConstants.MCC_CUSTOMER_SYSTEM_NUMBER -> field.setFieldValue(request.getBusinessCustomerId());
        case SubmitConstants.CUSTOMER_BUSINESS_EMAIL_ADDRESS -> field.setFieldValue(request.getEmailAddress());
        default -> {} // Keep existing value
      }
    }
    return fields;
  }

  private List<AdditionalAttributes> buildAdditionalAttributes(DynamicFormsRequest request, SubmitData submitData) {
    return Stream.of(
      new AdditionalAttributes(SubmitConstants.PROCESS_NAME, submitData.getProcessName()),
      new AdditionalAttributes(SubmitConstants.CUSTOMER_ID, request.getBusinessCustomerId()),
      new AdditionalAttributes(SubmitConstants.CHANNEL_KEY, apiRequestContext.getChannelId()),
      new AdditionalAttributes(SubmitConstants.FORM_ID, submitData.getFormId()),
      new AdditionalAttributes(SubmitConstants.REQUESTER_TYPE_KEY, "Customer"),
      new AdditionalAttributes(SubmitConstants.TYPE, submitData.getType()),
      new AdditionalAttributes(SubmitConstants.SUB_TYPE, submitData.getSubType()),
      new AdditionalAttributes(SubmitConstants.MCC_BUSINESS_NAME, request.getAccountDetails().getAccountName()),
      new AdditionalAttributes(SubmitConstants.MCC_ACCOUNT_NUMBER, request.getAccountDetails().getAccountNumber()),
      new AdditionalAttributes(SubmitConstants.MCC_SORT_CODE, request.getAccountDetails().getSortCode().replaceAll("-", "")),
      new AdditionalAttributes(SubmitConstants.MCC_CUSTOMER_SYSTEM_NUMBER, request.getBusinessCustomerId()),
      new AdditionalAttributes(SubmitConstants.CUSTOMER_BUSINESS_EMAIL_ADDRESS, request.getEmailAddress()),
      new AdditionalAttributes(SubmitConstants.ORIGINAL_REPAYMENT_DATE, formatDate(request.getTakenOutDate()))
    ).toList();
  }

  private String formatDate(String takenOutDate) {
    if (takenOutDate == null || takenOutDate.isBlank()) return "";
    try {
      SimpleDateFormat odsFormat = new SimpleDateFormat("yyyy-MM-dd");
      SimpleDateFormat displayFormat = new SimpleDateFormat("dd/MM/yyyy");
      return displayFormat.format(odsFormat.parse(takenOutDate));
    } catch (Exception e) { return ""; }
  }
}
```

### Example 3b.3: DynamicFormsInterceptorImpl (Complete AOP Pattern)

```java
@Aspect
@Configuration
public class DynamicFormsInterceptorImpl {
  private static final Logger log = new LoggerSlf4jImpl(DynamicFormsInterceptorImpl.class);
  private final DynamicFormsInterceptorMapper mapper;
  private final ApiRequestContext apiRequestContext;

  // @DynamicFormsInterceptor — validates session before forms/content access
  @Around(value = "@annotation(dynamicFormsInterceptor)", argNames = "joinPoint,dynamicFormsInterceptor")
  public Object dynamicFormsInterceptor(ProceedingJoinPoint joinPoint, DynamicFormsInterceptor dynamicFormsInterceptor) throws Throwable {
    Object[] args = joinPoint.getArgs();
    apiRequestContext.setApiHeadersContext((ApiHeadersContext) args[0]);
    DynamicFormsSession session = mapper.getSessionData(apiRequestContext);
    if (ObjectUtils.isEmpty(session) || ObjectUtils.isEmpty(session.getBusinessDetails())) {
      return ErrorCodes.INVALID_SESSION.buildErrorResponse(apiRequestContext.getSessionId());
    }
    return joinPoint.proceed(args);
  }

  // @SaveCustomerDetailsInterceptor — reads business details FROM session into request before submit
  @Around(value = "@annotation(saveCustomerDetailsInterceptor)", argNames = "joinPoint,saveCustomerDetailsInterceptor")
  public Object saveCustomerDetailsInterceptor(ProceedingJoinPoint joinPoint, SaveCustomerDetailsInterceptor saveCustomerDetailsInterceptor) throws Throwable {
    Object[] args = joinPoint.getArgs();
    apiRequestContext.setApiHeadersContext((ApiHeadersContext) args[0]);
    Request request = (Request) args[1];
    DynamicFormsRequest dynamicFormsRequest = request.getData(DynamicFormsRequest.class);
    DynamicFormsSession session = mapper.getSessionData(apiRequestContext);
    if (ObjectUtils.isEmpty(session) || ObjectUtils.isEmpty(session.getBusinessDetails())) {
      return ErrorCodes.INVALID_SESSION.buildErrorResponse(apiRequestContext.getSessionId());
    }
    // Inject session data INTO the request
    dynamicFormsRequest.setBusinessCustomerId(session.getBusinessDetails().getCustomerId());
    dynamicFormsRequest.setEmailAddress(session.getBusinessDetails().getEmailAddress());
    dynamicFormsRequest.setAccountDetails(session.getBusinessDetails().getAccountDetails());
    dynamicFormsRequest.setTakenOutDate(session.getBusinessDetails().getTakenOutDate());
    request.setData(dynamicFormsRequest);
    return joinPoint.proceed(args);
  }
}

// Separate class for @BusinessDetailsInterceptor — POST-processing after eligibility
@Aspect
@Configuration
public class BusinessDetailsInterceptorImpl {
  private final DynamicFormsInterceptorMapper mapper;
  private final ApiRequestContext apiRequestContext;

  // @BusinessDetailsInterceptor — AFTER eligibility, persists business context to session
  @Around(value = "@annotation(businessDetailsInterceptor)", argNames = "joinPoint,businessDetailsInterceptor")
  public Object businessDetailsInterceptor(ProceedingJoinPoint joinPoint, BusinessDetailsInterceptor businessDetailsInterceptor) throws Throwable {
    Object[] args = joinPoint.getArgs();
    apiRequestContext.setApiHeadersContext((ApiHeadersContext) args[0]);
    try {
      RestResponse response = (RestResponse) joinPoint.proceed(args);  // Execute FIRST
      Request request = (Request) args[1];
      if (CollectionUtils.isEmpty(response.getErrors())) {
        mapper.updateDynamicFormsSession(request, response, apiRequestContext);  // THEN save to session
      }
      return response;
    } catch (Exception e) {
      return ErrorCodes.GENERAL_ERROR.buildErrorResponse();
    }
  }
}
```

### Example 3b.4: NavigationContext (Enum Pattern)

```java
public enum NavigationContext {
  MANAGE_YOUR_LOAN("manageyourloan", "productlist", ""),
  FORMS("", "datacapture", ""),
  SUCCESS("success", "outcome", ""),
  ERROR("error", "outcome", ""),
  SERVICING_FORMS("manageyourloan", "launch", "servicingforms");

  private final String contentId;
  private final String screen;
  private final String journeyId;

  NavigationContext(String contentId, String screen, String journeyId) {
    this.contentId = contentId; this.screen = screen; this.journeyId = journeyId;
  }

  public static NavigationContextResponse build(NavigationContext nav) {
    return new NavigationContextResponse(nav.contentId, nav.journeyId, nav.screen);
  }

  public static class NavigationContextResponse {
    private String contentId;
    private String journeyId;
    private String screen;
    // constructor, getters, builder
  }
}
```

### Example 3b.5: EligibilityServiceMapper (Segment Validation Pattern)

## ⚠️ CRITICAL SEGMENT CODE MAPPING ⚠️

**The spec says "SM" and "BBK" — these are BUSINESS NAMES, not actual codes.**

**In the ODS Customer Enquiry API response, the ACTUAL marker codes are:**
- **Simple Mandate (SM):** groupSegmentCode = `"C01"`, lowSegmentCode = `"C06"`
- **BUK Mandate (BBK):** groupSegmentCode = `"DD0"`, lowSegmentCode = `"DD1"`

**VALIDATION LOGIC:** Customer is eligible ONLY if BOTH conditions are true (AND logic):
1. Has Simple Mandate marker (group="C01" AND low="C06")
2. Has BUK marker (group="DD0" AND low="DD1")

**NEVER use "SM" or "BBK" as literal code values. They don't exist in the API response.**

**Use an EligibilityConstant enum:**
```java
public enum EligibilityConstant {
  SIMPLE_MARKER_GROUP_SEGMENT_CODE("C01", "Customer does NOT have a Simple Mandate Marker"),
  SIMPLE_MARKER_LOW_SEGMENT_CODE("C06", "Customer does NOT have a Simple Mandate Marker"),
  BUK_GROUP_SEGMENT_CODE("DD0", "Customer does NOT have a BUK Marker"),
  BUK_LOW_SEGMENT_CODE("DD1", "Customer does NOT have a BUK Marker"),
  INVALID_CUSTOMER("INVALID_CUSTOMER", "Customer not Found in ODS"),
  INELIGIBLE_PRODUCT_CODE("INELIGIBLE_PRODUCT_CODE", "Eligible Product not Found for associated account");

  private final String marker;
  private final String errorMessage;
  EligibilityConstant(String marker, String errorMessage) { this.marker = marker; this.errorMessage = errorMessage; }
  public String getMarker() { return marker; }
  public String getErrorMessage() { return errorMessage; }
}
```

```java
@Service
public class EligibilityServiceMapper {
  private final DafConfig dafConfig;
  @Value("${manageloan.eligibleproducts}") private List<String> defaultEligibleProducts;

  // BOTH conditions must be true (AND logic):
  // 1. Simple Mandate: group="C01" AND low="C06"
  // 2. BUK Mandate: group="DD0" AND low="DD1"
  private String segmentInEligibilityMsg(CustomerEnquiryAPIResponse response) {
    AtomicBoolean isSimpleMandate = new AtomicBoolean(false);
    AtomicBoolean isBUKCustomer = new AtomicBoolean(false);
    response.getAttributes().getSegmentDataList().stream()
      .filter(s -> s.getGroupSegmentCode() != null && s.getLowSegmentCode() != null)
      .anyMatch(s -> {
        if (isSimpleMandateCustomer(s.getGroupSegmentCode().getCode(), s.getLowSegmentCode().getCode())) isSimpleMandate.set(true);
        if (isBUKMandateCustomer(s.getGroupSegmentCode().getCode(), s.getLowSegmentCode().getCode())) isBUKCustomer.set(true);
        return isSimpleMandate.get() && isBUKCustomer.get();
      });
    return (isSimpleMandate.get() && isBUKCustomer.get()) ? "" : getEligibilityMessage(isSimpleMandate.get(), isBUKCustomer.get());
  }

  private boolean isSimpleMandateCustomer(String groupCode, String lowCode) {
    return EligibilityConstant.SIMPLE_MARKER_GROUP_SEGMENT_CODE.getMarker().equals(groupCode)
        && EligibilityConstant.SIMPLE_MARKER_LOW_SEGMENT_CODE.getMarker().equals(lowCode);
  }

  private boolean isBUKMandateCustomer(String groupCode, String lowCode) {
    return EligibilityConstant.BUK_GROUP_SEGMENT_CODE.getMarker().equals(groupCode)
        && EligibilityConstant.BUK_LOW_SEGMENT_CODE.getMarker().equals(lowCode);
  }

  // Finds eligible product matching account number AND product code in eligible list
  private MiscellaneousProductHoldingData eligibleProduct(CustomerEnquiryAPIResponse response, Account accountDetails) {
    String eligibleProducts = dafConfig.getProperty("manageloan.eligibleproducts");
    List<String> eligibleProductsList = Arrays.asList(eligibleProducts.split(","));
    String sortCode = accountDetails.getSortCode().replaceAll("-", "");
    String fullAccountNumber = sortCode + accountDetails.getAccountNumber();
    return response.getAttributes().getMiscellaneousProductHoldingDataList().stream()
      .filter(p -> p.getProductCode() != null
          && p.getAccountNumber().equalsIgnoreCase(fullAccountNumber)
          && eligibleProductsList.contains(p.getProductCode()))
      .findFirst().orElse(null);
  }

  // Product Holding enrichment - matches loanAccountNumber and extracts nextDueDate + loanCollectionStatusCode
  public BusinessContext mapProductHoldingGatewayResponseToModel(ProductHoldingAPIResponse phResponse, BusinessContext currentContext, Account accountDetails) {
    if (phResponse.getAttributes() == null || phResponse.getAttributes().getAlsData() == null) return currentContext;
    String sortCode = accountDetails.getSortCode().replaceAll("-", "");
    String targetAccount = sortCode + accountDetails.getAccountNumber();
    return phResponse.getAttributes().getAlsData().stream()
      .filter(als -> als.getLoanAccountNumber().equalsIgnoreCase(targetAccount))
      .findFirst()
      .map(als -> BusinessContext.builder()
          .emailAddress(currentContext.getEmailAddress())
          .takenOutDate(als.getNextDueDate())
          .customerId(currentContext.getCustomerId())
          .productCode(currentContext.getProductCode())
          .loanCollectionStatusCode(als.getLoanCollectionStatusCode())
          .build())
      .orElse(currentContext);
  }
}
```

### Example 3b.6: ContentServiceImpl (AEM Caching Pattern)

```java
@Service
public class ContentServiceImpl implements ContentService {
  private static final Logger log = new LoggerSlf4jImpl(ContentServiceImpl.class);
  private final DafSessionManagementService sessionService;
  private final ConcurrentHashMap<String, Object> contentCache = new ConcurrentHashMap<>();

  @Value("${aem.content.cms-host}") private String contentHost;
  @Value("${manageloan.active.services}") private List<String> activeServices;
  @Value("${manageloan.eligibleproducts}") private List<String> eligibleProducts;

  @Override
  public RestResponse getContent(String journeyType, String contentId, ApiRequestContext apiRequestContext) {
    DynamicFormsSession session = sessionService.get(apiRequestContext);
    if (ObjectUtils.isEmpty(session) || ObjectUtils.isEmpty(session.getBusinessDetails())) {
      return ErrorCodes.INVALID_SESSION.buildErrorResponse(apiRequestContext.getSessionId());
    }
    try {
      Object cachedContent = contentCache.get(contentId);
      if (cachedContent == null) {
        return ErrorCodes.CONTENT_CACHING_ERROR.buildErrorResponse(contentId);
      }
      // Build response with content, navigation context, and business context from session
      BusinessContext businessContext = session.getBusinessDetails();
      NavigationContext.NavigationContextResponse navContext = buildNavigationContext(businessContext, contentId);
      DynamicFormsResponse response = DynamicFormsResponse.builder()
          .attributes(ResponseAttributes.builder()
              .aemContent(cachedContent)
              .businessContext(businessContext)
              .navigationContext(navContext)
              .build())
          .build();
      return RestResponse.assemble().build(ResponseHttpStatus.OK, response);
    } catch (Exception e) {
      log.error("Error retrieving content for contentId: {}", contentId, e);
      return ErrorCodes.ERROR_CALLING_CONTENT_API.buildErrorResponse(contentId);
    }
  }

  @Scheduled(cron = "${content.refresh.interval}")
  public void refreshContent() {
    // Fetch from AEM and populate contentCache
  }
}
```

---

## Section 4: Spec File Template

Copy this template, fill in every field, and provide it to the `/daf-engineer` command. All sections are required unless marked optional.

```markdown
# DAF Service Specification

## Service Identity
| Field | Value |
|---|---|
| Service Name | my-daf-service |
| Group ID | com.barclays.digital.daf |
| Artifact ID | my-daf-service |
| Version | 1.0 |
| Base Package | com.barclays.api.myservice |
| Server Port | 9090 |

## DAF Module Selections
- [x] daf-jwt
- [ ] daf-session-client
- [ ] daf-session-common
- [ ] daf-authorization
- [ ] daf-aem-cache
- [ ] daf-bcag
- [ ] daf-bcag-autoconfiguration
- [ ] daf-datasourcerouter
- [ ] daf-testbedrouter
- [ ] daf-env-config
- [ ] daf-bootstrap

## Header Configuration
### Headers to Forward
- Correlation-ID
- ChannelContext
- CustomerContext
- Authorization

### Header Objects for Controllers
| Header | Type | Required |
|---|---|---|
| Correlation-ID | String | true |
| CustomerContext | CustomerContext | false |
| ChannelContext | ChannelContext | false |

## Downstream APIs
### {API Name}
| Field | Value |
|---|---|
| Config Prefix | api.{name} |
| Base URL | https://... |
| Auth Type | TIAA / NONE / OAUTH2 |

#### TIAA Config (if applicable)
| Field | Value |
|---|---|
| Client ID | {client-id} |
| Username | {username} |
| Endpoint | {token-endpoint} |

## API Endpoints
### {Endpoint Name}
| Field | Value |
|---|---|
| Path | /resource/{id} |
| Method | GET |
| Controller | ResourceController |
| Method Name | getResource |
| Path Params | id: String |
| Query Params | (none) |
| Request Body | (none) |
| Response Type | ResourceResponseData |
| Success Status | 200 |
| Error Cases | 404 NOT_FOUND, 500 INTERNAL_SERVER_ERROR |

## Data Models
### Entities
#### {EntityName}
| Field | Type | Annotations |
|---|---|---|
| id | Long | @Id @GeneratedValue |
| name | String | |
JPA: yes/no

### DTOs
#### {DtoName}
| Field | Type |
|---|---|
| field1 | String |
Builder: yes/no

## Service Layer
### {ServiceName}
| Field | Value |
|---|---|
| Interface Methods | findEntity(String id): Entity |
| Business Logic | Fetches entity from repository, maps to DTO |
| Dependencies | EntityRepository |
| Downstream Calls | (none) |

## Error Handling
### Exception Class: {Name}ApiException
| Code | Name | HTTP Status | Return to Client |
|---|---|---|---|
| 001 | RESOURCE_NOT_FOUND | NOT_FOUND (404) | true |
| 002 | INTERNAL_ERROR | INTERNAL_SERVER_ERROR (500) | false |

## Test Scenarios
### {TestClassName}
| Field | Value |
|---|---|
| Type | controller / service / integration |
| Mocked Beans | Service1, Service2 |
| Scenarios | should return 200 for valid request; should return 404 for missing resource |
```

---

## Section 5: Lessons Learned

These are real issues encountered in DAF template projects. Agents MUST apply these fixes proactively during code generation.

### Issue 1: Template Application class name is lowercase

**Problem:** The daf_template ships with `public class application` (lowercase).
**Root cause:** Template oversight — Java convention requires PascalCase.
**Fix:** Rename class to `Application` and update `SpringApplication.run(Application.class, args)`.
**Applies to:** Phase 2 (App Core + Config).

### Issue 2: Test package uses com.example.daf_template

**Problem:** Default test file is in package `com.example.daf_template` instead of project base package.
**Root cause:** Template was scaffolded from Spring Initializr defaults.
**Fix:** Move test files to the correct base package and update package declaration.
**Applies to:** Phase 5 (Test Generation).

### Issue 3: @ComponentScan must include bap.bld package

**Problem:** Missing `@ComponentScan` with `com.barclays.api.bap.bld` causes SDK3 beans to not be loaded.
**Root cause:** SDK3 libraries live in a different base package.
**Fix:** Always add `@ComponentScan(basePackages = {"com.barclays.api", "com.barclays.api.bap.bld"})`.
**Applies to:** Phase 2 (App Core + Config).

### Issue 4: Tests need DefaultExceptionHandlers + ErrorMessagesService

**Problem:** Spock `@WebMvcTest` tests fail without DAF error handling beans.
**Root cause:** DAF error handling framework requires these beans even in test context.
**Fix:** Add the following to every `@WebMvcTest` Spock spec:

```groovy
@SpringBean
private ErrorMessagesService messagesService = Mock()

@SpringBean
private DefaultExceptionHandlers defaultExceptionHandlers = new DefaultExceptionHandlers()

def setup() {
  ReflectionTestUtils.setField(defaultExceptionHandlers, "messagesService", messagesService)
}
```

**Applies to:** Phase 5 (Test Generation).

### Issue 5: Hand-written builders, not Lombok

**Problem:** Using Lombok `@Builder` causes issues with DAF framework serialization.
**Root cause:** DAF framework expects specific builder patterns compatible with Jackson.
**Fix:** Always use hand-written builder pattern (static inner class) as shown in Pattern 3.7. Never use Lombok `@Builder`, `@Data`, or `@AllArgsConstructor` for DTOs.
**Applies to:** Phase 4 (Domain Layer).

### Issue 6: settings.gradle pluginManagement is required

**Problem:** Build fails to resolve DAF plugin without pluginManagement block.
**Root cause:** DAF plugin is hosted on internal Nexus, not Gradle Plugin Portal.
**Fix:** Add the following to `settings.gradle` before `rootProject.name`:

```gradle
pluginManagement {
  repositories {
    maven {
      url 'https://nexus.barcapint.com/nexus/content/groups/barclays/'
    }
  }
}
```

**Applies to:** Phase 1 (Build Configuration).

### Issue 7: MUST use SDK3 Logger, NOT standard SLF4J

**Problem:** AI-generated code uses `org.slf4j.LoggerFactory.getLogger()` which is the wrong logging facade for DAF services.
**Root cause:** Training data defaults to standard SLF4J patterns.
**Fix:** ALL classes MUST use SDK3 logging:
```java
import com.barclays.api.bap.bld.lib.logging.Logger;
import com.barclays.api.bap.bld.lib.logging.LoggerSlf4jImpl;

private static final Logger log = new LoggerSlf4jImpl(MyClass.class);
```
**NEVER use:** `org.slf4j.Logger`, `org.slf4j.LoggerFactory`, or `@Slf4j` from Lombok.
**Applies to:** ALL phases that generate Java classes (Phases 2-5).

### Issue 8: Gateway layer is MANDATORY for downstream API calls

**Problem:** AI-generated code makes RestTemplate calls directly in service implementations.
**Root cause:** Simplification during generation collapses gateway + service into one layer.
**Fix:** ALWAYS create a gateway interface + implementation pair per downstream API. Services call gateways, gateways call RestTemplate. This improves testability (mock gateway in service tests) and follows the gold standard pattern.
**Applies to:** Phase 4 (Domain Layer).

### Issue 9: daf-attributes.properties must be fully populated

**Problem:** When daf-session-client is selected, daf-attributes.properties is generated but left empty or with only comments.
**Root cause:** Agent doesn't know the session bean class name at module integration time.
**Fix:** Use the service identity to derive the session bean class. For service `digital-dynamic-forms-xapi` with base package `com.barclays.api`, the domain package is `com.barclays.api.digital.dynamicforms` and the session bean is `DynamicFormsSession`. The entry must be:
```properties
ServicingCustomerDetails.classes=com.barclays.api.digital.dynamicforms.service.session.bean.DynamicFormsSession
ServicingCustomerDetails.maxsize=10240
```
**Applies to:** Phase 3 (Module Integration).

### Issue 10: Config repo must include ALL service-specific properties

**Problem:** AI-generated config repo environment files miss many service-specific properties present in the gold standard (eligible products, AEM paths, forms source, etc.).
**Root cause:** Config repo agent only copies downstream API URLs and session properties but misses application-specific business configuration.
**Fix:** Parse spec's Step 7 (Configuration Properties) and copy ALL properties verbatim into the correct environment files. Properties from spec Step 7 are the authoritative source — include them exactly as specified.
**Applies to:** Phase 5 (Config Repository).

---

## Section 6: Module Integration Guide

This section documents the EXACT code changes required for each optional DAF module. The `daf-module-agent` references this section during Phase 3 (Module Integration).

**IMPORTANT:** Only modules explicitly selected `[x]` in the spec's DAF Module Selections should be integrated. Never add code for unselected modules.

---

### Module: daf-jwt

**Purpose:** JWT token management for TIAA authentication with downstream APIs.

**Dependency line:** `implementation "com.barclays.digital.daf:daf-jwt:${dafModulesVersion}"`

**Code changes:**
1. Add `DafJwtInterceptor` bean to `RestClientInterceptorConfig.java`:
   ```java
   import com.barclays.daf.api.interceptors.DafJwtInterceptor;
   import com.barclays.daf.jwt.manager.JwtTokenManager;

   @Bean
   public DafJwtInterceptor dafJwtInterceptor(JwtTokenManager jwtTokenManager) {
       return new DafJwtInterceptor(jwtTokenManager);
   }
   ```
2. Per-downstream API config beans (created in Phase 2) provide `JwtTokenManager` and `TiaaJwtTokenService` beans:
   ```java
   @Bean
   public JwtTokenManager jwtTokenManager(TiaaJwtTokenService tiaaJwtTokenService) {
       return new JwtTokenManagerImpl(tiaaJwtTokenService);
   }

   @Bean
   public TiaaJwtTokenService tiaaJwtTokenService() {
       RestTemplate restTemplate = new RestTemplate();
       return new TiaaJwtTokenServiceImpl(restTemplate, clientId, username, password, endpoint);
   }
   ```

**Properties:** TIAA credentials are per-downstream-API (already handled in Phase 2 config):
```properties
api.{name}.tiaa.client-id=
api.{name}.tiaa.username=
api.{name}.tiaa.password=
api.{name}.tiaa.endpoint=
```

**Beans provided:** `JwtTokenManager`, `TiaaJwtTokenService`, `DafJwtInterceptor`

---

### Module: daf-session-client

**Purpose:** Distributed session management via daf-session-mgt-api. Always paired with `daf-session-common`.

**Dependency lines:**
```
implementation "com.barclays.digital.daf:daf-session-client:${dafModulesVersion}"
implementation "com.barclays.digital.daf:daf-session-common:${dafModulesVersion}"
```

**Code changes:**
1. Create `src/main/resources/daf-attributes.properties`:
   ```properties
   # Session attribute definitions
   # Format: attribute-name.classes=fully.qualified.ClassName
   # attribute-name.maxsize=<bytes>
   ```
2. Create `config/DafSessionConfig.java` (if DAF Gradle Plugin does not auto-configure):
   ```java
   package com.barclays.api.config;

   import org.springframework.context.annotation.Configuration;
   import org.springframework.context.annotation.Import;

   @Configuration
   @Import(com.barclays.api.daf.session.config.DafSessionSpringConfig.class)
   public class DafSessionConfig {
   }
   ```

**Properties to add to application.properties:**
```properties
# DAF Session Management
daf.session.daf-session-mgt-api-endpoint-url=
daf.session.api-id={artifactId}
daf.session.channel-id=
daf.session.test-environment=
```

**Beans provided:** `DafSessionClient` (autowire in controllers/services that need session management)

**Usage in controllers:**
```java
@Autowired
private DafSessionClient dafSessionClient;

DafSession session = dafSessionClient.getDafSession(apiId, true);
session.preFetchAttributes("AttrName1", "AttrName2");
MyType attr = session.getAttribute("AttrName1", MyType.class);
session.setAttribute("AttrName2", updatedValue);
session.commit();
```

**Test setup:** Mock `DafSessionClient` as `@SpringBean` in Spock tests. Mock `DafSession` for `preFetchAttributes`, `getAttribute`, `setAttribute`, `commit`.

---

### Module: daf-authorization

**Purpose:** JWT-based ACL (Access Control List) filtering for endpoint-level authorization.

**Dependency line:** `implementation "com.barclays.digital.daf:daf-authorization:${dafModulesVersion}"`

**Code changes:**
1. Create `config/JwtAclFilterConfig.java`:
   ```java
   package com.barclays.api.config;

   import com.barclays.daf.authorization.filter.JwtAclFilter;
   import org.springframework.context.annotation.Bean;
   import org.springframework.context.annotation.Configuration;

   @Configuration
   public class JwtAclFilterConfig {
       @Bean
       public JwtAclFilter jwtAclFilter() {
           return new JwtAclFilter();
       }
   }
   ```

**Properties to add to application.properties:**
```properties
# JWT ACL Authorization
# Format: jwt.acl.userServlets.{N}={username}:{paths}:{methods}
jwt.acl.userServlets.1=anonymous:/man/health:GET
```

**Beans provided:** `JwtAclFilter`

---

### Module: daf-aem-cache

**Purpose:** Adobe Experience Manager (AEM) content caching with automatic refresh.

**Dependency line:** `implementation "com.barclays.digital.daf:daf-aem-cache:${dafModulesVersion}"`

**Code changes:** None — auto-configured. The `aemContentService` bean is automatically available.

**Properties to add to application.properties:**
```properties
# AEM Cache Configuration
aem.cache.enabled=true
aem.cache.max.entries=50
aem.cache.auto.refresh.enabled=false
aem.cache.auto.refresh.initial.delay=600
aem.cache.auto.refresh.period=600
aem.graphql.endpoint=
aem.graphql.persistedquery.endpoint=
```

**Beans provided:** `aemContentService` (auto-configured)

**Usage:**
```java
@Autowired
private AemContentService aemContentService;

String content = aemContentService.retrieveAemContent(contentKey);
String dynamicContent = aemContentService.retrieveAemContentRuntime(contentKey);
```

---

### Module: daf-bcag

**Purpose:** Barclays Cryptographic Application Gateway — encryption/decryption services. Always paired with `daf-bcag-autoconfiguration`.

**Dependency lines:**
```
implementation "com.barclays.digital.daf:daf-bcag:${dafModulesVersion}"
implementation "com.barclays.digital.daf:daf-bcag-autoconfiguration:${dafModulesVersion}"
```

**Code changes:** None — auto-configured by `daf-bcag-autoconfiguration`. The `BcagCommonInterface` bean is auto-created.

**Properties to add to application.properties:**
```properties
# BCAG Configuration
bcag.disabled=true
bcag.logon.key.store.type=JKS
bcag.logon.key.store.password=
bcag.logon.key.store.path=
bcag.username=
bcag.password=
bcag.server.addresses=
bcag.timeout=30000
bcag.logon.timeout=30000
bcag.connection.count=1
bcag.failure.retry=3
bcag.firewall.timeout=1000000
bcag.connection.keepalive=true
bcag.ticket.extend.mode=RELOG
```

**Beans provided:** `BcagCommonInterface` (auto-configured)

**Usage:**
```java
@Autowired
private BcagCommonInterface bcagCommonInterface;

byte[] encrypted = bcagCommonInterface.encrypt(plainText, encryptAlias, from, to);
byte[] decrypted = bcagCommonInterface.decrypt(encrypted, decryptAlias, from, to);
```

**Testing:** Set `bcag.disabled=true` in test properties to mock the BCAG service.

---

### Module: daf-testbedrouter

**Purpose:** Routes requests to different test bed environments based on the `TestContext` DAF header.

**Dependency line:** `implementation "com.barclays.digital.daf:daf-testbedrouter:${dafModulesVersion}"`

**Code changes:** None — `TestBedSource` is auto-configured.

**Properties to add to application.properties:**
```properties
# Testbed Router
app.testbed=P
```

**Beans provided:** `TestBedSource` (auto-configured)

**Usage in controllers:**
```java
@Autowired
private TestBedSource testBedSource;

// In endpoint method:
return RestResponse.assemble()
    .setHeader("testbed", testBedSource.getTestBed())
    .build(responseData);
```

**Header override:** `TestContext: {"testbed":"J"}` — only used in test environments, MUST be optional in OAS spec.

---

### Module: daf-env-config

**Purpose:** Environment-specific property overrides based on the `EnvironmentContext` DAF header.

**Dependency line:** `implementation "com.barclays.digital.daf:daf-env-config:${dafModulesVersion}"`

**Code changes:** None — `DafConfig` is auto-configured.

**Properties:** Define base properties and environment overrides:
```properties
# Base property
app.target-url=http://default.example.com/
# Environment-specific overrides (labels MUST be UPPERCASE)
app.target-url.ENV1=http://env1.example.com/
app.target-url.ENV2=http://env2.example.com/
```

**Beans provided:** `DafConfig` (auto-configured)

**Usage:**
```java
@Autowired
private DafConfig dafConfig;

String url = dafConfig.getProperty("app.target-url");
// Returns environment-specific value based on EnvironmentContext header
```

---

### Module: daf-bootstrap

**Purpose:** Enables DAF component scanning and context populating filter. Required for hybrid APIs.

**Dependency line:** `implementation "com.barclays.digital.daf:daf-bootstrap:${dafModulesVersion}"`

**Code changes:** None — automatic.

**Properties (optional, for hybrid APIs only):**
```properties
# Regex patterns for non-DAF endpoints to exclude from DAF processing
hybrid.api.non.daf.endpoints.ignoreList=
```

**Beans provided:** Component scanning enablement, `ContextPopulatingFilter`

---

### Module: daf-datasourcerouter

**Purpose:** Routes database connections based on DAF context headers.

**Dependency line:** `implementation "com.barclays.digital.daf:daf-datasourcerouter:${dafModulesVersion}"`

**Code changes:** Requires datasource configuration beans. Typically used with JPA/H2 for local dev.

**Properties to add to application.properties:**
```properties
# Datasource Configuration
spring.datasource.url=
spring.datasource.username=
spring.datasource.password=
spring.datasource.driver-class-name=
spring.jpa.hibernate.ddl-auto=none
```

---

### Modules NOT applicable for DAF services

The following modules are internal to the DAF framework build system and should NEVER be included in API service projects:
- daf-api-descriptor
- daf-gradle-consumer
- daf-registry-common
- daf-registry-rules
- daf-schema-constants
- daf-specification-publishing

If any of these appear in a spec, **ignore them** and log a warning.

---

## Section 7: Loading Instructions for Agents

Each phase of the FORGE pipeline loads only the sections it needs. Agents MUST follow these instructions to minimize context usage and ensure accuracy.

```
Phase 0 (Spec Analysis + Clone):
  Load Sections 1, 4, 5 of this file.
  Use Section 4 to validate spec format.
  Use Section 5 to plan template fixes.

Phase 1 (Build Configuration):
  Load Sections 1, 2 of this file.
  Use Section 1 for ALL version values.
  Use Section 2 for module selection logic.
  NEVER use training data for versions.

Phase 2 (App Core + Config):
  Load Sections 3 (Patterns 3.1, 3.6, 3.10), 5 of this file.
  Use Pattern 3.1 for Application.java.
  Use Pattern 3.6 for downstream API configs.
  Use Pattern 3.10 for interceptor config.

Phase 3 (Module Integration):
  Load Section 6 (Module Integration Guide) of this file.
  Only process modules that are selected [x] in the spec.
  Follow the exact code changes documented per module.

Phase 4 (Domain Layer):
  Load Section 3 (Patterns 3.2-3.5, 3.7, 3.12-3.19) AND Section 3b (Reference Implementations).
  Use Pattern 3.2 for DafHeadersContext.
  Use Pattern 3.3 for controllers.
  Use Pattern 3.4 for services.
  Use Pattern 3.5 for exceptions.
  Use Pattern 3.7 for DTOs.
  Use Pattern 3.12 for gateways.
  Use Pattern 3.13 for logging (SDK3 LoggerSlf4jImpl).
  Use Pattern 3.14 for EncoderDecoderUtil.
  Use Pattern 3.15 for AOP interceptors.
  Use Pattern 3.16 for session management.
  Use Pattern 3.17 for ApiRequestContext.
  Use Pattern 3.18 for ErrorCodes enum.
  Use Pattern 3.19 for unified response wrapper.
  Use Section 3b examples as TEMPLATES for implementation quality.

Phase 5 (Config Repository):
  Load Section 8 of this file.
  Use Section 8 for all environment-specific config patterns.
  Reference downstream API URLs from spec analysis.

Phase 6 (Test Generation):
  Load Section 3 (Patterns 3.8, 3.20, 3.21), 5 (Issues 2, 4) of this file.
  Load Section 9 for Karate integration tests and Section 10 for Spock unit test patterns.
  Use Pattern 3.8 for Spock tests.
  Use Pattern 3.20 for pitest mutation testing configuration.
  Use Pattern 3.21 for performance smoke tests.
  Use Issue 4 for required test beans.

Phase 7 (OAS Spec):
  Load Section 3 (Pattern 3.11) of this file.
  Load Section 11 for multi-file OAS structure.
  Use Pattern 3.11 for OAS structure.

Phase 8 (Validation):
  Load ALL sections.
  Cross-reference generated output against all patterns and lessons.
```

---

## Section 8: Config Repository Patterns

The config repository is a separate Git repository that holds environment-specific properties. It is consumed by Spring Cloud Config Server at runtime.

### 8.1 Directory Structure

```
{service-name}-config/
├── application-sit.properties      # SIT environment
├── application-oat.properties      # OAT environment
├── application-prod.properties     # Production environment
├── deployment-sit.properties       # SIT deployment config
├── deployment-oat.properties       # OAT deployment config
└── deployment-prod.properties      # Prod deployment config
```

### 8.2 Environment URL Resolution Patterns

| Environment | Eureka | API URL Format | TIAA Endpoint |
|---|---|---|---|
| SIT | `eureka.client.enabled=false` | Direct HTTPS URLs (e.g., `https://zuul-gateway-pt-a-XXXXX.np2.apaas4.barclays.intranet/...`) | SIT TIAA from spec |
| OAT | `eureka.client.enabled=true` | Eureka-resolved: `http://eureka-zuul-gateway/{api-path}` | OAT TIAA from spec |
| Prod | `eureka.client.enabled=true` | Eureka-resolved: `http://eureka-zuul-gateway/{api-path}` | Prod TIAA from spec |

### 8.3 Common Properties (All Environments)

```properties
spring.application.name={service-name}
server.port={serverPort from spec, typically 9090}
application.name={service-name}

# Error handling
xapi.identifier="{2-char identifier from spec}"
xapi.default-error-message=Something's gone wrong - please try again later.

# Request validation
requestValidation.isRequired=true
oasRequestValidation.isSwaggerValidation=true
oasRequestValidation.swaggerPath=oas/openapi.yaml
requestValidation.specPath=oas/openapi.yaml
```

### 8.4 SIT-Specific Properties

```properties
# Logging — DEBUG for service, ERROR for frameworks
logging.level.root=INFO
logging.level.com.barclays.api.{domain}=DEBUG
logging.level.org.springframework.cloud=ERROR
logging.level.org.springframework.web=ERROR

# Eureka disabled — direct URLs
eureka.client.enabled=false

# Each downstream API configured with direct SIT URLs from spec
api.{name}.url={sit-url-from-spec}
api.{name}.method={GET|POST|PUT}
```

### 8.5 OAT/Prod Properties

```properties
# Logging — INFO level
logging.level.root=INFO
logging.level.com.barclays.api.{domain}=INFO

# Eureka enabled — service discovery
eureka.client.enabled=true
eureka.client.serviceUrl.defaultZone=http://eureka.{env}.{zone}.apaas4.barclays.intranet/eureka/

# Downstream APIs use Eureka-resolved URLs
api.{name}.url=http://eureka-zuul-gateway/{api-path}
```

### 8.6 Deployment Properties

```properties
# deployment-sit.properties
jvm.args=-Xms512m -Xmx1024m -XX:+UseG1GC
instances=1
health.check.path=/man/health

# deployment-oat.properties
jvm.args=-Xms512m -Xmx1024m -XX:+UseG1GC
instances=2
health.check.path=/man/health

# deployment-prod.properties
jvm.args=-Xms1024m -Xmx2048m -XX:+UseG1GC
instances=3
health.check.path=/man/health
```

### 8.7 Module-Specific Environment Properties

If `daf-session-client` selected:
```properties
daf.session.api-id={service-name}
daf.session.channel-id=TBA
daf.session.daf-session-mgt-api-endpoint-url={env-specific URL}
daf.session.connection-timeout=1000
daf.session.socket-timeout=5000
daf.session.keep-alive=true
daf.session.keep-alive-duration=3600000
daf.session.socket-tcp-no-delay=false
config.session.api.retry.count=3
```

If `daf-aem-cache` selected:
```properties
daf.cache.enabled=true
aem.cache.envs={env-specific}
aem.cache.instance={env-specific}
content.refresh.interval=0 0 */2 * * *
aem.content.cms-host={env-specific}
aem.content.path={from spec}
```

If `daf-testbedrouter` selected:
```properties
api.test.bed={env-specific test bed ID}
```

---

## Section 9: Integration Testing (Karate + WireMock)

This section documents the generalizable patterns for writing integration tests in a DAF API using Karate (BDD syntax) and WireMock (JSON-based file stubs). The integration test suite boots WireMock first, then Spring Boot, then runs Karate feature files against the live application context.

### 9.1 Directory Structure

```
src/integrationTest/
├── java/
│   └── KarateTest/
│       ├── TestRunner.java           # JUnit 5 runner: boots Spring + WireMock
│       └── utils/
│           ├── WiremockRunner.java   # WireMock lifecycle utility
│           └── DataUtils.java        # Header construction utilities
└── resources/
    ├── karate-config.js              # Global Karate initialization
    ├── test-config.json              # Shared URL/port configuration
    ├── application-int.properties    # Spring Boot integration profile
    ├── features/                     # Feature files (one per endpoint)
    │   ├── {resource}_get.feature
    │   ├── {resource}_post.feature
    │   └── {resource}_delete.feature
    ├── templates/                    # Expected response JSON templates
    │   └── expected_{scenario}.json
    └── wiremock/
        └── autoloaded/               # WireMock asset root (classpath-loaded)
            ├── mappings/             # JSON stub descriptors
            │   ├── {downstream}_happy_path.json
            │   ├── {downstream}_error_503.json
            │   └── {downstream}_not_found.json
            └── __files/              # Static payload body templates
                ├── {downstream}_response_200.json
                └── {downstream}_response_error.json
```

### 9.2 TestRunner.java Pattern

The runner orchestrates the full lifecycle: WireMock starts first, then Spring Boot boots against it, then Karate runs.

```java
package KarateTest;

import KarateTest.utils.WiremockRunner;
import com.barclays.api.Application;
import com.intuit.karate.junit5.Karate;
import java.io.IOException;
import org.junit.jupiter.api.*;
import org.springframework.boot.SpringApplication;
import org.springframework.context.ApplicationContext;

public class TestRunner {

    private static final WiremockRunner wiremock = new WiremockRunner();
    private static ApplicationContext context;

    @BeforeAll
    public static void beforeClass() throws IOException {
        System.setProperty("karate.env", "int");
        wiremock.startWiremock();
        context = SpringApplication.run(Application.class, "--spring.profiles.active=int");
    }

    @AfterAll
    public static void tearDown() {
        wiremock.stopWiremock();
        SpringApplication.exit(context);
    }

    @Karate.Test
    Karate runAllTests() {
        return Karate.run("classpath:features")
                .tags("@env=int", "~@ignore")
                .relativeTo(getClass());
    }
}
```

**Startup sequence:**
1. `WiremockRunner.startWiremock()` -- stubs loaded from classpath
2. `SpringApplication.run(...)` -- Spring wires downstream URLs to WireMock
3. `Karate.run(...)` -- feature files execute against the live Spring context

### 9.3 WiremockRunner.java Utility

```java
package KarateTest.utils;

import com.github.tomakehurst.wiremock.WireMockServer;
import com.github.tomakehurst.wiremock.core.WireMockConfiguration;
import java.io.IOException;

public class WiremockRunner {

    private WireMockServer wireMockServer;

    public void startWiremock() throws IOException {
        wireMockServer = new WireMockServer(
                WireMockConfiguration.wireMockConfig()
                        .port(32131)
                        .usingFilesUnderClasspath("wiremock/autoloaded")
        );
        wireMockServer.start();
    }

    public void stopWiremock() {
        if (wireMockServer != null && wireMockServer.isRunning()) {
            wireMockServer.stop();
        }
    }
}
```

### 9.4 karate-config.js Pattern

Runs before every feature. Reads shared config and exposes global variables.

```javascript
function fn() {
    var env = karate.env;
    karate.log('karate.env system property was:', env);
    if (!env) {
        env = 'dev';
    }
    var testConfig = karate.read('classpath:test-config.json');
    karate.log('applicationConfig:', testConfig);
    var config = {
        applicationUrl: testConfig.applicationUrl,
        wiremockPort: testConfig.wiremockPort
    };
    return config;
}
```

### 9.5 test-config.json Pattern

Centralized URL and port configuration. Both karate-config.js and feature files read from this source.

```json
{
  "applicationUrl": "http://localhost:19090/",
  "wiremockPort": "32131"
}
```

### 9.6 application-int.properties Pattern

```properties
# Fixed port matching test-config.json
server.port=19090

# CRITICAL: All downstream service URLs MUST point to WireMock
api.{downstream-name}.url=http://localhost:32131/{downstream-path}

# In-memory database for test isolation
app.datasource.hikari.jdbcUrl=jdbc:h2:mem:default;DB_CLOSE_DELAY=-1
spring.jpa.hibernate.ddl-auto=create-drop
spring.sql.init.mode=always

# WireMock classpath location
api.wiremock.files-classpath=wiremock/autoloaded

# Flag to enable test-specific behaviour
integration-test=true
```

> **CRITICAL:** Every external service URL MUST point to `http://localhost:32131/...`. Any URL not directed to WireMock will attempt a real network call, causing flaky or failing tests.

### 9.7 DataUtils.java Utility Pattern

Constructs DAF headers required for integration test requests.

```java
package KarateTest.utils;

import java.util.UUID;

public class DataUtils {

    public static String generateCorrelationId() {
        return UUID.randomUUID().toString();
    }

    public static String buildCustomerContext(String customerId, String customerType) {
        return String.format("{\"customerPk\":{\"id\":\"%s\",\"type\":\"%s\"}}", customerId, customerType);
    }

    public static String buildChannelContext(String channelId) {
        return String.format("{\"channelId\":\"%s\"}", channelId);
    }

    public static String buildSessionContext(String sessionId) {
        return String.format("{\"sessionId\":\"%s\"}", sessionId);
    }

    public static String buildEnvironmentContext(String environment) {
        return String.format("{\"environment\":\"%s\"}", environment);
    }

    public static String buildTestContext(String testbed) {
        return String.format("{\"testbed\":\"%s\"}", testbed);
    }

    public static String buildProfileContext(String personaId, String personaType) {
        return String.format("{\"personaId\":\"%s\",\"personaType\":\"%s\"}", personaId, personaType);
    }
}
```

### 9.8 Feature File Structure

One `.feature` file per endpoint. Each feature file covers the happy path plus error scenarios.

```gherkin
@env=int
Feature: {Resource} {Method} Integration Tests

  Background:
    * def testConfig = read('classpath:test-config.json')
    * def DataUtils = Java.type('KarateTest.utils.DataUtils')
    * configure ssl = true
    * configure readTimeout = 999999999
    * configure connectTimeout = 99999999
    * configure report = false
    Given url testConfig.applicationUrl
    And header Content-Type = 'application/json'
    * def correlationId = DataUtils.generateCorrelationId()
    * def authorizationToken = 'Bearer <base64-encoded-test-token>'

  Scenario: GET {resource} returns 200 with expected payload
    Given path '/{resource}/{identifier}'
    And header Authorization = authorizationToken
    And header Correlation-ID = correlationId
    And header ChannelContext = DataUtils.buildChannelContext('APP')
    And header CustomerContext = DataUtils.buildCustomerContext('{testCustomerId}', 'CUSTOMER_SYSTEM')
    And header ProfileContext = DataUtils.buildProfileContext('{testPersonaId}', 'CUS_ID')
    When method GET
    Then status 200
    And match response.data.items[0].id == '#notnull'

  Scenario: GET {resource} returns 403 when customer context does not match
    Given path '/{resource}/{identifier}'
    And header Authorization = authorizationToken
    And header Correlation-ID = correlationId
    And header ChannelContext = DataUtils.buildChannelContext('APP')
    And header CustomerContext = DataUtils.buildCustomerContext('{mismatchedCustomerId}', 'CUSTOMER_SYSTEM')
    When method GET
    Then status 403

  Scenario: GET {resource} returns 503 when downstream is unavailable
    Given path '/{resource}/{identifier}'
    And header Authorization = authorizationToken
    And header Correlation-ID = 'TRIGGER-503'
    And header ChannelContext = DataUtils.buildChannelContext('APP')
    And header CustomerContext = DataUtils.buildCustomerContext('{testCustomerId}', 'CUSTOMER_SYSTEM')
    When method GET
    Then status 503
```

### 9.9 Scenario Outline with Examples Table (Data-Driven)

```gherkin
  Scenario Outline: GET {resource} returns <expectedStatus> for <description>
    Given path '/{resource}/<resourceId>'
    And header Authorization = authorizationToken
    And header Correlation-ID = correlationId
    And header ChannelContext = DataUtils.buildChannelContext('<channel>')
    And header CustomerContext = DataUtils.buildCustomerContext('<customerId>', 'CUSTOMER_SYSTEM')
    When method GET
    Then status <expectedStatus>

    Examples:
      | resourceId | customerId  | channel | expectedStatus | description              |
      | RES-001    | 1234567890  | APP     | 200            | happy path               |
      | RES-999    | 1234567890  | APP     | 404            | resource not found       |
      | RES-001    | 9999999999  | APP     | 403            | unauthorized customer    |
      | RES-001    | 1234567890  | WEB     | 200            | alternate channel        |
```

### 9.10 WireMock Stub Patterns

#### Happy Path Stub (mappings/{downstream}_happy_path.json)

```json
{
  "request": {
    "method": "GET",
    "urlPattern": "/{downstream-path}/.*"
  },
  "response": {
    "status": 200,
    "headers": {
      "Content-Type": "application/json"
    },
    "bodyFileName": "{downstream}_response_200.json"
  }
}
```

#### Header-Based Routing for Error Scenarios

Route specific error scenarios using a unique header value without affecting the happy-path stub:

```json
{
  "priority": 1,
  "request": {
    "method": "GET",
    "urlPattern": "/{downstream-path}/.*",
    "headers": {
      "X-Correlation-ID": {
        "equalTo": "TRIGGER-503"
      }
    }
  },
  "response": {
    "status": 503,
    "headers": {
      "Content-Type": "application/json"
    },
    "jsonBody": {
      "error": "Service Unavailable",
      "code": "DOWNSTREAM_TIMEOUT"
    }
  }
}
```

> **Pattern:** Use `priority: 1` (higher priority) on error stubs and leave happy-path stubs at default priority. Use a specific header value (e.g., Correlation-ID = "TRIGGER-503") to route requests to error stubs.

#### Dynamic Response Templating

```json
{
  "request": {
    "method": "POST",
    "urlPattern": "/{downstream-path}/([A-Z0-9]+)"
  },
  "response": {
    "status": 200,
    "headers": {
      "Content-Type": "application/json"
    },
    "bodyFileName": "dynamic_response.json",
    "transformers": ["response-template"]
  }
}
```

`__files/dynamic_response.json`:
```json
{
  "entityId": "{{request.pathSegments.[1]}}",
  "correlationId": "{{request.headers.X-Correlation-ID}}",
  "processedAt": "{{now format='yyyy-MM-dd\\'T\\'HH:mm:ss\\'Z\\''}}"
}
```

#### Simulating Timeouts

```json
{
  "request": {
    "method": "GET",
    "urlPattern": "/{downstream-path}/slow/.*"
  },
  "response": {
    "status": 200,
    "fixedDelayMilliseconds": 5000,
    "jsonBody": { "status": "DELAYED" }
  }
}
```

### 9.11 Branch Coverage Strategy

| Branch Target                  | Karate Input                              | WireMock Stub                      | Expected Outcome                |
|--------------------------------|-------------------------------------------|------------------------------------|---------------------------------|
| Happy Path                     | Valid headers + payload                   | Returns 200 with valid body        | Assert status + response schema |
| Authorization Failure          | Missing or invalid Authorization header   | Not invoked (Spring rejects early) | Assert 401 or 403              |
| Resource Not Found             | Valid auth, unknown resource ID           | Returns 404 or not invoked         | Assert 404                      |
| Downstream Service Error       | Valid request + trigger header            | Returns 500 or 503                 | Assert error response structure |
| Business Rule Violation        | Valid auth, specific header combination   | Returns 422 or 409                 | Assert conflict/error body      |
| Conditional Logic via Headers  | Vary a specific header value per scenario | Stub matched by header value       | Assert different status         |
| Timeout / Retry                | Valid request                             | fixedDelayMilliseconds in stub     | Assert fallback/retry behaviour |

---

## Section 10: Unit Testing (Spock Framework)

This section documents generalizable patterns for writing Spock unit tests in DAF APIs. Tests are written in Groovy and use Spock's BDD-style blocks.

### 10.1 Service Unit Test Pattern (Mock Dependencies)

Instantiate the service implementation directly with mocked dependencies. No Spring context needed.

```groovy
package com.barclays.api.{domain}.service.impl

import com.barclays.api.{domain}.gateway.{Name}Gateway
import spock.lang.Specification

class {Name}ServiceImplTest extends Specification {

    {Name}Gateway {name}Gateway = Mock()
    {Name}ServiceImpl {name}Service = new {Name}ServiceImpl({name}Gateway)

    def "should return data for valid request"() {
        given:
        def requestId = "REQ-001"
        def expectedResponse = // build expected object

        {name}Gateway.{method}(requestId) >> expectedResponse

        when:
        def result = {name}Service.{method}(requestId)

        then:
        result != null
        result.getId() == requestId
    }

    def "should handle gateway exception gracefully"() {
        given:
        {name}Gateway.{method}(_) >> { throw new RuntimeException("Downstream failure") }

        when:
        def result = {name}Service.{method}("REQ-002")

        then:
        // Assert error response or exception depending on service design
        result != null
        !result.getErrors().isEmpty()
    }
}
```

### 10.2 Controller Test with MockMvc and @WebMvcTest

```groovy
package com.barclays.api.{domain}.controller

import org.spockframework.spring.SpringBean
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest
import org.springframework.context.annotation.ComponentScan
import org.springframework.test.context.ActiveProfiles
import org.springframework.test.util.ReflectionTestUtils
import org.springframework.test.web.servlet.MockMvc
import com.barclays.daf.exception.handler.DefaultExceptionHandlers
import com.barclays.daf.exception.messages.ErrorMessagesService
import spock.lang.Specification
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*

@ActiveProfiles("Test")
@WebMvcTest(controllers = {Name}Controller)
@AutoConfigureMockMvc
@ComponentScan(["com.barclays.api.bap.bld.*"])
class {Name}ControllerTest extends Specification {

    @Autowired
    private MockMvc mvc

    @SpringBean
    private {Name}Service {name}Service = Mock()

    @SpringBean
    private ErrorMessagesService messagesService = Mock()

    @SpringBean
    private DefaultExceptionHandlers defaultExceptionHandlers = new DefaultExceptionHandlers()

    def setup() {
        ReflectionTestUtils.setField(defaultExceptionHandlers, "messagesService", messagesService)
    }

    def "should return 200 for GET /{path}/{id}"() {
        given:
        def expected = // build expected response
        {name}Service.{method}(_) >> expected

        when:
        def result = mvc.perform(get("/{path}/{id}")).andReturn()

        then:
        result.response.status == 200
    }

    def "should return 404 when resource not found"() {
        given:
        {name}Service.{method}(_) >> { throw new ApiResourceNotFoundException() }

        when:
        def result = mvc.perform(get("/{path}/UNKNOWN")).andReturn()

        then:
        result.response.status == 404
    }
}
```

### 10.3 Data-Driven Testing with where Blocks

Use Spock data tables to cover multiple branches in a single test method.

```groovy
def "should correctly validate input for #description"() {
    given:
    def request = buildRequest(inputValue)

    when:
    def result = {name}Service.validate(request)

    then:
    result.isValid() == expectedValid

    where: 'Various inputs exercise different validation branches'
    inputValue    | expectedValid | description
    'VALID-001'   | true          | 'valid standard input'
    ''            | false         | 'empty string rejected'
    null          | false         | 'null rejected'
    'X' * 101     | false         | 'exceeds max length'
    'SPECIAL!@#'  | false         | 'invalid characters rejected'
}
```

**Key rules:**
- Single pipe `|` separates columns
- Double pipe `||` visually separates inputs from expected outputs
- The feature runs once per row
- Use `@Unroll` annotation to report each row as a separate test in build output

### 10.4 Mock and Stub Patterns

```groovy
// Create a mock
{Name}Gateway gateway = Mock()

// Stubbing -- return a fixed value
gateway.fetchData(_) >> expectedData

// Verification -- assert called exactly once with specific argument
1 * gateway.fetchData("REQ-001") >> expectedData

// Sequential stubbing -- different results per call
gateway.checkStatus() >>> ["PENDING", "COMPLETED"] >> { throw new RuntimeException("Timeout") }

// Argument constraints
1 * gateway.fetchData({ it.startsWith("REQ-") }) >> expectedData
```

### 10.5 Exception Testing

```groovy
def "should throw exception when input is invalid"() {
    given:
    def invalidInput = null

    when:
    {name}Service.process(invalidInput)

    then:
    def exception = thrown(IllegalArgumentException)
    exception.message == "Input must not be null"
}
```

### 10.6 Coverage Strategies

| Strategy | Pattern | Example |
|---|---|---|
| Branch coverage via data tables | One test with `where` block covering all if/else paths | See 10.3 |
| Void method verification | Assert mock interactions | `1 * gateway.sendNotification(*_)` |
| Exception paths | Use stubbing to throw, then assert `thrown()` | See 10.5 |
| Sequential behavior | Use `>>>` for ordered returns | `gateway.poll() >>> ["PENDING", "DONE"]` |
| Null/empty edge cases | Include null and empty in data tables | `null \| false \| 'null rejected'` |

### 10.7 Gateway Unit Test Pattern

```groovy
package com.barclays.api.{domain}.gateway.impl

import org.springframework.web.client.RestTemplate
import org.springframework.http.*
import spock.lang.Specification

class {Name}GatewayImplTest extends Specification {

    RestTemplate restTemplate = Mock()
    {Name}GatewayImpl gateway = new {Name}GatewayImpl(restTemplate)

    def setup() {
        gateway.apiUrl = "http://localhost:8080/{downstream-path}"
        gateway.apiMethod = "GET"
    }

    def "should return response when downstream returns 200"() {
        given:
        def expectedBody = // build expected response
        def responseEntity = new ResponseEntity<>(expectedBody, HttpStatus.OK)
        restTemplate.exchange(_, _, _, _) >> responseEntity

        when:
        def result = gateway.{method}("{id}")

        then:
        result != null
    }

    def "should throw exception when downstream returns error"() {
        given:
        restTemplate.exchange(_, _, _, _) >> { throw new HttpClientErrorException(HttpStatus.NOT_FOUND) }

        when:
        gateway.{method}("UNKNOWN")

        then:
        thrown(HttpClientErrorException)
    }
}
```

---

## Section 11: OAS Multi-File Structure

This section documents the generalizable multi-file OAS (OpenAPI Specification) structure for DAF APIs. The DAF framework provides two mandatory shared libraries that MUST NOT be modified.

### 11.1 Full Directory Structure

```
oas/
├── openapi.yaml                          # Main OAS entry point
├── common-libraries/                     # COPY AS-IS from DAF framework (NEVER modify)
│   ├── components/
│   │   ├── headers.yaml
│   │   ├── responses.yaml
│   │   └── response-types.yaml
│   ├── examples/
│   │   ├── example-error-400.json
│   │   ├── example-error-401.json
│   │   ├── example-error-403.json
│   │   ├── example-error-404.json
│   │   ├── example-error-429.json
│   │   ├── example-error-500.json
│   │   └── example-error-503.json
│   └── security/
│       └── security-schemes.yaml
├── daf-library/                          # COPY AS-IS from DAF framework (NEVER modify)
│   ├── daf-library-headers.yaml
│   └── daf-library-base-types.yaml
├── lib/                                  # YOUR API-specific definitions
│   ├── types.yaml                        # Shared field types (IDs, enums, primitives)
│   ├── request-types.yaml                # Request body schemas
│   └── response-types.yaml               # Response body schemas
└── examples/                             # YOUR API-specific JSON examples
    ├── get-{resource}-response-200.json
    └── post-{resource}-request.json
```

**Key rules:**
- `common-libraries/` is COPY AS-IS from the DAF OAS template repository. Never modify.
- `daf-library/` is COPY AS-IS from the DAF OAS template repository. Never modify.
- `lib/` contains YOUR API-specific type definitions. All custom schemas go here.
- `openapi.yaml` references all three directories via `$ref`.

### 11.2 openapi.yaml Structure

```yaml
openapi: 3.0.3
info:
  title: {Your-API-Name}
  description: |-
    -**API Type:** Internal | External
    -**API Risk Classification:** LOW | MEDIUM | HIGH
    -**API Owner (business):** {team-code}
    -**API Owner (technical):** {owner-name}
    -**API Overview:** {Brief description of what this API does}
  contact:
    name: '{Your Team Name}'
    email: '{team-email@barclays.com}'
  version: 'v{version}'

servers:
  - url: 'https://{gateway-host}/{your-api-name}/'
    description: SIT Server URL

security:
  - InternalTiaaUsRopcAuth: []

components:
  securitySchemes:
    InternalTiaaUsRopcAuth:
      $ref: './common-libraries/security/security-schemes.yaml#/InternalTiaaUsRopcAuth'

  headers:
    Cache-Control:
      $ref: './common-libraries/components/headers.yaml#/Cache-Control'

  responses:
    BadRequest:
      $ref: './common-libraries/components/responses.yaml#/BadRequest'
    Unauthorized:
      $ref: './common-libraries/components/responses.yaml#/Unauthorized'
    Forbidden:
      $ref: './common-libraries/components/responses.yaml#/Forbidden'
    NotFound:
      $ref: './common-libraries/components/responses.yaml#/NotFound'
    TooManyRequests:
      $ref: './common-libraries/components/responses.yaml#/TooManyRequests'
    InternalServerError:
      $ref: './common-libraries/components/responses.yaml#/InternalServerError'
    ServiceUnavailable:
      $ref: './common-libraries/components/responses.yaml#/ServiceUnavailable'

  schemas:
    {YourRequestType}:
      $ref: './lib/request-types.yaml#/{YourRequestType}'
    {YourResponseType}:
      $ref: './lib/response-types.yaml#/{YourResponseType}'
```

### 11.3 Mandatory Headers Per Endpoint

Every endpoint MUST include at minimum `Correlation-ID`. Add DAF context headers as required:

```yaml
paths:
  /{resource}/{resourceId}:
    summary: {Brief description}
    parameters:
      # Path parameters first
      - name: resourceId
        in: path
        required: true
        description: "The unique resource identifier"
        schema:
          $ref: './lib/types.yaml#/resourceId'
        example: "ABC123"
      # Mandatory headers
      - $ref: './common-libraries/components/headers.yaml#/Correlation-ID'
      - $ref: './daf-library/daf-library-headers.yaml#/ChannelContext'
      - $ref: './daf-library/daf-library-headers.yaml#/CustomerContext'
      # Optional headers last
      - $ref: './daf-library/daf-library-headers.yaml#/Optional_TestContext'
```

**Available DAF context headers:**

| Header               | Reference                                  | Usage              |
|----------------------|--------------------------------------------|--------------------|
| Correlation-ID       | common-libraries/components/headers.yaml   | Always required    |
| ChannelContext       | daf-library/daf-library-headers.yaml       | Per business need  |
| CustomerContext      | daf-library/daf-library-headers.yaml       | Per business need  |
| AccountContext       | daf-library/daf-library-headers.yaml       | Per business need  |
| SessionContext       | daf-library/daf-library-headers.yaml       | Per business need  |
| ProfileContext       | daf-library/daf-library-headers.yaml       | Per business need  |
| Optional_TestContext | daf-library/daf-library-headers.yaml       | Non-prod only      |

### 11.4 Standard Error Responses

Every endpoint MUST include all standard error responses:

```yaml
    get:
      operationId: get{Resource}ById
      summary: Retrieve {resource} by ID
      responses:
        '200':
          description: Successful response
          headers:
            Cache-Control:
              $ref: './common-libraries/components/headers.yaml#/Cache-Control'
          content:
            application/json:
              schema:
                $ref: './lib/response-types.yaml#/{YourResponse}'
              examples:
                example-response:
                  $ref: './examples/get-{resource}-response-200.json'
        '400':
          $ref: '#/components/responses/BadRequest'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '403':
          $ref: '#/components/responses/Forbidden'
        '404':
          $ref: '#/components/responses/NotFound'
        '429':
          $ref: '#/components/responses/TooManyRequests'
        '500':
          $ref: '#/components/responses/InternalServerError'
        '503':
          $ref: '#/components/responses/ServiceUnavailable'
```

### 11.5 Defining Your Own Types (lib/types.yaml)

Apply maximum validation constraints on every field:

```yaml
resourceId:
  type: string
  description: The unique identifier for the resource
  pattern: "^[A-Za-z0-9\\-]{1,36}$"
  minLength: 1
  maxLength: 36
  nullable: false
  example: "ABC-12345"

amount:
  type: number
  format: double
  description: Monetary amount
  minimum: 0.00
  maximum: 999999999.99
  example: 100.50

statusCode:
  type: string
  description: Status of the resource
  enum:
    - ACTIVE
    - INACTIVE
    - PENDING
  example: ACTIVE
```

**Field validation checklist (EVERY field must have):**
- `type` declared
- `description` provided
- `pattern` for strings (regex)
- `minLength` / `maxLength` for strings
- `minimum` / `maximum` for numbers
- `nullable` explicitly set
- `example` provided
- `enum` used where values are finite

### 11.6 Request Types (lib/request-types.yaml)

```yaml
{CreateResourceRequest}:
  type: object
  additionalProperties: false
  description: Request body for creating a resource
  required:
    - name
    - type
  properties:
    name:
      type: string
      description: Name of the resource
      pattern: "^[A-Za-z0-9 \\-]{1,100}$"
      minLength: 1
      maxLength: 100
      nullable: false
      example: "My Resource"
    type:
      type: string
      description: Type classification
      pattern: "^[A-Z_]{1,20}$"
      minLength: 1
      maxLength: 20
      nullable: false
      example: "TYPE_A"
    optionalNote:
      type: string
      description: Optional free-text note
      pattern: "^[A-Za-z0-9 .,]{0,250}$"
      minLength: 0
      maxLength: 250
      nullable: true
      example: "Some note"
```

### 11.7 Response Types (lib/response-types.yaml)

```yaml
{MyResponse}:
  type: object
  additionalProperties: false
  deprecated: false
  nullable: false
  description: Standard response for resource retrieval
  properties:
    resourceId:
      type: string
      pattern: "^[A-Za-z0-9\\-]{1,36}$"
      minLength: 1
      maxLength: 36
      nullable: false
      example: "ABC-12345"
    status:
      type: string
      enum:
        - ACTIVE
        - INACTIVE
      nullable: false
      example: ACTIVE
    items:
      type: array
      minItems: 0
      maxItems: 100
      nullable: true
      items:
        $ref: '#/{ResourceItem}'

{ResourceItem}:
  type: object
  additionalProperties: false
  required:
    - id
    - value
  properties:
    id:
      type: string
      pattern: "^[A-Za-z0-9]{1,50}$"
      minLength: 1
      maxLength: 50
      nullable: false
      example: "ITEM001"
    value:
      type: string
      pattern: "^[A-Za-z0-9 ]{1,100}$"
      minLength: 1
      maxLength: 100
      nullable: false
      example: "Item value"
```

### 11.8 Key Rules Summary

| Rule | Detail |
|------|--------|
| Never modify `common-libraries/` or `daf-library/` | These are framework-owned. Raise a PR to `oas-template` for fixes. |
| Always use `$ref` | Never copy-paste shared definitions inline. |
| `Cache-Control` on every response | Required by GIS compliance. |
| `additionalProperties: false` on all object schemas | Prevents unexpected fields. |
| Explicit `nullable` on every property | Avoids ambiguity in code generation. |
| `pattern`, `minLength`, `maxLength` on every string | Maximum validation enforcement. |
| `operationId` must be unique and camelCase | Used for SDK code generation. |
| Include ALL standard error responses | 400, 401, 403, 404, 429, 500, 503 on every endpoint. |
| `Optional_TestContext` only on non-production paths | Never include in production-only endpoints. |

---

## Section 6: DAF Gradle Starter Plugin DSL Reference

The `com.barclays.digital.daf.starter` plugin (version defined in the cloned template's `gradle.properties` as `DAF_PLUGIN_VERSION` — do NOT hardcode) provides automatic configuration for testing, coverage, mutation testing, and code quality. Services MUST use the `daf{}` DSL block in `build.gradle` instead of raw Gradle configuration blocks.

### What the Plugin Provides Automatically

The DAF starter plugin auto-configures the following when `daf.autoConfigure.enabled = true`:

| Feature | What It Does | Raw Equivalent (DO NOT USE) |
|---------|-------------|----------------------------|
| Unit test setup | Configures `test { useJUnitPlatform() }`, Spock framework | Raw `test {}` block |
| JaCoCo coverage | Configures `jacoco`, `jacocoTestReport`, `jacocoTestCoverageVerification` | Raw `jacoco {}`, `jacocoTestReport {}`, `jacocoTestCoverageVerification {}` blocks |
| Pitest mutation testing | Adds pitest plugin, configures `pitest {}` task, adds JUnit5 plugin dependency | Raw `id 'info.solidsoft.pitest'`, raw `pitest {}` block |
| Integration test source set | Configures `sourceSets { integrationTest {} }`, task, and configuration inheritance | Raw `sourceSets {}`, `configurations {}`, `task integrationTest` blocks |
| Sonar analysis | Configures SonarQube integration | Raw `sonarqube {}` block |
| `afterEvaluate` overrides | Re-enables pitest and coverage verification (overriding any plugin defaults) | Raw `afterEvaluate {}` block |
| `check.dependsOn` wiring | Wires coverage verification into the build lifecycle | Raw `check.dependsOn jacocoTestCoverageVerification` |

### The `daf{}` DSL Block (Correct Pattern)

```groovy
daf {
    autoConfigure { enabled = true }
    test {
        unitTest {
            // JaCoCo line coverage minimum (0.0 to 1.0)
            violationRuleLimitMinimum = 0.90
            // Packages excluded from coverage checks (DTOs, POJOs, exceptions have no logic)
            violationRuleExcludes = ['**/dto/**', '**/model/**', '**/pojo/**', '**/bean/**', '**/exception/**']
        }
        integrationTest {
            // Separate coverage threshold for integration tests
            violationRuleLimitMinimum = 0.70
        }
        pitest {
            // Classes to mutate
            targetClasses = ['com.barclays.api.*']
            // Classes to exclude from mutation (no business logic)
            excludedClasses = [
                'com.barclays.api.*.dto.*',
                'com.barclays.api.*.model.*',
                'com.barclays.api.*.pojo.*',
                'com.barclays.api.*.bean.*',
                'com.barclays.api.*.exception.*'
            ]
            // Minimum percentage of mutations that must be killed
            mutationThreshold = 90
        }
    }
    sonar {
        // SonarQube project key (from spec)
        projectKey = 'my-service-key'
        // SonarQube project display name
        projectName = 'My Service'
        // Paths excluded from analysis (same as coverage excludes)
        exclusions = ['**/dto/**', '**/model/**', '**/pojo/**', '**/bean/**', '**/exception/**']
    }
}
```

### PROHIBITED Patterns (Must NOT appear in build.gradle)

The following raw Gradle blocks MUST NOT be present when using the DAF starter plugin. They conflict with or duplicate the plugin's auto-configuration:

| Prohibited Block | Why | Correct Alternative |
|-----------------|-----|-------------------|
| `plugins { id 'info.solidsoft.pitest' ... }` | Plugin bundles pitest | Use `daf.test.pitest {}` DSL |
| `pitest { ... }` (raw, outside `daf{}`) | Conflicts with plugin config | Use `daf.test.pitest {}` DSL |
| `jacoco { ... }` | Plugin configures JaCoCo | Use `daf.test.unitTest.violationRuleLimitMinimum` |
| `test { useJUnitPlatform(); finalizedBy ... }` | Plugin configures test task | Automatic via `daf.autoConfigure.enabled = true` |
| `jacocoTestReport { ... }` | Plugin configures reporting | Automatic |
| `jacocoTestCoverageVerification { ... }` | Plugin configures verification | Use `daf.test.unitTest.violationRuleLimitMinimum` and `violationRuleExcludes` |
| `afterEvaluate { ... }` | Plugin handles task re-enablement | Automatic |
| `check.dependsOn jacocoTestCoverageVerification` | Plugin wires lifecycle | Automatic |
| `sourceSets { integrationTest { ... } }` | Plugin provides source set | Automatic |
| `testImplementation 'org.pitest:pitest-junit5-plugin:...'` | Plugin provides dependency | Automatic |

### Minimal Correct build.gradle

```groovy
plugins {
    id 'com.barclays.digital.daf.starter' version "${DAF_PLUGIN_VERSION}"
}

group = "${GROUP_ID}"
version = "${VERSION}"

apply from: 'daf-dependencies.gradle'

daf {
    autoConfigure { enabled = true }
    test {
        unitTest {
            violationRuleLimitMinimum = 0.90
            violationRuleExcludes = ['**/dto/**', '**/model/**', '**/pojo/**', '**/bean/**', '**/exception/**']
        }
        integrationTest { violationRuleLimitMinimum = 0.70 }
        pitest {
            targetClasses = ['com.barclays.api.*']
            excludedClasses = ['com.barclays.api.*.dto.*', 'com.barclays.api.*.model.*', 'com.barclays.api.*.pojo.*', 'com.barclays.api.*.bean.*', 'com.barclays.api.*.exception.*']
            mutationThreshold = 90
        }
    }
    sonar {
        projectKey = '{from-spec}'
        projectName = '{from-spec}'
        exclusions = ['**/dto/**', '**/model/**', '**/pojo/**', '**/bean/**', '**/exception/**']
    }
}
```

### Key Points for All Agents

1. **Build agent**: Generate ONLY the minimal build.gradle shown above. No raw test/coverage/pitest blocks.
2. **Test agent**: Do NOT add pitest dependencies to `daf-dependencies.gradle` — the plugin provides them.
3. **Orchestrator Phase 0**: Validate `daf {}` block exists; reject if raw blocks are present.
4. **Validation agent**: Red Flag #17 checks for prohibited patterns.

## Source Attribution

**Primary sources:**
- Barclays DAF plugin documentation (internal Confluence pages, BUK API Engineering team)
- SDK3 BOM 1.6.001 release notes — version table for `daf-gradle-starter-plugin`, `SDK3_VERSION`, `DAF_PLUGIN_VERSION`
- DAF template repository (`git@app.gitlab.barcapint.com:vishal.khare1/daf-template.git`) — structure, module catalog, config patterns
- Production DAF service implementations reviewed by BUK API Engineering — lessons learned section (Section 5)

**Training knowledge applied:**
- Spring Boot 3 property binding (`@ConfigurationProperties`, `@Value`)
- Spring Retry (`@Retryable`, `@Recover`, `@Backoff`) patterns
- DAF `daf {}` DSL block semantics inferred from template `build.gradle` examples

**Known limitations:**
- Version table was last verified on 2026-07-17; values must be re-verified against the DAF template `gradle.properties` before use in production
- Module catalog in Section 2 reflects modules available at review date; newly released DAF modules will not appear until this skill is updated
- Lessons learned (Section 5) are drawn from known incidents; new patterns learned in production may not be captured until the next review cycle

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] Are all version numbers sourced from this skill's version table (Section 1–2) and not from training data or assumptions?
- [ ] Is the DAF plugin version in build.gradle sourced from gradle.properties (not hardcoded)?
- [ ] Are all SDK3 BOM coordinates referencing the version declared in this skill?
- [ ] Is the domain-reference skill version table current (checked against the DAF plugin release)?
- [ ] Are all mandatory DAF DSL patterns (daf {} block, not raw jacoco/pitest blocks) applied?
