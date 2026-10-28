---
name: dag-validation-validator
description: Validates generated Airflow DAG files for structural correctness, platform mandates, and cross-artefact consistency
owner: "BUK Data Product Build Assistant"
review_cadence: quarterly
last_reviewed: 2026-09-09
---

**Platform**: Glue + Databricks

# DAG Validation Validator

## Scope

All files in `generated/{platform}/dags/*.py`.

**Gate condition**: Run ONLY if `session/dag_spec.json` exists (confirms `/gen-dag` was executed). Skip entirely if no DAGs were generated.

## Inputs

- `session/dag_spec.json` — resolved DAG configuration (schedule, dependencies, platform config per table)
- `session/session_state.json` — platform, tenancy
- All `generated/{platform}/dags/*.py` files
- Cross-artefact references:
  - Databricks: `generated/databricks/jobs/{tenancy}_{dp}_jobs/{day0|day1}/*.yml` (single-flow) or `generated/databricks/jobs/{tenancy}_{dp}_jobs/{day0|day1}/{source_system}/*.yml` (multi-source-system)
  - Glue: `generated/glue/` (DTXOG configs, wrapper files)

---

## Checks

### R1 — DAG file exists (per table)

For each table in `session/dag_spec.json`.tables, verify the corresponding DAG file exists:
- Databricks: `generated/databricks/dags/{dag_id}.py`
- Glue: `generated/glue/dags/{db}_{table}_dag.py`
- Multi-source-system: one DAG file per source_system — Databricks: `{tenancy}_{source_system}_{table}_dag.py`, Glue: `{db}_{table}_{source_system}_dag.py`

| Condition | Severity |
|-----------|----------|
| dag_spec entry exists but DAG file missing | **BLOCKING** |
| `session/dag_spec.json` does not exist | SKIP entire validator |

### R2 — No unresolved placeholders

Scan each DAG file for `{{` patterns. Any remaining `{{placeholder}}` tokens indicate incomplete generation.

| Condition | Severity |
|-----------|----------|
| `{{` pattern found in DAG file | **BLOCKING** |

> **Note**: Also covered by `placeholder-completeness-validator` in Batch 3. This check is defense-in-depth specifically scoped to DAG files.

### R3 — retries = 0 (platform mandate)

Verify each DAG file's `default_args` contains `"retries": 0` (integer zero, not string `"0"`).

| Condition | Severity |
|-----------|----------|
| `retries` not set to `0` | **BLOCKING** |
| `default_args` section missing | **BLOCKING** |

### R4 — Timezone = Europe/London

Verify DAG uses `Europe/London` timezone. Check for:
- `pendulum.timezone("Europe/London")` assignment to `LOCAL_TZ`
- `start_date` created with `tz="Europe/London"` or `tz=LOCAL_TZ`

| Condition | Severity |
|-----------|----------|
| Wrong timezone (not `Europe/London`) | **BLOCKING** |
| No timezone declaration found | **BLOCKING** |

### R5 — DAG ID convention

Verify DAG ID matches naming convention:
- Databricks: `{tenancy}_{table}_dag`
- Glue: `{db}_{table}_dag`
- Multi-source-system: Databricks: `{tenancy}_{source_system}_{table}_dag`, Glue: `{db}_{table}_{source_system}_dag` (when `data_flow_detection.source_systems` is non-empty)

Cross-reference against `dag_spec.tables[].dag_id`.

| Condition | Severity |
|-----------|----------|
| DAG ID does not match convention or dag_spec | WARNING |

### R6 — Python syntax valid

Parse DAG file content using `ast.parse()` (or equivalent). Report any syntax errors.

| Condition | Severity |
|-----------|----------|
| Python syntax error | **BLOCKING** |
| Python not available for `ast.parse()` | WARNING (log: "Syntax validation skipped — Python unavailable") |

### R7 — Sensor timeout > poke_interval

For each sensor defined in the DAG (DynamoDB, ExternalTaskSensor, CrossDeploymentDagSensor), verify:
- `timeout` value > `poke_interval` value
- Both values are positive integers

| Condition | Severity |
|-----------|----------|
| `timeout` ≤ `poke_interval` | WARNING |
| Sensor has no timeout set | WARNING |

### R8 — Cross-artefact consistency (Databricks)

**Skip**: if `session_state.platform != "databricks"`

For each table in dag_spec:
1. Verify `TASKS_CONFIG` `job_name` matches the job resource name in `generated/databricks/jobs/`
2. Verify `job_accepted_params` keys exist as `base_parameters` keys in the corresponding job YAML

| Condition | Severity |
|-----------|----------|
| job_name mismatch | WARNING |
| job_accepted_params key not found in job YAML | WARNING |
| Job YAML file not found | WARNING |

### R9 — Cross-artefact consistency (Glue)

**Skip**: if `session_state.platform != "glue"`

For each table in dag_spec:
1. Verify `lambda_function_name` matches DTXOG state machine pattern (`dtx-sm-glue-byoc-{tenancy}` → lambda `dtx-glue-sm-invoke-{tenancy}`)
2. Verify `s3_bucket_pattern` aligns with DTXOG `byoc.wrapper-file` and `byoc.package-cnfg` S3 bucket segments
3. Verify `dtxog_config_key` matches actual DTXOG config file path in `generated/glue/`

| Condition | Severity |
|-----------|----------|
| lambda_function_name mismatch | WARNING |
| S3 bucket pattern mismatch | WARNING |
| dtxog_config_key does not match actual file path | WARNING |
| DTXOG config file not found | WARNING |

---

## Output Format

Findings follow the standard validator output format:

```json
{
  "validator": "dag-validation-validator",
  "findings": [
    {
      "check": "R3",
      "issue": "default_args.retries is 1, expected 0 (platform mandate)",
      "location": "generated/databricks/dags/buk_fdpmortgage_account_dag.py:45",
      "severity": "BLOCKING",
      "fix": "Set default_args['retries'] = 0. Re-run /gen-dag or edit manually."
    }
  ]
}
```
