# Validator: dtxog-structure-validator

**Purpose**: Validate the dtxog config JSON structure. Ensure all required keys are present and crypto block is correctly configured when crypto is active.

**Severity**: DRAFT_UNVALIDATED if incomplete — list violations.

**Platform**: Glue only

---

## Checks

### Check 1 — Required Top-Level Keys

`metadata`, `services`, `dtxog-byoc` must all be present.

### Check 2 — services Block

All three service flags present and valid:
- `services.dtxoh: "false"` (must be "false" for BYOC — this is Glue, not Hadoop)
- `services.dtxog: "false"` (must be "false" — BYOC mode uses dtxog-byoc, not dtxog)
- `services.dtxog-byoc: "true"` (BYOC pattern)

### Check 3 — app_details Environments

`dtxog-byoc.app_details.env` must contain all three: `dev`, `uat`, `prd`.

For each env block:
- `state_machine` — non-empty string
- `netcool_details.sev`, `netcool_details.itsi`, `netcool_details.compid` — non-empty
- `glue_args.worker-type`, `number-of-workers`, `timeout`, `max-retries` — non-empty
- `glue_args.xtra-args.sparkConf` — non-empty (Iceberg SparkConf required)
- `byoc.wrapper-file` — non-empty, comma-separated S3 paths (wrapper.py and .whl; must NOT contain config.json)
- `byoc.package-cnfg` — non-empty S3 path to config.json (must NOT be "NA"); pattern: `apps/pkg/[{source_system}/]conf/{database_name}/{table_name}/config.json`

### Check 4 — Crypto Block (conditional — only present in crypto template variant)

When `session/crypto_flags.json → any_column_crypto_flagged = true`:
- `crypto_dpaas` block MUST be present in each env (comes from crypto template variant)
- For ALL envs: `crypto_dpaas.enable_crypto_api` must equal `"true"`
- `crypto_dpaas.secret_name` — non-empty (may be placeholder `{{sms_secret_name}}`)
- `crypto_dpaas.custom_de_list` — non-empty; contains at least one DE name (never a placeholder)
- `crypto_dpaas.log_level` — non-empty (typically `"info"`)
- `byoc.wrapper-file` must include crypto package path as additional comma-separated entry

When `any_column_crypto_flagged = false`:
- `crypto_dpaas` block MUST NOT be present (non-crypto template does not include it)
- `byoc.package-file` must equal `"NA"`
- `byoc.package-cnfg` must be a valid S3 path to config.json (never `"NA"`)

### Check 5 — No Cross-Environment Values

dev bucket names must not appear in prd block, and vice versa. Run `infrastructure-validator` (Part B) as sub-check.

### Check 6 — Naming Convention

File must follow naming: `{target_database}_{target_table}_dtxog.json` (lowercase).

---

## Pass Condition

All 6 checks pass.

## Fail Action

Mark DRAFT_UNVALIDATED. List violations:
```
❌ dtxog validation failed:
   Check 4: crypto_dpaas.enable_crypto_api is "false" but column 'account_number' is crypto-flagged — must be "true"
   Check 4: custom_de_list is empty — should be auto-assembled from DE names
```
