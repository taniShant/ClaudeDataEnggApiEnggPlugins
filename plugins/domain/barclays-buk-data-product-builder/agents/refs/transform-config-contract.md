---
description: "Contract defining the boundary between config-declared behaviour and transform-generated code — covers SourceReader filter resolution (3-case logic) and multi-table scenario support at runtime."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-07-08
---

# Config Contract — What SourceReader/TargetWriter Handle at Runtime

**PURPOSE**: Define the boundary between config-declared runtime behaviour (handled by SourceReader and TargetWriter) and transform-generated code. The transform MUST NOT duplicate anything declared in config. Read this BEFORE generating any transformation code.

---

## SourceReader Filter Resolution — 3-Case Logic

SourceReader (`source_reader.py`) applies filters using this resolution:

```python
expr = section[table_alias] if table_alias in section else section.get("default")
```

**Config layout detection is automatic.** SourceReader supports both:
- **Single-data-flow**: `config['filters'][operation][table_type][alias|default]`
- **Multiple-data-flow**: `config['filters'][operation][source_system][table_type][alias|default]`

The reader detects which layout is in use by checking whether first-level keys under `config['source']` are known table_type values (`non-transactional`, `non-transactional-scd1`, `transactional`) or source_system names. No separate reader template is needed for multiple-data-flow pipelines.

| Case | Condition | Behaviour |
|------|-----------|-----------|
| 1 | Alias key **absent** from section | Use `default` filter |
| 2 | Alias key **present** with non-empty value | Use alias filter **exclusively** (default NOT merged) |
| 3 | Alias value = `'1=1'` | No restriction (explicit override to remove filtering) |
| 4 | Alias key **present** but value is `""` or `null` | **Treated as no restriction** (same runtime effect as Case 3) — prefer explicit `'1=1'` |

> ⚠️ **Empty/null values**: If an alias key exists but its value is empty (`""`) or `null`, the runtime truthiness check (`if expr:`) treats it as "no filter" — equivalent to `'1=1'`. This is intentional but implicit. Always prefer the explicit `'1=1'` override to signal intent. Config generators (`/gen-config`) MUST NOT emit empty filter values — either omit the key entirely (to inherit default) or write `'1=1'` explicitly.

### Operation Override — Catch-Up Mode Detection

SourceReader resolves its **effective operation** at construction:
```python
self._effective_operation = config.get("_source_operation_override", self.operation)
```

When the driver (Databricks) or wrapper (Glue) detects that `system_date - business_date > catch_up_threshold_days` AND the operation is `day1` or `bau`, it sets `config["_source_operation_override"] = "catch_up_mode"` before instantiating the transform. SourceReader uses `_effective_operation` for filter lookup; TargetWriter always uses the original operation — write strategy is unaffected.

| Runtime State | `self.operation` | `_effective_operation` | Filter Section Used |
|---|---|---|---|
| Normal BAU (no gap) | `"bau"` | `"bau"` | `filters.day1` |
| BAU with date gap > threshold | `"bau"` | `"catch_up_mode"` | `filters.catch_up_mode` |
| Normal day0 | `"day0"` | `"day0"` | `filters.day0` |

**Transform implication**: This is transparent to the transform — it always receives source DataFrames with the correct filter already applied. No transform code change is needed for catch-up scenarios.

**CRITICAL**: When an alias key is present, the `default` is NEVER applied. The alias entry must be self-contained — if it needs the default condition too, the default expression must be included explicitly:
```yaml
filters:
  day1:
    non_transactional:
      default: "active = '1'"                                         # applied to all aliases WITHOUT their own key
      cmrcase: "active = '1' AND status NOT IN ('CLO','RED','WOF')"   # exclusive — includes default + business
```

---

## Standard Default Filters (Always Present in Config)

These filters are ALWAYS populated from the config template. They represent the platform's standard temporal boundary logic:

| table_type | operation | Default Filter | Semantic |
|---|---|---|---|
| NonTransactional | day0 | `eff_start_date <= '{current_business_date}'` | Historical records up to business date |
| NonTransactional | day1 / bau | `active = '1'` | Current SCD2 records only |
| NonTransactional | catch_up_mode | `eff_start_date <= '{current_business_date}' AND eff_end_date > '{current_business_date}'` | Point-in-time valid records |
| Transactional | day0 | `dw_bus_dt <= '{current_business_date}'` | All transactions up to business date |
| Transactional | day1 / bau | `dw_bus_dt = '{current_business_date}'` | Today's transactions only |
| Transactional | catch_up_mode | `dw_bus_dt <= '{current_business_date}'` | Same as day0 (historical boundary) |

**Transform implication**: These are ALWAYS applied by SourceReader before `self.source_data[alias]` is available to the transform. NEVER duplicate them.

---

## Alias-Specific Business Filters (Config-Declared)

`/gen-config` extracts custom business filters from the mapping's `transformation_logic` column and writes them as alias-specific entries in config. Examples:

| Mapping transformation_logic (NL) | Extracted Business Filter | Config Entry (day1.non_transactional) |
|---|---|---|
| "Filter where status NOT IN ('CLO','RED','WOF')" | `status NOT IN ('CLO','RED','WOF')` | `cmrcase: "active = '1' AND status NOT IN ('CLO','RED','WOF')"` |
| "Only records where type = 'RETAIL'" | `type = 'RETAIL'` | `account: "active = '1' AND type = 'RETAIL'"` |
| "Exclude expired records (flag = 'N')" | `flag != 'N'` | `ref_product: "active = '1' AND flag != 'N'"` |

**Transform implication**: If a filter is declared in the filter manifest (`session/generated_configs/{table}_filters.json`), the transform MUST NOT generate a `.filter()` call for it. Emit a comment instead:
```python
# SourceReader applies 'active = '1' AND status NOT IN ('CLO','RED','WOF')' from config for alias 'cmrcase' — not duplicated here
```

### Config Generation Constraint

`/gen-config` MUST NOT emit empty or null filter values. When extracting business filters from the mapping's `transformation_logic` column:

| Extraction Result | Action |
|---|---|
| Valid filter expression (e.g. `status != 'CLO'`) | Write as alias-specific entry (Case 2) |
| No filter applicable to this alias | **Omit the key** — alias inherits `default` (Case 1) |
| Explicit "no filter" / "all records" intent | Write `'1=1'` (Case 3) |
| Empty string or null after parsing | **Omit the key** — never write `""` or `null` to config |

This prevents the ambiguous Case 4 state from reaching runtime and ensures config intent is always explicit.

---

## What Filters REMAIN in Transform Code

Only these categories belong as `.filter()` calls in the transform:

| Category | Example | Why Not Config |
|---|---|---|
| Post-join filters | `.filter(F.col("a.key") == F.col("b.key"))` after joining A and B | References columns from multiple sources — SourceReader reads sources independently |
| Cross-source derivation filters | `.filter(F.col("derived_score") > 100)` on a column computed from 2+ sources | Column doesn't exist until after transformation step |
| Aggregation output filters | `.filter(F.col("count") >= 5)` after groupBy | Operates on aggregated DataFrame, not raw source |
| Window function output filters | `.filter(F.col("row_num") == 1)` after ROW_NUMBER dedup | Operates on window result |

**Decision rule**: If the filter operates on columns from a SINGLE source alias and could be expressed as a SQL WHERE clause on that source table → it belongs in config. If it requires columns from multiple sources or computed columns → it belongs in transform.

---

## Broadcast Scope Separation

| Broadcast Context | Owner | Config/Transform |
|---|---|---|
| CDC merge broadcast (main source vs target during SCD2 merge) | `config['cdc']['broadcast_source']` → TargetWriter/run_cdc | **Config** — transform does NOT touch this |
| LOOKUP join broadcast (small reference table joined to enrich main table) | Transform code | **Transform** — `F.broadcast(lookup_df)` in join |

### How to Identify MAIN vs LOOKUP:

| Role | Characteristics | Broadcast in Transform? |
|---|---|---|
| **MAIN / Driver** | Majority of target columns derive from it; rows from this table map ~1:1 to target rows; appears first in source_tables | ❌ NEVER — config handles via `cdc.broadcast_source` |
| **LOOKUP / Reference** | Joined to provide 1-2 enrichment columns; name contains `_ref`, `_decode`, `_dim`, `_lookup`; typically small | ✓ YES — `F.broadcast(lookup_df)` in join |

**Decision rule:**
1. Count `source_references` per alias across all target columns
2. Alias with the MOST references = MAIN (do NOT broadcast in transform)
3. Aliases with few references = LOOKUP candidates (broadcast if small)
4. If uncertain → treat as MAIN (do not broadcast) — safer default

### Broadcast Hints from Volumetrics:

| Condition | For MAIN table | For LOOKUP table |
|---|---|---|
| `broadcast_hint = true` | Ignore in transform; config `cdc.broadcast_source` handles it | Apply `F.broadcast()` in join |
| `estimated_size_gb < 0.01` | Ignore in transform | Auto-broadcast (apply `F.broadcast()`) |
| `estimated_size_gb >= 0.01` | Ignore | Do NOT auto-broadcast |

---

## Source Column Allow-List (from Config)

Config's source column lists provide the authoritative column list per source alias. The transform generator uses this to:
1. Validate all `F.col("X")` references → X must exist in the config column list for that alias
2. Understand available data per source for join key selection
3. Ensure no hallucinated columns

The column list location depends on config layout:
- **Single-data-flow**: `source.{table_type}.{alias}.columns`
- **Multiple-data-flow**: `source.{source_system}.{table_type}.{alias}.columns`

The filter manifest (`session/generated_configs/{table}_filters.json`) includes the same column data under `source_columns` for fast access.

---

## File-Based Source and Target Configuration

When `io_mode` is `file` or `hybrid`, the config contains additional sections for parquet file I/O. These are handled by SourceReader and TargetWriter — the transform code is unaffected.

**Emission rule**: `target_io` (in environments block) and `source_file_paths` (in environments block) MUST NOT be emitted when file is not involved as source or target. `target_io` is only present when `session_state.target_io` exists. `source_file_paths` is only present when `io_mode` is `file` or `hybrid`. For table-only pipelines, both sections are omitted entirely from the generated config.

### File Source Config (`source.file`)

Populated by `/gen-config` STEP 1.8 when the mapping has file-based sources. Each entry follows the same pattern as table source entries (alias → config). The root-level `source.file.{alias}` holds columns, filter, and the original path from the mapping (dev environment default).

**Databricks (YAML):**
```yaml
source:
  file:
    customer_events:
      path: "/Volumes/raw_catalog/raw_schema/raw_volume/customer_events"
      columns: [event_id, customer_id, event_date]
      filter: "event_date >= '2024-01-01'"  # optional
```

**Glue (JSON):**
```json
"source": {
  "file": {
    "customer_events": {
      "path": "s3://raw-bucket/data/customer_events",
      "columns": ["event_id", "customer_id", "event_date"]
    }
  }
}
```

Path is the absolute storage path from the mapping document (Column H when source_database = `(file:parquet)`):
- **Glue**: `s3://` URI (e.g., `s3://raw-bucket/data/customer_events/`). SourceReader uses it as-is. Root-level path is the single source of truth.
- **Databricks**: `/Volumes/` path (e.g., `/Volumes/raw_catalog/raw_schema/raw_volume/customer_events/`). The root-level path stores the original mapping value (dev default). Per-environment paths are stored in `environments.{env}.source_file_paths.{alias}`. The driver overrides the root-level path at runtime from the active environment's `source_file_paths`:
  ```python
  for alias, path in env_config.get("source_file_paths", {}).items():
      config["source"]["file"][alias]["path"] = path
  ```
  **Dev** receives the actual path from the mapping. **Other environments** (preprd, prd, uat) receive `"{{REPLACE_BEFORE_PROMOTION}}"` — engineers must replace these with the correct environment-specific Volume paths before promoting the pipeline.

**Transform implication**: File sources are read by SourceReader and returned in `self.source_data[alias]` alongside table sources. The transform accesses them identically — no code change needed.

### File Target Config (`target_io`)

Populated by `/gen-config` STEP 3.8 when the mapping specifies a parquet file target.

**Databricks (YAML):** `target_io` is placed inside each `environments.{env}` block (same pattern as staging paths) with the per-environment catalog already resolved. The driver resolves the active environment's `target_io` at runtime via `config["target_io"] = env_config["target_io"]`, placing it at the root level for TargetWriter to consume.

```yaml
environments:
  dev:
    target_catalog: "DEV_BUK_COMPLAINTS_CDP"
    # ...
    target_io:
      path: "/Volumes/DEV_BUK_COMPLAINTS_CDP/cdp_uk_complaints/file_data/mortgage_account"
      write_mode: "append"
      partition_by: ["dw_bus_dt"]
      compression: "snappy"
  prd:
    target_catalog: "PRD_BUK_COMPLAINTS_CDP"
    # ...
    target_io:
      path: "/Volumes/PRD_BUK_COMPLAINTS_CDP/cdp_uk_complaints/file_data/mortgage_account"
      write_mode: "append"
      partition_by: ["dw_bus_dt"]
      compression: "snappy"
```

**Glue (JSON):** `target_io` remains at the root level with a relative path. The wrapper resolves `s3_bucket` at runtime:

```json
"target_io": {
  "path": "data/file_data/fdp_uk_mortgage_db/mortgage_account",
  "write_mode": "append",
  "partition_by": ["dw_bus_dt"],
  "compression": "snappy"
}
```

**Transform implication**: TargetWriter checks for `target_io` in config. When present, `write()` dispatches to `write_parquet()` instead of the table-based strategies. The transform still calls `self.writer.write(df)` — no code change needed.

**When `target_io` is present:**
- CDC section is **omitted** from config (no MERGE on parquet)
- `rolling_deletion` section is **omitted** (no DELETE on parquet)
- The existing `target` section is still populated (used for naming, audit logging, process_name)

---

## Rolling Deletion — Config-Owned Post-Write Deletion

`rolling_deletion` is a **config-owned** section — NOT transform-owned. When present, TargetWriter reads and executes the deletion predicate autonomously after each successful write.

**Config structure:**
```yaml
rolling_deletion:
  enabled: true
  predicate: "dw_bus_dt < CAST('{current_business_date}' AS DATE) - INTERVAL 90 DAY"
```

| Aspect | Detail |
|---|---|
| Owner | Config + TargetWriter (autonomous) |
| Applicable table types | Transactional, NonTransactional_SCD1 |
| NOT applicable | NonTransactional_SCD2 — physical deletion destroys SCD2 history (soft-expire pattern must be preserved) |
| Template variable | `{current_business_date}` — interpolated by TargetWriter at runtime |
| Execution | `DELETE FROM <target> WHERE <predicate>` after every successful `write()` call |

**Transform implication**: Transform code MUST NOT implement any deletion logic. Rolling deletion is entirely the writer's responsibility. If the config contains a `rolling_deletion` section, the transform should not generate any `.filter()` or `DELETE` statements to replicate this behaviour — TargetWriter handles it autonomously after `write()` completes.

---

## Per-Source-System Config (when source_systems is non-empty)

When `session_state.data_flow_detection.source_systems` is non-empty (declared via `source_system` key in Additional Context Column K):

- Each config uses **flat single-flow layout** scoped to one source_system
- SourceReader/reader sees standard `source.{table_type}.{alias}` layout — no runtime multi-flow detection needed
- `pipeline.process_name` includes source_system suffix (e.g., `{schema}_{table}_{source_system}`) for independent DateControl and audit tracking
- Filter manifest path includes source_system: `session/generated_configs/{schema}_{table}_{source_system}_filters.json`
- The generation pipeline handles source_system splitting — runtime components are source_system-agnostic

---

## Summary: Transform Generation Decision Table

| Source of logic | In Config? | In Transform? | Action |
|---|---|---|---|
| Standard temporal filter (active='1', dw_bus_dt=date) | ✅ default | ❌ | SUPPRESS — emit comment |
| Custom business filter on single source | ✅ alias-specific | ❌ | SUPPRESS — emit comment |
| Post-join / cross-source filter | ❌ | ✅ | GENERATE `.filter()` |
| Aggregation/window output filter | ❌ | ✅ | GENERATE `.filter()` |
| Broadcast for LOOKUP table | ❌ | ✅ | GENERATE `F.broadcast()` |
| Broadcast for MAIN source (CDC merge) | ✅ cdc.broadcast_source | ❌ | SUPPRESS — config handles |
| Column pruning / projection | ✅ source.columns | ❌ | SUPPRESS — SourceReader prunes |
| Rolling deletion (post-write) | ✅ rolling_deletion | ❌ | SUPPRESS — TargetWriter._rolling_delete() handles autonomously |
| File source read (parquet) | ✅ source.file | ❌ | SUPPRESS — SourceReader handles |
| File target write (parquet) | ✅ target_io | ❌ | SUPPRESS — TargetWriter handles |
