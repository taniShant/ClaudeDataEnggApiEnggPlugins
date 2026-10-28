---
description: "Reference for converting STTM multi-step operations to PySpark code — maps INSERT_SELECT, UPDATE, DELETE, TRUNCATE, MERGE, and RENAME operations to their DataFrame/SQL equivalents."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-28
---

# Multi-Step Operation → PySpark Conversion Patterns

Reference document for converting STTM Transformation Lineage operations to PySpark code.

## Operation Conversion Table

| STTM Operation | PySpark Equivalent | Notes |
|---|---|---|
| `INSERT_SELECT` | `df = spark.sql("SELECT ... FROM ... JOIN ...")` or DataFrame API join+select | Standard data flow — most common |
| `UPDATE` (SET col = expr WHERE cond) | `df = df.withColumn(col, F.when(cond, expr).otherwise(F.col(col)))` | In-place update simulation via conditional column replacement |
| `DELETE` (WHERE cond) | `df = df.filter(~(cond))` | Invert the WHERE condition to keep non-deleted rows |
| `TRUNCATE` | Not applicable — DataFrame is replaced entirely | TRUNCATE on intermediate table = skip or replace with empty |
| `MERGE` (MATCHED/NOT MATCHED) | See MERGE pattern below | Complex — requires join + conditional logic |
| `RENAME` (atomic swap) | Not applicable — DataFrames don't have persistent names | Variable reassignment: `final_df = new_df` |

## Detailed Conversion Patterns

### INSERT_SELECT → DataFrame Creation
```python
# STTM Step: INSERT_SELECT from s_acctdb.account_base JOIN r_refdb.risk_params
normal_risk_score_df = account_base_df.join(
    risk_params_df,
    on=account_base_df.scorecard_id == risk_params_df.scorecard_id,
    how="inner"
).filter(
    (F.col("behaviour_score") > 31) &
    (~F.col("status_code").isin("A", "B", "X"))
).select(
    account_base_df.account_id,
    (F.lit(1) / (F.lit(1) + F.exp(
        (risk_params_df.score_weight * account_base_df.behaviour_score) + risk_params_df.intercept
    ))).alias("risk_score")
)
```

### UPDATE → Conditional Column Replacement
```python
# STTM Step: UPDATE work_db.bc_history_temp SET payments_received = epp.amt_pymt_prch
#            FROM e_paydb.epp_payments_update epp
#            WHERE bc.account_number = epp.account_number
bc_history_temp_df = bc_history_temp_df.alias("bc").join(
    epp_payments_df.alias("epp"),
    on=F.col("bc.account_number") == F.col("epp.account_number"),
    how="left"
).withColumn(
    "payments_received",
    F.when(
        F.col("epp.account_number").isNotNull(),  # matched rows
        F.col("epp.amt_pymt_prch")
    ).otherwise(F.col("bc.payments_received"))
).withColumn(
    "payment_date",
    F.when(
        F.col("epp.account_number").isNotNull(),
        F.col("epp.payment_date")
    ).otherwise(F.col("bc.payment_date"))
).drop("epp.*")  # drop joined columns
```

### DELETE → Inverted Filter
```python
# STTM Step: DELETE FROM work_db.bc_history_temp
#            WHERE billing_period < ADD_MONTHS(:billing_period, -73)
bc_history_temp_df = bc_history_temp_df.filter(
    ~(F.col("billing_period") < F.add_months(F.lit(billing_period_param), -73))
)
# Equivalent: keep rows WHERE billing_period >= ADD_MONTHS(:billing_period, -73)
```

### TRUNCATE → Replace or Skip
```python
# STTM Step: TRUNCATE work_db.staging_table
# In PySpark: if this step is followed by INSERT_SELECT, simply replace the DataFrame
# staging_table_df = spark.createDataFrame([], staging_schema)  # if explicit empty needed
# Usually just let the next INSERT_SELECT step create a new DataFrame
```

### MERGE → Join + Conditional Logic
```python
# STTM Step: MERGE INTO fdp_uk_mortgage_db.mortgage_account tgt
#            USING e_staging_db.account_staging src
#            ON tgt.account_id = src.account_id AND tgt.active = '1'
#            WHEN MATCHED AND src.update_date > tgt.update_date THEN UPDATE SET ...
#            WHEN NOT MATCHED THEN INSERT ...

# Step 1: Identify matched and not-matched rows
merged_df = target_df.alias("tgt").join(
    source_df.alias("src"),
    on=(F.col("tgt.account_id") == F.col("src.account_id")) &
       (F.col("tgt.active") == F.lit("1")),
    how="full_outer"
)

# Step 2: Apply MATCHED logic (update existing rows)
matched_update_df = merged_df.filter(
    F.col("tgt.account_id").isNotNull() &
    F.col("src.account_id").isNotNull() &
    (F.col("src.update_date") > F.col("tgt.update_date"))
).select(
    F.col("tgt.account_id"),
    F.col("src.balance").alias("balance"),
    F.col("src.status").alias("status")
)

# Step 3: Apply NOT MATCHED logic (insert new rows)
not_matched_insert_df = merged_df.filter(
    F.col("tgt.account_id").isNull()
).select(
    F.col("src.account_id"),
    F.col("src.balance"),
    F.col("src.status")
)

# Step 4: Combine unchanged + updated + inserted
unchanged_df = target_df.join(source_df, on="account_id", how="left_anti")
result_df = unchanged_df.unionByName(matched_update_df).unionByName(not_matched_insert_df)
```

### RENAME → Variable Reassignment
```python
# STTM Step: RENAME work_db.bc_history_new TO work_db.bc_history
# In PySpark: simply reassign the variable
bc_history_df = bc_history_new_df
# If displaced table needed:
# bc_history_prev_df = bc_history_df  (save reference before swap)
# bc_history_df = bc_history_new_df
```

## Important Notes

1. **No in-place mutations**: PySpark DataFrames are immutable. All "updates" create new DataFrames.
2. **DELETE is filter inversion**: `DELETE WHERE cond` becomes `df.filter(~(cond))`.
3. **TRUNCATE is typically a no-op**: The subsequent INSERT_SELECT creates a fresh DataFrame.
4. **MERGE requires full outer join**: Must handle matched, not-matched, and unchanged rows separately.
5. **Variable naming**: Use STTM step names for DataFrame variables (see Step→DataFrame Naming Convention).
6. **Staging hints**: CHECKPOINT steps write intermediate parquet; PERSIST steps use `.persist()`.
