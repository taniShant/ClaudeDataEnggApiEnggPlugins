---
name: generate-dq
description: Generate DQ rule catalogue and executable checks from profiling and/or approved rules.
agent: data-quality-engineer
user-invocable: true
---

## Purpose

Generate a Data Quality (DQ) rule catalogue and platform-executable checks from source profiling statistics, mapping DQ expectations, and/or an existing approved rules file. All generated rules are marked PROPOSED until reviewed and approved. Approved rules can be embedded directly into pipelines via `/generate-pipeline`.

## Usage

```
/generate-dq --platform <platform-name> [--profile <path>] [--mapping <path>] [--approved-rules <path>] [--output <path>] [--help]
```

At least one of `--profile`, `--mapping`, or `--approved-rules` must be supplied.

## Arguments

| Name | Required / Optional | Description |
|------|---------------------|-------------|
| `--platform` | Required | Target platform for executable check generation (e.g., `dbt`, `great-expectations`, `databricks`, `snowflake`, `soda`). Determines the format of generated executable files. |
| `--profile` | Required if `--mapping` and `--approved-rules` not supplied | Path to a profiling results artefact (output of `/profile`). Used to derive statistical threshold rules (null rate, distinct count bounds, range checks). |
| `--mapping` | Required if `--profile` and `--approved-rules` not supplied | Path to a mapping file containing DQ expectation annotations. Used to derive field-level integrity and referential rules. |
| `--approved-rules` | Required if `--profile` and `--mapping` not supplied | Path to an approved DQ rules file from a prior run. Used to generate updated executables without re-deriving rules. |
| `--output` | Optional | Directory path to write DQ artefacts. Defaults to `./output/dq/`. |
| `--help` | Optional | Print the input/output schema, loaded standards, and an example invocation, then exit with code `0`. |

## Example Invocations

**1. Generate DQ rules from a profiling artefact for Great Expectations:**
```
/generate-dq --profile ./output/profile/crm/profile.json --platform great-expectations --output ./output/dq/crm/
```

**2. Generate DQ rules from a mapping with DQ annotations for dbt tests:**
```
/generate-dq --mapping ./mappings/crm-to-cdp-approved.json --platform dbt --output ./output/dq/dbt/
```

**3. Regenerate executables from approved rules for a new platform target:**
```
/generate-dq --approved-rules ./output/dq/approved-rules.json --platform snowflake --output ./output/dq/snowflake/
```

## Output

On success the agent writes the following artefacts to the output directory:

- `dq-rule-catalogue.json` — Structured rule catalogue containing:
  - `rules[]` — Each rule with id, rule_type (`null_check|range_check|referential_integrity|format_check|uniqueness|custom`), source_field, condition, threshold, severity (`ERROR|WARNING|INFO`), derivation_source (`profile|mapping|approved_rules`), and `status` (`PROPOSED|APPROVED`).
  - `rules_by_table{}` — Rules grouped by table for easy review.
  - `loaded_standards[]` — DQ framework version and rule authoring standards consulted.
  - `unverified_assumptions[]` — Thresholds set from profiling that may not reflect business tolerance.
- `executable/` — Platform-specific executable check files. Each file begins with a `# STATUS: DRAFT` header. Contents vary by platform:
  - **dbt**: `tests/` directory with `.sql` generic and singular tests and `schema.yml` expectations.
  - **Great Expectations**: `expectation_suites/` JSON files.
  - **Soda**: `checks.yml` configuration.
  - **Snowflake**: SQL assertion procedures.
  - **Databricks**: Python DQ assertion notebooks.
- `dq-summary.md` — Human-readable summary of rule counts by type and severity, with flagged assumptions.

All generated rules carry `status: PROPOSED`. Promote rules to `status: APPROVED` via the approval workflow before supplying the file to `/generate-pipeline`.

Exit codes:

| Code | Meaning |
|------|---------|
| `0` | DQ rule catalogue and executables generated successfully. |
| `1` | None of `--profile`, `--mapping`, or `--approved-rules` supplied. |
| `2` | Profile file not found (when `--profile` supplied). |
| `3` | Mapping file not found (when `--mapping` supplied). |
| `4` | Approved rules file not found (when `--approved-rules` supplied). |
| `10` | Unsupported platform; see `--help` for supported platforms. |

## Related Commands

- `/profile` — Produce the profiling artefact that drives statistical threshold derivation.
- `/generate-pipeline` — Embed the approved DQ rules into a generated pipeline.
- `/validate` — Run the generated executable checks against a dataset and report results.
