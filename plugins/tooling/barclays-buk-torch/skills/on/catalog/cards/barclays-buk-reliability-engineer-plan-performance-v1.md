# barclays-buk-reliability-engineer-plan-performance-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-reliability-engineer-plan-performance-v1` |
| Plugin name | `barclays-buk-reliability-engineer` |
| Component type | skill-model-invocable |
| Owner | BUK Retail CAPL |
| Action scope | local-modification |
| Invocation mode | model-invocable |
| Installation / release | /plugin install barclays-buk-reliability-engineer@barclays-cio-buk |
| Native command | `/barclays-buk-reliability-engineer:plan-performance` |
| Skill name | `plan-performance` |

## Description

Leads an interactive performance planning session for a greenfield service. Walks through one multichoice question per turn covering service tier, data access patterns, traffic shape, caching strategy, and memory constraints. Converges on a written performance target document.

## When to use

Use when planning performance design decisions for a new or greenfield service; covers service tier, data access patterns, traffic shape, caching strategy, and memory constraints; NOT for reviewing existing service performance (use review-performance)

## Inputs

- Interactive session — no upfront inputs required; the skill leads a Q&A dialogue asking one multichoice question per turn
- `CODE_PATH` (optional): absolute path to the service; defaults to current working directory

## Preconditions

- An active Claude Code session in or near the service repository
- The skill loads `barclays-buk-standards:performance` alongside itself; reports placeholder flags if unavailable (latency budget thresholds are advisory without it)

## Expected outputs

- `.reliability/performance-target.md` written to the repository, documenting agreed service tier, data access pattern, traffic pattern, caching strategy, memory constraints, patterns to enforce, and patterns not applicable

## Exclusions

- Does not scan or review an existing service's performance — use `review-performance` for that
- Does not implement any code changes
- Does not overwrite an existing `.reliability/performance-target.md` without explicit confirmation

## Verification

Confirm `.reliability/performance-target.md` has been written with correct frontmatter fields (`service_tier`, `data_access`, `traffic_pattern`, `caching_strategy`, `large_payload_risk`). Inspect the Patterns to Enforce and Patterns Not Applicable tables to confirm they reflect the decisions made during the session.
