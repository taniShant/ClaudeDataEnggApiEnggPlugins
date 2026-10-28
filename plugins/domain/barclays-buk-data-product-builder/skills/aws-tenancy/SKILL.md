---
name: aws-tenancy
description: "AWS Glue tenancy registry — a tenancy is the logical group of AWS resources (S3 buckets, databases, IAM roles) assigned to a feature team for building data products on AWS cloud. Maps each team to its S3 shortname, Hive/Iceberg database, BTB owner, and datasetType. Use when resolving a target database to its owning team, constructing Mesh JSON, or looking up bucket shortnames for Glue pipelines. For Databricks workspace config, see databricks-tenancy."
user-invocable: false
owner: "tom.franklin@barclays.com"
review_cadence: quarterly
last_reviewed: 2026-08-18
---

**Source:** Tom Franklin | **Owner:** tom.franklin@barclays.com | **Review:** Quarterly | **Last reviewed:** 2026-08-18

# Tenancy Registry — BUK CDAO Data Products

## When to Use This Skill

Use when:
- Resolving a target database name to its owning feature team
- Looking up S3 bucket shortnames for AWS Glue data products
- Constructing Mesh JSON metadata (BTB owner, datasetType)
- Determining Hive or Iceberg database names from a tenancy name

Do NOT use for:
- Databricks workspace folders, catalogs, or service principals → use `databricks-tenancy`
- AWS account IDs or S3 bucket path construction → use `aws-data-products`
- ITSI/Netcool component codes or runtime versions → use `service-management`

---

## Lookup Rules (Apply to ALL registry lookups)

When matching `target_database` against the Hive Database or Iceberg Database columns:
1. **Strip whitespace**: trim leading/trailing whitespace from the input value
2. **Case-insensitive**: compare lowercase input against lowercase registry values
3. These rules apply to all consumers: domain knowledge auto-discovery (STEP 2.1), env_config resolution (STEP 2.6), tenancy name derivation, and any other registry lookup

### Feature Teams and Data Product Types

| Feature Team Name | DP Type | Domain | S3 Bucket Shortname | Hive Database | Iceberg Database |
|---|---|---|---|---|---|
| `complaints` | fdp | Complaints | `fdpcomplaints01` | `fdp_uk_complaints_db` | `fdp_uk_complaints_db_iceberg` |
| `customer` | fdp | Customer | `fdpcustomer01` | `fdp_uk_customer_db` | `fdp_uk_customer_db_iceberg` |
| `fdprefdata` | fdp | Cross Domain Ref Data | `fdprefdata01` | `fdp_uk_ref_data_db` | Not available |
| `fdpchnlcc` | fdp | Contact Centre Channel | `fdpchnlcc01` | `fdp_uk_cntct_centr_chnl_db` | `fdp_uk_cntct_centr_chnl_db_icbg` |
| `fdpukcards` | fdp | Credit Cards | `fdpukcards01` | `fdp_uk_credit_card_db` | `fdp_uk_credit_card_db_iceberg` |
| `fdpbrnchchnl` | fdp | Branch Channel | `fdpbrnchchnl01` | `fdp_uk_brnch_chnl_db` | `fdp_uk_brnch_chnl_db_iceberg` |
| `fdpdigital` | fdp | Digital Channel | `fdpdigital01` | `fdp_uk_digitl_chnl_db` | `fdp_uk_digitl_chnl_db_iceberg` |
| `fdpmortgage` | fdp | Mortgage | `fdpmortgage01` | `fdp_uk_mortgage_db` | `fdp_uk_mortgage_db_iceberg` |
| `fdpukloans` | fdp | Consumer Loans | `fdpukloans01` | `fdp_uk_cnsmr_loan_db` | `fdp_uk_cnsmr_loan_db_iceberg` |
| `fdpbusbank` | fdp | Business Banking | `fdpbusbank01` | `fdp_uk_bb_db` | `fdp_uk_bb_db_iceberg` |
| `fdpnps` | fdp | NPS | `fdpnps01` | `fdp_uk_nps_db` | `fdp_uk_nps_db_iceberg` |
| `fdpbpf` | fdp | BPF | `fdpbpf01` | `fdp_bpf_customer_db` / `fdp_bpf_complaints_db` / `fdp_bpf_account_db` / `fdp_bpf_coll_rcvry_db` | Iceberg variants |
| `fdpcolrcvy` | fdp | Collections & Recoveries | `fdpcolrcvy01` | Not available | `fdp_uk_coll_rcovry_db` |
| `fdpsavings` | fdp | Savings Account | `fdpsavings01` | `fdp_uk_savings_acct_db` | `fdp_uk_savings_acct_db_iceberg` |
| `fdpcurrentaccount` | fdp | Current Account | `fdpcurrentaccount01` | `fdp_uk_current_acct_db` | `fdp_uk_current_acct_db_iceberg` |
| `fdpprodins` | fdp | Insurance | `fdpprodins01` | `fdp_uk_insure_packs_db` | `fdp_uk_insure_packs_db_iceberg` |
| `fdpcommchnl` | fdp | Communication Channel | `fdpcommchnl01` | `fdp_uk_comm_chnl_db` | `fdp_uk_comm_chnl_db_iceberg` |
| `fdpbbcu` | fdp | BB Current Account | `fdpbbcu01` | `fdp_uk_bb_current_acct_db` | `fdp_uk_bb_current_acct_db_iceberg` |
| `fdpbbsa` | fdp | BB Savings Account | `fdpbbsa01` | `fdp_uk_bb_savings_acct_db` | `fdp_uk_bb_savings_acct_db_iceberg` |
| `fdpbbfx` | fdp | BB FX Account | `fdpbbfx01` | `fdp_uk_bb_fx_acct_db` | `fdp_uk_bb_fx_acct_db_iceberg` |
| `fdprewards` | fdp | Rewards | `fdprewards01` | Not available | Not available |
| `fdpdormancy` | fdp | Dormancy | `fdpdormancy01` | Not available | Not available |
| `fdpbbcase` | fdp | BB Case | `fdpbbcase01` | Not available | Not available |
| `fdpsaukba` | fdp | UKBA | `fdpsaukba` | Not available | `fdp_uk_ukba_db` |
| `cdpcmplnts` | cdp | Complaints | `cdpcomplaints01` | `cdp_uk_complaints_db` | `cdp_uk_complaints_db_iceberg` |
| `cdpcustomer` | cdp | Customer | `cdpcustomer01` | `cdp_uk_customer_db` | `cdp_uk_customer_db_iceberg` |
| `cdpproddom` | cdp | Products | `cdpproddom01` | `cdp_uk_product_db` | `cdp_uk_product_db_iceberg` |
| `cdpchannels` | cdp | Channels | `cdpchannels01` | `cdp_uk_channels_db` | `cdp_uk_channels_db_iceberg` |
| `cdpnps` | cdp | NPS | `cdpnps01` | Not available | `cdp_uk_nps_db` |
| `cdpbusbank` | cdp | Business Banking | `cdpbusbank01` | `cdp_uk_bb_db` | `cdp_uk_bb_db_iceberg` |
| `cdpmortgage` | cdp | Mortgage | `cdpmortgage01` | `cdp_uk_mortgage_db` | `cdp_uk_mortgage_db_iceberg` |
| `cdptrans` | cdp | Transaction | `cdptrans01` | `cdp_uk_transaction_db` | `cdp_uk_transaction_db_iceberg` |
| `cdpcustjrny` | cdp | Customer Journey | `cdpcustjrny01` | `cdp_uk_customer_journey_db` | `cdp_uk_customer_journey_db_iceberg` |
| `cdpukcards` | cdp | Credit Cards | `cdpukcards01` | `cdp_uk_credit_card_db` | `cdp_uk_credit_card_db_iceberg` |
| `cdpukloans` | cdp | Consumer Loans | `cdpukloans01` | `cdp_uk_cnsmr_loan_db` | `cdp_uk_cnsmr_loan_db_iceberg` |
| `cdpretprod` | cdp | Retail Products | `cdpretprod01` | `cdp_uk_retail_account_db` | `cdp_uk_retail_account_db_iceberg` |
| `cdpukpayments` | cdp | UK Payments | `cdpukpayments01` | Not available | Not available |
| `cdprgltry` | cdp | Regulatory Reporting | `cdprgltry01` | Not available | Not available |
| `bdprgltry` | bdp | Regulatory | `bdprgltry01` | — | — |
| `bdpcontrolit` | bdp | Control IT | dedicated accounts — see aws skill | — | — |
| `bdpconsduty` | bdp | Consumer Duty | `bdpconsduty01` | — | — |
| `bdpukmarketing` | bdp | Marketing | `bdpukmarketing01` | — | — |
| `bdpukloans` | bdp | Consumer Loans | `bdpukloans01` | — | — |
| `bdpbbkyc` | bdp | BB KYC | `bdpbbkyc01` | — | — |
| `bdpbbrdsetl` | bdp | Risk Decisioning | `bdpbbrdsetl01` | — | — |
| `bdpcomplaints` | bdp | Complaints | `bdpcomplaints01` | — | — |
| `bdpchannels` | bdp | Channels | `bdpchannels01` | — | — |
| `bdpukcards` | bdp | Credit Cards | `bdpukcards01` | — | — |
| `bdpukspchl` | bdp | Specialist Domain | `bdpukspchl01` | — | — |
| `bdpsurveys` | bdp | Surveys | `bdpsurveys01` | — | — |

### Mesh JSON Metadata — BTB Owner, datasetType, datasetTypeSummary

> **Source:** Scanned from 963 production mesh JSON files across 27 feature team repos in `_repo_scan_workspace`.

| Feature Team Name | BTB Owner | datasetType | datasetTypeSummary.name | datasetTypeSummary.summary |
|---|---|---|---|---|
| `complaints` | `sdw_buk_btb` | — | — | — |
| `customer` | `buk_customer_btb` | `buk_customer_foundational_data_product` | `buk_customer_foundational_data_product` | buk_customer_foundational_data_product |
| `fdprefdata` | `sdw_buk_btb` | `foundation_uk_common_reference_data` | `foundation_uk_common_reference_data` | foundation_uk_common_reference_data_product |
| `fdpchnlcc` | `foundation_uk_contact_centre_channel_data_products_btb` | `foundation_uk_contact_centre_channel` | `foundation_uk_contact_centre_channel` | UK Contact Centre Foundational Data Product |
| `fdpukcards` | `sdw_buk_btb` | `uk_credit_cards` | `uk_credit_cards` | UK Credit Cards Data |
| `fdpbrnchchnl` | `foundation_uk_consumer_branch_data_products_btb` | `foundation_uk_consumer_branch` | `foundation_uk_consumer_branch` | Branch FDP tables |
| `fdpdigital` | `sdw_buk_btb` | `foundation_uk_digital_channels` | — | — |
| `fdpmortgage` | `buk_mortgage_btb` | `foundation_uk_mortgage_db` | — | — |
| `fdpukloans` | `fdp_consumer_loan_buk_btb` | `foundation_uk_consumer_loans` | — | — |
| `fdpbusbank` | `buk_bb_btb` | `foundation_uk_business_banking` | `foundation_uk_business_banking` | Foundational Data Product BUK Business Banking |
| `fdpnps` | `buk_nps_btb` | `buk_tnps_foundational_data_product` | `buk_tnps_foundational_data_product` | Transactional Net Promoter Score Foundation data product |
| `fdpbpf` | `sdw_buk_btb` | `foundation_uk_bpf` | `foundation_uk_bpf` | BPF Foundation data product |
| `fdpcolrcvy` | `sdw_buk_btb` | — | — | — |
| `fdpsavings` | `savings_buk_btb` | `foundation_uk_savings` | `foundation_uk_savings` | BUK Savings FDP will bring together key details for BUK Savings Accounts |
| `fdpcurrentaccount` | `buk_current_account_foundational_data_product` | `buk_current_account_foundational_data_product` | `buk_current_account_foundational_data_product` | Test UKBA Accounts table |
| `fdpprodins` | `insurance_buk_btb` | `foundation_uk_insurance` | `foundation_uk_insurance` | BUK insurance FDP will bring together key details for BUK insurance |
| `fdpcommchnl` | `sdw_buk_btb` | `foundation_uk_communication_channels` | `foundation_uk_communication_channels` | Communication Channel Foundational Data Product |
| `fdpbbcu` | `bb_cu_fdp` | `bb_current_account_fdp` | `bb_current_account_fdp` | BB current account FDP |
| `fdpbbsa` | `bb_sa_fdp` | `bb_savings_account_fdp` | `bb_savings_account_fdp` | BB savings account FDP |
| `fdpbbfx` | `bb_fx_fdp` | `bb_currency_account_fdp` | `bb_currency_account_fdp` | BB currency account FDP |
| `fdpsaukba` | `sdw_buk_btb` | — | — | — |
| `cdpcmplnts` | `sdw_buk_btb` | — | — | — |
| `cdpcustomer` | `buk_customer_btb` | `consolidated_uk_customer` | `consolidated_uk_customer` | BUK Customer Consolidated/Enterprise Data Product |
| `cdpproddom` | `prd_mstr_buk_btb` | `consolidated_uk_product_master` | `consolidated_uk_product_master` | BUK Product Master CDP |
| `cdpchannels` | `foundation_uk_contact_centre_channel_data_products_btb` | `consolidated_data_product_buk_channels` | `consolidated_uk_channels_data` | Consolidated data product tables of UK Channels |
| `cdpnps` | `buk_nps_btb` | — | — | — |
| `cdpbusbank` | `buk_bb_btb` | — | — | — |
| `cdpmortgage` | `buk_mortgage_btb` | — | — | — |
| `cdptrans` | `sdw_buk_btb` | — | — | — |
| `cdpukcards` | `sdw_buk_btb` | — | — | — |
| `cdpukloans` | `sdw_buk_btb` | — | — | — |
| `bdpukmarketing` | `buk_df_channel_communications` | `business_uk_customer_interaction` | `business_uk_customer_interaction` | Marketing Business Data Product |
| `bdpchannels` | `sdw_buk_btb` | — | — | — |
| `bdpukcards` | `sdw_buk_btb` | — | — | — |

#### BTB Owner Resolution Rules

1. **Domain-specific BTB** — look up from the table above by feature team name.
2. **Fallback** — if feature team not in table or value is `—`, use `sdw_buk_btb` (generic shared BTB group).
3. **RTB is always** `sdw_buk_rtb` across all teams.
4. **ITBS is always** `BSN0004626` across all teams.

#### datasetType Resolution Rules

1. `datasetType` is a **free-text string** (NOT restricted to ICEBERG/HIVE enum).
2. Look up from the table above by feature team name.
3. If not in table, derive as: `foundation_uk_<domain>` (FDP), `consolidated_uk_<domain>` (CDP), `business_uk_<domain>` (BDP).
4. `datasetTypeSummary` is **optional** — only include if the team has a known value in the table above.

---

## Related Skills

| Skill | Scope |
|-------|-------|
| `barclays-buk-data-product-builder:databricks-tenancy` | Databricks tenancy: team → workspace / catalog / service principal |
| `barclays-buk-data-product-builder:aws-data-products` | Infrastructure constants: account IDs, S3 naming patterns, glue.id |
| `barclays-buk-data-product-builder:service-management` | Runtime: ITSI codes, tool versions, state machines, known issues |

## Agent Self-Check

Before using this skill's data, verify:

- [ ] **Check 1**: target_database matches registry
- [ ] **Check 2**: bucket shortname resolved
- [ ] **Check 3**: BTB owner identified
- [ ] **Check 4**: datasetType assigned
- [ ] **Check 5**: Hive/Iceberg catalog determined
