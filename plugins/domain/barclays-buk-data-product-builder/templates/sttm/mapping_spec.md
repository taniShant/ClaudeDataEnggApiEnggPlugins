# STTM Output Excel Specification

This file defines the physical formatting for the STTM Excel output (e.g., `output/{prefix}_sttm.xlsx`). File names are dynamically prefixed per the output naming convention in `config/template_spec.yaml` → `output_naming`. It replaces the former `mapping_template.xlsx` binary template. Logical column definitions (allowed values, constraints, validation) remain in `config/template_spec.yaml`.

---

## Output Workbook Structure

The output Excel has exactly **2 sheets** regardless of scenario classification:

| Sheet Name | Tab Color | Purpose |
|---|---|---|
| Mapping | `#4472C4` (Blue) | All mapping rows for the classified scenario |
| Source Volumetrics | `#00B050` (Green) | One row per unique source table |

---

## Mapping Sheet — 16 Columns (A–P)

### Headers (Row 1, case-sensitive, exact text)

| Col | Header | Width |
|---|---|---|
| A | Target Database | 25 |
| B | Target Table | 22 |
| C | Target Column Name | 28 |
| D | Target Column Definition/Description | 40 |
| E | Target Column Datatype | 18 |
| F | Target Column Null Flag | 8 |
| G | Source Database | 22 |
| H | Source Table Name | 22 |
| I | Source Column Name | 28 |
| J | Business Logic/Transformation Logic | 55 |
| K | Additional Context | 50 |
| L | Target Table description | 50 |
| M | Transformation Type | 20 |
| N | Default Value | 15 |
| O | Target Table Type | 18 |
| P | Key Column | 12 |

### Header Formatting (Row 1)

- **Font**: Bold, size 11, default color (black)
- **Fill**: Solid, color `#D9E1F2` (light blue)
- **Alignment**: wrap_text=True, vertical=center

### Data Rows (Row 2+)

- **Font**: Regular, size 11, default color
- **Fill**: None
- **Alignment**: wrap_text=True, vertical=top

### Sheet Settings

- **Freeze panes**: `A2` (headers always visible)
- **Tab color**: `#4472C4`

---

## Column J — Business Logic/Transformation Logic Format

Column J contains the transformation logic for each target column. The format depends on complexity.

### Simple Columns (single source, no join)

Use inline SQL expressions directly:

| Pattern | Example |
|---|---|
| Direct mapping | `Direct mapping` |
| Type cast | `CAST(balance_amt AS DECIMAL(18,2))` |
| Date conversion | `CAST(TO_DATE(CAST(open_date AS STRING), 'yyyyMMdd') AS DATE)` |
| Conditional | `CASE WHEN status_code IN ('ACT','OPN') THEN 'ACTIVE' WHEN status_code = 'CLS' THEN 'CLOSED' ELSE 'OTHER' END` |
| Coalesce | `COALESCE(method_code, 'UNKNOWN')` |
| Crypto (unprotect) | `cloud_api_udf_UK_TOK_SORTCOD_L0R0_NUM_DE_unprotect(sort_code_encrypted)` |
| Crypto (protect) | `cloud_api_udf_UK_TOK_NI_NUM_L0R0_ID_DE_protect(ni_number_clear)` |
| Crypto (both) | `cloud_api_udf_UK_TOK_ACCT_L2R1_NUM_DE_protect(cloud_api_udf_UK_TOK_ACCT_L0R0_NUM_DE_unprotect(acct_num_encrypted))` |
| Timestamp audit | `current_timestamp()` |
| Partition direct | `Direct mapping -- partition column` |

Inline comments (`-- reason`) are permitted for documentation.

### Multi-Table Joins (Structured Compact Format — REQUIRED)

When a target column derives from a join across multiple source tables, use the **structured compact format with table aliases**. This format enables deterministic PySpark code generation.

```
Driver Table: <full_table_name> (<alias>)
Driver Conditions: [Filter <alias>.<col> <operator> <value>]
Join N: <TYPE> JOIN <full_table_name> (<alias>) ON <left_alias>.<col> = <right_alias>.<col> [Filter <alias>.<col> = '<value>']
Value: <alias>.<column_expression>
```

**Field definitions:**

| Field | Required | Description |
|---|---|---|
| `Driver Table` | Yes | Primary/driving table with alias in parentheses. Defines the grain. |
| `Driver Conditions` | No | Filter on driver table using alias. Omit line entirely if no filters. |
| `Join N` | Yes (per join) | One compact line per join (N = 1, 2, 3…) combining TYPE, table (alias), ON condition, and optional `[Filter]` suffix. |
| `Value` | Yes | SQL expression for this target column using aliases. May include CAST, CASE WHEN, functions. |

### Alias Rules

- Define alias in parentheses on **first mention** of each table (Driver Table line or Join N line)
- Alias = short lowercase abbreviation (first letter(s) of each word): `mortgage_account` → `ma`, `branch_lookup` → `bl`, `product_type` → `pt`
- **Aliases MUST be unique** — disambiguate collisions by appending extra characters (e.g., `complaint_case` → `cc`, `customer_consolidated` → `cco`, `case_category` → `cca`)
- After introduction, use alias **EVERYWHERE** (Driver Conditions, Join ON conditions, Filter suffixes, Value)

### Format Rules

- Each section separated by newline (`\n`) in JSON output; renders multi-line in Excel (`wrap_text=True`)
- One line per join — combines TYPE, table, ON condition, and optional table filter suffix
- Do NOT use `/` as separator between sections
- Omit `Driver Conditions` line entirely if no driver filters exist
- Omit `[Filter ...]` suffix on a Join line if that joined table has no pre-filter
- Natural language (e.g., "LEFT JOIN lookup ON id") is **FORBIDDEN** for multi-table logic

### Examples

**2-table LEFT JOIN (CDP Multi-Source):**
```
Driver Table: mortgage_account (ma)
Join 1: LEFT JOIN complaint_case (cc) ON ma.customer_id = cc.customer_id
Value: cc.complaint_case_id
```

**Value with CAST from driver table:**
```
Driver Table: mortgage_account (ma)
Join 1: LEFT JOIN complaint_case (cc) ON ma.customer_id = cc.customer_id
Value: CAST(ma.outstanding_balance AS DECIMAL(18,2))
```

**Lookup with CASE WHEN in Value:**
```
Driver Table: customer_consolidated (cc)
Join 1: LEFT JOIN segment_lookup (sl) ON cc.segment_code = sl.segment_code
Value: CASE WHEN cc.preferred_channel = 'D' THEN 'DIGITAL' WHEN cc.preferred_channel = 'B' THEN 'BRANCH' WHEN cc.preferred_channel = 'M' THEN 'MOBILE' ELSE NULL END
```

**Multiple joins with driver filter and table filter:**
```
Driver Table: mortgage_account (ma)
Driver Conditions: [Filter ma.active = '1']
Join 1: LEFT JOIN branch_lookup (bl) ON ma.branch_code = bl.branch_code
Join 2: INNER JOIN product_type (pt) ON ma.product_code = pt.product_type_code [Filter pt.product_category = 'MORTGAGE']
Value: bl.branch_name
```

### SCD2 Audit Columns (Non-Transactional targets only)

| Column | Format |
|---|---|
| `eff_start_date` | **Simple**: `derived from <source_column_name>` (e.g., `derived from row_lst_mod_dte`). **Full** (complex/multi-source): describe temporal stitching scenario — (1) How many sources? (2) Per source: has eff_start/eff_end? If not, which date column? (3) ALL or SUBSET columns mapped? (4) Join key between sources? |
| `eff_end_date` | `Derived from temporal stitching scenario above` |
| `active` | `CASE WHEN eff_end_date = DATE'3499-12-31' THEN '1' ELSE '0' END` |
| `dw_lod_tmp` | `current_timestamp()` |
| `dw_upd_lod_tmp` | `current_timestamp()` |

### Critical Constraints

1. **Alias on BOTH sides** — Join ON conditions MUST use alias on both sides (e.g., `ma.customer_id = cc.customer_id`). Do NOT use bare column names.
2. **Exact literal values** — Filter/literal values MUST be exactly the intended value (e.g., `nps_question_indicator='Y'` means exactly `Y`, not `V` or `Yes` or `1`).
3. **Natural language FORBIDDEN** — Free-text descriptions for multi-table logic are not permitted. They produce best-effort output with advisory comments and risk column/value inference errors.

**UNION example:**
```
Union Branch 1: SELECT account_id, balance FROM current_accounts (ca)
Union Branch 2: SELECT account_id, balance FROM historical_accounts (ha)
Union Type: UNION ALL
Value: account_id
```

**View resolution example (in Transformation Lineage block):**
```
Step 1 (Hist110): CREATE VIEW Prior_Cycle_v
  FROM s_trmfdb.ctcp (ctcp)
  [QUALIFY CSUM(1, NBR_CARDH_ACCT, TIME_LAST_UPD DESC) = 1]
  Columns: Account_Number = ctcp.NBR_CARDH_ACCT [New], Credit_Limit = ctcp.AMT_CRED_LMT [New]
  Grain: Account_Number
  → Prior_Cycle_v
  Resolves to: s_trmfdb.ctcp
```

**Self-join example (month-over-month):**
```
Driver Table: account_monthly_snapshot (acc_curr)
Join 1: INNER JOIN account_monthly_snapshot (acc_prev) ON acc_curr.account_id = acc_prev.account_id AND acc_curr.period_date = add_months(acc_prev.period_date, 1)
Value: acc_curr.balance - acc_prev.balance
```

**Non-equi join example (temporal range):**
```
Driver Table: transaction (t)
Join 1: LEFT JOIN rate_schedule (r) ON t.transaction_date BETWEEN r.effective_start AND r.effective_end
Value: t.amount * r.rate
```

**MERGE example (SCD2 close+insert):**
```
MERGE Source Table: staging_account (src)
MERGE Target Table: fdp_uk_account_db.account (tgt)
MERGE Match Key: tgt.account_id = src.account_id
MERGE Matched Action: src.balance (close existing, insert new with eff_start = src.mod_date)
MERGE Not Matched Action: src.balance (new record, eff_start = src.mod_date, active = '1')
```

---

## Source Volumetrics Sheet — 10 Columns (A–J)

### Headers (Row 1, case-sensitive, exact text)

| Col | Header | Width |
|---|---|---|
| A | Source Database | 25 |
| B | Source Table | 28 |
| C | Estimated Rows | 18 |
| D | Estimated Size (GB) | 22 |
| E | Daily Increment Rows | 22 |
| F | Daily Increment Size (GB) | 26 |
| G | Primary Key | 32 |
| H | Partition Key | 20 |
| I | Table Type | 18 |
| J | Broadcast Hint | 16 |

### Header Formatting (Row 1)

- **Font**: Bold, size 11, default color (black)
- **Fill**: Solid, color `#D9E1F2` (light blue)
- **Alignment**: wrap_text=True, vertical=center

### Data Rows (Row 2+)

- **Font**: Regular, size 11, default color
- **Fill**: None
- **Alignment**: wrap_text=True, vertical=top

### Sheet Settings

- **Freeze panes**: `A2`
- **Tab color**: `#00B050`

---

## JSON-to-Column Mapping

### Mapping Sheet — COL_MAP (ordered A–P)

```
target_database, target_table, target_column_name,
target_column_description, target_column_datatype, target_column_null_flag,
source_database, source_table_name, source_column_name,
business_logic, additional_context, target_table_description,
transformation_type, default_value, target_table_type, key_column
```

### Source Volumetrics — VOL_COL_MAP (ordered A–J)

```
source_database, source_table, estimated_rows, estimated_size_gb,
daily_increment_rows, daily_increment_size_gb, primary_key,
partition_key, table_type, broadcast_hint
```

---

## Row Structure

| Row | Content |
|---|---|
| 1 | Headers (bold, filled) |
| 2+ | Generated data (no instructions row in output) |

**Note**: The former template file had an instructions/advisory row at Row 2 which was deleted during export. The from-scratch generation approach simply never creates it — data starts directly at Row 2.

---

## Generation Approach

Excel output is built from scratch using `openpyxl.Workbook()`:
1. Create workbook with "Mapping" sheet (active) + "Source Volumetrics" sheet
2. Write headers to Row 1 with specified formatting
3. Set column widths per tables above
4. Set freeze panes and tab colors
5. Populate data rows from the STTM JSON (e.g., `output/{prefix}_sttm.json`) starting at Row 2
6. Save as the STTM Excel (e.g., `output/{prefix}_sttm.xlsx`)

No binary template file is needed. All formatting constants are defined in this specification.
