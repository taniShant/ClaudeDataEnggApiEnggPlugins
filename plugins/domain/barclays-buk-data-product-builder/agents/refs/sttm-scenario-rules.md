---
description: "Axis-based generation rules for STTM row generation engine — covers FDP (Foundational) and CDP (Consolidated) data product detection with specific generation rules per data product type."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-28
---

# Axis-Based Generation Rules

Per-axis rules for the STTM Generator row generation engine. Each axis contributes independently and additively to the final mapping rows.

## Axis 1 — Data Product Type

### FDP (Foundational Data Product)

**Purpose:** Clean and land source data from BASE/raw/source layer.

**Detection:** Database prefix `fdp_` or `shared_fdp_`, sources from raw/source systems, explicit declaration.

**Generation rules:**
- Source references point to raw/source layer tables
- No multi-FDP joins expected (single source system per FDP)
- Standard naming: `fdp_{country}_{domain}_db` or `shared_fdp_{country}_{domain}_db`

**Do NOT infer:** Whether a table belongs to FDP vs CDP — rely on database prefix or explicit declaration.

---

### CDP (Consolidated Data Product)

**Purpose:** Consolidate multiple FDPs together. Can be granular OR aggregated.

**Detection:** Database prefix `cdp_` or `shared_cdp_`, sources from FDP tables, explicit "consolidated" declaration.

**Generation rules:**
- Source references point to FDP layer tables
- Multi-source joins are common (SC9-SC10 rules likely to trigger)
- Structured compact newline-separated format with table aliases frequently required
- Standard naming: `cdp_{country}_{domain}_db` or `shared_cdp_{country}_{domain}_db`

**Do NOT infer:** Which FDP is the primary driver in a multi-source join — must be declared or determined from SQL.

---

### BDP (Business Data Product)

**Purpose:** Shape for specific business consumption. Can be granular OR aggregated.

**Detection:** Database prefix `bdp_` or `shared_bdp_`, sources from CDP tables, explicit "business" declaration.

**Generation rules:**
- Source references point to CDP layer tables
- Aggregation and window functions are common (SC11 rules likely to trigger)
- Business metric derivations expected
- Standard naming: `bdp_{country}_{domain}_db` or `shared_bdp_{country}_{domain}_db`

**Do NOT infer:** Business meaning of metric codes or segment logic — route to guided mode.

---

## Axis 2 — Table Type

### Transactional

**Audit columns:** dw_bus_dt + dw_lod_tmp

**What makes it unique:** Append-only event records. No SCD columns. Typically partitioned on business date.

**Auto-generate:** dw_lod_tmp + dw_bus_dt (from audit_columns.yaml under `transactional`).

**Extra inputs needed:** Partition column (usually dw_bus_dt), load type.

**Business logic style:** Simpler. "Direct mapping" dominant. CAST and COALESCE for edge cases.

**Validations triggered:** SC5 (no SCD columns present)

**Common errors:** Accidentally including SCD columns; missing partition column.

**Do NOT infer:** Whether a date column is partition key vs business attribute.

---

### NonTransactional_SCD1

**Audit columns:** dw_lod_tmp + dw_upd_lod_tmp

**What makes it unique:** Overwrite/upsert pattern. No effective dating. Latest state only.

**Auto-generate:** dw_lod_tmp + dw_upd_lod_tmp (from audit_columns.yaml under `scd1`).

**Extra inputs needed:** Merge key columns, update detection strategy.

**Business logic style:** Direct mappings with COALESCE for nullable fields. MERGE semantics implied.

**Validations triggered:** None specific (no SC rules unique to SCD1).

**Common errors:** Confusing SCD1 with SCD2; including effective dating columns.

**Do NOT infer:** Whether a table is SCD1 vs SCD2 — rely on explicit declaration or absence of SCD2 signals.

---

### NonTransactional_SCD2

**Audit columns:** eff_start_date + eff_end_date + active + dw_lod_tmp + dw_upd_lod_tmp

**What makes it unique:** Entity-state table with full history management. Has eff_start_date, eff_end_date, active columns.

**Auto-generate these columns:**
- eff_start_date: Derived from source modification date column (MUST have real source)
- eff_end_date: Source=(system)/(derived)/(derived), Logic=CAST('3499-12-31' AS DATE)
- active: Source=(derived)/(derived)/(derived), Logic=CASE WHEN eff_end_date = CAST('3499-12-31' AS DATE) THEN '1' ELSE '0' END
- dw_lod_tmp: Source=(system)/(system)/(system), Logic=current_timestamp()
- dw_upd_lod_tmp: Source=(system)/(system)/(system), Logic=current_timestamp()

**Extra inputs needed:** SCD config (high_end_date, source_mod_column), audit column spec, partition columns, CDC hash exclusion list.

**Business logic style:** Explicit expressions. Date casts follow: CAST(TO_DATE(CAST(x AS STRING), 'yyyyMMdd') AS DATE)

**Validations triggered:** SC1 (SCD2 columns present), SC2 (eff_end_date references high-end date), SC3 (active derives from eff_end_date), SC4 (eff_start_date has real source)

**Common errors:** Missing SCD source date column; wrong high-end date; active flag logic inverted.

**Do NOT infer:** Source column for eff_start_date; whether table is SCD1 or SCD2.

---

## Axis 3 — Crypto Aspect

### None

No crypto wrapping. Standard transformation logic applies without UDF wrapping.

---

### Tokenize

**Pattern:** `protect(source_col, 'DE')` — Source is clear-text; target stores tokenized via protect UDF.

**Business logic style:** `cloud_api_udf_{DE}_protect({source_col})`

**Validations triggered:** SC6 (valid DE), SC7 (UDF naming convention)

**Applied additively:** Wrap the column's base Business Logic with the protect UDF. The base logic (from Table Type axis) still determines the source mapping; crypto wraps the output.

**Do NOT infer:** DE names — NEVER guess. Must be explicitly provided.

---

### Detokenize

**Pattern:** `unprotect(source_col, 'DE')` — Source columns tokenized; target receives clear-text via unprotect UDF.

**Business logic style:** `cloud_api_udf_{DE}_unprotect({source_col})`

**Validations triggered:** SC6 (valid DE), SC7 (UDF naming convention)

**Applied additively:** Wrap the column's base Business Logic with the unprotect UDF.

**Do NOT infer:** DE names — NEVER guess. Must be explicitly provided.

---

### Both

**Pattern:** `protect(unprotect(...))` — Nested protect(unprotect(...)). Source DE differs from target DE.

**Business logic style:** `cloud_api_udf_{TARGET_DE}_protect(cloud_api_udf_{SOURCE_DE}_unprotect({source_col}))`

**Validations triggered:** SC6, SC7, SC8 (source DE != target DE)

**Applied additively:** Wrap with nested protect/unprotect.

**Common errors:** Nesting in wrong order; using same DE for both.

**Do NOT infer:** Either DE name. Level/rotation suffix encodes security policy.

---

## Cross-Axis Rules (SC9-SC11)

These rules are NOT tied to any single axis. They trigger based on detected evidence regardless of classification:

### SC9-SC10: Multi-Source

**Triggered by:** Multiple source tables detected in lineage OR LEFT JOIN patterns.

**Effect:** ALL multi-table columns MUST use structured compact newline-separated format with unique table aliases. Source references must be fully qualified. LEFT JOIN result columns must have Null Flag = Y.

**Common in:** CDP (consolidating multiple FDPs), BDP (joining multiple CDPs). Can also occur in FDP if source system has multiple related tables.

**Do NOT infer:** Which source is primary; join cardinality; whether NULL from LEFT JOIN is acceptable.

---

### SC11: Aggregation

**Triggered by:** Aggregate functions (SUM, COUNT, AVG, MAX, MIN) or window functions present in transformation logic.

**Effect:** PARTITION BY clause must be present and valid.

**Common in:** BDP (business metrics), CDP (consolidated summaries). Can occur in any data product type.

**Do NOT infer:** Business meaning of segment codes; grain; which lookup table.
