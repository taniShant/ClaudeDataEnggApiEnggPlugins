---
description: "Load guard for NL_INTERPRETATION mode — pre-checks locked predicates (mandatory) before interpreting join conditions and filters from free-text transformation_logic descriptions."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-07-08
---

# NL Join & Filter Interpretation Rules (Free-Text → PySpark)

> **Load guard:** Read ONLY if any column has `MODE = NL_INTERPRETATION` (references multiple source tables AND `structured_transformation` is null, OR single-source with filter language and no structured_transformation).

When a column references multiple source tables AND `structured_transformation` is null (NL_INTERPRETATION mode), attempt to interpret `transformation_logic` free-text for join and filter semantics.

## Pre-Check: Locked Predicates (MANDATORY — runs BEFORE any NL interpretation)

Before interpreting any join or filter from free-text, check if `session/extracted_predicates.json` provides LOCKED constraints for the current target column:

### Join Predicate Pre-Check

1. Read `session/extracted_predicates.json` → `join_predicates[]`
2. Filter to predicates where `target_columns` includes the current target column being generated
3. **If LOCKED join predicates exist for this column:**

   **Layer 1 — Semantic relationship (LOCKED, non-negotiable):**
   - The predicate defines WHICH columns join to which: `left_table.left_col OPERATOR right_table.right_col`
   - Do NOT change either side of the relationship (no column swaps, no name "corrections")
   - Do NOT re-interpret the join condition from `transformation_logic` free-text
   - Do NOT alter an asymmetric predicate (`A.x = B.y`) into a symmetric one (`A.x = B.x`) or vice versa

   **Layer 2 — PySpark syntax selection (derived from column names, NOT locked):**
   - Apply the symmetric/asymmetric syntax rule (see "Join Pattern Recognition" table below):
     - If locked predicate has `left_col == right_col` (same name) → list syntax `["col"]`
     - If locked predicate has `left_col != right_col` (different names) → expression syntax + `.drop(right_key)`
   - The locked predicate text format (`A.x = B.x`) does NOT dictate expression syntax — syntax is always determined by column-name equality

   **Emit:** `# JOIN: locked from mapping extraction (session/extracted_predicates.json)`
   **Skip:** the "Join Pattern Recognition" table below — predicates are already resolved (only syntax rule applies)
4. **If NO locked join predicates exist for this column** (or file doesn't exist):
   - Proceed with NL interpretation below as normal
   - The file may not exist if the mapping was parsed before STEP 2.8, or if no table.col patterns were found

### Literal Value Pre-Check

1. Read `session/extracted_predicates.json` → `literals[]`
2. Filter to literals where `target_column` matches the current target column being generated
3. **If LOCKED literals exist for this column:**
   - USE each locked value **exactly as specified** in `.filter()`, `F.when()`, or `F.lit()` calls
   - Do NOT substitute alternative values (even if they "make more sense" for the column name)
   - Emit: `# LITERAL: locked from mapping extraction`
   - Skip the "Filter Pattern Recognition" table below for these specific comparisons — they are resolved
4. **If NO locked literals exist for this column** (or file doesn't exist):
   - Proceed with NL filter interpretation below as normal

### Precedence Summary

```
LOCKED predicates/literals  →  semantic relationship fixed (apply syntax rule only)
         ↓ (if not locked)
NL Pattern Recognition      →  interpret from free-text (tables below)
         ↓ (if unparseable)
spark.sql() fallback        →  preserve as-is with TODO comment
```

---

## Join Pattern Recognition

| NL Pattern | PySpark Translation |
|---|---|
| `"LEFT JOIN <table> ON <condition>"` | `.join(table_df, on=<parsed_condition>, how="left")` |
| `"INNER JOIN <table> ON <condition>"` | `.join(table_df, on=<parsed_condition>, how="inner")` |
| `"RIGHT JOIN <table> ON <condition>"` | `.join(table_df, on=<parsed_condition>, how="right")` |
| `"FULL JOIN / FULL OUTER JOIN <table> ON <condition>"` | `.join(table_df, on=<parsed_condition>, how="full")` |
| `"Join/Merge with <table> on/where/using <key>"` | `.join(table_df, ["key"], "left")` — symmetric key, list syntax |
| `"Get/Fetch/Lookup <col> from <table> based on/using/where <key>"` | LEFT join to table, select col |
| `"Match <table> on <key>"` | `.join(table_df, on=<key>, how="left")` |
| `"Cross join with <table>"` | `.crossJoin(table_df)` |

**`<parsed_condition>` — PySpark join syntax selection (MANDATORY — applies to ALL rows above):**

The `<parsed_condition>` placeholder resolves to one of two PySpark syntaxes depending on whether left and right column NAMES are identical:

| Key Relationship | Syntax | Example |
|---|---|---|
| **SYMMETRIC (single key)** — `left_col == right_col` | LIST: `["col"]` | `.join(df, ["question_id"], "left")` |
| **SYMMETRIC (multiple keys)** — all keys same-name | LIST: `["col1", "col2"]` | `.join(df, ["order_id", "line_id"], "inner")` |
| **ASYMMETRIC (single key)** — `left_col != right_col` | EXPRESSION + `.drop(right_key)` | `.join(df, main["survey_id"] == df["unique_ref"], "left").drop(df["unique_ref"])` |
| **ASYMMETRIC (multiple keys)** — all keys different-name | EXPRESSION + `.drop()` all right keys | `.join(df, (a==b) & (c==d), "left").drop(right["b"], right["d"])` |
| **MIXED** — some symmetric, some asymmetric in same join | EXPRESSION + `.drop()` ALL right keys | See Rule 5b in transform-generator-agent |

**Why this matters**: Expression syntax (`left["col"] == right["col"]`) with same-name keys creates TWO columns with that name in the output. Any subsequent `F.col("col")` throws `AnalysisException: Reference 'col' is ambiguous`. List syntax auto-deduplicates.

**Asymmetric keys MUST use expression syntax + drop right key** because list syntax cannot express a relationship between differently-named columns. The right-side join key is a redundant foreign key reference post-join and should be dropped immediately to prevent column accumulation in chained joins.

Example: `customer_response.customer_survey_id = wm_append_data.unique_survey_ref` →
```python
.join(wm_df, cr["customer_survey_id"] == wm_df["unique_survey_ref"], "left").drop(wm_df["unique_survey_ref"])
```
Exception: Do NOT drop if the right key column itself maps to a target column in the final SELECT.

**Default join type when unspecified**: LEFT (most common in data product pipelines).

## Config-Aware Filter Suppression (MANDATORY pre-check)

Before generating ANY `.filter()` call from NL interpretation on a SINGLE source alias:
1. Look up the source alias in the filter manifest (`session/generated_configs/{table}_filters.json` → `filters_declared`)
2. If the interpreted filter is **semantically equivalent** to a filter already declared in config for this alias → **SUPPRESS**
3. Emit suppression comment: `# SourceReader applies '{filter_expr}' from config for alias '{alias}' — not duplicated here`
4. Only generate `.filter()` when:
   - The filter is a POST-JOIN filter (columns from multiple sources after join)
   - The filter has NO matching entry in the filter manifest (not declared in config)
   - The filter operates on a computed/derived column (doesn't exist in source)

**Semantic equivalence** means: same column(s), same operator, same value(s) — even if the NL phrasing differs from the config expression. Examples:
- NL "Only active records" ≡ config `active = '1'` → SUPPRESS
- NL "Filter status NOT IN ('CLO','RED')" ≡ config `status NOT IN ('CLO','RED')` → SUPPRESS
- NL "Filter status NOT IN ('CLO','RED','WOF')" vs config `status NOT IN ('CLO','RED')` → NOT equivalent (different values) → GENERATE

## Filter Pattern Recognition

| NL Pattern | PySpark Translation | Config Suppression Check |
|---|---|---|
| `"Filter/Where <col> = <value>"` | `.filter(F.col(col) == value)` | Check manifest for this alias |
| `"Filter/Where <col> != / <> / NOT <value>"` | `.filter(F.col(col) != value)` | Check manifest for this alias |
| `"Filter/Where <col> IN (<values>)"` | `.filter(F.col(col).isin(values))` | Check manifest for this alias |
| `"Filter/Where <col> NOT IN (<values>)"` | `.filter(~F.col(col).isin(values))` | Check manifest for this alias |
| `"Only active records" / "active = 1/Y/true"` | SUPPRESS if NonTransactional (config default handles it). Generate only if NOT in config. | Standard default — almost always suppressed |
| `"Exclude closed/inactive/expired"` | `.filter(F.col("status") != "<excluded_value>")` | Check manifest for this alias |
| `"Where <col> > / < / >= / <= <value>"` | `.filter(F.col(col) <op> value)` | Check manifest for this alias |
| `"Latest/most recent record per <key>"` | `ROW_NUMBER().over(Window.partitionBy(key).orderBy(F.col(ts).desc()))` dedup | NOT a config filter — always generate |
| `"Pick first/last record by <col>"` | ROW_NUMBER dedup with orderBy asc/desc | NOT a config filter — always generate |
| `"Date = {control_Date} / business_date"` | SUPPRESS if Transactional day1 (config default handles it). Generate only if NOT in config. | Standard default — almost always suppressed |
| `"Between <start> and <end>"` | `.filter(F.col(col).between(start, end))` | Check manifest for this alias |
| `"Is not null" / "not empty"` | `.filter(F.col(col).isNotNull())` | Check manifest for this alias |

## NL Interpretation Execution Rules

- **FIRST**: Check filter manifest for suppression (mandatory pre-check above)
- Apply filters BEFORE joins when the filter targets a specific source table AND is not suppressed by config
- Apply filters AFTER joins when the filter references columns from multiple tables (these are never in config)
- When join type is ambiguous, default to LEFT JOIN and emit: `# ADVISORY: Join type not specified — defaulting to LEFT JOIN`
- When join condition is ambiguous, attempt to match on columns with same name across source tables
- ALWAYS emit `# ADVISORY: Join/filter logic interpreted from natural language` at top of generated join block
- If completely unparseable (no join keywords, no identifiable table references) → fall back to spark.sql() with `# TODO: Verify generated SQL from free-text logic` (existing Rule 9 fallback)

## Single-Source Filter Interpretation

Rule 11 also applies to single-source columns whose `transformation_logic` contains filter/subset language:
- **FIRST**: Check filter manifest — if the filter is declared in config for this alias → SUPPRESS (emit comment)
- If NOT in config: Detect filter keywords: "Filter", "Where", "Only", "Exclude", "Active records", "Latest record"
- Generate `.filter()` or ROW_NUMBER dedup as appropriate (only for filters not in config)
- Emit: `# ADVISORY: Filter condition interpreted from natural language`
- If no filter language detected → no filter applied (entire table consumed)

## Examples

**Multi-Source NL Interpretation:**
```
Input: "LEFT JOIN ref_product ON account.product_code = ref_product.product_code, get product_description"

Generated:
# ADVISORY: Join/filter logic interpreted from natural language
account_df = self.source_data['account']
ref_product_df = self.source_data['ref_product']
joined_df = account_df.join(ref_product_df, ["product_code"], "left")  # symmetric key → list syntax
result_col = F.col("product_description").alias("target_column_name")
```

**Multi-Source NL Interpretation (asymmetric key — expression syntax + drop right key):**
```
Input: "LEFT JOIN wm_append_data ON customer_response.customer_survey_id = wm_append_data.unique_survey_ref"

Generated:
# ADVISORY: Join/filter logic interpreted from natural language
cr_df = self.source_data['customer_response']
wm_df = self.source_data['wm_append_data']
# Asymmetric key (different column names) → expression syntax + drop redundant right key
joined_df = cr_df.join(
    wm_df,
    cr_df["customer_survey_id"] == wm_df["unique_survey_ref"],
    "left"
).drop(wm_df["unique_survey_ref"])  # Right key is redundant FK reference post-join
```

**Single-Source NL with Filter:**
```
Input: "Get balance_amount, only active accounts where status NOT IN ('CLO','RED','WOF')"

Generated:
# ADVISORY: Filter condition interpreted from natural language
account_df = self.source_data['account']
account_filtered = account_df.filter(~F.col("status").isin("CLO", "RED", "WOF"))
result_col = F.col("balance_amount").alias("target_column_name")
```
