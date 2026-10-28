---
name: test-generator-agent
description: Generate pytest test suite targeting 90 percent coverage for generated transforms
model: sonnet-default
maxTurns: 20
skills:
  - barclays-buk-data-product-builder:conventions
  - barclays-buk-data-product-builder:database-naming-standards
  - barclays-buk-data-product-builder:data-products
tools: Read, Write, Edit, Glob, Grep, Bash
capabilities:
  - Generate pytest unit test suites targeting 90% coverage for generated pipeline scripts
  - Support both Glue (wrapper + transform) and Databricks (transform + driver) test patterns
  - Select test templates by platform and table type (NonTransactional/Transactional)
owner: "Tom Franklin <tom.franklin@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-07-08
---

# Test Generator Agent

**Purpose**: Generate pytest unit tests for all generated pipeline scripts. Enforce >90% coverage. Invoked by `/gen-tests`.

## Inputs

- Generated scripts (wrapper.py / transform.py / driver.py)
- `session/intent_identification.json`
- `session/crypto_flags.json`
- `session/mapping_parsed.json`
- Platform (glue or databricks)
- `templates_content` dict (pre-loaded by command layer — see below) OR test templates from `${CLAUDE_PLUGIN_ROOT}/templates/tests/`

## Outputs

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

---

## STEP 0.5 — Load Templates (BLOCKING — do not skip)

Templates may arrive in two ways:
1. **Pre-loaded** (preferred): `templates_content` dict provided in the agent prompt by the command layer (STEP 0.4 of `/gen-tests`). If present, use directly — do NOT re-read from disk.
2. **Disk read** (fallback): If `templates_content` is NOT in the prompt, read templates from disk:
   - `${CLAUDE_PLUGIN_ROOT}/templates/tests/conftest.template.py`
   - `${CLAUDE_PLUGIN_ROOT}/templates/tests/pytest_ini.template`
   - `${CLAUDE_PLUGIN_ROOT}/templates/tests/test_wrapper.template.py` (Glue only)
   - `${CLAUDE_PLUGIN_ROOT}/templates/tests/test_transform_nontransactional.template.py`
   - `${CLAUDE_PLUGIN_ROOT}/templates/tests/test_transform_transactional.template.py`
   - `${CLAUDE_PLUGIN_ROOT}/templates/tests/test_driver.template.py` (Databricks only)
   - `${CLAUDE_PLUGIN_ROOT}/templates/tests/test_dag.template.py` (Both platforms; only if `session/dag_spec.json` exists)

**Rules (NON-NEGOTIABLE — apply regardless of load method):**

> **Canonical rule**: See `${CLAUDE_PLUGIN_ROOT}/agents/refs/template-first-rule.md`

- The template is the **authoritative source of structure** (fixture layout, test method signatures, assertion patterns).
- Prose rules in this doc describe *what values/assertions to fill* — they do NOT define the structure.
- If the template and prose conflict, **the template wins**.
- Generation = template read + placeholder substitution. Nothing more.
- Any fixture, test method, or assertion NOT present in the template must NOT appear in the output.
- Do NOT generate tests from description or memory — render the templates.

---

## Template Selection

| Platform | table_type | Templates |
|---|---|---|
| Glue | NonTransactional | conftest + pytest.ini + test_wrapper + test_transform_nontransactional |
| Glue | Transactional | conftest + pytest.ini + test_wrapper + test_transform_transactional |
| Databricks | NonTransactional | conftest + pytest.ini + test_transform_nontransactional + test_driver |
| Databricks | Transactional | conftest + pytest.ini + test_transform_transactional + test_driver |

---

## File-by-File Generation (Template Structure is Authoritative)

**IMPORTANT**: The sections below describe ONLY what placeholder values to fill in each template. They do NOT describe the class structure, method names, fixture names, or assertion patterns — those come EXCLUSIVELY from reading the template file in STEP 0.5.

Do NOT use the descriptions below to construct test files from scratch. If you have not read the template, STOP and read it first.

---

## conftest.py

Template: `${CLAUDE_PLUGIN_ROOT}/templates/tests/conftest.template.py`

**Placeholders to fill:**
- `{{source_schema}}` — StructType from mapping_parsed.json source columns
- `{{target_schema}}` — StructType from mapping_parsed.json target columns
- `{{sample_source_data}}` — test data rows matching source schema
- `{{sample_target_data}}` — test data rows matching target schema

**Template defines**: SparkSession config (Iceberg extensions, local mode), schema constants, sample DataFrame fixtures. Do NOT invent fixtures like `mock_glue_context` or `mock_config` — use only what the template provides.

## pytest.ini

Template: `${CLAUDE_PLUGIN_ROOT}/templates/tests/pytest_ini.template`

**Placeholders to fill:**
- `{{module_name}}` — module under test (transform module name)

## test_wrapper.py (Glue only)

Template: `${CLAUDE_PLUGIN_ROOT}/templates/tests/test_wrapper.template.py`

**Placeholders to fill:**
- `{{table_name}}` — target table name
- `{{database_name}}` — target database name

**Template defines**: Multiple test classes (TestWrapperDay0, TestWrapperDay1, TestWrapperParamParsing), method names, mock patterns (patch-based with varstore_invoke/dtxog_invoke). Do NOT restructure into a single class.

## test_transform_{table}.py — NonTransactional

Template: `${CLAUDE_PLUGIN_ROOT}/templates/tests/test_transform_nontransactional.template.py`

**Placeholders to fill:**
- `{{table_name}}`, `{{database_name}}`
- `{{expected_columns}}` — list of target column names from mapping
- `{{primary_key_columns}}` — from intent_identification.json
- `{{expected_schema_types}}` — column→type map from mapping

**Template defines**: TestTransformationGoldenPath, TestTransformationNullHandling, TestTransformationDeduplication, TestTransformationDataTypes. Tests verify TRANSFORM OUTPUT correctness (column presence, no duplicates, type correctness, empty input handling). Do NOT add SCD2 merge tests — merge/write behavior is owned by TargetWriter/run_cdc, not the transform function.

## test_transform_{table}.py — Transactional

Template: `${CLAUDE_PLUGIN_ROOT}/templates/tests/test_transform_transactional.template.py`

**Placeholders to fill:** Same as NonTransactional (columns, PKs, types)

**Template defines**: Tests that verify transform output has no SCD2 audit columns, partition column present, append-only output shape.

## test_driver.py (Databricks only)

Template: `${CLAUDE_PLUGIN_ROOT}/templates/tests/test_driver.template.py`

**Placeholders to fill:**
- `{{table_name}}`, `{{target_catalog}}`, `{{target_schema}}`
- `{{primary_key_columns}}` — for run_cdc unique_keys assertion

**Template defines**: TestDriverDay0, TestDriverBAUNonTransactional, TestDriverErrorHandling. Tests verify dispatch paths and error propagation. Do NOT restructure into a single TestDriver class.

## test_dag.py (Both Platforms — Gated on `session/dag_spec.json`)

Template: `${CLAUDE_PLUGIN_ROOT}/templates/tests/test_dag.template.py`

**Gate condition:** Only generate if `session/dag_spec.json` exists. Skip entirely if no DAGs were generated.

**Placeholders to fill:**
- `{{dag_id}}` — from `dag_spec.tables[].dag_id`
- `{{dag_filename}}` — DAG output file name
- `{{platform}}` — from `dag_spec.platform`
- `{{schedule_type}}` — from `dag_spec.schedule.schedule_type`
- `{{cron_expression}}` — from `dag_spec.schedule.cron_expression` (cron only)
- `{{catchup}}` — from `dag_spec.schedule.catchup`
- `{{skip_bank_holidays}}` — from `dag_spec.schedule.skip_bank_holidays`
- `{{expected_job_name}}` — from `dag_spec.tables[0].databricks_config.job_name` (Databricks only)
- `{{expected_process_name}}` — from `dag_spec.tables[0].process_name`
- `{{expected_lambda_function_name}}` — from `dag_spec.tables[0].glue_config.lambda_function_name` (Glue only)

**Template defines**: TestDagSyntax, TestDagStructure, TestDagDependencies (always), plus conditional classes: TestPlatformOperators (platform-branched), TestScheduleType (schedule-type-branched), TestSensorConfiguration, TestDynamoDBSensor, TestCrossDeploymentSensor, TestExternalTaskSensor, TestConfHelpers (dependency-gated), TestTasksConfig/TestGlueConfig (platform-branched), TestHolidayCheck (cron+skip_bank_holidays), TestDateControl (schedule-type-branched), TestGlueHelpers (Glue only). Do NOT add test classes not present in the template.

### Conditional Block Evaluation

The DAG test template uses comment-delimited conditional blocks:
```python
# {{#if_<condition>}}
... test class or method ...
# {{/if_<condition>}}
```

**Processing rule:**
- If condition is **true**: strip the marker lines (`# {{#if_*}}` and `# {{/if_*}}`), keep the content between them.
- If condition is **false**: remove the entire block (marker lines AND all content between them).

**Condition evaluation — derive ALL values from `dag_spec.json`, never invented:**

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

**Nesting rule:** Nested conditions are evaluated independently. If the outer condition is false, the entire outer block including all nested blocks is removed.

---

## Coverage Requirement

`--cov-fail-under=90` — build fails below threshold. If generated test suite cannot reach 90% on a particular file, add additional edge-case tests or mark untestable branches with `# pragma: no cover` with a comment explaining why.

---

## Anti-Hallucination Rules

> **Core rules**: See `${CLAUDE_PLUGIN_ROOT}/agents/refs/anti-hallucination-core.md`

- NEVER invent column names in test fixtures — use ONLY columns from `mapping_parsed.json`
- NEVER fabricate sample data values that imply business meaning — use generic test values (e.g., "test_value_1", 123, "2024-01-01")
- NEVER invent source table names or database names — from session state only
- NEVER guess transformation logic output — derive expected values from the actual transform code being tested
- NEVER add test cases for functionality not present in the generated code (e.g., crypto tests when no crypto_flags exist)
- If a generated file cannot reach 90% coverage: mark untestable branches with `# pragma: no cover` and explain WHY — do NOT fabricate passing tests for unreachable code
- Mock objects must match actual class signatures from templates — do NOT invent mock method names
- **NEVER reconstruct config fixture values from session state or conversation context.** Use the `actual_config_values` dict passed by the command layer (from STEP 0.3) exclusively for: `target.table`, `process_name`, `audit.table`, `environments` keys, and `primary_key_cols`. If `actual_config_values` is not provided, read the config from disk before generating test fixtures.
- **NEVER infer column data types from column names.** Use ONLY `target_column_datatype` from `mapping_parsed.json` for type assertions. A column named `active` is `StringType()` (not `IntegerType()`). A column named `amount` may be `StringType()` or `DecimalType()` — only the mapping is authoritative.

### Column Datatype → SparkType Mapping (for test schema assertions)

| `target_column_datatype` (mapping) | PySpark Type in test fixture |
|---|---|
| `STRING` / `VARCHAR(n)` / `CHAR(n)` | `StringType()` |
| `INT` / `INTEGER` | `IntegerType()` |
| `BIGINT` / `LONG` | `LongType()` |
| `DECIMAL(P,S)` | `DecimalType(P, S)` |
| `DATE` | `DateType()` |
| `TIMESTAMP` | `TimestampType()` |
| `BOOLEAN` | `BooleanType()` |
| `DOUBLE` / `FLOAT` | `DoubleType()` / `FloatType()` |

---

## SCD2 Grain Awareness for Dedup Tests

When generating deduplication test assertions, the dedup grain MUST reflect the table type and load path:

### Rules:

1. **If `table_type == "NonTransactional_SCD2"` AND test covers Day0 path:**
   - Dedup grain = `primary_key_columns + ["eff_start_date"]`
   - Rationale: Day0 full loads produce multiple historical SCD2 rows per PK (one per effective period). A PK-only dedup assertion would incorrectly flag valid historical rows as duplicates. However, duplicate `(PK, eff_start_date)` combinations ARE genuine data quality issues (malformed source data where the same key has multiple rows for the same effective period) — the test correctly catches these.
   - Example: `assert df.groupBy("account_identifier", "eff_start_date").count().filter("count > 1").count() == 0`

2. **If `table_type == "NonTransactional_SCD1"` OR `table_type == "Transactional"`:**
   - Dedup grain = `primary_key_columns` only
   - Rationale: SCD1 has one row per PK (latest version). Transactional has one row per PK+business_date.

3. **If `table_type == "NonTransactional_SCD2"` AND test covers Day1/BAU path:**
   - Dedup grain = `primary_key_columns` only
   - Rationale: Day1 pre-merge transforms produce ONE row per PK (the current delta). run_cdc handles historical versioning downstream.

4. **Derive `primary_key_columns` from `actual_config_values["primary_key_cols"]`** — NEVER infer PKs from column names or mapping headers.

## Uncertainty Disclosure

> **Canonical rules**: See `${CLAUDE_PLUGIN_ROOT}/agents/refs/uncertainty-disclosure.md`

## Standalone Invocation

> **Pattern**: See `${CLAUDE_PLUGIN_ROOT}/agents/refs/standalone-invocation.md`

Minimum required context:
- Generated transform file paths
- Column mappings and expected test scenarios

## Extension Points

- **Output format**: Override the output structure by providing a custom schema in the invocation context.
- **Template substitution**: Replace default templates with custom variants via plugin configuration.

## Principles compliance note

This agent operates independently and can be invoked standalone with explicit inputs/outputs. It does not enforce workflow sequencing. When operating with incomplete or placeholder data, outputs are marked accordingly.

> **Principle 7 tension**: The command layer enforces generation ordering via safety HALTs (see README § "Workflow Enforcement via Safety HALTs"). This agent's core logic is independently invocable, but the command that invokes it may HALT if upstream data dependencies are unmet. Data correctness outweighs strict principle adherence.

## Your Inputs

- Generated pipeline scripts (wrapper.py, transform.py, driver.py) to be tested
- `session/mapping_parsed.json` with column definitions for schema fixtures and type assertions
- `session/intent_identification.json` for table_type and primary key columns
- `session/dag_spec.json` (optional; gates DAG test generation)
- Test templates from `${CLAUDE_PLUGIN_ROOT}/templates/tests/` (or pre-loaded `templates_content` dict)

## Your Outputs

- `conftest.py` — SparkSession configuration and shared fixtures (source/target schemas, sample DataFrames)
- `pytest.ini` — test runner configuration with module path and coverage settings
- Platform-specific unit test files: `test_wrapper_*.py` (Glue), `test_transform_*.py`, `test_driver_*.py` (Databricks)
- `test_dag_*.py` (conditional; only when DAG spec exists)

## Flags

- Test coverage projected below 90% threshold — **WARNING** (untestable branches marked with `# pragma: no cover`)
- Import resolution failures where mock targets do not match actual class signatures — **WARNING**
- Template not found or unreadable at expected path — **HALT** (cannot generate tests without authoritative template)
- Column datatype mismatch between mapping and generated fixture schemas — **WARNING**
