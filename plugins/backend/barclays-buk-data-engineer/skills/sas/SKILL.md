---
name: sas
description: SAS knowledge for migration and comprehension, covering DATA step, PROC SQL, macros, date handling, and SAS-to-modern-platform translation patterns
user-invocable: false
owner: BUK Data Engineering Practice
effective_date: 2026-07-13
review_cadence: quarterly
status: approved
---

# SAS Engineering Skill (Migration and Comprehension)

> **Important notice**: This skill is for comprehension and migration assistance only. It must NOT be used to generate new SAS code. All new data engineering work must be delivered on approved modern platforms using approved languages (Python, PySpark, SQL).

---

## DATA Step

The DATA step is the core SAS data processing construct. It reads observations from input datasets and writes observations to output datasets row by row.

```sas
/* Basic DATA step: read from WORK.source, filter, and write to WORK.target */
DATA WORK.target;
    SET WORK.source;
    WHERE status = 'ACTIVE';
    amount_gbp = amount / exchange_rate;
    FORMAT amount_gbp POUND12.2;
RUN;
```

### SET Statement
`SET` reads observations from one or more existing SAS datasets sequentially. Multiple datasets are concatenated vertically.

```sas
DATA WORK.combined;
    SET lib1.dataset_a lib2.dataset_b;  /* vertical concatenation */
RUN;
```

### MERGE Statement
`MERGE` performs a sorted join (similar to SQL JOIN). Input datasets must be sorted by the BY variable(s).

```sas
PROC SORT DATA=WORK.customers; BY customer_id; RUN;
PROC SORT DATA=WORK.accounts;  BY customer_id; RUN;

DATA WORK.customer_accounts;
    MERGE WORK.customers (IN=in_cust)
          WORK.accounts  (IN=in_acct);
    BY customer_id;
    IF in_cust AND in_acct;  /* equivalent to INNER JOIN */
RUN;
```

| IN flag condition | Equivalent SQL join |
|---|---|
| `IF in_a AND in_b` | INNER JOIN |
| `IF in_a` | LEFT JOIN |
| `IF in_b` | RIGHT JOIN |
| `IF in_a OR in_b` | FULL OUTER JOIN |

### BY Statement
`BY` specifies the sort key for MERGE, SORT, and grouped processing within a DATA step. Sets automatic first/last flag variables (`FIRST.varname`, `LAST.varname`).

```sas
DATA WORK.summary;
    SET WORK.transactions;
    BY account_id;
    IF FIRST.account_id THEN running_total = 0;
    running_total + amount;  /* sum statement: accumulates across BY group */
    IF LAST.account_id THEN OUTPUT;
RUN;
```

### OUTPUT Statement
Explicitly write the current observation to an output dataset. Without `OUTPUT`, SAS writes the observation automatically at the end of each iteration.

```sas
DATA WORK.pivoted;
    SET WORK.long_data;
    BY account_id;
    RETAIN q1_amount q2_amount q3_amount q4_amount 0;
    IF quarter = 'Q1' THEN q1_amount = amount;
    IF quarter = 'Q2' THEN q2_amount = amount;
    IF quarter = 'Q3' THEN q3_amount = amount;
    IF quarter = 'Q4' THEN q4_amount = amount;
    IF LAST.account_id THEN OUTPUT;
RUN;
```

### RETAIN Statement
`RETAIN` preserves variable values across iterations of the DATA step (unlike most variables which are reset to missing at each iteration).

```sas
DATA WORK.cumulative;
    SET WORK.daily_sales;
    RETAIN cumulative_total 0;
    cumulative_total + daily_amount;  /* sum statement implicitly retains */
RUN;
```

### Arrays
SAS arrays provide a shorthand to reference a list of variables in a loop.

```sas
DATA WORK.normalised;
    SET WORK.raw_scores;
    ARRAY scores{5} score_1 score_2 score_3 score_4 score_5;
    DO i = 1 TO 5;
        IF scores{i} = . THEN scores{i} = 0;  /* replace missing with 0 */
    END;
    DROP i;
RUN;
```

### DO Loops
```sas
/* Iterative DO loop */
DO i = 1 TO 12;
    month = i;
    OUTPUT;
END;

/* DO WHILE */
DO WHILE (balance > 0);
    balance = balance - payment;
    period + 1;
    OUTPUT;
END;

/* DO UNTIL */
DO UNTIL (converged);
    /* iterate until condition is true at end of loop */
END;
```

### Formats and Informats
- **Format**: controls how SAS displays or writes a value.
- **Informat**: controls how SAS reads a value from raw data.

```sas
/* Numeric formats */
amount_display = PUT(amount, DOLLAR12.2);  /* convert number to formatted string */

/* Date formats */
FORMAT transaction_date DATE9.;     /* display as 13JUL2026 */
FORMAT event_ts DATETIME20.;        /* display as 13JUL2026:10:15:00 */

/* Reading dates with INFORMAT */
INPUT transaction_date DDMMYY10.;   /* read "13/07/2026" as a SAS date */
```

---

## PROC SQL

PROC SQL implements a subset of ANSI SQL within SAS. It can query SAS datasets and create new datasets.

```sas
PROC SQL;
    CREATE TABLE WORK.summary AS
    SELECT
        account_id,
        COUNT(*) AS transaction_count,
        SUM(amount) AS total_amount,
        MAX(transaction_date) AS last_transaction_date
    FROM lib1.transactions
    WHERE status = 'COMPLETED'
    GROUP BY account_id
    HAVING COUNT(*) > 5
    ORDER BY total_amount DESC;
QUIT;
```

### PROC SQL Joins
```sas
PROC SQL;
    SELECT c.customer_id, c.name, a.account_id, a.balance
    FROM lib1.customers c
    INNER JOIN lib1.accounts a ON c.customer_id = a.customer_id
    WHERE a.status = 'ACTIVE';
QUIT;
```

### PROC SQL Macros Integration
```sas
%LET min_balance = 1000;

PROC SQL;
    SELECT * FROM lib1.accounts
    WHERE balance >= &min_balance;
QUIT;
```

---

## PROC SORT

```sas
PROC SORT DATA=lib1.transactions OUT=WORK.sorted_transactions NODUPKEY;
    BY account_id transaction_date;
    /* NODUPKEY: removes rows with duplicate BY variable values */
RUN;
```

`NODUPKEY` retains the first observation for each unique BY-variable combination. `NODUPRECS` removes complete duplicate rows.

---

## SAS Macro Language

The macro language enables code generation and parameterisation. Macro variables are substituted as text before SAS compiles and executes statements.

### %LET — Macro Variable Assignment
```sas
%LET run_date = 2026-07-13;
%LET schema = WORK;
%PUT NOTE: Running for date: &run_date;
```

### %MACRO / %MEND — Macro Definition
```sas
%MACRO process_transactions(in_lib=, out_lib=, start_date=, end_date=);
    DATA &out_lib..processed_transactions;
        SET &in_lib..transactions;
        WHERE transaction_date BETWEEN "&start_date."D AND "&end_date."D;
        processed_flag = 1;
    RUN;
    %PUT NOTE: Processed transactions from &start_date to &end_date;
%MEND process_transactions;

/* Call the macro */
%process_transactions(
    in_lib=lib1,
    out_lib=WORK,
    start_date=01JAN2026,
    end_date=31JAN2026
)
```

### %DO — Iterative Macro Loop
```sas
%MACRO loop_months(start_year=, end_year=);
    %DO year = &start_year %TO &end_year;
        %DO month = 1 %TO 12;
            %process_month(year=&year, month=&month)
        %END;
    %END;
%MEND loop_months;
```

### %INCLUDE
Includes and executes an external SAS file:
```sas
%INCLUDE '/path/to/common_macros.sas';
```

### Macro Variable Resolution
- `&var` resolves a macro variable value.
- `&&var` double ampersand: resolves a macro variable whose name is itself stored in another macro variable (indirect reference).
- `%SYSFUNC(funcname(args))` calls SAS functions within macro code.

```sas
%LET suffix = date;
%LET my_date = 2026-07-13;
%LET result = &&my_&suffix;  /* resolves to &my_date = 2026-07-13 */
```

---

## SAS Datasets (.sas7bdat)

SAS datasets are binary files with the `.sas7bdat` extension. They store:
- Data values in rows (observations) and columns (variables).
- Variable metadata: names, types (numeric or character), formats, informats, labels.
- Dataset-level attributes: creation date, encoding, compression flag.

Variable types:
- **Numeric**: 8-byte floating point by default. Stores dates as integers, datetimes as seconds since the SAS epoch.
- **Character**: fixed-width string up to 32,767 bytes.

There is no native integer type in SAS; all numbers are floating point.

---

## LIBNAME — Libraries

A SAS library is a logical name (libref) pointing to a directory or database connection.

```sas
/* Assign a library to a directory */
LIBNAME mylib '/data/sas/datasets/';

/* Database library via ODBC */
LIBNAME oracle ODBC DSN=oradb SCHEMA=finance;

/* Read a table via the library */
DATA WORK.copy;
    SET mylib.transactions;
RUN;

/* Deassign library */
LIBNAME mylib CLEAR;
```

The special `WORK` library is a temporary session-scoped library. All datasets in `WORK` are deleted when the SAS session ends.

---

## ODS (Output Delivery System)

ODS controls the format of SAS procedure output.

```sas
/* Write output to a CSV file */
ODS CSV FILE='/output/report.csv';
PROC PRINT DATA=WORK.summary NOOBS; RUN;
ODS CSV CLOSE;

/* Write output to HTML */
ODS HTML FILE='/output/report.html';
PROC REPORT DATA=WORK.summary; RUN;
ODS HTML CLOSE;
```

---

## Common Statistical PROCs

| PROC | Purpose | SQL/PySpark equivalent |
|---|---|---|
| PROC MEANS | Descriptive statistics (mean, std, min, max, N) | `df.describe()` / `SELECT AVG, STDDEV, MIN, MAX, COUNT` |
| PROC FREQ | Frequency and cross-tabulation | `GROUP BY col, COUNT(*)` |
| PROC SUMMARY | Flexible aggregation; output to dataset | `df.groupBy().agg()` |
| PROC TABULATE | Multi-dimensional summary table | Pivot / cross-tab queries |
| PROC REG | Linear regression | `sklearn.linear_model.LinearRegression` |
| PROC LOGISTIC | Logistic regression | `sklearn.linear_model.LogisticRegression` |

---

## SAS Date Handling

SAS stores dates as the number of days since 1 January 1960 (the SAS epoch). SAS datetimes are seconds since 1 January 1960. This differs from Unix epoch (1 January 1970) and Excel epoch (1 January 1900 or 1 January 1904).

```sas
/* SAS date literal */
ref_date = '13JUL2026'D;   /* SAS date value */
ref_dt   = '13JUL2026:10:15:00'DT;  /* SAS datetime value */

/* Convert SAS date to calendar components */
year  = YEAR(ref_date);
month = MONTH(ref_date);
day   = DAY(ref_date);

/* Format for display */
FORMAT ref_date DATE9.;    /* 13JUL2026 */
FORMAT ref_date YYMMDD10.; /* 2026-07-13 */
```

### Epoch Conversion Reference
| Platform | Epoch | Unit |
|---|---|---|
| SAS | 1 Jan 1960 | Days (date) / Seconds (datetime) |
| Unix / Python | 1 Jan 1970 | Seconds |
| Excel (Windows) | 31 Dec 1899 | Days |

### Converting SAS Dates to SQL/Python
SAS date value = days since 1960-01-01. To convert to a standard date:
```python
import datetime
SAS_EPOCH = datetime.date(1960, 1, 1)
def sas_date_to_python(sas_val):
    return SAS_EPOCH + datetime.timedelta(days=int(sas_val))
```

---

## Encoding Issues

SAS datasets may be encoded in non-UTF-8 encodings (e.g. WLATIN1 on Windows, LATIN1 on Unix). When converting SAS datasets, always identify the source encoding and transcode to UTF-8.

```sas
/* Check dataset encoding */
PROC CONTENTS DATA=lib1.transactions; RUN;
/* Look for "Encoding: wlatin1 Western (Windows)" in output */
```

During migration, use SAS `PROC COPY` with `NOCLONE` and explicit encoding options, or export via CSV with known encoding, then re-import with explicit encoding declaration in the target tool.

---

## SAS-to-SQL Translation Patterns

| SAS Pattern | SQL Equivalent |
|---|---|
| `DATA step SET + WHERE` | `SELECT ... FROM ... WHERE ...` |
| `MERGE ... BY ... IF in_a AND in_b` | `INNER JOIN ... ON ...` |
| `MERGE ... BY ... IF in_a` | `LEFT JOIN ... ON ...` |
| `RETAIN + sum statement` | `SUM() OVER (PARTITION BY ... ORDER BY ...)` |
| `FIRST.var / LAST.var` | `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)` |
| `PROC SORT NODUPKEY` | `SELECT DISTINCT` or `ROW_NUMBER()` deduplication |
| `PROC MEANS` | `SELECT AVG(), STDDEV(), MIN(), MAX(), COUNT()` |
| `PROC FREQ` | `SELECT col, COUNT(*) ... GROUP BY col` |
| `IF-THEN-ELSE` | `CASE WHEN ... THEN ... ELSE ... END` |
| `SUBSTR(var, 1, 3)` | `SUBSTRING(var, 1, 3)` |
| `LENGTH(var)` | `LENGTH(var)` / `LEN(var)` (T-SQL) |
| `COMPRESS(var, ' ')` | `REPLACE(var, ' ', '')` |
| `INPUT(charvar, 8.)` | `CAST(charvar AS INTEGER)` |
| `PUT(numvar, Z8.)` | `LPAD(CAST(numvar AS VARCHAR), 8, '0')` |

---

## SAS-to-PySpark Translation Patterns

| SAS Pattern | PySpark Equivalent |
|---|---|
| `DATA step: row-by-row processing` | DataFrame transformations (vectorised) |
| `SET` (concatenation) | `df1.union(df2)` |
| `MERGE BY` (join) | `df1.join(df2, on='key', how='inner')` |
| `RETAIN + sum statement` | `F.sum().over(Window.partitionBy().orderBy().rowsBetween(...))` |
| `FIRST./LAST.` within BY group | `Window.partitionBy().orderBy()` with `row_number()` |
| `PROC SORT NODUPKEY` | `df.dropDuplicates(['key_col'])` |
| `PROC MEANS` | `df.describe()` or `df.groupBy().agg(F.mean(), F.stddev(), ...)` |
| `Arrays with DO loop` | `F.array()`, `F.explode()`, `F.transform()` |
| `%LET macro variable` | Python variable or config parameter |
| `%DO loop over datasets` | Python `for` loop over DataFrames |
| SAS date integer | Convert using `F.date_add(F.lit('1960-01-01'), F.col('sas_date_col').cast('int'))` |

---

## SAS-to-Modern-Platform Migration Strategy

### Phase 1: Inventory
1. Catalogue all SAS programs: count, file sizes, LOC, last modified date, responsible team.
2. Catalogue input/output datasets: identify upstream sources and downstream consumers.
3. Identify SAS library connections (ODBC, NFS mounts, network paths).
4. Document scheduled execution: batch windows, dependencies, SLA.

### Phase 2: Complexity Scoring

Score each program on:
- Lines of code.
- Number of PROC calls and DATA steps.
- Macro usage complexity (nesting depth, dynamic code generation via `%INCLUDE`).
- Statistical PROC usage (e.g. PROC REG, PROC LOGISTIC require Python ML equivalents).
- ODS reporting outputs (require BI tool replacement).
- External file I/O (INFILE, FILE statements).
- Performance requirements (large dataset processing).

| Score Band | Indication | Approach |
|---|---|---|
| Low (1–3) | Simple filtering, aggregation, straightforward joins | Automated translation candidate |
| Medium (4–6) | Moderate macros, multiple merges, simple stats procs | Semi-automated with manual review |
| High (7–10) | Deep macro nesting, complex arrays/loops, statistical modelling | Manual rewrite required |

### Phase 3: Automated Translation Candidates
Suitable for automated or semi-automated translation:
- Simple DATA step filters and column calculations → PySpark or SQL.
- PROC SQL queries → direct SQL translation.
- PROC SORT NODUPKEY → `dropDuplicates()`.
- PROC MEANS / PROC FREQ with simple groupings → SQL aggregations.

### Phase 4: Manual Rewrite Candidates
Require full analysis and manual implementation:
- Programs using deep macro nesting or dynamic `%INCLUDE` chains.
- Programs using `RETAIN` for complex running totals (window functions in SQL/Spark).
- Programs calling PROC REG, PROC LOGISTIC, or other statistical procs.
- Programs producing ODS formatted reports (replacement BI tooling required).
- Programs with INFILE / FILE statements for fixed-width flat file processing.

### Phase 5: Validation and Reconciliation
For every migrated program:
1. Run both old (SAS) and new (Python/Spark/SQL) pipelines in parallel against the same input data.
2. Compare outputs: row counts, column-level aggregates (SUM, COUNT, MIN, MAX, NULL counts).
3. Document any intentional differences (bug fixes, logic improvements).
4. Obtain data owner sign-off on the reconciliation results before decommissioning the SAS version.

```python
# Example reconciliation check in PySpark
sas_counts  = sas_df.groupBy("account_id").agg(F.count("*").alias("row_count"), F.sum("amount").alias("total"))
spark_counts = spark_df.groupBy("account_id").agg(F.count("*").alias("row_count"), F.sum("amount").alias("total"))

diff = sas_counts.join(spark_counts, on="account_id", how="full_outer") \
    .withColumn("count_diff",  F.col("sas_counts.row_count")  - F.col("spark_counts.row_count")) \
    .withColumn("amount_diff", F.col("sas_counts.total") - F.col("spark_counts.total")) \
    .filter((F.col("count_diff") != 0) | (F.col("amount_diff") != 0))

diff.show()
```
