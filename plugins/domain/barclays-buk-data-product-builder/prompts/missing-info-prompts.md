# Missing Information Prompts

Standard prompts for collecting **individual** missing values during G5 inline placeholder resolution.

> **Full Tenancy Unknown — Batched Infrastructure Collection**
>
> When the **entire tenancy is unresolved** (target_database not found in any registry), the system uses `prompts/infrastructure-questionnaire-glue.md` (Glue) or `prompts/infrastructure-questionnaire-databricks.md` (Databricks) to collect all infrastructure values in a batched interaction with interactive question–answer flow. The individual prompts below are for resolving **SINGLE** missing values when the tenancy IS known but a specific field is missing.

## IMPORTANT: SKILL.md + Domain Knowledge First Rule

Before asking user for ANY mesh JSON field value:

1. **Look up tenancy skill — Mesh JSON Metadata table** (Glue only) — Primary source for `btb_team`, `datasetType`, `datasetTypeSummary`. Match feature team name derived from target database.
2. **Check `session_state.domain_knowledge_text`** (auto-discovered during `/parse-mapping` OR provided via `--domain-knowledge`) — Secondary source for overrides or additional metadata.
3. **Only ask user IF the value is NOT in SKILL.md or domain knowledge**

This applies to ALL fields listed below:
- `btb_team` → tenancy skill BTB Owner column (fallback: `sdw_buk_btb`)
- `datasetType` → tenancy skill datasetType column (fallback: derive as `foundation_uk_<domain>` / `consolidated_uk_<domain>` / `business_uk_<domain>`)
- `datasetTypeSummary` → tenancy skill (optional — omit if `—` in table)
- `summary`, `description` → domain knowledge or mapping document
- `dataGroup`, partition labels → derived from target database / intent

**Do not show placeholder prompt to user if value exists in SKILL.md or domain knowledge.**

**Auto-Discovery**: Domain knowledge is automatically discovered and loaded during `/parse-mapping` (STEP 2.1) by looking up `target_database` in the appropriate tenancy skill to find the Feature Team Name:
- If platform = Glue → `tenancy` skill Tenancy Registry (match Hive/Iceberg Database column)
- If platform = Databricks → `databricks-tenancy` skill Tenancy Infrastructure Registry (match Target DB column)

Then searching for `${CLAUDE_PLUGIN_ROOT}/configs/domain_knowledge/{feature_team_name}_knowledge.md`. If found, it populates `domain_knowledge_text` for all downstream agents. Users can override with `--domain-knowledge` flag in `/init` (user-provided path takes precedence).

---

---

## Infrastructure Placeholders

### ~~`{{itbs}}`~~ — REMOVED (HARDCODED)
**NOTE**: The ITBS code is now **HARDCODED** to `BSN0004626` in all mesh JSON generation. This is the global BUK CDAO IT Business Service identifier — it never varies and is never provided by the user.

Previously: "I need the **ITBS code** (IT Business Service identifier) for this tenancy..."

**New behavior**: Always use `BSN0004626` in `owner.itbs`. Never ask user, never derive from tenancy.

### `{{btb_team}}`
"I need the **BTB team name** for ownership metadata.

This is the Business Technology Business (BTB) team responsible for this data product. It appears in the Mesh JSON `owner.groups[]` array for both maintenance and origination roles.
Format: varies by team, e.g., `buk_mortgage_btb`, `buk_customer_btb`, `bb_cu_fdp`, `sdw_buk_btb`.

Where to find it: **tenancy skill Mesh JSON Metadata table** (Glue — primary), or your Feature Team / Platform team assignment."

### `{{itsi_dev}}` / `{{itsi_uat}}` / `{{itsi_prd}}`
"I need the **ITSI code** for the `{env}` environment.

ITSI codes are ServiceNow Service Instance identifiers used for Netcool alerting.
Format: `SNSVC` followed by 7 digits, e.g., `SNSVC0072836`.

Where to find it: `skills/tenancy-summary/SKILL.md` tenancy table (if your tenancy is listed) or your Platform team."

### `{{compid_prd}}`
"I need the **Netcool Component ID** for production alerting.

This appears in the DTXOG config `netcool_details.compid` for the `prd` environment.
Format: uppercase string, e.g., `FDPBUKMORT`, `BUKFDPCONSCOMP`.

Where to find it: `skills/tenancy-summary/SKILL.md` tenancy table (if your tenancy is listed) or your Platform team."

### `{{sf_group}}`
"I need the **Snowflake/IAM group name** for the Glue service role.

This appears in the DTXOG config `metadata.owner.groups.sf_group` field.
Format: typically `{tenancy_name}-glue-role` or similar.

Where to find it: your Platform team or the tenancy's IAM setup documentation."

---

## Crypto Placeholders

### `{{sms_secret_name}}`
"I need the **Protegrity crypto secret name** for this tenancy.

This is used in `crypto_dpaas.secret_name` in the DTXOG config.
Derived pattern: `sms-crypto-{tenancy_name}`, e.g., `sms-crypto-fdpmortgage`.

**Important**: The exact secret name must be confirmed with your Feature Team — never assume the pattern is correct. Please provide the confirmed value."

### `{{custom_de_list}}`
"I need the **custom Data Element list** for the crypto configuration.

This is a comma-separated list of Protegrity DE names that will be loaded by the ProtectorTools package.
Format: `DE_NAME1,DE_NAME2`, e.g., `MORTGAGE_ACC_NUM,SORT_CODE`.

These DE names are extracted from the transformation logic (`cloud_api_udf_{DE_NAME}_protect/unprotect`).
I have extracted the following DE names from the mapping: `{extracted_de_names}`.

Please confirm these are correct, or provide the full list."

---

## Operational Placeholders

### `{{change_request_no}}`
"I need the **Change Request number** for the generated pipeline artefacts.

This is the ServiceNow CR number that authorises this pipeline change.
Format: `CHG` followed by 10 digits, e.g., `CHG1016737102`.

This is optional for dev/uat but mandatory for production deployments.
Type `skip` to leave as a placeholder and fill in before the production CR."

### `{{expected_completion_sla}}`
"I need the **Expected Completion SLA** for the generated pipeline artefacts.

This is the latest time by which the pipeline is expected to complete, used for late-alerting.
Format: `HHmm+<day_offset>`, e.g., `2315+1` (23:15 the next day), `0600+1` (06:00 next day).

Where to find it: your team's SLA agreement with downstream consumers.
Type `skip` to leave as `{{expected_completion_sla}}` and fill in before the production CR."

### `{{tenancy_name}}`
"I need the **tenancy name** (Feature Team Name) for this data product.

This is the Feature Team Name from the appropriate tenancy skill registry. It is normally auto-resolved by looking up `target_database`:
- Glue → `tenancy` skill Tenancy Registry (match Hive/Iceberg Database column)
- Databricks → `databricks-tenancy` skill Tenancy Infrastructure Registry (match Target DB column)
Examples: Glue: `fdpmortgage`, `fdpchnlcc`, `cdpcustomer`. Databricks: `BUK_PAFER_BDP`, `BUK_BBKYC_BDP`.

It is used in S3 bucket names, state machine names, and DTXOG config.
Please provide the confirmed tenancy name."

---

## Target Table Placeholders

### `{{target_catalog}}`
"I need the **Unity Catalog name** for the target table (Databricks only).

This is the fully-qualified Databricks Unity Catalog name.
Examples: `PRD_BUK_CUSTOMER_FDP`, `PREPRD_BUK_CUSTOMER_FDP`, `BUK_DATA_PRODUCT_CENTRAL_CATALOG`.

Please confirm the catalog name with your Databricks Platform team."

### `{{dataset_type}}`
"I need the **dataset type name** for this table.

This is used in the Mesh JSON `datasetType` and `datasetTypeSummary.name` fields. It typically follows the pattern `{database_prefix}_{domain_acronym}` or similar.
Format: typically `{target_database}_{target_table}` or a short business name, e.g., `bb_current_account_fdp`.

Where to find it: your data domain or feature team documentation."

### `{{dataset_type_summary}}`
"I need a **one-line summary** for the dataset type.

This appears in the Mesh JSON `datasetTypeSummary.summary` field.
Example: 'Business Banking Current Account Foundation Data Product'.
Keep it concise (under 60 characters if possible)."

### `{{dataset_type_description}}`
"I need a **detailed description** for the dataset type.

This appears in the Mesh JSON `datasetTypeSummary.description` field. It should explain the purpose and scope of this dataset type across the organisation.
Example: 'Cleansed, enriched Business Banking current account data ready for downstream consumption by CDPs and BDPs.'"

### `{{s3_bucket_dev}}` / `{{s3_bucket_uat}}` / `{{s3_bucket_prd}}`
"I need the **S3 bucket name** for the `{env}` environment.

This is used in the Mesh JSON `environmentProperties` to tell EDP where to create the Iceberg table.
Expected pattern (Pattern 1 — Iceberg): `{env_prefix}-pre-{tenancy_shortname}01-{account_id}-eu-west-1`

Example: `dev1-pre-fdpmortgage01-767397940910-eu-west-1`

If you provide the tenancy name and environment, I can derive this for you."

---

## Structured Transformation Logic Guidance

When a column references multiple source tables, the plugin supports **two approaches**:

1. **Structured format** (Driver Table) — deterministic, no advisory comments, recommended for complex scenarios
2. **Natural language** (free-text) — best-effort interpretation via Rule 11, advisory comments added for review

### Advisory Prompt (when `join_logic_missing = true` is detected)

"The following columns reference multiple source tables and will use natural language interpretation for join/filter logic. Generated code will include ADVISORY comments for developer review.

Columns using NL interpretation:
- `{column_name}`: references tables [{table_list}]

Generation will proceed using Rule 11 (NL Join & Filter Interpretation).

**For more deterministic output**, consider using the structured format:

```
Driver Table: <primary_table>
Driver Conditions: [<filters on driver table before joins, if subset needed>]
Join 1 Table: <second_table>
Table1 Conditions: [<pre-join filters on joined table, if subset needed>]
Join 1 Type: LEFT|INNER|RIGHT|FULL|CROSS
Join 1 Conditions: <primary_table>.<col> = <second_table>.<col>
Value: <final expression for this column>
```

**Structured format benefits:**
- Explicit join order and type (no defaulting to LEFT)
- Pre-join filters clearly separated from join conditions
- Deduplication requirements explicitly stated
- Value expression isolated from join logic
- No ADVISORY comments in generated code

**Natural language is also fully supported.** The transform generator recognizes patterns like:
- `LEFT JOIN <table> ON <condition>` — explicit join
- `Get/Lookup <col> from <table> based on <key>` — lookup join
- `Filter/Where <col> NOT IN (<values>)` — exclusion filter
- `Latest record per <key>` — dedup pattern

See `docs/structured-transformation-logic.md` for the full specification and examples."

### Join Logic Missing Detection

When the parser detects a column referencing multiple source tables without structured format, it:
1. Sets `join_logic_missing = true` on the column in `mapping_parsed.json`
2. Appends an advisory to `session_state.parse_warnings[]`
3. Emits an informational advisory during `/identify-intent` (non-blocking)
4. Transform generator proceeds with NL interpretation mode (Rule 11) — advisory comments in output

```
ℹ️ Column '{column_name}' references {N} source tables ({table_list}) — using NL
interpretation for join logic. Generated code will include ADVISORY comments.
For deterministic output, structured Driver Table format is recommended.
```
