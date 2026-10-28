---
description: "Conditional STTM extension for multi-step ETL lineage — loaded when 2+ DML statements create or modify intermediate tables, tracking column lineage chains and effective source filters."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-28
---

# Multi-Step ETL Extension (Lineage)

> **Loaded conditionally** — only when 2+ DML statements are detected in the code artifact that create/modify intermediate tables.

### Multi-Step ETL Detection Gate (MANDATORY)

Before proceeding to Per-Step Lineage Capture, apply this binary detection gate:

**Detection condition:** 2+ DML statements in the code artifact that create or modify intermediate tables which reference each other or feed the final target statement.

**Detection patterns (any ONE triggers multi-step capture):**
- **DROP→CREATE→INSERT chains:** A table is dropped, recreated, and populated via INSERT...SELECT — then referenced by a later statement
- **UPDATE…FROM patterns:** An intermediate table created by one statement is modified by a later UPDATE...FROM/SET statement
- **MERGE INTO against intermediates:** A MERGE statement targets an intermediate table created earlier
- **Cross-statement references:** A later INSERT...SELECT's FROM/JOIN clause reads a table that was created or populated by an earlier statement in the same file

**When the gate triggers (any pattern matched):**
The agent MUST populate ALL of the following structures alongside existing `temp_table_chain[]`:
- `intermediate_steps[]` — per-step lineage capture (see schema below)
- `column_lineage_chains{}` — per-target-column chain through intermediate steps
- `effective_source_filters{}` — cumulative filter summary per base source table
- `resolved_variables{}` — DECLARE/SET variable registry forwarded to output

**When the gate does NOT trigger (single-statement SQL):**
Leave all four structures empty/absent. Existing temp_table_chain resolution handles base-table resolution alone.

**Confidence for multi-step capture:** 0.85–0.90 (same as temp table chain resolution). If a step cannot be fully parsed (e.g., complex nested CASE with Teradata NAMED syntax), capture what CAN be extracted and set that step's confidence to 0.70 with a warning. NEVER skip the step entirely or collapse it into the temp_table_chain — partial capture with a warning is always preferable to silent loss.

### Per-Step Lineage Capture (Multi-Statement ETL)

When the code artifact contains multiple statements creating/modifying intermediate temp tables before the final output (multi-step ETL), capture the full transformation context per step. This preserves the information that temp_table_chain resolution collapses.

**Trigger:** Multi-Step ETL Detection Gate (above) matched — 2+ DML statements creating/modifying temp tables feeding the final target statement.

**Output structures** — stored alongside existing `temp_table_chain[]`:

#### `intermediate_steps[]`

For each statement creating/modifying/deleting from a temp table, capture:

```
step_number              — (int) 1-based sequential execution order
step_label               — (string|null) From SQL comments (e.g., "HIST130", "STEP_A")
temp_table_name          — (string) Intermediate table created/modified by this step
statement_type           — (enum) INSERT_SELECT | UPDATE_FROM | MERGE | CREATE_VIEW |
                                  CREATE_AS_SELECT | DELETE | TRUNCATE | SELECT_INTO |
                                  RENAME_TABLE
source_tables[]          — (string[]) Base or intermediate tables read by this step
row_operation            — (enum) create | update | delete | truncate | merge | rename
```

**For INSERT_SELECT / CREATE_AS_SELECT / SELECT_INTO steps:**
```
joins[]                  — Same structure as joins_detected:
  .driver_table          — (string) Primary table for this step (the FROM table)
  .driver_conditions[]   — (string[]) Filters applied to the driver table
  .joins[]               — (array) Per joined table:
    .join_number         — (int) Sequential join number
    .table               — (string) Joined table FQN
    .alias               — (string, optional) Table alias
    .type                — (string) JOIN type (INNER, LEFT, RIGHT, FULL, CROSS)
    .on_condition        — (string) JOIN ON predicate
    .table_conditions[]  — (string[]) Filters specific to this joined table
filters[]                — (string[]) ALL SQL predicates at this step as a flat list for programmatic access
                           (anti-summarization rule applies). Note: for rendered output, per-table filter
                           attribution uses driver_conditions/table_conditions from joins[]. This flat array
                           is retained for backward compatibility and programmatic consumers.
filter_provenance[]      — (object[]) Per filter at this step:
  .filter_sql            — Exact SQL predicate
  .origin                — "applied" (new at this step) | "inherited" (from upstream via intermediate table)
  .inherited_from_step   — (int, optional) Step number that originally applied it
  .applied_to_table      — Base source table this filter ultimately constrains
columns_produced[]       — (object[]) Per column:
  .column_name           — Column name in the intermediate table
  .expression            — Exact SQL expression (no summarization — rule 3b applies)
  .source_columns[]      — Fully qualified source columns referenced
  .column_role           — (enum) "new" (introduced at this step) | "transformed" (modified from prior step) | "pass_through" (unchanged from prior step)
  .datatype_hint         — (string, optional) Data type when determinable from CAST/DDL
columns_dropped[]        — (string[], optional) Columns from prior step not carried forward to this step
grain_keys[]             — (string[]) Columns defining uniqueness at this step (from GROUP BY columns or temp table PK)
aggregation_semantics    — (object|null) Present only when step has GROUP BY or window functions:
  .group_by_columns[]    — GROUP BY column list with aliases
  .aggregate_functions[] — Each: {column, function (SUM/COUNT/MAX/etc.), arguments}
  .window_functions[]    — (optional) Each: {column, function, partition_by[], order_by[], frame_spec}
  .is_dedup_pattern      — (bool) True if GROUP BY is dedup (all cols in GROUP BY, no aggregates — per SC11 exception)
```

**For UPDATE_FROM steps:**
```
update_semantics:
  .update_target         — Table being updated
  .update_source         — Table providing new values (from the FROM/JOIN clause of the UPDATE)
  .set_columns[]         — Each: {target_column, source_expression, assignment_mode}
                           assignment_mode: "replace" (simple =) | "additive" (+= or col = col + expr) | "conditional" (CASE in SET)
  .join_condition        — Full ON/WHERE clause linking update target to source
  .scope_filter          — (string, optional) Additional WHERE clause limiting which rows are updated
```

**For MERGE steps:**
```
merge_semantics:
  .match_keys[]          — Columns in the ON clause
  .matched_action        — {action (UPDATE|DELETE), set_columns[] (same structure as update_semantics.set_columns)}
  .not_matched_action    — {action (INSERT), insert_columns[] (string[]), values[] (string[])}
  .not_matched_by_source — (object, optional) {action (DELETE)} — present only if MERGE has this clause
```

**For DELETE / TRUNCATE steps:**
```
delete_semantics:
  .target_table          — Table being deleted/truncated
  .where_condition       — (string, optional) DELETE WHERE clause (null for TRUNCATE)
  .estimated_impact      — "partial" (conditional DELETE) | "full" (TRUNCATE or unconditional DELETE)
```

**For RENAME TABLE steps (Atomic Table Swap Pattern):**

RENAME TABLE patterns indicate atomic table replacement — a common Teradata/legacy ETL pattern where the final target table is swapped in a single DDL operation to avoid downtime. Example:
```sql
RENAME TABLE target_db.bc_history TO target_db.bc_history_prev;
RENAME TABLE target_db.bc_history_new TO target_db.bc_history;
```

When RENAME TABLE is detected:
```
rename_semantics:
  .source_table          — Table being renamed FROM (the newly built table)
  .target_table          — Table being renamed TO (the production target name)
  .displaced_table       — (string, optional) Previous production table renamed away (e.g., _prev, _bak)
  .is_atomic_swap        — (bool) True when 2+ RENAME statements execute together as a swap
```

Capture RENAME TABLE as a step with `statement_type: RENAME_TABLE`, `row_operation: rename`. The step has no `columns_produced`, `joins`, or `filters` — it is a metadata-only operation. Document in Additional Context as: "Final target replacement uses atomic RENAME TABLE swap pattern." The displaced table name (if any) should also be recorded for operational context.

#### `column_lineage_chains{}`

Build per target column — traces how each column evolves through the intermediate steps:

```
{
  "payments_received": {
    "chain_depth": 4,
    "steps": [1, 2, 3, 4],
    "final_expression": "SUM(pc.AMT_PYMT_1 + ... 12 components)",
    "intermediate_expressions": [
      {"step": 1, "expression": "SUM(pc.AMT_PYMT_1 + ... 12 components)", "role": "new"},
      {"step": 2, "expression": "pass_through", "role": "pass_through"},
      {"step": 3, "expression": "SET PAYMENTS_RECEIVED = EPP_PAYMENTS_UPDATE.AMT_PYMT_PRCH", "role": "transformed"},
      {"step": 4, "expression": "pass_through", "role": "pass_through"}
    ],
    "datatype_changes": [
      {"step": 1, "datatype": "DECIMAL(18,2)"}
    ]
  }
}
```

Fields:
- `chain_depth` (int): Number of steps this column passes through
- `steps[]` (int[]): Ordered step numbers where this column exists
- `final_expression` (string): The expression that produces the final value
- `intermediate_expressions[]`: Per-step expression with `role` (new/transformed/pass_through)
- `datatype_changes[]` (optional): Steps where the column's data type changes

#### `effective_source_filters{}`

Computed summary: for each base source table, the union of all filters that cumulatively constrain which rows flow into the target. Derived by traversing `filter_provenance[]` across all steps, collecting filters where `applied_to_table` matches:

```json
{
  "effective_source_filters": {
    "a_trmf_base.account_header": [
      "billing_period >= ADD_MONTHS(:billing_period, -73)",
      "status_code NOT IN ('X','Z')"
    ],
    "a_trmf_base.prior_cycle_v": [
      "billing_period >= ADD_MONTHS(:billing_period, -73)"
    ]
  }
}
```

#### `resolved_variables{}`

Forward the variable registry (already tracked via DECLARE/SET handling above) to the output for downstream transparency:

```json
{
  "resolved_variables": {
    "@cutoff_date": {
      "value": "DATEADD(day, -90, CURRENT_DATE)",
      "source_statement": "SET @cutoff_date = DATEADD(day, -90, CURRENT_DATE)",
      "resolved": true,
      "referenced_tables": []
    },
    "@batch_id": {
      "value": "(SELECT MAX(batch_id) + 1 FROM control_table)",
      "source_statement": "SET @batch_id = (SELECT MAX(batch_id) + 1 FROM control_table)",
      "resolved": true,
      "referenced_tables": ["control_table"]
    }
  }
}
```

Only present when DECLARE/SET variables exist in the code artifact. Unresolvable variables have `resolved: false`.

#### Worked Example: rskm_fields Pattern (3-Variant Merge)

This example shows a common ETL pattern where multiple population segments are computed separately and then merged. The `rskm_fields` table in Billing Hist computes risk metrics (EDF, BRGEDF, EED) for three mutually-exclusive account populations, then merges via COALESCE. The output below demonstrates the expected `intermediate_steps[]` and `column_lineage_chains{}` for this pattern.

**SQL pattern (simplified):**
```sql
/* Step 1 - EDF normal */ DROP TABLE edf_01; CREATE TABLE edf_01 (...); INSERT INTO edf_01 SELECT ... 1/(1+EXP(...)) FROM data_table INNER JOIN edf_parms WHERE behaviour_score_raw > 31 AND scorecard != 9 AND status NOT IN ('A','B','E','K','O');
/* Step 2 - EDF scorecard 9 */ DROP TABLE edf_02; CREATE TABLE edf_02 (...); INSERT INTO edf_02 SELECT ... score FROM edf_parms_s9 WHERE scorecard = 9;
/* Step 3 - EDF status K0 */ DROP TABLE edf_03; CREATE TABLE edf_03 (...); INSERT INTO edf_03 SELECT ... EDF_value FROM edf_parms_k0 WHERE status = 'K0';
/* Step 10 - Merge */ DROP TABLE rskm_fields; CREATE TABLE rskm_fields (...); INSERT INTO rskm_fields SELECT histtab.logical_account_id, CASE WHEN COALESCE(edf03.edf_value, edf02.edf_value, edf01.edf_value) >= 0.9999995 THEN 0.999999 ELSE COALESCE(...) END, ... FROM data_table LEFT JOIN edf_01 ON ... LEFT JOIN edf_02 ON ... LEFT JOIN edf_03 ON ...;
```

**Expected output:**
```json
{
  "intermediate_steps": [
    {
      "step_number": 1,
      "step_label": "EDF normal",
      "temp_table_name": "l_bcs_loaddb.edf_01",
      "statement_type": "INSERT_SELECT",
      "row_operation": "create",
      "source_tables": ["l_bcs_loaddb.BC_HISTORY_new_month_billsort", "A_BCS_REFDB.edf_parms"],
      "joins": [{"driver_table": "l_bcs_loaddb.BC_HISTORY_new_month_billsort", "driver_conditions": ["achist.behaviour_score_raw > 31", "substr(achist.account_status_code,1,1) NOT IN ('A','B','E','K','O')"], "joins": [{"join_number": 1, "table": "A_BCS_REFDB.edf_parms", "type": "INNER", "on_condition": "achist.behaviour_scorecard_identifier = edf.scorecard", "table_conditions": []}]}],
      "filters": ["achist.behaviour_score_raw > 31", "substr(achist.account_status_code,1,1) NOT IN ('A','B','E','K','O')"],
      "filter_provenance": [
        {"filter_sql": "achist.behaviour_score_raw > 31", "origin": "applied", "applied_to_table": "l_bcs_loaddb.BC_HISTORY_new_month_billsort"},
        {"filter_sql": "substr(achist.account_status_code,1,1) NOT IN ('A','B','E','K','O')", "origin": "applied", "applied_to_table": "l_bcs_loaddb.BC_HISTORY_new_month_billsort"}
      ],
      "columns_produced": [
        {"column_name": "logical_account_id", "expression": "achist.logical_account_id", "source_columns": ["l_bcs_loaddb.BC_HISTORY_new_month_billsort.logical_account_id"], "column_role": "new"},
        {"column_name": "EDF_Value", "expression": "1/(1+EXP((edf.score * achist.behaviour_score_raw) + (edf.genscore * gscore) + edf.dummy_value + (edf.pivot_value * achist.behaviour_score_raw) + edf.intercept + tbooks + (edf.balance_climit * baltoclm)))", "source_columns": ["A_BCS_REFDB.edf_parms.score", "l_bcs_loaddb.BC_HISTORY_new_month_billsort.behaviour_score_raw", "A_BCS_REFDB.edf_parms.genscore", "A_BCS_REFDB.edf_parms.pivot_value", "A_BCS_REFDB.edf_parms.intercept", "A_BCS_REFDB.edf_parms.balance_climit"], "column_role": "new"}
      ],
      "grain_keys": ["logical_account_id"]
    },
    {
      "step_number": 2,
      "step_label": "EDF scorecard 9",
      "temp_table_name": "l_bcs_loaddb.edf_02",
      "statement_type": "INSERT_SELECT",
      "row_operation": "create",
      "source_tables": ["l_bcs_loaddb.BC_HISTORY_new_month_billsort", "A_BCS_REFDB.edf_parms_s9"],
      "joins": [{"driver_table": "A_BCS_REFDB.edf_parms_s9", "driver_conditions": [], "joins": [{"join_number": 1, "table": "l_bcs_loaddb.BC_HISTORY_new_month_billsort", "type": "INNER", "on_condition": "achist.behaviour_score_raw BETWEEN edfs9.lower_score AND edfs9.upper_score", "table_conditions": ["achist.behaviour_scorecard_identifier = 9", "achist.behaviour_score_raw > 31"]}]}],
      "filters": ["achist.behaviour_scorecard_identifier = 9", "achist.behaviour_score_raw > 31", "substr(achist.account_status_code,1,1) NOT IN ('A','B','E','K','O')"],
      "columns_produced": [
        {"column_name": "logical_account_id", "expression": "achist.logical_account_id", "source_columns": ["l_bcs_loaddb.BC_HISTORY_new_month_billsort.logical_account_id"], "column_role": "new"},
        {"column_name": "EDF_Value", "expression": "edfs9.score", "source_columns": ["A_BCS_REFDB.edf_parms_s9.score"], "column_role": "new"}
      ],
      "grain_keys": ["logical_account_id"]
    },
    {
      "step_number": 3,
      "step_label": "EDF status K0",
      "temp_table_name": "l_bcs_loaddb.edf_03",
      "statement_type": "INSERT_SELECT",
      "row_operation": "create",
      "source_tables": ["l_bcs_loaddb.BC_HISTORY_new_month_billsort", "A_BCS_REFDB.edf_parms_k0"],
      "joins": [{"driver_table": "l_bcs_loaddb.BC_HISTORY_new_month_billsort", "driver_conditions": ["bch.account_status_code = 'K0'"], "joins": [{"join_number": 1, "table": "A_BCS_REFDB.edf_parms_k0", "type": "INNER", "on_condition": "bch.delinquency = edf.delinquency", "table_conditions": []}]}],
      "filters": ["bch.account_status_code = 'K0'"],
      "columns_produced": [
        {"column_name": "logical_account_id", "expression": "bch.logical_account_id", "source_columns": ["l_bcs_loaddb.BC_HISTORY_new_month_billsort.logical_account_id"], "column_role": "new"},
        {"column_name": "EDF_Value", "expression": "edf.EDF_value", "source_columns": ["A_BCS_REFDB.edf_parms_k0.EDF_value"], "column_role": "new"}
      ],
      "grain_keys": ["logical_account_id"]
    },
    {
      "step_number": 10,
      "step_label": "Merge Values",
      "temp_table_name": "l_bcs_loaddb.rskm_fields",
      "statement_type": "INSERT_SELECT",
      "row_operation": "create",
      "source_tables": ["l_bcs_loaddb.BC_HISTORY_new_month_billsort", "l_bcs_loaddb.edf_01", "l_bcs_loaddb.edf_02", "l_bcs_loaddb.edf_03"],
      "joins": [{"driver_table": "l_bcs_loaddb.BC_HISTORY_new_month_billsort", "driver_conditions": [], "joins": [
        {"join_number": 1, "table": "l_bcs_loaddb.edf_01", "type": "LEFT", "on_condition": "histtab.logical_account_id = edf01.logical_account_id", "table_conditions": []},
        {"join_number": 2, "table": "l_bcs_loaddb.edf_02", "type": "LEFT", "on_condition": "histtab.logical_account_id = edf02.logical_account_id", "table_conditions": []},
        {"join_number": 3, "table": "l_bcs_loaddb.edf_03", "type": "LEFT", "on_condition": "histtab.logical_account_id = edf03.logical_account_id", "table_conditions": []}
      ]}],
      "filters": [],
      "columns_produced": [
        {"column_name": "logical_account_id", "expression": "histtab.logical_account_id", "source_columns": ["l_bcs_loaddb.BC_HISTORY_new_month_billsort.logical_account_id"], "column_role": "new"},
        {"column_name": "EDF_Value", "expression": "CASE WHEN COALESCE(edf03.edf_value, edf02.edf_value, edf01.edf_value) >= 0.9999995 THEN 0.999999 ELSE COALESCE(edf03.edf_value, edf02.edf_value, edf01.edf_value) END", "source_columns": ["l_bcs_loaddb.edf_01.edf_value", "l_bcs_loaddb.edf_02.edf_value", "l_bcs_loaddb.edf_03.edf_value"], "column_role": "new"}
      ],
      "grain_keys": ["logical_account_id"]
    }
  ],
  "column_lineage_chains": {
    "EDF_Value": {
      "chain_depth": 2,
      "steps": [1, 10],
      "final_expression": "CASE WHEN COALESCE(edf03.edf_value, edf02.edf_value, edf01.edf_value) >= 0.9999995 THEN 0.999999 ELSE COALESCE(edf03.edf_value, edf02.edf_value, edf01.edf_value) END",
      "intermediate_expressions": [
        {"step": 1, "expression": "1/(1+EXP((edf.score * achist.behaviour_score_raw) + (edf.genscore * gscore) + edf.dummy_value + (edf.pivot_value * achist.behaviour_score_raw) + edf.intercept + tbooks + (edf.balance_climit * baltoclm)))", "role": "new"},
        {"step": 10, "expression": "CASE WHEN COALESCE(edf03.edf_value, edf02.edf_value, edf01.edf_value) >= 0.9999995 THEN 0.999999 ELSE COALESCE(...) END", "role": "new"}
      ]
    }
  },
  "effective_source_filters": {
    "l_bcs_loaddb.BC_HISTORY_new_month_billsort": [
      "behaviour_score_raw > 31",
      "substr(account_status_code,1,1) NOT IN ('A','B','E','K','O')",
      "account_status_code = 'K0'"
    ],
    "A_BCS_REFDB.edf_parms": [],
    "A_BCS_REFDB.edf_parms_s9": [],
    "A_BCS_REFDB.edf_parms_k0": []
  },
  "resolved_variables": {}
}
```

**Key points demonstrated:**
- Steps 1-3 are mutually exclusive populations (different filters) producing the same column (`EDF_Value`) in different intermediate tables
- Step 10 merges via COALESCE with priority order `_03 → _02 → _01` (K0 → scorecard 9 → normal)
- `column_lineage_chains` shows `chain_depth: 2` because the column is created at step 1 (one variant) and then merged at step 10 (final)
- `effective_source_filters` accumulates all filters across all steps per base source table
- The logistic regression formula `1/(1+EXP(...))` is preserved in full — NOT summarized as "risk model calculation"

#### Per-Step Output Verification (MANDATORY before returning)

When `intermediate_steps` is non-empty, verify EVERY step has ALL required fields before returning. This is a pre-output checklist — do NOT return until all steps pass:

**Required fields per step (all non-null unless noted):**
- `step_number` (int, 1-based sequential)
- `step_label` (string or null — null only when no SQL comment label exists)
- `temp_table_name` (string, fully qualified)
- `statement_type` (enum: INSERT_SELECT | UPDATE_FROM | MERGE | CREATE_VIEW | CREATE_AS_SELECT | DELETE | TRUNCATE | SELECT_INTO | RENAME_TABLE)
- `row_operation` (enum: create | update | delete | truncate | merge)
- `source_tables[]` (string[], non-empty — at least one source table per step)
- `joins[]` (array — empty array if no joins, NEVER omitted)
- `filters[]` (string[] — exact SQL predicates, empty array if none, NEVER omitted)
- `columns_produced[]` (array — at least one column per step, each with `column_name`, `expression`, `column_role`)
- `grain_keys[]` (string[] — from GROUP BY or PK; empty array if unknown, NEVER omitted)
- Statement-type-specific semantics (aggregation_semantics, update_semantics, merge_semantics, delete_semantics) when applicable

**WRONG output (shallow — 3 fields only):**
```json
{"step": "Hist110", "description": "Prior_Cycle_v view over s_trmfdb.ctcp", "output": "Prior_Cycle_v"}
```

**CORRECT output (full schema):**
```json
{
  "step_number": 1,
  "step_label": "Hist110",
  "temp_table_name": "l_bcs_loaddb.Prior_Cycle_v",
  "statement_type": "CREATE_VIEW",
  "row_operation": "create",
  "source_tables": ["s_trmfdb.ctcp"],
  "joins": [],
  "filters": ["QUALIFY CSUM(1, NBR_CARDH_ACCT, TIME_LAST_UPD DESC) = 1"],
  "filter_provenance": [
    {"filter_sql": "QUALIFY CSUM(1, NBR_CARDH_ACCT, TIME_LAST_UPD DESC) = 1", "origin": "applied", "applied_to_table": "s_trmfdb.ctcp"}
  ],
  "columns_produced": [
    {"column_name": "Account_Number", "expression": "ctcp.NBR_CARDH_ACCT", "source_columns": ["s_trmfdb.ctcp.NBR_CARDH_ACCT"], "column_role": "new"},
    {"column_name": "Credit_Limit", "expression": "ctcp.AMT_CRED_LMT", "source_columns": ["s_trmfdb.ctcp.AMT_CRED_LMT"], "column_role": "new"}
  ],
  "grain_keys": ["Account_Number"],
  "view_definition_summary": "SELECT NBR_CARDH_ACCT AS Account_Number, AMT_CRED_LMT AS Credit_Limit, ... FROM s_trmfdb.ctcp QUALIFY CSUM(1, NBR_CARDH_ACCT, TIME_LAST_UPD DESC) = 1",
  "resolves_to_base_tables": ["s_trmfdb.ctcp"]
}
```

#### Population Completeness Rules (MANDATORY)

1. **`column_lineage_chains` must be non-empty** when `intermediate_steps` has 2+ entries. For EVERY target column that passes through 2+ intermediate steps, build the chain entry with `chain_depth`, `steps[]`, `final_expression`, and `intermediate_expressions[]`.

   WRONG: `"column_lineage_chains": {}` (empty when intermediate_steps has 26 entries)
   CORRECT: populated with one entry per multi-step column.

2. **`effective_source_filters` must be non-empty** when ANY step has non-empty `filters[]`. Traverse `filter_provenance[]` across all steps, collecting cumulative filters per base source table.

   WRONG: `"effective_source_filters": {}` (empty when multiple steps have filters)
   CORRECT: populated with one entry per base source table that has at least one filter.

3. **`resolved_variables` must be populated** when DECLARE/SET variables exist in the code artifact. Empty `{}` is valid only when no variables exist.

4. **CREATE_VIEW steps**: When the code artifact contains a CREATE VIEW statement, emit it as a full intermediate step with `statement_type: CREATE_VIEW`. Populate `source_tables` with the base tables the view's SELECT reads from. Populate `view_definition_summary` with the view's SELECT statement. Populate `resolves_to_base_tables` with the ultimate base tables (after resolving nested view chains). If the view references another view, chain through to the final base tables.

### CREATE_VIEW Step Capture

When the lineage agent encounters a view definition (CREATE VIEW, REPLACE VIEW, CREATE OR REPLACE VIEW, etc.), it MUST emit a CREATE_VIEW intermediate step:

```json
{
  "step_number": 1,
  "temp_table_name": "l_bcs_loaddb.prior_cycle_v",
  "statement_type": "CREATE_VIEW",
  "source_tables": ["s_trmfdb.ctcp"],
  "row_operation": "create",
  "columns_produced": [
    {"column_name": "Account_Number", "expression": "ctcp.NBR_CARDH_ACCT", "column_role": "new"},
    {"column_name": "Credit_Limit", "expression": "ctcp.AMT_CRED_LMT", "column_role": "new"}
  ],
  "grain_keys": ["Account_Number"],
  "view_definition_summary": "SELECT ctcp.NBR_CARDH_ACCT AS Account_Number, ctcp.AMT_CRED_LMT AS Credit_Limit FROM s_trmfdb.ctcp QUALIFY CSUM(1, NBR_CARDH_ACCT, TIME_LAST_UPD DESC) = 1",
  "resolves_to_base_tables": ["s_trmfdb.ctcp"]
}
```

Subsequent steps MUST reference `s_trmfdb.ctcp` (the base table), NOT `l_bcs_loaddb.prior_cycle_v` (the view name), in all `source_tables`, `joins`, and column references.
