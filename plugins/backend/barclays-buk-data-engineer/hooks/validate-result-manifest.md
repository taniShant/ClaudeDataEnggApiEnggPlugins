---
name: validate-result-manifest
trigger: post-agent
applies_to: [all agents]
description: Validates that every agent invocation produces a result manifest conforming to result-manifest.schema.json.
---

## Purpose

Ensures every agent produces a valid result manifest, maintaining contract integrity across all plugin agents. This hook runs after every agent invocation and validates the output against the canonical schema before the result is returned to the caller.

## Validation Steps

### 1. JSON Schema Validation

Validate the result manifest against `schemas/result-manifest.schema.json`. Any JSON Schema validation failure is recorded as a warning. The validation checks structural conformance including field types, required fields, and enum values.

### 2. Required Fields Check

The following fields must be present and non-empty in every result manifest regardless of status:

| Field | Type | Description |
|---|---|---|
| `request_id` | string | Unique identifier for the request, propagated from input manifest |
| `agent_version` | string | Semver version of the agent that produced this output |
| `task_type` | string | The task type identifier matching the invoking agent |
| `status` | string | One of: `PASS`, `PASS_WITH_WARNINGS`, `BLOCKED_SAFETY`, `BLOCKED_QUALITY`, `NEEDS_HUMAN_REVIEW`, `ERROR`, `SKIPPED` |
| `timestamp` | string | ISO 8601 datetime of when the agent completed |

### 3. Status Consistency Check

| Condition | Rule |
|---|---|
| `status` is `PASS` | `blocking_findings` must be empty or absent |
| `status` is `BLOCKED_SAFETY` | `blocking_findings` must contain at least one entry with `severity: blocking` and `category: safety` |
| `status` is `BLOCKED_QUALITY` | `blocking_findings` must contain at least one entry with `severity: blocking` and `category: quality` |
| `status` is `PASS_WITH_WARNINGS` | `warnings[]` must contain at least one entry |
| `status` is `NEEDS_HUMAN_REVIEW` | `review_required` must be `true` and `review_reason` must be non-empty |

## Behaviour on Failure

This hook does **not** block output. If validation fails:

1. Append a structured warning to the result manifest's `warnings[]` array with:
   - `source`: `validate-result-manifest-hook`
   - `code`: `MANIFEST_VALIDATION_FAILURE`
   - `message`: description of the specific validation failure
   - `fields_affected`: list of field paths that failed validation
2. If the manifest is so malformed that warnings cannot be appended, wrap the raw output in a minimal valid manifest with `status: ERROR` and the validation error in `errors[]`.

The hook does not modify or correct the manifest fields beyond appending warnings. Corrections are the responsibility of the agent author.
