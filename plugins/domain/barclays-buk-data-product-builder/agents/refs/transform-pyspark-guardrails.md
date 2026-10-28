---
description: "PySpark best-practice enforcement for both platforms — prohibits .collect(), .toPandas(), unbounded crossJoin, custom UDFs, F.cast() errors, and DELETE FROM in transform logic."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-07-08
---

# PySpark Generation Guardrails (Both Platforms)

**PURPOSE**: Enforce PySpark best practices at generation time so that anti-patterns are never produced. These rules are NON-NEGOTIABLE — code-review-agent will flag violations post-generation, but prevention is cheaper than correction.

## A. Prohibited Patterns (NEVER Generate)

| Pattern | Risk | Alternative |
|---------|------|-------------|
| `.collect()` in transformation logic | Memory explosion on driver | Use DataFrame operations; aggregate with `F.sum()`, `F.count()`, etc. |
| `.toPandas()` in transformation logic | Driver OOM for large datasets | Stay in Spark DataFrame API |
| Unbounded `crossJoin()` | Cartesian product — O(n×m) rows | Always require explicit join condition; if truly needed, document cardinality bounds |
| `.count()` inside transformation loops | Forces full DAG evaluation per iteration | Use `.count()` only at final validation (outside transform logic) |
| Custom Python UDFs (`@udf`, `F.udf(...)`) | Serialization overhead, no Catalyst optimization | Use built-in `pyspark.sql.functions` equivalents; exception: crypto via `spark.sql()` |
| Nested `F.concat(F.concat(...), ...)` | Hard to read, no separator handling | Use `F.concat_ws(separator, *cols)` |
| `df.rdd.map(...)` / `df.rdd.flatMap(...)` | Breaks Catalyst optimizer, forces serialization | Stay in DataFrame API with `withColumn`, `select`, `explode` |
| `df.foreach(...)` / `df.foreachPartition(...)` | Side effects break determinism | Use `write` operations or `F.transform()` for array processing |
| `F.cast('type', col)` / `F.cast(col, 'type')` | Runtime AttributeError — `F.cast()` does not exist in PySpark | `F.col('col').cast('type')` or `expr.cast('type')` |
| `__import__('pyspark.sql.window').Window` or any inline `__import__(...)` | Non-idiomatic, breaks IDE navigation, unreadable | Use `additional_imports` whitelist — approved imports are conditionally rendered via `{{#each additional_imports}}`. NEVER use `__import__()`. |
| `DELETE FROM` / `spark.sql("DELETE ...")` in transform code | Deletion is config-owned, not transform-owned | Rolling data deletion is executed by `TargetWriter._rolling_delete()` after each write, driven by `config['rolling_deletion']`. If the mapping mentions data retention, expiry, or rolling deletion — it belongs in config, not in the transform. |

## B. Performance Optimization Rules (ALWAYS Apply)

1. **Filter early (predicate pushdown)**
   - Apply the most-selective filter BEFORE any join — but ONLY filters not already in config
   - When multiple filters exist, order by selectivity: most-restrictive first
   - Example: `source_df.filter(F.col('status') == 'ACTIVE')` before joining with lookup table
   - **ALL source-level filters declared in config** (both partition AND business filters) are applied
     by SourceReader automatically BEFORE transform receives the DataFrame — do NOT duplicate.
     This includes standard defaults (active='1', dw_bus_dt=date) AND alias-specific business
     filters extracted from the mapping. Check the filter manifest before generating any `.filter()`.
   - Only POST-JOIN / cross-source filters (operating on columns from multiple sources) and
     filters on computed/derived columns belong in transform code.

2. **Column pruning at each step**
   - After each join or complex transformation, `.select()` only columns needed downstream
   - Do NOT carry all source columns through multi-step pipelines
   - Example: after a 3-way join producing 50 columns, select only the 12 needed for derivation step
   ```python
   # GOOD: prune after join
   joined_df = a.join(b, 'key').select('key', 'col1', 'col2', 'col3')
   
   # BAD: carry all columns through pipeline
   joined_df = a.join(b, 'key')  # 50+ columns from both sides
   ```

3. **Broadcast small tables (LOOKUP role only — never the main/driver source)**
   - Apply `F.broadcast()` ONLY for decode/lookup/reference tables (LOOKUP role)
   - NEVER broadcast the main/driver source table — config `cdc.broadcast_source` handles
     broadcast at the CDC merge layer via TargetWriter/run_cdc
   - MAIN = source table from which majority of target columns derive (most source_references)
   - LOOKUP = table joined to enrich 1-2 columns; name contains `_decode`, `_ref`, `_lookup`, `_dim`
   - Threshold: domain knowledge indicates < 500K rows OR table name matches LOOKUP naming patterns
   - If uncertain whether MAIN or LOOKUP → treat as MAIN (do NOT broadcast) — safer default
   ```python
   # GOOD: broadcast a small lookup/reference table
   joined_df = main_df.join(F.broadcast(lookup_df), 'lookup_key')
   
   # BAD: broadcasting the main source table (config handles this at CDC layer)
   # joined_df = F.broadcast(main_source_df).join(target_df, 'pk')  ← NEVER DO THIS
   ```

4. **Coalesce vs Repartition**
   - **Coalesce (narrow)**: Use when REDUCING partition count before write — no full shuffle
   - **Repartition (wide)**: Use ONLY when you need to INCREASE partitions OR repartition by a specific key before a large join
   - TargetWriter handles final write partitioning — do NOT coalesce in transform unless explicitly needed
   - If domain knowledge specifies target file count: add `.coalesce(n)` before returning `final_df`

5. **Repartition before large joins**
   - When BOTH sides of a join are large (>1M rows each) and share a join key:
   ```python
   # Co-locate data before join to reduce shuffle
   df_a = df_a.repartition('account_id')
   df_b = df_b.repartition('account_id')
   joined = df_a.join(df_b, 'account_id')
   ```
   - Only apply when domain knowledge indicates large volumes — NOT for small/medium datasets

6. **Shuffle-aware operation ordering**
   - Group transformations that share the same partitioning key together
   - Perform all filters on a DataFrame BEFORE joining (reduces shuffle volume)
   - Apply column derivations (withColumn) AFTER joins (derivations are narrow operations, joins are wide)

7. **Join key deduplication & right-key cleanup (MANDATORY)**
   - **Symmetric keys** (same column name both sides) → LIST syntax auto-deduplicates:
   ```python
   # GOOD: symmetric key — one copy of "account_id" in output
   joined_df = left_df.join(right_df, ["account_id"], "left")
   
   # BAD: creates TWO "account_id" columns → AnalysisException
   joined_df = left_df.join(right_df, left_df["account_id"] == right_df["account_id"], "left")
   ```
   - **Asymmetric keys** (different names) → expression syntax + DROP right key immediately:
   ```python
   # GOOD: asymmetric key with immediate right-key drop
   joined_df = left_df.join(
       right_df,
       left_df["customer_survey_id"] == right_df["unique_survey_ref"],
       "left"
   ).drop(right_df["unique_survey_ref"])  # redundant FK reference — prune immediately
   
   # Exception: keep right key ONLY if it maps to a target column in final SELECT
   ```
   - Compound all-symmetric: `["key1", "key2"]`
   - Mixed keys: expression syntax + `.drop()` ALL right-side keys (both symmetric duplicates and asymmetric FK refs)
   - **Chain join accumulation rule** (3+ joins): MUST prune after each join — never carry redundant keys into the next join. Accumulated unneeded columns from prior joins cause column bloat and increase ambiguity risk.
   - Post-join: never use bare `F.col("name")` for columns existing in multiple joined sources

## C. Null Safety Rules

1. **Derived columns with potential nulls**
   ```python
   # GOOD: explicit null handling
   F.coalesce(F.col('preferred_name'), F.col('first_name'), F.lit('Unknown'))
   
   # BAD: assumes non-null without validation
   F.col('preferred_name')
   ```

2. **LEFT JOIN outputs**
   - Right-side columns from LEFT JOIN may be null — always handle explicitly
   ```python
   # After LEFT JOIN: rate_pct may be null
   F.coalesce(F.col('rate_pct'), F.lit(0.0)).alias('rate_pct')
   ```

3. **Division operations**
   ```python
   # GOOD: guard against divide-by-zero
   F.when(F.col('denominator') != 0, F.col('numerator') / F.col('denominator')).otherwise(F.lit(None))
   
   # BAD: unguarded division
   F.col('numerator') / F.col('denominator')
   ```

4. **CAST operations**
   - `CAST(string_col AS INT)` returns null for non-numeric strings — document if business logic expects non-null
   - `CAST(null AS DATE)` returns null — guard if downstream logic requires non-null dates

## D. Data Skew Mitigation (Conditional — Domain Knowledge Driven)

**When to apply**: ONLY if domain knowledge mentions "skewed", "hot key", or join key has known high cardinality imbalance (e.g., 80% of records have same customer_id).

**Salt-key pattern**:
```python
# Salted join: customer_id is skewed per domain knowledge
salt_range = 10
df_large = df_large.withColumn('_salt', (F.rand() * salt_range).cast('int'))
df_small = df_small.crossJoin(
    spark.range(salt_range).withColumnRenamed('id', '_salt')
)
joined = df_large.join(df_small, ['customer_id', '_salt'])
result = joined.drop('_salt')
```

**When NOT to apply**: If domain knowledge does NOT mention skew — do NOT add salt-key pattern. It adds complexity with no benefit for balanced data.

## E. Data Volume & Partition Signals (Feed to Wrapper/Driver Generation)

When `additional_context` (mapping Excel) or domain knowledge provides data volume or partition information, capture it in `session/intent_identification.json` for downstream consumption by wrapper/driver generation agents:

**Signals to extract:**
- Explicit data volume: "1TB daily", "500MB per run", "<1GB total"
- Row count estimates: "50M rows", "10K records per day"
- Partition count: "target 10 partitions", "partition by month"
- Source table size hints: "large table", "lookup table ~5K rows"
- Skew indicators: "80% records on single key", "hot key"

**How these feed downstream:**
- `glue-wrapper-agent` uses volume to set `{{shuffle_partitions}}` in wrapper.py SparkSession config
- `databricks-artefact-agent` uses volume to determine if driver.py needs session-level config overrides
- Both agents use partition info to align write operations and coalesce decisions

## F. Staging & Lineage Break Rules

When `self.staging_path` or `config.staging.checkpoint_path` is available (resolved from config), the transform can write intermediate DataFrames between transformation stages to break deep DAG lineage.

**Path Resolution (platform-specific):**
- **Databricks:** `self.staging_path` → resolved by driver from `environments.<env>.staging.staging_path` (Unity Catalog Volume path)
- **Glue:** `self.staging_path` → `s3://{s3_bucket}/{config.file_locations.staging.staging_path}` (S3 prefix, constructed in `__init__`)

**Checkpoint Path:**
- **Databricks:** `config.staging.checkpoint_path` — read directly by transform (driver logs it only)
- **Glue:** `config.file_locations.spark_checkpoint_dir` — set by wrapper via `spark.sparkContext.setCheckpointDir`

> **⚠️ BLOCKED APIs (Databricks Shared Access Mode / Serverless):**
> - `spark.sparkContext.setCheckpointDir(...)` → raises `[JVM_ATTRIBUTE_NOT_SUPPORTED]`
> - `df.checkpoint()` → requires SparkContext checkpoint dir — same restriction
>
> Do NOT generate code using these APIs for Databricks. Use parquet persist/reload instead.

1. **Lineage Break** (Parquet persist/reload):
   - Use after large joins (both sides >1GB estimated) or 3+ sequential groupBys
   - Pattern:
     ```python
     _lineage_break_path = self.config.get("staging", {}).get("checkpoint_path")
     if _lineage_break_path:
         df.write.mode("overwrite").parquet(f"{_lineage_break_path}/step_name")
         df = self.spark.read.parquet(f"{_lineage_break_path}/step_name")
     ```
   - Breaks DAG lineage — prevents OOM from deep execution plans
   - Compatible with ALL Databricks compute modes (Shared, Serverless, Single User)
   - Do NOT use for small DataFrames or simple single-join pipelines
   - **Activation threshold: total source data >50GB (Day0) or >10GB (Day1)**

2. **Staging writes** (intermediate materialization):
   - Write intermediate DataFrames to `self.staging_path` as parquet between transformation stages
   - Use ONLY when: estimated_size_gb > 100 OR domain knowledge mentions staging/restart/intermediate
   - More aggressive than lineage break — creates persistent files (enables restart from midpoint)
   - ALWAYS use `.mode("overwrite")` to ensure idempotent reruns
   - ALWAYS use subdirectory per step (`/step1_joined`, `/step2_filtered`) for clarity
   ```python
   # Materialize intermediate result to staging (enables restart from midpoint)
   step1_df.write.mode("overwrite").parquet(f"{self.staging_path}/step1_joined")
   step1_df = self.spark.read.parquet(f"{self.staging_path}/step1_joined")
   ```

3. **When NOT to use staging/lineage breaks**:
   - Small pipelines (<10GB total source data, <5 join operations)
   - Simple single-source transformations with no multi-step logic
   - Transactional tables with daily increment <1GB
   - When domain knowledge does NOT mention OOM risk, staging, or intermediate writes

4. **Cleanup responsibility**:
   - Lineage break data: persists at checkpoint_path — treated as ephemeral (overwritten each run)
   - Staging data: persists across runs — pipeline does NOT auto-clean
   - Staging cleanup is operational concern (outside generated code scope)

5. **Glue platform exception**:
   - On Glue, `spark.sparkContext.setCheckpointDir()` and `df.checkpoint()` ARE supported
   - The wrapper sets `spark_checkpoint_dir` via SparkContext — this remains valid for Glue
   - The parquet persist/reload pattern also works on Glue as an alternative
