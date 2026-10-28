---
description: "Databricks SQL conventions for Data Validation — 3-part catalog.schema.table naming, resolved catalog substitution from tenancy registry, and platform-specific syntax loaded by dv-databricks-renderer-agent."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-26
---

# Databricks SQL Patterns for Data Validation

Loaded by `dv-databricks-renderer-agent` when the validation engine targets Databricks.

## Platform Conventions

### Parameterization — 3-Part Naming

All table references use 3-part dot-qualified identifiers:

```
{{catalog}}.{{schema}}.{{table}}
```

> **SUBSTITUTION RULE**: The patterns below use `{{source_catalog}}`, `{{target_catalog}}`, `{{source_schema}}`, `{{target_schema}}`, `{{source_table}}`, and `{{target_table}}` as template tokens. The renderer agent MUST replace every occurrence with the actual resolved value from the validation plan's `parameters{}` object (populated via `/dv-generate` Step 0.5 catalog resolution → contract → plan passthrough). The rendered SQL must contain literal catalog names (e.g., `077382350852_buk_data_products.landing_db.source_table`), never `{{...}}` tokens. The ONLY `{{...}}` token permitted in final rendered SQL is `{{control_date}}` (parameterized at execution time by the user).

Date parameters are rendered as typed literals:

```sql
DATE '{{control_date}}'
```

### Deterministic Ordering

All queries that produce row-level output MUST include an ORDER BY clause containing all PK columns followed by `eff_start_date` (when present):

```sql
ORDER BY {{pk_columns}}, eff_start_date
```

**UNION ALL chains**: When multiple SELECT branches are joined with UNION ALL,
ORDER BY must appear ONLY once, after the FINAL branch. Never inside an intermediate branch.

## SQL Function Reference

### Window Functions

```sql
LEAD(eff_start_date) OVER (PARTITION BY {{pk_columns}} ORDER BY eff_start_date)
LAG(eff_start_date)  OVER (PARTITION BY {{pk_columns}} ORDER BY eff_start_date)
```

### Date Functions

```sql
DATEDIFF(d1, d2)                  -- difference in days (d1 - d2)
DATE_ADD(d, n)                    -- add n days to date d
DATE '{{control_date}}'           -- typed date literal
```

### Set Operations

- `EXCEPT` — supported (set-based, removes duplicates)
- `EXCEPT ALL` — **supported** in Databricks; use ONLY for ER-08 (keyless multiset comparison). ER-05/ER-06/ER-07 MUST use FULL OUTER JOIN on PK columns — never EXCEPT/EXCEPT ALL.
- `INTERSECT` — supported
- `INTERSECT ALL` — supported

### Null-Safe Equality

Use the ANSI SQL `IS NOT DISTINCT FROM` operator for null-safe comparisons (supported on both Athena and Databricks):

```sql
col1 IS NOT DISTINCT FROM col2    -- returns TRUE when both are NULL
```

Use `IS NOT DISTINCT FROM` in join conditions and comparisons where NULL-to-NULL equality is required.

### QUALIFY Clause

Databricks supports `QUALIFY` for filtering window function results without a subquery:

```sql
SELECT {{pk_columns}}, eff_start_date, eff_end_date
FROM {{catalog}}.{{schema}}.{{table}}
QUALIFY COUNT(*) OVER (PARTITION BY {{pk_columns}}) > 1
```

Use QUALIFY where it simplifies the query. All templates below show the QUALIFY variant where applicable.

## Check Templates

### ER-01 — Exact Row Count

```sql
-- ER-01: Row count reconciliation
WITH src_count AS (
    SELECT COUNT(*) AS cnt
    FROM (
        SELECT {{mapping_transforms}}
        FROM {{source_catalog}}.{{source_schema}}.{{source_table}}
        WHERE {{source_filter}}
    )
),
tgt_count AS (
    SELECT COUNT(*) AS cnt
    FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
    WHERE {{target_filter}}
)
SELECT
    src_count.cnt AS source_count,
    tgt_count.cnt AS target_count,
    src_count.cnt - tgt_count.cnt AS difference
FROM src_count
CROSS JOIN tgt_count
WHERE src_count.cnt != tgt_count.cnt
```

### ER-05 — PK-Based Bidirectional Reconciliation

```sql
-- ER-05: PK-based bidirectional reconciliation via FULL OUTER JOIN
-- For SCD2 tables: source_filter and target_filter use eff_start/eff_end date-range predicates
-- to scope both sides to the same point-in-time. Do NOT add active = '1' — use date-range only.
SELECT
    COALESCE(s.{{pk_col1}}, t.{{pk_col1}}) AS {{pk_col1}},
    CASE
        WHEN t.{{pk_col1}} IS NULL THEN 'SOURCE_ONLY'
        WHEN s.{{pk_col1}} IS NULL THEN 'TARGET_ONLY'
        ELSE 'MATCHED'
    END AS reconciliation_status,
    COUNT(*) AS row_count
FROM (
    SELECT {{mapping_transforms}}
    FROM {{source_catalog}}.{{source_schema}}.{{source_table}}
    WHERE {{source_filter}}
) s
FULL OUTER JOIN (
    SELECT *
    FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
    WHERE {{target_filter}}
) t
    ON {{pk_join_condition}}
WHERE t.{{pk_col1}} IS NULL
   OR s.{{pk_col1}} IS NULL
GROUP BY 1, 2
ORDER BY {{pk_columns}}
```

### ER-08 — Multiset Comparison for Keyless Tables

```sql
-- ER-08: Multiset comparison for keyless tables (GROUP BY + FULL OUTER JOIN)
WITH src_freq AS (
    SELECT {{all_target_columns}}, COUNT(*) AS freq
    FROM (
        SELECT {{mapping_transforms}}
        FROM {{source_catalog}}.{{source_schema}}.{{source_table}}
        WHERE {{source_filter}}
    )
    GROUP BY {{all_target_columns}}
),
tgt_freq AS (
    SELECT {{all_target_columns}}, COUNT(*) AS freq
    FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
    WHERE {{target_filter}}
    GROUP BY {{all_target_columns}}
)
SELECT
    {{all_target_columns_coalesced}},
    s.freq AS source_freq,
    t.freq AS target_freq
FROM src_freq s
FULL OUTER JOIN tgt_freq t
    ON {{null_safe_join_all_columns}}
WHERE s.freq IS NULL
   OR t.freq IS NULL
   OR s.freq <> t.freq
```

### SCD2-01 — Overlap Detection

```sql
-- SCD2-01: Detect temporal overlaps within PK groups
SELECT
    {{pk_columns}},
    eff_start_date,
    eff_end_date,
    next_eff_start_date
FROM (
    SELECT
        {{pk_columns}},
        eff_start_date,
        eff_end_date,
        LEAD(eff_start_date) OVER (
            PARTITION BY {{pk_columns}}
            ORDER BY eff_start_date
        ) AS next_eff_start_date
    FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
    WHERE {{target_filter}}
)
WHERE eff_end_date > next_eff_start_date
ORDER BY {{pk_columns}}, eff_start_date
```

### SCD2-02 — Gap Detection

```sql
-- SCD2-02: Detect temporal gaps within PK groups
SELECT
    {{pk_columns}},
    eff_start_date,
    eff_end_date,
    next_eff_start_date,
    DATEDIFF(next_eff_start_date, eff_end_date) AS gap_days
FROM (
    SELECT
        {{pk_columns}},
        eff_start_date,
        eff_end_date,
        LEAD(eff_start_date) OVER (
            PARTITION BY {{pk_columns}}
            ORDER BY eff_start_date
        ) AS next_eff_start_date
    FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
    WHERE {{target_filter}}
)
WHERE next_eff_start_date IS NOT NULL
  AND eff_end_date < next_eff_start_date
ORDER BY {{pk_columns}}, eff_start_date
```

### SCD2-03 — Boundary Stitching

```sql
-- SCD2-03: Verify temporal boundary stitching (prev.eff_end = next.eff_start)
SELECT
    {{pk_columns}},
    eff_start_date,
    eff_end_date,
    next_eff_start_date
FROM (
    SELECT
        {{pk_columns}},
        eff_start_date,
        eff_end_date,
        LEAD(eff_start_date) OVER (
            PARTITION BY {{pk_columns}}
            ORDER BY eff_start_date
        ) AS next_eff_start_date
    FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
    WHERE {{target_filter}}
)
WHERE next_eff_start_date IS NOT NULL
  AND eff_end_date != next_eff_start_date
ORDER BY {{pk_columns}}, eff_start_date
```

### SCD2-04 — Active Record Invariant

```sql
-- SCD2-04: At most one active record per PK
SELECT
    {{pk_columns}},
    COUNT(*) AS active_count
FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
WHERE {{target_filter}}
  AND active = '1'
GROUP BY {{pk_columns}}
HAVING COUNT(*) > 1
ORDER BY {{pk_columns}}
```

### SCD2-04 (QUALIFY Variant) — Active Record Invariant

```sql
-- SCD2-04: At most one active record per PK (QUALIFY variant)
SELECT
    {{pk_columns}},
    eff_start_date,
    eff_end_date,
    active
FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
WHERE {{target_filter}}
  AND active = '1'
QUALIFY COUNT(*) OVER (PARTITION BY {{pk_columns}}) > 1
ORDER BY {{pk_columns}}, eff_start_date
```

### SCD2-12 — Day 0 Initialization

```sql
-- SCD2-12: Day 0 — one version per PK, active flag correct, sentinel end date
WITH day0_check AS (
    SELECT
        {{pk_columns}},
        COUNT(*) AS version_count,
        SUM(CASE WHEN active = '1' THEN 1 ELSE 0 END) AS active_count,
        SUM(CASE WHEN eff_end_date = DATE '3499-12-31' THEN 1 ELSE 0 END) AS sentinel_count
    FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
    WHERE {{target_filter}}
    GROUP BY {{pk_columns}}
)
SELECT
    {{pk_columns}},
    version_count,
    active_count,
    sentinel_count
FROM day0_check
WHERE version_count != 1
   OR active_count != 1
   OR sentinel_count != 1
ORDER BY {{pk_columns}}
```

### NC-01 — Null Check

```sql
-- NC-01: Non-nullable column null check
SELECT
    '{{column_name}}' AS column_name,
    COUNT(*) AS null_count
FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
WHERE {{target_filter}}
  AND {{column_name}} IS NULL
HAVING COUNT(*) > 0
```

### ER-02 — Column Aggregate Match (SUM)

```sql
-- ER-02: Column aggregate reconciliation (SUM) for numeric columns
WITH src_agg AS (
    SELECT SUM({{column}}) AS source_sum
    FROM (
        SELECT {{mapping_transforms}}
        FROM {{source_catalog}}.{{source_schema}}.{{source_table}}
        WHERE {{source_filter}}
    )
),
tgt_agg AS (
    SELECT SUM({{column}}) AS target_sum
    FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
    WHERE {{target_filter}}
)
SELECT
    '{{column}}' AS column_name,
    src_agg.source_sum,
    tgt_agg.target_sum,
    ABS(src_agg.source_sum - tgt_agg.target_sum) AS diff
FROM src_agg
CROSS JOIN tgt_agg
WHERE src_agg.source_sum != tgt_agg.target_sum
```

### ER-03 — Column Aggregate Match (MIN/MAX)

```sql
-- ER-03: Column aggregate reconciliation (MIN/MAX) for non-key business columns
WITH src_agg AS (
    SELECT
        MIN({{column}}) AS source_min,
        MAX({{column}}) AS source_max
    FROM (
        SELECT {{mapping_transforms}}
        FROM {{source_catalog}}.{{source_schema}}.{{source_table}}
        WHERE {{source_filter}}
    )
),
tgt_agg AS (
    SELECT
        MIN({{column}}) AS target_min,
        MAX({{column}}) AS target_max
    FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
    WHERE {{target_filter}}
)
SELECT
    '{{column}}' AS column_name,
    src_agg.source_min,
    tgt_agg.target_min,
    src_agg.source_max,
    tgt_agg.target_max
FROM src_agg
CROSS JOIN tgt_agg
WHERE NOT (src_agg.source_min IS NOT DISTINCT FROM tgt_agg.target_min)
   OR NOT (src_agg.source_max IS NOT DISTINCT FROM tgt_agg.target_max)
```

### ER-04 — Column Aggregate Match (COUNT DISTINCT)

```sql
-- ER-04: Column aggregate reconciliation (COUNT DISTINCT) for key columns
WITH src_agg AS (
    SELECT COUNT(DISTINCT {{column}}) AS source_distinct
    FROM (
        SELECT {{mapping_transforms}}
        FROM {{source_catalog}}.{{source_schema}}.{{source_table}}
        WHERE {{source_filter}}
    )
),
tgt_agg AS (
    SELECT COUNT(DISTINCT {{column}}) AS target_distinct
    FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
    WHERE {{target_filter}}
)
SELECT
    '{{column}}' AS column_name,
    src_agg.source_distinct,
    tgt_agg.target_distinct,
    src_agg.source_distinct - tgt_agg.target_distinct AS diff
FROM src_agg
CROSS JOIN tgt_agg
WHERE src_agg.source_distinct != tgt_agg.target_distinct
```

### ER-06 — PK-Based Column-Level Mismatch Detection

```sql
-- ER-06: PK-based column-level mismatch detection (matched rows with value differences)
-- For SCD2 tables: source_filter and target_filter use eff_start/eff_end date-range predicates
-- to scope both sides to the same point-in-time. Do NOT add active = '1' — use date-range only.
SELECT
    s.{{pk_columns}},
    '{{column}}' AS column_name,
    s.{{column}} AS source_value,
    t.{{column}} AS target_value
FROM (
    SELECT {{mapping_transforms}}
    FROM {{source_catalog}}.{{source_schema}}.{{source_table}}
    WHERE {{source_filter}}
) s
INNER JOIN (
    SELECT *
    FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
    WHERE {{target_filter}}
) t
    ON {{pk_join_condition}}
WHERE NOT (s.{{column}} IS NOT DISTINCT FROM t.{{column}})
-- NOTE (UNION ALL rendering): When this template is expanded for multiple columns
-- using UNION ALL, ORDER BY must appear ONLY after the FINAL branch.
-- Do NOT include ORDER BY inside intermediate UNION ALL branches — Spark SQL syntax error.
ORDER BY {{pk_columns}}
```

### ER-07 — Key-Based Column-Level Comparison

```sql
-- ER-07: Key-based column-level comparison (null-safe)
SELECT COUNT(*) AS mismatch_count
FROM (
    SELECT {{mapping_transforms}}
    FROM {{source_catalog}}.{{source_schema}}.{{source_table}}
    WHERE {{source_filter}}
) s
JOIN (
    SELECT *
    FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
    WHERE {{target_filter}}
) t
    ON {{pk_join_condition}}
WHERE NOT (s.{{column}} IS NOT DISTINCT FROM t.{{column}})
```

### SCD2-05 — Current-Flag Value Check

```sql
-- SCD2-05: Active flag consistency with eff_end_date sentinel
SELECT COUNT(*) AS violation_count
FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
WHERE {{target_filter}}
  AND (
    (eff_end_date = DATE '3499-12-31' AND active <> '1')
    OR (eff_end_date <> DATE '3499-12-31' AND active <> '0')
  )
```

### SCD2-06 — Open-Ended Sentinel Validation

```sql
-- SCD2-06: Active record has sentinel eff_end_date
SELECT COUNT(*) AS violation_count
FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
WHERE {{target_filter}}
  AND active = '1'
  AND eff_end_date <> DATE '3499-12-31'
```

### SCD2-07 — Historical-Record-Not-Current

```sql
-- SCD2-07: Expired records must not have sentinel eff_end_date
WITH ranked AS (
    SELECT
        {{pk_columns}},
        eff_start_date,
        eff_end_date,
        ROW_NUMBER() OVER (
            PARTITION BY {{pk_columns}}
            ORDER BY eff_start_date DESC
        ) AS rn
    FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
    WHERE {{target_filter}}
)
SELECT COUNT(*) AS violation_count
FROM ranked
WHERE rn > 1
  AND eff_end_date = DATE '3499-12-31'
```

### SCD2-07 (QUALIFY Variant) — Historical-Record-Not-Current

```sql
-- SCD2-07: Expired records must not have sentinel eff_end_date (QUALIFY variant)
SELECT
    {{pk_columns}},
    eff_start_date,
    eff_end_date
FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
WHERE {{target_filter}}
  AND eff_end_date = DATE '3499-12-31'
QUALIFY ROW_NUMBER() OVER (PARTITION BY {{pk_columns}} ORDER BY eff_start_date DESC) > 1
ORDER BY {{pk_columns}}, eff_start_date
```

### SCD2-08 — Version Uniqueness Per PK

```sql
-- SCD2-08: Each (PK, eff_start_date, eff_end_date) triple is unique
SELECT
    {{pk_columns}},
    eff_start_date,
    eff_end_date,
    COUNT(*) AS dupe_count
FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
WHERE {{target_filter}}
GROUP BY {{pk_columns}}, eff_start_date, eff_end_date
HAVING COUNT(*) > 1
ORDER BY {{pk_columns}}, eff_start_date
```

### SCD2-09 — Version Sequentiality

```sql
-- SCD2-09: Version numbers (if present) are sequential per PK
WITH sequenced AS (
    SELECT
        {{pk_columns}},
        version_number,
        LAG(version_number) OVER (
            PARTITION BY {{pk_columns}}
            ORDER BY eff_start_date
        ) AS prev_version
    FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
    WHERE {{target_filter}}
)
SELECT COUNT(*) AS violation_count
FROM sequenced
WHERE prev_version IS NOT NULL
  AND version_number <> prev_version + 1
```

### SCD2-10 — Duplicate Effective-Start Per PK

```sql
-- SCD2-10: No two versions share the same eff_start_date per PK
SELECT
    {{pk_columns}},
    eff_start_date,
    COUNT(*) AS dupe_count
FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
WHERE {{target_filter}}
GROUP BY {{pk_columns}}, eff_start_date
HAVING COUNT(*) > 1
ORDER BY {{pk_columns}}, eff_start_date
```

### SCD2-11 — Invalid Date Ordering

```sql
-- SCD2-11: eff_start_date must not exceed eff_end_date
SELECT COUNT(*) AS violation_count
FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
WHERE {{target_filter}}
  AND eff_start_date > eff_end_date
```

### SCD2-13 — Day 0 No-Unexpected-History

```sql
-- SCD2-13: Day 0 — no PK has more than one version on initial load
SELECT
    {{pk_columns}},
    COUNT(*) AS version_count
FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
WHERE {{target_filter}}
GROUP BY {{pk_columns}}
HAVING COUNT(*) > 1
ORDER BY {{pk_columns}}
```

### SCD2-14 — Day 1 New-Key

```sql
-- SCD2-14: New PK appears with a single active version
SELECT
    t.{{pk_columns}},
    COUNT(*) AS version_count,
    SUM(CASE WHEN t.active = '1' THEN 1 ELSE 0 END) AS active_count
FROM {{target_catalog}}.{{target_schema}}.{{target_table}} t
LEFT JOIN {{prior_catalog}}.{{prior_schema}}.{{prior_table}} p
    ON {{pk_join_condition_tp}}
WHERE p.{{pk_first_column}} IS NULL
GROUP BY t.{{pk_columns}}
HAVING COUNT(*) <> 1
   OR SUM(CASE WHEN t.active = '1' THEN 1 ELSE 0 END) <> 1
ORDER BY t.{{pk_columns}}
```

### SCD2-15 — Day 1 Tracked-Change

```sql
-- SCD2-15: Changed PK has exactly one closed + one new active version
SELECT
    {{pk_columns}},
    SUM(CASE WHEN active = '1' THEN 1 ELSE 0 END) AS active_count,
    SUM(CASE WHEN active = '0'
              AND eff_end_date = DATE '{{control_date}}'
         THEN 1 ELSE 0 END) AS newly_closed_count
FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
WHERE {{target_filter}}
  AND ({{changed_pk_filter}})
GROUP BY {{pk_columns}}
HAVING SUM(CASE WHEN active = '1' THEN 1 ELSE 0 END) <> 1
   OR SUM(CASE WHEN active = '0' AND eff_end_date = DATE '{{control_date}}' THEN 1 ELSE 0 END) < 1
ORDER BY {{pk_columns}}
```

### SCD2-16 — Day 1 No-Change-Idempotent

```sql
-- SCD2-16: Unchanged PK has no new version created
WITH prior_counts AS (
    SELECT {{pk_columns}}, COUNT(*) AS prior_version_count
    FROM {{prior_catalog}}.{{prior_schema}}.{{prior_table}}
    GROUP BY {{pk_columns}}
),
current_counts AS (
    SELECT {{pk_columns}}, COUNT(*) AS current_version_count
    FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
    WHERE {{target_filter}}
      AND NOT ({{changed_pk_filter}})
      AND NOT ({{new_pk_filter}})
    GROUP BY {{pk_columns}}
)
SELECT
    c.{{pk_columns}},
    c.current_version_count,
    p.prior_version_count
FROM current_counts c
JOIN prior_counts p ON {{pk_join_condition_cp}}
WHERE c.current_version_count <> p.prior_version_count
ORDER BY c.{{pk_columns}}
```

### SCD2-17 — Day 1 Late-Arriving

```sql
-- SCD2-17: Late-arriving data restitches predecessor/successor boundaries
WITH versions AS (
    SELECT
        {{pk_columns}},
        eff_start_date,
        eff_end_date,
        LAG(eff_end_date) OVER (
            PARTITION BY {{pk_columns}}
            ORDER BY eff_start_date
        ) AS prev_end,
        LEAD(eff_start_date) OVER (
            PARTITION BY {{pk_columns}}
            ORDER BY eff_start_date
        ) AS next_start
    FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
    WHERE {{target_filter}}
)
SELECT COUNT(*) AS violation_count
FROM versions
WHERE eff_start_date < DATE '{{control_date}}'
  AND eff_end_date <> DATE '3499-12-31'
  AND (prev_end IS NOT NULL AND prev_end <> eff_start_date)
  AND (next_start IS NOT NULL AND eff_end_date <> next_start)
```

### SCD2-18 — Day 1 Multi-Change-Ordering

```sql
-- SCD2-18: Multiple changes on same day for same PK are correctly ordered
SELECT
    {{pk_columns}},
    eff_start_date,
    COUNT(*) AS same_day_versions,
    SUM(CASE WHEN active = '1' THEN 1 ELSE 0 END) AS active_count
FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
WHERE {{target_filter}}
  AND eff_start_date = DATE '{{control_date}}'
GROUP BY {{pk_columns}}, eff_start_date
HAVING COUNT(*) > 1
  AND SUM(CASE WHEN active = '1' THEN 1 ELSE 0 END) <> 1
ORDER BY {{pk_columns}}
```

### NC-02 — PK Null Check

```sql
-- NC-02: Primary key column must never contain NULL
SELECT
    '{{pk_column}}' AS pk_column_name,
    COUNT(*) AS null_count
FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
WHERE {{target_filter}}
  AND {{pk_column}} IS NULL
HAVING COUNT(*) > 0
```

### DC-01 — Primary Key Uniqueness

```sql
-- DC-01: Primary key uniqueness (composite key support)
SELECT
    {{pk_columns}},
    COUNT(*) AS duplicate_count
FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
WHERE {{target_filter}}
GROUP BY {{pk_columns}}
HAVING COUNT(*) > 1
ORDER BY {{pk_columns}}
```

### DC-01 (QUALIFY Variant) — Primary Key Uniqueness

```sql
-- DC-01: Primary key uniqueness with full row context (QUALIFY variant)
SELECT
    {{pk_columns}},
    {{all_target_columns}}
FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
WHERE {{target_filter}}
QUALIFY COUNT(*) OVER (PARTITION BY {{pk_columns}}) > 1
ORDER BY {{pk_columns}}, eff_start_date
```

### DC-01a — PK + eff_start_date Uniqueness (SCD2 Whole Data)

```sql
-- DC-01a: PK + eff_start_date uniqueness for SCD2 tables (whole data)
SELECT
    {{pk_columns}},
    eff_start_date,
    COUNT(*) AS duplicate_count
FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
WHERE {{target_filter}}
GROUP BY {{pk_columns}}, eff_start_date
HAVING COUNT(*) > 1
ORDER BY {{pk_columns}}, eff_start_date
```

### DC-01b — PK Uniqueness (SCD2 Active Records Only)

```sql
-- DC-01b: PK uniqueness for SCD2 tables (active records only)
SELECT
    {{pk_columns}},
    COUNT(*) AS duplicate_count
FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
WHERE {{target_filter}}
  AND active = '1'
GROUP BY {{pk_columns}}
HAVING COUNT(*) > 1
ORDER BY {{pk_columns}}
```

### DC-02 — Business-Key + Eff_Start Uniqueness (SCD2)

```sql
-- DC-02: Business-key + eff_start_date uniqueness for SCD2 tables
SELECT
    {{business_key_columns}},
    eff_start_date,
    COUNT(*) AS dupe_count
FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
WHERE {{target_filter}}
GROUP BY {{business_key_columns}}, eff_start_date
HAVING COUNT(*) > 1
ORDER BY {{business_key_columns}}, eff_start_date
```

### DT-01 — CAST Validation

```sql
-- DT-01: Column values can be safely cast to declared datatype
SELECT
    '{{column}}' AS column_name,
    COUNT(*) AS cast_failure_count
FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
WHERE {{target_filter}}
  AND TRY_CAST({{column}} AS {{datatype}}) IS NULL
  AND {{column}} IS NOT NULL
```

### DT-02 — Precision/Scale Verification

```sql
-- DT-02: DECIMAL(p,s) columns match documented precision
SELECT
    '{{column}}' AS column_name,
    COUNT(*) AS precision_violation_count
FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
WHERE {{target_filter}}
  AND (
    LENGTH(CAST(ABS({{column}}) - FLOOR(ABS({{column}})) AS STRING)) - 2 > {{scale}}
    OR LENGTH(REPLACE(CAST(ABS({{column}}) AS STRING), '.', '')) > {{precision}}
  )
```

### DT-03 — Undocumented Precision Warning

```sql
-- DT-03: Flag numeric columns where precision is required but not documented
-- This check is always NOT_EVALUATED when the mapping does not document
-- precision/scale. It produces a metadata-only output row for the report.
SELECT
    '{{column}}' AS column_name,
    '{{datatype}}' AS declared_type,
    1 AS flagged
```

### BR-01 — Value Domain Check

```sql
-- BR-01: Column values within documented domain or enum set
SELECT
    '{{column}}' AS column_name,
    {{column}} AS invalid_value,
    COUNT(*) AS violation_count
FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
WHERE {{target_filter}}
  AND {{column}} NOT IN ({{allowed_values}})
  AND {{column}} IS NOT NULL
GROUP BY {{column}}
ORDER BY COUNT(*) DESC
```

### BR-02 — Referential Integrity Check

```sql
-- BR-02: FK references exist in parent table
SELECT
    t.{{fk_column}} AS orphan_key,
    COUNT(*) AS orphan_count
FROM {{target_catalog}}.{{target_schema}}.{{target_table}} t
LEFT JOIN {{parent_catalog}}.{{parent_schema}}.{{parent_table}} p
    ON t.{{fk_column}} = p.{{pk_column}}
WHERE {{target_filter}}
  AND p.{{pk_column}} IS NULL
  AND t.{{fk_column}} IS NOT NULL
GROUP BY t.{{fk_column}}
ORDER BY COUNT(*) DESC
```

### BR-03 — Failed Type/Domain Count

```sql
-- BR-03: Aggregated count of rows failing type or domain constraints
SELECT
    '{{column}}' AS column_name,
    SUM(CASE
        WHEN TRY_CAST({{column}} AS {{datatype}}) IS NULL
             AND {{column}} IS NOT NULL THEN 1
        ELSE 0
    END) AS type_fail_count,
    SUM(CASE
        WHEN {{column}} NOT IN ({{allowed_values}})
             AND {{column}} IS NOT NULL THEN 1
        ELSE 0
    END) AS domain_fail_count
FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
WHERE {{target_filter}}
```

### BR-04 — Aggregate Reconciliation

```sql
-- BR-04: Business-rule-level aggregate reconciliation
WITH src_agg AS (
    SELECT {{aggregate_function}}({{column}}) AS value
    FROM (
        SELECT {{mapping_transforms}}
        FROM {{source_catalog}}.{{source_schema}}.{{source_table}}
        WHERE {{source_filter}}
    )
),
tgt_agg AS (
    SELECT {{aggregate_function}}({{column}}) AS value
    FROM {{target_catalog}}.{{target_schema}}.{{target_table}}
    WHERE {{target_filter}}
)
SELECT
    '{{rule_name}}' AS rule_name,
    '{{aggregate_function}}' AS agg_func,
    src_agg.value AS source_value,
    tgt_agg.value AS target_value,
    ABS(src_agg.value - tgt_agg.value) AS diff
FROM src_agg
CROSS JOIN tgt_agg
WHERE ABS(src_agg.value - tgt_agg.value) > 0
```
