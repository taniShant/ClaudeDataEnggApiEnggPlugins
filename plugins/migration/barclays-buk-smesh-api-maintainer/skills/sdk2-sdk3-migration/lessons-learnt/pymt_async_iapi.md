# Lessons Learned - SDK2 to SDK3 Migration

**Project:** pymt-async-iapi
**JIRA:** ELECPAYAPI-7245
**Migration:** SDK2 (Java 8, Gradle 7.2, Spring Boot 2.x) → SDK3 (Java 21, Gradle 8.13, BOM 1.11.015)
**Date:** February 2026

---

## 1. ⚠️ `ext.jacocoCoverageExclusions` Must Be Declared BEFORE `apply plugin`

**Issue:** JaCoCo coverage gate always failed despite correct exclusion configuration.

**Root cause:** `bap-bld-lib-plugin` reads `ext.jacocoCoverageExclusions` synchronously during `apply()`. If the property is declared after the `apply plugin` line, it is silently ignored — no error, no warning, just zero exclusions applied.

**Fix:**
```gradle
// ✅ MUST come BEFORE apply plugin
ext.jacocoCoverageExclusions = project.findProperty('jacocoCoverageExclusions') ?: ''

apply plugin: 'com.barclays.api.bap-bld-lib-plugin'
```

---

## 2. meanbean — Use 2.0.3, Not 3.0.0-M9

**Issue:** `meanbean:3.0.0-M9` is a milestone release not available in Barclays Nexus.

**Fix:** Pin `meanbean` to `2.0.3`:
```gradle
testImplementation "com.github.meanbeanlib:meanbean:2.0.3"
```
The 2.x `BeanTester` and `ConfigurationBuilder` API is fully compatible with typical bean-testing patterns.

---

## 3. DISABLE_OAS_GENERATION for Projects with Pre-Committed OAS

**Issue:** `bap-bld-lib-plugin` registers a `barclaysApiGenerate` task that throws `NullPointerException` during `integrationTest` if `root.spec.url` property is not set.

**Fix:** Add to `gradle.properties`:
```properties
DISABLE_OAS_GENERATION=true
```

Use this when OAS files are already committed and code generation from spec is not required at build time.

---

## 4. RAML → OAS `application.properties` Migration

Projects using RAML validation have SDK2-specific properties that must be replaced.

**Remove (SDK2):**
```properties
ramlRequestValidation.isRamlOnClasspath=false
ramlRequestValidation.ramlPath=/api/config/raml.zip
```

**Add (SDK3) to `src/main/resources/application.properties`:**
```properties
api.spec.validation.enabled=false
api.spec.location=oas/openapi.yaml
```

**Also add to `src/test/resources/application.properties`** to prevent Spring Boot startup failures in unit tests (no real HTTP server context).

---

## 5. OAS `headers.yaml` — Standard Barclays Headers Must Be Defined

**Issue:** The RAML-to-OAS converter generates `openapi.yaml` referencing `Channel-ID` and `Agent-ID` as standard Barclays request headers, and all 202 response files reference `Content-Type` and `Correlation-ID-Response`. These are referenced via `$ref: './common-libraries/components/headers.yaml#/...'` but are **not auto-generated** in `headers.yaml`.

**Symptom:** 24 broken `$ref` links across `openapi.yaml` (12) and 6 response YAML files (12).

**Fix:** Add to `src/main/resources/oas/common-libraries/components/headers.yaml`:

```yaml
# Request headers (need name + in: header)
Channel-ID:
  name: "Channel-ID"
  in: header
  required: true
  description: "Initiating channel identifier"
  schema:
    type: string

Agent-ID:
  name: "Agent-ID"
  in: header
  required: false
  description: "Unique identifier for the calling agent or user"
  schema:
    type: string

# Response headers (NO name or in — per OAS spec for response headers)
Content-Type:
  description: "Response content type"
  schema:
    type: string
    enum:
      - "application/json"

Correlation-ID-Response:
  description: "Correlation ID in response"
  schema:
    type: string
    pattern: ^[a-zA-Z0-9-+/=_]{16,64}$
```

**Key distinction:** Request headers used in `parameters:` need `name` and `in: header`. Response headers used in `responses.headers:` must NOT have those fields.

---

## 6. HikariCP Version Pin — Intentional Downgrade

**Context:** BOM provides HikariCP 6.3.3 but this project pinned to 5.1.0.

**Reason:** The project previously used HikariCP 3.4.5 and was migrated to 5.1.0 as the maximum version compatible with the AMQP connection pooling behaviour. Accepting the BOM's 6.3.3 would require additional testing.

**Pattern:** When an explicit version pin is deliberate, document it in `PR.md` under "Key Decisions" to explain the intentional override.

---

## 7. RestResponse Lives in `bap-bld-lib-payload`

`RestResponse` (gateway/service layer response wrapper) is in `com.barclays.api:bap-bld-lib-payload` — BOM-managed in SDK3. No explicit version needed.

Do not confuse with `Response` (controller layer return type from `bap-bld-lib-restapi`).
