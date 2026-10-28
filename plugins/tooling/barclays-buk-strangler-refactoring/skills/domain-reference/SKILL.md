---
name: strangler-domain-reference
description: Domain knowledge for strangler pattern extraction - extraction patterns, service architectures, validation heuristics, and lessons learned from prior extractions
color: blue
Source: Barclays BUK Strangler Refactoring Plugin v3.2
Owner: preetha.ramaswamy@barclays.com
Review trigger: Quarterly or on major version bump
user-invocable: false
Status: Published
---
> **Source:** Strangler Refactoring Plugin v3.2 — Domain Reference — Extraction Patterns and Lessons Learned (internal)
> **Owner:** Preetha Ramaswamy / BUK CIO Engineering
> **Review trigger:** Quarterly or after each major extraction project
> **Status:** Published
> Source documents are Internal — Restricted.


## Quick Start

```
Phase: 0-4, 8 (discovery through validation)
Worker: Various (phase-gated sections loaded per phase)
Load: orchestrator passes domain-reference §1-2 (Phase 0-1), §3-5 (Phase 2-3), §4 (Phase 4), §3 (Phase 8)
Use: Ground truth for extraction patterns, service architectures, validation rules
Model: varies by phase (fast for discovery, balanced for planning/validation)
```

# Strangler Refactoring Domain Reference Skill

Ground truth for all strangler pattern extraction decisions. This skill is phase-gated: each agent loads only the sections it needs.

---

## § 1-2: CLASSIFICATION & PATTERN INVENTORY (Phase 0-1 only)

### Extraction Patterns

**Pattern: Orchestrator (Delegation Hub)**
- Use when: 3+ distinct domains, shared entry point
- Structure: Central orchestrator + 3-5 specialized services
- Example: AppPolicyRefactoringServiceImpl → WealthManagementPolicyService (orchestrator) + 5 specialized services
- Risk: Low (orchestrator is thin wrapper)
- Token cost: Medium (3+ agent batches)

**Pattern: Facade (Single Proxy)**
- Use when: 1-2 domains, clear responsibilities
- Structure: Single facade service + 2-3 helpers
- Example: PaymentPolicyService (facade) + PaymentValidator + PaymentProcessor
- Risk: Low
- Token cost: Low

**Pattern: Delegation Chain**
- Use when: Sequential dependencies (order matters)
- Structure: Service A → Service B → Service C
- Example: AuthenticationPolicy → AuthorizationPolicy → AuditPolicy
- Risk: Medium (dependency order must be correct)
- Token cost: Low

**Pattern: Repository (Data Aggregation)**
- Use when: Multiple data sources, single retrieval interface
- Structure: Repository service + data accessors
- Example: CustomerDataRepository (pulls from CRM + Banking + Cards)
- Risk: High (complex transaction handling)
- Token cost: High

---

### Domain Classification

**Financial Domains:**
- Payment Processing (put*, process*Payment)
- Card Management (Card*, DebitCard*, CreditCard*)
- Wealth Management (Wealth*, Investment*, Reward*)
- Lending (Loan*, Mortgage*, Credit*)
- Savings (Savings*, Account*, Deposit*)

**Non-Financial Domains:**
- Authentication (Auth*, Security*, Login*)
- Notification (Notify*, Alert*, Message*)
- Configuration (Config*, Feature*, Flag*)
- User Management (User*, Profile*, Customer*)

---

### Method Naming Conventions (Barclays)

| Prefix | Domain | Count | Pattern |
|--------|--------|-------|---------|
| put* | Configuration | varies | PUT operation (idempotent) |
| get* | Retrieval | varies | GET operation |
| process* | Business Logic | varies | Core processing |
| validate* | Validation | varies | Validation check |
| calculate* | Calculation | varies | Numeric calculation |
| transform* | Transformation | varies | Data transformation |
| notify* | Communication | varies | Notify external system |

---

## § 3-5: EXTRACTION STRATEGY & VALIDATION (Phase 4 extraction only)

### Service Mapping Templates

**Step 1: Identify Methods by Domain**
```
Domain: {DOMAIN_NAME}
Methods: [method1, method2, ...]
Count: N
Shared Dependencies: [dep1, dep2, ...]
```

**Step 2: Check Dependencies**
```
Intra-domain dependencies: {methods that call other methods in same domain}
Inter-domain dependencies: {domains this domain calls}
External dependencies: {frameworks, utilities, external services}
```

**Step 3: Create Service Class**
```
Service Name: {Domain}PolicyService or {Domain}Service
Location: com.barclays.mobile.gateway.service.solus.policy.{Domain}PolicyService
Responsibility: {brief description}
Public Methods: {extracted methods}
Dependencies (injected): {list of @Autowired fields}
```

---

### Validation Rules (Batched Validator)

**Rule 1: Logic Fidelity (>95% pure movement)**

Check that extraction is pure code movement, not logic changes:
- Original method body = Extracted method body (100% match or refactored-but-equivalent)
- No new lines added (except necessary wiring)
- No logic simplified/hardcoded
- No error handling changed
- Exceptions remain identical

Validation: Run git diff, count pure movement % 

**Rule 2: TDD Behavior Validation**

Check that tests validate behavior, not just coverage:
- For each extracted method:
  - ≥1 test validates input → expected behavior
  - ≥1 test validates error case
  - No pure mock tests (assert on mocks, not behavior)
  - Integration test proves delegation equivalence
- New service: ≥1 integration test calls orchestrator + validates delegation

**Rule 3: Anti-Pattern Detection**

Check that extracted services don't violate architecture:
- No "god service" (>15 public methods) created
- No new external dependencies introduced
- No circular dependencies between services
- No increase in coupling from original monolith
- Services maintain single responsibility

---

### Contract Preservation Guarantee

**Non-negotiable:**
- Public method signatures MUST remain 100% identical
- Return types unchanged
- Exception types unchanged
- Calling code requires ZERO modification
- If contract changes needed: Use adapter pattern, don't break contract

**Check:**
```
Original: public PolicyResult processPayment(PaymentRequest req) throws PaymentException
Extracted: public PolicyResult processPayment(PaymentRequest req) throws PaymentException
           { return paymentService.process(req); }

✅ Contract preserved (identical signature, same exceptions)
```

---

### Test Patterns for Extracted Services

**Unit Test Pattern:**
```java
@RunWith(MockitoJUnitRunner.class)
public class {Service}Test {
  @Mock private DependencyA depA;
  @InjectMocks private {Service} service;
  
  @Test public void should{Behavior}When{Condition}() {
    // Arrange
    when(depA.method()).thenReturn(expected);
    
    // Act
    Result result = service.publicMethod(input);
    
    // Assert
    assertEquals(expected, result);
    verify(depA).method();  // Assert actual behavior, not mock
  }
}
```

**Integration Test Pattern:**
```java
@SpringBootTest
public class {Service}IntegrationTest {
  @Autowired private {Service} service;
  @Autowired private TestDatabase db;
  
  @Test public void shouldDelegateEquivalently() {
    // Original monolith behavior
    OldService old = getOriginalMonolith();
    Result originalResult = old.publicMethod(input);
    
    // New service behavior
    Result newResult = service.publicMethod(input);
    
    // Assert equivalence
    assertEquals(originalResult, newResult);
  }
}
```

---

## § 6-7: LESSONS LEARNED & RISK MITIGATION

### Common Pitfalls (Avoid These)

❌ **Pitfall: Over-extraction**
- Extracting too many domains at once
- Recommendation: <8 methods per task

❌ **Pitfall: Tight Coupling**
- Creating services with too many dependencies
- Check: Service should have ≤5 injected dependencies

❌ **Pitfall: Lost Business Logic**
- Copy-pasting code instead of pure movement
- Check: git diff should show deletions = additions (line count)

❌ **Pitfall: Mock Overuse**
- Tests that mock everything, validate nothing
- Check: Integration tests must hit real code paths

---

### Phase 2F (Wealth Management) Lessons

**Success Pattern: Orchestrator + Specialized Services**

From WealthManagementPolicyService extraction (Phase 2F):
- 14 methods → 1 orchestrator + 5 specialized services
- Orchestrator: Thin wrapper (2 public methods)
- Specialized services: 2-3 methods each
- Result: 97.2% logic fidelity, all tests pass

**Applied Pattern:**
- WealthManagementPolicyService (orchestrator)
  - WealthInvestmentPolicyService (3 methods)
  - WealthAccountPolicyService (3 methods)
  - WealthCardsPolicyService (1 method)
  - WealthRewardsPolicyService (3 methods)
  - WealthAPIIntegrationService (4 methods)

**Key Success Factors:**
1. Clear domain boundaries (investment, accounts, cards, rewards, API)
2. Minimal inter-service calls (mostly orchestrator coordination)
3. Comprehensive integration tests (behavior equivalence proven)
4. Conservative extraction (pure movement, zero logic changes)

---

### Risk Assessment Matrix

| Risk Factor | Low Risk | Medium Risk | High Risk |
|-------------|----------|-------------|-----------|
| Domain coupling | 0-1 inter-domain calls | 2-3 inter-domain calls | >3 inter-domain calls |
| Service complexity | <5 methods | 5-10 methods | >10 methods |
| Dependencies injected | <3 | 3-5 | >5 |
| Test coverage | >95% | 80-95% | <80% |
| Extraction scope | <8 methods | 8-15 methods | >15 methods |

---

## § 8: PHASE-GATED LOADING GUIDE

**Phase 0 (Analysis):** Load §1-2 only
- Determine target complexity
- Identify extraction patterns

**Phase 1 (Discovery):** Load §1-2 only
- Classify domains
- Detect naming patterns

**Phase 2 (Planning):** Load §4-5 only
- Service mapping templates
- Risk assessment

**Phase 3 (Tasks):** Load §4 only
- Service templates for task descriptions

**Phase 4 (Extraction):** Load §3-5, §8
- All validation rules
- Test patterns
- Risk mitigation
- This section (phase-gated loading guide)

**Phase 5 (Validation):** Load §3 only
- Validation rules only

---

## Token Optimization Notes

This skill is designed for phase-gated loading to reduce token waste:

- **Phase 0-1**: §1-2 (3-4 KB) — don't load extraction rules yet
- **Phase 2-3**: §4-5 (5-6 KB) — don't load validation rules yet
- **Phase 4**: §3-5 (10-12 KB) — full extraction + validation context

**Total by phase:**
- Discovery: ~4 KB
- Planning: ~6 KB
- Extraction: ~12 KB

**vs. unoptimized (loading full skill every phase):**
- Every phase: ~25 KB

**Savings: ~50-60% token reduction from phase-gated loading**

---

## Agent Self-Check

- [ ] Only phase-gated sections loaded (not full skill — check §N reference)
- [ ] Domain classification based on runtime inspection (not hardcoded)
- [ ] Validation rules applied match the threshold for this version (85% fidelity)
- [ ] Anti-pattern list includes god service, circular deps, coupling limits
- [ ] Extraction patterns reference discovered API conventions
- [ ] Lessons learned section consulted for known failure modes

## Source

**Owner:** preetha.ramaswamy@barclays.com  
**Review cadence:** Quarterly or on major version bump  
**Origin:** Barclays BUK Strangler Refactoring Plugin v2.0→v3.0 — internal engineering  
**Classification:** Internal
