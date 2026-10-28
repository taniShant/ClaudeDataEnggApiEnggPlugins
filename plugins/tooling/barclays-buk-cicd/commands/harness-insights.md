---
description: Answer inventory and analytics questions about Harness — orgs, projects, pipelines, execution counts, status breakdowns, and comparisons
argument-hint: "QUESTION [--nonprod]"
---

You are the main Claude Code agent.

When the user runs `/barclays-buk-cicd:harness-insights`, they want to answer a question about Harness using live data. Collect the data via the Harness CLI and delegate reasoning and formatting to the `harness-insights-agent`.

## Step 1: Parse arguments

```
FORMAT: QUESTION [--nonprod]

POSITIONAL (required):
  QUESTION    Free-text question about Harness
              e.g. "how many pipelines failed in the last 24 hours"
              e.g. "what orgs exist"
              e.g. "what is the difference between prod and nonprod projects"

FLAG (optional):
  --nonprod   Target the nonprod Harness instance instead of prod
```

If no QUESTION is provided, print usage and STOP:
```
Usage: /barclays-buk-cicd:harness-insights QUESTION [--nonprod]

Examples:
  /barclays-buk-cicd:harness-insights how many pipelines failed in the last 24 hours
  /barclays-buk-cicd:harness-insights what orgs exist --nonprod
  /barclays-buk-cicd:harness-insights compare prod and nonprod projects
```

Strip `--nonprod` from the question text if present. Set:
- `--nonprod` present → `profile=nonprod`, `instance=barclays-nonprod.harness.io`
- default → `profile=prod`, `instance=barclays.harness.io`

If question contains "compare" or "difference" and mentions both prod and nonprod, set `compare_mode=true` — data will be fetched from both instances.

## Step 2: Resolve PLUGIN_DIR

```bash
bash -lc 'find ~/.claude -type f -name "harness_insights.py" 2>/dev/null | head -1'
```

Strip `scripts/harness_insights.py` to get `PLUGIN_DIR`. If not found:
```
Plugin script not found — is barclays-buk-cicd installed?
Run: /plugin install barclays-buk-cicd@barclays-cio-buk
```
and STOP.

## Step 3: Run harness_insights.py

```bash
# Detect Python: DevHome path (BUK Windows) or python3 from PATH (macOS/Linux)
if [ -f "/c/devhome/tools/python3.12/current/python" ]; then
  PYTHON_BIN="/c/devhome/tools/python3.12/current/python"
else
  PYTHON_BIN="python3"
fi
$PYTHON_BIN $PLUGIN_DIR/scripts/harness_insights.py \
  --question "QUESTION" \
  --profile  <prod|nonprod>
```

For compare mode, run twice:
```bash
$PYTHON_BIN $PLUGIN_DIR/scripts/harness_insights.py \
  --question "QUESTION" --profile prod
$PYTHON_BIN $PLUGIN_DIR/scripts/harness_insights.py \
  --question "QUESTION" --profile nonprod
```

The script emits a JSON summary to stdout:
```json
{
  "profile": "prod",
  "question": "...",
  "data_files": ["harness_insights_orgs.json", "harness_insights_projects.json", ...],
  "data_summary": {"orgs": 3, "projects": 12, ...}
}
```

On exit code 1 (CLI error): show stderr and STOP.

## Step 4: Delegate to harness-insights-agent

Use the Task tool with `subagent_type: "barclays-buk-cicd:harness-insights-agent"`:

```
Answer this Harness question using the data files already fetched.

QUESTION: <question>
PROFILE:  <prod|nonprod|both>
OUTPUT_PATH: ./harness-insights-answer.md

Data files written to current directory:
<list from data_files>

Data summary: <data_summary>
```

**Fallback**: If the subagent is unavailable, read the JSON files directly and answer inline.

## Step 5: Clean up

```bash
rm -f harness_insights_*.json
```
