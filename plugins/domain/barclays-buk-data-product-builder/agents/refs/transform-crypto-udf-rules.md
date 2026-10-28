---
description: "Conditional rules for crypto UDF usage in transform generation — defines detokenization placement (before transformation in source read SQL) and tokenization placement (after transformation before Iceberg insert)."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-07-08
---

# Crypto UDF Rules — Transform Generation (Phase 4)

**Load condition:** Only read this file if `crypto_flags.has_crypto == true` for the current target table.

## Crypto UDFs (both platforms — via self.spark.sql() ONLY)

**Detokenization** (before transformation — applied in source read SQL):
```python
source_view = self.spark.sql("""
    SELECT
        cloud_api_udf_{DE}_unprotect({col}) AS {col}_clear,
        other_col
    FROM source_table_view
    WHERE ...
""")
```

**Tokenization** (after transformation — applied in final write SQL before Iceberg insert):
```python
output_df = self.spark.sql("""
    SELECT
        cloud_api_udf_{DE}_protect({col}) AS {col},
        other_col
    FROM transformed_view
""")
```

**NEVER** use:
```python
df.withColumn("col", tokenize_udf(col("col")))  # WRONG
```

## UDF Naming Convention

- DE name from `crypto_flags.json` → `custom_de_list[].de_name`
- UDF format: `cloud_api_udf_{de_name}_protect` / `cloud_api_udf_{de_name}_unprotect`
- One UDF pair per DE name (multiple columns may share the same DE)

## Placement Rules

1. **Detokenization** happens FIRST — before any join/filter/transform operates on the cleartext value
2. **Tokenization** happens LAST — after all transformations, immediately before write
3. Both operations MUST use `self.spark.sql()` blocks with temp views — never DataFrame API `.withColumn()`
4. If a column is both detokenized from source AND tokenized for target, ensure intermediate logic uses `{col}_clear` name

## Multi-Column Crypto

When multiple columns in one table have crypto flags:
```python
source_view = self.spark.sql("""
    SELECT
        cloud_api_udf_{DE1}_unprotect(col_a) AS col_a_clear,
        cloud_api_udf_{DE2}_unprotect(col_b) AS col_b_clear,
        non_crypto_col
    FROM source_table_view
""")

```

Group all crypto operations in a single SQL block per phase (detokenize together, tokenize together).
