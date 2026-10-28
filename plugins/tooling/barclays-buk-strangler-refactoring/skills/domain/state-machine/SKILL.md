---
name: state-machine
Source: Barclays BUK Strangler Refactoring Plugin v3.2
Owner: preetha.ramaswamy@barclays.com
Review trigger: Quarterly or on major version bump
user-invocable: false
Status: Published
---
> **Source:** Strangler Refactoring Plugin v3.2 — State Machine — Phase Lifecycle and Transitions (internal)
> **Owner:** Preetha Ramaswamy / BUK CIO Engineering
> **Review trigger:** When new phases or state transitions are added
> **Status:** Published
> Source documents are Internal — Restricted.


## Quick Start

```
Phase: All (orchestrator state management)
Worker: Orchestrator (sole state writer)
Load: orchestrator loads state-machine for transition validation
Use: Validate state transitions, enforce guards, manage machine_state field
Model: N/A (lookup/validation logic, not generation)
```

# State Machine — Strangler Refactoring Pipeline

> **Purpose:** Formal state machine governing the 9-phase strangler pipeline. Replaces ad-hoc phase management with explicit states, transitions, guards, and rollback paths.

---

## §1 — States

| State | Phase | Description | Entry Condition |
|-------|-------|-------------|-----------------|
| `IDLE` | — | No active refactoring | Initial state or after COMPLETED/ROLLED_BACK |
| `DISCOVERING` | 0-1 | Analysis + discovery + API inspection | Target file validated |
| `ANALYZING` | 2 | Pattern and test strategy analysis | Discovery artifacts exist |
| `PLANNING` | 3 | Interactive or auto planning | Analysis artifacts exist |
| `TASK_BREAKING` | 4 | Breaking plan into executable tasks | Plan approved |
| `SPEC_GENERATING` | 5 | Generating service specifications | Tasks defined |
| `TEST_GENERATING` | 6 | Generating TDD tests from specs | Spec approved |
| `CODE_GENERATING` | 7 | Generating implementation from spec | Tests exist (RED state) |
| `EXTRACTING_PARALLEL` | 6-8 | Multiple independent tasks extracting concurrently | Specs approved + parallel mode + independent tasks identified |
| `VALIDATING` | 8 | Running unified validation + push | Code generated, tests pass |
| `COMPLETED` | — | Pipeline finished successfully | Validation APPROVED + push done |
| `PARTIAL_COMPLETE` | — | Some tasks extracted, some rolled back | Parallel mode, mixed results |
| `FAILED` | — | Unrecoverable error | Any fatal error (STR-*F*) |
| `ROLLED_BACK` | — | Extraction reverted | Validation REJECTED or test failure |

---

## §2 — Transitions

```
IDLE ──────────────→ DISCOVERING        [trigger: /strangler-discover]
DISCOVERING ───────→ ANALYZING          [guard: discovery_complete]
ANALYZING ─────────→ PLANNING           [guard: analysis_complete]
PLANNING ──────────→ TASK_BREAKING      [guard: plan_approved]
TASK_BREAKING ─────→ SPEC_GENERATING    [guard: tasks_defined]
SPEC_GENERATING ───→ TEST_GENERATING    [guard: spec_approved]
TEST_GENERATING ───→ CODE_GENERATING    [guard: tests_exist_and_fail]
CODE_GENERATING ───→ VALIDATING         [guard: tests_pass]
VALIDATING ────────→ COMPLETED          [guard: validation_approved]

# Parallel extraction transitions
SPEC_GENERATING ───→ EXTRACTING_PARALLEL  [guard: specs_approved AND parallel_mode AND independent_tasks_exist]
EXTRACTING_PARALLEL → COMPLETED           [guard: all_waves_done AND all_tasks_validated]
EXTRACTING_PARALLEL → PARTIAL_COMPLETE    [guard: all_waves_done AND some_tasks_rolled_back]

# Error/Rollback transitions (from any active state)
* ─────────────────→ FAILED             [trigger: fatal_error]
CODE_GENERATING ───→ ROLLED_BACK        [trigger: tests_fail_after_3_retries]
VALIDATING ────────→ ROLLED_BACK        [trigger: validation_rejected]
EXTRACTING_PARALLEL → ROLLED_BACK       [trigger: all_tasks_in_wave_rolled_back]

# Recovery transitions
FAILED ────────────→ IDLE               [trigger: /strangler-discover (fresh start)]
ROLLED_BACK ───────→ SPEC_GENERATING    [trigger: /strangler-spec (retry with updated spec)]
ROLLED_BACK ───────→ IDLE               [trigger: /strangler-discover (fresh start)]
PARTIAL_COMPLETE ──→ SPEC_GENERATING    [trigger: /strangler-spec (fix rolled-back tasks)]
PARTIAL_COMPLETE ──→ EXTRACTING_PARALLEL [trigger: /strangler-extract --all (retry remaining)]
```

---

## §3 — Guards (Preconditions)

Each guard is a predicate that MUST be true before a transition fires. If false, the transition is BLOCKED and the reason logged.

| Guard | Condition | Error if False |
|-------|-----------|----------------|
| `discovery_complete` | `STRANGLER_DISCOVERY.md` exists AND `STRANGLER_API_PATTERNS.md` exists | STR-1E001 |
| `analysis_complete` | `STRANGLER_ANALYSIS.md` exists | STR-2E001 |
| `plan_approved` | `STRANGLER_PLAN.md` exists AND `state.plan_status == "approved"` | STR-3E001 |
| `tasks_defined` | `STRANGLER_TASKS.md` exists AND task count > 0 | STR-4E001 |
| `monolith_extraction_ready` | health_score ≥ 40 OR total_methods_planned ≤ 8 OR `--override-guard` | STR-GCE001 |
| `spec_size_valid` | All specs have method_count ≤ 15 (no god service in proposed specs) | STR-GCE002 |
| `spec_approved` | `STRANGLER_SPECS/SPEC_MANIFEST.json` exists AND all specs have `status: "approved"` | STR-5E001 |
| `tests_exist_and_fail` | `STRANGLER_TESTS/TEST_MANIFEST.json` exists AND tests compile AND tests FAIL (RED) | STR-6E001 |
| `tests_pass` | All Phase 6 tests pass (GREEN) with ≥90% coverage | STR-7E001 |
| `validation_approved` | Unified validator returns `verdict: "APPROVED"` | STR-8E001 |
| `independent_tasks_exist` | ≥2 tasks have no mutual dependency (can run in parallel) | STR-4W001 |
| `all_waves_done` | All waves in parallel_extraction.waves have `status: "completed"` | STR-PE001 |
| `all_tasks_validated` | All tasks in parallel_extraction.task_states have `status: "validated"` | STR-PE002 |

---

## §4 — Template Method Hooks

Each state executes three hooks in sequence:

```
enter(state):
  - Log state entry: [STATE:{state}] [ENTER]
  - Load phase-gated skill sections
  - Validate guards (preconditions)
  - Record timestamp in state file

execute(state):
  - Spawn workers for this phase
  - Wait for worker completion
  - Aggregate worker outputs
  - Validate postconditions (artifacts exist, quality met)

exit(state):
  - Log state exit: [STATE:{state}] [EXIT]
  - Record completion timestamp
  - Update state file: phases.{phase} = "completed"
  - Evaluate next transition guard
```

---

## §5 — State File Schema (v2)

```json
{
  "schema_version": 2,
  "machine_state": "SPEC_GENERATING",
  "previous_state": "TASK_BREAKING",
  "jira_id": "HPTRX-9196",
  "target_file": "/path/to/MonolithService.java",
  "start_time": "2026-07-15T10:00:00Z",
  "locked_by": "orchestrator",
  "locked_at": "2026-07-15T10:15:00Z",
  "phases": {
    "phase_0": "completed",
    "phase_1": "completed",
    "phase_2": "completed",
    "phase_3": "completed",
    "phase_4": "completed",
    "phase_5": "in_progress",
    "phase_6": "pending",
    "phase_7": "pending",
    "phase_8": "pending"
  },
  "checkpoints": [
    {"task_id": "T001", "git_sha": "abc123", "timestamp": "2026-07-15T10:30:00Z"}
  ],
  "spec_status": {
    "T001": "approved",
    "T002": "pending_review",
    "T003": "pending"
  },
  "test_status": {
    "T001": "red",
    "T002": "pending"
  },
  "validation": {
    "verdict": null,
    "fidelity_score": null,
    "tdd_coverage": null,
    "anti_patterns_found": null
  },
  "quality_gate": {
    "phases_complete": false,
    "tests_pass": false,
    "validation_approved": false,
    "all_checks_pass": false
  },
  "metrics": {
    "total_tokens": 0,
    "execution_time_seconds": 0,
    "retries": 0
  },
  "artifacts": {
    "discovery": ".claude/STRANGLER_DISCOVERY.md",
    "api_patterns": ".claude/STRANGLER_API_PATTERNS.md",
    "analysis": ".claude/STRANGLER_ANALYSIS.md",
    "plan": ".claude/STRANGLER_PLAN.md",
    "tasks": ".claude/STRANGLER_TASKS.md",
    "specs": ".claude/STRANGLER_SPECS/",
    "tests": ".claude/STRANGLER_TESTS/"
  },

  "coverage": {
    "T001": {"line": 93.2, "branch": 91.5, "method": 100.0},
    "T002": null
  },

  "health_scores": {
    "baseline": 55,
    "current": 68,
    "risk_level": "moderate",
    "total_improvement": 13,
    "per_task": {
      "T001": {
        "before": 55,
        "after": 62,
        "delta": 7,
        "methods_extracted": 4,
        "lines_removed": 56,
        "complexity_removed": 15,
        "timestamp": "2026-07-15T11:05:00Z"
      },
      "T002": {
        "before": 62,
        "after": 68,
        "delta": 6,
        "methods_extracted": 3,
        "lines_removed": 42,
        "complexity_removed": 12,
        "timestamp": "2026-07-15T11:15:00Z"
      }
    },
    "trend": [55, 62, 68],
    "risk_transitions": [
      {"from": "high", "to": "moderate", "at_task": "T001", "at_score": 55}
    ]
  },

  "guard_results": {
    "god_class_reduction": {
      "checked_at": "2026-07-15T10:45:00Z",
      "health_score": 55,
      "total_methods_planned": 14,
      "max_methods_per_task": 5,
      "level_1_blocked": false,
      "level_2_warnings": [],
      "level_3_warning": false,
      "decision": "PASS",
      "override_used": false
    }
  },

  "model_execution": {
    "strategy": "auto",
    "health_score_used": 68,
    "model_overrides": {},
    "per_phase": {
      "phase_0": {"model": "fast", "tokens_used": 48, "time_ms": 1200},
      "phase_1": {
        "1A": {"model": "fast", "tokens_used": 145, "time_ms": 3200},
        "1B": {"model": "fast", "tokens_used": 98, "time_ms": 2800},
        "1C": {"model": "fast", "tokens_used": 92, "time_ms": 2600},
        "1D": {"model": "balanced", "tokens_used": 380, "time_ms": 4500}
      },
      "phase_2": {
        "2A": {"model": "balanced", "tokens_used": 720, "time_ms": 5200},
        "2B": {"model": "fast", "tokens_used": 410, "time_ms": 3100}
      },
      "phase_3": {"model": "balanced", "tokens_used": 1450, "time_ms": 12000},
      "phase_4": {"model": "fast", "tokens_used": 380, "time_ms": 3400},
      "phase_5": {"model": "balanced", "tokens_used": 880, "time_ms": 4800},
      "phase_6": {"model": "balanced", "tokens_used": 720, "time_ms": 4200},
      "phase_7A": {"model": "heavy", "tokens_used": 1850, "time_ms": 8500, "attempt": 1},
      "phase_7B": {"model": "fast", "tokens_used": 210, "time_ms": 2100},
      "phase_8": {"model": "balanced", "tokens_used": 890, "time_ms": 4900}
    },
    "totals": {
      "tokens_total": 7273,
      "tokens_saved_vs_all_heavy": 3627,
      "savings_percent": 33.3,
      "time_total_ms": 54900
    }
  },

  "parallel_extraction": {
    "enabled": false,
    "mode": null,
    "total_waves": 0,
    "current_wave": 0,
    "waves": [],
    "task_states": {},
    "monolith_write_lock": {
      "held_by": null,
      "acquired_at": null,
      "last_heartbeat": null,
      "queue": [],
      "protocol": {
        "type": "state-file-semaphore",
        "max_hold_time_seconds": 60,
        "heartbeat_interval_seconds": 10,
        "deadlock_timeout_seconds": 20,
        "queue_max_size": 10
      }
    },
    "summary": {
      "total_tasks": 0,
      "extracted": 0,
      "rolled_back": 0,
      "in_progress": 0,
      "pending": 0
    }
  }
}
```

---

## §6 — Resumption Protocol

On startup, orchestrator reads state file and resumes:

```
1. Read .claude/forge-state.json
2. If schema_version < 2: migrate (add machine_state from phases)
3. Determine machine_state
4. If state is terminal (COMPLETED, FAILED, ROLLED_BACK): report status, STOP
5. If state is active: validate guards for current state
   - If guards pass: re-enter execute() hook
   - If guards fail: log error, transition to FAILED
6. Resume execution from current state
```

---

## §7 — Rollback Protocol

Triggered when:
- `CODE_GENERATING` → tests fail after 3 retries
- `VALIDATING` → validator returns REJECTED

Rollback steps:
```
1. Find checkpoint for current task_id
2. Execute: git reset --hard {checkpoint.git_sha}
3. Update state file: machine_state = "ROLLED_BACK"
4. Log: [ROLLBACK] task_id={task_id} sha={sha} reason={reason}
5. Clean up generated artifacts for this task (specs preserved)
6. Report to user: what was rolled back and why
```

---

## §8 — Backward Compatibility

- State files with `schema_version: 1` (or missing) are auto-migrated
- Migration: `machine_state` derived from `phases` object (last completed phase + 1)
- Old commands continue to work — Phase 5 (old extraction) maps to Phase 7 (new code generation)
- `/strangler-extract T001` triggers Phases 5→6→7 in sequence for backward compat

---

## Agent Self-Check

- [ ] State transitions follow the defined guard conditions (no invalid jumps)
- [ ] Machine state matches phase status (e.g., DISCOVERING ↔ phase_1 in_progress)
- [ ] Rollback restores to exact checkpoint SHA (verified via git log)
- [ ] State file schema is v2 with all required fields present
- [ ] No orphan states (every state has at least one outbound transition)
- [ ] Error states produce structured STR-* error codes

## Source

**Owner:** preetha.ramaswamy@barclays.com  
**Review cadence:** Quarterly or on major version bump  
**Origin:** Barclays BUK Strangler Refactoring Plugin v3.0 — internal engineering  
**Classification:** Internal
