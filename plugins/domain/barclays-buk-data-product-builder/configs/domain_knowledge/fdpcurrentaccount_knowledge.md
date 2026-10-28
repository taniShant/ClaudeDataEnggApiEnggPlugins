# fdpcurrentaccount Domain Knowledge

**Domain**: Current Account (Foundation Data Product)
**Tenancy**: `fdpcurrentaccount`
**Data Product Type**: FDP — sourced from BASE layer (`e_ukba_db`, `e_customer_db`, `e_cams_db`); target account DDA
**Last Updated**: 2026-06-19

---

## Business Context

- A **current account** is a standard transactional bank account for personal retail customers. Each account is identified by a unique `account_identifier` constructed as `10001013|{stg_id}`, where `stg_id` is the internal staging key from the BASE layer source table `e_ukba_db.tehacct`.
- Only **BUK** (Barclays UK) accounts are included in this product. Accounts belonging to the **BCI** trading entity are explicitly excluded post-transformation: `result_consolidated.filter(col("trading_entity_name") != "BCI")`.
- Only **retail (personal) customers** are included: accounts where `cus_cls = 'P'` (personal classification from `e_customer_db.tdlcust` joined via `e_customer_db.tdlbaho`), or accounts with a NULL customer classification that pass the referral stream filter (`mng_rfr_srm_num < 300 AND active = '1'` in `e_ukba_db.tehrefr`).
- Product scope is controlled via a join to `cdp_uk_product_db.product_cross_reference`, filtering to `application_product_classification_code = 'CU'` (current accounts) with `source_system_key IN (9999999, 10001013)` and `active = '1'`. This join is always broadcast.
- "Active" in the current account context means `active = '1'` (string) in the Iceberg partition column, derived from `eff_end_date = '3499-12-31'`. There is no separate status code filter analogous to mortgage `case_status_code` — use the `active` column or check `eff_end_date` directly.
- **Transactions** are sourced from two separate BASE tables and unioned: debit entries (`e_ukba_db.tehdent`) receive `tran_category_code = 'D'`; credit entries (`e_ukba_db.tehcent`) receive `tran_category_code = 'C'`. `.distinct()` is applied after union.
- **Limits** are sourced from two tables: `e_ukba_db.tehlmts` (standard limits, columns `lmt_typ`/`lmt_amt`) and `e_ukba_db.teholmt` (operational limits, columns `opr_lmt_typ_cde`/`ref_lmt`/`ant_lmt`). Both are unioned. For `teholmt`: `opr_lmt_typ_cde IN ('0','1')` → use `ref_lmt`; `opr_lmt_typ_cde = '2'` → use `ant_lmt`; otherwise null.
- **Profile markers** link a profile flag table (`e_ukba_db.tehplfm`, column `pfl_mkr_cde`) to a profile marker definition table (`e_ukba_db.tehpmrk`, column `prf_num`) via `pfl_mkr_cde = prf_num`. Each account can hold multiple profile markers.

---

## SCD2 Team-Specific Notes

- **`active` column** is string type `'1'`/`'0'` (NOT boolean) — derived via `when(col("eff_end_date") == lit("3499-12-31"), lit("1")).otherwise(lit("0"))`

---

## Source System Quirks

### Account Identifier Construction
- All tables use: `concat('10001013', '|', stg_id)` or `concat_ws('|', lit('10001013'), col('stg_id'))`
- `source_system_key = 10001013` (UKBA source system identifier), always cast as `bigint`
- Sort code is obtained from `e_ukba_db.xref_ukba_skey_tehbalt`, column `srt_cde`, trimmed: `F.trim(F.col("srt_cde")).alias("t54_sort_code")`
- Account number (`cus_acc_num`) is left-padded to 8 digits when matching to `tdlbaho`: `lpad(col("cus_acc_num").cast("string"), 8, '0')`

### Retail Account Filtering
- BUK-only: semi-join accounts to branch table (`e_ukba_db.tehbrch`) filtered to `t54_srp_trad_ent_id == "BUK"` via sort code mapping from `xref_ukba_skey_tehbalt`
- BCI explicitly excluded post-consolidation: `filter(col("trading_entity_name") != "BCI")`
- Personal customers: `cus_cls = 'P'` from `e_customer_db.tdlcust` (joined to `e_customer_db.tdlbaho` on `cus_idr`)
- NULL-classified customers: included if `mng_rfr_srm_num < 300 AND active = '1'` in `e_ukba_db.tehrefr`

### Transaction Table Source Merging
- `current_account_transaction` is a union of two source tables:
  - `e_ukba_db.tehdent` → `tran_category_code = 'D'`
  - `e_ukba_db.tehcent` → `tran_category_code = 'C'`, `ath_dat_tme = null (timestamp)`, `cqe_num = null (bigint)`
- `.distinct()` applied post-union — cross-table duplicates are dropped

### Column Type Casts

```sql
-- Balance amounts (tehblnc) — all cast to decimal(19,6):
CAST(led_bal AS DECIMAL(19,6)) AS ledger_balance_amount
CAST(cld_int_bal AS DECIMAL(19,6)) AS cleared_for_interest_balance_amount
CAST(cld_fat_bal AS DECIMAL(19,6)) AS cleared_for_fate_balance_amount
CAST(fds_avl AS DECIMAL(19,6)) AS funds_available_balance_amount

-- Transaction amount (tehdent/tehcent):
CAST(ent_amt AS DECIMAL(19,6)) AS transaction_amount

-- Monthly balance amounts (tehamsm) — all 10 monetary columns cast to decimal(19,6):
CAST(mth_end_bal AS DECIMAL(19,6)) AS month_end_balance_amount
-- ... (and 9 further monthly columns, same pattern)

-- Prepaid card balance — AC_INTRL_ID must be castable to int; records failing cast are dropped:
expr("try_cast(AC_INTRL_ID as int)") AS Card_Arrangement_Id
filter(col("Card_Arrangement_Id_int").isNotNull())
```

### TEHACLN Column Inconsistency
- `e_ukba_db.tehacln` contains records in two structural formats:
  - `active = '0'` rows: use `eff_start_date` / `eff_end_date` columns
  - `active = '1'` rows: use `start_date` / `end_date` columns (different names)
- Both subsets filtered to `end_date = '3499-12-31' OR end_date IS NULL`
- `active = '1'` subset: `start_date` → `eff_start_date`, `end_date` → `eff_end_date` via rename; then deduplicated with `ROW_NUMBER()` partitioned by `stg_id`, ordered by `end_date IS NULL` first
- Final union uses `unionByName()`

### NULL Patterns
- `account_open_reason_code`: built as `concat(rsn_opd_one, '-', rsn_opd_two)` — no null guard; may produce `"null-null"` strings when both source columns are null
- `account_close_reason_code`: same pattern
- Surrogate key lookups: `coalesce(col('ref_det_key'), lit(-99))` — all dimension lookups default to `-99` (bigint) on no match
- `transaction_identifier`: UUID generated via `expr("uuid()")` — never null
- Rows with null `account_number` or `account_identifier` are explicitly dropped before write

### Date Format Notes
- Source BASE tables provide `eff_start_date` / `eff_end_date` as `DATE` type — no YYYYMMDD integer casting required (unlike Mortgage domain)
- Date normalisation pattern: `to_date(date_format(col('eff_start_date'), "yyyy-MM-dd"))`
- Transaction date: `to_date(date_format(ent_dte, 'yyyy-MM-dd'))`
- Transaction post date: `to_date(date_format(ent_pst_dte, 'yyyy-MM-dd'))`
- Business date: `to_date(date_format(dw_bus_dt, 'yyyy-MM-dd'))`
- Transaction time: `cast(concat(ent_dte, ' ', ent_tme) as timestamp)` — string concatenation then cast, not `to_timestamp()`

---

## Reference Decode Lookups (REF_SRC_DECODE)

Reference data loaded from `{env-bucket}/dependencies/REF_SRC_DECODE.csv`. All joins are `left_outer`. Columns returned: `ref_src_cd`, `ref_cat_key`, `ref_det_key`.

| `ref_cat_key` | Target column | Source column joined | Table |
|---|---|---|---|
| `170001` (+ `src_system_key = '10001013'`) | `account_status_key` | `status` | `current_account` |
| `170301` | `business_type_analysis_key` | `bus_typ_anl_cde` | `current_account` |
| `170401` | `refer_reason_key` | `rfr_rsn_cde` | `current_account` |
| `170501` | `limit_type_key` | `limit_type_code` | `current_account_limit` |
| `170601` | `refer_stream_key` | `mng_rfr_srm_num` | `current_account` |
| `180101` | `transaction_amount_type_key` | `ent_amt_typ` | `current_account_transaction`, `current_account_interest_transaction` |
| `180201` | `transaction_source_key` | `ent_src` | `current_account_transaction`, `current_account_interest_transaction` |
| `180301` | `transaction_type_key` | `ent_typ` | `current_account_transaction`, `current_account_interest_transaction` |
| `180401` | `commission_interest_key` | `com_int_typ` | `current_account_interest_transaction` |
| `180501` | `transaction_2b_key` | `ent_2b_cde` | `current_account_transaction`, `current_account_interest_transaction` |
| `200104` | `Currency_Key` | `AC_CUR_CD` | `current_account_prepaid_card_balance` |

---

## Sensitive Columns (documentation only)

> **IMPORTANT**: This section is for documentation only. It does NOT trigger crypto detection.
> No Protegrity UDF calls (`cloud_api_udf_*_protect` / `cloud_api_udf_*_unprotect`) exist in any transform script — crypto is disabled across all tables in this product.

| Column | Notes |
|---|---|
| `account_number` | Sourced from `cus_acc_num` in `e_ukba_db.xref_ukba_skey_tehbalt`; passed through as string; no tokenization detected |
| `sort_code` | Sourced from `srt_cde` in `e_ukba_db.xref_ukba_skey_tehbalt`; trimmed, cast to string |
| `originator_beneficiary_account_number` | Sourced from `org_ben_acc` in `e_ukba_db.tehdent`/`tehcent`; cast to `int` in target |
| `originator_beneficiary_sort_code` | Sourced from `org_ben_brh` in `e_ukba_db.tehdent`/`tehcent`; cast to `int` in target |

---

## Infrastructure (Exceptions & Non-Derivable)

> Standard S3 paths, ITSI codes, account IDs, and state machine name are derivable from skills (aws, ops, tenancy). Only tenancy-specific exceptions documented here.

### S3 Path Exception
- `current_account_monthly_balance` UAT/PRD uses a non-standard bucket: `uat1-fdp-customer-590184123059-eu-west-1` / `prd1-fdp-customer-194722397519-eu-west-1` (does not follow Pattern 1; sourced from `config/current_account_monthly_balance/config.json`)

### ITSI Override (Per-Job)
- UAT Balance BAU job uses `SNSVC0074822` instead of the tenancy default `SNSVC0076170`

### Glue Worker Configuration

| Table | Operation | dev | uat | prd |
|---|---|---|---|---|
| `current_account` | BAU | G.1X / 120 | G.1X / 120 | G.4X / 120 |
| `current_account` | Day 0 | G.1X / 120 | G.4X / 160 | G.4X / 160 |
| `current_account_transaction` | BAU | G.1X / 10 | G.1X / 120 | G.4X / 40 |
| `current_account_transaction` | Day 0 | G.1X / 120 | G.1X / 120 | G.4X / 80 |
| `current_account_balance` | BAU | G.1X / 4 | G.1X / 4 | G.4X / 40 |
| `current_account_limit` | BAU | G.4X / 120 | G.1X / 10 | G.4X / 40 |

### Date Control Files
- Daily tables: `date_control/fdp_date_control.dat`
- Monthly balance only: `date_control/fdp_date_control_monthly.dat`

---

## Transformation Style for This Team

### Day 0 Historical Backfill Notes
- `current_account` Day 0: processes all accounts across full history using boundary-based temporal stitching — no single date filter column. Minimum boundary clipped to `min(acct.eff_start_date, balt.eff_start_date)` per `stg_id`.
- `current_account_monthly_balance` Day 0: records must satisfy `dw_bus_dt >= acct.eff_start_date AND dw_bus_dt < acct.eff_end_date` (temporal semi-join against current account iceberg).
- `current_account_transaction` Day 0: full union of `tehdent` + `tehcent`, filtered to accounts present in `current_account_iceberg` and where `dw_bus_dt` falls within the account's effective period.

### Temporal Stitching Pattern (NonTransactional tables)
All NonTransactional tables use boundary-based temporal stitching rather than a simple SCD2 CDC merge:
1. Collect all `eff_start_date` / `eff_end_date` values from every participating source table as boundary points
2. `Window.partitionBy(pkey).orderBy("date_point")` + `lead("date_point")` → contiguous `[eff_start_date, eff_end_date)` ranges
3. Filter: `eff_end_date IS NOT NULL AND eff_start_date < eff_end_date`
4. Semi-join valid ranges against `current_account_iceberg` to remove period breaks
5. Left-join each source attribute DataFrame into the valid ranges using: `base.eff_start_date >= src.eff_start_date AND base.eff_start_date < src.eff_end_date`

### Island Consolidation (`optimize_dataframe`)
After temporal stitching, consecutive rows with identical attribute values are merged:
```python
window = Window.partitionBy(key_columns).orderBy("eff_start_date")
df = df.withColumn("prev_end_date", lag("eff_end_date", 1).over(window))
df = df.withColumn("is_new_group", when(...isNull() | eff_start_date > prev_end_date, 1).otherwise(0))
df = df.withColumn("group_id", sum("is_new_group").over(window))
df = df.groupBy(key_columns + ["group_id"]).agg(min("eff_start_date"), max("eff_end_date"))
```
Used in: `balance`, `current_account_limit`, `current_account_monthly_balance`, `current_account_interest_transaction`, `profile_marker`.

### DataFrame Naming Conventions
- Main account: `result_with_acct` → `result_with_balt` → `result_with_dims` → `result_consolidated`
- Balance: `balance_df`, `valid_ranges`, `valid_ranges_final`, `final_df`
- Transaction: `final_df_1` (raw union), `final_df` (after lookups), `output_df` (after account filter)
- Limit: `df_curr_lim`, `final_df`
- Profile marker: `tehplfm_filtered`, `final_temporal`, `final_df`

### Broadcast Join Candidates
- `df_product_cross_reference` (active CU products, `cdp_uk_product_db`) — always broadcast
- `df_acct_restriction` (`e_ukba_db.account_restrictions_dat`) — always broadcast
- `tehpmrk` (profile marker definitions) — broadcast in BAU profile marker job
- `df_brch` (branch table, `e_ukba_db.tehbrch`) — broadcast after temporal optimization in Day 0

### Null-Handling Patterns
- Surrogate key lookups: `coalesce(col('ref_det_key'), lit(-99))` — use `-99` (bigint) as null sentinel, NOT null
- Reason code concatenation: `concat(col("rsn_opd_one"), lit('-'), col("rsn_opd_two"))` — no null guard; strings may contain literal `"null"`
- Date normalisation: `to_date(date_format(col('col_name'), "yyyy-MM-dd"))` throughout all scripts
- `eff_end_date` null coalesce in tehacln: `coalesce(col("eff_end_date"), lit("3499-12-31"))`

### Recurring Filter Patterns
- Active-only BAU reads: `active = '1'` (string, not boolean — the partition column type is string throughout)
- Transactional BAU business date filter: `dw_bus_dt = '{current_business_date}'`
- BCI exclusion: `filter(col("trading_entity_name") != "BCI")` — applied post-consolidation to `current_account` only
- BUK inclusion: `filter(col("t54_srp_trad_ent_id") == "BUK")` — applied on branch table before sort-code semi-join
- `account_number` / `account_identifier` null drop: `filter((col("account_number").isNotNull()) & (col("account_identifier").isNotNull()))` — applied to `current_account` before write

### Performance Patterns
- `StorageLevel.MEMORY_AND_DISK` on intermediate `distinct_boundaries_optimized` and `result_transformed` in main account Day 0 transform
- Repartition by `stg_id` before temporal joins: `repartition(total_cores, "stg_id")` where `total_cores = spark.conf.get("spark.default.parallelism")` (NOTE: `spark.sparkContext.defaultParallelism` is blocked on Shared Access Mode — use spark.conf instead)
- Active records written to CDC previous-file path (Parquet, 160 partitions, snappy compression, 256MB block size) before Iceberg write
- Profile marker BAU: 480 output partitions in `full_mode`, 120 in incremental mode

---

## Scheduling and Orchestration Hints

### `current_account` / `current_account_balance` / `current_account_limit`
- **Schedule type**: business_calendar
- **Bank holiday skip**: true
- **Sequential processing**: false
- **External dependencies**: BASE layer GCPR (DynamoDB) — source tables from `e_uk_currentaccount_db` must complete before DAG triggers
- **Notes**: Runs on UK banking business days; T-1 business date offset

### `current_account_transaction` / `current_account_interest_transaction`
- **Schedule type**: business_calendar
- **Bank holiday skip**: true
- **Sequential processing**: false
- **External dependencies**: BASE layer GCPR (DynamoDB)
- **Notes**: Transactional tables — daily events loaded on business days only

### `current_account_monthly_balance`
- **Schedule type**: [UNKNOWN — likely `cron` with monthly cadence; resolve at /gen-dag time]
- **Bank holiday skip**: [UNKNOWN — confirm with domain team]
- **Sequential processing**: false
- **External dependencies**: [UNKNOWN — may depend on current_account_balance completion]

### `current_account_profile_marker`
- **Schedule type**: business_calendar
- **Bank holiday skip**: true
- **Sequential processing**: false
- **External dependencies**: BASE layer GCPR (DynamoDB)
