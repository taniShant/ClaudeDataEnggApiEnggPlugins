---
name: forward-spec
description: "Generate BDD specs from requirements, stories, or acceptance criteria. Produces .spec YAML with layer-attributed test scenarios ready for the traceability matrix."
user-invocable: false
---

# Skill: Forward Spec Generation

> **Source:** TRACER Plugin v1.0.0 — BUK CIO Marketplace
> **Owner:** Barclays BUK Digital Channels
> **Review trigger:** On .spec format change or forward spec generation rule update
> **Status:** Reviewed

## Quick Start

```yaml
# Minimal invocation via command
/tracer:trace-forward --docs story.md --module order_checkout

# Produces: order_checkout.spec (YAML)
# Behaviors extracted: 1 per AC item or "should" statement

# Inline requirements (no file needed)
/tracer:trace-forward \
  --docs "As a customer I want to see upgrade options. AC: 1. Eligible customers see Premier CTA. 2. Non-eligible see standard tier." \
  --module propositions_service

# After spec is written — verify it:
cat propositions_service.spec | python3 -c "import sys,yaml; d=yaml.safe_load(sys.stdin); print(len(d['behaviors']), 'behaviors')"
```

---

## Overview

Forward spec generation starts from **intent** — requirements, user stories, acceptance criteria, or any structured statement of what a system should do. It produces a `.spec` YAML file in the same BDD format used by the reverse spec generator, ensuring both flows produce a consistent artefact that TRACER's matrix can consume.

---

## Input Sources (Accepted)

Forward spec generation accepts any of the following as input:

| Input type | Examples |
|------------|---------|
| User story | "As a customer, I want to see my upgrade options so that I can choose a better plan" |
| Acceptance criteria | Numbered or bulleted AC list from a Jira story |
| Requirements doc | Confluence page, Word doc, plain text |
| API contract | OpenAPI/Swagger spec (operations → behaviors) |
| Figma screen | Screen content → UI behavior extraction |
| Change request | Delta description for legacy change flow |

---

## Output

A `.spec` YAML file with:
- `spec_source: forward` marker (TRACER-specific extension to base format)
- `entities` — domain objects mentioned in requirements
- `behaviors` — one per testable acceptance criterion
- `rules` — business rules explicitly stated in requirements
- `constraints` — limits, invariants, or dependencies called out

Each behavior includes `layer_hint` — the suggested owning layer based on what type of behavior it describes. Final layer assignment is confirmed by `layer_registry` skill.

---

## Source Attribution

**Primary sources:**
- TRACER Plugin v1.0.0 — BUK CIO Marketplace
- BDD (Behavior-Driven Development) specification conventions (Cucumber/Gherkin format)
- `barclays-buk-standards:testing` — layer attribution rules

**Training knowledge applied:**
- AC-to-behavior extraction patterns from Jira/Confluence story formats
- Observable outcome vs implementation distinction (BDD best practice)
- Layer hint assignment heuristics (UI → component/device, logic → service/xapi)

**Known limitations:**
- Cannot extract behaviors from ambiguous or contradictory ACs — flags instead
- `layer_hint` is a suggestion; the `layer_registry` skill makes the final attribution
- Does not directly generate behaviors from non-textual inputs (diagrams, wireframes)

---

## Spec Generation Rules

### 1. One behavior per AC

Each acceptance criterion maps to exactly one behavior. If an AC contains multiple assertions, split into separate behaviors.

**Input AC:**
> The customer sees only PREMIER upgrade option when BLUE is removed from config and they are not currently BLUE

**Two behaviors extracted:**
```yaml
- name: show_premier_upgrade_only_when_blue_removed_from_config
- name: suppress_blue_upgrade_for_non_blue_customers
```

### 2. Observable outcomes only

`then` clauses describe what the system returns, shows, or does — not how it achieves it.

**Wrong (implementation):**
```yaml
then:
  - Config service reads producthub.allowed.upgradeTiers property
```

**Right (observable):**
```yaml
then:
  - Upgrade section shows PREMIER option only
  - BLUE upgrade option is not present
```

### 3. Layer hint assignment

Assign a `layer_hint` based on the nature of the behavior:

| Behavior type | Layer hint |
|---------------|-----------|
| UI rendering, navigation, user interaction | closest UI layer |
| API contract, request/response shape | API/contract layer |
| Business logic, rules, calculations | service/logic layer |
| Data access, persistence, cache | data layer |
| End-to-end user journey | highest-level layer |
| Infrastructure, config | infrastructure layer |

`layer_hint` is a suggestion. The `layer_registry` skill makes the final assignment.

### 4. Traceability ID

Every behavior gets a `tracer_id` — a stable identifier used in the matrix:

```
Format: <module>_<behavior_name>
Example: producthub_show_premier_upgrade_only_when_blue_removed_from_config
```

### 5. Gap flagging

If an AC is ambiguous, contradictory, or missing preconditions — flag it:

```yaml
- name: ambiguous_behavior_name
  tracer_flags:
    - "AC does not specify expected state when customer has no products"
    - "Requires clarification before layer attribution"
```

Do not generate a behavior from an AC that cannot be tested. Flag instead.

---

## `.spec` Format Extension for TRACER

TRACER extends the base `.spec` format with two additional fields per behavior:

```yaml
behaviors:
  - name: "behavior_name"
    description: "..."
    given: [...]
    when: [...]
    then: [...]
    # TRACER extensions:
    tracer_id: "module_behavior_name"
    layer_hint: "service"           # suggested — confirmed by layer_registry
    spec_source: "forward"          # forward | reverse
    tracer_flags: []                # list of unresolved issues (empty if none)
```

These fields are ignored by the reverse spec generator tooling — they are TRACER-only metadata.

---

## Worked Example

**Input (Jira AC from EANDBLUE-7319):**
> AC1: When `producthub.allowed.upgradeTiers` does not include BLUE, the upgrade section must not show the Blue Rewards upgrade option
> AC2: An Essential customer (no active Blue Reward product) must see PREMIER upgrade only
> AC3: A BLUE customer (active product code 3950, endDate=null) must continue to see BLUE upgrade until the config is changed

**Generated spec (extract):**
```yaml
version: "1.0"
module: "blue_cease_upgrade_visibility"
description: "Upgrade section visibility rules for Blue Cease configuration change"
spec_source: "forward"

behaviors:
  - name: suppress_blue_upgrade_when_not_in_config
    description: Upgrade section hides Blue Rewards option when BLUE is absent from allowed upgrade tiers config
    given:
      - producthub.allowed.upgradeTiers config does not include BLUE
    when:
      - Customer loads the upgrade section
    then:
      - Blue Rewards upgrade option is not displayed
      - Only tiers present in producthub.allowed.upgradeTiers are shown
    tracer_id: "blue_cease_suppress_blue_upgrade_when_not_in_config"
    layer_hint: "service"
    spec_source: "forward"
    tracer_flags: []

  - name: essential_customer_sees_premier_only
    description: Essential customer (no active Blue Reward product) sees only PREMIER upgrade option
    given:
      - Customer has no product with code 3950 and endDate null
      - BLUE is not in producthub.allowed.upgradeTiers
    when:
      - Customer loads the upgrade section
    then:
      - PREMIER upgrade option is displayed
      - BLUE upgrade option is not displayed
    tracer_id: "blue_cease_essential_customer_sees_premier_only"
    layer_hint: "service"
    spec_source: "forward"
    tracer_flags: []
```

---

## Agent Self-Check

Before completing forward spec generation, verify:
- [ ] Every AC has produced at least one behavior (or a flag explaining why it couldn't)
- [ ] Every behavior has a unique `tracer_id`
- [ ] Every behavior has a `layer_hint` assigned
- [ ] No `then` clause describes implementation — only observable outcomes
- [ ] No AC with contradictions or missing preconditions silently skipped — flagged instead
- [ ] `.spec` file written and passes base bdd-specification validation rules
- [ ] `layer_registry` skill loaded before finalising `layer_hint` values
