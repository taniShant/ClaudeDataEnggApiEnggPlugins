---
description: Invoke Business Requirements Analyst — produce structured requirement from JIRA ticket or business input
disable-model-invocation: false
argument-hint: [<jira-ref|"business ask"|path>] [--modify <existing-requirement-path>]
---

# /dm-bra

Invoke the DM Business Requirements Analyst agent (Marcus) to produce a 9-section structured business requirement from a JIRA ticket, file, or informal business ask.

## Usage

```
/dm-bra BUKL2CUSX-2355
/dm-bra "Track savings eligibility under Consumer Duty"
/dm-bra path/to/business-input.md
/dm-bra --modify dm-output/BUKL2CUSX-2355/business-requirement.md
```

## Behaviour

### Step 1: Detect Input Type

Parse the user's argument to determine the input mode:

| Pattern | Mode | Example |
|---------|------|---------|
| Matches `[A-Z]+-\d+` (JIRA ref pattern) | **JIRA mode** | `BUKL2CUSX-2355` |
| Ends with `.md`, `.txt`, or is a valid file path | **File mode** | `path/to/input.md` |
| Starts with `--modify` | **Modify mode** | `--modify dm-output/.../business-requirement.md` |
| Anything else (quoted text or bare words) | **Direct mode** | `"Track savings eligibility"` |

### Step 2: Gather Context (Mode-Dependent)

#### JIRA Mode

1. **Fetch ticket** via JIRA MCP: `jira_get_issue(<jira-ref>)`
   - If fetch fails → report error with remediation steps, **HALT**
   - Extract: title, description, labels, linked issues, acceptance criteria

2. **Fetch attachments** via JIRA MCP: `jira_get_attachments(<jira-ref>)`
   - For each attachment: `jira_download_attachment(<attachment_id>)`
   - Parse binary content (xlsx → markdown table, docx → text, pdf → text)
   - If attachment download fails → log warning per attachment, continue with available content

3. **Extract Confluence links** from ticket description (URLs matching Confluence patterns)
   - For each linked page: fetch content via Confluence REST API (curl + CONF_PAT, following confluence-read skill pattern)
   - If page fetch fails → log warning, continue with remaining pages
   - If ALL Confluence fetches fail → proceed with JIRA content only

4. **Assemble full context** — ticket content + parsed attachments + Confluence pages

5. **Save audit trail** to `dm-output/<ref>/context/`:
   - `jira-ticket.md` — raw ticket content
   - `attachments.json` — attachment metadata and fetch status
   - `attachment_content.md` — parsed attachment content
   - `confluence-pages.md` — fetched Confluence page content

#### File Mode

1. Read the file at the specified path
2. If file not found → report error, **HALT**
3. Use file content as the business input

#### Direct Mode

1. Use the user's text as-is as the business input

#### Modify Mode

1. Read the existing requirement at the `--modify` path
2. If file not found → report error, **HALT**
3. Pass to agent in modify mode (Option 2)

### Step 3: Determine Reference Slug

- JIRA mode: use the JIRA ticket key (e.g., `BUKL2CUSX-2355`)
- File mode: use the filename stem (e.g., `business-input`)
- Direct mode: generate a slug from the first 5 words (e.g., `track-savings-eligibility-consumer-duty`)
- Modify mode: use the existing reference directory name

### Step 4: Create Output Directory

```
mkdir -p dm-output/<ref>/context/
mkdir -p data/source-domains/
```

**FDP Source Domains setup:** After creating directories, check if `data/source-domains/` contains any `.csv` files other than `sample_domain.csv`. If no real domain CSVs are present, emit:

> **FDP Source Domains:** The `data/source-domains/` folder is ready. To enable FDP-grounded data model design, place your domain CSV files here before running `/dm-model`. See the FDP Source Domains section in `README.md` for the expected CSV format.

If domain CSVs already exist, skip this message silently.

### Step 5: Invoke DM BRA Agent

Invoke `dm-bra-agent` via Agent tool with:
- The assembled context (ticket + attachments + Confluence OR file content OR text)
- **Explicit instruction to execute the full Intake Protocol (MANDATORY):** Tell the agent: "You MUST follow your complete Intake Protocol before producing any output. After classifying the input (Step 1) and passing the sufficiency check (Step 2), you MUST execute Step 3 (Ask Clarifying Questions) — ask up to 5 targeted clarifying questions and wait for the user's answers before producing the requirement document. Do NOT skip the clarifying questions step."
- If modify mode: the existing requirement content and the following instruction: "The user wants to modify an existing requirement — use Option 2. You MUST present the existing document to the user and ask 'What would you like to change?' with the three options (Add, Remove, Update). Wait for the user's explicit selection before making any amendments. Then apply the requested changes and produce the complete document using the Fixed Output Template."

### Step 6: Write Output

Write the agent's output to `dm-output/<ref>/business-requirement.md`.

### Step 7: Update Tracking

Read or create `dm-session/tracking.json` (schema: `schemas/dm_tracking.schema.json`).
Append to `commands_run` and update `outputs.business_requirement`.

### Step 8: Suggest Next Step

```
→ Next: Design the data model from this requirement:
  /dm-model dm-output/<ref>/business-requirement.md
```

If the agent returned a HARD STOP:
```
→ Action needed: Resolve the gaps listed above, then re-run:
  /dm-bra <input> [--modify dm-output/<ref>/business-requirement.md]
```

---

## Isolation

- Output goes to `dm-output/` — never touches `generated/` or `session/session_state.json`
- Tracking goes to `dm-session/` — never touches `session/`
- Existing plugin commands and hooks are unaffected
