# Phase 2.5 Validation Checklist

Post-Phase 2.5 verification checks. Run after Phase 2.5 commit to confirm test package alignment was executed correctly.

## Checks

### Check 1: Test Packages Match Source Packages

**What**: Test classes under `src/test/java` should mirror the package structure of `src/main/java`. Any test classes in mismatched packages should have been moved.

**How to verify**:
```bash
MISMATCHED=0
for TEST_FILE in $(find src/test/java -name "*.java" 2>/dev/null); do
  TEST_PKG=$(grep "^package " "$TEST_FILE" 2>/dev/null | sed 's/package //;s/;//' | tr '.' '/')
  if [ -n "$TEST_PKG" ]; then
    EXPECTED_DIR="src/test/java/$TEST_PKG"
    ACTUAL_DIR=$(dirname "$TEST_FILE" | sed 's|^src/test/java/||')
    if [ "$ACTUAL_DIR" != "$TEST_PKG" ]; then
      MISMATCHED=$((MISMATCHED + 1))
    fi
  fi
done

if [ "$MISMATCHED" -eq 0 ]; then
  echo "PASS: All test packages match their file locations"
else
  echo "FAIL: $MISMATCHED test files have mismatched package declarations"
fi
```

**On failure**: Agent must update the `package` declaration in mismatched test files to match their directory location, or move the files to match the declared package.

### Check 2: Test Compilation Succeeds

**What**: Tests compile successfully after package realignment.

**How to verify**:
```bash
$GRADLE_CMD compileTestJava 2>&1
if [ $? -eq 0 ]; then
  echo "PASS: Test compilation succeeds"
else
  echo "FAIL: Test compilation failed after package alignment"
fi
```

**On failure**: Agent must fix import statements or package declarations that were broken during the move.

### Check 3: No Orphaned Test Files

**What**: No test files exist in packages that have no corresponding source package.

**How to verify**:
```bash
ORPHANS=0
for TEST_DIR in $(find src/test/java -type d 2>/dev/null); do
  RELATIVE=$(echo "$TEST_DIR" | sed 's|src/test/java||')
  if [ -n "$RELATIVE" ] && [ ! -d "src/main/java$RELATIVE" ]; then
    TEST_COUNT=$(find "$TEST_DIR" -maxdepth 1 -name "*.java" 2>/dev/null | wc -l)
    if [ "$TEST_COUNT" -gt 0 ]; then
      ORPHANS=$((ORPHANS + TEST_COUNT))
    fi
  fi
done

if [ "$ORPHANS" -eq 0 ]; then
  echo "PASS: No orphaned test files found"
else
  echo "WARN: $ORPHANS test file(s) in packages with no corresponding source package"
fi
```

**On failure**: Not blocking — these may be intentional (e.g., test utilities, integration test packages). Log as warning.

See [common.md](common.md) for auto-fix behavior and integration details.

**Phase 2.5 specifics:** Ensures test classes are properly aligned with source packages before namespace migration in Phase 3.
