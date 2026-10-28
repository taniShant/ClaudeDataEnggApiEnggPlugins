# MCA2 Migration Reference — Consolidated

> **Scope:** Build infrastructure (Gradle plugins, wrapper, SSL, API changes), dependency consolidation, platform BOM setup, and Barclays internal library migration rules for Java 8 → 21 / Spring Boot 2.7 → 3.3+.

> **Cross-Platform Note:** All Gradle commands use `$GRADLE_CMD` instead of `./gradlew`. Validation searches use the Grep tool instead of shell `grep`. See CLAUDE.md Cross-Platform Execution section.

> **VERSION VERIFICATION:** Versions in this document may become outdated. Before finalizing any dependency version, verify in Barclays Nexus if a newer version exists. See [nexus_version_lookup.md](nexus_version_lookup.md). Libraries may be in either the `barclays` or `barclays-restricted-releases` repository.

> **ROUTING:** For third-party dependencies (`org.*`, `com.google.*`, `com.fasterxml.*`, etc.), use [third_party_dependencies.md](third_party_dependencies.md). This file covers `com.barclays.*` and `com.barclaycard.*` dependencies plus build infrastructure.

---

## Table of Contents

### Part 1: Build Infrastructure
- [1.1 gradle.properties SSL Configuration](#11-gradleproperties-ssl-configuration)
- [1.2 Gradle Wrapper Configuration](#12-gradle-wrapper-configuration)
- [1.3 Gradle Cache Resolution Strategy](#13-gradle-cache-resolution-strategy)
- [1.4 Gradle Version Compatibility Matrix](#14-gradle-version-compatibility-matrix)
- [1.5 MCA DevOps Gradle Plugins](#15-mca-devops-gradle-plugins)
- [1.6 OpenRewrite Recipe Versions](#16-openrewrite-recipe-versions)
- [1.7 Gradle API Breaking Changes (6→8)](#17-gradle-api-breaking-changes-68)

### Part 2: Dependency Consolidation
- [2.1 External Dependency File Consolidation](#21-external-dependency-file-consolidation)
- [2.2 MCA Platform BOM Setup](#22-mca-platform-bom-setup)

### Part 3: Barclays Internal Libraries
- [3.1 Security Libraries](#31-security-libraries)
- [3.2 MCA Platform Libraries](#32-mca-platform-libraries)
- [3.3 UKC Libraries](#33-ukc-libraries)
- [3.4 EPS Libraries](#34-eps-libraries)
- [3.5 MCA Transitive Dependency Issues](#35-mca-transitive-dependency-issues)

### Part 4: Migration Rules
- [4.1 Dependencies to REMOVE](#41-dependencies-to-remove)
- [4.2 Dependencies to MODIFY](#42-dependencies-to-modify)
- [4.3 Agent Modification Workflow](#43-agent-modification-workflow)
- [4.4 Modification Priority Order](#44-modification-priority-order)

### Part 5: Quick Reference & Troubleshooting
- [5.1 Version Quick Reference](#51-version-quick-reference)
- [5.2 Critical Upgrades](#52-critical-upgrades)
- [5.3 Troubleshooting](#53-troubleshooting)
- [5.4 Validation Commands](#54-validation-commands)

---

# PART 1: BUILD INFRASTRUCTURE

## 1.1 gradle.properties SSL Configuration

**When**: Phase 0, Step 1 — FIRST operation before any other migration steps.

**Why**: Custom truststore/keystore settings in gradle.properties can prevent Gradle from connecting to Nexus. This MUST be fixed before any other operations.

**Patterns to detect** (in gradle.properties):
```properties
javax.net.ssl.trustStore=/path/to/custom/truststore
javax.net.ssl.keyStore=/path/to/custom/keystore
javax.net.ssl.trustStorePassword=changeit
javax.net.ssl.keyStorePassword=changeit
systemProp.javax.net.ssl.trustStore=/path/to/custom/truststore
systemProp.javax.net.ssl.keyStore=/path/to/custom/keystore
systemProp.javax.net.ssl.trustStorePassword=changeit
systemProp.javax.net.ssl.keyStorePassword=changeit
```

**Fix**: Use Read/Edit tools to comment out each matching line (add `#` prefix).

**Validation**:
```bash
if grep -qE "^[^#]*javax\.net\.ssl\.(trust|key)Store" gradle.properties 2>/dev/null; then
  echo "FAIL: Uncommented SSL entries still present"
else
  echo "PASS: SSL entries handled"
fi
```

---

## 1.2 Gradle Wrapper Configuration

**Issue:** OpenRewrite downloads Gradle binaries using the `distributionUrl` pattern. Maven-style paths fail when OpenRewrite constructs URLs for newer Gradle versions.

**Incorrect Format (Maven-style path):**
```properties
distributionUrl=https\://nexus.barcapint.com/nexus/content/groups/third-party-apps-group/gradle/gradle/6.9.2/gradle-6.9.2-bin.zip
```

**Correct Format (flat path):**
```properties
distributionUrl=https\://nexus.barcapint.com/nexus/content/groups/barclays/gradle-6.9.2-bin.zip
```

**Phase 0 Fix (UNCONDITIONAL — normalize base URL path, PRESERVE version):**
```bash
CURRENT_VERSION=$(grep "distributionUrl" gradle/wrapper/gradle-wrapper.properties | sed 's/.*gradle-\([0-9][0-9.]*\)-bin.zip.*/\1/')
sed -i.bak "s|distributionUrl=.*|distributionUrl=https\\\\://nexus.barcapint.com/nexus/content/groups/barclays/gradle-${CURRENT_VERSION}-bin.zip|" gradle/wrapper/gradle-wrapper.properties
rm -f gradle/wrapper/gradle-wrapper.properties.bak
```

**Phase 1 Fix (upgrade Gradle version to 8.5+):**
```bash
sed -i.bak "s|gradle-[0-9][0-9.]*-bin.zip|gradle-8.5-bin.zip|" gradle/wrapper/gradle-wrapper.properties
rm -f gradle/wrapper/gradle-wrapper.properties.bak
```

**Validation (Phase 1 — checks format AND version):**
```bash
DIST_URL=$(grep "distributionUrl" gradle/wrapper/gradle-wrapper.properties)
if echo "$DIST_URL" | grep -qE "nexus.*barcapint.*content/groups/barclays/gradle-8\.[5-9]|gradle-8\.1[0-9]"; then
  echo "PASS: distributionUrl normalized (Nexus flat path, Gradle 8.5+)"
else
  echo "FAIL: distributionUrl not correct. Current: $DIST_URL"
fi
```

---

## 1.3 Gradle Cache Resolution Strategy

**When**: Phase 0 — before any dependency resolution with dynamic versions.

**Why**: Dynamic version ranges (`2.3.+`, `8.2.+`, `3.5.+`) are used during migration. Gradle's default 24-hour caching can cause stale versions.

**Configuration** (add to build.gradle after plugins/buildscript block, before dependencies):
```gradle
configurations.all {
    resolutionStrategy.cacheChangingModulesFor 0, 'seconds'
    resolutionStrategy.cacheDynamicVersionsFor 0, 'seconds'
}
```

If `configurations.all` already exists, merge the two `resolutionStrategy` lines into the existing block.

---

## 1.4 Gradle Version Compatibility Matrix

| Gradle Version | Max Java Version | MCA Plugin Version | OpenRewrite Plugin | Status |
|----------------|------------------|--------------------|--------------------|--------|
| 6.9.x | Java 15 | 1.0.x - 1.x.x | 7.0.2 | Incompatible with Java 21 |
| 7.6.x | Java 19 | 1.0.x - 1.x.x | 7.0.2 | Incompatible with Java 21 |
| 8.5 - 8.13 | Java 21+ | **8.1.x - 8.2.x** | 7.0.2 | **Recommended for Java 21** |

MCA plugin version numbers align with Gradle major version (e.g., 8.x plugins for Gradle 8). Dynamic versions like `1.0.+` will NEVER resolve to 8.x.

---

## 1.5 MCA DevOps Gradle Plugins

All plugins listed here are used in `buildscript { dependencies {} }` block.

| Plugin | GroupId | Gradle 6/7 (Java 8) | Gradle 8 (Java 21+) | Migration Action |
|--------|---------|----------------------|---------------------|------------------|
| gradle-eps2-war-plugin | com.barclays.mca.devops | 1.0.+ | **gradle-eps-war-plugin:8.2.002** | **BREAKING**: Rename `eps2` → `eps`, plugin ID `eps2-war` → `eps-war` |
| gradle-code-coverage-plugin | com.barclays.mca.devops | 1.1.+ | **8.1.+** | Upgrade to 8.x |
| gradle-mca-findbugs-plugin | com.barclays.mca.devops | 1.0.+ | Keep 1.0.+ | Compatible with Gradle 8 |
| gradle-integration-test-plugin | com.barclays.mca.devops | 2.0.+ | Keep 2.0.+ | Compatible with Gradle 8 |
| gradle-sonar-plugin | com.barclays.mca.devops | 2.0.+ | Keep 2.0.+ | Compatible with Gradle 8 |
| gradle-script-files-plugin | com.barclays.mca.devops | 1.0.+ | **Remove** | Not needed in Gradle 8 |
| gradle-eps-nexus-plugin | com.barclays.mca.devops | 1.0.+ | **Remove** | Not needed in Gradle 8 |
| gradle-jacoco-report-plugin | com.barclays.mca.devops | 2.0.+ | **Remove** | Not needed in Gradle 8 |
| gradle-mca-eclipse-plugin | com.barclays.mca.devops | 1.0.+ | **Remove** | Not needed in Gradle 8 |
| gradle-tagversion-plugin | com.barclays.mca.devops | 1.0.2 | **Remove** | Not needed in Gradle 8 |
| gradle-oidlt-plugin | com.barclays.mca.devops | 2.0.+ | **Remove** | Not needed in Gradle 8 |
| gradle-eps-code-coverage-plugin | com.barclays.mca.devops | 1.0.+ | **Remove** | Not needed in Gradle 8 |
| gradle-dependency-check-plugin | com.barclays.mca.devops | 1.0.+ | **Remove** | Not needed in Gradle 8 |
| gradle-mca-versioning-plugin | com.barclays.mca.devops | 1.0.+ | **Remove** | Not needed in Gradle 8 |

### EPS WAR Plugin Migration (CRITICAL)

Both the classpath artifact AND the apply plugin statement must change:

```gradle
// BEFORE (Java 8 / SB 2.7)
buildscript {
    dependencies {
        classpath("com.barclays.mca.devops:gradle-eps2-war-plugin:1.0.+")
    }
}
apply plugin: 'eps2-war'

// AFTER (Java 21 / SB 3.5+)
buildscript {
    dependencies {
        classpath("com.barclays.mca.devops:gradle-eps-war-plugin:8.2.+")
    }
}
apply plugin: 'eps-war'
```

### Plugin Incompatibility Warnings

| Plugin | Version Range | Issue | Failure Phase |
|--------|---------------|-------|---------------|
| gradle-code-coverage-plugin | 1.x | Missing @Input/@Output annotations. Gradle 8+ validation fails. | Phase 6 (test run) |
| gradle-sonarqube-plugin | 3.x | Deprecated configuration API usage | Phase 6 (build) |

---

## 1.6 OpenRewrite Recipe Versions

| Recipe | GroupId | Gradle 6/7 | Gradle 8 | Notes |
|--------|---------|------------|----------|-------|
| OpenRewrite Plugin | org.openrewrite | 7.0.2 | 7.0.2 | Works with Gradle 6-8 |
| mca-rewrite-spring | com.barclays.mca.recipe | 1.1.+ | **1.2.002** | MCA migration recipes |

**Nexus Lookup (MANDATORY):**
```bash
curl -sk "https://nexus.barcapint.com/nexus/content/groups/barclays/com/barclays/mca/recipe/mca-rewrite-spring/maven-metadata.xml"
```

**OpenRewrite Configuration for Phase 1:**
```groovy
buildscript {
    dependencies {
        classpath("org.openrewrite:plugin:7.0.2")
    }
}

apply plugin: 'org.openrewrite.rewrite'

dependencies {
    rewrite("com.barclays.mca.recipe:mca-rewrite-spring:1.2.002")
}

rewrite {
    activeRecipe("com.barclays.mca.rewrite.project.UpgradeMCA2_2_3")
}
```

---

## 1.7 Gradle API Breaking Changes (6→8)

### bootRun Configuration

```groovy
// BEFORE (Gradle 6/7 / Spring Boot 2.x)
bootRun { main = 'com.barclays.mca.SERVICE.ServiceApplication' }

// AFTER (Gradle 8 / Spring Boot 3.x)
bootRun { mainClass = 'com.barclays.mca.SERVICE.ServiceApplication' }
```

### JaCoCo: Report Directory

```groovy
// BEFORE (Gradle 6/7)
jacoco { reportsDir = file("$buildDir/reports/jacoco") }

// AFTER (Gradle 8)
jacoco { reportsDirectory = layout.buildDirectory.dir("$buildDir/reports/jacoco") }
```

### JaCoCo: Exclusion Pattern Syntax

```groovy
// BEFORE (Gradle 6/7) — array syntax
exclude: ['**/model/**', '**/dto/**']

// AFTER (Gradle 8) — string syntax (single pattern)
exclude: '**/model/**'
```

### Test Configuration: JUnit 5 Platform

```groovy
// AFTER (Gradle 8 / JUnit 5) — REQUIRED when junit-jupiter is present
test {
    finalizedBy jacocoTestReport
    useJUnitPlatform()
}
```

### Repository Configuration

Remove `metadataSources` blocks (Gradle 8 has better defaults). Keep `mavenContent` only for snapshot-only repos.

### Coverage Threshold Adjustments

Coverage thresholds may be lowered post-migration. Don't fail migration if coverage drops — log warning, document in PR, let team decide.

---

# PART 2: DEPENDENCY CONSOLIDATION

## 2.1 External Dependency File Consolidation

**When**: Phase 0, step 11 — BEFORE Phase 1 selective migration begins.

**When to Apply**: If `build.gradle` contains any of:
- `apply from: "dependencies.gradle"`
- `apply from: 'gradle/dependencies.gradle'`
- `apply from: "${rootDir}/gradle/dependencies.gradle"`

### Critical Distinction

**buildscript.dependencies** = BUILD PLUGINS only (classpath entries). **Top-level dependencies** = PROJECT DEPENDENCIES (implementation, testImplementation). All dependencies from external files go into the **top-level dependencies block**. The buildscript block MUST NOT be touched during consolidation.

### Example

**Before:**
```gradle
// build.gradle
apply from: "dependencies.gradle"
```
```gradle
// dependencies.gradle
dependencies {
    implementation 'com.barclays.ccd.ukcad:mca-experience-common-starter:3.0.0-RELEASE'
    implementation 'org.springframework.boot:spring-boot-starter-web'
    testImplementation 'org.junit.jupiter:junit-jupiter:5.11.3'
}
```

**After:**
```gradle
// build.gradle — "apply from" line DELETED (not commented)
dependencies {
    implementation 'com.barclays.ccd.ukcad:mca-experience-common-starter:3.0.0-RELEASE'
    implementation 'org.springframework.boot:spring-boot-starter-web'
    testImplementation 'org.junit.jupiter:junit-jupiter:5.11.3'
}
```
`dependencies.gradle`: **DELETED**

### Verification

Dependency tree must remain identical before and after:
```bash
diff deps_before.txt deps_after.txt
```

---

## 2.2 MCA Platform BOM Setup

**When**: Phase 1, steps 5-6. Applies to ALL projects regardless of group.

The MCA platform BOM (`com.barclays.global.mca:mca-dependencies`) manages transitive dependency versions for MCA libraries, eliminating version conflicts.

### Managed Dependency Groups

The BOM manages versions for SOME artifacts in these groupIds:
- `com.barclays.mca:*`
- `com.barclays.ukc:*`
- `com.barclays.global.mca:*`
- `com.barclays.ccd.ukcad:*`

**CRITICAL: Not ALL artifacts in these groupIds are BOM-managed.** You MUST verify each dependency against the actual BOM POM before stripping its version.

### BOM Verification Procedure

1. Download the BOM POM: `curl -sk "https://nexus-read.barcapint.com/nexus/content/groups/barclays/com/barclays/global/mca/mca-dependencies/{VERSION}/mca-dependencies-{VERSION}.pom"`
2. Parse the `<dependencyManagement><dependencies>` section
3. Only strip versions from dependencies that appear in that section
4. Keep explicit versions for dependencies NOT listed in the BOM

### Example

```gradle
// BEFORE
dependencies {
    implementation 'com.barclays.ccd.ukcad:mca-experience-common-starter:3.0.0-RELEASE'
    implementation 'com.barclays.global.mca:mca-eps-core:2.2.020'
    implementation 'org.apache.commons:commons-lang3:3.12.0'
}

// AFTER (BOM-managed versions stripped)
dependencies {
    implementation platform("com.barclays.global.mca:mca-dependencies:2.3.001")
    implementation 'com.barclays.ccd.ukcad:mca-experience-common-starter'
    implementation 'com.barclays.global.mca:mca-eps-core'
    implementation 'org.apache.commons:commons-lang3:3.12.0'  // Not managed — keep version
}
```

### Troubleshooting

**Managed dependency version not resolved:** Check if artifact is actually in the BOM POM. If not, add explicit version back.

**Version conflict after adding BOM:** Remove explicit versions from managed deps. If specific version needed, use constraint:
```gradle
constraints {
    implementation('com.barclays.mca:artifact:1.2.3') {
        because 'specific version needed for compatibility'
    }
}
```

---

# PART 3: BARCLAYS INTERNAL LIBRARIES

## 3.1 Security Libraries

| Library | GroupId | Pre-Java 21 (SB 2.7) | Java 21+ (SB 3.3) | Notes |
|---------|---------|----------------------|-------------------|-------|
| securityFilter | com.barclays.security | 6.x | **7.0.0-RELEASE** | **CRITICAL** — jakarta.servlet |

```gradle
// Java 8 / Spring Boot 2.7 (javax.servlet)
implementation 'com.barclays.security:securityFilter:6.x'

// Java 21 / Spring Boot 3.5+ (jakarta.servlet) — REQUIRED
implementation 'com.barclays.security:securityFilter:7.0.0-RELEASE'
```

**Error Without Upgrade:**
```
java.lang.NoClassDefFoundError: javax/servlet/Filter
ClassCastException: cannot be cast to jakarta.servlet.Filter
```

---

## 3.2 MCA Platform Libraries

| Library | GroupId | Pre-Java 21 (SB 2.7) | Java 21+ (SB 3.3) | Notes |
|---------|---------|----------------------|-------------------|-------|
| mca-experience-common-starter | com.barclays.mca | 2.x.x | **3.0.0-RELEASE** | Core MCA experience framework |
| mca-generic-experience-api-starter | com.barclays.mca | 1.x.x | **2.0.0-RELEASE** | Generic API experience starter |
| mca-global-libs | com.barclays.mca | 2.1.x | **2.2.020** | Global shared libraries |
| referencedata-service-starter | com.barclays.mca | 2.x.x | **3.0.0-RELEASE** | Reference data service starter |

> **Nexus Lookup:** Verify latest versions via [nexus_version_lookup.md](nexus_version_lookup.md). GroupId: `com.barclays.mca`. mca-global-libs is in `barclays-restricted-releases` repository.

With platform BOM, these dependencies omit versions:
```gradle
implementation platform("com.barclays.global.mca:mca-dependencies:2.3.001")
implementation 'com.barclays.mca:mca-experience-common-starter'
implementation 'com.barclays.mca:mca-generic-experience-api-starter'
implementation 'com.barclays.mca:mca-global-libs'
implementation 'com.barclays.mca:referencedata-service-starter'
```

---

## 3.3 UKC Libraries

| Library | GroupId | Pre-Java 21 (SB 2.7) | Java 21+ (SB 3.3) | Notes |
|---------|---------|----------------------|-------------------|-------|
| ukc-bronze-service-api | com.barclays.ukc | 1.2.x | **1.3.1-SNAPSHOT** | UKC Bronze service API |

> **Nexus Lookup:** GroupId: `com.barclays.ukc`. UKC libraries may have different versioning schemes — always verify via Nexus.

---

## 3.4 EPS Libraries

The `eps2-war` plugin is renamed to `eps-war` in Java 21 / Spring Boot 3.5+. Both the classpath artifact AND plugin apply statement must change. See [Section 1.5 EPS WAR Plugin Migration](#eps-war-plugin-migration-critical) for the full migration pattern.

---

## 3.5 MCA Transitive Dependency Issues

Some MCA libraries declare transitive dependencies with empty version placeholders ("." or ""), causing Gradle build failures.

**Symptom:**
```
Could not resolve org.aspectj:aspectjweaver:.
Could not resolve jakarta.validation:jakarta.validation-api:.
```

| MCA Library | Transitive Dependency | Empty Version | Required Explicit Version |
|-------------|----------------------|---------------|---------------------------|
| mca-logging-performance | org.aspectj:aspectjweaver | `.` | **1.9.22** |
| mca-eps-core | jakarta.validation:jakarta.validation-api | `.` | **3.0.2** |

**Solution (Phase 1 — proactive fix, BEFORE first build attempt):**
```gradle
dependencies {
    implementation 'jakarta.validation:jakarta.validation-api:3.0.2'
    implementation 'org.aspectj:aspectjweaver:1.9.22'
}
```

---

# PART 4: MIGRATION RULES

> **CRITICAL:** These dependencies must be REMOVED or MODIFIED (not just added). Do NOT add duplicate entries — replace existing entries. Check if dependency already exists before adding.

## 4.1 Dependencies to REMOVE

| Old Dependency (REMOVE) | Reason | Replacement |
|--------------------------|--------|-------------|
| Any `com.barclays.*` library compiled for Java 8 only | Incompatible bytecode | Search Nexus for Java 21 version |
| `eps2-war` plugin | Renamed | `eps-war` plugin (see Section 1.5) |

---

## 4.2 Dependencies to MODIFY

| Old Dependency | New Dependency | Action |
|---------------|---------------|--------|
| `com.barclays.security:securityFilter:6.x` | `securityFilter:7.0.0-RELEASE` | **CRITICAL** UPGRADE |
| `com.barclays.mca:mca-experience-common-starter:2.x` | `3.0.0-RELEASE` | UPGRADE |
| `com.barclays.mca:mca-generic-experience-api-starter:1.x` | `2.0.0-RELEASE` | UPGRADE |
| `com.barclays.mca:referencedata-service-starter:2.x` | `3.0.0-RELEASE` | UPGRADE |
| `com.barclays.mca:mca-global-libs:2.1.x` | `2.2.020` | UPGRADE |

---

## 4.3 Agent Modification Workflow

```
1. READ build.gradle to inventory all com.barclays.*/com.barclaycard.* dependencies
2. FOR EACH dependency:
   a. CHECK against removal list (Section 4.1) → REMOVE if found
   b. CHECK against modification list (Section 4.2) → MODIFY if found
   c. If not in either list:
      i.  Search Nexus for a Java 21-compatible version
      ii. If found → UPGRADE to latest Nexus version
      iii.If not found → KEEP current version, log warning
3. NEVER duplicate dependencies — always replace existing entries
4. Verify new versions in Nexus before applying
```

---

## 4.4 Modification Priority Order

1. **REMOVE** deprecated/incompatible dependencies (Section 4.1)
2. **MODIFY** security libraries to Java 21 versions (securityFilter)
3. **MODIFY** MCA platform libraries (experience starters, global libs, reference data)
4. **MODIFY** libraries with groupId/artifactId changes (EPS plugin rename)
5. **SEARCH NEXUS** for any remaining Barclays libraries not in the tables

---

# PART 5: QUICK REFERENCE & TROUBLESHOOTING

## 5.1 Version Quick Reference

| Artifact | Java 8 / SB 2.7 | Java 21 / SB 3.3 | Priority |
|----------|-----------------|-------------------|----------|
| securityFilter | 6.x | 7.0.0-RELEASE | **CRITICAL** |
| mca-experience-common-starter | 2.x.x | 3.0.0-RELEASE | HIGH |
| mca-generic-experience-api-starter | 1.x.x | 2.0.0-RELEASE | HIGH |
| mca-global-libs | 2.1.x | 2.2.020 | HIGH |
| referencedata-service-starter | 2.x.x | 3.0.0-RELEASE | HIGH |
| ukc-bronze-service-api | 1.2.x | 1.3.1-SNAPSHOT | MEDIUM |
| gradle-eps-war-plugin (was eps2) | 1.0.+ | 8.2.002 | HIGH |
| gradle-code-coverage-plugin | 1.1.+ | 8.1.+ | MEDIUM |
| mca-rewrite-spring | 1.1.+ | 1.2.002 | HIGH |

---

## 5.2 Critical Upgrades

### securityFilter:7.0.0-RELEASE (MANDATORY)

6.x uses `javax.servlet.Filter`. 7.0.0-RELEASE uses `jakarta.servlet.Filter`. Causes `ClassCastException` if not upgraded.

---

## 5.3 Troubleshooting

### ClassCastException for jakarta.servlet.Filter
Upgrade securityFilter to 7.0.0-RELEASE.

### UnsupportedClassVersionError from Barclays library
Library was compiled for Java 8. Search Nexus for a Java 21-compatible version:
```bash
curl -sk "https://nexus.barcapint.com/nexus/content/groups/barclays/{groupId-as-path}/{artifactId}/maven-metadata.xml"
```

### Dependency not found — Unknown Barclays library
Search Nexus broadly:
```bash
curl -sk "https://nexus-read.barcapint.com/nexus/service/local/lucene/search?q={artifact-name}"
```

### MavenPlugin not found in Gradle 8
MCA plugins version 1.x use `org.gradle.api.plugins.MavenPlugin` (removed in Gradle 8). Upgrade ALL MCA plugins to 8.x versions (see Section 1.5).

### Unsupported class file major version 65
Gradle 6.x/7.x cannot run on Java 21. Upgrade Gradle wrapper to 8.5+.

### OpenRewrite fails after Gradle 8 upgrade
mca-rewrite-spring version may be too old. Update to 1.2.002 or newer (see Section 1.6).

### Build fails after dependency consolidation
Check for syntax errors in dependencies block, verify all dependencies were copied, remove duplicates.

---

## 5.4 Validation Commands

Use the Grep tool (or `search_in_files_by_text` MCP tool) for these validations:

**Build Infrastructure:**
- **Check for old security filter:** Grep for `securityFilter:6` in `build.gradle` — Expected: No matches
- **Check for eps2-war:** Grep for `eps2-war` in `build.gradle` — Expected: No matches (should be `eps-war`)

**Dependency Consolidation:**
- **Check for apply from dependencies:** Grep for `apply from.*dependencies\.gradle` in `build.gradle` — Expected: No matches
- **Check gradle/ and buildSrc/ remain untouched:** Verify these directories were not modified

**BOM Management:**
- **Check for mca-dependencies platform:** Grep for `platform.*mca-dependencies` in `build.gradle` — Expected: Found
- **Check for versioned managed deps:** Grep for `com\.barclays\.mca:.*:[0-9]` in `build.gradle` — Expected: No matches in implementation contexts
- **Check for versioned UKC deps:** Grep for `com\.barclays\.ukc:.*:[0-9]` in `build.gradle` — Expected: No matches in implementation contexts

**Duplicate Detection:**
- Extract all dependency artifact IDs from `build.gradle`
- Group by artifact ID, flag if same artifact appears multiple times
- Each artifact should appear exactly once

**Agent Validation Workflow:**
1. After adding mca-dependencies platform BOM, verify `apply from` statement removed
2. Verify all BOM-managed dependencies omit version numbers
3. Run duplicate dependency detection
4. Run `$GRADLE_CMD dependencies` to confirm BOM is resolving versions
5. Check build output for "Platform dependency" or "BOM" references

---

**Document Version:** 3.0
**Last Updated:** 2026-02-23
**Consolidated from:** barclays_internal_libraries.md, barclays_internal_libraries_capl.md, dependency_consolidation.md, gradle_build_infrastructure.md
