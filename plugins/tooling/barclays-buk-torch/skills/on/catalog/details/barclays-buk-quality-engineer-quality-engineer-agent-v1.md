# barclays-buk-quality-engineer-quality-engineer-agent-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-quality-engineer-quality-engineer-agent-v1` |
| Plugin name | `barclays-buk-quality-engineer` |
| Component type | agent-plugin |
| Owner | BUK Retail CAPL |
| Action scope | local-modification |
| Invocation mode | tool/agent — no slash command |
| Installation / release | /plugin install barclays-buk-quality-engineer@barclays-cio-buk |

## Description

_No skill entry point — invoked through plugin tools/agents._

## Inputs

- `REQUIREMENTS_PATH` — path to requirements document (e.g. output from `product-manager-agent`); pass `"none"` if absent
- `CODE_PATH` — absolute path to the code under test
- `TEST_TYPE` — one of: `unit`, `integration`, `e2e`, `all`
- `TECH_STACK` — language and test framework (e.g. `Java/JUnit5`, `TypeScript/Jest`)
- `OUTPUT_PATH` — absolute path where generated test files and `TEST-PLAN.md` will be written

## Preconditions

- `CODE_PATH` must point to readable source code
- `TECH_STACK` must be specified; test generation is framework-specific
- `barclays-buk-quality-engineer` plugin installed via `/plugin install barclays-buk-quality-engineer@barclays-cio-buk`

## Expected outputs

- Test files written to `OUTPUT_PATH` targeting 90% line coverage and 90% mutation score (Java)
- `TEST-PLAN.md` at `OUTPUT_PATH` — test plan per acceptance criterion, edge case table, coverage report with gap analysis
- Flags section reporting any placeholder skills, missing requirements, or coverage decisions made under uncertainty

## Exclusions

- Does not run CI pipelines or trigger deployments
- Does not perform WCAG visual or dynamic accessibility testing (use `accessibility-auditor-agent` for that)
- Does not validate that tests pass against the implementation — test execution is the caller's responsibility
- Does not enforce mutation testing for non-Java stacks

## Verification

After the agent completes, confirm `OUTPUT_PATH` contains at least one test file and a `TEST-PLAN.md`. Open `TEST-PLAN.md` and verify it lists test cases mapped to acceptance criteria and reports line coverage achieved vs the 90% target. If coverage results are absent, the agent flagged that test execution was not possible and the caller must run the test suite manually.
