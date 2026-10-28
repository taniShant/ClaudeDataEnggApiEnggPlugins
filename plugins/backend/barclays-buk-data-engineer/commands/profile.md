---
name: profile
description: Profile an authorised data source and produce statistical aggregates without exposing sensitive values.
agent: source-profiler
user-invocable: true
---

## Purpose

Profile an authorised data source and produce statistical aggregates (row counts, null rates, distinct counts, min/max ranges, pattern frequencies) without exposing sensitive or PII values in any output artefact. The resulting profile drives mapping confidence scoring, DQ rule generation, and physical modelling decisions.

## Usage

```
/profile --source <connection-ref|schema-path> --tables <table-names|"*"> [--mode <metadata_only|aggregate_query|sample_query>] [--max-sample <integer>] [--output <path>] [--help]
```

## Arguments

| Name | Required / Optional | Description |
|------|---------------------|-------------|
| `--source` | Required | Connection reference (registered alias) or path to a schema definition file (`.json`, `.yaml`, `.sql`). |
| `--tables` | Required | Comma-separated list of table or view names to profile, or `*` to profile all tables visible to the connection. |
| `--mode` | Optional | Profiling depth. `metadata_only` — schema and constraint introspection only, no data queries. `aggregate_query` — executes COUNT/DISTINCT/NULL aggregates pushed down to the source (default). `sample_query` — executes aggregate queries on a random sample of `--max-sample` rows. |
| `--max-sample` | Optional | Maximum row count for the sample when `--mode sample_query` is used. Defaults to `10000`. |
| `--output` | Optional | Directory path to write profiling artefacts. Defaults to `./output/profile/`. |
| `--help` | Optional | Print the input/output schema, loaded standards, and an example invocation, then exit with code `0`. |

## Example Invocations

**1. Full aggregate profile of all tables on a registered source:**
```
/profile --source crm-db-prod --tables "*" --output ./output/profile/crm/
```

**2. Metadata-only profile of two specific tables (no data queries executed):**
```
/profile --source ./schemas/core-banking.yaml --tables "ACCOUNT,CUSTOMER" --mode metadata_only
```

**3. Sample-based profile with a custom sample size:**
```
/profile --source datalake-raw --tables "transactions_2024" --mode sample_query --max-sample 50000 --output ./output/profile/transactions/
```

## Output

On success the agent writes the following artefacts to the output directory:

- `profile.json` — Structured profile containing, per table and column:
  - Schema metadata (data type, nullable, primary key, foreign key references).
  - Aggregate statistics (row_count, null_count, null_rate, distinct_count, min, max, mean where applicable).
  - Pattern frequencies for string columns (top 5 regex patterns, no raw values).
  - `loaded_standards[]` — Classification and masking standards applied.
  - `unverified_assumptions[]` — Tables or columns that could not be profiled, with reasons.
- `profile-summary.md` — Human-readable summary with quality signal highlights.

No raw data values are written to any output file. All statistics are aggregates or masked patterns.

Exit codes:

| Code | Meaning |
|------|---------|
| `0` | All requested tables profiled successfully. |
| `1` | Source connection reference not found in registry. |
| `2` | One or more tables not found; partial profile written. |
| `3` | Source access denied; check authorisation and re-run. |
| `4` | `sample_query` mode requested but source does not support random sampling; re-run with `aggregate_query`. |
| `10` | Schema path not found or unreadable. |

## Related Commands

- `/map` — Use the profile output to augment or validate a source-to-target mapping.
- `/pii-discovery` — Run PII discovery against the profiled source using pattern frequencies.
- `/generate-dq` — Use the profile statistics to generate DQ rules and executable checks.
