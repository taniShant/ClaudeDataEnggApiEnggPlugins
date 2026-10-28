# barclays-buk-confluence-confluence-search-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-confluence-confluence-search-v1` |
| Plugin name | `barclays-buk-confluence` |
| Component type | skill-model-invocable |
| Owner | Vishal Khare |
| Action scope | read-only |
| Invocation mode | model-invocable |
| Installation / release | /plugin install barclays-buk-confluence@barclays-cio-buk |
| Native command | `/barclays-buk-confluence:confluence-search` |
| Skill name | `confluence-search` |

## Description

Search for Confluence pages by keywords and return matching results with titles and excerpts

## When to use

Use to search for Confluence pages by keywords; returns matching pages with titles and excerpts. NOT for reading full page content (use confluence-read) or answering questions synthesized from multiple pages (use confluence-rag-ask).

## Inputs

- `QUERY` (required): Search keywords or phrase (e.g. `authentication token refresh`)
- `SPACE` (optional): Confluence space key to scope the search (e.g. `ENG`)

## Preconditions

- The `barclays-buk-confluence` plugin must be installed and accessible
- Valid Confluence REST API connectivity and credentials must be configured
- The user must provide at least one keyword or phrase

## Expected outputs

- A numbered list of matching Confluence pages, each entry containing:
  - Page title as a clickable hyperlink
  - The Confluence space the page belongs to
  - Last-updated date and the name of the last author
- Results are formatted inline in the Claude Code conversation for quick scanning

## Exclusions

- Does not read or retrieve full page content — only returns search result summaries with titles and links
- Does not create, edit, update, or delete Confluence pages
- Does not handle authentication or credential management — assumed to be pre-configured
- Does not synthesize or answer questions from results — use confluence-rag-ask for that

## Verification

A successful run produces a numbered list of Confluence page results with clickable links, space names, and last-updated metadata. If no results match, the output explicitly states that no pages were found. If the plugin is unavailable, a clear error message suggesting plugin reinstallation is shown.
