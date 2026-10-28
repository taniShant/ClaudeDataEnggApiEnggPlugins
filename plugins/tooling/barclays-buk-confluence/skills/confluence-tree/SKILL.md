---
name: confluence-tree
user-invocable: false
description: >
    Use this skill whenever the user wants to browse the page hierarchy or
    structure of a Confluence space or see child pages under a specific page.
    Trigger phrases include: "show me the pages in this space",
    "browse the confluence space", "page hierarchy", "what pages are under",
    "table of contents for the space", "list pages in confluence space",
    "show the page tree", "child pages of", "space structure",
    "what documentation exists in the space".
    This skill fetches page hierarchies via the REST API and renders them
    as an indented tree structure.
---

# Confluence Tree

> **Source:** Migrated from barclays-claude-code-plugins/plugins/confluence
> **Owner:** BUK Platform Engineering
> **Review trigger:** When Confluence REST API version changes or pagination behaviour is updated
> **Status:** Active

---

Browse the page hierarchy of a Confluence space or view child pages under a specific parent page. This skill fetches the page structure via the REST API and renders it as a visual indented tree, making it easy to understand how documentation is organized.

## Quick Start

```bash
# 1. Set environment variables
export CONFLUENCE_BASE_URL=https://confluence.example.com
export CONF_PAT=<your-token>

# 2. Browse a space
/barclays-buk-confluence:tree ENG

# 3. Browse children of a page
/barclays-buk-confluence:tree 12345678
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

The skill delegates to the `barclays-buk-confluence:confluence-agent` subagent, which determines whether the input is a space key or page ID, fetches the page hierarchy, and renders it as a tree.

### API Endpoints

For browsing an entire space:
```
GET /rest/api/space/{key}/content/page?depth=all&limit=100
```

For browsing children of a specific page:
```
GET /rest/api/content/{id}/child/page?limit=100&expand=children.page
```

### Input Detection

The agent determines the input type automatically:

| Input | Detected As | API Used |
|-------|------------|----------|
| `ENG` | Space key (all uppercase, short) | Space content endpoint |
| `12345678` | Page ID (numeric) | Child page endpoint |
| Full URL | Page ID (extracted from URL) | Child page endpoint |

### Tree Rendering

Pages are rendered with Unicode box-drawing characters for a clean visual tree:

```
├── Page Title
│   ├── Child Page
│   └── Another Child
└── Last Top-Level Page
```

By default, the tree shows 2 levels of depth. The agent can fetch deeper hierarchies if requested.

## Example Invocations

### Using the command directly

```bash
/barclays-buk-confluence:tree ENG
/barclays-buk-confluence:tree 12345678
```

### Using natural language (auto-triggered)

- "Show me the pages in the Engineering confluence space"
- "What documentation exists in the PLAT space?"
- "Browse the page hierarchy under the Architecture section"
- "What child pages are under the Runbooks page?"
- "Show the table of contents for the ENG space"

## Output Format

The tree is displayed with the space or parent page name at the top:

```
Space: Engineering (ENG)
├── Architecture
│   ├── API Design Guidelines
│   └── Database Schema Docs
├── Runbooks
│   ├── Deployment Process
│   └── Incident Response
└── Onboarding
    ├── New Starter Guide
    └── Team Directory
```

For large spaces with many pages, results are limited to 100 pages per level. The agent will note if there are additional pages beyond the limit.

## Alternative

You can also use the explicit command: `/barclays-buk-confluence:tree [space key or page ID]`

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] Input is correctly classified as space key (uppercase, short) or page ID (numeric)
- [ ] `CONF_PAT` and `CONFLUENCE_BASE_URL` environment variables are validated before making API calls
- [ ] Tree is rendered with Unicode box-drawing characters (not plain text indentation)
- [ ] Default depth is 2 levels unless the user requests more
- [ ] Large result sets (100+ pages) are noted with a truncation message
- [ ] HTTP error codes are handled gracefully with user-friendly messages
- [ ] Only GET requests are used (read-only constraint respected)
