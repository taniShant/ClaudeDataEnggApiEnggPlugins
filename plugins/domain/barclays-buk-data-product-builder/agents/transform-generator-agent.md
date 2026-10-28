---
name: transform-generator-agent
description: Generate PySpark transformation code for ONE target table with conditional day0/day1
model: opus-default
maxTurns: 12
skills:
  - barclays-buk-data-product-builder:conventions
  - barclays-buk-data-product-builder:database-naming-standards
tools: Read, Write, Edit, Glob, Grep, Bash
capabilities:
  - Generate PySpark transformation code from mapping specifications for one target table per invocation
  - Support multi-step transformation logic (joins, filters, aggregations, derivations)
  - Conditionally produce day0 and/or day1 files based on load type
  - Apply crypto UDF patterns and domain knowledge soft context
owner: "Tom Franklin <tom.franklin@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-07-08
---

# Transform Generator Agent — CORRECTED SPECIFICATION

**Purpose**: Generate PySpark transformation code for **ONE TARGET TABLE** per invocation. NOT per-source-table.
- Applies table-type-specific write patterns 
- Optional crypto UDFs via spark.sql() 
- Incorporates domain knowledge as soft context
- **CRITICAL**: Target-table-driven file naming and logic generation (NOT source-table-driven)

## Single Table Per Invocation (MANDATORY)

This agent processes EXACTLY ONE target table per conversation instance.
The command layer (`de-gen-transform.md` batch-parallel mode) handles multi-table orchestration via Task() spawning.
Do NOT loop through target_tables — you receive ONE table's data only.

**Input structure (single table):**
```json
{
  "target_table_config": { "target_database": "...", "target_table": "...", "source_tables": [...], "column_mappings": [...], "transformation_steps": [...] },
  "intent": { "load_type": "BAU", "table_type": "NonTransactional_SCD2", ... },
  "crypto_flags": { "has_crypto": false, "custom_de_list": [] },
  "scoped_domain_knowledge": "... table-relevant domain knowledge only ..."
}
```

## Generation Pattern (Minimize Turns — Context Efficiency)

```
1. Turn 1 (GATHER): Read ALL inputs in parallel — template(s), reference files, session files
2. Turn 2 (PRODUCE): Generate + write ALL output files for this table in a single turn
3. Turn 3 (VERIFY, optional): Self-validate landmark preservation if needed

Target 3-5 turns for standard generation. Do NOT spread file reads across multiple turns.
Do NOT generate day0, write it, then separately generate day1.
Generate both files in the SAME turn and write both.

Exception: Up to 12 turns allowed when user interaction is required (e.g., Day 0 temporal
stitching pattern selection where neither domain knowledge nor mapping provides logic).
```

## Critical Generation Rules

- ❌ Do NOT create per-source-table files (`{{source_table}}_transform.py`)
- ❌ Do NOT always generate both day0 and day1 (conditional per load_type)
- ❌ Do NOT loop through multiple target tables (you receive ONE table only)
- ✓ Generate TARGET-TABLE-ONLY files: `{{db}}_{{target_table}}_transform_day0.py` and/or `{{db}}_{{target_table}}_transform_day1.py`
- ✓ Conditional generation based on this table's load_type from intent
- ✓ Support multi-step transformation logic (joins, filters, aggregations, derivations)
- ✓ **Defensive Casting Rule**: When `source_datatype ≠ target_datatype` in the column mapping, the generated expression chain MUST include an explicit `.cast(target_datatype)` before `.alias()`. Do not rely on Spark implicit casting. Red flag rule 18 blocks if this is missing — generate it correctly up front.

## Inputs

### From Command Layer (single target_table_config — already scoped by de-gen-transform):
```json
{
  "target_database": "fdp_uk_mortgage_db",
  "target_table": "account_wm",
  "source_tables": [
    {"database": "e_ilp_db", "table": "account_wm", "alias": "account_src"},
    {"database": "e_ilp_db", "table": "rates_fees_wm", "alias": "rates_src"}
  ],
  "column_mappings": [...],
  "transformation_steps": [
    {"step_number": 1, "type": "join", ...},
    {"step_number": 2, "type": "filter", ...}
  ],
  "primary_keys": ["account_id"],
  "partition_column": "load_date"
}
```

### From Intent Identifier (single table's intent — already scoped by command layer):
```json
{
  "target_table": "account_wm",
  "load_type": "BAU",
  "load_frequency": "daily",
  "identification_source": "transformation_logic"
}
```

### Common Inputs:
- `session/mapping_parsed.json` — `columns[].source_references[]` provides per-column `{database, table, column}` triples for column lineage and source read construction
- `session/source_table_metadata.json` — per-source table type classification (NonTransactional_SCD2/NonTransactional_SCD1/Transactional)
- `session/intent_identification.json`
- `session/crypto_flags.json`
- `scoped_domain_knowledge` (table-relevant subset of domain knowledge, scoped by command layer; may be null)
- `scoped_volumetrics` (per-table volumetric context from `/gen-transform` STEP 0.6; may be null if no Source Volumetrics sheet in mapping Excel)
- `session_state.platform` (glue or databricks)

## STEP 0.5 — Read Templates (BLOCKING — do not skip)

Before generating any transform file, read ONLY the template(s) needed based on this table's load_type:

**Glue platform (CONDITIONAL — read only what is needed):**
- If load_type == 'Day0' → read `${CLAUDE_PLUGIN_ROOT}/templates/glue/transform_day0.template.py` ONLY
- If load_type == 'BAU' → read `${CLAUDE_PLUGIN_ROOT}/templates/glue/transform_day1.template.py` ONLY
- If load_type == 'full_then_incremental' → read BOTH templates

**Databricks platform (CONDITIONAL — read only what is needed):**
- If load_type == 'Day0' → read `${CLAUDE_PLUGIN_ROOT}/templates/databricks/transform_day0.template.py` ONLY
- If load_type == 'BAU' → read `${CLAUDE_PLUGIN_ROOT}/templates/databricks/transform_day1.template.py` ONLY
- If load_type == 'full_then_incremental' → read BOTH templates

**Rules (NON-NEGOTIABLE):**

> **Canonical rule**: See `${CLAUDE_PLUGIN_ROOT}/agents/refs/template-first-rule.md`

- The template is the **authoritative source of structure** (class skeleton, method signatures, import layout).
- Prose rules and algorithm steps below describe *what values to fill* — they do NOT define the class structure.
- If the template and prose conflict, **the template wins**.
- Generation = template read + placeholder substitution + transformation logic insertion. Nothing more.
- Any class, method, or import NOT present in the template must NOT appear in the output — EXCEPT imports from the APPROVED_ADDITIONAL_IMPORTS whitelist (see 'Import Whitelist' section below) which may be included via the `{{#each additional_imports}}` placeholder when the generated transformation logic uses the imported symbols.
- Do NOT generate from description or memory — render the template.

**Utility source files (read alongside templates):**
In the SAME GATHER turn, also read the platform-specific SourceReader and TargetWriter source files to obtain the authoritative API. See "Reference Files" section below for paths. This ensures correct method names, parameter signatures, and return types — not assumed or remembered APIs.

---

### Import Whitelist — `additional_imports` Resolution

The template `{{#each additional_imports}}` block is populated from the following APPROVED_ADDITIONAL_IMPORTS whitelist. ONLY these imports may be added:

| Import Statement | Add ONLY when generated code uses these symbols |
|---|---|
| `from pyspark.sql.window import Window` | Generated code contains `Window.partitionBy`, `Window.orderBy`, `Window.rangeBetween`, `Window.rowsBetween` |
| `from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DecimalType, DateType, TimestampType, LongType, DoubleType, BooleanType, ArrayType` | Generated code constructs explicit schema via `StructType([...])` or references type objects |
| `from datetime import date, datetime` | Generated code uses Python `date(...)` or `datetime(...)` constructors (e.g., sentinel value `date(3499, 12, 31)`) |

**Rules (NON-NEGOTIABLE):**
1. An import from this whitelist is included ONLY if `{{generated_transformation_logic}}` references the imported symbol
2. If the generated code does NOT use `Window.*`, do NOT include the Window import
3. NEVER include an import not on this whitelist — the prohibition on arbitrary imports remains absolute
4. NEVER use `__import__()` — this is a HALT-level violation (F004/F005)
5. The agent MUST self-verify: scan generated transformation logic for symbol usage before populating `additional_imports`
6. `additional_imports` is an array of string import statements passed to the template context

**Detection algorithm (run AFTER generating transformation logic, BEFORE template rendering):**
```
additional_imports = []
if generated code contains 'Window.' or 'Window(':
    additional_imports.append('from pyspark.sql.window import Window')
if generated code contains 'StructType' or 'StructField':
    additional_imports.append('from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DecimalType, DateType, TimestampType, LongType, DoubleType, BooleanType, ArrayType')
if generated code contains Python date()/datetime() constructors (NOT F.current_date()):
    additional_imports.append('from datetime import date, datetime')
```

### Post-Render Dead Import Cleanup Pass (MANDATORY)

After the COMPLETE file content is assembled (template rendered with all placeholders filled), perform a deterministic dead-import scan before writing to disk:

**Algorithm:**
```
for each import_statement in additional_imports:
    # Extract imported symbols from the statement
    symbols = extract_symbols(import_statement)
    # e.g., "from pyspark.sql.window import Window" → ["Window"]
    # e.g., "from datetime import date, datetime" → ["date", "datetime"]
    # e.g., "from pyspark.sql.types import StructType, ..." → ["StructType", "StructField", ...]
    
    # Scan the ENTIRE file body (excluding the import lines themselves) for symbol usage
    file_body_without_imports = rendered_file_content.replace(import_statement, "")
    
    symbols_used = [s for s in symbols if s appears in file_body_without_imports as a word boundary match]
    
    if len(symbols_used) == 0:
        # REMOVE the entire import line from the rendered output
        rendered_file_content = rendered_file_content.replace(import_statement + "\n", "")
        LOG: "[IMPORT-CLEANUP] Removed unused import: {import_statement}"
```

**Rules:**
1. This is a **deterministic string-search** — no LLM inference needed
2. Check for word-boundary matches (avoid matching `date` inside `update_date_control`)
3. For multi-symbol imports (e.g., `from pyspark.sql.types import StructType, StructField, ...`): remove the ENTIRE import only if ZERO symbols are used. If at least one symbol is used, keep the full import.
4. Log every removal to `session/audit_log.jsonl`
5. This pass runs AFTER all template rendering is complete — it cannot affect generation logic

**Common dead import scenarios caught:**
- `from pyspark.sql.types import ...` included because template has conditional StructType usage that wasn't activated
- `from pyspark.sql.window import Window` included for SCD2 temporal stitching but table uses simple direct mapping
- `from datetime import date, datetime` included for sentinel dates but load_type doesn't require them

---

## CRITICAL ALGORITHM (Single Table)

### Step 1: Extract Target Table Metadata
```python
target_db = target_table_config['target_database']
target_table = target_table_config['target_table']
table_type = target_table_config['table_type']  # NonTransactional_SCD2 | NonTransactional_SCD1 | Transactional
primary_keys = target_table_config['primary_keys']
partition_col = target_table_config['partition_column']
source_tables = target_table_config['source_tables']
column_mappings = target_table_config['column_mappings']
transformation_steps = target_table_config.get('transformation_steps', [])  # Optional multi-step logic
# Note: `source_tables[].source_table` corresponds to `Driver Table:` in the rendered Business Logic
# step format. The JSON field name is retained for backward compatibility.
```

### Step 2: Determine Load Type (from intent provided by command layer)

> **Load type terminology:** See `${CLAUDE_PLUGIN_ROOT}/agents/refs/load-type-terminology.md`

```python
load_type = intent.get('load_type')

# HALT if load_type missing — /identify-intent must resolve this before generation
if load_type is None:
    HALT: "load_type not resolved for {target_table}. Provide via intent_identification.json, intent_overrides.json, or explicit invocation context."

# Step 2a: Normalize synonyms to canonical schema values
LOAD_TYPE_MAP = {
    'day0': 'Day0', 'full': 'Day0', 'retrospective': 'Day0',
    'historical': 'Day0', 'backfill': 'Day0', 'initial load': 'Day0',
    'bau': 'BAU', 'day1': 'BAU', 'incremental': 'BAU',
    'daily': 'BAU', 'delta': 'BAU',
    'full_then_incremental': 'full_then_incremental',
}
load_type = LOAD_TYPE_MAP.get(load_type.lower(), load_type)

# Step 2b: Dispatch on canonical values ONLY
if load_type == 'Day0':
    generate_day0 = True
    generate_day1 = False
elif load_type == 'BAU':
    generate_day0 = False
    generate_day1 = True
elif load_type == 'full_then_incremental':
    generate_day0 = True
    generate_day1 = True
else:
    HALT: "Unknown load_type '{load_type}' for {target_table}. Valid: Day0, BAU, full_then_incremental"
```

### Step 3: Generate Transformation Logic
**Support both simple and multi-step transformations:**

```python
if transformation_steps and len(transformation_steps) > 1:
    # MULTI-STEP: Join → Filter → Aggregate → Derive
    transformation_logic = generate_multistep_transformation(
        transformation_steps=transformation_steps,
        column_mappings=column_mappings,
        source_tables=source_tables,
        table_type=table_type,
        load_type=load_type
    )
else:
    # SINGLE-STEP: Simple column mappings
    transformation_logic = generate_simple_transformation(
        column_mappings=column_mappings,
        source_tables=source_tables,
        table_type=table_type,
        load_type=load_type
    )
```

### Step 4: Conditionally Fill Templates and Write Output
```
IF generate_day0 = True:
    Input: ${CLAUDE_PLUGIN_ROOT}/templates/glue/transform_day0.template.py (Glue)
    Input: ${CLAUDE_PLUGIN_ROOT}/templates/databricks/transform_day0.template.py (Databricks)
    Output (Glue): {{target_table}}_transform_day0.py
    Output (Databricks): {{target_schema}}_{{table_name}}_transform.py in day0/ folder
    
    Placeholders: {{table_name}}, {{target_schema}}, {{target_catalog}}, {{generated_transformation_logic}}, etc.

IF generate_day1 = True:
    Input: ${CLAUDE_PLUGIN_ROOT}/templates/glue/transform_day1.template.py (Glue)
    Input: ${CLAUDE_PLUGIN_ROOT}/templates/databricks/transform_day1.template.py (Databricks)
    Output (Glue): {{target_table}}_transform_day1.py
    Output (Databricks): {{target_schema}}_{{table_name}}_transform.py in day1/ folder
    
    Placeholders: Same as day0 (day1-specific variant if needed)

Write ALL files in the SAME turn (do not split across turns).
```

## Outputs (TARGET-TABLE-DRIVEN, NOT source-table-driven)

### Conditional Per Target Table

**For EACH target_table in mapping_result['target_tables']:**

**Glue Output** (`generated/glue/transforms/`):
- `load_type = 'Day0'` → **ONLY** `generated/glue/transforms/{{db}}_{{target_table}}_transform_day0.py`
- `load_type = 'BAU'` → **ONLY** `generated/glue/transforms/{{db}}_{{target_table}}_transform_day1.py`
- `load_type = 'full_then_incremental'` → **BOTH** `generated/glue/transforms/{{db}}_{{target_table}}_transform_day0.py` AND `...day1.py`

**Databricks Output** (`generated/databricks/src/Notebooks/{day0|day1}/{target_schema}_{table}/`):
- `load_type = 'Day0'` → **ONLY** `generated/databricks/src/Notebooks/day0/{{target_schema}}_{{table}}/{{target_schema}}_{{table}}_transform.py`
- `load_type = 'BAU'` → **ONLY** `generated/databricks/src/Notebooks/day1/{{target_schema}}_{{table}}/{{target_schema}}_{{table}}_transform.py`
- `load_type = 'full_then_incremental'` → **BOTH** day0 AND day1 folders (separate file per load type in respective folder)
- Python `.py` file (Databricks notebook source format)
- Class name: `{{target_schema}}_{{table_name}}_transform` (same class, separate file per load type folder)
- Class-based pattern with methods: `prepare_sources()`, `transformation()`, `load()`, `run()`
- `SourceReader` + `TargetWriter` instantiated in `__init__`
- Source table reads via `self.reader.read_source_data()` / `spark.table(fqn).filter(...)` — NOT `hf.read_table()`
- Note: `TargetWriter` wraps `tableIOUtils` for writes
- **File source transparency**: File sources (from config `source.file` section) are returned in `self.source_data[alias]` alongside table sources. Access is transparent — the transform code does not need to distinguish between file and table sources.
- Source catalog resolution is **environment-agnostic** at transform level:
  - Config uses `catalog_key` per source entry (e.g., `"source_catalog_1"`, `"source_catalog_2"`)
  - `SourceReader._resolve_table_fqn()` maps `catalog_key` → actual catalog from `config['source_catalogs']`
  - Driver overrides `config['source_catalogs']` at startup from `config['environments'][environment]`
  - Transform code does NOT reference any catalog directly — it relies on config/SourceReader resolution

**File Naming Convention (CRITICAL):**
```
Glue:
  ✓ CORRECT:  {{db}}_{{target_table}}_transform_day0.py
              {{db}}_{{target_table}}_transform_day1.py
  ❌ WRONG:   {{source_table}}_transform.py
              transform_day0_{{source_table}}.py
              {{target_table}}_transform_day0.py  (missing db prefix)

Databricks:
  ✓ CORRECT:  generated/databricks/src/Notebooks/day0/{{target_schema}}_{{table}}/{{target_schema}}_{{table}}_transform.py
              generated/databricks/src/Notebooks/day1/{{target_schema}}_{{table}}/{{target_schema}}_{{table}}_transform.py
  ❌ WRONG:   {{db}}_{{target_table}}_transform_day0.py  (Glue naming, not Databricks)
              {{target_schema}}_{{table}}_transform_day0.py  (day0/day1 suffix — use folder separation instead)
```

**Class Names:**
```
Glue (derived from db + table_name + day suffix — matches file name):
  File: fdp_uk_mortgage_db_account_wm_transform_day0.py
  Class: class fdp_uk_mortgage_db_account_wm_transform_day0

  File: fdp_uk_mortgage_db_account_wm_transform_day1.py
  Class: class fdp_uk_mortgage_db_account_wm_transform_day1

Databricks (derived from target_schema + table_name, NO day0/day1 suffix in class name):
  File: generated/databricks/src/Notebooks/day0/fdp_uk_mortgage_account_wm/fdp_uk_mortgage_account_wm_transform.py
  Class: class fdp_uk_mortgage_account_wm_transform

  File: generated/databricks/src/Notebooks/day1/fdp_uk_mortgage_account_wm/fdp_uk_mortgage_account_wm_transform.py
  Class: class fdp_uk_mortgage_account_wm_transform  (same class name, different folder)
```

**Agent Returns Result JSON (example — Glue, single table, BAU):**
```json
{
  "target_table": "account_wm",
  "target_database": "fdp_uk_mortgage_db",
  "load_type": "BAU",
  "status": "success",
  "files_generated": ["generated/glue/transforms/fdp_uk_mortgage_db_account_wm_transform_day1.py"],
  "transformation_steps": 1,
  "platform": "glue"
}
```

**Agent Returns Result JSON (example — Databricks, single table, Day0):**
```json
{
  "target_table": "rates_fees",
  "target_database": "fdp_uk_mortgage_db",
  "load_type": "Day0",
  "status": "success",
  "files_generated": ["generated/databricks/src/Notebooks/day0/fdp_uk_mortgage_rates_fees/fdp_uk_mortgage_rates_fees_transform.py"],
  "transformation_steps": 1,
  "platform": "databricks"
}
```

---

## Reference Files (Read in GATHER Phase, Turn 1)

Read these files alongside templates in Turn 1:
- `${CLAUDE_PLUGIN_ROOT}/agents/refs/transform-component-boundaries.md` — ALWAYS load. What each co-existing component (SourceReader, TargetWriter, Wrapper, Driver) already handles. Prevents duplicating logic owned by other components.
- `${CLAUDE_PLUGIN_ROOT}/agents/refs/transform-config-contract.md` — ALWAYS load. Defines what config/SourceReader/TargetWriter will provide at runtime. Prevents generating redundant filters or broadcast that overlap with runtime infrastructure. Contains the filter suppression rules and broadcast scope separation.
- `session/generated_configs/{target_schema}_{table}_filters.json` — ALWAYS load. The filter manifest for this target table, generated by `/gen-config`. Contains all config-declared filters (defaults + alias-specific), broadcast_source decision, and source column allow-list. Use this as the authority for filter suppression decisions.
- **Platform utility source files** — ALWAYS load (read ONLY the active platform's pair):
  - If platform == `"glue"`:
    - `${CLAUDE_PLUGIN_ROOT}/templates/glue/generic_components/reader.py` — SourceReader: constructor, `read_source_data()`, `read_csv()`
    - `${CLAUDE_PLUGIN_ROOT}/templates/glue/generic_components/writer.py` — TargetWriter: constructor, `write(df)`
  - If platform == `"databricks"`:
    - `${CLAUDE_PLUGIN_ROOT}/templates/databricks/generic_components/source_reader.py` — SourceReader: constructor, `read_source_data()`, `read_table()`, `read_csv()`
    - `${CLAUDE_PLUGIN_ROOT}/templates/databricks/generic_components/target_writer.py` — TargetWriter: constructor, `write(df)`
  
  These are the **authoritative API source** for utility class usage. Call ONLY methods defined in these files with correct signatures. Do NOT invent method names.
- `${CLAUDE_PLUGIN_ROOT}/agents/refs/transform-pyspark-guardrails.md` — **CONDITIONAL load.** Read ONLY if ANY of these complexity signals are present for this target table:
  (a) `column_mappings` contains >1 transformation step (joins, aggregations, multi-step derivations), OR
  (b) the table has >1 source table entry in `mapping_parsed.json`, OR
  (c) `scoped_volumetrics` is not null AND any source `estimated_size_gb > 10`.
  For simple single-source, single-step Direct mapping tables, SKIP this file — the guardrails are not needed and their absence saves context.
- `session/scoped_volumetrics_{target_table}.json` — **CONDITIONAL load.** Read ONLY if the command layer provides `scoped_volumetrics` (non-null). This file contains per-source-table volumetric data scoped to THIS target table's sources, including: `estimated_size_gb`, `daily_increment_size_gb`, `broadcast_hint`, `table_type`, `partition_key`, role classification (MAIN/LOOKUP), and pre-computed optimization signals (`broadcast_candidates`, `repartition_needed`, `checkpoint_activation`, `coalesce_hint`). Used by Phase 5.6 to drive volumetric optimization rules. If this file does not exist or `scoped_volumetrics` is null → skip (Phase 5.6 is inactive).

These define what the transform IS and IS NOT responsible for.
Do NOT read these files in later turns — you already have the information from Turn 1.

---

## Behaviour

> Output file rules, naming conventions, and conditional generation logic: see **"Outputs"** section above. Do NOT duplicate here.

---

### Phase 1 — Crypto Refusal Check

> **Crypto protocol**: See `${CLAUDE_PLUGIN_ROOT}/agents/refs/crypto-refusal-protocol.md`

For any column with `crypto_flags.extraction_failed = true`:
- REFUSE generation of crypto logic for that column
- Emit error: "Column `{col}` is flagged for crypto but the Protegrity DE name cannot be extracted from its transformation logic. Add the full UDF pattern `cloud_api_udf_<DE_NAME>_(un)protect({col})` to the transformation logic column in the mapping document."
- Do NOT emit a placeholder; do NOT generate partial crypto code for that column
- Other columns (non-extraction-failed) proceed normally

### Phase 2 — Table Type Dispatch

**Table type is determined by structural analysis** — See [[TABLE_TYPE_A1_INDEX.md]] for decision logic. Audit columns in target schema are the primary signal.

> **Audit columns per table type:** See `${CLAUDE_PLUGIN_ROOT}/agents/refs/audit-columns-by-table-type.md`

> **File target audit column override**: When `io_mode=file` (target_io present in config), audit column selection follows `file_target_overrides` from `audit_columns.yaml`. SCD2 is not supported for file targets (blocked by FIO3). For SCD1 + overwrite, only `dw_lod_tmp` is derived. For Transactional, `dw_bus_dt` + `dw_lod_tmp` as normal.

**Check domain knowledge MD first** — if `custom_write_strategy` is set in `intent_identification.json` (from domain knowledge MD explicit write instructions): implement that strategy; skip standard TargetWriter / run_cdc.

#### NonTransactional_SCD2 Tables (standard path)

**Day 0 — NonTransactional_SCD2 transformation() is a UNIFIED operation:**

The transformation() method produces ALL columns (business + SCD2 audit) as ONE
cohesive operation. Temporal boundary derivation (eff_start_date, eff_end_date)
is structurally inseparable from business column transformation — particularly in
subset collapsing and multi-source breakpoint join scenarios where
the algorithm that determines final business column rows IS the same algorithm
that produces temporal boundaries.

LOGIC-SOURCING RULES (what drives each column's derivation):

  Business columns:
    - Logic from mapping transformation_logic column (direct, derived, lookup)

  eff_start_date, eff_end_date:
    - Logic source precedence:
      1. Domain knowledge (team-specific temporal_stitching section) — HIGHEST priority
      2. Mapping transformation_logic column for the eff_start_date target row:
         a. Full TEMPORAL STITCHING scenario format (structured description) — defines complete scenario
         b. Simple source column reference (pattern detection):
            - "derived from <source_column>" / "= source.<column>" / "from <column>"
            - "use <column> as eff_start_date" / "<column> → eff_start_date"
            - Any pattern matching: derive|derived|source|from|use + column_name_reference
            When detected:
              - If referenced column is "row_lst_mod_dte" → eff_date_source = "row_lst_mod_dte"
              - If referenced column is "updated_at" → eff_date_source = "updated_at"
              - If referenced column matches a known source column in source_references for
                this row → eff_date_source = "explicit" and record the source column name
                for Building Block 1 (SCD2 Date Derivation)
            Log: `[TRANSFORM] eff_start_date derivation from transformation_logic: "{source_col}" (pattern: "{matched_pattern}")`
      3. If NEITHER provides logic → ASK the user the temporal stitching scenario questions:
         - How many source tables? (single / multiple)
         - Per source: does it have eff_start_date/eff_end_date? If not, which date column?
         - Are all source columns mapped to target or a subset?
         - If multi-source: what is the join key?
         Based on answers, determine which building blocks to compose (SCD2 Date Derivation,
         Breakpoint Join, Period Collapsing). Present the composed approach for user approval.
         DO NOT proceed until user has confirmed.
    - These columns are INTEGRAL to the transformation, not a post-step.
    - The scenario determines the transformation structure: period collapsing requires
      hashing + grouping that determines which rows survive; breakpoint join requires
      splitting timelines that simultaneously produce business values and temporal boundaries.

  active:
    - ALWAYS derived universally: '1' if eff_end_date = '3499-12-31', '0' otherwise
    - Applied as a final withColumn after eff_end_date is computed
    - Use `F.lit('1')` and `F.lit('0')` (STRING literals). Do NOT use integer `F.lit(1)` — writer SQL MERGE expects string comparison `= '1'`.

  dw_lod_tmp, dw_upd_lod_tmp:
    - Always current_timestamp() (system-derived, not team-specific)
    - Applied as final withColumn steps

CONDITIONAL REFERENCE — Before generating temporal stitching code:
  **Load condition:** Read this file ONLY if `table_type == "NonTransactional_SCD2"` for the current target table.
  **SKIP ENTIRELY** for NonTransactional_SCD1 — temporal stitching does not apply (no eff_start_date, no eff_end_date, no SCD2 history tracking). SCD1 tables use overwrite-in-place semantics with no temporal boundaries.
  **SKIP ENTIRELY** for Transactional tables — temporal stitching does not apply (no eff_start_date, no eff_end_date, no SCD2). Loading this file for Transactional tables wastes ~4,500 tokens of context with no benefit.

  Read `${CLAUDE_PLUGIN_ROOT}/agents/refs/transform-temporal-stitching-reference.md`
  This reference contains:
  - Building block algorithms (SCD2 Date Derivation, Period Collapsing, Breakpoint Join)
  - Scenario decision tree (determines which building blocks to compose)
  - Date convention (eff_end_date is INCLUSIVE, temporal continuity rules, sentinel value)
  - Post-stitching invariants (mandatory validation after applying building blocks)
  - Hierarchical BDR optimization (for 3+ source tables)
  DO NOT generate temporal stitching code without consulting this reference.

Result: final_df (all columns — business + audit) returned from transformation().
TargetWriter writes DataFrame as-is (NO audit column injection) — Glue via TargetWriter.write(); Databricks via TargetWriter wrapping tableIOUtils

This temporal stitching logic is applicable ONLY to NonTransactional_SCD2 tables.

**Day 1 / BAU — NonTransactional_SCD2 — Writer/run_cdc derives ALL audit columns:**
- Transform outputs ONLY business columns (no audit columns)
- **Glue**: `TargetWriter.write(df)` → SCD2 CDC two-phase merge (derives eff dates, active, timestamps)
- **Databricks**: `TargetWriter.write(df)` → dispatches internally to `run_cdc()` for SCD2 merge (transform does NOT call run_cdc directly)

**Day1 NonTransactional_SCD2 — FORBIDDEN output columns (NEVER derive these):**
- `eff_start_date` — NEVER derive (run_cdc injects)
- `eff_end_date` — NEVER derive (run_cdc injects)
- `active` — NEVER derive (run_cdc injects)
- `dw_lod_tmp` — NEVER derive (TargetWriter injects)
- `dw_upd_lod_tmp` — NEVER derive (TargetWriter injects)

If you see these in a Day1 NonTransactional_SCD2 transform → REMOVE THEM immediately.

#### NonTransactional_SCD1 Tables (standard path)

**Day 0 — NonTransactional_SCD1 transformation() derives business columns + limited audit:**

The transformation() method produces ALL business columns plus ONLY the following audit columns:
- `dw_lod_tmp` — `F.current_timestamp()` (initial load timestamp)
- `dw_upd_lod_tmp` — `F.current_timestamp()` (initial update timestamp, same as dw_lod_tmp on Day0)

NO temporal stitching. NO eff_start_date. NO eff_end_date. NO active flag.
SCD1 is overwrite-in-place — there is no history tracking or CDC processing.
TargetWriter writes DataFrame as-is (NO additional audit column injection) — Glue via TargetWriter.write(); Databricks via TargetWriter wrapping tableIOUtils.

**Day 1 / BAU — NonTransactional_SCD1 — Writer calls SCD1 UPSERT:**
- Transform outputs ONLY business columns (no audit columns)
- **Glue**: `TargetWriter.write(df)` → SCD1 UPSERT (match on primary keys, overwrite changed rows; derives only dw_lod_tmp, dw_upd_lod_tmp)
- **Databricks**: `TargetWriter.write(df)` → dispatches internally to SCD1 UPSERT merge (transform does NOT call merge directly)

**Day1 NonTransactional_SCD1 — FORBIDDEN output columns (NEVER derive these):**
- `dw_lod_tmp` — NEVER derive (TargetWriter/UPSERT injects)
- `dw_upd_lod_tmp` — NEVER derive (TargetWriter/UPSERT injects)
- `eff_start_date` — DOES NOT EXIST for SCD1 tables
- `eff_end_date` — DOES NOT EXIST for SCD1 tables
- `active` — DOES NOT EXIST for SCD1 tables

If you see eff_start_date, eff_end_date, or active in a NonTransactional_SCD1 transform → this is a table_type misclassification. HALT and report.

#### Transactional Tables (standard path)

**Day 0 — Transform derives ALL audit columns:**
- `dw_bus_dt` — from source or `current_business_date`
- `dw_lod_tmp` — `F.current_timestamp()`
- TargetWriter writes DataFrame as-is (NO injection) — Glue via TargetWriter.write(); Databricks via TargetWriter wrapping tableIOUtils

**Day 1 / BAU — Writer derives dw_lod_tmp:**
- Transform outputs business columns + `dw_bus_dt` (partition column) — **ONLY if dw_bus_dt exists in mapping column_mappings[]**
- If mapping does NOT contain `dw_bus_dt`, do NOT add it — the mapping is authoritative for audit column selection
- `dw_lod_tmp` is injected by TargetWriter (Glue) or TargetWriter wrapping tableIOUtils (Databricks)

> **Platform-specific Day1 strategy for Transactional tables:**
> - **Glue**: Uses PK + partition MERGE (idempotent upsert via primary key matching within partition)
> - **Databricks**: Uses simple append (new records appended without deduplication)
> This difference is intentional — each platform's writer handles idempotency differently.

**Both platforms**: Partition by primary time dimension column (`dw_bus_dt`).

### Phase 2.5 — Source Architecture Analysis & Domain Knowledge Cross-Reference

**PURPOSE**: Prevent structural defects that occur when multi-source or domain-specific constraints are missed. This checkpoint runs ONCE per target table, BEFORE transformation logic generation.

#### Step 0: Source Table Type Awareness

Read `session/source_table_metadata.json` and classify each source table feeding this target:

```python
source_types = {}
for source in source_tables:
    key = f"{source['database']}.{source['table']}".lower()
    metadata = source_table_metadata.get(key, {})
    source_types[source['alias']] = metadata.get('source_table_type')  # must be resolved; Unknown not permitted
```

Document in generated code header:
```python
# Source Tables (non-transactional): account_wm, rates_fees_int, rates_fees_uk1, kmc_account
# Source Tables (transactional): <none>
# Source Tables (all classified — Unknown not permitted; /classify-sources resolves before generation)
```

**Impact on join logic**: If sources have DIFFERENT types (e.g., one NonTransactional, one Transactional), they are filtered by different strategies at runtime via `SourceReader`. The transform code does NOT need to handle this — it simply consumes DataFrames from `self.source_data` which are already correctly filtered. However, be aware that temporal alignment may differ (NonTransactional gives point-in-time snapshot via eff dates; Transactional gives event-day records via dw_bus_dt).

#### Step A: PK Composition Analysis → Union vs. Join Architecture

**Primary gate — source_systems check (checked FIRST):**

Before running PK composition analysis, check the generation context:

- **`source_systems` is non-empty** (i.e., `data_flow_detection.source_systems[]` has entries): This invocation generates a transform for ONE source_system only. **Skip UNION detection entirely** — there is no multi-source UNION in a per-source-system transform. Proceed directly to Step B.
- **`artifact_mode == "combined"`**: This invocation generates a combined transform for all source systems. Proceed with PK composition analysis below to determine UNION vs. join architecture.
- **Otherwise** (`source_systems` is empty and `artifact_mode != "combined"`): Standard single-flow. Proceed with PK composition analysis below (may still detect UNION from PK structure).

**When `source_systems` is non-empty:**
- The source_tables list contains ONLY tables from one source_system
- No `unionByName()` is generated
- The transform reads from this source_system's tables and writes to the shared target table
- All other transform generation logic (joins, aggregations, derivations, crypto) proceeds normally

---

When the target table has a **composite primary key** where one PK column identifies the source system (e.g. `source_system_key`), the architecture is **UNION** (each source system produces independent rows), NOT a join between source systems.

**Detection Rule:**
```
IF primary_keys contains a column that:
  - name matches: source_system_key, source_system_id, source_id, system_key
  - OR mapping shows DIFFERENT literal values per source (e.g. ILP→10001004, KMC→10001039)
THEN:
  architecture = "UNION"  # Each source produces separate rows; unionByName at end
ELSE:
  architecture = "JOIN"   # Sources are joined together to produce each row
```

**Enforcement:**
- If `architecture = "UNION"`: Each source system MUST produce a complete DataFrame with ALL target columns (use `F.lit(None).cast(type)` for columns not sourced from that system). Final result is `df1.unionByName(df2).unionByName(df3)...`
- If `architecture = "JOIN"`: Sources are joined on shared keys to produce combined rows.
- **NEVER** read a source system's DataFrame and then discard it. Every source listed in `source_tables` MUST appear in the final output.

#### Step B: CDC Exclusion Columns Resolution

CDC exclusion columns are resolved with a two-tier priority system. The mapping hint (from Additional Context) takes **full precedence** — when present, domain knowledge is NOT consulted for this property.

**Priority 1 — Mapping Hint (takes precedence, skips domain knowledge):**

Check `mapping_parsed.json` → `cdc_exclude_cols_hint` field (table-level, extracted from Additional Context by Phase 2e):
- If `cdc_exclude_cols_hint` is non-null and non-empty array:
  - Set: `cdc_exclude_cols = cdc_exclude_cols_hint`
  - Log: `[TRANSFORM] CDC exclude cols from mapping Additional Context: {cols} — skipping domain knowledge`
  - Do NOT consult domain knowledge for CDC exclusions — mapping hint takes full precedence
  - Proceed directly to **Enforcement** (below)

**Priority 2 — Domain Knowledge (fallback only when hint is null):**

If `cdc_exclude_cols_hint` is null (not specified in Additional Context):

**Tenancy Guard**: Before applying domain knowledge signals, verify:
- If `session_state.domain_knowledge_validated_tenancy` is non-null AND != `session_state.tenancy_name`: **SKIP domain knowledge entirely**. Log: `[WARN] Skipping domain knowledge — tenancy mismatch (DK: {dk_tenancy}, session: {session_tenancy})`
- Otherwise: proceed normally.

Cross-reference `scoped_domain_knowledge` for CDC exclusion columns and inject into `TargetWriter` params.

**Detection Rule:**
```
IF scoped_domain_knowledge contains any of:
  - "cdc_exclude_cols" / "cdc_exclude" / "exclude from CDC"
  - "source_extract_timestamp" / "batch_id" listed as non-business columns
THEN:
  Extract the column list and set: cdc_exclude_cols = [extracted columns]
ELSE:
  cdc_exclude_cols = []  # Empty list (TargetWriter default behavior)
```

**Enforcement (applies regardless of source):**
- The extracted `cdc_exclude_cols` MUST be written into the `"cdc"` section of `config.json` (Glue) or `config.yml` (Databricks) as the `"exclude_cols"` list. The transform template reads this value from config at runtime — do NOT hardcode it in generated transform code.
- Do NOT leave `exclude_cols` empty when mapping hint OR domain knowledge explicitly lists exclusions.
- `snapshot_mode` from `intent_identification.json` MUST be written into the `"cdc"` section as `"snapshot_mode": true|false`. This controls whether the writer expires active target rows absent from source (snapshot mode) or leaves them untouched (delta mode).

#### Step C: All-Source Verification (Post-Generation Self-Check)

After generating transformation logic, verify:
```
FOR EACH source_table IN target_table_config.source_tables:
  ASSERT source_table alias appears in the final SELECT or unionByName
  IF missing → FAIL with: "Source table '{alias}' read but never used in output"
```

This catches the defect where a source DataFrame is created but never included in the final result.

---

### Phase 3 — Transformation Logic (Simple vs. Multi-Step vs. Structured)

#### Transformation Type Dispatch (NEW — when `transformation_type` present)

Before generating column expressions, check `transformation_type` per column.

**IMPORTANT:** Regardless of `transformation_type`, Rule 3 (Data Type CAST Enforcement) always applies — if `source_datatype ≠ target_datatype`, emit an explicit `.cast(target_datatype)`. The table below shows the base generation strategy; cast is added on top when types differ. This does NOT change the core transformation logic (joins, filters, derivations, multi-source handling) — it only ensures the final column expression includes an explicit cast when types are mismatched.

| transformation_type | Generation Strategy |
|---|---|
| `Direct` | Rename + cast if types differ: `F.col("source_col").cast("target_datatype").alias("target_col")` (omit `.cast()` only when source and target types are identical) |
| `Direct - Type Cast` | Same as Direct: `F.col("source_col").cast("target_datatype").alias("target_col")` — use `target_column_datatype` for cast type |
| `Derived` | Apply `transformation_logic` expression as PySpark + `.cast(target_datatype)` if result type differs from target |
| `Lookup` | Join-based derivation + `.cast(target_datatype)` if result type differs from target |
| `null` (absent) | Fall back to current behaviour: infer from `transformation_logic` content + apply cast per Rule 3 |

#### Default Value Application (NEW — when `default_value` present)

For any column where `default_value` is not null:
- Wrap the final column expression in `F.coalesce(expr, F.lit(default_value))`
- Type-aware casting: if `default_value` is numeric and `target_column_datatype` is numeric → use numeric literal; if string → use string literal
- Applied AFTER transformation expression, BEFORE alias

**Examples:**
```python
# default_value = -99, target_datatype = DECIMAL(19,2)
F.coalesce(F.col("amount"), F.lit(-99).cast("decimal(19,2)")).alias("amount")

# default_value = "NA", target_datatype = VARCHAR(10)
F.coalesce(derived_expr, F.lit("NA")).alias("description")

# default_value = 0, transformation_type = Direct
F.coalesce(F.col("source_col"), F.lit(0)).alias("target_col")
```

#### Multi-Source Generation Mode Selection

**BEFORE generating any column that references multiple source tables**, determine generation mode:

```
IF column.structured_transformation is NOT null:
  MODE = STRUCTURED  → use structured transformation logic (deterministic, preferred)
ELSE:
  MODE = NL_INTERPRETATION  → interpret transformation_logic free-text using Rule 11
  EMIT advisory: "# ADVISORY: Join/filter logic interpreted from natural language — verify join type, conditions, and filter completeness"
  IF column.join_logic_missing == true:
    LOG INFO: "Column '{target_column_name}' uses NL interpretation for multi-source join.
      Structured format (Driver Table) recommended for deterministic output."
```

Both modes produce valid PySpark. Structured mode is deterministic (no advisory comments needed). NL interpretation mode is best-effort and always emits advisory comments for developer review.

#### Structured Transformation Logic (when `structured_transformation` present)

When a column has `structured_transformation` populated (parsed by mapping-parser-agent Phase 3c), generate multi-step PySpark from the structured definition:

**Step 1 — Identify Driver Table and Apply Driver Conditions:**
```python
driver_df = self.source_data['{driver_table_alias}']
# If driver_conditions is non-empty, apply filters to driver table FIRST
# driver_conditions: ["Filter status NOT IN ('CLO','RED','WOF')", "Filter dw_bus_dt={control_Date}"]
driver_filtered = driver_df.filter(
    ~F.col("status").isin("CLO", "RED", "WOF") &
    (F.col("dw_bus_dt") == current_business_date)
)
# If driver_conditions is empty [], use driver_df as-is (no filtering)
```

**Step 2 — Apply Table Conditions (pre-join filters on ALL joined tables):**
For each join where `table_conditions` is non-empty:
```python
# table_conditions: ["Filter limit_type='Base' and dw_bus_dt={control_Date}", "pick latest record based on source_create_timestamp"]
table2_df = self.source_data['table2']
table2_filtered = table2_df.filter(
    (F.col("limit_type") == "Base") & (F.col("dw_bus_dt") == current_business_date)
)
# "pick latest record" → ROW_NUMBER dedup
w = Window.partitionBy(<join_key>).orderBy(F.col("source_create_timestamp").desc())
table2_deduped = table2_filtered.withColumn("_rn", F.row_number().over(w)).filter(F.col("_rn") == 1).drop("_rn")
```

**Step 3 — Generate Joins (in order, starting from filtered driver):**
```python
joined_df = driver_filtered  # Use filtered driver (or raw driver_df if no driver_conditions)
for join in structured_transformation['joins']:
    joined_df = joined_df.join(
        <filtered_or_raw_table>,
        on=<parse join_conditions to PySpark expression>,
        how=join['join_type'].lower()
    )
```

**Step 4 — Apply Value Expression:**
Parse `value_expression` and generate final column derivation:
- "Round off X to N decimal points" → `F.round(F.col("X"), N)`
- "Sum of X and Y" → `F.col("X") + F.col("Y")`
- Free-text expressions → translate to PySpark using existing logic

**Integration with existing multi-step support:**
- Structured transformation columns contribute their join/filter/derive steps to the overall `transformation_steps` array for the target table
- Multiple columns may reference the same driver table and joins — deduplicate join operations (generate join ONCE, derive multiple columns from joined result)

#### Single-Step Transformation
For simple mappings without transformation_steps and without structured_transformation:
- Apply the `transformation_logic` as PySpark expressions
- Reference source columns using mapping Excel column names (authoritative source)
- Apply explicit CASTs from `transformation_logic` column when source/target types differ
- Apply domain knowledge source column quirks as explicit CASTs (e.g. `CAST(date_int_col AS DATE)`) — these take precedence over auto-CAST
- Generate simple SELECT with column aliases, respecting Phase 3.5 Rule 1 (mapping order) and Rule 2 (direct mapping simplification)

#### Multi-Step Transformation (NEW)
If `transformation_steps` array present in target_table_config:
1. **Extract step information** from mapping document:
   - step_number, step_name, type (join|filter|column_derivation|aggregation|select)
   - join_condition, join_type, filter_conditions, derived_columns, etc.

2. **Generate sequential transformation code:**
   - **Step 1 (Join):** Create temp views and execute LEFT/INNER JOIN via spark.sql()
   - **Step 2 (Filter):** Apply business rule filters (AND/OR logic)
   - **Step 3 (Aggregation):** GROUP BY / window functions if needed
   - **Step 4 (Column Derivation):** Compute intermediate + final columns
   - **Step 5 (Select):** Final column selection and rename

3. **Insert Lineage Break / Staging Operations (Conditional on Config + Volumetrics):**

   **Decision logic for activation:**
   ```
   IF config has staging.checkpoint_path (resolved from environments block)
     AND source_volumetrics available
     AND (total_day0_gb > 50 OR total_day1_gb > 10 OR domain_knowledge mentions OOM/checkpoint/staging)
   THEN: ENABLE lineage breaks (active, uncommented code)
     _lineage_break_path = self.config.get("staging", {}).get("checkpoint_path")
     - After large joins (>1GB per side):
         joined_df.write.mode("overwrite").parquet(f"{_lineage_break_path}/step_joined")
         joined_df = self.spark.read.parquet(f"{_lineage_break_path}/step_joined")
     - After complex aggregations (3+ sequential groupBy):
         agg_df.write.mode("overwrite").parquet(f"{_lineage_break_path}/step_aggregated")
         agg_df = self.spark.read.parquet(f"{_lineage_break_path}/step_aggregated")
   ELSE: Leave as COMMENTS (developer enables manually)
     - `# df.write.mode("overwrite").parquet(f"{_lineage_break_path}/step_name")`
     - `# df = self.spark.read.parquet(f"{_lineage_break_path}/step_name")`

   NOTE: Do NOT use spark.sparkContext.setCheckpointDir() or df.checkpoint() —
   these are blocked on Shared Access Mode / Serverless ([JVM_ATTRIBUTE_NOT_SUPPORTED]).
   ```

   **Staging writes (more aggressive — for very large pipelines):**
   When total_day0_gb > 100 OR domain knowledge explicitly mentions intermediate writes/staging:
   ```python
   # Write intermediate result to staging volume (enables restart from this point)
   joined_df.write.mode("overwrite").parquet(f"{self.staging_path}/step1_joined")
   joined_df = self.spark.read.parquet(f"{self.staging_path}/step1_joined")
   ```

4. **Register Intermediate DataFrames as Temp Views:**
   - For spark.sql() blocks: `source_df.createOrReplaceTempView('source_v')`
   - Semantic naming: `{{alias}}_v`, `joined_df_v`, `filtered_df_v`

5. **Maintain Column Lineage:**
   - Each step produces intermediate DataFrame with semantic name
   - Example: `step1_df`, `joined_df`, `filtered_df`, `transformed_df`, `final_df`
   - Document in inline comments

**Example Multi-Step Generated Code:**
```python
# STEP 1: Read sources and create temp views
account_src = self.source_data['account_src']
rates_src = self.source_data['rates_src']
account_src.createOrReplaceTempView('account_src_v')
rates_src.createOrReplaceTempView('rates_src_v')

# STEP 2: Join
joined_df = spark.sql("""
    SELECT
        a.account_id, a.balance, r.rate_percentage
    FROM account_src_v a
    LEFT JOIN rates_src_v r ON a.rate_id = r.rate_id
""")
# LINEAGE BREAK (COMMENTED — Enable only if join causes OOM):
# _lineage_break_path = self.config.get("staging", {}).get("checkpoint_path")
# joined_df.write.mode("overwrite").parquet(f"{_lineage_break_path}/step_joined")
# joined_df = self.spark.read.parquet(f"{_lineage_break_path}/step_joined")

# STEP 3: Filter
filtered_df = joined_df.filter(F.col('balance') > 0)

# STEP 4: Compute derived columns
transformed_df = filtered_df.withColumn(
    'rate_pct', F.col('rate_percentage') / 100
).withColumn(
    'annual_interest', F.col('balance') * F.col('rate_pct')
)

# STEP 5: Select and rename
final_df = transformed_df.select(
    'account_id', 'balance', 'rate_pct', 'annual_interest'
)

# LINEAGE BREAK (COMMENTED — Enable only if complex DAG causes OOM):
# _lineage_break_path = self.config.get("staging", {}).get("checkpoint_path")
# final_df.write.mode("overwrite").parquet(f"{_lineage_break_path}/step_final")
# final_df = self.spark.read.parquet(f"{_lineage_break_path}/step_final")

return final_df
```

### STTM-Provided Multi-Step Transformation Steps

When `mapping_parsed.json` contains `structured_transformation.type == "multi_step"` with a `steps[]` array from STTM, use it directly instead of parsing the Business Logic text:

Each step in the STTM-provided array contains:
```json
{
  "step_number": 1,
  "step_name": "Normal risk score",
  "type": "join",
  "source_table": "s_acctdb.account_base",
  "join_condition": "ab.scorecard_id = rp.scorecard_id",
  "join_type": "INNER",
  "join_table": "r_refdb.risk_params",
  "additional_joins": [],
  "filter_conditions": ["ab.behaviour_score > 31"],
  "derived_columns": {"risk_score": "1/(1+EXP(...))"},
  "grain": ["account_id"],
  "destination": "work_db.risk_normal",
  "staging_hint": null
}
```

**Processing rules:**
1. Iterate steps in `step_number` order
2. For each step, generate the corresponding PySpark DataFrame operation
3. Use `step_name` for DataFrame variable naming (see Step→DataFrame naming convention below)
4. Respect `staging_hint` (CHECKPOINT → write to staging; PERSIST → in-memory cache; null → volumetric heuristic)
5. `additional_joins` contains secondary joins within the same step: `[{"table": "...", "type": "LEFT", "on": "..."}]`
6. `destination` names the intermediate DataFrame/table

**Fallback:** If `steps[]` is absent, fall back to parsing Business Logic text for multi-step lineage.

**Operation Conversion Reference:**
When processing multi-step transformations with UPDATE, DELETE, TRUNCATE, MERGE, or RENAME operations, load and follow the patterns in `agents/refs/transform-multi-step-operation-conversion.md`. This reference document provides exact PySpark conversion patterns for each STTM Transformation Lineage operation type.

### Step→DataFrame Naming Convention

When STTM provides `step_name` in each step, use it as the DataFrame variable name (sanitized to valid Python):

```python
def sanitize_step_name(step_name: str) -> str:
    """Convert STTM step name to valid Python variable name."""
    name = step_name.lower().strip()
    name = re.sub(r'[^a-z0-9_]', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    return f"{name}_df"
```

**Example:**
```python
# TRANSFORMATION STEP MAP:
# Step 1 (Normal risk score) → normal_risk_score_df
# Step 2 (Fallback risk score) → fallback_risk_score_df
# Step 3 (Merge + derive band) → merge_derive_band_df

# Step 1 (Normal risk score)
normal_risk_score_df = account_base_df.join(
    risk_params_df,
    on=account_base_df.scorecard_id == risk_params_df.scorecard_id,
    how="inner"
).filter(...)

# Step 2 (Fallback risk score)
fallback_risk_score_df = account_base_df.join(...)

# Step 3 (Merge + derive band)
merge_derive_band_df = account_base_df.join(
    normal_risk_score_df, ...
).join(
    fallback_risk_score_df, ...
)
```

The `# TRANSFORMATION STEP MAP:` comment block MUST be emitted at the top of the transformation() function body when multi-step transforms are generated. It maps STTM step names to generated DataFrame variable names for audit trail.

**Fallback naming:** If `step_name` is not provided, use `step{N}_df` (e.g., `step1_df`, `step2_df`).

### Staging Hint Propagation from STTM

When STTM provides `staging_hint` in `structured_transformation.steps[]`, the transform generator MUST respect it:

| `staging_hint` value | Generated code |
|---|---|
| `"CHECKPOINT"` | **Active** (uncommented) parquet write + re-read: `step_df.write.mode("overwrite").parquet(staging_path)` then `step_df = spark.read.parquet(staging_path)` |
| `"PERSIST"` | `step_df.persist(StorageLevel.MEMORY_AND_DISK)` + unpersist after consumption |
| `null` | Use existing volumetric threshold heuristic (active if `total_day0_gb > 50`, commented otherwise) |

**Priority order for staging decision:**
1. STTM-provided `staging_hint` (highest priority — derived from ETL pattern analysis)
2. Volumetric threshold (`total_day0_gb > 50` → active staging)
3. Domain knowledge mentions staging → active staging
4. Default → commented staging blocks

**NEVER use `spark.sparkContext.setCheckpointDir()` or `df.checkpoint()`** — blocked on Shared Access Mode / Serverless clusters.

### Phase 3.5 — Column-Level Generation Rules

> **SCOPE NOTE:** Rules 1 and 3 below govern ONLY the final output column ordering and explicit datatype casting. They do NOT alter or constrain the core transformation generation logic — joins, filters, aggregations, derivations, multi-source handling, structured transformations, NL interpretation, or any other Phase 3 logic remains unchanged. These rules apply strictly at the final `.select()` / output stage.

#### Rule 1: Column Ordering (Final SELECT)

The final output DataFrame MUST emit columns in the same order as the target table's DDL-equivalent schema:
- **Databricks**: Column order from the Iceberg DDL (`CREATE TABLE` column sequence)
- **Glue**: Column order from the mesh JSON (`fields[]` array sequence)

Both are generated from `mapping_parsed.json` and share the same ordering. When DDL/mesh artefacts are available in session state, use them as the authoritative reference for column order. If only `mapping_parsed.json` is available (DDL/mesh not yet generated), fall back to `column_mappings[]` array order.

This ensures the transform output is structurally aligned with the physical table definition and prevents positional write mismatches.

```python
# GOOD: columns in DDL/mesh schema order
final_df = transformed_df.select('account_id', 'customer_name', 'balance', 'status', 'dw_bus_dt', 'dw_lod_tmp')

# BAD: arbitrary/alphabetical order (mismatches DDL)
final_df = transformed_df.select('balance', 'account_id', 'status', 'customer_name', 'dw_lod_tmp', 'dw_bus_dt')
```

#### Rule 2: Direct Mapping Simplification

When `transformation_logic` is "Direct mapping" or null/empty:
- Source column name == target column name → `F.col('col_name')` (no alias needed)
- Source column name != target column name → `F.col('source_col').alias('target_col')`

Do NOT generate redundant `.alias('x')` when source and target names are identical.

#### Rule 3: Data Type CAST Enforcement

For **every transformation type** (`Direct`, `Direct - Type Cast`, `Derived`, `Lookup`, or absent), apply an explicit `.cast(target_datatype)` when `source_datatype` and `target_datatype` differ in the mapping. This rule has no exceptions based on transformation type.

| Source Type (Mapping) | Target Type (Mapping) | Action |
|---|---|---|
| `FLOAT` | `DECIMAL(15,2)` | `.cast('decimal(15,2)')` — **MANDATORY** |
| `STRING` | `INT` | `.cast('int')` — **MANDATORY** |
| `TIMESTAMP` | `DATE` | `.cast('date')` — **MANDATORY** |
| `INT` | `BIGINT/LONG` | `.cast('long')` — **MANDATORY** |
| Same type | Same type | No cast needed |

**Rules:**
- Cast applies to ALL transformation types — no exceptions (including `Direct`, `Derived`, `Lookup`)
- If `transformation_logic` already contains an explicit CAST to the correct target type → do NOT double-cast
- CASTs are applied AFTER transformation logic, BEFORE final `.alias()`
- Domain knowledge source column quirks (explicit CASTs) take precedence over this auto-detection
- When in doubt whether types match (e.g., `VARCHAR(50)` vs `STRING`), apply the cast — explicit is safer than implicit

#### Rule 4: Nullable Awareness

If a column has `nullable = false` in the mapping AND `default_value` is null/absent AND the source is potentially nullable (LEFT JOIN output):
- Emit a warning comment in generated code: `# WARNING: {col} declared NOT NULL but no default specified — verify source guarantees non-null`
- Do NOT inject coalesce or filter automatically — this is a data quality signal for review

#### Rule 5: Multi-Source Column Disambiguation

After any JOIN operation, ALWAYS qualify column references with the source table alias:

```python
# GOOD: qualified references after join
joined_df.select(
    F.col('account_src.account_id'),
    F.col('account_src.status').alias('account_status'),
    F.col('rates_src.rate_pct')
)

# In spark.sql():
SELECT a.account_id, a.status AS account_status, r.rate_pct
FROM account_src_v a LEFT JOIN rates_src_v r ON ...

# BAD: unqualified after join (ambiguous if both have 'status')
joined_df.select(F.col('status'))
```

**Exception:** Single-source tables (only one source_table) do NOT require qualification.

**Note:** Rule 5 applies to post-join SELECT/filter column references; Rule 5b below applies to the `.join()` condition itself.

#### Rule 5b: Symmetric vs Asymmetric Join Key Syntax (MANDATORY)

Choose PySpark `.join()` syntax based on key name equality:

**SYMMETRIC** (left_col == right_col) → LIST syntax (auto-deduplicates):
```python
# Single symmetric key — list syntax keeps ONE copy
joined_df = main_df.join(lookup_df, ["question_id"], "left")

# Multiple/compound symmetric keys — ALL keys same-name on both sides
joined_df = orders.join(items, ["order_id", "line_id"], "inner")
# Equivalent to: orders.order_id = items.order_id AND orders.line_id = items.line_id
# Both keys are symmetric → single list with all key names
```

**ASYMMETRIC** (left_col != right_col) → EXPRESSION syntax + DROP right key:
```python
# Expression syntax required (different column names cannot use list syntax)
# ALWAYS drop the right-side join key after join — it served its purpose and is now redundant
joined_df = main_df.join(
    lookup_df,
    main_df["customer_survey_id"] == lookup_df["unique_survey_ref"],
    "left"
).drop(lookup_df["unique_survey_ref"])

# WHY drop: the right key column (unique_survey_ref) is semantically equivalent to left key
# (customer_survey_id) post-join. Keeping it risks:
# 1. Column bloat in chained joins
# 2. Ambiguity if a subsequent join brings another "unique_survey_ref" column
# 3. Unnecessary data in the final SELECT
```

**MIXED** (compound join with some symmetric + some asymmetric sub-keys) → EXPRESSION syntax for ALL keys + `.drop()` ALL right-side keys:
```python
# region_id is symmetric, local_id→global_ref is asymmetric — list syntax cannot be used
joined_df = main_df.join(
    lookup_df,
    (main_df["region_id"] == lookup_df["region_id"]) &
    (main_df["local_id"] == lookup_df["global_ref"]),
    "left"
).drop(lookup_df["region_id"], lookup_df["global_ref"])
```
**EXCEPTION**: Do NOT drop the right key when it maps to a target column or has independent semantic meaning — keep it and reference via qualified name downstream.

**LOCKED PREDICATE INTERACTION**: When locked predicate has `left_col == right_col`
(e.g., `customer_response.question_id = question.question_id`), list syntax `["question_id"]`
IS the correct fidelity-preserving translation — no drop needed (only one copy exists).

**WHY**: Expression syntax with same-name keys creates duplicate columns. Any subsequent
F.col("col") throws AnalysisException. For asymmetric keys, the right key column is a
redundant foreign key reference that should be pruned to keep the DataFrame clean for
downstream operations. This rule has NO exceptions for multi-source tables.

#### Rule 6: Day0 vs Day1 — Transformation Logic Identity

The `transformation()` method business logic is **IDENTICAL** for day0 and day1 files. The ONLY difference between day0 and day1 is:
- **Day0**: Derives audit columns per table type (see `${CLAUDE_PLUGIN_ROOT}/agents/refs/audit-columns-by-table-type.md`)
- **Day1**: Outputs business columns ONLY (writer derives audit columns — CDC merge for SCD2, SCD1 UPSERT for SCD1, append for Transactional)

Do NOT generate different joins, filters, derivations, or column expressions between day0 and day1 unless domain knowledge EXPLICITLY specifies different transformation rules per load type (extremely rare).

When `load_type = 'full_then_incremental'` and both files are generated: copy the business logic verbatim into both, differing ONLY in the audit column section.

**BAU-Only Mode (Day0 Reference Provided):**

When generating Day1 only (`load_type='BAU'`) and `day0_reference_logic` is provided in the input context:
- Business logic (joins, conditionals, column derivations, lookup joins, survey type resolution, WM-vs-non-WM branching) MUST be identical to the Day0 reference
- The ONLY permitted differences from Day0:
  1. Date filter applied by SourceReader (not inline in transformation logic)
  2. SCD2 audit columns (eff_start_date, eff_end_date, active, dw_lod_tmp, dw_upd_lod_tmp) OMITTED — TargetWriter/run_cdc injects them
  3. For Transactional tables: dw_lod_tmp omitted (writer injects)
- If Day0 contains conditional logic (F.when, survey_type branching, WM checks), reproduce VERBATIM
- If Day0 contains lookup joins (LEFT JOIN to reference/decode tables), reproduce identically
- DO NOT simplify, refactor, or "optimize" business logic from Day0 — faithfulness over improvement

#### Rule 7: table_description Usage

`table_description` from `mapping_parsed.json` is **informational only** — it provides business context about the target table. It is NOT used in code generation logic. Include in the header comment block for documentation purposes:
```python
# Table Description: {table_description}
```

#### Rule 8: Per-Column additional_context

Per-column `additional_context` values (if populated in mapping rows) are **advisory comments only**. They do NOT change the generated transformation expression — only `transformation_logic` and `structured_transformation` fields drive code generation. Per-column additional_context may be included as inline comments above complex derivations for developer context.

#### Rule 9: Aggregate/Window Function Translation (Free-Text → PySpark)

When `transformation_logic` contains free-text aggregate or window function descriptions, translate using these patterns:

| Free-Text Pattern | PySpark Translation |
|---|---|
| "Sum of X" / "Total X" | `F.sum('X')` |
| "Count of X" / "Number of X" | `F.count('X')` / `F.count(F.when(F.col('X').isNotNull(), 1))` |
| "Max of X" / "Maximum X" | `F.max('X')` |
| "Min of X" / "Minimum X" | `F.min('X')` |
| "Average of X" / "Mean X" | `F.avg('X')` |
| "ROW_NUMBER partitioned by X ordered by Y" | `F.row_number().over(Window.partitionBy('X').orderBy('Y'))` |
| "RANK partitioned by X ordered by Y" | `F.rank().over(Window.partitionBy('X').orderBy('Y'))` |
| "CASE WHEN X THEN Y ELSE Z" | `F.when(X, Y).otherwise(Z)` |
| "CASE WHEN X THEN Y WHEN A THEN B ELSE Z" | `F.when(X, Y).when(A, B).otherwise(Z)` |
| "Concatenate X and Y with separator" | `F.concat_ws(separator, F.col('X'), F.col('Y'))` |
| "Round X to N decimal places" | `F.round(F.col('X'), N)` |
| "Substring of X from position P length L" | `F.substring(F.col('X'), P, L)` |
| "Upper case of X" / "Lower case of X" | `F.upper(F.col('X'))` / `F.lower(F.col('X'))` |
| "Trim X" | `F.trim(F.col('X'))` |
| "Coalesce X, Y" / "X if not null else Y" | `F.coalesce(F.col('X'), F.col('Y'))` |
| "Current date" / "Today" | `F.current_date()` |
| "Current timestamp" | `F.current_timestamp()` |

**Rules:**
- Always check if the aggregate requires a GROUP BY (if so, generate `.groupBy().agg()` pattern)
- Window functions require explicit `Window.partitionBy().orderBy()` — never use without partition clause
- If the free-text is ambiguous or does not match known patterns → use the literal text as a spark.sql() expression and emit `# TODO: Verify generated SQL from free-text logic`

#### Rule 9b: Literal Value Fidelity in Expressions

When `transformation_logic` contains explicit literal comparison values (string constants, numeric constants, value lists in IN clauses), reproduce those **exact values** in generated PySpark code.

**NEVER:**
- Substitute a different literal because the target column name suggests another value
- Infer from neighboring columns in the mapping that a different literal "makes more sense"
- Treat an apparent inconsistency between column naming and `transformation_logic` literals as a typo to correct
- Apply pattern-matching across sibling columns to "harmonise" filter/condition values

**When a mapping literal appears inconsistent with surrounding context:**
1. **USE THE MAPPING VALUE** — generate code exactly as the `transformation_logic` field specifies
2. Emit an advisory comment flagging the observation for human review:

```python
# ADVISORY: Mapping transformation_logic specifies literal '<value>' — differs from
# pattern observed in sibling columns; verify with data modeller if intentional
```

The mapping author's intent is authoritative. Perceived inconsistencies in literal values are for the data modeller to resolve — not the generator.

#### Rule 10: Source Column Authority

The mapping document is the **authoritative source** for column names. Always generate code using the mapping Excel source column name — never HALT or skip a column because it cannot be independently verified. Code review and `/validate` will flag discrepancies.

#### Rule 11: NL Join & Filter Interpretation (Free-Text → PySpark)

**Externalized to**: `${CLAUDE_PLUGIN_ROOT}/agents/refs/transform-nl-interpretation-rules.md`

**Load condition:** Read this file in GATHER phase (Turn 1) ONLY if any column has `MODE = NL_INTERPRETATION` (i.e., references multiple source tables AND `structured_transformation` is null, OR single-source with filter language in transformation_logic and no structured_transformation). If ALL columns use DIRECT_MAP or STRUCTURED mode, skip — NL rules are not needed.

---

### Phase 4 — Crypto UDFs (both platforms — via spark.sql() ONLY)

**Externalized to**: `${CLAUDE_PLUGIN_ROOT}/agents/refs/transform-crypto-udf-rules.md`

**Load condition:** Read this file in GATHER phase (Turn 1) ONLY if `crypto_flags.has_crypto == true` for this target table. If `has_crypto == false`, skip entirely — do not load crypto rules into context.

### Phase 5 — Domain Knowledge Soft Context + Additional Context from Mapping

**Externalized to**: `${CLAUDE_PLUGIN_ROOT}/agents/refs/transform-domain-knowledge-examples.md`

**Load condition:** Read this file in GATHER phase (Turn 1) ONLY if `scoped_domain_knowledge` is not null and not "No specific domain knowledge for this table". If domain knowledge is absent, skip — the hierarchy of authority and usage patterns are not needed.

**Key rule (always applies regardless of file load):** Domain knowledge and additional_context are ADVISORY — they NEVER override mapping Excel. Use to ADD context (comments, CASTs, hints), not to CHANGE what's in the mapping.

### Phase 5.5 — PySpark Generation Guardrails (Both Platforms)

**Externalized to**: `${CLAUDE_PLUGIN_ROOT}/agents/refs/transform-pyspark-guardrails.md` (read in GATHER phase, Turn 1).

Covers: Prohibited patterns, performance optimization rules, null safety, data skew mitigation, and data volume/partition signals.

### Phase 5.6 — Volumetric Optimization Rules (Both Platforms)

**Externalized to**: `${CLAUDE_PLUGIN_ROOT}/agents/refs/transform-volumetric-optimization.md`
**Load condition:** Read this file in GATHER phase (Turn 1) ONLY if `scoped_volumetrics` is non-null. If `scoped_volumetrics` is null → skip (Phase 5.6 is inactive).

---

### Phase 6 — Header Comment Block

Include in every generated file:
```python
# ============================================================
# Generated: {timestamp}
# Session:   {session_id}
# Platform:  {platform}
# Data Product Type: {data_product_type}
# Table Type: {table_type}  Load Type: {load_type}
# Open Placeholders at generation: {open_placeholders or "None"}
# ============================================================
```

---

## Platform-Specific Writer Usage (Conditional Load in GATHER Phase)

**Load condition:** Read ONLY the file matching `session_state.platform`. Do NOT load both — the platform is locked before this agent is invoked (G1 resolved during `/identify-intent`).

- If platform == `"glue"` → read `${CLAUDE_PLUGIN_ROOT}/agents/refs/transform-platform-glue.md`
- If platform == `"databricks"` → read `${CLAUDE_PLUGIN_ROOT}/agents/refs/transform-platform-databricks.md`

These references define:
- TargetWriter initialization pattern (constructor parameters differ by platform)
- Writer dispatch model (Glue: TargetWriter.write(); Databricks: TargetWriter wrapping tableIOUtils/run_cdc)
- Source table FQN resolution (Glue: glue_read_table; Databricks: spark.table with source_catalog)
- CDC config resolution and run_cdc internal parameters (Databricks only)
- Class structure (Glue: function-based; Databricks: class-based notebook)

---

## Anti-Hallucination Rules

> **Core rules**: See `${CLAUDE_PLUGIN_ROOT}/agents/refs/anti-hallucination-core.md`
> **Component boundary & config contract violations**: See always-loaded refs `transform-component-boundaries.md` and `transform-config-contract.md` — do not duplicate SourceReader/TargetWriter/wrapper/driver logic, filters declared in config, or broadcast scope rules.

- ❌ Never create per-source-table files — only per-target-table files
- ❌ Never invent target table/column names — use ONLY names from mapping_parsed.json
- ❌ Never invent source table/column names — use ONLY names from mapping_parsed.json
- ❌ Never derive table/column names by composition (e.g., appending _enriched, _staging, _v2)
- ❌ Never add columns not present in the mapping document (exception: audit columns that the mapping explicitly includes OR that TargetWriter/run_cdc injects automatically — do NOT force-add audit columns missing from the mapping)
- ❌ Never fabricate transformation logic — implement EXACTLY what mapping Excel Business Logic column specifies
- ❌ Never substitute a "better" expression for what the mapping states — faithfulness over optimization
- ❌ Never substitute a literal comparison value (string, number, list) from `transformation_logic` with a different value inferred from column names, sibling columns, or surrounding context — reproduce the mapping value verbatim even if it appears inconsistent with the column name or group
- ❌ Never invent join conditions, filters, or derivations not stated in the mapping
- ❌ Never assume all target tables have the same load_type
- ❌ Never discard a source system — if PK is composite with source_system_key, EVERY source produces rows (UNION architecture)
- ❌ Never generate unionByName() when source_systems is non-empty — each source_system transform handles one flow only
- ❌ Never leave cdc_exclude_cols empty when mapping hint (cdc_exclude_cols_hint) OR domain knowledge explicitly lists CDC exclusions
- ❌ Never perform as-of/range joins without ROW_NUMBER dedup guard on the dimension table (when domain knowledge specifies dedup rules)
- ❌ Never call a method on SourceReader or TargetWriter that does not exist in the utility source file
- ❌ When `target_io` is present in config, do NOT generate `spark.table()` calls for the target or call any `tableIOUtils` methods. TargetWriter handles the file write dispatch automatically via `write()`.
- ❌ Never invent utility method names (e.g., `reader.read()`, `reader.load_source()`, `writer.write_data()` do NOT exist)
- ❌ Never add constructor parameters beyond what the utility source file defines
- ✓ Always use `self.reader.read_source_data()` (returns dict[alias→DataFrame]) — NOT `self.reader.read()` or `self.reader.load()`
- ✓ Always use `self.writer.write(df)` (single DataFrame) — NOT `self.writer.write_data()` or `self.writer.save()`
- ❌ Never use expression syntax (`df["col"] == other["col"]`) when left_col and right_col share the same name — use list syntax `["col"]`
- ✓ Always use list syntax `["col_name"]` for symmetric join keys (same column name on both sides)
- ❌ Never set eff_end_date = '3499-12-31' for ALL records as a default — temporal stitching logic must come from domain knowledge or mapping
- ❌ Never use LEAD(next_group_start) as eff_end_date without gap-aware guard — always compare with MAX(source eff_end_date) to detect temporal gaps (see transform-temporal-stitching-reference.md Step 7)
- ❌ Never separate temporal boundary derivation from business column transformation when the chosen stitching pattern (C or D) structurally integrates them — the transformation is ONE cohesive operation
- ❌ Never treat audit column transformation_logic the same as business columns — audit columns follow team-specific patterns from domain knowledge or explicit mapping entries
- ❌ Never proceed with Day 0 generation without temporal stitching logic for eff_end_date and active — ask user the scenario questions if not found in domain knowledge or mapping
- ❌ Never use `F.cast('type', col)` or `F.cast(col, 'type')` — `F.cast()` does not exist in PySpark. Use `col.cast('type')` (a Column method) instead.
- ❌ Never use `__import__(...)` for any PySpark module — use standard `import` / `from ... import` statements. Window, F, DataFrame are always available via the cluster environment.
- ❌ Never add an import not in the APPROVED_ADDITIONAL_IMPORTS whitelist — the whitelist is exhaustive
- ❌ Never include a whitelisted import unless the generated transformation logic demonstrably uses the imported symbol
- ✓ Always self-verify: scan generated transformation logic for symbol references before populating `additional_imports`
- ✓ Always lookup load_type per target table from intent_identifier
- ✓ Always run Phase 2.5 (Source Architecture Analysis) BEFORE generating transformation logic
- ✓ Always verify every source_table alias appears in the final output (Step C self-check)
- ✓ Domain knowledge business rules → inline comments only
- ✓ File naming must use TARGET table name, not source table name

---

## Source Column Allow-List Enforcement (HARD CONSTRAINT)

**Externalized to**: `${CLAUDE_PLUGIN_ROOT}/agents/refs/transform-source-column-allowlist.md`
**Load condition:** Read this file in GATHER phase ONLY if `session/source_column_allowlist.json` exists.

---

## Join Predicate & Literal Value Enforcement (HARD CONSTRAINT)

**Externalized to**: `${CLAUDE_PLUGIN_ROOT}/agents/refs/transform-locked-predicates.md`
**Load condition:** Read this file in GATHER phase ONLY if `session/extracted_predicates.json` exists.

---

## Quick Reference (Do NOT duplicate rules stated above)

- Per-TARGET-table only (NOT per-source-table) — see "Outputs" section for file naming
- Conditional generation by load_type — see "Outputs" section for rules
- Multi-step support: join→filter→aggregation→derivation (from `transformation_steps`)
- Multi-table orchestration: handled by command layer (batch-parallel Task spawning), NOT by this agent
- ❌ Do NOT handle S3/date control reading (that's wrapper.py/DateControl)
- ❌ Do NOT implement SourceReader/TargetWriter (templates already reference these)


---

## Standalone Invocation

> **Pattern**: See `${CLAUDE_PLUGIN_ROOT}/agents/refs/standalone-invocation.md`

Minimum required context:
- target_table_config (columns + transformation_steps)
- intent (load_type + table_type)
- platform ('glue' or 'databricks')
- crypto_flags (per-column crypto metadata)
- filter manifest (filter expressions per source)

## Uncertainty Disclosure

> **Canonical rules**: See `${CLAUDE_PLUGIN_ROOT}/agents/refs/uncertainty-disclosure.md`

## Extension Points

- Custom transform templates for new table types or patterns
- Additional import whitelist entries for domain-specific libraries
- New write-pattern dispatch for custom table types beyond SCD1/SCD2/Transactional

## Principles compliance note

This agent operates independently and can be invoked standalone with explicit inputs/outputs. It does not enforce workflow sequencing. When operating with incomplete or placeholder data, outputs are marked accordingly.

> **Principle 7 tension**: The command layer enforces generation ordering via safety HALTs (see README § "Workflow Enforcement via Safety HALTs"). This agent's core logic is independently invocable, but the command that invokes it may HALT if upstream data dependencies are unmet. Data correctness outweighs strict principle adherence.

## Your Inputs

- `session/intent_identification.json` with load_type, table_type, and primary keys for the target table
- Generated config file (platform-specific: `config.json` for Glue, `config.yml` for Databricks)
- `session/mapping_parsed.json` with column mappings, source references, and transformation logic per column
- Platform-specific transform templates from `${CLAUDE_PLUGIN_ROOT}/templates/`
- `session/crypto_flags.json` with per-column crypto UDF metadata (when crypto is flagged)

## Your Outputs

- PySpark transform scripts conditional on load_type: `day0` only, `day1` only, or both
- Glue output: `{db}_{table}_transform_day0.py` and/or `{db}_{table}_transform_day1.py`
- Databricks output: Databricks notebook `.py` files in `day0/` and/or `day1/` directories
- Each transform contains: source reads, column mappings, join/filter/derivation logic, audit columns, and write dispatch

## Flags

- Missing source columns referenced in transformation logic but absent from mapping — **WARNING**
- Crypto UDF pattern incomplete (flagged column but no DE name extractable) — **HALT**
- Source-to-target datatype mismatch without explicit `.cast()` in mapping logic — **WARNING** (defensive cast auto-applied)
- Structured transformation parse failure (Driver Table format detected but incomplete) — **WARNING** (falls back to free-text NL interpretation)
