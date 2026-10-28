---
name: review-performance
description: >
    Scans a service codebase for performance issues and produces a prioritised findings report
    covering query patterns, synchronous I/O, caching, latency budgets, memory safety,
    and serialisation overhead against BUK performance standards.
user-invocable: false
owner: BUK Retail CAPL
review-trigger: When barclays-buk-standards:performance thresholds are updated
---

# Review — Performance

> **Skills needed:** Load `barclays-buk-standards:performance` alongside this skill.
> Report placeholder flags if unavailable — latency budget enforcement is best-effort without it.

---

## Inputs

```
CODE_PATH:  /absolute/path/to/service   (default: current working directory)
```

---

## Output

A focused performance findings report covering:
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

## Step 2: Assess performance

Scan for:

- **Database patterns**: N+1 queries (`findById` in loops, lazy-loaded relations), unbounded result sets (missing pagination), missing indexes (no `@Index`, no `CREATE INDEX` in migrations)
- **Synchronous I/O on critical path**: blocking HTTP calls that could be async, synchronous file reads on request threads
- **Caching gaps**: repeated identical queries or external calls with no cache layer, missing TTL on existing caches, writes to cached entities without cache invalidation call
- **Latency budget compliance**: compare service type (xAPI/pAPI/sAPI) against `barclays-buk-standards:performance` thresholds
- **Memory safety**: unbounded reads from external streams (`io.ReadAll`, `ioutil.ReadAll` in Go; `StreamUtils.copyToString` in Java; `response.text()` in Node.js; `response.read()` in Python) in memory-constrained runtimes without size guards (`io.LimitReader`, `maxBytes`)
- **Repeated computation**: expression/regex/template/schema compilation inside per-request functions instead of at init time. Look for `Compile()`, `Parse()`, `new RegExp()` inside handlers — these should be cached at package/module level.
- **Bounded collections**: data structures that grow without cap when serialised to size-limited transports (Lex session attributes 12KB, DynamoDB item 400KB, HTTP header 8KB). Flag `append()` / `.push()` in loops with no size check.
- **Speculative execution waste**: expensive operations (LLM inference, model invocations, remote service calls) performed unconditionally when a cheaper path might suffice or the result may be discarded
- **Serialisation overhead**: redundant encoding layers (JSON → base64 → JSON, double-serialisation) especially near transport size limits. Base64 adds +33% overhead per layer.

---

## Step 3: Produce findings report

Severity definitions:

| Priority | Definition |
|----------|-----------|
| **Critical** | Production outage risk; unbounded memory use in constrained runtime; per-request compilation causing CPU spikes |
| **High** | Performance bottleneck affecting latency SLA; N+1 queries; missing pagination on large tables |
| **Medium** | Improvement opportunity — meaningful gain but no immediate risk |

Report format:

```markdown
# Performance Review — [service name]

**Date:** [date]
**Stack:** [stack] ([build tool])
**Modules:** [list]

---

## Summary

[2–3 sentence overview: what is the most significant performance risk? Is the service within its latency budget?]

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

**Placeholder skills:**
- `barclays-buk-standards:performance` is a placeholder — latency budget enforcement is best-effort based on code patterns only; tier thresholds (xAPI/pAPI/sAPI ms targets) unavailable

**Missing or ambiguous inputs:**
- CODE_PATH not provided — skill scanned current working directory

**Decisions made under uncertainty:**
- Stack detected as [X] based on [indicator] — if incorrect, specify and re-run

---

## Agent Self-Check

- [ ] Stack detected
- [ ] All 9 performance scan patterns checked
- [ ] Latency budget compliance checked (flagged as best-effort if barclays-buk-standards:performance is a placeholder)
- [ ] Memory safety scan completed for detected stack's I/O primitives
- [ ] Placeholder skills flagged if barclays-buk-standards:performance is unavailable
