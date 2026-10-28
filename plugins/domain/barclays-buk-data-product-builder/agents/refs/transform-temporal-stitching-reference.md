---
description: "Temporal stitching logic for SCD2 target tables on Day0 — covers inclusive date convention (eff_end_date), temporal continuity checks, gap detection, and period collapsing building block."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-07-08
---

# Temporal Stitching Reference

## Temporal Stitching Logic for SCD2 Target table for day 0

Teams MUST declare their SCD2 temporal stitching approach in domain knowledge OR in the
mapping Excel's transformation_logic column for the eff_start_date target row.
This applies to ALL NonTransactional_SCD2 tables — both single-source and multi-source. NOT applicable to NonTransactional_SCD1 (no eff_start_date/eff_end_date exist).

### Date Convention (Universal — BUK CDAO Standard)

eff_end_date is INCLUSIVE — the record is valid INCLUDING eff_end_date.
Temporal continuity: eff_end_date of previous record = eff_start_date of next record.
Source data is EXPECTED to be continuous — no gaps between consecutive records for the same PK.
If gaps exist (precondition violated), Period Collapsing (Building Block 2) detects and preserves
them rather than silently bridging. See Step 5b and Step 7 gap-aware logic below.

Example:
  Record 1:  eff_start_date = 2025-01-01,  eff_end_date = 2025-07-01
  Record 2:  eff_start_date = 2025-07-01,  eff_end_date = 2025-12-31
  (Continuous — Record 1 ends where Record 2 starts)

Sentinel value: eff_end_date = '3499-12-31' → currently active record (open-ended).

### Universal vs Team-Specific Audit Columns

| Column           | Derivation                                            | Who Defines        |
|------------------|-------------------------------------------------------|--------------------|
| eff_start_date   | Temporal stitching logic                              | TEAM-SPECIFIC      |
| eff_end_date     | Temporal stitching logic                              | TEAM-SPECIFIC      |
| active           | '1' when eff_end_date = '3499-12-31', '0' otherwise  | UNIVERSAL (BUK CDAO) |
| dw_lod_tmp       | current_timestamp()                                   | UNIVERSAL          |
| dw_upd_lod_tmp   | current_timestamp()                                   | UNIVERSAL          |

Only eff_start_date and eff_end_date derivation comes from domain knowledge or mapping.
active, dw_lod_tmp, dw_upd_lod_tmp are ALWAYS framework-derived using the rules above.

### Applicability

Temporal stitching applies to BOTH eff_start_date AND eff_end_date — not just eff_end_date.
Both columns are derived together as part of the stitching logic.
Applies to ALL SCD2 tables: single-source AND multi-source.

### Post-Stitching Invariants (MANDATORY — all patterns must satisfy)

After any temporal stitching pattern is applied, the resultant dataset MUST satisfy:

1. No redundant durations (adjacent records for same pk with unchanged business cols are collapsed)

2. BUSINESS MEANING PRESERVED: The stitched result must represent the same semantic
   truth as the source data. Collapsing or splitting periods must NOT alter what
   business values were effective during any point in time.

3. TEMPORAL CONTINUITY (conditional):
   a. If source data is continuous (precondition holds): for any PK with multiple versions,
      when ordered by eff_start_date, each record's eff_end_date = next record's eff_start_date
      (no gaps, no overlaps).
   b. If source data has gaps (precondition violated): gaps are PRESERVED in the output —
      a record's eff_end_date may be < next record's eff_start_date (gap). Overlaps are
      still prohibited (eff_end_date > next eff_start_date is always an error).

4. EXACTLY ONE ACTIVE (at most): For each PK, at most one record has active='1'
   (the one with eff_end_date = '3499-12-31'). If the source entity is still active,
   exactly one record has active='1'. If the entity is expired/deactivated (last source
   record has eff_end_date < '3499-12-31'), zero records have active='1' — all are '0'.

If any pattern produces output violating these invariants, it indicates a logic error
in the stitching implementation.

### Multi-Source SCD2: Effective-Period-Start Join

When multiple SCD2 source tables (each with their own eff_start_date/eff_end_date) are joined
to produce a target SCD2 table, the target's temporal ranges must be SPLIT at every source
transition point to maintain temporal consistency.

Strategy: Collect all breakpoints from all source tables, create time slices, and for each
slice join the version of each source that was active at that point.

Example:
  Driving Table (customer):
    Period 2025-01-01 → 2025-12-31 (annual)
  Subordinate Table (address):
    Period 1: 2025-01-01 → 2025-07-01  "100 Oak Ave"
    Period 2: 2025-07-01 → 2025-12-31  "200 Pine St"
  
  Backfill Result (1 driving record becomes 2):
    Record 1: 2025-01-01 → 2025-07-01  address = "100 Oak Ave"
    Record 2: 2025-07-01 → 2025-12-31  address = "200 Pine St"

  Source data is continuous: eff_end_date of Record 1 = eff_start_date of Record 2.
  No gaps, no overlaps. Business meaning of each period preserved.

  NOTE: After the period-start join, if adjacent slices produce identical business column
  values (e.g., subordinate didn't actually change at that breakpoint for the target columns),
  those slices MUST be collapsed to avoid redundant durations (apply Period Collapsing).

Edge Cases:
  - Multiple transitions: 3 source changes within one driving period → 4 output records
  - N subordinate tables: collect ALL breakpoints from ALL sources → produce slices
  - Partial coverage: subordinate starts after driving period (handled by left join)
  - Overlapping source periods: detected and raised as errors

### Single-Source SCD2: Two Scenarios

Scenario A — All source columns mapped to target (direct carry-forward):
  If every source column is included in the target, eff_start_date and eff_end_date
  can be carried forward directly from source with no re-derivation needed.
  (No redundant durations since source is already non-redundant — every version
  has at least one column change.)

Scenario B — Subset of source columns mapped to target (period collapsing):
  When only a SUBSET of source columns maps to the target, adjacent source records
  that are identical on the target columns can be COLLAPSED into a single larger period.
  This eliminates redundant durations where business meaning (on target columns) is unchanged.

  Constraint: Business semantic meaning must NOT change from collapsing. Only collapse
  CONSECUTIVE records (ordered by eff_start_date) where target columns are unchanged.
  Records with matching values that are NOT adjacent (separated by a change) must NOT
  be merged — they represent distinct temporal versions.

  Algorithm (islands-and-gaps pattern):
    1. Order source records by PK + eff_start_date
    2. Hash target business columns for each record
    3. Compare each record's hash with PREVIOUS record's hash via LAG window
    4. Mark a new group boundary wherever hash differs from previous (or first row)
    5. Assign group IDs via cumulative sum of boundary flags
    5b. (Gap-aware boundary) Additionally mark a boundary wherever the PREVIOUS record's
        source eff_end_date != current record's source eff_start_date (temporal gap).
        Combined boundary flag = hash_changed OR gap_detected.
        This ensures records separated by a gap are NEVER collapsed into one group,
        even if their business column hashes match.
        For continuous data this is a no-op (prev eff_end always == current eff_start).
        NOTE: Step 5b executes BEFORE step 5's cumulative sum — the combined boundary
        flag (hash OR gap) feeds into group ID assignment.
    6. Per group: eff_start_date = MIN(source eff_start_date) within group
    7. Per group: derive eff_end_date (gap-aware):
         next_group_start = LEAD(eff_start_date) of NEXT group
         group_max_end    = MAX(source eff_end_date) within current group

         eff_end_date = CASE
           WHEN next_group_start IS NULL THEN group_max_end
              -- Last group: preserve source terminal end date
           WHEN next_group_start != group_max_end THEN group_max_end
              -- GAP DETECTED: next group starts after current ends → preserve actual end
           ELSE next_group_start
              -- CONTINUOUS: next group starts where current ends (backward compatible)
         END

       Behaviour summary:
       - Continuous data (precondition holds): next_group_start == group_max_end for all
         non-last groups, so ELSE branch fires → identical output to previous algorithm
       - Gap detected (precondition violated): next_group_start > group_max_end,
         second WHEN fires → preserves source eff_end_date, gap remains visible
       - Last group: LEAD is NULL → first WHEN → uses MAX(source eff_end_date)
         preserving actual terminal end date (could be '3499-12-31' if active,
         or an earlier date if the entity was expired/deactivated)

  WHY NOT just use '3499-12-31' for the last group:
    If the source entity was deactivated (last record has eff_end_date < '3499-12-31'),
    defaulting to '3499-12-31' would make an expired entity appear active — destroying
    business meaning. MAX(source eff_end_date) preserves the actual expiry date.

  This ensures:
    - No redundant durations (consecutive records with unchanged business cols are merged)
    - Business meaning preserved (expiry dates retained, gaps preserved, only collapse when
      target cols unchanged AND records are temporally adjacent)
    - Temporal continuity maintained for continuous source data (non-last groups: eff_end
      derived from next group's start when no gap exists)
    - Gap resilience: if source data violates continuity precondition, gaps are preserved
      (not bridged) — the output reflects the actual temporal coverage of the source

  Example (active entity — last record has eff_end = '3499-12-31'):
    Source has: [account_id, name, address, phone, eff_start_date, eff_end_date]
    Target uses only: [account_id, name, address]
    Source records (ordered by eff_start_date):
      V1: 2025-01-01 → 2025-04-01  name="John", address="Oak Ave", phone="111"
      V2: 2025-04-01 → 2025-06-01  name="John", address="Oak Ave", phone="222" ← only phone
      V3: 2025-06-01 → 2025-08-01  name="John", address="Pine St", phone="222" ← address changed
      V4: 2025-08-01 → 3499-12-31  name="John", address="Pine St", phone="333" ← only phone

    Hash comparison on target cols (name+address), consecutive only:
      V1 hash=H1 → prev=null → NEW GROUP (group 1, start=2025-01-01)
      V2 hash=H1 → prev=H1  → SAME → stays in group 1 (phone change irrelevant to target)
      V3 hash=H2 → prev=H1  → DIFFERENT → NEW GROUP (group 2, start=2025-06-01)
      V4 hash=H2 → prev=H2  → SAME → stays in group 2 (phone change irrelevant)

    After collapse (one row per group):
      Group 1: eff_start = 2025-01-01, cols = "John, Oak Ave"
      Group 2: eff_start = 2025-06-01, cols = "John, Pine St"

    Derive eff_end_date = COALESCE(LEAD(next_group_start), MAX(source_eff_end)):
      Group 1: LEAD = 2025-06-01 (next group exists) → eff_end = 2025-06-01
      Group 2: LEAD = NULL (no next group) → MAX(eff_end in group) = 3499-12-31

    Final result:
      R1: 2025-01-01 → 2025-06-01  name="John", address="Oak Ave"  active='0'
      R2: 2025-06-01 → 3499-12-31  name="John", address="Pine St"  active='1'

  Example (expired entity — last record has eff_end = '2025-08-01'):
    Source records:
      V1: 2025-01-01 → 2025-04-01  name="John", address="Oak Ave", phone="111"
      V2: 2025-04-01 → 2025-06-01  name="John", address="Oak Ave", phone="222"
      V3: 2025-06-01 → 2025-08-01  name="John", address="Pine St", phone="222" ← EXPIRED

    Collapse: Group 1 (V1+V2), Group 2 (V3)

    Derive eff_end_date:
      Group 1: LEAD = 2025-06-01 → eff_end = 2025-06-01
      Group 2: LEAD = NULL → MAX(eff_end in group) = 2025-08-01 (preserves expiry!)

    Final result (entity correctly shows as expired):
      R1: 2025-01-01 → 2025-06-01  name="John", address="Oak Ave"  active='0'
      R2: 2025-06-01 → 2025-08-01  name="John", address="Pine St"  active='0'

  Example (source with temporal GAP — precondition violated):
    Source has: [account_id, name, address, phone, eff_start_date, eff_end_date]
    Target uses only: [account_id, name, address]
    Source records (ordered by eff_start_date):
      V1: 2025-01-01 → 2025-03-01  name="John", address="Oak Ave", phone="111"
      V2: 2025-03-01 → 2025-04-01  name="John", address="Oak Ave", phone="222" ← only phone
      -- GAP: no record from 2025-04-01 to 2025-06-01 (customer inactive/data missing)
      V3: 2025-06-01 → 2025-09-01  name="John", address="Oak Ave", phone="333" ← same target cols
      V4: 2025-09-01 → 3499-12-31  name="John", address="Pine St", phone="333" ← address changed

    Step 5b — gap-aware boundary detection (hash + temporal adjacency):
      V1: hash=H1, prev_eff_end=null     → first row          → boundary (hash)
      V2: hash=H1, prev_eff_end=2025-03-01, eff_start=2025-03-01 → continuous, same hash → no boundary
      V3: hash=H1, prev_eff_end=2025-04-01, eff_start=2025-06-01 → GAP (04-01 != 06-01) → boundary (gap)
      V4: hash=H2, prev_eff_end=2025-09-01, eff_start=2025-09-01 → continuous, diff hash → boundary (hash)

    Groups (with Step 5b splitting at the gap):
      Group 1 (V1+V2): start=2025-01-01, group_max_end=MAX(2025-03-01, 2025-04-01)=2025-04-01
      Group 2 (V3):    start=2025-06-01, group_max_end=2025-09-01
      Group 3 (V4):    start=2025-09-01, group_max_end=3499-12-31

    Step 7 — gap-aware eff_end_date derivation:
      Group 1: next_group_start=2025-06-01, group_max_end=2025-04-01
               next_group_start != group_max_end → GAP DETECTED → eff_end = 2025-04-01
      Group 2: next_group_start=2025-09-01, group_max_end=2025-09-01
               next_group_start == group_max_end → CONTINUOUS → eff_end = 2025-09-01
      Group 3: next_group_start=NULL → last group → eff_end = 3499-12-31

    Final result (gap preserved):
      R1: 2025-01-01 → 2025-04-01  name="John", address="Oak Ave"  active='0'
      -- GAP: 2025-04-01 → 2025-06-01 (no record — matches source)
      R2: 2025-06-01 → 2025-09-01  name="John", address="Oak Ave"  active='0'
      R3: 2025-09-01 → 3499-12-31  name="John", address="Pine St"  active='1'

    Without gap-awareness (old algorithm), V1+V2+V3 would collapse into one group
    (same hash, consecutive-only check passes because V2→V3 are adjacent in order),
    producing: R1: 2025-01-01 → 2025-09-01 — falsely bridging the 2-month gap.

### Building Blocks (composable — NOT mutually exclusive alternatives)

Temporal stitching is achieved by composing these building blocks based on the scenario.
They are NOT independent patterns to choose between — they are layered operations
applied as needed. The agent determines the composition from the analyst's scenario description.

#### Building Block 1: SCD2 Date Derivation

**When needed:** Source table does NOT have eff_start_date/eff_end_date columns.
Converts a non-SCD2 source into SCD2 format so other building blocks can operate on it.

**Algorithm:**
  eff_start_date = <source date column specified by analyst in mapping or domain knowledge>
  eff_end_date = COALESCE(
    LEAD(eff_start_date) OVER (PARTITION BY {pk_cols} ORDER BY eff_start_date),
    '3499-12-31'
  )

**Analyst specifies:** Which source date column to derive eff_start_date from.
This is declared in EITHER:
  - Domain knowledge (e.g., "Eff date source: row_lst_mod_dte")
  - Transformation_logic cell for the eff_start_date target row (e.g., "derived from row_lst_mod_dte",
    "= source.updated_at", or structured TEMPORAL STITCHING scenario format)

#### Building Block 2: Period Collapsing (islands-and-gaps)

**When needed:** Target uses a SUBSET of source columns, OR after a Breakpoint Join
produces redundant time slices where target business columns are unchanged between
adjacent slices.

**Algorithm:**
  1. Order by PK + source eff_start_date
  2. Hash target business columns per record
  3. LAG(hash) — compare with PREVIOUS record's hash (consecutive only)
  4. Mark boundary where hash != prev_hash (or first row)
  5. Group ID = cumulative sum of boundary flags
  5b. (Gap-aware) Also mark boundary where prev record's eff_end_date != current eff_start_date
      Combined flag = hash_changed OR gap_detected → feeds into step 5 cumulative sum
  6. Per group: eff_start_date = MIN(source eff_start_date) within group
  7. Per group: eff_end_date (gap-aware):
       next_group_start = LEAD(eff_start_date) of NEXT group
       group_max_end = MAX(source eff_end_date) within group
       eff_end_date = CASE
         WHEN next_group_start IS NULL THEN group_max_end        -- last group
         WHEN next_group_start != group_max_end THEN group_max_end  -- gap detected
         ELSE next_group_start                                    -- continuous
       END
  (Only CONSECUTIVE identical records collapse — non-adjacent matches stay separate)
  (Gap-aware: if source has temporal gaps between groups, they are preserved not bridged)

**Analyst specifies:** That only a SUBSET of source columns maps to target (agent infers
this from the mapping document — if source has more columns than are mapped to target).

#### Building Block 3: Breakpoint Join (multi-source effective-period-start join)

**When needed:** Multiple SCD2 source tables (each with their own eff_start/eff_end)
feed one target SCD2 table. The target's temporal ranges must be SPLIT at every
source transition point to maintain temporal consistency.

**Prerequisite:** Each source must already have eff_start_date/eff_end_date. If any source
lacks them, apply Building Block 1 (SCD2 Date Derivation) first.

**Algorithm:**
  1. Per source table: apply Period Collapsing to eliminate redundant durations
     (considering only the columns from that source which map to the target)
  2. Collect breakpoints from all source eff_start_dates (post-collapsing)
  3. Create time slices (consecutive breakpoint pairs — continuous, no gaps)
  4. Join each source at each slice point (the version active at that point)
  5. eff_start_date = slice_start
  6. eff_end_date = LEAD(slice_start) over slices; last slice uses MAX(source eff_end)
     to preserve expiry if entity deactivated
     NOTE: Gap-aware Step 7 logic from Period Collapsing is NOT needed here because
     Breakpoint Join constructs slices from collected breakpoints — slices are inherently
     continuous (no gaps between consecutive slices). Gap detection applies only when
     operating directly on source records via Period Collapsing.
  7. Apply Period Collapsing on joined result to collapse any remaining redundant slices

**PERFORMANCE OPTIMIZATION — Hierarchical BDR (for 3+ source tables):**
  When many source tables are involved, instead of collecting ALL breakpoints
  from all sources at once (flat approach), chain operations in pairs:

  Step 1: Group related sources into logical pairs based on join keys
          (e.g., TEHBALT+TEHBRCH share srt_cde; TDLBAHO+TDLCUST share cus_idr)
  Step 2: Apply Breakpoint Join within each pair → produces intermediate stitched result
  Step 3: Apply Breakpoint Join again across intermediate results → compound stitching
  Step 4: Finally collect master breakpoints from all intermediate + remaining tables
  Step 5: Apply Period Collapsing on final result

  Benefits:
    - Reduces intermediate data volume (fewer breakpoints per step)
    - Allows source-pair-specific optimizations (broadcast small tables, fallback logic)
    - Each pair produces a narrower schema (fewer columns carried through)

  Example (10-source Current Account):
    Pair 1: TEHBALT ⊗ TEHBRCH → stitched on srt_cde
    Pair 2: TDLBAHO ⊗ TDLCUST → stitched on cus_idr
    Compound: Pair1_result ⊗ Pair2_result → stitched on (srt_cde, cus_acc_num)
    Master: Compound_result + TEHACCT + TEHPDET + TEHREFR + TEHACLN → final BDR
    Post: Apply Period Collapsing to collapse redundant durations in final result

**Analyst specifies:** Which source tables, the join key between them, and which columns
come from which source.

### Scenario Decision Tree (determines which building blocks to compose)

```
Q1: How many source tables feed this target?
  └─ ONE source table → go to Q2
  └─ MULTIPLE source tables → go to Q4

Q2: Does the source already have eff_start_date / eff_end_date columns?
  └─ YES → go to Q3
  └─ NO → Apply "SCD2 Date Derivation" (analyst specifies source date column), then Q3

Q3: Are ALL source columns mapped to target, or only a SUBSET?
  └─ ALL columns mapped → Just carry forward eff_start/eff_end from source (done)
  └─ SUBSET of columns → Apply "Period Collapsing" on target column hash (done)

Q4 (multi-source): Per source — does it have eff_start_date / eff_end_date?
  └─ For each source lacking SCD2 dates: Apply "SCD2 Date Derivation" first
  └─ Then: Apply "Breakpoint Join" across all sources (analyst specifies join key)
  └─ Breakpoint Join internally applies Period Collapsing per source AND on final result
```

### What the Analyst Specifies in the Mapping Document

Instead of choosing a "pattern", the analyst describes their scenario in the
eff_start_date transformation_logic cell by answering these questions:

```
TEMPORAL STITCHING:
  Sources: <list source table(s)>
  Per source — has SCD2 dates (eff_start_date/eff_end_date)?
    <source_table_1>: YES / NO
    <source_table_2>: YES / NO
  If NO for any source — derive eff_start from: <source_date_column_name>
  Column mapping: ALL source columns mapped to target / SUBSET
  If multi-source — join key: <join_key_columns>
```

The agent reads this scenario description and determines which building blocks to compose.
The eff_end_date row can simply state: "Derived from temporal stitching scenario above."

(active is ALWAYS derived universally after eff_end_date is computed:
 active = '1' if eff_end_date = '3499-12-31', '0' otherwise)

### Mandatory Post-Stitching Validation

After applying building blocks, verify resultant dataset satisfies ALL invariants:
  ✓ No redundant durations (adjacent records for same pk with unchanged business cols are collapsed)
  ✓ Business meaning preserved (point-in-time lookup returns correct values; gaps not bridged)
  ✓ No overlaps (for any PK, eff_end_date <= next record's eff_start_date — strictly)
  ✓ Temporal continuity (eff_end = next eff_start) when source is continuous; if source has
    gaps, they are preserved (eff_end < next eff_start at gap positions is acceptable)
  ✓ At most one active record per PK (eff_end_date = '3499-12-31'); zero if entity expired
  ✓ Gap advisory: if output has eff_end < next eff_start for any PK, emit log:
    "[TEMPORAL STITCHING] Gap detected for PK={pk}: eff_end={date1} < next_eff_start={date2}"

### Applicability Note

This temporal stitching logic is applicable ONLY to SCD2 (NonTransactional) tables.
Transactional tables do NOT use temporal stitching.

### Fallback — When Temporal Stitching Logic Is Missing

If no temporal_stitching section exists in domain knowledge AND no explicit logic
or source column reference (e.g., "derived from <column>") in mapping
transformation_logic for eff_start_date/eff_end_date:

1. Agent MUST ask the user the scenario questions:
   - How many source tables? (single / multiple)
   - Per source: does it have eff_start_date/eff_end_date? If not, which date column?
   - Are all source columns mapped to target or a subset?
   - If multi-source: what is the join key?
2. Based on answers, agent determines which building blocks to compose
3. Agent presents the composed approach to the user for approval
4. Only AFTER user's approval, agent applies the composed logic to code generation

DO NOT invent or default to any building block combination without explicit user approval.
DO NOT proceed with generation until user has reviewed and approved the approach.
