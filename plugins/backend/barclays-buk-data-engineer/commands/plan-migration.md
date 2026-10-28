---
name: plan-migration
description: Plan a database migration covering same-engine upgrades, cross-engine moves, and schema changes.
agent: migration-planner
user-invocable: true
---

## Purpose

Produce a structured migration plan for a database change, whether that is a same-engine version upgrade, a cross-engine platform move, or a schema-level change. The plan covers risk assessment, compatibility analysis, sequenced migration steps, rollback procedures, and estimated downtime.

## Usage

```
/plan-migration --type <migration-type> \
                   --source-platform <name> \
                   --source-version <version> \
                   --target-platform <name> \
                   --target-version <version> \
                   --schema-inventory <path> \
                  [--constraints <path>] \
                  [--acceptable-downtime <duration>] \
                  [--output <path>]
```

Pass `--help` to receive this document along with the full input and output JSON schemas and worked examples:

```
/plan-migration --help
```

## Arguments

| Name | Required / Optional | Description |
|---|---|---|
| `--type` | Required | Migration category. Accepted values: `same_engine_upgrade`, `cross_engine`, `schema_change`. |
| `--source-platform` | Required | Name of the source database platform (e.g. `oracle`, `postgres`, `teradata`, `snowflake`). |
| `--source-version` | Required | Version string of the source platform (e.g. `19c`, `14.5`, `16.20`). |
| `--target-platform` | Required | Name of the target database platform. Must match an approved platform in the loaded standards. |
| `--target-version` | Required | Version string of the target platform. |
| `--schema-inventory` | Required | Path to a file listing all schemas, tables, views, sequences and stored procedures to be migrated. Accepted formats: JSON, YAML, CSV. |
| `--constraints` | Optional | Path to a file describing non-negotiable constraints such as regulatory holds, integration SLAs or data residency requirements. |
| `--acceptable-downtime` | Optional | Maximum allowable downtime expressed as a duration string (e.g. `4h`, `30m`, `0`). Defaults to `unspecified`; the plan will flag if any proposed step exceeds a reasonable threshold. |
| `--output` | Optional | Directory or file path to write the migration plan artefact. Defaults to `./output/plan-migration/`. |

## Example Invocations

**1. Plan an Oracle 19c to PostgreSQL 16 cross-engine migration:**

```
/plan-migration \
  --type cross_engine \
  --source-platform oracle \
  --source-version 19c \
  --target-platform postgres \
  --target-version 16.3 \
  --schema-inventory ./inventory/oracle-schemas.json \
  --constraints ./constraints/regulatory-holds.yaml \
  --acceptable-downtime 4h \
  --output ./output/oracle-pg-migration/
```

**2. Plan a same-engine Postgres minor version upgrade:**

```
/plan-migration \
  --type same_engine_upgrade \
  --source-platform postgres \
  --source-version 14.5 \
  --target-platform postgres \
  --target-version 16.3 \
  --schema-inventory ./inventory/pg-schemas.yaml \
  --acceptable-downtime 30m
```

**3. Plan a schema change only (no platform change), with zero downtime requirement:**

```
/plan-migration \
  --type schema_change \
  --source-platform snowflake \
  --source-version 8.10 \
  --target-platform snowflake \
  --target-version 8.10 \
  --schema-inventory ./inventory/sf-tables.csv \
  --acceptable-downtime 0 \
  --output ./output/sf-schema-change/
```

## Output

The command writes the following artefacts to the `--output` directory:

- `migration-plan.yaml` — Sequenced migration steps, each with owner, estimated duration, risk level and rollback action.
- `compatibility-report.md` — Feature-by-feature compatibility analysis between source and target platforms (data types, functions, index types, partitioning strategies, etc.).
- `risk-register.yaml` — Identified risks with likelihood, impact and proposed mitigations.
- `unknowns.yaml` — Explicit list of assumptions made and items that could not be verified from the supplied inputs.
- `status.json` — Machine-readable exit status. Field `exit_code`: `0` = plan produced with no blockers, `1` = plan produced with warnings, `2` = plan could not be produced (see `errors` field).

**Loaded standards:** The agent states which version of the Barclays Data Engineering Migration Standard it loaded at the top of `migration-plan.yaml`.

**Exit codes:** `0` success, `1` success with warnings, `2` failure. The `status.json` file is always written, even on failure.

**Unknowns and assumptions:** All unverified assumptions are listed explicitly in `unknowns.yaml`. The agent will not silently infer values for required fields.

## Related Commands

- `/db-change` — Generate the DDL and DML scripts to execute a planned change.
- `/tech-choice` — Evaluate and recommend platform choices before committing to a target.
- `/validate` — Run deterministic validation checks against the produced migration plan artefacts.
