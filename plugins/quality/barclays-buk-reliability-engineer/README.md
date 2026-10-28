# barclays-buk-reliability-engineer

> **Status: Draft**

Makes sure solutions are sustainable services. Covers four capability areas: **Performance, Observability, Resilience, and Config Management**.

In review mode (default), scans the codebase and produces prioritised Critical/High/Medium findings. In plan mode, leads an interactive planning session for greenfield services. In implement mode, applies observability improvements with a red-green verification loop.

## Workflow Position

```
Solution Architect / API Engineer → Reliability Engineer → [gates release]
```

## Command Surface

### Review commands

| Command | Description |
|---------|-------------|
| `/barclays-buk-reliability-engineer:review` | Review all four capability areas in parallel |
| `/barclays-buk-reliability-engineer:review observability` | Review observability only |
| `/barclays-buk-reliability-engineer:review performance` | Review performance only |
| `/barclays-buk-reliability-engineer:review resilience` | Review resilience only |
| `/barclays-buk-reliability-engineer:review config` | Review config management only |
| `/barclays-buk-reliability-engineer:review-observability` | Review observability (direct skill invocation) |
| `/barclays-buk-reliability-engineer:review-performance` | Review performance (direct skill invocation) |
| `/barclays-buk-reliability-engineer:review-resilience` | Review resilience (direct skill invocation) |
| `/barclays-buk-reliability-engineer:review-config` | Review config management (direct skill invocation) |

### Plan commands

| Command | Description |
|---------|-------------|
| `/barclays-buk-reliability-engineer:plan-observability` | Interactive observability planning session for a greenfield service |
| `/barclays-buk-reliability-engineer:plan-performance` | Interactive performance planning session for a greenfield service |
| `/barclays-buk-reliability-engineer:plan-resilience` | Interactive resilience planning session for a greenfield service |
| `/barclays-buk-reliability-engineer:plan-config` | Interactive config management planning session for a greenfield service |

### Implementation commands

| Command | Description |
|---------|-------------|
| `/barclays-buk-reliability-engineer:implement` | Implement the next observability migration |
| `/barclays-buk-reliability-engineer:implement --all` | Implement all remaining migrations in one shot |
| `/barclays-buk-reliability-engineer:implement 003` | Implement a specific migration by number |
| `/barclays-buk-reliability-engineer:status` | Show current observability maturity without running tests |

## Capability Areas

### Observability ✓
Reviews and implements BUK OTel conventions:
- **Logging phase**: Structured JSON schema, OTel-native fields, severity levels
- **Correlation**: trace_id/span_id in request-scoped logs
- **Collector-ready**: OTLP exporter wired, activated by `OTEL_EXPORTER_OTLP_ENDPOINT` env var only
- **Sensitive data**: No PAN, sort codes, NI numbers, or email in log output
- **Capability attestation**: Component test with real OTel Collector proves end-to-end observability

Observability maturity progresses through three phases (logging → tracing → metrics).

Both review and plan (greenfield) are supported. Stack coverage: Spring Boot, Node.js, Python, Go.

### Performance _(review + plan — review findings only)_
Pattern-based review against code heuristics. Latency budget enforcement against `barclays-buk-standards:performance` thresholds is aspirational pending that skill being populated.

- N+1 queries and unbounded result sets
- Synchronous I/O on critical request paths
- Missing or misconfigured caching
- Latency budget compliance (xAPI/pAPI/sAPI thresholds)
- Memory safety: unbounded stream reads in memory-constrained runtimes
- Repeated computation: per-request regex/template/expression compilation
- Bounded collections: growth without cap near transport size limits (Lex 12KB, DynamoDB 400KB)
- Speculative execution waste: expensive calls performed unconditionally
- Serialisation overhead: redundant encoding layers (JSON → base64 → JSON)

### Resilience _(review + plan — review findings only)_
Pattern-based review. No automated implementation.

- Circuit breakers and timeouts on outbound dependencies
- Retry logic with exponential backoff and max-attempts ceiling
- Graceful degradation when non-critical dependencies are unavailable
- Inbound rate limiting
- Per-call context deadlines on every outbound call (not just runtime-level timeout)
- Defensive nil-check on SDK/API response pointer fields
- Application-level retry distinct from SDK transport retry
- Fire-and-forget error handling: errors deferred without logging or DLQ
- Async message consumers without failure visibility (no retry, no DLQ)
- Resource acquire without release (connection/handle leaks)
- No backpressure on unbounded queue consumption
- Batch processing: pre-flight validation, per-record error handling, phase markers
- External API response schema validation before property access

### Config Management _(review + plan — review findings only)_
Pattern-based review. No automated implementation.

- No hardcoded environment-specific values in source
- Secrets retrieved from CSM at runtime
- Feature flags for environment-specific behaviour
- Documented config keys
- Config validation at startup with fail-fast on missing required values
- No TODO/FIXME/HACK markers in production code paths

## Plugin structure

```
skills/
  otel-conventions/          ← OTel implementation patterns (Spring Boot, Node.js, Python, Go)
  review-observability/      ← Observability review skill
  review-performance/        ← Performance review skill
  review-resilience/         ← Resilience review skill
  review-config/             ← Config management review skill
  plan-observability/        ← Observability planning session skill
  plan-performance/          ← Performance planning session skill
  plan-resilience/           ← Resilience planning session skill
  plan-config/               ← Config management planning session skill
  implement/                 ← Observability implementation skill
  status/                    ← Observability status reporting skill
commands/
  review.md                  ← Orchestrates all 4 review skills in parallel
  review-observability.md    ← Direct invocation of review-observability skill
  review-performance.md      ← Direct invocation of review-performance skill
  review-resilience.md       ← Direct invocation of review-resilience skill
  review-config.md           ← Direct invocation of review-config skill
  plan-observability.md      ← Direct invocation of plan-observability skill
  plan-performance.md        ← Direct invocation of plan-performance skill
  plan-resilience.md         ← Direct invocation of plan-resilience skill
  plan-config.md             ← Direct invocation of plan-config skill
  implement.md               ← Direct invocation of implement skill
  status.md                  ← Direct invocation of status skill
```

## Dependencies

- `buk-standards` — provides `observability`, `performance`, and `security` skills
  - `barclays-buk-standards:observability` — full ✓
  - `barclays-buk-standards:performance` — placeholder (latency budget checks are best-effort until populated)
  - `barclays-buk-standards:security` — placeholder
- Plugin-local skill: `otel-conventions` — stack-specific OTel implementation patterns (Spring Boot, Node.js, Python, Go)

## State files

When working on a service, skills read and write `.reliability/` in the target repo:

| File | Purpose |
|------|---------|
| `.reliability/observability-target.md` | Agreed observability decisions (schema, strategy, stack) |
| `.reliability/performance-target.md` | Agreed performance decisions (tier, caching, data access) |
| `.reliability/resilience-target.md` | Agreed resilience decisions (circuit breakers, retry, degradation) |
| `.reliability/config-target.md` | Agreed config management decisions (secrets, flags, validation) |
| `.reliability/state.yaml` | Per-migration status (planned / implemented / verified) |
| `.reliability/changelog/###__*.md` | Migration declarations — one file per concern |
| `.reliability/docker-compose.verify.yaml` | OTel Collector for verification tests (created on first implement) |
| `.reliability/collector-config.yaml` | Collector pipeline config (created on first implement) |

If these files already exist, skills pick up where the previous session left off — they never reset state without being asked.
