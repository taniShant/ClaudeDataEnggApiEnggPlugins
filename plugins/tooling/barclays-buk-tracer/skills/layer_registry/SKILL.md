---
name: layer-registry
description: "Pluggable layer model — define any layers, test frameworks, and ownership rules for a project. TRACER reasons over whatever layers are registered. No hardcoded assumptions."
user-invocable: false
---

# Skill: Layer Registry

> **Source:** TRACER Plugin v1.0.0 — BUK CIO Marketplace
> **Owner:** Barclays BUK Digital Channels
> **Review trigger:** On layer-registry.yaml schema change or attribution rule update
> **Status:** Reviewed

## Quick Start

```yaml
# Minimal layer-registry.yaml — two layers
version: "1.0"
project: "my-service"
layers:
  - id: "unit"
    name: "Unit Tests"
    frameworks:
      - name: "junit"
        language: "java"
        test_path_pattern: "src/test/**/*Test.java"
    owns: ["Business logic", "Edge cases"]
    hierarchy_position: 2   # lower = more expensive (device=1, unit=4)
  - id: "integration"
    name: "Integration Tests"
    frameworks:
      - name: "karate"
        language: "gherkin"
        test_path_pattern: "src/integrationTest/**/*.feature"
    owns: ["API contract", "DB round-trips"]
    hierarchy_position: 1

# Validate on load:
python3 -c "
import yaml
reg = yaml.safe_load(open('layer-registry.yaml'))
for l in reg['layers']:
    assert 'id' in l and 'hierarchy_position' in l, f'Missing required field in {l}'
print('Layer registry valid:', [l[\"id\"] for l in reg['layers']])
"
```

---

## Overview

TRACER does not hardcode any test layers. Every project defines its own layers in a `layer-registry.yaml` file. This skill defines the schema for that file, the rules for resolving which layer owns a given test scenario, and how to create or extend a registry for a new project.

---

## Source Attribution

**Primary sources:**
- TRACER Plugin v1.0.0 internal design — BUK CIO Marketplace
- Testing pyramid theory (unit → integration → component → E2E layer hierarchy)
- `barclays-buk-standards:testing` — Barclays-specific layer definitions as reference examples

**Training knowledge applied:**
- Multi-framework test stack patterns (JUnit, Spock, Karate, Cypress, Jest, Gherkin/Xray)
- Layer ownership heuristics (UI rendering → device/component; API contract → DAF/xapi layer)
- Hierarchy position conventions for mobile banking stacks

**Known limitations:**
- `hierarchy_position` is project-defined — TRACER provides conventions but not a universal standard
- The 5 attribution rules are heuristic; edge cases may require `auto-decision-agent` tie-breaking
- Does not validate that `test_path_pattern` globs match any files at registry creation time

---

## `layer-registry.yaml` Schema

Created once per project. Stored at the project root alongside `.tracer.yaml`.

```yaml
version: "1.0"
project: "my-project-name"
description: "Optional: what this project is"

layers:
  - id: "layer-id"               # snake_case, unique across this registry
    name: "Human Readable Name"  # display name
    description: "What this layer owns and tests"
    frameworks:                  # one or more test frameworks used at this layer
      - name: "jest"
        language: "javascript"
        test_path_pattern: "**/*.spec.ts"   # glob pattern to locate tests
    owns:                        # types of behavior this layer is responsible for
      - "UI rendering"
      - "User interaction"
      - "Navigation"
    does_not_own:                # explicit exclusions (optional but recommended)
      - "Business logic"
      - "Data persistence"
    hierarchy_position: 1        # 1 = highest (closest to user), ascending = lower
```

**`hierarchy_position`** determines retirement direction: a test at position 3 is retirable if equivalent coverage exists at position 1 or 2. Higher-position (lower number) tests are the most expensive to run.

---

## Minimal Registry Example (2-layer project)

```yaml
version: "1.0"
project: "simple-api"

layers:
  - id: "e2e"
    name: "End-to-End Tests"
    frameworks:
      - name: "cypress"
        language: "javascript"
        test_path_pattern: "cypress/e2e/**/*.cy.ts"
    owns:
      - "Full user journey"
      - "Cross-service integration"
    hierarchy_position: 1

  - id: "unit"
    name: "Unit Tests"
    frameworks:
      - name: "jest"
        language: "javascript"
        test_path_pattern: "src/**/*.test.ts"
    owns:
      - "Individual function behaviour"
      - "Business logic"
      - "Edge cases"
    hierarchy_position: 2
```

---

## Reference Example (Mobile Banking Stack)

This is a real-world reference. It is NOT the default — it is an example of how a multi-layer mobile stack might define its registry.

```yaml
version: "1.0"
project: "mobile-banking-products-hub"

layers:
  - id: "device"
    name: "Device Tests (Xray/SeeTest)"
    frameworks:
      - name: "xray"
        language: "gherkin"
        test_path_pattern: "TBA-release-features/**/*.feature"
      - name: "seetest"
        language: "gherkin"
        test_path_pattern: "TBA-release-features/**/*.feature"
    owns:
      - "End-to-end user journeys on physical devices"
      - "Native OS integration"
      - "Cross-platform rendering"
    does_not_own:
      - "Business logic"
      - "API contract"
      - "Config-driven behaviour"
    hierarchy_position: 1

  - id: "react_native"
    name: "React Native Layer"
    frameworks:
      - name: "jest"
        language: "javascript"
        test_path_pattern: "**/__tests__/**/*.spec.ts"
      - name: "stryker"
        language: "javascript"
        test_path_pattern: "**/__tests__/**/*.spec.ts"
    owns:
      - "UI rendering"
      - "Component behaviour"
      - "Bridge delegation"
      - "Analytics events"
    hierarchy_position: 2

  - id: "daf"
    name: "DAF / BFF Layer"
    frameworks:
      - name: "karate"
        language: "gherkin"
        test_path_pattern: "src/test/resources/**/*.feature"
      - name: "wiremock"
        language: "json"
        test_path_pattern: "src/test/resources/wiremock/**/*.json"
    owns:
      - "API contract"
      - "Request/response mapping"
      - "Caching behaviour"
      - "Circuit breaker"
    hierarchy_position: 3

  - id: "xapi"
    name: "XAPI / Backend Layer"
    frameworks:
      - name: "spock"
        language: "groovy"
        test_path_pattern: "src/test/groovy/**/*Spec.groovy"
      - name: "karate"
        language: "gherkin"
        test_path_pattern: "src/test/resources/**/*.feature"
    owns:
      - "Business logic"
      - "Service orchestration"
      - "Data transformation"
      - "Config-driven behaviour"
    hierarchy_position: 4
```

---

## Layer Attribution Rules

When assigning a behavior to a layer, apply these rules in order:

### Rule 1 — Match on `owns` list
If the behavior description aligns with a layer's `owns` list, assign it there.

### Rule 2 — Exclude via `does_not_own`
If a layer explicitly lists something in `does_not_own`, it cannot own that behavior even if `owns` partially matches.

### Rule 3 — Use `layer_hint` from spec
If the `.spec` file includes a `layer_hint`, use it as a tiebreaker when two layers could own a behavior.

### Rule 4 — Prefer lower hierarchy position for ambiguous cases
If a behavior could be tested at multiple layers with no clear owner, assign to the highest-position layer (lowest hierarchy number = most expensive). Flag for retirement analysis if lower-layer coverage already exists.

### Rule 5 — Flag `unknown` rather than guess
If attribution cannot be determined confidently, set `layer: unknown` and raise a flag. Never silently assign to a default layer.

---

## Creating a Registry for a New Project

If no `layer-registry.yaml` exists, the TRACER orchestrator must create one before any matrix work proceeds.

**Prompts to gather from user or infer from codebase:**

1. What are the test types/levels in this project?
2. What framework does each use?
3. Where do the test files live (path pattern)?
4. What does each layer "own" — what kinds of behaviour is it responsible for?
5. Which layer is most expensive to run (hierarchy position 1)?

**Minimum viable registry:** At least 1 layer defined. Single-layer projects are valid — TRACER still provides traceability, just without retirement analysis.

---

## Agent Self-Check

Before attributing any behavior to a layer, verify:
- [ ] `layer-registry.yaml` exists at project root
- [ ] At least one layer is defined with `id`, `frameworks`, and `owns`
- [ ] `hierarchy_position` is set for all layers (required for retirement analysis)
- [ ] No two layers share the same `id`
- [ ] Attribution follows the 5 rules above in order
- [ ] Any `layer: unknown` entries are flagged to the user, not silently set
