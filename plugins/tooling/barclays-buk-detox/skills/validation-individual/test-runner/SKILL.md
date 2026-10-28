---
name: test-runner
description: "Test Runner — Detect and run test suite using the deterministic Python script."
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/validation_individual/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Test Runner

## Purpose

Detect and execute the test suite of a target repository to determine whether the codebase passes its existing tests after a vulnerability fix has been applied. Auto-detects the project's language and test framework, runs the appropriate test command, and reports structured pass/fail results.

## Implementation

This skill is implemented as a **deterministic Python script** at `scripts/validators/test_runner.py`. No LLM reasoning is required — framework detection uses config file probing.

## Invocation

> `{python}` = the verified Python 3 command (`python3`, `py -3` or `python`) from the calling agent's Python Interpreter rule. Detox never installs Python — if none is available, STOP.

```bash
echo '{
  "repo_dir": "/path/to/repo",
  "target_file": "/path/to/modified_file.py",
  "timeout_seconds": 300,
  "run_full_suite": false
}' | {python} $PLUGIN_DIR/scripts/validators/test_runner.py
```

## Input Schema

| Field | Required | Type | Description |
|---|---|---|---|
| `repo_dir` | Yes | string | Absolute path to repository root |
| `target_file` | No | string | Modified file for targeted test discovery |
| `timeout_seconds` | No | integer | Max test execution time (default: 300) |
| `run_full_suite` | No | boolean | Force full suite even with target_file (default: false) |

## Output Schema

```json
{
  "status": "success",
  "repo_dir": "/path/to/repo",
  "test_framework": {
    "name": "pytest",
    "language": "Python",
    "command_executed": "python -m pytest tests/test_auth.py -v --tb=short",
    "detection_confidence": "high"
  },
  "targeted": true,
  "target_test_file": "tests/test_auth.py",
  "results": {
    "exit_code": 0,
    "overall": "PASS",
    "total": 24,
    "passed": 24,
    "failed": 0,
    "skipped": 0,
    "errored": 0
  },
  "failures": [],
  "warnings": []
}
```

## Supported Frameworks

Python (pytest, unittest), JavaScript/TypeScript (Jest, Mocha, Vitest), Java/Kotlin (Maven, Gradle), Go (go test), C#/.NET (dotnet test), Rust (cargo test), Ruby (RSpec, Minitest).

## Error Handling

On failure, returns `{"status": "error", "error": "message", "repo_dir": "...", "test_framework": null, "results": null}`.

## Constraints

- NEVER modifies source code or test code.
- NEVER installs dependencies.
- NEVER runs tests with elevated privileges (sudo).
- Test timeout: max 600 seconds.
- Output truncated to last 50 lines in `raw_output_tail`.
