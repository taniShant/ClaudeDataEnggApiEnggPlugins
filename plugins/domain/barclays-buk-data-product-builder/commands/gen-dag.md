---
description: Generate Airflow DAG files for scheduling, dependency checks, and job orchestration — Databricks and Glue
disable-model-invocation: false
---

# /gen-dag — Airflow DAG Orchestration Generation

Generate Airflow DAG files for **EACH TARGET TABLE** independently. One DAG per table — no multi-table DAGs.
- Handles scheduling (cron, business calendar, adhoc)
- Resolves upstream dependencies (DynamoDB GCPR, ExternalTaskSensor, CrossDeploymentSensor)
- Computes business date (`curr_bus_dt`) from Airflow `logical_date`
- Triggers Databricks jobs (`DatabricksRunNowOperator`) or Glue jobs (Lambda → Step Function → Glue)
- Supports bank holiday skipping, manual date override, and dependency skip via `dag_run.conf`
- Configurable sensor retry intervals (`SENSOR_CFG`) and sequential processing (`depends_on_past`)

## Output Structure

```
generated/databricks/dags/
├── {tenancy}_{table1}_dag.py             ← One per target table
└── {tenancy}_{table2}_dag.py

generated/glue/dags/
├── {db}_{table1}_dag.py                      ← One per target table
└── {db}_{table2}_dag.py

session/
└── dag_spec.json                             ← Resolved DAG configuration (schedule, deps, platform config)
```

Create directory `generated/databricks/dags/` (Databricks) or `generated/glue/dags/` (Glue) if it does not exist.

Multi-source-system (when `data_flow_detection.source_systems` is non-empty — one DAG per source_system):
```
generated/databricks/dags/
├── {tenancy}_{source_system_1}_{table}_dag.py
└── {tenancy}_{source_system_2}_{table}_dag.py

generated/glue/dags/
├── {db}_{table}_{source_system_1}_dag.py
└── {db}_{table}_{source_system_2}_dag.py
```

### Multi-Source-System Awareness

Read `session_state.data_flow_detection`:

- **`source_systems` is non-empty**: Generate N DAGs (one per source_system):
  - **Databricks**: Output: `generated/databricks/dags/{tenancy}_{source_system}_{table}_dag.py`, DAG ID: `{tenancy}_{source_system}_{table}_dag`
  - **Glue**: Output: `generated/glue/dags/{db}_{table}_{source_system}_dag.py`, DAG ID: `{tenancy}_{source_system}_{table}_dag`
  - Each DAG triggers its source_system-specific job (Databricks notebook job or Glue Lambda → Step Function)
- **`"combined"` or `source_systems` is empty**: Unchanged (one DAG per target table).

## Usage

```
/gen-dag                                      # Interactive — prompts for schedule and dependencies
/gen-dag --schedule-type business_calendar    # Pre-select schedule type
/gen-dag --full-automation                    # Resolve everything from domain knowledge, halt if ambiguous
```

## Prerequisites

- G1 (platform) resolved
- **Databricks**: `/gen-bundle` completed (`session_state.bundle_generated == true`)
- **Glue**: `/gen-dtxog` completed (DTXOG config JSON exists for each target table in `generated/glue/`)

## STEP 0.0 — Chain Mode Output Compression

Apply `commands/refs/chain-mode-compression.md`. Compact return:
```
[gen-dag] ✓ Generated {n} DAG file(s) for {platform} | Checkpoint: post_dag updated
```

## STEP 0.5 — Read Templates (BLOCKING — Composable Blocks)

Templates use a **composable block architecture**. Read the skeleton + conditional blocks based on platform, schedule_type, and resolved dependencies:

### Skeleton (always read ONE based on platform + schedule_type):
- `${CLAUDE_PLUGIN_ROOT}/templates/dags/skeletons/{platform}_{schedule_type}.template.py`

### Blocks (read from `${CLAUDE_PLUGIN_ROOT}/templates/dags/blocks/`):

| Block | Condition |
|---|---|
| `imports_core.py` | Always |
| `imports_databricks.py` | platform=databricks |
| `imports_glue.py` | platform=glue |
| `imports_sensors.py` | Any external dep (dag_sensor, cross_deployment, dynamodb) |
| `imports_dynamodb.py` | Any dynamodb dep |
| `imports_timetable.py` | schedule_type=business_calendar |
| `conf_helpers.py` | Any external dep |
| `date_control.py` | schedule_type=cron or business_calendar |
| `date_control_adhoc.py` | schedule_type=adhoc |
| `holiday_check.py` | skip_bank_holidays=true AND schedule_type=cron |
| `bank_holidays_data.py` | skip_bank_holidays=true OR schedule_type=business_calendar |
| `dynamodb_sensor.py` | Any dynamodb dep |
| `cross_deployment_sensor.py` | Any cross_deployment dep |
| `external_dag_functions.py` | Any dag_sensor or cross_deployment dep |
| `taskgroup_databricks.py` | platform=databricks AND schedule_type=cron |
| `taskgroup_databricks_selfcontained.py` | platform=databricks AND schedule_type != cron |
| `taskgroup_glue.py` | platform=glue |
| `glue_helpers.py` | platform=glue |
| `glue_job_sensor.py` | platform=glue |
| `dag_wiring_with_deps.py` | platform=databricks AND any external dep |
| `dag_wiring_glue.py` | platform=glue AND (SOURCES_DB_TABLE_DETAILS or EXTERNAL_DAG_IDS non-empty) |

The agent assembles skeleton + blocks into a single self-contained `.py` output file. See `agents/dag-generator-agent.md` for assembly order.

---

## Behaviour

### STEP 1 — Resolve DAG Configuration (Gate G6)

#### 1.1 One DAG Per Table (Mandatory)

Every target table gets its own independent DAG file — no multi-table DAGs.
This simplifies dependency management, debugging, and independent re-runs.

#### 1.2 Resolve Schedule
Priority: Domain Knowledge > Additional Context hints > Gate G6 prompt
- If domain knowledge has "## Airflow DAG Configuration" section → parse it
- If Additional Context contains "schedule:" → extract
- Otherwise → apply **business_calendar auto-selection** (below), then fall back to Gate G6 prompt

**Business Calendar Auto-Selection Rule:**

Auto-select `business_calendar` (without prompting) when ALL three signals are detected from domain knowledge or additional context:

1. **Run cycle is Tue–Sat** (or described as "next business day after processing date")
2. **Bank holidays must be skipped** (explicit or implied by "business days only")
3. **Business date offset is T-1** (one prior calendar/business day)

When auto-selected:
- `schedule_type = "business_calendar"`
- `schedule_hour` / `schedule_minute` = extracted from domain knowledge, or default `6` / `0`
- No `skip_bank_holidays` flag needed — the timetable handles it natively
- No `cron_expression` needed

If fewer than three signals are present → do NOT auto-select. Fall back to Gate G6 prompt:
  ```
  Schedule type? [cron / business_calendar / adhoc]
  If cron: expression? (default "0 6 * * *"), skip bank holidays? [y/n]
  If business_calendar: hour? minute?
  ```

#### 1.2.1 Resolve Sequential Processing

Ask user whether each DAG run should depend on the previous run's success:

```
Sequential processing?
  [Y] Each DAG run waits for the previous run to succeed before starting.
      If Monday fails, Tuesday will not run until Monday is resolved.
  [N] Each DAG run is independent — failures do not block subsequent runs. (default)
```

- If **Y** → `depends_on_past = True`, `wait_for_downstream = True`
- If **N** → `depends_on_past = False`, `wait_for_downstream = False` (default)

Check domain knowledge first for "Sequential" or "depends_on_past" hints. If not found → prompt user.

Store in `dag_spec.schedule.sequential_processing` (boolean, default `false`).

#### 1.3 Resolve External Dependencies (Auto-Detection + Confirmation)

For each source table NOT matched internally:

**Auto-Detect Orchestration Type (Priority Order):**

1. **Base Layer Check** — 100% deterministic
   - Database starts with `e_` → `orchestration_type = "dynamodb"` (NO user input needed)
   - Reason: Base layer is never on Airflow, always uses DynamoDB state tracking

2. **Tenancy Registry Lookup** — 100% deterministic (from aws-tenancy skill)
   - Look up source database in registry's Hive/Iceberg Database column
   - If found:
     - Extract Feature Team Name (e.g., `fdpsavings`, `cdpcustomer`)
     - Compare against `session_state.tenancy_name`:
       - **Same**: `orchestration_type = "dag_sensor"` (same deployment)
       - **Different**: `orchestration_type = "cross_deployment"` (different deployment)
   - If NOT found in registry: → proceed to Domain Knowledge check

3. **Domain Knowledge Declaration**
   - Check `domain knowledge file` for "## Airflow DAG Configuration" section
   - If upstream dependency table listed → use declared `Orchestration` type

4. **Unresolved** → Gate G6 prompts user:
   ```
   Source: {db}.{table} (not found in registry)
   Orchestration type? [1] dynamodb [2] dag_sensor [3] cross_deployment
   (Proceed depends on answer)
   ```

**Confirmation for dag_sensor (same deployment):**
```
Source: fdp_uk_savings_db.savings_account
Detected: dag_sensor (same tenancy: fdpsavings)

Derived DAG ID: buk_fdpsavings_savings_account_dag
Is this correct? [Y / enter actual DAG ID]
```
DAG ID is **confirmed** (not assumed) because teams may use non-standard naming.

**Confirmation for cross_deployment (different deployment):**
```
Source: cdp_uk_customer_db.customer
Detected: cross_deployment (different tenancy: cdpcustomer)

Derived DAG ID: buk_cdpcustomer_customer_dag
Is this correct? [Y / enter actual DAG ID]

Derived deployment tenancy: buk-cdpcustomer-team
Is this correct? [Y / enter actual tenancy name]

API token variable (no default):
Airflow Variable name holding the API token? (e.g., API_TOKEN_CUSTOMER)
```
All three fields **must be confirmed or provided**.

#### 1.4 Confirm with User
Present resolved dependency list:
```
Schedule: cron "0 6 * * 1-5" (skip bank holidays: yes)
DAG files: 1 per table (2 total)

Dependencies:
  balance_journey:
    → fdp_uk_savings_acct_db.savings_account (DAG sensor: buk_fdpsavings_savings_account_dag)
    → fdp_uk_savings_acct_db.savings_account_daily_balance (DynamoDB)
  isa_journey:
    → fdp_uk_savings_acct_db.savings_account (DAG sensor: buk_fdpsavings_savings_account_dag)
    → e_ukba_db.tehisst (DynamoDB)

Confirm? [Y/modify]
```

#### 1.5 Resolve Platform-Specific Config

**Databricks:**
- **connection_id** (DATABRICKS_CONN_ID):
  - Check domain knowledge for "Databricks Connection ID" or "Connection ID"
  - Check additional context
  - If not found → prompt user:
    ```
    Databricks connection ID? (e.g., buk_fdpmortgage_fdp_cicd_dev_sp)
    ```
  - Store in dag_spec.tables[].databricks_config.connection_id

- **itsi_env_var** (ITSI_ENV_VAR) — needed for cron schedule only:
  - If schedule_type != "cron" → skip (not used in business_cal/adhoc templates)
  - Check domain knowledge for "ITSI" or "ITSI_ENV_VAR"
  - If not found → prompt user:
    ```
    ITSI environment variable name? (e.g., FDPMORTGAGE_ITSI)
    ```
  - Store in dag_spec.tables[].databricks_config.itsi_env_var

- **dda_ddb_conn_id** (DDA_DDB_CONN_ID) — needed when any DynamoDB dependency has source_layer != "base":
  - This is the Airflow connection ID for the DDA AWS account DynamoDB.
  - Platform-provided during Airflow setup — NOT derivable from ITSI.
  - Format: `{ITSI}-aws-dda-dtx-{layer}-{2_letter_tenancy_short}` (e.g., `snsvc0076404-aws-dda-dtx-fdp-sv`)
  - Check domain knowledge for "DDA Connection ID" or "DDA DynamoDB Connection"
  - If not found → prompt user:
    ```
    DDA DynamoDB connection ID? (platform-provided, e.g., snsvc0076404-aws-dda-dtx-fdp-sv)
    This is the Airflow connection for FDP/CDP/BDP layer DynamoDB checks.
    ```
  - Store in dag_spec.tables[].databricks_config.dda_ddb_conn_id
  - **Skip this prompt** if no DynamoDB dependencies exist for non-base (FDP/CDP/BDP) layers.
  - Base layer connection (`{ITSI}-aws-raw-ddb-read`) is auto-derived — no user input needed.

**Glue:**

- **Pre-check — env_config completeness**: If `session_state.env_config` is null or empty OR (`session_state.tenancy_resolution_method == "user_provided"` AND `session_state.env_config.questionnaire_turns_completed != 6`) → HALT: `"env_config incomplete — infrastructure questionnaire may not have completed all questions. Re-run /parse-mapping to resolve."`

- **itsi_env_var** (ITSI_ENV_VAR):
  - Check domain knowledge for "ITSI" or "ITSI_ENV_VAR"
  - Check env_config from session_state
  - If not found → prompt user:
    ```
    ITSI environment variable name? (e.g., FDPMORTGAGE_ITSI)
    ```
  - Store in dag_spec.tables[].glue_config.itsi_env_var

- Remaining Glue config fields (lambda_function_name, s3_bucket_pattern, dtxog_config_key, change_request_no, csm_name) are derived from existing session_state.env_config and generated artefact paths — no user prompt needed.

#### 1.6 Artefact Reconciliation (Cross-Artefact Sync Validation)

Before writing dag_spec, validate that resolved DAG configuration is consistent with previously generated artefacts. Mismatches are **errors** unless explicitly noted as warnings.

**Databricks — DAG ↔ job.yml sync**

For each table in dag_spec.tables:

1. **job_name match**: Verify `dag_spec.tables[].databricks_config.job_name` matches the job resource name in `generated/databricks/jobs/{tenancy}_{dp}_jobs/{day0|day1}/{target_schema}_{target_table}_job.yml`
2. **target naming match**: Verify `{target_schema}_{target_table}` in dag_spec matches the job.yml's `task_key` and `notebook_path` segment
3. **base_parameters coverage**: Verify every key in `dag_spec.tables[].job_accepted_params` exists as a `base_parameters` key in the job YAML (cross-check of STEP 1.5)

If any mismatch → WARNING with details (non-blocking — user may have intentionally modified job YAML post-generation).

**Glue — DAG ↔ wrapper.py + DTXOG config sync**

Since gen-dag runs after gen-dtxog (and gen-wrapper), both wrapper.py and DTXOG config are guaranteed to exist. All checks are **mandatory**.

For each table in dag_spec.tables:

1. **wrapper.py exists**: Verify `generated/glue/wrapper/{database_name}_{table_name}/wrapper.py` exists → ERROR if missing
2. **DTXOG config exists**: Verify DTXOG config JSON exists for the target table in `generated/glue/` → ERROR if missing
3. **table naming match**: Verify `database_name` and `table_name` in dag_spec match the wrapper file's class naming pattern (`{database_name}_{table_name}_transform_day0/day1`) → ERROR if mismatch
4. **lambda_function_name consistency**: Verify `dag_spec.tables[].glue_config.lambda_function_name` matches the DTXOG state machine pattern (`dtx-sm-glue-byoc-{tenancy_name}`) → ERROR if mismatch
5. **s3_bucket_pattern consistency**: Verify `dag_spec.tables[].glue_config.s3_bucket_pattern` aligns with the DTXOG `byoc.wrapper-file` and `byoc.package-cnfg` S3 paths → ERROR if mismatch
6. **dtxog_config_key consistency**: Verify `dag_spec.tables[].glue_config.dtxog_config_key` matches the DTXOG config file path pattern → ERROR if mismatch

On ERROR: halt DAG generation for the affected table, report the mismatch, and suggest re-running the upstream command that produced the mismatched artefact.

#### 1.7 Write dag_spec
Write resolved config to `session/dag_spec.json` (schema: `schemas/dag_spec.schema.json`)

### STEP 2 — Template Selection

| Platform | schedule_type | Template |
|----------|--------------|----------|
| databricks | cron | databricks_dag_cron.template.py |
| databricks | business_calendar | databricks_dag_business_cal.template.py |
| databricks | adhoc | databricks_dag_adhoc.template.py |
| glue | cron | glue_dag_cron.template.py |
| glue | business_calendar | glue_dag_business_cal.template.py |
| glue | adhoc | glue_dag_adhoc.template.py |

### STEP 3 — Generate DAG Files

Invoke dag-generator-agent **ONCE per table** (parallel batch, batch_size=3).
Each invocation produces one self-contained DAG file for that table.

This applies to **both Databricks and Glue** — no multi-table DAGs.

### STEP 4 — Validation

For each generated file:
1. No unresolved `{{placeholder}}` patterns
2. Python syntax check (if available): `ast.parse()`
3. DAG ID matches convention
4. `default_args.retries = 0` present
5. Timezone is `Europe/London`

Report results. Failures are WARNINGS (non-blocking) — user reviews manually.

### STEP 5 — Session State Update

```json
{
  "dag_generated": true,
  "dag_config": "{resolved dag_spec summary}",
  "chain_checkpoints": {
    "post_dag": {
      "files_generated": ["path1.py", "path2.py"],
      "schedule_type": "cron",
      "dependency_types_used": ["dynamodb", "dag_sensor"],
      "tables_covered": ["table1", "table2"],
      "timestamp": "ISO8601"
    }
  }
}
```

---

## Output Files

- `generated/{platform}/dags/{dag_id}.py` (per table or multi-table)
- `session/dag_spec.json`
- `session/audit_log.jsonl` (new entry)

## Failure Modes

- Platform not resolved → "Run /init first to select platform."
- Artefacts not generated → "Run /gen-bundle (Databricks) or /gen-dtxog (Glue) first."
- Artefact reconciliation error (Glue) → halt for affected table; re-run upstream `/gen-wrapper` or `/gen-dtxog`
- Artefact reconciliation warning (Databricks) → non-blocking; report field-level details
- Gate G6 unresolvable in full-auto → HALT with `auto_chain.halted_at_command = "/gen-dag"`
- Template file missing → "Template not found: {path}. Plugin installation may be corrupt."

## Full-Automation Mode

- Attempt all resolutions from domain knowledge + defaults
- Raw layer sources (`e_*`) → auto-classify as dynamodb
- Internal deps → auto-detect via set intersection
- If any external dep remains unresolved → HALT
- Otherwise → proceed through STEP 3-5 without confirmation

## Session State Updates

After generation:
```json
{
  "dag_generated": true,
  "dag_config": "{resolved dag_spec summary}",
  "chain_checkpoints": {
    "post_dag": {
      "files_generated": ["path1.py", "path2.py"],
      "schedule_type": "cron",
      "dependency_types_used": ["dynamodb", "dag_sensor"],
      "tables_covered": ["table1", "table2"],
      "timestamp": "ISO8601"
    }
  }
}
```
