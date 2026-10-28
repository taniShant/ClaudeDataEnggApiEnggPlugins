# Validator: literal-value-fidelity-validator

**Purpose**: Verify that literal values (`F.lit(...)`) in generated PySpark transform scripts exactly match the values specified in the mapping document's `transformation_logic` field. Catches LLM deviations where training patterns override in-context mapping values (e.g., using a column's semantic name as a literal instead of the mapping-specified value).

**Severity**: BLOCK on literal value mismatch against mapping source of truth.

**Platform**: Glue + Databricks

---

## Prerequisites

- Generated transform file(s) exist (`generated/{platform}/transforms/` or `generated/databricks/src/Notebooks/`)
- `session/mapping_parsed.json` exists and is populated (parse-mapping completed)

---

## Invocation

- **Primary**: Called inline by `/gen-transform` STEP FINAL.2 (runs after source-column-existence-validator)
- **Secondary**: Called by `/validate` Batch 5 Part D (runs as part of full validation suite)
- **Gate**: `/push` refuses if `session_state.literal_fidelity_result != "passed"`

---

## Checks

### Check 1 — F.lit() Value Extraction (BLOCKING)

For each `F.lit(value)` call in generated transform `.py` files:
1. Extract the literal value and its assignment context:
   - `F.lit("value").alias("target_col")` → `{value: "value", target_col: "target_col"}`
   - `F.lit('value')` inside `.when()` / `.otherwise()` → trace to target column via enclosing `.withColumn()` or `.alias()`
   - `F.lit(numeric_value)` → same extraction pattern
2. Identify the target column this literal contributes to (via `.alias()`, `.withColumn()`, or enclosing expression context)
3. Look up `mapping_parsed.json` → `columns[]` → find entry where `target_column_name` matches
4. Extract the `transformation_logic` field for that column
5. Compare: does the literal value in the generated code match what `transformation_logic` specifies?

**BLOCK** if:
- A `F.lit(value)` uses a value that is NOT present in the mapping's `transformation_logic` for that target column
- A `F.lit(value)` appears to use the target column name (or part of it) as the value, when the mapping specifies a different value

**Error format:**
```
❌ Literal value mismatch for target column 'ease_question_type_code' (line 83)
   Generated: F.lit("ease")
   Mapping transformation_logic specifies: "nps"
   Source: mapping_parsed.json → columns[12].transformation_logic
```

### Check 2 — CASE WHEN / F.when() Predicate Values (BLOCKING)

For each `F.when(condition, value)` chain:
1. Extract predicate comparison values: `F.col("x") == "value"` → extract `"value"`
2. Extract result values: `F.when(..., F.lit("result"))` → extract `"result"`
3. Cross-reference ALL extracted values against the corresponding target column's `transformation_logic` in the mapping
4. Verify each literal in the CASE chain appears in the mapping's logic description

**BLOCK** if generated CASE values deviate from mapping-specified values.

### Check 3 — Filter Predicate Values (WARNING, non-blocking)

For each `.filter()` or `.where()` clause containing literal comparisons:
1. Extract comparison values
2. Cross-reference against mapping `transformation_logic` for the relevant column(s)
3. **WARN** if a filter value does not trace to the mapping (may be a config-specified filter that's legitimate)

**Note:** Filter values may legitimately come from config.json rather than mapping transformation_logic. This check is advisory.

---

## Known Exceptions (NOT flagged as violations)

| Category | Examples | Reason |
|----------|----------|--------|
| **Audit column literals** | `F.lit("3499-12-31")`, `F.lit("1")`, `F.lit("0")`, `F.current_timestamp()` | Template-defined audit column derivation values |
| **Default values from mapping** | `F.coalesce(expr, F.lit(default))` where default matches `mapping_parsed.json` → `columns[].default_value` | Legitimate default value application |
| **NULL literals** | `F.lit(None)` | Standard null handling |
| **Type cast targets** | `.cast("string")`, `.cast("decimal(19,6)")` | Data type conversions, not business literals |
| **Join broadcast hints** | `F.broadcast(df)` | Performance hint, not a business value |

---

## Extraction Patterns (Regex)

```python
# F.lit("string_value") or F.lit('string_value')
r'''F\.lit\(["']([^"']+)["']\)'''

# F.lit(numeric_value)
r'''F\.lit\((\d+(?:\.\d+)?)\)'''

# F.when(F.col("x") == "value", ...) or F.when(F.col("x") == 'value', ...)
r'''F\.when\(.*?==\s*["']([^"']+)["']'''

# .otherwise(F.lit("value"))
r'''\.otherwise\(F\.lit\(["']([^"']+)["']\)\)'''
```

---

## Self-Heal Retry Logic

When violations are found during `/gen-transform` STEP FINAL.2:

1. **First attempt**: Re-invoke transform-generator-agent with:
   - Violation list (specific lines and expected vs actual values)
   - Explicit instruction: "Replace the incorrect literal with the mapping-specified value. Do NOT interpret or infer — use the exact value from transformation_logic."
   - The relevant mapping column entry (JSON snippet)
2. **Second attempt**: Same as above if violations persist.
3. **After 2 retries**: Mark file as `DRAFT_UNVALIDATED`. Set `session_state.literal_fidelity_result = "failed"`.

---

## Integration Points

| Integration | When | Behavior |
|---|---|---|
| `/gen-transform` STEP FINAL.2 | After source-column-existence-validator passes | Run validator → self-heal retry if violations |
| `/validate` Batch 5 Part D | During full validation suite | Run validator → report findings (no retry here) |
| `/push` gate | Before push/commit | Refuse if `literal_fidelity_result != "passed"` |

---

## Session State Fields

| Field | Type | Set By | Values |
|---|---|---|---|
| `literal_fidelity_result` | string | STEP FINAL.2 | `"passed"`, `"failed"`, `"skipped_no_python"` |
| `literal_fidelity_violations` | array\|null | STEP FINAL.2 | Array of violation objects, or null if passed |

---

## Pass Condition

All `F.lit()` values, `F.when()` predicate/result values, and hardcoded string constants in generated transform files trace back to the mapping document's `transformation_logic` or `default_value` fields. Zero violations across all generated files for the session.
