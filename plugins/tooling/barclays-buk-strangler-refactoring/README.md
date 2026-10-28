# Strangler Refactoring Plugin — v3.2

Spec-first strangler pattern refactoring with TDD pipeline. Inspects existing APIs to discover domain patterns, generates service specifications, writes tests first (RED), generates clean implementations (GREEN), and validates with quality gates. Supports **parallel extraction** with dependency wave scheduling, **model-aware execution** (Sonnet/Opus split, 34% cost savings), **90%+ test coverage enforcement**, and **dry-run preview mode**. Java-focused.

## Pipeline: Code → Specs → Tests → Generate

```
┌──────────┐     ┌──────────┐     ┌──────────────┐     ┌────────────┐     ┌──────────┐
│  INSPECT  │ ──→ │   SPEC   │ ──→ │  TESTS FIRST │ ──→ │  GENERATE  │ ──→ │ VALIDATE │
│  Existing │     │  Generate │     │  (TDD RED)   │     │  Clean Code│     │  + Push  │
│  APIs     │     │  Contracts│     │              │     │  (GREEN)   │     │          │
└──────────┘     └──────────┘     └──────────────┘     └────────────┘     └──────────┘
```

**🛡️ GUARANTEES:**
- Public method signatures remain 100% unchanged
- Behavior validated by tests BEFORE and AFTER extraction
- Domain patterns discovered from YOUR code (not hardcoded assumptions)
- Auto-rollback if validation fails — codebase never left broken
- 90%+ test coverage enforced per extracted service
- God class guard prevents aggressive extraction from unhealthy monoliths

## Quick Start

```bash
# 1. Preview what discovery will do (optional)
/barclays-buk-strangler-refactoring:strangler-discover src/main/java/.../MonolithService.java --jira HPTRX-9196 --dry-run

# 2. Discover monolith + inspect existing API patterns
/barclays-buk-strangler-refactoring:strangler-discover src/main/java/.../MonolithService.java --jira HPTRX-9196

# 3. Create extraction plan (interactive)
/barclays-buk-strangler-refactoring:strangler-plan

# 4. Break plan into tasks
/barclays-buk-strangler-refactoring:strangler-tasks

# 5. Generate service specifications
/barclays-buk-strangler-refactoring:strangler-spec --all

# 6. Review and approve specs
/barclays-buk-strangler-refactoring:strangler-spec --review
/barclays-buk-strangler-refactoring:strangler-spec --approve --all

# 7. Extract single task (runs TDD pipeline: tests → code → validate)
/barclays-buk-strangler-refactoring:strangler-extract T001

# 8. Or extract ALL tasks in parallel (dependency-aware wave scheduling)
/barclays-buk-strangler-refactoring:strangler-extract --all --parallel

# 9. Preview extraction impact without changes
/barclays-buk-strangler-refactoring:strangler-extract --all --dry-run

# 10. Check progress
/barclays-buk-strangler-refactoring:strangler-status
```

## Commands

### /strangler-discover

Analyze a monolith and discover domain patterns from existing APIs.

```bash
/barclays-buk-strangler-refactoring:strangler-discover TARGET_FILE [--jira JIRA_ID] [--quick] [--dry-run]
```

| Flag | Description |
|------|-------------|
| `--jira JIRA_ID` | JIRA ticket ID for tracking (auto-detected from branch if omitted) |
| `--quick` | Medium thoroughness — faster, less detail |
| `--dry-run` | Preview discovery scope without executing (no state file, no workers, no artifacts) |

**What it does (Phase 0-1):**
- Parses monolith structure (methods, dependencies, complexity)
- Inspects existing controllers, services, tests to discover naming conventions, DI style, test framework
- Produces: `STRANGLER_DISCOVERY.md` + `STRANGLER_API_PATTERNS.md`
- Creates feature branch: `feature/{JIRA_ID}-strangler-extract`

### /strangler-plan

Create a phased extraction plan. Asks 5 interactive questions (skip with `--skip-questions`).

```bash
/barclays-buk-strangler-refactoring:strangler-plan [--skip-questions] [--jira JIRA_ID]
```

### /strangler-tasks

Break the plan into executable tasks (T001, T002...).

```bash
/barclays-buk-strangler-refactoring:strangler-tasks
```

### /strangler-spec

Generate, review, and approve service specifications.

```bash
/barclays-buk-strangler-refactoring:strangler-spec --all                    # Generate specs for all tasks
/barclays-buk-strangler-refactoring:strangler-spec T001                     # Generate spec for one task
/barclays-buk-strangler-refactoring:strangler-spec --review                 # Display specs for review
/barclays-buk-strangler-refactoring:strangler-spec --approve T001           # Approve specific spec
/barclays-buk-strangler-refactoring:strangler-spec --approve --all          # Approve all specs
/barclays-buk-strangler-refactoring:strangler-spec --reject T001 --reason "Split processPayment"
```

**Specs include:** Contract interface, DTOs, behavior specification (Given/When/Then), error contracts, dependency list, delegation pattern.

### /strangler-extract

Execute extraction for a task (or all tasks). Triggers the full TDD pipeline:

```bash
/barclays-buk-strangler-refactoring:strangler-extract TASK_ID [flags]
/barclays-buk-strangler-refactoring:strangler-extract --all [flags]
```

| Flag | Description |
|------|-------------|
| `--parallel` | Extract independent tasks concurrently within dependency waves |
| `--all` | Extract all remaining tasks (implies `--parallel` for independent tasks) |
| `--dry-run` | Preview per-task impact, wave scheduling, cost estimate — no execution |
| `--model-strategy <auto\|heavy\|balanced>` | Force model tier (default: `auto` — Sonnet/Opus split) |
| `--override-guard` | Bypass Level 1 God Class Reduction Guard block (expert mode) |

**What happens internally:**
1. Phase 6: Generate tests from spec (RED — tests fail, no impl yet)
2. Phase 7: Generate clean service implementation (GREEN — tests pass)
3. Step 7.5: Coverage check (≥90% line + branch; supplement if needed)
4. Worker 7C: Health refresh (recalculate monolith metrics)
5. Phase 8: Validate (fidelity ≥85%, tests pass + coverage, no anti-patterns)
6. Commit if approved, rollback if rejected

### /strangler-status

View current progress, state machine status, health scores, and next steps.

```bash
/barclays-buk-strangler-refactoring:strangler-status
```

## Architecture (FORGE Hub-Spoke)

The plugin uses **FORGE orchestration patterns** (hub-spoke, phase gates, stateful resumption).
Hexagonal architecture applies to the **generated services** — the extracted microservices, not the plugin itself.

```
Plugin Structure:
├── commands/                    ← ENTRY POINTS (thin delegation)
├── agents/                      ← FORGE AGENTS
│   ├── orchestrator (Hub)       Sole state writer, 9-phase lifecycle, model-aware
│   ├── workers (Spokes)         Scope-bounded, never call back
│   ├── validator (Gatekeeper)   3-check quality gate + 90% coverage
│   ├── push-agent              Git push + MR creation
│   └── auto-decision-agent     7-rule autonomous decision framework
└── skills/
    ├── domain/                  ← DOMAIN SKILLS (phase-gated loading)
    │   ├── state-machine/       State transitions, guards, rollback
    │   ├── error-codes/         Structured error catalog (STR-*)
    │   ├── api-inspection/      Discover patterns from existing code
    │   ├── spec-generation/     Generate hexagonal service specs
    │   ├── test-generation/     Generate TDD tests (RED phase)
    │   ├── code-generation/     Generate implementations (GREEN phase)
    │   ├── rollback/            Checkpoint and undo protocol
    │   ├── branching-strategy/  Git branch, commit, push strategy
    │   └── model-aware-execution/  Model selection algorithm & cost matrix
    ├── tests/scenarios/         ← BEHAVIORAL TEST CONTRACTS
    │   └── SKILL.md             Given/When/Then scenarios
    └── domain-reference/        ← LEGACY (validation rules, examples)
```

## Agents

| Agent | Role | FORGE Pattern |
|-------|------|---------------|
| `strangler-orchestrator-agent` | Hub coordinator — 9-phase lifecycle, sole state writer, model-aware dispatcher, wave scheduler | Pattern 2, 4 |
| `strangler-worker-agent` | Scope-bounded workers (1A-1D, 5A, 6A, 6A-supplement, 7A, 7B, 7C, 8) | Pattern 5, 9 |
| `strangler-validation-agent` | 3-check gatekeeper (fidelity + tests + coverage + anti-patterns) | Pattern 7, 8 |
| `strangler-push-agent` | Git push + MR with anti-hallucination protocol | Pattern 8 |
| `auto-decision-agent` | Autonomous decisions in full-automation mode (7-rule framework) | Pattern 6 |

## 9-Phase Lifecycle

| Phase | Name | Workers | Model Tier | Output |
|-------|------|---------|------------|--------|
| 0 | Setup & Validation | 1 | Sonnet | State file, branch created |
| 1 | Discovery | 4 parallel (1A-1D) | Sonnet | DISCOVERY.md + API_PATTERNS.md |
| 2 | Analysis | 2 parallel (2A-2B) | Sonnet | ANALYSIS.md |
| 3 | Planning | 1 (interactive) | Sonnet | PLAN.md |
| 4 | Task Breakdown | 1 | Sonnet | TASKS.md |
| **4.5** | **God Class Reduction Guard** | — | — | **Block/Warn/Pass** |
| 5 | Spec Generation | 1 per task | Sonnet | STRANGLER_SPECS/ |
| 6 | Test Generation (RED) | 1 per task + supplement | Sonnet | STRANGLER_TESTS/ |
| 7 | Code Generation (GREEN) | 7A + 7B + 7C per task | Opus→Sonnet→Sonnet | New services + delegation |
| 8 | Validation + Push | 1 validator + push | Sonnet | MR on GitLab |

## Git Strategy

```
main/develop ─────────────────────────────────────────────→
     │
     └─→ feature/{JIRA_ID}-strangler-extract
           │            │            │            │
         commit       commit       commit       push + MR
         [setup]      [specs]      [T001]       (quality gate)
```

- **Branch:** `feature/{JIRA_ID}-strangler-extract` (created Phase 0)
- **Commits:** Setup → Specs → One per task extraction
- **Push:** ONCE at end (after all tasks pass validation)
- **Rollback:** `git reset --hard` to per-task checkpoint (local only)
- **No squashing:** Linear history for `git bisect` and per-task revert

## Validation Guarantees

### Logic Fidelity (≥85%)
- Clean code improvements allowed (up to 15% delta)
- Guard clauses, constant extraction, better naming = OK
- Conditional logic changes, exception type changes = BLOCKED
- **Tests are the primary proof of behavior preservation**

### TDD Behavior (PRIMARY GATE)
- Tests generated BEFORE implementation (Phase 6)
- Implementation MUST pass all tests (Phase 7)
- 4 test categories: Contract, Behavior, Integration, Error Path
- No mock-only tests (behavior always asserted)

### Test Coverage (≥90%)
- JaCoCo line coverage ≥ 90% AND branch coverage ≥ 90%
- Worker 6A-supplement generates additional tests for uncovered lines/branches
- Max 2 supplement rounds; hard block if <85% after supplementation
- Coverage collected per extracted service, not cumulative

### Anti-Pattern Detection
- No god service (≤15 methods)
- No new external dependencies
- No circular dependencies
- Single responsibility maintained
- Coupling ≤5 injected dependencies (warn at 5-10, fail >10)

## Model-Aware Execution

Each worker uses an optimal model tier, selected automatically (override with `--model-strategy`):

| Tier | Model | Used For | Cost |
|------|-------|----------|------|
| Heavy (Opus) | Highest reasoning | Phase 7A code gen, complex specs (health < 50) | $$$ |
| Balanced (Sonnet) | Reliable analysis | All other phases — discovery, planning, tests, validation, push | $$ |

> **Note:** Haiku (Fast tier) removed based on pilot feedback — produced incorrect results on code parsing and analysis tasks.

**Adaptive overrides:**
- Health score < 50 → upgrade to Opus (risky monolith needs deeper reasoning)
- Method count > 6 → force Opus for 7A
- Retry attempt 2/3 → fall back to Sonnet

**Result:** ~34% token savings vs all-Opus approach, with no quality compromise.

## Parallel Extraction

Tasks with no shared dependencies execute concurrently via topological wave scheduling:

```
Wave 1: [T001, T003, T004]   ← independent, run in parallel
Wave 2: [T002]               ← depends on T001
Wave 3: [T005]               ← depends on T002, T003
```

**Monolith Write Lock:** Only ONE task at a time writes delegation stubs (60s timeout, heartbeat every 10s, max 2 retries).

**Cascading Invalidation:** If a task fails/rolls back, all dependent tasks in same/later waves are automatically invalidated and re-queued.

**Usage:**
```bash
/barclays-buk-strangler-refactoring:strangler-extract --all --parallel
```

## God Class Reduction Guard

Phase 4.5 runs a 3-level health check preventing aggressive extraction:

| Level | Condition | Action |
|-------|-----------|--------|
| Level 1 (BLOCK) | `health < 40 AND total_methods > 8` | Hard block — extract smaller "pioneer" first |
| Level 2 (WARN) | Any single task > 10 methods | Suggest splitting into smaller services |
| Level 3 (WARN) | `health < 60 AND total_tasks > 5` | Recommend phased extraction (Wave A → re-assess → Wave B) |

**Override:** `--override-guard` bypasses Level 1 (expert mode). Validation still enforces >15 methods = FAIL.

## Key Differences from v2.0

| Aspect | v2.0 | v3.0 | v3.2 |
|--------|------|------|------|
| Extraction approach | Pure code movement | Spec-driven generation | Spec-driven + parallel waves |
| Domain knowledge | Hardcoded in SKILL.md | Inferred from API inspection | Same |
| Tests | Generated AFTER code | Generated BEFORE code (TDD) | TDD + 90% coverage enforcement |
| Fidelity threshold | >95% (strict) | ≥85% (clean code allowed) | Same |
| Validation primary gate | Line-by-line matching | Tests pass | Tests pass + coverage ≥90% |
| Phases | 6 | 9 | 9 + Phase 4.5 guard |
| Rollback | None | Auto-rollback on failure | Same + cascading invalidation |
| State management | Ad-hoc JSON | Formal state machine | Same + wave state tracking |
| Error handling | Free-form strings | Structured codes (STR-*) | Same + parallel error codes |
| Architecture | Monolithic skills | FORGE Hub-Spoke + hexagonal output | Same |
| Model selection | N/A | N/A | Model-aware Sonnet/Opus split (34% savings) |
| Parallel support | N/A | N/A | Dependency wave scheduling |
| Preview mode | N/A | N/A | --dry-run for discover & extract |
| Health monitoring | N/A | N/A | Per-task health refresh (Worker 7C) |

## Resume After Interruption

Re-run any command — the plugin detects prior state and resumes:

```bash
/barclays-buk-strangler-refactoring:strangler-discover src/main/java/.../MonolithService.java
# Detects state file, skips completed phases, resumes from last checkpoint
```

State file schema v2 supports migration from v1 (auto-detected on resume).

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| STR-0F001 "Target file not found" | Path wrong | Check file path |
| STR-0F002 "Not source code" | Non-.java file | Provide .java file |
| STR-5E001 "Spec generation failed" | Methods not in source | Verify task assignments |
| STR-6E003 "JaCoCo not configured" | No coverage tool | Add JaCoCo to `build.gradle` |
| STR-7E002 "Tests fail after 3 retries" | Can't satisfy spec | Auto-rollback, modify spec |
| STR-8E001 "Validation REJECTED" | Fidelity <85% or anti-patterns | Auto-rollback, review extraction |
| STR-PE003 "Empty wave detected" | Circular dependency in task graph | Fix DEPENDS_ON relationships |
| STR-PE004 "Delegation conflict" | Write lock contention (parallel) | Auto-retry (max 2); reduce parallelism |
| "Phase N not complete" | Sequential phases | Complete earlier phases first |
| "Guard Level 1 BLOCKED" | Unhealthy monolith | Extract smaller pioneer first, or use `--override-guard` |

## Quality Score

**`/test-plugin` score:** 100/100 — PRODUCTION READY

Validated 2026-08-06 against plugin-testing-toolkit v1.0.1. All structure, content, schema, and BUK compliance checks pass.

## Pilot Summary

**Pilot validated 2026-08-06** — real user extraction sessions on production monoliths.

**Pilot users (3):**
- Naveen Kumar Reddy (naveen.kumarreddy@barclays.com) — COP01 opcode extractions from Fat Gateway to DAF API ([DIGICAW-4782](https://estjira.barcapint.com/browse/DIGICAW-4782))
- Srushti Jambhulkar (srushti.jambhulkar@barclays.com) — C001A opcode feature flag complexity reductions, 43% God class optimisations from 31k lines of code ([DIGICAW-5122](https://estjira.barcapint.com/browse/DIGICAW-5122))
- Anshul Chouhan (anshulsingh.chouhan@barclays.com) — C001A opcode feature flag complexity reductions, 43% God class optimisations from 31k lines of code ([DIGICAW-5122](https://estjira.barcapint.com/browse/DIGICAW-5122))

### Strengths Observed

- Strong strangler pattern identification and migration recommendations
- Generates phased migration plans instead of big-bang rewrites
- Modernizes Experience API ↔ Process API interactions effectively
- Produces meaningful service decomposition and simplifies target architectures
- Handles both simple and complex APIs with practical implementation roadmaps
- Significantly reduces migration effort and accelerates modernization

### Improvements Fed Back and Implemented

| Feedback | Resolution |
|----------|-----------|
| God Class Reduction Guard — prioritize monolith extraction before decomposition | ✅ Implemented (Phase 4.5 health-aware blocking) |
| Per-Task Health Scoring — refresh metrics after each extraction | ✅ Implemented (Worker 7C) |
| Dry-Run Mode — preview impact before changes | ✅ Implemented (`--dry-run` for discover & extract) |
| Model-Aware Execution — optimal model per phase | ✅ Implemented (Sonnet/Opus split, 34% cost savings) |
| Parallel Extraction — independent services extracted concurrently | ✅ Implemented (dependency wave scheduling) |
| 90%+ Test Coverage — generated tests must meet coverage gate | ✅ Implemented (JaCoCo line + branch ≥90%) |
| Multi-agent Sonnet/Opus coordination | ✅ Validated (Haiku removed — produced incorrect results) |

## Version

- **Plugin Version:** 3.2.0
- **Author:** Preetha Ramaswamy (preetha.ramaswamy@barclays.com)
- **Contributors:** Rajshree Jha (rajshree.jha@barclays.com)
- **Language Support:** Java (Spring Boot, JUnit 5, Gradle)
- **VCS Support:** GitLab (via glab CLI)
- **Dependency:** barclays-buk-reverse-spec-generator (soft — Phase 5 BDD extraction)
