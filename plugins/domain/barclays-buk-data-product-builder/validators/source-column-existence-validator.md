# Validator: source-column-existence-validator

**Purpose**: Verify that generated PySpark transform scripts only reference source columns that exist in the mapping document (`mapping_parsed.json` `source_references[]`). Catches hallucinated/invented column names that would cause runtime `AnalysisException` failures in Spark.

**Severity**: BLOCK on invented source or target column references.

**Platform**: Glue + Databricks

---

## Prerequisites

- Generated transform file(s) exist (`generated/{platform}/transforms/` or `generated/databricks/src/Notebooks/`)
- `session/mapping_parsed.json` exists and is populated (parse-mapping completed)
- `session/source_column_allowlist.json` exists (written by `/gen-transform` STEP 0.4)

---

## Invocation

- **Primary**: Called inline by `/gen-transform` STEP FINAL.1 (runs immediately after syntax check)
- **Secondary**: Called by `/validate` Batch 5 Part C (runs as part of full validation suite)
- **Gate**: `/push` refuses if `session_state.column_validation_result != "passed"`

**Script**: `${CLAUDE_PLUGIN_ROOT}/scripts/validate_column_refs.py`

```bash
python scripts/validate_column_refs.py <transform_file.py> session/mapping_parsed.json [--target-table <name>]
```

Exit codes:
- `0` = all column references valid
- `1` = violations found (JSON printed to stdout)
- `2` = usage/parse error

---

## Checks

### Check 1 — Source Column Existence (BLOCKING)

For each source column reference in generated `.py` files:
1. Extract column name via regex patterns:
   - `F.col("column_name")` / `F.col('column_name')`
   - `self.alias["column_name"]` (bracket access)
   - Column references in `.select()` argument lists
2. Identify the source table alias via code context (`self.alias_name` on same/nearby line)
3. Verify column exists in `mapping_parsed.json` → `columns[].source_references[]` for that alias

**BLOCK** if any source column is referenced that does NOT appear in the mapping for its alias.

**Error format:**
```
❌ Column 'nps_business_date' referenced for alias 'customer_response' (line 47)
   but not found in mapping source_references.
   Available columns for customer_response: [customer_survey_id, question_id, customer_response_date, ...]
```

### Check 2 — Target Column Existence (BLOCKING)

For the final output DataFrame (columns in `.alias()` calls or final `.select()`):
1. Verify each output column name exists in `mapping_parsed.json` → `columns[].target_column_name`
2. **Exceptions** (always allowed, never flagged):
   - Audit columns: `eff_start_date`, `eff_end_date`, `active`, `dw_lod_tmp`, `dw_upd_lod_tmp`, `dw_bus_dt`

**BLOCK** if the output includes columns not present in the mapping's target column list + audit exceptions.

### Check 3 — Completeness (WARNING, non-blocking)

Verify ALL target columns from mapping appear in the generated output `.select()`.

**WARN** (do not block) if any mapping target column is missing from generated code.
This indicates a potential generation gap but is not a blocking issue (column may be added in a later transform step or by TargetWriter).

### Check 4 — Mapping Row Coverage (BLOCKING)

Verify ALL target columns from `mapping_parsed.json → columns[].target_column_name` are produced by the generated transform's final output.

Unlike Check 3 (which warns about completeness), this check **blocks** if any mapping row is silently dropped during generation.

1. Collect all `target_column_name` values from `mapping_parsed.json → columns[]`
2. Extract all output column names from the generated transform:
   - Column names in the final `.select()` statement
   - Column names produced by `.withColumn()` or `.alias()` that survive to the output
3. For each mapping target column: verify it appears in the generated output
4. **BLOCK** if any mapping column is absent

**Exceptions (NOT flagged):**
- Audit columns managed by TargetWriter for Day1 transforms: `eff_start_date`, `eff_end_date`, `active`, `dw_lod_tmp`, `dw_upd_lod_tmp`, `dw_bus_dt`
- Day1 transforms are NOT expected to produce audit columns — TargetWriter injects them

**Error format:**
```
❌ MAPPING ROW NOT PRODUCED: target column 'customer_survey_id' exists in mapping_parsed.json
   but is NOT present in the generated transform output (no .alias() or .withColumn() produces it).
   This column was silently dropped during generation.
```

**Script flag:** `python scripts/validate_column_refs.py <transform.py> <mapping.json> --check-coverage [--target-table <name>]`

---

## Known Exceptions (NOT flagged as violations)

The following column references are **legitimate** and must NOT be reported as violations:

| Category | Examples | Reason |
|----------|----------|--------|
| **Intermediate processing columns** | `_rn`, `_rank`, `_dedup_flag`, `_join_key`, `response_count` | Created via `.withColumn()`, `.alias()`, `.agg()`, or window functions during multi-step transform logic |
| **Audit columns** | `eff_start_date`, `eff_end_date`, `active`, `dw_lod_tmp`, `dw_upd_lod_tmp`, `dw_bus_dt` | System-managed temporal/audit columns defined by templates |
| **Spark built-in functions** | `current_timestamp`, `current_date`, `monotonically_increasing_id` | Spark expressions, not column references |
| **F.lit() values** | Any column created via `F.lit(value).alias("name")` | Literal value assignment, not source read |
| **Target column names in .alias()** | `.alias("survey_response_id")` | Target-side naming, not source-side read |

**Key distinction**: The validator checks that **source column references** (columns read FROM source tables) match the mapping. Columns **created** by the transform logic itself are detected by looking for prior `.withColumn()`, `.alias()`, or `.agg()` calls in the same file — these are NOT flagged.

---

## Self-Heal Retry Logic

When violations are found during `/gen-transform` STEP FINAL.1:

1. **First attempt**: Re-invoke transform-generator-agent with ONLY the violation list + `session/source_column_allowlist.json`. Instruction: fix only flagged columns.
2. **Second attempt**: Same as above if violations persist.
3. **After 2 retries**: Mark file as `DRAFT_UNVALIDATED`. Set `session_state.column_validation_result = "failed"`.

The retry agent gets a **fresh context** (no compaction risk) containing:
- Violation list (~100 tokens)
- Allow-list file path (`session/source_column_allowlist.json`)
- Generated file to fix (read from disk)
- Instruction to fix only flagged columns

---

## Integration Points

| Integration | When | Behavior |
|---|---|---|
| `/gen-transform` STEP FINAL.1 | After syntax check passes | Run validator → self-heal retry if violations |
| `/validate` Batch 5 Part C | During full validation suite | Run validator → report findings (no retry here) |
| `/push` gate | Before push/commit | Refuse if `column_validation_result != "passed"` |

---

## Session State Fields

| Field | Type | Set By | Values |
|---|---|---|---|
| `column_validation_result` | string | STEP FINAL.1 | `"passed"`, `"failed"`, `"skipped_no_python"` |
| `column_validation_failures` | array\|null | STEP FINAL.1 | Array of violation objects, or null if passed |

---

## Pass Condition

All source and target column references in generated transform files trace back to the mapping document. Zero violations across all generated files for the session.
