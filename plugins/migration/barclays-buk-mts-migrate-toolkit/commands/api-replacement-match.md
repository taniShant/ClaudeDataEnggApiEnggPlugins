---
description: Find candidate ODS replacement APIs for an MTS mainframe service, compare fields and TDL table overlap, and produce a confidence-scored match report
argument-hint: <ServiceName.method> [--spaces spacekey1,spacekey2] [--url https://confluence.barcapint.com/...]
---

You are the main Claude Code agent. When the user runs `/api-replacement-match`, you will find candidate ODS replacement APIs from multiple sources (Backstage catalogue index, seed catalogue, and Confluence spaces), compare request/response fields and TDL table overlap against the MTS service documentation, and produce a confidence-scored match report.

**Important:** This plugin compares API specifications only. It does NOT inspect code (no converters, no mappers, no config files). The match score reflects whether the ODS API **can** provide the same data as the MTS service, based on their respective documentation.

**Output:** A match report at `docs/mts/api-match-<ServiceName>-<method>.md`.

**Search Sources (13 layers, in priority order):**
1. **Backstage Catalogue** — GitLab software templates repo (2000+ BUK API components, live clone)
2. **Seed Catalogue + pcbcooiit** — ODS sAPI LLD pages (read-only enquiry APIs)
3. **PCBICCAPIS** — TC 31 API Catalog (pAPIs, dAPIs, iAPIs — process/domain APIs)
4. **COOCUSTCRM** — z/OS Connect sAPIs (system APIs — primary for write operations)
5. **GRPQRTUKBA** — UKBA z/OS sAPIs (conditional — when UKBA tables/IMS codes detected)
6. **BCDUKCAPI** — Cards & Lending APIs (conditional — when Cards/Lending SOAP stubs detected)
7a. **EST** — Open Banking APIs (conditional — when account/payment/consent/PSD2 detected)
7b. **DCMDEV** — DCM APIs (conditional — when document/correspondence/CMOD detected)
7c. **APITECHDES** — API Index (ALWAYS — master cross-reference) + Digital Channels
7d. **EMMAPIS** — EMM / Customer Insights APIs (conditional — when insights/marketing detected)
7e. **EPZOSCON** — EP z/OS Connect APIs (conditional — when payments/branch accounting/debit cards detected)
8. **Deep Investigation** — broader searches, user-supplied `--spaces`, widened Backstage search

**Execution Order (optimized):**
```
Step 1:   Load MTS service doc (sequential — needed by everything)
Step 1.9: Check Confluence tool availability (quick probe)

Launch IN PARALLEL (single tool-call message):
  - Step 1.5 agent: Downstream impact analysis
  - Step 2:         Candidate search (Layers 1-8 per api-match-search-layers.md)

Wait for both to complete.

Step 3:   Launch match agent with combined data from Step 1.5 + Step 2
Step 4:   Report
```

---

## Input Parsing

Parse the argument to extract:

1. **Method identifier** — one of:
   - Method name only: `findByPrimaryKey`
   - Qualified name: `CustomerGateway.findByPrimaryKey`
   - Confluence URL (additional candidate): `--url https://confluence.barcapint.com/pages/viewpage.action?pageId=852701158`
2. **Additional spaces** (optional): `--spaces pcbcooiit,anotherspacekey`

**Default Confluence spaces:** `pcbcooiit` and `COOCUSTCRM` (always included in searches).
**Default Backstage source:** `backstage_catalogue_index.md` (always available — local file, no MCP required).

If the argument is only a Confluence URL without a method name, report an error:
```
Error: Please provide a service method name. Example:
  /api-replacement-match CustomerGateway.findByPrimaryKey
  /api-replacement-match findByPrimaryKey --url https://...
```

---

## Step 1 — Load or Generate MTS Service Doc

### 1a. Find existing doc

```
Glob docs/mts/service-doc-*<method>*.md
```

If the argument includes a gateway name (e.g., `CustomerGateway.findByPrimaryKey`), also match against the gateway prefix:
```
Glob docs/mts/service-doc-*<GatewayName>*<method>*.md
```

### 1b. If found — extract MTS service data

Read the service doc and extract the following data points:

- **TDL tables**: From Section 6 (Backend Mappings) — the "TDL Tables Accessed" sub-section. Collect all TDL table names (e.g., TDLBAHO, TDLMAHO, TDLCAHO).
- **Transaction names**: From Section 6 — "Transaction Identity" sub-section. Extract both the CICS Programme Code (e.g., `TDLQCU`) and the Messaging/ROP name (e.g., `CUS_ALL_RETRIEVE_VO`).
- **Gateway class + method**: From Section 2 (Overview) and Section 3 (Call Flow).
- **Request fields**: From Section 4 (Request & Response) — the field table listing each request field, its type, and source.
- **Response fields**: From Section 4 and Section 5 (End-to-End Field Mapping) — the field mapping table with field names and types.
- **DataGroups requested**: From Section 6 — "DataGroup Chain" sub-section. Collect the DataGroup enum values.
- **Source systems**: From Section 6 and the summary — identify which source systems are involved (CS, UKBA, Triumph, PFS, etc.).
- **Service category**: From Section 1 — Transport row (mainframe-mq / oracle-db-direct / soap-stub / etc.).
- **Migration complexity indicators**: From Section 9 (Migration Complexity Indicators) — extract the full indicator table if present. Pass this data to the match agent for inclusion in its report.

### 1c. If NOT found — auto-generate

Run `/mts-documentation <method>` in single-service mode first:

```
/mts-documentation <method>
```

Wait for it to complete, then re-read the generated doc at:
```
Glob docs/mts/service-doc-*<method>*.md
```

Extract the same data points as in Step 1b.

### 1d. Verify field completeness

After extracting response fields from Section 6 and Section 7, check:
- Are all top-level arrays from Section 7 represented in Section 6's sample JSON?
- Does Section 7 include field-level tables for ALL sub-object types mentioned in the response?

If gaps exist, note them — the match agent prompt should mention which data groups have incomplete field coverage so the agent knows it may need to use fallback sources.

---

## Step 1.8 — Check for Existing Match Report (Cache)

Before running the expensive analysis, check if a match report already exists:

```
Glob docs/mts/api-match-*<method>*.md
```

If a match report is found:
- Read its first 10 lines to extract the generation date (look for a date in the header/metadata)
- If generated **today**: Ask the user via `AskUserQuestion`:
  - question: "An existing match report was found at `<path>`. Regenerate?"
  - options:
    - "Yes — regenerate from scratch"
    - "No — use the existing report"
  - If "No": Read the report and skip to Step 4 (Report). STOP here.
- If generated on a **previous day**: Continue with regeneration (don't ask).

---

## Step 1.9 — Confluence Tool Availability Check

Before running Layer 2 searches, detect whether Confluence MCP tools are available at runtime:

1. Attempt: `confluence_search(cql="space=pcbcooiit AND type=page", limit=1)`
2. If it returns results: Set `CONFLUENCE_AVAILABLE = true`
3. If tool not found, authorization error, or any error: Set `CONFLUENCE_AVAILABLE = false`
   - Log: `"WARNING: Confluence MCP tools not available. Using seed catalogue + GitLab only."`

This probe determines which search layers are available in Step 2.

---

## Step 1.9b — GitLab Tool Availability Check

Before running Deep Fetch (GitLab spec repo + gateway equivalence searches), detect whether GitLab MCP tools are authenticated:

1. Attempt: `mcp__GitLab__search(scope="projects", search="sodscustenq", per_page=1)`
2. If it returns results: Set `GITLAB_AVAILABLE = true`
3. If tool not found, authorization error, or any error: Set `GITLAB_AVAILABLE = false`
   - Log: `"WARNING: GitLab MCP tools not available or not authenticated. Deep Fetch will be skipped — field mappings will be unverified."`
   - Ask the user via `AskUserQuestion`:
     - question: "GitLab MCP is not authenticated. Deep Fetch (spec repo lookup, gateway equivalence) will be skipped. Response field scores will be discounted as unverified. Proceed anyway, or authenticate first?"
     - options:
       - "Proceed without GitLab (unverified mode)"
       - "Stop — I'll authenticate GitLab first"
   - If "Stop": STOP execution. Tell user to authenticate and re-run.

Pass `GITLAB_AVAILABLE` to Step 2 as a search input (alongside `CONFLUENCE_AVAILABLE`).

---

### Staleness Warning

Read the catalogue metadata from `ods_api_catalogue.md` — check the `Last full refresh` date. If the date is more than 30 days ago:

```
WARNING: Seed catalogue last refreshed on YYYY-MM-DD (>30 days ago).
Run /refresh-ods-catalogue to update. Page IDs may be stale.
```

Print this warning to the user before proceeding.

---

## Step 1.5 + Step 2 — Parallel Execution

> **CRITICAL — DO NOT SHORTCUT THE SEARCH.**
> You MUST execute ALL search layers for EVERY service. Do NOT:
> - Provide candidate data from memory or prior match reports
> - Skip Backstage grep because you "already know" the answer
> - Skip GitLab search because Confluence returned data
> - Assume the same ODS API matches because a similar service matched it
>
> Each service may have different TDL tables, DataGroups, and field requirements
> that change which ODS API is the best match. Execute the searches fresh.

**Launch Step 1.5 and Step 2 IN PARALLEL using a single message with multiple Task tool calls.** These steps are completely independent — they both use data from Step 1 but do not depend on each other.

### Step 1.5 — Downstream Impact Analysis (launched as parallel agent)

Launch a `general-purpose` agent (model: `sonnet`) to analyze downstream impacts:
- The agent reads the service doc and identifies converter classes, mapper classes, and configuration referenced by the MTS service
- It reads those files from the codebase and documents the downstream call chain

**Performance: The Step 1.5 agent MUST read all converter/mapper files in parallel tool-call messages.** When multiple independent files need reading (e.g., 6 sub-converter files, multiple mapper files, property files), read them ALL in ONE parallel tool-call message. Do NOT read them one at a time. This reduces 65 sequential calls to ~10-15 parallel batches.

Include this performance instruction in the agent prompt:
```
PERFORMANCE RULE: When you need to read multiple independent files, issue ALL Read
tool calls in a SINGLE message. For example, if you identify 6 sub-converter files
in a parent converter, read all 6 in one parallel tool call. Same for mapper files
and property files. Never read files one at a time when they are independent.
```

### Step 2 — Find Candidate ODS APIs (launched in parallel with Step 1.5)

Proceed with Step 1.95 (Backstage clone) then the search layers below.

---

## Step 1.95 — Clone/Pull Backstage Software Catalogue (MANDATORY)

Before searching for candidates, ensure the Backstage software catalogue is available locally:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/backstage_clone.py
```

Parse the output:
- `BACKSTAGE_REPO_PATH` — path to the cloned repo (typically `/tmp/software-catalogue-templates`)
- `BACKSTAGE_REPO_STATUS` — `CLONED`, `PULLED`, or `FAILED`
- `BACKSTAGE_COMPONENT_COUNT` — number of YAML files in `components/`

If `BACKSTAGE_REPO_STATUS = FAILED`: Set `BACKSTAGE_SOURCE = STATIC` and fall back to `backstage_catalogue_index.md`.
If `BACKSTAGE_REPO_STATUS = CLONED` or `PULLED`: Set `BACKSTAGE_SOURCE = LIVE`.

---

## Step 2 — Find Candidate ODS APIs (13-Layer Search)

> **Full search strategy is defined in:** `${CLAUDE_PLUGIN_ROOT}/skills/mts-reference/reference/api-match-search-layers.md`
> **Read that file** and follow ALL instructions: Layers 1-6, 7a-7e, 8 (Deep Investigation),
> Deep Fetch (Steps A/A2/A2b/B), Quality Check, E2E Mapping, Additional Investigation, and Search Exhaustion Log.

### Search inputs to pass forward

- `BACKSTAGE_SOURCE` and `BACKSTAGE_REPO_PATH` (from Step 1.95)
- `CONFLUENCE_AVAILABLE` (from Step 1.9)
- `GITLAB_AVAILABLE` (from Step 1.9b)
- MTS service data from Step 1: TDL tables, transaction names, gateway class + method, transport type, source systems, DataGroups
- `IS_WRITE` flag: set to `true` if the method name contains create/update/modify/amend/delete/remove/maintain/set/put

### Search outputs to collect for Step 3

After completing all search layers per the reference file, collect:
- Top 5 deduplicated candidates (name, source type, endpoints, response fields)
- Gateway equivalence flags per candidate (`gateway_equivalent`, `gateway_evidence` — from Deep Fetch Step A2)
- DB table equivalence flags for oracle-db-direct transport (from Step A2b)
- Documentation completeness per candidate (`full-schema` / `partial-endpoints` / `metadata-only`)
- E2E mapping data for the winning candidate (if found)
- VPT/test page evidence (endpoint URLs, API versions — from Additional Investigation)
- Search exhaustion log (all layers, queries tried, results)

---

## Step 2.9 — Search Verification Checkpoint (MANDATORY)

**Before proceeding to Step 3, verify the search was actually executed.** Print the following checklist to confirm:

```
SEARCH VERIFICATION:
- [x/!] Step 1.95 Backstage clone: BACKSTAGE_SOURCE=<LIVE|STATIC>, COMPONENT_COUNT=<N>
- [x/!] Confluence probe: CONFLUENCE_AVAILABLE=<true/false>
- [x/!] GitLab probe: GITLAB_AVAILABLE=<true/false>
- [x/!] Layer 1 Backstage (<LIVE|STATIC>): Ran <N> grep searches — found <N> candidates
- [x/!] Layer 2 pcbcooiit: Checked seed catalogue + CQL — found <N> candidates
- [x/!] Layer 3 PCBICCAPIS: <ran/skipped (reason)> — found <N> candidates
- [x/!] Layer 4 COOCUSTCRM: <ran/skipped (reason)> — found <N> candidates
- [x/!] Layer 5 GRPQRTUKBA: <ran/skipped (reason)> — found <N> candidates
- [x/!] Layer 6 BCDUKCAPI: <ran/skipped (reason)> — found <N> candidates
- [x/!] Layer 7a EST: <ran/skipped (reason)> — found <N> candidates
- [x/!] Layer 7b DCMDEV: <ran/skipped (reason)> — found <N> candidates
- [x/!] Layer 7c APITECHDES: <ran/skipped (reason)> — found <N> candidates
- [x/!] Layer 7d EMMAPIS: <ran/skipped (reason)> — found <N> candidates
- [x/!] Layer 7e EPZOSCON: <ran/skipped (reason)> — found <N> candidates
- [x/!] GitLab OpenAPI: Searched <N> repos for OpenAPI/swagger — found specs: <yes/no>
Total unique candidates: <N>
Top 3 for scoring: <name1>, <name2>, <name3>
```

**If Step 1.95 was not executed:** STOP. Run `backstage_clone.py` first.
**If Layer 1 Backstage was not executed:** STOP. Go back and run the Backstage Grep searches.
**If GitLab was not searched for any candidate with a GitLab slug:** STOP. Go back and run the GitLab search.

Only after this checkpoint passes may you proceed to Step 3.

---

## Step 3 — Score Candidates and Deep-Map the Winner

Ensure the output directory exists:
```bash
mkdir -p docs/mts
```

Determine the output file name:
- If gateway name is known: `docs/mts/api-match-<GatewayName>-<method>.md`
- If only method name: `docs/mts/api-match-<method>.md`

Launch **one** `mts-api-match-agent` using the Task tool:

```
Task tool call:
  subagent_type: general-purpose
  model: sonnet
  prompt: <include the full agent instructions from agents/mts-api-match-agent.md, followed by:>
    - MTS service data extracted in Step 1
    - Per-candidate ODS API data extracted in Step 2 (for each of the top 3 candidates)
    - Output file path
```

The agent prompt MUST include:
1. The full agent system prompt (from `agents/mts-api-match-agent.md`)
2. All extracted MTS service data from Step 1 (TDL tables, transaction names, request/response fields, gateway, DataGroups, source systems, category, per-service doc path)
3. All extracted ODS API data for each candidate from Step 2, including:
   - **Source type**: backstage-catalogue / seed-catalogue / pcbcooiit / COOCUSTCRM / PCBICCAPIS / user-space / broad
   - For Confluence candidates: API name, endpoint, request params, **full list of available query params and what data they return**, response fields/schema, TDL references, fallback txn names, source systems, error responses, page URL
   - For GitLab candidates: component name, description, tags, providesApis, links, owner, system, lifecycle — plus any Confluence page data if a linked page was also fetched
4. The output file path
5. **Search exhaustion log** (from Layers 1-6, 7a-7e, 8) — for inclusion in Section 5 of the report
6. **VPT/test page evidence** — any endpoint URLs, query parameters, API versions discovered
   from performance test or VPT pages. Format:
   - Endpoint: `GET /JourneyDetails?sourceSystem=...&pageStartIndex=...`
   - Source: Confluence page URL and title
   - Evidence type: "VPT test URL" / "SOM document" / "delivery doc"
7. **Documentation completeness flag** per candidate:
   - `full-schema`: OpenAPI spec or Confluence API page with endpoint + request + response fields
   - `partial-endpoints`: Endpoint paths known but no response field schema
   - `metadata-only`: Only Backstage index name/description/tags, no API documentation
8. **Gateway equivalence flags** per candidate:
   - `gateway_equivalent: true/false` — whether GitLab source search (Step A2) found the MTS gateway class name or transaction name in the candidate's source repo
   - `gateway_evidence: "<search term found>"` — what was found (e.g., "CustomerGateway found in CustomerDataGroup.java")
   - The match agent applies the Gateway-Equivalence Boost per `api-match-scoring.md`
9. **Enum completeness:** When passing Map<Enum, Value> fields, the orchestrator MUST
   include ALL enum constants from the service doc. Cross-check against the HoldingsMenuType
   (or equivalent) enum declaration in the service doc Section 8 (VERBATIM Field Declarations)
   or Section 5 (field mapping). Do NOT omit any enum value — each maps to a separate row
   in Section 4 and may have a different match status.
10. **Unverified flag** per candidate:
   - `unverified: true/false` — set to `true` when `GITLAB_AVAILABLE = false` AND the candidate
     has no Confluence-sourced response field schema (i.e., fields were inferred from seed
     catalogue or Backstage metadata only, not verified against OpenAPI spec or Confluence LLD)
   - When `unverified = true`: the match agent applies a 25% discount to Dimension 3 score
     (see `api-match-scoring.md` "Unverified Field Discount" section)

**Important:** Do NOT pass any code-level data (no converter classes, no mapper classes, no application.properties config). The agent works purely from API documentation.

---

## Step 4 — Report

After the agent completes:

1. **Confirm file exists:**
   ```
   Glob docs/mts/api-match-*.md
   ```

2. **Read the generated file** to extract the top match name, confidence score, and field mapping stats.

3. **Report to user:**
   ```
   API replacement match complete:
   - docs/mts/api-match-<ServiceName>-<method>.md

   Top match: <API Name> -- <confidence>% (<confidence band>)
   Candidates evaluated: <N>
   Field mapping: <X> MTS fields matched, <Y> missing, <Z> new ODS fields
   ODS query params needed: <list of query params that cover the MTS data groups>
   [Any warnings about missing data, truncated pages, or low confidence]
   ```

4. **Ask if they want to match another service:**
   Use `AskUserQuestion`:
   - question: "Would you like to match another MTS service against ODS APIs?"
   - options:
     - "Yes — provide another service name"
     - "No — done for now"

---

## Error Handling

- **No MTS service doc found and auto-generation fails:** Report the error and suggest the user run `/mts-documentation <method>` manually first.
- **No candidates found in any layer:** Report: "No candidate ODS APIs found across Backstage index, seed catalogue, or Confluence for this service. This may be a service without a current ODS replacement, or the ODS API may be in a different source. Try providing a direct URL with `--url` or additional spaces with `--spaces`."
- **Confluence search fails or returns empty for a specific space:** Log a warning (e.g., "COOCUSTCRM search failed — MCP auth may be expired") and continue with other sources. Do NOT abort the entire search.
- **Backstage index not found:** Report: "Backstage catalogue index not found at expected path. Run `/refresh-ods-catalogue` to regenerate it."
- **Page fetch fails for a candidate:** Skip that candidate and continue with remaining ones. Note the skip in the report.
- **MTS service is reference-data-only:** Proceed with matching but note in the report that TDL table overlap scoring is not applicable (weight redistributed).
- **Fewer than 3 candidates:** Proceed with however many are available. The match agent handles 1-3 candidates.
- **All MCP sources fail:** If Confluence MCP calls fail, fall back to Backstage index + seed catalogue matches only. If those also have no matches, report: "No candidates found. Provide a direct URL with `--url` or additional spaces with `--spaces`."
- **SSO redirect on deep fetch:** If the first `confluence_search` page-fetch returns SSO/SAML redirect content, skip all remaining deep fetches. Use Backstage metadata and seed catalogue data only.
- **Stale seed catalogue:** If the catalogue's `Last full refresh` date is >30 days old, print a warning suggesting `/refresh-ods-catalogue` but continue with available data.