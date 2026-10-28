---
name: otel-conventions
description: >
    BUK OTel implementation patterns — stack-specific guidance for applying the observability
    standard (barclays-buk-standards:observability). Covers SDK wiring, logging config, bridge patterns,
    context propagation, graceful degradation, and detection indicators across Spring Boot,
    Node.js, Python, and Go. Load alongside barclays-buk-standards:observability when implementing
    or reviewing observability in a specific stack.
user-invocable: false
---

# BUK OTel Implementation Conventions

> **Source:** BUK Observability Working Group
> **Owner:** BUK Retail CAPL
> **Review trigger:** When OTel SDK versions change or new stacks are adopted
> **Status:** Production

**Conventions version:** 1.0.0

This skill contains the HOW — stack-specific patterns for implementing the BUK observability standard. The WHAT (required schema, severity rules, sensitive data rules, phase gates) lives in `barclays-buk-standards:observability`.

## Quick Start

1. **Detect the stack** — look for `pom.xml` (Spring Boot), `package.json` (Node.js), `pyproject.toml` (Python), or `go.mod` (Go)
2. **Load the stack-specific file** — e.g. `spring-boot.md` for Java services
3. **Apply the bridge pattern** — add OTel as an export path alongside existing logging; never remove existing appenders
4. **Gate on environment** — use `OTEL_EXPORTER_OTLP_ENDPOINT` as the activation switch; absent = silent, zero overhead
5. **Verify with a real Collector** — use `docker-compose.verify.yaml` to run assertions against exported telemetry

## Supported Stacks

See sibling files for per-stack implementation details:
- `spring-boot.md` — Java with Spring Boot (Logback, MDC, Maven/Gradle)
- `nodejs.md` — Node.js with TypeScript (Pino/Winston, AsyncLocalStorage, npm/yarn)
- `python.md` — Python (structlog/stdlib, context vars, pip/poetry)
- `go.md` — Go (slog/zap, explicit context, go modules)

## Stack Detection

Before implementing, identify the repo's stack:

| Stack | Primary indicator |
|-------|-----------------|
| Spring Boot | `pom.xml` or `build.gradle` with `spring-boot-starter-*` |
| Node.js | `package.json` at root |
| Python | `requirements.txt`, `pyproject.toml`, or `setup.py` |
| Go | `go.mod` at root |

See each stack file's Detection Patterns section for secondary indicators (framework, build tool, application type).

## General Implementation Principles

**Bridge first:** If existing logging is configured, add OTel as an additional export path — never remove existing log destinations. Existing log pipelines (Splunk forwarders, custom appenders, file handlers) continue unchanged.

**Graceful degradation:** The OTel SDK MUST be configured so the app runs correctly with no Collector present. The `OTEL_EXPORTER_OTLP_ENDPOINT` env var is the activation gate — absent means silent and zero-overhead.

**Internal container registry:** When referencing Collector container images, always use `container-release.container-registry-non-prod.barcapint.com/external/docker.io/otel/opentelemetry-collector-contrib:0.149.0`. Never reference Docker Hub directly.

**Follow repo conventions:** Test framework, naming, file organisation, and import style MUST match the target repo's existing patterns. OTel plumbing should look native to the codebase.

## Verification Infrastructure

When implementing and setting up verification tests, create these files in `.reliability/` within the target repo:

**docker-compose.verify.yaml** — starts a real OTel Collector for component tests:
```yaml
services:
  otel-collector:
    image: container-release.container-registry-non-prod.barcapint.com/external/docker.io/otel/opentelemetry-collector-contrib:0.149.0
    volumes:
      - ./.reliability/collector-config.yaml:/etc/otel/config.yaml
      - ./.reliability/exports:/exports
    command: ["--config=/etc/otel/config.yaml"]
    ports:
      - "4317:4317"
      - "4318:4318"
```

**collector-config.yaml** — routes OTLP to file exports for test assertions:
```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:

exporters:
  file/traces:
    path: /exports/traces.json
  file/logs:
    path: /exports/logs.json

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [file/traces]
    logs:
      receivers: [otlp]
      processors: [batch]
      exporters: [file/logs]
```

Test assertions read `/exports/logs.json` and `/exports/traces.json` to verify schema correctness, correlation, and sensitive data absence.

## Implementation Sequence

When implementing observability from scratch:

1. **001** — Structured logging: configure the logging framework with OTel-native schema
2. **002** — Correlation IDs: inject TraceId/SpanId into logs from request context
3. **003** — Collector-ready: wire OTel SDK with OTLP exporter, env-var gated
4. **004** — Sensitive data guard: add test assertions that PAN/sort-code patterns are absent from exports
5. **005** — Capability attestation: component test with real Collector (docker-compose)

Then identify enrichment opportunities for additional migrations: async jobs, slow operations, business events, error enrichment, health check logging, circuit breaker state logging.

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] Correct stack-specific file loaded (Spring Boot / Node.js / Python / Go)
- [ ] Bridge pattern used — existing log destinations preserved, OTel added alongside
- [ ] `OTEL_EXPORTER_OTLP_ENDPOINT` is the activation gate — app runs cleanly without a Collector
- [ ] Container images reference internal registry (`container-release.container-registry-non-prod.barcapint.com`), not Docker Hub
- [ ] Verification test asserts on exported telemetry (reads `/exports/logs.json` or `/exports/traces.json`)
- [ ] Sensitive data patterns (PAN, sort code, account number, NI number, email) are not present in exported logs
- [ ] Implementation follows the target repo's existing code style, naming, and test framework
