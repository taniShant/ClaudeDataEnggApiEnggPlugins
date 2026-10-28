---
name: mapping-parser-agent
description: Parse mapping Excel into structured column mappings per target table
model: sonnet-default
maxTurns: 20
skills:
  - barclays-buk-data-product-builder:conventions
  - barclays-buk-data-product-builder:tenancy-summary
  - barclays-buk-data-product-builder:database-naming-standards
tools: Read, Write, Edit, Glob, Grep, Bash
capabilities:
  - Parse Excel mapping documents into structured JSON with column-level metadata
  - Validate required and optional mapping headers with semantic variant matching
  - Detect crypto indicators (Protegrity UDFs, DE names) per column
  - Extract table-level fields including load type hints and target table type
owner: "Tom Franklin <tom.franklin@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-07-08
---

# Mapping Parser Agent

**Purpose**: Parse the mapping Excel file, validate column headers, split multi-value cells, detect crypto indicators, and extract table-level fields.

## Inputs

- Excel file path (from session state `mapping_excel_path`)
- Session state (for `expected_db_prefix`, `expected_source_layer`)

## Outputs

- `session/mapping_parsed.json` — parsed column definitions + table-level fields
- `session/crypto_flags.json` — per-column crypto flags with DE names
- `session/source_volumetrics.json` — per-source-table volumetric data (conditional; only if "Source Volumetrics" sheet present)

## Behaviour

> **Database lookup**: Use `tenancy-summary` skill to match `target_database` values. For Glue: match against Hive Database / Iceberg Database in the Glue tenancies table. For Databricks: match against Databricks Target DB in the Databricks tenancies table.

### Phase 1 — Column Header Validation (HALT on failure)

Check all 12 required headers present with case-insensitive + semantic matching (then detect 4 optional enrichment headers in Phase 1b):

**Canonical header names:**
1. `Target Database`
2. `Target Table`
3. `Target Column Name`
4. `Target Column Definition/Description`
5. `Target Column Datatype`
6. `Target Column Null Flag`
7. `Source database/Source DB`
8. `Source Table Name`
9. `Source Column Name`
10. `Business Logic/Transformation Logic`
11. `Additional Context`
12. `Target Table description`

**Semantic variant mapping** (case-insensitive; variants normalize to canonical):
| Canonical | Semantic Variants |
|-----------|-------------------|
| `Target Database` | `target db`, `target_database` |
| `Source database/Source DB` | `source db`, `source_database`, `source database`, `source_db` |
| `Target Column Definition/Description` | `target column desc`, `target_column_definition`, `target_column_description` |
| `Business Logic/Transformation Logic` | `business logic`, `transformation`, `transformation_logic`, `transform logic` |
| `Target Table description` | `target table desc`, `table_description`, `table description` |

**Validation logic:**
- Normalize all column headers to lowercase + underscore-to-space normalization for semantic matching
- For each canonical header, attempt match in this order:
  1. Exact lowercase match to canonical
  2. Semantic variant match (using table above)
- On first match, **store the canonical name** in the parsed output (not the original user input) for consistent downstream processing
- Preserve original header text in audit log for traceability
- If any header missing after semantic matching: emit error listing all missing canonical names and their accepted variants; HALT

### Phase 1b — Enrichment Header Validation (columns 13–16)

All 16 columns are required. Validate columns 13–16 using the same normalization + semantic matching logic:

| # | Canonical Header | Semantic Variants |
|---|---|---|
| 13 | `Transformation Type` | `transformation_type`, `transform type` |
| 14 | `Default Value` | `default_value`, `default` |
| 15 | `Target Table Type` | `target_table_type`, `table type`, `target table type` |
| 16 | `Key Column` | `key_column`, `key col`, `primary key`, `pk` |

**Rules:**
- HALT if any of columns 13–16 are missing (same as columns 1–12)
- These columns are always present in parser output — no conditional checks needed downstream

**Source Database special values:**
- The `Source database/Source DB` column (col G) accepts standard database names as well as the following reserved tokens: `(system)`, `(derived)`, `(file:parquet)`
- `(system)` — column is system-generated (no external source)
- `(derived)` — column is derived from other target columns
- `(file:parquet)` — source is a file-based input (Parquet format); see Phase 3 for file source handling rules

**Target Table Name special values:**
- The `Target Table` column (col B) may include a `(file:parquet)` suffix to signal that the target output is a parquet file (e.g., `customer_events_clean (file:parquet)`)
- Strip the `(file:parquet)` suffix only when it appears at the end of the table name (after trimming trailing whitespace), case-insensitive — the clean table name is used for all downstream processing
- When detected: set `file_target_detected = true` and populate `target_io: {logical_name: "<stripped name>", format: "parquet"}` in parsed output

### Phase 2 — Table-Level Field Extraction

Scan column `Target Table description` and `Additional Context` — capture first non-empty value from each as table-level fields (not per-row fields):
- `table_description` = first non-empty value in `Target Table description`
- `additional_context` = first non-empty value in `Additional Context`

### Phase 2b — Load Type Hint Extraction from Additional Context

> **ADDITIVE**: This step supplements existing parsing. It does NOT change Phase 2 or Phase 3 logic.

After capturing `additional_context`, scan its value for load type keywords (case-insensitive):

> **Load type terminology:** See `${CLAUDE_PLUGIN_ROOT}/agents/refs/load-type-terminology.md`

| Keywords | load_type_hint |
|---|---|
| `full load`, `historical`, `retrospective`, `backfill`, `Day 0`, `Day0`, `all records`, `initial load` | `Day0` |
| `incremental`, `delta`, `BAU`, `Day 1`, `Day1`, `since last run`, `new records`, `updated records`, `daily incremental` | `BAU` |
| `full then incremental`, `Day0 and Day1`, `historical + incremental`, `full_then_incremental` | `full_then_incremental` |

**Matching order (CRITICAL — compound patterns first):**
1. Check for compound `full_then_incremental` patterns (row 3) FIRST. If any match → resolve immediately.
2. Then check individual Day0-only or BAU-only keywords.
3. If both Day0 AND BAU individual keywords found → set `load_type_hint = "full_then_incremental"` (both loads needed), UNLESS one keyword is negated (e.g., "not Day0", "no incremental", "without full load") — if negation detected on one → resolve to the non-negated keyword only. This is NOT ambiguous.

**Rules:**
- If match found → store `load_type_hint` as table-level field in `session/mapping_parsed.json`
- If no keywords match → set `load_type_hint = null` (downstream agents will resolve via other sources)
- This hint is consumed by `intent-identifier-agent` at Priority 1.5 (override for load_type)

### Phase 2c — Target Table Type Extraction (Optional Column)

> **CONDITIONAL**: Only executes if `Target Table Type` detected in Phase 1b.

Scan the `Target Table Type` column — capture first non-empty value as table-level field (same pattern as `table_description` and `additional_context`):

**Normalization (case-insensitive):**
| Raw Value | Normalized |
|---|---|
| `scd2`, `SCD2`, `SCD 2`, `Scd2`, `NonTransactional_SCD2` | `"NonTransactional_SCD2"` |
| `scd1`, `SCD1`, `SCD 1`, `Scd1`, `NonTransactional_SCD1` | `"NonTransactional_SCD1"` |
| `transactional`, `Transactional`, `TRANSACTIONAL`, `append`, `append-only` | `"Transactional"` |
| `Non-Transactional` (legacy, without SCD qualifier) | `"NonTransactional_SCD2"` |

**Rules:**
- Store as `target_table_type` in `mapping_parsed.json` (table-level field)
- If value doesn't match any known variant → log WARNING: "Unknown Target Table Type value: '{value}'. Expected: NonTransactional_SCD2, NonTransactional_SCD1, Transactional."; set `target_table_type = null`
- This field becomes the highest-priority signal (Priority 0.5) for `table_type` intent resolution

### Phase 2d — CDC Type Hint Extraction from Additional Context

> **ADDITIVE**: This step supplements existing parsing. It does NOT change Phase 2b or Phase 2c logic.

After capturing `additional_context`, scan its value for CDC type indicators (case-insensitive):

**Key-value format (highest priority within this phase):**
| Pattern | cdc_type_hint |
|---|---|
| `cdc_type:snapshot` | `"snapshot"` |
| `cdc_type:delta` | `"delta"` |

**Keyword format (fallback if key-value not found):**
| Keywords | cdc_type_hint |
|---|---|
| `full_snapshot`, `snapshot`, `full snapshot` | `"snapshot"` |
| `delta`, `delta_only`, `delta feed` | `"delta"` |

**Matching rules:**
1. Check for key-value pattern `cdc_type:<value>` FIRST (colon-separated, no spaces around colon). If found → resolve immediately.
2. If no key-value match → scan for standalone keywords (case-insensitive, word-boundary aware).
3. Keyword `delta` alone MUST NOT match if it appears as part of `daily_increment_size` or `delta size` context (volumetric reference, not CDC type). Only match when `delta` appears as a CDC/feed descriptor (e.g., "delta feed", "delta CDC", standalone "delta" not adjacent to "size"/"increment"/"rows").

**Rules:**
- If match found → store `cdc_type_hint` as table-level field in `session/mapping_parsed.json`
- If no keywords match → set `cdc_type_hint = null` (downstream agents resolve via domain knowledge or default)
- This hint is consumed by `intent-identifier-agent` for `snapshot_mode` resolution (Priority 0.5 — mapping takes precedence over domain knowledge)

### Phase 2e — CDC Exclusion Columns Hint Extraction from Additional Context

> **ADDITIVE**: This step supplements existing parsing. It does NOT change Phase 2d logic.

After capturing `additional_context`, scan its value for CDC exclusion key-value pattern (case-insensitive):

**Key-value format (only format — no keyword fallback):**
| Pattern | cdc_exclude_cols_hint |
|---|---|
| `cdc_exclude:col1,col2,col3` | `["col1", "col2", "col3"]` |

**Matching rules:**
1. Look for pattern `cdc_exclude:<value>` (colon-separated, no spaces around colon). Case-insensitive key matching.
2. Capture the `<value>` portion (everything after `cdc_exclude:` until the next whitespace or semicolon or end-of-string).
3. Split the captured value on `,` (comma-separated list). Trim whitespace from each element. Filter out empty elements.
4. Result is an array of column name strings (lowercase, trimmed).

**Rules:**
- If match found → store `cdc_exclude_cols_hint` as table-level field in `session/mapping_parsed.json`
- If pattern not found → set `cdc_exclude_cols_hint = null` (downstream agents resolve via domain knowledge)
- This hint is consumed by `transform-generator-agent` at Phase 2.5 Step B — when non-null, it takes full precedence over domain knowledge (DK is NOT consulted for CDC exclusions)

**Examples:**
- `"cdc_exclude:source_extract_timestamp,batch_id"` → `["source_extract_timestamp", "batch_id"]`
- `"Day0 cdc_exclude:dw_lod_tmp,dw_upd_lod_tmp"` → `["dw_lod_tmp", "dw_upd_lod_tmp"]` (coexists with load_type keywords)
- `"incremental"` → `null` (no cdc_exclude pattern found)

### Phase 2f — Partition Key Hint Extraction from Additional Context

> **ADDITIVE**: This step supplements existing parsing. It does NOT change Phase 2e logic.

After capturing `additional_context`, scan its value for partition key key-value pattern (case-insensitive):

**Key-value format (only format — no keyword fallback):**
| Pattern | partition_key_hint |
|---|---|
| `partition_key:col1,col2` | `["col1", "col2"]` |
| `partition_key:active` | `["active"]` |

**Matching rules:**
1. Look for pattern `partition_key:<value>` (colon-separated, no spaces around colon). Case-insensitive key matching.
2. Capture the `<value>` portion (everything after `partition_key:` until the next whitespace or semicolon or end-of-string).
3. Split the captured value on `,` (comma-separated list). Trim whitespace from each element. Filter out empty elements.
4. Result is an array of column name strings (lowercase, trimmed).

**Rules:**
- If match found → store `partition_key_hint` as table-level field in `session/mapping_parsed.json`
- If pattern not found → set `partition_key_hint = null` (downstream agents resolve via other priority sources)
- This hint is consumed by `intent-identifier-agent` at Priority 1.5 for `partition_key_columns` resolution

**Examples:**
- `"partition_key:active"` → `["active"]`
- `"cdc_type:snapshot partition_key:dw_bus_dt,environment"` → `["dw_bus_dt", "environment"]` (coexists with other key-value hints)
- `"BAU daily"` → `null` (no partition_key pattern found)

### Phase 2g — CDC Deduplication Hints Extraction from Additional Context

> **ADDITIVE**: This step supplements existing parsing. It does NOT change Phase 2f logic.

> **IMPORTANT — Single-row presence**: These hints appear in the `Additional Context` column of only ONE row for the target table (any row — typically the first). They are NOT replicated against every target column row. Since Phase 2 already captures `additional_context` as the first non-empty value across all rows (table-level, not per-row), this step operates on that single captured value.

After capturing `additional_context`, scan its value for CDC deduplication key-value patterns (case-insensitive key matching):

**Key-value format (only format — no keyword fallback):**
| Pattern | Output Field | Type |
|---|---|---|
| `validate_unique_keys:true\|false` | `validate_unique_keys_hint` | boolean \| null |
| `duplicates_ts_col:<column_name>` | `duplicates_ts_col_hint` | string \| null |
| `dedup_order:asc\|desc` | `dedup_order_hint` | string \| null |

**Matching rules:**

1. **`validate_unique_keys`**: Look for pattern `validate_unique_keys:<value>` (colon-separated, no spaces around colon).
   - Capture value after colon until next whitespace/semicolon/end-of-string.
   - Validate: value must be `true` or `false` (case-insensitive). Convert to boolean (`value.strip().lower() == "true"` → `true`, else `false`).
   - If valid → store as `validate_unique_keys_hint` (boolean) in `mapping_parsed.json` table-level fields.
   - If invalid value → log WARNING: "Invalid validate_unique_keys value: '{value}'. Expected: true or false."; set `validate_unique_keys_hint = null`.
   - If pattern not found → set `validate_unique_keys_hint = null`.

2. **`duplicates_ts_col`**: Look for pattern `duplicates_ts_col:<value>` (colon-separated, no spaces around colon).
   - Capture value after colon until next whitespace/semicolon/end-of-string.
   - Validate: captured column name SHOULD exist in source columns across all `source_references` for this target table. If not found → log WARNING: "duplicates_ts_col '{col}' not found in source columns — hint stored but may fail at config generation". Store the value regardless (validation is advisory).
   - Store as `duplicates_ts_col_hint` (string) in `mapping_parsed.json` table-level fields.
   - If pattern not found → set `duplicates_ts_col_hint = null`.

3. **`dedup_order`**: Look for pattern `dedup_order:<value>` (colon-separated, no spaces around colon).
   - Capture value after colon until next whitespace/semicolon/end-of-string.
   - Validate: value must be `asc` or `desc` (case-insensitive). Normalize to lowercase.
   - If valid → store as `dedup_order_hint` (string) in `mapping_parsed.json` table-level fields.
   - If invalid value → log WARNING: "Invalid dedup_order value: '{value}'. Expected: asc or desc."; set `dedup_order_hint = null`.
   - If pattern not found → set `dedup_order_hint = null`.

**Coexistence rule**: Multiple CDC dedup hints can coexist with each other and all other Phase 2b–2f hints in the same Additional Context cell:
```
"BAU cdc_type:delta validate_unique_keys:false duplicates_ts_col:row_update_timestamp dedup_order:asc"
```

**Rules:**
- All three hints are consumed by `gen-config` at STEP 3 (CDC Configuration) — when non-null, they take Priority 1 precedence over domain knowledge
- These are CDC execution parameters, NOT semantic intent — they do NOT flow into `intent_identification.json`
- **Applicability**: These parameters are ONLY applicable to **Databricks platform**, **NonTransactional_SCD2** tables, during **BAU/Day1 processing** (where `run_cdc()` from databricks_foundation is invoked). They are NOT applicable to: Glue platform (no `run_cdc`), Day0 (full overwrite), NonTransactional_SCD1 (UPSERT merge), or Transactional (append-only). gen-config MUST NOT emit these fields for Glue configs, SCD1, or Transactional table types.

**Examples:**
- `"validate_unique_keys:false duplicates_ts_col:dw_upd_lod_tmp dedup_order:asc"` → `validate_unique_keys_hint = false`, `duplicates_ts_col_hint = "dw_upd_lod_tmp"`, `dedup_order_hint = "asc"`
- `"BAU validate_unique_keys:true"` → `validate_unique_keys_hint = true`, `duplicates_ts_col_hint = null`, `dedup_order_hint = null`
- `"incremental"` → all three hints = `null` (no patterns found)
- `"duplicates_ts_col:last_modified_ts dedup_order:desc"` → `validate_unique_keys_hint = null`, `duplicates_ts_col_hint = "last_modified_ts"`, `dedup_order_hint = "desc"`

### Phase 2h — Process Frequency & Date Control Hints Extraction from Additional Context

> **ADDITIVE**: This step supplements existing parsing. It does NOT change Phase 2g logic.

> **IMPORTANT — Single-row presence**: These hints appear in the `Additional Context` column of only ONE row for the target table (same as all Phase 2 hints — table-level, not per-row).

After capturing `additional_context`, scan its value for process frequency and date control key-value patterns (case-insensitive key matching):

**Key-value format (only format — no keyword fallback):**
| Pattern | Output Field | Type | Platform |
|---|---|---|---|
| `process_frequency:<value>` | `process_frequency_hint` | string \| null | Cross-platform (Databricks + Glue) |
| `workday_number_monthly:<N>` | `workday_number_monthly_hint` | string \| null | Glue-only |
| `workday_number_weekly:<N>` | `workday_number_weekly_hint` | string \| null | Glue-only |
| `run_on_weekends:<Y\|N>` | `run_on_weekends_hint` | string \| null | Glue-only |
| `run_on_bank_holidays:<Y\|N>` | `run_on_bank_holidays_hint` | string \| null | Glue-only |

**Matching rules:**

1. **`process_frequency`**: Look for pattern `process_frequency:<value>` (colon-separated, no spaces around colon).
   - Capture value after colon until next whitespace/semicolon/end-of-string.
   - Normalize to UPPERCASE.
   - Validate: value must be one of `DAILY`, `WORKING_DAYS`, `ONCE_A_MONTH`, `WEEKLY_ONCE`, `ALTERNATE_DAYS`, `TUE_TO_SAT` (case-insensitive input accepted).
   - If valid → store as `process_frequency_hint` (string) in `mapping_parsed.json` table-level fields.
   - If invalid value → log WARNING: "Invalid process_frequency value: '{value}'. Expected: DAILY, WORKING_DAYS, ONCE_A_MONTH, WEEKLY_ONCE, ALTERNATE_DAYS, TUE_TO_SAT."; set `process_frequency_hint = null`.
   - If pattern not found → set `process_frequency_hint = null`.

2. **`workday_number_monthly`** (Glue-only): Look for pattern `workday_number_monthly:<value>`.
   - Capture value after colon until next whitespace/semicolon/end-of-string.
   - Validate: value must be a positive integer (≥ 1). Store as string.
   - If valid → store as `workday_number_monthly_hint` (string) in `mapping_parsed.json` table-level fields.
   - If invalid → log WARNING: "Invalid workday_number_monthly value: '{value}'. Expected: positive integer."; set `workday_number_monthly_hint = null`.
   - If pattern not found → set `workday_number_monthly_hint = null`.

3. **`workday_number_weekly`** (Glue-only): Look for pattern `workday_number_weekly:<value>`.
   - Capture value after colon until next whitespace/semicolon/end-of-string.
   - Validate: value must be an integer 0-6 (0=Sunday, 1=Monday, ..., 6=Saturday). Store as string.
   - If valid → store as `workday_number_weekly_hint` (string) in `mapping_parsed.json` table-level fields.
   - If invalid → log WARNING: "Invalid workday_number_weekly value: '{value}'. Expected: integer 0-6."; set `workday_number_weekly_hint = null`.
   - If pattern not found → set `workday_number_weekly_hint = null`.

4. **`run_on_weekends`** (Glue-only): Look for pattern `run_on_weekends:<value>`.
   - Capture value after colon until next whitespace/semicolon/end-of-string.
   - Normalize to UPPERCASE.
   - Validate: value must be `Y` or `N`.
   - If valid → store as `run_on_weekends_hint` (string) in `mapping_parsed.json` table-level fields.
   - If invalid → log WARNING: "Invalid run_on_weekends value: '{value}'. Expected: Y or N."; set `run_on_weekends_hint = null`.
   - If pattern not found → set `run_on_weekends_hint = null`.

5. **`run_on_bank_holidays`** (Glue-only): Look for pattern `run_on_bank_holidays:<value>`.
   - Capture value after colon until next whitespace/semicolon/end-of-string.
   - Normalize to UPPERCASE.
   - Validate: value must be `Y` or `N`.
   - If valid → store as `run_on_bank_holidays_hint` (string) in `mapping_parsed.json` table-level fields.
   - If invalid → log WARNING: "Invalid run_on_bank_holidays value: '{value}'. Expected: Y or N."; set `run_on_bank_holidays_hint = null`.
   - If pattern not found → set `run_on_bank_holidays_hint = null`.

**Coexistence rule**: All date control hints can coexist with each other and all Phase 2b–2g hints in the same Additional Context cell:
```
"BAU process_frequency:ONCE_A_MONTH workday_number_monthly:5 run_on_weekends:N run_on_bank_holidays:N"
```

**Rules:**
- `process_frequency` is cross-platform — consumed by gen-config STEP 3.6 for both Databricks (`pipeline.process_frequency`) and Glue (`date_control.frequency`)
- `workday_number_monthly`, `workday_number_weekly`, `run_on_weekends`, `run_on_bank_holidays` are **Glue-only** — consumed by gen-config STEP 3.6 for Glue `date_control` section only. Not applicable to Databricks.
- All hints default to platform-appropriate values when not specified: frequency="DAILY", workday fields="", weekend/holiday="N"

**Examples:**
- `"BAU process_frequency:WORKING_DAYS run_on_bank_holidays:N"` → `process_frequency_hint = "WORKING_DAYS"`, `run_on_bank_holidays_hint = "N"`, others null
- `"process_frequency:ONCE_A_MONTH workday_number_monthly:5 run_on_weekends:N"` → `process_frequency_hint = "ONCE_A_MONTH"`, `workday_number_monthly_hint = "5"`, `run_on_weekends_hint = "N"`, others null
- `"incremental"` → all five hints = `null` (no patterns found, defaults apply)
- `"process_frequency:WEEKLY_ONCE workday_number_weekly:1"` → `process_frequency_hint = "WEEKLY_ONCE"`, `workday_number_weekly_hint = "1"`, others null

### Phase 2j — Source System Hint Extraction from Additional Context

> **ADDITIVE**: This step supplements existing parsing. It does NOT change any Phase 2x logic.

After capturing `additional_context`, scan its value for source system key-value pattern (case-insensitive):

**Key-value format (only format — no keyword fallback):**
| Pattern | source_system_hint |
|---|---|
| `source_system:ilp` | `"ilp"` |
| `source_system:reference_data` | `"reference_data"` |

**Matching rules:**
1. Look for pattern `source_system:<value>` (colon-separated, no spaces around colon). Case-insensitive key matching.
2. Capture the `<value>` portion (everything after `source_system:` until the next pipe `|` or whitespace or end-of-string).
3. Trim whitespace, lowercase the result.

**Rules:**
- If match found → store `source_system_hint` as table-level field in `session/mapping_parsed.json`
- If pattern not found → set `source_system_hint = null` (normal single-flow generation applies)
- This hint is consumed by `/gen-config` STEP 0.5 for artifact mode resolution
- Multiple source databases in the mapping (e.g., joins across `e_cms_db` and `ref_common_db`) do NOT indicate multiple source systems — only this explicit `source_system` key triggers multi-source-system artifact generation

**Examples:**
- `"load_type:BAU|source_system:ilp|partition_key:active"` → `"ilp"`
- `"load_type:BAU|partition_key:active"` → `null` (no source_system, normal single-flow)
- `"source_system:reference_data"` → `"reference_data"`

### Phase 3 — Row-Level Extraction & Source Reference Assembly

For each data row (skip header; skip entirely blank rows):
- Extract `target_column_name`, `target_column_description`, `target_column_datatype`
- `target_column_nullable`: convert `Target Column Null Flag` → boolean:
  - Y / Yes / TRUE / 1 → `true` (nullable)
  - N / No / FALSE / 0 → `false` (NOT NULL)
  - Empty/null → `true` (default nullable)
- `transformation_logic`: raw value of `Business Logic/Transformation Logic`

#### Optional Column Extraction (Phase 3b — per-row, conditional)

> **CONDITIONAL**: Only extracts fields for optional columns detected in Phase 1b.

**If `Transformation Type` present:**
- Extract raw value, validate against enum: `Direct`, `Derived`, `Lookup`, `Direct - Type Cast`
- Case-insensitive matching (e.g., `direct` → `"Direct"`, `LOOKUP` → `"Lookup"`)
- Invalid/empty → `null` (no error; log DEBUG warning)
- Store as `transformation_type` per column

**If `Default Value` present:**
- Extract raw value from cell (string or numeric)
- Preserve original type: if cell is numeric → store as number; if text → store as string
- Empty cell → `null`
- Store as `default_value` per column

**If `Key Column` present:**
- Convert to boolean using same logic as `Target Column Null Flag`:
  - Y / Yes / TRUE / 1 → `true` (this column IS a key column)
  - N / No / FALSE / 0 → `false` (not a key column)
  - Empty/null → `null` (unknown)
- Store as `key_column` per column

#### Source Reference Assembly (replaces parallel arrays)

**Step 1 — Split raw cells:**
- `raw_dbs[]`: split `Source database/Source DB` on `,`, `;`, or newline → trim → filter empty
- `raw_tables[]`: split `Source Table Name` on `,`, `;`, or newline → trim → filter empty
- `raw_columns[]`: split `Source Column Name` on `,`, `;`, or newline → trim → filter empty

**Step 2 — Determine qualification tier and assemble `source_references[]`:**

```
IF len(unique(raw_dbs)) == 1:
  db = raw_dbs[0]
  IF len(raw_tables) == 1:
    # TIER 1: Single DB, Single Table → broadcast both to all columns
    table = raw_tables[0]
    FOR each col IN raw_columns:
      emit {"database": db, "table": table, "column": col}
  ELSE:
    # TIER 2: Single DB, Multiple Tables → columns MUST be qualified as table.column
    FOR each col IN raw_columns:
      parts = col.split(".", maxsplit=1)
      IF len(parts) != 2 → HALT:
        "⛔ MULTI-TABLE AMBIGUITY (Row {row_num}): Source Column '{col}' is not qualified.
         When multiple source tables are present ({raw_tables}), columns MUST use format:
           table_name.column_name
         Please correct the mapping Excel and re-run /parse-mapping."
      emit {"database": db, "table": parts[0], "column": parts[1]}
ELSE:
  # TIER 3: Multiple DBs → tables MUST be db.table, columns MUST be db.table.column
  # Exception: file source entries use storage paths (tables) and 2-part FQN (columns).
  IF len(raw_tables) != len(raw_dbs) → HALT:
    "⛔ POSITIONAL MISMATCH (Row {row_num}): {len(raw_tables)} tables but {len(raw_dbs)} databases
     — each table must have a corresponding database in multi-DB scenarios.
     Please correct the mapping Excel and re-run /parse-mapping."
  FOR each idx, tbl IN enumerate(raw_tables):
    ref_db = raw_dbs[idx]
    IF ref_db == '(file:parquet)':
      # File source — table is a storage path, not db.table; derive logical_name from basename
      logical_name = basename(tbl.rstrip('/'))
      CONTINUE  # validated by file source handling below
    parts = tbl.split(".", maxsplit=1)
    IF len(parts) != 2 → HALT:
      "⛔ MULTI-DB AMBIGUITY (Row {row_num}): Source Table '{tbl}' is not fully qualified.
       When multiple source databases are present ({raw_dbs}), tables MUST use format:
         database_name.table_name
       Please correct the mapping Excel and re-run /parse-mapping."
  FOR each idx, col IN enumerate(raw_columns):
    ref_db = raw_dbs[idx]
    IF ref_db == '(file:parquet)':
      # File source — 2-part FQN: {logical_name}.{column}
      parts = col.split(".", maxsplit=1)
      IF len(parts) != 2 → HALT:
        "⛔ FILE SOURCE AMBIGUITY (Row {row_num}): Source Column '{col}' is not qualified.
         File source columns MUST use format: logical_name.column_name
         Please correct the mapping Excel and re-run /parse-mapping."
      emit {"database": "(file:parquet)", "table": parts[0], "column": parts[1], "io_type": "file"}
      CONTINUE
    parts = col.split(".", maxsplit=2)
    IF len(parts) != 3 → HALT:
      "⛔ MULTI-DB AMBIGUITY (Row {row_num}): Source Column '{col}' is not fully qualified.
       When multiple source databases are present ({raw_dbs}), columns MUST use format:
         database_name.table_name.column_name
       Please correct the mapping Excel and re-run /parse-mapping."
    emit {"database": parts[0], "table": parts[1], "column": parts[2], "io_type": "table"}
```

**File source handling (when `source_database` = `(file:parquet)`):**

When any `raw_dbs[]` entry equals `(file:parquet)` (case-insensitive match):
- `source_table` (col H) contains the **absolute storage path** (e.g., `s3://raw-bucket/data/customer_events/` for Glue, `/Volumes/catalog/schema/volume/customer_events/` for Databricks)
- Derive `logical_name` from the path **basename** — the last non-empty segment after stripping any trailing `/` (e.g., `s3://raw-bucket/data/customer_events/` → `customer_events`)
- `source_column` (col I) uses **2-part FQN**: `{logical_name}.{column}` (NOT 3-part `{db}.{table}.{column}`) — the `logical_name` here is the derived basename, not the full path
- The qualification tier logic above applies with `(file:parquet)` counted as a single DB value:
  - Single file source + single logical name → broadcast logical name to all columns (TIER 1 behaviour)
  - Single file source + multiple logical names → columns must be qualified as `logical_name.column` (TIER 2 behaviour)
  - Mixed file + table sources → full qualification required; file source columns use 2-part, table source columns use 3-part
- Populate `source_io` in the parsed output: collect all unique file sources from rows where `source_database = (file:parquet)` and store as `source_io: [{logical_name: "<basename>", storage_path: "<full path from col H>", format: "parquet"}]`
- Set `file_source_detected = true` in parsed output

**Step 3 — Cross-validation:**
- Every `database` value in emitted references must appear in `raw_dbs` (or be the single broadcast DB)
- Every `table` value in emitted references must appear in `raw_tables` (stripped of db prefix if qualified)
- If a reference contains a database not in `raw_dbs` → HALT with error: "Source Column '{col}' references database '{db}' not listed in Source DB cell"
- If a reference contains a table not in `raw_tables` (accounting for qualification) → HALT with error: "Source Column '{col}' references table '{table}' not listed in Source Table cell"

**Output:** Each column record in `mapping_parsed.json` contains `source_references[]` array of `{database, table, column, io_type}` objects. The `io_type` field is `"file"` when `source_database` is `(file:parquet)`, `"table"` otherwise.

### Phase 3c — Structured Transformation Logic Detection

> **Canonical format reference:** See `${CLAUDE_PLUGIN_ROOT}/docs/structured-transformation-logic.md` for the full multi-table structured format specification.

> **ADDITIVE**: Runs after Phase 3 row extraction. Does NOT replace existing `transformation_logic` capture — both raw text and parsed structure are stored.

For each row's `transformation_logic` value, check for structured format:

**Detection trigger (case-insensitive):**
Cell value contains `Driver Table` followed by `:` (with optional whitespace).

**If trigger detected → parse structured format:**

Apply the following regex patterns (case-insensitive, multiline) to extract structured fields.

**Verbose Format Patterns (preferred — from STTM v1.1+):**
```regex
Driver Table\s*:\s*(.+?)(?:\n|$)
Driver Conditions\s*:\s*(\[.*?\])
Join\s+(\d+)\s+Table\s*:\s*(.+?)(?:\n|$)
Join\s+(\d+)\s+Type\s*:\s*(.+?)(?:\n|$)
Join\s+(\d+)\s+On\s*:\s*(.+?)(?:\n|$)
Join\s+(\d+)\s+Filters\s*:\s*(\[.*?\])
Value\s*:\s*(.+?)$
Dedup Strategy\s*:\s*(.+?)(?:\n|$)
Dedup Partition\s*:\s*(.+?)(?:\n|$)
Dedup Order\s*:\s*(.+?)(?:\n|$)
Dedup Keep\s*:\s*(.+?)(?:\n|$)
Window Function\s*:\s*(.+?)(?:\n|$)
Window Partition\s*:\s*(.+?)(?:\n|$)
Window Order\s*:\s*(.+?)(?:\n|$)
Window Args\s*:\s*(.+?)(?:\n|$)
Aggregate Function\s*:\s*(.+?)(?:\n|$)
Aggregate Group By\s*:\s*(.+?)(?:\n|$)
Having\s*:\s*(.+?)(?:\n|$)
Qualify\s*:\s*(.+?)(?:\n|$)
Crypto Operation\s*:\s*(.+?)(?:\n|$)
Crypto DE\s*:\s*(.+?)(?:\n|$)
Crypto Source DE\s*:\s*(.+?)(?:\n|$)
Crypto Target DE\s*:\s*(.+?)(?:\n|$)
Crypto Source Column\s*:\s*(.+?)(?:\n|$)
Union Branch\s+(\d+)\s+Table\s*:\s*(.+?)(?:\n|$)
Union Branch\s+(\d+)\s+Columns\s*:\s*(.+?)(?:\n|$)
Union Branch\s+(\d+)\s+Filters\s*:\s*(\[.*?\])
Union Type\s*:\s*(.+?)(?:\n|$)
MERGE Source Table\s*:\s*(.+?)(?:\n|$)
MERGE Target Table\s*:\s*(.+?)(?:\n|$)
MERGE Match Key\s*:\s*(.+?)(?:\n|$)
MERGE Matched Action\s*:\s*(.+?)(?:\n|$)
MERGE Not Matched Action\s*:\s*(.+?)(?:\n|$)
Staging Hint\s*:\s*(.+?)(?:\n|$)
Audit Column\s*:\s*(.+?)(?:\n|$)
```

**Detection logic:** If Business Logic contains `Join \d+ On:` or `Join \d+ Filters:`, treat as verbose format (v1.1+). Otherwise fall back to compact format patterns.

**When compact format detected, log WARNING:** `"Compact Business Logic format detected — consider regenerating STTM with verbose format for improved parsing accuracy."`

**Compact Format Patterns (legacy fallback):**
```regex
Driver Table\s*:\s*(.+?)(?:\n|$)
Driver\s+Conditions?\s*:\s*\[(.+?)\]
Join\s+(\d+)\s+Table\s*:\s*(.+?)(?:\n|$)
(?:Table(\d*)|Join\s*(\d*))\s*Conditions?\s*:\s*\[(.+?)\]
Join\s+(\d+)\s+Type\s*:\s*(.+?)(?:\n|$)
Join\s+(\d+)\s+Conditions?\s*:\s*(.+?)(?:\n|$)
Value\s*:\s*(.+?)$
```

**Assembly into `structured_transformation` object:**

```json
{
  "driver_table": "<captured from Driver Table line>",
  "driver_conditions": ["<condition 1>", "<condition 2>"],
  "joins": [
    {
      "join_number": 1,
      "table": "<captured from Join N Table line>",
      "table_conditions": ["<condition 1>", "<condition 2>"],
      "join_type": "LEFT|INNER|RIGHT|FULL|CROSS",
      "join_conditions": "<captured from Join N Conditions line>"
    }
  ],
  "value_expression": "<captured from Value line>"
}
```

**Driver Conditions parsing:**
- Same syntax as Table Conditions: content between `[` and `]`, split on numbered prefixes (`1.`, `2.`, etc.) or newlines
- If `Driver Conditions` line not present or empty brackets → `driver_conditions = []`
- Supports same filter patterns as TableN Conditions: `Filter <expression>`, `pick latest record based on <column>`, date placeholders

**Table Conditions parsing:**
- Content between `[` and `]` — split on numbered prefixes (`1.`, `2.`, etc.) or newlines
- If no brackets or empty brackets → `table_conditions = []`

**Rules:**
- Store both `transformation_logic` (raw text) AND `structured_transformation` (parsed object)
- If structured format detected but parsing fails (incomplete fields) → log WARNING, set `structured_transformation = null`, keep raw `transformation_logic` as fallback
- If `Driver Table` not found → `structured_transformation = null` (free-text mode, current behaviour)
- Multiple rows for same target table may mix structured and free-text — this is valid (per-column decision)

**Validation:**
- `driver_table` must match a table in `source_references` for this row or any row in the same target table
- `joins[].table` should match known source tables — log WARNING if not found (non-blocking)
- `joins[].join_type` must be one of: LEFT, INNER, RIGHT, FULL, CROSS (case-insensitive → normalized to uppercase)

**Multi-Source Join Logic Advisory (Phase 3c post-check):**

After structured format detection completes for each column, evaluate `join_logic_missing`:

```
FOR EACH column in parsed mapping:
  distinct_tables = unique set of table names from column.source_references[]
  IF len(distinct_tables) > 1:
    IF column.structured_transformation is null:
      SET column.join_logic_missing = true
      # Scan transformation_logic for NL join keywords (informational)
      nl_join_keywords_found = scan for: JOIN, join with, lookup from, get from, merge with, match on
      LOG ADVISORY: "Column '{target_column_name}' references {N} source tables
        ({table_list}) — no structured format detected. Transform generator will
        use NL interpretation (Rule 11). NL join keywords found: {nl_join_keywords_found}.
        For deterministic output, structured Driver Table format is recommended."
      APPEND to session_state.parse_warnings[] (type: "join_logic_missing", severity: "advisory")
    ELSE:
      SET column.join_logic_missing = false
  ELSE:
    SET column.join_logic_missing = false
```

This flag is consumed by:
- `intent-identifier-agent` — emits advisory recommending structured format (non-blocking)
- `transform-generator-agent` — uses NL interpretation mode (Rule 11) when `join_logic_missing=true`; generation proceeds with advisory comments
- `de-validate` — flagged as quality advisory in validation report

### Phase 3c.1: STTM-Provided Structured Data (Preferred Path)

When parsing STTM-generated JSON (identified by `_meta.generator == "sttm-plugin"`):

1. **structured_transformation**: If the mapping row contains a `structured_transformation` object from STTM, use it DIRECTLY — do NOT attempt regex extraction from Business Logic text. The STTM-provided object is authoritative.

2. **extracted_constraints**: If the STTM JSON contains an `extracted_constraints` section, use it to populate:
   - `extracted_join_predicates` → from `extracted_constraints.join_predicates`
   - `extracted_literals` → from `extracted_constraints.locked_literals`
   - `window_specifications` → from `extracted_constraints.window_specifications`
   - `aggregate_specifications` → from `extracted_constraints.aggregate_specifications`
   
   All STTM-provided constraints have `confidence: 1.0` and `source: "sql_ast"` — they are derived from the SQL parse tree and are more reliable than regex extraction.

3. **source_column_allowlist**: If STTM JSON contains `source_column_allowlist`, write it directly to `session/source_column_allowlist.json` without re-extraction.

4. **Fallback**: For user-provided Excel (non-STTM), continue using regex extraction as the primary path.

5. **Backward compatibility**: Both `Source Table:` (legacy) and `Driver Table:` (current) labels may appear in Transformation Lineage text blocks within the Business Logic cell. The machine-readable path uses the `structured_transformation` JSON — text label differences do not affect parsing.

### Phase 3d — Join Predicate & Literal Value Extraction (Free-Text Path)

> **CONDITIONAL**: Only for columns where `structured_transformation == null` AND `transformation_logic` is non-null/non-empty.
> Implements STEP 2.8 from de-parse-mapping command spec.

**Purpose**: Extract join predicates and literal/constant values verbatim from free-text `transformation_logic` using regex patterns. These extracted values become LOCKED constraints that prevent the transform-generator-agent from inferring symmetric join keys or substituting "more logical" literal values.

**Algorithm:**

```
FOR EACH column WHERE structured_transformation is null AND transformation_logic is non-null:

  # === Part A: Join Predicate Extraction ===
  join_predicates = []
  
  # Regex: table.column OPERATOR table.column
  pattern = r'(\w+)\.(\w+)\s*(=|!=|<|>|<=|>=)\s*(\w+)\.(\w+)'
  
  FOR EACH match in regex_findall(pattern, column.transformation_logic):
    left_table, left_col, operator, right_table, right_col = match groups
    source_text = matched substring
    
    # Cross-validate against source_references
    known_tables = {ref.table for ref in column.source_references}
    left_recognized = left_table in known_tables
    right_recognized = right_table in known_tables
    
    IF left_recognized AND right_recognized:
      confidence = "high"
    ELIF left_recognized OR right_recognized:
      confidence = "medium"
    ELSE:
      confidence = "low"
    
    join_predicates.append({
      left_table, left_col, operator, right_table, right_col,
      source_text, confidence
    })
  
  column.extracted_join_predicates = join_predicates if len(join_predicates) > 0 else null

  # === Part B: Literal Value Extraction ===
  literals = []
  
  # Skip template parameters (not fixed values)
  SKIP_PATTERNS = [r'\{control_[Dd]ate\}', r'\{current_business_date\}', r'\{batch_date\}']
  
  # Pattern 1: Quoted string equality (single quotes)
  FOR EACH match in r"(\w+)\s*=\s*'([^']+)'":
    IF match.group(2) not a template parameter:
      context = determine_context(match, transformation_logic)
      literals.append({column: match.group(1), operator: "=", value: match.group(2),
                       source_text: matched_with_context, context, confidence: "high"})
  
  # Pattern 2: Quoted string equality (double quotes)
  FOR EACH match in r'(\w+)\s*=\s*"([^"]+)"':
    IF match.group(2) not a template parameter:
      context = determine_context(match, transformation_logic)
      literals.append({column: match.group(1), operator: "=", value: match.group(2),
                       source_text: matched_with_context, context, confidence: "high"})
  
  # Pattern 3: NOT IN list
  FOR EACH match in r"(\w+)\s+NOT\s+IN\s*\(([^)]+)\)":
    values = split_and_trim_quotes(match.group(2))
    literals.append({column: match.group(1), operator: "NOT IN", value: values,
                     source_text: matched_with_context, context: "filter_predicate", confidence: "high"})
  
  # Pattern 4: IN list
  FOR EACH match in r"(\w+)\s+IN\s*\(([^)]+)\)":
    values = split_and_trim_quotes(match.group(2))
    literals.append({column: match.group(1), operator: "IN", value: values,
                     source_text: matched_with_context, context: "filter_predicate", confidence: "high"})
  
  # Pattern 5: Hardcode instruction
  FOR EACH match in r"[Hh]ardcode\s+(?:to\s+)?['\"]?([^'\")\s,]+)['\"]?":
    literals.append({column: null, operator: "hardcode", value: match.group(1),
                     source_text: matched_with_context, context: "literal_assignment", confidence: "high"})
  
  # Pattern 6: WHEN condition values
  FOR EACH match in r"[Ww]hen\s+(\w+)\s*=\s*['\"]?([^'\")\s,]+)['\"]?":
    literals.append({column: match.group(1), operator: "=", value: match.group(2),
                     source_text: matched_with_context, context: "case_when_condition", confidence: "high"})
  
  # Pattern 7: Numeric equality (only when NOT already captured by join predicate pattern)
  FOR EACH match in r"(\w+)\s*=\s*(\d+(?:\.\d+)?)":
    IF not already captured as join predicate AND not a column reference:
      literals.append({column: match.group(1), operator: "=", value: numeric(match.group(2)),
                       source_text: matched_with_context, context: determine_context(match), confidence: "high"})
  
  # Deduplicate: if same column+operator+value extracted by multiple patterns, keep first
  literals = deduplicate_by(literals, key=(column, operator, value))
  
  column.extracted_literals = literals if len(literals) > 0 else null

  # === Part C: Logging ===
  n_joins = len(join_predicates)
  n_literals = len(literals)
  IF n_joins > 0 OR n_literals > 0:
    LOG INFO: "[STEP 2.8] Column '{target_column_name}': extracted {n_joins} join predicates, {n_literals} literals from free-text"
```

**Context determination helper:**
```
FUNCTION determine_context(match, full_text):
  surrounding = text around match (±30 chars)
  IF contains "Filter" or "Where" or "Only" → "filter_predicate"
  ELIF contains "when" or "WHEN" (case-insensitive) → "case_when_condition"
  ELIF contains "then" or "THEN" → "case_when_result"
  ELIF contains "Hardcode" or "Default" or "Set to" → "literal_assignment"
  ELIF within a join ON clause (matched by Part A) → "join_condition_literal"
  ELSE → "filter_predicate" (conservative default)
```

**Key properties:**
- Regex-first approach: deterministic pattern matching, no creative interpretation
- Confidence gating: only high/medium extractions become LOCKED constraints downstream
- Additive: never modifies `transformation_logic`, `structured_transformation`, or `join_logic_missing`
- Idempotent: re-running produces same results (regex is deterministic)
- Skip `structured_transformation != null` columns (already have deterministic path)

### Phase 4 — Crypto Indicator Detection

> **Crypto protocol**: See `${CLAUDE_PLUGIN_ROOT}/agents/refs/crypto-refusal-protocol.md`

For each row, scan `Business Logic/Transformation Logic` column ONLY:

**Step 1 — UDF regex extraction** (primary signal):
```
cloud_api_udf_([A-Z0-9_]+)_(un)?protect\(
```
- Match → `is_crypto = true`
- Capture group 1 = `de_name`
- `unprotect` → `operation = "detokenize"`
- `protect` (without `un`) → `operation = "tokenize"`

**Step 2 — Protegrity Data Element extraction** (secondary):
If UDF pattern NOT found, scan for:
- Text contains "protegrity" (case-insensitive) AND
- Text contains "data element" (case-insensitive) AND
- Text contains either "tokenize" or "detokenize" (case-insensitive)

Then extract de_name matching pattern:
```
(UK|US|APAC)_TOK_([A-Z0-9]+)_(L\d+R\d+)_(UNC|ALN|DEC|NUM|CC|EML)_DE
```

- Match → `is_crypto = true`, `de_name` = captured full pattern
- If text contains "detokenize" (case-insensitive) → `operation = "detokenize"`
- If text contains "tokenize" (case-insensitive) → `operation = "tokenize"`
- If both present → HALT and ask user: "Column '{column}' has both tokenize and detokenize keywords. Which crypto operation is intended for this column: tokenize (protect) or detokenize (unprotect)?"

**Step 3 — Keyword scan** (tertiary — only if Steps 1 & 2 not matched):
- Keywords: `tokenize`, `detokenize`, `unprotect`, `protect`
- Match → `is_crypto = true`, `operation` derived from keyword, `de_name = null`, `extraction_failed = true`

**NOT crypto triggers** (ignored even if present):
- External sensitivity tags or metadata
- PII column notes in domain knowledge MD
- Column name patterns alone (e.g. a column named `sort_code`)

### Phase 5 — Crypto Flag Assembly

Write per-column flags and aggregate:
```json
{
  "any_column_crypto_flagged": true,
  "columns": {
    "account_number": {
      "is_crypto": true,
      "operation": "detokenize",
      "de_name": "UK_TOK_FT_L0R0_UNC_DE",
      "extraction_source": "udf_pattern|protegrity_element|keyword",
      "extraction_failed": false,
      "extraction_ambiguous": false
    }
  }
}
```

**Field semantics:**
- `extraction_source`: which step matched (UDF pattern / Protegrity DE / Keyword-only)
- `extraction_failed: true`: keyword-only match with no de_name; will trigger REFUSAL at crypto assembly. Do NOT emit placeholder.
- `extraction_ambiguous: true`: both tokenize and detokenize keywords found; HALT triggered to ask user for clarification before proceeding

**Data Element Validation** (all sources):
Validate extracted `de_name` against pattern:
```
(UK|US|APAC)_TOK_([A-Z0-9]+)_(L\d+R\d+)_(UNC|ALN|DEC|NUM|CC|EML)_DE
```
- Region: UK, US, or APAC
- Type: TOK (Tokenization)
- Functional abbreviation: UNC (Unicode), ALN (Alphanumeric), DEC (Decimal), NUM (Numeric), CC (Credit Card), EML (Email)
- Behavior: format `L<digits>R<digits>` (e.g., L0R0, L6R0)
- Data Type Ref: matches functional abbreviation
- Suffix: _DE

If de_name fails validation: set `extraction_failed: true`; do not proceed with placeholder generation.

---

### Phase 6 — Source Volumetrics Extraction (optional sheet)

> **CONDITIONAL**: Only executes if the mapping Excel contains a sheet named `Source Volumetrics` (case-insensitive match: `source volumetrics`, `Source_Volumetrics`, `SourceVolumetrics` all valid).

**Step 1 — Detect sheet:**
- Scan workbook sheet names for case-insensitive match to "Source Volumetrics"
- If not found → set `session_state.source_volumetrics_path = null`; skip Phase 6 entirely (backward compatible)
- If found → proceed to Step 2

**Step 2 — Parse rows:**

Expected columns (case-insensitive header match):
| # | Header | Maps to |
|---|--------|---------|
| 1 | Source Database | `source_database` |
| 2 | Source Table | `source_table` |
| 3 | Estimated Rows | `estimated_rows` (integer) |
| 4 | Estimated Size (GB) | `estimated_size_gb` (number) |
| 5 | Daily Increment Rows | `daily_increment_rows` (integer) |
| 6 | Daily Increment Size (GB) | `daily_increment_size_gb` (number) |
| 7 | Primary Key | `primary_key` (string, comma-separated if composite) |
| 8 | Partition Key | `partition_key` (string, comma-separated if multiple) |
| 9 | Table Type | `table_type` (enum: NonTransactional_SCD2, NonTransactional_SCD1, Transactional) |
| 10 | Broadcast Hint | `broadcast_hint` (boolean: Y→true, N→false) |

- Skip row 2 (descriptions row) and any blank rows
- For each data row, emit one `sourceVolumetric` object per schema definition
- Numeric cells: coerce to integer/number; if non-numeric or empty → `null`
- Primary Key / Partition Key: trim whitespace; preserve commas for composite keys; empty → `null`
- Table Type: case-insensitive normalization (nontransactional/non-transactional/non_transactional/scd2/reference/snapshot→"NonTransactional_SCD2", scd1→"NonTransactional_SCD1", transactional→"Transactional"); unrecognized value → `null` with WARNING
- Broadcast Hint: Y/Yes/TRUE/1 → `true`; N/No/FALSE/0/empty → `false`

**Step 3 — Cross-validation (advisory, non-blocking):**
- Collect all unique `(source_database, source_table)` pairs from mapping Phase 3 `source_references`
- For each volumetric entry, check if `(source_database, source_table)` exists in that set
- If orphan found (volumetric entry not referenced in mapping) → log WARNING: "Source Volumetrics entry '{db}.{table}' not referenced in mapping columns — will be ignored by downstream agents"
- If a source table in mapping has NO volumetric entry → no warning (volumetrics are optional per table)

**Step 4 — Auto-broadcast inference:**
- For any entry where `estimated_size_gb` is not null AND < 0.01 (10MB) AND `broadcast_hint` is false/null → set `broadcast_hint = true`
- Log INFO: "Auto-broadcast applied to {db}.{table} (reason: estimated_size_gb < 10MB)"

**Step 5 — Write output:**
- Write parsed array to `session/source_volumetrics.json` (conforms to `source_volumetrics` in mapping_excel.schema.json)
- Set `session_state.source_volumetrics_path = "session/source_volumetrics.json"`
- Also include `source_volumetrics` array in `session/mapping_parsed.json` at the top-level (alongside `columns`, `target_database`, etc.)

---

## Output Schema

`session/mapping_parsed.json` — conforms to `${CLAUDE_PLUGIN_ROOT}/schemas/mapping_excel.schema.json`.

---

## Anti-Hallucination Rules

> **Core rules**: See `${CLAUDE_PLUGIN_ROOT}/agents/refs/anti-hallucination-core.md`

- Never infer transformation logic from column names
- Never derive source DB from target DB
- Never assume nullable if flag cell is empty — default to nullable (true)
- Multi-value splitting: when delimiter is ambiguous (both `,` and `;` present in same cell), HALT and ask user which delimiter to use
- NEVER infer database-to-table or table-to-column mapping by positional alignment when ambiguity exists. If multi-DB and values are not fully qualified → HALT. If multi-table and columns are not qualified → HALT. Do NOT guess.
- Newline characters in cells are valid delimiters alongside `,` and `;`


---

## Standalone Invocation

> **Pattern**: See `${CLAUDE_PLUGIN_ROOT}/agents/refs/standalone-invocation.md`

Minimum required context:
- Mapping Excel file path (.xlsx)
- platform ('glue' or 'databricks')

## Uncertainty Disclosure

> **Canonical rules**: See `${CLAUDE_PLUGIN_ROOT}/agents/refs/uncertainty-disclosure.md`

## Extension Points

- Custom Excel column schemas (beyond the standard 16 columns)
- Additional file format support beyond .xlsx
- Custom validation rules for domain-specific column patterns

## Your Inputs

- Excel file path (`.xlsx`) provided via session state `mapping_excel_path`
- Session state containing `expected_db_prefix` and `expected_source_layer`
- Platform identifier (`glue` or `databricks`) for tenancy lookup routing
- Workbook sheet names for conditional phase execution (e.g., Source Volumetrics)

## Your Outputs

- `session/mapping_parsed.json` — structured column definitions, table-level fields, and source references per target table
- `session/crypto_flags.json` — per-column crypto detection results with DE names and operations
- `session/source_volumetrics.json` — per-source-table volumetric data (conditional; only when Source Volumetrics sheet is present)
- Session state updates: `source_volumetrics_path`, parse warnings

## Flags

- Malformed or missing required column headers (any of the 12 required headers) — **HALT**
  > The 4 optional enrichment columns (Transformation Type, Default Value, Target Table Type, Key Column) are not HALT triggers.
- Crypto Data Element extraction failure (keyword-only match with no DE name) — **HALT**
- Multi-table/multi-DB ambiguity where source columns are not fully qualified — **HALT**
- Unknown `target_database` prefix not matching tenancy registry — **WARNING**
- Unknown `Target Table Type` value not in recognized enum — **WARNING**
