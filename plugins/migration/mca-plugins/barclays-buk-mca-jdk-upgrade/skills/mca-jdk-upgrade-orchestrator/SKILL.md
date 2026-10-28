---
name: mca-jdk-upgrade-orchestrator
description: Shared orchestration workflow for /mca1-jdk-upgrade and /mca2-jdk-upgrade commands. Parses and validates arguments, detects build tool, handles resume detection, initialises logging, then delegates to mca-jdk-upgrade-agent.
version: 1.0.0
author: Barclays
parameters:
  required:
    - MCA_LABEL    # "MCA1" or "MCA2"
    - MCA_GROUPID  # "com.barclays.eps" or "com.barclays.global.mca"
    - MCA_TYPE     # "mca1" or "mca2"
tags: [mca1, mca2, jdk21, migration, barclays, orchestrator]
user-invocable: false
source: barclays-claude-code-plugins/plugins/mca-jdk-upgrade/skills/mca_jdk_upgrade_orchestrator/SKILL.md
owner: Barclays AI (barclaysai@barclays.com)
review-trigger: When Java/Spring Boot target versions change or new MCA project structures are identified
status: Full
---

# MCA JDK Upgrade Orchestrator

Shared orchestration workflow for both `/mca1-jdk-upgrade` and `/mca2-jdk-upgrade` commands.

**Required parameters (set by the calling command):**
- `{MCA_LABEL}` — "MCA1" or "MCA2"
- `{MCA_GROUPID}` — "com.barclays.eps" or "com.barclays.global.mca"
- `{MCA_TYPE}` — "mca1" or "mca2"

**CRITICAL: DO NOT DETECT, DERIVE, OR VALIDATE THE PROJECT TYPE.**
- The calling command already determined `{MCA_TYPE}`. It is authoritative and final.
- Do NOT read build.gradle or source files to verify the project type.
- Do NOT throw "Project Type Mismatch" errors or suggest a different command.
- **Why:** MCA2 projects commonly contain BOTH `com.barclays.global.mca` (primary) AND `com.barclays.eps` (legacy to remove) dependencies. Seeing `com.barclays.eps` in a project does NOT mean it's MCA1 — it may be a legacy dep in an MCA2 project. The migration type controls HOW dependencies are treated, not which project this is.
- Proceed directly to Step 1.

---
## Quick Start

Orchestrator skill that coordinates the full MCA JDK upgrade pipeline.

```bash
/mca2-jdk-upgrade <project_path>   # Runs full Java 8→21 / Spring Boot 2.7→3.5 upgrade
/mca1-jdk-upgrade <project_path>   # Includes EAR-to-WAR conversion phase
```


## Step 1: Parse Arguments

Parse the arguments provided after the command:

```
FORMAT: PROJECT_PATH --branch BRANCH_NAME --jira JIRA_ID [--group GROUP] [--template TEXT]

POSITIONAL:
  PROJECT_PATH     Path to project (required) - "." for current directory or absolute path

FLAGS:
  --branch NAME    Source branch to create migration branch from (required)
  --jira JIRA_ID   JIRA ticket ID (required) - e.g., GENAIACCEL-1234
                   Used for branch naming (feature/{jira_id}) and commit messages
  --group GROUP    Barclays business group (optional, default: capl)
                   Valid values are discovered dynamically from available reference files
                   Controls which group-specific library reference is loaded
  --template TEXT  Custom instructions (optional) - in quotes if contains spaces
```

**Parsing rules:**
- First non-flag argument -> `project_path`
- `--branch` followed by value -> `branch_name`
- `--jira` followed by value -> `jira_id`
- `--group` followed by value -> `group` (default: `capl` if not provided)
- `--template` followed by value -> `custom_template`
- `migration_type` is **always `{MCA_TYPE}`** (hardcoded for this command)

---

## Step 2: Validate Arguments (MANDATORY - DO NOT SKIP)

**You MUST validate ALL arguments before proceeding. If validation fails, report the error and STOP.**

### 2.1 Validate project_path

**Validation rules:**
- Path can be `.` (current directory) OR an absolute path (starts with `/`)
- If path is `.`, resolve it to the current working directory
- Directory must exist
- Must contain either `build.gradle` (Gradle) or `pom.xml` (Maven)
- Must contain `src/main/java` directory

**On failure:** Report which check failed and STOP.

### 2.2 Validate branch_name

**Validation rules:**
- Must be a non-empty string
- Must be a valid git branch name

**On failure:** Report "Invalid branch name" and STOP.

### 2.3 Validate jira_id

**Validation rules:**
- Must match regex pattern: `^[A-Z]+-[0-9]+$`
- Examples: GENAIACCEL-1234, CARDOPSAPI-5678, JIRA-999

**On failure:** Report "Invalid JIRA ID format. Expected pattern: PROJECTKEY-12345" and STOP.

### 2.4 Validate group (if provided)

**Validation rules:**
- If provided, validate group is a known value (default: `capl`). The consolidated reference file `skills/mca2_jdk_upgrade_reference/reference/mca2_migration_reference.md` contains all group library data.
- If the group is not recognized, report available groups and STOP

**On failure:** Report "Unknown group '{group}'. Available groups: {list}" and STOP.

### 2.5 Validate custom_template (if provided)
- If provided, it should be a non-empty string
- No specific format required

---

## Step 3: Detect Build Tool

- If `build.gradle` exists -> `build_tool = gradle`
- If `pom.xml` exists -> `build_tool = maven`
- If both exist -> prefer Gradle

---

## Step 4: Resume Detection

Check if a migration is already in progress by reading the state file (`.mca2-jdk-migration-state.json`):

1. Check if state file exists: `{project_path}/.mca2-jdk-migration-state.json`
2. If state file exists:
   - Read the state file to determine which phases are completed
   - Look for the last phase with `"status": "completed"`
   - Check if any phase has `"status": "in_progress"` (interrupted migration)
   - Determine the next phase to execute
3. If state file does not exist:
   - Check if branch `feature/{jira_id}` already exists
   - If branch exists WITHOUT state file, this is an error condition (manual migration or corrupted state)
   - If branch does not exist, this is a fresh migration (start from Phase 0)
4. Report resume state to user

**CRITICAL**: Phase detection MUST use the state file ONLY. Never parse commit messages or logs to determine completed phases. The state file (`.mca2-jdk-migration-state.json`) is the single source of truth for migration progress.

---

## Step 5: Initialize Logging

Create logging infrastructure in the project:

1. Create logs directory: `mkdir -p {project_path}/logs`
2. Set log file path: `{project_path}/logs/migration.log`
3. **Rotate existing log file** (if present):
   - If `migration.log` exists, rename it to `migration_{timestamp}.log`
   - Timestamp format: `YYYYMMDD_HHMMSS` (UTC)
   - Example: `logs/migration_20260222_143045.log`
4. Create new `migration.log` with header:
   ```
   === {MCA_LABEL} JDK 8->21 Migration Log ===
   Started: {timestamp}
   JIRA: {jira_id}
   Project: {project_path}
   Build Tool: {build_tool}
   Source Branch: {branch_name}
   Target Group: {group}
   Resume From: Phase {N} / Fresh start
   ========================================
   ```
5. Pass log file path to agent: `log_file = {project_path}/logs/migration.log`

**NOTE**: The agent handles log rotation internally. Old logs are preserved with timestamps for debugging.

**All subsequent operations MUST append to this log file.**

---

## Step 6: Report Validation Results

After validation passes, display:

```
{MCA_LABEL} JDK UPGRADE - Validation Passed

  Project:      {project_path}
  Build Tool:   {gradle|maven}
  Source Branch: {branch_name}
  JIRA:         {jira_id}
  Type:         {MCA_TYPE} ({MCA_GROUPID})
  Group:        {group}
  Template:     {custom_template or "not provided"}
  Resume:       {Resuming from Phase N / Fresh start}

Migration Phases:
  Phase 0: Project Analysis & Branch Setup
  Phase 1: Selective Dependency & Build Migration (switches to Java 21)
  Phase 2: Build Configuration (Java 21, Spring Boot 3.5.x from Nexus)
  Phase 2.5: Test Package Alignment
  Phase 3: javax -> jakarta Namespace Migration
  Phase 4: Java 8->21 Code Changes
  Phase 5: Apache HttpClient -> JDK HttpClient (if applicable)
  Phase 6: Test Migration (JUnit 4->5, Mockito 5) -> test-fix-agent
  Phase 7: Validation -> integration-test-agent
  Phase 8: Push & MR Creation -> push-agent

Starting {MCA_LABEL} migration...
```

---

## Step 7: Delegate to Migration Agent

Delegate the full migration work to `mca-jdk-upgrade-agent` via the Task tool:

```
Task:
  subagent_type: mca-jdk-upgrade-agent
  description: "Execute {MCA_LABEL} JDK upgrade migration"
  prompt: |
    Execute the {MCA_LABEL} JDK upgrade for the following project:

    Project Path: {project_path}
    Build Tool: {build_tool}
    Source Branch: {branch_name}
    JIRA ID: {jira_id}
    Migration Type: {MCA_TYPE}
    Group: {group}
    Log File: {log_file}
    Custom Template: {custom_template or "none"}
    Resume From Phase: {next_phase or "0"}

    Execute all phases from {next_phase} to 8 in order.

    AUTOMATION MODE: Run fully automated. Never use AskUserQuestion.
    Use auto-decision-agent for any ambiguous decisions.

    LOGGING: Append all phase actions, decisions, and results to {log_file}.
```

---

## Step 8: Handle Phase Completion

For each phase completed by the agent:

1. Update the task list (mark phase as completed)
2. Report the commit to the user
3. If a phase fails after max retries, log the failure and continue to next phase

---

## Fallback Behavior

If the `mca-jdk-upgrade-agent` subagent is unavailable, execute the migration inline using the mca2_jdk_upgrade_reference skill reference files:

0. **[MCA1 only — MANDATORY before Phase 1]** `skills/ear_to_war_conversion/SKILL.md` for Phase 0 Step 2.5 (EAR detection and structural conversion). Run this FIRST if `migration_type == mca1`. Check state file for `phases.phase_0.ear_to_war_converted` — if already set (true or false), skip. Otherwise: detect EAR structure, convert if detected, update state file.
1. `reference/nexus_version_lookup.md` for Phase 0 (Nexus version discovery)
2. `skills/mca_jdk21_migration/SKILL.md` for Phase 1 (selective migration)
3. `reference/nexus_version_lookup.md` + `reference/mca2_migration_reference.md` for Phase 2 (Build config)
4. `reference/javax_jakarta.md` for Phase 3 (Namespace migration)
5. `reference/mca2_migration_reference.md` + `reference/third_party_dependencies.md` for Phase 4 (Code changes)
6. Java 11 `java.net.http.HttpClient` API docs for Phase 5 (HttpClient migration)
7. `reference/test_migration.md` for Phase 6 (Test migration)
8. Run tests and coverage tools directly for Phase 7 (Validation)
9. `templates/pr_template.md` for Phase 8 (Push & MR)

## Agent Self-Check

- [ ] Skill loaded before the upgrade phase it governs
- [ ] Source version (Java 8 / Spring Boot 2.7) confirmed before applying upgrade patterns
- [ ] Build verified with ./gradlew clean build after each phase
- [ ] No MCA1/legacy patterns remain after migration step
- [ ] Test suite still passes after code changes
- [ ] Upgrade summary logged to migration report
