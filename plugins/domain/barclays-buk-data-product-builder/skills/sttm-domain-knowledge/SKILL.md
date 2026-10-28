---
name: sttm-domain-knowledge
description: "Source-to-Target Mapping domain knowledge: 16 Mapping Columns (A–P), 10 Source Volumetrics Columns (A–J), classification model, evidence precedence, design constraints, and profiling policy. Use when agents need STTM field definitions, validation context, or mapping output schema."
user-invocable: false
owner: "samir.chaudhari@barclays.com"
review_cadence: quarterly
last_reviewed: 2026-09-21
---

**Source:** Samir Chaudhari | **Owner:** samir.chaudhari@barclays.com | **Review:** Quarterly | **Last reviewed:** 2026-09-21

# STTM Domain Knowledge

## Preamble

A Source-to-Target Mapping (STTM) is a formal documentation artifact that describes, for every column in a target data product table:
- Where the data comes from (source database, table, column)
- How it gets there (transformation logic, business rules)
- What it means (descriptions, context, constraints)
- How confident we are in the mapping (provenance, evidence)

The STTM is the authoritative contract between data engineers, architects, and business stakeholders for data pipeline development.

The STTM Generator produces:
1. **JSON** (system of record) — canonical representation with provenance metadata
2. **Excel** (projection) — formatted to match the mapping spec exactly (16 mapping columns + 10 Source Volumetrics columns)

Excel output always has exactly 2 sheets regardless of classification:
- Mapping (Blue #4472C4) — All mapping rows for the classified target
- Source Volumetrics (Green #00B050) — One row per unique source table

## 16 Mapping Columns (A–P)

| Col | Header | Description |
|-----|--------|-------------|
| A | Target Database | Target database name (pattern: {tier}_{country}_{domain}_db) |
| B | Target Table | Target table name (snake_case) |
| C | Target Column Name | Target column name (snake_case, no leading digits, no reserved words) |
| D | Target Column Definition/Description | Business description of the column |
| E | Target Column Datatype | Iceberg/Spark type: string, int, bigint, decimal(p,s), date, timestamp, boolean, float, double |
| F | Target Column Null Flag | Y = nullable, N = NOT NULL |
| G | Source Database | Source database name. Special values: (system), (derived) |
| H | Source Table Name | Source table name. Special values: (system), (derived), Hardcoded, N/A |
| I | Source Column Name | Source column name. Special values: (system), (derived), Hardcoded, N/A |
| J | Business Logic/Transformation Logic | SQL expression or structured Driver Table format. For multi-table: MUST use structured format |
| K | Additional Context | Table-level operational metadata as pipe-delimited key:value. First row only. Allowed keys: load_type, partition_key, process_frequency, rolling_deletion_predicate, cdc_type, cdc_exclude, validate_unique_keys, duplicates_ts_col, dedup_order. |
| L | Target Table description | Business description of the target table (first row only) |
| M | Transformation Type | Direct / Derived / Lookup / Direct - Type Cast / blank |
| N | Default Value | Fallback value when logic yields NULL |
| O | Target Table Type | scd2 / scd1 / transactional / blank |
| P | Key Column | Y = primary/business key; N or blank |

### Row Structure
- Row 1: Column headers (bold, filled background)
- Row 2+: Generated mapping data (no instructions row in output)

## 10 Source Volumetrics Columns (A–J)

| Col | Header |
|-----|--------|
| A | Source Database |
| B | Source Table |
| C | Estimated Rows |
| D | Estimated Size (GB) |
| E | Daily Increment Rows |
| F | Daily Increment Size (GB) |
| G | Primary Key |
| H | Partition Key |
| I | Table Type |
| J | Broadcast Hint |

## Key Constraints

1. **Never invent business logic** — if transformation cannot be determined from evidence, route to guided mode
2. **Never silently fill required fields** — below confidence threshold (0.7) → guided mode
3. **Never guess crypto DE names** — must be explicitly provided
4. **Never override authoritative sources** — target template values are sacrosanct
5. **Multi-table = structured format** — natural language join descriptions are FORBIDDEN for multi-table mappings
6. **Source Volumetrics required** — one row per unique source table referenced in mappings
7. **Provenance is per-field** — every field in every row must have evidence tracking

## Multi-Table Structured Format

For ALL mappings involving multiple tables (joins, lookups), the Business Logic column MUST use:
```
Driver Table: <primary_table>
Driver Conditions: [Filter conditions or empty []]
Join N Table: <table_to_join>
TableN Conditions: [Filter conditions or empty []]
Join N Type: LEFT|INNER|RIGHT|FULL
Join N Conditions: <left_table>.<left_col> = <right_table>.<right_col>
Value: <column_expression>
```

Rules:
- "Driver Table" = table defining the grain
- Join conditions MUST use explicit table.column = table.column on BOTH sides
- "Value" = the SQL expression for THIS target column
- Natural language descriptions are NOT PERMITTED

### UNION Structured Format

When UNION/UNION ALL combines multiple SELECT branches:
```
Union Branch 1: SELECT <columns> FROM <table> (<alias>) [joins if any]
Union Branch 2: SELECT <columns> FROM <table> (<alias>) [joins if any]
Union Type: UNION ALL
Value: <alias>.<expression>
```

### Self-Join Format

When the same table is joined to itself:
```
Driver Table: <table> (<role_alias_L>)
Join 1: <TYPE> JOIN <table> (<role_alias_R>) ON <role_alias_L>.<col> = <role_alias_R>.<col>
Value: <role_alias_L>.<expr> - <role_alias_R>.<expr>
```
Aliases must reflect the logical role (e.g., `account_curr`, `account_prev`).

### Non-Equi Join Format

When JOIN ON conditions use inequality operators:
```
Driver Table: <table> (<alias>)
Join 1: <TYPE> JOIN <table> (<alias>) ON <alias>.<col> BETWEEN <alias>.<col_start> AND <alias>.<col_end>
Value: <alias>.<expression>
```
Supported operators: =, >, <, >=, <=, BETWEEN...AND, !=/<>

### MERGE Structured Format

When MERGE INTO is used:
```
MERGE Source Table: <source_table> (<alias>)
MERGE Target Table: <target_table> (<alias>)
MERGE Match Key: <target_alias>.<col> = <source_alias>.<col>
MERGE Matched Action: <source_alias>.<expression>
MERGE Not Matched Action: <source_alias>.<expression>
```

## Column Resolution Records

The internal working model for each target column:
```json
{
  "target_column": "column_name",
  "target_datatype": "type",
  "target_nullable": "Y/N",
  "candidate_sources": [
    {
      "source": "db.table.column",
      "evidence_type": "sql_ast | metadata | user | heuristic",
      "confidence": 0.0-1.0,
      "expression": "transformation expression"
    }
  ],
  "scenario_hints": ["scd2", "type_cast"],
  "unresolved": []
}
```

## Design Constraints

- JSON is the source of truth; Excel is only a projection matching the mapping spec exactly
- Deterministic evidence (SQL AST, DDL, metadata) always preferred over heuristic inference
- Business logic must NEVER be invented — route to guided mode instead
- Crypto DE names must NEVER be inferred — must be explicitly provided
- Confidence threshold: 0.7 — below this → guided mode, never silently fill
- Provenance tracking is per-FIELD (not per-row) — every field has evidence
- Source Volumetrics sheet required — one row per unique source table

## Classification Model (4-Axis)

Classification uses 4 independent orthogonal axes (3 × 3 × 4 × 3 = 108 valid combinations):

- **Axis 1 — Data Product Type**: FDP (from raw/source), CDP (from FDP; BASE exceptionally), BDP (from CDP) — detected by database prefix (`fdp_`, `cdp_`, `bdp_`)
- **Axis 2 — Table Type**: Transactional (append-only), NonTransactional_SCD1 (overwrite), NonTransactional_SCD2 (history with eff_start/end/active) — detected by audit columns and MERGE patterns
- **Axis 3 — Crypto Aspect**: None, Tokenize (protect UDF), Detokenize (unprotect UDF), Both (nested protect/unprotect) — detected by protect/unprotect UDF presence

Audit columns are determined solely by Table Type axis. Crypto is applied additively on top of base logic.

## Evidence Precedence Hierarchy

| Priority | Source | Trust Level |
|----------|--------|-------------|
| 1 | Target template / DDL constraints | Never override |
| 2 | SQL / PySpark AST | Authoritative for transformation |
| 3 | Pre-extracted metadata / Source Excel / DM1 / Crypto config | Strong supporting |
| 4 | Source dictionary / Markdown docs | Supporting (validate, don't override) |
| 5 | Profiling (user answers or Excel report) / Heuristic / User free-text | Advisory (warn, never auto-apply) |

When same-priority sources conflict → surface to guided mode. NEVER silently resolve conflicts.

## Provenance Model

Every generated field carries provenance metadata:
```json
{
  "field": "business_logic",
  "value": "CAST(balance_amt AS DECIMAL(18,2))",
  "provenance": {
    "source_of_evidence": "sql",
    "artifact": "code/transform.sql:line_42",
    "confidence": 0.95,
    "method": "extracted",
    "precedence_applied": "sql > metadata > heuristic"
  }
}
```

Methods:
- **provided** — directly from input template, no modification
- **extracted** — parsed from SQL/PySpark/DDL code
- **inferred** — deduced from metadata/profiling patterns (profiling from Excel report or user answers only)
- **user_supplied** — explicitly given in guided mode or interview
- **rule_generated** — produced by plugin rules (audit columns, system columns)

## Profiling Policy

Profiling is advisory (Level 5) and NEVER provided as a JSON file. The plugin does NOT accept `profiling_signals.json`.

Accepted sources:
- User interview / guided-mode answers
- Excel profiling report in `input/source_metadata/` or `input/profiling/`

When missing — ask targeted questions, recommend queries, continue with available info, never fail solely because profiling data is absent.

## Agent Self-Check

Before using this skill's data, verify:

- [ ] **Check 1**: 16 mapping columns complete
- [ ] **Check 2**: classification axes resolved
- [ ] **Check 3**: evidence precedence applied
- [ ] **Check 4**: naming conventions match prefix
- [ ] **Check 5**: design constraints respected
