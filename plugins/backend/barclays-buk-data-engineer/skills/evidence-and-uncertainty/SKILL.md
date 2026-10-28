---
name: evidence-and-uncertainty
description: How the worker handles evidence, uncertainty and transparency in all outputs
user-invocable: false
owner: BUK Data Engineering Practice
effective_date: 2026-07-13
review_cadence: quarterly
status: approved
---

# Evidence and Uncertainty

## Evidence States

Every claim, value or assertion in a worker output must carry one of the following evidence states:

| State | Definition |
|---|---|
| `VERIFIED_STANDARD` | Directly stated in a loaded, approved, non-stale standard. Version and section cited. |
| `VERIFIED_SOURCE` | Directly observed from an authorised, accessible data source or schema at runtime. |
| `RUNTIME_OBSERVATION` | Observed at runtime (e.g. row count, profile statistic) but not from a canonical reference. |
| `USER_SUPPLIED` | Provided explicitly by the user in the current session. Not independently verified. |
| `INFERRED_CANDIDATE` | Inferred by the worker from available context using documented reasoning. Requires human confirmation. |
| `ASSUMPTION` | Held in the absence of evidence. Explicitly stated; must be validated before production use. |
| `UNKNOWN` | No evidence available; recorded in the unknowns register with resolution path. |

No output may omit an evidence state for a material claim.

---

## Evidence Rules

### Citation

- Every reference to a standard must cite the source document title, version and section.
- Every reference to a data source schema must cite the source name, access method and retrieval timestamp.
- Observed schema and inferred semantics must be presented separately and never merged without explicit labelling.

### Business Rules and Proposals

- Generated business rules are marked as `INFERRED_CANDIDATE` or `ASSUMPTION` unless directly and verbatim supplied by the user or a loaded authoritative standard.
- No business rule may be presented as approved or authoritative without explicit human confirmation.

### Prohibited Claims

The worker must never:

- Invent data owners, approvers, thresholds, SLAs or authoritative sources.
- Claim a test passed or ran when only test code was generated; the distinction between "test generated" and "test executed and passed" must always be explicit.
- Claim compliance with a standard that is unavailable, in `draft` status, stale or superseded.
- Present a candidate or observation as an authoritative standard.
- Assert confidence without a defined, documented method for deriving that confidence.

### Unknowns Register

All unresolved placeholders, missing inputs and open assumptions are preserved in an unknowns register within the output. Each entry includes:

- Description of the unknown.
- Evidence state assigned.
- Impact if unresolved.
- Proposed resolution path and responsible human.

---

## Result Statuses

Every invocation result carries one of the following statuses:

| Status | Meaning |
|---|---|
| `PASS` | All requested outputs delivered; validation passed against applicable standards; no material unknowns outstanding. |
| `PASS_WITH_WARNINGS` | Outputs are usable; one or more non-blocking gaps, stale standards or informational unknowns exist. Warnings enumerated. |
| `NEEDS_HUMAN_DECISION` | One or more material business, architecture or ownership decisions remain unresolved. Output is partial or conditional pending human input. |
| `BLOCKED_SAFETY` | The request or a portion of it exceeds permitted action boundaries, would reveal sensitive row-level data, or involves a destructive operation. Affected action halted; explanation provided. |
| `FAILED` | A tool invocation, validation step or critical dependency failed. Error details and recovery options provided. |

---

## Input Severity Classification

| Severity | Definition |
|---|---|
| `informational` | Absence reduces quality marginally; does not affect output reliability materially. |
| `material` | Absence meaningfully reduces confidence, completeness or correctness. Caveated in output. |
| `hand_off_required` | A specific human decision or artefact must be provided before the affected output section can be completed. |
| `unsafe_to_proceed` | Proceeding would breach safety, permissions or destructive-operation boundaries. Action halted. |

---

## Context Classification

All context sources used by the worker are classified as one of:

| Classification | Definition |
|---|---|
| `authoritative_standard` | An approved, non-stale, loaded standard with confirmed provenance. |
| `approved_reference` | An approved reference document (e.g. architecture decision record, approved design). |
| `user_supplied_evidence` | Information provided by the user in the current session. |
| `runtime_observation` | Data observed at runtime from an authorised source. |
| `unverified_candidate` | Information whose authority has not been confirmed. |

A source classified as `unverified_candidate` or `runtime_observation` must never be presented as an `authoritative_standard`.

---

## Source Register

Every URL or external source accessed during an invocation is recorded in a source register within the output. Each entry includes:

| Field | Description |
|---|---|
| `title` | Human-readable name of the source. |
| `url` | Full URL or identifier. |
| `version_or_date` | Version number or publication date where visible. |
| `retrieval_timestamp` | ISO 8601 timestamp of access. |
| `access_result` | One of: `accessible`, `denied`, `not_found`, `timeout`. |
| `authority_status` | Classification from the context classification table above. |

Sources that returned `denied`, `not_found` or `timeout` must be flagged in the unknowns register with impact assessment.

---

## FR-22 through FR-27 Compliance

The following functional requirements from the V2.0 standards apply to all worker outputs:

| Requirement | Rule |
|---|---|
| FR-22 | Every output artefact must carry an evidence state on all material claims. |
| FR-23 | The worker must not assert compliance with any standard unless that standard is loaded, approved, current and applicable to the artefact type. |
| FR-24 | Test generation and test execution are distinct states; the worker must never conflate them. |
| FR-25 | All unknowns must be registered with impact and resolution path; none may be silently dropped. |
| FR-26 | The source register must be complete for every invocation; partial registers are not permitted. |
| FR-27 | Confidence scores or confidence language may only be used where the derivation method is explicitly documented in the output. |
