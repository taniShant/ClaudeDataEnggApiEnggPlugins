# Performance — Detailed Standards

The agent reviews code and configuration for performance risks. No automated implementation — findings are advisory with remediation guidance.

---

## API Tier Latency Budget

BUK DAF services operate in a cascade. Each tier's budget includes downstream time.

| Tier | Target | Risk if breached |
|------|--------|-----------------|
| **xAPI** (Experience) | < 500ms | Thread exhaustion at channel; customer-facing timeout |
| **pAPI** (Process) | < 300ms | xAPI misses its 500ms budget |
| **sAPI** (System) | < 100ms (aspire < 20ms) | Cascade failure through pAPI → xAPI |
| **API Connect timeout** | ≤ 500ms | Long-lived threads exhaust pool |

The agent flags any call chain that structurally cannot meet its tier's budget.

---

## Patterns Detected

### Database

| Pattern | Severity | What the agent looks for |
|---------|----------|------------------------|
| N+1 queries | High | `findById` in a loop, lazy-loaded collections iterated without batch fetch |
| Unbounded result sets | High | Queries with no `LIMIT` / pagination, `findAll()` on large tables |
| Missing indexes | Medium | Filter/sort columns with no corresponding index in migrations |

### I/O

| Pattern | Severity | What the agent looks for |
|---------|----------|------------------------|
| Sync I/O on request thread | High | Blocking HTTP calls, file reads on critical path |
| No timeout on outbound calls | High | HTTP clients, DB pools, Kafka consumers with no timeout config |

### Caching

| Pattern | Severity | What the agent looks for |
|---------|----------|------------------------|
| Repeated identical calls | Medium | Same query/API call executed multiple times per request |
| No TTL on cache | Medium | Cache entries that never expire (stale data risk) |
| Cache writes without invalidation | High | Code writes/updates a DB entity that is also read via a cache elsewhere, but the write path has no cache invalidation call (`cache.del()`, `cache.evict()`, `invalidate()`) or TTL short enough to limit stale window |

### Memory Safety

| Pattern | Severity | What the agent looks for |
|---------|----------|------------------------|
| Unbounded stream read | Critical | `io.ReadAll` / `ioutil.ReadAll` (Go), `StreamUtils.copyToString` (Java), `response.text()` / `await body.text()` (Node.js), `response.read()` (Python) with no size guard (`io.LimitReader`, `maxBytes` config) in memory-constrained runtimes (Lambda, container with memory limit) |
| Large response buffering | High | HTTP response body read entirely into memory without streaming or chunked processing when response size is unbounded |

### Repeated Computation

| Pattern | Severity | What the agent looks for |
|---------|----------|------------------------|
| Per-request compilation | Critical | `expr.Compile`, `regexp.Compile`, `regexp.MustCompile` (Go), `Pattern.compile` (Java), `new RegExp()` (JS), `re.compile` (Python), `template.Parse`, or schema validator initialisation called inside a per-request function rather than at package/module init |
| Redundant validation setup | High | Schema validators, JSON schema compilation, XML parser initialisation, or expression program compilation repeated per invocation without caching the compiled result |

### Bounded Collections

| Pattern | Severity | What the agent looks for |
|---------|----------|------------------------|
| Unbounded append to transport-limited store | High | `append()` (Go) or `.push()` (JS) in a loop with no size check, where the collection is serialised to a size-limited transport (Lex session attributes 12KB, DynamoDB item 400KB, HTTP header 8KB, SQS message 256KB) |
| Growing map without eviction | High | Map/dict that grows with request volume and has no TTL, max-size, or eviction policy — memory leak in long-running processes |

### Speculative Execution Waste

| Pattern | Severity | What the agent looks for |
|---------|----------|------------------------|
| Unconditional expensive call | Medium | Expensive operation (LLM inference, model invocation, remote service call) always executed even when a cheaper path might suffice or the result may be discarded. Advisory — requires judgment. |
| Unused computation on error path | Medium | Results computed eagerly that are only consumed in non-error paths, wasting resources when errors are common |

### Serialisation Overhead

| Pattern | Severity | What the agent looks for |
|---------|----------|------------------------|
| Redundant encoding layers | High | Double-serialisation (JSON inside JSON, struct → JSON → base64 → JSON) near transport size limits. Base64 adds +33% overhead per layer. |
| Unnecessary marshal/unmarshal cycles | Medium | Data deserialised from one format only to be immediately re-serialised into the same format with no transformation in between |

---

## Load Testing

The agent does not run load tests but flags their absence:
- VPT (Volume and Performance Testing) is a mandatory exit gate for production release
- All in-scope OP codes must be exercised
- Approved tools: LoadRunner, JMeter (backend); Lighthouse / Chrome DevTools (web frontend)

---

## Skill Status

Performance review relies on `barclays-buk-standards:performance`. That skill is partially populated (latency budgets and VPT exit criteria are defined; throughput targets, autoscaling thresholds, and cache TTL conventions are not yet). The agent reviews against what exists and reports gaps in its Flags section.
