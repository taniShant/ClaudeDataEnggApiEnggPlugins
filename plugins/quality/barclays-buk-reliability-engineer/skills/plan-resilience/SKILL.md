---
name: plan-resilience
description: >
    Leads an interactive resilience planning session for a greenfield service. Walks through
    one multichoice question per turn covering outbound dependencies, circuit breaker strategy,
    retry policy, graceful degradation, and rate limiting. Converges on a written resilience target document.
user-invocable: false
owner: BUK Retail CAPL
review-trigger: When BUK resilience standards or accepted circuit breaker frameworks change
---

# Plan — Resilience

For greenfield services making upfront resilience design decisions. Leads a session that converges on a resilience target covering circuit breaker strategy, retry policies, and degradation patterns.

---

## Inputs

```
CODE_PATH:  /absolute/path/to/service   (default: current working directory)
```

---

## Output

`.reliability/resilience-target.md` documenting agreed circuit breaker strategy, retry policy, graceful degradation approach, and rate limiting decisions.

---

## Format rule

Every question must be a numbered multichoice list. Always mark one option **(recommended)**. Always offer a custom/different option. One question per response — never batch questions.

---

## Step 1: Silent scan

Scan the repo to detect stack, build tool, module structure, and any existing HTTP clients, messaging clients, or circuit breaker configuration. Do NOT output anything.

---

## Step 2: Walk the decision tree

Ask one question at a time, wait for response, then continue:

**Question 1 — Outbound dependencies:**
```
What outbound dependencies does this service call?
1. One or more synchronous HTTP APIs (recommended if standard API-to-API)
2. Message broker (Kafka, SQS, SNS)
3. Database only — no external service calls
4. Multiple types — describe
```

**Question 2 — Dependency criticality:**
```
Are all outbound dependencies required for every response, or are some non-critical?
1. All are critical — the service cannot respond without them
2. Some are non-critical — the service can degrade gracefully if they are down (recommended pattern)
3. Not sure — describe the dependency relationship
```

**Question 3 — Circuit breaker framework:**
```
Which circuit breaker framework will this service use?
1. Resilience4j (recommended for Spring Boot)
2. Polly (recommended for .NET)
3. opossum (recommended for Node.js)
4. Manual implementation or no framework — describe
```

**Question 4 — Retry strategy:**
```
Are outbound calls idempotent? This determines the safe retry approach.
1. Yes — all outbound calls are idempotent; exponential backoff + jitter + max-attempts is safe (recommended)
2. Partially — some are idempotent, some are not — retry only the idempotent ones
3. No — calls are not idempotent; retry is not safe at the application level
4. Not sure — describe the operations
```

**Question 5 — Inbound rate limiting:**
```
Does this service need protection from inbound request floods?
1. Yes — rate limiting at the gateway or application layer (recommended for customer-facing services)
2. Handled upstream — API gateway or load balancer provides rate limiting
3. Not needed — internal service with controlled callers
4. Not sure — describe the expected callers
```

---

## Step 3: Convergence summary

Present a summary of agreed decisions. Explain what the resilience target gives the team — protection boundaries, degradation contract, and retry guarantees. Ask for approval.

---

## Step 4: Write the target

On approval, write `.reliability/resilience-target.md`:

```markdown
---
outbound_dependencies: <http-apis|messaging|database-only|mixed>
non_critical_deps: <true|false>
circuit_breaker_framework: <resilience4j|polly|opossum|manual|none>
retry_strategy: <exponential-backoff|partial|none>
inbound_rate_limiting: <application|gateway|none>
---

# Resilience Target

## Decisions

- **Outbound dependencies:** [types]
- **Non-critical dependencies:** [yes/no — list if yes]
- **Circuit breaker framework:** [framework]
- **Retry strategy:** [strategy — idempotency scope]
- **Inbound rate limiting:** [location]

## Patterns to Enforce

Based on the above decisions, enforce these patterns in code review:

| Pattern | Why it applies here |
|---------|-------------------|
| [e.g. Circuit breaker on every outbound HTTP call] | [HTTP API dependencies confirmed] |
| [e.g. Per-call context deadline, not just runtime timeout] | [Lambda deployment — 60s runtime timeout is not per-call] |
| [e.g. Graceful degradation for non-critical deps] | [non-critical deps identified: list them] |

## Patterns Not Applicable

| Pattern | Why it is excluded |
|---------|-------------------|
| [e.g. Retry logic] | [calls are not idempotent — retry is unsafe] |
```

After writing, suggest next steps.

---

## Backward compatibility

If `.reliability/resilience-target.md` already exists:
- Read it and understand agreed decisions
- Report what has already been decided and ask whether to update specific decisions or proceed with a review
- Do NOT overwrite without explicit confirmation

---

## Suggested Next Steps

Always end with 2–5 numbered options. Examples:

```
**Suggested next steps:**
1. Review resilience — run /barclays-buk-reliability-engineer:review-resilience to scan existing code against this target
2. Design another area — run /barclays-buk-reliability-engineer:plan observability|performance|config
3. Review the target — inspect .reliability/resilience-target.md before starting
4. Something different — describe what you'd like to do
```

---

## Flags

State any of the following that apply (or "None identified"):

**Missing or ambiguous inputs:**
- CODE_PATH not provided — scanned current working directory

**Decisions made under uncertainty:**
- Stack detected as [X] based on [indicator] — if incorrect, specify and re-run
- Framework recommendation based on detected stack — override in Question 3 if needed

---

## Agent Self-Check

- [ ] Silent scan completed before asking any questions
- [ ] Each question presented one at a time with numbered options and a recommendation
- [ ] All 5 decision questions answered before writing the target
- [ ] Convergence summary shown and approved before writing
- [ ] `.reliability/resilience-target.md` written with correct frontmatter
- [ ] Backward compatibility: existing target read and preserved unless explicitly overwritten
