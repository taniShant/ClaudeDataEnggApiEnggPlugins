---
name: code-generation
Source: Barclays BUK Strangler Refactoring Plugin v3.2
Owner: preetha.ramaswamy@barclays.com
Review trigger: Quarterly or on major version bump
user-invocable: false
Status: Published
---
> **Source:** Strangler Refactoring Plugin v3.2 — Code Generation — Hexagonal Implementation Patterns (internal)
> **Owner:** Preetha Ramaswamy / BUK CIO Engineering
> **Review trigger:** Quarterly or when new code generation patterns are added
> **Status:** Published
> Source documents are Internal — Restricted.


## Quick Start

```
Phase: 7 (Code Generation — GREEN)
Worker: 7A (Code Generator)
Load: orchestrator passes skill_context = code-generation §1-10
Use: Generate hexagonal service from spec → make Phase 6 tests pass
Model: heavy (attempt 1), balanced (attempt 2), fast (attempt 3)
```

# Code Generation — Spec-Driven Implementation (Green Phase)

> **Purpose:** Generate clean service implementations from specifications that pass Phase 6 tests. This replaces pure code movement with spec-driven generation that produces clean, well-structured code while preserving behavior.

---

## §1 — Philosophy: Make Tests Pass (Green Phase)

```
Phase 5 (Spec) → Phase 6 (Tests — RED) → Phase 7 (Code — GREEN) → Validate
                                                ↑
                                           YOU ARE HERE

The implementation MUST:
- Implement the contract interface (from Phase 5)
- Pass ALL tests (from Phase 6)
- Preserve behavior equivalence with monolith
- Follow clean code principles and discovered patterns
```

---

## §2 — Code Generation Input

| Input | Source | Purpose |
|-------|--------|---------|
| Service spec | `STRANGLER_SPECS/T{NNN}-*-spec.md` | Contract, dependencies, behavior table |
| Tests | `STRANGLER_TESTS/T{NNN}-*/` | Tests that must pass (GREEN) |
| Monolith source | Original target file | Method bodies to extract logic from |
| API patterns | `STRANGLER_API_PATTERNS.md` | Code style, DI, naming to follow |
| Contract interface | `STRANGLER_SPECS/contracts/` | Interface to implement |

---

## §3 — Generation Strategy

### Step 1: Implement Contract Interface

```java
@Service
@RequiredArgsConstructor  // Match detected DI style
@Slf4j                    // If logging pattern detected in project
public class {ServiceName} implements {ServiceName}Contract {

    private final {Dep1Type} {dep1Name};
    private final {Dep2Type} {dep2Name};
    // All dependencies from spec
}
```

### Step 2: Extract Method Logic from Monolith

For each method in the contract:

```
1. Read method body from monolith source
2. Copy the core logic (business rules, conditions, calculations)
3. Apply clean code transformations:
   - Remove dead code (unreachable branches, commented code)
   - Clarify variable names (match project conventions)
   - Extract magic numbers to constants
   - Simplify nested conditions (guard clauses)
   - Remove redundant null checks if type system handles it
4. Wire dependencies (replace monolith's internal calls with injected service calls)
5. Preserve ALL behavior (same inputs → same outputs → same exceptions)
```

### Step 3: Apply Discovered Code Style

From `STRANGLER_API_PATTERNS.md`:

| Pattern Detected | Apply |
|-----------------|-------|
| Constructor injection + Lombok | `@RequiredArgsConstructor`, `private final` fields |
| Field injection | `@Autowired private` fields (respect legacy style) |
| `@Transactional` on writes | Add to methods that modify state |
| `@Cacheable` on reads | Add to idempotent read methods |
| Slf4j logging | Add `log.info()`/`log.error()` at entry/exit |
| Correlation ID via MDC | Preserve MDC context in method calls |

### Step 4: Validate Against Tests

```
1. Compile generated service class
2. Run contract tests → MUST PASS
3. Run behavior tests → MUST PASS
4. Run error path tests → MUST PASS
5. Run integration tests → MUST PASS (if Spring context available)

If ANY test fails:
  - Analyze failure reason
  - Fix implementation (not the test!)
  - Retry (max 3 attempts)
  - If 3 retries exhausted → ROLLBACK, error STR-7E002
```

---

## §4 — Clean Code Transformations (Allowed)

The generated code MAY differ from the monolith in these ways:

### Allowed Transformations (within 85% fidelity):

| Transformation | Example | Why Allowed |
|---------------|---------|-------------|
| Extract constant | `if (retries > 3)` → `if (retries > MAX_RETRIES)` | Readability |
| Guard clause | Nested `if/else` → early return | Readability |
| Variable rename | `x` → `accountBalance` | Clarity |
| Remove dead code | Unreachable `else` branch | Cleanliness |
| Formatting | Consistent indentation, line breaks | Style |
| @Override annotation | Add if implementing interface | Correctness |
| Remove redundant cast | `(String) stringVar` → `stringVar` | Cleanup |
| Constructor injection | `@Autowired` field → constructor param | Best practice |

### NOT Allowed (behavior changes — would fail tests):

| Forbidden | Example | Why Forbidden |
|-----------|---------|---------------|
| Change logic | Remove null check | Behavior change |
| Change exception type | `PaymentException` → `RuntimeException` | Contract violation |
| Add new dependency | Import external library not in monolith | Scope creep |
| Hardcode values | Replace config lookup with literal | Behavior change |
| Change method signature | Add/remove parameters | Contract violation |
| Swallow exception | `catch(e) { /* ignore */ }` | Behavior change |
| Change return value | Return different default | Behavior change |

---

## §5 — Delegation Update in Monolith

After generating the new service, update the monolith to delegate:

```java
// In the original monolith class:

// 1. Add dependency injection for new service
@Autowired private {ServiceName}Contract {serviceName};  // Match DI style

// 2. Replace method body with delegation
@Override
public {ReturnType} {methodName}({params}) throws {exceptions} {
    return {serviceName}.{methodName}({args});
}
```

### Delegation Rules:
- Method signature remains IDENTICAL (no changes to callers)
- Delegate using the contract interface (not concrete class)
- Keep all annotations on the method (@Transactional, @Cacheable, etc.)
- Remove the original method body (replaced with one-liner delegation)
- Preserve Javadoc/comments on the method

---

## §6 — Test Execution Protocol

```
STEP 1: Compile Check
  javac / gradle compileJava — verify no syntax errors
  If fails: Fix syntax → retry (count toward 3 max)

STEP 2: Unit Tests (Fast)
  Run: ContractTest + BehaviorTest + ErrorTest
  Expected: ALL PASS (GREEN)
  If fails: Analyze → fix implementation → retry

STEP 3: Integration Tests (Slow)
  Run: IntegrationTest (needs Spring context)
  Expected: ALL PASS
  If fails: Check delegation wiring, check bean registration → retry
  If no Spring context available: SKIP with warning STR-8W002

STEP 4: Fidelity Check
  Compare original method body vs generated method body
  Calculate: clean_code_changes / total_lines
  Expected: ≥85% fidelity (up to 15% clean code improvements)
  If below 85%: Review transformations, revert over-aggressive cleanup
```

---

## §7 — Iteration Strategy (Max 3 Retries)

```
Attempt 1: Standard generation (heavy model)
  - Extract logic directly from monolith
  - Apply clean code transformations
  - Enforce hexagonal structure from spec (domain, adapters, ports)
  - Run tests
  - IF tests pass: verify hexagonal compliance (Check 4)
    - IF hexagonal violations detected: apply hexagonal repair (see below)

If tests fail → Attempt 2: Conservative generation (balanced model)
  - Reduce clean code transformations (closer to pure movement)
  - Keep original variable names
  - Keep original structure
  - Still enforce hexagonal boundaries (ports, adapters)
  - Run tests

If tests fail → Attempt 3: Pure movement fallback (fast model)
  - Copy method body exactly (only change: add @Override, wire DI)
  - No clean code transformations
  - Minimal hexagonal structure (single adapter wrapping existing logic)
  - Run tests

If tests STILL fail → ROLLBACK
  - Error: STR-7E002 "Tests still fail after 3 retries"
  - Trigger rollback protocol (git reset to checkpoint)
  - State machine → ROLLED_BACK
  - Report to user: which tests fail and why
```

### Hexagonal Repair Strategy (v3.2)

If tests PASS but hexagonal validation (Check 4) detects violations, apply targeted repairs BEFORE committing:

```
Hexagonal Repair Cases:

H1-REPAIR: Framework imports in domain service
  → Move @Transactional, @Cacheable, @Retryable to inbound adapter
  → Domain service remains framework-free (pure Java)

H2-REPAIR: Concrete class instantiation in domain
  → Extract port interface for the dependency
  → Create outbound adapter implementing the port
  → Domain references port interface only

H3-REPAIR: Business logic in inbound adapter
  → Move logic from adapter to domain service
  → Adapter delegates only: domainService.execute(command)

H4-REPAIR: Outbound adapter missing port implementation
  → Add `implements {Dependency}Port` to adapter class
  → Verify method signatures match port interface

H5-REPAIR: Framework objects at port boundary
  → Replace JPA entities at boundary with plain DTOs/records
  → Map between entity and DTO in outbound adapter

After repair:
  - Re-run tests (must still pass)
  - Re-run hexagonal check (must now pass)
  - If repair breaks tests → revert repair, commit code WITH hexagonal violations
    (Check 4 in validation is WARNING-ONLY — it logs the violation but does NOT block the commit)
```

---

## §8 — Generated Service Structure

```java
package {base.package}.{domain}.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
// ... other imports from spec dependencies

/**
 * {ServiceName} — extracted from {MonolithClass}.
 *
 * <p>Responsibility: {from spec overview}
 *
 * <p>Extracted as part of strangler pattern refactoring.
 * Task: {task_id}, JIRA: {jira_id}
 *
 * @see {ServiceName}Contract
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class {ServiceName} implements {ServiceName}Contract {

    private final {Dep1Type} {dep1Name};
    private final {Dep2Type} {dep2Name};

    /**
     * {Method Javadoc from monolith — preserve exactly}
     */
    @Override
    @Transactional  // if detected in original
    public {ReturnType} {methodName}({params}) throws {exceptions} {
        log.info("Entering {methodName} with {param summary}");
        
        // Core logic extracted from monolith
        {extracted and cleaned method body}
        
        log.info("Exiting {methodName} with result: {result summary}");
        return result;
    }
}
```

---

## §9 — Output Artifacts

Phase 7 produces:

```
Source files (in project src/main/java/):
  - {ServiceName}.java (new service implementation)
  - {ServiceName}Contract.java (interface — from spec, copied to src)

Source files (modified):
  - {MonolithClass}.java (delegation added, method bodies removed)

Test files (moved to project src/test/java/):
  - {ServiceName}ContractTest.java
  - {ServiceName}BehaviorTest.java
  - {ServiceName}IntegrationTest.java
  - {ServiceName}ErrorTest.java

State file updates:
  - test_status.{task_id} = "green"
  - machine_state = "VALIDATING"
```

---

## §10 — Worker 7A & 7B Specifications

**Worker 7A: Code Generator**

```
Phase: 7
Scope: Read specs/tests + write service implementation
Input: STRANGLER_SPECS/*, STRANGLER_TESTS/*, monolith source, API patterns
Output: New service file, updated monolith, tests placed in project
Token Budget: ~1200-1800 tokens per task

Execution:
1. Read spec (contract, behavior, dependencies)
2. Read monolith method bodies
3. Generate service class implementing contract
4. Apply clean code transformations (within 85% fidelity)
5. Generate delegation in monolith
6. Place contract interface in project source
7. Place test files in project test directory
8. Trigger Worker 7B for test execution

Constraints:
- MUST implement contract interface exactly
- MUST preserve behavior (tests are the judge)
- May apply clean code within 85% fidelity
- If tests fail: iterate (max 3 retries per §7)
- If all retries fail: trigger rollback
```

**Worker 7B: Test Runner**

```
Phase: 7
Scope: Execute tests, report results
Input: Generated service + test files
Output: Test execution report (pass/fail per test)
Token Budget: ~200-400 tokens

Execution:
1. Compile service + tests
2. Run unit tests (contract + behavior + error)
3. Run integration tests (if context available)
4. Report: {total, passed, failed, skipped}
5. If failures: return failure details to Worker 7A
6. If all pass: signal GREEN to orchestrator

Constraints:
- Read-only (never modifies source or tests)
- Reports facts (pass/fail) — does not fix
- Integration tests optional (skip if no context)
```

---

## Agent Self-Check

- [ ] Generated service follows hexagonal architecture from spec
- [ ] Domain service has ZERO Spring/framework imports
- [ ] Inbound adapter is the ONLY Spring-annotated class
- [ ] Outbound adapters implement port interfaces (method signatures match)
- [ ] All tests pass (GREEN state achieved)
- [ ] Delegation stubs added to monolith (calls forwarded to new service)
- [ ] Method signatures unchanged from original (public API preserved)

## Source

**Owner:** preetha.ramaswamy@barclays.com  
**Review cadence:** Quarterly or on major version bump  
**Origin:** Barclays BUK Strangler Refactoring Plugin v3.0 — internal engineering  
**Classification:** Internal
