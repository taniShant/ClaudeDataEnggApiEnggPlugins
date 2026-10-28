---
description: Classify source table types (NonTransactional_SCD1/NonTransactional_SCD2/Transactional) — invoke after mapping is parsed
disable-model-invocation: false
---

# /classify-sources

Classify source tables as NonTransactional_SCD1, NonTransactional_SCD2, or Transactional using local data sources. Produces `session/source_table_metadata.json` consumed by all downstream generation commands.

## Classification Priority Chain

0. **Source Volumetrics** `table_type` from mapping Excel (analyst-declared, highest priority) — if non-null, use directly (HIGH confidence)
1. **Domain Knowledge** file (`${CLAUDE_PLUGIN_ROOT}/configs/domain_knowledge/<feature_team_name>_knowledge.md`) — explicit type hints
2. **Mapping Document** heuristics — detect audit columns in `source_column` references (H0–H4)
3. If type CANNOT be determined for ANY source table → **HALT** and ask user

## Usage

```
/classify-sources
```

Invoked automatically after `/parse-mapping`. No flags required.

## Prerequisites

- Session initialised; mapping parsed (`/parse-mapping` completed)
- `session/mapping_parsed.json` exists

## STEP 0.0 — Chain Mode Output Compression

Apply `commands/refs/chain-mode-compression.md` pattern. Compact return: `[{step}/{total}] ✓ /classify-sources — {N} tables classified, mode: {source} | Checkpoint: post_classification written`

## STEP 0 — Logging Initialization

Apply `conventions` skill logging pattern, component="de-classify-sources".

---

## Behaviour

### STEP 1 — Extract Source Tables

Read `session/mapping_parsed.json`. Collect all unique `{database}.{table}` pairs from `columns[].source_references[]` across all columns. Deduplicate. Lowercase both database and table names for matching.

### STEP 2 — Priority 0: Source Volumetrics Classification

1. Read `session_state.source_volumetrics_path`
2. If null → skip STEP 2 entirely (no volumetrics available)
3. If exists → load `session/source_volumetrics.json` as array of volumetric entries
4. Build volumetrics lookup dict keyed by `(source_database.lower(), source_table.lower())`
5. For each source table:
   - Look up matching volumetric entry (case-insensitive)
   - If match found AND `table_type` is not null:
     - Classify:
       - `source_table_type` = entry's `table_type` ("NonTransactional_SCD1", "NonTransactional_SCD2", or "Transactional")
       - Apply normalization: legacy `"NonTransactional"` → `"NonTransactional_SCD2"` (backward compat)
       - `classification_confidence` = `"HIGH"`
       - `classification_heuristic` = `"VOL"`
       - `classification_source` = `"source_volumetrics"`
       - `audit_columns_present` = all `null`
       - `full_column_list` = `[]`
     - Add to `classified_tables`
   - If no match OR `table_type` is null → add to `unclassified_tables`
6. Log INFO: "Volumetrics: {len(classified_tables)}/{total} tables classified"

**If `unclassified_tables` is EMPTY** → skip STEP 3 and STEP 4; jump to STEP 5 (write output).

### STEP 3 — Priority 1: Domain Knowledge Classification

For each table remaining in `unclassified_tables`:

1. Load domain knowledge from `session_state.domain_knowledge_text` (or read from `session_state.domain_knowledge_path`)
2. If domain knowledge unavailable → skip to STEP 4
3. Search for explicit table type hints matching the source table name:
   - Look for `Table type: NonTransactional_SCD2` / `Table type: NonTransactional_SCD1` / `Table type: Transactional` annotations
   - Look for grain/type hints: "SCD Type 2" → NonTransactional_SCD2; "SCD Type 1" / "overwrite" / "reference table" → NonTransactional_SCD1; "append-only" → Transactional
   - Look for partition column hints: `active` partition → NonTransactional_SCD2; `dw_bus_dt` partition without eff_start/end → NonTransactional_SCD1 or Transactional
   - Default when ambiguous NonTransactional detected without SCD-specific signals: `NonTransactional_SCD2` (safer — SCD2 is more common)
4. If found → classify with:
   - `classification_source` = `"domain_knowledge"`
   - `classification_confidence` = `"MEDIUM"`
   - `classification_heuristic` = `"DK"`
   - `audit_columns_present` = all `null`
   - `full_column_list` = `[]`
5. Move classified tables from `unclassified_tables` to `classified_tables`

### STEP 4 — Priority 2: Mapping Document Heuristics

For each table remaining in `unclassified_tables`:

1. From `session/mapping_parsed.json`, collect all `source_column` names referenced for this source table
2. Apply audit column heuristics against those column names:

| Heuristic | Condition | Type | Confidence |
|-----------|-----------|------|------------|
| **H0-map** | ALL of {eff_start_date, eff_end_date, active, dw_upd_lod_tmp} present in source columns | NonTransactional_SCD2 | MEDIUM |
| **H0b-map** | {dw_bus_dt, dw_lod_tmp} present + NONE of {eff_start_date, eff_end_date, active} | Transactional | MEDIUM |
| **H0c-map** | {dw_lod_tmp, dw_upd_lod_tmp} present + NONE of {eff_start_date, eff_end_date, active} + NO dw_bus_dt | NonTransactional_SCD1 | MEDIUM |
| **H1-map** | {eff_start_date, eff_end_date} present | NonTransactional_SCD2 | LOW |
| **H3-map** | Column name contains `event_date`/`transaction_date`/`posted_date` | Transactional | LOW |

3. If matched → classify with:
   - `classification_source` = `"mapping_document"`
   - `classification_confidence` = per heuristic table above
   - `classification_heuristic` = per heuristic table above
   - `audit_columns_present` = set booleans for detected audit columns (others = null)
   - `full_column_list` = `[]`
4. Move classified tables from `unclassified_tables` to `classified_tables`

### STEP 4a — HALT on Unclassified Tables

If `unclassified_tables` is still NON-EMPTY after all priorities:

- Log ERROR: "PIPELINE HALTED: Cannot determine source table type"
- Display:
  ```
  ⛔ PIPELINE HALTED: Cannot determine source table type for:
    - {db1.table1}
    - {db2.table2}

  Fallback classification failed — neither source volumetrics, domain knowledge,
  nor mapping document provided enough signal.

  Options:
    1. Add table type hints to domain knowledge file:
       ${CLAUDE_PLUGIN_ROOT}/configs/domain_knowledge/<feature_team_name>_knowledge.md
       (Look up Feature Team Name:
         - If platform = Glue → `tenancy` skill Tenancy Registry (match Hive/Iceberg Database column)
         - If platform = Databricks → `databricks-tenancy` skill Tenancy Infrastructure Registry (match Target DB column))
       Example: "### source_table_name\n- **Table type**: NonTransactional (SCD Type 2)"
    2. Ensure mapping document includes audit columns (eff_start_date, dw_bus_dt, etc.)
       in source column references
    3. Add Source Volumetrics tab to the mapping Excel with table_type per source table
  ```
- **Do NOT continue** to downstream commands

### STEP 5 — Write Output

Write `session/source_table_metadata.json` conforming to `${CLAUDE_PLUGIN_ROOT}/schemas/source_table_metadata.schema.json`.

Each entry keyed by `db.table` (lowercase):
```json
{
  "e_ilp_db.account_wm": {
    "source_table_type": "NonTransactional_SCD2",
    "classification_confidence": "HIGH",
    "classification_heuristic": "VOL",
    "classification_source": "source_volumetrics",
    "audit_columns_present": {
      "eff_start_date": null,
      "eff_end_date": null,
      "active": null,
      "dw_upd_lod_tmp": null,
      "dw_bus_dt": null,
      "dw_lod_tmp": null
    },
    "full_column_list": [],
    "classified_at": "<ISO 8601 timestamp>"
  }
}
```

Update `session_state.json`:
```json
{
  "source_table_metadata": {
    "status": "completed",
    "classified_at": "<ISO 8601>",
    "total_sources": N,
    "non_transactional_scd1_count": W,
    "non_transactional_scd2_count": X,
    "transactional_count": Y,
    "unknown_count": 0,
    "volumetrics_classified_count": V,
    "fallback_count": F,
    "output_file": "session/source_table_metadata.json"
  }
}
```

### STEP 6 — Context Checkpoint Write (Full-Automation Only)

If `session_state.auto_chain.enabled == true`, write `chain_checkpoints.post_classification` to `session/session_state.json`:

```json
{
  "chain_checkpoints": {
    "post_classification": {
      "source_table_types": { "db.table1": "NonTransactional_SCD2", "db.table2": "Transactional" },
      "classification_status": "success",
      "tables_classified_count": N,
      "volumetrics_count": V,
      "domain_knowledge_count": D,
      "mapping_document_count": M,
      "timestamp": "<ISO 8601>"
    }
  }
}
```

## Output Files

- `session/source_table_metadata.json` — per-source type classification per `${CLAUDE_PLUGIN_ROOT}/schemas/source_table_metadata.schema.json`
- `session/audit_log.jsonl` — append entry with source tables classified and classification sources

## Notes

**Automatic Invocation**: This command is invoked automatically after `/parse-mapping` as part of the pipeline flow.

**Volumetrics Fast Path**: If Source Volumetrics tab provides `table_type` for ALL source tables, classification completes in STEP 2 with no further processing needed.

**Downstream Impact**: `session/source_table_metadata.json` is consumed by:
- `glue-wrapper-agent` → config.json source grouping (non-transactional vs transactional per source)
- `transform-generator-agent` → filter strategy awareness in prepare_sources()
- `source-table-type-consistency-validator` → validates config matches classification

**Confidence Levels**:
- HIGH = Source Volumetrics (analyst-declared, authoritative)
- MEDIUM = Domain Knowledge or strong mapping-document heuristic (H0-map, H0b-map)
- LOW = Weak mapping-document heuristic (H1-map, H3-map)
