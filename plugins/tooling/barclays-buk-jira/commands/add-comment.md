---
description: Post a comment to a JIRA issue
user-invocable: true
argument-hint: "<ISSUE-KEY> <comment body>"
---

You are the main Claude Code agent.

When the user runs `/barclays-buk-jira:add-comment`, they want to post a comment to a JIRA issue.

## Instructions

1. **Parse arguments**: First token is the issue key; the remainder is the comment body.

2. **Delegate to Subagent**: Delegate to the `barclays-buk-jira:jira-agent` subagent with:
   - `OPERATION=AddComment`
   - `ISSUE_KEY=<first token>`
   - `ARGS=<remaining text as comment body>`

3. **Fallback**: If the subagent is unavailable, inform the user and suggest reinstalling the plugin.

## Usage Examples

```bash
/barclays-buk-jira:add-comment BUKL2CUSX-173655 MR created: https://app.gitlab.barcapint.com/.../merge_requests/62
```

## Example Output

```
{
  "id": "98765",
  "issue_key": "BUKL2CUSX-173655",
  "message": "Comment added to BUKL2CUSX-173655."
}
```
