---
description: Generate pytest test suite with 90 percent coverage target
disable-model-invocation: false
---

# /gen-tests

Generate unit tests for all generated scripts. Enforces >90% coverage target. Runs after all platform scripts are generated, before `/validate`.

## Usage

```
/gen-tests
```

## Prerequisites

- At least one of: `generated/glue/wrapper/{db}_{table}_wrapper.py` (Glue), `generated/glue/transforms/{db}_{table}_transform_day*.py` (Glue), `generated/databricks/src/Notebooks/{day0|day1}/{target_schema}_{table}/*_transform.py`, `generated/databricks/src/Notebooks/{day0|day1}/{target_schema}_{table}/*_driver.py` (Databricks) generated
- `session/intent_identification.json` exists
- `session/crypto_flags.json` exists

## STEP 0.0 — Chain Mode Output Compression

If `session_state.auto_chain.enabled == true` (full-automation mode):
- **Suppress verbose output:** Do NOT print session_state.json content, per-test-file generation details, template selection, or pytest execution output to conversation.
- **Audit log instead:** Write verbose progress entries to `session/audit_log.jsonl` (append-only structured logging).
- **Compact return only:** At command completion, emit ONLY:
  ```
  [{step}/{total}] ✓ /gen-tests — {N} test files generated, syntax: {passed|failed|skipped}
  Checkpoint: post_generation updated
  ```
- **Halt output:** If test generation or syntax check fails, emit max 5-line halt summary. Full details written to `session/audit_log.jsonl`.

---

## STEP 0.1 — Chain Checkpoint Loading

Apply `commands/refs/chain-checkpoint-pattern.md`. Checkpoint key: `post_intent`.

## STEP 0.3 — Read Actual Generated Config (BLOCKING — Anti-Hallucination)

Before template loading, read the ACTUAL generated config file from disk for each target table. This prevents test fixtures from using hallucinated or session-state-inferred config values.

**For each target table:**

1. **Determine config path:**
   - Databricks: `generated/databricks/src/Notebooks/{day0|day1}/{target_schema}_{table}/{target_schema}_{table}_config.yml`
   - Glue: `generated/glue/config/{db}_{table}_config.json`

2. **Read and extract critical values:**
   ```python
   actual_config_values = {
       "target_table": config["target"]["table"],
       "target_schema": config["target"]["schema"],
       "target_catalog": config["target"].get("catalog", "{{target_catalog}}"),
       "process_name": config["pipeline"]["process_name"],
       "audit_table": config["audit"]["table"],
       "environments_keys": list(config.get("environments", {}).keys()),
       "primary_key_cols": config.get("cdc", {}).get("primary_key_cols", []),
       "table_type": config["pipeline"]["table_type"],
       "load_type": config["pipeline"]["load_type"],
   }
   ```

3. **Pass `actual_config_values` dict to test-generator-agent** alongside `templates_content`.

4. **HALT condition:** If config file does NOT exist on disk:
   ```
   ⛔ HALT: Config file not found at {expected_path}.
      /gen-config must run before /gen-tests.
      Run /gen-config first, then retry /gen-tests.
   ```
   This enforces the correct ordering: gen-config → gen-tests.

---

## STEP 0.4 — Pre-Read Templates at Command Level (Context Efficiency)

The command layer reads ALL relevant templates ONCE and passes their content to each per-table agent invocation. This eliminates N-1 redundant disk reads when N tables are processed in parallel.

**Pre-read templates:**
- `${CLAUDE_PLUGIN_ROOT}/templates/tests/conftest.template.py`
- `${CLAUDE_PLUGIN_ROOT}/templates/tests/pytest_ini.template`
- `${CLAUDE_PLUGIN_ROOT}/templates/tests/test_wrapper.template.py` (Glue only)
- `${CLAUDE_PLUGIN_ROOT}/templates/tests/test_transform_nontransactional.template.py`
- `${CLAUDE_PLUGIN_ROOT}/templates/tests/test_transform_transactional.template.py`
- `${CLAUDE_PLUGIN_ROOT}/templates/tests/test_driver.template.py` (Databricks only)
- `${CLAUDE_PLUGIN_ROOT}/templates/tests/test_dag.template.py` (Both platforms; only if `session/dag_spec.json` exists)

**Store as context dict:**
```python
templates_content = {
    "conftest": "<file content>",
    "pytest_ini": "<file content>",
    "test_wrapper": "<file content>",         # Glue only; null for Databricks
    "test_transform_nontransactional": "<file content>",
    "test_transform_transactional": "<file content>",
    "test_driver": "<file content>",          # Databricks only; null for Glue
    "test_dag": "<file content>"              # Both platforms; null if dag_spec.json missing
}
```

**Per-table agent invocation includes:** `templates_content` dict (pre-loaded). Agent skips STEP 0.5 file reads when templates arrive pre-loaded.

**Savings:** For N=10 tables, eliminates 9 × 4 = 36 redundant template file reads (~360KB aggregate).

## STEP 0.5 — Template Rules (BLOCKING — agents must honour)

**Rules (apply whether templates arrive pre-loaded or are read from disk):**
- The template is the **authoritative source of structure** (fixture layout, test method signatures, assertion patterns).
- If the template and prose conflict, **the template wins**.
- Generation = template read + placeholder substitution. Nothing more.
- Any fixture, test method, or assertion NOT present in the template must NOT appear in the output.
- Do NOT generate tests from description or memory — render the template.

---

## Behaviour

Delegate to `test-generator-agent` (using the Agent tool). Pass `templates_content` dict from STEP 0.4. Select templates based on platform and table type:

| Platform | Table Type | Templates Used |
|---|---|---|
| Glue | NonTransactional | `test_wrapper.template.py` + `test_transform_nontransactional.template.py` |
| Glue | Transactional | `test_wrapper.template.py` + `test_transform_transactional.template.py` |
| Databricks | NonTransactional | `test_transform_nontransactional.template.py` + `test_driver.template.py` |
| Databricks | Transactional | `test_transform_transactional.template.py` + `test_driver.template.py` |

### STEP 1 — conftest.py

Generate shared `conftest.py` from `${CLAUDE_PLUGIN_ROOT}/templates/tests/conftest.template.py`:
- Session-scoped `SparkSession` fixture (local[2])
- Mock `GlueContext` (Glue only)
- Mock Databricks foundation library functions (Databricks only)
- Mock factory functions for source DataFrames

### STEP 2 — pytest.ini

Generate `pytest.ini` from `${CLAUDE_PLUGIN_ROOT}/templates/tests/pytest_ini.template`:
```ini
[pytest]
addopts = --cov={{module_name}} --cov-fail-under=90 --cov-report=html
```

### STEP 3 — test_wrapper.py (Glue only)

From `${CLAUDE_PLUGIN_ROOT}/templates/tests/test_wrapper.template.py`:
- Test day0 dispatch instantiates `_transform_day0`
- Test day1/bau dispatch instantiates `_transform_day1`
- Test DTX `param` passed correctly (4-slot comma-delimited)
- Test `business_date` arg overrides `dc.retrieve_date()`
- Test invalid `operation` value raises exception
- Test `dc.update_date_control()` called only on success (not on exception)
- Mock: DTX-injected globals (`glue_read_table`, `glue_read_icb_table`), `SparkSession`, `date_control`, config `environments` section

### STEP 4 — test_transform_{table}.py

Based on table_type:

**NonTransactional** (`test_transform_nontransactional.template.py`):
- Output schema matches all target columns from mapping Excel
- SCD2 merge produces correct row count (inserts new + expires changed)
- `eff_start_date` populated; `eff_end_date = 3499-12-31` for active records
- `active = '1'` for current records; `active = '0'` for expired
- NULL columns handled per `nullable` flag
- Re-run on same business date is no-op (idempotency test)
- If crypto flagged: verify UDF called via `spark.sql()`, not DataFrame API

**Transactional** (`test_transform_transactional.template.py`):
- Output schema matches target columns
- Append-only: no MERGE/UPDATE executed
- Partition column present in output
- No `eff_start_date`/`eff_end_date` columns in output
- If crypto flagged: same spark.sql() verification

### STEP 5 — test_driver.py (Databricks only)

From `${CLAUDE_PLUGIN_ROOT}/templates/tests/test_driver.template.py`:
- `DateControl.insert_date_control_if_missing()` called with correct params
- `AuditLogger.start()` called before transform
- For NonTransactional: `run_cdc()` invoked with correct `unique_keys`
- For Transactional: `hf.write_iceberg_table_append()` called (not `run_cdc`)
- `DateControl.update_date_control()` called on success
- Exception propagated and logged to AuditLogger
- Mock all external dependencies

### STEP 5.5 — test_dag.py (Both Platforms — Gated)

**Gate condition:** Run ONLY if `session/dag_spec.json` exists (i.e., `/gen-dag` was executed). Skip entirely if no DAGs were generated.

From `${CLAUDE_PLUGIN_ROOT}/templates/tests/test_dag.template.py`:

For each table in `session/dag_spec.json`:

**5.5.1 — Resolve basic placeholders:**
1. Resolve `{{dag_id}}` from `dag_spec.tables[].dag_id`
2. Resolve `{{dag_filename}}` from the DAG output file name (e.g., `buk_fdpmortgage_account_wm_dag.py` for Databricks, `fdp_uk_mortgage_db_account_wm_dag.py` for Glue)
3. Resolve `{{platform}}` from `dag_spec.platform`
4. Generate test file at `generated/{platform}/tests/unit/test_{dag_id}.py`

**5.5.2 — Resolve DAG-specific placeholders from `dag_spec.json`:**

| Placeholder | Source | Notes |
|---|---|---|
| `{{schedule_type}}` | `dag_spec.schedule.schedule_type` | One of: `cron`, `business_calendar`, `adhoc` |
| `{{cron_expression}}` | `dag_spec.schedule.cron_expression` | Only when schedule_type=cron |
| `{{schedule_hour}}` | `dag_spec.schedule.schedule_hour` | Only when schedule_type=business_calendar |
| `{{schedule_minute}}` | `dag_spec.schedule.schedule_minute` | Only when schedule_type=business_calendar |
| `{{catchup}}` | `dag_spec.schedule.catchup` | Boolean: `True` or `False` |
| `{{skip_bank_holidays}}` | `dag_spec.schedule.skip_bank_holidays` | Boolean |
| `{{has_dependencies}}` | `len(dag_spec.tables[0].dependencies) > 0` | Boolean |
| `{{has_dynamodb}}` | any dep with `orchestration_type == "dynamodb"` | Boolean |
| `{{has_dag_sensor}}` | any dep with `orchestration_type == "dag_sensor"` | Boolean |
| `{{has_cross_deployment}}` | any dep with `orchestration_type == "cross_deployment"` | Boolean |
| `{{expected_job_name}}` | `dag_spec.tables[0].databricks_config.job_name` | Databricks only |
| `{{expected_process_name}}` | `dag_spec.tables[0].process_name` | Both platforms |
| `{{expected_lambda_function_name}}` | `dag_spec.tables[0].glue_config.lambda_function_name` | Glue only |

**5.5.3 — Evaluate conditional blocks:**

The DAG test template uses comment-delimited conditional blocks:
```python
# {{#if_<condition>}}
... test class or method ...
# {{/if_<condition>}}
```

For each conditional block:
- If the condition evaluates to **true** → strip the `# {{#if_*}}` and `# {{/if_*}}` marker lines, keep the content between them.
- If the condition evaluates to **false** → remove the entire block (marker lines AND content).

**Supported conditions:**

| Condition | True When |
|---|---|
| `if_platform_databricks` | `dag_spec.platform == "databricks"` |
| `if_platform_glue` | `dag_spec.platform == "glue"` |
| `if_schedule_cron` | `dag_spec.schedule.schedule_type == "cron"` |
| `if_schedule_business_calendar` | `dag_spec.schedule.schedule_type == "business_calendar"` |
| `if_schedule_adhoc` | `dag_spec.schedule.schedule_type == "adhoc"` |
| `if_has_dependencies` | `len(dag_spec.tables[0].dependencies) > 0` |
| `if_has_dynamodb` | any dependency with `orchestration_type == "dynamodb"` |
| `if_has_dag_sensor` | any dependency with `orchestration_type == "dag_sensor"` |
| `if_has_cross_deployment` | any dependency with `orchestration_type == "cross_deployment"` |
| `if_skip_bank_holidays_true` | `schedule_type == "cron" AND skip_bank_holidays == true` |
| `if_skip_bank_holidays_false_and_cron` | `schedule_type == "cron" AND skip_bank_holidays == false` |

**Nesting rule:** Nested conditions (e.g., `if_has_dynamodb` inside `if_has_dependencies`) are evaluated independently. If the outer condition is false, the entire outer block including all nested blocks is removed.

**Test coverage targets (12 test classes, conditionally included):**

| Test Class | Condition | Validates |
|---|---|---|
| `TestDagSyntax` | Always | File exists, syntax valid, no `{{placeholder}}` |
| `TestDagStructure` | Always | DAG ID, retries=0, timezone, DAG(), default_args, TaskGroup |
| `TestDagDependencies` | Always | Task wiring, no circular imports |
| `TestPlatformOperators` | Platform-branched | Correct operators present; wrong-platform absent |
| `TestScheduleType` | Schedule-type-branched | Cron/timetable/None schedule config |
| `TestSensorConfiguration` | `has_dependencies` | poke_interval < timeout per sensor type |
| `TestDynamoDBSensor` | `has_dynamodb` | Sensor class, poke method, entry key format |
| `TestCrossDeploymentSensor` | `has_cross_deployment` | Sensor class, requests import, API token |
| `TestExternalTaskSensor` | `has_dag_sensor` | ExternalTaskSensor, execution_date_fn_factory |
| `TestConfHelpers` | `has_dependencies` | _should_wait, _should_skip functions |
| `TestTasksConfig / TestGlueConfig` | Platform-branched | TASKS_CONFIG keys/values or Glue config vars |
| `TestHolidayCheck / TestHolidayCheckNotPresent` | `skip_bank_holidays` + `cron` | ShortCircuit or EmptyOperator |
| `TestDateControl` | Schedule-type-branched | calculate_business_dates, XCom push, conf override |
| `TestGlueHelpers` | `platform=glue` | Lambda payload, SFN ARN, GlueJobDetailsSensor, task chain |

---

## Placeholder Resolution (Phase 2: Auto-Resolve)

**BEFORE Generation** (pre-flight check):
- If crypto enabled: Check `crypto_flags.custom_de_list` for completeness
  - If empty and crypto columns exist: ⛔ HALT

**AFTER Generation** (post-generation validation):
- Scan test files for `\{\{[a-z_]+\}\}` patterns
- Verify no blocking placeholders remain
- For {{custom_de_list}}: If used in crypto tests, verify DE names are injected
- Update `session/placeholders.json` with test generation status

**Reference**: See `validators/placeholder-auto-resolver.helper.md` for detailed logic

| Placeholder | Type | Source | Resolution |
|---|---|---|---|
| `{{custom_de_list}}` | Blocking (if crypto) | crypto_flags.json | Extract DE names for mock setup — ⛔ HALT if empty + crypto |

## Output Files

**Glue** (`generated/glue/tests/`):
- `generated/glue/tests/conftest.py`
- `generated/glue/tests/pytest.ini`
- `generated/glue/tests/unit/test_wrapper_{db}_{table}.py`
- `generated/glue/tests/unit/test_transform_{db}_{table}.py`
- `generated/glue/tests/unit/test_{dag_id}.py` (if DAGs generated)

**Databricks** (`generated/databricks/tests/`):
- `generated/databricks/tests/conftest.py`
- `generated/databricks/tests/pytest.ini`
- `generated/databricks/tests/unit/test_transform_{db}_{table}.py`
- `generated/databricks/tests/unit/test_driver_{db}_{table}.py`
- `generated/databricks/tests/unit/test_{dag_id}.py` (if DAGs generated)

Create directory `generated/{platform}/tests/unit/` if it does not exist.

Multi-source-system (when `data_flow_detection.source_systems` is non-empty — one test file per source_system):
- Glue: `test_wrapper_{db}_{table}_{source_system}.py`, `test_transform_{db}_{table}_{source_system}.py`
- Databricks: `test_transform_{schema}_{table}_{source_system}.py`, `test_driver_{schema}_{table}_{source_system}.py`

### Multi-Source-System Awareness

Read `session_state.data_flow_detection`:

- **`source_systems` is non-empty**: Generate N test files per source_system:
  - Databricks: `tests/unit/test_transform_{schema}_{table}_{source_system}.py`, `test_driver_{schema}_{table}_{source_system}.py`
  - Glue: `tests/unit/test_wrapper_{db}_{table}_{source_system}.py`, `tests/unit/test_transform_{db}_{table}_{source_system}.py`
  - DAG tests: `test_{dag_id}.py` (DAG ID already includes source_system from /gen-dag)
  - Each test file imports and tests only its source_system-specific transform/driver/wrapper
- **`"combined"` or `source_systems` is empty**: Unchanged.

**Session State:**
- `session/audit_log.jsonl` (new entry)
- `session/placeholders.json` (updated with {{custom_de_list}} status if crypto)

### Context Checkpoint Write — `post_generation` (Full-Automation Only)

`/gen-tests` is the FINAL generation command in the auto-chain. After successful completion, if `session_state.auto_chain.enabled == true`, write the cumulative `chain_checkpoints.post_generation` to `session/session_state.json`:

```json
{
  "chain_checkpoints": {
    "post_generation": {
      "generated_files": ["generated/glue/transforms/...", "generated/glue/wrapper/...", "..."],
      "crypto_applied": ["col1", "col2"],
      "template_versions_used": {
        "transform": "test_transform_nontransactional.template.py",
        "wrapper": "wrapper_py_per_table.template.py"
      },
      "artefact_count": N,
      "platform": "glue|databricks",
      "timestamp": "<ISO 8601>"
    }
  }
}
```

This checkpoint captures ALL generated files across prior generation commands (transform, wrapper, mesh, dtxog, driver, ddl, tests). Downstream `/validate` and `/push` load this for reliable artifact tracking across compaction boundaries.

**How to populate `generated_files`:** Read `session/session_state.json` → collect all paths from `phases[*].output_files` where phase status = "completed".

---

## STEP 6 — Syntax Validation (Non-Blocking)

After all test files are generated, validate Python syntax using `py_compile` (stdlib — no pip dependencies).

### Pre-conditions

**Python guard** — follow `agents/refs/python-runtime-contract.md § Guard Pattern`.
If `python_path == null`: set `syntax_check_result = "skipped_no_python"`, log to audit, CONTINUE.

### If `python_path` available:

For each generated `.py` file produced by this command (all `test_*.py` and `conftest.py` in `generated/{platform}/tests/`):

Run via Bash tool:
```bash
{python_path} -m py_compile "{file_path}" 2>&1
```

**If ALL files pass (exit code 0 for each):**
```
✅ Syntax check passed ({N} test files)
```
Set `session_state.syntax_check_result = "passed"`. Set `session_state.syntax_check_failures = null`.

**If ANY file fails:**
```
⚠️ Syntax errors detected (non-blocking):
   • {file_path}: {error message from py_compile}
   ...
```
Set `session_state.syntax_check_result = "failed"`. Set `session_state.syntax_check_failures = ["{file1}", "{file2}", ...]`.

Log to `session/audit_log.jsonl`: `[SYNTAX-CHECK] {result} — {N} files checked, {M} failures`. CONTINUE (non-blocking).

---

## STEP 7 — Optional Test Execution (Non-Blocking)

After syntax validation, optionally execute the generated test suite using `pytest`.

### Pre-conditions

**Python guard** — follow `agents/refs/python-runtime-contract.md § Guard Pattern`.
If `python_path == null`: set `test_execution_result = "skipped_no_python"`, log to audit, CONTINUE.

### If `python_path` is available:

#### Step 7.1 — Dependency Check (Non-Blocking)

Run via Bash tool:
```bash
{python_path} -m pytest --version 2>/dev/null
```

- If exit code != 0 (pytest not installed):
  ```
  ⚠️ pytest not installed in the detected Python environment ({python_path}).
     Generated tests saved to {test_dir} but NOT executed.
     
     To install: {python_path} -m pip install pytest pytest-cov pyspark
  ```
  Log: `[TEST-EXEC] Skipped — pytest not installed`. Set `session_state.test_execution_result = "skipped_no_pytest"`. CONTINUE.

- If exit code == 0 (pytest available): proceed to Step 7.2.

#### Step 7.2 — Execute Tests

**In full-automation mode** (`session_state.auto_chain.enabled == true`): Execute automatically (no user prompt).

**In interactive mode** (`auto_chain` is null or `enabled == false`): Ask user:
```
pytest is available. Run generated tests now? [Y/n]
```
- If user declines: set `session_state.test_execution_result = "skipped_user_declined"`. CONTINUE.
- If user accepts (or full-automation): proceed to execution.

**Execution command:**
```bash
{python_path} -m pytest {test_dir} --tb=short -q 2>&1
```

**Timeout:** 120 seconds. If timeout → set `session_state.test_execution_result = "timeout"`, WARN and CONTINUE.

#### Step 7.3 — Report Results

**If all tests pass (exit code == 0):**
```
✅ Test execution PASSED
   {N} tests collected, {N} passed in {T}s
```
Set `session_state.test_execution_result = "passed"`. Set `session_state.test_execution_output = null`.

**If tests fail (exit code != 0):**
```
⚠️ Test execution completed with FAILURES (non-blocking)
   {summary line from pytest output}
   
   This does NOT block generation. Review failures before /push:
     {python_path} -m pytest {test_dir} --tb=long
```
Set `session_state.test_execution_result = "failed"`. Store first 50 lines of pytest output in `session_state.test_execution_output`.

Log to `session/audit_log.jsonl`: `[TEST-EXEC] {result} — {N} tests, exit_code={code}`.

**CRITICAL:** Test execution failure does NOT halt the pipeline, even in full-automation mode. The `/push` quality gate (Condition 4) is the authoritative test gate.

---

## Coverage Requirement

Build fails if any file falls below 90% coverage threshold. All external dependencies must be mocked.

## Failure Modes

- ⛔ **{{custom_de_list}} is empty** (crypto enabled but no DE extraction) → HALT (fail fast)
