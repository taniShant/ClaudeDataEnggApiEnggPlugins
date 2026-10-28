---
name: generate-pipeline
description: Generate ETL/ELT pipeline code from an approved mapping.
agent: pipeline-generator
user-invocable: true
---

## Purpose

Generate ETL/ELT pipeline code from an approved source-to-target mapping and a physical data model. All generated code is marked DRAFT and must pass peer review before deployment. The agent supports batch, micro-batch, and streaming execution patterns and can embed approved DQ rule checks directly into the generated pipeline.

## Usage

```
/generate-pipeline --mapping <path> --physical-model <path> --platform <platform-name> [--pattern <batch|micro-batch|streaming>] [--dq-rules <path>] [--output <path>] [--help]
```

## Arguments

| Name | Required / Optional | Description |
|------|---------------------|-------------|
| `--mapping` | Required | Path to an approved mapping file (output of `/map` with `status: APPROVED`). The agent will reject mappings with `status: PROPOSED`. |
| `--physical-model` | Required | Path to the physical model artefact (output of `/model-physical`) for the target platform. |
| `--platform` | Required | Target execution platform (e.g., `databricks`, `dbt`, `apache-spark`, `snowflake-tasks`, `glue`). Must match the platform in the physical model. |
| `--pattern` | Optional | Execution pattern. `batch` — scheduled full or incremental load (default). `micro-batch` — structured streaming with trigger intervals. `streaming` — continuous event-driven processing. |
| `--dq-rules` | Optional | Path to approved DQ rules file (output of `/generate-dq` with approved rules). DQ checks are embedded as pre/post-load assertions in the generated pipeline. |
| `--output` | Optional | Directory path to write generated pipeline artefacts. Defaults to `./output/pipeline/`. |
| `--help` | Optional | Print the input/output schema, loaded standards, and an example invocation, then exit with code `0`. |

## Example Invocations

**1. Generate a batch pipeline for Databricks with no DQ rules:**
```
/generate-pipeline --mapping ./mappings/crm-to-cdp-approved.json --physical-model ./output/model/physical/databricks/physical-model.json --platform databricks --output ./output/pipeline/databricks/
```

**2. Generate a dbt ELT pipeline with embedded DQ checks:**
```
/generate-pipeline --mapping ./mappings/crm-to-cdp-approved.json --physical-model ./output/model/physical/snowflake/physical-model.json --platform dbt --dq-rules ./output/dq/approved-rules.json --output ./output/pipeline/dbt/
```

**3. Generate a micro-batch pipeline for streaming ingestion:**
```
/generate-pipeline --mapping ./mappings/events-to-warehouse-approved.json --physical-model ./output/model/physical/databricks/physical-model.json --platform databricks --pattern micro-batch --output ./output/pipeline/streaming/
```

## Output

On success the agent writes the following artefacts to the output directory:

- `pipeline/` — Platform-specific pipeline code. Every generated file begins with a `-- STATUS: DRAFT` or `# STATUS: DRAFT` header comment. Contents vary by platform:
  - **dbt**: `models/`, `tests/`, `sources.yml`, `schema.yml`.
  - **Databricks / Spark**: PySpark notebooks or Python scripts with job definitions.
  - **Glue**: Python ETL scripts and job configuration JSON.
  - **Snowflake Tasks**: SQL task definitions and procedure stubs.
- `pipeline-manifest.json` — Metadata containing:
  - `generated_files[]` — List of all generated files with purpose and platform.
  - `mapping_version` — Version hash of the mapping consumed.
  - `dq_rules_embedded` — Boolean, plus list of embedded rule IDs.
  - `execution_pattern` used.
  - `loaded_standards[]` — Coding standards and pipeline patterns applied.
  - `unverified_assumptions[]` — Transformation logic inferred from mapping without explicit expression.
- `pipeline-summary.md` — Human-readable summary of the generated pipeline structure, lineage diagram (Mermaid), and review checklist.

Exit codes:

| Code | Meaning |
|------|---------|
| `0` | Pipeline code generated successfully. |
| `1` | Mapping file not found. |
| `2` | Mapping status is not APPROVED; pipeline generation refused. |
| `3` | Physical model file not found. |
| `4` | Platform in `--platform` argument does not match platform in physical model. |
| `5` | DQ rules file not found (when `--dq-rules` supplied); pipeline generated without DQ checks. |
| `10` | Unsupported platform/pattern combination; see `--help` for supported combinations. |

## Related Commands

- `/map` — Produce and approve the mapping that this command requires.
- `/model-physical` — Produce the physical model that this command requires.
- `/generate-dq` — Generate the DQ rules catalogue to embed in the pipeline.
