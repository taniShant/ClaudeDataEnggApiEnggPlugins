# Per-Environment Infrastructure Resolution

All environment-varying infrastructure values are resolved **once** during `/parse-mapping` STEP 2.6 and stored in `session_state.env_config`. Downstream agents (mesh, dtxog, wrapper) consume from this centralized source — they never independently derive per-environment values.

## Why Centralized

- Eliminates redundant lookups (same value resolved once, not per-agent)
- Prevents inconsistency (one authoritative source, not per-agent derivation)
- Resolves all 3 environments (dev/uat/prd) together, not just dev

## Values Resolved Per Environment

| Field | Description | Source |
|-------|-------------|--------|
| `s3_bucket` | Full S3 bucket name | aws skill Pattern 1 (Iceberg) or Pattern 2 (Hive) |
| `aws_account_id` | AWS account ID | aws skill account table (DDA or BCA row) |
| `itsi` | ITSI code | ops skill tenancy ITSI table |
| `compid` | Netcool component ID | ops skill (prd only; null for dev/uat) |
| `crypto_account_id` | Account ID for crypto bucket | aws skill (same account type) |
| `crypto_itsi` | ITSI for crypto operations | ops skill |
| `crypto_api_endpoint_url` | Crypto API endpoint | ops skill (Crypto API Endpoints table) |

## Resolution Algorithm (STEP 2.6)

1. Parse `target_database` → extract DP type (fdp/cdp/bdp) + domain. Determine catalog type by matching `target_database` against the tenancy registry's Hive Database and Iceberg Database columns — the matched column determines the catalog type (Iceberg → Pattern 1; Hive → Pattern 2). Skip cells marked "Not available". If no match → invoke **Interactive Infrastructure Collection** (see below).
2. From the matched tenancy row → extract `bucket_shortname`, `tenancy_name`
3. Determine account type: FDP/CDP → DDA; BDP → BCA
4. **For EACH environment (dev, uat, prd):**
   - S3 bucket: account_id + env_prefix → bucket name via Pattern 1 or 2
   - AWS account ID: from aws skill account table
   - ITSI: from ops skill tenancy ITSI table
   - Compid: from ops skill (prd only)
   - Crypto account ID: same account type (DDA/BCA)
   - Crypto ITSI: from ops skill
   - Crypto API endpoint: from standards/ops skill
5. Store in `session_state.env_config`
6. Auto-populate `session_state.mesh_json_s3_locations` (marks G3 resolved)

## Environment Prefix Mapping

| Catalog Type | Dev | UAT | Prd |
|---|---|---|---|
| Iceberg | `dev1` | `uat1` | `prd1` |
| Hive | `dev` | `uat` | `prd` |

## S3 Bucket Name Patterns

**Pattern 1 — Iceberg (Pre-Integration Landing)**:
```
{env_prefix}-pre-{bucket_shortname}-{account_id}-eu-west-1
```
Example: `dev1-pre-fdpmortgage01-767397940910-eu-west-1`

**Pattern 2 — Hive (DP-type prefixed)**:
```
{env_prefix}-{dp_type}-{bucket_shortname}-{account_id}-eu-west-1
```
Example: `dev-fdp-fdpmortgage01-767397940910-eu-west-1`

### Catalog Type Determination

Catalog type is determined by which column in the tenancy registry the `target_database` matches:

| `target_database` matched in column | Catalog Type | Env Prefix | Bucket Pattern |
|---|---|---|---|
| Iceberg Database | Iceberg | dev1/uat1/prd1 | Pattern 1 |
| Hive Database | Hive | dev/uat/prd | Pattern 2 |

Examples:
- `fdp_uk_mortgage_db` → matches Hive Database column of `fdpmortgage` → Hive
- `fdp_uk_mortgage_db_iceberg` → matches Iceberg Database column of `fdpmortgage` → Iceberg
- `fdp_uk_coll_rcovry_db` → matches Iceberg Database column of `fdpcolrcvy` → Iceberg
- `cdp_uk_nps_db` → matches Iceberg Database column of `cdpnps` → Iceberg

## Account ID Lookup

| Account Type | Dev | UAT | Prd |
|---|---|---|---|
| DDA (FDP/CDP) | 767397940910 | 590184123059 | 194722397519 |
| BCA (BDP) | 998403225349 | 105695603553 | 233301737440 |

## Domain Knowledge Override Precedence

If domain knowledge provides explicit overrides for any env-specific value, those take precedence over auto-derived values. Check domain knowledge FIRST.

Supported overrides:
- `s3_bucket_dev`, `s3_bucket_uat`, `s3_bucket_prd`
- `itsi_dev`, `itsi_uat`, `itsi_prd`
- `compid_prd`
- `crypto_package_path_dev`, `crypto_package_path_uat`, `crypto_package_path_prd`

## Downstream Consumption

| Agent | Fields Used |
|-------|------------|
| glue-mesh-agent | `mesh_json_s3_locations` (auto-populated from env_config) |
| glue-dtxog-agent | `s3_bucket`, `aws_account_id`, `itsi`, `compid`, `crypto_account_id` |
| glue-wrapper-agent | `crypto_itsi`, `crypto_api_endpoint_url` |

## Fallback: Interactive Infrastructure Collection

When `target_database` is not matched in the tenancy registry (step 1 of the resolution algorithm returns no match):

1. The system does **NOT** halt
2. Auto-derives all fixed/constant values: AWS account IDs (from account type), crypto API endpoints, source catalogs (Databricks), workspace hosts (Databricks)
3. **Asks the user interactively** for tenancy-specific values via the platform-specific questionnaire:
   - **Glue**: `prompts/infrastructure-questionnaire-glue.md` — Q1–Q2 + Q3g–Q6g (bucket_shortname, catalog_type, ITSI codes, compid)
   - **Databricks**: `prompts/infrastructure-questionnaire-databricks.md` — Turn 1–5 batched flow (feature team, catalogs, workspace/SPs, security/tagging, confirmation)
4. Each turn is presented and the system **waits for the user's response** before proceeding to the next turn
5. Values that are **NEVER derived from naming conventions**: service principals, target catalogs, workspace folders — if the user skips, `{{placeholder}}` values are retained
6. **Per-environment ITSI and FIN:Role**: These values may differ per environment (e.g., BUK_BBKYC_BDP: DEV=SNSVC0081840, PRD=SNSVC0081846). The questionnaire asks for each environment separately.
7. **Notification email** (Databricks only): New field used in `databricks.yml.template` (5 places) and all 5 job templates. Default: `BUKDataPlatformDatabricks@barclays.com`
8. Derives S3 buckets (Glue) from user-provided bucket_shortname + known account IDs + catalog_type
9. Presents a **Confirmation Summary** for user review before storing values
10. The resulting `env_config` / `dbx_config` has the **identical schema** to registry-resolved values
11. Downstream agents consume `env_config` / `dbx_config` identically regardless of resolution method

### Tenancy Resolution Method Tracking

`session_state.tenancy_resolution_method` records how infrastructure values were obtained:

| Value | Meaning |
|---|---|
| `"registry"` | Resolved from tenancy skill (standard path) |
| `"domain_knowledge"` | Resolved from domain knowledge overrides |
| `"user_provided"` | Collected via interactive infrastructure questionnaire |

### Safety Notes

- User-provided values bypass registry validation — the confirmation summary step ensures the user reviews all values before proceeding
- Any skipped values are retained as `{{placeholder}}` — **never fabricated**
- Artefacts with unresolved placeholders are marked `DRAFT_UNVALIDATED`
- The existing `infrastructure-validator` still runs and flags format mismatches
- Anti-hallucination guardrails remain enforced

## Session State Structure

```json
{
  "env_config": {
    "tenancy_name": "fdpmortgage",
    "catalog_type": "iceberg",
    "bucket_shortname": "fdpmortgage01",
    "account_type": "DDA",
    "domain": "Mortgage",
    "tenancy_resolution_method": "registry",
    "dev": {
      "s3_bucket": "dev1-pre-fdpmortgage01-767397940910-eu-west-1",
      "aws_account_id": "767397940910",
      "itsi": "SNSVC0072836",
      "compid": null,
      "crypto_account_id": "767397940910",
      "crypto_itsi": "SNSVC0072836",
      "crypto_api_endpoint_url": "https://rvv79qtyhc.execute-api.eu-west-1.amazonaws.com/development/v1"
    },
    "uat": {
      "s3_bucket": "uat1-pre-fdpmortgage01-590184123059-eu-west-1",
      "aws_account_id": "590184123059",
      "itsi": "SNSVC0072837",
      "compid": null,
      "crypto_account_id": "590184123059",
      "crypto_itsi": "SNSVC0072837",
      "crypto_api_endpoint_url": "https://b3sdxfbp85.execute-api.eu-west-1.amazonaws.com/qa/v1"
    },
    "prd": {
      "s3_bucket": "prd1-pre-fdpmortgage01-194722397519-eu-west-1",
      "aws_account_id": "194722397519",
      "itsi": "SNSVC0073328",
      "compid": "FDPBUKMORT",
      "crypto_account_id": "194722397519",
      "crypto_itsi": "SNSVC0073328",
      "crypto_api_endpoint_url": "https://l3s21rqu32.execute-api.eu-west-1.amazonaws.com/production/v1"
    }
  }
}
```

---

## DV Stage — Databricks Catalog Resolution

Data Validation (Stage 4) has its own catalog resolution mechanism for Databricks, separate from the Stage 3 centralized `env_config` approach.

### Why Separate

- DV generates standalone SQL files with no runtime driver — catalog names must be embedded at generation time
- DV can run independently of Stage 3 (standalone mode with `--excel`)
- DV resolves for ONE environment per invocation (`--env`), not all environments at once

### Resolution Model

| Priority | Source | Condition |
|----------|--------|-----------|
| 1 | DE session state (`env_config.{env}.target_catalog`) | Dependent mode only |
| 2 | Tenancy registry (match `target_database` → Write/Target Catalog + Source Catalog) | Match by Target DB column |
| 3 | Ask user (source pre-filled from env table, target user-supplied) | Registry match failed or value is TBD |

Source catalogs: resolved from the matched tenancy row's "Source Catalog" column (may differ from the per-environment default — e.g., `TSC_CUSTOMER_FDP` uses `077382350852_glue_shared_catalog_sierra`). Falls back to fixed env table default if no row match or row value matches default.

Target catalogs: resolved from the matched tenancy row's "Write/Target Catalog" column. If TBD or no match, user is asked — no automated derivation.

### Source Catalog (Default per Environment)

Default source catalogs from `databricks-tenancy` skill (overridable by matched tenancy row):

| Environment | Default Source Catalog |
|---|---|
| dev | `077382350852_buk_data_products` |
| preprd | `buk_data_product_central_catalog` |
| prd | `buk_data_product_central_catalog` |
| uat | `279373726337_buk_data_products_uat` |

### Session State

Resolution is stored in `dv_session_state.json` under `databricks_catalog_resolution` (not in `session_state.env_config`).

### Limitation

V1 supports a single source catalog per environment (`source_catalog_1`). Multi-source-catalog scenarios (`source_catalog_2`, etc.) are deferred.

### Null-Safety Guarantees

The DV pipeline enforces defense-in-depth to prevent null catalog values from reaching SQL:

| Layer | File | Behavior on Null |
|---|---|---|
| Step 0.5 Gate | `dv-generate.md` § 0.5.5b | HALT with actionable error |
| Step 1 Pre-condition | `dv-generate.md` § Step 1 | HALT if catalogs missing |
| Plan Agent | `dv-validation-plan-agent.md` | Mark plan BLOCKED, empty checks[] |
| Renderer Agent | `dv-databricks-renderer-agent.md` | Write stub SQL, HALT |
| Schema | `dv_session_state.schema.json` | Conditional `required` via if/then |

The Step 0.5 Gate is the primary defense. Downstream guards are safety nets that should not fire in normal operation.

### Token Substitution

The renderer agent MUST substitute `{{source_catalog}}`, `{{target_catalog}}`, `{{source_schema}}`, `{{target_schema}}` from the SQL pattern templates with actual resolved values from the plan's `parameters{}`. The only permitted surviving `{{...}}` token in rendered SQL is `{{control_date}}`.
