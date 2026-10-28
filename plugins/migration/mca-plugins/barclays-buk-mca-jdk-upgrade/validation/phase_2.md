# Phase 2 Validation Checklist

Post-Phase 2 verification checks. Run after Phase 2 commit to confirm selective dependency migration and build configuration procedures were executed.

## Checks

### Check 1: MCA Dependencies Updated

**What**: MCA dependencies (com.barclays.global.mca or com.barclays.eps) have been updated to target versions.

**How to verify**:
```bash
# For MCA2: check for 2.2.+ or 2.3.+ versions (or no version if BOM-managed)
# For MCA1: check for 6.2.+ or 6.3.+ versions (or no version if BOM-managed)
if grep -qE "com\.barclays\.(global\.mca|eps):.*:(1\.|0\.|5\.)" build.gradle 2>/dev/null; then
  echo "FAIL: Old MCA dependency versions still present"
else
  echo "PASS: MCA dependencies updated to target versions"
fi
```

**On failure**: Agent must re-run the selective migration skill to update remaining dependencies. Attempt auto-fix by applying version updates via Edit tool.

### Check 2: Deprecated Dependencies Removed

**What**: Deprecated dependencies (Log4j, old IBM MQ, old JDBC drivers) have been removed.

**How to verify**:
```bash
if grep -qE "log4j:log4j|slf4j-log4j12|com\.ibm\.wmq:mqjms|ojdbc14" build.gradle 2>/dev/null; then
  echo "FAIL: Deprecated dependencies still present"
else
  echo "PASS: Deprecated dependencies removed"
fi
```

**On failure**: Agent must use Edit tool to remove deprecated dependency lines.

### Check 3 (HARD GATE): Multi-Part Transformations Complete

**What**: All multi-part transformations must be fully complete before Phase 2 can be marked successful. Multi-part transformations require updating multiple related locations (e.g., plugin artifact + apply plugin statement).

**Transformations to verify**:
1. eps2-war → eps-war (if applicable)
2. dependencies.gradle consolidated (if applicable - should be done in Phase 0)

**How to verify**:
```bash
INCOMPLETE_TRANSFORMATIONS=0

# Check eps2-war transformation
if grep -q "gradle-eps-war-plugin" build.gradle 2>/dev/null; then
  # New plugin present, verify old one is gone
  if grep -q "eps2-war" build.gradle 2>/dev/null; then
    echo "FAIL: Incomplete eps2-war transformation (old pattern still exists)"
    INCOMPLETE_TRANSFORMATIONS=$((INCOMPLETE_TRANSFORMATIONS + 1))
  else
    echo "PASS: eps2-war fully migrated"
  fi
elif grep -q "eps2-war" build.gradle 2>/dev/null; then
  echo "FAIL: eps2-war found but not migrated"
  INCOMPLETE_TRANSFORMATIONS=$((INCOMPLETE_TRANSFORMATIONS + 1))
fi

# Check dependencies.gradle consolidation
if grep -qE "^[^/]*apply from.*dependencies\.gradle" build.gradle 2>/dev/null; then
  echo "FAIL: dependencies.gradle still applied (not consolidated)"
  INCOMPLETE_TRANSFORMATIONS=$((INCOMPLETE_TRANSFORMATIONS + 1))
elif [ -f "dependencies.gradle" ]; then
  echo "FAIL: dependencies.gradle file still exists (not deleted)"
  INCOMPLETE_TRANSFORMATIONS=$((INCOMPLETE_TRANSFORMATIONS + 1))
else
  echo "PASS: dependencies.gradle consolidated or not present"
fi

# HARD GATE
if [ "$INCOMPLETE_TRANSFORMATIONS" -gt 0 ]; then
  echo "FATAL: $INCOMPLETE_TRANSFORMATIONS incomplete transformations detected"
  echo "Phase 2 cannot be marked complete until all transformations finish"
  exit 1
fi
```

**On failure**: This is a **HARD GATE** — migration STOPS. Cannot proceed to Phase 2.5 with incomplete transformations. Agent must:
1. Re-read the selective migration skill Task 3.2 (for eps2-war) or Phase 0 step 11 (for dependencies.gradle)
2. Re-execute the incomplete transformation
3. Verify again using the checks above
4. If still incomplete after retry, log detailed failure and exit

### Check 4: bootRun Uses mainClass

**What**: The bootRun configuration block uses `mainClass` property instead of deprecated `main`.

**How to verify**:
```bash
if grep -qE "bootRun\s*\{" build.gradle 2>/dev/null; then
  if grep -qE "^\s*main\s*=" build.gradle 2>/dev/null; then
    echo "FAIL: bootRun uses deprecated 'main' property"
  else
    echo "PASS: bootRun uses mainClass"
  fi
else
  echo "SKIP: No bootRun block in build.gradle"
fi
```

**On failure**: Agent must use Edit tool to replace `main =` with `mainClass =` inside the bootRun block.

### Check 5: JaCoCo Uses reportsDirectory

**What**: The JaCoCo configuration uses `reportsDirectory` instead of deprecated `reportsDir`.

**How to verify**:
```bash
if grep -qE "jacoco\s*\{" build.gradle 2>/dev/null; then
  if grep -q "reportsDir\s*=" build.gradle 2>/dev/null; then
    echo "FAIL: JaCoCo uses deprecated 'reportsDir' property"
  else
    echo "PASS: JaCoCo uses reportsDirectory"
  fi
else
  echo "SKIP: No JaCoCo block in build.gradle"
fi
```

**On failure**: Agent must use Edit tool to replace `reportsDir = file("$buildDir/reports/jacoco")` with `reportsDirectory = layout.buildDirectory.dir("reports/jacoco")`.

### Check 6: Java 21 Source/Target Compatibility

**What**: Java source and target compatibility are set to 21 (not 1.8 or 8).

**How to verify**:
```bash
if grep -qE "sourceCompatibility.*=.*['\"]?(1\.8|8)['\"]?" build.gradle 2>/dev/null; then
  echo "FAIL: sourceCompatibility still set to Java 8"
else
  echo "PASS: Java source/target compatibility updated"
fi
```

**On failure**: Agent must use Edit tool to update sourceCompatibility and targetCompatibility to '21'.

### Check 7: Spring Boot 3.x

**What**: No Spring Boot 2.x dependency versions remain.

**How to verify**:
```bash
if grep -qE "spring-boot.*:2\." build.gradle 2>/dev/null; then
  echo "FAIL: Spring Boot 2.x dependencies still present"
else
  echo "PASS: Spring Boot upgraded to 3.x"
fi
```

**On failure**: Agent must update all Spring Boot dependency versions to 3.x as per Phase 2 main workflow.

### Check 8 (HARD GATE): Spring Boot BOM Version Stripping

**What**: If Spring Boot plugin or BOM is present, Spring Framework, Jackson, and Lombok dependencies MUST have NO explicit versions.

**How to verify**:
```bash
if grep -qE "org\.springframework\.boot" build.gradle 2>/dev/null || grep -qE "platform.*spring-boot-dependencies" build.gradle 2>/dev/null; then
  SPRING_VERSIONED=$(grep -cE "(org\.springframework(\.\w+)?|com\.fasterxml\.jackson\.\w+|org\.projectlombok):[^:]+:[0-9]" build.gradle 2>/dev/null || echo "0")
  if [ "$SPRING_VERSIONED" -gt 0 ]; then
    echo "FAIL: $SPRING_VERSIONED Spring Boot BOM-managed deps have explicit versions"
    grep -E "(org\.springframework(\.\w+)?|com\.fasterxml\.jackson\.\w+|org\.projectlombok):[^:]+:[0-9]" build.gradle | head -5
    exit 1  # HARD GATE - Phase 2 cannot continue with BOM violations
  else
    echo "PASS: Spring Boot BOM version stripping complete"
  fi
else
  echo "SKIP: No Spring Boot BOM present"
fi
```

**On failure**: This is a **HARD GATE**. Agent MUST use Edit tool to strip versions from all Spring Boot BOM-managed dependencies (org.springframework:*, com.fasterxml.jackson.*:*, org.projectlombok:lombok). Cannot proceed to Phase 2.5 until all BOM-managed dependencies have versions removed.

### Check 9: Stale Build Files Cleaned Up

**What**: Orphaned build script files (sonar.gradle, quality.gradle, codeCoverage.gradle) that are no longer applied in build.gradle should be handled.

**How to verify**:
```bash
STALE_FILES_FOUND=0
for STALE_FILE in sonar.gradle quality.gradle codeCoverage.gradle; do
  if [ -f "$STALE_FILE" ]; then
    if ! grep -qE "^[^/]*apply from.*${STALE_FILE}" build.gradle 2>/dev/null; then
      echo "WARN: Orphaned build file found: $STALE_FILE (no longer applied in build.gradle)"
      STALE_FILES_FOUND=$((STALE_FILES_FOUND + 1))
    else
      # Check for conflicting plugin versions between build.gradle and the stale file
      if grep -qE "sonarqube.*['\"]2\." "$STALE_FILE" 2>/dev/null; then
        echo "FAIL: $STALE_FILE has conflicting sonarqube plugin version (2.x)"
        STALE_FILES_FOUND=$((STALE_FILES_FOUND + 1))
      fi
    fi
  fi
done

if [ "$STALE_FILES_FOUND" -eq 0 ]; then
  echo "PASS: No stale build files found"
fi
```

**On failure**: Agent must either remove the stale file or update it to use compatible plugin versions. If build.gradle buildscript classpath still references a plugin from the stale file but the `apply plugin` is commented out, remove the classpath entry.

### Check 10 (CRITICAL): Project Compiles

**What**: Project compiles successfully after selective migration changes.

**How to verify**:
```bash
$GRADLE_CMD compileJava > /dev/null 2>&1
if [ $? -eq 0 ]; then
  echo "PASS: compileJava succeeded"
else
  echo "FAIL: compileJava failed after selective migration"
fi
```

**On failure**: This is a CRITICAL issue. Agent must diagnose compilation errors and apply fixes (up to 5 retry attempts). If compilation still fails after 5 retries, migration STOPS — do not proceed to Phase 2.5.

See [common.md](common.md) for auto-fix behavior, integration details, and the mandatory Gradle exit code verification pattern.

**Phase 2 specifics:** This phase performs selective dependency migration and build configuration. HARD GATES are Check 3 (transformation completeness), Check 8 (Spring Boot BOM version stripping), and Check 10 (compilation). If any HARD GATE fails, migration STOPS. The validation agent covers these checks via red flags 4, 5, 7, 8, 11, 16, 17, 18.
