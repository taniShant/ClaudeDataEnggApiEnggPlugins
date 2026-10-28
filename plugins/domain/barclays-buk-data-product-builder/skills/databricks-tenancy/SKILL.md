---
name: databricks-tenancy
description: "Databricks tenancy registry — per-environment workspace configuration for teams deploying data products on Databricks (not Glue). Contains workspace folders, AD groups, Unity Catalog names, service principals, ITSI codes (IT Service Identifiers for Netcool alerting). Use when generating DABs config, resolving per-environment Databricks placeholders, or looking up service principal names. For Glue tenancy lookups, see aws-tenancy."
user-invocable: false
owner: "tom.franklin@barclays.com"
review_cadence: quarterly
last_reviewed: 2026-09-10
---

# Databricks Tenancy Registry — BUK Data Product Build Assistant

## When to Use This Skill

Use when:
- Generating Databricks Asset Bundle (DABs) YAML configuration
- Resolving Databricks workspace folder, catalog, or service principal per environment
- Looking up AD groups or tagging info (App Service Tag) for a Databricks tenancy

Do NOT use for:
- Glue-based tenancy lookups (Hive/Iceberg databases, BTB owners) → use `aws-tenancy`
- Constructing S3 bucket paths from naming patterns → use `aws-data-products`
- ITSI/Netcool mappings for Glue jobs → use `service-management`

---

**Source:** [Confluence - Data Engineering Tenancy](https://confluence.barcapint.com/spaces/SDWH/pages/3738117955/Data+Engineering+Tenancy)

---

## Lookup Rules

1. **Match by workspace folder name**: Strip the environment prefix (`DEV_`, `PRD_`, `PREPRD_`) from the Databricks workspace folder → the remainder is the Feature Team Name (e.g., `DEV_BUK_BBKYC_BDP` → `BUK_BBKYC_BDP`).
2. **Match by target database**: Look up `Target DB / Schema` column against `mapping_parsed.json` target database. **EXACT match only** — `row["Target DB"].lower() == target_database.lower()`. Do NOT use fuzzy matching, partial matching, substring matching, similarity matching, or closest-match heuristics. If no row matches exactly, the lookup result is "not found".
3. **Case-insensitive**: All lookups — including Environment column matching — are case-insensitive (e.g., `DEV`, `Dev`, `dev` all match the DEV row).

---

## Environment → DABs Target Mapping

| Confluence Environment | DABs Target Name | Config Key |
|---|---|---|
| DEV | `dev` | `dev` |
| PREPRD (Prod Parallel) | `prod_parallel` | `preprd` |
| PRD | `prod_prod` | `prd` |
| UAT (optional) | `uat` | `uat` |

---

## Workspace Hosts (Fixed — Shared Across ALL Tenancies)

| Environment | DABs Target | Workspace URL | Default Policy ID |
|---|---|---|---|
| DEV | `dev` | `https://dev-buk-uk.cloud.databricks.com/` | `00186E9BB6908351` |
| PREPRD (Prod Parallel) | `prod_parallel` | `https://prod-buk-parallel-uk.cloud.databricks.com/` | `000CB013172B29C7` |
| PRD | `prod_prod` | `https://prod-buk-prod-uk.cloud.databricks.com` | `000A02890D1F23ED` |
| UAT | `uat` | TBD | TBD |

**Policy ID resolution:** If a tenancy row has a specific Policy ID, use that. If the tenancy row shows `TBD`, use the **Default Policy ID** from the table above for the corresponding environment.

---

## Source Catalogs (Fixed — Shared Across ALL Tenancies)

| Environment | DABs Target | Default Source Catalog (source_catalog_1) |
|---|---|---|
| DEV | `dev` | `077382350852_buk_data_products` |
| PREPRD (Prod Parallel) | `prod_parallel` | `buk_data_product_central_catalog` |
| PRD | `prod_prod` | `buk_data_product_central_catalog` |
| UAT | `uat` | `279373726337_buk_data_products_uat` |

**Additional source catalogs** (`source_catalog_2`, `source_catalog_3`, ...): Only added to config.yml when domain knowledge specifies that source tables come from a catalog other than the default. If domain knowledge does not mention additional catalogs, `source_catalogs` contains only `source_catalog_1`.

---

## Fields NOT Resolvable (TBD — Domain Knowledge Required)

| Placeholder | Notes |
|---|---|
| `{{notification_email}}` | Team notification email address. Default: `BUKDataPlatformDatabricks@barclays.com` (from onboarding emails). Some teams have team-specific emails — check Notification Email column. |

---

## Placeholder → Column Resolution Map

| Template Placeholder | Table Column |
|---|---|
| `{{dev_ws_root}}` / `{{preprd_ws_root}}` / `{{prd_ws_root}}` / `{{uat_ws_root}}` / `{{ws_root_default}}` | Workspace Folder |
| `{{dev_target_catalog}}` / `{{preprd_target_catalog}}` / `{{prd_target_catalog}}` / `{{uat_target_catalog}}` | Write/Target Catalog |
| `{{dev_ad_group}}` / `{{preprd_ad_group}}` / `{{prd_ad_group}}` / `{{uat_ad_group}}` / `{{ad_group}}` | AD Group |
| `{{dev_cicd_sp}}` / `{{preprd_cicd_sp}}` / `{{prd_cicd_sp}}` / `{{uat_cicd_sp}}` / `{{cicd_sp_id}}` | CICD Service Principal |
| `{{dev_exec_sp}}` / `{{preprd_exec_sp}}` / `{{prd_exec_sp}}` / `{{uat_exec_sp}}` / `{{exec_sp_id}}` | Exec Service Principal |
| `{{app_service_tag}}` | ITSI column (plain ITSI only for `APP:ApplicationService` tag, e.g., `SNSVC0075004`) |
| `{{fin_role_tag}}` | App Service Tag column (composite `FIN:Role` value, format: `{ITSI}_{Use_Case_Jira_ID}_{Feature_Team_Name}`, e.g., `SNSVC0081846_EDPUC-1597_BUK_BBKYC_BDP`) |
| `{{dev_workspace_host}}` / `{{preprd_workspace_host}}` / `{{prd_workspace_host}}` / `{{uat_workspace_host}}` | Fixed Workspace Hosts table above |
| `{{dev_source_catalog_1}}` / `{{preprd_source_catalog_1}}` / `{{prd_source_catalog_1}}` / `{{uat_source_catalog_1}}` | Source Catalog column (or Fixed table above) |
| `{{*_policy_id}}` | Default Policy ID (from Workspace Hosts table — shared across all tenancies per environment) |
| `{{notification_email}}` | Notification Email (TBD) |
| `{{domain_name}}` | Domain |
| `{{dp_type_lower}}` | DP Type (lowercased) |
| `{{tenancy_name}}` | Feature Team Name (lowercase, env prefix stripped) |

---

## Tagging Convention

| Tag Key | Format | Resolves From |
|---|---|---|
| App Service Tag | `{ITSI}_EDPUC-{number}_{FEATURE_TEAM_NAME}` | App Service Tag column |
| `APP:ApplicationService` | ITSI only | ITSI column |

**Rules:**
- EDPUC always includes hyphen: `EDPUC-1551` (never `EDPUC1551`)
- Feature Team Name follows the Use Case Jira ID

**Examples:**
- `FIN:Role`: `SNSVC0075004_EDPUC-1551_BUK_PAFER_BDP`
- `APP:ApplicationService`: `SNSVC0075004`

---

## Tenancy Infrastructure Registry

Each row = one Feature Team × one Environment. `TBD` = value not available from source (requires Domain Knowledge or onboarding confirmation).

| Feature Team Name | Domain | DP Type | Target DB | Environment | Workspace Folder | ITSI | App Service Tag | CICD Service Principal | Exec Service Principal | Write/Target Catalog | Source Catalog | AD Group | Notification Email |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BUK_BBKYC_BDP | Business Banking | BDP | bdp_uk_bbcdd_db_dbxw | DEV | DEV_BUK_BBKYC_BDP | SNSVC0081840 | SNSVC0081840_EDPUC-1597_BUK_BBKYC_BDP | buk_bbkyc_bdp_cicd_dev_sp | buk_bbkyc_bdp_exec_dev_sp | dev_buk_bbkyc_bdp | 077382350852_buk_data_products | GLO-CLI-SEC-AZADDBXBUKBBSOFDDE / fglbAZADDBXBUKSOFDDE | TBD |
| BUK_BBKYC_BDP | Business Banking | BDP | bdp_uk_bbcdd_db_dbxw | PREPRD | PREPRD_BUK_BBKYC_BDP | SNSVC0081846 | SNSVC0081846_EDPUC-1597_BUK_BBKYC_BDP | buk_bbkyc_bdp_cicd_preprd_sp | buk_bbkyc_bdp_exec_preprd_sp | preprd_buk_bbkyc_bdp | buk_data_product_central_catalog | GLO-CLI-SEC-AZADDBXBUKRTBSDE / glo-cli-sec-AZADDBXBUKBBSOFSDE | TBD |
| BUK_BBKYC_BDP | Business Banking | BDP | bdp_uk_bbcdd_db_dbxw | PRD | PRD_BUK_BBKYC_BDP | SNSVC0081846 | SNSVC0081846_EDPUC-1597_BUK_BBKYC_BDP | buk_bbkyc_bdp_cicd_prd_sp | buk_bbkyc_bdp_exec_prd_sp | prd_buk_bbkyc_bdp | buk_data_product_central_catalog | GLO-CLI-SEC-AZADDBXBUKRTBPDE / glo-cli-sec-AZADDBXBUKBBSOFPDE | TBD |
| BUK_BUSBANK_BDP | Business Banking CDD | BDP | bdp_uk_busbank_db_dbxw | PREPRD | PREPRD_BUK_BUSBANK_BDP | SNSVC0081846 | SNSVC0081846_EDPUC-1597_BUK_BUSBANK_BDP | buk_busbank_bdp_cicd_preprd_sp | buk_busbank_bdp_exec_preprd_sp | preprd_buk_busbank_bdp | buk_data_product_central_catalog | GLO-CLI-SEC-AZADDBXBUKRTBSDE | BUKDataPlatformDatabricks@barclays.com |
| BUK_BUSBANK_BDP | Business Banking CDD | BDP | bdp_uk_busbank_db_dbxw | PRD | PRD_BUK_BUSBANK_BDP | SNSVC0081846 | SNSVC0081846_EDPUC-1597_BUK_BUSBANK_BDP | buk_busbank_bdp_cicd_prd_sp | buk_busbank_bdp_exec_prd_sp | prd_buk_busbank_bdp | buk_data_product_central_catalog | GLO-CLI-SEC-AZADDBXBUKRTBSDE | BUKDataPlatformDatabricks@barclays.com |
| BUK_BUSBANK_CDP | Business Banking | CDP | — | DEV | DEV_BUK_BUSBANK_CDP | SNSVC0073660 | SNSVC0073660_EDPUC-1676_BUK_BUSBANK_CDP | buk_busbank_cdp_cicd_dev_sp | buk_busbank_cdp_exec_dev_sp | dev_buk_busbank_CDP | 077382350852_buk_data_products | GLO-CLI-SEC-AZADDBXBUKBBCDPDDE | TBD |
| BUK_BUSBANK_CDP | Business Banking | CDP | — | UAT | UAT_BUK_BUSBANK_CDP | SNSVC0073660 | SNSVC0073660_EDPUC-1676_BUK_BUSBANK_CDP | buk_busbank_cdp_cicd_uat_sp | buk_busbank_cdp_exec_uat_sp | dev_buk_busbank_cdp | 279373726337_buk_data_products_uat | GLO-CLI-SEC-AZADDBXBUKBBCDPDDE | BUKDataPlatformDatabricks@barclays.com |
| BUK_CARDSCOMM_CDP | Card Commercial | CDP | cdp_uk_credit_card_db | DEV | DEV_BUK_CARDSCOMM_CDP | SNSVC0072630 | SNSVC0072630_EDPUC-1631_BUK_CARDSCOMM_CDP | buk_cardscomm_cdp_cicd_dev_sp | buk_cardscomm_cdp_exec_dev_sp | dev_buk_cardscomm_cdp | 077382350852_buk_data_products | GLO-CLI-SEC-AZADDBXBUKCOMDDE / fGLBAZADDBXBUKCOMDDE | BUKDataPlatformDatabricks@barclays.com |
| BUK_CCD | Customer Communications Delivery (CCD) | BDP | BUK_CCD_Campaign_DB | PRD | PRD_BUK_CCD | SNSVC0084537 | SNSVC0084537_EDPUC-1004_BUK_CCD | buk_marketingccd_bdp_cicd_prd_sp | buk_marketingccd_bdp_exec_prd_sp | prd_buk_ccd_marketing_bdp | buk_data_product_central_catalog | GLO-CLI-SEC-AZADDBXBUKCCDPDE | TBD |
| BUK_COMPLAINTS_BDP | Complaints | BDP | — | DEV | DEV_BUK_COMPLAINTS_BDP | SNSVC0069877 | SNSVC0069877_EDPUC-1983_buk_complaints_bdp | buk_complaints_bdp_cicd_dev_sp | buk_complaints_bdp_exec_dev_sp | dev_buk_complaints_bdp | 077382350852_buk_data_products | GLO-CLI-SEC-AZADDBXBUKCMPLNTBDPPDDE | TBD |
| BUK_COMPLAINTS_CDP | Complaints | CDP | cdp_uk_complaints_db_dbx | PREPRD | PREPRD_BUK_COMPLAINTS_CDP | SNSVC0069873 | SNSVC0069873_buk_dataeng_cmp_cdp_catalog_dbx | TBD | TBD | TBD | buk_data_product_central_catalog | TBD | TBD |
| BUK_COMPLAINTS_CDP | Complaints | CDP | cdp_uk_complaints_db_dbx | PRD | PRD_BUK_COMPLAINTS_CDP | SNSVC0069873 | SNSVC0069873_EDPUC-1080_buk_dataeng_cmp_cdp_catalog_dbx | buk_complaints_cdp_cicd_prd_sp | buk_complaints_cdp_exec_prd_sp | prd_buk_complaints_cdp | buk_data_product_central_catalog | GLO-CLI-SEC-AZADDBXBUKCMPCDPPDE | TBD |
| BUK_CONSUMER_LOANS_BDP | Consumer Loans | BDP | — | DEV | DEV_BUK_CONSUMER_LOANS_BDP | TBD | TBD | buk_consumer_loans_bdp_cicd_dev_sp | buk_consumer_loans_bdp_exec_dev_sp | dev_buk_consumer_loans_bdp | 077382350852_buk_data_products | GLO-CLI-SEC-AZADDBXBUKCLNBDPDDE | BUKDataPlatformDatabricks@barclays.com |
| BUK_CONTROLIT_BDP | ControlIT | BDP | buk_controlit_db | DEV | DEV_BUK_CONTROLIT_BDP | SNSVC0074774 | SNSVC0074774_EDPUC-1633_buk_controlit_bdp | buk_controlit_bdp_cicd_dev_sp | buk_controlit_bdp_exec_dev_sp | dev_buk_controlit_bdp | 077382350852_buk_data_products | GLO-CLI-SEC-AZADDBXBUKCITBDPDDE / fglbAZADDBXBUKCITDDE | ControlItDevelopers@barclays.com |
| BUK_CUSTOMER_BDP | Customer | BDP | — | DEV | DEV_BUK_CUSTOMER_BDP | SNSVC0070020 | SNSVC0070020_EDPUC-2020_BUK_CUSTOMER_BDP | buk_customer_bdp_cicd_dev_sp | buk_customer_bdp_exec_dev_sp | dev_buk_customer_bdp | 077382350852_buk_data_products | GLO-CLI-SEC-AZADDBXBUKCUSBDPRDDE | BUKDataPlatformDatabricks@barclays.com |
| BUK_CUSTOMER_BDP | Customer | BDP | — | UAT | UAT_BUK_CUSTOMER_BDP | SNSVC0070020 | SNSVC0070020_EDPUC-2020_BUK_CUSTOMER_BDP | buk_customer_bdp_cicd_uat_sp | buk_customer_bdp_exec_uat_sp | dev_buk_customer_bdp | 279373726337_buk_data_products_uat | GLO-CLI-SEC-AZADDBXBUKCUSBDPRDDE | BUKDataPlatformDatabricks@barclays.com |
| BUK_CUSTOMER_FDP | Customer | FDP | — | PREPRD | PREPRD_BUK_CUSTOMER_FDP | SNSVC0069880 | TBD | TBD | TBD | preprd_buk_customer_fdp | buk_data_product_central_catalog | GLO-CLI-SEC-AZADDBXBUKCUSFDPSDE | TBD |
| BUK_CUSTOMER_FDP | Customer | FDP | — | PRD | PRD_BUK_CUSTOMER_FDP | SNSVC0069880 | SNSVC0070020_EDPUC-1080_BUK_CUSTOMER_FDP | buk_customer_fdp_cicd_prd_sp | buk_customer_fdp_exec_prd_sp | prd_buk_customer_fdp | buk_data_product_central_catalog | GLO-CLI-SEC-AZADDBXBUKCUSFDPPDE | TBD |
| BUK_DIGITALROLB_BDP | Digital ROLB | BDP | — | DEV | DEV_BUK_DIGITALROLB_BDP | SNSVC0072843 | SNSVC0072843_EDPUC-1502_buk_digitalrolb_bdp | buk_dgtlrolb_bdp_cicd_dev_sp | buk_dgtlrolb_bdp_exec_dev_sp | dev_buk_digitalrolb_bdp | 077382350852_buk_data_products | GLO-CLI-SEC-AZADDBXBUKDIGRLBDDE / fglbAZADDBXBUKRLBDDE | DigitalTeam-BUKDataFoundations@barclays.com |
| BUK_DIGITALROLB_BDP | Digital ROLB | BDP | — | UAT | UAT_BUK_DIGITALROLB_BDP | SNSVC0072843 | SNSVC0072843_EDPUC-1502_BUK_DIGITALROLB_BDP | buk_dgtlrolb_bdp_cicd_uat_sp | buk_dgtlrolb_bdp_exec_uat_sp | dev_buk_digitalrolb_bdp | 279373726337_buk_data_products_uat | GLO-CLI-SEC-AZADDBXBUKDIGRLBUDE / fglbAZADDBXBUKRLBDDE | BUKDataPlatformDatabricks@barclays.com |
| BUK_ECF | Current Account (ECF) | BDP | bdp_uk_current_acct_db | DEV | DEV_BUK_CRNTACCT_BDP | SNSVC0076076 | SNSVC0076076_EDPUC-1631_buk_crntacctecf_bdp | buk_caecf_bdp_cicd_dev_sp | buk_caecf_bdp_exec_dev_sp | dev_buk_crntacct_bdp | 077382350852_buk_data_products | GLO-CLI-SEC-AZADDBXBUKCAPLECFDDE | TBD |
| BUK_ECF | Current Account (ECF) | BDP | bdp_uk_current_acct_db | PREPRD | PRD_BUK_ECF | SNSVC0076074 | SNSVC0076074_EDPUC-1631_BUK_CRNTACCT_BDP | buk_crntacct_bdp_cicd_preprd_sp | buk_crntacct_bdp_exec_preprd_sp | preprd_buk_crntacct_bdp | buk_data_product_central_catalog | GLO-CLI-SEC-AZADDBXBUKRTBSDE | TBD |
| BUK_ECF | Current Account (ECF) | BDP | bdp_uk_current_acct_db | PRD | PRD_BUK_ECF | SNSVC0076074 | SNSVC0076074_EDPUC-1631_BUK_CRNTACCT_BDP | buk_crntacct_bdp_cicd_prd_sp | buk_crntacct_bdp_exec_prd_sp | PRD_BUK_CRNTACCT_BDP | buk_data_product_central_catalog | GLO-CLI-SEC-AZADDBXBUKRTBSDE | TBD |
| BUK_ESC_BDP | Exec ScoreCards | BDP | — | DEV | DEV_BUK_ESC_BDP | SNSVC0081242 | SNSVC0081242_EDPUC-1818_BUK_ESC_BDP | buk_esc_bdp_cicd_dev_sp | buk_esc_bdp_exec_dev_sp | dev_buk_esc_bdp | 077382350852_buk_data_products | GLO-CLI-SEC-AZADDBXBUKESCDDE / fGLBAZADDBXBUKESCDDE | TBD |
| BUK_ESC_BDP | Exec ScoreCards | BDP | — | PRD | PRD_BUK_ESC_BDP | SNSVC0081204 | SNSVC0081204_EDPUC-1818_BUK_ESC_BDP | buk_esc_bdp_cicd_prd_sp | buk_esc_bdp_exec_prd_sp | prd_buk_esc_bdp | buk_data_product_central_catalog | GLO-CLI-SEC-AZADDBXBUKRTBPDE | BUKDataPlatformDatabricks@barclays.com |
| BUK_INSURANCE_BDP | Insurance | BDP | BDP_UK_INSURANCE_AND_PACKS_DB_DBX | DEV | DEV_BUK_INSURANCE_BDP | SNSVC0076216 | SNSVC0076216_EDPUC-1722_BUK_INSURANCE_BDP | buk_insurance_bdp_cicd_dev_sp | buk_insurance_bdp_exec_dev_sp | dev_buk_insurance_bdp | 077382350852_buk_data_products | GLO-CLI-SEC-AZADDBXBUKINSBDPDDE | TBD |
| BUK_INSURANCE_BDP | Insurance | BDP | BDP_UK_INSURANCE_AND_PACKS_DB_DBX | PREPRD | PREPRD_BUK_INSURANCE_BDP | SNSVC0076172 | SNSVC0076172_buk_dataeng_ins_bdp_catalog_dbx | TBD | TBD | TBD | buk_data_product_central_catalog | GLO-CLI-SEC-AZADDBXBUKRTBSDE | TBD |
| BUK_INSURANCE_BDP | Insurance | BDP | BDP_UK_INSURANCE_AND_PACKS_DB_DBX | PRD | PRD_BUK_INSURANCE_BDP | SNSVC0076172 | SNSVC0076172_EDPUC-1722_BUK_INSURANCE_BDP | buk_insurance_bdp_cicd_prd_sp | buk_insurance_bdp_exec_prd_sp | prd_buk_insurance_bdp | buk_data_product_central_catalog | GLO-CLI-SEC-AZADDBXBUKRTBPDE | TBD |
| BUK_MARKETING_BDP | Marketing | BDP | BDP_UK_MARKETING_DB_DBX | DEV | DEV_BUK_MARKETING_BDP | SNSVC0077456 | SNSVC0077456_EDPUC-1953_buk_marketing_bdp | buk_marketing_bdp_cicd_dev_sp | buk_marketing_bdp_exec_dev_sp | dev_buk_marketing_bdp | 077382350852_buk_data_products | GLO-CLI-SEC-AZADDBXBUKMKBDPPDDE | BUKDataPlatformDatabricks@barclays.com |
| BUK_MARKETING_BDP | Marketing | BDP | BDP_UK_MARKETING_DB_DBX | PREPRD | PREPRD_BUK_MARKETING_BDP | SNSVC0077458 | SNSVC0077458_EDPUC-1953_BUK_MARKETING_BDP | buk_marketing_bdp_cicd_preprd_sp | buk_marketing_bdp_exec_preprd_sp | preprd_buk_marketing_bdp | buk_data_product_central_catalog | GLO-CLI-SEC-AZADDBXBUKRTBSDE | BUKDataPlatformDatabricks@barclays.com |
| BUK_MARKETING_BDP | Marketing | BDP | BDP_UK_MARKETING_DB_DBX | PRD | PRD_BUK_MARKETING_BDP | SNSVC0077458 | SNSVC0077458_EDPUC-1953_BUK_MARKETING_BDP | buk_marketing_bdp_cicd_prd_sp | buk_marketing_bdp_exec_prd_sp | prd_buk_marketing_bdp | buk_data_product_central_catalog | GLO-CLI-SEC-AZADDBXBUKRTBPDE | BUKDataPlatformDatabricks@barclays.com |
| BUK_MARKETING_CIDP | MarTech / CIDP | BDP | BUK_MDP_PARTNER_PRD | PREPRD | PREPRD_BUK_MARKETING_CIDP | SNSVC0077458 | SNSVC0077458_EDPUC-1014_buk_marketing_bdp | buk_marketingcidp_cicd_preprd_sp | buk_marketingcidp_exec_preprd_sp | PREPRD_BUK_MARKETING_CIDP | buk_data_product_central_catalog | GLO-CLI-SEC-AZADDBXBUKMARSDE | TBD |
| BUK_MORTGAGES_BDP | Mortgages | BDP | — | DEV | DEV_BUK_MORTGAGES_BDP | SNSVC0072836 | SNSVC0072836_EDPUC-1743_buk_mortgage_bdp | buk_mtge_bdp_cicd_dev_sp | buk_mtge_bdp_exec_dev_sp | dev_buk_mortgages_bdp | 077382350852_buk_data_products | GLO-CLI-SEC-AZADDBXBUKMORTBDPPDDE | TBD |
| BUK_MORTGAGES_CDP | Mortgages CDP | CDP | cdp_uk_mortgages_db_dbx | PREPRD | PREPRD_BUK_MORTGAGES_CDP | SNSVC0072837 | SNSVC0072837_EDPUC-1744_BUK_MORTGAGES_CDP | buk_mortgages_cdp_cicd_preprd_sp | buk_mortgages_cdp_exec_preprd_sp | preprd_buk_mortgages_cdp | buk_data_product_central_catalog | GLO-CLI-SEC-AZADDBXBUKRTBSDE | BUKDataPlatformDatabricks@barclays.com |
| BUK_MORTGAGES_CDP | Mortgages CDP | CDP | cdp_uk_mortgages_db_dbx | PRD | PRD_BUK_MORTGAGES_CDP | SNSVC0072837 | SNSVC0072837_EDPUC-1744_BUK_MORTGAGES_CDP | buk_mortgages_cdp_cicd_prd_sp | buk_mortgages_cdp_exec_prd_sp | prd_buk_mortgages_cdp | buk_data_product_central_catalog | GLO-CLI-SEC-AZADDBXBUKRTBSDE | BUKDataPlatformDatabricks@barclays.com |
| BUK_OTMI | OTMI | BDP | — | DEV | DEV_BUK_OTMI | SNSVC0082172 | SNSVC0082172_EDPUC-1645_BUK_OTMI | buk_otmi_cicd_dev_sp | buk_otmi_exec_dev_sp | NA | 077382350852_buk_data_products | GLO-CLI-SEC-AZADDBXBUKOTMDDE | TBD |
| BUK_OTMI | OTMI | BDP | — | PRD | PRD_BUK_OTMI | SNSVC0082242 | SNSVC0082172_EDPUC-1645_BUK_OTMI | buk_otmi_ro_pan_sp | NA | NA | buk_data_product_central_catalog | GLO-CLI-SEC-AZADDBXBUKOTMABI , fglbAZADDBXBUKOTMABI | TBD |
| BUK_PAFER_BDP | PAFER (Regulatory) | BDP | bdp_uk_pafer_db | DEV | DEV_BUK_PAFER_BDP | SNSVC0075004 | SNSVC0075004_EDPUC-1551_buk_pafer_bdp | buk_pafer_bdp_cicd_dev_sp | buk_pafer_bdp_exec_dev_sp | dev_buk_pafer_bdp | 077382350852_buk_data_products | GLO-CLI-SEC-AZADDBXBUKRNCDDE | TBD |
| BUK_PAFER_BDP | PAFER (Regulatory) | BDP | bdp_uk_pafer_db | UAT | UAT_BUK_PAFER_BDP | SNSVC0075004 | SNSVC0075004_EDPUC-1551_buk_pafer_bdp | buk_pafer_bdp_cicd_uat_sp | buk_pafer_bdp_exec_uat_sp | uat_buk_pafer_bdp | 077382350852_buk_data_products | GLO-CLI-SEC-AZADDBXBUKRNCTDE | TBD |
| BUK_PLATFORM | Platform | NA | buk_cdao_platform | DEV | DEV_BUK_PLATFORM | SNSVC0057600 | SNSVC0057600_EDPUC-1080_buk_platform | buk_platform_cicd_dev_sp | buk_platform_exec_dev_sp | buk_platform | 077382350852_buk_data_products | GLO-CLI-SEC-AZADDBXBUKPLTDDE | TBD |
| BUK_UKBA_FDP | UKBA | FDP | fdp_uk_ukba_db | DEV | DEV_BUK_UKBA_FDP | SNSVC0076076 | SNSVC0076076_EDPUC-1920_buk_ukba_fdp | buk_ukba_fdp_cicd_dev_sp | buk_ukba_fdp_exec_dev_sp | dev_buk_ukba_fdp | 077382350852_buk_data_products | GLO-CLI-SEC-AZADDBXBUKSAUKBAFDPDDE | BUKDataPlatformDatabricks@barclays.com |
| BUK_UKBA_FDP | UKBA | FDP | fdp_uk_ukba_db | UAT | UAT_BUK_UKBA_FDP | SNSVC0079174 | TBD | buk_ukba_fdp_cicd_uat_sp | buk_ukba_fdp_exec_uat_sp | uat_buk_ukba_fdp | 077382350852_buk_data_products | TBD | TBD |
| BUK_UKBA_FDP | UKBA | FDP | fdp_uk_ukba_db | PRD | PRD_BUK_UKBA_FDP | SNSVC0079172 | TBD | buk_ukba_fdp_cicd_prd_sp | buk_ukba_fdp_exec_prd_sp | prd_buk_ukba_fdp | buk_data_product_central_catalog | TBD | TBD |
| TSC_CUSTOMER_FDP | Customer | FDP | dev_tsc_customer_fdp | DEV | DEV_TSC_CUSTOMER_FDP | SNSVC0086795 | TBD | tsc_cust_fdp_cicd_dev_sp | tsc_cust_fdp_exec_dev_sp | dev_tsc_customer_fdp | 077382350852_glue_shared_catalog_sierra | GLO-CLI-SEC-AZADDBXTSCCUSTFDPDDE | TBD |
| UK-BUK DEV | BUK-Marketing | BI Reporting | — | DEV | TBD | SNSVC0077456 | TBD | buk_MKT_ro_dev_sp | NA | TBD | 077382350852_buk_data_products | GLO-CLI-SEC-AZADDBXBUKMRKTNGMIDBI | BUKDataPlatformDatabricks@barclays.com |
| UK-BUK-Marketing-MI | BUK-Marketing | BI Reporting | — | PREPRD | TBD | SNSVC0077458 | TBD | buk_mkt_ro_pan_sp | NA | TBD | buk_data_product_central_catalog | GLO-CLI-SEC-AZADDBXBUKMRKTNGMIABI | BUKDataPlatformDatabricks@barclays.com |
| UK-BUK-Marketing-MI | BUK-Marketing | BI Reporting | — | PRD | TBD | SNSVC0077458 | TBD | buk_mkt_ro_prd_sp | NA | TBD | buk_data_product_central_catalog | TBD | BUKDataPlatformDatabricks@barclays.com |

---

## Service Principal Resolution

Where SP details are marked TBD, the system asks the user via the infrastructure questionnaire (`prompts/infrastructure-questionnaire-databricks.md` Turn 3 — Q5/Q6). Do NOT derive SP names from naming conventions. If the user skips, `{{*_cicd_sp}}` / `{{*_exec_sp}}` placeholders are retained and artefacts marked `DRAFT_UNVALIDATED`.

---

## Write Catalog Resolution

Where write catalog is marked TBD, the system asks the user via the infrastructure questionnaire (`prompts/infrastructure-questionnaire-databricks.md` Turn 2 — Q3). Do NOT derive catalog names from naming conventions. If the user skips, `{{*_target_catalog}}` placeholders are retained and artefacts marked `DRAFT_UNVALIDATED`.

---

## Related Skills

| Skill | Scope |
|-------|-------|
| `barclays-buk-data-product-builder:aws-tenancy` | Glue tenancy: team → database / bucket-shortname / BTB owner / datasetType |
| `barclays-buk-data-product-builder:aws-data-products` | Infrastructure constants: account IDs, S3 naming patterns, glue.id |
| `barclays-buk-data-product-builder:service-management` | Runtime: ITSI codes, tool versions, state machines, known issues |

## Agent Self-Check

Before using this skill's data, verify:

- [ ] **Check 1**: workspace URL matches env
- [ ] **Check 2**: Unity Catalog name resolved
- [ ] **Check 3**: service principal assigned
- [ ] **Check 4**: AD groups configured
- [ ] **Check 5**: ITSI codes per env complete
