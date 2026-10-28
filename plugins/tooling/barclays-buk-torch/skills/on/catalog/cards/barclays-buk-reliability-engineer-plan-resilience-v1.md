# barclays-buk-reliability-engineer-plan-resilience-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-reliability-engineer-plan-resilience-v1` |
| Plugin name | `barclays-buk-reliability-engineer` |
| Component type | skill-model-invocable |
| Owner | BUK Retail CAPL |
| Action scope | local-modification |
| Invocation mode | model-invocable |
| Installation / release | /plugin install barclays-buk-reliability-engineer@barclays-cio-buk |
| Native command | `/barclays-buk-reliability-engineer:plan-resilience` |
| Skill name | `plan-resilience` |

## Description

Leads an interactive resilience planning session for a greenfield service. Walks through one multichoice question per turn covering outbound dependencies, circuit breaker strategy, retry policy, graceful degradation, and rate limiting. Converges on a written resilience target document.

## When to use

Use when planning resilience design decisions for a new or greenfield service; covers outbound dependencies, circuit breaker strategy, retry policy, graceful degradation, and inbound rate limiting; NOT for reviewing existing service resilience (use review-resilience)

## Inputs

- Interactive session — no upfront inputs required; the skill leads a Q&A dialogue asking one multichoice question per turn
- `CODE_PATH` (optional): absolute path to the service; defaults to current working directory

## Preconditions

- An active Claude Code session in or near the service repository
- The skill performs a silent scan to detect stack, build tool, and any existing circuit breaker or HTTP client configuration before asking questions

## Expected outputs

- `.reliability/resilience-target.md` written to the repository, documenting agreed outbound dependency types, non-critical dependency list, circuit breaker framework, retry strategy, and inbound rate limiting approach, plus patterns to enforce and patterns not applicable

## Exclusions

- Does not scan or review an existing service's resilience posture — use `review-resilience` for that
- Does not implement any code changes
- Does not overwrite an existing `.reliability/resilience-target.md` without explicit confirmation

## Verification

Confirm `.reliability/resilience-target.md` has been written with correct frontmatter fields (`outbound_dependencies`, `non_critical_deps`, `circuit_breaker_framework`, `retry_strategy`, `inbound_rate_limiting`). Inspect the Patterns to Enforce table to confirm circuit breaker and retry decisions are captured.
