# Lessons Learned - PrepymtChk iAPI Project

**Project:** prepymtchk-iapi
**Migration:** SDK2 (api-bom 2.15.1.1) → SDK3 (1.11.015)
**Date:** January 2026

---

## Critical Lessons

### 1. HttpStatusCodeException Handling for 4xx/5xx Responses

**Issue:** SDK3's `RestApiClient.call()` throws `HttpStatusCodeException` for 4xx/5xx HTTP responses instead of returning them in the response object.

**SDK2 Behavior:**
```java
// SDK2: 4xx/5xx responses returned in Response object
Response response = restClient.callForResponse(uri, method, entity);
if (response.getHttpStatus() == HttpStatus.BAD_REQUEST) {
    // Handle 400 error - this worked in SDK2
}
```

**SDK3 Behavior:**
```java
// SDK3: 4xx/5xx responses THROW HttpStatusCodeException
try {
    ResponseEntity<String> responseEntity = restApiClient.call(
        HttpMethod.POST, uri, payload, headers, String.class
    );
    // This only executes for 2xx responses
    return parseSuccessResponse(responseEntity);

} catch (HttpStatusCodeException httpEx) {
    // SDK3: 4xx/5xx responses caught here
    return parseErrorResponse(httpEx);
}
```

**Why This Matters:**
- Tests expecting specific 4xx status codes (400, 401, 403, 404) may fail with 500 if you don't handle `HttpStatusCodeException`
- Generic `catch (Exception e)` will catch the HTTP error and convert it to 500 Internal Server Error
- You must explicitly catch `HttpStatusCodeException` before generic exceptions

**Complete Pattern:**
```java
public RestResponse consumeApiWithPayload(String url, HttpMethod method,
        Map<String, String> requestHeaders, Object payload) {

    HttpHeaders headers = buildHeaders(requestHeaders);
    URI uri = UriComponentsBuilder.fromHttpUrl(url).build().toUri();

    try {
        ResponseEntity<String> responseEntity = restApiClient.call(
            method, uri, payload, headers, String.class
        );
        return parseSuccessResponse(responseEntity);

    } catch (HttpStatusCodeException httpEx) {
        // SDK3: Handle 4xx/5xx HTTP errors - parse error response body
        logger.error("API returned error: {}", httpEx.getStatusCode());
        return parseErrorResponse(httpEx);

    } catch (Exception ex) {
        // Network errors, parsing errors, etc.
        logger.error("Unexpected error calling API", ex);
        throw new ServiceException(MessageConstants.UNEXPECTED_ERROR,
            ResponseHttpStatus.INTERNAL_SERVER_ERROR);
    }
}

private RestResponse parseErrorResponse(HttpStatusCodeException httpEx) {
    try {
        String errorBody = httpEx.getResponseBodyAsString();
        HttpStatus errorStatus = HttpStatus.valueOf(httpEx.getStatusCode().value());

        if (errorBody != null && !errorBody.isEmpty()) {
            RestResponse response = objectMapper.readValue(errorBody, RestResponse.class);
            response.setHttpStatus(errorStatus);  // Critical: set status from exception
            return response;
        } else {
            return RestResponse.empty(errorStatus);
        }
    } catch (Exception ex) {
        HttpStatus errorStatus = HttpStatus.valueOf(httpEx.getStatusCode().value());
        return RestResponse.empty(errorStatus);
    }
}
```

**Required Import:**
```java
import org.springframework.web.client.HttpStatusCodeException;
```

---

### 2. Always Set httpStatus on RestResponse After JSON Parsing

**Issue:** When parsing JSON response body to `RestResponse`, the `httpStatus` field is null because it's not included in the JSON payload from downstream APIs.

**Problem:**
```java
// ❌ WRONG - httpStatus will be null
String responseBody = responseEntity.getBody();
RestResponse response = objectMapper.readValue(responseBody, RestResponse.class);

// response.getHttpStatus() returns NULL here!
if (response.getHttpStatus() == HttpStatus.OK) {  // NullPointerException!
```

**Solution:**
```java
// ✅ CORRECT - Always set httpStatus from ResponseEntity
String responseBody = responseEntity.getBody();
RestResponse response = objectMapper.readValue(responseBody, RestResponse.class);

// Set httpStatus from the actual HTTP response
HttpStatus httpStatus = HttpStatus.valueOf(responseEntity.getStatusCode().value());
response.setHttpStatus(httpStatus);

// Now safe to use
if (response.getHttpStatus() == HttpStatus.OK) {
    // Works correctly
}
```

**Why This Matters:**
- JSON response bodies from APIs typically don't include HTTP status
- RestResponse deserialization leaves httpStatus as null
- Downstream validators using `response.getHttpStatus()` will fail with NullPointerException
- This applies to both success and error responses

---

### 3. ObjectMapper Must Be Reused (Static or Injected)

**Issue:** Creating new `ObjectMapper` instances per request is expensive and wasteful.

**Problem:**
```java
// ❌ WRONG - Creates new ObjectMapper for each request
public void validateResponse(RestResponse response) {
    try {
        ObjectMapper mapper = new ObjectMapper();  // Expensive!
        String json = mapper.writeValueAsString(response.getErrors());
        logger.error("Errors: " + json);
    } catch (Exception e) {
        // ...
    }
}
```

**Solution:**
```java
// ✅ CORRECT - Reuse ObjectMapper (it's thread-safe)
public class ResponseValidator {

    // Static constant for utility classes
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    public void validateResponse(RestResponse response) {
        try {
            String json = OBJECT_MAPPER.writeValueAsString(response.getErrors());
            logger.error("Errors: " + json);
        } catch (Exception e) {
            // ...
        }
    }
}

// OR inject via Spring for service classes
@Component
public class GatewayClient {

    @Autowired
    private ObjectMapper objectMapper;  // Spring-managed singleton

    // Use injected objectMapper
}
```

**Why This Matters:**
- ObjectMapper initialization is expensive (reflection, cache building)
- ObjectMapper is thread-safe and designed for reuse
- Creating per-request instances causes unnecessary GC pressure
- Spring Boot auto-configures a singleton ObjectMapper bean

---

### 4. Unused Dependencies to Remove After SDK3 Migration

**Issue:** Several SDK2-era dependencies are no longer needed in SDK3 projects.

**Common Unused Dependencies:**

| Dependency | Reason to Remove |
|------------|------------------|
| `com.rabbitmq:amqp-client` | Only if not using RabbitMQ messaging |
| `jackson-datatype-jsr310` | Only needed if using java.time types in JSON beans |
| `json-schema-validator` | Only if not validating JSON schemas |
| `spring-boot-starter-cache` | Only if no `@Cacheable`/`@EnableCaching` annotations |
| `assertj-core` | Only if not using AssertJ assertions in tests |
| `junit-platform-suite-api` | Only if not using `@Suite` annotation |
| `htmlunit-core-js` | Often transitive, rarely directly used |
| `neko-htmlunit` | Often transitive, rarely directly used |

**Detection Script:**
```bash
# Check for unused imports in main source
for dep in "rabbitmq" "jsr310" "json-schema" "assertj" "htmlunit"; do
    echo "=== $dep ==="
    grep -r "import.*$dep" src/main --include="*.java" | wc -l
done

# Check for cache annotations
grep -rE "@Cacheable|@CacheEvict|@EnableCaching" src/main --include="*.java"
```

**Scope Corrections:**
```gradle
// Move test-only dependencies to testImplementation
// ❌ WRONG
implementation 'commons-io:commons-io:2.16.1'

// ✅ CORRECT (if only used in tests)
testImplementation 'commons-io:commons-io:2.16.1'
```

**Why This Matters:**
- Reduces JAR size and startup time
- Avoids potential version conflicts
- Clearer dependency tree for maintenance
- Faster builds

---

### 5. GitLab Branch and Commit Message Patterns

**Issue:** GitLab repositories may enforce branch naming and commit message patterns.

**Branch Naming Pattern:**
```bash
# ❌ WRONG - GitLab rejects 'feat/' prefix
feat/ELECPAYAPI-3638/sdk3-migration

# ✅ CORRECT - Use 'feature/' prefix
feature/ELECPAYAPI-3638/sdk3-migration
```

**Pattern:** `(feature|release|hotfix|develop)/*`

**Commit Message Pattern:**
```bash
# ❌ WRONG - Missing JIRA prefix
Phase 1: Complete Gradle 8.13 and SDK3 build configuration

# ✅ CORRECT - Starts with JIRA ID
ELECPAYAPI-3638 Phase 1: Complete Gradle 8.13 and SDK3 build configuration
```

**Pattern:** `(ELECPAYAPI-|CURSAVAPI-|UNSECLAPI-)*`

**Fix for Multiple Commits:**
```bash
# Squash multiple commits into one with proper prefix
git reset --soft master
git commit -m "ELECPAYAPI-3638 Complete SDK3 migration

- Phase 1: Gradle 8.13 configuration
- Phase 2: Java imports migration
- Phase 3: Test fixes

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Why This Matters:**
- GitLab pre-receive hooks reject non-compliant branches/commits
- CI/CD pipelines may fail without proper JIRA linking
- Traceability requires consistent naming conventions

---

### 6. Test Behavior Changes: ResourceAccessException vs HTTP 500

**Issue:** Tests expecting `ResourceAccessException` for connection failures may need updating for SDK3.

**SDK2 Test Pattern:**
```java
// SDK2: Invalid URL throws ResourceAccessException
@Test(expected = ResourceAccessException.class)
public void testInvalidUrlThrowsException() {
    ReflectionTestUtils.setField(gateway, "apiUrl", "invalidUrl");
    service.callDownstreamApi(request);
}
```

**SDK3 Test Pattern:**
```java
// SDK3: Invalid URL caught and converted to HTTP 500
@Test
public void testInvalidUrlReturns500() {
    ReflectionTestUtils.setField(gateway, "apiUrl", "invalidUrl");

    ResponseEntity<String> response = restTemplate.exchange(
        endpoint, HttpMethod.POST,
        new HttpEntity<>(request, headers),
        String.class
    );

    assertEquals(500, response.getStatusCodeValue());
}
```

**Why This Matters:**
- SDK3's exception handling may convert low-level exceptions to HTTP responses
- Tests expecting specific exception types may fail
- Validate whether test expectations match actual SDK3 behavior

---

### 7. Null Response Body Handling in RestApiClient

**Issue:** `RestApiClient.call()` can return a `ResponseEntity` with a null body, causing `NullPointerException` when parsing with `ObjectMapper`.

**Problem:**
```java
// ❌ WRONG - Assumes body is never null
ResponseEntity<String> responseEntity = restApiClient.call(
    method, uri, payload, headers, String.class
);
String responseBody = responseEntity.getBody();
RestResponse response = objectMapper.readValue(responseBody, RestResponse.class);  // NPE if body is null!
```

**Solution:**
```java
// ✅ CORRECT - Check for null/empty body before parsing
ResponseEntity<String> responseEntity = restApiClient.call(
    method, uri, payload, headers, String.class
);

String responseBody = responseEntity.getBody();
RestResponse response;

if (responseBody != null && !responseBody.isEmpty()) {
    response = objectMapper.readValue(responseBody, RestResponse.class);
} else {
    response = new RestResponse();
}

// Always set httpStatus from actual HTTP response
response.setHttpStatus(HttpStatus.valueOf(responseEntity.getStatusCode().value()));
```

**Why This Matters:**
- Some APIs return 200/204 responses with empty body
- Network issues may result in incomplete responses
- Defensive coding prevents unexpected NPEs in production

---

### 8. Java 21 Module System Access for Tests (--add-opens)

**Issue:** Java 21's module system blocks reflection access required by Spring Boot, Mockito, and Groovy in tests.

**Error Pattern:**
```
java.lang.reflect.InaccessibleObjectException: Unable to make field private final byte[] java.lang.String.value accessible:
module java.base does not "opens java.lang" to unnamed module
```

**Solution - Gradle:**
```gradle
tasks.named('test') {
    useJUnitPlatform()
    jvmArgs = [
        '--add-opens', 'java.base/java.lang=ALL-UNNAMED',
        '--add-opens', 'java.base/java.lang.reflect=ALL-UNNAMED',
        '--add-opens', 'java.base/java.util=ALL-UNNAMED',
        '--add-opens', 'java.base/java.io=ALL-UNNAMED'
    ]
}

// Also add to integration tests if applicable
task integrationTest(type: Test) {
    useJUnitPlatform()
    jvmArgs = [
        '--add-opens', 'java.base/java.lang=ALL-UNNAMED',
        '--add-opens', 'java.base/java.lang.reflect=ALL-UNNAMED',
        '--add-opens', 'java.base/java.util=ALL-UNNAMED',
        '--add-opens', 'java.base/java.io=ALL-UNNAMED'
    ]
}
```

**Solution - Maven:**
```xml
<build>
    <plugins>
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-surefire-plugin</artifactId>
            <version>3.2.5</version>
            <configuration>
                <argLine>
                    --add-opens java.base/java.lang=ALL-UNNAMED
                    --add-opens java.base/java.lang.reflect=ALL-UNNAMED
                    --add-opens java.base/java.util=ALL-UNNAMED
                    --add-opens java.base/java.io=ALL-UNNAMED
                </argLine>
            </configuration>
        </plugin>
        <!-- For integration tests -->
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-failsafe-plugin</artifactId>
            <version>3.2.5</version>
            <configuration>
                <argLine>
                    --add-opens java.base/java.lang=ALL-UNNAMED
                    --add-opens java.base/java.lang.reflect=ALL-UNNAMED
                    --add-opens java.base/java.util=ALL-UNNAMED
                    --add-opens java.base/java.io=ALL-UNNAMED
                </argLine>
            </configuration>
        </plugin>
    </plugins>
</build>
```

**Why This Matters:**
- Java 9+ module system (JPMS) enforces strong encapsulation
- Testing frameworks use reflection extensively
- Without these flags, tests fail with InaccessibleObjectException
- Must be set in Phase 1 (build config) to avoid surprises in Phase 4 (tests)

---

### 9. Mockito 5.x Strict Stubbing - @MockitoSettings(strictness = LENIENT)

**Issue:** Mockito 5.x uses strict stubbing by default, which fails tests with unused stubs.

**Error Pattern:**
```
org.mockito.exceptions.misusing.UnnecessaryStubbingException:
Unnecessary stubbings detected.
Clean & maintainable test code requires zero unnecessary code.
Following stubbings are unnecessary (click to navigate to relevant line of code):
  1. -> at com.example.TestClass.setUp(TestClass.java:45)
```

**Problem:** Test setup creates mocks for multiple scenarios, but individual tests only use some of them.

**Solution - Per Test Class:**
```java
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;

@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
public class MyServiceTest {

    @Mock
    private RestApiClient restApiClient;

    @BeforeEach
    void setUp() {
        // Setup stubs that may not all be used in every test
        when(restApiClient.call(any(), any(), any(), any()))
            .thenReturn(ResponseEntity.ok("{}"));
    }

    @Test
    void testScenarioA() {
        // Uses the stub
    }

    @Test
    void testScenarioB() {
        // May not use the stub - LENIENT mode prevents failure
    }
}
```

**Solution - Per Mock (More Targeted):**
```java
@Mock(strictness = Mock.Strictness.LENIENT)
private RestApiClient restApiClient;
```

**Why This Matters:**
- Mockito 5.x default changed from LENIENT to STRICT_STUBS
- Helps identify dead code in tests, but can be overly strict during migration
- Use LENIENT temporarily during migration, then tighten after stabilization
- SDK2 tests may have legacy setup patterns that trigger this

---

### 10. Test Profile Properties for SDK3 Request Validator

**Issue:** SDK3's request validator throws "Invalid Swagger or Path" errors when it cannot find API spec files during tests.

**Error Pattern:**
```
com.barclays.api.bap.bld.lib.requestvalidator.exception.RequestValidatorException:
Invalid Swagger or Path : /some/api/endpoint
```

**Solution:** Create test profile to disable request validation during tests.

**Create `src/test/resources/application-wiremock.properties`:**
```properties
# Disable SDK3 request validation for tests
requestValidation.isRequired=false
ramlRequestValidation.isRamlOnClasspath=false
api.spec.validation.enabled=false
```

**Activate Profile in Tests - Annotation:**
```java
@SpringBootTest
@ActiveProfiles("wiremock")
public class MyIntegrationTest {
    // Tests run with validation disabled
}
```

**Activate Profile in Tests - Gradle:**
```gradle
tasks.named('test') {
    useJUnitPlatform()
    systemProperty 'spring.profiles.active', 'wiremock'
}
```

**Activate Profile in Tests - Maven:**
```xml
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-surefire-plugin</artifactId>
    <configuration>
        <systemPropertyVariables>
            <spring.profiles.active>wiremock</spring.profiles.active>
        </systemPropertyVariables>
    </configuration>
</plugin>
```

**Why This Matters:**
- SDK3 includes request validation that verifies API calls match OpenAPI/RAML specs
- Tests often use mock endpoints not defined in specs
- Validation must be disabled in test context to avoid false failures
- Create in Phase 1 (build config) as pre-flight setup

---

### 11. Karate Test Migration (JUnit 4 → JUnit 5)

**Issue:** Old Karate versions (0.9.x) use JUnit 4 and are not compatible with Java 21.

**SDK2 Pattern:**
```java
import com.intuit.karate.junit4.Karate;
import org.junit.runner.RunWith;

@RunWith(Karate.class)
@KarateOptions(features = {"src/test/resources/features/mytest.feature"})
public class KarateTestRunner {
}
```

**Gradle Dependencies - Old:**
```gradle
testImplementation 'com.intuit.karate:karate-junit4:0.9.6'
testImplementation 'com.intuit.karate:karate-apache:0.9.6'
```

**SDK3 Pattern:**
```java
import com.intuit.karate.junit5.Karate;

public class KarateTestRunner {

    @Karate.Test
    Karate testAll() {
        return Karate.run("mytest").relativeTo(getClass());
    }
}
```

**Gradle Dependencies - New:**
```gradle
testImplementation 'com.intuit.karate:karate-junit5:1.4.1'
```

**Maven Dependencies - New:**
```xml
<dependency>
    <groupId>com.intuit.karate</groupId>
    <artifactId>karate-junit5</artifactId>
    <version>1.4.1</version>
    <scope>test</scope>
</dependency>
```

**Migration Notes:**
- Karate 0.9.x is NOT compatible with Java 21
- Karate 1.4.x uses JUnit 5 Jupiter
- Feature file syntax remains largely compatible
- `@RunWith(Karate.class)` replaced with `@Karate.Test` method annotation

---

### 12. Compile Validation Commands Per Phase

**Issue:** Migration errors cascade if not caught early. Each phase requires specific compile validation.

**Phase Validation - Gradle:**
```bash
# Phase 1 (Build Config) - Verify dependencies resolve
./gradlew dependencies --configuration implementation -x barclaysApiGenerate

# Phase 2 (Packages) - Verify main code compiles
./gradlew compileJava -x barclaysApiGenerate

# Phase 3 (REST Client) - Verify main code still compiles
./gradlew compileJava -x barclaysApiGenerate

# Phase 4 (Tests) - Verify test code compiles
./gradlew compileTestJava -x barclaysApiGenerate

# Phase 5 (Final) - Run all tests
./gradlew test -x barclaysApiGenerate -x jacocoTestCoverageVerification
```

**Phase Validation - Maven:**
```bash
# Phase 1 (Build Config) - Verify dependencies resolve
mvn dependency:tree -DskipTests

# Phase 2 (Packages) - Verify main code compiles
mvn compile -DskipTests

# Phase 3 (REST Client) - Verify main code still compiles
mvn compile -DskipTests

# Phase 4 (Tests) - Verify test code compiles
mvn test-compile -DskipTests

# Phase 5 (Final) - Run all tests
mvn test -Djacoco.skip=true
```

**Why This Matters:**
- Catching errors early prevents cascading failures
- Each phase has different compile scope (main vs test)
- Skip API generation and coverage verification during migration
- Validation gates ensure clean handoff between phases

---

## Summary

Key differences from SDK2 to SDK3 discovered in prepymtchk-iapi migration:

1. **HttpStatusCodeException** - SDK3 throws exceptions for 4xx/5xx, must catch explicitly
2. **httpStatus on RestResponse** - Always set from ResponseEntity after JSON parsing
3. **ObjectMapper reuse** - Use static constant or injected bean, never create per-request
4. **Dependency cleanup** - Remove unused SDK2-era dependencies
5. **GitLab patterns** - Use `feature/` prefix, JIRA ID in commit messages
6. **Test expectations** - May need to change from exception to HTTP status assertions
7. **Null response body** - Check for null before ObjectMapper.readValue()
8. **Java 21 module opens** - Add --add-opens JVM args for test tasks
9. **Mockito strict stubbing** - Use @MockitoSettings(strictness = LENIENT) if needed
10. **Request validator in tests** - Create application-wiremock.properties to disable
11. **Karate migration** - Upgrade to karate-junit5:1.4.1 for Java 21 compatibility
12. **Phase validation commands** - Run specific compile checks after each migration phase

---

**Document Version:** 2.0
**Date:** 2026-01-16
**Migration Team:** SDK3 Migration
