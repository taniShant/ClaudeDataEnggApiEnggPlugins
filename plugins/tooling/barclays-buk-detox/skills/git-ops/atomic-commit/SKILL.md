---
name: atomic-commit
description: "Atomic Commit — Create a single, focused git commit for one CWE remediation fix using the deterministic Python script."
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/git_ops/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Atomic Commit

## Purpose

Create a single, focused git commit for one CWE remediation fix. Each commit contains only the files relevant to that specific fix, uses a standardized commit message format (`fix(CWE-XX): <description>`), and must not include unrelated changes.

## Implementation

This skill is implemented as a **deterministic Python script** at `scripts/git/atomic_commit.py`. No LLM reasoning is required — the operation is purely mechanical git operations.

## Invocation

> `{python}` = the verified Python 3 command (`python3`, `py -3` or `python`) from the calling agent's Python Interpreter rule. Detox never installs Python — if none is available, STOP.

```bash
echo '{
  "cwe_id": "CWE-89",
  "files": ["/absolute/path/to/file.py"],
  "description": "Parameterize SQL queries in user_repository.py",
  "repo_dir": "/path/to/repo",
  "jira_id": "PROJ-1234",
  "verification_result": {"verdict": "PASS"},
  "allow_unvalidated": false
}' | {python} $PLUGIN_DIR/scripts/git/atomic_commit.py
```

## Input Schema

| Field | Required | Type | Description |
|---|---|---|---|
| `cwe_id` | Yes | string | CWE identifier (e.g., `CWE-89`) |
| `files` | Yes | list[string] | Absolute paths to files modified by this fix |
| `description` | Yes | string | Concise fix description (max 200 chars) |
| `repo_dir` | Yes | string | Absolute path to repository root |
| `jira_id` | No | string | JIRA ticket ID for commit message prefix |
| `verification_result` | No | object | Rescan validator output (`{"verdict": "PASS"}`) |
| `allow_unvalidated` | No | boolean | Allow commit without verification (default: false) |

## Output Schema

```json
{
  "status": "success",
  "commit_sha": "abc1234...",
  "commit_message_subject": "fix(CWE-89): Parameterize SQL queries in user_repository.py",
  "cwe_id": "CWE-89",
  "files_committed": ["src/repositories/user_repository.py"],
  "verification_verdict": "PASS",
  "warnings": []
}
```

## Error Handling

On failure, returns `{"status": "error", "error": "message", "stage": "validation|verification_check|staging|commit"}`.

## Constraints

- One CWE per commit — never combine multiple CWE fixes.
- Only specified files are staged — never uses `git add .` or `git add -A`.
- No force operations (`--amend`, `--force`, `reset --hard`).
- No hooks bypass (`--no-verify`).
- Rejects secret files (`.env`, `*.pem`, `*.key`, `credentials.json`).
- Subject line ≤ 72 characters.
- Commit message format: `fix(CWE-<number>): <description>`.
