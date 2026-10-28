# fdpcolrcvy Domain Knowledge

**Domain**: Collection and Recovery (Foundation Data Product)
**Tenancy**: `fdpcolrcvy`
**Data Product Type**: FDP — sourced from multiple legacy and modern collection/recovery systems (Cards, OneTallyman, Tallyman Loans, Mortgages, Strategic Debt Manager (SDM))
**Last Updated**: 2026-06-19

---

# 1. Executive Summary

The **Collection and Recovery Foundational Data Product (FDP)** is a PySpark-based data engineering pipeline running on AWS Glue within the DTX framework. It consolidates data from multiple legacy and modern collection/recovery systems into a unified Iceberg-based data model under the database `fdp_uk_coll_rcovry_db`.

**Repository Organization**:
- Organized by source system → flow type (legacy/forward_flow) → load type (day0/day1)
- Four main source system folders: `cards`, `onetallyman`, `tallyman_loans`, `mortgages`
- Shared generic components for temporal processing, date control, and S3 operations
- Each table has: config JSON, wrapper.py, transform.py, DTXOG config, date control file, and mesh schema JSON

**Major Source Systems Supported**:
1. **Cards (DM6 Legacy + DM11/SDM Forward Flow)** — most complete implementation
2. **Tallyman Loans (T4L)** — full Day 0/Day 1 separation with config-driven filters
3. **One Tallyman (1TM)** — legacy only, Day 0/Day 1 separation
4. **Mortgages (Secured Tallyman)** — legacy only, Day 0/Day 1 separation

**Major Loading Patterns**:
- Cards: single combined wrapper handles both Day 0 and Day 1 logic internally
- Tallyman Loans / OneTallyman / Mortgages: explicit Day 0 / Day 1 code 

---

# 2. End-to-End Architecture View

```
Source Systems (Glue Catalog - e_* databases)
    │
    ├── e_ngcb_debtmgr_db (DM11/SDM → Cards FF)
    ├── e_ukc_debtmgr_db (DM6 → Cards Legacy)
    ├── e_loans_tallyman_db (T4L → Tallyman Loans)
    ├── e_one_tallyman_db (1TM → OneTallyman)
    └── e_sec_tallyman_db (Secured → Mortgages)
         │
         ▼
    ┌─────────────────────────────────────────┐
    │  Wrapper (bin/{source}/{flow}/wrapper.py) │
    │  - Reads config JSONs                    │
    │  - Determines operation mode (day0/bau)  │
    │  - Manages date control                  │
    │  - Creates SparkSession                  │
    │  - Invokes transform object dynamically  │
    └───────────────────┬─────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────┐
    │  Integrate (fdp_uk_coll_rcovry_db/...)   │
    │  - Reads source tables via config        │
    │  - Applies date-based filters            │
    │  - Routes to Day0 or Day1 transform      │
    │  - Updates date control on success       │
    └───────────────────┬─────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────┐
    │  Transform (transform/{table}_transform) │
    │  - Core business logic                   │
    │  - Source extracts with date filters     │
    │  - Joins, derivations, CDC logic         │
    │  - Case ID generation                    │
    │  - Writes to staging (S3 parquet)        │
    │  - Writes to Iceberg target table        │
    └───────────────────┬─────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────┐
    │  Target: Iceberg Tables                  │
    │  glue_catalog.fdp_uk_coll_rcovry_db.*   │
    │  Partitioned by:                         │
    │    active / source_system_key /          │
    │    product_category_code                 │
    └─────────────────────────────────────────┘
```

**Orchestration**: DTXOG framework (EventBridge → Lambda → DynamoDB) schedules Glue jobs via dtxog config JSONs.

**Data Quality**: Custom validation in `utils/validation.py` — duplicate detection, null checks, row count assertions.

**Reference Data**: CSV files in `ref_data/` loaded separately via `bin/ref_data/wrapper.py`.

---

# 3. Product and Source-System Knowledge Base

## 3.1 UK Credit Cards — Legacy (DM6)

| Attribute | Value |
|-----------|-------|
| Source System | Debt Manager 6 (DM6) |
| Parent System | Triumph, NGCB |
| Source DB | `e_ukc_debtmgr_db` |
| Flow | Legacy |
| Day 0/Day 1 | Combined (single script, both handled) |
| Entry Point | `bin/cards/legacy/wrapper.py` |
| Config | `conf/cards/legacy/cards_leg_config.json` |
| Internal Source Key | `10001034` (UKC DM) |
| Target Tables | All 14 target tables supported |
| Key Quirk | Uses DM6-specific table names (`ny_extra_router_detail_1`, `tc_debt_item`, etc.) |
| Active Transform | Has separate `*_active_transform.py` and `*_stich_transform.py` files |

**Evidence**: `conf/cards/legacy/cnr_case_cards_leg_config.json` shows source tables from `e_ukc_debtmgr_db`

## 3.2 UK Credit Cards — Forward Flow (DM11/SDM)

| Attribute | Value |
|-----------|-------|
| Source System | Strategic Debt Manager (SDM) / DM11 |
| Parent System | Triumph, NGCB |
| Source DB | `e_ngcb_debtmgr_db` |
| Flow | Forward Flow (FF) |
| Day 0/Day 1 | Combined (handles both internally) |
| Entry Point | `bin/cards/forward_flow/wrapper.py` |
| Config | `conf/cards/forward_flow/cards_ff_config.json` |
| Internal Source Key | `10001088` (SDM) |
| Target Tables | 15 tables (includes `case_counts`, `case_trace` not in legacy) |
| Key Quirk | Large tag ID exclusion list (230+ IDs); uses `consumer_acct` tables |
| CDC Pattern | complex merge of delta + snapshot; backward fill for exit dates |

**Evidence**: `cnr_case_cards_ff_transform.py` line 124 — filters by `case_internal_source_system_key==10001088`

## 3.3 Personal Loans — Tallyman Loans (T4L)

| Attribute | Value |
|-----------|-------|
| Source System | Loan Tallyman (T4L) |
| Parent System | ALS |
| Source DB | `e_loans_tallyman_db` |
| Flow | Legacy |
| Day 0 | Separate: `loans_tallyman/legacy/day0/transform/` |
| Day 1 | Separate: `loans_tallyman/legacy/day1/transform/` |
| Entry Point | `bin/tallyman_loans/legacy/wrapper.py` |
| Config | `conf/tallyman_loans/legacy/loans_leg_config.json` |
| Key Quirk | Config-driven filters for day_0_run / day_1_bau_run / catch_up_mode |
| Generic Component | `generic_components/tallyman_loans/generic_functions_loans.py` |
| Tables Supported | 12 tables (cnr_case, case_acct_map, case_plan, case_position, etc.) |

**Evidence**: `conf/tallyman_loans/legacy/cnr_case_loans_leg_config.json` shows `filters` block with three modes

## 3.4 Business Loans / Business Current Accounts / Personal Current Accounts — One Tallyman (1TM)

| Attribute | Value |
|-----------|-------|
| Source System | One Tallyman (1TM) |
| Parent System | ALS (Business Loans) / UKBA (Current Accounts) |
| Source DB | `e_one_tallyman_db` (inferred) |
| Flow | Legacy |
| Day 0 | Separate: `onetallyman/legacy/day0/transform/` |
| Day 1 | Separate: `onetallyman/legacy/day1/transform/` |
| Entry Point | `bin/onetallyman/legacy/wrapper.py` |
| Config | `conf/onetallyman/legacy/onetallyman_leg_config.json` |
| Tables Supported | 6 tables (cnr_case, case_account_map, case_customer, case_hold, case_plan, third_party) |

**Evidence**: Directory `fdp_uk_coll_rcovry_db/onetallyman/legacy/` with day0/day1 subfolders

## 3.5 Mortgages — Secured Tallyman

| Attribute | Value |
|-----------|-------|
| Source System | Secured Tallyman |
| Parent System | ILP |
| Source DB | `e_sec_tallyman_db` (inferred) |
| Flow | Legacy |
| Day 0 | Separate: `mortgages/legacy/day0/transform/` |
| Day 1 | Separate: `mortgages/legacy/day1/transform/` |
| Entry Point | `bin/mortgages/legacy/wrapper.py` |
| Config | `conf/mortgages/legacy/mortgages_leg_config.json` |
| Tables Supported | 5 tables (cnr_case, case_account_map, case_customer, case_hold, case_plan) |
| Key Quirk | Has `*_active1_transform.py` files for special active-record handling |

**Evidence**: `fdp_uk_coll_rcovry_db/mortgages/legacy/day0/transform/` directory listing

---

# 4. Data Transformation Style

## 4.1 CDC/SCD2 Pattern

The CDC pattern (from cards FF `cnr_case`):
1. Read existing target table (snapshot)
2. Generate new records (delta)
3. Union delta + snapshot with flag column
4. Apply window functions to detect changes
5. Classify: INSERT / UPDATE / DELETE / NO CHANGE
6. Populate eff_end_date using `lead()` over window
7. Set `active` column: `"1"` if `eff_end_date == "3499-12-31"`, else `"0"`

## 4.2 Case ID Generation

Case IDs follow the pattern: `{source_system_key_prefix}{sequential_number}`
- Example: `1088` prefix + dense_rank = `108800001`, `108800002`, etc.
- Max case_id is fetched via `spark.sql("SELECT MAX(CASE_ID)...")`
- New case IDs are generated using `dense_rank()` window function
- Case ID history is maintained in `fdp_uk_coll_rcovry_db.case_identifier`

## 4.3 Audit Columns

All target tables include:
- `eff_start_date` (DATE) — effective start
- `eff_end_date` (DATE) — effective end, `3499-12-31` for active
- `dw_lod_tmp` (TIMESTAMP) — load timestamp via `current_timestamp()`
- `dw_upd_lod_tmp` (TIMESTAMP) — update load timestamp
- `active` (STRING) — `"1"` or `"0"` (partition column)

## 4.4 Staging/Checkpointing

Intermediate results are written to S3 staging paths:
```
s3://{bucket}/stg/{source_abbrev}/{table}/
s3://{bucket}/stg/{source_abbrev}/{table}/checkpoints/
```
- Cards FF uses: `stg/dm11/cnr_case/`
- Cards Legacy uses: `stg/dm6/cnr_case/`
- Tallyman uses: `stg/tallyman/legacy/cnr_case/`

---

# 5. Source System Quirks Catalog

## 5.1 DM6 (Cards Legacy) vs DM11/SDM (Cards Forward Flow)

| Quirk | DM6 | DM11/SDM |
|-------|-----|----------|
| Database | `e_ukc_debtmgr_db` | `e_ngcb_debtmgr_db` |
| Case detection | Router tables (`n9_router_account`) | Tags (`consumer_acct_tag`) |
| Source key | `10001034` | `10001088` |
| Account linking | Direct DM6 account references | Uses `consumer_acct.cnsmr_accnt_crdtr_rfrnc_id_txt` |
| Account ID resolution | Built into table structure | Requires join to `fdp_uk_credit_card_db.cr_card_acct_rel` |
| Collection/Recovery status | Derived from DM6 route codes | Derived from tags (`COLLS`/`RECS`/`PPECURED`) |
| Test account exclusion | Unknown | Hardcoded account IDs `8956`, `8957` excluded |

## 5.2 SDM Tag System

The SDM forward flow relies heavily on a tag-based system:
- Tags have types (`tag_type.tag_typ_shrt_nm`)
- `AREASA` tag type with `COLLS` = Collections, `RECS` = Recoveries
- `PPECURED` tag = case cured
- Soft delete flag (`cnsmr_accnt_sft_delete_flg`) differentiates active vs deleted tags
- **230+ tag IDs are explicitly excluded** — these appear to be system/internal tags

## 5.3 Tallyman Table Naming

All Tallyman source tables use abbreviated prefixes:
- `tetltcad` = account details
- `tetltccc` = case creation/collection
- `tetlcaac` = account activity context
- `tetltcrc` = recovery details
- `tetltcco` = charge-off details
- `tetltaba` = account balance/arrears
- `tetltctp` = Third party details
- `tetltccd` = Cured details 
- `tetltcds` = debt sale
- `tetlccaa` = account activity (transactional)

## 5.4 Account Source System Key Mapping (Cards FF)

```python
# From cnr_case_cards_ff_transform.py line 566
"AMAZNCRD" → "NGCB"
"BARCCARD" → "Triumph"  
default → "NGCB"
```

## 5.5 Reference Stock Integration (Tallyman Loans)

Tallyman loans uses `pre_coll_rcvry_ref_data.reference_stock` for stock categorization with `segment_id`, `route_id`, `worklist_id` → `stock_category_level1_name`.

## 5.6 Temporal Join Pattern (Tallyman)

Tallyman systems use a temporal union join pattern (`TemporalDataUtils.create_temporal_union_join`) to handle overlapping effective date ranges from multiple SCD2 tables.

---

# 6. Day 0 / Day 1 Population Pattern Analysis

## 6.1 Pattern Matrix

| Product | Source System | Flow | Day 0 | Day 1 | Script Separation | Script Path(s) |
|---------|--------------|------|-------|-------|-------------------|----------------|
| Credit Cards | DM6 | Legacy | Yes | Yes | **Combined** (in-class routing) | `cards/legacy/transform/*` |
| Credit Cards | DM11/SDM | Forward Flow | Yes | Yes | **Combined** (in-class routing) | `cards/forward_flow/transform/*` |
| Personal Loans | T4L | Legacy | Yes | Yes | **Separate** (day0/ + day1/) | `loans_tallyman/legacy/day{0,1}/` |
| Business Loans/CA | 1TM | Legacy | Yes | Yes | **Separate** (day0/ + day1/) | `onetallyman/legacy/day{0,1}/` |
| Mortgages | Secured TM | Legacy | Yes | Yes | **Separate** (day0/ + day1/) | `mortgages/legacy/day{0,1}/` |

## 6.2 Day 0 Semantics

- **Purpose**: Initial/full population of a target table
- **Filter**: `eff_start_date <= '{current_business_date}'` (all history up to now)
- **For transactional tables**: `dw_bus_dt <= '{current_business_date}'`
- **Triggered by**: `operation = 'day0'` parameter passed to Glue job
- **Writes**: Full table overwrite or fresh append

## 6.3 Day 1 (BAU) Semantics

- **Purpose**: Daily incremental processing
- **Filter**: `eff_start_date <= '{current_business_date}' AND eff_end_date > '{current_business_date}'`
- **For transactional tables**: `dw_bus_dt == '{current_business_date}'`
- **Special**: `tetlccaa` has custom filter with ±365 day window for `datetime1`
- **Writes**: Append inactive + overwrite active partition

---

# 7. Data Model and Mapping Insights

## 7.1 Key Reference Data Values

From `reference_source_decode.csv`:
| reference_detail_key | source_system_key | code | description |
|---------------------|-------------------|------|-------------|
| 10001088 | 10001088 | SDM | Strategic Debt Manager (DM11) |
| 10001090 | 10001090 | NGCB | NGCB |
| 10001031 | 10001031 | Triumph | Triumph UK Cards |
| 10001034 | 10001034 | UKC DM | UK Cards Debt Manager |

## 7.2 Cross-Domain Dependencies

The FDP reads from other FDPs:
- `fdp_uk_credit_card_db.cr_card_acct_rel` — account relationship for Cards
- `fdp_uk_cnsmr_loan_db_iceberg.consumer_loan_account` — for loan account identifiers
- `fdp_uk_cnsmr_loan_db_iceberg.consumer_loan_account_status` — for account status
- `pre_coll_rcvry_ref_data.reference_stock` — stock reference data

---

# 8. Code Generation Guidance for Claude Code

## How Claude Code Should Generate Code for Collection and Recovery FDP

### Core Principles

1. **Match the naming convention exactly**: `{table}_{source_abbrev}_{flow_abbrev}_transform`
2. **Use the correct source system key**: Never guess — look up in `ref_data/reference_source_decode.csv`
3. **Respect the Day0/Day1 separation**: For tallyman/onetallyman/mortgages, create separate day0 and day1 transform files
4. **Use config-driven source reading**: New code should read tables via config JSON, not hardcode table names
5. **Maintain CDC/SCD2 semantics**: active='1' for current, active='0' for history, eff_end_date='3499-12-31' for open

### A. Checklist Before Generating Code

- [ ] Identify source system and flow type (legacy vs forward_flow)
- [ ] Determine if this is Cards (combined) or Tallyman/OTM/Mortgages (separated Day0/Day1)
- [ ] Identify the correct source database prefix (`e_*_db`)
- [ ] Identify the `case_internal_source_system_key` value from reference data
- [ ] Define target table columns from `schemas/` JSON
- [ ] Identify partition columns from mesh JSON
- [ ] Set up date control configuration in table-level config JSON
- [ ] Determine CDC keys and columns from similar existing configs
- [ ] Check if table needs case_id generation or uses existing case_id

### B. Checklist Before Modifying Existing Pipelines

- [ ] Read the full existing transform file to understand current logic
- [ ] Check the config JSON for CDC keys, filters, and date control settings
- [ ] Verify which source tables are used and their effective date filtering
- [ ] Check if there are staging/checkpoint paths that need updating
- [ ] Verify the write pattern (append vs overwritePartitions)
- [ ] Ensure no breaking changes to downstream CDC logic
- [ ] Check if any `*_active_transform.py` or `*_stich_transform.py` exists

### C. Checklist Before Raising a Merge Request

- [ ] All new files follow the exact naming convention
- [ ] Config JSON has all required fields (source, target, date_control, cdc if applicable)
- [ ] DTXOG config JSON created with correct BYOC section
- [ ] Date control `.dat` file initialized
- [ ] `__init__.py` files updated for new modules
- [ ] Tests added (even if mocked)
- [ ] No hardcoded S3 bucket paths (use config)
- [ ] No hardcoded business dates
- [ ] Active flag correctly set (`"1"` not `1`, `"0"` not `0` — STRING type)

### D. Common Mistakes a Coding Agent Might Make

1. **Wrong active flag type**: Must be STRING `"1"`/`"0"`, not integer
2. **Wrong high-end date**: Must be `3499-12-31`, not `9999-12-31`
3. **Missing partition columns**: `cnr_case` partitions on 3 columns: active, case_internal_source_system_key, product_category_code
4. **Wrong source system key**: Each source system has a specific numeric key — never guess
5. **Mixing DM6 and DM11 table names**: These are completely different schemas
6. **Forgetting date control update**: Must call `date_control_obj.update_date_control()` at end
7. **Not handling catch_up_mode**: Tallyman pipelines have 3 modes, not 2
8. **Wrong write semantics**: Active records → overwritePartitions, inactive → append
9. **Missing `glue_catalog.` prefix**: Iceberg writes must use `glue_catalog.` prefix
10. **Wrong date format**: Date control uses `%Y%m%d`, business dates use `%Y-%m-%d` after conversion
11. **Not filtering by source system key when reading target**: Must filter existing target by source_system_key to avoid cross-contamination

### E. Recommended Prompt Context for Future Sessions

When working on this repository, include:
- Which source system (DM6/DM11/T4L/1TM/Secured Tallyman)
- Which target table
- Whether this is Day 0 or Day 1 (or both)
- The business requirement or mapping document
- The target table schema from `schemas/` folder
- An example of the same table from another source system (for pattern reference)

---

# 9. Knowledge Gaps and Open Questions

1. **No Forward Flow for Tallyman Loans, OneTallyman, or Mortgages** — only legacy flow exists. Is FF planned?
2. **Missing `case_contact_strategy` implementation** — schema exists but no production code found (only data analysis SQL)
3. **Missing `case_identifier` standalone pipeline** — appears to be populated inline within cnr_case transforms
4. **No explicit Day 0 code for Cards** — Cards transforms appear to handle Day 0 implicitly but the routing logic is less clear than Tallyman
5. **Test coverage appears minimal** — only `conftest.py`, `wrapper_test.py`, `test_helpers.py`, `date_validator_test.py`, `purge_script_test.py`
6. **Reference data tables** (`reference_debt_purchaser_detail`, `reference_debt_sale_segment_price`, `reference_stock`) — loaded via separate DTXOG jobs but no clear Python transform code in repository
7. **`data_analysis/` folder** — contains raw SQL analysis scripts; unclear if these are production dependencies or exploratory
8. **Cards `*_stich_transform.py` files** — purpose of "stitch" logic unclear without reading full file
9. **Crypto usage** — configuration exists but no actual Protegrity UDF calls found in transform code
10. **`cnr_case_dup` table** — used as intermediate in Cards FF; unclear if this is a permanent table or temporary
11. **Consumer Duty (reference_category_key 80001)** — category exists in reference data but no clear transform logic visible

---

# 10. Glossary

| Term | Meaning |
|------|---------|
| FDP | Foundational Data Product — single-domain, source-agnostic cleansed data |
| FF | Forward Flow — data sourced from SDM (Strategic Debt Manager) |
| Legacy | Data from older collection systems (DM6, Tallyman variants) |
| Day 0 | Initial/full historical load of a target table |
| Day 1 | Daily incremental (BAU) processing |
| BAU | Business As Usual — day 1 incremental processing |
| 1TM | One Tallyman — source system for Business Loans, Business CA, Personal CA |
| T4L | Tallyman for Loans — source system for Personal Loans |
| DM6 | Debt Manager 6 — legacy credit card collections system |
| DM11 | Debt Manager 11 — newer credit card collections (part of SDM) |
| SDM | Strategic Debt Manager — modern collections platform replacing legacy systems |
| ALS | Account Lending System — parent system for loans |
| UKBA | UK Branch Accounting — parent system for current accounts |
| ILP | Integrated Lending Platform — parent system for mortgages |
| NGCB | Next Generation Credit Bureau — credit card parent system |
| Triumph | Legacy credit card platform |
| CDC | Change Data Capture — detecting inserts/updates/deletes |
| SCD2 | Slowly Changing Dimension Type 2 — track history via eff_start/end dates |
| DTXOG | DTX Orchestration Glue — job scheduling framework |
| BYOC | Bring Your Own Code — DTXOG mode for custom PySpark |
| DTX | Data Transformation eXtended framework |
| EDP | Enterprise Data Platform team |
| DDA | Datalake Domain Account |
| Mesh JSON | Table creation definition file used by EDP for Glue catalog |
| Iceberg | Apache Iceberg table format used for ACID transactions |
| Active flag | "1" = current record, "0" = historical/superseded |
| stg_id | Stage ID — unique record identifier in Tallyman source tables |
| cnsmr_accnt_id | Consumer Account ID — primary key in DM11 consumer_acct table |
| case_id | Synthetic primary key for cnr_case — format: `{source_prefix}{sequential}` |
| product_category_code | CARDS, LOANS, MORTGAGES — identifies the product domain |
| `3499-12-31` | Standard high-end date indicating "currently active" or "no end date" |

---

## Scheduling and Orchestration Hints

> **Note:** Scheduling details should be confirmed with the Collections & Recovery data team. The hints below are defaults based on typical patterns.

### General Pattern (NonTransactional entity tables — cnr_case, case_account_map, case_position, etc.)
- **Schedule type**: business_calendar
- **Bank holiday skip**: true
- **Sequential processing**: false
- **External dependencies**: BASE layer GCPR (DynamoDB) — source tables from Tallyman/DM11 must complete before DAG triggers
- **Notes**: Runs on UK banking business days; T-1 business date offset

### Transactional tables (case_recovery_transaction, case_contact_strategy)
- **Schedule type**: business_calendar
- **Bank holiday skip**: true
- **Sequential processing**: false
- **External dependencies**: BASE layer GCPR (DynamoDB)
- **Notes**: Append-only event tables loaded on business days
