---
description: "TRACER status dashboard — shows current traceability matrix state: coverage summary, uncovered behaviors, retirement candidates, and recommended next actions."
argument-hint: [--matrix <tracer_yaml_path>] [--open-only]
---

# TRACER: trace-status

Lightweight read-only command. Reads `.tracer.yaml` and renders a dashboard. No agents spawned unless matrix is missing.

---

## STRUCTURED LOGGING

```
[TRACER:trace-status] [{ISO-timestamp}] [{level}] {message}
```

---

## Section 1: Parse Arguments

```
FORMAT: [--matrix <path>] [--open-only]

FLAGS:
  --matrix PATH    Path to .tracer.yaml (optional — auto-discovers if not given)
  --open-only      Show only uncovered behaviors and unresolved flags
```

---

## Section 2: Locate Matrix

1. If `--matrix` provided: use that path
2. If not provided: glob for `*.tracer.yaml` in current directory and subdirectories
3. If multiple found: list them, ask user to specify
4. If none found: report "No traceability matrix found. Run trace-forward, trace-reverse, or trace-legacy first."

---

## Section 3: Render Dashboard

```
TRACER STATUS — <module>
=========================
Spec file:          <path>          [forward | reverse | legacy_change]
Matrix file:        <path>
Last updated:       <timestamp>     Iteration: <n>
Layer registry:     <path>          (<n> layers)

COVERAGE SUMMARY
----------------
Total behaviors:        {n}
  ✓ Covered:            {n}
  ~ Partial:            {n}
  ✗ Uncovered:          {n}
  ★ Retirement cands:   {n}
  ? Unknown layer:      {n}

UNCOVERED BEHAVIORS
-------------------
{behavior_name}  [layer: {layer_id}]
  Flags: {tracer_flags if any}
...
(empty if all covered)

RETIREMENT CANDIDATES
---------------------
{behavior_name}
  High-layer tests:  {test_ids}  [{layer_id}]
  Covered by:        {test_ids}  [{lower_layer_id}]
...
(empty if no candidates)

UNRESOLVED FLAGS
----------------
{behavior_name}: {flag text}
...
(empty if no flags)

NEXT ACTIONS
------------
{Recommended actions based on matrix state}
```

**Next action logic:**

| Condition | Recommended action |
|-----------|-------------------|
| `uncovered` behaviors exist | Run test scan or write new tests, then `trace-reverse` to update matrix |
| `retirement_candidates` exist | Run `/tracer:trace-retire` for evidence report |
| `unknown_layer` > 0 | Review and update `layer-registry.yaml`, re-run matrix |
| `tracer_flags` unresolved | Review flagged behaviors, resolve ambiguities |
| All covered, no candidates, no flags | Matrix complete — no action needed |

---

## Section 4: Zero-Touch Rules

1. Read-only — never modify `.tracer.yaml` or `.spec`
2. If matrix missing: report and stop (do not auto-run other commands)
3. `--open-only`: suppress covered behaviors and empty sections from output
