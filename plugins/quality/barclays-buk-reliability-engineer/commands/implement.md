---
description: Implement observability improvements with a red-green verification loop
argument-hint: [--all | migration-number]
---

Read `skills/implement/SKILL.md` and follow its instructions exactly.

Also load `skills/otel-conventions/SKILL.md`.

## Argument parsing

Before reading the skill, parse the argument:
- `--all` — pass `MIGRATION=--all` to the skill (implement all remaining migrations in sequence)
- `<NNN>` (e.g., `003`) — pass `MIGRATION=NNN` to the skill (implement a specific migration by number)
- (no args) — pass `MIGRATION=(none)` to the skill (implement the next unimplemented migration only)

## Example

```
$ /barclays-buk-reliability-engineer:implement 001

Implementing migration 001 — Structured Logging

✅ Test written: StructuredLoggingTest#v001_structuredLoggingEmitsOtelSchema
❌ Iteration 1: missing logback-otel dependency
✅ Iteration 2: test passes

Migration 001 complete. State updated in .reliability/state.yaml

**Suggested next steps:**
1. Implement the next migration — run /barclays-buk-reliability-engineer:implement for 002
2. Review other capability areas
3. Nothing right now
```
