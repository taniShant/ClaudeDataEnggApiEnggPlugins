# Filter Chain Configuration: Ordering, Exclusions, and Behavior

## Executive Summary

The **Filter Chain Configuration** controls how MCA2 processes HTTP requests through an ordered series of filters. This guide covers filter ordering, URL pattern exclusions, per-filter configuration, and common setup patterns.

---

## Filter Chain Execution Order

### Core Filter Ordering (Immutable)

These orders are fixed and cannot be changed:

```
Order 0:  CorrelationIdFilter
          └─ MUST be first (needed by all downstream components)
          └─ Generates/propagates correlation IDs
          └─ Stores in thread-local context

Order 1:  ExceptionFilter
          └─ MUST be second (wraps entire chain)
          └─ Catches all exceptions
          └─ Converts to Response<T>

Order 2:  DisableSessionFilter
          └─ Prevents unwanted session creation
          └─ Enforces stateless architecture

Order 3:  MultiReadRequestFilter
          └─ Caches request body
          └─ Enables body re-reading for logging/validation
```

### Optional Filter Ordering (Configurable)

```
Order 4:  OAuthValidatorFilter (if enabled)
          └─ Validates JWT tokens
          └─ Extracts claims

Order 5:  DdosFilter (if enabled)
          └─ Rate limiting
          └─ DDoS prevention

Order 300: ValidationFilter (if enabled)
          └─ Input validation against schema
          └─ Enforces constraints

Order 7:  RequestWhitelistingFilter (if enabled)
          └─ Endpoint whitelist enforcement

Order 8:  DynamicLoggingFilter (if enabled)
          └─ Dynamic log level adjustment

Order 9:  PerfLogExclusionFilter (if enabled)
          └─ Performance logging exclusions

Order 10+: Custom Application Filters
          └─ Application-specific processing
```

---

## Configuration: Enabling/Disabling Filters

### Filter Toggle Properties

```properties
# Core filters (typically always on)
mca.eps.filter.correlation-id.enabled=true
mca.eps.filter.exception.enabled=true
mca.eps.filter.disable-session.enabled=true
mca.eps.filter.multiread.enabled=true

# Optional filters (toggle as needed)
mca.security.oauth.enabled=false              # Enable OAuth
mca.security.ddos.enabled=false               # Enable DDoS prevention
mca.validation.enabled=false                  # Enable validation
mca.security.request-whitelist.enabled=false  # Enable whitelist
mca.logging.dynamic-level.enabled=false       # Enable dynamic logging
```

### Per-Filter Configuration

#### CorrelationIdFilter

```properties
# Header name for correlation ID
mca.eps.filter.correlation-id.header-name=Correlation-ID

# Generate if missing
mca.eps.filter.correlation-id.generate-if-missing=true

# Excluded paths (skip correlation ID generation)
mca.eps.filter.correlation-id.excluded-paths[0]=/actuator/health
```

#### ExceptionFilter

```properties
# Include stack traces in error response
mca.eps.filter.exception.stack-trace-enabled=false

# Include detailed error messages
mca.eps.filter.exception.detailed-error-messages=false

# Wrap errors in data field
mca.eps.filter.exception.wrap-errors-in-data=false
```

#### MultiReadRequestFilter

```properties
# Maximum buffer size for cached request body
mca.eps.filter.multiread.max-buffer-size=1048576  # 1 MB

# Excluded paths (don't cache body)
mca.eps.filter.multiread.excluded-paths[0]=/file/upload
```

#### OAuthValidatorFilter

```properties
# Enable OAuth validation
mca.security.oauth.enabled=true

# Token configuration
mca.security.oauth.jwt.issuer=https://auth.example.com
mca.security.oauth.jwt.audience=api.example.com
mca.security.oauth.token.validate-exp=true
mca.security.oauth.token.clock-skew-seconds=60

# Excluded paths (public endpoints)
mca.security.oauth.excluded-paths[0]=/api/public/**
mca.security.oauth.excluded-paths[1]=/health
```

#### DdosFilter

```properties
# Enable DDoS prevention
mca.security.ddos.enabled=true

# Rate limits
mca.security.ddos.requests-per-minute=1000
mca.security.ddos.requests-per-hour=50000

# Block duration
mca.security.ddos.block-duration-seconds=60

# Strategy
mca.security.ddos.strategy=channel-based

# Per-channel limits
mca.security.ddos.limits.MOBILE=5000
mca.security.ddos.limits.WEB=3000

# Excluded paths (bypass rate limiting)
mca.security.ddos.excluded-paths[0]=/health
```

#### ValidationFilter

```properties
# Enable validation
mca.validation.enabled=true

# Validation strategy
mca.validation.strategy=openapi

# Fail fast or collect errors
mca.validation.fail-fast=false

# Excluded paths (skip validation)
mca.validation.excluded-paths[0]=/health
mca.validation.excluded-paths[1]=/metrics
```

---

## URL Pattern Exclusions

### Global Filter Exclusions

```properties
# Paths to exclude from ALL filters
mca.eps.filter.excluded-paths[0]=/actuator/**
mca.eps.filter.excluded-paths[1]=/health
mca.eps.filter.excluded-paths[2]=/metrics
mca.eps.filter.excluded-paths[3]=/swagger-ui.html
mca.eps.filter.excluded-paths[4]=/v3/api-docs/**
```

### Per-Filter Exclusions

```properties
# OAuth validation exemptions
mca.security.oauth.excluded-paths[0]=/api/public/**
mca.security.oauth.excluded-paths[1]=/api/login

# DDoS prevention exemptions
mca.security.ddos.excluded-paths[0]=/health
mca.security.ddos.excluded-paths[1]=/metrics

# Validation exemptions
mca.validation.excluded-paths[0]=/file/upload
mca.validation.excluded-paths[1]=/webhook/github
```

### Pattern Matching

```properties
# Exact match
mca.eps.filter.excluded-paths[0]=/health

# Wildcard (single level)
mca.eps.filter.excluded-paths[0]=/actuator/*

# Wildcard (multiple levels)
mca.eps.filter.excluded-paths[0]=/actuator/**

# Multiple patterns
mca.eps.filter.excluded-paths[0]=/actuator/**
mca.eps.filter.excluded-paths[1]=/health
mca.eps.filter.excluded-paths[2]=/metrics
```

---

## Filter Chain Configuration: Practical Examples

### Development Configuration

```properties
# application-dev.properties

# Minimal security - ease of development
mca.eps.filter.correlation-id.enabled=true
mca.eps.filter.exception.enabled=true
mca.eps.filter.disable-session.enabled=true
mca.eps.filter.multiread.enabled=true

# Security OFF for local development
mca.security.oauth.enabled=false
mca.security.ddos.enabled=false
mca.validation.enabled=true

# Detailed error information for debugging
mca.eps.filter.exception.detailed-error-messages=true
mca.eps.filter.exception.stack-trace-enabled=true

# No masking for easier debugging
mca.masking.enabled=false

# Verbose logging
logging.level.com.barclays.global.mca=DEBUG
```

### Testing Configuration

```properties
# application-test.properties

# Fast filter chain - minimal overhead
mca.eps.filter.correlation-id.enabled=true
mca.eps.filter.exception.enabled=true
mca.eps.filter.disable-session.enabled=true
mca.eps.filter.multiread.enabled=true

# Optional filters off for speed
mca.security.oauth.enabled=false
mca.security.ddos.enabled=false
mca.validation.enabled=false

# Test the masking logic
mca.masking.enabled=true

# Quiet logging
logging.level.com.barclays.global.mca=WARN
```

### Production Configuration

```properties
# application-prod.properties

# All core filters enabled
mca.eps.filter.correlation-id.enabled=true
mca.eps.filter.exception.enabled=true
mca.eps.filter.disable-session.enabled=true
mca.eps.filter.multiread.enabled=true

# Security fully enabled
mca.security.oauth.enabled=true
mca.security.oauth.jwt.issuer=https://prod-auth.example.com
mca.security.oauth.jwt.audience=api.example.com

mca.security.ddos.enabled=true
mca.security.ddos.requests-per-minute=5000

# Validation enabled
mca.validation.enabled=true
mca.validation.strategy=openapi

# Masking enabled
mca.masking.enabled=true
mca.masking.patterns.credit-card=^([0-9]{4}).*([0-9]{4})$

# Production logging
mca.eps.filter.exception.stack-trace-enabled=false
mca.eps.filter.exception.detailed-error-messages=false
logging.level.com.barclays.global.mca=INFO
logging.config=classpath:log4j2-prod.xml

# Excluded paths
mca.eps.filter.excluded-paths[0]=/actuator/**
mca.eps.filter.excluded-paths[1]=/health
mca.security.oauth.excluded-paths[0]=/api/public/**
```

---

## Advanced: Custom Filter Registration

### Adding Custom Filters to Chain

```java
@Configuration
public class CustomFilterConfig {

    @Bean
    public FilterRegistrationBean<CustomAuthFilter>
        customAuthFilterRegistration() {

        CustomAuthFilter filter = new CustomAuthFilter();

        FilterRegistrationBean<CustomAuthFilter> bean =
            new FilterRegistrationBean<>(filter);

        bean.setOrder(11);  // After core filters
        bean.addUrlPatterns("/api/*");
        bean.setFilterName("CustomAuthFilter");

        return bean;
    }

    @Bean
    public FilterRegistrationBean<AuditFilter>
        auditFilterRegistration() {

        FilterRegistrationBean<AuditFilter> bean =
            new FilterRegistrationBean<>(new AuditFilter());

        bean.setOrder(12);
        bean.addUrlPatterns("/api/**");
        bean.setFilterName("AuditFilter");

        return bean;
    }
}
```

### Custom Filter Implementation

```java
public class CustomAuthFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {

        // Custom authentication logic
        String customHeader = request.getHeader("X-Custom-Auth");

        if (customHeader == null) {
            // Public endpoint
            filterChain.doFilter(request, response);
            return;
        }

        try {
            // Validate custom auth
            validateCustomAuth(customHeader);
            filterChain.doFilter(request, response);

        } catch (AuthException ex) {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.getWriter().write("{\"error\": \"Auth failed\"}");
        }
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        // Skip filter for public paths
        String path = request.getRequestURI();
        return path.startsWith("/api/public/")
            || path.startsWith("/health");
    }

    private void validateCustomAuth(String header) throws AuthException {
        // Custom validation logic
    }
}
```

---

## Conditional Filter Registration

### Enable Filters Based on Properties

```java
@Bean
@ConditionalOnProperty(name = "mca.security.oauth.enabled", havingValue = "true")
public FilterRegistrationBean<OAuthValidatorFilter>
    oauthFilterRegistration() {

    // Only registered if property is true
    FilterRegistrationBean<OAuthValidatorFilter> bean =
        new FilterRegistrationBean<>(new OAuthValidatorFilter());

    bean.setOrder(4);
    bean.addUrlPatterns("/api/*");

    return bean;
}

@Bean
@ConditionalOnProperty(name = "mca.validation.enabled", havingValue = "true")
public FilterRegistrationBean<ValidationFilter>
    validationFilterRegistration() {

    // Only registered if property is true
    FilterRegistrationBean<ValidationFilter> bean =
        new FilterRegistrationBean<>(new ValidationFilter());

    bean.setOrder(300);
    bean.addUrlPatterns("/api/*");

    return bean;
}
```

---

## Filter Chain Debugging

### Enable Debug Output

```properties
# Enable Spring security debug logging
logging.level.org.springframework.security=DEBUG

# Enable filter chain debug
logging.level.org.springframework.web.filter=DEBUG

# Enable MCA filter debug
logging.level.com.barclays.global.mca.libs.filters=DEBUG
```

### Verify Filter Registration

```bash
# Run with --debug to see which filters are registered
java -jar app.jar --debug | grep -i "filter"

# Look for output like:
# Registering filter: 'CorrelationIdFilter' with url-patterns=['/*']
# Registering filter: 'ExceptionFilter' with url-patterns=['/*']
# Registering filter: 'DisableSessionFilter' with url-patterns=['/*']
# ...
```

### Test Filter Execution

```java
@SpringBootTest
public class FilterChainTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    public void verifyCorrelationIdFilterIsExecuted() throws Exception {
        mockMvc.perform(get("/api/test"))
            .andExpect(header().exists("Correlation-ID"));
    }

    @Test
    public void verifyExceptionFilterHandlesExceptions() throws Exception {
        mockMvc.perform(post("/api/error"))
            .andExpect(status().is5xxServerError());
    }

    @Test
    public void verifyOAuthFilterIsExecuted() throws Exception {
        mockMvc.perform(get("/api/protected"))
            .andExpect(status().isUnauthorized());  // No token provided
    }
}
```

---

## Performance Tuning

### Filter Chain Performance

```properties
# Reduce buffer size if memory is limited
mca.eps.filter.multiread.max-buffer-size=524288  # 512 KB instead of 1 MB

# Exclude paths from expensive filters
mca.eps.filter.multiread.excluded-paths[0]=/file/upload
mca.validation.excluded-paths[0]=/webhook/**

# Async logging for better throughput
mca.logging.async.enabled=true
mca.logging.async.queue-size=10000
```

### Monitoring Filter Performance

```properties
# Enable performance logging
mca.logging.performance.enabled=true

# Log filters taking > 100ms
mca.logging.performance.threshold-ms=100

# Exclude expensive but acceptable operations
mca.logging.performance.excluded-packages[0]=org.mongodb
mca.logging.performance.excluded-packages[1]=org.postgresql
```

---

## Troubleshooting Filter Chain Issues

### Issue: Filter Not Executing

```properties
# Verify filter is enabled
mca.security.oauth.enabled=true

# Check URL pattern matches
mca.security.oauth.excluded-paths=...  # Make sure not excluded

# Verify order value
# If order is negative, filter runs before core filters
# If order is not set, defaults to Integer.MAX_VALUE (last)
```

### Issue: Order Conflicts

```java
// All filters must have unique order values
@Bean
public FilterRegistrationBean<FilterA> filterA() {
    bean.setOrder(10);  // ✓ Unique
    return bean;
}

@Bean
public FilterRegistrationBean<FilterB> filterB() {
    bean.setOrder(11);  // ✓ Unique (not 10!)
    return bean;
}
```

### Issue: Response Already Committed

```java
// Don't write response in early filters if later filters will write
@Override
protected void doFilterInternal(...) {
    // ✗ BAD: Writing response here
    response.getWriter().write("something");

    filterChain.doFilter(request, response);  // Now response is committed
}

// ✓ GOOD: Let later filters or handler write response
@Override
protected void doFilterInternal(...) {
    // Do processing
    filterChain.doFilter(request, response);

    // Can check if committed before writing
    if (!response.isCommitted()) {
        response.getWriter().write("something");
    }
}
```

---

## Next Steps

1. **Copy configuration template** — Use application-prod.properties as base
2. **Customize exclusions** — Add paths specific to your API
3. **Enable security filters** — Turn on OAuth, DDoS as needed
4. **Test filter order** — Run with --debug and verify ordering
5. **Monitor performance** — Enable perf logging and tune

---

## Quick Reference: Filter Configuration Checklist

```
☐ Core filters always enabled
☐ Optional filters configured per environment
☐ URL patterns defined for OAuth/DDoS
☐ Excluded paths configured
☐ Error handling configured
☐ Masking enabled for production
☐ Logging configured
☐ Performance monitoring enabled
☐ Tested with MockMvc
☐ Verified with --debug output
```

**Filter Chain Configuration provides complete control over MCA2 request processing.**
