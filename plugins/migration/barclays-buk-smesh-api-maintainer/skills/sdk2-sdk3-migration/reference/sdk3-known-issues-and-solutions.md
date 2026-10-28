# SDK3 Known Issues and Migration Solutions

> **Scope**: This guide documents known issues encountered during SDK2→SDK3 migrations and their recommended solutions for future API migrations.

---

## Table of Contents

- [SDK3 Specific Issues](#sdk3-specific-issues)
- [EBCP Pipeline Issues](#ebcp-pipeline-issues)
- [Spring Boot 3 Issues](#spring-boot-3-issues)

---

## SDK3 Specific Issues

### 1. RestApiClient - Missing Parameterized Return Type Methods

**Issue**: SDK3's `RestApiClient` does not provide parameterized return type methods that were available in SDK2. This impacts APIs consuming downstream services that return collections (e.g., `List<T>`).

**Problem**: Absence of equivalent parameterized methods prevents proper generic type handling during deserialization. Automatic JSON-to-object conversion fails for list-based responses, requiring custom code.

**SDK2 Example**:
```java
public interface RestClient {
    <T> ResponseEntity<T> call(URI uri, HttpMethod method, HttpEntity<?> entity, Class<T> clazz);
    <T> ResponseEntity<T> call(URI uri, HttpMethod method, HttpEntity<?> entity, ParameterizedTypeReference<T> ref);
    Response callForResponse(URI uri, HttpMethod method, HttpEntity<?> entity);
}
```

**SDK3 Current Implementation**:
```java
public interface RestApiClient {
    <T> ResponseEntity<T> call(HttpMethod method, URI uri, HttpHeaders headers, Class<T> clazz);
    <T> ResponseEntity<T> call(HttpMethod method, URI uri, Object body, HttpHeaders headers, Class<T> clazz);
    <T> ResponseEntity<T> call(RestClientHttpMethod method, URI uri, Map<String, List<String>> headers, Class<T> clazz);
}
```

**Solution**: When consuming collections, explicitly deserialize responses:
```java
// Instead of direct generic method call, use Jackson ObjectMapper
List<YourType> result = objectMapper.readValue(response, new TypeReference<List<YourType>>() {});
```

**Workaround**: If `ParameterizedTypeReference` support is critical, contact SDK3 team for enhancement request.

---

### 2. RequestResponseLoggingFilter - Request Body Consumption

**Issue**: `RequestResponseLoggingFilter` reads the original request input stream directly for non-JSON content types instead of creating a cached/wrapped copy. The request body is consumed by the filter and no longer available to the controller.

**Symptoms**:
- Request payload becomes `null` in controllers
- Only occurs with `Content-Type: application/x-www-form-urlencoded`
- Issue does NOT occur with `Content-Type: application/json` (due to different filter logic path)
- Issue does NOT occur when logging level is DEBUG (different code execution path)

**Root Cause**: Filter reading request stream without wrapping it in a `ContentCachingRequestWrapper`.

**Solution**: Ensure incoming requests are wrapped in `ContentCachingRequestWrapper` before reaching the filter:

```java
@Component
public class RequestCachingFilter implements Filter {
    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        if (request instanceof HttpServletRequest) {
            HttpServletRequest httpRequest = (HttpServletRequest) request;
            ContentCachingRequestWrapper wrappedRequest = new ContentCachingRequestWrapper(httpRequest);
            chain.doFilter(wrappedRequest, response);
        } else {
            chain.doFilter(request, response);
        }
    }
}
```

**Mitigation**: Place request caching filter BEFORE `RequestResponseLoggingFilter` in filter chain order.

---

### 3. ExternalApiLoggingContextFilter - Removed from SDK3

**Issue**: `ExternalApiLoggingContextFilter`, which extracted `x-fapi-interaction-id` from incoming requests and populated it into MDC (Mapped Diagnostic Context), has been removed in SDK3.

**Impact**: `x-fapi-interaction-id` is no longer propagated to logging context. Interaction IDs are not printed in application logs, impacting request traceability.

**SDK2 Implementation** (for reference):
```java
public class ExternalApiLoggingContextFilter extends LoggingContextFilter {
    protected Map<String, String> getLoggingContextProperties(HttpServletRequest request) {
        Map<String, String> props = new HashMap<>();
        props.put("x-fapi-interaction-id", request.getHeader("x-fapi-interaction-id"));
        return props;
    }
}
```

**Solution**: Implement custom filter to replace the removed functionality:

```java
@Component
public class ExternalApiInteractionIdFilter implements Filter {
    private static final String INTERACTION_ID_HEADER = "x-fapi-interaction-id";
    private static final Logger logger = LogFactory.getLogger(ExternalApiInteractionIdFilter.class);

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        if (request instanceof HttpServletRequest) {
            HttpServletRequest httpRequest = (HttpServletRequest) request;
            String interactionId = httpRequest.getHeader(INTERACTION_ID_HEADER);
            
            if (interactionId != null && !interactionId.isEmpty()) {
                logger.debug("Adding {} to MDC with value: {}", INTERACTION_ID_HEADER, interactionId);
                MDC.put(INTERACTION_ID_HEADER, interactionId);
            }
            
            try {
                chain.doFilter(request, response);
            } finally {
                MDC.remove(INTERACTION_ID_HEADER);
            }
        } else {
            chain.doFilter(request, response);
        }
    }
}
```

**Filter Ordering**: Place this filter early in chain, after security filters but before application filters.

---

### 4. SSLContext - JVM SSL System Properties Not Honored

**Issue**: SDK3's `SSLContext` implementation does not honor standard JVM SSL system properties:
- `javax.net.ssl.keyStore`
- `javax.net.ssl.keyStorePassword`
- `javax.net.ssl.trustStore`
- `javax.net.ssl.trustStorePassword`

**Impact**: Client certificates configured via system properties are not loaded. APIs using mutual TLS (mTLS) fail to present client certificate during TLS handshake, causing authentication failures with downstream systems.

**SDK3 Default (Problem)**:
```java
SSLContext sslContext = SSLContexts.createDefault();
// Does NOT read javax.net.ssl.* system properties
```

**Solution**: Use `SSLContexts.createSystemDefault()` to honor JVM system properties:

```java
public class HttpPoolingClientBuilder {
    public HttpComponentsClientHttpRequestFactory build(HttpConnectionPoolingConfig config) {
        // Use createSystemDefault() instead of createDefault()
        SSLContext sslContext = SSLContexts.createSystemDefault();
        
        SSLConnectionSocketFactory sslSocketFactory = SSLConnectionSocketFactoryBuilder.create()
            .setSslContext(sslContext)
            .setHostnameVerifier(new DefaultHostnameVerifier())  // Replace NoopHostnameVerifier
            .build();
        
        return new HttpComponentsClientHttpRequestFactory(
            HttpClients.custom()
                .setConnectionManager(
                    PoolingHttpClientConnectionManagerBuilder.create()
                        .setSSLSocketFactory(sslSocketFactory)
                        .build())
                .build());
    }
}
```

**System Property Configuration** (at JVM startup):
```bash
-Djavax.net.ssl.keyStore=/path/to/keystore.jks
-Djavax.net.ssl.keyStorePassword=keystore-password
-Djavax.net.ssl.trustStore=/path/to/truststore.jks
-Djavax.net.ssl.trustStorePassword=truststore-password
```

---

### 5. NoopHostnameVerifier - Security Vulnerability

**Issue**: SDK3's default request factory uses `NoopHostnameVerifier`, which disables hostname validation during SSL/TLS certificate verification. This is a **CSO Security Vulnerability**.

**Risk**: Disables key security control that validates certificate hostname matches target endpoint. Can be exploited for man-in-the-middle (MITM) attacks or unauthorized endpoint impersonation.

**Problem Code**:
```java
SSLConnectionSocketFactory sslSocketFactory = SSLConnectionSocketFactoryBuilder.create()
    .setHostnameVerifier(NoopHostnameVerifier.INSTANCE)  // ❌ INSECURE
    .build();
```

**Solution**: Replace with standard hostname verifier:

```java
// Option 1: Use DefaultHostnameVerifier (recommended)
SSLConnectionSocketFactory sslSocketFactory = SSLConnectionSocketFactoryBuilder.create()
    .setSslContext(sslContext)
    .setHostnameVerifier(new DefaultHostnameVerifier())  // ✅ Validates hostname
    .build();

// Option 2: Use HttpClientBuilder convenience method
HttpClient httpClient = HttpClients.custom()
    .setConnectionManager(connectionManager)
    .build();  // Default hostname verifier applied
```

**Verification**: Ensure in security scans and code review that `NoopHostnameVerifier` is NOT used in production code.

---

### 6. Publishing Multiple Jars - GitLab Pipeline Failure

**Issue**: SDK3 publish task attempts to publish multiple jars, causing failures with GitLab pipeline.

**Problem**: Gradle configuration or Maven POM publishes all generated artifacts instead of primary jar only.

**Solution**: Configure publish task to single artifact:

```gradle
// build.gradle
java {
    withSourcesJar()
    withJavadocJar()
}

publishing {
    publications {
        mavenJava(MavenPublication) {
            from components.java
            // Publish only primary JAR, not sources/javadoc
            artifact sourcesJar
            // Remove or conditionally include javadocJar if not needed
        }
    }
}
```

**Alternative**: Check SDK3 BOM publish configuration for guidance on recommended artifact strategy.

---

## EBCP Pipeline Issues

### 1. log4j2 Folder Issue - ${env:HOSTNAME} Not Resolved

**Issue**: Deployment pipeline injects default `log4j2.xml` with placeholder `${env:HOSTNAME}` for log folder creation. This placeholder is NOT resolved at runtime to actual pod hostname.

**Symptom**: Physical folder created with literal name `${env:HOSTNAME}` instead of actual pod name.

**Problem**: Log4j2 configuration references environment variable that is not available during initialization.

**Solution**: Update `log4j2.xml` configuration to use System properties or Environment-aware path:

```xml
<!-- Option 1: Use System property with fallback -->
<Properties>
    <Property name="log.dir">${sys:LOG_DIR:-/var/log/application}</Property>
</Properties>

<!-- Option 2: Use computed property from Spring -->
<Properties>
    <Property name="pod.hostname">${env:HOSTNAME:-unknown}</Property>
    <Property name="log.dir">/var/log/application/${pod.hostname}</Property>
</Properties>

<!-- Option 3: Inject at runtime via environment -->
<RollingFile name="File" fileName="${log.dir}/app-${pod.hostname}.log">
    ...
</RollingFile>
```

**Runtime Setup**: Ensure environment variables are exported before application startup:
```bash
export HOSTNAME=$(hostname)
java -DLOG_DIR=/var/log/application ...
```

---

### 2. GC Parameter - CMS Garbage Collector Not Supported in JDK 21

**Issue**: Deployment pipeline applies JVM garbage collection (GC) parameters designed for JDK 8, including CMS (Concurrent Mark-Sweep) collector parameters. These are no longer supported in JDK 21.

**Problem Parameters** (JDK 8 legacy):
```
-XX:+UseConcMarkSweepGC
-XX:CMSInitiatingOccupancyFraction=75
-XX:+UseCMSInitiatingOccupancyOnly
```

**Impact**: JVM startup failures or silently ignored configurations, unpredictable GC behavior in production.

**Solution**: Update GC configuration for JDK 21 using G1 Garbage Collector:

**Recommended JDK 21 GC Parameters**:
```bash
# G1GC configuration (default and recommended for JDK 21)
-XX:+UseG1GC
-XX:MaxGCPauseMillis=200
-XX:+ParallelRefProcEnabled

# Optional: For high-throughput scenarios
-XX:+UseG1GC
-XX:MaxGCPauseMillis=200
-XX:InitiatingHeapOccupancyPercent=35

# Optional: For low-latency scenarios
-XX:+UseG1GC
-XX:MaxGCPauseMillis=50
-XX:InitiatingHeapOccupancyPercent=35
```

**Migration Path**:
1. Remove all CMS-specific parameters
2. Add G1GC parameters above
3. Test GC behavior with actual workload
4. Monitor GC logs for pause times and throughput

---

## Spring Boot 3 Issues

### 1. Max-http-header Property - Configuration Change

**Issue**: Property `server.max-http-header-size` was deprecated in Spring Boot 3 and replaced with separate properties for request and response headers.

**Spring Boot 2**:
```properties
server.max-http-header-size=16KB  # Applies to both request and response
```

**Spring Boot 3**:
```properties
# Request headers only
server.max-http-request-header-size=16KB

# Response headers (uses different mechanism, often through client library)
# No direct property; depends on HTTP client library (RestTemplate, HttpClient, etc.)
```

**Solution**: Update `application.properties` or `application.yml`:

```yaml
# application.yml
server:
  max-http-request-header-size: 16KB  # For incoming requests
```

**Note**: Response header size limits depend on the HTTP client library. For Apache HttpClient, configure separately.

---

### 2. @Validated Annotation - Behavior Changes

**Issue**: Usage and behavior of `@Validated` changed due to transition from `javax.validation` to `jakarta.validation` and Spring Framework 6 changes for method-level validation.

**Changes in Spring Framework 6**:
- Controller validation increasingly supported through native Spring MVC mechanisms
- Method-level validation may follow different execution path
- Validation failures result in different exception types (e.g., `HandlerMethodValidationException` instead of `ConstraintViolationException`)

**Migration Actions**:
1. Update import statements: `javax.validation` → `jakarta.validation`
2. Review exception handlers for changed exception types
3. Test all validation flows with actual validation failures
4. Regression-test JUnit test cases that expect validation behavior

**Example Migration**:
```java
// OLD (Spring Boot 2)
import javax.validation.Valid;
import javax.validation.ConstraintViolationException;

// NEW (Spring Boot 3)
import jakarta.validation.Valid;
import org.springframework.web.method.annotation.HandlerMethodValidationException;

// Exception handler update
@ExceptionHandler(HandlerMethodValidationException.class)
public ResponseEntity<?> handleValidationException(HandlerMethodValidationException ex) {
    // Handle new exception type
    return ResponseEntity.badRequest().body(ex.getMessage());
}
```

---

### 3. EHCache - Ehcache 2 to Ehcache 3 Migration

**Issue**: Spring Boot 2 used **Ehcache 2** with deprecated classes (`EhCacheCacheManager`, `EhCacheManagerFactoryBean`). Spring Framework 6 / Spring Boot 3 no longer supports Ehcache 2.

**Requirement**: Migrate to **Ehcache 3 using JCache (JSR-107) integration**.

**Migration Steps**:

1. **Update Dependencies** (Maven):
```xml
<!-- Remove old Ehcache 2 -->
<!-- <dependency>
    <groupId>net.sf.ehcache</groupId>
    <artifactId>ehcache</artifactId>
</dependency> -->

<!-- Add Spring Boot Cache starter -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-cache</artifactId>
</dependency>

<!-- Add Ehcache 3 with JCache support -->
<dependency>
    <groupId>org.ehcache</groupId>
    <artifactId>ehcache</artifactId>
    <version>3.10.x</version>
    <classifier>jakarta</classifier>
</dependency>

<!-- JCache API -->
<dependency>
    <groupId>javax.cache</groupId>
    <artifactId>cache-api</artifactId>
</dependency>
```

2. **Create Ehcache 3 Configuration** (`ehcache.xml`):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<config xmlns="http://www.ehcache.org/v3" 
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://www.ehcache.org/v3 http://www.ehcache.org/schema/ehcache-core.xsd">

    <cache alias="users">
        <key-type>java.lang.String</key-type>
        <value-type>com.example.User</value-type>
        <expiry>
            <ttl unit="minutes">10</ttl>
        </expiry>
        <resources>
            <heap unit="entries">100</heap>
        </resources>
    </cache>
</config>
```

3. **Update Spring Configuration**:
```java
@Configuration
@EnableCaching
public class CacheConfig {
    // No longer need EhCacheCacheManager bean
    // Spring Boot auto-configures JCache manager from ehcache.xml
}
```

4. **Update application.yml**:
```yaml
spring:
  cache:
    type: jcache  # Use JCache (JSR-107)
    jcache:
      config: classpath:ehcache.xml
```

**Important**: Ehcache 2 XML schema is NOT compatible with Ehcache 3. If you have Ehcache 2 XML configuration, it must be completely rewritten to Ehcache 3 schema.

---

### 4. Spring MVC Resource Handling - 404 Error Behavior Change

**Issue**: **MVC 404 error handling behavior changed** between Spring Boot 2 and Spring Boot 3.

**Spring Boot 2 Behavior**: Unknown routes implicitly forwarded to `index.html` (SPA fallback)
```
Request: /unknown-route → Serves /index.html (200 OK)
```

**Spring Boot 3 Behavior**: Unknown routes return `NoResourceFoundException` and HTTP 404 JSON response:
```json
Request: /unknown-route → HTTP 404
{
    "timestamp": "2024-01-01T00:00:00...",
    "status": 404,
    "error": "Not Found",
    "message": "No static resource ...",
    "path": "/unknown-route"
}
```

**Solution**: Implement custom error handling for SPA fallback:

**Option 1: Custom Error Controller**:
```java
@Controller
public class ErrorViewController {
    @RequestMapping("/error")
    public String handleError(HttpServletResponse response) {
        if (response.getStatus() == HttpServletResponse.SC_NOT_FOUND) {
            // Forward unknown routes to SPA entry point
            return "forward:/index.html";
        }
        return "error/error";
    }
}
```

**Option 2: Web Configuration**:
```java
@Configuration
public class WebMvcConfig implements WebMvcConfigurer {
    @Override
    public void configureDefaultServletHandling(DefaultServletHandlerConfigurer configurer) {
        configurer.enable();
    }
    
    @Override
    public void addViewControllers(ViewControllerRegistry registry) {
        // Route all unknown paths to SPA entry
        registry.addViewController("/{spring:[a-zA-Z0-9_-]+}")
                .setViewName("forward:/");
        registry.addViewController("/{spring:[a-zA-Z0-9_-]+}/**{spring:.*}")
                .setViewName("forward:/");
    }
}
```

**Option 3: Exception Handler**:
```java
@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(NoResourceFoundException.class)
    public ResponseEntity<?> handleNoResourceFound(NoResourceFoundException ex) {
        // For SPA apps, redirect to index.html
        return ResponseEntity.status(HttpStatus.FOUND)
            .location(URI.create("/index.html"))
            .build();
    }
}
```

---

## Java 8 → Java 21 / Spring Boot 2 → 3 Behaviour Changes

---

### 5. Jackson Null Serialization — Fields Excluded by Default

**Issue**: Spring Boot 3 / Jackson 2.15+ excludes `null` fields from JSON responses by default. Spring Boot 2 included them.

**Impact**: Karate integration tests using `#null` matchers will fail; `#notpresent` is the correct matcher in SDK3.

**Root cause**: Spring Boot 3 auto-configuration enables `NON_NULL` serialization inclusion by default via its `JacksonProperties`.

**Fix — Option 1: Update Karate tests (preferred — reflects actual API contract)**
```
# OLD (Spring Boot 2)
* match response.prodConfigRepo == '#null'

# NEW (Spring Boot 3) — field absent, not null
* match response.prodConfigRepo == '#notpresent'
```

**Fix — Option 2: Restore null-inclusion globally**
```java
@Configuration
public class JacksonConfig {
    @Bean
    public ObjectMapper objectMapper() {
        ObjectMapper mapper = new ObjectMapper();
        mapper.setSerializationInclusion(JsonInclude.Include.ALWAYS);
        return mapper;
    }
}
```

**Fix — Option 3: Per-DTO annotation**
```java
@JsonInclude(JsonInclude.Include.ALWAYS)
public class MyResponseDto { ... }
```

---

### 6. Spring Data JPA `deleteById()` — Silent Success on Missing Entity

**Issue**: `deleteById()` behaviour changed between Spring Data JPA 2.x (SB2) and 3.x (SB3).

| | Spring Boot 2 (JPA 2.x) | Spring Boot 3 (JPA 3.x) |
|---|---|---|
| Entity exists | Deletes | Deletes |
| Entity missing | Throws `EmptyResultDataAccessException` | **Silently succeeds** |

**Impact**: Tests that assert `EmptyResultDataAccessException` is thrown will fail silently.

**Solution — if exception on missing entity is required**:
```java
// Pattern 1: find + delete
Optional<Entity> entity = repository.findById(id);
if (entity.isEmpty()) {
    throw new EntityNotFoundException("Entity not found: " + id);
}
repository.delete(entity.get());

// Pattern 2: custom JPQL with count check
@Modifying
@Query("DELETE FROM Entity e WHERE e.id = :id")
int deleteByIdAndReturnCount(@Param("id") Long id);
// Returns 0 if not found → caller can throw
```

**Test update**:
```java
// OLD
assertThrows(EmptyResultDataAccessException.class, () -> repo.deleteById(nonExistentId));

// NEW — either expect no exception, or use find + delete pattern above
assertDoesNotThrow(() -> repo.deleteById(nonExistentId));
```

---

### 7. WireMock 2.x → 3.x — Stub Ordering and Priority

**Issue**: WireMock 3.x changed how overlapping stubs are resolved.

| Behaviour | WireMock 2.x | WireMock 3.x |
|---|---|---|
| Overlapping stubs | First-added wins | **Most-recently-added wins** |
| Priority | Optional, rarely needed | Use `priority` field to control precedence |

**Impact**: Test suites with multiple stubs for the same URL may return unexpected responses.

**Solution**: Add explicit `priority` to stubs where ordering matters (lower number = higher priority):
```json
{
  "priority": 1,
  "request": {
    "urlPattern": "/api/specific/path",
    "method": "GET"
  },
  "response": {
    "status": 200,
    "body": "{ \"result\": \"specific\" }"
  }
}
```

**Note**: Also verify URL pattern matching — WireMock 3.x applies stricter pattern matching rules than 2.x.

---

### 8. WireMock Stub Duplicate UUIDs

**Issue**: WireMock stubs with duplicate UUIDs cause failures (behaviour differs from WireMock 2.x where duplicates were silently ignored).

**Solution**: Ensure all stub file UUIDs are unique:
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "request": { "url": "/api/endpoint" },
  "response": { "status": 200 }
}
```

**Detection**:
```bash
# Find duplicate IDs across all stub files
grep -rh '"id":' src/test/resources/wiremock/ | sort | uniq -d
```

**Best Practice**: Use a UUID generator for each stub; never copy-paste stub files without changing the `id` field.

---

## Migration Checklist

When migrating APIs to SDK3, verify these items are addressed:

- [ ] RestApiClient method calls handle List<T> deserialization correctly
- [ ] Request body is not consumed by logging filters (ContentCachingRequestWrapper in place)
- [ ] Custom filter added to propagate x-fapi-interaction-id to MDC
- [ ] SSLContext uses createSystemDefault() for mTLS support
- [ ] NoopHostnameVerifier removed, DefaultHostnameVerifier used instead
- [ ] Publish configuration limited to single primary JAR
- [ ] log4j2.xml resolves ${env:HOSTNAME} correctly
- [ ] GC parameters updated from CMS to G1GC for JDK 21
- [ ] HTTP header size property updated to server.max-http-request-header-size
- [ ] @Validated imports changed to jakarta.validation
- [ ] Exception handlers updated for HandlerMethodValidationException
- [ ] Ehcache migrated from 2 to 3 with JCache support
- [ ] SPA routing configured for Spring Boot 3 404 handling
- [ ] Jackson null serialization — Karate tests updated `#null` → `#notpresent` (or ALWAYS inclusion configured)
- [ ] Spring Data JPA deleteById() — tests updated; exception-on-missing pattern replaced if required
- [ ] WireMock stubs have explicit priority if URL patterns overlap
- [ ] WireMock stub UUIDs are all unique
- [ ] Apache HttpClient 4.x imports updated to httpclient5 (org.apache.hc.core5.*) — see sdk2_to_sdk3_package_mapping.md

---

## References

- [SDK3 Documentation](https://internal.barclays.com/sdk3-docs)
- [Spring Boot 3 Migration Guide](https://spring.io/blog/2023/09/30/introducing-spring-boot-3-2-m1)
- [Ehcache 3 User Guide](https://www.ehcache.org/documentation/3.10/)
- [JCache (JSR-107) Specification](https://github.com/jsr107/jsr107spec)
