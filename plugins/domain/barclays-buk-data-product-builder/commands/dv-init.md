---
description: Initialize a Data Validation session for a target mapping, setting engine and creating session state
disable-model-invocation: false
argument-hint: --engine athena|databricks [--excel <path>] [--domain-knowledge <path>] [--mapping-session <path>]
---

# /dv-init — Initialize Data Validation Session

Initialize a DV session by selecting the SQL engine (Athena or Databricks) and creating the DV session state file.

Supports **two modes**:

- **Dependent mode** (default) — Reads existing `mapping_parsed.json` and `intent_identification.json` produced by the DE code-generation pipeline (`/init` → `/parse-mapping` → `/identify-intent`).
- **Standalone mode** (`--excel`) — Parses the mapping Excel directly, runs intent identification via the `intent-identifier-agent`, and writes artifacts to `session/dv/` so the DE pipeline is never impacted.

## Usage

```
/dv-init --engine athena|databricks [--mapping-session <path>]
/dv-init --engine athena|databricks --excel <path> [--domain-knowledge <path>]
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--engine` | Yes | SQL dialect engine: `athena` or `databricks` |
| `--excel <path>` | No | Path to mapping Excel (.xlsx). Enables **standalone mode** — parses Excel, identifies intent, writes artifacts to `session/dv/`. Mutually exclusive with `--mapping-session`. |
| `--domain-knowledge <path>` | No | Path to domain knowledge markdown file. Standalone mode only — fed to `intent-identifier-agent` at Priority 2 for intent resolution. |
| `--mapping-session` | No | Path to mapping session directory (default: `session/`). Dependent mode only — points to directory containing `mapping_parsed.json` and `intent_identification.json`. Mutually exclusive with `--excel`. |

## Prerequisites

**Dependent mode:**
- `session/mapping_parsed.json` must exist (output of `/parse-mapping`)
- `session/intent_identification.json` must exist (output of `/identify-intent`)

**Standalone mode:**
- A valid mapping Excel file (.xlsx) with the required 16-column header structure

## Workflow

### Step 0 — RESOLVE PLUGIN ROOT

`${CLAUDE_PLUGIN_ROOT}` is automatically set by the plugin loader. Verify:
- `${CLAUDE_PLUGIN_ROOT}` exists and load plugin configuration

If missing, STOP with: "❌ Plugin root not resolved. Ensure barclays-buk-data-product-builder plugin is loaded."

### Step 1 — PARSE ARGUMENTS AND DETERMINE INPUT MODE

1. Parse `--engine`, `--excel`, `--domain-knowledge`, `--mapping-session` arguments.

2. **Mutual exclusivity check:**
   - If BOTH `--excel` AND `--mapping-session` are provided:
     ```
     ❌ --excel and --mapping-session are mutually exclusive. Use --excel for standalone mode or --mapping-session for dependent mode.
     ```
   - If `--domain-knowledge` is provided WITHOUT `--excel`:
     ```
     ❌ --domain-knowledge requires --excel (standalone mode). In dependent mode, domain knowledge is loaded by /init.
     ```

3. **Determine input mode:**
   - If `--excel` provided → `input_mode = "standalone_excel"` → proceed to **Step 2** (engine), then **Step 3** (standalone path)
   - Else → `input_mode = "de_pipeline"` → proceed to **Step 2** (engine), then **Step 7** (dependent path)

---

### Step 2 — READ ENGINE ARGUMENT

Parse `--engine` argument:
- `athena` → platform: `glue`, output under `generated/glue/validation/`
- `databricks` → platform: `databricks`, output under `generated/databricks/validation/`
- Missing or invalid → HALT: `❌ --engine is required. Valid values: athena, databricks`

Engine-to-platform mapping table:

| Engine | Platform | SQL Dialect | Output Directory | Table Naming |
|--------|----------|-------------|-----------------|--------------|
| `athena` | `glue` | Athena/Presto SQL | `generated/glue/validation/` | 2-part: `{{database}}.{{table}}` |
| `databricks` | `databricks` | Spark SQL | `generated/databricks/validation/` | 3-part: `{{catalog}}.{{schema}}.{{table}}` |

> **Note:** When engine is `databricks`, Unity Catalog names (source/target catalog) are resolved during `/dv-generate` using the `--env` argument (default: `dev`). No catalog information is needed at `/dv-init` time.

---

## Standalone Mode (Steps 3–6)

> These steps execute ONLY when `--excel` is provided.

### Step 3 — CREATE OUTPUT DIRECTORY

Create `session/dv/` directory if it does not exist. This is the **DV-exclusive** artifact directory — it is never read by DE pipeline commands.

If directory creation fails:
```
❌ Cannot create output directory session/dv/. Verify the session/ directory exists and is writable.
```

### Step 4 — PARSE MAPPING EXCEL (Standalone)

Parse the Excel file at `--excel <path>` following the column validation and row extraction rules defined in `${CLAUDE_PLUGIN_ROOT}/commands/parse-mapping.md`, with DV-specific scoping.

**Read `${CLAUDE_PLUGIN_ROOT}/commands/parse-mapping.md`** and follow these steps only:

| parse-mapping Step | Action |
|-------------------|--------|
| **STEP 1** — Column Header Validation | ✅ Execute: Validate the 12 required + 4 optional column headers. Reference `${CLAUDE_PLUGIN_ROOT}/configs/plugin.config.json` for the expected header list. |
| **STEP 2** — Row Extraction | ✅ Execute: Extract all data rows. Build per-row source references, target column mappings, null flags, transformation logic. |
| **STEP 2.5** — Multi-Table Detection | ✅ Execute: Detect multiple unique `(target_database, target_table)` pairs. |
| **STEP 2.8** — Enrichment Column Extraction | ✅ Execute: Extract `target_table_type` (column 14) and `key_column` (column 16) values. Apply PascalCase normalization to `target_table_type` per the mapping table in Step 2.8. |
| **STEP 3** — Table-Level Fields | ✅ Execute: Extract `table_description`, `additional_context` per table. |
| **STEP 3b** — Load Type Hint Extraction | ✅ Execute: Extract `load_type_hint` from Additional Context column if present. |
| **STEP 4** — Crypto Indicator Detection | ✅ Execute: Scan for crypto indicators (protegrity/tokenize/detokenize signals). Build crypto flags. |
| STEP 0, 0.0 — Logging/Compression | ❌ Skip: No DE session state for logging |
| STEP 2.1 — Domain Knowledge Auto-Discovery | ❌ Skip: DK provided via `--domain-knowledge` if needed |
| STEP 2.6, 2.6b — Data Flow / I/O Mode | ❌ Skip: DE-specific |
| STEP 2.7 — Infrastructure Resolution | ❌ Skip: DE-specific |
| STEP 2.9 — Join Predicate & Literal Extraction | ❌ Skip: Not needed for DV checks |
| STEP 4.5 — Source Volumetrics | ❌ Do NOT read the "Source Volumetrics" sheet. DV does not use volumetric data — skip entirely, do not open or parse this sheet. |
| STEP 5 — Post-Parse Validators | ❌ Skip: DE-specific consistency checks |
| STEP 6.1 — Session State Updates | ❌ Skip: No DE session state |

**Sheet handling rule (DV standalone):** Read ONLY the main mapping sheet (first/active sheet). Do NOT open or read the "Source Volumetrics" sheet even if it exists in the workbook. The DV pipeline does not consume volumetric data.

**Validation:**
- If Excel file not found or not `.xlsx`: HALT: `❌ Excel file not found at {path}. Provide a valid .xlsx file.`
- If required column headers missing: HALT with same error format as `/parse-mapping` Step 1.
- If zero data rows extracted: HALT: `❌ No data rows found in mapping Excel.`
- If zero target tables detected: HALT: `❌ No target tables detected in mapping.`
- If `target_table_type` is NULL for any table after extraction: HALT: `❌ Cannot determine table_type for {database}.{table}. Ensure the 'Target Table Type' column is populated in the mapping Excel.`

**Write outputs:**
- `session/dv/mapping_parsed.json` — conforms to `${CLAUDE_PLUGIN_ROOT}/schemas/mapping_excel.schema.json`
- `session/dv/crypto_flags.json` — crypto indicator flags per column

**BLOCKING verification:** After writing, read back `session/dv/mapping_parsed.json` and verify it is valid JSON with at least one table entry. Retry once on failure.

### Step 5 — INTENT IDENTIFICATION VIA AGENT (Standalone)

#### 5a — Pre-Agent Setup

1. If `--domain-knowledge` provided:
   - Read the file contents as text
   - If file unreadable: WARN: `⚠️ Domain knowledge file unreadable at {path} — continuing without it.` (non-blocking)
   - Store text for agent prompt below

#### 5b — Invoke Intent-Identifier Agent

Invoke the `intent-identifier-agent` via the **Agent tool** with the following prompt context. The agent follows the rules defined in `${CLAUDE_PLUGIN_ROOT}/agents/intent-identifier-agent.md`.

**Agent invocation prompt must include:**

```
You are the intent-identifier-agent. Follow the full specification in
${CLAUDE_PLUGIN_ROOT}/agents/intent-identifier-agent.md.

=== PATH OVERRIDES (critical — do NOT use session/ paths) ===
- Read mapping from: session/dv/mapping_parsed.json
- Read crypto flags from: session/dv/crypto_flags.json
- Write output to: session/dv/intent_identification.json
- Do NOT read or write session/session_state.json
- Do NOT check for session/source_table_metadata.json (standalone invocation)
- Do NOT check for session/intent_overrides.json (not used in DV standalone mode)

=== DOMAIN KNOWLEDGE ===
{If --domain-knowledge provided: include full text here as scoped_domain_knowledge}
{If not provided: "No domain knowledge available. Skip Priority 2 resolution."}

=== PRIORITY CHAIN ===
Apply the priority chain (skip Priority 0 — no intent overrides in DV standalone):
  Priority 0.5: mapping columns (target_table_type, key_column from mapping_parsed)
  Priority 1: transformation logic signals
  Priority 1.5: additional context / load_type_hint
  Priority 2: domain knowledge (if provided above)
  Priority 3: ask user via AskUserQuestion (G5-grain gate)

=== TARGET TABLES ===
Extract target tables from session/dv/mapping_parsed.json — process all unique
(target_database, target_table) combinations.
```

**Error handling:**
- If agent fails entirely: HALT:
  ```
  ❌ Intent identification failed. Check that the mapping Excel contains Target Table Type
  and/or Key Column columns, or structural signals (SCD2/transactional audit columns).
  ```
- If agent produces output that doesn't conform to `intent_identification.schema.json`: HALT with validation details.

### Step 6 — VERIFY OUTPUTS AND CREATE SESSION STATE

1. Verify `session/dv/mapping_parsed.json` exists and is valid JSON
2. Verify `session/dv/intent_identification.json` exists and is valid JSON array
3. Extract `target_tables[]` from `session/dv/mapping_parsed.json`
4. Extract per-table `table_type` and `primary_keys` from `session/dv/intent_identification.json`
5. Proceed to **Step 8** (Create Session State) with:
   - `source_session_path = "session/dv/"`
   - `input_mode = "standalone_excel"`

---

## Dependent Mode (Step 7)

> This step executes ONLY when `--excel` is NOT provided. This is the existing behavior.

### Step 7 — VERIFY PREREQUISITES (Dependent)

Resolve session directory from `--mapping-session` (default: `session/`).

Read and verify:
1. `{session_dir}/mapping_parsed.json` exists and is valid JSON
2. `{session_dir}/intent_identification.json` exists and is valid JSON
3. Extract `target_tables[]` from `mapping_parsed.json` — read ONLY per-table fields: `target_database`, `target_table`, `table_description`, `additional_context`, `load_type_hint`, `target_table_type`, `columns[]`. **Ignore `source_volumetrics`** — it is not used by DV and should not be loaded into context.
4. Extract per-table `table_type` and `primary_keys` from `intent_identification.json`

If either file is missing:
```
❌ Missing prerequisite: {file}. Run /parse-mapping and /identify-intent before /dv-init,
   or use --excel <path> to run in standalone mode.
```

Proceed to **Step 8** with:
- `source_session_path = "{session_dir}/"`
- `input_mode = "de_pipeline"`

---

## Common Steps (Both Modes)

### Step 8 — CREATE SESSION STATE

Create `session/dv_session_state.json` with:
```json
{
    "session_id": "dv_YYYYMMDD_HHMMSS",
    "created_at": "ISO 8601 timestamp",
    "engine": "athena|databricks",
    "input_mode": "de_pipeline|standalone_excel",
    "source_session_path": "session/|session/dv/",
    "source_excel_path": "<path or null>",
    "domain_knowledge_path": "<path or null>",
    "phases": {
        "dv_init": {"status": "completed", "started_at": "...", "completed_at": "..."},
        "dv_generate": {"status": "pending"},
        "dv_report": {"status": "pending"}
    },
    "tables": [
        {
            "target_database": "...",
            "target_table": "...",
            "table_type": "...",
            "contract_path": null,
            "plan_path": null,
            "sql_directory": null,
            "check_count": 0,
            "not_evaluated_count": 0
        }
    ],
    "generated_files": [],
    "report_path": null
}
```

Field values by mode:

| Field | Dependent mode | Standalone mode |
|-------|---------------|-----------------|
| `input_mode` | `"de_pipeline"` | `"standalone_excel"` |
| `source_session_path` | `"session/"` (or `--mapping-session` value) | `"session/dv/"` |
| `source_excel_path` | `null` | `--excel` path |
| `domain_knowledge_path` | `null` | `--domain-knowledge` path or `null` |

### Step 9 — REPORT STATUS

**Dependent mode:**
```
✅ DV session initialized
   Session ID: dv_20260926_143022
   Engine:     athena (Glue platform)
   Tables:     3 (mortgage_account, customer_profile, payment_history)
   
   Next step: /dv-generate
```

**Standalone mode:**
```
✅ DV session initialized (standalone from Excel)
   Session ID: dv_20260926_143022
   Engine:     athena (Glue platform)
   Excel:      Mortgage_Mapping.xlsx
   Tables:     3 (mortgage_account, customer_profile, payment_history)
   Artifacts:  session/dv/

   Next step: /dv-generate
```

## Output

- `session/dv_session_state.json` (both modes)
- `session/dv/mapping_parsed.json` (standalone mode only)
- `session/dv/crypto_flags.json` (standalone mode only)
- `session/dv/intent_identification.json` (standalone mode only)

## Important Rules

- Engine argument is MANDATORY — no default engine
- `--excel` and `--mapping-session` are MUTUALLY EXCLUSIVE
- `--domain-knowledge` requires `--excel` (standalone mode only)
- Standalone mode writes to `session/dv/` — NEVER to `session/mapping_parsed.json` or `session/intent_identification.json`
- DE pipeline artifacts in `session/` are NEVER read or modified in standalone mode
- Session state follows same pattern as `sttm_session_state.json`
- Table types are normalized to PascalCase in the session state
- NEVER infer `table_type` or engine from filenames or external context

## Anti-Hallucination Rules

- NEVER infer, guess, or display **Data Product Type** (FDP/CDP/BDP) during `/dv-init`. This includes shared-prefix databases (`shared_fdp_*`, `shared_cdp_*`, `shared_bdp_*`) — while these resolve to their parent DP type (FDP/CDP/BDP) during `/parse-mapping`, they are NOT inferred during `/dv-init`.
- The Excel filename is NOT a valid source for inferring table_type, domain, or any routing field.
- In standalone mode, `table_type` MUST come from one of: mapping Excel `Target Table Type` column (Priority 0.5), transformation logic signals (Priority 1), additional context (Priority 1.5), domain knowledge (Priority 2), or explicit user answer (Priority 3). No other source.
