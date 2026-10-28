# TRACER

**Test Requirements And Coverage Evidence Registry**

TRACER builds and maintains a bidirectional traceability matrix between specs, test scenarios, test layers, and concrete test IDs. It turns test coverage from an assumption into evidence.

---

## What Problem Does TRACER Solve?

Tests accumulate at expensive layers (UI, device, E2E) covering logic that belongs at cheaper layers (unit, integration). This is invisible until someone maps coverage across layers. TRACER makes that map explicit and keeps it current.

It also solves the forward problem: when writing new tests, which layer should own each scenario? TRACER answers that from requirements, before any code is written.

---

## Three Flows

| Flow | When | Command |
|------|------|---------|
| **Forward** | Requirements exist, no code yet | `/tracer:trace-forward` |
| **Reverse** | Code/tests exist, no specs | `/tracer:trace-reverse` |
| **Legacy Change** | Legacy code + new change request | `/tracer:trace-legacy` |

For existing test suites: `/tracer:trace-retire`  
For Xray reduction (scan + report): `/tracer:trace-scan`  
For current state: `/tracer:trace-status`

---

## Quick Start

### New feature (requirements-first)
```
/tracer:trace-forward --docs story.md --module order_checkout
```

### Existing codebase (no specs)
```
/tracer:trace-reverse --src src/services/OrderService.java --module order_service
```

### Legacy change
```
/tracer:trace-legacy --src src/ --delta change-request.md --module order_service
```

### Analyse existing test suite for retirement candidates
```
/tracer:trace-retire --matrix order_service.tracer.yaml
```

### Xray reduction — scan repos and generate retirement report
```
/tracer:trace-scan --repos /local/java-backend,/local/mobile-app --xray EANDBLUE-1234 --module products_hub --report both
```

### Regenerate report from an existing matrix
```
/tracer:trace-report --matrix products_hub.tracer.yaml --xray EANDBLUE-1234 --format markdown
```

---

## Output Artefacts

| File | Purpose |
|------|---------|
| `<module>.spec` | BDD behavioural spec (YAML) |
| `<module>.tracer.yaml` | Traceability matrix |
| `layer-registry.yaml` | Project layer definitions (created once) |
| `<module>-xray-retirement-report.md` | Xray retirement report (retire-ready / needs-coverage / keep) |
| `<module>-xray-retirement-report.csv` | Same decisions as CSV for spreadsheet review |

After every run TRACER prints the absolute path for each file written:

```
TRACER — files written
  📄 Markdown report:  /your/output/dir/<module>-xray-retirement-report.md
  📊 CSV report:       /your/output/dir/<module>-xray-retirement-report.csv
```

The Phase 8 summary also includes `Output directory:` so you always know exactly where artefacts landed, regardless of which directory the command was run from.

---

## Layer Registry

TRACER does not assume any layers. You define your own in `layer-registry.yaml`:

```yaml
version: "1.0"
project: "my-project"
layers:
  - id: "e2e"
    name: "End-to-End Tests"
    frameworks:
      - name: "cypress"
        language: "javascript"
        test_path_pattern: "cypress/e2e/**/*.cy.ts"
    owns: ["Full user journey"]
    hierarchy_position: 1
  - id: "unit"
    name: "Unit Tests"
    frameworks:
      - name: "jest"
        language: "javascript"
        test_path_pattern: "src/**/*.test.ts"
    owns: ["Business logic", "Edge cases"]
    hierarchy_position: 2
```

If no registry exists, TRACER creates one for you on first run.

---

## Key Principles

- **Retirement ≠ deletion** — retired tests have a permanent evidence record
- **Retirement requires proof** — lower-layer coverage must be in the matrix
- **TRACER recommends, humans decide** — it never executes retirements
- **Any layer, any framework** — no hardcoded assumptions about your stack

---

## Dependencies

- `barclays-buk-reverse-spec-generator` — spec extraction from source code
- `barclays-buk-standards` — shared standards

---

## Quality Gates

**Plugin Test Score:**
- Current: 100/100 (DIGICAW-6219 audit, 2026-10-21)
- Required: ≥90/100
- Last run: `cd plugins/tooling/barclays-buk-tracer && /test-plugin .`
- Result: PASS ✓

**To reproduce:**
```
cd plugins/tooling/barclays-buk-tracer && /test-plugin .
```

---

## Pilot Evidence

### Run 1 — products_hub (2026-10-21)

**Module:** `products_hub` | **Repos:** x-digi-products-hub-mgt (Java/Groovy), productHub (React Native/TypeScript) | **Xray source:** 296 tests from Jira XLS export

#### Pass 1 — XLS-only (names, no test content)

| Decision | Count | % of suite |
|----------|-------|-----------|
| ✅ Retire-ready | 22 | 7% |
| ⚠️ Needs new coverage | 12 | 4% |
| 🔒 Keep | 262 | 88% |

Initial classification used only Xray IDs and summary names from the XLS. `Per_*` prefix was assumed to mean device-only.

#### Pass 2 — Feature file read (`Per_ProductHub2.0_main_adb.feature`)

After reading the actual Gherkin scenarios from the device automation repo, the Android main series alone (81 mapped tests) broke down as:

| Decision | Count | What they actually are |
|----------|-------|------------------------|
| ✅ Retire-ready | 28 | Coming-soon routing, error screen, proposition visibility, navigation-back via CTA/footer, life events list render |
| ⚠️ Needs new coverage | 45 | Per-category back navigation, individual life event CTA deep links |
| 🔒 Keep | 5 | Device login flow, Android hardware back button, scroll layout |

**Only ~6% of the Android main series are genuinely device-specific** (vs the initial 100% assumption).

#### Revised projected totals (extrapolated to full suite)

| Decision | XLS-only | With feature files | Change |
|----------|----------|--------------------|--------|
| ✅ Retire-ready | 22 (7%) | **~107 (36%)** | +85 |
| ⚠️ Needs new coverage | 12 (4%) | **~143 (48%)** | +131 |
| 🔒 Keep | 262 (88%) | **~46 (16%)** | −216 |

> Confirmed by: iOS and Per_UI feature files pending — fetch with `--insecure` from `app.gitlab.barcapint.com` to harden these projections into exact numbers.

#### Discovery: 4th layer (gateway_e2e_nonui)

`tba-release-nonui-features` repo contains BMB NonUI gateway E2E tests (`@JiraXrayTest_BMB-1257623/5/6`) that call `x-digi-products-hub-mgt` through the real gateway + auth stack and verify the full JSON response field-by-field. This is a layer between Karate integration and device — previously unregistered. The EANDBLUE NonUI tests are covered at **four layers simultaneously** once this layer is added to `layer-registry.yaml`.

**Key learnings from this pilot:**
- Always provide device feature files alongside the XLS — `Per_` does not mean performance-only; the series contains navigation, routing, error screen, and content visibility tests
- Reading 1 feature file (1,799 lines, 87 scenarios) reclassified 88% "keep" down to 16% — the content reading step is the most valuable action in trace-scan
- Jira `.xls` exports are HTML-disguised — parse with `html.parser`, not `xlrd`/`openpyxl`
- BCB SOLUS and Premier tier logic is covered at 3 layers (unit + integration + component) — strongest retire-ready evidence
- A single Jest component test unlocks an entire Xray series: 1 test = 12 LifeEvents tests retired
- NonUI gateway tests (`tba-release-nonui-features`) are an invisible layer — check for them before declaring a behavior uncovered

---

## Xray Reduction

TRACER v1.1.0 adds an end-to-end pipeline for reducing Xray (device-layer) test suites by finding lower-layer coverage evidence across any stack.

### How it works

```
/tracer:trace-scan
  → tracer-xray-importer-agent    (fetch tests from Jira/files/CSV)
  → tracer-repo-scanner-agent     (scan repos: Java/Kotlin/Swift/TS/JS/Python)
  → tracer-spec-agent             (reverse spec per repo)
  → tracer-traceability-agent     (cross-layer matrix)
  → tracer-validator-agent
  → tracer-file-writer-agent
  → tracer-report-agent           (retirement report: retire-ready / needs-coverage / keep)
```

### Xray input sources

TRACER accepts Xray tests in any of these forms — pass whichever you have:

| Input | Example | Notes |
|-------|---------|-------|
| Jira test plan ID | `--xray EANDBLUE-1234` | Fetches via Xray REST API |
| Jira test execution ID | `--xray EANDBLUE-5678 --xray-type execution` | Fetches via Xray REST API |
| Device UI feature file | `--xray ./Feature/ADB/Per_ProductHub2.0_main_adb.feature` | Extracts `@JiraXrayTest_` tags + scenario titles |
| Device UI feature directory | `--xray ./Feature/ADB/` | Scans all `*.feature` files in dir |
| NonUI gateway feature file | `--xray ./Feature/PSR/ProductHub/ProductHub.feature` | Same tag extraction — works for BMB-* IDs too |
| Jira XLS/HTML export | `--xray xray-export.xls` | Jira exports `.xls` as HTML — parsed automatically |
| CSV export | `--xray xray-export.csv` | Auto-detects `key`/`summary` columns |

> **Tip:** Always provide the device feature file (`*.feature`) alongside or instead of the XLS. The feature file contains the actual scenario text, which is required to distinguish navigation tests, routing tests, and error screen tests from genuinely device-specific rendering tests. XLS-only classification significantly over-counts the "Keep" group (see Pilot Evidence).

### Repo input

```
--repos /local/java-backend,https://stash.barcapint.com/scm/team/mobile.git
```

Supports local paths and remote git URLs. Remote repos are shallow-cloned using `STASH_PAT` or `GITLAB_PAT` and cleaned up after scanning.

### Report output

Three groups, per test:
- **Retire-ready** — covered at lower layer, evidence confirmed
- **Needs new coverage** — no lower-layer test found yet; prescription provided (see below)
- **Keep** — hardware/journey/regulatory; intentionally retained

Report written as Markdown and CSV. Optional Jira comment posted to the test plan ticket.

#### Needs-coverage prescriptions

For every behavior in the "Needs new coverage" group, TRACER generates an explicit prescription — not just a flag. Tests are grouped by behavior so the retirement multiplier is visible:

```
### Group: `life_events_section_renders_on_android_device` — 12 Xray tests

> ⚡ Writing 1 test at `component_jest` unlocks 12 Xray tests for retirement.

- Gap:     No component_jest (jest) test found
- Write in: productHub/src/screens/landing-screen/landing-screen-container.native.spec.tsx
- Suggested test:
    it('should render life events section for retail customer', () => {
      /* mock API returning life events data */
      /* assert life events section visible, first card title/CTA present */
    });
- Xray tests unlocked (12): EANDBLUE-5569, EANDBLUE-5570, EANDBLUE-5571 ...
- Then re-run: /tracer:trace-scan (same flags) to move 12 test(s) to retire-ready
```

The CSV `action` column carries the same prescription — paste directly into a sprint ticket.

---

## Version

`1.1.0` — Xray reduction pipeline (scan + report)  
`1.0.0` — Initial release
