# barclays-buk-confluence-confluence-rag-ask-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-confluence-confluence-rag-ask-v1` |
| Plugin name | `barclays-buk-confluence` |
| Component type | skill-model-invocable |
| Owner | Vishal Khare |
| Action scope | read-only |
| Invocation mode | model-invocable |
| Installation / release | /plugin install barclays-buk-confluence@barclays-cio-buk |
| Native command | `/barclays-buk-confluence:confluence-rag-ask` |
| Skill name | `confluence-rag-ask` |

## Description

Ask a question and get an answer synthesized from Confluence pages, with citations

## When to use

Use when the user has a question that should be answered from Confluence or internal wiki content — e.g. questions about internal processes, architecture, or team knowledge that are likely documented; performs search + multi-page read + synthesis with citations. NOT for reading a specific known page (use confluence-read) or browsing space structure (use confluence-tree).

## Inputs

- `QUESTION` (required): Free-text question about internal processes, architecture, or team knowledge (e.g. `How does our authentication service handle token refresh?`)

## Preconditions

- The `barclays-buk-confluence` plugin must be installed and accessible
- The user must have network access to the internal Confluence instance
- Valid authentication/credentials for the Confluence API must be configured
- Relevant Confluence pages must already exist and be readable by the querying user

## Expected outputs

- A synthesized natural-language answer to the question, with every factual claim accompanied by an inline citation (`[Page Title - <full Confluence URL>]`)
- A consolidated **Sources** section listing all referenced Confluence pages with titles, URLs, and space names
- No files are created or modified on disk

## Exclusions

- Does not create, edit, delete, or publish any Confluence pages
- Does not perform searches outside of Confluence (e.g. Jira, GitHub, SharePoint)
- Does not modify any local files, repositories, or project state

## Verification

The capability completed successfully if you receive a prose answer with inline citations containing both a page title and a full Confluence URL for every factual claim, followed by a consolidated Sources section. If the plugin is unavailable, an explicit error message suggesting plugin reinstallation will be shown instead.
