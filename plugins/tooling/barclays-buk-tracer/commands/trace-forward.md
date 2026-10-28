---
description: "TRACER forward spec flow — generate a .spec from requirements/stories/ACs, attribute to layers, build traceability matrix. Entry point for greenfield or requirements-first work."
argument-hint: --docs [INPUT1] [INPUT2 ...] --module <module_name> [--layers <registry_path>]
---

# TRACER: trace-forward

Thin command. Parses arguments → validates inputs → delegates to orchestrator. Zero domain logic inline.

---

## STRUCTURED LOGGING

```
[TRACER:trace-forward] [{ISO-timestamp}] [{level}] {message}
```

---

## STATEFUL RESUMPTION

On startup (BEFORE any work):
1. Run `TaskList` — check for existing TRACER trace-forward tasks
2. If tasks exist → RESUME (skip completed phases)
3. If no tasks → FRESH RUN (create tasks for all phases)

---

## Section 1: Parse Arguments

| Flag | Required | Description |
|------|----------|-------------|
| `--docs INPUTS` | optional | One or more input files or inline requirements/stories/ACs text |
| `--module NAME` | required | Module name in snake_case (e.g. `order_checkout`) |
| `--layers PATH` | optional | Path to `layer-registry.yaml` — created automatically if missing |

**Example output** (Phase 8 summary returned after pipeline completes):

```
TRACER SUMMARY — order_checkout
==========================
Flow:                forward
Output directory:    /local/project/tracer-output
Spec file:           /local/project/tracer-output/order_checkout.spec
Matrix file:         /local/project/tracer-output/order_checkout.tracer.yaml
Layer registry:      /local/project/tracer-output/layer-registry.yaml

Behaviors total:     8
  Covered:           5
  Partial:           1
  Uncovered:         2
  Retirement cands:  0
  Unknown layer:     0

Flags: 2 unresolved
  - B006: layer_hint unknown — no matching test pattern for 'payment_gateway_timeout'
  - B007: layer_hint unknown — no matching test pattern for 'fraud_check_integration'

Next actions:
  - Write unit tests for B006 and B007 to complete coverage
  - Re-run /tracer:trace-reverse after tests are added to update the matrix
```

---

## Section 2: Validate Inputs

1. `--module` must be present and snake_case — fail if missing
2. If `--docs` provided: verify at least one input resolves (file exists or inline text non-empty)
3. If `--docs` absent: zero-input mode — orchestrator will prompt for requirements inline
4. On validation failure: report error, STOP

---

## Section 3: Delegate to Orchestrator

Spawn `tracer-orchestrator-agent` with:
```
FLOW: forward
SOURCE: {resolved inputs}
MODULE: {module name}
LAYER_REGISTRY: {path or "create"}
```

---

## Section 4: Zero-Touch Rules

1. NEVER ask the user questions mid-pipeline
2. NEVER pause for approval
3. Run end-to-end without stopping
4. If layer registry missing: orchestrator creates it — do not block
