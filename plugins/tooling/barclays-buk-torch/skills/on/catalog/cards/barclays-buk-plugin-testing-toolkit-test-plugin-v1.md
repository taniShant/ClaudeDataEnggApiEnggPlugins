# barclays-buk-plugin-testing-toolkit-test-plugin-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-plugin-testing-toolkit-test-plugin-v1` |
| Plugin name | `barclays-buk-plugin-testing-toolkit` |
| Component type | skill-user-only |
| Owner | Barclays BUK |
| Action scope | externally-consequential |
| Invocation mode | user-only |
| Installation / release | /plugin install barclays-buk-plugin-testing-toolkit@barclays-cio-buk |
| Native command | `/barclays-buk-plugin-testing-toolkit:test-plugin` |
| Skill name | `test-plugin` |

## Description

Run comprehensive tests on a plugin — structure, content, functionality, and performance.

## When to use

Use after building or modifying a Claude Code plugin to validate it before release. Produces a scored quality report (100 pts) across structure, content, schema compliance, and BUK compliance categories. Use /validate-plugin for a faster lightweight structural check during development; use /test-plugin as the pre-release quality gate. A score of 90+ indicates the plugin is production-ready.

## Inputs

- `<path>` (required) — path to the plugin directory to test
- `--full` (optional flag) — include performance tests (agent init, skill load, command execution timing)
- `--report` (optional flag) — generate a detailed scored quality report
- `--fix-issues` (optional flag) — auto-fix simple issues such as trailing whitespace and missing newlines
- `--verbose` (optional flag) — show per-file pass/fail detail in output
- `--watch` (optional flag) — re-run tests automatically on file changes

## Preconditions

- The plugin directory must exist and contain a `.claude-plugin/plugin.json` file
- `plugin.json` must be valid JSON — an invalid or missing manifest caps the score at 0 regardless of other checks
- For `--fix-issues`: write access to the plugin directory is required

## Expected outputs

- Scored report across 4 categories totalling 100 points: Structure (40 pts), Content (40 pts), Schema Compliance (10 pts), BUK Compliance (10 pts)
- Per-check pass/fail detail with point values
- Overall score with status: `PRODUCTION READY` (90–100), `NEEDS MINOR FIXES` (70–89), `NEEDS WORK` (50–69), or `NOT READY` (< 50)
- When `--fix-issues` is used: list of auto-fixed files and any issues that require manual resolution

## Exclusions

- Does not deploy or install the plugin into Claude Code — the test runner only reads and validates files
- Does not test plugin behaviour in a live Claude Code session — only static file structure and content quality are assessed
- The `--fix-issues` flag only corrects trivial issues (whitespace, line endings); content quality issues require manual editing
- Performance tests (`--full`) measure file sizes and declared timings but do not execute agents in a live environment

## Verification

Re-run `/test-plugin <path>` without `--fix-issues` to confirm the final score. A score of 90+ with status `PRODUCTION READY` is the target before promoting a plugin. If the score is below 90, review the per-check output to identify which categories need attention.
