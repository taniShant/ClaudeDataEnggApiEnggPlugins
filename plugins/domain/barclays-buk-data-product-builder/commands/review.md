---
description: Review generated code for quality, redundancy, and correctness — both platforms
disable-model-invocation: false
---

# /review

Review all generated PySpark code for quality, redundancy, and correctness. Applicable to **both Glue and Databricks**. Runs after all generation commands complete, before `/validate`.

## Prerequisites

- Session state exists with `platform` set
- At least one generation command has completed (`transform_generator` in `agent_status`)
- Generated artefacts exist in `generated/` directory

## Orchestration Position

```
/gen-tests → /review → /validate → /push
```

---

## STEP 0 — Load Context

1. Read `session/session_state.json`
2. Determine `platform` (glue | databricks)
3. Collect all generated file paths from `artefact_status`
4. Check resume: if `agent_status.code_review == "completed"` and no artefacts have been regenerated since last review → skip (log [SKIP])

## STEP 1 — Identify Review Targets

### Glue Platform
- All `generated/glue/transforms/*_transform_day0.py` files
- All `generated/glue/transforms/*_transform_day1.py` files
- All `generated/glue/wrapper/*_wrapper.py` files
- All `generated/glue/wrapper/*_config.json` files (validate structure only)
- All `generated/glue/dags/*_dag.py` files
- All test files in `generated/glue/tests/`

### Databricks Platform
- All `generated/databricks/src/Notebooks/{day0|day1}/{target_schema}_{table}/*_transform.py` files
- All `generated/databricks/src/Notebooks/{day0|day1}/{target_schema}_{table}/*_driver.py` files
- All `generated/databricks/src/Notebooks/{day0|day1}/{target_schema}_{table}/*_config.yml` files (validate structure only)
- `generated/databricks/src/Notebooks/utilities/{target_schema}_table_creation_utility.py` (DDL embedded)
- All `generated/databricks/dags/*_dag.py` files
- All test files in `generated/databricks/tests/`

### Both Platforms
- `generated/{platform}/tests/conftest.py`
- `generated/{platform}/tests/pytest.ini`

## Phase A — Review Only (Isolated Context)

### STEP 2 — Invoke Code Review Agent (Findings Only)

Delegate to `code-review-agent` (using the Agent tool) with:
- List of file paths to review
- Platform identifier
- Mapping document context (column names, source tables) from `session/mapping_parsed.json`
- Intent identification from `session/intent_identification.json`
- Domain knowledge text from session state (if loaded)

**CRITICAL**: The code-review-agent produces a **findings list ONLY**. It does NOT re-invoke generators or modify files. Its sole output is structured findings with severity, location, and fix direction. This keeps the review agent's context bounded (no re-generation accumulation).

### STEP 3 — Classify Findings (Action Matrix)

For each finding returned by the review agent:

| Severity | Category | Action |
|----------|----------|--------|
| **Critical** | Wrong column/table reference, layer violation, security | Route to Phase B (fix cycle) |
| **Critical** | Cross-artefact consistency (alias mismatch, db/table mismatch, mesh↔transform column mismatch) | Route to Phase B (fix cycle) |
| **High** | Logic errors, missing joins, crypto misuse, hardcoded values, anti-patterns | Route to Phase B (fix cycle) |
| **High** | Cross-artefact consistency (source type mismatch, filter/load-type mismatch, DTXOG path mismatch, reader/writer mismatch) | Route to Phase B (fix cycle) |
| **Medium** | Redundant code (dead imports, duplicates, unreachable code, unused vars) | **Auto-fix in-place**: remove the redundant lines directly (no agent needed) |
| **Medium** | Style/naming issues | Log `[WARN]` to `logs/de-pipeline.log` + continue |
| **Low** | Suggestions, alternative approaches | Log to `session/audit_log.jsonl` + ignore |

### Auto-Fix Logic (Medium — Redundant Code)

For `auto_fixable: true` findings (executed directly by command, no agent delegation):
- `fix_action: "remove_line"` → Delete the specified line(s) from the file
- `fix_action: "collapse_duplicate"` → Keep first occurrence, remove subsequent duplicates
- `fix_action: "remove_block"` → Remove the entire unreachable block (from line to next non-indented line)

---

## Phase B — Fix Cycle (Isolated Per-Finding)

For each Critical/High finding, spawn a **SEPARATE, ISOLATED agent invocation** for re-generation. Each fix agent gets minimal context (not the full review session):

### STEP 4 — Re-Generation (Isolated Context Per Finding)

1. **Identify the originating agent:**
   - Transform files → `transform-generator-agent`
   - Wrapper/config → `glue-wrapper-agent`
   - Mesh JSON → `glue-mesh-agent`
   - DTXOG config → `glue-dtxog-agent`
   - DAG files → `dag-generator-agent`
   - Driver/DDL → `databricks-artefact-agent` (pass `artefact_scope: "driver"` for driver files, `artefact_scope: "ddl"` for DDL files)
   - Test files → `test-generator-agent`

2. **Spawn isolated agent** (using the Agent tool, fresh context) with ONLY:
   - The finding description and fix direction
   - The affected file path (agent reads it)
   - The relevant template for this file type
   - Minimal session context: target_table, load_type, table_type (from checkpoint or session state)
   ```
   REVIEW FINDING (must fix): {finding.description} in {finding.file}:{finding.line}
   Fix direction: {finding.fix_hint}
   ```

3. **Do NOT pass**: full mapping_parsed.json, all other generated files, domain knowledge (unless the finding specifically requires it), other findings

### Cross-Artefact Finding Routing

For findings with `category: "cross_artefact_consistency"`, the originating agent depends on which artefact needs correction:

| Finding | Originating Agent |
|---------|-------------------|
| Config ↔ Transform alias mismatch | `glue-wrapper-agent` (config defines aliases; transform consumes them) |
| Config database/tablename mismatch | `glue-wrapper-agent` |
| Config source table type mismatch | `glue-wrapper-agent` (config filter section structure) |
| Config filters ↔ load type mismatch | `glue-wrapper-agent` |
| DTXOG ↔ Wrapper/Config S3 path mismatch | `glue-dtxog-agent` (DTXOG references wrapper+config paths) |
| Reader/Writer ↔ Transform PK/partition mismatch | `transform-generator-agent` (transform instantiates writer with wrong args) |
| Mesh JSON ↔ Transform column mismatch | `glue-mesh-agent` (if mesh has extra columns) or `transform-generator-agent` (if transform missing columns) |
| DDL partition ↔ Transform alignment (Databricks) | `transform-generator-agent` |
| DAG ↔ job.yml param mismatch (Databricks) | `dag-generator-agent` (DAG defines param mapping) |
| DAG ↔ DTXOG lambda/S3 mismatch (Glue) | `dag-generator-agent` (DAG consumes DTXOG values) |
| DAG ↔ wrapper naming mismatch (Glue) | `dag-generator-agent` (DAG references wrapper table names) |

Context passed to originating agent (minimal — isolated):
```
CROSS-ARTEFACT FINDING (must fix): {finding.description}
Affected files: {finding.file} ↔ {related_file}
Target table: {target_table}  Load type: {load_type}  Table type: {table_type}
```

---

## Phase C — Re-Review (Affected Files Only)

### STEP 5 — Targeted Re-Review

After ALL Phase B fixes complete, spawn ONE final `code-review-agent` invocation reviewing ONLY the files that were modified in Phase B (not all generated files).

- Input: only modified file paths (not the full target list from STEP 1)
- Same review checks apply but scoped to fewer files
- This keeps re-review context minimal

### STEP 6 — Retry Logic

- **Max retries per finding**: 2 (Phase B attempted twice per finding before giving up)
- If a Critical/High finding persists after 2 re-generation attempts:
  - Mark `agent_status.code_review = "rejected"`
  - Log `[ERROR] Review finding not resolved after 2 retries: {finding.description}`
  - HALT — do not proceed to `/validate`
  - Display remaining findings to user

## STEP 5 — Write Results

Write `session/code_review_results.json`:

```json
{
  "review_status": "PASS|FINDINGS|REJECTED",
  "platform": "glue|databricks",
  "files_reviewed": 8,
  "retry_count": 0,
  "findings": [],
  "summary": {
    "critical": 0,
    "high": 0,
    "medium_auto_fixed": 3,
    "medium_logged": 1,
    "low": 2
  },
  "auto_fixes_applied": [
    {
      "file": "generated/glue/mortgage_account_balance_transform_day0.py",
      "line": 5,
      "action": "remove_line",
      "description": "Removed unused import: from pyspark.sql.functions import lit"
    }
  ]
}
```

## STEP 6 — Update Session State

```json
{
  "agent_status": {
    "code_review": "completed"
  },
  "artefact_status": {
    "review_results": "session/code_review_results.json"
  }
}
```

Log to `session/audit_log.jsonl`:
```json
{"timestamp": "...", "event": "code_review_completed", "findings_count": 5, "auto_fixed": 3, "review_status": "PASS"}
```

---

## Failure Modes

| Condition | Behaviour |
|-----------|-----------|
| No generated artefacts found | HALT with error: "No generated files to review. Run generation commands first." |
| Critical finding persists after 2 retries | HALT with `review_status: "REJECTED"` — display findings |
| Session state missing platform | HALT with error: "Platform not set. Run /init first." |
| Review agent timeout (>25 turns) | Mark as FINDINGS with partial results; log [WARN] |

---

## Anti-Hallucination Rules

- NEVER invent findings — only report issues found by reading the actual generated code
- NEVER auto-fix code that changes business logic (only remove provably dead/redundant code)
- NEVER assume a column exists — verify against mapping_parsed.json
- NEVER skip a file because it "looks fine" — every file in the target list MUST be reviewed
- ALWAYS read the file content before reporting findings (no findings from memory)
