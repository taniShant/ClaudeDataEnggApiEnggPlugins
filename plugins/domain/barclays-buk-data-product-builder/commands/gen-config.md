---
description: Generate pipeline config (config.yml for Databricks, config.json for Glue) — both platforms
disable-model-invocation: false
---

# /gen-config

Generate the pipeline configuration file per target table. This is the **single source of truth** for all runtime parameters consumed by SourceReader, TargetWriter, driver/wrapper, and scheduling artefacts.

**Runs BEFORE `/gen-transform`** — the transform generator reads the generated config to understand what SourceReader will filter, which columns are available, and what broadcast decisions are already made.

## CRITICAL: Config-First Execution Model

Config generation must precede transform generation because:
1. SourceReader applies ALL filters from config (defaults + alias-specific) BEFORE the transform sees data
2. Transform must NOT duplicate any filter declared in config
3. The filter manifest (session artefact) tells the transform agent exactly which filters to suppress

## Per-Target-Table Output

This command generates **ONE CONFIG PER TARGET TABLE**.

**Databricks** — config placement is conditional on load_type:
- `Day0` → config in `day0/` only
- `BAU` → config in `day1/` only
- `full_then_incremental` → config in BOTH `day0/` AND `day1/`

### load_type Resolution for Config Output (Databricks Only)

When the intent phase resolves `load_type = "full_then_incremental"`:
- You MUST generate TWO config files (day0 and day1)
- The day0 config MUST set `pipeline.load_type: "Day0"`
- The day1 config MUST set `pipeline.load_type: "BAU"`

When the intent phase resolves `load_type = "Day0"`:
- Generate ONLY the day0 config with `pipeline.load_type: "Day0"`

When the intent phase resolves `load_type = "BAU"`:
- Generate ONLY the day1 config with `pipeline.load_type: "BAU"`

NEVER write `"full_then_incremental"` as the `pipeline.load_type` value in a generated config.yml.
The `full_then_incremental` value is an INTENT signal (meaning "generate both day0 and day1 artefacts"), not a runtime value.
The downstream utilities (`source_reader.py`, `target_writer.py`, transforms) expect `"Day0"` or `"BAU"` and route via `.lower()` normalization.

**Glue** — always ONE config file per table (load_type does NOT affect file count):
- All load types → single config at `generated/glue/wrapper/{db}_{target_table}_config.json`
- The file contains all filter modes (`day0`, `day1`, `catch_up_mode`); the wrapper selects the correct section at runtime.

### Output Format

**Databricks**:
```
generated/databricks/src/Notebooks/{day0|day1}/{target_schema}_{table}/{target_schema}_{table}_config.yml
```
Multi-source-system (when `data_flow_detection.source_systems` is non-empty — one config per source_system):
```
generated/databricks/src/Notebooks/{day0|day1}/{source_system}/{target_schema}_{table}/{target_schema}_{table}_config.yml
```

**Glue**:
```
generated/glue/wrapper/{db}_{target_table}_config.json
```
Multi-source-system (when `data_flow_detection.source_systems` is non-empty — one config per source_system):
```
generated/glue/wrapper/{db}_{target_table}_{source_system}_config.json
```

Create directories for output config file paths if they do not exist:
- Databricks: `generated/databricks/src/Notebooks/{day0|day1}/{target_schema}_{table}/`
- Databricks multi-source-system (when `data_flow_detection.source_systems` is non-empty): `generated/databricks/src/Notebooks/{day0|day1}/{source_system}/{target_schema}_{table}/`
- Glue: `generated/glue/wrapper/`

**Session manifest** (always, both platforms):
```
session/generated_configs/{target_schema}_{table}_filters.json
```

## Usage

```
/gen-config
```

## Prerequisites

- `session/intent_identification.json` exists (load_type, table_type, primary_key_cols, partition_col)
- `session/mapping_parsed.json` exists (source tables, columns, transformation_logic)
- `session/crypto_flags.json` exists (crypto section population)
- Platform resolved (session_state.platform = "databricks" | "glue")

## STEP 0.0 — Chain Mode Output Compression

Apply `commands/refs/chain-mode-compression.md` pattern. Compact return: `[{step}/{total}] ✓ /gen-config — {N} config files, {M} filter manifests generated | Checkpoint: post_config written`

## STEP 0 — Logging Initialization

Apply `conventions` skill logging pattern, component="de-gen-config".

## STEP 0.1 — Chain Checkpoint Loading

Apply `commands/refs/chain-checkpoint-pattern.md`. Checkpoint key: `post_intent`. Additional read: `session/mapping_parsed.json` for column_mappings + transformation_logic (needed for filter extraction).

## STEP 0.5 — Read Templates (BLOCKING — do not skip)

Before generating any config file, the agent MUST resolve the data flow mode and read the appropriate template.

### Source System Detection & Artifact Mode Resolution

Determine whether this target requires multi-source-system artifact generation. The **only** authoritative signal is the `source_system` key in Additional Context (Column K) of the mapping Excel.

**CRITICAL**: Multiple source databases in the mapping (e.g., `e_cms_db.cmrcase` JOIN `ref_common_db.region_lookup`) do NOT indicate multiple source systems. This is a normal multi-table join within a single flow. Multi-source-system is triggered ONLY by the explicit `source_system:<value>` key in Column K. Never infer from database count, duplicate target columns, or number of source tables.

**Step 1 — Detect source_system presence:**

Read `mapping_parsed.json` → collect all distinct non-null `source_system_hint` values.

**Where to find `source_system_hint`:** It is a **top-level field** in mapping_parsed.json (written by mapping-parser-agent Phase 2j), NOT nested inside `columns[]`. For single-table mappings, mapping_parsed.json is a single object — read its `source_system_hint` field directly. For multi-table mappings (array of objects), iterate and collect from each.

**IMPORTANT: Even a SINGLE non-null `source_system_hint` value triggers multi-source-system artifact generation.** Do NOT require 2+ distinct values. One source_system = one loop iteration with `{source_system}/` folder nesting.

Decision:
- If 0 non-null values → `source_systems = []` (no multi-source-system; single-flow)
- If 1+ non-null distinct values → `source_systems = [distinct values]` (multi-source-system flow)

Examples:
- `source_system_hint = "trmph"` → `source_systems = ["trmph"]` ← MULTI-FLOW (1 source_system)
- `source_system_hint = null` → `source_systems = []` ← single-flow
- Two tables: hints `"ilp"` and `"reference_data"` → `source_systems = ["ilp", "reference_data"]` ← MULTI-FLOW (2 source_systems)

Also check override sources (higher priority):
1. **Priority 0 — User Override**: `session/intent_overrides.json` → `data_flow_type: "multiple"` (requires `source_system` in Column K to identify systems)
2. **Priority 1 — Domain Knowledge**: `domain_knowledge_text` → `source_system` field (supplements Column K)

**Step 2 — Determine artifact mode:**

- If `source_systems` is non-empty AND mapping contains `Union Branch N:` format or `union_metadata`:
  → `artifact_mode = "combined"` (single artifact with UNION logic)
- If `source_systems` is non-empty AND no UNION:
  → `artifact_mode = "default"` with source_systems list (separate artifacts per source_system)
- If `source_systems` is empty:
  → `artifact_mode = "default"` with empty source_systems (normal single-flow)

**Step 3 — Build table mapping (when source_systems non-empty):**

For each target table in `mapping_parsed.json`:
- Read its `source_system_hint` value
- Group all `source_database.source_table` references from that table's `source_references[]` under this source_system label
- Result: `source_system_table_mapping = {"ilp": ["e_cms_db.cmrcase", "e_cms_db.cmrcase_event"], "reference_data": ["ref_common_db.region_lookup"]}`

**Write to session state:**
- `session_state.data_flow_detection.artifact_mode` = `"default"` | `"combined"`
- `session_state.data_flow_detection.source_systems` = `["ilp", "reference_data"]` or `[]`
- `session_state.data_flow_detection.source_system_table_mapping` = `{...}` or `null`
- `session_state.data_flow_detection.union_detected` = `true` | `false`

### Template Selection

**Both platforms always use the single-flow template:**
- Databricks: `${CLAUDE_PLUGIN_ROOT}/templates/databricks/config_single_data_flow_multi_env.template.yml`
- Glue: `${CLAUDE_PLUGIN_ROOT}/templates/glue/config_single_data_flow.template.json`

When `source_systems` is non-empty, the template is instantiated **once per source_system** with `source_system` injected into:
- `pipeline.process_name` → `{schema}_{table}_{source_system}`
- staging/checkpoint paths → `.../{source_system}/{table}/...`
- output file paths → Databricks: `{day}/{source_system}/{schema}_{table}/`, Glue: `{db}_{table}_{source_system}_*`
- Each instantiation includes ONLY the source tables belonging to that source_system (from `source_system_table_mapping`)

When `source_systems` is empty: standard single instantiation (today's behavior).

**Rules:**
- The template is the **authoritative source of structure** (sections, key names, nesting).
- If the template and prose conflict, **the template wins**.
- Generation = template read + placeholder substitution + filter extraction. Nothing more.

---

## STEP 0.6 — Resolve target_schema, tenancy_name, domain_name (MANDATORY — both platforms)

Resolve the three fields that depend on tenancy skill lookup. These fields have **explicit priority cascades** to handle the case where the target database is NOT found in the tenancy registry.

### target_schema / database_name Resolution (NON-NEGOTIABLE)

**Databricks:** `target_schema` = `mapping_parsed.json → target_database` (EXACT value, case-preserved)
**Glue:** `database_name` = `mapping_parsed.json → target_database` (EXACT value, case-preserved)

Rules:
- Do NOT strip any prefix (fdp_, cdp_, bdp_, shared_fdp_, shared_cdp_, shared_bdp_)
- Do NOT strip any suffix (_dbx, _dbxw, _iceberg, _icbg)
- Do NOT derive from tenancy Feature Team Name or domain knowledge
- Do NOT transform, normalize, or abbreviate the value
- The mapping Excel "Target Database" column IS the target schema/database name

This resolved value is used for:
- Databricks: `target.schema`, `pipeline.process_name`, file/folder naming (`{target_schema}_{table}`), staging paths, audit table
- Glue: `database`, file naming (`{db}_{target_table}`), S3 path components (with `_iceberg` stripping for S3 paths only per glue-wrapper-agent S3 Path Database Name Rule)

### tenancy_name Resolution (Priority Cascade)

**Pre-Check — env_config Already Populated**: If `session_state.env_config` is non-null AND `session_state.env_config.tenancy_name` is set AND (`session_state.tenancy_resolution_method != "user_provided"` OR `session_state.env_config.questionnaire_turns_completed == 6`) (populated by `/parse-mapping` STEP 2.7 — either from registry lookup or interactive infrastructure questionnaire) → `tenancy_name = session_state.env_config.tenancy_name`. DONE — skip priority cascade below.

1. **Priority 0 — Tenancy Skill**: If `target_database` matched in tenancy registry during `/parse-mapping` → use `session_state.tenancy_name` (already resolved). DONE.
2. **Priority 1 — Domain Knowledge**: If domain knowledge file is loaded and contains a `Tenancy:` marker → use that value. DONE.
3. **Priority 2 — Platform-Aware Fallback**:
   - **If platform = Databricks AND (`session_state.dbx_config` is null or empty OR `session_state.dbx_config.dev.target_catalog` is null):**
     Log WARNING: `"[STEP 0.6] dbx_config not populated — parse-mapping STEP 2.7 may have skipped infrastructure resolution. Triggering full Databricks infrastructure questionnaire as safety net."`
     Invoke the **Interactive Infrastructure Collection** from `prompts/infrastructure-questionnaire-databricks.md` (Databricks Turn 1–5 batched flow). Store results in `session_state.dbx_config`. This is a DEFENSIVE fallback — parse-mapping STEP 2.7 should have already populated these values.
   - **Otherwise (Glue, or dbx_config already populated):**
     Present question to user: "Target database '{target_database}' was not found in the tenancy registry and tenancy_name could not be resolved from domain knowledge. Please provide the Feature Team Name (tenancy_name):"
     Store in `session_state.env_config.tenancy_name` + `session_state.tenancy_name`.
     If skipped → proceed with `{{tenancy_name}}` placeholder; mark `DRAFT_UNVALIDATED`.
     **NO DERIVATION from target_database prefix stripping.**

### domain_name Resolution (Priority Cascade)

**Pre-Check — env_config Already Populated**: If `session_state.env_config` is non-null AND `session_state.env_config.domain` is set → `domain_name = session_state.env_config.domain`. DONE — skip priority cascade below.

1. **Priority 0 — Tenancy Skill**: From tenancy registry `Domain` column (if target_database matched). DONE.
2. **Priority 1 — Domain Knowledge**: If loaded, extract domain description. DONE.
3. **Priority 2 — ASK USER**: "What business domain does this data product belong to? (Optional)"
   If value provided → use it. If skipped → Priority 3.
4. **Priority 3 — Placeholder**: Leave as `{{domain_name}}` — non-blocking. Log: `"[STEP 0.6] domain_name unresolved — placeholder retained"`

---

## STEP 1 — Source Column Extraction (Per Target Table)

For each target table, extract the per-alias source column list:

**Algorithm:**
1. Scan all `column_mappings[]` for this target table in `mapping_parsed.json`
2. For each column's `source_references[]`, group by `source_table` alias
3. Collect unique `source_column` values per alias
4. Populate config `source.{table_type}.{alias}.columns` with sorted unique list

**Example:**
```yaml
source:
  non_transactional:
    customer_response:
      catalog_key: "source_catalog_1"
      table: "uk_nps_db_icbg.customer_response"
      columns:
        - "active"
        - "customer_response_date"
        - "customer_survey_id"
        - "question_id"
```

**Why populated (not empty):**
- Empty `columns` → SourceReader reads ALL columns (full table scan, no projection)
- Populated `columns` → projection at scan time → major I/O reduction
- CRITICAL for transform correctness validation (source column allow-list)

---

## STEP 1.5 — Infrastructure Column Augmentation (Per Target Table)

Augment the per-alias column list from STEP 1 with "infrastructure columns" — columns that are NOT mapped to any target column but ARE required by the transform for join predicates, dedup ordering, or pre-join filtering.

**Why needed**: SourceReader applies `.select(columns)` after reading each source table. If a column is absent from the `columns` list, it is pruned before the transform receives the DataFrame. Infrastructure columns appear only in `transformation_logic` (not in `source_references`) and would otherwise be dropped.

**Algorithm:**

1. **From `extracted_join_predicates`** (available if STEP 2.8 of `/parse-mapping` ran):
   - For each `column_mapping` with `extracted_join_predicates != null`:
     - For each predicate where `confidence` is `"high"` or `"medium"`:
       - Add `left_col` to the column set of alias matching `left_table`
       - Add `right_col` to the column set of alias matching `right_table`
   - Only add if the alias exists in the STEP 1 output (i.e., it's a recognized source table for this target)

2. **From `extracted_literals`** (filter columns):
   - For each `column_mapping` with `extracted_literals != null`:
     - For each literal where `confidence` is `"high"` or `"medium"` AND `context` is `"filter_predicate"` or `"case_when_condition"`:
       - Determine which alias owns the `column` field:
         - If the column already exists in an alias's column set from STEP 1 → that alias owns it (already present, no action needed)
         - If the column does NOT exist in any alias → check `source_table_metadata` for which source table contains it; add to that alias
       - Add the `column` to the owning alias's column set

3. **From `mapping_parsed.json → duplicates_ts_col_hint` OR domain knowledge `duplicates_ts_col`** (CDC dedup ordering column):
   - Resolve `duplicates_ts_col` value: check `mapping_parsed.json → duplicates_ts_col_hint` first (Priority 1); if null, check domain knowledge (Priority 2)
   - If resolved value is non-null:
     - Determine the MAIN/driver source alias (alias with the most `source_references` across all target columns)
     - Add the resolved `duplicates_ts_col` to that alias's column set

4. **Defensive audit columns by table_type** (from `session/source_table_metadata.json`):

   > **Audit columns per table type:** See `${CLAUDE_PLUGIN_ROOT}/agents/refs/audit-columns-by-table-type.md`

   - For each source alias, based on its classified `source_table_type`, ensure the corresponding audit columns are in column set
   - Only add if the source table is expected to have these columns (they are standard framework columns added by the ingestion layer)

5. **Re-sort**: After all augmentation, re-sort unique column lists per alias alphabetically (same format as STEP 1 output).

**Logging**: For each alias where columns were added:
```
[STEP 1.5] Augmented '{alias}' with infrastructure columns: {added_columns}
```

**Graceful degradation**: If `extracted_join_predicates` and `extracted_literals` are both null for ALL columns in the mapping (old session parsed before STEP 2.8), this step is a no-op — STEP 1 output passes through unchanged. Log: `"[STEP 1.5] Skipped — no extracted predicates in mapping (parsed before STEP 2.8)."`

---

## STEP 1.8 — File Source Config Population (Conditional)

**Condition**: `session_state.io_mode` ∈ {`file`, `hybrid`}. If `io_mode` is `table` (default) or absent → skip this step entirely.

**Action**: Add a `source.file` section to the generated config. Each file source from `session_state.source_io.sources[]` becomes an entry keyed by its logical alias.

### Per-Entry Fields

| Field | Source | Notes |
|-------|--------|-------|
| `path` | `session_state.source_io.sources[alias].storage_path` | Absolute path from mapping Column H — used as-is |
| `columns` | Same STEP 1 + STEP 1.5 column extraction logic as table sources | Projection list for SourceReader |
| `filter` | Optional — extracted from `transformation_logic` per STEP 2 classification | Omit if no filter applies |

### Path Resolution

The `path` value comes directly from the mapping document (Column H when `source_database` = `(file:parquet)`). It is the user-provided absolute storage path:
- **Glue**: `s3://` URI (e.g., `s3://raw-bucket/data/customer_events/`). SourceReader uses it as-is. The root-level `source.file.{alias}.path` is the single source of truth.
- **Databricks**: `/Volumes/` path (e.g., `/Volumes/raw_catalog/raw_schema/raw_volume/customer_events/`). The root-level `source.file.{alias}.path` stores the original mapping value (defaults to dev). Additionally, emit per-environment paths into each `environments.{env}.source_file_paths.{alias}`:
  - **dev**: Use the actual user-provided path from the mapping
  - **preprd, prd** (and **uat** if present): Use the placeholder value `"{{REPLACE_BEFORE_PROMOTION}}"` — engineers must replace these with the correct environment-specific Volume paths before promoting the pipeline to higher environments
  - At runtime, the driver overrides `source.file.{alias}.path` from `environments.{env}.source_file_paths.{alias}` for the active environment (same pattern as staging path resolution)

### Column Population

File source columns use the same STEP 1 + STEP 1.5 logic as table sources:
1. Scan `column_mappings[]` for `source_references` pointing to this file source alias
2. Collect unique source column names → sort alphabetically
3. Augment with infrastructure columns (join keys, filter columns) per STEP 1.5

**Logging**: `"[STEP 1.8] File source '{alias}' added to config source.file — {N} columns, path: {path}"`

---

## STEP 2 — Filter Extraction from Mapping (NEW — Core Logic)

> **Platform scope**: When `source_systems` is non-empty, both Databricks and Glue generate per-source-system configs using flat single-flow structure. Each config is scoped to ONE source_system — no nested source_system keys. Filter isolation is achieved by generating separate configs, not by nesting. Multiple source databases in a mapping do NOT imply separate source systems — only the explicit `source_system` key in Column K triggers this.

Extract single-data-flow filter expressions from mapping `transformation_logic` and classify them for config placement.

### 2.0 — Determine Filter Nesting Mode (PREREQUISITE)

Before composing filters, determine the nesting mode based on template selected in STEP 0.5:

**Single data flow template** → flat nesting:
```
filters.{operation}.{table_type}.{default|alias}
```

**Multiple data flow template** → source_system-nested:
```
filters.{operation}.{source_system}.{table_type}.{default|alias}
```

**Multiple data flow rule**: When `config_multiple_data_flow.template.json` is selected, filters MUST be nested under EACH source_system key. The source_system keys in `filters` MUST match EXACTLY the source_system keys in the `source` section.

**Default filter replication rule**: ALL source_systems receive ALL three table_type default filters in ALL three operations — regardless of whether that source_system has tables of that type in the `source` section:

| table_type | day0 default | day1 default | catch_up_mode default |
|---|---|---|---|
| `non-transactional` | `eff_start_date <= '{current_business_date}'` | `active = '1'` | `eff_start_date <= '{current_business_date}' AND eff_end_date > '{current_business_date}'` |
| `non-transactional-scd1` | `1=1` | `1=1` | `1=1` |
| `transactional` | `dw_bus_dt <= '{current_business_date}'` | `dw_bus_dt = '{current_business_date}'` | `dw_bus_dt <= '{current_business_date}'` |

**Example (multiple data flow with two systems)**:
```json
"filters": {
  "day0": {
    "system_a": {
      "non-transactional": { "default": "eff_start_date <= '{current_business_date}'" },
      "non-transactional-scd1": { "default": "1=1" },
      "transactional": { "default": "dw_bus_dt <= '{current_business_date}'" }
    },
    "system_b": {
      "non-transactional": { "default": "eff_start_date <= '{current_business_date}'" },
      "non-transactional-scd1": { "default": "1=1" },
      "transactional": { "default": "dw_bus_dt <= '{current_business_date}'" }
    }
  },
  "day1": {
    "system_a": {
      "non-transactional": { "default": "active = '1'" },
      "non-transactional-scd1": { "default": "1=1" },
      "transactional": { "default": "dw_bus_dt = '{current_business_date}'" }
    },
    "system_b": {
      "non-transactional": { "default": "active = '1'" },
      "non-transactional-scd1": { "default": "1=1" },
      "transactional": { "default": "dw_bus_dt = '{current_business_date}'" }
    }
  },
  "catch_up_mode": {
    "system_a": {
      "non-transactional": { "default": "eff_start_date <= '{current_business_date}' AND eff_end_date > '{current_business_date}'" },
      "non-transactional-scd1": { "default": "1=1" },
      "transactional": { "default": "dw_bus_dt <= '{current_business_date}'" }
    },
    "system_b": {
      "non-transactional": { "default": "eff_start_date <= '{current_business_date}' AND eff_end_date > '{current_business_date}'" },
      "non-transactional-scd1": { "default": "1=1" },
      "transactional": { "default": "dw_bus_dt <= '{current_business_date}'" }
    }
  }
}
```

**Single data flow**: skip source_system nesting — use flat structure as described in 2.1–2.4.

### 2.1 — Scan for Single-Data-Flow Filters

For each source table alias used by this target table:
1. Collect all `column_mappings[].transformation_logic` entries where `source_references[].source_table == alias`
2. Identify filter keywords in transformation_logic: "Filter", "Where", "Only", "Exclude", "Active records", "NOT IN", "= '<value>'"
3. Parse each identified filter and determine:
   - Does it reference ONLY columns from this single alias? → **candidate for config**
   - Does it reference columns from MULTIPLE aliases? → **post-join filter (transform-owned)**

### 2.2 — Classify Extracted Filters

For each candidate single-source filter:

**Standard (already covered by default):**
- `active = '1'` / `active = 1` / "Only active records" → matches NonTransactional day1 default
- `dw_bus_dt = '{current_business_date}'` / "Today's records" → matches Transactional day1 default
- `eff_start_date <= '{current_business_date}'` / "Historical up to date" → matches NonTransactional day0 default
- `dw_bus_dt <= '{current_business_date}'` / "Records up to date" → matches Transactional day0 default

If classified as standard → no alias-specific entry needed (default covers it).

**Business (custom — not covered by default):**
- `status NOT IN ('CLO', 'RED', 'WOF')` → custom business filter
- `type = 'ACTIVE'` → business classification filter
- `flag = 'Y' AND category = 'RETAIL'` → compound business filter

If classified as business → write alias-specific entry in config filters section.

### 2.3 — Compose Alias-Specific Filter Entries

**CRITICAL**: SourceReader's 3-case logic uses alias key EXCLUSIVELY when present (default is NOT merged). So alias-specific entries must contain the COMPLETE filter:

```
alias_filter = default_filter + " AND " + business_filter
```

**Example:**
- Default for NT day1: `active = '1'`
- Business filter for `cmrcase`: `status NOT IN ('CLO','RED','WOF')`
- Combined alias-specific entry: `active = '1' AND status NOT IN ('CLO','RED','WOF')`

**Day0 + Day1 separation:**
- If the business filter applies to Day1 operations only (e.g., "Only active CLO records in BAU") → add alias entry under `day1` only
- If the business filter applies universally (no temporal qualification) → add alias entry under BOTH `day0` and `day1`
- Default heuristic: add to the same operation(s) as the default filter applies

**Multiple data flow alias placement:**
When using multiple-data-flow nesting (STEP 2.0), alias-specific filter entries are placed under the source_system that OWNS that alias. Determine ownership from the `source` section — the alias appears under exactly one source_system's table_type grouping. Place the alias-specific entry under that same source_system in `filters`.

Example: if alias `cmrcase` is under `source.system_a.non-transactional`, its business filter goes under:
```
filters.day1.system_a.non-transactional.cmrcase = "active = '1' AND status NOT IN ('CLO','RED','WOF')"
```

### 2.4 — Catch-Up Mode Filters

For `catch_up_mode` filters:
- NonTransactional default: `eff_start_date <= '{current_business_date}' AND eff_end_date > '{current_business_date}'`
- If alias has a business filter → compose: `catch_up_default AND business_filter`
- Transactional: same as day0 default (historical boundary); add business filter if applicable

**Multiple data flow catch_up_mode**: Apply the same source_system nesting from STEP 2.0. Each source_system gets its own `catch_up_mode` entry with all three table_type defaults. Alias-specific catch_up entries are nested under the owning source_system (same ownership rule as STEP 2.3).

---

### Per-Source-System Config Generation (when source_systems is non-empty)

When `data_flow_detection.source_systems` is non-empty and `artifact_mode != "combined"`, STEPS 1–6 execute in a **loop over source_systems**:

For each `source_system` in `session_state.data_flow_detection.source_systems[]`:
1. **STEP 1**: Extract source columns for ONLY this source_system's tables (use `source_system_table_mapping[source_system]` to scope)
2. **STEP 2**: Extract filters for ONLY this source_system's tables (alias-specific filters go into the config that owns that alias; default filters per table_type applied to every config)
3. **STEP 6**: Generate config using the single-flow template with `source_system` injected into process_name and paths

**Output paths (per-source-system):**
- Databricks: `generated/databricks/src/Notebooks/{day}/{source_system}/{schema}_{table}/{schema}_{table}_config.yml`
- Glue: `generated/glue/wrapper/{db}_{table}_{source_system}_config.json`

**Filter manifest (per-source-system):**
- `session/generated_configs/{schema_or_db}_{table}_{source_system}_filters.json` — one per source_system

When `source_systems` is empty OR `artifact_mode == "combined"`: STEPS 1–6 execute once with all source tables. Output paths unchanged from today.

---

## STEP 3 — CDC Configuration

Populate the `cdc` section from intent identification, mapping hints, and domain knowledge:

### Common CDC fields (Glue + Databricks)

| Field | Source | Default (if no hint & no DK) |
|-------|--------|------------------------------|
| `primary_key_cols` | `intent_identification.json → primary_key_columns` | — (required) |
| `exclude_cols` | `mapping_parsed.json → cdc_exclude_cols_hint` (Priority 1) OR Domain knowledge `cdc_exclude_cols` (Priority 2) | `[]` |
| `high_ended_date` | Always `"3499-12-31"` (standard) | — |
| `snapshot_mode` | `intent_identification.json → snapshot_mode` | `false` |

> **Glue type conversion:** When writing Glue config JSON, convert `snapshot_mode` from boolean (as produced by intent identification) to string (`"true"`/`"false"`).

---

### Databricks-only CDC fields (NOT applicable to Glue)

> **Platform restriction**: The following fields are consumed by Databricks `target_writer.py` → `run_cdc()` (foundation library). Glue does NOT have `run_cdc()` — its writer uses a different CDC mechanism. Do NOT emit these fields in Glue config.json.

| Field | Source | Default (if no hint & no DK) |
|-------|--------|------------------------------|
| `broadcast_source` | Domain knowledge `broadcast_source` flag | `false` |
| `validate_unique_keys` | `mapping_parsed.json → validate_unique_keys_hint` (Priority 1) OR Domain knowledge (Priority 2) | `false` |
| `duplicates_ts_col` | `mapping_parsed.json → duplicates_ts_col_hint` (Priority 1) OR Domain knowledge (Priority 2) | **OMIT field** |
| `dedup_order` | `mapping_parsed.json → dedup_order_hint` (Priority 1) OR Domain knowledge (Priority 2) | **OMIT field** |

### CDC Deduplication Parameters — Priority Resolution & Emission Rules (Databricks only)

For `validate_unique_keys`, `duplicates_ts_col`, and `dedup_order` — **Databricks platform only**:

1. **Priority 1 — Mapping Hint**: Check `mapping_parsed.json` for the corresponding `*_hint` field.
   - If non-null → use mapping hint value. Do NOT consult domain knowledge. Log: `"[STEP 3] cdc.{field} from mapping hint: {value}"`
2. **Priority 2 — Domain Knowledge**: If hint is null, check domain knowledge for the field.
   - If found → use domain knowledge value. Log: `"[STEP 3] cdc.{field} from domain knowledge: {value}"`
3. **Default**: If neither source provides a value:
   - `validate_unique_keys` → emit as `false` (always present in Databricks CDC section)
   - `duplicates_ts_col` → **do NOT emit** the field (omit from YAML entirely)
   - `dedup_order` → **do NOT emit** the field (omit from YAML entirely)

**Emission rule**: `duplicates_ts_col` and `dedup_order` are ONLY written to Databricks config.yml when explicitly provided by mapping hint or domain knowledge. When absent from config, `target_writer.py` handles gracefully via `.get()` defaults (`None` and `"desc"` respectively).

**Applicability**: `validate_unique_keys`, `duplicates_ts_col`, `dedup_order`, and `broadcast_source` are ONLY applicable to **Databricks platform**, **NonTransactional_SCD2** tables, during **BAU/Day1 processing** (where `run_cdc()` is invoked). They have NO effect on Day0 (full overwrite), NonTransactional_SCD1 (UPSERT merge), Transactional (append), or any Glue config. Do NOT emit these fields for SCD1, Transactional, or Glue platform.

### Table-type emission rules (both platforms)

**NonTransactional_SCD2 (Databricks)**: Include full `cdc` section (primary_key_cols, exclude_cols, high_ended_date, snapshot_mode, broadcast_source, validate_unique_keys; conditionally: duplicates_ts_col, dedup_order).
**NonTransactional_SCD2 (Glue)**: Include `cdc` section with primary_key_cols, exclude_cols, snapshot_mode only. Omit broadcast_source, validate_unique_keys, duplicates_ts_col, dedup_order.
**NonTransactional_SCD1 (both)**: Include `cdc` section with ONLY `primary_key_cols` and `exclude_cols`. Omit all other CDC fields.
**Transactional (both)**: Omit `cdc` section entirely (append mode).

**Source table placement rule** (STEP 1 source grouping):
- Source classified as `NonTransactional_SCD2` → placed under `"non-transactional"` key (Glue) / `non_transactional` key (Databricks)
- Source classified as `NonTransactional_SCD1` → placed under `"non-transactional-scd1"` key (Glue) / `non_transactional_scd1` key (Databricks)
- Source classified as `Transactional` → placed under `"transactional"` key

---

## STEP 3.5 — Catch-Up Threshold Configuration

Populate the `catch_up_threshold_days` field in the generated config:

| Platform | Location in Config | Access Pattern |
|----------|-------------------|----------------|
| Databricks | `pipeline.catch_up_threshold_days` | `config.get("pipeline", {}).get("catch_up_threshold_days", 1)` |
| Glue | Top-level `catch_up_threshold_days` | `config.get('catch_up_threshold_days', 1)` |

**Default value**: `1`

**Meaning**: At runtime, the driver (Databricks) or wrapper (Glue) compares `system_date - business_date`. If the gap exceeds `catch_up_threshold_days` AND the operation is `day1` or `bau`, SourceReader automatically uses `catch_up_mode` filters instead of `day1` filters. The write strategy (TargetWriter) remains unchanged — only source filter selection is affected.

**Override**: Domain knowledge may specify `catch_up_threshold_days: N` (e.g., `2` for tables that tolerate a 2-day gap without needing wider filters).

**When to omit**: If domain knowledge explicitly states "never use catch_up_mode" for a table, omit the field entirely — the default of `1` will still apply at runtime. To effectively disable, set to a very high value (e.g., `9999`).

---

## STEP 3.6 — Process Frequency & Date Control Resolution

Populate the process frequency and date control fields from mapping hints and domain knowledge. **Synonym**: `load_frequency` (used in intent identification) and `process_frequency` (used in mapping Additional Context and config output) are synonymous — they represent the same scheduling frequency.

### Priority Cascade (all fields)

1. **Priority 1 — Mapping Hint**: Check `mapping_parsed.json` for the corresponding `*_hint` field.
   - If non-null → use value. Log: `"[STEP 3.6] {field} from mapping hint: {value}"`
2. **Priority 2 — Domain Knowledge**: If hint is null, check domain knowledge for the field.
   - If found → use value. Log: `"[STEP 3.6] {field} from domain knowledge: {value}"`
3. **Priority 3 — Default**: If neither source provides a value, use the platform default.

### Platform-Specific Emission

| Field | Databricks Config Location | Glue Config Location | Default |
|-------|---------------------------|---------------------|---------|
| frequency | `pipeline.process_frequency` | `date_control.frequency` | `"DAILY"` |
| workday_number_monthly | N/A (do not emit) | `date_control.workday_number_monthly` | `""` |
| workday_number_weekly | N/A (do not emit) | `date_control.workday_number_weekly` | `""` |
| run_on_weekends | N/A (do not emit) | `date_control.run_on_weekends` | `"N"` |
| run_on_bank_holidays | N/A (do not emit) | `date_control.run_on_bank_holidays` | `"N"` |

### Databricks Resolution

Emit ONLY `pipeline.process_frequency`:
- Resolved value from priority cascade (default: `"DAILY"`)
- Replaces the former hardcoded `"DAILY"` in template

### Glue Resolution

Emit the full `date_control` section with all 5 fields resolved:
- `frequency`: Resolved from `process_frequency_hint` → domain knowledge → `"DAILY"`
- `workday_number_monthly`: Resolved from `workday_number_monthly_hint` → domain knowledge → `""`
- `workday_number_weekly`: Resolved from `workday_number_weekly_hint` → domain knowledge → `""`
- `run_on_weekends`: Resolved from `run_on_weekends_hint` → domain knowledge → `"N"`
- `run_on_bank_holidays`: Resolved from `run_on_bank_holidays_hint` → domain knowledge → `"N"`

Additionally populate the file paths (already templated):
- `filename`: `data/stg/date_control/{database_name}/{table_name}/date_control.dat`
- `backup_filename`: `data/stg/date_control/{database_name}/{table_name}/date_control_bkp.dat`

**Validation**: If `frequency` resolves to `ONCE_A_MONTH` but `workday_number_monthly` is empty → log WARNING: "frequency is ONCE_A_MONTH but workday_number_monthly not specified — date_control may fail at runtime". Same for `WEEKLY_ONCE` without `workday_number_weekly`.

---

## STEP 3.7 — Rolling Deletion Configuration

Populate the optional `rolling_deletion` section in the generated config. This drives TargetWriter's `_rolling_delete()` method, which executes a `DELETE FROM <target> WHERE <predicate>` after every successful write.

### Applicability

- **Transactional**: Emit when predicate resolved ✅
- **NonTransactional_SCD1**: Emit when predicate resolved ✅
- **NonTransactional_SCD2**: **Never emit** — SCD2 tables maintain history via soft-expire (`active='0'`); physical deletion would destroy audit history ❌

### Priority Cascade

1. **Priority 1 — Mapping Hint**: Check `mapping_parsed.json → rolling_deletion_predicate_hint`.
   - If non-null → use value. Log: `"[STEP 3.7] rolling_deletion.predicate from mapping hint: {value}"`
2. **Priority 2 — Domain Knowledge**: If hint is null, check domain knowledge for `rolling_deletion_predicate` field.
   - If found → use value. Log: `"[STEP 3.7] rolling_deletion.predicate from domain knowledge: {value}"`
3. **Default**: If neither source provides a value → **do NOT emit** `rolling_deletion` section (omit entirely from config). The absence of the section means rolling deletion is disabled at runtime.

### Config Emission

When a predicate is resolved AND table_type is Transactional or NonTransactional_SCD1:

**Glue** (config.json):
```json
"rolling_deletion": {
  "enabled": true,
  "predicate": "<resolved predicate>"
}
```

**Databricks** (config.yml):
```yaml
rolling_deletion:
  enabled: true
  predicate: "<resolved predicate>"
```

When emitting, `enabled` is always set to `true` — the section's presence with `enabled: true` activates the feature. Users can disable by setting `enabled: false` or removing the section entirely.

### Template Variable

The `predicate` field supports `{current_business_date}` as a template variable — TargetWriter interpolates it at runtime with the ISO date string (YYYY-MM-DD) of the current business date. No other variables are supported.

### Validation

- If table_type is `NonTransactional_SCD2` AND a `rolling_deletion_predicate_hint` or domain knowledge predicate was provided → log WARNING: `"[STEP 3.7] rolling_deletion_predicate provided for SCD2 table — IGNORED (SCD2 tables must not use rolling deletion)"`. Do NOT emit the section.
- If predicate is resolved but empty string → log WARNING: `"[STEP 3.7] rolling_deletion_predicate is empty — section omitted"`. Do NOT emit.

---

## STEP 3.8 — File Target Config Population (Conditional)

**Condition**: `session_state.target_io` is present (non-null). If absent → skip this step entirely.

**Action**: Add a `target_io` section to the generated config with the following fields:

| Field | Source | Default |
|-------|--------|---------|
| `path` | Platform naming convention (see below) | — (required) |
| `write_mode` | `session_state.target_io.write_mode` | `"append"` |
| `partition_by` | `session_state.target_io.partition_by` | `[]` (no partitioning) |
| `compression` | `session_state.target_io.compression` | `"snappy"` |

### Path Convention

- **Glue**: `data/file_data/{database_name}/{table_name}` (relative path at root level). At runtime: `s3://{config['environments'][env]['s3_bucket']}/{path}`
- **Databricks**: Emit `target_io` inside each `environments.{env}` block (same pattern as staging paths) with the per-environment catalog already resolved. Path: `/Volumes/{env_target_catalog}/{target_schema}/file_data/{table_name}` where `{env_target_catalog}` is `session_state.dbx_config.{env}.target_catalog`. The driver resolves the active environment's `target_io` at runtime via `config["target_io"] = env_config["target_io"]`.

### Config Emission Constraints

When `target_io` is present in the generated config:
- **OMIT** the `cdc` section entirely — MERGE operations are not supported on parquet file targets
- **OMIT** the `rolling_deletion` section entirely — DELETE operations are not supported on parquet file targets
- The existing `target` section (database/tablename) is **still populated** — used for naming, audit logging, and `process_name` resolution

**Logging**: `"[STEP 3.8] target_io section added — path: {path}, write_mode: {write_mode}, partition_by: {partition_by}"`

### Validation

- If `session_state.target_io` is present AND `table_type == "NonTransactional_SCD2"` → this should have been blocked by FIO3 validation during `/init`. Log ERROR if encountered: `"[STEP 3.8] target_io present for SCD2 table — FIO3 should have blocked this. Proceeding but CDC will be omitted."`

---

## STEP 4 — Environment & Catalog Resolution (Databricks Only)

**Pre-Check (Databricks only)**: If platform = Databricks AND `session_state.dbx_config` is null or not populated → **HALT**: `"Cannot generate Databricks config — dbx_config is empty. Target schema '{target_database}' was not resolved against the tenancy registry and the infrastructure questionnaire was not completed. Run /parse-mapping to trigger tenancy resolution, or provide a domain knowledge file with all required infrastructure values."`

Read pre-resolved catalogs from `session_state.dbx_config` (populated during `/parse-mapping` STEP 2.7 from the `databricks-tenancy` skill's **Write/Target Catalog** column, or from user via infrastructure questionnaire Q3).

1. For each environment (dev, preprd, prd, optional uat):
   - `target_catalog` = `session_state.dbx_config.{env}.target_catalog` — **NEVER derive from naming convention**
   - If value is null → retain `{{*_target_catalog}}` placeholder and mark artefacts `DRAFT_UNVALIDATED`
   - `source_catalog_1` = standard source catalog per environment (auto-resolved; DEV/UAT: `077382350852_buk_data_products`; PREPRD/PRD: `buk_data_product_central_catalog`)
   - `source_catalog_2+` = from domain knowledge (only if specified)
2. Populate `environments` section with catalog mappings + staging paths
3. **File target paths** (conditional — only when `session_state.target_io` is present): For each environment, add `target_io` inside `environments.{env}` with the path `/Volumes/{env_target_catalog}/{target_schema}/file_data/{table_name}` using that environment's resolved `target_catalog`. Include `write_mode`, `partition_by`, and `compression` from `session_state.target_io` (same values across all environments — only the catalog in the path varies).
4. **File source paths** (conditional — only when `session_state.io_mode` ∈ {`file`, `hybrid`}): For each file source alias from `session_state.source_io.sources[]`, add `source_file_paths.{alias}` inside each `environments.{env}` block:
   - **dev**: Use the actual user-provided path from `session_state.source_io.sources[alias].storage_path`
   - **preprd, prd** (and **uat** if present): Use the placeholder value `"{{REPLACE_BEFORE_PROMOTION}}"` with a YAML comment: `# REPLACE: Update source file path for {env} environment before promotion`

**Glue equivalent**: Uses `database`, `source.{alias}.table` (FQN from Glue catalog), file_locations from tenancy. Additionally, populate `environments.{env}.s3_bucket` for each environment (dev/uat/prd) from `session_state.env_config.{env}.s3_bucket`. This provides the runtime S3 bucket name resolved by wrapper.py via `config['environments'][env]['s3_bucket']`.

---

## STEP 5 — Crypto Section (Conditional)

If `crypto_flags.any_column_crypto_flagged = true`:
- Populate `crypto` section per environment (dev/uat/prd)
- `secret_name`: `sms-crypto-{tenancy_name}`
- `itsi`: from env_config
- `api_endpoint_url`: from env_config

If no crypto → omit section entirely.

---

## STEP 6 — Generate Config File

**Platform dispatch:**
- IF `session_state.platform == "databricks"`: Delegate to `databricks-artefact-agent` with `artefact_scope: "config"`. Generates config per load_type folder (day0/ and/or day1/).
- IF `session_state.platform == "glue"`: Generate ONE config file at `generated/glue/wrapper/{db}_{target_table}_config.json` using the populated template from STEP 0.5. Do NOT split by load_type — the single file contains all filter modes.

**Databricks output**: YAML format using `config_single_data_flow_multi_env.template.yml` structure.
**Glue output**: JSON format using `config_single_data_flow.template.json` or `config_multiple_data_flow.template.json`.

**Multiple data flow filter completeness check** (Glue only): After populating the template, verify that EVERY source_system key present in `source` also appears in `filters.day0`, `filters.day1`, AND `filters.catch_up_mode`. Each source_system entry MUST contain all three table_type keys (`non-transactional`, `non-transactional-scd1`, `transactional`) with at minimum a `default` value. Missing entries cause SourceReader to apply no filter, resulting in full table scans.

---

## STEP 7 — Write Filter Manifest (Session Artefact)

Write `session/generated_configs/{target_schema}_{table}_filters.json` containing:

```json
{
  "target_table": "{target_schema}_{table}",
  "platform": "databricks|glue",
  "config_path": "generated/.../config.yml|json",
  "template_mode": "single_data_flow|multiple_data_flow",
  "filters_declared": "<<see mode-specific structure below>>",
  "broadcast_config": {
    "cdc_broadcast_source": false
  },
  "source_columns": {
    "<alias_1>": ["col1", "col2", "..."],
    "<alias_2>": ["col1", "col2", "..."]
  },
  "file_sources": []
}
```

**`filters_declared` — Single data flow mode** (`template_mode: "single_data_flow"`):
```json
"filters_declared": {
  "day0": {
    "non_transactional": {
      "default": "eff_start_date <= '{current_business_date}'",
      "<alias>": "<combined filter if business filter present>"
    },
    "transactional": {
      "default": "dw_bus_dt <= '{current_business_date}'"
    }
  },
  "day1": {
    "non_transactional": {
      "default": "active = '1'",
      "<alias>": "active = '1' AND <business_filter>"
    },
    "transactional": {
      "default": "dw_bus_dt = '{current_business_date}'"
    }
  },
  "catch_up_mode": {
    "non_transactional": {
      "default": "eff_start_date <= '{current_business_date}' AND eff_end_date > '{current_business_date}'"
    },
    "transactional": {
      "default": "dw_bus_dt <= '{current_business_date}'"
    }
  }
}
```

**`filters_declared` — Multiple data flow mode** (`template_mode: "multiple_data_flow"`):
```json
"filters_declared": {
  "day0": {
    "<source_system_1>": {
      "non-transactional": { "default": "eff_start_date <= '{current_business_date}'" },
      "non-transactional-scd1": { "default": "1=1" },
      "transactional": { "default": "dw_bus_dt <= '{current_business_date}'" }
    },
    "<source_system_2>": {
      "non-transactional": { "default": "eff_start_date <= '{current_business_date}'" },
      "non-transactional-scd1": { "default": "1=1" },
      "transactional": { "default": "dw_bus_dt <= '{current_business_date}'" }
    }
  },
  "day1": {
    "<source_system_1>": {
      "non-transactional": { "default": "active = '1'", "<alias>": "active = '1' AND <business_filter>" },
      "non-transactional-scd1": { "default": "1=1" },
      "transactional": { "default": "dw_bus_dt = '{current_business_date}'" }
    },
    "<source_system_2>": {
      "non-transactional": { "default": "active = '1'" },
      "non-transactional-scd1": { "default": "1=1" },
      "transactional": { "default": "dw_bus_dt = '{current_business_date}'" }
    }
  },
  "catch_up_mode": {
    "<source_system_1>": {
      "non-transactional": { "default": "eff_start_date <= '{current_business_date}' AND eff_end_date > '{current_business_date}'" },
      "non-transactional-scd1": { "default": "1=1" },
      "transactional": { "default": "dw_bus_dt <= '{current_business_date}'" }
    },
    "<source_system_2>": {
      "non-transactional": { "default": "eff_start_date <= '{current_business_date}' AND eff_end_date > '{current_business_date}'" },
      "non-transactional-scd1": { "default": "1=1" },
      "transactional": { "default": "dw_bus_dt <= '{current_business_date}'" }
    }
  }
}
```

**Purpose**: The transform-generator-agent reads this manifest to:
1. Know which filters are already declared in config → SUPPRESS in transform code
2. Know which source columns are available → validate F.col() references
3. Know broadcast_source decision → avoid redundant F.broadcast() on main table
4. Know the nesting mode (`template_mode`) → correctly parse filter paths for suppression logic
5. Know which aliases are file-based (from `file_sources` array) → emit appropriate comments in transform

The `file_sources` array lists aliases that are file-based (from `source.file` config section). When empty (`[]`), all sources are table-based (default). When populated (e.g., `["customer_events"]`), the transform generator emits comments for those aliases indicating SourceReader handles the parquet read.

---

## STEP 8 — Write Checkpoint

Write `session_state.chain_checkpoints.post_config` containing:
- List of generated config file paths
- List of filter manifest paths
- Per-table summary: alias count, filter count, crypto flag

---

## Output Files

- Config file (per target table):
  - Databricks (per load_type folder): `generated/databricks/src/Notebooks/{day0|day1}/{target_schema}_{table}/{target_schema}_{table}_config.yml`
  - Glue (single file, all filter modes): `generated/glue/wrapper/{db}_{target_table}_config.json`
- Filter manifest (per target table): `session/generated_configs/{target_schema}_{table}_filters.json`
- `session/audit_log.jsonl` (new entry)
- `session/session_state.json` (updated: `chain_checkpoints.post_config`)

---

## Multi-Table Batching

**Mode Detection**: Single table → standard generation. Multiple tables → batch-parallel.

### Per-Table File Naming

Each config uses `{target_schema}_{table}` (Databricks) or `{db}_{target_table}` (Glue) naming for uniqueness.

### Batch Processing

- Process tables in parallel batches (batch_size = 3–5)
- Each table gets independent context (no cross-table filter contamination)
- Filter extraction is per-table — filters for table A do not affect table B

---

## Failure Modes

| Condition | Action |
|-----------|--------|
| Missing `intent_identification.json` | HALT — run `/identify-intent` first |
| Missing `mapping_parsed.json` | HALT — run `/parse-mapping` first |
| Platform not resolved | HALT — run `/init` first |
| Filter extraction ambiguous (NL interpretation unclear) | WARN — use default only; log advisory for manual review |
| Tenancy not found in registry | Check `session_state.env_config` — if populated (user-provided via infrastructure questionnaire or domain knowledge), proceed using those values; otherwise HALT |
| `{{placeholder}}` unresolved after generation | Mark DRAFT_UNVALIDATED; update `session/placeholders.json` |

---

## Validation (Post-Generation)

1. **Schema validation**: Generated config matches template structure
2. **Source column coverage**: Every source_column referenced in column_mappings appears in at least one alias's columns list
3. **Filter consistency**: Alias-specific entries include the default condition (exclusive semantics enforced)
4. **Placeholder scan**: `\{\{[a-z_]+\}\}` patterns → blocking vs non-blocking classification
5. **CDC completeness**: If table_type = NonTransactional_SCD1 or NonTransactional_SCD2 → `cdc` section must exist with `primary_key_cols` non-empty. If SCD1 → assert no `high_ended_date`/`snapshot_mode` keys present.
6. **Multiple data flow filter coverage**: If multiple-data-flow template selected → every source_system in `source` section has a corresponding entry under each operation in `filters` (day0, day1, catch_up_mode), and each contains all three table_type keys (`non-transactional`, `non-transactional-scd1`, `transactional`) with defaults populated.
