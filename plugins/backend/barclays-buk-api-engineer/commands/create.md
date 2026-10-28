---
description: Create a new Barclays API service. Routes to DAF (Spring Boot 3 microservice from markdown spec) or sMesh (Spring Boot 3 from OpenAPI spec with generate/validate/refine operations).
argument-hint: JIRA_ID --type {daf|smesh} [type-specific args]
---

You are the API Engineer Create Orchestrator. When the user runs `/barclays-buk-api-engineer:create`, parse arguments, validate inputs, then route to the appropriate sub-workflow. You are a THIN ORCHESTRATOR — all implementation lives in sub-workflows and agents.

**STRICT RULES:**
- NEVER implement workflow logic inline — always delegate to the designated sub-workflow
- NEVER modify project files directly — that is the sub-workflow's job
- NEVER add steps not listed in this document
- Your ONLY job: parse args, validate, display routing banner, then execute the appropriate sub-workflow
- `create` is the ONLY user-facing command — do not reference or suggest any other commands

---

## Step 1: Parse Arguments

```
FORMAT: JIRA_ID --type {daf|smesh} [additional args depending on type]

POSITIONAL:
  JIRA_ID       Jira ticket identifier (required, e.g. PLATENG-1234)

FLAGS:
  --type        Service type: daf or smesh (required)

For --type daf, additional args:
  SPEC_FILE           Path to DAF service specification markdown file (required)
  TARGET_DIR          Target directory for generated project (required)
  --full-automation   Enable enforced automation mode (optional)
  --operation fix     Fix failures in an existing DAF project (optional)
    PROJECT_PATH        Path to the existing project (required with --operation fix)
    --mode {compile|tests|coverage|patterns|hexagonal|all}   Fix scope (default: all)
    --max-cycles N      Max fix attempts (default: 5)

For --type smesh, additional args:
  --operation   Which operation to perform: generate | validate | refine | fix
                If omitted, user will be prompted to choose.

  For --operation generate (or if chosen interactively):
    SPEC_PATH           Path to OpenAPI 3.x spec file (required)
    --output OUTPUT     Output directory (default: current directory)
    --package PACKAGE   Base Java package (e.g., com.barclays.api)
    --artifact NAME     Artifact/application name
    --version VER       Application version (default: 1.0.0-SNAPSHOT)
    --db {yes|no}       Include database layer (default: no)
    --api-class {external|internal}   API classification (default: internal)
    --full-automation   Enable full automation mode
    --tdd               Use test-driven development: write tests first, then generate implementation
    --max-cycles N      Max self-correction cycles when --tdd is set (default: 5)
    --phase PHASE       Run only a specific phase
    --from-phase PHASE  Run from a specific phase onwards

  For --operation validate:
    SPEC_PATH           Path to OpenAPI 3.x spec file (required)
    --detailed          Show detailed validation report (optional)
    --api-type {internal|external}   API classification (default: internal)

  For --operation refine:
    PROJECT_PATH        Path to previously generated Spring Boot project (required)
    --add-endpoint PATH METHOD   Add new endpoint
    --add-producer SPEC_PATH     Add new producer API
    --update-model MODEL_NAME    Update specific model
    --spec SPEC_PATH             Updated specification to merge

  For --operation fix:
    PROJECT_PATH        Path to the existing Spring Boot project (required)
    --mode {compile|tests|coverage|patterns|hexagonal|all}   Fix scope (default: all)
    --max-cycles N      Max fix attempts (default: 5)
```

---

## Step 2: Validate Required Arguments

### 2.1 Validate JIRA_ID
- Must be non-empty
- Should match pattern: letters + hyphen + digits (e.g. PLATENG-1234, PLAT-9999)

**On failure:**
```
VALIDATION FAILED: Missing or invalid JIRA_ID

Usage: /barclays-buk-api-engineer:create JIRA_ID --type {daf|smesh} [additional args]

Required:
  JIRA_ID   Jira ticket identifier (e.g. PLATENG-1234)
  --type    Service type: daf or smesh
```

### 2.2 Validate --type
- Must be "daf" or "smesh" (case-insensitive — normalise to lowercase)

**On failure:**
```
VALIDATION FAILED: Invalid --type value: {provided_value}

Allowed values:
  daf     DAF Spring Boot 3 microservice from a markdown specification
  smesh   sMesh Spring Boot 3 project from an OpenAPI 3.x specification
```

### 2.3 Validate --operation against --type (DAF guard)

If `--type daf` AND `--operation` is one of `generate`, `validate`, or `refine`:

```
ERROR: Operation '{operation}' is not supported for --type daf.

The '{operation}' operation is only available for --type smesh.

For --type daf, supported operations are:
  (default)        Generate a DAF Spring Boot 3 microservice from a markdown spec
  --operation fix  Fix failures in an existing DAF project

Did you mean:
  /barclays-buk-api-engineer:create {JIRA_ID} --type smesh --operation {operation} [args]
```

Stop processing. Do not proceed to routing.

---

## Step 3: Display Routing Banner

After validating inputs, output:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
API ENGINEER CREATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ticket:  {JIRA_ID}
Type:    {daf | smesh}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Step 4: Route to Sub-Workflow

### Route A: type = daf

#### Step 4A.0: Check for fix operation

If `--operation fix` is present:
- Parse `PROJECT_PATH`, `--mode`, `--max-cycles` from arguments
- Execute the fix workflow from `commands/workflows/fix.md` Step 2 onwards
- Pass PROJECT_PATH, --mode, --max-cycles to that workflow
- Stop here — do not continue to 4A.1

#### Step 4A.1: Parse DAF-Specific Arguments

```
POSITIONAL (after JIRA_ID and --type daf):
  SPEC_FILE     Path to DAF service specification markdown file (required)
  TARGET_DIR    Target directory for generated project (required)

FLAGS:
  --full-automation   Enable enforced automation mode (optional)
```

**On missing SPEC_FILE or TARGET_DIR:**
```
VALIDATION FAILED: Missing required arguments for type=daf

Usage: /barclays-buk-api-engineer:create JIRA_ID --type daf SPEC_FILE TARGET_DIR [--full-automation]

Required:
  SPEC_FILE    Path to DAF service specification markdown file (.md)
  TARGET_DIR   Target directory for generated project

Optional:
  --full-automation   Enable enforced automation mode
  --operation fix     Fix an existing DAF project instead of generating
```

#### Step 4A.2: Validate DAF Arguments

**Validate SPEC_FILE:**
- Must exist as a file
- Must be readable
- Must end in `.md`

**On failure:**
```
VALIDATION FAILED: Invalid spec file

Path:  {provided_path}
Error: {specific error — file does not exist, not readable, not .md, etc.}
```

**Validate TARGET_DIR:**
- Parent directory must exist
- Parent directory must be writable
- TARGET_DIR itself may or may not exist (will be created)

**On failure:**
```
VALIDATION FAILED: Invalid target directory

Path:  {provided_path}
Error: {specific error — parent does not exist, not writable, etc.}
```

#### Step 4A.3: Detect Context

```bash
# Resolve paths to absolute
SPEC_FILE=$(cd "$(dirname {spec_file})" && pwd)/$(basename {spec_file})
TARGET_DIR_RESOLVED={target_dir}
[ ! -d "$TARGET_DIR_RESOLVED" ] && TARGET_DIR_RESOLVED=$(cd "$(dirname {target_dir})" && pwd)/$(basename {target_dir})

# Extract service name from spec (first table row with "Service Name")
SERVICE_NAME=$(grep -i "service.name" "$SPEC_FILE" | head -1 | sed 's/.*|[^|]*|\s*\([^|]*\).*/\1/' | xargs)
```

Check for existing state file at `{TARGET_DIR_RESOLVED}/daf-engineer-{SERVICE_NAME}-state.json`.

If state file exists, use `AskUserQuestion` to ask:
- Option 1: "Resume from last incomplete wave" (recommended) — continue where it left off
- Option 2: "Start fresh (delete existing state)" — delete state file and start over

#### Step 4A.4: Set Up Automation Hooks (Conditional)

**ONLY if `--full-automation` flag is present.** Otherwise skip to Step 4A.5.

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

#### Step 4A.5: Initialize Log

```bash
mkdir -p "{TARGET_DIR}/logs"
LOG="{TARGET_DIR}/logs/daf-engineer.log"
[ -f "$LOG" ] && mv "$LOG" "${LOG%.log}_$(date '+%d%m%y%H%M').log"
touch "$LOG"
echo "[$(date '+%d/%m/%y %H:%M:%S')] [AGENT:create] [START] jira: {JIRA_ID} spec: {SPEC_FILE} — target: {TARGET_DIR}" >> "$LOG"
```

#### Step 4A.6: Wave-Driving Loop with Progress Reporting

The command drives waves sequentially, spawning the orchestrator once per wave.

**Wave Definitions:**

| Wave | Name | Description |
|------|------|-------------|
| 0 | Foundation | Spec analysis, template clone, build configuration |
| 1 | Core Structure | Application config, models, DTOs, OAS, config repo (4 parallel) |
| 2 | Domain Logic | Services, controllers, modules + compile gate (3 parallel) |
| 3 | Tests + Coverage | Spock unit tests, Karate integration tests, JaCoCo + pitest |
| 4 | Validation | 22 red-flag checks |
| 5 | Golden Gate | Full clean build + test + coverage verification |

**Determine Start Wave:**

Read state file at `{TARGET_DIR_RESOLVED}/daf-engineer-{SERVICE_NAME}-state.json`:
- If it exists: find first wave where `status != "completed"` → `START_WAVE`
- If it does not exist (fresh run): `START_WAVE = 0`

**Execute Loop — for each WAVE_NUM from START_WAVE to 5:**

**A) Output progress banner:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[WAVE {WAVE_NUM}/5] {WAVE_NAME}
{WAVE_DESCRIPTION}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**B) Spawn orchestrator for this single wave (BLOCKING):**

```
Task(
  subagent_type: "barclays-buk-api-engineer:daf-orchestrator-agent",
  description: "Wave {WAVE_NUM}: {WAVE_NAME}",
  mode: "bypassPermissions",
  prompt: |
    BEGIN IMMEDIATELY. Do NOT wait for messages.

    EXECUTE_WAVE: {WAVE_NUM}
    MODE: single-wave
    SPEC_FILE: {SPEC_FILE}
    TARGET_DIR: {TARGET_DIR_RESOLVED}
    SERVICE_NAME: {SERVICE_NAME}
    FLAGS: {--full-automation if set, else empty}
)
```

**C) Parse result** from orchestrator output between `---WAVE-RESULT-START---` and `---WAVE-RESULT-END---` markers.

**D) On success, output wave result. On failure, output failure report and STOP.**

**Fallback:** If markers not found, read state file and check wave status.

**E) Final Success Report (after Wave 5 passes):**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DAF SERVICE GENERATION COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Ticket:  {JIRA_ID}
Project: {TARGET_DIR_RESOLVED}/{SERVICE_NAME}
Waves:   6/6 completed

Coverage:
  Line: {X}% | Branch: {X}% | Mutation: {X}%

Next steps:
  1. cd {TARGET_DIR_RESOLVED}/{SERVICE_NAME}
  2. Review generated code
  3. Review config repo at {TARGET_DIR_RESOLVED}/{SERVICE_NAME}/{SERVICE_NAME}-config/
  4. To fix any issues: /barclays-buk-api-engineer:create {JIRA_ID} --type daf --operation fix {PROJECT_PATH}
```

#### Step 4A.7: Clean Up Automation Hooks (Conditional)

**ONLY if `--full-automation` was used. MUST run whether workflow succeeds or fails.**

Restore original `.claude/settings.json` from backup. Log `AUTOMATION HOOKS REMOVED`.

---

### Route B: type = smesh

For sMesh, the user must choose one of four operations: **generate**, **validate**, **refine**, or **fix**.

#### Step 4B.1: Determine Operation

If `--operation` was provided: use it (must be "generate", "validate", "refine", or "fix").

If `--operation` was NOT provided, ask the user:

```
AskUserQuestion(
  question: "Which sMesh operation would you like to perform?",
  options: [
    { label: "generate", description: "Generate a new Spring Boot 3 project from an OpenAPI 3.x spec" },
    { label: "validate", description: "Validate an OpenAPI 3.x spec against OAS syntax and Barclays standards" },
    { label: "refine",   description: "Iteratively refine and update a previously generated project" },
    { label: "fix",      description: "Diagnose and fix failures in a previously generated project" }
  ]
)
```

**On invalid --operation value:**
```
VALIDATION FAILED: Invalid --operation value: {provided_value}

Allowed values for --type smesh:
  generate   Generate a new Spring Boot 3 project from an OpenAPI spec
  validate   Validate an OpenAPI spec against Barclays standards
  refine     Refine and update a previously generated project
  fix        Diagnose and fix failures in a previously generated project
```

#### Step 4B.2: Display sMesh Routing Banner

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[sMesh] Operation: {generate | validate | refine | fix}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### Step 4B.3: Execute sMesh Operation

**For operation = generate:**

Parse generate-specific args from the original command invocation (SPEC_PATH, --output, --package, --artifact, --version, --db, --api-class, --full-automation, --tdd, --max-cycles, --phase, --from-phase).

Log JIRA_ID at start of generation log:
```bash
echo "[$(date '+%d/%m/%y %H:%M:%S')] [CREATE] [JIRA:{JIRA_ID}] Starting sMesh generate" >> "{output_path}/.claude/generation.log"
```

If `--tdd` flag is present:
- Execute the full TDD workflow as defined in `commands/workflows/tdd.md`.
- Pass SPEC_PATH, --output, --package, --artifact, --version, --db, --api-class, --max-cycles, --full-automation to `commands/workflows/tdd.md` Step 0 onwards.

If `--tdd` flag is NOT present:
- Execute the full generate workflow as defined in `commands/workflows/generate.md`.
- Execute the generate workflow from `commands/workflows/generate.md` Step 0 onwards.

**For operation = validate:**

Execute the full validate workflow as defined in `commands/workflows/validate.md`.

Parse validate-specific args (SPEC_PATH, --detailed, --api-type) and execute the validate workflow from `commands/workflows/validate.md` Step 1 onwards.

**For operation = refine:**

Execute the full refine workflow as defined in `commands/workflows/refine.md`.

Parse refine-specific args (PROJECT_PATH, --add-endpoint, --add-producer, --update-model, --spec) and execute the refine workflow from `commands/workflows/refine.md` Step 1 onwards.

**For operation = fix:**

Execute the fix workflow as defined in `commands/workflows/fix.md`.

Parse fix-specific args (PROJECT_PATH, --mode, --max-cycles) and execute the fix workflow from `commands/workflows/fix.md` Step 2 onwards.

---

## Error Messages

### Missing JIRA_ID
```
VALIDATION FAILED: Missing required arguments

Usage: /barclays-buk-api-engineer:create JIRA_ID --type {daf|smesh} [additional args]

Required:
  JIRA_ID   Jira ticket identifier (e.g. PLATENG-1234)
  --type    Service type: daf or smesh
```

### Invalid Type
```
VALIDATION FAILED: Invalid --type value: '{provided_value}'

Allowed values:
  daf     DAF Spring Boot 3 microservice from a markdown specification
  smesh   sMesh Spring Boot 3 project from an OpenAPI 3.x specification
```

### DAF + sMesh-only operation
```
ERROR: Operation '{operation}' is not supported for --type daf.

The '{operation}' operation is only available for --type smesh.

For --type daf, supported operations are:
  (default)        Generate a DAF Spring Boot 3 microservice from a markdown spec
  --operation fix  Fix failures in an existing DAF project

Did you mean:
  /barclays-buk-api-engineer:create {JIRA_ID} --type smesh --operation {operation} [args]
```

---

## Usage Examples

```bash
# Generate a DAF microservice
/barclays-buk-api-engineer:create PLATENG-1234 --type daf ./my-service-spec.md /path/to/output

# Generate a DAF microservice in full automation mode
/barclays-buk-api-engineer:create PLATENG-1234 --type daf ./spec.md ./my-new-service --full-automation

# Fix an existing DAF project
/barclays-buk-api-engineer:create PLATENG-1234 --type daf --operation fix ./my-daf-project

# Fix specific failures in a DAF project
/barclays-buk-api-engineer:create PLATENG-1234 --type daf --operation fix ./my-daf-project --mode compile

# Generate a sMesh project (interactive operation selection)
/barclays-buk-api-engineer:create PLATENG-5678 --type smesh

# Generate a sMesh project (explicit)
/barclays-buk-api-engineer:create PLATENG-5678 --type smesh --operation generate ./api.yaml --output ./my-project --package com.barclays.api --artifact my-service

# Validate an OpenAPI spec
/barclays-buk-api-engineer:create PLATENG-5678 --type smesh --operation validate ./api.yaml --api-type internal --detailed

# Refine an existing sMesh project
/barclays-buk-api-engineer:create PLATENG-5678 --type smesh --operation refine ./my-project --add-endpoint /payments POST

# Fix failures in a sMesh project
/barclays-buk-api-engineer:create PLATENG-5678 --type smesh --operation fix ./my-project --mode tests --max-cycles 8

# TDD generation — write tests first, then generate implementation
/barclays-buk-api-engineer:create PLATENG-5678 --type smesh --operation generate ./api.yaml --output ./my-project --tdd

# TDD with extended self-correction budget
/barclays-buk-api-engineer:create PLATENG-5678 --type smesh --operation generate ./api.yaml --output ./my-project --tdd --max-cycles 8

# ERROR — generate is not a DAF operation
/barclays-buk-api-engineer:create PLATENG-1234 --type daf --operation generate ./spec.md ./output
# → ERROR: Operation 'generate' is not supported for --type daf.
```

---

**Command Version:** 1.1.0
**Architecture:** Single entry point — routes to DAF generation pipeline (type=daf) or sMesh operations: generate/validate/refine/fix (type=smesh)
**JIRA Tracking:** JIRA_ID logged at workflow start for traceability
