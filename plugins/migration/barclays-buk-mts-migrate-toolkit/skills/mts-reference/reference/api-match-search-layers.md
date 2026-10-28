# API Match Search Layers

Complete 13-layer search strategy (Layers 1-6 + 7a-7e + Layer 8 Deep Investigation), deduplication, ranking, deep-fetch (GitLab + Confluence), quality-check, and E2E mapping instructions for the `/api-replacement-match` command (Step 2). This is the **single source of truth** for all search logic — the command file delegates here.

## Prerequisites (set by the command file before entering Step 2)

- `BACKSTAGE_SOURCE` — `LIVE` or `STATIC` (from Step 1.95 Backstage clone)
- `BACKSTAGE_REPO_PATH` — path to cloned repo (when LIVE)
- `CONFLUENCE_AVAILABLE` — `true` or `false` (from Step 1.9 probe)
- `GITLAB_AVAILABLE` — `true` or `false` (from Step 1.9b probe)
- `IS_WRITE` — `true` if method name contains create/update/modify/amend/delete/remove/maintain/set/put
- MTS service data: TDL tables, transaction names, gateway class + method, transport type, source systems, DataGroups

### Confluence Availability Branching

All Confluence-dependent layers (2-6) respect this flag:
- If `CONFLUENCE_AVAILABLE = false`: Skip all Confluence CQL searches. Use seed catalogue page IDs for direct fetches only. Report: `"Confluence MCP tools unavailable — using seed catalogue + Backstage index only."`
- If `CONFLUENCE_AVAILABLE = true`: Execute all Confluence layers normally.

### GitLab Availability Branching

All GitLab-dependent steps (Deep Fetch Steps A0, A, A2, A2b) respect this flag:
- If `GITLAB_AVAILABLE = false`: Skip ALL GitLab searches (spec repo discovery, OpenAPI blob search, gateway equivalence search). For each candidate that would have been GitLab-searched:
  - Set `doc_completeness = "metadata-only"` (unless Confluence provided full data)
  - Set `unverified = true` (unless Confluence LLD provided verified response field schema)
  - Report: `"GitLab MCP not authenticated — Deep Fetch skipped. Field mappings unverified."`
- If `GITLAB_AVAILABLE = true`: Execute all GitLab Deep Fetch steps normally.

**Both unavailable:** If BOTH `CONFLUENCE_AVAILABLE = false` AND `GITLAB_AVAILABLE = false`, candidates are scored from Backstage metadata and seed catalogue data ONLY. All candidates get `unverified = true` and `doc_completeness = "metadata-only"`. The 25% Dimension 3 discount applies to all.

### Search Priority Rule

**Always search for higher-level APIs first, then fall back to system APIs.**

The ODS API catalogue (see `ods_api_catalogue.md` — "API Hierarchy & Search Priority") defines a 5-tier API taxonomy. When collecting candidates:

1. **First**, look for **Process APIs (pAPI)** or **Domain APIs (dAPI)** — preferred replacements.
2. **Then**, look for **Internal APIs (iAPI)** or **External APIs (xAPI)**.
3. **Last resort**: look for **System APIs (sAPI)** — read-only enquiry endpoints.

**Read vs Write distinction:**
- ODS sAPIs are **primarily read/enquiry** operations. If the MTS service performs a **write** (create, update, delete), the replacement is likely a pAPI or dAPI, NOT an ODS sAPI.
- If `IS_WRITE = true` — flag it as a write operation and **search for pAPI/dAPI candidates first**. Only fall back to sAPIs if no write-capable API exists.
- **Hard rule:** ODS APIs MUST always be ranked above ZOS/system APIs for reads. For writes, z/OS sAPIs may be preferred (see Layer 4).

---

## Layer 1 — Live Backstage Catalogue (cloned repo, with static fallback)

**Primary source:** Cloned `software-catalog-templates` repo at `<BACKSTAGE_REPO_PATH>/components/` (set by `backstage_clone.py` in Step 1.95).
**Fallback source:** Static `backstage_catalogue_index.md` (used when `BACKSTAGE_SOURCE = STATIC`).

### Layer 1A — Live repo search (when BACKSTAGE_SOURCE = LIVE)

Grep YAML files in `<BACKSTAGE_REPO_PATH>/components/` for domain nouns and system names.

**You MUST run at least 3 searches.** Run them in a single parallel tool-call message.

Extract the domain noun from the gateway class name (e.g., `CustomerGateway` → "Customer").

**Search terms to try (in order):**

1. Domain noun from the method name (e.g., `customer`, `account`, `address`, `party`, `membership`)
2. Backend system / source system name from the MTS service doc (e.g., `CUST`, `WMID`, `BASPC`)
3. Domain keyword from the TDL table names (e.g., `core`, `details`, `party`)
4. Method semantic (e.g., `retrieve` → `get`, `fetch`, `read`, `query`)
5. Any known system abbreviation found in Section 1 of the service doc

**Grep pattern examples (live repo):**
```
Grep <BACKSTAGE_REPO_PATH>/components/ for: customer.*details  (glob: *.yaml)
Grep <BACKSTAGE_REPO_PATH>/components/ for: party.*core  (glob: *.yaml)
Grep <BACKSTAGE_REPO_PATH>/components/ for: srv-cust  (glob: *.yaml)
Grep <BACKSTAGE_REPO_PATH>/components/ for: personalcustomer  (glob: *.yaml)
```

**Extract per candidate from YAML:**
- `metadata.name` — API component name (e.g., `srv-custdtlsmgmt-api`)
- `kind` — should be `Component`
- `spec.system` — owning system
- `spec.domain` — domain classification
- `metadata.description` — description (if present)
- `metadata.tags[]` — tags (e.g., `java`, `smesh`)
- `metadata.links[]` — any linked Confluence URL (look for `icon: confluence`)
- `metadata.annotations["gitlab.com/project-slug"]` — GitLab project path

**For matched YAML files:** Read the full YAML content to extract all fields above. Run up to 5 file reads in parallel.

### Layer 1B — Static index fallback (when BACKSTAGE_SOURCE = STATIC)

Grep `backstage_catalogue_index.md` for the same search terms as Layer 1A.

**Grep pattern examples (static index):**
```
Grep backstage_catalogue_index.md for: customer.*details
Grep backstage_catalogue_index.md for: party.*core
Grep backstage_catalogue_index.md for: srv-cust
Grep backstage_catalogue_index.md for: personalcustomer
```

**Extract per candidate:**
- API component name (e.g., `srv-custdtlsmgmt-api`)
- Kind (`API`, `Component`)
- Owner / system
- Description (if present)
- Any linked Backstage or Confluence URL

**Layer 1 output:** List of Backstage API names with descriptions. No deep fetch at this stage.

---

## Layer 2 — pcbcooiit Confluence Space (ODS sAPI LLD pages)

**Parent page:** `507590733` (21+ child pages — ODS sAPI Low Level Design documents)

**Seed catalogue:** `ods_api_catalogue.md` — check first for known direct mappings and page IDs before running CQL.

**CQL search pattern:**
```
space="pcbcooiit" AND ancestor=507590733 AND text~"<search terms>"
```

**Search terms to try:**
1. Domain noun (e.g., `"customer details"`, `"party core"`)
2. TDL table names from the MTS service doc (e.g., `"CUSTREF"`, `"WMID"`)
3. Source system abbreviation (e.g., `"BASPC"`, `"CUST"`)
4. Method semantic combined with domain (e.g., `"retrieve customer"`)

**Run up to 3 distinct CQL queries** with different search terms. Collect all unique page results.

**Extract per page result:**
- Page title
- Page ID
- Summary / excerpt (from CQL result)
- Any sAPI name mentioned in the title or excerpt

**Layer 2 output:** List of pcbcooiit page titles and IDs. Deep fetch deferred until after deduplication.

---

## Layer 3 — PCBICCAPIS Confluence Space (TC 31 API Catalog — process APIs)

**Parent page:** `1228557435` (TC 31 API Catalog — domain/process APIs, pAPIs, dAPIs, iAPIs)

**CQL search pattern:**
```
space="PCBICCAPIS" AND ancestor=1228557435 AND text~"<search terms>"
```

**Search terms to try:**
1. Domain noun from the method name (e.g., `"customer details"`, `"account balance"`)
2. TDL table names from the MTS service doc
3. Backend system abbreviation
4. Method semantic combined with domain (e.g., `"retrieve customer"`)

**Run up to 3 distinct CQL queries** with different search terms. Collect all unique page results.

**Extract per page result:**
- Page title
- Page ID
- Summary / excerpt (from CQL result)
- Any API name mentioned in the title or excerpt
- API type if identifiable (pAPI, dAPI, iAPI, sAPI)

**Layer 3 output:** List of PCBICCAPIS page titles and IDs. Deep fetch deferred until after deduplication.

**Note:** Many Backstage components (Layer 1) already link to PCBICCAPIS pages via `metadata.links[]`. When deduplicating, merge candidates that refer to the same API across Layer 1 and Layer 3.

---

## Layer 4 — COOCUSTCRM Confluence Space (z/OS Connect sAPI pages)

**Parent page:** `1798520644` (28+ child pages — z/OS Connect sAPI specification pages)

**CQL search pattern:**
```
space="COOCUSTCRM" AND ancestor=1798520644 AND text~"<search terms>"
```

**Search terms to try:**
1. Same domain nouns as Layer 2
2. `"z/OS"` combined with domain noun
3. TDL table names from the MTS service doc
4. CICS transaction code or messaging name from the MTS service doc (if mainframe-mq transport)

**Known write candidates** (always include for WRITE operations — check these pages directly):

| sAPI Name | Page ID | Scope |
|-----------|---------|-------|
| `cust-coreCustomerDetails-sAPI-v14.0` | `3852609006` | Customer detail read/write |
| `cust-membershipMaintenance-sAPI-v1.0` | `2164463698` | Membership maintenance |
| `cust-customerPreferences-sAPI-v1.1` | `1850479771` | Preferences maintenance |

### Write-Operation Rules (MANDATORY)

**COOCUSTCRM MUST ALWAYS be searched for these cases, regardless of Layer 1-3 candidate count:**
- `IS_WRITE = true` (method contains create/update/modify/delete/maintain/set/put)
- The MTS service transport is `mainframe-mq` and no candidate scored >70% from GitLab
- The Known write candidates table above has a matching entry for this service

> **Why:** ODS sAPIs (from pcbcooiit/Backstage) and process APIs (from PCBICCAPIS) are
> primarily read/enquiry. Write operations can ONLY be replaced by z/OS Connect sAPIs in
> COOCUSTCRM. Skipping COOCUSTCRM for writes guarantees a 0% score — which is wrong if
> a z/OS sAPI exists.
> Example: `cust-membershipMaintenance-sAPI-v1.0` (page 2164463698) is the write replacement
> for `MembershipMaintenanceService.updateMembership`.

If `IS_WRITE = true` and the Known write candidates table has a matching entry, fetch that page directly in addition to CQL search results.

**Layer 4 output:** List of COOCUSTCRM page titles and IDs. Deep fetch deferred until after deduplication.

---

## Layer 5 — GRPQRTUKBA Confluence Space (UKBA z/OS sAPIs)

**Parent page:** `1087522407` (UKBA API Design Reference — all UKBA mainframe z/OS Connect sAPIs)

**When to search:** When the MTS service accesses UKBA tables (TDLBAHO, TDLMAHO, etc.), uses `UkbaGateway`, or has IMS transaction codes starting with `TGJ` or `TGT`.

**CQL search pattern:**
```
space="GRPQRTUKBA" AND ancestor=1087522407 AND text~"<search terms>"
```

**Search terms to try:**
1. UKBA TDL table names from the MTS service doc
2. IMS transaction code from the service doc (e.g., `TGJ3MA`, `TGJ3FH`)
3. Domain noun (e.g., `"account enquiry"`, `"generic enquiry"`, `"bonds"`, `"financial histories"`)

**Known UKBA z/OS sAPIs:**

| sAPI Name | IMS Transaction | Method + Path | Scope |
|-----------|----------------|---------------|-------|
| `ukba-bondsEnquiries-sAPI-v1.0` | TGT1S400 | POST /details/queries | Bonds enquiry |
| `ukba-bondsUpdate-sAPI-v1.0` | TGT1S200 | PATCH /addModify | Bonds update (WRITE) |
| `ukba-entriesSOI-sAPI-v1.0` | TGTU58S0 | POST /forcedEntrySets | Entries SOI (WRITE) |
| `ukba-financialHistories-sAPI-v2.0` | TGJ3FHS0 | GET /details | Financial histories |
| `ukba-genericEnquiry-sAPI-v2.0` | TGJ9OGS0 | GET /queries | Generic enquiry |
| `ukba-genericUpdate-sAPI-v1.0` | TGJ8G100 | PATCH /parameters | Generic update (WRITE) |
| `ukba-multipleAccountEnquiries-sAPI-v1.1` | TGJ1MLS0 | POST /accounts/queries | Multiple account enquiry |
| `ukba-referReasonCode-sAPI-v1.0` | KGTRRMS0/KGTRMUS0 | POST+PUT+PATCH | Refer reason codes (READ+WRITE) |

**Layer 5 output:** List of GRPQRTUKBA page titles and IDs.

---

## Layer 6 — BCDUKCAPI Confluence Space (Cards & Lending API Catalogue)

**Parent page:** `1276948367` (API Catalogue — TC04 Cards domain-aligned, process, and Lending APIs)

**When to search:** When the MTS service uses FraudDesktop SOAP stubs (BEM), CAMS card enquiries, Cards StubConnectors, or Lending services.

**CQL search pattern:**
```
space="BCDUKCAPI" AND ancestor=1276948367 AND text~"<search terms>"
```

**Search terms to try:**
1. Cards domain noun (e.g., `"account enquiry"`, `"device enquiry"`, `"billing"`, `"reward"`)
2. SOAP operation name from the MTS service doc (e.g., `"retrieveBalanceConsolidations"`, `"retrieveCreditCardAcctList"`)
3. Lending domain noun (e.g., `"loan"`, `"disbursement"`, `"pre-authorization"`)
4. Service mesh name pattern (e.g., `"cc-domain-qry"`, `"cc-cmd"`)

**Three tabs on the catalogue page:**

| Tab | Count | Type | Examples |
|-----|:-----:|------|---------|
| Cards (Domain Aligned) | 33 | Domain APIs | Account Enquiry, Customer Enquiry, Device Enquiry, Billing, Rewards |
| Cards (Process) | 26 | Process APIs | Eligibility, Identity Mapping, Token APIs, VISA/Mastercard provisioning |
| Lending | 20+ | Process + SOAP | Loan Calculator, Loan Disbursement, Pre-Authorization, Diary Notes |

**Layer 6 output:** List of BCDUKCAPI page titles and IDs.

---

## Layer 7a — EST Confluence Space (Open Banking APIs)

**Parent page:** `559035965` (Open Banking APIs)

**When to search:** When the MTS service accesses account balance, transaction history, payment initiation, consent management, or account information services. Also search when the service doc mentions PSD2, Open Banking, or AISP/PISP patterns.

**CQL search pattern:**
```
space="EST" AND ancestor=559035965 AND text~"<search terms>"
```

**Search terms to try:**
1. Domain noun (e.g., `"account balance"`, `"payment"`, `"transactions"`)
2. Open Banking patterns (e.g., `"AISP"`, `"PISP"`, `"consent"`)
3. TDL table overlap (same as other layers)
4. PSD2 keywords (e.g., `"PSD2"`, `"open banking"`, `"account information"`)

**Run up to 2 distinct CQL queries.** Collect all unique page results.

**Layer 7a output:** List of EST page titles and IDs. Deep fetch deferred until after deduplication.

---

## Layer 7b — DCMDEV Confluence Space (DCM APIs)

**Parent page:** `737076546` (DCM Application Programming Interfaces)

**When to search:** When the MTS service relates to document management, correspondence generation, statement retrieval, or CMOD document access. **ALWAYS search for services classified as `cmod-odwek` transport.**

**CQL search pattern:**
```
space="DCMDEV" AND ancestor=737076546 AND text~"<search terms>"
```

**Search terms to try:**
1. Document type (e.g., `"statement"`, `"correspondence"`, `"letter"`)
2. CMOD references (e.g., `"CMOD"`, `"ODWEK"`, `"document retrieval"`)
3. Content management patterns (e.g., `"document"`, `"content"`, `"archive"`)

**Run up to 2 distinct CQL queries.** Collect all unique page results.

**Layer 7b output:** List of DCMDEV page titles and IDs. Deep fetch deferred until after deduplication.

---

## Layer 7c — APITECHDES Confluence Space (API Index + Digital Channels)

**Parent page (API Index):** `1311225934` (API Index — master cross-reference across ALL domains)
**Parent page (Digital Channels):** `1311226039` (Digital Channels API Design - Published)

**When to search:** **ALWAYS** for the API Index — it is a master catalogue of all APIs across all domains and serves as a cross-reference. Digital Channels sub-page: search when the service is customer-facing or accessed via digital banking channels (mobile, online, open banking).

**CQL search patterns:**
```
space="APITECHDES" AND ancestor=1311225934 AND text~"<search terms>"
space="APITECHDES" AND ancestor=1311226039 AND text~"<search terms>"
```

**Search terms to try:**
1. Domain noun from the MTS service (e.g., `"customer"`, `"account"`, `"payment"`)
2. Service name or gateway name (e.g., `"CustomerGateway"`, `"ProductGateway"`)
3. API type keywords (e.g., `"process API"`, `"domain API"`, `"system API"`)
4. Known API names from Layers 1-6 results (cross-reference lookup)

**Run up to 3 distinct CQL queries** (2 for API Index, 1 for Digital Channels if applicable). Collect all unique page results.

**Deduplication note:** The API Index is a catalogue of catalogues. Results here often point to APIs already found in Layers 2-6. Apply standard deduplication — keep the existing Layer 2-6 entry, enrich with API Index metadata (e.g., API tier classification, lifecycle status) if new info found.

**Layer 7c output:** List of APITECHDES page titles and IDs. Deep fetch deferred until after deduplication.

---

## Layer 7d — EMMAPIS Confluence Space (EMM / Customer Insights APIs)

**Parent page:** `2214221355` (API Design - Published)
**Known sub-page:** `2214221813` (Customer Insights Process API - v1)

**When to search:** When the MTS service relates to customer insights, marketing eligibility, next-best-action, product recommendations, or customer segmentation.

**CQL search pattern:**
```
space="EMMAPIS" AND ancestor=2214221355 AND text~"<search terms>"
```

**Search terms to try:**
1. Customer insight keywords (e.g., `"eligibility"`, `"insight"`, `"recommendation"`)
2. Marketing patterns (e.g., `"next best action"`, `"campaign"`, `"offer"`)
3. Segmentation (e.g., `"segment"`, `"propensity"`, `"classification"`)

**Run up to 2 distinct CQL queries.** Collect all unique page results.

**Layer 7d output:** List of EMMAPIS page titles and IDs. Deep fetch deferred until after deduplication.

---

## Layer 7e — EPZOSCON Confluence Space (Enterprise Platforms z/OS Connect)

**Parent page:** `954298640` (API Catalogue — Enterprise Platforms z/OS Connect)

**Sub-pages (domains covered):**
- Customer System (may overlap COOCUSTCRM)
- Payments & Stationary
- UK Branch Accounting
- UKBA sAPI Catalogue (live + backlog — complements GRPQRTUKBA)
- UK Debit Cards

**When to search:** When the MTS service involves payments, branch accounting, debit cards, or any mainframe-mq service that has no match from COOCUSTCRM (Layer 4) or GRPQRTUKBA (Layer 5). Also search when transport is `mainframe-mq` and domain is outside Customer CRM.

**CQL search pattern:**
```
space="EPZOSCON" AND ancestor=954298640 AND text~"<search terms>"
```

**Search terms to try:**
1. Domain noun (e.g., `"payment"`, `"branch"`, `"debit card"`, `"stationary"`)
2. Transaction/program codes from the MTS service doc
3. UKBA-specific terms (e.g., `"sAPI"`, `"z/OS Connect"`)
4. Account operation keywords (e.g., `"transfer"`, `"standing order"`, `"direct debit"`)

**Run up to 2 distinct CQL queries.** Collect all unique page results.

**Layer 7e output:** List of EPZOSCON page titles and IDs. Deep fetch deferred until after deduplication.

---

## Deduplication and Ranking

After collecting candidates from ALL layers (1–6, 7a–7e):

### Deduplication rules

1. If the same API name appears in both Backstage (Layer 1) and a Confluence page (Layers 2–6, 7a–7e), merge into one candidate (keep all source references).
2. If a Backstage component links to a PCBICCAPIS page that also appears in Layer 3, merge (keep both references).
3. If two Confluence pages describe the same sAPI version (e.g., `v13.0` and `v14.0`), keep the **higher version** only.
4. If a page title is a sub-page of another (e.g., appendix), prefer the parent LLD page.
5. If the API Index (Layer 7c) returns an API already found in Layers 2-6, keep the existing entry — enrich with any additional metadata from the API Index (tier classification, lifecycle status).
6. If EPZOSCON (Layer 7e) returns a UKBA sAPI also found in GRPQRTUKBA (Layer 5), merge — prefer the GRPQRTUKBA entry (more detailed).

### Ranking criteria (apply in order)

1. **TDL table overlap** — does the candidate API mention the same TDL tables as the MTS service? (highest weight)
2. **Source system match** — does the candidate reference the same backend system (e.g., BASPC, WMID, CUST)?
3. **Domain noun match** — does the API name / page title contain the same domain noun as the MTS method?
4. **Operation semantic match** — does the API support a compatible HTTP method (GET for read, POST/PUT for write)?
5. **Layer priority** — Layer 1 (Backstage) > Layer 2 (pcbcooiit) > Layer 3 (PCBICCAPIS) > Layer 4 (COOCUSTCRM) > Layer 5 (GRPQRTUKBA) > Layer 6 (BCDUKCAPI) > Layer 7a-7e as tiebreaker for reads; reversed for writes (COOCUSTCRM, GRPQRTUKBA, and EPZOSCON preferred for writes).

**Keep top 5 candidates after ranking.**

---

## Deep Fetch: Top 3 Candidates

**Priority order: GitLab FIRST, Confluence SECOND.**

### GitLab Availability Gate

**If `GITLAB_AVAILABLE = false`:** Skip Steps A0, A, and A2/A2b entirely. For each candidate:
- Set `doc_completeness = "metadata-only"` (unless Confluence data upgrades it)
- Set `unverified = true` (no GitLab-verified field data)
- Proceed directly to Step B (Confluence Page Fetch) — which becomes the PRIMARY source

**If `GITLAB_AVAILABLE = true`:** Execute Steps A0, A, A2, A2b as normal below.

---

### Step A0 — Spec Repo Discovery (MANDATORY for candidates with GitLab slugs)

BUK service mesh APIs typically separate application code and API specifications into **sibling repos** under the same GitLab group. The Backstage YAML only gives the `apps/` (or `app/`) slug. The OpenAPI spec often lives in a dedicated spec repo.

**For each of the top 3 candidates with a GitLab slug**, derive and check for a spec repo:

**1. Derive spec repo paths** from the Backstage slug `barclays/<group>/<subfolder>/<api-name>`:

| Pattern | Derivation | Example |
|---------|-----------|---------|
| Pattern 1 (most common) | Replace `apps/` or `app/` with `spec/`, append `-spec` | `barclays/cct-collg-servicing-apis/spec/rc-colleague-eligibility-api-spec` |
| Pattern 2 | Replace `apps/` or `app/` with `spec/`, no suffix | `barclays/cct-collg-servicing-apis/spec/rc-colleague-eligibility-api` |
| Pattern 3 (fallback) | `mcp__Gitlab__search_repositories(search="<api-name>-spec")` | Catches non-standard naming |

Try Pattern 1 first, then Pattern 2. Only use Pattern 3 if both fail.

**2. Check if spec repo exists** — call `mcp__Gitlab__get_repository_tree(project_id=<derived-path>)`:
- If the call succeeds → spec repo exists. Look for `openapi.yaml`, `swagger.yaml`, or any `.yaml` file under `oas/` or `spec/` directories.
- If the call fails (404) → try the next pattern.
- Try the repo's default branch first. If the default branch is `master` but the tree is empty/skeletal, also check for `release/*` branches (some repos use `release/X.Y` as the active branch).

**3. Read the OpenAPI YAML** — `mcp__Gitlab__get_file_contents(project_id=<spec-repo>, file_path=<found-yaml>)`.

**4. Resolve `$ref` components** — OpenAPI specs typically use `$ref` to split schemas across files. For each `$ref` found in the main YAML, fetch the referenced file:

| $ref Pattern | What It Contains | Action |
|-------------|-----------------|--------|
| `./components/parameters.yaml` | Request parameters (query, header, path) | Read → extract parameter names, types, required flags |
| `./components/<response-model>.yaml` | Response schema (field names, types, nesting) | Read → extract full response structure |
| `./examples/<example>.json` | Example request/response payloads | Read → use for Section 6 of match report |
| `./common-libraries/components/*.yaml` | Shared headers, error responses | Read only if needed for request parameter extraction |

**5. Extract and record** for each candidate where spec repo was found:
- Set `doc_completeness = "full-schema"` (highest quality)
- Set `spec_source = "spec-repo"` with the repo path
- Record: endpoint paths (HTTP method + URL), request parameters (name, type, in, required), response schema (field names, types, nesting as dot-notation), example responses

> **Why spec repo first:** Dedicated spec repos are the authoritative source for API contracts.
> They are maintained by API teams and contain the exact OpenAPI definition used for code generation.
> A spec repo OpenAPI YAML supersedes blob search results and Confluence pages.

### Step A — GitLab OpenAPI/Swagger Blob Search (SKIP if Step A0 found full-schema)

**If Step A0 already found `doc_completeness = "full-schema"` for a candidate → SKIP Step A for that candidate.** The spec repo is authoritative; blob search would be redundant.

**Otherwise**, for each remaining candidate that has a GitLab slug but Step A0 found no spec repo, search for API specs in the app repo:
```
mcp__GitLab__search(scope="blobs", search="openapi", project_id="<gitlab-slug>")
mcp__GitLab__search(scope="blobs", search="swagger", project_id="<gitlab-slug>")
```
If an OpenAPI/Swagger spec is found, this is the **highest quality** source — extract endpoint paths, request parameters, and response schemas from it. Mark the candidate as `doc_completeness = "full-schema"`.

> **Why GitLab first:** OpenAPI specs in source repos are authoritative and complete.
> Confluence pages may be outdated, incomplete, or delivery documents rather than API specs.
> A GitLab OpenAPI spec supersedes any Confluence data for the same candidate.

### Step A2 — Gateway Equivalence Search (MANDATORY for candidates with GitLab slugs)

For each top candidate with a GitLab slug, search for the MTS service's **gateway class name** and **transaction name** in the candidate's source code:
```
mcp__GitLab__search(scope="blobs", search="<MTS_gateway_class_name>", project_id="<gitlab-slug>")
mcp__GitLab__search(scope="blobs", search="<MTS_transaction_name>", project_id="<gitlab-slug>")
```

Where:
- `<MTS_gateway_class_name>` = the gateway from the service doc (e.g., `CustomerGateway`, `MembershipGateway`, `ProductGateway`)
- `<MTS_transaction_name>` = the messaging/transaction name (e.g., `CUS_ALL_RETRIEVE`, `CCP_RETRIEVE_MEMBER`)

If the candidate's source code contains EITHER the gateway class name OR the transaction name:
- Set `gateway_equivalent = true` for that candidate
- Record `gateway_evidence` = what was found (e.g., "CustomerGateway found in CustomerDataGroup.java")

### Step A2b — Oracle Table Search (MANDATORY when transport = oracle-db-direct)

If the MTS service doc identifies the transport as `oracle-db-direct` and names a specific Oracle table (e.g., `ti_tukprod`, `tukprgl`, `tukprsv`), search each candidate's GitLab repo:
```
mcp__GitLab__search(scope="blobs", search="<oracle_table_name>", project_id="<gitlab-slug>")
```
If the candidate's source code queries the same Oracle table, set `db_table_equivalent = true` and record the evidence. This is the oracle-db-direct equivalent of gateway equivalence — the API that reads from the same table is the architecturally correct replacement.

> **Why this matters:** The ODS API that wraps the same EGS gateway as the MTS service
> is architecturally the correct replacement. A different API might provide the same data
> but through a different abstraction — that's a less direct migration path.

### Step B — Confluence Page Fetch (confidence-gated)

After Steps A + A2, evaluate each candidate's GitLab evidence level:

- **>90% confidence from GitLab** (OpenAPI spec found WITH full response schema, OR `gateway_equivalent=true` with DataGroup enum match):
  → SKIP Confluence for this candidate. GitLab data is sufficient.

- **<70% confidence from GitLab** (no OpenAPI spec, no gateway match, OR only partial gateway match):
  → **MUST** fetch Confluence page for this candidate. GitLab data is insufficient.

- **70-90% confidence** (OpenAPI found but no response schema, OR gateway match but no DataGroup enum):
  → Confluence fetch is RECOMMENDED but not mandatory.

- **GitLab skipped** (when `GITLAB_AVAILABLE = false`): ALL candidates are treated as <70% confidence — Confluence fetch is MANDATORY for every candidate that has a Confluence URL.

- **Both GitLab AND Confluence unavailable** (when `GITLAB_AVAILABLE = false` AND `CONFLUENCE_AVAILABLE = false`): Candidate remains at `doc_completeness = "metadata-only"` and `unverified = true`. Score using Backstage metadata and seed catalogue data only. The 25% Dimension 3 discount applies.

> **CRITICAL:** "GitLab was searched but found nothing" means <70% — the candidate
> MUST be deep-fetched from Confluence. Do NOT treat "searched but empty" as "done."

**How to fetch:** Use the Confluence URL from the Backstage YAML (`metadata.links[]` where `icon: confluence`).
```
confluence_search(search_pages=["<confluence-url-from-yaml>"], extract_content=true)
```

**Extract from each page:**
- Full sAPI name and version
- Base path and HTTP endpoints (list all)
- Request parameters (path params, query params, request body fields)
- Response body fields (field name, type, description)
- TDL table references (any mention of TDL, WMID, CUSTREF, etc.)
- Source systems referenced
- Any known limitations or read-only / write-only notes
- Page URL (for citation in the match report)

**If the page is too large (truncated by MCP):** Extract the endpoint table and response field table only. Note truncation in the candidate record.

For candidates with neither GitLab specs nor Confluence URLs, use available Backstage metadata only (name, title, description, system, domain, tags, GitLab slug).

---

## Deep Fetch Quality Check

After fetching data for the top 3 candidates, evaluate content quality:

For each candidate, check whether the collected data (GitLab + Confluence) contains:
- Endpoint paths (HTTP method + URL path pattern) → `has_endpoints = true/false`
- Response field names or JSON schema → `has_response_schema = true/false`
- Request parameters (query params, path params) → `has_request_params = true/false`

If a Confluence page is a **delivery document** (contains "PWR", "release", "delivery", "sprint" but NOT "endpoint", "GET", "POST", "response", "schema"), mark it as `doc_type = "delivery"` rather than `doc_type = "api-spec"`.

**Standard quality checks:**
1. **Endpoint present** — at least one HTTP endpoint path was extracted. If absent, note "no endpoint found" and reduce ranking.
2. **Response fields present** — at least 3 response fields were extracted. If fewer, note "sparse documentation" and flag for manual review.
3. **TDL or source system overlap confirmed** — at least one TDL table or source system from the MTS service doc appears in the candidate data. If none, note "no TDL/source overlap" and reduce confidence.
4. **Version is current** — if the page title includes a version number older than a known newer version, add a note "older version — newer version may exist".

**If no candidate has `has_endpoints = true` after Deep Fetch → trigger Additional Investigation.**

---

## E2E Mapping Page Extraction

After deep-fetching the **winning candidate** (top-ranked after scoring), search its Confluence page for linked End-to-End (E2E) field mapping pages. These pages contain authoritative ODS field path → TDL table → TDL column mappings that significantly improve Section 4 accuracy.

### How to find the E2E mapping page

1. **Check the candidate's Confluence page** for links to pages with titles containing "E2E", "End to End", "Field Mapping", or "Response Mapping".
2. **Check the seed catalogue** (`ods_api_catalogue.md`) for any `e2e_page_id` associated with the candidate sAPI.
3. **Search pcbcooiit space** if not found in steps 1-2:
   ```
   space="pcbcooiit" AND text~"<sAPI name> E2E" AND type=page
   ```

### What to extract from the E2E mapping page

Extract the field mapping table with these columns (where available):
- **ODS Response Field Path** — the full dot-notation JSON path (e.g., `ukbaProductHoldingDataList[].classificationCode.code`)
- **ODS Type** — the data type (`String`, `Object`, `Integer`, etc.)
- **Source Table** — the TDL/backend table (e.g., `TDLBAHO`, `TUKPRCL`)
- **Source Column** — the TDL column name (e.g., `GncPdtCde`, `PdtHlgEndDte`)
- **Reference Data** — any reference data lookups or ClassKey references

### Output format

Pass the extracted E2E data to the match agent as:
```
CANDIDATE_E2E_PAGE_URL: <Confluence URL of the E2E mapping page>
CANDIDATE_E2E_MAPPINGS:
  - ods_field: <full dot-notation path>
    ods_type: <data type>
    source_table: <TDL table>
    source_column: <TDL column>
    reference_data: <any reference lookups>
```

The match agent uses this data for:
- **Higher-confidence field matching** — E2E mappings confirm which ODS field corresponds to which TDL table/column, replacing guesswork with documented links.
- **Accurate ODS Field paths** — real dot-notation paths for Section 4 instead of prose descriptions.
- **Accurate ODS Types** — real data types for Section 4 instead of vague descriptions.
- **Section 5.4 ODS API Reference** — the E2E page URL is included as a reference link.

---

## Additional Investigation (when documentation is STILL thin after Deep Fetch)

**Trigger condition:** Runs when ANY of these are true after Deep Fetch:
- No candidate has `doc_completeness = "full-schema"` after GitLab + Confluence fetch
- The top candidate has no endpoint paths and no response field schema
- The Deep Fetch Confluence page is a delivery document (PWR/release doc) not an API spec

**Run these searches IN PARALLEL in a single tool-call message:**

**A. GitLab broader search (if initial OpenAPI search found nothing):**
Try alternative search terms in the same repos:
```
mcp__GitLab__search(scope="blobs", search="paths:", project_id="<gitlab-slug>")
mcp__GitLab__search(scope="blobs", search="application/json", project_id="<gitlab-slug>")
```

**B. Broad Confluence search — transport-specific terms:**
Build search queries from the MTS service doc's transport type and backend:
- For `soap-stub` TCV services:
  - `confluence_search(query="<candidate-name>")` across ALL spaces
  - `confluence_search(query="<candidate-name> VPT test")` — VPT test results often contain actual endpoint URLs
  - `confluence_search(query="<candidate-name> SOM document")` in TCVBA space
- For `soap-stub` BEM services:
  - `confluence_search(query="<SOAP-operation-name> API")` across ALL spaces
- For all transports:
  - `confluence_search(query="<candidate-name> API specification swagger openapi")`

**C. Fetch newly discovered Confluence pages:**
If B found new Confluence pages not already fetched, fetch them to extract endpoint paths, query parameters, and any field/schema information.

**Evidence extraction from VPT/test pages:**
VPT and performance test pages often contain endpoint URLs in test configuration tables. Extract:
- Full endpoint URLs (e.g., `https://zuul-gateway.../partyfinancialservicesmgmt-api/1.02.13-1.11/JourneyDetails?...`)
- Parse endpoint paths and query parameters from the URLs
- Service names and API version numbers
- Transaction names and TPS volumes (confirms the API is live/production-grade)

---

## Layer 8: Deep Investigation

**Trigger:** Fewer than 3 viable candidates after Layers 1–6 and 7a–7e AND Additional Investigation, OR all top 3 candidates fail the quality check.

**Layer 8 actions (in order):**

1. **Expand to user-supplied spaces** — if the user passed `--spaces`, search those spaces with the same CQL patterns.
2. **Search all of pcbcooiit** (not just ancestor=507590733) — some sAPIs may live outside the standard parent:
   ```
   space="pcbcooiit" AND text~"<domain noun>" AND type=page
   ```
3. **Search all of COOCUSTCRM** (not just ancestor=1798520644):
   ```
   space="COOCUSTCRM" AND text~"<domain noun>" AND type=page
   ```
4. **Search all of PCBICCAPIS** (not just ancestor=1228557435):
   ```
   space="PCBICCAPIS" AND text~"<domain noun>" AND type=page
   ```
5. **Search all of EPZOSCON** (not just ancestor=954298640):
   ```
   space="EPZOSCON" AND text~"<domain noun>" AND type=page
   ```
6. **Try the `--url` candidate** — if the user passed `--url`, fetch that page directly and add it as a candidate regardless of score.
7. **Widen Backstage search** — try broader terms (e.g., remove domain noun, search by system only). If `BACKSTAGE_SOURCE = LIVE`, try Grepping the full repo (not just `components/`).

**Layer 8 stops when:** 3 viable candidates found, or all Layer 8 actions exhausted.

---

## Search Exhaustion Log (ALWAYS collect)

Throughout ALL layers (1–6, 7a–7e, 8), collect every search attempted and its result into a structured log. This log is ALWAYS collected and passed to the match agent — not just when candidates are few.

```
SEARCH EXHAUSTION LOG:
- Confluence probe: CONFLUENCE_AVAILABLE=<true/false>
- GitLab probe: GITLAB_AVAILABLE=<true/false>
- Layer 1 (Backstage — <LIVE|STATIC>): <N> candidates found — search terms tried: <list>
- Layer 2 (pcbcooiit): <N> candidates found — CQL queries tried: <list>
- Layer 3 (PCBICCAPIS): <N> candidates found — CQL queries tried: <list>
- Layer 4 (COOCUSTCRM): <N> candidates found — CQL queries tried: <list>
- Layer 5 (GRPQRTUKBA): <ran/skipped (reason)> — <N> candidates found
- Layer 6 (BCDUKCAPI): <ran/skipped (reason)> — <N> candidates found
- Layer 7a (EST): <ran/skipped (reason)> — <N> candidates found
- Layer 7b (DCMDEV): <ran/skipped (reason)> — <N> candidates found
- Layer 7c (APITECHDES): <ran/skipped (reason)> — <N> candidates found
- Layer 7d (EMMAPIS): <ran/skipped (reason)> — <N> candidates found
- Layer 7e (EPZOSCON): <ran/skipped (reason)> — <N> candidates found
- Layer 8 (Deep Investigation) triggered: <yes/no> — actions taken: <list>
- Deep Fetch: GitLab <ran/skipped (GITLAB_AVAILABLE=false)> — specs found: <N>
- Deep Fetch: Confluence <ran/skipped (CONFLUENCE_AVAILABLE=false)> — pages fetched: <N>
- Unverified candidates: <N> (fields not verified against spec repo or Confluence LLD)
- Total unique candidates: <N>
- Note: Match report will proceed with <N> candidate(s). Confidence may be lower than usual.
```

The match agent must include this log verbatim in the "Data Gaps & Risks" section of the output report.
