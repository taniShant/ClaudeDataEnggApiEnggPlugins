---
name: rollback
Source: Barclays BUK Strangler Refactoring Plugin v3.2
Owner: preetha.ramaswamy@barclays.com
Review trigger: Quarterly or on major version bump
user-invocable: false
Status: Published
---
> **Source:** Strangler Refactoring Plugin v3.2 — Rollback — Phase Recovery and Checkpoint Patterns (internal)
> **Owner:** Preetha Ramaswamy / BUK CIO Engineering
> **Review trigger:** Quarterly or on major version bump
> **Status:** Published
> Source documents are Internal — Restricted.


## Quick Start

```
Phase: 7-8 (on failure)
Worker: Orchestrator (triggers rollback)
Load: orchestrator loads rollback skill when code gen or validation fails
Use: git reset --hard to checkpoint SHA, update state, cascade invalidation
Model: fast (git operations are mechanical)
```

# Rollback Protocol — Safe Undo for Failed Extractions

> **Purpose:** Automatic and manual rollback when code generation fails tests or validation rejects. Ensures the codebase is never left in a broken state.

---

## §1 — Checkpoint Creation

Before any code generation (Phase 7), the orchestrator creates a checkpoint:

```bash
# Create checkpoint before extraction attempt
GIT_SHA=$(git rev-parse HEAD)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Record in state file
jq --arg tid "$TASK_ID" --arg sha "$GIT_SHA" --arg ts "$TIMESTAMP" \
  '.checkpoints += [{"task_id": $tid, "git_sha": $sha, "timestamp": $ts}]' \
  .claude/forge-state.json > tmp && mv tmp .claude/forge-state.json
```

---

## §2 — Auto-Rollback Triggers

| Trigger | Condition | Action |
|---------|-----------|--------|
| Test failure after 3 retries | Worker 7A fails all attempts | `git reset --hard {checkpoint_sha}` |
| Validation REJECTED | Worker 8 returns REJECTED | `git reset --hard {checkpoint_sha}` |
| Compilation failure after retries | `compileJava` fails 3 times | `git reset --hard {checkpoint_sha}` |

---

## §3 — Rollback Execution

```bash
# Auto-rollback protocol
rollback_task() {
    TASK_ID=$1
    REASON=$2
    
    # Find checkpoint for this task
    CHECKPOINT_SHA=$(jq -r --arg tid "$TASK_ID" \
      '.checkpoints[] | select(.task_id == $tid) | .git_sha' \
      .claude/forge-state.json)
    
    if [ -z "$CHECKPOINT_SHA" ]; then
        echo "[ERROR] STR-XE002: No checkpoint found for $TASK_ID"
        return 1
    fi
    
    # Execute rollback
    git reset --hard "$CHECKPOINT_SHA"
    
    # Update state
    jq --arg tid "$TASK_ID" --arg reason "$REASON" '. + {
      "machine_state": "ROLLED_BACK",
      "previous_state": .machine_state
    } | .test_status[$tid] = "rolled_back"' \
      .claude/forge-state.json > tmp && mv tmp .claude/forge-state.json
    
    # Log
    echo "[$(date)] [ROLLBACK] task=$TASK_ID sha=$CHECKPOINT_SHA reason=$REASON"
    
    # Clean up generated test/spec artifacts for this task (optional)
    # Specs are preserved (user may want to modify and retry)
}
```

---

## §4 — Manual Rollback Command

`/strangler-rollback TASK_ID` triggers manual rollback:

1. Validate TASK_ID has a checkpoint
2. Show what will be undone (commits since checkpoint)
3. Confirm with user
4. Execute `git reset --hard {checkpoint_sha}`
5. Update state: machine_state = "ROLLED_BACK"
6. Report: "Rolled back T001. Specs preserved. Re-run /strangler-extract T001 to retry."

---

## §5 — Recovery After Rollback

From ROLLED_BACK state, user can:

| Action | Command | Effect |
|--------|---------|--------|
| Retry with same spec | `/strangler-extract T001` | Re-runs Phase 7 (code gen) |
| Modify spec then retry | `/strangler-spec T001` then `/strangler-extract T001` | Regenerates spec, then code |
| Skip this task | Continue with next task | T001 stays rolled back |
| Start fresh | `/strangler-discover target.java` | Full reset |

---

## §6 — What's Preserved After Rollback

| Artifact | Preserved | Why |
|----------|-----------|-----|
| State file | ✅ Yes | Tracks rollback event |
| STRANGLER_SPECS/ | ✅ Yes | User may modify and retry |
| STRANGLER_TESTS/ | ✅ Yes | Tests are correct (code was wrong) |
| Generated service code | ❌ No | Rolled back (was broken) |
| Monolith changes | ❌ No | Rolled back |
| Git history | Clean | Reset removes failed commits |

---

## Agent Self-Check

- [ ] Checkpoint SHA recorded before each extraction attempt
- [ ] `git reset --hard` targets exact checkpoint (not HEAD~N)
- [ ] State file updated to reflect rollback (phase status reverted)
- [ ] Rolled-back files match pre-extraction state (verified via git diff)
- [ ] Cascading invalidation applied to dependent tasks (if parallel mode)
- [ ] Rollback logged with reason: `[ROLLBACK] task=$ID sha=$SHA reason=$REASON`

## Source

**Owner:** preetha.ramaswamy@barclays.com  
**Review cadence:** Quarterly or on major version bump  
**Origin:** Barclays BUK Strangler Refactoring Plugin v3.0 — internal engineering  
**Classification:** Internal
