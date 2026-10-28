# Validator: pk-null-risk-validator

**Purpose**: Detect generated PySpark transform code that exposes primary key columns to NULL-producing patterns. Primary keys that can be NULL cause silent data corruption — CDC MERGE ON conditions fail, deduplication breaks, and downstream joins produce incorrect results. These patterns are detectable statically without executing the transform against real data.

**Severity**: BLOCK on patterns A, B, D. WARNING on pattern C.

**Platform**: Glue + Databricks

---

## Prerequisites

- Generated transform file(s) exist (`generated/{platform}/transforms/` or `generated/databricks/src/Notebooks/`)
- `session/mapping_parsed.json` exists and is populated (parse-mapping completed)
- `session/intent_identification.json` exists and has `primary_key_columns` populated (identify-intent completed)

---

## Invocation

- **Primary**: Called inline by `/gen-transform` STEP FINAL.4 (runs after join predicate validation)
- **Secondary**: Called by `/validate` Batch 5 Part F (runs as part of full validation suite)
- **Gate**: `/push` refuses if `session_state.pk_null_risk_result != "passed"` and any BLOCKING violations exist

**Script**: `${CLAUDE_PLUGIN_ROOT}/scripts/validate_pk_null_risk.py`

```bash
python scripts/validate_pk_null_risk.py <transform_file.py> session/mapping_parsed.json session/intent_identification.json [--target-table <name>]
```

Exit codes:
- `0` = no PK null risks detected
- `1` = violations found (JSON printed to stdout)
- `2` = usage/parse error

---

## Checks

### Check 1 — LEFT JOIN Nullable Side (BLOCKING)

If a PK column's derivation traces to the right-side DataFrame of a LEFT JOIN and is NOT wrapped in `F.coalesce()`:

1. Parse all `.join()` calls, identify `how="left"` or `how="left_outer"`
2. Determine which DataFrame is the RIGHT side (nullable side)
3. For each PK column, check if its expression references a nullable-side DataFrame
4. Verify `F.coalesce()` wraps the reference (either in the immediate expression or in a subsequent `.withColumn()` that overrides the same column)

**BLOCK** if a PK column sources from a nullable-side DataFrame without coalesce protection.

**Error format:**
```
❌ PK column 'customer_survey_id' may source from the nullable side of a LEFT JOIN
   (right-side DataFrames: ['wm_append_data']) without F.coalesce() protection.
   If the join does not match, this PK column will be NULL.
   Fix: Wrap with F.coalesce(F.col('customer_survey_id'), F.lit(<default>))
```

### Check 2 — F.when() Without .otherwise() (BLOCKING)

If a PK column is derived from an `F.when()` chain that ends without `.otherwise()`:

1. Find the expression that produces each PK column (`.withColumn()`, `.alias()`, etc.)
2. Check if the expression contains `F.when()`
3. Verify `.otherwise()` is present in the chain

Spark returns NULL for rows that match no `F.when()` condition when `.otherwise()` is absent.

**BLOCK** if a PK column's `F.when()` chain lacks `.otherwise()`.

**Error format:**
```
❌ PK column 'account_status' is derived from F.when() without .otherwise().
   Spark returns NULL for rows that match no condition.
   Fix: Add .otherwise(F.lit(<default>)) to the F.when() chain.
```

### Check 3 — UDF-Derived PK Column (WARNING)

If a PK column is derived through a UDF (`cloud_api_udf_*`) inside `spark.sql()`:

1. Check if the PK column's derivation method is `spark_sql`
2. Check if the SQL block contains `cloud_api_udf_` references

UDF behaviour is opaque — cannot statically verify it never returns NULL.

**WARN** (do not block) — UDFs may return NULL for invalid inputs but this cannot be proven statically.

**Error format:**
```
⚠️ PK column 'masked_account_id' is derived through a UDF inside spark.sql().
   UDF behaviour is opaque — cannot statically verify it never returns NULL.
   Fix: Add COALESCE() wrapper inside the SQL or F.coalesce() after the result.
```

### Check 4 — PK Column Not Produced (BLOCKING)

If a PK column listed in `intent_identification.json → primary_key_columns` does not appear in any expression chain in the generated transform:

1. Search for `.withColumn("pk_col", ...)`, `.alias("pk_col")`, `F.col("pk_col")`, or `pk_col` in `spark.sql()` blocks
2. If not found by any method, the PK column is entirely missing from the transform

**BLOCK** if any PK column is not produced.

**Error format:**
```
❌ PK column 'case_id' is listed in intent_identification.json but not found
   in any .withColumn(), .alias(), F.col(), or spark.sql() expression.
   Fix: Ensure the transform produces 'case_id' in its output .select().
```

---

## Known Exceptions (NOT flagged as violations)

| Category | Examples | Reason |
|----------|----------|--------|
| **Audit columns** | `eff_start_date`, `eff_end_date`, `active`, `dw_lod_tmp`, `dw_upd_lod_tmp`, `dw_bus_dt` | TargetWriter-managed; never PK candidates even if listed in intent |
| **INNER JOIN sources** | PK column from right side of INNER JOIN | INNER JOIN guarantees match — no NULL risk from join itself |
| **Coalesce-wrapped** | `F.coalesce(F.col("pk_col"), F.lit(default))` | Null risk is explicitly mitigated |
| **Otherwise-present** | `F.when(...).otherwise(F.lit(default)).alias("pk_col")` | All branches covered |

---

## Self-Heal Retry Logic

When BLOCKING violations are found during `/gen-transform` STEP FINAL.4:

1. **First attempt**: Re-invoke transform-generator-agent with ONLY the violation list. Instruction: fix only the flagged PK columns by adding `F.coalesce()` or `.otherwise()` as appropriate.
2. **Second attempt**: Same as above if violations persist.
3. **After 2 retries**: Mark file as `DRAFT_UNVALIDATED`. Set `session_state.pk_null_risk_result = "failed"`.

The retry agent gets a **fresh context** (no compaction risk) containing:
- Violation list (~200 tokens)
- `session/intent_identification.json` (PK column names)
- Generated file to fix (read from disk)
- Instruction to fix only flagged PK columns

---

## Integration Points

| Integration | When | Behavior |
|---|---|---|
| `/gen-transform` STEP FINAL.4 | After join predicate validation passes | Run validator → self-heal retry if BLOCKING violations |
| `/validate` Batch 5 Part F | During full validation suite | Run validator → report findings (no retry here) |
| `/push` gate | Before push/commit | Refuse if any BLOCKING `pk_null_risk_violations` exist |

---

## Session State Fields

| Field | Type | Set By | Values |
|---|---|---|---|
| `pk_null_risk_result` | string | STEP FINAL.4 | `"passed"`, `"failed"`, `"skipped_no_python"`, `"skipped_no_pks"` |
| `pk_null_risk_violations` | array\|null | STEP FINAL.4 | Array of violation objects, or null if passed |

---

## Pass Condition

All primary key columns in generated transform files are free from NULL-producing patterns. Zero BLOCKING violations across all generated files for the session. WARNING violations (Check 3 — UDF-derived) are surfaced but do not block.
