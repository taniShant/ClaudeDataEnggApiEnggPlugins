---
description: "Conditional STTM extension for multi-step ETL rendering — defines rules for CREATE/INSERT, UPDATE, DELETE, TRUNCATE, MERGE steps with column tagging ([New]/[Transformed]) and effective source filters."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-28
---

# Multi-Step ETL & View Resolution Patterns (Extension)

> **Loaded conditionally** — only when `intermediate_steps` is non-empty in the lineage data.

## 24. Multi-Step ETL Chain (Intermediate Table Pattern)

**Detection:** sttm-sql-lineage-agent returns non-empty `intermediate_steps[]` with 2+ entries (multi-statement ETL with intermediate temp tables).

**Template Output:**
- Business Logic (first key column row): Full transformation lineage chain appended after `---\nTransformation Lineage:` divider
- Business Logic (non-key column with `chain_depth > 1`): Column-specific chain showing steps where the column is new or transformed; pass-through steps as one-liners
- Transformation Type: As determined by the final step's expression

**Step Rendering Rules:**
- **CREATE/INSERT steps:** Show FROM, JOINs with conditions, Columns with `[New]`/`[Transformed]` tags, `Grain:` annotation, `→ intermediate_table`
- **UPDATE steps:** Show SET columns with assignment mode (`[Replace]`/`[Additive]`/`[Conditional]`), FROM/ON scope
- **DELETE steps:** Show WHERE condition and `[Partial removal]` tag
- **TRUNCATE steps:** Show `[Full removal]` tag
- **MERGE steps:** Show Match Key, WHEN MATCHED, WHEN NOT MATCHED branches
- **Pass-through** in column chains: Render as `Step N: pass-through` (one line) to maintain step numbering continuity

**Post-Chain Blocks:**
- `Effective Source Filters:` — Cumulative filter summary per base source table (from `effective_source_filters`)
- `Variables:` — Resolved DECLARE/SET variables (from `resolved_variables`, when present)

**Example 1 — Key column row (complete, rskm_fields variant-merge pattern):**

All content below is ONE cell value in ONE Excel row (newline-separated text, wrap_text=True):
```
Driver Table: l_bcs_loaddb.BC_HISTORY_new_month_billsort (bh)
Join 1: LEFT JOIN l_bcs_loaddb.rskm_fields (rsk) ON bh.logical_account_id = rsk.logical_account_id [Filter bh.purge_flag = 'N']
Value: COALESCE(amx.NBR_ACCT_TGT, bh.logical_account_id)
---
Transformation Lineage:
Step 1 (EDF normal): FROM l_bcs_loaddb.BC_HISTORY_new_month_billsort (ach)
  INNER JOIN A_BCS_REFDB.edf_parms (edf) ON ach.behaviour_scorecard_identifier = edf.scorecard
  [Filter ach.behaviour_score_raw > 31, substr(ach.account_status_code,1,1) NOT IN ('A','B','E','K','O')]
  Columns: EDF_Value = 1/(1+EXP((edf.score * ach.behaviour_score_raw) + (edf.genscore * gscore) + edf.dummy_value + (edf.pivot_value * ach.behaviour_score_raw) + edf.intercept + tbooks + (edf.balance_climit * baltoclm))) [New]
  Grain: logical_account_id
  → edf_01

Step 2 (EDF scorecard 9): FROM A_BCS_REFDB.edf_parms_s9 (edfs9)
  INNER JOIN l_bcs_loaddb.BC_HISTORY_new_month_billsort (ach) ON ach.behaviour_score_raw BETWEEN edfs9.lower_score AND edfs9.upper_score
  [Filter ach.behaviour_scorecard_identifier = 9, ach.behaviour_score_raw > 31]
  Columns: EDF_Value = edfs9.score [New]
  Grain: logical_account_id
  → edf_02

Step 3 (EDF status K0): FROM l_bcs_loaddb.BC_HISTORY_new_month_billsort (bch)
  INNER JOIN A_BCS_REFDB.edf_parms_k0 (edf) ON bch.delinquency = edf.delinquency
  [Filter bch.account_status_code = 'K0']
  Columns: EDF_Value = edf.EDF_value [New]
  Grain: logical_account_id
  → edf_03

Step 10 (Merge Values): FROM l_bcs_loaddb.BC_HISTORY_new_month_billsort (histtab)
  LEFT JOIN l_bcs_loaddb.edf_01 (edf01) ON histtab.logical_account_id = edf01.logical_account_id
  LEFT JOIN l_bcs_loaddb.edf_02 (edf02) ON histtab.logical_account_id = edf02.logical_account_id
  LEFT JOIN l_bcs_loaddb.edf_03 (edf03) ON histtab.logical_account_id = edf03.logical_account_id
  Columns: EDF_Value = CASE WHEN COALESCE(edf03.edf_value, edf02.edf_value, edf01.edf_value) >= 0.9999995 THEN 0.999999 ELSE COALESCE(edf03.edf_value, edf02.edf_value, edf01.edf_value) END [New]
  Columns: BRG_Value = CASE WHEN brgedf < .0015 THEN '1' WHEN brgedf < .003 THEN '2' WHEN brgedf < .006 THEN '3' WHEN brgedf < .012 THEN '4' WHEN brgedf < .025 THEN '5' WHEN brgedf < .050 THEN '6' WHEN brgedf < .100 THEN '7' WHEN brgedf < 1 THEN '8' ELSE NULL END [New]
  Grain: logical_account_id
  → rskm_fields
---
Effective Source Filters:
  l_bcs_loaddb.BC_HISTORY_new_month_billsort: behaviour_score_raw > 31, substr(account_status_code,1,1) NOT IN ('A','B','E','K','O'), account_status_code = 'K0'
```

**Example 2 — Non-key column chain for `EXPECTED_DEFAULT_FREQ` (chain_depth=2):**

All content below is ONE cell value in ONE Excel row:
```
Step 1: EDF_Value = 1/(1+EXP((edf.score * ach.behaviour_score_raw) + (edf.genscore * gscore) + edf.dummy_value + (edf.pivot_value * ach.behaviour_score_raw) + edf.intercept + tbooks + (edf.balance_climit * baltoclm))) [New]
Step 10: EDF_Value = CASE WHEN COALESCE(edf03.edf_value, edf02.edf_value, edf01.edf_value) >= 0.9999995 THEN 0.999999 ELSE COALESCE(edf03.edf_value, edf02.edf_value, edf01.edf_value) END [Transformed]
```

**Example 3 — Non-key column chain with UPDATE-back (chain_depth=3):**

All content below is ONE cell value in ONE Excel row:
```
Step 1: PAYMENTS_RECEIVED = SUM(pc.AMT_PYMT_1 + pc.AMT_PYMT_2 + pc.AMT_PYMT_3 + pc.AMT_PYMT_4 + pc.AMT_PYMT_5 + pc.AMT_PYMT_6 + pc.AMT_PYMT_7 + pc.AMT_PYMT_8 + pc.AMT_PYMT_9 + pc.AMT_PYMT_10 + pc.AMT_PYMT_11 + pc.AMT_PYMT_12) [New]
Step 3: pass-through
Step 4: SET PAYMENTS_RECEIVED = EPP_PAYMENTS_UPDATE.AMT_PYMT_PRCH [Transformed, Replace]
Step 5: pass-through
```

**Single-cell constraint:** Every example above produces exactly ONE row per target column. Multi-step logic is newline-separated text within a single `business_logic` cell — never split across rows.

**Backward Compatibility:** Single-statement SQL is unaffected — `intermediate_steps` is empty and no lineage chain is appended.

---

## 26. View Resolution (Intermediate Step Type)

**Detection:** sttm-sql-lineage-agent encounters CREATE VIEW in the code artifacts AND emits the view as a `statement_type: CREATE_VIEW` intermediate step.

**Template Output — in Transformation Lineage block:**

View steps are rendered as CREATE_VIEW intermediate steps with a `Resolves to:` annotation showing the ultimate base tables:

```
Step N (label): CREATE VIEW <view_name>
  FROM <base_table> (<alias>)
  [QUALIFY/WHERE conditions]
  Columns: <col1> = <alias>.<source_col1> [New], <col2> = <alias>.<source_col2> [New]
  Grain: <grain_columns>
  → <view_name>
  Resolves to: <base_table1>, <base_table2>
```

**Rules:**
- View resolution appears as an intermediate step in the Transformation Lineage block — NOT as ad-hoc text in business_logic
- `Resolves to:` lists the ultimate base tables (after resolving nested view chains). For a simple view over one table, list that table. For views over multiple joined tables, list all.
- Columns produced by the view are listed with their source column mapping and `[New]` tag
- For columns that trace through a view, the per-column chain (`Step N: ...`) includes the view step
- Source attribution (columns G/H/I) always references the BASE tables, not the view name
- When the view DDL is not available, the sttm-sql-lineage-agent logs a warning and treats the view as a base table — no CREATE_VIEW step is emitted

**Example — Prior_Cycle_v view (Billing Hist Hist110):**

```
Step 1 (Hist110): CREATE VIEW Prior_Cycle_v
  FROM s_trmfdb.ctcp (ctcp)
  [QUALIFY CSUM(1, NBR_CARDH_ACCT, TIME_LAST_UPD DESC) = 1]
  Columns: Account_Number = ctcp.NBR_CARDH_ACCT [New], Credit_Limit = ctcp.AMT_CRED_LMT [New], Date_Last_Cash_Advance = ctcp.DATE_LAST_CASH_ADVANCE [New]
  Grain: Account_Number
  → Prior_Cycle_v
  Resolves to: s_trmfdb.ctcp
```

**WRONG (ad-hoc narrative text — FORBIDDEN):**
```
pc traces to s_trmfdb.ctcp via Prior_Cycle_v view (Hist110)
Ultimate sources: pc traces to s_trmfdb.ctcp via Prior_Cycle_v view (Hist110)
```

**RIGHT (structured step in Transformation Lineage block):**
Use the CREATE VIEW step format above. The view resolution is part of the numbered step chain, not a free-text annotation.
