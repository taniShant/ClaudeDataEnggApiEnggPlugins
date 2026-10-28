---
description: "TRACER legacy change flow — reverse-spec existing code as baseline, apply delta (new change request), forward-spec the target, produce gap analysis and updated matrix."
argument-hint: --src <source_path> --delta <delta_path_or_text> --module <module_name> [--lang <language>] [--layers <registry_path>]
---

# TRACER: trace-legacy

Thin command. Parses arguments → validates inputs → delegates to orchestrator. Zero domain logic inline.

---

## STRUCTURED LOGGING

```
[TRACER:trace-legacy] [{ISO-timestamp}] [{level}] {message}
```

---

## STATEFUL RESUMPTION

On startup (BEFORE any work):
1. Run `TaskList` — check for existing TRACER trace-legacy tasks
2. If tasks exist → RESUME (skip completed phases)
3. If no tasks → FRESH RUN (create tasks for all phases)

---

## Section 1: Parse Arguments

| Flag | Required | Description |
|------|----------|-------------|
| `--src PATH` | required | Path to existing legacy source code file or directory |
| `--delta INPUT` | required | Path to change request / story / delta description file or inline text |
| `--module NAME` | required | Module name in snake_case (e.g. `order_service`) |
| `--lang LANGUAGE` | optional | `java` \| `python` \| `javascript` \| `auto-detect` (default) |
| `--layers PATH` | optional | Path to `layer-registry.yaml` — created automatically if missing |

**Example output** (Phase 8 summary — gap analysis included):

```
TRACER SUMMARY — payments_service (legacy change)
==========================
Flow:                legacy_change
Output directory:    /local/project/tracer-output
Baseline spec:       /local/project/tracer-output/payments_service.spec (12 behaviors)
Target spec:         /local/project/tracer-output/payments_service.spec (15 behaviors, post-delta)
Matrix file:         /local/project/tracer-output/payments_service.tracer.yaml
Layer registry:      /local/project/tracer-output/layer-registry.yaml

Gap analysis (new behaviors from delta):
  + B013: open_banking_payment_initiated_via_new_consent_flow
  + B014: duplicate_payment_detected_within_24h_window
  + B015: payment_cancelled_after_authorisation

Behaviors total:     15
  Covered:           10
  Partial:           2
  Uncovered:         3   ← gap behaviors need new tests

Flags: 3 unresolved (new behaviors with no lower-layer tests yet)

Next actions:
  - Write tests for B013, B014, B015 at the appropriate layers
  - Re-run /tracer:trace-reverse after tests are added to update the matrix
```

---

## Section 2: Validate Inputs

1. `--src` must be present and path must exist — fail if missing
2. `--delta` must be present (file or inline text) — fail if missing
3. `--module` must be present and snake_case — fail if missing
4. On validation failure: report error, STOP

This command is ONLY valid when both legacy source AND a delta exist. If no delta: use `trace-reverse` instead.

---

## Section 3: Delegate to Orchestrator

Spawn `tracer-orchestrator-agent` with:
```
FLOW: legacy_change
SOURCE: {src path}
DELTA: {delta input}
MODULE: {module name}
LANGUAGE: {language}
LAYER_REGISTRY: {path or "create"}
```

The orchestrator will:
1. Generate baseline spec (reverse) from `--src`
2. Generate target spec (forward) from `--delta`
3. Produce gap analysis (baseline vs target)
4. Build matrix for target spec only (delta behaviors)

---

## Section 4: Zero-Touch Rules

1. NEVER ask the user questions mid-pipeline
2. NEVER pause for approval
3. Run end-to-end without stopping
4. If baseline `.spec` already exists: orchestrator skips reverse gen — do not block
