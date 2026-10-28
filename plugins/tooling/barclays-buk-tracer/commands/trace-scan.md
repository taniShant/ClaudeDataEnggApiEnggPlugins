---
description: "TRACER Xray reduction scan — import Xray tests, scan repos across any stack, build cross-layer coverage matrix, and generate an evidence-backed retirement report."
argument-hint: --repos <path-or-url>[,…] --xray <plan-id|path|csv> --module <name> [--xray-type test_plan|execution] [--stack <lang>] [--layers <path>] [--report markdown|jira|both]
---

# TRACER: trace-scan

Thin command. Parses arguments → validates inputs → delegates to orchestrator with `FLOW: scan`. Zero domain logic inline.

---

## STRUCTURED LOGGING

```
[TRACER:trace-scan] [{ISO-timestamp}] [{level}] {message}
```

---

## STATEFUL RESUMPTION

On startup (BEFORE any work):
1. Run `TaskList` — check for existing TRACER trace-scan tasks
2. If tasks exist → RESUME (skip completed phases)
3. If no tasks → FRESH RUN (create tasks for all phases)

---

## Section 1: Parse Arguments

| Flag | Required | Description |
|------|----------|-------------|
| `--repos REPOS` | required | Comma-separated local paths or remote git URLs |
| `--xray SOURCE` | required | Jira test plan key, `.feature` path/dir, CSV, or XLS |
| `--module NAME` | required | Module name in snake_case |
| `--xray-type TYPE` | optional | `test_plan` (default) \| `execution` |
| `--stack LANG` | optional | `java` \| `kotlin` \| `swift` \| `typescript` \| `javascript` \| `python` \| `auto` (default) |
| `--layers PATH` | optional | Path to `layer-registry.yaml` — created automatically if missing |
| `--report FORMAT` | optional | `markdown` (default) \| `jira` \| `both` |
| `--output-dir PATH` | optional | Output directory for reports (default: current directory) |

**Example output** (full pipeline, Phase 8 summary — products_hub pilot with feature files):

```
TRACER SUMMARY — products_hub (scan)
==========================
Flow:                scan
Output directory:    /local/mobile-team/tracer-output
Spec file:           /local/mobile-team/tracer-output/products_hub.spec
Matrix file:         /local/mobile-team/tracer-output/products_hub.tracer.yaml
Layer registry:      /local/mobile-team/tracer-output/layer-registry.yaml
Report (markdown):   /local/mobile-team/tracer-output/products_hub-xray-retirement-report.md
Report (CSV):        /local/mobile-team/tracer-output/products_hub-xray-retirement-report.csv
Xray tests:          296 imported (Per_ProductHub2.0_main_adb.feature)
Repos scanned:       2 (x-digi-products-hub-mgt, productHub)

Retirement summary (296 total):
  ✅ Retire-ready:   ~107 tests (36%)  — navigation, routing, error screen, proposition CTA
  ⚠️  Needs coverage: ~143 tests (48%)  — per-category back nav, life event deep links
  🔒 Keep:            ~46 tests (16%)  — device login, hardware back, scroll layout, a11y

Device suite reduction: 84% eligible to retire or shift-left (250/296 tests)
Keep group reduction:   88% → 16%  (-216 tests permanently off the device layer)

Flags: 1 unresolved
  - B008/B009: no Jest component test found for life events section rendering

Next actions:
  - Review products_hub-xray-retirement-report.md
  - Raise PR to retire ~107 device tests from EANDBLUE test plan
  - Write 1 Jest component test (life events) → re-run trace-scan to unlock ~143 needs-coverage tests
```

> **Tip:** Always provide a feature file (`*.feature`) rather than just the Jira XLS as your `--xray` input. The feature file contains actual scenario text — without it, trace-scan cannot distinguish navigation tests from genuinely device-specific tests and over-counts the Keep group. In the products_hub pilot, XLS-only classified 88% as Keep; with feature files that dropped to 16%.

---

## Section 2: Validate Inputs

1. `--repos` must be present with at least one entry — fail if missing
2. `--xray` must be present — fail if missing
3. `--module` must be present and snake_case — fail if missing
4. If `--report` includes `jira`: verify `JIRA_PAT` and `JIRA_BASE_URL` are set in env — warn if missing
5. If any `--repos` entry is a remote URL: verify `STASH_PAT` or `GITLAB_PAT` is set — warn if missing
6. On hard validation failure: report error and STOP

---

## Section 3: Delegate to Orchestrator

Spawn `tracer-orchestrator-agent` with:
```
FLOW:             scan
REPOS:            {comma-separated list}
XRAY_SOURCE:      {xray input}
XRAY_TYPE:        {test_plan | execution | local | csv}
MODULE:           {module name}
STACK_HINT:       {lang or auto}
LAYER_REGISTRY:   {path or "create"}
REPORT_FORMAT:    {markdown | jira | both}
OUTPUT_DIR:       {output directory}
```

The orchestrator runs the full scan pipeline:
- Phase 1: Xray import (tracer-xray-importer-agent)
- Phase 2: Repo scan (tracer-repo-scanner-agent)
- Phase 3: Spec generation (tracer-spec-agent, reverse per repo)
- Phase 4: Matrix build (tracer-traceability-agent)
- Phase 5: Validation (tracer-validator-agent)
- Phase 6: Write artefacts (tracer-file-writer-agent)
- Phase 7: Report generation (tracer-report-agent)

---

## Section 4: Zero-Touch Rules

1. NEVER ask the user questions mid-pipeline
2. NEVER pause for approval between phases
3. Run end-to-end without stopping
4. If layer registry missing: orchestrator creates it — do not block
5. If remote clone fails for one repo: log as red_flag, continue with remaining repos
