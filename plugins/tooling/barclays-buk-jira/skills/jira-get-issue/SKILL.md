---
name: jira-get-issue
user-invocable: false
description: >
    Use this skill to fetch full details of a single JIRA issue by key.
    Returns summary, description, status, assignee, reporter, priority,
    type, labels, components, fix versions, linked issues, subtasks,
    comment count, and a direct URL to the issue.
    Trigger when an agent needs ticket context before generating artefacts
    or populating a requirement template.
---

# JIRA Get Issue

Fetch full metadata for a JIRA issue by key. Delegates to the `barclays-buk-jira:jira-agent` subagent with `OPERATION=GetIssue`.

## Prerequisites

`JIRA_AUTH_TOKEN` environment variable must be set — a personal access token from `https://estjira.barcapint.com/secure/ViewProfile.jspa`.

## Invocation

```
OPERATION:  GetIssue
ISSUE_KEY:  BUKL2CUSX-173655
```

## Output

```json
{
  "key": "BUKL2CUSX-173655",
  "summary": "...",
  "description": "...",
  "status": "In Progress",
  "assignee": "Jane Smith",
  "reporter": "John Doe",
  "priority": "High",
  "issuetype": "Story",
  "labels": [],
  "components": ["Data Engineering"],
  "fixVersions": [],
  "created": "2026-01-10T09:00:00.000+0000",
  "updated": "2026-09-11T14:30:00.000+0000",
  "resolution": null,
  "comment_count": 3,
  "issuelinks": [],
  "subtasks": [],
  "url": "https://estjira.barcapint.com/browse/BUKL2CUSX-173655"
}
```

## Error Handling

If `JIRA_AUTH_TOKEN` is not set or the API returns an error, the agent reports the exact failure with remediation steps and stops. It does not proceed with incomplete data.

## Agent Self-Check

- [ ] `JIRA_AUTH_TOKEN` validated before API call
- [ ] HTTP status checked; non-200 handled with error message
- [ ] Output is structured JSON, not raw API response
- [ ] Issue key sourced from explicit input — never invented
