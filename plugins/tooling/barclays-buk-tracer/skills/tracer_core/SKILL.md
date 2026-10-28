---
name: tracer-core
description: "TRACER core methodology — the 3 flows (forward, reverse, legacy change), principles, flow selection rules, and non-negotiables"
user-invocable: false
---

# Skill: TRACER Core Methodology

> **Source:** TRACER Plugin v1.0.0 — BUK CIO Marketplace
> **Owner:** Barclays BUK Digital Channels
> **Review trigger:** On TRACER methodology update or flow model change
> **Status:** Reviewed

## Quick Start

```bash
# Flow A — you have requirements, no code yet:
/tracer:trace-forward --docs story.md --module checkout_service

# Flow B — code and tests exist, no specs:
/tracer:trace-reverse --src src/services/ --module checkout_service

# Flow C — legacy code + new change request:
/tracer:trace-legacy --src src/ --delta change-request.md --module checkout_service

# Xray reduction — scan repos and classify device tests:
/tracer:trace-scan \
  --repos /local/mobile-app,/local/java-backend \
  --xray EANDBLUE-1234 \
  --module products_hub \
  --report both
```

**Which flow?** If you only have a Jira ticket or AC → Forward. If you have source code with tests → Reverse. If you have both plus a change request → Legacy Change. If you have an Xray test plan and want to know which tests can be retired → Scan.

---

## Overview

TRACER builds a bidirectional traceability matrix between specs, test scenarios, and test layers. It operates in one of three flows, selected based on what exists at the time of invocation. The flows are mutually exclusive entry points — not a sequential pipeline.

---

## Source Attribution

**Primary sources:**
- TRACER Plugin v1.0.0 internal design — BUK CIO Marketplace
- `barclays-buk-standards:testing` — testing layer hierarchy principles

**Training knowledge applied:**
- BDD behavior extraction patterns (Given/When/Then structure)
- Testing pyramid and shift-left testing economics
- Layer attribution heuristics for multi-layer test suites

**Known limitations:**
- Flow selection heuristics are deterministic but may not cover all edge-case project structures
- Layer attribution for non-standard frameworks may require manual override
- Does not address non-functional requirements (performance, security) — behavioural specs only

---

## The 3 Flows

### Flow A — Forward Spec (greenfield / requirements-first)

**Trigger:** Requirements, stories, or acceptance criteria exist. No code written yet.

```
Requirements / Stories / ACs
        ↓
  Forward Spec Gen
  (what SHOULD the system do?)
        ↓
  Test Scenarios with Layer Attribution
  (which layer owns each scenario?)
        ↓
  Traceability Matrix
  (spec ↔ scenario ↔ layer ↔ test ID)
```

**When to use:**
- New feature with documented intent
- Any greenfield work where specs precede code
- Test strategy planning before implementation begins

**Output:** `.spec` YAML + populated `.tracer.yaml` matrix

---

### Flow B — Reverse Spec (code-first / no requirements)

**Trigger:** Code and/or tests already exist. No formal specs.

```
Existing Code / Tests
        ↓
  Reverse Spec Gen
  (what does it ACTUALLY do?)  ← delegates to barclays-buk-reverse-spec-generator
        ↓
  Layer Attribution
  (map each behavior to owning layer)
        ↓
  Traceability Matrix
  (spec ↔ scenario ↔ layer ↔ test ID)
```

**When to use:**
- Legacy code with no requirements docs
- Inherited test suites with no spec coverage
- Audit: understand what is actually being tested and at what layer

**Output:** `.spec` YAML (from reverse spec generator) + populated `.tracer.yaml` matrix

---

### Flow C — Legacy Change (reverse → delta → forward)

**Trigger:** Legacy code exists AND a new change request has arrived.

```
Legacy Code (no requirements)
        ↓
  Reverse Spec Gen (Flow B)
  (baseline: what does it currently do?)
        ↓
  Understand the Delta
  (new ask / change request / story)
        ↓
  Forward Spec Gen (Flow A)
  (target: what should it do after the change?)
        ↓
  Gap Analysis
  (baseline spec vs target spec = scope of change)
        ↓
  Test Scenarios for Delta Only
        ↓
  Traceability Matrix (updated)
```

**When to use:**
- Adding a feature to legacy code that has no specs
- Changing behaviour where the existing behaviour was never documented
- The reverse spec provides the baseline; the forward spec defines the target

**Key rule:** Chaining reverse → forward is ONLY valid here. It is not the default flow and should not be applied unless a delta exists.

**Output:** Baseline `.spec` + target `.spec` + gap analysis + updated `.tracer.yaml`

---

## Flow Selection Rules

| What exists | Flow to use |
|-------------|-------------|
| Requirements/stories only | **A — Forward** |
| Code/tests only, no change needed | **B — Reverse** |
| Code/tests only, new change requested | **C — Legacy Change** |
| Code + requirements already exist | **A — Forward** (requirements are the entry point) |
| Existing test suite to audit/retire | **B — Reverse** then `/trace-retire` |

---

## Core Principles

1. **Traceability is evidence, not documentation.** The matrix must link to real test IDs — not to intentions or plans.

2. **Retirement requires proof.** A test is retirable when the matrix shows coverage at a lower layer. The evidence is in the matrix, not in someone's judgement.

3. **Layer attribution is mandatory.** Every test scenario must be assigned to exactly one owning layer. Unowned scenarios are a coverage gap.

4. **The matrix is bidirectional.** You must be able to navigate: spec → scenarios → layer → test IDs, AND test ID → layer → scenario → spec.

5. **Flows are not sequential by default.** Do not chain A → B or B → A unless the legacy change condition is met.

6. **Specs describe observable behaviour.** Not implementation. Not infrastructure. What the system does from the outside.

---

## Non-Negotiables

- Never mark a test as retirable without a matrix entry proving lower-layer coverage
- Never assign a scenario to multiple layers — if ambiguous, flag for human decision
- Never skip layer attribution when generating test scenarios
- Always load `layer_registry` skill before attributing scenarios to layers
- Always load `traceability_matrix` skill before writing or updating `.tracer.yaml`

---

## Agent Self-Check

Before starting any TRACER flow, confirm:
- [ ] Flow selected matches the actual state of what exists (requirements vs code vs both + delta)
- [ ] `layer-registry.yaml` exists and has at least one layer defined before any matrix work
- [ ] No `AskUserQuestion` calls in the pipeline — ambiguity routed to `auto-decision-agent`
- [ ] Both `.spec` and `.tracer.yaml` artefacts go through `tracer-validator-agent` before writing
- [ ] All file writes delegated to `tracer-file-writer-agent` — workers return content, not write directly
- [ ] `tracer_flags` reviewed before marking any behavior `coverage_status: covered`
- [ ] Retirement analysis only runs when explicitly triggered (`trace-retire`) or flow is `retire`
