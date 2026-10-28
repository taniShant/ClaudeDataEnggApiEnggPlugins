---
name: test-retirement
description: "Evidence-based test retirement — criteria for retiring tests, how to build the retirement evidence record, retirement vs deletion, and the keep decision"
user-invocable: false
---

# Skill: Test Retirement

> **Source:** TRACER Plugin v1.0.0 — BUK CIO Marketplace
> **Owner:** Barclays BUK Digital Channels
> **Review trigger:** On retirement eligibility criteria change or evidence record schema update
> **Status:** Reviewed

## Quick Start

```yaml
# In a .tracer.yaml — mark a behavior as a retirement candidate:
coverage_map:
  - behavior_id: "B002"
    behavior_name: "barclaycard_solus_customer_routed_to_alternative_content"
    coverage:
      - layer_id: "unit_spock"
        test_ids:
          - "CustomerSolusClassifierTest#should return BARCLAYCARD_SOLUS when customer has ONLY credit cards"
        hierarchy_position: 4
      - layer_id: "component_jest"
        test_ids:
          - "landing-screen-container.native.spec.tsx: should redirect to Legacy product hub screen for barclaycard solus"
        hierarchy_position: 2
    retirement_status: "candidate"   # ← retire-ready at 2 lower layers
    retirement_evidence: >
      Covered at unit_spock (pos 4) and component_jest (pos 2).
      Device test is redundant.
```

```bash
# Trigger retirement analysis on an existing matrix:
/tracer:trace-retire --matrix products_hub.tracer.yaml

# Output: retirement-report.md with retire-ready / needs-coverage / keep groups
```

**Key rule:** `retirement_status: "candidate"` requires confirmed coverage at ≥1 lower `hierarchy_position`. Never set without a populated `coverage` block.

---

## Overview

Test retirement is the process of decommissioning a test that is already covered at a lower, cheaper layer. Retirement is not deletion — it is an evidence-based decision recorded in the traceability matrix. A retired test has a permanent audit trail: what covered it, where, and when.

---

## Source Attribution

**Primary sources:**
- TRACER Plugin v1.0.0 — BUK CIO Marketplace
- Shift-left testing economics (Martin Fowler's Test Pyramid; cost-of-test-at-layer principles)

**Training knowledge applied:**
- Test lifecycle management patterns (retirement vs deletion distinction)
- Evidence-based decision patterns for regulated environments
- Keep decision criteria for hardware/biometric/regulatory test cases

**Known limitations:**
- Retirement analysis is recommendation-only; human sign-off is always required before executing retirements
- Cannot detect test fragility or reliability from matrix data alone — lower-layer test quality must be assessed separately
- Does not cover retirement for non-behavioural tests (performance, security, accessibility)

---

## Core Principle

**Retirement requires proof, not judgement.**

A test is retirable only when the traceability matrix contains a concrete test ID at a lower hierarchy layer covering the same behavior. The matrix entry IS the evidence. Without it, the test must stay.

---

## Retirement Eligibility Criteria

All four conditions must be true:

| # | Condition | How to verify |
|---|-----------|--------------|
| 1 | The behavior is defined in `.spec` | `tracer_id` exists in `.tracer.yaml` |
| 2 | The behavior is covered at a lower-hierarchy layer | `coverage_status: covered` at a layer with higher `hierarchy_position` number |
| 3 | The lower-layer test is concrete and locatable | `test_ids` contains real test references, not descriptions |
| 4 | No `tracer_flags` are unresolved on the behavior | `tracer_flags: []` on the behavior entry |

If any condition is false: **the test is not retirable.**

---

## What "Lower Layer" Means

Lower layer = higher `hierarchy_position` number in `layer-registry.yaml` = cheaper/faster to run.

A device test (position 1) is retirable if equivalent coverage exists at position 2, 3, or 4.  
A layer-2 test is retirable if covered at layer 3 or 4.  
A layer-4 (unit) test is never retirable — it is already at the lowest layer.

---

## Building the Retirement Evidence Record

The evidence record is written to `retirement_candidates` in `.tracer.yaml`:

```yaml
retirement_candidates:
  - layer: "xapi"                 # layer where coverage exists
    test_ids:
      - "PropositionsManagementServiceTest#shouldReturnPremierOnly"
    retirement_status: "candidate"
    retirement_evidence: >
      Behavior 'suppress_blue_upgrade_when_not_in_config' is covered by
      PropositionsManagementServiceTest#shouldReturnPremierOnly (Spock unit test,
      xapi layer, hierarchy_position 4). Device test EANDBLUE-8254 tests the same
      observable outcome at the UI layer. Lower-layer coverage confirmed.
```

The `retirement_evidence` string must be human-readable and self-contained — a future reader must understand the decision without needing to re-run the analysis.

---

## Retirement vs Deletion

| Action | When | Effect |
|--------|------|--------|
| **Retirement** | Lower-layer coverage proven | Test decommissioned, matrix records evidence permanently |
| **Deletion** | Test is wrong, duplicate with no spec mapping, or belongs to another suite | Test removed with no traceability obligation |
| **Keep** | Intentionally retained despite lower-layer coverage | `retirement_status: keep`, reason recorded |

**When to delete instead of retire:**
- Test has no `tracer_id` mapping in the matrix (orphan test)
- Test is an exact duplicate of another test at the same layer
- Test belongs in a different test suite (e.g. a navigation test in a business logic suite)

**When to keep despite retirement candidate status:**
- Test covers a user journey that lower layers cannot replicate (e.g. biometric auth, hardware sensors)
- Regulatory requirement mandates the test at that layer
- The lower-layer test is known to be fragile or unreliable

---

## The Keep Decision

When `retirement_status: keep` is set, the reason is mandatory:

```yaml
retirement_candidates:
  - layer: "xapi"
    test_ids:
      - "ProductHubServiceTest#shouldReturnCategories"
    retirement_status: "keep"
    retirement_evidence: >
      Keeping device test EANDBLUE-5099 despite xapi coverage.
      Reason: tests device-specific rendering of category tiles which
      cannot be verified at the service layer. Distinct observable outcome.
```

---

## Retirement Analysis Workflow

1. **Load the matrix** — read `.tracer.yaml`
2. **Load the layer registry** — get `hierarchy_position` for all layers
3. **Find retirement candidates** — behaviors where `coverage_status: covered` at layer N, and tests exist at layer M where M has lower `hierarchy_position` than N
4. **Verify each candidate** — confirm test IDs are real and the behaviors are equivalent
5. **Build evidence records** — write `retirement_candidates` entries
6. **Flag edge cases** — any candidate that might warrant `keep` instead of `candidate`
7. **Present findings** — summary of candidates, evidence, and keep recommendations
8. **Do not action retirements** — TRACER records candidates; the team decides and executes

**TRACER recommends. Humans decide.**

---

## Retirement Summary Report Format

```
RETIREMENT ANALYSIS — <module>
===============================
Total behaviors:        12
Retirement candidates:   5
  → Ready to retire:     4  (full evidence, no flags)
  → Review needed:       1  (keep candidate — see flags)
Keep decisions:          1
Already retired:         2

CANDIDATES READY TO RETIRE
---------------------------
Behavior: suppress_blue_upgrade_when_not_in_config
  High-layer tests:  EANDBLUE-8254, EANDBLUE-8277, EANDBLUE-8300  [device, pos 1]
  Covered by:        PropositionsManagementServiceTest#shouldReturnPremierOnly  [xapi, pos 4]
  Evidence:          Spock unit test, xapi layer, confirmed covered

Behavior: essential_customer_sees_premier_only
  High-layer tests:  EANDBLUE-8335, EANDBLUE-8358, EANDBLUE-8381  [device, pos 1]
  Covered by:        getproductshubdata_sdh_cached.feature:TC12  [xapi, pos 4]
  Evidence:          Karate integration test, RIT615 env, confirmed covered

REVIEW NEEDED
-------------
Behavior: blue_customer_continues_to_see_blue
  High-layer tests:  EANDBLUE-8255  [device, pos 1]
  Flag: No test found at xapi layer — not retirable until covered
```

---

## Agent Self-Check

Before finalising retirement analysis, verify:
- [ ] All 4 eligibility criteria checked for each candidate
- [ ] `retirement_evidence` is human-readable and self-contained for every candidate
- [ ] `keep` decisions have a mandatory reason recorded
- [ ] No candidate marked `retired` — only `candidate` (humans action retirements)
- [ ] Behaviors with `tracer_flags` not listed as candidates
- [ ] Retirement summary report produced and presented to user
- [ ] Matrix updated with `retirement_candidates` entries before presenting report
