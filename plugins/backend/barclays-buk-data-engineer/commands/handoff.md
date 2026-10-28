---
name: handoff
description: Produce a complete handoff pack with validation results, evidence and suggested next steps.
agent: validation-and-handoff-agent
user-invocable: true
---

## Purpose

Assemble a complete, self-contained handoff pack from a validated artefacts directory, a result manifest, and an evidence ledger. The pack is intended for consumption by downstream teams (platform engineering, operations, governance) and includes a structured summary, all evidence, outstanding unknowns, and explicit suggested next steps. This command does not re-run validation; it consumes prior validation output.

## Usage

```
/handoff --artefacts <path> \
            --result-manifest <path> \
            --evidence-ledger <path> \
           [--unknowns-register <path>] \
           [--output <path>]
```

Pass `--help` to receive this document along with the full input and output JSON schemas and worked examples:

```
/handoff --help
```

## Arguments

| Name | Required / Optional | Description |
|---|---|---|
| `--artefacts` | Required | Path to the directory containing all produced artefacts. The agent will include a manifest of all files found. |
| `--result-manifest` | Required | Path to the result manifest produced by the prior agent run(s) (JSON or YAML). Must include at minimum the list of produced artefacts, exit codes, and agent identifiers. |
| `--evidence-ledger` | Required | Path to the evidence ledger file (JSON or YAML) cataloguing all evidence items collected during the run. |
| `--unknowns-register` | Optional | Path to a consolidated unknowns register (JSON or YAML). If omitted, the agent will collect individual `unknowns.yaml` files from the `--artefacts` directory and merge them. |
| `--output` | Optional | Directory or file path for output artefacts. Defaults to `./output/handoff/`. |

## Example Invocations

**1. Produce a handoff pack from a completed pipeline build:**

```
/handoff \
  --artefacts ./output/pipeline-build/ \
  --result-manifest ./output/pipeline-build/result-manifest.yaml \
  --evidence-ledger ./output/pipeline-build/evidence-ledger.yaml \
  --output ./output/handoff/
```

**2. Produce a handoff pack with an explicit unknowns register:**

```
/handoff \
  --artefacts ./output/pipeline-build/ \
  --result-manifest ./output/pipeline-build/result-manifest.yaml \
  --evidence-ledger ./output/pipeline-build/evidence-ledger.yaml \
  --unknowns-register ./output/pipeline-build/unknowns-consolidated.yaml \
  --output ./output/handoff/
```

**3. Produce a handoff pack from a migration planning run:**

```
/handoff \
  --artefacts ./output/oracle-pg-migration/ \
  --result-manifest ./output/oracle-pg-migration/result-manifest.yaml \
  --evidence-ledger ./output/oracle-pg-migration/evidence-ledger.yaml \
  --output ./output/handoff/migration-pack/
```

## Output

The command writes the following artefacts to the `--output` directory:

- `handoff-pack.md` — Human-readable handoff document. Sections: executive summary, scope and objectives, artefacts inventory (with file paths and descriptions), validation outcome, outstanding unknowns and open questions, suggested next steps (ordered by priority), and contact/ownership information extracted from the result manifest.
- `handoff-pack.yaml` — Machine-readable equivalent of `handoff-pack.md` for tooling and portal ingestion.
- `artefacts-index.yaml` — Complete file-by-file inventory of all artefacts in the `--artefacts` directory, with type, size, producing agent, and validation status.
- `evidence-summary.yaml` — Condensed evidence ledger listing each evidence item, its category, the artefact it supports, and a pass/fail flag.
- `unknowns-consolidated.yaml` — Merged, deduplicated register of all unknowns and unverified assumptions from the run. Each entry includes source agent, description, risk level, and a suggested resolution action.
- `next-steps.yaml` — Prioritised list of suggested next steps, each with: description, responsible role, dependency on prior step, and suggested deadline category (immediate, short-term, long-term).
- `status.json` — Machine-readable exit status. Field `exit_code`: `0` = handoff pack produced with no outstanding blockers in the result manifest, `1` = handoff pack produced but result manifest contains warnings or open unknowns, `2` = handoff pack could not be produced.

**Loaded standards:** The agent states the Barclays Handoff Pack Standard version at the top of `handoff-pack.md`.

**Exit codes:** `0` success with clean validation, `1` success with outstanding items, `2` failure. Exit code reflects the state of the supplied result manifest, not the handoff production process itself.

**Unknowns and assumptions:** All unknowns from all input sources are consolidated and deduplicated in `unknowns-consolidated.yaml`. The handoff pack explicitly flags any open unknowns that require resolution before the work can be considered complete.

## Related Commands

- `/validate` — Run validation before invoking this command; `/handoff` consumes the output of `/validate`.
- `/review-mr` — MR review findings may be included as evidence items in the evidence ledger.
