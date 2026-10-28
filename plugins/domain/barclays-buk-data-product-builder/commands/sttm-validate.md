---
description: Run full validation checklist against an existing STTM output
disable-model-invocation: false
---

# /sttm-validate — Validate Generated STTM

Run the full validation checklist against an existing STTM output.

## Description

Executes all 102 validation checks (defined in validation_rules.yaml) against the STTM JSON and reports results.

## Arguments

- `--input`: Path to STTM JSON file. Default: resolved from manifest (see Step 0B)
- `--strict`: Treat warnings as blockers (default: false)

## Workflow

### Step 0 — RESOLVE PLUGIN ROOT

`${CLAUDE_PLUGIN_ROOT}` is automatically set by the plugin loader. Verify:
- `${CLAUDE_PLUGIN_ROOT}/configs/sttm/template_spec.yaml` exists

If missing, STOP with: "❌ Plugin root not resolved. Ensure barclays-buk-data-product-builder plugin is loaded."

---

### Step 0B — RESOLVE INPUT PATH

If `--input` is not explicitly provided, resolve the default from the output manifest:

1. Check if `output/.sttm_manifest.json` exists
   - **YES**: read manifest, use `files.sttm_json` as input path
   - **NO**: fall back to legacy default `output/sttm.json`
2. Log: `"Validating: {resolved_input_path}"`

For validation report output path:
- If manifest exists: use `files.validation_report` from manifest
- If `--input` was explicitly provided: derive by replacing `_sttm.json` with `_validation_report.json` in the input path
- Otherwise: fall back to `output/validation_report.json`

Store resolved paths as variables:
- `STTM_INPUT` = resolved input path
- `VAL_REPORT` = resolved validation report output path

---

1. Read the STTM JSON from `{STTM_INPUT}`
2. Determine the scenario from `_meta.scenario`
3. Load `${CLAUDE_PLUGIN_ROOT}/configs/sttm/validation_rules.yaml` and `${CLAUDE_PLUGIN_ROOT}/configs/sttm/template_spec.yaml`
4. Spawn `sttm-validation-agent` with the STTM data and scenario
5. Report results in structured format:
   - Total checks run
   - Pass / Warning / Blocker counts
   - Detailed findings with row/column references
   - Fix suggestions for each finding
6. Write results to `{VAL_REPORT}`

### Post-Validation — UPDATE SESSION STATE

If `output/sttm_session_state.json` exists, update the `validation_result` block:
```json
{
  "total_checks": <count>,
  "passed": <count>,
  "warnings": <count>,
  "blockers": <count>,
  "result": "passed|warning|blocker",
  "validated_at": "<ISO 8601 timestamp>"
}
```

## Output

Displays a summary table:
```
Validation Results:
  ✅ Pass: 98/102
  ⚠️  Warning: 3
  ❌ Blocker: 1

BLOCKERS (must fix before export):
  M15 [Row 3, Business Logic]: Multi-table logic uses natural language instead of structured format
       Fix: Convert to structured compact newline-separated format with aliases: "Driver Table: X (x)\nJoin 1: LEFT JOIN Y (y) ON x.col = y.col\nValue: ..."

WARNINGS (review recommended):
  M14 [Row 5, Default Value]: COALESCE detected but Default Value is empty
       Fix: Add "'UNKNOWN'" to Default Value field
```
