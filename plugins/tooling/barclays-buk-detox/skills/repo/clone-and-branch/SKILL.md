---
name: clone-and-branch
description: "Clone and Branch — Clone repository and create working branch using the deterministic Python script."
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/repo/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Clone and Branch

## Purpose

Clone a remote Git repository over HTTPS using a Personal Access Token (PAT) for authentication, then create and check out a dedicated working branch named `remediate-cwe-<ids>-<timestamp>` where all remediation changes will be committed.

## Implementation

This skill is implemented as a **deterministic Python script** at `scripts/git/repo_setup.py`. No LLM reasoning is required.

## Invocation

> `{python}` = the verified Python 3 command (`python3`, `py -3` or `python`) from the calling agent's Python Interpreter rule. Detox never installs Python — if none is available, STOP.

```bash
echo '{
  "repo_url": "https://app.gitlab.barcapint.com/org/repo.git",
  "cwe_ids": ["CWE-89", "CWE-79"],
  "clone_dir": null,
  "base_branch": "main",
  "git_pat_env_var": "GIT_PAT",
  "checkout_branch": null,
  "new_branch": null,
  "jira_id": null
}' | {python} $PLUGIN_DIR/scripts/git/repo_setup.py
```

## Input Schema

| Field | Required | Type | Description |
|---|---|---|---|
| `repo_url` | Yes | string | HTTPS URL or local path to repository |
| `cwe_ids` | No | list[string] | CWE identifiers for branch naming |
| `clone_dir` | No | string | Target directory (auto-generated if omitted) |
| `base_branch` | No | string | Base branch to clone (default: `main`) |
| `git_pat_env_var` | No | string | Env var name for PAT (default: `GIT_PAT`) |
| `checkout_branch` | No | string | Existing branch to checkout before branching |
| `new_branch` | No | string | Custom branch name override |

## Output Schema

```json
{
  "status": "success",
  "clone_dir": "/absolute/path/to/repo",
  "branch_name": "remediate-cwe-79-89-20260429-143000",
  "base_branch": "main",
  "commit_sha_head": "abc1234...",
  "gitignore_updated": true
}
```

## Error Handling

On failure, returns `{"status": "error", "error": "message", "stage": "input_validation|pat_validation|clone_prep|clone|branch_creation"}`.

## Constraints

- NEVER logs, prints, or includes the PAT in any output.
- NEVER clones via SSH — HTTPS with PAT only.
- Always clones fresh — uses incremental directory naming if target exists.
- Neutralizes stored remote URL after clone (strips PAT).
- Clone uses `--single-branch` for efficiency.
- All git operations must complete within 120 seconds.
