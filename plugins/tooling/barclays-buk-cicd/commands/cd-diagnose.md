---
description: Diagnose a Harness CD pipeline execution failure — fetches execution data via the Harness CLI and produces a structured root cause report
argument-hint: EXECUTION_URL [OUTPUT_PATH]
---

You are the main Claude Code agent.

When the user runs `/barclays-buk-cicd:cd-diagnose`, they want to diagnose a failed Harness CD pipeline execution. Parse the execution URL, fetch data via the Harness CLI script, and delegate reasoning to the `cd-diagnose-agent`.

## Step 1: Parse arguments

```
FORMAT: EXECUTION_URL [OUTPUT_PATH]

POSITIONAL (required):
  EXECUTION_URL   Full Harness execution URL
                  e.g. https://barclays.harness.io/ng/account/.../orgs/.../projects/.../deployments/<id>/pipeline

POSITIONAL (optional):
  OUTPUT_PATH     Where to write the diagnosis report
                  Default: ./harness-cd-diagnosis.md
```

If no `EXECUTION_URL` is provided, report:
```
Usage: /barclays-buk-cicd:cd-diagnose EXECUTION_URL [OUTPUT_PATH]

Example:
  /barclays-buk-cicd:cd-diagnose https://barclays.harness.io/ng/account/.../deployments/eUme.../pipeline
```
and STOP.

## Step 2: Extract URL components

Parse the execution URL to extract:

| Component | URL segment |
|-----------|-------------|
| `instance` | hostname — `barclays.harness.io` or `barclays-nonprod.harness.io` |
| `plan_id` | segment after `/deployments/` |

Determine the CLI profile:
- `barclays.harness.io` → `--profile prod`
- `barclays-nonprod.harness.io` → `--profile nonprod`

If `plan_id` is empty or the URL does not contain `/deployments/`, report:
```
Invalid execution URL — expected format:
  https://barclays.harness.io/ng/account/.../deployments/<planExecutionId>/pipeline
```
and STOP.

## Step 3: Resolve PLUGIN_DIR

Locate the absolute path to this plugin's root directory — the folder containing `scripts/`, `agents/`, `commands/`. This is where `harness_diagnose.py` lives.

```bash
bash -lc 'find ~/.claude -type f -name "harness_diagnose.py" 2>/dev/null | head -1'
```

> **Note:** `~/.claude` is the default Claude Code plugin installation directory. BUK plugins are installed here by `/plugin install`.

Strip the `scripts/harness_diagnose.py` suffix to get `PLUGIN_DIR`. If the file is not found, report:
```
Plugin script not found — is barclays-buk-cicd installed?
Run: /plugin install barclays-buk-cicd@barclays-cio-buk
```
and STOP.

## Step 4: Run harness_diagnose.py

```bash
# Detect Python: DevHome path (BUK Windows) or python3 from PATH (macOS/Linux)
if [ -f "/c/devhome/tools/python3.12/current/python" ]; then
  PYTHON_BIN="/c/devhome/tools/python3.12/current/python"
else
  PYTHON_BIN="python3"
fi
$PYTHON_BIN $PLUGIN_DIR/scripts/harness_diagnose.py \
  --exec-id <plan_id> \
  --profile  <prod|nonprod>
```

The script writes to the current directory:
- `harness_execution.json` — execution summary
- `harness_steps.json` — all steps with status and log keys
- `harness_log_<step>_<id>.json` — one per failed step (best-effort)

It also prints a JSON summary to stdout:
```json
{
  "failed_steps": {"<log_key>": "<step name>", ...},
  "execution_file": "harness_execution.json",
  "steps_file": "harness_steps.json",
  "log_files": ["harness_log_<step>_<id>.json", ...]
}
```

**On exit code 1** (CLI error / auth): show the message printed to stderr and STOP.
**On exit code 2** (API error): show the error and STOP.
**On exit code 3** (unexpected): show the error and STOP.

## Step 5: Detect pipeline type

Read `harness_execution.json` and extract the org and pipeline identifier to determine the pipeline family:

```
org = execution.orgIdentifier (or from pipelineExecutionSummary.orgIdentifier)
pipeline = execution.pipelineIdentifier (or pipelineExecutionSummary.pipelineIdentifier)
```

Map to `PIPELINE_TYPE`:

| Org + pipeline pattern | PIPELINE_TYPE |
|------------------------|---------------|
| org=`MCA`, pipeline targets BCP2 (identifier contains `non_prod`, `nonprod`, or `bcp2`) | `bcp2` |
| org=`MCA`, pipeline targets prod BCP2 (identifier contains `prod` and not `aws`) | `bcp2` |
| org=`MCA`, pipeline targets AWS (identifier contains `aws`) | `aws` |
| anything else | _(omit — no pipeline pattern skill)_ |

If `PIPELINE_TYPE` cannot be determined, print a note to the user:
```
Note: pipeline type not recognised — proceeding without pipeline-specific diagnostics.
      Pipeline-specific failure patterns and escalation contacts will not be available.
```
Then proceed without it.

## Step 6: Delegate to cd-diagnose-agent

Use the Task tool with `subagent_type: "barclays-buk-cicd:cd-diagnose-agent"`:

```
Diagnose this Harness CD execution failure.

EXECUTION_URL:  <execution_url>
OUTPUT_PATH:    <output_path>
PIPELINE_TYPE:  <bcp2 | aws | omit if unknown>

Fetch output from harness_diagnose.py (files already written to current directory):
- harness_execution.json
- harness_steps.json
- log files: <log_files list>

Failed steps identified by the fetch script: <failed_steps dict>

Read these files and produce the diagnosis report.
```

**Fallback**: If the subagent is unavailable, read the JSON files directly and produce the diagnosis report inline following the report structure from the `cd-diagnose-agent`.

## Step 7: Clean up

After the agent returns, delete the temporary fetch files:
```bash
rm -f harness_execution.json harness_steps.json harness_log_*.json
```

## Usage examples

```bash
# Diagnose a prod execution
/barclays-buk-cicd:cd-diagnose https://barclays.harness.io/ng/account/NTEwZ.../all/orgs/MCA/projects/MCA_Prod/deployments/eUmeIVTiScKDHQznhdvfGA/pipeline

# Write report to a specific path
/barclays-buk-cicd:cd-diagnose https://barclays.harness.io/ng/account/.../deployments/eUme.../pipeline /workspace/my-diagnosis.md
```
