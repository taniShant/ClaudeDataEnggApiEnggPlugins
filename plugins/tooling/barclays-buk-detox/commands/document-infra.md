---
description: Generate corrective action documents for infrastructure/config findings that cannot be fixed in code
argument-hint: THREAT_MODEL_PATH [--output-dir DIR]
---

You are the main Claude Code agent.

When the user runs `/barclays-buk-detox:document-infra`, they want to **generate corrective action documentation** for infrastructure and configuration findings that cannot be auto-fixed in source code.

## Options

| Option | Required | Description |
|---|---|---|
| `THREAT_MODEL_PATH` | Yes | Path to threat model Markdown report |
| `--output-dir DIR` | No | Output directory for generated docs (default: ./corrective_actions_output) |

## Step 1: Parse Arguments

```
FORMAT: THREAT_MODEL_PATH [--output-dir DIR]

POSITIONAL (required):
  THREAT_MODEL_PATH    Path to threat model Markdown report

FLAGS (optional):
  --output-dir DIR     Output directory for generated docs (default: ./corrective_actions_output)
```

## Step 2: Validate Arguments

### 2.1 Validate threat_model_path
- File must exist
- Must have `.md` extension

**On failure:** Report "Threat model file not found: {path}" and STOP.

### 2.2 Validate output_dir (if provided)
- If directory does not exist, it will be created
- Parent directory must exist

## Step 3: Delegate to detox-orchestrator-agent

**Delegate to Subagent**: Use the Task tool with `subagent_type: "barclays-buk-detox:detox-orchestrator-agent"`:

```
Run infrastructure documentation stage only:
- mode: document_infra_only
- threat_model_path: {threat_model_path}
- output_dir: {output_dir}
```

**Fallback Behavior**: If the orchestrator is unavailable, perform directly:
1. Parse the threat model to identify infra/config findings
2. For each finding classified as `infra_config`, generate a corrective action document:
   - Finding title and CWE ID
   - Severity level
   - Detailed description
   - Recommended remediation steps
   - Responsible team suggestion
3. Save documents to the output directory
4. Display a summary table

## Step 4: Report Results

Display:
```
✅ CORRECTIVE ACTION DOCUMENTS GENERATED

| # | Finding | CWE | Severity | Output File |
|---|---------|-----|----------|-------------|
| 1 | ...     | ... | ...      | ...         |

Total: {count} documents written to {output_dir}/
```

## Usage Examples

### Example 1: Default Output Directory
```bash
/barclays-buk-detox:document-infra ./threat-model.md
```

### Example 2: Custom Output Directory
```bash
/barclays-buk-detox:document-infra ./reports/threat-model.md --output-dir ./docs/corrective-actions
```
