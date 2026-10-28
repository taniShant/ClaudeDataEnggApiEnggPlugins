---
name: review-resilience
description: >
    Scans a service codebase for resilience gaps and produces a prioritised findings report
    covering circuit breakers, timeouts, retry logic, graceful degradation, rate limiting,
    error handling, and batch processing patterns.
user-invocable: false
owner: BUK Retail CAPL
review-trigger: When BUK resilience standards or accepted frameworks change
---

# Review — Resilience

---

## Inputs

```
CODE_PATH:  /absolute/path/to/service   (default: current working directory)
```

---

## Output

A focused resilience findings report covering:
- Prioritised findings table (Critical / High / Medium)
- Suggested next steps

---

## Step 1: Silent scan

Use Glob, Read, Bash, and Grep. Output nothing during this phase.

Detect stack and build tool:
- `pom.xml` / `build.gradle` → Spring Boot, Maven/Gradle
- `package.json` → Node.js
- `go.mod` → Go
- `requirements.txt` / `pyproject.toml` → Python

---

## Step 2: Assess resilience

Scan for:

- **Single points of failure**: outbound dependencies called without circuit breakers
- **Timeout configuration**: any HTTP client, database pool, or Kafka consumer with no timeout or infinite timeout
- **Retry logic**: missing retry on transient failures, or retry without exponential backoff / jitter
- **Infinite retry risk**: retry loops without an exit condition or max-attempts ceiling
- **Graceful degradation**: does the service degrade gracefully (return cached data, serve limited functionality) when a non-critical dependency is unavailable?
- **Rate limiting**: is the service protected from request floods? Any inbound rate limiting?
- **Per-call timeouts**: each outbound call must have its own context deadline (`context.WithTimeout` in Go, `AbortSignal.timeout()` in Node.js, per-call timeout config in Java/Python), not rely solely on the overall runtime timeout (Lambda 60s, container orchestrator). Flag absence of per-call deadlines.
- **Defensive response handling**: SDK/API response pointer fields dereferenced without nil/null check. AWS SDK pointer fields (`*output.Field`), gRPC response fields, optional JSON fields may be nil even on successful calls. Flag direct dereference without guard.
- **Application-level retry**: domain transient failures (throttling 429, model timeout, empty response from eventually-consistent store) need their own retry layer above SDK transport retry. Flag when only SDK-level retry is configured.
- **Fire-and-forget error handling**: errors sent to queues or deferred handlers without logging at the deferral point (error type, correlation ID, operation context) and without dead-letter/alert configuration. Flag silent error routing.
- **Async message consumer without failure visibility**: Kafka/SQS/RabbitMQ consumers that process and ack without retry-on-failure, dead-letter queue, or error logging at consumption point. Flag silent message loss risk.
- **Resource acquire without release**: `Open()`/`NewClient()`/`connect()` without corresponding `defer close()`/`finally`/context-manager in same scope or error path. Flag connection/handle leaks.
- **No backpressure on queue consumption**: unbounded consumer loops without concurrency limiter, semaphore, or worker pool size when the framework doesn't provide built-in backpressure. Flag OOM/exhaustion risk.
- **Batch pre-flight validation**: batch entry points (scheduled jobs, ETL, CLI) that begin processing immediately without checking preconditions (input file exists, format valid, row count reasonable). Flag fail-late patterns.
- **Batch per-record error handling**: loops iterating records with no try/catch inside the loop body. One bad record should not abort the entire batch. Flag when error handling only wraps the outer loop.
- **Batch job phase markers**: long-running batch methods without structured START/END/FAILED log markers at phase boundaries. Flag jobs that would be invisible if hung.
- **External API schema validation**: HTTP responses from external APIs (third-party, cross-team) used directly without type assertion or shape validation. Flag when upstream format changes would cause crashes.

---

## Step 3: Produce findings report

Severity definitions:

| Priority | Definition |
|----------|-----------|
| **Critical** | Production outage risk; per-call timeout absent; nil dereference; resource leak |
| **High** | Missing circuit breakers; silent error routing; message consumers without DLQ |
| **Medium** | Improvement opportunity — meaningful resilience gain but no immediate risk |

Report format:

```markdown
# Resilience Review — [service name]

**Date:** [date]
**Stack:** [stack] ([build tool])
**Modules:** [list]

---

## Summary

[2–3 sentence overview: what is the most significant resilience risk? Is the service safe under partial outages?]

---

## Findings

| Priority | Finding | File / Location | Recommendation |
|----------|---------|-----------------|---------------|
| Critical | | | |
| High | | | |
| Medium | | | |

---

## Suggested Next Steps

[3–5 numbered options — never require a specific path]
```

---

## Flags

State any of the following that apply (or "None identified"):

**Missing or ambiguous inputs:**
- CODE_PATH not provided — skill scanned current working directory

**Decisions made under uncertainty:**
- Stack detected as [X] based on [indicator] — if incorrect, specify and re-run
- Framework detection (circuit breaker library, messaging client) inferred from import patterns only

---

## Agent Self-Check

- [ ] Stack detected
- [ ] All 17 resilience scan patterns checked
- [ ] Batch processing patterns checked if batch jobs are present
- [ ] Message consumer failure visibility checked if async consumers are present
- [ ] Resource acquire/release checked across all I/O entry points
