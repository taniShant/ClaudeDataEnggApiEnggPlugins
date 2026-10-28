---
description: Run the full CWE remediation pipeline — parse SAST/threat model reports, apply fixes, validate with Semgrep, create PR
argument-hint: --repo PATH --model MODEL [--wiz-report PATH] [--threat-model PATH] [--jira JIRA_ID] [--severity LEVEL] [--dry-run] [--generate-tests] [--checkout-branch NAME] [--new-branch NAME]
---

You are the main Claude Code agent.

When the user runs `/barclays-buk-detox:remediate`, they want to **scan and remediate CWE vulnerabilities** in their project using SAST reports and/or threat model reports. This command validates inputs and delegates to the detox orchestrator agent.

## Options

| Option | Required | Description |
|---|---|---|
| `--repo PATH` | Yes | Path to project: `.` for current directory, absolute path, or git URL |
| `--model MODEL` | Yes | AI model for worker agents: `sonnet`, `opus`, or `haiku` |
| `--wiz-report PATH` | At least one | Path to Wiz SAST JSON report |
| `--threat-model PATH` | At least one | Path to threat model Markdown report |
| `--jira JIRA_ID` | No | JIRA ticket ID for commit messages (e.g., `GENAIACCEL-1234`) |
| `--severity LEVEL` | No | Severity filter: `critical`, `high`, `medium`, `critical+high`, `all` (default: `all`) |
| `--dry-run` | No | Parse and classify only — no fixes applied |
| `--generate-tests` | No | Generate security regression tests for each fix (default: enabled) |
| `--no-tests` | No | Skip test generation entirely |
| `--test-mode MODE` | No | Test generation mode: `fast` (2–3 tests) or `full` (5–7 tests). Default: `fast` |
| `--checkout-branch NAME` | No | Git branch to checkout before applying fixes |
| `--new-branch NAME` | No | Branch name to create for remediation changes |

## Step 1: Parse Arguments

Parse the arguments provided after `/barclays-buk-detox:remediate`:

```
FORMAT: --repo PATH --model MODEL [--wiz-report PATH] [--threat-model PATH] [--jira JIRA_ID] [--severity LEVEL] [--dry-run] [--generate-tests] [--test-mode MODE] [--checkout-branch NAME] [--new-branch NAME]

FLAGS (required):
  --repo PATH            Path to project - "." for current directory, absolute path, or git repo URL
  --model MODEL          AI model for worker agents: sonnet, opus, or haiku

FLAGS (at least one report required):
  --wiz-report PATH     Path to Wiz report JSON (SAST or SCA findings)
  --threat-model PATH    Path to threat model Markdown report

FLAGS (OPTIONAL):
  --jira JIRA_ID         JIRA ticket ID for commit messages (e.g., GENAIACCEL-1234)
  --severity LEVEL       Severity filter: critical, high, medium, critical+high, all (default: all)
  --dry-run              Parse and classify only — no fixes applied
  --generate-tests       Generate security regression tests for each fix (default: enabled)
  --no-tests             Skip test generation entirely
  --test-mode MODE       Test generation mode: fast (2-3 tests) or full (5-7 tests). Default: fast
  --checkout-branch NAME Git branch to checkout before applying fixes
  --new-branch NAME      Branch name to create for remediation changes
```

**Parsing rules:**
- `--repo` followed by path → `project_path`
- `--model` followed by value → `model` (must be `sonnet`, `opus`, or `haiku`)
- `--wiz-report` followed by path → `sast_report_path`
- `--threat-model` followed by path → `threat_model_path`
- `--jira` followed by value → `jira_id`
- `--severity` followed by value → `severity_filter`
- `--dry-run` (boolean flag) → `dry_run = true`
- `--generate-tests` (boolean flag) → `generate_tests = true` (default: true)
- `--no-tests` (boolean flag) → `generate_tests = false`
- `--test-mode` followed by value → `test_mode` (must be `fast` or `full`, default: `fast`)
- `--checkout-branch` followed by value → `checkout_branch`
- `--new-branch` followed by value → `new_branch`

## Step 2: Validate Arguments (MANDATORY - DO NOT SKIP)

**You MUST validate ALL arguments before proceeding. If validation fails, report the error and STOP.**

### 2.1 Validate project_path (--repo)

- `--repo` is required
- Path can be `.` (current directory), an absolute path (starts with `/`), or a git URL (starts with `https://` or `git@`)
- If path is `.`, resolve it to the current working directory
- If path is a local directory, it must exist
- If path is a git URL, it will be cloned by the orchestrator

**On failure:** Report which check failed and STOP.

### 2.2 Validate model (--model)

- `--model` is required
- Must be one of: `sonnet`, `opus`, `haiku`
- Case-insensitive (normalize to lowercase)

**On failure:** Report "Invalid --model value. Must be one of: sonnet, opus, haiku" and STOP.

### 2.3 Validate reports (at least one required)

- At least one of `--wiz-report` or `--threat-model` must be provided
- If `--wiz-report` is provided, file must exist and have `.json` extension
- If `--threat-model` is provided, file must exist and have `.md` extension

**On failure:** Report "At least one of --wiz-report or --threat-model is required" and STOP.

### 2.4 Validate jira_id (if provided)

- Must match regex: `^[A-Z]+-[0-9]+$`
- Examples: GENAIACCEL-1234, DIGICAW-3667

**On failure:** Report "Invalid JIRA ID format. Expected: PROJECTKEY-12345" and STOP.

### 2.5 Validate severity_filter (if provided)

- Must be one of: `critical`, `high`, `medium`, `critical+high`, `all`
- Case-insensitive
- Default: `all`

**On failure:** Report valid options and STOP.

### 2.6 Verify Python 3 is installed

Detox does NOT install Python — it only checks that Python 3 is already present.
Run each candidate below as its own command, in order, and stop at the first one
that prints `3`. Each line is valid in bash, PowerShell and cmd, so do NOT wrap
them in a shell loop or `||` chain:

```bash
python3 -c "import sys; print(sys.version_info[0])"
py -3 -c "import sys; print(sys.version_info[0])"
python -c "import sys; print(sys.version_info[0])"
```

- The first candidate that prints `3` becomes `{python}` — use it for EVERY Detox
  script invocation in this run (macOS/Linux: normally `python3`; Windows: normally
  `py -3` or `python`).
- A candidate that errors, prints nothing, or opens the Microsoft Store (the Windows
  `python3` alias) does not count — move to the next one.

**On failure (no candidate prints `3`):** Report the "Python 3 Not Found" error
below and STOP. Do NOT attempt to install Python and do NOT continue LLM-only.

## Step 3: Report Validation Results

After validation passes, display:
```
✅ DETOX ARGUMENTS VALIDATED
   project_path: {project_path}
   model: {model}
   python: {python}
   sast_report: {sast_report_path or "not provided"}
   threat_model: {threat_model_path or "not provided"}
   jira_id: {jira_id or "not provided"}
   severity_filter: {severity_filter}
   dry_run: {dry_run}
   generate_tests: {generate_tests}
   test_mode: {test_mode}
   checkout_branch: {checkout_branch or "not provided"}
   new_branch: {new_branch or "not provided"}

Starting CWE remediation pipeline...
```

## Step 3b: Archive Stale Report (MANDATORY — DO NOT SKIP)

**Before running the pipeline, check for a leftover report from a prior run.** If
`{project_path}/DETOX-REMEDIATION-REPORT.md` already exists, it is **stale** — it
was generated by a previous remediation, not by this invocation. You MUST archive it
so it cannot be confused with a fresh result:

```bash
if [ -f "{project_path}/DETOX-REMEDIATION-REPORT.md" ]; then
  mv "{project_path}/DETOX-REMEDIATION-REPORT.md" \
     "{project_path}/DETOX-REMEDIATION-REPORT.md.bak.$(date +%Y%m%d-%H%M%S)"
fi
```

Display to user if archived:
```
⚠️  Archived stale report from prior run → DETOX-REMEDIATION-REPORT.md.bak.{timestamp}
```

**Why this matters:** If you find an existing `DETOX-REMEDIATION-REPORT.md` and
present it as the result of this run, the user sees stale data (wrong date, wrong
branch, no OTel emitted). Archiving prevents this failure mode.

## Step 4: Prepare Pipeline (Stages 0–3)

**MANDATORY — DO NOT SKIP**: Run the preparation script below BEFORE delegating to the orchestrator. The orchestrator REQUIRES the classified findings JSON that this script produces.

**Resolve the plugin root deterministically and CROSS-PLATFORM.** The script lives
under `${CLAUDE_PLUGIN_ROOT}/scripts`. `${CLAUDE_PLUGIN_ROOT}` is NOT an environment variable at runtime — Claude Code
substitutes that literal text in this file with the plugin's absolute install path
before you read it. Copy the path exactly as it appears in the snippets; do NOT read
it via `os.environ`, `$env:` or `%...%` (those are empty). Do NOT guess the path and do NOT use `$0`
(it resolves to the shell, not the plugin). Do NOT write bash-only path logic
(`test -f`, `|| { … }`) — on Windows the shell is PowerShell/cmd and that
syntax silently fails, which is what causes Stages 0–3 to be skipped. Instead let
**Python** (verified in Step 2.6, identical on macOS/Linux/Windows) resolve the path,
assert the script exists, and run it — all in one invocation:

```bash
echo '{
  "project_path": "{project_path}",
  "sast_report_path": "{sast_report_path_or_null}",
  "threat_model_path": "{threat_model_path_or_null}",
  "severity_filter": "{severity_filter}",
  "checkout_branch": {checkout_branch_json_or_null},
  "new_branch": {new_branch_json_or_null},
  "jira_id": {jira_id_json_or_null},
  "dry_run": {dry_run},
  "model": "{model}",
  "generate_tests": {generate_tests},
  "test_mode": "{test_mode}"
}' | {python} -c "import os,sys,runpy; r=r'${CLAUDE_PLUGIN_ROOT}'; p=os.path.join(r,'scripts','prepare_pipeline.py'); sys.exit('FATAL: prepare_pipeline.py not found under CLAUDE_PLUGIN_ROOT='+repr(r)+' — detox plugin not installed correctly; do NOT skip preparation or delegate a full pipeline.') if not (r and os.path.isfile(p)) else runpy.run_path(p, run_name='__main__')"
```

(`{python}` is the Python 3 command verified in Step 2.6 — the invocation is otherwise identical on every OS.)

**Fail loud, never skip.** If that command exits non-zero or prints `FATAL`, you MUST
**STOP** and report a plugin-installation problem. Do NOT work around it by skipping
preparation, performing Stages 0–3 LLM-only, or delegating a 'full pipeline' to the
orchestrator — doing so silently bypasses the mandatory Barclays setup hard-gate and
the deterministic Wiz parse/classify, which is a correctness failure.

This script executes Stages 0–3 (preflight, repo setup, report parsing, classification) and writes stage-by-stage progress to stderr. The JSON output on the last line of stdout contains the classified findings.

- If the script cannot be found or run: **STOP** with the plugin-installation error above — do NOT fall back to delegating the full pipeline.
- If `status` is `"error"`: display the error message from the output and **STOP**
- Extract from JSON output: `job_id`, `state_path` (the pipeline state file — source of truth for run telemetry), `project_path` (may have changed if cloned), `branch_name`, `base_branch`, `classified` (the full classification result), `threat_model_pending` (boolean), `summary`
- **Save the full JSON output** — the `classified` field is required by the orchestrator

If `threat_model_path` was provided, the script sets `threat_model_pending: true` because threat model parsing requires LLM. The orchestrator will handle it.

### Proof-of-Execution Gate (MANDATORY)

**You MUST have captured the JSON stdout from the bash command above in THIS
conversation turn.** The following rules are non-negotiable:

1. **If you did not run the bash command above**, you have NOT executed the pipeline.
   Go back and run it NOW. Loading the skill or saying "stand by" is not execution.
2. **Do NOT read `DETOX-REMEDIATION-REPORT.md`** as proof that the pipeline ran. The
   report is generated much later in Stage 8 by the orchestrator. If a report file
   exists before you delegated to the orchestrator, it is **STALE from a prior run**
   (you should have archived it in Step 3b).
3. **The ONLY proof that Stages 0–3 executed** is JSON output from the bash command
   containing `"status": "success"` and a non-empty `classified` field. If you do not
   have this JSON in your conversation context, you MUST run the bash command.
4. **Do NOT fabricate or assume classified findings.** If the script didn't run, you
   have no findings. Period.

## Step 5: Delegate Stages 4–9 to Orchestrator

### Gate Check (MANDATORY — DO NOT SKIP)

**Before delegating, verify you have REAL output from Step 4:**

- You MUST have the JSON output from `prepare_pipeline.py` in this conversation.
- That JSON MUST contain `"status": "success"` and a non-empty `classified` field.
- If you cannot paste/reference the `classified` findings JSON from Step 4's bash
  output, **STOP — go back to Step 4 and run the bash command.** Do NOT delegate
  with empty, assumed, or fabricated findings.
- If `prepare_pipeline.py` returned `"status": "error"`, do NOT delegate — display
  the error and STOP.

Output to user:
```
▸ Stages 4–9 — Applying fixes, validating, generating tests, creating merge request...
  This may take several minutes. Progress will appear when stages complete.
```

**Delegate to Subagent**: Use the Task tool with `subagent_type: "barclays-buk-detox:detox-orchestrator-agent"`. Pass `model: "{model}"` as the Task tool's model parameter.

**Delegation Prompt:**
```
Continue CWE remediation pipeline from Stage 4 (pre-parsed mode).
Stages 0-3 are complete — DO NOT re-run them.

Pipeline inputs:
- job_id: {job_id}
- state_path: {state_path}
- project_path: {project_path}
- model: {model}
- python: {python}
- branch_name: {branch_name}
- base_branch: {base_branch}
- sast_report_path: {sast_report_path or "None"}
- threat_model_path: {threat_model_path or "None"}
- jira_id: {jira_id or "None"}
- severity_filter: {severity_filter}
- dry_run: {dry_run}
- generate_tests: {generate_tests}
- test_mode: {test_mode}

Classified findings (JSON from Stage 3):
{full_classify_output_json}

Execute Stages 4 through 9 in order.
```

**Fallback**: If the orchestrator subagent is unavailable, inform the user that the detox plugin requires the orchestrator agent and suggest checking plugin installation.

## Step 6: Report Results

After the orchestrator returns, summarize:
- Total vulnerabilities found
- Fixes applied (success/failed/skipped)
- Validation results
- Security tests generated (count, frameworks used, pass/fail status)
- DETOX_REMEDIATION_REPORT.md location (comprehensive audit report)
- MR URL (if created)
- Any items requiring manual review

## Usage Examples

### Example 1: Full Pipeline with SAST Report
```bash
/barclays-buk-detox:remediate --repo . --model opus --wiz-report ./wiz-report.json --jira DIGICAW-3667
```

### Example 2: Threat Model Only (Dry Run)
```bash
/barclays-buk-detox:remediate --repo . --model sonnet --threat-model ./threat-model.md --dry-run
```

### Example 3: Both Reports with Severity Filter
```bash
/barclays-buk-detox:remediate --repo . --model opus --wiz-report ./wiz.json --threat-model ./threat.md --severity critical+high --jira GENAIACCEL-1234
```

### Example 4: Remote Repository
```bash
/barclays-buk-detox:remediate --repo https://app.gitlab.barcapint.com/barclays/digital-dss/DSS-COMMON-CONTAINER_V4 --model sonnet --wiz-report ./report.json --jira PROJ-100 --new-branch remediate/cwe-fixes
```

### Example 5: Critical Only with Branch Options
```bash
/barclays-buk-detox:remediate --repo https://app.gitlab.barcapint.com/barclays/digital-dss/DSS-COMMON-CONTAINER_V4 --model opus --threat-model "./AttackPaths.md" --checkout-branch release/dss-aws-fw-v4-2026.01 --new-branch feature/dss-aws-fw-v4-cwe-fixes-test
```

### Example 6: Full Test Generation (Comprehensive)
```bash
/barclays-buk-detox:remediate --repo . --model opus --wiz-report ./wiz.json --jira PROJ-100 --test-mode full
```

### Example 7: Skip Test Generation
```bash
/barclays-buk-detox:remediate --repo . --model haiku --wiz-report ./wiz.json --jira PROJ-100 --no-tests
```

## Example Output

```
✅ DETOX ARGUMENTS VALIDATED
   project_path: /path/to/project
   model: opus
   sast_report: ./wiz-report.json
   threat_model: ./threat-model.md
   jira_id: DIGICAW-3667
   severity_filter: critical+high
   dry_run: false
   generate_tests: true
   test_mode: fast
   checkout_branch: not provided
   new_branch: not provided

Starting CWE remediation pipeline...

▸ Stage 0/9 — Preflight check...
  ✓ Preflight passed — semgrep v1.96.0, git v2.45.0, glab v1.40.0

▸ Stage 1/9 — Setting up repository...
  ✓ Repository ready — branch remediate-cwe-79-89-937-20260902-143000

▸ Stage 2/9 — Parsing reports...
  ✓ Wiz report — 12 findings
  ▸ Parsing threat model (LLM)...
  ✓ Threat model — 5 findings
  ✓ 15 unique findings (2 duplicates removed)

▸ Stage 3/9 — Classifying findings...
  ✓ Code: 5 | Dependency: 8 | Infra: 1 | Manual: 1 | Filtered: 0

▸ Stages 4–9 — Applying fixes, validating, generating tests, creating merge request...
  This may take several minutes. Progress will appear when stages complete.
  [orchestrator applies fixes, validates, generates tests, creates report and MR]

REMEDIATION SUMMARY
═════════════════════════════════════════
Total vulnerabilities: 17
Fixed: 12
Manual review: 3
Deferred (low severity): 2

DETOX_REMEDIATION_REPORT.md generated
   Location: ./DETOX_REMEDIATION_REPORT.md
   Contains: Full audit trail, fix details, CWE mappings

Merge request: https://app.gitlab.barcapint.com/barclays/project/-/merge_requests/43
```

## Error Messages

### Missing --repo Flag
```
❌ VALIDATION FAILED: --repo is required

Usage: /barclays-buk-detox:remediate --repo PATH --model MODEL [--wiz-report PATH] [--threat-model PATH] [--jira JIRA_ID] [--severity LEVEL] [--dry-run]
```

### Missing --model Flag
```
❌ VALIDATION FAILED: --model is required

Must be one of: sonnet, opus, haiku

Usage: /barclays-buk-detox:remediate --repo PATH --model MODEL [--wiz-report PATH] [--threat-model PATH] [--jira JIRA_ID] [--severity LEVEL] [--dry-run]
```

### Missing Reports
```
❌ VALIDATION FAILED: No vulnerability report provided

At least one of --wiz-report or --threat-model is required.

Usage: /barclays-buk-detox:remediate --repo PATH --model MODEL [--wiz-report PATH] [--threat-model PATH] [--jira JIRA_ID] [--severity LEVEL] [--dry-run]
```

### Python 3 Not Found
```
❌ VALIDATION FAILED: Python 3 is required but was not found

Checked: python3, py -3, python

Detox runs its pipeline scripts with Python 3 and does not install it for you.
Install Python 3 (https://www.python.org/downloads/), make sure it is on PATH,
then re-run /barclays-buk-detox:remediate.
```

### Invalid Project Path
```
❌ VALIDATION FAILED: Invalid --repo value

Path: {provided_path}
Error: {specific error}

Requirements:
  - Must be "." (current dir), absolute path, or git URL
  - Local directories must exist
```
