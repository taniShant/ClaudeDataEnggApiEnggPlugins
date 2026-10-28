---
name: plugin-architecture
description: >
  This skill should be used when auditing whether a Claude Code plugin is architecturally sound.
  Use when the user asks to "audit this plugin", "review plugin design", "check primitive placement",
  "review plugin architecture", "is this plugin well-designed", "assess orchestration patterns",
  or "check if responsibilities are in the right primitives".
user-invocable: true
---

<!-- Source: barclays-buk-plugin-testing-toolkit -->
<!-- Owner: Barclays BUK Tooling -->
<!-- Review trigger: When Claude Code plugin primitive model changes -->
<!-- Status: Active -->

# Claude Code Plugin Architecture Auditor

Audit the plugin as an architecture, not merely as a collection of files.

The primary question is:

> Is each responsibility implemented in the correct Claude Code primitive, with the right scope, expert reasoning, orchestration pattern, enforcement mechanism, and level of generality?

Do not modify the plugin unless explicitly requested. Review first.

## Mandatory review dimensions

Every audit MUST assess all of these:

1. Primitive placement
2. Agent quality
3. Skill quality
4. Generality and hardcoding
5. Policy and knowledge scope
6. Orchestration pattern
7. Dynamic vs deterministic control
8. Enforcement mechanism
9. Composition and boundaries
10. Context efficiency and progressive disclosure
11. Duplication and single source of truth
12. Failure, termination, and verification behaviour

Read the relevant reference files before making conclusions:

- `references/primitives.md` — Claude Code primitive boundaries
- `references/decision-framework.md` — mandatory classification process
- `references/expert-quality.md` — principles for expert agents and skills
- `references/generality-and-hardcoding.md` — accidental hardcoding and portability
- `references/workflow-patterns.md` — orchestration pattern catalogue
- `references/anti-patterns.md` — architectural failure modes
- `references/report-template.md` — required final report

## Governing model

Use this mental model:

- Plugin = packaging and distribution
- Agent/main Claude = goal reasoning, dynamic decisions, orchestration
- Skill = reusable instructions, expertise, methodology, or workflow Claude follows
- Subagent = isolated worker Claude spawns
- Agent team = lead agent supervising collaborating peer sessions
- Dynamic workflow = JavaScript orchestration script executed by the runtime
- Hook = lifecycle-triggered automation/enforcement
- MCP/tool = external capability/access
- Script = deterministic computation/validation/transformation
- Command = explicit invocation surface
- References/knowledge = detailed material loaded only when required

These can compose. Do not force a capability into one primitive when a composition is cleaner.

## Core separation test

For each significant responsibility determine:

- WHO should perform it?
- WHAT knowledge is required?
- HOW should the procedure be applied?
- WHO/WHAT decides what runs next?
- WHAT capability performs external actions?
- WHAT must be deterministic?
- WHAT must be enforced automatically?
- WHAT is generic vs organisation/team/project-specific?

## Mandatory placement validation

For every substantial responsibility produce:

| Responsibility | Current home | Recommended home | Verdict | Evidence | Reason |
|---|---|---|---|---|---|

Allowed verdicts: KEEP, KEEP INLINE, EXTRACT TO SKILL, EXTRACT TO SUBAGENT, USE AGENT TEAM, MOVE TO DYNAMIC WORKFLOW, MOVE TO HOOK, MOVE TO MCP/TOOL, MOVE TO SCRIPT, MOVE TO COMMAND, MOVE TO CONFIG/POLICY, GENERALISE, PARAMETERISE, MERGE, SIMPLIFY, DELETE.

Never recommend extraction merely because extraction is possible. For every change answer:

> What concrete architectural problem does this solve?

If there is no material improvement in correctness, reuse, isolation, context efficiency, deterministic enforcement, portability, security, or maintainability, recommend KEEP.

## Mandatory orchestration classification

Classify the overall workflow and important subflows as STATIC, DYNAMIC, or HYBRID. Then identify the orchestration pattern where applicable (Fan-out/Fan-in, Pipeline, Map-Reduce, Planner→Executor, Generator→Verifier, Retry/Repair Loop, etc.).

## Dynamic workflow test

For every substantial orchestration explicitly ask:

> Who should hold the plan?

- Claude turn-by-turn → Skill/Subagent/main-agent orchestration
- Lead agent coordinating peers → Agent Team
- Executable repeatable orchestration → Dynamic Workflow
- Event system → Hook
- Deterministic program → Script

Do not recommend Dynamic Workflow simply because a task has multiple steps.

## Expert-component rule

Expert components should encode HOW TO REASON, not a collection of answers that happened to work once.

Validate agents and expert skills for: durable principles, decision criteria, trade-off reasoning, evidence grounding, scope and boundaries, uncertainty handling, verification, justified exceptions, anti-pattern awareness, context-sensitive adaptation.

## Generality rule

For every rule or recommendation ask:

> Would this still be correct if this plugin were installed in another appropriate repository by another team?

If NO, classify as: intentionally domain-scoped knowledge, organisation policy, team convention, project constraint, runtime configuration, example-specific assumption, accidental hardcoding, or secret/sensitive configuration.

## Enforcement rule

Distinguish advisory reasoning from guaranteed enforcement. If something MUST happen on every matching lifecycle event, determine whether it belongs in a Hook rather than only in prose.

## Context rule

Prefer progressive disclosure: discovery metadata concise, core Skill instructions contain only necessary workflow/methodology, detailed knowledge in references, deterministic work in scripts. Flag content loaded earlier or more broadly than necessary.

## Required final output

Use `references/report-template.md`. The report MUST include:

1. Overall verdict
2. Current architecture
3. Primitive placement matrix
4. Agent quality audit
5. Skill quality audit
6. Generality/hardcoding audit
7. Policy-scope audit
8. Workflow/orchestration classification
9. Dynamic workflow assessment
10. Enforcement assessment
11. Context/progressive-disclosure assessment
12. Over-engineering findings
13. Under-engineering findings
14. Target architecture
15. Exact current → target refactoring map
16. Prioritised migration sequence
17. Explicit KEEP / DO NOT EXTRACT section
18. Scores

Base important findings on actual repository evidence: file, section, implementation, or configuration. Do not infer architecture from names alone.

## Agent Self-Check

Before finalising the audit report, verify:

- [ ] All 12 mandatory review dimensions assessed
- [ ] Primitive placement matrix completed for every substantial responsibility
- [ ] Every EXTRACT/MOVE recommendation answers "what concrete problem does this solve?"
- [ ] Orchestration classified as STATIC / DYNAMIC / HYBRID with pattern named
- [ ] Dynamic Workflow assessment explicitly states whether orchestration should or should not become a Dynamic Workflow and why
- [ ] Generality rule applied — no project-specific solution silently promoted to universal rule
- [ ] KEEP / DO NOT EXTRACT section present
- [ ] Findings grounded in file/section/configuration evidence, not inferred from names
