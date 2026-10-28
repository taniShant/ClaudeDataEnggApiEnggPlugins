---
description: "Conditional STTM row generation extension for file I/O — loaded when io_mode is file or hybrid to define source attribution with format markers (file:parquet) and logical name resolution."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
last_reviewed: 2026-09-24
---

# File I/O Row Generation Extension

> **Loaded conditionally** — only when `io_mode` ∈ {file, hybrid}.

**PURPOSE**: Define row generation rules for file-based sources and targets. Loaded conditionally when `io_mode` ∈ {file, hybrid}.

## Source Attribution for File Sources

When a source is a parquet file (identified by `source_io.sources[]` in session state):

| Mapping Column | Table Source (unchanged) | File Source |
|---|---|---|
| G — Source Database | `fdp_uk_db` | `(file:parquet)` |
| H — Source Table Name | `fdp_uk_db.account_table` | Absolute storage path (e.g., `s3://raw-bucket/data/customer_events/`); `logical_name` derived from basename |
| I — Source Column Name | `fdp_uk_db.account_table.col` | `{logical_name}.{column}` (e.g., `customer_events.event_id`) |

### Rules

1. `(file:parquet)` in Source Database (col G) is a **format marker** — analogous to `(system)` and `(derived)`. It signals that this source is a parquet file, not a database table.
2. Source Table (col H) contains the **absolute storage path** to the parquet file/directory. The **logical name** is derived from the path basename (last non-empty segment after stripping trailing `/`). This logical name acts as a pseudo-table reference throughout the mapping.
3. Source Column (col I) uses a **2-part FQN** (`{logical_name}.{column}`) instead of the standard 3-part (`{database}.{table}.{column}`), since parquet files have no database hierarchy. The `logical_name` here is the basename derived from col H.

## Structured Business Logic with File Sources

The existing structured format (Driver Table, Join N, Value) works identically for file sources — they use their logical names as table aliases:

```
Driver Table: customer_events (ce)
Join 1 Table: fdp_uk_mortgage_db.account_table (at)
Join 1 Type: LEFT JOIN
Join 1 On: ce.customer_id = at.customer_id
Value: ce.event_type
```

File sources can be the driver table or a joined table — position does not depend on I/O mode.

## Hybrid Source Attribution Example

When a target column derives from BOTH a file source and a table source (hybrid `io_mode`), source columns G/H/I use mixed formats — file refs use 2-part FQN, table refs use 3-part:

**Scenario:** Target column `customer_event_type` = `COALESCE(ce.event_type, at.default_event_type)` where `customer_events` is a parquet file source and `account_table` is a database table.

| Column | Value |
|--------|-------|
| G — Source Database | `(file:parquet), fdp_uk_mortgage_db` |
| H — Source Table Name | `s3://raw-bucket/data/customer_events/, fdp_uk_mortgage_db.account_table` |
| I — Source Column Name | `customer_events.event_type, fdp_uk_mortgage_db.account_table.default_event_type` |
| J — Business Logic | `Driver Table: customer_events (ce)\nJoin 1: LEFT JOIN fdp_uk_mortgage_db.account_table (at) ON ce.customer_id = at.customer_id\nJoin 1 Filters: []\nValue: COALESCE(ce.event_type, at.default_event_type)` |
| M — Transformation Type | `Derived` |

**Key rules for hybrid rows:**
- File source entries use `(file:parquet)` in G, absolute storage path in H, `{logical_name}.{column}` (2-part) in I
- Table source entries use real database in G, `{db}.{table}` in H, `{db}.{table}.{column}` (3-part) in I
- Entries are comma-separated with positional correspondence across G, H, and I
- Business Logic uses the same structured format — file sources appear by logical_name, table sources by `{db}.{table}`

## Audit Columns for File Targets

When `target_io` is present (target is a parquet file), audit column selection follows `file_target_overrides` in `audit_columns.yaml`:

- **SCD2 + file target = NOT SUPPORTED** — validation blocker FIO3 prevents this combination
- **SCD1 + overwrite**: Only `dw_lod_tmp` (no `dw_upd_lod_tmp` — full replace makes update timestamp meaningless)
- **SCD1 + append**: Both `dw_lod_tmp` and `dw_upd_lod_tmp`
- **Transactional**: `dw_bus_dt` and `dw_lod_tmp` (same as table target)

## Source Volumetrics for File Sources

File sources get volumetric entries in the Source Volumetrics sheet:

| Field | Value |
|---|---|
| Source Database | `(file:parquet)` |
| Source Table | `{logical_name}` (basename derived from storage path) |
| Estimated Rows | From interview Q5.9a or `(unknown)` |
| Estimated Size (GB) | From interview Q5.9b or `(unknown)` |
| Table Type | `file` |
| Broadcast Hint | Based on estimated size (Y if ≤ 10,000 rows) |
