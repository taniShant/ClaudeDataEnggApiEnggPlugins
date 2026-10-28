---
name: review-observability
description: >
    Scans a service codebase for observability gaps and produces a prioritised findings report
    covering structured logging, OTel SDK wiring, correlation IDs, sensitive data risks,
    and phase gate status against BUK OTel conventions.
user-invocable: false
owner: BUK Retail CAPL
review-trigger: When barclays-buk-standards:observability phase gate criteria change
---

# Review — Observability

> **Skills needed:** Load `barclays-buk-standards:observability` and `otel-conventions` alongside this skill.
> Report placeholder flags if either is unavailable.

---

## Inputs

```
CODE_PATH:  /absolute/path/to/service   (default: current working directory)
```

---

## Output

A focused observability findings report covering:
- Prioritised findings table (Critical / High / Medium)
- Phase gate status (logging → tracing → metrics)
- Observability detail section
- Suggested next steps

---

## Step 1: Silent scan

Use Glob, Read, Bash, and Grep. Output nothing during this phase.

Detect stack and build tool:
- `pom.xml` / `build.gradle` → Spring Boot, Maven/Gradle
- `package.json` → Node.js
- `go.mod` → Go
- `requirements.txt` / `pyproject.toml` → Python

Load the `otel-conventions` skill's stack-specific file for the detected stack.

If `.reliability/observability-target.md` exists, read it — understand agreed schema, strategy, and current phase progress.

---

## Step 2: Assess observability

Scan for:

- **Logging schema**: structured JSON? OTel-native fields? ECS? Unstructured println/string-concatenation?
- **Correlation IDs**: trace_id/span_id in request-scoped logs? MDC configured? AsyncLocalStorage?
- **Collector readiness**: OTLP exporter wired? `OTEL_EXPORTER_OTLP_ENDPOINT` env-var gated?
- **Sensitive data risks**: any log statement that could emit PAN, sort codes, account numbers, NI numbers, or email
- **Health and readiness endpoints**: implemented? Return meaningful status?
- **Missing observability opportunities**: async/background jobs, Kafka consumers, outbound calls without correlation, exception handlers logging raw stack traces, circuit breaker state
- **Trace coverage consistency**: if sibling methods in the same package are traced, ALL I/O-performing methods in that package must also be traced. Flag any method that performs outbound I/O (HTTP calls, DB writes, SDK calls) without a span when its siblings have spans.
- **Correlation ID in outbound requests**: correlation IDs (TraceId, SpanId) must appear not just in log fields but also in outbound HTTP headers (`traceparent`) and message metadata (Kafka headers, SQS attributes). Flag when logs have trace context but outbound calls do not propagate it.
- **Consistency of operational signals**: if some entry points of the same type (Lambda handlers, HTTP endpoints, Kafka consumers) emit a signal (duration log, error classification, metric), then ALL entry points of that type must emit the same signal. Flag inconsistency.
- **Structured error context in catch blocks**: `catch`/`except`/`recover` blocks that log only the error message without correlation ID, operation name, stack trace, and input context. Flag catch blocks that would make incidents undiagnosable.

**Critical:** Structured JSON alone does NOT complete the logging phase. Collector integration (OTLP exporter, env-var gated) and a capability attestation test are required.

Assess against the phase gates in `barclays-buk-standards:observability`. If `.reliability/observability-target.md` exists, report current phase and what remains to reach the next phase.

---

## Step 3: Produce findings report

Severity definitions:

| Priority | Definition |
|----------|-----------|
| **Critical** | Regulatory risk (sensitive data in logs), security vulnerability, production outage risk |
| **High** | Missing observability making failures undetectable; collector not wired |
| **Medium** | Improvement opportunity — meaningful benefit but no immediate risk |

Report format:

```markdown
# Observability Review — [service name]

**Date:** [date]
**Stack:** [stack] ([build tool])
**Modules:** [list]
**Observability phase:** [logging | tracing | metrics] — [pending / in-progress / complete]

---

## Summary

[2–3 sentence overview: what is the current observability posture? What is the most important gap?]

---

## Findings

| Priority | Finding | File / Location | Recommendation |
|----------|---------|-----------------|---------------|
| Critical | | | |
| High | | | |
| Medium | | | |

---

## Observability Detail

[Phase gate table showing which of the 5 logging criteria are met / unmet. Reference barclays-buk-standards:observability criteria.]

| Gate criterion | Status | Notes |
|---------------|--------|-------|
| Structured JSON to stdout | ✅ / ❌ | |
| No unstructured logging | ✅ / ❌ | |
| Correlation IDs in request-scoped logs | ✅ / ❌ | |
| Collector-ready (OTLP exporter, env-var gated) | ✅ / ❌ | |
| Capability attestation test with real Collector | ✅ / ❌ | |

---

## Suggested Next Steps

[3–5 numbered options — never require a specific path]
```

---

## Flags

State any of the following that apply (or "None identified"):

**Placeholder skills:**
- `barclays-buk-standards:observability` is a placeholder — phase gate checks use code patterns only; normative schema rules unavailable
- `otel-conventions` unavailable — stack-specific patterns not applied

**Missing or ambiguous inputs:**
- No `.reliability/observability-target.md` found — assessment based on code scan only; no agreed decisions to compare against
- CODE_PATH not provided — skill scanned current working directory

**Decisions made under uncertainty:**
- Stack detected as [X] based on [indicator] — if incorrect, specify and re-run

---

## Agent Self-Check

- [ ] Stack detected and stack-specific `otel-conventions` file loaded
- [ ] All 10 observability scan patterns checked
- [ ] Phase gate table populated (all 5 criteria assessed)
- [ ] Sensitive data scan completed
- [ ] Placeholder skills flagged if barclays-buk-standards:observability is unavailable
