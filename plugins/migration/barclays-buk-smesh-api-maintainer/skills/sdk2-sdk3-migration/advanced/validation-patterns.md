# SDK2 to SDK3 Migration - 18 Red Flags and Validation Patterns

**Purpose**: Domain-specific hallucination patterns, red flags, and validation checklists for SDK2 to SDK3 migration validation.

**For Use With**: sdk2-to-sdk3-validation-agent

**Version**: 2.1
**Last Updated**: 2026-04-21

---

## Overview

This document contains specific patterns, red flags, and checklists for validating SDK2 to SDK3 migration code. These patterns are used by the sdk2-to-sdk3-validation-agent to detect common hallucinations and errors specific to Barclays Internal API migration work.

## The 18 Red Flags

These are the most common hallucination patterns in SDK2 to SDK3 migrations:

### Red Flag 1: Simplified Package Names

**Problem**: LLMs often simplify long package paths, omitting critical segments.

**HALLUCINATION:**
```java
import com.barclays.api.response.Response;
import com.barclays.sdk3.core.RestResponse;
import com.barclays.api.client.RestApiClient;
```

**SKILL-DOCUMENTED** (SKILL.md, Section "Package Import Changes"):
```java
import com.barclays.api.bap.bld.lib.common.response.Response;
import com.barclays.api.bap.bld.lib.payload.response.RestResponse;
import com.barclays.api.bap.bld.lib.restapi.client.RestApiClient;
```

**Why It Matters**:
- Missing `.bap.bld.lib` segments causes compilation failures
- Package structure changed fundamentally in SDK3
- No shortcuts or abbreviations are valid

**How to Detect**:
- Count segments: SDK3 packages have `com.barclays.api.bap.bld.lib.*`
- Any package starting with `com.barclays.api.` but missing `.bap.bld.lib` is wrong
- Look for invented middle segments like `sdk3.core` or `client` without full path

---

### Red Flag 2: Invented REST Client Method Signatures

**Problem**: LLMs invent plausible-sounding but non-existent REST client methods.

**HALLUCINATION:**
```java
// Invented method names
Response response = restApiClient.execute(url, method);
ResponseEntity<Object> result = restApiClient.callApi(uri, body);
String data = restApiClient.get(url);
Response resp = restApiClient.invoke(endpoint, headers);
```

**SKILL-DOCUMENTED** (SKILL.md, Pattern 2: REST Client Calls):
```java
// Only valid SDK3 method is: call()
ResponseEntity<String> responseEntity = restApiClient.call(
    HttpMethod.GET,
    URI.create(url),
    headers,
    String.class
);
```

**Why It Matters**:
- SDK3 has ONE method: `call()`
- All other method names are hallucinations
- Parameter order is specific: HttpMethod FIRST, then URI

**How to Detect**:
- Any method name other than `call()` is wrong
- Methods like `execute()`, `callApi()`, `get()`, `post()`, `invoke()` don't exist
- Check SKILL.md Pattern 2 for exact signature

---

### Red Flag 3: Mixed JUnit Versions

**Problem**: LLMs mix JUnit 4 and JUnit 5 imports or annotations.

**HALLUCINATION** (mixing JUnit 4 and 5):
```java
import org.junit.Test;  // JUnit 4
import org.junit.jupiter.api.Assertions;  // JUnit 5
import org.junit.Before;  // JUnit 4

public class MyTest {
    @Before  // JUnit 4
    public void setup() { }

    @Test  // JUnit 4
    public void testSomething() {
        Assertions.assertEquals(1, 1);  // JUnit 5
    }
}
```

**SKILL-DOCUMENTED** (SKILL.md, Section "JUnit 4 to JUnit 5 Migration"):
```java
import org.junit.jupiter.api.Test;  // JUnit 5
import org.junit.jupiter.api.BeforeEach;  // JUnit 5
import org.junit.jupiter.api.Assertions;  // JUnit 5

public class MyTest {
    @BeforeEach  // JUnit 5
    void setup() { }

    @Test  // JUnit 5
    void testSomething() {
        Assertions.assertEquals(1, 1);
    }
}
```

**Why It Matters**:
- JUnit 4 and 5 are incompatible
- Mixing causes classpath conflicts and test failures
- SDK3 requires pure JUnit 5

**How to Detect**:
- Check imports: `org.junit.*` is JUnit 4, `org.junit.jupiter.api.*` is JUnit 5
- Check annotations: `@Before/@After/@BeforeClass/@AfterClass` are JUnit 4
- JUnit 5 uses: `@BeforeEach/@AfterEach/@BeforeAll/@AfterAll`
- JUnit 4 `@Test(expected=...)` vs JUnit 5 `assertThrows()`

**Complete Annotation Mapping**:
| JUnit 4 | JUnit 5 |
|---------|---------|
| @Before | @BeforeEach |
| @After | @AfterEach |
| @BeforeClass | @BeforeAll |
| @AfterClass | @AfterAll |
| @Ignore | @Disabled |
| @Test(expected=X.class) | assertThrows(X.class, ...) |
| @RunWith(SpringRunner.class) | @ExtendWith(SpringExtension.class) |

---

### Red Flag 4: Invented Gradle Configuration

**Problem**: LLMs invent plausible but incorrect Gradle plugin IDs and dependency names.

**HALLUCINATION:**
```gradle
// Invented plugin IDs
apply plugin: 'com.barclays.sdk3-plugin'
apply plugin: 'barclays-api-plugin'
apply plugin: 'sdk3-migration'

// Invented dependency names
implementation 'com.barclays.api:sdk3-core'
implementation 'com.barclays:bld-lib'
implementation 'com.barclays.api:rest-client-sdk3'
```

**SKILL-DOCUMENTED** (SKILL.md, Quick Start, Step 1):
```gradle
// Correct plugin ID
apply plugin: 'com.barclays.api.bap-bld-lib-plugin'

// Correct dependencies
implementation 'com.barclays.api:bap-bld-lib-request-validator'
implementation 'com.barclays.api:bap-bld-lib-restapi'
implementation 'com.barclays.api:bap-bld-lib-meshconnector'
```

**Why It Matters**:
- Wrong plugin IDs cause build failures
- Dependency names must match exactly for resolution
- No shortcuts or simplified names exist

**How to Detect**:
- Plugin must be exactly: `com.barclays.api.bap-bld-lib-plugin`
- All dependencies start with: `com.barclays.api:bap-bld-lib-*`
- Look for invented suffixes like `-sdk3`, `-core`, or simplified names

---

### Red Flag 5: Wrong Response Builder Pattern

**Problem**: Using SDK2 Response.assemble() pattern in SDK3 code.

**HALLUCINATION** (SDK2 pattern in SDK3):
```java
public Response buildResponse(Object resource) {
    return Response.assemble().build(resource);  // WRONG! Response is interface
}
```

**SKILL-DOCUMENTED** (SKILL.md, Pattern 1: Building Responses):
```java
public Response buildResponse(Object resource) {
    return RestResponse.assemble().build(resource);  // CORRECT! RestResponse is concrete class
}
```

**Why It Matters**:
- `Response` is an INTERFACE in SDK3 - it has no `assemble()` method
- `RestResponse` is a CONCRETE CLASS - it has the `assemble()` builder
- This is SKILL.md Common Pitfall #1

**How to Detect**:
- `Response.assemble()` is always wrong in SDK3
- Must use `RestResponse.assemble()`
- Service return types use `Response` interface
- Service implementations use `RestResponse.assemble()` for building

---

### Red Flag 6: Standard Gradle Distribution URL

**Problem**: Using public Gradle distribution instead of Barclays Nexus.

**HALLUCINATION:**
```properties
# gradle/wrapper/gradle-wrapper.properties
distributionUrl=https://services.gradle.org/distributions/gradle-8.13-bin.zip
```

**SKILL-DOCUMENTED** (SKILL.md, Quick Start, Step 1):
```properties
# gradle/wrapper/gradle-wrapper.properties
distributionUrl=https://nexus.barcapint.com/nexus/content/groups/barclays/gradle-8.13-bin.zip
```

**Why It Matters**:
- Barclays network blocks public Gradle downloads
- Must use internal Nexus repository
- Build will fail without correct URL

**How to Detect**:
- Any URL with `services.gradle.org` is wrong
- Must use `nexus.barcapint.com`
- SKILL.md Common Pitfall #4

---

### Red Flag 7: Wrong Parameter Order in RestApiClient

**Problem**: SDK3 changed parameter order - HttpMethod comes FIRST now.

**HALLUCINATION** (SDK2 or wrong parameter order):
```java
// Wrong: URI first (SDK2 style)
restApiClient.call(URI.create(url), HttpMethod.GET, headers, String.class)

// Wrong: Different order
restApiClient.call(headers, HttpMethod.GET, URI.create(url), String.class)
```

**SKILL-DOCUMENTED** (SKILL.md, Pattern 2: REST Client Calls):
```java
// Correct: HttpMethod FIRST, then URI
restApiClient.call(HttpMethod.GET, URI.create(url), headers, String.class)
```

**Why It Matters**:
- Parameter order changed from SDK2 to SDK3
- Wrong order causes compilation error
- HttpMethod must come FIRST

**How to Detect**:
- First parameter must be `HttpMethod.XXX`
- Second parameter must be `URI` type
- Third parameter is headers
- Fourth parameter is response class type

**SDK2 vs SDK3 Comparison**:
```java
// SDK2 (OLD - don't use):
restClient.callForResponse(uri, method, httpEntity)

// SDK3 (NEW - correct):
restApiClient.call(method, uri, headers, String.class)
```

---

### Red Flag 8: Using Response Interface for Status/Error Methods

**Problem**: Using `Response` type when code needs `getHttpStatus()` or `getErrors()`.

**HALLUCINATION** (wrong type):
```java
public void validateResponse(Response response) {
    if (response.getHttpStatus().is4xxClientError()) {  // Compilation error!
        // getHttpStatus() is NOT in Response interface
    }

    List<Error> errors = response.getErrors();  // Also compilation error!
}
```

**SKILL-DOCUMENTED** (SKILL.md, Pattern 4: Validation Utilities):
```java
public void validateResponse(RestResponse response) {
    if (response.getHttpStatus().is4xxClientError()) {  // Works!
        // getHttpStatus() IS in RestResponse
    }

    List<Error> errors = response.getErrors();  // Works!
}
```

**Why It Matters**:
- `Response` interface only has `getData()` methods
- `RestResponse` has status and error access methods
- Using wrong type causes compilation failure

**How to Detect**:
- If code calls `getHttpStatus()`, type must be `RestResponse`
- If code calls `getErrors()`, type must be `RestResponse`
- Service return types use `Response` (interface)
- Gateway variables for validation use `RestResponse` (concrete)

**When to Use Which**:
```java
// Service layer - return interface
public Response getUser(String id) {
    return RestResponse.assemble().build(userData);
}

// Gateway layer - use concrete for validation
RestResponse response = (RestResponse) service.getUser(id);
if (response.getHttpStatus().is2xxSuccessful()) {
    // validation logic
}
```

---

### Red Flag 9: POST/PUT/PATCH Without Request Body

**Problem**: Using 4-parameter `call()` for POST/PUT/PATCH which omits the request body.

**HALLUCINATION** (4 parameters - missing body):
```java
// WRONG: POST without request body
ResponseEntity<Void> response = restApiClient.call(
    HttpMethod.POST,
    URI.create(url),
    headers,              // This is headers, NOT body!
    Void.class
);

// WRONG: PATCH without request body
ResponseEntity<Void> response = restApiClient.call(
    HttpMethod.PATCH,
    URI.create(url),
    headers,
    Void.class
);
```

**SKILL-DOCUMENTED** (SKILL.md, Pattern 2B: POST/PUT/PATCH with body):
```java
// CORRECT: POST with request body (5 parameters)
ResponseEntity<Void> response = restApiClient.call(
    HttpMethod.POST,
    URI.create(url),
    requestBody,          // Request body - REQUIRED!
    headers,
    Void.class
);

// CORRECT: PATCH with request body (5 parameters)
ResponseEntity<Void> response = restApiClient.call(
    HttpMethod.PATCH,
    URI.create(url),
    requestBody,          // Request body - REQUIRED!
    headers,
    Void.class
);
```

**Why It Matters**:
- POST/PUT/PATCH requests typically require a request body
- Using 4-parameter variant sends request WITHOUT body
- This causes **silent failures** - request is sent but server receives empty body
- Very hard to debug because no compilation error occurs

**How to Detect**:
- Count parameters in `call()` method
- If HttpMethod is POST/PUT/PATCH, there should be **5 parameters**
- 3rd parameter should be the request body object, NOT headers
- If 3rd parameter is `HttpHeaders` or `headers`, it's WRONG

**Parameter Comparison**:
| HTTP Method | Parameters | Signature |
|-------------|-----------|-----------|
| GET/DELETE | 4 params | `call(method, uri, headers, responseType)` |
| POST/PUT/PATCH | 5 params | `call(method, uri, body, headers, responseType)` |

**Common Mistake Pattern**:
```java
// Developer has HttpEntity<Request> and extracts only headers
HttpEntity<CreateRequest> httpEntity = new HttpEntity<>(request, headers);

// WRONG - forgot to include body!
restApiClient.call(HttpMethod.POST, uri, httpEntity.getHeaders(), Void.class);

// CORRECT - include body from HttpEntity
restApiClient.call(HttpMethod.POST, uri, httpEntity.getBody(), httpEntity.getHeaders(), Void.class);
```

---

### Red Flag 10: SecurityFilter Version Mismatch

**Problem:** Using SDK2 securityFilter (6.x) with SDK3 which requires Jakarta EE.

**HALLUCINATION** (wrong version):
```gradle
// Using SDK2 version with SDK3 - WRONG!
implementation 'com.barclays.security:securityFilter:6.0.1'
implementation 'com.barclays.security:securityFilter:6.1.0'
```

**HALLUCINATION** (commenting out filters):
```java
// DON'T comment out security filters!
// @Bean
// public FilterRegistrationBean securityFilter() { ... }
```

**SKILL-DOCUMENTED** (common_libraries.md, SecurityFilter section):
```gradle
// SDK3 requires Jakarta EE compatible version
implementation 'com.barclays.security:securityFilter:7.0.0-RELEASE'
```

**Why It Matters**:
- SDK2 securityFilter 6.x uses `javax.servlet.Filter`
- SDK3 requires `jakarta.servlet.Filter`
- Using 6.x causes ClassCastException or NoClassDefFoundError
- **NEVER** comment out security filters - they provide critical security headers

**How to Detect**:
- Check for `com.barclays.security:securityFilter:6.*` in build.gradle
- Check for commented-out security filter beans
- Look for `NoClassDefFoundError: javax/servlet/Filter` errors

**Errors Without Upgrade**:
```
java.lang.NoClassDefFoundError: javax/servlet/Filter
ClassCastException: cannot be cast to jakarta.servlet.Filter
```

---

### Red Flag 11: Plain RestTemplate for Custom SSL Instead of CoreRestApiClient

**Problem**: Using RestTemplate directly for custom SSL loses SDK3 handler integration.

**HALLUCINATION** (plain RestTemplate):
```java
@Bean
public RestTemplate restTemplate() {
    RestTemplate template = new RestTemplate(sslClientHttpRequestFactory());
    return template;  // WRONG - Bypasses SDK3 handlers
}
```

**SKILL-DOCUMENTED** (SKILL.md, Pattern 2C: Custom SSL with CoreRestApiClient):
```java
import com.barclays.api.bap.bld.lib.common.request.RequestHandler;
import com.barclays.api.bap.bld.lib.common.response.ResponseHandler;
import com.barclays.api.bap.bld.lib.restclient.CoreRestApiClient;
import com.barclays.api.bap.bld.lib.restclient.RestApiClient;

@Bean
public RestApiClient restApiClient(
        RequestHandler requestHandler,
        ResponseHandler responseHandler) {
    RestTemplate restTemplate = new RestTemplate(sslClientHttpRequestFactory());
    return new CoreRestApiClient(
        RestClient.create(restTemplate),
        requestHandler,
        responseHandler
    );
}
```

**Why It Matters**:
- Plain RestTemplate doesn't integrate with SDK3 request/response handlers
- Loses SDK3 logging, tracing, and header propagation
- Custom SSL is commonly needed but must still use SDK3 patterns
- `CoreRestApiClient` wraps RestTemplate with SDK3 handlers

**How to Detect**:
- Look for `@Bean public RestTemplate` without `CoreRestApiClient`
- Check for SSL configuration that doesn't use `RequestHandler`/`ResponseHandler`
- Look for `new RestTemplate(...)` returned directly without wrapping

**Required Classes for Custom SSL**:
| Class | Package |
|-------|---------|
| RequestHandler | `com.barclays.api.bap.bld.lib.common.request` |
| ResponseHandler | `com.barclays.api.bap.bld.lib.common.response` |
| CoreRestApiClient | `com.barclays.api.bap.bld.lib.restclient` |
| RestClient | `org.springframework.web.client` (Spring 6.1+) |

---

### Red Flag 12: Using `var` Instead of Explicit Types

**Problem**: Using Java `var` keyword instead of explicit type declarations reduces code readability and consistency.

**AVOID:**
```java
var assembler = RestResponse.assemble();
var response = gateway.callService(request);
var headers = new HttpHeaders();
```

**PREFERRED:**
```java
ResponseAssembler assembler = RestResponse.assemble();
RestResponse response = gateway.callService(request);
HttpHeaders headers = new HttpHeaders();
```

**Why It Matters**:
- Maintains readability and consistency with existing Barclays codebase style
- Makes code more self-documenting, especially for SDK3 library types like `ResponseAssembler`
- Easier for developers unfamiliar with SDK3 APIs to understand the code
- Aligns with Barclays coding standards for enterprise Java applications
- Type is immediately visible without IDE hover or navigation

**How to Detect**:
- Search for `var ` keyword in production code (`src/main/java`)
- Check variable declarations for SDK3 types like `RestResponse`, `ResponseAssembler`, `RestApiClient`
- Especially flag `var` usage with SDK3-specific types where the type isn't obvious

**Scope**:
- **Production code (`src/main/java`)**: Always use explicit types
- **Test code (`src/test/java`)**: May use `var` at developer discretion for simple local variables where type is obvious from context (e.g., `var list = new ArrayList<String>()`)

**Common SDK3 Types Requiring Explicit Declaration**:
```java
// ALWAYS use explicit types for these:
ResponseAssembler assembler = RestResponse.assemble();
RestResponse response = service.call();
RestApiClient restApiClient = ...;
ResponseEntity<String> entity = restApiClient.call(...);
```

**Note**: While Java 10+ supports `var` and it's a valid language feature, explicit typing is preferred in SDK3 migrations to maintain consistency with the existing codebase and improve code readability for team members.

---

### Red Flag 13: Incorrect Branch Structure (Workflow Validation)

**Problem**: Creating multiple branches per migration instead of using a single feature branch with phase commits.

**INCORRECT (Multiple branches per migration):**
```
master
+-- feature/phase-1-build-config
    +-- feature/phase-2-packages
        +-- feature/phase-3-rest-client
            +-- feature/phase-4-tests
                +-- feature/phase-5-validation
```

**CORRECT (Single branch with phase commits):**
```
master
+-- feature/<JIRA-ID>
    |-- commit: <JIRA-ID> : Phase 0 - Pre-migration analysis
    |-- commit: <JIRA-ID> : Phase 1 - Build configuration migrated to SDK3
    |-- commit: <JIRA-ID> : Phase 2 - Package and import migration
    |-- commit: <JIRA-ID> : Phase 3 - REST client migration
    |-- commit: <JIRA-ID> : Phase 4 - Test migration to JUnit 5
    +-- commit: <JIRA-ID> : Phase 5 - SDK3 migration complete
```

**Why It Matters**:
- Simpler workflow with one branch to manage
- Each phase is a discrete commit for easy rollback (`git revert`)
- Clear comparison of changes per phase (`git diff HEAD~1`)
- Single PR for the entire migration
- Follows the `branching-strategy` skill requirements

**How to Detect**:
```bash
# Check current branch follows single-branch convention
git branch --show-current | grep -E "^feature/"

# Verify phase commits are sequential on the same branch
git log --oneline | head -10

# Ensure no stray phase-specific branches exist
git branch --list "feature/phase-*"  # Should return nothing
```

**Validation Commands (Run Before Each Phase):**
```bash
# Before starting Phase N, verify:
# 1. You're on the correct feature branch
git branch --show-current  # Should be feature/<JIRA-ID>

# 2. Previous phase commit exists
git log --oneline | grep "Phase $((N-1))"

# 3. Working tree is clean
git status
```

**Commit Message Format:**
```
<JIRA-ID> : Phase <N> - <Short description>

- Change 1
- Change 2

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Recovery if Wrong Structure:**
```bash
# If multiple branches were created, squash onto single branch:
# 1. Create the correct feature branch from master
git checkout master && git checkout -b feature/<JIRA-ID>

# 2. Cherry-pick commits from each phase branch in order
git cherry-pick <phase-1-commit>
git cherry-pick <phase-2-commit>
# ... etc
```

---

### Red Flag 14: IBM MQ Jakarta Client Misconfiguration

**Problem:** Suggesting to use ONLY jakarta.client or removing working MQ configuration methods

**CRITICAL HALLUCINATION PATTERNS:**

**Pattern 1: Missing allclient dependency**
```gradle
// WRONG - Only jakarta.client
testImplementation 'com.ibm.mq:com.ibm.mq.jakarta.client:9.4.1.0'

// CORRECT - BOTH dependencies needed
testImplementation 'com.ibm.mq:com.ibm.mq.jakarta.client:9.4.1.0'
testImplementation 'com.ibm.mq:com.ibm.mq.allclient:9.4.1.0'
```

**Pattern 2: Wrong import package**
```java
// WRONG
import com.ibm.mq.jms.MQQueue;

// CORRECT
import com.ibm.mq.jakarta.jms.MQQueue;
```

**Pattern 3: Missing dual exception handling**
```java
// CORRECT - BOTH exception types
public QueueConnectionFactory mainframeJmsConnectionFactory()
    throws javax.jms.JMSException, JMSException {
```

**Validation Rule:**
- IBM MQ 9.4 requires BOTH `jakarta.client` AND `allclient` artifacts
- Use `com.ibm.mq.jakarta.jms.*` package (NOT `com.ibm.mq.jms.*`)
- Never suggest removing MQ configuration methods - they work fine

---

### Red Flag 15: Incorrectly Migrating javax.sql.* to jakarta.sql.*

**Problem:** LLMs hallucinate that javax.sql.* should be migrated to jakarta.sql.*

**CRITICAL HALLUCINATION:**
```java
// WRONG - javax.sql is part of Java SE, not Java EE
import jakarta.sql.DataSource;
```

**CORRECT:**
```java
// CORRECT - javax.sql stays as-is (part of Java SE)
import javax.sql.DataSource;
```

**Rule:** Only Java EE packages migrate to jakarta. Java SE packages (javax.sql, javax.swing, javax.crypto, javax.net) stay as javax.

---

### Red Flag 16: Incorrect Dependency Scope (implementation vs api)

**Problem:** Using `implementation` scope for library dependencies that expose types to consumers

**HALLUCINATION:**
```gradle
// WRONG - EMM libraries expose types to consumers
implementation 'com.barclays.api.emm.common.core:api-connector-data:1.2.001'
```

**CORRECT:**
```gradle
// Logging - implementation (internal use only)
implementation 'com.barclays.api:bap-bld-lib-logging:1.3.001'

// EMM Common Libraries - api (types exposed to consumers)
api 'com.barclays.api.emm.common.core:api-connector-data:1.2.001'
```

**Decision Rule:** If dependency's type appears in public method signatures, use `api`. Otherwise, use `implementation`.

Use `$GRADLE_CMD dependencies` to verify scope after changes.

---

### Red Flag 17: Test Package Misalignment

**Problem:** Test files in non-standard packages (with prefixes like `integ.`, `mock.`, `test.`) instead of matching source package structure.

**CRITICAL HALLUCINATION PATTERNS:**

**Pattern 1: Non-standard test package prefixes**
```java
// WRONG - Test package doesn't match source package
// Source: com.barclays.api.gateway.UserGateway
// Test:   integ.com.barclays.api.gateway.UserGatewayTest
package integ.com.barclays.api.gateway;

public class UserGatewayTest {
    // ...
}
```

**Pattern 2: Test prefix packages**
```java
// WRONG - Using 'test.' prefix
package test.barclays.api.service;

public class PaymentServiceTest {
    // ...
}
```

**Pattern 3: Mock prefix packages**
```java
// WRONG - Using 'mock.' prefix
package mock.barclays.api.util;

public class HelperUtilTest {
    // ...
}
```

**CORRECT - Test package matches source package exactly:**
```java
// Source: src/main/java/com/barclays/api/gateway/UserGateway.java
package com.barclays.api.gateway;

public class UserGateway {
    // ...
}

// Test: src/test/java/com/barclays/api/gateway/UserGatewayTest.java
package com.barclays.api.gateway;

public class UserGatewayTest {
    // ...
}
```

**Why It Matters:**
- **PIT Mutation Testing requires exact package match** between test and source
- Industry best practice for test organization
- Better IDE support for test discovery and navigation
- Required for Phase 3 (coverage improvement) to succeed

**How to Detect:**
```bash
# Search for non-standard test package prefixes
grep -r "^package integ\." src/test/java
grep -r "^package mock\." src/test/java
grep -r "^package test\." src/test/java

# Any results = misalignment detected
```

**Validation Rule:**
```bash
# For each test file, verify package matches source
# Extract test package
TEST_PKG=$(grep "^package " src/test/java/path/to/MyTest.java | sed 's/package //;s/;//')

# Extract source package (strip Test suffix from class name)
SOURCE_CLASS=$(basename MyTest.java .java | sed 's/Test$//')
SOURCE_PKG=$(grep "^package " src/main/java/**/${SOURCE_CLASS}.java | sed 's/package //;s/;//')

# Compare - must be identical
if [ "$TEST_PKG" != "$SOURCE_PKG" ]; then
    echo "MISMATCH: Test in $TEST_PKG but source in $SOURCE_PKG"
fi
```

**Fix Pattern:**
```bash
# 1. Update package declaration in test file
sed -i 's/^package integ\./package /' src/test/java/path/to/test/file.java
sed -i 's/^package mock\./package /' src/test/java/path/to/test/file.java
sed -i 's/^package test\./package /' src/test/java/path/to/test/file.java

# 2. Move file to correct directory structure
# From: src/test/java/integ/com/barclays/api/UserTest.java
# To:   src/test/java/com/barclays/api/UserTest.java
```

**Common Non-Standard Prefixes to Check:**
- `integ.` - Integration test prefix (WRONG)
- `mock.` - Mock test prefix (WRONG)
- `test.` - Generic test prefix (WRONG)
- `unit.` - Unit test prefix (WRONG)

**Standard Practice:**
- Test package MUST match source package exactly
- Test file location: `src/test/java/{package-path}/{ClassName}Test.java`
- Source file location: `src/main/java/{package-path}/{ClassName}.java`
- NO prefixes, NO suffixes, NO organizational sub-packages

---

### Red Flag 18: Removing Working Code

**Problem**: Removing methods, classes, or code blocks that are functionally correct.

**AVOID:**
```
// Agent incorrectly removing method
// [Method removed]
```

**PREFERRED:**
```java
// VALIDATE: Method signature and dependencies are correct
// DO NOT suggest removal unless documented in migration spec
// If method works after migration -> it stays
```

**Why It Matters**:
- Breaks functionality: Working code is removed
- Creates runtime errors: Callers of removed methods fail
- Loses business logic: Domain logic deleted without review

**How to Detect**:
- Agent suggests "removing" or "deleting" code
- Agent says "not needed in SDK3" without spec citation
- Agent removes methods that compile and work
- Agent suggests "simplifying" by deletion

**Agent Rule**:
- **NEVER** suggest removing code unless specified in sdk2-sdk3-migration skill as deprecated
- **NEVER** suggest removing code unless code causes compilation errors that can't be fixed
- **NEVER** suggest removing code unless Code is SDK2-specific with no SDK3 equivalent (documented)
- **VALIDATE** that existing code works with SDK3
- **DO NOT** suggest deletion of working code

### Example
```java
// WRONG - Below 2 configuration beans are removed from @configuration class
/**
 * This is the bean of InternalApiInitializer to initiailize the IAPI beans.
 *
 * @return InternalApiInitializer bean
 */
@Bean
public InternalApiInitializer internalApiInitializer() {
  return new InternalApiInitializer();
}
@Bean
public ExternalApiInitializer externalApiInitializer() {
  return new ExternalApiInitializer();
}
// CORRECT - These beans should not be removed from @Configuration class
```

---


## The Big 5 Patterns

See SKILL.md Patterns 1-5 for the canonical patterns. This section provides the validation checklist only.

### Pattern 1: Building Responses

**Key Points**:
- Use `RestResponse.assemble()` for building (NOT `Response.assemble()`)
- Return type is `Response` interface
- Implementation uses `RestResponse` concrete class

### Pattern 2: REST Client Calls

**Key Points**:
- Method name is `call()` (not execute, callApi, get, post, etc.)
- HttpMethod comes FIRST (changed from SDK2)
- Returns `ResponseEntity<String>`
- Parse body using ObjectMapper separately
- **CRITICAL**: POST/PUT/PATCH must use 5-parameter variant with body (Red Flag 9)

### Pattern 3: Date/Time Migration

**Key Points**:
- Use `LocalDate.now()` (not `new LocalDate()`)
- No direct conversion from `Date` to `LocalDate`
- Must go through Instant and ZoneId

### Pattern 4: Validation with RestResponse

**Key Points**:
- Parameter type is `RestResponse` (not `Response`)
- `Response` interface doesn't have `getHttpStatus()` or `getErrors()`
- Cast from `Response` to `RestResponse` when needed

### Pattern 5: Test Mocking

**Key Points**:
- Use `@ExtendWith(SpringExtension.class)` (JUnit 5)
- Use `@MockitoBean` (not `@MockBean`)
- Match parameter types in exact order
- Use specific type matchers (`any(HttpMethod.class)`, not `any()`)

---

## Emergency 60-Second Validation Checklist

Use this for quick validation when under time pressure:

```
EMERGENCY SDK2 to SDK3 VALIDATION - 60 Second Check

1. Skill Pattern Located?
   [ ] Yes (SKILL.md, lessons_learnt.md, sdk2_to_sdk3_package_mapping.md, or test_migration_specification.md + section) -> Continue
   [ ] No -> STOP - REJECT until found

2. Exact Code Pattern Found in Skill?
   [ ] Yes, exact match -> Continue
   [ ] Close but different -> STOP - VERIFY exact pattern
   [ ] No example found -> STOP - REJECT

3. Any Red Flag Phrases Present?
   [ ] "should work"
   [ ] "typically"
   [ ] "usually"
   [ ] "standard pattern"
   If YES -> STOP - REJECT with skill citation requirement

4. Package Name Check:
   [ ] Includes "com.barclays.api.bap.bld.lib" -> Continue
   [ ] Shorter path (missing .bap.bld.lib) -> STOP - REJECT as Red Flag 1
   [ ] Different structure -> STOP - VERIFY skill mapping

5. Response/RestResponse Check (if applicable):
   [ ] Using RestResponse.assemble() for building -> Continue
   [ ] Using Response.assemble() -> STOP - REJECT (Red Flag 5)
   [ ] Using RestResponse type for getHttpStatus() -> Continue
   [ ] Using Response type for getHttpStatus() -> STOP - REJECT (Red Flag 8)

6. RestApiClient Check (if applicable):
   [ ] HttpMethod parameter FIRST -> Continue
   [ ] URI parameter first -> STOP - REJECT (Red Flag 7)
   [ ] Method name is "call" -> Continue
   [ ] Method name is anything else -> STOP - REJECT (Red Flag 2)

7. POST/PUT/PATCH Body Check (if applicable):
   [ ] If GET/DELETE, using 4-parameter call() -> Continue
   [ ] If POST/PUT/PATCH, using 5-parameter call() with body -> Continue
   [ ] If POST/PUT/PATCH with only 4 parameters -> STOP - REJECT (Red Flag 9)
   [ ] If 3rd parameter is headers (not body) for POST/PUT/PATCH -> STOP - REJECT (Red Flag 9)

8. JUnit Import Check (if test code):
   [ ] All "org.junit.jupiter.api.*" -> Continue
   [ ] Any "org.junit.*" (without jupiter) -> STOP - REJECT (Red Flag 3)
   [ ] Using assertThrows() for exceptions -> Continue
   [ ] Using @Test(expected=...) -> STOP - REJECT (JUnit 4 pattern)

9. Gradle URL Check (if gradle-wrapper.properties):
   [ ] Contains "nexus.barcapint.com" -> Continue
   [ ] Contains "services.gradle.org" -> STOP - REJECT (Red Flag 6)

10. SecurityFilter Check (if build.gradle):
    [ ] Using securityFilter:7.0.0-RELEASE -> Continue
    [ ] Using securityFilter:6.x -> STOP - REJECT (Red Flag 10)
    [ ] Security filter beans commented out -> STOP - REJECT (Red Flag 10)

11. Custom SSL Check (if SSL configuration present):
    [ ] Using CoreRestApiClient with RequestHandler/ResponseHandler -> Continue
    [ ] Using plain RestTemplate for SSL -> STOP - REJECT (Red Flag 11)
    [ ] Missing RequestHandler/ResponseHandler injection -> STOP - REJECT (Red Flag 11)

12. Variable Type Declaration Check (production code):
    [ ] Using explicit types (e.g., ResponseAssembler assembler = ...) -> Continue
    [ ] Using var for SDK3 types (e.g., var assembler = ...) -> FLAG - Recommend explicit type (Red Flag 12)
    [ ] Using var for obvious types in test code -> Continue (acceptable)

13. Branch Structure Check (workflow validation):
    [ ] Single feature branch: `feature/<JIRA-ID>` -> Continue
    [ ] Phase commits are sequential on the same branch -> Continue
    [ ] No stray `feature/phase-*` branches exist -> Continue
    [ ] Multiple branches per migration detected -> STOP - REJECT (Red Flag 13)
    [ ] Branch name missing JIRA ID -> STOP - Fix branch name

14. Test Package Alignment Check (if test code):
    [ ] Test package matches source package exactly (no prefixes) -> Continue
    [ ] Test package has 'integ.', 'mock.', 'test.', or 'unit.' prefix -> STOP - REJECT (Red Flag 17)
    [ ] Test file location matches source structure -> Continue
    [ ] Test and source in different package hierarchies -> STOP - REJECT (Red Flag 17)

15. Code Removal Check (removing working code):
    [ ] Code suggested for removal is SDK2-specific with no SDK3 equivalent -> Continue
    [ ] Code being removed causes compilation errors that can't be fixed -> Continue
    [ ] Code suggests removal without spec citation -> FLAG - REJECT (Red Flag 18)
    [ ] Code removes methods that compile and work -> STOP - REJECT (Red Flag 18)
    [ ] Code suggests deletion as "simplification" -> STOP - REJECT (Red Flag 18)

16. Confidence Level:
   [ ] HIGH (exact skill match) -> APPROVE
   [ ] MEDIUM (close skill match) -> APPROVE WITH NOTES
   [ ] LOW (uncertain) -> REJECT

If ANY STOP condition -> REJECT and provide specific fix with skill reference
```

---

## Language Hallucination Indicators

These phrases indicate uncertainty and potential hallucination:

### Red Flag Phrases

| Phrase | Why It's Wrong | What to Use Instead |
|--------|---------------|-------------------|
| "should work in SDK3" | Uncertainty | "documented in SKILL.md, Section X" |
| "typically works with Spring Boot 3" | Assumption | "matches Pattern Y from SKILL.md" |
| "usually done this way" | Generic knowledge | "verified against SKILL.md" |
| "standard Spring pattern" | Not SDK3-specific | "documented in SKILL.md, Pattern 2" |
| "commonly used approach" | Not verified | "exact match with skill documentation" |
| "probably correct" | Guessing | "confirmed in SKILL.md" |
| "looks right" | Visual similarity | "character-by-character match verified" |
| "close enough" | Approximation | "exact match required" |

### Confident Language

| Phrase | Why It's Good |
|--------|--------------|
| "documented in SKILL.md, Section X" | Specific citation |
| "matches Pattern Y from SKILL.md" | Pattern identification |
| "verified against skill documentation" | Explicit verification |
| "character-by-character match confirmed" | Precision |
| "exact match with SKILL.md line 45" | Traceability |

---

## Cross-Reference Validation

When validating patterns, also check:

### Related Patterns

| If Validating | Also Check |
|--------------|------------|
| Package imports | SKILL.md: Package Import Changes section |
| REST client calls | SKILL.md: Pattern 2 + parameter order note |
| Response building | SKILL.md: Pattern 1 + Common Pitfall #1 |
| Test code | SKILL.md: JUnit 4 to 5 Migration + Pattern 5 |
| Gradle config | SKILL.md: Quick Start Step 1 + Pitfall #4 |
| Date/Time | SKILL.md: Pattern 3 + Joda migration notes |

### Common Combinations

Some patterns frequently appear together:

**REST Client + Response Validation:**
```java
// Must validate both call() signature AND RestResponse usage
ResponseEntity<String> entity = restApiClient.call(
    HttpMethod.GET,  // Red Flag 7: Check order
    URI.create(url),
    headers,
    String.class
);

RestResponse response = parseResponse(entity);  // Red Flag 8: Must be RestResponse
if (response.getHttpStatus().is2xxSuccessful()) {
    // validation logic
}
```

**Test Code + JUnit 5:**
```java
// Must validate imports, annotations, AND assertions together
import org.junit.jupiter.api.Test;  // Red Flag 3: Check for mixed versions
import org.junit.jupiter.api.BeforeEach;

@ExtendWith(SpringExtension.class)  // Not @RunWith
class MyTest {
    @MockitoBean  // Pattern 5: Use MockitoBean
    private RestApiClient client;

    @Test  // Not @org.junit.Test
    void test() {
        assertThrows(Exception.class, () -> {});  // Not @Test(expected=...)
    }
}
```

---

## Usage with Validation Agent

This document is designed to be used by the sdk2-to-sdk3-validation-agent. The agent will:

1. **Load this document** as domain-specific knowledge
2. **Apply Red Flags 1-18** during hallucination detection phase
3. **Check against Big 5 Patterns** for core scenarios
4. **Use Emergency Checklist** for quick validation
5. **Reference specific sections** when citing sources

**Agent Invocation:**
```
Use the sdk2-to-sdk3-validation-agent with this code:
[paste code to validate]
```

The agent will automatically reference this validation-patterns.md file for domain-specific checks while applying its generic validation framework.

---

## Version Information

**Patterns Version**: 2.0
**SDK3 Version Covered**: 1.12.007
**Last Updated**: 2026-02-17
**Compatible With**: sdk2-to-sdk3-validation-agent v1.0

**Changelog:**

- **v2.1** (2026-03-13):
  - Added Red Flag 18: Removing Working Code
  - Updated Emergency Checklist with step 15 for code removal validation
  - Updated title to "18 Red Flags"
  - Rationale: Enforces that working code must be maintained or properly migrated, not deleted without spec citation

- **v2.0** (2026-02-17):
  - Consolidated all changelog entries into single section
  - Fixed title to consistently reference "17 Red Flags"
  - Replaced Big 5 Patterns full code examples with SKILL.md reference and validation checklists only
  - Fixed Emergency Checklist item 13 to validate single-branch model (not branch-per-phase)

- **v1.5**:
  - Added Red Flag 17: Test Package Misalignment
  - Added test package alignment detection and fix patterns

- **v1.4**:
  - Added Red Flag 14: IBM MQ Jakarta Client Misconfiguration
  - Added Red Flag 15: javax.sql.* (Java SE) should NOT migrate to jakarta
  - Added Red Flag 16: Dependency Scope (api vs implementation)
  - Added Red Flag 13: Incorrect Branch Structure (Workflow Validation)
  - Added dependency scope guidance to Red Flag 16

- **v1.3**:
  - Added Red Flag 12: Using `var` Instead of Explicit Types

- **v1.2**:
  - Added Red Flag 10: SecurityFilter Version Mismatch (6.x vs 7.0.0-RELEASE)
  - Added Red Flag 11: Plain RestTemplate for Custom SSL Instead of CoreRestApiClient

- **v1.1**:
  - Added Red Flag 9: POST/PUT/PATCH Without Request Body
  - Updated Pattern 2 to include Pattern 2A (GET/DELETE) and Pattern 2B (POST/PUT/PATCH)
  - Added step 7 to Emergency Checklist for body parameter check

- **v1.0**:
  - Initial release with Red Flags 1-8
