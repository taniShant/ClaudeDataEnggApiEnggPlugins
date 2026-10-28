# Claude Code Primitive Boundaries

## Plugin
Packaging/distribution boundary. A plugin can bundle skills, subagents, hooks, MCP servers and related extension configuration. Do not treat Plugin as a behavioural primitive.

## Main Agent / Claude
Use for dynamic goal interpretation, reasoning, routing, choosing capabilities, evaluating intermediate results, adapting plans, and deciding completion.

Keep small, core orchestration logic inline when abstraction gives no concrete benefit.

## Skill
Reusable instructions, expertise, methodology, reference knowledge, or an invocable workflow Claude follows. Skills can contain multi-step reasoning and can orchestrate a few subagents. Reasoning alone does not imply Subagent.

## Subagent
An isolated worker with its own context. Use when isolation, parallel work, extensive file reading, specialist tool boundaries, or returning only a summary materially helps.

Ask: what concrete benefit does a separate context window provide? If none, prefer Skill or inline reasoning.

## Agent Team
A lead agent coordinates independent peer sessions through shared tasks/messages. Use when a handful of long-running peers genuinely need collaboration or competing perspectives. Do not use merely for parallelism.

## Dynamic Workflow
A JavaScript orchestration script executed by the workflow runtime. The script holds loops, branches, orchestration state, and intermediate results. Use when orchestration itself should be codified, repeatable, inspectable, resumable, or scaled to many agents.

Key distinction: with Skills/Subagents/Agent Teams Claude/lead holds the plan turn-by-turn; with Dynamic Workflow the script holds the plan.

## Hook
Lifecycle-triggered automation. Use when behaviour must run on matching events. Hooks can execute commands/HTTP/prompts/subagents, but deterministic enforcement is the strongest use case.

## MCP / Tool
Capability/access boundary, especially external systems. Keep business methodology outside the connectivity layer where possible.

## Script
Deterministic computation, validation, parsing, formatting, transformation, or structural checks. Prefer code over repeated LLM reasoning when judgement is unnecessary.

## Command
Explicit user invocation surface. Do not use commands merely as storage for reusable knowledge. Saved workflows can also surface as commands.

## Reference / Knowledge
Detailed, version-specific, domain-specific, or example-heavy material loaded only when required. Use to keep core Skills lean.
