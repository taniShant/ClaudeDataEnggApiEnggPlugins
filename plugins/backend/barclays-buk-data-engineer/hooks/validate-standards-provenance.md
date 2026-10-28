---
name: validate-standards-provenance
trigger: post-agent
applies_to: [all agents]
description: Checks that every standards claim in the output has provenance (source, version, owner, review status).
---

## Purpose

Prevents unsubstantiated compliance claims from passing through to consumers. Every standard referenced in an agent output must have traceable provenance. This hook ensures that compliance posture is grounded in verifiable sources rather than model-generated assertions.

## Validation Steps

### 1. Standards Entry Validation

For each entry in `standards_applied[]` of the result manifest, verify:

| Field | Rule |
|---|---|
| `standard_id` | Must be non-empty. A blank or whitespace-only standard ID is a validation failure. |
| `version` | Must be present and non-empty. Version `unknown` is permitted but triggers a warning. |
| `owner` | Must be present and non-empty. Identifies the team or individual accountable for the standard. |
| `review_status` | Must be one of: `current`, `overdue`, `draft`, `placeholder`, `missing` |
| `source_url` | Must be present. If the source URL is genuinely unavailable, the field must be explicitly set to `"unavailable"` rather than omitted. |

### 2. Staleness Check

| `review_status` value | Behaviour |
|---|---|
| `current` | No additional action required. |
| `overdue` | Append a warning to `warnings[]` identifying the standard ID and the overdue review. |
| `draft` | Append a warning. Status remains as-is. |
| `placeholder` | The result manifest status must not be `PASS`. Downgrade to `PASS_WITH_WARNINGS` at minimum. Append a warning identifying the placeholder standard. |
| `missing` | The result manifest status must not be `PASS`. Downgrade to `PASS_WITH_WARNINGS` at minimum. Append a warning identifying the missing standard. |

### 3. Unprovenanced Claims

If any entry in `standards_applied[]` fails the field validation above, it is treated as an unprovenanced claim. Unprovenanced claims:

- Are never silently passed through
- Generate a `MANIFEST_STANDARDS_PROVENANCE_FAILURE` warning in `warnings[]`
- Prevent `status: PASS` — downgrade to `PASS_WITH_WARNINGS` at minimum

## Behaviour

This hook does **not** block output. It appends warnings and may downgrade status. Specific behaviour:

1. For each provenance failure, append to `warnings[]`:
   - `source`: `validate-standards-provenance-hook`
   - `code`: `MANIFEST_STANDARDS_PROVENANCE_FAILURE`
   - `standard_id`: the affected standard identifier
   - `message`: human-readable description of the provenance gap
   - `fields_missing`: list of field names that failed validation

2. If `status` was `PASS` but provenance failures require downgrade, set `status` to `PASS_WITH_WARNINGS` and record the downgrade reason.

3. Never silently pass unprovenanced claims. Every gap must be surfaced in the result manifest.
