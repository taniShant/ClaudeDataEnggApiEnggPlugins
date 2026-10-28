# Phase 7 Validation Checklist

Post-Phase 7 verification checks. Run after Phase 7 commit to confirm validation and coverage targets were met.

## Checks

### Check 1: Unit Test Coverage ≥ 90%

**What**: JaCoCo line/instruction coverage meets the 90% threshold.

**How to verify**:
```bash
# Run JaCoCo
$GRADLE_CMD jacocoTestReport > /dev/null 2>&1

# Check coverage from XML report
JACOCO_XML=$(find build -name "jacoco*.xml" -path "*/jacocoTestReport/*" 2>/dev/null | sed -n '1p')
if [ -n "$JACOCO_XML" ]; then
  # Parse instruction coverage from the report
  MISSED=$(grep -o 'type="INSTRUCTION" missed="[0-9]*"' "$JACOCO_XML" | sed 's/.*missed="\([0-9]*\)".*/\1/' | paste -sd+ - | bc 2>/dev/null || echo "0")
  COVERED=$(grep -o 'type="INSTRUCTION" missed="[0-9]*" covered="[0-9]*"' "$JACOCO_XML" | sed 's/.*covered="\([0-9]*\)".*/\1/' | paste -sd+ - | bc 2>/dev/null || echo "0")
  TOTAL=$((MISSED + COVERED))
  if [ "$TOTAL" -gt 0 ]; then
    COVERAGE=$((COVERED * 100 / TOTAL))
    if [ "$COVERAGE" -ge 90 ]; then
      echo "PASS: Unit test coverage is ${COVERAGE}%"
    else
      echo "FAIL: Unit test coverage is ${COVERAGE}% (required ≥90%)"
    fi
  else
    echo "UNABLE TO VERIFY: Could not parse JaCoCo report"
  fi
else
  echo "UNABLE TO VERIFY: JaCoCo XML report not found"
fi
```

**On failure**: Coverage orchestrator agent should have already attempted to improve coverage. If still below 90%, log as a known gap in the PR description.

### Check 2: Mutation Coverage ≥ 90%

**What**: Pitest mutation coverage meets the 90% threshold.

**How to verify**:
```bash
# Run Pitest
$GRADLE_CMD pitest > /dev/null 2>&1

# Check mutation score from report
PITEST_HTML=$(find build -name "index.html" -path "*/pitest/*" 2>/dev/null | sed -n '1p')
if [ -n "$PITEST_HTML" ]; then
  MUTATION_SCORE=$(grep -o "[0-9]*% mutation coverage" "$PITEST_HTML" | sed 's/%.*//' | sed -n '1p')
  if [ -n "$MUTATION_SCORE" ] && [ "$MUTATION_SCORE" -ge 90 ]; then
    echo "PASS: Mutation coverage is ${MUTATION_SCORE}%"
  elif [ -n "$MUTATION_SCORE" ]; then
    echo "FAIL: Mutation coverage is ${MUTATION_SCORE}% (required ≥90%)"
  else
    echo "UNABLE TO VERIFY: Could not parse Pitest report"
  fi
else
  echo "UNABLE TO VERIFY: Pitest report not found"
fi
```

**On failure**: Log as a gap. Coverage orchestrator should have made its best effort.

### Check 3: All Tests Pass (HARD GATE)

**What**: All unit and integration tests pass. This is a hard gate — migration cannot proceed to Phase 8 with failing tests.

**How to verify**:
```bash
$GRADLE_CMD test > /tmp/phase7_test.log 2>&1
TEST_EXIT_CODE=$?
cat /tmp/phase7_test.log >> "$LOG_FILE"

if [ $TEST_EXIT_CODE -eq 0 ] && ! grep -q "BUILD FAILED" /tmp/phase7_test.log; then
  echo "PASS: All tests pass"
else
  echo "FAIL: Tests failing in Phase 7 quality gate"
  grep -A2 "FAILED" /tmp/phase7_test.log | head -20
fi
```

**On failure**: This is a **HARD GATE**. Do NOT proceed to Phase 8 with failing tests. Log specific failures, attempt fixes, and re-run. If tests still fail after retries, log all failures in the PR description as known gaps and mark Phase 7 as failed.

### Check 4: Full Validation Scan (MANDATORY)

**What**: Invoke the full validation agent scan (all 18 red flags). This is MANDATORY — the validation agent MUST be explicitly invoked via the Task tool.

**How to verify**:
```
Spawn mca-jdk-validation-agent via Task tool with:
  subagent_type: mca-jdk-validation-agent
  prompt: |
    project_path: {project_path}
    log_file: {log_file}
    group: {group}
    validation_phase: Full
```

Parse the validation agent's output:
- If **APPROVED**: Log approval and proceed to Phase 8.
- If **REJECTED**: Log each red flag issue. Attempt auto-fix for fixable issues. Re-invoke validation agent (up to 2 retries). If still REJECTED after retries, log all remaining issues in PR description as known gaps.

**On failure**: Log all red flags found in the PR description with remediation steps.

### Check 5: Integration Test Status

**What**: If integration-test-agent was invoked, verify all integration tests now pass.

**How to verify**:
```bash
log "├─ Validation: Check #7 - Integration test status"

# Check if project has integration tests
if [ -d "src/integrationTest" ] || grep -q "integrationTest" build.gradle 2>/dev/null; then
  log "│  └─ Project has integration test configuration"

  # Run integration tests
  $GRADLE_CMD integrationTest --console=plain > /tmp/integration_test.log 2>&1
  INTEGRATION_EXIT_CODE=$?

  if [ $INTEGRATION_EXIT_CODE -eq 0 ]; then
    log "│  └─ Result: PASS - All integration tests pass"
    echo "PASS: Integration tests pass"
  else
    FAILED_COUNT=$(grep -c "FAILED" /tmp/integration_test.log || echo "0")
    log "│  └─ ERROR: $FAILED_COUNT integration tests failing"
    cat /tmp/integration_test.log >> "$LOG_FILE"
    echo "FAIL: $FAILED_COUNT integration tests failing"
    grep "FAILED" /tmp/integration_test.log | head -10
  fi
else
  log "│  └─ No integration tests in project"
  echo "SKIP: No integration tests to verify"
fi
```

**On failure**: Re-invoke integration-test-agent or log failures in PR description. Integration test failures are NOT a hard gate (may require external dependencies).

> **Note:** Coverage improvement (JaCoCo/PIT) is handled separately by the `improve-tests` plugin via `/improve-coverage`. Run it after migration completes.

## Integration

Phase 7 is the final quality gate before push. All 18 red flags should be checked here via the validation agent. The validation agent invocation is MANDATORY — do not skip it or replace it with inline checks alone.
