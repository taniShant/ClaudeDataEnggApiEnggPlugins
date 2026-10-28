---
description: Run pytest on generated test suite (optional — requires Python)
disable-model-invocation: false
---

# /run-tests

Run the generated pytest test suite against the generated pipeline code. Non-blocking — failures are reported but do not halt the session.

## Usage

```
/run-tests [--verbose]
```

## Arguments

- `--verbose` (optional) — Show full pytest output with long tracebacks (default: short/summary mode)

## Prerequisites

- Test files must exist (run `/gen-tests` first)
- `session/session_state.json` must exist with `platform` set

## Behaviour

### STEP 0.5 — Test Fixture Staleness Detection (Pre-Execution Warning)

Before executing tests, compare critical fixture values against the actual generated config to detect stale test fixtures from a previous generation run.

**Algorithm:**

1. For each test file in `{test_dir}`:
   - Search for config-derived values: `target.table`, `process_name`, `audit.table`
   - Extract these values from the test fixture (regex: assignment patterns or mock return values)

2. Read actual config:
   - Databricks: `generated/databricks/src/Notebooks/{day0|day1}/{schema}_{table}/{schema}_{table}_config.yml`
   - Glue: `generated/glue/config/{db}_{table}_config.json`

3. Compare fixture values against actual config values.

4. **If mismatch detected:**
   ```
   ⚠️ Stale test fixtures detected (non-blocking):
      test_transform_{table}.py:
        fixture process_name = "{fixture_value}"
        actual config process_name = "{actual_value}"
      
      Tests may pass with incorrect assertions. Consider re-running /gen-tests.
   ```
   Log to `session/audit_log.jsonl`: `[TEST-STALENESS] Fixture mismatch detected — {details}`
   
   **CONTINUE** (non-blocking) — staleness does not prevent test execution.

5. **If no config file found:** Skip staleness check (config not yet generated or different structure).

6. **If all values match:** No warning emitted. Continue to STEP 1.

---

### STEP 1 — Load Session State

1. Read `session/session_state.json`
2. Extract `python_path`, `platform`
3. Determine `test_dir`:
   - Glue: `generated/glue/tests/`
   - Databricks: `generated/databricks/tests/`

### STEP 2 — Validate Python Availability

**Python guard** — follow `agents/refs/python-runtime-contract.md § Guard Pattern`.
If `python_path == null`: set `test_execution_result = "skipped_no_python"`, log, CONTINUE (non-blocking EXIT).

If `python_path` is set, verify pytest is installed:
```bash
{python_path} -m pytest --version 2>/dev/null
```

If exit code != 0 (pytest not installed):
```
⚠️ pytest not installed in {python_path} environment.

To install:
  {python_path} -m pip install pytest pytest-cov pyspark
```
Set `session_state.test_execution_result = "skipped_no_pytest"`. EXIT (non-blocking).

### STEP 3 — Validate Test Files Exist

Check that `{test_dir}` contains at least one `test_*.py` file.

If no test files found:
```
No test files found in {test_dir}.
Run /gen-tests first to generate the test suite.
```
EXIT with error.

### STEP 4 — Execute pytest

Run via Bash tool:
```bash
{python_path} -m pytest {test_dir} --tb={short|long} -q 2>&1
```

Use `--tb=long` if `--verbose` flag provided, otherwise `--tb=short`.

Timeout: 120 seconds.

### STEP 5 — Report Results

**If passed (exit code == 0):**
```
✅ ALL TESTS PASSED
   {N} tests collected, {N} passed in {T}s
```
Set `session_state.test_execution_result = "passed"`. Set `session_state.test_execution_output = null`.

**If failed (exit code != 0):**
```
⚠️ TEST FAILURES DETECTED (non-blocking)
   {summary from pytest output}

   Full output:
   {pytest output — first 80 lines if --verbose, first 30 lines otherwise}
   
   Next steps:
     • Fix test or implementation issues
     • Re-run: /run-tests
     • /push will also verify tests before pushing
```
Set `session_state.test_execution_result = "failed"`. Store first 50 lines of output in `session_state.test_execution_output`.

**If timeout (>120s):**
```
⚠️ Test execution timed out (>120s). Possible causes:
   • SparkSession initialization slow on this machine
   • Tests are hanging on external resource
   
   Try running manually: {python_path} -m pytest {test_dir} --tb=short -x
```
Set `session_state.test_execution_result = "timeout"`. Set `session_state.test_execution_output = null`.

### STEP 6 — Update Session State

Write to `session/session_state.json`:
- `test_execution_result`
- `test_execution_output` (if failed, first 50 lines; null otherwise)

Log to `session/audit_log.jsonl`:
```json
{"timestamp": "<ISO 8601>", "event": "test_execution", "command": "/run-tests", "result": "{result}", "tests_collected": N, "tests_passed": M, "duration_s": T}
```

## Output Files

- `session/session_state.json` (updated: `test_execution_result`, `test_execution_output`)
- `session/audit_log.jsonl` (new entry)

## Failure Modes

| Condition | Behaviour |
|-----------|-----------|
| Python not found | WARN and exit (non-blocking) |
| pytest not installed | WARN and exit (non-blocking) |
| No test files | ERROR — direct user to `/gen-tests` |
| Tests fail | WARN with details (non-blocking) |
| Timeout | WARN with manual execution instructions |

## Anti-Hallucination Rules

- NEVER report test results without actually running pytest via Bash tool
- NEVER invent pass/fail counts — parse from actual pytest output
- NEVER install packages for the consumer — only suggest installation commands
- NEVER block the pipeline on test failure — this command is always non-blocking
