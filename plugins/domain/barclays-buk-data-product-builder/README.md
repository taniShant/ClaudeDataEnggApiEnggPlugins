# Data Product Builder

BUK Data Product Build Assistant — automated PySpark pipeline generation from Excel mapping documents, business requirement-to-data-model development, Source-to-Target Mapping (STTM) generation from requirement documents, target data models, SQL/PySpark code, or interview questionnaires with users, and data validation SQL generation for Athena and Databricks with exact reconciliation and SCD2 temporal checks.

> **Session model requirement:** This plugin requires `sonnet-default` or higher as the session model. `haiku-default` will fail on `/init` due to multi-step reasoning requirements. Launch Claude Code with:
>
> ```bash
> claude --model sonnet-default
> ```

## Plugin Workflow Overview

The plugin covers four stages of the data product lifecycle. Each stage operates independently but produces outputs that naturally feed the next. Stage 4 branches from Stage 2 output — it validates data against the mapping specification, independent of Stage 3 code generation:

```
Stage 1: DM                    Stage 2: STTM                     Stage 3: Code Generation
──────────────────────         ──────────────────────             ──────────────────────────
Business requirements    ──►   Requirements + data models   ──►   Mapping Excel (.xlsx)
     ↓                         (+ optionally SQL/artefacts)            ↓
Data models                         ↓                          PySpark pipelines,
                               Mapping documents               configs, tests, DAGs
                                     │
                                     └──►   Stage 4: Data Validation
                                            ──────────────────────────
                                            Mapping + intent
                                                 ↓
                                            Validation SQL (Athena/Databricks),
                                            reconciliation & SCD2 temporal checks
```

**Which entry point should I use?**

| You have... | Start at | Commands |
|-------------|----------|----------|
| A business requirement or JIRA ticket | **Stage 1 — DM** | `/dm-bra` → `/dm-model` → `/dm-validate` |
| Requirements + data models (optionally SQL/PySpark code) | **Stage 2 — STTM** | `/sttm-init` → `/sttm-generate` |
| A ready mapping Excel document | **Stage 3 — Code Generation** | `/init` → `/push` |
| Generated mapping + intent, **or** a mapping Excel | **Stage 4 — Data Validation** | `/dv-init` → `/dv-generate` → `/dv-report` |

---

## Prerequisites

- Claude Code CLI (v2.1.100+)
- **Session model: `sonnet-default` or higher** — `haiku-default` may fail on first `/init` due to multi-step reasoning requirements; subagents use their own model overrides
- Access to GitLab
- Mapping Excel document (16-column format) — required for Stage 3 (Code Generation)
- Optional: `JIRA_AUTH_TOKEN` environment variable for automatic JIRA comment updates on push. Obtain a personal access token from [JIRA Personal Access Tokens](https://estjira.barcapint.com/secure/ViewProfile.jspa).
- Optional: `CONFLUENCE_BASE_URL` and `CONF_PAT` environment variables for Confluence page and attachment fetching in `/dm-bra`. See the [barclays-buk-confluence README](../../tooling/barclays-buk-confluence/README.md) for setup.
- Recommended: Python 3.10+ for syntax validation, test execution, Excel export, and SQL parsing (see below)

### Python Runtime (Recommended)

Python is **recommended** for full plugin functionality. Core artefact generation works without it, but quality checks, Excel export, and SQL parsing require Python 3.10+:

| Feature | Requirement | When It Runs |
|---------|-------------|--------------|
| **Syntax validation** (`py_compile`) | Bare Python only (no packages) | Automatically after each `/gen-*` command |
| **Test execution** (`pytest`) | Python + `pytest` + `pyspark` | Optionally after `/gen-tests`; on-demand via `/run-tests` |
| **Excel export** (`openpyxl`) | Python + `openpyxl` | `/sttm-export`, `/sttm-generate` Excel output |
| **SQL parsing** (`sqlglot`) | Python + `sqlglot` | `/sttm-parse-sql`, `/sttm-generate` DDL pre-extraction |

Detection order (see `agents/refs/python-runtime-contract.md`): `python` → `$PYTHON_PATH` → `python3` → `py` → `null`.

**Setup (choose one):**

```bash
# Option A: ensure 'python' is on PATH (most common — auto-detected first)

# Option B: set environment variable before launching Claude Code
export PYTHON_PATH="/path/to/python"

# Option C: add to project .claude/settings.json
{ "env": { "PYTHON_PATH": "/path/to/python" } }

# Option D: 'python3' or 'py' (Windows launcher) on PATH are also auto-detected
```

**Behaviour when Python is unavailable:** All generation commands run normally. Syntax check and test execution are skipped with warnings. `/push` soft-passes the test quality gate with an explicit disclaimer. STTM Excel export (`/sttm-export`) requires Python and will halt with an error if unavailable.

**Behaviour when Python is available but tests fail:** Generation pipeline continues (non-blocking). `/push` runs pytest and blocks push if tests fail (with 3 auto-fix retries). Syntax errors (`py_compile` failures) always block `/push`.

---

## Key Concepts

### Supported Platforms

- **AWS Glue 4.0** — DTX/DTXOG framework, Iceberg tables, S3
- **Databricks** — Foundation Library, Unity Catalog, Iceberg

### Data Product Types

- **FDP** — Foundation Data Product (Base layer; prefix `fdp_*` or `shared_fdp_*`)
- **CDP** — Consolidated Data Product (sources: FDP primarily; BASE allowed exceptionally; prefix `cdp_*` or `shared_cdp_*`)
- **BDP** — Business Data Product (sources: FDP/CDP only; prefix `bdp_*` or `shared_bdp_*`)

### Naming Conventions

- **Glue** artefacts use `{db}_{table}` (e.g. `fdp_uk_mortgage_db_account_wm`)
- **Databricks** artefacts use `{schema}_{table}` (e.g. `uk_mortgage_account_wm`)

This guarantees unique file names across multi-table sessions without batch indexing.

### Multi-Source-System Pipelines

When multiple independent source systems feed a single target table, the plugin generates **separate artifacts per source system** — each executed as an independent job. This applies to both Glue and Databricks.

- **Declaration:** Add `source_system:<label>` to Additional Context (Column K) of the mapping Excel. Each distinct label produces a separate set of artifacts. If `source_system` is absent, normal single-flow generation applies.
- **Multiple databases ≠ multiple source systems:** A mapping can join tables from `e_cms_db` and `ref_common_db` — this is a normal multi-table join, NOT multi-source-system. Only the explicit `source_system` key triggers artifact splitting.
- **Combined mode (UNION exception):** When the mapping explicitly uses `Union Branch N:` structured format, a single artifact set is generated with `unionByName()` logic, even if `source_system` is declared.
- **Naming:** Databricks uses `{source_system}` as a directory level; Glue uses `_{source_system}` suffix in file names.

### Gates (Overview)

The plugin uses a gating state machine to collect required information before code generation. Gates are resolved sequentially — each must pass before dependent commands can execute.

- **Hard gate** — Pipeline HALTs until resolved. No downstream commands can execute.
- **Soft gate** — Pipeline continues with defaults or partial context. Improves output quality but does not block.
- **Implicit gate** — Resolved automatically without user interaction.

See [Gates (Detailed Reference)](#gates-detailed-reference) for the full gate flow and per-gate documentation.

---

## Stage 1 — Data Model Development (DM)

The DM stage transforms business requirements into formal data models. Each command runs independently — invoke them in sequence or use any one standalone.

### Recommended Workflow

```
/dm-bra "Track savings eligibility under Consumer Duty"
  → produces: dm-output/<ref>/business-requirement.md
  → suggests: /dm-model dm-output/<ref>/business-requirement.md

/dm-model dm-output/<ref>/business-requirement.md
  → produces: dm-output/<ref>/data-model.md
  → suggests: /dm-validate dm-output/<ref>/data-model.md --type dm

/dm-validate dm-output/<ref>/data-model.md --type dm
  → produces: APPROVED / REJECTED verdict with findings
```

### /dm-bra — Business Requirements Analyst

Accepts a JIRA ticket reference (auto-fetches ticket + attachments + Confluence pages + Confluence page attachments)
or direct business input (text or file path). Produces a 9-section structured
business requirement document.

> **Prerequisites for JIRA mode:** Ensure `CONFLUENCE_BASE_URL` and `CONF_PAT` are set if the ticket links to Confluence pages (see [Prerequisites](#prerequisites)).

```bash
# From JIRA ticket (auto-fetches content, attachments, linked Confluence pages)
/dm-bra BUKL2CUSX-2355

# From informal business ask
/dm-bra "Track savings eligibility under Consumer Duty"

# From existing document
/dm-bra path/to/business-input.md

# Modify an existing requirement
/dm-bra --modify dm-output/BUKL2CUSX-2355/business-requirement.md
```

### /dm-model — Data Modeller

Accepts a business requirement document and designs the target data model with
ER diagrams, composite keys, audit columns, and optional KPI normalised pattern.

```bash
/dm-model dm-output/BUKL2CUSX-2355/business-requirement.md
```

### FDP Source Domains (Optional)

The Data Modeller agent (Elena) can ground data model design in existing **Foundational Data Product (FDP)** entity definitions. FDP CSVs provide entity structure, grain (composite PKs), attribute names, data types, and business definitions — reducing net-new design and improving alignment with the enterprise logical data model.

**Location:** `data/source-domains/` — created automatically by `/dm-bra` on first run.

**CSV schema (11 columns):**

| Column | Description |
|--------|-------------|
| Entity Name | Logical entity name (e.g., SAVINGS ACCOUNT BALANCE) |
| Table Name | Physical table name (e.g., SAVINGS_ACCOUNT_BALANCE) |
| Attribute Name | Business name of the column |
| Column Name | Physical column name |
| Datatype | VARCHAR, INTEGER, BIGINT, DECIMAL, DATE, etc. |
| Length | Character length or numeric precision |
| Scale | Numeric scale (decimal places) |
| Primary Key | "K" if part of composite PK |
| Allow Nulls | "Y" or "N" |
| Definition | Business definition of the attribute |
| Note | Additional notes (e.g., CDE Asset ID) |

See `data/source-domains/sample_domain.csv` for the exact format.

**How to populate:** Copy domain CSV exports from the enterprise FDP catalogue or ER Studio exports. One CSV per source domain (e.g., `Customer.csv`, `Savings.csv`, `Mortgage.csv`, `Credit_Card.csv`).

**Without FDP CSVs:** `/dm-model` works normally — Elena designs from the business requirement alone. FDP alignment features (entity classification as Logical Only vs Physical, FDP reuse summary, deviation tracking) are skipped.

### /dm-validate — Quality Gate Validation

Validates BRA or Data Modeller output against MUST-HAVE and SHOULD-HAVE checks.

```bash
/dm-validate dm-output/BUKL2CUSX-2355/business-requirement.md --type bra
/dm-validate dm-output/BUKL2CUSX-2355/data-model.md --type dm
```

### /dm-status — Progress Display

Shows what data model artefacts exist and suggests the next command.

```bash
/dm-status
```

### DM Output Structure

```
dm-output/<JIRA-REF>/
├── business-requirement.md    ← /dm-bra output (9 sections)
├── data-model.md              ← /dm-model output (ER diagrams + table definitions)
└── context/                   ← JIRA mode audit trail
    ├── jira-ticket.md
    ├── attachments.json
    ├── attachment_content.md
    └── confluence-pages.md

data/source-domains/           ← FDP CSV files (optional, created by /dm-bra)
├── sample_domain.csv          ← Template showing expected CSV format
├── Customer.csv               ← (user-provided) FDP entity definitions
├── Savings.csv                ← (user-provided)
└── ...                        ← One CSV per source domain

dm-session/
└── tracking.json              ← DM session tracking (commands run, output paths, validation verdicts, timestamps)
```

---

## Stage 2 — Source-to-Target Mapping (STTM)

The STTM stage generates Source-to-Target Mapping documentation from requirements, data models, and optionally SQL/PySpark code or other artefacts. STTM maps every column in a target data product table to its source, transformation logic, and provenance metadata. The output is a mapping Excel that can be used as input to Stage 3 (Code Generation).

### STTM Quick Start

```bash
# 1. Initialize workspace
/sttm-init

# 2. Place your SQL/PySpark code in input/code/ and target schema in input/

# 3. Run the full pipeline (8 steps: ingest → interview → classify → resolve → generate → validate → export)
/sttm-generate

# Or run individual steps:
/sttm-classify          # 4-axis classification (DP type × table type × crypto)
/sttm-parse-sql         # Extract column lineage from SQL/PySpark
/sttm-validate          # Run 102 validation checks
/sttm-export            # Export JSON → Excel (Mapping + Source Volumetrics sheets)
/sttm-resolve           # Interactively resolve low-confidence fields
```

### STTM Agents

| Agent | Model | Purpose |
|-------|-------|---------|
| `sttm-scenario-classifier-agent` | Sonnet | 4-axis classification (FDP/CDP/BDP × Table Type × Crypto × I/O Mode) |
| `sttm-sql-lineage-agent` | Opus | Column-level lineage extraction from SQL/PySpark/Teradata |
| `sttm-row-generator-agent` | Opus | Generate all 16 mapping fields per target column |
| `sttm-validation-agent` | Sonnet | 102 validation checks (schema, content, scenario, artefact, format) |
| `sttm-provenance-agent` | Sonnet | Per-field provenance tracking with confidence scores |

### STTM Output Structure

```
output/
├── {prefix}_sttm.json              ← Canonical mapping (JSON source of truth)
├── {prefix}_sttm.xlsx              ← Excel projection (Mapping + Source Volumetrics sheets)
├── {prefix}_provenance.json        ← Per-field provenance metadata
├── {prefix}_provenance.xlsx        ← Excel provenance (Field Provenance + Business Rules sheets)
├── {prefix}_validation_report.json ← 102-check validation results
├── .sttm_manifest.json             ← Output discovery manifest (persists across runs)
├── sttm_session_state.json         ← Session state tracking (pipeline progress, classification, validation)
└── .intermediate/                  ← Temp inter-stage files (deleted after export, kept with --debug)
    ├── context_inventory.json      ← Step 1: ingested file inventory + code pre-scan
    ├── interview_summary.json      ← Step 2: compressed interview answers
    ├── classification.json         ← Step 4: classification result
    ├── lineage_cache.json          ← Step 5: full SQL lineage output
    ├── batch_{N}_rows.jsonl        ← Step 6: per-batch generated rows
    ├── merged_rows.json            ← Step 6: combined rows post-merge
    └── scoped_validation_rules.json ← Step 7: classification-scoped rules
```

Where `{prefix}` = `{target_database}_{target_table}` (single table) or `{target_database}` (multiple tables).

### STTM Pipeline State Flow

```
/sttm-init → creates workspace + output/sttm_session_state.json

/sttm-generate (8 steps):
  Step 1 INGEST     → context_inventory.json       → state: ingestion_status, output_prefix
  Step 2 INTERVIEW  → interview_summary.json        → state: step_2 completed/skipped
  Step 3 NORMALIZE  → (in-memory)                   → state: step_3 completed
  Step 4 CLASSIFY   → classification.json           → state: classification block
  Step 5 LINEAGE    → lineage_cache.json            → state: step_5 completed
  Step 6 ROWGEN     → merged_rows.json              → state: step_6 completed
  Step 7 VALIDATE   → validation_report.json        → state: validation_result block
  Step 8 EXPORT     → {prefix}_sttm.json/.xlsx      → state: output_files, overall=completed

/sttm-classify  → updates classification in state
/sttm-validate  → updates validation_result in state
/sttm-resolve   → updates ambiguities_status in state
/sttm-export    → updates output_files in state
```

### STTM Input Structure (created by /sttm-init)

```
input/
├── target_schema.xlsx        ← Target schema (required)
├── code/                     ← SQL/PySpark code files
├── source_metadata/          ← Optional: column_metadata.json, join_candidates.json
├── source_dictionary/        ← Optional: data_dictionary.json, model.dm1
└── design_docs/              ← Optional: markdown design documents
```

### STTM Reference Files

| Category | Location | Count |
|----------|----------|-------|
| Configs | `configs/sttm/` | 9 YAML files |
| Agent refs | `agents/refs/sttm-*.md` | 15 reference documents |
| Command refs | `commands/refs/sttm-guided-mode-questions.md` | 1 |
| Skill | `skills/sttm-domain-knowledge/SKILL.md` | 1 |
| Templates | `templates/sttm/mapping_spec.md` | 1 |
| Examples | `examples/sttm/*.json` | 15 example scenarios (31 JSON files) |
| Schemas | `schemas/sttm_input_contract.schema.json`, `schemas/sttm_session_state.schema.json` | 2 |
| Design docs | `docs/sttm_*.md` | 2 |

---

## Stage 3 — Code Generation

### Quick Start Guide

#### Step 1 — Prepare your mapping document

Create a mapping Excel (.xlsx) with all 16 required columns:

| # | Column | Description |
|---|--------|-------------|
| 1 | Target Database | Target database name (e.g. `fdp_uk_mortgage_db`) |
| 2 | Target Table | Target table name (e.g. `mortgage_account`) |
| 3 | Target Column Name | Column name in snake_case |
| 4 | Target Column Definition/Description | Business description of the column |
| 5 | Target Column Datatype | Spark/Iceberg datatype (`string`, `int`, `decimal(18,2)`, `date`, `timestamp`) |
| 6 | Target Column Null Flag | `Y` = nullable, `N` = NOT NULL |
| 7 | Source Database | Source database (e.g. `e_ilp_db`) |
| 8 | Source Table Name | Source table name |
| 9 | Source Column Name | Source column name |
| 10 | Business Logic/Transformation Logic | Transformation expression (e.g. `Direct mapping`, `CAST(...)`, crypto UDF, or structured join format) |
| 11 | Additional Context | Pipe-delimited key:value metadata: `load_type`, `partition_key`, `process_frequency`, `source_system`, `cdc_type`, `cdc_exclude`, `rolling_deletion_predicate`, etc. `source_system:<label>` triggers per-source-system artifact generation. |
| 12 | Target Table description | Business description of the target table |
| 13 | Transformation Type | `Direct` / `Derived` / `Lookup` / `Direct - Type Cast` — guides PySpark generation strategy |
| 14 | Default Value | Fallback value when logic yields NULL (e.g. `-99`, `0`, `NA`). Blank if no default. |
| 15 | Target Table Type | `scd2` / `scd1` / `transactional` — declares table type (bypasses heuristic analysis) |
| 16 | Key Column | `Y` / `N` — marks primary key columns for the table |

#### Step 2 — Initialize and run the plugin

```bash
# Interactive mode — run commands step by step
/init path/to/mapping.xlsx --platform glue

# With explicit domain knowledge file
/init path/to/mapping.xlsx --platform glue --domain-knowledge ./docs/mortgage_knowledge.md

# Full-automation mode — entire pipeline runs end-to-end (no user prompts)
/init path/to/mapping.xlsx --platform glue --domain-knowledge ./docs/mortgage_knowledge.md --full-automation
```

Use `/status` at any time to check progress.

#### Step 3 — Review and push

After all artefacts are generated (automatic in full-automation mode; manual in interactive mode):

```
/review      # Code quality review
/validate    # Red flag validation
/push        # Push to GitLab + create MR (always manual — never auto-pushed)
```

### Common Workflows

**Full-automation (recommended for known-good mappings):**
```
/init mapping.xlsx --platform glue --domain-knowledge ./team_rules.md --full-automation
# Entire chain runs automatically: parse → classify → intent → mesh → config → transform → wrapper → dtxog → dag → tests → validate
/push        # Push to GitLab (always explicit)
```

**Interactive mode — Glue (step by step):**
```
/init mapping.xlsx --platform glue
/parse-mapping
/classify-sources
/identify-intent
/gen-mesh
/gen-config
/gen-transform
/gen-wrapper
/gen-dtxog
/gen-dag
/gen-tests
/review
/validate
```

**Full-automation — Databricks:**
```
/init mapping.xlsx --platform databricks --domain-knowledge ./kyc_rules.md --full-automation
# Auto-chains: parse → classify → intent → config → transform → driver → DDL → bundle → dag → tests → validate
/push
```

**Crypto-enabled (tokenize/detokenize):**
- Ensure your mapping Excel has complete UDF patterns in the transformation logic column
- Example: `cloud_api_udf_UK_TOK_ACCT_L0R0_NUM_DE_unprotect(source_column)`
- Incomplete crypto patterns (keyword only, no DE name) will HALT the session

---

## Data Dependency Graph

Commands have data dependencies — each requires specific session artefacts produced by upstream commands. The diagrams below show the dependency flow. Commands can be invoked in any order provided their input artefacts exist; the standard flow satisfies all dependencies naturally.

### AWS Glue Flow

```
/init ──► /parse-mapping ──► /classify-sources ──► /identify-intent
                                                                     │
    ┌────────────────────────────────────────────────────────────────┘
    │
    ▼
/gen-mesh ──► /gen-config ──► /gen-transform ──► /gen-wrapper
                                                                   │
    ┌──────────────────────────────────────────────────────────────┘
    │
    ▼
/gen-dtxog ──► /gen-dag ──► /gen-tests ──► /review ──► /validate ──► /push
```

### Databricks Flow

```
/init ──► /parse-mapping ──► /classify-sources ──► /identify-intent
                                                                     │
    ┌────────────────────────────────────────────────────────────────┘
    │
    ▼
/gen-config ──► /gen-transform ──► /gen-driver ──► /gen-ddl ──► /gen-bundle ──► /gen-dag
                                                                                                          │
    ┌─────────────────────────────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
/gen-tests ──► /review ──► /validate ──► /push
```

> **Source table type classification priority**: (0) Source Volumetrics tab `table_type` (analyst-declared, highest priority) → (1) Domain knowledge hints → (2) Mapping document inference → (3) User prompt (HALT).

---

## Stage 4 — Data Validation (DV)

Stage 4 is an **independent** validation SQL generator that produces read-only SQL queries to verify that live data in the target matches the source exactly according to the mapping specification. The mapping document is the sole validation source of truth — generated PySpark code is not referenced.

### Overview

| Feature | Description |
|---------|-------------|
| **Source of truth** | Mapping document (`mapping_parsed.json` + `intent_identification.json`) |
| **Independence** | Does not reference generated PySpark/Spark SQL code |
| **Tolerance** | Zero — PASS only when all mismatch counts are zero |
| **Dialects** | Athena SQL (Glue flow) and Databricks SQL |
| **SCD2 support** | Full temporal validation: overlap, gap, stitching, active record, Day 0/Day 1 |
| **NOT_EVALUATED** | When exact semantics are unavailable (missing precision, ambiguous boundary, inaccessible source) |

### Quick Start

**Dependent mode** (after running the DE code-generation pipeline):
```
/dv-init --engine athena
/dv-generate
/dv-report
```

**Standalone mode** (from mapping Excel — no DE pipeline needed):
```
/dv-init --engine athena --excel path/to/mapping.xlsx
/dv-generate
/dv-report
```

**Standalone with domain knowledge (Databricks, preprd):**
```
/dv-init --engine databricks --excel Mortgage_Mapping.xlsx --domain-knowledge ./docs/mortgage_rules.md
/dv-generate --env preprd --mode day0
/dv-report
```

**Databricks dependent flow:**
```
/dv-init --engine databricks
/dv-generate --env dev
/dv-report
```

**SCD2 with Day 0 checks:**
```
/dv-init --engine athena
/dv-generate --mode day0
/dv-report
```

### Commands

| Command | Purpose |
|---------|---------|
| `/dv-init` | Initialize DV session — set engine, create session state. Supports standalone mode (`--excel`) when DE pipeline has not run |
| `/dv-generate` | Generate validation contracts, dialect-neutral plans, and rendered SQL. For Databricks, resolves catalog names from tenancy registry using `--env` (default: `dev`) |
| `/dv-report` | Generate validation report from plans and optionally user-provided execution results |

### Validation Check Categories

| Category | Checks | Description |
|----------|--------|-------------|
| Exact Reconciliation | ER-01 – ER-08 | Row count, aggregate, EXCEPT-based, key-based, multiset comparison |
| SCD2 Temporal | SCD2-01 – SCD2-18 | Overlap, gap, stitching, active record, Day 0/Day 1 scenarios |
| Null Check | NC-01 – NC-02 | Mandatory column and PK null detection |
| Duplicate Check | DC-01 – DC-02 | PK and business-key uniqueness |
| Datatype Check | DT-01 – DT-03 | CAST validation, precision/scale verification |
| Business Rule | BR-01 – BR-04 | Value domain, referential integrity, aggregate reconciliation |

### Output Structure

```
generated/
├── glue/validation/                    ← Athena engine
│   └── {db}_{table}/
│       ├── {db}_{table}_validation.sql
│       └── {db}_{table}_results_summary.sql
└── databricks/validation/              ← Databricks engine
    └── {db}_{table}/
        ├── {db}_{table}_validation.sql
        └── {db}_{table}_results_summary.sql
```

### Databricks Catalog Resolution

When `--engine databricks`, `/dv-generate` resolves Unity Catalog names so generated SQL is immediately runnable (no manual placeholder replacement needed):

| Value | Resolution Source | Example |
|-------|-------------------|---------|
| `source_catalog` | Fixed per environment (from `databricks-tenancy` skill) | `077382350852_buk_data_products` (dev) |
| `target_catalog` | Tenancy registry → domain knowledge → user prompt | `dev_buk_bbkyc_bdp` |
| `target_schema` | `target_database` from mapping (exact) | `bdp_uk_bbcdd_db_dbxw` |
| `source_schema` | Per-column `source_database` from mapping | `uk_nps_db_icbg` |

Resolution priority: DE session state (dependent mode) → tenancy registry lookup → domain knowledge → ask user. If catalog cannot be resolved automatically, the user is prompted via `AskUserQuestion`.

### SCD2 Temporal Validation

BUK CDAO convention: `eff_end_date` is **inclusive** (`prev.eff_end_date = next.eff_start_date`). Sentinel: `'3499-12-31'`.

- **Steady state** (default): Overlap, gap, stitching, active record invariants (SCD2-01 – SCD2-11)
- **Day 0**: Additionally validates initial population (SCD2-12, SCD2-13)
- **Day 1**: Additionally validates tracked changes, idempotency, late-arriving (SCD2-14 – SCD2-18)

Gap handling is **mapping-driven**: gaps may be legitimate (period collapsing, intermittent entity). Check severity adapts per mapping documentation.

### Security

- **Read-only SQL only** — no DDL, DML, dynamic SQL, or catalog mutations
- **SQL safety validator** — 10 rules (SAFETY-01 – SAFETY-10) applied to all generated files
- **No execution** — SQL is generated, not executed. Users run queries through their own Athena/Databricks interfaces
- **Results are counts-only** — no row-level data, business keys, or PII enters the report pipeline

### Troubleshooting

| Issue | Resolution |
|-------|-----------|
| `/dv-init` fails with missing prerequisites | Run `/parse-mapping` and `/identify-intent` first, **or** use `--excel <path>` for standalone mode |
| Safety validator HALT | Check violation details — usually a hardcoded date or DML keyword in comment |
| NOT_EVALUATED checks | Review the specific reason — typically missing source precision or inaccessible table |
| Results Excel rejected | Ensure single sheet "Validation Results" with exactly 13 columns A–M |

---

## Available Commands

### DM Commands (Stage 1)

| Command | Purpose |
|---------|---------|
| `/dm-bra` | Business Requirements Analyst — structured requirement from JIRA ticket or business input |
| `/dm-model` | Data Modeller — target data model with ER diagrams from requirement document |
| `/dm-validate` | Validate BRA or Data Modeller output against quality gates |
| `/dm-status` | Display data model outputs and suggested next step |

### STTM Commands (Stage 2)

| Command | Purpose |
|---------|---------|
| `/sttm-init` | Initialize STTM workspace (input/output directories, .gitignore) |
| `/sttm-classify` | Classify target along 4 axes (DP type, table type, crypto aspect) |
| `/sttm-parse-sql` | Extract column-level lineage from SQL/PySpark code |
| `/sttm-generate` | Full 8-step STTM pipeline (ingest → interview → classify → resolve → generate → validate → export) |
| `/sttm-resolve` | Interactive resolution of below-threshold confidence fields |
| `/sttm-validate` | Validate STTM output against 102 checks (schema, content, scenario, artefact, format) |
| `/sttm-export` | Export STTM JSON to formatted Excel (Mapping + Source Volumetrics sheets) |

### Code Generation Commands (Stage 3)

| Command | Purpose | Platform |
|---------|---------|----------|
| `/init` | Initialize session from mapping Excel | Both |
| `/parse-mapping` | Parse and validate Excel columns | Both |
| `/classify-sources` | Classify source table types | Both |
| `/identify-intent` | Identify table type, load type, grain, PK | Both |
| `/gen-mesh` | Generate Mesh JSON for table creation | Glue |
| `/gen-config` | Generate pipeline config (config.yml / config.json) — source columns, filters, CDC, crypto | Both |
| `/gen-transform` | Generate PySpark transformation scripts | Both |
| `/gen-wrapper` | Generate DTX-BYOC wrapper (config.json already exists from `/gen-config`) | Glue |
| `/gen-dtxog` | Generate DTXOG orchestration config | Glue |
| `/gen-driver` | Generate Databricks driver notebook | Databricks |
| `/gen-ddl` | Generate Iceberg DDL (embedded in table_creation_utility.py) | Databricks |
| `/gen-bundle` | Generate DABs bundle (databricks.yml + job YAMLs) | Databricks |
| `/gen-dag` | Generate Airflow DAG files for scheduling, dependency checks, and job orchestration | Both |
| `/gen-tests` | Generate pytest test suite (>90% coverage) + syntax check + optional test execution | Both |
| `/run-tests` | Re-run pytest on generated test suite (standalone, non-blocking) | Both |
| `/review` | Code quality review of generated artefacts | Both |
| `/validate` | Validate artefacts against red flags | Both |
| `/push` | Push via quality gates + create MR | Both |
| `/status` | Display session progress (read-only) | Both |
| `/resume` | Resume auto-chain from HALT point (applies intent overrides) | Both |

### DV Commands (Stage 4)

| Command | Purpose |
|---------|---------|
| `/dv-init` | Initialize DV session — set engine, verify prerequisites |
| `/dv-generate` | Generate validation SQL (contracts, plans, rendered SQL). For Databricks, resolves catalog names from tenancy registry using `--env` (default: `dev`) |
| `/dv-report` | Generate validation report from plans and execution results |

---

## Gates (Detailed Reference)

The plugin uses a gating state machine to collect required information before code generation begins. Gates are resolved sequentially — each must pass before dependent downstream commands can execute.

### Gate Flow

```
/init
    │
    ▼
[G1] Platform Selection ──────────── Hard gate (blocks all /gen-* commands)
    │
    ▼
/parse-mapping
    │
    ├── [G0.5] Domain Knowledge ──── Soft gate (auto-discovered from target_database, non-blocking)
    ├── [G1.5] Data Product Type ─── Implicit (auto-derived from prefix, no user prompt)
    ├── [G3] S3 Locations ────────── Hard gate (Glue only, auto-selected from tenancy skill)
    └── [G5-C] Crypto DE Extraction  Hard gate (HALT if extraction failed)
    │
    ▼
/classify-sources
    │
    ▼
/identify-intent
    │
    ├── [G5-grain] Intent Clarification ── Hard gate (only if intent unresolved per table)
    └── [G5] Placeholder Resolution ────── Soft gate (blocking placeholders only)
    │
    ▼
Code Generation
```

### Gate Details

| Gate | Type | Resolved During | Mechanism | Blocks |
|------|------|----------------|-----------|--------|
| **G1** | Hard | `/init` | User prompt (`glue` / `databricks`) or `--platform` argument | All `/gen-*` commands |
| **G0.5** | Soft | `/parse-mapping` | Auto-discovery from `target_database` in parsed Excel; user can override with `--domain-knowledge` in `/init` | Nothing (advisory context for intent identification) |
| **G1.5** | Implicit | `/parse-mapping` | Auto-derived from target database prefix: `fdp_*` → FDP, `cdp_*` → CDP, `bdp_*` → BDP (also `shared_fdp_*` → FDP, `shared_cdp_*` → CDP, `shared_bdp_*` → BDP) | Layer promotion validation |
| **G3** | Hard | `/parse-mapping` | Auto-selected from tenancy skill (Tenancy Registry: bucket shortname + account ID + pattern) | `/gen-mesh`, DTXOG S3 paths (Glue only) |
| **G5-grain** | Hard | `/identify-intent` | User prompted per-table if extended priority chain (0→0.5→1→1.5→2→3) cannot resolve: grain, type, PK, partition, load_type | Transform + artefact generation for that table |
| **G5** | Soft | Per-artefact | Inline placeholder resolution — user prompted only for blocking placeholders (e.g., Unity Catalog names) | Specific artefact with unresolved placeholder |
| **G5-C** | Hard | `/parse-mapping` | Crypto DE name extraction from UDF pattern or Protegrity reference; HALT if `extraction_failed: true` | ALL code generation (entire session halted) |

### Gate Persistence

- Gate answers persist for the session lifetime in `session/session_state.json` under `gates_resolved[]`
- If the mapping document is replaced mid-session, gates are preserved but downstream artefact status is invalidated
- Platform (G1) is immutable — changing platform requires a new session via `/init`
- G4 (source classification) is now fully local — no external API required

### G1 — Platform Selection

```
Which compute platform is this pipeline targeting?

- 1 or glue     — AWS Glue (DTX/DTXOG framework)
- 2 or databricks — Databricks (Foundation Library + Unity Catalog)
```

Accepted inputs: `1`, `2`, `glue`, `databricks`, `aws glue`, `dtx`, `dtxog`, `dbx` (case-insensitive). Unrecognised input re-prompts G1.

### G0.5 — Domain Knowledge (Optional)

Resolved during `/parse-mapping` (not `/init`) — avoids reading the Excel file twice.

**Auto-discovery** (default): After parsing the Excel, the plugin looks up `target_database` in the appropriate tenancy skill to find the Feature Team Name:
- Glue → `tenancy` skill Tenancy Registry (match Hive/Iceberg Database column)
- Databricks → `databricks-tenancy` skill Tenancy Infrastructure Registry (match Target DB column)

Then searches `${CLAUDE_PLUGIN_ROOT}/configs/domain_knowledge/` for `{feature_team_name}_knowledge.md` (e.g., Glue: `fdpchnlcc_knowledge.md`; Databricks: `buk_bbkyc_bdp_knowledge.md`). If found, loaded silently.

**Explicit override**: Pass `--domain-knowledge <path>` to `/init` to load a specific file immediately (skips auto-discovery).

No user prompt in either case — domain knowledge is always non-blocking.

### G1.5 — Data Product Type (Implicit)

No user prompt. Derived from target database prefix during `/parse-mapping`:

| Prefix | DP Type | Target Account | Source Layer |
|--------|---------|---------------|--------------|
| `fdp_*` | FDP | DDA | BASE (`e_*` databases) |
| `cdp_*` | CDP | DDA | FDP/CDP (BASE allowed exceptionally — WARNING logged) |
| `bdp_*` | BDP | BCA | FDP/CDP (no BASE, no BDP) |
| `shared_fdp_*` | FDP | DDA | BASE (`e_*` databases) |
| `shared_cdp_*` | CDP | DDA | FDP/CDP (BASE allowed exceptionally — WARNING logged) |
| `shared_bdp_*` | BDP | BCA | FDP/CDP (no BASE, no BDP) |

Shared variants (`shared_fdp_*`, `shared_cdp_*`, `shared_bdp_*`) resolve to the same parent type and set `is_shared_data_product = true` in session state.

Invalid prefix (e.g., `stg_`, `tmp_`) → ERROR. Mixed prefixes across tables → ERROR.

### G3 — S3 Locations (Glue Only)

Auto-selected from tenancy skill during `/parse-mapping`. The plugin:
1. Parses target database to extract DP type + domain
2. Looks up tenancy in tenancy skill for bucket shortname
3. Determines Hive vs Iceberg from database suffix
4. Builds full bucket name per environment using S3 naming pattern

No user prompt unless tenancy is not found in tenancy skill (then HALT with guidance).

### New / Unlisted Target Database

If your mapping Excel's `target_database` does not match any entry in the tenancy registry (`aws-tenancy` or `databricks-tenancy` skills), the plugin handles it gracefully:

1. **Domain Knowledge (G0.5)** — Auto-discovery skips with a WARNING. Non-blocking. You can still supply domain knowledge manually via `--domain-knowledge <path>` on `/init`.

2. **Infrastructure Resolution (G3)** — The plugin switches to **interactive infrastructure collection** and prompts you for the missing values in batches:
   - **Batch 1 (blocking):** tenancy name, domain name
   - **Batch 2 — Glue (blocking):** bucket shortname, catalog type (hive/iceberg), ITSI codes per environment, production compid
   - **Batch 3 — Databricks (blocking):** Unity Catalog names, workspace folders, service principals, AD groups, ITSI/tags per environment
   - A confirmation summary is shown before proceeding.
   - If blocking values cannot be provided after one re-prompt → session **HALTs**.

3. **Downstream** — Any values you could not supply are stored as `{{placeholders}}`. The `/validate` command will flag them before `/push`.

> **Tip:** To avoid interactive prompts, ask your platform team to add the new tenancy to the relevant skill file (`skills/aws-tenancy/SKILL.md` or `skills/databricks-tenancy/SKILL.md`) before running `/init`.

### G5-grain — Intent Clarification (Per Table)

Only triggered if the full priority chain (0→0.5→1→1.5→2→3) fails to resolve intent for a target table:

```
For table: {database}.{table}

Please confirm the following:
- Table type: scd2 / scd1 / transactional?
- Grain: What uniquely identifies a row?
- Primary key columns?
- Partition column(s)?
- Load type: full / incremental / full_then_incremental?
```

Priority chain (checked before prompting user):
0. Intent overrides (`session/intent_overrides.json` — user-supplied)
0.5. Mapping column signals (`Target Table Type` → table_type, `Key Column` → PK)
1. Mapping document (transformation logic + target description)
1.5. Additional Context (load_type keywords)
2. Domain knowledge MD (grain/type hints)
3. User prompt + structural analysis (audit column heuristics H0/H0b)

**Full-automation recovery:** If G5-grain HALTs in full-automation mode, the pipeline generates `session/intent_resolution_report.md` with per-field analysis and fix options. Users can supply missing values in `session/intent_overrides.json` and run `/resume` to continue from the HALT point without re-running completed steps.

### G5-C — Crypto DE Extraction (Hard HALT)

If mapping contains crypto indicators (tokenize/detokenize keywords) but DE name extraction fails:
- `extraction_failed: true` → **HALT entire session**
- User must fix mapping Excel with complete UDF pattern or Protegrity reference
- No placeholder fallback — crypto generation is refused until DE name is extractable

---

## Output Structure

### Code Generation Output

The plugin produces the following directory structure in the user's working directory:

```
project_root/
├── session/                                        # Session state & intermediate files
│   ├── session_state.json                          # Full session state (gates, phases, artefact_status, chain_checkpoints)
│   ├── mapping_parsed.json                         # Parsed Excel mapping document
│   ├── intent_identification.json                  # Resolved intent per target table
│   ├── crypto_flags.json                           # Crypto column detection results
│   ├── source_table_metadata.json                  # Source table type classification (incl. volumetrics priority)
│   ├── dag_spec.json                              # DAG specification (schedule, deps, config per table — written by /gen-dag)
│   ├── source_column_allowlist.json                # Per-table source column constraints (anti-hallucination)
│   ├── generated_configs/                          # Filter manifests from /gen-config
│   │   └── {schema}_{table}_filters.json           # Declared filters, source columns, broadcast config
│   ├── placeholders.json                           # Placeholder resolution tracking
│   ├── audit_log.jsonl                             # Structured audit log (append-only)
│   ├── validation_results.json                     # Validator pass/fail results
│   ├── code_review_results.json                    # Code review findings
│   ├── intent_overrides.json                       # [Optional] User-supplied intent overrides
│   ├── intent_resolution_report.md                 # [Optional] G5 HALT failure analysis
│   ├── dv_session_state.json                       # [Stage 4] DV session tracking
│   ├── dv_validation_contract_{table}.json         # [Stage 4] Normalized validation contract per table
│   ├── dv_validation_plan_{table}.json             # [Stage 4] Dialect-neutral validation plan per table
│   ├── dv_execution_results_{table}.json           # [Stage 4] Parsed results from user Excel
│   ├── dv_validation_report.json                   # [Stage 4] Structured report
│   ├── dv_validation_report.md                     # [Stage 4] Human-readable report
│   └── .dv_manifest.json                           # [Stage 4] Output discovery manifest
│
└── generated/                                      # ALL generated artefacts (platform-separated)
    ├── glue/
    │   ├── mesh/
    │   │   └── {db}_{table}_mesh.json
    │   ├── transforms/
    │   │   ├── {db}_{table}_transform_day0.py
    │   │   ├── {db}_{table}_transform_day1.py
    │   │   └── generic_components/
    │   │       ├── __init__.py
    │   │       ├── reader.py
    │   │       ├── writer.py
    │   │       └── date_control.py
    │   ├── wrapper/
    │   │   ├── {db}_{table}_wrapper.py
    │   │   └── {db}_{table}_config.json
    │   ├── dtxog/
    │   │   └── {db}_{table}_dtxog.json
    │   ├── dags/
    │   │   └── {db}_{table}_dag.py                    # Airflow DAG (one per table)
    │   ├── tests/
    │   │   ├── conftest.py
    │   │   ├── pytest.ini
    │   │   └── unit/
    │   │       ├── test_wrapper_{db}_{table}.py
    │   │       ├── test_transform_{db}_{table}.py
    │   │       └── test_{dag_id}.py                    # DAG tests (if DAGs generated)
    │   └── validation/                                 # Stage 4: Data Validation SQL
    │       └── {db}_{table}/
    │           ├── {db}_{table}_validation.sql         # All checks, sectioned
    │           └── {db}_{table}_results_summary.sql    # 12-column result-shaping query
    │
    └── databricks/
        ├── databricks.yml                              # DABs bundle config (all targets + variables)
        ├── dags/
        │   └── {tenancy}_{table}_dag.py            # Airflow DAG (one per table)
        ├── jobs/
        │   └── {tenancy}_{dp}_jobs/
        │       ├── day0/
        │       │   └── {schema}_{table}_job.yml        # Per-table Day0 job definition
        │       ├── day1/
        │       │   └── {schema}_{table}_job.yml        # Per-table Day1 job definition
        │       ├── {schema}_table_creation_utility.yml  # Shared utility jobs (root level)
        │       ├── {schema}_date_control_insert_utility.yml
        │       ├── {schema}_daily_date_control_update_utility.yml
        │       └── {schema}_volume_creation_utility.yml # (conditional — if volumes needed)
        ├── src/
        │   └── Notebooks/
        │       ├── day0/
        │       │   └── {schema}_{table}/
        │       │       ├── {schema}_{table}_driver.py
        │       │       ├── {schema}_{table}_transform.py
        │       │       └── {schema}_{table}_config.yml
        │       ├── day1/
        │       │   └── {schema}_{table}/
        │       │       ├── {schema}_{table}_driver.py
        │       │       ├── {schema}_{table}_transform.py
        │       │       └── {schema}_{table}_config.yml
        │       └── utilities/
        │           ├── {schema}_table_creation_utility.py    # DDL embedded (all tables)
        │           ├── {schema}_date_control_insert_utility.py  # All table processes
        │           ├── {schema}_daily_date_control_update_utility.py
        │           └── {schema}_volume_creation_utility.py   # (conditional)
        ├── tests/
        │   ├── conftest.py
        │   ├── pytest.ini
        │   └── unit/
        │       ├── test_transform_{schema}_{table}.py
        │       ├── test_driver_{schema}_{table}.py
        │       └── test_{dag_id}.py                    # DAG tests (if DAGs generated)
        └── validation/                                 # Stage 4: Data Validation SQL
            └── {db}_{table}/
                ├── {db}_{table}_validation.sql         # All checks, sectioned
                └── {db}_{table}_results_summary.sql    # 12-column result-shaping query
```

**Conditional generation**: Transform files are generated based on each table's `load_type` — not every table produces both day0 and day1. Wrapper imports only the files that were actually generated.

**Platform separation**: Glue artefacts (mesh, wrapper, config.json, dtxog) are never mixed with Databricks artefacts (config.yml, driver, DDL, bundle, job YAMLs). Each platform has its own test folder.

### Multi-Source-System Output

When `source_system` is declared in Additional Context (Column K) and no explicit UNION is in the mapping, each source_system gets its own artifact set:

**Databricks** — `{source_system}` appears as a directory level:
```
generated/databricks/src/Notebooks/
├── day1/
│   ├── ilp/                                    # source_system directory
│   │   └── {schema}_{table}/
│   │       ├── {schema}_{table}_config.yml     # scoped to this source_system
│   │       ├── {schema}_{table}_transform.py
│   │       └── {schema}_{table}_driver.py
│   └── reference_data/                         # another source_system
│       └── {schema}_{table}/
│           └── ...
```

**Glue** — `_{source_system}` suffix in file names:
```
generated/glue/
├── wrapper/
│   ├── {db}_{table}_ilp_config.json            # scoped to source_system 'ilp'
│   ├── {db}_{table}_ilp_wrapper.py
│   ├── {db}_{table}_reference_data_config.json # scoped to source_system 'reference_data'
│   └── {db}_{table}_reference_data_wrapper.py
├── transforms/
│   ├── {db}_{table}_ilp_transform_day1.py
│   └── {db}_{table}_reference_data_transform_day1.py
├── dtxog/
│   ├── {db}_{table}_ilp_dtxog.json
│   └── {db}_{table}_reference_data_dtxog.json
└── dags/
    ├── {db}_{table}_ilp_dag.py
    └── {db}_{table}_reference_data_dag.py
```

Each per-source-system config uses **flat single-flow structure** — SourceReader sees standard `source.{table_type}.{alias}` layout. No runtime multi-flow detection needed.

---

## Plugin Architecture

For internal architecture details including the full plugin source structure, agent model tiering, skills breakdown, and design rationale, see [ARCHITECTURE.md](./ARCHITECTURE.md).

## Author

Samir Chaudhari — BUK Data Product Build Assistant
