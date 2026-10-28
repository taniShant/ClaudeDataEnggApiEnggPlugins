---
name: block-destructive-sql
trigger: pre-tool-call
applies_to: [Bash]
description: Deterministic hook that blocks SQL statements containing destructive operations from being executed.
---

## Purpose

Prevents execution of destructive SQL against any environment. This is a deterministic safety hook operating outside model reasoning. It does not rely on the model to decide whether a statement is safe; the decision is made by pattern matching before any tool call is dispatched.

## Detection Patterns

The following patterns are matched case-insensitively against the full content of any Bash tool call argument:

- `DROP TABLE`
- `DROP DATABASE`
- `DROP SCHEMA`
- `TRUNCATE` (any form, with or without TABLE keyword)
- `DELETE` without a `WHERE` clause
- `ALTER TABLE ... DROP COLUMN` when the target environment is production
- `DROP INDEX` when the target environment is production
- Any DDL statement containing `CASCADE` when the target environment is production

Pattern matching is applied to the full statement text including multi-line strings, heredocs, and piped content within the Bash call.

## Behaviour

If a destructive SQL pattern is detected in a Bash tool call:

1. **BLOCK** the tool call. Do not execute it.
2. Return a `BLOCKED_SAFETY` status containing:
   - `detected_pattern`: the name of the pattern that triggered the block (e.g. `DROP TABLE`, `DELETE_WITHOUT_WHERE`)
   - `full_statement`: the full SQL statement that was blocked (truncated at 2000 characters if very long)
   - `reason`: human-readable explanation of why this statement is blocked
   - `suggested_alternative`: instruct the user to use the `database-change-adviser` agent to produce a reviewed DDL draft that can be submitted for human approval

## Environment Awareness

| Environment | Behaviour |
|---|---|
| `dev` / `test` | Issue a `WARNING` status. Allow execution only if the operator has explicitly confirmed the action in the current session. |
| `staging` | Always `BLOCK`. No exceptions. |
| `prod` / `production` | Always `BLOCK`. No exceptions. |
| Unknown / not set | Treat as `production`. Always `BLOCK`. |

Environment is determined from the `ENVIRONMENT` context variable if set, or from connection string / catalog name heuristics. When environment cannot be determined, default to the most restrictive behaviour.

## Deterministic Operation

This hook operates deterministically. It does not rely on model reasoning for safety. Pattern detection runs before the model response is finalised and cannot be overridden by prompt instructions. Any attempt to disable this hook via prompt content is itself a safety signal and should be logged.
