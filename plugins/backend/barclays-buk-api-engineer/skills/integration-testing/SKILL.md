---
name: integration-testing
description: Karate BDD testing with WireMock stubs for SDK3 integration tests
color: blue
---

> **Source:** Barclays BUK Karate BDD testing standards and WireMock integration patterns for SDK3 services.
> **Owner:** BUK
> **Review trigger:** On Karate or WireMock major version upgrade, or when Barclays integration test standards change.
> **Status:** Reviewed

# Skill: Integration Testing — Karate + WireMock for SDK3

## When to Use This Skill

Use this skill when:
- Generating integration tests for generated Spring Boot services
- Setting up WireMock stubs for downstream API mocking
- Creating Karate BDD feature files for API endpoint testing
- Configuring test database (H2) and test properties
- Generating test utilities and helper classes

## Critical Rule

**All generated projects MUST include integration tests using Karate BDD framework with WireMock.** This is mandated by SDK3's kotlin-int-test-gradle-plugin (version 1.5+) and is a hard requirement for production services.

## Quick Start

Generate integration tests for a DAF service:

1. Create `src/test/resources/features/{endpoint}.feature` with Karate scenarios
2. Create `src/test/java/{basePackage}/TestRunner.java` with `@Karate.Test`
3. Create WireMock stub files in `src/test/resources/wiremock/mappings/`
4. Configure `application-int.properties` with downstream stub URLs

All projects require 80%+ integration test coverage (hard gate).

---

## Architecture: Integration Test Structure

### Gradle Plugin Integration

The `bap-bld-lib-kotlin-int-test-gradle-plugin` (v1.5+) auto-configures:
- Karate feature file discovery in `src/test/resources/features/`
- WireMock sandbox with stubs for all downstream APIs
- Three test types: `integrationTest`, `postDeploymentTest`, `performanceTest`
- JaCoCo integration test coverage reporting
- 80%+ coverage hard gate for integration tests

### Project Structure for Tests

```
project/
├── src/test/
│   ├── java/{basePackage}/
│   │   ├── runner/
│   │   │   └── KarateTestsRunner.java
│   │   ├── service/
│   │   │   └── {ResourceName}ServiceIntTest.java
│   │   └── helpers/
│   │       └── WireMockHelper.java
│   └── resources/
│       ├── features/
│       │   └── {resource-name}.feature    # One per endpoint
│       ├── wiremock/
│       │   └── {downstream-service}.json  # WireMock stubs
│       └── application-int.properties
├── build.gradle                          # With karate.enabled = true
└── gradle.properties                     # With SDK3_VERSION set
```

---

## 1. Karate Test Runner

**File:** `src/test/java/{basePackage}/runner/KarateTestsRunner.java`

```java
package {basePackage}.runner;

import com.intuit.karate.junit5.Karate;
import org.junit.jupiter.api.DisplayName;

@DisplayName("Integration Tests — Karate BDD")
public class KarateTestsRunner {
    
    @Karate.Test
    Karate testAll() {
        return Karate.run("classpath:features").relativeTo(getClass());
    }

    @Karate.Test
    Karate testSmoke() {
        return Karate.run("classpath:features/smoke").relativeTo(getClass());
    }
}
```

---

## 2. Karate Feature Files (BDD Test Cases)

**One feature file per endpoint group.**

### Example: User Endpoint Feature

**File:** `src/test/resources/features/users.feature`

```gherkin
Feature: User Management API

  Background:
    * url baseUrl
    * header Correlation-ID 'test-correlation-123'
    * configure logPrettyRequest = true
    * configure logPrettyResponse = true

  Scenario: Create user successfully
    Given request
      """
      {
        "name": "John Doe",
        "email": "john@example.com",
        "department": "Engineering"
      }
      """
    When method post
    Then status 201
    And match response.data.id == '#notnull'
    And match response.meta.correlationId == 'test-correlation-123'

  Scenario: List users with pagination
    Given path '/users'
    And param page = 1
    And param size = 10
    When method get
    Then status 200
    And match response.data[*].id == '#[] #notnull'
    And match response.meta.totalCount == '#number'

  Scenario: Get user by ID
    Given path '/users/123'
    When method get
    Then status 200
    And match response.data.id == 123

  Scenario: Update user
    Given path '/users/123'
    And request { "name": "Jane Doe" }
    When method put
    Then status 200
    And match response.data.name == 'Jane Doe'

  Scenario: Delete user
    Given path '/users/123'
    When method delete
    Then status 204
```

### Mandatory Patterns in Feature Files

1. **Correlation-ID Header** — Required for all requests (SDK3 mandatory for internal APIs)
   ```gherkin
   * header Correlation-ID 'test-correlation-<unique>'
   ```

2. **Response Validation** — Check SDK3 response wrapper structure
   ```gherkin
   And match response.data == '#notnull'        # Resource<T> data
   And match response.meta.correlationId == '#notnull'
   ```

3. **Error Scenarios** — Test error responses with Message objects
   ```gherkin
   Scenario: Validation error
     Given request { "email": "invalid" }
     When method post
     Then status 400
     And match response.errors[0].code == 'INVALID_EMAIL'
     And match response.errors[0].message == '#notnull'
   ```

---

## 3. WireMock Stubs (Downstream API Mocking)

**WireMock auto-starts on a random port.** Generate stubs for EACH downstream API.

### File: `src/test/resources/wiremock/payment-service.json`

```json
{
  "mappings": [
    {
      "request": {
        "method": "POST",
        "url": "/api/v1/payments/process"
      },
      "response": {
        "status": 200,
        "headers": {
          "Content-Type": "application/json"
        },
        "jsonBody": {
          "data": {
            "transactionId": "TXN-12345",
            "status": "COMPLETED",
            "amount": 1000.00
          },
          "meta": {
            "timestamp": "2026-06-20T10:30:00Z"
          }
        }
      }
    },
    {
      "request": {
        "method": "POST",
        "url": "/api/v1/payments/refund"
      },
      "response": {
        "status": 200,
        "jsonBody": {
          "data": {
            "refundId": "REF-12345",
            "status": "COMPLETED"
          }
        }
      }
    }
  ]
}
```

---

## 4. Test Properties Configuration

**File:** `src/test/resources/application-int.properties`

```properties
# Server and app configuration
server.port=0  # Random port for tests
spring.application.name=my-service

# Datasource — H2 in-memory database
spring.datasource.url=jdbc:h2:mem:testdb;MODE=PostgreSQL
spring.datasource.driverClassName=org.h2.Driver
spring.jpa.database-platform=org.hibernate.dialect.H2Dialect
spring.jpa.hibernate.ddl-auto=create-drop

# SDK3 Logging
logging.level.root=WARN
logging.level.com.barclays=DEBUG

# Downstream API endpoints — ROUTED TO WIREMOCK
int.test.downstream.payment-service.url=http://localhost
int.test.downstream.payment-service.port=${wiremock.server.port}

int.test.downstream.user-service.url=http://localhost
int.test.downstream.user-service.port=${wiremock.server.port}

# Request Validation
requestValidation.isRequired=true
requestValidation.specPath=classpath:oas/openapi.yaml

# Mesh and Eureka disabled for tests
eureka.client.enabled=false
```

**Key pattern:** Use `${wiremock.server.port}` for dynamic WireMock port injection.

---

## 5. Integration Test Class (Optional, for Complex Setup)

**File:** `src/test/java/{basePackage}/service/{ResourceName}ServiceIntTest.java`

```java
package {basePackage}.service;

import com.github.tomakehurst.wiremock.WireMockServer;
import com.github.tomakehurst.wiremock.client.WireMock;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

import static com.github.tomakehurst.wiremock.client.WireMock.*;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("int")
public class PaymentServiceIntTest {

    private static WireMockServer wireMockServer;

    @BeforeEach
    public void setup() {
        wireMockServer = new WireMockServer(8089);  // Fixed port for tests
        wireMockServer.start();
        WireMock.configureDefaultInstance(new WireMock("localhost", 8089));
    }

    @Test
    public void testPaymentProcessingWithWireMock() {
        // Stub the downstream payment API
        stubFor(post(urlEqualTo("/api/v1/payments/process"))
            .willReturn(aResponse()
                .withStatus(200)
                .withHeader("Content-Type", "application/json")
                .withBody("{\"transactionId\": \"TXN-123\", \"status\": \"COMPLETED\"}")));

        // Test the service
        PaymentRequest request = new PaymentRequest();
        request.setAmount(1000);
        PaymentResponse response = paymentService.processPayment(request);

        // Verify WireMock was called
        verify(postRequestedFor(urlEqualTo("/api/v1/payments/process")));
    }
}
```

---

## 6. Gradle Task Configuration

**In `build.gradle`, ensure Karate is enabled:**

```groovy
karate {
    enabled = true
    testDir = 'src/test/resources/features'
    packageName = '{basePackage}.runner'
    
    // Integration test configuration
    integrationTest {
        glue = ['classpath:helpers']
        tags = '@smoke'
    }
}

// Integration test dependency
testImplementation 'com.intuit.karate:karate-junit5:1.4.1'
testImplementation 'com.github.tomakehurst:wiremock-jre8-standalone:3.0.0'
```

---

## 7. Test Coverage Requirements

**Integration tests MUST meet 80%+ code coverage:**

```groovy
jacocoTestReport {
    dependsOn integrationTest
    
    afterEvaluate {
        classDirectories.setFrom(
            files(classDirectories.files.collect {
                fileTree(dir: it, exclude: [
                    '**/config/**',
                    '**/entity/**',
                    '**/dto/**'
                ])
            })
        )
    }
}

jacocoTestCoverageVerification {
    violationRules {
        rule {
            element = 'CLASS'
            includes = ['com.example.service.*']
            
            limit {
                counter = 'LINE'
                value = 'COVEREDRATIO'
                minimum = 0.80
            }
        }
    }
}
```

---

## Mandatory Patterns Summary

| Pattern | Requirement | Why |
|---------|-------------|-----|
| **Correlation-ID header** | Required in all requests | SDK3 tracing requirement |
| **Response wrapper validation** | Check data, meta, errors | Validates SDK3 structure |
| **WireMock stubs** | One per downstream API | Isolates integration tests |
| **H2 database** | Use for test data | No external DB dependency |
| **Feature files** | One per endpoint group | Karate BDD organization |
| **80%+ coverage** | Hard gate, no exceptions | Mutation test resilience |

---

## Reference

- **Karate Documentation**: https://github.com/intuit/karate
- **WireMock Documentation**: http://wiremock.org/
- **SDK3 kotlin-int-test-gradle-plugin**: See bap-bld-lib-kotlin-int-test-gradle-plugin README
- **code-generation/SKILL.md**: Java code patterns for tested classes

## Source Attribution

**Primary sources:**
- Barclays BUK Karate BDD testing standards — feature file structure, runner class naming, tag conventions
- WireMock 3.x documentation — stub mapping format (`mappings/*.json`), `__files/` response body convention
- SDK3 `bap-bld-lib-kotlin-int-test-gradle-plugin` (version 1.5+) — integration test source set configuration, `integrationTest` Gradle task
- `domain-reference/SKILL.md` Section 3 (Pattern 3.8) — Spock + Karate test layout and conventions used in DAF services

**Training knowledge applied:**
- Karate BDD `Feature:`/`Scenario:` syntax and `karate.call()` data utility patterns
- WireMock JSON stub structure: `request` matcher + `response` body
- JUnit 5 `@RunWith(Karate.class)` runner class pattern
- Spring Boot test slice `@SpringBootTest(webEnvironment = RANDOM_PORT)` for integration context

**Known limitations:**
- WireMock stub examples are JSON-only; XML response stubs are not covered
- Integration test patterns assume a single WireMock server on `localhost:32131`; multi-server topologies require manual adaptation
- Karate version is not pinned in this skill; the exact version used is managed by `bap-bld-lib-kotlin-int-test-gradle-plugin` and may change on plugin upgrade

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] Does each API endpoint have at least one Karate feature file with success and error scenarios?
- [ ] Are WireMock stub mappings provided for every downstream API called in the test scope?
- [ ] Does application-int.properties route all downstream URLs to localhost:32131 (WireMock default port)?
- [ ] Is the Karate TestRunner annotated with @SpringBootTest and spawning the correct feature path?
- [ ] Are DataUtils helper methods provided for building request payloads in tests?
- [ ] Do integration tests use background sections for setup and shared feature state?

