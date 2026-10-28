# Validator: iceberg-ddl-validator

**Purpose**: Validate Databricks Iceberg DDL SQL files against structural and content rules defined in `schemas/iceberg_ddl_rules.json` — ensuring correct table creation syntax, Unity Catalog naming, Iceberg format specification, column fidelity, partitioning correctness, and absence of destructive operations.

**Severity**: DRAFT_UNVALIDATED for R01–R06.

**Platform**: Databricks only.

**Invocation points**: `/validate` Batch 2, `post-generate-validate` hook, `/gen-ddl` STEP 4.

**Rule schema**: `schemas/iceberg_ddl_rules.json`

---

## Validation Logic

### Check 1 — R01: CREATE TABLE IF NOT EXISTS Present

DDL file must contain the `CREATE TABLE IF NOT EXISTS` statement. This is the foundational DDL keyword for Iceberg table creation on Databricks.

**check_type**: `contains`
**fail_action**: `DRAFT_UNVALIDATED`

**Rules:**
1. Scan the DDL `.sql` file for the literal string `CREATE TABLE IF NOT EXISTS`
2. The statement must appear exactly once
3. `CREATE TABLE` without `IF NOT EXISTS` is rejected — all generated DDL must be idempotent

**Anti-patterns (BLOCK):**
```sql
-- ❌ Missing IF NOT EXISTS — not idempotent, will fail on re-run
CREATE TABLE dev_buk_complaints_cdp.cdp_uk_complaints_db.case_event_dbx (
  ...
);

-- ❌ Missing entirely — file contains only INSERT or SELECT
INSERT INTO dev_buk_complaints_cdp.cdp_uk_complaints_db.case_event_dbx
SELECT * FROM source;

-- ✅ Correct
CREATE TABLE IF NOT EXISTS dev_buk_complaints_cdp.cdp_uk_complaints_db.case_event_dbx (
  ...
);
```

---

### Check 2 — R02: Three-Part Unity Catalog Table Name

The table name in the `CREATE TABLE IF NOT EXISTS` statement must use the three-part Unity Catalog format: `catalog.schema.table`.

**check_type**: `regex_match`
**pattern**: `CREATE TABLE IF NOT EXISTS\s+[\w]+\.[\w]+\.[\w]+`
**fail_action**: `DRAFT_UNVALIDATED`

**Rules:**
1. Extract the table identifier following `CREATE TABLE IF NOT EXISTS`
2. It must match three dot-separated identifiers: `{catalog}.{schema}.{table}`
3. Single-part or two-part names are rejected — Databricks Unity Catalog requires the full path
4. Each segment must contain only word characters (letters, digits, underscores)

**Anti-patterns (BLOCK):**
```sql
-- ❌ Two-part name — missing catalog
CREATE TABLE IF NOT EXISTS cdp_uk_complaints_db.case_event_dbx (
  ...
) USING iceberg;

-- ❌ Single-part name — completely ambiguous
CREATE TABLE IF NOT EXISTS case_event_dbx (
  ...
) USING iceberg;

-- ❌ Quoted identifiers with special characters
CREATE TABLE IF NOT EXISTS `dev-catalog`.`my-schema`.`my-table` (
  ...
) USING iceberg;

-- ✅ Correct — three-part Unity Catalog format
CREATE TABLE IF NOT EXISTS dev_buk_complaints_cdp.cdp_uk_complaints_db.case_event_dbx (
  ...
) USING iceberg;
```

---

### Check 3 — R03: USING iceberg Clause Present

The DDL must specify the `USING iceberg` clause to declare the table format as Apache Iceberg.

**check_type**: `contains`
**fail_action**: `DRAFT_UNVALIDATED`

**Rules:**
1. Scan the DDL file for the literal string `USING iceberg`
2. Case-sensitive match — `USING ICEBERG` or `using Iceberg` are non-standard and rejected
3. The clause must appear after the column definitions and before `PARTITIONED BY`
4. Without this clause, Databricks defaults to Delta format, which is incorrect for Iceberg tables

**Anti-patterns (BLOCK):**
```sql
-- ❌ Missing USING clause — defaults to Delta format
CREATE TABLE IF NOT EXISTS dev_buk_complaints_cdp.cdp_uk_complaints_db.case_event_dbx (
  case_id STRING,
  event_date DATE
)
PARTITIONED BY (event_date);

-- ❌ Wrong format specified
CREATE TABLE IF NOT EXISTS dev_buk_complaints_cdp.cdp_uk_complaints_db.case_event_dbx (
  case_id STRING,
  event_date DATE
) USING delta;

-- ❌ Wrong case
CREATE TABLE IF NOT EXISTS dev_buk_complaints_cdp.cdp_uk_complaints_db.case_event_dbx (
  case_id STRING,
  event_date DATE
) USING ICEBERG;

-- ✅ Correct
CREATE TABLE IF NOT EXISTS dev_buk_complaints_cdp.cdp_uk_complaints_db.case_event_dbx (
  case_id STRING,
  event_date DATE
) USING iceberg;
```

---

### Check 4 — R04: Column Count Matches Mapping Excel

The number of columns declared in the DDL must match the number of target columns defined in the mapping Excel file.

**check_type**: `count_match`
**source**: `mapping_excel.columns`
**fail_action**: `DRAFT_UNVALIDATED`

**Rules:**
1. Parse the column definitions between `CREATE TABLE IF NOT EXISTS ... (` and the closing `)`
2. Count the number of column declarations (each `column_name TYPE` pair)
3. Compare against the column count from `mapping_excel.columns` (the parsed mapping spreadsheet)
4. Counts must be exactly equal — missing or extra columns indicate a generation defect
5. Do not count partition columns separately if they are also declared in the column list

**Anti-patterns (BLOCK):**
```sql
-- ❌ Mapping Excel has 5 columns but DDL declares only 3 — missing columns
-- mapping_excel.columns = [case_id, event_date, status, category, resolution_date]
CREATE TABLE IF NOT EXISTS dev_buk_complaints_cdp.cdp_uk_complaints_db.case_event_dbx (
  case_id STRING,
  event_date DATE,
  status STRING
) USING iceberg;

-- ❌ DDL has extra column not in mapping — hallucinated column
-- mapping_excel.columns = [case_id, event_date, status]
CREATE TABLE IF NOT EXISTS dev_buk_complaints_cdp.cdp_uk_complaints_db.case_event_dbx (
  case_id STRING,
  event_date DATE,
  status STRING,
  created_by STRING    -- Not in mapping Excel!
) USING iceberg;

-- ✅ Correct — column count matches mapping Excel exactly
-- mapping_excel.columns = [case_id, event_date, status]
CREATE TABLE IF NOT EXISTS dev_buk_complaints_cdp.cdp_uk_complaints_db.case_event_dbx (
  case_id STRING,
  event_date DATE,
  status STRING
) USING iceberg;
```

---

### Check 5 — R05: Partition Column Is a Declared Target Column

Any column referenced in the `PARTITIONED BY` clause must also appear in the column definition list of the DDL.

**check_type**: `column_present`
**source**: `intent_identification.partition_key_columns`
**fail_action**: `DRAFT_UNVALIDATED`

**Rules:**
1. Extract column names from the `PARTITIONED BY (...)` clause
2. Cross-reference each partition column against `intent_identification.partition_key_columns` from the intent file
3. Each partition column must also be declared in the table's column list
4. BLOCK if a partition column is not found in the column definitions — this causes a runtime DDL error
5. If no `PARTITIONED BY` clause exists but `intent_identification.partition_key_columns` is non-empty, flag as a warning

**Anti-patterns (BLOCK):**
```sql
-- ❌ Partition column "process_date" not declared in column list
CREATE TABLE IF NOT EXISTS dev_buk_complaints_cdp.cdp_uk_complaints_db.case_event_dbx (
  case_id STRING,
  event_date DATE,
  status STRING
) USING iceberg
PARTITIONED BY (process_date);    -- "process_date" is not a declared column!

-- ❌ Partition column name has typo
CREATE TABLE IF NOT EXISTS dev_buk_complaints_cdp.cdp_uk_complaints_db.case_event_dbx (
  case_id STRING,
  event_date DATE,
  status STRING
) USING iceberg
PARTITIONED BY (evnt_date);       -- Typo: should be "event_date"

-- ✅ Correct — partition column exists in column list
CREATE TABLE IF NOT EXISTS dev_buk_complaints_cdp.cdp_uk_complaints_db.case_event_dbx (
  case_id STRING,
  event_date DATE,
  status STRING
) USING iceberg
PARTITIONED BY (event_date);
```

---

### Check 6 — R06: No Destructive Operations

The DDL file must not contain destructive SQL operations. Generated DDL is strictly for table creation — never for dropping, truncating, or altering existing tables.

**check_type**: `not_contains`
**patterns**: `DROP TABLE`, `TRUNCATE TABLE`, `ALTER TABLE`
**fail_action**: `DRAFT_UNVALIDATED`

**Rules:**
1. Scan the entire DDL file for the literal strings: `DROP TABLE`, `TRUNCATE TABLE`, `ALTER TABLE`
2. Case-insensitive match — `drop table`, `Drop Table`, etc. are all rejected
3. These operations are never part of generated DDL; their presence indicates hallucination or template contamination
4. `DROP TABLE IF EXISTS` followed by `CREATE TABLE` is a known anti-pattern from other SQL dialects — not permitted here

**Anti-patterns (BLOCK):**
```sql
-- ❌ DROP before CREATE — destructive re-creation pattern
DROP TABLE IF EXISTS dev_buk_complaints_cdp.cdp_uk_complaints_db.case_event_dbx;
CREATE TABLE IF NOT EXISTS dev_buk_complaints_cdp.cdp_uk_complaints_db.case_event_dbx (
  ...
) USING iceberg;

-- ❌ TRUNCATE — data loss
TRUNCATE TABLE dev_buk_complaints_cdp.cdp_uk_complaints_db.case_event_dbx;

-- ❌ ALTER TABLE — schema evolution is managed separately, not in generated DDL
ALTER TABLE dev_buk_complaints_cdp.cdp_uk_complaints_db.case_event_dbx
ADD COLUMN new_col STRING;

-- ✅ Correct — CREATE only, no destructive operations
CREATE TABLE IF NOT EXISTS dev_buk_complaints_cdp.cdp_uk_complaints_db.case_event_dbx (
  case_id STRING,
  event_date DATE,
  status STRING
) USING iceberg;
```

---

## Pass Condition

All 6 rules pass: DDL contains `CREATE TABLE IF NOT EXISTS` with a three-part Unity Catalog table name and `USING iceberg` clause. Column count matches the mapping Excel. Partition columns are declared in the column list. No destructive operations (`DROP`, `TRUNCATE`, `ALTER TABLE`) are present.

## Fail Action

DRAFT_UNVALIDATED for R01–R06. Output:
```
❌ Iceberg DDL validation failed:

  [R01] Missing CREATE TABLE IF NOT EXISTS:
    File: {filename}
    Found: "{actual_statement}"
    Fix: DDL must contain exactly: CREATE TABLE IF NOT EXISTS

  [R02] Table name not in three-part Unity Catalog format:
    File: {filename}
    Found: "{found_table_reference}"
    Fix: Use fully-qualified format: {catalog}.{schema}.{table}

  [R03] Missing USING iceberg clause:
    File: {filename}
    Fix: Add USING iceberg after column definitions

  [R04] Column count mismatch:
    File: {filename}
    DDL columns: {ddl_count}, Mapping Excel columns: {excel_count}
    Missing: [{missing_columns}]
    Extra: [{extra_columns}]
    Fix: Reconcile DDL columns with mapping Excel target columns

  [R05] Partition column not in column list:
    File: {filename}
    Partition column: "{partition_col}"
    Declared columns: [{column_list}]
    Fix: Ensure partition column is declared in the CREATE TABLE column list

  [R06] Destructive operation found:
    File: {filename}, Line {n}
    Found: "{destructive_statement}"
    Fix: Remove destructive operation. Generated DDL must only contain CREATE TABLE IF NOT EXISTS.
```
