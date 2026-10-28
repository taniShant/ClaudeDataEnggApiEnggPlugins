---
name: pr-creator
description: "MR Creator — Push branch and create GitLab merge request using the deterministic Python script."
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/git_ops/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Merge Request Creator

## Purpose

Push the remediation branch to the remote repository and create a merge request on GitLab using `glab mr create`. Handles branch pushing, MR title and body formatting, base branch targeting, and MR metadata (labels, reviewers).

## Implementation

This skill is implemented as a **deterministic Python script** at `scripts/git/pr_creator.py`. No LLM reasoning is required.

## Invocation

> `{python}` = the verified Python 3 command (`python3`, `py -3` or `python`) from the calling agent's Python Interpreter rule. Detox never installs Python — if none is available, STOP.

```bash
echo '{
  "repo_dir": "/path/to/repo",
  "branch_name": "remediate-cwe-79-89-20260429-143000",
  "base_branch": "main",
  "mr_title": "fix: CWE remediation for CWE-79, CWE-89",
  "mr_body": "## Summary\n...",
  "labels": ["security", "cwe-remediation", "automated"],
  "reviewers": [],
  "draft": false
}' | {python} $PLUGIN_DIR/scripts/git/pr_creator.py
```

## Input Schema

| Field | Required | Type | Description |
|---|---|---|---|
| `repo_dir` | Yes | string | Absolute path to repository root |
| `branch_name` | Yes | string | Branch to push and create MR from |
| `base_branch` | No | string | Target branch for MR (default: `main`) |
| `mr_title` | Yes | string | Merge request title (max 256 chars) |
| `mr_body` | Yes | string | Full MR body in Markdown |
| `labels` | No | list[string] | Labels to apply (default: `["security", "cwe-remediation", "automated"]`) |
| `reviewers` | No | list[string] | GitLab usernames to request as reviewers |
| `draft` | No | boolean | Create as draft MR (default: false) |

## Output Schema

```json
{
  "status": "success",
  "mr_url": "https://app.gitlab.barcapint.com/org/repo/-/merge_requests/42",
  "mr_iid": 42,
  "mr_title": "fix: CWE remediation for CWE-79, CWE-89",
  "branch_name": "remediate-cwe-79-89-20260429-143000",
  "base_branch": "main",
  "state": "opened",
  "commits_included": 5
}
```

## Error Handling

On failure, returns `{"status": "error", "error": "message", "stage": "validation|branch_check|glab_check|push|mr_creation"}`.

## Constraints

- No force push — never uses `git push --force`.
- No branch deletion.
- No merging — MR is created, not merged.
- Idempotent — if MR already exists for the branch, returns existing MR details.
- PAT security — never logs or prints the PAT value.
- Requires `glab` CLI installed and authenticated against `https://app.gitlab.barcapint.com`.
