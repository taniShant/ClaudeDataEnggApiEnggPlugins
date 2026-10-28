---
description: "Canonical reference defining which audit columns (eff_start_date, eff_end_date, dw_bus_dt, etc.) are required for each table type — SCD2, SCD1, and Transactional — used by transform and DDL generation."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-25
canonical_source: "${CLAUDE_PLUGIN_ROOT}/configs/sttm/audit_columns.yaml"
---

# Audit Columns by Table Type (Canonical Reference)

> **Single source of truth** for audit column sets per table type. All agents,
> commands, and validators **must reference this file** rather than inline
> audit column lists. For full column definitions (datatypes, logic templates,
> requires_source flags), see `${CLAUDE_PLUGIN_ROOT}/configs/sttm/audit_columns.yaml`.

| Table Type              | Audit Columns                                                        | Count |
|-------------------------|----------------------------------------------------------------------|-------|
| NonTransactional_SCD2   | eff_start_date, eff_end_date, active, dw_lod_tmp, dw_upd_lod_tmp    | 5     |
| NonTransactional_SCD1   | dw_lod_tmp, dw_upd_lod_tmp                                          | 2     |
| Transactional           | dw_bus_dt, dw_lod_tmp                                                | 2     |

## Key Rules

- `dw_bus_dt` is **Transactional-only** (Transactional tables use `dw_bus_dt` + `dw_lod_tmp` — 2 columns, as shown in the table above) — never add it to SCD1 or SCD2 tables.
- Day1 transforms for SCD2 must **never derive** eff_start_date, eff_end_date, or active
  (the Iceberg MERGE handles these). dw_lod_tmp and dw_upd_lod_tmp may be set pre-write
  by some pipelines.
- For SCD1, there are no temporal/history columns — only load timestamps.
- **`high_end_date` policy (SCD2):** Accept both `9999-12-31` and `3499-12-31` as SCD2 sentinel signals during detection and classification; always emit `3499-12-31` in generated output (config, transforms, and DDL). The canonical emit value is defined in `${CLAUDE_PLUGIN_ROOT}/configs/plugin.config.json` → `scd2_defaults.high_end_date`.
