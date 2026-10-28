# SDK3 Dependency Versions Reference

> **AGENT ROUTING:** Use this file for **third-party** dependencies only (`org.*`, `com.google.*`, `com.fasterxml.*`, etc.)
>
> For Barclays internal libraries (`com.barclays.*`, `com.barclaycard.*`), use [barclays_internal_libraries_versions.md](barclays_internal_libraries_versions.md) for versions and `barclays_internal_libraries_{group}.md` for group-specific MODIFY rules

**Scope:** Third-party libraries only

## Overview

This document provides a comprehensive reference for all **third-party** dependency versions required for SDK3 migration. These versions are validated and tested for compatibility with SDK3 (version 1.12.007), Spring Boot 3.3.x, and Java 21.

---

## Core SDK3 Dependencies

These dependencies are provided by the SDK3 platform and should NOT have explicit versions (managed by BOM):

| Dependency | GroupId | ArtifactId | Version Management |
|------------|---------|------------|-------------------|
| SDK3 Platform | com.barclays.api | sdk3 | `${SDK3_VERSION}` (e.g., 1.12.007) |
| REST API Library | com.barclays.api | bap-bld-lib-restapi | BOM managed |
| Mesh Connector | com.barclays.api | bap-bld-lib-meshconnector | BOM managed |
| Request Validator | com.barclays.api | bap-bld-lib-request-validator | BOM managed |
| Plugin | com.barclays.api | bap-bld-lib-plugin | BOM managed |

---

## Spring Framework Dependencies

| Dependency | SDK3 Version | Notes |
|------------|--------------|-------|
| spring-boot-starter-webflux | BOM managed | For reactive REST clients |
| spring-boot-starter-data-jpa | BOM managed | JPA support |
| spring-cloud-dependencies | 2023.0.6 | Spring Cloud BOM |
| spring-cloud-function-context | 4.2.2 | Cloud functions |
| spring-ws-core | 4.1.0 | Web services |
| spring-xml | 4.1.0 | XML processing |
| spring-jdbc | 6.2.5 | JDBC support |

---

## Testing Dependencies

| Dependency | GroupId | ArtifactId | SDK3 Version |
|------------|---------|------------|--------------|
| JUnit Jupiter | org.junit.jupiter | junit-jupiter | 5.13.4 |
| JUnit Platform Launcher | org.junit.platform | junit-platform-launcher | 1.14.2 |
| JUnit Platform Suite | org.junit.platform | junit-platform-suite-api | 1.10.1 |
| Mockito Core | org.mockito | mockito-core | 5.9.0 |
| Mockito JUnit 5 | org.mockito | mockito-junit-jupiter | 5.9.0 |
| WireMock Standalone | org.wiremock | wiremock-standalone | 3.13.2 |
| Karate JUnit 5 | com.intuit.karate | karate-junit5 | 1.4.1 |
| Karate Core | com.intuit.karate | karate-core | 1.4.1 |
| Cucumber Reporting | net.masterthought | cucumber-reporting | 5.4.0 |
| Cucumber Core | info.cukes | cucumber-core | 1.2.5 |
| Groovy | org.codehaus.groovy | groovy | 3.0.17 |
| AssertJ | org.assertj | assertj-core | 3.24.2 |
| H2 Database | com.h2database | h2 | 2.2.220 |
| MeanBean | com.github.meanbeanlib | meanbean | **2.0.3** |

> **meanbean version:** Use `2.0.3`. Version `3.0.0-M9` is a milestone release **not available** in Barclays Nexus. The 2.x API (`BeanTester`, `ConfigurationBuilder`) is fully compatible with all typical bean-testing patterns.

---

## Common Library Dependencies

| Dependency | GroupId | ArtifactId | SDK3 Version |
|------------|---------|------------|--------------|
| Guava | com.google.guava | guava | 33.4.7-jre |
| Gson | com.google.code.gson | gson | 2.10.1 |
| Commons IO | commons-io | commons-io | 2.16.1 |
| Commons Collections 4 | org.apache.commons | commons-collections4 | 4.5.0 |
| Commons Text | org.apache.commons | commons-text | 1.15.0 |
| Lombok | org.projectlombok | lombok | 1.18.38 |
| HikariCP | com.zaxxer | HikariCP | 5.1.0 |
| Apache HttpClient 5 | org.apache.httpcomponents.client5 | httpclient5 | 5.4.4 |

---

## Jakarta EE Dependencies

| Dependency | GroupId | ArtifactId | SDK3 Version |
|------------|---------|------------|--------------|
| Jakarta Servlet API | jakarta.servlet | jakarta.servlet-api | 6.0.0 |
| Jakarta XML WS API | jakarta.xml.ws | jakarta.xml.ws-api | 4.0.2 |
| Jakarta Validation API | jakarta.validation | jakarta.validation-api | BOM managed |

---

## XML/JAXB Dependencies

| Dependency | GroupId | ArtifactId | SDK3 Version |
|------------|---------|------------|--------------|
| JAXB XJC | org.glassfish.jaxb | jaxb-xjc | 4.0.3 |
| JAXB Impl | com.sun.xml.bind | jaxb-impl | 4.0.3 |
| JAXB Core | com.sun.xml.bind | jaxb-core | 4.0.3 |

---

## Database Dependencies

| Dependency | GroupId | ArtifactId | SDK3 Version |
|------------|---------|------------|--------------|
| Oracle JDBC | com.oracle.database.jdbc | ojdbc8 | 18.3.0.0 |
| H2 Database | com.h2database | h2 | 2.2.220 |

---

## Messaging Dependencies

| Dependency | GroupId | ArtifactId | SDK3 Version |
|------------|---------|------------|--------------|
| IBM MQ Jakarta Client | com.ibm.mq | com.ibm.mq.jakarta.client | 9.4.4.0 |

---

## Documentation Dependencies

| Dependency | GroupId | ArtifactId | SDK3 Version |
|------------|---------|------------|--------------|
| SpringDoc OpenAPI | org.springdoc | springdoc-openapi-starter-webmvc-ui | 2.2.0 |

---

## Security Dependencies

| Dependency | GroupId | ArtifactId | SDK3 Version |
|------------|---------|------------|--------------|
| Security Filter | com.barclays.security | securityFilter | 7.0.0-RELEASE |

> **Note:** For `com.barclaycard.digital` libraries (common-filter, common-context, etc.), see [barclays_internal_libraries_versions.md](barclays_internal_libraries_versions.md)

---

## Build Tool Dependencies

| Dependency | GroupId | ArtifactId | SDK3 Version |
|------------|---------|------------|--------------|
| OWASP Dependency Check | org.owasp | dependency-check-gradle | 12.1.9 |

---

## Barclays Internal Dependencies

| Dependency | GroupId | ArtifactId | SDK3 Version |
|------------|---------|------------|--------------|
| API BCAG Connector | com.barclays.api | api-bcag-connector | 1.1.7 |
| API DB Connector | com.barclays.api | api-db-connector | 1.1.3 |
| Functional Test Generator | com.barclays.api | functional-test-generator | 1.0.068 |

---

## Dependencies to REMOVE (SDK2 Only)

These dependencies are NOT compatible with SDK3 and must be removed:

| Dependency | GroupId | ArtifactId | Reason |
|------------|---------|------------|--------|
| API Core Boot | com.barclays.api | api-core-boot | Replaced by bap-bld-lib-restapi |
| API Core Properties | com.barclays.api | api-core-properties | Replaced by Spring Boot properties |
| API Mesh Client | com.barclays.api | api-mesh-client-connector | Replaced by bap-bld-lib-meshconnector |
| GIS SDK Filters | com.barclays.api.tools | gissdk-filters-wrapper | No longer needed |
| API Request Validator | com.barclays.api.tools | api-request-validator | Replaced by bap-bld-lib-request-validator |
| IBM MQ (old) | com.ibm.wmq | mq | Replaced by com.ibm.mq.jakarta.client |
| IBM MQ JMS (old) | com.ibm.wmq | mqjms | Replaced by com.ibm.mq.jakarta.client |
| Karate JUnit 4 | com.intuit.karate | karate-junit4 | Replaced by karate-junit5 |
| Karate Apache | com.intuit.karate | karate-apache | No longer needed |
| Karate TestNG | com.intuit.karate | karate-testng | No longer needed |
| WireMock (old groupId) | com.github.tomakehurst | wiremock | Replaced by org.wiremock |
| WireMock JRE8 | com.github.tomakehurst | wiremock-jre8 | Replaced by org.wiremock |
| WireMock Standalone (old) | com.github.tomakehurst | wiremock-standalone | Replaced by org.wiremock |
| Mockito All | org.mockito | mockito-all | Replaced by mockito-core |
| Log4j SLF4J Impl | org.apache.logging.log4j | log4j-slf4j-impl | SDK3 uses Logback |
| Log4j API | org.apache.logging.log4j | log4j-api | SDK3 uses Logback |
| Log4j Core | org.apache.logging.log4j | log4j-core | SDK3 uses Logback |
| Log4j Web | org.apache.logging.log4j | log4j-web | SDK3 uses Logback |
| RabbitMQ Client | com.rabbitmq | amqp-client | Use Spring AMQP instead |
| Tomcat Embed Core | org.apache.tomcat.embed | tomcat-embed-core | BOM managed |
| Tomcat Embed EL | org.apache.tomcat.embed | tomcat-embed-el | BOM managed |
| Tomcat Embed Websocket | org.apache.tomcat.embed | tomcat-embed-websocket | BOM managed |
| JSON Sanitizer | com.mikesamuel | json-sanitizer | No longer needed |
| SnakeYAML | org.yaml | snakeyaml | BOM managed |
| HTMLUnit Core JS | net.sourceforge.htmlunit | htmlunit-core-js | No longer needed |
| Neko HTMLUnit | net.sourceforge.htmlunit | neko-htmlunit | No longer needed |
| Rest Assured | io.rest-assured | rest-assured | Use WireMock/Karate |
| Rest Assured JSON Path | io.rest-assured | json-path | Use WireMock/Karate |
| Rest Assured XML Path | io.rest-assured | xml-path | Use WireMock/Karate |
| Jersey Core | com.sun.jersey | jersey-core | Incompatible with SDK3 |
| Jersey Client | com.sun.jersey | jersey-client | Incompatible with SDK3 |
| Jersey Apache Client | com.sun.jersey.contribs | jersey-apache-client4 | Incompatible with SDK3 |
| Apache HttpClient 4 | org.apache.httpcomponents | httpclient | Use `org.apache.httpcomponents.client5:httpclient5:5.4.4` |
| Apache HttpClient 4 | org.apache.httpcomponents | httpclient | Replaced by httpclient5 |

---

## Dependency Change Summary (GroupId Changes)

| Old GroupId | Old ArtifactId | New GroupId | New ArtifactId |
|-------------|----------------|-------------|----------------|
| com.github.tomakehurst | wiremock | org.wiremock | wiremock-standalone |
| com.github.tomakehurst | wiremock-jre8 | org.wiremock | wiremock-standalone |
| com.intuit.karate | karate-junit4 | com.intuit.karate | karate-junit5 |
| javax.servlet | javax.servlet-api | jakarta.servlet | jakarta.servlet-api |
| com.ibm.wmq | mq | com.ibm.mq | com.ibm.mq.jakarta.client |
| com.ibm.wmq | mqjms | com.ibm.mq | com.ibm.mq.jakarta.client |
| org.apache.httpcomponents | httpclient | org.apache.httpcomponents.client5 | httpclient5 |

---

## SDK2 to SDK3 Third-Party Dependency Migration Rules

> **CRITICAL AGENT INSTRUCTIONS:**
> - These dependencies must be **REMOVED** or **MODIFIED** (not just added)
> - If a dependency exists in build.gradle, MODIFY its version/groupId/artifactId
> - Do NOT add duplicate entries - replace the existing entry
> - Check if dependency already exists before adding new entries

### Third-Party Dependencies That MUST BE REMOVED

These dependencies are **completely removed** in SDK3 (managed by Spring Boot 3.x BOM or obsolete):

| SDK2 Dependency (REMOVE) | Reason | Replacement |
|--------------------------|--------|-------------|
| `org.springframework:spring-web` (explicit version) | Managed by Spring Boot BOM | Remove (BOM managed) |
| `org.springframework:spring-core` (explicit version) | Managed by Spring Boot BOM | Remove (BOM managed) |
| `org.springframework:spring-beans` (explicit version) | Managed by Spring Boot BOM | Remove (BOM managed) |
| `org.springframework.boot:spring-boot-starter-web` (explicit version) | Managed by Spring Boot BOM | Remove version (BOM managed) |
| `com.rabbitmq:amqp-client` (old version) | Spring Boot manages version | Remove version (BOM managed) |
| `org.apache.tomcat.embed:tomcat-embed-*` (all) | Managed by Spring Boot | Remove (BOM managed) |
| `org.apache.tomcat:tomcat-annotations-api` | Managed by Spring Boot | Remove (BOM managed) |
| `org.apache.logging.log4j:log4j-*` (all Log4j deps) | Use Logback (Spring Boot default) | Remove all Log4j |
| `org.apache.commons:commons-lang3` | Obsolete utility | Remove (use Java 21 features) |
| `com.github.tomakehurst:wiremock` (old groupId) | Old groupId | Use `org.wiremock:wiremock-standalone:3.13.2` |
| `com.github.tomakehurst:wiremock-jre8` | Java 8 specific | Use `org.wiremock:wiremock-standalone:3.13.2` |
| `com.github.tomakehurst:wiremock-standalone` (old groupId) | Old groupId | Use `org.wiremock:wiremock-standalone:3.13.2` |
| `com.intuit.karate:karate-junit4` | JUnit 4 specific | Use `com.intuit.karate:karate-junit5:1.4.1` |
| `com.intuit.karate:karate-apache` | Obsolete | Remove |
| `com.intuit.karate:karate-testng` | TestNG not used | Remove (or keep if using TestNG) |
| `org.mockito:mockito-all` | Obsolete all-in-one | Use `mockito-core:5.9.0` + `mockito-junit-jupiter:5.9.0` |
| `junit:junit:4.x` | JUnit 4 | Use `org.junit.jupiter:junit-jupiter:5.13.4` |
| `io.rest-assured:rest-assured` (if using Karate) | Duplicate testing | Use Karate or REST Assured, not both |
| `io.rest-assured:json-path` (if using Karate) | Duplicate testing | Use Karate or REST Assured, not both |
| `io.rest-assured:xml-path` (if using Karate) | Duplicate testing | Use Karate or REST Assured, not both |
| `com.mikesamuel:json-sanitizer` (old version) | Security concern | Verify BOM-managed version or remove |
| `org.yaml:snakeyaml` (old version) | Security concern | Verify BOM-managed version or remove |
| `net.sourceforge.htmlunit:htmlunit-core-js` | Obsolete | Remove |
| `net.sourceforge.htmlunit:neko-htmlunit` | Obsolete | Remove |
| `info.cukes:cucumber-core:1.x` | Very old Cucumber | Upgrade to `io.cucumber:cucumber-java:7.x` |

**Agent Action:**
```gradle
// BEFORE (SDK2) - REMOVE all these
implementation 'org.springframework:spring-web:5.3.10'
implementation 'org.apache.logging.log4j:log4j-core:2.17.0'
implementation 'com.github.tomakehurst:wiremock:2.27.2'
implementation 'junit:junit:4.12'

// AFTER (SDK3) - Use BOM or new versions
// Remove above - Spring managed by BOM
testImplementation 'org.wiremock:wiremock-standalone:3.13.2'
testImplementation 'org.junit.jupiter:junit-jupiter:5.13.4'
```

### Third-Party Dependencies That MUST BE MODIFIED

These dependencies exist in SDK2 but require **groupId/artifactId/version changes** for SDK3:

| SDK2 Dependency | SDK3 Dependency | Version | Action |
|-----------------|-----------------|---------|--------|
| `javax.servlet:javax.servlet-api:*` | `jakarta.servlet:jakarta.servlet-api` | `6.0.0` | MODIFY groupId + artifactId |
| `com.github.tomakehurst:wiremock:*` | `org.wiremock:wiremock-standalone` | `3.13.2` | MODIFY groupId + artifactId |
| `com.intuit.karate:karate-junit4:*` | `com.intuit.karate:karate-junit5` | `1.4.1` | MODIFY artifactId |
| `com.oracle.jdbc:ojdbc8:*` | `com.oracle.database.jdbc:ojdbc8` | `18.3.0.0` | MODIFY groupId |
| `com.sun.jersey.contribs:jersey-apache-client4:*` | N/A | N/A | REMOVE (incompatible) |
| `org.apache.httpcomponents:httpclient:*` | `org.apache.httpcomponents.client5:httpclient5` | `5.4.4` | MODIFY groupId + artifactId |
| `com.google.code.gson:gson:<2.10` | `com.google.code.gson:gson` | `2.10.1` | UPGRADE version |
| `com.google.guava:guava:<33.x` | `com.google.guava:guava` | `33.4.7-jre` | UPGRADE version |
| `commons-io:commons-io:<2.16` | `commons-io:commons-io` | `2.16.1` | UPGRADE version |
| `org.apache.commons:commons-collections4:<4.5` | `org.apache.commons:commons-collections4` | `4.5.0` | UPGRADE version |
| `org.apache.commons:commons-text:<1.15` | `org.apache.commons:commons-text` | `1.15.0` | UPGRADE version |
| `org.projectlombok:lombok:<1.18.38` | `org.projectlombok:lombok` | `1.18.38` | UPGRADE version |
| `com.zaxxer:HikariCP:<5.1` | `com.zaxxer:HikariCP` | `5.1.0` | UPGRADE version |
| `org.springframework.cloud:spring-cloud-dependencies:*` | `org.springframework.cloud:spring-cloud-dependencies` | `2023.0.6` | UPGRADE version |
| `org.owasp:dependency-check-gradle:*` | `org.owasp:dependency-check-gradle` | `12.1.9` | UPGRADE version |

**Agent Action:**
```gradle
// BEFORE (SDK2)
implementation 'javax.servlet:javax.servlet-api:3.1.0'
implementation 'com.google.guava:guava:30.1-jre'
testImplementation 'com.intuit.karate:karate-junit4:0.9.6'

// AFTER (SDK3) - MODIFY existing lines
implementation 'jakarta.servlet:jakarta.servlet-api:6.0.0'
implementation 'com.google.guava:guava:33.4.7-jre'
testImplementation 'com.intuit.karate:karate-junit5:1.4.1'
```

### Agent Modification Workflow for Third-Party Dependencies

**When agent encounters existing dependencies:**

```
1. READ build.gradle to check if dependency already exists
2. IF exists:
   a. CHECK against removal list → REMOVE if found
   b. CHECK against modification list → MODIFY groupId/artifactId/version if found
   c. CHECK if version is BOM-managed → REMOVE explicit version
3. IF does not exist:
   a. ADD new dependency with correct coordinates
4. NEVER duplicate dependencies - always replace existing entries
```

### Special Cases

**Spring Boot Dependencies:**
- ALL `org.springframework.*` and `org.springframework.boot.*` should rely on BOM
- Remove explicit versions unless overriding for specific reason
- Document any version overrides with comments

**IBM MQ:**
- Old `com.ibm.wmq:mq` and `com.ibm.wmq:mqjms` → Single `com.ibm.mq:com.ibm.mq.jakarta.client:9.4.4.0`
- Package renames handled automatically by Jakarta EE migration
- See detailed IBM MQ migration guide below

**Testing Frameworks:**
- JUnit 4 → JUnit 5: Change imports, lifecycle annotations, assertions
- Mockito 1.x/3.x → 5.9.0: Significant API changes
- Karate: Update to 1.4.1 for Java 21 compatibility

---

## IBM MQ Jakarta EE Migration (CRITICAL)

### HALLUCINATION CORRECTION

When migrating IBM MQ to Jakarta EE, there are common mistakes. This section documents the **correct** pattern.

### Required Dependencies (BOTH are needed!)

```gradle
// WRONG - Only jakarta.client
testImplementation 'com.ibm.mq:com.ibm.mq.jakarta.client:9.4.4.0'

// CORRECT - BOTH dependencies required
testImplementation 'com.ibm.mq:com.ibm.mq.jakarta.client:9.4.4.0'
testImplementation 'com.ibm.mq:com.ibm.mq.allclient:9.4.4.0'
```

### Correct Package Names

```java
// WRONG - Base package
import com.ibm.mq.jms.MQQueue;
import com.ibm.mq.jms.MQQueueConnectionFactory;

// CORRECT - Jakarta-specific package
import com.ibm.mq.jakarta.jms.MQQueue;
import com.ibm.mq.jakarta.jms.MQQueueConnectionFactory;
import jakarta.jms.JMSException;
import jakarta.jms.QueueConnectionFactory;
```

### Package Migration Patterns

| Old Package (SDK2) | New Package (SDK3) |
|-------------------|-------------------|
| `com.ibm.mq.jms` | `com.ibm.mq.jakarta.jms` |
| `com.ibm.jms` | `com.ibm.jakarta.jms` |
| `com.ibm.msg.client.jms` | `com.ibm.msg.client.jakarta.jms` |

### Dual Exception Handling (Required!)

```java
// WRONG - Single exception type
public QueueConnectionFactory mainframeJmsConnectionFactory() throws JMSException {

// CORRECT - Both exception types
public QueueConnectionFactory mainframeJmsConnectionFactory()
    throws javax.jms.JMSException, jakarta.jms.JMSException {
```

### MQ Configuration Methods (All Work!)

These methods are **NOT deprecated** - do NOT remove them:

```java
connectionFactory.setCCSID(500);
connectionFactory.setMessageRetention(1);       // WORKS - Don't remove
connectionFactory.setMsgBatchSize(10);          // WORKS - Don't remove
connectionFactory.setPollingInterval(5000);     // WORKS - Don't remove
connectionFactory.setSyncpointAllGets(false);   // WORKS - Don't remove
connectionFactory.setUseConnectionPooling(true); // WORKS - Don't remove
```

### Complete Working Example

```java
import com.ibm.mq.jakarta.jms.MQQueue;
import com.ibm.mq.jakarta.jms.MQQueueConnectionFactory;
import jakarta.jms.JMSException;
import jakarta.jms.QueueConnectionFactory;

@Configuration
public class JmsConfig {

    @Bean
    public QueueConnectionFactory mainframeJmsConnectionFactory()
            throws javax.jms.JMSException, JMSException {

        MQQueueConnectionFactory connectionFactory = new MQQueueConnectionFactory();
        connectionFactory.setHostName(mqHost);
        connectionFactory.setPort(mqPort);
        connectionFactory.setChannel(mqChannel);
        connectionFactory.setQueueManager(mqQueueManager);
        connectionFactory.setCCSID(500);
        connectionFactory.setMessageRetention(1);
        connectionFactory.setMsgBatchSize(10);
        connectionFactory.setPollingInterval(5000);
        connectionFactory.setSyncpointAllGets(false);
        connectionFactory.setUseConnectionPooling(true);

        return connectionFactory;
    }
}
```

### Validation

Run `$GRADLE_CMD dependencies --configuration runtimeClasspath` and search the output for `com.ibm.mq`. Expected: Both `jakarta.client` AND `allclient` present.

Use the Grep tool to search for `import com.ibm.mq.jms` in `src/`. Expected: No matches (should be `com.ibm.mq.jakarta.jms`).

---

## Guava Package Migration

### MoreObjects → Objects

| Old Class (SDK2) | New Class (SDK3) | Notes |
|-----------------|------------------|-------|
| `com.google.common.base.MoreObjects` | `com.google.common.base.Objects` | MoreObjects deprecated |

#### Migration Pattern

```java
// SDK2
import com.google.common.base.MoreObjects;
MoreObjects.toStringHelper(this).add("field", value).toString();

// SDK3
import com.google.common.base.Objects;
Objects.toStringHelper(this).add("field", value).toString();

// OR use Java's native toString (recommended for Java 21)
@Override
public String toString() {
    return "MyClass{field=" + value + "}";
}
```

---

## Version Update Commands

To check current dependency versions in your project:

```bash
# List all dependencies with versions
$GRADLE_CMD dependencies --configuration compileClasspath

# Check for dependency updates
$GRADLE_CMD dependencyUpdates
```

---

**Document Version:** 1.1
**Last Updated:** 2026-02-05
**Source:** rewrite.yml and SDK3 migration experience
**Compatibility:** SDK3 1.12.007, Spring Boot 3.3.x, Java 21
