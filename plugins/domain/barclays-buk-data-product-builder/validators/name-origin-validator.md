# Validator: name-origin-validator

**Purpose**: Validate that all table names, column names, and transformation expressions in generated artefacts trace back to the mapping document. Prevents invented/hallucinated names from reaching production code.

**Severity**: HALT (target name violations) / WARNING (source name mismatches).

**Platform**: Glue + Databricks

**Triggered**: After any generation command (`/gen-transform`, `/gen-wrapper`, `/gen-mesh`, `/gen-driver`, `/gen-ddl`).

---

## Part A — Target Table Name Validation

### Allowed Set (Closed)

Extract from `session/mapping_parsed.json`:
- All unique `(target_database, target_table)` pairs

### Validation Logic

1. Read `session/mapping_parsed.json` → collect unique `target_database` and `target_table` values
2. Scan all files in `generated/` for table name references:
   - Python files: class names containing table name, string literals with table names
   - JSON files: values in `"database"`, `"tablename"`, `"table"` fields
   - SQL files: `CREATE TABLE`, `INSERT INTO`, `FROM` references
3. For each referenced table name, check membership in the closed set
4. Ignore audit/framework references: `date_control`, `audit_log` (these are infrastructure tables)

### Pass Condition (Part A)

All target table references in generated artefacts match entries in `mapping_parsed.json`.

### Fail Action (Part A)

HALT:
```
❌ Invented target table name detected!
Generated file: {filename}
Table referenced: {invented_name}
Allowed target tables (from mapping): {list_from_mapping}

This table does not exist in the mapping document.
Fix: Remove the invented reference or correct the mapping Excel.
```

---

## Part B — Target Column Name Validation

### Allowed Set (Closed)

Extract from `session/mapping_parsed.json`:
- Per target table: all `target_column_name` values from column_mappings

Augment with known audit/framework columns (template-defined):
- `dw_lod_tmp`, `dw_upd_lod_tmp`
- `eff_start_date`, `eff_end_date`
- `active`
- `dw_bus_dt`

### Validation Logic

1. Read `session/mapping_parsed.json` → for each target table, collect all `target_column_name` values
2. Merge audit/framework columns into allowed set
3. Scan generated transform files for target column references:
   - `.withColumn("{col_name}", ...)` patterns
   - `.alias("{col_name}")` patterns
   - `F.col("{col_name}")` when in target context (after transformation, before write)
   - `.select(...)` column lists
4. For each referenced target column, check membership in (mapping columns ∪ audit columns)

### Pass Condition (Part B)

All target column references trace to mapping_parsed.json or known audit columns.

### Fail Action (Part B)

HALT:
```
❌ Invented target column name detected!
Generated file: {filename}
Target table: {target_table}
Column referenced: {invented_column}
Allowed columns (from mapping + audit): {allowed_list}

This column does not exist in the mapping document.
Fix: Remove the invented column or update the mapping Excel.
```

---

## Part B.1 — Source Column Name Validation

### Authority Rule

**Mapping Excel is authoritative for source column names in generated code.** Generated code MUST always use column names from `mapping_parsed.json` `source_references[].column`.

### Allowed Set

Extract from:
1. `session/mapping_parsed.json` → `source_column_name` per source table (PRIMARY — authoritative)

### Validation Logic

1. Collect all source column names from mapping (authoritative set)
2. Scan generated transform files for source column references:
   - `F.col("{src_col}")` in source DataFrame context
   - `df["{src_col}"]` patterns
   - Source columns in join conditions and filter expressions
3. For each referenced source column:
   - If NOT in mapping → **HALT** (invented column — not traceable to mapping)
   - If in mapping → **PASS**

### Pass Condition (Part B.1)

All source column references trace to mapping_parsed.json.

### Fail Action (Part B.1 — Invented Column)

HALT:
```
❌ Invented source column detected!
Generated file: {filename}
Source table: {source_table}
Column referenced: {invented_column}
Allowed source columns (from mapping): {allowed_list}

This column does not exist in the mapping document.
Fix: Remove the invented column or update the mapping Excel.
```

---

## Part C — Source Table Name Validation

### Allowed Set

Extract from `session/mapping_parsed.json`:
- All unique source table entries from `source_references[]` (database + table)

### Validation Logic

1. Collect all source tables from mapping
2. Scan generated transform files for source table references:
   - `glue_read_table("{db}.{table}")` calls
   - `spark.table("{catalog}.{schema}.{table}")` calls
   - DataFrame alias assignments referencing source tables
3. For each referenced source table, check membership in allowed set

### Pass Condition (Part C)

All source table references trace to mapping.

### Fail Action (Part C)

HALT:
```
❌ Invented source table detected!
Generated file: {filename}
Source table referenced: {invented_source}
Allowed source tables (from mapping): {allowed_list}

This source table does not exist in the mapping document.
Fix: Remove the invented reference or correct the mapping Excel.
```

---

## Integration

This validator is invoked by the post-generate-validate hook (`hooks/post-generate-validate.hook.md`) after each generation command completes. Results are written to `session/validation_results.json`.

### Validation Result Entry

```json
{
  "validator": "name-origin-validator",
  "timestamp": "...",
  "status": "pass|halt|warning",
  "findings": [
    {
      "part": "A|B|B.1|C",
      "severity": "HALT|WARNING",
      "file": "generated/...",
      "name": "{invented_name}",
      "context": "{where_found}",
      "allowed_set_source": "mapping_parsed|audit_columns"
    }
  ]
}
```
