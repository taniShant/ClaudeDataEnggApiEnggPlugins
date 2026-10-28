---
name: traceability-matrix
description: "Traceability matrix schema, .tracer.yaml state file format, bidirectional navigation rules, and matrix update lifecycle"
user-invocable: false
---

# Skill: Traceability Matrix

> **Source:** TRACER Plugin v1.0.0 — BUK CIO Marketplace
> **Owner:** Barclays BUK Digital Channels
> **Review trigger:** On .tracer.yaml schema change or matrix lifecycle update
> **Status:** Reviewed

## Quick Start

```bash
# Build matrix from spec + registry (Phase 4 of trace-scan/trace-reverse):
/tracer:trace-reverse --src src/ --module order_service
# → writes order_service.tracer.yaml

# Read the matrix summary:
python3 -c "
import yaml
m = yaml.safe_load(open('order_service.tracer.yaml'))
s = m['summary']
print(f'Behaviors: {s[\"total_behaviors\"]} | Covered: {s[\"covered\"]} | Partial: {s[\"partial\"]} | Keep: {s[\"keep\"]}')
print(f'Retire-ready: {s[\"retire_ready\"]} | Needs coverage: {s[\"needs_new_coverage\"]}')
"

# Navigate: which tests cover behavior B002?
python3 -c "
import yaml
m = yaml.safe_load(open('order_service.tracer.yaml'))
b = next(b for b in m['coverage_map'] if b['behavior_id'] == 'B002')
for layer in b.get('coverage', []):
    print(layer['layer_id'], '→', layer['test_ids'])
"
```

---

## Overview

The traceability matrix is TRACER's primary output artefact. It is a bidirectional map between specs, test scenarios, test layers, and concrete test IDs. It is stored as `<module>.tracer.yaml` and maintained as a living document — updated whenever specs, tests, or layers change.

---

## Source Attribution

**Primary sources:**
- TRACER Plugin v1.0.0 schema design — BUK CIO Marketplace
- Barclays BUK test traceability requirements (internal standards)

**Training knowledge applied:**
- Bidirectional traceability matrix patterns from requirements engineering
- Test evidence record patterns for audit and regulatory compliance contexts
- YAML schema design for mutable, versioned lifecycle artefacts

**Known limitations:**
- Schema v1.0 does not support many-to-many spec-to-layer mappings — one owning layer per behavior
- `iteration` counter is informational only; no conflict resolution on concurrent updates
- `retirement_candidates` hierarchy validation is manual — the schema does not enforce that candidates are at a strictly lower `hierarchy_position`

---

## `.tracer.yaml` Schema

```yaml
version: "1.0"
module: "module_name"           # snake_case, matches .spec module name
spec_file: "module.spec"        # path to associated .spec file
spec_source: "forward"          # forward | reverse | legacy_change
layer_registry: "layer-registry.yaml"  # path to layer registry
last_updated: "2026-09-30T10:00:00Z"
iteration: 1                    # increments on each matrix update

summary:
  total_behaviors: 12
  covered: 8                    # has at least one test ID at attributed layer
  partial: 2                    # has test IDs but not at all required layers
  uncovered: 2                  # no test IDs found at attributed layer
  retirement_candidates: 3      # covered at lower layer than attributed
  unknown_layer: 0              # attribution unresolved

behaviors:
  behavior_name:
    tracer_id: "module_behavior_name"
    spec_source: "forward"       # forward | reverse
    layer: "xapi"                # owning layer id from layer-registry
    layer_status: "confirmed"    # confirmed | hint | unknown
    test_ids:                    # concrete test IDs at the owning layer
      - "ProductHubServiceTest#shouldReturnUpgradeTiersForPremierCustomer"
    coverage_status: "covered"   # covered | partial | uncovered
    retirement_candidates:       # tests at HIGHER hierarchy layers (more expensive)
      - layer: "device"
        test_ids:
          - "EANDBLUE-8254"
          - "EANDBLUE-8277"
        retirement_status: "candidate"  # candidate | retired | keep
        retirement_evidence: "Covered by ProductHubServiceTest at xapi layer"
    tracer_flags: []             # unresolved issues
    notes: ""
```

---

## Bidirectional Navigation

The matrix must support both directions of traversal:

### Forward (spec → test)
Given a spec behavior, find what tests cover it and at which layer.

```
spec: show_premier_upgrade_only_when_blue_removed_from_config
  → layer: xapi
  → test_ids: [PropositionsManagementServiceTest#shouldReturnPremierOnlyWhenBlueRemovedFromConfig]
  → retirement_candidates: [EANDBLUE-8254, EANDBLUE-8277] at device layer
```

### Reverse (test → spec)
Given a test ID, find which spec behavior it covers and at which layer.

```
test_id: EANDBLUE-8254
  → layer: device
  → behavior: show_premier_upgrade_only_when_blue_removed_from_config
  → coverage_status: retirement_candidate (covered at xapi layer)
```

Both directions must be resolvable from the `.tracer.yaml` file without needing to read source code.

---

## Coverage Status Values

| Status | Meaning |
|--------|---------|
| `covered` | At least one concrete test ID exists at the attributed layer |
| `partial` | Tests exist but not covering all `then` clauses of the behavior |
| `uncovered` | No test ID found at the attributed layer |
| `retirement_candidate` | Covered at a lower layer — higher-layer tests are candidates for retirement |

---

## Retirement Status Values

Per entry in `retirement_candidates`:

| Status | Meaning |
|--------|---------|
| `candidate` | Lower-layer coverage confirmed — eligible for retirement |
| `retired` | Test has been decommissioned — matrix is the evidence record |
| `keep` | Intentionally kept despite lower-layer coverage (e.g. journey test, regulatory) |

---

## Matrix Update Lifecycle

The matrix is updated at these lifecycle events:

| Event | What changes |
|-------|-------------|
| New spec generated (forward or reverse) | New behavior entries added, `coverage_status: uncovered` until tests mapped |
| Tests scanned and matched | `test_ids` populated, `coverage_status` updated |
| Layer registry updated | Re-run layer attribution, update `layer` and `layer_status` |
| Test retired | `retirement_status: retired` set, evidence recorded |
| Spec amended | Behavior entry updated, `iteration` incremented |
| New test added | Scan for matches, update `test_ids` |

---

## Matrix Integrity Rules

1. **Every behavior in `.spec` must have a corresponding entry in `.tracer.yaml`.** No orphan specs.

2. **Every `test_id` must be a real, locatable test.** Not a description — a concrete reference (class#method, feature:scenario, Xray ticket ID).

3. **`layer` must reference a valid `id` from `layer-registry.yaml`.** Foreign key constraint.

4. **`retirement_candidates` only valid when `coverage_status: covered` at a lower hierarchy layer.** Cannot mark a test as a retirement candidate if the owning layer has no coverage.

5. **`retirement_status: retired` requires `retirement_evidence` to be non-empty.** The evidence string is the audit trail.

6. **`tracer_flags` must be empty before marking `coverage_status: covered`.** Unresolved flags mean coverage is uncertain.

---

## Worked Example (Partial Matrix)

```yaml
version: "1.0"
module: "blue_cease_upgrade_visibility"
spec_file: "blue_cease_upgrade_visibility.spec"
spec_source: "forward"
layer_registry: "layer-registry.yaml"
last_updated: "2026-09-16T14:30:00Z"
iteration: 3

summary:
  total_behaviors: 3
  covered: 2
  partial: 0
  uncovered: 1
  retirement_candidates: 2
  unknown_layer: 0

behaviors:
  suppress_blue_upgrade_when_not_in_config:
    tracer_id: "blue_cease_suppress_blue_upgrade_when_not_in_config"
    spec_source: "forward"
    layer: "xapi"
    layer_status: "confirmed"
    test_ids:
      - "PropositionsManagementServiceTest#shouldReturnPremierOnlyWhenBlueRemovedFromConfig"
    coverage_status: "covered"
    retirement_candidates:
      - layer: "device"
        test_ids:
          - "EANDBLUE-8254"
          - "EANDBLUE-8277"
          - "EANDBLUE-8300"
        retirement_status: "candidate"
        retirement_evidence: "Covered by PropositionsManagementServiceTest at xapi layer (Spock unit test)"
    tracer_flags: []

  essential_customer_sees_premier_only:
    tracer_id: "blue_cease_essential_customer_sees_premier_only"
    spec_source: "forward"
    layer: "xapi"
    layer_status: "confirmed"
    test_ids:
      - "getproductshubdata_sdh_cached.feature:Blue Cease TC12:Essential customer PREMIER upgrade only"
    coverage_status: "covered"
    retirement_candidates:
      - layer: "device"
        test_ids:
          - "EANDBLUE-8335"
          - "EANDBLUE-8358"
          - "EANDBLUE-8381"
        retirement_status: "candidate"
        retirement_evidence: "Covered by Karate RIT615 row at xapi layer"
    tracer_flags: []

  blue_customer_continues_to_see_blue_until_config_changes:
    tracer_id: "blue_cease_blue_customer_continues_to_see_blue"
    spec_source: "forward"
    layer: "xapi"
    layer_status: "confirmed"
    test_ids: []
    coverage_status: "uncovered"
    retirement_candidates: []
    tracer_flags:
      - "No test found at xapi layer for active Blue customer scenario"
    notes: "Needs new Karate row or Spock test"
```

---

## Agent Self-Check

Before writing or updating `.tracer.yaml`, verify:
- [ ] Every behavior from `.spec` has a corresponding entry
- [ ] `layer` values all reference valid IDs from `layer-registry.yaml`
- [ ] All `test_ids` are concrete references, not descriptions
- [ ] `retirement_candidates` only set where owning layer has `coverage_status: covered`
- [ ] `retirement_status: retired` entries all have non-empty `retirement_evidence`
- [ ] `summary` counts match actual behavior entries
- [ ] `iteration` incremented from previous value
