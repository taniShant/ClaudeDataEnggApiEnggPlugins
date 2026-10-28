# barclays-buk-confluence

Read-only Confluence integration for Claude Code. Search pages, read content, ask questions with RAG-style answers, view edit history, browse page trees, and read comments — all from within Claude Code.

## Dual Invocation: Deterministic Commands + Agentic Skills

This plugin's defining feature is its **dual invocation model**. Every capability is exposed in two ways simultaneously:

1. **Slash commands** — deterministic, explicit invocation when you know exactly what you want:
   ```
   /barclays-buk-confluence:search deployment runbook
   /barclays-buk-confluence:read 12345678
   ```

2. **Skills** — auto-triggered by Claude Code's harness when it recognises natural language intent:
   ```
   "What does our wiki say about the payments API?"
   "Who last edited the architecture decision record?"
   ```

This makes the plugin uniquely suited for **agentic development**. When you build your own agents or multi-step workflows, you don't need to wire up API calls or configure tool schemas. Just write natural language instructions in your agent markdown and the skill system handles the rest.

## Prerequisites

| Variable | Description |
|----------|-------------|
| `CONFLUENCE_BASE_URL` | Base URL of your Confluence instance (no trailing slash) |
| `CONF_PAT` | Your Confluence **Personal Access Token** (PAT) |

### Generating a Personal Access Token (PAT)

1. Visit: `https://confluence.barcapint.com/plugins/personalaccesstokens/usertokens.action`
2. Click **Create token**
3. Give it a name and click **Create**
4. Copy the generated token

### Setting the environment variables

**macOS / Linux** — add to `~/.zshrc` or `~/.bashrc` to persist:

```bash
export CONFLUENCE_BASE_URL=https://confluence.example.com
export CONF_PAT=<your-token>
# Then run: source ~/.zshrc  (or source ~/.bashrc)
```

**Windows (Command Prompt):**

```cmd
setx CONFLUENCE_BASE_URL "https://confluence.example.com"
setx CONF_PAT "<your-token>"
:: Restart your terminal after running these commands
```

**Windows (PowerShell):**

```powershell
[System.Environment]::SetEnvironmentVariable("CONFLUENCE_BASE_URL", "https://confluence.example.com", "User")
[System.Environment]::SetEnvironmentVariable("CONF_PAT", "<your-token>", "User")
# Restart your terminal after running these commands
```

## Commands & Skills

| Command | Skill | Description | Sample Prompt |
|---------|-------|-------------|---------------|
| `/barclays-buk-confluence:search [keywords or CQL]` | `confluence-search` | Search pages by keyword or CQL query | "Search confluence for the incident response runbook" |
| `/barclays-buk-confluence:read [page ID or URL]` | `confluence-read` | Fetch and summarize a Confluence page | "Read this confluence page https://confluence.example.com/pages/12345" |
| `/barclays-buk-confluence:ask [question]` | `confluence-rag-ask` | Ask a question answered from Confluence pages | "What does our wiki say about the payments API?" |
| `/barclays-buk-confluence:history [page ID or URL]` | `confluence-history` | Show edit history of a page | "Who last edited the architecture decision record?" |
| `/barclays-buk-confluence:tree [space key or page ID]` | `confluence-tree` | Browse page hierarchy in a space | "Show me all pages in the Platform space" |
| `/barclays-buk-confluence:comments [page ID or URL]` | `confluence-comments` | Read and summarize comments on a page | "What are the comments on this page?" |

## Usage Examples

### Search for pages
```bash
/barclays-buk-confluence:search deployment runbook
/barclays-buk-confluence:search type=page AND space=ENG AND text~"API design"
```

### Read a page
```bash
/barclays-buk-confluence:read 12345678
/barclays-buk-confluence:read https://confluence.example.com/spaces/ENG/pages/12345678/Deployment+Guide
```

### Ask a question (RAG)
```bash
/barclays-buk-confluence:ask How does our authentication service handle token refresh?
/barclays-buk-confluence:ask What is the deployment process for production releases?
```

### View edit history
```bash
/barclays-buk-confluence:history 12345678
```

### Browse page tree
```bash
/barclays-buk-confluence:tree ENG
/barclays-buk-confluence:tree 12345678
```

### Read/Summarize comments
```bash
/barclays-buk-confluence:comments 12345678
```

### Natural language (auto-triggered)
```
"Search confluence for the incident response runbook"
"What does our wiki say about the payments API?"
"Who last edited the architecture decision record?"
"Show me all pages in the Platform space"
```

## API Endpoints

All requests are read-only (GET only) and authenticated with a Personal Access Token (Bearer `CONF_PAT`).

| Operation | Endpoint |
|-----------|----------|
| Search | `GET /rest/api/content/search?cql={CQL}` |
| Read | `GET /rest/api/content/{id}?expand=body.storage,space,version,ancestors` |
| History | `GET /rest/experimental/content/{id}/version` |
| Tree (space) | `GET /rest/api/space/{key}/content/page` |
| Tree (page) | `GET /rest/api/content/{id}/child/page` |
| Comments | `GET /rest/api/content/{id}/child/comment` |

## Plugin Structure

```
plugins/tooling/barclays-buk-confluence/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   └── confluence-agent.md
├── commands/
│   ├── search.md
│   ├── read.md
│   ├── ask.md
│   ├── history.md
│   ├── tree.md
│   └── comments.md
├── skills/
│   ├── confluence-search/
│   │   └── SKILL.md
│   ├── confluence-read/
│   │   └── SKILL.md
│   ├── confluence-rag-ask/
│   │   └── SKILL.md
│   ├── confluence-history/
│   │   └── SKILL.md
│   ├── confluence-tree/
│   │   └── SKILL.md
│   └── confluence-comments/
│       └── SKILL.md
└── README.md
```

## Installation

```bash
/plugin  # Select "Add marketplace" → enter path to the BUK marketplace repo
/plugin  # Select "Browse and install plugins" → choose "barclays-buk-confluence"
```
