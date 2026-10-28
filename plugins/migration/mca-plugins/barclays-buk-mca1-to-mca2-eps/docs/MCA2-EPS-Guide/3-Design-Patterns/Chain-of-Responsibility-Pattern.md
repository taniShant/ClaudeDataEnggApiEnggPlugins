# Chain of Responsibility Pattern: Filter Chain Execution

## Executive Summary

The **Chain of Responsibility Pattern** is the primary pattern for the MCA2 **Filter Chain**, enabling a series of filters to process HTTP requests in a defined order. Each filter has the opportunity to process the request, make modifications, and decide whether to pass it to the next filter in the chain.

**Pattern Definition (Gang of Four):**
> "Avoid coupling the sender of a request to its receiver by giving more than one object a chance to handle the request. Chain the handlers so that the request travels along the chain."

**MCA2 Application:**
- **Chain:** Filter chain (CorrelationId → Exception → DisableSession → MultiRead → ...)
- **Handler:** OncePerRequestFilter subclass
- **Request:** HttpServletRequest and HttpServletResponse
- **Propagation:** filterChain.doFilter(request, response) passes to next

---

## Chain of Responsibility Structure

```
HTTP Request
    │
    ├─────────────────────────────────────────────┐
    │                                             │
    ▼                                             │
┌─────────────────────────────────┐              │
│ Filter 0: CorrelationIdFilter   │              │
│ (Order 0)                       │              │
│                                 │              │
│ Before:                         │              │
│ • Generate correlation ID       │              │
│ • Store in thread-local         │              │
│                                 │              │
│ filterChain.doFilter(req, res)──┼──┐           │
│         (passes to next)        │  │           │
│                                 │  │           │
│ After:                          │  │           │
│ • Add response header           │  │           │
│ • Clean up thread-local         │◄─┤─ After   │
└─────────────────────────────────┘  │           │
                                      │           │
    ┌─────────────────────────────────┘           │
    │                                             │
    ▼                                             │
┌─────────────────────────────────┐              │
│ Filter 1: ExceptionFilter       │              │
│ (Order 1)                       │              │
│                                 │              │
│ try {                           │              │
│   filterChain.doFilter(req, res)┼──┐           │
│       (passes to next)          │  │           │
│ } catch (Exception ex) {        │  │           │
│   Convert to Response<T>        │  │           │
│   Write to response             │  │           │
│ }                               │  │           │
│                                 │◄─┤─ After   │
└─────────────────────────────────┘  │           │
                                      │           │
    ┌─────────────────────────────────┘           │
    │                                             │
    ▼                                             │
┌─────────────────────────────────┐              │
│ Filter 2: DisableSessionFilter  │              │
│ (Order 2)                       │              │
│                                 │              │
│ Wrap request                    │              │
│ filterChain.doFilter(req, res)──┼──┐           │
│                                 │  │           │
│                                 │◄─┤─ After   │
└─────────────────────────────────┘  │           │
                                      │           │
    ┌─────────────────────────────────┘           │
    │                                             │
    ▼                                             │
┌─────────────────────────────────┐              │
│ Filter 3: MultiReadRequestFilter│              │
│ (Order 3)                       │              │
│                                 │              │
│ Cache request body              │              │
│ filterChain.doFilter(req, res)──┼──┐           │
│                                 │  │           │
│                                 │◄─┤─ After   │
└─────────────────────────────────┘  │           │
                                      │           │
    ┌─────────────────────────────────┘           │
    │                                             │
    ▼                                             │
┌─────────────────────────────────┐              │
│ Other Filters (Order 4+)        │              │
│ • OAuthValidator                │              │
│ • DdosFilter                    │              │
│ • Validation, etc.              │              │
│                                 │              │
│ filterChain.doFilter(req, res)──┼──┐           │
│                                 │  │           │
│                                 │◄─┤─ After   │
└─────────────────────────────────┘  │           │
                                      │           │
    ┌─────────────────────────────────┘           │
    │                                             │
    ▼                                             │
┌──────────────────────────────────────┐         │
│ DispatcherServlet                    │         │
│ Routes to Handler/Controller         │         │
│ Business logic executes              │         │
└──────────────────────────────────────┘         │
                                                  │
                Response/Exception               │
                         ▲                       │
                         │                       │
                    ─────┴───────────────────────┘
                    Response travels back through
                    chain in reverse order
```

---

## Filter Chain: Request Flow

### Phase 1: REQUEST (Forward Direction)

```
Request enters from client
    │
    ├─ Filter 0: Before logic
    │   ├─ Generate correlation ID
    │   ├─ Add to thread-local
    │   └─ Call filterChain.doFilter()
    │
    ├─ Filter 1: Before logic
    │   ├─ Wrap with try-catch
    │   └─ Call filterChain.doFilter()
    │
    ├─ Filter 2: Before logic
    │   ├─ Wrap request
    │   └─ Call filterChain.doFilter()
    │
    ├─ Filter 3: Before logic
    │   ├─ Cache request body
    │   └─ Call filterChain.doFilter()
    │
    ├─ Other Filters...
    │
    └─ DispatcherServlet
        └─ Business logic executes
```

### Phase 2: RESPONSE (Reverse Direction)

```
Response/Exception generated
    │
    └─ Exception Filter: After logic
        ├─ Catch any exceptions
        ├─ Convert to Response<T>
        ├─ Set HTTP status
        └─ Write response

    └─ Other Filters: After logic
        ├─ Post-processing
        ├─ Cleanup
        └─ Return response

    └─ MultiRead Filter: After logic
        └─ Cleanup

    └─ DisableSession Filter: After logic
        └─ Cleanup

    └─ Correlation ID Filter: After logic
        ├─ Add response header
        ├─ Clear thread-local
        └─ Return to client

Response sent to client
```

---

## Filter Chain: Code Implementation

### Base Class: OncePerRequestFilter

**Location:** Spring Framework (spring-webmvc)

```java
// Spring's base class for filters
public abstract class OncePerRequestFilter extends HttpServlet Filter {

    protected abstract void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException;

    @Override
    public final void doFilter(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {

        String alreadyFilteredAttributeName = getAlreadyFilteredAttributeName();

        if (request.getAttribute(alreadyFilteredAttributeName) != null) {
            // Filter already executed, skip (prevents double execution)
            filterChain.doFilter(request, response);
        } else {
            request.setAttribute(alreadyFilteredAttributeName, Boolean.TRUE);

            try {
                // Execute filter logic
                doFilterInternal(request, response, filterChain);
            } finally {
                // Always clean up
                request.removeAttribute(alreadyFilteredAttributeName);
            }
        }
    }
}
```

**Key Benefit:** Ensures each filter runs exactly once per request (prevents double execution in forwarded requests)

### MCA2 Filter Pattern: CorrelationIdFilter

**Location:** `mca-filter-core/src/main/java/com/barclays/global/mca/libs/filters/CorrelationIdFilter.java`

```java
public class CorrelationIdFilter extends OncePerRequestFilter {

    private static final Logger logger =
        LoggerFactory.getLogger(CorrelationIdFilter.class);

    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {

        // === BEFORE: First filter in chain ===
        String correlationId = request.getHeader("Correlation-ID");

        if (correlationId == null || correlationId.isEmpty()) {
            correlationId = UUID.randomUUID().toString();
        }

        // Store in thread-local for access throughout request
        CorrelationIdContext.set(correlationId);

        // Set response header
        response.setHeader("Correlation-ID", correlationId);

        // Set thread name for thread pools
        String originalThreadName = Thread.currentThread().getName();
        Thread.currentThread().setName(correlationId);

        logger.info("Request started: {}", correlationId);

        try {
            // === PASS TO NEXT FILTER ===
            filterChain.doFilter(request, response);

        } finally {
            // === AFTER: Cleanup (when response returns) ===
            CorrelationIdContext.clear();
            Thread.currentThread().setName(originalThreadName);

            logger.info("Request completed: {}", correlationId);
        }
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request)
        throws ServletException {

        // Skip filter for certain paths if needed
        String path = request.getRequestURI();
        return path.startsWith("/actuator/health");
    }
}
```

### MCA2 Filter Pattern: ExceptionFilter

**Location:** `mca-filter-core/src/main/java/com/barclays/global/mca/libs/filters/ExceptionFilter.java`

```java
public class ExceptionFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {

        try {
            // === PASS TO NEXT FILTER (wrapped in try-catch) ===
            filterChain.doFilter(request, response);

        } catch (Exception ex) {
            // === CATCH EXCEPTIONS FROM CHAIN ===

            // Map exception to HTTP status
            int statusCode = ResponseHttpStatus.getStatusCode(ex);
            response.setStatus(statusCode);
            response.setContentType("application/json");

            // Build error response
            Response<?> errorResponse;
            if (ex instanceof GenericException) {
                Message message = ((GenericException) ex).toMessage();
                errorResponse = Response.assemble()
                    .error(List.of(message))
                    .withStatusCode(statusCode);
            } else {
                errorResponse = Response.assemble()
                    .error(List.of(
                        new Message("INTERNAL_ERROR", ex.getMessage())
                    ))
                    .withStatusCode(500);
            }

            // === WRITE ERROR RESPONSE ===
            response.getWriter().write(
                objectMapper.writeValueAsString(errorResponse)
            );

            logger.error("Request exception: {}",
                CorrelationIdContext.get(),
                ex);
        }
    }
}
```

---

## Chain Ordering: Critical for Functionality

### Recommended Order

```
Order 0:  CorrelationIdFilter
          └─ MUST be first (needed by all downstream components)

Order 1:  ExceptionFilter
          └─ MUST be second (wraps entire chain)

Order 2:  DisableSessionFilter
          └─ Prevent session creation

Order 3:  MultiReadRequestFilter
          └─ Cache request body

Order 4+: Optional/Conditional Filters
          ├─ OAuthValidatorFilter
          ├─ DdosFilter
          ├─ ValidationFilter
          ├─ RequestWhitelistingFilter
          └─ [others]

Order 10+: Custom Application Filters
          └─ Application-specific

Order 20+: Monitoring/Cleanup Filters
          └─ Health checks, metrics
```

### Why Order Matters

**Correct Order (CorrelationId → Exception):**
```
Request enters CorrelationId filter
    ├─ Generate correlation ID
    ├─ Store in thread-local
    └─ Pass to Exception filter
        └─ Wrap with try-catch
        └─ Pass to DisableSession filter
        └─ ...
        └─ Exception occurs
    └─ Exception filter catches
    └─ Logs with correlation ID ← WORKS!
```

**Wrong Order (Exception → CorrelationId):**
```
Request enters Exception filter
    ├─ Wrap with try-catch
    └─ Pass to CorrelationId filter
    └─ Generate correlation ID
    └─ ...
    └─ Exception occurs
    └─ Exception filter catches
    └─ Try to log with correlation ID ← NULL! (not set yet)
```

---

## How to Add Custom Filters to Chain

### Pattern 1: Register via FilterRegistrationBean

```java
@Configuration
public class CustomFilterConfig {

    @Bean
    public FilterRegistrationBean<CustomAuthFilter>
        customAuthFilterRegistration() {

        CustomAuthFilter filter = new CustomAuthFilter();

        FilterRegistrationBean<CustomAuthFilter> bean =
            new FilterRegistrationBean<>(filter);

        bean.setOrder(11);                    // After core filters
        bean.addUrlPatterns("/api/*");        // Apply to /api/* only
        bean.setFilterName("CustomAuthFilter");

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

        // Verify correlation ID is available
        String correlationId = CorrelationIdContext.get();
        logger.debug("CustomAuth for correlation: {}", correlationId);

        // Proceed to next filter
        filterChain.doFilter(request, response);
    }
}
```

### Pattern 2: Conditional Registration

```java
@Bean
@ConditionalOnProperty(
    name = "custom.auth.enabled",
    havingValue = "true"
)
public FilterRegistrationBean<CustomAuthFilter>
    customAuthFilterRegistration() {
    // Only register if property is true
}
```

### Pattern 3: URL Pattern Matching

```java
@Bean
public FilterRegistrationBean<CustomFilter>
    customFilterRegistration() {

    FilterRegistrationBean<CustomFilter> bean =
        new FilterRegistrationBean<>(new CustomFilter());

    bean.setOrder(11);
    bean.addUrlPatterns("/api/protected/*");  // Only protected endpoints
    bean.addUrlPatterns("/admin/*");          // And admin endpoints
    // Exclude patterns if needed
    bean.addInitParameter("excludePaths", "/api/public/*");

    return bean;
}
```

---

## Filter Chain: Complete Execution Flow

### Example: Card Lock Request

```
1. HTTP POST /api/card-control/lock
   headers: X-UserContext, Correlation-ID (optional)
   body: {"cardId": "CARD123", "reason": "LOST"}

2. CorrelationIdFilter (Order 0)
   - Extract/generate correlation ID: "550e8400-e29b-41d4-a716-446655440000"
   - CorrelationIdContext.set("550e8400-...")
   - response.setHeader("Correlation-ID", "550e8400-...")
   - Call filterChain.doFilter()

3. ExceptionFilter (Order 1)
   - Wrap remaining chain in try-catch
   - Call filterChain.doFilter()

4. DisableSessionFilter (Order 2)
   - Wrap request to prevent getSession()
   - Call filterChain.doFilter()

5. MultiReadRequestFilter (Order 3)
   - Cache request body: {"cardId": "CARD123", ...}
   - Call filterChain.doFilter()

6. OAuthValidatorFilter (Order 4)
   - Extract JWT from Authorization header
   - Validate signature
   - Set user context
   - Call filterChain.doFilter()

7. DdosFilter (Order 5)
   - Check rate limit for this user/channel
   - Allow request
   - Call filterChain.doFilter()

8. DispatcherServlet
   - Route to CardControlController
   - Invoke lockCard(@IOLContext IOLSchema context, ...)

9. CardControlController.lockCard()
   - Receive injected context
   - Call cardService.lockCard(context, "CARD123", "LOST")

10. CardService.lockCard()
    - Access context via WebUtils.getIOLSchema()
    - Update database
    - Build Response<LockResult>
    - Return response

11. ExceptionFilter (response phase)
    - No exception occurred
    - Response passes through

12. Other Filters (response phase)
    - Post-processing
    - Response passes through

13. CorrelationIdFilter (response phase)
    - Response header already set
    - Clean up thread-local
    - Response sent to client

Output:
HTTP/1.1 200 OK
Correlation-ID: 550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json

{
  "data": {"status": "LOCKED", "lockTime": "2025-02-26T12:00:00Z"},
  "status": "SUCCESS",
  "statusCode": "200"
}
```

---

## Chain of Responsibility: Benefits

| Benefit | How Achieved |
|---------|-------------|
| **Separation of Concerns** | Each filter has single responsibility |
| **Flexibility** | Add/remove filters without changing others |
| **Dynamic Behavior** | Conditional filter registration |
| **Ordering Control** | Define execution sequence precisely |
| **Exception Handling** | Centralized via ExceptionFilter |
| **Performance Monitoring** | Track time spent in each filter |
| **Security Enforcement** | Multiple validation layers |

---

## Anti-Patterns: What NOT To Do

### ❌ Anti-Pattern 1: Breaking the Chain

```java
// BAD - Doesn't call filterChain.doFilter()
public class BrokenFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {

        response.getWriter().write("Filtered!");
        // ❌ MISSING: filterChain.doFilter(request, response);
        // Result: Rest of chain doesn't execute, response incomplete
    }
}
```

### ✅ Correct Approach

```java
// GOOD - Always call filterChain.doFilter()
public class ProperFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {

        // Before
        logger.info("Before logic");

        try {
            filterChain.doFilter(request, response);  // ✓ REQUIRED
        } finally {
            // After
            logger.info("After logic");
        }
    }
}
```

### ❌ Anti-Pattern 2: Wrong Filter Order

```gradle
// BAD - Exception filter AFTER other filters
bean.setOrder(0);   // Exception filter
// Other filters with Order 1, 2, 3...

// Result: CorrelationId not set when Exception filter tries to use it
```

### ✅ Correct Approach

```gradle
// GOOD - Correct order
bean.setOrder(0);   // CorrelationIdFilter FIRST
bean.setOrder(1);   // ExceptionFilter SECOND
bean.setOrder(2);   // Other filters
```

### ❌ Anti-Pattern 3: Swallowing Exceptions

```java
// BAD - Catches exception without re-throwing or handling
public class ProblematicFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(...) throws ServletException, IOException {
        try {
            filterChain.doFilter(request, response);
        } catch (Exception ex) {
            logger.error("Error", ex);
            // ❌ MISSING: throw ex; or handle properly
            // Result: Client never knows about error
        }
    }
}
```

### ✅ Correct Approach

```java
// GOOD - Handle exception or re-throw
public class ProperFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(...) throws ServletException, IOException {
        try {
            filterChain.doFilter(request, response);
        } catch (SpecificException ex) {
            // Handle expected exceptions
            response.setStatus(400);
            response.getWriter().write(errorJson);
        } catch (Exception ex) {
            // Re-throw unexpected exceptions (ExceptionFilter will catch)
            throw ex;
        }
    }
}
```

---

## Troubleshooting Chain Issues

### Issue: Filter Not Executing

**Check:**
1. Is FilterRegistrationBean created?
2. Is @ConditionalOnProperty true?
3. Does URL pattern match request path?
4. Is filter order between 0-20?

```java
@Bean
@ConditionalOnProperty(name = "custom.filter.enabled", havingValue = "true")  // ✓
public FilterRegistrationBean<CustomFilter> registration() {
    FilterRegistrationBean bean = new FilterRegistrationBean<>(new CustomFilter());
    bean.setOrder(11);                               // ✓
    bean.addUrlPatterns("/api/*");                  // ✓
    bean.setName("CustomFilter");                   // ✓
    return bean;
}
```

### Issue: CorrelationId Null in Filter

**Cause:** Filter executes before CorrelationIdFilter

**Solution:**
```java
// Verify CorrelationIdFilter has Order 0
// Your filter should have Order > 0

// If needed to run first, use Order -1 (not recommended)
bean.setOrder(0);   // CorrelationIdFilter
bean.setOrder(1);   // Your filter
```

### Issue: Response Already Committed

**Cause:** Trying to set status after response has been written

**Solution:**
```java
// Don't write response in filter if another filter will write it
// Use ExceptionFilter pattern: wrap chain in try-catch

try {
    filterChain.doFilter(request, response);
} catch (Exception ex) {
    // Only write response if not committed
    if (!response.isCommitted()) {
        response.setStatus(500);
        response.getWriter().write(errorJson);
    }
}
```

---

## Next Steps

1. **Understand filter ordering** - Correlation ID first, Exception second
2. **Review core filters** - Study CorrelationIdFilter and ExceptionFilter
3. **Create custom filter** - Follow FilterRegistrationBean pattern
4. **Test filter execution** - Verify order with logging
5. **Handle exceptions** - Let ExceptionFilter catch them

---

## Quick Reference: Chain of Responsibility

```
HTTP Request
    │
    ├─ Filter 0 (Before) ──┐
    │                      │
    ├─ Filter 1 (Before)   │ Request Phase (In Order)
    │                      │
    ├─ Filter N (Before) ──┤
    │                      │
    ├─ Business Logic      │
    │                      │
    ├─ Filter N (After) ──┐│
    │                     ││ Response Phase (Reverse Order)
    ├─ Filter 1 (After)   ││
    │                     ││
    ├─ Filter 0 (After) ──┘│
    │
    └─ HTTP Response

CRITICAL: Every filter MUST call filterChain.doFilter()
CRITICAL: CorrelationIdFilter MUST be Order 0
CRITICAL: ExceptionFilter MUST be Order 1
CRITICAL: Always use try-finally for cleanup
```

**Chain of Responsibility enables clean, ordered, composable request processing.**
