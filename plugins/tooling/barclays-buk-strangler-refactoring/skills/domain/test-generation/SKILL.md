---
name: test-generation
Source: Barclays BUK Strangler Refactoring Plugin v3.2
Owner: preetha.ramaswamy@barclays.com
Review trigger: Quarterly or on major version bump
user-invocable: false
Status: Published
---
> **Source:** Strangler Refactoring Plugin v3.2 — Test Generation — TDD Test Patterns (internal)
> **Owner:** Preetha Ramaswamy / BUK CIO Engineering
> **Review trigger:** When new test patterns or frameworks are supported
> **Status:** Published
> Source documents are Internal — Restricted.


## Quick Start

```
Phase: 6 (Test Generation — RED)
Worker: 6A (Test Generator), 6A-supplement (Coverage)
Load: orchestrator passes skill_context = test-generation §1-11
Use: Generate 4 test categories from spec (Contract, Behavior, Integration, Error)
Model: balanced
```

# Test Generation — TDD First (Red Phase)

> **Purpose:** Generate comprehensive tests from service specifications BEFORE implementation exists. Tests define the expected behavior contract. Implementation (Phase 7) must make these tests pass.

> **Complementary scope:** This skill defines how to generate TDD tests for strangler-extracted hexagonal services (Phase 6 automation). It is complementary to `barclays-buk-standards:testing`, which defines organisation-wide testing policy (methodology, anti-patterns, platform splits). Shared principles (90% coverage, no mock theatre) are stated in both because both enforce them independently. This skill adds: Java-specific templates, TDD RED/GREEN workflow, coverage supplementation rounds, JaCoCo integration. The standards skill adds: mutation testing (pitest), async patterns, multi-platform splits, 4-step methodology.

---

## §1 — TDD Philosophy

```
Phase 5 (Spec) → Phase 6 (Tests — RED) → Phase 7 (Code — GREEN) → Refactor
                       ↑
                  YOU ARE HERE

Tests are written FIRST. They:
- COMPILE (all types/interfaces referenced exist in spec)
- FAIL (no implementation yet — this is RED in TDD)
- Define BEHAVIOR (not implementation details)
- Serve as living documentation of the contract
```

---

## §2 — Test Categories

For each service spec, generate 4 test categories:

| Category | Tests | Purpose | Must Compile | Must Pass |
|----------|-------|---------|--------------|-----------|
| Contract | 2-4 | Verify interface implementation, method signatures | Yes | After Phase 7 |
| Behavior | 1 per spec row | Verify Given/When/Then from spec | Yes | After Phase 7 |
| Integration | 1-2 | Verify delegation equivalence with monolith | Yes | After Phase 7 |
| Error Path | 1 per exception | Verify error contracts | Yes | After Phase 7 |

---

## §3 — Test File Structure

```
.claude/STRANGLER_TESTS/
├── T001-payment-service/
│   ├── PaymentServiceContractTest.java
│   ├── PaymentServiceBehaviorTest.java
│   ├── PaymentServiceIntegrationTest.java
│   └── PaymentServiceErrorTest.java
├── T002-cards-service/
│   ├── CardsServiceContractTest.java
│   ├── CardsServiceBehaviorTest.java
│   ├── CardsServiceIntegrationTest.java
│   └── CardsServiceErrorTest.java
└── TEST_MANIFEST.json
```

---

## §4 — Contract Test Template (Java)

**Purpose:** Verify the new service implements the contract interface and preserves method signatures.

```java
package {base.package}.{domain}.service;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import static org.assertj.core.api.Assertions.*;

@DisplayName("{ServiceName} Contract Compliance")
class {ServiceName}ContractTest {

    @Test
    @DisplayName("Should implement {ServiceName}Contract interface")
    void shouldImplementContract() {
        assertThat({ServiceName}.class)
            .isAssignableTo({ServiceName}Contract.class);
    }

    @Test
    @DisplayName("Should expose {methodName} with correct signature")
    void shouldExpose{MethodName}WithCorrectSignature() throws NoSuchMethodException {
        var method = {ServiceName}.class.getMethod(
            "{methodName}",
            {ParamType1}.class, {ParamType2}.class
        );
        
        assertThat(method.getReturnType()).isEqualTo({ReturnType}.class);
        assertThat(method.getExceptionTypes()).contains({ExceptionType}.class);
    }

    @Test
    @DisplayName("Should use constructor injection for all dependencies")
    void shouldUseConstructorInjection() {
        var constructors = {ServiceName}.class.getConstructors();
        assertThat(constructors).hasSize(1);
        assertThat(constructors[0].getParameterCount()).isEqualTo({depCount});
    }
}
```

### Generation Rules:
- One `shouldImplementContract()` test per service
- One `shouldExpose*WithCorrectSignature()` per public method in contract
- One `shouldUseConstructorInjection()` if DI style is constructor (from API patterns)
- Use detected test framework (JUnit 5 preferred, fall back to JUnit 4 if project uses it)
- Use detected assertion library (AssertJ preferred, fall back to Hamcrest/JUnit)

---

## §5 — Behavior Test Template (Java)

**Purpose:** Verify each row of the behavior specification table from the spec.

```java
package {base.package}.{domain}.service;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.junit.jupiter.api.extension.ExtendWith;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;

@ExtendWith(MockitoExtension.class)
@DisplayName("{ServiceName} Behavior")
class {ServiceName}BehaviorTest {

    @Mock private {Dep1Type} {dep1Name};
    @Mock private {Dep2Type} {dep2Name};
    @InjectMocks private {ServiceName} service;

    @Nested
    @DisplayName("{methodName}")
    class {MethodName}Tests {
    
        @Test
        @DisplayName("Should {then} when {given}")
        void should{Then}When{Given}() {
            // Given — from spec behavior row
            {setup mocks based on spec preconditions}
            
            // When
            var result = service.{methodName}({testInput});
            
            // Then — from spec behavior row
            assertThat(result).{assertion from spec};
            verify({mockDep}).{expectedInteraction};
        }

        @Test
        @DisplayName("Should throw {exception} when {errorCondition}")
        void shouldThrow{Exception}When{Condition}() {
            // Given — error condition from spec
            {setup mocks for error condition}
            
            // When/Then
            assertThatThrownBy(() -> service.{methodName}({errorInput}))
                .isInstanceOf({ExceptionType}.class)
                .hasMessageContaining("{expected message fragment}");
        }
    }
}
```

### Generation Rules:
- One `@Nested` class per method in the contract
- One `@Test` per row in the Behavior Specification table from the spec
- Mock ALL dependencies (unit test — no Spring context)
- Assert on BEHAVIOR (return values, state changes, interactions) not implementation
- Use `@DisplayName` for readable test reports
- Match project's test naming convention (from API patterns)

### Anti-Pattern Detection in Generated Tests:
```
REJECT if test only does:
  verify(mock).someMethod();  // Mock-only verification without behavior assertion

REQUIRE at least one of:
  assertThat(result).isEqualTo(expected);  // Value assertion
  assertThat(result.getStatus()).isEqualTo(SUCCESS);  // State assertion
  assertThatThrownBy(...).isInstanceOf(...);  // Exception assertion
```

---

## §6 — Integration Test Template (Java)

**Purpose:** Verify that the extracted service produces identical results to the monolith for the same inputs.

```java
package {base.package}.{domain}.service;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.TestPropertySource;
import static org.assertj.core.api.Assertions.*;

import java.util.stream.Stream;

@SpringBootTest
@TestPropertySource(properties = {
    "spring.profiles.active=integration-test"
})
@DisplayName("{ServiceName} Integration — Delegation Equivalence")
class {ServiceName}IntegrationTest {

    @Autowired private {ServiceName}Contract newService;
    @Autowired private {MonolithClass} monolith;

    @ParameterizedTest
    @MethodSource("testCases")
    @DisplayName("Should produce same result as monolith for {methodName}")
    void shouldProduceSameResultAsMonolith({InputType} input) {
        // Given — same input to both implementations
        
        // When — call both
        var monolithResult = monolith.{methodName}(input);
        var extractedResult = newService.{methodName}(input);
        
        // Then — same output
        assertThat(extractedResult).isEqualTo(monolithResult);
    }

    static Stream<{InputType}> testCases() {
        return Stream.of(
            // Happy path case
            {happyPathInput},
            // Edge case
            {edgeCaseInput},
            // Boundary case
            {boundaryInput}
        );
    }
}
```

### Generation Rules:
- One integration test class per service
- Uses `@SpringBootTest` (full context) for delegation equivalence
- Parameterized with representative inputs from spec behavior table
- Compares monolith result vs extracted service result
- If no Spring context available, fall back to manual wiring in `@BeforeAll`

---

## §7 — Error Path Test Template (Java)

**Purpose:** Verify each error contract from the spec.

```java
package {base.package}.{domain}.service;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@DisplayName("{ServiceName} Error Handling")
class {ServiceName}ErrorTest {

    @Mock private {Dep1Type} {dep1Name};
    @InjectMocks private {ServiceName} service;

    @Test
    @DisplayName("Should throw {ExceptionType} when {condition}")
    void shouldThrow{ExceptionName}When{Condition}() {
        // Given — condition that triggers error
        when({dep}.{method}({args})).thenThrow(new {UpstreamException}("{msg}"));
        
        // When/Then
        assertThatThrownBy(() -> service.{methodName}({input}))
            .isInstanceOf({ExceptionType}.class);
    }

    @Test
    @DisplayName("Should handle null {paramName} gracefully")
    void shouldHandleNull{ParamName}() {
        assertThatThrownBy(() -> service.{methodName}(null))
            .isInstanceOf(IllegalArgumentException.class);
    }
}
```

---

## §8 — Test Manifest

```json
// .claude/STRANGLER_TESTS/TEST_MANIFEST.json
{
  "generated_at": "2026-07-15T11:00:00Z",
  "framework": "junit5",
  "assertions": "assertj",
  "mocking": "mockito",
  "tasks_total": 5,
  "tests_generated": {
    "contract": 10,
    "behavior": 25,
    "integration": 5,
    "error_path": 15,
    "total": 55
  },
  "compile_status": "success",
  "run_status": "all_fail",
  "tasks": [
    {
      "task_id": "T001",
      "service_name": "PaymentService",
      "test_files": [
        "T001-payment-service/PaymentServiceContractTest.java",
        "T001-payment-service/PaymentServiceBehaviorTest.java",
        "T001-payment-service/PaymentServiceIntegrationTest.java",
        "T001-payment-service/PaymentServiceErrorTest.java"
      ],
      "test_count": 12,
      "compile_status": "success",
      "run_status": "all_fail"
    }
  ]
}
```

---

## §9 — Adaptation to Project Style

The test generator MUST match the project's existing test style (from `STRANGLER_API_PATTERNS.md`):

| Detected Style | Adaptation |
|---------------|------------|
| JUnit 4 | Use `@RunWith(MockitoJUnitRunner.class)`, `@Test` from junit4 |
| JUnit 5 | Use `@ExtendWith(MockitoExtension.class)`, `@Test` from jupiter |
| AssertJ | Use `assertThat().isEqualTo()` style |
| Hamcrest | Use `assertThat(x, is(y))` style |
| JUnit native | Use `assertEquals(expected, actual)` style |
| `shouldXWhenY` naming | `shouldProcessPaymentWhenValidRequest()` |
| `givenWhenThen` naming | `givenValidRequest_whenProcessPayment_thenReturnsSuccess()` |
| `test` prefix | `testProcessPaymentWithValidRequest()` |

---

## §10 — Worker 6A Specification

**Worker 6A: Test Generator**

```
Phase: 6
Scope: Read specs + write test artifacts
Input: STRANGLER_SPECS/*, STRANGLER_API_PATTERNS.md
Output: .claude/STRANGLER_TESTS/ directory (test files + manifest)
Token Budget: ~600-1000 tokens per task

Execution per task:
1. Read spec file for task
2. Read API patterns (test framework, assertion library, naming)
3. Generate contract test class
4. Generate behavior test class (1 test per spec row)
5. Generate integration test class
6. Generate error path test class
7. Write all test files
8. Verify tests compile (syntax check only — no runtime)
9. Update TEST_MANIFEST.json

Constraints:
- Tests MUST compile against the contract interface (generated in Phase 5)
- Tests MUST FAIL without implementation (RED state)
- Tests MUST match project's existing test style
- NO mock-only tests (every test must assert behavior)
- NEVER write implementation code (that's Phase 7)
- Integration tests assume Spring context available
- Tests MUST target ≥90% line + branch coverage (see §11)
```

---

## §11 — Coverage Requirements (≥90% Line + Branch + Mutation)

### Coverage Thresholds (Mandatory)

Generated tests MUST achieve the following coverage on the extracted service class:

| Metric | Threshold | Enforcement |
|--------|-----------|-------------|
| **Line Coverage** | ≥ 90% | BLOCK if below (validation Check 2.4) |
| **Branch Coverage** | ≥ 90% | BLOCK if below (validation Check 2.4) |
| **Method Coverage** | 100% | Every public method must be exercised |
| **Mutation Score** | ≥ 90% | WARN if below (per `barclays-buk-standards:testing`) |

> **Rationale:** Tests are the PRIMARY quality gate (v3.0). High coverage ensures behavioral equivalence is proven, not assumed. 90% allows practical exceptions (unreachable defensive code, framework-generated methods) while ensuring comprehensive verification.

### Mutation Testing (pitest)

Per `barclays-buk-standards:testing`, extracted services must achieve **≥90% mutation score** using pitest. This ensures tests detect real behavioral changes, not just execute lines.

**Integration:**
```
# Gradle (add to build.gradle if not present)
plugins {
    id 'info.solidsoft.pitest' version '1.15.0'
}

pitest {
    targetClasses = ['{base.package}.{domain}.*']
    targetTests = ['{base.package}.{domain}.*Test']
    mutators = ['DEFAULTS']
    outputFormats = ['XML', 'HTML']
    timestampedReports = false
    threads = 4
}
```

**Enforcement:**
- Worker 7B runs `./gradlew pitest` after JaCoCo coverage passes
- Parse `build/reports/pitest/mutations.xml` for mutation score
- If score < 90%: log `[WARN] STR-6W003 "Mutation score {score}% below 90% target"`
- Mutation score is a WARN gate (not BLOCK) — low mutation score indicates weak assertions but doesn't prevent merge
- Common surviving mutants to address: negated conditionals, replaced return values, removed method calls

---

### Coverage-Driven Test Generation Strategy

Worker 6A should generate SUFFICIENT tests to reach 90%+ coverage by targeting all code paths:

**1. Branch Coverage Strategy:**
- For each `if/else`: generate test for TRUE branch AND FALSE branch
- For each `switch`: generate test for EACH case + default
- For each ternary (`? :`): generate test for both outcomes
- For each `try/catch`: generate test that enters catch block
- For each `&&` / `||` in conditions: consider short-circuit paths

**2. Line Coverage Strategy:**
- For methods with loops: test empty collection, single item, multiple items
- For guard clauses (early return): test the guard trigger AND the happy path
- For null checks: explicit null-input test per nullable parameter
- For exception paths: one test per catch block + one per throws declaration

**3. Edge Case Generation (for high coverage):**
- Boundary values: 0, -1, Integer.MAX_VALUE, empty string, null
- Collection edge cases: empty list, single element, large collection
- Optional.empty() paths
- Default branch in switch statements
- Nested conditional combinations

---

### Minimum Test Count Formula

```
min_tests = max(
  methods_count * 2,                          // At least 2 tests per method (happy + error)
  branch_count,                               // At least 1 test per branch path
  spec_behavior_rows + error_contract_rows    // Cover all spec rows
)

Example:
  Service with 5 methods, 12 branches, 8 spec rows, 4 error contracts:
  min_tests = max(5*2, 12, 8+4) = max(10, 12, 12) = 12 tests minimum
```

---

### Coverage Verification Loop

After Phase 7 code generation, Worker 7B collects coverage metrics. If below threshold:

```
Round 0 (initial): Worker 6A generates tests per §2-§7 templates
  → Worker 7B reports: line=82%, branch=78%
  → BELOW 90% threshold

Round 1 (supplement): Worker 6A-supplement spawned
  Input:
    - test_execution_report.json (includes uncovered lines/branches list)
    - spec_file (for behavior context)
    - existing test files (to avoid duplication)
  Task:
    - Analyze uncovered lines → identify missing scenarios
    - Generate ADDITIONAL tests for:
      - Uncovered branches (each conditional not yet tested)
      - Uncovered lines (defensive code, edge cases)
      - Missing error paths (exceptions not triggered)
    - Append new test methods to existing test files OR create supplementary file
  Output:
    - {ServiceName}SupplementaryTest.java (additional coverage tests)
    - Updated TEST_MANIFEST.json
  → Worker 7B re-runs: line=91%, branch=89%
  → Branch still below 90%

Round 2 (final supplement): Worker 6A-supplement spawned again
  Input: updated coverage report showing remaining gaps
  Task: Target specifically the remaining uncovered branches
  → Worker 7B re-runs: line=93%, branch=91%
  → ABOVE 90% ✅ — proceed to Phase 8

Max rounds: 2 (to prevent infinite loops)
If still < 90% after 2 rounds:
  → Log: [WARN] STR-6W002 "Coverage below 90% after 2 supplement rounds"
  → Proceed to Phase 8 with warning
  → Validation agent flags in Check 2.4 (but does not necessarily REJECT — 
    85-90% is WARN, below 85% is FAIL)
```

---

### Supplementary Test Template

```java
package {base.package}.{domain}.service;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@DisplayName("{ServiceName} Supplementary Coverage Tests")
class {ServiceName}SupplementaryTest {

    @Mock private {Dep1Type} {dep1Name};
    @InjectMocks private {ServiceName} service;

    // Tests targeting uncovered branches from coverage report

    @Test
    @DisplayName("Should handle {edgeCase} for {methodName}")
    void shouldHandle{EdgeCase}For{MethodName}() {
        // Given — setup for specific uncovered branch
        {setup targeting uncovered line/branch}
        
        // When
        var result = service.{methodName}({edgeCaseInput});
        
        // Then
        assertThat(result).{expected assertion};
    }

    @Test
    @DisplayName("Should cover default branch in {methodName}")
    void shouldCoverDefaultBranchIn{MethodName}() {
        // Given — input that triggers default/else path
        {setup for default branch}
        
        // When
        var result = service.{methodName}({defaultTriggerInput});
        
        // Then
        assertThat(result).{expected for default path};
    }
}
```

---

### Coverage Tool Integration

Worker 7B detects and uses the project's coverage tool:

| Build Tool | Coverage Plugin | Report Location | Parse Format |
|-----------|----------------|-----------------|--------------|
| Gradle | JaCoCo | `build/reports/jacoco/test/jacocoTestReport.xml` | XML |
| Maven | JaCoCo | `target/site/jacoco/jacoco.xml` | XML |
| Gradle (Kotlin) | Kover | `build/reports/kover/xml/report.xml` | XML |

**If no coverage tool configured:**
- Log: [WARN] STR-6E003 "Coverage tool not configured"
- Skip coverage gate (do not fail)
- Validation agent logs warning but proceeds

**Coverage Report Parsing:**
```
Extract for service class {package}.{ServiceName}:
  - INSTRUCTION_COVERED / INSTRUCTION_TOTAL → line coverage %
  - BRANCH_COVERED / BRANCH_TOTAL → branch coverage %
  - METHOD_COVERED / METHOD_TOTAL → method coverage %
  
Report in test_execution_report.json:
  "coverage": {
    "tool": "jacoco",
    "service_class": "{ServiceName}",
    "line_coverage": 93.2,
    "branch_coverage": 91.5,
    "method_coverage": 100.0,
    "uncovered_lines": [45, 67, 89],
    "uncovered_branches": [{"line": 52, "type": "if-else", "missed": "false-branch"}],
    "meets_threshold": true,
    "threshold": 90.0
  }
```

---

## Agent Self-Check

- [ ] 4 test categories generated (Contract, Behavior, Integration, Error Path)
- [ ] Tests are in RED state (fail without implementation)
- [ ] No mock-only tests — behavior is always asserted
- [ ] ≥1 test per extracted public method
- [ ] Integration test proves delegation equivalence
- [ ] Tests use project's discovered test framework and assertion style

## Source

**Owner:** preetha.ramaswamy@barclays.com  
**Review cadence:** Quarterly or on major version bump  
**Origin:** Barclays BUK Strangler Refactoring Plugin v3.0 — internal engineering  
**Classification:** Internal
