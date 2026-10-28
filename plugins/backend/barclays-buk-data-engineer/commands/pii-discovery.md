---
name: pii-discovery
description: Classify columns for PII and PCI content using approved detection methods.
agent: pii-discovery-adviser
user-invocable: true
---

## Purpose

Classify columns in one or more tables for the presence of personally identifiable information (PII) and payment card industry (PCI) data using the approved detection methods specified. Results are produced as a classification report suitable for data governance review; no data is modified or masked by this command.

## Usage

```
/pii-discovery --source <schema-path-or-connection-ref> \
                  --tables <table,...|*> \
                 [--profile <path>] \
                 [--methods <method,...>] \
                 [--output <path>]
```

Pass `--help` to receive this document along with the full input and output JSON schemas and worked examples:

```
/pii-discovery --help
```

## Arguments

| Name | Required / Optional | Description |
|---|---|---|
| `--source` | Required | Path to a schema definition file (SQL DDL, JSON, YAML, dbt `manifest.json`) or a connection reference string (e.g. `snowflake://db/schema`). When a connection reference is supplied, the agent will introspect metadata only; it will not read row data unless `profiling` is listed in `--methods`. |
| `--tables` | Required | Comma-separated list of fully qualified table names to classify, or `"*"` to classify all tables reachable from `--source`. |
| `--profile` | Optional | Path to pre-existing column profiling results (JSON or CSV) from a prior profiling run. Providing this avoids re-profiling and is required when `profiling` is in `--methods` but no live connection is available. |
| `--methods` | Optional | Comma-separated list of detection methods to apply. Accepted values: `naming` (column name pattern matching), `profiling` (statistical profiling of sampled values), `metadata` (catalogue/tag lookup), `ml` (ML-based classifier). Default: `naming,profiling,metadata`. Methods are applied in the listed order and results are merged by majority vote. |
| `--output` | Optional | Directory or file path for output artefacts. Defaults to `./output/pii-discovery/`. |

## Example Invocations

**1. Classify all tables in a Snowflake schema using all four methods:**

```
/pii-discovery \
  --source snowflake://my-db/raw_schema \
  --tables "*" \
  --methods naming,profiling,metadata,ml \
  --output ./output/pii/
```

**2. Classify specific tables from a DDL file using naming and metadata only:**

```
/pii-discovery \
  --source ./schema/warehouse-ddl.sql \
  --tables "dim_customer,fact_payments,stg_addresses" \
  --methods naming,metadata \
  --output ./output/pii/
```

**3. Classify using pre-existing profiling results to avoid re-profiling:**

```
/pii-discovery \
  --source ./schema/physical-model.yaml \
  --tables "*" \
  --profile ./profiling/column-profiles-2024-q4.json \
  --methods naming,profiling,metadata \
  --output ./output/pii/
```

## Output

The command writes the following artefacts to the `--output` directory:

- `classification-report.yaml` — Per-column classification results. Each column entry includes: table, column name, inferred data type, PII classification (none, low, medium, high, definite), PCI flag, detection methods that fired, confidence score, and recommended handling action (none, mask, tokenise, encrypt, restrict).
- `classification-summary.md` — Human-readable summary table grouped by table, with counts by classification level and a list of definite/high-confidence PII columns for immediate review.
- `method-evidence.yaml` — Per-method, per-column breakdown of what triggered a classification (matched pattern, profiling statistic, metadata tag, or ML score). Provides the audit trail for each finding.
- `unclassified.yaml` — Columns that could not be assessed due to missing schema, profiling data, or unsupported data types. No column is silently omitted.
- `unknowns.yaml` — Assumptions made during classification (e.g. assumed character encoding, assumed locale for date patterns). Stated explicitly.
- `status.json` — Machine-readable exit status. Field `exit_code`: `0` = all tables classified, `1` = partial classification, `2` = failure.

**Loaded standards:** The agent states the Barclays Data Classification Standard version and the approved PII pattern library version at the top of `classification-report.yaml`.

**Exit codes:** `0` success, `1` partial (some columns or tables unclassified), `2` failure.

**Unknowns and assumptions:** All inference and assumptions are listed in `unknowns.yaml`. The agent will not assign a definite PII classification without at least one explicit evidence signal.

## Related Commands

- `/profile` — Run column profiling to produce the input for the `--profile` argument.
- `/map` — Produce or validate source-to-target mapping documents, optionally incorporating PII classification results.
- `/review-mr` — Review a merge request; PII handling is one review dimension.
