---
description: Show current observability maturity status without running tests
argument-hint:
---

Read `skills/status/SKILL.md` and follow its instructions exactly against the current working directory.

This command takes no arguments and makes no changes to the repository.

## Example

```
$ /barclays-buk-reliability-engineer:status

# Observability Status — payments-api

**Current phase:** Logging
**Phase status:** In progress (2/5 migrations complete)

| Migration | Status | Implemented |
|-----------|--------|-------------|
| 001 — Structured logging | ✅ Complete | 2026-07-15 |
| 002 — Correlation IDs | ✅ Complete | 2026-07-18 |
| 003 — Collector-ready | ⏳ Pending | — |
| 004 — Sensitive data guard | ⏳ Pending | — |
| 005 — Capability attestation | ⏳ Pending | — |

**Suggested next steps:**
1. Implement next migration — run /barclays-buk-reliability-engineer:implement
2. Review other areas — run /barclays-buk-reliability-engineer:review
3. Nothing right now
```
