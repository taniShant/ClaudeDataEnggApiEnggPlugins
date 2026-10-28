---
name: pyspark
description: PySpark engineering knowledge covering DataFrame API, configuration, formats, performance, testing, and approved coding patterns
user-invocable: false
owner: BUK Data Engineering Practice
effective_date: 2026-07-13
review_cadence: quarterly
status: approved
---

# PySpark Engineering Skill

## SparkSession Configuration

Initialise SparkSession once per application entry point. Avoid creating multiple sessions within a single job.

```python
from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .appName("my-data-pipeline")
    .config("spark.sql.adaptive.enabled", "true")
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
    .config("spark.sql.shuffle.partitions", "200")
    .config("spark.sql.parquet.datetimeRebaseModeInWrite", "CORRECTED")
    .getOrCreate()
)
```

Set `spark.sql.adaptive.enabled` to `true` in all production jobs to enable Adaptive Query Execution (AQE).

## DataFrame API Patterns

Prefer the DataFrame API over the RDD API for all tabular data processing.

```python
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, LongType, TimestampType

# Prefer method chaining for readability
result = (
    df
    .filter(F.col("status") == "ACTIVE")
    .withColumn("processed_at", F.current_timestamp())
    .select("id", "name", "status", "processed_at")
)

# Column references: prefer F.col() over string column names in complex expressions
df.filter(F.col("amount") > 0)

# Avoid lambda-style column expressions that mask intent
# Bad: df.filter(lambda row: row["amount"] > 0)
# Good: df.filter(F.col("amount") > 0)
```

## Read/Write Formats

### Parquet
```python
# Read
df = spark.read.parquet("s3://bucket/path/to/data/")

# Write with partitioning
(
    df.write
    .mode("overwrite")
    .partitionBy("year", "month")
    .parquet("s3://bucket/path/to/output/")
)
```

### Delta
```python
# Read
df = spark.read.format("delta").load("s3://bucket/path/to/delta-table/")

# Write with merge schema
(
    df.write
    .format("delta")
    .mode("append")
    .option("mergeSchema", "true")
    .save("s3://bucket/path/to/delta-table/")
)
```

### Avro
```python
# Requires spark-avro package on classpath
df = spark.read.format("avro").load("s3://bucket/path/to/avro/")

(
    df.write
    .format("avro")
    .mode("overwrite")
    .save("s3://bucket/path/to/output/")
)
```

### CSV / JSON
```python
# CSV: always specify schema to avoid costly schema inference pass
schema = StructType([
    StructField("id", LongType(), nullable=False),
    StructField("name", StringType(), nullable=True),
])

df = spark.read.schema(schema).option("header", "true").csv("s3://bucket/path/")

# JSON: enforce schema for production reads
df = spark.read.schema(schema).json("s3://bucket/path/")
```

Always specify an explicit schema when reading CSV or JSON in production. Do not rely on `inferSchema=True` in production pipelines.

## Partitioning Strategies

- Partition by columns used in downstream filter/join predicates (e.g. `year`, `month`, `day`, `region`).
- Avoid high-cardinality partition columns (e.g. `user_id`); aim for partition counts of dozens to low hundreds per job run.
- Target file sizes of 128 MB–1 GB per output file for efficient downstream reads.
- Use `repartition(n, col)` before writing when you need a specific number of output files or partition layout; use `coalesce(n)` only to reduce partition count without a full shuffle.

```python
# Repartition before writing for controlled output file count
df.repartition(50, F.col("region")).write.partitionBy("region").parquet(output_path)
```

## Broadcast Joins

Use broadcast joins when one side of the join is small enough to fit in executor memory (typically < 10 MB by default, tunable via `spark.sql.autoBroadcastJoinThreshold`).

```python
from pyspark.sql.functions import broadcast

result = large_df.join(broadcast(small_df), on="key", how="inner")
```

Disable auto-broadcast for a specific join if it causes memory pressure:
```python
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", -1)
```

## UDFs — Use Sparingly

Avoid Python UDFs on performance-critical paths. Python UDFs serialise each row through the Python interpreter, bypassing Catalyst and Tungsten optimisations.

Prefer built-in Spark SQL functions (`pyspark.sql.functions`) in all cases. Fall back to UDFs only when no built-in equivalent exists.

```python
# Bad: Python UDF for a simple string operation
from pyspark.sql.types import StringType
upper_udf = F.udf(lambda s: s.upper() if s else None, StringType())
df.withColumn("upper_name", upper_udf(F.col("name")))

# Good: built-in function
df.withColumn("upper_name", F.upper(F.col("name")))
```

When a UDF is unavoidable, prefer Pandas UDFs (vectorised UDFs) over row-level Python UDFs:

```python
from pyspark.sql.functions import pandas_udf
import pandas as pd

@pandas_udf("double")
def score_series(series: pd.Series) -> pd.Series:
    return series * 1.5

df.withColumn("score", score_series(F.col("raw_score")))
```

## Caching and Persistence

Cache DataFrames that are reused multiple times within the same job to avoid recomputation.

```python
from pyspark import StorageLevel

# Default cache (memory and disk)
df.cache()

# Explicit storage level
df.persist(StorageLevel.MEMORY_AND_DISK)

# Always unpersist when no longer needed
df.unpersist()
```

Do not cache DataFrames that are used only once. Excessive caching wastes memory and can cause spill.

## Error Handling Patterns

```python
# Use try/except around Spark actions (writes, counts, collects on small results)
try:
    df.write.mode("overwrite").parquet(output_path)
except Exception as exc:
    logger.error("Write failed: %s", exc, exc_info=True)
    raise

# Capture bad records during read
df = (
    spark.read
    .option("mode", "PERMISSIVE")
    .option("columnNameOfCorruptRecord", "_corrupt_record")
    .schema(schema)
    .csv(input_path)
)

bad_records = df.filter(F.col("_corrupt_record").isNotNull())
bad_records.write.mode("append").text(dead_letter_path)
```

## Schema Evolution

For Delta tables, use `mergeSchema` option to add new columns safely. For incompatible schema changes (type changes, column drops), perform explicit schema migration steps and document breaking changes.

```python
# Append with new columns
df.write.format("delta").mode("append").option("mergeSchema", "true").save(path)

# Overwrite and rewrite schema
df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(path)
```

## Testing

Use `pyspark.testing` (Spark >= 3.1) or the `chispa` library for DataFrame equality assertions.

```python
# pyspark.testing
from pyspark.testing.utils import assertDataFrameEqual

assertDataFrameEqual(actual_df, expected_df, checkRowOrder=False)

# chispa
from chispa.dataframe_comparer import assert_df_equality

assert_df_equality(actual_df, expected_df, ignore_row_order=True, ignore_nullable=True)
```

Create a shared `SparkSession` fixture at module or session scope in `conftest.py` to avoid per-test session startup cost:

```python
# conftest.py
import pytest
from pyspark.sql import SparkSession

@pytest.fixture(scope="session")
def spark():
    return (
        SparkSession.builder
        .master("local[2]")
        .appName("test")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )
```

## Observability

### Spark UI Metrics
- **Jobs/Stages tab**: identify slow stages, high task skew, spill.
- **SQL tab**: visualise physical plan, identify missing predicate pushdown.
- **Storage tab**: monitor cached RDD/DataFrame sizes.
- **Executors tab**: track GC time, spill to disk, peak memory.

### Custom Accumulators
```python
from pyspark.accumulators import AccumulatorParam

# Built-in integer accumulator
bad_record_count = spark.sparkContext.accumulator(0)

def process_row(row):
    if row["amount"] is None:
        bad_record_count.add(1)
    # ...

# Accumulators are reliable only for side-effect tracking, not for correctness logic
```

## Performance Patterns

### Predicate Pushdown
Ensure filters are applied as close to the data source as possible. Parquet and Delta readers support column pruning and predicate pushdown natively.

```python
# Spark will push this filter down to the Parquet reader
df = spark.read.parquet(path).filter(F.col("region") == "UK")
```

Avoid operations that break predicate pushdown (e.g. applying a UDF before a filter).

### Partition Pruning
When reading partitioned data, filter on the partition column before any joins or aggregations to minimise data scanned.

### Adaptive Query Execution (AQE)
Enable AQE to allow runtime coalescing of shuffle partitions, dynamic join strategy switching, and skew join optimisation:

```python
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
```

### Skew Handling
When a join key has heavily skewed distribution, use AQE skew join handling or apply salting:

```python
import random

SALT_FACTOR = 10

# Salt the large side
large_df = large_df.withColumn("salt", (F.rand() * SALT_FACTOR).cast("int"))
large_df = large_df.withColumn("salted_key", F.concat(F.col("key"), F.lit("_"), F.col("salt")))

# Explode the small side
small_df_exploded = small_df.withColumn("salt", F.explode(F.array([F.lit(i) for i in range(SALT_FACTOR)])))
small_df_exploded = small_df_exploded.withColumn("salted_key", F.concat(F.col("key"), F.lit("_"), F.col("salt")))

result = large_df.join(small_df_exploded, on="salted_key", how="inner")
```

## Idempotent Writes

Writes must be idempotent to support safe retries.

- Use `mode("overwrite")` with `partitionOverwriteMode = "dynamic"` to replace only affected partitions.
- For Delta tables, use `MERGE INTO` to upsert rather than blind overwrites.
- Include a unique job run ID or watermark in output to enable deduplication.

```python
spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")
df.write.mode("overwrite").partitionBy("year", "month").parquet(output_path)
```

## Checkpoint and Recovery

Use checkpointing for long lineage chains and streaming jobs to truncate lineage and enable recovery from a known good state.

```python
spark.sparkContext.setCheckpointDir("s3://bucket/checkpoints/")

# Truncate long lineage
df_checkpointed = df.checkpoint()
```

For Structured Streaming, always configure a checkpoint location:

```python
(
    query_df.writeStream
    .format("delta")
    .option("checkpointLocation", "s3://bucket/checkpoints/my-stream/")
    .outputMode("append")
    .start(output_path)
)
```

## Hive Metastore Integration

```python
# Register as a Hive table
df.write.mode("overwrite").saveAsTable("database.table_name")

# Read from Hive
df = spark.table("database.table_name")

# Repair partitions after manual write
spark.sql("MSCK REPAIR TABLE database.table_name")
```

## Approved Coding Patterns

| Pattern | Guidance |
|---|---|
| `collect()` on large DataFrames | NEVER. Use `.show()`, `.limit()`, or write to storage instead. `collect()` pulls all data to the driver and will OOM on large datasets. |
| Python UDFs on performance-critical paths | AVOID. Use built-in Spark SQL functions. Use Pandas UDFs only when no built-in alternative exists. |
| `inferSchema` on CSV/JSON in production | NEVER. Always define an explicit schema. |
| `SELECT *` in Spark SQL / `df.select("*")` | AVOID in production. Always project only required columns to enable column pruning. |
| Nested `for` loops over DataFrames | NEVER. Apply transformations as DataFrame operations, not Python iterations. |
| Printing DataFrames with `print()` | AVOID in production code. Use `df.show()` for debugging only; never in production pipelines. |
| Hardcoded paths and credentials | NEVER. Use configuration injection and Secrets management. |
| Spark SQL string interpolation with user input | NEVER. Use parameterised expressions or `F.col()` references. |
