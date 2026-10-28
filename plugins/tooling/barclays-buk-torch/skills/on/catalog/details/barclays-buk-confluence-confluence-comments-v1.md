# barclays-buk-confluence-confluence-comments-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-confluence-confluence-comments-v1` |
| Plugin name | `barclays-buk-confluence` |
| Component type | skill-model-invocable |
| Owner | Vishal Khare |
| Action scope | read-only |
| Invocation mode | model-invocable |
| Installation / release | /plugin install barclays-buk-confluence@barclays-cio-buk |
| Native command | `/barclays-buk-confluence:confluence-comments` |
| Skill name | `confluence-comments` |

## Description

Read the discussion thread and inline comments on a specific Confluence page

## When to use

Use when you want to read the discussion thread or inline comments on a specific Confluence page.

## Inputs

- `PAGE_ID` (required, one of): A numeric Confluence page ID (e.g. `12345678`)
- `PAGE_URL` (required, one of): A full Confluence page URL from which the page ID is extracted

## Preconditions

- The `barclays-buk-confluence` plugin must be installed and accessible
- The user must have network access to the internal Confluence instance
- Valid authentication/credentials for the Confluence API must be configured
- The target Confluence page must exist and the user must have read permissions on it

## Expected outputs

- A formatted list of comments and discussion threads on the page, each entry including:
  - Author name and comment date
  - Comment body with HTML stripped for readability
- Inline comments (annotations) and page-level comments are both returned where available

## Exclusions

- Does not read the main body content of the page — use confluence-read for that
- Does not create, edit, or delete comments
- Does not fetch page attachments or version history
- Does not handle authentication setup — credentials must already be configured

## Verification

The capability completed successfully when a list of comments is displayed with author, date, and content for each entry. If the page has no comments, an explicit message stating that no comments exist will be shown. If the page ID or URL is invalid, an error message will be returned.
