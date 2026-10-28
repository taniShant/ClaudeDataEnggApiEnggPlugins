# SDK3 Pre-Migration Validation Checklist

> **Purpose:** Automated validation checklist for SDK3 migration agents to validate project configuration BEFORE starting migration.
> **Version:** 1.0
> **Last Updated:** 2026-01-21

## Overview

This checklist must be executed by the SDK3 migration agent BEFORE any code changes. All validations should pass or be explicitly acknowledged before proceeding.

**Cross-References:**
- [Barclays Internal Libraries — Versions](barclays_internal_libraries_versions.md)
- [Third-Party Dependencies](third_party_dependencies.md)
- [Package Mapping](sdk2_to_sdk3_package_mapping.md)
- [Migration Specification](sdk2_to_sdk3_migration_specification.md)

---

## Checklist Execution Instructions

```
AGENT INSTRUCTION: Before starting SDK3 migration, execute ALL validations below.
For each check:
- [PASS] = Validation successful, proceed
- [FAIL] = Must fix before migration
- [WARN] = Review and acknowledge before proceeding
- [SKIP] = Not applicable to this project

Report all findings to user before starting migration work.
```

---

## SECTION 1: Build Configuration Validation

### 1.1 Gradle Wrapper Version
**Required:** Gradle 8.13+
**Check:** `gradle/wrapper/gradle-wrapper.properties`

```properties
# REQUIRED SDK3 Value:
distributionUrl=https\://nexus.barcapint.com/nexus/content/groups/barclays/gradle-8.13-bin.zip
```

**Validation Rules:**
- [ ] Gradle version >= 8.13
- [ ] URL points to Barclays Nexus (not gradle.org)

### 1.2 Java Version
**Required:** Java 21
**Check:** `build.gradle` and `.java-version`

```gradle
# REQUIRED SDK3 Values:
java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}
```

**Validation Rules:**
- [ ] Java toolchain set to 21
- [ ] `.java-version` file contains `21` (if present)
- [ ] No `sourceCompatibility = 1.8` or `targetCompatibility = 1.8`

### 1.3 SDK3 Platform BOM
**Required:** SDK3 BOM declaration
**Check:** `build.gradle` or `buildSrc/build.gradle`

```gradle
# REQUIRED:
implementation(platform("com.barclays.api:sdk3:${SDK3_VERSION}"))
```

**Validation Rules:**
- [ ] SDK3 BOM is declared
- [ ] SDK3_VERSION defined in `gradle.properties` (e.g., `1.12.007`)

### 1.4 Repository Configuration
**Check:** `build.gradle`

```gradle
# REQUIRED SDK3 Repositories:
repositories {
    maven {
        url 'https://nexus.barcapint.com/nexus/content/groups/barclays/'
    }
}
```

**Validation Rules:**
- [ ] Barclays Nexus repository configured
- [ ] No references to mavenCentral() or gradlePluginPortal() (BANNED per project policy)

### 1.5 SDK3 Plugin
**Check:** `build.gradle`

```gradle
# REQUIRED:
apply plugin: 'com.barclays.api.bap-bld-lib-plugin'
```

**Validation Rules:**
- [ ] SDK3 plugin applied
- [ ] Old SDK2 plugins NOT present (`api-boot-plugin`, etc.)

### 1.6 Configuration Exclusions
**Check:** `build.gradle`

```gradle
# REQUIRED SDK3 Exclusions:
configurations {
    all*.exclude module: 'api-core-boot'
    all*.exclude module: 'spring-boot-starter-logging'
    all*.exclude module: 'logback-classic'
    all*.exclude module: 'slf4j-simple'
    all*.exclude module: 'log4j-slf4j-impl'
}
```

**Validation Rules:**
- [ ] SDK2 boot module excluded
- [ ] Conflicting logging modules excluded

### 1.7 Version Overrides
**Check:** `build.gradle`

```gradle
# REQUIRED SDK3 Version Overrides:
ext['tomcat.version'] = '10.1.44'
ext['netty.version'] = '4.1.125.Final'
ext['spring-framework.version'] = '6.2.11'
```

**Validation Rules:**
- [ ] Tomcat version override present
- [ ] Netty version override present
- [ ] Spring Framework version override present

### 1.8 JUnit 5 Configuration
**Check:** `build.gradle`

```gradle
# REQUIRED:
tasks.named('test') {
    useJUnitPlatform()
}
```

**Validation Rules:**
- [ ] `useJUnitPlatform()` configured
- [ ] No JUnit 4 runner configuration

---

## SECTION 2: Core SDK3 Dependencies Validation

### 2.1 SDK3 Platform Dependencies (BOM Managed)
**Reference:** [third_party_dependencies.md](third_party_dependencies.md)

| Artifact | Required State |
|----------|---------------|
| com.barclays.api:bap-bld-lib-restapi | Present, no version (BOM) |
| com.barclays.api:bap-bld-lib-meshconnector | Present, no version (BOM) |
| com.barclays.api:bap-bld-lib-request-validator | Present, no version (BOM) |

**Validation Rules:**
- [ ] All SDK3 core dependencies declared
- [ ] No explicit versions (BOM managed)

### 2.2 Security Filter
**Reference:** [third_party_dependencies.md](third_party_dependencies.md)

| Artifact | SDK3 Version |
|----------|--------------|
| com.barclays.security:securityFilter | **7.0.0-RELEASE** |

**Validation Rules:**
- [ ] Security filter version is 7.0.0-RELEASE
- [ ] NOT using older versions (6.x, 5.x, etc.)

---

## SECTION 3: Common Libraries Version Validation

### 3.1 Critical Libraries (MUST VALIDATE)
**Reference:** [barclays_internal_libraries_versions.md](barclays_internal_libraries_versions.md)

| Artifact | SDK2 (INVALID) | SDK3 (REQUIRED) | Priority |
|----------|----------------|-----------------|----------|
| com.barclaycard.digital:common-filter | 4.1.0 | **5.0.3** | CRITICAL |
| com.barclaycard.digital:common-context | 1.3.0 | **2.0.4** | HIGH |
| com.barclaycard.digital:executor-core | 1.1.1 | **2.0.0** | HIGH |
| com.barclaycard.digital:core-jsonapi-web | 4.4.1 | **5.2-001** | HIGH |
| com.barclaycard.digital:system-core-ods | 5.3.2 | **6.1-001** | HIGH |
| com.barclaycard.digital:core-mapping | 1.0.6 | **2.0.2** | MEDIUM |

**Validation Rules:**
- [ ] common-filter is 5.0.3 (NOT 4.1.0)
- [ ] common-context is 2.0.4 (NOT 1.3.0)
- [ ] executor-core is 2.0.0 (NOT 1.1.1)
- [ ] core-jsonapi-web is 5.2-001 (NOT 4.4.1)
- [ ] system-core-ods is 6.1-001 (NOT 5.3.2)

### 3.2 Tokenization Libraries
**Reference:** [barclays_internal_libraries_versions.md](barclays_internal_libraries_versions.md)

| Artifact | SDK2 (INVALID) | SDK3 (REQUIRED) |
|----------|----------------|-----------------|
| com.barclaycard.digital:domain-core-tokenization-uuid | 5.0.0, 6.x | **7.1-001** |
| com.barclaycard.digital:domain-core-tokenization-protegrity | 6.1.1, 7.x | **8.2-002** |
| com.barclaycard.digital:domain-core-agnostic-gateway | 4.1.0 | **5.1-000** |

**Validation Rules:**
- [ ] UUID tokenization is 7.1-001
- [ ] Protegrity tokenization is 8.2-002
- [ ] Agnostic gateway is 5.1-000

### 3.3 Triumph Integration
**Reference:** [barclays_internal_libraries_versions.md](barclays_internal_libraries_versions.md)

| Artifact | SDK2 (INVALID) | SDK3 (REQUIRED) | Note |
|----------|----------------|-----------------|------|
| com.barclaycard.digital.core:core-triumph | 8.3.0 | **9.1-000** | Group ID changed! |

**Validation Rules:**
- [ ] core-triumph is 9.1-000
- [ ] Group ID is `com.barclaycard.digital.core` (NOT `com.barclaycard.digital`)

### 3.4 Resilience Libraries
**Reference:** [barclays_internal_libraries_versions.md](barclays_internal_libraries_versions.md)

| Artifact | Status | SDK3 Version |
|----------|--------|--------------|
| com.barclaycard.digital:system-core-resilience4j | NEW | **1.0.5** |
| com.barclaycard.digital:system-core-resilliency | DEPRECATED | REMOVE |

**Validation Rules:**
- [ ] system-core-resilience4j:1.0.5 present (if using circuit breaker)
- [ ] system-core-resilliency (Hystrix) NOT present

### 3.5 Testing Libraries
**Reference:** [barclays_internal_libraries_versions.md](barclays_internal_libraries_versions.md)

| Artifact | SDK2 (INVALID) | SDK3 (REQUIRED) |
|----------|----------------|-----------------|
| com.barclaycard.digital:test-utilities | 6.2.5 | **8.0-000:tests** |

**Validation Rules:**
- [ ] test-utilities is 8.0-000 with `:tests` classifier
- [ ] NOT using 6.x versions

### 3.6 Cryptography & Security Libraries
**Reference:** [barclays_internal_libraries_versions.md](barclays_internal_libraries_versions.md)

| Artifact | SDK2 | SDK3 |
|----------|------|------|
| core-bcag-encryption | 6.1.2 | **7.0.3** |
| core-jose | 3.1.0 | **4.0.1** |
| core-ssl | 1.0.3 | **2.0.0** |
| domain-core-hybrid-decryption | 2.0.3 | **3.1-000** |
| core-protegrity-encryption | 6.0.1 | **7.0.0** |

**Validation Rules:**
- [ ] All cryptography libraries on SDK3 versions
- [ ] No SDK2 versions present

---

## SECTION 4: System Components Validation

### 4.1 High-Priority System Components
**Reference:** [barclays_internal_libraries_versions.md](barclays_internal_libraries_versions.md)

Validate any system components in use against the reference:

| Artifact Pattern | SDK2 Range | SDK3 Range |
|-----------------|------------|------------|
| system-qry-* | 1.x-6.x | 2.x-12.x |
| system-cmd-* | 1.x-4.x | 2.x-5.x |
| ods-wrapper-* | 1.x-4.x | 2.x-5.x |
| system-common-* | 1.x-3.x | 2.x-4.x |

**Validation Rules:**
- [ ] Cross-reference each system component against system_components.md
- [ ] Flag any SDK2 versions found
- [ ] Report components with TBD/Pending status

### 4.2 Payment Domain Components
**Reference:** [barclays_internal_libraries_versions.md](barclays_internal_libraries_versions.md)

| Artifact | SDK2 | SDK3 |
|----------|------|------|
| system-common-payment | 2.0.0 | **3.1-000** |
| system-common-directdebit | 3.0.0 | **4.1-003** |
| system-cmd-payment-management | 4.0.3 | **5.0-001** |
| system-cmd-directdebit | 2.2.1 | **3.0-001** |
| payment-management-common | 1.0.0 | **2.1-000** |

**Validation Rules:**
- [ ] All payment components on SDK3 versions

### 4.3 Cardholder/Account Query Components
**Reference:** [barclays_internal_libraries_versions.md](barclays_internal_libraries_versions.md)

| Artifact | SDK2 | SDK3 |
|----------|------|------|
| system-qry-cardholder-account | 11.0.1 | **12.0.2** |
| system-qry-cardholder-account-api | 11.0.0 | **12.0.2** |
| system-qry-cardholder-account-runtime | N/A | **10.1-000** |
| system-qry-account-details-api | 6.0.0 | **7.3-000** |

**Validation Rules:**
- [ ] All cardholder/account components on SDK3 versions

---

## SECTION 5: Deprecated/Removed Dependencies Check

### 5.1 Dependencies to REMOVE
**Reference:** [third_party_dependencies.md](third_party_dependencies.md)

| GroupId | ArtifactId | Reason |
|---------|------------|--------|
| com.barclays.api | api-core-boot | Replaced by bap-bld-lib-restapi |
| com.barclays.api | api-core-properties | Replaced by Spring Boot properties |
| com.barclays.api | api-mesh-client-connector | Replaced by bap-bld-lib-meshconnector |
| com.barclays.api.tools | gissdk-filters-wrapper | No longer needed |
| com.barclays.api.tools | api-request-validator | Replaced by bap-bld-lib-request-validator |
| com.ibm.wmq | mq | Replaced by com.ibm.mq.jakarta.client |
| com.ibm.wmq | mqjms | Replaced by com.ibm.mq.jakarta.client |
| com.intuit.karate | karate-junit4 | Replaced by karate-junit5 |
| com.github.tomakehurst | wiremock | Replaced by org.wiremock |
| com.github.tomakehurst | wiremock-jre8 | Replaced by org.wiremock |
| org.mockito | mockito-all | Replaced by mockito-core |
| junit | junit | Replaced by org.junit.jupiter |

**Validation Rules:**
- [ ] NONE of the above dependencies present in build.gradle
- [ ] Flag any found for removal

### 5.2 Deprecated Barclays Libraries
**Reference:** [barclays_internal_libraries_versions.md](barclays_internal_libraries_versions.md)

| Artifact | Status | Replacement |
|----------|--------|-------------|
| system-core-resilliency | DEPRECATED | system-core-resilience4j:1.0.5 |

**Validation Rules:**
- [ ] No deprecated libraries present

---

## SECTION 6: Package Import Validation

### 6.1 Jakarta EE Migration
**Reference:** [sdk2_to_sdk3_package_mapping.md](sdk2_to_sdk3_package_mapping.md)

| SDK2 (INVALID) | SDK3 (REQUIRED) |
|----------------|-----------------|
| javax.servlet | jakarta.servlet |
| javax.persistence | jakarta.persistence |
| javax.validation | jakarta.validation |
| javax.annotation | jakarta.annotation |
| javax.ws.rs | jakarta.ws.rs |

**Validation Rules:**
- [ ] Scan all .java files for `javax.` imports
- [ ] Flag any javax.servlet, javax.persistence, javax.validation imports

### 6.2 SDK2 to SDK3 Package Migration
**Reference:** [sdk2_to_sdk3_package_mapping.md](sdk2_to_sdk3_package_mapping.md)

| SDK2 Package (INVALID) | SDK3 Package (REQUIRED) |
|------------------------|-------------------------|
| com.barclays.api.core.logging | com.barclays.api.bap.bld.lib.logging |
| com.barclays.api.core.web.beans.Request | com.barclays.api.bap.bld.lib.payload.beans.Request |
| com.barclays.api.core.web.beans.Resource | com.barclays.api.bap.bld.lib.payload.beans.Resource |
| com.barclays.api.core.web.response.Response | com.barclays.api.bap.bld.lib.common.response.Response |
| com.barclays.api.core.web.response.Message | com.barclays.api.bap.bld.lib.payload.response.Message |
| com.barclays.api.core.web.response.MetaData | com.barclays.api.bap.bld.lib.payload.response.MetaData |
| com.barclays.api.core.web.exceptions | com.barclays.api.bap.bld.lib.payload.exceptions |
| com.barclays.api.core.web.util.RestClient | com.barclays.api.bap.bld.lib.restclient.RestApiClient |
| com.barclays.api.core.web.beans.SecureField | com.barclays.api.bap.bld.lib.logging.beans.SecureField |
| com.barclays.api.tools.security.SecurityFilterConfiguration | REMOVED (auto-configured) |

**Validation Rules:**
- [ ] Scan for `com.barclays.api.core.` imports
- [ ] Flag all SDK2 package imports for migration

### 6.3 Removed Classes
**Reference:** [sdk2_to_sdk3_package_mapping.md](sdk2_to_sdk3_package_mapping.md)

| Class | Status |
|-------|--------|
| SecurityFilterConfiguration | REMOVED - Auto-configured in SDK3 |
| RequestValidationInitializer | REMOVED - Auto-configured in SDK3 |

**Validation Rules:**
- [ ] No imports of removed classes
- [ ] No @Import annotations referencing removed classes

---

## SECTION 7: Test Framework Validation

### 7.1 JUnit Migration
**Reference:** [test_migration_specification.md](test_migration_specification.md)

| SDK2 (INVALID) | SDK3 (REQUIRED) |
|----------------|-----------------|
| org.junit.Test | org.junit.jupiter.api.Test |
| org.junit.Before | org.junit.jupiter.api.BeforeEach |
| org.junit.After | org.junit.jupiter.api.AfterEach |
| org.junit.Assert | org.junit.jupiter.api.Assertions |
| org.junit.Ignore | org.junit.jupiter.api.Disabled |
| @Test(expected=...) | Assertions.assertThrows() |

**Validation Rules:**
- [ ] Scan test files for JUnit 4 imports
- [ ] Flag @Test(expected=...) patterns
- [ ] Flag org.junit.Assert usage

### 7.2 Spring Boot Test Mocking
**Reference:** [test_migration_specification.md](test_migration_specification.md)

| SDK2 (INVALID) | SDK3 (REQUIRED) |
|----------------|-----------------|
| @MockBean | @MockitoBean |
| @SpyBean | @MockitoSpyBean |

**Validation Rules:**
- [ ] Scan for @MockBean annotations
- [ ] Flag for migration to @MockitoBean

### 7.3 Test Dependencies
**Reference:** [third_party_dependencies.md](third_party_dependencies.md)

| Artifact | SDK3 Version |
|----------|--------------|
| org.junit.jupiter:junit-jupiter | 5.13.4 |
| org.junit.platform:junit-platform-suite-api | 1.10.1 |
| org.mockito:mockito-core | 5.9.0 |
| org.mockito:mockito-junit-jupiter | 5.9.0 |
| org.wiremock:wiremock-standalone | 3.13.2 |
| com.intuit.karate:karate-junit5 | 1.4.1 |

**Validation Rules:**
- [ ] JUnit Jupiter present (not JUnit 4)
- [ ] Mockito 5.x present (not 3.x)
- [ ] WireMock from org.wiremock (not com.github.tomakehurst)
- [ ] Karate JUnit 5 (not JUnit 4)

---

## SECTION 8: Third-Party Dependencies Validation

### 8.1 Critical Third-Party Versions
**Reference:** [third_party_dependencies.md](third_party_dependencies.md)

| Artifact | SDK3 Version |
|----------|--------------|
| com.google.guava:guava | 33.4.7-jre |
| commons-io:commons-io | 2.16.1 |
| org.projectlombok:lombok | 1.18.38 |
| com.zaxxer:HikariCP | 5.1.0 |
| org.yaml:snakeyaml | 2.0 (or BOM managed) |

**Validation Rules:**
- [ ] Guava is 33.x (not 30.x or older)
- [ ] Commons IO is 2.16.1
- [ ] No vulnerable versions of SnakeYAML

### 8.2 Jakarta EE Dependencies
**Reference:** [third_party_dependencies.md](third_party_dependencies.md)

| Artifact | SDK3 Version |
|----------|--------------|
| jakarta.servlet:jakarta.servlet-api | 6.0.0 |
| jakarta.validation:jakarta.validation-api | BOM managed |
| jakarta.xml.ws:jakarta.xml.ws-api | 4.0.2 |

**Validation Rules:**
- [ ] Using jakarta.* dependencies (not javax.*)

### 8.3 Messaging Dependencies
**Reference:** [third_party_dependencies.md](third_party_dependencies.md)

| SDK2 (INVALID) | SDK3 (REQUIRED) |
|----------------|-----------------|
| com.ibm.wmq:mq | com.ibm.mq:com.ibm.mq.jakarta.client:9.4.4.0 |
| com.ibm.wmq:mqjms | com.ibm.mq:com.ibm.mq.jakarta.client:9.4.4.0 |

**Validation Rules:**
- [ ] Using Jakarta MQ client (not old WMQ)

---

## SECTION 9: Files to Remove/Add

### 9.1 Files to REMOVE
**Reference:** [sdk2_to_sdk3_migration_specification.md](sdk2_to_sdk3_migration_specification.md)

**Delete the entire `gradle/common/` directory — no files carried forward:**
```bash
rm -rf gradle/common
```

**Validation Rules:**
- [ ] `gradle/common/` directory does not exist after migration

### 9.2 Files to ADD/VERIFY
**Reference:** [sdk2_to_sdk3_migration_specification.md](sdk2_to_sdk3_migration_specification.md)

```
buildSrc/build.gradle          (SDK3 buildSrc configuration)
settings.gradle                (Plugin management)
```

**Validation Rules:**
- [ ] buildSrc/build.gradle exists with SDK3 configuration
- [ ] settings.gradle has SDK3 plugin management

---

## SECTION 10: Pre-Migration Report Template

After completing all validations, generate a report:

```markdown
# SDK3 Pre-Migration Validation Report

**Project:** [PROJECT_NAME]
**Date:** [DATE]
**Validator:** SDK3 Migration Agent

## Summary
- Total Checks: [X]
- Passed: [X]
- Failed: [X]
- Warnings: [X]
- Skipped: [X]

## Critical Issues (Must Fix Before Migration)
1. [Issue description]
2. [Issue description]

## Warnings (Review Before Proceeding)
1. [Warning description]
2. [Warning description]

## Validated Configurations
- [ ] Build configuration
- [ ] Core SDK3 dependencies
- [ ] Common library versions
- [ ] System component versions
- [ ] Deprecated dependencies removed
- [ ] Package imports ready
- [ ] Test framework ready
- [ ] Third-party dependencies

## Recommendation
[ ] PROCEED with migration
[ ] FIX ISSUES before migration
[ ] REVIEW WARNINGS before migration
```

---

## Quick Validation Commands

Use the Grep tool (or `search_in_files_by_text` / `search_in_files_by_regex` MCP tools) for these validations. See CLAUDE.md for tool guidance.

- **Check Gradle wrapper version:** Grep for `distributionUrl` in `gradle/wrapper/gradle-wrapper.properties`
- **Check Java version configuration:** Grep for `JavaLanguageVersion|sourceCompatibility|targetCompatibility` in `build.gradle`
- **Find SDK2 package imports:** Grep for `com.barclays.api.core\.` in `src/`
- **Find javax imports:** Grep for `import javax\.` in `src/`
- **Find JUnit 4 imports:** Grep for `import org.junit\.` in `src/test/` (exclude matches containing `jupiter`)
- **Find deprecated dependencies:** Grep for `api-core-boot|api-mesh-client|mockito-all|junit:junit` in `build.gradle`
- **List all Barclays dependencies:** Grep for `com\.barclays|com\.barclaycard` in `build.gradle`

---

**Document Version:** 1.0
**Created:** 2026-01-21
**Purpose:** Pre-migration validation for SDK3 migration agents
**Compatibility:** SDK3 1.12.007, Spring Boot 3.3.x, Java 21
