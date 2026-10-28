---
description: Generate a Spring Boot 3 project using test-driven development — tests are written first (RED), then implementation is generated to make them pass (GREEN), then self-correcting until fully green (REFACTOR).
argument-hint: SPEC_PATH [--output OUTPUT] [--package PACKAGE] [--artifact NAME] [--max-cycles N] [--full-automation]
---

You are the TDD Command. Generate a Spring Boot 3 project test-first: write contracts as failing tests before a single line of production code is generated, then generate implementation, then self-correct until all tests pass.

**STRICT RULES:**
- NEVER write production code inline — delegate entirely to tdd-orchestrator-agent
- NEVER skip the RED phase — tests before implementation is non-negotiable
- NEVER modify the spec during generation

---

## Step 0: Parse Arguments

```
FORMAT: SPEC_PATH [--output OUTPUT] [--package PACKAGE] [--artifact NAME]
                  [--version VERSION] [--db {yes|no}] [--api-class {internal|external}]
                  [--max-cycles N] [--full-automation]

POSITIONAL:
  SPEC_PATH         Path to OpenAPI 3.x .yaml/.yml/.json file (required)

FLAGS:
  --output OUTPUT   Output directory (default: current directory)
  --package         Base Java package (e.g., com.barclays.api)
  --artifact        Artifact/application name
  --version         Application version (default: 1.0.0-SNAPSHOT)
  --db {yes|no}     Include database layer (default: no)
  --api-class       API classification: internal or external (default: internal)
  --max-cycles N    Maximum self-correction cycles (default: 5, max: 10)
  --full-automation Skip all interactive prompts
```

---

## Step 1: Validate SPEC_PATH

- Must exist as a file
- Must have extension `.yaml`, `.yml`, or `.json`

**On failure:**
```
VALIDATION FAILED: Invalid spec path

Path:  {provided_path}
Error: {file does not exist | not a .yaml/.yml/.json file}

Usage: /barclays-buk-api-engineer:tdd SPEC_PATH [options]
```

---

## Step 2: Display TDD Banner

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TDD GENERATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Spec:        {SPEC_PATH}
Output:      {OUTPUT_PATH}
Max cycles:  {MAX_CYCLES}
Mode:        RED → GREEN → REFACTOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Step 3: Parse Spec

Spawn `spec-parsing-agent`:

```
Task(
  subagent_type: "barclays-buk-api-engineer:spec-parsing-agent",
  description: "Parse OpenAPI spec",
  prompt: |
    Parse the OpenAPI 3.x spec at: {SPEC_PATH}
    Return the full semantic model JSON.
)
```

After the agent returns, extract `SPEC_ANALYSIS.detected_api_classification` from the `MACHINE_READABLE_ANALYSIS` JSON.

---

## Step 3a: OAS API Classification Detection

Apply the same resolution logic as `generate.md` Step 6a:

```
if --api-class flag was explicitly provided:
    OAS_DETECTED_API_CLASS = null      # flag wins — no auto-detection needed
elif SPEC_ANALYSIS.detected_api_classification is not null:
    OAS_DETECTED_API_CLASS = SPEC_ANALYSIS.detected_api_classification
    display: "ℹ️  API classification auto-detected from spec: {value}"
else:
    OAS_DETECTED_API_CLASS = null      # clarification agent will prompt or use default
```

---

## Step 4: Collect Configuration

If `--full-automation` is set, derive defaults from spec and args. Otherwise spawn `clarification-checkpoint-agent`:

```
Task(
  subagent_type: "barclays-buk-api-engineer:clarification-checkpoint-agent",
  description: "Collect project configuration",
  prompt: |
    SPEC_ANALYSIS: {SPEC_ANALYSIS_JSON}
    OVERRIDES: {parsed flags as JSON}
    FULL_AUTOMATION: {true|false}
    OAS_DETECTED_API_CLASS: {OAS_DETECTED_API_CLASS}   # "external", "internal", or null
)
```

---

## Step 5: Initialise Output Directory

```bash
OUTPUT_PATH=$(realpath --canonicalize-missing "{output}")
mkdir -p "$OUTPUT_PATH"
mkdir -p "$OUTPUT_PATH/.claude"

LOG_FILE="$OUTPUT_PATH/.claude/generation.log"
touch "$LOG_FILE"
echo "[$(date '+%d/%m/%y %H:%M:%S')] [COMMAND:tdd] [START] spec: {SPEC_PATH} output: $OUTPUT_PATH max_cycles: {MAX_CYCLES}" >> "$LOG_FILE"
```

---

## Step 6: Run TDD Cycle

Display phase banner:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PHASE 1/3] RED — Writing Failing Tests
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Spawn `tdd-orchestrator-agent` (BLOCKING):

```
Task(
  subagent_type: "barclays-buk-api-engineer:tdd-orchestrator-agent",
  description: "TDD cycle — RED → GREEN → REFACTOR",
  prompt: |
    BEGIN IMMEDIATELY. Do NOT wait for messages.

    SPEC_ANALYSIS: {SPEC_ANALYSIS_JSON}
    CONFIG: {CONFIG_JSON}
    OUTPUT_PATH: {OUTPUT_PATH}
    MAX_CYCLES: {MAX_CYCLES}
    LOG_FILE: {LOG_FILE}
)
```

Parse result between `---TDD-CYCLE-RESULT-START---` and `---TDD-CYCLE-RESULT-END---`.

Display intermediate phase banners as the result arrives:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PHASE 2/3] GREEN — Generating Implementation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PHASE 3/3] REFACTOR — Self-Correcting Until Green
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Step 7: Output Final Report

### On status = passed

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TDD GENERATION COMPLETE ✓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Spec:    {SPEC_PATH}
Project: {OUTPUT_PATH}
Phases:  RED ✓  GREEN ✓  REFACTOR ✓

Tests:     {tests_passed} passed / {tests_failed} failed
Coverage:  Line {line_coverage_pct}% | Branch {branch_coverage_pct}%
Cycles:    {cycles_used}/{max_cycles}

Next steps:
  1. cd {OUTPUT_PATH}
  2. ./gradlew test   — verify test suite
  3. Review generated tests in src/test/
  4. /barclays-buk-api-engineer:refine {OUTPUT_PATH} to add endpoints
```

### On status = partial

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TDD GENERATION COMPLETE (PARTIAL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phases:  RED ✓  GREEN ✓  REFACTOR ⚠ ({cycles_used}/{max_cycles} cycles used)

Tests:     {tests_passed} passed / {tests_failed} failed
Remaining: {remaining_failures}

To continue fixing:
  /barclays-buk-api-engineer:fix {OUTPUT_PATH}
```

### On status = failed

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TDD GENERATION FAILED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Failed at: {red|green|refactor} phase
Reason:    {summary from result block}

Check log: {LOG_FILE}
```

---

## Usage Examples

```bash
# Full TDD generation
/barclays-buk-api-engineer:tdd ./api.yaml --output ./my-project \
  --package com.barclays.api --artifact my-service

# Full automation — no prompts
/barclays-buk-api-engineer:tdd ./api.yaml --output ./my-project --full-automation

# Extended self-correction budget
/barclays-buk-api-engineer:tdd ./api.yaml --output ./my-project --max-cycles 10
```

---

**Command Version:** 1.0.0
**Workflow:** spec-parsing-agent → clarification-checkpoint-agent → tdd-orchestrator-agent (RED → GREEN → REFACTOR)
