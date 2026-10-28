---
description: Autonomously migrate MCA1 UI projects to MCA2 with Blueprint-React and functional component patterns
argument-hint: PROJECT_PATH [--jira JIRA_ID] [--eps-repo "<url>"] [--template-repo "<url>"] [--additional-input "<instructions>"] [--full-automation] [--regression-repo "<url>"]
---

You are the MCA1 Migration Command. When the user runs `/mca-ui-migrate`, parse arguments, validate inputs, detect context, then delegate to the orchestrator. You are a THIN ORCHESTRATOR — all implementation lives in agents.

**STRICT DELEGATION RULES:**
- NEVER implement workflow logic inline — always delegate to the designated agent
- NEVER modify project files directly — that is the agent's job
- NEVER add steps or phases not listed in this document
- Your ONLY job: parse args, validate, detect context, spawn orchestrator

---

## Step 1: Parse Arguments

```
FORMAT: PROJECT_PATH [--jira JIRA_ID] [--eps-repo "<url>"] [--template-repo "<url>"] [--additional-input "<instructions>"] [--full-automation] [--regression-repo "<url>"]

POSITIONAL:
  PROJECT_PATH    Path to MCA1 project being migrated (required) — "." for current directory or absolute path

FLAGS:
  --jira JIRA_ID              JIRA ticket ID (optional — used for logging and branch naming)
  --eps-repo "<url>"          Git clone URL for the EPS backend repository (optional — used for API contract verification)
  --template-repo "<url>"     Git clone URL for team's custom MCA2 template repository (optional — overrides default migration patterns with template conventions)
  --additional-input "<text>" Free-text instructions to pass to orchestrator (optional)
  --full-automation           Enable enforced automation mode — blocks AskUserQuestion (optional)
  --regression-repo "<url>"   Git clone URL for regression test scripts repository (optional)
```

---

## Step 2: Validate Arguments (MANDATORY)

### 2.1 Validate PROJECT_PATH

- Path can be `.` (resolve to cwd) or absolute
- Must exist as a directory
- Should contain a `package.json` (warn if absent, but do not block)

**On failure:** Log specific error and STOP.

### 2.2 Validate JIRA_ID (if provided)

- If `--jira` is provided, validate format: must match `^[A-Z]+-[0-9]+$`
- Examples of valid IDs: `MCAUI-1234`, `MCA-567`, `GENAIACCEL-999`
- If `--jira` is NOT provided, skip this step — JIRA ID is optional

**On failure (when provided with invalid format):** Log specific error and STOP.

### 2.3 Validate EPS_REPO (if provided)

- If `--eps-repo` is provided, validate the URL format
- Must match a git URL pattern: HTTPS (`https://...`) or SSH (`git@...`)
- This is the backend/EPS repository for API contract verification

**On failure:** Log specific error and STOP.

### 2.4 Validate REGRESSION_REPO (if provided)

- If `--regression-repo` is provided, validate the URL format
- Must match a git URL pattern: HTTPS (`https://...`) or SSH (`git@...`)
- Examples of valid URLs: `https://gitlab.barclays.internal/team/regression-tests.git`, `git@app.gitlab.barcapint.com:team/regression-tests.git`

**On failure:** Log specific error and STOP.

### 2.5 Validate TEMPLATE_REPO (if provided)

- If `--template-repo` is provided, validate the URL format
- Must match a git URL pattern: HTTPS (`https://...`) or SSH (`git@...`)
- Examples of valid URLs: `https://gitlab.barclays.internal/team/mca2-template.git`, `git@app.gitlab.barcapint.com:team/custom-mca2-template.git`

**On failure:** Log specific error and STOP.

---

## Step 3: Detect Context

```bash
# Resolve "." to absolute path
PROJECT_PATH=$(cd {project_path} && pwd)

# Detect if state file exists (resume scenario)
STATE_FILE="${PROJECT_PATH}/.claude/mca1-ui-mca2-migration-state.json"
if [ -f "$STATE_FILE" ]; then
    echo "Resuming from existing state file — prior migration run detected"
else
    echo "Fresh run — no prior state"
fi

# Detect if this looks like an MCA1 project
if [ -f "${PROJECT_PATH}/package.json" ]; then
    echo "package.json found"
else
    echo "WARNING: No package.json found at ${PROJECT_PATH} — verify this is the correct MCA1 project root"
fi
```

---

## Step 4: Set Up Automation Hooks (Conditional)

**ONLY if `--full-automation` flag is present.** Otherwise skip to Step 5.

Read `{PROJECT_PATH}/.claude/settings.json` (or use `{}` if missing). Backup original as `settings.json.bak`. Merge automation hooks:

```json
{
  "hooks": {
    "PreToolUse": [{ "matcher": "AskUserQuestion", "hooks": [{ "type": "command", "command": "echo '{\"hookSpecificOutput\":{\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"AskUserQuestion is BLOCKED in FULL AUTOMATION MODE. Make the best autonomous decision and continue.\"}}' >&2; exit 2", "timeout": 5 }] }],
    "Stop": [{ "hooks": [{ "type": "prompt", "prompt": "Check if the assistant's last response indicates incomplete work. If incomplete, respond with {\"ok\": false, \"reason\": \"Work is incomplete. Continue executing the remaining tasks autonomously.\"}. If genuinely complete, respond with {\"ok\": true}.", "model": "haiku", "timeout": 15 }] }]
  }
}
```

Write updated settings. Log `AUTOMATION HOOKS INSTALLED`.

---

## Step 5: Initialize Log

```bash
mkdir -p "{PROJECT_PATH}/logs"
LOG="{PROJECT_PATH}/logs/mca1-ui-mca2-migration.log"
[ -f "$LOG" ] && mv "$LOG" "${LOG%.log}_$(date '+%d%m%y%H%M').log"
touch "$LOG"
echo "[$(date '+%d/%m/%y %H:%M:%S')] [COMMAND:mca1-migration] [START] {JIRA_ID or 'no-jira'} — project: {PROJECT_PATH}" >> "$LOG"
```

---

## Step 6: Determine Plugin Directory and Delegate to Orchestrator

Establish PLUGIN_DIR using the best available method:

```bash
# Try to resolve plugin directory
PLUGIN_DIR="${CLAUDE_PLUGIN_ROOT}"

# If CLAUDE_PLUGIN_ROOT is not set, use the current context
if [ -z "$PLUGIN_DIR" ]; then
    # The plugin directory is typically where this command file lives
    # This is a fallback for cases where CLAUDE_PLUGIN_ROOT is unavailable
    PLUGIN_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
fi

echo "Plugin dir for spawned agents: ${PLUGIN_DIR}"
```

Spawn the orchestrator via the Task tool:

```
Task(
  subagent_type: "mca1-ui-mca2-migration:mca1-orchestrator-agent",
  description: "MCA1→MCA2 UI migration workflow{' for ' + JIRA_ID if provided}",
  prompt: |
    PROJECT_PATH: {project_path}
    JIRA_ID: {jira_id or "none"}
    PLUGIN_DIR: {PLUGIN_DIR}
    EPS_REPO: {eps_repo or "none"}
    TEMPLATE_REPO: {template_repo or "none"}
    ADDITIONAL_INPUT: {additional_input or "none"}
    FLAGS: {--full-automation if set, else empty}
    REGRESSION_REPO: {regression_repo or "none"}
)
```

**CRITICAL:** `PLUGIN_DIR: {PLUGIN_DIR}` MUST be included in the prompt so the orchestrator and all spawned agents can access skill files.

Wait for completion.

---

## Step 7: Clean Up Automation Hooks (Conditional)

**ONLY if `--full-automation` was used. MUST run whether workflow succeeds or fails.**

Restore original `.claude/settings.json` from backup. Log `AUTOMATION HOOKS REMOVED`.

---

## Error Messages

### Missing Arguments
```
VALIDATION FAILED: Missing required arguments

Usage: /mca-ui-migrate PROJECT_PATH [--jira JIRA_ID] [--eps-repo "<url>"] [--template-repo "<url>"] [--additional-input "<instructions>"] [--full-automation] [--regression-repo "<url>"]

Required:
  PROJECT_PATH   Path to MCA1 project ("." or absolute path)

Optional:
  --jira         JIRA ticket ID (e.g., MCAUI-1234) — used for logging and branch naming
  --eps-repo     EPS backend repository URL — for API contract verification
  --template-repo  Team's custom MCA2 template repository URL — overrides default patterns
  --additional-input "<text>"   Extra guidance for the migration agents
  --full-automation             Enable enforced automation mode
  --regression-repo  Regression test scripts repository URL — for E2E test generation
```

### Invalid Project Path
```
VALIDATION FAILED: Invalid project_path

Path: {provided_path}
Error: {specific error — path does not exist, not a directory, etc.}
```

### Invalid JIRA ID (only shown when --jira is provided with invalid format)
```
VALIDATION FAILED: Invalid jira_id format

Provided: {provided_jira_id}
Expected: PROJECTKEY-12345 (e.g., MCAUI-1234)
```

### Invalid EPS Repo URL
```
VALIDATION FAILED: Invalid EPS repo URL

Provided: {provided_url}
Expected: A valid git clone URL (HTTPS or SSH)
Examples:
  https://gitlab.barclays.internal/team/my-app-eps.git
  git@app.gitlab.barcapint.com:team/my-app-eps.git
```

### Invalid Regression Repo URL
```
VALIDATION FAILED: Invalid regression repo URL

Provided: {provided_url}
Expected: A valid git clone URL (HTTPS or SSH)
Examples:
  https://gitlab.barclays.internal/team/regression-tests.git
  git@app.gitlab.barcapint.com:team/regression-tests.git
```

### Invalid Template Repo URL
```
VALIDATION FAILED: Invalid template repo URL

Provided: {provided_url}
Expected: A valid git clone URL (HTTPS or SSH)
Examples:
  https://gitlab.barclays.internal/team/mca2-template.git
  git@app.gitlab.barcapint.com:team/custom-mca2-template.git
```

---

## Usage Examples

```bash
/mca-ui-migrate .
/mca-ui-migrate /path/to/mca1-project
/mca-ui-migrate . --jira MCAUI-1234
/mca-ui-migrate /path/to/mca1-project --eps-repo "git@app.gitlab.barcapint.com:team/my-app-eps.git"
/mca-ui-migrate /path/to/mca1-project --jira MCAUI-2388 --full-automation
/mca-ui-migrate /path/to/mca1-project --jira MCAUI-2388 --eps-repo "https://gitlab.barclays.internal/team/my-app-eps.git" --regression-repo "https://gitlab.barclays.internal/team/regression-tests.git"
/mca-ui-migrate /path/to/mca1-project --jira MCAUI-2388 --full-automation --regression-repo "git@app.gitlab.barcapint.com:team/regression-tests.git"
/mca-ui-migrate /path/to/mca1-project --jira MCAUI-2388 --template-repo "https://gitlab.barclays.internal/team/custom-mca2-template.git"
/mca-ui-migrate /path/to/mca1-project --jira MCAUI-2388 --template-repo "git@app.gitlab.barcapint.com:team/mca2-template.git" --regression-repo "https://gitlab.barclays.internal/team/regression-tests.git"
```

---

**Command Version:** 1.0.0
**Architecture:** Thin command — all implementation in mca1-orchestrator-agent
