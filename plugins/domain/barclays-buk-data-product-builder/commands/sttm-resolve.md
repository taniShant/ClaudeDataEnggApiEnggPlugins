---
description: Interactively resolve ambiguous or below-confidence STTM fields
disable-model-invocation: false
---

# /sttm-resolve — Resolve STTM Ambiguities

Interactively resolve ambiguous or below-confidence fields in a generated STTM.

## Description

After generation, some fields may have confidence below the threshold (0.7) or have conflicts between sources. This command presents each ambiguity to the user with evidence and options for resolution.

## Arguments

- `--input`: Path to STTM JSON. Default: resolved from manifest (see Step 0B)
- `--provenance`: Path to provenance JSON. Default: resolved from manifest (see Step 0B)
- `--threshold`: Confidence threshold (0.0-1.0). Default: 0.7

## Workflow

### Step 0 — RESOLVE PLUGIN ROOT

`${CLAUDE_PLUGIN_ROOT}` is automatically set by the plugin loader. Verify:
- `${CLAUDE_PLUGIN_ROOT}/configs/sttm/template_spec.yaml` exists

If missing, STOP with: "❌ Plugin root not resolved. Ensure barclays-buk-data-product-builder plugin is loaded."

---

### Step 0B — RESOLVE INPUT PATHS

If `--input` or `--provenance` are not explicitly provided, resolve defaults from the output manifest:

1. Check if `output/.sttm_manifest.json` exists
   - **YES**: read manifest, use `files.sttm_json` for `--input` and `files.provenance_json` for `--provenance`
   - **NO**: fall back to legacy defaults (`output/sttm.json`, `output/provenance.json`)
2. Log: `"Resolving from: {resolved_sttm_path}"`

Store resolved paths as variables:
- `STTM_INPUT` = resolved `--input` path
- `PROV_INPUT` = resolved `--provenance` path

Write-back in Step 3 MUST use the same resolved paths (not hardcoded defaults).

---

### 1. Identify Unresolved Fields

1. Read `{STTM_INPUT}` and `{PROV_INPUT}`
2. Scan provenance for fields with confidence < threshold
3. Scan for fields marked "unresolved" in _meta.questions
4. Scan `source_volumetrics[]` for entries with `estimated_rows: null` — add as WARNING-level questions (Q21–Q23 from guided-mode-questions.md)
5. Sort by severity (blockers first, then warnings)

### 2. Present Each Ambiguity

For each unresolved field:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ambiguity #1 of 3 [BLOCKER]
Row: outstanding_balance
Field: Source Column Name

Question: Which source column maps to target "outstanding_balance"?

Evidence available:
  • SQL suggests: balance_amt (confidence: 0.6 — ambiguous alias)
  • Design doc suggests: outstanding_bal_amt (confidence: 0.5 — naming convention)
  • Column name similarity: outstanding_bal (confidence: 0.3 — different table)

Options:
  1. balance_amt (from SQL — most likely)
  2. outstanding_bal_amt (from design document)
  3. Enter custom value
  4. Mark as "requires investigation" and continue

Risk if guessed wrong: Incorrect lineage → wrong data in target
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 3. Apply Resolution

For each user answer:
1. Update the field value in the STTM JSON
2. Update provenance with method = "user_supplied", confidence = 0.95
3. Re-validate affected rows
4. Write updated files

**For source volumetrics answers (Q21–Q23):**
1. Update `source_volumetrics[].estimated_rows` (and/or estimated_size_gb, daily_increment_rows, daily_increment_size_gb)
2. Recalculate `broadcast_hint`: set to `true` if estimated_rows < 10,000, `false` otherwise (boolean, matching schema)
3. No provenance update needed (volumetrics are not per-column provenance tracked)

### 4. Update Session State

If `output/sttm_session_state.json` exists, update the `ambiguities_status` block:
```json
{
  "total_ambiguities": <total_found>,
  "resolved": <count_resolved_this_session>,
  "pending": <remaining_count>,
  "last_resolution_at": "<ISO 8601 timestamp>"
}
```

### 5. Completion

Report:
- Fields resolved: {count}
- Remaining unresolved: {count}
- Updated: {STTM_INPUT}, {PROV_INPUT}
- Re-validation result: {pass/warning/blocker}

## Question Catalog Reference

Standard questions are drawn from `${CLAUDE_PLUGIN_ROOT}/commands/refs/sttm-guided-mode-questions.md`:
- Q1: SCD Type Unknown [BLOCKER]
- Q2: Source Modification Date [BLOCKER]
- Q3: Crypto DE Name [BLOCKER]
- Q4: Crypto Direction [BLOCKER]
- Q5: Join Cardinality [BLOCKER]
- Q6: Multi-source Primary Source [BLOCKER]
- Q7-Q20: [WARNING level questions]
- Q21-Q24: Source Volumetrics & Profiling [WARNING/INFO]
- Q25: Unqualified Column Source Table [BLOCKER]

## Important Rules

- Never auto-resolve a BLOCKER question — always ask the user
- For WARNING questions: suggest the default if one exists, but still present the choice
- Record the user's exact answer — do not paraphrase
- Update provenance to reflect the resolution source
- Re-validate after each resolution to catch cascading fixes
