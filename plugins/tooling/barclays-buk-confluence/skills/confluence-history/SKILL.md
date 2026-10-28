---
name: confluence-history
user-invocable: false
description: >
    Use this skill whenever the user wants to see the edit history or version
    history of a Confluence page. Trigger phrases include: "who edited this page",
    "when was this page last updated", "show page history",
    "version history of this confluence page", "what changes were made to the page",
    "who last modified", "show me the revisions", "page changelog",
    "when did someone last edit", "what versions does this page have".
    This skill fetches the version history via the REST API and displays
    a chronological table of edits with author, date, and version comments.
---

# Confluence History

> **Source:** Migrated from barclays-claude-code-plugins/plugins/confluence
> **Owner:** BUK Platform Engineering
> **Review trigger:** When Confluence REST API version changes or experimental endpoints are promoted to stable
> **Status:** Active

---

View the edit history of a Confluence page. This skill fetches the version history via the REST API and displays a chronological table showing who made each edit, when it happened, and what version comment was left.

## Quick Start

```bash
# 1. Set environment variables
export CONFLUENCE_BASE_URL=https://confluence.example.com
export CONF_PAT=<your-token>

# 2. View history by page ID
/barclays-buk-confluence:history 12345678

# 3. View history by URL
/barclays-buk-confluence:history https://confluence.example.com/spaces/ENG/pages/12345678/API+Design+Guide
```

## Prerequisites

Two environment variables must be set before using this skill:

- `CONFLUENCE_BASE_URL` — the base URL of your Confluence instance (e.g. `https://confluence.example.com`). Must NOT have a trailing slash.
- `CONF_PAT` — your Confluence Personal Access Token (PAT) for Bearer authentication

To generate a PAT, visit: `https://confluence.barcapint.com/plugins/personalaccesstokens/usertokens.action`

Set the variables in your shell environment:

```bash
# macOS / Linux (add to ~/.zshrc or ~/.bashrc to persist)
export CONFLUENCE_BASE_URL=https://confluence.example.com
export CONF_PAT=<your-token>

# Windows (Command Prompt)
setx CONFLUENCE_BASE_URL "https://confluence.example.com"
setx CONF_PAT "<your-token>"

# Windows (PowerShell)
[System.Environment]::SetEnvironmentVariable("CONFLUENCE_BASE_URL", "https://confluence.example.com", "User")
[System.Environment]::SetEnvironmentVariable("CONF_PAT", "<your-token>", "User")
```

## How It Works

The skill delegates to the `barclays-buk-confluence:confluence-agent` subagent, which resolves the page ID (from URL if needed), fetches the version history, and formats it as a readable table.

### API Endpoint

```
GET /rest/experimental/content/{id}/version?limit=25
```

### Response Processing

The agent extracts from each version entry:
- **Version number** — incremental version identifier
- **Author** — the `displayName` of the editor
- **Date** — the `when` timestamp, formatted as `YYYY-MM-DD`
- **Message** — the version comment left by the editor (if any)

### Data Extraction with jq

```bash
curl -s -H "Authorization: Bearer $CONF_PAT" -H "Accept: application/json" \
  "$CONFLUENCE_BASE_URL/rest/experimental/content/$PAGE_ID/version?limit=25" \
  | jq -r '.results[] | "\(.number)\t\(.by.displayName)\t\(.when[:10])\t\(.message // "No message")"'
```

## Example Invocations

### Using the command directly

```bash
/barclays-buk-confluence:history 12345678
/barclays-buk-confluence:history https://confluence.example.com/spaces/ENG/pages/12345678/API+Design+Guide
```

### Using natural language (auto-triggered)

- "Who edited the API Design Guide page on confluence?"
- "When was the deployment runbook last updated?"
- "Show me the version history of confluence page 98765"
- "What changes were made to the architecture doc recently?"

## Output Format

Results are displayed as a markdown table sorted chronologically:

```
## Version History for "API Design Guide"

| Version | Author          | Date       | Message                     |
|---------|-----------------|------------|-----------------------------|
| 1       | Jane Smith      | 2024-01-15 | Initial creation            |
| 2       | John Doe        | 2024-02-20 | Updated endpoint section    |
| 3       | Jane Smith      | 2024-03-10 | Added authentication flow   |
| 4       | Alice Johnson   | 2024-03-15 | Fixed formatting issues     |
```

The most recent 25 versions are shown by default. The table includes version number, author display name, edit date, and the version comment (or "No message" if none was provided).

## Alternative

You can also use the explicit command: `/barclays-buk-confluence:history [page ID or URL]`

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] Page ID is correctly extracted from URL or used directly from numeric input
- [ ] `CONF_PAT` and `CONFLUENCE_BASE_URL` environment variables are validated before making API calls
- [ ] Version history is formatted as a markdown table with Version, Author, Date, and Message columns
- [ ] Missing version messages default to "No message" rather than empty or null
- [ ] HTTP error codes are handled gracefully with user-friendly messages
- [ ] Only GET requests are used (read-only constraint respected)
