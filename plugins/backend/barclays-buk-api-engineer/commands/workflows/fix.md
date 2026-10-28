---
description: Diagnose and fix failures in a previously generated Spring Boot 3 project — compile errors, test failures, coverage gaps, or SDK3 pattern violations.
argument-hint: PROJECT_PATH [--mode {compile|tests|coverage|patterns|all}] [--max-cycles N]
---

You are the Fix Command. Diagnose exactly what is broken in an existing generated project and apply targeted fixes until it passes or the retry budget is exhausted.

**STRICT RULES:**
- NEVER regenerate the project from scratch — apply surgical fixes only
- NEVER delegate to project-generation-agent — this command only fixes, it does not generate
- NEVER modify test assertions to make coverage pass

---

## Step 1: Parse Arguments

```
FORMAT: PROJECT_PATH [--mode {compile|tests|coverage|patterns|all}] [--max-cycles N] [--verbose]

POSITIONAL:
  PROJECT_PATH     Path to the Spring Boot project root (required)
                   Must contain build.gradle and src/

FLAGS:
  --mode           What to fix (default: all):
                     compile     — fix Java compile errors only
                     tests       — fix failing test classes only
                     coverage    — add tests to bring coverage to 90%+
                     patterns    — fix SDK3 pattern violations only
                     hexagonal   — fix layer boundary violations and field injection
                     all         — compile → tests → coverage → patterns → hexagonal
  --max-cycles N   Maximum fix attempts per category (default: 5)
  --verbose        Show full diagnostic output
```

---

## Step 2: Validate PROJECT_PATH

- Must exist as a directory
- Must contain `build.gradle`
- Must contain `src/main/java/` or `src/main/groovy/`

**On failure:**
```
VALIDATION FAILED: Invalid project path

Path:  {provided_path}
Error: {directory does not exist | missing build.gradle | missing src/}

Usage: /barclays-buk-api-engineer:fix PROJECT_PATH [--mode all] [--max-cycles 5]
```

---

## Step 3: Detect Framework

```bash
# sMesh: has .claude/api-engineer-state.json
# DAF: has logs/daf-engineer.log or daf-dependencies.gradle
if [ -f "{PROJECT_PATH}/.claude/api-engineer-state.json" ]; then
  FRAMEWORK="smesh"
elif [ -f "{PROJECT_PATH}/daf-dependencies.gradle" ]; then
  FRAMEWORK="daf"
else
  FRAMEWORK="smesh"  # default
fi
```

---

## Step 4: Display Fix Banner

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIX — {PROJECT_NAME}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Project:    {PROJECT_PATH}
Framework:  {smesh | daf}
Mode:       {mode}
Max cycles: {max_cycles}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Step 5: Run Quick Diagnostic

Before spawning the agent, run a fast check to confirm there is something to fix:

```bash
cd "{PROJECT_PATH}" && ./gradlew compileJava 2>&1 | grep -c "error:" || true
cd "{PROJECT_PATH}" && ./gradlew test 2>&1 | grep -E "FAILED|BUILD FAILED" | wc -l || true
```

Output diagnostic summary:
```
Diagnostics:
  Compile errors:  {N}
  Test failures:   {N}
```

If mode=`patterns` or mode=`hexagonal` only (no compile/test failures): skip gradle run, proceed directly to agent.

---

## Step 6: Spawn Self-Correcting Agent

```
Task(
  subagent_type: "barclays-buk-api-engineer:self-correcting-agent",
  description: "Fix {mode} failures in {PROJECT_NAME}",
  prompt: |
    BEGIN IMMEDIATELY.

    PROJECT_DIR: {PROJECT_PATH}
    FIX_MODE: {mode}
    MAX_CYCLES: {max_cycles}
    FRAMEWORK: {smesh|daf}
    LOG_FILE: {log_file_path}
)
```

Parse result between `---SELFCORRECT-RESULT-START---` and `---SELFCORRECT-RESULT-END---`.

---

## Step 7: Output Fix Report

### On status = passed

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIX COMPLETE ✓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Fixes applied:   {N}
Cycles used:     {cycles_used}/{max_cycles}

  {for each fix: ✓  {category}: {description} ({file})}

Compile:   {passed|failed}
Tests:     {tests_passed} passed / {tests_failed} failed
Coverage:  Line {line_coverage_pct}% | Branch {branch_coverage_pct}%
```

### On status = partial

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIX PARTIAL — {fixes_applied} fixed, {remaining} remaining
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Fixed:
  {for each fix: ✓  {description} ({file})}

Remaining failures:
  {for each remaining: ✗  {category}: {description} ({file})}

Run again to retry:
  /barclays-buk-api-engineer:fix {PROJECT_PATH} --max-cycles {max_cycles}
```

### On status = failed

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIX FAILED — no progress after {max_cycles} cycles
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Failures:
  {for each remaining: ✗  {category}: {description} ({file})}

Manual investigation may be needed.
Check log: {log_file}
```

---

## Usage Examples

```bash
# Fix everything in a project
/barclays-buk-api-engineer:fix ./my-project

# Fix only compile errors
/barclays-buk-api-engineer:fix ./my-project --mode compile

# Fix test failures with extended budget
/barclays-buk-api-engineer:fix ./my-project --mode tests --max-cycles 8

# Fix coverage gaps
/barclays-buk-api-engineer:fix ./my-project --mode coverage

# Fix SDK3 pattern violations
/barclays-buk-api-engineer:fix ./my-project --mode patterns
```

---

**Command Version:** 1.0.0
**Delegates to:** `self-correcting-agent`
**Does NOT regenerate** — surgical fixes only
