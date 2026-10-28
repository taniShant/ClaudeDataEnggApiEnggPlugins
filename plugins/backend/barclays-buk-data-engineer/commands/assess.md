---
name: assess
description: Assess a requirement document and extract structured FRs, NFRs, ambiguities and gaps.
agent: requirement-assessor
user-invocable: true
---

## Purpose

Assess a requirement document and extract structured functional requirements (FRs), non-functional requirements (NFRs), ambiguities and gaps. Produces a machine-readable assessment artefact that downstream commands such as `/map` and `/resolve-context` can consume directly.

## Usage

```
/assess --input <path> [--format <prose|jira|hld|mapping>] [--output <path>] [--help]
```

## Arguments

| Name | Required / Optional | Description |
|------|---------------------|-------------|
| `--input` | Required | Path to the requirement document to assess. Accepts `.md`, `.txt`, `.docx`, `.pdf`, `.json`, or `.yaml`. |
| `--format` | Optional | Input document format. One of `prose`, `jira`, `hld`, or `mapping`. If omitted the agent auto-detects from file extension and content heuristics. |
| `--output` | Optional | Directory path to write assessment artefacts. Defaults to `./output/assessment/`. |
| `--help` | Optional | Print the input/output schema, loaded standards, and an example invocation, then exit with code `0`. |

## Example Invocations

**1. Assess a prose requirements document with auto-detection:**
```
/assess --input ./docs/requirements/data-product-v1.md
```

**2. Assess a Jira export with an explicit output directory:**
```
/assess --input ./exports/jira-epics.json --format jira --output ./output/assessment/sprint-12/
```

**3. Assess an HLD document and pipe results into a mapping session:**
```
/assess --input ./design/hld-customer-360.docx --format hld --output ./output/assessment/hld/
```

## Output

On success the agent writes the following artefacts to the output directory:

- `assessment.json` — Structured assessment containing:
  - `functional_requirements[]` — Each FR with id, statement, priority, and source reference.
  - `non_functional_requirements[]` — Each NFR with id, category (performance, security, availability, etc.), statement, and source reference.
  - `ambiguities[]` — Items where intent is unclear, each with a clarifying question.
  - `gaps[]` — Items missing entirely from the document but required by relevant standards.
  - `loaded_standards[]` — Names and versions of all standards consulted during assessment.
  - `unverified_assumptions[]` — Any assumptions the agent made that have not been confirmed.
- `assessment-summary.md` — Human-readable summary of the above.

Exit codes:

| Code | Meaning |
|------|---------|
| `0` | Assessment completed successfully. |
| `1` | Input file not found or unreadable. |
| `2` | Format auto-detection failed; supply `--format` explicitly. |
| `3` | Assessment produced zero FRs and zero NFRs (likely an empty or unrecognised document). |
| `10` | Standards version check failed (network unreachable); assessment produced with stale standards — check `loaded_standards[]`. |

## Related Commands

- `/resolve-context` — Resolve and validate the context sources cited in the assessment output.
- `/map` — Use the extracted FRs and NFRs to drive source-to-target mapping creation or validation.
- `/model-logical` — Feed the assessment artefact into logical data modelling.
