# Validator: unity-catalog-validator

**Purpose**: Validate Unity Catalog naming conventions — fully-qualified table names, external location paths, and catalog name correctness for Databricks-generated artefacts.

**Severity**: HALT — generation stops until all UC naming issues are resolved. Incorrect catalog or table references cause runtime failures in Databricks.

**Platform**: Databricks only

---

## Validation Logic

### Check 1 — Fully-Qualified Table Names

All table references in generated artefacts must use three-part Unity Catalog format: `{catalog}.{schema}.{table}`.

**Scan locations:**
- DDL files: `CREATE TABLE IF NOT EXISTS {fqn}`
- config.yml: `target.catalog` + `target.schema` + `target.table` compose the FQN at runtime
- driver.py: `target_table` variable construction (e.g., `f"{config['target']['catalog']}.{config['target']['schema']}.{config['target']['table']}"`)
- transform.py: Any `spark.table()`, `spark.read.table()`, or `spark.sql("... FROM ...")` string references
- source entries in config.yml: `table` field must be two-part `{schema}.{table}` (catalog resolved via `catalog_key`)

**Rules:**
1. Any hardcoded table name in `.py` files must be three-part: `catalog.schema.table`
2. Exception: config.yml `source.*.table` uses two-part `schema.table` because catalog is resolved at runtime via `catalog_key` → `source_catalogs`
3. Pattern: `^\w[\w]*\.\w[\w]*\.\w[\w]*$` (three dot-separated identifiers)
4. BLOCK if any table reference is single-part (`table_name`) or two-part without catalog resolution (`schema.table` in code — not in config source entries)

**Anti-patterns (BLOCK):**
```python
# ❌ Missing catalog — will fail at runtime
spark.table("cdp_uk_complaints_db.case_event_dbx")

# ❌ Single-part — ambiguous
spark.sql("SELECT * FROM case_event_dbx")

# ✅ Correct — fully-qualified
spark.table(f"{config['target']['catalog']}.{config['target']['schema']}.{config['target']['table']}")
```

### Check 2 — External Location for Volume Paths

Any `/Volumes/` path in config.yml must reference a catalog that exists in the `environments` section.

**Scan locations:**
- config.yml: `environments.*.staging.checkpoint_path`
- config.yml: `environments.*.staging.staging_path`
- transform.py: Any string literal containing `/Volumes/`

**Rules:**
1. Extract the catalog segment from Volume path: `/Volumes/{CATALOG}/{schema}/{volume_name}/...`
2. The `{CATALOG}` must match the `target_catalog` of the corresponding environment
3. Volume paths must not use hardcoded environment prefixes across all environments (each env must have its own path)
4. BLOCK if Volume path references a catalog not present in any environment's `target_catalog` or `source_catalogs`

**Anti-patterns (BLOCK):**
```yaml
# ❌ Hardcoded DEV catalog in prod environment
prod:
  target_catalog: "PRD_BUK_COMPLAINTS_CDP"
  staging:
    checkpoint_path: "/Volumes/DEV_BUK_COMPLAINTS_CDP/..."  # Wrong catalog!
```

### Check 3 — Catalog Name Correctness

Catalog names must follow the BUK naming pattern and be consistent with the tenancy and data product type.

**Rules:**
1. Pattern: `{ENV_PREFIX}_{TENANCY}_{DP_TYPE}` where:
   - `ENV_PREFIX` ∈ {`DEV`, `PREPRD`, `PRD`}
   - `TENANCY` matches `session_state.tenancy_name` (uppercase, with `BUK_` prefix)
   - `DP_TYPE` matches `session_state.data_product_type` (uppercase: `FDP`, `CDP`, `BDP`)
2. Cross-reference `config.yml → environments.*.target_catalog` against session state
3. Source catalogs follow similar pattern but may reference different tenancies (e.g., `BUK_BASE_GLUE_CATALOG`, `BUK_REFERENCE_CATALOG`)
4. BLOCK if target catalog doesn't match the expected pattern for the tenancy/DP combination
5. Environment prefixes must be consistent: `dev` env → `DEV_*`, `preprd` → `PREPRD_*`, `prd` → `PRD_*`, `uat` → `UAT_*`

**Anti-patterns (BLOCK):**
```yaml
# ❌ Wrong DP type in catalog name
# session_state says data_product_type = "CDP" but catalog says "FDP"
dev:
  target_catalog: "DEV_BUK_COMPLAINTS_FDP"  # Should be CDP!
```

---

## Pass Condition

All table references are fully-qualified (three-part) or use catalog resolution via `catalog_key`. Volume paths reference correct catalogs for their environment. Catalog names follow the `{ENV}_{TENANCY}_{DP}` pattern consistent with session state.

## Fail Action

HALT. Output:
```
❌ Unity Catalog validation failed:

  [CHECK 1] Non-qualified table reference:
    File: {filename}, Line {n}
    Found: "{two_part_reference}"
    Fix: Use fully-qualified format: {catalog}.{schema}.{table}

  [CHECK 2] Volume path references wrong catalog:
    File: config.yml, Environment: {env}
    Path: "{volume_path}"
    Expected catalog: "{expected_catalog}"
    Fix: Update Volume path to use the target_catalog for this environment

  [CHECK 3] Catalog name mismatch:
    Environment: {env}
    Found: "{found_catalog}"
    Expected pattern: {ENV_PREFIX}_BUK_{TENANCY}_{DP_TYPE}
    Fix: Correct the target_catalog to match tenancy "{tenancy}" and DP type "{dp_type}"
```
