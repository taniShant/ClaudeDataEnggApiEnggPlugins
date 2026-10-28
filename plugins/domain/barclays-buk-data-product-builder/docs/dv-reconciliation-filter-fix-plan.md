# Plan: Fix Missing Reconciliation Filters in Validation Plan Agent

## Context

The generated validation SQL for `fdp_uk_ukba_db.account_balance` has two related issues:

1. **No filter on source table** — all ER-01 through ER-07 source-side queries scan the full table with no WHERE clause
2. **Wrong filter on target** — `active = '1'` is used instead of the correct as-of control_date SCD2 date-range filter

Root cause: `dv-validation-plan-agent.md` has no instruction to derive `source_filter` / `target_filter` and populate them into each ER check's `parameters{}`. The renderer, receiving no filter fields, dropped the source WHERE entirely and inferred `active = '1'` on the target — violating its own anti-hallucination rule.

This is a gap in the **plugin instruction files** at `barclays-buk-data-product-builder/`. Fixing it there ensures correct generation for all future runs and all table types.

---

## Scope: Which Checks Need Filters

Only **reconciliation checks** compare source vs. target — they need as-of-date filtering on both sides. Structural checks scan all rows by design and are unaffected.

| Check Category | Needs filter? | Rationale |
|---|---|---|
| **ER-01 to ER-08** (exact reconciliation) | ✅ Yes | Source-to-target comparison must align to same point-in-time |
| **BR-04** (aggregate reconciliation) | ✅ Yes (target only) | Reconciliation against source; same logic as ER |
| SCD2-01–SCD2-11 (structural temporal) | ❌ No | Must validate ALL versions, not a time-slice |
| SCD2-04, SCD2-05, SCD2-06, SCD2-07 (`active` flag checks) | ❌ Correct as-is | `active` is the subject of these checks, not a filter criterion |
| NC, DC, DT | ❌ No | Structural checks on all rows |

---

## Correct Filters Per Table Type

Gap analysis applies to **all table types** (Transactional, NonTransactional_SCD1, NonTransactional_SCD2).

**Anti-hallucination constraint — applies to all filter derivation**:
> All column names, table names, database names, and filter predicates used in `source_filter` / `target_filter` must be read directly from the **mapping document / contract** (`columns[]`, `source_references[]`, `scd2_metadata`). No agent or skill may invent, assume, or guess any column name, table name, filter predicate, or SQL function. Audit columns (`is_audit_column: true`) are excluded from source reconciliation but SCD2 temporal audit columns (`eff_start_date`, `eff_end_date`) are used for the filter itself.

| Table Type | Source Filter | Target Filter | Column source |
|---|---|---|---|
| **NonTransactional_SCD2** | `{src_eff_start_col} <= DATE '{{control_date}}' AND {src_eff_end_col} > DATE '{{control_date}}'` | `{tgt_eff_start_col} <= DATE '{{control_date}}' AND {tgt_eff_end_col} > DATE '{{control_date}}'` | Column names read from `contract.scd2_metadata.eff_start_date_source` and the `eff_end_date` column in `contract.columns[]` |
| **NonTransactional_SCD1** | Explicit filter from mapping if documented; else no filter (full snapshot) | No filter (SCD1 current state = full table) | Read from mapping `additional_context` or column with `transformation_type = "snapshot_date"` |
| **Transactional** | Batch/partition date column from mapping `partition_key_hint` or `additional_context` | Same predicate on target | Column name read from mapping `partition_key_hint[]` or documented batch date column |

**Priority order for filter derivation** (all table types):
1. Explicit filter predicate stated in the mapping document → use verbatim, column name from mapping
2. SCD2 table → date-range predicate using column names from `contract.scd2_metadata` and `contract.columns[]`
3. Transactional/SCD1 → predicate using column name from `mapping.partition_key_hint` or `additional_context`
4. No filter determinable from mapping → populate `source_filter = "1 = 1"` (no-op) and add `assumptions_and_gaps` entry with reason

---

## Files to Fix (Plugin Instructions Only)

Session artefacts (`dv_validation_plan_*.json`, generated SQL) are **regenerated**, not patched manually.

### Fix 1: `dv-validation-plan-agent.md`

**File**: `agents/dv-validation-plan-agent.md`

**Change**: Add **Step 3b** in the Validation Plan Construction Algorithm (after current step 3, before step 4):

> **Step 3b — Derive reconciliation filter pair per table type**
>
> For all **ER** checks (ER-01 through ER-08) and **reconciliation BR checks** (e.g. BR-04):
>
> **Priority 1 — Mapping-explicit filter**: If the mapping document explicitly states a source or target filter predicate, use that verbatim. Column names must come from the mapping.
>
> **Priority 2 — SCD2 (NonTransactional_SCD2)**: When source or target is SCD2:
> - Read `eff_start_date` column name from `contract.scd2_metadata.eff_start_date_source`
> - Read `eff_end_date` column name from the matching entry in `contract.columns[]`
> - `source_filter = "<src_eff_start_col> <= DATE '{{control_date}}' AND <src_eff_end_col> > DATE '{{control_date}}'"`
> - `target_filter = "<tgt_eff_start_col> <= DATE '{{control_date}}' AND <tgt_eff_end_col> > DATE '{{control_date}}'"`
>
> **Priority 3 — Transactional / NonTransactional_SCD1**: Read batch/partition date column from `mapping.partition_key_hint` or `additional_context`. If documented, use `<batch_date_col> = DATE '{{control_date}}'`. If not documented, set `source_filter = "1 = 1"` and record in `assumptions_and_gaps`.
>
> **Populate both `source_filter` and `target_filter` into `parameters{}`** for every applicable check. Do NOT apply to SCD2 structural checks (SCD2-01–SCD2-11), NC, DC, DT checks.
>
> **CRITICAL**: Column names, table names, database names, and filter predicates MUST be read from `contract.columns[]`, `contract.scd2_metadata`, or `mapping.partition_key_hint`. Never invent or assume any column name, table name, or function.

**Change**: Add three anti-hallucination rules:
> ❌ Never omit `source_filter` from ER check `parameters{}` — derive per Priority 1/2/3 logic above  
> ❌ Never use `active = '1'` as an ER reconciliation `target_filter` — this is a current-state shortcut, not a point-in-time predicate; use the as-of date-range predicate for SCD2  
> ❌ Never invent column names, table names, database names, filter predicates, or SQL functions — use ONLY values read from `contract.columns[]`, `contract.scd2_metadata`, and the mapping document

### Fix 2: `dv-validation-patterns.md`

**File**: `agents/refs/dv-validation-patterns.md`

**Change**: Add a new section **"Reconciliation Filter Derivation"** (to be inserted after "Exact Reconciliation Patterns"):

> ### Reconciliation Filter Derivation
>
> Both source and target must be filtered to the same logical point-in-time before reconciliation counts or aggregates are compared. The filter is derived in priority order:
>
> **Anti-hallucination**: All column names and predicates used in filters MUST come from `contract.columns[]`, `contract.scd2_metadata`, or the mapping document. Never invent or assume a column name, table name, or function.
>
> **Priority 1 — Mapping-explicit**: If mapping states an explicit filter predicate for source or target, use it verbatim.
>
> **Priority 2 — SCD2 (NonTransactional_SCD2)**: Use as-of date-range for both sides, using column names read from `contract.scd2_metadata.eff_start_date_source` and the `eff_end_date` entry in `contract.columns[]`:
> ```sql
> <eff_start_col_from_contract> <= DATE '{{control_date}}'
> AND <eff_end_col_from_contract> > DATE '{{control_date}}'
> ```
> Note: `active = '1'` must NOT be used as an ER filter — it captures records open at query time, not records active as of control_date.
>
> **Priority 3 — Transactional / NonTransactional_SCD1**: Use batch/partition date column name from `mapping.partition_key_hint` or `additional_context`:
> ```sql
> <batch_date_col_from_mapping> = DATE '{{control_date}}'
> ```
> If not documented → populate `source_filter = "1 = 1"` as no-op and add `assumptions_and_gaps` entry.
>
> **Do not apply reconciliation filters to**: SCD2 structural checks (SCD2-01 to SCD2-11), NC, DC, or DT checks.

---

## What Remains Correct (No Change)

- `agents/dv-athena-renderer-agent.md` — the renderer's no-inference rule is correct; the gap is upstream
- `agents/refs/dv-athena-sql-patterns.md` — `{{source_filter}}` / `{{target_filter}}` placeholders are already correct
- `agents/dv-databricks-renderer-agent.md` — same no-inference rule as Athena renderer; gap is upstream
- `agents/refs/dv-databricks-sql-patterns.md` — `{{source_filter}}` / `{{target_filter}}` placeholders are already correct
- SCD2 structural check logic (SCD2-04/05/06/07 `active` usage) — correct by design
- `configs/dv/validation_checks.yaml` — check definitions are correct; filter derivation is an agent-level concern

---

## Verification (after regeneration)

1. Re-run `dv-validation-plan-agent` → `dv_validation_plan_account_balance.json` should now have `source_filter` and `target_filter` in all 7 ER check and BR-04 `parameters{}`
2. Re-run `dv-athena-renderer-agent` → regenerated SQL should have date-range WHERE on both source and target for ER-01–ER-07 and BR-04
3. Grep generated SQL: `WHERE active = '1'` should appear ONLY in SCD2-04, SCD2-05, SCD2-06 structural checks — NOT in ER or BR-04
4. Grep generated SQL: every `FROM e_ukba_db.tehblnc` in ER checks should be followed by the date-range WHERE
5. Smoke test: at execution time with `{{control_date}} = 2026-09-25`, source count should equal target count when ETL is correct
