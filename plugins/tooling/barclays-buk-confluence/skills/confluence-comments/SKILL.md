---
name: confluence-comments
user-invocable: false
description: >
    Use this skill whenever the user wants to read comments or discussion
    threads on a Confluence page. Trigger phrases include:
    "what are the comments on this page", "show page discussion",
    "read comments on the wiki page", "what did people say about",
    "show feedback on the confluence page", "page comments",
    "any discussion on this page", "read the comments on",
    "who commented on this page", "show the conversation on this doc".
    This skill fetches page comments via the REST API, strips HTML,
    and displays them as formatted discussion threads with author and date.
---

# Confluence Comments

> **Source:** Migrated from barclays-claude-code-plugins/plugins/confluence
> **Owner:** BUK Platform Engineering
> **Review trigger:** When Confluence REST API version changes or comment threading model is updated
> **Status:** Active

---

Read and display comments and discussion threads on a Confluence page. This skill fetches all comments via the REST API, strips HTML markup, and presents them as clean, chronologically ordered discussion threads with author names and dates.

## Quick Start

```bash
# 1. Set environment variables
export CONFLUENCE_BASE_URL=https://confluence.example.com
export CONF_PAT=<your-token>

# 2. Read comments by page ID
/barclays-buk-confluence:comments 12345678

# 3. Read comments by URL
/barclays-buk-confluence:comments https://confluence.example.com/spaces/ENG/pages/12345678/RFC+New+Auth+Flow
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

The skill delegates to the `barclays-buk-confluence:confluence-agent` subagent, which resolves the page ID (from URL if needed), fetches all comments including nested replies, strips HTML from comment bodies, and formats them as readable discussion threads.

### API Endpoint

```
GET /rest/api/content/{id}/child/comment?expand=body.storage,version&depth=all&limit=50
```

### Comment Processing

1. Comments are fetched with their storage-format HTML bodies
2. HTML tags are stripped using python3 regex processing
3. HTML entities are unescaped for clean text output
4. Comments are organized chronologically
5. Author display names and dates are extracted from the version metadata

### Data Extraction

```bash
curl -s -H "Authorization: Bearer $CONF_PAT" -H "Accept: application/json" \
  "$CONFLUENCE_BASE_URL/rest/api/content/$PAGE_ID/child/comment?expand=body.storage,version&depth=all&limit=50" \
  | python3 -c "
import json, sys, re, html
data = json.load(sys.stdin)
for c in data.get('results', []):
    author = c.get('version', {}).get('by', {}).get('displayName', 'Unknown')
    date = c.get('version', {}).get('when', '')[:10]
    body_html = c.get('body', {}).get('storage', {}).get('value', '')
    body = re.sub(r'<[^>]+>', ' ', body_html)
    body = html.unescape(body).strip()
    body = re.sub(r'\s+', ' ', body)
    print(f'**{author}** -- {date}:')
    print(f'{body}')
    print()
"
```

## Example Invocations

### Using the command directly

```bash
/barclays-buk-confluence:comments 12345678
/barclays-buk-confluence:comments https://confluence.example.com/spaces/ENG/pages/12345678/RFC+New+Auth+Flow
```

### Using natural language (auto-triggered)

- "What are the comments on the API Design page in confluence?"
- "Show the discussion on the RFC for the new auth flow"
- "Read the feedback on confluence page 98765"
- "Who commented on the deployment runbook?"
- "Any discussion on the architecture decision record?"

## Output Format

Comments are displayed as a formatted thread with the page title as a header:

```
## Comments on "RFC: New Auth Flow" (3 comments)

**Jane Smith** -- 2024-03-15:
This looks great, but we should update the API endpoint section to reflect the new gateway.

**John Doe** -- 2024-03-16:
Agreed. I'll update it this week. Should we also add the sequence diagram?

**Jane Smith** -- 2024-03-17:
Yes, a sequence diagram would be very helpful. Also consider adding the new token refresh flow.
```

If the page has no comments, the agent reports this clearly. Up to 50 comments are fetched per request, including nested reply threads.

## Alternative

You can also use the explicit command: `/barclays-buk-confluence:comments [page ID or URL]`

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] Page ID is correctly extracted from URL or used directly from numeric input
- [ ] `CONF_PAT` and `CONFLUENCE_BASE_URL` environment variables are validated before making API calls
- [ ] HTML is fully stripped from comment bodies (no raw tags in output)
- [ ] Comments display author name, date, and clean text content
- [ ] Pages with no comments report this clearly rather than showing empty output
- [ ] HTTP error codes are handled gracefully with user-friendly messages
- [ ] Only GET requests are used (read-only constraint respected)
