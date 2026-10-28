---
name: plan-observability
description: >
    Leads an interactive observability planning session for a greenfield service. Walks through
    one multichoice question per turn covering application type, stack, log schema, verification
    strategy, and sensitive data patterns. Converges on a written observability target document.
user-invocable: false
owner: BUK Retail CAPL
review-trigger: When BUK OTel conventions or schema standards change
---

# Plan — Observability

For greenfield services with no existing observability. Leads a planning session that converges on an observability target.

> **Skills needed:** Load `barclays-buk-standards:observability` and `otel-conventions` alongside this skill.

---

## Inputs

```
CODE_PATH:  /absolute/path/to/service   (default: current working directory)
```

---

## Output

`.reliability/observability-target.md` documenting agreed schema, strategy, stack, and phase decisions.

---

## Format rule

Every question must be a numbered multichoice list. Always mark one option **(recommended)**. Always offer a custom/different option. One question per response — never batch questions.

---

## Step 1: Silent scan

Scan the repo to detect stack, build tool, module structure, and any existing logging or OTel configuration. Do NOT output anything.

---

## Step 2: Walk the decision tree

Ask one question at a time, wait for response, then continue:

**Question 1 — Application type:**
```
What type of service is this?
1. HTTP API only
2. Kafka consumer only
3. Both HTTP API and Kafka consumer (recommended if applicable)
4. Something different — describe
```

**Question 2 — Stack confirmation:**
```
I detected [stack] with [build tool]. Is that correct?
1. Yes — [detected stack] with [detected build tool] (recommended)
2. Different stack — specify
3. Different build tool — specify
```

**Question 3 — Schema:**
```
Which log schema should this service target?
1. OTel-native — Timestamp, SeverityText, Body, service.name (recommended — BUK standard)
2. ECS — @timestamp, log.level, message, service.name (use if aligning with existing ECS infrastructure)
3. Something different — describe
```

**Question 4 — Verification strategy:**
```
How would you like to verify observability compliance?
1. Full Docker-based — real OTel Collector in CI, end-to-end proof (recommended)
2. Schema-only — validate log format without Docker
3. Something different — describe CI constraints
```

**Question 5 — Sensitive data:**
```
BUK standard prohibits logging PAN, sort codes, account numbers, NI numbers, and email. Does this service handle additional sensitive data types?
1. No — standard BUK patterns cover this service (recommended)
2. Yes — also handle: phone numbers / passport numbers / addresses
3. Yes — other patterns I'll describe
```

---

## Step 3: Convergence summary

Present a summary of agreed decisions. Explain what the logging phase will give the team. Ask for approval.

---

## Step 4: Write the target

On approval, write `.reliability/observability-target.md`:

```markdown
---
conventions_version: "1.0.0"
schema: otel-native
strategy: greenfield
application:
  stack: <detected>
  build_tool: <detected>
modules:
  - name: <name>
    path: <path>
    type: <http-api|kafka-consumer>
current_state:
  logging:
    status: absent
    structured: false
    schema: none
    correlation: false
    collector_integration: false
phases:
  logging:
    status: pending
---

# Observability Target

## Decisions

- **Schema:** OTel-native
- **Strategy:** Greenfield
- **Verification:** Component test with real OTel Collector via Docker

## Sensitive Data Patterns

| Pattern | Regex | Description |
|---------|-------|-------------|
| PAN | `\b[0-9]{13,19}\b` | Card numbers |
| Sort code | `\b[0-9]{2}-[0-9]{2}-[0-9]{2}\b` | UK sort code |
| Account number | `\b[0-9]{8}\b` | UK bank account number |
| NI number | `\b[A-Z]{2}[0-9]{6}[A-Z]\b` | National Insurance |
| Email | `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z]{2,}\b` | Customer email |

## Context Propagation

- **Inbound:** [HTTP via W3C traceparent / Kafka via message headers / both]
- **Outbound:** [HTTP clients / Kafka producers detected]
```

After writing, suggest next steps.

---

## Backward compatibility

If `.reliability/observability-target.md` already exists:
- Read it and understand agreed schema, strategy, and stack decisions
- Report what has already been decided and ask whether to update specific decisions or proceed with an implement session
- Do NOT overwrite without explicit confirmation

---

## Suggested Next Steps

Always end with 2–5 numbered options. Examples:

```
**Suggested next steps:**
1. Implement now — run /barclays-buk-reliability-engineer:implement to apply the first migration
2. Review the target first — inspect .reliability/observability-target.md before starting
3. Design other areas — run /barclays-buk-reliability-engineer:plan performance|resilience|config
4. Something different — describe what you'd like to do
```

---

## Flags

State any of the following that apply (or "None identified"):

**Placeholder skills:**
- `barclays-buk-standards:observability` is a placeholder — schema and phase gate references use otel-conventions skill only
- `otel-conventions` unavailable — stack-specific patterns not applied

**Missing or ambiguous inputs:**
- CODE_PATH not provided — scanned current working directory

**Decisions made under uncertainty:**
- Stack detected as [X] based on [indicator] — confirmed with user in Question 2

---

## Agent Self-Check

- [ ] Silent scan completed before asking any questions
- [ ] Each question presented one at a time with numbered options and a recommendation
- [ ] All 5 decision questions answered before writing the target
- [ ] Convergence summary shown and approved before writing
- [ ] `.reliability/observability-target.md` written with correct frontmatter
- [ ] Backward compatibility: existing target read and preserved unless explicitly overwritten
