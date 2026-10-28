---
description: "Data Validation check patterns for all table types — exact reconciliation, SCD2 temporal, and NOT_EVALUATED patterns for row-level and aggregate comparison, loaded by dv-validation-plan-agent."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-26
---

# Data Validation Patterns Reference

Loaded by `dv-validation-plan-agent` for all table types. Defines exact reconciliation, SCD2 temporal, and NOT_EVALUATED patterns.

## Exact Reconciliation Patterns

### Row-Level Reconciliation (ER-05, ER-06, ER-07)
- Join source (with mapping transforms applied) to target via FULL OUTER JOIN on primary key columns
- ER-05: Rows where source PK is NULL = TARGET_ONLY; rows where target PK is NULL = SOURCE_ONLY — both counts must be zero
- ER-06: For matched rows (INNER JOIN on PK), compare each non-audit, non-crypto column value — mismatch count must be zero
- EXCEPT/EXCEPT ALL is NOT used for PK-based reconciliation — it cannot identify which specific rows or columns differ
- For SCD2 tables: both source and target subqueries MUST be filtered to the same point-in-time using eff_start_date/eff_end_date range predicates (from contract.scd2_metadata) BEFORE the join — this prevents cross-version fan-out

### Aggregate Reconciliation
- COUNT, SUM, MIN, MAX comparison per column
- MIN/MAX (ER-03) applies to non-key business columns only — primary key columns are excluded (MIN/MAX on surrogate keys is not meaningful for data quality)
- Source aggregates computed after applying mapping transforms
- Target aggregates computed directly

### Keyless Table Reconciliation
- Multiset comparison using GROUP BY all columns with COUNT(*) as frequency
- Source and target frequency CTEs joined with FULL OUTER JOIN
- Any row where COALESCE(src.row_freq, 0) != COALESCE(tgt.row_freq, 0) is a mismatch

### Tolerance Policy: ZERO
- **Explicitly forbids** epsilon, percentage, threshold tolerance
- Decimal: compare after applying documented DECIMAL(p,s) cast
- If precision/rounding undocumented → NOT_EVALUATED
- Floating-point: no automatic epsilon; warning + NOT_EVALUATED if exact comparison infeasible
- Timestamp: compare after documented tz/precision/truncation; if precision differs undocumented → NOT_EVALUATED

## Reconciliation Filter Derivation

Both source and target must be filtered to the same logical point-in-time before reconciliation counts or aggregates are compared. The filter is derived in priority order:

**Anti-hallucination**: All column names and predicates used in filters MUST come from `contract.columns[]`, `contract.scd2_metadata`, or the mapping document. Never invent or assume a column name, table name, or function.

**Priority 1 — Mapping-explicit**: If mapping states an explicit filter predicate for source or target, use it verbatim.

**Priority 2 — SCD2 (NonTransactional_SCD2)**: Use as-of date-range for both sides, using column names read from `contract.scd2_metadata.eff_start_date_source` and the `eff_end_date` entry in `contract.columns[]`. Filter form: `<eff_start_col> <= DATE '{{control_date}}' AND <eff_end_col> > DATE '{{control_date}}'`.

**Note on `>` vs `>=`**: BUK CDAO convention defines `eff_end_date` as INCLUSIVE, yet the filter uses strict `>`. This is intentional — it is the **boundary deduplication rule**. At the boundary date where `prev.eff_end_date = next.eff_start_date` (the BUK continuity convention), using `>` ensures only the successor record is selected, preventing double-counting in reconciliation. When `control_date` lands exactly on a version boundary (`control_date = prev.eff_end_date = next.eff_start_date`), the filter intentionally selects the successor record and excludes the predecessor — this is the correct and expected behavior under BUK CDAO continuous-history convention. For the active record (`eff_end_date = '3499-12-31'`), `> control_date` is always TRUE. This filter assumes BUK CDAO continuous history where a successor always exists; if an entity expires without a successor, the expired record is excluded on its final day — this is accepted by convention.

Note: `active = '1'` must NOT be used as an ER filter — it captures records open at query time, not records active as of control_date.

**Priority 3 — Transactional / NonTransactional_SCD1**: Use batch/partition date column name from `mapping.partition_key_hint` or `additional_context`. Filter form: `<batch_date_col> = DATE '{{control_date}}'`. If not documented → populate `source_filter = "1 = 1"` as no-op and add `assumptions_and_gaps` entry.

**Do not apply reconciliation filters to**: SCD2 structural checks (SCD2-01 to SCD2-11), NC, DC, or DT checks.

## SCD2 Temporal Patterns

Aligned with `transform-temporal-stitching-reference.md`.

### BUK CDAO Date Convention
- **eff_end_date is INCLUSIVE**: `prev.eff_end_date = next.eff_start_date` for continuity
- Sentinel: `'3499-12-31'` for active records
- Active flag: `active = '1'` when `eff_end_date = '3499-12-31'`, `'0'` otherwise
- At most one active record per PK; zero if entity is expired

### Overlap Detection
- Formula: `prev.eff_end_date > next.eff_start_date`
- Uses LEAD window: `LEAD(eff_start_date) OVER (PARTITION BY {{pk_columns}} ORDER BY eff_start_date)`
- Any overlap is severity: blocker

### Gap Handling — Configurable Per Mapping
**Gaps are NOT always prohibited.** The existing `transform-temporal-stitching-reference.md` documents that source data may have legitimate gaps.

- If mapping states "continuous history required" → `severity: blocker`
- If mapping documents explicit gaps as valid → gap check is **not generated** (omitted)
- If mapping is silent on gap policy → `severity: warning` with note: "Gap policy not documented"

### Boundary Stitching
- For each consecutive pair within contiguous segments: `prev.eff_end_date = next.eff_start_date`
- Not checked across documented gaps

### Active Record Invariant
- `COUNT(*) WHERE active = '1' GROUP BY pk HAVING COUNT > 1` must be zero
- At most one active record per PK

### Day 0 Checks
- One version per PK
- active flag correct (= '1')
- eff_end = sentinel ('3499-12-31')
- Source population = target population

### Day 1 Checks
- Tracked change: exactly one closed + one new version
- New key: single version, active flag correct
- No-change: no new version created
- Late-arriving: restitch predecessors/successors
- Multi-change: correct ordering for multiple changes on same day

## Expression Preservation Rule

From anti-hallucination-core. When constructing validation SQL from mapping business_logic:
- NEVER summarize IN-list values — preserve every literal value. Exception: for IN-lists exceeding 100 values, preserve the first 10 and last 10 values with a comment `-- ... {N} total values from mapping ...` and add a NOT_EVALUATED entry with reason `"IN-list too large for exact preservation (>100 values) — manual review required"`.
- NEVER replace numeric thresholds with descriptions
- NEVER paraphrase filter predicates — use exact SQL from mapping
- NEVER invent column aliases not in the mapping
- If business_logic is absent or ambiguous → NOT_EVALUATED, never fabricate

## NOT_EVALUATED Conditions Catalog

This is the **single authoritative list** of all NOT_EVALUATED conditions. The plan agent references this catalog — it must not maintain a separate list.

### Cross-Cutting Conditions (affect multiple check categories)

| Condition | Affected Checks | Reason Text |
|-----------|----------------|-------------|
| Missing `business_logic` for column | ER-07, BR-01, BR-03, BR-04 | `"business_logic is null/empty — cannot determine expected transformation"` |
| Missing `scd2_metadata` for SCD2 table | SCD2-01 through SCD2-18 | `"scd2_metadata absent — cannot construct temporal invariant checks"` |
| Missing source table reference | ER-01 through ER-08, BR-04 | `"source table/column reference missing — cannot reconcile"` |
| Source table not accessible from validation engine | ER-01 through ER-08 | `"source table not accessible — cross-platform access limitation"` |
| Ambiguous transformation semantics | ER-05, ER-06, ER-07 | `"transformation_logic is ambiguous — manual review required"` |
| Unknown aggregation pattern | ER-02, BR-04 | `"aggregation pattern not recognized — cannot generate reconciliation SQL"` |
| IN-list exceeds 100 literal values | ER-07, BR-01, BR-03, BR-04 | `"IN-list too large for exact preservation (>100 values) — manual review required"` |

### Numeric / Precision Conditions

| Condition | Affected Checks | Reason Text |
|-----------|----------------|-------------|
| Column is non-numeric (SUM not applicable) | ER-02 | `"column is non-numeric — SUM reconciliation not applicable"` |
| Missing source precision metadata | DT-02, DT-03 | `"precision/scale not documented in mapping — cannot verify"` |
| Floating-point column without documented cast | ER-02, ER-07 | `"floating-point without documented cast — exact comparison infeasible"` |
| Missing rounding rule for differing decimal scales | ER-02, ER-07 | `"rounding rule not documented — cannot determine comparison behavior"` |
| Timestamp precision mismatch without documented conversion | ER-02, ER-07 | `"timestamp precision differs without documented conversion — cannot align"` |

### Type / Domain Conditions

| Condition | Affected Checks | Reason Text |
|-----------|----------------|-------------|
| Missing `source_datatype` for type check | DT-01 | `"source_datatype not specified — cannot validate type conversion"` |
| No domain/enum documented in `business_logic` | BR-01 | `"no domain or enum set documented — cannot validate value domain"` |
| Reference table not accessible | BR-02 | `"reference table not accessible — cannot validate referential integrity"` |

### SCD2-Specific Conditions

| Condition | Affected Checks | Reason Text |
|-----------|----------------|-------------|
| Missing gap policy for SCD2 | SCD2-02 | `"gap policy not documented — defaulting to warning severity"` |
| Ambiguous temporal boundary convention | SCD2-03 | `"temporal boundary convention unclear — should not occur for BUK CDAO"` |
| Source history unavailable for change completeness | SCD2-14 through SCD2-18 | `"source history unavailable — Day 1 checks require access to previous state"` |
| `version_number` column not present | SCD2-09 | `"version_number column not present in contract columns — check not applicable"` |

### Structural Conditions

| Condition | Affected Checks | Reason Text |
|-----------|----------------|-------------|
| Table has no PK and columns exceed comparison threshold | ER-08 | `"no primary key and column count exceeds multiset comparison threshold"` |
