# Troubleshooting Guide: Common Issues & Solutions

## Executive Summary

Diagnosis and resolution strategies for common MCA2 EPS integration issues. Organized by symptom with root cause analysis, debugging techniques, and preventive measures.

---

## Troubleshooting Framework

### Diagnosis Process

```
1. Identify Symptom
   └─ What is the observable problem?

2. Check Framework Prerequisites
   └─ Is @EnableExperienceAPI present?

3. Review Logs
   └─ ERROR level messages
   └─ Correlation IDs for tracing

4. Trace Context Flow
   └─ Does correlation ID appear in logs?
   └─ Is context propagated between services?

5. Check Configuration
   └─ Are properties correct?
   └─ Are profiles being applied?

6. Validate Data
   └─ Is context schema valid?
   └─ Are HTTP headers correct?

7. Test in Isolation
   └─ Can you reproduce locally?
   └─ Does unit test pass?
```

---

## Issue 1: Application Fails to Start

### Symptom
```
ERROR: Application failed to start
org.springframework.beans.factory.BeanCreationException: Error creating bean...
```

### Root Cause Analysis

**Check 1: Missing @EnableExperienceAPI**
```java
// ❌ WRONG - No EPS enablement
@SpringBootApplication
public class OrderApp { }

// ✅ CORRECT
@SpringBootApplication
@EnableExperienceAPI
public class OrderApp { }
```

**Check 2: Circular Dependencies**
```bash
# Verify no circular dependencies
./gradlew :your-module:dependencies 2>&1 | grep -E "→.*←"

# If found:
# Error: mca-context → context-utils → mca-context
# Solution: Refactor to use interfaces (see Refactoring Guide)
```

**Check 3: Database Connection Failed**
```properties
# application-prod.properties
spring.datasource.url=jdbc:postgresql://db-host:5432/context_db
spring.datasource.username=${DB_USER}
spring.datasource.password=${DB_PASSWORD}

# Test connection
psql -h db-host -U postgres -d context_db -c "SELECT 1"
```

### Debugging Techniques

```bash
# Enable Spring Boot debug logging
java -Ddebug -jar app.jar

# Or in application.properties
debug=true
logging.level.org.springframework.boot=DEBUG

# Check what beans are being created
# Look for: Creating new instance of bean 'filterRegistrationBean'
```

### Solutions

```java
// Step 1: Add @EnableExperienceAPI
@SpringBootApplication
@EnableExperienceAPI                    // ADD THIS
public class OrderApp { }

// Step 2: Verify EPS dependencies
// build.gradle
dependencies {
  implementation "com.barclays.global.mca:mca-eps-core"
  implementation "com.barclays.global.mca:mca-filter-core"
}

// Step 3: Configure database (for your application data)
// application.properties
spring.datasource.url=jdbc:postgresql://localhost:5432/order_db
spring.datasource.username=postgres
spring.datasource.password=password
```

---

## Issue 2: Correlation ID Not Propagating

### Symptom
```
Logs show missing or inconsistent correlation IDs:

2026-02-26T10:15:23.123Z [] RequestId: 12345 - Processing order
2026-02-26T10:15:24.456Z [] RequestId: 12345 - Calling service A
2026-02-26T10:15:25.789Z [] RequestId: DIFFERENT - Service A received request
                                          ^^^^^^^^^
                                          Should match!
```

### Root Cause Analysis

**Check 1: CorrelationIdFilter Not Executing**
```bash
# Verify filter is registered
grep -r "CorrelationIdFilter\|FilterRegistrationBean" \
  src/main/java --include="*.java" | head -3

# Or check if filter is disabled via properties
grep -E "mca.filter.correlation.*enabled=false" \
  src/main/resources/application*.properties

# Should NOT be disabled
```

**Check 2: Service Client Not Propagating**
```java
// ❌ WRONG - Manual RestTemplate without context
RestTemplate template = new RestTemplate();
template.getForObject("http://service/api", Response.class);

// ✅ CORRECT - Use RestClientFactory
@Autowired
private RestClientFactory clientFactory;

RestTemplate template = clientFactory.createRestTemplate();
// Correlation ID automatically included in headers
```

**Check 3: Async Operations Losing Context**
```java
// ❌ WRONG - Context lost in async
@GetMapping("/report")
public CompletableFuture<Report> generateReport() {
  return CompletableFuture.supplyAsync(() -> {
    // Correlation ID not available here!
    return reportService.generate();
  });
}

// ✅ CORRECT - Preserve context
@GetMapping("/report")
public CompletableFuture<Report> generateReport() {
  String correlationId = MDC.get("correlationId");

  return CompletableFuture.supplyAsync(() -> {
    MDC.put("correlationId", correlationId);
    try {
      return reportService.generate();
    } finally {
      MDC.remove("correlationId");
    }
  });
}
```

### Debugging Techniques

```bash
# Check MDC (Mapped Diagnostic Context)
# Add to logger configuration:
logging.pattern.console=%d{ISO8601} [%X{correlationId}] %5p %msg%n

# Verify header is in HTTP response
curl -v http://localhost:8080/api/orders 2>&1 | grep -i "correlation-id"

# Should show:
# < Correlation-ID: 550e8400-e29b-41d4-a716-446655440000
```

### Solutions

```java
// Step 1: Verify CorrelationIdFilter is first (order 0)
@Bean
public FilterRegistrationBean<CorrelationIdFilter> registerCorrelationIdFilter() {
  FilterRegistrationBean<CorrelationIdFilter> bean =
    new FilterRegistrationBean<>(new CorrelationIdFilter());
  bean.setOrder(0);  // MUST be first
  return bean;
}

// Step 2: Always use RestClientFactory for service calls
@Autowired
private RestClientFactory clientFactory;

public void callDownstreamService() {
  RestTemplate template = clientFactory.createRestTemplate();
  // Correlation ID automatically propagated in Correlation-ID header
  template.getForObject("http://other-service/api", Response.class);
}

// Step 3: Manual context in async operations
String cid = MDC.get("correlationId");
MDC.put("correlationId", cid);  // Restore in thread
```

---

## Issue 3: Context Not Available in Handlers

### Symptom
```java
@GetMapping("/accounts/{id}")
public ResponseEntity<Account> getAccount(
  @PathVariable String id,
  @IOLContext CustomerContext context  // NULL!
) {
  if (context == null) {
    logger.warn("Context is null!");
  }
}
```

### Root Cause Analysis

**Check 1: ContextFilter Not Executing**
```bash
# Verify ContextFilter is in filter chain
grep -r "ContextFilter" src/main/java --include="*.java"

# Check if it's configured
grep -E "mca.filter.*context.*enabled" \
  src/main/resources/application*.properties

# Should not be disabled (default is enabled)
```

**Check 2: Wrong Header Format**
```bash
# Verify headers are in correct format
curl -H "X-CustomerContext={json}" http://localhost:8080/api/accounts

# Expected format: X-CustomerContext: {"customerId":"123",...}
# Wrong format will be ignored
```

**Check 3: Missing @IOLContext Annotation**
```java
// ❌ WRONG - No annotation
@GetMapping("/accounts/{id}")
public ResponseEntity<Account> getAccount(CustomerContext context) {
  // Context is null
}

// ✅ CORRECT - With annotation
@GetMapping("/accounts/{id}")
public ResponseEntity<Account> getAccount(
  @IOLContext CustomerContext context
) {
  // Context is properly injected
}
```

### Debugging Techniques

```java
// Check context directly from WebUtils
@GetMapping("/debug/context")
public ResponseEntity<?> debugContext() {
  IOLSchema schema = WebUtils.getIOLSchemaFromScope();
  if (schema == null) {
    return ResponseEntity.ok("Context is NULL");
  }
  CustomerContext ctx = schema.getContext("customer");
  return ResponseEntity.ok(ctx);
}

// Enable trace-level logging
logging.level.com.barclays.global.mca.libs.filter=TRACE
logging.level.com.barclays.global.mca.libs.context=TRACE
```

### Solutions

```java
// Step 1: Add @IOLContext annotation
@RestController
public class AccountController {
  @GetMapping("/accounts/{id}")
  public ResponseEntity<Account> getAccount(
    @IOLContext CustomerContext context  // ADD ANNOTATION
  ) {
    // Context now properly injected
  }
}

// Step 2: Verify headers from client
curl -X GET http://localhost:8080/api/accounts/123 \
  -H "X-CustomerContext: {\"customerId\":\"456\",\"name\":\"Test\"}"

// Step 3: Fallback to WebUtils if needed
public void processAccount(String accountId) {
  IOLSchema schema = WebUtils.getIOLSchemaFromScope();
  if (schema != null) {
    CustomerContext context = schema.getContext("customer");
    // Use context
  }
}
```

---

## Issue 4: Exception Handling Not Working

### Symptom
```
500 Internal Server Error response instead of proper error handling
```

### Root Cause Analysis

**Check 1: ExceptionFilter Not Registered**
```bash
# Verify ExceptionFilter is enabled and has correct order
grep -r "ExceptionFilter\|FilterRegistrationBean.*Exception" \
  src/main/java --include="*.java"

# Check order (should be 1, after CorrelationIdFilter at 0)
grep -A 2 "ExceptionFilter" src/main/java/*Config.java
```

**Check 2: Using Wrong Exception Type**
```java
// ❌ WRONG - Generic exception
throw new IllegalArgumentException("Invalid input");

// ✅ CORRECT - MCA2 exception
throw new RequestException(
  "Invalid input",
  ErrorCode.VALIDATION_ERROR
);
```

**Check 3: Exception Handler Order**
```java
// ❌ WRONG - Handler after base exception
@RestControllerAdvice
public class GlobalExceptionHandler {
  @ExceptionHandler(Exception.class)
  public ResponseEntity<?> handleAll(Exception e) { }

  @ExceptionHandler(ValidationException.class)
  public ResponseEntity<?> handleValidation(ValidationException e) { }
  // Specific handler unreachable!
}

// ✅ CORRECT - Specific before general
@RestControllerAdvice
public class GlobalExceptionHandler {
  @ExceptionHandler(ValidationException.class)  // Specific first
  public ResponseEntity<?> handleValidation(ValidationException e) { }

  @ExceptionHandler(Exception.class)  // General last
  public ResponseEntity<?> handleAll(Exception e) { }
}
```

### Debugging Techniques

```bash
# Enable exception-level logging
logging.level.com.barclays.global.mca.libs.filter.exception=DEBUG
logging.level.com.barclays.global.mca.libs.core.exception=DEBUG

# Check error response format
curl -X POST http://localhost:8080/api/orders \
  -H "Content-Type: application/json" \
  -d '{"invalid": "data"}' -v

# Should return Response<> envelope with error status
```

### Solutions

```java
// Step 1: Ensure ExceptionFilter registered with order 1
@Bean
public FilterRegistrationBean<ExceptionFilter> registerExceptionFilter() {
  FilterRegistrationBean<ExceptionFilter> bean =
    new FilterRegistrationBean<>(new ExceptionFilter());
  bean.setOrder(1);  // After CorrelationIdFilter (0)
  return bean;
}

// Step 2: Use MCA2 exceptions
@PostMapping("/orders")
public ResponseEntity<Response<Order>> createOrder(@RequestBody CreateOrderRequest req) {
  if (req.getAmount() < 0) {
    throw new RequestException(
      "Order amount must be positive",
      ErrorCode.VALIDATION_ERROR
    );
  }
  // ...
}

// Step 3: Implement global exception handler
@RestControllerAdvice
@Slf4j
public class GlobalExceptionHandler {
  @ExceptionHandler(GenericException.class)
  public ResponseEntity<Response<?>> handleGenericException(GenericException e) {
    logger.error("Business exception", e);
    return ResponseEntity
      .status(e.getResponseHttpStatus().getStatusCode())
      .body(Response.assemble()
        .status("ERROR")
        .error(e.getMessage())
        .build()
      );
  }

  @ExceptionHandler(Exception.class)
  public ResponseEntity<Response<?>> handleUnexpected(Exception e) {
    logger.error("Unexpected exception", e);
    return ResponseEntity.status(500)
      .body(Response.assemble()
        .status("INTERNAL_ERROR")
        .error("Internal server error")
        .build()
      );
  }
}
```

---

## Issue 5: Service-to-Service Communication Failing

### Symptom
```
Exception: Connection refused / Service unavailable
OR
Context not available in downstream service
```

### Root Cause Analysis

**Check 1: Service Discovery Not Working**
```bash
# Verify downstream service is registered
curl http://consul.internal:8500/v1/catalog/service/inventory-service

# Should return service instances
# If empty: service not registered
```

**Check 2: RestClientFactory Not Used**
```java
// ❌ WRONG - Direct RestTemplate creation
new RestTemplate().postForObject(...)  // Breaks context propagation

// ✅ CORRECT - Use RestClientFactory
clientFactory.createRestTemplate().postForObject(...)  // Context included
```

**Check 3: Circuit Breaker Activated**
```bash
# Check circuit breaker status
curl http://localhost:8080/actuator/health/circuitbreakers

# May show OPEN status: service calls failing
# Solution: Check downstream service health
curl http://inventory-service:8080/actuator/health
```

### Debugging Techniques

```bash
# Test service connectivity
curl -v http://inventory-service:8080/api/inventory \
  -H "Correlation-ID: test-123"

# Check if correlation ID echoed back
# < Correlation-ID: test-123

# Test with context header
curl -v http://inventory-service:8080/api/inventory \
  -H "X-CustomerContext: {\"customerId\":\"456\"}"

# Verify downstream receives context
```

### Solutions

```java
// Step 1: Always use RestClientFactory
@Autowired
private RestClientFactory clientFactory;

public void callInventoryService(ReserveRequest req) {
  RestTemplate client = clientFactory.createRestTemplate();

  InventoryResponse response = client.postForObject(
    "http://inventory-service/api/reserve",  // Uses service discovery
    req,
    InventoryResponse.class
  );
  // Correlation ID and context automatically propagated
}

// Step 2: Handle circuit breaker failures
@Transactional
public void createOrderWithFallback(CreateOrderRequest req) {
  try {
    callInventoryService(req);
  } catch (CallNotPermittedException e) {
    // Circuit breaker open
    logger.warn("Inventory service unavailable, using fallback", e);
    // Use cached data or degraded mode
    return;
  }
}

// Step 3: Verify upstream service is healthy
public void validateDownstream() {
  RestTemplate client = clientFactory.createRestTemplate();
  try {
    ResponseEntity<Map> health = client.getForEntity(
      "http://inventory-service/actuator/health",
      Map.class
    );
    if ("UP".equals(health.getBody().get("status"))) {
      logger.info("Downstream service healthy");
    }
  } catch (Exception e) {
    logger.error("Downstream service check failed", e);
  }
}
```

---

## Issue 6: Database Connection Pool Exhaustion

### Symptom
```
ERROR: Cannot get a connection, pool error Timeout waiting for idle object
```

### Root Cause Analysis

**Check 1: Connection Pool Too Small**
```properties
# application.properties
spring.datasource.hikari.maximum-pool-size=5  # Too small!

# For production: (CPU_cores × 2) + 1 = minimum
# Example: 4-core CPU → (4 × 2) + 1 = 9 minimum
spring.datasource.hikari.maximum-pool-size=25  # Better
```

**Check 2: Queries Holding Connections Too Long**
```java
// ❌ WRONG - Transaction too long
@Transactional
public void processLargeDataset() {
  List<accounts> = getAllAccounts();  // Locks connection
  for (Account account : accounts) {
    // Long processing for each account
    Thread.sleep(1000);  // Holds connection while sleeping!
  }
}

// ✅ CORRECT - Process outside transaction
@Transactional(readOnly = true)
public List<Account> getAllAccounts() {
  return accountRepository.findAll();
  // Connection returned immediately
}

public void processLargeDataset() {
  List<Account> accounts = getAllAccounts();
  for (Account account : accounts) {
    // Process without holding connection
    Thread.sleep(1000);  // No connection held
  }
}
```

**Check 3: Connection Leak**
```properties
# Enable leak detection
spring.datasource.hikari.leak-detection-threshold=60000

# Logs will show:
# WARNING: Connection leak detected: java.lang.Exception
#   at <Connection creation stack trace>
```

### Solutions

```properties
# application-prod.properties
spring.datasource.hikari.maximum-pool-size=25
spring.datasource.hikari.minimum-idle=5
spring.datasource.hikari.connection-timeout=30000
spring.datasource.hikari.idle-timeout=600000
spring.datasource.hikari.max-lifetime=1800000
spring.datasource.hikari.leak-detection-threshold=60000
```

---

## Common Error Messages & Quick Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `BeanCreationException: No bean named 'experienceApiConfig'` | Missing @EnableExperienceAPI | Add annotation to @SpringBootApplication |
| `Correlation ID not in MDC` | CorrelationIdFilter not executing | Check filter order (must be 0) |
| `Connection pool exhausted` | Pool too small or connections leaking | Increase max-pool-size or fix transaction lengths |
| `Service B cannot reach Service A` | Service discovery or network issue | Verify DNS, verify circuit breaker status |
| `ExceptionFilter not catching` | Wrong exception type thrown | Use GenericException or subclasses |

---

## Preventive Best Practices

### Testing

```java
// Always test with full EPS framework
@SpringBootTest(webEnvironment = RANDOM_PORT)
@ActiveProfiles("test")
public class OrderControllerTest {
  @LocalServerPort
  private int port;

  @Autowired
  private TestRestTemplate restTemplate;

  @Test
  void shouldPropagateCorrelationId() {
    HttpHeaders headers = new HttpHeaders();
    headers.set("Correlation-ID", "test-123");

    ResponseEntity<Response<Order>> response = restTemplate.exchange(
      "/api/orders",
      POST,
      new HttpEntity<>(createOrderRequest(), headers),
      new ParameterizedTypeReference<Response<Order>>() {}
    );

    // Verify correlation ID in response
    assertThat(response.getHeaders().getFirst("Correlation-ID"))
      .isEqualTo("test-123");
  }
}
```

### Monitoring

```bash
# Set up continuous monitoring
watch -n 1 'curl -s http://localhost:8080/actuator/health | jq'

# Check key metrics
curl http://localhost:8080/actuator/metrics | jq '.names[]' | grep -E "http|db"
```

---

## Getting Help

### Where to Look

1. **Logs First** - Always enable DEBUG level for MCA2 modules
2. **Metrics** - `/actuator/metrics` endpoint shows health
3. **Health Check** - `/actuator/health` detailed information
4. **Stack Traces** - Save full exception stack for debugging
5. **Thread Dumps** - If hung, capture with `jstack`

### Collecting Diagnostics

```bash
#!/bin/bash
# Collect diagnostics for troubleshooting

echo "=== System Info ===" > diagnostics.txt
uname -a >> diagnostics.txt
java -version >> diagnostics.txt

echo -e "\n=== Application Health ===" >> diagnostics.txt
curl -s http://localhost:8080/actuator/health >> diagnostics.txt

echo -e "\n=== Active Beans ===" >> diagnostics.txt
curl -s http://localhost:8080/actuator/beans | jq '.contexts.application.beans | keys' >> diagnostics.txt

echo -e "\n=== Recent Logs ===" >> diagnostics.txt
tail -100 /var/log/order-service/application.log >> diagnostics.txt

echo "Diagnostics saved to diagnostics.txt"
```

---

## Next Steps

1. **Identify Symptom** — Use matrix above to find your issue
2. **Follow Root Cause Analysis** — Check each suggested verification
3. **Apply Solution** — Implement provided code examples
4. **Verify Fix** — Test with provided debugging techniques
5. **Monitor Prevention** — Implement best practices to avoid recurrence

**Troubleshooting Guide enables rapid issue resolution.**

