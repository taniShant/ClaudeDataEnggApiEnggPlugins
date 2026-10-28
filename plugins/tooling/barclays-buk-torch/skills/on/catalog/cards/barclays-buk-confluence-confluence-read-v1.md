# barclays-buk-confluence-confluence-read-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-confluence-confluence-read-v1` |
| Plugin name | `barclays-buk-confluence` |
| Component type | skill-model-invocable |
| Owner | Vishal Khare |
| Action scope | read-only |
| Invocation mode | model-invocable |
| Installation / release | /plugin install barclays-buk-confluence@barclays-cio-buk |
| Native command | `/barclays-buk-confluence:confluence-read` |
| Skill name | `confluence-read` |

## Description

Fetch and read a specific Confluence page by ID or URL

## When to use

Use when you need to fetch and read a specific Confluence page by ID or URL. NOT for searching across Confluence (use confluence-search) or answering questions synthesized from multiple pages (use confluence-rag-ask).

## Inputs

- `PAGE_ID` (required, one of): A numeric Confluence page ID (e.g. `12345678`)
- `PAGE_URL` (required, one of): A full Confluence page URL (e.g. `https://confluence.example.com/spaces/ENG/pages/12345678/Deployment+Guide`)

## Preconditions

- The `barclays-buk-confluence` plugin must be installed and accessible
- The user must have network access to the internal Confluence instance
- Valid authentication/credentials for the Confluence API must be configured
- The target Confluence page must exist and the user must have read permissions on it

## Expected outputs

- A formatted summary of the Confluence page content with HTML stripped and content cleaned for readability
- Page metadata including: page title, space name, version number, last updated date, and last author
- The full page body text rendered as plain/readable content within the Claude Code session

## Exclusions

- Does not create, update, or delete Confluence pages
- Does not search Confluence spaces or perform keyword queries across multiple pages
- Does not list child pages, page trees, or space hierarchies
- Does not fetch page attachments, comments, or inline comments
- Does not handle authentication setup — credentials must already be configured
- Does not write any files to the local filesystem

## Verification

The capability completed successfully when a formatted page summary is displayed in the Claude Code session, including the page title, space name, version number, last-updated metadata, and readable body content. If the page ID or URL was invalid or inaccessible, an explicit error message will be shown instead.
