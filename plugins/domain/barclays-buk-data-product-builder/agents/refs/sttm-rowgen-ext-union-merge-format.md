---
description: "Conditional STTM row generation extension for UNION and MERGE operations — defines structured rendering format for UNION branches (table, columns, filters, type) and MERGE operations."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-28
---

# UNION + MERGE Structured Format (Row Generator Extension)

> **Loaded conditionally** — only when `union_metadata` or `merge_metadata` is non-null in the lineage data.

## UNION Structured Format (Scenario 6)

**When to use:** `union_metadata` is non-null.

**Format (simple UNION):**
```
Union Branch 1 Table: {database}.{table} ({alias})
Union Branch 1 Columns: {col1}, {col2}, {col3}
Union Branch 1 Filters: [{filters or empty}]
Union Branch 2 Table: {database}.{table} ({alias})
Union Branch 2 Columns: {col1}, {col2}, {col3}
Union Branch 2 Filters: [{filters or empty}]
Union Type: UNION ALL
Value: {column_name}
```

**Format (UNION with joins inside branches):**
```
Union Branch 1 Table: {database}.{table} ({alias})
Union Branch 1 Joins: INNER JOIN {database}.{table} ({alias}) ON {cond}
Union Branch 1 Columns: {alias}.{col1}, {alias}.{col2}
Union Branch 1 Filters: [{filters}]
Union Branch 2 Table: {database}.{table} ({alias})
Union Branch 2 Joins: INNER JOIN {database}.{table} ({alias}) ON {cond}
Union Branch 2 Columns: {alias}.{col1} AS {target_col}, {alias}.{col2} AS {target_col}
Union Branch 2 Filters: [{filters or empty}]
Union Type: UNION ALL
Value: {column_name}
```

**Rules:**
- `Union Branch N Table:` always FQN with alias
- `Union Branch N Columns:` must list columns in matching order across all branches
- `Union Branch N Joins:` (optional) — only when branch has inner joins
- `Union Branch N Filters:` always present (empty = `[]`)
- `Union Type:` must be exactly `UNION ALL` or `UNION DISTINCT`
- Column count and order across branches MUST match (validation rule M42)

**Example (UNION ALL from two tables):**
```json
"business_logic": "Union Branch 1 Table: e_savings_db.savings_account (sa)\nUnion Branch 1 Columns: sa.account_id, sa.balance\nUnion Branch 1 Filters: []\nUnion Branch 2 Table: e_checking_db.checking_account (ca)\nUnion Branch 2 Columns: ca.account_id, ca.balance\nUnion Branch 2 Filters: []\nUnion Type: UNION ALL\nValue: balance"
```

**Example (UNION ALL with joins in a branch):**
```json
"business_logic": "Union Branch 1 Table: e_order_db.orders (o)\nUnion Branch 1 Joins: INNER JOIN e_customer_db.customer (c) ON o.customer_id = c.customer_id\nUnion Branch 1 Columns: o.order_id, c.name\nUnion Branch 1 Filters: []\nUnion Branch 2 Table: e_order_db.returns (r)\nUnion Branch 2 Joins: INNER JOIN e_supplier_db.supplier (s) ON r.supplier_id = s.supplier_id\nUnion Branch 2 Columns: r.order_id, s.name\nUnion Branch 2 Filters: []\nUnion Type: UNION ALL\nValue: name"
```

Each branch is a self-contained set of labeled fields. The `Union Type` line specifies UNION ALL or UNION DISTINCT. When `union_metadata` is present in the input, use the branch information to build these lines.

## MERGE Structured Format (Scenario 7)

**When to use:** `merge_metadata` is non-null.

**Format (standard MERGE):**
```
MERGE Source Table: {database}.{table} ({alias})
MERGE Target Table: {database}.{table} ({alias})
MERGE Match Key: {alias}.{col} = {alias}.{col} [AND ...]
MERGE Matched Action: UPDATE SET {col} = {alias}.{col}, {col} = {alias}.{col}
MERGE Not Matched Action: INSERT ({cols}) VALUES ({alias}.{cols})
Value: {alias}.{expression}
```

**Format (MERGE with conditional matched clause):**
```
MERGE Source Table: {database}.{table} ({alias})
MERGE Target Table: {database}.{table} ({alias})
MERGE Match Key: {alias}.{col} = {alias}.{col} AND {alias}.{col} = '{value}'
MERGE Matched Condition: {alias}.{col} > {alias}.{col}
MERGE Matched Action: UPDATE SET {col} = {alias}.{col}, {col} = {alias}.{col}
MERGE Not Matched Action: INSERT ({cols}) VALUES ({alias}.{cols})
Value: {alias}.{expression}
```

**Format (SCD2 per-column MERGE branch):**
For audit columns like eff_end_date, active:
```
MERGE Branch [NOT MATCHED → INSERT]: CAST('3499-12-31' AS DATE)
MERGE Branch [MATCHED → UPDATE]: SET tgt.eff_end_date = src.eff_start_date
```

**Rules:**
- `MERGE Match Key:` supports compound keys with AND
- `MERGE Matched Condition:` (optional) — conditional update trigger
- All table names FQN; all column references use `alias.column`
- SCD2 audit columns use `MERGE Branch [ACTION → TYPE]:` per-column format

**Example (MERGE with matched update and not-matched insert):**
```json
"business_logic": "MERGE Source Table: e_staging_db.staging_account (stg)\nMERGE Target Table: fdp_uk_account_db.account (tgt)\nMERGE Match Key: tgt.account_id = stg.account_id\nMERGE Matched Action: UPDATE SET balance = stg.balance\nMERGE Not Matched Action: INSERT (account_id, balance) VALUES (stg.account_id, stg.balance)\nValue: stg.balance"
```

**Example (MERGE with conditional matched clause):**
```json
"business_logic": "MERGE Source Table: e_feed_db.daily_feed (df)\nMERGE Target Table: fdp_uk_customer_db.customer (tgt)\nMERGE Match Key: tgt.customer_id = df.customer_id AND tgt.product_code = df.product_code\nMERGE Matched Condition: df.update_date > tgt.update_date\nMERGE Matched Action: UPDATE SET amount = df.amount\nMERGE Not Matched Action: INSERT (customer_id, product_code, amount) VALUES (df.customer_id, df.product_code, df.amount)\nValue: df.amount"
```

When `merge_metadata` is present in the input, use its `matched` and `not_matched` branch details to build the appropriate lines. Include only the clauses that exist in the MERGE statement (e.g., omit `MERGE Not Matched Action` if the MERGE has no NOT MATCHED clause).

NEVER use natural language for multi-table transformations. This is a BLOCKER validation rule.
