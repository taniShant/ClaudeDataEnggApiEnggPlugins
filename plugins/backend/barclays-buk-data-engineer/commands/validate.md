---
name: validate
description: Run deterministic validation checks on all produced artefacts and determine final status.
agent: validation-and-handoff-agent
user-invocable: true
---

## Purpose

Run a deterministic, schema-driven set of validation checks against a directory of produced artefacts. Validation covers schema conformance, completeness of required fields, cross-artefact consistency, and exit-code compliance across all `status.json` files present. Produces a structured validation result that can feed directly into `/handoff`.

## Usage

```
/validate --artefacts <path> \
            [--result-manifest <path>] \
            [--evidence-ledger <path>] \
            [--schemas <path>] \
            [--output <path>]
```

Pass `--help` to receive this document along with the full input and output JSON schemas and worked examples:

```
/validate --help
```

## Arguments

| Name | Required / Optional | Description |
|---|---|---|
| `--artefacts` | Required | Path to the directory containing all artefacts to validate. The agent will recursively discover all JSON, YAML, and Markdown files and classify them by artefact type. |
| `--result-manifest` | Optional | Path to a result manifest file (JSON or YAML) produced by a prior agent run. If supplied, the agent validates that the manifest is internally consistent and that all referenced artefact files exist on disk. |
| `--evidence-ledger` | Optional | Path to an evidence ledger file. If supplied, the agent checks that all evidence entries are well-formed, reference existing artefacts, and that no required evidence category is absent. |
| `--schemas` | Optional | Path to a directory of JSON Schema or YAML Schema files to use for artefact validation. Defaults to the plugin's bundled `schemas/` directory. The loaded schema version is stated in all output. |
| `--output` | Optional | Directory or file path for output artefacts. Defaults to `./output/validate/`. |

## Example Invocations

**1. Validate all artefacts in an output directory using bundled schemas:**

```
/validate \
  --artefacts ./output/pipeline-build/ \
  --output ./output/validation/
```

**2. Validate artefacts with an explicit result manifest and evidence ledger:**

```
/validate \
  --artefacts ./output/pipeline-build/ \
  --result-manifest ./output/pipeline-build/result-manifest.yaml \
  --evidence-ledger ./output/pipeline-build/evidence-ledger.yaml \
  --output ./output/validation/
```

**3. Validate against a custom schema directory:**

```
/validate \
  --artefacts ./output/pipeline-build/ \
  --schemas ./governance/schemas/v4/ \
  --output ./output/validation/
```

## Output

The command writes the following artefacts to the `--output` directory:

- `validation-result.yaml` — Structured validation result for each artefact file checked. Each entry includes: file path, artefact type, validation status (`pass`, `fail`, `skipped`), and a list of specific violations for failed items.
- `validation-summary.md` — Human-readable summary showing total counts of passed, failed and skipped artefacts, with a table of all failures and their severity.
- `cross-artefact-checks.yaml` — Results of cross-artefact consistency checks (e.g. lineage graph node IDs match those referenced in the metadata payload; all `status.json` exit codes are non-error).
- `unknowns.yaml` — Files that could not be classified into a known artefact type and were therefore skipped, listed with the reason. No file is silently ignored.
- `status.json` — Machine-readable exit status. Field `exit_code`: `0` = all checks passed, `1` = checks passed with warnings or skipped files, `2` = one or more failures. Field `failure_count` gives the exact number of failed checks.

**Loaded standards:** The agent states the plugin schema version and the validation rule set version at the top of `validation-result.yaml`.

**Exit codes:** `0` all artefacts valid, `1` valid with warnings or skips, `2` one or more artefacts invalid.

**Unknowns and assumptions:** Unrecognised artefact types are listed in `unknowns.yaml`. The agent does not apply partial schemas; if a schema cannot be matched, the file is listed as skipped, not silently passed.

## Related Commands

- `/handoff` — Consume the validation result to produce a complete handoff pack.
- `/review-mr` — Judgement-based MR review that complements this deterministic validation.
- `/generate-dq` — Generate data quality rules; produced rules can then be validated with this command.
