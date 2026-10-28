---
description: |
  Break the extraction plan into Jira-ready tasks with dependencies.
  Thin command: Validate prerequisites, delegate to orchestrator for Phase 3.
argument-hint: [--jira JIRA_ID]
---

# Strangler Pattern Task Breakdown (FORGE-Compliant)

You are the Strangler Tasks Command. Your ONLY job: validate prerequisites, spawn the orchestrator for task breakdown.

**STRICT RULES:**
- NEVER generate tasks inline — orchestrator delegates to tasks agent
- NEVER read plan files directly — orchestrator loads them
- NEVER modify files — orchestrator coordinates writes
- Parse args, validate prerequisites, spawn orchestrator → STOP

---

## Step 1: Parse Arguments

```
FORMAT: [--jira JIRA_ID]

FLAGS (optional):
  --jira JIRA_ID        JIRA ticket ID (optional, for tracking)
```

**On parse failure:** Log error and STOP.

---

## Step 2: Validate Prerequisites

Check that planning output exists:

```bash
# State file must exist and show Phase 2 (planning) complete
STATE_FILE=".claude/forge-state.json"
if [ ! -f "$STATE_FILE" ]; then
    echo "❌ Error: State file missing"
    echo "Required workflow:"
    echo "1. /strangler-discover <TARGET_FILE>"
    echo "2. /strangler-plan"
    echo "3. /strangler-tasks"
    exit 1
fi

# Check phase status
if ! grep -q '"phase_2".*"completed"' "$STATE_FILE"; then
    echo "❌ Error: Phase 2 (planning) not complete"
    echo "Run /strangler-plan first"
    exit 1
fi

# Verify plan artifact exists
if [ ! -f ".claude/STRANGLER_PLAN.md" ]; then
    echo "❌ Error: Plan file missing"
    exit 1
fi
```

**On validation failure:** STOP and provide guidance.

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

## Step 4: Delegate to Orchestrator

Spawn the orchestrator to run Phase 3 (task breakdown):

```
Subagent type: general-purpose
Prompt:
---
You are the Strangler Orchestrator. You are running Phase 3 (task breakdown).

**Context (from .claude/forge-state.json):**
- Target file: {TARGET_FILE}
- JIRA ID: {JIRA_ID}
- Log file: logs/forge.log

**Task:**
1. Read state file to verify Phase 2 complete
2. Load STRANGLER_PLAN.md from Phase 2
3. Run Phase 3 (task breakdown):
   - Break extraction plan into Jira-ready tasks
   - Each task: <1 day effort, <8 methods extracted
   - Format: T001, T002, ... TN
   - For each task:
     - Task ID
     - Title
     - Methods to extract
     - Acceptance criteria
     - Dependencies (DEPENDS_ON: [])
     - Estimated effort
4. Save STRANGLER_TASKS.md artifact
5. Update state file:
   - phase_3 = "completed"
   - task_count = N
6. Log [COMPLETE] to forge.log

**Requirements:**
- Load domain-reference skill ONLY §4 (service mapping templates)
- Report token usage and execution time
- Provide task summary and next step guidance
- Do not proceed to Phase 4 (extraction) — that's a separate command

**Constraints:**
- Execute ONLY what is listed above
- NOTHING ELSE
```

---

## Output

Example output after successful task breakdown:

```
═══════════════════════════════════════════════════════════════
          ✅ TASK BREAKDOWN COMPLETE — Phase 4
═══════════════════════════════════════════════════════════════

📋 TASKS GENERATED
  File: .claude/STRANGLER_TASKS.md
  Total tasks: 5

  T001  PaymentProcessingService (3 methods)  DEPENDS_ON: []
  T002  PaymentValidationService (2 methods)  DEPENDS_ON: [T001]
  T003  CardManagementService    (4 methods)  DEPENDS_ON: []
  T004  WealthInvestmentService  (3 methods)  DEPENDS_ON: []
  T005  WealthRewardsService     (2 methods)  DEPENDS_ON: [T003, T004]

📊 METRICS
  Tokens used: ~150
  Duration: 1 min 15s
  Model: fast

📝 NEXT STEP
  Run: /strangler-spec --all
  This will generate hexagonal service specifications for review.

═══════════════════════════════════════════════════════════════
```

Log completion and report task breakdown summary to user.
