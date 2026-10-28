---
description: Validate BRA or Data Modeller output against quality gates
disable-model-invocation: false
argument-hint: <output-path> [--type bra|dm]
---

# /dm-validate

Validate a Business Requirement or Data Model document against MUST-HAVE and SHOULD-HAVE quality gates. Returns an APPROVED or REJECTED verdict with specific findings.

## Usage

```
/dm-validate dm-output/BUKL2CUSX-2355/business-requirement.md --type bra
/dm-validate dm-output/BUKL2CUSX-2355/data-model.md --type dm
/dm-validate dm-output/BUKL2CUSX-2355/data-model.md
```

## Behaviour

### Step 1: Read Output Document

1. Read the file at the specified `<output-path>`
2. If file not found → report error: `"Document not found at <path>. Run the relevant /dm-* command first."`, **HALT**

### Step 2: Determine Document Type

- If `--type bra` → validate as BRA output
- If `--type dm` → validate as Data Model output
- If no `--type` → auto-detect:
  - Contains "BUSINESS REQUIREMENT" header + numbered sections 1-9 → BRA
  - Contains "DATA MODEL" header + `PRIMARY KEY` declarations + Mermaid diagrams → DM
  - Cannot determine → ask user: `"Cannot auto-detect document type. Please specify: --type bra or --type dm"`

### Step 3: Invoke DM Validation Agent

Invoke `dm-validation-agent` via Agent tool with:
- The full document content
- The document path
- The determined type (`bra` or `dm`)

### Step 4: Display Verdict

Display the agent's structured verdict output directly:
- ✅ APPROVED or ❌ REJECTED
- MUST-HAVE results table
- SHOULD-HAVE results table
- Summary counts

### Step 5: Update Tracking

Read or create `dm-session/tracking.json` (schema: `schemas/dm_tracking.schema.json`).
Append to `commands_run` and update `outputs.bra_validation` or `outputs.dm_validation`.

### Step 6: Suggest Next Step

**If APPROVED:**
```
✅ Validated. This artefact is ready for downstream consumption.
```

**If REJECTED:**
```
→ Action needed: Fix the flagged issues, then re-run the relevant command (/dm-bra or /dm-model).
```

---

## Isolation

- Does not produce output files — only displays the verdict
- Tracking goes to `dm-session/` — never touches `session/`
- Existing plugin commands and hooks are unaffected
