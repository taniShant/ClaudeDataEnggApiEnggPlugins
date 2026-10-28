---
description: "Conditional STTM extension for PySpark lineage extraction — maps DataFrame methods to SQL equivalents, detects source tables via spark.table() and path-based reads with confidence scoring."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-28
---

# PySpark Comprehensive Handling (Lineage Extension)

> **Loaded conditionally** — only when code_artifact type = "pyspark" is detected.

## PySpark Comprehensive Handling

PySpark code requires sequential analysis of DataFrame method chains. The agent must map all common DataFrame operations to SQL equivalents for lineage extraction.

### Source Table Detection (CRITICAL)

Identify source tables from PySpark read operations — without this, lineage has no source:

| PySpark Pattern | Mapping |
|----------------|---------|
| `spark.table("db.table")` | source_database = "db", source_table = "table" |
| `spark.read.format("iceberg").load("db.table")` | source_database = "db", source_table = "table" |
| `spark.read.table("db.table")` | source_database = "db", source_table = "table" |
| `spark.read.parquet("s3://bucket/path/table")` | Route to guided mode — ask for logical table name |
| `spark.read.csv(...)` / `spark.read.json(...)` | Route to guided mode — ask for logical table name |
| `spark.sql("SELECT ... FROM db.table")` | Parse the SQL string for source tables |

**Confidence**: `spark.table()` / `.load("db.table")` = 0.95. Path-based reads = 0.50 (guided mode).

### DataFrame Method → SQL Mapping

| PySpark Method | SQL Equivalent | Lineage Impact |
|---------------|----------------|----------------|
| `.select("col1", "col2")` | `SELECT col1, col2` | Defines target columns |
| `.select(F.col("a").alias("b"))` | `SELECT a AS b` | Column rename |
| `.withColumn("new", expr)` | `SELECT *, expr AS new` | Adds/replaces column |
| `.withColumnRenamed("old", "new")` | `SELECT old AS new` | Column rename |
| `.filter(cond)` / `.where(cond)` | `WHERE cond` | Row filter → `filters_extracted` |
| `.join(other, on, how)` | `JOIN other ON ... TYPE` | Join → `joins_detected`, `how` = join type |
| `.groupBy("col").agg(...)` | `GROUP BY col` + aggregate | Aggregation lineage |
| `.orderBy("col")` / `.sort("col")` | `ORDER BY col` | Note only — no lineage change |
| `.drop("col")` | Removes column from projection | Column excluded from lineage |
| `.distinct()` | `SELECT DISTINCT` | Note in `filters_extracted.distinct` |
| `.union(other)` / `.unionAll(other)` | `UNION ALL` | See UNION handling above |
| `.unionByName(other)` | `UNION ALL` (name-aligned) | Align by column name not position |
| `.crossJoin(other)` | `CROSS JOIN` | Emit cartesian warning |
| `.limit(n)` | `LIMIT n` | Note only — warn if in production |

### PySpark Expression Mapping

| PySpark Expression | SQL Equivalent | Signal |
|-------------------|----------------|--------|
| `F.col("col")` | Column reference | direct |
| `F.lit(value)` | Literal/constant | hardcoded |
| `F.when(cond, val).when(...).otherwise(default)` | `CASE WHEN cond THEN val ... ELSE default END` | case |
| `F.coalesce(col1, col2)` | `COALESCE(col1, col2)` | coalesce |
| `F.concat(col1, F.lit(" "), col2)` | `CONCAT(col1, ' ', col2)` | concat |
| `F.sum("col")` / `F.count("col")` etc. | `SUM(col)` / `COUNT(col)` | aggregate |
| `F.window(...)` / `F.lag(...)` / `F.lead(...)` | Window function | window |
| `F.upper("col")` / `F.trim("col")` | `UPPER(col)` / `TRIM(col)` | string_transform |
| `F.broadcast(df)` | Broadcast hint | Note for Source Volumetrics `broadcast_hint` |

### expr() and selectExpr()

`df.withColumn("col", expr("CASE WHEN x > 0 THEN 'Y' ELSE 'N' END"))` and `df.selectExpr("col1", "CAST(col2 AS INT)")` embed SQL expressions inside PySpark:

1. **Extract the string argument** from `expr()` or each string in `selectExpr()`
2. **Parse as SQL expression** for lineage — apply the same transformation pattern detection as for pure SQL
3. **Confidence**: 0.90 (SQL semantics are explicit)

### PySpark UDFs

User-defined functions (`@udf`, `udf()`, `pandas_udf()`) wrap custom Python logic:

1. **Input columns**: List all columns passed as arguments to the UDF as `source_column`
2. **UDF name**: Include in `expression` — e.g., `custom_hash_udf(col1, col2)`
3. **Transformation type**: "Derived"
4. **Confidence**: 0.50–0.60 (cannot trace logic inside UDF)
5. **If UDF body is available** in the same file/notebook: attempt to trace the Python logic for source columns
6. Otherwise: Route to guided mode

### Variable Reuse / DataFrame Reassignment

PySpark code frequently reassigns variables: `df = df.withColumn("a", ...).withColumn("b", ...)`

1. **Track DataFrame state sequentially** through the script/notebook — each assignment updates the column schema
2. **The final state** of the target DataFrame (the one written or returned) determines the lineage
3. **Maintain a running column list** per variable name, updating on each `.withColumn()`, `.drop()`, `.withColumnRenamed()`, `.select()` call
4. This is analogous to temp table chain resolution in SQL

### PySpark: spark.sql() with Dynamic SQL (f-strings / .format())

When PySpark code builds SQL strings dynamically:

```python
table_name = f"{database}.{table}"
df = spark.sql(f"SELECT * FROM {table_name} WHERE date = '{bus_date}'")
```

1. **Attempt variable resolution**: Trace variable assignments backward in the same file/notebook to resolve string values
2. **If resolved**: Parse the resolved SQL string for lineage. Confidence = 0.80 (variable resolution adds uncertainty)
3. **If NOT resolved**: Apply CP15 penalty (-0.60). Route to guided mode Q35 — BLOCKER. Return the unresolved SQL template as evidence.
4. **Common patterns to resolve**:
   - `f"...{var}..."` — trace `var` assignment
   - `"...{}...".format(var)` — trace `var` assignment
   - `"..." + var + "..."` — trace `var` assignment
   - `sql_template % (var,)` — trace `var` assignment
5. **If variable comes from function parameter or external config**: Cannot resolve → guided mode

**transformation_signals**: `["pyspark", "dynamic_sql", "f_string"]`

### PySpark: RDD Operations

When PySpark code uses RDD operations (`df.rdd.map`, `df.rdd.flatMap`, `rdd.reduceByKey`):

1. **RDD operations are opaque** — the Python function inside .map/.flatMap cannot be traced for column lineage
2. **If RDD result is converted back to DataFrame** (`rdd.toDF()`, `spark.createDataFrame(rdd)`):
   - Record that lineage passes through an opaque RDD stage
   - source_column = all columns from the input DataFrame that was converted to RDD
   - Confidence = 0.40 (opaque transformation)
3. **Emit warning**: "RDD operation detected — column lineage cannot be traced through rdd.{method}(). Consider refactoring to DataFrame API for traceable lineage."
4. **Route to guided mode** if the RDD result feeds into the target DataFrame

**transformation_signals**: `["pyspark", "rdd", "opaque"]`

### PySpark: Pandas UDF / .toPandas()

When PySpark code uses `pandas_udf` or `.toPandas()`:

1. **pandas_udf**: Treat like a regular UDF (see PySpark UDFs section above) but note that it operates on pandas Series/DataFrames internally
   - Input columns = function arguments
   - Confidence = 0.50 (opaque Python logic)
2. **.toPandas()**: Converts Spark DataFrame to pandas — usually for post-processing or export
   - If followed by pandas operations that feed back into Spark: lineage through pandas is opaque
   - Record the columns of the Spark DataFrame before `.toPandas()` as the last traceable lineage point
3. **Emit warning**: "pandas UDF/.toPandas() detected — lineage through pandas operations is not traceable"

**transformation_signals**: `["pyspark", "pandas_udf", "opaque"]` or `["pyspark", "to_pandas", "opaque"]`

### PySpark: Recursive DataFrame Construction (Loop Reassignment)

When PySpark code builds a DataFrame in a loop:

```python
for col_name in column_list:
    df = df.withColumn(col_name, some_expression(col_name))
```

1. **Detect loop patterns**: for/while loops containing DataFrame method calls (`.withColumn`, `.drop`, `.withColumnRenamed`)
2. **If loop body is static** (same operation per iteration, just different column names): Unroll by applying the operation to each column in the iterable. Confidence = 0.80.
3. **If loop body is dynamic** (different logic per iteration, conditional branches): Mark as partially opaque. List all potentially affected columns. Confidence = 0.60.
4. **Track state**: The final state of `df` after the loop exit determines lineage — same principle as Variable Reuse above, but applied across loop iterations.
5. **Emit warning**: "DataFrame constructed in loop — verify all loop iterations are accounted for in lineage."

**transformation_signals**: `["pyspark", "loop_construction"]`
