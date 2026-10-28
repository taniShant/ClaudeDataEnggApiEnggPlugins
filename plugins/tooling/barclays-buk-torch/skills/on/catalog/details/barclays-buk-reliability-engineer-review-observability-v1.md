# barclays-buk-reliability-engineer-review-observability-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-reliability-engineer-review-observability-v1` |
| Plugin name | `barclays-buk-reliability-engineer` |
| Component type | skill-model-invocable |
| Owner | BUK Retail CAPL |
| Action scope | read-only |
| Invocation mode | model-invocable |
| Installation / release | /plugin install barclays-buk-reliability-engineer@barclays-cio-buk |
| Native command | `/barclays-buk-reliability-engineer:review-observability` |
| Skill name | `review-observability` |

## Description

Scans a service codebase for observability gaps and produces a prioritised findings report covering structured logging, OTel SDK wiring, correlation IDs, sensitive data risks, and phase gate status against BUK OTel conventions.

## When to use

Use to scan an existing service codebase for observability gaps; produces a prioritised findings report covering structured logging, OTel SDK wiring, correlation IDs, sensitive data risks, and phase gate status; NOT for greenfield observability design (use plan-observability)

## Inputs

- `CODE_PATH` (optional): absolute path to the service; defaults to current working directory
- `.reliability/observability-target.md` (optional): if present, findings are assessed against the agreed schema, strategy, and phase decisions rather than defaults

## Preconditions

- An active Claude Code session with read access to the service repository
- The skill loads `barclays-buk-standards:observability` and `otel-conventions` alongside itself; reports placeholder flags if either is unavailable

## Expected outputs

- A prioritised findings report covering:
  - Findings table with Critical / High / Medium severity (structured logging, OTel SDK wiring, correlation IDs, sensitive data risks, trace coverage consistency, outbound propagation, catch block quality)
  - Phase gate status table (all 5 logging phase criteria: structured JSON, no unstructured logging, correlation IDs in request-scoped logs, collector-ready OTLP exporter, capability attestation test)
  - Suggested next steps

## Exclusions

- Does not write any changes to the codebase — read-only assessment
- Does not generate a migration plan or implement fixes — use `plan-observability` then `implement` for that
- Does not cover performance or resilience concerns — use `review-performance` or `review-resilience`

## Verification

Review the findings report for completeness: confirm the phase gate table lists all 5 criteria with explicit pass/fail status, sensitive data scan is noted, and at least one suggested next step points to an actionable capability.
