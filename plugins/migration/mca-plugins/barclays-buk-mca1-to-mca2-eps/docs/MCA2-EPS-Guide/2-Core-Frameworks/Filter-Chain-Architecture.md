# Filter Chain Architecture

## Executive Summary

The **Filter Chain** is the foundational request processing mechanism in MCA2, implementing the **Chain of Responsibility** design pattern to execute ordered filters for systematic HTTP request/response handling. It provides the infrastructure for cross-cutting concerns like request tracing, exception handling, input validation, and security enforcement.

**Key Characteristics:**
- **13 core filters** with precise execution ordering
- **Chain of Responsibility pattern** for composable request processing
- **OncePerRequestFilter base class** ensures each filter runs exactly once per request
- **Configurable ordering** via Spring's FilterRegistrationBean
- **Exception wrapping** ensures errors are handled consistently
- **Extension mechanism** for custom application filters

---

## Filter Chain: High-Level Flow

```
┌────────────────────────────────────────────────────────┐
│ HTTP Request Arrives                                   │
└────────────┬───────────────────────────────────────────┘
             │
    ┌────────▼─────────────────────────────────────────┐
    │ Filter Chain Execution (CoreFilterConfig)         │
    │ Each filter in order: doFilterInternal()          │
    │                                                   │
    │  1. CorrelationIdFilter (Order 0)               │
    │  2. ExceptionFilter (Order 1)                   │
    │  3. DisableSessionFilter (Order 2)              │
    │  4. MultiReadRequestFilter (Order 3)            │
    │  5. [Conditional Filters - Order 4+]            │
    │     - OAuthValidatorFilter                       │
    │     - DdosFilter                                 │
    │     - ValidationFilter                           │
    │     - RequestWhitelistingFilter                  │
    │     - DynamicLoggingFilter                       │
    │     - PerfLogExclusionFilter                     │
    │  6. [Custom Application Filters - Order 10+]    │
    │                                                   │
    │  Entry point: First filter's doFilterInternal()  │
    │  Chain parameter: Calls filterChain.doFilter()   │
    │                  to pass to next filter           │
    └────────┬──────────────────────────────────────────┘
             │
    ┌────────▼──────────────────────────────────────────┐
    │ DispatcherServlet Routes to Handler               │
    │ (Controller/Handler method)                       │
    └────────┬──────────────────────────────────────────┘
             │
    ┌────────▼──────────────────────────────────────────┐
    │ Business Logic Executes                           │
    │ (May throw exceptions)                            │
    └────────┬──────────────────────────────────────────┘
             │
    ┌────────▼──────────────────────────────────────────┐
    │ Response Generation                               │
    │ (Response<T> envelope or error)                   │
    └────────┬──────────────────────────────────────────┘
             │
    ┌────────▼──────────────────────────────────────────┐
    │ Filter Chain RESPONSE Phase                       │
    │ (Reverse order - outer filters last)             │
    │                                                   │
    │  ExceptionFilter catches exceptions              │
    │  Response interceptors process response          │
    │  Headers/content-type set                        │
    └────────┬──────────────────────────────────────────┘
             │
    ┌────────▼──────────────────────────────────────────┐
    │ HTTP Response Returns to Client                   │
    └────────────────────────────────────────────────────┘
```

---

## Core Filters: 13 Implementations

### Module Location
**Location:** `mca-libraries/filter-core/src/main/java/com/barclays/global/mca/libs/filters/`

### Execution Order (Request Phase)

The **first filter to execute is CorrelationIdFilter (Order 0)**, then each subsequent filter in order.

#### **ORDER 0: CorrelationIdFilter**

**Class:** `com.barclays.global.mca.libs.filters.CorrelationIdFilter`
**Purpose:** Generate and propagate request IDs for distributed tracing
**Module:** mca-filter-core

**Responsibilities:**
1. Generate unique correlation ID (UUID or custom format)
2. Extract existing correlation ID from `Correlation-ID` header if present
3. Add to thread-local context for access by all downstream components
4. Set response header with correlation ID
5. Duration tracking (request start time)
6. Thread naming for thread pools

**Configuration:**
```properties
# application.properties
filter.correlationid.enabled=true  # Default: true
filter.correlationid.header.name=Correlation-ID
```

> **Note:** The deprecated `X-CorrelationId` header is also supported for backward compatibility.

**Code Example (mca-filter-core):**
```java
public class CorrelationIdFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {

        String correlationId = request.getHeader("Correlation-ID");
        if (correlationId == null) {
            correlationId = UUID.randomUUID().toString();
        }

        // Store in thread-local
        CorrelationIdContext.set(correlationId);

        // Add to response header
        response.setHeader("Correlation-ID", correlationId);

        try {
            // Set thread name for thread pools
            Thread.currentThread().setName(correlationId);

            // Continue chain
            filterChain.doFilter(request, response);
        } finally {
            CorrelationIdContext.clear();
        }
    }
}
```

**Output:**
```
Response Header: Correlation-ID: 550e8400-e29b-41d4-a716-446655440000
Logs: [550e8400-...] Request processing started
```

---

#### **ORDER 1: ExceptionFilter**

**Class:** `com.barclays.global.mca.libs.filters.ExceptionFilter`
**Purpose:** Wrap filter chain and catch all exceptions for centralized error handling
**Module:** mca-filter-core

**Responsibilities:**
1. Wrap entire filter chain in try-catch
2. Convert exceptions to Response<T> error envelopes
3. Map GenericException subclasses to HTTP status codes
4. Log exceptions with correlation ID
5. Return structured error response

**Configuration:**
```properties
# application.properties
filter.exception.enabled=true  # Default: true
filter.exception.stack-trace-enabled=false  # Include stack traces in response?
```

**Code Example (mca-filter-core):**
```java
public class ExceptionFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {

        try {
            filterChain.doFilter(request, response);
        } catch (Exception ex) {
            // Map exception to Response<T>
            Response<?> errorResponse = mapExceptionToResponse(ex);

            // Set HTTP status
            response.setStatus(
                ResponseHttpStatus.getStatusCode(ex)  // Uses exception class
            );

            // Write JSON response
            response.setContentType("application/json");
            response.getWriter().write(
                objectMapper.writeValueAsString(errorResponse)
            );

            // Log with correlation ID
            logger.error(
                "Exception in request: {}",
                CorrelationIdContext.get(),
                ex
            );
        }
    }

    private Response<?> mapExceptionToResponse(Exception ex) {
        if (ex instanceof NotFoundException) {
            return Response.assemble()
                .error(List.of(
                    new Message("NOT_FOUND", ex.getMessage())
                ))
                .withStatusCode(404);
        }
        // ... handle other exception types
    }
}
```

**Output:**
```json
HTTP/1.1 404 Not Found

{
  "data": null,
  "messages": [
    {
      "code": "NOT_FOUND",
      "message": "Customer not found",
      "severity": "ERROR"
    }
  ],
  "status": "ERROR",
  "statusCode": "404"
}
```

---

#### **ORDER 2: DisableSessionFilter**

**Class:** `com.barclays.global.mca.libs.filters.DisableSessionFilter`
**Purpose:** Prevent unwanted HTTP session creation for stateless APIs
**Module:** mca-filter-core

**Responsibilities:**
1. Wrap HttpServletRequest to prevent session creation
2. Raise exception if `getSession()` is called
3. Allow `getSession(false)` reads but prevent creation

**Configuration:**
```properties
# application.properties
filter.disable-session.enabled=true  # Default: true
```

**Benefits:**
- Prevents memory leaks from abandoned sessions
- Enforces stateless architecture
- Reduces memory footprint
- Catches accidental session usage in code

**Code Example (mca-filter-core):**
```java
public class DisableSessionFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {

        HttpServletRequestDisableSessionWrapper wrapped =
            new HttpServletRequestDisableSessionWrapper(request);

        filterChain.doFilter(wrapped, response);
    }
}

// Wrapper class
public class HttpServletRequestDisableSessionWrapper
    extends HttpServletRequestWrapper {

    @Override
    public HttpSession getSession() {
        throw new IllegalStateException(
            "Session creation disabled for stateless API"
        );
    }

    @Override
    public HttpSession getSession(boolean create) {
        if (create) {
            throw new IllegalStateException(
                "Session creation disabled"
            );
        }
        return super.getSession(false);  // Allow reads
    }
}
```

---

#### **ORDER 3: MultiReadRequestFilter**

**Class:** `com.barclays.global.mca.libs.filters.MultiReadRequestFilter`
**Purpose:** Enable request body re-reading for logging and validation
**Module:** mca-filter-core

**Responsibilities:**
1. Wrap request to cache request body
2. Make body readable multiple times
3. Used by logging, validation filters
4. Support for multipart requests

**Configuration:**
```properties
# application.properties
filter.multiread.enabled=true  # Default: true
filter.multiread.max-buffer-size=1048576  # 1MB
```

**Why Needed:**
- InputStream can only be read once
- Logging needs to read body without consuming it
- Validation needs request body
- Handlers need request body

**Code Example (mca-filter-core):**
```java
public class MultiReadRequestFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {

        MultiReadRequestWrapper wrapped =
            new MultiReadRequestWrapper(request);

        filterChain.doFilter(wrapped, response);
    }
}

// Wrapper implementation
public class MultiReadRequestWrapper
    extends HttpServletRequestWrapper {

    private byte[] cachedBody;

    @Override
    public ServletInputStream getInputStream() throws IOException {
        if (cachedBody == null) {
            // Cache body on first read
            byte[] body = super.getInputStream()
                .readAllBytes();
            cachedBody = body;
        }
        // Return new stream over cached body
        return new CachedBodyInputStream(cachedBody);
    }

    @Override
    public BufferedReader getReader() throws IOException {
        // Support multiple calls to getReader()
        return new BufferedReader(
            new InputStreamReader(getInputStream())
        );
    }
}
```

**Usage Scenario:**
```
First read (by logging filter):  Request body → log message
Second read (by handler):        Request body → parse JSON to object
Third+ read (by validations):    Request body → validate schema
```

---

#### **ORDER 4+: Conditional Filters**

These filters are conditionally registered based on configuration.

##### **OAuthValidatorFilter**

**Class:** `com.barclays.global.mca.libs.filters.OAuthValidatorFilter`
**Purpose:** Validate JWT/OAuth tokens
**Enabled:** `@ConditionalOnProperty(name = "oauth.validation.enabled")`

**Responsibilities:**
- Extract JWT from `Authorization: Bearer` header
- Validate token signature
- Extract claims
- Populate security context

**Configuration:**
```properties
# application.properties
oauth.validation.enabled=true
oauth.jwt.issuer=https://auth.example.com
oauth.jwt.audience=api.example.com
```

##### **DdosFilter**

**Class:** `com.barclays.global.mca.libs.filters.DdosFilter`
**Purpose:** Prevent DDoS attacks via rate limiting
**Enabled:** `@ConditionalOnProperty(name = "ddos.prevention.enabled")`

**Responsibilities:**
- Rate limiting per IP/user/channel
- Track request frequency
- Block excessive requests
- Return 429 Too Many Requests

**Configuration:**
```properties
# application.properties
ddos.prevention.enabled=true
ddos.requests-per-minute=1000
ddos.block-duration-seconds=60
```

**Strategy Pattern:**
```java
// Strategy interface in mca-filter-core
public interface DdosPreventor {
    boolean isAllowed(HttpServletRequest request);
}

// Implementations
public class DefaultAllowAllRequestDdosPreventor
    implements DdosPreventor {

    @Override
    public boolean isAllowed(HttpServletRequest request) {
        return true;  // Allow all requests
    }
}

public class ChannelPropositionBasedDdosPreventor
    implements DdosPreventor {

    @Override
    public boolean isAllowed(HttpServletRequest request) {
        // Rate limit by channel/proposition
        IOLSchema context = WebUtils.getIOLSchema();
        return rateLimiter.isAllowed(
            context.getChannel()
        );
    }
}
```

##### **ValidationFilter (OAS Validation)**

**Class:** `com.barclays.global.mca.libs.filters.ValidationFilter`
**Purpose:** Validate HTTP requests against OpenAPI 3.0 specifications before they reach the controller
**Order:** 300
**Enabled:** `@ConditionalOnProperty(name = "core.default.oas.enabled")`
**Module:** mca-filter-core (validation engine in mca-oas-validation)

The ValidationFilter integrates the **Atlassian swagger-request-validator** library to perform comprehensive request validation against an OpenAPI 3.0 specification at the servlet filter level. This ensures malformed or non-conforming requests are rejected (or flagged) before reaching business logic.

**Responsibilities:**
- Validate HTTP request method, path, query parameters, headers, and body against an OpenAPI 3.0 spec
- Perform JSON schema validation on request bodies
- Operate in **blocking mode** (reject invalid requests with 400) or **reporting-only mode** (log warnings, allow request through)
- Check for the `X-SchemaValidated` header to skip redundant validation (e.g., when an upstream gateway has already validated)
- Exclude configurable paths from validation (default: `/actuator/**`, `/process/**`)
- Delegate to `OASRequestValidation` from the `mca-oas-validation` module for the core validation logic

**How It Works:**
```
1. Request arrives at ValidationFilter (Order 300)
2. Check if path matches exclusion patterns → skip if matched
3. Check for X-SchemaValidated header → skip if present (unless alwaysValidate=true)
4. Load OpenAPI spec via OasProvider (SimpleOasProvider or EmptyOasProvider)
5. Validate request against spec using Atlassian swagger-request-validator
6. Build OasValidationResult with status, errors, and messages
7. If blockingMode=true and errors found → throw RequestException (400 Bad Request)
8. If blockingMode=false and errors found → log warnings, continue chain
9. If valid → continue to next filter
```

**Configuration Properties:**
```yaml
core:
  default:
    oas:
      enabled: true                          # Enable OAS validation (default: false)
      path: classpath:openapi/api-spec.yaml  # Path to OpenAPI YAML/JSON file
      version: "3.0"                         # OAS version identifier
      ignore-missing-schema: false           # Don't fail if schema missing (default: false)
      blockingMode: true                     # Block requests on validation errors (default: false)
      excludedHeaders:                       # Headers to exclude from validation
        - X-Internal-Token
        - X-Trace-Id
      alwaysValidate: false                  # Force validation even if already validated (default: false)
    validation-filter:
      exclude:
        paths: /actuator/**,/process/**      # Paths to skip validation (default)
```

**OasProvider Strategy Pattern:**
```java
// Strategy interface for loading OpenAPI specs
public interface OasProvider {
    OpenApiInteractionValidator getValidator();
}

// Production implementation: loads spec from Spring Resource
public class SimpleOasProvider implements OasProvider {
    // Loads OpenAPI YAML/JSON from classpath or file path
    // Configured via core.default.oas.path
}

// No-op implementation: used when validation is disabled
public class EmptyOasProvider implements OasProvider {
    // Returns null validator; ValidationFilter skips validation
}
```

**Code Example - ValidationFilter Processing:**
```java
public class ValidationFilter extends OncePerRequestFilter {

    private final OASRequestValidation oasRequestValidation;
    private final boolean blockingMode;
    private final boolean alwaysValidate;
    private final AntPathMatcher pathMatcher = new AntPathMatcher();
    private final List<String> excludedPaths;

    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {

        String requestPath = request.getRequestURI();

        // Skip excluded paths (e.g., /actuator/**, /process/**)
        if (isExcludedPath(requestPath)) {
            filterChain.doFilter(request, response);
            return;
        }

        // Skip if already validated upstream (unless alwaysValidate)
        if (!alwaysValidate && request.getHeader("X-SchemaValidated") != null) {
            filterChain.doFilter(request, response);
            return;
        }

        // Perform OAS validation
        OasValidationResult result = oasRequestValidation.validate(request);

        if (result.hasErrors()) {
            if (blockingMode) {
                // Reject the request with 400 Bad Request
                throw new RequestException(
                    "OAS validation failed: " + result.getMessages()
                );
            } else {
                // Log warning but allow request through
                logger.warn("OAS validation errors: {}", result.getMessages());
            }
        }

        filterChain.doFilter(request, response);
    }
}
```

**Example OpenAPI Spec (referenced by `core.default.oas.path`):**
```yaml
openapi: 3.0.3
info:
  title: Card Control API
  version: 1.0.0
paths:
  /api/v1/cards/{cardId}/controls:
    get:
      parameters:
        - name: cardId
          in: path
          required: true
          schema:
            type: string
            pattern: "^[0-9]{16}$"
      responses:
        '200':
          description: Card controls retrieved
    post:
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CardControlRequest'
      responses:
        '201':
          description: Control created
components:
  schemas:
    CardControlRequest:
      type: object
      required:
        - controlType
        - enabled
      properties:
        controlType:
          type: string
          enum: [CONTACTLESS, ONLINE, ATM, INTERNATIONAL]
        enabled:
          type: boolean
        limit:
          type: number
          minimum: 0
```

**Filter Chain Position:**
```
Order 100: ContextFilter
    → Order 150: DdosFilter
        → Order 200: DynamicLoggingFilter
            → Order 300: ValidationFilter (OAS) ← HERE
                → Order 550: PerfLogExclusionFilter
                    → Controller
```

##### **RequestWhitelistingFilter**

**Class:** `com.barclays.global.mca.libs.filters.RequestWhitelistingFilter`
**Purpose:** Whitelist allowed request endpoints
**Enabled:** `@ConditionalOnProperty(name = "request.whitelist.enabled")`

**Responsibilities:**
- Maintain whitelist of allowed endpoints
- Return 403 Forbidden for non-whitelisted requests
- Support wildcard patterns

##### **DynamicLoggingFilter**

**Class:** `com.barclays.global.mca.libs.filters.DynamicLoggingFilter`
**Purpose:** Dynamically adjust log levels at runtime
**Enabled:** `@ConditionalOnProperty(name = "dynamic-logging.enabled")`

**Responsibilities:**
- Accept log level changes via headers/properties
- Apply to current request context
- Integrate with SLF4J/Log4j

**Configuration:**
```properties
# Request header or property
X-Log-Level: DEBUG
X-Log-Category: com.barclays.global.mca
```

##### **PerfLogExclusionFilter**

**Class:** `com.barclays.global.mca.libs.filters.PerfLogExclusionFilter`
**Purpose:** Exclude specific requests from performance logging
**Enabled:** `@ConditionalOnProperty(name = "perf-log.exclusions.enabled")`

**Responsibilities:**
- Skip performance logging for health checks
- Exclude static resources
- Exclude metrics endpoints

**Configuration:**
```properties
# application.properties
perf-log.exclusions.paths=/actuator/health,/swagger-ui.html
```

---

#### **ORDER 10+: Custom Application Filters**

Applications can register custom filters with order >= 10:

```java
@Configuration
public class ApplicationFilterConfig {

    @Bean
    public FilterRegistrationBean<CustomAuthFilter>
        customAuthFilter() {

        FilterRegistrationBean<CustomAuthFilter> bean =
            new FilterRegistrationBean<>(new CustomAuthFilter());

        bean.setOrder(11);  // After core filters
        bean.addUrlPatterns("/api/*");

        return bean;
    }
}

public class CustomAuthFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {

        // Custom authentication logic

        filterChain.doFilter(request, response);
    }
}
```

---

## Core Filter Configuration

### Filter Registration (CoreFilterConfig)

**Location:** `mca-libraries/mca-eps-core/src/main/java/.../config/CoreFilterConfig.java`

**Responsibilities:**
- Register all 13 core filters
- Set execution order
- Apply URL patterns
- Enable/disable based on properties

**Code Pattern (mca-eps-core):**
```java
@Configuration
public class CoreFilterConfig {

    @Bean
    public FilterRegistrationBean<CorrelationIdFilter>
        correlationIdFilterRegistration() {

        FilterRegistrationBean<CorrelationIdFilter> bean =
            new FilterRegistrationBean<>(
                new CorrelationIdFilter()
            );

        bean.setOrder(0);                    // PRIORITY: First filter
        bean.addUrlPatterns("/*");           // All requests
        bean.setName("CorrelationIdFilter");

        return bean;
    }

    @Bean
    public FilterRegistrationBean<ExceptionFilter>
        exceptionFilterRegistration() {

        FilterRegistrationBean<ExceptionFilter> bean =
            new FilterRegistrationBean<>(
                new ExceptionFilter()
            );

        bean.setOrder(1);
        bean.addUrlPatterns("/*");
        bean.setName("ExceptionFilter");

        return bean;
    }

    // ... similar for all 13 core filters
}
```

### Filter Ordering Best Practices

**Recommended Ordering Strategy:**

```
0-3:     Core infrastructure filters (required)
4-9:     Conditional security/validation filters
10-19:   Custom application filters
20+:     Special-purpose filters
```

**Why This Order:**
1. **CorrelationId first (0):** Needed by all downstream components
2. **Exception wrapping second (1):** Captures all subsequent exceptions
3. **Session/Body handling (2-3):** Prepare request for processing
4. **Validation/Security (4-9):** Check request before business logic
5. **App-specific (10+):** Application extensions
6. **Special (20+):** Rate limiting, monitoring, cleanup

---

## Extension Points: Custom Filters

### Creating a Custom Filter

**Pattern 1: Extend OncePerRequestFilter**

```java
public class CustomAuditFilter extends OncePerRequestFilter {

    @Override
    public void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {

        // Before request
        String correlationId =
            request.getHeader("Correlation-ID");
        String endpoint = request.getRequestURI();
        String method = request.getMethod();

        auditService.logRequest(
            correlationId,
            endpoint,
            method
        );

        try {
            // Pass to next filter
            filterChain.doFilter(request, response);
        } finally {
            // After response
            int statusCode = response.getStatus();
            auditService.logResponse(
                correlationId,
                statusCode
            );
        }
    }

    @Override
    protected boolean shouldNotFilter(
        HttpServletRequest request
    ) throws ServletException {

        // Skip filter for health checks
        String path = request.getRequestURI();
        return path.startsWith("/actuator/health");
    }
}
```

**Pattern 2: Register in Configuration**

```java
@Configuration
public class AuditFilterConfig {

    @Bean
    public FilterRegistrationBean<CustomAuditFilter>
        auditFilterRegistration(AuditService auditService) {

        CustomAuditFilter filter =
            new CustomAuditFilter(auditService);

        FilterRegistrationBean<CustomAuditFilter> bean =
            new FilterRegistrationBean<>(filter);

        bean.setOrder(12);  // After core filters
        bean.addUrlPatterns("/api/*");
        bean.setName("CustomAuditFilter");

        return bean;
    }
}
```

### Conditional Filter Registration

```java
@Bean
@ConditionalOnProperty(
    name = "audit.filter.enabled",
    havingValue = "true"
)
public FilterRegistrationBean<CustomAuditFilter>
    auditFilterRegistration() {

    // Only register if property is true
    // ...
}
```

---

## Error Handling in Filters

### Exception Flow

```
Application exception
    ↓
ExceptionFilter catches in doFilterInternal() catch block
    ↓
Maps to Response<T> error envelope
    ↓
Sets HTTP status code
    ↓
Writes JSON to response
    ↓
Returns to client
```

### Exception Mapping

**In ExceptionFilter (mca-filter-core):**

```java
private int mapExceptionToStatus(Exception ex) {
    if (ex instanceof NotFoundException) {
        return 404;
    } else if (ex instanceof AuthorizationException) {
        return 403;
    } else if (ex instanceof RequestException) {
        return 400;
    } else if (ex instanceof ServerException) {
        return 500;
    } else {
        return 500;  // Default to server error
    }
}
```

---

## Filter Chain Configuration Properties

### MCA2 Standard Properties

```properties
# Core Filters
filter.correlationid.enabled=true
filter.correlationid.header.name=Correlation-ID

filter.exception.enabled=true
filter.exception.stack-trace-enabled=false

filter.disable-session.enabled=true

filter.multiread.enabled=true
filter.multiread.max-buffer-size=1048576

# Conditional Filters
oauth.validation.enabled=false
oauth.jwt.issuer=https://auth.example.com
oauth.jwt.audience=api.example.com

ddos.prevention.enabled=false
ddos.requests-per-minute=1000
ddos.block-duration-seconds=60

request.validation.enabled=false

request.whitelist.enabled=false
request.whitelist.paths=/api/public/*

dynamic-logging.enabled=false

perf-log.exclusions.enabled=true
perf-log.exclusions.paths=/actuator/health,/metrics

# Filter Ordering
filter.order.correlation-id=0
filter.order.exception=1
filter.order.disable-session=2
filter.order.multiread=3
filter.order.custom=10
```

---

## Filter Chain: Request/Response Lifecycle

### Request Phase (In Order)

```
1. Request arrives at Servlet Container
2. CorrelationIdFilter (Order 0)
   ├─ Generate/extract correlation ID
   ├─ Store in thread-local
   └─ Pass to next filter
3. ExceptionFilter (Order 1)
   ├─ Wrap remaining chain
   └─ Pass to next filter
4. DisableSessionFilter (Order 2)
   ├─ Wrap request
   └─ Pass to next filter
5. MultiReadRequestFilter (Order 3)
   ├─ Cache request body
   └─ Pass to next filter
6. Conditional Filters (Order 4-9)
   ├─ OAuth validation
   ├─ DDoS prevention
   ├─ Request validation
   └─ Pass to next filter
7. Custom Filters (Order 10+)
   └─ Application-specific processing
8. DispatcherServlet
   ├─ Route to handler
   └─ Execute handler
9. Handler generates response
```

### Response Phase (Reverse Order)

```
9. Handler returns response/exception
8. DispatcherServlet sends response
7. Custom Filters (Order 10+)
   ├─ Post-processing
   └─ Return to previous filter
6. Conditional Filters (Order 4-9)
   ├─ Response modification
   └─ Return to previous filter
5. MultiReadRequestFilter (Order 3)
   ├─ Clean up cached body
   └─ Return to previous filter
4. DisableSessionFilter (Order 2)
   ├─ Clean up wrapper
   └─ Return to previous filter
3. ExceptionFilter (Order 1)
   ├─ Catch any exceptions from chain
   ├─ Convert to Response<T>
   └─ Write response
2. CorrelationIdFilter (Order 0)
   ├─ Add response header
   ├─ Clean up thread-local
   └─ Return response
1. Response returns to client
```

---

## Performance Considerations

### Filter Latency

**Typical latency per filter:**
- CorrelationIdFilter: < 0.1ms
- ExceptionFilter: < 0.1ms (no exception)
- DisableSessionFilter: < 0.05ms
- MultiReadRequestFilter: 0.1-2ms (depends on body size)
- Conditional filters: 0.1-1ms each

**Total typical overhead:** < 5ms for full chain

### Optimization Tips

1. **Use `shouldNotFilter()` to skip expensive filters**
   ```java
   protected boolean shouldNotFilter(HttpServletRequest request) {
       String path = request.getRequestURI();
       return path.startsWith("/actuator/");  // Skip monitoring
   }
   ```

2. **Cache validation results** for repeated requests
3. **Defer expensive operations** (e.g., database lookups)
4. **Use connection pools** for external service calls
5. **Profile filter chain** with JProfiler or async-profiler

---

## Troubleshooting Filter Issues

### Issue: Filter Not Executing

**Solution:**
- Check filter order configuration
- Verify URL pattern matches request
- Check `@ConditionalOnProperty` is true
- Verify filter bean is created

### Issue: Request Body Consumed (Can't Read Twice)

**Solution:**
- Ensure MultiReadRequestFilter is enabled (Order 3)
- Check MultiReadRequestFilter is before your filter
- Verify it hasn't been disabled via property

### Issue: Session Created Despite DisableSessionFilter

**Solution:**
- Verify DisableSessionFilter is before handler
- Check no code calls `request.getSession(true)`
- Ensure DisableSessionFilter bean is registered

### Issue: Exceptions Not Caught

**Solution:**
- Verify ExceptionFilter is at Order 1
- Check exception is subclass of Exception
- Verify ExceptionFilter bean is registered
- Check exception is thrown before response committed

---

## Filter Chain: Complete Code Reference

### Key Classes Location

```
mca-libraries/filter-core/src/main/java/
com/barclays/global/mca/libs/filters/
├── CorrelationIdFilter.java
├── ExceptionFilter.java
├── DisableSessionFilter.java
├── MultiReadRequestFilter.java
├── OAuthValidatorFilter.java
├── DdosFilter.java
├── ValidationFilter.java
├── RequestWhitelistingFilter.java
├── DynamicLoggingFilter.java
├── PerfLogExclusionFilter.java
├── providers/
│   ├── DdosPreventor.java (interface)
│   ├── DefaultAllowAllRequestDdosPreventor.java
│   └── ChannelPropositionBasedDdosPreventor.java
└── data/
    ├── RequestContextData.java
    └── DdosResponse.java
```

### Core Configuration

```
mca-libraries/mca-eps-core/src/main/java/
com/barclays/global/mca/libs/eps/config/
├── ExperienceAPIConfig.java (master config)
├── CoreFilterConfig.java (filter registration)
├── FilterConfig.java (filter configuration)
├── WebMvcConfig.java (Web MVC setup)
├── ProcessConfig.java
├── SchemaConfig.java
└── OAuthValidatorConfigProperties.java
```

---

## Next Steps

1. **Understand Filter Ordering:** Review OrderingStrategy section
2. **Study Individual Filters:** Focus on CorrelationIdFilter and ExceptionFilter
3. **Create Custom Filter:** Follow extension point patterns
4. **Configure Conditional Filters:** Use @ConditionalOnProperty
5. **Profile Performance:** Measure filter chain overhead
6. **Reference Application:** Study filter usage in experience-api-cardcontrol-reference-app

---

## Quick Reference: Filter Chain Summary

| Filter | Order | Purpose | Required |
|--------|-------|---------|----------|
| CorrelationIdFilter | 0 | Request tracing | ✅ Yes |
| ExceptionFilter | 1 | Error handling | ✅ Yes |
| DisableSessionFilter | 2 | Stateless enforcement | ✅ Yes |
| MultiReadRequestFilter | 3 | Body re-reading | ✅ Yes |
| OAuthValidatorFilter | 4+ | Token validation | ⚠️ Optional |
| DdosFilter | 5+ | Rate limiting | ⚠️ Optional |
| ValidationFilter (OAS) | 300 | OpenAPI 3.0 request validation | ⚠️ Optional |
| RequestWhitelistingFilter | 7+ | Endpoint whitelist | ⚠️ Optional |
| DynamicLoggingFilter | 8+ | Log level control | ⚠️ Optional |
| PerfLogExclusionFilter | 9+ | Perf log exclusions | ⚠️ Optional |
| Custom Filters | 10+ | Application-specific | ⚠️ Custom |

**Filter Chain is the primary request processing model in MCA2.**
