---
name: sdk3-sdk4-gradle
description: Gradle build configuration migration from SDK3 (Spring Boot 3.5.x) to SDK4 (Spring Boot 4.1.x) for Barclays iAPI projects. Covers OpenRewrite recipe execution, Gradle wrapper update to 8.14, upgrading SDK3_VERSION to 4.x with enforcedPlatform, Jackson group ID migration to tools.jackson, and dependency version cleanup. The sdk3 BOM artifact name and SDK3_VERSION property name are retained. Use when uplifting an existing SDK3 API to Spring Boot 4.1.x.
owner: Barclays AI (barclaysai@barclays.com)
version: 1.0.0
license: Proprietary. For Barclays internal use only.
user-invocable: false
source: barclays-claude-code-plugins/plugins/migration/barclays-buk-smesh-api-maintainer/skills/sdk3-sdk4-gradle/SKILL.md
review-trigger: When SDK4 BOM version changes, Gradle minimum version requirement changes, or new dependency version constraints are identified
status: Full
---

# Gradle Build Configuration — SDK3 to SDK4 Uplift

## Overview

This skill covers all `build.gradle`, `gradle.properties`, and Gradle wrapper changes required to uplift a Barclays iAPI project from SDK3 (Spring Boot 3.5.x) to SDK4 (Spring Boot 4.1.x).

**Prerequisites:**
- API must already be on SDK3 — `gradle.properties` must contain `SDK3_VERSION`
- No `sourceCompatibility = JavaVersion.VERSION_1_8` may be present (that is an SDK2 indicator)
- Java 21 toolchain remains the baseline (no JDK change required for the 3→4 uplift)

---

## Step 1: Run OpenRewrite Automatically

The first and most important step is running the OpenRewrite Spring Boot 4 recipe. This handles the majority of boilerplate changes automatically.

### 1.1 Obtain the init.gradle script

The `init.gradle` script is stored in the Barclays internal SDK repository. It configures the OpenRewrite plugin and activates the `UpgradeSpringBoot_4_0` recipe. The content is:

```groovy
initscript {
    repositories {
        maven {
            url 'https://nexus.barcapint.com/nexus/content/groups/barclays'
        }
    }
    dependencies {
        classpath 'org.openrewrite:plugin:7.35.0'
    }
}

allprojects {
    repositories {
        maven {
            url 'https://nexus.barcapint.com/nexus/content/groups/barclays'
        }
    }
}

rootProject {
    plugins.apply(org.openrewrite.gradle.RewritePlugin)

    dependencies {
        // Remove the 0.29.0 classified artefact requested transitively.
        rewrite('org.openrewrite.recipe:rewrite-spring:6.34.0') {
            exclude group: 'tech.picnic.error-prone-support',
                    module: 'error-prone-contrib'
        }

        // Add the exact classified recipe JAR available in Nexus.
        rewrite 'tech.picnic.error-prone-support:error-prone-contrib:0.28.0:recipes'
    }

    rewrite {
        activeRecipe 'org.openrewrite.java.spring.boot4.UpgradeSpringBoot_4_0'
        exclusion 'gradle/wrapper/gradle-wrapper.properties'
        exclusion '**/gradle/wrapper/gradle-wrapper.properties'
        setExportDatatables(true)
    }
}
```

Save this file as `init.gradle` at the project root (do not commit it — it is a temporary migration aid).

### 1.2 Run the recipe

```bash
# Windows
gradlew.bat --init-script init.gradle rewriteRun

# Linux / macOS
./gradlew --init-script init.gradle rewriteRun
```

This will apply automated source and configuration changes. After it completes, **do not run tests yet** — proceed through the manual version changes below first, then attempt compilation.

> **Important:** OpenRewrite handles most boilerplate, but several changes listed in this skill are **not** covered by the recipe and must be applied manually. See [sdk3-sdk4-migration SKILL.md](../sdk3-sdk4-migration/SKILL.md) for the full list.

---

## Step 2: Update Gradle Wrapper

Spring Boot 4 requires **Gradle 8.14 minimum** (up from 8.13).

**File:** `gradle/wrapper/gradle-wrapper.properties`

```properties
# Before
distributionUrl=https\://nexus.barcapint.com/nexus/content/groups/barclays/org/gradle/gradle/8.13/gradle-8.13-bin.zip

# After
distributionUrl=https\://nexus.barcapint.com/nexus/content/groups/barclays/org/gradle/gradle/8.14/gradle-8.14-bin.zip
```

---

## Step 3: Uplift SDK3 BOM Version to 4.0

### 3.1 gradle.properties

Update `SDK3_VERSION` to the target 4.x release version. The property name stays as `SDK3_VERSION` — do not rename it:

```properties
# Before
SDK3_VERSION=1.12.007
GLOBAL_VERSION=1.1.2

# After
SDK3_VERSION=4.0.0
GLOBAL_VERSION=1.1.2
```

> Note: Confirm the exact 4.x release version from Nexus at `https://nexus.barcapint.com/nexus/content/groups/barclays` under group `com.barclays.api` artifact `sdk3` before applying. Never use a SNAPSHOT version in a committed build file.

### 3.2 build.gradle — Switch to enforcedPlatform

The BOM artifact remains `sdk3`. Switch from `platform` to `enforcedPlatform` so the SDK4 BOM versions take strict precedence over any transitive constraints:

```groovy
// Before
dependencies {
    implementation(platform("com.barclays.api:sdk3:${SDK3_VERSION}"))
    ...
}

// After
dependencies {
    implementation(enforcedPlatform("com.barclays.api:sdk3:${SDK3_VERSION}"))
    ...
}
```

> `enforcedPlatform` is required for the SDK4 uplift because Spring Boot 4 and Jackson 3 introduce transitive dependency conflicts that `platform` cannot resolve without explicit enforcement. The same change applies to any `classpath platform(...)` declaration in the `buildscript` block.

---

## Step 4: Update Dependency Versions

The following versions changed as part of the SDK4 uplift. Remove explicit versions for entries now managed by the SDK4 BOM; keep explicit overrides only where you need to pin above what the BOM provides.

### 4.1 Version change reference table

Spring Boot, Spring Framework, and Tomcat versions are all managed by the `sdk3` BOM at the 4.x level — do **not** add explicit `ext` overrides for these. Only override versions for dependencies that the SDK BOM does not manage, or where a specific CVE fix requires pinning above what the BOM provides.

| Dependency | Old Version | New Version | Notes |
|---|---|---|---|
| Spring Boot | 3.5.16 | 4.1.1 | Managed by `sdk3` BOM — no `ext` override needed |
| Spring Framework | 6.2.19 | 7.0.9 | Managed by `sdk3` BOM — no `ext` override needed |
| Tomcat | 10.1.55 | 11.0.22 | Managed by `sdk3` BOM — no `ext` override needed |
| Spring Cloud Dependencies | 2025.0.2 | 2025.1.2 | Update manually if used |
| Jackson | 2.21.4 | 3.2.1 | **Group ID also changed** — see section 4.2 |
| commons-io | 2.16.1 | 2.22.0 | Update explicitly if pinned |
| OkHttp3 | 4.12.0 | 5.4.0 | Update explicitly if used |

### 4.2 Jackson group ID change — CRITICAL

Jackson has a new major version (3.x) **and** a new group ID. This is **not** handled automatically by OpenRewrite.

```groovy
// Before — com.fasterxml.jackson
implementation('com.fasterxml.jackson:jackson-bom') {
    version { strictly '2.21.4' }
}
implementation 'com.fasterxml.jackson.core:jackson-databind'
implementation 'com.fasterxml.jackson.core:jackson-annotations'
implementation 'com.fasterxml.jackson.datatype:jackson-datatype-jsr310'

// After — tools.jackson (new group ID, version managed by enforcedPlatform BOM)
implementation('tools.jackson:jackson-bom')
implementation 'tools.jackson.core:jackson-databind'
implementation 'tools.jackson.core:jackson-annotations'
implementation 'tools.jackson.datatype:jackson-datatype-jsr310'
```

Remove any `strictly` version constraints on the old `com.fasterxml.jackson:jackson-bom` — these are replaced by the `tools.jackson:jackson-bom` entry without a version (the `enforcedPlatform` BOM resolves it).

Search the entire project for `com.fasterxml.jackson` references and replace with `tools.jackson`:

```bash
grep -rn "com.fasterxml.jackson" . --include="*.gradle" --include="*.gradle.kts" --include="*.properties"
```

### 4.3 Spring Cloud (if used)

If the project uses Spring Cloud, update the BOM import:

```groovy
// Before
implementation(platform("org.springframework.cloud:spring-cloud-dependencies:2025.0.2"))

// After
implementation(platform("org.springframework.cloud:spring-cloud-dependencies:2025.1.2"))
```

---

## Step 5: Add spring-cloud-starter-bootstrap Dependency

Bootstrap context loading is **no longer enabled by default** in Spring Boot 4. If the project uses `bootstrap.yml` or `bootstrap.properties`, add the following dependency as a temporary bridge (a permanent solution is to migrate all bootstrap properties to `application.yaml`):

```groovy
// Add to dependencies block
implementation 'org.springframework.cloud:spring-cloud-starter-bootstrap'
```

> **Note:** This is marked deprecated. Raise a follow-up ticket to migrate bootstrap properties to `application.yaml` after the uplift stabilises.

---

## Step 6: Remove Versions Now Managed by SDK4 BOM

After uplifting to SDK4, audit `build.gradle` for any explicit version numbers that the SDK4 BOM now manages. Remove the version string for those entries to avoid version conflicts:

```groovy
// Before — explicit version that was needed for SDK3
implementation 'com.barclays.api:bap-bld-lib-restapi:1.12.007'
implementation 'commons-io:commons-io:2.16.1'

// After — let SDK4 BOM manage the version
implementation 'com.barclays.api:bap-bld-lib-restapi'
implementation 'commons-io:commons-io'
```

Run `./gradlew dependencies` after changes and look for version conflicts flagged by Gradle.

---

## Step 7: Validate Build Compiles

Run compile-only (do not run tests yet — see [sdk3-sdk4-migration SKILL.md](../sdk3-sdk4-migration/SKILL.md) for manual source fixes needed before tests pass):

```bash
# Windows
gradlew.bat compileJava -x barclaysApiGenerate

# Linux / macOS
./gradlew compileJava -x barclaysApiGenerate
```

Fix all compilation errors before proceeding to test execution.

---

## Quick Reference Checklist

| Step | Action | File |
|---|---|---|
| 1 | Run OpenRewrite `UpgradeSpringBoot_4_0` recipe | project root |
| 2 | Update Gradle wrapper: `8.13` → `8.14` | `gradle/wrapper/gradle-wrapper.properties` |
| 3 | Update `SDK3_VERSION` to target 4.x release (keep property name as-is) | `gradle.properties` |
| 4 | Change `platform(...)` → `enforcedPlatform(...)` for `sdk3` BOM (artifact stays `sdk3`) | `build.gradle` |
| 5 | Replace Jackson group: `com.fasterxml.jackson` → `tools.jackson`; switch BOM entry to `tools.jackson:jackson-bom` | `build.gradle` |
| 6 | Update Spring Cloud BOM: `2025.0.2` → `2025.1.2` (if used) | `build.gradle` |
| 7 | Add `spring-cloud-starter-bootstrap` (if using bootstrap properties) | `build.gradle` |
| 8 | Remove explicit versions now covered by `sdk3` BOM at 4.x | `build.gradle` |
| 9 | Run `compileJava` and fix errors | — |

## Related Skills

- [sdk3-sdk4-migration](../sdk3-sdk4-migration/SKILL.md) — Source code and API migration patterns (manual changes not covered by OpenRewrite)
- [sdk2-sdk3-gradle](../sdk2-sdk3-gradle/SKILL.md) — SDK2→SDK3 Gradle reference (prerequisite baseline)
