---
description: Migrate an MCA1 (scp-eps-java-common) application to MCA2 (mca-java-common) using aggressive strategy
argument-hint: [project_path] [--target=PATH] [--plan-only] [--phase=N]
user_invocable: true
---

You are the main Claude Code agent.

When the user runs `/migrate-mca1-to-mca2`, they want to **fully migrate an MCA1 application to MCA2** using the aggressive strategy (replace ALL MCA1 patterns with MCA2 equivalents).

## Step 1: Parse Arguments

Extract the following from the user's arguments:

- `project_path` (required): Path to the MCA1 project root. Must be `.` (current directory) or an absolute path containing `build.gradle` and `src/main/java`.
- `--target=PATH` (optional): Destination path. If provided, the source project is copied to this path first, and the migration runs on the copy. The original project remains untouched. The target directory must not already exist.
- `--plan-only` (optional): Generate migration plan without executing changes.
- `--phase=N` (optional): Execute only phase N (1-14).

If no path argument is provided, default to `.` (current working directory).

## Step 2: Validate Arguments (MANDATORY)

Before delegating, validate:

1. **project_path exists**: The directory must exist
2. **Contains build.gradle**: Must be a Gradle project
3. **Contains src/main/java**: Must have Java source files
4. **Is an MCA1 project**: Must contain at least one of:
   - `scp-eps-core-comm` in build.gradle or dependencies.gradle
   - `@ImportResource` in a Java source file
   - `EpsServiceAbstractController` in a Java source file
   - `EpsServiceHelper` in a Java source file
   - `EpsAbstractService` in a Java source file
   - `com.barclays.scp.eps` package references

If validation fails, show the error and stop:

```
VALIDATION FAILED: Not an MCA1 project

Path: {project_path}
Error: Could not detect MCA1 framework patterns.

Expected at least one of:
  - scp-eps-core-comm dependency in build.gradle
  - @ImportResource annotation in Java sources
  - EpsServiceAbstractController usage
  - EpsServiceHelper usage
  - EpsAbstractService usage
  - com.barclays.scp.eps package references

Ensure this is an MCA1 (scp-eps-java-common) application.
```

## Step 2b: Copy to Target (if --target specified)

If `--target=PATH` was provided:

1. **Check target does not already exist**: If the target directory exists, show error and stop:
   ```
   TARGET ERROR: Directory already exists: {target_path}
   Remove it first or choose a different target path.
   ```
2. **Copy the project**: Run `cp -r {project_path} {target_path}`
3. **Update project_path**: From this point forward, use `target_path` as the `project_path` for all subsequent steps. The migration will run on the copy.
4. **Report**:
   ```
   Project copied: {original_path} → {target_path}
   Migration will run on the copy. Original project is untouched.
   ```

## Step 3: Locate Plugin Path

Before delegating, find the plugin's installation directory so the agent can locate its reference documents:

1. Use Glob to search for `**/skills/mca1-to-mca2-eps/SKILL.md`
2. Extract the plugin root path (parent of `skills/`)
3. Store this as `plugin_path`

If not found, try `**/mca1-to-mca2-eps/skills/**/SKILL.md`.

If still not found, warn the user: "Cannot locate plugin reference files. The agent will attempt to find them at runtime."

## Step 3b: Initialize Logging

Set up the log directory and rotate old logs:

```bash
mkdir -p {project_path}/logs
# Rotate existing log if present
if [ -f "{project_path}/logs/mca1-to-mca2.log" ]; then
  mv "{project_path}/logs/mca1-to-mca2.log" "{project_path}/logs/mca1-to-mca2.$(date +%Y%m%d%H%M%S).log"
fi
```

## Step 4: Report Validation Results

```
MCA1 Project Detected

Project: {project_path}
Plugin:  {plugin_path}
Build:   Gradle
Source:   {count} Java files in src/main/java

Starting migration analysis (aggressive strategy)...
```

## Step 5: Validate --phase flag

If `--phase=N` is specified, validate that N is between 1 and 14. Phase 0 (DevOps) runs automatically and cannot be targeted individually via this command.

If N is outside 1-14, show error:
```
Invalid phase: {N}. Valid range is 1-14.
```

## Step 5b: Present Migration Plan (MANDATORY — before delegation)

Before delegating to the agent, present a comprehensive migration plan to the user. This gives visibility into what will happen and allows the user to confirm before proceeding.

### Gather Project Profile

Run these detection scans on `{project_path}`:

```bash
# Controllers
grep -rn "extends EpsServiceAbstractController" src/main/java --include="*.java"

# Services
grep -rn "extends EpsAbstractService" src/main/java --include="*.java"

# Helpers (classes with ServiceManager or ReferenceDataHelper usage)
grep -rln "ServiceManager\|ReferenceDataHelper" src/main/java --include="*.java" | grep -v Controller | grep -v Service

# Filters
grep -rn "FilterRegistrationBean\|extends.*Filter" src/main/java --include="*.java"

# XML configs
find src/main/resources -name "*.xml" -not -path "*/META-INF/*" 2>/dev/null

# ServiceManager call patterns
grep -rn "ServiceManager\|doService" src/main/java --include="*.java"

# Test files
find src/test/java -name "*.java" 2>/dev/null | wc -l

# DataSource beans
grep -rn "HikariDataSource\|DataSource" src/main/java --include="*.java" | wc -l
```

### Present Plan

Output a formatted plan like this:

```
## MCA1 to MCA2 Migration Plan: {project_name}

### Context

The user wants to fully migrate the {project_name} MCA1 application to MCA2 using the
aggressive strategy. The source project will be copied to a target directory first
(preserving the original), then the migration agent will execute the 14-phase transformation.

- Source: {original_path}
- Target: {target_path}
- Plugin: {plugin_path}

### Validation Results (Confirmed)

- build.gradle exists
- src/main/java exists ({count} Java files)
- MCA1 patterns detected: {patterns found}
- Target directory: {status}

### Project Profile

| Attribute | Value |
|-----------|-------|
| Domains | {count} ({list of controllers}) |
| Controllers | {count} ({list — extends EpsServiceAbstractController}) |
| Services | {count} ({list — extends EpsAbstractService}) |
| Helpers | {count} ({list — ServiceManager/ReferenceDataHelper users}) |
| Filters | {count} (app-owned + framework) |
| DB Sources | {count} HikariDataSource beans |
| Tests | {count} test classes |
| XML Configs | {count} ({list}) |
| ServiceManager calls | {pattern descriptions} |

### Execution Steps

| Phase | Action | Key Files Affected |
|-------|--------|--------------------|
| 0 | DevOps plugin migration | build.gradle, gradle/ |
| 1 | Build system (deps swap) | build.gradle |
| 2 | Application bootstrap | Application.java + ApplicationConfig.java |
| 3 | XML to Java config | Delete XML files, update properties |
| 4 | Controllers | {controller} → MCA2 controller |
| 5 | Services | Remove EpsAbstractService, preserve business logic |
| 6 | Context & Headers | EpsServiceHelper → contextProvider |
| 7 | REST Clients (GATED) | ServiceManager → RestClient/MisClient (user choice) |
| 8 | Exception Handling | EpsApplicationException → ApplicationException |
| 9 | Helpers & Utilities | LogHelper → SLF4J |
| 10 | Filter Chain | Remove framework filters |
| 11 | Testing (GATED) | Rewrite tests (user choice) |
| 12 | OAS3 Specification | Generate openapi.yaml |
| 13 | Process.json | Update journey definitions |
| 14 | Package rename (GATED) | com.barclays.scp.eps → com.barclays.mca.eps (user choice) |

### Verification

After migration completes:
1. ./gradlew clean build passes on the target project
2. No MCA1 remnants: grep -r "EpsService\|EpsAbstract\|@ImportResource" src/ returns empty
3. All tests pass with adequate coverage
4. OAS3 spec generated
5. Original project at source path remains untouched
```

### Ask Confirmation

After presenting the plan, call `AskUserQuestion`:
- question: "Proceed with the migration?"
- header: "Confirm"
- multiSelect: false
- options:
  1. label: "Proceed with all phases (Recommended)", description: "Execute the full 14-phase migration with gates at Phases 7, 11, and 14"
  2. label: "Plan only — stop here", description: "Do not execute changes. Plan has been presented."

If user chooses "Plan only", stop here and do NOT proceed to Step 6.
If `--plan-only` was specified, skip this question and stop after presenting the plan.

## Step 6: Phase-Bounded Delegation (Orchestrator-Controlled Gates)

The migration is executed in **5 bounded segments**. You (the orchestrator) physically control the flow — the agent is NEVER given permission to cross a gated phase boundary. Between segments, YOU call `AskUserQuestion` directly.

**Why this approach:** Subagents cannot reliably call `AskUserQuestion` (the tool doesn't surface to the user from within a subagent). Instructing the agent to "stop" at certain phases is unreliable. Instead, we NEVER tell the agent about phases beyond its current segment.

### Segment 1: Phase 0 + Pre-Migration Analysis + Phases 1-6

Launch the `mca1-to-mca2-eps-agent` subagent:

```
subagent_type: mca1-to-mca2-eps:mca1-to-mca2-eps-agent

prompt:
Migrate MCA1 application to MCA2 using aggressive strategy (replace ALL MCA1 patterns).

Plugin path: {plugin_path}
Project path: {project_path}
Target: {target_path if --target was used, otherwise "in-place"}

SCOPE FOR THIS INVOCATION: Execute Phase 0 (DevOps), Pre-Migration Analysis, and Phases 1 through 6 ONLY.

HARD STOP: After Phase 6 completes, STOP. Do NOT start Phase 7. Do NOT proceed beyond Phase 6. Your job ends when Phase 6 is done and verified with ./gradlew compileJava.

Report what was completed and any issues found.
```

After this segment returns, display the agent's progress summary to the user.

### Gate 1: Phase 7 — REST Client Strategy

After Segment 1 completes, call `AskUserQuestion` with:
- question: "Which REST client replacement strategy should I use for migrating ServiceManager.doService() calls?"
- header: "REST strategy"
- multiSelect: false
- options:
  1. label: "RestClient.callRest() for all (Recommended)", description: "MCA2 framework-level replacement for all call sites"
  2. label: "MisClient for EBS, RestClient for REST", description: "Use MisClient for EBS backend calls, RestClient for REST API calls"
  3. label: "Let me choose per call site", description: "You pick individually for each call site"

Store the user's answer as `phase7_choice`.

### Segment 2: Phase 7B through Phase 10

**Resume** the agent (using its agent ID from Segment 1):

```
resume: {agent_id from Segment 1}

prompt:
The user chose REST strategy: "{phase7_choice}".

SCOPE FOR THIS INVOCATION: Execute Phase 7B (using the user's chosen strategy), then continue with Phases 8, 9, and 10 ONLY.

HARD STOP: After Phase 10 completes, STOP. Do NOT start Phase 11. Do NOT proceed beyond Phase 10. Your job ends when Phase 10 is done and verified with ./gradlew compileJava.

Report what was completed and any issues found.
```

### Gate 2: Phase 11 — Testing

After Segment 2 completes, call `AskUserQuestion` with:
- question: "Should I migrate and write tests now, or skip testing for this run?"
- header: "Testing"
- multiSelect: false
- options:
  1. label: "Write tests now (Recommended)", description: "Migrate existing tests, write new tests, and achieve coverage gate"
  2. label: "Skip for now", description: "Defer test migration — existing tests may break but code migration is complete"

Store the user's answer as `phase11_choice`.

### Segment 3: Phase 11B through Phase 13

**Resume** the agent:

```
resume: {agent_id}

prompt:
The user chose testing: "{phase11_choice}".

SCOPE FOR THIS INVOCATION: Execute Phase 11B (using the user's choice), then continue with Phases 12 and 13 ONLY.

HARD STOP: After Phase 13 completes, STOP. Do NOT start Phase 14. Do NOT proceed beyond Phase 13. Your job ends when Phase 13 is done and verified.

Report what was completed and any issues found.
```

### Gate 3: Phase 14 — Package Rename

After Segment 3 completes, call `AskUserQuestion` with:
- question: "Should I rename packages from com.barclays.scp.eps.* to com.barclays.mca.eps.*?"
- header: "Pkg rename"
- multiSelect: false
- options:
  1. label: "Rename now (Recommended)", description: "Rename all com.barclays.scp.eps.* packages to com.barclays.mca.eps.* in all source files and move to new directories"
  2. label: "Keep existing", description: "Keep com.barclays.scp.eps.* package names — defer rename to a later stage"

Store the user's answer as `phase14_choice`.

### Segment 4: Phase 14B + Final Validation + Tech Debt Report

**Resume** the agent:

```
resume: {agent_id}

prompt:
The user chose package rename: "{phase14_choice}".

SCOPE FOR THIS INVOCATION: Execute Phase 14B (using the user's choice), then run Final Validation (./gradlew clean build), then generate the Tech Debt Report (write TECH-DEBT-REPORT.md).

This is the LAST segment. After Tech Debt Report is written, output the migration summary.
```

### Completion

When Segment 4 returns, display the agent's final summary to the user. The migration is complete.

### Full Flow Diagram

```
Orchestrator launches Segment 1 → agent runs Phases 0-6 → returns
Orchestrator: AskUserQuestion (Phase 7 gate) → user answers
Orchestrator resumes Segment 2 → agent runs Phases 7-10 → returns
Orchestrator: AskUserQuestion (Phase 11 gate) → user answers
Orchestrator resumes Segment 3 → agent runs Phases 11-13 → returns
Orchestrator: AskUserQuestion (Phase 14 gate) → user answers
Orchestrator resumes Segment 4 → agent runs Phase 14 + Final → returns
Orchestrator: Display final summary
```

### Handling --plan-only

If `--plan-only` is specified, launch Segment 1 with an additional flag: `--plan-only`. The agent will stop after Pre-Migration Analysis and output the plan. No gates fire. No further segments are needed.

### Handling --phase=N

If `--phase=N` is specified:
- If N is 1-6: Launch only Segment 1 with `--phase=N`
- If N is 7: Launch Segment 1 (Phases 0-6), then Gate 1, then Segment 2 with `--phase=7`
- If N is 8-10: Launch Segment 1 (Phases 0-6), then Gate 1, then Segment 2 with `--phase=N`
- If N is 11: Launch through Segment 2, then Gate 2, then Segment 3 with `--phase=11`
- If N is 12-13: Launch through Segment 2, then Gate 2, then Segment 3 with `--phase=N`
- If N is 14: Launch through Segment 3, then Gate 3, then Segment 4

## Step 7: Fallback Behavior

If the `mca1-to-mca2-eps-agent` subagent is unavailable, inform the user and stop:

```
AGENT UNAVAILABLE: mca1-to-mca2-eps-agent could not be launched.

Ensure the mca1-to-mca2-eps plugin is installed via /plugin.
The migration requires the agent — inline execution is not supported.
```

## Usage Examples

### Example 1: Full Migration of Current Directory
```bash
/migrate-mca1-to-mca2
```

### Example 2: Migrate Specific Project
```bash
/migrate-mca1-to-mca2 /Users/dev/gitlab/scp-eps-audit
```

### Example 3: Migrate to a Target Directory (Preserves Original)
```bash
/migrate-mca1-to-mca2 /Users/dev/gitlab/scp-eps-audit --target=/Users/dev/gitlab/scp-eps-audit-migrated
```

### Example 4: Plan Only (No Changes)
```bash
/migrate-mca1-to-mca2 . --plan-only
```

### Example 5: Execute Only Phase 1 (Build System)
```bash
/migrate-mca1-to-mca2 . --phase=1
```

### Example 6: Execute Only Phase 11 (Testing)
```bash
/migrate-mca1-to-mca2 ../my-mca1-service --phase=11
```

### Example 7: Execute Only Phase 12 (OAS3 Specification)
```bash
/migrate-mca1-to-mca2 . --phase=12
```

### Example 8: Execute Only Phase 13 (Process.json)
```bash
/migrate-mca1-to-mca2 . --phase=13
```
