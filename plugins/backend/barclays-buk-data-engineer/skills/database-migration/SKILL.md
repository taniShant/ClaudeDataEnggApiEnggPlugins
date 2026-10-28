---
name: database-migration
description: Database migration knowledge covering same-engine upgrades, cross-engine migration, data movement, reconciliation, cutover strategies, and decommission controls
user-invocable: false
owner: BUK Data Engineering Practice
effective_date: 2026-07-13
review_cadence: quarterly
status: approved
---

# Database Migration Skill

## Same-Engine Upgrades

A same-engine upgrade replaces a database with a newer version of the same engine (e.g. PostgreSQL 13 to PostgreSQL 16).

### Version Compatibility Matrix

Before beginning an upgrade:
1. Review the target version's release notes for deprecated features, removed features, and changed defaults.
2. Identify all deprecated SQL syntax and functions used in application code and stored procedures.
3. Confirm driver/client compatibility (JDBC driver version, psycopg2 version, ODBC driver) against the target engine version.
4. Check character set, collation, and encoding compatibility — especially if upgrading across major versions.

| Risk Area | Check |
|---|---|
| Deprecated features | Review `pg_upgrade` output (PostgreSQL) or vendor upgrade advisory |
| SQL compatibility | Run application query set against target version in a test environment |
| Driver compatibility | Check vendor driver compatibility matrix against target DB version |
| Extension compatibility | Verify all installed extensions are available for the target version |
| Collation changes | PostgreSQL 15+ changed `C.UTF-8` collation handling; review `pg_collation` |

### Timezone Handling
Timezone definitions change periodically (DST rule changes, country rule changes). After a major version upgrade, verify:
- `CURRENT_TIMESTAMP AT TIME ZONE 'zone'` returns expected results.
- Historical timestamp queries that depend on timezone conversion are unaffected.
- Application timezone configuration (`timezone` GUC, JDBC `serverTimezone`) matches the database setting.

### Backup Before Upgrade
Always take a full, verified backup immediately before the upgrade. Test restore to a separate environment to confirm backup integrity.

```bash
# PostgreSQL: logical backup
pg_dump -Fc -h host -U user -d dbname -f /backup/pre-upgrade-$(date +%Y%m%d).dump

# PostgreSQL: verify dump is readable
pg_restore --list /backup/pre-upgrade-$(date +%Y%m%d).dump | head -20
```

### Performance Baseline
Capture key query performance metrics before the upgrade:
- Top 20 queries by total execution time (`pg_stat_statements`).
- Table sizes and index sizes.
- Autovacuum settings and bloat estimates.

After the upgrade, run the same benchmark and compare. Planner statistics are preserved by `pg_upgrade` but may need re-analysis if the planner behaves differently.

```sql
-- Capture pre-upgrade query statistics (PostgreSQL)
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;
```

---

## Cross-Engine Migration

Cross-engine migration moves data from one database engine to another (e.g. Oracle to PostgreSQL, SQL Server to Spark/Delta, DB2 to Snowflake).

### Type Mapping Matrices

#### Oracle to PostgreSQL
| Oracle | PostgreSQL | Notes |
|---|---|---|
| `NUMBER(p,s)` | `NUMERIC(p,s)` / `DECIMAL(p,s)` | Exact match |
| `NUMBER(p)` with p <= 18 | `BIGINT` or `INTEGER` | Use integer type for whole numbers |
| `VARCHAR2(n)` | `VARCHAR(n)` | Max length 4000 (Oracle) vs 10485760 (PG) |
| `CLOB` | `TEXT` | Unlimited in PostgreSQL |
| `BLOB` | `BYTEA` | PostgreSQL binary |
| `DATE` | `TIMESTAMP` | Oracle DATE includes time component; PostgreSQL DATE does not |
| `TIMESTAMP WITH TIME ZONE` | `TIMESTAMPTZ` | Both store UTC with timezone metadata |
| `INTERVAL YEAR TO MONTH` | `INTERVAL` | PostgreSQL interval covers both |
| `ROWID` | No equivalent | Synthesise with `ctid` or an auto-increment column |
| `XMLTYPE` | `XML` | PostgreSQL has native XML type |

#### SQL Server to PostgreSQL
| SQL Server | PostgreSQL | Notes |
|---|---|---|
| `INT` | `INTEGER` | Identical |
| `BIGINT` | `BIGINT` | Identical |
| `DECIMAL(p,s)` / `NUMERIC(p,s)` | `NUMERIC(p,s)` | Identical |
| `MONEY` | `NUMERIC(19,4)` | No native MONEY type in PostgreSQL |
| `NVARCHAR(n)` | `VARCHAR(n)` | PostgreSQL is UTF-8 native; no NVARCHAR needed |
| `NVARCHAR(MAX)` | `TEXT` | Unlimited |
| `DATETIME` | `TIMESTAMP` | SQL Server DATETIME has 3ms precision; PG TIMESTAMP has microsecond |
| `DATETIME2` | `TIMESTAMP` | Closer match |
| `DATETIMEOFFSET` | `TIMESTAMPTZ` | Timezone-aware |
| `BIT` | `BOOLEAN` | SQL Server BIT is 0/1; PostgreSQL BOOLEAN is TRUE/FALSE |
| `UNIQUEIDENTIFIER` | `UUID` | PostgreSQL has native UUID type |
| `ROWVERSION` / `TIMESTAMP` | No equivalent | Use `xmin` or application-managed version column |
| `XML` | `XML` | Both have native XML |

### Function and Procedure Translation

| Oracle / SQL Server | PostgreSQL |
|---|---|
| `NVL(a, b)` | `COALESCE(a, b)` |
| `DECODE(col, v1, r1, v2, r2, default)` | `CASE WHEN col=v1 THEN r1 WHEN col=v2 THEN r2 ELSE default END` |
| `SYSDATE` (Oracle) | `CURRENT_DATE` |
| `SYSTIMESTAMP` (Oracle) | `CURRENT_TIMESTAMP` |
| `GETDATE()` (T-SQL) | `CURRENT_TIMESTAMP` |
| `ISNULL(a, b)` (T-SQL) | `COALESCE(a, b)` |
| `TOP n` (T-SQL) | `LIMIT n` |
| `ROWNUM` (Oracle) | `ROW_NUMBER() OVER ()` or `LIMIT` |
| `CONNECT BY PRIOR` (Oracle hierarchical) | Recursive CTE (`WITH RECURSIVE`) |
| `LISTAGG(col, delim) WITHIN GROUP (ORDER BY ...)` | `STRING_AGG(col, delim ORDER BY ...)` |
| `WMSYS.WM_CONCAT` (Oracle) | `STRING_AGG(col, ',')` |
| `TO_DATE(str, fmt)` | `TO_DATE(str, fmt)` — format codes differ |
| `TO_CHAR(date, 'YYYYMMDD')` | `TO_CHAR(date, 'YYYYMMDD')` — similar but verify |

Always test function translations with representative data, including NULLs, boundary values, and special characters.

### Sequence and Identity Migration
Oracle sequences and SQL Server IDENTITY columns require translation:

```sql
-- Oracle sequence to PostgreSQL
-- Oracle: CREATE SEQUENCE seq_transaction_id START WITH 1000 INCREMENT BY 1;
-- PostgreSQL:
CREATE SEQUENCE seq_transaction_id START WITH 1000 INCREMENT BY 1;
-- Or use GENERATED ALWAYS AS IDENTITY (preferred in PostgreSQL 10+):
ALTER TABLE finance.transactions
    ALTER COLUMN transaction_id ADD GENERATED ALWAYS AS IDENTITY (START WITH 1000 INCREMENT BY 1);
```

Set the sequence current value to be higher than the maximum existing key value after migrating data to prevent collisions.

```sql
SELECT setval('seq_transaction_id', (SELECT MAX(transaction_id) FROM finance.transactions));
```

### Constraint Mapping
| Constraint | Oracle / SQL Server | PostgreSQL |
|---|---|---|
| Primary key | `PRIMARY KEY` | `PRIMARY KEY` |
| Unique | `UNIQUE` | `UNIQUE` |
| Foreign key | `FOREIGN KEY ... REFERENCES` | Same; note ON DELETE behaviour |
| Check constraint | `CHECK (condition)` | `CHECK (condition)` |
| NOT NULL | `NOT NULL` | `NOT NULL` |
| Deferrable constraints | Supported in Oracle | Supported in PostgreSQL (`DEFERRABLE INITIALLY DEFERRED`) |
| SQL Server check constraints | `WITH CHECK` / `WITH NOCHECK` | PostgreSQL check constraints are always validated on insert unless table-level check is disabled |

### Transaction and Isolation Semantics
Different engines implement isolation levels differently. Verify isolation behaviour after migration:
- SQL Server `READ COMMITTED` with snapshot isolation (RCSI) behaves like PostgreSQL `READ COMMITTED` but is not the same as default SQL Server `READ COMMITTED` (which allows dirty reads in some configurations).
- Oracle `READ COMMITTED` is multi-version (MVCC) — similar to PostgreSQL.
- SQL Server `NOLOCK` hint (dirty reads) has no direct PostgreSQL equivalent; remove all `NOLOCK` hints.

### Partitioning Differences
| Engine | Partitioning Support |
|---|---|
| Oracle | Range, list, hash, composite (range-hash, range-list, list-list) |
| SQL Server | Partition function + partition scheme; only one partitioning key per table |
| PostgreSQL | Range, list, hash, and composite (via sub-partitioning since PG 11) |
| Spark/Delta | Dynamic partition overwrite; liquid clustering |

Partition strategies may need redesigning if the source engine's partitioning model does not map directly.

### Case Sensitivity
| Engine | Default identifier case |
|---|---|
| Oracle | Stores unquoted identifiers in UPPERCASE |
| SQL Server | Case-insensitive by default (depends on collation) |
| PostgreSQL | Stores unquoted identifiers in lowercase |
| MySQL | Case-insensitive on Windows; case-sensitive on Linux (depends on `lower_case_table_names`) |

When migrating from Oracle or SQL Server to PostgreSQL, convert all unquoted identifiers to lowercase in SQL scripts. Remove any `"QUOTED_UPPERCASE"` identifiers and replace with lowercase equivalents.

### NULL Handling
- Empty string `''` and NULL are distinct in PostgreSQL and SQL Server. In Oracle, `''` is equivalent to NULL. All Oracle code that tests `col = ''` must be rewritten as `col IS NULL`.
- `WHERE col <> 'value'` does not match NULLs in any SQL standard engine; this is consistent.

### Decimal Precision and Rounding
Different engines may have subtle differences in decimal rounding behaviour. Test all financial calculations with boundary values and verify results match to the required precision.

### Encoding
Verify source encoding and ensure target encoding is UTF-8. Migrating from LATIN1 or WE8MSWIN1252 to UTF-8 requires character set conversion. Use `iconv` or database export/import with explicit encoding conversion.

---

## Data Movement Approaches

### Full Extract
Export all data from the source and load into the target. Simple; complete; requires a maintenance window if the source continues to change.

```python
# Full extract via JDBC (Spark)
df = (
    spark.read.format("jdbc")
    .option("url", source_jdbc_url)
    .option("dbtable", "finance.transactions")
    .option("partitionColumn", "transaction_id")
    .option("lowerBound", "1")
    .option("upperBound", str(max_id))
    .option("numPartitions", "50")
    .load()
)
df.write.format("delta").mode("overwrite").save(target_path)
```

### Change Data Capture (CDC)
Capture changes from the source's transaction log and apply them to the target in near real-time. Minimises the maintenance window for cutover.

Common CDC tools:
- **Debezium**: source connector for Kafka; supports PostgreSQL, Oracle, SQL Server, MySQL.
- **AWS DMS**: managed CDC with replication instance.
- **Striim**: enterprise CDC and streaming integration.

CDC requirements:
- Source must have logical replication or transaction log access enabled.
- Source must retain log entries for the duration of the migration.
- Target must support upsert (MERGE/INSERT ON CONFLICT) to apply CDC events idempotently.

### Dual-Write
Application writes to both source and target simultaneously during the migration window. Ensures target stays current without CDC. Complex to implement; risk of inconsistency if one write fails.

```python
# Application dual-write pattern (pseudocode)
def write_transaction(txn):
    source_db.insert(txn)
    try:
        target_db.insert(txn)
    except Exception as e:
        reconciliation_queue.put(txn)  # catch up on failure
        log_error(e)
```

### Trickle Migration
Migrate data in small batches over time, prioritising active or recently accessed data first. Suitable when full extract is too slow and CDC is not available.

---

## Reconciliation Methods

Reconciliation must be performed at every stage of the migration to confirm data completeness and accuracy.

### Row Counts
```sql
-- Source count
SELECT COUNT(*) FROM source_db.finance.transactions;

-- Target count
SELECT COUNT(*) FROM target_db.finance.transactions;
```

Row count match is necessary but not sufficient — it does not detect swapped or corrupted rows.

### Column Aggregates
```sql
-- Compare SUM, MIN, MAX, NULL counts for key columns
SELECT
    COUNT(*)              AS row_count,
    SUM(amount)           AS total_amount,
    MIN(transaction_ts)   AS earliest_ts,
    MAX(transaction_ts)   AS latest_ts,
    COUNT(amount)         AS non_null_amount,
    COUNT(DISTINCT account_id) AS distinct_accounts
FROM finance.transactions;
```

Run on both source and target and compare results.

### Hash Comparison
For exact row-level verification, compute a hash of each row and compare:

```python
from pyspark.sql import functions as F

# Deterministic row hash (exclude volatile columns like created_at)
source_hashed = source_df.withColumn(
    "row_hash",
    F.md5(F.concat_ws("|", F.col("transaction_id"), F.col("account_id"),
                       F.col("amount").cast("string"), F.col("currency")))
)
target_hashed = target_df.withColumn(
    "row_hash",
    F.md5(F.concat_ws("|", F.col("transaction_id"), F.col("account_id"),
                       F.col("amount").cast("string"), F.col("currency")))
)

# Find rows in source not in target
missing = source_hashed.join(target_hashed, on="row_hash", how="left_anti")
missing.show()
```

### Key Coverage
Verify that all primary keys from the source exist in the target:
```sql
-- Rows in source not in target
SELECT s.transaction_id
FROM source.transactions s
LEFT JOIN target.transactions t ON s.transaction_id = t.transaction_id
WHERE t.transaction_id IS NULL
LIMIT 100;
```

### Business Rule Outcomes
Re-run key business queries or reports against both source and target and compare the results. This validates that the data semantics are preserved, not just the raw values.

---

## Cutover Strategies

### Big Bang
Stop the source, migrate all remaining data, switch applications to target, restart.

- **Pros**: simple; no dual system maintenance; no synchronisation complexity.
- **Cons**: requires a full maintenance window; high risk if migration fails; rollback is a full restore.
- **Use when**: dataset is small; maintenance window is available; rollback is straightforward.

### Parallel Run
Source and target run concurrently. Applications write to both; reads are served from target with fallback to source. Monitor for divergence.

- **Pros**: extensive validation opportunity; low cutover risk.
- **Cons**: complex dual-write; resource cost of running two systems.
- **Use when**: high-risk migration; strict accuracy requirements; sufficient infrastructure budget.

### Phased Migration
Migrate one subset (table, schema, service, or data partition) at a time. Gradually shift traffic to the target.

- **Pros**: limits blast radius; allows iterative validation.
- **Cons**: requires routing logic to direct reads/writes to the correct system per entity; longer migration timeline.
- **Use when**: large, complex system; multiple teams involved; cannot afford a long single maintenance window.

### Canary Migration
Route a small percentage of traffic to the target first. Increase gradually as confidence grows.

- **Pros**: early failure detection with limited impact.
- **Cons**: requires feature flag or routing infrastructure; potential for state inconsistency between canary and non-canary traffic.
- **Use when**: stateless or idempotent workloads; read-heavy workloads where divergence is acceptable temporarily.

---

## Rollback and Fallback Plans

Every migration must have a documented, tested rollback plan before cutover begins.

| Scenario | Rollback Action |
|---|---|
| Migration fails during data movement | Restore from pre-migration backup; verify restore succeeded before announcing rollback |
| Application errors after cutover | Re-point application connection strings to source; verify source data currency |
| Data corruption detected post-cutover | Halt writes to target; restore from backup or re-apply CDC from last known good checkpoint |

Rollback criteria must be defined in advance (e.g. error rate threshold, data mismatch percentage, business metric deviation). Assign a decision-maker who is empowered to trigger rollback.

Rollback window: define the maximum time after cutover during which rollback is still feasible. After this window, the cost of reverting may exceed the cost of remediating forward.

---

## Residual Data Handling

After a successful migration and the rollback window has closed:
1. **Archive**: take a final logical backup of the source database and store according to the data retention policy.
2. **Access revocation**: revoke application credentials and network access to the source database.
3. **Freeze**: set the source database to read-only to prevent accidental writes.
4. **Decommission schedule**: agree a decommission date with all stakeholders. Do not decommission immediately after cutover; allow an observation period.

---

## Decommission Controls

Before decommissioning a database:
1. Confirm with all consuming teams that they have completed migration to the target.
2. Verify no active network connections exist to the source (monitor `pg_stat_activity` or equivalent).
3. Verify no active jobs, ETL pipelines, or reports reference the source.
4. Confirm data retention obligations are met (backup archived).
5. Obtain sign-off from the data owner.
6. Document the decommission event: date, responsible team, sign-off reference.

```sql
-- PostgreSQL: check active connections before decommission
SELECT pid, usename, application_name, client_addr, state, query
FROM pg_stat_activity
WHERE datname = 'source_db'
  AND pid <> pg_backend_pid();
```

---

## Performance Comparison Methodology

After migration, verify that the target meets or exceeds the performance of the source.

1. **Capture source baseline**: top queries by execution time, row counts, index statistics (collected before migration announcement).
2. **Warm the target**: run the query workload against the target for at least 24 hours to populate the buffer cache and gather planner statistics.
3. **Run the benchmark**: execute the top query set against the target and capture execution plans and timings.
4. **Compare**: compare execution time, I/O (blocks read), and plan structure between source and target.
5. **Tune if needed**: if a query performs worse on the target, obtain the execution plan from both engines, identify the difference, and address it (missing index, stale statistics, compatibility setting, query rewrite).
6. **Sign off**: obtain stakeholder sign-off on performance parity before proceeding to decommission.

```sql
-- PostgreSQL: after migration, run ANALYZE to collect fresh statistics
ANALYZE VERBOSE finance.transactions;

-- Reset pg_stat_statements for clean post-migration baseline
SELECT pg_stat_statements_reset();
```
