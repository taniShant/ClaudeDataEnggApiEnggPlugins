---
description: "Question catalogue for resolving ambiguities when field confidence is below 0.7 — covers SCD type detection, source modification dates for SCD2, Protegrity DE names for encryption, and crypto direction handling."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-28
---

# Guided Mode — Ambiguity Resolution

When the plugin cannot resolve a field with confidence ≥ 0.7, it surfaces an ambiguity to the user. These are the standard questions with risk context.

## Confidence Threshold
- Default: 0.7
- Below threshold → route to guided mode
- Never silently fill a required field when confidence is below threshold

## Question Catalog

### Q1: SCD Type Unknown [BLOCKER]
**Question:** "Is this table SCD1 (overwrite) or SCD2 (history-preserving)? Are eff_start_date/eff_end_date/active columns expected?"
**Risk if guessed:** Generates wrong audit columns; breaks CDC logic downstream
**Default possible:** No safe default
**Evidence to show:** Target column list (presence/absence of eff_start_date, eff_end_date, active)

### Q2: Source Modification Date for SCD2 [BLOCKER]
**Question:** "Which source column drives versioning for eff_start_date? (e.g., row_lst_mod_dte, last_modified, update_ts)"
**Risk:** Wrong SCD start date → incorrect history
**Default:** No
**Evidence:** Source column list with date/timestamp types

### Q3: Crypto DE Name [BLOCKER]
**Question:** "What is the exact Protegrity Data Element name for column {x}? (e.g., UK_TOK_ACCT_L0R0_NUM_DE)"
**Risk:** Wrong DE → crypto failure at runtime, potential compliance breach
**Default:** No — never guess a DE
**Evidence:** Crypto UDF calls found in SQL, column sensitivity classification

### Q4: Crypto Direction [BLOCKER]
**Question:** "Should this column be detokenized (encrypted→clear), tokenized (clear→encrypted), or re-tokenized (source DE→different target DE)?"
**Risk:** Wrong direction → data exposed or double-encrypted
**Default:** No

### Q5: Join Cardinality [BLOCKER]
**Question:** "Is the join to {table} expected to produce 1:1 or 1:many? Could it produce duplicates?"
**Risk:** 1:many → row explosion; wrong grain
**Default:** No
**Evidence:** Source table row counts, join key cardinality (from Excel profiling report or user answer).
If unavailable, recommend: `SELECT {join_key}, COUNT(*) AS cnt FROM {table} GROUP BY {join_key} HAVING COUNT(*) > 1 LIMIT 10;` (Query 2F from `profiling_queries.sql`)

### Q5b: Join Key Column Names [BLOCKER]
**Question:** "For the join between {left_table} and {right_table}: what column on {left_table} joins to what column on {right_table}? (They may have different names.)"
**Risk:** Incorrect join condition → wrong data linkage, missing rows, or cartesian products
**Default:** No — must be explicitly provided
**Evidence:** DDL/metadata column lists for both tables, SQL JOIN clause if available
**When to ask:** When join is detected between two tables but column names are NOT identical or NOT inferrable from SQL/metadata
**Example prompt:** "TETLTCCC.FRC_RSN_CDE joins to ref_src_decode.src_code — is this correct, or is there a different join column?"

### Q6: Multi-source Primary Source [BLOCKER]
**Question:** "Which source table is the primary driver (one row per primary key)? Others join to it."
**Risk:** Wrong grain, incorrect NULL expectations
**Default:** No
**Evidence:** Table row counts, PK definitions

### Q7: Business Rule for CASE WHEN [WARNING]
**Question:** "What should the ELSE value be for status_code mapping? What codes map to what values?"
**Risk:** Incorrect business classification
**Default:** Can default to 'UNKNOWN' with warning
**Evidence:** Distinct values from profiling (Excel report or user answer), existing CASE expressions in SQL.
If unavailable, recommend: `SELECT {column}, COUNT(*) AS freq FROM {table} GROUP BY {column} ORDER BY freq DESC LIMIT 20;` (Query 1D from `profiling_queries.sql`)

### Q8: Default Value for NULLs [WARNING]
**Question:** "When {column} is NULL in source, should target be NULL, -99, 'UNKNOWN', or something else?"
**Risk:** May break downstream consumers expecting non-NULL
**Default:** Leave NULL (no COALESCE)
**Evidence:** Null rates from profiling (Excel report or user answer), downstream consumption patterns.
If unavailable, recommend: `SELECT COUNT(*) AS total, SUM(CASE WHEN {column} IS NULL THEN 1 ELSE 0 END) AS null_count FROM {table};` (Query 1A from `profiling_queries.sql`)

### Q9: Source-of-Truth in Multi-Source [BLOCKER]
**Question:** "When {field} differs between source A and source B, which takes precedence?"
**Risk:** Incorrect value reported
**Default:** No

### Q10: Date Format in Source [WARNING]
**Question:** "Is {column} stored as YYYYMMDD integer, epoch, or ISO string?"
**Risk:** Wrong date parse → NULL or wrong dates
**Default:** Can infer from profiling (Excel report or user answer) if available
**Evidence:** Sample values, column datatype, profiling patterns.
If unavailable, recommend: `SELECT {column}, TYPEOF({column}) FROM {table} LIMIT 5;` (Query 1E from `profiling_queries.sql`)

### Q11: Table Grain [BLOCKER]
**Question:** "What is the grain of {target_table}? (i.e., what uniquely identifies one row?)"
**Risk:** Wrong results, duplicates, or incorrect downstream joins. Grain is appended to Target Table Description (Column L) and defines the table's uniqueness contract.
**Default:** No safe default — must be resolved.
**When triggered:** When the sttm-row-generator-agent's §Grain Derivation algorithm cannot determine grain with confidence ≥ 0.7 (all evidence sources P1–P5 produced empty results).
**Evidence to show:**
  - Columns with Key Column = Y: `{key_columns}`
  - Columns with `grain_impact = "key"` from SQL lineage: `{grain_key_columns}`
  - GROUP BY columns (if aggregation detected): `{group_by_columns}`
  - `grain_keys` from final intermediate step (if multi-step ETL): `{final_grain_keys}`
  - Interview Q3.7 answer (if available): `{pk_composition}`
  - Table type classification: `{table_type}` (SCD2 implies "per effective period")
**Resolution action:** On answer, append `" Grain: <user_answer>."` to target_table_description on first row. For SCD2 tables, append "per effective period" if not already stated. Set provenance: method = "user_supplied", confidence = 0.95. Verify Key Column (P) alignment — if user's grain columns differ from Key Column = Y markings, flag discrepancy as WARNING.

### Q12: Column Renamed [WARNING]
**Question:** "{source_col} not in metadata but {similar_col} exists. Are these the same?"
**Risk:** Wrong lineage if assumed
**Default:** No — present as guided question

### Q13: Notebook Logic Outdated [WARNING]
**Question:** "SQL notebook references table {x} not in metadata. Use notebook logic or current metadata?"
**Risk:** Mapping references non-existent objects
**Default:** Trust current metadata for structure; warn about logic

### Q14: Partition Column Identity [WARNING]
**Question:** "Which column(s) should be used for partitioning? Is {dw_bus_dt} the partition key?"
**Risk:** Wrong partition → query performance issues
**Default:** Can infer from convention if matches dw_bus_dt or active

### Q15: High-End Date Value [WARNING]
**Question:** "What high-end date for open SCD2 records? (3499-12-31, 9999-12-31)"
**Risk:** Inconsistency with existing data
**Default:** 3499-12-31

### Q16: Audit Column Naming [WARNING]
**Question:** "Does this project use dw_lod_tmp/dw_upd_lod_tmp or different names?"
**Risk:** Naming inconsistency
**Default:** dw_lod_tmp/dw_upd_lod_tmp

### Q17: Cross-Source Metadata Conflict [WARNING]
**Question:** "Source dictionary shows source as {A} but current metadata shows {B}. Which is correct?"
**Risk:** Incorrect mapping if source dictionary was correct
**Default:** Trust current metadata

### Q18: DM1 Model Version [WARNING]
**Question:** "Does the .dm1 represent logical or physical model? Are entity names = deployed table names?"
**Risk:** Wrong entity→table mapping
**Default:** Treat as physical model

### Q19: Markdown Target Schema Completeness [WARNING]
**Question:** "Markdown target schema may omit precision/null flags. Accept defaults? (string for types, Y for nullability)"
**Risk:** Incorrect types/constraints
**Default:** string/Y with warning

### Q20: Source Volumetrics Accuracy [WARNING]
**Question:** "Profiling data was obtained from {source_type}. When was it last updated? Are the numbers still representative?"
**Risk:** Over/underestimation of sizing
**Default:** Use provided values with staleness warning
**Note:** Only asked when profiling data IS available. Source type may be: Excel report or user answer.

### Q21: Source Table Row Count Missing [WARNING]
**Question:** "Source table {source_database}.{source_table} has no row count estimate. Approximately how many rows does it contain? (needed for broadcast hint and performance planning)"
**Risk:** Cannot determine broadcast_hint accurately; partitioning strategy may be suboptimal; capacity planning has no data
**Default:** Leave null with warning — broadcast_hint defaults to "N" (safe but possibly suboptimal for small reference tables)
**Evidence:** Table type (transactional typically large, non-transactional reference tables often small), any available sizing hints from design docs or source metadata
**Resolution action:** On answer, update `source_volumetrics[].estimated_rows` AND recalculate `broadcast_hint` (Y if estimated_rows < 10,000, N otherwise)

### Q22: Source Table Size Missing [WARNING]
**Question:** "Source table {source_database}.{source_table} has no size estimate. Approximately how large is it in GB?"
**Risk:** Storage capacity planning has no data
**Default:** Leave null with warning
**Evidence:** Row count (if provided), typical row widths for the source system
**Resolution action:** On answer, update `source_volumetrics[].estimated_size_gb`

### Q23: Source Table Daily Increment Missing [WARNING]
**Question:** "Source table {source_database}.{source_table} has no daily increment estimate. Approximately how many rows are added/changed per day?"
**Risk:** Day 1 scheduling and batch sizing have no data
**Default:** Leave null with warning
**Evidence:** Table type (transactional = typically high daily volume; non-transactional reference = typically low/zero)
**Resolution action:** On answer, update `source_volumetrics[].daily_increment_rows` and `source_volumetrics[].daily_increment_size_gb` (derive size from row count × avg row size if known)

### Q24: Profiling Data Acquisition Guidance [INFO]
**Trigger:** When profiling data is missing for one or more source tables and user cannot provide estimates directly.
**Action:** Present the user with specific SQL queries from `profiling_queries.sql` they can execute externally:
- For row counts and sizing: `SELECT COUNT(*) AS row_count FROM {source_database}.{source_table};`
- For PK uniqueness: `SELECT {pk_column}, COUNT(*) FROM {table} GROUP BY {pk_column} HAVING COUNT(*) > 1;` (Query 2C)
- For join cardinality: `SELECT {join_key}, COUNT(*) FROM {table} GROUP BY {join_key} HAVING COUNT(*) > 1 LIMIT 10;` (Query 2F)
- For null rates: `SELECT COUNT(*) AS total, SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END) AS nulls FROM {table};` (Query 1A)
- For value distribution: `SELECT {col}, COUNT(*) AS freq FROM {table} GROUP BY {col} ORDER BY freq DESC LIMIT 20;` (Query 1D)
**Explain:** "These queries can be run against your source database (Athena/Presto/Spark SQL compatible). Results will help populate Source Volumetrics accurately and determine broadcast hints, partitioning strategy, and capacity planning."
**Follow-up:** Accept results in any format (copy-paste, screenshot, Excel). Parse and integrate into profiling inventory.
**Note:** Do NOT assume `profiling_signals.json` exists. Profiling is obtained exclusively via Excel reports or user-provided answers.

### Q25: Unqualified Column Source Table [BLOCKER]
**Question:** "Column '{column}' in the SQL {clause_type} clause has no table alias. It exists in multiple source tables: {candidate_list}. Which table should provide this column?"
**Risk if guessed:** Wrong source table → incorrect lineage (SELECT), wrong row filtering (WHERE/HAVING/QUALIFY), wrong join (ON), or wrong grouping (GROUP BY)
**Default:** No safe default — column could have different values in each table
**Evidence to show:**
  - Candidate tables with the column and their datatypes
  - SQL context (the clause containing the unqualified reference + FROM/JOIN clauses)
  - Join relationship between tables
  - Which clause the ambiguity appears in (SELECT, WHERE, JOIN ON, GROUP BY, HAVING, QUALIFY, expression)
**When to ask:** When sttm-sql-lineage-agent's Unqualified Column Resolution cascade reaches Step 3 (heuristic) or Step 4 (unresolvable) — i.e., metadata schema lookup and sqlglot qualify_columns could not deterministically resolve to exactly one table. Applies to unqualified references in ANY SQL clause — not just SELECT.
**Resolution action:** On answer, update lineage entry / filter / join condition with confirmed source table, set confidence to 0.95 (user_supplied), record provenance method as "user_supplied"

### Q26: UNION Branch Source Attribution [WARNING]
**Question:** "This SQL uses UNION ALL to combine {N} SELECT branches. For target column '{column}': Branch 1 sources from {table_a}.{col_a}, Branch 2 sources from {table_b}.{col_b}. Is this correct? Are there additional source considerations?"
**Risk:** Wrong branch attribution → incorrect lineage for union-combined data
**Default:** Accept sttm-sql-lineage-agent's per-branch extraction
**Evidence:** Per-branch lineage extraction, source table metadata
**When to ask:** When UNION is detected and branch-level source columns cannot be deterministically aligned with target columns

### Q27: Self-Join Semantics [WARNING]
**Question:** "Table '{table}' is joined to itself with aliases '{alias_L}' and '{alias_R}'. What does each alias represent? (e.g., current period vs prior period, parent vs child, active vs historical)"
**Risk:** Wrong alias interpretation → incorrect transformation logic
**Default:** No safe default
**Evidence:** SQL JOIN condition, column references in SELECT
**When to ask:** When self-join is detected and the logical role of each alias is not obvious from column names or conditions

### Q28: MERGE Branch Strategy [BLOCKER]
**Question:** "This MERGE statement has both MATCHED (update) and NOT MATCHED (insert) branches. For the MATCHED branch: does it close the old record and insert new (SCD2 close+insert), or update in place (SCD1 overwrite)?"
**Risk:** Wrong merge strategy → incorrect SCD behavior, data corruption
**Default:** No safe default
**Evidence:** MERGE WHEN MATCHED SET clause, presence of eff_end_date/active columns
**When to ask:** When MERGE is detected and the SCD strategy cannot be determined from SQL patterns alone

### Q29: PIVOT Column Semantics [WARNING]
**Question:** "This SQL uses PIVOT on column '{value_col}' with key values {key_values}. Each pivot value becomes a separate target column. Confirm: target column '{target_col}' maps to pivot key '{key_value}' — is this correct?"
**Risk:** Wrong pivot key mapping → columns contain wrong aggregated values
**Default:** Accept positional mapping from SQL PIVOT clause
**Evidence:** PIVOT clause, target column names, pivot key values

### Q30: Temp Table Chain Resolution [WARNING]
**Question:** "The SQL creates temporary table '{temp_name}' which is then used in the final query. The agent traced this to base table(s): {resolved_tables}. Is this resolution correct, or does '{temp_name}' source from different tables?"
**Risk:** Incomplete lineage — temp table may reference additional sources not in the same file
**Default:** Accept agent's resolution if all referenced tables are found
**Evidence:** CREATE TEMP TABLE statement, INSERT...SELECT into temp table, final query referencing temp table
**When to ask:** When temp table's source SELECT references tables not in known_sources

### Q31: PySpark Source Table Name [BLOCKER]
**Question:** "PySpark reads from path '{path}' (e.g., s3://bucket/path/table). What is the logical table name (database.table) for this data source?"
**Risk:** Missing source attribution → no lineage trace
**Default:** No safe default — path-based reads have no inherent logical name
**Evidence:** spark.read path, any variable names or comments in the code
**When to ask:** When PySpark uses spark.read.parquet/csv/json with a file path instead of spark.table()

### Q32: NATURAL JOIN Column Matching [BLOCKER]
**Question:** "SQL uses NATURAL JOIN between '{left_table}' and '{right_table}'. Without an explicit ON condition, columns are matched by name. Which columns should be matched? Available common columns from schema_dict: {common_column_list}"
**Risk:** Silent wrong match — columns with the same name but different semantics join incorrectly, producing corrupt lineage
**Default:** No safe default
**Evidence:** schema_dict column lists for both tables, common column names between them
**When to ask:** When NATURAL JOIN is detected AND schema_dict lookup finds 2+ common columns or schema_dict is incomplete for either table (CP10 applies)
**Resolution action:** Rewrite as explicit JOIN ON with confirmed columns. Confidence = 0.95 (user_supplied).

### Q33: Conditional Crypto Direction [BLOCKER]
**Question:** "Column '{column}' has a crypto UDF inside a CASE WHEN expression: branch(es) {branches_with_crypto} apply {direction}, but branch(es) {branches_without} do not apply crypto. Should ALL branches apply crypto uniformly, or is the conditional application intentional?"
**Risk:** Data partially unprotected in some code paths → compliance breach
**Default:** No safe default
**Evidence:** Full CASE expression showing which branches have crypto UDFs and which do not
**When to ask:** When CASE WHEN branches have inconsistent crypto UDF application (CP13 applies)
**Resolution action:** On answer, either apply crypto uniformly across all branches, or document the intentional conditional pattern with compliance justification in Additional Context.

### Q34: Multiple DEs in Single Column [BLOCKER]
**Question:** "Column '{column}' has a CASE expression that applies different Protegrity Data Elements in different branches: {de_list}. Is this intentional? Which DE governs the column's overall crypto classification?"
**Risk:** Multiple DEs in one column → unclear which DE controls access policy; downstream consumers may apply wrong decryption
**Default:** No safe default
**Evidence:** CASE expression with different cloud_api_udf_{DE} calls per branch, list of detected DEs
**When to ask:** When 2+ different DE names are detected in CASE branches for the same target column
**Resolution action:** On answer, record the governing DE for the column and document branch-specific DEs in Additional Context.

### Q35: Dynamic PySpark Table Name [BLOCKER]
**Question:** "PySpark code uses spark.sql() with dynamic SQL: '{code_snippet}'. The table name contains f-string variable '{variable}' which cannot be resolved from static analysis. What is the actual table name (database.table)?"
**Risk:** Missing source attribution → no lineage trace for the entire query
**Default:** No safe default — variable value is unknown at parse time
**Evidence:** spark.sql() call with f-string or .format(), variable name, any variable assignments in the same file/notebook
**When to ask:** When spark.sql() contains {variable} interpolation and the variable value cannot be determined from static backward analysis (CP15 applies)
**Resolution action:** On answer, substitute the resolved table name into the SQL string and re-parse for lineage. Confidence = 0.90 (user_supplied).

### Q36: VALUES Clause Semantics [WARNING]
**Question:** "SQL contains a VALUES clause used as an inline table source: VALUES {value_preview}. What do the columns represent? Suggested column names: {inferred_names_or_positional}"
**Risk:** Incorrect column naming → wrong lineage attribution from the inline source
**Default:** Use positional names (col1, col2, ...) with a warning that names are inferred
**Evidence:** VALUES clause content, any surrounding alias (AS v(name1, name2)) or parent MERGE/INSERT column list
**When to ask:** When VALUES clause is used as a source (in FROM or MERGE USING) and column names are not provided via explicit alias (CP11 applies)
**Resolution action:** On answer, assign confirmed column names to the VALUES source. Confidence = 0.90.

### Q37: CTE Depth Confirmation [WARNING]
**Question:** "SQL contains a CTE chain {depth} levels deep: {cte_chain_description}. The final CTE references intermediate CTEs which reference base tables. Resolved base table lineage: {resolved_bases}. Is this chain correct, or do intermediate CTEs have additional transformations that affect lineage?"
**Risk:** Deep CTE chains may have subtle intermediate transformations that alter lineage attribution
**Default:** Accept resolved chain if all base tables are in known_sources
**Evidence:** CTE dependency graph (DAG), base table resolution per CTE, chain depth count
**When to ask:** When CTE chain depth exceeds 3 levels
**Resolution action:** On confirmation, accept chain lineage with depth-adjusted confidence. On correction, update intermediate CTE attribution.

### Q38: Rolling Deletion Predicate [WARNING]
**Question:** "Does target table '{target_table}' require rolling deletion of aged data? If yes, provide the SQL WHERE-clause predicate defining which rows to delete."
**Format:** SQL WHERE-clause predicate (a boolean expression suitable for a DELETE ... WHERE clause)
**Sample values:**
  - `dw_bus_dt < CURRENT_DATE - INTERVAL 7 YEARS`
  - `effective_end_date < DATE_SUB(CURRENT_DATE, 365)`
  - `snapshot_date < DATEADD(year, -3, GETDATE())`
**Risk if guessed:** Wrong predicate could delete current data or retain data beyond compliance requirements
**Default:** None — leave the key absent from additional_context if rolling deletion is not applicable
**Evidence to show:**
  - Date/timestamp columns in the target table that could serve as age boundaries
  - Any DELETE statements found in source SQL targeting the same or similar tables
  - Design document references to data retention policies or rolling deletion windows
  - Source volumetrics row counts (large historical tables more likely to need rolling deletion)
**When to ask:** CP18 penalty applies (indicators of rolling data retention but predicate not determined), or interview question 5.13b was skipped but design docs hint at retention policy
**Resolution action:** On answer, set `rolling_deletion_predicate` in `additional_context`. If user says "not applicable" or "no rolling deletion", omit the key entirely. Set provenance: method = "user_supplied", confidence = 0.95.
