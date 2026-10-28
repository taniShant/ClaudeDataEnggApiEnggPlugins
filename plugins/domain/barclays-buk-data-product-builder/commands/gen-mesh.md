---
description: Generate Mesh JSON for table creation — Glue platform only
disable-model-invocation: false
---

# /gen-mesh

Generate the Mesh JSON file for **each target table**. **AWS Glue only** — refused for Databricks.

## ⚠️ CRITICAL: Per-Target-Table Output

This command generates **ONE MESH JSON FILE PER TARGET TABLE** — NOT a single generic mesh for all tables.

### Output Format

**Single-target output**:
```
fdp_uk_mortgage_db_account_wm_mesh.json
```

**Multi-target output** (3 target tables):
```
fdp_uk_mortgage_db_account_wm_mesh.json
fdp_uk_mortgage_db_rates_fees_mesh.json
fdp_uk_mortgage_db_mortgage_detail_mesh.json
```

Each mesh JSON is **target-table-specific** and contains:
- Target database and table name
- Target table column schema (with Iceberg type conversion)
- S3 storage locations per environment (dev/uat/prd)
- Owner and team information for this table
- Partition configuration for this table

**Multi-source-system output** (when `data_flow_detection.source_systems` is non-empty — one mesh per source_system):
```
fdp_uk_mortgage_db_account_wm_ilp_mesh.json
fdp_uk_mortgage_db_account_wm_reference_data_mesh.json
```

### Key Point
When you have 3 target tables in your mapping, you get 3 separate mesh JSON files — one per target. Each is independent and self-contained.

### Multi-Source-System Awareness

Read `session_state.data_flow_detection`:

- **`source_systems` is non-empty**: Generate N mesh configs (one per source_system):
  - Output: `generated/glue/mesh/{db}_{table}_{source_system}_mesh.json`
  - Each mesh config contains only the columns/metadata relevant to that source_system's pipeline
- **`"combined"` or `source_systems` is empty**: Unchanged (one mesh per target table).

## Usage

```
/gen-mesh
```

## Mapping Input Projection (Context Efficiency)

When passing `mapping_parsed.json` data to the `glue-mesh-agent`, include ONLY these fields per target table:
- `target_table`, `target_database`
- `columns[]` → `name`, `type`, `nullable`, `description` only
- `partition_key`
- `primary_keys`
- `table_description`

**Omit**: `transformation_logic`, `source_tables`, `source_columns`, `additional_context`, `column_mappings`

This reduces mapping input from ~6.5K tokens to ~2K tokens for the mesh agent.

## Prerequisites

- Platform = Glue (refuse if Databricks)
- Gate G3 fully resolved (all environment S3 locations provided)
- `session/intent_identification.json` exists
- `session/mapping_parsed.json` exists
- `session_state.domain_knowledge_text` may be present (checked if available)

## STEP 0.0 — Chain Mode Output Compression

Apply `commands/refs/chain-mode-compression.md` pattern. Compact return: `[{step}/{total}] ✓ /gen-mesh — {N} mesh JSON files generated | Checkpoint: post_generation updated`

## STEP 0 — Logging Initialization

Apply `conventions` skill logging pattern, component="de-gen-mesh".

## STEP 0.1 — Chain Checkpoint Loading

Apply `commands/refs/chain-checkpoint-pattern.md`. Checkpoint key: `post_intent`.

---

## STEP 0.5 — Read Templates (BLOCKING — do not skip)

Before generating any mesh JSON file, the agent MUST read the template from disk:

- `${CLAUDE_PLUGIN_ROOT}/templates/glue/mesh_json.template.json`

**Rules:**
- The template defines the **authoritative JSON skeleton** (key names, nesting, structural layout).
- Phase 3–8 rules in this doc populate field *values* — they do NOT define the structure.
- If the template and prose rules conflict on structure, **the template wins**.
- Generation = template read + value population into the template skeleton. Nothing more.
- Any key or nesting NOT present in the template must NOT appear in the output.

---

## Missing Information Resolution Priority

**For any mesh JSON field that is missing or unresolved**:

1. **Look up tenancy skill — Mesh JSON Metadata table** — Primary source for `btb_team`, `datasetType`, `datasetTypeSummary`. Match feature team name (derived from target database prefix, e.g. `fdp_uk_mortgage_db_iceberg` → `fdpmortgage`)
2. **Check domain knowledge MD** — If domain knowledge was provided (G0.5), search it for overrides or missing values
3. **Then ask user** — Only if steps 1-2 don't contain the value

**Fields resolved from tenancy skill**:
- `btb_team` → BTB Owner column (fallback: `sdw_buk_btb`)
- `datasetType` → datasetType column (fallback: derive as `foundation_uk_<domain>` / `consolidated_uk_<domain>` / `business_uk_<domain>`)
- `datasetTypeSummary` → datasetTypeSummary.name and .summary columns (optional — omit if `—` in table)
- RTB always `sdw_buk_rtb`. ITBS always `BSN0004626`.

**Fields resolved from domain knowledge**:
- Table summary/description (table overview)
- Any BTB team override (only if explicitly different from SKILL.md)

Do NOT prompt user for a value that exists in SKILL.md or domain knowledge.

## Behaviour — Multi-Table Batching (Phase B2)

**NEW**: This command now supports **multiple tables in parallel batches**.

### Multi-Table Execution Flow

```
Load target_tables from session state (array)
├─→ If length = 1: Single-table mode (backward compatible)
├─→ If length > 1: Multi-table batch mode
│    ├─→ Batch into groups of 3–5 tables
│    ├─→ Launch parallel glue-mesh-agent (Phase M) tasks (background)
│    ├─→ Wait for all tasks to complete
│    ├─→ Merge results into single session state
│    └─→ Verify all tables generated successfully
└─→ Write consolidated audit log entry
```

### Parallel Batching Configuration

```
Default batch_size = 3 (can be overridden in session_state)
Max concurrent tasks = min(16, cpu_cores - 2)
Wait strategy = barrier (wait for all in batch before next batch)
```

### Result Aggregation

```json
{
  "total_tables": 10,
  "batches": 4,
  "meshes_generated": 10,
  "batch_results": [
    {
      "batch_num": 1,
      "tables": ["customer_master", "account_detail", "transaction_history"],
      "status": "success",
      "time_ms": 2850
    }
  ],
  "total_time_ms": 9200,
  "per_table_avg_ms": 920,
  "speedup_vs_sequential": 4.3
}
```

---

### STEP 0 — Missing Information Resolution

Identify all mesh JSON fields that will be needed:
- `summary`, `description`
- `datasetType`, `datasetTypeSummary`
- `btb_team` (for owner.groups)
- S3 buckets (per env)

For each missing value:
1. Look up tenancy skill Mesh JSON Metadata table (primary source for btb_team, datasetType, datasetTypeSummary)
2. Check `session_state.domain_knowledge_text` (if available)
3. If not found → Add to placeholder list and prompt user in one grouped question

### STEP 1 — Platform Check

If `session_state.platform = "databricks"`: REFUSE with:
> "Mesh JSON is AWS Glue / EDP team pipeline only. For Databricks, table creation uses Iceberg DDL (`/gen-ddl`)."

### STEP 2 — G3 Completeness Check

**Pre-check — env_config completeness**: Verify `session_state.env_config` is non-null AND (`session_state.tenancy_resolution_method != "user_provided"` OR `session_state.env_config.questionnaire_turns_completed == 6`). If this check fails → HALT: `"env_config incomplete — infrastructure questionnaire may not have completed all questions. Re-run /parse-mapping to resolve."`

Check all three environments (dev/uat/prd) have `bucket` and `prefix` in `mesh_json_s3_locations` (auto-populated from `session_state.env_config` during /parse-mapping STEP 2.6). If any missing: HALT with "Re-run /parse-mapping to resolve per-environment infrastructure."

### STEP 3 — Build Column Schema & Audit Columns

For each column in `mapping_parsed.json`:
- Apply Iceberg type conversion from `${CLAUDE_PLUGIN_ROOT}/configs/plugin.config.json` → `iceberg_type_conversion`:
  - char/varchar/nvarchar → string
  - float/double → decimal(19,6)
  - bigint → long
  - smallint → int
  - numeric(P,S) / number(P,S) → decimal(P,S)
  - datetime → timestamp
  - bit → boolean
  - integer → int
- Set `nullable` from `target_column_nullable`
- Set `description` from `target_column_description`

After all columns: auto-append audit columns conditionally based on `table_type`:

> **Audit columns per table type:** See `${CLAUDE_PLUGIN_ROOT}/agents/refs/audit-columns-by-table-type.md`

### STEP 4 — Build S3 Location Values

From `intent_identification.json → partition_key_columns[0]` (primary partition):

```
baselocation: s3://env:$s3_bucket/data/{target_database_base}/{target_table}
location:     s3://env:$s3_bucket/data/{target_database_base}/{target_table}/{partition_col}=${{partition_col}}
```

Example: `active` partition → `s3://env:$s3_bucket/data/fdp_uk_mortgage_db/account_wm/active=$active`

For multi-partition (additional columns): append `/{col2}=${{col2}}` etc.

### STEP 5 — Build Owner & Labels

**Owner** (note: `itbs` is always hardcoded, not derived):
```json
{
  "itbs": "BSN0004626",
  "groups": [
    { "owner": "{{btb_team}}", "ownerGroup": "maintenance", "ownerType": "BTB" },
    { "owner": "{{btb_team}}", "ownerGroup": "origination", "ownerType": "BTB" },
    { "owner": "sdw_buk_rtb", "ownerGroup": "maintenance", "ownerType": "RTB" },
    { "owner": "sdw_buk_rtb", "ownerGroup": "origination", "ownerType": "RTB" }
  ]
}
```

**Labels**: Always include `businessdate`. Add `active` if partition column exists.

### STEP 6 — Build environmentProperties

Per env (dev/uat/prd): set `s3_bucket` from `mesh_json_s3_locations`.

Format (single object per name):
```json
{
  "name": "s3_bucket",
  "properties": {
    "dev": "{{s3_bucket_dev}}",
    "uat": "{{s3_bucket_uat}}",
    "prod": "{{s3_bucket_prd}}"
  }
}
```

> **Convention note:** Mesh JSON uses `"prod"` (not `"prd"`) as the production environment key. This is intentional and differs from other schemas/configs in the plugin that use `"prd"`. The mapping from the session state's `prd` bucket value to the mesh JSON's `prod` key happens in this step.

### STEP 7 — Build Metadata Fields

- `summary`: short title
- `description`: detailed description
- `datasetType`: dataset type name
- `datasetTypeSummary`: object with name, summary, description

### STEP 8 — Build storageMediumLinks & Aspects

**storageMediumLinks**: standard consumption HOT object (see STEP 8b for platformDefinition)

**aspects[0]**: data aspect with schema FLATTENED + storageMediumProperties

### STEP 8b — Determine platformDefinition (NEW)

For `storageMediumLinks[0].platformDefinition`:

**Default**: `"edp_cloud_datalake"` (Iceberg table in central catalog)

**Override to `"buk_cloud_datalake"` (Hive table in local catalog) ONLY when**:
1. Domain knowledge MD explicitly contains "hive" keyword (case-insensitive)
2. User explicitly said "hive" or "hive table" during gating (case-insensitive)

**Priority**:
1. Check `session_state.domain_knowledge_text` for "hive" keyword
2. Check user prompts/gates for "hive" keyword
3. Default to `"edp_cloud_datalake"` if neither found

**Why Iceberg by Default?**
- BUK CDAO strategic direction: Iceberg is the standard for all new data products
- Hive is legacy; must be explicitly declared
- Aligns with S3 bucket Pattern 1 (Iceberg central catalog)

See Phase M.8 of glue-mesh-agent.md for full detection algorithm.

### STEP 9 — Validate

Run `mesh-json-completeness-validator`:
- All columns present
- All env S3 values filled
- `baselocation` matches pattern `s3://env:$s3_bucket/data/`
- `location` contains partition col in `{partition_col}=${{partition_col}}` format (e.g. `active=$active`)
- All `dataType` values are Iceberg-native (no bigint/smallint)

### STEP 10 — Write & Confirm

Write file: `generated/glue/mesh/{target_database}_{target_table}_mesh.json` with 2-space indentation.

Create directory `generated/glue/mesh/` if it does not exist.

Confirm output:
```
Mesh JSON written to: generated/glue/mesh/{target_database}_{target_table}_mesh.json
Table: {database}.{table}
Fields: N (M audit columns auto-appended)
Partitions: [active | dw_bus_dt | dw_bus_dt, col2 | none]
Owner: {btb_team} (BTB) + sdw_buk_rtb (RTB)
```

## Output Files

- `generated/glue/mesh/{target_database}_{target_table}_mesh.json`
- `session/audit_log.jsonl` (new entry)

## Placeholder Resolution (Phase 2: Auto-Resolve)

**Note**: `{{itbs}}` is hardcoded in template as `BSN0004626` (pre-resolved, not Phase 2 placeholder)

**BEFORE Generation** (pre-flight check):
- Check template for any blocking placeholders (none in mesh; all auto-derived)

**AFTER Generation** (post-generation validation):
- Scan rendered file for `\{\{[a-z_]+\}\}` patterns
- Verify `itbs` is hardcoded as "BSN0004626"
- Verify all S3 bucket references are resolved
- Update `session/placeholders.json` with mesh generation status
- Mark artefact: ✅ VALIDATED (all values present and valid)

**Reference**: See `validators/placeholder-auto-resolver.helper.md` for detailed logic

## Validation Checklist

Before reporting success, verify:
- [ ] `name` = `{database}_{table}` (underscore separator, lowercase)
- [ ] `versionPolicy` = `NO_CONSTRAINT`, `versionManagement` = `CLIENT`
- [ ] `owner.itbs` = `BSN0004626` (hardcoded)
- [ ] `owner.groups` has exactly 4 entries (BTB maintenance + origination, RTB maintenance + origination)
- [ ] `businessdate` label present
- [ ] `storageMediumLinks[0].storageType` = `HOT`
- [ ] `aspects[0].schema.schemaType` = `FLATTENED`
- [ ] All audit columns present at end of fields per table_type (see `${CLAUDE_PLUGIN_ROOT}/agents/refs/audit-columns-by-table-type.md`)
- [ ] `environmentProperties.properties` has dev/uat/prod keys
- [ ] No placeholder tokens remain in JSON
- [ ] JSON parses (valid structure)

## Batching Execution (Phase B2)

### Algorithm: Batch Processing with Parallel Launch

```
Step A: Load Configuration
  session = load_session_state()
  target_tables = session.target_tables (array)
  batch_size = session.batch_size or 3 (default)
  
Step B: Determine Mode
  if len(target_tables) == 1:
    MODE = "single-table" (backward compatible)
  else:
    MODE = "batch-parallel"

Step C: Single-Table Mode (unchanged)
  if MODE == "single-table":
    Run Steps 0–10 as currently documented
    Write single mesh JSON
    Return

Step D: Batch-Parallel Mode (NEW)
  if MODE == "batch-parallel":
    batches = []
    for i in range(0, len(target_tables), batch_size):
      batch = target_tables[i:i+batch_size]
      batches.append(batch)
    
    all_results = []
    for batch_num, batch in enumerate(batches):
      tasks = []
      for table_index, table in enumerate(batch):
        task = Task(
          agent="glue-mesh-agent",
          prompt=f"Generate mesh JSON for table {table.name}",
          label=f"mesh_batch{batch_num}_table{table_index}",
          run_in_background=True
        )
        tasks.append(task)
      
      # Wait for all tasks in batch to complete (barrier)
      for task in tasks:
        result = task.wait()  # blocking
        all_results.append(result)
    
    # Merge results
    merged = merge_mesh_results(all_results)
    
    # Update session state
    session.target_tables.all_mesh_generated = True
    session.batch_results = merged.batch_results
    session.performance_metrics = {
      "total_time_ms": merged.total_time_ms,
      "per_table_avg_ms": merged.per_table_avg_ms,
      "speedup": merged.speedup_vs_sequential
    }
    save_session_state(session)
    
    # Log aggregated result
    log_audit_entry({
      "event": "mesh_generation_batch_complete",
      "tables": len(all_results),
      "time_ms": merged.total_time_ms,
      "status": "success"
    })
```

### Result Merging Logic

```
For each mesh_{{index}}.json:
  Load JSON
  Verify structure (all fields present)
  Collect metadata (table_name, fields_count, partition_col)
  
Aggregate:
  total_tables = count of successful meshes
  total_time = sum of all batch times
  per_table_avg = total_time / total_tables
  speedup = (expected_sequential_time) / (actual_parallel_time)
    where expected_sequential_time = total_tables * per_table_avg (if sequential)
```

### Per-Table Mesh Naming

When running in batch mode, each mesh JSON includes table index:

```
Batch 1:
  customer_master_0_mesh.json (index 0)
  account_detail_1_mesh.json (index 1)
  transaction_history_2_mesh.json (index 2)

Batch 2:
  contact_history_3_mesh.json (index 3)
  ...
```

**Reason**: Prevents filename collisions when tables are processed concurrently.

### Resumability (Future)

When resume logic is implemented:
```
if phase "gen_mesh" status = "in_progress":
  Check session.batch_results for per_table status
  Skip tables already completed in batches
  Re-run only failed tables
  Merge with existing results
```

---

## Failure Modes

- Platform = Databricks → REFUSE
- G3 incomplete → HALT with missing env list
- `dataType` validation failure → mark DRAFT_UNVALIDATED; list invalid types
- `owner.groups` mismatch → regenerate with correct structure
- Partition col not in fields → HALT, requires intent clarification
- **Batch mode: One table fails → SKIP and continue with others (fault-tolerant)**
- **Batch mode: Partial batch failure → Mark as DRAFT_UNVALIDATED; log which tables failed**
