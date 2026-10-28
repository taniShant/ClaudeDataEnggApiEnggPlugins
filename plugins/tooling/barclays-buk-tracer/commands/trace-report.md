---
description: "TRACER standalone report — generate an Xray retirement report from an existing traceability matrix. Use when the matrix already exists and you only need the report regenerated or posted to Jira."
argument-hint: --matrix <tracer_yaml_path> --xray <plan-id|path|csv> [--format markdown|jira|both] [--output-dir <path>]
---

# TRACER: trace-report

Thin command. Parses arguments → validates inputs → delegates to report agent. Zero domain logic inline. Use this command when `.tracer.yaml` already exists and you want the report without re-running the full scan pipeline.

---

## STRUCTURED LOGGING

```
[TRACER:trace-report] [{ISO-timestamp}] [{level}] {message}
```

---

## STATEFUL RESUMPTION

On startup (BEFORE any work):
1. Run `TaskList` — check for existing TRACER trace-report tasks
2. If tasks exist → RESUME
3. If no tasks → FRESH RUN

---

## Section 1: Parse Arguments

| Flag | Required | Description |
|------|----------|-------------|
| `--matrix PATH` | required | Path to existing `.tracer.yaml` |
| `--xray SOURCE` | required | Jira test plan key (e.g. `EANDBLUE-1234`), feature file path, directory, CSV, or XLS |
| `--xray-type TYPE` | optional | `test_plan` (default) \| `execution` |
| `--format FORMAT` | optional | `markdown` (default) \| `jira` \| `both` |
| `--output-dir PATH` | optional | Directory for report files (default: same directory as matrix) |

**Example output** (report files written):

```
TRACER REPORT — products_hub
==========================
Matrix:              /local/mobile-team/tracer-output/products_hub.tracer.yaml
Xray source:         EANDBLUE-1234 (296 tests imported)
Format:              both
Output directory:    /local/mobile-team/tracer-output

Report written:      /local/mobile-team/tracer-output/products_hub-xray-retirement-report.md
CSV written:         /local/mobile-team/tracer-output/products_hub-xray-retirement-report.csv

Summary:
  ✅ Retire-ready:   ~107 tests (36%)  — evidence confirmed, safe to retire now
  ⚠️  Needs coverage: ~143 tests (48%)  — write lower-layer tests to unlock
  🔒 Keep:            ~46 tests (16%)  — device/hardware/regulatory only

Device suite reduction: 84% eligible to retire or shift-left (250/296 tests)
Keep group reduction:   88% → 16%  (-216 tests off the device layer)

Jira comment posted: EANDBLUE-1234 ✓
```

---

## Section 2: Validate Inputs

1. `--matrix` must be present and path must exist — fail if missing or not found
2. `--xray` must be present — fail if missing
3. If `--format` includes `jira`: verify `JIRA_PAT` and `JIRA_BASE_URL` set in env — warn if missing
4. On failure: report error and STOP

---

## Section 3: Pipeline

This command skips the scan pipeline entirely and runs only two agents:

**Step 1: Import Xray tests**
Spawn `tracer-xray-importer-agent` with:
```
XRAY_SOURCE: {xray input}
XRAY_TYPE:   {type}
MODULE:      {inferred from matrix filename}
```

**Step 2: Generate report**
Spawn `tracer-report-agent` with:
```
MATRIX_PATH:     {matrix path}
XRAY_TESTS:      {list from step 1}
XRAY_SOURCE_REF: {original xray source}
MODULE:          {inferred from matrix filename}
FORMAT:          {format}
OUTPUT_DIR:      {output dir}
```

---

## Section 4: Zero-Touch Rules

1. NEVER ask the user questions mid-pipeline
2. NEVER re-run the full scan — report only
3. If Jira API unavailable: write Markdown report and flag Jira step as skipped
