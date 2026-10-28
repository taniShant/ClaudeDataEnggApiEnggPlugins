# barclays-buk-reliability-engineer-status-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-reliability-engineer-status-v1` |
| Plugin name | `barclays-buk-reliability-engineer` |
| Component type | skill-model-invocable |
| Owner | BUK Retail CAPL |
| Action scope | read-only |
| Invocation mode | model-invocable |
| Installation / release | /plugin install barclays-buk-reliability-engineer@barclays-cio-buk |
| Native command | `/barclays-buk-reliability-engineer:status` |
| Skill name | `status` |

## Description

Reads .reliability/ state files and reports current observability phase, migration progress, and suggested next steps. Makes no changes to the repository.

## When to use

Use at any point in the reliability improvement workflow to check current phase, migration progress, and suggested next steps; read-only, makes no changes; works even if only a subset of .reliability/ state files are present

## Inputs

- None — reads `.reliability/` state files from the current repository automatically
- `CODE_PATH` (optional): absolute path to the service; defaults to current working directory

## Preconditions

- An active Claude Code session with read access to the service repository
- No `.reliability/` directory is required — if absent, the skill reports that no session has been started yet

## Expected outputs

- Console output only — no files created or modified
- Status report covering: current observability phase (Logging / Tracing / Metrics / Not started), phase status (not started / in progress / complete), migration progress table (per-migration title and implementation status), and suggested next steps

## Exclusions

- Does not run tests or execute verification steps
- Does not write or modify any files
- Does not cover performance or resilience target state — reports only the observability phase and migration sequence

## Verification

Confirm the output includes the current observability phase, a migration progress table, and at least one suggested next step. If `.reliability/` is absent, confirm the skill reports "No reliability state found" rather than an error.
