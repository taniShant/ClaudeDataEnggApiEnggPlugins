---
name: branching-strategy
Source: Barclays BUK Strangler Refactoring Plugin v3.2
Owner: preetha.ramaswamy@barclays.com
Review trigger: Quarterly or on major version bump
user-invocable: false
Status: Published
---
> **Source:** Strangler Refactoring Plugin v3.2 — Branching Strategy — Git Conventions (internal)
> **Owner:** Preetha Ramaswamy / BUK CIO Engineering
> **Review trigger:** Quarterly or on major version bump
> **Status:** Published
> Source documents are Internal — Restricted.


## Quick Start

```
Phase: All (cross-cutting)
Worker: Orchestrator + Push Agent
Load: orchestrator loads branching-strategy for commit/push decisions
Use: Branch naming, commit format, push timing, rollback via git reset
Model: fast (git operations are mechanical)
```

# Branching Strategy — Strangler Refactoring Pipeline

> **Purpose:** Defines when branches are created, how commits are staged, when pushes happen, and how rollback interacts with git history. Adapted from SDK3 migration strategy for task-based iterative extraction.

---

## §1 — Branch Lifecycle

```
main/develop ──────────────────────────────────────────────────────────────→
     │
     └─→ feature/{JIRA_ID}-strangler-extract
           │            │            │            │            │
         commit       commit       commit       commit       push + MR
         [setup]      [specs]      [T001]       [T002]       (after quality gate)
         Phase 0-4    Phase 5      Phase 7      Phase 7      Phase 8
```

### Rules:
1. **One feature branch per strangler refactoring** (one monolith target = one branch)
2. **Branch created at Phase 0** (start of `/strangler-discover`)
3. **All commits are LOCAL until final push** (enables safe rollback)
4. **Push happens ONCE at the end** (after Phase 8 quality gate passes)
5. **Rollback resets LOCAL commits only** (never force-pushes)

---

## §2 — Branch Creation

### When: Phase 0 (start of `/strangler-discover`)

```bash
# Detect JIRA ID (from --jira flag or git branch name)
JIRA_ID="${JIRA_ID:-$(git rev-parse --abbrev-ref HEAD | grep -oP '(?<=/|^|-)[A-Z]{2,}-\d+' | head -1)}"

# Branch naming pattern
BRANCH_NAME="feature/${JIRA_ID}-strangler-extract"

# Create or checkout branch
if git rev-parse --verify "$BRANCH_NAME" &>/dev/null; then
    git checkout "$BRANCH_NAME"
    echo "[BRANCH] Resuming existing branch: $BRANCH_NAME"
else
    # Branch from target (detect default remote branch)
    TARGET_BRANCH=$(git remote show origin | grep 'HEAD branch' | awk '{print $NF}')
    git checkout -b "$BRANCH_NAME" "origin/$TARGET_BRANCH"
    echo "[BRANCH] Created: $BRANCH_NAME from origin/$TARGET_BRANCH"
fi
```

### Branch Name Validation:
```
Pattern: feature/{JIRA_ID}-strangler-extract
Example: feature/HPTRX-9196-strangler-extract
         feature/CARDOPSAPI-15153-strangler-extract

Rules:
- Must contain valid JIRA ID: ^[A-Z]+-[0-9]+$
- Must have "strangler" in name (identifies purpose)
- Prefix: feature/ (Git Flow convention)
```

---

## §3 — Commit Strategy

### Commit Points (in order):

| # | When | What's Committed | Message Format |
|---|------|-----------------|----------------|
| 1 | Phase 4 complete (tasks defined) | Discovery artifacts, plan, tasks | `{JIRA_ID} : strangler setup — discovery + analysis + plan + tasks` |
| 2 | Phase 5 complete (specs approved) | STRANGLER_SPECS/ directory | `{JIRA_ID} : strangler specs — service contracts for T001-T{N}` |
| 3..N | Each task extraction (Phase 7 GREEN) | New service + tests + monolith delegation | `{JIRA_ID} : extract T{NNN} — {ServiceName} ({N} methods)` |

### Commit Message Format:

```
{JIRA_ID} : {phase_marker} — {short description}

- {bullet point 1: what was done}
- {bullet point 2: key change}
- {bullet point 3: validation result}

Task: T{NNN}
Fidelity: {N}%
Tests: {passed}/{total}

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Examples:

**Setup commit (Phase 0-4):**
```
HPTRX-9196 : strangler setup — discovery + analysis + plan + tasks

- Analyzed MonolithService.java (136 methods, health score: 42)
- Discovered 5 domains via API inspection (Payment, Cards, Wealth, Rewards, Integration)
- Created extraction plan: Orchestrator pattern with 5 services
- Generated 5 tasks (T001-T005)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Spec commit (Phase 5):**
```
HPTRX-9196 : strangler specs — service contracts for T001-T005

- Generated 5 service specifications with contracts
- PaymentServiceContract (3 methods)
- CardsServiceContract (2 methods)
- WealthServiceContract (4 methods)
- RewardsServiceContract (3 methods)
- IntegrationServiceContract (4 methods)
- All specs reviewed and approved

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Extraction commit (Phase 7, per task):**
```
HPTRX-9196 : extract T001 — PaymentService (3 methods)

- Extracted: processPayment, getPaymentStatus, cancelPayment
- Created: PaymentService implements PaymentServiceContract
- Delegation: MonolithService now delegates to PaymentService
- Tests: 12 passed (contract: 3, behavior: 5, integration: 2, error: 2)

Task: T001
Fidelity: 91%
Tests: 12/12 passed

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## §4 — Commit Commands

### After Phase 4 (setup):
```bash
git add .claude/STRANGLER_DISCOVERY.md \
        .claude/STRANGLER_DISCOVERY_CACHE.json \
        .claude/STRANGLER_API_PATTERNS.md \
        .claude/STRANGLER_ANALYSIS.md \
        .claude/STRANGLER_PLAN.md \
        .claude/STRANGLER_TASKS.md \
        .claude/forge-state.json

git commit -m "${JIRA_ID} : strangler setup — discovery + analysis + plan + tasks

$(cat <<EOF
- Analyzed $(basename $TARGET_FILE) (${METHOD_COUNT} methods, health score: ${HEALTH_SCORE})
- Discovered ${DOMAIN_COUNT} domains via API inspection
- Created extraction plan: ${PATTERN} pattern
- Generated ${TASK_COUNT} tasks (T001-T$(printf '%03d' $TASK_COUNT))

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### After Phase 5 (specs):
```bash
git add .claude/STRANGLER_SPECS/

git commit -m "${JIRA_ID} : strangler specs — service contracts for T001-T$(printf '%03d' $TASK_COUNT)

$(cat <<EOF
- Generated ${TASK_COUNT} service specifications with contracts
$(for spec in .claude/STRANGLER_SPECS/contracts/*.java; do
    echo "- $(basename $spec .java)"
done)
- All specs reviewed and approved

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### After Each Task Extraction (Phase 7):
```bash
# Commit ONLY the files for this task
git add src/main/java/${PACKAGE_PATH}/${SERVICE_NAME}.java \
        src/main/java/${PACKAGE_PATH}/${SERVICE_NAME}Contract.java \
        src/test/java/${PACKAGE_PATH}/${SERVICE_NAME}*Test.java \
        ${TARGET_FILE}  # monolith with delegation update

git commit -m "${JIRA_ID} : extract ${TASK_ID} — ${SERVICE_NAME} (${METHOD_COUNT} methods)

$(cat <<EOF
- Extracted: ${METHODS_LIST}
- Created: ${SERVICE_NAME} implements ${SERVICE_NAME}Contract
- Delegation: $(basename $TARGET_FILE) now delegates to ${SERVICE_NAME}
- Tests: ${TESTS_PASSED}/${TESTS_TOTAL} passed

Task: ${TASK_ID}
Fidelity: ${FIDELITY}%
Tests: ${TESTS_PASSED}/${TESTS_TOTAL} passed

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## §5 — Checkpoint Strategy (for Rollback)

**Before each task's Phase 7 (code generation), a checkpoint is saved:**

```bash
# Save checkpoint BEFORE code generation
CHECKPOINT_SHA=$(git rev-parse HEAD)

# Record in state file
jq --arg tid "$TASK_ID" --arg sha "$CHECKPOINT_SHA" --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '.checkpoints += [{"task_id": $tid, "git_sha": $sha, "timestamp": $ts}]' \
  .claude/forge-state.json > tmp && mv tmp .claude/forge-state.json
```

**Checkpoint timeline:**
```
[setup commit] ← checkpoint before T001
     │
   [T001 commit] ← checkpoint before T002
     │
   [T002 commit] ← checkpoint before T003
     │
   [T003 commit]
     │
   [push] ← only if ALL pass quality gate
```

**Rollback resets to the checkpoint:**
```bash
git reset --hard ${CHECKPOINT_SHA}
# Result: T002's commit is gone, T001's commit preserved
```

---

## §6 — Push Strategy

### When: Phase 8 — ONLY after ALL quality gates pass

```
Push Preconditions (ALL must be true):
  ✅ All phases 0-8 completed (no pending/failed)
  ✅ All tasks extracted successfully (T001-T{N})
  ✅ All tests pass (unit + integration)
  ✅ Unified validation APPROVED (fidelity ≥85%, no anti-patterns)
  ✅ No uncommitted changes (working tree clean)
  ✅ Branch has commits ahead of target
```

### Push Execution:
```bash
# 1. Final verification (anti-hallucination)
git status  # must be clean
git log --oneline origin/${TARGET_BRANCH}..HEAD  # show what we're pushing

# 2. Verify remote URL is a known Barclays GitLab instance
REMOTE_URL=$(git config --get remote.origin.url)
if [[ ! "$REMOTE_URL" =~ (gitlab\.barcapint\.com|gitlab\.barclays\.com|app\.gitlab\.barcapint\.com)[:/] ]]; then
    echo "[PUSH:BLOCKED] Remote URL '$REMOTE_URL' not a recognized Barclays GitLab instance"
    echo "  Allowed: gitlab.barcapint.com, app.gitlab.barcapint.com, gitlab.barclays.com"
    exit 1
fi

# 3. Push
git push -u origin ${BRANCH_NAME}

# 4. Create Merge Request
glab mr create \
    --title "${JIRA_ID}: Strangler extraction — ${SERVICE_COUNT} services from $(basename $TARGET_FILE)" \
    --description "$(cat .claude/STRANGLER_MR_DESCRIPTION.md)" \
    --source-branch "${BRANCH_NAME}" \
    --target-branch "${TARGET_BRANCH}" \
    --label "barclays-buk-strangler-refactoring,automated" \
    --assignee "@me"
```

### Why NOT Push After Each Phase (unlike SDK3):

| SDK3 Strategy | Strangler Strategy | Reason |
|---------------|-------------------|--------|
| Push after each phase | Push ONLY at the end | Strangler has rollback — pushing broken state prevents clean `git reset` |
| Forward-only migration | Can roll back any task | Remote must not have rolled-back commits |
| Single sequential run | Multiple task iterations | Each task might fail and retry |
| No rollback needed | Rollback is core feature | Can't rollback what's already pushed |

---

## §7 — No Squashing Policy

**Commits are NEVER squashed.** Each commit represents a distinct, valuable checkpoint:

```bash
# View all strangler commits
git log --oneline --grep="strangler"

# Compare what changed between tasks
git diff T001_SHA..T002_SHA

# Revert a specific task (if needed after push)
git revert T002_SHA
```

**Benefits of linear history:**
- `git bisect` works across extraction tasks (find which task broke something)
- Each commit is independently revertable
- Code review shows clear task boundaries
- Phase markers (`strangler setup`, `strangler specs`, `extract T001`) enable filtering

---

## §8 — MR Description Template

Generated automatically by push agent:

```markdown
## Strangler Pattern Extraction

**JIRA:** {JIRA_ID}
**Target:** `{MonolithClass}` ({total_methods} methods → {extracted} extracted)
**Pattern:** {Orchestrator | Facade | Delegation Chain}
**Services Created:** {count}

### Extraction Summary

| Task | Service | Methods | Fidelity | Tests |
|------|---------|---------|----------|-------|
| T001 | PaymentService | 3 | 91% | 12/12 ✅ |
| T002 | CardsService | 2 | 93% | 8/8 ✅ |
| T003 | WealthService | 4 | 88% | 15/15 ✅ |

### Quality Gate
- ✅ All phases complete (0-8)
- ✅ Validation: APPROVED (avg fidelity: {avg}%)
- ✅ Tests: {total_tests} passed, 0 failed
- ✅ Anti-patterns: None detected

### Discovered Patterns (from API Inspection)
- Architecture: {detected_style}
- DI Style: {detected_di}
- Test Framework: {detected_test}
- Naming: {detected_naming}

### How to Verify
```bash
git checkout {BRANCH_NAME}
./gradlew test  # All tests should pass
```

---
🤖 Generated with [Claude Code](https://claude.ai/claude-code)
```

---

## §9 — Recovery Scenarios

### Scenario A: Task T002 fails validation → rollback
```
Commits: [setup] → [specs] → [T001] → [T002 attempt — ROLLED BACK]
State after rollback: [setup] → [specs] → [T001]
Next: Re-run /strangler-extract T002 (retry from T001 checkpoint)
```

### Scenario B: All tasks done, push fails (network)
```
Commits: [setup] → [specs] → [T001] → [T002] → [T003]
Action: Retry push (commits preserved locally)
Command: git push -u origin ${BRANCH_NAME}
```

### Scenario C: MR rejected by reviewer
```
Commits already pushed to remote.
Action: Make fixes on same branch, add new commits, push again.
Convention: Fix commit: "{JIRA_ID} : strangler fix — address review feedback"
```

### Scenario D: Need to restart entire extraction
```
Action: Delete branch and start fresh
Commands:
  git checkout ${TARGET_BRANCH}
  git branch -D ${BRANCH_NAME}
  rm -rf .claude/forge-state.json .claude/STRANGLER_*
  /strangler-discover ${TARGET_FILE} --jira ${JIRA_ID}
```

---

## §10 — Comparison with SDK3 Strategy

| Aspect | SDK3 Migration | Strangler Extraction |
|--------|---------------|---------------------|
| Branch pattern | `feature/sdk3-migration-{JIRA}` | `feature/{JIRA}-strangler-extract` |
| Commits per run | 8-15 (one per phase) | 2 + N (setup + specs + N tasks) |
| Push frequency | After each phase (backup) | Once at end (rollback safety) |
| Squash policy | Never squash | Never squash |
| Rollback mechanism | Revert to phase commit | `git reset --hard` to checkpoint |
| Commit message | `{JIRA} : Phase N - desc` | `{JIRA} : extract T{NNN} — ServiceName` |
| Co-Authored-By | Required | Required |
| Quality gate | Build + tests pass | 3 gates (phases + tests + validation) |
| MR platform | GitLab (`glab`) | GitLab (`glab`) |
| Forward-only | Yes (migration) | No (can rollback tasks) |

### What We Adopted from SDK3:
- ✅ JIRA ID in every commit (mandatory)
- ✅ Phase markers for filtering (`git log --grep`)
- ✅ No squashing (linear history)
- ✅ `Co-Authored-By` footer
- ✅ Quality gate before push
- ✅ Feature branch naming with JIRA ID
- ✅ Descriptive MR body with summary table

### What We Did Differently:
- ❌ No push after each phase (rollback needs clean local history)
- ❌ No fixed phase numbers in messages (tasks are dynamic T001-T{N})
- ❌ No remote backup mid-workflow (LOCAL until quality gate passes)
- ✅ Added checkpoint SHAs in state file (SDK3 doesn't need this)
- ✅ Added rollback protocol (SDK3 is forward-only)

---

## Agent Self-Check

- [ ] Branch name follows `feature/{JIRA_ID}-strangler-extract` pattern
- [ ] Commits follow format: `{JIRA_ID} : extract T{NNN} — ServiceName (N methods)`
- [ ] Push occurs ONCE at end (after all tasks validated)
- [ ] No squash commits (linear history for bisect/revert)
- [ ] MR targets correct branch (develop or main, auto-detected)
- [ ] Co-Authored-By trailer present on all commits

## Source

**Owner:** preetha.ramaswamy@barclays.com  
**Review cadence:** Quarterly or on major version bump  
**Origin:** Barclays BUK Strangler Refactoring Plugin v3.0 — internal engineering  
**Classification:** Internal
