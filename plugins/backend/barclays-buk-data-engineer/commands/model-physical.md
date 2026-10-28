---
name: model-physical
description: Translate a logical model into platform-specific physical structures with DDL draft.
agent: physical-data-modeller
user-invocable: true
---

## Purpose

Translate a platform-independent logical data model into platform-specific physical structures — tables, columns, indexes, partitions, and constraints — and produce a draft DDL script. All generated DDL is marked DRAFT and must be reviewed before execution. Workload and volume hints drive physical design decisions such as partitioning strategy and index selection.

## Usage

```
/model-physical --logical-model <path> --platform <platform-name> [--platform-version <version>] [--workload <path>] [--volume <integer>] [--output <path>] [--help]
```

## Arguments

| Name | Required / Optional | Description |
|------|---------------------|-------------|
| `--logical-model` | Required | Path to the logical model artefact (output of `/model-logical`). |
| `--platform` | Required | Target platform name (e.g., `snowflake`, `bigquery`, `postgresql`, `databricks`, `oracle`, `sqlserver`). |
| `--platform-version` | Optional | Target platform version string (e.g., `7.x`, `14.2`). If omitted, the agent uses the latest approved version for the platform and records this as an assumption. |
| `--workload` | Optional | Path to a workload description file (query patterns, access frequencies, concurrency levels). Informs partitioning and clustering decisions. |
| `--volume` | Optional | Expected row count for the largest entity (integer). Used to guide partitioning thresholds. |
| `--output` | Optional | Directory path to write physical model artefacts. Defaults to `./output/model/physical/`. |
| `--help` | Optional | Print the input/output schema, loaded standards, and an example invocation, then exit with code `0`. |

## Example Invocations

**1. Translate a logical model to Snowflake DDL with no workload hints:**
```
/model-physical --logical-model ./output/model/logical/v1/logical-model.json --platform snowflake --output ./output/model/physical/snowflake/
```

**2. Translate with an explicit platform version and workload description:**
```
/model-physical --logical-model ./output/model/logical/final/logical-model.json --platform bigquery --platform-version "2.0" --workload ./workloads/cdp-query-patterns.yaml --output ./output/model/physical/bigquery/
```

**3. Translate with volume hint to influence partitioning:**
```
/model-physical --logical-model ./output/model/logical/v3/logical-model.json --platform databricks --volume 5000000000 --workload ./workloads/batch-etl.yaml --output ./output/model/physical/databricks/
```

## Output

On success the agent writes the following artefacts to the output directory:

- `physical-model.json` — The physical data model containing:
  - `tables[]` — Each table with column definitions (name, physical type, nullable, default), primary keys, foreign keys, indexes, partitioning, and clustering specifications.
  - `design_decisions[]` — Each partitioning or indexing decision with rationale and input evidence.
  - `platform` and `platform_version` used.
  - `loaded_standards[]` — Platform naming conventions and approved DDL patterns applied.
  - `unverified_assumptions[]` — Physical type mappings or design choices made without explicit workload evidence.
- `ddl-draft.sql` — Platform-specific DDL script. Every file begins with a `-- STATUS: DRAFT` header. Must not be executed without human review and approval.
- `physical-model-summary.md` — Human-readable summary of table structures and design rationale.

Exit codes:

| Code | Meaning |
|------|---------|
| `0` | Physical model and DDL draft produced successfully. |
| `1` | Logical model file not found or unreadable. |
| `2` | Unrecognised platform name; see `--help` for supported platforms. |
| `3` | Logical model contains entities with no attributes; inspect `unverified_assumptions[]`. |
| `4` | Workload file not found (when `--workload` supplied); physical design produced without workload context. |
| `10` | Platform version not found in approved version registry; latest approved version used and flagged as assumption. |

## Related Commands

- `/model-logical` — Produce the logical model that this command consumes.
- `/tech-choice` — Evaluate platform candidates before committing to a physical model target.
- `/db-change` — Assess a schema change against this physical model's DDL output.
