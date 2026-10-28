---
name: performance-engineering
description: Performance engineering knowledge covering query plan analysis, indexing, partitioning, caching, file formats, skew, and regression testing
user-invocable: false
owner: BUK Data Engineering Practice
effective_date: 2026-07-13
review_cadence: quarterly
status: approved
---

# Performance Engineering Skill

## Query Plan Analysis

Understanding the query execution plan is the first step in any performance investigation. Always obtain and analyse the plan before making changes.

### PostgreSQL

```sql
-- Estimated plan (fast; no data read)
EXPLAIN SELECT * FROM finance.transactions WHERE account_id = 42;

-- Actual execution plan with timing and buffer stats
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT t.*, a.account_holder_id
FROM finance.transactions t
JOIN core.accounts a ON t.account_id = a.account_id
WHERE t.transaction_ts >= NOW() - INTERVAL '30 days';
```

Key plan nodes to recognise:
| Node | Meaning |
|---|---|
| `Seq Scan` | Full table scan; investigate if table is large |
| `Index Scan` | Uses an index; good |
| `Index Only Scan` | Index covers all required columns; best case |
| `Bitmap Heap Scan` | Combines multiple index scans; often good |
| `Hash Join` | In-memory hash join; good for large unsorted inputs |
| `Nested Loop` | Row-by-row lookup; only efficient if inner side is very small or indexed |
| `Merge Join` | Requires sorted inputs; good for pre-sorted data |
| `Sort` | Explicit sort operation; may indicate missing index |
| `Hash Aggregate` | Hash-based aggregation; good |
| `GroupAggregate` | Sort-based aggregation; requires sorted input |

### Key Metrics in EXPLAIN ANALYZE Output
- **rows**: actual rows returned vs estimated rows. A large discrepancy indicates stale statistics.
- **loops**: number of times the node was executed (in nested loops, the inner node loops per outer row).
- **actual time**: total time in milliseconds.
- **Buffers: shared hit/read**: pages read from cache vs from disk. High `read` values indicate an I/O bottleneck.
- **Planning time vs Execution time**: high planning time may indicate complex parameterisation or stale statistics.

### Spark SQL
```python
# Logical and physical plan
df.explain(extended=True)

# Formatted plan (Spark 3.x)
df.explain(mode="formatted")

# Cost-based plan
df.explain(mode="cost")
```

In the Spark UI, navigate to the SQL tab to view the physical plan as a DAG. Key things to check:
- Presence of `FileScan` with partition filters applied (predicate pushdown working).
- Exchange (shuffle) operations — minimise by co-partitioning joining datasets.
- Sort operations — necessary for merge joins and range partitioning.
- Broadcast join hints applied correctly.
- AQE coalesced partition counts.

### Athena / Presto
```sql
EXPLAIN SELECT * FROM raw.transactions WHERE year = 2026 AND month = 7;
```

Look for `TableScan` with `predicate` showing partition filters applied. If partition filters are absent, the query will scan all partitions.

---

## Index Selection

### B-tree Indexes
The default PostgreSQL index type. Supports equality (`=`), range (`<`, `>`, `BETWEEN`), prefix matching (`LIKE 'abc%'`), and `IS NULL`.

```sql
-- Single-column index
CREATE INDEX idx_transactions_account_id ON finance.transactions (account_id);

-- Multi-column (composite) index: most selective column first, or follow query WHERE clause order
CREATE INDEX idx_transactions_account_ts ON finance.transactions (account_id, transaction_ts DESC);
```

For a composite index `(a, b)`:
- Queries filtering on `a` alone: index used.
- Queries filtering on `a AND b`: index used optimally.
- Queries filtering on `b` alone: index NOT used (leading column rule).

### Hash Indexes
Suitable only for equality predicates. Not useful for range queries. Smaller than B-tree for pure equality use cases (PostgreSQL 10+).

```sql
CREATE INDEX idx_transactions_hash_ref ON finance.transactions USING HASH (transaction_ref);
```

### GIN Indexes (PostgreSQL)
Suitable for full-text search, JSONB, array containment.

```sql
CREATE INDEX idx_metadata_gin ON finance.transactions USING GIN (metadata jsonb_path_ops);

-- Query using the GIN index
SELECT * FROM finance.transactions WHERE metadata @> '{"type": "payment"}';
```

### GiST Indexes (PostgreSQL)
Suitable for geometric, range, and full-text data types.

```sql
CREATE INDEX idx_valid_period ON contracts USING GIST (valid_period);

-- Query using GiST
SELECT * FROM contracts WHERE valid_period @> CURRENT_DATE;
```

### Covering Indexes (INCLUDE)
Include non-key columns to enable index-only scans. Particularly useful when the query projects a small number of columns.

```sql
CREATE INDEX idx_transactions_covering
    ON finance.transactions (account_id, transaction_ts DESC)
    INCLUDE (amount, currency);
-- Query projecting only (account_id, transaction_ts, amount, currency) can use index-only scan
```

### Partial Indexes
Index a subset of rows. Smaller index size; faster range scans on the filtered subset.

```sql
-- Only index unprocessed transactions (usually a small fraction)
CREATE INDEX idx_transactions_pending
    ON finance.transactions (account_id)
    WHERE processed_flag = FALSE;
```

### Index-Only Scans
Occur when the index covers all projected columns and the visibility map confirms the page is fully visible. Check `pg_stat_user_tables.n_live_tup` and run `VACUUM` regularly to maintain visibility maps.

### Index Maintenance
```sql
-- Identify unused indexes (PostgreSQL)
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS scans_since_last_reset
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY schemaname, tablename;

-- Rebuild bloated indexes
REINDEX INDEX CONCURRENTLY idx_transactions_account_id;
```

---

## Partitioning Strategies

### Range Partitioning
Partition by a continuous range (e.g. date, numeric ID). Most common for time-series and event data.

```sql
CREATE TABLE finance.transactions (
    transaction_id  BIGINT    NOT NULL,
    transaction_ts  TIMESTAMP NOT NULL
) PARTITION BY RANGE (transaction_ts);

CREATE TABLE finance.transactions_2026_q3
    PARTITION OF finance.transactions
    FOR VALUES FROM ('2026-07-01') TO ('2026-10-01');
```

### List Partitioning
Partition by a discrete set of values (e.g. region, product type).

```sql
CREATE TABLE finance.transactions PARTITION BY LIST (region);

CREATE TABLE finance.transactions_uk
    PARTITION OF finance.transactions
    FOR VALUES IN ('UK');

CREATE TABLE finance.transactions_us
    PARTITION OF finance.transactions
    FOR VALUES IN ('US');
```

### Hash Partitioning
Distribute rows evenly across a fixed number of partitions using a hash of the partition key. Useful for high-cardinality keys where range and list partitioning are not meaningful.

```sql
CREATE TABLE finance.transactions PARTITION BY HASH (account_id);

CREATE TABLE finance.transactions_p0
    PARTITION OF finance.transactions
    FOR VALUES WITH (MODULUS 4, REMAINDER 0);
-- ... partitions p1, p2, p3
```

### Composite Partitioning
Combine partitioning strategies (e.g. range by date, then hash by account_id for hot partitions).

### Partition Pruning
The query planner eliminates irrelevant partitions when the `WHERE` clause matches the partition key.

```sql
-- Partition pruning active: only 2026 Q3 partition scanned
SELECT * FROM finance.transactions
WHERE transaction_ts BETWEEN '2026-07-01' AND '2026-09-30';
```

Always verify partition pruning is occurring via `EXPLAIN`. If the planner cannot determine partition bounds at plan time (e.g. due to a parameterised query), enable run-time partition pruning (`enable_partition_pruning = on`).

---

## Clustering and Sort Keys

In column-store databases (Redshift, BigQuery, Spark with bucketing), the physical sort order of data on disk significantly impacts range scan performance.

```sql
-- Redshift: sort key
CREATE TABLE finance.transactions (
    transaction_id  BIGINT,
    account_id      BIGINT,
    transaction_ts  TIMESTAMP
)
SORTKEY (transaction_ts, account_id);

-- Spark: bucket by join/filter key (write time)
df.write.bucketBy(128, "account_id").sortBy("transaction_ts").saveAsTable("finance.transactions")
```

Z-ORDER and liquid clustering in Delta Lake achieve co-location of related data without requiring repartitioning:
```sql
OPTIMIZE finance.transactions ZORDER BY (account_id, transaction_ts);
```

---

## Statistics and Cardinality Estimation

Query planners use column statistics to estimate row counts and choose join strategies. Stale statistics lead to poor plans (e.g. nested loop instead of hash join, underestimated memory allocation).

```sql
-- PostgreSQL: update statistics on a table
ANALYZE finance.transactions;

-- PostgreSQL: increase statistics target for a column with high cardinality
ALTER TABLE finance.transactions ALTER COLUMN account_id SET STATISTICS 500;

-- Spark SQL: compute statistics for CBO
ANALYZE TABLE finance.transactions COMPUTE STATISTICS FOR ALL COLUMNS;
```

---

## Join Algorithms

| Algorithm | Best For | Requires | Notes |
|---|---|---|---|
| Nested Loop | Small inner side with an index | Index on join key of inner relation | O(n*m) without index; O(n log m) with index |
| Hash Join | Large unsorted inputs | Enough memory for build side hash table | Default for most large joins in Postgres, Spark |
| Merge Join | Pre-sorted inputs | Sorted or indexed input on both sides | Efficient when inputs are already sorted |
| Broadcast Join (Spark) | One small side | Small table fits in executor memory | Eliminates shuffle; set threshold via config |
| Shuffle Hash Join (Spark) | Both sides medium | Memory for partition hash table | Fallback when sort-merge is too expensive |
| Sort-Merge Join (Spark) | Large-large joins | Shuffle and sort both sides | Default for large joins in Spark |

```python
# Force broadcast join in Spark
from pyspark.sql.functions import broadcast
result = large_df.join(broadcast(lookup_df), on="id", how="inner")

# Hint in Spark SQL
spark.sql("SELECT /*+ BROADCAST(small_table) */ * FROM large_table JOIN small_table USING (id)")
```

---

## Shuffle Optimisation (Spark)

Shuffles (Exchange operations) are the most expensive operations in Spark. Minimise and optimise them:

```python
# Set shuffle partitions based on data size (default 200 is often wrong)
spark.conf.set("spark.sql.shuffle.partitions", "400")

# AQE auto-coalesces shuffle partitions at runtime
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")

# Repartition by join key before a known expensive join to avoid double shuffle
df1 = df1.repartition(400, F.col("account_id"))
df2 = df2.repartition(400, F.col("account_id"))
result = df1.join(df2, on="account_id", how="inner")

# Coalesce to reduce partitions without shuffle (only use to decrease partition count)
df.coalesce(50).write.parquet(output_path)
```

Bucketing pre-partitions tables on disk, eliminating the shuffle on join and aggregation:
```python
df.write.bucketBy(256, "account_id").sortBy("account_id").saveAsTable("bucketed_transactions")
```

---

## Caching Strategies

### Materialised Views (PostgreSQL)
Pre-compute expensive query results. Refresh on a schedule or on demand.

```sql
CREATE MATERIALIZED VIEW reporting.mv_daily_spend AS
SELECT DATE_TRUNC('day', transaction_ts) AS day, account_id, SUM(amount) AS total
FROM finance.transactions
GROUP BY 1, 2
WITH DATA;

CREATE UNIQUE INDEX ON reporting.mv_daily_spend (day, account_id);

-- Concurrent refresh (non-blocking; requires unique index)
REFRESH MATERIALIZED VIEW CONCURRENTLY reporting.mv_daily_spend;
```

### Result Cache
Some query engines (Redshift, BigQuery, Athena) cache identical query results for a configurable period. Enable result caching for dashboards and frequently repeated analytical queries.

### Application Cache
Cache reference/lookup data (e.g. exchange rates, product codes) in application memory or a Redis/ElastiCache layer rather than querying the database on every request.

### Spark DataFrame Caching
```python
# Cache when a DataFrame is used multiple times
df.cache()
# Or with explicit storage level
df.persist(StorageLevel.MEMORY_AND_DISK)
# Release when done
df.unpersist()
```

---

## File Format Optimisation

### Columnar vs Row Formats

| Format | Type | Compression | Predicate Pushdown | Best For |
|---|---|---|---|---|
| Parquet | Columnar | Yes (Snappy, ZSTD, GZIP) | Yes | Analytics; projection-heavy queries |
| ORC | Columnar | Yes (ZLIB, Snappy) | Yes | Hive ecosystem; analytics |
| Avro | Row | Yes (Snappy, Deflate) | No | Serialisation; Kafka messages; schema evolution |
| CSV | Row | Optional | No | External exchange only |
| JSON | Row | Optional | No | External exchange; debugging |
| Delta Lake | Columnar (Parquet + log) | Yes | Yes (+ data skipping) | ACID transactions; upsert workloads |

Use **Parquet** or **Delta** for all analytical pipeline storage. Never use CSV or JSON as the primary storage format for data at scale.

### Compression Codecs

| Codec | Ratio | Speed | Splittable |
|---|---|---|---|
| Snappy | Medium | Fast | Yes (with Parquet/ORC) |
| ZSTD | High | Fast | Yes |
| GZIP | High | Slow | No (raw; yes within Parquet) |
| LZ4 | Low | Very fast | Yes |

Prefer **Snappy** for general use (balanced ratio and speed). Prefer **ZSTD** when storage cost reduction is a priority.

### Block and Row Group Sizes
- Parquet row group size: default 128 MB. Increase to 512 MB or 1 GB for analytics-only workloads to improve compression and reduce metadata overhead.
- Target output file sizes of 128 MB–1 GB. Files smaller than 16 MB create excessive metadata overhead and slow down Athena/Glue scans.

---

## Data Skew Detection and Mitigation

Data skew occurs when one partition or key value contains significantly more data than others, causing one task to take disproportionately longer (straggler tasks).

### Detection
```python
# Check partition sizes
df.groupBy(F.spark_partition_id()).count().orderBy(F.desc("count")).show(20)

# Check key distribution
df.groupBy("join_key").count().orderBy(F.desc("count")).show(20)
```

In the Spark UI: look for task duration distribution in the Stages tab. A straggler task (one task much slower than others) indicates skew.

### Mitigation

1. **AQE Skew Join** (Spark 3.x+): automatically splits skewed partitions.
```python
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.skewedPartitionFactor", "5")
spark.conf.set("spark.sql.adaptive.skewJoin.skewedPartitionThresholdInBytes", "256MB")
```

2. **Salting**: manually add randomness to the skewed key.
```python
SALT_N = 10
skewed_df = skewed_df.withColumn("salt", (F.rand() * SALT_N).cast("int"))
skewed_df = skewed_df.withColumn("salted_key", F.concat(F.col("key"), F.lit("_"), F.col("salt")))
small_df = small_df.withColumn("salt", F.explode(F.array([F.lit(i) for i in range(SALT_N)])))
small_df = small_df.withColumn("salted_key", F.concat(F.col("key"), F.lit("_"), F.col("salt")))
result = skewed_df.join(small_df, on="salted_key")
```

3. **Broadcast join**: if one side is small, broadcast it to eliminate the shuffle entirely.

4. **Repartition by additional key**: add a secondary key to spread the skewed key across more partitions.

---

## Connection Pooling

For JDBC/ODBC data sources, always use a connection pool rather than creating a new connection per query.

```python
# SQLAlchemy connection pool (PostgreSQL)
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql+psycopg2://user:pass@host:5432/db",
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_pre_ping=True,  # verify connection before use
)
```

For Spark JDBC reads, partition the read across multiple connections to parallelise ingestion:
```python
df = (
    spark.read.format("jdbc")
    .option("url", jdbc_url)
    .option("dbtable", "finance.transactions")
    .option("partitionColumn", "transaction_id")
    .option("lowerBound", "1")
    .option("upperBound", "10000000")
    .option("numPartitions", "20")
    .load()
)
```

---

## Query Rewriting Patterns

### Replace Correlated Subquery with JOIN
```sql
-- Before: correlated subquery (executes once per outer row)
SELECT account_id, amount
FROM finance.transactions t
WHERE amount > (
    SELECT AVG(amount) FROM finance.transactions WHERE account_id = t.account_id
);

-- After: window function (single pass)
SELECT account_id, amount
FROM (
    SELECT account_id, amount,
           AVG(amount) OVER (PARTITION BY account_id) AS avg_amount
    FROM finance.transactions
) sub
WHERE amount > avg_amount;
```

### Replace `NOT IN` with `NOT EXISTS` (for nullable subquery results)
```sql
-- Before: NOT IN returns no rows if subquery has any NULL
SELECT * FROM accounts WHERE account_id NOT IN (SELECT account_id FROM closed_accounts);

-- After: NOT EXISTS is NULL-safe
SELECT * FROM accounts a
WHERE NOT EXISTS (
    SELECT 1 FROM closed_accounts ca WHERE ca.account_id = a.account_id
);
```

### Avoid Functions on Indexed Columns
```sql
-- Before: function prevents index use
SELECT * FROM transactions WHERE EXTRACT(YEAR FROM transaction_ts) = 2026;

-- After: range predicate allows index/partition use
SELECT * FROM transactions
WHERE transaction_ts >= '2026-01-01' AND transaction_ts < '2027-01-01';
```

---

## Batch Size Tuning

For batch insert/update operations, the optimal batch size balances:
- Transaction overhead (smaller batches = more commits = more overhead).
- Memory consumption (larger batches = more memory per transaction).
- Lock contention (larger batches hold locks longer).

General guidance:
- Start with batch sizes of 1,000–10,000 rows for OLTP inserts.
- Test incrementally and measure throughput (rows/s) and transaction duration.
- For bulk loads into analytics systems (Redshift, Snowflake), prefer single large transactions.
- For Spark JDBC writes, set `batchsize` option:
```python
df.write.format("jdbc").option("batchsize", 10000).save()
```

---

## Parallelism Configuration

### PostgreSQL
```sql
-- Maximum parallel workers per query
SET max_parallel_workers_per_gather = 4;

-- Minimum table size to enable parallelism
SET min_parallel_table_scan_size = '8MB';
SET min_parallel_index_scan_size = '512kB';
```

### Spark
```python
# Default parallelism for RDD operations
spark.conf.set("spark.default.parallelism", "200")

# Shuffle partitions (affects post-shuffle stages)
spark.conf.set("spark.sql.shuffle.partitions", "400")

# Number of executor cores
# Set in cluster config: spark.executor.cores = 4
```

---

## Memory and Spill Management

### PostgreSQL
```sql
-- Work memory per sort/hash operation (per query, may be multiplied by concurrent operations)
SET work_mem = '256MB';

-- Maintenance work memory (for VACUUM, CREATE INDEX)
SET maintenance_work_mem = '1GB';
```

### Spark
```python
# Fraction of executor memory for storage (cached DataFrames)
spark.conf.set("spark.memory.storageFraction", "0.3")

# Enable disk spill for sorts and aggregations (default is true)
# Monitor via Spark UI: Spill (Memory) and Spill (Disk) in Stage details

# Increase executor memory to reduce spill
# Set in cluster config: spark.executor.memory = 16g
# Set overhead: spark.executor.memoryOverhead = 4g
```

When spill is observed in Spark:
1. Increase `spark.executor.memory`.
2. Reduce `spark.sql.shuffle.partitions` to increase data per partition (or increase it to reduce partition size if the issue is total memory).
3. Use AQE to dynamically coalesce partitions.

---

## Regression Testing Methodology

Performance regression testing ensures that code or data changes do not degrade pipeline performance.

### Methodology
1. **Baseline capture**: before any change, record execution time, data scanned, rows processed, and resource consumption (CPU, memory, I/O) for each pipeline or query under test.
2. **Define thresholds**: agree acceptable regression tolerances (e.g. execution time must not increase by more than 10%; data scanned must not increase by more than 5%).
3. **Reproduce in CI**: run benchmarks against representative data volumes in CI pipelines. Do not benchmark against small test datasets.
4. **Compare**: after the change, compare results against the baseline using the agreed thresholds.
5. **Investigate regressions**: for any breach, produce EXPLAIN output before and after and identify the changed plan node.
6. **Document**: record baseline metrics in version control alongside the query or pipeline definition.

### Tooling
- PostgreSQL: `pg_stat_statements` extension for query-level CPU time and total calls.
- Spark: Spark History Server for job-level duration, shuffle read/write, spill.
- Athena: `SHOW STATS FOR` and query execution statistics from the Athena console or API.
