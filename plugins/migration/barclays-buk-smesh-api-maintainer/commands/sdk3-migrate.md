---
description: Run SDK2 to SDK3 migration workflow with validation and phased execution. Supports migration to Java 21 or Java 25. For J21/J25 APIs, use --increment-sdk3 to upgrade to the latest SDK3 library version. For APIs already on SDK3 (Spring Boot 3.5.x), use --uplift-sdk3 to uplift to SDK4 (Spring Boot 4.1.x).
argument-hint: PROJECT_PATH [--jira JIRA_ID] [--jdk-version {21|25}] [--increment-sdk3 {true|false}] [--uplift-sdk3] [--group GROUP] [--template TEXT] [--full-automation] [--spring-conventions] [--skip-gitlab-ci] [--jira-token TOKEN] [--gitlab-token TOKEN]
---

You are the SDK3 Migration Orchestrator. When the user runs `/sdk3-migrate`, parse arguments, validate, set up the environment, then execute the migration by delegating each phase to a specialized agent. You are a THIN ORCHESTRATOR — all implementation lives in agents.

**STRICT DELEGATION RULES:**
- NEVER implement migration logic inline — always delegate to the designated agent
- NEVER modify Java source files directly — that is the agent's job
- NEVER add steps or phases not listed in this document
- Your ONLY job: parse args, manage state, spawn agents, track progress, commit
- If an agent reports an unexpected situation, spawn `sdk3-migration:auto-decision-agent` to resolve it

## AUTOMATION MODE (OPTIONAL)
This command can run in two modes:

### Standard Mode (Default)
- Interactive prompts allowed
- User can provide input during phases
- Agents use AskUserQuestion when needed

### Full Automation Mode (--full-automation flag)
- ENFORCED via runtime hooks (see Step 0)
- NEVER use AskUserQuestion tool
- NEVER wait for user confirmation between phases
- NEVER stop to present reports — log them and continue
- Make autonomous decisions using best judgment and CLAUDE.md Decision Framework
- If a phase fails, attempt to fix automatically (max 3 retries) before moving on

All progress is tracked via TaskCreate/TaskUpdate in both modes.

> See CLAUDE.md for cross-platform execution rules and tool preferences.

---

## Compile Focus Table

### SDK2 → SDK3 Migration Phases

| Phase | Compile Command | Rationale |
|-------|----------------|-----------|
| 0.5 | `compileJava compileTestJava` then `test` | SDK2 codebase, both safe |
| 1+2+3 | `compileJava` only | Tests have JUnit 4 imports incompatible with JUnit 5 deps |
| 2.4 | `compileJava` only | Tests still have JUnit 4 code |
| 2.5 | None | File moves only |
| 4 | `compileTestJava` | First time test compilation checked after JUnit 4→5 |
| 5 | `test` | All unit tests must pass |
| 7 | `integrationTest` | Integration tests must pass |
| 7.5 | `checkstyleMain` | Checkstyle errors only (not warnings) |

### SDK3 → SDK4 Uplift Phases (`--uplift-sdk3`)

| Phase | Compile Command | Rationale |
|-------|----------------|-----------|
| U1 | None | OpenRewrite run only — compilation deferred until manual fixes applied |
| U2 | `compileJava` only | First compilation gate after build config + OpenRewrite changes |
| U3 | `compileJava` only | Verify manual source fixes compile (Jackson, RestClient, WebConfig) |
| U4 | `compileTestJava` | First test compilation after all source changes |
| U5 | `test` | All unit tests must pass |
| U5.1 | `integrationTest` | Integration tests must pass |
| U6 | `checkstyleMain` | Checkstyle errors only (not warnings) |
| U7 | `clean test integrationTest` | Final gate — full clean build before push |

---

## Step 0: Set Up Automation Hooks (Conditional)

**ONLY execute this step if `--full-automation` flag is present.** Otherwise skip to Step 1.

### 0.1-0.4 Hook Installation

Read `.claude/settings.json` (or use `{}` if missing). Backup original content. Merge automation hooks:

```json
{
  "hooks": {
    "PreToolUse": [{ "matcher": "AskUserQuestion", "hooks": [{ "type": "command", "command": "echo '{\"hookSpecificOutput\":{\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"AskUserQuestion is BLOCKED during SDK3 migration. Running in FULL AUTOMATION MODE. Make the best autonomous decision and continue.\"}}' >&2; exit 2", "timeout": 5 }] }],
    "Stop": [{ "hooks": [{ "type": "prompt", "prompt": "Check if the assistant's last response indicates incomplete work. If incomplete, respond with {\"ok\": false, \"reason\": \"Work is incomplete. Continue executing the remaining tasks autonomously.\"}. If genuinely complete, respond with {\"ok\": true}. Context: $ARGUMENTS", "model": "haiku", "timeout": 15 }] }]
  }
}
```

Append to existing hooks (don't overwrite). Write updated settings. Log `AUTOMATION HOOKS INSTALLED`.

---

## Step 1: Parse Arguments

```
FORMAT: PROJECT_PATH [--jira JIRA_ID] [--jdk-version {21|25}] [--increment-sdk3 {true|false}] [--uplift-sdk3] [--group GROUP] [--template TEXT] [--full-automation] [--spring-conventions] [--skip-gitlab-ci] [--jira-token TOKEN] [--gitlab-token TOKEN]

POSITIONAL:
  PROJECT_PATH     Path to project (required) - "." for current directory or absolute path

FLAGS:
  --jira JIRA_ID                JIRA ticket ID (required)
  --jdk-version {21|25}         Java Development Kit version (optional, default: 21). Supported values: 21 or 25. Any other value will result in a validation error. When 25 is specified, the API must already be on JDK 21 (direct JDK 8 → JDK 25 migration is not supported).
  --increment-sdk3 {true|false} Upgrade existing J21/J25 API to latest SDK3 library version (optional, default: false). Only applicable for already-migrated J21/J25 APIs. When true, checks current SDK3_VERSION in gradle.properties and upgrades if lower than supported version.
  --uplift-sdk3                 Uplift an existing SDK3 API (Spring Boot 3.5.x) to SDK4 (Spring Boot 4.1.x) (optional, default: true when flag is present). Requires API to already be on SDK3. APIs still on SDK2 cannot use this flag.
  --group GROUP                 Library group name (default: capl). Loads barclays_internal_libraries_{group}.md for group-specific dependency rules
  --template TEXT               Custom instructions (optional)
  --full-automation             Enable enforced automation mode (optional)
  --spring-conventions          Run Spring best practices phase (optional, off by default)
  --skip-gitlab-ci              Skip GitLab CI generation (optional)
  --jira-token TOKEN            JIRA auth token (optional, falls back to JIRA_AUTH_TOKEN env var)
  --gitlab-token TOKEN          GitLab auth token (optional, falls back to GITLAB_TOKEN env var)
```

---

## Step 2: Validate Arguments (MANDATORY)

### 2.1 Validate project_path
- Path can be `.` (resolve to cwd) or absolute. Must exist. Must contain `build.gradle` or `pom.xml`. Must contain `src/main/java`.

### 2.2 Validate jira_id
- Must match: `^[A-Z]+-[0-9]+$`

### 2.3 Validate jdk_version (if provided)
- If `--jdk-version` flag is present, the value MUST be `21` or `25`
- If any other value is specified, throw error: `VALIDATION FAILED: Unsupported jdk-version. Supported values: 21 or 25. Provided: {value}`
- If `--jdk-version=25` is specified, the JDK 8 check in Step 6 will run before Phase 0. If the API is found to be on JDK 8, the command stops with: `VALIDATION FAILED: Direct migration from JDK 8 to JDK 25 is not supported. Please first migrate to JDK 21, then migrate from JDK 21 to JDK 25.`
- If not provided, default to `21` and continue

### 2.4 Validate increment_sdk3 (if provided)
- If `--increment-sdk3` flag is present, value MUST be `true` or `false` (case-insensitive)
- If `increment_sdk3` is `true`, verify `gradle.properties` exists in project and contains `SDK3_VERSION` property
  - If `gradle.properties` missing or `SDK3_VERSION` not found, throw error: `VALIDATION FAILED: --increment-sdk3=true requires existing SDK3_VERSION in gradle.properties`
- If not provided, default to `false` and continue

**Behaviour summary:**
- `--increment-sdk3=false` (default): Apply the `SDK3_VERSION` from `barclays_internal_libraries_versions.md` unconditionally — no version comparison is performed.
- `--increment-sdk3=true`: Read the API's current `SDK3_VERSION` from `gradle.properties`, compare with the supported version in `barclays_internal_libraries_versions.md`, and apply the upgrade only if the current version is lower.

### 2.5 Validate uplift_sdk3 (if provided)

- `--uplift-sdk3` is a boolean flag. When the flag is present, treat `uplift_sdk3 = true` (default when specified).
- If `--uplift-sdk3` is present, determine the current SDK version of the API by running the following checks in order:

**Check 1 — SDK2 detection** (Java 8 indicator):

  ```bash
  grep -n "sourceCompatibility" "{project_path}/build.gradle"
  grep -rn "sourceCompatibility" "{project_path}/buildSrc/"
  ```

**Check 2 — SDK4 detection** (OpenRewrite already applied):

  ```bash
  grep -n "SDK4_VERSION" "{project_path}/gradle.properties"
  grep -n "sdk4" "{project_path}/build.gradle"
  ```

**Check 3 — SDK3 detection** (ready for uplift):

  ```bash
  grep -n "SDK3_VERSION" "{project_path}/gradle.properties"
  ```

**Decision logic:**

- **If SDK2 is detected** (either build file contains `sourceCompatibility = JavaVersion.VERSION_1_8`):
  - Throw error and STOP:

    ```
    ERROR: SDK3 uplift is not possible for this API.

    The project is still on SDK2 (Java 8). APIs on SDK2 must be migrated to SDK3
    (Spring Boot 3.5.x / Java 21) before they can be uplifted to the latest Spring Boot version.

    Please run the SDK2 to SDK3 migration first:
      /sdk3-migrate {project_path} --jira {jira_id}

    Once the API is on SDK3, re-run with the --uplift-sdk3 flag to uplift to Spring Boot 4.1.x.
    ```

- **If SDK4 is detected** (`SDK4_VERSION` present in `gradle.properties` OR `sdk4` BOM reference found in `build.gradle`):
  - The OpenRewrite recipe (`UpgradeSpringBoot_4_0`) has already been run on this codebase.
  - Set `openrewrite_run = true` in the state file immediately — Phase U1.1 will skip the recipe execution.
  - Log: `[INFO] SDK4 detected (openrewrite already applied) — OpenRewrite will be skipped in Phase U1`
  - Set `uplift_sdk3 = true` and continue. Load skills `barclays-buk-smesh-api-maintainer:sdk3-sdk4-gradle` and `barclays-buk-smesh-api-maintainer:sdk3-sdk4-migration` before executing uplift phases.

- **If SDK3 is detected** (no `sourceCompatibility = JavaVersion.VERSION_1_8` found, and `SDK3_VERSION` is present in `gradle.properties`, no SDK4 indicators present):
  - The OpenRewrite recipe has not been run yet. Leave `openrewrite_run = false` — Phase U1.1 will execute it.
  - Set `uplift_sdk3 = true` and continue. Load skills `barclays-buk-smesh-api-maintainer:sdk3-sdk4-gradle` and `barclays-buk-smesh-api-maintainer:sdk3-sdk4-migration` before executing uplift phases.

- If `--uplift-sdk3` is not provided, default to `false` and continue with normal SDK2→SDK3 migration flow.

**On failure:** Log specific error and STOP.

---

## Step 2.5: Open Project in IDE

```bash
command -v idea >/dev/null 2>&1 && idea "{project_path}"
```

---

## Step 3: Log Validation + Initialize

Log validated arguments. Detect platform and set `GRADLE_CMD`:

```bash
if [ "$OSTYPE" = "msys" ] || [ "$OSTYPE" = "win32" ] || [ -n "$WINDIR" ]; then
    GRADLE_CMD="gradlew.bat"
else
    GRADLE_CMD="./gradlew"
fi
```

(Use `"mvn"` if Maven project.)

Set branch name based on mode:
```
IF uplift_sdk3 = true:
  BRANCH_NAME = "feature/sdk4-uplift-{jira_id}"
  LOG_PREFIX  = "[AGENT:sdk4-uplift]"
ELSE:
  BRANCH_NAME = "feature/sdk3-migration-{jira_id}"
  LOG_PREFIX  = "[AGENT:sdk3-migrate]"
```

Rotate migration log:

```bash
mkdir -p "{project_path}/logs"
[ -f "{project_path}/logs/migration.log" ] && mv "{project_path}/logs/migration.log" "{project_path}/logs/migration_$(date '+%d%m%y%H%M').log"
touch "{project_path}/logs/migration.log"
echo "[$(date '+%d/%m/%y %H:%M:%S')] {LOG_PREFIX} [START] {jira_id} — project: {project_path}" >> "{project_path}/logs/migration.log"
```

---

## Step 4: State File Management

**Location:** `{project_path}/.claude/migration-state.json`

### 4.1 Read or Create State File

```bash
mkdir -p "{project_path}/.claude"
```

If state file exists → read it. Extract `phases` to determine resume point.
If state file missing but feature branch exists → fall back to git commit parsing (see Step 4.2).
If neither → create initial state file:

```json
{
  "version": 1,
  "jira_id": "{jira_id}",
  "project_path": "{project_path}",
  "started_at": "{ISO timestamp}",
  "build_system": "{gradle|maven}",
  "gradle_cmd": "{GRADLE_CMD}",
  "jdk_version": "{jdk_version}",
  "increment_sdk3": false,
  "uplift_sdk3": false,
  "openrewrite_run": false,
  "flags": {
    "full_automation": false,
    "spring_conventions": false,
    "skip_gitlab_ci": false,
    "group": "capl"
  },
  "branch_name": "feature/sdk3-migration-{jira_id}",
  "phases": {},
  "analysis": {}
}
```

> When `uplift_sdk3 = true`, set `"branch_name": "feature/sdk4-uplift-{jira_id}"` in the initial state. The `openrewrite_run` boolean guards the OpenRewrite execution — it must run exactly once even if the command is resumed after a failure.

### 4.2 Fallback: Git Commit Parsing (if state file missing)

```bash
BRANCH_NAME="feature/sdk3-migration-{jira_id}"
git branch --list "${BRANCH_NAME}"
```

If branch exists (non-empty output), parse commits to reconstruct state:
```bash
git log --oneline --grep="{jira_id} : Phase"
```

Use the Grep tool (NOT shell grep/sed) to extract phase numbers from the commit messages.

Map completed phases to state file entries. Write reconstructed state file.

### 4.3 Resume Logic

Find first non-completed/non-skipped phase from state file → set `RESUME_FROM`.
Mark completed phases' tasks as completed via TaskUpdate.

---

## Step 5: Create Feature Branch

```bash
BRANCH_NAME="feature/sdk3-migration-{jira_id}"
git checkout "${BRANCH_NAME}" 2>/dev/null || git checkout -b "${BRANCH_NAME}"
```

### 5.1 Update .gitignore (first commit)

Ensure `.claude/` and `scripts/` are in `.gitignore`. Commit if changed:
```bash
git add .gitignore && git commit -m "{jira_id} : Update .gitignore — exclude .claude and scripts directories

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Step 6: Pre-Migration JDK Version Check (Conditional)

**ONLY if `--jdk-version=25` is specified. Otherwise skip directly to Step 6.1.**

Detect the current JDK version of the API from its build configuration:

```bash
# Check for Java 8 source compatibility in build.gradle and buildSrc
grep -n "sourceCompatibility.*1_8\|sourceCompatibility.*1\.8\|VERSION_1_8" "{project_path}/build.gradle" 2>/dev/null
grep -rn "sourceCompatibility.*1_8\|sourceCompatibility.*1\.8\|VERSION_1_8" "{project_path}/buildSrc/" 2>/dev/null
grep -n "sourceCompatibility=8\|sourceCompatibility=1\.8" "{project_path}/gradle.properties" 2>/dev/null
```

**Decision logic:**
- If any of the above commands returns a match → the API is on JDK 8. Stop and display the error below.
- If no matches found → the API is on JDK 21 or already upgraded. Proceed to Step 6.1.

If JDK 8 is detected with `--jdk-version=25`, display:

```
VALIDATION FAILED: Direct migration from JDK 8 to JDK 25 is not supported.

Please perform a two-step migration:

Step 1: Migrate from JDK 8 to JDK 21
  /sdk3-migrate {project_path} --jira {jira_id} --jdk-version 21

Step 2: Migrate from JDK 21 to JDK 25
  /sdk3-migrate {project_path} --jira {jira_id} --jdk-version 25
```

---

## DIVERGENCE POINT — uplift_sdk3 flag

**After Step 6, check the `uplift_sdk3` flag:**

```
IF uplift_sdk3 = true:
  → SKIP Steps 6.1 through Step 19 entirely
  → JUMP to the UPLIFT FLOW section below
  → The SDK2→SDK3 migration phases do NOT run for an uplift

ELSE:
  → Continue to Step 6.1 (normal SDK2→SDK3 migration flow)
```

> The uplift flow has its own phase sequence (U1–U7), its own quality gate, its own branch name, and its own final report. The two flows are **completely independent**.

---

## Step 6.1: Execute Phase 0 — Analysis

**Skip if state file shows Phase 0 completed.**

```
TaskCreate(subject: "Phase 0: Pre-Migration Analysis", activeForm: "Analyzing project")
TaskUpdate(status: in_progress)
log "[START] Phase 0 — pre-migration analysis"
```

Spawn `sdk3-migration-agent` via Task tool:
```
subagent_type: "sdk3-migration:sdk3-migration-agent"
description: "Analyze project for SDK3 migration"
prompt:
  PROJECT_PATH: {project_path}
  JIRA_ID: {jira_id}
  BUILD_SYSTEM: {gradle|maven}
  JDK_VERSION: {jdk_version}
  STATE_FILE: {project_path}/.claude/migration-state.json
  Custom Template: {custom_template or "none"}
```

Wait for completion. Parse the `MACHINE_READABLE_ANALYSIS` section from the agent's output. Update state file with analysis results.

```
TaskUpdate(status: completed)
log "[INFO] Phase 0 complete"
```

---

## Step 6.5: Execute SDK3 Increment Phase

**This phase always runs** (for both fresh migrations and existing J21 APIs). It applies the latest SDK3 library version to the API. The `--increment-sdk3` flag controls whether a version comparison is performed before applying.

### 6.5.1 Determine Target SDK3 Version

Read `SUPPORTED_SDK3_VERSION` from the `barclays_internal_libraries_versions.md` skill (e.g., `1.12.007`). This is the version to be applied.

### 6.5.2 Version Gate (conditional on `--increment-sdk3`)

**IF `increment_sdk3=false` (default — not specified or explicitly set to false):**

- No version comparison is performed.
- log `[INFO] SDK3 version uplift: applying SDK3_VERSION {SUPPORTED_SDK3_VERSION} unconditionally`
- Proceed directly to Step 6.5.3.

**IF `increment_sdk3=true`:**

Read the API's current `SDK3_VERSION`:

```bash
CURRENT_SDK3_VERSION=$(grep "^SDK3_VERSION=" {project_path}/gradle.properties | cut -d'=' -f2 | tr -d '[:space:]')
```

Compare versions:
```
IF CURRENT_SDK3_VERSION < SUPPORTED_SDK3_VERSION:
  → log "[INFO] SDK3 upgrade: {CURRENT_SDK3_VERSION} → {SUPPORTED_SDK3_VERSION}"
  → Proceed to Step 6.5.3
ELSE:
  → log "[INFO] API already at latest SDK3_VERSION {CURRENT_SDK3_VERSION} — skipping increment"
  → Skip to Step 7 (Dynamic Task List Generation)
```

### 6.5.3 Apply Incremental Changes

Copy `scripts/incremental.yml` from the plugin to a temp file beside the project, substitute the target version, then run the OpenRewrite recipe:

```bash
# Copy and substitute @@jenkinsBuildVersion@@ with SUPPORTED_SDK3_VERSION
cp "{plugin_scripts_dir}/incremental.yml" "{project_path}/../temp_incremental.yml"
sed -i "s/@@jenkinsBuildVersion@@/{SUPPORTED_SDK3_VERSION}/g" "{project_path}/../temp_incremental.yml"

# Run OpenRewrite with the recipe
{GRADLE_CMD} -p {project_path} rewrite \
  --activeRecipes=com.barclays.SDK3_1_11_Incremental \
  --recipeFile="{project_path}/../temp_incremental.yml"

# Clean up temp file
rm -f "{project_path}/../temp_incremental.yml"
```

**Changes applied by the recipe (`scripts/incremental.yml`):**
- Set `SDK3_VERSION` property in `gradle.properties` to `{SUPPORTED_SDK3_VERSION}` (adds the property if missing)
- Remove deprecated Jacoco task configurations (`jacocoIntegrationTestCoverageVerification`, `jacocoIntegrationTestReport`, `jacocoTestReport`, `jacocoTestCoverageVerification`)
- Add new SDK Jacoco configurations (`sdkJacocoTestReport`, `sdkJacocoTestCoverageVerification`)
- Remove deprecated property keys (`jacocoCoverageExclusions`, `domain.jacocoCoverageExclusions`)

### 6.5.4 Validate Increment

```bash
{GRADLE_CMD} -p {project_path} compileJava --console=plain
```

If compilation fails, log the full error and stop. Do not proceed to commit.

### 6.5.5 Commit Increment Changes

```bash
git add {project_path}
git commit -m "{jira_id} : SDK3 Incremental - Upgrade SDK3_VERSION to {SUPPORTED_SDK3_VERSION}

Changes:
- Updated SDK3_VERSION property to {SUPPORTED_SDK3_VERSION}
- Removed deprecated Jacoco configurations
- Added new SDK Jacoco configurations
- Cleaned deprecated properties

Co-Authored-By: Claude <noreply@anthropic.com>"
```

Update state file: `increment_phase: completed`

---

## Step 7: Dynamic Task List Generation

Read `analysis` from state file. Create tasks based on results:

```
ALWAYS create:
  - "Phase 6.5: SDK3 Version Uplift — apply SDK3_VERSION {SUPPORTED_SDK3_VERSION} [{increment_sdk3=true → version-gated | increment_sdk3=false → unconditional}]"

ALWAYS create:
  - "Phases 1+2+3: Build Config, Package Migration, REST Client"
  - "Phase 2.4: BOM Version Cleanup"
  - "Phase 5: Final Validation & Cleanup"
  - "Phase 8: Push & Finalize"

CREATE IF analysis.has_junit4:
  - "Phase 2.5: Test Package Alignment"
  - "Phase 4: Test Migration (JUnit 4 to JUnit 5)"

CREATE IF analysis.has_integration_tests:
  - "Phase 7: Integration Test Fixes"

CREATE IF analysis.has_checkstyle:
  - "Phase 7.5: Checkstyle Fixes"

CREATE IF analysis.has_raml:
  - "RAML-OAS: Conversion"

CREATE IF flags.spring_conventions:
  - "Phase 0.5: Spring Conventions"
```

Include analysis context in task descriptions (e.g., "Migrate {junit4_file_count} test files from JUnit 4 to JUnit 5"). For SDK3 increment tasks, include current and target SDK3 versions.

---

## Phase Orchestration — Thin Delegation Pattern

**Each phase follows the same pattern (~10-15 lines each):**

```
1. Read state file — skip if phase status is "completed" or "skipped"
2. TaskUpdate(in_progress), update state file: status=in_progress
3. log "[START] Phase {N}"
4. Spawn agent via Task tool
5. Run compile check (per Compile Focus Table)
6. Commit (agent handles its own commits for some phases)
7. Update state file: status=completed
8. TaskUpdate(completed), log "[INFO] Phase {N} complete"
```

### Parallelization Rules

**MAXIMIZE PARALLELISM. Launch independent agents concurrently using multiple Task tool calls in a single message.**

```
SEQUENTIAL:
  Phase 0 → Phase 0.5 (parallel batches) → Phases 1+2+3 → Phase 2.4

PARALLEL GROUP A (after Phase 2.4, launch together):
  Validation (READ-ONLY) + Phase 2.5 (writes src/test/java/ only)

SEQUENTIAL:
  Phase 4 → Phase 5

PARALLEL GROUP B (after Phase 5, launch ALL together):
  Phase 7 (src/integrationTest/) + Phase 7.5 (src/main/java/ checkstyle) + RAML-OAS (src/main/resources/oas/)

SEQUENTIAL:
  Smart Quality Gate → Phase 8 (Push)
```

**Parallel safety by file domain:**
- **Group A:** Validation reads only; Phase 2.5 moves files in `src/test/java/`. No overlap.
- **Group B:** Phase 7 touches `src/integrationTest/`, Phase 7.5 touches `src/main/java/`, RAML-OAS touches `src/main/resources/oas/` + property files. Disjoint domains.

Phase 0.5 spawns ALL spring-conventions-agent batches in parallel (disjoint file sets assigned by orchestrator). Phase 4 is internally parallel (batches of junit-migration-agent). Phase 5 spawns test-fix-agents in parallel per failing test class.

**When launching parallel agents:** Use a SINGLE message with MULTIPLE Task tool calls. Do NOT launch one, wait, then launch the next.

---

## Step 8: Execute Phase 0.5 — Spring Conventions (Optional)

**Skip if `spring_conventions` flag is false (default) or state shows completed.**

Discover ALL files with `@Autowired` upfront, then batch into disjoint groups of 3-4 files. Spawn ALL batches in PARALLEL in a SINGLE message — each batch gets its own `spring-conventions-agent`. Safe because the orchestrator assigns non-overlapping file sets.

```
# Discover all files, then assign to batches deterministically
files = grep -rl "@Autowired" src/
batch_1 = files[0:3], batch_2 = files[3:6], ...

# In a SINGLE message, spawn ALL batches concurrently:
subagent_type: "sdk3-migration:spring-conventions-agent"  # Batch 1
prompt: PROJECT_PATH + FILES: [batch_1]
run_in_background: true

subagent_type: "sdk3-migration:spring-conventions-agent"  # Batch 2
prompt: PROJECT_PATH + FILES: [batch_2]
run_in_background: true

# ... one per batch
```

Wait for ALL background tasks to complete. Compile check: `$GRADLE_CMD compileJava compileTestJava` then `$GRADLE_CMD test`. Commit. Update state.

---

## Step 9: Execute Phases 1+2+3 — Build, Package, REST

**Skip if state shows completed.**

Spawn `build-migration-agent` via Task tool:
```
subagent_type: "sdk3-migration:build-migration-agent"
prompt:
  PROJECT_PATH: {project_path}
  JIRA_ID: {jira_id}
  BUILD_SYSTEM: {build_system}
  GRADLE_CMD: {GRADLE_CMD}
  STATE_FILE: {state_file}
  GROUP: {group}
```

Agent handles: parallel execution, 4-pass residual check, compile validation, per-phase commits, state file update.

**Note:** Validation of Phases 1-3 is deferred to Step 11, where it runs in parallel with Phase 2.5.

---

## Step 10: Execute Phase 2.4 — BOM Version Cleanup

**Skip if state shows completed.**

Spawn `bom-cleanup-agent` via Task tool:
```
subagent_type: "sdk3-migration:bom-cleanup-agent"
prompt:
  PROJECT_PATH: {project_path}
  JIRA_ID: {jira_id}
  GRADLE_CMD: {GRADLE_CMD}
  STATE_FILE: {state_file}
```

Agent handles: cross-reference, version removal, validation, commit, state update.

---

## Step 11: PARALLEL GROUP — Validation + Phase 2.5

**Launch BOTH in a SINGLE message. Skip any that show "completed" or were not created.**

**Safety analysis:** Validation agent is READ-ONLY (tools: `Bash, Read, Grep, Glob`) — it never writes files. Phase 2.5 writes only `src/test/java/` (file moves). No file overlap.

```
# In a SINGLE message, spawn BOTH concurrently:

# Validate Phases 1-3 work (READ-ONLY)
subagent_type: "sdk3-migration:sdk2-to-sdk3-validation-agent"
prompt:
  PROJECT_PATH: {project_path}
  JIRA_ID: {jira_id}
run_in_background: true

# Phase 2.5 — Test Package Alignment (if task exists)
subagent_type: "sdk3-migration:test-package-alignment-agent"
prompt:
  PROJECT_PATH: {project_path}
  JIRA_ID: {jira_id}
  STATE_FILE: {state_file}
run_in_background: true
```

Wait for BOTH to complete. Read validation output — if critical issues detected, spawn `sdk3-migration:auto-decision-agent` to assess whether to proceed or fix. Update state for Phase 2.5.

---

## Step 12: Execute Phase 4 — Test Migration (Parallel)

**Skip if state shows completed or task was not created.**

Discover JUnit 4 test files. Batch into groups of 5-8 files. Spawn `junit-migration-agent` for each batch in parallel:
```
subagent_type: "sdk3-migration:junit-migration-agent"
prompt:
  PROJECT_PATH: {project_path}
  FILES: [batch]
  JIRA_ID: {jira_id}
  BATCH_ID: {n}/{total}
  TASK_ID: {task-id}
```

After all batches complete: `$GRADLE_CMD compileTestJava -x barclaysApiGenerate`. Commit. Update state.

---

## Step 13: Execute Phase 5 — Final Validation & Cleanup

**Skip if state shows completed.**

Run `$GRADLE_CMD test -x barclaysApiGenerate -x jacocoTestCoverageVerification`.

If failures, spawn `sdk3-migration:test-fix-agent` per failing test class. Repeat until green. Commit. Update state.

### Phase 5 Datasource Detection

If test failures contain database connectivity patterns (see `h2_test_database_config.md` skill reference), check for PostgreSQL-specific features. If none → auto-configure H2 via the patterns documented in that skill reference.

---

## Steps 14-15: PARALLEL GROUP — Integration Tests, Checkstyle, RAML-OAS

**Launch ALL applicable phases in a SINGLE message with MULTIPLE Task/Skill tool calls. Do NOT run sequentially.**

**Safety analysis — disjoint file domains:**
- Phase 7 (integration-test-agent): `src/integrationTest/`
- Phase 7.5 (checkstyle-agent): `src/main/java/` (formatting only)
- RAML-OAS: `src/main/resources/oas/`, `gradle.properties`, property files

**Guard:** If Phase 7 integration-test-agent requires `build.gradle` edits (library incompatibility), it may conflict with RAML-OAS writing `gradle.properties`. The orchestrator checks Phase 7 output after completion — if `build.gradle` was modified, re-run RAML-OAS validation.

Check state file for each. Skip any that show "completed" or were not created. Launch all remaining in ONE message:

```
# In a SINGLE message, spawn ALL of these concurrently:

# Phase 7 — Integration Test Fixes (if task exists)
subagent_type: "sdk3-migration:integration-test-agent"
prompt:
  PROJECT_PATH: {project_path}
  JIRA_ID: {jira_id}
run_in_background: true

# Phase 7.5 — Checkstyle Fixes (if task exists)
subagent_type: "sdk3-migration:checkstyle-agent"
prompt:
  PROJECT_PATH: {project_path}
  JIRA_ID: {jira_id}
  GRADLE_CMD: {GRADLE_CMD}
  STATE_FILE: {state_file}
run_in_background: true

# RAML-OAS Conversion (if has_raml task exists)
skill: "raml-to-oas"
args: "{raml_path} --output {project_path}/src/main/resources/oas"
run_in_background: true
```

Wait for ALL background tasks to complete. Commit results. Update state for each phase.

---

## Step 17.5: Final Quality Gate (MANDATORY — blocks push)

**This step ALWAYS runs. It cannot be skipped.**

### 17.5.1: Validate All Phases Completed

Read state file. Every phase that was created MUST have status `completed` or `skipped`. If any phase is `in_progress` or `failed`:
```
log "[FAIL] Phase {N} status is {status} — cannot push"
```
List all incomplete phases. Do NOT proceed to push.

### 17.5.2: Run Full Test Suite (Smart Clean)

Determine whether `clean` is needed by checking if source files changed since Phase 5:

```bash
PHASE5_COMMIT=$(git log --oneline --grep="{jira_id} : Phase 5" -1 --format="%H")
CHANGED_SOURCE=$(git diff --name-only "$PHASE5_COMMIT"..HEAD -- '*.java' '*.gradle' '*.properties' '*.xml' | grep -c .)

if [ "$CHANGED_SOURCE" -eq 0 ]; then
  # No source changes since Phase 5 — incremental build is safe, saves ~2 min recompile
  $GRADLE_CMD test -x barclaysApiGenerate --console=plain
else
  # Source changed (Phase 7/7.5/RAML-OAS modified files) — full clean build
  $GRADLE_CMD clean test -x barclaysApiGenerate --console=plain
fi
```

If ANY test fails → spawn `sdk3-migration:test-fix-agent` per failing class (max 3 retries). Re-run until green.

### 17.5.3: Gate Decision

```
IF all tests pass:
  log "[PASS] Final quality gate — tests: GREEN"
  → proceed to Step 18 (Push)
ELSE after 3 fix attempts:
  log "[FAIL] Quality gate NOT met after 3 attempts — BLOCKING PUSH"
  → STOP. Do NOT proceed to push. Report failures to user.
```

> **Note:** Coverage improvement (JaCoCo/PIT) is handled separately by the `improve-tests` plugin via `/improve-coverage`. Run it after migration completes.

---

## Step 18: Execute Phase 8 — Push & Finalize

**Skip if state shows completed.**

Spawn `push-agent` via Task tool:
```
subagent_type: "sdk3-migration:push-agent"
prompt:
  PROJECT_PATH: {project_path}
  JIRA_ID: {jira_id}
  BASE_BRANCH: {base_branch}
  STATE_FILE: {state_file}
  SKIP_GITLAB_CI: {skip_gitlab_ci}
```

Agent handles: temp file cleanup, GitLab CI update, PR.md generation, migration report, final clean build, innersource.yml, push, MR creation, JIRA comment, state file update.

---

## Step 19: Clean Up Automation Hooks (Conditional)

**ONLY if `--full-automation` was used. MUST run whether migration succeeds or fails.**

Restore original `.claude/settings.json` from Step 0.2 backup. Verify hooks removed. Log `AUTOMATION HOOKS REMOVED`.

---

## Commit Message Rules (All Phases)

Format:
```
{jira_id} : Phase {N} - {Phase Title}

Changes:
- {specific change 1}
- {specific change N}

Co-Authored-By: Claude <noreply@anthropic.com>
```

Build dynamically from `git diff --cached --stat`. Never use generic placeholder text.

---

## Error Messages

### Missing Arguments
```
VALIDATION FAILED: Missing required arguments

Usage: /sdk3-migrate PROJECT_PATH [--jira JIRA_ID] [--jdk-version {21|25}] [--group GROUP] [--template TEXT] [--full-automation] [--spring-conventions] [--skip-gitlab-ci]

Required:
  PROJECT_PATH   Path to project ("." or absolute path)
  --jira         JIRA ticket ID (e.g., GENAIACCEL-1234)

Optional:
  --jdk-version        Java version: 21 or 25 (default: 21)
  --full-automation    Enable enforced automation mode with runtime hooks
  --template           Custom instructions in quotes
  --spring-conventions Run Spring best practices phase (off by default)
  --group              Library group name (default: capl)
  --skip-gitlab-ci     Skip GitLab CI generation (for non-CAPL projects)
```

### Invalid Project Path
```
VALIDATION FAILED: Invalid project_path

Path: {provided_path}
Error: {specific error}

Requirements:
  - Must be "." or an absolute path
  - Directory must exist
  - Must contain build.gradle or pom.xml
  - Must contain src/main/java directory
```

### Invalid JIRA ID
```
VALIDATION FAILED: Invalid jira_id format

Provided: {provided_jira_id}
Expected: PROJECTKEY-12345 (e.g., GENAIACCEL-1234, CARDOPSAPI-5678)
```

### Unsupported JDK Version
```
VALIDATION FAILED: Unsupported jdk-version

Supported values: 21 or 25.
Provided: {provided_jdk_version}

Usage:
  /sdk3-migrate PROJECT_PATH --jira JIRA_ID [--jdk-version 21]
  /sdk3-migrate PROJECT_PATH --jira JIRA_ID [--jdk-version 25]
```

### JDK 8 to JDK 25 Direct Migration Not Supported
```
VALIDATION FAILED: Direct migration from JDK 8 to JDK 25 is not supported.

Please perform a two-step migration:

Step 1: Migrate from JDK 8 to JDK 21
  /sdk3-migrate PROJECT_PATH --jira JIRA_ID --jdk-version 21

Step 2: Migrate from JDK 21 to JDK 25
  /sdk3-migrate PROJECT_PATH --jira JIRA_ID --jdk-version 25
```

### Invalid increment-sdk3 Value
```
VALIDATION FAILED: Invalid increment-sdk3 value

Value must be 'true' or 'false'.
Provided: {provided_value}

Usage:
  /sdk3-migrate PROJECT_PATH --jira JIRA_ID                          # applies SDK3_VERSION unconditionally (default)
  /sdk3-migrate PROJECT_PATH --jira JIRA_ID --increment-sdk3 false   # same as above
  /sdk3-migrate PROJECT_PATH --jira JIRA_ID --increment-sdk3 true    # version-gated: only upgrades if current < supported
```

### Missing SDK3_VERSION for Increment (--increment-sdk3=true only)
```
VALIDATION FAILED: --increment-sdk3=true requires existing SDK3_VERSION in gradle.properties

When --increment-sdk3=true, the API's current SDK3_VERSION must be readable for version comparison.
The project gradle.properties file must contain an SDK3_VERSION property.

Expected format:
  SDK3_VERSION=1.x.xxx

Path: {project_path}/gradle.properties

Note: If you want to apply SDK3_VERSION unconditionally without a version check, omit
--increment-sdk3 or set it to false.
```

---

---

# UPLIFT FLOW — SDK3 to SDK4 (`--uplift-sdk3`)

> **This section executes ONLY when `uplift_sdk3 = true`.** It is a completely independent flow from the SDK2→SDK3 migration steps above. The two flows share: argument parsing (Steps 1–3), state file management (Step 4), branch creation (Step 5), automation hook setup (Step 0), and final hook cleanup (Step 19). Everything else is unique to the uplift.

## Skill Loading (Mandatory — Load Before Any Uplift Phase)

Before executing any uplift phase, load both skills in full:

```
barclays-buk-smesh-api-maintainer:sdk3-sdk4-gradle    ← Gradle / build config changes
barclays-buk-smesh-api-maintainer:sdk3-sdk4-migration ← Source code changes
```

These two skills are the **sole source of truth** for all uplift changes. Do not apply any build or source changes that are not documented in these skills.

## Uplift Phase Task List

Create the following tasks before executing any phase:

```
TaskCreate("Uplift Phase U1: OpenRewrite + Build Config")
TaskCreate("Uplift Phase U2: Manual Source Fixes")
TaskCreate("Uplift Phase U3: Unit Test Fixes")
TaskCreate("Uplift Phase U4: Integration Test Fixes")
TaskCreate("Uplift Phase U5: Checkstyle Fixes")
TaskCreate("Uplift Phase U6: Quality Gate + Validation")
TaskCreate("Uplift Phase U7: Push & Final Report")
```

---

## Uplift Phase U1: OpenRewrite + Build Config

**Skip if state file shows `U1: completed`.**

```
TaskUpdate("Uplift Phase U1", in_progress)
log "[START] Uplift Phase U1 — OpenRewrite + build configuration"
```

### U1.1 — Run OpenRewrite (Conditional — ONCE ONLY)

**Check `openrewrite_run` in state file first.**

```
IF openrewrite_run = true:
  → Log: "[INFO] OpenRewrite already applied (SDK4 detected at validation, or prior run) — skipping recipe"
  → Skip directly to U1.2
  → No init.gradle is written or executed

IF openrewrite_run = false:
  → SDK3 API — OpenRewrite has not been run yet → execute steps below
```

When `openrewrite_run = false`, run the recipe:

1. Write `init.gradle` to `{project_path}/init.gradle` using the exact content from the `sdk3-sdk4-gradle` skill (Step 1 of that skill).
2. Run the recipe:

```bash
# Windows
gradlew.bat --init-script init.gradle rewriteRun

# Linux / macOS
./gradlew --init-script init.gradle rewriteRun
```

3. On success: set `openrewrite_run = true` in state file. Delete `init.gradle` (it is temporary — never commit it). Log: `[INFO] OpenRewrite UpgradeSpringBoot_4_0 complete`.
4. On failure: log the error. Set `openrewrite_run = false` in state file. STOP and report to user — do not attempt manual changes before OpenRewrite succeeds.

### U1.2 — Gradle and Build Configuration Changes

Apply all changes from the `sdk3-sdk4-gradle` skill, Steps 2–6. For each item, **check the current state of the file before applying** — if OpenRewrite was already run (SDK4 path), some of these may already be in place. Apply only what is not yet present:

- Update `gradle/wrapper/gradle-wrapper.properties`: `8.13` → `8.14`
- Rename `SDK3_VERSION` → `SDK4_VERSION` in `gradle.properties`, set `4.0.0` (skip if `SDK4_VERSION` already present)
- Replace `sdk3` BOM with `sdk4` BOM in `build.gradle` (skip if `sdk4` already referenced)
- Update `ext['tomcat.version']`: `10.1.55` → `11.0.22`
- Update `ext['spring-framework.version']`: `6.2.19` → `7.0.9`
- Replace all `com.fasterxml.jackson` references with `tools.jackson` in `build.gradle`; update Jackson version to `3.2.1`
- Update Spring Cloud BOM if present: `2025.0.2` → `2025.1.2`
- Add `spring-cloud-starter-bootstrap` if project uses bootstrap properties
- Remove explicit dependency versions now managed by SDK4 BOM

### U1.3 — Compile Gate

```bash
{GRADLE_CMD} compileJava -x barclaysApiGenerate --console=plain
```

If this fails, the errors will be **source-level breaking changes** not covered by OpenRewrite. Log all errors clearly — they will be fixed in Phase U2. **Do not stop here** — log the errors, note them in state, and proceed to commit what has been applied.

### U1.4 — Commit

Build the commit message dynamically from `git diff --cached --stat`. Omit the OpenRewrite line if `openrewrite_run` was already `true` at the start of this phase:

```bash
git add -A
git commit -m "{jira_id} : Uplift Phase U1 - Build Config

Changes:
{IF openrewrite was executed this phase:}
- Ran OpenRewrite UpgradeSpringBoot_4_0 recipe
{IF openrewrite was already applied (SDK4 detected):}
- OpenRewrite skipped — SDK4 already detected in project
- Updated Gradle wrapper: 8.13 → 8.14
- Renamed SDK3_VERSION → SDK4_VERSION (4.0.0)     {omit if already done}
- Updated BOM: sdk3 → sdk4                         {omit if already done}
- Updated Jackson: com.fasterxml.jackson → tools.jackson 3.2.1
- Updated Spring Framework: 6.2.19 → 7.0.9
- Updated Tomcat: 10.1.55 → 11.0.22
{any other changes detected via git diff --cached --stat}

Co-Authored-By: Claude <noreply@anthropic.com>"
```

> If `git diff --cached` is empty (all build config changes were already applied by a prior OpenRewrite run with no further changes needed), skip the commit and log `[INFO] Phase U1 — no build config changes to commit`.

```
TaskUpdate("Uplift Phase U1", completed)
log "[INFO] Uplift Phase U1 complete"
```

---

## Uplift Phase U2: Manual Source Fixes

**Skip if state file shows `U2: completed`.**

```
TaskUpdate("Uplift Phase U2", in_progress)
log "[START] Uplift Phase U2 — manual source fixes"
```

Apply all manual source changes documented in the `sdk3-sdk4-migration` skill. Work through each section in order. For each change, search the codebase first to confirm whether it applies before modifying files.

### U2.1 — JsonProcessingException → JacksonException

Search: `grep -rn "JsonProcessingException" src/ --include="*.java"`

Replace all occurrences — both import statements and catch blocks — per Step 2.1 of the migration skill.

### U2.2 — ObjectMapper immutability: migrate to JsonMapper.builder()

Search: `grep -rn "new ObjectMapper()" src/ --include="*.java"`

For each occurrence, migrate to `JsonMapper.builder()` construction pattern per Step 2.2 of the migration skill.

### U2.3 — ObjectMapperUtil return type

Search: `grep -rn "ObjectMapperUtil\|createObjectMapper" src/ --include="*.java"`

Update return type to `JsonMapper` per Step 2.3 of the migration skill.

### U2.4 — InternalApiInitializerConfig ObjectMapper bean

Search: `grep -rn "InternalApiInitializerConfig\|objectMapper" src/ --include="*.java" | grep "@Bean"`

Update bean return type to `JsonMapper`; add `@Qualifier("objectMapper")` at autowiring sites per Step 2.4 of the migration skill.

### U2.5 — @JsonInclude(NON_EMPTY) null handling

Search: `grep -rn "JsonInclude\|NON_EMPTY\|getErrors" src/ --include="*.java"`

Update `getErrors()` and similar collection-returning methods to return `null` instead of empty collection per Step 2.5 of the migration skill.

### U2.6 — @JsonPropertyOrder on DTOs

Search: `grep -rn "JsonPropertyOrder\|@JsonProperty" src/ --include="*.java"`

Add explicit `@JsonPropertyOrder` where API contract requires deterministic field order per Step 2.6 of the migration skill.

### U2.7 — RestClientHttpMethod → HttpMethod

Search: `grep -rn "RestClientHttpMethod" src/ --include="*.java"`

Replace with `org.springframework.http.HttpMethod` per Step 3 of the migration skill.

### U2.8 — Remove configurePathMatch from WebConfig

Search: `grep -rn "configurePathMatch" src/ --include="*.java"`

Remove the overriding method entirely per Step 4 of the migration skill.

### U2.9 — Jackson import migration sweep

Search: `grep -rn "com.fasterxml.jackson" src/ --include="*.java"`

Replace any remaining `com.fasterxml.jackson` imports that OpenRewrite missed with `tools.jackson` equivalents, using the import table in Step 8 of the migration skill.

### U2.10 — Compile Gate

```bash
{GRADLE_CMD} compileJava -x barclaysApiGenerate --console=plain
```

**This compile must succeed before continuing.** If errors remain, fix them referencing the migration skill's Common Pitfalls section. Repeat until clean.

### U2.11 — Commit

```bash
git add -A
git commit -m "{jira_id} : Uplift Phase U2 - Manual Source Fixes

Changes:
{dynamically generated from git diff --cached --stat}

Co-Authored-By: Claude <noreply@anthropic.com>"
```

```
TaskUpdate("Uplift Phase U2", completed)
log "[INFO] Uplift Phase U2 complete"
```

---

## Uplift Phase U3: Unit Test Fixes

**Skip if state file shows `U3: completed`.**

```
TaskUpdate("Uplift Phase U3", in_progress)
log "[START] Uplift Phase U3 — unit test fixes"
```

### U3.1 — Compile Test Sources

```bash
{GRADLE_CMD} compileTestJava -x barclaysApiGenerate --console=plain
```

Fix any test compilation errors (Jackson import changes in test code, constructor injection changes, etc.) before proceeding.

### U3.2 — Run Unit Tests

```bash
{GRADLE_CMD} test -x barclaysApiGenerate --console=plain
```

### U3.3 — Fix Failures

For each failing test class, spawn `barclays-buk-smesh-api-maintainer:test-fix-agent`:

```
subagent_type: "barclays-buk-smesh-api-maintainer:test-fix-agent"
prompt:
  PROJECT_PATH: {project_path}
  FAILING_TEST: {test_class_name}
  JIRA_ID: {jira_id}
  CONTEXT: SDK4 uplift — failures likely due to Jackson 3 changes, ObjectMapper immutability,
            or Karate case-sensitive JSON matching. Refer to sdk3-sdk4-migration skill.
```

Spawn test-fix-agents **in parallel** per failing test class (single message, multiple Task calls). Re-run tests after all fix agents complete. Repeat up to 3 times until green.

### U3.4 — Karate JSON Case Sensitivity (Integration test files)

Search for potential case-sensitivity issues in Karate feature files (noted in migration skill Step 6):

```bash
grep -rn "match response\." src/test --include="*.feature" | head -20
```

Flag any assertions that reference string enum values for manual review.

### U3.5 — Commit

```bash
git add -A
git commit -m "{jira_id} : Uplift Phase U3 - Unit Test Fixes

Changes:
{dynamically generated from git diff --cached --stat}

Co-Authored-By: Claude <noreply@anthropic.com>"
```

```
TaskUpdate("Uplift Phase U3", completed)
log "[INFO] Uplift Phase U3 complete"
```

---

## Uplift Phase U4: Integration Test Fixes

**Skip if state file shows `U4: completed` or project has no integration tests.**

Detect integration tests:
```bash
find {project_path}/src -type d -name "integrationTest" 2>/dev/null | head -1
```

If no integration test directory found, mark `U4: skipped` and continue.

```
TaskUpdate("Uplift Phase U4", in_progress)
log "[START] Uplift Phase U4 — integration test fixes"
```

### U4.1 — Run Integration Tests

```bash
{GRADLE_CMD} integrationTest -x barclaysApiGenerate --console=plain
```

### U4.2 — Fix WireMock Timestamp Format

Search for the `+00:00` / `+0000` format in stub files (from migration skill Step 7):

```bash
grep -rn "+00:00\|+0000" src/test --include="*.json" --include="*.yaml" --include="*.feature"
```

Replace with `000Z` format in all affected stub response files and Karate `match` assertions.

### U4.3 — Fix Karate Case Sensitivity

Search for Karate `match` assertions on string values:

```bash
grep -rn "== '" src/test --include="*.feature" | grep "match response"
```

Align expected string values to exact casing produced by the API.

### U4.4 — Fix Remaining Failures

Spawn `barclays-buk-smesh-api-maintainer:integration-test-agent` for any remaining failures:

```
subagent_type: "barclays-buk-smesh-api-maintainer:integration-test-agent"
prompt:
  PROJECT_PATH: {project_path}
  JIRA_ID: {jira_id}
  CONTEXT: SDK4 uplift — known issues: WireMock timestamp format (use 000Z not +00:00),
            Karate case-sensitive JSON matching, Jackson 3 serialisation changes.
            Refer to sdk3-sdk4-migration skill Steps 6 and 7.
```

### U4.5 — Commit

```bash
git add -A
git commit -m "{jira_id} : Uplift Phase U4 - Integration Test Fixes

Changes:
{dynamically generated from git diff --cached --stat}

Co-Authored-By: Claude <noreply@anthropic.com>"
```

```
TaskUpdate("Uplift Phase U4", completed)
log "[INFO] Uplift Phase U4 complete"
```

---

## Uplift Phase U5: Checkstyle Fixes

**Skip if state file shows `U5: completed` or project has no checkstyle configuration.**

Detect checkstyle config:
```bash
find {project_path} -name "checkstyle*.xml" -not -path "*/build/*" | head -1
```

If none found, mark `U5: skipped` and continue.

```
TaskUpdate("Uplift Phase U5", in_progress)
log "[START] Uplift Phase U5 — checkstyle fixes"
```

Spawn `barclays-buk-smesh-api-maintainer:checkstyle-agent`:

```
subagent_type: "barclays-buk-smesh-api-maintainer:checkstyle-agent"
prompt:
  PROJECT_PATH: {project_path}
  JIRA_ID: {jira_id}
  GRADLE_CMD: {GRADLE_CMD}
  STATE_FILE: {state_file}
```

Wait for completion. Agent handles: detect config, run check, parse XML severity="error" only, apply fixes, verify. Agent commits its own changes and updates state.

```
TaskUpdate("Uplift Phase U5", completed)
log "[INFO] Uplift Phase U5 complete"
```

---

## Uplift Phase U6: Quality Gate + Validation

**This gate is MANDATORY. It cannot be skipped.**

```
TaskUpdate("Uplift Phase U6", in_progress)
log "[START] Uplift Phase U6 — quality gate"
```

### U6.1 — Verify All Uplift Phases Completed

Read state file. Every phase from U1–U5 must have status `completed` or `skipped`. If any is `in_progress` or `failed`:

```
log "[FAIL] Uplift phase {N} status is {status} — cannot proceed to push"
```

List all incomplete phases. Do NOT proceed.

### U6.2 — Full Clean Build + Test Suite

Run the final clean build to confirm everything compiles and all tests pass from scratch:

```bash
{GRADLE_CMD} clean test -x barclaysApiGenerate --console=plain
```

If unit tests fail → spawn `barclays-buk-smesh-api-maintainer:test-fix-agent` per failing class (max 3 retries).

### U6.3 — Integration Tests (Final Pass)

```bash
{GRADLE_CMD} integrationTest -x barclaysApiGenerate --console=plain
```

If integration tests fail → spawn `barclays-buk-smesh-api-maintainer:integration-test-agent` (max 2 retries).

### U6.4 — Gate Decision

```
IF all tests pass:
  log "[PASS] Uplift quality gate — all tests GREEN"
  → proceed to U7 (Push & Report)
ELSE after retries:
  log "[FAIL] Uplift quality gate NOT met — BLOCKING PUSH"
  → STOP. Do not push. Present failure summary to user.
```

```
TaskUpdate("Uplift Phase U6", completed)
log "[INFO] Uplift Phase U6 complete"
```

---

## Uplift Phase U7: Push & Final Report

**Skip if state file shows `U7: completed`.**

```
TaskUpdate("Uplift Phase U7", in_progress)
log "[START] Uplift Phase U7 — push & final report"
```

Spawn `barclays-buk-smesh-api-maintainer:push-agent`:

```
subagent_type: "barclays-buk-smesh-api-maintainer:push-agent"
prompt:
  PROJECT_PATH: {project_path}
  JIRA_ID: {jira_id}
  BASE_BRANCH: {base_branch}
  STATE_FILE: {state_file}
  SKIP_GITLAB_CI: {skip_gitlab_ci}
  MIGRATION_TYPE: sdk4-uplift
```

Agent handles: temp file cleanup, GitLab CI update (if applicable), push to remote, MR creation, JIRA comment, state update.

### U7.1 — Generate Final Uplift Report

After the push agent completes, generate and display the final report. This report is **always presented** to the user at the end of the uplift, regardless of automation mode.

```
═══════════════════════════════════════════════════════════
  SDK3 → SDK4 UPLIFT REPORT
  Project : {project_path}
  JIRA    : {jira_id}
  Branch  : feature/sdk4-uplift-{jira_id}
  Started : {started_at}
  Ended   : {current_timestamp}
═══════════════════════════════════════════════════════════

PHASE SUMMARY
─────────────────────────────────────────────────────────
  Phase           │ Status      │ Notes
  ────────────────┼─────────────┼────────────────────────
  U1 OpenRewrite  │ {COMPLETED} │ {e.g. "Recipe run, build config updated" OR "OpenRewrite skipped — SDK4 already detected; build config verified"}
  U2 Source Fixes │ {COMPLETED} │ {e.g. "Jackson 3, ObjectMapper, RestClient fixed"}
  U3 Unit Tests   │ {COMPLETED} │ {e.g. "42 tests pass"}
  U4 Integ Tests  │ {COMPLETED} │ {e.g. "8 tests pass" or "SKIPPED — no integ tests"}
  U5 Checkstyle   │ {COMPLETED} │ {e.g. "0 errors" or "SKIPPED — no config"}
  U6 Quality Gate │ {COMPLETED} │ {e.g. "clean test: PASS, integrationTest: PASS"}
  U7 Push         │ {COMPLETED} │ {e.g. "MR created: {mr_url}"}

CHANGES APPLIED
─────────────────────────────────────────────────────────
  Build:
    ✓ Gradle wrapper: 8.13 → 8.14
    ✓ BOM: sdk3 (SDK3_VERSION) → sdk4 (SDK4_VERSION=4.0.0)
    ✓ Jackson: com.fasterxml.jackson 2.21.4 → tools.jackson 3.2.1
    ✓ Spring Framework: 6.2.19 → 7.0.9
    ✓ Tomcat: 10.1.55 → 11.0.22
    {list any other version changes actually applied}

  Source:
    ✓ OpenRewrite: UpgradeSpringBoot_4_0 applied  {OR: "skipped — SDK4 already detected"}
    ✓ JsonProcessingException → JacksonException ({N} occurrences)
    ✓ ObjectMapper → JsonMapper.builder() ({N} occurrences)
    ✓ RestClientHttpMethod → HttpMethod ({N} occurrences)
    ✓ configurePathMatch removed ({found/not found})
    ✓ WireMock timestamps updated ({N} files)
    ✓ Karate assertions aligned ({N} files)
    {only list changes that were actually applied}

TEST RESULTS
─────────────────────────────────────────────────────────
  Unit tests        : {PASS} ({N} tests)
  Integration tests : {PASS / SKIPPED} ({N} tests)
  Checkstyle errors : {0 errors / SKIPPED}

OVERALL STATUS
─────────────────────────────────────────────────────────
  {✓ UPLIFT COMPLETE — API is now on Spring Boot 4.1.x (SDK4)}
  {or: ✗ UPLIFT INCOMPLETE — {reason}}

MR / PUSH
─────────────────────────────────────────────────────────
  Remote branch : feature/sdk4-uplift-{jira_id}
  MR URL        : {mr_url or "not created — see push agent output"}
═══════════════════════════════════════════════════════════
```

Populate all `{N}` counts from actual `git diff` stats and test output. Do not leave placeholder values in the report.

```
TaskUpdate("Uplift Phase U7", completed)
log "[INFO] Uplift Phase U7 complete — uplift finished"
```

---

## Usage Examples

```bash
# SDK2 to Java 21 with SDK3 (full migration - default)
/sdk3-migrate . --jira GENAIACCEL-1234
/sdk3-migrate /path/to/project --jira GENAIACCEL-1234
/sdk3-migrate . --jira GENAIACCEL-1234 --full-automation

# Explicit JDK 21
/sdk3-migrate . --jira GENAIACCEL-1234 --jdk-version 21

# SDK2/J21 to Java 25 (API must already be on JDK 21 — direct JDK 8 → 25 not supported)
/sdk3-migrate . --jira GENAIACCEL-1234 --jdk-version 25
/sdk3-migrate . --jira GENAIACCEL-1234 --jdk-version 25 --full-automation

# Two-step migration: JDK 8 → JDK 21 → JDK 25
# Step 1: SDK2 to Java 21
/sdk3-migrate . --jira GENAIACCEL-1234 --jdk-version 21
# Step 2: Java 21 to Java 25 (run after Step 1 completes)
/sdk3-migrate . --jira GENAIACCEL-1234-JDK25 --jdk-version 25

# J21/J25 API with SDK3 version upgrade (incremental)
/sdk3-migrate . --jira GENAIACCEL-1234 --increment-sdk3 true
/sdk3-migrate . --jira GENAIACCEL-1234 --increment-sdk3 true --full-automation

# Explicit JDK version with incremental upgrade
/sdk3-migrate . --jira GENAIACCEL-1234 --jdk-version 21 --increment-sdk3 true
/sdk3-migrate . --jira GENAIACCEL-1234 --jdk-version 25 --increment-sdk3 true

# Combined options
/sdk3-migrate . --jira GENAIACCEL-1234 --jdk-version 21 --increment-sdk3 true --full-automation --spring-conventions --skip-gitlab-ci

# SDK4 uplift: API already on SDK3 (Spring Boot 3.5.x), uplift to Spring Boot 4.1.x
/sdk3-migrate . --jira GENAIACCEL-5678 --uplift-sdk3
/sdk3-migrate /path/to/project --jira GENAIACCEL-5678 --uplift-sdk3 --full-automation
/sdk3-migrate . --jira GENAIACCEL-5678 --uplift-sdk3 --skip-gitlab-ci
```

---

## Error Messages

### Missing Arguments
```
VALIDATION FAILED: Missing required arguments

Usage: /sdk3-migrate PROJECT_PATH [--jira JIRA_ID] [--jdk-version {21|25}] [--group GROUP] [--template TEXT] [--full-automation] [--spring-conventions] [--skip-gitlab-ci]

Required:
  PROJECT_PATH   Path to project ("." or absolute path)
  --jira         JIRA ticket ID (e.g., GENAIACCEL-1234)

Optional:
  --jdk-version        Java version: 21 or 25 (default: 21)
  --full-automation    Enable enforced automation mode with runtime hooks
  --template           Custom instructions in quotes
  --spring-conventions Run Spring best practices phase (off by default)
  --group              Library group name (default: capl)
  --skip-gitlab-ci     Skip GitLab CI generation (for non-CAPL projects)
  --uplift-sdk3        Uplift an existing SDK3 API to Spring Boot 4.1.x (SDK4)
```

### Invalid Project Path
```
VALIDATION FAILED: Invalid project_path

Path: {provided_path}
Error: {specific error}

Requirements:
  - Must be "." or an absolute path
  - Directory must exist
  - Must contain build.gradle or pom.xml
  - Must contain src/main/java directory
```

### Invalid JIRA ID
```
VALIDATION FAILED: Invalid jira_id format

Provided: {provided_jira_id}
Expected: PROJECTKEY-12345 (e.g., GENAIACCEL-1234, CARDOPSAPI-5678)
```

### Unsupported JDK Version
```
VALIDATION FAILED: Unsupported jdk-version

Supported values: 21 or 25.
Provided: {provided_jdk_version}

Usage:
  /sdk3-migrate PROJECT_PATH --jira JIRA_ID [--jdk-version 21]
  /sdk3-migrate PROJECT_PATH --jira JIRA_ID [--jdk-version 25]
```

### JDK 8 to JDK 25 Direct Migration Not Supported
```
VALIDATION FAILED: Direct migration from JDK 8 to JDK 25 is not supported.

Please perform a two-step migration:

Step 1: Migrate from JDK 8 to JDK 21
  /sdk3-migrate PROJECT_PATH --jira JIRA_ID --jdk-version 21

Step 2: Migrate from JDK 21 to JDK 25
  /sdk3-migrate PROJECT_PATH --jira JIRA_ID --jdk-version 25
```

### Invalid increment-sdk3 Value
```
VALIDATION FAILED: Invalid increment-sdk3 value

Value must be 'true' or 'false'.
Provided: {provided_value}

Usage:
  /sdk3-migrate PROJECT_PATH --jira JIRA_ID                          # applies SDK3_VERSION unconditionally (default)
  /sdk3-migrate PROJECT_PATH --jira JIRA_ID --increment-sdk3 false   # same as above
  /sdk3-migrate PROJECT_PATH --jira JIRA_ID --increment-sdk3 true    # version-gated: only upgrades if current < supported
```

### Missing SDK3_VERSION for Increment (--increment-sdk3=true only)
```
VALIDATION FAILED: --increment-sdk3=true requires existing SDK3_VERSION in gradle.properties

When --increment-sdk3=true, the API's current SDK3_VERSION must be readable for version comparison.
The project gradle.properties file must contain an SDK3_VERSION property.

Expected format:
  SDK3_VERSION=1.x.xxx

Path: {project_path}/gradle.properties

Note: If you want to apply SDK3_VERSION unconditionally without a version check, omit
--increment-sdk3 or set it to false.
```

### SDK2 API Cannot Be Uplifted
```
ERROR: SDK3 uplift is not possible for this API.

The project is still on SDK2 (Java 8). APIs on SDK2 must be migrated to SDK3
(Spring Boot 3.5.x / Java 21) before they can be uplifted to Spring Boot 4.1.x.

Please run the SDK2 to SDK3 migration first:
  /sdk3-migrate {project_path} --jira {jira_id}

Once the API is on SDK3, re-run with the --uplift-sdk3 flag:
  /sdk3-migrate {project_path} --jira {jira_id} --uplift-sdk3
```

---

**Command Version:** 9.1.1
**Updated:** 2026-09-28
**Architecture:** Thin orchestrator — all implementation in specialized agents
