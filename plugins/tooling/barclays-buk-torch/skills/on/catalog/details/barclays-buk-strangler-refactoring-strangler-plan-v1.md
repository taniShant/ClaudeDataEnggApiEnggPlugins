# barclays-buk-strangler-refactoring-strangler-plan-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-strangler-refactoring-strangler-plan-v1` |
| Plugin name | `barclays-buk-strangler-refactoring` |
| Component type | skill-user-only |
| Owner | Preetha Ramaswamy |
| Action scope | local-modification |
| Invocation mode | user-only |
| Installation / release | /plugin install barclays-buk-strangler-refactoring@barclays-cio-buk |
| Native command | `/barclays-buk-strangler-refactoring:strangler-plan` |
| Skill name | `strangler-plan` |

## Description

Create a phased extraction plan with service architecture and risk assessment.

## When to use

Use this capability after Phase 1 discovery is complete (via /strangler-discover) to generate a phased extraction plan with service architecture mapping, risk assessment, and timeline for a strangler-pattern refactoring — it is NOT for running discovery, generating executable tasks, or performing the actual code extraction.

## Inputs

- DOMAIN_FOCUS (optional, positional): restrict the plan to a specific domain (e.g., "wealth", "payment"); defaults to all domains
- --skip-questions (optional flag): skip the 5 interactive planning questions and use defaults derived from the analysis output
- --jira JIRA_ID (optional flag): JIRA ticket ID for tracking; if omitted, the value is read from .claude/forge-state.json

## Preconditions

- .claude/forge-state.json must exist and show phase_1 as "completed" (created by /strangler-discover)
- STRANGLER_DISCOVERY.md and STRANGLER_ANALYSIS.md must be present from Phase 1 output
- The target_file field must be populated in the state file
- The domain-reference skill (§4-5: service mapping and test patterns) must be loadable by the orchestrator subagent

## Expected outputs

- .claude/STRANGLER_PLAN.md: comprehensive extraction plan covering identified domains, extraction approach, risk tolerance, timeline preference, and test strategy
- .claude/forge-state.json updated with phase_2 set to "completed"
- logs/forge.log appended with a [COMPLETE] entry including token usage and execution time
- Console summary showing domains identified, extraction approach, risk tolerance, timeline, test strategy, metrics, and the next-step command (/strangler-tasks)

## Exclusions

- Does NOT run Phase 1 discovery or analysis — requires /strangler-discover to have completed first
- Does NOT generate executable task breakdowns (T001, T002…) — that is handled by /strangler-tasks (Phase 3)
- Does NOT perform any actual code extraction, refactoring, or file modification beyond its own plan artifact and state files
- Does NOT read discovery/analysis files directly in the thin command layer — all file loading is delegated to the orchestrator subagent
- Does NOT ask planning questions inline — interactive questions (domain priority, extraction approach, risk tolerance, timeline preference, test strategy) are delegated to the orchestrator's planner agent unless --skip-questions is set

## Verification

Confirm that .claude/STRANGLER_PLAN.md has been created and contains domain breakdowns, extraction approach, risk assessment, and timeline. Check .claude/forge-state.json to verify phase_2 is marked as "completed", and inspect logs/forge.log for a [COMPLETE] entry with token usage and duration metrics.
