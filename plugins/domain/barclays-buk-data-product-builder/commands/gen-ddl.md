---
description: Generate Iceberg DDL and table creation utility — Databricks platform only
disable-model-invocation: false
---

# /gen-ddl

Generate Databricks-compliant Iceberg table DDL **atomically paired with driver per target table**. DDL is embedded into the `table_creation_utility.py` notebook for execution. No standalone `.sql` files are generated. **Databricks only** — refused for Glue.

## CRITICAL: Per-Target-Table Output with Atomic Pairs

This command generates **ONE DDL FILE PER TARGET TABLE** (atomic with driver) — NOT a single DDL with all tables.

### Atomic Pair Concept

**DDL and driver are always generated together**:
- Both exist or both are missing — never one without the other
- Ensures schema consistency between table definition and driver logic
- If generation fails for one, both are rolled back

### Output Format

**Output** — DDL embedded in table_creation_utility.py:
```
generated/databricks/src/Notebooks/utilities/{target_schema}_table_creation_utility.py
```

**DDL → table_creation_utility flow:**
```
iceberg_ddl.template.sql (per-table template)
        │
        ▼ render with target columns/types
        │
rendered DDL string
        │
        ▼ convert to f-string entry
        │
f"""
CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.{table_name} (
  ... columns from mapping document ...
)
USING iceberg
PARTITIONED BY ({partition_col})
"""
        │
        ▼ inject into table_creation_utility ddl_statements list
        │
table_creation_utility.py
  ddl_statements = [
    f"""CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.case_event_dbx (...)""",
    f"""CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.date_control (...)""",
    f"""CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.audit_log (...)""",
  ]
```

**Multi-table accumulation:** All target table DDLs are accumulated into a single `table_creation_utility.py`.

Create directory `generated/databricks/src/Notebooks/utilities/` if it does not exist.

## Usage

```
/gen-ddl
```

## Prerequisites

- Platform = Databricks (refuse if Glue)
- `session/mapping_parsed.json` exists
- `session/intent_identification.json` exists

## STEP 0 — Logging Initialization

Apply `conventions` skill logging pattern, component="de-gen-ddl".

## STEP 0.1 — Chain Checkpoint Loading

Apply `commands/refs/chain-checkpoint-pattern.md`. Checkpoint key: `post_transform`. Additional read: `session/mapping_parsed.json` for column_mappings (needed for DDL column definitions and types).

## STEP 0.5 — Read Templates (BLOCKING — do not skip)

Before generating any DDL file, the agent MUST read templates from disk:

- `${CLAUDE_PLUGIN_ROOT}/templates/databricks/iceberg_ddl.template.sql`
- `${CLAUDE_PLUGIN_ROOT}/templates/databricks/utilities/table_creation_utility.template.py`

**Rules:**
- The template is the **authoritative source of structure** (CREATE TABLE syntax, USING clause, PARTITION BY layout).
- If the template and prose conflict, **the template wins**.
- Generation = template read + placeholder substitution. Nothing more.

---

## Behaviour

### STEP 1 — Platform Check

If platform = Glue: REFUSE with:
> "Iceberg DDL generation is Databricks only. For AWS Glue, table creation is handled via Mesh JSON through the EDP team pipeline."

### STEP 2 — Resolve Unity Catalog Name

Catalog name resolution (in priority order):
1. From `domain_knowledge_text` — Unity Catalog section
2. From user G5 answer
3. Placeholder: `{{target_catalog}}`

### STEP 3 — Build Column Definitions

For each column in `mapping_parsed.json`:
- Map datatype to Spark SQL types (char/varchar → STRING, bigint → BIGINT, etc.)
- `Target Column Null Flag = false` → `NOT NULL` constraint
- Add `COMMENT '{target_column_description}'` per column

### STEP 4 — Build DDL

Render `iceberg_ddl.template.sql` with target columns and types. Convert rendered SQL to a Python f-string entry using `{CATALOG}.{SCHEMA}` variables (resolved at runtime from job parameters).

### STEP 5 — Build table_creation_utility.py

**If `generated/databricks/src/Notebooks/utilities/{target_schema}_table_creation_utility.py` already exists:**
- Read the existing notebook
- Append the new target table DDL entry into the `ddl_statements` list (before `date_control` and `audit_log` entries)
- Do NOT duplicate DDLs for tables that already exist in the list

**If it does not exist:**
- Render from `table_creation_utility.template.py` template
- Inject rendered DDL into `{{generated_ddl_list}}` slot

Always ensure `date_control` and `audit_log` DDLs are present as the final entries.

**NOTE:** A single `table_creation_utility.py` accumulates DDLs for ALL target tables. One execution of this utility notebook creates multiple tables in Databricks. When a new target table is added to the data product, its DDL is appended to the existing notebook — no separate utility per table.

### STEP 5.1 — Build date_control_insert_utility.py

**If `generated/databricks/src/Notebooks/utilities/{target_schema}_date_control_insert_utility.py` already exists:**
- Read the existing notebook
- Append the new target table process entry into the `processes` list
- Do NOT duplicate entries for tables that already exist in the list

**If it does not exist:**
- Render from `date_control_insert_utility.template.py` template
- Inject process entries into `{{generated_process_list}}` slot

Each process entry contains: `tenancy_name`, `process_name`, `data_product_type`, `process_frequency`.

**NOTE:** A single `date_control_insert_utility.py` accumulates process entries for ALL target tables. One execution seeds date control for all tables. When a new target table is added, its process entry is appended to the existing notebook.

### Multi-Source-System Awareness (DateControl)

Read `session_state.data_flow_detection`:

- **`source_systems` is non-empty**: The `{schema}_date_control_insert_utility.py` generates N process entries (one per source_system):
  ```python
  {"process_name": "{schema}_{table}_{source_system_1}", "tenancy_name": "...", ...},
  {"process_name": "{schema}_{table}_{source_system_2}", "tenancy_name": "...", ...},
  ```
  This enables each source_system job to track its own business date independently.
  - Target table DDL: unchanged (one DDL per target table — the table is shared across all source_system jobs)
  - Audit table DDL: unchanged (shared `{schema}.audit_log`)
  - Volume DDL: unchanged (Volumes are at schema level)
- **`"combined"` or `source_systems` is empty**: Unchanged (one process entry per target table).

### STEP 6 — Validate

Run `iceberg-ddl-validator`:
- `CREATE TABLE IF NOT EXISTS` present
- Three-part `catalog.schema.table` format
- `USING iceberg` present
- Column count matches mapping Excel
- Partition column declared in column list
- `active` column is STRING type (not INT)
- No `DROP`, `TRUNCATE`, or `ALTER TABLE`


### STEP 7 — Write

Files:
- `generated/databricks/src/Notebooks/utilities/{target_schema}_table_creation_utility.py` (all tables accumulated)

## Placeholder Resolution

| Placeholder | Type | Source | Resolution |
|---|---|---|---|
| `{{target_catalog}}` | Non-blocking | Domain knowledge or user | Unity Catalog name |
| `{{target_schema}}` | Non-blocking | Domain knowledge or mapping | Schema name |

## Output Files

- `generated/databricks/src/Notebooks/utilities/{target_schema}_table_creation_utility.py`
- `generated/databricks/src/Notebooks/utilities/{target_schema}_date_control_insert_utility.py`
- `session/audit_log.jsonl` (new entry)
- `session/placeholders.json` (updated)

## Failure Modes

- Platform = Glue → REFUSE
- Non-blocking placeholder unresolved → Continue; mark DRAFT_UNVALIDATED

---

## Multi-Table Batching

Each DDL uses `{target_schema}_{table}` naming. All target table DDLs accumulate into one `table_creation_utility.py`.

### Session State Updates

After generation: `table_status[table_name].ddl_generated = true`
