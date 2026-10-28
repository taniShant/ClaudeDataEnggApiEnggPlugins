# Hook: post-generate-validate

**Trigger**: After any generation command (`/gen-*`) completes

**Purpose**: Validate each generated file against its schema. Mark files as `VALIDATED` or `DRAFT_UNVALIDATED` in session state.

**File Discovery Scope**: Search under `generated/` directory (platform-separated subfolders).

---

## Validation Sequence

### Step 1a — Schema / Structure Validation

Apply the appropriate validation rules inline (read generated file, check rules, report pass/fail — these are NOT separate tool invocations):

| Generated File Type | Validator | Pass Status | Fail Status |
|---|---|---|---|
| `*_mesh.json` | `mesh-json-completeness-validator` | VALIDATED | DRAFT_UNVALIDATED |
| `*_dtxog.json` | `dtxog-structure-validator` | VALIDATED | DRAFT_UNVALIDATED |
| `*_table_creation_utility.py` | `iceberg-ddl-validator` (DDL embedded) | VALIDATED | DRAFT_UNVALIDATED |
| `*_dag.py` (in `generated/*/dags/`) | `dag-validation-validator` (R1–R6: file exists, no placeholders, retries=0, timezone, DAG ID, syntax) | VALIDATED | DRAFT_UNVALIDATED |
| Any `*.py` file | `code-quality-validator` (Part A + Part B) | VALIDATED | Flag violations |
| Any config/dtxog JSON | `infrastructure-validator` (Part B) | VALIDATED | Flag violations |

**Rolling deletion note:** `rolling_deletion` validation is now included in: `consistency-validator` (Part F), `cdc-presence-assertion-validator` (Check 8), `scd1-structural-validator` (CHECK 6), `contract-reconciliation-validator` (Check C8). These run as part of their respective batches — no separate post-generate rolling deletion check is needed.

### Step 1b — Template Landmark Preservation (NEW)

After schema validation, run `template-landmark-preservation-validator` on each generated file.

This validator checks that the generated file retains the structural skeleton defined by its source template — function signatures, required keys, import patterns, SQL clauses, etc. If landmarks are missing, the file was likely generated from description instead of the template.

| Generated File Pattern | Landmark Set | Severity |
|---|---|---|
| `generated/glue/wrapper/*_wrapper.py` (includes `*_{source_system}_wrapper.py`) | wrapper.py (6 landmarks) | DRAFT_UNVALIDATED |
| `generated/glue/wrapper/*_config.json` (includes `*_{source_system}_config.json`) | config.json (7 landmarks) | DRAFT_UNVALIDATED |
| `generated/glue/mesh/*_mesh.json` (includes `*_{source_system}_mesh.json`) | mesh.json (8 landmarks) | DRAFT_UNVALIDATED |
| `generated/glue/transforms/*_transform_day0.py`, `*_transform_day1.py` (includes `*_{source_system}_transform_*.py`) | transform-glue (5 landmarks) | DRAFT_UNVALIDATED |
| `generated/databricks/src/Notebooks/{day0\|day1}/{target_schema}_{table}/*_transform.py` | transform-dbx (4 landmarks) | DRAFT_UNVALIDATED |
| `generated/databricks/src/Notebooks/{day0\|day1}/{source_system}/{target_schema}_{table}/*_transform.py` | transform-dbx (4 landmarks) | DRAFT_UNVALIDATED |
| `generated/databricks/src/Notebooks/{day0\|day1}/{target_schema}_{table}/*_driver.py` | driver.py (4 landmarks) | DRAFT_UNVALIDATED |
| `generated/databricks/src/Notebooks/{day0\|day1}/{source_system}/{target_schema}_{table}/*_driver.py` | driver.py (4 landmarks) | DRAFT_UNVALIDATED |
| `generated/databricks/src/Notebooks/{day0\|day1}/{target_schema}_{table}/*_config.yml` | config.yml (3 landmarks) | DRAFT_UNVALIDATED |
| `generated/databricks/src/Notebooks/{day0\|day1}/{source_system}/{target_schema}_{table}/*_config.yml` | config.yml (3 landmarks) | DRAFT_UNVALIDATED |
| `generated/databricks/src/Notebooks/utilities/{target_schema}_table_creation_utility.py` | DDL utility (4 landmarks) | DRAFT_UNVALIDATED |
| `generated/glue/dtxog/*_dtxog.json` | dtxog (5 landmarks) | DRAFT_UNVALIDATED |
| `generated/{platform}/dags/*_dag.py` | dag-skeleton (6 landmarks: `DAG()` instantiation, `default_args` dict, `LOCAL_TZ` assignment, `TASKS_CONFIG`/Glue CONFIG dict, TaskGroup definition, task wiring `>>` block) | DRAFT_UNVALIDATED |
| `generated/{platform}/tests/unit/test_*_dag.py` | test_dag (4 landmarks: `@pytest.mark.dag` decorator, `TestDagSyntax` class, `TestDagStructure` class, `TestDagDependencies` class) | DRAFT_UNVALIDATED |

**On failure**: Reject output, mark DRAFT_UNVALIDATED, emit error with missing landmarks and instruction to re-read template (STEP 0.5).

See `validators/template-landmark-preservation-validator.md` for full landmark definitions.

---

## Placeholder Check

After schema validation, run `placeholder-completeness-validator` on the generated file:
- Zero open placeholders → no action (file may still be VALIDATED)
- Open placeholders found → ensure each is registered in `session/placeholders.json`
- A file with open placeholders is marked as requiring completion — but may still be DRAFT unless schema validation also failed

---

## Session State Update

Write updated `artefact_status` to `session/session_state.json`:
```json
{
  "artefact_status": {
    "{filename}": "VALIDATED"
  }
}
```

---

## User Alert

If any file is `DRAFT_UNVALIDATED`:
> "⚠️ `{filename}` failed validation — marked DRAFT_UNVALIDATED. Run `/validate` for full details."

If all files VALIDATED:
> "✅ All generated artefacts validated successfully."

---

## Audit Log

Write validation results to:
- `session/validation_results.json` (append per-file results)
- `session/audit_log.jsonl` (summary entry with pass/fail counts)
