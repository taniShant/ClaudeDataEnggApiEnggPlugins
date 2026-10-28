# Mandatory Decision Framework

Apply this to every significant responsibility.

## Step 1 — Identify the nature of the responsibility

Ask:

1. Is it reusable knowledge/methodology/procedure? → Skill candidate.
2. Is it dynamic goal-level reasoning/routing? → Main agent/Claude candidate.
3. Does execution need isolated context? → Subagent candidate.
4. Do a few independent peers need ongoing collaboration? → Agent Team candidate.
5. Should orchestration itself be executable/repeatable or scale to many agents? → Dynamic Workflow candidate.
6. Must it run automatically on a lifecycle event? → Hook candidate.
7. Is it external capability/access? → MCP/tool candidate.
8. Is it deterministic computation? → Script candidate.
9. Is it an explicit invocation surface? → Command candidate.
10. Is it tiny, core, and tightly coupled to orchestration? → Keep inline.

## Step 2 — Ask who holds the plan

- Claude turn-by-turn: Skill/Subagent/main orchestration.
- Lead agent: Agent Team.
- JavaScript script: Dynamic Workflow.
- Lifecycle event: Hook.
- Deterministic program: Script.

## Step 3 — Test composition

A responsibility may require composition rather than one primitive:

- Agent → Skill
- Agent → Skill → MCP
- Agent → Skill → Script
- Agent → Subagent → Skill
- Dynamic Workflow → many Subagents → Skills → Tools
- Hook → Script
- Skill → a few Subagents

Recommend the simplest composition that preserves correctness.

## Step 4 — Test scope

Classify instructions as:

- universal/durable principle
- domain-specific knowledge
- organisation policy
- team convention
- project constraint
- runtime configuration
- example only

Move or parameterise content whose scope is narrower than its current home.

## Step 5 — Test enforcement

- judgement/advice → Agent/Skill
- guaranteed event-driven behaviour → Hook
- deterministic validation → Script/Hook

## Step 6 — Test context cost

Ask whether the content must be loaded now, in this context, for most invocations. If not, use progressive disclosure, reference material, runtime discovery, or isolation.

## Step 7 — Test reuse and abstraction value

Do not extract unless the change creates concrete benefit.
