# fdpmortgage Domain Knowledge

**Domain**: Mortgage (Foundation Data Product)
**Tenancy**: `fdpmortgage`
**Data Product Type**: FDP — sourced from BASE layer; target account DDA
**Last Updated**: 2026-06-03

---

## Business Context

- A **mortgage case** represents a single mortgage application lifecycle from submission through to full redemption or write-off. One customer may hold multiple concurrent mortgage cases.
- A **mortgage account** is opened once a case reaches completion (offer accepted and funds drawn down). Not all cases result in an account — declined and withdrawn cases never reach account stage.
- **Arrears** are tracked at account level, not case level. A case in arrears has an associated arrears flag and outstanding balance shortfall.
- **Product transfer** (PT): an existing mortgage customer switching to a new rate without a new case. PT events produce a new `product_code` and `rate_effective_date` on the existing account row — they do NOT create a new case or account.
- **Further advance** (FA): additional borrowing against an existing mortgage. FAs create a new sub-account (`sub_acct_id`) linked to the original account.
- "Active" in the mortgage context means `case_status_code NOT IN ('CLO', 'RED', 'WOF')` — do not filter on raw active flag from BASE; use `case_status_code` directly.

---

## SCD2 Team-Specific Notes

- **Pipeline-specific CDC exclusion** (`cdc_exclude_cols`) — beyond the standard audit columns:
  - `source_extract_timestamp` — appears in some BASE tables; always changes, never represents a business change
  - `batch_id` — ETL batch identifier from BASE; exclude from hash

---

## Source System Quirks

### Day 0 Historical Filter
- For Day 0 historical loads: process all cases regardless of `row_lst_mod_dte`
- Day 0 filter: `case_create_date <= '{current_business_date}'` — no date upper bound on source

### Date Format Issues
- `row_lst_mod_dte` in source table `mrt_mortgage_case` is stored as `YYYYMMDD` integer (e.g. `20240315`). Must be cast before use:
  ```sql
  CAST(TO_DATE(CAST(row_lst_mod_dte AS STRING), 'yyyyMMdd') AS DATE) AS row_lst_mod_dte
  ```
- `case_create_date` and `offer_expiry_date` are also `YYYYMMDD` integer — apply same cast.
- `payment_date` in `mrt_mortgage_payment` is already `DATE` type — no cast required.

### NULL Patterns
- `product_transfer_date` is NULL for all cases that have never had a product transfer — this is valid; do NOT filter out NULL values.
- `arrears_start_date` is NULL when account is not in arrears — expected; do not coalesce or replace.
- `sub_acct_id` is NULL for primary accounts (not further advance sub-accounts) — expected; do not filter.
- `redemption_date` is NULL for all open mortgages — expected; populate only on closed cases.

### Source System Join Behaviour
- `mrt_mortgage_case` and `mrt_mortgage_account` join on `case_id`. Not all cases have an account — use LEFT JOIN when linking to account; inner join will silently drop pipeline and declined cases.
- `mrt_mortgage_case` contains duplicate rows for the same `case_id` within the same `row_lst_mod_dte` when multiple system events fire on the same day. Deduplicate using `ROW_NUMBER() OVER (PARTITION BY case_id ORDER BY case_event_seq DESC)` before CDC merge.
- `mrt_mortgage_payment` may contain reversed payments with `payment_type_code = 'REV'`. These are legitimate events — do NOT filter them out; they must appear as separate rows in the target.

### Dedup Guard for As-Of / Range Joins

When source tables are joined using inequality conditions (as-of joins, range joins, temporal joins), duplicate rows WILL occur unless sources are deduped first.

**Detection Rule:**
```
IF transformation involves:
  - As-of join (join on account + date range / effective period)
  - Range join (between conditions on dates/values)
  - Multiple rows per key in EITHER side of a left/inner join
THEN:
  MANDATORY: Apply ROW_NUMBER() OVER (PARTITION BY join_key ORDER BY priority_col DESC) 
  dedup BEFORE the join, keeping only rn=1 per join_key.
```

**Enforcement (Day0 only — Day1 receives pre-filtered active=1 data):**
- Before any as-of or range join, apply `ROW_NUMBER` window to the dimension being joined:
  ```python
  from pyspark.sql.window import Window
  w = Window.partitionBy('join_key').orderBy(F.col('priority_col').desc())
  deduped_df = source_df.withColumn('_rn', F.row_number().over(w)).filter(F.col('_rn') == 1).drop('_rn')
  ```
- `rates_fees_wm`: use `lrf_index` as the ORDER BY column for dedup window.
- Suffix convention for deduped intermediate DataFrames: `_lrf` ("last-row-filtered").

### Column Type Mismatches vs Mapping Document
- Mapping document declares `outstanding_balance` as `decimal(15,2)` — source stores as `float`. Cast to `DECIMAL(15,2)` in transformation:
  ```sql
  CAST(outstanding_balance AS DECIMAL(15,2)) AS outstanding_balance
  ```
- `ltv_ratio` (loan-to-value) is stored as a whole number percentage in source (e.g. `75` for 75%) but mapping document specifies it as a `decimal(5,2)`. Divide by 100 in transformation:
  ```sql
  CAST(ltv_ratio AS DECIMAL(5,2)) / 100 AS ltv_ratio
  ```

---

## PII / Sensitive Columns (documentation only)

> **IMPORTANT**: This section is for documentation only. It does NOT trigger crypto detection.
> Crypto is triggered ONLY by explicit `cloud_api_udf_<DE>_(un)protect(col)` UDF pattern
> in the `Business Logic/Transformation Logic` column of the mapping document.

The following columns may be sensitive and should be reviewed against the mapping transformation logic for tokenization/detokenization requirements:

| Column | Sensitivity | Notes |
|---|---|---|
| `applicant_sort_code` | PII — bank account identifier | May require tokenization if written to target |
| `applicant_account_number` | PII — bank account identifier | May require tokenization if written to target |
| `national_insurance_number` | PII — government identifier | Typically tokenized in BASE; detokenize before transformation if needed |
| `applicant_dob` | PII — date of birth | Usually passed through masked (year only); check mapping |

---

## Unity Catalog Names (Databricks only)

- **DDA catalog** (FDP tables): `DEV_BUK_MORTGAGE_FDP` (dev), `UAT_BUK_MORTGAGE_FDP` (uat), `PRD_BUK_MORTGAGE_FDP` (prod)
- **Schema**: `fdp_mortgage_db`
- Note: Unity Catalog names must be confirmed with the platform team before first deployment.

---

## Transformation Style for This Team

### Intermediate DataFrame Naming
- Use `_lrf` suffix for "last-row-filtered" DataFrames (after deduplication step): e.g. `case_lrf`, `account_lrf`
- Use `_cast` suffix for DataFrames after date/type casting: e.g. `case_cast`
- Use `_joined` suffix after multi-table joins: e.g. `case_account_joined`
- Final transformed DataFrame before load: `transformed_df` (standardised across all scripts)

### SQL Alias Conventions in spark.sql()
- Always qualify column references with table alias in multi-table SQL: `c.case_id`, `a.account_id`
- Avoid single-letter aliases for clarity: use `c` for case, `a` for account, `p` for payment

### Null-Handling Patterns
- Use `F.coalesce()` before string concatenation to prevent null propagation: `F.coalesce(col, F.lit('UNKNOWN'))`
- Never use `fillna()` on date columns — use `F.when(condition, value).otherwise(F.lit(None))` to preserve null semantics
- `CASE WHEN col IS NULL THEN 'N' ELSE 'Y' END` pattern preferred for null-to-flag derivations

### Broadcast Join Candidates
- `dim_case_status` lookup table (~200 rows) — always broadcast when joining to case
- `dim_product_type` lookup table (~50 rows) — always broadcast
- `dim_channel` lookup table (~30 rows) — always broadcast
- Add `/*+ BROADCAST(alias) */` hint in `spark.sql()` calls for these tables

### Recurring Filter Patterns
- Active-only BAU filter for NonTransactional source reads: `active = 1`
- Current business date partition filter for Transactional source reads: `dw_bus_dt = '{current_business_date}'`
- Exclude test/dummy cases: `case_id NOT LIKE 'TST%' AND case_id NOT LIKE 'DMY%'`
  - This filter is business-validated and should be applied to all case-level source reads

---

## Scheduling and Orchestration Hints

### `fdp_mortgage_case`
- **Schedule type**: business_calendar
- **Bank holiday skip**: true
- **Sequential processing**: false
- **External dependencies**: BASE layer GCPR (DynamoDB) — `e_uk_mortgage_db.mrt_mortgage_case` must complete before DAG triggers
- **Notes**: Runs Tue–Sat aligned with UK banking business calendar; T-1 business date offset

### `fdp_mortgage_account`
- **Schedule type**: business_calendar
- **Bank holiday skip**: true
- **Sequential processing**: false
- **External dependencies**: BASE layer GCPR (DynamoDB) — `e_uk_mortgage_db.mrt_mortgage_account` must complete before DAG triggers
- **Notes**: Same schedule as fdp_mortgage_case — aligned with UK banking business calendar

### `fdp_mortgage_payment`
- **Schedule type**: business_calendar
- **Bank holiday skip**: true
- **Sequential processing**: false
- **External dependencies**: BASE layer GCPR (DynamoDB) — `e_uk_mortgage_db.mrt_mortgage_payment` must complete before DAG triggers
- **Notes**: Transactional table — daily payment events loaded on business days only
