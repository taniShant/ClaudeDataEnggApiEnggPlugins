---
name: sdk2-sdk3-gradle
description: Complete Gradle build configuration migration from SDK2 to SDK3 for Barclays iAPI projects. Covers Gradle wrapper update to 8.13, buildSrc folder setup with SDK3 platform dependencies, and root build.gradle modifications. Use when migrating build.gradle files or setting up Gradle configuration for SDK3 migration.
owner: Barclays AI (barclaysai@barclays.com)
version: 1.0.0
license: Proprietary. For Barclays internal use only.
user-invocable: false
source: barclays-claude-code-plugins/plugins/sdk3-migration/skills/sdk2_sdk3_gradle/SKILL.md
owner: Barclays AI (barclaysai@barclays.com)
review-trigger: When SDK3 BOM versions change or new migration patterns are identified
status: Full
---

# Gradle Build Configuration Migration - SDK2 to SDK3
## Quick Start

Gradle build configuration migration patterns for SDK2 → SDK3.

```groovy
// Replace SDK2 BOM with SDK3 BOM in build.gradle
// Before: implementation platform("com.barclays:sdk2-bom:1.x.x")
// After:  implementation platform("com.barclays.sdk3:sdk3-bom:3.x.x")
```


## Overview

This skill provides step-by-step guidance for migrating Gradle build configuration files from SDK2 (api-core-boot) to SDK3 (bap-bld-lib) for Barclays iAPI projects. This includes:

0. **Delete gradle/common/ entirely and remove all apply-from references** (MUST be first — before any other build changes)
1. Gradle wrapper update to 8.13 with Barclays Nexus URL
2. buildSrc folder creation and configuration
3. Root build.gradle modifications for SDK3 dependencies and plugins
4. gradle.properties updates

**CRITICAL**: Step 0 (gradle/common deletion) MUST execute before any other build changes. The build system must be fully configured before any Java code migration.

> **AGENT INSTRUCTION - VERSION SOURCE OF TRUTH:** Dependency versions in this guide and in `barclays_internal_libraries_versions.md` are the authoritative source. Do NOT search Nexus for versions already documented here. Only use Nexus for libraries NOT found in any reference doc. See [Nexus Version Lookup Reference](../sdk2-sdk3-migration/reference/nexus_version_lookup.md) for undocumented libraries only.

---

## Prerequisites

Before starting, verify:
- [ ] JDK 21 or JDK 25 is available in your environment (matching your target migration version — `java -version` to verify)
- [ ] You have access to Barclays Nexus repository
- [ ] Migration branch created: `git checkout -b feature/sdk3-migration`
- [ ] Current project uses SDK2 (api-core-boot)

---

## Part 0: Delete gradle/common (MUST BE FIRST — NON-NEGOTIABLE)

**EXECUTE THIS BEFORE ANY OTHER BUILD CHANGES. This is Step 0, not Step 5.**

SDK3 does not use the `gradle/common/` pattern at all. The `bap-bld-lib-plugin` provides all necessary Gradle configuration. Leaving `gradle/common/` in place while modifying `build.gradle` causes import conflicts and confusing build errors.

**ABSOLUTE RULE: Delete `gradle/common/` unconditionally. Do NOT read any files inside it. Do NOT migrate any content from it into `build.gradle`. Every file in `gradle/common/` is replaced by SDK3 plugin defaults or by the standard steps in this guide — no manual migration is needed.**

### Step 0.1: Delete the Entire gradle/common/ Directory

```bash
# macOS/Linux
rm -rf gradle/common

# Windows (PowerShell)
Remove-Item -Path "gradle\common" -Recurse -Force
```

### Step 0.2: Remove ALL apply-from References to gradle/common

In `build.gradle`, **delete every line** matching `apply from: ".*gradle/common/.*"` or `apply from: '.*gradle/common/.*'`. No `apply from: gradle/common/` line should remain.

**Keep** `apply from` lines that reference files outside `gradle/common/` (e.g., `apply from: "${rootDir}/upload-artifact.gradle"`).

### Step 0.3: Verify Deletion

```bash
# Verify directory is gone
ls gradle/common 2>/dev/null && echo "ERROR: gradle/common still exists!" || echo "OK: gradle/common deleted"

# Verify no apply-from references remain
grep -n "gradle/common" build.gradle && echo "ERROR: apply-from references remain!" || echo "OK: no gradle/common references"
```

**Why this must be first:**
- `gradle/common/` files contain SDK2 plugin configurations that conflict with SDK3
- Modifying `build.gradle` while `apply from: gradle/common/...` lines exist causes unpredictable behavior
- The `bap-bld-lib-plugin` replaces ALL functionality previously in `gradle/common/`

---

## Part 1: Gradle Wrapper Update

### Step 1.1: Update gradle-wrapper.properties

**File:** `gradle/wrapper/gradle-wrapper.properties`

**Action:** Update distributionUrl to use Gradle 8.13 from Barclays Nexus

```properties
distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https://nexus.barcapint.com/nexus/content/groups/barclays/gradle-8.13-bin.zip
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
```

**IMPORTANT NOTES:**
- Do NOT use standard Gradle distribution URL (services.gradle.org) - it may be blocked
- Always use Barclays Nexus URL for Gradle distribution
- Gradle 8.13 is required for Java 21 support

### Step 1.2: Verify Gradle Wrapper

```bash
$GRADLE_CMD --version
```

**Expected output:** Gradle 8.13

If download fails, verify:
- VPN connection active
- Nexus repository access configured
- Proxy settings if applicable

---

## Part 2: buildSrc Folder Setup

### Step 2.1: Create buildSrc Directory Structure

Use Glob tool to check if `buildSrc` exists. If it does not exist, use Bash `mkdir buildSrc` to create it (works on both Unix and Windows without flags when parent directory exists).

### Step 2.2: Create buildSrc/build.gradle

**File:** `buildSrc/build.gradle`

**CRITICAL RULES:**
- NO plugins block in buildSrc/build.gradle
- Dependencies must reference SDK3_VERSION from root gradle.properties
- Must include platform BOM and three SDK3 plugins

**Complete buildSrc/build.gradle content:**

```gradle
repositories {
    maven {
        url 'https://nexus.barcapint.com/nexus/content/groups/barclays'
    }
}

def rootProperties = new Properties()
file('../gradle.properties').withInputStream {
    rootProperties.load(it)
}
def sdkVersion = rootProperties.getProperty('SDK3_VERSION')

dependencies {
    implementation(platform("com.barclays.api:sdk3:${sdkVersion}"))
    implementation("com.barclays.api:bap-bld-lib-plugin")
    implementation("com.barclays.api:bap-bld-lib-kotlin-int-test-gradle-plugin")
    implementation("org.springframework.boot:spring-boot-gradle-plugin") {
        exclude group:'ch.qos.logback', module: 'logback-classic'
    }
}
```

**Key Points:**
- `rootProperties` loads SDK3_VERSION from parent gradle.properties
- Platform BOM: `platform("com.barclays.api:sdk3:${sdkVersion}")` - provides dependency versions
- Three SDK3 plugins: bap-bld-lib-plugin, bap-bld-lib-kotlin-int-test-gradle-plugin
- Spring Boot plugin with logback exclusion

---

## Part 3: gradle.properties Updates

### Step 3.1: Add SDK3 Properties

**File:** `gradle.properties` (in project root)

**Add these properties:**

```properties
SDK3_VERSION=1.12.007  # Source of truth: barclays_internal_libraries_versions.md
GLOBAL_VERSION=1.0.0
SONAR_PROJECT_NAME=your-project-name
GROUP_ID=com.barclays.api

# OAS Generation — set DISABLE_OAS_GENERATION=true if project does NOT use barclaysApiGenerate
# Without this, barclaysApiGenerate throws NullPointerException if root.spec.url is absent
DISABLE_OAS_GENERATION=true

# Root OAS spec (only if DISABLE_OAS_GENERATION is NOT true)
# root.spec.url=https://nexus-read.barcapint.com/nexus/.../openapi.zip
# root.spec.filename=openapi.yaml

# Downstream APIs (repeat for each consumed API)
# {name}.downstream.spec.url=https://nexus-read.barcapint.com/nexus/.../downstream-api-spec.zip
# {name}.downstream.spec.filename=api.yaml

# JaCoCo line coverage minimum (fraction) — used by sdkJacocoTestCoverageVerification.
# Adjust per-project if a lower gate is agreed. Default: 0.80 (80%).
jacoco.line.minimum=0.80

# JaCoCo exclusions - see Step 3.2 for detailed configuration guidance
# Coverage exclusions use dot notation: com.package.Class
jacocoCoverageExclusions=com.barclays.api.yourproject.Application,com.barclays.api.yourproject.beans.*,com.barclays.api.yourproject.config.*,com.barclays.api.yourproject.dto.*

# Report exclusions use path notation: **/com/package/**
jacocoReportExclusions=**/com/barclays/api/yourproject/Application.class,**/com/barclays/api/yourproject/beans/**,**/com/barclays/api/yourproject/config/**,**/com/barclays/api/yourproject/dto/**

# Checkstyle tool version — read by the conditional checkstyle block in build.gradle.
# Update this property to upgrade Checkstyle without modifying build.gradle.
checkstyle_tool_version=12.2.0

# Publishing (CI/CD)
# REP_URL=https://nexus.barcapint.com/nexus/content/repositories/barclays-releases/
# NEXUS_USER=${nexusUsername}
# NEXUS_PASSWORD=${nexusPassword}
```

**Adjust values:**
- `SDK3_VERSION`: Use the version from `barclays_internal_libraries_versions.md` (currently `1.12.007`) — do NOT search Nexus for a newer version
- `GLOBAL_VERSION`: Your application version
- `GROUP_ID`: Maven group ID (typically `com.barclays.api`)
- `SONAR_PROJECT_NAME`: Your project name for SonarQube
- `DISABLE_OAS_GENERATION`: Set to `true` unless project actively uses `barclaysApiGenerate`
- `root.spec.url` / `root.spec.filename`: Root OAS spec location (uncomment if using OAS generation)
- `{name}.downstream.spec.url`: Downstream API spec URLs (one per consumed API)
- `jacoco.line.minimum`: JaCoCo line coverage gate as a fraction (default `0.80` = 80%); override per project if a lower threshold is agreed
- `jacocoCoverageExclusions`: See Step 3.2 for proper configuration
- `jacocoReportExclusions`: See Step 3.2 for proper configuration
- `checkstyle_tool_version`: Checkstyle release version (default `12.2.0`); update here to upgrade without touching `build.gradle`

### Step 3.2: Configure JaCoCo Exclusions (INTELLIGENT ANALYSIS REQUIRED)

**CRITICAL: Do not blindly configure exclusions. Analyze the codebase first.**


**Correct ordering in build.gradle:**
```gradle
// CORRECT — ext property set BEFORE apply plugin

apply plugin: 'java'
apply plugin: "org.springframework.boot"
apply plugin: 'com.barclays.api.bap-bld-lib-kotlin-int-test-gradle-plugin'
apply plugin: 'com.barclays.api.bap-bld-lib-plugin'  
```



#### Step 3.2.1: Analyze Codebase to Identify Excludable Code

**Before configuring, analyze the codebase to identify:**

1. **Infrastructure Code** (no business logic - safe to exclude):
   - `Application.java` (Spring Boot main class)
   - Configuration classes (`@Configuration`, `@EnableXxx`)
   - DTOs/Beans (only getters/setters, no logic)
   - Exception classes (simple constructors)
   - Constants classes (static final fields only)

2. **Files with Only Getters/Setters**:
   - Read the file and check for method signatures
   - Criteria: Only getter/setter methods, no business logic

**Intelligent Detection Criteria** (check each file):
- Exclude: `Application.java` (Spring Boot `@SpringBootApplication`)
- Exclude: Files in `/beans/`, `/config/`, `/dto/`, `/model/` packages
- Exclude: Classes with ONLY `@Component`/`@Configuration` (no business methods)
- Exclude: Classes with ONLY getters/setters/constructors
- Exclude: Exception classes (extend `Exception`/`RuntimeException` with simple constructors)
- Exclude: Constant classes (all fields are `static final`)
- Include: Service/Gateway/Controller/Util classes (contain business logic)
- Include: Classes with business methods (validation, transformation, calculation)

#### Step 3.2.2: Detect Base Package and Build Exclusions

Use Grep tool to search for `^package` in `src/main/java/**/*.java` files to find the base package from the first Java source file. Then use Read tool to extract the package declaration. Take the first 3-4 segments (e.g., `com.barclays.api.directmandate`).

```
# Coverage exclusions use DOT notation: com.package.Class
# Report exclusions use PATH notation: **/com/package/**
```

**Example Configuration** (for `com.barclays.api.directmandate`):
```properties
# JaCoCo Coverage Configuration - Exclude infrastructure and DTO code
# Coverage exclusions use dot notation (e.g., com.package.Class)
jacocoCoverageExclusions=com.barclays.api.directmandate.Application,com.barclays.api.directmandate.beans.*,com.barclays.api.directmandate.config.*,com.barclays.api.directmandate.dto.*,com.barclays.api.directmandate.model.*,com.barclays.api.directmandate.exception.*

# Report exclusions use path notation (e.g., **/com/package/**)
jacocoReportExclusions=**/com/barclays/api/directmandate/Application.class,**/com/barclays/api/directmandate/beans/**,**/com/barclays/api/directmandate/config/**,**/com/barclays/api/directmandate/dto/**,**/com/barclays/api/directmandate/model/**,**/com/barclays/api/directmandate/exception/**
```

#### Step 3.2.3: VALIDATE EXCLUSIONS - PREVENT GAMING METRICS (MANDATORY)

**CRITICAL**: Evidence shows agents have excluded business logic to game metrics.

**VALIDATION RULES - NEVER EXCLUDE:**
1. **`service.builders.*`** - Despite "Builder" in name, contains BUSINESS LOGIC
2. **`controller.*`** - Contains business logic (validation, request processing)
3. **`gateway.*`** - Contains business logic (external API communication, error handling)
4. **`utils.RequestValidator*`** - Contains business logic (validation rules)
5. **ANY class with business methods** - Even if it "seems" like infrastructure

**Validation Check:**

Use Grep tool to search for `jacocoCoverageExclusions` in `gradle.properties` and Read tool to extract its value. Then use Grep tool to check the exclusion value for forbidden patterns: `service.builders`, `controller.`, `gateway.`, `utils.RequestValidator`. If any forbidden pattern is found, report a validation failure and require their removal from `jacocoCoverageExclusions`.

**File Analysis Validation (Before Adding Exclusions):**

For each class proposed for exclusion, read the file and verify it's safe:
```
Safe to exclude if:
   - @Data or @Value annotation (Lombok data class)
   - record class (Java record)
   - Only has getters/setters (no business methods)
   - Exception class with simple constructor
   - @Configuration with no business logic

MUST TEST (never exclude) if:
   - Contains: validate, process, calculate, transform, handle, build, create, execute
   - In packages: service.*, controller.*, gateway.*, utils.*
   - Has any business logic methods
```

**Why This Validation is Critical:**
- **Gaming metrics**: Agents can take shortcuts by excluding code instead of writing tests
- **False baselines**: Fake baseline 57% vs real baseline 20%
- **Cost of correction**: 3-4 hours of manual work to fix inappropriate exclusions

**REMEMBER**: If unsure whether to exclude, err on the side of TESTING IT.


---

## Parts 4-5: Root build.gradle Modifications & Additional Configuration

**These sections are in a separate reference file to keep this skill loadable in a single read.**

Reference file: `reference/build_gradle_modifications.md`

Contents:
- **Part 4** — Root build.gradle modifications (plugins, repositories, dependencies, Java config, IDE cleanup, version overrides, test config, publishing, barclaysApiGenerate)
- **Part 5** — JaCoCo integration test report task, PIT mutation testing configuration
- **Validation & Testing** — Build verification steps
- **Common Issues & Solutions** — Troubleshooting guide
- **CI/CD Tasks** — Tasks registered by bap-bld-lib-plugin

Load this file AFTER completing Parts 0-3, when you are ready to modify `build.gradle`.


## Build.gradle Migration Checklist

Use this checklist to ensure all changes are applied:

### buildSrc Setup
- [ ] buildSrc folder created
- [ ] buildSrc/build.gradle created with correct content
- [ ] No plugins block in buildSrc/build.gradle
- [ ] SDK3 platform BOM referenced: `platform("com.barclays.api:sdk3:${sdkVersion}")`
- [ ] Three SDK3 plugins added: bap-bld-lib-plugin, bap-bld-lib-kotlin-int-test-gradle-plugin, spring-boot-gradle-plugin
- [ ] Spring Boot plugin has logback exclusion

### gradle.properties
- [ ] SDK3_VERSION added (e.g., 1.12.007)
- [ ] GROUP_ID added
- [ ] GLOBAL_VERSION added
- [ ] SONAR_PROJECT_NAME configured
- [ ] DISABLE_OAS_GENERATION=true (unless project uses barclaysApiGenerate)
- [ ] Downstream API URLs configured (if applicable): `{name}.downstream.spec.url`
- [ ] jacocoCoverageExclusions configured

### gradle/wrapper
- [ ] gradle-wrapper.properties updated to Gradle 8.13
- [ ] distributionUrl uses Barclays Nexus URL

### Part 0: gradle/common Deletion (MUST BE FIRST)
- [ ] Entire `gradle/common/` directory deleted (`rm -rf gradle/common`) — BEFORE any other changes
- [ ] ALL `apply from: gradle/common/...` lines removed from build.gradle — BEFORE any other changes
- [ ] Verified: no `gradle/common` references remain in build.gradle

### Root build.gradle - Structure
- [ ] jacocoIntegrationTestReport task added (see Step 5.1)
- [ ] pitest block configured in build.gradle with auto-detect base package (see Step 5.2)
- [ ] buildscript block removed (if present)
- [ ] dependencyManagement block removed (if present)
- [ ] Obsolete plugins commented out (maven-publish, eclipse, jacoco, org.springframework.boot, checkstyle, etc.) — only `java`, `bap-bld-lib-kotlin-int-test-gradle-plugin`, `bap-bld-lib-plugin` are active
- [ ] bap-bld-lib-plugin added

### Root build.gradle - IDE Config Removal
- [ ] `eclipse {}` configuration block removed
- [ ] `idea {}` configuration block removed
- [ ] `sourceSets {}` for generated sources removed
- [ ] `generatedSourcesDir` variable removed
- [ ] Eclipse/IDEA comment headers removed (e.g., `// Eclipse //`)

### Root build.gradle - Java Configuration
- [ ] sourceCompatibility/targetCompatibility changed to VERSION_21
- [ ] Java toolchain block added with languageVersion 21

### Root build.gradle - Repositories
- [ ] Repositories block present with Nexus URL
- [ ] Barclays Nexus repository configured

### Root build.gradle - Version Overrides
- [ ] Tomcat version updated to 10.1.44
- [ ] Netty version added: 4.1.125.Final
- [ ] Spring Framework version added: 6.2.11

### Root build.gradle - Configurations
- [ ] api-core-boot exclusion added

### Root build.gradle - Dependencies
- [ ] SDK3 platform BOM added at top of dependencies block
- [ ] SDK2 dependencies removed (api-core-boot, api-core-properties, etc.)
- [ ] SDK3 dependencies added (bap-bld-lib-request-validator, bap-bld-lib-restapi, etc.)
- [ ] spring-boot-starter-cache kept
- [ ] EhCache 2.x dependencies removed (if present)
- [ ] jackson-datatype-jsr310 added
- [ ] commons-io added
- [ ] JUnit 4 dependencies removed
- [ ] JUnit 5 dependencies added (junit-jupiter, junit-platform-launcher)
- [ ] Mockito updated to 5.7.0
- [ ] mockito-junit-jupiter added

### Root build.gradle - Test Configuration
- [ ] test task updated to tasks.named('test')
- [ ] useJUnitPlatform() added to test task
- [ ] barclaysApiGenerate task disabled (or DISABLE_OAS_GENERATION=true in gradle.properties)
- [ ] No explicit `id 'org.springframework.boot'` in plugins block (bap-bld-lib-plugin applies it)

### Validation
- [ ] `$GRADLE_CMD --version` shows Gradle 8.13
- [ ] `$GRADLE_CMD dependencies` resolves without conflicts
- [ ] `$GRADLE_CMD clean build` runs (will fail on Java compilation - expected)
- [ ] Changes committed to version control

---

## Next Steps

After completing Gradle build configuration (Phase 1):

1. **Phase 2: Package & Import Migration** - Replace javax.* → jakarta.*, SDK2 → SDK3 packages
2. **Phase 3: REST Client Migration** - Update RestApiClient patterns, response handling
3. **Phase 4: Test Migration** - Migrate JUnit 4 → JUnit 5, @MockBean → @MockitoBean
4. **Phase 5: Final Validation & Cleanup** - Run all tests, remove unused dependencies

---

## Reference Documents

For complete migration guidance, refer to the `sdk2-sdk3-migration` skill:
- **SKILL.md** - Core migration patterns, Big 5 Patterns, common pitfalls
- **reference/sdk2_to_sdk3_package_mapping.md** - SDK2 to SDK3 package mappings
- **reference/test_migration_specification.md** - JUnit 4 to JUnit 5 migration
- **lessons_learnt/quick_reference.md** - Condensed problem/solution cards

---

**Version:** 2.0.0

## Agent Self-Check

Before executing, verify:
- [ ] All required inputs are present
- [ ] Skill documentation has been loaded
- [ ] Scope boundary is understood — no out-of-scope changes
- [ ] Iron Rules (No Assumptions, Version Source of Truth) acknowledged
- [ ] Output format understood
