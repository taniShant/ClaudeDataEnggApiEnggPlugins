# Phase 0 Validation Checklist

Post-Phase 0 verification checks. Run after Phase 0 commit to confirm all documented procedures were executed.

## Checks

### Check 1: Repository Deduplication

**What**: Repository declarations in build.gradle were deduplicated.

**How to verify**:
```bash
REPO_COUNT=$(grep -c "maven {" build.gradle 2>/dev/null || echo "0")
if [ "$REPO_COUNT" -gt 8 ]; then
  echo "FAIL: Repository count is $REPO_COUNT (expected ≤8 after deduplication)"
else
  echo "PASS: Repository count is $REPO_COUNT"
fi
```

**On failure**: Agent must re-apply repository deduplication using Read/Grep/Edit tools, then amend the Phase 0 commit.

### Check 2: No Public Repositories

**What**: All public repository declarations (mavenCentral, gradlePluginPortal, etc.) have been removed.

**How to verify**:
```bash
if grep -qE "mavenCentral\(\)|gradlePluginPortal\(\)|repo\.maven\.apache|services\.gradle\.org" build.gradle 2>/dev/null; then
  echo "FAIL: Public repository declarations still present"
else
  echo "PASS: No public repositories found"
fi
```

**On failure**: Agent must use Edit tool to remove or replace public repository declarations with Barclays Nexus URLs.

### Check 3: distributionUrl Base Path Normalized

**What**: The Gradle wrapper distributionUrl base path has been normalized to Barclays Nexus flat-path format. The Gradle version is NOT checked here — version upgrade to 8.5+ is Phase 1's responsibility.

**How to verify**:
```bash
DIST_URL=$(grep "distributionUrl" gradle/wrapper/gradle-wrapper.properties 2>/dev/null)
if echo "$DIST_URL" | grep -qE "nexus.*barcapint.*content/groups/barclays/gradle-[0-9]"; then
  echo "PASS: distributionUrl base path normalized (Nexus flat path)"
else
  echo "FAIL: distributionUrl base path not normalized. Current: $DIST_URL"
fi
```

**On failure**: Agent must extract the current Gradle version from the existing distributionUrl and replace only the base URL path with `https\://nexus.barcapint.com/nexus/content/groups/barclays/` while preserving the version number.

### Check 4: Truststore/Keystore Commented Out

**What**: Custom SSL truststore/keystore entries in gradle.properties are commented out (if they existed).

**How to verify**:
```bash
if grep -qE "^[^#]*javax\.net\.ssl\.(trust|key)Store" gradle.properties 2>/dev/null; then
  echo "FAIL: Uncommented truststore/keystore entries in gradle.properties"
else
  echo "PASS: Truststore/keystore entries handled"
fi
```

**On failure**: Agent must use Edit tool to comment out (add `#` prefix) all truststore/keystore lines.

### Check 5: dependencies.gradle Consolidated (CRITICAL for Phase 1)

**What**: If dependencies.gradle (or other external dependency files) existed, they must be consolidated into build.gradle and deleted.

**How to verify**:
```bash
# Check if any external dependency files still exist and are applied
if grep -qE "apply from.*['\"].*(dependencies|libs)\.gradle['\"]" build.gradle 2>/dev/null; then
  echo "FAIL: External dependency file still applied in build.gradle"
elif [ -f "dependencies.gradle" ] || [ -f "gradle/dependencies.gradle" ] || [ -f "libs.gradle" ]; then
  echo "FAIL: External dependency file still exists (not deleted after consolidation)"
else
  echo "PASS: No external dependency files remain"
fi
```

**On failure**: Agent must:
1. Re-read external dependency file
2. Merge dependencies into build.gradle top-level dependencies { } block
3. Remove "apply from" statement
4. Delete external file if blank
5. Verify dependency tree unchanged (diff before/after)

**Why this matters**: Phase 1 needs to add platform BOM as the FIRST dependency in the dependencies block. This is only possible if all dependencies are consolidated in build.gradle.

### Check 6: Cache Resolution Strategy Present

**What**: `configurations.all` block with `resolutionStrategy.cacheChangingModulesFor 0` and `resolutionStrategy.cacheDynamicVersionsFor 0` must be present in build.gradle.

**How to verify**:
```bash
if grep -q "cacheChangingModulesFor" build.gradle 2>/dev/null && grep -q "cacheDynamicVersionsFor" build.gradle 2>/dev/null; then
  echo "PASS: Cache resolution strategy present"
else
  echo "FAIL: Cache resolution strategy missing — dynamic versions may resolve stale artifacts"
fi
```

**On failure**: Agent must add the following block to build.gradle (after plugins/buildscript, before dependencies):
```gradle
configurations.all {
    resolutionStrategy.cacheChangingModulesFor 0, 'seconds'
    resolutionStrategy.cacheDynamicVersionsFor 0, 'seconds'
}
```

See [common.md](common.md) for auto-fix behavior and integration details.

**Phase 0 specifics:** The validation agent covers these checks via red flags 5, 11, 14.

---

## EAR to WAR Checks (MCA1 only, run if `ear_to_war_converted = true`)

Skip this section if `migration_type != mca1` or if state file shows `ear_to_war_converted = false`.

### Check 7: war/ Directory Removed

**What**: The `war/` submodule directory no longer exists at project root after conversion.

**How to verify**:
```bash
if [ -d "war" ]; then
  echo "FAIL: war/ directory still exists — EAR→WAR conversion may be incomplete"
else
  echo "PASS: war/ directory removed"
fi
```

**On failure**: HARD FAIL — conversion did not complete. Re-run skill Phase 3 Step 2 (restructure project files).

### Check 8: settings.gradle Single-Line

**What**: `settings.gradle` contains only the `rootProject.name` declaration (no `include` lines remain).

**How to verify**:
```bash
if grep -qE "^include " settings.gradle 2>/dev/null; then
  echo "FAIL: settings.gradle still contains include lines"
elif grep -q "rootProject.name" settings.gradle 2>/dev/null; then
  echo "PASS: settings.gradle is single rootProject.name declaration"
else
  echo "WARN: settings.gradle has unexpected content"
fi
```

**On failure**: Use Edit tool to remove all `include` lines from `settings.gradle`.

### Check 9: Root Build Backup Exists

**What**: `backup/root-build.gradle.backup` was created in skill Phase 2 (pre-conversion backup).

**How to verify**:
```bash
if [ -f "backup/root-build.gradle.backup" ]; then
  echo "PASS: Root build.gradle backup exists"
else
  echo "WARN: backup/root-build.gradle.backup missing — backup may not have been created"
fi
```

**On failure**: WARN only — backup is evidence of correct procedure, not a functional requirement.

### Check 10: War Backup Exists

**What**: `backup/war-backup/` directory was created in skill Phase 2.

**How to verify**:
```bash
if [ -d "backup/war-backup" ]; then
  echo "PASS: war-backup directory exists"
else
  echo "WARN: backup/war-backup/ missing — war submodule backup may not have been created"
fi
```

**On failure**: WARN only.

### Check 11: No EAR Plugin in build.gradle

**What**: The merged root `build.gradle` does not apply the `ear` plugin.

**How to verify**:
```bash
if grep -qE "apply plugin: ['\"]ear['\"]|id ['\"]ear['\"]" build.gradle 2>/dev/null; then
  echo "FAIL: EAR plugin still applied in build.gradle"
else
  echo "PASS: No EAR plugin in build.gradle"
fi
```

**On failure**: HARD FAIL — use Edit tool to remove the `apply plugin: 'ear'` (or equivalent) line from `build.gradle`.

### Check 12: Eclipse IDE Artefacts Removed

**What**: Eclipse-specific files (`.classpath`, `.project`, `.settings/`, `bin/`) have been removed from the project root.

**How to verify**:
```bash
ECLIPSE_FOUND=false
[ -f ".classpath" ] && echo "FAIL: .classpath still present" && ECLIPSE_FOUND=true
[ -f ".project" ] && echo "FAIL: .project still present" && ECLIPSE_FOUND=true
[ -d ".settings" ] && echo "FAIL: .settings/ still present" && ECLIPSE_FOUND=true
[ -d "bin" ] && echo "FAIL: bin/ still present (Eclipse compiled output)" && ECLIPSE_FOUND=true
[ "$ECLIPSE_FOUND" = false ] && echo "PASS: No Eclipse IDE artefacts found"
```

**On failure**: Use Bash to delete the artefacts and Edit tool to ensure they are in `.gitignore`.

### Check 13: Functional Test Source Set Configured (if applicable)

**What**: If `src/functional/java/` exists, `build.gradle` must contain a `functional` sourceSets entry and a `functionalTest` task. `Feature/` and `Fixture/` must be inside `src/functional/`, not at project root.

**How to verify**:
```bash
if [ -d "src/functional/java" ]; then
  if grep -q "sourceSets" build.gradle 2>/dev/null && grep -q "functional {" build.gradle 2>/dev/null; then
    echo "PASS: functional sourceSet configured"
  else
    echo "FAIL: src/functional/java exists but no functional sourceSet in build.gradle"
  fi
  if grep -q "functionalTest" build.gradle 2>/dev/null; then
    echo "PASS: functionalTest task present"
  else
    echo "FAIL: functionalTest task missing from build.gradle"
  fi
  [ -d "src/functional/Feature" ] && echo "PASS: Feature/ inside src/functional/" || echo "WARN: Feature/ not found under src/functional/"
  [ -d "src/functional/Fixture" ] && echo "PASS: Fixture/ inside src/functional/" || echo "INFO: No Fixture/ directory (optional)"
  [ -d "Feature" ] && echo "FAIL: Feature/ still at project root — should be moved to src/functional/Feature/"
  [ -d "Fixture" ] && echo "FAIL: Fixture/ still at project root — should be moved to src/functional/Fixture/"
else
  echo "PASS: No functional source set present — skipping"
fi
```

**On failure**: Re-run Step 10 of the EAR→WAR skill (Configure Functional Tests).

### Check 14: GitLab CI Variables Updated (if applicable)

**What**: If `.gitlab-ci-variables.yml` exists, no `war/build/` prefixes should remain in variable values.

**How to verify**:
```bash
if [ -f ".gitlab-ci-variables.yml" ]; then
  if grep -q "war/build/" .gitlab-ci-variables.yml 2>/dev/null; then
    echo "FAIL: .gitlab-ci-variables.yml still contains war/build/ path references"
    grep "war/build/" .gitlab-ci-variables.yml
  else
    echo "PASS: No war/build/ references in .gitlab-ci-variables.yml"
  fi
else
  echo "PASS: No .gitlab-ci-variables.yml present — skipping"
fi
```

**On failure**: Use Edit tool with `replace_all: true` to replace `war/build/` with `build/` in `.gitlab-ci-variables.yml`.
