# JUnit 4 to JUnit 5 Test Migration Specification

> **Used by:** junit-migration-agent | **Errors/Advanced:** [test_migration_errors_and_advanced.md](test_migration_errors_and_advanced.md)

---

## 1. Build Configuration

### 2.1 Gradle Dependencies

Add the following JUnit 5 dependencies to `build.gradle`:

```gradle
dependencies {
    // Test dependencies - JUnit 5
    testRuntimeOnly 'org.junit.platform:junit-platform-launcher'
    testImplementation 'org.junit.jupiter:junit-jupiter:5.13.4'
    testImplementation 'org.junit.platform:junit-platform-suite-api:1.10.1'  // For test suites
    testImplementation 'org.assertj:assertj-core:3.24.2'
    testImplementation 'org.mockito:mockito-core:5.9.0'
    testImplementation 'org.mockito:mockito-junit-jupiter:5.9.0'
    testImplementation 'org.springframework.boot:spring-boot-starter-test'

    // WireMock for API mocking
    testImplementation 'org.wiremock:wiremock-standalone:3.13.2'

    // Karate for API testing
    testImplementation 'com.intuit.karate:karate-junit5:1.4.1'
    testImplementation 'com.intuit.karate:karate-core:1.4.1'

    // Cucumber reporting
    testImplementation 'net.masterthought:cucumber-reporting:5.4.0'

    // Groovy for test scripting
    testImplementation 'org.codehaus.groovy:groovy:3.0.17'
}
```

**SDK3 Test Dependency Versions:**

| Dependency | SDK3 Version | Notes |
|------------|--------------|-------|
| junit-jupiter | 5.13.4 | Core JUnit 5 testing |
| junit-platform-suite-api | 1.10.1 | For @Suite and @SelectClasses |
| mockito-core | 5.9.0 | Mocking framework |
| mockito-junit-jupiter | 5.9.0 | Mockito JUnit 5 integration |
| wiremock-standalone | 3.13.2 | API mocking (replaces com.github.tomakehurst) |
| karate-junit5 | 1.4.1 | Karate API testing (replaces karate-junit4) |
| karate-core | 1.4.1 | Karate core library |
| cucumber-reporting | 5.4.0 | Cucumber test reporting |
| groovy | 3.0.17 | Groovy scripting support |

**Key Points:**
- `junit-jupiter` provides core JUnit 5 testing
- `junit-platform-suite-api` is required for `@Suite` and `@SelectClasses` annotations
- `mockito-junit-jupiter` provides Mockito integration for JUnit 5
- WireMock groupId changed from `com.github.tomakehurst` to `org.wiremock`
- Karate migrated from `karate-junit4` to `karate-junit5`

### 2.2 API Generation Task Configuration

**IMPORTANT:** When running tests, always exclude the `barclaysApiGenerate` task to avoid regenerating API code unnecessarily.

```bash
# Compile tests
$GRADLE_CMD compileTestJava -x barclaysApiGenerate

# Run tests
$GRADLE_CMD test -x barclaysApiGenerate
```

**For complete documentation on the `barclaysApiGenerate` task configuration and when to disable it, see:**
- [sdk2_to_sdk3_migration_specification.md - Section 1.7](sdk2_to_sdk3_migration_specification.md#17-api-generation-task-configuration)

---

## 3. Test Annotation Migration

### 3.1 Basic Test Annotations

JUnit 5 uses the same `@Test` annotation but from a different package.

#### JUnit 4 (BEFORE):
```java
import org.junit.Test;
import org.junit.Before;
import org.junit.After;

public class MyTest {
    @Before
    public void setUp() {
        // setup code
    }

    @Test
    public void myTestMethod() {
        // test code
    }

    @After
    public void tearDown() {
        // cleanup code
    }
}
```

#### JUnit 5 (AFTER):
```java
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.AfterEach;

public class MyTest {
    @BeforeEach
    public void setUp() {
        // setup code
    }

    @Test
    public void myTestMethod() {
        // test code
    }

    @AfterEach
    public void tearDown() {
        // cleanup code
    }
}
```

### 3.2 Import Mapping Table

| JUnit 4 | JUnit 5 | Notes |
|---------|---------|-------|
| `org.junit.Test` | `org.junit.jupiter.api.Test` | Basic test annotation |
| `org.junit.Before` | `org.junit.jupiter.api.BeforeEach` | Run before each test |
| `org.junit.After` | `org.junit.jupiter.api.AfterEach` | Run after each test |
| `org.junit.BeforeClass` | `org.junit.jupiter.api.BeforeAll` | Run once before all tests |
| `org.junit.AfterClass` | `org.junit.jupiter.api.AfterAll` | Run once after all tests |
| `org.junit.Ignore` | `org.junit.jupiter.api.Disabled` | Skip test execution |
| `org.junit.Assert` | `org.junit.jupiter.api.Assertions` | Assertion methods |

---

## 4. Exception Testing Migration

### 4.1 The @Test(expected) Pattern

One of the most significant changes in JUnit 5 is the removal of the `expected` parameter from `@Test`.

#### JUnit 4 Pattern (WRONG in JUnit 5):
```java
@Test(expected = ApiRequestException.class)
public void getTransactionsDetailsErrorTest() {
    InternalPostQueriesRequest request = CreateMixRequest();
    request.setAccountNumber("12d");
    accountsService.getTransactionsDetails(request, accountContext);
}
```

#### JUnit 5 Pattern (CORRECT):
```java
@Test
public void getTransactionsDetailsErrorTest() {
    Assertions.assertThrows(ApiRequestException.class, () -> {
        InternalPostQueriesRequest request = CreateMixRequest();
        request.setAccountNumber("12d");
        accountsService.getTransactionsDetails(request, accountContext);
    });
}
```

### 4.2 Step-by-Step Conversion

1. **Remove the `expected` parameter from `@Test`**
   ```java
   // BEFORE
   @Test(expected = ApiServerException.class)

   // AFTER
   @Test
   ```

2. **Wrap the test code in `assertThrows()`**
   ```java
   Assertions.assertThrows(ExpectedException.class, () -> {
       // Original test code here
   });
   ```

3. **Update imports**
   ```java
   import org.junit.jupiter.api.Assertions;
   ```

### 4.3 Real-World Examples

#### Example 1: Simple Exception Test

**BEFORE (JUnit 4):**
```java
@Test(expected = ApiRequestException.class)
public void getTransactionsDetailsRequestExceptionDateTest() {
    InternalPostQueriesRequest request = CreateMixRequest();
    request.setFromDate("2015-07-03");
    request.setToDate("2012-07-03");
    accountsService.getTransactionsDetails(request, accountContext);
}
```

**AFTER (JUnit 5):**
```java
@Test
public void getTransactionsDetailsRequestExceptionDateTest() {
    Assertions.assertThrows(ApiRequestException.class, () -> {
        InternalPostQueriesRequest request = CreateMixRequest();
        request.setFromDate("2015-07-03");
        request.setToDate("2012-07-03");
        accountsService.getTransactionsDetails(request, accountContext);
    });
}
```

#### Example 2: Complex Exception Test with Mocking

**BEFORE (JUnit 4):**
```java
@Test(expected = ApiServerException.class)
public void getAccountsDetailFromOdsRestFailTest() throws Exception {
    BDDMockito.given(restClient.callForResponse(any(), any(), any()))
        .willThrow(ResourceAccessException.class);
    refDbGateway.getStructuredEntryCodeFromOds(accountContext, meta);
}
```

**AFTER (JUnit 5):**
```java
@Test
public void getAccountsDetailFromOdsRestFailTest() throws Exception {
    BDDMockito.given(restClient.call(any(HttpMethod.class), any(URI.class),
                     any(HttpHeaders.class), eq(String.class)))
        .willThrow(ResourceAccessException.class);
    Assertions.assertThrows(ApiServerException.class, () -> {
        refDbGateway.getStructuredEntryCodeFromOds(accountContext, meta);
    });
}
```

### 4.4 Handling @Disabled Tests

Tests marked with `@Disabled` should keep the annotation along with the new pattern:

```java
@Disabled
@Test
public void getTransactionsDetailsErrorTest() throws Exception {
    Assertions.assertThrows(ApiRequestException.class, () -> {
        // test code
    });
}
```

---

## 5. Test Suite Migration

### 5.1 JUnit 4 vs JUnit 5 Test Suites

Test suites in JUnit 5 use different annotations and require an additional dependency.

#### JUnit 4 Pattern (WRONG in JUnit 5):
```java
import org.junit.runners.Suite;
import org.junit.runner.RunWith;

@RunWith(Suite.class)
@Suite.SuiteClasses({
    AccountEntriesControllerMockTest.class,
    AccountEntriesServiceMockTest.class,
    AccountGatewayMockTest.class,
    RefDbGatewayMockTest.class
})
public class MockTestSuite {
}
```

#### JUnit 5 Pattern (CORRECT):
```java
import org.junit.platform.suite.api.Suite;
import org.junit.platform.suite.api.SelectClasses;

@Suite
@SelectClasses({
    AccountEntriesControllerMockTest.class,
    AccountEntriesServiceMockTest.class,
    AccountGatewayMockTest.class,
    RefDbGatewayMockTest.class
})
public class MockTestSuite {
}
```

### 5.2 Required Dependency

**CRITICAL:** Test suites require the `junit-platform-suite-api` dependency:

```gradle
testImplementation 'org.junit.platform:junit-platform-suite-api:1.10.1'
```

**Without this dependency, you will get:**
```
error: package org.junit.platform.suite.api does not exist
import org.junit.platform.suite.api.SelectClasses;
```

### 5.3 Import Changes

| JUnit 4 | JUnit 5 |
|---------|---------|
| `org.junit.runner.RunWith` | *Removed - not needed* |
| `org.junit.runners.Suite` | `org.junit.platform.suite.api.Suite` |
| `@Suite.SuiteClasses` | `@SelectClasses` from `org.junit.platform.suite.api` |

### 5.4 Complete Example

#### File: `MockTestSuite.java`

**BEFORE (JUnit 4):**
```java
package com.barclays.iapi.branchaccounts.mock;

import com.barclays.iapi.branchaccounts.mock.controller.AccountEntriesControllerMockTest;
import com.barclays.iapi.branchaccounts.mock.gateway.AccountGatewayMockTest;
import com.barclays.iapi.branchaccounts.mock.gateway.RefDbGatewayMockTest;
import com.barclays.iapi.branchaccounts.mock.service.AccountEntriesServiceMockTest;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.runners.Suite;

@RunWith(Suite.class)
@Suite.SuiteClasses({
    AccountEntriesControllerMockTest.class,
    AccountEntriesServiceMockTest.class,
    AccountGatewayMockTest.class,
    RefDbGatewayMockTest.class
})
public class MockTestSuite {
}
```

**AFTER (JUnit 5):**
```java
package com.barclays.iapi.branchaccounts.mock;

import com.barclays.iapi.branchaccounts.mock.controller.AccountEntriesControllerMockTest;
import com.barclays.iapi.branchaccounts.mock.gateway.AccountGatewayMockTest;
import com.barclays.iapi.branchaccounts.mock.gateway.RefDbGatewayMockTest;
import com.barclays.iapi.branchaccounts.mock.service.AccountEntriesServiceMockTest;
import org.junit.platform.suite.api.SelectClasses;
import org.junit.platform.suite.api.Suite;

@Suite
@SelectClasses({
    AccountEntriesControllerMockTest.class,
    AccountEntriesServiceMockTest.class,
    AccountGatewayMockTest.class,
    RefDbGatewayMockTest.class
})
public class MockTestSuite {
}
```

---

## 6. Mocking Changes

### 6.1 Spring Boot Test Annotations

Spring Boot 3 changes the mock bean annotations.

#### BEFORE (Spring Boot 2 / SDK2):
```java
import org.springframework.boot.test.mock.mockito.MockBean;

@MockBean
private RestClient restClient;
```

#### AFTER (Spring Boot 3 / SDK3):
```java
import org.springframework.test.context.bean.override.mockito.MockitoBean;

@MockitoBean
private RestApiClient restClient;
```

### 6.2 Import Changes

| Spring Boot 2 | Spring Boot 3 |
|---------------|---------------|
| `org.springframework.boot.test.mock.mockito.MockBean` | `org.springframework.test.context.bean.override.mockito.MockitoBean` |

---

## 7. Response API Changes in Tests

### 7.1 Response.assemble() Migration

In SDK3, `Response.assemble()` and `Response.empty()` methods do not exist on the `Response` interface. They are only available on the concrete `RestResponse` class.

#### Problem Code (SDK2):
```java
private Response getRefDBodsEmptyResponse() {
    List<Resource<RulesClassResponse>> resourceList = new ArrayList<>();
    Response response = Response.assemble().build(resourceList);
    return response;
}
```

#### Fixed Code (SDK3):
```java
private Response getRefDBodsEmptyResponse() {
    List<Resource<RulesClassResponse>> resourceList = new ArrayList<>();
    Response response = RestResponse.assemble().build(resourceList);
    return response;
}
```

### 7.2 Response.empty() Migration

#### Problem Code (SDK2):
```java
private Response getNewODSErrorResponse() {
    Response response = Response.empty(HttpStatus.NOT_FOUND);
    List<Message> errors = new ArrayList<>();
    errors.add(Message.create("ERROR", "Error message"));
    response.setErrors(errors);  // This will fail!
    return response;
}
```

**Error:**
```
error: cannot find symbol
    response.setErrors(errors);
            ^
  symbol:   method setErrors(List<Message>)
  location: variable response of type Response
```

#### Fixed Code (SDK3):
```java
private Response getNewODSErrorResponse() {
    RestResponse response = RestResponse.empty(HttpStatus.NOT_FOUND);
    List<Message> errors = new ArrayList<>();
    errors.add(Message.create("ERROR", "Error message"));
    response.setErrors(errors);  // Now works!
    return response;
}
```

### 7.3 Required Imports

```java
import com.barclays.api.bap.bld.lib.common.response.Response;
import com.barclays.api.bap.bld.lib.payload.response.RestResponse;
import com.barclays.api.bap.bld.lib.payload.response.ResponseHttpStatus;
import org.springframework.http.HttpStatus;
```

### 7.4 Response.getData() Method Signature Change

In SDK3, the `Response.getData(TypeReference<T>)` method is only available on `RestResponse`, not on the `Response` interface.

#### Problem Code:
```java
Response response = accountsService.getTransactionsDetails(request, accountContext);
Resource<PostPostAccountEntriesResponse> postResource =
    response.getData(new TypeReference<Resource<PostPostAccountEntriesResponse>>() {});
```

**Error:**
```
error: no suitable method found for getData(<anonymous TypeReference<Resource<...>>>)
```

#### Solution 1: Use Class Parameter (Recommended):
```java
Response response = accountsService.getTransactionsDetails(request, accountContext);
Resource<PostPostAccountEntriesResponse> postResource =
    response.getData(Resource.class);
```

#### Solution 2: Change to RestResponse Type:
```java
RestResponse response = accountsService.getTransactionsDetails(request, accountContext);
Resource<PostPostAccountEntriesResponse> postResource =
    response.getData(new TypeReference<Resource<PostPostAccountEntriesResponse>>() {});
```

### 7.5 Response vs RestResponse Decision Matrix

| If you need to call... | Use Type... |
|------------------------|-------------|
| `getData()` | `Response` (interface) |
| `getData(Class<T>)` | `Response` (interface) |
| `getData(TypeReference<T>)` | `RestResponse` (concrete) |
| `setData()` | `RestResponse` (concrete) |
| `getErrors()` | `RestResponse` (concrete) |
| `setErrors()` | `RestResponse` (concrete) |
| `getMeta()` | `RestResponse` (concrete) |
| `setMeta()` | `RestResponse` (concrete) |
| `getHttpStatus()` | `RestResponse` (concrete) |

**Rule of Thumb:**
- **Use `Response`** when you only need to read data
- **Use `RestResponse`** when you need to build, modify, or access metadata

> **Canonical Reference:** See `lessons_learnt.md` Section 3 for the complete Response vs RestResponse guide with method availability matrix, package locations, and full service examples.

### 7.6 Casting Response to RestResponse in Tests

When handlers return `Response` interface (as is common in production code), but tests need to access RestResponse-specific methods like `getHttpStatus()` or `getErrors()`, you must cast explicitly.

#### Problem - Handler Returns Response Interface:

```java
// Production handler method signature
public Response execute(Request request) {
    // ...
    return RestResponse.assemble().build(data);
}
```

#### Problem Code - Test Accessing RestResponse Methods:

```java
@Test
public void testHandlerSuccess() {
    Response response = handler.execute(request);
    // ERROR: cannot find symbol: method getHttpStatus()
    assertEquals(HttpStatus.OK, response.getHttpStatus());
    // ERROR: cannot find symbol: method getErrors()
    assertNotNull(response.getErrors());
}
```

**Error:**
```
error: cannot find symbol
  symbol:   method getHttpStatus()
  location: variable response of type Response
```

#### Solution - Explicit Cast to RestResponse:

```java
@Test
public void testHandlerSuccess() {
    Response response = handler.execute(request);
    // CORRECT: Cast to RestResponse to access implementation methods
    assertEquals(HttpStatus.OK, ((RestResponse) response).getHttpStatus());
    assertNotNull(((RestResponse) response).getErrors());
}
```

#### Alternative - Store as RestResponse in Test:

```java
@Test
public void testHandlerSuccess() {
    // Cast at assignment if you need multiple RestResponse methods
    RestResponse response = (RestResponse) handler.execute(request);
    assertEquals(HttpStatus.OK, response.getHttpStatus());
    assertNotNull(response.getErrors());
    assertNull(response.getData());
}
```

### 7.7 Bulk Fix Commands for Response Casting

When migrating tests with many `response.getHttpStatus()` or `response.getErrors()` calls:

Use the Edit tool or `replace_text_in_file` MCP tool for these bulk replacements. Avoid `find -exec sed` (not cross-platform).

- **Fix getHttpStatus() calls:** Replace `response.getHttpStatus()` with `((RestResponse) response).getHttpStatus()` in all `src/test/**/*.java` files
- **Fix getErrors() calls:** Replace `response.getErrors()` with `((RestResponse) response).getErrors()` in all `src/test/**/*.java` files
- **Add RestResponse import:** After each `import...common.response.Response;` line, add `import com.barclays.api.bap.bld.lib.payload.response.RestResponse;`

**Warning:** Review the changes after running bulk fixes to ensure correct behavior.

### 7.8 When NOT to Cast

Don't cast when calling methods that exist on the `Response` interface:

```java
// These methods exist on Response interface - NO CAST NEEDED
Object data = response.getData();
Object data = response.getData(MyClass.class);
```

Only cast when calling RestResponse-specific methods:
- `getHttpStatus()`
- `setHttpStatus()`
- `getErrors()`
- `setErrors()`
- `getMeta()`
- `setMeta()`
- `setData()`
- `getData(TypeReference<T>)` (the TypeReference variant)

---

## 8. RestApiClient Mocking for SDK3

### 8.1 The Challenge

In SDK2, `RestClient.callForResponse()` returned a `Response` object directly. In SDK3, `RestApiClient.call()` returns a `ResponseEntity<String>` that must be deserialized.

#### SDK2 Pattern (OLD):
```java
// Mock returns Response directly
BDDMockito.given(restClient.callForResponse(any(), any(), any()))
    .willReturn(getRefDBodsResponse());

private Response getRefDBodsResponse() {
    // Build and return Response
}
```

#### SDK3 Pattern (NEW):
```java
// Mock returns ResponseEntity<String> with serialized JSON
BDDMockito.given(restClient.call(any(HttpMethod.class), any(URI.class),
                                  any(HttpHeaders.class), eq(String.class)))
    .willReturn(toResponseEntity(getRefDBodsResponse()));

private ResponseEntity<String> toResponseEntity(Response response)
        throws JsonProcessingException {
    String json = objectMapper.writeValueAsString(response);
    return ResponseEntity.ok(json);
}

private Response getRefDBodsResponse() {
    // Build and return Response
}
```

### 8.2 Step-by-Step Migration

#### Step 1: Add ObjectMapper to Test Class

```java
@ExtendWith(SpringExtension.class)
@SpringBootTest
public class AccountGatewayMockTest {

    @MockitoBean
    private RestApiClient restClient;

    @Autowired
    private ObjectMapper objectMapper;  // ADD THIS

    // ... rest of class
}
```

#### Step 2: Add Helper Method

```java
// Helper method to convert Response to ResponseEntity<String> for SDK3 mocking
private ResponseEntity<String> toResponseEntity(Response response)
        throws JsonProcessingException {
    String json = objectMapper.writeValueAsString(response);
    return ResponseEntity.ok(json);
}
```

#### Step 3: Add Required Imports

```java
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.http.ResponseEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import java.net.URI;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
```

#### Step 4: Update Mock Statements

**BEFORE (SDK2):**
```java
BDDMockito.given(restClient.callForResponse(any(), any(), any()))
    .willReturn(getodsResponse());
```

**AFTER (SDK3):**
```java
BDDMockito.given(restClient.call(any(HttpMethod.class), any(URI.class),
                                  any(HttpHeaders.class), eq(String.class)))
    .willReturn(toResponseEntity(getodsResponse()));
```

**Why the specific matchers?**
- `any(HttpMethod.class)` - HTTP method (GET, POST, etc.)
- `any(URI.class)` - Request URI
- `any(HttpHeaders.class)` - Request headers
- `eq(String.class)` - Response type class (always String.class for JSON)

Using specific matchers avoids "reference to call is ambiguous" errors when `RestApiClient` has multiple overloaded `call()` methods.

### 8.3 Complete Example: RefDbGatewayMockTest

**BEFORE (SDK2):**
```java
package com.barclays.iapi.branchaccounts.mock.gateway;

import com.barclays.api.core.web.util.RestClient;
import org.junit.Test;
import org.mockito.BDDMockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.mock.mockito.MockBean;

import static org.mockito.ArgumentMatchers.any;

public class RefDbGatewayMockTest {

    @MockBean
    RestClient restClient;

    @Autowired
    RefdbGateway refDbGateway;

    @Test
    public void getAccountsDetailFromOdsSucessTest() throws Exception {
        BDDMockito.given(restClient.callForResponse(any(), any(), any()))
            .willReturn(getRefDBodsResponse());
        String response = refDbGateway.getStructuredEntryCodeFromOds(accountContext, meta);
        Assertions.assertNotNull(response);
    }

    private Response getRefDBodsResponse() {
        List<Resource<RulesClassResponse>> resourceList = new ArrayList<>();
        resourceList.add(getListodsResponse());
        Response response = Response.assemble().build(resourceList);
        return response;
    }
}
```

**AFTER (SDK3):**
```java
package com.barclays.iapi.branchaccounts.mock.gateway;

import com.barclays.api.bap.bld.lib.restclient.RestApiClient;
import com.barclays.api.bap.bld.lib.payload.response.RestResponse;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;
import org.mockito.BDDMockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.http.ResponseEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;

import java.net.URI;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;

public class RefDbGatewayMockTest {

    @MockitoBean
    RestApiClient restClient;

    @Autowired
    RefdbGateway refDbGateway;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    public void getAccountsDetailFromOdsSucessTest() throws Exception {
        BDDMockito.given(restClient.call(any(HttpMethod.class), any(URI.class),
                                          any(HttpHeaders.class), eq(String.class)))
            .willReturn(toResponseEntity(getRefDBodsResponse()));
        String response = refDbGateway.getStructuredEntryCodeFromOds(accountContext, meta);
        Assertions.assertNotNull(response);
    }

    // Helper method to convert Response to ResponseEntity<String> for SDK3 mocking
    private ResponseEntity<String> toResponseEntity(Response response)
            throws JsonProcessingException {
        String json = objectMapper.writeValueAsString(response);
        return ResponseEntity.ok(json);
    }

    private Response getRefDBodsResponse() {
        List<Resource<RulesClassResponse>> resourceList = new ArrayList<>();
        resourceList.add(getListodsResponse());
        Response response = RestResponse.assemble().build(resourceList);
        return response;
    }
}
```

### 8.4 Exception Mocking

When mocking exceptions with the SDK3 `call()` method:

**BEFORE (SDK2):**
```java
@Test(expected = ApiServerException.class)
public void getAccountsDetailFromOdsExceptionTest() throws JsonProcessingException {
    BDDMockito.given(restClient.callForResponse(any(), any(), any()))
        .willThrow(ResourceAccessException.class);
    accountGatewayImpl.getAccountsDetailFromOds("20165600018201", "2018-07-23",
                                                  "2018-07-24", accountContext,
                                                  structureType, meta);
}
```

**AFTER (SDK3):**
```java
@Test
public void getAccountsDetailFromOdsExceptionTest() throws JsonProcessingException {
    BDDMockito.given(restClient.call(any(HttpMethod.class), any(URI.class),
                                      any(HttpHeaders.class), eq(String.class)))
        .willThrow(ResourceAccessException.class);
    Assertions.assertThrows(ApiServerException.class, () -> {
        accountGatewayImpl.getAccountsDetailFromOds("20165600018201", "2018-07-23",
                                                      "2018-07-24", accountContext,
                                                      structureType, meta);
    });
}
```

---

## 9. Complete Migration Checklist

Use this checklist to track your test migration progress:

### 9.1 Build Configuration

- [ ] Add `org.junit.jupiter:junit-jupiter` dependency
- [ ] Add `org.junit.platform:junit-platform-suite-api` dependency (if using test suites)
- [ ] Add `org.mockito:mockito-junit-jupiter` dependency
- [ ] Configure `barclaysApiGenerate` task to be disabled or skipped during tests
- [ ] Update Gradle commands to use `-x barclaysApiGenerate`

### 9.2 Import Updates

- [ ] Replace `org.junit.Test` with `org.junit.jupiter.api.Test`
- [ ] Replace `org.junit.Before` with `org.junit.jupiter.api.BeforeEach`
- [ ] Replace `org.junit.After` with `org.junit.jupiter.api.AfterEach`
- [ ] Replace `org.junit.Assert` with `org.junit.jupiter.api.Assertions`
- [ ] Replace `org.junit.Ignore` with `org.junit.jupiter.api.Disabled`

### 9.3 Test Method Updates

- [ ] Remove all `@Test(expected = Exception.class)` patterns
- [ ] Convert to `Assertions.assertThrows(Exception.class, () -> { ... })`
- [ ] Update all exception tests (look for `expected =` in @Test annotations)

### 9.4 Test Suite Migration

- [ ] Remove `@RunWith(Suite.class)` annotations
- [ ] Replace `@Suite.SuiteClasses` with `@SelectClasses`
- [ ] Add `@Suite` annotation
- [ ] Update imports to use `org.junit.platform.suite.api.*`

### 9.5 Spring Boot Test Annotations

- [ ] Replace `@MockBean` with `@MockitoBean`
- [ ] Update imports to `org.springframework.test.context.bean.override.mockito.MockitoBean`

### 9.6 Response API Updates in Tests

- [ ] Replace `Response.assemble()` with `RestResponse.assemble()`
- [ ] Replace `Response.empty()` with `RestResponse.empty()`
- [ ] Change variable types from `Response` to `RestResponse` where `setErrors()`, `setData()`, etc. are called
- [ ] Replace `getData(TypeReference<T>)` with `getData(Class<T>)` or use `RestResponse` type

### 9.7 RestApiClient Mocking

- [ ] Add `@Autowired ObjectMapper` to test classes that mock REST calls
- [ ] Add `toResponseEntity()` helper method to test classes
- [ ] Replace `restClient.callForResponse(any(), any(), any())` with specific matchers
- [ ] Update to `restClient.call(any(HttpMethod.class), any(URI.class), any(HttpHeaders.class), eq(String.class))`
- [ ] Wrap mock return values with `toResponseEntity(...)`
- [ ] Add required imports: `HttpMethod`, `URI`, `HttpHeaders`, `ResponseEntity`, `ObjectMapper`

### 9.8 Assertion Method Argument Order Verification

- [ ] Verify `assertEquals()` calls have expected value first: `assertEquals(expected, actual, message)`
- [ ] Verify `assertNotEquals()` calls have expected value first: `assertNotEquals(expected, actual, message)`
- [ ] Verify `assertThrows()` calls have exception class first: `assertThrows(ExceptionClass.class, () -> { ... })`
- [ ] Verify `assertTrue()/assertFalse()` have condition first: `assertTrue(condition, message)`
- [ ] Verify `assertNull()/assertNotNull()` have value first: `assertNotNull(value, message)`
- [ ] Ensure all message parameters are the last argument
- [ ] Review all assertions for consistency and proper ordering (see Section 10.1a)

### 9.9 Verification

- [ ] Compile tests: `$GRADLE_CMD compileTestJava -x barclaysApiGenerate`
- [ ] Run tests: `$GRADLE_CMD test -x barclaysApiGenerate`
- [ ] Verify test count matches expected
- [ ] Check test coverage reports
- [ ] Review test failure messages for clarity

---

---

**END OF SPECIFICATION**
