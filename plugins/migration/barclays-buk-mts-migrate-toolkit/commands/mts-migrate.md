---
description: Generate migration code from MTS mainframe service to a replacement API, with strategy selection (new microservice, existing microservice, or in-place dual-path)
argument-hint: <ServiceName.method> [--report path/to/api-match-report.md]
---

You are the main Claude Code agent. When the user runs `/mts-migrate`, you orchestrate a 3-strategy migration pipeline: load inputs, ask which strategy, dispatch to the strategy workflow, then run shared code generation steps.

**Pipeline position:** This is step 3 of a three-stage pipeline:
```
/mts-documentation  ->  /api-replacement-match  ->  /mts-migrate
```

**Strategies:**
- **A) New microservice** — Clone a GitLab template, scaffold, add endpoint
- **B) Existing microservice** — Developer provides local path, add endpoint there
- **C) In-place migration** — Dual-path routing with feature flag in this BUK repo

---

## Input Parsing

Parse the argument to extract:

1. **Method identifier** — one of:
   - Method name only: `findByPrimaryKey`
   - Qualified name: `CustomerGateway.findByPrimaryKey`
2. **Report path** (optional): `--report docs/mts/api-match-CustomerGateway-findByPrimaryKey.md`

If `--report` is not provided, auto-discover the match report:
```
Glob docs/mts/api-match-*<method>*.md
Glob docs/mts/test/api-match-*<method>*.md
```

If no match report is found:
```
Error: No API match report found for <method>. Run /api-replacement-match first:
  /api-replacement-match <ServiceName.method>
```

---

## Step 0 — Load Inputs

### 0a. Read Match Report

Read the full API match report file. Extract:
- **Winner API name**: from "Winner:" or top-ranked candidate
- **Confidence score and band**: e.g., "91% Strong match"
- **API endpoint**: HTTP method + URL pattern
- **Confluence page URL**
- **Request parameter mapping table**: every row
- **Response field mapping table**: every row (exact/renamed/transformed/missing/new)
- **Query parameter mapping table**: MTS DataGroup -> API query param
- **Data gaps**: all missing fields, transformations, constraints
- **Error/status handling**: HTTP status code mappings vs MTS status envelope
- **Converter bug scan** (if present)
- **Notification impacts** (if present)
- **Derived field impacts** (if present)
- **Config cascade table** (if present)

Store all as `MATCH_REPORT_DATA`.

### 0b. Validate Confidence

If confidence < 40%:
```
Warning: Match report confidence is <score>% (<band>). Below typical migration threshold.
Proceeding, but review the match report carefully before using generated code.
```

### 0c. System API Gate

If the match report indicates a system API:
```
The matched API is a system API. System APIs typically require a new microservice.
Select Strategy A (new microservice) or Strategy B (existing microservice) in the next step
to generate standalone endpoint code, or select Strategy C for in-place if appropriate.
```

### 0d. Load MTS Service Doc

Find and read the MTS service doc:
```
Glob docs/mts/service-doc-*<method>*.md
Glob docs/mts/test/service-doc-*<method>*.md
```

If no service doc found:
```
Error: No MTS service doc found for <method>. Run /mts-documentation first:
  /mts-documentation <ServiceName.method>
```

Extract:
- **Gateway class and method**
- **EDO response class name**
- **MTS service name constant**
- **MTS method constant**
- **Request fields and types**
- **Response field structure**

Store all as `MTS_SERVICE_DOC_DATA`.

### 0e. Load Settings

Read the settings file at `${CLAUDE_PLUGIN_ROOT}/config/mts-migrate-settings.md`.
Extract template URL, scaffolding defaults, clone location.
Store as `SETTINGS_DATA`.

---

## Step 1 — Strategy Selection

```
AskUserQuestion:
  question: "Which migration strategy do you want to use?"
  header: "Strategy"
  options:
    - label: "A) New microservice"
      description: "Clone a GitLab template into code/mts/<service>/, scaffold it, and generate the endpoint there"
    - label: "B) Existing microservice"
      description: "Provide a local path to an existing microservice and generate the endpoint there"
    - label: "C) In-place migration (Recommended)"
      description: "Generate dual-path routing with feature flag in this BUK repo (current behavior)"
```

Store the selection as `STRATEGY` (A, B, or C).

---

## Step 1.5 — Dispatch to Strategy File

Based on STRATEGY, follow the instructions in the corresponding strategy file. Pass all required input data. Each strategy file returns a structured result with `TARGET_REPO_PATH` and `PATTERN_PROFILE`.

### If STRATEGY = A

Follow instructions in `commands/mts-migrate-strategy-a.md`.

Pass: `SERVICE_NAME_METHOD`, `SETTINGS_DATA`

Receive: `STRATEGY_A_RESULT` with TARGET_REPO_PATH, PATTERN_PROFILE, SCAFFOLD_RESULT

### If STRATEGY = B

Follow instructions in `commands/mts-migrate-strategy-b.md`.

Pass: `SERVICE_NAME_METHOD`

Receive: `STRATEGY_B_RESULT` with TARGET_REPO_PATH, PATTERN_PROFILE

### If STRATEGY = C

Follow instructions in `commands/mts-migrate-strategy-c.md`.

Pass: `SERVICE_NAME_METHOD`, `MTS_SERVICE_DOC_DATA`, `MATCH_REPORT_DATA`

Receive: `STRATEGY_C_RESULT` with TARGET_REPO_PATH, PATTERN_PROFILE, CALLING_SERVICE_CLASS, CALLING_SERVICE_CLASS_PATH, FEATURE_FLAG_DATA, FEATURE_FLAG_FILE_PATH, CONFIG_DATA, CONFIG_FILE_PATH, BEAN_GAP_LIST

---

## Step 1.7 — Response Contract

```
AskUserQuestion:
  question: "Which response contract should the generated code use?"
  header: "Contract"
  options:
    - label: "mts-compat (Recommended)"
      description: "Converter maps ODS response to BUK EDO type. Same JSON shape as MTS path. Safe for in-place swap."
    - label: "ods-native"
      description: "Clean response model from ODS schema. New JSON shape. Use for new endpoints with no MTS consumers."
```

Store as `RESPONSE_CONTRACT` (mts-compat or ods-native).

If `RESPONSE_CONTRACT` = mts-compat:
  Read the BUK EDO class definitions (from MTS_SERVICE_DOC_DATA's EDO response class).
  Store verbatim field declarations as `BUK_EDO_CLASS_DEFINITIONS`.
  This applies to ALL strategies — Strategy A/B need it to generate a converter to the EDO type.

---

## Steps 2-5 — Delegate to Shared Steps

Follow instructions in `commands/mts-migrate-shared.md`.

Pass ALL collected data:
- `STRATEGY`
- `RESPONSE_CONTRACT`
- `TARGET_REPO_PATH` (from strategy result)
- `PATTERN_PROFILE` (from strategy result)
- `MATCH_REPORT_DATA` (from Step 0a)
- `MTS_SERVICE_DOC_DATA` (from Step 0d)
- `SERVICE_NAME_METHOD`
- (Strategy C only) `CALLING_SERVICE_CLASS`, `CALLING_SERVICE_CLASS_PATH`, `FEATURE_FLAG_DATA`, `FEATURE_FLAG_FILE_PATH`, `CONFIG_DATA`, `CONFIG_FILE_PATH`, `BEAN_GAP_LIST`
- (mts-compat only) `BUK_EDO_CLASS_DEFINITIONS`

The shared steps file handles code generation, test generation, issues doc, and final report.

---

## Error Handling

- **No match report found:** Report error, suggest running `/api-replacement-match` first.
- **No service doc found:** Report error, suggest running `/mts-documentation` first.
- **Calling service class not found (Strategy C):** Warn — user must manually add flag routing.
- **Confidence below 40%:** Warn but proceed. Generated code may have significant gaps.
- **Pattern Discovery fails:** Report which patterns could not be determined. Agents fall back to reasonable defaults but warn to review generated code style.
- **Clone fails (Strategy A):** Report the git error. Check network access and template URL.
- **Path invalid (Strategy B):** Re-prompt for a valid path.
- **Agent fails mid-generation:** Report which files were created and which were not. User can re-run `/mts-migrate` to retry.
