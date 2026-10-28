---
name: observability
description: >
    BUK observability standards. Covers OTel-native log schema, severity levels, sensitive data
    rules, correlation ID propagation, context propagation standards, and the observability
    maturity model (logging → tracing → metrics). Use when reviewing observability coverage,
    implementing logging, or defining telemetry architecture.
user-invocable: false
---

# BUK Observability Standards

> **Source:** BUK SDF Observability Conventions v1.0.0
> **Owner:** BUK Principal Engineers / Platform Engineering
> **Review trigger:** Annual, or on OTel spec major version change
> **Status:** Full

---

## 1. OTel-Native Log Schema (Default)

All BUK services emit structured JSON logs with the following fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `Timestamp` | string (ISO 8601) | yes | When the log was emitted |
| `SeverityText` | string | yes | Human-readable severity (INFO, WARN, ERROR, etc.) |
| `SeverityNumber` | integer | yes | Numeric severity per OTel spec |
| `Body` | string | yes | The log message |
| `TraceId` | string (32 hex chars) | yes (if in request context) | W3C trace ID from propagated context |
| `SpanId` | string (16 hex chars) | yes (if in request context) | Current span ID |
| `Resource.service.name` | string | yes | Logical service name |
| `Resource.service.version` | string | yes | Deployed version |
| `Resource.deployment.environment` | string | yes | Environment (dev, staging, prod) |
| `Attributes` | object | optional | Additional structured key-value pairs |

---

## 2. ECS Alternative Mapping

If a repo already uses Elastic Common Schema (ECS), migrating schema is disruptive and unnecessary. Keep ECS and use these equivalent fields:

| OTel-Native | ECS Equivalent |
|-------------|---------------|
| `Timestamp` | `@timestamp` |
| `SeverityText` | `log.level` |
| `Body` | `message` |
| `TraceId` | `trace.id` |
| `SpanId` | `span.id` |
| `Resource.service.name` | `service.name` |
| `Resource.service.version` | `service.version` |
| `Resource.deployment.environment` | `service.environment` |

---

## 3. Severity Levels

| SeverityText | SeverityNumber | Use when |
|-------------|---------------|----------|
| TRACE | 1 | Fine-grained debugging (never in production) |
| DEBUG | 5 | Diagnostic information for development |
| INFO | 9 | Normal operational events (request handled, job completed) |
| WARN | 13 | Unexpected but recoverable conditions |
| ERROR | 17 | Failures requiring attention |
| FATAL | 21 | Unrecoverable failures causing shutdown |

**Rules:**
- Production logging level is INFO minimum
- Never log at INFO for per-request detail in high-throughput services — use DEBUG
- ERROR means "someone should look at this" — not "an expected branch was taken"
- FATAL should only precede process termination

---

## 4. Sensitive Data Rules

The following patterns **MUST NEVER** appear in log output:

| Pattern | Regex | Description |
|---------|-------|-------------|
| PAN (card number) | `\b[0-9]{13,19}\b` | Primary Account Number — mask to last 4 |
| Sort code | `\b[0-9]{2}-[0-9]{2}-[0-9]{2}\b` | UK sort code |
| Account number | `\b[0-9]{8}\b` (context-dependent) | UK bank account number |
| National Insurance | `\b[A-Z]{2}[0-9]{6}[A-Z]\b` | NI number |
| Date of birth | context-dependent | Customer DOB |
| Email | `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z]{2,}\b` | Customer email addresses |
| Full name | context-dependent | Customer full names in log bodies |

**Verification requirement:** Observability test suites MUST include assertions that no exported log line matches PAN or sort code regex patterns.

---

## 5. Resource Attributes

Every service MUST set these OTel resource attributes on all logs and traces:

| Attribute | Source | Example |
|-----------|--------|---------|
| `service.name` | Application config | `bmb-payments-api` |
| `service.version` | Build metadata | `1.2.3` |
| `deployment.environment` | Runtime env var | `prod` |

---

## 6. Context Propagation

| Application Type | Inbound Context | Standard |
|-----------------|----------------|----------|
| HTTP API | `traceparent` + `tracestate` headers | W3C Trace Context |
| Kafka Consumer | Kafka message headers | W3C Trace Context over Kafka headers |

**Rule:** If a service receives a `traceparent` header (or Kafka trace headers), it MUST extract the trace context and include `TraceId` and `SpanId` in all logs emitted during that request or message processing.

---

## 7. Observability Maturity Phases

BUK services progress through three observability phases. Logging is the foundation — tracing and metrics build on top of it.

| Phase | Gate Criteria |
|-------|--------------|
| **Logging** | Structured JSON + correlation IDs + Collector-ready + verified by component test |
| **Tracing** | Spans on all inbound handlers + context propagation on all outbound calls |
| **Metrics** | Golden signal histograms on key endpoints + cardinality within budget |

### Logging Phase — Detailed Gate Criteria

The logging phase is complete when ALL of the following are verified:

1. **Structured JSON to stdout** — all log statements emit structured JSON with the required schema fields to stdout. This is the primary log output; it works in every environment regardless of Collector presence.
2. **No unstructured logging** — zero raw println or string-concatenation log statements remain.
3. **Correlation IDs present** — logs emitted during a request contain TraceId and SpanId matching the propagated context.
4. **Collector-ready (env-var driven)** — OTel SDK configured with OTLP exporter that activates only when `OTEL_EXPORTER_OTLP_ENDPOINT` is set. When absent, export is disabled gracefully with no error, no memory pressure, no startup failure.
5. **Capability attested via test** — a component test starts a Collector, sets the env var, sends a request with `traceparent`, and asserts the Collector receives correctly structured, correlated logs.

### Tracing Phase — Gate Criteria

1. Spans created on all inbound HTTP handlers and Kafka consumers.
2. Outbound HTTP calls and Kafka produce operations propagate `traceparent` context.
3. Span names follow the convention: `<HTTP_METHOD> <path_template>` for HTTP, `<topic> process` for Kafka.
4. Sensitive data not included in span attributes.

### Metrics Phase — Gate Criteria

1. Request count, latency histogram (P50/P95/P99), and error rate instrumented on key endpoints.
2. Metric names follow format: `<service_name>_<domain>_<unit>` (e.g., `payments_api_request_duration_seconds`).
3. Label cardinality bounded — no unbounded label dimensions (e.g., no customer IDs as labels).

---

## 8. Production Deployment Model

This standard does NOT mandate how logs reach a backend in production. Teams choose:

- **Collector in production** — set `OTEL_EXPORTER_OTLP_ENDPOINT` and logs export via OTLP.
- **Platform logging only** — leave the env var unset; structured JSON on stdout gets scraped by platform agents (Splunk, ELK, etc.).
- **Both** — stdout for platform + OTLP for OTel backend simultaneously.

The verification test proves capability. Production strategy is the team's choice.

### Graceful Degradation Requirements

The OTel SDK configuration MUST handle Collector absence safely:

| State | Required behaviour |
|-------|--------------------|
| No `OTEL_EXPORTER_OTLP_ENDPOINT` set | Exporter disabled, zero overhead, app starts normally |
| Endpoint set but unreachable | Bounded queue (max 512 records), short timeout (5s), drop on full. No memory leak, no thread exhaustion, app continues serving traffic. |
| Endpoint set and reachable | Normal OTLP export |

---

## 9. Agent Self-Check

- [ ] All log statements emit structured JSON with required schema fields
- [ ] No unstructured logging (raw println, string concatenation) remains
- [ ] Correlation IDs (TraceId, SpanId) present in request-scoped logs
- [ ] OTel SDK configured with OTLP exporter activated only when `OTEL_EXPORTER_OTLP_ENDPOINT` is set
- [ ] Graceful degradation: bounded queue, short timeouts, app runs fine without Collector
- [ ] No sensitive data (PAN, sort codes, NI numbers, emails) in log output
- [ ] Resource attributes (service.name, service.version, deployment.environment) set on all telemetry
- [ ] Context propagation implemented on inbound (extract) and outbound (inject) paths

---

## Areas for Specialist Extension

- **Platform Engineering** — OPAL query patterns, standard dashboards, alert routing
- **SRE** — SLO definitions, burn-rate alerting thresholds, on-call escalation paths
- **Security** — Audit event schema, security event tagging, retention periods
