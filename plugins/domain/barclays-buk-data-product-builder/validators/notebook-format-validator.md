# Validator: notebook-format-validator

**Purpose**: Validate Databricks notebook format markers (header, cell separators), widget declarations, file extensions, and config.yml structural correctness for generated artefacts.

**Severity**: HALT — generation stops until format issues are resolved. Incorrect notebook format causes import failures in Databricks workspace; malformed config.yml causes runtime errors.

**Platform**: Databricks only

---

## Validation Logic

### Check 1 — Notebook Header

Every `.py` file under `generated/databricks/src/Notebooks/` must begin with the Databricks notebook source marker.

**Rules:**
1. First line of file must be exactly: `# Databricks notebook source`
2. No leading whitespace, no trailing content on the same line
3. This marker tells Databricks workspace to treat the `.py` file as a notebook (not a library)
4. BLOCK if header is missing, misspelled, or has extra characters

**Anti-patterns (BLOCK):**
```python
# ❌ Wrong — missing header entirely (file treated as Python module, not notebook)
import pyspark.sql.functions as F

# ❌ Wrong — typo in marker
# Databricks Notebook Source

# ❌ Wrong — extra content after marker
# Databricks notebook source — Driver for case_event_dbx

# ✅ Correct
# Databricks notebook source
```

### Check 2 — Cell Separators

Notebook files must use Databricks cell separator comments to delineate code cells.

**Rules:**
1. File must contain at least one cell separator: `# COMMAND ----------`
2. Exact format: `# COMMAND ----------` (space, then 10 hyphens)
3. Separators appear on their own line (no code on the same line)
4. BLOCK if no separators found (indicates file was not generated in notebook format)
5. Optional: `# DBTITLE 1,{title}` lines are valid but not required

**Anti-patterns (BLOCK):**
```python
# ❌ Wrong separator format
# COMMAND ---
# COMMAND ---------- some comment
# --- COMMAND ---

# ✅ Correct
# COMMAND ----------
```

### Check 3 — File Format

All generated notebook source files must use `.py` extension.

**Rules:**
1. Scan `generated/databricks/src/Notebooks/` recursively
2. Allowed extensions: `.py` (Python notebook source), `.yml` / `.yaml` (config files), `.sql` (DDL files)
3. BLOCK if `.dbc` files found (Databricks archive format — not suitable for version control)
4. BLOCK if `.ipynb` files found (Jupyter format — not compatible with Databricks source format)
5. Config files (`*_config.yml`) are co-located with notebooks and are valid

### Check 4 — Widget Restrictions (Driver Only)

Driver notebooks must use only the approved widget declarations. All other runtime parameters must come from config.yml.

**Allowed widgets (exhaustive whitelist):**
```python
dbutils.widgets.text("environment", "dev")
dbutils.widgets.text("business_date", "")
dbutils.widgets.text("log_level", "INFO")
```

**Rules:**
1. Scan driver `.py` files (files matching `*_driver.py` pattern)
2. Count all `dbutils.widgets.text(` occurrences
3. Each must match one of the three whitelisted widgets (parameter name match)
4. BLOCK if any additional `dbutils.widgets.text()` call is found
5. BLOCK if `dbutils.widgets.dropdown()` or `dbutils.widgets.multiselect()` is found
6. Transform files must NOT contain any `dbutils.widgets.*` calls

**Anti-patterns (BLOCK):**
```python
# ❌ Extra widget — parameter should come from config.yml
dbutils.widgets.text("source_database", "dev_db")
dbutils.widgets.text("target_schema", "cdp_uk_complaints_db")
dbutils.widgets.dropdown("load_type", "full", ["full", "incremental"])

# ❌ Widget in transform file — only allowed in driver
# (in transform.py)
dbutils.widgets.text("environment", "dev")
```

### Check 5 — Config.yml Structure

The pipeline config.yml file must contain all required sections with correct structure.

**Required top-level sections:**

| Section | Required Keys | Notes |
|---|---|---|
| `target` | `schema`, `table` | Catalog injected at runtime from environments |
| `pipeline` | `process_name`, `tenancy_name`, `data_product_type`, `table_type`, `load_type`, `process_frequency` | Metadata for the pipeline |
| `cdc` | `primary_key_cols` | May have additional keys; `primary_key_cols` is mandatory |
| `source` | At least one of `non_transactional` or `transactional` | Source table definitions |
| `filters` | `day0`, `day1` | Filter expressions per load type |
| `audit` | `table` | Audit log table reference |

**Multi-environment structure (if `environments` section present):**

1. Must contain keys: `dev`, `preprd`, `prd` (and optionally `uat` if tenancy supports it)
2. Each environment must have `target_catalog` (string)
3. Each environment must have `source_catalogs` (mapping with at minimum `source_catalog_1`)
4. Optional per-environment: `staging` with `checkpoint_path` and `staging_path`

**Source entry validation (multi-env config):**

1. Each source entry must have `catalog_key` referencing a valid key in `source_catalogs`
2. Source `table` field must be two-part: `{schema}.{table}` (NOT `{catalog}.{schema}.{table}`)
3. Source `table` field must NOT start with any catalog name from `environments`
4. Each source entry must have `columns` list (non-empty)

**load_type value validation:**

1. `pipeline.load_type` must be one of: `"Day0"`, `"BAU"` — these are the ONLY valid runtime values
2. BLOCK if `pipeline.load_type` is `"full_then_incremental"` — this is an intent-phase signal, not a runtime value
3. Cross-reference with folder placement: day0 config must have `load_type: "Day0"`, day1 config must have `load_type: "BAU"`

**Process name validation:**

1. `pipeline.process_name` must match pattern: `{target_schema}_{table_name}` (single-flow) or `{target_schema}_{table_name}_{source_system}` (multi-source-system)
2. Cross-reference with `target.schema` and `target.table` values in same config
3. `target.schema` must equal `mapping_parsed.json → target_database` (exact value from mapping Excel, no prefix/suffix stripping)
4. Example (single-flow): `target.schema: "cdp_uk_complaints_db"` + `target.table: "case_event_dbx"` → `process_name: "cdp_uk_complaints_db_case_event_dbx"`
5. Example (multi-source-system): same target + `source_system: "ilp"` → `process_name: "cdp_uk_complaints_db_case_event_dbx_ilp"`
6. When `data_flow_detection.source_systems` is non-empty, the `_{source_system}` suffix is REQUIRED for independent DateControl tracking

**Rules:**
1. Scan `*_config.yml` files in generated output
2. BLOCK if any required section is missing
3. BLOCK if `environments` section is incomplete (missing env keys)
4. BLOCK if source `catalog_key` references non-existent key in `source_catalogs`
5. BLOCK if source `table` contains catalog prefix (three-part name)
6. BLOCK if `process_name` doesn't match `{schema}_{table}` pattern (single-flow) or `{schema}_{table}_{source_system}` pattern (multi-source-system)

**Anti-patterns (BLOCK):**
```yaml
# ❌ Source table with catalog prefix (should be schema.table only)
source:
  non_transactional:
    my_source:
      catalog_key: "source_catalog_1"
      table: "DEV_BUK_BASE.e_resolve_db.cmrcase"  # Three-part — wrong!

# ❌ catalog_key references non-existent catalog
source:
  non_transactional:
    my_source:
      catalog_key: "source_catalog_99"  # Not defined in source_catalogs!
      table: "e_resolve_db.cmrcase"

# ❌ Missing required environment
environments:
  dev:
    target_catalog: "DEV_BUK_COMPLAINTS_CDP"
  prod:
    target_catalog: "PRD_BUK_COMPLAINTS_CDP"
  # Missing: preprd

# ❌ process_name doesn't match target schema+table
pipeline:
  process_name: "complaints_pipeline"  # Should be "cdp_uk_complaints_db_case_event_dbx"
target:
  schema: "cdp_uk_complaints_db"  # = mapping_parsed.json → target_database (exact)
  table: "case_event_dbx"

# ❌ load_type contains intent signal instead of runtime value
pipeline:
  load_type: "full_then_incremental"  # Should be "Day0" or "BAU"
```

---

## Pass Condition

All notebook files have `# Databricks notebook source` header and `# COMMAND ----------` separators. No `.dbc` or `.ipynb` files present. Driver widgets limited to the three-widget whitelist. Config.yml has all required sections, valid multi-env structure, correct source catalog references, and matching `process_name`.

## Fail Action

HALT. Output:
```
❌ Notebook format validation failed:

  [CHECK 1] Missing notebook header:
    File: {filename}
    Line 1 contains: "{actual_first_line}"
    Fix: First line must be exactly: # Databricks notebook source

  [CHECK 2] Missing cell separators:
    File: {filename}
    Found: 0 separators (expected ≥1)
    Fix: Add # COMMAND ---------- between logical code cells

  [CHECK 3] Invalid file format:
    File: {filename}
    Extension: .{ext}
    Fix: Convert to .py format (Databricks notebook source)

  [CHECK 4] Unauthorized widget:
    File: {filename}, Line {n}
    Widget: dbutils.widgets.text("{param_name}", "{default}")
    Fix: Remove widget. Move parameter to config.yml under pipeline section.

  [CHECK 5] Config.yml structural error:
    File: {filename}
    Issue: {description}
    Fix: {remediation}
```
