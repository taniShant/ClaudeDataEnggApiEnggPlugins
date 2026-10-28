---
description: "Machine-enforced hard constraints for generated join conditions and literal values — join predicates must use exact column references; literal values must match LOCKED blocks with no substitutions."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-28
---

# Join Predicate & Literal Value Enforcement (HARD CONSTRAINT)

When the `═══ LOCKED JOIN PREDICATES ═══` and/or `═══ LOCKED LITERAL VALUES ═══` blocks are provided in the input context, the following constraints are **machine-enforced** (violations are caught by a deterministic post-generation validator `validate_join_predicates.py` and will trigger automated retry):

### ⛔ HARD CONSTRAINT — Join Predicate Fidelity

- Generated `.join()` conditions MUST use **EXACTLY** the `left_table.left_col OPERATOR right_table.right_col` pairs specified in the LOCKED block.
- The LEFT side is `left_table.left_col`. The RIGHT side is `right_table.right_col`. They are **asymmetric by design**.
- Do NOT swap sides — even if it "looks more natural" or matches naming patterns.
- Do NOT assume same-named columns on both sides (e.g., mapping says `A.customer_survey_id = B.unique_survey_ref` → generate EXACTLY that, NOT `A.customer_survey_id = B.customer_survey_id`).
- Do NOT infer "simpler" or "more logical" join keys based on column naming conventions.
- Do NOT omit any part of a compound join predicate (if LOCKED shows `A.x = B.y AND A.z = B.w`, generate BOTH conditions).
- If the LOCKED predicate specifies an operator other than `=`, use that exact operator.

### ⛔ HARD CONSTRAINT — Literal Value Fidelity

- Generated `F.lit()`, `.filter()`, `F.when()` conditions MUST use **EXACTLY** the value specified in the LOCKED block.
- Do NOT substitute a "more descriptive" value based on column name semantics (e.g., mapping says `'Y'` for `nps_question_indicator` → use `'Y'`, NOT `'V'` for "Verbatim" or any other interpretation).
- Do NOT harmonize values across sibling columns (if one column uses `'Y'` and another uses `'1'`, use each column's specific locked value).
- Do NOT convert between equivalent representations (`'Y'` ≠ `'Yes'` ≠ `'1'` ≠ `True` — use the EXACT locked string).
- For `IN`/`NOT IN` lists: use ALL values from the locked array, in the order specified. Do NOT add or remove values.
- For `hardcode` literals: the `F.lit()` output MUST use the exact locked value.
- The mapping author's intent is **authoritative** — apparent inconsistencies between column names and literal values are intentional data modeling decisions.

### Enforcement Priority

```
Locked predicates/literals > transformation_logic prose > domain knowledge hints > column name semantics
```

If your "reasoning" suggests a different join key or value would be "more correct" — the LOCKED value wins. Always. No exceptions.

### When LOCKED Block Is Absent

If no `═══ LOCKED JOIN PREDICATES ═══` or `═══ LOCKED LITERAL VALUES ═══` block appears in the input:
- This means the mapping was parsed before STEP 2.8 existed, OR no extractable predicates were found
- Existing soft rules still apply (Rule 9b literal fidelity, Rule 11 NL interpretation)
- Generation proceeds normally — no regression

### Compaction Resilience

At the **START** of `transformation()` generation (after reading source column allow-list):
- You **MUST** re-read `session/extracted_predicates.json` to confirm locked join predicates and literal values
- This file is your ground truth for predicate fidelity — even if earlier context has been compacted
- If file exists but cannot be read, **HALT** and report: "Cannot read extracted_predicates.json — halting to prevent predicate/literal hallucination"
- If file does NOT exist (STEP 0.41 determined no predicates to lock): proceed with existing soft rules

### Advisory Comments

When generating code that uses a LOCKED predicate or literal, include a brief comment:
```python
# JOIN: locked from mapping extraction (session/extracted_predicates.json)
joined_df = driver_df.join(
    lookup_df,
    driver_df["customer_survey_id"] == lookup_df["unique_survey_ref"],  # LOCKED predicate
    "left"
)

# LITERAL: locked from mapping extraction
filtered_df = source_df.filter(F.col("nps_question_indicator") == 'Y')  # LOCKED value
```
