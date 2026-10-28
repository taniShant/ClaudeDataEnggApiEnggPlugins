# Validation Common Patterns

Shared validation behaviors referenced by individual phase validation files.

## Auto-Fix Behavior

When any validation check fails in a phase:

1. Log the specific failure with `WARNING` severity
2. Attempt automatic fix using Read/Edit tools
3. Re-run the failed check to confirm fix
4. If fix was applied, amend the phase commit
5. If fix cannot be applied, log `ERROR` and proceed with warning

## Gradle Exit Code Verification (MANDATORY)

**IRON LAW**: Never pipe Gradle output through `tee` when checking exit codes. The `| tee` pattern masks the real exit code because `$?` reflects tee's status (always 0), not Gradle's.

**WRONG — exit code is always 0:**
```bash
$GRADLE_CMD compileJava 2>&1 | tee -a "$LOG_FILE"
if [ $? -eq 0 ]; then  # BUG: this checks tee's exit code, not gradle's
```

**WRONG — PIPESTATUS is fragile and shell-dependent:**
```bash
$GRADLE_CMD clean build -x test 2>&1 | tee -a "$LOG_FILE"
BUILD_EXIT_CODE=${PIPESTATUS[0]}  # BUG: not portable, fails in subshells
```

**CORRECT — redirect-then-check pattern:**
```bash
$GRADLE_CMD compileJava > /tmp/gradle_compile.log 2>&1
COMPILE_EXIT_CODE=$?
cat /tmp/gradle_compile.log >> "$LOG_FILE"

if [ $COMPILE_EXIT_CODE -eq 0 ] && ! grep -q "BUILD FAILED" /tmp/gradle_compile.log; then
  log "│  └─ Result: SUCCESS"
else
  log "│  └─ Result: FAILED (exit code: $COMPILE_EXIT_CODE)"
fi
```

**Key rules:**
1. Redirect output to a temp file, NOT through a pipe
2. Capture `$?` immediately after the Gradle command
3. Append the temp file to the log with `cat >>` after capturing the exit code
4. Always perform a secondary `BUILD FAILED` string check as a guard

All phases MUST use this pattern for every `$GRADLE_CMD` invocation.

## Integration

The main agent (`mca-jdk-upgrade-agent.md`) runs phase checks after each phase commit via inline bash. The validation agent (`mca-jdk-validation-agent.md`) can also run these checks in phase-specific mode or full mode (all 18 red flags).
