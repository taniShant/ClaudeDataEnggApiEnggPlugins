# Filter Configuration Reference: Complete Guide

## Executive Summary

Complete reference for all 13 MCA2 EPS filters including configuration properties, ordering, exclusions, and behavior. Use this as authoritative guide during development and troubleshooting.

---

## Filter Chain Overview

### Execution Order (0-10+)

```
Order  Filter Name              Mandatory  Property
─────────────────────────────────────────────────────────────────
  0    CorrelationIdFilter      YES        mca.filter.correlation-id.enabled
  1    ExceptionFilter          YES        mca.filter.exception.enabled
  2    DisableSessionFilter     YES        mca.filter.disable-session.enabled
  3    MultiReadRequestFilter   YES        mca.filter.multiread-request.enabled

  4    ContextFilter            OPTIONAL   mca.filter.context.enabled
  5    OAuthValidatorFilter     OPTIONAL   mca.filter.oauth-validator.enabled
  6    DdosPreventionFilter     OPTIONAL   mca.filter.ddos-prevention.enabled
  300  ValidationFilter (OAS)   OPTIONAL   core.default.oas.enabled
  8    RequestWhitelistingFilter OPTIONAL   mca.filter.request-whitelisting.enabled

  10+  Custom Filters           VARIES     N/A
```

---

## CORE FILTERS (Always Enabled)

### Filter 0: CorrelationIdFilter

**Purpose:** Generate and propagate unique correlation ID for request tracing

**Order:** 0 (MUST be first)

**Configuration Properties:**
```properties
mca.filter.correlation-id.enabled=true                    # Default: true
mca.filter.correlation-id.header=Correlation-ID           # Header name
mca.filter.correlation-id.generate-if-missing=true       # Generate UUID if not present
mca.filter.correlation-id.pattern=^[a-zA-Z0-9-]{36}$    # Validation pattern
```

**Behavior:**
```
1. Check for Correlation-ID header in request
2. If present: validate format, use if valid
3. If missing: generate new UUID
4. Set in MDC: MDC.put("correlationId", id)
5. Add to response header: Correlation-ID: {id}
6. Remove from MDC on exit
```

**Methods:**
```java
String correlationId = MDC.get("correlationId");
// Available throughout request lifecycle in all logs
```

**Exclusions:** None (always applied)

**Performance Impact:** <1ms per request

**Critical for:** Distributed tracing, log aggregation, debugging

> **Note:** The deprecated `X-CorrelationId` header is also supported for backward compatibility.

---

### Filter 1: ExceptionFilter

**Purpose:** Global exception handling and Response<> envelope conversion

**Order:** 1 (MUST be second, after CorrelationIdFilter)

**Configuration Properties:**
```properties
mca.filter.exception.enabled=true                         # Default: true
mca.filter.exception.detailed-error-messages=false       # NEVER true in production!
mca.filter.exception.include-stacktrace=false            # Avoid exposing internals
mca.filter.exception.log-level=ERROR                     # ERROR or WARN
```

**Behavior:**
```
1. Wrap entire request in try-catch
2. On exception:
   a. Log with correlation ID
   b. Map to ResponseHttpStatus
   c. Build Response<> envelope
   d. Return with appropriate HTTP status
3. Convert GenericException → HTTP status (400/403/404/500)
4. Catch unexpected exceptions → 500 Internal Server Error
5. Never expose stack traces in response body
```

**Exception Mapping:**
```
RequestException             → 400 Bad Request
NotFoundException            → 404 Not Found
AuthorizationException       → 403 Forbidden
ApplicationException         → 200 OK (app-level error)
ServerException              → 500 Internal Server Error
Any other Exception          → 500 Internal Server Error
```

**Methods:**
```java
// In controller - just throw, ExceptionFilter handles response
throw new RequestException("Invalid amount", ErrorCode.VALIDATION_ERROR);
// ExceptionFilter converts to:
// Status: 400, Response: {status: "ERROR", error: "Invalid amount"}
```

**Exclusions:** None (always applied)

**Performance Impact:** <2ms per request

**Critical for:** Error handling, response standardization

---

### Filter 2: DisableSessionFilter

**Purpose:** Prevent HTTP session creation for stateless services

**Order:** 2 (MUST be third)

**Configuration Properties:**
```properties
mca.filter.disable-session.enabled=true                  # Default: true
mca.filter.disable-session.allow-jsessionid=false        # Block JSESSIONID
```

**Behavior:**
```
1. Override request.getSession() to return null
2. Prevent session cookie creation
3. Force stateless request processing
4. Reduce memory footprint
```

**Methods:**
```java
// Attempting to access session
HttpSession session = request.getSession();
// Returns null - stateless processing enforced
```

**Exclusions:** None (always applied)

**Performance Impact:** <1ms per request

**Critical for:** Stateless architecture, container memory reduction

---

### Filter 3: MultiReadRequestFilter

**Purpose:** Allow reading request body multiple times

**Order:** 3 (MUST be fourth)

**Configuration Properties:**
```properties
mca.filter.multiread-request.enabled=true                # Default: true
mca.filter.multiread-request.max-size=1MB               # Buffer size limit
```

**Behavior:**
```
1. Wrap request in BufferedRequest
2. Cache request body in memory (limited by max-size)
3. Allow multiple InputStream.read() calls
4. Required for request validation and logging
```

**Methods:**
```java
// Can now read body multiple times
String body1 = IOUtils.toString(request.getInputStream());
String body2 = IOUtils.toString(request.getInputStream());
// Both read the same cached body
```

**Exclusions:**
- GET/HEAD requests (no body)
- Requests larger than max-size

**Performance Impact:** 2-5ms (body caching)

**Critical for:** Request validation, request logging

---

## OPTIONAL FILTERS (Conditional)

### Filter 4: ContextFilter

**Purpose:** Extract context from HTTP headers and populate IOLSchema

**Order:** 4

**Configuration Properties:**
```properties
mca.filter.context.enabled=true                         # Default: true
mca.filter.context.header-prefix=X-                     # Header prefix
mca.filter.context.validate-schema=true                 # Validate context
mca.filter.context.strict-mode=false                    # Strict validation
```

**Behavior:**
```
1. Extract headers starting with X-
2. Parse JSON context headers
3. Validate against IOLSchema
4. Set in request scope via WebUtils
5. Available throughout request to handlers
```

**Header Format:**
```
X-CustomerContext: {"customerId": "cust-123", "name": "Acme Corp"}
X-UserContext: {"userId": "user-456", "email": "john@acme.com"}
X-AccountContext: {"accountId": "acc-789", "type": "CHECKING"}
```

**Methods:**
```java
@IOLContext CustomerContext context  // Injected in controller
IOLSchema schema = WebUtils.getIOLSchemaFromScope();  // Direct access
```

**Exclusions:**
- /health (health check endpoint)
- /public/* (public endpoints)
- /actuator/* (metrics endpoints)

**Performance Impact:** 1-3ms per request

**Critical for:** Context propagation, multi-tenant isolation

---

### Filter 5: OAuthValidatorFilter

**Purpose:** Validate OAuth2 tokens before processing requests

**Order:** 5

**Configuration Properties:**
```properties
mca.filter.oauth-validator.enabled=true                 # Default: false (@ConditionalOnProperty)
mca.filter.oauth-validator.provider-url=https://...    # OAuth provider
mca.filter.oauth-validator.cache-ttl=3600              # Token cache (seconds)
mca.filter.oauth-validator.scope-required=api           # Required scope
```

**Behavior:**
```
1. Extract Authorization header: Bearer {token}
2. Validate token against OAuth provider
3. Cache valid tokens (TTL configurable)
4. Inject user context if valid
5. Return 401 if invalid
```

**Methods:**
```java
// Token required for protected endpoints
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  http://localhost:8080/api/protected
```

**Exclusions:**
- /public/* (public endpoints)
- /health
- /metrics

**Performance Impact:** 5-50ms (first call, <1ms cached)

**Critical for:** API security, authentication

---

### Filter 6: DdosPreventionFilter

**Purpose:** Rate limit requests per IP address

**Order:** 6

**Configuration Properties:**
```properties
mca.filter.ddos-prevention.enabled=true                 # Default: false
mca.filter.ddos-prevention.requests-per-second=100      # RPM threshold
mca.filter.ddos-prevention.window-size=60               # Time window (seconds)
mca.filter.ddos-prevention.block-duration=300           # Block duration (seconds)
mca.filter.ddos-prevention.redis-enabled=true           # Distributed mode
```

**Behavior:**
```
1. Extract client IP from request
2. Track requests per IP in time window
3. If threshold exceeded: return 429 Too Many Requests
4. Use Redis for distributed rate limiting (optional)
5. Block offending IP for configured duration
```

**Response When Limited:**
```
HTTP/1.1 429 Too Many Requests
Retry-After: 300
{status: "RATE_LIMITED", message: "Too many requests"}
```

**Exclusions:**
- /health (always allowed)
- Whitelist via property: `mca.filter.ddos-prevention.whitelist=10.0.0.0/8`

**Performance Impact:** 1-2ms per request

**Critical for:** DDoS protection, rate limiting

---

### Filter 300: ValidationFilter (OAS Validation)

**Purpose:** Validate HTTP requests against OpenAPI 3.0 specifications using the Atlassian swagger-request-validator library. Performs both structural OAS validation and JSON schema validation on request bodies before they reach the controller.

**Order:** 300

**Validation Engine:** `OASRequestValidation` from `mca-oas-validation` module, powered by `com.atlassian.oai:swagger-request-validator-spring-webmvc:2.45.1`

**Configuration Properties:**
```properties
# Enable/disable OAS validation (default: false)
core.default.oas.enabled=true

# Path to OpenAPI YAML or JSON specification file
core.default.oas.path=classpath:openapi/api-spec.yaml

# OAS version identifier
core.default.oas.version=3.0

# Don't fail if schema is missing for a given path/operation (default: false)
core.default.oas.ignore-missing-schema=false

# Block requests that fail validation with 400 Bad Request (default: false)
# When false, validation errors are logged as warnings but the request continues
core.default.oas.blockingMode=true

# Headers to exclude from OAS validation checks
core.default.oas.excludedHeaders=X-Internal-Token,X-Trace-Id

# Force validation even if X-SchemaValidated header is present (default: false)
core.default.oas.alwaysValidate=false

# Paths to exclude from validation (comma-separated Ant patterns)
# Default: /actuator/**,/process/**
core.default.validation-filter.exclude.paths=/actuator/**,/process/**
```

**Behavior:**
```
1. Check if request path matches exclusion patterns (/actuator/**, /process/**)
   → If excluded, skip validation and continue chain
2. Check for X-SchemaValidated header on the request
   → If present and alwaysValidate=false, skip validation (upstream already validated)
3. Load OpenAPI spec via OasProvider strategy:
   → SimpleOasProvider: loads from Spring Resource (classpath or file)
   → EmptyOasProvider: no-op when validation is disabled
4. Validate request method, path, query params, headers, and body against spec
5. Perform JSON schema validation on request body (if applicable)
6. Build OasValidationResult containing status, error flags, and OasValidationMessage list
7. If errors found and blockingMode=true:
   → Throw RequestException (caught by ExceptionFilter → 400 Bad Request)
8. If errors found and blockingMode=false:
   → Log validation warnings, allow request to continue
9. If no errors:
   → Continue to next filter in chain
```

**Exclusions:**
- Paths matching `core.default.validation-filter.exclude.paths` (default: `/actuator/**`, `/process/**`)
- Requests with `X-SchemaValidated` header present (unless `alwaysValidate=true`)
- Headers listed in `core.default.oas.excludedHeaders`

**Performance Impact:** 5-20ms per request (depends on OpenAPI spec complexity and request body size)

**Critical for:** API contract enforcement, request validation, input sanitization

**Example Configuration (YAML):**
```yaml
core:
  default:
    oas:
      enabled: true
      path: classpath:openapi/card-control-api.yaml
      version: "3.0"
      blockingMode: true
      ignore-missing-schema: false
      alwaysValidate: false
      excludedHeaders:
        - X-Internal-Token
        - X-Forwarded-For
    validation-filter:
      exclude:
        paths: /actuator/**,/process/**,/health/**
```

**Blocking vs Reporting-Only Mode:**
```
blockingMode=true  → Invalid requests receive 400 Bad Request immediately
blockingMode=false → Invalid requests are logged as warnings, processing continues
                     (useful during migration or gradual rollout)
```

---

### Filter 8: RequestWhitelistingFilter

**Purpose:** Allow only whitelisted request paths/methods

**Order:** 8

**Configuration Properties:**
```properties
mca.filter.request-whitelisting.enabled=true            # Default: false
mca.filter.request-whitelisting.allowed-paths=/api/.*   # Regex patterns
mca.filter.request-whitelisting.allowed-methods=GET,POST,PUT  # HTTP methods
```

**Behavior:**
```
1. Check request path against whitelist
2. Check HTTP method against allowed list
3. Allow: continue to next filter
4. Deny: return 403 Forbidden
```

**Configuration Example:**
```properties
mca.filter.request-whitelisting.allowed-paths=/api/.*,/health,/metrics
mca.filter.request-whitelisting.allowed-methods=GET,POST,PUT,DELETE
```

**Performance Impact:** <1ms per request

**Critical for:** Security, access control

---

## CUSTOM FILTERS

### Adding Custom Filters (Order 10+)

**Registration Pattern:**
```java
@Configuration
public class CustomFilterConfig {

  @Bean
  public FilterRegistrationBean<MyCustomFilter> registerMyFilter() {
    FilterRegistrationBean<MyCustomFilter> bean =
      new FilterRegistrationBean<>(new MyCustomFilter());

    bean.setOrder(10);  // After core filters
    bean.addUrlPatterns("/api/*");  // Apply to paths
    bean.setAsyncSupported(true);   // Enable async

    return bean;
  }
}
```

**Custom Filter Implementation:**
```java
@Component
public class MyCustomFilter extends OncePerRequestFilter {

  @Override
  protected void doFilterInternal(
    HttpServletRequest request,
    HttpServletResponse response,
    FilterChain chain
  ) throws ServletException, IOException {

    try {
      // Custom logic before
      logger.info("Custom filter processing");

      chain.doFilter(request, response);  // MUST call!

      // Custom logic after
    } catch (Exception e) {
      logger.error("Custom filter error", e);
      throw e;
    }
  }

  @Override
  protected boolean shouldNotFilter(HttpServletRequest request) {
    // Exclude paths
    return request.getRequestURI().startsWith("/health");
  }
}
```

---

## Filter Chain Configuration Examples

### Development Profile (All Filters)
```properties
# application-dev.properties
mca.filter.correlation-id.enabled=true
mca.filter.exception.enabled=true
mca.filter.exception.detailed-error-messages=true  # OK for dev
mca.filter.disable-session.enabled=true
mca.filter.multiread-request.enabled=true
mca.filter.context.enabled=true
mca.filter.oauth-validator.enabled=false
mca.filter.ddos-prevention.enabled=false
core.default.oas.enabled=false                                 # OAS validation off in dev
mca.filter.request-whitelisting.enabled=false
```

### Production Profile (Selective Filters)
```properties
# application-prod.properties
mca.filter.correlation-id.enabled=true
mca.filter.exception.enabled=true
mca.filter.exception.detailed-error-messages=false  # CRITICAL
mca.filter.disable-session.enabled=true
mca.filter.multiread-request.enabled=true
mca.filter.context.enabled=true
mca.filter.oauth-validator.enabled=true            # Security
mca.filter.ddos-prevention.enabled=true            # Protection
core.default.oas.enabled=true                      # OAS validation
core.default.oas.path=classpath:openapi/api-spec.yaml
core.default.oas.blockingMode=true                 # Reject invalid requests
mca.filter.request-whitelisting.enabled=true       # Allow list
```

### High-Security Profile (Maximum Protection)
```properties
# application-secure.properties
mca.filter.correlation-id.enabled=true
mca.filter.exception.enabled=true
mca.filter.exception.detailed-error-messages=false
mca.filter.exception.include-stacktrace=false
mca.filter.disable-session.enabled=true
mca.filter.multiread-request.enabled=true
mca.filter.context.enabled=true
mca.filter.oauth-validator.enabled=true
mca.filter.oauth-validator.cache-ttl=300           # Shorter cache
mca.filter.ddos-prevention.enabled=true
mca.filter.ddos-prevention.requests-per-second=50  # Stricter limit
core.default.oas.enabled=true                      # OAS validation
core.default.oas.path=classpath:openapi/api-spec.yaml
core.default.oas.blockingMode=true                 # Block invalid requests
core.default.oas.ignore-missing-schema=false       # Strict schema enforcement
core.default.oas.alwaysValidate=true               # Always validate, ignore X-SchemaValidated
mca.filter.request-whitelisting.enabled=true
```

---

## Filter Troubleshooting

### Issue: Correlation ID Not in Logs

**Check:**
1. CorrelationIdFilter is enabled
2. Logging pattern includes `%X{correlationId}`
3. Filter order is 0 (must be first)

**Solution:**
```properties
mca.filter.correlation-id.enabled=true
logging.pattern.console=%d{ISO8601} [%X{correlationId}] %5p %msg%n
```

### Issue: Context Not Available in Controller

**Check:**
1. ContextFilter is enabled
2. X-*Context headers are present in request
3. @IOLContext annotation used in parameter

**Solution:**
```properties
mca.filter.context.enabled=true
```

```java
@GetMapping("/endpoint")
public ResponseEntity<?> endpoint(
  @IOLContext CustomerContext context  // ADD THIS
) { }
```

### Issue: Requests Getting 429 (Too Many Requests)

**Check:**
1. DdosPreventionFilter threshold too low
2. Client IP being blocked

**Solution:**
```properties
mca.filter.ddos-prevention.requests-per-second=1000  # Increase
mca.filter.ddos-prevention.whitelist=10.0.0.0/8     # Whitelist IP
```

---

## Filter Performance Matrix

| Filter | Typical Latency | When Slow | Solution |
|--------|-----------------|-----------|----------|
| CorrelationIdFilter | <1ms | UUID generation | Pre-generate UUIDs |
| ExceptionFilter | <2ms | Logging overhead | Async logging |
| DisableSessionFilter | <1ms | N/A | Always fast |
| MultiReadRequestFilter | 2-5ms | Large body | Increase buffer |
| ContextFilter | 1-3ms | Large context | Compress context |
| OAuthValidatorFilter | 5-50ms | First call | Enable caching |
| DdosPreventionFilter | 1-2ms | Redis latency | Local Redis |
| ValidationFilter (OAS) | 5-20ms | Complex spec | Simplify OAS spec |

---

## Filter Chain Visualization

```
┌─────────────────────────────────────────────┐
│ HTTP Request from Client                     │
└──────────────┬────────────────────────────────┘
               ↓
       ┌───────────────┐
       │ Order 0       │
       │ Correlation   │ Generate/extract correlation ID
       │ ID Filter     │ Set in MDC, add to response headers
       └───────┬───────┘
               ↓
       ┌───────────────┐
       │ Order 1       │
       │ Exception     │ Wrap entire request
       │ Filter        │ Catch exceptions → Response<>
       └───────┬───────┘
               ↓
       ┌───────────────┐
       │ Order 2       │
       │ Disable       │ Force stateless (no sessions)
       │ Session       │
       └───────┬───────┘
               ↓
       ┌───────────────┐
       │ Order 3       │
       │ MultiRead     │ Cache body for multiple reads
       │ Request       │
       └───────┬───────┘
               ↓
       ┌───────────────────────────────────────┐
       │ OPTIONAL FILTERS (if enabled)          │
       ├───────────────────────────────────────┤
       │ Order 4: ContextFilter                 │
       │ Order 5: OAuthValidatorFilter         │
       │ Order 6: DdosPreventionFilter         │
       │ Order 300: ValidationFilter (OAS)     │
       │ Order 8: RequestWhitelistingFilter    │
       └───────┬───────────────────────────────┘
               ↓
       ┌───────────────────────────────────────┐
       │ CUSTOM FILTERS (Order 10+)             │
       │ Application-specific filters           │
       └───────┬───────────────────────────────┘
               ↓
       ┌───────────────────────────────────────┐
       │ CONTROLLER / SERVICE                   │
       │ Business logic executes                │
       │ Context available via @IOLContext      │
       └───────┬───────────────────────────────┘
               ↓
       ┌───────────────────────────────────────┐
       │ RESPONSE ASSEMBLY                      │
       │ Response<> envelope wrapping           │
       └───────┬───────────────────────────────┘
               ↓
       ┌───────────────────────────────────────┐
       │ CORRELATION ID CLEANUP                 │
       │ Remove from MDC                        │
       │ Exception filter adds to response      │
       └───────┬───────────────────────────────┘
               ↓
       ┌──────────────────────────────────────┐
       │ HTTP Response to Client                │
       │ Status code, Response<> body,         │
       │ Correlation-ID header                  │
       └──────────────────────────────────────┘
```

---

## Quick Reference: Enable/Disable Filters

```bash
# Enable single filter
-Dmca.filter.oauth-validator.enabled=true

# Disable single filter
-Dmca.filter.ddos-prevention.enabled=false

# Configure property
-Dmca.filter.ddos-prevention.requests-per-second=1000

# In application.properties
mca.filter.context.enabled=true
mca.filter.oauth-validator.enabled=true
```

**Filter Configuration Reference provides authoritative guide for all MCA2 filters.**

