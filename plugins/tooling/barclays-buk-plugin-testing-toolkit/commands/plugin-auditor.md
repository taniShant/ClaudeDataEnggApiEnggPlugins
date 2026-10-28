---
name: plugin-auditor
description: Deep architectural audit of a Claude Code plugin — reviews primitive placement, agent and skill quality, orchestration patterns, generality, and enforcement mechanisms.
allowed-tools: Read, Glob, Grep, Bash
---

# /plugin-auditor — Plugin Architecture Audit

## What This Does

Runs a deep architectural audit against a plugin directory. Goes beyond structure and content checks to assess whether responsibilities are in the correct Claude Code primitives, whether agents and skills encode durable expert reasoning, and whether the plugin is portable, maintainable, and context-efficient.

Use this after `/test-plugin` passes — it addresses design quality, not surface compliance.

## Usage

```
/plugin-auditor <path>
```

## Example

```
$ /plugin-auditor ./my-plugin

PLUGIN ARCHITECTURE AUDIT
═══════════════════════════════════════
Plugin: my-plugin  v1.0.0

Auditing across 12 dimensions...

PRIMITIVE PLACEMENT
  ⚠️  Session state managed in agent prose — move to skill + script
  ✅ Orchestration correctly in command

EXPERT QUALITY
  ✅ Agent encodes durable principles
  ⚠️  Skill encodes one team's solution — generalise trigger description

ORCHESTRATION
  Pattern: Sequential Handoff → STATIC (appropriate for this use case)
  ✅ No Dynamic Workflow needed

GENERALITY
  ⚠️  3 hardcoded repo paths — parameterise or move to config

═══════════════════════════════════════
Verdict: NEEDS MINOR ARCHITECTURAL WORK
Full report follows...
```

## When to Use

- Before submitting a plugin to the BUK marketplace
- When a plugin has grown complex and design drift is suspected
- When reviewing a plugin from another team
- After a major feature addition to check primitive boundaries haven't blurred

## Levels

| Command | Checks |
|---------|--------|
| `/validate-plugin` | Structure — manifest, files, naming |
| `/test-plugin` | Quality — content scoring, BUK compliance |
| `/plugin-auditor` | Architecture — design, primitives, orchestration |

## Related Commands

- `/validate-plugin` — Quick structural check
- `/test-plugin` — Full quality score

---

**Status**: ✅ Ready | **Updated**: 2026
