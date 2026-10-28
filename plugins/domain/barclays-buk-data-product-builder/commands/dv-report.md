---
description: Generate a validation report from plans and optionally user-provided execution results
disable-model-invocation: false
argument-hint: [--results <path>] [--format md|json]
---

# /dv-report — Generate Data Validation Report

Generate a structured validation report from generated plans and optionally from user-provided execution results. This command does **NOT** execute SQL — it only generates reports.

## Usage

```
/dv-report [--results <path>] [--format md|json]
```

## Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--results` | No | none | Path to Excel (.xlsx) with execution results |
| `--format` | No | both | Output format: `md`, `json`, or both |

## Prerequisites

- `/dv-generate` must have completed (`dv_session_state.json` exists with `dv_generate.status == "completed"`)

## Workflow

### Step 0 — RESOLVE PLUGIN ROOT + LOAD SESSION STATE

1. Check `${CLAUDE_PLUGIN_ROOT}` exists
2. Read `session/dv_session_state.json`
3. Verify `phases.dv_generate.status == "completed"`
4. If not: `❌ /dv-generate has not been completed. Run /dv-generate first.`
5. Read `.dv_manifest.json` for generated file inventory

If plugin root is missing, STOP with: "❌ Plugin root not resolved. Ensure barclays-buk-data-product-builder plugin is loaded."

---

### Step 1 — READ VALIDATION PLANS

For each table in manifest:
1. Read `session/dv_validation_plan_{table}.json`
2. Extract check inventory, categories, severities
3. Collect NOT_EVALUATED checks with reasons
4. Collect `assumptions_and_gaps[]`

### Step 2 — PARSE RESULTS (if --results provided)

If `--results <path>` is provided:

1. **Validate Excel structure against `dv_validation_results.schema.json`:**
   a. Sheet count = 1 (named "Validation Results") → else HALT
   b. Column count = 13 (A through M) → else HALT
   c. Header match (case-insensitive): `check_id`, `check_name`, `status`, `source_count`, `target_count`, `mismatch_count`, `violation_count`, `overlap_count`, `gap_count`, `broken_boundary_count`, `invalid_current_record_count`, `affected_key_count`, `error_message` → else HALT
   d. Spot check: columns D–L must be integers or blank/zero; non-numeric values >20 chars → HALT

   On HALT:
   ```
   ❌ Results file does not match expected schema. Expected exactly 13 columns (A–M) in a single 'Validation Results' sheet.
   Violation: {specific issue}
   ```

2. Parse validated Excel into `session/dv_execution_results_{table}.json`

3. Delegate to `dv-result-interpreter-agent` with:
   - Input: execution results JSON + validation plan JSON
   - Output: report files

### Step 3 — GENERATE REPORT

Generate report files:

**`session/dv_validation_report.md`** structure:
1. `## Summary` — Total tables, total checks, per-category counts. Overall verdict: ALL PASS / N FAILURES / N NOT_EVALUATED
2. `## Per-Table Results` — Per table: metadata, check results table, NOT_EVALUATED, assumptions
3. `## SCD2 Temporal Summary` (SCD2 tables only) — invariants validated, boundary convention, gap policy
4. `## Execution Instructions` — Per-engine placeholder guide, how to run SQL, how to format results
5. `## Generated File Index` — Per-table SQL file paths from manifest

**`session/dv_validation_report.json`** structure:
```json
{
    "report_version": "1.0",
    "session_id": "...",
    "engine": "...",
    "summary": {
        "total_tables": 1,
        "total_checks": 28,
        "passed": 0,
        "failed": 0,
        "not_evaluated": 2
    },
    "tables": [{
        "target_database": "...",
        "target_table": "...",
        "table_type": "...",
        "checks": [{
            "check_id": "...",
            "check_name": "...",
            "category": "...",
            "verdict": "PASS|FAIL|NOT_EVALUATED",
            "counts": {},
            "not_evaluated_reason": null
        }],
        "assumptions_and_gaps": []
    }]
}
```

If `--results` was NOT provided, generate the report as a check inventory + execution instructions (no verdicts — verdicts require execution results).

### Step 4 — UPDATE SESSION STATE

1. Update `phases.dv_report.status = "completed"`
2. Set `report_path` in session state
3. Display report summary to user:
```
✅ DV report generated
   Tables:         1 (mortgage_account)
   Total checks:   28
   Verdicts:       26 PASS, 0 FAIL, 2 NOT_EVALUATED
   
   Reports:
     session/dv_validation_report.md
     session/dv_validation_report.json
```

## Output

- `session/dv_validation_report.md`
- `session/dv_validation_report.json`

## Important Rules

- This command does NOT execute SQL
- Results are strictly counts-only — no row-level data, no PII
- Without `--results`, report is a check inventory (no verdicts)
- With `--results`, Excel must pass 4 structural validation checks before parsing
