---
name: forge-patterns
description: "Runtime reference for the 12 FORGE patterns (Federated Orchestration with Reference-driven Gated Execution). Loaded by TRACER orchestrator at startup to self-validate compliance."
user-invocable: false
---

# FORGE Patterns — Runtime Skill

> **Source:** FORGE Standard v1.0 — BUK CIO Marketplace
> **Owner:** Barclays BUK Digital Channels
> **Review trigger:** On FORGE standard version change or plugin architecture update
> **Status:** Reviewed

---

## Source Attribution

**Primary sources:**
- FORGE Standard v1.0 — BUK CIO Marketplace (Federated Orchestration with Reference-driven Gated Execution)
- `barclays-buk-standards` plugin architecture principles

**Training knowledge applied:**
- Orchestrator-worker hierarchy patterns from distributed systems design
- Phase-gated execution patterns from workflow engineering
- Gatekeeper/validator patterns from enterprise integration

**Known limitations:**
- Pattern 5 (Parallel Batching) requires human judgment on domain boundary selection — the skill defines the pattern, not the boundary
- Pattern 6 (Autonomous Decision-Making) covers common cases; novel ambiguity types may need additional decision rules
- This skill is a runtime copy of the FORGE standard; if FORGE Standard is updated, this skill must be manually resynced

---

## Quick Start

Load this skill in your orchestrator's MANDATORY FIRST STEP alongside other core skills. The most-used patterns are P1 (Thin Command) and P2 (Orchestrator-Worker) — verify your implementation against both before any phase gate.

```markdown
# In your orchestrator frontmatter:
skills:
  - barclays-buk-tracer:forge-patterns
  - barclays-buk-tracer:tracer_core

# Pattern 1 check — is your command thin?
# ✅ Command parses flags, delegates to orchestrator
# ❌ Command contains domain logic or writes files

# Pattern 2 check — is your hierarchy acyclic?
# ✅ orchestrator → spec-agent → (reads only)
# ❌ spec-agent → orchestrator (cycle — forbidden)

# Pattern 4 check — are phase gates hard where required?
# ✅ if [ -z "${SPEC_PATH}" ]; then tracer_log "ABORT" "spec_path missing"; exit 1; fi
# ❌ continuing silently when a hard gate fails
```

---

## Quick Reference: The 12 FORGE Patterns

| # | Pattern | One-Line Rule |
|---|---------|--------------|
| 1 | Thin Command | Parse/validate/detect/delegate only. Zero domain logic inline. |
| 2 | Orchestrator-Worker Hierarchy | One hub, many spokes. Workers never call orchestrators. No cycles. |
| 3 | Phase-Gated Execution | Numbered sequential phases. Hard gates block. Soft gates log-and-continue. |
| 4 | Stateful Resumption | State file or TaskCreate/TaskUpdate as single source of truth. |
| 5 | Parallel Batching | Disjoint file domains. All batches of a phase in ONE message. 3-8 files per agent. |
| 6 | Autonomous Decision-Making | AskUserQuestion is FORBIDDEN in full automation. 7-rule decision framework. |
| 7 | Gatekeeper Validation Agent | Read-only, N red flags, APPROVED/REJECTED verdict. Blocks push if rejected. |
| 8 | Dedicated Push Agent | All external I/O isolated here. Anti-hallucination protocol mandatory. |
| 9 | Scope Enforcement | Every agent: "Execute ONLY what is listed. NOTHING ELSE." |
| 10 | Reference-Doc-Driven (Skills) | >=2 skills per plugin. Phase-gated loading. Never hardcode domain values. |
| 11 | Structured Logging | `[timestamp] [AGENT:name] EVENT: action`. Real timestamps only. |
| 12 | Task-Based Progress | TaskCreate/TaskUpdate/TaskList for progress visibility and resume detection. |

---

## Pattern Details

### Pattern 1: Thin Command
A command file does exactly four things: parse arguments, validate inputs, detect context, delegate to orchestrator via Task tool. Zero domain logic inline.

### Pattern 2: Orchestrator-Worker Hierarchy
One hub, many spokes. Workers report results upward. Orchestrator never delegates to another orchestrator. Workers never call back to orchestrator.

### Pattern 3: Phase-Gated Execution
Hard gates block on failure. Soft gates log and continue. Phase numbering: integers (0, 1, 2, ..., N). Each phase labelled with gate type.

### Pattern 4: Stateful Resumption
State file at `{PROJECT_PATH}/.claude/tracer-state.json`. Phase status values: `pending | in_progress | completed | skipped | failed`. Resume from first non-completed phase.

### Pattern 5: Parallel Batching
Disjoint file domains (no file in two batches). All batches launched in ONE message with `run_in_background: true`. 3-8 files per agent.

### Pattern 6: Autonomous Decision-Making
`AskUserQuestion` FORBIDDEN in full-automation mode. `auto-decision-agent` resolves ambiguity with 7-rule decision framework.

### Pattern 7: Gatekeeper Validation Agent
Read-only (Read, Glob, Grep, Bash). Returns `APPROVED` or `REJECTED`. Minimum 5 red flags. Blocks file write/push if rejected.

### Pattern 8: Dedicated Push/Writer Agent
All external I/O (file writes, git operations) isolated here. Anti-hallucination: never assume paths, branch names, or IDs — verify before use.

### Pattern 9: Scope Enforcement
Every agent has `## SCOPE BOUNDARY (NON-NEGOTIABLE)` block. Execute ONLY listed steps. No "while I'm here" improvements.

### Pattern 10: Reference-Doc-Driven
Domain knowledge lives in skills. Phase-gated loading. Never hardcode versions, schemas, or domain values in agent logic.

### Pattern 11: Structured Logging
`log()` function with real timestamps via Bash `$(date)`. Mandatory events: START, INFO, WARN, SKIP, ERROR, COMPLETE.

### Pattern 12: Task-Based Progress
`TaskCreate`/`TaskUpdate`/`TaskList` for progress tracking and resume detection. On startup: check existing tasks to determine resume point.

---

## Quality Gate Protocol

All conditions MUST be true before file-writer agent proceeds:
1. **ALL PHASES COMPLETE** — state file shows all phases `completed` or `skipped`
2. **VALIDATION AGENT APPROVED** — no `REJECTED` verdict

Gate: (1) AND (2) → proceed. ELSE → BLOCK.

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] Command file is thin — parse, validate, detect, delegate only
- [ ] Orchestrator delegates domain work to workers, never implements inline
- [ ] All phases have numbered gates (hard or soft) documented
- [ ] State file tracks phase status for resumable execution
- [ ] `auto-decision-agent` handles ambiguity — no `AskUserQuestion` in pipeline
- [ ] Validation agent is read-only with minimum 5 red flags
- [ ] File-writer agent has anti-hallucination protocol for all write operations
- [ ] Every agent has `SCOPE BOUNDARY` block
- [ ] Domain knowledge loaded from skills, not hardcoded in agents
- [ ] Structured logging with real `$(date)` timestamps at all lifecycle events
- [ ] `TaskCreate`/`TaskUpdate` used for progress tracking and resume detection
