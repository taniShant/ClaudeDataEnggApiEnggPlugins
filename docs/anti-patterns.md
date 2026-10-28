# BUK Plugin Anti-Patterns

This document records patterns that are explicitly prohibited in BUK plugins, with the principle each violation breaks and the concrete harm it causes.

---

## 1. Using Claude Code hooks inside a plugin

**What it looks like**

Registering shell commands in `.claude/settings.json` — or instructing users to do so — as part of a plugin's intended behaviour. For example, adding a `PostToolUse` hook to auto-run validation, or a `PreToolUse` hook to gate a command.

**Why it is prohibited**

| Reason | Detail |
|---|---|
| Violates Principle 2 — framework-agnostic | Hooks are a Claude Code harness mechanic. A plugin that depends on hooks is coupled to a specific execution environment and will not work in any other workflow layer (custom orchestrators, CI, SDK integrations). |
| Violates Principle 4 — independently invocable | A plugin whose behaviour depends on hooks registered outside the plugin itself cannot be invoked standalone. Its outputs become non-deterministic depending on what a given user has configured. |
| Unreliable by design | `settings.json` is user-controlled. It may be absent, partially configured, or deliberately overridden. There is no mechanism inside a plugin to assert that a required hook is present. Silent, untraceable failures are the result. |

**What to do instead**

Express all plugin behaviour through agents and skills:

- Logic that should run automatically → put it in the agent's instruction body
- Validation that must happen → make it a skill the agent loads and applies
- Suggested next steps → surface them in the agent's `## Flags` or output section (per Principle 7 — agents suggest, never enforce)

---

## Adding a new anti-pattern

When a recurring misuse is identified, add an entry here following the structure above:

1. **What it looks like** — a concrete example an author might recognise
2. **Why it is prohibited** — which principle(s) it breaks and the practical harm
3. **What to do instead** — the correct pattern
