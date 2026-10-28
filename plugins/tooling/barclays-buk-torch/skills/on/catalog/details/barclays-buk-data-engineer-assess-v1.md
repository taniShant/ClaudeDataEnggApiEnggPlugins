# barclays-buk-data-engineer-assess-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-data-engineer-assess-v1` |
| Plugin name | `barclays-buk-data-engineer` |
| Component type | skill-user-only |
| Owner | Barclays BUK |
| Action scope | local-modification |
| Invocation mode | user-only |
| Installation / release | /plugin install barclays-buk-data-engineer@barclays-cio-buk |
| Native command | `/barclays-buk-data-engineer:assess` |
| Skill name | `assess` |

## Description

Assess a requirement document and extract structured FRs, NFRs, ambiguities and gaps.

## When to use

Use when you have a requirement document (prose, Jira export, HLD, or mapping) that needs to be broken down into structured functional requirements, non-functional requirements, ambiguities, and gaps before downstream data engineering activities such as source-to-target mapping, context resolution, or logical modelling — this capability only extracts and structures requirements; it does not resolve ambiguities, perform mapping, or model data.

## Inputs

- `--input <path>` (required) — Path to the requirement document to assess; accepts `.md`, `.txt`, `.docx`, `.pdf`, `.json`, or `.yaml` files.
- `--format <prose|jira|hld|mapping>` (optional) — Explicitly specifies the input document format; if omitted, the agent auto-detects from file extension and content heuristics.
- `--output <path>` (optional) — Directory path for assessment artefacts; defaults to `./output/assessment/`.
- `--help` (optional) — Prints the input/output schema, loaded standards, and an example invocation, then exits with code `0`.

## Preconditions

- The input file specified by `--input` must exist and be readable by the agent.
- The input file must be in one of the supported formats: `.md`, `.txt`, `.docx`, `.pdf`, `.json`, or `.yaml`.
- The document must contain recognisable requirement content (at least one FR or NFR must be extractable, otherwise exit code `3` is returned).
- If auto-detection of the document format is unreliable for your file, you must supply `--format` explicitly to avoid exit code `2`.
- Network connectivity is recommended so the agent can perform a standards version check; without it, assessment proceeds with stale standards (exit code `10`).

## Expected outputs

- `assessment.json` — Machine-readable structured assessment containing arrays for `functional_requirements[]` (each with id, statement, priority, source reference), `non_functional_requirements[]` (each with id, category, statement, source reference), `ambiguities[]` (each with a clarifying question), `gaps[]` (missing items required by relevant standards), `loaded_standards[]` (names and versions consulted), and `unverified_assumptions[]`.
- `assessment-summary.md` — Human-readable summary of the structured assessment.
- Both artefacts are written to the output directory (default `./output/assessment/` or the path specified via `--output`).

## Exclusions

- Does not resolve ambiguities or gaps — it only identifies and documents them; use `/resolve-context` for resolution.
- Does not perform source-to-target mapping — use `/map` to consume the assessment output for that purpose.
- Does not generate logical data models — use `/model-logical` to feed the assessment artefact into modelling.
- Does not modify or annotate the original input document.
- Does not validate or verify external context sources cited in the requirements; that is the responsibility of `/resolve-context`.

## Verification

Confirm the command exits with code `0`, then verify that both `assessment.json` and `assessment-summary.md` exist in the output directory. Open `assessment.json` and check that `functional_requirements[]` and `non_functional_requirements[]` are populated with meaningful entries, review `ambiguities[]` and `gaps[]` for completeness, and inspect `loaded_standards[]` to ensure current standard versions were used (a stale-standards warning via exit code `10` indicates the standards version check failed).
