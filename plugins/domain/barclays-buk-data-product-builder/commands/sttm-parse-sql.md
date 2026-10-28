---
description: Extract per-column source lineage from SQL or PySpark code
disable-model-invocation: false
---

# /sttm-parse-sql — Extract Lineage from SQL/PySpark

Parse SQL or PySpark code to extract per-column source lineage.

## Description

Analyzes SQL/PySpark artifacts and produces a structured lineage map showing source table, column, expression, and confidence for each target column.

## Arguments

- `--file`: Specific file to parse. Default: all files in `input/code/`
- `--target-columns`: Comma-separated list of target columns to trace (optional — traces all if omitted)
- `--format`: Output format (json | table). Default: table

## Workflow

### Step 0 — RESOLVE PLUGIN ROOT

`${CLAUDE_PLUGIN_ROOT}` is automatically set by the plugin loader. Verify:
- `${CLAUDE_PLUGIN_ROOT}/configs/sttm/template_spec.yaml` exists

If missing, STOP with: "❌ Plugin root not resolved. Ensure barclays-buk-data-product-builder plugin is loaded."

---

1. Read SQL/PySpark files from `input/code/` (or specified --file)
2. **Pre-flight validation** — check for degenerate cases before parsing:
   - Empty file → `❌ Code file is empty — no SQL/PySpark to parse.`
   - File > 10MB → `❌ Code file exceeds 10MB limit ({size}). Split into smaller files.`
   - Comments-only → `⚠️ File contains only comments — no executable SQL.`
   - DDL-only → `ℹ️ File contains only DDL. Schema registered for column resolution. No lineage to extract.`
   - Parse failure → `⚠️ sqlglot parse failed ({error}). Falling back to LLM interpretation.`
3. Attempt deterministic parsing via sqlglot:

   > Read `python_path` from `output/sttm_session_state.json` — per `agents/refs/python-runtime-contract.md § Invocation Pattern`. If `python_path == null`: skip sqlglot parsing, proceed directly to LLM fallback.

   ```
   {python_path} -c "import sqlglot; ..."
   ```
4. Spawn `sttm-sql-lineage-agent` with code content and target columns
5. Report per-column lineage

## Output (table format)

```
SQL Lineage Extraction Results:
┌─────────────────────┬──────────────┬─────────────┬──────────────────────────────────────┬────────┐
│ Target Column       │ Source Table │ Source Col  │ Expression                           │ Conf.  │
├─────────────────────┼──────────────┼─────────────┼──────────────────────────────────────┼────────┤
│ mortgage_account_id │ account_wm   │ account_id  │ Direct mapping                       │ 0.99   │
│ outstanding_balance │ account_wm   │ balance_amt │ CAST(balance_amt AS DECIMAL(18,2))   │ 0.95   │
│ account_status      │ account_wm   │ status_code │ CASE WHEN status_code IN ...         │ 0.90   │
└─────────────────────┴──────────────┴─────────────┴──────────────────────────────────────┴────────┘

Tables referenced: e_ilp_db.account_wm
Joins detected: none
Unresolved columns: none
Multi-step ETL: 0 intermediate steps detected
```

When multi-step ETL is detected (2+ DML statements creating intermediate tables):
```
Multi-step ETL: {N} intermediate steps detected
  Intermediate tables: {comma-separated list}
  Columns with multi-step chains: {count}
```

## Output (json format)

Writes lineage JSON to stdout or `output/lineage.json`:
```json
{
  "lineage": [
    {
      "target_column": "column_name",
      "source_database": "database_name",
      "source_table": "table_name",
      "source_column": "column_name",
      "expression": "transformation expression or 'Direct mapping'",
      "confidence": 0.95,
      "evidence": "sql:SELECT_item_N",
      "transformation_signals": ["direct"],
      "grain_impact": "1_to_1"
    }
  ],
  "tables_referenced": ["database.table"],
  "joins_detected": [
    {
      "driver_table": "database.table",
      "driver_conditions": [],
      "joins": [
        {
          "join_number": 1,
          "table": "database.table",
          "type": "LEFT",
          "on_condition": "alias.col = alias.col",
          "table_conditions": []
        }
      ]
    }
  ],
  "filters_extracted": {
    "where_clauses": [],
    "having_clauses": [],
    "distinct": false,
    "exists_subqueries": [],
    "correlated_subqueries": [],
    "qualify_clauses": []
  },
  "union_metadata": null,
  "merge_metadata": null,
  "temp_table_chain": [],
  "intermediate_steps": [],
  "column_lineage_chains": {},
  "effective_source_filters": {},
  "resolved_variables": {},
  "unresolved": [],
  "warnings": [],
  "pre_flight": {
    "dialect_detected": "teradata | generic | spark",
    "statement_count": 1,
    "ddl_tables_registered": []
  }
}
```

**Note**: `filters_extracted`, `union_metadata`, `merge_metadata`, `temp_table_chain`, `warnings`, and `pre_flight` are always present in JSON output. The `grain_impact` field on lineage entries indicates how each column affects output grain (key, 1_to_1, aggregated, windowed, hardcoded).

**Multi-step ETL detection:** When source SQL contains multiple DML statements creating intermediate tables (DROP→CREATE→INSERT chains, UPDATE-back patterns, MERGE sequences), the output includes `intermediate_steps[]` with per-step joins, filters, columns, and grain; `column_lineage_chains{}` tracking per-column evolution through steps; `effective_source_filters{}` with cumulative filter summary per base source table; and `resolved_variables{}` with DECLARE/SET variable resolution. See `transformation-patterns.md` Pattern 24 for rendering rules. When the source SQL is a single statement, all four fields are empty.
