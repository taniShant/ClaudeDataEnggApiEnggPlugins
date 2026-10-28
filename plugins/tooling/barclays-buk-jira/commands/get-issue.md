---
description: Fetch full details of a JIRA issue by key
user-invocable: true
argument-hint: "<ISSUE-KEY>"
---

You are the main Claude Code agent.

When the user runs `/barclays-buk-jira:get-issue`, they want to fetch and display full metadata for a JIRA issue.

## Instructions

1. **Delegate to Subagent**: Delegate to the `barclays-buk-jira:jira-agent` subagent with:
   - `OPERATION=GetIssue`
   - `ISSUE_KEY=<user argument>`

2. **Fallback**: If the subagent is unavailable, inform the user and suggest reinstalling the plugin.

## Usage Examples

```bash
/barclays-buk-jira:get-issue BUKL2CUSX-173655
```

## Example Output

```
{
  "key": "BUKL2CUSX-173655",
  "summary": "Build FDP for mortgage repayment data",
  "status": "In Progress",
  "assignee": "Jane Smith",
  ...
}
```
