---
name: run
description: Convenience composition that routes a full input manifest through the appropriate agents.
agent: data-engineer-worker
user-invocable: true
---

## Purpose

Convenience front-door command that accepts a single input manifest describing the full work to be done, routes each declared task to the appropriate specialist agent, and collects all outputs into a unified result directory. This command is not required; every specialist agent can be invoked directly via its own command. Use `/run` when you want to execute multiple tasks from a single manifest file without invoking each command individually.

## Usage

```
/run --manifest <path> \
       [--output <path>] \
       [--dry-run]
```

Pass `--help` to receive this document along with the full input and output JSON schemas and worked examples:

```
/run --help
```

## Arguments

| Name | Required / Optional | Description |
|---|---|---|
| `--manifest` | Required | Path to an input manifest file (YAML or JSON) declaring the tasks to execute and their arguments. The manifest schema is described in `schemas/run-manifest-schema.json` within the plugin. Each task entry in the manifest maps directly to one specialist command and its arguments. |
| `--output` | Optional | Directory path for all output artefacts. Each task writes its output to a subdirectory named after the task type (e.g. `./output/plan-migration/`, `./output/validate/`). Defaults to `./output/`. |
| `--dry-run` | Optional | When set, the agent parses and validates the manifest, resolves all file references, and prints the execution plan (ordered task list with arguments) without executing any task. Accepts boolean values: `true` / `false`. Defaults to `false`. |

## Example Invocations

**1. Run a full manifest for a new pipeline delivery:**

```
/run \
  --manifest ./manifests/new-fraud-pipeline-manifest.yaml \
  --output ./output/fraud-pipeline/
```

**2. Dry run to preview what would be executed without side effects:**

```
/run \
  --manifest ./manifests/new-fraud-pipeline-manifest.yaml \
  --dry-run true
```

**3. Run a migration planning manifest with a custom output directory:**

```
/run \
  --manifest ./manifests/oracle-pg-migration-manifest.json \
  --output ./output/migrations/oracle-pg/
```

**Example manifest structure (YAML):**

```yaml
version: "1"
tasks:
  - type: plan-migration
    args:
      type: cross_engine
      source-platform: oracle
      source-version: 19c
      target-platform: postgres
      target-version: "16.3"
      schema-inventory: ./inventory/oracle-schemas.json
      acceptable-downtime: 4h

  - type: lineage-impact
    args:
      repository: ./dbt-project/
      change-scope: "rename column customer_id to party_id in dim_customer"

  - type: validate
    args:
      artefacts: "{{ output }}/plan-migration/"
```

## Output

The command writes the following artefacts to the `--output` directory:

- Per-task subdirectories — Each task produces its own artefacts in a named subdirectory, identical to what the specialist command would produce when invoked directly.
- `result-manifest.yaml` — Consolidated result manifest summarising all tasks executed, their exit codes, output directories, and any warnings or errors.
- `evidence-ledger.yaml` — Aggregated evidence ledger collecting evidence entries from all tasks.
- `execution-plan.yaml` — Always written, even on `--dry-run`. Lists the tasks in execution order with resolved arguments and estimated sequence dependencies.
- `unknowns-consolidated.yaml` — Merged unknowns register from all tasks.
- `status.json` — Machine-readable exit status. Field `exit_code`: `0` = all tasks succeeded, `1` = all tasks completed but one or more returned exit code `1`, `2` = one or more tasks returned exit code `2` or failed to start. Field `task_results` is an array of per-task exit codes.

**Loaded standards:** Each task states its own loaded standard version in its task-specific output. The `result-manifest.yaml` aggregates the standard versions across all tasks.

**Exit codes:** `0` all tasks succeeded, `1` all tasks ran with warnings, `2` one or more tasks failed. The `--dry-run` flag always exits `0` if the manifest is valid, `2` if the manifest fails schema validation.

**Unknowns and assumptions:** Each task records its own unknowns. `/run` consolidates all of them into `unknowns-consolidated.yaml` without modification. No task's unknowns are suppressed.

## Related Commands

- `/status` — Summarise a prior result manifest produced by this command.
- All other commands — Each specialist command that can appear as a task in the manifest; any of them can also be invoked directly without using `/run`.
