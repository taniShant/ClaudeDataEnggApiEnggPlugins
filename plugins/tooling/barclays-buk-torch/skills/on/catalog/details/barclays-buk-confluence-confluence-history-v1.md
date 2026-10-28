# barclays-buk-confluence-confluence-history-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-confluence-confluence-history-v1` |
| Plugin name | `barclays-buk-confluence` |
| Component type | skill-model-invocable |
| Owner | Vishal Khare |
| Action scope | read-only |
| Invocation mode | model-invocable |
| Installation / release | /plugin install barclays-buk-confluence@barclays-cio-buk |
| Native command | `/barclays-buk-confluence:confluence-history` |
| Skill name | `confluence-history` |

## Description

View the edit history and version changelog of a Confluence page

## When to use

Use when you want to view the edit history or version changelog of a Confluence page.

## Inputs

- `PAGE_ID` (required, one of): A numeric Confluence page ID (e.g. `12345678`)
- `PAGE_URL` (required, one of): A full Confluence page URL from which the page ID is extracted

## Preconditions

- The `barclays-buk-confluence` plugin must be installed and accessible
- The user must have network access to the internal Confluence instance
- Valid authentication/credentials for the Confluence API must be configured
- The target Confluence page must exist and the user must have read permissions on it

## Expected outputs

- A chronological table of page versions, each entry including:
  - Version number
  - Author who made the edit
  - Date and time of the edit
  - Version comment or change summary (where provided by the editor)

## Exclusions

- Does not read the main body content of any version — use confluence-read for that
- Does not restore or revert the page to a prior version
- Does not create, edit, or delete page content
- Does not fetch comments or attachments

## Verification

The capability completed successfully when a version table is displayed with author, date, version number, and any available version comments for each entry. If only one version exists, a single-row table is returned. If the page ID or URL is invalid, an error message will be shown.
