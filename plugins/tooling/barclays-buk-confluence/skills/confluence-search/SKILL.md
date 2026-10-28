---
name: confluence-search
user-invocable: false
description: >
    Use this skill whenever the user wants to search for Confluence pages.
    Trigger phrases include: "search confluence", "find on confluence",
    "look up docs on confluence", "search the wiki for", "find pages about",
    "look for confluence pages", "search wiki pages", "find documentation on",
    "what confluence pages mention", "search for docs about".
    This skill searches Confluence content via the REST API using CQL queries
    and returns a formatted list of matching pages with titles, spaces, and links.
---

# Confluence Search

> **Source:** Migrated from barclays-claude-code-plugins/plugins/confluence
> **Owner:** BUK Platform Engineering
> **Review trigger:** When Confluence REST API version changes or CQL syntax is updated
> **Status:** Active

---

Search for Confluence pages by keyword or CQL (Confluence Query Language) query. This skill uses the Confluence REST API to find pages matching your criteria and returns a formatted, clickable list of results.

## Quick Start

```bash
# 1. Set environment variables
export CONFLUENCE_BASE_URL=https://confluence.example.com
export CONF_PAT=<your-token>

# 2. Search by keyword
/barclays-buk-confluence:search deployment runbook

# 3. Search with CQL
/barclays-buk-confluence:search type=page AND space=ENG AND text~"API design"
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

The skill delegates to the `barclays-buk-confluence:confluence-agent` subagent, which constructs a CQL query from your input and calls the Confluence search API.

### API Endpoint

```
GET /rest/api/content/search?cql={CQL}&limit=10&expand=space,version
```

### CQL Query Construction

- **Plain keywords** are automatically wrapped: `type=page AND text~"your keywords"`
- **CQL queries** are passed through directly if they contain CQL operators (`=`, `~`, `AND`, `OR`, `type`, `space`)

### Example CQL Patterns

| Intent | CQL |
|--------|-----|
| Search all pages for a keyword | `type=page AND text~"deployment"` |
| Search within a specific space | `type=page AND space=ENG AND text~"runbook"` |
| Search by page title | `type=page AND title~"API Design"` |
| Recently modified pages | `type=page AND lastModified>now("-7d")` |
| Pages by a specific author | `type=page AND creator="john.doe"` |

## Example Invocations

### Using the command directly

```bash
/barclays-buk-confluence:search authentication API
/barclays-buk-confluence:search type=page AND space=ENG AND text~"deployment guide"
```

### Using natural language (auto-triggered)

- "Search confluence for authentication docs"
- "Find pages about the deployment process on the wiki"
- "Look up the incident response runbook on confluence"
- "What confluence pages mention the payments API?"

## Output Format

Results are displayed as a numbered list with clickable markdown links. Each page title MUST be a hyperlink:

```
1. [**Authentication Service Overview**](https://confluence.example.com/spaces/ENG/pages/12345/Authentication+Service+Overview) — Engineering — Last updated 2024-03-15 by Jane Smith

2. [**API Gateway Configuration**](https://confluence.example.com/spaces/PLAT/pages/67890/API+Gateway+Configuration) — Platform — Last updated 2024-02-20 by John Doe
```

If no results are found, the agent suggests alternative search terms or CQL queries to try.

## Alternative

You can also use the explicit command: `/barclays-buk-confluence:search [keywords or CQL]`

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] `CONF_PAT` and `CONFLUENCE_BASE_URL` environment variables are validated before making API calls
- [ ] User input is correctly classified as CQL or plain keywords
- [ ] CQL query is URL-encoded before being passed to the API
- [ ] Results include clickable markdown hyperlinks with page title, space, date, and author
- [ ] HTTP error codes are handled gracefully with user-friendly messages
- [ ] Only GET requests are used (read-only constraint respected)
