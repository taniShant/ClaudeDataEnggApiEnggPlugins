---
description: Generate DTXOG orchestration config — Glue platform only
disable-model-invocation: false
---

# /gen-dtxog

Generate the DTXOG config JSON file **per target table**. **AWS Glue only** — refused for Databricks.

## ⚠️ CRITICAL: Per-Target-Table Output

This command generates **ONE DTXOG CONFIG JSON PER TARGET TABLE** — NOT a single generic DTXOG for all tables.

### Output Format

**Single-target output**:
```
generated/glue/dtxog/fdp_uk_mortgage_db_account_wm_dtxog.json
```

**Multi-target output** (3 target tables):
```
generated/glue/dtxog/fdp_uk_mortgage_db_account_wm_dtxog.json
generated/glue/dtxog/fdp_uk_mortgage_db_rates_fees_dtxog.json
generated/glue/dtxog/fdp_uk_mortgage_db_mortgage_detail_dtxog.json
```

Create directory `generated/glue/dtxog/` if it does not exist.

Each DTXOG config is **target-table-specific** and contains:
- Dataset ID for this specific table
- Wrapper reference for this specific table (`{db}_{table}_wrapper.py`)
- Glue job parameters tuned for this table
- Iceberg configuration for this table
- Crypto configuration if applicable to this table

**Multi-source-system output** (when `data_flow_detection.source_systems` is non-empty — one DTXOG per source_system):
```
generated/glue/dtxog/fdp_uk_mortgage_db_account_wm_ilp_dtxog.json
generated/glue/dtxog/fdp_uk_mortgage_db_account_wm_reference_data_dtxog.json
```

### Multi-Source-System Awareness

Read `session_state.data_flow_detection`:

- **`source_systems` is non-empty**: Generate N DTXOGs (one per source_system):
  - Output: `generated/glue/dtxog/{db}_{table}_{source_system}_dtxog.json`
  - S3 paths include `{source_system}` prefix (reuse path patterns from `dtxog_config_byoc_multiple_data_flow.template.json`):
    - `wrapper-file: "s3://bucket/apps/pkg/{{source_system}}/bin/wrapper.py,..."`
    - `package-cnfg: "s3://bucket/apps/pkg/{{source_system}}/conf/{{db}}/{{table}}/config.json"`
- **`"combined"` or `source_systems` is empty**: Use single-data-flow DTXOG template (unchanged).

## Usage

```
/gen-dtxog
```

## Mapping Input Projection (Context Efficiency)

When passing `mapping_parsed.json` data to the `glue-dtxog-agent`, include ONLY these fields per target table:
- `target_table`, `target_database`
- `source_tables[]` → `database`, `table`
- `crypto_flagged` (boolean)
- `load_type`

**Omit**: `column_mappings`, `transformation_logic`, `descriptions`, full column definitions, source_columns

This reduces mapping input from ~6.5K tokens to ~1K tokens for the dtxog agent.

## Prerequisites

- Platform = Glue (refuse if Databricks)
- `session/intent_identification.json` exists
- `session/crypto_flags.json` exists
- Tenancy name known (from tenancy skill Tenancy Registry lookup on target_database)
- **Infrastructure config complete**: `session_state.env_config` is non-null AND (`session_state.tenancy_resolution_method != "user_provided"` OR `session_state.env_config.questionnaire_turns_completed == 6`). If this check fails → HALT: `"env_config incomplete — infrastructure questionnaire may not have completed all questions. Re-run /parse-mapping to resolve."`

## Resume Logic (A2 Feature)

**Before running the glue-dtxog-agent:**

1. Load `session/session_state.json`
2. Check `session.phases["gen_dtxog"].status`:
   - **If "completed"** → Skip agent; load cached result → return dtxog config path
   - **If "in_progress"** → Resume: check if `{target_database}_{target_table}_dtxog.json` exists → skip if present
   - **If "pending"** → Run agent normally

3. **On entry:**
   - Set `session.phases["gen_dtxog"].status = "in_progress"`
   - Set `session.phases["gen_dtxog"].started_at = now()`
   - Save session state

4. **On completion:**
   - Set `session.phases["gen_dtxog"].status = "completed"`
   - Set `session.phases["gen_dtxog"].completed_at = now()`
   - Cache result: path to dtxog config file
   - Save session state

5. **On error:**
   - Set `session.phases["gen_dtxog"].status = "failed"`
   - Set `session.phases["gen_dtxog"].error = error_message`
   - Save session state; propagate error

## STEP 0.0 — Chain Mode Output Compression

Apply `commands/refs/chain-mode-compression.md` pattern. Compact return: `[{step}/{total}] ✓ /gen-dtxog — {N} dtxog config files generated | Checkpoint: post_generation updated`

## STEP 0.1 — Chain Checkpoint Loading

Apply `commands/refs/chain-checkpoint-pattern.md`. Checkpoint key: `post_intent`.

## STEP 0.5 — Read Templates (BLOCKING — do not skip)

Before generating any DTXOG config, the agent MUST read the actual template from disk after determining the correct variant (see STEP 2 below for variant selection).

**Template variants:**
- `${CLAUDE_PLUGIN_ROOT}/templates/glue/dtxog_config_byoc_single_data_flow.template.json`
- `${CLAUDE_PLUGIN_ROOT}/templates/glue/dtxog_config_byoc_multiple_data_flow.template.json`
- `${CLAUDE_PLUGIN_ROOT}/templates/glue/dtxog_config_byoc_crypto_single_data_flow.template.json`
- `${CLAUDE_PLUGIN_ROOT}/templates/glue/dtxog_config_byoc_crypto_multiple_data_flow.template.json`

**Rules:**
- The template is the **authoritative source of structure**. The prose rules in this doc are *reference* only.
- If the template and prose conflict, **the template wins**.
- Generation = template read + placeholder substitution. Nothing more.
- Any key, section, or structure NOT present in the template must NOT appear in the output.
- Do NOT generate from description or memory — render the template.

---

## Behaviour

### STEP 1 — Platform Check

If platform = Databricks: REFUSE with:
> "DTXOG config is AWS Glue / DTX framework only."

### STEP 2 — Select Template

**Step 2a — Determine source system scenario** (from domain knowledge):
- Check `domain_knowledge_text` for source system specification:
  - If `source_system` field present → multiple-data-flow scenario (use multiple-data-flow template)
  - Else → single data flow scenario (use single-data-flow template)
- If domain knowledge not provided: use single-data-flow template (default — multiple-data-flow requires explicit `source_system` declaration in domain knowledge)

**Step 2b — Select crypto variant**:
- If `crypto_flags.any_column_crypto_flagged = true`: use `*_crypto_*` variant
- Else: use base variant

**Final template name**:
```
dtxog_config_byoc[_crypto][_single_data_flow|_multiple_data_flow].template.json
```

Examples:
- No crypto, single data flow: `dtxog_config_byoc_single_data_flow.template.json`
- Crypto active, multiple-data-flow: `dtxog_config_byoc_crypto_multiple_data_flow.template.json`

### STEP 3 — Populate Fields

**Hardcoded values** (consistent across all environments):
- `itbs`: `BSN0004626` (global BUK CDAO identifier — hardcoded in template, not a placeholder)

**Derived from tenancy name** (auto-derive, never block):
- `state_machine`: `dtx-sm-glue-byoc-{tenancy_name}`
- Glue job: `dtx-glue-byoc-{tenancy_name}`

**ITSI values** (from `session_state.env_config`):
- dev: `env_config.dev.itsi`
- uat: `env_config.uat.itsi`
- prd: `env_config.prd.itsi` + `env_config.prd.compid`

**Worker sizing** (defaults — confirm with team):
- dev/uat: `worker-type: G.1X`, `number-of-workers: 10`, `timeout: 300`
- prd: `worker-type: G.2X`, `number-of-workers: 10`, `timeout: 2880`

**SparkConf** — Iceberg extensions (always included for BYOC Iceberg):
```
spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions
--conf spark.sql.catalog.glue_catalog=org.apache.iceberg.spark.SparkCatalog
--conf spark.sql.catalog.glue_catalog.warehouse=file:///tmp/spark-warehouse
--conf spark.sql.catalog.glue_catalog.catalog-impl=org.apache.iceberg.aws.glue.GlueCatalog
--conf spark.sql.catalog.glue_catalog.io-impl=org.apache.iceberg.aws.s3.S3FileIO
--conf spark.sql.catalog.glue_catalog.glue.lakeformation-enabled=true
--conf spark.sql.catalog.glue_catalog.glue.id={account_id_for_env}
--conf spark.sql.iceberg.handle-timestamp-without-timezone=True
```

**Crypto block** (when `any_column_crypto_flagged = true`):
- `enable_crypto_api: "true"`
- `secret_name`: Ask via G5 — `{{sms_secret_name}}` placeholder if not provided
- `custom_de_list`: Auto-assembled from all successfully extracted DE names across all flagged columns — never a placeholder
- `log_level: "info"`
- Additional SparkConf: arrow execution conf + crossJoin enabled
- `package-file` per env (from `session_state.env_config.{env}.crypto_account_id` + Pattern 4 crypto bucket format)

### STEP 4 — Validate

Run `dtxog-structure-validator` (inline validation — read generated file and apply rules):
- All required keys present
- `crypto_dpaas.enable_crypto_api = "true"` if crypto flagged
- No cross-environment values

### STEP 5 — Write

File: `generated/glue/dtxog/{target_database}_{target_table}_dtxog.json`

## Output Files

- `generated/glue/dtxog/{target_database}_{target_table}_dtxog.json`
- `session/audit_log.jsonl` (new entry)

## Placeholder Resolution (Phase 2: Auto-Resolve)

**Note**: `{{itbs}}` is hardcoded in template as `BSN0004626` (not a placeholder)

**BEFORE Generation** (pre-flight check):
- Check if `crypto_flags.any_column_crypto_flagged = true`
- If YES: Attempt blocking placeholder resolution:
  - `{{sms_secret_name}}`: Construct from tenancy
  - `{{custom_de_list}}`: Extract from crypto_flags.json
- If either fails: ⛔ HALT (fail fast; don't generate)

**AFTER Generation** (post-generation validation):
- Scan rendered file for `\{\{[a-z_]+\}\}` patterns
- For blocking placeholders ({{sms_secret_name}}, {{custom_de_list}}):
  - If unresolved: error (pre-flight should have caught this)
- Update `session/placeholders.json` with resolution status
- Mark artefact: ✅ VALIDATED (if all blocking resolved) or ⛔ DRAFT_UNVALIDATED

**Reference**: See `validators/placeholder-auto-resolver.helper.md` for detailed logic

| Placeholder | Source | Resolution |
|---|---|---|
| `{{s3_bucket_{env}}}` | `session_state.env_config.{env}.s3_bucket` | Centralized — resolved during /parse-mapping STEP 2.6 |
| `{{source_system}}` | Domain knowledge | Only present in multiple-data-flow template; must be provided |
| `{{database_name}}` | mapping_parsed.json | target_database **with `_iceberg` suffix stripped** for S3 paths (BYOC wrapper-file .whl segment and package-cnfg conf/ path); kept as-is for `metadata.db_name` |
| `{{table_name}}` | mapping_parsed.json | target_table |
| `{{aws_account_id_{env}}}` | `session_state.env_config.{env}.aws_account_id` | Centralized — resolved during /parse-mapping STEP 2.6 |
| `{{crypto_package_path_{env}}}` | `session_state.env_config.{env}.crypto_account_id` + Pattern 4 | Derive path from centralized crypto_account_id; or domain knowledge override |
| `{{sms_secret_name}}` | Phase 2 auto-resolver | Construct: `sms-crypto-{tenancy_short_name}` — ⛔ HALT if fails |
| `{{custom_de_list}}` | Phase 2 auto-resolver | Extract from crypto_flags.json — ⛔ HALT if empty + crypto |
| `{{tenancy_name}}` | `session_state.env_config.tenancy_name` | Centralized — resolved during /parse-mapping STEP 2.6 |
| `{{itsi_{env}}}`, `{{compid_prd}}` | `session_state.env_config.{env}.itsi` / `.compid` | Centralized — resolved during /parse-mapping STEP 2.6 |

## Domain Knowledge Format

For multiple-data-flow scenarios or path overrides, users should provide in `${CLAUDE_PLUGIN_ROOT}/configs/domain_knowledge/<tenancy>_knowledge.md`:

```markdown
## DTXOG Configuration

**Source system scenario**:
- source_system: "SYSTEM_A"  (required for multiple-data-flow)

**S3 bucket overrides** (optional):
- s3_bucket_dev: "dev-custom-bucket-name"
- s3_bucket_uat: "uat-custom-bucket-name"
- s3_bucket_prd: "prd-custom-bucket-name"

**Crypto package path overrides** (optional):
- crypto_package_path_dev: "s3://custom-dev-bucket/crypto/ProtectorTools-1.0.whl"
- crypto_package_path_uat: "s3://custom-uat-bucket/crypto/ProtectorTools-1.0.whl"
- crypto_package_path_prd: "s3://custom-prd-bucket/crypto/ProtectorTools-1.0.whl"

**ITSI or Netcool overrides** (optional):
- itsi_dev: "SNSVC0000000"
- itsi_uat: "SNSVC0000001"
- itsi_prd: "SNSVC0000002"
- compid_prd: "CUSTOM_COMPID"
```

## Failure Modes

- Platform = Databricks → REFUSE with: "DTXOG config is AWS Glue / DTX framework only."
- ⛔ **{{sms_secret_name}} cannot be resolved** (invalid tenancy) → HALT (fail fast)
- ⛔ **{{custom_de_list}} is empty** (crypto columns flagged but no DE extraction) → HALT (fail fast)

## Do Not Invent

- Account IDs — use aws skill for known tenancies; placeholder otherwise
- ITSI values — use ops skill; placeholder if tenancy unknown or use domain knowledge override
- Crypto DE names — assembled from mapping, never guessed
- Source systems — must come from domain knowledge for multiple-data-flow scenario
- S3 bucket names — from G3 answers, aws skill patterns, or domain knowledge override
