---
name: reverse-spec
description: "TRACER adapter for barclays-buk-reverse-spec-generator — when and how to invoke it, how to consume .spec output, and how to feed layer attribution into the traceability matrix"
user-invocable: false
---

# Skill: Reverse Spec (TRACER Adapter)

> **Source:** TRACER Plugin v1.0.0 — BUK CIO Marketplace
> **Owner:** Barclays BUK Digital Channels
> **Review trigger:** On barclays-buk-reverse-spec-generator interface change or adapter contract update
> **Status:** Reviewed

## Quick Start

```bash
# Reverse spec from source code path
/tracer:trace-reverse --src src/services/OrderService.java --module order_service

# Reverse spec from entire backend (multi-file)
/tracer:trace-reverse --src src/main/java/com/bank/orders/ --module orders_domain

# Verify the .spec was generated:
cat order_service.spec | python3 -c "
import sys, yaml
d = yaml.safe_load(sys.stdin)
print(f'{len(d[\"behaviors\"])} behaviors extracted')
for b in d['behaviors']:
    print(f'  {b[\"id\"]} {b[\"name\"]} → layer: {b.get(\"layer_owner\",\"unknown\")}')"
```

**What the adapter does:** reads the `.spec` produced by `barclays-buk-reverse-spec-generator`, applies TRACER's layer attribution rules (matching behavior names to layer test patterns), and outputs a TRACER-compatible spec ready for matrix build.

---

## Overview

TRACER does not implement reverse spec generation — it delegates to `barclays-buk-reverse-spec-generator`. This skill defines the adapter contract: when to invoke the dependency, how to consume its `.spec` output, and how to translate the raw spec into TRACER's layer-attributed traceability matrix.

---

## Source Attribution

**Primary sources:**
- `barclays-buk-reverse-spec-generator` plugin — adapter contract derived from that plugin's interface
- TRACER Plugin v1.0.0 — adapter layer design

**Training knowledge applied:**
- Reverse engineering patterns: behavior extraction from method signatures, test names, and API annotations
- Name normalisation conventions (Java camelCase → snake_case, Gherkin scenario title → behavior name)

**Known limitations:**
- Quality of the reverse spec depends entirely on `barclays-buk-reverse-spec-generator` — TRACER only adds layer attribution
- Confidence threshold defaults to 0.5; lower-confidence extractions require manual review
- XML and non-REST protocols (gRPC, GraphQL) are not currently covered by the reverse spec generator

---

## When to Invoke the Reverse Spec Generator

Invoke when:
- Flow B (Reverse) is selected: code/tests exist, no formal specs
- Flow C (Legacy Change) is selected: establishing the baseline spec before processing the delta

Do NOT invoke when:
- Flow A (Forward) is selected — no code to reverse-spec from
- A `.spec` file already exists and is current — run `/converge` on the existing spec instead

---

## Invocation Contract

The reverse spec generator is invoked via its agent:

```
Agent: reverse-spec-generator-agent
Action: generate-spec
SOURCE_PATH: <path to source code>
OUTPUT_PATH: <where to write .spec>
LANGUAGE: <python | java | javascript | auto-detect>
```

TRACER passes `SOURCE_PATH` and receives back:
- `<module>.spec` — BDD YAML file with entities, behaviors, rules, constraints
- `<module>.convergence.yaml` — convergence loop state (owned by reverse spec generator, not TRACER)

---

## What the Raw Spec Lacks (TRACER's Job)

The reverse spec generator produces a behavioural spec with no concept of:
- Which **layer** owns each behavior
- Which **test framework** covers it
- Whether existing tests **trace to** each behavior
- Whether any behaviors are **covered at a lower layer** (retirement candidates)

TRACER adds this attribution layer on top.

---

## Consuming the `.spec` Output

After the reverse spec generator writes `<module>.spec`, TRACER:

### Step 1 — Read the spec

Parse all `behaviors`, `rules`, and `constraints` from the `.spec` file.

### Step 2 — Attribute each behavior to a layer

For each behavior:
1. Load `layer_registry` skill — get the project's defined layers
2. Apply layer attribution rules (see `layer_registry` skill)
3. Assign exactly one owning layer
4. If ambiguous — flag as `layer: unknown`, do not guess

### Step 3 — Map existing tests

For each behavior:
1. Scan known test locations for the attributed layer (from `layer_registry`)
2. Match tests to behaviors using name normalisation (snake_case alignment)
3. Record matched test IDs in the matrix

### Step 4 — Write `.tracer.yaml`

Populate the traceability matrix with:
- Spec source: `reverse`
- Per-behavior: layer, test IDs found, coverage status
- See `traceability_matrix` skill for schema

---

## Worked Example

**Source:** Java Spring Boot service `ProductHubService.java`

**Invocation:**
```
Agent: reverse-spec-generator-agent
Action: generate-spec
SOURCE_PATH: src/main/java/com/example/ProductHubService.java
OUTPUT_PATH: specs/
LANGUAGE: java
```

**Raw spec output (extract):**
```yaml
behaviors:
  - name: get_product_hub_data
    description: Returns product hub data for an authenticated customer
    given:
      - Customer is authenticated
      - Customer ID is present in request
    when:
      - GET /producthub/data is called
    then:
      - Returns propositions, categories, and upgrade tiers
```

**TRACER layer attribution:**
```yaml
# In .tracer.yaml
behaviors:
  get_product_hub_data:
    spec_source: reverse
    layer: xapi                    # owns service-layer business logic
    test_ids:
      - ProductHubServiceTest#shouldReturnProductHubData
      - getproductshubdata.feature:Scenario:Happy path
    coverage_status: covered
```

---

## Confidence Threshold

The reverse spec generator applies a confidence threshold (default 0.5) when extracting behaviors. TRACER inherits whatever the generator produces. If behaviors appear missing:
- Re-run with `confidence_threshold=0.3` to surface lower-confidence extractions
- Review flagged items manually before layer attribution

---

## Agent Self-Check

Before completing reverse spec ingestion, verify:
- [ ] `reverse-spec-generator-agent` invoked with correct `SOURCE_PATH`
- [ ] `.spec` file exists on disk at `OUTPUT_PATH`
- [ ] Every behavior in `.spec` has been attributed to exactly one layer
- [ ] No behaviors left with `layer: unknown` without a flag raised to user
- [ ] `.tracer.yaml` written with `spec_source: reverse` for all entries
- [ ] `layer_registry` skill was loaded before attribution
