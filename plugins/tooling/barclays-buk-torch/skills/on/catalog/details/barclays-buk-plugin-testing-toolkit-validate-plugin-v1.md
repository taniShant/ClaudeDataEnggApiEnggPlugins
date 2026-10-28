# barclays-buk-plugin-testing-toolkit-validate-plugin-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-plugin-testing-toolkit-validate-plugin-v1` |
| Plugin name | `barclays-buk-plugin-testing-toolkit` |
| Component type | skill-user-only |
| Owner | Barclays BUK |
| Action scope | read-only |
| Invocation mode | user-only |
| Installation / release | /plugin install barclays-buk-plugin-testing-toolkit@barclays-cio-buk |
| Native command | `/barclays-buk-plugin-testing-toolkit:validate-plugin` |
| Skill name | `validate-plugin` |

## Description

Quick structural validation of a plugin — checks manifest JSON and file references without full content scoring.

## When to use

Use immediately after editing plugin.json, renaming or moving plugin files, or before running the full /test-plugin suite. Performs a fast structural check only — validates JSON syntax and confirms all referenced files exist on disk. Runs in seconds. Not a substitute for /test-plugin before a production release; use /test-plugin for scored quality assessment.

## Inputs

- `<path>` (required) — path to the plugin directory to validate
- `--verbose` (optional flag) — show per-file pass/fail detail alongside the summary

## Preconditions

- The plugin directory must exist and contain a `.claude-plugin/plugin.json` file

## Expected outputs

- Per-file check results: `plugin.json` validity and presence of each referenced agent/skill/command file
- Summary line: `N/N checks passed` with overall `STRUCTURE VALID` or failure status
- On failure: the specific missing file path and a suggested fix (create the file or remove the reference from `plugin.json`)

## Exclusions

- Does not perform content quality scoring — use `/test-plugin` for that
- Does not check agent/skill/command file content for completeness, correctness, or BUK compliance
- Does not test plugin functionality in a live Claude Code session
- Does not check for naming convention violations (lowercase-hyphen for agents/commands, `SKILL.md` for skills) — that is covered by `/test-plugin`

## Verification

All `N/N checks passed` with `STRUCTURE VALID` status. If any check fails, the output identifies the missing file and the corrective action. After fixing, re-run `/validate-plugin <path>` to confirm all checks pass before proceeding to `/test-plugin`.
