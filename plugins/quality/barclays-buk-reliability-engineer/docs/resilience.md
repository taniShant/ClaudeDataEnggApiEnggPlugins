# Resilience — Detailed Standards

The agent reviews code for resilience risks. No automated implementation — findings are advisory with remediation guidance.

---

## Circuit Breakers

Every outbound dependency (HTTP, gRPC, database, Kafka) must be protected by a circuit breaker or timeout. The agent flags:

| Finding | Severity | Trigger |
|---------|----------|---------|
| No circuit breaker on outbound call | High | External HTTP/gRPC call with no Resilience4j, Polly, or equivalent wrapper |
| Circuit trips on errors only | Medium | Should also trip on sustained latency above tier budget |
| No fallback defined | Medium | Circuit open with no fallback behaviour (hard failure to caller) |

---

## Retry Logic

| Finding | Severity | Trigger |
|---------|----------|---------|
| No retry on transient failure | Medium | Network calls with no retry mechanism |
| Retry without backoff | High | Fixed-interval or immediate retry (thundering herd risk) |
| No max-attempts ceiling | Critical | Retry loop without exit condition (infinite retry risk) |
| Retry on non-idempotent operation | Critical | POST/PUT retried without idempotency key |

**Required pattern:** Exponential backoff with jitter, max attempts capped, idempotency verified before enabling retry.

### SDK vs Application-Level Retry

The retry entries above cover SDK/transport-level retry (connection reset, TLS handshake failure, HTTP 503). Application-level retry is a separate concern:

| Finding | Severity | Trigger |
|---------|----------|---------|
| No application-level retry for domain transient failures | High | Throttling (429), model timeout, empty response from an eventually-consistent store — not retried at the application layer even though SDK retry would not cover these |
| SDK retry confused with domain retry | Medium | Only SDK-level retry configured (e.g., AWS SDK `MaxRetries`) without separate application logic for domain-specific transient conditions (e.g., Bedrock model throttle, DynamoDB conditional check failure) |

---

## Per-Call Timeouts

Client-level timeouts are necessary but insufficient. Each outbound call must have its own context deadline within the overall request budget.

| Finding | Severity | Trigger |
|---------|----------|---------|
| Relying solely on runtime timeout | Critical | No per-call `context.WithTimeout` / `context.WithDeadline` (Go), `AbortSignal.timeout()` (Node.js), or call-level timeout config — relying only on Lambda 60s / container orchestrator timeout |
| No deadline propagation | High | Incoming request has a deadline but outbound calls do not inherit or set a tighter sub-deadline |
| Timeout budget not partitioned | Medium | Multiple sequential outbound calls share one timeout without individual budgets (one slow call consumes the entire budget) |

---

## Defensive Response Handling

External SDK/API responses contain pointer/optional fields that may be nil/null even on successful calls. Direct dereference without nil check causes panics or NPEs.

| Finding | Severity | Trigger |
|---------|----------|---------|
| Nil pointer dereference on SDK response | Critical | AWS SDK pointer field (e.g., `*output.Item`, `*response.Body`), gRPC response field, or optional JSON field accessed without nil/null check |
| Missing empty-response guard | High | API call returns successfully but with an empty/nil body — code proceeds to use the body without checking |
| No type assertion safety | Medium | Interface type assertion (Go `x.(Type)`) or cast without comma-ok pattern or error handling |

---

## Graceful Degradation

| Finding | Severity | Trigger |
|---------|----------|---------|
| Hard failure on non-critical dependency | High | Service returns 500 when a non-essential downstream is unavailable |
| No cached fallback | Medium | Data that could be served stale is not cached for degraded mode |
| No partial response support | Medium | All-or-nothing responses where partial data would be acceptable |

---

## Rate Limiting

| Finding | Severity | Trigger |
|---------|----------|---------|
| No inbound rate limiting | High | Service accepts unbounded request volume with no protection |
| Rate limit with no retry-after header | Medium | Callers cannot back off gracefully |

---

## Health and Readiness

| Finding | Severity | Trigger |
|---------|----------|---------|
| No health endpoint | High | No `/health` or `/actuator/health` equivalent |
| Health endpoint doesn't check dependencies | Medium | Returns 200 regardless of downstream state |
| No readiness probe distinction | Medium | No separate endpoint for "starting" vs "ready to accept traffic" |
| Graceful shutdown missing | High | No drain period for in-flight requests before termination |

---

## Fire-and-Forget Error Handling

Errors deferred to queues, async handlers, or background workers must still be logged with full context at the point of deferral. Silent error routing causes incidents to be invisible until customer impact.

| Finding | Severity | Trigger |
|---------|----------|---------|
| Error deferred without logging | High | Error sent to exception queue, async retry handler, or background worker without logging: error type, message, correlation ID, and operation context at the deferral point |
| No dead-letter or alert on deferred errors | High | Deferred error processing with no dead-letter queue, no alert threshold, and no visibility into queue depth or failure rate |

---

## Async Message Processing

Message consumers that process and acknowledge without failure handling cause silent data loss in event-driven systems.

| Finding | Severity | Trigger |
|---------|----------|---------|
| Consumer without failure visibility | High | Message consumer (Kafka, SQS, RabbitMQ) that processes and acks without: retry-on-failure mechanism, dead-letter queue configuration, or error logging at consumption point |
| No dead-letter queue configured | High | Queue consumer implementation with no DLQ or error destination — failed messages vanish silently |

---

## Resource Lifecycle

Resources acquired from external systems (connections, file handles, streams) must be released deterministically. Leaks cause exhaustion under load.

| Finding | Severity | Trigger |
|---------|----------|---------|
| Resource acquire without release | High | `Open()` / `NewClient()` / `connect()` / `acquire()` without corresponding `defer close()` (Go), `finally { close() }` (Java/JS), or context-manager `with` (Python) in the same scope or error path |
| No backpressure on queue consumption | High | Unbounded `for msg := range channel` (Go), `consumer.poll()` loop (Java), or `on('message')` handler (Node.js) without concurrency limiter, semaphore, worker pool size, or buffer — when the framework does not provide built-in backpressure |

---

## Batch Processing

Batch jobs and ETL processes have distinct reliability requirements: they run unattended, process many records, and failures may go undetected for hours.

| Finding | Severity | Trigger |
|---------|----------|---------|
| No pre-flight validation | High | Batch entry point (scheduled job, ETL pipeline, CLI command) begins processing immediately without checking preconditions: input file existence, expected format, minimum row count, or upstream dependency health |
| No per-record error handling | High | Loop iterating records with no try/catch inside the loop body (only around the entire loop) — one bad record aborts the entire batch; remaining valid records are not processed |
| Missing job phase markers | Medium | Long-running batch method without structured log markers at major phase boundaries (START with input count, phase transitions, END with processed/failed counts, or FAILED with error context) — makes hung jobs indistinguishable from slow jobs |

---

## Schema Validation at External Boundaries

Responses from external APIs (outside the team's control) must be validated before use. Internal shared-contract APIs are excluded.

| Finding | Severity | Trigger |
|---------|----------|---------|
| External API response used without validation | High | HTTP response body from an external API (third-party, cross-team, vendor SDK) cast directly to type or properties accessed without schema validation, type assertion, or shape check — crashes when upstream silently changes response format |
