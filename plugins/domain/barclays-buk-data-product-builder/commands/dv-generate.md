---
description: Generate validation contracts, plans, and SQL files for data validation
disable-model-invocation: false
argument-hint: [--table <name>] [--checks exact,scd2,null,duplicate,datatype,business] [--mode day0|day1|steady_state] [--env dev|preprd|prd|uat]
---

# /dv-generate — Generate Data Validation SQL

Generate validation SQL for one or all tables in the DV session. Builds validation contracts from mapping data, generates dialect-neutral validation plans via the plan agent, renders SQL via the appropriate dialect renderer, validates generated SQL for safety, and evaluates SQL quality against the validation plan.

## Usage

```
/dv-generate [--table <name>] [--checks exact,scd2,null,duplicate,datatype,business] [--mode day0|day1|steady_state] [--env dev|preprd|prd|uat]
```

## Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--table` | No | all | Generate for specific table only |
| `--checks` | No | all | Comma-separated check categories |
| `--mode` | No | steady_state | SCD2 temporal check mode |
| `--env` | No | `dev` | Databricks only. Target environment for catalog resolution: `dev`, `preprd`, `prd`, `uat`. Determines which Unity Catalog names are embedded in generated SQL. Ignored when engine=athena. |

Mode controls SCD2 checks:
- `steady_state`: SCD2-01 through SCD2-11
- `day0`: Additionally SCD2-12, SCD2-13
- `day1`: Additionally SCD2-14 through SCD2-18

## Prerequisites

- `/dv-init` must have completed (`dv_session_state.json` exists with `dv_init.status == "completed"`)

## Context Management

This command uses **staged loading** to minimize context pressure. Each step loads ONLY its required files. Previously-consumed files are released once their content is fully captured in an output artifact.

### Loading Rules

| Step | Load | Do NOT load yet |
|------|------|-----------------|
| Step 0 | `dv_session_state.json` | Everything else |
| Step 0.5 | `databricks-tenancy` skill, `mapping_parsed.json` (target_database only) | Configs, agent refs, schemas |
| Step 1 | `mapping_parsed.json`, `intent_identification.json`, `crypto_flags.json`, `audit_columns.yaml` | `validation_checks.yaml`, agent refs, SQL patterns, safety/quality rules |
| Step 2 | `validation_checks.yaml`, agent refs per plan agent | SQL patterns, safety/quality rules |
| Step 3 | Dialect-specific SQL patterns (ONE engine only) | Safety/quality rules, unused engine's patterns |
| Step 4/4b | `sql_safety_rules.yaml`, `sql_quality_rules.yaml`, validator specs | Plan agent refs, SQL patterns |

### Release Rules

- **After Step 1**: `mapping_parsed.json`, `intent_identification.json`, and `crypto_flags.json` are fully captured in the validation contract. Do NOT re-read them in Steps 2-5.
- **After Step 2**: `validation_checks.yaml` and `dv-validation-patterns.md` are fully captured in the validation plan. Do NOT re-read them in Steps 3-5.
- **After Step 3**: The generated SQL is already in conversation from rendering. Do NOT re-read SQL files from disk for Step 4 validation — use the content already present. **Exception**: re-read after a self-heal retry that re-generates files.
- **Schema files** (`dv_session_state.schema.json`, `dv_validation_contract.schema.json`, `dv_validation_plan.schema.json`): Load ONLY when writing the corresponding artifact, for post-write structural validation. Do not pre-load at Step 0.

### Multi-Table Isolation

When processing table N (N > 1), prior tables' artifacts are NOT needed:
- Do NOT re-read prior tables' contract, plan, or SQL files
- Each table is processed independently through the full Step 1→4b pipeline
- Only shared context across tables: session state (status tracking) and static reference/config files

## Workflow

### Step 0 — RESOLVE PLUGIN ROOT + LOAD SESSION STATE

1. Check `${CLAUDE_PLUGIN_ROOT}` exists
2. Read `session/dv_session_state.json`
3. Verify `phases.dv_init.status == "completed"`
4. If not: `❌ /dv-init has not been completed. Run /dv-init --engine <engine> first.`
5. Update `phases.dv_generate.status = "in_progress"`
6. **Resolve artifact paths from session state:**
   ```
   source = dv_session_state.source_session_path   # "session/" or "session/dv/"
   mapping_path = ${source}/mapping_parsed.json
   intent_path  = ${source}/intent_identification.json
   ```
   This ensures correct path resolution for both dependent mode (`session/`) and standalone mode (`session/dv/`).

If plugin root is missing, STOP with: "❌ Plugin root not resolved. Ensure barclays-buk-data-product-builder plugin is loaded."

---

### Step 0.5 — RESOLVE DATABRICKS CATALOGS

> **Condition:** Execute ONLY when `dv_session_state.engine == "databricks"`. Skip entirely for `athena`.

See `${CLAUDE_PLUGIN_ROOT}/commands/refs/dv-databricks-catalog-resolution.md` for the full resolution algorithm (environment parsing, source/target catalog resolution via tenancy registry + user fallback, target_schema derivation, catalog resolution gate, and storage in session state).

---

### Step 1 — BUILD VALIDATION CONTRACT

**Pre-condition (Databricks only):** When `engine == "databricks"`:
  Read `dv_session_state.databricks_catalog_resolution`.
  IF null or any of `source_catalog`/`target_catalog`/`target_schema` is null/empty:
    HALT: `❌ Cannot build validation contract: Databricks catalog resolution is missing or incomplete. Re-run /dv-generate with --env <env>.`

For each target table (or the single `--table` if specified):

1. Read `{mapping_path}` (resolved in Step 0) — extract ONLY: `target_database`, `target_table`, `columns[]` (with `source_references`, `transformation_logic`, `transformation_type`), `table_description`, `additional_context`. **Ignore `source_volumetrics`** — volumetric data is not used in validation contract or SQL generation.
2. Read `{intent_path}` (resolved in Step 0) — extract `table_type`, `primary_keys`, `partition_column`
3. Read `${CLAUDE_PLUGIN_ROOT}/configs/sttm/audit_columns.yaml` — identify audit columns by `table_type`
4. Read `{source}/crypto_flags.json` (resolved from `source_session_path`) — identify crypto-flagged columns for `is_crypto` marking in the contract

4. **table_type normalization (MANDATORY):** `mapping_parsed.json` uses short-form lowercase. Apply:
   - `scd2` → `NonTransactional_SCD2`
   - `scd1` → `NonTransactional_SCD1`
   - `transactional` → `Transactional`
   - If already PascalCase → pass through

5. Build contract JSON:
   - `target_database`, `target_table` from mapping
   - `table_type` (normalized)
   - `engine` from session state
   - `primary_key_columns` from intent
   - `columns[]` with `source_database`, `source_table`, `source_column`, `business_logic`, `transformation_type`, `is_audit_column`, `is_crypto`
   - `scd2_metadata` (for SCD2 tables): `eff_start_date_source`, `high_end_date_sentinel` (`"3499-12-31"`), `temporal_boundary_convention` (`"inclusive"`), `close_logic`
   - `audit_columns[]` (from `audit_columns.yaml`)
   - `control_date`: `"{{control_date}}"` (parameterized placeholder)
   - `validation_mode` from `--mode` argument
   - Engine-specific naming fields:
     - **Athena:** `source_database`/`target_database` — use values from `mapping_parsed.json` directly
     - **Databricks:** `source_catalog`/`source_schema`/`target_catalog`/`target_schema` — use **RESOLVED** values from `dv_session_state.databricks_catalog_resolution` (populated in Step 0.5):
       - `source_catalog` = `databricks_catalog_resolution.source_catalog`
       - `source_schema` = per-column from `columns[].source_database` in mapping (for the contract-level field, use the primary source table's database)
       - `target_catalog` = `databricks_catalog_resolution.target_catalog`
       - `target_schema` = `databricks_catalog_resolution.target_schema`
       - These are actual catalog names (e.g., `077382350852_buk_data_products`), NOT `{{placeholder}}` tokens. They flow through the validation plan to the renderer, which embeds them directly in SQL.

6. Write `session/dv_validation_contract_{table}.json`

### Step 2 — GENERATE VALIDATION PLAN

For each table:

Delegate to `dv-validation-plan-agent` with:
- Input: `session/dv_validation_contract_{table}.json`
- Config: `${CLAUDE_PLUGIN_ROOT}/configs/dv/validation_checks.yaml`
- Audit columns: `${CLAUDE_PLUGIN_ROOT}/configs/sttm/audit_columns.yaml`
- Check filter: `--checks` argument (if provided)
- Output: `session/dv_validation_plan_{table}.json`

**Error handling**: If the plan agent fails for a table:
1. Log the error to `session/audit_log.jsonl` with `"status": "failed"` and the error message
2. Update `session_state.tables[]` for the failed table with `plan_path: null` and record the error
3. **Continue** with remaining tables — a single table failure does not halt the entire batch
4. If ALL tables fail plan generation: set `phases.dv_generate.status = "failed"` and HALT

### Step 3 — RENDER SQL

> **ENGINE GUARD**: Load ONLY the renderer agent and SQL patterns file for the session engine. Never load both `dv-athena-sql-patterns.md` AND `dv-databricks-sql-patterns.md` in the same run.

For each table that has a successful validation plan (`plan_path` is not null):

Based on engine from session state:
- `athena` → Delegate to `dv-athena-renderer-agent` with validation plan
  - Output directory: `generated/glue/validation/{db}_{table}/`
  - Files: `{db}_{table}_validation.sql`, `{db}_{table}_results_summary.sql`
- `databricks` → Delegate to `dv-databricks-renderer-agent` with validation plan
  - Output directory: `generated/databricks/validation/{db}_{table}/`
  - Files: `{db}_{table}_validation.sql`, `{db}_{table}_results_summary.sql`

**Error handling**: If the renderer agent fails for a table:
1. Log the error to `session/audit_log.jsonl` with `"status": "failed"` and the error message
2. Update `session_state.tables[]` for the failed table with `sql_directory: null` and record the error
3. **Continue** with remaining tables — a single table failure does not halt the batch
4. If ALL tables fail rendering: set `phases.dv_generate.status = "failed"` and HALT

### Step 4 — SQL SAFETY VALIDATION

For each generated SQL file:

Invoke `dv-sql-safety-validator` (inline, not a separate agent):
1. Read SQL file
2. Strip comments (`--` and `/* */`) before regex matching
3. Apply safety rules from `${CLAUDE_PLUGIN_ROOT}/configs/dv/sql_safety_rules.yaml`
4. On BLOCKING violation: attempt self-heal (re-invoke renderer with violation context)
5. Up to 2 retries before final HALT

```
⛔ SQL safety violation in {file}:
   SAFETY-02: DML statement detected: 'MERGE'
   Line 45: ... MERGE INTO ...
   
   Attempting self-heal (retry 1/2)...
```

### Step 4b — SQL QUALITY VALIDATION

For each table that passed safety validation (Step 4):

Invoke `dv-sql-quality-validator` (inline, not a separate agent):
1. Read rendered SQL files from Step 3 output (post-safety-heal)
2. Read validation plan JSON from Step 2 output (`session/dv_validation_plan_{table}.json`)
3. Read validation contract JSON from Step 1 output (`session/dv_validation_contract_{table}.json`)
4. Read engine from session state
5. Apply quality rules from `${CLAUDE_PLUGIN_ROOT}/configs/dv/sql_quality_rules.yaml`
6. On BLOCKING violation: attempt self-heal (re-invoke renderer with violation context + plan JSON)
7. Up to 2 retries; re-run Step 4 (safety) after any re-render to maintain safety guarantee
8. After 2 retries: set `dv_quality_validation_result = "failed"`, continue to Step 5 (do NOT halt)

```
⚠️ Quality violation in {file}:
   QUALITY-01: Plan check ER-05 not found in rendered SQL
   Expected: Comment header "-- ER-05:" in SQL file
   
   Attempting self-heal (retry 1/2)...
```

Quality validation produces three session state fields: `dv_quality_validation_result`, `dv_quality_violations`, `dv_quality_coverage_summary` (see `dv-sql-quality-validator.md` for details).

**Key difference from Step 4**: Quality blocker failures do NOT halt the pipeline. Artifacts are written with a prominent warning — the SQL may be functionally correct even if imperfect.

### Step 5 — WRITE ARTIFACTS + UPDATE SESSION STATE

1. Update session state `tables[]` with `contract_path`, `plan_path`, `sql_directory`, `check_count`, `not_evaluated_count`
2. Create `.dv_manifest.json` in session directory:
```json
{
    "session_id": "dv_20260926_143022",
    "engine": "athena|databricks",
    "target_environment": "dev",
    "catalog_resolution": {
        "source_catalog": "077382350852_buk_data_products",
        "target_catalog": "dev_buk_pafer_bdp",
        "resolution_method": "tenancy_registry"
    },
    "tables": [{
        "target_database": "fdp_uk_mortgage_db",
        "target_table": "mortgage_account",
        "table_type": "NonTransactional_SCD2",
        "contract_path": "session/dv_validation_contract_mortgage_account.json",
        "plan_path": "session/dv_validation_plan_mortgage_account.json",
        "sql_directory": "generated/glue/validation/fdp_uk_mortgage_db_mortgage_account/",
        "sql_files": ["..._validation.sql", "..._results_summary.sql"],
        "check_count": 28,
        "not_evaluated_count": 2,
        "safety_validation_result": "passed",
        "quality_validation_result": "passed"
    }],
    "quality_summary": {
        "rules_evaluated": 10,
        "rules_passed": 10,
        "rules_warned": 0,
        "rules_failed": 0,
        "checks_covered": 28,
        "checks_total": 28
    },
    "generated_at": "ISO 8601 timestamp"
}
```
3. Append audit log entries to `session/audit_log.jsonl`:
```jsonl
{"component": "DV-GENERATE", "step": "contract_build", "table": "mortgage_account", "status": "completed", "timestamp": "..."}
{"component": "DV-GENERATE", "step": "plan_generation", "table": "mortgage_account", "checks_generated": 28, "not_evaluated": 2, "timestamp": "..."}
{"component": "DV-GENERATE", "step": "sql_rendering", "table": "mortgage_account", "engine": "athena", "files_written": 2, "timestamp": "..."}
{"component": "DV-GENERATE", "step": "safety_validation", "table": "mortgage_account", "result": "passed", "violations": 0, "timestamp": "..."}
{"component": "DV-GENERATE", "step": "quality_validation", "table": "mortgage_account", "result": "passed", "rules_evaluated": 10, "checks_covered": 28, "checks_total": 28, "timestamp": "..."}
```
4. Update `phases.dv_generate.status = "completed"`
5. Display summary:

```
✅ DV generation complete
   Engine:     {engine} [Databricks: append "(env: {env})" and "Catalogs: source={src}, target={tgt}"]
   Tables processed: {count}
   Total checks:     {n} (ER: {n}, SCD2: {n}, NC: {n}, DC: {n}, DT: {n}, BR: {n})
   NOT_EVALUATED:    {n} ({check_id}: {reason}, ...)
   Safety validation:  {result} ({passed}/{total} rules)
   Quality validation: {result} ({passed}/{total} rules, {covered}/{total} checks covered)
   
   Generated files:
     generated/{platform}/validation/{db}_{table}/
       ├── {db}_{table}_validation.sql
       └── {db}_{table}_results_summary.sql
   
   Next step: Run validation SQL in {engine}, then /dv-report --results <path>
```

Where `{platform}` is `glue` for athena or `databricks` for databricks.

## Output

```
generated/
├── glue/
│   └── validation/
│       └── {db}_{table}/
│           ├── {db}_{table}_validation.sql
│           └── {db}_{table}_results_summary.sql
session/
├── dv_session_state.json (updated)
├── dv_validation_contract_{table}.json
├── dv_validation_plan_{table}.json
├── .dv_manifest.json
└── audit_log.jsonl (appended)
```

## Important Rules

- Contract builds from mapping data only — never fabricate metadata
- `table_type` must be normalized from short-form to PascalCase
- `control_date` is always parameterized, never hardcoded
- Safety validation runs AFTER rendering, BEFORE quality validation
- Quality validation runs AFTER safety, BEFORE final write
- Self-heal up to 2 retries on safety violations before HALT
- Self-heal up to 2 retries on quality violations before accepting failure (no HALT — artifacts written with warning)
