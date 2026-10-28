---
name: mca-jdk21-migration
description: Intelligent migration assistant for MCA1 (com.barclays.eps) and MCA2 (com.barclays.global.mca) projects upgrading to JDK 21. Analyzes project first, then selectively updates only what exists. Handles MCA1 6.2+/6.3+, MCA2 2.2+/2.3+, Spring Boot 3.3+/3.5+, Gradle 8.5, DevOps plugins, javax->jakarta, deprecated dependencies, cross-dependency upgrades, and legacy dependency removal.
version: 1.0.0
author: Barclays
tags: [mca1, mca2, jdk21, migration, barclays, gradle, spring-boot, jakarta]
user-invocable: false
source: barclays-claude-code-plugins/plugins/mca-jdk-upgrade/skills/mca_jdk21_migration/SKILL.md
owner: Barclays AI (barclaysai@barclays.com)
review-trigger: When Java/Spring Boot target versions change or new MCA project structures are identified
status: Full
---

# MCA JDK 21 Selective Migration Assistant
## Quick Start

Migration patterns for upgrading MCA Spring Boot applications from Java 8 to Java 21.

```bash
# Phase 1: OpenRewrite automated migration
./gradlew rewriteRun   # Applies automated Java 21 / Spring Boot 3 transformations

# Phase 2: Build fix
./gradlew clean build   # Verify build after OpenRewrite
```


## Purpose

Intelligent migration assistant for **MCA1 (com.barclays.eps)** and **MCA2 (com.barclays.global.mca)** projects migrating to JDK 21. Analyzes your project first, then suggests only the changes you actually need.

**The `migration_type` parameter is set by which command you ran:**
- `/mca1-jdk-upgrade` sets `migration_type = mca1` — You're migrating an **MCA1 application**. MCA1 dependencies are upgraded; any MCA2 dependencies present are upgraded as cross-dependencies.
- `/mca2-jdk-upgrade` sets `migration_type = mca2` — You're migrating an **MCA2 application**. MCA2 dependencies are upgraded; any legacy MCA1 dependencies present are removed.

**The skill trusts your command choice** — it NEVER detects, derives, or validates the migration type from the codebase. Do NOT throw "Project Type Mismatch" errors. MCA projects commonly contain BOTH `com.barclays.eps` AND `com.barclays.global.mca` dependencies — the groupId does NOT determine the migration type.

## Approach
1. **Analyze**: Scan project for both MCA1 and MCA2 dependencies and configuration
2. **Identify**: List what's present vs. what's missing
3. **Plan**: Create selective update plan based on migration_type (primary vs secondary/legacy treatment)
4. **Execute**: Apply targeted changes

---

# MIGRATION WORKFLOW

## Phase 1: Project Analysis

### Task 1.1: Find All Gradle Files

**Objective:** Locate all `.gradle` files in the project

**Common locations to check:**
- Root: `build.gradle`, `settings.gradle`
- Subprojects: `*/build.gradle`
- Gradle scripts: `gradle/*.gradle` (e.g., `dependencies.gradle`, `versions.gradle`)
- Build source: `buildSrc/build.gradle`

**Instruction for Claude:**
Use Glob or file search to find all `.gradle` files recursively from project root.

---

### Task 1.2: Search for Primary MCA Dependencies

**Objective:** Identify which primary MCA libraries are used (based on the command you ran)

#### If migration_type = mca1:

You ran `/mca1-jdk-upgrade`, so you're migrating an **MCA1 application**. Search for MCA1 dependencies to upgrade.

**Search pattern:** `com.barclays.eps`

**What to look for in `.gradle` files:**
- `implementation 'com.barclays.eps:*'`
- `implementation "com.barclays.eps:*"`
- BOM: `com.barclays.eps:mca-dependencies`

**Instruction for Claude:**
Search all `.gradle` files for the pattern `com.barclays.eps`. List which specific artifacts are found (e.g., `scp-eps-core-comm`, `scp-eps-libs-audit`).

#### If migration_type = mca2:

You ran `/mca2-jdk-upgrade`, so you're migrating an **MCA2 application**. Search for MCA2 dependencies to upgrade.

**Search pattern:** `com.barclays.global.mca`

**What to look for in `.gradle` files:**
- `implementation 'com.barclays.global.mca:*'`
- `implementation "com.barclays.global.mca:*"`
- BOM: `com.barclays.global.mca:mca-dependencies`

**Instruction for Claude:**
Search all `.gradle` files for the pattern `com.barclays.global.mca`. List which specific artifacts are found with their current versions.

---

### Task 1.3: Search for Secondary MCA Dependencies

#### If migration_type = mca1:

**You're migrating an MCA1 application.** Check if any **MCA2 cross-dependencies** exist that need to be upgraded alongside MCA1.

**Search pattern:** `com.barclays.global.mca`

**What to look for in `.gradle` files:**
- `implementation 'com.barclays.global.mca:*'`
- `implementation "com.barclays.global.mca:*"`
- BOM: `com.barclays.global.mca:mca-dependencies`

**Instruction for Claude:**
Search all `.gradle` files for the pattern `com.barclays.global.mca`. List which specific artifacts are found with their current versions. These must be upgraded alongside MCA1 for compatibility.

#### If migration_type = mca2:

**You're migrating an MCA2 application.** Check if any **legacy MCA1 dependencies** exist that should be removed.

**Search pattern:** `com.barclays.eps`

**What to look for in `.gradle` files:**
- `implementation 'com.barclays.eps:*'`
- `implementation "com.barclays.eps:*"`
- BOM: `com.barclays.eps:mca-dependencies`

**Instruction for Claude:**
Search all `.gradle` files for the pattern `com.barclays.eps`. List which specific artifacts are found. These are legacy dependencies that should be removed (MCA2 replaces MCA1 functionality).

---

### Task 1.4: Search for Spring Boot Gradle Plugin

**Objective:** Find the Spring Boot Gradle plugin and its current version

**Search pattern:** `org.springframework.boot` or `spring-boot-gradle-plugin`

**What to look for in `.gradle` files:**
- `id 'org.springframework.boot' version '...'`
- `org.springframework.boot:spring-boot-gradle-plugin`

**Instruction for Claude:**
Search all `.gradle` files for `spring-boot` plugin references. Note the current version.

---

### Task 1.5: Search for DevOps Plugins

**Objective:** Find current DevOps plugin usage

**Search patterns:**
- `com.barclays.mca.devops.gradle-eps2-war-plugin` (old name)
- `com.barclays.mca.devops.gradle-eps-war-plugin` (new name)
- `com.barclays.mca.devops.gradle-mca-jar-plugin`

**Instruction for Claude:**
Search all `.gradle` files for `com.barclays.mca.devops` pattern. Note which plugins are found and their versions.

---

### Task 1.6: Search for Deprecated Dependencies

**Objective:** Find deprecated dependencies that need removal

**Deprecated patterns to search for:**

1. **Log4j (deprecated - replaced by Logback):**
   - `org.apache.logging.log4j:log4j-slf4j-impl`
   - `org.apache.logging.log4j:log4j-core`
   - `org.apache.logging.log4j:log4j-jul`
   - `org.apache.logging.log4j:log4j-jcl`
   - `org.apache.logging.log4j:log4j-web`
   - `log4j:log4j`
   - `org.slf4j:slf4j-log4j12`

2. **IBM MQ legacy (deprecated - use jakarta versions):**
   - `com.ibm.mq:com.ibm.mq.allclient`
   - `com.ibm.wmq:mqjms`
   - `com.ibm.mq.jms:com.ibm.mqjms`
   - `com.ibm:mqjms`
   - `com.ibm:com.ibm.mqjms`
   - `com.ibm:com.ibm.mq.jmqi`
   - `com.ibm.mq:jmqi`
   - `com.ibm.wmq:jmqi`
   - `com.ibm:com.ibm.dhbcore`
   - `com.ibm:dhbcore`
   - `com.ibm.msg:com.ibm.msg.client.wmq.factories`
   - `com.ibm.msg:com.ibm.msg.client.wmq`

3. **Old JDBC drivers:**
   - `com.oracle:ojdbc14`
   - `ojdbc14:ojdbc14`

4. **MTS messaging (deprecated):**
   - `com.barclays.is:is_messaging`

5. **IS framework — Java 21 incompatible versions:**
   - `com.barclays.mca:is-fwork-slf4j` version < 6.x
   - `com.barclays.mca:is-logging-slf4j` version < 6.x
   > v1.x uses `sun.reflect.Reflection` (removed in Java 9) → all tests fail with `NoClassDefFoundError: sun/reflect/Reflection`. Upgrade to `6.3.+`.

**Instruction for Claude:**
Search all `.gradle` files for these deprecated dependency patterns. List which ones are found.

---

### Task 1.7: Search Property Files

**Objective:** Find property files and check for outdated configurations

**File patterns to search:** `*.properties`, `*.yml`, `*.yaml`

**Property patterns to search for:**

1. **MQ SSL Cipher Suite (needs update):**
   - Pattern: `mq.mca.connection.sslCipherSuite`
   - Old value: `TLS_RSA_WITH_AES_128_CBC_SHA256`
   - New value: `TLS_AES_256_GCM_SHA384`

2. **MQ Connection Factory (needs javax to jakarta change):**
   - Pattern: `implementationClass.*com.ibm.mq.jms`
   - Old value contains: `com.ibm.mq.jms.MQQueue.MQQueueConnectionFactory`
   - New value contains: `com.ibm.mq.jakarta.jms.MQQueue.MQQueueConnectionFactory`

3. **Hibernate Dialect (needs update):**
   - Pattern: `hibernate.dialect.*Oracle10gDialect`
   - Old value: `org.hibernate.dialect.Oracle10gDialect`
   - New value: `org.hibernate.dialect.OracleDialect`

**Instruction for Claude:**
1. Find all property files recursively
2. Search for the above property patterns
3. Note which properties exist and what their current values are

---

### Task 1.8: Search Java Code for javax Imports

**Objective:** Find Java files still using `javax.*` packages that need migration to `jakarta.*`

**Search patterns in `*.java` files:**
- `import javax.servlet`
- `import javax.persistence`
- `import javax.validation`
- `import javax.annotation`
- `import javax.inject`
- `import javax.jms`
- `import javax.xml.bind`

**Instruction for Claude:**
Search all `.java` files for `import javax.` patterns. List files that need javax to jakarta migration. Note: Not all javax packages changed - only Java EE / Jakarta EE ones (not javax.crypto, javax.net, javax.sql.DataSource etc.).

---

### Task 1.8a: Search Java Code for Deprecated Date Constructor

**Search pattern in `*.java` files:** `new Date("`

**Instruction for Claude:**
Search all `.java` files for `new Date("`. List any matches — replace with `Date.from(LocalDate.of(...).atStartOfDay(ZoneId.systemDefault()).toInstant())`. Remove any `@SuppressWarnings("deprecation")` on the same field.

---

### Task 1.9: Search Java Code for @Autowired on @Bean (Spring Boot 3.5+ only)

**Objective:** Find @Bean methods with @Autowired annotation (invalid in Spring 6.2+)

**File pattern:** `*.java`

**Search approach:**
1. Find Java files containing both `@Bean` and `@Autowired` annotations
2. Read those files to check if `@Autowired` is specifically on `@Bean` methods

**Instruction for Claude:**
Search for Java files containing both annotations, then analyze to confirm if @Autowired needs removal from @Bean methods.

---

### Task 1.10: Search for JAXB Dependencies (if present)

**Objective:** Find JAXB-related dependencies that need updating

**Search patterns in `.gradle` files:**
- `com.sun.xml.bind:jaxb-core` (should be removed)
- `jaxb2-maven-plugin` or `jaxb-maven-plugin` (version update needed)
- `jakarta.xml.soap` (version update needed)

**Instruction for Claude:**
Search all `.gradle` and `.xml` files for JAXB-related dependencies.

---

### Task 1.11: Generate Analysis Report

**Objective:** Summarize findings based on the migration type you're running

**Instruction for Claude:**
Create a report showing:

#### If migration_type = mca1:

**You're migrating an MCA1 application** (you ran `/mca1-jdk-upgrade`).

```
MCA1 MIGRATION ANALYSIS REPORT
===============================

GRADLE FILES SCANNED:
  - List all .gradle files found

MCA1 DEPENDENCIES FOUND (primary - will be upgraded):
  - [artifact:version] in [file-path]
  - ...
  (or "None found" if empty)

MCA2 DEPENDENCIES FOUND (cross-dependencies - will be upgraded alongside MCA1):
  - [artifact:version] in [file-path]
  - ...
  (or "None found" if empty)
```

#### If migration_type = mca2:

**You're migrating an MCA2 application** (you ran `/mca2-jdk-upgrade`).

```
MCA2 MIGRATION ANALYSIS REPORT
===============================

GRADLE FILES SCANNED:
  - List all .gradle files found

MCA2 DEPENDENCIES FOUND (primary - will be upgraded):
  - [artifact:version] in [file-path]
  - ...
  (or "None found" if empty)

MCA1 DEPENDENCIES FOUND (legacy - will be removed):
  - [artifact:version] in [file-path]
  - ...
  (or "None found - good!" if empty)
```

**Common report sections (both types):**

```
SPRING BOOT PLUGIN:
  - [version] in [file-path]
  - Action: Update to 3.3.+ or 3.5.+
  (or "Not found" if empty)

DEVOPS PLUGINS FOUND:
  - [plugin:version] in [file-path]
  - ...

DEPRECATED DEPENDENCIES FOUND:
  - [groupId:artifactId] in [file-path]
  - ...
  (or "None found - good!" if empty)

PROPERTY FILES SCANNED:
  - List all property files found

PROPERTIES NEEDING UPDATE:
  - [property-key] in [file-path]: current=[value] -> new=[value]
  - ...
  (or "None found" if empty)

JAVA FILES:

JAVAX IMPORTS (need jakarta migration):
  - [import-pattern] in [file-path]
  - ...
  (or "None found" if empty)

@AUTOWIRED ON @BEAN (Spring Boot 3.5+ only):
  - [file-path:line]
  - ...
  (or "None found" if empty)

JAXB DEPENDENCIES:
  - [groupId:artifactId] in [file-path]
  - ...
  (or "None found" if empty)
```

---

## Phase 2: Create Selective Update Plan

**Objective:** Generate a plan that ONLY updates what was found in Phase 1

**Instruction for Claude:**
Based on the analysis report and your migration type, create a migration plan that:

1. Updates ONLY the primary MCA dependencies that exist

#### If migration_type = mca1:
2. Updates ONLY the MCA2 cross-dependencies that exist (for compatibility with upgraded MCA1)

#### If migration_type = mca2:
2. Removes ONLY the MCA1 legacy dependencies that were found (MCA2 replaces MCA1)

**Common steps (both types):**
3. Removes ONLY the deprecated dependencies that were found
4. Updates ONLY the properties that need changing
5. Fixes ONLY the code issues that were identified
6. **Skips everything else that doesn't exist in the project**

---

## Phase 3: Execute Changes

#### If migration_type = mca1:

### You're Migrating an MCA1 Application

**MCA1 and MCA2 Cross-Dependency Upgrade:**
- Upgrade MCA1 dependencies to 6.2+/6.3+
- If any MCA2 dependencies were found in Phase 1, upgrade them to 2.2+/2.3+ for compatibility
- Both must be upgraded together

**Instruction for Claude:**
Upgrade MCA1 dependencies. If MCA2 dependencies were found in Phase 1, upgrade those too.

#### If migration_type = mca2:

### You're Migrating an MCA2 Application

**MCA2 Upgrade and MCA1 Removal:**
- Upgrade MCA2 dependencies to 2.2+/2.3+
- If any legacy MCA1 dependencies were found in Phase 1, remove them (MCA2 replaces MCA1 functionality)

**Instruction for Claude:**
Upgrade MCA2 dependencies. If MCA1 dependencies were found in Phase 1, remove them after confirming MCA2 equivalents exist in the project.

---

### Task 3.0: Add Resolution Strategy Cache Settings (always)

Add `cacheChangingModulesFor` and `cacheDynamicVersionsFor` to **both** `buildscript configurations.all` AND the main `configurations.all`.

**Why:** Dynamic version ranges (`2.3.+`, `8.2.+`, `3.3.+`) and `changing = true` artifacts use Gradle's default 24-hour caching. Without these settings, stale versions can be resolved unexpectedly.

**Step 1: Update buildscript `configurations.all`**

In the `buildscript { ... }` block, find or create `configurations.all { ... }`:

```gradle
buildscript {
    configurations.all {
        resolutionStrategy.cacheChangingModulesFor 0, 'seconds'
        resolutionStrategy.cacheDynamicVersionsFor 0, 'seconds'
    }
    ...
}
```

**Step 2: Update main `configurations.all`**

Outside the `buildscript` block, find or create `configurations.all { resolutionStrategy { ... } }`:

```gradle
configurations.all {
    resolutionStrategy {
        cacheChangingModulesFor 0, 'seconds'
        cacheDynamicVersionsFor 0, 'seconds'
        // any existing forcedModules stay here
    }
}
```

If a `configurations.all` block already exists, merge the two cache lines into the existing `resolutionStrategy` block.

**Instruction for Claude:**
Use Read and Edit tools to add or merge these settings in both the buildscript and main configurations.all blocks.

---

### VERSION FORMAT CONVENTION: Barclays Internal Artifacts

**RULE:** When a Nexus search returns a version in `major.minor.patch` format for a **Barclays internal artifact**, declare the dependency as `major.minor.+` in build.gradle.

| Nexus returns | Write in build.gradle |
|---|---|
| `1.0.036` | `1.0.+` |
| `03.0011.001` | `03.0011.+` |
| `2.3.021` | `2.3.+` |
| `6.3.019` | `6.3.+` |

**Do NOT use `major.minor.+` for** 4-part versions (e.g., `14.04.001.0`) — pin those explicitly.

**Why:** Barclays internal artifacts release patches frequently within a minor version. `major.minor.+` keeps the build on the latest compatible patch without manual version bumps.

---

### Task 3.1: Update Spring Boot Gradle Plugin (if found)

**If Spring Boot plugin was found:**
- **Find:** `id 'org.springframework.boot' version '[old-version]'`
- **Replace with:** `id 'org.springframework.boot' version '3.3.+'` (or `3.5.+` for latest)

**If spring-boot-gradle-plugin dependency was found:**
- **Find:** `org.springframework.boot:spring-boot-gradle-plugin:[old-version]`
- **Replace with:** `org.springframework.boot:spring-boot-gradle-plugin:3.3.+` (or `3.5.+`)

**Also add `io.spring.dependency-management` plugin (required for Spring Boot 3.x):**

Use Grep to check if `io.spring.dependency-management` already exists. If missing, add it immediately after the `org.springframework.boot` apply line. Without it, BOM-managed transitives with empty versions fail to resolve.

**Instruction for Claude:**
Use Edit tool to update the Spring Boot plugin version in the identified files. Add `io.spring.dependency-management` if missing.

---

### Task 3.2: Update DevOps Plugins (if found)

**If gradle-eps2-war-plugin was found:**

CRITICAL: This plugin requires BOTH artifact name AND plugin ID to be updated.

1. **Update classpath dependency:**
   - **Find:** `gradle-eps2-war-plugin`
   - **Replace with:** `gradle-eps-war-plugin`
   - **Update version to:** `8.2.+`

2. **Update plugin application statement:**
   - **Find:** `apply plugin : 'eps2-war'` or `apply plugin: "eps2-war"`
   - **Replace with:** `apply plugin : 'eps-war'` (preserve original quote style)

**If gradle-mca-jar-plugin was found:**
- **Update version to:** `8.2.+`

**Remove deprecated DevOps plugins (if found):**
- Remove lines containing these plugins:
  - `gradle-script-files-plugin`
  - `gradle-eps-nexus-plugin`
  - `gradle-jacoco-report-plugin`
  - `gradle-eps-code-coverage-plugin`
  - `gradle-code-coverage-plugin`
  - `gradle-mca-versioning-plugin`
  - `gradle-mca-eclipse-plugin`
  - `gradle-tagversion-plugin`
  - `gradle-dependency-check-plugin`
  - `gradle-oidlt-plugin`

**Instruction for Claude:**
Use Edit tool to make these replacements in the identified files. For eps2-war plugin, BOTH the classpath dependency and the apply plugin statement MUST be updated.

---

### Tasks 3.3-3.6: Update MCA Dependencies

#### If migration_type = mca1:

**Task 3.3: Update MCA1 BOM Version (if found)**

- **Find:** `com.barclays.eps:mca-dependencies:[old-version]`
- **Replace with:** `com.barclays.eps:mca-dependencies:6.2.+` (or `6.3.+` for Spring Boot 3.5)

**Task 3.4: Update MCA2 BOM Version (cross-dependency, if found)**

- **Find:** `com.barclays.global.mca:mca-dependencies:[old-version]`
- **Replace with:** `com.barclays.global.mca:mca-dependencies:2.2.+` (or `2.3.+` for Spring Boot 3.5)

**Task 3.5: Update Individual MCA1 Dependencies (if not using BOM)**

For each MCA1 dependency found:
- **Find:** `com.barclays.eps:[artifact]:[old-version]`
- **Replace with:** `com.barclays.eps:[artifact]:6.2.+` (or `6.3.+`)

**Task 3.6: Update Individual MCA2 Dependencies (cross-dependency, if not using BOM)**

For each MCA2 dependency found:
- **Find:** `com.barclays.global.mca:[artifact]:[old-version]`
- **Replace with:** `com.barclays.global.mca:[artifact]:2.2.+` (or `2.3.+`)

#### If migration_type = mca2:

**Task 3.3: Update MCA2 BOM Version (if found)**

- **Find:** `com.barclays.global.mca:mca-dependencies:[old-version]`
- **Replace with:** `com.barclays.global.mca:mca-dependencies:2.2.+` (or `2.3.+` for Spring Boot 3.5)

**Task 3.4: Update Individual MCA2 Dependencies (if not using BOM)**

For each MCA2 dependency found:
- **Find:** `com.barclays.global.mca:[artifact]:[old-version]`
- **Replace with:** `com.barclays.global.mca:[artifact]:2.2.+` (or `2.3.+`)

**Task 3.5: Remove MCA1 Dependencies (if found)**

For each MCA1 dependency found in Phase 1:
- **Action:** Remove the entire dependency line
- **Also remove:** MCA1 BOM line (`com.barclays.eps:mca-dependencies`) if present

**Example:**
```gradle
// Remove these lines:
implementation 'com.barclays.eps:scp-eps-core-comm:5.x.x'
implementation 'com.barclays.eps:scp-eps-libs-audit:5.x.x'

// Also remove BOM if present:
implementation platform('com.barclays.eps:mca-dependencies:5.x.x')
```

**Instruction for Claude:**
Use Edit tool to remove all MCA1 dependency lines from the identified files. Confirm with user before removing if unsure about MCA2 equivalent availability.

---

### Task 3.7: Remove Deprecated Dependencies (if found)

**For each deprecated dependency found in Phase 1:**
- **Action:** Remove the entire dependency line
- **Example:**
  ```gradle
  // Remove this line:
  implementation 'org.apache.logging.log4j:log4j-core'
  ```

**Instruction for Claude:**
Use Edit tool to remove deprecated dependency lines from the identified files.

---

### Task 3.7a: Upgrade IS Framework to Java 21 Compatible Version (if found)

**If `com.barclays.mca:is-fwork-slf4j` or `com.barclays.mca:is-logging-slf4j` version < 6.x was found in Phase 1:**
- Upgrade both to `6.3.+`

**Also:** If `mca-logging-spy` is not in `forcedModules`, add `'com.barclays.global.mca:mca-logging-spy:2.3.+'`. It is a BOM-managed transitive of `scp-eps-test-common` with an empty version string that causes `Could not resolve` errors.

**Instruction for Claude:**
Use Edit tool to upgrade `is-fwork-slf4j` and `is-logging-slf4j` if < 6.x. Add `mca-logging-spy:2.3.+` to forcedModules if missing.

---

### Task 3.7b: Migrate Tests to JUnit 5 (if JUnit 4 tests exist)

**Detection:** `Grep(pattern="import org.junit.Test|junit:junit|jmock-junit4", path="build.gradle")`

**If JUnit 4 tests are present, migrate them to JUnit 5:**

**build.gradle changes:**
- Replace `junit:junit` with `org.junit.jupiter:junit-jupiter` (via `spring-boot-starter-test` BOM)
- Replace `jmock-legacy:2.x` → `2.12.0`, `jmock-junit4:2.x` → `2.12.0` (ByteBuddy-based, Java 9+ compatible)
- Add `testImplementation 'org.springframework.boot:spring-boot-starter-test'`
- Remove explicit `mockito-core` and `spring-test` versions (BOM-managed)
- Add `useJUnitPlatform()` to `test {}` block
- Add `--add-opens` JVM args to `test {}`:
  ```gradle
  "--add-opens=java.base/java.lang=ALL-UNNAMED",
  "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED",
  "--add-opens=java.base/java.util=ALL-UNNAMED",
  "--add-opens=java.base/java.io=ALL-UNNAMED"
  ```

**Java test file changes** (for each test file):
- `import org.junit.Test` → `import org.junit.jupiter.api.Test`
- `import org.junit.Before` → `import org.junit.jupiter.api.BeforeEach`
- `import org.junit.After` → `import org.junit.jupiter.api.AfterEach`
- `import org.junit.Assert.*` → `import org.junit.jupiter.api.Assertions.*`
- `extends TestCase` or `extends GenericTestCase` → remove, add `@ExtendWith(MockitoExtension.class)` if using Mockito
- Remove `@RunWith(...)` annotations — JUnit 5 uses extensions
- `setUp()` annotated with nothing → add `@BeforeEach`
- `Assert.assertEquals` → `Assertions.assertEquals`
- `assertNotNull(true)` → `assertTrue(true)` or simply remove (it always passes)

**Instruction for Claude:**
Search for all test files with JUnit 4 imports. Migrate build.gradle and all test Java files to JUnit 5.

---

### Task 3.8: Update Properties (if found)

**For each property needing update found in Phase 1:**

1. **MQ SSL Cipher (if found):**
   - **Find:** `mq.mca.connection.sslCipherSuite=TLS_RSA_WITH_AES_128_CBC_SHA256`
   - **Replace:** `mq.mca.connection.sslCipherSuite=TLS_AES_256_GCM_SHA384`

2. **MQ Connection Factory (if found):**
   - **Find:** `com.ibm.mq.jms.MQQueue.MQQueueConnectionFactory`
   - **Replace:** `com.ibm.mq.jakarta.jms.MQQueue.MQQueueConnectionFactory`

3. **Hibernate Dialect (if found):**
   - **Find:** `org.hibernate.dialect.Oracle10gDialect`
   - **Replace:** `org.hibernate.dialect.OracleDialect`

**Instruction for Claude:**
Use Edit tool to update properties in the identified files.

---

### Task 3.9: Update Gradle Wrapper (always)

**File:** `gradle/wrapper/gradle-wrapper.properties`

**Update:**
- **Find:** `distributionUrl=.*gradle.*-bin.zip` (matches any existing distributionUrl)
- **Replace:** `distributionUrl=https\://nexus.barcapint.com/nexus/content/groups/barclays/gradle-8.5-bin.zip`

**Important:** Use the flat path format (NOT Maven-style `.../gradle/gradle/VERSION/...`). The correct format is `.../barclays/gradle-VERSION-bin.zip`.

**Instruction for Claude:**
Use Edit tool to update the gradle wrapper URL. Ensure the backslash escaping (`https\://`) is preserved in the file.

---

### Task 3.10: Fix Bootclasspath Flags (if found)

**Search for:** `-Xbootclasspath/p:` or `-Xbootclasspath:`

**If found in any .gradle file:**
- **Replace:** `-Xbootclasspath/a:`

**Instruction for Claude:**
Search for old bootclasspath flags and replace with the Java 21 compatible version.

---

### Task 3.11: Remove @Autowired from @Bean Methods (if found)

**For each Java file identified in Phase 1:**
- **Find:** `@Autowired` annotation on methods that also have `@Bean`
- **Action:** Remove the `@Autowired` annotation line
- **Keep:** The `@Bean` annotation and method

**Instruction for Claude:**
Use Edit tool to remove @Autowired annotations from @Bean methods.

---

### Task 3.12: Migrate javax Imports to jakarta (if found)

**For each Java file identified in Phase 1 with javax imports:**

Replace the following import prefixes:

| Old Import                              | New Import                               |
|-----------------------------------------|------------------------------------------|
| `import javax.servlet`                  | `import jakarta.servlet`                 |
| `import javax.persistence`              | `import jakarta.persistence`             |
| `import javax.validation`               | `import jakarta.validation`              |
| `import javax.annotation.PostConstruct` | `import jakarta.annotation.PostConstruct`|
| `import javax.annotation.PreDestroy`    | `import jakarta.annotation.PreDestroy`   |
| `import javax.annotation.Resource`      | `import jakarta.annotation.Resource`     |
| `import javax.annotation.ManagedBean`   | `import jakarta.annotation.ManagedBean`  |
| `import javax.inject`                   | `import jakarta.inject`                  |
| `import javax.jms`                      | `import jakarta.jms`                     |
| `import javax.xml.bind`                 | `import jakarta.xml.bind`               |

**Do NOT change these javax packages (they remain in Java SE):**
- `javax.crypto`
- `javax.net`
- `javax.sql` (except `javax.sql.DataSource` which stays)
- `javax.security.auth`
- `javax.security.cert`
- `javax.naming`
- `javax.management`
- `javax.imageio`
- `javax.swing`
- `javax.xml.parsers`
- `javax.xml.transform`
- `javax.xml.xpath`

**Instruction for Claude:**
For each Java file with javax imports found in Phase 1, use Edit tool with replace_all to change the import prefix from `javax.` to `jakarta.` only for the Jakarta EE packages listed above. Leave Java SE javax packages unchanged.

---

### Task 3.12a: Fix Deprecated Date(String) Constructor (if found)

**If `new Date("` was found in Task 1.8a:**

Replace with: `Date.from(LocalDate.of(YYYY, MM, DD).atStartOfDay(ZoneId.systemDefault()).toInstant())`

Parse the date string to extract year/month/day. Remove any `@SuppressWarnings("deprecation")` on the same field.

**Instruction for Claude:**
For each file found in Task 1.8a, use Edit tool to replace the deprecated constructor.

---

### Task 3.13: Update JAXB Dependencies (if found)

**If `com.sun.xml.bind:jaxb-core` was found:**
- **Action:** Remove the entire dependency line (this is now included in the JAXB runtime)

**If `jaxb2-maven-plugin` was found (in `.gradle` or `.xml` files):**
- **For Spring Boot 3.3 (javax to jakarta transition):** Update version to `2.5.x`
- **For Spring Boot 3.5 (full jakarta):** Update version to `3.x`

**If `jaxb-maven-plugin` was found:**
- **Update version to:** `4.x`

**If `jakarta.xml.soap:jakarta.xml.soap-api` was found:**
- **Update version to:** latest release (e.g., `3.0.+`)

**Instruction for Claude:**
Use Edit tool to remove jaxb-core dependency and update JAXB plugin versions in the identified files.

---

## Phase 4: Verification

**Instruction for Claude:**
After making changes, recommend the user:
1. Build the project: `./gradlew clean build`
2. Run tests: `./gradlew test`
3. Check for dependency conflicts
4. Verify application starts
5. Test integrations (MQ, DB, etc.)

---

# REFERENCE DATA

## Target Versions

#### If migration_type = mca1:

| Component     | Version for 6.2/2.2 | Version for 6.3/2.3 |
|---------------|----------------------|----------------------|
| Java          | 21                   | 21                   |
| Spring Boot   | 3.3.+                | 3.5.+                |
| Gradle        | 8.5                  | 8.5                  |
| MCA1          | 6.2.+                | 6.3.+                |
| MCA2          | 2.2.+                | 2.3.+                |
| DevOps Plugin | 8.2.+                | 8.2.+                |

**Note:** Use 6.2/2.2 for stable production, 6.3/2.3 for latest features (requires Spring 6.2 code changes).

#### If migration_type = mca2:

| Component     | Version for 2.2 | Version for 2.3 |
|---------------|------------------|------------------|
| Java          | 21               | 21               |
| Spring Boot   | 3.3.+            | 3.5.+            |
| Gradle        | 8.5              | 8.5              |
| MCA2          | 2.2.+            | 2.3.+            |
| DevOps Plugin | 8.2.+            | 8.2.+            |

**Note:** Use 2.2 for stable production, 2.3 for latest features (requires Spring 6.2 code changes).

---

## Complete MCA2 Library List (com.barclays.global.mca)

#### If migration_type = mca1:
Update these IF found in your project (cross-dependency upgrade):

#### If migration_type = mca2:
Update these IF found in your project:

**Logging:**
- `mca-activity-logging`
- `mca-ecrime-logging`
- `mca-logging-aspects`
- `mca-logging-config-dynamic`
- `mca-logging-config-logback`
- `mca-logging-config-logback-json`
- `mca-logging-config-test`
- `mca-logging-performance`
- `mca-spy`

**Context Management:**
- `mca-context`
- `mca-context-utils`
- `mca-context-store-ehcache`
- `mca-context-store-mongo`
- `mca-context-store-rdb`

**Security:**
- `mca-entitlement`
- `mca-masking`
- `mca-oauth-validator-core`
- `mca-sso`
- `mca-sso-bam`
- `mca-spring-boot-ssl`
- `mca-jceks-spring-properties-processor`

**Configuration:**
- `mca-placeholder-converter`
- `mca-placeholder-resolvers`
- `mca-placeholder-starter`
- `mca-placeholder-vault-resolver`

**Service Integration:**
- `mca-service-client`
- `mca-service-client-starter`
- `mca-service-locator`
- `mca-remote-discovery`
- `mca-consul-process-discovery`

**Routing & Proxy:**
- `mca-router-api`
- `mca-router-http`
- `mca-secure-proxy-api`
- `mca-secure-proxy-core`
- `mca-secure-proxy-routing-gateway`

**Error & Response Handling:**
- `mca-exception-handling-core`
- `mca-exception-handling-spring`
- `mca-response-handling-core`

**Core Framework:**
- `mca-eps-core`
- `mca-filter-core`
- `mca-process`
- `mca-process-lib`
- `mca-referencedata`
- `mca-schema-validation`
- `mca-external-resources`

**Utilities:**
- `mca-common-utils`
- `mca-web-utils`
- `mca-spring-context-utils`
- `mca-refresh-utils`
- `mca-i18n`

**Content & Integration:**
- `mca-bcag`
- `mca-cms`

**Client Libraries:**
- `mca-bem-client`
- `mca-mis-client`
- `mca-tiaaas-client`

**Testing & Legacy:**
- `mca-test-common`
- `mca-legacy-common`

**BOM:** `com.barclays.global.mca:mca-dependencies:2.2.+` (or `2.3.+`)

---

## MCA1 Library List (com.barclays.eps)

#### If migration_type = mca1:
Update these IF found in your project:

#### If migration_type = mca2:
These MCA1 dependencies should be removed if found during MCA2 migration:

- `scp-eps-core-comm`
- `scp-eps-libs-accesscontrol`
- `scp-eps-libs-appconfig`
- `scp-eps-libs-audit`
- `scp-eps-libs-content`
- `scp-eps-libs-filters`
- `scp-eps-libs-preferences`
- `scp-eps-libs-transientstate`
- `scp-eps-libs-bem`
- `scp-eps-test-common`

#### If migration_type = mca1:
**BOM:** `com.barclays.eps:mca-dependencies:6.2.+` (or `6.3.+`)

#### If migration_type = mca2:
**BOM:** `com.barclays.eps:mca-dependencies` (remove entirely)

---

**Last Updated:** 2026-02-22
**Source:** Barclays MCA OpenRewrite (Java21.yml, common.yml, rewrite.yml)

#### If migration_type = mca1:
**Scope:** MCA1 (com.barclays.eps) projects with cross-dependency MCA2 upgrade
**MCA1 Libraries:** 10 artifacts
**MCA2 Libraries:** 57 artifacts (upgraded if present alongside MCA1)

#### If migration_type = mca2:
**Scope:** MCA2 (com.barclays.global.mca) projects with MCA1 dependency removal
**MCA2 Libraries:** 57 artifacts
**MCA1 Libraries:** 10 artifacts (to be removed)

**Deprecated Items:** 32 items to remove if present

## Agent Self-Check

- [ ] Skill loaded before the upgrade phase it governs
- [ ] Source version (Java 8 / Spring Boot 2.7) confirmed before applying upgrade patterns
- [ ] Build verified with ./gradlew clean build after each phase
- [ ] No MCA1/legacy patterns remain after migration step
- [ ] Test suite still passes after code changes
- [ ] Upgrade summary logged to migration report
