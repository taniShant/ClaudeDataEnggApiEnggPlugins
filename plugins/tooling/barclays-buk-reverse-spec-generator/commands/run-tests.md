---
name: run-tests
description: Execute the project test suite and map results back to spec behaviors, updating .convergence.yaml with pass/fail status per behavior.
agent: reverse-spec-generator-status-agent
allowed-tools: Bash, Read, Write
---

# Run Tests

Execute the project's test suite and map results back to spec behaviors, closing the verify feedback loop.

## Overview

After generating tests with `/generate-tests`, use this command to:

- **Run the test suite** — auto-detects JUnit 5, pytest, or Jest
- **Map failures to behaviors** — links each failing test to its spec behavior by naming convention
- **Update convergence state** — writes `test_status` (passing/failing/error) per behavior into `.convergence.yaml`
- **Surface the next action** — shows which behaviors need code fixes vs spec fixes based on `source_of_truth`

## How It Works

1. Detect the test framework from build files (`build.gradle` → JUnit 5, `pyproject.toml` → pytest, `package.json` → Jest)
2. Run the test suite (Gradle, pytest, or Jest)
3. Parse test results from XML/JSON reports
4. Map each test name to a spec behavior using snake_case normalisation:
   - Java: `testDeleteEventLog` → `delete_event_log`
   - Python: `test_delete_event_log` → `delete_event_log`
   - Jest: `"should delete event log"` → `delete_event_log`
5. Update `.convergence.yaml` with `test_status` per behavior
6. Print a summary showing pass rate and convergence impact

## Usage

```
/run-tests
# Spec file: a-digi-msg-data-mgt.spec
# Project root: /path/to/project
```

Or simply:

```
/run-tests
```

The command will locate the spec and project root from your current working context.

## Output

```
Test Results: a-digi-msg-data-mgt (JUnit 5)
─────────────────────────────────────────────
  ✓ get_messages              passing
  ✓ get_account_messages      passing
  ✗ delete_event_log          FAILING
    Error: XOR validation not enforced — both accountId and customerId accepted
  ✓ create_event_log          passing
  ✓ create_or_update_served_log passing
  ~ dismiss_message           not_run (no test generated)

Summary: 4/5 passing · 1 failing · 1 not_run
Convergence: 72.7% → 77.3% (after test update)

Next actions:
  ✗ delete_event_log  [source_of_truth: spec] → fix the code
    Run /implement to generate a corrected stub, or fix manually
```

## Behavior Mapping Convention

Tests are mapped to spec behaviors by normalising the test name to snake_case and matching against behavior names:

| Test name | Normalised | Matched behavior |
|---|---|---|
| `testDeleteEventLog` | `delete_event_log` | `delete_event_log` |
| `test_delete_event_log` | `delete_event_log` | `delete_event_log` |
| `DeleteEventLogTest` | `delete_event_log` | `delete_event_log` |
| `"should delete the event log"` | `delete_event_log` | `delete_event_log` |
| `testXORValidationOnDelete` | `xor_validation_on_delete` | `delete_event_log` (substring match) |

If a test cannot be mapped to any behavior, it is recorded as unmapped and shown separately.

## When to Run

Use `/run-tests` whenever you want to update convergence state: after writing tests with `/generate-tests`, after fixing code, or at any point in the loop to get a fresh pass/fail picture.

## Framework Detection

| Build file | Framework detected |
|---|---|
| `build.gradle` with `junit-jupiter` | JUnit 5 (Gradle) |
| `pom.xml` with `junit-jupiter` | JUnit 5 (Maven) |
| `pyproject.toml` / `setup.py` with pytest | pytest |
| `package.json` with `jest` or `vitest` | Jest |

Override detection by specifying explicitly:

```
/run-tests
# Framework: junit5
```

## Test Status Values

| Status | Meaning |
|---|---|
| `passing` | Test exists and passes |
| `failing` | Test exists and fails |
| `error` | Test threw an unexpected error |
| `not_run` | No test run result available |
| `no_test` | No test was generated for this behavior |

## What Happens Next

After `/run-tests`:

- **All passing** → run `/converge` to check spec alignment
- **Some failing, source_of_truth=spec** → fix the code; run `/implement` for stubs
- **Some failing, source_of_truth=code** → run `/amend` to update the spec
- **Some failing, source_of_truth=unknown** → human judgment on which side to fix

## Loop Integration

```
/generate-spec → /generate-tests → /run-tests → /converge → decision
                                         │
              source_of_truth: spec ─────┼──→ /implement → fix code
              source_of_truth: code ─────┼──→ /amend spec
              source_of_truth: unknown ──┘──→ human review
```

Run `/status` at any point to see overall loop progress and the recommended next action.
