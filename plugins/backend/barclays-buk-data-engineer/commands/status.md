---
name: status
description: Summarise a supplied prior result manifest with no hidden session dependency.
agent: data-engineer-worker
user-invocable: true
---

## Purpose

Read a result manifest produced by a prior `/run` or individual agent run and produce a human-readable and machine-readable status summary. This command has no hidden session state dependency; it operates entirely from the supplied file. Use it to get a quick overview of what ran, what succeeded or failed, and what outstanding actions remain.

## Usage

```
/status --result-manifest <path> \
           [--verbose]
```

Pass `--help` to receive this document along with the full input and output JSON schemas and worked examples:

```
/status --help
```

## Arguments

| Name | Required / Optional | Description |
|---|---|---|
| `--result-manifest` | Required | Path to a result manifest file (JSON or YAML) produced by a prior `/run` invocation or by any individual specialist agent command. The manifest must contain at minimum: a list of tasks or artefacts, per-task exit codes, and the output directory reference. |
| `--verbose` | Optional | When set to `true`, the summary includes the full per-task artefact inventory, all loaded standard versions, and the full unknowns list. When `false` (default), only the task status table, exit code counts, and outstanding action items are shown. Accepts boolean values: `true` / `false`. Defaults to `false`. |

## Example Invocations

**1. Quick status summary of a prior run:**

```
/status \
  --result-manifest ./output/fraud-pipeline/result-manifest.yaml
```

**2. Verbose summary showing full details:**

```
/status \
  --result-manifest ./output/fraud-pipeline/result-manifest.yaml \
  --verbose true
```

**3. Status check on a migration planning result manifest:**

```
/status \
  --result-manifest ./output/migrations/oracle-pg/result-manifest.yaml \
  --verbose false
```

## Output

The command writes to stdout and optionally to file. No output directory is written unless the manifest specifies one.

**Standard output (default):**

- Task status table — One row per task: task type, exit code, output directory, and a one-line status description.
- Exit code counts — Total tasks, succeeded (exit `0`), warned (exit `1`), failed (exit `2`).
- Outstanding action items — Bulleted list of tasks with exit code `1` or `2`, with the top-level failure or warning reason from each task's `status.json`.
- Open unknowns count — Number of unresolved unknowns in the manifest, with a pointer to the `unknowns-consolidated.yaml` file if present.

**Verbose output (when `--verbose true`):**

All of the above, plus:

- Full per-task artefact inventory with file paths and descriptions.
- All loaded standard versions across all tasks.
- Full unknowns list with descriptions and risk levels.
- Evidence ledger summary (categories present, count of items, any missing required categories).

**`status.json`** — Written alongside stdout if the manifest's output directory is writable. Field `exit_code`: `0` = manifest read successfully and all tasks in the manifest exited `0`, `1` = manifest read successfully and one or more tasks exited `1`, `2` = manifest could not be read or one or more tasks exited `2`. This exit code reflects the state described by the manifest, not the status command itself.

**Loaded standards:** The agent states which version of the result manifest schema it used to parse the file. If the manifest does not declare a schema version, that fact is noted explicitly.

**Exit codes:** `0` manifest parsed and all tasks succeeded, `1` manifest parsed with warnings in one or more tasks, `2` manifest could not be parsed or contains failed tasks.

**Unknowns and assumptions:** If the manifest is missing expected fields, those are noted explicitly in stdout rather than silently defaulted. The command will not invent values for absent fields.

## Related Commands

- `/run` — Produces the result manifest consumed by this command.
- `/validate` — Run additional deterministic validation checks against the artefacts referenced in the manifest.
