---
name: jira-add-comment
user-invocable: false
description: >
    Use this skill to post a comment to a JIRA issue. Accepts plain text or
    JIRA wiki markup. This is the primary skill used by push agents to post
    MR links and generation summaries after a successful push.
    This operation is best-effort — a failure must never block a push or
    primary workflow. Log the warning and continue.
---

# JIRA Add Comment

Post a comment to a JIRA issue. Delegates to `barclays-buk-jira:jira-agent` with `OPERATION=AddComment`.

## Prerequisites

`JIRA_AUTH_TOKEN` environment variable must be set.

## Invocation

```
OPERATION:  AddComment
ISSUE_KEY:  BUKL2CUSX-173655
ARGS:       "Code generated successfully.\n\nMR: https://app.gitlab.barcapint.com/...\nPlatform: Glue\nFiles: transform.py, wrapper.py"
```

The `ARGS` value is the comment body. Plain text and JIRA wiki markup are both accepted.

## Output (success)

```json
{
  "id": "98765",
  "issue_key": "BUKL2CUSX-173655",
  "author": "Automation Bot",
  "created": "2026-09-11T15:00:00.000+0000",
  "message": "Comment added to BUKL2CUSX-173655."
}
```

## Graceful Degradation

If `JIRA_AUTH_TOKEN` is not set or the API returns an error:
- Log the warning with the HTTP status and response
- **Continue** — do not block the push or any calling workflow
- Report the skipped step in the output summary

## Agent Self-Check

- [ ] `JIRA_AUTH_TOKEN` validated; missing token produces a warning, not a hard stop
- [ ] HTTP 201 is success; anything else is a warning logged and skipped
- [ ] Comment body sourced from explicit input — never invented
- [ ] Issue key sourced from branch name or explicit `--jira-id` — never invented
