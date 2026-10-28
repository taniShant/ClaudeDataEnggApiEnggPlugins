# barclays-buk-reliability-engineer-review-performance-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-reliability-engineer-review-performance-v1` |
| Plugin name | `barclays-buk-reliability-engineer` |
| Component type | skill-model-invocable |
| Owner | BUK Retail CAPL |
| Action scope | read-only |
| Invocation mode | model-invocable |
| Installation / release | /plugin install barclays-buk-reliability-engineer@barclays-cio-buk |
| Native command | `/barclays-buk-reliability-engineer:review-performance` |
| Skill name | `review-performance` |

## Description

Scans a service codebase for performance issues and produces a prioritised findings report covering query patterns, synchronous I/O, caching, latency budgets, memory safety, and serialisation overhead against BUK performance standards.

## When to use

Use to scan an existing service codebase for performance issues; produces a prioritised findings report covering N+1 queries, synchronous I/O on critical path, caching gaps, latency budget compliance, memory safety, and serialisation overhead; NOT for greenfield performance design (use plan-performance)

## Inputs

- `CODE_PATH` (optional): absolute path to the service; defaults to current working directory
- `.reliability/performance-target.md` (optional): if present, findings are assessed against the agreed service tier, caching strategy, and memory constraints

## Preconditions

- An active Claude Code session with read access to the service repository
- The skill loads `barclays-buk-standards:performance` alongside itself; reports placeholder flags if unavailable (latency budget enforcement is best-effort without it)

## Expected outputs

- A prioritised findings report covering:
  - Findings table with Critical / High / Medium severity (database patterns, synchronous I/O, caching gaps, latency compliance, memory safety, repeated computation, bounded collections, speculative execution waste, serialisation overhead)
  - Suggested next steps

## Exclusions

- Does not write any changes to the codebase — read-only assessment
- Does not cover observability or resilience concerns — use `review-observability` or `review-resilience`

## Verification

Review the findings report for completeness: confirm all 9 scan pattern categories are addressed, latency budget compliance is assessed (or flagged as best-effort), and at least one suggested next step is actionable.
