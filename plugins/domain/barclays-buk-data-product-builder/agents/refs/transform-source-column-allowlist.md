---
description: "Hard constraint enforcing column boundaries — only columns in the source allow-list may be referenced; use {{placeholder_column}} for missing columns; final output must produce only target + audit columns."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-28
---

# Source Column Allow-List Enforcement (HARD CONSTRAINT)

When the `═══ STRICT SOURCE COLUMN CONSTRAINTS ═══` block is provided in the input context, the following constraints are **machine-enforced** (violations are caught by a deterministic post-generation validator and will trigger automated retry):

### ⛔ HARD CONSTRAINT — Source Column Boundary

- You may **ONLY** reference source columns that appear in the allow-list for their respective source table alias.
- If `transformation_logic` free-text references a column NOT in the list:
  → Do NOT assume it exists under a different name
  → Do NOT invent a plausible-sounding column name
  → Emit `{{placeholder_column}}` with a TODO comment explaining the gap
  → Log a WARNING in the generated file header: `"Unresolved column: {col_name} from {alias}"`
- The allow-list is **EXHAUSTIVE** — it is derived from the mapping document which is the single source of truth for column lineage.

### ⛔ HARD CONSTRAINT — Target Column Boundary

- The final `.select()` or DataFrame returned from `transformation()` must produce **ONLY**:
  → Columns listed in `TARGET TABLE ALLOWS ONLY` + `AUDIT COLUMNS`
- Do NOT add intermediate columns to the **FINAL** output DataFrame
- Do NOT rename target columns from what the mapping specifies

### ✅ PERMITTED — Intermediate Processing Columns

- You **MAY** create intermediate columns during multi-step transformation logic
- Examples: `_rn` from ROW_NUMBER, `_join_key` from concat, `_dedup_flag`, aggregation outputs like `response_count`
- These are legitimate processing artifacts — **NOT** violations of the source allow-list
- They must be dropped/excluded before the final output DataFrame is returned
- The allow-list applies to **SOURCE TABLE READS** only — not to columns you create yourself via `.withColumn()`, `.alias()`, `.agg()`, or window functions

### Enforcement Priority

```
Allow-list > transformation_logic prose > domain knowledge hints
```

If `transformation_logic` mentions a column not in the allow-list, **the allow-list wins**. Emit a placeholder, not an invented column.

### Compaction Resilience

At the **START** of `transformation()` generation (before writing any `F.col()` or join logic):
- You **MUST** re-read `session/source_column_allowlist.json` to confirm the valid columns
- This file is your ground truth — even if earlier context has been compacted
- If you cannot access this file, **HALT** and report: "Cannot read source_column_allowlist.json — halting to prevent column hallucination"

### Column Manifest Header

After generating the transform, include a source column manifest in the file header:

```python
# =============================================================================
# SOURCE COLUMN MANIFEST (auto-generated — do not edit)
# {alias_1}: col_a, col_b, col_c, ...
# {alias_2}: col_x, col_y, col_z, ...
# =============================================================================
```

This documents which columns are valid for quick reference and serves as a cross-check for the post-generation validator.
