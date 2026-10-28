---
name: sdk3-sdk4-migration
description: Complete migration guide for uplifting Barclays iAPI projects from SDK3 (Spring Boot 3.5.x, Java 21) to SDK4 (Spring Boot 4.1.x). Covers OpenRewrite automation, Jackson 3 breaking changes, ObjectMapper immutability, RestClient HTTP method changes, WebConfig strict path matching, Karate JSON case sensitivity, WireMock timestamp format, and bootstrap property migration. Use when uplifting an existing SDK3 API to Spring Boot 4.1.x.
owner: Barclays AI (barclaysai@barclays.com)
version: 1.0.0
license: Proprietary. For Barclays internal use only.
user-invocable: false
source: barclays-claude-code-plugins/plugins/migration/barclays-buk-smesh-api-maintainer/skills/sdk3-sdk4-migration/SKILL.md
review-trigger: When SDK4 BOM or Spring Boot 4.x introduces additional breaking changes or new migration patterns are identified from consuming API projects
status: Full
---

# SDK3 to SDK4 Migration Guide

## Overview

This guide covers all **source code and configuration changes** required to uplift a Barclays iAPI project from SDK3 (Spring Boot 3.5.x) to SDK4 (Spring Boot 4.1.x).

**For Gradle and build configuration changes**, see [sdk3-sdk4-gradle SKILL.md](../sdk3-sdk4-gradle/SKILL.md).

**Prerequisites:**
- API is already on SDK3 (Java 21, Spring Boot 3.5.x, `SDK3_VERSION` in `gradle.properties`)
- `sourceCompatibility = JavaVersion.VERSION_1_8` must NOT be present — that indicates SDK2
- Direct uplift from SDK2 to SDK4 is not supported; migrate to SDK3 first

---

## Step 1: Run OpenRewrite First

Before making any manual changes, run the OpenRewrite recipe. It handles most boilerplate automatically:

```bash
gradlew.bat --init-script init.gradle rewriteRun   # Windows
./gradlew --init-script init.gradle rewriteRun      # Linux/macOS
```

See [sdk3-sdk4-gradle SKILL.md](../sdk3-sdk4-gradle/SKILL.md) Step 1 for the full `init.gradle` content and Nexus coordinates.

After OpenRewrite runs, attempt compilation and work through the manual fixes below for anything it did not handle.

---

## Step 2: Jackson 3 — Breaking Changes

Jackson has a **new major version (3.x) and a new group ID** (`tools.jackson` replaces `com.fasterxml.jackson`). OpenRewrite does **not** fully handle all Jackson 3 breaking changes.

### 2.1 Replace `JsonProcessingException` with `JacksonException`

OpenRewrite does **not** replace this. Search the entire codebase and replace manually:

```bash
grep -rn "JsonProcessingException" src/ --include="*.java"
```

```java
// Before
import com.fasterxml.jackson.core.JsonProcessingException;

public String serialize(Object obj) throws JsonProcessingException {
    return objectMapper.writeValueAsString(obj);
}
```

```java
// After
import tools.jackson.core.JacksonException;

public String serialize(Object obj) throws JacksonException {
    return objectMapper.writeValueAsString(obj);
}
```

Also update catch blocks:

```java
// Before
try {
    return objectMapper.writeValueAsString(obj);
} catch (JsonProcessingException e) {
    log.error("Serialisation failed", e);
}

// After
try {
    return objectMapper.writeValueAsString(obj);
} catch (JacksonException e) {
    log.error("Serialisation failed", e);
}
```

### 2.2 ObjectMapper is now immutable after creation

In Jackson 3, `ObjectMapper` is **immutable once created**. Any code that creates an `ObjectMapper` and then calls configuration methods on it (`.configure(...)`, `.setSerializationInclusion(...)`, `.registerModule(...)`) will fail at runtime.

**Pattern: Use the builder instead.**

```java
// Before — configure after construction (BROKEN in Jackson 3)
ObjectMapper objectMapper = new ObjectMapper();
objectMapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
objectMapper.setSerializationInclusion(JsonInclude.Include.NON_NULL);
objectMapper.registerModule(new JavaTimeModule());
```

```java
// After — configure via builder
import tools.jackson.databind.json.JsonMapper;
import tools.jackson.databind.DeserializationFeature;
import tools.jackson.annotation.JsonInclude;
import tools.jackson.datatype.jsr310.JavaTimeModule;

JsonMapper objectMapper = JsonMapper.builder()
    .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false)
    .serializationInclusion(JsonInclude.Include.NON_NULL)
    .addModule(new JavaTimeModule())
    .build();
```

### 2.3 Spring Boot 4 prefers JsonMapper — update ObjectMapperUtil

If the project has an `ObjectMapperUtil` or similar utility class that returns `ObjectMapper`, update its return type to `JsonMapper`:

```java
// Before
import com.fasterxml.jackson.databind.ObjectMapper;

public class ObjectMapperUtil {
    public static ObjectMapper createObjectMapper() {
        ObjectMapper mapper = new ObjectMapper();
        mapper.registerModule(new JavaTimeModule());
        mapper.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
        return mapper;
    }
}
```

```java
// After
import tools.jackson.databind.json.JsonMapper;
import tools.jackson.datatype.jsr310.JavaTimeModule;
import tools.jackson.databind.SerializationFeature;

public class ObjectMapperUtil {
    public static JsonMapper createObjectMapper() {
        return JsonMapper.builder()
            .addModule(new JavaTimeModule())
            .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS)
            .build();
    }
}
```

### 2.4 ObjectMapper bean in InternalApiInitializerConfig

Spring Boot 4 requires the `ObjectMapper` bean to be a `JsonMapper`. If the project's initializer config declares an `ObjectMapper` bean, update it and add the `"objectMapper"` qualifier where it is autowired:

```java
// Before — in InternalApiInitializerConfig or equivalent
@Bean
public ObjectMapper objectMapper() {
    ObjectMapper mapper = new ObjectMapper();
    mapper.registerModule(new JavaTimeModule());
    return mapper;
}
```

```java
// After
import tools.jackson.databind.json.JsonMapper;

@Bean
public JsonMapper objectMapper() {
    return JsonMapper.builder()
        .addModule(new JavaTimeModule())
        .build();
}
```

Autowiring sites that inject `ObjectMapper` must add the qualifier if there are multiple candidates:

```java
// Before
@Autowired
private ObjectMapper objectMapper;

// After
@Autowired
@Qualifier("objectMapper")
private JsonMapper objectMapper;
```

### 2.5 @JsonInclude(Include.NON_EMPTY) behaviour change — error responses

Jackson 3 changed how `@JsonInclude(Include.NON_EMPTY)` handles `null` vs empty collections. In error responses, a `data` field that was previously excluded may now be included (or vice versa).

**Fix pattern:** Explicitly return `null` instead of an empty collection from `getErrors()` and similar methods so Jackson correctly excludes the field:

```java
// Before — returned empty list (worked in Jackson 2, broken in Jackson 3)
public List<Error> getErrors() {
    return errors != null ? errors : Collections.emptyList();
}

// After — return null so NON_EMPTY excludes it
public List<Error> getErrors() {
    return errors;  // null is excluded by @JsonInclude(NON_EMPTY) in Jackson 3
}
```

Also ensure the `data` field is not returned with error responses. Add a `dataFilter` or conditional logic:

```java
// Example: ensure data is null on error responses
@JsonInclude(JsonInclude.Include.NON_EMPTY)
public Object getData() {
    return hasErrors() ? null : data;
}
```

### 2.6 JSON annotations now stricter — DTO ordering

Jackson 3 enforces stricter ordering for JSON annotations, which may change the serialisation order of DTO fields compared to Jackson 2. Review response DTOs against the API contract and add `@JsonPropertyOrder` where field order must be deterministic:

```java
// Before — relied on insertion order (worked by chance in Jackson 2)
public class AccountResponse {
    private String accountId;
    private String sortCode;
    private BigDecimal balance;
}

// After — explicit order declared
@JsonPropertyOrder({"accountId", "sortCode", "balance"})
public class AccountResponse {
    private String accountId;
    private String sortCode;
    private BigDecimal balance;
}
```

---

## Step 3: RestClient HTTP Method Change

`RestClientHttpMethod` has been replaced by the standard Spring `HttpMethod` in REST client calls.

```bash
grep -rn "RestClientHttpMethod" src/ --include="*.java"
```

```java
// Before
import com.barclays.api.bap.bld.lib.restclient.RestClientHttpMethod;

ResponseEntity<String> response = restApiClient.call(
    RestClientHttpMethod.GET,
    URI.create(url),
    headers,
    String.class
);
```

```java
// After
import org.springframework.http.HttpMethod;

ResponseEntity<String> response = restApiClient.call(
    HttpMethod.GET,
    URI.create(url),
    headers,
    String.class
);
```

Apply the same replacement for all HTTP methods (`POST`, `PUT`, `PATCH`, `DELETE`).

---

## Step 4: Remove configurePathMatch from WebConfig

Spring Boot 4 enforces strict endpoint path matching. Overriding `configurePathMatch` to allow trailing/leading slash ambiguity is no longer supported and will cause a startup error.

```bash
grep -rn "configurePathMatch" src/ --include="*.java"
```

```java
// Before — REMOVE this entire method
@Configuration
public class WebConfig implements WebMvcConfigurer {

    @Override
    public void configurePathMatch(PathMatchConfigurer configurer) {
        configurer.setUseTrailingSlashMatch(true);  // No longer supported
    }
}
```

```java
// After — delete the configurePathMatch method entirely
// If WebConfig has no other content, delete the class too.
@Configuration
public class WebConfig implements WebMvcConfigurer {
    // configurePathMatch removed — Spring Boot 4 enforces strict matching
}
```

If the project has integration tests or Karate tests that call endpoints with a trailing slash, those test paths will also need updating to match the exact registered path.

---

## Step 5: Bootstrap Properties Migration

Spring Boot 4 does not load `bootstrap.yml` / `bootstrap.properties` by default. A temporary fix is adding the `spring-cloud-starter-bootstrap` dependency (see [sdk3-sdk4-gradle SKILL.md](../sdk3-sdk4-gradle/SKILL.md) Step 5). The permanent fix is migrating the bootstrap content to `application.yaml`.

**Temporary fix (add dependency):** Defer full migration.

**Permanent fix:** Move all properties from `bootstrap.yml` to `application.yaml`:

```yaml
# bootstrap.yml (to be removed)
spring:
  application:
    name: my-api
  cloud:
    config:
      uri: http://config-server:8888
      fail-fast: true
```

```yaml
# application.yaml (add these sections)
spring:
  application:
    name: my-api
  cloud:
    config:
      uri: http://config-server:8888
      fail-fast: true
```

---

## Step 6: Karate Integration Tests — JSON Case Sensitivity

Karate's JSON matching is now **case sensitive** in the version bundled with Spring Boot 4. Tests that previously passed due to case-insensitive matching may now fail.

**Search for Karate feature files with potentially case-mismatched assertions:**

```bash
grep -rn "match" src/test --include="*.feature" | grep -i "status\|type\|message"
```

Example fix for a common case — HTTP status string values:

```gherkin
# Before — worked because matching was case-insensitive
* match response.status == 'success'

# After — must exactly match the JSON value the API returns
* match response.status == 'SUCCESS'
```

Review all `match` assertions in `.feature` files and align the expected values exactly with what the API produces.

---

## Step 7: WireMock Stub Timestamps

WireMock stubs now require timestamps in `000Z` UTC format. The `+00:00` offset format used in SDK3 stubs will cause matching failures.

```bash
grep -rn "+00:00\|+0000" src/test --include="*.json" --include="*.yaml"
```

```json
// Before — WireMock stub response body
{
  "createdAt": "2024-01-15T10:30:00+00:00",
  "updatedAt": "2024-01-15T10:30:00+0000"
}

// After — use 000Z format
{
  "createdAt": "2024-01-15T10:30:00.000Z",
  "updatedAt": "2024-01-15T10:30:00.000Z"
}
```

Also update Karate `match` assertions that compare timestamp values:

```gherkin
# Before
* match response.createdAt == '2024-01-15T10:30:00+00:00'

# After
* match response.createdAt == '2024-01-15T10:30:00.000Z'
```

---

## Step 8: Jackson Import Migration

Update all Jackson imports across the codebase from `com.fasterxml.jackson` to `tools.jackson`. OpenRewrite handles many of these, but verify coverage:

```bash
grep -rn "com.fasterxml.jackson" src/ --include="*.java"
```

Common replacements:

| Before (com.fasterxml.jackson) | After (tools.jackson) |
|---|---|
| `com.fasterxml.jackson.core.JsonProcessingException` | `tools.jackson.core.JacksonException` |
| `com.fasterxml.jackson.databind.ObjectMapper` | `tools.jackson.databind.ObjectMapper` (or `JsonMapper`) |
| `com.fasterxml.jackson.databind.json.JsonMapper` | `tools.jackson.databind.json.JsonMapper` |
| `com.fasterxml.jackson.databind.DeserializationFeature` | `tools.jackson.databind.DeserializationFeature` |
| `com.fasterxml.jackson.databind.SerializationFeature` | `tools.jackson.databind.SerializationFeature` |
| `com.fasterxml.jackson.annotation.JsonInclude` | `tools.jackson.annotation.JsonInclude` |
| `com.fasterxml.jackson.annotation.JsonProperty` | `tools.jackson.annotation.JsonProperty` |
| `com.fasterxml.jackson.annotation.JsonPropertyOrder` | `tools.jackson.annotation.JsonPropertyOrder` |
| `com.fasterxml.jackson.annotation.JsonIgnore` | `tools.jackson.annotation.JsonIgnore` |
| `com.fasterxml.jackson.datatype.jsr310.JavaTimeModule` | `tools.jackson.datatype.jsr310.JavaTimeModule` |
| `com.fasterxml.jackson.core.type.TypeReference` | `tools.jackson.core.type.TypeReference` |

---

## Step 9: Compile, Test, and Validate

Work through the build in phases — fix each gate before proceeding:

```bash
# 1. Compile main sources
gradlew.bat compileJava -x barclaysApiGenerate

# 2. Compile test sources
gradlew.bat compileTestJava -x barclaysApiGenerate

# 3. Run unit tests
gradlew.bat test -x barclaysApiGenerate

# 4. Run integration tests
gradlew.bat integrationTest -x barclaysApiGenerate

# 5. Run checkstyle
gradlew.bat checkstyleMain
```

---

## Common Pitfalls

### Pitfall 1: `JsonProcessingException` symbol not found

```
error: cannot find symbol: class JsonProcessingException
  location: package com.fasterxml.jackson.core
```

**Fix:** Replace with `tools.jackson.core.JacksonException` — see Step 2.1.

### Pitfall 2: ObjectMapper configuration fails at runtime

```
UnsupportedOperationException: Cannot change configuration of immutable ObjectMapper
```

**Fix:** Migrate to `JsonMapper.builder()` — see Step 2.2.

### Pitfall 3: RestClientHttpMethod not found

```
error: cannot find symbol: variable RestClientHttpMethod
```

**Fix:** Replace with `org.springframework.http.HttpMethod` — see Step 3.

### Pitfall 4: Application fails to start — ambiguous handler mapping

```
IllegalStateException: Ambiguous handler methods mapped for '/my-endpoint'
```

**Fix:** Remove `configurePathMatch` override from WebConfig — see Step 4.

### Pitfall 5: Bootstrap properties not loaded

```
IllegalArgumentException: Could not resolve placeholder 'spring.application.name'
```

**Fix:** Add `spring-cloud-starter-bootstrap` or migrate to `application.yaml` — see Step 5 and [sdk3-sdk4-gradle SKILL.md](../sdk3-sdk4-gradle/SKILL.md) Step 5.

### Pitfall 6: Karate tests fail with `AssertionError` on previously passing assertions

**Cause:** JSON string matching is now case-sensitive.

**Fix:** Align expected values in `.feature` files to the exact casing the API returns — see Step 6.

### Pitfall 7: WireMock stubs not matching

**Cause:** Timestamp format changed from `+00:00` to `000Z`.

**Fix:** Update all stub JSON files and Karate assertions — see Step 7.

### Pitfall 8: Empty error response includes `data: null`

**Cause:** `@JsonInclude(NON_EMPTY)` behaviour changed in Jackson 3 — `null` is no longer treated the same as empty.

**Fix:** Return `null` explicitly from `getErrors()` and add `dataFilter` logic — see Step 2.5.

---

## Migration Checklist

| # | Step | Handled by OpenRewrite? |
|---|---|---|
| 1 | Run `rewriteRun` with `UpgradeSpringBoot_4_0` recipe | — (this IS the automated step) |
| 2 | Update Gradle wrapper to 8.14 | No |
| 3 | Replace `SDK3_VERSION` / BOM with `SDK4_VERSION` / `sdk4` | No |
| 4 | Replace `com.fasterxml.jackson` → `tools.jackson` imports | Partial |
| 5 | Replace `JsonProcessingException` → `JacksonException` | **No** |
| 6 | Migrate `ObjectMapper` construction to `JsonMapper.builder()` | **No** |
| 7 | Update `ObjectMapperUtil` return type to `JsonMapper` | **No** |
| 8 | Add `@Qualifier("objectMapper")` where autowired | **No** |
| 9 | Replace `RestClientHttpMethod` → `HttpMethod` | **No** |
| 10 | Remove `configurePathMatch` from WebConfig | **No** |
| 11 | Add `spring-cloud-starter-bootstrap` (if using bootstrap) | **No** |
| 12 | Fix `@JsonInclude(NON_EMPTY)` null/empty handling in DTOs | **No** |
| 13 | Fix DTO `@JsonPropertyOrder` for strict Jackson 3 ordering | **No** |
| 14 | Fix Karate assertions for case-sensitive JSON matching | **No** |
| 15 | Fix WireMock stub timestamps to `000Z` format | **No** |
| 16 | Compile `compileJava`, fix errors | — |
| 17 | Compile `compileTestJava`, fix errors | — |
| 18 | Run `test`, fix failures | — |
| 19 | Run `integrationTest`, fix failures | — |

## Related Skills

- [sdk3-sdk4-gradle](../sdk3-sdk4-gradle/SKILL.md) — Gradle and build configuration changes (Gradle 8.14, BOM, dependency versions)
- [sdk2-sdk3-migration](../sdk2-sdk3-migration/SKILL.md) — Prerequisite migration path from SDK2
