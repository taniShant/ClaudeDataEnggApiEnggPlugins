# Phase 6 Validation Checklist

Post-Phase 6 verification checks. Run after Phase 6 commit to confirm test migration was executed.

## Checks

### Check 1: No JUnit 4 Imports

**What**: All JUnit 4 imports have been migrated to JUnit 5 (Jupiter).

**How to verify**:
```bash
JUNIT4_COUNT=$(grep -rnc "import org.junit.Test\b\|import org.junit.Before\b\|import org.junit.After\b\|import org.junit.BeforeClass\b\|import org.junit.AfterClass\b\|import org.junit.Ignore\b\|import org.junit.runner.RunWith\b\|import org.junit.Rule\b" --include="*.java" src/test/ 2>/dev/null | grep -v ":0$" | wc -l)
if [ "$JUNIT4_COUNT" -gt 0 ]; then
  echo "FAIL: $JUNIT4_COUNT files still have JUnit 4 imports"
else
  echo "PASS: No JUnit 4 imports found"
fi
```

**On failure**: Agent must apply JUnit 4→5 annotation mappings from `reference/test_migration.md`.

### Check 2: useJUnitPlatform() Present

**What**: All test tasks have `useJUnitPlatform()` for JUnit 5 discovery.

**How to verify**:
```bash
if ! grep -q "useJUnitPlatform()" build.gradle 2>/dev/null; then
  echo "FAIL: useJUnitPlatform() not found"
else
  echo "PASS: useJUnitPlatform() present"
fi
```

**On failure**: Agent must add `useJUnitPlatform()` to test task configuration.

### Check 3: --add-opens JVM Args Present

**What**: Test tasks have `--add-opens` args required for Mockito/Spring reflection on Java 21.

**How to verify**:
```bash
if grep -q "add-opens" build.gradle 2>/dev/null; then
  echo "PASS: --add-opens JVM args present"
else
  echo "WARN: --add-opens JVM args not found (may cause Mockito/reflection failures)"
fi
```

**On failure**: Agent must add `--add-opens` args for `java.base/java.lang`, `java.base/java.lang.reflect`, `java.base/java.util` to test task JVM args.

### Check 4: Mockito 5 Compatible

**What**: Test classes use `@ExtendWith(MockitoExtension.class)` instead of `@RunWith(MockitoJUnitRunner.class)`.

**How to verify**:
```bash
MOCKITO_RUNNER=$(grep -rnc "MockitoJUnitRunner\|MockitoRunner" --include="*.java" src/test/ 2>/dev/null | grep -v ":0$" | wc -l)
if [ "$MOCKITO_RUNNER" -gt 0 ]; then
  echo "FAIL: $MOCKITO_RUNNER files still use MockitoJUnitRunner"
else
  echo "PASS: Mockito 5 compatible annotations"
fi
```

**On failure**: Agent must replace `@RunWith(MockitoJUnitRunner.class)` with `@ExtendWith(MockitoExtension.class)`.

### Check 5: Tests Pass

**What**: All tests pass after migration.

**How to verify**:
```bash
$GRADLE_CMD test > /dev/null 2>&1
if [ $? -eq 0 ]; then
  echo "PASS: All tests pass"
else
  echo "FAIL: Some tests are failing"
fi
```

**On failure**: Delegate remaining failures to `test-fix-agent`.

### Check 6: vintage-engine Bridge Present When JUnit 4 Imports Remain

**What**: If any JUnit 4 imports remain after migration (partial migration), `junit-vintage-engine` must be present to run those tests.

**How to verify**:
```bash
JUNIT4_REMAINING=$(grep -rl "import org.junit.Test\b" --include="*.java" src/test/ 2>/dev/null | wc -l)
if [ "$JUNIT4_REMAINING" -gt 0 ]; then
  if grep -q "junit-vintage-engine" build.gradle 2>/dev/null; then
    echo "PASS: $JUNIT4_REMAINING files still use JUnit 4 but junit-vintage-engine bridge is present"
  else
    echo "FAIL: $JUNIT4_REMAINING files still use JUnit 4 but junit-vintage-engine is MISSING"
  fi
else
  echo "PASS: No JUnit 4 imports remain (vintage-engine not needed)"
fi
```

**On failure**: Agent must add `testRuntimeOnly 'org.junit.vintage:junit-vintage-engine'` to the dependencies block in build.gradle. The version is managed by the spring-boot-dependencies BOM, so no explicit version is needed.

## Integration

The validation agent (`mca-jdk-validation-agent.md`) covers these checks via red flags #3 (JUnit 4), #6 (--add-opens), #8 (useJUnitPlatform).
