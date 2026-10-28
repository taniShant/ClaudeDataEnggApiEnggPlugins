# Gating Questions — Prompts and Flow

This document defines the exact language and expected response handling for each gate in the DE Agent gating state machine.

## Important: Mesh JSON Hardcoded Constants & Domain Knowledge Priority

### Hardcoded Constants (never asked, never varied)
- `"versionPolicy": "NO_CONSTRAINT"` — Always hardcoded
- `"versionManagement": "CLIENT"` — Always hardcoded
- `"owner.itbs": "BSN0004626"` — Always hardcoded (global BUK CDAO identifier)

Enforced at JSON schema level (`const` constraints) and never requested during any gate.

### Resolution Priority for Missing Fields
When mesh JSON fields are missing (e.g., `btb_team`, `datasetType`, `summary`, `description`):

**Priority Order**:
1. **Look up tenancy skill — Mesh JSON Metadata table** (Glue only) — Primary source for `btb_team`, `datasetType`, `datasetTypeSummary`. Match feature team name derived from target database.
2. **Check domain knowledge MD** (auto-discovered or provided) — Secondary source for `summary`, `description`, overrides
3. **Then ask user** — Only if steps 1-2 don't yield a value

**Do NOT prompt user for a value that exists in SKILL.md or domain knowledge.**

Fields from SKILL.md: `btb_team` (BTB Owner), `datasetType`, `datasetTypeSummary`.
Fields from domain knowledge: `summary`, `description`, `dataGroup`, partition labels.

---

## Auto-Discovery — Domain Knowledge (during `/parse-mapping`)

**Automatic Detection** — No gate question required:

During `/parse-mapping` (STEP 2.1), the plugin automatically discovers and loads domain knowledge:

1. Extract `target_database` from the parsed Excel rows (e.g., `fdp_uk_cntct_centr_chnl_db_icbg`)
2. **Look up `target_database` in the appropriate tenancy skill** — normalize (case-insensitive, strip whitespace):
   - If platform = Glue → `tenancy` skill Tenancy Registry (match Hive Database or Iceberg Database column)
   - If platform = Databricks → `databricks-tenancy` skill Tenancy Infrastructure Registry (match Target DB column)
3. If match found: extract the **Feature Team Name** from the matched row (e.g., Glue: `fdpchnlcc`; Databricks: `BUK_BBKYC_BDP`)
4. Construct expected filename: `{feature_team_name}_knowledge.md` (e.g., `fdpchnlcc_knowledge.md`)
5. Search in `${CLAUDE_PLUGIN_ROOT}/configs/domain_knowledge/` (plugin installation directory)
6. If found: auto-load into `session_state.domain_knowledge_text` (silent, non-blocking)
7. If `target_database` not found in SKILL.md: log WARNING, continue without (non-blocking)
8. If found in SKILL.md but file does not exist: log INFO, continue without (non-blocking)

**User can override** via `--domain-knowledge` flag during `/init` (takes precedence over auto-discovery):
```bash
/init Mortgage_Mapping.xlsx --domain-knowledge ./my_project_docs/custom_rules.md
# → Uses user-provided project-relative path immediately; skips auto-discovery from plugin directory
```

---

## G1 — Platform Selection (OPTIONAL via `--platform` argument)

**When Prompted** (if `--platform` NOT provided to `/init`):

"Which platform are you generating code for?
- `1` — **AWS Glue** (DTX-BYOC framework, Iceberg, DTXOG config)
- `2` — **Databricks** (Foundation library, Unity Catalog, driver + transform pattern)

Please enter `1` or `2`."

**When Skipped** (if `--platform` provided):

```bash
/init Mortgage_Mapping.xlsx --platform glue
# G1 gate skipped; platform set directly
# No prompt shown
```

**Valid responses**: `1`, `Glue`, `AWS Glue`, `2`, `Databricks`  
**Effect**: Sets `session_state.platform`. Platform is locked for the remainder of the session.  
**Cross-commands**: After G1, `/gen-wrapper`, `/gen-dtxog`, `/gen-mesh` are blocked for Databricks; `/gen-driver`, `/gen-ddl` are blocked for Glue.

**How to Skip G1**: Pass `--platform` to `/init` command (enables zero-interaction automation with `--full-automation`)

---

## G0.5 — Domain Knowledge (Optional — may already be auto-discovered)

**Auto-Discovery Status**: Check first if domain knowledge was already auto-discovered during `/parse-mapping`. If yes, skip this gate entirely.

**Ask** (only if auto-discovery found nothing AND `--domain-knowledge` not provided): "Do you have a domain knowledge file to provide? (Optional — press Enter to skip)

If yes, please provide the file path (`.md` format) or paste the content directly.
Domain knowledge helps with intent identification (grain, primary key, table type) and transformation logic."

**Valid responses**: file path, inline text, empty (skip)  
**Effect**: Loads domain knowledge as Priority 2 context for intent identification. Non-blocking on failure.  
**Timing**: Auto-discovery runs during `/parse-mapping` (STEP 2.1). Skipped if `--domain-knowledge` was provided to `/init`.  
**Override**: User can provide `--domain-knowledge` flag to `/init` to override auto-discovered file.

---

## G1.5 — Data Product Type (IMPLICIT — Auto-Derived)

**Status**: ✅ **NO GATE QUESTION** — G1.5 is auto-resolved based on target database prefix

**How it works** (during `/parse-mapping`):
1. Extract `target_database` from first row of mapping Excel (e.g., `fdp_uk_complaints_db`)
2. Parse database prefix: `fdp_` → FDP, `cdp_` → CDP, `bdp_` → BDP, `shared_fdp_` → FDP, `shared_cdp_` → CDP, `shared_bdp_` → BDP
3. Auto-set all derived fields:
   - `data_product_type`: FDP | CDP | BDP
   - `is_shared_data_product`: true (if `shared_` prefix) | false
   - `source_layer`: BASE | FDP/CDP | FDP/CDP
   - `target_account`: DDA | BCA
4. Mark G1.5 as "RESOLVED" in `gates_resolved` (no user interaction)

**Error Handling**: Invalid prefix (not `fdp_`, `cdp_`, `bdp_`, `shared_fdp_`, `shared_cdp_`, `shared_bdp_`) → ERROR; require user to fix mapping Excel with correct prefix

**Multi-table validation**: If mapping has multiple tables with DIFFERENT prefixes → ERROR; cannot mix DP types in one session

---

## G3 — Mesh JSON S3 Locations (Glue only — FULLY AUTOMATIC)

**Status**: ✅ **FULLY AUTOMATIC** — No user input required

**How it works**: During `/parse-mapping` (Step 2.6 — Per-Environment Infrastructure Resolution), the plugin resolves ALL per-environment infrastructure values centrally and stores them in `session_state.env_config`. The S3 bucket values are auto-populated into `mesh_json_s3_locations` as part of this step.

**Algorithm**:
1. Extract `target_database` from mapping Excel (e.g., `fdp_uk_complaints_db`)
2. Parse DP type + domain from database name
3. Determine catalog type by matching `target_database` against the tenancy registry: if it matches the **Iceberg Database** column → Iceberg; if it matches the **Hive Database** column → Hive (skip cells marked "Not available")
4. From the matched tenancy row → extract `bucket_shortname` (Glue only)
5. Route to correct AWS account based on DP type (FDP/CDP → DDA; BDP → BCA)
6. **For EACH environment (dev, uat, prd)**: build full S3 bucket name using appropriate pattern:
   - **Pattern 1 (Iceberg)**: `{env_prefix}-pre-{bucket_shortname}-{account_id}-eu-west-1`
   - **Pattern 2 (Hive)**: `{env_prefix}-{dp_type}-{bucket_shortname}-{account_id}-eu-west-1`
7. Store in `session_state.env_config` + auto-populate `mesh_json_s3_locations`

**Examples** (all 3 environments resolved together):
- `fdp_uk_mortgage_db_icbg` (Iceberg, DDA):
  - dev: `dev1-pre-fdpmortgage01-767397940910-eu-west-1`
  - uat: `uat1-pre-fdpmortgage01-590184123059-eu-west-1`
  - prd: `prd1-pre-fdpmortgage01-194722397519-eu-west-1`

**Effect**: `mesh_json_s3_locations` and `env_config` both auto-populated in session state. G3 gate auto-resolved.  
**User input needed**: If tenancy is unknown or not found in Tenancy Registry, the system invokes the interactive infrastructure questionnaire (see `prompts/infrastructure-questionnaire-glue.md` for Glue or `prompts/infrastructure-questionnaire-databricks.md` for Databricks) to collect all required values interactively — the system asks batched questions and waits for user responses. Otherwise, fully automatic.  
**Reference**: See `docs/per_environment_resolution.md` for detailed algorithm and all resolved values.

**Related: Mesh JSON platformDefinition**

The catalog type detected in Step 3 determines `storageMediumLinks[0].platformDefinition`:
- **Iceberg** (matched Iceberg Database column, OR Pattern 1 S3 bucket) → `"edp_cloud_datalake"` (default)
- **Hive** (matched Hive Database column, OR Pattern 2 S3 bucket) → `"buk_cloud_datalake"` (only if explicitly clarified)

**Default Rule**: Assume Iceberg (`edp_cloud_datalake`) UNLESS domain knowledge or user explicitly clarifies "Hive".

See gen-mesh.md STEP 8b and glue-mesh-agent.md Phase M.8 for full detection logic.

---

## G4 — Source Classification (AUTOMATIC - No User Gate)

**Status**: ✅ **AUTOMATIC BY DEFAULT** — Source table type classification runs without user prompt

**Trigger**: After /parse-mapping completes

**Behaviour**:
1. Classify source tables using local data (Volumetrics → Domain Knowledge → Mapping heuristics)
2. Write source_table_metadata.json with per-table NonTransactional/Transactional classification
3. HALT only if type cannot be determined from any source

---

## G5 — Placeholder Completion (Auto-Resolve or HALT)

**Status**: ❌ NO USER PROMPT — Auto-resolve or HALT (Zero-Prompt Architecture)

**Trigger**: Any open `{{placeholder}}` in a generated artefact.

**Blocking Placeholders** (auto-resolve or HALT):

1. **{{itbs}}** — ITSI owner code
   - Auto-resolve: Lookup in **ops** skill (ITSI & Netcool Components)
   - If found: Inject automatically
   - If NOT found: ⛔ HALT (user must verify tenancy in mapping)

2. **{{sms_secret_name}}** — Crypto secret name
   - Auto-resolve: Construct from tenancy → `sms-crypto-{tenancy_short_name}`
   - If tenancy valid: Inject automatically
   - If NOT valid: ⛔ HALT (user must fix mapping database name)

3. **{{custom_de_list}}** — Protegrity Data Elements
   - Auto-resolve: Extract from `crypto_flags.json` (already extracted during parsing)
   - If extraction succeeded: Inject automatically
   - If empty + crypto columns exist: ⛔ HALT (user must add complete UDF patterns)

**Non-Blocking Placeholders** (auto-resolve or skip):

- **{{change_request_no}}** — Leave as-is; user resolves manually later
- **{{expected_completion_sla}}** — Lookup in domain knowledge; if found: inject; if not: leave as-is
- **{{compid_prd}}** — Lookup in SKILL.md; if found: inject; if not: leave as-is

**HALT Messages** (per blocking placeholder):

For {{itbs}}:
```
⛔ HALT — Cannot resolve {{itbs}} for tenancy '{tenancy}'
REQUIRED ACTION:
  1. Verify tenancy in target_database matches known tenancies
  2. Valid tenancies: [list from `skills/tenancy-summary/SKILL.md`]
  3. Fix mapping and re-run
```

For {{sms_secret_name}}:
```
⛔ HALT — Cannot construct {{sms_secret_name}} (invalid tenancy)
REQUIRED ACTION:
  1. Verify target_database uses valid tenancy
  2. Valid format: fdp_/cdp_/bdp_ prefix
  3. Fix mapping and re-run
```

For {{custom_de_list}}:
```
⛔ HALT — Crypto columns detected but {{custom_de_list}} empty
REQUIRED ACTION:
  1. Add complete UDF patterns to mapping Excel
  2. Expected: cloud_api_udf_{DE_NAME}_(un)protect({column})
  3. Re-run /parse-mapping
```

**Effect**:
- ✅ Blocking placeholders auto-resolved: Inject automatically
- ⛔ Blocking placeholders cannot be resolved: HALT (user must fix mapping)
- ⚪ Non-blocking placeholders: Leave as-is; user resolves later

---

## G5-grain — Intent Ambiguity (HALT — No User Prompt)

**Status**: ❌ NO USER PROMPT — HALT instead (Zero-Prompt Architecture)

**Triggers**:

1. **Join Logic Missing (advisory, non-blocking)**: Any column in the target table has `join_logic_missing = true` in `mapping_parsed.json`. Emits advisory message — pipeline continues.
2. **Intent Ambiguity (HALT)**: Any table in `session_state.pending_intent_tables[]` could not resolve intent fields with confidence.

### G5-grain Advisory: Join Logic Missing (Non-Blocking)

**Trigger**: `session_state.parse_warnings[]` contains entries with `type = "join_logic_missing"` for the current target table.

**Advisory Message** (non-blocking — pipeline continues):
```
ℹ️ ADVISORY — NL Join Interpretation Active

TABLE: {target_database}.{target_table}
Columns using NL interpretation for multi-source joins:
  - {column_name}: references tables [{table_list}]
  - ...

The transform generator will interpret join/filter logic from free-text in the
Business Logic/Transformation Logic column (Rule 11). Generated code will include
ADVISORY comments for developer review.

OPTIONAL (for more deterministic output):
  Consider updating the mapping Excel to use structured format:
    Driver Table: <primary_table>
    Driver Conditions: [<filters on driver table, if subset needed>]
    Join 1 Table: <joined_table>
    Table1 Conditions: [<filters on joined table, if subset needed>]
    Join 1 Type: LEFT|INNER|RIGHT|FULL|CROSS
    Join 1 Conditions: <join ON clause>
    Value: <final expression>
```

**Effect**: Advisory only — intent resolution and generation proceed. No halt, no user action required.

---

### G5-grain Sub-gate: Intent Ambiguity (HALT)

**Trigger**: Any table in `session_state.pending_intent_tables[]` could not resolve intent fields with confidence.

**HALT Message**:
```
⛔ HALT — G5-grain: Intent Ambiguity (Cannot Auto-Decide)

TABLE: {target_database}.{target_table}
Fields with LOW confidence or UNRESOLVED: {field_list}

Analysis Summary:
  - Audit columns (structural): {H0/H0b result}
  - Transformation logic signals: {found or "none"}
  - Domain knowledge: {provided or "not found"}
  - 7-rule framework: {rule result}

REQUIRED ACTION (Choose One):

Option A — Add Audit Columns:
  For SCD2: eff_start_date, eff_end_date, active, dw_upd_lod_tmp
  For Transactional: dw_bus_dt, dw_lod_tmp

Option B — Add Transformation Logic Signals:
  For SCD2: "MERGE INTO table ON key_cols" or "SCD2"
  For Transactional: "INSERT INTO ... SELECT ... GROUP BY" or "append-only"

Option C — Provide Domain Knowledge:
  Create: ${CLAUDE_PLUGIN_ROOT}/configs/domain_knowledge/{feature_team_name}_knowledge.md
  (Look up Feature Team Name:
    - If platform = Glue → `tenancy` skill Tenancy Registry (match Hive/Iceberg Database column)
    - If platform = Databricks → `databricks-tenancy` skill Tenancy Infrastructure Registry (match Target DB column))
  Include: grain, primary_key, table_type, partition, load_type

Option D — Specify load_type in Additional Context column (for load_type resolution only):
  In the mapping Excel, populate the "Additional Context" column (table-level, first non-empty cell) with:
    - "Day0" or "full load" or "historical" or "retrospective" or "backfill" or "initial load" → resolves load_type = Day0 (all synonyms for one-time full historical load)
    - "BAU" or "Day1" or "incremental" or "delta" or "daily incremental" → resolves load_type = BAU (all synonyms for ongoing new/changed records load)
    - "full then incremental" or "Day0 and Day1" → resolves load_type = full_then_incremental (both)
  This is scanned at Priority 1.5 and OVERRIDES Priority 1 (transformation logic). Both Day0+BAU keywords present (without negation) resolves to full_then_incremental.

NEXT STEPS:
  1. Update mapping Excel or create domain knowledge file
  2. Re-run: /parse-mapping
  3. Re-run: /identify-intent
```

**Effect**: 
- ⛔ HALT — Stop processing
- User must fix mapping Excel, provide domain knowledge, or supply intent overrides
- User re-runs `/identify-intent` (interactive) or `/resume` (full-automation)
- Upon retry: Resume from first unresolved table

**Full-Automation Mode Recovery (when `--full-automation` active):**

In full-automation mode, the HALT additionally:
1. Persists halt state to `session_state.auto_chain` (step number, command, reason, timestamp)
2. Generates `session/intent_resolution_report.md` with per-field analysis (what was tried, why it failed)
3. Displays recovery options referencing `/resume` command

**Recovery via Intent Overrides (Priority 0):**

Users can supply missing field values directly in `session/intent_overrides.json` (schema: `intent_overrides.schema.json`):
```json
{
  "overrides": [
    {
      "target_database": "fdp_uk_mortgage_db",
      "target_table": "account_wm",
      "primary_key_columns": ["account_id", "eff_start_date"],
      "partition_key_columns": ["active"]
    }
  ]
}
```
Then run `/resume` — override fields are applied as Priority 0 (highest), skipping standard 3-source resolution for those fields.

---

## G5-C — Crypto Refusal

**Trigger**: A column has `crypto_flagged: true` but `extraction_failed: true` (DE name not extractable from transformation logic).

**REFUSE with**: "I detected a crypto operation on column `{column_name}` but could not extract the Protegrity Data Element (DE) name from the transformation logic.

Expected pattern: `cloud_api_udf_{DE_NAME}_protect({col})` or `cloud_api_udf_{DE_NAME}_unprotect({col})`

Found: `{actual_expression}`

**I cannot generate the crypto configuration or transformation code for this column** because guessing the DE name would create incorrect tokenisation that could silently corrupt data.

Please update the mapping document with the correct UDF expression pattern and re-run `/parse-mapping`."

**Effect**: Halts all code generation. Session cannot proceed until mapping is corrected and re-parsed.
