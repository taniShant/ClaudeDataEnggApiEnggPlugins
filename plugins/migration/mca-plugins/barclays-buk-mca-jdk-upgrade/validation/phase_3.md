# Phase 3 Validation Checklist

Post-Phase 3 verification checks. Run after Phase 3 commit to confirm javax→jakarta namespace migration was executed.

## Checks

### Check 1: No Remaining javax Imports (Migratable)

**What**: All migratable javax imports have been converted to jakarta equivalents.

**How to verify**:
```bash
JAVAX_COUNT=$(grep -rncE "import javax\.(servlet|validation|persistence|annotation|inject|transaction|ws\.rs|xml\.bind|mail|activation|el|faces)" --include="*.java" src/ 2>/dev/null | wc -l)
if [ "$JAVAX_COUNT" -gt 0 ]; then
  echo "FAIL: $JAVAX_COUNT migratable javax imports still present"
else
  echo "PASS: No migratable javax imports found"
fi
```

**Exclusions**: Do NOT flag javax.swing, javax.crypto, javax.sql, javax.net, javax.naming, javax.management, javax.imageio — these are JDK packages.

**On failure**: Agent must apply the 12 javax→jakarta package mappings from `reference/javax_jakarta.md`.

### Check 2: jakarta Dependencies Present

**What**: Jakarta dependency coordinates have been added to replace javax dependencies.

**How to verify**:
```bash
if grep -q "jakarta" build.gradle 2>/dev/null; then
  echo "PASS: Jakarta dependencies present"
else
  if [ "$JAVAX_COUNT" -gt 0 ]; then
    echo "FAIL: No jakarta dependencies found but javax code was present"
  else
    echo "PASS: No javax code to migrate"
  fi
fi
```

**On failure**: Agent must add jakarta dependency coordinates per `reference/javax_jakarta.md`.

### Check 3: Compilation Success

**What**: Project compiles successfully after namespace migration.

**How to verify**:
```bash
$GRADLE_CMD compileJava > /dev/null 2>&1
if [ $? -eq 0 ]; then
  echo "PASS: compileJava succeeded"
else
  echo "FAIL: compileJava failed after Phase 3"
fi
```

**On failure**: Agent must investigate compilation errors (likely missed imports or dependency coordinates) and fix.

## Integration

The validation agent (`mca-jdk-validation-agent.md`) covers these checks via red flag #1 (Mixed javax/jakarta imports).
