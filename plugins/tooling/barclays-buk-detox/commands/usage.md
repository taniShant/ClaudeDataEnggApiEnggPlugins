---
description: Display Detox usage metrics, pipeline run history, and observability dashboard
argument-hint: "[--period 7d|30d|90d|all] [--group-by user|project|cwe|repo] [--format table|json|html] [--output PATH]"
---

# /barclays-buk-detox:usage — Usage Dashboard

Display aggregated Detox pipeline metrics from the telemetry run history.

## Arguments

| Flag | Default | Description |
|------|---------|-------------|
| `--period` | `30d` | Time window: `7d`, `30d`, `90d`, or `all` |
| `--group-by` | none | Group results by: `user`, `project`, `cwe`, or `repo` |
| `--format` | `table` | Output format: `table` (terminal), `json` (machine), `html` (report) |
| `--output` | auto | Path for HTML output (default: `~/.detox/telemetry/reports/usage-{date}.html`) |

## Execution

1. Parse arguments and validate
2. Call the deterministic Python script to generate the report. Resolve the plugin
   root cross-platform via Python (`${CLAUDE_PLUGIN_ROOT}` below is substituted inline with the
   plugin path by Claude Code — it is not an env var; do NOT use
   `$0`, and do NOT use bash-only `test -f` which fails on Windows PowerShell/cmd):

```bash
echo '{"period": "{period}", "group_by": "{group_by}", "format": "{format}", "output": "{output}"}' | {python} -c "import os,sys,runpy; r=r'${CLAUDE_PLUGIN_ROOT}'; p=os.path.join(r,'scripts','telemetry','usage_report.py'); sys.exit('FATAL: usage_report.py not found under CLAUDE_PLUGIN_ROOT='+repr(r)) if not (r and os.path.isfile(p)) else runpy.run_path(p, run_name='__main__')"
```
`{python}` is the first of these that prints `3` — run each as its own command, in order:
`python3 -c "import sys; print(sys.version_info[0])"`, `py -3 -c "import sys; print(sys.version_info[0])"`,
`python -c "import sys; print(sys.version_info[0])"`. Detox does not install Python: if none prints `3`,
report "Python 3 is required but was not found (checked: python3, py -3, python) — install Python 3
and re-run." and STOP.

3. Display the result:
   - **table** format: Print the rendered ASCII dashboard directly to the user
   - **json** format: Print the raw JSON report
   - **html** format: Write the HTML file and inform the user of the path

## What It Shows

- **Usage Overview**: Total runs, unique users, unique repos, runs/day average, most active repo and user
- **Performance**: Average, median, p95 total duration; per-phase breakdown with visual bars
- **Effectiveness**: CWEs remediated, fix success rate, validation pass rate, test pass rate
- **Security Posture**: Top CWEs fixed (ranked), severity distribution
- **Cost (Estimated)**: Total agent invocations, model distribution, estimated budget cap
- **Errors**: Pipeline failure count and rate, common failure reasons, total retries
- **Repos Covered**: Per-repo breakdown with runs, success rate, CWEs fixed
- **CONTRIBUTING Step 5**: Invocation count, flag frequency, self-check pass rate

## Data Source

Reads from `~/.detox/telemetry/runs.jsonl` — the append-only run history populated by the pipeline orchestrator at the end of each `/barclays-buk-detox:remediate` run.

If no telemetry data exists yet (first time), display a message explaining that data will accumulate after pipeline runs.

## Examples

```bash
# Default: last 30 days, terminal table
/barclays-buk-detox:usage

# Last 7 days, grouped by repo
/barclays-buk-detox:usage --period 7d --group-by repo

# Export as JSON for CI consumption
/barclays-buk-detox:usage --period 90d --format json

# Generate executive HTML report
/barclays-buk-detox:usage --format html --period 30d --output /shared/reports/detox-monthly.html
```
