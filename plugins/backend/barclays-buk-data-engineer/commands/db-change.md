---
name: db-change
description: Assess a schema change for compatibility, blast radius and produce DDL drafts.
agent: database-change-adviser
user-invocable: true
---

## Purpose

Assess a proposed schema change for backward compatibility, forward compatibility, and blast radius — the set of consumers, pipelines, and downstream models affected by the change. Produces a structured impact report and DRAFT DDL for review. No DDL produced by this command should be executed without human review and explicit approval.

## Usage

```
/db-change --current-schema <path> --change <path> [--consumers <path>] [--environment <dev|test|staging|prod>] [--output <path>] [--help]
```

## Arguments

| Name | Required / Optional | Description |
|------|---------------------|-------------|
| `--current-schema` | Required | Path to the current DDL script or schema introspection output representing the live schema being changed. |
| `--change` | Required | Path to a change description document (natural language or structured YAML) or a proposed DDL file describing the intended schema change. |
| `--consumers` | Optional | Path to a consumer list file (JSON or YAML) mapping tables/views to the pipelines, reports, APIs, or data products that depend on them. If omitted, blast radius analysis will be partial and flagged. |
| `--environment` | Optional | Target environment for impact assessment. One of `dev`, `test`, `staging`, or `prod`. Defaults to `dev`. Production assessments trigger additional compatibility and rollback checks. |
| `--output` | Optional | Directory path to write impact and DDL artefacts. Defaults to `./output/db-change/`. |
| `--help` | Optional | Print the input/output schema, loaded standards, and an example invocation, then exit with code `0`. |

## Example Invocations

**1. Assess a proposed column addition on a dev schema with no consumer list:**
```
/db-change --current-schema ./schemas/current/core-banking-ddl.sql --change ./changes/add-account-status-column.yaml --output ./output/db-change/add-account-status/
```

**2. Assess a column rename against a staging schema with a full consumer list:**
```
/db-change --current-schema ./schemas/staging/transactions.sql --change ./changes/rename-txn-ref.yaml --consumers ./consumers/transactions-consumers.json --environment staging --output ./output/db-change/rename-txn-ref/
```

**3. Assess a table drop against the production schema:**
```
/db-change --current-schema ./introspection/prod-schema.json --change ./changes/drop-legacy-audit-table.sql --consumers ./consumers/all-consumers.json --environment prod --output ./output/db-change/drop-audit/
```

## Output

On success the agent writes the following artefacts to the output directory:

- `impact-report.json` — Structured impact assessment containing:
  - `change_summary` — Classification of the change type (`additive|non-breaking|breaking|destructive`).
  - `compatibility` — `backward_compatible` and `forward_compatible` booleans with rationale.
  - `blast_radius[]` — Each affected consumer with impact type (`schema_mismatch|type_mismatch|removed_column|renamed_column|constraint_change`), severity (`HIGH|MEDIUM|LOW`), and recommended remediation.
  - `rollback_plan` — Suggested rollback DDL or steps. Marked PROPOSED.
  - `migration_steps[]` — Ordered steps to apply the change safely (e.g., add column, backfill, drop old column).
  - `environment` assessed.
  - `loaded_standards[]` — Change management standards and versioning conventions applied.
  - `unverified_assumptions[]` — Consumers or dependencies not confirmed due to missing consumer list.
- `ddl-draft.sql` — Platform-specific DDL implementing the proposed change. Every file begins with a `-- STATUS: DRAFT` header. Must not be executed without review and approval.
- `impact-summary.md` — Human-readable summary of change classification, blast radius, and recommended next steps.

Exit codes:

| Code | Meaning |
|------|---------|
| `0` | Impact assessment completed; change classified as non-breaking or additive. |
| `1` | Impact assessment completed; one or more breaking or destructive changes detected — review `blast_radius[]`. |
| `2` | Current schema file not found. |
| `3` | Change file not found. |
| `4` | Consumer list file not found (when `--consumers` supplied); partial blast radius analysis performed. |
| `10` | Change description could not be parsed; supply as explicit DDL or structured YAML. |

## Related Commands

- `/plan-migration` — Produce a full migration plan from this impact report.
- `/model-physical` — Update the physical model after the change is approved.
- `/review-mr` — Submit the DDL draft for merge request review.
