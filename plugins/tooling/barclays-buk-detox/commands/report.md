---
description: Generate a comprehensive DETOX-REMEDIATION-REPORT at repo level — holistic view of all remediation activities, fixes, skipped items, and next steps
argument-hint: --repo PATH [--wiz-report PATH] [--threat-model PATH] [--jira JIRA_ID] [--branch NAME] [--base-branch NAME] [--output PATH] [--generate-corrective-actions]
---

You are the main Claude Code agent.

When the user runs `/barclays-buk-detox:report`, they want to **generate a comprehensive, executive-level DETOX-REMEDIATION-REPORT** for a repository. This report provides a holistic view of all remediation activities — what was fixed, what was skipped, what needs manual review, commit details, and next steps.

This command can be run:
1. **After a `/barclays-buk-detox:remediate` run** — to regenerate or enhance the report with additional context
2. **Standalone** — to generate a report by analyzing git history, WIZ reports, and threat models without running the full pipeline

## Options

| Option | Required | Description |
|---|---|---|
| `--repo PATH` | Yes | Path to project: `.` for current directory or absolute path |
| `--wiz-report PATH` | No | Path to Wiz SAST/SCA JSON report (for context on total findings) |
| `--threat-model PATH` | No | Path to threat model Markdown report (for attack path context) |
| `--jira JIRA_ID` | No | JIRA ticket ID for the remediation effort |
| `--branch NAME` | No | Current remediation branch (auto-detected if not provided) |
| `--base-branch NAME` | No | Base branch the remediation was branched from (default: `main`) |
| `--output PATH` | No | Output file path (default: `{repo}/DETOX-REMEDIATION-REPORT.md`) |
| `--generate-corrective-actions` | No | Generate corrective action documents for all unresolved items into `corrective_actions_output/` |

## Step 1: Parse Arguments

```
FORMAT: --repo PATH [--wiz-report PATH] [--threat-model PATH] [--jira JIRA_ID] [--branch NAME] [--base-branch NAME] [--output PATH] [--generate-corrective-actions]

FLAGS (required):
  --repo PATH            Path to project — "." for current directory or absolute path

FLAGS (optional):
  --wiz-report PATH     Path to Wiz report JSON (SAST or SCA findings, for context on total findings)
  --threat-model PATH    Path to threat model Markdown report (for attack path context)
  --jira JIRA_ID         JIRA ticket ID for the remediation effort
  --branch NAME          Current remediation branch (auto-detected if not provided)
  --base-branch NAME     Base branch the remediation was branched from (default: main)
  --output PATH          Output file path (default: {repo}/DETOX-REMEDIATION-REPORT.md)
  --generate-corrective-actions   Generate corrective action documents for all unresolved items
                                  (partially addressed, skipped, manual review) into corrective_actions_output/
```

**Parsing rules:**
- `--repo` followed by path → `project_path`
- `--wiz-report` followed by path → `wiz_report_path`
- `--threat-model` followed by path → `threat_model_path`
- `--jira` followed by value → `jira_id`
- `--branch` followed by value → `branch_name`
- `--base-branch` followed by value → `base_branch`
- `--output` followed by path → `output_path`
- `--generate-corrective-actions` (boolean flag, no value) → `generate_corrective_actions = true`

## Step 2: Validate Arguments (MANDATORY - DO NOT SKIP)

### 2.1 Validate project_path (--repo)

- `--repo` is required
- Path can be `.` (current directory) or an absolute path
- If `.`, resolve to the current working directory
- Must exist and be a git repository

**On failure:** Report which check failed and STOP.

### 2.2 Validate reports (optional but recommended)

- If `--wiz-report` is provided, file must exist and have `.json` extension
- If `--threat-model` is provided, file must exist and have `.md` extension
- If neither is provided, the report will be generated from git history analysis only

### 2.3 Validate jira_id (if provided)

- Must match regex: `^[A-Z]+-[0-9]+$`

### 2.4 Validate branch (auto-detect if not provided)

- If not provided, detect current branch via `git branch --show-current`
- If not provided, detect base branch by checking for `main` or `master`

## Step 3: Report Validation Results

After validation passes, display:
```
✅ DETOX REPORT ARGUMENTS VALIDATED
   project_path: {project_path}
   wiz_report: {wiz_report_path or "not provided"}
   threat_model: {threat_model_path or "not provided"}
   jira_id: {jira_id or "not provided"}
   branch: {branch_name}
   base_branch: {base_branch}
   output: {output_path}
   generate_corrective_actions: {generate_corrective_actions or "false"}

Generating DETOX-REMEDIATION-REPORT...
```

## Step 4: Delegate to detox-report-agent

**Delegate to Subagent**: Use the Task tool with `subagent_type: "barclays-buk-detox:detox-report-agent"` to invoke the report generation agent with the validated arguments.

**Delegation Prompt Format:**
```
Generate a comprehensive DETOX-REMEDIATION-REPORT with the following inputs:
- project_path: {project_path}
- wiz_report_path: {wiz_report_path or "None"}
- threat_model_path: {threat_model_path or "None"}
- jira_id: {jira_id or "None"}
- branch_name: {branch_name}
- base_branch: {base_branch}
- output_path: {output_path}
- generate_corrective_actions: {generate_corrective_actions or "false"}
```

**Important:**
- Do NOT construct detailed workflow instructions — the report agent has its own logic
- The report agent analyzes the repo, git history, reports, and generates the full document
- Do NOT add domain logic here — this is a thin command

**Fallback Behavior**: If the `detox-report-agent` subagent is unavailable, inform the user that the detox plugin requires the report agent and suggest checking plugin installation.

## Step 5: Report Results

After the report agent returns, display:
```
✅ DETOX-REMEDIATION-REPORT GENERATED

   Output: {output_path}

   Summary:
   - Total findings: {count}
   - Fixes applied: {fixed_count}
   - Items skipped (out-of-repo): {skipped_count}
   - Manual review required: {manual_count}
   - Attack paths addressed: {addressed_count}
   - Corrective action docs: {corrective_action_count} (in corrective_actions_output/)
```

If `generate_corrective_actions` was not set, omit the last line.

## Usage Examples

### Example 1: Generate Report After Remediation
```bash
/barclays-buk-detox:report --repo . --threat-model ./AttackPaths.md --jira DIGICAW-007
```

### Example 2: Full Context Report
```bash
/barclays-buk-detox:report --repo . --wiz-report ./wiz-report.json --threat-model ./threat-model.md --jira PROJ-100 --base-branch release/v4-2026.01
```

### Example 3: Custom Output Path
```bash
/barclays-buk-detox:report --repo /path/to/project --threat-model ./threats.md --output ./docs/DETOX-REMEDIATION-REPORT.md
```

### Example 4: Report from Git History Only
```bash
/barclays-buk-detox:report --repo . --jira DIGICAW-007 --branch feature/cwe-fixes --base-branch main
```

### Example 5: Report with Corrective Action Documents
```bash
/barclays-buk-detox:report --repo . --threat-model ./AttackPaths.md --jira DIGICAW-007 --generate-corrective-actions
```
This generates the report AND produces individual corrective action documents in `corrective_actions_output/` for all partially addressed, skipped, and manual review items.

## Error Messages

### Missing --repo Flag
```
❌ VALIDATION FAILED: --repo is required

Usage: /barclays-buk-detox:report --repo PATH [--wiz-report PATH] [--threat-model PATH] [--jira JIRA_ID] [--branch NAME] [--base-branch NAME] [--output PATH]
```

### Not a Git Repository
```
❌ VALIDATION FAILED: Not a git repository

Path: {provided_path}
Error: The specified directory is not a git repository. A git repository is required for report generation.
```
