# barclays-buk-reliability-engineer-implement-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-reliability-engineer-implement-v1` |
| Plugin name | `barclays-buk-reliability-engineer` |
| Component type | skill-user-only |
| Owner | Barclays BUK |
| Action scope | local-modification |
| Invocation mode | user-only |
| Installation / release | /plugin install barclays-buk-reliability-engineer@barclays-cio-buk |
| Native command | `/barclays-buk-reliability-engineer:implement` |
| Skill name | `implement` |

## Description

Implement observability improvements with a red-green verification loop

## When to use

Use when you are ready to implement one or more observability migrations from a previously generated reliability migration plan, applying a red-green TDD verification loop that writes a failing test first and iterates until it passes; this is NOT for generating the initial migration plan or for non-observability code changes.

## Inputs

- `--all` (optional flag): implements all remaining unimplemented observability migrations in sequence
- `<NNN>` (optional positional argument): a specific migration number to implement, e.g., `001`, `003`
- (no argument): defaults to implementing the next unimplemented migration in order

## Preconditions

- A reliability migration plan must already exist with numbered migrations (the `.reliability/` directory and its state file must be present)
- `.reliability/state.yaml` must be accessible and track which migrations have been implemented
- The `buk-reliability-engineer:reliability-engineer-agent` sub-agent must be available in the plugin environment
- The project must have a test framework configured so that the red-green verification loop can write and execute tests (e.g., JUnit with a compatible build tool)

## Expected outputs

- New or modified test files implementing a failing test for the target migration (e.g., `StructuredLoggingTest#v001_structuredLoggingEmitsOtelSchema`)
- Production code changes that make the failing test pass (e.g., adding dependencies like `logback-otel`, configuring structured logging)
- Updated `.reliability/state.yaml` reflecting the newly completed migration(s)
- A summary of each red-green iteration showing test failures and eventual pass status
- Suggested next steps for continuing the migration sequence

## Exclusions

- Does not generate or modify the observability migration plan itself — use the plan/assess capabilities for that
- Does not handle non-observability concerns such as functional feature work, security hardening, or performance tuning
- Does not deploy or release changes to any environment — all modifications are local
- Does not run migrations out of the numbered sequence unless a specific migration number is explicitly provided

## Verification

The engineer should confirm that the command reports a green test pass for each implemented migration and that `.reliability/state.yaml` has been updated to mark the migration(s) as complete. Running the project's test suite independently (e.g., `mvn test` or `gradle test`) should show the newly added observability tests passing.
