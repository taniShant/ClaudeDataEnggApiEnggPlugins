# barclays-buk-jira

JIRA integration for Claude Code. Fetch issue details, list and download attachments, and post comments — all via the internal JIRA REST API at `estjira.barcapint.com`.

## Prerequisites

### Environment Variable

| Variable | Required | Description |
|----------|----------|-------------|
| `JIRA_AUTH_TOKEN` | Yes | Personal Access Token for JIRA authentication |

#### Generating a Personal Access Token (PAT)

1. Visit: `https://estjira.barcapint.com/secure/ViewProfile.jspa`
2. Click **Personal Access Tokens**
3. Create a new token and copy it

#### Setting the environment variable

**macOS / Linux** — add to `~/.zshrc` or `~/.bashrc` to persist:

```bash
export JIRA_AUTH_TOKEN='<your-token>'
# Then run: source ~/.zshrc  (or source ~/.bashrc)
```

**Windows (Command Prompt):**

```cmd
setx JIRA_AUTH_TOKEN "<your-token>"
:: Restart your terminal after running this command
```

**Windows (PowerShell):**

```powershell
[System.Environment]::SetEnvironmentVariable("JIRA_AUTH_TOKEN", "<your-token>", "User")
# Restart your terminal after running this command
```

### Python

`python` must be available on PATH. The plugin uses Python for JSON response processing and attachment parsing.

To verify: `python --version`

### Optional Python Packages (for attachment parsing)

These are only needed if you use the **DownloadAttachment** operation:

| Package | Extension | Install |
|---------|-----------|---------|
| `openpyxl` | `.xlsx`, `.xls` | `pip install openpyxl` |
| `python-docx` | `.docx`, `.doc` | `pip install python-docx` |
| `pdfplumber` | `.pdf` | `pip install pdfplumber` |

Plain text formats (`.json`, `.xml`, `.sql`, `.txt`, `.md`, `.yaml`, `.yml`, `.csv`) work without any extra packages.

## Commands & Skills

| Command | Skill | Description |
|---------|-------|-------------|
| `/barclays-buk-jira:get-issue <ISSUE-KEY>` | `jira-get-issue` | Fetch full issue details (summary, status, assignee, links, subtasks) |
| `/barclays-buk-jira:add-comment <ISSUE-KEY> <body>` | `jira-add-comment` | Post a comment to a JIRA issue |
| — | `jira-get-attachments` | List all attachments on a JIRA issue |
| — | `jira-download-attachment` | Download and parse an attachment by ID |

## Usage Examples

### Fetch issue details

```
/barclays-buk-jira:get-issue BUKL2CUSX-173655
```

### Post a comment

```
/barclays-buk-jira:add-comment BUKL2CUSX-173655 MR created: https://app.gitlab.barcapint.com/.../merge_requests/62
```

### Natural language (auto-triggered via skills)

```
"Get the details of BUKL2CUSX-173655"
"What attachments are on BUKL2CUSX-173655?"
"Download attachment 12345 from BUKL2CUSX-173655"
```

## Known Issues

### Windows: curl TLS handshake failure

On Windows, curl using the Schannel backend may fail with:

```
schannel: next InitializeSecurityContext failed: CRYPT_E_NO_REVOCATION_CHECK (0x80092012)
```

This happens when the CRL (Certificate Revocation List) endpoint is unreachable from the corporate network. The plugin already includes `--ssl-no-revoke` on all curl calls to work around this. The flag is Windows-only and silently ignored on Linux/macOS.

## Plugin Structure

```
barclays-buk-jira/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   └── jira-agent.md
├── commands/
│   ├── add-comment.md
│   └── get-issue.md
├── skills/
│   ├── jira-add-comment/
│   │   └── SKILL.md
│   ├── jira-download-attachment/
│   │   └── SKILL.md
│   ├── jira-get-attachments/
│   │   └── SKILL.md
│   └── jira-get-issue/
│       └── SKILL.md
└── README.md
```

## Installation

```
/plugin   # Select "Add marketplace" → enter path to the BUK marketplace repo
/plugin   # Select "Browse and install plugins" → choose "barclays-buk-jira"
```
