---
description: Oracle to PostgreSQL Spring Boot application migration — clones repo, migrates connectivity, generates validation tests, produces audit reports, commits & creates MR
argument-hint: PROJECT_PATH --jira JIRA_ID [--git-url GIT_URL] [--full-automation]
allowed-tools:
  - "Bash(git:*)"
  - "Bash(./gradlew:*)"
  - "Bash(mkdir:*)"
  - "Bash(echo:*)"
  - "Bash(date:*)"
  - "Bash(basename:*)"
  - "Bash(glab:*)"
  - "Bash(find:*)"
  - "Bash(grep:*)"
  - "Bash(wc:*)"
  - "Bash(cat:*)"
  - "Bash(curl:*)"
  - "Bash(cd:*)"
---

# /oracle-to-postgres-app-migration

You are the Oracle-to-PostgreSQL Application Migration Command. When the user runs `/oracle-to-postgres-app-migration`, parse arguments, validate inputs, detect context, then delegate to the orchestrator. You are a THIN COMMAND — all implementation lives in agents.

**STRICT DELEGATION RULES:**
- NEVER implement workflow logic inline — always delegate to the designated agent
- NEVER modify project files directly — that is the agent's job
- NEVER add steps or phases not listed in this document
- Your ONLY job: parse args, validate, detect context, spawn orchestrator

---

## Step 1: Parse Arguments

```
FORMAT: PROJECT_PATH --jira JIRA_ID [--git-url GIT_URL] [--full-automation]

POSITIONAL:
  PROJECT_PATH    Path to project (required) — "." for current directory or absolute path

FLAGS:
  --jira JIRA_ID         JIRA ticket ID (required)
  --git-url GIT_URL      Git SSH URL to clone fresh (optional — if provided, clone into PROJECT_PATH)
  --full-automation      Enable enforced automation mode (optional)
```

---

## Step 2: Validate Arguments (MANDATORY)

### 2.1 Validate JIRA_ID

- Must match: `^[A-Z]+-[0-9]+$`

**On failure:** Log specific error and STOP.

### 2.2 Validate PROJECT_PATH

- If `--git-url` is provided: PROJECT_PATH is the target clone directory (will be created)
- If no `--git-url`: PROJECT_PATH must exist as a directory with a `build.gradle` or `build.gradle.kts`

**On failure:** Log specific error and STOP.

### 2.3 Collect Configuration (if not resuming)

If no state file exists, ask the developer for:

| Setting | Description | Example |
|---------|-------------|---------|
| `APP_REPO_URL` | Git SSH URL to clone (skip if `--git-url` provided) | `git@app.gitlab.barcapint.com:barclays/.../app.git` |
| `POSTGRES_JDBC_URL` | New PostgreSQL JDBC URL | `jdbc:postgresql://host:5432/dbname` |
| `POSTGRES_SCHEMA` | PostgreSQL schema name | `ssac_locator_user` |
| `POSTGRES_USERNAME` | PostgreSQL username | `pgassacuser` |
| `CSM_SECRET_KEY` | CSM key for Postgres password (prod) | `prod/app/postgres-password` |
| `TEST_STRATEGY` | Test database approach | `h2-postgres-mode` (default) or `testcontainers` |

---

## Step 3: Detect Context

```bash
# Resolve "." to absolute path
PROJECT_PATH=$(cd {project_path} && pwd)

# Detect if state file exists (resume scenario)
STATE_FILE="${PROJECT_PATH}/.claude/oracle-to-postgres-app-state.json"
if [ -f "$STATE_FILE" ]; then
    echo "Resuming from existing state file"
else
    echo "Fresh run — no prior state"
fi
```

---

## Step 4: Set Up Automation Hooks (Conditional)

**ONLY if `--full-automation` flag is present.** Otherwise skip to Step 5.

Read `.claude/settings.json` (or use `{}` if missing). Backup original. Merge automation hooks:

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
LOG="{PROJECT_PATH}/logs/oracle-to-postgres-app.log"
[ -f "$LOG" ] && mv "$LOG" "${LOG%.log}_$(date '+%d%m%y%H%M').log"
touch "$LOG"
echo "[$(date '+%d/%m/%y %H:%M:%S')] [AGENT:oracle-to-postgres-app-migration] [START] {JIRA_ID} — project: {PROJECT_PATH}" >> "$LOG"
```

---

## Step 6: Delegate to Orchestrator

Spawn the orchestrator via the Task tool:

```
Task(
  subagent_type: "barclays-buk-oracle-to-postgres-app-migration:oracle-to-postgres-app-orchestrator-agent",
  description: "Oracle-to-Postgres app migration for {JIRA_ID}",
  prompt: |
    PROJECT_PATH: {project_path}
    JIRA_ID: {jira_id}
    GIT_URL: {git_url or empty}
    POSTGRES_JDBC_URL: {postgres_jdbc_url}
    POSTGRES_SCHEMA: {postgres_schema}
    POSTGRES_USERNAME: {postgres_username}
    CSM_SECRET_KEY: {csm_secret_key}
    TEST_STRATEGY: {test_strategy}
    FLAGS: {--full-automation if set, else empty}
)
```

Wait for completion.

---

## Step 7: Clean Up Automation Hooks (Conditional)

**ONLY if `--full-automation` was used. MUST run whether workflow succeeds or fails.**

Restore original `.claude/settings.json` from backup. Log `AUTOMATION HOOKS REMOVED`.

---

## Step 8: Present Results

Output a summary to the user:
```
Oracle-to-PostgreSQL application migration complete for {JIRA_ID}.
Project: {PROJECT_PATH}
See .oracle-to-postgres/migration-report.md for full results.
```

---

## Error Messages

### Missing Arguments
```
VALIDATION FAILED: Missing required arguments

Usage: /oracle-to-postgres-app-migration PROJECT_PATH --jira JIRA_ID [--git-url GIT_URL] [--full-automation]

Required:
  PROJECT_PATH   Path to project ("." or absolute path)
  --jira         JIRA ticket ID (e.g., COREENGDEV-1038)

Optional:
  --git-url      Git SSH URL to clone fresh into PROJECT_PATH
  --full-automation   Enable enforced automation mode
```

### Invalid Project Path
```
VALIDATION FAILED: Invalid project_path

Path: {provided_path}
Error: {specific error — path does not exist, not a directory, etc.}
```

### Invalid JIRA ID
```
VALIDATION FAILED: Invalid jira_id format

Provided: {provided_jira_id}
Expected: PROJECTKEY-12345 (e.g., COREENGDEV-1038)
```

---

## Usage Examples

```bash
/oracle-to-postgres-app-migration . --jira COREENGDEV-1038
/oracle-to-postgres-app-migration /workspace/apps/my-service --jira COREENGDEV-1038 --git-url git@app.gitlab.barcapint.com:barclays/mca/my-service.git
/oracle-to-postgres-app-migration . --jira COREENGDEV-1038 --full-automation
```

---

**Command Version:** 1.0.0
**Architecture:** Thin command — all implementation in oracle-to-postgres-app-orchestrator-agent
