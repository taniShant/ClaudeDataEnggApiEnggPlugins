---
description: |
  Report current workflow progress and phase completion status.
  Thin command: Read state file, report progress dashboard, recommend next steps.
---

# Strangler Pattern Status (FORGE-Compliant)

You are the Strangler Status Command. Your ONLY job: read state, report progress, recommend next steps.

**STRICT RULES:**
- NEVER modify state — read-only operation
- NEVER implement workflow — just report status
- Parse args, read state, report status → STOP

---

## Step 1: Detect Context

```bash
# Check if state file exists
STATE_FILE=".claude/forge-state.json"
if [ ! -f "$STATE_FILE" ]; then
    echo "❌ No active workflow"
    echo "Start a new workflow:"
    echo "  /strangler-discover <TARGET_FILE>"
    exit 0
fi
```

---

## Step 2: Read State and Report

Read `.claude/forge-state.json` and display:

```
═══════════════════════════════════════════════════════════════
             STRANGLER REFACTORING WORKFLOW STATUS
═══════════════════════════════════════════════════════════════

🎯 TARGET
  File: {target_file}
  JIRA: {jira_id}
  Domain Focus: {domain_focus or "all domains"}

📊 PHASE PROGRESS
  Phase 0 (Setup):              {phase_0_status}
  Phase 1 (Discovery):          {phase_1_status}
  Phase 2 (Analysis):           {phase_2_status}
  Phase 3 (Planning):           {phase_3_status}
  Phase 4 (Task Breakdown):     {phase_4_status}
  Phase 4.5 (God Class Guard):  {guard_status}
  Phase 5 (Spec Generation):    {phase_5_status}
  Phase 6 (Test Gen — RED):     {phase_6_status}
  Phase 7 (Code Gen — GREEN):   {phase_7_status} ({extraction_count} tasks complete)
  Phase 8 (Validation + Push):  {phase_8_status}
  Quality Gate:                 {quality_gate_status}

📈 METRICS
  Total tokens used:       {total_tokens}
  Model strategy:          {model_strategy} (savings: ~{savings_pct}%)
  Execution time:          {execution_time_seconds}s
  Tasks completed:         {extraction_count}/{task_total}
  Validation results:      {validation_approved}/{validation_total}
  Coverage (last task):    {line_coverage}% line / {branch_coverage}% branch
  Health score:            {health_current}/100 (baseline: {health_baseline})

📝 NEXT STEP
  {recommendation}

🔗 ARTIFACTS
  - STRANGLER_DISCOVERY.md      (Phase 1 output)
  - STRANGLER_API_PATTERNS.md   (Phase 1 output)
  - STRANGLER_ANALYSIS.md       (Phase 2 output)
  - STRANGLER_PLAN.md           (Phase 3 output)
  - STRANGLER_TASKS.md          (Phase 4 output)
  - STRANGLER_SPECS/            (Phase 5 output)
  - STRANGLER_TESTS/            (Phase 6 output)

📋 LOGS
  logs/forge.log
```

---

## Step 3: Recommend Next Step

Based on phase status:

| Current Status | Next Step | Command |
|---|---|---|
| Phase 0 complete | Run discovery | `/strangler-discover <TARGET>` |
| Phase 1 complete | Create plan | `/strangler-plan` |
| Phase 2 complete | Break into tasks | `/strangler-tasks` |
| Phase 3 complete | Break into tasks | `/strangler-tasks` |
| Phase 4 complete | Generate specs | `/strangler-spec --all` |
| Phase 4.5 BLOCKED | Reduce scope or override | `/strangler-extract --override-guard` |
| Phase 5 complete (specs) | Review and approve | `/strangler-spec --approve --all` |
| Phase 5 approved | Extract first task | `/strangler-extract T001` |
| Phase 6-7 in progress | Continue or parallel | `/strangler-extract --all --parallel` |
| Phase 8 complete (all tasks) | Done | Workflow complete! Push + MR created ✅ |

---

## Implementation

```bash
#!/bin/bash
set -e

STATE_FILE=".claude/forge-state.json"

if [ ! -f "$STATE_FILE" ]; then
    echo "❌ No active workflow"
    echo ""
    echo "Start a new workflow:"
    echo "  /strangler-discover <TARGET_FILE>"
    exit 0
fi

# Read and display state
jq '.' "$STATE_FILE" | sed 's/^/  /'

echo ""
echo "Recommendation:"
# Add logic to recommend next step based on phase status

```

This command is read-only and performs no writes.
