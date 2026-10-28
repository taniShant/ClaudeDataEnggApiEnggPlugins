# Third-Party Dependency Versions - MCA2 JDK Upgrade Reference

> **Cross-Platform Note:** All Gradle commands in this document use `$GRADLE_CMD` instead of `./gradlew`. Validation searches use the Grep tool instead of shell `grep`. See CLAUDE.md Cross-Platform Execution section for details.

> **AGENT ROUTING:** Use this file for **third-party** dependencies only (`org.*`, `com.google.*`, `com.fasterxml.*`, etc.)
>
> For Barclays internal libraries (`com.barclays.*`, `com.barclaycard.*`), use [MCA2 Migration Reference](mca2_migration_reference.md)

**Scope:** Third-party libraries only

## Overview

This document provides a reference for all **third-party** dependency versions required for MCA2 JDK 8→21 upgrade. These versions are validated for compatibility with Spring Boot 3.5+.x and Java 21.

---

## Spring Framework Dependencies

| Dependency | GroupId | ArtifactId | Java 21 / SB 3.3 Version | Notes |
|------------|---------|------------|--------------------------|-------|
| Spring Boot Parent | org.springframework.boot | spring-boot-starter-parent | 3.5.x (search Nexus for latest) | BOM — manages most Spring deps |
| Spring Cloud BOM | org.springframework.cloud | spring-cloud-dependencies | 2023.0.6 | Must match Spring Boot 3.5+ |
| Spring Cloud Function | org.springframework.cloud | spring-cloud-function-context | 4.2.2 | Cloud functions |
| Spring WS Core | org.springframework.ws | spring-ws-core | 4.1.0 | Web services |
| Spring XML | org.springframework.xml | spring-xml | 4.1.0 | XML processing |
| Spring JDBC | org.springframework | spring-jdbc | 6.2.5 | JDBC support |
| SpringDoc OpenAPI | org.springdoc | springdoc-openapi-starter-webmvc-ui | 2.2.0 | Replaces springfox |

---

## Testing Dependencies

| Dependency | GroupId | ArtifactId | Java 21 / SB 3.3 Version |
|------------|---------|------------|--------------------------|
| JUnit Jupiter | org.junit.jupiter | junit-jupiter | 5.11.3 |
| JUnit Platform Launcher | org.junit.platform | junit-platform-launcher | 1.11.3 |
| Mockito Core | org.mockito | mockito-core | 5.14.2 |
| Mockito JUnit 5 | org.mockito | mockito-junit-jupiter | 5.14.2 |
| WireMock Standalone | org.wiremock | wiremock-standalone | 3.13.2 |
| Karate JUnit 5 | com.intuit.karate | karate-junit5 | 1.4.1 |
| Karate Core | com.intuit.karate | karate-core | 1.4.1 |
| AssertJ | org.assertj | assertj-core | 3.24.2 |
| H2 Database | com.h2database | h2 | 2.2.220 |

---

## Common Library Dependencies

| Dependency | GroupId | ArtifactId | Java 21 / SB 3.3 Version |
|------------|---------|------------|--------------------------|
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

| Dependency | GroupId | ArtifactId | Java 21 / SB 3.3 Version |
|------------|---------|------------|--------------------------|
| Jakarta Servlet API | jakarta.servlet | jakarta.servlet-api | 6.0.0 |
| Jakarta XML WS API | jakarta.xml.ws | jakarta.xml.ws-api | 4.0.2 |
| Jakarta Validation API | jakarta.validation | jakarta.validation-api | BOM managed |

---

## XML/JAXB Dependencies

| Dependency | GroupId | ArtifactId | Java 21 / SB 3.3 Version |
|------------|---------|------------|--------------------------|
| JAXB XJC | org.glassfish.jaxb | jaxb-xjc | 4.0.3 |
| JAXB Impl | com.sun.xml.bind | jaxb-impl | 4.0.3 |
| JAXB Core | com.sun.xml.bind | jaxb-core | 4.0.3 |

---

## Database Dependencies

| Dependency | GroupId | ArtifactId | Java 21 / SB 3.3 Version |
|------------|---------|------------|--------------------------|
| Oracle JDBC | com.oracle.database.jdbc | ojdbc8 | 18.3.0.0 |
| H2 Database | com.h2database | h2 | 2.2.220 |
| PostgreSQL Driver | org.postgresql | postgresql | 42.6.x+ |
| Flyway | org.flywaydb | flyway-core | 9.x+ |

---

## Messaging Dependencies

| Dependency | GroupId | ArtifactId | Java 21 / SB 3.3 Version |
|------------|---------|------------|--------------------------|
| IBM MQ Jakarta Client | com.ibm.mq | com.ibm.mq.jakarta.client | 9.4.4.0 |
| IBM MQ All Client | com.ibm.mq | com.ibm.mq.allclient | 9.4.4.0 |

---

## Build Tool Dependencies

| Dependency | GroupId | ArtifactId | Java 21 / SB 3.3 Version |
|------------|---------|------------|--------------------------|
| OWASP Dependency Check | org.owasp | dependency-check-gradle | 12.1.9 |
| PIT Mutation Testing | info.solidsoft.pitest | info.solidsoft.pitest.gradle.plugin | 1.15.0 |
| JaCoCo | org.jacoco | jacoco | 0.8.14 |

---

## Dependencies to REMOVE (Java 8 / SB 2.7 Only)

These dependencies are NOT compatible with Java 21 / Spring Boot 3.5+ and must be removed:

| Dependency (REMOVE) | GroupId | ArtifactId | Reason | Replacement |
|---------------------|---------|------------|--------|-------------|
| JUnit 4 | junit | junit | Replaced by JUnit 5 | `org.junit.jupiter:junit-jupiter:5.11.3` |
| Mockito All | org.mockito | mockito-all | Obsolete all-in-one | `mockito-core:5.14.2` + `mockito-junit-jupiter:5.14.2` |
| WireMock (old groupId) | com.github.tomakehurst | wiremock | Old groupId | `org.wiremock:wiremock-standalone:3.13.2` |
| WireMock JRE8 | com.github.tomakehurst | wiremock-jre8 | Java 8 specific | `org.wiremock:wiremock-standalone:3.13.2` |
| WireMock Standalone (old) | com.github.tomakehurst | wiremock-standalone | Old groupId | `org.wiremock:wiremock-standalone:3.13.2` |
| Karate JUnit 4 | com.intuit.karate | karate-junit4 | JUnit 4 specific | `karate-junit5:1.4.1` |
| Karate Apache | com.intuit.karate | karate-apache | Obsolete | Remove |
| IBM MQ (old) | com.ibm.wmq | mq | Jakarta migration | `com.ibm.mq:com.ibm.mq.jakarta.client:9.4.4.0` |
| IBM MQ JMS (old) | com.ibm.wmq | mqjms | Jakarta migration | `com.ibm.mq:com.ibm.mq.jakarta.client:9.4.4.0` |
| Log4j SLF4J Impl | org.apache.logging.log4j | log4j-slf4j-impl | SB 3.3 uses Logback | Remove |
| Log4j API | org.apache.logging.log4j | log4j-api | SB 3.3 uses Logback | Remove |
| Log4j Core | org.apache.logging.log4j | log4j-core | SB 3.3 uses Logback | Remove |
| Log4j Web | org.apache.logging.log4j | log4j-web | SB 3.3 uses Logback | Remove |
| Apache HttpClient 4 | org.apache.httpcomponents | httpclient | Replaced by HttpClient 5 or JDK HttpClient | `httpclient5:5.4.4` or JDK `java.net.http.HttpClient` |
| javax.servlet API | javax.servlet | javax.servlet-api | javax replaced by jakarta | `jakarta.servlet:jakarta.servlet-api:6.0.0` |
| Rest Assured (if using Karate) | io.rest-assured | rest-assured | Duplicate testing | Use Karate or REST Assured, not both |
| Jersey (old) | com.sun.jersey | jersey-* | Incompatible with SB 3.3 | Use Spring MVC / WebFlux |
| Springfox Swagger | io.springfox | springfox-* | Incompatible with SB 3.3 | `org.springdoc:springdoc-openapi-starter-webmvc-ui:2.2.0` |
| Tomcat Embed (explicit) | org.apache.tomcat.embed | tomcat-embed-* | BOM managed | Remove explicit version |
| SnakeYAML (explicit) | org.yaml | snakeyaml | BOM managed | Remove explicit version |

**Agent Action:**
```gradle
// BEFORE (Java 8 / SB 2.7) — REMOVE all these
testImplementation 'junit:junit:4.12'
testImplementation 'com.github.tomakehurst:wiremock:2.27.2'
implementation 'org.apache.logging.log4j:log4j-core:2.17.0'
implementation 'javax.servlet:javax.servlet-api:3.1.0'

// AFTER (Java 21 / SB 3.3) — Use new versions
testImplementation 'org.junit.jupiter:junit-jupiter:5.11.3'
testImplementation 'org.wiremock:wiremock-standalone:3.13.2'
// Log4j removed — Logback is Spring Boot default
implementation 'jakarta.servlet:jakarta.servlet-api:6.0.0'
```

---

## Dependencies to MODIFY (GroupId/ArtifactId/Version Changes)

These dependencies exist in Java 8 / SB 2.7 projects but require changes for Java 21 / SB 3.3:

| Old Dependency | New Dependency | Version | Action |
|---------------|---------------|---------|--------|
| `javax.servlet:javax.servlet-api:*` | `jakarta.servlet:jakarta.servlet-api` | `6.0.0` | MODIFY groupId + artifactId |
| `com.github.tomakehurst:wiremock:*` | `org.wiremock:wiremock-standalone` | `3.13.2` | MODIFY groupId + artifactId |
| `com.intuit.karate:karate-junit4:*` | `com.intuit.karate:karate-junit5` | `1.4.1` | MODIFY artifactId |
| `com.oracle.jdbc:ojdbc8:*` | `com.oracle.database.jdbc:ojdbc8` | `18.3.0.0` | MODIFY groupId |
| `org.apache.httpcomponents:httpclient:*` | `org.apache.httpcomponents.client5:httpclient5` | `5.4.4` | MODIFY groupId + artifactId |
| `com.ibm.wmq:mq:*` | `com.ibm.mq:com.ibm.mq.jakarta.client` | `9.4.4.0` | MODIFY groupId + artifactId |
| `com.ibm.wmq:mqjms:*` | `com.ibm.mq:com.ibm.mq.jakarta.client` | `9.4.4.0` | MODIFY groupId + artifactId |
| `com.google.guava:guava:<33.x` | `com.google.guava:guava` | `33.4.7-jre` | UPGRADE version |
| `com.google.code.gson:gson:<2.10` | `com.google.code.gson:gson` | `2.10.1` | UPGRADE version |
| `commons-io:commons-io:<2.16` | `commons-io:commons-io` | `2.16.1` | UPGRADE version |
| `org.projectlombok:lombok:<1.18.30` | `org.projectlombok:lombok` | `1.18.38` | UPGRADE version |
| `io.springfox:springfox-*:*` | `org.springdoc:springdoc-openapi-starter-webmvc-ui` | `2.2.0` | REPLACE entirely |

**Agent Action:**
```gradle
// BEFORE (Java 8 / SB 2.7)
implementation 'javax.servlet:javax.servlet-api:3.1.0'
implementation 'com.google.guava:guava:30.1-jre'
testImplementation 'com.intuit.karate:karate-junit4:0.9.6'

// AFTER (Java 21 / SB 3.3) — MODIFY existing lines
implementation 'jakarta.servlet:jakarta.servlet-api:6.0.0'
implementation 'com.google.guava:guava:33.4.7-jre'
testImplementation 'com.intuit.karate:karate-junit5:1.4.1'
```

---

## Dependency Change Summary (GroupId Changes)

| Old GroupId | Old ArtifactId | New GroupId | New ArtifactId |
|-------------|----------------|-------------|----------------|
| com.github.tomakehurst | wiremock / wiremock-jre8 | org.wiremock | wiremock-standalone |
| com.intuit.karate | karate-junit4 | com.intuit.karate | karate-junit5 |
| javax.servlet | javax.servlet-api | jakarta.servlet | jakarta.servlet-api |
| com.ibm.wmq | mq / mqjms | com.ibm.mq | com.ibm.mq.jakarta.client |
| org.apache.httpcomponents | httpclient | org.apache.httpcomponents.client5 | httpclient5 |
| io.springfox | springfox-* | org.springdoc | springdoc-openapi-starter-webmvc-ui |

---

## Agent Modification Workflow for Third-Party Dependencies

**When agent encounters existing dependencies:**

```
1. READ build.gradle to check if dependency already exists
2. IF exists:
   a. CHECK against removal list → REMOVE if found
   b. CHECK against modification list → MODIFY groupId/artifactId/version if found
   c. CHECK if version is BOM-managed → REMOVE explicit version
3. IF does not exist AND is needed:
   a. ADD new dependency with correct coordinates
4. NEVER duplicate dependencies — always replace existing entries
```

### Special Cases

**Spring Boot Dependencies:**
- ALL `org.springframework.*` and `org.springframework.boot.*` should rely on BOM
- Remove explicit versions unless overriding for specific reason
- Document any version overrides with comments

**BOM-Managed Dependencies (remove explicit versions):**
- Jackson (`com.fasterxml.jackson.*`)
- Hibernate (`org.hibernate.*`)
- Tomcat (`org.apache.tomcat.embed.*`)
- SnakeYAML (`org.yaml:snakeyaml`)
- SLF4J (`org.slf4j:*`)
- Logback (`ch.qos.logback:*`)

---

## IBM MQ Jakarta EE Migration (CRITICAL)

### Required Dependencies (BOTH are needed!)

```gradle
// WRONG — Only jakarta.client
testImplementation 'com.ibm.mq:com.ibm.mq.jakarta.client:9.4.4.0'

// CORRECT — BOTH dependencies required
testImplementation 'com.ibm.mq:com.ibm.mq.jakarta.client:9.4.4.0'
testImplementation 'com.ibm.mq:com.ibm.mq.allclient:9.4.4.0'
```

### Correct Package Names

```java
// WRONG — Old javax packages
import com.ibm.mq.jms.MQQueue;
import com.ibm.mq.jms.MQQueueConnectionFactory;

// CORRECT — Jakarta-specific packages
import com.ibm.mq.jakarta.jms.MQQueue;
import com.ibm.mq.jakarta.jms.MQQueueConnectionFactory;
import jakarta.jms.JMSException;
import jakarta.jms.QueueConnectionFactory;
```

### Package Migration Patterns

| Old Package (Java 8) | New Package (Java 21) |
|----------------------|----------------------|
| `com.ibm.mq.jms` | `com.ibm.mq.jakarta.jms` |
| `com.ibm.jms` | `com.ibm.jakarta.jms` |
| `com.ibm.msg.client.jms` | `com.ibm.msg.client.jakarta.jms` |

### Dual Exception Handling (Required!)

```java
// WRONG — Single exception type
public QueueConnectionFactory factory() throws JMSException {

// CORRECT — Both exception types during migration
public QueueConnectionFactory factory()
    throws javax.jms.JMSException, jakarta.jms.JMSException {
```

### MQ Configuration Methods (All Work!)

These methods are **NOT deprecated** — do NOT remove them:

```java
connectionFactory.setCCSID(500);
connectionFactory.setMessageRetention(1);
connectionFactory.setMsgBatchSize(10);
connectionFactory.setPollingInterval(5000);
connectionFactory.setSyncpointAllGets(false);
connectionFactory.setUseConnectionPooling(true);
```

### Validation

Run `$GRADLE_CMD dependencies --configuration runtimeClasspath` and search the output for `com.ibm.mq`. Expected: Both `jakarta.client` AND `allclient` present.

Use the Grep tool to search for `import com.ibm.mq.jms` in `src/`. Expected: No matches (should be `com.ibm.mq.jakarta.jms`).

---

## Guava Migration Notes

### MoreObjects → Objects

```java
// Java 8 / SB 2.7
import com.google.common.base.MoreObjects;
MoreObjects.toStringHelper(this).add("field", value).toString();

// Java 21 / SB 3.3 — Option 1: Updated Guava
import com.google.common.base.Objects;
Objects.toStringHelper(this).add("field", value).toString();

// Java 21 / SB 3.3 — Option 2: Java native (recommended)
@Override
public String toString() {
    return "MyClass{field=" + value + "}";
}
```

---

## Springfox → SpringDoc Migration

Springfox is incompatible with Spring Boot 3.x. Replace with SpringDoc.

### Dependencies

```gradle
// REMOVE (Java 8 / SB 2.7)
implementation 'io.springfox:springfox-boot-starter:3.0.0'
implementation 'io.springfox:springfox-swagger-ui:3.0.0'

// ADD (Java 21 / SB 3.3)
implementation 'org.springdoc:springdoc-openapi-starter-webmvc-ui:2.2.0'
```

### Annotations

```java
// REMOVE — Springfox annotations
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;

// ADD — SpringDoc/OpenAPI annotations
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
```

### Configuration

```java
// REMOVE — Springfox Docket
@Bean
public Docket api() { ... }

// ADD — SpringDoc configuration (usually just properties)
// application.properties:
// springdoc.api-docs.path=/v3/api-docs
// springdoc.swagger-ui.path=/swagger-ui.html
```

---

## Version Update Commands

To check current dependency versions in your project:

```bash
$GRADLE_CMD dependencies --configuration compileClasspath
$GRADLE_CMD dependencies --configuration runtimeClasspath
$GRADLE_CMD dependencies --configuration testCompileClasspath
```

---

**Document Version:** 1.0
**Last Updated:** 2026-02-19
**Compatibility:** Spring Boot 3.5+.x, Java 21
**Document Type:** Agent-Optimized MCA2 JDK Upgrade Reference
