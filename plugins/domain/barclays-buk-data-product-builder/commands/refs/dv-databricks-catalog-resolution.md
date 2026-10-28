# Step 0.5 — Resolve Databricks Catalogs

> **Condition:** Execute ONLY when `dv_session_state.engine == "databricks"`. Skip entirely for `athena`.

This step resolves Unity Catalog names so generated SQL embeds actual catalog identifiers (not `{{placeholder}}` tokens). DV SQL is standalone — there is no runtime driver to resolve placeholders.

**Skill required:** `barclays-buk-data-product-builder:databricks-tenancy`

## 0.5.1 — Parse `--env`

Parse `--env` argument. Default: `dev`. Validate against `["dev", "preprd", "prd", "uat"]`.

If invalid:
```
❌ --env must be one of: dev, preprd, prd, uat
```

## 0.5.2 — Resolve `source_catalog` (default per environment, overridable)

Default source catalogs from `databricks-tenancy` skill → **Source Catalogs** table:

| `--env` | Default `source_catalog` |
|---------|--------------------------|
| `dev` | `077382350852_buk_data_products` |
| `preprd` | `buk_data_product_central_catalog` |
| `prd` | `buk_data_product_central_catalog` |
| `uat` | `279373726337_buk_data_products_uat` |

Store as `default_source_catalog`. This MAY be overridden in Step 0.5.3 if the matched tenancy registry row has a different Source Catalog value (e.g., `TSC_CUSTOMER_FDP` uses `077382350852_glue_shared_catalog_sierra` instead of the default).

## 0.5.3 — Resolve `target_catalog` and `source_catalog` (tenancy registry + user fallback)

```
Priority 1 — DE session state (dependent mode only):
  IF input_mode == "de_pipeline":
    Read session/session_state.json (READ-ONLY — never modify)
    Check env_config.{env}.target_catalog OR dbx_config.{env}.target_catalog
    IF found and not null/"TBD" → USE for target_catalog
    Also check for source_catalog — if found, use; otherwise keep default_source_catalog from 0.5.2
    resolution_method = "de_session_state"
    Skip to Step 0.5.4 (no user prompt needed)

Priority 2 — Tenancy registry lookup:
  a) Read mapping_parsed.json → extract target_database (first table's value)
  b) Load databricks-tenancy skill → Tenancy Infrastructure Registry
  c) MATCHING ALGORITHM:
     - For each row in the registry:
       - Skip rows where "Target DB" column is "—", empty, or null
       - Compare: row["Target DB"].lower() == target_database.lower()
       - FIRST match wins — stop iterating
  d) IF matched:
     - Filter matched Feature Team's rows to the row where Environment == --env (case-insensitive)
     - Extract "Write/Target Catalog" value from that row:
       - IF value exists and is not "TBD"/"—"/null/empty → USE for target_catalog
       - ELSE → fall through to Priority 3 (user prompt)
     - Extract "Source Catalog" value from that row:
       - IF value exists and differs from default_source_catalog → USE (override default)
       - ELSE → keep default_source_catalog from 0.5.2
     - resolution_method = "tenancy_registry"
     - tenancy_name = matched Feature Team Name
  e) IF no match found:
     - Log: "ℹ️ No tenancy registry match for target_database '{value}'"
     - Fall through to Priority 3

Priority 3 — Ask user (MANDATORY if Priority 1 and 2 did not fully resolve):
  Ask catalog questions ONE AT A TIME — two sequential AskUserQuestion calls:

  Step A — Source catalog:
    AskUserQuestion: "Confirm or override the source catalog for the '{env}' environment"
    Pre-fill with default_source_catalog from Step 0.5.2
    (e.g., 077382350852_buk_data_products for dev)
    Options:
      - "{pre-filled value} (from environment lookup)" (Recommended)
      - Provide a different source catalog name
    Wait for user response before proceeding to Step B.

  Step B — Target catalog:
    AskUserQuestion: "What is the Unity Catalog write/target catalog name for the '{env}' environment?"
    No pre-fill — user must provide the value.
    Hint: "e.g., dev_buk_pafer_bdp, dev_buk_bbkyc_bdp"

  resolution_method = "user_provided"
```

## 0.5.4 — Resolve `target_schema`

`target_schema` = `target_database` from `mapping_parsed.json` (EXACT value, no transformation). This is identical to how `databricks-artefact-agent` handles `target.schema`.

## 0.5.5 — Store resolution in `dv_session_state.json`

Write to DV session state:
```json
{
  "target_environment": "{env}",
  "databricks_catalog_resolution": {
    "source_catalog": "<resolved>",
    "target_catalog": "<resolved>",
    "target_schema": "<resolved>",
    "resolution_method": "<method>",
    "tenancy_name": "<matched Feature Team Name or null>",
    "environment": "{env}"
  }
}
```

## 0.5.5b — CATALOG RESOLUTION GATE (MANDATORY)

Verify all required values are resolved non-null, non-empty strings before proceeding:

- IF `source_catalog` is null/empty → HALT: `❌ source_catalog could not be resolved for env '{env}'.`
- IF `target_catalog` is null/empty → HALT: `❌ target_catalog was not provided. Re-run /dv-generate --env {env} and provide the catalog name when prompted.`
- IF `target_schema` is null/empty → HALT: `❌ target_schema could not be determined. Verify mapping_parsed.json contains a valid target_database.`

Only proceed to Step 0.5.6 if ALL values are non-null, non-empty strings.

## 0.5.6 — Display resolution summary

```
ℹ️ Databricks catalog resolution (env: {env}):
   Source catalog: {value} (fixed)
   Target catalog: {value} ({resolution_method})
   Target schema:  {value} (mapping)
```
