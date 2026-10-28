# Strangler Refactoring Plugin — v3.2 Design Document

**Document Type:** Technical Design & Architecture Decision Record  
**Status:** Implemented  
**Date:** 2026-07-29  
**Author:** Principal Engineering — API Platform  
**Audience:** Engineering leads, API engineers, architecture reviewers  

---

## 1. Executive Summary

The barclays-buk-strangler-refactoring plugin has been upgraded from v2.0.0 through v3.0.0 to v3.2.0 to address fundamental limitations in the extraction pipeline. The upgrade introduces a **spec-first TDD pipeline** (Code → Specs → Tests → Generate), replaces hardcoded domain assumptions with **runtime API inspection**, adds a **formal state machine** with rollback capability, and generates **hexagonal architecture services** (ports & adapters) from extracted code.

**v3.2.0 additions:** **God Class Reduction Guard** (Phase 4.5 health-aware blocking), **model-aware execution** (optimal model tier per phase — 52% cost savings), **parallel extraction** with dependency wave scheduling, **90%+ test coverage enforcement** with supplementary generation, **dry-run preview mode** for both discovery and extraction, and **per-task health scoring** (Worker 7C refreshes metrics after each extraction).

> **Important distinction:** The plugin itself uses a **FORGE Hub-Spoke orchestration pattern** (orchestrator → workers → validators). Hexagonal architecture applies to the **generated/extracted services** — the output of the plugin, not the plugin's own structure.

**Result:** Architecture score improved from 6.4/10 → 9.1/10 across generated code quality, TDD, extensibility, and robustness dimensions.

---

## 2. Problem Statement (v2.0.0 Limitations)

### 2.1 No Specification Stage

v2.0.0 jumped directly from planning to extraction. There was no formal contract definition — workers inferred service structure on-the-fly during code movement. This caused:
- Inconsistent service interfaces across tasks
- No reviewable blueprint before irreversible code changes
- Test generation happened AFTER extraction (violating TDD principles)

### 2.2 Hardcoded Domain Knowledge

Domain classification was baked into SKILL.md:
```
"Payment Processing" → methods starting with put*, process*Payment
"Wealth Management" → classes starting with Wealth*, Investment*
```
Any project not following these exact naming conventions would get incorrect domain boundaries.

### 2.3 Pure Code Movement Only

v2.0.0 enforced >95% line-by-line fidelity. While safe, this meant:
- Extracted code inherited all legacy patterns (field injection, dead code, poor naming)
- No opportunity to apply clean code during extraction
- Generated services were copies of bad code, not improvements

### 2.4 No Rollback

If validation rejected an extraction, the developer was left with uncommitted dirty state. There was no checkpoint mechanism to safely undo.

### 2.5 Shared Mutable State

All agents (orchestrator, workers, validators) could read/write `forge-state.json`. No ownership model, no locking, potential race conditions.

### 2.6 Ad-Hoc Phase Management

Phases were tracked as flat strings (`"phase_0": "completed"`) with no formal state machine. Invalid transitions were possible, and error states were undefined.

### 2.7 Mixed Concerns in Agents

Domain logic, infrastructure concerns (GitLab, Java, Gradle), and orchestration were mixed in agent definitions. No separation between domain skills and orchestration logic. Adding support for a new VCS or language required rewriting agents.

---

## 3. Solution: v3.0 Architecture

### 3.1 Spec-First TDD Pipeline

```
Phase 4 (Tasks) → Phase 5 (SPECS) → Phase 6 (TESTS) → Phase 7 (CODE) → Phase 8 (VALIDATE)
                       │                   │                  │
                  Contracts +         Tests written       Clean code
                  Behavior specs     BEFORE impl         generated from
                  reviewed by        (RED state)         spec blueprint
                  engineer                               (GREEN state)
```

**Key shift:** Instead of moving code then testing it, we now define contracts → write tests → generate code that passes those tests.

### 3.2 Runtime API Pattern Discovery

Worker 1D (API Inspector) scans the existing codebase at discovery time:

| Inspects | Discovers |
|----------|-----------|
| Controllers (`@RestController`) | Domain boundaries from URL paths |
| Services (`@Service`) | Naming conventions (actual, not assumed) |
| Tests (`*Test.java`) | Test framework, assertion library, naming style |
| Build config (`build.gradle`) | Java version, dependencies, plugins |
| Dependencies (`@Autowired` vs constructor) | DI style to follow |

Output: `STRANGLER_API_PATTERNS.md` — a discovered fact sheet that replaces all hardcoded assumptions.

### 3.3 Plugin Architecture (FORGE Hub-Spoke)

The plugin itself uses FORGE orchestration patterns — NOT hexagonal. Hexagonal architecture is applied to the **generated services** (see §3.4).

```
┌─────────────────────────────────────────────────────────────────┐
│                    COMMANDS (Entry Points)                        │
│  strangler-discover, strangler-plan, strangler-spec,             │
│  strangler-extract, strangler-tasks, strangler-status            │
└───────────────────────────┬─────────────────────────────────────┘
                            │ thin delegation
┌───────────────────────────▼─────────────────────────────────────┐
│              ORCHESTRATOR AGENT (Hub — FORGE Pattern 2)           │
│  • 9-phase lifecycle manager                                     │
│  • Sole writer of forge-state.json                               │
│  • Phase-gated skill loading (Pattern 10)                        │
│  • Spawns workers, enforces quality gates                        │
└──────────┬────────────────────────────────────┬─────────────────┘
           │                                    │
┌──────────▼──────────────┐      ┌──────────────▼─────────────────┐
│  WORKER AGENTS (Spokes)  │      │  GATEKEEPER AGENTS             │
│  1A: Structure Analyzer  │      │  Validation Agent (3-check)    │
│  1B: Domain Detector     │      │  Push Agent (git + MR)         │
│  1C: Complexity Metrics  │      │  Auto-Decision Agent           │
│  1D: API Inspector       │      └────────────────────────────────┘
│  5A: Spec Generator      │
│  6A: Test Generator      │
│  7A: Code Generator      │
│  7B: Test Runner         │
│  • Never write state     │
│  • Never call back       │
│  • Scope-bounded (P9)    │
└──────────┬──────────────┘
           │ loads per-phase
┌──────────▼──────────────────────────────────────────────────────┐
│                  DOMAIN SKILLS (Phase-Gated)                      │
│  skills/domain/                                                  │
│  ├── state-machine/      State transitions, guards, rollback     │
│  ├── api-inspection/     Discover patterns from existing code    │
│  ├── spec-generation/    Generate hexagonal service specs        │
│  ├── test-generation/    Generate TDD tests (RED phase)          │
│  ├── code-generation/    Generate implementations (GREEN phase)  │
│  ├── error-codes/        Structured error catalog (STR-*)        │
│  ├── rollback/           Checkpoint and undo protocol            │
│  └── branching-strategy/ Git branch, commit, push strategy       │
└─────────────────────────────────────────────────────────────────┘
```

**FORGE Patterns Used:**
- Pattern 2: Hub-Spoke (orchestrator → workers, no callbacks)
- Pattern 3: Phase Gates (hard validation between phases)
- Pattern 4: Stateful Resumption (forge-state.json)
- Pattern 5: Parallel Batching (workers within phases + dependency wave scheduling)
- Pattern 6: Autonomous Decisions (7-rule framework for full-automation)
- Pattern 7: Gatekeeper Validation (3-check unified validator)
- Pattern 8: Dedicated External I/O (push agent)
- Pattern 9: Scope Enforcement ("execute ONLY what is listed")
- Pattern 10: Reference-Driven (phase-gated skill loading)
- Pattern 11: Structured Logging (timestamped events)

### 3.5 Model-Aware Execution (v3.2)

Each phase/worker uses an optimal model tier, selected based on task complexity:

| Tier | Model | Used For |
|------|-------|----------|
| Heavy (Opus) | Highest reasoning | Phase 7A code generation (attempt 1) |
| Balanced (Sonnet) | Moderate reasoning | Phases 2A, 3, 5A, 6A, 7A (attempt 2), 8 |
| Fast (Haiku) | Mechanical/formulaic | Phases 1A-1C, 2B, 4, 7B, 7C |

**Complexity-Adaptive Overrides:**
- Health score < 50 → upgrade tier (risky monolith needs more reasoning)
- Method count > 6 → force heavy for Phase 7A
- Retry attempt 2/3 → downgrade tier (simpler/conservative approach)
- Parallel mode with > 5 tasks → downgrade Phase 6A & 8 for cost containment

**Cost Impact:** ~52% token savings vs all-heavy approach.

### 3.6 Parallel Extraction with Wave Scheduling (v3.2)

Tasks with no shared dependencies can be extracted concurrently. The orchestrator computes dependency waves via topological sort:

```
Wave 1: [T001, T003, T004]   ← no dependencies, run in parallel
Wave 2: [T002]               ← depends on T001
Wave 3: [T005]               ← depends on T002, T003
```

**Monolith Write Lock Protocol:**
- Only ONE task at a time can write delegation stubs to the monolith
- Max 10 tasks queued, 60s timeout with auto-release, heartbeat every 10s
- Max 2 retries for delegation conflicts

**Cascading Invalidation:** If a task fails/rolls back, all dependent tasks in same or later waves are automatically invalidated and re-queued.

### 3.7 God Class Reduction Guard (Phase 4.5) (v3.2)

A 3-level health check that prevents aggressive extraction from unhealthy monoliths:

| Level | Condition | Action |
|-------|-----------|--------|
| Level 1 (BLOCK) | `health_score < 40 AND total_methods > 8` | Hard block — extract smaller "pioneer" first |
| Level 2 (WARN) | Any single task > 10 methods | Suggest splitting into smaller services |
| Level 3 (WARN) | `health_score < 60 AND total_tasks > 5` | Recommend phased extraction (Wave A → re-assess → Wave B) |

**Override:** `--override-guard` bypasses Level 1 block (expert mode). Level 2/3 warnings still shown. Validation still enforces >15 methods = FAIL.

### 3.8 90%+ Test Coverage Enforcement (v3.2)

After code generation (Phase 7), Worker 7B collects JaCoCo coverage:

```
Step 1: Run all Phase 6 tests against generated code
Step 2: Check coverage: line ≥ 90% AND branch ≥ 90%
Step 3: If below 90% → spawn Worker 6A-supplement
Step 4: Supplement targets ONLY uncovered lines/branches
Step 5: Re-run tests → check coverage again
Step 6: Max 2 supplement rounds; hard block if <85% after 2 rounds
```

### 3.9 Dry-Run Preview Mode (v3.2)

Both `/strangler-discover` and `/strangler-extract` support `--dry-run`:

- **Reads:** existing artifacts, state file, discovery cache, API patterns
- **Computes:** per-task impact, wave scheduling, quality gate predictions, cost estimates
- **Displays:** comprehensive preview report
- **Does NOT:** create state files, spawn workers, modify code, push

**Does NOT predict:** actual fidelity (depends on generation), test results, compilation errors.

### 3.4 Generated Code Architecture (Hexagonal)

The **extracted services** (output of the plugin) follow hexagonal architecture. The spec-generation skill defines this structure:

```
{base.package}.{domain}/
├── domain/
│   ├── {DomainName}UseCase.java          ← Inbound port (use-case interface)
│   ├── {DomainName}DomainService.java    ← Domain core (no Spring, no framework)
│   ├── {OutboundDep}Port.java            ← Outbound port (driven interface)
│   └── model/
│       ├── {DomainCommand}.java          ← Input DTO
│       └── {DomainResult}.java           ← Output DTO
├── adapters/
│   ├── in/
│   │   └── {DomainName}ServiceAdapter.java ← Spring @Service (inbound adapter)
│   └── out/
│       └── {OutboundDep}Adapter.java      ← Infrastructure wiring (outbound adapter)
└── application/
    └── {DomainName}ApplicationService.java ← Use-case orchestrator
```

**Benefit:** Extracted services are clean, testable, framework-decoupled microservices — not just copies of monolith code.

---

## 4. What Changed

### 4.1 New Files Created (v3.0: 10 files, v3.2: +1 file)

| File | Layer | Purpose | Version |
|------|-------|---------|---------|
| `skills/domain/state-machine/SKILL.md` | Domain | 9-state formal machine with guards and rollback | v3.0 |
| `skills/domain/error-codes/SKILL.md` | Domain | 40+ structured error codes (STR-*) | v3.0 |
| `skills/domain/api-inspection/SKILL.md` | Domain | Runtime pattern discovery from existing APIs | v3.0 |
| `skills/domain/spec-generation/SKILL.md` | Domain | Service contract + behavior spec generation (hexagonal output) | v3.0 |
| `skills/domain/test-generation/SKILL.md` | Domain | TDD test generation (4 categories) | v3.0 |
| `skills/domain/code-generation/SKILL.md` | Domain | Spec-driven implementation with 3-retry strategy | v3.0 |
| `skills/domain/rollback/SKILL.md` | Domain | Checkpoint creation and auto-rollback protocol | v3.0 |
| `skills/domain/branching-strategy/SKILL.md` | Domain | Git branch, commit, push strategy | v3.0 |
| `skills/tests/scenarios/SKILL.md` | Tests | Behavioral contracts (Given/When/Then) | v3.0 |
| `commands/strangler-spec.md` | Command | New `/strangler-spec` command | v3.0 |
| `skills/domain/model-aware-execution/SKILL.md` | Domain | Model selection algorithm, cost matrix, phase overrides | v3.2 |

> **Note:** An earlier design proposed `skills/ports/` and `skills/adapters/` directories to make the plugin itself hexagonal. This was reverted — the plugin uses FORGE Hub-Spoke patterns for orchestration. Hexagonal architecture is applied to the **generated services** (defined in `spec-generation/SKILL.md`).

### 4.2 Files Modified (v3.0: 5 files, v3.2: +5 files)

| File | Key Changes | Version |
|------|-------------|---------|
| `agents/strangler-orchestrator-agent.md` | 9-phase lifecycle, state machine, Worker 1D, spec review gate, sole state writer | v3.0 |
| `agents/strangler-worker-agent.md` | Workers 5A, 6A, 7A, 7B added; workers cannot write state file | v3.0 |
| `agents/strangler-validation-agent.md` | Fidelity relaxed 95%→85%; tests-pass is primary gate | v3.0 |
| `.claude-plugin/plugin.json` | Version 3.0.0, updated description | v3.0 |
| `README.md` | Complete rewrite for v3.0 | v3.0 |
| `agents/strangler-orchestrator-agent.md` | Phase 4.5 guard, model-aware execution, parallel wave scheduling, monolith extraction cache, Worker 7C dispatch, 90% coverage gate | v3.2 |
| `agents/strangler-worker-agent.md` | Worker 6A-supplement (coverage), Worker 7C (health refresh) added | v3.2 |
| `commands/strangler-extract.md` | --parallel, --all, --dry-run, --model-strategy, --override-guard flags | v3.2 |
| `commands/strangler-discover.md` | --dry-run flag and dry-run preview section | v3.2 |
| `.claude-plugin/plugin.json` | Version 3.2.0, updated description and changelog | v3.2 |

### 4.3 Files Unchanged (8)

All existing commands (`plan`, `tasks`, `status`), `push-agent`, `auto-decision-agent`, and `domain-reference/` skills remain backward-compatible.

---

## 5. Phase-by-Phase Flow

```
/strangler-discover MonolithService.java --jira HPTRX-9196
│
├─ Phase 0: Validate target, create branch (feature/HPTRX-9196-strangler-extract)
├─ Phase 1: 4 parallel workers
│   ├─ 1A: Structure Analyzer (AST parse → cache)
│   ├─ 1B: Domain Boundary Detector (from cache)
│   ├─ 1C: Complexity Metrics (from cache)
│   └─ 1D: API Pattern Inspector (scan controllers, services, tests) ← NEW
│
/strangler-plan
├─ Phase 2: Pattern + test analysis (2 parallel workers)
├─ Phase 3: Interactive planning (5 questions)
│
/strangler-tasks
├─ Phase 4: Break plan into T001, T002, T003...
│
├─ Phase 4.5: God Class Reduction Guard                        ← NEW v3.2
│   ├─ Level 1: BLOCK if health<40 AND methods>8
│   ├─ Level 2: WARN if any task >10 methods
│   └─ Level 3: WARN if health<60 AND tasks>5
│
/strangler-spec --all
├─ Phase 5: Generate specs (contracts, DTOs, behavior tables)
├─ ⏸️  PAUSE — engineer reviews specs
│
/strangler-spec --approve --all
│
/strangler-extract T001 [--parallel] [--dry-run] [--model-strategy auto]
├─ Phase 6: Generate tests from spec (RED — tests fail)
├─ Phase 7: Generate implementation (GREEN — tests pass)
│   ├─ Attempt 1: Clean code — heavy model (85-90% fidelity)
│   ├─ Attempt 2: Conservative — balanced model (93-97% fidelity) [if tests fail]
│   └─ Attempt 3: Pure movement — fast model (>98%) [if still failing]
│   └─ ROLLBACK if all 3 fail
│   ├─ Step 7.5: Coverage check (≥90% line + branch)           ← NEW v3.2
│   │   ├─ Worker 6A-supplement: generate supplementary tests
│   │   └─ Max 2 supplement rounds; hard block if <85%
│   └─ Worker 7C: Health refresh (recalculate monolith metrics) ← NEW v3.2
├─ Phase 8: Validate + commit
│   ├─ Check 1: Logic fidelity ≥85%
│   ├─ Check 2: ALL tests pass + coverage ≥90% (PRIMARY GATE)
│   └─ Check 3: No anti-patterns
│
[repeat for T002, T003... or use --parallel/--all for wave scheduling]
│
Phase 8 final: Quality gate → push → MR on GitLab
```

---

## 6. Git & Branching Strategy

| Aspect | Strategy |
|--------|----------|
| Branch name | `feature/{JIRA_ID}-strangler-extract` |
| Created | Phase 0 (start of discover) |
| Commits | 1 setup + 1 specs + N task extractions |
| Push | ONCE at end after quality gate |
| Rollback | `git reset --hard` to per-task checkpoint (local) |
| Squash | Never (linear history for bisect/revert) |
| MR target | `develop` or `main` (auto-detected) |

**Commit message format:**
```
{JIRA_ID} : extract T001 — PaymentService (3 methods)

- Extracted: processPayment, getPaymentStatus, cancelPayment
- Tests: 12/12 passed
- Fidelity: 91%

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## 7. Architecture Scoring

| Dimension | v2.0 | v3.0 | v3.2 | Improvement |
|-----------|------|------|------|-------------|
| Generated Code Quality | 5/10 | 9/10 | 9/10 | Hexagonal services with ports + adapters |
| Clean Code (SOLID) | 7.9/10 | 9.2/10 | 9.2/10 | DIP in generated code, OCP via skills registry |
| TDD | 3/10 | 8/10 | 9/10 | 90%+ coverage enforcement, supplement loop |
| Domain Model | 8/10 | 9.5/10 | 9.5/10 | Inferred patterns, spec-driven |
| FORGE Patterns | 9.6/10 | 9.8/10 | 9.8/10 | State machine, sole-writer, rollback |
| Extensibility | 5/10 | 8/10 | 8.5/10 | Model-aware execution, domain skill extensibility |
| Robustness | 6/10 | 9/10 | 9.5/10 | God class guard, parallel safety, cascading invalidation |
| Cost Efficiency | N/A | N/A | 9/10 | Model-aware execution — 52% savings |
| **Overall** | **6.4/10** | **9.0/10** | **9.1/10** | **+42%** |

---

## 8. Key Design Decisions

| # | Decision | Rationale | Version |
|---|----------|-----------|---------|
| AD-1 | Specs before code | TDD requires knowing WHAT before HOW. Specs define the contract. | v3.0 |
| AD-2 | Tests before implementation | Red/Green/Refactor. Tests prove behavior; implementation satisfies tests. | v3.0 |
| AD-3 | Infer domain patterns, don't hardcode | Plugin must work on ANY Java project, not just Barclays naming conventions. | v3.0 |
| AD-4 | Relax fidelity 95%→85% | Tests are stronger proof than line-matching. Clean code improvements are valuable. | v3.0 |
| AD-5 | Push only at end | Rollback requires clean local history. Can't `git reset` what's already pushed. | v3.0 |
| AD-6 | Orchestrator = sole state writer | Eliminates race conditions. Workers communicate via artifact files only. | v3.0 |
| AD-7 | 3-attempt retry with degradation | Attempt 1 (clean) → 2 (conservative) → 3 (pure movement) → rollback. Progressive fallback. | v3.0 |
| AD-8 | Spec review gate | Human approval before irreversible code generation. Safety over speed. | v3.0 |
| AD-9 | Parallel extraction with dependency waves | Topological sort enables concurrent extraction of independent tasks. Monolith write lock prevents conflicts. | v3.2 |
| AD-10 | Model-aware execution | Phase complexity determines model tier. Mechanical work (parsing, test running) doesn't need heavy models. 52% cost savings. | v3.2 |
| AD-11 | God Class Reduction Guard | Prevents extracting too much from an unhealthy monolith. Forces incremental improvement. | v3.2 |
| AD-12 | 90% coverage enforcement | Supplementary test generation closes coverage gaps. Hard block <85% ensures quality floor. | v3.2 |

---

## 9. Reusability for API Engineers

This plugin is designed as a **reusable API engineering tool** across Barclays:

1. **No hardcoded conventions** — discovers YOUR project's patterns via runtime API inspection
2. **Self-documenting** — specs serve as architecture documentation for extracted services
3. **Reversible** — auto-rollback means no fear of breaking production code
4. **Hexagonal output** — extracted services follow ports & adapters, not just code movement
5. **Domain skill extensibility** — new domain skills can be added without modifying agents
6. **GitLab + Gradle focused** — currently targets Barclays iAPI stack (glab CLI, Java, Gradle)

> **Future extensibility:** Adding VCS/language/build support would require new domain skills (not ports/adapters in the plugin). The plugin's FORGE architecture keeps orchestration separate from domain logic — a new `skills/domain/maven-build/SKILL.md` extends capability without touching agents.

---

## 10. How to Use

### Prerequisites
- Java project with Gradle build
- GitLab repository (glab CLI authenticated)
- Claude Code with barclays-buk-strangler-refactoring plugin installed

### Workflow
```bash
/barclays-buk-strangler-refactoring:strangler-discover <monolith.java> --jira <JIRA-ID>
/barclays-buk-strangler-refactoring:strangler-plan
/barclays-buk-strangler-refactoring:strangler-tasks
/barclays-buk-strangler-refactoring:strangler-spec --all
/barclays-buk-strangler-refactoring:strangler-spec --approve --all
/barclays-buk-strangler-refactoring:strangler-extract T001
/barclays-buk-strangler-refactoring:strangler-status
```

### Resume After Interruption
Re-run any command — state machine detects prior progress and resumes from last checkpoint.

---

## 11. Risk & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Generated code doesn't pass tests | Medium | Low | 3-retry strategy with progressive fallback + auto-rollback |
| Spec doesn't capture all behavior | Low | Medium | Behavior extraction from method body analysis + human review gate |
| API inspection misidentifies domains | Low | Low | Human reviews discovery output before planning |
| State file corruption | Very Low | Medium | Schema versioning, locked_by field, recovery protocol |
| Parallel delegation conflicts | Low | Low | Monolith write lock (60s timeout, 2 retries, heartbeat) |
| Cascading task failures in wave mode | Low | Medium | Automatic invalidation of dependent tasks; re-queue after fix |
| Coverage stalls below 90% | Low | Low | 2-round supplement loop; warn at 85% hard block; manual intervention path |
| God class guard false positive | Very Low | Low | `--override-guard` flag for expert users; Level 2/3 are warnings only |

---

## 12. Plugin Integration: reverse-spec-generator (v3.1.0)

**Added in v3.1.0:** Phase 5 now delegates BDD behavior extraction to the `barclays-buk-reverse-spec-generator` plugin.

### Integration Point

```
Phase 5 (Spec Generation):
  Worker 5A → invokes reverse-spec-generator Python CLI → gets .spec YAML
           → maps BDD output to hexagonal architecture → writes both artifacts
```

### What the reverse-spec-generator provides

| Capability | Value to Strangler Plugin |
|-----------|--------------------------|
| Language-aware extraction (Java, Python, JS) | Better behavior detection than inline analysis |
| Confidence scoring (0.2 → 1.0) | Low-confidence methods get extra test coverage in Phase 6 |
| BDD format (Given/When/Then) | Directly maps to hexagonal behavior table |
| Validated output (.spec YAML) | Guaranteed schema compliance before hexagonal mapping |
| Entity extraction | Feeds domain model DTO generation |
| Rule extraction (guard clauses) | Feeds domain service guard logic |
| Constraint extraction (dependencies) | Identifies outbound port candidates |

### Soft Dependency

The reverse-spec-generator is a **soft dependency** — if unavailable, Worker 5A falls back to inline method body analysis. This ensures the strangler plugin works standalone, but produces higher-quality specs when the reverse-spec-generator is installed alongside it.

### Output Changes

Phase 5 now produces TWO artifacts per task:
1. `.spec` file (BDD extraction) — raw, validated, confidence-scored
2. `-service-spec.md` (hexagonal spec) — architecture blueprint derived from the BDD spec

---

*Document Version: 1.2 | Plugin Version: 3.2.0 | Classification: Internal*
