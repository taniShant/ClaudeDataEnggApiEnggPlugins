---
name: forge-patterns
description: "Runtime reference for the 12 FORGE patterns (Federated Orchestration with Reference-driven Gated Execution). Loaded by FORGE orchestrators at startup to self-validate compliance. Covers thin commands, orchestrator-worker hierarchy, phase-gated execution, stateful resumption, parallel batching, autonomous decision-making, gatekeeper validation, dedicated push agent, scope enforcement, reference-doc-driven design, structured logging, and task-based progress."
user-invocable: false
---

# FORGE Patterns — Runtime Skill

> **Source:** FORGE Standard v1.0 — BUK CIO Marketplace
> **Owner:** MCA Core Engineering
> **Review trigger:** On FORGE standard version change or plugin architecture update
> **Status:** Reviewed

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
Hard gates block on failure (compile, test). Soft gates log and continue (warnings, non-critical checks). Phase numbering: integers.

### Pattern 4: Stateful Resumption
State file at `{PROJECT_PATH}/.claude/{plugin}-state.json`. Phase status values: pending | in_progress | completed | skipped | failed. Resume from first non-completed phase.

### Pattern 5: Parallel Batching
Disjoint file domains (no file in two batches). All batches launched in ONE message with run_in_background: true. 3-8 files per agent.

### Pattern 6: Autonomous Decision-Making
AskUserQuestion blocked in full-automation mode. Auto-decision-agent resolves ambiguity with 7-rule framework.

### Pattern 7: Gatekeeper Validation Agent
Read-only (Read, Glob, Grep, Bash). Returns APPROVED or REJECTED. Minimum 5 red flags. Blocks push if rejected.

### Pattern 8: Dedicated Push Agent
All external I/O (git push, MR creation) isolated here. Anti-hallucination: never assume branch names, remote URLs, or IDs.

### Pattern 9: Scope Enforcement
Every agent has SCOPE BOUNDARY block. Execute ONLY listed steps. No "while I'm here" improvements.

### Pattern 10: Reference-Doc-Driven
domain-reference/SKILL.md contains team's domain knowledge. Phase-gated loading. Never hardcode versions or mappings.

### Pattern 11: Structured Logging
`log()` function with real timestamps via Bash. Mandatory events: START, INFO, WARN, SKIP, ERROR, COMPLETE.

### Pattern 12: Task-Based Progress
TaskCreate/TaskUpdate/TaskList for progress tracking and resume detection. On startup: check existing tasks to determine resume point.

---

## Quality Gate Protocol

All three conditions MUST be true before push:
1. ALL PHASES COMPLETE (state file)
2. VALIDATION AGENT APPROVED (no REJECTED)
3. TESTS GREEN (exit 0)

Gate Decision: (1) AND (2) AND (3) → proceed to push. ELSE → BLOCK.

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] Command file is thin — parse, validate, detect, delegate only
- [ ] Orchestrator delegates domain work to workers, never implements inline
- [ ] All phases have numbered gates (hard or soft) documented
- [ ] State file tracks phase status for resumable execution
- [ ] Workers process disjoint file batches (no file in two batches)
- [ ] Auto-decision-agent handles ambiguity in full-automation mode
- [ ] Validation agent is read-only with minimum 5 red flags
- [ ] Push agent has anti-hallucination protocol for remote operations
- [ ] Every agent has SCOPE BOUNDARY block
- [ ] Domain knowledge loaded from skills, not hardcoded in agents
- [ ] Structured logging with real timestamps at all lifecycle events
- [ ] TaskCreate/TaskUpdate used for progress tracking and resume detection

---

## Areas for Specialist Extension

This skill covers the FORGE pattern baseline. The following areas need extension by the relevant teams:

- **Plugin Authors** — Domain-specific red flags for validation agent, phase-specific gate commands
- **Platform Engineering** — CI/CD integration patterns for FORGE workflows, observability hooks
