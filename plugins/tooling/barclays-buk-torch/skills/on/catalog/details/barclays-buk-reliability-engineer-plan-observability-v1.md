# barclays-buk-reliability-engineer-plan-observability-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-reliability-engineer-plan-observability-v1` |
| Plugin name | `barclays-buk-reliability-engineer` |
| Component type | skill-model-invocable |
| Owner | BUK Retail CAPL |
| Action scope | local-modification |
| Invocation mode | model-invocable |
| Installation / release | /plugin install barclays-buk-reliability-engineer@barclays-cio-buk |
| Native command | `/barclays-buk-reliability-engineer:plan-observability` |
| Skill name | `plan-observability` |

## Description

Leads an interactive observability planning session for a greenfield service. Walks through one multichoice question per turn covering application type, stack, log schema, verification strategy, and sensitive data patterns. Converges on a written observability target document.

## When to use

Use when designing the observability strategy for a new or greenfield service; walks through application type, stack, log schema, verification strategy, and sensitive data patterns; NOT for reviewing existing services (use review-observability)

## Inputs

- Interactive session — no upfront inputs required; the skill leads a Q&A dialogue asking one multichoice question per turn
- `CODE_PATH` (optional): absolute path to the service; defaults to current working directory

## Preconditions

- An active Claude Code session in or near the service repository
- The skill loads `barclays-buk-standards:observability` and `otel-conventions` alongside itself; reports placeholder flags if either is unavailable

## Expected outputs

- `.reliability/observability-target.md` written to the repository, documenting agreed schema, strategy, stack, phase decisions, sensitive data patterns, and context propagation approach

## Exclusions

- Does not review or audit an existing service's observability — use `review-observability` for that
- Does not implement any code changes — use `implement` after the target is written
- Does not overwrite an existing `.reliability/observability-target.md` without explicit confirmation

## Verification

Confirm `.reliability/observability-target.md` has been written with correct frontmatter fields (`conventions_version`, `schema`, `strategy`, `application`, `phases`). Inspect the sensitive data patterns table and verify context propagation section reflects the service's inbound/outbound transport types.
