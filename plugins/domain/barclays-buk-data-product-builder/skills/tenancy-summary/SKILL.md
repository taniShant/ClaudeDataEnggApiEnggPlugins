---
name: tenancy-summary
description: "Tenancy lookup — lightweight summary of Feature Team Name → database name mappings, split by platform. Glue table: Hive, Iceberg databases + S3 bucket shortnames. Databricks table: Target DB names. For full infrastructure details (service principals, AD groups, catalogs, tagging info), load aws-tenancy or databricks-tenancy directly."
user-invocable: false
owner: "tom.franklin@barclays.com"
review_cadence: quarterly
last_reviewed: 2026-09-10
---

**Source:** Tom Franklin | **Owner:** tom.franklin@barclays.com | **Review:** Quarterly | **Last reviewed:** 2026-09-10

# Tenancy Summary — Unified Lookup

## When to Use This Skill

Use when:
- Resolving a `target_database` value to a Feature Team Name and tenancy
- Domain knowledge auto-discovery (matching target database against known registries)
- Tenancy name derivation from database name

Do NOT use for:
- Generating infrastructure artefacts (S3 paths, workspace folders, service principals) → load `aws-tenancy` or `databricks-tenancy` directly
- Constructing Mesh JSON metadata (BTB owner, datasetType) → use `aws-tenancy`
- Databricks Asset Bundle (DABs) configuration (catalogs, AD groups, tagging) → use `databricks-tenancy`

## Lookup Rules

When matching `target_database`:
- **Glue platform**: match against Hive Database or Iceberg Database columns in the **Glue / AWS Tenancies** table below
- **Databricks platform**: match against Databricks Target DB column in the **Databricks Tenancies** table below

1. **Strip whitespace**: trim leading/trailing whitespace from the input value
2. **Case-insensitive**: compare lowercase input against lowercase registry values
3. These rules apply to all consumers: domain knowledge auto-discovery (STEP 2.1), env_config resolution (STEP 2.6), tenancy name derivation, and any other registry lookup

## Glue / AWS Tenancies

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
| `bdprgltry` | bdp | Regulatory | `bdprgltry01` | Not available | Not available |
| `bdpcontrolit` | bdp | Control IT | dedicated accounts — see aws skill | Not available | Not available |
| `bdpconsduty` | bdp | Consumer Duty | `bdpconsduty01` | Not available | Not available |
| `bdpukmarketing` | bdp | Marketing | `bdpukmarketing01` | Not available | Not available |
| `bdpukloans` | bdp | Consumer Loans | `bdpukloans01` | Not available | Not available |
| `bdpbbkyc` | bdp | BB KYC | `bdpbbkyc01` | Not available | Not available |
| `bdpbbrdsetl` | bdp | Risk Decisioning | `bdpbbrdsetl01` | Not available | Not available |
| `bdpcomplaints` | bdp | Complaints | `bdpcomplaints01` | Not available | Not available |
| `bdpchannels` | bdp | Channels | `bdpchannels01` | Not available | Not available |
| `bdpukcards` | bdp | Credit Cards | `bdpukcards01` | Not available | Not available |
| `bdpukspchl` | bdp | Specialist Domain | `bdpukspchl01` | Not available | Not available |
| `bdpsurveys` | bdp | Surveys | `bdpsurveys01` | Not available | Not available |

## Databricks Tenancies

| Feature Team Name | DP Type | Domain | Databricks Target DB |
|---|---|---|---|
| `BUK_BBKYC_BDP` | BDP | Business Banking | `bdp_uk_bbcdd_db_dbxw` |
| `BUK_BUSBANK_BDP` | BDP | Business Banking CDD | `bdp_uk_busbank_db_dbxw` |
| `BUK_BUSBANK_CDP` | CDP | Business Banking | Not available |
| `BUK_CARDSCOMM_CDP` | CDP | Card Commercial | `cdp_uk_credit_card_db` |
| `BUK_CCD` | BDP | Customer Communications Delivery (CCD) | `BUK_CCD_Campaign_DB` |
| `BUK_COMPLAINTS_BDP` | BDP | Complaints | Not available |
| `BUK_COMPLAINTS_CDP` | CDP | Complaints | `cdp_uk_complaints_db_dbx` |
| `BUK_CONSUMER_LOANS_BDP` | BDP | Consumer Loans | Not available |
| `BUK_CONTROLIT_BDP` | BDP | ControlIT | `buk_controlit_db` |
| `BUK_CUSTOMER_BDP` | BDP | Customer | Not available |
| `BUK_CUSTOMER_FDP` | FDP | Customer | Not available |
| `BUK_DIGITALROLB_BDP` | BDP | Digital ROLB | Not available |
| `BUK_ECF` | BDP | Current Account (ECF) | `bdp_uk_current_acct_db` |
| `BUK_ESC_BDP` | BDP | Exec ScoreCards | Not available |
| `BUK_INSURANCE_BDP` | BDP | Insurance | `BDP_UK_INSURANCE_AND_PACKS_DB_DBX` |
| `BUK_MARKETING_BDP` | BDP | Marketing | `BDP_UK_MARKETING_DB_DBX` |
| `BUK_MARKETING_CIDP` | BDP | MarTech / CIDP | `BUK_MDP_PARTNER_PRD` |
| `BUK_MORTGAGES_BDP` | BDP | Mortgages | Not available |
| `BUK_MORTGAGES_CDP` | CDP | Mortgages CDP | `cdp_uk_mortgages_db_dbx` |
| `BUK_OTMI` | BDP | OTMI | Not available |
| `BUK_PAFER_BDP` | BDP | PAFER (Regulatory) | `bdp_uk_pafer_db` |
| `BUK_PLATFORM` | NA | Platform | `buk_cdao_platform` |
| `BUK_UKBA_FDP` | FDP | UKBA | `fdp_uk_ukba_db` |
| `TSC_CUSTOMER_FDP` | FDP | Customer | `dev_tsc_customer_fdp` |
| `UK-BUK DEV` | BI Reporting | BUK-Marketing | Not available |
| `UK-BUK-Marketing-MI` | BI Reporting | BUK-Marketing | Not available |

## Escalation

> **Need full infrastructure details?** Load the platform-specific skill:
> - **Glue/AWS**: `aws-tenancy` — S3 paths, BTB owners, datasetType, Hive/Iceberg databases
> - **Databricks**: `databricks-tenancy` — service principals, AD groups, catalogs, tagging

## Agent Self-Check

Before using this skill's data, verify:

- [ ] **Check 1**: platform lookup matches target
- [ ] **Check 2**: tenancy name resolved
- [ ] **Check 3**: database name confirmed
- [ ] **Check 4**: no stale entries used
- [ ] **Check 5**: cross-platform consistency verified
