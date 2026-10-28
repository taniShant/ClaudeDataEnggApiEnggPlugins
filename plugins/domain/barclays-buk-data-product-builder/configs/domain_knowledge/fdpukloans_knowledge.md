# fdpukloans Domain Knowledge

**Domain**: Consumer Loans (Foundation Data Product)
**Tenancy**: `fdpukloans`
**Data Product Type**: FDP — sourced from E_ALS_DB and E_CUSTOMER_DB; target Iceberg tables in `fdp_uk_cnsmr_loan_db_iceberg`
**Last Updated**: 2026-06-16

---

## Business Context

- A **consumer loan account** represents a single loan account lifecycle from origination through to closure or write-off. One customer may hold multiple concurrent loan accounts.
- A **loan application** represents the loan approval/underwriting record. Applications are linked to accounts via fuzzy logic matching (not a strict foreign key) — the `app_id` is derived using business rules applied during transformation.
- **Arrears/Delinquency** are tracked at account level. An account in arrears has an associated delinquency flag, delinquency amount, and last delinquency update date.
- **Loan lifecycle** is fully tracked: applications flow through status progression (status code `13` indicates an approved/finalized application), and accounts maintain current and historical state via SCD2 versioning.
- "Active" in the consumer loans context means `active = 1` (non-transaction tables) or `dw_bus_dt = current_business_date` (transaction tables); use these directly rather than filtering on a derived "active" flag.

---

## Source System Filter Rules

### E_ALS_DB Source Filters
- **TEJVRT00** (root loan account): Filter on `rt_ctl_3 = '010'` (product type code for consumer loans)
- **TEJVEX01, TEJVZ401, TEJVZ101**: Filter on `substring(root_key, 6, 3) = '010'`
- **TEJVDQ01** (delinquency): Filter on `dq_tot_amt_pdue > 0` AND substring `'010'` — only accounts currently in arrears
- **TEJVTR00** (financial transactions): Transaction-level detail (Day 1+ only); keyed on `dw_bus_dt`

### E_CUSTOMER_DB Source Filters
- **TDLSPRO**: Status code `13` = finalized/approved application; used as priority in ranking windows for `app_id` derivation
- **TDKJCMT**: Joined only for status `13` records (working/month-end hands-on amounts)

---

## SCD2 Team-Specific Notes

No pipeline-specific CDC exclusion beyond standard audit columns (no `source_extract_timestamp` or `batch_id` encountered in current codebase).

---

## Source System Quirks & Date/Type Handling

### Date Format Issues

**No YYYYMMDD Integer Casting Required**
- All source date columns (`sle_pgs_sta_dte`, `sle_pgs_sts_dte`, `dq_lst_updt`, `rt_acct_eff_date`) are already in DATE format in source
- Use `to_date(col)` if conversion from string is needed, or `.cast("date")` for explicit casting
- Example from `cnsmr_loan_acct_transform.py`:
  ```python
  F.col("dq_lst_updt").cast("date").alias("dq_lst_updt_final")
  F.col("eff_start_date").cast("date").alias("eff_start_date")
  ```

### Type Casting for Amounts

**Decimal Precision Required**
- Amounts like `sle_pgs_amt`, `wrk_hds_on_rpy_amt`, `dq_tot_amt_pdue` must be cast to `DECIMAL(19,6)`:
  ```python
  when(col("wrk_hds_on_rpy_amt").isNotNull(), col("wrk_hds_on_rpy_amt")).otherwise(lit(None)).cast("decimal(19,6)")
  col("rt_orig_loan_amt").cast("decimal(19,6)") == col("sle_pgs_amt").cast("decimal(19,6)")
  ```

### NULL Patterns (Expected & Valid)
- `app_id` is NULL for accounts not matched to an application (fuzzy join may not find all matches) — this is valid
- `dq_tot_amt_pdue` is NULL when account is not in arrears (filter logic: `dq_tot_amt_pdue > 0`) — expected
- `cus_upd_tmp, wrk_hds_on_rpy_amt, hds_on_rpy_amt` are NULL for applications with status ≠ `13` — expected
- `eff_end_date` from source is NULL for currently active records — expected; SCD2 processing replaces with `3499-12-31`

---

## Fuzzy Logic: Application-to-Account Matching

### Account Identifier Derivation (`acct_id`)
Constructed from E_ALS_DB root key:
```python
concat(lit("10001011"), lit("|"), TEJVRT00.rt_acct_num).alias("acct_id")
```
Format: `"10001011|<rt_acct_num>"` — system prefix `10001011` + pipe + root account number

### Application Identifier Derivation (`app_id`)
Constructed from E_CUSTOMER_DB TDLSPRO record:
```python
concat(
    lit("10001001"),
    lit("|"),
    col("pmy_cus_idr"),
    lpad(col("sle_pgs_seq_num"), 3, "0"),  # Pad to 3 digits
    date_format(col("sle_pgs_sta_dte"), "yyyyMMdd"),
    col("gnc_pdt_cde")
)
```
Format: `"10001001|<pmy_cus_idr><sle_pgs_seq_num_padded><sle_pgs_sta_dte_yyyyMMdd><gnc_pdt_cde>"` — system prefix + customer ID + sequence (padded) + application start date + product code

### Fuzzy Join Logic (Account ↔ Application)
**Location**: `cnsmr_loan_acct_transform.py` lines 59-125

The join between accounts (TEJVRT00) and applications (TDLSPRO) uses **multi-stage fuzzy matching**:

**Stage 1: Account → Customer**
- Join TEJVRT00 to TDLMAHO on `rt_acct_num == trim(hlg_gnc_acc_num)` (LEFT JOIN)
- Extract customer ID (`cus_idr`) and product code (`gnc_pdt_cde_maho`)

**Stage 2: Application Match with Date Window**
- Join to TDLSPRO on:
  - `cus_idr == pmy_cus_idr` (same customer)
  - `gnc_pdt_cde_maho == gnc_pdt_cde` (same product)
  - `abs(datediff(rt_acct_eff_date, sle_pgs_sts_dte)) <= 31` (account opened within 31 days of application status date)
- Calculates `var_date_diff_days` — absolute day difference between account effective date and application status date

**Stage 3: Deduplication via Ranking Window**
```python
window_spec = Window.partitionBy(
    df_joined_1.acct_id_1, 
    df_joined_1.sle_pgs_seq_num
).orderBy(
    when(df_joined_1.sle_pgs_sts_cde == '13', 0).otherwise(1),  # Status 13 (approved) prioritized
    df_joined_1.var_date_diff_days,  # Closest date match
    df_joined_1.eff_end_date_spro.desc(),
    df_joined_1.eff_start_time_spro.desc(),
    df_joined_1.dw_upd_lod_tmp_spro.desc(),
    df_joined_1.psdm_seq_no_spro.desc(),
    when(col("rt_orig_loan_amt").cast("decimal(19,6)") == col("sle_pgs_amt").cast("decimal(19,6)"), 0).otherwise(1),  # Loan amount match
    when(df_joined_1.rt_orig_term == df_joined_1.sle_pgs_rpy_prd, 0).otherwise(1)  # Term match
)
```
Selects rank=1 (best match by: approved status → closest date → latest timestamp → matching amount/term)

**Stage 4: Final Deduplication (Account Level)**
Additional window function to ensure one application per account, with dense ranking across MAHO and SPRO records to resolve ties.

**Result**: `app_id` column in account table links to applications; some accounts may have NULL `app_id` if no fuzzy match found.

---

## Effective Date Management & SCD2 Versioning

### Boundary-Based Effective Dating (Day 0 Account Table)

**Problem**: Account state changes across multiple source tables (TEJVRT00, TEJVDQ01, TEJVEX01, TEJVZ401, TEJVZ101) on different dates; need to track when combined state changes occur.

**Solution** (Lines 203-250 in `cnsmr_loan_acct_transform.py`):

1. **Extract date boundaries** from all source tables:
   - For each source table, collect all `eff_start_date` and `eff_end_date` values
   - Union all boundaries into a single list of potential state-change points

2. **Deduplicate and sort**:
   ```python
   distinct_boundaries = all_boundaries.filter(col("date_point").isNotNull()).distinct()
   ```

3. **Create effective date ranges** via window function:
   ```python
   window_spec = Window.partitionBy(pkey).orderBy("date_point")
   date_ranges = distinct_boundaries.withColumn(
       "eff_end_date",
       lead("date_point").over(window_spec)
   ).withColumnRenamed("date_point", "eff_start_date")
   ```
   For each boundary, the next boundary becomes the `eff_end_date`; last boundary gets `3499-12-31`

4. **Filter valid ranges**:
   ```python
   valid_ranges = date_ranges.filter(
       col("eff_end_date").isNotNull() &
       (col("eff_start_date") < col("eff_end_date")) &
       (to_date(col("eff_end_date")) >= to_date(lit(curr_business_date), "yyyyMMdd"))
   )
   ```
   Keep only ranges with `eff_end_date >= current_business_date` (future-dated or current records only)

**Result**: Multiple versions of the same account spanning non-overlapping effective date ranges, each capturing the state at that time.

---

## Application Lifecycle & Status Codes

### Application Status Code `13` (Approved/Finalized)
- Status code `13` in `TDLSPRO.sle_pgs_sts_cde` indicates an approved, finalized application
- Used as a filter/priority in joins and transformations
- Only applications with status `13` are joined to `TDKJCMT` for hands-on amounts
- Prioritized in ranking windows (status `13` → rank 0, others → rank 1)

### Application-to-Account Conversion (Not Automatic)
- **Declined applications**: NOT converted to accounts; remain in `consumer_loan_application` table only
- **Withdrawn applications**: NOT converted to accounts; remain in `consumer_loan_application` table only
- **Approved applications** (status `13`): Matched to accounts via fuzzy logic; `app_id` appears in `consumer_loan_account` if match found

### Hands-On Amounts (Application Detail)
- `wrk_hds_on_rpy_amt` — Working hands-on amount
- `hds_on_rpy_amt` — Month-end hands-on amount
- Sourced from `TDKJCMT`, joined only for applications with status `13`
- Cast to `DECIMAL(19,6)`; NULL for applications with other statuses

---

## Reference Data & Source Decode Pattern

### Consumer Loan Reference Source Decode Table
**Table**: `consumer_loan_reference_source_decode`

**Purpose**: Central decode table for system source code mappings. Loaded once (snapshot pattern) and referenced in multiple downstream tables.

**Schema**:
- `reference_source_code` — Source system code
- `src_sys_key` — Source system key identifier (e.g., `10001011` for E_ALS_DB, `10001001` for E_CUSTOMER_DB)
- `reference_detail_key` — Foreign key to `consumer_loan_reference_detail`
- `reference_category_key` — Foreign key to `consumer_loan_reference_category`
- `reference_source_name` — Human-readable name
- `reference_source_description` — Description
- `dw_lod_tmp` — Load timestamp
- `dw_bus_dt` — Business date

**Usage Pattern**:
1. Financial transactions (`TEJVTR00`) include `amhstr01_tr_tran_cd` (transaction code)
2. Join to `consumer_loan_reference_source_decode` to decode the code and get category/detail keys
3. Then join to `consumer_loan_reference_category` and `consumer_loan_reference_detail` for detailed information

**Example Join**:
```python
transaction_df.join(
    source_decode_df,
    transaction_df.tran_cd == source_decode_df.reference_source_code,
    "left"
).select(
    ...,
    source_decode_df.reference_category_key,
    source_decode_df.reference_detail_key
)
```

---

## Load Patterns & Orchestration

### Load Type Classification

**NT (Non-Transaction/Dimensional)**
- Day 0: Full snapshot (all history)
- Day 1+: Incremental CDC with `full_snapshot` merge (compare to previous file hash, apply changes)
- Tables: Account, Application, Reference, Satellite tables

**T (Transaction/Fact)**
- Day 0: Full snapshot (all transactions)
- Day 1+: Append-only with `key_without_indicator` CDC (new transactions only)
- Tables: Financial Transaction, Non-Financial Transaction

**SDH (Snapshot Dimension Hierarchy)**
- Full overwrite each run
- Reference/static data

### Date Control Configuration

Each table has a `date_control` configuration in its JSON config file:

| Setting | Values | Purpose |
|---------|--------|---------|
| `frequency` | `working_days`, `daily`, `monthly` | Load scheduling |
| `workday_number_weekly` | `1`, `2`, etc. | Which weekday (1=Monday) |
| `workday_number_monthly` | `1`, `2`, etc. | Which working day of month |
| `run_on_weekends` | `Y` / `N` | Include weekends |
| `run_on_bank_holidays` | `Y` / `N` | Include bank holidays |

**Examples**:
- Account (main) — `frequency: working_days`, `workday_number_weekly: 1` — Mondays only
- Application — `frequency: daily`, `run_on_weekends: Y`, `run_on_bank_holidays: Y` — Every day
- Financial Transaction — `frequency: working_days` — Working days only

### CDC Types

**`full_snapshot`** (Non-Transaction tables)
- Compares entire DataFrame to previous file (via hash on non-audit columns)
- If any column changes, row is treated as updated
- Exclusion list ensures `eff_start_date`, `eff_end_date`, `dw_lod_tmp`, `dw_upd_lod_tmp`, `active` don't trigger updates
- Full data write with SCD2 merge

**`key_without_indicator`** (Transaction tables)
- Append-only pattern; no delete indicators
- New transactions are appended each day
- No comparison to previous file

---

## Transformation Style & Naming Conventions

### DataFrame Naming
- Use descriptive names reflecting the source/state: `TEJVRT00`, `df_joined`, `df_kjcmt`, `tdlspro_kjcmt_13`
- Intermediate steps may use suffixes for clarity:
  - `_13` — Filtered to status 13 records (e.g., `tdlspro_13`)
  - `_no_13` — Filtered to non-status-13 records (e.g., `tdlspro_no_13`)
  - `_union` — Result of union operation (e.g., `df_union`)

### SQL Alias Conventions in Spark SQL
- Use meaningful aliases in multi-table SQL:
  - `spro` for TDLSPRO
  - `kjcmt` for TDKJCMT
  - `final` for final result set
- Always qualify column references in multi-table joins

### Window Function Patterns
- **Deduplication**: `ROW_NUMBER()` with custom ORDER BY logic to pick best record
- **Ranking**: `RANK()` or `DENSE_RANK()` to score multiple records
- **Lead/Lag**: Used for date range generation (e.g., `lead("eff_start_date")` to compute next boundary)

### Filter Patterns
- **Test/Dummy Records**: Exclude on all source table reads:
  - Filter on `rt_ctl_3 == '010'` or `substring(root_key, 6, 3) == "010"` (product type code)
- **Status Filtering**: Split on `sle_pgs_sts_cde == '13'` for conditional downstream logic
- **Delinquency**: `dq_tot_amt_pdue > 0` to identify accounts in arrears only

---

## PII / Sensitive Columns

> **IMPORTANT**: This section is for documentation only and does NOT trigger crypto detection.
> Crypto is triggered ONLY by explicit `cloud_api_udf_<DE>_(un)protect(col)` UDF pattern in transformation code.

The following columns may contain sensitive data and should be reviewed against actual transformation logic in the config and code for tokenization/detokenization:

| Column | Sensitivity | Source Table | Notes |
|--------|------------|--------------|-------|
| `cus_idr` (Customer ID) | PII — Customer identifier | E_CUSTOMER_DB (TDLMAHO, TDLSPRO) | Typically tokenized in BASE; check if detokenization needed |
| `pmy_cus_idr` (Primary Customer ID) | PII — Customer identifier | E_CUSTOMER_DB (TDLSPRO) | Used in joins; same sensitivity as `cus_idr` |
| `hlg_gnc_acc_num` (Generic Account Number) | PII — Account identifier | E_CUSTOMER_DB (TDLMAHO) | Internal account reference |
| `aps_apl_ref_num` (Application Reference Number) | PII — Application/loan reference | E_CUSTOMER_DB (TDLSPRO, TDKJCMT) | Customer-facing or internal reference |

---

## Unity Catalog Names (Databricks)

- **Schema**: `fdp_uk_cnsmr_loan_db_iceberg`
- **DDA Catalog** (Iceberg target tables): **NOT CONFIRMED** — check with platform team before first deployment
- Likely pattern: `DEV_BUK_LOANS_FDP` (dev), `UAT_BUK_LOANS_FDP` (uat), `PRD_BUK_LOANS_FDP` (prod)
- Confirm actual names in deployment documentation or with the platform team

---

## Key Transformation Modules

### `read_src.py`
Orchestrates reading source tables with:
- Glue/Iceberg partitioning and filtering logic
- Day 0 vs Day 1 date filtering (Day 0: `>= curr_business_date`, Day 1: `== curr_business_date`)
- Transaction table filtering on `dw_bus_dt`
- DataFrame validation (exit with error if empty)

### `cnsmr_loan_acct_transform.py` (Day 0)
- Complex multi-table joins (TEJVRT00, TDLMAHO, TDLSPRO, TEJVEX01, TEJVZ401, TEJVZ101, TEJVDQ01)
- Fuzzy matching logic to link accounts to applications
- Boundary-based effective dating across multiple source tables
- Delinquency amount extraction and SCD2 versioning

### `cnsmr_loan_app_transform.py` (Day 0)
- Application-level transformations from TDLSPRO (sales/product subscription)
- Hands-on amount extraction from TDKJCMT (only for status 13 records)
- Application ID derivation with padded sequence number and formatted date
- Loan amount casting from TDLLAMT and TDLSPRO

### `load_target.py`
- Handles Iceberg writes with partition-level overwrite or full snapshot
- CDC merge logic (compares to previous file, applies delta or full load)
- Error handling and logging

### `date_control.py`
- Manages business date progression for day0/day1 runs
- Working day / bank holiday calculation
- Date control file I/O

### `cdc_load.py`
- Change Data Capture orchestration
- Manages previous file archival
- Tracks CDC state across runs

### `validation.py`
- Data quality checks (row counts, schema validation)
- Exit on validation failure

### `util_functions.py`
- Checkpoint utilities with data validation
- Working day calculation (RRULE DAILY, MO-FR patterns)
- File path helpers

---

## Sample Code Patterns

### Fuzzy Date Matching
```python
# Join condition with date window (within 31 days)
join_condition2 = (
    (df_joined1.cus_idr == TDLSPRO.pmy_cus_idr) & 
    (df_joined1.gnc_pdt_cde_maho == TDLSPRO.gnc_pdt_cde) & 
    (abs(datediff(to_date(col("rt_acct_eff_date")), to_date(col("sle_pgs_sts_dte")))) <= 31)
)
df_joined_2 = df_joined1.join(TDLSPRO, join_condition2, "left")
```

### Window-Based Deduplication with Multiple Sort Keys
```python
window_spec = Window.partitionBy(
    df_joined_1.acct_id_1, 
    df_joined_1.sle_pgs_seq_num
).orderBy(
    when(df_joined_1.sle_pgs_sts_cde == '13', 0).otherwise(1),  # Status 13 first
    df_joined_1.var_date_diff_days,  # Closest date
    df_joined_1.eff_end_date_spro.desc(),  # Latest timestamp
    df_joined_1.eff_start_time_spro.desc(),
    when(col("rt_orig_loan_amt").cast("decimal(19,6)") == col("sle_pgs_amt").cast("decimal(19,6)"), 0).otherwise(1),  # Amount match
    when(df_joined_1.rt_orig_term == df_joined_1.sle_pgs_rpy_prd, 0).otherwise(1)  # Term match
)
df_joined_1 = df_joined_1.withColumn("rnk", rank().over(window_spec)) \
                         .filter(col("rnk") == 1) \
                         .drop("rnk")
```

### Boundary-Based Effective Dating
```python
# Collect all date points from multiple source tables
all_boundaries = rt00_joined_df.union(dq01_df).union(EX01).union(VZ401).union(VZ101)

# Deduplicate boundaries
distinct_boundaries = all_boundaries.filter(col("date_point").isNotNull()).distinct()

# Create ranges using lead()
window_spec = Window.partitionBy(pkey).orderBy("date_point")
date_ranges = distinct_boundaries.withColumn(
    "eff_end_date",
    lead("date_point").over(window_spec)
).withColumnRenamed("date_point", "eff_start_date")

# Filter to valid ranges (end >= current date)
valid_ranges = date_ranges.filter(
    col("eff_end_date").isNotNull() &
    (col("eff_start_date") < col("eff_end_date")) &
    (to_date(col("eff_end_date")) >= to_date(lit(curr_business_date), "yyyyMMdd"))
)
```

### Conditional NULL Handling for Amounts
```python
# Set NULL for non-status-13 applications
df_tdlspro = df_tdlspro.withColumn("cus_upd_tmp", lit(None).cast(DateType())) \
                        .withColumn("wrk_hds_on_rpy_amt", lit(None).cast(DecimalType(19, 6))) \
                        .withColumn("hds_on_rpy_amt", lit(None).cast(DecimalType(19, 6)))

# Cast amounts with NULL-safe logic
when(col("wrk_hds_on_rpy_amt").isNotNull(), col("wrk_hds_on_rpy_amt")) \
    .otherwise(lit(None)) \
    .cast("decimal(19,6)")
```

### Application ID Derivation
```python
TDLSPRO = TDLSPRO.withColumn(
    "app_id",
    concat(
        lit("10001001"),  # System prefix
        lit("|"),
        col("pmy_cus_idr"),
        lpad(col("sle_pgs_seq_num"), 3, "0"),  # Pad sequence to 3 digits
        date_format(col("sle_pgs_sta_dte"), "yyyyMMdd"),  # Format date as YYYYMMDD
        col("gnc_pdt_cde")  # Product code
    )
)
```

---

## Related Documentation

- **Mortgage FDP**: `fdpmortgage_knowledge.md` — Similar SCD2 patterns and CDC configuration (reference for comparison)
- **Deployment**: Check platform team for Unity Catalog names and deployment environment details
- **Business Rules**: Fuzzy logic matching tolerances (31-day window, amount/term matching) may require updates if business rules change

---

## Special / Non-Standard Transformation Patterns

This section documents business-logic-specific transformation patterns unique to the consumer loans FDP. These are not typical ETL patterns and require careful understanding.

### 1. Temporal Overlap Join Pattern (Account-to-Satellite Join)

**Location**: `cnsmr_loan_acct_transform.py`, function `drop_rename_join()` (lines 640-658)

**Problem**: Account records can span multiple effective date ranges. When joining satellite data (TEJVDQ01, TEJVEX01, TEJVZ401, TEJVZ101), we need to match the account record with the satellite record that is valid during that account's effective date range (time-based overlap join).

**Standard approach**: Simple date-range join using `BETWEEN`

**Custom approach** (Temporal Overlap Join):
```python
def drop_rename_join(df_base, df_second, p_column_name, append_name):
    # Join condition: 
    # 1. Match on primary key (root_key)
    # 2. Base eff_start_date >= Second eff_start_date (base starts after or at second start)
    # 3. Base eff_start_date < Second eff_end_date (base starts before second ends)
    # Result: Finds which satellite record was active at the start of the base record
    
    result_df = df_base.alias("a").join(df_second.alias(append_name), (
        col("a."+p_column_name) == col(append_name+"."+p_column_name)) & (
            col("a.eff_start_date") >= col(append_name+".eff_start_date")) & (
                col("a.eff_start_date") < col(append_name+".eff_end_date")), 
        "LEFT"
    ).drop(col(append_name+"."+p_column_name)) \
     .drop(col(append_name+".eff_start_date")) \
     .drop(col(append_name+".eff_end_date"))
    return result_df
```

**Why This Approach?**
- Each account version has a valid period (`eff_start_date` to `eff_end_date`)
- Satellite records (extensions, delinquencies, descriptors) also have validity periods
- We want the satellite data that was active when the account version became effective
- Used for: joining TEJVDQ01 (delinquency), TEJVEX01 (extensions), TEJVZ401/TEJVZ101 (descriptors) to main account

**Data Flow**:
```
Account v1: [2020-01-15 to 2021-06-30]    + Satellite valid [2020-01-01 to 2022-12-31]  → MATCH
Account v2: [2021-07-01 to 3499-12-31]    + Satellite valid [2021-07-01 to 3499-12-31]  → MATCH
Satellite updates happen independently; temporal join tracks which version applies when
```

---

### 2. Boundary-Based SCD2 Versioning (Multi-Source State Changes)

**Location**: `cnsmr_loan_acct_transform.py`, lines 203-259 and functions `boundary_start_end()` (lines 659-666)

**Problem**: Account state is fragmented across multiple source tables, each maintaining its own effective dates. When TEJVRT00 changes on Day 1, TEJVDQ01 on Day 5, and TEJVEX01 on Day 12, we need to create new account versions at each point, even if the joined record hasn't technically changed.

**Standard approach**: Union date boundaries and generate date ranges.

**Custom approach** (Comprehensive Multi-Source Boundary Generation):

**Step 1: Extract Boundaries from All Sources**
```python
# Collect eff_start_date AND eff_end_date from each source as separate "boundary points"
def boundary_start_end(df, p_column_name):
    df_start = df.select(p_column_name, col("eff_start_date").alias("date_point"))
    df_end = df.select(p_column_name, col("eff_end_date").alias("date_point"))
    df_final = df_start.union(df_end)  # Both start AND end dates are boundaries
    return df_final

# Collect from all source tables
all_boundaries = rt00_joined_df.union(dq01_df).union(EX01).union(VZ401).union(VZ101)
distinct_boundaries = all_boundaries.filter(col("date_point").isNotNull()).distinct()
```

**Step 2: Generate Date Ranges Between Consecutive Boundaries**
```python
window_spec = Window.partitionBy(pkey).orderBy("date_point")
date_ranges = distinct_boundaries.withColumn(
    "eff_end_date",
    lead("date_point").over(window_spec)  # Next boundary becomes end date
).withColumnRenamed("date_point", "eff_start_date")

# Filter valid ranges (no gaps, no backwards dates, future-dated only)
valid_ranges = date_ranges.filter(
    col("eff_end_date").isNotNull() &
    (col("eff_start_date") < col("eff_end_date")) &
    (to_date(col("eff_end_date")) >= to_date(lit(curr_business_date), "yyyyMMdd"))
)
```

**Step 3: Join Account + Satellite Data to Each Date Range**
For each valid range, use temporal overlap join to get the satellite data active during that range:
```python
result_df = drop_rename_join(valid_ranges, joined_df, pkey, 't1')
result_df_1a = drop_rename_join(result_df, TEJVDQ01_transformed, pkey, 't1a')
result_df_1 = drop_rename_join(result_df_1a, TEJVEX01, pkey, 't2')
# ... repeat for all satellites
```

**Result**: Multiple versions of the same account, each valid during a specific date range where at least one source table is active.

**Example**:
```
Account 12345 versions:
- [2020-01-15 to 2021-06-30]: TEJVRT00 active, TEJVDQ01 inactive
- [2021-07-01 to 2021-12-15]: TEJVRT00 active, TEJVDQ01 active (entered arrears)
- [2021-12-16 to 2022-05-30]: TEJVRT00 active, TEJVDQ01 active, TEJVEX01 active (term extended)
- [2022-05-31 to 3499-12-31]: TEJVRT00 active, TEJVDQ01 inactive (exited arrears)
```

---

### 3. Consecutive Date Consolidation via Cumulative Sum (DDUP Process)

**Location**: `cnsmr_loan_acct_transform.py`, lines 318-332 (Account) and `cnsmr_loan_app_transform.py`, lines 207-235 (Application)

**Problem**: After multi-source boundary versioning, we may have many consecutive versions with identical business data but different effective dates (e.g., state unchanged from Day 10-15, then Day 20-30). These create unnecessary versioning bloat. We need to consolidate consecutive records with identical business values.

**Standard approach**: Simple `coalesce()` or `window function grouping`.

**Custom approach** (Gap-and-Island Consolidation):

**Step 1: Identify Gaps (When Previous Version Ends Before Current Starts)**
```python
key_columns = ["acct_id", "app_id", "prd_id", ...]  # All business columns
window_spec = Window.partitionBy(key_columns).orderBy("eff_start_date")

# Check if gap exists between records
final_df3 = final_df.withColumn("prev_end_date", lag("eff_end_date", 1).over(window_spec))
final_df3 = final_df3.withColumn(
    "is_new_group",
    when((col("prev_end_date").isNull()) |          # First record
         (col("eff_start_date") > col("prev_end_date")), 
         lit(1)
    ).otherwise(lit(0))  # Consecutive (no gap)
)
```

**Step 2: Create Group ID Using Cumulative Sum (Gap-and-Island Technique)**
```python
window_cumsum = Window.partitionBy(key_columns).orderBy("eff_start_date")
final_df3 = final_df3.withColumn(
    "group_id", 
    sum("is_new_group").over(window_cumsum)  # Cumsum increments at each gap
)
```

**Example Cumsum Logic**:
```
Record 1: is_new_group=1 (first)   → group_id=1
Record 2: is_new_group=0 (consecutive) → group_id=1
Record 3: is_new_group=0 (consecutive) → group_id=1
Record 4: is_new_group=1 (gap!)    → group_id=2
Record 5: is_new_group=0 (consecutive) → group_id=2
```

**Step 3: Consolidate by Group**
```python
final_df3 = final_df3.groupBy(key_columns + ["group_id"]).agg(
    min_("eff_start_date").alias("eff_start_date"),
    max_("eff_end_date").alias("eff_end_date")
)
final_df3 = final_df3.drop("group_id")
```

**Result**: Consecutive records with identical business data are consolidated into single records with merged date ranges.

---

### 4. Day 1 Incremental Logic: Delinquency Carryforward

**Location**: `cnsmr_loan_acct_transform.py`, lines 527-559 (Day 1 only)

**Problem**: On Day 1, account data comes from fresh daily source extracts. Delinquency flags (`tot_dlq_amt`, `last_dlq_dt`) are only populated if the account is currently in arrears. If an account exits arrears on Day 2, the delinquency amount in the source will be 0 or NULL. But the historical delinquency should be preserved (for audit trail, history, etc.), even though the account is no longer in arrears.

**Custom Logic** (Split-Path Carryforward):

**Part 1: New Accounts (Not in Previous Run)**
```python
# Accounts not in previous day's active data
rt00_dlq_join_CNSMR_LOAN_ACCT_Previous_1 = rt00_dlq_join.filter(col("previous_acct_id").isNull())

joined_df1 = rt00_dlq_join_CNSMR_LOAN_ACCT_Previous_1.withColumn(
    "tot_dlq_amt",
    F.when(F.col("dq_tot_amt_pdue") == 0, F.lit(None))  # No arrears → NULL
     .otherwise(F.col("dq_tot_amt_pdue"))
).withColumn(
    "last_dlq_dt",
    F.when(F.col("dq_tot_amt_pdue") == 0, F.lit(None).cast(DateType()))  # No arrears → NULL
     .otherwise(F.col("dq_lst_updt"))
).withColumn(
    "app_id_final",
    F.when(F.col("app_id").isNull(), F.col("previous_app_id"))  # Use new value or fallback
     .otherwise(F.col("app_id"))
)
```

**Part 2: Existing Accounts (Were in Previous Run)**
```python
# Accounts in previous day's active data
rt00_dlq_join_CNSMR_LOAN_ACCT_Previous_2 = rt00_dlq_join.filter(col("previous_acct_id").isNotNull())

joined_df2 = rt00_dlq_join_CNSMR_LOAN_ACCT_Previous_2.withColumn(
    "tot_dlq_amt",
    F.when(F.col("dq_tot_amt_pdue") > 0, F.col("dq_tot_amt_pdue"))  # If NEWLY in arrears
     .otherwise(F.col("previous_tot_dlq_amt"))  # CARRY FORWARD previous day's amount
).withColumn(
    "last_dlq_dt",
    F.when(F.col("dq_tot_amt_pdue") > 0, F.col("dq_lst_updt").cast(DateType()))  # Update if newly in arrears
     .otherwise(F.col("previous_last_dlq_dt"))  # CARRY FORWARD previous day's date
).withColumn(
    "app_id_final",
    F.when(F.col("app_id").isNull(), F.col("previous_app_id"))  # Fallback to previous
     .otherwise(F.col("app_id"))
)

# Union both paths
Union_df = joined_df1.union(joined_df2)
```

**Why This Complexity?**
- Business requirement: Once an account is flagged in arrears, that flag/amount must be historically preserved even if the account later exits arrears
- If we just set NULL, we lose the arrears history
- By carryforwarding from previous day, we maintain audit trail
- Only update (`dq_tot_amt_pdue > 0`) triggers a new/updated delinquency date

---

### 5. Application-Level Loan Purpose Derivation (Conditional Lead with Priority)

**Location**: `cnsmr_loan_app_transform.py`, lines 152-200

**Problem**: Loan purpose is stored in TDLLAMT with multiple records per application (product code changes, multiple amendments). Different amendments may have different loan purposes. We need to pick the "most relevant" one, with special handling for purpose code `16`.

**Custom Logic** (Lead-Based Purpose Selection):

**Step 1: Create Effective Date Ranges Using Lead()**
```python
# Within TDLLAMT, if loan purpose changes, create versions
# Purpose 16 is special (gets priority)
# Use LEAD to create the "until" date (when purpose changes)

tdllamt_df = spark.sql("""
SELECT 
    pmy_cus_idr,
    sle_pgs_seq_num,
    prs_lon_amt,
    loan_purp_cd,
    eff_start_date,
    CAST(COALESCE(rev_eff_end_date, eff_end_date) AS DATE) as eff_end_date
FROM (
    SELECT 
        pmy_cus_idr, 
        sle_pgs_seq_num, 
        COALESCE(TRIM(prs_lon_cde), '15') as loan_purp_cd,  -- Default to '15' if NULL
        prs_lon_amt, 
        CAST(eff_start_date AS DATE) as eff_start_date, 
        eff_end_date,
        LEAD(eff_start_date) OVER (
            PARTITION BY pmy_cus_idr, sle_pgs_seq_num
            ORDER BY case when prs_lon_cde='16' then 0 else 1 end,  -- Purpose '16' first
                     eff_start_date, 
                     eff_end_date, 
                     prs_lon_cde desc
        ) as rev_eff_end_date
    FROM tdllamt_view
)
""")
```

**Logic Breakdown**:
- `COALESCE(TRIM(prs_lon_cde), '15')` — Default loan purpose to `15` if missing
- `ORDER BY case when prs_lon_cde='16' then 0 else 1 end` — Purpose code `16` sorts first (priority)
- `LEAD(eff_start_date)` — Next record's start date becomes current record's end date
- `COALESCE(rev_eff_end_date, eff_end_date)` — Use calculated end date, or original if NULL (last record)

**Step 2: Select Latest Valid Purpose for Each Application**
```python
window_spec_ap = Window.partitionBy("app_id", "eff_start_date").orderBy(
    when(col("loan_purp_cd") == "16", 1).otherwise(0).asc(),  # Purpose '16' last (lower priority at this stage)
    joined_df.llamt_eff_end_date.desc(),  # Most recent end date
    joined_df.llamt_eff_start_date.desc()  # Most recent start date
)

joined_df = (joined_df
    .withColumn("rn", row_number().over(window_spec_ap))
    .filter(col("rn") == 1)  # Keep top 1 per app+eff_start_date
    .drop("rn", "pmy_cus_idr", "llamt_eff_end_date", "llamt_eff_start_date")
)
```

**Result**: Each application has one loan purpose, with purpose code `16` filtered earlier if multiple versions exist, defaulting to `15` if all missing.

---

### 6. Broadcast Join Strategy for Reference Decode (Multiple Category Lookups)

**Location**: `cnsmr_loan_acct_transform.py`, lines 263-296 (Day 0) and 571-604 (Day 1)

**Pattern** (Filter-Broadcast-Join Multiplexing):

**Why Broadcast?**
- Reference decode table is small (~1000 rows)
- We perform FOUR separate lookups on the same decode table
- Broadcasting eliminates repeated large-table scans

**Implementation**:
```python
# Filter decode table ONCE for each reference category
ref_decode_110001 = CNSMR_LOAN_REF_SRC_DECODE \
    .filter((col("ref_cat_key") == '110001') & (col("src_sys_key") == 10001011)) \
    .select(col("ref_src_cd").alias("ref_src_cd_1"), col("ref_dtl_key").alias("ref_dtl_key_1"))

ref_decode_160001_cat = CNSMR_LOAN_REF_SRC_DECODE \
    .filter((col("ref_cat_key") == '160001') & (col("src_sys_key") == 10001011)) \
    .select(col("ref_src_cd").alias("ref_src_cd_2"), col("ref_dtl_key").alias("ref_dtl_key_2"))

# ... (repeat for other categories)

# BROADCAST each small filtered dataset
ref_decode_110001 = broadcast(ref_decode_110001)
ref_decode_160001_cat = broadcast(ref_decode_160001_cat)
# ...

# Chain joins (each looks up a different business dimension)
final_df_3 = final_df \
    .join(ref_decode_110001,     col("ex_reas_lst_ext_cd") == col("ref_src_cd_1"), "left") \
    .join(ref_decode_160001_cat, col("loan_cat_cd") == col("ref_src_cd_2"), "left") \
    .join(ref_decode_160001_enfrc, col("ZM_DESC_15_4") == col("ref_src_cd_3"), "left") \
    .join(ref_decode_300001,     col("RT_PROC_TYPE") == col("ref_src_cd_4"), "left")
```

**Categories Decoded**:
- `110001` — Extension reason lookup
- `160001` — Loan category & agreement enforcibility
- `300001` — Account sub-type code

**Result**: Four dimension keys injected in a single multi-join pass, with each reference category as a small broadcast table.

---

### 7. Balloon Loan Indicator Transformation (Character to Binary)

**Location**: `cnsmr_loan_acct_transform.py`, lines 181-183 (Day 0) and 514-516 (Day 1)

**Pattern** (Character Code Translation):

**Source Logic**:
```python
joined_df = joined_df.withColumn(
    "balloon_loan_ind", 
    F.when(F.col("rt_sngl_balloon_cd") == "B", "1")   # Balloon loan → "1"
     .when(F.col("rt_sngl_balloon_cd") == "S", "0")   # Standard loan → "0"
     .otherwise(None)                                  # Unknown → NULL
)
```

**Why This Pattern?**
- Source stores as character codes: `B` (Balloon), `S` (Single/Standard)
- Target expects binary indicator: `1` (yes balloon), `0` (no balloon), NULL (unknown)
- Multiple derivations of this type exist across transformations

---

## Quick Reference: Common Queries

### Find Accounts in Arrears
```sql
SELECT acct_id, tot_dlq_amt, last_dlq_dt
FROM consumer_loan_account
WHERE active = 1 AND eff_end_date = CAST('3499-12-31' AS DATE)
  AND tot_dlq_amt > 0
```

### Find Applications Approved but Not Yet Converted to Accounts
```sql
SELECT app_id, application_status_code, application_loan_amount
FROM consumer_loan_application
WHERE application_status_code = '13'
  AND active = 1
  AND eff_end_date = CAST('3499-12-31' AS DATE)
  AND app_id NOT IN (SELECT app_id FROM consumer_loan_account WHERE app_id IS NOT NULL)
```

### Historical Account State by Effective Date
```sql
SELECT acct_id, original_loan_amount, current_maturity_date, eff_start_date, eff_end_date
FROM consumer_loan_account
WHERE acct_id = '<account_id>'
ORDER BY eff_start_date DESC
```

### Transaction Volume by Day
```sql
SELECT dw_bus_dt, COUNT(*) AS tran_count, SUM(transaction_amount) AS total_amount
FROM consumer_loan_financial_transaction
GROUP BY dw_bus_dt
ORDER BY dw_bus_dt DESC
```

---

## Day 0 vs Day 1 Transformation Differences

The account and application transformations have **significantly different logic** for Day 0 vs Day 1. Understanding these differences is critical for troubleshooting and maintenance.

### Account Table (fdp_uk_cnsmr_loan_db_iceberg.consumer_loan_account)

| Aspect | Day 0 | Day 1 |
|--------|-------|-------|
| **Data Source** | Full historical TEJVRT00, TEJVDQ01, TEJVEX01, TEJVZ401, TEJVZ101 | Incremental daily from same tables |
| **Boundary Logic** | Extracts ALL boundaries from all source tables; creates SCD2 versions for each state change in history | Uses only today's source data; joins directly to previous day's state from parquet file |
| **Delinquency Handling** | Boundary-based with multiple versions per account | NEW LOGIC: Split-path carryforward (see section 4 above) — preserves historical arrears even if account exits arrears |
| **Repartitioning** | `repartition(20)` then `coalesce(8)` | Direct `coalesce(8)` (no repartition) |
| **Previous Day Lookup** | N/A (full load) | Reads previous day's active records from s3://bucket/cdc/consumer_loan_account/previous_file to carryforward delinquency |
| **Output Pattern** | Stores active records (active=1) to CDC previous_file for Day 1 to reference | Directly transforms and outputs |
| **Temporal Window Joins** | ALL source tables undergo boundary-based temporal overlap joins | Simpler direct joins on root_key to TEJVDQ01; TEJVEX01/TEJVZ401/TEJVZ101 via renamed columns |

### Application Table (fdp_uk_cnsmr_loan_db_iceberg.consumer_loan_application)

| Aspect | Day 0 | Day 1 |
|--------|-------|-------|
| **Hands-On Amounts** | SQL CTE with complex join (status 13 + date filtering + ranking) | Same SQL logic repeated |
| **Loan Purpose** | Complex LEAD-based window function (priority 16, default 15) | Same logic |
| **Deduplication** | Gap-and-island consolidation (DDUP process) | Same DDUP process |
| **Previous Day Lookup** | N/A | N/A (no carryforward logic like accounts) |
| **Repartitioning** | None shown (commented out) | None shown (commented out) |
| **Output to S3** | Coalesce(8) write to stg_write_path | Coalesce(8) write to stg_write_path |

### Key Callouts: Day 0 → Day 1 Handoff

**What Day 0 Creates for Day 1**:
1. Writes active account records to: `s3://bucket/cdc/consumer_loan_account/previous_file` (parquet)
2. This file is read by Day 1 to join and carryforward delinquency state

**What Day 1 Must Do**:
1. Read today's fresh source data
2. Join to previous day's snapshot (left join on acct_id)
3. Split: new accounts vs. existing accounts
   - **New**: Use today's delinquency amount as-is (may be NULL if not in arrears)
   - **Existing**: Carryforward previous day's delinquency UNLESS today's amount > 0 (entered/stayed in arrears)
4. Apply same fuzzy app matching as Day 0
5. Deduplicate via gap-and-island

**Why This Design?**
- **Day 0**: Historical rebuild; boundaries ensure we capture all state changes ever
- **Day 1**: Incremental; only processes today's changes; relies on previous state to maintain audit trail

---

## Repartitioning & Coalesce Strategy

### Account Table Partitioning (Day 0)
```python
final_df3 = final_df3.repartition(20)   # Spread across 20 partitions for transformation work
final_df3 = final_df3.coalesce(8)       # Consolidate to 8 partitions for output
```

**Rationale**:
- Repartition(20) spreads work during complex multi-join transformations
- Coalesce(8) reduces I/O overhead on write (8 output files instead of 20)

### Day 1 Explicit Repartitioning on Join Keys
```python
# Day 1 only (lines 353-354)
TDLMAHO = source_data_frame["TDLMAHO"].repartition(240, "cus_idr")
TDLSPRO = source_data_frame["TDLSPRO"].repartition(240, "pmy_cus_idr")
```

**Rationale**:
- Pre-repartition join tables on their join keys (customer ID)
- 240 partitions co-locates related records for the fuzzy join
- Reduces shuffle during the complex multi-criteria join

---

## Handling of NULL / Missing Values

### Reference Key Defaults
When reference lookups fail (no matching category/code found), reference keys default to **-99**:
```python
when(col("ref_dtl_key_1").isNotNull(), col("ref_dtl_key_1")) \
    .otherwise(lit(-99)) \
    .cast("bigint")
```

**Why -99?**
- Distinguishes "unknown/unmapped" from "no category applies" (NULL)
- Allows downstream queries to filter: `WHERE ref_dtl_key > 0` to find mapped records
- Consistent across all four reference lookups

### Delinquency Amounts
- NULL when account is **not in arrears** (`dq_tot_amt_pdue = 0`)
- On Day 1, carried forward from previous day if account was in arrears

### Application IDs
- NULL if fuzzy matching fails (no matching application found for account)
- Fallback logic: On Day 1, use previous day's app_id if today's lookup fails (`app_id_final`)

---

## Debugging Common Issues

### Issue: Accounts Have Multiple Rows with Same Date Range
**Cause**: Gap-and-island consolidation didn't fully merge. Usually means `dropDuplicates()` call isn't removing logical duplicates.

**Check**:
1. Verify all key_columns in DDUP groupBy match the actual changes
2. Ensure consecutive date ranges really have no gaps (`eff_end_date` of row N = `eff_start_date` of row N+1)
3. Run `final_df3.show()` to inspect window spec ordering

### Issue: Delinquency Amount Changed but Account Otherwise Identical
**Cause**: This is expected on Day 1 if delinquency status changed. Account may or may not create a new version depending on other changes.

**Carryforward Logic**:
- If `tot_dlq_amt` changes from previous day, a new version IS created (different key_columns)
- Check: `SELECT * FROM consumer_loan_account WHERE acct_id='X' ORDER BY eff_start_date DESC`

### Issue: Application Loan Purpose Is '15' for All Records
**Cause**: Either all source TDLLAMT records have NULL `prs_lon_cde`, or no valid rank-1 records found.

**Check**:
1. Verify TDLLAMT has non-NULL `prs_lon_cde` values for relevant apps
2. Inspect window spec order: purpose '16' should sort first (`when()` returns 0)
3. Check LEAD query: does it correctly set end dates?

### Issue: Application Hands-On Amounts Are NULL for Status 13
**Cause**: TDKJCMT join failed (no matching record found), or `aps_apl_ref_num` is NULL in source.

**Check**:
1. Verify TDKJCMT has records matching status 13 apps by `aps_apl_ref_num` + `cus_idr`
2. Check date filter in SQL: `TO_DATE(spro.sle_pgs_sts_dte_1) >= TO_DATE(kjcmt.cus_upd_tmp)`
3. If multiple TDKJCMT records per app, ranking should pick latest (`cus_upd_tmp DESC`)

---

## Scheduling and Orchestration Hints

### Entity tables (consumer_loan_account, consumer_loan_application, consumer_loan_account_balance, etc.)
- **Schedule type**: business_calendar
- **Bank holiday skip**: true
- **Sequential processing**: false
- **External dependencies**: BASE layer GCPR (DynamoDB) — source tables from `e_uk_loans_db` must complete before DAG triggers
- **Notes**: Runs on UK banking business days; T-1 business date offset

### Transactional tables (consumer_loan_financial_transaction, consumer_loan_non_financial_transaction)
- **Schedule type**: business_calendar
- **Bank holiday skip**: true
- **Sequential processing**: false
- **External dependencies**: BASE layer GCPR (DynamoDB)
- **Notes**: Append-only event tables loaded on business days only

### Reference tables (consumer_loan_reference_category, consumer_loan_reference_detail, etc.)
- **Schedule type**: [UNKNOWN — likely `cron` with weekly or monthly cadence; resolve at /gen-dag time]
- **Bank holiday skip**: false
- **Sequential processing**: false
- **External dependencies**: [UNKNOWN — reference data typically has no upstream pipeline dependency]
