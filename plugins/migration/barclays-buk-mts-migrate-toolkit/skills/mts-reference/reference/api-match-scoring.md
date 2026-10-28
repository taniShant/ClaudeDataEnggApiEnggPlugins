# API Match Scoring Algorithm

Score each candidate across 5 dimensions. Compute each dimension score as a percentage (0-100), then compute the weighted overall confidence.

### Dimension 1: TDL Table Overlap (Weight: 35%)

```
score = |MTS_tables INTERSECT API_tables| / |MTS_tables| * 100
```

- Extract TDL table names from the MTS service data.
- Extract TDL table references from the ODS API page content (look for `tdl`, `TDLMAHO`, `TDLBAHO`, Mongo collection names that mirror TDL tables like `prodHolding.tdlbaho`).
- Also check if any ODS query parameter documentation mentions a TDL table — even if the table name doesn't appear verbatim, a query param that returns the same data group counts as a match.
- Compute intersection ratio.
- If MTS has 0 TDL tables (reference-data-only service), score this dimension as 0 and redistribute its weight equally across the other 4 dimensions.

#### Table Equivalence Rules (Deterministic)

When determining whether an MTS TDL table is "matched" in an ODS API, apply these rules **in order** — use the FIRST rule that applies:

| Rule | Condition | Result |
|---|---|---|
| 1. Exact name | ODS API references the identical TDL table name | **MATCHED** |
| 2. Query-param data-group equivalence | An ODS query parameter returns the same data group as the MTS table | **MATCHED** |
| 3. Table subsumption | The ODS API accesses a superset table documented as subsuming the MTS table | **MATCHED** |
| 4. Known equivalences | The table pair appears in the hardcoded equivalences list below | **MATCHED** |
| 5. No documented link | None of the above rules apply | **NOT MATCHED** |

**Hardcoded Known Table Equivalences:**

| MTS Table | ODS Table | Reason |
|---|---|---|
| TDLBARH | TDLCCAX | Both serve UKBA arrangements/holdings data; TDLCCAX is the ODS-era replacement |
| TDLBAHO | TDLBAHO | Identity |
| TDLMAHO | TDLMAHO | Identity |
| TDLCAHO | TDLCAHO | Identity |

### Dimension 2: Transaction Name Match (Weight: 25%)

- **100**: The ODS API explicitly references the MTS service's CICS code, its Messaging name, or a documented z/OS variant in the same program lineage chain.
- **50**: The API references a transaction from a DIFFERENT method of the same gateway class (different ProgramCode, same SystemCode).
- **0**: No transaction name overlap found.

### Dimension 3: Response Field Similarity (Weight: 20%)

**This dimension compares MTS response fields against the ODS API's documented response fields from Confluence — NOT against any code or converter mappings.**

#### Field Origin Classification

Before scoring, classify every MTS response field by its **origin**. Use the `fieldOriginClassification` data provided in your prompt (produced by the Step 1.5 agent). If no classification data is provided, treat all fields as `gateway-response`.

**Origin categories:**

| Category | In Scope? |
|---|---|
| `gateway-response` — Field populated directly from the gateway method's MTS response | YES |
| `derived-local` — Field derived locally from gateway response data | YES |
| `external-service` — Field from a separate external service call | NO |
| `controller-layer` — Field set by controller from HTTP request context | NO |
| `full-retrieval-only` — Field from a full-retrieval code path calling a DIFFERENT service | NO |
| `request-context-derived` — Field from authentication/session context | NO |
| `error-from-non-gateway-call` — Error from catch block around a non-gateway call | NO |

#### Scoped Scoring

```
scoped_denominator = count of fields where origin IN ('gateway-response', 'derived-local')
scoped_score = matched_fields_in_scope / scoped_denominator * 100
```

**Use `scoped_score` for the weighted overall calculation.**

#### External-Service-Dependent Derived Fields

A `derived-local` field whose derivation requires data from an `external-service` call
(not just gateway response data) MUST be reclassified as `external-service` for scoring
purposes. The ODS API cannot replace the external service dependency.

**Test:** If removing the external service call would make the field impossible to compute,
it is external-service-dependent. Classify as `es`, not `dl`.

**Example:** `holdingCounters[INSURANCES]` is computed locally by filtering product arrays
through `insuranceTypeService.isInsuranceProduct()`. The filter logic is local, but the
classification data comes from an external service. Origin = `es`, not `dl`.

#### Field Matching Rules

A field is considered matched if:
1. **Exact match**: identical field name (case-insensitive)
2. **Dot-notation match**: MTS `classificationCode.code` matches ODS `classificationCode.code`
3. **Suffix match**: MTS `accountNumber` matches ODS `account.accountNumber`
4. **Semantic match**: MTS `sortCode` matches ODS `branchSortCode` (common banking synonyms)
5. **Data-group match**: MTS field comes from TDL table X, ODS has a query parameter that returns data from TDL table X

#### Unverified Field Discount

When a candidate has `unverified = true` (set when `GITLAB_AVAILABLE = false` AND no Confluence LLD verified the response fields), the Dimension 3 scoped score is discounted before being used in the weighted overall calculation:

```
IF unverified = true AND gateway_equivalent = true:
    dim3_final = scoped_score * 0.90    (10% discount — gateway match provides partial confidence)
ELSE IF unverified = true:
    dim3_final = scoped_score * 0.75    (25% discount — field names inferred from seed catalogue only)
ELSE:
    dim3_final = scoped_score           (no discount — fields verified from spec repo or Confluence LLD)
```

**Reporting:** When `unverified = true`:
- Append `(unverified)` to the Dimension 3 line in the score breakdown table
- In Section 5 (Data Gaps & Risks), add note: `"Response fields matched against seed catalogue / Backstage metadata — not verified against OpenAPI spec or Confluence LLD. Re-run with GitLab authenticated for verified scoring."`

### Dimension 4: Request Parameter Alignment (Weight: 10%)

```
score = covered_params / total_MTS_request_fields * 100
```

#### Gateway Dispatch Parameter Exclusion

Some MTS request fields are **gateway-internal dispatch parameters** — they select which method overload or code path the gateway invokes but do NOT carry data-fetching semantics. These fields have no ODS equivalent because ODS APIs use HTTP method + path routing instead.

**Exclusion rule:** A request field is excluded from the Dim 4 denominator if it meets ALL of these criteria:
1. The field selects between method overloads or code paths within the gateway (e.g., `requestType` choosing between `doRetrieve` vs `doFullRetrieve`)
2. The field has a fixed set of enum/string values that map to different gateway behaviours
3. The field does NOT carry customer or account data used by the backend query

**Common excluded fields:** `requestType`, `operationType`, `actionCode` (when used purely for dispatch)

**Handling:** Excluded fields are still listed in Section 2 (Request Mapping) for completeness with Match = `**MISSING**` and Notes = `Gateway dispatch parameter — excluded from scoring`. They are NOT counted in the Dim 4 denominator.

### Dimension 5: Source System Match (Weight: 10%)

```
score = |MTS_sources INTERSECT API_sources| / |MTS_sources| * 100
```

### Overall Confidence

```
overall = (dim1_score * 0.35) + (dim2_score * 0.25) + (dim3_score * 0.20) + (dim4_score * 0.10) + (dim5_score * 0.10)
```

### Transport-Adaptive Weight Redistribution

| Transport | Dim 1 (35%) | Dim 2 (25%) | Dim 3 (20%) | Dim 4 (10%) | Dim 5 (10%) |
|-----------|-------------|-------------|-------------|-------------|-------------|
| `mainframe-mq` | TDL Overlap 35% | Txn Name 25% | Response 20% | Request 10% | Source 10% |
| `soap-stub` / `soap-eao` | N/A 0% | SOAP Op Match 25% | Response 40% | Request 15% | Source 20% |
| `oracle-db-direct` / `db2-reference` | DB Table Match 35% | N/A 0% | Response 30% | Request 15% | Source 20% |
| `cmod-odwek` | N/A 0% | N/A 0% | Response 35% | Request 20% | Source 45% |
| `scv` | N/A 0% | N/A 0% | Response 40% | Request 20% | Source 40% |
| `tcv-hybrid` | Per legacy path | Per legacy path | Per legacy path | Per legacy path | Per legacy path |

### Confidence Bands

| Range | Band | Interpretation |
|---|---|---|
| 80-100% | Strong match | Likely direct replacement |
| 60-79% | Partial match | Covers most data, some gaps |
| 40-59% | Weak match | Significant field/table gaps |
| 0-39% | Unlikely match | Different data domain |

### Candidate Ranking Priority (Strict)

When multiple candidates exist, rank by API tier FIRST, then by raw score within the same tier:

1. **pAPI/dAPI (Process/Domain APIs)** — Preferred. Handle orchestration, business logic,
   aggregation, and error mapping server-side. Always ranked above lower tiers.
2. **iAPI/xAPI (Internal/External APIs)** — Integration tier. Useful when no pAPI/dAPI
   exists for the domain. Ranked below pAPI/dAPI, above sAPI.
3. **sAPI (System APIs, e.g. ODS Retail enquiry)** — Low-level read-only data access.
   Last resort for read operations. Consuming a sAPI means the migration team must
   implement all business logic (classification, aggregation, error mapping) client-side.
4. **ZOS/System APIs** — Require writing a pAPI wrapper to consume. Always ranked last.

**Rationale:** Consuming a sAPI means the migration team must implement all business
logic (classification, aggregation, error mapping) client-side. A pAPI/dAPI handles
this orchestration already and is always preferred. A ZOS/system API requires building
an entirely new pAPI wrapper, adding even more migration effort.

**Elimination reasons by tier:**
- If a pAPI/dAPI candidate exists with score >= 40% (Weak match or better), sAPI candidates get:
  `Eliminated — system API (sAPI); higher-level pAPI/dAPI available`
- If any ODS API (tier 1-3) is the winner, ZOS candidates get:
  `Eliminated — z/OS system API; requires pAPI wrapper to consume; ODS API available`

### Gateway-Equivalence Boost (from GitLab Source Evidence)

If a candidate's GitLab source code contains the MTS service's gateway class name
OR transaction name (confirmed via GitLab blob search in Deep Fetch Step A2), that
candidate receives a **+15% scoring boost** (added to weighted total, capped at 100%).

This is NOT a hardcoded mapping — the evidence comes from searching the actual
source code of each candidate API via `mcp__GitLab__search`. For example, if
`sodscustenq`'s repo contains `CustomerGateway` and `CUS_ALL_RETRIEVE`, that's
proof it wraps the same EGS gateway as the MTS service.

**Rules:**
- Gateway name match (e.g., `CustomerGateway` found in source): +10%
- Transaction name match (e.g., `CUS_ALL_RETRIEVE` found in source): +5%
- Both found: +15% (cumulative)
- If two candidates both qualify, the one with BOTH gateway + transaction wins
  over one with only one match
- The boost is applied AFTER the 5-dimension weighted calculation

### DB-Table-Equivalence Boost (for oracle-db-direct transport)

If the MTS transport is `oracle-db-direct` and a candidate's GitLab source code
queries the same Oracle table (confirmed via Step A2b search), that candidate
receives a **+15% scoring boost** (same rules as Gateway-Equivalence Boost).

Example: MTS queries `ti_tukprod`. If `sodsproductsenq`'s source has
`"select PDT_CDE, PDT_FUL_NME, PDT_CLS_CDE from ti_tukprod"`, that's proof
it reads the same table → +15% boost.

### z/OS sAPI Scoring for WRITE Operations

For WRITE operations (method contains create/update/modify/delete/maintain):
- z/OS Connect sAPIs from COOCUSTCRM are **valid replacement candidates**
  and MUST NOT be ranked below ODS sAPIs
- The "ODS APIs MUST always be ranked above ZOS" rule does NOT apply to writes
  because ODS sAPIs are read-only and cannot perform writes
- A z/OS sAPI that supports the write operation is preferred over any read-only
  ODS sAPI, regardless of read-side field overlap scores

**Why this matters:** The ODS API that wraps the same EGS gateway is the
architecturally correct replacement. A different API may provide similar data
but through a different internal flow — that's a less direct migration path
with more integration risk.

### Scoring Documentation-Dark Candidates

**Tier A — Full schema**: Score normally using all dimension rules.
**Tier B — Endpoints confirmed, no schema**: Score with 50% confidence discount on Dim 3 and Dim 4. Use `Probable` / `Unknown` / `Gap` for field mapping instead of blanket "UNKNOWN".
**Tier C — Metadata only**: Dim 3 and Dim 4 score 0. Note manual investigation required.
