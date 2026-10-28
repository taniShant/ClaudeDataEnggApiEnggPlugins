---
description: "Comprehensive pattern definitions (24+) for the STTM Generator — covers Direct Mapping, Derived, Lookup, Type Cast, Aggregation, and conditional transformation detection with output formats."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-28
---

# Transformation Detection Patterns

This document defines all transformation patterns the STTM Generator must detect and generate. Each pattern includes detection rules, output format, and metadata assignment.

---

## 1. Direct Mapping

**Detection:** Single column reference with no function wrapper, no expression, no modification.

**Template Output:**
- Business Logic: `Direct mapping`
- Transformation Type: `Direct`
- Source Column: The single source column name
- Additional Context: Role-based (e.g., "Primary key", "Foreign key", "Business attribute")

**Example:**
- Source: `account_id` → Target: `mortgage_account_id`
- Business Logic: "Direct mapping"

### Temporal Self-Lookup Exception (MANDATORY)

When a column's value comes from the **same table but a different temporal period** (e.g., "previous billing period's `Date_Next_Payment_Due` becomes current period's `Date_Payment_Due`"), this is NOT a Direct mapping — it is a **Derived** transformation.

**Detection:** The source data involves:
- A self-join on a period/date column (e.g., `billing_period = prior_billing_period`)
- A LAG/LEAD window function with period-based ordering
- A lookup to the same table filtered to a prior temporal range
- The phrase "previous period" or "prior cycle" in design documents

**Classification:**
- Transformation Type: `Derived` (NOT `Direct`)
- Even though a single source column is referenced, the complexity lies in the temporal JOIN condition — the value comes from a different row, not the current row
- Source Column: the column being looked up (e.g., `date_next_payment_due`)
- Business Logic: must document the temporal join or window function, not "Direct mapping"

**Example:**
- Target: `date_payment_due` — "Previous period's Date_Next_Payment_Due"
- WRONG: Transformation Type = `Direct`, Business Logic = "Direct mapping"
- RIGHT: Transformation Type = `Derived`, Business Logic =
  ```
  Driver Table: t_bcard_restdb.bc_history (curr)
  Join 1: LEFT JOIN t_bcard_restdb.bc_history (prev) ON curr.account_number = prev.account_number AND prev.billing_period = curr.prior_billing_period
  Value: prev.date_next_payment_due
  ```

**Rule:** Any cross-period source lookup — even to a single column in the same table — is `Derived`. The temporal join IS the transformation.

---

## 2. CAST / Type Conversion

**Detection:** CAST(column AS type) expression wrapping a single source column.

**Template Output:**
- Business Logic: Full CAST expression (e.g., `CAST(balance_amt AS DECIMAL(18,2))`)
- Transformation Type: `Direct - Type Cast`
- Source Column: The inner column being cast
- Additional Context: Describe why cast is needed (e.g., "Source stored as FLOAT; precision cast required")

**Example:**
- Business Logic: `CAST(balance_amt AS DECIMAL(18,2))`
- Source Column: `balance_amt`
- Transformation Type: `Direct - Type Cast`

---

## 3. Date Conversion (YYYYMMDD Integer → DATE)

**Detection:** Integer column + TO_DATE + date format string. Source column is numeric but target is date type.

**Template Output:**
- Business Logic: `CAST(TO_DATE(CAST({{source_column}} AS STRING), 'yyyyMMdd') AS DATE)`
- Transformation Type: `Derived`
- Additional Context: "YYYYMMDD integer in source; cast required"

**Example:**
- Source column: `open_date` (int)
- Target datatype: `date`
- Business Logic: `CAST(TO_DATE(CAST(open_date AS STRING), 'yyyyMMdd') AS DATE)`

---

## 4. CASE WHEN (Conditional Logic)

**Detection:** CASE/WHEN/THEN/ELSE/END keywords in expression.

**Template Output:**
- Business Logic: Full CASE expression
- Transformation Type: `Derived`
- Additional Context: "Normalize status codes" or describe the business rule
- Source Column: The column being tested in WHEN clause

**Example:**
- Business Logic: `CASE WHEN status_code IN ('ACT','OPN') THEN 'ACTIVE' WHEN status_code = 'CLS' THEN 'CLOSED' ELSE 'UNKNOWN' END`
- Source Column: `status_code`
- Additional Context: "Normalize status codes; business rule required for code meanings"

**Nested CASE Example:**
```sql
CASE 
  WHEN status = 'A' THEN 
    CASE WHEN sub_status = '1' THEN 'Active-Primary' 
         WHEN sub_status = '2' THEN 'Active-Secondary' 
         ELSE 'Active-Other' END
  WHEN status = 'I' THEN 'Inactive'
  ELSE 'Unknown'
END
```
Note: all source columns referenced across branches must be listed. If branches reference different source tables, all tables must be listed.

---

## 4b. Fan-in CASE/COALESCE (Multiple Sources to One Target)

**Detection:** CASE WHEN or COALESCE where different branches reference DIFFERENT source columns (potentially from different tables). Distinct from simple CASE which tests ONE source column's values — fan-in pulls VALUES from DIFFERENT source columns per branch.

**Template Output:**
- Source Column: ALL contributing source columns listed comma-separated
- Business Logic: Full CASE/COALESCE expression with all branches
- Transformation Type: `Derived`
- If columns come from different tables: triggers multi-table structured format (Pattern 14)
- Additional Context: "Fan-in — multiple source columns contribute to single target column. Primary source: {first_branch_source}"

**Example (multi-table fan-in):**
```sql
COALESCE(a.primary_email, b.secondary_email, 'unknown@example.com')
```
- Source Column: `a.primary_email, b.secondary_email`
- Business Logic (structured format):
  ```
  Driver Table: db.contacts (a)
  Join 1: LEFT JOIN db.backup_contacts (b) ON a.customer_id = b.customer_id
  Value: COALESCE(a.primary_email, b.secondary_email, 'unknown@example.com')
  ```
- Default Value: `'unknown@example.com'`
- Transformation Type: `Derived`

**Example (single-table fan-in):**
```sql
CASE WHEN preferred_flag = 'Y' THEN preferred_amount ELSE standard_amount END
```
- Source Column: `preferred_amount, standard_amount`
- Business Logic: `CASE WHEN preferred_flag = 'Y' THEN preferred_amount ELSE standard_amount END`
- Transformation Type: `Derived`

---

## 5. COALESCE (NULL Fallback)

**Detection:** COALESCE function call in expression.

**Template Output:**
- Business Logic: `COALESCE({{source_column}}, '{{fallback_value}}')`
- Transformation Type: `Derived`
- Default Value: The fallback value (e.g., 'UNKNOWN', -99)
- Additional Context: "NULL for some legacy records"

**IMPORTANT:** When COALESCE is detected, the Default Value field (column N) MUST be populated with the fallback value.

**Example:**
- Business Logic: `COALESCE(method_code, 'UNKNOWN')`
- Default Value: `'UNKNOWN'`

**Variants:**
- `NVL(col, default)` → equivalent to `COALESCE(col, default)`
- `NVL2(col, not_null_val, null_val)` → `CASE WHEN col IS NOT NULL THEN not_null_val ELSE null_val END`
- `IFNULL(col, default)` → equivalent to `COALESCE(col, default)`
- `IIF(cond, true_val, false_val)` → `CASE WHEN cond THEN true_val ELSE false_val END`
- **Multi-table COALESCE:** when COALESCE draws from different tables (e.g., `COALESCE(a.email, b.email)`), ALL source columns must be listed and multi-table structured format triggered

---

## 6. Aggregation (SUM/COUNT/AVG/MAX/MIN/Window)

**Detection:** Aggregate functions (SUM, COUNT, AVG, MAX, MIN) or window functions (OVER, PARTITION BY, ROW_NUMBER, RANK).

**Template Output:**
- Business Logic: Full aggregate expression including PARTITION BY if window function
- Transformation Type: `Derived`
- Additional Context: "Aggregate from FDP" or describe the metric

**Example:**
- Business Logic: `SUM(outstanding_balance) OVER (PARTITION BY customer_id)`
- Transformation Type: `Derived`
- Additional Context: "Aggregate from FDP"

**String Aggregation Variant:**
- `LISTAGG(col, delimiter)` / `STRING_AGG(col, delimiter)` / `GROUP_CONCAT(col)` / `XMLAGG(col)`
- These aggregate multiple row values into a single concatenated string
- Source column: the aggregated column
- Transformation Type: `Derived`
- Signal: `["aggregate", "string_agg"]`

---

## 7. System-Generated — current_timestamp()

**Detection:** Column name matches audit column config (dw_lod_tmp, dw_upd_lod_tmp) OR column is explicitly marked as system-generated.

**Template Output:**
- Source Database: `(system)`
- Source Table: `(system)`
- Source Column: `(system)`
- Business Logic: `current_timestamp()`
- Transformation Type: `Derived`
- Additional Context: "System audit column" or "System audit column; Excluded from CDC hash"
- Key Column: `N`
- Null Flag: `N`

**Variants:**
- `dw_lod_tmp`: Additional Context = "System audit column; {{Day0/Day1}} = {{load description}}"
- `dw_upd_lod_tmp`: Additional Context = "System audit column; Excluded from CDC hash"

---

## 7b. System Functions (Non-Timestamp)

**Detection:** SQL expression is entirely a system function with no source column dependency (beyond window framing columns).

**Template Output (pure system functions — CURRENT_DATE, UUID, etc.):**
- Source Database: `(system)`
- Source Table: `(system)`
- Source Column: `(system)`
- Business Logic: The function expression (e.g., `CURRENT_DATE`, `UUID()`)
- Transformation Type: `Derived`
- Additional Context: "System-generated value — no source column dependency"

**Template Output (positional functions — ROW_NUMBER, RANK with source columns in OVER):**
- Source Database: Real database of PARTITION BY / ORDER BY columns
- Source Table: Real table of referenced columns
- Source Column: `(derived)` (the value is a positional computation, not a source column value)
- Business Logic: Full window function expression
- Transformation Type: `Derived`
- Additional Context: "Positional/ranking function — value derived from row position"

**Variants:**

| Function | Source Attribution | Notes |
|----------|-------------------|-------|
| `CURRENT_DATE` | (system) | Date only |
| `CURRENT_TIMESTAMP` / `NOW()` | (system) | Covered by Pattern 7 (audit columns) |
| `GETDATE()` | (system) | Teradata equivalent |
| `UUID()` / `MONOTONICALLY_INCREASING_ID()` | (system) | Spark identifier generation |
| `ROW_NUMBER() OVER (PARTITION BY x ORDER BY y)` | source table of x, y | Positional — source from frame columns |
| `RANK() OVER (...)` / `DENSE_RANK() OVER (...)` | source table of frame columns | Ranking — source from frame columns |
| `CURRENT_USER` / `SESSION_USER` | (system) | Session context |

**Validation**: SC18 checks that pure system functions use (system) or (derived) source markers.

---

## 8. Active Flag (SCD2)

**Detection:** Column named "active" AND table_type = scd2.

**Template Output:**
- Source Database: `(derived)`
- Source Table: `(derived)`
- Source Column: `(derived)`
- Business Logic: `CASE WHEN eff_end_date = CAST('{{high_end_date}}' AS DATE) THEN '1' ELSE '0' END`
- Transformation Type: `Derived`
- Additional Context: "System-managed; partition column"
- Null Flag: `N`

**Default high_end_date:** `3499-12-31`

---

## 9. Effective End Date (SCD2)

**Detection:** Column named "eff_end_date" AND table_type = scd2.

**Template Output (INSERT — new/current record):**
- Source Database: `(system)`
- Source Table: `(derived)`
- Source Column: `(derived)`
- Business Logic: `CAST('{{high_end_date}}' AS DATE)`
- Transformation Type: `Derived`
- Default Value: `{{high_end_date}}`
- Additional Context: "High-end date for open records; closed records use {{close_date_formula}} (default: new_eff_start_date)"
- Null Flag: `N`

**Close Logic (MERGE — previous active record):**
Determined by `configuration.scd.close_date_formula` (captured via interview Q4.5):
- `new_eff_start_date` (default) — previous version closed on the day the new version starts
- `new_eff_start_date - 1 day` — gap-free at day granularity
- `batch_date - 1` — close on the day before processing
- Custom expression — as specified by user

---

## 10. Effective Start Date (SCD2)

**Detection:** Column named "eff_start_date" AND table_type = scd2.

**CRITICAL:** eff_start_date MUST have a real source column (the modification date from source). It is NOT system-generated. If the source mod column is unknown → guided mode (BLOCKER).

**Template Output:**
- Source Database: Real source database
- Source Table: Real source table
- Source Column: The modification date column (e.g., `row_lst_mod_dte`)
- Business Logic: `CAST(TO_DATE(CAST({{source_mod_column}} AS STRING), 'yyyyMMdd') AS DATE)`
- Transformation Type: `Derived`
- Additional Context: "SCD2 audit column; always NOT NULL"
- Null Flag: `N`

---

## 11–13. Crypto Patterns (Detokenize / Tokenize / Both)

**CONDITIONAL EXTENSION** — When `classification.crypto_aspect != "None"`: load `${CLAUDE_PLUGIN_ROOT}/agents/refs/sttm-pattern-ext-crypto.md` for Detokenize (unprotect), Tokenize (protect), and Both (nested protect/unprotect) pattern detection rules, template outputs, and examples. DE names must NEVER be inferred.

---

## 14. Multi-Table Structured Format (MANDATORY for joins)

> **Canonical format reference:** See `${CLAUDE_PLUGIN_ROOT}/docs/structured-transformation-logic.md` for the full multi-table structured format specification.

**Detection:** Multiple tables in FROM/JOIN; source table count > 1; any lookup table referenced.

**MANDATORY:** Free-text natural language is NOT PERMITTED for multi-table transformations.

**Template Output (Structured Compact Newline-Separated Format with Aliases):**
```
Driver Table: <full_table_name> (<alias>)
Driver Conditions: [Filter <alias>.<col> <operator> <value>]
Join N: <TYPE> JOIN <full_table_name> (<alias>) ON <left_alias>.<col> = <right_alias>.<col> [Filter <alias>.<col> = '<value>']
Value: <alias>.<column_expression>
```

**Cell Format:** Each section MUST be separated by a newline character (`\n`) in the JSON value. Do NOT use "/" as a section separator. The Excel cell has `wrap_text=True`, so each section renders on its own line for human readability.

**Alias Rules:**
- Define alias in parentheses on FIRST mention of each table (Driver Table or Join N line)
- Alias = short lowercase abbreviation (first letter(s) of each word): `mortgage_account` → `ma`, `branch_lookup` → `bl`
- **Aliases MUST be unique** — disambiguate collisions by appending extra characters (e.g., `cc`, `cco`, `cca`)
- After introduction, use alias EVERYWHERE (conditions, joins, filters, value)
- Join ON conditions MUST have alias on BOTH sides: `ma.col = bl.col`
- Filter conditions MUST use alias of the concerned table: `[Filter bl.status = 'ACTIVE']`

**Format Rules:**
- "Driver Table" = the table that defines the grain (one row per PK of this table)
- "Driver Conditions" = optional WHERE filters on driver table — omit line entirely if no filters
- "Join N" = one compact line per join (incrementing 1, 2, 3...) combining type, table, ON condition, and optional filter
- "Value" = SQL expression for THIS target column (can contain CAST, CASE WHEN, functions, using aliases)

**Applicability:**
- ALL multi-table transformations (CDP Multi-Source, BDP Aggregated with lookups)
- Single-table with lookup joins (even if lookup is small/broadcast)
- NOT used for: single-table direct mappings, system columns, derived columns with no join

**Why mandatory:** Enables deterministic PySpark code generation downstream. Eliminates ambiguity. Newline separation improves readability in Excel.

**Example (2 tables — CDP Multi-Source):**
```
Driver Table: mortgage_account (ma)
Join 1: LEFT JOIN complaint_case (cc) ON ma.customer_id = cc.customer_id
Value: CAST(ma.outstanding_balance AS DECIMAL(18,2))
```

**Example (1 table + lookup with filter on driver):**
```
Driver Table: customer_consolidated (cc)
Driver Conditions: [Filter cc.status = 'ACTIVE']
Join 1: LEFT JOIN segment_lookup (sl) ON cc.segment_code = sl.segment_code
Value: sl.segment_description
```

**Example (3 tables — BDP Aggregated with lookup + table filter):**
```
Driver Table: mortgage_account (ma)
Driver Conditions: [Filter ma.active = '1']
Join 1: LEFT JOIN branch_lookup (bl) ON ma.branch_code = bl.branch_code
Join 2: INNER JOIN product_type (pt) ON ma.product_code = pt.product_type_code [Filter pt.product_category = 'MORTGAGE']
Value: bl.branch_name
```

**Example (alias collision — tables with same initials):**
```
Driver Table: complaint_case (cc)
Join 1: LEFT JOIN customer_consolidated (cco) ON cc.customer_id = cco.customer_id
Join 2: LEFT JOIN case_category (cca) ON cc.category_code = cca.category_code
Value: cco.customer_name
```

**Transformation Type:** `Lookup` (if join to reference table) or `Derived` (if join + complex expression)
**Additional Context:** "LEFT JOIN; NULL if customer has no mortgage" or "Lookup join; can be NULL if code not mapped"

---

## 15. UPPER / TRIM / String Normalization

**Detection:** UPPER(), TRIM(), LOWER() functions in expression.

**Template Output:**
- Business Logic: `UPPER({{source_column}})` or `UPPER(TRIM({{source_column}}))`
- Transformation Type: `Derived`
- Additional Context: "Normalize to uppercase" or "Remove whitespace and normalize"

---

## 16. Division / Arithmetic

**Detection:** Mathematical operators (+, -, *, /) in expression.

**Template Output:**
- Business Logic: Full arithmetic expression (e.g., `CAST(rate_pct AS DECIMAL(8,6)) / 100`)
- Transformation Type: `Derived`
- Additional Context: Describe the business reason (e.g., "Stored as whole number percentage (e.g. 75 = 0.75)")

---

## 17. Partition Column (from source)

**Detection:** Column appears in partition_columns config AND is sourced from upstream (not derived).

**Template Output:**
- Business Logic: `Direct mapping` (if direct from source partition) or the actual expression
- Transformation Type: `Direct` or appropriate type
- Additional Context: "Partition column; business date from source"

---

## 18. Teradata-Specific Patterns

**CONDITIONAL EXTENSION** — When Teradata dialect is detected: load `${CLAUDE_PLUGIN_ROOT}/agents/refs/sttm-pattern-ext-teradata.md` for all Teradata-specific pattern detection rules (QUALIFY, ZEROIFNULL/NULLIFZERO, OREPLACE/OTRANSLATE, STRTOK, DECODE, NORMALIZE ON, EXPAND ON, HASHROW, PERIOD operations) with template outputs and examples.

---

## 20. CONCAT / String Concatenation

**Detection:** CONCAT() function, `||` operator, or `+` operator in string context.

**Template Output:**
- Source Column: ALL contributing source columns listed comma-separated
- Business Logic: Preserve full CONCAT expression
- Transformation Type: `Derived`
- If columns come from different tables: triggers multi-table structured format

**Example:**
- `CONCAT(a.first_name, ' ', a.last_name)` or `a.first_name || ' ' || b.last_name`

---

## 21. LAG / LEAD Window Functions

**Detection:** LAG(col, N) or LEAD(col, N) with OVER clause.

**Template Output:**
- Source Column: The column being lagged/led
- Business Logic: Full LAG/LEAD expression including PARTITION BY and ORDER BY
- Transformation Type: `Derived`

**Example:**
- `LAG(balance, 1, 0) OVER (PARTITION BY account_id ORDER BY period_date)`

**Note:** Always requires real source table (apply CP2 penalty if `(derived)` would be used).

---

## 22. PIVOT / UNPIVOT

**Detection:** PIVOT(...FOR...IN...) or UNPIVOT clause.

**Template Output:**
- **PIVOT:** source_column = value column; each pivot output column has the pivot key value in its expression
- **UNPIVOT:** source_column = comma-separated list of all unpivoted source columns
- Transformation Type: `Derived`
- Route to guided mode for confirmation of pivot semantics

**Example:**
- `PIVOT(SUM(amount) FOR quarter IN ('Q1','Q2','Q3','Q4'))`

---

## 23. UNION Format (for row-generator consumption)

**Detection:** sttm-sql-lineage-agent detects UNION or UNION ALL in SQL and populates `union_metadata`.

**Template Output — UNION Structured Format (MANDATORY):**

Business Logic MUST use the following format for every non-audit column:

```
Union Branch 1: SELECT <columns> FROM <table> (<alias>) [joins if any] [Filter <condition>]
Union Branch 2: SELECT <columns> FROM <table> (<alias>) [joins if any] [Filter <condition>]
Union Type: UNION ALL | UNION
Value: <alias>.<expression>
```

**Rules:**
- One `Union Branch N:` line per branch (N = 1, 2, 3, ...) — even when branch_count > 2
- Each branch is self-contained: its own SELECT columns, FROM table (alias), JOINs, and per-branch filters
- `Union Type:` specifies UNION (dedup) or UNION ALL (preserve duplicates)
- `Value:` shows the column expression for THIS target column
- Source Column (I): ALL columns from ALL branches, semicolon-separated
- Source Table (H): ALL tables from ALL branches, semicolon-separated
- Transformation Type: `Derived`
- NEVER collapse branches into narrative ("N-way union with <flag>") — this is FORBIDDEN

**Example (2-branch UNION ALL — simple):**
```
Union Branch 1: SELECT account_id, balance AS account_balance FROM fdp_uk_current_account_db.current_account (ca)
Union Branch 2: SELECT account_id, balance AS account_balance FROM fdp_uk_savings_account_db.savings_account (sa)
Union Type: UNION ALL
Value: account_id
```

**Example (4-branch UNION ALL with per-branch filters — complex):**
```
Union Branch 1: SELECT account_number, balance, 'N' AS purge_flag FROM bc_history_new_month_1stpart (p1) [Filter p1.purge_flag = 'N']
Union Branch 2: SELECT account_number, balance, 'Y' AS purge_flag FROM bc_hist_purge_dummy (pd)
Union Branch 3: SELECT account_number, balance, purge_flag FROM bc_history_temp (ht) [Filter ht.billing_period < :CUR_BILLING_PERIOD]
Union Branch 4: SELECT account_number, balance, purge_flag FROM bc_hist_dup_one_row (dup)
Union Type: UNION ALL
Value: account_number
```

**Example (hardcoded discriminator column):**
```
Union Branch 1: SELECT 'CURRENT' AS source_system FROM fdp_uk_current_account_db.current_account (ca)
Union Branch 2: SELECT 'SAVINGS' AS source_system FROM fdp_uk_savings_account_db.savings_account (sa)
Union Type: UNION ALL
Value: Hardcoded per branch ('CURRENT' or 'SAVINGS')
```

---

## 24 & 26. Multi-Step ETL Chain + View Resolution

**CONDITIONAL EXTENSION** — When `intermediate_steps` is non-empty: load `${CLAUDE_PLUGIN_ROOT}/agents/refs/sttm-pattern-ext-multi-step.md` for Multi-Step ETL Chain (Pattern 24) and View Resolution (Pattern 26) detection rules, step rendering rules, post-chain blocks, worked examples including the rskm_fields variant-merge pattern, and CREATE_VIEW step format.

---

## 25. Grain Statement (Auto-Derived for Target Table Description)

**Detection:** The sttm-row-generator-agent checks whether Column L (Target Table Description) already contains "Grain:" (case-insensitive). If absent, it derives the grain from pipeline evidence and appends it to the description.

**Derivation priority:** P1 (grain_keys from final intermediate step) → P2 (grain_impact "key" columns) → P3 (GROUP BY columns) → P4 (Key Column = Y) → P5 (interview Q3.7). See sttm-row-generator-agent §Grain Derivation for full algorithm.

**Derivation Examples by Table Type:**

| Scenario | Evidence Source | Derived Grain Suffix |
|----------|----------------|---------------------|
| FDP Transactional (single PK) | Key Column = Y on `payment_id` | ` Grain: payment_id.` |
| FDP Non-Transactional SCD2 | Key Column = Y on `mortgage_account_id` + SCD2 classification | ` Grain: mortgage_account_id per effective period.` |
| CDP Multi-Source SCD2 | grain_impact "key" on `customer_id` + SCD2 classification | ` Grain: customer_id per effective period.` |
| BDP Aggregated (composite key) | GROUP BY = `[customer_id, segment_code]` | ` Grain: customer_id + segment_code.` |
| BDP Aggregated with time | GROUP BY = `[branch_id, reporting_date]` | ` Grain: branch_id per reporting_date.` |
| Multi-step ETL | Final step grain_keys = `[account_number]` | ` Grain: account_number.` |

**WRONG (grain in Additional Context):**
```
additional_context: "load_type:BAU|grain:customer_id"
```
This violates the excluded_keys rule. grain is PROHIBITED in Additional Context.

**CORRECT (grain in Target Table Description):**
```
target_table_description: "Business Data Product - customer metrics. Grain: customer_id + segment_code."
```

**Time Dimension Detection (non-SCD2 only):**
When a grain column has datatype `date` or `timestamp` and its name suggests a time dimension (contains `date`, `dt`, `period`, `month`, `year`, `day`, `time`, `timestamp`), use `per <column>` format:
- `[branch_id, reporting_date]` → `Grain: branch_id per reporting_date.`
- `[customer_id, segment_code]` → `Grain: customer_id + segment_code.` (neither is a date)

**Confidence threshold:** 0.7 — if grain cannot be determined at or above this level, it is NOT appended. Instead, the field is routed to guided mode (Q11).

---

## Pattern Priority (When Multiple Patterns Match)

1. Crypto patterns take highest priority (if protect/unprotect detected)
2. Multi-table structured format (if multiple tables involved)
3. PIVOT / UNPIVOT (if PIVOT or UNPIVOT clause detected)
4. Aggregation (if SUM/COUNT/AVG/window function — includes string aggregation: LISTAGG, STRING_AGG, GROUP_CONCAT, XMLAGG)
5. LAG / LEAD (if LAG or LEAD window function detected)
6. CASE WHEN (if conditional logic — includes nested CASE, DECODE, IIF)
7. COALESCE (if null fallback — includes NVL, IFNULL)
8. CONCAT (if string concatenation via CONCAT, ||, or + in string context)
9. Date conversion (if integer → date)
10. CAST (if simple type cast)
11. Teradata-specific (QUALIFY, ZEROIFNULL, NULLIFZERO, OREPLACE, OTRANSLATE, STRTOK, NORMALIZE ON, EXPAND ON, HASHROW — when dialect = Teradata)
12. String normalization (if UPPER/TRIM)
13. Arithmetic (if math operators)
14. Direct mapping (default fallback)

---

## Transformation Type Assignment Summary

| Transformation Type | When to Assign |
|--------------------|-----------------------|
| Direct | Single column, no modification |
| Direct - Type Cast | Single column with CAST only |
| Derived | Any expression, function, CASE, COALESCE, UDF, aggregate, crypto, arithmetic |
| Lookup | Value obtained via JOIN to a reference/lookup table |

---

## 19. Provenance Separation Rule (applies to ALL patterns above)

**Rule:** Business Logic output must contain ONLY executable transformation descriptions. Provenance annotations are NEVER part of the mapping output.

**Prohibited in Business Logic (column J):**
- "Derived from BR-04:" prefix labels
- "per BR-XX" suffixes
- "from design doc" references
- "confidence:", "evidence:", "source_priority:" markers
- Any annotation whose purpose is to trace WHERE the logic came from rather than WHAT the logic does

**Prohibited in Additional Context (column K):**
- `br_ref` key — business rule references are provenance/traceability data

**Acceptable in Business Logic:**
- BR identifiers that appear as part of the VALUE semantics — e.g., a controlled vocabulary code like `'DAILY_REVENUE'` that maps to BR-01 in documentation is acceptable because it describes WHAT is produced, not WHERE it came from.
- References to table names, column names, join conditions, CASE expressions — these are operational logic.

**Where provenance belongs:**
- The provenance JSON file (e.g., `output/{prefix}_provenance.json`) — per-field evidence metadata (system of record)
- The provenance Excel file (e.g., `output/{prefix}_provenance.xlsx`) — human-friendly projection for reviewers
- The "Business Rule Reference" column (J) in provenance.xlsx's "Field Provenance" sheet

**Example — BEFORE (wrong):**
```
Derived from BR-04: CASE WHEN measure_identifier = 'DAILY_MARGIN' AND measure_value_1 < 0 THEN 'Y' ELSE 'N' END
```

**Example — AFTER (correct):**
```
CASE WHEN measure_identifier = 'DAILY_MARGIN' AND measure_value_1 < 0 THEN 'Y' WHEN measure_identifier = 'DAILY_MARGIN' THEN 'N' ELSE NULL END
```
(The BR-04 association is captured in provenance.json/provenance.xlsx, not in the Business Logic field.)

**Example — Additional Context BEFORE (wrong):**
```
load_type:append|grain:product×segment×period×measure|partition_key:reporting_period_end_date|br_ref:BR-01,BR-02,BR-03
```

**Example — Additional Context AFTER (correct):**
```
load_type:append|partition_key:reporting_period_end_date|process_frequency:daily|cdc_type:delta
```
(grain belongs in Target Table Description (L). br_ref associations are captured in provenance.xlsx's Business Rules sheet.)
