---
name: confluence-read
user-invocable: false
description: >
    Use this skill whenever the user wants to read or view a specific Confluence page.
    Trigger phrases include: "read this confluence page", "summarize the wiki page",
    "what does the page say about", "open this confluence page", "show me the page",
    "fetch the confluence page", "get the wiki page content", "read page ID",
    or when the user pastes a Confluence URL and wants to see its content.
    This skill fetches page content via the REST API, strips HTML, and presents
    a clean readable summary with metadata.
---

# Confluence Read

> **Source:** Migrated from barclays-claude-code-plugins/plugins/confluence
> **Owner:** BUK Platform Engineering
> **Review trigger:** When Confluence REST API version changes or content storage format is updated
> **Status:** Active

---

Fetch and display the full content of a Confluence page by its page ID or URL. The skill retrieves the page body, strips HTML markup, and presents clean readable text with metadata including title, space, version, author, and date.

## Quick Start

```bash
# 1. Set environment variables
export CONFLUENCE_BASE_URL=https://confluence.example.com
export CONF_PAT=<your-token>

# 2. Read by page ID
/barclays-buk-confluence:read 12345678

# 3. Read by URL
/barclays-buk-confluence:read https://confluence.example.com/spaces/ENG/pages/12345678/Deployment+Guide
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

The skill delegates to the `barclays-buk-confluence:confluence-agent` subagent, which resolves the page ID (from a URL if needed), fetches the page content via the Confluence REST API, and strips HTML to produce readable output.

### API Endpoint

```
GET /rest/api/content/{id}?expand=body.storage,space,version,ancestors
```

### URL Resolution

The agent can extract page IDs from various Confluence URL formats:

| URL Pattern | Extracted ID |
|------------|-------------|
| `/spaces/ENG/pages/12345/Page+Title` | `12345` |
| `/pages/12345/` | `12345` |
| `?pageId=12345` | `12345` |

### Content Processing

1. The raw HTML body (`body.storage.value`) is fetched from the API
2. HTML tags are stripped using python3 regex processing
3. HTML entities are unescaped for clean text
4. Whitespace is normalized for readability
5. Long pages (over 3000 words) get a TL;DR summary at the top

## Example Invocations

### Using the command directly

```bash
/barclays-buk-confluence:read 12345678
/barclays-buk-confluence:read https://confluence.example.com/spaces/ENG/pages/12345678/Deployment+Guide
```

### Using natural language (auto-triggered)

- "Read this confluence page: https://confluence.example.com/spaces/ENG/pages/12345"
- "Summarize the wiki page on deployment procedures"
- "What does the API design page say about versioning?"
- "Show me the content of confluence page 98765"

## Output Format

The page is displayed with metadata followed by the content:

```
# Deployment Guide
Space: Engineering | Version: 12 | Last updated: 2024-03-15 by Jane Smith

The deployment process follows a blue-green pattern with the following stages...
```

For pages exceeding 3000 words, a TL;DR summary appears before the full content.

## Alternative

You can also use the explicit command: `/barclays-buk-confluence:read [page ID or URL]`

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] Page ID is correctly extracted from URL or used directly from numeric input
- [ ] `CONF_PAT` and `CONFLUENCE_BASE_URL` environment variables are validated before making API calls
- [ ] HTML is fully stripped from the page body (no raw tags in output)
- [ ] Page metadata (title, space, version, author, date) is displayed
- [ ] Long pages (3000+ words) include a TL;DR summary
- [ ] HTTP error codes are handled gracefully with user-friendly messages
- [ ] Only GET requests are used (read-only constraint respected)
