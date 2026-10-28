# barclays-buk-data-engineer-run-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-data-engineer-run-v1` |
| Plugin name | `barclays-buk-data-engineer` |
| Component type | skill-user-only |
| Owner | Barclays BUK |
| Action scope | externally-consequential |
| Invocation mode | user-only |
| Installation / release | /plugin install barclays-buk-data-engineer@barclays-cio-buk |
| Native command | `/barclays-buk-data-engineer:run` |
| Skill name | `run` |

## Description

Convenience composition that routes a full input manifest through the appropriate agents.

## When to use

Use when you need to execute multiple data-engineering tasks (e.g. plan-migration, lineage-impact, validate) from a single YAML or JSON manifest file rather than invoking each specialist command individually; this is a convenience orchestrator and is NOT required — every specialist agent can be called directly via its own command.

## Inputs

- `--manifest <path>` (required): Path to a YAML or JSON input manifest file conforming to `schemas/run-manifest-schema.json`, declaring an ordered list of tasks (each with a `type` and `args` block mapping to a specialist command)
- `--output <path>` (optional): Directory path for all output artefacts; defaults to `./output/`; each task writes to a subdirectory named after its type (e.g. `./output/plan-migration/`)
- `--dry-run` (optional, boolean): When `true`, parses and validates the manifest and prints the execution plan without executing any task; defaults to `false`
- `--help` (optional): Prints full usage documentation including input/output JSON schemas and worked examples

## Preconditions

- A valid input manifest file must exist at the path given to `--manifest`, conforming to the schema defined in `schemas/run-manifest-schema.json` (version `"1"`)
- All file references within task `args` (e.g. `schema-inventory`, `repository`, `artefacts`) must resolve to existing, accessible paths at execution time
- The `data-engineer-worker` agent and all specialist agents referenced by task types in the manifest (e.g. `plan-migration`, `lineage-impact`, `validate`) must be available in the plugin environment
- The output directory (default `./output/` or the path supplied via `--output`) must be writable
- Manifest task entries may use template expressions (e.g. `{{ output }}`) to reference earlier task outputs; the referenced tasks must appear earlier in the task list

## Expected outputs

- Per-task subdirectories under the output directory, each containing the same artefacts the specialist command would produce when invoked directly (e.g. `./output/plan-migration/`, `./output/validate/`)
- `result-manifest.yaml` — consolidated summary of all tasks executed, their exit codes, output directories, warnings/errors, and aggregated standard versions
- `evidence-ledger.yaml` — aggregated evidence entries collected from all tasks
- `execution-plan.yaml` — ordered task list with resolved arguments and estimated sequence dependencies (always written, including on `--dry-run`)
- `unknowns-consolidated.yaml` — merged unknowns register from all tasks, without suppression
- `status.json` — machine-readable exit status containing `exit_code` (0/1/2) and a `task_results` array of per-task exit codes

## Exclusions

- Does not replace direct invocation of specialist commands — each task type (e.g. `plan-migration`, `lineage-impact`, `validate`) can be called on its own without `/run`
- Does not suppress or filter unknowns or assumptions raised by individual tasks; they are passed through unmodified into `unknowns-consolidated.yaml`
- Does not define its own data-engineering logic; it only orchestrates and aggregates outputs from specialist agents
- Does not execute any tasks when `--dry-run true` is set — it only validates the manifest and emits the execution plan
- Does not provide post-run analysis of results; use `/status` to summarise a prior `result-manifest.yaml`

## Verification

Check `status.json` in the output directory: an `exit_code` of `0` confirms all tasks succeeded, while `1` indicates warnings and `2` indicates failures — inspect the `task_results` array for per-task detail. Review `result-manifest.yaml` for a human-readable summary of executed tasks, their exit codes, and output paths, and confirm that each per-task subdirectory contains the expected artefacts. For dry runs, verify that `execution-plan.yaml` lists the correct resolved task sequence and that the command exited with code `0`.
