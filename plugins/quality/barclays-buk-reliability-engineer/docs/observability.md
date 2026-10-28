# Observability — Detailed Standards

The agent reviews and implements observability against the BUK OTel conventions. This is the only capability area with automated implementation.

---

## Maturity Phases

Services progress through three phases. Each phase builds on the last.

| Phase | What it proves | Gate criteria |
|-------|---------------|--------------|
| **Logging** | Structured, correlated, Collector-ready logs | All 5 criteria below pass |
| **Tracing** | Spans on handlers, context propagates outbound | Spans + propagation verified |
| **Metrics** | Golden signals instrumented, cardinality bounded | Histograms + cardinality pass |

Phase order is advisory. The agent recommends logging first but does not block.

---

## Logging Phase — 5 Gate Criteria

1. **Structured JSON to stdout** — all logs emit JSON with required schema fields (Timestamp, SeverityText, Body, Resource.service.name)
2. **No unstructured logging** — zero raw println or string-concatenation log statements
3. **Correlation IDs** — logs during a request contain TraceId and SpanId matching propagated context
4. **Collector-ready** — OTel SDK with OTLP exporter activated only when `OTEL_EXPORTER_OTLP_ENDPOINT` is set; disabled gracefully when absent
5. **Capability attestation** — component test starts a real Collector, sends a request with `traceparent`, asserts Collector received correctly structured correlated logs

---

## Implementation Sequence

When implementing from scratch, migrations follow this order:

| # | Migration | What it adds |
|---|-----------|-------------|
| 001 | Structured logging | Logging framework configured with OTel-native schema |
| 002 | Correlation IDs | TraceId/SpanId injected from request context |
| 003 | Collector-ready | OTel SDK with OTLP exporter, env-var gated |
| 004 | Sensitive data guard | Test assertions: PAN/sort-code patterns absent from exports |
| 005 | Capability attestation | Component test with real Collector via docker-compose |

After baseline, the agent identifies **enrichment opportunities** (async jobs, outbound calls, business events, error enrichment) and generates additional migrations.

---

## State Files

The agent manages `.reliability/` in the target repo:

| File | Written by | Purpose |
|------|-----------|---------|
| `observability-target.md` | design-observability/review | Agreed decisions — schema, strategy, stack, phases |
| `state.yaml` | implement | Per-migration status (planned / implemented / verified) |
| `changelog/###__*.md` | implement | One migration file per concern |
| `docker-compose.verify.yaml` | implement (first run) | Starts OTel Collector for component tests |
| `collector-config.yaml` | implement (first run) | Collector pipeline: OTLP → file export |
| `exports/` | runtime | Gitignored; Collector writes JSON here for test assertions |

---

## Sensitive Data Patterns

These must NEVER appear in log output. The agent asserts their absence in verification tests.

| Pattern | Regex |
|---------|-------|
| PAN (card number) | `\b[0-9]{13,19}\b` |
| Sort code | `\b[0-9]{2}-[0-9]{2}-[0-9]{2}\b` |
| Account number | `\b[0-9]{8}\b` (context-dependent) |
| NI number | `\b[A-Z]{2}[0-9]{6}[A-Z]\b` |
| Email | `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z]{2,}\b` |

---

## Trace Coverage Consistency

When tracing is present in a codebase, it must be applied consistently across all I/O-performing methods.

| Finding | Severity | Trigger |
|---------|----------|---------|
| Inconsistent trace coverage | Critical | Sibling methods in the same package are traced (have `span.Start` / `tracer.Start` / `trace.Begin`) but one or more methods performing I/O are not. All methods that call external services, databases, or perform file I/O must be traced if any sibling is. |
| Missing span on public entry point | High | A public handler or entry point (Lambda handler, HTTP handler, gRPC method) has no span — even if internal methods are traced |

---

## Correlation ID Propagation

Correlation IDs must appear not only in log fields but also in outbound request metadata for end-to-end distributed tracing across service boundaries.

| Finding | Severity | Trigger |
|---------|----------|---------|
| Correlation ID in logs only | High | TraceId/SpanId present in log fields but not propagated in outbound HTTP headers (`traceparent`, `X-Request-Id`) or message metadata (Kafka headers, SQS message attributes) |
| No inbound-to-outbound propagation | High | Incoming request carries a trace context (e.g., `traceparent` header) but outbound calls do not forward it — breaks distributed trace chain |

---

## Consistency of Operational Signals

If one entry point of a given type (e.g., Lambda handler, HTTP endpoint, Kafka consumer) emits a particular operational signal, then ALL entry points of that type must emit the same signal.

| Finding | Severity | Trigger |
|---------|----------|---------|
| Inconsistent duration logging | High | Some handlers log execution duration but others of the same type do not — makes it impossible to identify slow invocations uniformly |
| Inconsistent error classification | High | Some handlers classify errors (transient vs permanent, upstream vs internal) but sibling handlers do not |
| Partial metric coverage | Medium | Metrics (histograms, counters) instrumented on some endpoints but missing on others of the same type |

---

## Structured Error Context

Catch blocks that log only the error message without operational context make incidents undiagnosable. Production incidents have remained in RCA for 50+ days because errors lacked sufficient context to identify root cause.

| Finding | Severity | Trigger |
|---------|----------|---------|
| Catch block without structured context | High | `catch` / `except` / `recover` block that logs only `e.getMessage()` / `err.Error()` / `str(e)` without also logging: correlation ID (TraceId or request ID), operation name, stack trace, and input context (resource ID, record count, or relevant parameters) |
| Exception re-thrown without wrapping | High | Exception caught and re-thrown (or returned) without adding context about what operation was being performed and what input triggered the failure |

---

## Supported Stacks

| Stack | Detection | Logging framework | OTel SDK |
|-------|-----------|------------------|----------|
| Spring Boot | pom.xml / build.gradle with spring-boot-starter | Logback | opentelemetry-spring-boot-starter |
| Node.js | package.json | Pino / Winston | @opentelemetry/sdk-node |
| Python | requirements.txt / pyproject.toml | structlog / stdlib | opentelemetry-sdk |
| Go | go.mod | slog / zap | go.opentelemetry.io/otel |

Stack-specific implementation patterns are in the plugin-local `otel-conventions` skill.

---

## Verification Infrastructure

The agent uses a real OTel Collector in component tests — not mocks. The Collector image is pulled from the internal registry only:

```
container-release.container-registry-non-prod.barcapint.com/external/docker.io/otel/opentelemetry-collector-contrib:0.149.0
```

When Docker is unavailable, a schema-only mode validates log format without starting containers.
