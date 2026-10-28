---
name: cwe-937-vulnerable-components
description: "CWE-937: Vulnerable Components Remediation — Safely upgrade or replace known-vulnerable third-party dependencies by validating the replacement version with the user before applying build file changes. Covers Gradle, Maven, and npm projects across any library (Log4j, Spring, Commons, Jackson, etc.)."
source: "Barclays BUK Security Standards - CWE Remediation"
owner: "Security Champions"
review-trigger: "Any CWE-937 finding in Wiz or threat model reports"
status: "stable"
---

# CWE-937: Using Components with Known Vulnerabilities

## CWE Information

- **CWE ID**: CWE-937
- **CWE Name**: Using Components with Known Vulnerabilities
- **Severity**: High / Critical (depends on the CVE CVSS score)
- **OWASP Category**: A06:2021 — Vulnerable and Outdated Components

## Purpose

Remediate known-vulnerable third-party dependencies by removing or upgrading the affected library to a safe, validated version. This skill covers any library across any ecosystem — Log4j, Spring Framework, Apache Commons, Jackson, Netty, OpenSSL, etc. Before making any build file change, the skill validates the replacement version with the user (or auto-selects a safe version using documented criteria when the user cannot confirm). The skill detects the project's existing version management pattern (ext block, gradle.properties, version catalog, pom.xml properties, direct declaration) and applies the fix using the same pattern to keep the build consistent.

**Static scanner visibility:** Some WIZ tools (including Wiz CLI) scan `build.gradle` statically — they read declared version literals directly without evaluating Gradle's dependency resolution. For these tools, runtime-resolution mechanisms like `resolutionStrategy.eachDependency { useVersion }` and `dependencies { constraints {} }` are invisible — the scanner continues to report the version it sees declared in the file. When a finding comes from a static scanner, the fix MUST produce an explicit version string visible in the build file. The correct mechanisms are: (a) update the declared version in-place, or (b) use `resolutionStrategy { force "group:artifact:safe_version" }` which writes the target version explicitly in the config block.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the affected build file (e.g., `build.gradle`, `pom.xml`, `package.json`).
  - `cwe_id` (string, required): Must be `CWE-937`.
  - `cve_ids` (array of strings, required): One or more CVE IDs driving the remediation (e.g., `["CVE-2022-23302", "CVE-2022-23305", "CVE-2022-23307"]`).
  - `affected_package` (string, required): Vulnerable package in `group:artifact` format for Java or `name` for npm (e.g., `log4j:log4j`, `org.springframework:spring-webmvc`, `lodash`).
  - `current_version` (string, required): Currently declared vulnerable version (e.g., `1.2.17`).
  - `title` (string, optional): Short description of the vulnerability.
  - `severity` (string, optional): `critical`, `high`, `medium`.
- **repo_root** (required, string): Absolute path to the repository root.
- **safe_version** (optional, string): User-confirmed safe replacement version. If not provided, the skill prompts the user and falls back to auto-selection.
- **nexus_confirmed** (optional, boolean): Whether the user has confirmed the replacement version is available in the internal Nexus repository. Defaults to `false`.
- **version_source** (optional, string): `"config_validated"` or `"wiz_recommended"`. When `"wiz_recommended"`, Steps V1-V2 are skipped and the provided `safe_version` (from the Wiz report) is used directly. Defaults to `"config_validated"`.

## Pre-Flight: Version Validation (MANDATORY — DO THIS BEFORE ANY FILE CHANGE)

**This step MUST execute before reading or modifying any build file.**

### Step V0: Determine Version Source (JDK Version Gate)

Before loading any config, check the `version_source` input:

- **If `version_source == "wiz_recommended"`** (JDK ≥ 9 path):
  - SKIP Steps V1 and V2 entirely (no safe-versions.json loading)
  - Set `safe_version` = the provided `safe_version` input (this is `vuln.fixed_version` from the Wiz report)
  - Set `nexus_confirmed` = `false` (Wiz versions are not Nexus-validated)
  - Set `version_source` = `"wiz_recommended"`
  - Log: `ℹ️ Using Wiz-recommended version: {affected_package} → {safe_version} (JDK 9+ path, no Nexus validation)`
  - Add warning: `"⚠️ Version sourced from Wiz report — not validated against internal Nexus or safe-versions.json config"`
  - Proceed directly to Step V3 (confirm selection before file changes)

- **If `version_source == "config_validated"` or not provided** (JDK ≤ 8 / default path):
  - Execute Steps V1 and V2 as documented below (load safe-versions.json)
  - This is the existing behavior, unchanged

### Step V1: Load Pre-Validated Safe Versions from Config

1. Read `{plugin_root}/config/safe-versions.json`, where `{plugin_root}` is the `plugin_root` value returned by `resolve_skill.py` when this skill was loaded (the installed Detox plugin directory — NOT the target repo)
   - Never read a `safe-versions.json` from the target project; it must not influence version selection
   - If the file is missing, STOP and report a plugin-installation problem
2. Search for the vulnerable `affected_package` in the `versions` section
3. If found:
   - Validate required fields exist: `safe_version`, `strategy`, `nexus_confirmed`
   - If any required field is missing: Return error JSON with `status: "needs_review"` and message "Config entry malformed — missing required fields"
   - Check the `expires` date on the entry: if today > expires, flag as stale and proceed to exclusions check
   - Set `safe_version` to the config entry's `safe_version`
   - Set `nexus_confirmed` to the config entry's `nexus_confirmed` value
   - Set `version_source` to `config_validated`
   - Log: `✅ Using pre-validated version from config: {affected_package} → {safe_version} (Nexus: {nexus_confirmed})`
   - Proceed to Step V3 (confirm selection before file changes)

4. If NOT found in config or entry expired:
   - Check if the package is in the `exclusions` section
   - If excluded: Set `status: "needs_review"` and return error indicating manual review required
   - If expired: Set `status: "needs_review"` and return message "Config entry expired — review_cadence exceeded, manual version verification required"
   - Log: `⚠️ Package {affected_package} not in pre-validated config. Manual review required.`

### Step V2: Auto-select a safe version (only if not in config)

**This step is SKIPPED** when using the pre-validated config. All CWE-937 findings should use Step V1.

If a package is encountered that is NOT in the config and NOT excluded:
- Apply auto-selection criteria (see original criteria below)
- Flag the finding as `needs_review` 
- Do NOT apply the fix autonomously
- Log: `⚠️ No pre-validated version found for {affected_package}. Manual review required.`

### Step V3: Confirm selection before proceeding

**Version source depends on the JDK version gate:**
- **JDK ≤ 8 repos** (or unknown JDK): All versions come from the pre-validated config (`safe-versions.json`). If a package is not in the config, it is marked for manual review.
- **JDK ≥ 9 repos**: Versions come from the Wiz report's `fixedVersion` field directly. If Wiz provides no fix version, falls back to `safe-versions.json`.

The `version_source` field in the output records which path was used: `"config_validated"` or `"wiz_recommended"`.

The selection criteria below are preserved for reference when updating the config:

| Priority | Criterion | Rationale |
|----------|-----------|-----------|
| 1 | Remediates ALL listed CVEs | Non-negotiable — partial fixes are rejected |
| 2 | Minimal version jump from current | Reduces risk of breaking API changes |
| 3 | Same major version as current (x.Y.Z) | Maximizes backward compatibility |
| 4 | Actively maintained / not EOL | Avoids selecting a version that itself has known CVEs |
| 5 | Widely adopted stable release | Not a release candidate or milestone build |

**Pre-validated safe baselines (from `safe-versions.json`):**

| Library (group:artifact) | Vulnerable ≤ | Safe baseline | Notes |
|--------------------------|-------------|---------------|-------|
| `log4j:log4j` (1.x) | 1.2.17 | Replace with `ch.qos.reload4j:reload4j:1.2.26` (primary) OR migrate to `org.apache.logging.log4j:log4j-core:2.17.2` + `log4j-api:2.17.2` (if Log4j 2.x APIs needed) | 1.x is EOL. reload4j is the drop-in replacement (API-compatible, no code changes); Log4j 2.x requires bridge if legacy imports exist. See reload4j strategy in Language-Specific Examples. |
| `org.apache.logging.log4j:log4j-core` (2.x) | 2.14.1 | 2.17.2 | CVE-2021-44228 (Log4Shell) |
| `org.apache.struts:struts2-core` | 2.5.29 | 2.5.33 | CVE-2023-50164 |
| `org.springframework:spring-webmvc` | 5.3.26 | 5.3.39 | Spring4Shell family |
| `commons-text:commons-text` | 1.9 | 1.10.0 | CVE-2022-42889 (Text4Shell) |
| `com.fasterxml.jackson.core:jackson-databind` | 2.15.2 | 2.19.4 (or latest 2.x) | Deserialization gadgets. Force all three jackson-core artifacts to the same version. If fixing a static scanner finding, use `resolutionStrategy { force }` rather than `useVersion`/`constraints` — see Jackson example. |
| `io.netty:netty-codec` | 4.1.85 | 4.1.94.Final | HTTP request smuggling |
| `org.yaml:snakeyaml` | 1.32 | 2.0 | Unsafe deserialization |
| `org.glassfish.jersey.core:jersey-common` | 2.41 | 2.42 | In-place upgrade; apply same version to all `org.glassfish.jersey.*` artifacts |

> **Important:** These baselines are provided as guidance only. Always verify the exact fixed version against the reported CVE IDs before applying. If the library is not in this table, describe the auto-selection criteria applied and state the chosen version explicitly.

**Log: config-validated version:**
```
✅ Config-validated version: {safe_version}
   Source            : {config_validated}
   Nexus status      : {nexus_confirmed from config}
   CVEs patched      : {cves_patched from config}
   Tested in projects: {tested_projects from config}
```

### Step V4: Confirm selection before proceeding

Always output a version summary before touching any file:

```
📋 Version Summary
─────────────────────────────────────────────
Vulnerable package   : {affected_package}:{current_version}
Safe replacement     : {safe_version}
Version source       : CONFIG-VALIDATED | WIZ-RECOMMENDED
Nexus confirmed      : YES | NO | UNCONFIRMED
CVEs addressed       : {cve_ids}
─────────────────────────────────────────────
Proceeding with build file changes...
```

---

## Steps

1. **Read the build file and detect version management pattern.**
   - Use `Read` to open the file at `vulnerability.file_path`.
   - Detect which version management pattern is in use (apply checks in this order):

   **Gradle — ext block (highest priority):**
   ```
   Grep for: ext\s*\{
   Look for: <artifactName>Version\s*=\s*'...' or versions\s*=\s*\[
   ```
   **Gradle — gradle.properties:**
   ```
   Read: {repo_root}/gradle.properties
   Look for: <artifactName>.version= or <artifactName>Version=
   ```
   **Gradle — version catalog:**
   ```
   Read: {repo_root}/gradle/libs.versions.toml
   Look for: [versions] section entries
   ```
   **Maven — properties block:**
   ```
   Grep pom.xml for: <properties> ... <{artifactName}.version>
   ```
   **Direct declaration (fallback):**
   ```
   Grep for: group:artifact:version literal in build.gradle or <version> in pom.xml
   ```

   **Gradle — existing resolutionStrategy block:**
   ```
   Grep for: resolutionStrategy\.eachDependency
   Look for: details\.requested\.group == '{group}' && details\.requested\.name == '{artifact}'
   If found → record as version_management_style = resolution_strategy_existing; update in place rather than adding a new block.
   ```

   Record the detected pattern as `version_management_style`.

2. **Identify all declarations of the vulnerable package.**
   - Use `Grep` to search the entire `repo_root` for the vulnerable group/artifact:
     - Gradle: `grep -r "{group}:{artifact}" .`
     - Maven: `grep -r "<artifactId>{artifact}</artifactId>" .`
     - npm: `grep -r '"{package_name}"' package.json`
   - Identify every location: direct `implementation`/`runtimeOnly`/`compile` declarations, `force = true` pins, `resolutionStrategy` overrides.
   - For multi-module Gradle projects, check both root and subproject `build.gradle` files.

   **Classify each found declaration:**
   - `direct_versioned`: `implementation "group:artifact:version"` — version is explicit in the declaration itself
   - `forced_pin`: `implementation("group:artifact:version") { force = true }` — version is explicit AND forced
   - `transitive_only`: not declared, only appears in dependency tree output — version not in build file at all

   Record the classification as `declaration_type`. This determines which fix strategy produces a scanner-visible result.

3. **Check for transitive introduction (if package is not declared directly).**
   - If `Grep` finds no direct declaration, the package is transitively pulled in.
   - Use `Bash` to run the dependency tree (read-only):
     - Gradle: `./gradlew dependencies --configuration runtimeClasspath 2>/dev/null | grep "{artifact}"`
     - Maven: `mvn dependency:tree -Dincludes={group}:{artifact} 2>/dev/null`
   - Identify the parent dependency that pulls in the vulnerable package.
   - Record as `transitive_via`.

4. **Apply the fix using the detected version management style.**

   **Strategy selection — pick exactly ONE:**

   | Scenario | Declaration type | Correct strategy | Scanner sees explicit version? |
   |---|---|---|---|
   | Same artifact, update declared version | `direct_versioned` | Update version literal in-place (ext_block / gradle_properties / version_catalog / direct) | YES |
   | Forced pin being upgraded | `forced_pin` | Replace `{ force = true }` declaration with `resolutionStrategy { force "group:artifact:safe_version" }` in the same `configurations.all` block | YES |
   | Transitive only, no declaration | `transitive_only` | `resolutionStrategy.eachDependency { useVersion }` OR `constraints` | NO — acceptable only when the scanner does not flag it |
   | EOL library → different artifact | any | `configurations.all { exclude }` + new `implementation` declaration | YES (new explicit declaration) |

   ### Gradle — Update ext block property
   If `version_management_style` is `ext_block`:
   - Use `Edit` to update the version property value in the ext block.
   - If the library is being migrated to a different group (e.g., Log4j 1.x → 2.x), also update the group/artifact reference in the dependency declaration.

   ### Gradle — Update gradle.properties
   If `version_management_style` is `gradle_properties`:
   - Use `Edit` to update the version value in `gradle.properties`.

   ### Gradle — Update version catalog
   If `version_management_style` is `version_catalog`:
   - Use `Edit` to update the version entry in `gradle/libs.versions.toml`.

   ### Gradle — Add resolutionStrategy (for transitive in-place upgrade, same group:artifact)
   Use this when the package stays the same group:artifact but needs a higher safe version (e.g., `commons-text:1.9` → `1.10.0`). Do NOT combine with `exclude` — these are mutually exclusive strategies.
   ```groovy
   configurations.all {
       resolutionStrategy.eachDependency { details ->
           if (details.requested.group == '{group}' &&
               details.requested.name == '{artifact}') {
               details.useVersion '{safe_version}'
               details.because '{cve_ids joined by ", "}'
           }
       }
   }
   ```
   For multi-module projects, wrap in `allprojects { }`.

   ### Gradle — Add global exclusion (for EOL library replacement with a different artifact)
   Use this when the vulnerable library is being replaced by a completely different group:artifact (e.g., `log4j:log4j` → `org.apache.logging.log4j:log4j-core`). Add the exclusion to block the old library, then declare the replacement in `dependencies {}` (Step 6). Do NOT combine with `useVersion` / `useTarget` — `exclude` prevents the dependency from resolving at all, so a redirect would never apply.
   ```groovy
   configurations.all {
       exclude group: '{group}', module: '{artifact}'
   }
   ```
   For multi-module projects, wrap in `allprojects { }`.

   ### Gradle — Add dependency constraints (modern Gradle 5.0+, alternative to resolutionStrategy)
   ```groovy
   dependencies {
       constraints {
           implementation('{group}:{artifact}:{safe_version}') {
               because '{cve_ids joined by ", "}'
           }
       }
   }
   ```

   ### Maven — Update properties and add exclusions
   Update `<properties>`:
   ```xml
   <{artifactName}.version>{safe_version}</{artifactName}.version>
   ```
   Add global exclusion in `<dependencyManagement>` if replacing with a different artifact:
   ```xml
   <dependency>
       <groupId>{group}</groupId>
       <artifactId>{artifact}</artifactId>
       <version>{safe_version}</version>
   </dependency>
   ```

   ### npm — Update package.json
   Use `Edit` to update the version constraint in `dependencies` or `devDependencies`. If the package must be replaced, remove the old entry and add the replacement.

5. **Handle forced declarations of the vulnerable package (Gradle).**

   First check whether the project uses a static SAST scanner (Wiz CLI, SonarQube, Checkmarx, or similar). If the vulnerability finding came from a static scanner report (i.e., `wiz_report_path` was provided), scanner-visibility rules apply:

   - If declaration type is `forced_pin`: Do NOT simply remove `{ force = true }`. Removing it while leaving the old version declared, or relying on the BOM, leaves the old version string in the file — the scanner will continue to flag it. Instead:
     1. Remove the `implementation("group:artifact:old_version") { force = true }` line entirely.
     2. Add a `resolutionStrategy { force "group:artifact:safe_version" }` block (or add to existing `resolutionStrategy` block). This writes the safe version explicitly in the config — visible to the static scanner.
     ```groovy
     configurations.all {
         resolutionStrategy {
             force 'com.fasterxml.jackson.core:jackson-databind:{safe_version}'
             force 'com.fasterxml.jackson.core:jackson-core:{safe_version}'
             force 'com.fasterxml.jackson.core:jackson-annotations:{safe_version}'
         }
     }
     ```
     Note: For jackson-databind, also force `jackson-core` and `jackson-annotations` to the same version — they are a coordinated artifact family and mismatched versions cause runtime errors.

   - If the fix does NOT come from a static scanner (threat model only, or project has no static scanner), `force = true` removal without replacement is acceptable — the BOM or dependency resolution will provide the safe version at runtime.

   In both cases: Forced pins of the vulnerable version MUST NOT remain in the file, as they would override the fix.

6. **Add the replacement library (only if migrating to a different artifact).**
   This step applies when the vulnerable library is EOL and must be replaced by a different group/artifact.

   **Option A (recommended for log4j 1.x EOL): reload4j drop-in replacement**
   - See "Gradle — Log4j 1.x → reload4j" example in Language-Specific Examples section.
   - Use when: project uses log4j 1.x APIs directly and no Log4j 2.x-specific features are needed.
   - Advantage: No code changes; PatternLayout subclasses like PatternLayoutIBank continue to work.

   **Option B: Log4j 2.x migration**
   - Use when: project requires Log4j 2.x-specific capabilities.
   - Requires compatibility bridge check (Step 7).

   **Gradle example (Log4j 1.x → 2.x migration):**
   ```groovy
   // Add Log4j 2 core and API
   implementation "org.apache.logging.log4j:log4j-core:{safe_version}"
   implementation "org.apache.logging.log4j:log4j-api:{safe_version}"

   // Add backward-compatibility bridge only if legacy org.apache.log4j.* imports exist in src/
   // (check in Step 7 before adding this line)
   implementation "org.apache.logging.log4j:log4j-1.2-api:{safe_version}"
   ```

   **Maven example:**
   ```xml
   <dependency>
       <groupId>org.apache.logging.log4j</groupId>
       <artifactId>log4j-core</artifactId>
       <version>{safe_version}</version>
   </dependency>
   <dependency>
       <groupId>org.apache.logging.log4j</groupId>
       <artifactId>log4j-api</artifactId>
       <version>{safe_version}</version>
   </dependency>
   ```

7. **Check for legacy API usage and SLF4J binding before adding compatibility bridges.**

   There are two independent checks — run both:

   **Check A: Direct Log4j 1.x API usage in source code**
   - Use `Grep` to search `src/` for direct Log4j 1.x imports:
     ```bash
     grep -r "import org.apache.log4j\." src/
     grep -r "import org.apache.commons.logging\." src/
     ```
   - If found → add `log4j-1.2-api` bridge (re-implements the Log4j 1.x API on top of Log4j 2.x):
     ```groovy
     implementation "org.apache.logging.log4j:log4j-1.2-api:${log4j2Version}"
     ```
   - If not found → do NOT add `log4j-1.2-api`. Unnecessary bridges expand the attack surface.

   **Check B: SLF4J → Log4j 1.x binding in build files**
   - Use `Grep` to search build files for the `slf4j-log4j12` binding:
     ```bash
     grep -r "slf4j-log4j12" .
     ```
   - This binding wires SLF4J to Log4j 1.x as its backend. When Log4j 1.x is excluded, `slf4j-log4j12` loses its backend and causes `NoClassDefFoundError` at runtime even though the build compiles cleanly.
   - If found → remove `slf4j-log4j12` and replace it with the SLF4J → Log4j 2.x binding:
     ```groovy
     // REMOVE:
     // implementation "org.slf4j:slf4j-log4j12:{version}"

     // ADD in its place:
     implementation "org.apache.logging.log4j:log4j-slf4j-impl:${log4j2Version}"
     ```
   - If not found → no SLF4J binding change is needed.

   > **Why these are different:** `log4j-1.2-api` is for source code that calls `org.apache.log4j.*` directly. `log4j-slf4j-impl` is for build configs that routed SLF4J through Log4j 1.x as a backend. A project can need both, either, or neither — always check before adding.

8. **Verify no remaining references to the vulnerable version.**
   - Use `Grep` to confirm the vulnerable group:artifact no longer appears at the old version:
     ```bash
     grep -r "{group}:{artifact}:{current_version}" .
     grep -r "{group}:{artifact}" . | grep -v "{safe_version}"
     ```
   - For Gradle: run a dependency check (read-only):
     ```bash
     ./gradlew dependencies --configuration runtimeClasspath 2>/dev/null | grep "{artifact}"
     ```
   - Confirm the output shows `{safe_version}`, not `{current_version}`.

9. **Scan for similar vulnerable declarations across the project.**
   - Use `Grep` to search all `build.gradle`, `pom.xml`, and `package.json` files for other packages from the same CVE family (e.g., other Log4j 1.x artifacts: `log4j-extra`, `apache-log4j-extras`).
   - Report any additional vulnerable declarations found, even if not in scope for this fix.

10. **Assemble the output.**
    - Compose the output JSON as specified in the Output Format section.

## Language-Specific Examples

### Gradle — Log4j 1.x → reload4j (drop-in replacement, recommended)

**Approach:** Replace log4j 1.2.17 with reload4j 1.2.26 (100% API-compatible, no code changes required).

**Tested in:** coreMortgages, Mortgages, FeatureStore2 (production Barclays mini-apps).

**Before (vulnerable):**
```groovy
// build.gradle
ext {
    log4jVersion = '1.2.17'
}

dependencies {
    implementation ("log4j:log4j:${log4jVersion}") { force = true }
    runtimeOnly ("log4j:log4j:${log4jVersion}") { force = true }
    
    // SLF4J binding to Log4j 1.x
    implementation "org.slf4j:slf4j-log4j12:1.7.36"
}
```

**After (fixed — CVE-2019-17571, CVE-2021-4104, CVE-2022-23302):**
```groovy
// build.gradle
ext {
    reload4jVersion = '1.2.26'
}

// Exclude competing SLF4J implementations — retain only slf4j-log4j12 bridge.
// reload4j provides the backend for slf4j-log4j12.
configurations.all {
    exclude group: 'log4j', module: 'log4j'
    all*.exclude group: 'ch.qos.logback', module: 'logback-classic'
    all*.exclude group: 'org.slf4j', module: 'slf4j-simple'
    all*.exclude group: 'org.slf4j', module: 'slf4j-nop'
    all*.exclude group: 'org.slf4j', module: 'slf4j-jdk14'
    all*.exclude group: 'com.barclays.ROLB_LIBS.libs.slf4j', module: 'slf4j-log4j12'
}

dependencies {
    // Drop-in replacement — 100% API-compatible with log4j 1.2.17
    implementation "ch.qos.reload4j:reload4j:${reload4jVersion}"

    // Retain the SLF4J → log4j 1.x bridge (reload4j provides the backend)
    implementation "org.slf4j:slf4j-log4j12:1.7.36"
}
```

**Why reload4j:**
- 100% API-compatible with log4j 1.2.17 — no source code changes required
- PatternLayout subclass support preserved (PatternLayoutIBank continues to work unchanged)
- Backports CVE-2019-17571, CVE-2021-4104, CVE-2022-23302 security patches
- Structured logging preserved — PerThreadService + custom pattern tokens work unchanged
- Community-maintained fork of log4j 1.2.x with ongoing security support

**When to use reload4j:** Default choice for any project using log4j 1.x APIs or dependencies. No code changes needed.

**When to use Log4j 2.x instead:** Only if the project requires Log4j 2.x-specific capabilities (e.g., `LogManager.getLogger()` with async appenders, context propagation, Log4j 2.x MDC). For pure log4j 1.x compatibility, reload4j is strongly preferred.

---

### Gradle — Log4j 1.x → 2.x (EOL library replacement)

**Before (vulnerable):**
```groovy
// build.gradle
ext {
    log4jVersion = '1.2.17'
}

dependencies {
    implementation ("log4j:log4j:${log4jVersion}") { force = true }
    runtimeOnly ("log4j:log4j:${log4jVersion}") { force = true }
}
```

**After (fixed — CVE-2022-23302, CVE-2022-23305, CVE-2022-23307):**
```groovy
// build.gradle
ext {
    log4j2Version = '2.17.2'  // replaces EOL log4j 1.x
}

// Exclude Log4j 1.x globally — blocks both direct and transitive pulls.
// Do NOT combine with resolutionStrategy.eachDependency/useVersion here:
// exclude prevents the artifact from resolving, so any redirect would never apply.
configurations.all {
    exclude group: 'log4j', module: 'log4j'
}

dependencies {
    // Log4j 2.x replacements — both log4j-core and log4j-api are required.
    // log4j-core provides the implementation; log4j-api provides the public API surface.
    implementation "org.apache.logging.log4j:log4j-core:${log4j2Version}"
    implementation "org.apache.logging.log4j:log4j-api:${log4j2Version}"

    // --- Compatibility bridges (add only what applies after running Step 7 checks) ---

    // Check A: src/ contains "import org.apache.log4j.*" → add this:
    // implementation "org.apache.logging.log4j:log4j-1.2-api:${log4j2Version}"

    // Check B: build file previously declared "org.slf4j:slf4j-log4j12" → replace it with this:
    // implementation "org.apache.logging.log4j:log4j-slf4j-impl:${log4j2Version}"
    // (slf4j-log4j12 routes SLF4J through Log4j 1.x; without Log4j 1.x it causes
    //  NoClassDefFoundError at runtime even though the build compiles cleanly)
}
```

**What changed:**
- Removed: forced `log4j:log4j:1.2.17` `implementation` and `runtimeOnly` declarations
- Removed: `org.slf4j:slf4j-log4j12` if present — its Log4j 1.x backend no longer exists
- Added: `configurations.all { exclude }` block to block `log4j:log4j` globally (direct + transitive)
- Added: `log4j-core` **and** `log4j-api` 2.17.2 as explicit replacements — both are required for Log4j 2.x to function
- Commented bridges: enable `log4j-1.2-api` if direct Log4j 1.x imports exist; enable `log4j-slf4j-impl` if `slf4j-log4j12` was present

---

### Gradle — In-place version upgrade (same artifact, new safe version)

**Before (vulnerable — e.g., commons-text 1.9, CVE-2022-42889):**
```groovy
ext {
    commonsTextVersion = '1.9'
}
dependencies {
    implementation "org.apache.commons:commons-text:${commonsTextVersion}"
}
```

**After (fixed):**
```groovy
ext {
    commonsTextVersion = '1.10.0'  // CVE-2022-42889 (Text4Shell)
}
dependencies {
    implementation "org.apache.commons:commons-text:${commonsTextVersion}"
}
```

---

### Gradle — Jackson forced-pin upgrade (scanner-visible fix)

**Scenario:** Jackson was forced to a vulnerable version to suppress a transitive pull of a newer (incompatible) version. A Wiz static scan continues to flag the forced-pinned version in the build file, even though Gradle's runtime resolution works correctly with a BOM. The fix must make the safe version explicitly visible to the static scanner.

**Before (vulnerable — forced pin visible to static scanner):**
```groovy
ext {
    jacksonVersion = '2.15.2'
}

dependencies {
    implementation ("com.fasterxml.jackson.core:jackson-databind:${jacksonVersion}") { force = true }
    implementation ("com.fasterxml.jackson.core:jackson-core:${jacksonVersion}") { force = true }
    implementation ("com.fasterxml.jackson.core:jackson-annotations:${jacksonVersion}") { force = true }
}
```

**After (fixed — CVE-2022-42003, CVE-2022-42004 — safe version explicit and scanner-visible):**
```groovy
// Remove forced declarations from dependencies {} — they pinned the vulnerable version.
// Use resolutionStrategy.force instead: this writes the safe version explicitly in the
// build file so static scanners (Wiz CLI) can see it, unlike useVersion or constraints.
configurations.all {
    resolutionStrategy {
        force 'com.fasterxml.jackson.core:jackson-databind:2.19.4'
        force 'com.fasterxml.jackson.core:jackson-core:2.19.4'
        force 'com.fasterxml.jackson.core:jackson-annotations:2.19.4'
    }
}

dependencies {
    // Retain implementation declarations without the version pin —
    // the resolutionStrategy.force above governs the resolved version.
    implementation "com.fasterxml.jackson.core:jackson-databind"
    implementation "com.fasterxml.jackson.core:jackson-core"
    implementation "com.fasterxml.jackson.core:jackson-annotations"
}
```

**Why resolutionStrategy.force instead of useVersion:**
- `resolutionStrategy.force "group:artifact:version"` writes the target version literally into the build file — Wiz CLI's static scan reads this and sees the safe version.
- `resolutionStrategy.eachDependency { useVersion }` and `dependencies { constraints {} }` are evaluated at Gradle resolution time — they do not produce a readable version string in the file, so static scanners continue to report the originally-declared (vulnerable) version.

---

### Maven — Dependency management upgrade

**Before (vulnerable):**
```xml
<properties>
    <log4j.version>1.2.17</log4j.version>
</properties>
<dependencies>
    <dependency>
        <groupId>log4j</groupId>
        <artifactId>log4j</artifactId>
        <version>${log4j.version}</version>
    </dependency>
</dependencies>
```

**After (fixed):**
```xml
<properties>
    <log4j2.version>2.17.2</log4j2.version>
</properties>

<!-- Option A: If log4j is pulled transitively, exclude it from the consuming dependency -->
<dependency>
    <groupId><!-- the parent lib that pulls log4j --></groupId>
    <artifactId><!-- parent artifact --></artifactId>
    <version>...</version>
    <exclusions>
        <exclusion>
            <groupId>log4j</groupId>
            <artifactId>log4j</artifactId>
        </exclusion>
    </exclusions>
</dependency>

<!-- Option B: Use dependencyManagement to pin reload4j as the replacement -->
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>ch.qos.reload4j</groupId>
            <artifactId>reload4j</artifactId>
            <version>1.2.26</version>
        </dependency>
    </dependencies>
</dependencyManagement>

<!-- Add replacements to dependencies -->
<dependencies>
    <!-- If using reload4j (Option B): -->
    <dependency>
        <groupId>ch.qos.reload4j</groupId>
        <artifactId>reload4j</artifactId>
    </dependency>

    <!-- OR if migrating to Log4j 2.x (Option A + new backend): -->
    <dependency>
        <groupId>org.apache.logging.log4j</groupId>
        <artifactId>log4j-core</artifactId>
        <version>${log4j2.version}</version>
    </dependency>
    <dependency>
        <groupId>org.apache.logging.log4j</groupId>
        <artifactId>log4j-api</artifactId>
        <version>${log4j2.version}</version>
    </dependency>
</dependencies>
```

> **Note:** The `99-empty` version trick (using a phantom version higher than any real version) is not a Maven standard and may fail with stricter resolvers. Use `<exclusions>` in the consuming dependency or `<dependencyManagement>` with the replacement artifact instead.

---

### npm — Package upgrade

**Before (vulnerable — e.g., lodash < 4.17.21, CVE-2021-23337):**
```json
{
  "dependencies": {
    "lodash": "^4.17.19"
  }
}
```

**After (fixed):**
```json
{
  "dependencies": {
    "lodash": "^4.17.21"
  }
}
```

## Output Format

Return a JSON object:

```json
{
  "status": "fixed | partial | needs_review | failed",
  "file_path": "<string: path to the primary modified build file>",
  "affected_package": "<string: group:artifact or package name>",
  "vulnerable_version": "<string: the version that was removed>",
  "safe_version": "<string: the version applied>",
  "version_source": "config_validated | wiz_recommended",
  "nexus_confirmed": "<boolean>",
  "version_management_style": "ext_block | gradle_properties | version_catalog | pom_properties | direct_declaration",
  "migration_type": "in_place_upgrade | library_replacement | transitive_override",
  "changes": [
    {
      "file_path": "<string: path to modified file>",
      "description": "<string: what was changed and why>",
      "before": "<string: the original line(s)>",
      "after": "<string: the replacement line(s)>"
    }
  ],
  "bridge_added": "<boolean: whether a compatibility bridge was added>",
  "bridge_reason": "<string or null: why the bridge was added>",
  "legacy_imports_found": ["<string: file paths with legacy API imports>"],
  "similar_vulnerabilities_found": [
    {
      "file_path": "<string>",
      "declaration": "<string: the vulnerable line found>",
      "note": "<string: recommendation>"
    }
  ],
  "nexus_warning": "<string or null: populated when nexus_confirmed is false>",
  "scanner_visible_fix": "<boolean: true if the applied fix writes an explicit version string readable by static file scanners; false if it relies on runtime resolution only>",
  "warnings": ["<string: any additional caveats>"],
  "error": "<string or null: error description if status is failed>"
}
```

### Success Indicator

`status` is `"fixed"` and `changes` is non-empty. The vulnerable version is no longer present in the build file.

### Failure Indicator

`status` is `"failed"` with a description in `error`. No build file has been modified.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **Build file not found at `file_path`** | Return `{"status": "failed", "error": "Build file not found: <path>"}`. Do not attempt to create it. |
| **Vulnerable version not found in build file** | Use `Grep` to search the full `repo_root`. If found elsewhere, update `file_path` and proceed. If not found at all, set `status: "needs_review"` with a warning that the package may be pulled only transitively. |
| **Multi-module Gradle project** | Apply `resolutionStrategy` inside `allprojects { }` in the root `build.gradle` to ensure all submodules are covered. |
| **No safe version confirmed and library not in known-safe-baselines table** | Set `status: "needs_review"`. Do NOT apply a version change. Output: `"error": "Cannot auto-select safe version for {package} — CVEs {cve_ids} require manual version verification."` |
| **Version catalog (libs.versions.toml) present** | Prefer updating the catalog over adding a resolutionStrategy override. Both patterns in the same project conflict. |
| **Nexus availability unconfirmed** | Proceed with the fix but set `nexus_warning: "Version {safe_version} has not been confirmed in the internal Nexus repository. Verify availability before merging."` |
| **Legacy imports found after bridge removal** | Re-add the compatibility bridge. Set `bridge_added: true` and list the legacy import files. |
| **Gradle dependency tree command unavailable** | Skip Step 8 verification. Add a warning: `"Could not run ./gradlew dependencies — manual verification recommended."` |
| **Maven wrapper not present** | Use `mvn` directly. If neither is available, skip dependency tree verification and warn. |

## Constraints

- **Version confirmation first**: NEVER modify any build file before completing the Pre-Flight version validation (Steps V1–V4). This is mandatory.
- **Nexus transparency**: Always surface Nexus confirmation status in the output. Never silently proceed without flagging an unconfirmed version.
- **Minimal diff**: Modify only the build configuration relevant to the vulnerable package. Do not upgrade unrelated dependencies or restructure the build file.
- **No source code changes**: This skill modifies only build files (`build.gradle`, `gradle.properties`, `libs.versions.toml`, `pom.xml`, `package.json`). It does NOT modify `.java`, `.kt`, `.py`, `.js`, or other source files (except to grep them for legacy imports).
- **Preserve existing version management style**: If the project uses an ext block for versions, update the ext block. Do not introduce a different pattern (e.g., gradle.properties) if one already exists.
- **Bridge only when needed**: Do not add compatibility bridges (log4j-1.2-api, SLF4J adapters) unless legacy imports are confirmed by Grep. Unnecessary bridges expand the attack surface.
- **No forced versions without documentation**: Do not use `force = true` without a `because` clause documenting the CVE rationale.
- **No network calls**: Do not attempt to resolve versions from Maven Central, npm registry, or Nexus. Version selection is based on user input or the known-safe-baselines table.
- **Tool usage**: Use `Read` for file inspection, `Grep` for pattern searching, `Glob` for multi-file discovery, `Edit` for applying changes, `Bash` only for read-only dependency tree commands (`./gradlew dependencies`, `mvn dependency:tree`).
