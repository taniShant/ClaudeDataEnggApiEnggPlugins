# TRACER Methodology

## Core Idea

Tests accumulate at expensive layers (UI, device, E2E) covering logic that could be proven at cheaper layers (unit, integration, service). This happens gradually — each test is added for a good reason at the time — and is invisible until someone maps coverage across layers.

TRACER makes that map explicit, keeps it current, and turns it into evidence.

---

## The 3 Flows

### Flow A — Forward Spec

```
Requirements / Stories / ACs
        ↓
  Forward Spec Gen           (tracer-spec-agent, forward_spec skill)
        ↓
  .spec YAML
        ↓
  Layer Attribution           (tracer-traceability-agent, layer_registry skill)
        ↓
  Test Scan
        ↓
  .tracer.yaml Matrix
```

**Entry point:** Intent exists before code.  
**Output:** Spec + matrix with attribution and coverage gaps identified upfront.

---

### Flow B — Reverse Spec

```
Existing Code / Tests
        ↓
  Reverse Spec Gen            (tracer-spec-agent → barclays-buk-reverse-spec-generator)
        ↓
  .spec YAML + TRACER extensions (tracer_id, layer_hint, spec_source)
        ↓
  Layer Attribution
        ↓
  Test Scan
        ↓
  .tracer.yaml Matrix
```

**Entry point:** Code exists, no intent documented.  
**Output:** Spec derived from code + matrix mapping what is covered where.

---

### Flow C — Legacy Change

```
Legacy Code (no docs)           New Change Request (delta)
        ↓                               ↓
  Reverse Spec (baseline)        Forward Spec (target)
        ↓                               ↓
  baseline.spec              ──→  Gap Analysis (delta behaviors)
                                         ↓
                                  Layer Attribution (delta only)
                                         ↓
                                  Test Scan
                                         ↓
                                  .tracer.yaml Matrix (delta behaviors)
```

**Entry point:** Both legacy code AND a new change exist simultaneously.  
**When to use this flow:** ONLY when there is a delta. Legacy code alone → use Flow B.  
**Output:** Baseline spec (audit trail), target spec (what changes), gap analysis, matrix for delta behaviors.

---

## The Traceability Matrix

The matrix is a `.tracer.yaml` file with bidirectional linkage:

```
Spec Behavior  ←→  Layer  ←→  Test IDs
```

Forward navigation: given a behavior, find what tests cover it and at which layer.  
Reverse navigation: given a test ID, find which behavior it covers and at which layer.

The matrix is a living document. It is updated when specs change, tests are added, or layers are reconfigured.

---

## The Layer Registry

Layers are not hardcoded. Each project defines its own `layer-registry.yaml`:
- Any number of layers
- Any test framework per layer
- `hierarchy_position` determines retirement direction (1 = most expensive, highest number = cheapest)

TRACER reasons over whatever layers are registered. The mobile banking stack (RN/DAF/XAPI/Device) is a reference example, not the default model.

---

## Test Retirement

Retirement is evidence-based, not opinion-based:

1. Behavior is in the spec (`tracer_id` exists in matrix)
2. Covered at a lower-hierarchy layer (`coverage_status: covered` at higher `hierarchy_position`)
3. Lower-layer test ID is concrete and locatable
4. No unresolved flags on the behavior

If all four are true: retirement candidate. The matrix entry is the evidence.

**Retirement ≠ deletion.** A retired test has a permanent record:
- What behavior it covered
- What lower-layer test now covers it
- When it was retired

This prevents the same test from being re-written in future.

---

## Worked Example (Generic)

**Project:** Order Management Service  
**Layer registry:**

```yaml
layers:
  - id: e2e          hierarchy_position: 1   (Cypress)
  - id: contract     hierarchy_position: 2   (Pact)
  - id: integration  hierarchy_position: 3   (JUnit + Testcontainers)
  - id: unit         hierarchy_position: 4   (JUnit + Mockito)
```

**Scenario:** E2E test `TC-445` tests "order total calculated correctly with discount."

**After running `/tracer:trace-reverse`:**

```yaml
behaviors:
  calculate_order_total_with_discount:
    layer: unit
    test_ids:
      - OrderCalculatorTest#shouldApplyDiscountToOrderTotal
    coverage_status: covered
    retirement_candidates:
      - layer: e2e
        test_ids: [TC-445]
        retirement_status: candidate
        retirement_evidence: >
          Covered by OrderCalculatorTest#shouldApplyDiscountToOrderTotal
          (JUnit unit test, unit layer, hierarchy_position 4).
          E2E test TC-445 exercises same calculation logic through UI.
```

**Result:** TC-445 is a retirement candidate. The matrix is the evidence.

---

## Integration with barclays-buk-reverse-spec-generator

TRACER uses the reverse spec generator as a dependency for Flow B and the baseline phase of Flow C. The dependency:
- Extracts entities, behaviors, rules, constraints from source code
- Produces `.spec` YAML in BDD format
- Maintains `.convergence.yaml` for spec-code alignment

TRACER adds on top:
- `tracer_id` per behavior (stable matrix key)
- `layer_hint` per behavior (suggested layer attribution)
- `spec_source` per behavior (forward | reverse | baseline)
- `.tracer.yaml` matrix (owned entirely by TRACER)

The two plugins are complementary. The reverse spec generator owns the spec-code convergence loop. TRACER owns the spec-test-layer traceability layer.
