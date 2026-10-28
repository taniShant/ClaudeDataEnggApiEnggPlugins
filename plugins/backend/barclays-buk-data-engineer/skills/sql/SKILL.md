---
name: sql
description: SQL engineering knowledge covering ANSI patterns, dialect awareness, DDL/DML, query optimisation, and anti-patterns
user-invocable: false
owner: BUK Data Engineering Practice
effective_date: 2026-07-13
review_cadence: quarterly
status: approved
---

# SQL Engineering Skill

## ANSI SQL Patterns and Dialect Awareness

Prefer ANSI SQL constructs where possible to maximise portability. Document any platform-specific syntax with an inline comment indicating the target dialect.

| Feature | PostgreSQL | Oracle | Spark SQL | Athena/Presto | T-SQL (SQL Server) |
|---|---|---|---|---|---|
| String concat | `\|\|` or `CONCAT` | `\|\|` or `CONCAT` | `CONCAT` or `\|\|` | `\|\|` or `CONCAT` | `+` or `CONCAT` |
| Limit rows | `LIMIT n` | `FETCH FIRST n ROWS ONLY` | `LIMIT n` | `LIMIT n` | `TOP n` or `FETCH FIRST` |
| Current timestamp | `NOW()` / `CURRENT_TIMESTAMP` | `SYSTIMESTAMP` | `CURRENT_TIMESTAMP()` | `NOW()` | `GETDATE()` / `SYSDATETIME()` |
| Auto-increment | `SERIAL` / `GENERATED ALWAYS AS IDENTITY` | `GENERATED ALWAYS AS IDENTITY` | Not applicable | Not applicable | `IDENTITY(1,1)` |
| Boolean literals | `TRUE` / `FALSE` | `1` / `0` | `TRUE` / `FALSE` | `TRUE` / `FALSE` | `1` / `0` |
| Date diff | `AGE()` / `DATE_PART` | `MONTHS_BETWEEN` | `DATEDIFF` | `DATE_DIFF` | `DATEDIFF` |

Always test SQL against the target engine. Do not assume cross-engine compatibility without validation.

## DDL Patterns

Use `IF EXISTS` / `IF NOT EXISTS` guards in all DDL statements to ensure idempotency.

```sql
-- Create table
CREATE TABLE IF NOT EXISTS finance.transactions (
    transaction_id  BIGINT          NOT NULL,
    account_id      BIGINT          NOT NULL,
    amount          DECIMAL(18, 2)  NOT NULL,
    currency        CHAR(3)         NOT NULL,
    transaction_ts  TIMESTAMP       NOT NULL,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP,
    CONSTRAINT pk_transactions PRIMARY KEY (transaction_id)
);

-- Add column (idempotent pattern — PostgreSQL)
ALTER TABLE finance.transactions
    ADD COLUMN IF NOT EXISTS processed_flag BOOLEAN DEFAULT FALSE;

-- Drop table
DROP TABLE IF EXISTS staging.temp_load;

-- Create index
CREATE INDEX IF NOT EXISTS idx_transactions_account_id
    ON finance.transactions (account_id);

-- Drop index
DROP INDEX IF EXISTS idx_transactions_account_id;
```

For platform-managed tables (e.g. Glue catalog, Hive, Delta), prefer declarative schema management tools (e.g. dbt, Terraform, Flyway) over ad-hoc DDL execution.

## DML Patterns

### INSERT

```sql
-- Explicit column list always; never rely on positional inserts
INSERT INTO finance.transactions (transaction_id, account_id, amount, currency, transaction_ts)
VALUES (1001, 42, 99.99, 'GBP', '2026-07-13 10:00:00');

-- Insert from select
INSERT INTO finance.transactions_archive
SELECT * FROM finance.transactions
WHERE transaction_ts < '2025-01-01';
```

### MERGE / UPSERT

```sql
-- PostgreSQL UPSERT
INSERT INTO finance.transactions (transaction_id, account_id, amount, currency, transaction_ts)
VALUES (1001, 42, 105.00, 'GBP', '2026-07-13 10:00:00')
ON CONFLICT (transaction_id)
DO UPDATE SET
    amount         = EXCLUDED.amount,
    updated_at     = CURRENT_TIMESTAMP;

-- ANSI MERGE (SQL Server, Oracle, Spark SQL)
MERGE INTO finance.transactions AS target
USING staging.transactions_incoming AS source
    ON target.transaction_id = source.transaction_id
WHEN MATCHED THEN
    UPDATE SET
        target.amount      = source.amount,
        target.updated_at  = CURRENT_TIMESTAMP
WHEN NOT MATCHED THEN
    INSERT (transaction_id, account_id, amount, currency, transaction_ts)
    VALUES (source.transaction_id, source.account_id, source.amount, source.currency, source.transaction_ts);
```

### UPDATE with Safety

Always include a `WHERE` clause on UPDATE and DELETE. Never issue a bare `UPDATE table SET col = val` without a predicate in production.

```sql
-- Safe update with WHERE
UPDATE finance.transactions
SET processed_flag = TRUE,
    updated_at     = CURRENT_TIMESTAMP
WHERE transaction_id IN (
    SELECT transaction_id FROM staging.processed_batch WHERE batch_id = :batch_id
);
```

### DELETE with Safety

```sql
-- Soft delete preferred over hard delete
UPDATE finance.transactions
SET deleted_at = CURRENT_TIMESTAMP
WHERE transaction_id = :transaction_id;

-- Hard delete: confirm scope with COUNT before execution in production
DELETE FROM staging.temp_load WHERE batch_id = :batch_id;
```

## Common Table Expressions (CTEs)

Use CTEs to improve readability and avoid deeply nested subqueries. Name CTEs to reflect their business or logical meaning.

```sql
WITH active_accounts AS (
    SELECT account_id, account_holder_id
    FROM core.accounts
    WHERE status = 'ACTIVE'
      AND deleted_at IS NULL
),
recent_transactions AS (
    SELECT t.account_id, SUM(t.amount) AS total_spend
    FROM finance.transactions t
    WHERE t.transaction_ts >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY t.account_id
)
SELECT
    aa.account_id,
    aa.account_holder_id,
    COALESCE(rt.total_spend, 0) AS total_spend_30d
FROM active_accounts aa
LEFT JOIN recent_transactions rt ON aa.account_id = rt.account_id;
```

Recursive CTEs are supported in PostgreSQL, SQL Server, Oracle 11g+, and Spark SQL 3.x. Verify support before use in Athena/Presto (limited recursive CTE support).

## Window Functions

```sql
-- Row numbering for deduplication
SELECT *
FROM (
    SELECT
        transaction_id,
        account_id,
        amount,
        transaction_ts,
        ROW_NUMBER() OVER (
            PARTITION BY account_id
            ORDER BY transaction_ts DESC
        ) AS rn
    FROM finance.transactions
) ranked
WHERE rn = 1;

-- Running totals and moving averages
SELECT
    transaction_id,
    account_id,
    amount,
    SUM(amount)  OVER (PARTITION BY account_id ORDER BY transaction_ts
                       ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total,
    AVG(amount)  OVER (PARTITION BY account_id ORDER BY transaction_ts
                       ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)         AS moving_avg_7,
    LAG(amount, 1) OVER (PARTITION BY account_id ORDER BY transaction_ts) AS prev_amount
FROM finance.transactions;

-- NTILE and PERCENT_RANK for distribution analysis
SELECT
    account_id,
    amount,
    NTILE(10) OVER (ORDER BY amount DESC)        AS decile,
    PERCENT_RANK() OVER (ORDER BY amount DESC)   AS pct_rank
FROM finance.transactions;
```

## Set Operations

```sql
-- UNION ALL (preserves duplicates, faster than UNION DISTINCT)
SELECT account_id FROM current_customers
UNION ALL
SELECT account_id FROM legacy_customers;

-- UNION DISTINCT (deduplicates, requires sort/hash)
SELECT account_id FROM current_customers
UNION
SELECT account_id FROM legacy_customers;

-- INTERSECT and EXCEPT
SELECT account_id FROM set_a
INTERSECT
SELECT account_id FROM set_b;

SELECT account_id FROM set_a
EXCEPT
SELECT account_id FROM set_b;
```

Prefer `UNION ALL` over `UNION` unless deduplication is explicitly required. `UNION` incurs extra cost.

## Parameterised Queries

NEVER construct SQL by string concatenation with user-supplied or runtime values. Always use parameterised queries or prepared statements.

```python
# Python — psycopg2 parameterised query
cursor.execute(
    "SELECT * FROM finance.transactions WHERE account_id = %s AND transaction_ts > %s",
    (account_id, cutoff_date)
)

# SQLAlchemy bindparam
from sqlalchemy import text
stmt = text("SELECT * FROM finance.transactions WHERE account_id = :account_id")
conn.execute(stmt, {"account_id": account_id})
```

For Spark SQL, use DataFrame operations or pass parameters through SparkSession configuration rather than f-string formatted SQL strings.

## Query Plan Analysis

Use `EXPLAIN` to inspect query plans before deploying expensive queries.

```sql
-- PostgreSQL: estimated plan
EXPLAIN SELECT * FROM finance.transactions WHERE account_id = 42;

-- PostgreSQL: actual execution plan with timing
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM finance.transactions WHERE account_id = 42;

-- Spark SQL
EXPLAIN EXTENDED SELECT * FROM transactions WHERE account_id = 42;

-- Presto/Athena
EXPLAIN SELECT * FROM transactions WHERE account_id = 42;
```

Key things to look for in query plans:
- Sequential scans on large tables (expect index scans or partition pruning instead)
- Nested loop joins against large datasets (prefer hash joins)
- High estimated vs actual row count discrepancy (stale statistics)
- Sort operations that can be avoided with appropriate indexing
- Spill to disk (temp writes in PostgreSQL, exchange spill in Spark)

## Indexing Strategy

```sql
-- B-tree: default; suitable for equality and range queries
CREATE INDEX idx_transactions_account_ts
    ON finance.transactions (account_id, transaction_ts DESC);

-- Partial index: smaller, faster for filtered queries
CREATE INDEX idx_transactions_pending
    ON finance.transactions (transaction_id)
    WHERE processed_flag = FALSE;

-- Covering index: includes non-key columns to enable index-only scans (PostgreSQL)
CREATE INDEX idx_transactions_covering
    ON finance.transactions (account_id)
    INCLUDE (amount, currency, transaction_ts);

-- GIN: full-text search and JSONB (PostgreSQL)
CREATE INDEX idx_metadata_gin ON finance.transactions USING GIN (metadata jsonb_path_ops);

-- GiST: geometric/range types (PostgreSQL)
CREATE INDEX idx_valid_range ON records USING GIST (valid_range);
```

Index guidelines:
- Every foreign key column should have an index.
- Index columns used in frequent `WHERE`, `JOIN ON`, and `ORDER BY` clauses.
- Avoid over-indexing on write-heavy tables; each index adds write overhead.
- Monitor unused indexes (`pg_stat_user_indexes` in PostgreSQL) and remove them.

## Partitioning

```sql
-- PostgreSQL range partitioning
CREATE TABLE finance.transactions (
    transaction_id BIGINT NOT NULL,
    transaction_ts TIMESTAMP NOT NULL
) PARTITION BY RANGE (transaction_ts);

CREATE TABLE finance.transactions_2026_q1
    PARTITION OF finance.transactions
    FOR VALUES FROM ('2026-01-01') TO ('2026-04-01');

-- Attach existing table as partition
ALTER TABLE finance.transactions
    ATTACH PARTITION finance.transactions_2026_q2
    FOR VALUES FROM ('2026-04-01') TO ('2026-07-01');
```

Partition by the most common filter predicate. Avoid partitioning by high-cardinality columns. Always include the partition key in filter predicates to enable partition pruning.

## Views and Materialised Views

```sql
-- Regular view (no storage; executes query on each access)
CREATE OR REPLACE VIEW reporting.v_active_customer_spend AS
SELECT
    a.account_holder_id,
    SUM(t.amount) AS total_spend
FROM core.accounts a
JOIN finance.transactions t ON a.account_id = t.account_id
WHERE a.status = 'ACTIVE'
GROUP BY a.account_holder_id;

-- Materialised view (PostgreSQL: stores result; must be refreshed)
CREATE MATERIALIZED VIEW reporting.mv_monthly_spend AS
SELECT
    DATE_TRUNC('month', transaction_ts) AS month,
    account_id,
    SUM(amount) AS total_spend
FROM finance.transactions
GROUP BY 1, 2
WITH DATA;

-- Refresh materialised view (non-concurrent; locks reads)
REFRESH MATERIALIZED VIEW reporting.mv_monthly_spend;

-- Refresh without locking (requires unique index)
REFRESH MATERIALIZED VIEW CONCURRENTLY reporting.mv_monthly_spend;
```

## Transaction Isolation

```sql
-- Default read committed (PostgreSQL, SQL Server)
BEGIN;
UPDATE finance.accounts SET balance = balance - 100 WHERE account_id = :debit_id;
UPDATE finance.accounts SET balance = balance + 100 WHERE account_id = :credit_id;
COMMIT;

-- Serializable isolation for critical consistency requirements
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
-- ...
COMMIT;
```

| Level | Dirty Read | Non-repeatable Read | Phantom Read |
|---|---|---|---|
| READ UNCOMMITTED | Possible | Possible | Possible |
| READ COMMITTED | Not possible | Possible | Possible |
| REPEATABLE READ | Not possible | Not possible | Possible |
| SERIALIZABLE | Not possible | Not possible | Not possible |

Use `READ COMMITTED` by default. Use `SERIALIZABLE` only when required; it has significant performance implications.

## Temporary Tables

```sql
-- PostgreSQL: session-scoped temp table
CREATE TEMP TABLE tmp_batch_ids (
    transaction_id BIGINT PRIMARY KEY
) ON COMMIT DELETE ROWS;

INSERT INTO tmp_batch_ids SELECT transaction_id FROM staging.incoming_batch;

-- T-SQL: session-scoped temp table
CREATE TABLE #tmp_batch_ids (transaction_id BIGINT PRIMARY KEY);
```

Use temp tables for intermediate results in complex multi-step transformations. Drop or truncate temp tables at the end of the session or procedure.

## Type Casting and Conversion

```sql
-- Explicit cast (ANSI)
SELECT CAST('2026-07-13' AS DATE);
SELECT CAST(amount AS DECIMAL(18,2));

-- PostgreSQL shorthand
SELECT '2026-07-13'::DATE;

-- Safe cast (returns NULL on failure — Spark SQL, T-SQL)
SELECT TRY_CAST('abc' AS INT);  -- T-SQL
SELECT TRY(CAST('abc' AS INT)); -- Presto/Athena
```

Always use explicit casts. Never rely on implicit type coercion across engines.

## NULL Handling

```sql
-- NULL-safe comparisons
SELECT * FROM t WHERE col IS NULL;
SELECT * FROM t WHERE col IS NOT NULL;

-- COALESCE: returns first non-null value
SELECT COALESCE(nickname, first_name, 'Unknown') AS display_name FROM customers;

-- NULLIF: returns NULL if two expressions are equal (useful to avoid division by zero)
SELECT total_revenue / NULLIF(transaction_count, 0) AS avg_revenue_per_transaction;

-- NULL in aggregations: NULLs are excluded from COUNT(col), SUM, AVG, MAX, MIN
-- Use COUNT(*) to count all rows including NULLs
```

## Date/Time Handling

```sql
-- Always store timestamps in UTC; convert at presentation layer
INSERT INTO events (event_ts) VALUES (NOW() AT TIME ZONE 'UTC');  -- PostgreSQL

-- Truncate to period
SELECT DATE_TRUNC('month', transaction_ts) AS month FROM finance.transactions; -- PostgreSQL/Spark

-- Extract components
SELECT EXTRACT(YEAR FROM transaction_ts), EXTRACT(DOW FROM transaction_ts) FROM finance.transactions;

-- Date arithmetic
SELECT transaction_ts + INTERVAL '7 days' AS due_date FROM finance.transactions; -- PostgreSQL
SELECT DATEADD(day, 7, transaction_ts) AS due_date FROM finance.transactions;    -- T-SQL

-- Athena/Presto date functions
SELECT DATE_ADD('day', 7, transaction_ts), DATE_DIFF('day', start_date, end_date) FROM t;
```

## Aggregate Patterns

```sql
-- GROUP BY with HAVING for filtered aggregations
SELECT
    account_id,
    COUNT(*) AS tx_count,
    SUM(amount) AS total,
    AVG(amount) AS avg_amount,
    MAX(amount) AS max_amount,
    MIN(amount) AS min_amount
FROM finance.transactions
WHERE transaction_ts >= CURRENT_DATE - INTERVAL '1 year'
GROUP BY account_id
HAVING COUNT(*) > 10;

-- FILTER clause (ANSI, PostgreSQL, Spark SQL 3.x)
SELECT
    COUNT(*) FILTER (WHERE status = 'COMPLETED') AS completed_count,
    COUNT(*) FILTER (WHERE status = 'FAILED')    AS failed_count
FROM finance.transactions;

-- Conditional aggregation (cross-platform)
SELECT
    SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_count,
    SUM(CASE WHEN status = 'FAILED'    THEN 1 ELSE 0 END) AS failed_count
FROM finance.transactions;
```

## Anti-Patterns to Avoid

| Anti-Pattern | Why to Avoid | Preferred Alternative |
|---|---|---|
| `SELECT *` | Fetches unneeded columns; breaks column-order assumptions; disables column pruning | Project only required columns explicitly |
| Implicit cartesian joins (`FROM a, b` without a join condition) | Returns the product of all rows; catastrophic on large tables | Use explicit `JOIN ... ON` syntax |
| Correlated subqueries on large sets without indexes | Re-executes the subquery for every outer row; exponential cost | Rewrite as a CTE, derived table, or `EXISTS` with an index |
| String concatenation to build SQL | SQL injection risk; parse overhead | Use parameterised queries / prepared statements |
| Functions on indexed columns in `WHERE` | Defeats index use | Rewrite predicate to apply the function to the literal instead |
| `ORDER BY` without `LIMIT` in subqueries | Expensive sort with no benefit | Remove unnecessary ordering from inner queries |
| `NOT IN` with a subquery that may return NULLs | Returns 0 rows if the subquery returns any NULL | Use `NOT EXISTS` or filter NULLs from the subquery |
| Implicit type coercion in join conditions | Prevents index use; causes unexpected results | Always cast to a common type explicitly |
