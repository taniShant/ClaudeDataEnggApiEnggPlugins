---
description: "TRACER retirement analysis — maps an existing test suite into the traceability matrix, identifies retirement candidates with evidence, produces a retirement report."
argument-hint: --matrix <tracer_yaml_path> [--target-layer <layer_id>] [--layers <registry_path>]
---

# TRACER: trace-retire

Thin command. Parses arguments → validates inputs → delegates to retirement agent. Zero domain logic inline.

---

## STRUCTURED LOGGING

```
[TRACER:trace-retire] [{ISO-timestamp}] [{level}] {message}
```

---

## STATEFUL RESUMPTION

On startup (BEFORE any work):
1. Run `TaskList` — check for existing TRACER trace-retire tasks
2. If tasks exist → RESUME (skip completed phases)
3. If no tasks → FRESH RUN

---

## Section 1: Parse Arguments

| Flag | Required | Description |
|------|----------|-------------|
| `--matrix PATH` | required | Path to existing `.tracer.yaml` |
| `--target-layer LAYER` | optional | Only analyse candidates at this layer ID (e.g. `device_xray`) |
| `--layers PATH` | optional | Path to `layer-registry.yaml` — inferred from matrix path if not given |

**Example output** (retirement analysis summary):

```
TRACER RETIREMENT ANALYSIS — order_service
==========================
Matrix:              order_service.tracer.yaml
Target layer:        all layers

Retirement candidates: 3
  ✅ Retire-ready:     2   (covered at lower layer — evidence confirmed)
  ⚠️  Needs coverage:   1   (no lower-layer test found — write tests first)

Keep decisions:       7   (device/hardware/regulatory — must stay)

Candidates:
  EANDBLUE-5155  barclaycard_solus_customer_routed_to_alternative_content
    → Covered at unit_spock (pos 4) + component_jest (pos 2) — RETIRE READY
  EANDBLUE-5123  premier_customer_sees_tier_upgrade_proposition
    → Covered at unit_spock (pos 4) + integration_karate (pos 3) — RETIRE READY
  EANDBLUE-5569  life_events_section_renders_on_android_device
    → No component-layer test found. Action: write Jest test, then re-run

Note: TRACER recommends — team actions retirements. No tests were deleted.
```

---

## Section 2: Validate Inputs

1. `--matrix` must be present and path must exist — fail if missing
2. If `--target-layer` provided: verify layer ID exists in registry — fail if not found
3. If no `.tracer.yaml` exists: user must run `trace-forward` or `trace-reverse` first — report and STOP
4. On validation failure: report error, STOP

---

## Section 3: Delegate to Orchestrator

Spawn `tracer-orchestrator-agent` with:
```
FLOW: retire
MATRIX_PATH: {matrix path}
LAYER_REGISTRY_PATH: {registry path}
TARGET_LAYER: {layer id or null}
MODULE: {inferred from matrix filename}
```

The orchestrator runs Phase 7 (retirement analysis) and Phase 6 (write artefacts) only — earlier phases are skipped as the matrix already exists.

---

## Section 4: Zero-Touch Rules

1. NEVER set `retirement_status: retired` — only `candidate` or `keep`
2. NEVER ask the user mid-pipeline
3. Present candidates — humans action retirements
4. Run end-to-end without stopping
