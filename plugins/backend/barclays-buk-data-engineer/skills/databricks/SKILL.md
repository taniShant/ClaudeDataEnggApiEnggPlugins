---
name: databricks
description: Databricks engineering knowledge covering Unity Catalog, Delta Lake, Workflows, DLT, Structured Streaming, and approved patterns
user-invocable: false
owner: BUK Data Engineering Practice
effective_date: 2026-07-13
review_cadence: quarterly
status: approved
---

# Databricks Engineering Skill

> **Important notice**: This skill provides factual capability and constraint evidence for Databricks. It must NOT be used to score Databricks more favourably than alternative platforms in any technology decision or evaluation. Technology selection must follow the BUK platform governance process.

## Unity Catalog

### Three-Level Namespace
Unity Catalog organises all data assets using a three-level namespace: `catalog.schema.table`.

```sql
-- Create catalog
CREATE CATALOG IF NOT EXISTS finance_prod;

-- Create schema (database)
CREATE SCHEMA IF NOT EXISTS finance_prod.transactions;

-- Create table within the catalog
CREATE TABLE IF NOT EXISTS finance_prod.transactions.raw_payments (
    payment_id   BIGINT NOT NULL,
    account_id   BIGINT NOT NULL,
    amount       DECIMAL(18, 2),
    currency     STRING,
    event_ts     TIMESTAMP
)
USING DELTA
PARTITIONED BY (DATE(event_ts));

-- Query
SELECT * FROM finance_prod.transactions.raw_payments WHERE DATE(event_ts) = '2026-07-13';
```

### Access Control
Unity Catalog implements ANSI SQL-style privileges. Manage grants at the catalog, schema, or table level.

```sql
-- Grant read access on a schema to a group
GRANT USE CATALOG ON CATALOG finance_prod TO `data-analysts`;
GRANT USE SCHEMA  ON SCHEMA  finance_prod.transactions TO `data-analysts`;
GRANT SELECT      ON TABLE   finance_prod.transactions.raw_payments TO `data-analysts`;

-- Grant data engineering write access
GRANT CREATE, MODIFY ON SCHEMA finance_prod.transactions TO `data-engineers`;

-- Row and column-level security via dynamic views or column masks (Unity Catalog)
```

### Data Lineage
Unity Catalog captures column-level lineage automatically for SQL and Delta operations. Lineage is available in the Catalog Explorer UI and via the Lineage API. Preserve lineage by always writing to tables (not raw file paths) from notebooks and jobs.

---

## Delta Lake

### ACID Transactions
Delta Lake provides ACID transactions on top of Parquet files stored in cloud object storage. All reads and writes go through the Delta transaction log (`_delta_log/`).

```python
# Write — always use Delta format for managed or external tables in Databricks
df.write.format("delta").mode("overwrite").saveAsTable("finance_prod.transactions.payments")

# Append
df.write.format("delta").mode("append").saveAsTable("finance_prod.transactions.payments")
```

### Time Travel
```sql
-- Query a previous version
SELECT * FROM finance_prod.transactions.payments VERSION AS OF 42;

-- Query by timestamp
SELECT * FROM finance_prod.transactions.payments TIMESTAMP AS OF '2026-07-01T00:00:00';

-- Restore to a previous version
RESTORE TABLE finance_prod.transactions.payments TO VERSION AS OF 42;
```

```python
# PySpark time travel
df = spark.read.format("delta").option("versionAsOf", 42).load(table_path)
```

### OPTIMIZE and Z-ORDER
```sql
-- Compact small files
OPTIMIZE finance_prod.transactions.payments;

-- Z-ORDER by frequently filtered columns for improved query performance
OPTIMIZE finance_prod.transactions.payments ZORDER BY (account_id, event_ts);
```

Run `OPTIMIZE` on a scheduled basis (e.g. nightly or after large batch loads). Z-ORDER benefits degrade after each write and must be re-applied.

### VACUUM
```sql
-- Remove files older than the retention threshold (default 7 days)
VACUUM finance_prod.transactions.payments;

-- Remove files older than a specific threshold (minimum 7 days to protect time travel)
VACUUM finance_prod.transactions.payments RETAIN 168 HOURS;
```

Never set the VACUUM retention period below 7 days without disabling the safety check. Doing so can corrupt streaming checkpoints and time-travel queries that are still referencing older versions.

### Liquid Clustering
Liquid clustering is the recommended replacement for static partitioning on Delta tables. It re-clusters data incrementally without a full rewrite.

```sql
-- Create a table with liquid clustering
CREATE TABLE finance_prod.transactions.payments
CLUSTER BY (account_id, DATE(event_ts))
AS SELECT * FROM staging.payments;

-- Incrementally re-cluster after writes
OPTIMIZE finance_prod.transactions.payments;
```

Use liquid clustering instead of `PARTITIONED BY` for new tables where the partition key has moderate-to-high cardinality or where the access pattern is multi-dimensional.

### Change Data Feed (CDF)
Change Data Feed exposes row-level change records (insert, update, delete) for Delta tables.

```sql
-- Enable on an existing table
ALTER TABLE finance_prod.transactions.payments SET TBLPROPERTIES (delta.enableChangeDataFeed = true);
```

```python
# Read changes since version 10
changes = (
    spark.read.format("delta")
    .option("readChangeData", True)
    .option("startingVersion", 10)
    .table("finance_prod.transactions.payments")
)
```

CDF is used for incremental processing pipelines and to feed downstream CDC consumers.

---

## Databricks Workflows

### Jobs and Task Orchestration
Define jobs as code (JSON/YAML via the Databricks CLI or Terraform provider) rather than through the UI for version control and reproducibility.

```yaml
# Example job definition (YAML)
name: daily-payments-pipeline
tasks:
  - task_key: ingest_raw
    notebook_task:
      notebook_path: /Repos/my-team/pipeline/notebooks/ingest_raw
    cluster_key: shared_job_cluster
    timeout_seconds: 1800
    retry_on_timeout: true

  - task_key: transform_payments
    depends_on:
      - task_key: ingest_raw
    python_wheel_task:
      package_name: my_pipeline
      entry_point: transform_payments
    cluster_key: shared_job_cluster

job_clusters:
  - job_cluster_key: shared_job_cluster
    new_cluster:
      spark_version: 14.3.x-scala2.12
      node_type_id: Standard_DS3_v2
      num_workers: 4
      spark_conf:
        spark.sql.adaptive.enabled: "true"
```

### Retry Policies
```yaml
retry_on_timeout: true
max_retries: 2
min_retry_interval_millis: 60000
```

### Cluster Policies
Use cluster policies to enforce governance on cluster configurations:
- Set maximum DBU costs per cluster.
- Restrict allowed instance types.
- Enforce autotermination.
- Pin approved Databricks Runtime versions.

Attach cluster policies to job clusters via policy ID. Do not allow unrestricted all-purpose cluster creation for production jobs.

---

## SQL Warehouses

### Types
| Type | Use Case | Scaling |
|---|---|---|
| Serverless | Interactive analytics, dashboards, dbt | Auto-scale to zero; fastest cold start |
| Classic Pro | Production BI tools, large queries | Manual scaling |
| Classic | General purpose | Manual scaling |

### Serverless SQL Warehouses
Prefer serverless SQL warehouses for BI and analytics workloads:
- Auto-scales to zero when idle (no cost when not in use).
- Faster startup than classic warehouses.
- Managed by Databricks; no cluster configuration required.

### Auto-Scaling
Configure `min_num_clusters` and `max_num_clusters` for classic warehouses to handle variable concurrency without over-provisioning.

---

## Notebooks

**Notebooks are not for production pipelines.** Use notebooks only for:
- Exploration and ad-hoc analysis.
- Development and debugging.
- Documentation with embedded code (clearly marked as non-production).

Production logic must be packaged as Python wheels, Spark SQL scripts, or DLT pipelines and executed via Databricks Workflows.

---

## Delta Live Tables (DLT)

### Concepts
DLT is a declarative framework for building reliable, maintainable batch and streaming data pipelines on Delta Lake.

- **Streaming tables**: continuously ingest and process data from streaming sources.
- **Materialized views**: computed from batch or streaming sources; refreshed on each pipeline run.
- **Expectations**: data quality constraints evaluated at runtime.

### Pipeline Definition
```python
import dlt
from pyspark.sql.functions import col, current_timestamp

# Streaming table — ingest from Auto Loader
@dlt.table(
    name="raw_payments",
    comment="Raw ingested payment events from S3",
    partition_cols=["event_date"],
)
def raw_payments():
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", "/mnt/schema/raw_payments/")
        .load("/mnt/landing/payments/")
        .withColumn("event_date", col("event_ts").cast("date"))
        .withColumn("ingested_at", current_timestamp())
    )


# Materialized view with expectations
@dlt.table(name="clean_payments", comment="Validated and cleansed payment records")
@dlt.expect_or_drop("valid_amount", "amount > 0")
@dlt.expect("non_null_account", "account_id IS NOT NULL")
@dlt.expect_or_fail("valid_currency", "currency IN ('GBP', 'USD', 'EUR')")
def clean_payments():
    return dlt.read_stream("raw_payments").filter(col("event_date") >= "2024-01-01")
```

### Expectation Policies
| Policy | Behaviour |
|---|---|
| `@dlt.expect` | Record the violation count; row is retained |
| `@dlt.expect_or_drop` | Drop rows that violate the constraint |
| `@dlt.expect_or_fail` | Fail the pipeline update if any row violates the constraint |

### Pipeline Modes
- **Triggered**: runs once and stops (equivalent to a batch job).
- **Continuous**: runs as a streaming pipeline; processes data as it arrives.

Use triggered mode for SLA-driven batch pipelines. Use continuous mode only when near-real-time latency is required.

---

## Repos — Git Integration

Databricks Repos provides Git-backed notebook and code synchronisation. All production code must reside in Git (not in Databricks Workspace files).

- Use a dedicated service principal for CI/CD automation against Repos.
- Do not commit secrets, credentials, or PII to Repos.
- Use branch-based development; merge to main via a peer-reviewed PR before deploying to production.

---

## Secrets

Never store secrets in notebooks, code, configuration files, or Repos. Always use Databricks Secret Scopes.

```python
# Retrieve a secret — the value is redacted in notebook output
password = dbutils.secrets.get(scope="my-scope", key="db-password")

# List secret keys in a scope (values are never exposed)
dbutils.secrets.list(scope="my-scope")
```

Databricks secret scopes can be backed by:
- **Databricks-managed**: secrets stored in the Databricks control plane.
- **Azure Key Vault-backed**: secrets resolved from Azure Key Vault (preferred in Azure deployments).

---

## Structured Streaming

### foreachBatch
Use `foreachBatch` to apply batch DataFrame operations (e.g. Delta MERGE) on each micro-batch:

```python
def upsert_to_delta(batch_df, batch_id):
    from delta.tables import DeltaTable
    target = DeltaTable.forName(spark, "finance_prod.transactions.payments")
    (
        target.alias("t")
        .merge(batch_df.alias("s"), "t.payment_id = s.payment_id")
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )

(
    stream_df.writeStream
    .format("delta")
    .foreachBatch(upsert_to_delta)
    .option("checkpointLocation", "/mnt/checkpoints/payments-stream/")
    .trigger(processingTime="60 seconds")
    .start()
)
```

### Trigger Modes
| Trigger | Behaviour |
|---|---|
| `processingTime="n seconds"` | Micro-batch at a fixed interval |
| `once=True` | Process all available data then stop |
| `availableNow=True` | Process all available data in multiple batches then stop (better for large backlogs) |
| `continuous="1 second"` | Experimental low-latency continuous processing |

### Checkpoints
Always configure a checkpoint location for every streaming query. Checkpoints store the stream offset and query progress; they are required for recovery after restart.

```python
.option("checkpointLocation", "/mnt/checkpoints/unique-stream-id/")
```

Use a unique checkpoint path per streaming query. Never share a checkpoint directory between queries.

### Watermarks
```python
from pyspark.sql.functions import col

df_with_watermark = (
    stream_df
    .withWatermark("event_ts", "10 minutes")
    .groupBy(
        F.window("event_ts", "5 minutes"),
        col("account_id")
    )
    .sum("amount")
)
```

Watermarks bound the state store size and control when late data is dropped. Always set a watermark on event-time aggregations.

---

## Photon

Photon is Databricks' native vectorised query engine written in C++. It accelerates SQL and DataFrame operations on Delta tables without code changes.

- Photon is available on Databricks Runtime 9.1+ and is enabled by default on supported instance types.
- Photon accelerates: filters, aggregations, joins, sort, and Delta Lake I/O.
- Photon does not accelerate Python UDFs or Pandas UDFs (still executed via Python interpreter).
- To verify Photon usage, check the Spark UI — Photon-accelerated operators appear with a Photon badge.

---

## Auto Loader

Auto Loader (`cloudFiles`) incrementally ingests new files from cloud storage as they arrive, with automatic schema inference and evolution.

```python
df = (
    spark.readStream.format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.schemaLocation", "/mnt/schema/payments/")
    .option("cloudFiles.inferColumnTypes", "true")
    .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
    .option("rescuedDataColumn", "_rescued_data")
    .load("/mnt/landing/payments/")
)
```

### Schema Evolution Modes
| Mode | Behaviour |
|---|---|
| `addNewColumns` | New columns added to schema; existing columns unchanged |
| `rescue` | New columns captured in `_rescued_data` as JSON; no schema update |
| `failOnNewColumns` | Pipeline fails if a new column is detected |
| `none` | No schema evolution; new columns are dropped |

Use `addNewColumns` for most ingestion pipelines. Use `rescue` when strict schema control is required and unknown columns must be captured without breaking the pipeline.

### Schema Hints
Override inferred types for specific columns:
```python
.option("cloudFiles.schemaHints", "amount DECIMAL(18,2), event_ts TIMESTAMP")
```
