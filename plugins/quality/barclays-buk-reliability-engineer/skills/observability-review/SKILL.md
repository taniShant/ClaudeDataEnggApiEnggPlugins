---
name: observability-review
description: >
    Observability review criteria for BUK services — what to scan, maturity phase gates,
    log level correctness rules, sensitive data patterns, trace coverage consistency,
    correlation propagation, and structured error context. Load when the agent is reviewing
    observability (FOCUS=observability or FOCUS=all in review mode).
user-invocable: false
---

# BUK Observability Review Standards

| | |
|---|---|
| **Source** | BUK OTel Conventions v1.0.0 |
| **Owner** | BUK Retail CAPL |
| **Review trigger** | OTel SDK major version bump or new stack adoption |
| **Status** | Active |
| **Classification** | Internal |

---

## Scan Criteria

When reviewing observability, scan for ALL of the following:

### Logging Schema

- **Structured JSON?** — Are all logs emitted as JSON to stdout with required schema fields (Timestamp, SeverityText, Body, Resource.service.name)?
- **OTel-native or ECS?** — Which schema is in use? Is it consistent across modules?
- **Unstructured logging** — Any raw `println`, `System.out`, `console.log`, or string-concatenation log statements remaining?

### Correlation IDs

- **trace_id/span_id in logs?** — Are request-scoped logs enriched with TraceId and SpanId?
- **MDC / AsyncLocalStorage / context vars configured?** — Is the mechanism for propagating trace context into log records wired?

### Correlation ID Propagation

Correlation IDs must appear not only in log fields but also in outbound request metadata for end-to-end distributed tracing.

| Finding | Severity | Trigger |
|---------|----------|---------|
| Correlation ID in logs only | High | TraceId/SpanId present in log fields but not propagated in outbound HTTP headers (`traceparent`, `X-Request-Id`) or message metadata (Kafka headers, SQS message attributes) |
| No inbound-to-outbound propagation | High | Incoming request carries a trace context (e.g., `traceparent` header) but outbound calls do not forward it — breaks distributed trace chain |

### Collector Readiness

- **OTLP exporter wired?** — Is an OTel SDK configured with an OTLP exporter?
- **Env-var gated?** — Is the exporter activated only when `OTEL_EXPORTER_OTLP_ENDPOINT` is set, and disabled gracefully when absent?

### Sensitive Data Risks

Any log statement that could emit the following patterns is a **Critical** finding:

| Pattern | Regex | Description |
|---------|-------|-------------|
| PAN (card number) | `\b[0-9]{13,19}\b` | Card numbers |
| Sort code | `\b[0-9]{2}-[0-9]{2}-[0-9]{2}\b` | UK sort code |
| Account number | `\b[0-9]{8}\b` | UK bank account number (context-dependent) |
| NI number | `\b[A-Z]{2}[0-9]{6}[A-Z]\b` | National Insurance number |
| Email | `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z]{2,}\b` | Customer email |

### Log Level Correctness

Are the right levels used for the right data?

| Level | When to use | Anti-patterns |
|-------|-------------|--------------|
| **ERROR** | Failures requiring immediate attention — unhandled exceptions, unrecoverable errors, data integrity violations | Using ERROR for expected business conditions (e.g. "user not found") |
| **WARN** | Degraded or unexpected conditions that don't block the current operation — retries, fallbacks, missing optional config, slow dependencies | Using WARN for normal flow variation |
| **INFO** | Business-meaningful milestones only — request received, payment processed, job completed, service started | Loop-iteration noise, chatty INFO in hot paths, logging every retry attempt |
| **DEBUG** | Verbose diagnostic detail for development and investigation | Emitting in production, containing sensitive data, unconditionally enabled |

**Rules:**
1. Stack traces must only appear at ERROR level.
2. DEBUG must be gated by a `LOG_LEVEL` env var (or equivalent) and must not emit in production by default.
3. INFO must not be noisy — if a log line fires more than once per logical operation, it should be DEBUG.
4. Exceptions must not be swallowed silently — every caught exception must produce at least a WARN with the exception message.
5. DEBUG must never contain sensitive data (PAN, sort code, account numbers, NI numbers, email).

**Severity mapping:**
- DEBUG unconditionally enabled in production → **High**
- Stack traces at INFO/WARN → **High**
- Chatty INFO in hot paths → **Medium**
- Swallowed exceptions (catch block with no log) → **Medium**

### Trace Coverage Consistency

When tracing is present in a codebase, it must be applied consistently across all I/O-performing methods.

| Finding | Severity | Trigger |
|---------|----------|---------|
| Inconsistent trace coverage | Critical | Sibling methods in the same package are traced (have `span.Start` / `tracer.Start` / `trace.Begin`) but one or more methods performing I/O are not. All methods that call external services, databases, or perform file I/O must be traced if any sibling is. |
| Missing span on public entry point | High | A public handler or entry point (Lambda handler, HTTP handler, gRPC method) has no span — even if internal methods are traced |

### Consistency of Operational Signals

If one entry point of a given type emits a particular operational signal, then ALL entry points of that type must emit the same signal.

| Finding | Severity | Trigger |
|---------|----------|---------|
| Inconsistent duration logging | High | Some handlers log execution duration but others of the same type do not |
| Inconsistent error classification | High | Some handlers classify errors (transient vs permanent, upstream vs internal) but sibling handlers do not |
| Partial metric coverage | Medium | Metrics instrumented on some endpoints but missing on others of the same type |

### Structured Error Context

Catch blocks that log only the error message without operational context make incidents undiagnosable.

| Finding | Severity | Trigger |
|---------|----------|---------|
| Catch block without structured context | High | `catch` / `except` / `recover` block that logs only `e.getMessage()` / `err.Error()` / `str(e)` without also logging: correlation ID, operation name, stack trace, and input context |
| Exception re-thrown without wrapping | High | Exception caught and re-thrown without adding context about what operation was being performed and what input triggered the failure |

### Health and Readiness Endpoints

- **Implemented?** — Is there a `/health` or `/actuator/health` equivalent?
- **Meaningful status?** — Does it check downstream dependencies or just return 200?

### Missing Observability Opportunities

Flag as **Medium** findings:
- Async/background jobs with no logging or trace context
- Kafka consumers with no correlation ID propagation
- Outbound HTTP calls without W3C traceparent header propagation
- Exception handlers logging raw stack traces without structured context
- Circuit breaker state changes not logged

### Logging Coverage Gaps

Look for code paths that should have logging but don't. Flag as **Medium**:
- **Error paths** with no log at all (catch blocks that return an error response silently)
- **External calls** with no log before or after (HTTP clients, DB queries in critical paths)
- **State transitions** with no audit trail (status changes, payment state machines, account operations)

Keep this lightweight — flag only obvious gaps in critical paths, not every function missing a log line.

---

## Maturity Phases

Services progress through three phases. Each phase builds on the last.

| Phase | What it proves | Gate criteria |
|-------|---------------|--------------|
| **Logging** | Structured, correlated, Collector-ready logs | All 5 criteria below pass |
| **Tracing** | Spans on handlers, context propagates outbound | Spans + propagation verified |
| **Metrics** | Golden signals instrumented, cardinality bounded | Histograms + cardinality pass |

Phase order is advisory. Recommend logging first but do not block.

### Logging Phase — 5 Gate Criteria

1. **Structured JSON to stdout** — all logs emit JSON with required schema fields (Timestamp, SeverityText, Body, Resource.service.name)
2. **No unstructured logging** — zero raw println or string-concatenation log statements
3. **Correlation IDs** — logs during a request contain TraceId and SpanId matching propagated context
4. **Collector-ready** — OTel SDK with OTLP exporter activated only when `OTEL_EXPORTER_OTLP_ENDPOINT` is set; disabled gracefully when absent
5. **Capability attestation** — component test starts a real Collector, sends a request with `traceparent`, asserts Collector received correctly structured correlated logs

**Critical:** Structured JSON alone does NOT complete the logging phase. Collector integration (OTLP exporter, env-var gated) and a capability attestation test are required.

---

## Supported Stacks

| Stack | Detection | Logging framework | OTel SDK |
|-------|-----------|------------------|----------|
| Spring Boot | pom.xml / build.gradle with spring-boot-starter | Logback | opentelemetry-spring-boot-starter |
| Node.js | package.json | Pino / Winston | @opentelemetry/sdk-node |
| Python | requirements.txt / pyproject.toml | structlog / stdlib | opentelemetry-sdk |
| Go | go.mod | slog / zap | go.opentelemetry.io/otel |

Stack-specific implementation patterns are in the `otel-conventions` skill.

---

## Assessing Current State

If `.reliability/observability-target.md` exists in the target repo:
- Read it to understand agreed schema, strategy, and stack decisions
- Report current phase and what remains to reach the next phase
- Reference the specific gate criteria that are unmet

If no target exists, assess based on code scan alone and note this in Flags.

---

## Agent Self-Check

Before producing observability findings, verify:

- [ ] I scanned for ALL criteria listed above (schema, correlation, collector, sensitive data, log levels, trace coverage, signal consistency, error context, health, opportunities, coverage gaps)
- [ ] I checked every logging statement for log level correctness, not just schema
- [ ] I verified trace coverage consistency — all I/O methods traced if any sibling is
- [ ] I checked correlation ID propagation in outbound calls, not just log fields
- [ ] I assessed maturity against the 5 logging phase gate criteria
- [ ] I verified that sensitive data patterns cannot appear in log output at ANY level including DEBUG
- [ ] I flagged structured-only logging (no collector) as incomplete — not as "logging phase complete"
- [ ] I read `.reliability/observability-target.md` if it existed, or noted its absence in Flags

---

## Areas for Specialist Extension

- Tracing phase gate criteria (when tracing review is added)
- Metrics phase gate criteria (when metrics review is added)
- Custom sensitive data patterns per service domain
- Log volume budgets and cost estimation
