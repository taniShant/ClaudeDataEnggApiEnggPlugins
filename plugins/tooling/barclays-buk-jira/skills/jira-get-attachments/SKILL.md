---
name: jira-get-attachments
user-invocable: false
description: >
    Use this skill to list all attachments on a JIRA issue.
    Returns filename, size, MIME type, author, created date, and download URL
    for each attachment. Use before jira-download-attachment to discover IDs.
    Trigger when an agent needs to find mapping spreadsheets, spec documents,
    or other artefacts attached to a ticket.
---

# JIRA Get Attachments

List all attachments on a JIRA issue. Delegates to `barclays-buk-jira:jira-agent` with `OPERATION=GetAttachments`.

## Prerequisites

`JIRA_AUTH_TOKEN` environment variable must be set.

## Invocation

```
OPERATION:  GetAttachments
ISSUE_KEY:  BUKL2CUSX-173655
```

## Output

```json
{
  "issue_key": "BUKL2CUSX-173655",
  "total": 2,
  "attachments": [
    {
      "id": "12345",
      "filename": "mapping_spec.xlsx",
      "size": 45678,
      "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "author": "Jane Smith",
      "created": "2026-09-01T10:00:00.000+0000",
      "content": "https://estjira.barcapint.com/secure/attachment/12345/mapping_spec.xlsx"
    }
  ]
}
```

## Typical Follow-On

Pass the `id` of a relevant attachment to `barclays-buk-jira:jira-download-attachment` to retrieve its parsed content.

## Agent Self-Check

- [ ] `JIRA_AUTH_TOKEN` validated before API call
- [ ] HTTP status checked; non-200 handled
- [ ] Attachment IDs and content URLs included in output for downstream use
