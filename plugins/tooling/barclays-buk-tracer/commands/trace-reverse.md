---
description: "TRACER reverse spec flow — extract .spec from existing code, attribute to layers, build traceability matrix. Entry point for code-first or legacy audit work."
argument-hint: --src <source_path> --module <module_name> [--lang <language>] [--layers <registry_path>]
---

# TRACER: trace-reverse

Thin command. Parses arguments → validates inputs → delegates to orchestrator. Zero domain logic inline.

---

## STRUCTURED LOGGING

```
[TRACER:trace-reverse] [{ISO-timestamp}] [{level}] {message}
```

---

## STATEFUL RESUMPTION

On startup (BEFORE any work):
1. Run `TaskList` — check for existing TRACER trace-reverse tasks
2. If tasks exist → RESUME (skip completed phases)
3. If no tasks → FRESH RUN (create tasks for all phases)

---

## Section 1: Parse Arguments

| Flag | Required | Description |
|------|----------|-------------|
| `--src PATH` | required | Path to source code file or directory |
| `--module NAME` | required | Module name in snake_case (e.g. `order_service`) |
| `--lang LANGUAGE` | optional | `java` \| `python` \| `javascript` \| `auto-detect` (default) |
| `--layers PATH` | optional | Path to `layer-registry.yaml` — created automatically if missing |

**Example output** (Phase 8 summary):

```
TRACER SUMMARY — order_service
==========================
Flow:                reverse
Output directory:    /local/project/tracer-output
Spec file:           /local/project/tracer-output/order_service.spec
Matrix file:         /local/project/tracer-output/order_service.tracer.yaml
Layer registry:      /local/project/tracer-output/layer-registry.yaml

Behaviors total:     12
  Covered:           9
  Partial:           2
  Uncovered:         1
  Retirement cands:  3
  Unknown layer:     0

Flags: 1 unresolved
  - B011: no component test found for error-screen rendering

Next actions:
  - Write component test for B011 error-screen rendering
  - Run /tracer:trace-retire to generate retirement evidence for the 3 candidates
```

---

## Section 2: Validate Inputs

1. `--src` must be present and path must exist — fail if missing
2. `--module` must be present and snake_case — fail if missing
3. `--lang` defaults to `auto-detect` if not provided
4. On validation failure: report error, STOP

---

## Section 3: Delegate to Orchestrator

Spawn `tracer-orchestrator-agent` with:
```
FLOW: reverse
SOURCE: {src path}
MODULE: {module name}
LANGUAGE: {language}
LAYER_REGISTRY: {path or "create"}
```

---

## Section 4: Zero-Touch Rules

1. NEVER ask the user questions mid-pipeline
2. NEVER pause for approval
3. Run end-to-end without stopping
4. If `.spec` already exists: orchestrator runs converge instead of regenerate — do not block
