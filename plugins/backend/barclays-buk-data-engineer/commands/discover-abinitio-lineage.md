---
name: discover-abinitio-lineage
description: Discover Ab Initio pipelines from any sandbox, extract attribute-level lineage, and optionally publish OpenLineage events to Marquez. Supports single-dataset and multi-job pipeline discovery modes.
agent: ab-initio-discovery-agent
user-invocable: true
---

## Purpose

Scan an Ab Initio sandbox, auto-discover its structure, parse DML/graph/XFR/PSET/DBC artifacts, walk TWS/RES schedule dependencies to identify source database tables and job orchestration, extract complete attribute-level end-to-end lineage, and produce mapping workbooks, HTML dashboards, and OpenLineage events.

Supports two modes:
1. **Single-dataset mode** (default) — Focuses on one target dataset/DML; produces 8-sheet attribute mapping workbook
2. **Pipeline mode** (`--pipeline`) — Discovers multiple interconnected jobs from scheduling definitions; produces 7-sheet pipeline workbook + HTML dashboard + lineage document

## Usage

### Single-Dataset Mode

```
/discover-abinitio-lineage \
  --sandbox <path> \
  --dataset <name> \
  --target-dml <path> \
  [--graph <graph_name>] \
  [--res <directory>] \
  [--job <job_name>] \
  [--dictionary <path>] \
  [--pub-dml <path>] \
  [--output <directory>] \
  [--namespace <namespace>] \
  [--html] \
  [--upload] \
  [--endpoint <url>]
```

### Pipeline Discovery Mode

```
/discover-abinitio-lineage \
  --pipeline \
  --sandbox <path> \
  --schedule <scheduling_file> \
  --jobs <job_code1,job_code2,...> \
  [--dictionary <path>] \
  [--output <directory>] \
  [--namespace <namespace>] \
  [--html] \
  [--upload] \
  [--endpoint <url>]
```

## Arguments

### Common Arguments

| Name | Required | Description |
|---|---|---|
| `--sandbox` | Yes | Path to Ab Initio sandbox root (directory containing graphs, DMLs, XFRs, PSETs) |
| `--output` | Optional | Output directory. Default: current directory |
| `--dictionary` | Optional | Path to data dictionary `.xlsx` for business definition enrichment |
| `--namespace` | Optional | OpenLineage namespace. Auto-generated if omitted |
| `--html` | Optional | Generate an HTML dashboard alongside the workbook |
| `--upload` | Optional | Publish validated events to Marquez. Without this flag, dry-run only |
| `--endpoint` | Optional | Marquez API URL. Default: `https://emh-open-lineage-dev.barcapint.com` |

### Single-Dataset Mode Arguments

| Name | Required | Description |
|---|---|---|
| `--dataset` | Yes | Target dataset name |
| `--target-dml` | Yes | Path to the target DML file defining the output schema |
| `--graph` | Optional | Graph `.mp` filename. Auto-discovered from sandbox if omitted |
| `--res` | Optional | Path to directory containing RES/TWS `.xlsm`/`.xlsx` schedule files |
| `--job` | Optional | TWS job name as starting point for RES dependency walk |
| `--pub-dml` | Optional | Path to published DML directory (source table DMLs). Auto-discovered if omitted |

### Pipeline Discovery Mode Arguments

| Name | Required | Description |
|---|---|---|
| `--pipeline` | Yes | Activates pipeline discovery mode |
| `--schedule` | Yes | Path to TWS scheduling definition file (text-format `dumps_*` or RES Excel directory) |
| `--jobs` | Yes | Comma-separated list of TWS job codes to discover |

## Example Invocations

**1. Full single-dataset analysis with RES and dictionary:**

```
/discover-abinitio-lineage \
  --sandbox /path/to/sandbox \
  --dataset my_target_dataset \
  --target-dml /path/to/target.dml \
  --graph my_graph.mp \
  --res /path/to/RES \
  --job ETLJOB001 \
  --dictionary /path/to/data_dictionary.xlsx \
  --output ./output
```

**2. Minimal single-dataset (sandbox + DML only):**

```
/discover-abinitio-lineage \
  --sandbox /path/to/sandbox \
  --dataset my_dataset \
  --target-dml /path/to/target.dml
```

**3. Pipeline discovery from TWS dumps file:**

```
/discover-abinitio-lineage \
  --pipeline \
  --sandbox /path/to/imp_bsl/imp_bsl_sbp_os \
  --schedule /path/to/dumps_BDH \
  --jobs PBXXXXXXXXXXXXX1,PBXXXXXXXXXXXXX2,PBXXXXXXXXXXXXX3,PBXXXXXXXXXXXXX4,PBXXXXXXXXXXXXX5,PBXXXXXXXXXXXXX7,PBXXXXXXXXXXXXXX8,PBXXXXXXXXXXXXXX9 \
  --html \
  --output ./output
```

**4. Pipeline discovery with Marquez publication:**

```
/discover-abinitio-lineage \
  --pipeline \
  --sandbox /path/to/sandbox \
  --schedule /path/to/dumps_BDH \
  --jobs JOB1,JOB2,JOB3 \
  --html \
  --upload \
  --namespace MY_PIPELINE_V1
```

**5. Single-dataset with HTML dashboard:**

```
/discover-abinitio-lineage \
  --sandbox /path/to/sandbox \
  --dataset my_dataset \
  --target-dml /path/to/target.dml \
  --html
```

## Output

### Single-Dataset Mode

| Artefact | Description |
|---|---|
| `<dataset>_End_To_End_Mapping.xlsx` | 8-sheet attribute-level mapping workbook |
| `<dataset>_openlineage_events.json` | OpenLineage RunEvents (START + COMPLETE per graph) |
| `<dataset>_field_source_map.json` | Intermediate field-to-source analysis (audit artifact) |
| `<dataset>_validation_report.json` | 12 validation checks with pass/fail status |
| `<dataset>_publication_report.json` | Publication status per event (only if --upload) |
| `<dataset>_Dashboard.html` | HTML dashboard (only if --html) |

### Pipeline Discovery Mode

| Artefact | Description |
|---|---|
| `<pipeline>_Pipeline_Workbook/` | 7 CSV sheets: Pipeline_Inventory, Source_Target_Mapping, Column_Level_Lineage, Transformation_Catalog, Dependency_Matrix, Data_Quality_Rules, Infrastructure |
| `<pipeline>_E2E_Lineage.md` | Comprehensive end-to-end lineage document (Markdown) |
| `<pipeline>_Pipeline_Dashboard.html` | Interactive HTML dashboard with flow diagrams, Gantt, dependency matrix, schemas (if --html) |
| `<pipeline>_openlineage_events.json` | OpenLineage RunEvents for all graphs in pipeline |
| `<pipeline>_validation_report.json` | Validation checks with pass/fail status |
| `<pipeline>_publication_report.json` | Publication status (only if --upload) |

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | Success — all critical validations pass, deliverables generated |
| 1 | Failure — critical validation failure, publication blocked |
| 2 | Error — invalid arguments or missing dependencies |

## Related Commands

- `/lineage-impact` — Build lineage from existing code/mappings and calculate blast radius.
- `/map` — Produce or validate source-to-target mapping documents.
