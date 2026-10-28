# Validator: test-coverage-validator

**Purpose**: Verify test file existence for each generated transform/driver notebook and report test execution status from session state. Informational only — never blocks pipeline.

**Severity**: Flag — informational only. This validator reports coverage status but does NOT block generation. Actual test enforcement occurs at `/push` gate (Condition 4).

**Platform**: Glue + Databricks

**Important Constraint**: This validator does NOT run `pytest` or `py_compile`. It reads `session_state` values populated by `/run-tests`. Test execution is handled separately by that command.

---

## Validation Logic

### Check 1 — Test File Existence

For each generated notebook, verify a corresponding test file exists.

**Expected test file mapping:**

| Generated File | Expected Test File |
|---|---|
| `generated/databricks/src/Notebooks/day0/{schema}_{table}/{schema}_{table}_transform.py` | `generated/databricks/tests/test_{schema}_{table}_transform.py` |
| `generated/databricks/src/Notebooks/day1/{schema}_{table}/{schema}_{table}_transform.py` | `generated/databricks/tests/test_{schema}_{table}_transform.py` |
| `generated/databricks/src/Notebooks/day0/{schema}_{table}/{schema}_{table}_driver.py` | `generated/databricks/tests/test_{schema}_{table}_driver.py` |
| `generated/databricks/src/Notebooks/day1/{schema}_{table}/{schema}_{table}_driver.py` | `generated/databricks/tests/test_{schema}_{table}_driver.py` |

Multi-source-system (when `data_flow_detection.source_systems` is non-empty):

| Generated File | Expected Test File |
|---|---|
| `generated/databricks/src/Notebooks/{day}/{source_system}/{schema}_{table}/{schema}_{table}_transform.py` | `generated/databricks/tests/test_{schema}_{table}_{source_system}_transform.py` |
| `generated/databricks/src/Notebooks/{day}/{source_system}/{schema}_{table}/{schema}_{table}_driver.py` | `generated/databricks/tests/test_{schema}_{table}_{source_system}_driver.py` |

**Rules:**
1. Scan `generated/databricks/src/Notebooks/{day0,day1}/` (and `{day0,day1}/{source_system}/` for multi-source-system) for `*_transform.py` and `*_driver.py` files
2. For each, check existence of corresponding `test_*` file in `generated/databricks/tests/`
3. WARNING if test file missing (indicates `/gen-tests` was not run or failed for this table)
4. Day0 and Day1 transforms may share the same test file (test covers both load types)

### Check 2 — Syntax Check Status

Read `session_state.syntax_check_result` and report.

**Possible values:**
| Value | Report |
|---|---|
| `"passed"` | ✅ Syntax check: PASSED |
| `"failed"` | ⚠️ Syntax check: FAILED — review errors before `/push` |
| `null` | ℹ️ Syntax check: NOT EXECUTED — run `/run-tests` |
| `"skipped_no_python"` | ℹ️ Syntax check: SKIPPED (Python not available on this machine) |

**Rules:**
1. Read `session/session_state.json` → `syntax_check_result` field
2. Report status using appropriate indicator
3. Never BLOCK — always informational

### Check 3 — Test Execution Status

Read `session_state.test_execution_result` and report.

**Possible values:**
| Value | Report |
|---|---|
| `"passed"` | ✅ Tests: PASSED |
| `"failed"` | ⚠️ Tests: FAILED (non-blocking — review output) |
| `null` | ℹ️ Tests: NOT EXECUTED — run `/run-tests` |
| `"skipped"` | ℹ️ Tests: SKIPPED |

**Rules:**
1. Read `session/session_state.json` → `test_execution_result` field
2. Report status using appropriate indicator
3. Never BLOCK — always informational

### Check 4 — Coverage Gate Assessment

Assess whether the >90% coverage target is met based on available information.

**Rules:**
1. If `test_execution_result == "passed"` → Report: "✅ Coverage gate: TARGET MET (>90% — generation templates ensure high coverage)"
2. If `test_execution_result == "failed"` → Report: "⚠️ Coverage gate: INDETERMINATE — tests failed, coverage cannot be confirmed"
3. If `test_execution_result` is `null` or `"skipped"` → Report: "ℹ️ Coverage gate: NOT ASSESSED — tests not executed"

**Note on coverage measurement:**
- The plugin does NOT invoke a coverage tool (e.g., `pytest-cov`) at validation time
- The >90% target is a generation-time guarantee: test templates are designed to exercise all transform paths
- Actual coverage percentage is verified during `/run-tests` execution, not here
- This validator only reports whether that execution was successful

### Check 5 — Test Fixture Config Fidelity

Compare critical config values in test fixtures against the actual generated config.yml. Detects stale or hallucinated fixture values that would cause tests to pass spuriously.

**Severity**: WARNING (informational — does not block)

**Validation Logic:**

1. For each test file in `generated/{platform}/tests/`:
   - Search for `sample_config` fixture or config mock definitions
   - Extract values for: `target.table`, `pipeline.process_name`, `audit.table`
2. Read actual config from `generated/databricks/src/Notebooks/{day0|day1}/{schema}_{table}/{schema}_{table}_config.yml` (or `{day0|day1}/{source_system}/{schema}_{table}/{schema}_{table}_config.yml` for multi-source-system)
3. Compare extracted test fixture values against actual config values
4. Report mismatches

**Report format:**
```
⚠️ Test Fixture Config Fidelity:
   test_transform_{table}.py:
     fixture target.table = "{fixture_value}" ≠ actual "{actual_value}"
     fixture process_name = "{fixture_value}" ≠ actual "{actual_value}"
```

**Common false-positives:** If config uses placeholders (e.g., `{{target_catalog}}`), fixture may use a test-specific value — this is acceptable and should NOT be flagged.

### Check 6 — Test Schema Type Correctness

Compare `expected_types` or StructType definitions in test files against `target_column_datatype` from `mapping_parsed.json`. Detects type inference errors where column types are guessed from names rather than read from the mapping.

**Severity**: WARNING (informational — does not block)

**Validation Logic:**

1. For each test file containing StructType definitions or type assertion dicts:
   - Extract column→type mappings from test fixtures (e.g., `StructField("active", StringType())`)
2. Read `session/mapping_parsed.json` → for each target column, get `target_column_datatype`
3. Compare: does the test fixture type match the mapping-specified type?
4. Flag mismatches

**Report format:**
```
⚠️ Test Schema Type Mismatch:
   conftest.py:
     column "active" — fixture: IntegerType() ≠ mapping: STRING → should be StringType()
     column "amount" — fixture: StringType() ≠ mapping: DECIMAL(18,2) → should be DecimalType(18,2)
```

**Known correct patterns (do NOT flag):**
- Audit columns (`eff_start_date`, `eff_end_date`, `dw_lod_tmp`, etc.) — these follow platform convention, not mapping
- Columns where mapping says `STRING` and fixture uses `StringType()` — correct match

---

## Pass Condition

Test files exist for all generated transforms/drivers. Session state shows successful syntax check and test execution. (This validator always "passes" — it only reports status, never blocks.)

## Fail Action

Flag (never HALT). Output:
```
📋 Test Coverage Report:

  Test Files:
    ✅ test_{schema}_{table}_transform.py — exists
    ✅ test_{schema}_{table}_driver.py — exists
    ⚠️ test_{schema2}_{table2}_transform.py — MISSING
       → Run /gen-tests to generate

  Execution Status:
    Syntax check     : {status_indicator} {status_message}
    Test execution   : {status_indicator} {status_message}
    Coverage gate    : {status_indicator} {status_message}

  Next Steps:
    {recommended_actions}
```

**Recommended actions (conditional):**
- If test files missing: `Run /gen-tests to generate missing test files.`
- If tests not executed: `Run /run-tests to execute the test suite.`
- If tests failed: `Review test output in session/test_results/ and fix failing assertions.`
- If all passed: `All checks passed. Ready for /push.`

---

## Notes

- This validator is assigned to **Batch 6 (Informational)** in the `/validate` pipeline
- Batch 6 NEVER produces BLOCKING findings — even if all tests are missing
- The `/push` command independently gates on test passage (Condition 4) — this validator is advisory only
- Coverage percentage reporting is by design NOT a runtime measurement in this validator
