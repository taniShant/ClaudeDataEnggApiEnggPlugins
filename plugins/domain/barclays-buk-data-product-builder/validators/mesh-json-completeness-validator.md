# Validator: mesh-json-completeness-validator

**Purpose**: Validate that the generated Mesh JSON is complete — all columns present, all environment S3 values filled, location pattern correct, Iceberg types valid.

**Severity**: DRAFT_UNVALIDATED if incomplete — list specific gaps.

**Platform**: Glue only

---

## Checks

### Check 1 — Column Completeness

All target columns from `mapping_parsed.json` must be present as `fields` in `aspects[].schema.fields`. Count must match.

### Check 2 — Environment S3 Values

`environmentProperties` must contain an entry with `"name": "s3_bucket"`. Its `properties` object must have all three keys: `dev`, `uat`, `prod` (NOT `prd` — mesh template uses `prod`). Each value must be non-null and non-empty.

### Check 3 — baselocation Pattern

`consumption.baselocation` must match:
```
s3://env:$s3_bucket/data/{target_database_base}/{target_table}
```
- Pattern check: starts with `s3://env:$s3_bucket/data/`
- Uses **base** database name (strip `_iceberg` suffix) — same as Check 4

### Check 4 — location Pattern

`consumption.location` must match:
```
s3://env:$s3_bucket/data/{target_database_base}/{target_table}/{partition_col}=${partition_col}
```
- Starts with `s3://env:$s3_bucket/data/`
- Uses base database name (strip `_iceberg` suffix from target_database)
- Contains at least one `{partition_col}=${partition_col}` partition suffix (e.g. `active=$active`)

`consumption.partitions` must be format: `'{partition_column}':'{partition_type}'` (e.g. `'active':'string'`)

### Check 5 — Iceberg Type Validation

All `dataType` values in schema fields must be Iceberg-native (regardless of `datasetType` value — `datasetType` is a free-text metadata string from tenancy skill, NOT a table format indicator):
- Valid: `string`, `date`, `timestamp`, `timestamptz`, `int`, `long`, `float`, `double`, `decimal(P,S)`, `boolean`, `binary`, `uuid`
- **Invalid (rejected)**: `bigint`, `smallint`, `varchar`, `nvarchar`, `char`, `datetime`

Note: `datasetType` is a free-text domain identifier (e.g. `foundation_uk_mortgage_db`, `buk_customer_foundational_data_product`) — NOT restricted to ICEBERG/HIVE. Do not use `datasetType` to determine Iceberg vs Hive validation rules. All tables in this pipeline use Iceberg format.

### Check 6 — No Session-State Fields in Mesh JSON

`data_product_type` and `target_account` must NOT appear in the mesh JSON (these are session state fields only).

### Check 7 — schemaType = FLATTENED

`aspects[].schema.schemaType` must equal `"FLATTENED"`.

### Check 8 — Column Count Alignment (WARNING)

Cross-reference column counts between three sources (excluding audit columns):

1. **Mapping count**: `mapping_parsed.json → columns[]` — count of unique `target_column_name` values (excluding audit columns)
2. **Mesh count**: `aspects[].schema.fields[]` — count of entries (excluding audit columns: `eff_start_date`, `eff_end_date`, `active`, `dw_lod_tmp`, `dw_upd_lod_tmp`, `dw_bus_dt`)
3. **Transform count**: Generated transform's final `.select()` — count of output columns (excluding audit columns)

**WARN** (do not block) if any pair of counts differs. Count mismatch is a signal — not always a defect (intermediate columns, TargetWriter-injected columns, etc.). The existing Check 1 (column completeness by name) remains the blocking check.

**Error format:**
```
⚠️ Column count mismatch:
   Mapping: {N} columns | Mesh JSON: {M} columns | Transform output: {T} columns
   Investigate: mapping may have dropped columns, or transform adds/removes columns not in mapping.
```

---

## Pass Condition

All 8 checks pass (Check 8 is WARNING-only — does not fail the validator).

## Fail Action

Mark `DRAFT_UNVALIDATED`. List specific violations:
```
❌ Mesh JSON completeness check failed:
   Check 2: uat s3_bucket is empty — provide via G3
   Check 4: location missing partition suffix — ensure partition_col from intent_identification.json
   Check 5: dataType 'bigint' is invalid for Iceberg — should be 'long'
```
