---
description: Parse and validate mapping Excel columns — invoke after init completes
disable-model-invocation: false
---

# /parse-mapping

Parse and validate the mapping Excel file. Validates 12 required + 4 optional column headers, splits multi-value cells, detects structured transformation logic, scans for crypto indicators, extracts source volumetrics (if sheet present), and produces `mapping_parsed.json`, `crypto_flags.json`, and optionally `source_volumetrics.json`.

## Usage

```
/parse-mapping
```

(Uses `mapping_excel_path` from current session state — set by `/init`.)

## Prerequisites

- Session initialised (`/init` completed)
- Gate G1 resolved (platform selected, either via `/init --platform` or G1 gate question)

## STEP 0.0 — Chain Mode Output Compression

If `session_state.auto_chain.enabled == true` (full-automation mode):
- **Suppress verbose output:** Do NOT print session_state.json content, per-column parse progress, or per-table discovery messages to conversation.
- **Audit log instead:** Write verbose progress entries to `session/audit_log.jsonl` (append-only structured logging).
- **Compact return only:** At command completion, emit ONLY:
  ```
  [1/{total}] ✓ /parse-mapping — {N} target tables, {M} source tables, crypto: {yes|no}
  Checkpoint: post_parse written
  ```
- **Halt output:** If BLOCKING error, emit max 5-line halt summary. Full details written to `session/audit_log.jsonl`.

---

## STEP 0 — Logging Initialization

Apply `conventions` skill logging pattern, component="de-parse-mapping".

---

## Auto-Resolution During Parse

**Gate G1.5 (Data Product Type) is resolved automatically during this step** — no user interaction required.

The DP type is derived from the target database prefix:
- `fdp_*` or `shared_fdp_*` → FDP (source layer: BASE, account: DDA)
- `cdp_*` or `shared_cdp_*` → CDP (source layer: FDP/CDP, account: DDA)
- `bdp_*` or `shared_bdp_*` → BDP (source layer: FDP/CDP, account: BCA)

Shared-prefix databases (`shared_fdp_*`, `shared_cdp_*`, `shared_bdp_*`) resolve to the SAME parent DP type as their non-shared counterparts. The `shared_` prefix indicates a cross-team shared data product but does NOT change routing, layer, or account classification.

If all tables resolve to the same parent DP type: Auto-resolve G1.5 and mark as "RESOLVED" (e.g., `fdp_*` and `shared_fdp_*` together is valid — both are FDP)  
If tables resolve to MIXED parent DP types (e.g., `fdp_*` and `cdp_*`, or `shared_fdp_*` and `bdp_*`): **ERROR** — cannot mix DP types in one session  
If prefix is invalid (e.g., `stg_`, `tmp_`, `e_`, `shared_stg_*`): **ERROR** — require user to fix mapping Excel

## Behaviour — Step by Step

### STEP 1 — Excel Column Validation (HALT on failure)

Invoke `excel-schema-validator`. Check all 16 required column headers are present (case-insensitive + semantic variant matching):

**Required Headers (HALT if missing):**

| # | Canonical Header | Semantic Variants (examples) |
|---|---|---|
| 1 | `Target Database` | `target db`, `target_database` |
| 2 | `Target Table` | — |
| 3 | `Target Column Name` | — |
| 4 | `Target Column Definition/Description` | `target column desc`, `target_column_definition`, `target_column_description` |
| 5 | `Target Column Datatype` | — |
| 6 | `Target Column Null Flag` | — |
| 7 | `Source database/Source DB` | `source db`, `source_database`, `source database`, `source_db` |
| 8 | `Source Table Name` | — |
| 9 | `Source Column Name` | — |
| 10 | `Business Logic/Transformation Logic` | `business logic`, `transformation`, `transformation_logic`, `transform logic` |
| 11 | `Additional Context` | — |
| 12 | `Target Table description` | `target table desc`, `table_description`, `table description` |
| 13 | `Transformation Type` | `transformation_type`, `transform type` |
| 14 | `Default Value` | `default_value`, `default` |
| 15 | `Target Table Type` | `target_table_type`, `table type`, `target table type` |
| 16 | `Key Column` | `key_column`, `key col`, `primary key`, `pk` |

**Source Database special values:** Column 7 (`Source database/Source DB`) accepts standard database names as well as reserved tokens: `(system)`, `(derived)`, `(file:parquet)`. These tokens are NOT validated as real database names — they signal special source types handled in STEP 2.

**Target Table Name special values:** Column 2 (`Target Table`) may include a `(file:parquet)` suffix (e.g., `customer_events_clean (file:parquet)`) to signal that the target output is a parquet file rather than a database table. The suffix is stripped during STEP 2 row extraction; downstream consumers see only the clean table name.

**Validation logic:**
- Normalize all column headers to lowercase + underscore-to-space for matching
- For each canonical header (required), attempt match in this order:
  1. Exact lowercase match to canonical
  2. Semantic variant match (using table above)
- **Store canonical names** in parsed output (not user input) for consistent downstream processing
- Preserve original header text in audit log for traceability
- If any REQUIRED header missing after semantic matching: **HALT** and list all missing canonical names with their accepted variants

### STEP 2 — Row Extraction

For each data row (skipping header):
- Extract all 12 field values
- `Target Column Null Flag` → convert to boolean (Y/Yes/TRUE/1 = nullable; N/No/FALSE/0 = NOT NULL)
- `Source database/Source DB`, `Source Table Name`, `Source Column Name` → split on `,`, `;`, or newline → assemble into `source_references[]` using cascading qualification rules:
  - Single DB + Single Table: broadcast DB and table to all columns (no qualification needed)
  - Single DB + Multiple Tables: columns must be qualified as `table.column`
  - Multiple DBs: tables must be `db.table`, columns must be `db.table.column`
  - HALT if multi-source entries are not fully qualified (never infer by position)
- **File source handling** — when `source_database` = `(file:parquet)`:
  - `source_table` contains the **absolute storage path** (e.g., `s3://raw-bucket/data/customer_events/` for Glue, `/Volumes/catalog/schema/volume/customer_events/` for Databricks)
  - Derive `logical_name` from the path **basename** — the last non-empty segment after stripping any trailing `/` (e.g., `s3://raw-bucket/data/customer_events/` → `customer_events`)
  - Cascading qualification uses **2-part FQN** for file source columns: `{logical_name}.{column}` (not 3-part)
  - Each `source_references[]` entry from a file source includes `io_type: "file"` (table sources use `io_type: "table"`)
  - Populate `session_state.source_io` with detected file sources: `[{logical_name: "<basename>", storage_path: "<full path from Column H>", format: "parquet"}]`
  - Set `session_state.file_source_detected = true`
- **File target handling** — when `target_table` contains `(file:parquet)`:
  - Strip the `(file:parquet)` suffix (case-insensitive, optional surrounding whitespace) → the remaining text is the clean `target_table` (logical name for the file target)
  - Store the clean value back as `target_table` in the parsed row — all downstream consumers (file naming, validators, config generation) see only the stripped name
  - Auto-populate `session_state.target_io`: `{logical_name: "<stripped name>", format: "parquet"}`
  - Set `session_state.file_target_detected = true`

### STEP 2.1 — Domain Knowledge Auto-Discovery (G0.5)

If `session_state.domain_knowledge_path` is already set (user provided `--domain-knowledge` in `/init`): **SKIP this step**.

Otherwise, auto-discover using the appropriate tenancy skill based on platform:

1. Extract `target_database` from the first data row's `Target Database` column
2. **Normalize before comparison**: strip leading/trailing whitespace, convert to lowercase
3. **Look up normalized `target_database` — branched by platform**:

   **If platform = Glue** → use `barclays-buk-data-product-builder:aws-tenancy` skill (AWS Tenancy Registry):
   - Match (case-insensitive, whitespace-trimmed) against the **Hive Database** column OR the **Iceberg Database** column
   - If match found: extract the **Feature Team Name** from the matched row (e.g., `fdpchnlcc`)

   **If platform = Databricks** → use `barclays-buk-data-product-builder:databricks-tenancy` skill (Tenancy Infrastructure Registry):
   - Match (case-insensitive, whitespace-trimmed) against the **Target DB** column
   - If match found: extract the **Feature Team Name** from the matched row (e.g., `BUK_PAFER_BDP`)

4. Construct expected filename: `{feature_team_name}_knowledge.md` (e.g., `fdpchnlcc_knowledge.md` or `buk_pafer_bdp_knowledge.md`)
5. Search in `${CLAUDE_PLUGIN_ROOT}/configs/domain_knowledge/` (plugin installation directory, NOT project directory)
6. If found:
   - Read file header (first 10 lines) and extract `**Tenancy**: \`{marker}\``
   - If marker is present AND marker != feature_team_name → HALT: "Domain knowledge file tenancy marker (`{marker}`) does not match resolved feature team (`{feature_team_name}`). File may be misnamed or registry corrupted."
   - If marker matches OR no marker present → proceed: load file content into `session_state.domain_knowledge_text` and set `session_state.domain_knowledge_path`; set `session_state.domain_knowledge_validated_tenancy = {marker}` (or null if no marker); log INFO: "Domain knowledge auto-discovered: {filename}"
   - **Size guard**: If loaded file size > 30KB → log WARNING to `session/audit_log.jsonl`: `"Domain knowledge file exceeds 30KB ({size}KB). Consider restructuring into smaller feature-team-specific files to reduce context pressure."` Continue loading — this is a WARNING, not a HALT.
7. If `target_database` not found in skill registry: log WARNING: "Target database '{db}' not found in tenancy registry — cannot auto-discover domain knowledge"; continue without (non-blocking)
8. If found in registry but file does not exist: log INFO: "No domain knowledge file found for feature team '{feature_team_name}'"; continue without (non-blocking)

**Auto-Discovery Examples (Glue):**

| Target Database | Skill | Match Column | Feature Team Name | Auto-Discovered File |
|---|---|---|---|---|
| `fdp_uk_mortgage_db` | tenancy | Hive Database | `fdpmortgage` | `fdpmortgage_knowledge.md` |
| `fdp_uk_mortgage_db_iceberg` | tenancy | Iceberg Database | `fdpmortgage` | `fdpmortgage_knowledge.md` |
| `fdp_uk_cntct_centr_chnl_db` | tenancy | Hive Database | `fdpchnlcc` | `fdpchnlcc_knowledge.md` |
| `fdp_uk_cntct_centr_chnl_db_icbg` | tenancy | Iceberg Database | `fdpchnlcc` | `fdpchnlcc_knowledge.md` |

**Auto-Discovery Examples (Databricks):**

| Target Database | Skill | Match Column | Feature Team Name | Auto-Discovered File |
|---|---|---|---|---|
| `bdp_uk_bbcdd_db_dbxw` | databricks-tenancy | Target DB | `BUK_BBKYC_BDP` | `buk_bbkyc_bdp_knowledge.md` |
| `bdp_uk_pafer_db` | databricks-tenancy | Target DB | `BUK_PAFER_BDP` | `buk_pafer_bdp_knowledge.md` |
| `BDP_UK_INSURANCE_AND_PACKS_DB_DBX` | databricks-tenancy | Target DB | `BUK_INSURANCE_BDP` | `buk_insurance_bdp_knowledge.md` |

**Why SKILL.md lookup instead of string parsing?** Database names like `fdp_uk_cntct_centr_chnl_db_icbg` cannot be reliably converted to tenancy shortname `fdpchnlcc` via string manipulation. The SKILL.md registry is the single source of truth for database-to-tenancy mapping.

Mark G0.5 as resolved in `gates_resolved[]`.

### STEP 2.5 — [NEW] Multi-Table Detection

Scan all extracted rows to identify unique target tables:
- For each unique `(Target Database, Target Table)` combination:
  - Count rows mapping to this table
  - Store in session_state.target_tables[] with: {target_database, target_table, intent_resolved: false, row_count_in_mapping}

Set session_state.total_target_tables = count of unique tables
Set session_state.pending_intent_tables = array of all unique tables (in "database.table" format)

**Log INFO**: "Mapping contains {N} unique target table(s): {list}"

**Example**:
```
Mapping 1 table:
  total_target_tables: 1
  target_tables: [{target_database: "fdp_uk_complaints_db", target_table: "complaints", intent_resolved: false, row_count_in_mapping: 342}]
  pending_intent_tables: ["fdp_uk_complaints_db.complaints"]

Mapping 2 tables:
  total_target_tables: 2
  target_tables: [
    {target_database: "fdp_uk_complaints_db", target_table: "complaints", intent_resolved: false, row_count_in_mapping: 342},
    {target_database: "fdp_uk_complaints_db", target_table: "complaint_activity", intent_resolved: false, row_count_in_mapping: 1245}
  ]
  pending_intent_tables: ["fdp_uk_complaints_db.complaints", "fdp_uk_complaints_db.complaint_activity"]
```

### STEP 2.6 — Data Flow Mode Detection

After target table identification (STEP 2.5), detect whether the mapping indicates multiple independent data flows feeding a single target table.

**Algorithm:**
1. Group all parsed column_mappings by `(target_database, target_table, target_column_name)`
2. For each group with row count > 1 (same target column appears in multiple mapping rows):
   - This indicates multiple independent data flows populating the same target column
   - Flag this target table as **multiple data flow candidate**
   - The duplicate rows may originate from different source databases OR the same source database — both patterns indicate multiple data flows feeding a single target
3. Also check: for columns with multiple `source_references[]` entries in a SINGLE row that represent distinct independent flows (not a join) → same signal

**Key distinction**: Multiple data flow ≠ multi-table join. A join combines sources within ONE flow to produce ONE target row. Multiple data flows means the same target table/column is populated by SEPARATE independent pipelines (same or different source DBs). The signal is structural: the same `(target_table, target_column)` tuple appearing in multiple mapping rows.

**Session state write:**
- `session_state.data_flow_detection.mapping_signal` = `true` | `false`
- `session_state.data_flow_detection.mapping_evidence[]` = affected tables with duplicate column details
- `session_state.data_flow_detection.detection_signals.mapping_signal` = `true` | `false`

**Example evidence entries:**
```json
[
  {
    "target_table": "complaints",
    "duplicate_columns": ["complaint_id", "customer_name"],
    "source_flows": [
      {"source_database": "e_cms_db", "source_table": "cms_complaints"},
      {"source_database": "e_crm_db", "source_table": "crm_cases"}
    ]
  },
  {
    "target_table": "transactions",
    "duplicate_columns": ["txn_id", "amount"],
    "source_flows": [
      {"source_database": "e_payments_db", "source_table": "card_txns"},
      {"source_database": "e_payments_db", "source_table": "wire_txns"}
    ]
  }
]
```

Note: The second example shows multiple data flows from the **same** source database — this is still a valid multiple-data-flow scenario (two independent pipelines converging on one target).

**Logging:**
- If detected: `[ADVISORY] Multiple data flow detected from mapping structure for {target_table}: {N} flows identified from duplicate target columns`
- This is NON-BLOCKING — config generation (STEP 0.5) will confirm and select the appropriate template using the 3-way priority resolution.

**No detection (default):**
- `session_state.data_flow_detection.mapping_signal = false`
- `session_state.data_flow_detection.mapping_evidence = []`

### STEP 2.6b — I/O Mode Detection

After source reference assembly, classify the I/O mode based on source and target file indicators:

**Source-side**: `source_database` values across all parsed rows (`(file:parquet)` = file source).
**Target-side**: `session_state.file_target_detected` flag (set in STEP 2 when `target_table` contained `(file:parquet)`).

| Source files? | Target file? | `io_mode` |
|---|---|---|
| ALL sources are file | Yes | `"file"` |
| ALL sources are file | No | `"hybrid"` |
| SOME sources are file | Yes or No | `"hybrid"` |
| NO sources are file | Yes | `"hybrid"` |
| NO sources are file | No | `"table"` (default) |

**Log INFO**: "I/O mode detected: {io_mode}" (only logged when io_mode is not `"table"`)

This classification is consumed by downstream agents (export, config generation) to determine whether file I/O metadata is included in generated artefacts.

### STEP 2.7 — Per-Environment Infrastructure Resolution

Resolve ALL per-environment infrastructure values **once** for all downstream agents. Platform-conditional: Glue resolves S3 buckets + AWS infra; Databricks resolves catalogs + workspace infra.

**Algorithm (shared preamble):**
1. Parse `target_database` → extract DP type (fdp/cdp/bdp, including shared variants shared_fdp/shared_cdp/shared_bdp) + domain
2. Look up `target_database` (normalized: case-insensitive, whitespace-trimmed) against the platform tenancy registry:

**If platform = Glue** — resolve via `tenancy-summary` (Glue / AWS Tenancies table):
   a. Match against the **Iceberg Database** column → **Iceberg (Pattern 1)**; or **Hive Database** column → **Hive (Pattern 2)**. Skip cells marked "Not available".
   b. If match found → extract `bucket_shortname`, `tenancy_name` from matched row. Continue to step 3 below.
   c. If no match → invoke **Interactive Infrastructure Collection** (see below).

**If platform = Databricks** — resolve via `barclays-buk-data-product-builder:databricks-tenancy` skill (Tenancy Infrastructure Registry):
   a. Match against the **Target DB** column using **EXACT case-insensitive equality only**: for each row in the registry, skip rows where Target DB is "—", empty, or null; compare `row["Target DB"].lower() == target_database.lower()`. First match wins. Do NOT use fuzzy, partial, substring, similarity, or closest-match heuristics — if no row matches exactly, proceed to step (d) (no match).
   b. If match found → extract `tenancy_name` (Feature Team Name) from matched row. For EACH environment (dev, preprd, prd, optional uat):
      - Read **Write/Target Catalog** column value for that env row
      - If value is a real catalog name (not `TBD`, not `NA`, not empty) → store in `session_state.dbx_config.{env}.target_catalog`
      - If value is `TBD` or `NA` → store null; infrastructure questionnaire Q3 will ask for just the missing env(s)
      - Also extract per-env: `workspace_folder`, `cicd_sp`, `exec_sp`, `ad_group`, `app_service_tag`, `fin_role_tag` from the matched tenancy rows
   c. If any `target_catalog` env values are null after skill lookup → invoke **Partial Infrastructure Collection**: present only Q3 (Target Catalogs) from `infrastructure-questionnaire-databricks.md`, pre-filled with resolved envs, asking only for missing env(s).
   d. If no match at all → **BLOCKING**: invoke **Interactive Infrastructure Collection** (see below). Do NOT proceed to step (e) or (f) until the questionnaire has completed and `session_state.dbx_config` is populated with user-provided values. The Interactive Infrastructure Collection flow for Databricks follows the batched Turn 1–5 flow from `infrastructure-questionnaire-databricks.md`.
   e. Auto-derive fixed constants: `source_catalog` per env (DEV/UAT: `077382350852_buk_data_products`; PREPRD/PRD: `buk_data_product_central_catalog`), `workspace_host` per env (DEV: `https://dev-buk-uk.cloud.databricks.com/`; UAT: `https://dev-buk-uk.cloud.databricks.com/`; PREPRD: `https://prod-buk-parallel-uk.cloud.databricks.com/`; PRD: `https://prod-buk-prod-uk.cloud.databricks.com`), `policy_id` per env (DEV: `00186E9BB6908351`; PREPRD: `000CB013172B29C7`; PRD: `000A02890D1F23ED`).
   f. Store all values in `session_state.dbx_config` (same schema as `session_state.schema.json` `dbx_config`).
   g. **POST-RESOLUTION ASSERTION (NON-NEGOTIABLE)**: After completing steps (a)–(f), verify:
      - `session_state.dbx_config` is non-null
      - `session_state.dbx_config.tenancy_name` is set (from either registry lookup in step (b) or user input from Interactive Infrastructure Collection in step (d))
      - If tenancy was resolved via Interactive Infrastructure Collection (step d):
        `session_state.dbx_config.questionnaire_turns_completed == 5` AND
        `session_state.dbx_config.dev.target_catalog` is non-null
      If any check fails → **HALT**: `"STEP 2.7 Databricks infrastructure questionnaire incomplete — questionnaire_turns_completed={N}, expected 5. Re-run /parse-mapping."` This assertion guards against both silent fallthrough and partial questionnaire completion (e.g., only Turn 1 completed).

**Interactive Infrastructure Collection** (fallback — tenancy not found in either platform):
   1. Log WARNING: `"Target database '{target_database}' not found in tenancy registry. Initiating interactive infrastructure collection."`
   2. IF `session_state.domain_knowledge_text` is non-null: Check domain knowledge for explicit infrastructure overrides. If ALL required values present → use them, skip questions. IF null/empty: Skip — proceed directly to step 3.
   3. Auto-derive fixed/constant values: DP type (from prefix), account_type (DDA/BCA), AWS account IDs (from aws-data-products skill), crypto API endpoints (from service-management skill).
   4. **INTERACTIVE**: Present questions and wait for user response per turn.
      - For Databricks: Follow batched Turn 1–5 from `infrastructure-questionnaire-databricks.md`
      - For Glue: Follow sequential Q1–Q2 + Q3g–Q6g from `infrastructure-questionnaire-glue.md`
   5. For each question (or batched turn):
      a. IF `session_state.domain_knowledge_text` is non-null: Check domain knowledge — if value found, skip question silently
      b. Present question(s), wait for response
      c. If any per-env field is left blank within a turn, present a follow-up sub-question for ONLY the missing environment(s) per the Per-Environment Partial Answer Rules
      d. Store in `dbx_config` (Databricks) or `env_config` (Glue)
   6. Derive S3 buckets (Glue) from user-provided `bucket_shortname` + known account IDs + `catalog_type`. For any skipped non-blocking value → store null, retain `{{placeholder}}`.
   7. Present **Confirmation Summary** with all collected/derived values — **WAIT for user to confirm** before proceeding. If user says no → re-present all questions.
   9. Store all values in `session_state.env_config` (Glue) or `session_state.dbx_config` (Databricks) using the same schema as registry-resolved values.
   10. Set `session_state.tenancy_resolution_method = "user_provided"`.
   11. Continue to step 3 below.

**Post-resolution (both platforms):**
3. From the matched tenancy row OR from user-provided values → extract `bucket_shortname` (Glue), `tenancy_name`
4. Determine account type: FDP/CDP → DDA; BDP → BCA
5. **Check domain knowledge for overrides FIRST** — if `s3_bucket_dev`, `itsi_prd`, etc. explicitly provided, use those
6. **For EACH environment (dev, uat, prd)** — derive from skills (Glue-specific):
   - **S3 bucket**: Look up account_id (aws skill, DDA/BCA row, env column) + env_prefix (Iceberg: dev1/uat1/prd1; Hive: dev/uat/prd) → build bucket name using Pattern 1 or 2
   - **AWS account ID**: From aws skill account table (DDA or BCA row, env column)
   - **ITSI**: From ops skill tenancy ITSI table (tenancy × env)
   - **Compid**: From ops skill (prd only; null for dev/uat)
   - **Crypto account ID**: Same as AWS account ID (Pattern 4 uses same account)
   - **Crypto ITSI**: From ops skill (same tenancy ITSI or crypto-specific if documented)
   - **Crypto API endpoint**: From ops skill (Crypto API Endpoints table — per env)
7. Store in `session_state.env_config` (Glue) or `session_state.dbx_config` (Databricks) — centralized, all envs, all values
8. Auto-populate `session_state.mesh_json_s3_locations` from `env_config` (Glue only — marks G3 as RESOLVED)
9. **POST-RESOLUTION ASSERTION — Glue (NON-NEGOTIABLE)**: If platform = Glue, verify:
   - `session_state.env_config` is non-null
   - `session_state.env_config.tenancy_name` is set
   - If tenancy was resolved via Interactive Infrastructure Collection:
     `session_state.env_config.questionnaire_turns_completed == 6` AND
     `session_state.env_config.dev.s3_bucket` is non-null
   If any check fails → **HALT**: `"STEP 2.7 Glue infrastructure questionnaire incomplete — questionnaire_turns_completed={N}, expected 6. Re-run /parse-mapping."` This assertion mirrors the Databricks assertion in step (g) above and guards against partial questionnaire completion.

**Output**: Store in `session_state.env_config`:
```json
{
  "tenancy_name": "fdpmortgage",
  "catalog_type": "iceberg",
  "bucket_shortname": "fdpmortgage01",
  "account_type": "DDA",
  "dev": {
    "s3_bucket": "dev1-pre-fdpmortgage01-767397940910-eu-west-1",
    "aws_account_id": "767397940910",
    "itsi": "SNSVC0012345",
    "compid": null,
    "crypto_account_id": "767397940910",
    "crypto_itsi": "SNSVC0012345",
    "crypto_api_endpoint_url": "https://rvv79qtyhc.execute-api.eu-west-1.amazonaws.com/development/v1"
  },
  "uat": {
    "s3_bucket": "uat1-pre-fdpmortgage01-590184123059-eu-west-1",
    "aws_account_id": "590184123059",
    "itsi": "SNSVC0012346",
    "compid": null,
    "crypto_account_id": "590184123059",
    "crypto_itsi": "SNSVC0012346",
    "crypto_api_endpoint_url": "https://b3sdxfbp85.execute-api.eu-west-1.amazonaws.com/qa/v1"
  },
  "prd": {
    "s3_bucket": "prd1-pre-fdpmortgage01-194722397519-eu-west-1",
    "aws_account_id": "194722397519",
    "itsi": "SNSVC0012347",
    "compid": "COMPID_MORTGAGE",
    "crypto_account_id": "194722397519",
    "crypto_itsi": "SNSVC0012347",
    "crypto_api_endpoint_url": "https://l3s21rqu32.execute-api.eu-west-1.amazonaws.com/production/v1"
  }
}
```

Also auto-populates `session_state.mesh_json_s3_locations`:
```json
{
  "dev": { "bucket": "dev1-pre-fdpmortgage01-767397940910-eu-west-1", "prefix": "data" },
  "uat": { "bucket": "uat1-pre-fdpmortgage01-590184123059-eu-west-1", "prefix": "data" },
  "prd": { "bucket": "prd1-pre-fdpmortgage01-194722397519-eu-west-1", "prefix": "data" }
}
```

**Log INFO**: "Per-environment infrastructure resolved for {tenancy_name}: dev={s3_bucket_dev}, uat={s3_bucket_uat}, prd={s3_bucket_prd}"

**Fallback handling**: If tenancy not found in tenancy skill → invoke interactive infrastructure collection per `prompts/infrastructure-questionnaire-glue.md` (Glue) or `prompts/infrastructure-questionnaire-databricks.md` (Databricks). The system asks the user for all required infrastructure values interactively, waits for responses, and presents a confirmation summary. System only HALTs if user cannot provide `tenancy_name` AND `bucket_shortname` (Glue) / core Databricks values after one re-prompt. See the platform-specific questionnaire for full question flow, sample values, and partial answer handling.

### STEP 2.8 — Enrichment Column Extraction & Structured Logic Detection

**Per-row extraction (columns 13–16):**

- **`Transformation Type`**: Extract and validate against enum (`Direct`, `Derived`, `Lookup`, `Direct - Type Cast`). Case-insensitive normalization. Invalid → `null`.
- **`Default Value`**: Extract raw value preserving type (numeric stays numeric, text stays text). Empty → `null`.
- **`Key Column`**: Convert Y/N to boolean (same logic as Null Flag). Y/Yes/TRUE/1 → `true`. N/No/FALSE/0 → `false`. Empty → `null`.
- **`Target Table Type`**: Extract from FIRST NON-EMPTY cell only (table-level, like `additional_context`). Normalize to CamelCase canonical values: `scd2`/`SCD2` → `"NonTransactional_SCD2"`, `scd1`/`SCD1` → `"NonTransactional_SCD1"`, `transactional`/`Transactional`/`append` → `"Transactional"`.

**Table Type Normalization (all inputs normalize to CamelCase canonical value):**

| User Input (case-insensitive) | Normalized Value |
|---|---|
| `scd2`, `SCD2`, `non-transactional`, `Non-Transactional`, `nontransactional`, `NonTransactional_SCD2` | `"NonTransactional_SCD2"` |
| `scd1`, `SCD1`, `NonTransactional_SCD1` | `"NonTransactional_SCD1"` |
| `transactional`, `Transactional`, `append`, `Transactional` | `"Transactional"` |

**Legacy compatibility:** If mapping contains literal `Non-Transactional` (without SCD qualifier), normalize to `"NonTransactional_SCD2"` (preserves backward compatibility with existing mappings that predate SCD1 support).

The **Normalized Value** (`"NonTransactional_SCD2"`, `"NonTransactional_SCD1"`, `"Transactional"`) is stored directly in `mapping_parsed.json` and used by all downstream agents (config generation, DTXOG, mesh JSON, intent identification) without further translation.

**Structured Transformation Logic Detection:**

For each row's `Business Logic/Transformation Logic` cell value:
1. Check if value contains `Driver Table` (case-insensitive trigger)
2. If detected → parse structured format using regex patterns:
   - `Driver Table:\s*(.+)` → driver_table
   - `Driver Conditions:\s*\[(.+?)\]` → driver_conditions (split on numbered items, same syntax as TableN Conditions)
   - `Join N Table:\s*(.+)` → joins[].table
   - `TableN Conditions:\s*\[(.+?)\]` → joins[].table_conditions (split on numbered items)
   - `Join N Type:\s*(.+)` → joins[].join_type (normalize to uppercase)
   - `Join N Conditions:\s*(.+)` → joins[].join_conditions
   - `Value:\s*(.+)` → value_expression
3. Assemble into `structured_transformation` object per column (including `driver_conditions` array — empty `[]` if not specified)
4. If parsing incomplete → log WARNING, fallback to free-text (`structured_transformation = null`)
5. Store BOTH `transformation_logic` (raw) and `structured_transformation` (parsed)
6. Set `session_state.structured_logic_detected = true` if any row uses structured format

**Note on filters**: When using structured format, `Driver Conditions` and `TableN Conditions` fields provide explicit filter/subset logic. When using natural language, filter descriptions in the transformation logic text are interpreted by the transform generator (Rule 11). Structured format filters are deterministic; NL filter interpretation is best-effort with advisory comments.

**Multi-Source Join Logic Detection (Advisory):**

After source reference assembly (STEP 2c), for each column where `source_references` contains MORE than one distinct table:
1. Check if `structured_transformation` was successfully parsed for that row
2. If NOT (i.e., `structured_transformation = null` despite multiple source tables):
   - Emit ADVISORY: `"Column '{target_column_name}' references {N} source tables ({table_list}) — no structured format detected. Transform generator will use NL interpretation (Rule 11) for join/filter logic. For deterministic output, structured Driver Table format is recommended."`
   - Add to `session_state.parse_warnings[]` (severity: "advisory")
   - Mark column with `join_logic_missing = true` in `mapping_parsed.json`
3. During `/identify-intent`, columns with `join_logic_missing = true` trigger an advisory message (non-blocking) recommending structured format
4. Transform generation proceeds using NL interpretation mode (Rule 11) — joins, filters, and expressions are interpreted from the free-text `transformation_logic` with advisory comments in generated code

### STEP 2.9 — Join Predicate & Literal Value Extraction (Free-Text Path)

> **CONDITIONAL**: Only executes for columns where `structured_transformation` is null AND `transformation_logic` is non-null and non-empty. Columns using structured Driver Table format already have deterministic join/filter handling — this step provides equivalent determinism for the free-text path.

**Purpose**: Extract join predicates and literal values verbatim from free-text `transformation_logic` using regex patterns. These become LOCKED constraints that the transform-generator-agent MUST reproduce exactly — preventing LLM inference of symmetric join keys or semantic value substitution.

**Per-qualifying-column extraction:**

#### A. Join Predicate Extraction (regex-first)

Apply pattern: `(\w+)\.(\w+)\s*(=|!=|<|>|<=|>=)\s*(\w+)\.(\w+)`

For each match:
1. Extract: `left_table`, `left_col`, `operator`, `right_table`, `right_col`
2. Preserve `source_text` (the verbatim matched substring)
3. **Confidence scoring** — cross-validate table names against this column's `source_references[]`:
   - Both `left_table` AND `right_table` appear in `source_references[].table` → confidence = `"high"`
   - Only ONE table recognized in `source_references` → confidence = `"medium"`
   - NEITHER table recognized → confidence = `"low"` (stored but NOT locked as constraint)
4. Produce `extractedJoinPredicate` object per match

**Multiple matches per cell**: A single `transformation_logic` cell may contain multiple join predicates (e.g., compound ON clause `A.x = B.y AND A.z = B.w`). Extract ALL matches.

#### B. Literal Value Extraction (regex-first)

Apply patterns in order:

| Pattern | Regex | Extracted Fields |
|---------|-------|------------------|
| Quoted string equality | `(\w+)\s*=\s*'([^']+)'` | column, operator=`"="`, value (string) |
| Double-quoted equality | `(\w+)\s*=\s*"([^"]+)"` | column, operator=`"="`, value (string) |
| NOT IN list | `(\w+)\s+NOT\s+IN\s*\(([^)]+)\)` | column, operator=`"NOT IN"`, value (array — split on `,` and trim quotes) |
| IN list | `(\w+)\s+IN\s*\(([^)]+)\)` | column, operator=`"IN"`, value (array — split on `,` and trim quotes) |
| Hardcode instruction | `[Hh]ardcode\s+(?:to\s+)?['"]?([^'")\s,]+)['"]?` | column=null, operator=`"hardcode"`, value (string) |
| WHEN/THEN condition | `[Ww]hen\s+(\w+)\s*=\s*['"]?([^'")\s,]+)['"]?` | column (from WHEN), operator=`"="`, value (from comparison) |
| Numeric equality | `(\w+)\s*=\s*(\d+(?:\.\d+)?)` | column, operator=`"="`, value (number) |
| Inequality comparisons | `(\w+)\s*(!=|<>|>=|<=|>|<)\s*['"]?([^'")\s,]+)['"]?` | column, operator, value |

For each match:
1. Determine `context`: based on surrounding text — `"filter_predicate"` (appears with Filter/Where/Only keywords), `"case_when_condition"` (inside WHEN clause), `"case_when_result"` (inside THEN clause), `"literal_assignment"` (Hardcode/Default/Set), `"join_condition_literal"` (literal value within a join ON clause)
2. Preserve `source_text` (verbatim matched substring with surrounding context up to 10 chars each side)
3. All regex matches → confidence = `"high"` (unambiguous pattern match)

**Exclusions** (do NOT extract as literals):
- Template parameters: `{control_Date}`, `{current_business_date}`, `{batch_date}` — these are runtime placeholders, not fixed values
- Audit column standard values: `'3499-12-31'`, `'1'` (for active flag), `current_timestamp()` — these are template-defined
- Join predicate column references: `table.column` on both sides of `=` — these are join predicates (handled by Part A), not literal comparisons

#### C. Storage

- Store `extracted_join_predicates` array in column entry (or `null` if no matches)
- Store `extracted_literals` array in column entry (or `null` if no matches)
- Log: `"[STEP 2.9] Column '{target_column_name}': extracted {N} join predicates, {M} literals from free-text"`
- If ZERO patterns match for a qualifying column → both arrays = `null` (no extraction possible from this text). This is expected for simple transformation logic without joins or comparisons.

#### D. Backward Compatibility

- This step ADDS fields — never removes or modifies existing fields
- Columns with `structured_transformation != null` → skip (both arrays remain `null`)
- Columns with `transformation_logic == null` → skip (both arrays remain `null`)
- Old `mapping_parsed.json` files without these fields remain schema-valid (both properties are nullable)

**STTM-Generated Input Detection:**
If the input JSON contains `_meta.generator == "sttm-plugin"` and rows have `structured_transformation` objects, prefer the STTM-provided structures over regex extraction. Log: `"Using STTM-provided structured_transformation (confidence: 1.0, source: sql_ast)"`

---

### STEP 3 — Table-Level Fields (captured once from first non-empty row)

- `table_description` — first non-empty value in `Target Table description` column
- `additional_context` — first non-empty value in `Additional Context` column

### STEP 3b — Load Type Hint Extraction from Additional Context

> **ADDITIVE**: This step supplements STEP 3. It does NOT change existing parsing logic or downstream field extraction.

After capturing `additional_context`, scan its value for load type keywords (case-insensitive):

| Keywords | load_type_hint |
|---|---|
| `full load`, `historical`, `retrospective`, `backfill`, `Day 0`, `Day0`, `all records`, `initial load` | `Day0` |
| `incremental`, `delta`, `BAU`, `Day 1`, `Day1`, `since last run`, `new records`, `updated records`, `daily incremental` | `BAU` |
| `full then incremental`, `Day0 and Day1`, `historical + incremental`, `full_then_incremental` | `full_then_incremental` |

**Matching order (compound patterns first):**
1. Check compound `full_then_incremental` patterns FIRST. If any match → resolve immediately.
2. Then check individual Day0-only or BAU-only keywords.
3. If both Day0 AND BAU individual keywords found → set `load_type_hint = "full_then_incremental"` (both loads needed), UNLESS one keyword is negated (e.g., "not Day0", "no incremental", "without full load") — if negation detected on one → resolve to the non-negated keyword only.

- If match found → store `load_type_hint` as table-level field in output `mapping_parsed.json`
- If no keywords match → set `load_type_hint = null`
- This hint is consumed by `/identify-intent` at Priority 1.5

### STEP 4 — Crypto Indicator Detection

For each row, scan `Business Logic/Transformation Logic` only using three-step detection (in order):

**Step 4a — UDF Pattern (primary):**
- Apply regex: `cloud_api_udf_([A-Z0-9_]+)_(un)?protect\(` → extract DE name
- Match → `is_crypto = true`, `extraction_source = "udf_pattern"`
- Capture group 1 = `de_name`
- `_unprotect` → `operation = "detokenize"`
- `_protect` (without `un`) → `operation = "tokenize"`

**Step 4b — Protegrity Data Element Reference (secondary — only if Step 4a not matched):**
- Check if text contains "protegrity" (case-insensitive) AND "data element" (case-insensitive) AND "tokenize" or "detokenize" (case-insensitive)
- If all present, extract DE name matching pattern: `(UK|US|APAC)_TOK_([A-Z0-9]+)_(L\d+R\d+)_(UNC|ALN|DEC|NUM|CC|EML|DT)_DE`
- Match → `is_crypto = true`, `extraction_source = "protegrity_element"`
- If text contains "detokenize" → `operation = "detokenize"`
- If text contains "tokenize" → `operation = "tokenize"`
- If both or ambiguous → HALT and ask user: "Column '{column}' has both tokenize and detokenize keywords. Which operation is intended?" Set `extraction_ambiguous = true`.

**Step 4c — Keyword Scan (tertiary — only if Steps 4a & 4b not matched):**
- Check for keywords: `tokenize`, `detokenize`, `unprotect`, `protect` (case-insensitive)
- Match → `is_crypto = true`, `extraction_source = "keyword"`, `de_name = null`, `extraction_failed = true`

**Validation (applied to all extraction sources):**
- Validate extracted `de_name` against pattern: `(UK|US|APAC)_TOK_([A-Z0-9]+)_(L\d+R\d+)_(UNC|ALN|DEC|NUM|CC|EML|DT)_DE`
- If validation fails: `extraction_failed = true`

**Per-column crypto_flags structure:**
```json
{
  "column_name": {
    "is_crypto": true,
    "operation": "detokenize|tokenize",
    "de_name": "UK_TOK_ACCT_L0R0_NUM_DE or null",
    "extraction_source": "udf_pattern|protegrity_element|keyword",
    "extraction_failed": false,
    "extraction_ambiguous": false
  }
}
```

Write `session/crypto_flags.json`.

### STEP 4.5 — Source Volumetrics Extraction (optional sheet)

> **CONDITIONAL**: Only executes if the mapping Excel contains a sheet named `Source Volumetrics` (case-insensitive match: `source volumetrics`, `Source_Volumetrics`, `SourceVolumetrics` all valid). If sheet not found → set `session_state.source_volumetrics_path = null` and skip this step entirely (backward compatible).

**Sheet handling rule**: The workbook may contain multiple sheets (Template, sample/example tabs, Source Volumetrics). Only two sheets are relevant to parsing: (1) the main mapping sheet (first/active sheet — read by STEP 1–4), and (2) the "Source Volumetrics" sheet (read here). All other sheets are ignored.

**Step 4.5a — Parse rows:**

Expected columns (case-insensitive header match):

| # | Header | Maps to | Type |
|---|--------|---------|------|
| 1 | Source Database | `source_database` | string |
| 2 | Source Table | `source_table` | string |
| 3 | Estimated Rows | `estimated_rows` | integer |
| 4 | Estimated Size (GB) | `estimated_size_gb` | number |
| 5 | Daily Increment Rows | `daily_increment_rows` | integer |
| 6 | Daily Increment Size (GB) | `daily_increment_size_gb` | number |
| 7 | Primary Key | `primary_key` | string (comma-separated if composite) |
| 8 | Partition Key | `partition_key` | string (comma-separated if multiple) |
| 9 | Table Type | `table_type` | enum: NonTransactional_SCD2, NonTransactional_SCD1, Transactional |
| 10 | Broadcast Hint | `broadcast_hint` | boolean: Y→true, N→false |

- Skip row 2 (descriptions row) and any blank rows
- For each data row, emit one `sourceVolumetric` object per `schemas/mapping_excel.schema.json` definition
- Numeric cells: coerce to integer/number; if non-numeric or empty → `null`
- Primary Key / Partition Key: trim whitespace; preserve commas for composite keys; empty → `null`
- Table Type: case-insensitive normalization using canonical mapping:
    - `scd2`/`non-transactional`/`non_transactional`/`nontransactional`/`reference`/`snapshot` → `"NonTransactional_SCD2"`
    - `scd1` → `"NonTransactional_SCD1"`
    - `transactional`/`append` → `"Transactional"`
    - Legacy `Non-Transactional` (without SCD qualifier) → `"NonTransactional_SCD2"`
    - Unrecognized value → `null` with WARNING
- Broadcast Hint: Y/Yes/TRUE/1 → `true`; N/No/FALSE/0/empty → `false`

**Step 4.5b — Cross-validation (advisory, non-blocking):**
- Collect all unique `(source_database, source_table)` pairs from STEP 2 `source_references`
- For each volumetric entry, check if `(source_database, source_table)` exists in that set
- If orphan found (volumetric entry not referenced in mapping) → log WARNING: "Source Volumetrics entry '{db}.{table}' not referenced in mapping columns — will be ignored by downstream agents"
- If a mapping source table has NO volumetric entry → no warning (volumetrics are optional per table)

**Step 4.5c — Auto-broadcast inference:**
- For any entry where `estimated_size_gb` is not null AND < 0.01 (10MB) AND `broadcast_hint` is false/null → set `broadcast_hint = true`
- Log INFO: "Auto-broadcast applied to {db}.{table} (reason: estimated_size_gb < 10MB)"

**Step 4.5d — Write output:**
- Write parsed array to `session/source_volumetrics.json` (conforms to `sourceVolumetric` in `schemas/mapping_excel.schema.json`)
- Set `session_state.source_volumetrics_path = "session/source_volumetrics.json"`
- Also include `source_volumetrics` array in `session/mapping_parsed.json` at the top-level (alongside `columns`, `target_database`, etc.)

### STEP 5 — Post-Parse Validators

Run in order (non-blocking except where noted):

1. `consistency-validator` (Part B) — check target DB prefix matches `expected_db_prefix` from session state → WARNING if mismatch
2. `consistency-validator` (Part C) — check source DB prefixes against `expected_source_layer` → **BLOCK** on layer promotion violation; WARNING on unexpected layer

### STEP 6 — Write Output

Write `session/mapping_parsed.json` conforming to `${CLAUDE_PLUGIN_ROOT}/schemas/mapping_excel.schema.json`.
Write updated `session/crypto_flags.json`.

### STEP 6.1 — Context Checkpoint Write (Full-Automation Only)

If `session_state.auto_chain.enabled == true`, write `chain_checkpoints.post_parse` to `session/session_state.json`:

```json
{
  "chain_checkpoints": {
    "post_parse": {
      "tenancy": "<session_state.tenancy_name>",
      "data_product_type": "<session_state.data_product_type>",
      "target_tables": ["<db.table1>", "<db.table2>"],
      "optional_columns_detected": ["<col1>", "<col2>"],
      "crypto_enabled": true/false,
      "source_volumetrics_available": true/false,
      "total_target_tables": N,
      "timestamp": "<ISO 8601>"
    }
  }
}
```

This checkpoint survives context compaction and is loaded by downstream commands for reliable state awareness.

## Output Files

- `session/mapping_parsed.json`
- `session/crypto_flags.json` (updated)
- `session/source_volumetrics.json` (conditional — only if "Source Volumetrics" sheet present in mapping Excel)
- `session/audit_log.jsonl` (new entry)

## Failure Modes

- Missing required column headers (after semantic matching) → HALT; list missing canonical names with accepted variants
- Layer promotion violation (CDP/BDP reading BASE) → BLOCK for that table; surface error message
- Crypto column with unextractable DE name (keyword-only with no UDF or Protegrity pattern) → flag `extraction_failed: true`; generation for that column will be refused at crypto assembly (not a placeholder — user must add complete UDF pattern or Protegrity reference to mapping)
- Invalid DE name format (fails pattern validation) → flag `extraction_failed: true`; generation refused
- Ambiguous crypto operation (both tokenize and detokenize keywords present) → flag `extraction_ambiguous = true`; HALT and ask user which operation is intended (do NOT default to tokenize)
