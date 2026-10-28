---
name: lineage-impact
description: Build a data lineage graph and calculate the blast radius of a proposed change.
agent: lineage-impact-analyst
user-invocable: true
---

## Purpose

Build a data lineage graph from one or more source inputs (code repository, mapping files, or metadata catalogue entries) and calculate the blast radius — the set of downstream assets affected — for a proposed change. At least one of `--repository`, `--mappings`, or `--metadata-sources` must be provided.

## Usage

```
/lineage-impact [--repository <path>] \
                   [--mappings <path>] \
                   [--metadata-sources <bdp|alation|...>] \
                   [--change-scope <description>] \
                   [--output <path>]
```

Pass `--help` to receive this document along with the full input and output JSON schemas and worked examples:

```
/lineage-impact --help
```

**Constraint:** At least one of `--repository`, `--mappings`, or `--metadata-sources` is required. If none are supplied the command exits with code `2`.

## Arguments

| Name | Required / Optional | Description |
|---|---|---|
| `--repository` | At least one of these three required | Path to the root of a code repository containing SQL, dbt models, Spark jobs, or similar. The agent will crawl recognised file types. |
| `--mappings` | At least one of these three required | Path to one or more source-to-target mapping files (JSON, YAML, or CSV). Multiple files may be comma-separated. |
| `--metadata-sources` | At least one of these three required | Comma-separated list of metadata catalogue integrations to query. Supported values: `bdp`, `alation`. Credentials must be available in the environment. |
| `--change-scope` | Optional | Free-text description of the proposed change (e.g. "rename column customer_id to party_id in dim_customer"). Used to focus the blast-radius calculation on specific nodes. If omitted, the full lineage graph is produced without a focused impact assessment. |
| `--output` | Optional | Directory or file path for output artefacts. Defaults to `./output/lineage-impact/`. |

## Example Invocations

**1. Build lineage from a dbt repository and calculate blast radius for a column rename:**

```
/lineage-impact \
  --repository ./dbt-project/ \
  --change-scope "rename column customer_id to party_id in dim_customer" \
  --output ./output/lineage/
```

**2. Build lineage from mapping files and Alation metadata:**

```
/lineage-impact \
  --mappings ./mappings/etl-maps.yaml,./mappings/legacy-maps.csv \
  --metadata-sources alation \
  --output ./output/lineage/
```

**3. Full lineage from all sources with a proposed table drop scope:**

```
/lineage-impact \
  --repository ./pipelines/ \
  --mappings ./mappings/ \
  --metadata-sources bdp,alation \
  --change-scope "drop table stg_payments_v1" \
  --output ./output/lineage/
```

## Output

The command writes the following artefacts to the `--output` directory:

- `lineage-graph.json` — Full directed acyclic graph of lineage nodes and edges in a portable JSON format.
- `lineage-graph.dot` — Graphviz DOT representation for visual rendering.
- `blast-radius.yaml` — When `--change-scope` is supplied: ranked list of directly and transitively affected assets, with asset type, owner and estimated risk level.
- `coverage-report.yaml` — Summary of how much of the repository or mappings could be parsed, with any unresolved references listed explicitly.
- `unknowns.yaml` — Assets or references that could not be resolved from the supplied inputs. Unresolved items are never silently dropped.
- `status.json` — Machine-readable exit status. Field `exit_code`: `0` = complete, `1` = partial (some assets unresolved), `2` = failure.

**Loaded standards:** The agent states the lineage schema version it used at the top of `lineage-graph.json`.

**Exit codes:** `0` success, `1` success with unresolved references, `2` failure.

**Unknowns and assumptions:** All unresolved references are listed in `unknowns.yaml`. The agent will not fabricate lineage edges.

## Related Commands

- `/metadata` — Generate metadata and Alation payload drafts, optionally consuming the lineage graph produced here.
- `/review-mr` — Review a merge request; uses lineage impact as one review dimension.
- `/map` — Produce or validate source-to-target mapping documents.
