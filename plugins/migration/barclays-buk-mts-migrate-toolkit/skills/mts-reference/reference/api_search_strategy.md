# API Candidate Search Strategy

Reference document for `/api-replacement-match` candidate discovery. Describes the 3-layer search, deduplication, ranking, and deep-fetch strategy.

## Search Priority Rule

**Always search for higher-level APIs first, then fall back to system APIs.**

The ODS API catalogue (`ods_api_catalogue.md` — "API Hierarchy & Search Priority") defines a 5-tier API taxonomy:

1. **First**, look for **Process APIs (pAPI)** or **Domain APIs (dAPI)** that aggregate the data.
2. **Then**, look for **Internal APIs (iAPI)** or **External APIs (xAPI)**.
3. **Last resort**: **System APIs (sAPI)** — the "ODS Retail ..." branded APIs.

**Read vs Write distinction:** ODS sAPIs are primarily read/enquiry operations. If the MTS method name contains `create`, `update`, `modify`, `amend`, `delete`, `remove`, `maintain`, `set`, or `put` — flag as a write operation and:
1. Search COOCUSTCRM z/OS Connect sAPIs FIRST (these have write support)
2. Search Backstage for pAPI/dAPI orchestration APIs (e.g., `srv-custdtlsmgmt-api`, `partycoredetailsmgmt-api`)
3. Include known write candidates: `cust-coreCustomerDetails-sAPI-v14.0` (page 3852609006), `cust-membershipMaintenance-sAPI-v1.0` (page 2164463698), `cust-customerPreferences-sAPI-v1.1` (page 1850479771)
4. Do NOT report "NOT FEASIBLE" without checking all 3 sources

**NO GitLab search:** Do NOT search GitLab source repos. All candidate discovery uses: (1) Backstage catalogue index, (2) pcbcooiit Confluence space, (3) COOCUSTCRM Confluence space.

## Canonical TDL Table Rule

When extracting TDL tables from the MTS service doc, use **ALL tables from Section 9** — including tables from ALL code paths. Collect the union of all tables. This is the canonical TDL table set for Dimension 1 scoring.

## Layer 1: Backstage Catalogue Index Lookup (highest priority, local file)

Read the Backstage catalogue index:
```
Read ${CLAUDE_PLUGIN_ROOT}/skills/mts-reference/reference/backstage_catalogue_index.md
```

Static fallback catalogue (used when live Backstage repo clone fails). No MCP calls needed.

**Search strategy — use Grep tool against the index file:**

Extract the domain noun from the gateway class name by stripping "Gateway", "Eao", "Service", "Delegate" suffixes (e.g., `CustomerGateway` -> "Customer").

| Search | Pattern | Purpose |
|--------|---------|---------|
| B1 — Domain noun | `<domain_noun>` (case-insensitive) | Matches Name, Title, Description, Domain, Tags |
| B2 — System-specific | `buk/ods` | Returns all 52 ODS system APIs |
| B3 — Domain-specific | `<backstage_domain>` (e.g., `buk-domain-customer-party`) | Domain-scoped results |
| B4 — Method-semantic | `enquiry` / `qry` / `create` / `mgt` etc. | Functional purpose of method |
| B5 — Backend system | `cust` / `account` / `ukba` / `card` / `membership` | Backend system keywords |

For each matching row, extract: Name, Title, System, Domain, Tags, Description, Confluence URL, GitLab Slug. Store as `source = "backstage-catalogue"`.

## Layer 2: Seed Catalogue Lookup

Read the seed catalogue:
```
Read ${CLAUDE_PLUGIN_ROOT}/skills/mts-reference/reference/ods_api_catalogue.md
```

Search using:
1. **Gateway method name**: Look in "Direct Mappings" table.
2. **Transaction name**: Look for CICS code or EGS Transaction name.
3. **TDL table overlap**: Look in "Keyword Index" for TDL table names.
4. **Backend system match**: Check "Backend Source Systems" table.
5. **Known API Endpoints**: Check "Known API Endpoints by Layer" tables.

Add all matched page IDs with `source = "seed-catalogue"`.

**Mandatory Seed Catalogue Inclusion Rule:** ALL candidates from the seed catalogue that match via rules 1-5 MUST be included. Do NOT filter out during deduplication. If a seed candidate also appears in Backstage or Confluence results, merge metadata but keep the candidate.

## Layer 3: Confluence Search (fallback — if fewer than 5 candidates from Layers 1+2)

**Confluence availability branching:**
- If `CONFLUENCE_AVAILABLE = true` AND fewer than 5 unique candidates: Run sub-layers 3a, 3b, 3c.
- If `CONFLUENCE_AVAILABLE = true` AND 5+ candidates: Skip Confluence search.
- If `CONFLUENCE_AVAILABLE = false`: Skip all Confluence searches.

### 3a: pcbcooiit Space

| Search | CQL Pattern |
|--------|------------|
| A — Gateway broad | `title~"<DomainNoun>" AND space="pcbcooiit"` |
| A2 — Method-semantic | `title~"<DomainNoun>" AND title~"Enquiry" AND space="pcbcooiit"` |
| B — Transaction keywords | `siteSearch ~ "<CICS code>" AND space="pcbcooiit"` |
| C — TDL tables | `siteSearch ~ "<TDL table>" AND space="pcbcooiit"` |
| D — User URL | Extract page ID from `--url` parameter (if given) |

### 3b: COOCUSTCRM Space

Run the SAME search patterns (A, A2, B, C) against `COOCUSTCRM`.

### 3c: Additional Spaces + Broad Fallback

Run searches A and A2 against any user-provided `--spaces`.

**Search E — Broad fallback:** If all layers yield fewer than 5 candidates, run a broad siteSearch across ALL spaces (no space filter).

### Transport-Specific Search Hints

| Transport | Additional Strategy |
|-----------|-------------------|
| `mainframe-mq` | Standard (TDL, transaction names) |
| `soap-stub` / `soap-eao` | Domain noun + operation semantics + backend system name |
| `oracle-db-direct` / `db2-reference` | "Static Data Hub" in Confluence, specific table names |
| `cmod-odwek` | "CMOD replacement API", "ODWEK migration", "Document retrieval API" |
| `scv` | Card-specific ODS APIs, "SingleCustomerView replacement" |
| `tcv-hybrid` | Apply strategy matching the legacy path's transport type |

### ZOS Candidate Tagging

After collecting candidates, tag each candidate's `source_type`. For ZOS fallback APIs set `source_type = "zos-fallback"`. All others retain their original source_type.

## Deduplication and Ranking

**Deduplication:** Merge results from all layers. Remove duplicates by name. Merge metadata for candidates appearing in multiple sources.

**Ranking (priority order):**
1. Seed catalogue direct match (highest priority)
2. Multi-search hit count
3. TDL table name hit count
4. Title/component keyword match count
5. Source priority (tiebreaker): seed-catalogue > backstage-catalogue > pcbcooiit > COOCUSTCRM > user-space > broad

Keep the top 5 unique candidates for Deep Fetch evaluation.

## Deep Fetch: Top 3 Candidates

Select top 3 ranked candidates. Fetch strategy depends on source type.

**Confluence availability:** If `CONFLUENCE_AVAILABLE = false`, skip all Confluence deep fetches.

**SSO Detection / Fail Fast:** If the FIRST `confluence_search` page-fetch returns SAML/SSO redirect, skip all remaining Confluence deep-fetch attempts.

**Confluence MCP Tool:** Only one tool: `confluence_search`. It handles:
- CQL search: `confluence_search(cql="<CQL>", limit=N)`
- Page fetch by ID: `confluence_search(page_ids=["<pageId>"])`
- Page fetch by URL: `confluence_search(urls=["<URL>"])`
- Children: `confluence_search(page_ids=["<pageId>"], expand="children")`

### Candidates with Confluence URLs

Batch-fetch pages: `confluence_search(page_ids=["<id1>", "<id2>", "<id3>"])`

Extract: API name/version, endpoint paths, request parameters, response JSON structure, available query parameters, TDL table references, fallback transaction names, source systems, error responses, data constraints.

Check for child pages: `confluence_search(cql="ancestor=<pageId> AND type=page", limit=10)`

### Backstage Candidates without Confluence URLs

Use available metadata from the index (name, title, description, system, domain, tags, GitLab slug). These candidates have less API-level detail and may require manual investigation.
