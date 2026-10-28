---
description: "Handling rules when multiple source systems load into a single target table — generates separate independent artefacts per source system using 3-way detection (user override, domain knowledge, mapping structure)."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-24
---

# Multiple Data Flow Scenarios

> **Load guard:** Read this ref ONLY when generating config (`/gen-config`), wrapper (`/gen-wrapper`), or any `/gen-*` command AND `source_system` field is detected in domain_knowledge_text OR `data_flow_detection.artifact_mode == "multiple_data_flow"` in session state.

When data from multiple source systems is loaded into a single target table, the plugin generates **separate independent artifacts per source system** — each executed as an independent job — unless the mapping explicitly specifies UNION.

---

## Detection Mechanism (3-Way)

The plugin determines whether to use multiple-data-flow configuration through a 3-way detection mechanism (highest priority wins):

1. **User override (Priority 0)** — User explicitly states the target has multiple data flows, either via `session/intent_overrides.json` (`data_flow_type: "multiple"`) or conversational instruction during interactive mode / after halting full-automation.
2. **Domain knowledge (Priority 1)** — `source_system: "SYSTEM_NAME"` explicitly declared in the domain knowledge file, or explicit statement about multiple source systems loading a single target.
3. **Mapping structure (Priority 2)** — The same `(target_table, target_column)` appears in multiple mapping rows, indicating multiple independent data flows populating the same target. The flows may originate from different source databases OR from the same source database — both indicate multiple data flows converging on one target.

**Key distinction**: Multiple data flow ≠ multi-table join. A join combines sources within ONE flow to produce ONE target row. Multiple data flows means the same target table/column is populated by SEPARATE independent pipelines.

---

## Source System Declaration

The `source_system` key in Additional Context (Column K) of the mapping Excel is the **authoritative signal** for multi-source-system flows. Format: `source_system:<label>` (e.g., `source_system:ilp`).

**CRITICAL**: Multiple source databases in the mapping (e.g., `e_cms_db` JOIN `ref_common_db`) do NOT indicate multiple source systems. This is a normal multi-table join. Multi-source-system is triggered ONLY by the explicit `source_system` key in Column K. Never infer from database count, duplicate target columns, or number of source tables.

**Single source_system is multi-flow:** A single `source_system` value (e.g., `source_system:trmph`) triggers multi-source-system artifact generation with `{source_system}/` folder nesting. This is NOT limited to cases with 2+ source systems. The purpose is to namespace artifacts by source_system for future extensibility and consistent folder structure.

## Artifact Mode Resolution

```
Step 1: Collect distinct non-null source_system_hint values from mapping_parsed.json
  (source_system_hint is a TOP-LEVEL field, not inside columns[])
  → If 0 non-null values: source_systems = [] (normal single-flow)
  → If 1+ non-null values: source_systems = [distinct values] (MULTI-FLOW — even if only 1 value)

Examples:
  source_system_hint = "trmph"         → source_systems = ["trmph"]                  → MULTI-FLOW
  source_system_hint = null            → source_systems = []                          → single-flow
  hints: "ilp", "reference_data"       → source_systems = ["ilp", "reference_data"]   → MULTI-FLOW

Step 2: Check for UNION exception
  → If source_systems non-empty AND Union Branch N: detected: artifact_mode = "combined"
  → Otherwise: artifact_mode = "default"
```

When `source_systems` is non-empty and `artifact_mode = "default"`: the single-flow template is instantiated N times, once per source_system, with source_system injected into naming/paths.

Session state fields (written by `/gen-config` STEP 0.5):
- `data_flow_detection.artifact_mode` = `"default"` | `"combined"`
- `data_flow_detection.source_systems` = `["ilp", "reference_data"]` or `[]`
- `data_flow_detection.source_system_table_mapping` = `{"ilp": ["e_cms_db.cmrcase"], ...}` or `null`
- `data_flow_detection.union_detected` = `true` | `false`

---

## Default Mode — `artifact_mode = "default"`

- Uses the **single-flow template** always (no separate multi-flow template)
- If `source_systems` is empty → one artifact set per target table (today's behavior)
- If `source_systems` is non-empty → N artifact sets (one per source_system), each with source_system in naming/paths
- Standard artifact structure per set: one config, one transform, one driver/wrapper

### Per-Source-System Artifacts (when source_systems is non-empty)

Each source_system gets **separate independent artifacts** executed as independent jobs.

### Architectural Principle

- Each per-source-system config uses **flat single-flow structure** (not nested by source_system)
- Since each config is scoped to one source_system, SourceReader/reader sees standard `source.{table_type}.{alias}` layout — no runtime multi-flow detection needed
- `process_name` includes source_system suffix for independent DateControl and scheduling
- Each source_system job runs independently — different schedules, failure isolation, independent business date advancement

### Platform-Specific Artifact Layout

| Aspect | Databricks | Glue |
|--------|-----------|------|
| Config | `{day}/{source_system}/{schema}_{table}/{schema}_{table}_config.yml` | `wrapper/{db}_{table}_{source_system}_config.json` |
| Transform | `{day}/{source_system}/{schema}_{table}/{schema}_{table}_transform.py` | `transforms/{db}_{table}_{source_system}_transform_{day}.py` |
| Driver/Wrapper | `{day}/{source_system}/{schema}_{table}/{schema}_{table}_driver.py` | `wrapper/{db}_{table}_{source_system}_wrapper.py` |
| DABs Job YAML | `jobs/.../{day}/{source_system}/{schema}_{table}_job.yml` | N/A |
| DTXOG | N/A | `dtxog/{db}_{table}_{source_system}_dtxog.json` |
| DAG | `dags/{tenancy}_{source_system}_{table}_dag.py` | `dags/{db}_{table}_{source_system}_dag.py` |
| Mesh | N/A | `mesh/{db}_{table}_{source_system}_mesh.json` |
| Tests | `test_transform_{schema}_{table}_{source_system}.py` | `test_wrapper_{db}_{table}_{source_system}.py` |
| process_name | `{schema}_{table}_{source_system}` | `{db}_{table}_{source_system}` |
| DateControl | One row per source_system (date_control_insert_utility) | One date_control.dat per source_system |
| Staging/Checkpoint | `/Volumes/{catalog}/{schema}/temp/{source_system}/{table}/...` | `data/stg/*/{source_system}/{db}/{table}` |

**Directory pre-creation**: Commands that generate artifacts at these paths MUST create the `{source_system}/` directories before writing files. For Databricks Notebooks, this means `generated/databricks/src/Notebooks/{day}/{source_system}/{schema}_{table}/`. For Databricks jobs, `generated/databricks/jobs/.../day{N}/{source_system}/`. Glue artifacts use filename suffixes — no additional directories needed.

### Glue S3 Paths (Independent Mode)

S3 paths include `{source_system}` prefix for artifact isolation:
- `wrapper-file` = `s3://bucket/apps/pkg/{{source_system}}/bin/wrapper.py`
- `package` = `s3://bucket/apps/pkg/{{source_system}}/{{database_name}}.whl`
- `package-cnfg` = `s3://bucket/apps/pkg/{{source_system}}/conf/{{database_name}}/{{table_name}}/config.json`
- `staging` = `data/stg/intermediate/{{source_system}}/{{database_name}}/{{table_name}}`
- `date_control` = `data/stg/date_control/{{source_system}}/{{database_name}}/{{table_name}}/date_control.dat`

### Databricks Staging/Checkpoint Paths (Independent Mode)

Volume paths include `{source_system}` for isolation:
- `checkpoint_path` = `/Volumes/{catalog}/{schema}/temp/{{source_system}}/{table}/checkpoint`
- `staging_path` = `/Volumes/{catalog}/{schema}/temp/{{source_system}}/{table}/staging`

---

## Combined Mode (UNION Exception) — `artifact_mode = "combined"`

When the mapping explicitly uses `Union Branch N:` structured format, a **single combined artifact set** is generated:

- All source tables appear in one config (flat single-flow layout)
- Transform contains `unionByName()` logic to merge rows from different sources
- One driver/wrapper, one DAG, one job per target table
- `process_name` does NOT include source_system (same as single-flow)
- Same output structure as `artifact_mode = "default"`

---

## Rolling Deletion

`rolling_deletion` config is per-table and source-system-independent — a single predicate applies to the target table regardless of how many source systems feed it. The `rolling_deletion` section lives at the top level of config, not nested under `source_system`.

In independent mode, each source_system's TargetWriter._rolling_delete() executes independently per job invocation. The deletion predicate is idempotent — multiple executions of the same predicate against the same target table are safe.

---

## Shared Infrastructure (Independent Mode)

These artifacts are shared across source systems and NOT duplicated:
- **Target table DDL** — one DDL per target table (the table is shared)
- **Audit table** — shared `{schema}.audit_log` (concurrent jobs write separate audit rows with distinct process_names; append-only, no contention)
- **Volume DDL** — Volumes are at schema level, not table level
- **Generic components** — source_reader.py, target_writer.py (Databricks) / reader.py, writer.py (Glue)

> **`%run` path depth**: Because multi-source-system transforms sit one directory deeper (`Notebooks/{day}/{source_system}/{schema}_{table}/`), the template variable `utilities_run_prefix` must be `../../..` (3 levels up to `Notebooks/`) vs `../..` (2 levels) in standard mode. The templates use `{{utilities_run_prefix}}/utilities/source_reader` and `target_writer`.

---

## How It Works

1. `/gen-config` STEP 0.5: Collect distinct `source_system_hint` values from `mapping_parsed.json` (extracted from Column K `source_system:<value>`)
2. If `source_systems` is non-empty AND no UNION detected:
   - `artifact_mode = "default"` — loop per source_system
   - For each source_system: generate separate config (single-flow template with source_system injected into process_name/paths), transform, driver/wrapper, DAG, deployment artifacts
   - Write `data_flow_detection` (including `source_system_table_mapping`) to session state for downstream commands
3. If `source_systems` is non-empty AND UNION detected: `artifact_mode = "combined"` — single artifact set with `unionByName()` logic
4. If `source_systems` is empty: `artifact_mode = "default"` — standard single-flow generation (one artifact set per target table)
5. Crypto selection orthogonal: whether source_systems is empty or non-empty, select crypto template variant if crypto flagged
6. **Single source_system (e.g., `["trmph"]`) follows the same multi-flow path as multiple source_systems.** The loop executes once, producing one artifact set under `{source_system}/` directories. This ensures consistent naming when a second source system is added later.
