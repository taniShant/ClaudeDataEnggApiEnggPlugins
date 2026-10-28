---
name: plan-performance
description: >
    Leads an interactive performance planning session for a greenfield service. Walks through
    one multichoice question per turn covering service tier, data access patterns, traffic shape,
    caching strategy, and memory constraints. Converges on a written performance target document.
user-invocable: false
owner: BUK Retail CAPL
review-trigger: When BUK performance tier thresholds or NFR standards change
---

# Plan — Performance

For greenfield services making upfront performance design decisions. Leads a session that converges on a performance target covering latency budgets, caching strategy, and data access patterns.

> **Skills needed:** Load `barclays-buk-standards:performance` alongside this skill.
> Report placeholder flags if unavailable — tier thresholds will be advisory only.

---

## Inputs

```
CODE_PATH:  /absolute/path/to/service   (default: current working directory)
```

---

## Output

`.reliability/performance-target.md` documenting agreed service tier, caching strategy, data access patterns, and memory constraints.

---

## Format rule

Every question must be a numbered multichoice list. Always mark one option **(recommended)**. Always offer a custom/different option. One question per response — never batch questions.

---

## Step 1: Silent scan

Scan the repo to detect stack, build tool, module structure, and any existing caching configuration, database clients, or HTTP clients. Do NOT output anything.

---

## Step 2: Walk the decision tree

Ask one question at a time, wait for response, then continue:

**Question 1 — Service tier:**
```
What is this service's API tier? This determines the latency budget.
1. xAPI — customer-facing, synchronous, strict latency target (recommended if serving UI)
2. pAPI — partner or process API, moderate latency tolerance
3. sAPI — system or async API, batch-friendly
4. Not sure / internal only — describe the traffic pattern
```

**Question 2 — Data access pattern:**
```
How does this service read and write data?
1. Relational database (JPA/Hibernate, SQLAlchemy, GORM, Prisma) (recommended if data has structure)
2. Document store (DynamoDB, MongoDB, CosmosDB)
3. External API calls only — no owned database
4. Multiple — describe
```

**Question 3 — Traffic pattern:**
```
How does this service receive work?
1. Synchronous HTTP requests — request/response (recommended for APIs)
2. Async message consumer — Kafka, SQS, or similar
3. Scheduled batch job — cron or trigger-based
4. Mixed — describe
```

**Question 4 — Caching strategy:**
```
Does this service need caching for frequently repeated reads?
1. No caching needed — data changes too frequently or reads are not repeated (recommended if uncertain)
2. In-process cache (Caffeine, node-cache, functools.lru_cache) — simple, no network hop
3. Distributed cache (Redis, ElastiCache) — shared across instances
4. CDN / edge cache — for static or infrequently changing responses
```

**Question 5 — Memory constraints:**
```
Will this service process large payloads or streams?
1. No — requests and responses are small and bounded (recommended if standard API)
2. Yes — handles file uploads, large JSON payloads, or streaming responses
3. Yes — reads from external streams (S3, Kafka, external APIs) that could be large
4. Not sure — describe the largest expected payload
```

---

## Step 3: Convergence summary

Present a summary of agreed decisions. Explain what the performance target gives the team — known budget constraints, caching approach, and patterns to avoid. Ask for approval.

---

## Step 4: Write the target

On approval, write `.reliability/performance-target.md`:

```markdown
---
service_tier: <xapi|papi|sapi|internal>
data_access: <relational|document|external-api|mixed>
traffic_pattern: <http|async-consumer|batch|mixed>
caching_strategy: <none|in-process|distributed|cdn>
large_payload_risk: <true|false>
---

# Performance Target

## Decisions

- **Service tier:** [tier] — latency budget: [threshold from barclays-buk-standards:performance, or "advisory — standards not yet populated"]
- **Data access:** [pattern]
- **Traffic pattern:** [pattern]
- **Caching:** [strategy]
- **Large payload risk:** [yes/no]

## Patterns to Enforce

Based on the above decisions, enforce these patterns in code review:

| Pattern | Why it applies here |
|---------|-------------------|
| [e.g. Pagination on all DB queries] | [relational DB with high row count risk] |
| [e.g. io.LimitReader / maxBytes on stream reads] | [large payload risk confirmed] |
| [e.g. Compile regex/templates at init] | [high-traffic xAPI tier — per-request compilation would spike CPU] |

## Patterns Not Applicable

| Pattern | Why it is excluded |
|---------|-------------------|
| [e.g. Distributed cache] | [in-process cache sufficient — single-instance deployment] |
```

After writing, suggest next steps.

---

## Backward compatibility

If `.reliability/performance-target.md` already exists:
- Read it and understand agreed decisions
- Report what has already been decided and ask whether to update specific decisions or proceed with a review
- Do NOT overwrite without explicit confirmation

---

## Suggested Next Steps

Always end with 2–5 numbered options. Examples:

```
**Suggested next steps:**
1. Review performance — run /barclays-buk-reliability-engineer:review-performance to scan existing code against this target
2. Design another area — run /barclays-buk-reliability-engineer:plan resilience|config|observability
3. Review the target — inspect .reliability/performance-target.md before starting
4. Something different — describe what you'd like to do
```

---

## Flags

State any of the following that apply (or "None identified"):

**Placeholder skills:**
- `barclays-buk-standards:performance` is a placeholder — latency budget thresholds are advisory only; actual ms targets unavailable

**Missing or ambiguous inputs:**
- CODE_PATH not provided — scanned current working directory

---

## Agent Self-Check

- [ ] Silent scan completed before asking any questions
- [ ] Each question presented one at a time with numbered options and a recommendation
- [ ] All 5 decision questions answered before writing the target
- [ ] Convergence summary shown and approved before writing
- [ ] `.reliability/performance-target.md` written with correct frontmatter
- [ ] Backward compatibility: existing target read and preserved unless explicitly overwritten
- [ ] Placeholder skills flagged if barclays-buk-standards:performance is unavailable
