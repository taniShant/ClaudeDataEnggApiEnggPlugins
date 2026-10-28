---
name: review-mr
description: Review a merge request across code quality, security, DQ, performance, observability, lineage and documentation.
agent: merge-request-adviser
user-invocable: true
---

## Purpose

Perform a structured review of a merge request against the applicable engineering standards, a supplied Definition of Done checklist, and seven review dimensions: code quality, security, data quality, performance, observability, lineage completeness, and documentation. Produces a prioritised findings report and a pass/fail recommendation.

## Usage

```
/review-mr --repository <path> \
              --branch <branch-or-mr-ref> \
             [--target-branch <branch>] \
             [--standards <path>] \
             [--dod <path>] \
             [--output <path>]
```

Pass `--help` to receive this document along with the full input and output JSON schemas and worked examples:

```
/review-mr --help
```

## Arguments

| Name | Required / Optional | Description |
|---|---|---|
| `--repository` | Required | Path to the root of the repository to review. The agent will read only files changed between `--branch` and `--target-branch`. |
| `--branch` | Required | Name of the feature branch to review, or a merge request reference string (e.g. `feature/PLATENG-1234-new-pipeline` or `MR!456`). |
| `--target-branch` | Optional | Target branch to diff against. Defaults to `main`. |
| `--standards` | Optional | Path to a file listing the applicable standards to enforce during review (JSON or YAML). If omitted, the agent uses the plugin's bundled default standards list and states which version was loaded. |
| `--dod` | Optional | Path to a Definition of Done checklist file (JSON, YAML, or Markdown checklist format). If omitted, the agent uses the plugin's bundled default DoD and states which version was loaded. |
| `--output` | Optional | Directory or file path for output artefacts. Defaults to `./output/review-mr/`. |

## Example Invocations

**1. Review a feature branch against main using default standards and DoD:**

```
/review-mr \
  --repository ./my-data-pipeline/ \
  --branch feature/PLATENG-1234-add-fraud-pipeline \
  --output ./output/mr-review/
```

**2. Review with explicit standards and DoD, targeting a release branch:**

```
/review-mr \
  --repository ./my-data-pipeline/ \
  --branch feature/PLATENG-5678-schema-change \
  --target-branch release/2024-q4 \
  --standards ./governance/applicable-standards.yaml \
  --dod ./governance/dod-checklist.yaml \
  --output ./output/mr-review/
```

**3. Review using an MR reference (when repository is a local clone):**

```
/review-mr \
  --repository ./cloned-repo/ \
  --branch "MR!789" \
  --standards ./standards/de-standards-v3.yaml
```

## Output

The command writes the following artefacts to the `--output` directory:

- `review-report.md` — Human-readable review report organised by dimension (code quality, security, data quality, performance, observability, lineage, documentation). Each finding includes: severity (blocker, major, minor, suggestion), the specific file and line reference, the standard or DoD item violated, and the recommended remediation action.
- `findings.yaml` — Machine-readable findings list, identical content to `review-report.md` but structured for tooling consumption.
- `dod-checklist.yaml` — The DoD checklist with each item marked `pass`, `fail`, or `not-applicable`, with evidence references for failed items.
- `recommendation.yaml` — Overall pass/fail recommendation with a summary count of blockers and majors. Field `recommendation`: `approve`, `approve_with_conditions`, `request_changes`.
- `unknowns.yaml` — Files or aspects that could not be assessed (e.g. generated files excluded from review, encrypted secrets, binary assets). Each entry states why it was excluded.
- `status.json` — Machine-readable exit status. Field `exit_code`: `0` = review complete, `1` = review complete with warnings, `2` = review could not be completed.

**Loaded standards:** The agent states the version of each standard it loaded at the top of `review-report.md`. If a bundled default was used, the version is clearly identified.

**Exit codes:** `0` review produced (outcome may be pass or fail), `1` review produced with caveats, `2` review could not be completed.

**Unknowns and assumptions:** Any file or aspect excluded from review is listed in `unknowns.yaml` with a reason. The agent will not pass a DoD item without evidence.

## Related Commands

- `/validate` — Run deterministic artefact validation checks; complements the judgement-based MR review.
- `/generate-dq` — Generate data quality rules that may be missing from the MR under review.
- `/performance` — Perform a deeper query plan analysis for performance findings identified during review.
