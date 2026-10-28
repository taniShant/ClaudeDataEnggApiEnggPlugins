# barclays-buk-strangler-refactoring-strangler-extract-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-strangler-refactoring-strangler-extract-v1` |
| Plugin name | `barclays-buk-strangler-refactoring` |
| Component type | skill-user-only |
| Owner | Preetha Ramaswamy |
| Action scope | local-modification |
| Invocation mode | user-only |
| Installation / release | /plugin install barclays-buk-strangler-refactoring@barclays-cio-buk |
| Native command | `/barclays-buk-strangler-refactoring:strangler-extract` |
| Skill name | `strangler-extract` |

## Description

Execute extraction tasks with automatic validation. Supports single, parallel, and batch modes.

## When to use

Use when strangler-pattern task definitions already exist (Phases 1–3 complete) and you need to execute the actual extraction of methods from a monolith god class into new microservices, either one task at a time, in parallel waves, or as a full batch — this command does NOT perform extraction itself but orchestrates it by spawning worker agents, and is NOT a substitute for the preceding discover/plan/tasks workflow.

## Inputs

- TASK_ID (positional, required unless --all): One or more task IDs in format T001, T002, etc., referencing entries in `.claude/STRANGLER_TASKS.md`
- --parallel (optional flag): Enable concurrent extraction of independent tasks, automatically partitioned into dependency waves
- --all (optional flag): Extract all remaining tasks respecting dependency order; implies --parallel for independent tasks
- --dry-run (optional flag): Preview the full extraction plan (impact analysis, wave scheduling, quality gate predictions, cost estimates) without modifying any files, state, or spawning workers
- --model-strategy (optional, default: auto): Model selection for worker agents — `auto` (Sonnet/Opus split, ~34% savings), `heavy` (Opus everywhere), or `balanced` (Sonnet everywhere)
- --override-guard (optional flag): Bypass the God Class Reduction Guard Level 1 health score block; Level 2/3 warnings and Phase 8 validation still apply
- --skip-validation (optional flag): Skip validation hooks (testing use only)
- --jira JIRA_ID (optional): JIRA ticket ID; if omitted, read from `.claude/forge-state.json`

## Preconditions

- `.claude/forge-state.json` must exist and show `phase_3` as `completed` (i.e., `/strangler-discover`, `/strangler-plan`, and `/strangler-tasks` have all been run successfully in order)
- `.claude/STRANGLER_TASKS.md` must exist and contain the requested TASK_ID(s) with valid entries including DEPENDS_ON fields
- `.claude/STRANGLER_DISCOVERY_CACHE.json` must exist (used for method body lines, dependency lists, branch counts in dry-run and by downstream workers)
- `.claude/STRANGLER_SPECS/SPEC_MANIFEST.json` must exist (used for service name resolution and fidelity/test predictions)
- For --parallel or --all: DEPENDS_ON fields in STRANGLER_TASKS.md must be parseable to build a valid DAG (no circular dependencies)

## Expected outputs

- In **dry-run mode**: a read-only impact report printed to stdout covering per-task method extraction details, estimated fidelity/coverage, dependency wave schedule, monolith delegation changes, quality gate predictions, and model-aware cost estimates — no files or state are modified
- In **execution mode**: spawns the orchestrator which delegates to worker agents to perform Phase 6 (test generation), Phase 7 (code generation + test execution), and Phase 8 (validation) for each task; the orchestrator coordinates file writes, state updates in `.claude/forge-state.json`, and batched validation
- In parallel/batch mode: outputs a wave execution plan (e.g., Wave 1: T001, T003, T004 → Wave 2: T002 → Wave 3: T005) before spawning workers per wave

## Exclusions

- Does NOT implement extraction logic inline — all code generation, test generation, and file modification is delegated to the orchestrator and its worker agents
- Does NOT run validators directly — the orchestrator coordinates batched validation in Phase 8
- Does NOT modify source files itself — the orchestrator coordinates all writes
- Does NOT perform discovery, planning, or task decomposition (those are handled by `/strangler-discover`, `/strangler-plan`, and `/strangler-tasks` respectively)
- Does NOT remove methods from the monolith — method bodies are replaced with delegation one-liners but preserved for backward compatibility
- Does NOT execute git operations directly (those are orchestrator-managed)

## Verification

In dry-run mode, verify the impact report renders completely with per-task fidelity, coverage, and quality gate predictions all showing expected PASS status. In execution mode, check `.claude/forge-state.json` for updated phase completion status for each extracted task, confirm that new service files and test files were created under the expected paths referenced in SPEC_MANIFEST.json, and verify that the orchestrator's Phase 8 validation reports all quality gates (logic fidelity ≥85%, test coverage ≥90%, no god-service anti-patterns with >15 methods) as APPROVED.
