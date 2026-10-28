# barclays-buk-reliability-engineer-review-resilience-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-reliability-engineer-review-resilience-v1` |
| Plugin name | `barclays-buk-reliability-engineer` |
| Component type | skill-model-invocable |
| Owner | BUK Retail CAPL |
| Action scope | read-only |
| Invocation mode | model-invocable |
| Installation / release | /plugin install barclays-buk-reliability-engineer@barclays-cio-buk |
| Native command | `/barclays-buk-reliability-engineer:review-resilience` |
| Skill name | `review-resilience` |

## Description

Scans a service codebase for resilience gaps and produces a prioritised findings report covering circuit breakers, timeouts, retry logic, graceful degradation, rate limiting, error handling, and batch processing patterns.

## When to use

Use to scan an existing service codebase for resilience gaps; produces a prioritised findings report covering circuit breakers, per-call timeouts, retry logic, graceful degradation, rate limiting, message consumer failure visibility, and batch processing patterns; NOT for greenfield resilience design (use plan-resilience)

## Inputs

- `CODE_PATH` (optional): absolute path to the service; defaults to current working directory
- `.reliability/resilience-target.md` (optional): if present, findings are assessed against the agreed circuit breaker framework, retry strategy, and dependency criticality decisions

## Preconditions

- An active Claude Code session with read access to the service repository

## Expected outputs

- A prioritised findings report covering:
  - Findings table with Critical / High / Medium severity (single points of failure, timeout configuration, retry logic, infinite retry risk, graceful degradation, rate limiting, per-call timeouts, nil dereference, application-level retry, fire-and-forget error handling, async consumer failure visibility, resource leaks, backpressure, batch pre-flight validation, batch per-record error handling, batch phase markers, external API schema validation)
  - Suggested next steps

## Exclusions

- Does not write any changes to the codebase — read-only assessment
- Does not cover observability or performance concerns — use `review-observability` or `review-performance`

## Verification

Review the findings report for completeness: confirm all 17 resilience scan patterns are addressed, batch processing patterns are checked if batch jobs are present, and resource acquire/release patterns are checked across all I/O entry points.
