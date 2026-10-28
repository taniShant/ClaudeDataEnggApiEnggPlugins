# Template Method Pattern: Reusable Filter Architecture

## Executive Summary

The **Template Method Pattern** provides the foundation for MCA2's filter architecture via Spring's `OncePerRequestFilter` base class. It defines a template (skeleton) of the filter algorithm, allowing subclasses to override specific steps without changing the algorithm's structure. This enables consistent, reusable filter implementations across all MCA2 filters.

**Pattern Definition (Gang of Four):**
> "Define the skeleton of an algorithm in a base class, but let subclasses override specific steps without changing the algorithm's structure."

**MCA2 Application:**
- **Template Method:** OncePerRequestFilter (Spring Framework)
- **Algorithm Skeleton:** doFilter() → doFilterInternal() → response
- **Subclasses:** CorrelationIdFilter, ExceptionFilter, etc.
- **Extension Points:** doFilterInternal(), shouldNotFilter()

---

## Template Method Structure in Filters

```
┌────────────────────────────────────────────────────────────┐
│ OncePerRequestFilter (Template)                            │
├────────────────────────────────────────────────────────────┤
│                                                             │
│ doFilter() {                                               │
│   // 1. Check if already filtered (algorithm structure)   │
│   if (alreadyFiltered) {                                  │
│     filterChain.doFilter();  // Skip                      │
│     return;                                                │
│   }                                                        │
│                                                             │
│   // 2. Mark as filtered                                  │
│   setAttribute(ALREADY_FILTERED, true);                   │
│                                                             │
│   try {                                                    │
│     // 3. Call template method (to be overridden)        │
│     doFilterInternal(request, response, filterChain);    │
│   } finally {                                              │
│     // 4. Cleanup                                         │
│     removeAttribute(ALREADY_FILTERED);                    │
│   }                                                        │
│ }                                                          │
│                                                             │
│ // Template method to override in subclasses             │
│ protected abstract void doFilterInternal(                 │
│   HttpServletRequest request,                            │
│   HttpServletResponse response,                          │
│   FilterChain filterChain                                │
│ ) throws ServletException, IOException;                  │
│                                                             │
│ // Hook method (optional override)                        │
│ protected boolean shouldNotFilter(HttpServletRequest req) │
│   throws ServletException {                               │
│   return false;  // Override to exclude paths            │
│ }                                                          │
│ }                                                          │
│                                                             │
└────────────────────────────────────────────────────────────┘
                           ▲
                           │ extends
                           │
┌────────────────────────────────────────────────────────────┐
│ Concrete Filter: CorrelationIdFilter                       │
├────────────────────────────────────────────────────────────┤
│                                                             │
│ @Override                                                  │
│ protected void doFilterInternal(                           │
│   HttpServletRequest request,                             │
│   HttpServletResponse response,                           │
│   FilterChain filterChain                                 │
│ ) throws ServletException, IOException {                  │
│   // Specific implementation (can assume                  │
│   // OncePerRequestFilter handled the structure)          │
│                                                             │
│   String correlationId = ...  // Generate                │
│   CorrelationIdContext.set(correlationId);               │
│   try {                                                    │
│     filterChain.doFilter(request, response);             │
│   } finally {                                              │
│     CorrelationIdContext.clear();                         │
│   }                                                        │
│ }                                                          │
│                                                             │
│ @Override                                                  │
│ protected boolean shouldNotFilter(HttpServletRequest req) │
│   throws ServletException {                               │
│   // Override to exclude health check endpoints          │
│   return req.getRequestURI().startsWith("/health");      │
│ }                                                          │
│ }                                                          │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

---

## OncePerRequestFilter: Base Class Template

### Source (Spring Framework)

**Location:** `org.springframework.web.filter.OncePerRequestFilter`

```java
public abstract class OncePerRequestFilter extends HttpServletFilter {

    // Template method - defines algorithm structure
    @Override
    public final void doFilter(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {

        // STEP 1: Generate already-filtered attribute name
        String alreadyFilteredAttributeName =
            getAlreadyFilteredAttributeName();

        // STEP 2: Check if filter already executed for this request
        if (request.getAttribute(alreadyFilteredAttributeName) != null) {
            // Already filtered - skip (prevents double execution)
            filterChain.doFilter(request, response);
            return;
        }

        // STEP 3: Mark request as filtered
        request.setAttribute(alreadyFilteredAttributeName, Boolean.TRUE);

        try {
            // STEP 4: Call abstract method for subclass implementation
            // This is the extension point - subclasses override this
            doFilterInternal(request, response, filterChain);

        } finally {
            // STEP 5: Cleanup - remove attribute
            request.removeAttribute(alreadyFilteredAttributeName);
        }
    }

    // ABSTRACT TEMPLATE METHOD - subclasses must implement
    protected abstract void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException;

    // HOOK METHOD - subclasses can optionally override
    protected boolean shouldNotFilter(HttpServletRequest request)
        throws ServletException {
        return false;  // By default, apply to all requests
    }

    // Helper
    protected String getAlreadyFilteredAttributeName() {
        return getClass().getName() + ".FILTERED";
    }
}
```

### Why This Design?

| Aspect | Benefit |
|--------|---------|
| **Algorithm Encapsulation** | Structure is fixed, details are extensible |
| **Double Execution Prevention** | Handles complex request dispatch scenarios |
| **Finally Block** | Guarantees cleanup even with exceptions |
| **Hook Method** | Optional customization via shouldNotFilter() |
| **Consistent Pattern** | All filters follow same structure |

---

## Implementing Custom Filters with Template Method

### Basic Filter Implementation

```java
public class CustomLoggingFilter extends OncePerRequestFilter {

    private static final Logger logger =
        LoggerFactory.getLogger(CustomLoggingFilter.class);

    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {

        // BEFORE: This code runs before the request is processed
        String method = request.getMethod();
        String path = request.getRequestURI();

        logger.info("Request: {} {}", method, path);
        long startTime = System.currentTimeMillis();

        try {
            // Pass control to next filter in chain
            // (or to DispatcherServlet if this is last filter)
            filterChain.doFilter(request, response);

        } finally {
            // AFTER: This code runs after response is generated
            long duration = System.currentTimeMillis() - startTime;
            int statusCode = response.getStatus();

            logger.info("Response: {} {} - {} ms",
                statusCode,
                path,
                duration);
        }
    }

    // OPTIONAL: Skip filter for certain paths
    @Override
    protected boolean shouldNotFilter(HttpServletRequest request)
        throws ServletException {

        String path = request.getRequestURI();
        return path.startsWith("/actuator/")   // Skip actuator
            || path.startsWith("/health")      // Skip health
            || path.startsWith("/swagger-ui"); // Skip Swagger
    }
}
```

### Advanced: Multi-Purpose Filter

```java
public class AuthenticationFilter extends OncePerRequestFilter {

    @Autowired
    private AuthenticationProvider authProvider;

    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {

        // BEFORE: Extract and validate credentials
        String token = extractToken(request);

        if (token == null) {
            // No token - might be public endpoint
            filterChain.doFilter(request, response);
            return;
        }

        try {
            // Validate token
            Authentication auth = authProvider.authenticate(token);

            // Store in security context for handlers to access
            SecurityContextHolder.getContext().setAuthentication(auth);

            // PROCEED TO NEXT FILTER
            filterChain.doFilter(request, response);

        } catch (InvalidTokenException ex) {
            // HANDLE ERROR: Write error response
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType("application/json");
            response.getWriter().write(
                "{\"error\": \"Invalid token\"}"
            );

        } finally {
            // AFTER: Cleanup security context
            SecurityContextHolder.clearContext();
        }
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request)
        throws ServletException {

        // Only apply to API endpoints that require auth
        String path = request.getRequestURI();
        return !path.startsWith("/api/");
    }

    private String extractToken(HttpServletRequest request) {
        String header = request.getHeader("Authorization");
        if (header != null && header.startsWith("Bearer ")) {
            return header.substring(7);
        }
        return null;
    }
}
```

---

## Extension Points in Template Method

### Extension Point 1: doFilterInternal()

**Primary override point** - subclasses implement this to define filter behavior

```java
@Override
protected void doFilterInternal(...) throws ServletException, IOException {
    // Your filter logic here
    filterChain.doFilter(request, response);
}
```

### Extension Point 2: shouldNotFilter()

**Hook method** - optionally override to skip filter for certain paths

```java
@Override
protected boolean shouldNotFilter(HttpServletRequest request)
    throws ServletException {

    // Return true to SKIP filter, false to APPLY filter
    return request.getRequestURI().startsWith("/health");
}
```

### Extension Point 3: getFilterName()

**Optional** - provide custom filter name for debugging

```java
@Override
public String getFilterName() {
    return "CustomAuthenticationFilter";
}
```

---

## MCA2 Filter Examples Using Template Method

### Example 1: CorrelationIdFilter

**Uses:**
- doFilterInternal() to generate and store correlation ID
- finally block to cleanup
- No shouldNotFilter() override (applies to all)

```java
public class CorrelationIdFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {

        // EXTRACT or GENERATE correlation ID
        String correlationId = request.getHeader("Correlation-ID");
        if (correlationId == null) {
            correlationId = UUID.randomUUID().toString();
        }

        // STORE in thread-local
        CorrelationIdContext.set(correlationId);
        response.setHeader("Correlation-ID", correlationId);

        try {
            filterChain.doFilter(request, response);
        } finally {
            // CLEANUP
            CorrelationIdContext.clear();
        }
    }
}
```

### Example 2: ExceptionFilter

**Uses:**
- doFilterInternal() wrapped in try-catch
- Converts exceptions to Response<T>
- shouldNotFilter() to skip certain endpoints

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
            // HANDLE EXCEPTIONS
            int statusCode = ResponseHttpStatus.getStatusCode(ex);
            response.setStatus(statusCode);
            response.setContentType("application/json");

            // Build error response
            Response<?> errorResponse = buildErrorResponse(ex);
            response.getWriter().write(
                objectMapper.writeValueAsString(errorResponse)
            );
        }
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        // Skip for static resources
        return request.getRequestURI().endsWith(".js")
            || request.getRequestURI().endsWith(".css");
    }
}
```

### Example 3: DisableSessionFilter

**Uses:**
- doFilterInternal() to wrap request
- No error handling needed
- Template method prevents double wrapping

```java
public class DisableSessionFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {

        // WRAP request to prevent session creation
        HttpServletRequest wrappedRequest =
            new HttpServletRequestDisableSessionWrapper(request);

        // PROCEED with wrapped request
        filterChain.doFilter(wrappedRequest, response);
    }
}
```

---

## Benefits of Template Method in Filters

| Benefit | How Achieved |
|---------|-------------|
| **Consistency** | All filters follow same structure |
| **Reusability** | Common logic in base class, not repeated |
| **Prevents Bugs** | Already-filtered attribute prevents double execution |
| **Simplicity** | Subclasses only implement specific logic |
| **Error Safety** | finally block guarantees cleanup |
| **Extensibility** | Hook methods for customization |
| **Testability** | Clear separation of concerns |

---

## Anti-Patterns: What NOT To Do

### ❌ Anti-Pattern 1: Not Calling doFilter()

```java
// BAD - Breaks the chain
public class BrokenFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(...) {
        logger.info("Filter applied");
        // ❌ Missing: filterChain.doFilter(request, response);
        // Result: Rest of chain doesn't execute
    }
}
```

### ✅ Correct Approach

```java
// GOOD - Always continue chain
public class ProperFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(...) {
        logger.info("Before");
        try {
            filterChain.doFilter(request, response);  // ✓
        } finally {
            logger.info("After");
        }
    }
}
```

### ❌ Anti-Pattern 2: Overriding doFilter()

```java
// BAD - Breaks the template structure
public class WrongFilter extends OncePerRequestFilter {
    @Override
    public void doFilter(  // ❌ Should NOT override
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {
        // This breaks the algorithm structure
    }
}
```

### ✅ Correct Approach

```java
// GOOD - Override only doFilterInternal()
public class CorrectFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(  // ✓ Correct method
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {
        // Implementation
    }
}
```

### ❌ Anti-Pattern 3: Not Cleaning Up Resources

```java
// BAD - Resource leak
public class LeakyFilter extends OncePerRequestFilter {
    private ThreadLocal<String> context = new ThreadLocal<>();

    @Override
    protected void doFilterInternal(...) {
        context.set("value");
        filterChain.doFilter(request, response);
        // ❌ Missing cleanup - ThreadLocal not cleared
    }
}
```

### ✅ Correct Approach

```java
// GOOD - Always cleanup in finally
public class CleanFilter extends OncePerRequestFilter {
    private ThreadLocal<String> context = new ThreadLocal<>();

    @Override
    protected void doFilterInternal(...) {
        context.set("value");
        try {
            filterChain.doFilter(request, response);
        } finally {
            context.remove();  // ✓ Always cleanup
        }
    }
}
```

---

## Complete Filter Implementation Checklist

### ✅ Template Method Filter Checklist

```
□ Extends OncePerRequestFilter (not HttpFilter)
□ Implements doFilterInternal() (not doFilter())
□ Calls filterChain.doFilter() to continue chain
□ Uses try-finally for cleanup
□ Implements shouldNotFilter() if excluding paths
□ Logs with correlation ID
□ Handles exceptions gracefully
□ Registers with FilterRegistrationBean
□ Sets correct order value (0-20 for core filters)
□ Tested with MockHttpServletRequest/Response
□ No direct attribute access to request scope
□ Uses WebUtils for context access
□ Thread-local cleanup in finally block
```

---

## Troubleshooting Template Method Issues

### Issue: Filter Executing Twice

**Cause:** Not extending OncePerRequestFilter

**Solution:**
```java
// ✓ Extends OncePerRequestFilter (prevents double execution)
public class MyFilter extends OncePerRequestFilter { }

// ❌ Directly implements Filter (no double-execution prevention)
public class MyFilter implements Filter { }
```

### Issue: Resources Not Cleaned Up

**Cause:** No finally block

**Solution:**
```java
try {
    filterChain.doFilter(request, response);
} finally {
    context.remove();  // ✓ Always cleanup
    threadLocal.remove();
}
```

### Issue: shouldNotFilter() Not Working

**Cause:** Returning wrong boolean value

**Solution:**
```java
@Override
protected boolean shouldNotFilter(HttpServletRequest request) {
    // Return TRUE to SKIP filter
    // Return FALSE to APPLY filter
    return request.getRequestURI().startsWith("/health");
}
```

---

## Next Steps

1. **Extend OncePerRequestFilter** - Never directly implement Filter
2. **Implement doFilterInternal()** - Define your filter logic
3. **Use try-finally** - Always cleanup resources
4. **Override shouldNotFilter()** - Exclude specific paths if needed
5. **Register as Bean** - Use FilterRegistrationBean
6. **Test execution** - Verify order and behavior

---

## Quick Reference: Template Method Pattern

```
OncePerRequestFilter (Template)
    │
    ├─ Ensures single execution per request
    ├─ Handles already-filtered attribute
    ├─ Calls doFilterInternal() for subclass implementation
    ├─ Guarantees finally block execution
    └─ Provides shouldNotFilter() hook

Subclass Implementation
    ├─ Override doFilterInternal()
    ├─ Implement specific filter logic
    ├─ Always call filterChain.doFilter()
    ├─ Use try-finally for cleanup
    └─ Optionally override shouldNotFilter()
```

**Template Method Pattern provides a consistent, safe foundation for all MCA2 filters.**
