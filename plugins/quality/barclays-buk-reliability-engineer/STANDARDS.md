# barclays-buk-reliability-engineer — Standards

---

## Mission

BUK services must be deployable, monitorable, and recoverable without tribal knowledge. This plugin exists as a plugin rather than documentation because it mechanically scans code, reports prioritised findings with file-level remediation, and — for observability — writes the fix. Documentation tells engineers what to do; this plugin does it or proves it's missing.

---

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Service codebase | Current working directory or `CODE_PATH` | Yes |
| `.reliability/observability-target.md` | Previous plan-observability session | No — skill scans from scratch if absent |
| `.reliability/performance-target.md` | Previous plan-performance session | No — skill reviews without a target if absent |
| `.reliability/resilience-target.md` | Previous plan-resilience session | No — skill reviews without a target if absent |
| `.reliability/config-target.md` | Previous plan-config session | No — skill reviews without a target if absent |
| `.reliability/state.yaml` | Previous implement session | No — skill starts from migration 001 if absent |
| `.reliability/changelog/` | Previous implement sessions | No — skill plans the next migration if absent |
| Focus area | User command argument (`observability`, `performance`, `resilience`, `config`, `all`) | No — defaults to `all` |
| Mode | User command (`review`, `review-*`, `plan-*`, `implement`, `status`) | No — defaults to `review` |

---

## Outputs

| Mode | Artifacts created or modified |
|------|-------------------------------|
| **Review** | Prioritised findings report (Critical/High/Medium), deployment readiness checklist, suggested next steps |
| **Implement** | Application code changes, verification test(s), `.reliability/state.yaml` update, `.reliability/changelog/<NNN>__<title>.md` |
| **Plan — observability** | `.reliability/observability-target.md` capturing agreed schema, strategy, stack, and phase decisions |
| **Plan — performance** | `.reliability/performance-target.md` capturing agreed tier, caching, and data access decisions |
| **Plan — resilience** | `.reliability/resilience-target.md` capturing agreed circuit breaker, retry, and degradation decisions |
| **Plan — config** | `.reliability/config-target.md` capturing agreed secrets, feature flag, and validation decisions |
| **Status** | Console output only — no files created or modified |

First-run implement also creates: `.reliability/docker-compose.verify.yaml`, `.reliability/collector-config.yaml`, `.reliability/exports/.gitignore`

---

## Standards Enforced

Each standard has a mechanical check — the agent either passes or reports a finding.

### Observability

| Standard | Passing means | Severity if missing |
|----------|--------------|---------------------|
| Structured JSON to stdout | All log statements emit JSON with Timestamp, SeverityText, Body, Resource.service.name | High |
| No unstructured logging | Zero `println`, `System.out`, or string-concatenation log statements | High |
| Correlation IDs | Request-scoped logs contain TraceId and SpanId from propagated context | High |
| Collector-ready | OTLP exporter activates only when `OTEL_EXPORTER_OTLP_ENDPOINT` is set; silent when absent | High |
| Sensitive data absence | PAN, sort code, account number, NI number, email never appear in log output | Critical |
| Capability attestation | Component test with real OTel Collector proves structured, correlated logs reach the Collector | High |
| Trace coverage consistent | All I/O-performing methods in a package are traced if any sibling method is traced | Critical |
| Correlation IDs in outbound calls | TraceId propagated in outbound HTTP headers (`traceparent`) and message metadata, not just log fields | High |
| Operational signals consistent | All entry points of the same type emit the same operational signals (duration, error classification, metrics) | High |
| Structured error context in catch blocks | Catch blocks log correlation ID, operation name, stack trace, and input context — not just error message | High |

Detail: [docs/observability.md](docs/observability.md)

### Performance

| Standard | Passing means | Severity if missing |
|----------|--------------|---------------------|
| No N+1 queries | No `findById` in loops or lazy-loaded collections iterated without fetch join | High |
| Bounded result sets | All queries use pagination or explicit LIMIT | Medium |
| No sync I/O on critical path | Blocking HTTP/file calls on request threads are async or off-thread | High |
| Latency budget compliance | Service type (xAPI/pAPI/sAPI) meets tier threshold | High |
| Caching where repeated | Identical external calls or queries use a cache with TTL; writes to cached entities have invalidation calls | Medium |
| No unbounded stream reads | `io.ReadAll` / equivalent in memory-constrained runtimes uses `io.LimitReader` or size cap | Critical |
| No per-request compilation | Regex/template/expression compiled at init, not inside request handlers | Critical |
| Bounded collections for limited transports | Append loops have size checks when target is size-limited (Lex 12KB, DynamoDB 400KB) | High |
| No speculative execution waste | Expensive calls not performed unconditionally when a cheaper path exists or result may be discarded (advisory) | Medium |
| No redundant serialisation layers | No double-encoding (JSON → base64 → JSON) near transport size limits | High |

Detail: [docs/performance.md](docs/performance.md)

### Resilience

| Standard | Passing means | Severity if missing |
|----------|--------------|---------------------|
| Circuit breakers on outbound deps | Every external dependency call is wrapped with a circuit breaker | High |
| Timeouts configured | No HTTP client, DB pool, or consumer has infinite or missing timeout | High |
| Retry with backoff | Transient-failure retries use exponential backoff + jitter + max-attempts ceiling | Medium |
| Graceful degradation | Service returns partial/cached response when non-critical deps are down | Medium |
| Rate limiting | Inbound request protection is configured | Medium |
| Per-call context deadlines | Every outbound call has its own timeout, not just the runtime-level deadline (Lambda 60s) | Critical |
| Defensive response handling | SDK/API pointer fields nil-checked before dereference — no panics on nil response fields | Critical |
| Application-level retry | Domain transient failures (throttling, model timeout, empty response) retried separately from SDK transport retry | High |
| No fire-and-forget error handling | Errors deferred to queues/async handlers are logged with context at deferral point with DLQ or alert | High |
| Async consumers have failure visibility | Message consumers have retry, dead-letter queue, or error logging at consumption point | High |
| Resource acquire has matching release | Connections/handles/streams released in defer/finally/context-manager | High |
| Backpressure on queue consumption | Unbounded consumers have concurrency limiter or buffer when framework doesn't handle it | High |
| Batch pre-flight validation | Batch jobs validate preconditions before processing loop | High |
| Batch per-record error handling | Loop bodies have try/catch — one bad record doesn't abort entire batch | High |
| Batch job phase markers | Long-running jobs log START/END/FAILED at phase boundaries | Medium |
| External API schema validation | External API responses validated before property access | High |

Detail: [docs/resilience.md](docs/resilience.md)

### Config Management

| Standard | Passing means | Severity if missing |
|----------|--------------|---------------------|
| No hardcoded env values | Zero URLs, hostnames, ports, or environment names as string literals in source | High |
| Secrets from CSM | Passwords, API keys, tokens fetched from secrets manager at runtime, not in config files | Critical |
| Feature flags | Environment-specific behaviour uses flags, not code branching | Medium |
| Config documented | Every config key has a description or rationale | Medium |
| Config validated at startup | Required env vars checked early with clear failure messages — no silent empty strings at runtime | Critical |
| No TODO/FIXME in production paths | Incomplete implementation markers absent from production code (tests and docs excluded) | High |

Detail: [docs/config-management.md](docs/config-management.md)

---

## Tools and Tech

### Skills

| Skill | Purpose | Loaded by |
|-------|---------|-----------|
| `review-observability` | Observability review scan patterns and report | `review-observability` command, `review` orchestrator |
| `review-performance` | Performance review scan patterns and report | `review-performance` command, `review` orchestrator |
| `review-resilience` | Resilience review scan patterns and report | `review-resilience` command, `review` orchestrator |
| `review-config` | Config management review scan patterns and report | `review-config` command, `review` orchestrator |
| `plan-observability` | Observability planning session and target file | `plan-observability` command, `design` orchestrator |
| `plan-performance` | Performance planning session and target file | `plan-performance` command, `design` orchestrator |
| `plan-resilience` | Resilience planning session and target file | `plan-resilience` command, `design` orchestrator |
| `plan-config` | Config management planning session and target file | `plan-config` command, `design` orchestrator |
| `implement` | Observability migration implementation and red-green loop | `implement` command |
| `status` | Observability phase and migration progress reporting | `status` command |
| `otel-conventions` | Stack-specific OTel implementation patterns (Spring Boot, Node.js, Python, Go) | `review-observability`, `plan-observability`, `implement` commands |

### External standards loaded at runtime

| Skill | Source | Purpose |
|-------|--------|---------|
| `barclays-buk-standards:observability` | `buk-standards` plugin | Normative standard — schema rules, phase gates, severity definitions |
| `barclays-buk-standards:performance` | `buk-standards` plugin | Latency budget thresholds (placeholder — best-effort until populated) |
| `barclays-buk-standards:security` | `buk-standards` plugin | Security config checks (placeholder) |

### External infrastructure

| Dependency | Used when | Why |
|------------|-----------|-----|
| OTel Collector container (`container-release.container-registry-non-prod.barcapint.com/external/docker.io/otel/opentelemetry-collector-contrib:0.149.0`) | Implement mode, migration 005+ | Capability attestation requires a real Collector to prove end-to-end telemetry; internal registry only |
| Docker / docker-compose | Implement mode (full verification) | Runs the Collector container; schema-only fallback available when Docker is unavailable |

---

## Handoff Criteria

Before this plugin is ready for use by other teams, the contributing engineer must complete:

| Gate | Why |
|------|-----|
| `review-*` skills tested against a real Spring Boot service | Spring Boot is the primary BUK stack; all 4 review skills must produce correct findings |
| `review-*` skills tested against a real Node.js service | Second most common stack; validates stack detection and pattern matching across languages |
| All commands exercised (`review`, `review-*`, `design`, `design-*`, `implement`, `status`) | Each skill has distinct logic paths; untested skills will ship broken |
| Implement red-green loop verified (test fails → skill fixes → test passes) | The core value proposition of the implement skill; if the loop doesn't converge, the plugin produces broken code |
| `barclays-buk-standards:observability` skill reviewed by Principal Engineer | This skill defines what "correct observability" means for all BUK services; incorrect rules propagate bad practice at scale |
| Docker-unavailable fallback confirmed | Many developer laptops and CI runners lack Docker; schema-only mode must degrade gracefully without error |
| `plugin.json` version matches STANDARDS.md and README.md state | Version drift between metadata and documentation creates confusion about what's shipped |
| Plugin tester score 90+ (`/test-plugin ./plugins/quality/barclays-buk-reliability-engineer`) | BUK marketplace quality gate — ensures structural correctness of the plugin |

---

## Definition of Done

A reviewer confirms the plugin is shippable when all of the following are true:

- [ ] Every standard in "Standards Enforced" above has a corresponding check in the relevant review skill
- [ ] The `implement` skill produces code that passes the migration's own verification test without manual intervention
- [ ] Every skill reports placeholder skills in its Flags section (Principle 5 — transparent about what it doesn't know)
- [ ] Every skill suggests next steps but never blocks on missing upstream artifacts (Principle 7)
- [ ] State files (`.reliability/`) are backward-compatible — existing state from a previous session is picked up, never reset
- [ ] No references to Docker Hub directly — all container images use the internal registry
- [ ] Sensitive data patterns (PAN, sort code, NI number, email) are asserted absent in every verification test that touches log output
- [ ] README.md, STANDARDS.md, and `plugin.json` are internally consistent (version, capability list, command list)
