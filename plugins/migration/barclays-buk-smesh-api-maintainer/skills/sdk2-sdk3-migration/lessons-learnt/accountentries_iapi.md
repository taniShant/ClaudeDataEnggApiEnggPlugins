# Lessons Learned - SDK2 to SDK3 Migration

**Project:** accountentries-iapi
**Migration:** SDK2 (api-bom 2.15.1.1) → SDK3 (1.11.015)
**Date:** December 2025

---

## Critical Lessons

### 1. ⚠️ NEVER Include Eclipse or IntelliJ IDEA Gradle Plugins

**Issue:** Eclipse and IntelliJ IDEA Gradle plugins cause conflicts with SDK3's bap-bld-lib-plugin

**Problem:**
```gradle
// ❌ DO NOT ADD THESE TO build.gradle
apply plugin: 'eclipse'
apply plugin: 'eclipse-wtp'
apply plugin: 'idea'
```

**Why This Matters:**
- SDK3's `bap-bld-lib-plugin` automatically applies Spring Boot plugin and other necessary plugins
- Eclipse/IDEA plugins can interfere with SDK3's Gradle configuration
- Modern IDEs (IntelliJ IDEA, Eclipse with Buildship, VS Code) automatically detect Gradle projects without explicit plugins
- These plugins are legacy and not needed with Gradle 8.13+

**Correct Approach:**
```gradle
// ✅ ONLY use SDK3 plugin
apply plugin: 'com.barclays.api.bap-bld-lib-plugin'

// IDEs will automatically detect Gradle configuration
// No explicit IDE plugins needed
```

**Detection:**
If you see build errors like "plugin already applied" or "duplicate configuration", check for Eclipse/IDEA plugins and remove them.

**References:**
- Gradle 8.x no longer requires explicit IDE plugins
- SDK3 plugin provides all necessary build configuration

---

### 2. HTTP Status Must Come from ResponseEntity, Not RestResponse

**Critical Pattern Change:**

**SDK2 (WRONG in SDK3):**
```java
Response response = restClient.callForResponse(uri, method, entity);
if (response.getHttpStatus() == HttpStatus.OK) {  // ❌ getHttpStatus() returns null in SDK3
    // Process response
}
```

**SDK3 (CORRECT):**
```java
ResponseEntity<String> responseEntity = restApiClient.call(
    HttpMethod.GET, uri, headers, String.class
);
String responseBody = responseEntity.getBody();
Response response = objectMapper.readValue(responseBody, RestResponse.class);

if (responseEntity.getStatusCode().is2xxSuccessful()) {  // ✅ Use ResponseEntity
    // Process response
}
```

**Why This Matters:**
- `RestResponse.getHttpStatus()` returns null after JSON deserialization
- HTTP status is only available from `ResponseEntity.getStatusCode()`
- This causes NullPointerException if not handled correctly

**Common Error:**
```
Cannot invoke 'org.springframework.http.HttpStatus.name()'
because the return value of 'RestResponse.getHttpStatus()' is null
```

**Solution:**
Always check HTTP status from `ResponseEntity`, never from `RestResponse`

**Example Fix:**
```java
// Declare ResponseEntity at method scope
ResponseEntity<String> responseEntity = null;

try {
    // SDK3: RestApiClient.call() returns ResponseEntity<String>
    responseEntity = restApiClient.call(
        HttpMethod.GET,
        URI.create(url),
        headers,
        String.class
    );

    // Parse JSON response
    String responseBody = responseEntity.getBody();
    response = objectMapper.readValue(responseBody, RestResponse.class);

} catch (IOException | ResourceAccessException e) {
    logger.error("Exception occurred in API call");
    throw new ApiServerException(ErrorMessages.INTERNAL_SERVER_ERROR.withDetail(e.getMessage()), e);
}

// ✅ Check HTTP status from ResponseEntity
if (responseEntity.getStatusCode().is2xxSuccessful()) {
    // Process successful response
} else {
    // Log with ResponseEntity status
    logger.error("API call returned with http status=[{}]", responseEntity.getStatusCode());

    // Pass ResponseEntity status to validation
    ValidationUtils.validateResponse(response, responseEntity.getStatusCode(), errorMessage, throwError, meta);
}
```

---

### 3. ⚠️ Response vs RestResponse - Know the Difference (CANONICAL REFERENCE)

**This is the primary reference for Response vs RestResponse patterns. Other documents link here.**

---

#### Quick Summary

| Action | Use This Type |
|--------|---------------|
| **Building** a response | `RestResponse.assemble()` |
| **Return type** in method signatures | `Response` (interface) |
| **Setting** errors, meta, data | `RestResponse` (concrete) |
| **Reading** data only | `Response` (interface) |

---

#### Method Availability Matrix

| Method | `Response` (interface) | `RestResponse` (concrete) |
|--------|:----------------------:|:-------------------------:|
| `getData()` | ✅ | ✅ |
| `getData(Class<T>)` | ✅ | ✅ |
| `getData(TypeReference<T>)` | ❌ | ✅ |
| `setData()` | ❌ | ✅ |
| `getErrors()` | ❌ | ✅ |
| `setErrors()` | ❌ | ✅ |
| `getMeta()` | ❌ | ✅ |
| `setMeta()` | ❌ | ✅ |
| `getHttpStatus()` | ❌ | ✅ (but returns null after JSON deserialization!) |
| `assemble()` | ❌ | ✅ (static method) |
| `empty()` | ❌ | ✅ (static method) |

---

#### Package Locations

```java
// Response INTERFACE - use for return types and variable declarations
import com.barclays.api.bap.bld.lib.common.response.Response;

// RestResponse CONCRETE CLASS - use for building and modification
import com.barclays.api.bap.bld.lib.payload.response.RestResponse;

// Related imports often needed together
import com.barclays.api.bap.bld.lib.payload.response.Message;
import com.barclays.api.bap.bld.lib.payload.response.MetaData;
import com.barclays.api.bap.bld.lib.payload.response.ResponseHttpStatus;
import com.barclays.api.bap.bld.lib.payload.beans.Resource;
```

---

#### Rule of Thumb

- **Use `Response`** when you only need to read data or declare return types
- **Use `RestResponse`** when you need to build, modify, or access metadata/errors

---

#### Correct Usage Pattern

```java
// Building response - use RestResponse
public Response buildResponse(Resource resource) {
    return RestResponse.assemble().build(resource);  // ✅ RestResponse.assemble()
}

// Method signature - use Response interface
public Response getAccountDetails(...) {  // ✅ Response interface
    // Implementation
}
```

---

#### Common Compilation Errors

**Error 1: Using Response.assemble()**
```java
// ❌ WRONG - Response interface doesn't have assemble()
return Response.assemble().build(resource);

// Compilation error:
// cannot find symbol: method assemble()
//   symbol:   method assemble()
//   location: interface Response
```

**Error 2: Using response.setErrors() on Response type**
```java
Response response = RestResponse.empty(HttpStatus.NOT_FOUND);
response.setErrors(errors);  // ❌ WRONG - setErrors() not on Response interface

// Compilation error:
// cannot find symbol: method setErrors(List<Message>)
//   location: variable response of type Response
```

**Fix:** Declare variable as `RestResponse`:
```java
RestResponse response = RestResponse.empty(HttpStatus.NOT_FOUND);
response.setErrors(errors);  // ✅ Works
```

---

#### Why This Matters

- `Response` is the **interface** - defines the contract for reading data
- `RestResponse` is the **concrete implementation** - provides building and modification methods
- `assemble()` and `empty()` are **static factory methods** on `RestResponse` only
- `getHttpStatus()` exists on `RestResponse` but **returns null after JSON deserialization** (see Lesson 2)

---

#### Complete Service Example

```java
import com.barclays.api.bap.bld.lib.common.response.Response;
import com.barclays.api.bap.bld.lib.payload.response.RestResponse;
import com.barclays.api.bap.bld.lib.payload.response.Message;
import com.barclays.api.bap.bld.lib.payload.beans.Resource;
import org.springframework.http.HttpStatus;
import java.util.Arrays;
import java.util.List;

public class AccountService {

    // ✅ Return type is Response interface
    public Response buildSuccessResponse(List<Resource<Account>> accounts) {
        // ✅ Build with RestResponse.assemble()
        return RestResponse.assemble().build(accounts);
    }

    // ✅ Return type is Response interface, but use RestResponse for building
    public Response buildErrorResponse(Message errorMessage) {
        // ✅ Declare as RestResponse to access setErrors()
        RestResponse response = RestResponse.assemble().build(HttpStatus.BAD_REQUEST);
        response.setErrors(Arrays.asList(errorMessage));
        return response;  // ✅ Can return as Response interface
    }

    // ✅ Return type is Response interface
    public Response buildEmptyResponse() {
        return RestResponse.empty(HttpStatus.NO_CONTENT);
    }
}
```

---

#### Test Mocking Example

```java
@Test
public void testMockResponse() throws Exception {
    // ✅ Build mock response with RestResponse.assemble()
    Response mockResponse = RestResponse.assemble().build(mockData);

    // Convert to JSON for SDK3 mocking pattern
    String jsonString = objectMapper.writeValueAsString(mockResponse);
    ResponseEntity<String> responseEntity = ResponseEntity.ok(jsonString);

    BDDMockito.given(restClient.call(
        any(HttpMethod.class), any(URI.class), any(), any()
    )).willReturn(responseEntity);
}
```

---

#### Related Documentation

- **Test mocking patterns:** See `test_migration_specification.md` Section 8
- **Package mappings:** See `sdk2_to_sdk3_package_mapping.md` Section 3
- **HTTP status handling:** See Lesson 2 in this document (getHttpStatus() returns null)

---

### 4. ⚠️ Remove Jersey Dependencies from build.gradle

**Issue:** Jersey (JAX-RS) client dependencies are incompatible with SDK3 and cause conflicts

**Problem:**
```gradle
// ❌ DO NOT include these in build.gradle
dependencies {
    implementation 'com.sun.jersey:jersey-core'
    implementation 'com.sun.jersey:jersey-client'
}
```

**Why This Matters:**
- SDK3 uses Spring's RestApiClient (based on RestTemplate/WebClient), not Jersey JAX-RS clients
- Jersey dependencies can cause classpath conflicts with Spring Boot 3.x
- Jersey is a legacy JAX-RS implementation not used in SDK3 architecture
- Including Jersey dependencies will cause runtime conflicts with Spring's HTTP client infrastructure

**Common Errors When Jersey is Present:**
```
ClassNotFoundException: javax.ws.rs.client.Client
or
NoSuchMethodError in Jersey client initialization
or
Conflicting implementations of JAX-RS API
```

**Correct Approach:**
```gradle
dependencies {
    // ✅ SDK3 uses RestApiClient (included via bap-bld-lib-restapi)
    implementation 'com.barclays.api:bap-bld-lib-restapi'

    // ❌ DO NOT add Jersey dependencies
    // implementation 'com.sun.jersey:jersey-core'
    // implementation 'com.sun.jersey:jersey-client'
}
```

**Migration Path:**
If your SDK2 code used Jersey client:

**SDK2 (Jersey):**
```java
import com.sun.jersey.api.client.Client;
import com.sun.jersey.api.client.ClientResponse;
import com.sun.jersey.api.client.WebResource;

Client client = Client.create();
WebResource webResource = client.resource("http://example.com/api");
ClientResponse response = webResource.get(ClientResponse.class);
```

**SDK3 (RestApiClient):**
```java
import com.barclays.api.bap.bld.lib.restclient.RestApiClient;
import org.springframework.http.ResponseEntity;
import org.springframework.http.HttpMethod;

@Autowired
private RestApiClient restApiClient;

ResponseEntity<String> response = restApiClient.call(
    HttpMethod.GET,
    URI.create("http://example.com/api"),
    headers,
    String.class
);
```

**Detection:**
Search your build.gradle for:
```bash
grep -i "jersey" build.gradle
```

If found, remove all Jersey dependencies and migrate to RestApiClient pattern.

**References:**
- SDK3 standardizes on Spring's HTTP client infrastructure
- RestApiClient is the only supported HTTP client in SDK3
- Jersey/JAX-RS is not part of SDK3 ecosystem

---

### 5. RestApiClient call() Methods - Understanding the API

**Issue:** RestApiClient provides multiple method overloads - knowing which to use is critical

**RestApiClient Interface Overview:**

The `com.barclays.api.bap.bld.lib.restclient.RestApiClient` interface provides **two method groups**:
1. **`call()` methods** - Return `ResponseEntity<T>` ✅ **Recommended for SDK3**
2. **`makeRequest()` methods** - Return `Response` ❌ **Not recommended (legacy)**

---

#### call() Method Variants

**Variant 1: Basic GET/DELETE without request body**
```java
<T> ResponseEntity<T> call(
    HttpMethod method,           // Spring's HttpMethod (GET, POST, PUT, DELETE, PATCH)
    URI uri,                     // Target URI
    HttpHeaders headers,         // Request headers
    Class<T> responseType        // Response type (use String.class)
)
```

**Usage:**
```java
ResponseEntity<String> response = restApiClient.call(
    HttpMethod.GET,
    URI.create("http://api.example.com/accounts/123"),
    headers,
    String.class
);
```

**When to use:**
- GET requests
- DELETE requests without body
- Any request without request body

---

**Variant 2: POST/PUT/PATCH with request body**
```java
<T> ResponseEntity<T> call(
    HttpMethod method,           // Spring's HttpMethod
    URI uri,                     // Target URI
    Object requestBody,          // Request body (automatically serialized to JSON)
    HttpHeaders headers,         // Request headers
    Class<T> responseType        // Response type (use String.class)
)
```

**Usage:**
```java
AccountRequest request = new AccountRequest("12345");

ResponseEntity<String> response = restApiClient.call(
    HttpMethod.POST,
    URI.create("http://api.example.com/accounts"),
    request,                     // Request body
    headers,
    String.class
);
```

**When to use:**
- POST requests with body
- PUT requests with body
- PATCH requests with body

---

**Variant 3: With RestClientHttpMethod (custom enum)**
```java
<T> ResponseEntity<T> call(
    RestClientHttpMethod method,                    // Barclays custom HTTP method enum
    URI uri,
    Map<String, List<String>> headers,             // Headers as Map
    Class<T> responseType
)
```

**When to use:**
- When working with Map-based headers
- When using Barclays' custom RestClientHttpMethod enum
- **Less common** - prefer Spring's HttpMethod + HttpHeaders

---

**Variant 4: With RestClientHttpMethod and request body**
```java
<T> ResponseEntity<T> call(
    RestClientHttpMethod method,
    URI uri,
    Object requestBody,
    Map<String, List<String>> headers,
    Class<T> responseType
)
```

**When to use:**
- POST/PUT with custom RestClientHttpMethod and Map headers
- **Less common** - prefer Spring's HttpMethod + HttpHeaders

---

#### call() vs makeRequest() - Key Differences

| Feature | call() | makeRequest() |
|---------|--------|---------------|
| **Return Type** | `ResponseEntity<T>` | `Response` |
| **HTTP Status** | ✅ Available via `getStatusCode()` | ❌ Not available (returns null) |
| **Generic Type** | ✅ Generic `<T>` for any type | ❌ Fixed Response type |
| **Recommended** | ✅ Yes | ❌ No (legacy) |

**Why avoid makeRequest():**
- Returns `Response` which doesn't include HTTP status (causes NullPointerException)
- Abstracts away important HTTP details needed for debugging
- Less flexible than `ResponseEntity<T>`

---

#### Complete Usage Pattern

**Recommended Pattern:**
```java
@Autowired
private RestApiClient restApiClient;

@Autowired
private ObjectMapper objectMapper;

public List<Account> getAccounts(String accountId) {
    // 1. Prepare headers
    HttpHeaders headers = new HttpHeaders();
    headers.add("Authorization", context.getAuthorization());
    headers.add("X-Correlation-ID", context.getCorrelationId());

    ResponseEntity<String> responseEntity = null;
    RestResponse response = null;

    try {
        // 2. Call API - returns ResponseEntity<String>
        responseEntity = restApiClient.call(
            HttpMethod.GET,
            URI.create(apiUrl + "/accounts/" + accountId),
            headers,
            String.class              // Always use String.class
        );

        // 3. Parse JSON response manually
        String responseBody = responseEntity.getBody();
        response = objectMapper.readValue(responseBody, RestResponse.class);

    } catch (IOException | ResourceAccessException e) {
        logger.error("Exception occurred in API call");
        throw new ApiServerException(ErrorMessages.INTERNAL_SERVER_ERROR.withDetail(e.getMessage()), e);
    }

    // 4. Check HTTP status from ResponseEntity (NOT from Response!)
    if (responseEntity.getStatusCode().is2xxSuccessful()) {
        // 5. Extract data from Response
        List<Resource<Account>> accounts = response.getData(
            new TypeReference<List<Resource<Account>>>() {}
        );
        return processAccounts(accounts);
    } else {
        // 6. Handle error - pass ResponseEntity status to validation
        logger.error("API returned status: {}", responseEntity.getStatusCode());
        ValidationUtils.validateResponse(
            response,
            responseEntity.getStatusCode(),    // From ResponseEntity
            errorMessage,
            throwError,
            meta
        );
        return null;
    }
}
```

---

#### Exception Handling

**Exceptions thrown by call():**
```java
try {
    ResponseEntity<String> responseEntity = restApiClient.call(...);
    // Process response
} catch (RestClientResponseException e) {
    // API returned error response (4xx, 5xx)
    logger.error("API error: status={}, body={}",
        e.getStatusCode(), e.getResponseBodyAsString());
    throw new ApiServerException(ErrorMessages.INTERNAL_SERVER_ERROR.withDetail(e.getMessage()), e);
} catch (ResourceAccessException e) {
    // Network/connection failure
    logger.error("Connection failed: {}", e.getMessage());
    throw new ApiServerException(ErrorMessages.INTERNAL_SERVER_ERROR.withDetail(e.getMessage()), e);
}
```

---

#### Best Practices

**✅ DO:**
- Use `call()` methods (not `makeRequest()`)
- Always use `String.class` as response type
- Parse JSON manually with ObjectMapper
- Check status from `responseEntity.getStatusCode()`
- Declare `ResponseEntity` at method scope for use in multiple places
- Handle both `RestClientResponseException` and `ResourceAccessException`

**❌ DON'T:**
- Don't use `makeRequest()` methods
- Don't check `response.getHttpStatus()` (returns null)
- Don't assume automatic JSON deserialization
- Don't ignore exception handling

---

#### Quick Reference

**GET Request:**
```java
ResponseEntity<String> response = restApiClient.call(
    HttpMethod.GET, uri, headers, String.class
);
```

**POST Request:**
```java
ResponseEntity<String> response = restApiClient.call(
    HttpMethod.POST, uri, requestBody, headers, String.class
);
```

**PUT Request:**
```java
ResponseEntity<String> response = restApiClient.call(
    HttpMethod.PUT, uri, requestBody, headers, String.class
);
```

**DELETE Request:**
```java
ResponseEntity<String> response = restApiClient.call(
    HttpMethod.DELETE, uri, headers, String.class
);
```

**Status Check:**
```java
if (responseEntity.getStatusCode().is2xxSuccessful()) {
    // Success
} else {
    // Error
}
```

---

**Reference:**
- **Library:** bap-bld-lib-restclient v1.4.002
- **Interface:** com.barclays.api.bap.bld.lib.restclient.RestApiClient
- **Implementation:** com.barclays.api.bap.bld.lib.restclient.CoreRestApiClient

---

### 6. ⚠️ Correlation ID Pattern Simplification

**Issue:** SDK3 simplifies correlation ID retrieval - no longer need to check X_CORRELATION_ID

**SDK2 (Complex Pattern):**
```java
String correlationId =
    StringUtils.hasText(MDC.get(InternalRequestContext.X_CORRELATION_ID))
        ? MDC.get(InternalRequestContext.X_CORRELATION_ID)
        : MDC.get(InternalRequestContext.CORRELATION_ID);
```

**SDK3 (Simplified Pattern):**
```java
String correlationId = MDC.get(InternalRequestContext.CORRELATION_ID);
```

**Why This Matters:**
- SDK3 consolidates correlation ID handling to single `CORRELATION_ID` constant
- `X_CORRELATION_ID` is no longer used or needed
- Simplifies code and reduces potential null pointer issues

**Detection:**
```bash
grep -r "X_CORRELATION_ID" src/main/java/
```

**Migration Actions:**
- Search for `X_CORRELATION_ID` in all Java files
- Replace ternary patterns with simple `CORRELATION_ID` retrieval
- Remove `StringUtils.hasText` check for correlation ID

**Full Details:** See Section 19.5.7 in sdk2_to_sdk3_migration_specification.md

---

## Summary

These six lessons represent the most critical patterns that differ between SDK2 and SDK3:

1. **Never use Eclipse/IDEA Gradle plugins** - they conflict with SDK3's bap-bld-lib-plugin
2. **Always check HTTP status from ResponseEntity** - RestResponse.getHttpStatus() returns null
3. **Use RestResponse.assemble() for building, Response interface for return types** - know the difference
4. **Remove Jersey dependencies from build.gradle** - incompatible with SDK3's RestApiClient
5. **Use RestApiClient.call() methods correctly** - understand the four variants and always use ResponseEntity<T>
6. **Simplify correlation ID retrieval** - use CORRELATION_ID only, remove X_CORRELATION_ID checks

Following these patterns will avoid the most common migration issues.

---

**Document Version:** 1.3
**Date:** 2026-01-07
**Migration Team:** SDK3 Migration
**New in 1.3:** Added Lesson 6 - Correlation ID Pattern Simplification
