---
name: performance
description: Analyse query plans and runtime metrics to produce evidence-based optimisation recommendations.
agent: performance-engineer
user-invocable: true
---

## Purpose

Analyse one or more query explain plans, optionally combined with runtime metrics and schema/index information, to produce prioritised, evidence-based optimisation recommendations. All recommendations cite the specific plan node or metric that motivated them. No optimisation is proposed without a supporting evidence reference.

## Usage

```
/performance --explain-plan <path> \
               [--metrics <path>] \
               [--schema <path>] \
               [--sla <description>] \
               [--output <path>]
```

Pass `--help` to receive this document along with the full input and output JSON schemas and worked examples:

```
/performance --help
```

## Arguments

| Name | Required / Optional | Description |
|---|---|---|
| `--explain-plan` | Required | Path to one or more explain plan output files. Accepted formats: plain text (`EXPLAIN` / `EXPLAIN ANALYZE` output), JSON (`EXPLAIN (FORMAT JSON)`), or XML. Multiple files may be comma-separated. Supported dialects: PostgreSQL, Snowflake, BigQuery, Spark, Oracle. |
| `--metrics` | Optional | Path to a runtime metrics file containing query execution history, resource utilisation, or APM data. Accepted formats: JSON, CSV, Prometheus exposition format. |
| `--schema` | Optional | Path to a file describing the current schema, including table definitions, column statistics, indexes and partitioning. Accepted formats: SQL DDL, JSON, YAML. Used to evaluate index coverage and partition pruning. |
| `--sla` | Optional | Free-text description of the latency or throughput requirement (e.g. `"p99 < 2s"`, `"daily batch must complete within 1h"`). Used to contextualise priority of recommendations. If omitted, recommendations are made without SLA context. |
| `--output` | Optional | Directory or file path for output artefacts. Defaults to `./output/performance/`. |

## Example Invocations

**1. Analyse a PostgreSQL explain plan with schema context and an SLA target:**

```
/performance \
  --explain-plan ./plans/query-001-explain.json \
  --schema ./schema/current-ddl.sql \
  --sla "p99 < 500ms" \
  --output ./output/performance/
```

**2. Analyse multiple Snowflake query plans with runtime metrics:**

```
/performance \
  --explain-plan ./plans/sf-plan-1.txt,./plans/sf-plan-2.txt \
  --metrics ./metrics/snowflake-query-history.csv \
  --output ./output/performance/
```

**3. Analyse a Spark explain plan with no additional context:**

```
/performance \
  --explain-plan ./plans/spark-physical-plan.txt
```

## Output

The command writes the following artefacts to the `--output` directory:

- `recommendations.yaml` — Prioritised list of optimisation recommendations. Each entry includes: description, estimated impact (high/medium/low), evidence reference (plan node ID or metric), required change type (index, rewrite, statistics, configuration), and implementation notes.
- `annotated-plan.md` — The original explain plan(s) annotated with inline commentary at identified bottleneck nodes.
- `evidence-summary.yaml` — Structured cross-reference of each recommendation to the specific plan cost, row estimate error, metric, or anti-pattern that motivated it.
- `unknowns.yaml` — Aspects that could not be assessed due to missing inputs (e.g. statistics not available, dialect not fully supported). No recommendation is made beyond what the evidence supports.
- `status.json` — Machine-readable exit status. Field `exit_code`: `0` = analysis complete, `1` = analysis complete with caveats, `2` = failure.

**Loaded standards:** The agent states the Barclays Query Optimisation Standard version it loaded at the top of `recommendations.yaml`.

**Exit codes:** `0` success, `1` success with caveats or missing inputs, `2` failure.

**Unknowns and assumptions:** Any aspect of the plan that could not be interpreted unambiguously is listed in `unknowns.yaml`. The agent does not guess at query semantics.

## Related Commands

- `/generate-pipeline` — Generate or regenerate pipeline code incorporating the recommended changes.
- `/db-change` — Generate DDL to apply index or schema changes recommended here.
- `/review-mr` — Review a merge request; performance analysis is one review dimension.
