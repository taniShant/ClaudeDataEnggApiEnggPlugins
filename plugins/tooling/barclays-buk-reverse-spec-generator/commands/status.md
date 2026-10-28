---
name: status
description: Show the self-verification loop dashboard — convergence percentage, iteration count, open divergences, and the recommended next action.
agent: reverse-spec-generator-status-agent
allowed-tools: Read, Glob
---

# Status

Show where a spec is in its self-verification loop. Reads `.convergence.yaml` and renders a dashboard with convergence percentage, iteration count, open divergences, and the recommended next action.

## Options

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `spec_file` | path | no | all .spec files | Path to specific .spec file (omit for multi-spec dashboard) |
| `--format` | enum | no | `dashboard` | Output format: `dashboard` (ASCII), `json`, `table` |
| `--open-only` | flag | no | off | Show only diverged/missing behaviors (hide aligned) |

## Overview

After each loop iteration (`/converge`, `/run-tests`, `/amend`, `/implement`), run `/status` to:

- **See overall convergence** — what percentage of behaviors are aligned
- **Track iterations** — how many times the loop has run
- **Identify the bottleneck** — which items are blocking convergence
- **Get the next action** — what to do next to progress the loop
- **Know when you're done** — 100% convergence signals the loop is complete

## Usage

```
/status
# Spec file: a-digi-msg-data-mgt.spec
```

Or for all specs in the current directory:

```
/status
```

## Dashboard Output

```
╔══════════════════════════════════════════════════════════════╗
║  Convergence Status: a-digi-msg-data-mgt                    ║
╚══════════════════════════════════════════════════════════════╝

  Progress:    ████████████░░░░  77.3%  (iteration 4)
  Last run:    2026-07-12 14:30 UTC

  Summary:
    ✓ aligned        17   behaviors/rules/constraints
    ✗ diverged        2   need resolution
    ✗ missing_impl    1   spec-led, code not written
    ? missing_spec    2   code-led, spec not updated
    ~ unknown         0

  Tests:
    passing          14
    failing           2   → delete_event_log, get_steps
    not_run           1   → dismiss_message

══════════════════════════════════════════════════════════════

  OPEN ITEMS  (action required)

  [HIGH] delete_event_log
    status : diverged
    truth  : spec  → fix the code
    tests  : failing
    action : Run /implement to generate a stub, then implement

  [HIGH] get_steps
    status : missing_impl
    truth  : spec  → implement in code
    tests  : failing
    action : Run /implement to generate a stub

  [MEDIUM] missing_spec × 2
    create_served_log_failed  → code-led, run /amend
    validate_account_ids      → code-led, run /amend

══════════════════════════════════════════════════════════════

  RECOMMENDED NEXT ACTION:
  → /implement  (2 spec-led missing/diverged behaviors)

══════════════════════════════════════════════════════════════
```

## Convergence Complete

When all items are aligned:

```
╔══════════════════════════════════════════════════════════════╗
║  Convergence Status: a-digi-msg-data-mgt                    ║
╚══════════════════════════════════════════════════════════════╝

  Progress:    ████████████████  100.0%  (iteration 7)

  ✓ All 22 items aligned — spec and code are converged.

  The loop is complete. Recommended next steps:
  → Commit the .spec file as living documentation
  → Share with the team as the canonical behavioral reference
  → Schedule periodic /converge runs to catch future drift

╚══════════════════════════════════════════════════════════════╝
```

## Next Action Logic

The recommended next action is determined by the open items:

| Condition | Recommended action |
|---|---|
| `missing_impl` or `diverged` with `source_of_truth: spec` | `/implement` |
| `missing_spec` or `diverged` with `source_of_truth: code` | `/amend` |
| `diverged` with `source_of_truth: unknown` | Human review |
| Tests failing, `source_of_truth: spec` | Fix code → `/run-tests` |
| Tests failing, `source_of_truth: code` | `/amend` spec |
| All aligned, tests passing | Loop complete |

## Multi-Spec View

Running `/status` without specifying a spec file shows all specs in the directory:

```
  Spec                          Progress    Iteration   Open
  ─────────────────────────────────────────────────────────
  a-digi-msg-data-mgt.spec      77.3%       4           3
  user_service.spec             100.0%      6           0  ✓
  api_service.spec              45.0%       1           11
```

## State File

`/status` reads `.convergence.yaml` — the state file written by `/converge` and `/run-tests`. If no state file exists, it reports "not yet run" and suggests starting with `/converge`.

```
  a-digi-msg-data-mgt.spec — no convergence state found
  → Run /converge to begin the verification loop
```

## Loop Reference

```
gather context        take action           verify              repeat
──────────────────    ─────────────────     ─────────────────   ───────
/generate-spec        /generate-tests  →    /run-tests      →   until
→ the spec            /implement       →    /converge       →   converged
(durable context)     (spec-led items)      → .convergence.yaml
       ▲                                           │
       └────── /amend (when spec was wrong) ◀──────┘
                                                   │
                                              /status
                                         (loop dashboard)
```
