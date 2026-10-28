# Root build.gradle Modifications & Additional Configuration

> **Parent document:** This is a reference companion to the main `sdk2_sdk3_gradle` SKILL.md (Parts 0-3). Load this file when working on Parts 4-5 of the Gradle migration.

---

## Part 4: Root build.gradle Modifications

### Step 4.1: Update Plugins Block

> **Note:** `apply from: gradle/common/...` lines were already removed in Part 0 Step 0.2.

**Comment out ALL existing plugin declarations**, then leave only these three active:

```gradle

apply plugin: 'java'
apply plugin: 'com.barclays.api.bap-bld-lib-kotlin-int-test-gradle-plugin'
apply plugin: 'com.barclays.api.bap-bld-lib-plugin'
```

All other `apply plugin:` lines (e.g. `org.springframework.boot`, `checkstyle`, `eclipse`, any SDK2 plugins) must be **commented out**, not deleted.

**What `bap-bld-lib-plugin` provides automatically (do NOT declare these separately):**

| Plugin Applied | Condition | What It Provides |
|---------------|-----------|------------------|
| `maven-publish` | Always | Artifact publishing to Nexus |
| `org.springframework.boot` | When `test.mode` ≠ true | Spring Boot plugin (bootJar, dependency management) |
| `io.spring.dependency-management` | When `test.mode` ≠ true | Spring dependency BOM resolution |
| `jacoco` | When `test.mode` ≠ true | Code coverage with 80% line minimum at CLASS level |
| `jacoco-report-aggregation` | When `test.mode` ≠ true | Multi-project report aggregation |
| `org.sonarqube` | When `test.mode` ≠ true | SonarQube integration with JaCoCo |
| `info.solidsoft.pitest` | When `test.mode` ≠ true | Mutation testing (target `com.barclays.*`, JUnit5 plugin) |
| `info.solidsoft.pitest.aggregator` | When `test.mode` ≠ true | Multi-project PIT aggregation |
| `org.cyclonedx.bom` | When `test.mode` ≠ true | SBOM generation (`gl-sbom-bom`) |

**Key behaviors:**
- Reads `ext.jacocoCoverageExclusions` synchronously during `apply()` — see Step 3.2 ordering constraint
- JaCoCo enforced at 80% line coverage minimum per CLASS (configurable exclusions via `jacocoCoverageExclusions`)
- PIT runs with 4 threads, 1GB JVM heap, JUnit5 plugin 1.2.1
- **Cannot coexist** with `org.springframework.boot` in the plugins block — remove any explicit Spring Boot plugin declaration

### Step 4.3: Ensure Group and Version Properties

**Add these lines if they are missing:**

```gradle
group = "${GROUP_ID}"
version = "${GLOBAL_VERSION}"
```

These properties reference the variables defined in `gradle.properties` (see Part 3).

### Step 4.4: Add Conditional Checkstyle Configuration

The Checkstyle tool version is read from `gradle.properties` via the `checkstyle_tool_version` property so it can be updated without touching `build.gradle`. Ensure the property is set in `gradle.properties` before applying this block (see Step 3.1):

```properties
# gradle.properties
checkstyle_tool_version=12.2.0
```

```gradle
def checkstyleConfigFile = file('config/checkstyle/checkstyle.xml')
if (checkstyleConfigFile.exists()) {
    checkstyle {
        toolVersion = "${checkstyle_tool_version}"
        configFile = checkstyleConfigFile
        ignoreFailures = false
        showViolations = true
        maxWarnings = Integer.MAX_VALUE  // warnings are informational only — never fail the build
    }
    tasks.register('allCheckstyle') {
        dependsOn 'checkstyleMain'
    }
} else {
    logger.warn('Checkstyle config file not found at config/checkstyle/checkstyle.xml - skipping checkstyle checks')
    tasks.withType(Checkstyle).configureEach {
        enabled = false
    }
    tasks.register('allCheckstyle') {
        doLast {
            logger.warn('Checkstyle checks are disabled because config file is missing')
        }
    }
}
```

**Key points:**
- Checkstyle version is externalised to `gradle.properties` via `checkstyle_tool_version` — update the property to upgrade Checkstyle without modifying `build.gradle`
- Checkstyle is disabled by default if config file doesn't exist
- Only enables checkstyle when `config/checkstyle/checkstyle.xml` is present
- Logs clear warning messages when checkstyle is skipped
- Provides an `allCheckstyle` task that either runs checks or reports disabled state

### Step 4.5: Remove IDE Configuration Blocks (IMPORTANT)

SDK3 projects should NOT include IDE-specific Gradle configurations. Modern IDEs (IntelliJ IDEA, Eclipse with Buildship, VS Code) automatically detect Gradle projects without explicit plugins.

**Delete these entire configuration blocks from build.gradle:**

```gradle
// ❌ DELETE - Eclipse configuration block
//////////////////////
// Eclipse //
//////////////////////
eclipse {
    classpath {
        downloadJavadoc = true
        downloadSources = true
    }
}

// ❌ DELETE - IntelliJ IDEA configuration block
idea {
    module {
        downloadJavadoc = true
        downloadSources = true
    }
}

// ❌ DELETE - Generated sources configuration (SDK3 handles this automatically)
sourceSets {
    generated {
        java.srcDir "${buildDir}/generated/sources"
    }
}

// ❌ DELETE - Generated sources directory variable
def generatedSourcesDir = file("${buildDir}/generated/sources")
```

**Why Remove IDE Configs:**
- SDK3's `bap-bld-lib-plugin` automatically applies 9 plugins (see Step 4.1 table)
- Eclipse/IDEA plugins can interfere with SDK3's Gradle configuration
- Gradle 8.13+ works seamlessly with modern IDEs without explicit plugins
- Reduces build.gradle complexity and maintenance burden
- Generated sources are handled automatically by SDK3 plugin

**Detection - Search for these patterns in build.gradle:**

Use Grep tool to search `build.gradle` for patterns: `eclipse\s*\{`, `idea\s*\{`, `sourceSets\s*\{`, and `generatedSourcesDir`.

**Migration Actions:**
- Remove `apply plugin: 'eclipse'` and `apply plugin: 'idea'` if present (covered in Step 4.2)
- Remove entire `eclipse {}` configuration block
- Remove entire `idea {}` configuration block
- Remove `sourceSets {}` blocks for generated sources
- Remove `generatedSourcesDir` variable definitions
- Remove any Eclipse/IntelliJ comment headers (e.g., `// Eclipse //`)

### Step 4.6: Update Java Configuration

**Delete:**

```gradle
sourceCompatibility = JavaVersion.VERSION_1_8
targetCompatibility = JavaVersion.VERSION_1_8
```

**Add (substitute `{JDK_VERSION}` with the target JDK version — `21` or `25` — from the migration context):**

```gradle
java {
    toolchain {
        languageVersion = JavaLanguageVersion.of({JDK_VERSION})
    }
}

sourceCompatibility = JavaVersion.VERSION_{JDK_VERSION}
targetCompatibility = JavaVersion.VERSION_{JDK_VERSION}
```

> **JDK 21 (default migration):**
> ```gradle
> java {
>     toolchain {
>         languageVersion = JavaLanguageVersion.of(21)
>     }
> }
> sourceCompatibility = JavaVersion.VERSION_21
> targetCompatibility = JavaVersion.VERSION_21
> ```
>
> **JDK 25 migration (`--jdk-version 25`):**
> ```gradle
> java {
>     toolchain {
>         languageVersion = JavaLanguageVersion.of(25)
>     }
> }
> sourceCompatibility = JavaVersion.VERSION_25
> targetCompatibility = JavaVersion.VERSION_25
> ```

This is the **only** build.gradle change that differs between JDK 21 and JDK 25 migration. All other Gradle configuration (wrapper, buildSrc, SDK3 BOM, repositories, plugins, JaCoCo, PITest) is identical for both versions.

### Step 4.7: Update Repositories Block

**Delete entire buildscript block** (if present):

```gradle
buildscript {
    // Delete everything here
}
```

**Delete entire dependencyManagement block** (if present):

```gradle
dependencyManagement {
    // Delete everything here
}
```

**Add/update repositories block:**

```gradle
repositories {

    //
    //Public repositories
    //
    maven {
        url 'https://nexus.barcapint.com/nexus/content/groups/barclays/'
    }
    maven {
        url 'https://nexus.barcapint.com/nexus/content/repositories/barclaysint-group'
    }
    maven {
        url 'https://nexus.barcapint.com/nexus/content/groups/buk-maven2-group/'
    }

    def nexusUser = readProperty("nexusUsername")
    def nexusPassword = readProperty("nexusPassword")

    if (!nexusUser || !nexusPassword) {
        logger.warn('Nexus credentials are missing or incomplete.  Any restricted access repositories will not be included.')
    } else {
        maven {
            url 'https://nexus.barcapint.com/nexus/content/repositories/iAPIs_RELEASE/'
            credentials {
                username nexusUser
                password nexusPassword
            }
        }
        maven {
            url 'https://nexus.barcapint.com/nexus/content/repositories/barclays-restricted-releases/'
            credentials {
                username nexusUser
                password nexusPassword
            }
        }
    }
}


//////////////////////////////////////
//           Functions              //
//////////////////////////////////////
def readProperty(String property){
    String sysValue = System.env.get(property);
    if (sysValue != null) {
        return sysValue;
    }
    if (project.hasProperty(property)) {
        return project.property(property);
    }
    return null;
}

```

### Step 4.8: Add Resolution Strategy Configuration

**Add this configuration if it is missing:**

```gradle
configurations.all {
    resolutionStrategy.cacheChangingModulesFor 1, 'hours'
    resolutionStrategy.cacheDynamicVersionsFor 1, 'hours'
}
```

This configuration controls how Gradle caches dynamic and changing module versions, improving build performance while ensuring dependencies are refreshed periodically.

### Step 4.9: Update Version Overrides

**Change Tomcat version:**

```gradle
// OLD
ext['tomcat.version'] = '9.0.90'

// NEW
ext['tomcat.version'] = '10.1.44'
```

**Add new version overrides:**

```gradle
ext['netty.version'] = '4.1.125.Final'
ext['spring-framework.version'] = '6.2.11'
```

### Step 4.10: Update Configurations Block

**Add exclusion for api-core-boot:**

```gradle
configurations {
    all*.exclude module: 'api-core-boot'
}
```

This prevents SDK2 artifacts from being included transitively.

### Step 4.11: Update Core Dependencies

**At the very top of dependencies block, add SDK3 platform BOM:**

```gradle
dependencies {
    implementation(platform("com.barclays.api:sdk3:${SDK3_VERSION}"))

    // Rest of dependencies below...
}
```

**Delete these SDK2 dependencies:**

```gradle
implementation 'com.barclays.api:api-core-boot'
implementation 'com.barclays.api:api-core-properties'
implementation 'com.barclays.api.tools:api-request-validator'
implementation 'com.barclays.api.tools:gissdk-filters-wrapper'
implementation 'com.barclays.api:api-mesh-client-connector'
implementation 'com.sun.jersey:jersey-core'
```

**Add these SDK3 dependencies:**

```gradle
implementation 'com.barclays.api:bap-bld-lib-request-validator'
implementation 'com.barclays.api:bap-bld-lib-restapi'
implementation 'com.barclays.api:bap-bld-lib-meshconnector'
implementation 'commons-io:commons-io:2.16.1'
```

### Step 4.12: Update Cache Dependencies

**IMPORTANT: Cache Configuration Rules**

1. **KEEP:** `spring-boot-starter-cache` - this is the primary caching dependency
2. **REMOVE:** Any explicit EhCache 2.x dependencies (e.g., `net.sf.ehcache:ehcache:2.x`)
3. **ADD:** Jackson JSR310 support for date/time serialization

```gradle
// Keep this
implementation 'org.springframework.boot:spring-boot-starter-cache'

// Remove this if present
// implementation 'net.sf.ehcache:ehcache:2.10.x'

// Add this
implementation 'com.fasterxml.jackson.datatype:jackson-datatype-jsr310'
```

**Note:** Spring Boot 3.x auto-configuration handles EhCache integration. Cache implementation is configured through `ehcache.xml` (will be migrated separately).

### Step 4.13: Update Test Dependencies

**Delete these test dependencies:**

```gradle
testImplementation 'junit:junit'
testImplementation 'org.mockito:mockito-core'  // old version ~2.x
testImplementation 'com.fasterxml.jackson.datatype:jackson-datatype-joda'
```

**Add these JUnit 5 and Mockito 5 dependencies:**

```gradle
testRuntimeOnly 'org.junit.platform:junit-platform-launcher'
testImplementation 'org.junit.jupiter:junit-jupiter'
testImplementation 'org.junit.platform:junit-platform-suite-api:1.10.1'
testImplementation 'org.assertj:assertj-core:3.24.2'
testImplementation 'org.mockito:mockito-core:5.7.0'
testImplementation 'org.mockito:mockito-junit-jupiter:5.7.0'
```

### Step 4.14: Update Test Task Configuration

**Find and replace:**

```gradle
// OLD
test {
    include 'com/**/*MockTest.class'
    exclude 'com/**/*RealTest.class'
}

// NEW
tasks.named('test') {
    useJUnitPlatform()
    include 'com/**/*MockTest.class'
    exclude 'com/**/*RealTest.class'
}
```

**Key change:** Add `useJUnitPlatform()` to enable JUnit 5 support.

### Step 4.15: Disable Auto-generation Tasks

**Add at the end of build.gradle:**

```gradle
tasks.named('barclaysApiGenerate').configure {
    enabled = false
}
```

This disables SDK3's automatic code generation (if not needed for your project).

Alternatively, set `DISABLE_OAS_GENERATION=true` in `gradle.properties` (see Step 3.1).

### Step 4.16: barclaysApiGenerate Task — Behavior & Generated Package Structure

The `barclaysApiGenerate` task runs before `compileJava` and performs these steps:
1. Downloads `openapi-generator-cli-6.6.0.jar` from Nexus
2. Downloads Barclays custom generator JAR (`bap-bld-lib-oas-generator`)
3. Downloads and unzips Mustache templates (`bap-bld-ext-mustache-templates`)
4. Downloads root OAS zip → generates code under `{groupId}.{projectName}.generated`
5. Moves JPA entities to `{groupId}.{projectName}.generated.jpa`
6. For each `{name}.downstream.spec.url`, generates under `{groupId}.{projectName}.downstream.{name}`

**Generated package structure (output in `build/genCode/`):**
```
com.barclays.api.{projectName}.generated              ← root API models/controllers
com.barclays.api.{projectName}.generated.jpa           ← JPA entities (auto-moved)
com.barclays.api.{projectName}.downstream.{name}       ← downstream client API
com.barclays.api.{projectName}.downstream.{name}.generated  ← downstream models
```

**During Phase 2 (package migration):** These generated packages are auto-created by the plugin. Do NOT manually migrate imports pointing to these packages — they are regenerated from OAS specs. Only migrate hand-written source code.

**IMPORTANT:** The plugin **cannot coexist** with the Spring Boot Gradle plugin in the `plugins {}` block. `bap-bld-lib-plugin` applies Spring Boot internally. Remove any explicit `id 'org.springframework.boot'` from the plugins block.

### Step 4.17: barclaysApiSdk Extension (Optional Overrides)

Override default OAS generation settings in `build.gradle`:

```groovy
barclaysApiSdk {
    openApiGeneratorCliUrl = 'https://...'           // Override OpenAPI Generator CLI JAR URL
    barclaysApiGeneratorUrl = 'https://...'          // Override Barclays generator JAR URL
    barclaysApiGeneratorTemplateUrl = 'https://...'  // Override Mustache templates zip URL
    downloadConnectionTimeout = 60000                // Download timeout (ms), default 30000
    downloadReadTimeout = 60000                      // Read timeout (ms), default 30000
    generatorName = 'oas-spring'                     // Generator type for downstream specs
    workingDirectory = "${projectDir}/tmp"            // Working directory for plugin ops
    rootCommandArgs = ''                             // Extra CLI args for root OAS generation
    downstreamCommandArgs = ''                       // Extra CLI args for downstream generation
}
```

These are rarely needed — defaults work for most projects. Use when troubleshooting OAS generation failures (e.g., timeout on slow Nexus, custom generator).

### Step 4.18: Publishing Configuration

The plugin auto-publishes Maven artifacts with classifiers:

| Classifier | Source | Condition |
|-----------|--------|-----------|
| _(none)_ | Spring Boot fat JAR | Always |
| `infrastructure` | `build/libs/infrastructure.jar` | Always |
| `domain` | `domain/build/libs/domain.jar` | If `domain` subproject exists |
| `sandbox` | `sandbox/build/libs/sandbox.jar` | If `sandbox` subproject exists |
| `stubs` | `sandbox/build/libs/sandbox-fat.jar` | If file exists |

**Required gradle.properties for publishing:**
```properties
REP_URL=https://nexus.barcapint.com/nexus/content/repositories/barclays-releases/
NEXUS_USER=${nexusUsername}
NEXUS_PASSWORD=${nexusPassword}
# Optional overrides:
# nexusReleaseRepo=https://...
# nexusSnapshotRepo=https://...
# ARTIFACT_ID=custom-artifact-name   (default: rootProject.name)
```

---

## Part 5: Additional Build Configuration

### Step 5.1: Add JaCoCo Integration Test Report Task

**Add this task configuration to `build.gradle` (BEFORE the PITest configuration):**

```gradle
// First, register the task
tasks.register('jacocoIntegrationTestReport', JacocoReport) {
    description = 'Generates JaCoCo coverage reports for integration tests.'
    group = 'Verification'
}

// Then configure it
jacocoIntegrationTestReport {
    // TEMPORARY: Disabled until integration tests are re-enabled (see bootJar task comment above)
    // dependsOn integrationTest
    executionData fileTree(project.buildDir).include("/jacoco/integrationTest.exec")

    // Configure source sets
    sourceSets sourceSets.main

    reports {
        xml.required = true
        csv.required = false
        html.required = true
    }
}
```

**Key points:**
- Task is registered first, then configured
- `dependsOn integrationTest` is commented out initially (integration tests fixed in Phase 7)
- Generates XML, HTML reports (no CSV)
- Uses `sourceSets.main` for source analysis

### Step 5.2: Configure PIT Mutation Testing

**PIT is auto-applied by the `bap-bld-lib-plugin`.** Add this configuration block to `build.gradle`:

```gradle
pitest {
    // Auto-detect base package from first Java source file
    def firstSourceFile = fileTree('src/main/java').matching { include '**/*.java' }.files.first()
    def basePackage = firstSourceFile.text.find(/package\s+([\w\.]+);/) { match, pkg -> pkg }
    // Take first 3-4 segments (e.g., com.barclays.api.standingorders)
    basePackage = basePackage.split('\\.')[0..Math.min(3, basePackage.split('\\.').size()-1)].join('.')

    targetClasses = ["${basePackage}.*"]
    targetTests = ["${basePackage}.*"]  // MUST match source package structure!

    // Derive excludedClasses from jacocoCoverageExclusions property
    def jacocoExclusions = project.findProperty('jacocoCoverageExclusions') ?: ''
    excludedClasses = jacocoExclusions ? jacocoExclusions.split(',').collect { it.trim() } : []

    threads = Runtime.getRuntime().availableProcessors()
    outputFormats = ['HTML', 'XML']
    timestampedReports = false
    mutationThreshold = 90
    coverageThreshold = 80
    verbose = true
    testPlugin = 'junit5'
    useClasspathFile = true
    failWhenNoMutations = false

    avoidCallsTo = [
        'java.util.logging',
        'org.apache.log4j',
        'org.slf4j',
        'org.apache.commons.logging',
        'ch.qos.logback'
    ]
}
```

**Key points:**
- PIT plugin is auto-applied by `bap-bld-lib-plugin` — do NOT add `apply plugin: 'info.solidsoft.pitest'`
- `excludedClasses` automatically derives from `jacocoCoverageExclusions` in `gradle.properties`
- `testPlugin = 'junit5'` is required for JUnit 5 compatibility
- `useClasspathFile = true` avoids command-line length issues on Windows
- `mutationThreshold = 90` (mutation score gate), `coverageThreshold = 80` (line coverage gate)
- `verbose = true` provides detailed mutation testing output for debugging
- `failWhenNoMutations = false` allows build to succeed even when no mutations are possible (e.g., DTO-only projects)

---

## Validation and Testing

### Step 1: Validate Gradle Configuration

```bash
# Test Gradle wrapper
$GRADLE_CMD --version
# Expected: Gradle 8.13

# Test dependencies resolution
$GRADLE_CMD dependencies --configuration implementation
# Expected: Should resolve SDK3 dependencies without conflicts
```

### Step 2: Attempt Build

```bash
$GRADLE_CMD clean build --stacktrace
```

**Expected Result at This Stage:**
- ✗ Build will FAIL with Java compilation errors
- ✓ Dependencies should resolve correctly
- ✓ No Gradle configuration errors
- ✓ SDK3 platform BOM should be applied

**This is EXPECTED!** Java code still uses SDK2 packages and will not compile until Java code migration is completed in subsequent phases.

### Step 3: Commit Changes

```bash
git add gradle/ buildSrc/ gradle.properties build.gradle
git commit -m "Phase 1: Complete Gradle 8.13 and SDK3 build configuration"
```

---

## Common Issues and Solutions

### Issue 1: Gradle Wrapper Download Fails

**Symptoms:**
- Cannot download Gradle distribution
- Connection timeout errors

**Solutions:**
1. Verify VPN connection is active
2. Check proxy settings in `gradle.properties`:
   ```properties
   systemProp.http.proxyHost=proxy.barclays.com
   systemProp.http.proxyPort=8080
   systemProp.https.proxyHost=proxy.barclays.com
   systemProp.https.proxyPort=8080
   ```
3. Test Nexus access: `curl https://nexus.barcapint.com/nexus/`

### Issue 2: SDK3 Dependencies Not Found

**Symptoms:**
- Could not resolve: com.barclays.api:sdk3:1.12.007
- Could not resolve: com.barclays.api:bap-bld-lib-plugin

**Solutions:**
1. Verify `SDK3_VERSION` property in gradle.properties
2. Check Nexus repository access
3. Verify buildSrc/build.gradle has correct repository URL
4. Clear Gradle cache: `~/.gradle/caches/` on macOS/Linux, `%USERPROFILE%\.gradle\caches\` on Windows

### Issue 3: Plugin Application Fails

**Symptoms:**
- Plugin 'com.barclays.api.bap-bld-lib-plugin' not found
- Could not apply plugin

**Solutions:**
1. Verify buildSrc/build.gradle has all three SDK3 plugins
2. Check that SDK3_VERSION is properly loaded in buildSrc
3. Ensure buildSrc/build.gradle has NO plugins block (common mistake)
4. Clean and rebuild: `$GRADLE_CMD clean --refresh-dependencies`

### Issue 4: Duplicate Plugin Warnings

**Symptoms:**
- Warning about Spring Boot plugin applied multiple times
- Duplicate plugin application warnings

**Solutions:**
1. Remove explicit `apply plugin: 'org.springframework.boot'` from root build.gradle
2. bap-bld-lib-plugin applies Spring Boot, dependency-management, JaCoCo, PIT, SonarQube, CycloneDX, and maven-publish automatically (see Step 4.1 table) — it **cannot coexist** with these in the `plugins {}` block
3. Remove `io.spring.dependency-management` plugin (managed by SDK3)

### Issue 6: barclaysApiGenerate Throws NullPointerException

**Symptoms:**
- `NullPointerException` during `integrationTest` or `test`
- Task fails even when OAS generation is not needed

**Solutions:**
1. Set `DISABLE_OAS_GENERATION=true` in `gradle.properties`
2. Or disable via Gradle: `tasks.named('barclaysApiGenerate').configure { enabled = false }`
3. If OAS generation IS needed: ensure `root.spec.url` is set in `gradle.properties`

### Issue 5: Java Version Conflicts

**Symptoms:**
- Compilation fails with "invalid target release: 21"
- "source/target value 8 is obsolete"

**Solutions:**
1. Verify JDK 21 is active: `java -version`
2. Switch to Java 21: `jenv local 21` or set JAVA_HOME
3. Verify IDE project SDK is set to Java 21
4. Clean build: `$GRADLE_CMD clean build`

---

## CI/CD Tasks Registered by the Plugin

### `gitlab-java-build`
CI/CD task used by GitLab pipelines. Depends on: `compileJava`, `compileTestJava`, `bootJar`. If `sandbox` subproject exists, finalizes with `sandbox:build`.

### `gitlab-java-unit-test`
CI/CD task for unit testing in GitLab pipelines. Depends on: `compileJava`, `compileTestJava`, `test`.

### `initBuildPipelineFile`
Scaffolds GitLab CI bootstrap files (invoke manually once during project setup):
1. `.gitlab-ci.yml` — includes `gradle-java-ci-pipeline` component (v1.3)
2. `project_metadata.yml` — metadata template (owner, business_unit, pod, itba, etc.)
3. Sonar configuration block in `build.gradle`

### `buildInfo`
Creates `build/classes/main/META-INF/api-buildInfo.properties` after `compileJava`. Reads these env vars:
- `GIT_REPO`, `BRANCH_NAME`, `BRANCH_COMMIT_ID`, `BUILD_URL`
- All `bap-bld-lib-*` dependency versions from runtime classpath

---
