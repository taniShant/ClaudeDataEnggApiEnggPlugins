# barclays-buk-smesh-api-maintainer

Complete SDK2 to SDK3 migration toolkit for Java 21 and Java 25. Includes SDK3 library version uplift for existing J21/J25 APIs via `--increment-sdk3`.

**Latest SDK3 Version Support**: 1.12.007 (same for JDK 21 and JDK 25)

## Usage

### Full SDK2 to SDK3 Migration (Java 21 — default)
```
/sdk3-migrate PROJECT_PATH --jira JIRA_ID [--jdk-version 21] [--group GROUP] [--full-automation] [--spring-conventions] [--skip-gitlab-ci]
```

### Full SDK2 to SDK3 Migration (Java 25)
> **Requires API to already be on JDK 21. Direct migration from JDK 8 to JDK 25 is not supported.**
```
/sdk3-migrate PROJECT_PATH --jira JIRA_ID --jdk-version 25 [--group GROUP] [--full-automation] [--spring-conventions] [--skip-gitlab-ci]
```

### Two-Step Migration: JDK 8 → JDK 21 → JDK 25
```
# Step 1: migrate from SDK2 / Java 8 to Java 21
/sdk3-migrate PROJECT_PATH --jira JIRA_ID --jdk-version 21

# Step 2: migrate from Java 21 to Java 25 (run after Step 1 completes)
/sdk3-migrate PROJECT_PATH --jira JIRA_ID-JDK25 --jdk-version 25
```

### SDK3 Version Uplift — Unconditional (default)
Applies the latest `SDK3_VERSION` from `barclays_internal_libraries_versions.md` unconditionally. Works for both JDK 21 and JDK 25 APIs.
```
/sdk3-migrate PROJECT_PATH --jira JIRA_ID
/sdk3-migrate PROJECT_PATH --jira JIRA_ID --increment-sdk3 false
```

### SDK3 Version Uplift — Version-Gated (`--increment-sdk3 true`)
Checks the API's current `SDK3_VERSION` in `gradle.properties` first. Applies the uplift only if the current version is lower than the supported SDK3 version.
```
/sdk3-migrate PROJECT_PATH --jira JIRA_ID --increment-sdk3 true [--full-automation]
/sdk3-migrate PROJECT_PATH --jira JIRA_ID --jdk-version 25 --increment-sdk3 true [--full-automation]
```

### SDK4 Uplift (API already on SDK3 / Spring Boot 3.5.x)
```
/sdk3-migrate PROJECT_PATH --jira JIRA_ID --uplift-sdk3 [--full-automation] [--skip-gitlab-ci]
```

### RAML to OpenAPI Conversion
```
/sdk3-migrate:raml-to-oas [RAML_PATH] [--output OAS_PATH] [--validate-only]
```

## What it does

### Full Migration: SDK2 (Java 8, JUnit 4, Spring Boot 2) → SDK3 (Java 21 or Java 25, JUnit 5, Spring Boot 3)

The following changes are **identical for JDK 21 and JDK 25**:
- Gradle build migration with SDK3 BOM (same `SDK3_VERSION` for both)
- Spring Boot 2.7 → 3.x (javax → jakarta namespace)
- JUnit 4 → JUnit 5 (Jupiter) test migration
- Package restructuring from `api.core.*` to `bap.bld.lib.*`
- RAML 1.0 → OpenAPI 3.0.3 conversion
- Phased branching strategy with build validation gates
- All dependency versions, JaCoCo, PITest, checkstyle configuration

The **only difference** between JDK 21 and JDK 25 is the Java toolchain version in `build.gradle`:

| | JDK 21 | JDK 25 |
|---|---|---|
| Toolchain | `JavaLanguageVersion.of(21)` | `JavaLanguageVersion.of(25)` |
| sourceCompatibility | `JavaVersion.VERSION_21` | `JavaVersion.VERSION_25` |
| targetCompatibility | `JavaVersion.VERSION_21` | `JavaVersion.VERSION_25` |
| SDK3_VERSION | `1.12.007` | `1.12.007` (same) |

### JDK 25-specific features (optional enhancements)
Java 25 builds on all Java 21 features (Records, Sealed Classes, Pattern Matching, Virtual Threads, Sequenced Collections, Text Blocks). Refer to [`jdk21-to-jdk25-changes.md`](skills/sdk2-sdk3-migration/reference/jdk21-to-jdk25-changes.md) for Java 25-specific enhancements available after migration.

### SDK3 Version Uplift: `--increment-sdk3`

For APIs already on SDK3, the command applies the latest SDK3 library version using the OpenRewrite recipe in `scripts/incremental.yml`.

| Mode | Trigger | Behaviour |
|------|---------|-----------|
| Unconditional (default) | `--increment-sdk3 false` or omitted | Applies `SDK3_VERSION` unconditionally regardless of current API version |
| Version-gated | `--increment-sdk3 true` | Reads current `SDK3_VERSION` from `gradle.properties`; only applies if current < supported |

**Changes applied by the recipe (`scripts/incremental.yml`):**
- Sets `SDK3_VERSION` in `gradle.properties` to the latest supported version
- Removes deprecated Jacoco task configurations
- Adds new SDK Jacoco configurations (`sdkJacocoTestReport`, `sdkJacocoTestCoverageVerification`)
- Removes deprecated property keys
- Build validation (`compileJava`) run after the recipe

## Skills

| Skill | Purpose |
|---|---|
| `sdk2-sdk3-migration/` | Complete SDK2→SDK3 migration guide with production lessons learned |
| `sdk2-sdk3-gradle/` | Gradle build configuration migration patterns |
| `java8-to-java21-features/` | Modern Java language features (JDK 8→21 reference) |
| `sdk2-sdk3-migration/reference/jdk21-to-jdk25-changes.md` | JDK 21→25 migration guide and feature reference |
| `branching-strategy/` | Phased development workflow |
| `raml-oas-conversion/` | RAML to OAS conversion patterns and validation |
| `spring-conventions/` | Spring Boot 3 best practices |

## Standards

Loads `barclays-buk-standards:security`, `barclays-buk-standards:testing`, and `barclays-buk-standards:governance`.

## Author

Barclays AI (barclaysai@barclays.com)
