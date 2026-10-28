# Structured Transformation Logic

## Overview

The `Business Logic/Transformation Logic` column in the mapping Excel supports both **free-text** and **structured format**. Structured format reduces hallucination by providing explicit join definitions, pre-join filters, and value expressions that the parser can decompose into deterministic PySpark generation steps.

Both formats coexist — different rows in the same mapping can use either approach. The parser detects format per-cell and stores both raw text and parsed structure.

---

## Two Supported Approaches

The plugin supports **two approaches** for expressing transformation logic:

| Approach | Determinism | Use Case |
|----------|-------------|----------|
| **Structured Format** (Driver Table) | Deterministic — no ambiguity | Complex multi-table joins, explicit filter declarations, deduplication requirements |
| **Natural Language** (free-text) | Best-effort — advisory comments added | Simple joins, lookups, filters expressible as clear NL descriptions |

Both approaches work for single-source AND multi-source scenarios. Different rows in the same mapping can mix approaches.

---

## When to Use Structured Format (RECOMMENDED)

**Recommended** (produces deterministic output) when a target column's derivation involves:
- Multiple source tables joined together — explicit join definitions eliminate ambiguity
- Filtering/subsetting on ANY source table (driver or joined) — explicit filter conditions
- Pre-join filtering on specific tables (e.g., filter before join for performance)
- Complex conditions that would be ambiguous as free-text
- Deduplication requirements (e.g., "pick latest record")

> **Guideline 1 — Joins**: When multiple source tables are involved, structured format produces fully deterministic PySpark with no advisory comments. NL interpretation (Rule 11) also works but may default to LEFT JOIN when type is unspecified and emits advisory comments for developer review.

> **Guideline 2 — Filters**: Structured format `Driver Conditions` / `TableN Conditions` produce explicit `.filter()` calls. NL filter descriptions (e.g., "only active records") are also interpreted via Rule 11 but are best-effort. If no filter is expressed in either format, the entire source table is consumed.

---

## When to Use Natural Language (Supported)

**Natural language free-text** works for both single and multi-source when:
- Join logic is clearly expressible (e.g., "LEFT JOIN lookup_table ON product_code")
- Filter conditions use recognizable patterns (e.g., "Where status NOT IN ('CLO','RED')")
- The derivation is simple enough that NL is unambiguous

**Supported NL patterns for joins:**
- `"LEFT JOIN <table> ON <condition>"` — explicit join with type and condition
- `"INNER JOIN <table> ON <condition>"` — inner join
- `"Join with <table> on/where/using <key>"` — defaults to LEFT
- `"Get/Lookup <col> from <table> based on <key>"` — lookup pattern
- `"Match <table> on <key>"` — join on shared key

**Supported NL patterns for filters:**
- `"Filter/Where <col> = <value>"` — equality filter
- `"Filter/Where <col> NOT IN (<values>)"` — exclusion filter
- `"Only active records"` — active flag filter
- `"Latest/most recent record per <key>"` — ROW_NUMBER dedup
- `"Exclude <status values>"` — status exclusion

**Advisory comments**: When NL interpretation is used, generated code includes `# ADVISORY: Join/filter logic interpreted from natural language` for developer review. This is the key difference from structured format which produces clean output without advisories.

For simple mappings (direct column rename, single CAST, one-table expressions with no filtering), free-text remains the natural choice. For complex scenarios (multi-source joins, filters, lookups), free-text NL is also fully supported via Rule 11 — structured format is recommended for deterministic output but not required.

---

## Format Specification

### Detection Trigger

The parser detects structured format when a cell contains `Driver Table` (case-insensitive) followed by `:`.

### Syntax

```
Driver Table : <table_alias_or_name>
Driver Conditions: [<filter conditions on driver table, numbered>]
Join 1 Table: <table_alias_or_name>
Table1 Conditions: [<pre-join filter conditions on joined table, numbered>]
Join 1 Type: LEFT|INNER|RIGHT|FULL|CROSS
Join 1 Conditions: <join ON clause expression>
Join 2 Table: <table_alias_or_name>
Table2 Conditions: [<pre-join filter conditions on joined table, numbered>]
Join 2 Type: LEFT|INNER|RIGHT|FULL|CROSS
Join 2 Conditions: <join ON clause expression>
...
Value: <final expression for this target column>
```

### Field Definitions

| Field | Required | Description |
|-------|----------|-------------|
| `Driver Table` | YES | Primary/driving table for the join sequence. All joins attach to this. |
| `Driver Conditions` | NO | Filters applied to the driver table BEFORE any joins execute. Use when only a subset of driver table rows should be processed (e.g., active records only, specific business date, exclude certain status codes). Enclosed in `[]`. Same syntax as TableN Conditions. |
| `Join N Table` | YES (per join) | Table being joined. N is sequential (1, 2, 3...). |
| `TableN Conditions` | NO | Pre-join filters applied to the joined table BEFORE the join executes. Use when only a subset of the joined table should participate in the join. Enclosed in `[]`. Numbered items separated by newlines or semicolons. |
| `Join N Type` | YES (per join) | SQL join type: `LEFT`, `INNER`, `RIGHT`, `FULL`, `CROSS` |
| `Join N Conditions` | YES (per join) | Join ON clause (e.g., `driver.id = table1.id AND table1.active = 1`) |
| `Value` | YES | Final column derivation expression applied after all joins complete |

> **Rule — All Filters in This Column**: If only a subset of data needs to be read from ANY source table (driver or joined), those filter conditions MUST be specified here. The transform generator will NOT invent WHERE clauses. If no filter is specified, the entire table is read. This applies to:
> - Business date filters (e.g., `dw_bus_dt = {control_Date}`)
> - Status/active-record filters (e.g., `status NOT IN ('CLO','RED','WOF')`)
> - Deduplication (e.g., `pick latest record based on timestamp`)
> - Type/category filters (e.g., `limit_type = 'Base'`)

### Table Conditions Syntax

Pre-join conditions are enclosed in square brackets `[]`. Multiple conditions are numbered:

```
Table2 Conditions: [ 1. Filter limit_type='Base' and dw_bus_dt={control_Date} 2. pick latest record based on source_create_timestamp ]
```

Special condition patterns the parser recognizes:
- **Filter conditions**: `Filter <expression>` → generates `.filter()` on the table DataFrame
- **Dedup/latest record**: `pick latest record based on <column>` → generates `ROW_NUMBER() OVER (PARTITION BY <join_key> ORDER BY <column> DESC)` dedup
- **Top N**: `pick top N records by <column>` → generates window-based filter with `rn <= N`
- **Date filters**: `{control_Date}` or `{current_business_date}` → resolves to runtime `current_business_date` parameter

### Value Expression

The `Value:` field describes the final column derivation. It can be:
- A PySpark-like expression: `ROUND(limit_amount, 2)`, `COALESCE(a, b)`, `CONCAT(first, ' ', last)`
- Natural language: `Round off the limit_amount to 2 decimal points`
- Column reference: `table1.account_name` (direct select from a joined table)

The transform generator interprets both PySpark syntax and natural language descriptions.

---

## Example

### Mapping Excel Cell Content

```
Driver Table : Master_Tab
Driver Conditions: [ 1. Filter status NOT IN ('CLO','RED','WOF') 2. Filter dw_bus_dt={control_Date} ]
Join 1 Table: Table1
Table1 Conditions: [ 1. Filter active=1 ]
Join 1 Type: LEFT
Join 1 Conditions : Master_Tab.acctid=Table1.acctid
Join 2 Table : Table2
Table2 Conditions: [ 1. Filter limit_type='Base' and dw_bus_dt={control_Date} 2. pick latest record based on source_create_timestamp ]
Join 2 Type: LEFT
Join 2 Conditions : Master_Tab.acctid=Table2.acctid
Value: Round off the limit_amount to 2 decimal points
```

### Parser Output (`structured_transformation`)

```json
{
  "driver_table": "Master_Tab",
  "driver_conditions": [
    "Filter status NOT IN ('CLO','RED','WOF')",
    "Filter dw_bus_dt={control_Date}"
  ],
  "joins": [
    {
      "join_number": 1,
      "table": "Table1",
      "table_conditions": [
        "Filter active=1"
      ],
      "join_type": "LEFT",
      "join_conditions": "Master_Tab.acctid=Table1.acctid"
    },
    {
      "join_number": 2,
      "table": "Table2",
      "table_conditions": [
        "Filter limit_type='Base' and dw_bus_dt={control_Date}",
        "pick latest record based on source_create_timestamp"
      ],
      "join_type": "LEFT",
      "join_conditions": "Master_Tab.acctid=Table2.acctid"
    }
  ],
  "value_expression": "Round off the limit_amount to 2 decimal points"
}
```

### Generated PySpark

```python
# Driver table with conditions
master_tab_df = self.source_data['Master_Tab']
master_tab_filtered = master_tab_df.filter(
    ~F.col("status").isin("CLO", "RED", "WOF") &
    (F.col("dw_bus_dt") == current_business_date)
)

# Pre-join conditions for Table1
table1_df = self.source_data['Table1']
table1_filtered = table1_df.filter(F.col("active") == 1)

# Pre-join conditions for Table2
table2_df = self.source_data['Table2']
table2_filtered = table2_df.filter(
    (F.col("limit_type") == "Base") &
    (F.col("dw_bus_dt") == current_business_date)
)
# Dedup: pick latest record based on source_create_timestamp
w = Window.partitionBy("acctid").orderBy(F.col("source_create_timestamp").desc())
table2_deduped = table2_filtered.withColumn("_rn", F.row_number().over(w)).filter(
    F.col("_rn") == 1
).drop("_rn")

# Joins (sequential, on filtered driver)
joined_df = master_tab_filtered.join(
    table1_filtered,
    master_tab_filtered["acctid"] == table1_filtered["acctid"],
    "left"
).join(
    table2_deduped,
    master_tab_filtered["acctid"] == table2_deduped["acctid"],
    "left"
)

# Value: Round off the limit_amount to 2 decimal points
result_col = F.round(F.col("limit_amount"), 2).alias("target_column_name")
```

---

## Single-Source with Filters (No Joins)

When only one source table is involved but a **subset of data** needs to be read (filtered), the structured format is still used — simply omit the `Join N` lines:

### Syntax (Single Source, Filtered)

```
Driver Table: account_wm
Driver Conditions: [ 1. Filter status NOT IN ('CLO','RED','WOF') 2. Filter dw_bus_dt={control_Date} ]
Value: CAST(balance_amt AS DECIMAL(18,2))
```

### Parser Output

```json
{
  "driver_table": "account_wm",
  "driver_conditions": [
    "Filter status NOT IN ('CLO','RED','WOF')",
    "Filter dw_bus_dt={control_Date}"
  ],
  "joins": [],
  "value_expression": "CAST(balance_amt AS DECIMAL(18,2))"
}
```

### Generated PySpark

```python
account_wm_df = self.source_data['account_wm']
account_wm_filtered = account_wm_df.filter(
    ~F.col("status").isin("CLO", "RED", "WOF") &
    (F.col("dw_bus_dt") == current_business_date)
)
result_col = account_wm_filtered.select(
    F.col("balance_amt").cast("decimal(18,2)").alias("outstanding_balance")
)
```

> **When to use single-source structured format**: Use it whenever only a subset of source data should be read. If no filter is specified in the Business Logic/Transformation Logic column, the transform generator assumes the ENTIRE source table is consumed. If the data analyst/solution designer intends only active records, a specific date range, or specific categories to be processed, they MUST specify those filters here.

---

## Multiple Columns Sharing Joins

When multiple target columns reference the same driver table and joins (common in complex mappings), the transform generator **deduplicates** join operations:

1. Identify all columns with `structured_transformation` that share the same `driver_table`
2. Merge join definitions (same table + same conditions = one join operation)
3. Generate the join sequence ONCE
4. Apply each column's `value_expression` individually on the joined result

This prevents redundant DataFrame operations and maintains optimal execution plans.

---

## Interaction with Other Fields

| Field | Interaction |
|-------|-------------|
| `transformation_type = "Lookup"` | Signals join-based derivation; parser expects `structured_transformation` to be present for full definition |
| `default_value` | Applied AFTER `value_expression` via `F.coalesce(value_result, F.lit(default))` |
| `source_references[]` | Tables in `structured_transformation.joins[].table` should map to entries in `source_references` |
| `crypto_flags` | If value_expression involves a crypto column, crypto UDF wrapping happens at the PySpark generation layer |

---

## Fallback Behaviour

If the structured format is detected (contains `Driver Table:`) but parsing is incomplete:
- Missing `Value:` line → WARNING; parser falls back to free-text for this cell
- Missing `Join N Type:` → WARNING; defaults to `LEFT` join
- Unparseable `TableN Conditions:` → WARNING; conditions treated as empty
- Unrecognized table alias → WARNING logged; generation proceeds with alias as-is (source_references validation catches mismatches)

In all fallback cases, `transformation_logic` (raw text) is preserved alongside `structured_transformation = null`.
