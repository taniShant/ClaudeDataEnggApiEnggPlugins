---
description: Generate Databricks Asset Bundles (DABs) config, job YAMLs, and utility notebooks — Databricks platform only
disable-model-invocation: false
---

# /gen-bundle

Generate Databricks Asset Bundles (DABs) configuration, per-table job YAMLs, and shared utility notebooks. **Databricks only** — refused for Glue.

## Output Structure

```
generated/databricks/
├── databricks.yml                                       ← DABs bundle config
├── jobs/{tenancy}_{dp_type}_jobs/
│   ├── day0/{target_schema}_{table}_job.yml             ← Per-table Day0 job
│   ├── day1/{target_schema}_{table}_job.yml             ← Per-table Day1 job
│   ├── {target_schema}_table_creation_utility.yml       ← Utility job
│   ├── {target_schema}_date_control_insert_utility.yml  ← Utility job
│   └── {target_schema}_daily_date_control_update_utility.yml ← Utility job
└── src/Notebooks/utilities/
    ├── source_reader.py                                 ← SourceReader class
    ├── target_writer.py                                 ← TargetWriter class
    ├── {target_schema}_table_creation_utility.py        ← DDL execution notebook
    ├── {target_schema}_date_control_insert_utility.py   ← Date control seed
    └── {target_schema}_daily_date_control_update_utility.py ← Manual date advance
```

**Multi-Source-System Output Structure** (when `data_flow_detection.source_systems` is non-empty):
```
generated/databricks/
├── databricks.yml                                                    ← unchanged
├── jobs/{tenancy}_{dp_type}_jobs/
│   ├── day0/{source_system}/{target_schema}_{table}_job.yml          ← per source_system
│   ├── day1/{source_system}/{target_schema}_{table}_job.yml          ← per source_system
│   ├── {target_schema}_table_creation_utility.yml                    ← shared (unchanged)
│   ├── {target_schema}_date_control_insert_utility.yml               ← shared (unchanged)
│   └── {target_schema}_daily_date_control_update_utility.yml         ← shared (unchanged)
└── src/Notebooks/utilities/                                          ← shared (unchanged)
    ├── source_reader.py
    ├── target_writer.py
    ├── {target_schema}_table_creation_utility.py
    ├── {target_schema}_date_control_insert_utility.py
    └── {target_schema}_daily_date_control_update_utility.py
```

## Usage

```
/gen-bundle
```

## Prerequisites

- Platform = Databricks (refuse if Glue)
- `session/mapping_parsed.json` exists
- `session/intent_identification.json` exists
- At least one transform + driver already generated (or generate together)
- Domain knowledge loaded (for tenancy, catalog, workspace info)

## STEP 0.0 — Chain Mode Output Compression

Apply `commands/refs/chain-mode-compression.md` pattern. Compact return: `[{step}/{total}] ✓ /gen-bundle — databricks.yml + {N} job YAMLs + {M} utility notebooks | Checkpoint: post_generation updated`

## STEP 0 — Platform Guard

If platform = Glue: REFUSE with:
> "DABs bundle generation is Databricks only. Glue uses DTXOG/Mesh JSON for deployment."

## STEP 0.1 — Chain Checkpoint Loading

Apply `commands/refs/chain-checkpoint-pattern.md`. Checkpoint key: `post_transform`. Note: Bundle generation does NOT need column_mappings — checkpoint provides all required metadata.

## STEP 0.5 — Read Templates (BLOCKING)

Read all required templates:
- `${CLAUDE_PLUGIN_ROOT}/templates/databricks/databricks.yml.template`
- `${CLAUDE_PLUGIN_ROOT}/templates/databricks/jobs/job.template.yml`
- `${CLAUDE_PLUGIN_ROOT}/templates/databricks/jobs/table_creation_utility_job.template.yml`
- `${CLAUDE_PLUGIN_ROOT}/templates/databricks/jobs/date_control_insert_utility_job.template.yml`
- `${CLAUDE_PLUGIN_ROOT}/templates/databricks/jobs/daily_date_control_update_utility_job.template.yml`
- `${CLAUDE_PLUGIN_ROOT}/templates/databricks/utilities/table_creation_utility.template.py`
- `${CLAUDE_PLUGIN_ROOT}/templates/databricks/utilities/date_control_insert_utility.template.py`
- `${CLAUDE_PLUGIN_ROOT}/templates/databricks/utilities/daily_date_control_update_utility.template.py`
- `${CLAUDE_PLUGIN_ROOT}/templates/databricks/generic_components/source_reader.py`
- `${CLAUDE_PLUGIN_ROOT}/templates/databricks/generic_components/target_writer.py`

---

## Behaviour

### STEP 1 — Resolve Bundle Parameters

From session_state and domain knowledge, resolve:
- `tenancy_name` — e.g., "complaints"
- `dp_type_lower` — e.g., "cdp" (lowercase data product type)
- `target_catalog` — Unity Catalog name
- `target_schema` — from `mapping_parsed.json → target_database` (EXACT value, no prefix/suffix stripping; see `/gen-config` STEP 0.6)
- `source_catalog` — source Unity Catalog name
- `tables[]` — list of all target tables generated in this session

**Consult `databricks-tenancy` skill** for per-environment infrastructure:

1. Match `Feature Team Name` (case-insensitive) against `session_state.tenancy_name`
2. Extract per-environment rows (DEV, PREPRD, PRD, and UAT if present) → resolve:
   - Workspace Folder → `{{dev_ws_root}}`, `{{preprd_ws_root}}`, `{{prd_ws_root}}`
   - Write/Target Catalog → `{{dev_target_catalog}}`, `{{preprd_target_catalog}}`, `{{prd_target_catalog}}`
   - CICD Service Principal → `{{dev_cicd_sp}}`, `{{preprd_cicd_sp}}`, `{{prd_cicd_sp}}`
   - Exec Service Principal → `{{dev_exec_sp}}`, `{{preprd_exec_sp}}`, `{{prd_exec_sp}}`
   - AD Group → `{{dev_ad_group}}`, `{{preprd_ad_group}}`, `{{prd_ad_group}}`
   - ITSI → `{{dev_app_service_tag}}`, `{{preprd_app_service_tag}}`, `{{prd_app_service_tag}}` (plain ITSI per env — ⚠️ may differ per environment, e.g., DEV=SNSVC0081840, PRD=SNSVC0081846)
   - FIN:Role Tag → `{{dev_fin_role_tag}}`, `{{preprd_fin_role_tag}}`, `{{prd_fin_role_tag}}` (per env — includes env-specific ITSI and env prefix)
   - Notification Email → `{{notification_email}}` (default: `BUKDataPlatformDatabricks@barclays.com`)
3. From **Workspace Hosts table** (fixed, shared across all tenancies):
   - `{{dev_workspace_host}}`, `{{preprd_workspace_host}}`, `{{prd_workspace_host}}`
   - `{{dev_policy_id}}`, `{{preprd_policy_id}}`, `{{prd_policy_id}}`
4. From **Source Catalogs table** (fixed):
   - `{{dev_source_catalog_1}}`, `{{preprd_source_catalog_1}}`, `{{prd_source_catalog_1}}`, `{{uat_source_catalog_1}}` (uat only if has_uat)
5. **Fallback** — if Feature Team Name not found in registry:
   a. **Check `session_state.dbx_config`** — if already populated AND (`session_state.dbx_config.questionnaire_turns_completed == 5` OR `session_state.tenancy_resolution_method == "registry"`), use those values for workspace folders, target catalogs, service principals, AD groups, ITSI, and tags. DONE.
   b. **Otherwise**, INTERACTIVELY invoke the infrastructure questionnaire (`prompts/infrastructure-questionnaire-databricks.md` — batched Turn 1–5 flow):
      - Turn 1: Q1 (Feature Team Name) — standalone, BLOCKING → **WAIT for response**
      - Turn 2: Q2 (Domain) + Q3 (Target Catalogs) → **WAIT for response**
      - Turn 3: Q4 (Workspace Folders) + Q5 (CICD SPs) + Q6 (Exec SPs) → **WAIT for response**
      - Turn 4: Q7 (AD Groups) + Q8 (ITSI per env) + Q9 (FIN:Role per env) + Q10 (Notification Email) → **WAIT for response**
      - Turn 5: **Confirmation Summary** → **WAIT for user confirmation**
   c. Store all answers in `session_state.dbx_config`
   d. For any values user skips → retain `{{placeholder}}` and mark artefact `DRAFT_UNVALIDATED`
   e. **NEVER derive target catalogs, workspace folders, or service principals from naming conventions** — these MUST come from the user or domain knowledge. If not provided, retain placeholders.
   f. Log WARNING: `"Tenancy not found in databricks-tenancy registry — infrastructure values collected from user"`

### STEP 1.5 — ITSI / Tagging Null Guard (MANDATORY) — Per-Environment

After parameter resolution from `databricks-tenancy` registry, validate ITSI and FIN:Role values **for each environment separately** (dev, preprd, prd):

1. **Check `{{app_service_tag}}` per environment** (ITSI):
   - For each env (dev, preprd, prd): resolve ITSI from the **environment-specific row** in the registry (DEV row for dev target, PREPRD row for prod_parallel target, PRD row for prod_prod target)
   - When resolving from **dbx_config** (questionnaire): read from `dbx_config.{env}.app_service_tag`
   - If registry/dbx_config returns `null`, empty string, `"TBD"`, or `"N/A"` for that env → **DO NOT substitute** from another tenancy or another environment
   - Emit raw placeholder: `{{dev_app_service_tag}}` / `{{preprd_app_service_tag}}` / `{{prd_app_service_tag}}` for that env's job YAMLs and databricks.yml target
   - Mark artefact `DRAFT_UNVALIDATED`
   - Log WARNING: `[ITSI-NULL-GUARD] ITSI not found for tenancy '{tenancy_name}' env '{env}' — placeholder retained`

2. **Check `{{fin_role_tag}}` per environment** (FIN:Role):
   - Same per-env rules as ITSI — resolve from the environment-specific registry row or `dbx_config.{env}.fin_role_tag`
   - If null/empty/TBD → emit `{{dev_fin_role_tag}}` / `{{preprd_fin_role_tag}}` / `{{prd_fin_role_tag}}` placeholder for that env
   - Log WARNING: `[ITSI-NULL-GUARD] FIN:Role not found for tenancy '{tenancy_name}' env '{env}' — placeholder retained`

3. **Per-environment target resolution**:
   - For **databricks.yml targets**: Each target (dev, prod_parallel, prod_prod) gets its own ITSI/FIN:Role values resolved from the corresponding environment row
   - For **job templates**: `{{app_service_tag}}` and `{{fin_role_tag}}` in cluster `custom_tags` must be resolved as DABs variables that differ per target, not as static literals

4. **Cross-tenancy contamination prevention**:
   - NEVER copy ITSI from a different tenancy when the current tenancy returns null
   - NEVER copy ITSI from a different environment when the current environment returns null
   - If domain knowledge contains an ITSI that does NOT match the tenancy registry → treat as stale; use registry value (or placeholder if registry is null)

5. **Notification Email resolution**:
   - Resolve from: `dbx_config.notification_email` (Priority 1) → tenancy skill Notification Email column (Priority 2) → default `"BUKDataPlatformDatabricks@barclays.com"` (Priority 3)
   - If registry shows `"TBD"` → use default
   - Emit resolved value for `{{notification_email}}` placeholder in `databricks.yml.template` (5 places) and all 5 job templates

6. **Logging**: Write to `session/audit_log.jsonl`:
   ```json
   {"timestamp": "<ISO 8601>", "event": "itsi_resolution", "tenancy": "{tenancy_name}", "dev_app_service_tag": "{value_or_placeholder}", "preprd_app_service_tag": "{value_or_placeholder}", "prd_app_service_tag": "{value_or_placeholder}", "dev_fin_role_tag": "{value_or_placeholder}", "preprd_fin_role_tag": "{value_or_placeholder}", "prd_fin_role_tag": "{value_or_placeholder}", "notification_email": "{value}", "source": "databricks-tenancy-registry|dbx_config|placeholder|default"}
   ```

---

### STEP 2 — Generate databricks.yml

Render `databricks.yml.template` with:
- All variables section populated (includes `environment` variable with default `"dev"`)
- `include` section listing all utility jobs and per-table jobs. Which day-folders to include depends on `load_type` per table:
  - `Day0` → day0 only
  - `BAU` → day1 only
  - `full_then_incremental` → both day0 and day1
- `targets` section with 3 deployment targets (dev, prod_parallel, prod_prod) + optional `uat` if tenancy has UAT row in registry
- Each target sets `environment` variable to its corresponding config.yml key:
  - `targets.dev` → `environment: "dev"`
  - `targets.prod_parallel` → `environment: "preprd"`
  - `targets.prod_prod` → `environment: "prd"`
  - `targets.uat` → `environment: "uat"` (only if `has_uat = true`)
- All environment-specific values from domain knowledge or `{{placeholder}}`

Write to: `generated/databricks/databricks.yml`

### STEP 3 — Generate Per-Table Job YAMLs

Read `session_state.data_flow_detection` to determine generation mode:

Create the job YAML output directories if they do not exist (only for load_type-applicable folders):
- Single-flow: `generated/databricks/jobs/{tenancy}_{dp}_jobs/{load_type_folder}/` where load_type_folder is determined by load_type (Day0→day0, BAU→day1, full_then_incremental→both)
- Multi-source-system (when `source_systems` is non-empty): `generated/databricks/jobs/{tenancy}_{dp}_jobs/{load_type_folder}/{source_system}/`

**Single-flow mode** (`source_systems` is empty or `artifact_mode == "combined"`):

For each target table in session_state, determine which job variants to render based on `load_type` (from `chain_checkpoints.post_transform.tables[].load_type`):

- **`load_type = "Day0"`**: Render `job.template.yml` ONCE — Day0 variant only:
  1. **Day0 variant**: `load_type_folder = "day0"` → write to `jobs/{tenancy}_{dp}_jobs/day0/{target_schema}_{table}_job.yml`

- **`load_type = "BAU"`**: Render `job.template.yml` ONCE — Day1 variant only:
  1. **Day1 variant**: `load_type_folder = "day1"` → write to `jobs/{tenancy}_{dp}_jobs/day1/{target_schema}_{table}_job.yml`

- **`load_type = "full_then_incremental"`**: Render `job.template.yml` TWICE:
  1. **Day0 variant**: `load_type_folder = "day0"` → write to `jobs/{tenancy}_{dp}_jobs/day0/{target_schema}_{table}_job.yml`
  2. **Day1 variant**: `load_type_folder = "day1"` → write to `jobs/{tenancy}_{dp}_jobs/day1/{target_schema}_{table}_job.yml`

**Multi-source-system mode** (`source_systems` is non-empty and `artifact_mode == "default"`):

For each target table in session_state, for EACH source_system in `data_flow_detection.source_systems[]`, determine which job variants to render based on `load_type`:

- **`load_type = "Day0"`**: Render Day0 variant only:
  1. **Day0 variant**: write to `jobs/{tenancy}_{dp}_jobs/day0/{source_system}/{target_schema}_{table}_job.yml`

- **`load_type = "BAU"`**: Render Day1 variant only:
  1. **Day1 variant**: write to `jobs/{tenancy}_{dp}_jobs/day1/{source_system}/{target_schema}_{table}_job.yml`

- **`load_type = "full_then_incremental"`**: Render BOTH:
  1. **Day0 variant**: write to `jobs/{tenancy}_{dp}_jobs/day0/{source_system}/{target_schema}_{table}_job.yml`
  2. **Day1 variant**: write to `jobs/{tenancy}_{dp}_jobs/day1/{source_system}/{target_schema}_{table}_job.yml`

Per-source-system rendering overrides (applied to `job.template.yml`):
- **Job resource name** (line 3 of template): `{target_schema}_{table}_{source_system}` — prevents name collision
- **Job display name** (line 4 of template): `"{target_schema}_{table}_{source_system}"`
- **notebook_path**: inject `{source_system}/` after `{{load_type_folder}}/` — becomes `.../{{load_type_folder}}/{source_system}/{{target_schema}}_{{table_name}}/{{target_schema}}_{{table_name}}_driver`
- **task_key**: `{target_schema}_{table}_{source_system}_driver`
- **job_cluster_key**: `{target_schema}_{table}_{source_system}_compute`
- `databricks.yml` bundle config: No structural change needed — it discovers job YAMLs from the jobs/ directory. The N separate YAMLs auto-register as N separate jobs.

Key parameters per job (both modes):
- `notebook_path`: points to the driver notebook in the correct day0/day1 (and source_system if applicable) folder
- `base_parameters`: `business_date: ""` and `environment: ${var.environment}` (resolved from DABs target)
- `{{spark_version}}`: Resolved from `session_state.spark_version`. Default: `16.4.x-scala2.12`
- `{{foundation_library_url}}`: Resolved from `session_state.foundation_library_url`. Default: `https://nexus-amazon-pdn.barclays.intranet/repository/barclays-read-conda/barclays_sdw/databricks/0.1.5/databricks_foundation-0.1.5-py3-none-any.whl`
- Cluster config: node type, env vars for Nexus proxy

### STEP 4 — Generate Utility Job YAMLs

Render 3 utility job templates:
1. `table_creation_utility_job.template.yml` → `{target_schema}_table_creation_utility.yml`
2. `date_control_insert_utility_job.template.yml` → `{target_schema}_date_control_insert_utility.yml`
3. `daily_date_control_update_utility_job.template.yml` → `{target_schema}_daily_date_control_update_utility.yml`

Write to: `generated/databricks/jobs/{tenancy}_{dp}_jobs/`

### STEP 5 — Generate Utility Notebooks

Render 3 utility notebook templates:
1. `table_creation_utility.template.py` → `{target_schema}_table_creation_utility.py`
   - `{{generated_ddl_list}}` populated from all target table DDLs + date_control + audit_log
2. `date_control_insert_utility.template.py` → `{target_schema}_date_control_insert_utility.py`
3. `daily_date_control_update_utility.template.py` → `{target_schema}_daily_date_control_update_utility.py`

Write to: `generated/databricks/src/Notebooks/utilities/`

### STEP 6 — Copy Generic Components (MANDATORY — DO NOT SKIP)

Copy the following static utility files from the plugin templates directory to the output utilities directory. These files are required by EVERY generated transform notebook (`# MAGIC %run {utilities_run_prefix}/utilities/source_reader` and `# MAGIC %run {utilities_run_prefix}/utilities/target_writer`, where path depth varies by layout — `../..` standard, `../../..` multi-source-system). If these files are absent, ALL transforms fail with `NameError` at Databricks runtime.

**Source → Destination mapping:**
- `${CLAUDE_PLUGIN_ROOT}/templates/databricks/generic_components/source_reader.py` → `generated/databricks/src/Notebooks/utilities/source_reader.py`
- `${CLAUDE_PLUGIN_ROOT}/templates/databricks/generic_components/target_writer.py` → `generated/databricks/src/Notebooks/utilities/target_writer.py`

**Execution:**
1. Ensure directory `generated/databricks/src/Notebooks/utilities/` exists (create if needed)
2. Write the EXACT content of the template files to the destination paths (no placeholder substitution — these are static files, copy verbatim)
3. Verify BOTH files exist and have size > 0 after write
4. If either file fails to write → HALT with:
   ```
   ❌ STEP 6 FAILED — utility files not copied.
   All transform %run references will be broken at runtime.
   Source: ${CLAUDE_PLUGIN_ROOT}/templates/databricks/generic_components/
   Destination: generated/databricks/src/Notebooks/utilities/
   ```

**Idempotency:** If files already exist (e.g., from `/gen-transform` STEP 0.55), overwrite unconditionally — the plugin templates are the authoritative source.

**This step has NO skip conditions.** It runs unconditionally every time `/gen-bundle` executes.

### STEP 7 — Validate

- Verify `databricks.yml` has `bundle`, `variables`, `include`, `sync`, `targets` sections
- Verify all `include` paths reference existing generated job YAML files
- Verify each job YAML has `resources.jobs.{name}.tasks[0].notebook_task.notebook_path`
- Verify `base_parameters` contains `business_date: ""` and `environment: ${var.environment}`
- Verify utility notebooks are valid Databricks notebook format
- Verify `generated/databricks/src/Notebooks/utilities/source_reader.py` exists and contains `class SourceReader`
- Verify `generated/databricks/src/Notebooks/utilities/target_writer.py` exists and contains `class TargetWriter`
- If either utility file is missing or empty → HALT with: "STEP 6 (Copy Generic Components) did not complete successfully. Re-run /gen-bundle."

---

## Output Files

- `generated/databricks/databricks.yml`
- `generated/databricks/jobs/{tenancy}_{dp}_jobs/day0/{target_schema}_{table}_job.yml` (per table)
- `generated/databricks/jobs/{tenancy}_{dp}_jobs/day1/{target_schema}_{table}_job.yml` (per table)
- `generated/databricks/jobs/{tenancy}_{dp}_jobs/day0/{source_system}/{target_schema}_{table}_job.yml` (per table, per source_system — multi-source-system mode only)
- `generated/databricks/jobs/{tenancy}_{dp}_jobs/day1/{source_system}/{target_schema}_{table}_job.yml` (per table, per source_system — multi-source-system mode only)
- `generated/databricks/jobs/{tenancy}_{dp}_jobs/{target_schema}_table_creation_utility.yml`
- `generated/databricks/jobs/{tenancy}_{dp}_jobs/{target_schema}_date_control_insert_utility.yml`
- `generated/databricks/jobs/{tenancy}_{dp}_jobs/{target_schema}_daily_date_control_update_utility.yml`
- `generated/databricks/src/Notebooks/utilities/source_reader.py`
- `generated/databricks/src/Notebooks/utilities/target_writer.py`
- `generated/databricks/src/Notebooks/utilities/{target_schema}_table_creation_utility.py`
- `generated/databricks/src/Notebooks/utilities/{target_schema}_date_control_insert_utility.py`
- `generated/databricks/src/Notebooks/utilities/{target_schema}_daily_date_control_update_utility.py`
- `session/audit_log.jsonl` (new entry)

## Failure Modes

- Platform = Glue → REFUSE
- No target tables generated → REFUSE (must run `/gen-transform` + `/gen-driver` first)
- Domain knowledge missing → Generate with `{{placeholder}}` values; mark DRAFT_UNVALIDATED

## Session State Updates

After generation:
```json
{
  "bundle_generated": true,
  "bundle_tables": ["table_1", "table_2"],
  "utility_notebooks_generated": true,
  "job_yamls_generated": true
}
```
