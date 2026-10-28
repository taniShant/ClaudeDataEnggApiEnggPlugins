---
description: |
  Execute extraction tasks with automatic validation. Supports single, parallel, and batch modes.
  Thin command: Parse task IDs, validate prerequisites, analyze dependencies, delegate to orchestrator.
argument-hint: TASK_ID [TASK_IDS...] [--parallel] [--all] [--model-strategy auto] [--skip-validation] [--jira JIRA_ID]
---

# Strangler Pattern Extraction (FORGE-Compliant)

You are the Strangler Extract Command. Your ONLY job: parse task IDs, validate prerequisites, analyze dependencies for parallel mode, spawn the orchestrator for extraction.

**STRICT RULES:**
- NEVER implement extraction logic inline — orchestrator delegates to worker agents
- NEVER run validators directly — orchestrator coordinates batched validation
- NEVER modify files — orchestrator coordinates writes
- Parse args, validate prerequisites, spawn orchestrator → STOP

---

## Step 1: Parse Arguments

```
FORMAT: TASK_ID [TASK_IDS...] [--parallel] [--all] [--dry-run] [--model-strategy STRATEGY] [--skip-validation] [--jira JIRA_ID]

POSITIONAL:
  TASK_ID              Task ID(s) to extract
                       - Format: T001, T002, etc.
                       - Multiple IDs allowed: T001 T003 T004
                       - Example: T001

FLAGS:
  --dry-run            Preview extraction plan WITHOUT executing any changes
                       - Shows per-task impact analysis (methods, estimated fidelity, tests)
                       - Simulates parallel wave scheduling (if --parallel or --all)
                       - Predicts monolith delegation changes
                       - Estimates quality gate outcomes
                       - Displays model tier assignments and cost projections
                       - NO files modified, NO state changed, NO workers spawned
  --parallel           Extract multiple independent tasks concurrently
                       - Requires multiple TASK_IDs or --all
                       - Tasks with no dependency on each other run in parallel
                       - Dependent tasks are sequenced into waves automatically
  --all                Extract ALL remaining tasks (respecting dependency order)
                       - Implies --parallel for independent tasks
                       - Tasks are automatically partitioned into dependency waves
  --model-strategy     Model selection strategy for worker agents (default: auto)
                       - auto:     Optimal model per phase (recommended — Sonnet/Opus split, 34% savings)
                       - heavy:    Force Opus for all workers (max quality, highest cost)
                       - balanced: Force Sonnet for all workers (reliable, recommended floor)
  --override-guard     Override the God Class Reduction Guard (expert mode)
                       - Bypasses the Level 1 health score block
                       - Level 2/3 warnings still shown
                       - Validation (Phase 8) still enforces >15 method = FAIL
                       - Use when you're confident the extraction is safe despite low health
  --skip-validation    Skip validation hooks (use only for testing)
  --jira JIRA_ID       JIRA ticket ID (optional)

MODES:
  Single:    /strangler-extract T001
  Parallel:  /strangler-extract T001 T003 T004 --parallel
  Batch All: /strangler-extract --all
  Dry Run:   /strangler-extract --all --dry-run
  Cost-Opt:  /strangler-extract T001 --model-strategy fast
```

**On parse failure:** Log error and STOP.

---

## Step 2: Validate Prerequisites

Check that planning output exists and task(s) are valid:

```bash
# State file must exist and show Phase 3 (tasks) complete
STATE_FILE=".claude/forge-state.json"
if [ ! -f "$STATE_FILE" ]; then
    echo "❌ Error: State file missing"
    echo "Required workflow:"
    echo "1. /strangler-discover <TARGET_FILE>"
    echo "2. /strangler-plan"
    echo "3. /strangler-tasks"
    echo "4. /strangler-extract TASK_ID [--parallel]"
    exit 1
fi

# Check phase status
if ! grep -q '"phase_3".*"completed"' "$STATE_FILE"; then
    echo "❌ Error: Phase 3 (tasks) not complete"
    echo "Run /strangler-tasks first"
    exit 1
fi

# Verify TASK_IDs exist in STRANGLER_TASKS.md
TASK_FILE=".claude/STRANGLER_TASKS.md"
if [ ! -f "$TASK_FILE" ]; then
    echo "❌ Error: Task file missing"
    exit 1
fi

# If --all: collect all tasks from file
if [ "$ALL_FLAG" = true ]; then
    TASK_IDS=$(grep -oP 'T\d{3}' "$TASK_FILE" | sort -u)
fi

# Validate each task ID exists
for TASK_ID in $TASK_IDS; do
    if ! grep -q "^.*$TASK_ID" "$TASK_FILE"; then
        echo "❌ Error: Task $TASK_ID not found"
        echo "Available tasks in $TASK_FILE"
        exit 1
    fi
done
```

**On validation failure:** STOP and provide guidance.

---

## Step 2.5: Dependency Analysis (Parallel Mode Only)

**When `--parallel` or `--all` is specified**, build a dependency DAG and partition tasks into waves:

```bash
# Parse DEPENDS_ON fields from STRANGLER_TASKS.md
# Format expected: "DEPENDS_ON: [T001, T002]" or "DEPENDS_ON: []"

# Build directed acyclic graph (DAG) of task dependencies
# Node = Task ID, Edge = "depends on" relationship

# Algorithm: Topological Sort into Waves
#   Wave 1: Tasks with no dependencies (or all deps already completed)
#   Wave 2: Tasks whose dependencies are ALL in Wave 1
#   Wave N: Tasks whose dependencies are ALL in Waves 1..N-1

# Example:
#   T001: DEPENDS_ON: []
#   T002: DEPENDS_ON: [T001]
#   T003: DEPENDS_ON: []
#   T004: DEPENDS_ON: []
#   T005: DEPENDS_ON: [T002, T003]
#
#   Wave 1: [T001, T003, T004]  ← independent, run in parallel
#   Wave 2: [T002]              ← depends on T001 (Wave 1)
#   Wave 3: [T005]              ← depends on T002 (Wave 2) + T003 (Wave 1)

# Filter: only include requested TASK_IDs in waves
# Tasks already completed (from state file) are treated as satisfied dependencies

# Report parallel plan:
echo "📋 Parallel Extraction Plan:"
echo "  Wave 1 (parallel): T001, T003, T004"
echo "  Wave 2 (parallel): T002"
echo "  Wave 3 (parallel): T005"
echo "  Total waves: 3"
echo "  Tasks per wave: max 3"
```

**If single task (no --parallel):** Skip this step entirely, proceed to Step 3.

---

## Step 3: Detect Context

```bash
# Extract JIRA_ID from state file if not provided
if [ -z "$JIRA_ID" ]; then
    JIRA_ID=$(jq -r '.jira_id // empty' "$STATE_FILE")
fi

# Extract target file from state
TARGET_FILE=$(jq -r '.target_file // empty' "$STATE_FILE")
```

---

## Step 3.5: Dry-Run Preview (--dry-run mode)

**When `--dry-run` is specified**, generate a comprehensive preview WITHOUT modifying any files or state:

```
CRITICAL: In dry-run mode:
  ✗ NO workers are spawned
  ✗ NO state file is modified
  ✗ NO artifacts are created or changed
  ✗ NO git operations occur
  ✗ NO code generation or test generation runs
  ✓ READ existing artifacts only
  ✓ COMPUTE predictions from specs + state
  ✓ DISPLAY impact report → STOP
```

**Dry-Run Output Report:**

```
═══════════════════════════════════════════════════════════════
          🔍 DRY-RUN: EXTRACTION PREVIEW
═══════════════════════════════════════════════════════════════

📋 EXTRACTION SCOPE
  Target:     {TARGET_FILE}
  JIRA:       {JIRA_ID}
  Tasks:      {TASK_IDS} ({count} tasks)
  Mode:       {single | parallel | batch-all}
  Strategy:   {model-strategy}

───────────────────────────────────────────────────────────────
📊 PER-TASK IMPACT ANALYSIS
───────────────────────────────────────────────────────────────

┌─ T001: {task_title}
│  Service:        {ServiceName} (new)
│  Methods:        {N} methods to extract
│    - {method1}(): {lines} lines (clean extraction — guard clauses)
│    - {method2}(): {lines} lines (pure movement — copy)
│    - {method3}(): {lines} lines (moderate cleanup)
│  Dependencies:   {N} injected services
│  Fidelity Est:   ~{X}% (within ≥85% gate ✅)
│  Test Count:     ~{N} tests (contract: {c}, behavior: {b}, integration: {i}, error: {e})
│  Coverage Est:   ~{X}% line, ~{Y}% branch (target: 90% ✅)
│  Risk Level:     {LOW | MEDIUM | HIGH}
│  Model Tier:     Phase 6={tier}, Phase 7={tier} (attempt 1), Phase 8={tier}
│
├─ T003: {task_title}
│  ...
│
└─ T004: {task_title}
   ...

───────────────────────────────────────────────────────────────
🔀 EXECUTION SCHEDULE
───────────────────────────────────────────────────────────────

  {IF single mode:}
  Sequential: T001 → Phase 6 (tests) → Phase 7 (code) → Phase 8 (validate)
  Estimated duration: ~{X} min

  {IF parallel mode:}
  Wave 1 (parallel): T001, T003, T004
    - Concurrent duration: ~{X} min (longest task)
    - Dependencies satisfied: all independent ✅
    - Conflict risk: NONE (distinct service files)
  Wave 2 (parallel): T002
    - Depends on: T001 (from Wave 1)
    - Duration: ~{X} min
  Wave 3 (parallel): T005
    - Depends on: T002, T003 (from Waves 1-2)
    - Duration: ~{X} min

  Total estimated: ~{X} min (parallel) vs ~{Y} min (sequential)
  Speedup: {Z}x

───────────────────────────────────────────────────────────────
📁 MONOLITH CHANGES (Predicted)
───────────────────────────────────────────────────────────────

  File: {TARGET_FILE}
  Changes type: DELEGATION ONLY (additive, no logic modification)

  New fields (per task):
    + @Autowired private {ServiceName}Contract {serviceName};  // T001
    + @Autowired private {ServiceName}Contract {serviceName};  // T003
    + @Autowired private {ServiceName}Contract {serviceName};  // T004

  Method body replacements (per task):
    ~ {method1}() → return {serviceName}.{method1}(...);  // T001
    ~ {method2}() → return {serviceName}.{method2}(...);  // T001
    ...

  Total monolith impact:
    - {N} new @Autowired fields
    - {M} method bodies replaced with delegation one-liners
    - {0} methods removed (preserved for backward compat)

───────────────────────────────────────────────────────────────
✅ QUALITY GATE PREDICTIONS
───────────────────────────────────────────────────────────────

  Check 1: Logic Fidelity (≥85%)
    T001: ~{X}% ✅ | T003: ~{X}% ✅ | T004: ~{X}% ✅
    Prediction: PASS (all tasks above threshold)

  Check 2: TDD + Coverage (≥90%)
    T001: ~{X} tests, ~{Y}% coverage ✅
    T003: ~{X} tests, ~{Y}% coverage ✅
    T004: ~{X} tests, ~{Y}% coverage ✅
    Prediction: PASS (sufficient tests from spec)

  Check 3: Anti-Patterns
    God service (>15 methods): NO ✅
    New dependencies: NO ✅
    Circular deps: NO ✅
    Prediction: PASS

  Overall verdict prediction: ✅ APPROVED

───────────────────────────────────────────────────────────────
💰 COST ESTIMATE (Model-Aware)
───────────────────────────────────────────────────────────────

  Model strategy: {auto | heavy | balanced | fast}

  Per-task estimate:
    Phase 6 (tests):      ~{X} tokens × {model_tier}
    Phase 7A (code gen):  ~{X} tokens × {model_tier}
    Phase 7B (test run):  ~{X} tokens × {model_tier}
    Phase 8 (validation): ~{X} tokens × {model_tier}
    Coverage supplements: ~{X} tokens (if needed)

  Total estimate:
    - {N} tasks × ~{X} tokens/task = ~{TOTAL} tokens
    - vs all-heavy: ~{HEAVY_TOTAL} tokens (savings: {PERCENT}%)

═══════════════════════════════════════════════════════════════
  ℹ️  This is a DRY RUN — no changes were made.
  ➡️  Remove --dry-run to execute: /strangler-extract {TASK_IDS} {FLAGS}
═══════════════════════════════════════════════════════════════
```

**Data Sources for Dry-Run Predictions:**

| Prediction | Source |
|-----------|--------|
| Methods & lines | STRANGLER_DISCOVERY_CACHE.json (method body lines) |
| Service names | STRANGLER_SPECS/SPEC_MANIFEST.json |
| Fidelity estimate | Method complexity from cache (simpler = higher fidelity) |
| Test count | Spec behavior rows + error contracts (formula from §11) |
| Coverage estimate | Branch count from cache × test coverage formula |
| Dependencies | STRANGLER_DISCOVERY_CACHE.json (dependency list) |
| Wave schedule | STRANGLER_TASKS.md (DEPENDS_ON fields) |
| Model tiers | select_model_for_worker() with current context |
| Token costs | model-aware-execution §6 cost table |
| Duration estimate | Phase timing from model-aware-execution §6 |

**After dry-run output: STOP.** Do not proceed to Step 4.

---

## Step 4: Delegate to Orchestrator

### 4A: Single Task Mode (default — no --parallel)

Spawn the orchestrator to run extraction for a single task:

```
Subagent type: general-purpose
Prompt:
---
You are the Strangler Orchestrator. You are running extraction (Phases 6-7-8) for task {TASK_ID}.

**Context (from .claude/forge-state.json):**
- Target file: {TARGET_FILE}
- JIRA ID: {JIRA_ID}
- Task ID: {TASK_ID}
- Skip validation: {--skip-validation flag present}
- Log file: logs/forge.log
- Mode: single

**Task:**
1. Read state file to verify Phase 3 complete
2. Load STRANGLER_PLAN.md and STRANGLER_TASKS.md
3. Find task {TASK_ID} in tasks list
4. Run extraction pipeline (Phase 6 → 7 → 8):
   - Phase 6: Spawn test generator (Worker 6A) — RED state
   - Phase 7: Spawn code generator (Worker 7A) + test runner (Worker 7B)
     - Step 6.5: Coverage verification (≥90% line + branch)
     - 3-attempt strategy if tests fail
   - Phase 8: If NOT --skip-validation:
     - Run unified validation agent (single pass, 3 checks):
       1. Logic fidelity (≥85% pure movement)
       2. TDD behavior validation (including ≥90% coverage gate)
       3. Anti-pattern detection
     - If REJECTED: BLOCK extraction, ROLLBACK, log [FAIL], return errors
     - If APPROVED: Continue to commit
   - Generate commit message with JIRA ID
   - Update task status: completed
5. Update state file: extraction_count += 1
6. Log [COMPLETE] to forge.log

**Requirements:**
- Load phase-gated skills per orchestrator protocol
- Report token usage and execution time
- Provide clear results and next step guidance

**Constraints:**
- Execute ONLY what is listed above
- NOTHING ELSE
```

### 4B: Parallel Mode (--parallel or --all)

Spawn the orchestrator with the full wave plan for concurrent extraction:

```
Subagent type: general-purpose
Prompt:
---
You are the Strangler Orchestrator. You are running PARALLEL extraction for multiple tasks.

**Context (from .claude/forge-state.json):**
- Target file: {TARGET_FILE}
- JIRA ID: {JIRA_ID}
- Mode: parallel
- Skip validation: {--skip-validation flag present}
- Log file: logs/forge.log

**Extraction Waves (from dependency analysis):**
{WAVES_JSON}
# Example:
# [
#   {"wave": 1, "tasks": ["T001", "T003", "T004"]},
#   {"wave": 2, "tasks": ["T002"]},
#   {"wave": 3, "tasks": ["T005"]}
# ]

**Task:**
1. Read state file to verify Phase 3 complete
2. Load STRANGLER_PLAN.md and STRANGLER_TASKS.md
3. Update state: machine_state = "EXTRACTING_PARALLEL"
4. Update state: parallel_extraction.enabled = true, parallel_extraction.waves = {WAVES_JSON}
5. Execute wave-by-wave (sequential BETWEEN waves, parallel WITHIN wave):

   For each wave (in order):
     a. Create per-task checkpoints (git SHA snapshot)
     b. For ALL tasks in this wave (CONCURRENTLY):
        - Phase 6: Spawn Worker 6A (Test Generator) for this task
        - Wait for 6A: verify tests compile + fail (RED)
        - Phase 7: Spawn Worker 7A (Code Generator) for this task
        - Spawn Worker 7B (Test Runner) for this task
        - Step 6.5: Coverage verification (≥90% line + branch)
        - If tests fail: retry (attempt 2=conservative, attempt 3=pure movement)
        - If all retries fail: ROLLBACK this task only, mark ROLLED_BACK
        - If tests pass + coverage OK: mark GREEN
     c. Wait for ALL tasks in wave to reach GREEN or ROLLED_BACK
     d. For each GREEN task (CONCURRENTLY):
        - Phase 8: Spawn Unified Validator per task
        - If APPROVED: commit per-task (separate commit per service)
        - If REJECTED: rollback per-task only
     e. Acquire monolith_write_lock for delegation updates:
        - Apply monolith delegation changes one task at a time
        - Each delegation is additive (add @Autowired + replace method body)
        - Release lock after each delegation
     f. Update state: wave.status = "completed"

6. After all waves complete:
   - Report: N tasks extracted, M rolled back, K validated
   - Update state: machine_state = "COMPLETED" (or partial if some rolled back)
   - Log [COMPLETE] to forge.log

**Conflict Resolution:**
- Each task creates DIFFERENT service files (no overlap possible)
- The only shared file is the monolith (delegation updates)
- Delegation updates are serialized via monolith_write_lock
- No two tasks extract the same method (guaranteed by Phase 4 assignment)
- If merge conflict: task that lost the race retries delegation on current HEAD

**Requirements:**
- Load phase-gated skills per orchestrator protocol
- Report token usage and execution time per task
- Provide clear per-task results and overall summary

**Constraints:**
- Execute ONLY what is listed above
- NOTHING ELSE
```

---

## Output

Log completion and report task results to user.

**Single mode output:**
```
✅ Task {TASK_ID} extracted successfully
   Service: {ServiceName}
   Tests: {N} tests (coverage: {X}% line, {Y}% branch)
   Validation: APPROVED
   Commit: {short_sha}
```

**Parallel mode output:**
```
📋 Parallel Extraction Complete
   Wave 1: T001 ✅ | T003 ✅ | T004 ✅
   Wave 2: T002 ✅
   Wave 3: T005 ❌ (ROLLED_BACK: tests fail after 3 retries)
   
   Summary: 4/5 tasks extracted | 1 rolled back
   Next: Fix T005 spec and retry with /strangler-extract T005
```
