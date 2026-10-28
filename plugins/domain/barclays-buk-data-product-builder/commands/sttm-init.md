---
description: Initialize STTM plugin workspace directories and configuration
disable-model-invocation: false
---

# /sttm-init — Initialize STTM Plugin Workspace

Set up workspace directories for the STTM plugin in the current project.

## Description

When this plugin is installed in another project (not its own repo), the workspace directories (`input/`, `output/`) won't exist. This command detects the situation and scaffolds what's needed.

Plugin assets (`configs/sttm/`, `agents/refs/`, `examples/sttm/`, `templates/sttm/`) remain at the plugin's install path — they are NOT copied into the consumer project.

## Arguments

- `--force`: Re-create workspace structure even if it already exists (default: false)

## Workflow

### Step 0 — RESOLVE PLUGIN ROOT

`${CLAUDE_PLUGIN_ROOT}` is automatically set by the plugin loader. Verify:
- `${CLAUDE_PLUGIN_ROOT}/configs/sttm/template_spec.yaml` exists

If missing, STOP with: "❌ Plugin root not resolved. Ensure barclays-buk-data-product-builder plugin is loaded."

### Step 1 — Verify Hard Dependencies

Verify all hard dependencies exist at the plugin root:
- `${CLAUDE_PLUGIN_ROOT}/configs/sttm/template_spec.yaml`
- `${CLAUDE_PLUGIN_ROOT}/configs/sttm/scenarios.yaml`
- `${CLAUDE_PLUGIN_ROOT}/configs/sttm/validation_rules.yaml`
- `${CLAUDE_PLUGIN_ROOT}/configs/sttm/audit_columns.yaml`
- `${CLAUDE_PLUGIN_ROOT}/configs/sttm/precedence.yaml`
- `${CLAUDE_PLUGIN_ROOT}/configs/sttm/naming_conventions.yaml`
- `${CLAUDE_PLUGIN_ROOT}/configs/sttm/interview_questionnaire.yaml`
- `${CLAUDE_PLUGIN_ROOT}/templates/sttm/mapping_spec.md`
- `${CLAUDE_PLUGIN_ROOT}/schemas/sttm_input_contract.schema.json`

If any missing → ERROR: "Plugin installation is incomplete at ${CLAUDE_PLUGIN_ROOT}. Missing: [list]"

### Step 2 — Check if Already Initialized (Idempotency)

Check if workspace directories already exist in CWD:
- If `input/` and `output/` both exist and `--force` is not set:
  - If `output/sttm_session_state.json` exists, read and report current session status:
    ```
    ✅ STTM workspace already initialized.
    Session: {session_id} (created {created_at})
    Pipeline: {generation_status.overall_status}
    Use --force to re-create.
    ```
  - Else report: "✅ STTM workspace already initialized. Use --force to re-create."
  - Exit successfully

### Step 3 — Create Workspace Directories

Create workspace directories in CWD:
```
input/
input/source_metadata/
input/source_dictionary/
input/design_docs/
input/code/
output/
output/provenance/
```

### Step 4 — Create Session State

Generate a unique session ID and write the initial session state file:

1. Generate `session_id` = `sttm_<YYYYMMDD_HHMMSS>` (current timestamp)
2. **Stale session detection**: If `output/sttm_session_state.json` already exists:
   - Read the existing state
   - If `generation_status.overall_status` is `"completed"`:
     - Warn: "⚠️ Previous session {session_id} completed. Starting fresh session."
   - If `generation_status.overall_status` is `"in_progress"` or `"halted"`:
     - Warn: "⚠️ Previous session {session_id} was {status}. Overwriting with fresh session."
3. Write `output/sttm_session_state.json`:
```json
{
  "session_id": "sttm_<YYYYMMDD_HHMMSS>",
  "created_at": "<ISO 8601 timestamp>",
  "workspace_initialized": true,
  "output_prefix": null,
  "target_database": null,
  "target_tables": [],
  "classification": null,
  "generation_status": {
    "step_1_ingest": "pending",
    "step_2_interview": "pending",
    "step_3_normalize": "pending",
    "step_4_classify": "pending",
    "step_5_lineage": "pending",
    "step_6_rowgen": "pending",
    "step_7_validate": "pending",
    "step_8_export": "pending",
    "overall_status": "pending"
  },
  "python_path": null,
  "python_version": null,
  "ingestion_status": null,
  "validation_result": null,
  "ambiguities_status": null,
  "output_files": null
}
```
4. Verify write: Read back and confirm `session_id` matches

### Step 4b — Python Runtime Validation (non-blocking)

Follow `agents/refs/python-runtime-contract.md § Detection Algorithm`:

1. Run `python --version` — if exit code 0: store `python_path = "python"` and `python_version = "<detected version>"`
2. Else if `PYTHON_PATH` environment variable is set → use that value directly
3. Else run `python3 --version` — if exit code 0: store that path
4. Else run `py --version` — if exit code 0: store `py`
5. If all fail: store `python_path = null`, `python_version = null` and log WARNING:
   ```
   ⚠️ Python not found on PATH.
   Impact:
     • Excel export (openpyxl) will be UNAVAILABLE
     • sqlglot-based SQL parsing will fall back to LLM interpretation
     • All other STTM operations still work (no Python needed)
   To enable:
     • Ensure 'python' is on PATH (most common)
     • export PYTHON_PATH="/path/to/python"
     • Or add to .claude/settings.json: { "env": { "PYTHON_PATH": "/path/to/python" } }
   ```

Update `output/sttm_session_state.json` with `python_path` and `python_version` fields. This check is **non-blocking** — init always continues. Downstream STTM commands read `python_path` from session state, never re-probe.

### Step 5 — Update .gitignore

Update `.gitignore` (create if not exists, append if exists):
- Add `output/` if not already listed

### Step 6 — Report Summary

Report summary:
```
✅ STTM workspace initialized!

Session:         {session_id}
Plugin location: ${CLAUDE_PLUGIN_ROOT}
Workspace root:  <CWD>

Created:
  📁 input/source_metadata/
  📁 input/source_dictionary/
  📁 input/design_docs/
  📁 input/code/
  📁 output/
  📁 output/provenance/
  📄 output/sttm_session_state.json
  📄 .gitignore (updated)

Next steps:
  1. Place your target schema in input/ (Excel or markdown)
  2. Place SQL/PySpark code in input/code/
  3. Place source metadata in input/source_metadata/ (optional)
  4. Run /sttm-generate to produce the mapping
```

## Important Rules

- NEVER copy configs/sttm/ or templates/sttm/ into the consumer project — always reference from plugin path
- If `--force` is set, recreate workspace dirs even if they exist (does not delete existing files)
- Running `/sttm-init` multiple times is idempotent — it won't overwrite existing input files
