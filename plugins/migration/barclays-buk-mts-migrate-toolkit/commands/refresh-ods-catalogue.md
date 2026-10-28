---
description: Refresh the ODS API seed catalogue by validating entries against live Confluence and GitLab data
argument-hint: [--dry-run]
---

You are the main Claude Code agent. When the user runs `/refresh-ods-catalogue`, you will validate and update the seed catalogue file used by `/api-replacement-match`.

**Catalogue file:** `${CLAUDE_PLUGIN_ROOT}/skills/mts-reference/reference/ods_api_catalogue.md`

**Output:** Updated catalogue file with validated entries, new pages added, stale entries marked.

---

## Step 0 — Check Confluence Tool Availability

Before refreshing, detect whether Confluence MCP tools are available:

1. Attempt: `confluence_search(cql="space=pcbcooiit AND type=page", limit=1)`
2. If SUCCESS: Set `CONFLUENCE_AVAILABLE = true`
3. If TOOL NOT FOUND or ERROR: Set `CONFLUENCE_AVAILABLE = false`

If `CONFLUENCE_AVAILABLE = false`:
- Report: "Cannot refresh catalogue — Confluence MCP tools not available. Ensure the `Confluence` MCP server is configured with a valid Confluence PAT. See the MCP setup instructions in the plan."
- Suggest: "You can manually verify page IDs by visiting `https://confluence.barcapint.com/pages/viewpage.action?pageId=<ID>` in your browser."
- STOP — do not proceed with refresh.

---

## Step 1 — Read Current Catalogue

Read the catalogue file:
```
Read ${CLAUDE_PLUGIN_ROOT}/skills/mts-reference/reference/ods_api_catalogue.md
```

Parse:
- **Direct Mappings table**: Extract all Page IDs and their associated gateway methods
- **All ODS API Pages tables**: Extract all Page IDs from Source 1 (pcbcooiit) and Source 2 (COOCUSTCRM)
- **Catalogue Metadata**: Read the `Last full refresh` date

Collect a deduplicated list of all Page IDs in the catalogue.

---

## Step 2 — Validate pcbcooiit Pages (Source 1)

### 2a: List children of parent page

Fetch children of the pcbcooiit parent page (507590733):
```
confluence_get_page_children(parent_id="507590733", limit=50, include_content=false)
```

This returns the live set of child pages under the ODS API LLD parent.

### 2b: Cross-validate existing entries

For each Page ID in the catalogue's Source 1 table:
- If the page ID appears in the live children list: Mark as **VALID** — update the `Verified` date to today
- If the page ID does NOT appear in the live children list:
  - Attempt `confluence_get_page(page_id="<ID>")` to check if the page still exists elsewhere
  - If page exists but moved: Update the entry with a note `(moved from pcbcooiit)`
  - If page returns 404/error: Mark the entry as `STALE — page not found (as of YYYY-MM-DD)`

### 2c: Discover new pages

For each child page returned by Step 2a that is NOT already in the catalogue:
- Extract: Page ID, Title
- Derive keywords from the title (domain nouns, system names, TDL table references)
- Add a new row to the Source 1 table

---

## Step 3 — Validate COOCUSTCRM Pages (Source 2)

Run a CQL search to discover pages in the COOCUSTCRM space:
```
confluence_search(cql="space=COOCUSTCRM AND ancestor=1798520644 AND type=page", limit=50)
```

For each result:
- If already in the catalogue: Verify title matches, update `Verified` date
- If new: Add to the Source 2 table with extracted keywords

If the search fails (auth, space not found): Log a warning and skip this section. Do NOT mark existing COOCUSTCRM entries as stale based on a failed search.

---

## Step 3b — Validate Additional API Sources (v1.3 Spaces)

Validate each of the 7 additional Confluence spaces added in v1.3. For each space, confirm the parent page exists and count child pages.

**Run these validations IN PARALLEL (single tool-call message):**

```
confluence_search(search_pages=["559035965"], extract_content=false, max_results=1)    # EST
confluence_search(search_pages=["737076546"], extract_content=false, max_results=1)    # DCMDEV
confluence_search(search_pages=["1311225934"], extract_content=false, max_results=1)   # APITECHDES Index
confluence_search(search_pages=["1311226039"], extract_content=false, max_results=1)   # APITECHDES Digital
confluence_search(search_pages=["2214221355"], extract_content=false, max_results=1)   # EMMAPIS
confluence_search(search_pages=["954298640"], extract_content=false, max_results=1)    # EPZOSCON
```

For each space:
- If page found: Mark as **VALID**, record child page count if available
- If page returns error/404: Mark as **STALE** with note `(parent page not found as of YYYY-MM-DD)`
- Do NOT remove stale entries — mark them for investigation

**Optionally (if time permits):** For spaces marked VALID, run a descendant search to count available API pages:
```
confluence_search(search_pages=["<parent_page_id>"], search_descendants=true, extract_content=false, max_results=100)
```

Record the child page count in the "Additional API Sources (v1.3)" table's Notes column.

---

## Step 4 — Validate GitLab Entries (Source 3b)

Search GitLab for ODS system component projects:
```
gitlab_search(scope="projects", search="system-qry ods", per_page=50)
```

For each result:
- If the project is already in the catalogue (by project ID or name): Verify name matches
- If new: Add to the Source 3b table with project ID, name, domain, and keywords

If GitLab search fails: Log a warning and skip. Do NOT mark existing entries as stale.

---

## Step 5 — Update Direct Mappings Verification

For each entry in the Direct Mappings table:
- If the page ID was validated in Step 2b or 3: Update the `Verified` column to today's date
- If the page ID was marked STALE: Update the `Verified` column to `STALE — YYYY-MM-DD`
- Do NOT remove stale entries — mark them so the user can investigate

---

## Step 6 — Write Updated Catalogue

### 6a: Update metadata header

Update the Catalogue Metadata table:
- `Last full refresh`: Today's date (YYYY-MM-DD)
- `Entries`: Updated count of Confluence pages and GitLab projects

### 6b: Write the file

If `--dry-run` was specified:
- Print a summary of changes (new entries, stale entries, updated verifications) but do NOT write the file
- Report: "Dry run complete. Run `/refresh-ods-catalogue` without `--dry-run` to apply changes."

Otherwise:
- Write the updated catalogue file using the Edit tool (preserve all existing sections, only modify the tables and metadata)
- Also update the Keyword Index if new pages were added (derive keywords from page titles)

### 6c: Sync to commands directory

After writing the catalogue, no sync needed (the catalogue is in the skills directory, not commands).

---

## Step 7 — Report

Print a summary:

```
ODS API Catalogue Refresh Complete
===================================
Source 1 (pcbcooiit):  X valid, Y new, Z stale
Source 2 (COOCUSTCRM): X valid, Y new, Z stale
Source 3b (GitLab):    X valid, Y new

Additional Spaces (v1.3):
  EST (559035965):           VALID / STALE — <N> child pages
  DCMDEV (737076546):        VALID / STALE — <N> child pages
  APITECHDES (1311225934):   VALID / STALE — <N> child pages
  APITECHDES (1311226039):   VALID / STALE — <N> child pages
  EMMAPIS (2214221355):      VALID / STALE — <N> child pages
  EPZOSCON (954298640):      VALID / STALE — <N> child pages

Direct Mappings: X/7 verified, Y stale

Last refresh date updated to: YYYY-MM-DD

[If any entries are stale:]
WARNING: The following entries are stale (page not found):
  - Page ID XXXXXXX: <title> — last valid YYYY-MM-DD
  Action: Verify manually or remove from catalogue.
```

---

## Error Handling

- **Confluence MCP not available:** Stop immediately with setup instructions (Step 0).
- **Individual page fetch fails:** Log warning, mark as STALE, continue with other pages.
- **GitLab search fails:** Log warning, skip GitLab validation, continue with Confluence results.
- **Rate limiting:** If Confluence returns rate limit errors, wait 5 seconds and retry once. If still failing, log warning and skip remaining pages.
- **Catalogue file not found:** Report error — the file should exist at the expected path. Do not create a new one from scratch.
