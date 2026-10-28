# barclays-buk-jira-jira-agent-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-jira-jira-agent-v1` |
| Plugin name | `barclays-buk-jira` |
| Component type | agent-plugin |
| Owner | BUK CDAO Platform |
| Action scope | read-only |
| Invocation mode | tool/agent — no slash command |
| Installation / release | /plugin install barclays-buk-jira@barclays-cio-buk |

## Description

_No skill entry point — invoked through plugin tools/agents._

## Inputs

- `JIRA_ISSUE_KEY` — JIRA issue key in the format `PROJECT-NNNNN` (e.g. `BUKL2CUSX-173655`); required for all operations
- `OPERATION` — one of: `GetIssue`, `GetAttachments`, `DownloadAttachment`, `AddComment`
- `ATTACHMENT_ID` — integer attachment ID; required only for `DownloadAttachment`; obtain from a prior `GetAttachments` call
- `ARGS` — comment body (plain text or JIRA wiki markup); required only for `AddComment`
- `JIRA_AUTH_TOKEN` — personal access token from `https://estjira.barcapint.com/secure/ViewProfile.jspa`; must be set as an environment variable before invoking the agent

## Preconditions

- `barclays-buk-jira` plugin installed via `/plugin install barclays-buk-jira@barclays-cio-buk`
- `JIRA_AUTH_TOKEN` environment variable set to a valid personal access token
- Network connectivity to `estjira.barcapint.com`
- For `DownloadAttachment` with spreadsheet files: `openpyxl` installed (`pip install openpyxl`); for `.docx`: `python-docx`; for `.pdf`: `pdfplumber`

## Expected outputs

- **GetIssue**: structured JSON object containing summary, description, status, assignee, reporter, priority, issue type, labels, components, fix versions, linked issues, subtasks, comment count, and a direct URL to the issue
- **GetAttachments**: JSON listing all attachments on the issue with filename, size, MIME type, author, created date, download URL, and attachment ID for use with `DownloadAttachment`
- **DownloadAttachment**: JSON object with filename, extension, size, and `parsed_content` — spreadsheets rendered as markdown tables, documents and PDFs as extracted text, structured text files as raw UTF-8; image files return metadata only
- **AddComment**: JSON confirmation with comment ID, issue key, author, and creation timestamp; failures are logged as warnings and do not block calling workflows

## Exclusions

- Does not create, update, or delete JIRA issues or subtasks
- Does not search or browse JIRA — a valid issue key must be known before invocation
- Does not parse image attachments beyond filename, size, and MIME type metadata
- Comment posting (`AddComment`) is best-effort — failure is logged but never propagated as a hard error

## Verification

After a `GetIssue` call, confirm the returned JSON contains a non-null `summary` and `url` field matching the requested issue key. After a `DownloadAttachment` call, confirm `parsed_content` is non-empty and that the `filename` field matches the attachment selected from the prior `GetAttachments` response. After `AddComment`, confirm the returned `id` is a non-null integer.
