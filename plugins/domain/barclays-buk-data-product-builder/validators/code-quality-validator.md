# Validator: code-quality-validator

**Purpose**: Check generated PySpark scripts for best practice violations (no SELECT *, framework read functions, early filters) and validate crypto UDF syntax correctness.

**Severity**: Flag violations — generation continues; user should fix before production deployment.

**Platform**: Glue + Databricks

---

## Part A — PySpark Column Projection & Framework Checks

### Check 1 — No SELECT *

Pattern: `SELECT\s+\*\s+FROM` or `df.select("*")` or `.select(F.col("*"))`

Violation message:
```
⚠️ SELECT * found in {filename} at line {n}.
   Use explicit column lists only: SELECT col1, col2, col3 FROM ...
```

### Check 2 — Framework Read Functions Used (Glue)

For Glue scripts: source reads must use `glue_read_table()` or `glue_read_icb_table()` — not raw SparkSession SQL against catalog.

Anti-pattern: `spark.sql("SELECT ... FROM {db}.{table}")` used directly for source reads without the framework functions.

Note: `spark.sql()` IS allowed for crypto UDFs and transformation logic — this check is specifically about source table reads that bypass the DTX framework.

### Check 3 — Framework Read Functions Used (Databricks)

For Databricks scripts: source reads must use `hf.read_table()` — not raw `spark.read.table()` or direct S3 paths.

### Check 4 — Early Filters Applied

For Transactional tables with `partition_col = dw_bus_dt`: check that `dw_bus_dt` filter is applied at read time, not post-transformation.

Pattern: if `dw_bus_dt` filter appears AFTER a large join or window function → WARNING (performance concern).

### Pass Condition (Part A)

No `SELECT *` found. Framework read functions used. Early filters applied.

### Fail Action (Part A)

Flag each violation with line number and suggested fix:
```
⚠️ PySpark linter warnings in {filename}:
  Line {n}: SELECT * — replace with explicit column list
  Line {m}: Source read without framework function — use glue_read_table() / hf.read_table()
```

---

## Part B — Crypto UDF Syntax Validation

Allowed and disallowed crypto UDF patterns: see `agents/refs/transform-crypto-udf-rules.md` (authoritative). In summary: all `cloud_api_udf_*` calls MUST use `spark.sql()` blocks — DataFrame API (`.withColumn()`, `F.expr()`, `F.udf()`) is never allowed.

### Validation Logic

For each generated `.py` file:

1. Find all crypto-flagged column names from `session/crypto_flags.json`
2. Search for UDF pattern calls: `cloud_api_udf_` in the file
3. For each match: check if it's inside a `spark.sql("""...""")` or `spark.sql('...')` call
   - Inside `spark.sql()` → PASS for that occurrence
   - NOT inside `spark.sql()` (e.g. in `.withColumn()`, `.select()`, `F.expr()`) → VIOLATION

### Pass Condition (Part B)

All `cloud_api_udf_*` UDF calls are inside `spark.sql()` blocks.

### Fail Action (Part B)

Flag violations:
```
⚠️ Crypto UDF syntax violation in {filename}:
  Line {n}: cloud_api_udf_UK_TOK_FT_L0R0_UNC_DE_protect({col}) used outside spark.sql()
  
  Fix: All tokenization/detokenization UDFs must use spark.sql() only.
  DataFrame API is NOT supported for sensitive column handling.
```

---

## Part C — Duplicate Column Detection

### Check 5 — No Duplicate Columns in Final Output

Parse the final `.select()` statement (or the cumulative output of `.withColumn()` and `.alias()` chains) in each generated transform file.

1. Extract all output column names (case-insensitive)
2. Check for duplicates

Spark silently picks one occurrence when duplicate column names exist in a DataFrame — the other is shadowed. This causes silent data loss that is extremely difficult to debug downstream.

**Severity:** BLOCK — duplicate columns cause silent data corruption.

**Error format:**
```
❌ DUPLICATE COLUMN in {filename}:
  Column '{col}' appears {count} times in the output.
  Spark will ambiguously resolve this — one occurrence silently shadows the others.
  Fix: Remove duplicate or rename with distinct .alias()
```

### Pass Condition (Part C)

No duplicate column names in any generated transform output.

---

## Part D — Naming Convention Enforcement

### Check 6 — Output Column Names Follow Convention

For target columns in generated PySpark transform output:

1. Extract all target column names from the final `.select()` or `.alias()` output
2. Validate against the data engineering naming convention: `^[a-z][a-z0-9_]*$` (snake_case, lowercase)
3. Cross-reference against `mapping_parsed.json → columns[].target_column_name`

**Important:** The mapping document is the source of truth. If the mapping specifies a column name that violates the convention, the pipeline MUST faithfully reproduce it. This check only flags columns whose names in generated code deviate from BOTH the mapping AND the convention.

**Severity:** WARNING (non-blocking) — naming violations don't cause runtime failures but indicate generation drift.

Pattern: `^[a-z][a-z0-9_]*$`

**Error format:**
```
⚠️ Column naming violation in {filename}:
  Column '{col}' does not follow snake_case convention (pattern: ^[a-z][a-z0-9_]*$)
  AND differs from mapping target_column_name '{mapping_col}'
  Fix: Use lowercase snake_case, or verify the mapping column name is intentional
```

### Pass Condition (Part D)

All output column names either match the mapping exactly OR follow the snake_case convention.

---

## Part E — Redundant Type Cast Detection

### Check 7 — No Redundant .cast() Calls

For each `.cast("type")` in generated code:

1. Identify the column being cast
2. Look up the column's `source_datatype` from `mapping_parsed.json → columns[].source_datatype`
3. If `source_datatype` equals the cast target type (with alias normalization), flag as redundant

**Type equivalence mapping** (to avoid false positives):
- `string` = `varchar` = `nvarchar` = `char`
- `long` = `bigint`
- `int` = `integer`
- `double` = `float` (precision-dependent — flag only exact matches)
- `timestamp` = `timestamp_ntz` (context-dependent — only flag exact matches)
- `decimal(p,s)` — compare precision and scale exactly

**Severity:** WARNING (non-blocking, auto-fixable) — redundant casts are harmless but add noise.

**Error format:**
```
⚠️ Redundant .cast() in {filename}:
  Line {n}: F.col('{col}').cast('{type}') — source_datatype is already '{source_type}'
  Fix: Remove the redundant .cast() call
```

### Pass Condition (Part E)

No redundant type casts in generated transform code.

---

## Part F — Rolling Deletion Boundary Enforcement

### Check 8 — No DELETE Statements in Transform Code

Pattern: `DELETE\s+FROM` in any generated transform `.py` file.

Rolling data deletion is TargetWriter's responsibility via `config['rolling_deletion']`. Transform code must never execute `DELETE FROM` — TargetWriter._rolling_delete() handles this after writes.

**Severity:** BLOCK — DELETE in transform code bypasses the controlled rolling deletion lifecycle.

**Error format:**
```
❌ DELETE statement in transform code {filename}:
  Line {n}: DELETE FROM detected in transform.
  Rolling deletion is handled by TargetWriter._rolling_delete() via config['rolling_deletion'].
  Fix: Remove the DELETE statement — transform code must never execute DELETE FROM.
```

### Pass Condition (Part F)

No `DELETE FROM` statements in any generated transform code.
