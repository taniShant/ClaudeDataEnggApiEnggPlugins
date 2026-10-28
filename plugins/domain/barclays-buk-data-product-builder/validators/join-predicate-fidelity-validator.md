# Validator: join-predicate-fidelity-validator

**Purpose**: Verify that generated PySpark join conditions and literal values match the locked predicates from `session/extracted_predicates.json`. Catches LLM deviations where training patterns override mapping-specified join keys (e.g., assuming symmetric join keys) or literal values (e.g., substituting semantically "logical" values).

**Severity**: BLOCK on join predicate mismatch. BLOCK on literal value mismatch. WARNING on phantom joins.

**Platform**: Glue + Databricks

---

## Prerequisites

- Generated transform file(s) exist (`generated/{platform}/transforms/` or `generated/databricks/src/Notebooks/`)
- `session/extracted_predicates.json` exists (written by STEP 0.41 of `/gen-transform`)
- Python available (`session_state.python_path` is set)

---

## Invocation

- **Primary**: Called inline by `/gen-transform` STEP FINAL.3 (runs after chain checkpoint write)
- **Secondary**: Called by `/validate` Batch 5 Part E (runs as part of full validation suite)
- **Gate**: `/push` refuses if `session_state.join_predicate_fidelity_result != "passed"` AND `!= "skipped_no_predicates"`

---

## Checks

### Check 1 — Join Condition Structure (BLOCKING)

For each locked join predicate in `extracted_predicates.json → join_predicates[]`:
1. Scan generated `.join(` calls in the transform file
2. Extract the ON condition argument (the equality/comparison expression)
3. Parse column references from both sides of the condition:
   - `df["col"]` format → extract `col`
   - `F.col("alias.col")` format → extract `alias`, `col`
   - `alias_df["col"]` format → extract alias (from df variable name), `col`
   - `alias_df.col_name` format → extract alias, col
4. Verify: LEFT side references `left_table` and `left_col` as specified in the locked predicate
5. Verify: RIGHT side references `right_table` and `right_col` as specified in the locked predicate

**BLOCK** if:
- Left-side column name doesn't match `left_col` (e.g., locked says `customer_survey_id` but code uses `survey_id`)
- Right-side column name doesn't match `right_col` (e.g., locked says `unique_survey_ref` but code uses `customer_survey_id`)
- Columns are swapped between sides (left uses right's column or vice versa)
- Join predicate is entirely missing from generated code

**Error format:**
```
❌ Join predicate mismatch (line 47)
   LOCKED: customer_response.customer_survey_id = wm_append_data.unique_survey_ref
   GENERATED: customer_response["customer_survey_id"] == wm_append_data["customer_survey_id"]
   Issue: RIGHT side uses 'customer_survey_id' but LOCKED specifies 'unique_survey_ref'
   Source: mapping extraction → "customer_response.customer_survey_id = wm_append_data.unique_survey_ref"
```

### Check 2 — Literal Value Fidelity (BLOCKING)

For each locked literal in `extracted_predicates.json → literals[]`:
1. Determine the target column this literal applies to (`target_column` field)
2. In the generated code, find the section that produces this target column (trace through `.withColumn()`, `.alias()`, `F.when()` chains)
3. Extract literal values used in:
   - `.filter(F.col("col") == "value")` or `.filter(F.col("col") == 'value')`
   - `F.when(F.col("col") == "value", ...)` comparisons
   - `F.lit("value")` assignments
   - `.isin(["val1", "val2"])` or `~F.col("col").isin([...])`
4. Compare extracted values against the locked literal's `value` field

**BLOCK** if:
- A filter/comparison uses a different value than what's locked (e.g., locked `'Y'` but code uses `'V'`)
- An IN/NOT IN list has different values than locked (added, removed, or substituted values)
- A hardcoded literal uses a different value than locked

**Error format:**
```
❌ Literal value mismatch for target column 'nps_response_value' (line 52)
   LOCKED: nps_question_indicator = 'Y' (context: filter_predicate)
   GENERATED: F.col("nps_question_indicator") == 'V'
   Issue: Value 'V' does not match locked value 'Y'
   Source: mapping extraction → "nps_question_indicator='Y'"
```

### Check 3 — Phantom Join Detection (WARNING, non-blocking)

Scan for ALL `.join(` calls in the generated code:
1. Extract the join condition from each
2. For each join condition, check if it matches:
   - A locked predicate from `extracted_predicates.json → join_predicates[]` (expected)
   - A join in `structured_transformation.joins[]` from `mapping_parsed.json` (expected)
   - Neither (potentially hallucinated)
3. **WARN** if a join exists in generated code with no corresponding locked predicate AND no structured_transformation entry

**Warning format:**
```
⚠️ Untraced join detected (line 63) — not in locked predicates or structured_transformation
   Generated: source_a["col_x"] == source_b["col_y"]
   This join may be correct (NL interpretation) or may be hallucinated.
   Manual review recommended.
```

**Note:** Phantom join warnings are advisory only. In NL interpretation mode, not all joins will have locked predicates (low-confidence extractions are excluded). This check surfaces potential hallucinations for human attention but does NOT block.

### Check 4 — Symmetric Key Ambiguity Detection (BLOCKING)

Scan `.join()` calls using expression syntax (== operator between column references):

1. Extract left column name and right column name from each equality
2. IF left_col_name == right_col_name (case-insensitive) → **BLOCK**:
   ```
   ❌ Symmetric key ambiguity (line NN)
      Generated: customer_response["question_id"] == question_bc["question_id"]
      Issue: Both sides use 'question_id' — expression syntax creates duplicate columns.
      Fix: .join(question_bc, ["question_id"], "left")
      Severity: BLOCKING — downstream references throw AnalysisException
   ```
3. IF left_col_name != right_col_name → PASS (asymmetric, expression syntax correct)

**Self-heal**: Replace `.join(right, left["col"] == right["col"], type)` → `.join(right, ["col"], type)`

---

## Known Exceptions (NOT flagged as violations)

| Category | Examples | Reason |
|----------|----------|--------|
| **Config-suppressed filters** | Filters that appear in `session/generated_configs/{table}_filters.json` | Config handles these — they correctly do NOT appear in transform code |
| **Intermediate dedup joins** | `self_join` for ROW_NUMBER dedup patterns | Standard dedup pattern, not a business join |
| **Broadcast hint** | `F.broadcast(df)` around a join | Performance optimization, doesn't change join semantics |
| **Order of equality sides** | `a["col"] == b["col"]` vs `b["col"] == a["col"]` | Python equality is symmetric; validator checks column presence on each table, not expression ordering |
| **List-syntax symmetric joins** | `.join(df, ["col"], "left")` for predicates where left_col == right_col | Correct — satisfies predicate fidelity via semantics |

---

## Extraction Patterns (Regex for generated code parsing)

```python
# .join() call detection
r'''\.join\(\s*(\w+).*?,\s*(.+?),\s*["'](\w+)["']\s*\)'''

# Column reference patterns in join conditions
r'''(\w+)\[["'](\w+)["']\]'''                  # df["col"]
r'''F\.col\(["'](\w+)\.(\w+)["']\)'''          # F.col("alias.col")
r'''F\.col\(["'](\w+)["']\)'''                  # F.col("col") — alias from context
r'''(\w+)_(?:df|filtered)\[["'](\w+)["']\]'''   # alias_df["col"]

# Literal value patterns
r'''==\s*["']([^"']+)["']'''                    # == 'value' or == "value"
r'''F\.lit\(["']([^"']+)["']\)'''               # F.lit("value")
r'''F\.lit\((\d+(?:\.\d+)?)\)'''                # F.lit(number)
r'''\.isin\(\[([^\]]+)\]\)'''                    # .isin([...])
```

---

## Self-Heal Retry Logic

When violations are found during `/gen-transform` STEP FINAL.3:

1. **First attempt**: Re-invoke transform-generator-agent with:
   - Violation list (specific lines, expected vs actual values)
   - Explicit instruction: "Replace the incorrect join condition/literal with the LOCKED value. Do NOT interpret or infer — use the exact predicate/value from extracted_predicates.json."
   - The relevant locked predicate entries (JSON snippet from `session/extracted_predicates.json`)
2. **Second attempt**: Same as above if violations persist.
3. **After 2 retries**: Mark file as `DRAFT_UNVALIDATED`. Set `session_state.join_predicate_fidelity_result = "failed"`.

---

## Integration Points

| Integration | When | Behavior |
|---|---|---|
| `/gen-transform` STEP FINAL.3 | After chain checkpoint write | Run validator → self-heal retry if violations |
| `/validate` Batch 5 Part E | During full validation suite | Run validator → report findings (no retry here) |
| `/push` gate | Before push/commit | Refuse if `join_predicate_fidelity_result` is `"failed"` |

---

## Session State Fields

| Field | Type | Set By | Values |
|---|---|---|---|
| `join_predicate_fidelity_result` | string | STEP FINAL.3 | `"passed"`, `"failed"`, `"skipped_no_predicates"`, `"skipped_no_python"` |
| `join_predicate_fidelity_violations` | array\|null | STEP FINAL.3 | Array of violation objects, or null if passed |

---

## Pass Condition

All generated `.join()` conditions match their corresponding locked predicates exactly (left_col and right_col on correct sides). All generated literal values match their locked counterparts exactly. Symmetric-key joins use list syntax (no ambiguity). Zero BLOCKING violations across all generated files for the session.
