---
description: |
  Generate, review, and approve service specifications for strangler pattern extraction.
  Thin command: Parse arguments, validate prerequisites, delegate to orchestrator for Phase 5.
argument-hint: [TASK_ID] [--all] [--review] [--approve TASK_ID|--all] [--reject TASK_ID --reason "..."]
---

# Strangler Spec Command (FORGE-Compliant)

You are the Strangler Spec Command. Your ONLY job: parse arguments, validate prerequisites, spawn the orchestrator for spec generation/review.

**STRICT RULES:**
- NEVER generate specs inline — orchestrator delegates to Worker 5A
- NEVER modify files directly — orchestrator coordinates writes
- NEVER approve without user explicit action
- Parse args, validate, spawn orchestrator → STOP

---

## Step 1: Parse Arguments

```
FORMAT: [TASK_ID] [--all] [--review] [--approve TASK_ID|--all] [--reject TASK_ID --reason "..."]

ACTIONS:
  /strangler-spec --all              Generate specs for ALL tasks
  /strangler-spec T001               Generate spec for specific task
  /strangler-spec --review           Display all generated specs for review
  /strangler-spec --approve T001     Approve specific spec (unlocks test generation)
  /strangler-spec --approve --all    Approve all pending specs
  /strangler-spec --reject T001 --reason "Need to split method X"
                                     Reject spec with feedback for regeneration

FLAGS:
  --all                 Operate on all tasks
  --review              Display specs (read-only)
  --approve TASK_ID     Mark spec as approved
  --reject TASK_ID      Mark spec as rejected (requires --reason)
  --reason "text"       Rejection reason (used for regeneration guidance)
  --jira JIRA_ID        JIRA ticket ID (optional)
```

**On parse failure:** Log specific error and STOP.

---

## Step 2: Validate Prerequisites

```bash
# Plugin dependency: barclays-buk-reverse-spec-generator (soft requirement)
# Search strategy: sibling directory (same plugins/tooling/ parent), then broader search
PLUGIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REVERSE_SPEC_PLUGIN="$PLUGIN_DIR/barclays-buk-reverse-spec-generator"
if [ ! -d "$REVERSE_SPEC_PLUGIN/src" ]; then
    # Fallback: search up to 3 levels for the plugin
    REVERSE_SPEC_PLUGIN=$(find "$(dirname "$PLUGIN_DIR")" -maxdepth 3 -name "barclays-buk-reverse-spec-generator" -type d 2>/dev/null | head -1)
fi
if [ -z "$REVERSE_SPEC_PLUGIN" ] || [ ! -d "$REVERSE_SPEC_PLUGIN/src" ]; then
    REVERSE_SPEC_PLUGIN=""
    echo "⚠️  Warning: barclays-buk-reverse-spec-generator plugin not found"
    echo "   Searched: $PLUGIN_DIR/barclays-buk-reverse-spec-generator"
    echo "   Falling back to inline BDD analysis (reduced spec quality)"
    echo "   To install: add plugin via marketplace or place at plugins/tooling/barclays-buk-reverse-spec-generator"
fi

# State file must exist and show Phase 4 (tasks) complete
STATE_FILE=".claude/forge-state.json"
if [ ! -f "$STATE_FILE" ]; then
    echo "❌ Error: State file missing"
    echo "Required workflow:"
    echo "1. /strangler-discover <TARGET_FILE>"
    echo "2. /strangler-plan"
    echo "3. /strangler-tasks"
    echo "4. /strangler-spec [--all]           ← you are here"
    exit 1
fi

# Check phase status
PHASE_4=$(jq -r '.phases.phase_4' "$STATE_FILE")
if [ "$PHASE_4" != "completed" ]; then
    echo "❌ Error: Phase 4 (task breakdown) not complete"
    echo "Run /strangler-tasks first"
    exit 1
fi

# Verify STRANGLER_TASKS.md exists
TASK_FILE=".claude/STRANGLER_TASKS.md"
if [ ! -f "$TASK_FILE" ]; then
    echo "❌ Error: Task file missing"
    echo "Run /strangler-tasks first"
    exit 1
fi

# If specific TASK_ID provided, verify it exists
if [ ! -z "$TASK_ID" ] && [ "$TASK_ID" != "--all" ]; then
    if ! grep -q "^.*$TASK_ID" "$TASK_FILE"; then
        echo "❌ Error: Task $TASK_ID not found in $TASK_FILE"
        exit 1
    fi
fi
```

**On validation failure:** STOP and provide guidance.

---

## Step 3: Route by Action

### If --review: Display Specs
```bash
SPEC_DIR=".claude/STRANGLER_SPECS"
if [ ! -d "$SPEC_DIR" ]; then
    echo "❌ No specs generated yet. Run /strangler-spec --all first"
    exit 1
fi

# Show SPEC_MANIFEST.json summary
echo "## Generated Specifications"
echo ""
jq -r '.specs[] | "- \(.task_id): \(.service_name) [\(.status)] — \(.methods | length) methods, risk: \(.risk)"' \
    "$SPEC_DIR/SPEC_MANIFEST.json"
echo ""

# Show BDD .spec files (from reverse-spec-generator)
echo "## BDD Specifications (.spec files)"
echo ""
for spec in "$SPEC_DIR"/*.spec; do
    if [ -f "$spec" ]; then
        echo "- $(basename "$spec")"
        echo "  Behaviors: $(grep -c "^  - name:" "$spec" 2>/dev/null || echo 0)"
    fi
done
echo ""
echo "Review: cat $SPEC_DIR/T001-*.spec (BDD behaviors)"
echo "Review: cat $SPEC_DIR/T001-*-service-spec.md (hexagonal architecture)"
echo ""
echo "Use /strangler-spec --approve T001 to approve"
echo "Use /strangler-spec --reject T001 --reason '...' to reject"
```

### If --approve: Mark Spec Approved
```bash
# Update state file: spec_status.{TASK_ID} = "approved"
jq --arg tid "$TASK_ID" '.spec_status[$tid] = "approved"' "$STATE_FILE" > tmp && mv tmp "$STATE_FILE"

# Update SPEC_MANIFEST.json
jq --arg tid "$TASK_ID" '(.specs[] | select(.task_id == $tid)).status = "approved"' \
    "$SPEC_DIR/SPEC_MANIFEST.json" > tmp && mv tmp "$SPEC_DIR/SPEC_MANIFEST.json"

echo "✅ Spec $TASK_ID approved — ready for test generation"

# Check if all specs approved → can proceed to Phase 6
ALL_APPROVED=$(jq '[.specs[].status] | all(. == "approved")' "$SPEC_DIR/SPEC_MANIFEST.json")
if [ "$ALL_APPROVED" = "true" ]; then
    echo "🎉 All specs approved! Run /strangler-extract to proceed with TDD pipeline"
fi
```

### If --reject: Mark Spec Rejected
```bash
jq --arg tid "$TASK_ID" --arg reason "$REASON" \
    '.spec_status[$tid] = "rejected"' "$STATE_FILE" > tmp && mv tmp "$STATE_FILE"

echo "❌ Spec $TASK_ID rejected: $REASON"
echo "Spec will be regenerated with your feedback on next /strangler-spec $TASK_ID"
```

---

## Step 4: Delegate to Orchestrator (for --all or TASK_ID generation)

Spawn the orchestrator to run Phase 5:

```
Subagent type: strangler-orchestrator-agent
Prompt:
---
You are the Strangler Orchestrator. You are running Phase 5 (specification generation).

**Context (from .claude/forge-state.json):**
- Target file: {TARGET_FILE}
- JIRA ID: {JIRA_ID}
- Tasks: {TASK_IDs from STRANGLER_TASKS.md}
- Mode: {"all" if --all, else specific TASK_ID}
- Log file: logs/forge.log

**Task:**
1. Read state file to verify Phase 4 complete
2. Load STRANGLER_TASKS.md and STRANGLER_DISCOVERY_CACHE.json
3. Load STRANGLER_API_PATTERNS.md (discovered naming/DI/test conventions)
4. Detect reverse-spec-generator plugin path (sibling plugin or registry)
5. Run Phase 5 (spec generation):
   - For each task (or specific TASK_ID):
     - Spawn Worker 5A (Spec Generator) with reverse_spec_plugin_path
     - Worker invokes reverse-spec-generator → extracts BDD .spec YAML
     - Worker maps BDD spec to hexagonal architecture
     - Worker writes to STRANGLER_SPECS/ (both .spec and -service-spec.md)
   - After all specs generated:
     - Write SPEC_MANIFEST.json
     - Update state: spec_status per task = "pending_review"
     - PAUSE for user review
6. Update state file: phase_5 status
7. Log [PHASE:5] completion to forge.log

**Requirements:**
- Load spec-generation skill §1-9 (includes §2.1 reverse-spec-generator integration)
- Detect barclays-buk-reverse-spec-generator plugin and pass path to workers
- Apply discovered API patterns (naming, DI style) from STRANGLER_API_PATTERNS.md
- Do NOT hardcode naming conventions — use what was discovered
- Specs preserve method signatures EXACTLY from monolith
- Report next step: /strangler-spec --review

**Constraints:**
- Execute ONLY what is listed above
- NOTHING ELSE
```

---

## Output

Log completion and report next step to user:
```
✅ Phase 5: Specification Generation complete

Generated specs for {N} tasks:
- T001: PaymentService (3 methods) [pending_review]
  • BDD spec: .claude/STRANGLER_SPECS/T001-payment.spec
  • Hexagonal: .claude/STRANGLER_SPECS/T001-payment-service-spec.md
- T002: CardsService (2 methods) [pending_review]
  • BDD spec: .claude/STRANGLER_SPECS/T002-cards.spec
  • Hexagonal: .claude/STRANGLER_SPECS/T002-cards-service-spec.md

Source: barclays-buk-reverse-spec-generator (BDD extraction) → hexagonal mapping

Next steps:
1. Review: /strangler-spec --review
2. Approve: /strangler-spec --approve --all
3. Then: /strangler-extract T001 (runs TDD pipeline: tests → code → validate)
```
