---
description: "Conditional STTM row generation extension for multi-step transformation lineage — defines verbose step format (v1.1) with Operation, Driver Table, Conditions, Joins, and Window Functions."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-28
---

# Multi-Step Transformation Lineage Rendering (Row Generator Extension)

> **Loaded conditionally** — only when `intermediate_steps` is non-empty in the lineage data.

### Multi-Step Transformation Lineage Format

When `intermediate_steps` is non-empty (multi-statement ETL with intermediate temp tables):

**First Key Column Row:** The **first row with `key_column = "Y"`** gets the full transformation lineage chain appended to its Business Logic, separated by a `---\nTransformation Lineage:` divider. The column's own mapping logic comes first, then the divider, then the full chain. All other `key_column = "Y"` rows do NOT repeat the lineage chain.

### Verbose Step Format (v1.1)

Each step in the Transformation Lineage block uses the verbose labeled format:

```
Step N ({step_label}):
  Operation: {INSERT_SELECT|UPDATE|DELETE|TRUNCATE|MERGE|RENAME|CREATE_VIEW}
  Driver Table: {database}.{table} ({alias})
  Driver Conditions: [{filters on driver table or empty}]
  [Join N Table: {database}.{table} ({alias})]
  [Join N Type: {type}]
  [Join N On: {condition}]
  [Join N Filters: [{filters on this joined table}]]
  [Window Function: {function}]
  [Window Partition: {columns}]
  [Window Order: {column} {direction}]
  [Post Filter: {condition}]
  [Aggregate Function: {functions}]
  [Aggregate Group By: {columns}]
  Columns:
    {target_col} = {expression} [{role}]
  Grain: {grain_columns}
  Destination: {database}.{table}
  [Staging Hint: {CHECKPOINT|PERSIST|NONE}]
  [Estimated Volume: {size}]
```

**Rules:**
- `Operation:` is mandatory — one of: `INSERT_SELECT`, `UPDATE`, `DELETE`, `TRUNCATE`, `MERGE`, `RENAME`, `CREATE_VIEW`
- `Driver Table:` identifies the primary/driving table for this step — same convention as column-level Business Logic format
- `Driver Conditions:` mandatory on INSERT_SELECT / CREATE_AS_SELECT / SELECT_INTO steps — filters applied to the driver table. Use empty `[]` when no driver filters exist (matching column-level convention)
- `Join N Filters:` mandatory per join — filters specific to that joined table. Use empty `[]` when no join-specific filters exist
- **Per-table filter attribution:** derive from `filter_provenance[].applied_to_table` — filters where `applied_to_table` matches the driver table go to `Driver Conditions:`, filters where `applied_to_table` matches a joined table go to that join's `Join N Filters:`. Cross-table predicates (referencing both tables) go to `Driver Conditions:` as fallback
- `Columns:` block lists each produced column as `{name} = {expression} [{role}]`
- Column roles: `[New]`, `[Transformed]`, `[Pass-through]`, `[Replace]`, `[Additive]`, `[Conditional]`, `[New, Infrastructure]`
- `Grain:` mandatory for every step (composite grains use `+` separator: `customer_id + product_code`)
- `Destination:` uses FQN for the intermediate/target table (replaces `→` arrow notation)
- `Staging Hint:` optional, added when volumetrics indicate large intermediate results
- `Estimated Volume:` informational for the transform generator

**Step Rendering Rules:**

1. **CREATE/INSERT steps** (`row_operation: create`): Show Driver Table + Driver Conditions, JOINs with per-join filters, per-column expressions with `[New]` or `[Transformed]` tags, Grain annotation, and Destination:
   ```
   Step 1 (HIST130):
     Operation: INSERT_SELECT
     Driver Table: account_header (ah)
     Driver Conditions: []
     Join 1 Table: prior_cycle_v (pc)
     Join 1 Type: LEFT
     Join 1 On: ah.NBR = pc.NBR
     Join 1 Filters: []
     Join 2 Table: automatic_payments (ap)
     Join 2 Type: LEFT
     Join 2 On: ah.NBR = ap.NBR
     Join 2 Filters: [ap.DATE_EFF <= ah.DATE_ACCT_LST_CYC]
     Columns:
       PAYMENTS_RECEIVED = SUM(pc.AMT_PYMT_1 + ... 12 components) [New]
       Behaviour_Score_Raw = bsh.Current_Raw_Behaviour_Score [New]
     Grain: ACCOUNT_NUMBER
     Destination: work_db.bc_history_new_temp1
   ```

2. **UPDATE steps** (`row_operation: update`): Show SET columns with assignment mode tags `[Replace]`/`[Additive]`/`[Conditional]`, FROM/ON scope:
   ```
   Step 3 (HIST140): UPDATE bc_history_new_temp1
     SET PAYMENTS_RECEIVED = EPP_PAYMENTS_UPDATE.AMT_PYMT_PRCH [Replace]
     FROM EPP_PAYMENTS_UPDATE ON ACCOUNT_NUMBER = ACCOUNT_NUMBER
   ```

3. **DELETE steps** (`row_operation: delete`): Show WHERE condition and `[Partial removal]` tag:
   ```
   Step 12 (HIST180): DELETE FROM bc_history_temp
     WHERE billing_period < ADD_MONTHS(:billing_period, -73)
     [Partial removal]
   ```

4. **TRUNCATE steps** (`row_operation: truncate`): Show `[Full removal]` tag:
   ```
   Step 5: TRUNCATE staging_table
     [Full removal]
   ```

5. **MERGE steps** (`row_operation: merge`): Show Match Key, WHEN MATCHED, WHEN NOT MATCHED:
   ```
   Step 8 (HIST160): MERGE INTO bc_history_temp
     MERGE Match Key: account_number = src.account_number
     MERGE Matched Action: SET balance = src.new_balance [Replace]
     MERGE Not Matched Action: (account_number, balance)
   ```

### Non-Key Column Chain Format (Scenario 9)

For non-key columns (not the first key_column="Y" row), use per-column chain:
```
Step 1: {col} = {expression} [{role}]
Step 2: {col} = {expression} [{role}]
Step 3: Pass-through
Step 4: {col} = {expression} [{role}]
```

**Rules:**
- Only steps where this column is [New], [Transformed], or [Replace] show the expression
- Steps where column is unchanged show `Pass-through`
- Step numbers MUST match the lineage chain from the key column's Transformation Lineage block

For non-key columns with `chain_depth > 1` in `column_lineage_chains`, show the column-specific chain. Pass-through steps render as `Step N: pass-through` (one line) to maintain step numbering continuity. Transformed/new steps get full detail with `[New]` or `[Transformed]` tag:

```
Step 1: PAYMENTS_RECEIVED = SUM(pc.AMT_PYMT_1 + ... 12 components) [New]
Step 2: pass-through
Step 3: SET PAYMENTS_RECEIVED = EPP_PAYMENTS_UPDATE.AMT_PYMT_PRCH [Transformed, Replace]
Step 4: pass-through
Step 5: pass-through
```

### UPDATE Step Format (Scenario 10)
```
Step N ({label}):
  Operation: UPDATE
  Target Table: {database}.{table}
  Update Source Table: {database}.{table} ({alias})
  Update Join On: {alias}.{col} = {alias}.{col}
  Update Source Filters: [{filters on update source table or empty}]
  [Scope Filter: {condition on which target rows are updated}]
  Set Columns:
    {col} = {alias}.{expression} [Replace]
    {col} = {alias}.{expression} [Replace]
```

### DELETE Step Format
```
Step N ({label}):
  Operation: DELETE
  Target Table: {database}.{table}
  Delete Condition: {SQL WHERE predicate}
  Delete Impact: Partial
```

### TRUNCATE Step Format
```
Step N ({label}):
  Operation: TRUNCATE
  Target Table: {database}.{table}
  Delete Impact: Full
```

### RENAME Step Format
```
Step N ({label}):
  Operation: RENAME
  Source Table: {database}.{new_table}
  Target Table: {database}.{original_table}
  Displaced Table: {database}.{prev_table}
  Atomic Swap: Yes
```

**Post-Chain Blocks:**

After all steps, append these blocks when the corresponding data is non-empty:

```
---
Effective Source Filters:
  account_header: billing_period >= ADD_MONTHS(:billing_period, -73)
  prior_cycle_v: billing_period >= ADD_MONTHS(:billing_period, -73)
Variables:
  :billing_period = (runtime parameter — Teradata BTEQ substitution)
```

- `Effective Source Filters:` — cumulative filter summary per base source table from `effective_source_filters`
- `Variables:` — resolved DECLARE/SET variables from `resolved_variables`

#### Complete Worked Example: rskm_fields → EXPECTED_DEFAULT_FREQ (EDF_Value)

This example shows how multi-step ETL with 3-variant computation + merge renders in business_logic cells.

**Scenario:** Target column `EXPECTED_DEFAULT_FREQ` in `bc_history` is populated from `l_bcs_loaddb.rskm_fields.EDF_Value`, which is itself built through 10 SQL steps (3 variant computations for different account populations + merge via COALESCE).

**Output for first key_column="Y" row (`LOGICAL_ACCOUNT_ID_NEW`):**

One row, one cell — the full lineage chain is newline-separated text in a single `business_logic` cell:
```
Driver Table: l_bcs_loaddb.BC_HISTORY_new_month_billsort (bh)
Driver Conditions: [bh.purge_flag = 'N']
Join 1: LEFT JOIN l_bcs_loaddb.rskm_fields (rsk) ON bh.logical_account_id = rsk.logical_account_id
Join 1 Filters: []
Value: COALESCE(amx.NBR_ACCT_TGT, bh.logical_account_id)
---
Transformation Lineage:
Step 1 (EDF normal):
  Operation: INSERT_SELECT
  Driver Table: l_bcs_loaddb.BC_HISTORY_new_month_billsort (ach)
  Driver Conditions: [ach.behaviour_score_raw > 31, substr(ach.account_status_code,1,1) NOT IN ('A','B','E','K','O')]
  Join 1 Table: A_BCS_REFDB.edf_parms (edf)
  Join 1 Type: INNER
  Join 1 On: ach.behaviour_scorecard_identifier = edf.scorecard
  Join 1 Filters: []
  Columns:
    EDF_Value = 1/(1+EXP((edf.score * ach.behaviour_score_raw) + (edf.genscore * gscore) + edf.dummy_value + (edf.pivot_value * ach.behaviour_score_raw) + edf.intercept + tbooks + (edf.balance_climit * baltoclm))) [New]
  Grain: logical_account_id
  Destination: l_bcs_loaddb.edf_01

Step 2 (EDF scorecard 9):
  Operation: INSERT_SELECT
  Driver Table: A_BCS_REFDB.edf_parms_s9 (edfs9)
  Driver Conditions: []
  Join 1 Table: l_bcs_loaddb.BC_HISTORY_new_month_billsort (ach)
  Join 1 Type: INNER
  Join 1 On: ach.behaviour_score_raw BETWEEN edfs9.lower_score AND edfs9.upper_score
  Join 1 Filters: [ach.behaviour_scorecard_identifier = 9, ach.behaviour_score_raw > 31]
  Columns:
    EDF_Value = edfs9.score [New]
  Grain: logical_account_id
  Destination: l_bcs_loaddb.edf_02

Step 3 (EDF status K0):
  Operation: INSERT_SELECT
  Driver Table: l_bcs_loaddb.BC_HISTORY_new_month_billsort (bch)
  Driver Conditions: [bch.account_status_code = 'K0']
  Join 1 Table: A_BCS_REFDB.edf_parms_k0 (edf)
  Join 1 Type: INNER
  Join 1 On: bch.delinquency = edf.delinquency
  Join 1 Filters: []
  Columns:
    EDF_Value = edf.EDF_value [New]
  Grain: logical_account_id
  Destination: l_bcs_loaddb.edf_03

Step 10 (Merge Values):
  Operation: INSERT_SELECT
  Driver Table: l_bcs_loaddb.BC_HISTORY_new_month_billsort (histtab)
  Driver Conditions: []
  Join 1 Table: l_bcs_loaddb.edf_01 (edf01)
  Join 1 Type: LEFT
  Join 1 On: histtab.logical_account_id = edf01.logical_account_id
  Join 1 Filters: []
  Join 2 Table: l_bcs_loaddb.edf_02 (edf02)
  Join 2 Type: LEFT
  Join 2 On: histtab.logical_account_id = edf02.logical_account_id
  Join 2 Filters: []
  Join 3 Table: l_bcs_loaddb.edf_03 (edf03)
  Join 3 Type: LEFT
  Join 3 On: histtab.logical_account_id = edf03.logical_account_id
  Join 3 Filters: []
  Columns:
    EDF_Value = CASE WHEN COALESCE(edf03.edf_value, edf02.edf_value, edf01.edf_value) >= 0.9999995 THEN 0.999999 ELSE COALESCE(edf03.edf_value, edf02.edf_value, edf01.edf_value) END [New]
  Grain: logical_account_id
  Destination: l_bcs_loaddb.rskm_fields
---
Effective Source Filters:
  l_bcs_loaddb.BC_HISTORY_new_month_billsort: behaviour_score_raw > 31, substr(account_status_code,1,1) NOT IN ('A','B','E','K','O'), account_status_code = 'K0'
```

**Output for non-key column `EXPECTED_DEFAULT_FREQ`:**

One row, one cell — the per-column chain is newline-separated text in a single `business_logic` cell:
```
Step 1: EDF_Value = 1/(1+EXP((edf.score * ach.behaviour_score_raw) + (edf.genscore * gscore) + edf.dummy_value + (edf.pivot_value * ach.behaviour_score_raw) + edf.intercept + tbooks + (edf.balance_climit * baltoclm))) [New]
Step 10: EDF_Value = CASE WHEN COALESCE(edf03.edf_value, edf02.edf_value, edf01.edf_value) >= 0.9999995 THEN 0.999999 ELSE COALESCE(edf03.edf_value, edf02.edf_value, edf01.edf_value) END [Transformed]
```

**Note:** Both examples above produce exactly **1 row each** in the Excel output. The multi-step content is newline-separated text within a single `business_logic` cell, not multiple rows. The full rskm_fields pipeline has 10 intermediate steps but the Mapping sheet has exactly one row for `EXPECTED_DEFAULT_FREQ`.

**Single-cell constraint:** Every example above produces exactly ONE row per target column. Multi-step logic is newline-separated text within a single `business_logic` cell — never split across rows.

**Backward Compatibility:** Single-statement SQL is unaffected — `intermediate_steps` is empty and no lineage chain is appended.
