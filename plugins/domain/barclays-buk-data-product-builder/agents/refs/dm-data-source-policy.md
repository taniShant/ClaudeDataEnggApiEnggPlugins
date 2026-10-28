---
description: "Hard requirements for data sourcing in DM agents — accepted sources (JIRA, Confluence, user input, attachments), prohibited sources (fabricated data, assumptions), and traceability enforcement."
owner: "Satish Khanna <satish.khanna@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-09
---

# Data Source Policy — DM Agents

**Purpose:** Hard requirements for data sourcing in `/dm-*` commands to prevent silent fallback to simulated data.

---

## Policy Statement

All requirement and data model documents produced by `/dm-*` commands MUST be traceable to actual, verified source data. No simulated, mocked, or example data is acceptable as input.

---

## Accepted Data Sources

1. **Live JIRA Tickets** — Fetched via JIRA MCP (`jira_get_issue`), HTTP 200 confirmed, full content extracted
2. **Live Confluence Pages** — Fetched via Confluence REST API (curl + CONF_PAT, confluence-read skill pattern), content verified
3. **User-Provided Business Asks** — Informal requirements provided directly by user in plaintext
4. **Existing Requirement Documents** — Files in `dm-output/<ref>/business-requirement.md` from prior runs
5. **JIRA Attachments** — Downloaded and parsed via JIRA MCP (`jira_download_attachment`), content extracted
6. **Confluence Page Attachments** — Downloaded via Confluence REST API (`GET /rest/api/content/{id}/child/attachment`), parsed from Excel/Word/PDF

## Rejected Data Sources

1. **Simulated/Mocked JIRA Tickets** — Generated from examples or training data → **HALT**
2. **Fabricated Confluence Pages** — Generated from domain knowledge when API fails → **HALT**
3. **Default/Fallback Requirements** — Proceeding with partial context after fetch failure → **HALT**
4. **Test/Example Data** — Using documentation examples as real input → **HALT**

---

## Enforcement Rules

### JIRA Reference Validation

When user provides a JIRA reference (e.g., `BUKL2CUSX-2355`):

1. Fetch ticket via JIRA MCP (`jira_get_issue`)
2. If success → extract content, continue
3. If 404/403/500/timeout → retry up to 3× → if still fails, **HALT**
4. **NEVER** create simulated ticket content as fallback

### Confluence Page Linking

When JIRA ticket has linked Confluence pages:

1. Extract Confluence URLs from ticket description
2. Fetch each page via Confluence REST API (curl + CONF_PAT, following confluence-read skill pattern)
3. If page fetch fails → log warning, continue with remaining pages
4. If ALL pages fail → proceed with JIRA content only (log warning)
5. **NEVER** generate fake Confluence page content

### Attachment Handling

When JIRA ticket has attachments:

1. List attachments via JIRA MCP (`jira_get_attachments`)
2. Download and parse each via JIRA MCP (`jira_download_attachment`)
3. If attachment download fails → log warning, note filename, continue
4. If ticket references attachments but none retrievable → **HARD STOP** (see BRA agent sufficiency check)
5. **NEVER** guess at attachment contents

### Business Ask Validation

When user provides informal text (not a JIRA reference):

1. Verify input is NOT a JIRA reference pattern
2. Treat as user-provided requirement content
3. Proceed directly — no API fetch needed

### Hard Failure Rule

When any required data source fetch fails:

1. Log full error (HTTP status, endpoint, retry count)
2. **Do NOT** proceed with partial/fake data
3. **Do NOT** silently skip the failing source
4. **HALT** and report: what failed, why, how to fix, how to retry

---

## Audit Trail

Every `/dm-bra` run in JIRA mode MUST produce audit files in `dm-output/<ref>/context/`:

| File | Content |
|------|---------|
| `jira-ticket.md` | Raw JIRA ticket content (proves real ticket was fetched) |
| `attachments.json` | Attachment metadata (filenames, types, sizes, fetch status) |
| `attachment_content.md` | Parsed attachment content (readable text from xlsx/docx/pdf) |
| `confluence-pages.md` | Fetched Confluence page content (or log of failed fetches) |

---

**This policy is non-negotiable. Enforcement is critical to document integrity.**
