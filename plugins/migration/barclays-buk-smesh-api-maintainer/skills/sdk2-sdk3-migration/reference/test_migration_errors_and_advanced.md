# JUnit 4 to JUnit 5 Test Migration — Errors & Advanced Topics

> **Split Note:** Sections 10-13 from test_migration_specification.md. For core migration mappings (Sections 1-9), see [test_migration_specification.md](test_migration_specification.md).

---

## 10. Common Errors and Solutions

### 10.1 Compilation Errors

#### Error: "cannot find symbol @Test(expected)"
```
error: cannot find symbol
@Test(expected = ApiRequestException.class)
      ^
  symbol:   method expected()
```

**Cause:** JUnit 5 doesn't support the `expected` parameter on `@Test`.

**Solution:** Convert to `assertThrows()` pattern (see Section 4).

---

#### Error: "cannot find symbol @RunWith"
```
error: cannot find symbol
@RunWith(Suite.class)
 ^
  symbol: class RunWith
```

**Cause:** JUnit 5 doesn't use `@RunWith` for test suites.

**Solution:** Replace with `@Suite` and `@SelectClasses` (see Section 5).

---

#### Error: "package org.junit.platform.suite.api does not exist"
```
error: package org.junit.platform.suite.api does not exist
import org.junit.platform.suite.api.SelectClasses;
```

**Cause:** Missing `junit-platform-suite-api` dependency.

**Solution:**
```gradle
testImplementation 'org.junit.platform:junit-platform-suite-api:1.10.1'
```

---

#### Error: "cannot find symbol Response.assemble()"
```
error: cannot find symbol
Response response = Response.assemble().build(resourceList);
                            ^
  symbol:   method assemble()
  location: interface Response
```

**Cause:** `assemble()` method is only on `RestResponse`, not `Response` interface.

**Solution:** Change to `RestResponse.assemble()` (see Section 7).

---

#### Error: "cannot find symbol response.setErrors()"
```
error: cannot find symbol
response.setErrors(errors);
        ^
  symbol:   method setErrors(List<Message>)
  location: variable response of type Response
```

**Cause:** `setErrors()` method is only on `RestResponse`, not `Response` interface.

**Solution:** Change variable type to `RestResponse` (see Section 7).

---

#### Error: "reference to call is ambiguous"
```
error: reference to call is ambiguous
BDDMockito.given(restClient.call(any(), any(), any(), any()))
                           ^
```

**Cause:** `RestApiClient` has multiple `call()` methods with 4 parameters.

**Solution:** Use specific argument matchers:
```java
restClient.call(any(HttpMethod.class), any(URI.class),
                any(HttpHeaders.class), eq(String.class))
```

---

#### Error: "no suitable method found for willReturn(ResponseEntity<String>)"
```
error: no suitable method found for willReturn(ResponseEntity<String>)
```

**Cause:** Ambiguous method reference due to generic matchers.

**Solution:** Same as above - use specific matchers with types.

---

#### Error: "cannot find symbol" - Missing Assertion Method Imports
```
error: cannot find symbol
        assertThrows(NoSuchAlgorithmException.class, () -> {
        ^
  symbol:   method assertThrows(Class,functional interface)
  location: class MyTest
```

**Cause:** The assertion method is used but not imported. When migrating from JUnit 4, developers often only import `assertNotNull` or other commonly-used methods, forgetting to import all required assertions.

**Solution:**
```java
// Option 1: Import all assertions (RECOMMENDED)
import static org.junit.jupiter.api.Assertions.*;

// Option 2: Import specific assertion methods
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertEquals;
```

**Prevention:** Always use `import static org.junit.jupiter.api.Assertions.*;` to avoid missing individual assertion imports.

---

### 10.1a JUnit5 Assertion Method Argument Order

#### Overview

JUnit5 assertion methods have specific parameter orders that differ from manual validation code. Developers migrating from JUnit 4 sometimes accidentally reverse the argument order, leading to confusing test failures.

#### Common Assertion Methods and Their Correct Signatures

| Method | Signature | Correct Order | Example |
|--------|-----------|---------------|---------|
| `assertNotNull()` | `assertNotNull(T value, String message)` | (actual, message) | `assertNotNull(template, "MongoTemplate should not be null")` |
| `assertNull()` | `assertNull(T value, String message)` | (actual, message) | `assertNull(result, "Result should be null")` |
| `assertEquals()` | `assertEquals(T expected, T actual, String message)` | (expected, actual, message) | `assertEquals("expected", actual, "Values don't match")` |
| `assertNotEquals()` | `assertNotEquals(T expected, T actual, String message)` | (expected, actual, message) | `assertNotEquals(0, count, "Count should not be zero")` |
| `assertTrue()` | `assertTrue(boolean condition, String message)` | (condition, message) | `assertTrue(isValid, "Should be valid")` |
| `assertFalse()` | `assertFalse(boolean condition, String message)` | (condition, message) | `assertFalse(isEmpty, "Should not be empty")` |
| `assertThrows()` | `<T extends Throwable> T assertThrows(Class<T> expectedType, Executable executable)` | (exceptionClass, codeBlock) | `assertThrows(ApiException.class, () -> { ... })` |
| `assertDoesNotThrow()` | `<T> T assertDoesNotThrow(Executable executable)` | (codeBlock) | `assertDoesNotThrow(() -> { ... })` |

#### Critical Differences from JUnit 4

**JUnit 4 Pattern (INCORRECT for JUnit 5):**
```java
// JUnit 4 assertions - different parameter order
assertEquals(actualValue, expectedValue);  // actual first, expected second
```

**JUnit 5 Pattern (CORRECT):**
```java
// JUnit 5 assertions - expected FIRST, actual SECOND
assertEquals(expectedValue, actualValue, "Message");  // expected first, actual second
```

#### Real-World Examples

##### Example 1: Simple Value Assertion

**WRONG - Reversed Arguments:**
```java
@Test
public void testCalculateTotal() {
    int actual = calculator.add(2, 3);
    // WRONG: Message as first argument, value as second
    assertEquals("Result should be 5", actual);

    // WRONG: Value first, expected second
    assertEquals(actual, 5);
}
```

**CORRECT - Proper Argument Order:**
```java
@Test
public void testCalculateTotal() {
    int actual = calculator.add(2, 3);
    // CORRECT: Expected value first, actual second, message last
    assertEquals(5, actual, "Result should be 5");
}
```

##### Example 2: Exception Testing

**WRONG - Message as First Parameter:**
```java
@Test
public void testThrowsException() {
    // WRONG: Message cannot be first parameter for assertThrows
    assertThrows("Should throw exception", ApiException.class, () -> {
        service.throwException();
    });
}
```

**CORRECT - Exception Class First:**
```java
@Test
public void testThrowsException() {
    // CORRECT: Exception class first, then executable code
    assertThrows(ApiException.class, () -> {
        service.throwException();
    });
}
```

##### Example 3: String Comparison

**WRONG - Actual vs Expected Reversed:**
```java
@Test
public void testStringFormatting() {
    String actual = service.formatName("john", "doe");
    // WRONG: Actual first, expected second
    assertEquals(actual, "John Doe", "Name format incorrect");
}
```

**CORRECT - Expected vs Actual Proper Order:**
```java
@Test
public void testStringFormatting() {
    String actual = service.formatName("john", "doe");
    // CORRECT: Expected first, actual second
    assertEquals("John Doe", actual, "Name format incorrect");
}
```

#### Why Argument Order Matters

1. **Test Report Clarity** - When a test fails, JUnit displays "expected X but got Y". Having the correct order makes the message meaningful.

2. **IDE Support** - IDEs with JUnit support can better suggest fixes if argument order is correct.

3. **Code Review** - Reviewers can immediately spot mistakes with proper argument order conventions.

**Comparison of Test Failure Messages:**

```java
// WRONG ORDER: assertEquals(actual, expected)
assertEquals(5, 10, "Values don't match");
// Output: "Values don't match - expected 5 but got 10" (CONFUSING!)

// CORRECT ORDER: assertEquals(expected, actual)
assertEquals(10, 5, "Values don't match");
// Output: "Values don't match - expected 10 but got 5" (CLEAR!)
```

#### Checklist for Argument Order Verification

When reviewing test code, check:

- [ ] `assertEquals()` has expected value first
- [ ] `assertNotEquals()` has expected value first
- [ ] `assertThrows()` has exception class first, then code block
- [ ] `assertTrue()/assertFalse()` have condition first, message last
- [ ] `assertNull()/assertNotNull()` have value first, message last
- [ ] Messages (if present) are always the last argument
- [ ] No message parameters appear before actual/expected values

#### Migration from JUnit 4

If you see `Assert.assertEquals()` patterns in your JUnit 4 code:

```java
// JUnit 4 (legacy)
import org.junit.Assert;
Assert.assertEquals(actualValue, expectedValue);  // Note the order!

// JUnit 5 (corrected)
import static org.junit.jupiter.api.Assertions.assertEquals;
assertEquals(expectedValue, actualValue);  // Expected FIRST
```

Note: JUnit 4 `Assert.assertEquals()` also had expected first, actual second, so if you maintained that pattern, your conversion should be straightforward. However, if the original code was inconsistent, now is the time to fix it.

---

### 10.2 Runtime Errors

#### Error: Tests not found or not running

**Symptoms:**
- Gradle says "0 tests completed"
- Test methods are not discovered

**Possible Causes:**
1. Missing `@Test` annotation
2. Test class not public
3. Missing JUnit 5 dependencies

**Solution:**
1. Verify `@Test` annotation is `org.junit.jupiter.api.Test`
2. Ensure test class is `public`
3. Verify `testImplementation 'org.junit.jupiter:junit-jupiter'` in build.gradle

---

#### Error: JsonProcessingException when mocking

**Symptoms:**
```
com.fasterxml.jackson.databind.exc.InvalidDefinitionException:
No serializer found for class ...
```

**Cause:** Response object contains non-serializable fields or circular references.

**Solution:**
1. Ensure all DTOs used in tests are serializable
2. Use `@JsonIgnore` on problematic fields
3. Configure ObjectMapper with appropriate settings

---

### 10.3 Best Practices

1. **Always read files before editing** - Use the Read tool first
2. **Update imports systematically** - Check all JUnit 4 imports
3. **Test incrementally** - Compile after each major change
4. **Use specific matchers** - Avoid `any()` for all parameters when mocking
5. **Document complex changes** - Add comments for non-obvious conversions
6. **Run tests frequently** - Don't wait until all changes are done
7. **Check test coverage** - Ensure coverage requirements are met

---

## 11. Karate Test Migration (JUnit 4 → JUnit 5)

### 11.1 Overview

Karate 0.9.x uses JUnit 4 and is **NOT compatible with Java 21**. You must migrate to Karate 1.4.x which uses JUnit 5.

**Key Changes:**
- `karate-junit4` → `karate-junit5`
- `@RunWith(Karate.class)` → `@Karate.Test` method annotation
- `@KarateOptions(features=...)` → Programmatic configuration
- `Runner.parallel()` → `Runner.path().parallel()`

### 11.2 Dependency Changes

#### Gradle - BEFORE (SDK2 / JUnit 4):
```gradle
testImplementation 'com.intuit.karate:karate-core:0.9.6'
testImplementation 'com.intuit.karate:karate-apache:0.9.6'
testImplementation 'com.intuit.karate:karate-testng:0.8.0.RC9'
testImplementation 'com.intuit.karate:karate-junit4:0.9.6'
testImplementation 'net.masterthought:cucumber-reporting:5.4.0'
```

#### Gradle - AFTER (SDK3 / JUnit 5):
```gradle
testImplementation 'com.intuit.karate:karate-junit5:1.4.1'
testImplementation 'net.masterthought:cucumber-reporting:5.7.7'
```

#### Maven - AFTER (SDK3 / JUnit 5):
```xml
<dependency>
    <groupId>com.intuit.karate</groupId>
    <artifactId>karate-junit5</artifactId>
    <version>1.4.1</version>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>net.masterthought</groupId>
    <artifactId>cucumber-reporting</artifactId>
    <version>5.7.7</version>
    <scope>test</scope>
</dependency>
```

**Notes:**
- `karate-junit5` includes `karate-core` transitively - no need for separate dependency
- Remove `karate-apache` and `karate-testng` - not needed with Karate 1.x
- Update `cucumber-reporting` to 5.7.7 for compatibility

### 11.3 TestRunner Migration

#### JUnit 4 Pattern (BEFORE):
```java
package KarateTest;

import com.intuit.karate.KarateOptions;
import com.intuit.karate.Results;
import com.intuit.karate.Runner;
import com.intuit.karate.junit4.Karate;
import org.junit.AfterClass;
import org.junit.Assert;
import org.junit.BeforeClass;
import org.junit.runner.RunWith;

@RunWith(Karate.class)
@KarateOptions(
    features = {
      "src/integrationTest/resources/features/myFeature1.feature",
      "src/integrationTest/resources/features/myFeature2.feature"
    })
public class TestRunner {

  private static Results results;

  @BeforeClass
  public static void beforeClass() throws Exception {
    // Start application and wiremock
    Application.main(new String[]{"--spring.profiles.active=int-test"});
    results = Runner.parallel(TestRunner.class, 1);
  }

  @AfterClass
  public static void tearDown() throws Exception {
    // Cleanup
    Assert.assertTrue(results.getErrorMessages(), results.getFailCount() == 0);
  }
}
```

#### JUnit 5 Pattern (AFTER):
```java
package KarateTest;

import com.intuit.karate.Results;
import com.intuit.karate.Runner;
import com.intuit.karate.junit5.Karate;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeAll;

public class TestRunner {

  private static Results results;

  /** Feature files to run - classpath prefix for resources */
  private static final String[] FEATURES = {
    "classpath:features/myFeature1.feature",
    "classpath:features/myFeature2.feature"
  };

  @BeforeAll
  public static void beforeAll() throws Exception {
    // Start application and wiremock
    Application.main(new String[]{"--spring.profiles.active=int-test"});
  }

  /**
   * Karate test runner - JUnit 5 style.
   * This method is discovered and executed by JUnit 5.
   */
  @Karate.Test
  Karate testAll() {
    return Karate.run(FEATURES).relativeTo(getClass());
  }

  @AfterAll
  public static void afterAll() throws Exception {
    // Run parallel for reporting (separate from @Karate.Test execution)
    results = Runner.path(FEATURES).parallel(1);
    Assertions.assertEquals(0, results.getFailCount(), results.getErrorMessages());
  }
}
```

### 11.4 Key API Changes

| JUnit 4 (Karate 0.9.x) | JUnit 5 (Karate 1.4.x) | Notes |
|------------------------|------------------------|-------|
| `@RunWith(Karate.class)` | *Removed* | Not needed |
| `@KarateOptions(features={...})` | `@Karate.Test` method | Programmatic |
| `Runner.parallel(Class, int)` | `Runner.path(String[]).parallel(int)` | API changed |
| `results.getFailedMap()` | `results.getErrorMessages()` | Method renamed |
| `Assert.assertTrue(msg, cond)` | `Assertions.assertEquals(exp, act, msg)` | JUnit 5 style |

### 11.5 Import Changes

| JUnit 4 | JUnit 5 |
|---------|---------|
| `com.intuit.karate.junit4.Karate` | `com.intuit.karate.junit5.Karate` |
| `com.intuit.karate.KarateOptions` | *Removed - not needed* |
| `org.junit.runner.RunWith` | *Removed - not needed* |
| `org.junit.BeforeClass` | `org.junit.jupiter.api.BeforeAll` |
| `org.junit.AfterClass` | `org.junit.jupiter.api.AfterAll` |
| `org.junit.Assert` | `org.junit.jupiter.api.Assertions` |

### 11.6 Feature File Path Changes

**IMPORTANT:** Feature file paths change from relative to classpath-based:

| JUnit 4 Pattern | JUnit 5 Pattern |
|-----------------|-----------------|
| `"src/integrationTest/resources/features/test.feature"` | `"classpath:features/test.feature"` |

The `classpath:` prefix tells Karate to look in the test resources directory.

### 11.7 Complete Migration Example

#### File: `TestRunner.java`

**BEFORE (Karate 0.9.6 / JUnit 4):**
```java
package KarateTest;

import com.barclays.api.bap.bld.lib.logging.LogFactory;
import com.barclays.api.bap.bld.lib.logging.Logger;
import com.barclays.iapi.paymentchecks.Application;
import com.intuit.karate.KarateOptions;
import com.intuit.karate.Results;
import com.intuit.karate.Runner;
import com.intuit.karate.junit4.Karate;
import java.io.File;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import net.masterthought.cucumber.Configuration;
import net.masterthought.cucumber.ReportBuilder;
import org.apache.commons.io.FileUtils;
import org.junit.AfterClass;
import org.junit.Assert;
import org.junit.BeforeClass;
import org.junit.runner.RunWith;

@RunWith(Karate.class)
@KarateOptions(
    features = {
      "src/integrationTest/resources/features/test1.feature",
      "src/integrationTest/resources/features/test2.feature"
    })
public class TestRunner {

  private static final Logger LOG = LogFactory.getLogger(TestRunner.class);
  public static WireMockClass wireMock;
  private static Results results;

  @BeforeClass
  public static void beforeClass() throws Exception {
    LOG.info("Starting application");
    String[] args = {"--spring.profiles.active=int-test"};
    Application.main(args);
    wireMock = new WireMockClass();
    wireMock.startWiremock();
    results = Runner.parallel(TestRunner.class, 1);
  }

  @AfterClass
  public static void tearDown() throws Exception {
    wireMock.stopWiremock();
    generateReport(results.getReportDir(), results);
    Assert.assertTrue(results.getErrorMessages(), results.getFailCount() == 0);
  }

  public static void generateReport(String karateOutputPath, Results results) {
    Collection<File> jsonFiles =
        FileUtils.listFiles(new File(karateOutputPath), new String[] {"json"}, true);
    List<String> jsonPaths = new ArrayList(jsonFiles.size());
    jsonFiles.forEach(file -> jsonPaths.add(file.getAbsolutePath()));
    Configuration config = new Configuration(new File("target"), "myTests");
    ReportBuilder reportBuilder = new ReportBuilder(jsonPaths, config);
    reportBuilder.generateReports();
  }
}
```

**AFTER (Karate 1.4.1 / JUnit 5):**
```java
package KarateTest;

import com.barclays.api.bap.bld.lib.logging.LogFactory;
import com.barclays.api.bap.bld.lib.logging.Logger;
import com.barclays.iapi.paymentchecks.Application;
import com.intuit.karate.Results;
import com.intuit.karate.Runner;
import com.intuit.karate.junit5.Karate;
import java.io.File;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import net.masterthought.cucumber.Configuration;
import net.masterthought.cucumber.ReportBuilder;
import org.apache.commons.io.FileUtils;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeAll;

/** JUnit 5 Karate test runner for Java 21. */
public class TestRunner {

  private static final Logger LOG = LogFactory.getLogger(TestRunner.class);
  public static WireMockClass wireMock;
  private static Results results;

  /** Feature files - use classpath prefix */
  private static final String[] FEATURES = {
    "classpath:features/test1.feature",
    "classpath:features/test2.feature"
  };

  @BeforeAll
  public static void beforeAll() throws Exception {
    LOG.info("Starting application");
    String[] args = {"--spring.profiles.active=int-test"};
    Application.main(args);
    wireMock = new WireMockClass();
    wireMock.startWiremock();
  }

  /** Karate test entry point - JUnit 5 style */
  @Karate.Test
  Karate testAll() {
    return Karate.run(FEATURES).relativeTo(getClass());
  }

  @AfterAll
  public static void afterAll() throws Exception {
    wireMock.stopWiremock();
    // Run parallel for reporting
    results = Runner.path(FEATURES).parallel(1);
    generateReport(results.getReportDir(), results);
    Assertions.assertEquals(0, results.getFailCount(), results.getErrorMessages());
  }

  public static void generateReport(String karateOutputPath, Results results) {
    Collection<File> jsonFiles =
        FileUtils.listFiles(new File(karateOutputPath), new String[] {"json"}, true);
    List<String> jsonPaths = new ArrayList<>(jsonFiles.size());
    jsonFiles.forEach(file -> jsonPaths.add(file.getAbsolutePath()));
    Configuration config = new Configuration(new File("target"), "myTests");
    ReportBuilder reportBuilder = new ReportBuilder(jsonPaths, config);
    reportBuilder.generateReports();
  }
}
```

### 11.8 Migration Checklist

- [ ] Update `build.gradle` or `pom.xml` with `karate-junit5:1.4.1`
- [ ] Remove old Karate dependencies (`karate-core`, `karate-apache`, `karate-testng`, `karate-junit4`)
- [ ] Update `cucumber-reporting` to `5.7.7`
- [ ] Remove `@RunWith(Karate.class)` annotation
- [ ] Remove `@KarateOptions` annotation
- [ ] Add `@Karate.Test` method returning `Karate` instance
- [ ] Change feature paths from relative to `classpath:` prefix
- [ ] Replace `@BeforeClass` with `@BeforeAll`
- [ ] Replace `@AfterClass` with `@AfterAll`
- [ ] Replace `Assert` with `Assertions`
- [ ] Update `Runner.parallel()` to `Runner.path().parallel()`
- [ ] Verify integration tests compile: `$GRADLE_CMD compileIntegrationTestJava`

### 11.9 Common Errors

#### Error: "java.lang.NoClassDefFoundError: com/intuit/karate/junit4/Karate"
**Cause:** Still using old `karate-junit4` dependency.
**Solution:** Replace with `karate-junit5:1.4.1`.

#### Error: "Runner.parallel(Class, int) method not found"
**Cause:** Karate 1.x changed the Runner API.
**Solution:** Use `Runner.path(String[]).parallel(int)` instead.

#### Error: "Feature file not found"
**Cause:** Using relative paths instead of classpath paths.
**Solution:** Change paths to use `classpath:` prefix.

---

## Appendix A: Quick Reference

### A.1 Command Cheat Sheet

```bash
# Compile tests (excluding API generation)
$GRADLE_CMD compileTestJava -x barclaysApiGenerate

# Run all tests (excluding API generation)
$GRADLE_CMD test -x barclaysApiGenerate

# Run specific test class
$GRADLE_CMD test --tests "*.AccountGatewayMockTest" -x barclaysApiGenerate

# Clean and rebuild
$GRADLE_CMD clean build -x barclaysApiGenerate

# View test report - open in a browser (path: build/reports/tests/test/index.html)
```

### A.2 Import Quick Reference

```java
// JUnit 5
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Disabled;

// JUnit 5 Test Suites
import org.junit.platform.suite.api.Suite;
import org.junit.platform.suite.api.SelectClasses;

// Spring Boot 3 Testing
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.boot.test.context.SpringBootTest;

// SDK3 Response API
import com.barclays.api.bap.bld.lib.common.response.Response;
import com.barclays.api.bap.bld.lib.payload.response.RestResponse;
import com.barclays.api.bap.bld.lib.payload.response.ResponseHttpStatus;

// SDK3 REST Client
import com.barclays.api.bap.bld.lib.restclient.RestApiClient;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import java.net.URI;

// Jackson for JSON
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

// Mockito
import org.mockito.BDDMockito;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
```

---

## 12. Mockito Checked Exception Constraints

### 12.1 The Problem

Mockito 5.x validates that exceptions passed to `willThrow()` are declared in the mocked method's `throws` clause. This causes `MockitoException: Checked exception is invalid for this method!` when the exception type doesn't match.

### 12.2 Diagnostic Workflow

When you see this error during Phase 5 test fixing:

1. **Find the willThrow() line** from the error message
2. **Find the interface** that declares the mocked method
3. **Read the throws clause** - only those exceptions are valid
4. **Change willThrow()** to use a declared exception

### 12.3 Exception Type Determination for assertThrows

After fixing the mock, you must also determine what `assertThrows` should expect. Read the implementation code:

```
Mock throws X → Implementation catches X → Rethrows as Y → assertThrows(Y.class)
```

| Mock Throws | If Caught By | Rethrown As | assertThrows Expects |
|-------------|-------------|-------------|---------------------|
| `UseCaseException` | `catch (UseCaseException)` | `ApiRequestException` | `ApiRequestException.class` |
| `RemoteException` | `catch (RemoteException)` | `ApiServerException` | `ApiServerException.class` |
| `ServiceException` | `catch (ServiceException)` | `ServerException` | `ServerException.class` |
| Any exception | Not caught (outside try-catch) | Propagates as-is | Original exception type |

### 12.4 SOAP/Axis Test Migration

For projects using Apache Axis 1.4 SOAP web services, see the dedicated reference:
- **[SOAP/Axis Test Migration Reference](soap_axis_test_migration.md)** - Complete patterns for JAX-RPC service tests, binding stubs, and SOAP client mocks

---

## 13. Testing Policy

### 13.1 Mocking Preference

Mocking is the preferred approach for all unit tests. Use `@MockitoBean` and `@MockitoSpyBean` for test isolation rather than integration-style tests that load real beans.

### 13.2 Coverage Target

All migrations must achieve **at least 90% line coverage**. After completing test migration, verify coverage with:

```bash
$GRADLE_CMD test jacocoTestReport -x barclaysApiGenerate
```

### 13.3 Bean Overriding

**Never enable bean overriding** (`spring.main.allow-bean-definition-overriding=true`) as a fix for `BeanDefinitionOverrideException`. Spring Boot 3 disables bean overriding by default for good reason - it catches real configuration problems.

If `BeanDefinitionOverrideException` occurs during tests:
1. Identify which beans conflict (the error message names them)
2. Check for duplicate `@Bean` definitions in test `@Configuration` classes
3. Use `@MockitoBean` instead of manually defining mock beans that override real ones
4. If a test `@Configuration` creates a bean that duplicates an application bean, remove the test one and use `@MockitoBean`

---

---

**END OF SPECIFICATION**
