---
name: ear-to-war-conversion
description: Converts MCA1 EAR (multi-module, war/ submodule) projects to single-module WAR structure. Detects EAR layout, backs up originals, restructures files, combines build.gradle, configures functional tests, removes Eclipse IDE artefacts, and verifies build. Safe no-op if already WAR structure.
version: 1.3.0
author: Barclays
tags: [mca1, ear, war, migration, barclays, gradle]
user-invocable: false
source: barclays-claude-code-plugins/plugins/mca-jdk-upgrade/skills/ear_to_war_conversion/SKILL.md
owner: Barclays AI (barclaysai@barclays.com)
review-trigger: When Java/Spring Boot target versions change or new MCA project structures are identified
status: Full
---

# EAR to WAR Conversion Skill
## Quick Start

This skill covers the EAR-to-WAR conversion required for MCA1 projects before JDK upgrade.

```bash
# Run the EAR-to-WAR conversion phase
/mca1-jdk-upgrade <project_path>   # Phase 0 handles EAR-to-WAR automatically
```


## Purpose

Converts MCA1 EAR-packaged projects (multi-module Gradle layout with a nested `war/` submodule) into a single-module WAR structure compatible with the MCA JDK 21 upgrade flow.

This skill is **idempotent and safe**: if the project is already single-module WAR, Phase 1 returns `ear_detected = false` and exits immediately — no files are changed.

**All file operations use Read/Write/Glob/Edit tools** — no reliance on bash `cp`, `rsync`, `mv`, or `rm`. This makes the skill cross-platform (Windows and Mac).

---

## Phase 1: Detection

**Objective:** Determine whether this project uses EAR packaging.

EAR is detected if **either** signal is present:

**Signal A — `eps-ear` plugin (primary signal):**
`build.gradle` applies the `eps-ear` plugin:
```
Grep(pattern="apply plugin: ['\"]eps-ear['\"]", path="build.gradle")
```
If this matches → `EAR_DETECTED=true` immediately. No further checks needed.

**Signal B — `war/` submodule layout (structural signal):**
Both of the following must be true:
1. `war/build.gradle` exists — check with `Glob("war/build.gradle")`
2. `settings.gradle` contains `include ':war'` or `include 'war'` — check with `Grep(pattern="include ['\"](:war|war)['\"]", path="settings.gradle")`

If both match → `EAR_DETECTED=true`.

**Detection logic:**

Run Signal A first:
```
Grep(pattern="apply plugin: ['\"]eps-ear['\"]", path="build.gradle")
```

If no match, run Signal B:
```
Glob("war/build.gradle")
Grep(pattern="include ['\"](:war|war)['\"]", path="settings.gradle")
```

**If either signal matches → `EAR_DETECTED=true`:**
- Set `ear_detected = true` in state file
- Proceed to Phase 2

**If no signal matches → `EAR_DETECTED=false`:**
- Log: `"Already single-module WAR structure. Skipping EAR→WAR conversion."`
- Set `ear_detected = false` in state file
- Return — do NOT execute Phases 2, 3, or 4

---

## Phase 2: Pre-Conversion Backup

**Objective:** Preserve originals so the conversion can be rolled back if needed.

Use the **Read tool then Write tool** for each individual file backup. Use Bash only to copy entire directories.

| Source | Backup destination |
|--------|-------------------|
| `build.gradle` | `backup/root-build.gradle.backup` |
| `src/` (if exists at root) | `backup/root-src/` |
| `src/main/application/META-INF/application.xml` (if exists) | preserved inside `backup/root-src/` |
| `settings.gradle` | `backup/settings.gradle.backup` |
| `war/` (full copy) | `backup/war-backup/` |
| `war/src/main/webapp/WEB-INF/web.xml` (if exists) | `backup/web.xml` |

**Implementation:**

```bash
# Create backup directory
mkdir -p backup
```

For individual files — Read then Write:
- Read `build.gradle`, Write to `backup/root-build.gradle.backup`
- Read `settings.gradle`, Write to `backup/settings.gradle.backup`
- If `war/src/main/webapp/WEB-INF/web.xml` exists (check with Glob), Read then Write to `backup/web.xml`

For directory copies — use Bash (cross-platform approach):
```bash
# Copy entire war/ submodule
cp -r war backup/war-backup

# Copy root src/ if it exists
[ -d src ] && cp -r src backup/root-src
```

On Windows, the agent should use `xcopy /E /I war backup\war-backup` and `xcopy /E /I src backup\root-src` instead of `cp -r`.

Log each backup path created.

---

## Phase 3: Structural Conversion

Execute steps 1–10 in sequence. Use Read/Write/Edit/Glob tools for file operations. Use Bash only when a tool equivalent is not available.

### Step 1: Clean Root

Delete root `build.gradle` and root `src/` (already backed up in Phase 2). This also removes the EAR deployment descriptor (`src/main/application/META-INF/application.xml`) if present.

Use Glob to confirm `src/` exists before deleting:
```bash
rm -f build.gradle
rm -rf src
```

On Windows: `del build.gradle` and `rmdir /S /Q src`.

### Step 2: Restructure Project Files

Move all content from `war/` to project root, **excluding** `war/build/`.

Use Glob to discover all files under `war/` (excluding `war/build/`), then for each file:
- Read the file content
- Write it to the equivalent path at project root (strip the `war/` prefix)

After all files are promoted, delete the `war/` directory:
```bash
# Remove war/ now that all content is at root
rm -rf war
```

On Windows: `rmdir /S /Q war`.

After this step, the project root contains the source tree previously under `war/`, including `war/build.gradle` now at `./build.gradle`. This is an intermediate state — Step 5 will overwrite `./build.gradle` with the properly merged version.

**Note:** After promotion, `Feature/` and `Fixture/` directories (Cucumber test artefacts) land at project root. This is correct — `FluidTestRunner.java` expects `features = "Feature"` at the working directory root.

### Step 3: Update settings.gradle

Use Read tool to get the current `settings.gradle` content. Extract the `rootProject.name` value.

Use Write tool to produce a new `settings.gradle` containing only:

```
rootProject.name = '<extracted-name>'
```

Remove all `include` statements, `project(":war").*` configuration lines, and any other content.

### Step 4: Remove Web Configuration

Check for `src/main/webapp/WEB-INF/web.xml` using Glob. If it exists, delete it (already backed up). Spring Boot annotation config replaces XML-based web configuration.

```bash
rm -f src/main/webapp/WEB-INF/web.xml
```

On Windows: `del src\main\webapp\WEB-INF\web.xml`.

### Step 5: Combine build.gradle

Read both backed-up files and produce a single merged `build.gradle` at project root:

**Sources (always read from backups, not the intermediate promoted file):**
- `backup/root-build.gradle.backup` — original root EAR `buildscript {}` and plugin declarations
- `backup/war-backup/build.gradle` — original WAR dependencies, repositories, test config

The merged result overwrites the intermediate `./build.gradle` that Step 2 promoted from `war/`.

**Merge rules:**
1. Keep `buildscript {}` block from root backup (EAR bootstrap config)
2. Replace `apply plugin: 'ear'` with `apply plugin: 'eps2-war'` (for MCA1/EPS projects: `com.barclays.eps` group). Add to `buildscript dependencies`: `classpath("com.barclays.mca.devops:gradle-eps2-war-plugin:8.2.+") { changing = true }`. **IMPORTANT**: `apply plugin: 'eps2-war'` must appear **after** `apply plugin: 'org.springframework.boot'` — it depends on the `bootWar` task that Spring Boot registers. For non-EPS MCA2 projects use `apply plugin: 'war'` with no additional classpath entry.
3. Remove any `deploy project(':war')` or `deploy project('war')` dependency lines
4. Merge `dependencies {}` blocks from both files — deduplicate identical lines
5. Remove `ear {}` configuration block entirely
6. Carry over `repositories {}`, `configurations {}`, `test {}`, `jar {}`, `war {}`, `bootRepackage {}`, `bootJar {}` blocks from `war/build.gradle`
7. Remove any `subprojects {}` or `allprojects {}` blocks that reference `:war`
8. Preserve any variable declarations from root backup (e.g., `ext.pluginBaseDirectory`) that are referenced in `apply from:` statements

Use Read tool on both source files, construct merged content, Write tool to `build.gradle`.

### Step 5.5: Fix war/-Prefixed Path References

After promotion, `war/src/` no longer exists. Use Grep to find all occurrences of `war/src/` in `build.gradle`:

```
Grep(pattern="war/src/", path="build.gradle", output_mode="content")
```

For each match, use Edit tool to replace:
- `${rootDir}/war/src/` → `${rootDir}/src/`
- `war/src/` → `src/`

These typically appear in `test {}`, `bootRun {}`, `jvmArgs`, and resource path declarations.

Also scan `gradle/scripts/` for the same pattern using Grep on that directory, and apply the same replacements.

**Also fix stale `war/src/` paths in application properties files:**

Use Grep to find all occurrences of `war/src/` across `src/main/resources/`:

```
Grep(pattern="war/src/", path="src/main/resources/", output_mode="content")
```

These typically appear in `application-dev.properties` as SSL keystore paths like:
```
core.rest-template.socket-factory.external-ssl.key-store-path=${rootDir}/war/src/main/resources/keystores/mqssl.jks
```

For each match, determine the correct post-flattening path. Keystores that were previously under `war/src/main/resources/` are typically now under `src/test/resources/` (verify with Glob). Replace:
- `${rootDir}/war/src/main/resources/keystores/` → `${rootDir}/src/test/resources/keystores/`
- `${rootDir}/war/src/` → `${rootDir}/src/`

> **Note:** `${rootDir}` in a Spring properties file is NOT a Gradle property. It only resolves if a system property or Spring property named `rootDir` is defined at runtime (e.g. via `-DrootDir=...` JVM arg). If no such property is defined, Spring will throw an `IllegalArgumentException` for unresolvable placeholders unless a default is provided (`${rootDir:}`). These keystore properties are usually overridden by JVM args in `bootRun` (`-Djavax.net.ssl.trustStore=...`), so the unresolvable placeholder may never cause a runtime error — but the stale `war/` path should still be corrected to avoid confusion.

### Step 5.6: Verify No Dependencies Were Dropped

After writing the merged `build.gradle`, grep `backup/root-build.gradle.backup` and `backup/war-backup/build.gradle` for all dependency declarations, then verify each artifact name appears in the merged `build.gradle`. If any are missing, add them using Edit tool and log each restoration.

> Silent merge gaps cause compile failures that are hard to trace back to this step.

### Step 6: Update JVM Arguments

Use Grep to check for `-Xbootclasspath` entries referencing EAR paths:

```
Grep(pattern="Xbootclasspath.*ear", path="build.gradle", output_mode="content")
```

Use Edit tool to remove any matching lines found.

### Step 7: Modernize Dependency Configurations

In the merged `build.gradle`, replace deprecated Gradle dependency configurations with their modern equivalents:

| Deprecated | Modern equivalent |
|------------|-------------------|
| `compile` | `implementation` |
| `testCompile` | `testImplementation` |
| `runtime` | `runtimeOnly` |
| `providedCompile` | `compileOnly` |
| `providedRuntime` | `runtimeOnly` |

Apply to the `dependencies {}` block only. Use Edit tool with `replace_all: true` for each substitution. Be precise — only match `compile(`, `compile '`, `compile "` etc., not substrings of other words.

### Step 8: Post-Combine Gradle 8 Cleanup

Remove configurations that no longer apply after EAR removal:

- `configurations.all { resolutionStrategy.force ... }` blocks that reference removed EAR artifacts
- `subprojects { ... }` and `allprojects { ... }` blocks that only existed to configure `:war`
- Any remaining `ear` task configuration blocks
- `integrationTest*` dependency configurations that reference the `:war` submodule — comment them out (they may need manual re-enablement after migration)

Use Grep to identify candidates, Edit tool to remove.

### Step 9: Migrate gradle/scripts/*.gradle (Line-Safe)

Use Glob to check whether `gradle/scripts/` directory exists: `Glob("gradle/scripts/*.gradle")`.

For each matching file:
1. Read the file content
2. Write a backup to `backup/gradle-scripts-line-safe/<filename>.backup`
3. Apply the same configuration replacements as Step 7 using Edit tool (Read → modify → Write)

### Step 10: Configure Functional Tests

**Objective:** Wire up `src/functional/` as a Gradle source set and add a `functionalTest` task so functional (Cucumber/BDD) tests can be compiled and run.

**Detection:** Use Glob to check whether `src/functional/java/` exists.

If `src/functional/java/` does not exist, skip this step and log `"No functional test source set found — skipping Step 10"`.

If it exists, proceed:

**10.1 — Identify existing Cucumber runner and migrate imports**

Use Glob to find `**/FluidTestRunner.java` (or any `*Runner.java`) under `src/functional/`. Read the file to extract:
- `features` path value (e.g., `"Feature"` — relative to working directory, so `Feature/` must be at project root ✓)
- `glue` package (e.g., `"com.barclays.cumcumber.steps"`)
- `plugin` outputs (e.g., `html:build/cucumber/test-reports`)

Confirm `Feature/` exists at project root (it should, from Step 2 promotion). Log its presence.

**Migrate old Cucumber API imports:** If the runner uses `cucumber.api.*` imports (old Cucumber pre-5.0), use Edit tool to replace them with the modern `io.cucumber.junit.*` equivalents:

| Old import | New import |
|------------|-----------|
| `import cucumber.api.CucumberOptions;` | `import io.cucumber.junit.CucumberOptions;` |
| `import cucumber.api.junit.Cucumber;` | `import io.cucumber.junit.Cucumber;` |

Also update the `tags` field syntax if it uses the old negation style:
- Old: `tags = { "~@ignore" }` → New: `tags = "not @ignore"`

**10.2 — Add sourceSets block to build.gradle**

Use Grep to check whether `sourceSets` already exists in `build.gradle`.

If it does not exist, use Edit tool to add the following after the `java { ... }` block (or after `apply plugin: 'java'` if no `java {}` block):

```gradle
sourceSets {
    functional {
        java {
            srcDirs = ['src/functional/java']
        }
        resources {
            srcDirs = ['src/functional/resources']
        }
        compileClasspath += sourceSets.main.output + configurations.testRuntimeClasspath
        runtimeClasspath += output + compileClasspath
    }
}
```

If a `sourceSets` block already exists, use Edit tool to add the `functional { ... }` entry inside it.

**10.3 — Move Feature/ and Fixture/ into src/functional/**

All functional test artefacts should live under `src/functional/` to keep the project organised.

After Step 2, `Feature/` and `Fixture/` land at project root (promoted from `war/`). Move them:

```bash
mv Feature src/functional/Feature
mv Fixture src/functional/Fixture
```

On Windows: `move Feature src\functional\Feature` and `move Fixture src\functional\Fixture`.

If either directory does not exist (use Glob to check), skip the move for that directory and log it.

**10.4 — Add functionalTest task to build.gradle**

Use Grep to check whether a `functionalTest` task already exists in `build.gradle`.

If it does not exist, use Edit tool to append the following after the `test { ... }` block:

```gradle
task functionalTest(type: Test) {
    description = 'Runs functional (Cucumber/BDD) tests.'
    group = 'verification'
    testClassesDirs = sourceSets.functional.output.classesDirs
    classpath = sourceSets.functional.runtimeClasspath
    useJUnitPlatform()
    workingDir = file("${rootDir}/src/functional")
}
```

`workingDir = file("${rootDir}/src/functional")` ensures that `features = "Feature"` in `@CucumberOptions` resolves to `src/functional/Feature/`, and fixture path references resolve correctly.

**10.5 — Add functional dependencies**

Use Grep to check whether `functionalImplementation` already appears in `build.gradle`.

In the `configurations {}` block, add:

```gradle
    functionalImplementation.extendsFrom testImplementation
    functionalRuntimeOnly.extendsFrom testRuntimeOnly
```

This inherits all test dependencies (including BOM platform constraints) for the functional source set without duplication.

Also add Cucumber dependencies inside the `dependencies {}` block:

```gradle
    functionalImplementation 'io.cucumber:cucumber-junit:7.15.0'
    functionalImplementation 'io.cucumber:cucumber-java:7.15.0'
```

### Step 11: Remove Eclipse IDE Artefacts

**Objective:** Remove Eclipse-specific files that have no relevance to the Gradle build and should not be committed.

**Detection:** Use Glob to identify Eclipse artefacts at project root and under `war/` (post-promotion):

Patterns to check:
- `.classpath` (Eclipse classpath file)
- `.project` (Eclipse project descriptor)
- `.settings/` directory (Eclipse settings)
- `bin/` directory (Eclipse compiled output — not Gradle's `build/`)

For each file found using Glob:
- Delete it using Bash:
  ```bash
  rm -f .classpath
  rm -f .project
  rm -rf .settings
  rm -rf bin
  ```
  On Windows: `del .classpath`, `del .project`, `rmdir /S /Q .settings`, `rmdir /S /Q bin`.

**Update .gitignore:**

Use Grep to check whether `.classpath`, `.project`, `.settings`, and `bin/` are already in `.gitignore`.

For any that are missing, use Edit tool (or Read → Write) to append them to `.gitignore`. If `.gitignore` does not exist, use Write tool to create it with:

```
.classpath
.project
.settings/
bin/
```

Log each artefact removed.

### Step 12: Update GitLab CI Variables

**Objective:** Remove `war/build/` path prefixes from CI variable values — these paths referred to the `war/` submodule's build output directory, which no longer exists after promotion to single-module.

**Detection:** Use Glob to check whether `.gitlab-ci-variables.yml` exists at project root.

If it does not exist, skip this step.

If it exists, use Grep to find all occurrences of `war/build/` in `.gitlab-ci-variables.yml`:

```
Grep(pattern="war/build/", path=".gitlab-ci-variables.yml", output_mode="content")
```

For each match, use Edit tool to replace `war/build/` with `build/`.

**Typical variables requiring update:**

| Variable | Old value | New value |
|----------|-----------|-----------|
| `MUT_TEST_PITEST_REPORT_PATH` | `war/build/reports/pit/` | `build/reports/pit/` |
| `BUILD_CLASSES_PATH` | `war/build/classes/` | `build/classes/` |
| `BUILD_LIB_PATH` | `war/build/libs/` | `build/libs/` |
| `JACOCO_CSV_REPORT_PATH` | `war/build/reports/jacoco/...` | `build/reports/jacoco/...` |
| `JACOCO_XML_REPORT_PATH` | `war/build/reports/jacoco/...` | `build/reports/jacoco/...` |
| `JUNIT_XML_PATH` | `war/build/test-results/...` | `build/test-results/...` |

Use Edit tool with `replace_all: true` to replace all `war/build/` occurrences in the file in a single operation.

Also check `.gitlab-ci.yml` for any hardcoded `war/build/` references using Grep, and apply the same replacement.

### Step 13: Harden `bootRun` for Spring Boot 3.x and Gradle 8

**Objective:** Fix two categories of `bootRun` failures that appear after EAR→WAR conversion with Spring Boot 3.x.

This step applies only when `bootRun {}` is present in `build.gradle`. Use Grep to check:
```
Grep(pattern="bootRun", path="build.gradle", output_mode="content")
```

---

#### 13.1 — Fix `archivePath` Deprecation (Gradle 7+)

If `bootRun` uses a `pathingJar` pattern, the old Gradle API `archivePath` was removed in Gradle 7. Look for:

```
Grep(pattern="archivePath", path="build.gradle", output_mode="content")
```

If found, replace `pathingJar.archivePath` with `pathingJar.archiveFile.get().asFile`:

```groovy
// OLD (broken in Gradle 7+)
classpath = files(sourceSets.main.output.files, pathingJar.archivePath)

// NEW
classpath = files(sourceSets.main.output.files, pathingJar.archiveFile.get().asFile)
```

---

#### 13.2 — Verify `mainClass` Points to Actual Application Class

Use Grep to find the `mainClass` value in `bootRun`:
```
Grep(pattern="mainClass\s*=", path="build.gradle", output_mode="content")
```

Then verify the referenced class exists by searching for `@SpringBootApplication`:
```
Grep(pattern="@SpringBootApplication", path="src/main/java/", output_mode="content")
```

The `mainClass` must match the FQCN of the actual `@SpringBootApplication` annotated class. A common mistake after migration is setting `mainClass = 'com.barclays.xxx.Application'` when the actual class is named `XxxApplication` or `ChequeProcessingApplication`.

If mismatched, use Edit tool to correct it.

---

#### 13.3 — Override Log Paths for CI Environments (Spring Boot 3.x BREAKING CHANGE)

**Critical:** Spring Boot 3.x changed Logback startup failure handling. In Spring Boot 2.x, a `RollingFileAppender` that cannot create its log directory emits a warning and continues. In Spring Boot 3.x, this causes a **fatal `IllegalStateException: Logback configuration error detected`** that prevents the application from starting.

MCA applications typically configure `logging.file.path=/opt/springboot/logs/${HOSTNAME}/` in `application.properties` or profile-specific files. This path does not exist in CI component-test or bootRun environments.

**Fix — add these overrides to the `bootRun {}` block:**

```groovy
bootRun {
    dependsOn pathingJar
    doFirst {
        new File("${rootDir}/build/logs").mkdirs()   // Create dir BEFORE Spring starts
        classpath = files(sourceSets.main.output.files, pathingJar.archiveFile.get().asFile)
    }
    // ... existing jvmArgs ...
    jvmArgs "-Dlogging.file.path=${rootDir}/build/logs"
    jvmArgs "-Dserver.tomcat.accesslog.directory=${rootDir}/build/logs"
}
```

The `mkdirs()` call in `doFirst` ensures the directory exists before the JVM starts. The two JVM args override whatever `logging.file.path` and `server.tomcat.accesslog.directory` are set to in any Spring profile (JVM system properties always win over application properties).

**Detection — check if already present:**
```
Grep(pattern="logging.file.path", path="build.gradle", output_mode="content")
```

If not present, use Edit tool to add both args and the `mkdirs()` call.

**Also check `application-dev.properties` for Tomcat access log path:**
```
Grep(pattern="server.tomcat.accesslog.directory", path="src/main/resources/", output_mode="content")
```

If found with a value pointing to `/opt/springboot/...`, the `jvmArgs` override above handles it at runtime. No change to the properties file is needed since the JVM arg takes precedence.

---

#### 13.4 — Disable JCEKS Placeholder Resolver in `bootRun`

**Critical:** MCA applications that include `mca-jceks-spring-properties-processor` on the classpath trigger `JceksSecretsToSpringEnvironmentPropertiesPostProcessor` at startup. If `placeholder.resolver.vault=true` is set in `application.properties`, this processor attempts to open a JCEKS keystore whose path is null in CI/local `bootRun` environments, causing:

```
JCEKS KeyStore initialization failed.
java.lang.NullPointerException
    at java.base/java.io.FileInputStream.<init>(FileInputStream.java:144)
    at com.barclays.global.mca.libs.placeholder.JCEKeyStorePropertyPlaceholderProcessor.initializeKeyStore(...)
java.lang.NullPointerException: Cannot invoke "java.security.KeyStore.aliases()" because "this.keyStore" is null
```

This error occurs **after** the Logback fix (Step 13.3) is applied and the app starts to boot — it is a separate failure that also prevents `bootRun` from completing.

**Detection — check if vault placeholder is enabled:**
```
Grep(pattern="placeholder\.resolver\.vault", path="src/main/resources/", output_mode="content")
```

If the result shows `placeholder.resolver.vault=true`, the fix is required.

**Fix — add override to `bootRun {}` block:**

```groovy
jvmArgs "-Dplaceholder.resolver.vault=false"
```

JVM system properties always override `application.properties`, so deploying to real environments (where the keystore is present) is unaffected — deployed servers set the keystore path via external configuration.

---

#### 13.5 — Remove `<task:annotation-driven/>` from XML Configs (Spring Boot 3.x BREAKING CHANGE)

**Critical:** Spring Boot 3.x (Spring Framework 6.x) throws a **fatal `BeanDefinitionParsingException`** if more than one `ScheduledAnnotationBeanPostProcessor` exists in the context:

```
BeanDefinitionParsingException: Configuration problem: Only one ScheduledAnnotationBeanPostProcessor may exist within the context.
Offending resource: class path resource [some-config.xml]
```

Spring Boot auto-configuration always creates a `ScheduledAnnotationBeanPostProcessor`. If any XML config loaded via `@ImportResource` also declares `<task:annotation-driven/>`, Spring 6.x rejects the duplicate. Spring 5.x (Spring Boot 2.x) silently tolerated this.

**Detection — scan all XML resources for the element:**
```
Grep(pattern="task:annotation-driven", path="src/main/resources/", output_mode="content")
```

**Fix — remove the element and clean up the namespace declaration:**

1. Remove `<task:annotation-driven/>` from the offending XML file
2. Remove the `xmlns:task="http://www.springframework.org/schema/task"` namespace declaration
3. Remove the task schema location from `xsi:schemaLocation`

Spring Boot handles scheduling auto-configuration automatically. The XML element is redundant and must be removed.

---

**Step 13 checklist:**
- [ ] `archivePath` → `archiveFile.get().asFile` (if `pathingJar` pattern used)
- [ ] `mainClass` verified against actual `@SpringBootApplication` class
- [ ] `logging.file.path` override added to `bootRun`
- [ ] `server.tomcat.accesslog.directory` override added to `bootRun`
- [ ] `mkdirs()` for `${rootDir}/build/logs` in `doFirst`
- [ ] `placeholder.resolver.vault=false` override added if `mca-jceks-spring-properties-processor` on classpath
- [ ] `<task:annotation-driven/>` removed from all XML configs loaded via `@ImportResource`

---

### Step 14: Update `ftpupload.gradle` EAR References

After EAR→WAR conversion, `gradle/scripts/ftpupload.gradle` (if present) may still reference `.ear` artifacts in its `ftp` and `scp` tasks. These tasks are not called automatically by the standard build, but they will fail if ever invoked.

Use Grep to check:
```
Grep(pattern="\.ear", path="gradle/scripts/ftpupload.gradle", output_mode="content")
```

If `.ear` references are found, update them to `.war`:
```groovy
// OLD
move(file: "${rootDir}/build/libs/${NAME}-${REVISION}.ear", tofile: "...")
// NEW
move(file: "${rootDir}/build/libs/${NAME}-${REVISION}.war", tofile: "...")
```

---

## Phase 4: Verify

Run `compileJava` to confirm the structural conversion did not break compilation. Allow up to 3 retries with auto-fix attempts for compilation errors.

```bash
$GRADLE_CMD compileJava 2>&1 | tee -a "$LOG_FILE"
```

**On success:** Log `"EAR→WAR conversion verified: compileJava passed"`. Phase complete.

**On failure (attempt 1–3):**
- Read compiler error output
- Identify missing imports, moved classes, or classpath issues introduced by restructuring
- Apply targeted fixes using Edit tool
- Retry `$GRADLE_CMD compileJava`

**On failure after 3 attempts:** Log the errors, set `ear_conversion_verify_status = failed` in state, and continue — Phase 2 of the main migration (full compilation) will surface and fix remaining issues.

Do NOT run the full build here — `compileJava` only. Full build verification is Phase 2's responsibility.

---

## State File Updates

Record the following in `.mca2-jdk-migration-state.json` under `phases.phase_0`:

```json
{
  "ear_to_war_converted": true,
  "ear_conversion_verify_status": "passed"
}
```

Or, if EAR was not detected:

```json
{
  "ear_to_war_converted": false
}
```

These flags are used by the orchestrator and Phase 0 validation to determine whether EAR→WAR checks apply.

## Agent Self-Check

- [ ] Skill loaded before the upgrade phase it governs
- [ ] Source version (Java 8 / Spring Boot 2.7) confirmed before applying upgrade patterns
- [ ] Build verified with ./gradlew clean build after each phase
- [ ] No MCA1/legacy patterns remain after migration step
- [ ] Test suite still passes after code changes
- [ ] Upgrade summary logged to migration report
