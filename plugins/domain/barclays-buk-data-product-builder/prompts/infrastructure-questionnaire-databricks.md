# Infrastructure Questionnaire — Databricks Platform

Standard prompts for collecting **all required infrastructure values** when `target_database` is not found in the Databricks tenancy registry during `/parse-mapping` STEP 2.7.

## When Used

Invoked when `target_database` (normalized: case-insensitive, whitespace-trimmed) cannot be matched against:
- **Databricks**: Target DB column in `databricks-tenancy` skill

For Glue/AWS tenancy questionnaire, see `infrastructure-questionnaire-glue.md`.

## CRITICAL: Interactive Execution

Questions are presented in **batched turns** — related questions are grouped together in a single conversational turn. The system presents one batch, waits for the user's response, stores values, then proceeds to the next batch.

- The system MUST **wait for the user's response** before proceeding to the next turn
- Environment-specific values MUST be asked interactively — **never skipped, never assumed**
- The system MUST NOT proceed to artefact generation until all turns have been presented and answers collected
- After all turns, present a **Confirmation Summary** and wait for user to confirm before storing values

**CRITICAL — Indivisible Execution:** This questionnaire is a SINGLE INDIVISIBLE UNIT.
Once you begin presenting turns:
- You MUST present all 5 turns sequentially (Turn 1 → Turn 2 → Turn 3 → Turn 4 → Turn 5 Confirmation)
  without exiting or yielding to the orchestrator between turns. Waiting for user input between turns is expected and required — "indivisible" means you must not exit the agent context or treat a partial turn count as completion.
- Completing Turn 1 does NOT constitute questionnaire completion.
- The questionnaire is ONLY complete when:
  1. All 5 turns have been presented
  2. User answers collected for each turn
  3. Turn 5 Confirmation Summary presented and user confirmed
  4. `questionnaire_turns_completed: 5` written to `session_state.dbx_config`
- If resumed via SendMessage after a mid-questionnaire interruption, continue from
  the next unasked turn — do not restart and do not treat the previous turn as completion.

## Domain Knowledge Override Precedence

Before presenting each batched turn:
1. **Check domain knowledge** for explicit overrides for ALL fields in that batch
2. If domain knowledge provides a value for a field → **use it silently, skip that question** within the batch
3. If ALL fields in a batch are resolved by domain knowledge → **skip the entire turn**
4. If ALL required values across all turns are provided by domain knowledge → skip the entire questionnaire with info log:
   ```
   ℹ️ Target schema '{target_database}' not found in tenancy registry, but domain knowledge 
   provides all required infrastructure values. Using domain knowledge overrides.
   ```

### Domain Knowledge Short-Circuit

If `session_state.domain_knowledge_text` is null or empty at questionnaire start:
- **Skip ALL per-turn domain knowledge checks below**
- Present every turn directly without checking for overrides

---

## Phase 0 — Auto-Derive (No Questions Asked)

The following values are **fixed constants** and are auto-derived without user interaction:

| Field | Derivation | Source |
|-------|-----------|--------|
| `data_product_type` | From `target_database` prefix: `fdp_` → FDP, `cdp_` → CDP, `bdp_` → BDP, `shared_fdp_` → FDP, `shared_cdp_` → CDP, `shared_bdp_` → BDP | STEP G1.5 (already resolved) |
| `account_type` | FDP/CDP → DDA; BDP → BCA | Derived from DP type |
| `source_catalog` (per env) | DEV/UAT: `077382350852_buk_data_products`; PREPRD/PRD: `buk_data_product_central_catalog` | `databricks-tenancy` skill (fixed) |
| `workspace_host` (per env) | DEV: `https://dev-buk-uk.cloud.databricks.com/`; PREPRD: `https://prod-buk-parallel-uk.cloud.databricks.com/`; PRD: `https://prod-buk-prod-uk.cloud.databricks.com` | `databricks-tenancy` skill (fixed) |
| `policy_id` (per env) | DEV: `00186E9BB6908351`; PREPRD: `000CB013172B29C7`; PRD: `000A02890D1F23ED` | `databricks-tenancy` skill (fixed) |

---

## Turn 1 — Feature Team Name (standalone, BLOCKING)

```
⚠️ Target schema '{target_database}' was not found in the tenancy registry.

Q1. **Feature Team Name** (tenancy name) — REQUIRED
This is the team identifier used in workspace folders, catalog names, job names, and bundle config.
Examples: BUK_PAFER_BDP, BUK_BBKYC_BDP, BUK_MORTGAGES_CDP, fdpchnlcc

Feature Team Name: 
```

| User Answer | Stored In | Blocking? |
|---|---|---|
| Feature Team Name | `session_state.dbx_config.tenancy_name` + `session_state.tenancy_name` | **YES** — re-prompt once if skipped |

Wait for response before Turn 2.

---

## Turn 2 — Identity & Catalogs (Q2 + Q3)

```
**Identity & Target Catalogs**

Q2. **Domain Name** — optional (type 'skip' to use placeholder)
The business domain this data product belongs to.
Examples: Mortgage, Complaints, Customer, Regulatory, Business Banking, Insurance

Domain Name: 

Q3. **Target Catalogs** (Unity Catalog write/target catalog per env)
type 'skip' for placeholder
Examples: dev: dev_buk_pafer_bdp, preprd: preprd_buk_pafer_bdp, prd: prd_buk_pafer_bdp

dev: 
preprd: 
prd: 
```

**Q3 — When asked**: Q3 is asked only when `target_catalog` could not be fully resolved from the `databricks-tenancy` skill during `/parse-mapping` STEP 2.7. This happens when:
- The skill's **Write/Target Catalog** column returns `TBD` or `NA` for one or more environments
- The tenancy was not found in the skill at all (full questionnaire fallback)

If the skill already resolved `target_catalog` for ALL environments → **skip Q3**, present only Q2 in this turn.

If the skill resolved some but not all environments → pre-fill the resolved envs and ask only for the missing ones.

| User Answer | Stored In | Blocking? |
|---|---|---|
| Domain Name | `session_state.dbx_config.domain` | No — `{{domain_name}}` placeholder if skipped |
| Target Catalogs (per env) | `session_state.dbx_config.{env}.target_catalog` | No — `{{*_target_catalog}}` placeholder retained. **NEVER derive.** |

**NO derivation from naming convention** — if user skips, retain placeholder.

Wait for response before Turn 3.

---

## Turn 3 — Workspace & Service Principals (Q4 + Q5 + Q6)

All Databricks tenancy-specific values MUST be asked from the user. They are **NEVER derived from naming conventions**. If the user skips any value → retain `{{placeholder}}` and mark artefacts `DRAFT_UNVALIDATED`.

```
**Workspace & Service Principal Infrastructure**
type 'skip' for any to use placeholders

Q4. **Workspace Folders** (per env)
Examples: dev: DEV_BUK_PAFER_BDP, preprd: PREPRD_BUK_PAFER_BDP, prd: PRD_BUK_PAFER_BDP

dev: 
preprd: 
prd: 

Q5. **CICD Service Principals** (per env)
Examples: dev: buk_pafer_bdp_cicd_dev_sp, preprd: buk_pafer_bdp_cicd_preprd_sp, prd: buk_pafer_bdp_cicd_prd_sp

dev: 
preprd: 
prd: 

Q6. **Exec Service Principals** (per env)
Examples: dev: buk_pafer_bdp_exec_dev_sp, preprd: buk_pafer_bdp_exec_preprd_sp, prd: buk_pafer_bdp_exec_prd_sp

dev: 
preprd: 
prd: 
```

| User Answer | Stored In | Blocking? |
|---|---|---|
| Workspace Folders (per env) | `session_state.dbx_config.{env}.workspace_folder` | No — `{{*_ws_root}}` placeholder retained |
| CICD SPs (per env) | `session_state.dbx_config.{env}.cicd_sp` | No — `{{*_cicd_sp}}` placeholder retained. **NEVER derive.** |
| Exec SPs (per env) | `session_state.dbx_config.{env}.exec_sp` | No — `{{*_exec_sp}}` placeholder retained. **NEVER derive.** |

**NO derivation from SP naming convention** — if user skips, retain placeholder.

Wait for response before Turn 4.

---

## Turn 4 — Security, Tagging & Notification (Q7 + Q8 + Q9 + Q10)

```
**Security, Tagging & Notification**
type 'skip' for any to use placeholders

Q7. **AD Groups** (Azure AD security groups per env) — optional
May have multiple groups separated by ' / '.
Examples: dev: GLO-CLI-SEC-AZADDBXBUKBBSOFDDE / fglbAZADDBXBUKSOFDDE, preprd: GLO-CLI-SEC-AZADDBXBUKRTBSDE / glo-cli-sec-AZADDBXBUKBBSOFSDE, prd: GLO-CLI-SEC-AZADDBXBUKRTBPDE / glo-cli-sec-AZADDBXBUKBBSOFPDE

dev: 
preprd: 
prd: 

Q8. **ITSI** (IT Service Instance for APP:ApplicationService tag, per env)
Format: SNSVC followed by 7 digits. May differ per environment.
Examples: dev: SNSVC0081840, preprd: SNSVC0081846, prd: SNSVC0081846

dev: 
preprd: 
prd: 

Q9. **FIN:Role Tag** (composite tag, per env)
Format: {ITSI}_{Use_Case_Jira_ID}_{Feature_Team_Name}. Differs per environment (ITSI may differ per env).
Examples: 
  dev: SNSVC0081840_EDPUC-1597_BUK_BBKYC_BDP
  preprd: SNSVC0081846_EDPUC-1597_BUK_BBKYC_BDP
  prd: SNSVC0081846_EDPUC-1597_BUK_BBKYC_BDP

dev: 
preprd: 
prd: 

Q10. **Notification Email** — type 'skip' for default
Email for job success/failure notifications.
Default: BUKDataPlatformDatabricks@barclays.com (press Enter to use default)

Notification email: 
```

| User Answer | Stored In | Blocking? |
|---|---|---|
| AD Groups (per env) | `session_state.dbx_config.{env}.ad_group` | No — `{{*_ad_group}}` placeholder retained |
| ITSI (per env) | `session_state.dbx_config.{env}.app_service_tag` | No — `{{*_app_service_tag}}` placeholder retained |
| FIN:Role Tag (per env) | `session_state.dbx_config.{env}.fin_role_tag` | No — `{{*_fin_role_tag}}` placeholder retained |
| Notification Email | `session_state.dbx_config.notification_email` | No — default `BUKDataPlatformDatabricks@barclays.com` if skipped or Enter |

Note: ITSI (`{{app_service_tag}}`) and FIN:Role (`{{fin_role_tag}}`) template placeholders in job templates must be resolved per-environment during gen-bundle.

Used in: `databricks.yml.template` (5 places) + all 5 job templates.

Wait for response before Confirmation Summary.

---

## Turn 5 — Confirmation Summary

After all turns are completed, present a **confirmation summary** and **WAIT for user confirmation** before storing values in session state:

```
✅ Infrastructure Summary for target schema '{target_database}':

| Field            | dev              | preprd           | prd              |
|------------------|------------------|------------------|------------------|
| Feature Team     | {tenancy_name}   |                  |                  |
| Domain           | {domain | {{domain_name}}} |         |                  |
| DP Type          | {dp_type} (auto) |                  |                  |
| Target Catalog   | {dev_cat | {{dev_target_catalog}}} | {preprd_cat | {{preprd_target_catalog}}} | {prd_cat | {{prd_target_catalog}}} |
| Workspace Folder | {dev_ws | {{dev_ws_root}}} | {preprd_ws | {{preprd_ws_root}}} | {prd_ws | {{prd_ws_root}}} |
| CICD SP          | {dev_cicd | {{dev_cicd_sp}}} | {preprd_cicd | {{preprd_cicd_sp}}} | {prd_cicd | {{prd_cicd_sp}}} |
| Exec SP          | {dev_exec | {{dev_exec_sp}}} | {preprd_exec | {{preprd_exec_sp}}} | {prd_exec | {{prd_exec_sp}}} |
| AD Group         | {dev_ad | {{dev_ad_group}}} | {preprd_ad | {{preprd_ad_group}}} | {prd_ad | {{prd_ad_group}}} |
| ITSI             | {dev_itsi | {{dev_app_service_tag}}} | {preprd_itsi | {{preprd_app_service_tag}}} | {prd_itsi | {{prd_app_service_tag}}} |
| FIN:Role         | {dev_fin | {{dev_fin_role_tag}}} | {preprd_fin | {{preprd_fin_role_tag}}} | {prd_fin | {{prd_fin_role_tag}}} |
| Notif. Email     | {email | BUKDataPlatformDatabricks@barclays.com} | |          |
| Source Catalog   | 077382350852_buk_data_products (auto) | buk_data_product_central_catalog (auto) | buk_data_product_central_catalog (auto) |

Values shown as {{placeholder}} will need manual resolution before deployment.
Artefacts with unresolved placeholders will be marked DRAFT_UNVALIDATED.

Confirm and proceed? (yes / no — to re-enter values)
```

### On Confirmation

- **yes** → Store all values in `session_state.dbx_config` (per schema `schemas/session_state.schema.json#/properties/dbx_config`). Set `session_state.tenancy_resolution_method = "user_provided"`. Write `session_state.dbx_config.questionnaire_turns_completed = 5` (at the root of `dbx_config`, not nested under an environment key). Continue with STEP 2.7 remainder.
- **no** → Re-present all turns from the beginning for the user to correct values.

---

## Partial Answer Handling

For each question:
- If user provides a value → store it directly in session state
- If user types `skip` or leaves empty → store `null`; downstream uses `{{placeholder}}`
- Anti-hallucination: **NEVER guess or fabricate any skipped value**
- Artefacts with any `{{placeholder}}` are marked `DRAFT_UNVALIDATED`

### Per-Environment Partial Answer Rules

When a per-environment question asks for values across dev/preprd/prd (Q3, Q4, Q5, Q6, Q7, Q8, Q9):

1. **Each environment is independent** — a provided value for one env does NOT imply the same value for another env
2. **If an env field is left blank or empty** → treat as `skip`: store null → `{{placeholder}}`. Do NOT ask a follow-up sub-question or replicate another environment's value.
3. **Storage**:
   - Provided value → store as-is
   - Blank or empty → store null → `{{placeholder}}`

### Truly Blocking Fields (Re-prompt Once)

| Field | Why Blocking | If Still Skipped After Re-prompt |
|---|---|---|
| `tenancy_name` | Cannot construct workspace folders, catalog names, job names, bundle config | Proceed with `{{tenancy_name}}` placeholder throughout; ALL artefacts marked `DRAFT_UNVALIDATED` |

### Non-Blocking Fields (Placeholder if Skipped)

| Field | Placeholder Used | Downstream Impact |
|---|---|---|
| `domain_name` | `{{domain_name}}` | Mesh JSON metadata incomplete; non-critical |
| `target_catalog` (per env) | `{{dev_target_catalog}}` etc. | DABs bundle and driver config incomplete |
| `workspace_folder` (per env) | `{{dev_ws_root}}` etc. | DABs bundle config incomplete |
| `cicd_sp` / `exec_sp` (per env) | `{{dev_cicd_sp}}` etc. | DABs bundle permissions config incomplete |
| `ad_group` (per env) | `{{dev_ad_group}}` etc. | DABs bundle permissions config incomplete |
| `app_service_tag` (per env) | `{{dev_app_service_tag}}` etc. | Job tagging incomplete |
| `fin_role_tag` (per env) | `{{dev_fin_role_tag}}` etc. | Job tagging incomplete |
| `notification_email` | `BUKDataPlatformDatabricks@barclays.com` (default) | Uses platform default — not a placeholder |

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
  "values_provided": ["tenancy_name", "target_catalog_dev", "target_catalog_preprd", ...],
  "values_skipped": ["domain_name", "ad_group_dev", ...],
  "platform": "databricks"
}
```
