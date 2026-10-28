---
description: Review a service across all four reliability capability areas in parallel
argument-hint:
---

You are the orchestrator for `/barclays-buk-reliability-engineer:review`.

Use the Agent tool to spawn 4 agents in parallel (all 4 calls in a single message):
- Agent 1: read and execute `skills/review-performance/SKILL.md`
- Agent 2: read and execute `skills/review-observability/SKILL.md` + `skills/otel-conventions/SKILL.md`
- Agent 3: read and execute `skills/review-resilience/SKILL.md`
- Agent 4: read and execute `skills/review-config/SKILL.md`

When all 4 complete, consolidate their findings into a **single report**:

```
# Reliability Review — [service name]

**Date:** [date]
**Stack:** [stack] ([build tool])
**Modules:** [list]
**Observability phase:** [phase] — [status]

---

## Summary
[2–3 sentences covering overall reliability posture]

---

## Findings

| # | Priority | Area | Finding | File / Location | Recommendation |
|---|----------|------|---------|-----------------|---------------|

---

## Observability Detail
[phase gate table from observability agent]

---

## Deployment Readiness
- [ ] Health check endpoint implemented and returns meaningful status
- [ ] Readiness probe distinguishes between starting and ready states
- [ ] Graceful shutdown handles in-flight requests
- [ ] Resource limits (CPU/memory) defined
- [ ] Runbook exists covering: startup, shutdown, common failure modes, escalation path
- [ ] Alerts defined for critical failure conditions

---

## Suggested Next Steps
[numbered list — de-duplicated across all agents]
```

**Consolidation rules:**
- **Findings MUST be a single markdown table** — sort by priority: Critical → High → Medium. Number rows sequentially.
- Combine Observability Detail sections
- Merge Deployment Readiness checklists (de-duplicate identical items)
- Unify Suggested Next Steps (keep most actionable phrasing)
- Include Flags from all agents

**Write the full report:**
Use Bash to create the directory if needed (`mkdir -p .reliability/reports`), then Write the complete markdown report to:
```
.reliability/reports/reliability-review-[YYYY-MM-DD].md
```
If `.reliability/reports/.gitignore` does not exist, create it:
```
*
!.gitignore
```

**Display in terminal:**
Show a compact summary — report header, condensed findings table (max 50 chars per cell, truncate with `…`), suggested next steps, and a clickable absolute path to the full report.

## Example

```
$ /barclays-buk-reliability-engineer:review

# Reliability Review — payments-api

**Date:** 2026-09-03
**Stack:** Spring Boot (Maven)
**Observability phase:** logging — in-progress

## Findings

| # | Priority | Area | Finding | File | Recommendation |
|---|----------|------|---------|------|---------------|
| 1 | Critical | Observability | PAN logged in payment response | PaymentController.java:45 | Mask card number |
| 2 | High | Performance | N+1 query in transaction list | TransactionService.java:82 | Use batch fetch |
| 3 | Medium | Resilience | No circuit breaker on fraud call | FraudClient.java:30 | Add Resilience4j CB |
```
