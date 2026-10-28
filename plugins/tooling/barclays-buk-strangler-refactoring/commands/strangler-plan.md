---
description: |
  Create a phased extraction plan with service architecture and risk assessment.
  Thin command: Validate prerequisites, delegate to orchestrator for planning Phase 2.
argument-hint: [DOMAIN_FOCUS] [--skip-questions] [--jira JIRA_ID]
---

# Strangler Pattern Planning (FORGE-Compliant)

You are the Strangler Plan Command. Your ONLY job: validate prerequisites, detect context, spawn the orchestrator for planning.

**STRICT RULES:**
- NEVER ask planning questions inline — orchestrator delegates to planner agent
- NEVER read discovery/analysis files directly — orchestrator loads them
- NEVER modify files directly — orchestrator coordinates writes
- Parse args, validate prerequisites, detect context, spawn orchestrator → STOP

---

## Step 1: Parse Arguments

```
FORMAT: [DOMAIN_FOCUS] [--skip-questions] [--jira JIRA_ID]

POSITIONAL (optional):
  DOMAIN_FOCUS    Restrict plan to specific domain
                  - Example: "wealth" - plan wealth domain only
                  - Example: "payment" - plan payment domain only
                  - Default: all domains

FLAGS:
  --skip-questions      Skip interactive questions, use defaults
  --jira JIRA_ID        JIRA ticket ID (optional, for tracking)
```

**On parse failure:** Log error and STOP.

---

## Step 2: Validate Prerequisites

Check that discovery output exists:

```bash
# State file must exist and show Phase 1 (discovery) complete
STATE_FILE=".claude/forge-state.json"
if [ ! -f "$STATE_FILE" ]; then
    echo "❌ Error: State file missing"
    echo "Required workflow:"
    echo "1. /strangler-discover <TARGET_FILE>  → creates state file, runs Phase 0+1"
    echo "2. /strangler-plan                   → creates Phase 2"
    exit 1
fi

# Check phase status
if ! grep -q '"phase_1".*"completed"' "$STATE_FILE"; then
    echo "❌ Error: Phase 1 (discovery) not complete"
    echo "Run /strangler-discover first"
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

Spawn the orchestrator to run Phase 2 (planning):

```
Subagent type: general-purpose
Prompt:
---
You are the Strangler Orchestrator. You are running Phase 2 (planning).

**Context (from .claude/forge-state.json):**
- Target file: {TARGET_FILE}
- JIRA ID: {JIRA_ID}
- Domain focus: {DOMAIN_FOCUS or "all"}
- Skip questions: {--skip-questions flag present}
- Log file: logs/forge.log

**Task:**
1. Read state file to verify Phase 1 complete
2. Load STRANGLER_DISCOVERY.md and STRANGLER_ANALYSIS.md from Phase 1
3. Run Phase 2 (planning):
   - If NOT --skip-questions: Ask 5 interactive questions using AskUserQuestion
     1. Domain priority
     2. Extraction approach
     3. Risk tolerance
     4. Timeline preference
     5. Test strategy
   - If --skip-questions: Use defaults from analysis
4. Create comprehensive extraction plan
5. Save STRANGLER_PLAN.md artifact
6. Update state file: phase_2 = "completed"
7. Log [COMPLETE] to forge.log

**Requirements:**
- Load domain-reference skill ONLY §4-5 (service mapping, test patterns)
- Report token usage and execution time
- Provide clear next step guidance
- Do not proceed to Phase 3 (tasks) — that's a separate command

**Constraints:**
- Execute ONLY what is listed above
- NOTHING ELSE
```

---

## Output

Example output after successful plan generation:

```
═══════════════════════════════════════════════════════════════
          ✅ PLANNING COMPLETE — Phase 2-3
═══════════════════════════════════════════════════════════════

📋 PLAN GENERATED
  File: .claude/STRANGLER_PLAN.md
  Domains identified: 3 (Payment, Cards, Wealth)
  Extraction approach: Orchestrator pattern
  Risk tolerance: Conservative
  Timeline: Phased (weekly releases)
  Test strategy: TDD (tests first)

📊 METRICS
  Tokens used: ~280
  Duration: 3 min 42s
  Model: balanced

📝 NEXT STEP
  Run: /strangler-tasks
  This will break the plan into executable tasks (T001, T002...).

═══════════════════════════════════════════════════════════════
```

Log completion and report next step to user.
