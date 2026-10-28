---
name: scenarios
Source: Barclays BUK Strangler Refactoring Plugin v3.2
Owner: preetha.ramaswamy@barclays.com
Review trigger: Quarterly or on major version bump
user-invocable: false
Status: Published
---
> **Source:** Strangler Refactoring Plugin v3.2 — Test Scenarios — End-to-End Extraction Validation (internal)
> **Owner:** Preetha Ramaswamy / BUK CIO Engineering
> **Review trigger:** When new scenarios are validated from real extractions
> **Status:** Published
> Source documents are Internal — Restricted.


## Quick Start

```
Phase: 6 (referenced by test generation)
Worker: 6A (Test Generator)
Load: orchestrator passes as supplementary context with test-generation skill
Use: Provides Given/When/Then behavioral contracts for extracted methods
Model: balanced (same as Worker 6A)
```

# Test Scenarios — Behavioral Contracts for the Plugin

> **Purpose:** Defines expected behavior of the barclays-buk-strangler-refactoring plugin itself. These scenarios serve as regression contracts — if the plugin's behavior changes, scenarios must be updated. Used by the validation agent to verify its own correctness.

---

## §1 — Scenario Format

```
SCENARIO: {descriptive name}
  GIVEN: {preconditions — state file status, files present, etc.}
  WHEN: {command or action triggered}
  THEN: {expected outcomes — artifacts produced, state changes, errors}
  ERROR: {expected error code if failure scenario}
```

---

## §2 — Discovery Scenarios

```
SCENARIO: Fresh discovery on valid Java monolith (>500 lines)
  GIVEN: No .claude/forge-state.json exists
         Target file is src/main/java/.../MonolithService.java (800 lines)
  WHEN: /strangler-discover src/main/java/.../MonolithService.java
  THEN: .claude/forge-state.json created (schema_version=2, machine_state=DISCOVERING→IDLE)
        .claude/STRANGLER_DISCOVERY.md exists
        .claude/STRANGLER_DISCOVERY_CACHE.json exists (valid JSON)
        .claude/STRANGLER_API_PATTERNS.md exists (discovered patterns, not hardcoded)
        State: phase_0=completed, phase_1=completed
        Health score calculated (0-100)
        At least 1 domain identified

SCENARIO: Discovery on small file (<500 lines)
  GIVEN: No state file, target is 200-line Java file
  WHEN: /strangler-discover src/main/java/.../SmallService.java
  THEN: Warning STR-0W001 logged
        Discovery still proceeds (not blocked)
        STRANGLER_DISCOVERY.md exists

SCENARIO: Discovery on non-Java file
  GIVEN: Target is application.yml
  WHEN: /strangler-discover src/main/resources/application.yml
  THEN: Error STR-0F002 "Target file is not source code"
        State machine: IDLE (never started)
        No artifacts created

SCENARIO: Resume after interrupted discovery
  GIVEN: State file exists with phase_0=completed, phase_1=failed
  WHEN: /strangler-discover (same target)
  THEN: Skips phase_0
        Retries phase_1
        Does NOT recreate state file
        On success: phase_1=completed
```

---

## §3 — Spec Generation Scenarios

```
SCENARIO: Generate specs for all tasks
  GIVEN: phase_4=completed, STRANGLER_TASKS.md has T001, T002, T003
         STRANGLER_API_PATTERNS.md exists with discovered conventions
  WHEN: /strangler-spec --all
  THEN: .claude/STRANGLER_SPECS/ directory created
        T001-*-spec.md, T002-*-spec.md, T003-*-spec.md generated
        contracts/ directory with interface files
        SPEC_MANIFEST.json with all 3 tasks (status: pending_review)
        State: machine_state=SPEC_GENERATING, spec_status.T001=pending_review

SCENARIO: Approve specific spec
  GIVEN: Specs generated, T001 is pending_review
  WHEN: /strangler-spec --approve T001
  THEN: spec_status.T001 = "approved" in state file
        SPEC_MANIFEST.json updated
        Message: "Spec T001 approved"

SCENARIO: Reject spec with reason
  GIVEN: Specs generated, T002 is pending_review
  WHEN: /strangler-spec --reject T002 --reason "Split processPayment into two methods"
  THEN: spec_status.T002 = "rejected"
        Reason stored for regeneration guidance
        Message: "Spec T002 rejected, will regenerate with feedback"

SCENARIO: Spec generation before tasks exist
  GIVEN: phase_4 NOT completed (no STRANGLER_TASKS.md)
  WHEN: /strangler-spec --all
  THEN: Error: "Phase 4 (task breakdown) not complete. Run /strangler-tasks first"
        No artifacts created
```

---

## §4 — TDD Pipeline Scenarios

```
SCENARIO: Tests generated in RED state
  GIVEN: All specs approved (spec_status.* = approved)
  WHEN: /strangler-extract T001 (triggers Phase 6)
  THEN: .claude/STRANGLER_TESTS/T001-*/ directory created
        4 test files generated (Contract, Behavior, Integration, Error)
        Tests COMPILE successfully
        Tests FAIL (no implementation exists yet = RED)
        test_status.T001 = "red"

SCENARIO: Code generation makes tests GREEN
  GIVEN: test_status.T001 = "red" (tests exist and fail)
  WHEN: Phase 7 code generation runs (Worker 7A, attempt 1)
  THEN: New service file generated in src/main/java/
        Monolith updated with delegation
        Worker 7B runs tests → ALL PASS
        test_status.T001 = "green"
        Commit created

SCENARIO: Code generation fails, retries, then succeeds
  GIVEN: test_status.T001 = "red"
  WHEN: Worker 7A attempt 1 (clean) → tests fail
        Worker 7A attempt 2 (conservative) → tests fail
        Worker 7A attempt 3 (pure movement) → tests pass
  THEN: Attempt 3 code committed (pure movement fallback)
        test_status.T001 = "green"
        Warning: STR-7W001 "Fidelity below 90%"

SCENARIO: All 3 attempts fail → auto-rollback
  GIVEN: Checkpoint exists at SHA abc123
  WHEN: Worker 7A all 3 attempts fail
  THEN: git reset --hard abc123 executed
        machine_state = "ROLLED_BACK"
        Error: STR-7E002 "Tests still fail after 3 retries"
        Specs preserved (not deleted)
        Tests preserved (not deleted)
        Report to user: which tests fail and why
```

---

## §5 — Validation Scenarios

```
SCENARIO: Validation APPROVED (all checks pass)
  GIVEN: Generated code, tests pass, fidelity=92%
  WHEN: Worker 8 (Unified Validator) runs
  THEN: Check 1 (fidelity ≥85%): PASS (92%)
        Check 2 (tests pass): PASS (all green)
        Check 3 (anti-patterns): PASS (3 methods, no cycles)
        Verdict: APPROVED
        quality_gate.validation_approved = true

SCENARIO: Validation REJECTED (fidelity too low)
  GIVEN: Generated code, tests pass, fidelity=78%
  WHEN: Worker 8 runs
  THEN: Check 1 (fidelity ≥85%): FAIL (78%)
        Verdict: REJECTED
        Auto-rollback triggered
        machine_state = "ROLLED_BACK"

SCENARIO: Validation REJECTED (anti-pattern: god service)
  GIVEN: Generated service has 18 public methods
  WHEN: Worker 8 runs
  THEN: Check 3 (anti-patterns): FAIL (>15 methods)
        Verdict: REJECTED
        Auto-rollback triggered
```

---

## §6 — State Machine Scenarios

```
SCENARIO: Valid forward transition
  GIVEN: machine_state = "DISCOVERING"
         Guard: STRANGLER_DISCOVERY.md exists
  WHEN: Orchestrator calls transition to ANALYZING
  THEN: machine_state = "ANALYZING"
        previous_state = "DISCOVERING"
        Logged: [STATE:ANALYZING] [ENTER]

SCENARIO: Invalid transition (skipping phases)
  GIVEN: machine_state = "DISCOVERING"
  WHEN: Attempt transition to CODE_GENERATING (skipping 5 states)
  THEN: Transition BLOCKED
        machine_state remains "DISCOVERING"
        Error logged: "Invalid transition: DISCOVERING → CODE_GENERATING"

SCENARIO: Rollback transition
  GIVEN: machine_state = "VALIDATING", checkpoint exists
  WHEN: Validator returns REJECTED
  THEN: machine_state = "ROLLED_BACK"
        git reset executed
        Logged: [ROLLBACK] reason=validation_rejected

SCENARIO: Recovery from ROLLED_BACK
  GIVEN: machine_state = "ROLLED_BACK"
  WHEN: User runs /strangler-spec T001 (to fix and retry)
  THEN: machine_state transitions to "SPEC_GENERATING"
        Spec regenerated with modifications
```

---

## §7 — API Inspection Scenarios

```
SCENARIO: Standard Spring Boot project with controllers
  GIVEN: Project has PaymentController, CardController, AccountController
         Each controller has @RequestMapping with base paths
  WHEN: Worker 1D (API Inspector) runs
  THEN: STRANGLER_API_PATTERNS.md contains:
        - architecture_style: "layered"
        - 3 domains detected (payment, cards, accounts)
        - naming conventions discovered (not hardcoded)
        - DI style detected (constructor vs field)
        - Test framework detected

SCENARIO: Flat monolith with no controllers
  GIVEN: Project has one service class, no REST layer
  WHEN: Worker 1D runs
  THEN: STRANGLER_API_PATTERNS.md contains:
        - architecture_style: "monolith"
        - Domains inferred from method prefixes and package structure
        - Warning: STR-1E002 "No REST endpoints found" (continues anyway)

SCENARIO: Domain conventions DON'T match hardcoded assumptions
  GIVEN: Project uses *Handler instead of *Service, *Command instead of *Request
  WHEN: Worker 1D runs
  THEN: STRANGLER_API_PATTERNS.md reports:
        - service_suffix: "Handler" (discovered, not assumed)
        - dto_suffix: "Command" (discovered, not assumed)
        - These conventions flow into spec generation (Phase 5)
```

---

## Agent Self-Check

- [ ] Scenarios follow Given/When/Then format consistently
- [ ] Each scenario maps to exactly one extracted method behavior
- [ ] Edge cases covered (null inputs, empty collections, error paths)
- [ ] Scenarios reference domain terminology from discovery phase
- [ ] No implementation details leaked into scenario descriptions
- [ ] Scenarios are executable (can be directly translated to JUnit test methods)

## Source

**Owner:** preetha.ramaswamy@barclays.com  
**Review cadence:** Quarterly or on major version bump  
**Origin:** Barclays BUK Strangler Refactoring Plugin v3.0 — internal engineering  
**Classification:** Internal
