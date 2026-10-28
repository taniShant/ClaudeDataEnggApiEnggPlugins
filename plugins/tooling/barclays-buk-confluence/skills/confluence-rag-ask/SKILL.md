---
name: confluence-rag-ask
user-invocable: false
description: >
    Use this skill whenever the user asks a question that should be answered
    from Confluence or internal wiki content. Trigger phrases include:
    "what does confluence say about", "ask confluence", "find the answer on the wiki",
    "check the wiki for", "does our documentation cover",
    "what do our docs say about", "look up on confluence and answer",
    "answer from the wiki", or any question about internal processes, architecture,
    or team knowledge that is likely documented in Confluence.
    This skill performs RAG-style question answering by searching, reading top pages,
    and synthesizing an answer with citations.
---

# Confluence Ask (RAG Q&A)

> **Source:** Migrated from barclays-claude-code-plugins/plugins/confluence
> **Owner:** BUK Platform Engineering
> **Review trigger:** When Confluence REST API version changes or RAG citation requirements are updated
> **Status:** Active

---

Ask a natural language question and receive a comprehensive answer synthesized from relevant Confluence pages. This skill implements a RAG (Retrieval-Augmented Generation) pipeline: it searches for relevant pages, reads the top results, and synthesizes a cited answer.

## Quick Start

```bash
# 1. Set environment variables
export CONFLUENCE_BASE_URL=https://confluence.example.com
export CONF_PAT=<your-token>

# 2. Ask a question
/barclays-buk-confluence:ask How does our authentication service handle token refresh?

# 3. Ask about processes
/barclays-buk-confluence:ask What is the deployment process for production releases?
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

The skill delegates to the `barclays-buk-confluence:confluence-agent` subagent, which executes a multi-step RAG pipeline to answer the question from Confluence content.

### RAG Pipeline Steps

1. **Query Formulation** — Extract key terms from the question and build a CQL search query
2. **Search** — Call the Confluence search API to find up to 5 relevant pages
3. **Read** — Fetch the full content of the top 3 matching pages
4. **Synthesize** — Combine the page contents to produce a comprehensive answer
5. **Cite** — Include inline `[Page Title](URL)` citations **for every statement and fact** in the answer, embedded directly in the text where the information appears

### API Endpoints Used

```
GET /rest/api/content/search?cql={CQL}&limit=5&expand=space,version
GET /rest/api/content/{id}?expand=body.storage,space,version
```

### Citation Format

Answers include inline citations with visible URLs showing both page title and full link:

```
The deployment process uses blue-green deployments [Deployment Guide - https://confluence.example.com/pages/123] with
automated rollback capabilities described in the [Incident Response Runbook - https://confluence.example.com/pages/456].
```

The citation format must show both the page title AND the full URL so both are visible and clickable.

## Example Invocations

### Using the command directly

```bash
/barclays-buk-confluence:ask How does our authentication service handle token refresh?
/barclays-buk-confluence:ask What is the deployment process for production releases?
/barclays-buk-confluence:ask What databases does the payments service depend on?
```

### Using natural language (auto-triggered)

- "What does confluence say about our CI/CD pipeline?"
- "Ask the wiki how we handle database migrations"
- "Check our docs for the incident response process"
- "What do our internal docs say about the API rate limiting policy?"

## Output Format

The answer includes a synthesized response with **inline citations showing both page title and full URL for every statement**, embedded directly in the text:

```
The authentication service handles token refresh using a [rotating refresh token pattern - https://confluence.example.com/spaces/ENG/pages/111].
When a client presents an expired access token, the [auth middleware checks for a valid refresh token - https://confluence.example.com/spaces/ENG/pages/111]
and issues a [new access/refresh token pair - https://confluence.example.com/spaces/ENG/pages/111]. [Refresh tokens have a 30-day TTL - https://confluence.example.com/spaces/ENG/pages/222]
configured in the service properties.

## Sources
- [Auth Service Architecture](https://confluence.example.com/spaces/ENG/pages/111/Auth+Architecture) — Engineering
- [Service Configuration Guide](https://confluence.example.com/spaces/ENG/pages/222/Config+Guide) — Engineering
```

**Note**: Every claim, fact, or statement must be cited inline with both page title AND visible URL. Do not rely solely on a sources list at the end.

If no relevant pages are found, the agent reports this clearly and suggests refining the question.

## Alternative

You can also use the explicit command: `/barclays-buk-confluence:ask [your question]`

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] Key terms are correctly extracted from the user's question to form a CQL query
- [ ] Search returns results and the top 3 pages are read in full
- [ ] Every statement in the synthesized answer has an inline citation with page title and URL
- [ ] A Sources section is appended at the end listing all referenced pages
- [ ] When no relevant pages are found, this is reported clearly with suggestions
- [ ] `CONF_PAT` and `CONFLUENCE_BASE_URL` environment variables are validated before making API calls
- [ ] Only GET requests are used (read-only constraint respected)
