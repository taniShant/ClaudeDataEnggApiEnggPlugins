---
name: sdk2-sdk3-migration
description: Complete migration guide for Barclays Internal API projects from SDK2 (Java 8, JUnit 4, Spring Boot 2) to SDK3 (Java 21, JUnit 5, Spring Boot 3). Covers build config, package mappings, REST client changes, test migration, and common patterns. Use when migrating any Barclays iAPI project from SDK2 to SDK3.
owner: Barclays AI (barclaysai@barclays.com)
version: 1.0.0
license: Proprietary. For Barclays internal use only.
user-invocable: false
source: barclays-claude-code-plugins/plugins/sdk3-migration/skills/sdk2_sdk3_migration/SKILL.md
owner: Barclays AI (barclaysai@barclays.com)
review-trigger: When SDK3 BOM versions change or new migration patterns are identified
status: Full
---

# SDK2 to SDK3 Migration Guide

## Overview

Migrate Barclays iAPI projects from SDK2 to SDK3:

- **Java 8 → Java 21** with modern toolchain configuration
- **Spring Boot 2.7.x → Spring Boot 3.x** (Jakarta EE migration)
- **JUnit 4 → JUnit 5** (Jupiter) for all tests
- **Gradle 7.x → Gradle 8.13** with new SDK3 plugin
- **Package restructuring** from `api.core.*` to `bap.bld.lib.*`
- **REST Client API changes** from `RestClient` to `RestApiClient`

## Before You Start

Before starting any SDK3 migration:
1. Run the [Pre-Migration Validation Checklist](reference/pre_migration_checklist.md) to validate project configuration
2. Report all validation findings to the user before proceeding with code changes
3. For library version lookups, see [Nexus Version Lookup](reference/nexus_version_lookup.md)

## Dependency Version Lookup

When looking up SDK3 versions for dependencies in `build.gradle`, use this routing:

| GroupId Pattern | Reference File |
|-----------------|----------------|
| `com.barclays.*` | [barclays_internal_libraries_versions.md](reference/barclays_internal_libraries_versions.md) + `barclays_internal_libraries_{group}.md` |
| `com.barclaycard.*` | [barclays_internal_libraries_versions.md](reference/barclays_internal_libraries_versions.md) + `barclays_internal_libraries_{group}.md` |
| `org.*`, `com.google.*`, `com.fasterxml.*`, etc. | [Third-Party Dependencies](reference/third_party_dependencies.md) |

**Quick Decision:**
- Barclays groupId (`com.barclays`, `com.barclaycard`) → `barclays_internal_libraries_versions.md` + `barclays_internal_libraries_{group}.md`
- Everything else (third-party) → `third_party_dependencies.md`

## Related Documentation

### Pre-Migration Validation (RUN FIRST)
- [Pre-Migration Checklist](reference/pre_migration_checklist.md) - **MANDATORY** validation checklist to run before starting migration

### Lessons Learned
- [Lessons Learned - AccountEntries iAPI](lessons_learnt/accountentries_iapi.md) - Critical patterns and common pitfalls
- [Lessons Learned - Cards API Project](lessons_learnt/cards_api.md) - Comprehensive cards covering Log4j, Spring Framework, Tomcat, Netty, Jakarta EE, Karate testing, and more
- [Lessons Learned - Quick Reference Cards](lessons_learnt/quick_reference.md) - Condensed problem/solution cards
- [Lessons Learned - Resilience4j Implementation](lessons_learnt/resilience4j.md) - Circuit breaker, bulkhead, and time limiter configuration
- [Lessons Learned - custpreapprvdlmt-iapi](lessons_learnt/custpreapprvdlmt_iapi.md) - Legacy groupId variants (`com.barclays.buk.imcc.buk`), transitive SDK2 libs, undocumented project-specific libs, api-mainframe-connector breaking change

### Library Version References
- [Barclays Internal Libraries — CAPL Group](reference/barclays_internal_libraries_capl.md) - CAPL-specific MODIFY rules (group-specific: `barclays_internal_libraries_{group}.md`)
- [Barclays Internal Libraries — Version Lookup](reference/barclays_internal_libraries_versions.md) - 600+ Barclays libraries with version mappings
- [Third-Party Dependencies](reference/third_party_dependencies.md) - External library versions (JUnit, Mockito, Spring, Jackson, etc.)

### Spring Best Practices (Optional)
- [Spring Conventions Skill](../spring-conventions/SKILL.md) - Constructor injection, Lombok, bean disambiguation, config class organization. Applied as Phase 0.5 during migration only if `--spring-conventions` is passed (skipped by default).

### Reference Documentation
- [SDK2 to SDK3 Package Mapping](reference/sdk2_to_sdk3_package_mapping.md) - Package import changes
- [Test Migration Specification](reference/test_migration_specification.md) - JUnit 4→5 core mappings (sections 1-9)
- [Test Migration — Errors & Advanced](reference/test_migration_errors_and_advanced.md) - Common errors, Karate, Mockito constraints, testing policy (sections 10-13)
- [SOAP/Axis Test Migration](reference/soap_axis_test_migration.md) - Apache Axis 1.4 SOAP test patterns
- [Joda to Java Time Migration](reference/joda-to-java-time-migration-spec.md) - Date/time migration patterns
- [H2 Test Database Config](reference/h2_test_database_config.md) - Datasource failure detection and H2 fallback
- [Checkstyle Fix Patterns](reference/checkstyle_fix_patterns.md) - Automated checkstyle error fixes
- [Nexus Version Lookup](reference/nexus_version_lookup.md) - Barclays Nexus repository search patterns
- [GitLab CI Template](reference/capl/gitlab_ci_template.yml) - Standard .gitlab-ci.yml for SDK3 CAPL projects

## Testing Policy

- **Mocking preferred** for all unit tests (`@MockitoBean` / `@MockitoSpyBean`)
- **Target 90% line coverage** and 90% mutation score
- **Never enable bean overriding** — fix root cause of `BeanDefinitionOverrideException`

## Quick Start

### 1. Update Build Configuration

**build.gradle - Critical Changes:**
** IMPORTANT **
- The content of build.gradle under buildSrc folder is really important with entries in settings.gradle - refer [sdk2_to_sdk3_migration_specification.md](reference/sdk2_to_sdk3_migration_specification.md)
- The content of build.gradle under root directory should have only SDK3 plugins (IMPORTANT DO NOT ADD ANYTHING ELSE)

```gradle
// 1. Update plugins
apply plugin: 'java'
apply plugin: 'com.barclays.api.bap-bld-lib-plugin'  // SDK3 plugin

// 2. Add repositories (Barclays Nexus only - mavenCentral() is BANNED per policy)
repositories {
    maven {
        url 'https://nexus.barcapint.com/nexus/content/groups/barclays/'
    }
}

// 3. Java 21 toolchain
java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}

// 4. Version overrides
ext['tomcat.version'] = '10.1.44'
ext['netty.version'] = '4.1.125.Final'
ext['spring-framework.version'] = '6.2.11'

// 5. SDK3 platform BOM
dependencies {
    implementation(platform("com.barclays.api:sdk3:${SDK3_VERSION}"))

    // SDK3 core libraries
    implementation 'com.barclays.api:bap-bld-lib-request-validator'
    implementation 'com.barclays.api:bap-bld-lib-restapi'
    implementation 'com.barclays.api:bap-bld-lib-meshconnector'
    implementation 'commons-io:commons-io:2.16.1'
}

// 6. JUnit 5 test dependencies
dependencies {
    testRuntimeOnly 'org.junit.platform:junit-platform-launcher'
    testImplementation 'org.junit.jupiter:junit-jupiter'
    testImplementation 'org.mockito:mockito-core:5.7.0'
    testImplementation 'org.mockito:mockito-junit-jupiter:5.7.0'
    testImplementation 'org.springframework.boot:spring-boot-starter-test'
}

// 7. Enable JUnit 5
tasks.named('test') {
    useJUnitPlatform()
}
```

**gradle.properties - Add SDK3 version:**

```properties
SDK3_VERSION=1.12.007  # Source of truth: barclays_internal_libraries_versions.md
GLOBAL_VERSION=1.1.2
```

**Update Gradle wrapper to 8.13:**

See `sdk2-sdk3-gradle` skill for detailed instructions on updating `gradle-wrapper.properties`.

Quick reference:
- Target: Gradle 8.13 from Barclays Nexus
- File: `gradle/wrapper/gradle-wrapper.properties`

### 2. Package Import Changes

**Find and replace across all .java files:**

```java
// Logging
com.barclays.api.core.logging → com.barclays.api.bap.bld.lib.logging

// Payload beans
com.barclays.api.core.web.beans.Request → com.barclays.api.bap.bld.lib.payload.beans.Request
com.barclays.api.core.web.beans.Resource → com.barclays.api.bap.bld.lib.payload.beans.Resource

// CoreHttpMessageConverter
com.barclays.api.core.web.CoreHttpMessageConverter → com.barclays.api.bap.bld.lib.payload.CoreHttpMessageConverter

// Response classes (IMPORTANT: Different packages!)
com.barclays.api.core.web.response.Response → com.barclays.api.bap.bld.lib.common.response.Response
com.barclays.api.core.web.response.Message → com.barclays.api.bap.bld.lib.payload.response.Message
com.barclays.api.core.web.response.MetaData → com.barclays.api.bap.bld.lib.payload.response.MetaData

// NEW in SDK3
import com.barclays.api.bap.bld.lib.payload.response.RestResponse;

// Exceptions
com.barclays.api.core.web.exceptions → com.barclays.api.bap.bld.lib.payload.exceptions

// REST Client (RENAMED)
com.barclays.api.core.web.util.RestClient → com.barclays.api.bap.bld.lib.restclient.RestApiClient

// SecureFields (MOVED to logging package)
com.barclays.api.core.web.beans.SecureField → com.barclays.api.bap.bld.lib.logging.beans.SecureField
```

### 3. Jakarta EE Migration

**Find and replace all javax imports:**

```java
javax.servlet       → jakarta.servlet
javax.persistence   → jakarta.persistence
javax.validation    → jakarta.validation
javax.annotation    → jakarta.annotation
javax.ws.rs         → jakarta.ws.rs
```

### 4. JUnit 4 → JUnit 5 Migration

**Update test imports:**

```java
// Test annotations
org.junit.Test              → org.junit.jupiter.api.Test
org.junit.Before            → org.junit.jupiter.api.BeforeEach
org.junit.After             → org.junit.jupiter.api.AfterEach
org.junit.Assert            → org.junit.jupiter.api.Assertions
org.junit.Ignore            → org.junit.jupiter.api.Disabled

// Spring Boot test mocks
org.springframework.boot.test.mock.mockito.MockBean →
    org.springframework.test.context.bean.override.mockito.MockitoBean
```

**Convert exception tests:**

```java
// BEFORE (JUnit 4)
@Test(expected = ApiRequestException.class)
public void testException() {
    service.callMethod();
}

// AFTER (JUnit 5)
@Test
public void testException() {
    Assertions.assertThrows(ApiRequestException.class, () -> {
        service.callMethod();
    });
}
```

## Core Migration Patterns

### Pattern 1: Building Responses

**SDK2:**
```java
import com.barclays.api.core.web.response.Response;

public Response buildResponse(Resource resource, MetaData meta) {
    return Response.assemble().addMetadata(meta).build(resource);
}
```

**SDK3:**
```java
import com.barclays.api.bap.bld.lib.common.response.Response;
import com.barclays.api.bap.bld.lib.payload.response.RestResponse;

public Response buildResponse(Resource resource, MetaData meta) {
    return RestResponse.assemble().addMetadata(meta).build(resource);
}
```

**Key Points:**
- Keep `Response` interface for return types
- Use `RestResponse.assemble()` for building (NOT `Response.assemble()`)

### Pattern 2: REST Client Calls

**SDK2:**
```java
@Autowired
private RestClient restClient;

Response response = restClient.callForResponse(
    URI.create(url),
    HttpMethod.GET,
    httpEntity
);

if (response.getHttpStatus() == HttpStatus.OK) {
    List<Resource<Data>> data = objectMapper.readValue(
        objectMapper.writeValueAsString(response.getData()),
        new TypeReference<List<Resource<Data>>>() {}
    );
}
```

**SDK3:**
```java
@Autowired
private RestApiClient restApiClient;

@Autowired
private ObjectMapper objectMapper;

// Step 1: Call API (returns ResponseEntity<String>)
ResponseEntity<String> responseEntity = restApiClient.call(
    HttpMethod.GET,
    URI.create(url),
    httpEntity.getHeaders(),
    String.class
);

// Step 2: Parse response body
String responseBody = responseEntity.getBody();
Response response = objectMapper.readValue(responseBody, RestResponse.class);

// Step 3: Check status
if (responseEntity.getStatusCode().is2xxSuccessful()) {
    List<Resource<Data>> data = objectMapper.readValue(
        objectMapper.writeValueAsString(response.getData()),
        new TypeReference<List<Resource<Data>>>() {}
    );
}
```

**Key Changes:**
- `RestClient` → `RestApiClient`
- `callForResponse()` → `call()`
- Returns `ResponseEntity<String>` (not `Response`)
- Must parse JSON manually with `ObjectMapper`
- Parameter order changed: method first, then URI

#### Pattern 2A: GET/DELETE (without request body)

Use **4-parameter** variant for requests without a body:

```java
ResponseEntity<String> responseEntity = restApiClient.call(
    HttpMethod.GET,              // 1. HTTP method
    URI.create(url),             // 2. URI
    headers,                     // 3. HttpHeaders
    String.class                 // 4. Response type
);
```

#### Pattern 2B: POST/PUT/PATCH (with request body)

Use **5-parameter** variant for requests WITH a body:

```java
ResponseEntity<String> responseEntity = restApiClient.call(
    HttpMethod.POST,             // 1. HTTP method
    URI.create(url),             // 2. URI
    requestBody,                 // 3. Request body (Object)
    headers,                     // 4. HttpHeaders
    String.class                 // 5. Response type
);
```

**CRITICAL**: POST/PUT/PATCH requests must use the 5-parameter variant with the request body. Using the 4-parameter variant will send requests without a body, causing silent failures.

**Example - POST with body:**
```java
CreateTransactionRequest request = new CreateTransactionRequest();
request.setAmount(100.00);

ResponseEntity<Void> responseEntity = restApiClient.call(
    HttpMethod.POST,
    URI.create(apiUrl + "/transactions"),
    request,                     // Request body - REQUIRED for POST!
    httpHeaders,
    Void.class
);
```

**Example - PATCH with body:**
```java
UpdateTransactionRequest request = new UpdateTransactionRequest();
request.setStatus("COMPLETED");

ResponseEntity<Void> responseEntity = restApiClient.call(
    HttpMethod.PATCH,
    URI.create(apiUrl + "/transactions/" + id),
    request,                     // Request body - REQUIRED for PATCH!
    httpHeaders,
    Void.class
);
```

#### Pattern 2C: Custom SSL Configuration with CoreRestApiClient

**When to Use:** Projects requiring custom SSL certificates (mutual TLS, custom truststores, certificate pinning).

**IMPORTANT:** The default `@Autowired RestApiClient` does NOT use custom SSL context. You must create a custom bean using `CoreRestApiClient`.

**SDK3 - Custom SSL Configuration:**
```java
import com.barclays.api.bap.bld.lib.common.request.RequestHandler;
import com.barclays.api.bap.bld.lib.common.response.ResponseHandler;
import com.barclays.api.bap.bld.lib.restclient.CoreRestApiClient;
import com.barclays.api.bap.bld.lib.restclient.RestApiClient;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.client5.http.impl.io.PoolingHttpClientConnectionManagerBuilder;
import org.apache.hc.client5.http.io.HttpClientConnectionManager;
import org.apache.hc.client5.http.ssl.NoopHostnameVerifier;
import org.apache.hc.client5.http.ssl.SSLConnectionSocketFactoryBuilder;
import org.springframework.http.client.ClientHttpRequestFactory;
import org.springframework.http.client.HttpComponentsClientHttpRequestFactory;
import org.springframework.web.client.DefaultResponseErrorHandler;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestTemplate;

@Configuration
public class SSLConfiguration {

    @Value("${ssl.truststore.path}")
    private String trustStorePath;

    @Value("${ssl.truststore.password}")
    private String trustStorePassword;

    @Value("${ssl.keystore.path}")
    private String keyStorePath;

    @Value("${ssl.keystore.password}")
    private String keyStorePassword;

    @Primary
    @Bean(name = "customRestClient")
    public RestApiClient restApiClient(
            RequestHandler requestHandler,
            ResponseHandler responseHandler) throws Exception {
        RestTemplate restTemplate = new RestTemplate(clientHttpRequestFactory());
        restTemplate.setErrorHandler(new DefaultResponseErrorHandler());
        return new CoreRestApiClient(
            RestClient.create(restTemplate),
            requestHandler,
            responseHandler
        );
    }

    @Bean
    public ClientHttpRequestFactory clientHttpRequestFactory() throws Exception {
        // Load SSL context with custom certificates
        SSLContext sslContext = new SSLContextBuilder()
            .loadTrustMaterial(new File(trustStorePath), trustStorePassword.toCharArray())
            .loadKeyMaterial(
                new File(keyStorePath),
                keyStorePassword.toCharArray(),
                keyStorePassword.toCharArray())
            .build();

        // Apache HttpClient 5 for Spring Boot 3.x
        HttpClientConnectionManager connectionManager =
            PoolingHttpClientConnectionManagerBuilder.create()
                .setSSLSocketFactory(SSLConnectionSocketFactoryBuilder.create()
                    .setSslContext(sslContext)
                    .setHostnameVerifier(NoopHostnameVerifier.INSTANCE)
                    .build())
                .build();

        CloseableHttpClient httpClient = HttpClients.custom()
            .setConnectionManager(connectionManager)
            .build();

        return new HttpComponentsClientHttpRequestFactory(httpClient);
    }
}
```

**Key Classes and Packages:**
| Class | Package |
|-------|---------|
| `RequestHandler` | `com.barclays.api.bap.bld.lib.common.request` |
| `ResponseHandler` | `com.barclays.api.bap.bld.lib.common.response` |
| `CoreRestApiClient` | `com.barclays.api.bap.bld.lib.restclient` |
| `RestApiClient` | `com.barclays.api.bap.bld.lib.restclient` |
| `RestClient` | `org.springframework.web.client` (Spring 6.1+) |

**Usage in Service Classes:**
```java
@Service
public class MyService {
    @Qualifier("customRestClient")
    @Autowired
    private RestApiClient restApiClient;

    @Autowired
    private ObjectMapper objectMapper;

    public MyResponse callApi(MyRequest request) throws Exception {
        ResponseEntity<String> responseEntity = restApiClient.call(
            HttpMethod.POST,
            URI.create(apiUrl),
            request,
            headers,
            String.class
        );

        String responseBody = responseEntity.getBody();
        if (responseBody != null && !responseBody.isEmpty()) {
            return objectMapper.readValue(responseBody, MyResponse.class);
        }
        return new MyResponse();
    }
}
```

**Apache HttpClient 5 Dependency (if not in SDK3 BOM):**
```gradle
implementation 'org.apache.httpcomponents.client5:httpclient5:5.3'
```

**IMPORTANT:** SDK2 uses Apache HttpClient 4.x, SDK3 requires Apache HttpClient 5.x. Class names and packages have changed:
- `org.apache.http.impl.client.*` → `org.apache.hc.client5.http.impl.classic.*`
- `org.apache.http.conn.ssl.*` → `org.apache.hc.client5.http.ssl.*`

### Pattern 3: Date/Time Migration

**SDK2 (Joda Time):**
```java
import org.joda.time.LocalDate;

LocalDate date = new LocalDate();
LocalDate converted = LocalDate.fromDateFields(javaUtilDate);
```

**SDK3 (java.time):**
```java
import java.time.LocalDate;
import java.time.ZoneId;

LocalDate date = LocalDate.now();
LocalDate converted = javaUtilDate.toInstant()
    .atZone(ZoneId.systemDefault())
    .toLocalDate();
```

### Pattern 4: Validation Utilities with RestResponse

**SDK2:**
```java
import com.barclays.api.core.web.response.Response;

public static void validateResponse(Response response, ...) {
    if (response.getHttpStatus().is4xxClientError()) {
        if (response.getErrors() != null) {
            // Handle errors
        }
    }
}
```

**SDK3:**
```java
import com.barclays.api.bap.bld.lib.payload.response.RestResponse;

public static void validateResponse(RestResponse response, ...) {
    if (response.getHttpStatus().is4xxClientError()) {
        if (response.getErrors() != null) {
            // Handle errors
        }
    }
}
```

**Why:** `getHttpStatus()` and `getErrors()` only exist on `RestResponse`, not `Response` interface.

### Pattern 5: Test Mocking for RestApiClient

**SDK2 Test:**
```java
@MockBean
RestClient restClient;

@Test
public void testSuccess() {
    BDDMockito.given(restClient.callForResponse(any(), any(), any()))
        .willReturn(getMockResponse());
}

private Response getMockResponse() {
    return Response.assemble().build(data);
}
```

**SDK3 Test:**
```java
@MockitoBean
RestApiClient restClient;

@Autowired
private ObjectMapper objectMapper;

@Test
public void testSuccess() throws Exception {
    BDDMockito.given(restClient.call(
        any(HttpMethod.class),
        any(URI.class),
        any(HttpHeaders.class),
        eq(String.class)
    )).willReturn(toResponseEntity(getMockResponse()));
}

// Helper method
private ResponseEntity<String> toResponseEntity(Response response)
        throws JsonProcessingException {
    String json = objectMapper.writeValueAsString(response);
    return ResponseEntity.ok(json);
}

private Response getMockResponse() {
    return RestResponse.assemble().build(data);
}
```

**Key Changes:**
- `@MockBean` → `@MockitoBean`
- Add `ObjectMapper` autowiring
- Use specific type matchers in `call()` mock
- Convert Response to `ResponseEntity<String>` via JSON

## Quick Reference

| Task | SDK2 | SDK3 | Notes |
|------|------|------|-------|
| **Java Version** | Java 8 | Java 21 | Update toolchain |
| **Gradle Version** | 7.x | 8.13+ | Use Barclays Nexus URL |
| **GitLab CI Image** | `BUILDER_IMAGE_JAVA_8_BUK` | `BUILDER_IMAGE_JAVA_21_BUK` | Update both `GLOBAL_JAVA_BUILDER_IMAGE` and `sonar_builder_image` |
| **Spring Boot** | 2.7.18 | 3.x | Jakarta EE migration |
| **JUnit** | JUnit 4 | JUnit 5 | Change all imports |
| **Build Response** | `Response.assemble()` | `RestResponse.assemble()` | Interface vs concrete |
| **REST Client** | `RestClient.callForResponse()` | `RestApiClient.call()` | Returns ResponseEntity |
| **Date/Time** | Joda Time | java.time | Update conversions |
| **Mock Annotation** | `@MockBean` | `@MockitoBean` | Spring Boot 3.4+ |
| **Test Exception** | `@Test(expected=...)` | `assertThrows(...)` | JUnit 5 pattern |
| **Servlet API** | `javax.servlet` | `jakarta.servlet` | All javax → jakarta |

## Common Pitfalls

### Pitfall 1: Response.assemble() Compilation Error

**Error:**
```
error: cannot find symbol: method assemble()
  symbol:   method assemble()
  location: interface Response
```

**Fix:** Use `RestResponse.assemble()` instead of `Response.assemble()`

### Pitfall 2: getHttpStatus() on Response Interface

**Error:**
```
error: cannot find symbol: method getHttpStatus()
  location: variable response of type Response
```

**Fix:** Change parameter/variable type from `Response` to `RestResponse`

### Pitfall 3: RestApiClient Mock Ambiguity

**Error:**
```
error: reference to call is ambiguous
```

**Fix:** Use specific type matchers:
```java
restClient.call(
    any(HttpMethod.class),    // Not just any()
    any(URI.class),
    any(HttpHeaders.class),
    eq(String.class)          // Very important!
)
```

### Pitfall 4: Test Suite Not Compiling

**Error:**
```
error: package org.junit.platform.suite.api does not exist
```

**Fix:** Add dependency:
```gradle
testImplementation 'org.junit.platform:junit-platform-suite-api:1.10.1'
```

### Pitfall 5: LocalDate.fromDateFields() Missing

**Error:**
```
error: cannot find symbol: method fromDateFields(Date)
```

**Fix:**
```java
date.toInstant().atZone(ZoneId.systemDefault()).toLocalDate()
```

## File Structure Changes

### Files to Remove:
```
gradle/common/  (entire directory — rm -rf gradle/common)
```
SDK3 does not use gradle/common at all. No files from this directory are carried forward.

### Files to Add:
```
buildSrc/build.gradle
settings.gradle
src/main/resources/application.properties
```

### Files to Modify:
```
build.gradle (major changes)
gradle.properties (add SDK3_VERSION, etc.)
.java-version (8 → 21)
gradle/wrapper/gradle-wrapper.properties (Gradle 8.13)
.gitlab-ci.yml (BUILDER_IMAGE_JAVA_8_BUK → BUILDER_IMAGE_JAVA_21_BUK, remove allow_failure from mandatory quality gates)
```

**GitLab CI update (MANDATORY — do not skip):**

```yaml
# Before (SDK2)
GLOBAL_JAVA_BUILDER_IMAGE: $BUILDER_IMAGE_JAVA_8_BUK
sonar_builder_image: $BUILDER_IMAGE_JAVA_8_BUK

# After (SDK3)
GLOBAL_JAVA_BUILDER_IMAGE: $BUILDER_IMAGE_JAVA_21_BUK
sonar_builder_image: $BUILDER_IMAGE_JAVA_21_BUK
```

Also remove `allow_failure: true` from mandatory quality gates (mutation test, component test, sonar, SBOM, veracode). Keep `allow_failure: true` only for `gradle-java-checkstyle`.

See [GitLab CI Template](reference/capl/gitlab_ci_template.yml) for the full reference.

## Running Tests

**Always exclude API generation task when testing:**

```bash
# Compile tests
$GRADLE_CMD compileTestJava -x barclaysApiGenerate

# Run tests
$GRADLE_CMD test -x barclaysApiGenerate

# Run specific test
$GRADLE_CMD test --tests "*.AccountGatewayMockTest" -x barclaysApiGenerate

# Full build
$GRADLE_CMD clean build -x barclaysApiGenerate
```

## Agent Self-Check

Before executing, verify:
- [ ] All required inputs are present
- [ ] Skill documentation has been loaded
- [ ] Scope boundary is understood — no out-of-scope changes
- [ ] Iron Rules (No Assumptions, Version Source of Truth) acknowledged
- [ ] Output format understood
