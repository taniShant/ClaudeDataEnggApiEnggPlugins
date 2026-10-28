---
name: devops-gradle-plugin
description: >
  MCA DevOps Gradle plugin migration for EPS applications. Use when user says
  "migrate DevOps plugins", "upgrade gradle plugins", "consolidate gradle plugins",
  or "fix gradle build". Replaces legacy individual DevOps plugins with the unified
  Java 21 plugin, removes aPaaS URL references, deletes unused Gradle files,
  deletes services.xml, updates Gradle wrapper distribution URL, and validates the build.
  Runs independently of MCA1-to-MCA2 code migration.
user-invocable: false
source: barclays-claude-code-plugins/plugins/mca1-to-mca2-eps/skills/devops-gradle-plugin/SKILL.md
owner: MCA Core Engineering (mcaplatform@barclays.com)
review-trigger: When gradle-eps-war-plugin major version changes or new legacy plugins are identified
status: Full
---

# DevOps Gradle Plugin Migration

## Overview

MCA1 projects use many individual DevOps Gradle plugins (ear, war, nexus, jacoco, findbugs, versioning, etc.) spread across build files. These must be consolidated into a single unified plugin for Java 21.

**This skill is independent of MCA1-to-MCA2 code migration.** It applies to:
- Any MCA1 project that needs DevOps plugin modernization
- Projects before or after MCA2 code migration
- Projects already in WAR structure

## Pre-requisite: Verify Gradle Build

Before making any plugin changes, confirm the project builds successfully in its current state:

```bash
cd <project_root> && ./gradlew clean build 2>&1
```

**If the build FAILS:**
- Do NOT proceed with plugin migration until the existing build is fixed
- Flag the build errors to the user — these must be resolved first

**If the build SUCCEEDS:**
- Proceed with the migration steps below

## Detection

Scan for old DevOps plugins and related artifacts:

```bash
# Find old DevOps plugin classpath entries
grep -n "gradle-ear-plugin\|gradle-eps-war-plugin\|gradle-eps2-war-plugin\|gradle-script-files-plugin\|gradle-eps-nexus-plugin\|gradle-jacoco-report-plugin\|gradle-eps-code-coverage-plugin\|gradle-dependency-check-plugin\|gradle-mca-findbugs-plugin\|gradle-mca-versioning-plugin\|gradle-mca-eclipse-plugin\|gradle-integration-test-plugin\|gradle-eps-release-notes-plugin\|gradle-tagversion-plugin\|gradle-json-plugin\|gradle-oidlt-plugin\|mca-common-utility" <project_root>/build.gradle

# Find old aPaaS URL references
grep -rn "mca-apache-3970" <project_root>/build.gradle <project_root>/gradle/ 2>/dev/null

# Find old plugin apply statements
grep -n "apply plugin.*eps-ear\|apply plugin.*eps2-war\|apply plugin.*integration-test" <project_root>/build.gradle

# Find unused gradle files (EAR-related build files, old subproject gradle files)
ls <project_root>/*.gradle 2>/dev/null
ls <project_root>/gradle/scripts/ 2>/dev/null

# Check for services.xml (legacy MCA1 descriptor)
ls <project_root>/services.xml 2>/dev/null

# Check Gradle wrapper distribution URL
grep "distributionUrl" <project_root>/gradle/wrapper/gradle-wrapper.properties 2>/dev/null
```

**Positive indicators (needs migration):**
- Any old DevOps plugin classpath entries found (version 1.0.x or 1.1.x)
- aPaaS URL references (`mca-apache-3970.appcloud-np.barclays.intranet`)
- Old plugin apply statements (`eps-ear`, `eps2-war`)
- Unused gradle files from the EAR structure (e.g., `war.gradle`, EAR-related scripts)
- `services.xml` present at project root
- Gradle wrapper `distributionUrl` pointing to `services.gradle.org` or old Nexus path instead of `https://nexus.barcapint.com/nexus/content/groups/barclays/gradle-8.5-bin.zip`

**Negative indicators (already migrated):**
- `gradle-eps-war-plugin:8.2` already present in build.gradle
- `apply plugin: 'eps-war'` already present
- No old DevOps plugin references found
- No `services.xml` at project root
- Gradle wrapper `distributionUrl` already set to `https://nexus.barcapint.com/nexus/content/groups/barclays/gradle-8.5-bin.zip`

## Migration Steps

### Step 1: Identify and delete unused Gradle files

After EAR-to-WAR conversion (or in any MCA1 project), there may be leftover Gradle files that are no longer referenced. These should be identified and deleted.

**Common unused files to look for:**
- `war.gradle` — old subproject build file from EAR structure
- Old EAR-level gradle scripts that applied to the parent project
- Any `.gradle` files at root that are not `build.gradle`, `settings.gradle`, or actively referenced

**Detection:**
```bash
# List all .gradle files at root
ls <project_root>/*.gradle 2>/dev/null

# Check which gradle files are referenced from build.gradle or settings.gradle
grep -n "apply from" <project_root>/build.gradle 2>/dev/null
grep -n "apply from" <project_root>/settings.gradle 2>/dev/null

# List gradle scripts directory
ls <project_root>/gradle/scripts/ 2>/dev/null
```

**Action:**
- For each `.gradle` file at root (other than `build.gradle` and `settings.gradle`), check if it is referenced by `apply from` in build.gradle
- If NOT referenced, confirm with user and delete
- For files in `gradle/scripts/`, check if they are referenced. Delete unreferenced ones after user confirmation

**User confirmation required:** Show the list of unused gradle files and ask: "These gradle files are not referenced and will be deleted. Confirm?"

### Step 2: Remove references to legacy aPaaS Gradle scripts URL

Search for and remove any references to the old OpenShift Gradle project URL:

```bash
grep -rn "mca-apache-3970.appcloud-np.barclays.intranet/gradle-common" <project_root>/build.gradle <project_root>/gradle/ 2>/dev/null
```

If scripts are being downloaded from that URL, download them locally and place in `${rootDir}/gradle/scripts`:

**Before:**
```gradle
ext.pluginBaseDirectory = 'https://mca-apache-3970.appcloud-np.barclays.intranet/gradle-common/gradle1/'
apply from: "${pluginBaseDirectory}/eps-ear/ftpupload.gradle"
```

**After:**
```gradle
ext.pluginBaseDirectory = '${rootDir}/gradle/scripts'
apply from: "${pluginBaseDirectory}/ftpupload.gradle"
```

### Step 3: Replace all old DevOps plugin classpath dependencies

The old MCA1 build had many individual plugin dependencies. These are ALL replaced by a single unified plugin.

**Plugin version for Java 21:** `8.2` (use incremental version `8.2.+`)

**Old MCA1 plugins to REMOVE (all of these):**
```gradle
// REMOVE all of these individual plugin classpath entries:
classpath("com.barclays.mca.devops:gradle-ear-plugin:1.0.+")
classpath("com.barclays.mca.devops:gradle-eps-war-plugin:1.0.+")      // old version
classpath("com.barclays.mca.devops:gradle-eps2-war-plugin:1.0.+")     // old MCA2 version
classpath("com.barclays.mca.devops:gradle-script-files-plugin:1.0.+")
classpath("com.barclays.mca.devops:gradle-eps-nexus-plugin:1.0.+")
classpath("com.barclays.mca.devops:gradle-jacoco-report-plugin:1.0.+")
classpath("com.barclays.mca.devops:gradle-eps-code-coverage-plugin:1.0.+")
classpath("com.barclays.mca.devops:gradle-dependency-check-plugin:1.0.+")
classpath("com.barclays.mca.devops:gradle-mca-findbugs-plugin:1.0.+")
classpath("com.barclays.mca.devops:gradle-mca-versioning-plugin:1.0.+")
classpath("com.barclays.mca.devops:gradle-mca-eclipse-plugin:1.0.+")
classpath("com.barclays.mca.devops:gradle-integration-test-plugin:1.0.+")
classpath("com.barclays.mca.devops:gradle-eps-release-notes-plugin:1.0.+")
classpath("com.barclays.mca.devops:gradle-tagversion-plugin:1.0.+")
classpath("com.barclays.mca.devops:gradle-json-plugin:1.0.+")
classpath("com.barclays.mca.devops:gradle-oidlt-plugin:1.0.5")
classpath("com.barclays.buk.devops.cpe.gradle:gradle-release-notes-plugin:1.1.+")
classpath("com.barclays.buk.devops.cpe.gradle:gradle-code-coverage-plugin:1.1.+")

// ALSO REMOVE mca-common-utility (MCA1 buildscript utility plugin, not needed in MCA2):
classpath("com.barclays.global.mca:mca-common-utility:X.X.X")
```

**Also REMOVE old plugin apply statements:**
```gradle
// REMOVE these:
apply plugin: 'eps-ear'
apply plugin: 'eps2-war'           // old MCA2 plugin name
apply plugin: 'integration-test'
apply plugin: 'common-utility'    // from mca-common-utility, not needed in MCA2
// and any other old DevOps plugin applies
```

**New unified plugin (REPLACE WITH):**
```gradle
buildscript {

    dependencies {
        // MCA Devops plugins - START
        classpath("com.barclays.mca.devops:gradle-eps-war-plugin:8.2.+")
        // MCA Devops plugins - END

        // Other application specific plugins (keep as needed) - START
        classpath("info.solidsoft.gradle.pitest:gradle-pitest-plugin:1.15.0")
        classpath("org.springframework.boot:spring-boot-gradle-plugin:3.3.4")
        classpath("org.openrewrite:plugin:6.26.0")
        // Other application specific plugins - END
    }

    repositories {
        maven {
            url = uri("https://nexus.barcapint.com/nexus/content/groups/barclays/")
        }
    }
}

// Applying MCA EPS WAR DevOps plugin (single plugin replaces all old ones)
apply plugin: 'eps-war'
```

**For JAR-type projects (libraries, not EPS WARs):**
```gradle
classpath("com.barclays.mca.devops:gradle-mca-jar-plugin:8.2.+")
apply plugin: 'mca-jar'
```

### Step 4: Keep application-specific plugins

Non-DevOps plugins that are application-specific should be kept in the buildscript dependencies. Examples:
- `gradle-pitest-plugin` (mutation testing)
- `spring-boot-gradle-plugin`
- `org.openrewrite:plugin` (code modernization)
- `com.bmuschko:gradle-nexus-plugin` (if still needed)

### Step 5: Keep application-specific gradle scripts

If the project has custom gradle scripts (e.g., `sonar.gradle`, `ftpupload.gradle`, `version.gradle`) in `${rootDir}/gradle/scripts/`, these should be preserved. Only the DevOps plugin classpath entries and their `apply plugin` statements are replaced.

### Step 6: Delete services.xml and MCA1 test XML files

MCA1 projects have a `services.xml` file at the project root and/or in `src/test/resources/`. These are legacy MCA1 service descriptors used for EPS service registration and are not needed in MCA2. MCA1 projects may also have `UserBean.xml` or other test data XML files in `src/test/resources/` that are loaded by `GenericTestCase` — these should also be removed after test migration.

**Detection:**
```bash
ls <project_root>/services.xml 2>/dev/null
ls <project_root>/src/test/resources/services.xml 2>/dev/null
ls <project_root>/src/test/resources/UserBean.xml 2>/dev/null
find <project_root>/src/test/resources -name "*.xml" 2>/dev/null
```

**Action:**
- Delete `services.xml` from both the project root and `src/test/resources/` if present
- Delete `UserBean.xml` from `src/test/resources/` if present (loaded by `GenericTestCase`, no longer needed after JUnit 5 migration)
- Check for any other MCA1 test XML data files and remove if no longer referenced

**User confirmation required:** Show the user the list of XML files to delete and ask: "These XML files are MCA1 legacy artifacts not needed in MCA2. Confirm deletion?"

### Step 7: Update Gradle wrapper distribution URL

The Gradle wrapper must download the Gradle 8.5 distribution from the Barclays internal Nexus repository, not from the public `services.gradle.org`.

**Detection:**
```bash
grep "distributionUrl" <project_root>/gradle/wrapper/gradle-wrapper.properties
```

**Old values (any of these need updating):**
```properties
# Old public URL
distributionUrl=https\://services.gradle.org/distributions/gradle-6.5-bin.zip

# Old Nexus path (third-party group or older Gradle version)
distributionUrl=https\://nexus.barcapint.com/nexus/content/groups/third-party-apps-group/gradle/gradle/4.10.2/gradle-4.10.2-bin.zip
```

**New value (REPLACE WITH):**
```properties
distributionUrl=https://nexus.barcapint.com/nexus/content/groups/barclays/gradle-8.5-bin.zip
```

**Action:**
- Set the active `distributionUrl` line to exactly: `distributionUrl=https://nexus.barcapint.com/nexus/content/groups/barclays/gradle-8.5-bin.zip`
- Comment out or remove any old `distributionUrl` lines
- If the file already has the correct URL, skip this step

## Verification Checklist

After migration, verify:

| Check | Command | Expected |
|-------|---------|----------|
| Unified plugin classpath | `grep "gradle-eps-war-plugin:8.2" build.gradle` | Match found |
| Single `apply plugin: 'eps-war'` | `grep "apply plugin.*eps-war" build.gradle` | Match found |
| No old DevOps plugins | `grep "gradle-ear-plugin\|gradle-eps2-war\|gradle-mca-findbugs\|gradle-mca-eclipse\|gradle-script-files\|gradle-eps-nexus\|gradle-tagversion\|gradle-json-plugin\|gradle-oidlt\|mca-common-utility\|common-utility" build.gradle` | No output |
| No aPaaS URL references | `grep "mca-apache-3970" build.gradle` | No output |
| No unused gradle files | Check for unreferenced `.gradle` files at root | None found |
| No `services.xml` | `ls services.xml 2>/dev/null` | No output |
| Gradle distribution URL | `grep "distributionUrl" gradle/wrapper/gradle-wrapper.properties` | `https://nexus.barcapint.com/nexus/content/groups/barclays/gradle-8.5-bin.zip` |
| Gradle build succeeds | `./gradlew clean build` | BUILD SUCCESSFUL |

## Post-Migration Build Validation

After all changes, run the Gradle build to confirm the project compiles:

```bash
cd <project_root> && ./gradlew clean build 2>&1
```

**If the build SUCCEEDS:** The DevOps plugin migration is complete.

**If the build FAILS:** Analyze the error output. Check the "Common Gradle Build Errors" section below for known fixes. Fix what can be fixed automatically, flag the rest to the user. Do NOT proceed until the build passes.

## Common Gradle Build Errors

### 1. `DirectoryReport.setDestination` NoSuchMethodError

**Error:**
```
* What went wrong:
A problem occurred evaluating root project 'scp-eps-securities'.
> org.gradle.api.reporting.DirectoryReport.setDestination(Ljava/lang/Object;)V
```

**Diagnosis:** Run with `./gradlew clean build --stacktrace`. If the stacktrace shows:
```
Caused by: java.lang.NoSuchMethodError: org.gradle.api.reporting.DirectoryReport.setDestination(Ljava/lang/Object;)V
        at com.barclays.mca.devops.plugins.gradle.JacocoReportPlugin.apply(JacocoReportPlugin.java:42)
        at com.barclays.mca.devops.plugins.gradle.JacocoReportPlugin.apply(JacocoReportPlugin.java:18)
```

**Fix:** Upgrade the JaCoCo report plugin to version 2.0:
```gradle
classpath("com.barclays.mca.devops:gradle-jacoco-report-plugin:2.0.+"){ changing = true }
```

### 2. `Plugin with id 'org.springframework.boot' not found`

**Error:**
```
> Plugin with id 'org.springframework.boot' not found.
```

**Fix:** Add the Spring Boot Gradle plugin to the buildscript dependencies:
```gradle
classpath("org.springframework.boot:spring-boot-gradle-plugin:<Spring_Boot_version_used_in_your_project>")
```
Replace `<Spring_Boot_version_used_in_your_project>` with the actual version (e.g., `3.3.4`, `3.3.8`).

### 3. `Plugin with id 'integration-test' not found`

**Error:**
```
> Plugin with id 'integration-test' not found.
```

**Fix:** Add the integration test plugin to the buildscript dependencies at version 2.0:
```gradle
classpath("com.barclays.mca.devops:gradle-integration-test-plugin:2.0.+"){ changing = true }
```

## Agent Self-Check

- [ ] Initial build verified passing before any changes (`./gradlew clean build` baseline)
- [ ] All old DevOps plugin classpath entries removed (15+ individual plugins replaced by single 8.2.+ plugin)
- [ ] `apply plugin: 'eps-war'` present and old `eps-ear`/`eps2-war`/`integration-test` apply statements removed
- [ ] No aPaaS URL references remain (`mca-apache-3970`)
- [ ] `services.xml` deleted from project root and `src/test/resources/` (confirmed with user)
- [ ] Gradle wrapper `distributionUrl` updated to `https://nexus.barcapint.com/nexus/content/groups/barclays/gradle-8.5-bin.zip`
- [ ] Application-specific plugins (`gradle-pitest-plugin`, `spring-boot-gradle-plugin`, etc.) preserved
- [ ] Final build verified passing after migration (`./gradlew clean build`)
