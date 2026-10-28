---
description: "Conditional STTM extension for Teradata SQL dialect — pre-processes non-standard syntax (LOCKING ROW, TITLE, COLLECT STATS) before sqlglot parsing with dialect-specific configuration."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-28
---

# Teradata Dialect Extension (Lineage)

> **Loaded conditionally** — only when Teradata dialect is detected (QUALIFY, SEL, ZEROIFNULL, etc.).

## Dialect Detection and Pre-processing

### SQL Dialect Detection

**Detection order:**
1. User-specified dialect in input (if `code_artifacts[].dialect` is provided)
2. Teradata indicators — any of: `QUALIFY` clause, `SEL` (without `ECT`), `ZEROIFNULL`, `NULLIFZERO`, `OREPLACE`, `OTRANSLATE`, `STRTOK`, `CASESPECIFIC`, `FORMAT '...'` on column, `LOCKING ROW`, `RANGE_N`, `HASHROW`, `SET TABLE` / `MULTISET TABLE`, `NORMALIZE`, `EXPAND ON`
3. Default: generic SQL (sqlglot default)

### Teradata Pre-processing (before sqlglot parse)

Strip syntactic noise that sqlglot's Teradata dialect doesn't handle:
- `LOCKING ROW FOR ACCESS` / `LOCKING TABLE ... FOR ACCESS` → remove entirely
- `(TITLE '...')` on columns → remove (display metadata, not transformation)
- `COLLECT STATS` statements → skip entirely

### sqlglot Dialect Parameter

- Teradata detected → `sqlglot.parse_one(sql, read='teradata')`
- Use `MappingSchema(schema_dict, dialect='teradata')` for qualify_columns
- Generic → `sqlglot.parse_one(sql)` (current behavior)

### Teradata-Specific Transformation Signals

| Teradata Function | Signal | Transformation Type |
|-------------------|--------|-------------------|
| `QUALIFY ROW_NUMBER() OVER(...) = 1` | dedup_qualify | Derived |
| `ZEROIFNULL(col)` | null_handling | Derived (equivalent to COALESCE(col, 0)) |
| `NULLIFZERO(col)` | null_handling | Derived (equivalent to NULLIF(col, 0)) |
| `OREPLACE(col, old, new)` | string_transform | Derived (equivalent to REPLACE) |
| `OTRANSLATE(col, from, to)` | string_transform | Derived (equivalent to TRANSLATE) |
| `STRTOK(col, delim, n)` | string_transform | Derived (string tokenization) |
| `RANGE_N(col BETWEEN...)` | partition_function | Derived |
| `FORMAT 'pattern'` | display_format | Note only — not a transformation (strip) |

## QUALIFY Extraction Rules (Teradata / Spark SQL)

- QUALIFY is a row-filtering clause (like WHERE, but applied after window function evaluation)
- Extract the QUALIFY expression into `filters_extracted` as a dedicated QUALIFY filter:
  ```json
  { "qualify_clauses": ["ROW_NUMBER() OVER (PARTITION BY acct_id ORDER BY eff_dt DESC) = 1"] }
  ```
- Columns in PARTITION BY and ORDER BY within the QUALIFY window function are filter-context columns — record them in `filters_extracted`, NOT as per-column lineage sources
- The column being filtered (e.g., ROW_NUMBER() result) does NOT appear as a target column unless it is explicitly selected in the SELECT list
- When QUALIFY references columns from multiple tables in PARTITION BY/ORDER BY, apply the Unqualified Column Resolution cascade (Steps 1–4) for each bare column
- QUALIFY pattern `ROW_NUMBER() OVER (...) = 1` is a dedup pattern — flag with signal `["dedup_qualify"]` and note in warnings

## Additional Teradata Patterns

**NORMALIZE ON**: Merges overlapping PERIOD ranges. Source column = the PERIOD column. Transformation type = "Derived". Signal = `["teradata", "normalize"]`. Note grain change.

**EXPAND ON**: Converts a PERIOD column into individual rows (one per time unit). This fundamentally changes the grain. Signal = `["teradata", "expand"]`. Route to guided mode Q11 for grain confirmation.

**HASHROW / HASHBUCKET / ROWHASH**: Hash functions over one or more columns. List ALL input columns as source_columns. Signal = `["teradata", "hash"]`. Transformation type = "Derived".

**PERIOD data type**: Teradata's PERIOD stores start/end dates as a single column. Decompose to start and end date columns for lineage. Flag PERIOD operations (P_INTERSECT, P_NORMALIZE) for guided mode.

**SET TABLE vs MULTISET TABLE**: If source DDL declares SET TABLE, note that the source has implicit dedup semantics (no duplicate rows) — affects row count and grain analysis. Add to warnings.

**SAMPLE / TOP**: If detected in production SQL, emit warning: "SAMPLE/TOP detected — may indicate development/testing artifact, not production logic."

## BTEQ Parameter Resolution (MANDATORY for Teradata BTEQ scripts)

BTEQ scripts inject runtime parameters via `.IMPORT DATA ... USING` blocks. These parameters appear as `:param_name` references in subsequent SQL and are NOT table columns — they are runtime-injected values.

### Detection

Scan for BTEQ `.IMPORT` blocks preceding SQL statements:

```
.IMPORT DATA FILE = 'filename'
USING (
  BILLING_PERIOD  CHAR(6),
  DATE_BILLING_DAY19  DATE FORMAT 'YYYY-MM-DD',
  DATE_BILLING_DAY20  DATE FORMAT 'YYYY-MM-DD',
  CUR_BILLING_PERIOD  CHAR(6)
)
```

### Extraction Rules

1. **Parse the USING block**: Extract each parameter as `{name: <param_name>, datatype: <type>, format: <format_or_null>}`.
2. **Register in `resolved_variables{}`**: For each extracted parameter:
   ```json
   {
     "BILLING_PERIOD": {
       "value": ":BILLING_PERIOD",
       "source_statement": ".IMPORT DATA USING",
       "resolved": false,
       "referenced_tables": [],
       "parameter_type": "bteq_import"
     }
   }
   ```
3. **Preserve `:param` references literally**: When `:BILLING_PERIOD` or `:DATE_BILLING_DAY19` appears in SQL expressions (WHERE clauses, CASE conditions, function arguments), preserve the exact `:param_name` token in lineage output — do NOT substitute with a table column name, alias, or human-readable label.

### CRITICAL — Parameter vs Column Distinction

BTEQ parameters (`:DATE_BILLING_DAY19`) are **NOT** the same as table columns (`billing_date`, `date_last_billed`, etc.). They are externally injected values specific to a run — often the 19th of the billing month, a system cutoff date, or a period identifier.

**NEVER** replace a `:param_name` with:
- A column name that "sounds similar" (e.g., `:DATE_BILLING_DAY19` ≠ `billing_date`)
- A human-readable description (e.g., `:BILLING_PERIOD` ≠ "billing period")
- A table alias reference

**DO** preserve the exact `:param_name` in:
- `filters_extracted.where_clauses`: `"billing_date >= :DATE_BILLING_DAY19"`
- `expression` in lineage entries: `"CASE WHEN :DATE_BILLING_DAY19 >= autop.Date_EFF THEN ..."`
- `business_logic` in row output: exact `:param` reference maintained

### BTEQ Control Command Stripping

Before SQL parsing, strip BTEQ-specific control commands that are NOT SQL:
- `.LOGON`, `.LOGOFF`, `.QUIT`, `.EXIT`, `.REMARK`
- `.SET`, `.SHOW`, `.EXPORT`, `.IMPORT` (the block itself — after extracting USING parameters)
- `.RUN FILE`, `.COMPILE`
- `.IF ERRORCODE <> 0 THEN .GOTO` and `.LABEL` directives
- `.DATABASE` (set default database context — note the database name for unqualified table resolution but do NOT pass to sqlglot)

Strip these commands entirely before passing remaining SQL to sqlglot. They are Teradata session-management commands, not transformation logic.
