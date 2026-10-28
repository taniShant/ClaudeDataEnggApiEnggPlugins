# Infrastructure Questionnaire — Glue/AWS Platform

Standard prompts for collecting **all required infrastructure values** when `target_database` is not found in the Glue/AWS tenancy registry during `/parse-mapping` STEP 2.7.

## When Used

Invoked when `target_database` (normalized: case-insensitive, whitespace-trimmed) cannot be matched against:
- **Glue/AWS**: Hive Database or Iceberg Database columns in `aws-tenancy` skill

For Databricks tenancy questionnaire, see `infrastructure-questionnaire-databricks.md`.

## CRITICAL: Interactive & Sequential Execution

Each question is presented as a **single conversational turn**. The system presents ONE question, waits for the user's response, stores it, then proceeds to the next question. Per-environment values (e.g., ITSI codes for dev/uat/prd) are grouped within a single turn.

- The system MUST **wait for the user's response** before proceeding to the next question
- Environment-specific values MUST be asked interactively — **never skipped, never assumed**
- The system MUST NOT proceed to artefact generation until all questions have been presented and answers collected
- After all questions, present a **Confirmation Summary** (see below) and wait for user to confirm before storing values

**CRITICAL — Indivisible Execution:** This questionnaire is a SINGLE INDIVISIBLE UNIT.
Once you begin presenting questions:
- You MUST present all questions sequentially (Q1 → Q2 → Q3g → Q4g → Q5g → Q6g → Confirmation)
  without exiting or yielding to the orchestrator between questions. Waiting for user input between questions is expected and required — "indivisible" means you must not exit the agent context or treat a partial question count as completion.
- Completing Q1 does NOT constitute questionnaire completion.
- The questionnaire is ONLY complete when:
  1. All questions have been presented
  2. User answers collected for each question
  3. Confirmation Summary presented and user confirmed
  4. `questionnaire_turns_completed: 6` written to `session_state.env_config`
- If resumed via SendMessage after a mid-questionnaire interruption, continue from
  the next unasked question — do not restart and do not treat the previous question as completion.

## Domain Knowledge Override Precedence

Before asking each question:
1. **Check domain knowledge** for an explicit override for that field
2. If domain knowledge provides a value → **use it silently, skip that question**
3. If ALL required values are provided by domain knowledge → skip the entire questionnaire with info log:
   ```
   ℹ️ Target database '{target_database}' not found in tenancy registry, but domain knowledge 
   provides all required infrastructure values. Using domain knowledge overrides.
   ```

### Domain Knowledge Short-Circuit

If `session_state.domain_knowledge_text` is null or empty at questionnaire start:
- **Skip ALL per-question domain knowledge checks below**
- Present every question directly without checking for overrides

---

## Phase 0 — Auto-Derive (No Questions Asked)

The following values are **fixed constants** and are auto-derived without user interaction:

| Field | Derivation | Source |
|-------|-----------|--------|
| `data_product_type` | From `target_database` prefix: `fdp_` → FDP, `cdp_` → CDP, `bdp_` → BDP, `shared_fdp_` → FDP, `shared_cdp_` → CDP, `shared_bdp_` → BDP | STEP G1.5 (already resolved) |
| `account_type` | FDP/CDP → DDA; BDP → BCA | Derived from DP type |
| `aws_account_id` (per env) | Fixed per account_type per env (see Account ID table below) | `aws-data-products` skill |
| `crypto_api_endpoint_url` (per env) | Fixed across all tenancies (see Crypto Endpoints table below) | `service-management` skill |

### Account ID Lookup (Fixed)

| Account Type | Dev | UAT | Prd |
|---|---|---|---|
| DDA (FDP/CDP) | 767397940910 | 590184123059 | 194722397519 |
| BCA (BDP) | 998403225349 | 105695603553 | 233301737440 |

### Crypto API Endpoints (Fixed)

| Environment | Endpoint |
|---|---|
| dev | `https://rvv79qtyhc.execute-api.eu-west-1.amazonaws.com/development/v1` |
| uat | `https://b3sdxfbp85.execute-api.eu-west-1.amazonaws.com/qa/v1` |
| prd | `https://l3s21rqu32.execute-api.eu-west-1.amazonaws.com/production/v1` |

---

## Sequential Questions — Q1–Q2

### Q1 — Feature Team Name (standalone turn)

```
⚠️ Target database '{target_database}' was not found in the tenancy registry.

Q1. **Feature Team Name** (tenancy name) — REQUIRED
This is the team identifier used in workspace folders, catalog names, job names, and bundle config.
Examples: BUK_PAFER_BDP, BUK_BBKYC_BDP, BUK_MORTGAGES_CDP, fdpchnlcc

Feature Team Name: 
```

| User Answer | Stored In | Blocking? |
|---|---|---|
| Feature Team Name | `session_state.env_config.tenancy_name` + `session_state.tenancy_name` | **YES** — re-prompt once if skipped |

Wait for response before Q2.

### Q2 — Domain Name (standalone turn)

```
Q2. **Domain Name** — optional (type 'skip' to use placeholder)
The business domain this data product belongs to.
Examples: Mortgage, Complaints, Customer, Regulatory, Business Banking, Insurance

Domain Name: 
```

| User Answer | Stored In | Blocking? |
|---|---|---|
| Domain Name | `session_state.env_config.domain` | No — `{{domain_name}}` placeholder if skipped |

Wait for response before next question.

---

## Sequential Questions — Glue-Specific (Q3g–Q6g)

### Q3g — S3 Bucket Shortname (standalone turn)

```
Q3. **S3 Bucket Shortname** — REQUIRED
The shortname used in S3 bucket path construction.
Examples: fdpmortgage01, cdpcustomer01, bdpsavings01, fdpcolrcvy01

S3 Bucket Shortname: 
```

| User Answer | Stored In | Blocking? |
|---|---|---|
| S3 Bucket Shortname | `session_state.env_config.bucket_shortname` | **YES** — cannot derive S3 buckets without it. Re-prompt once if skipped. |

Wait for response before Q4g.

### Q4g — Catalog Type (standalone turn)

```
Q4. **Catalog Type** — REQUIRED (iceberg or hive)
Determines S3 bucket naming pattern and environment prefixes.
• iceberg — env prefixes: dev1/uat1/prd1, bucket pattern: {env}-pre-{shortname}-{account_id}-eu-west-1
• hive — env prefixes: dev/uat/prd, bucket pattern: {env}-{dp_type}-{shortname}-{account_id}-eu-west-1

Catalog Type: 
```

| User Answer | Stored In | Blocking? |
|---|---|---|
| Catalog Type | `session_state.env_config.catalog_type` | **YES** — cannot determine env prefix or bucket pattern. Re-prompt once if skipped. |

Wait for response before Q5g.

### Q5g — ITSI Codes per env (standalone turn, grouped dev/uat/prd)

```
Q5. **ITSI Codes** (per environment) — optional
type 'skip' for placeholder
ServiceNow Service Instance identifiers for Netcool alerting.
Format: SNSVC followed by 7 digits.
Examples: dev: SNSVC0072836, uat: SNSVC0072837, prd: SNSVC0073328

dev ITSI: 
uat ITSI: 
prd ITSI: 
```

| User Answer | Stored In | Blocking? |
|---|---|---|
| ITSI dev | `session_state.env_config.dev.itsi` + `.crypto_itsi` | No — `{{itsi_dev}}` placeholder retained |
| ITSI uat | `session_state.env_config.uat.itsi` + `.crypto_itsi` | No — `{{itsi_uat}}` placeholder retained |
| ITSI prd | `session_state.env_config.prd.itsi` + `.crypto_itsi` | No — `{{itsi_prd}}` placeholder retained |

Wait for response before Q6g.

### Q6g — Production Compid (standalone turn)

```
Q6. **Production Compid** — optional (type 'skip' for placeholder)
Netcool Component ID for production alerting, used in DTXOG netcool_details.compid.
Examples: FDPBUKMORT, BUKFDPCONSCOMP, CDPBUKCUST

Production Compid: 
```

| User Answer | Stored In | Blocking? |
|---|---|---|
| Compid | `session_state.env_config.prd.compid` | No — `{{compid_prd}}` placeholder retained |

### S3 Bucket Derivation (After Q3g–Q4g Answers)

Once `bucket_shortname` + `catalog_type` are provided, derive per-env S3 buckets:

**Iceberg (Pattern 1):**
```
{env_prefix}-pre-{bucket_shortname}-{account_id}-eu-west-1
```
- dev: `dev1-pre-{shortname}-{dev_account_id}-eu-west-1`
- uat: `uat1-pre-{shortname}-{uat_account_id}-eu-west-1`
- prd: `prd1-pre-{shortname}-{prd_account_id}-eu-west-1`

**Hive (Pattern 2):**
```
{env_prefix}-{dp_type}-{bucket_shortname}-{account_id}-eu-west-1
```
- dev: `dev-{dp_type}-{shortname}-{dev_account_id}-eu-west-1`
- uat: `uat-{dp_type}-{shortname}-{uat_account_id}-eu-west-1`
- prd: `prd-{dp_type}-{shortname}-{prd_account_id}-eu-west-1`

Also set:
- `crypto_account_id` per env = same as `aws_account_id` per env
- `crypto_itsi` per env = same as `itsi` per env (if provided)
- `crypto_api_endpoint_url` per env = from fixed constants (Phase 0)

---

## Confirmation Summary

After all questions are collected, present a **confirmation summary** and **WAIT for user confirmation** before storing values in session state:

```
✅ Infrastructure Summary for '{target_database}':

  Feature Team Name:  {tenancy_name}
  Domain:             {domain_name | {{domain_name}}}
  Platform:           Glue
  Data Product Type:  {dp_type} (auto-derived from prefix)
  Account Type:       {account_type} (auto-derived)
  Catalog Type:       {catalog_type}
  
  S3 Bucket Shortname: {bucket_shortname}
  S3 Dev:  {derived_s3_dev}
  S3 UAT:  {derived_s3_uat}
  S3 PRD:  {derived_s3_prd}
  
  AWS Account IDs:  dev={dev_id}, uat={uat_id}, prd={prd_id} (auto-derived)
  
  ITSI Dev:  {itsi_dev | {{itsi_dev}}}
  ITSI UAT:  {itsi_uat | {{itsi_uat}}}
  ITSI PRD:  {itsi_prd | {{itsi_prd}}}
  Compid PRD: {compid_prd | {{compid_prd}}}
  
  Values shown as {{placeholder}} will need manual resolution before deployment.
  Artefacts with unresolved placeholders will be marked DRAFT_UNVALIDATED.
  
  Confirm and proceed? (yes / no — to re-enter values)
```

### On Confirmation

- **yes** → Store all values in `session_state.env_config`. Set `session_state.tenancy_resolution_method = "user_provided"`. Write `session_state.env_config.questionnaire_turns_completed = 6`. Continue with STEP 2.7 remainder.
- **no** → Re-present all questions from the beginning for the user to correct values.

---

## Partial Answer Handling

For each question:
- If user provides a value → store it directly in session state
- If user types `skip` or leaves empty → store `null`; downstream uses `{{placeholder}}`
- Anti-hallucination: **NEVER guess or fabricate any skipped value**
- Artefacts with any `{{placeholder}}` are marked `DRAFT_UNVALIDATED`

### Per-Environment Partial Answer Rules

When a per-environment question asks for values across dev/uat/prd (Q5g ITSI codes):

1. **Each environment is independent** — a provided value for one env does NOT imply the same value for another env
2. **If an env field is left blank or empty** → treat as `skip`: store null → `{{placeholder}}`. Do NOT ask a follow-up sub-question or replicate another environment's value.
3. **Storage**:
   - Provided value → store as-is
   - Blank or empty → store null → `{{placeholder}}`

### Truly Blocking Fields (Re-prompt Once)

| Field | Why Blocking | If Still Skipped After Re-prompt |
|---|---|---|
| `tenancy_name` | Cannot construct S3 bucket names, state machine names, job folders, SMS secret | Proceed with `{{tenancy_name}}` placeholder throughout; ALL artefacts marked `DRAFT_UNVALIDATED` |
| `bucket_shortname` | Cannot derive any S3 bucket path | Proceed with `{{s3_bucket_dev/uat/prd}}` placeholders; Glue artefacts marked `DRAFT_UNVALIDATED` |
| `catalog_type` | Cannot determine env prefix (dev1 vs dev) or bucket pattern (Pattern 1 vs 2) | Proceed with `{{catalog_type}}` placeholder; S3 buckets cannot be derived; Glue artefacts marked `DRAFT_UNVALIDATED` |

### Non-Blocking Fields (Placeholder if Skipped)

| Field | Placeholder Used | Downstream Impact |
|---|---|---|
| `domain_name` | `{{domain_name}}` | Mesh JSON metadata incomplete; non-critical |
| `itsi_{env}` | `{{itsi_dev}}` / `{{itsi_uat}}` / `{{itsi_prd}}` | DTXOG Netcool alerting config incomplete |
| `compid_prd` | `{{compid_prd}}` | Production Netcool monitoring config incomplete |

---

## Audit Trail

Log all user-provided values to `session/audit_log.jsonl`:

```json
{
  "timestamp": "<ISO 8601>",
  "event": "infrastructure_questionnaire_completed",
  "reason": "tenancy_not_found_in_registry",
  "target_database": "{target_database}",
  "tenancy_resolution_method": "user_provided",
  "values_provided": ["tenancy_name", "bucket_shortname", "catalog_type", ...],
  "values_skipped": ["domain_name", "itsi_dev", ...],
  "platform": "glue"
}
```
