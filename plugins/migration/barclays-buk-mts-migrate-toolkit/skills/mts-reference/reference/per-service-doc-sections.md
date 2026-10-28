# Per-Service Doc: Section Rules & Backend Mapping Variants

This file contains detailed rules for Sections 5 and 6 of per-service documentation files. Referenced from `agents/mts-per-service-doc-agent.md`. The agent MUST read this file before generating Sections 5 and 6.

---

## Section 5: End-to-End Field Mapping Rules

### Field Enumeration Approach (MANDATORY — response-backward)

Section 5 MUST enumerate fields starting from the **response** (WireMock fixture or Response EDO), then trace BACKWARD to the mainframe source. Do NOT start from WMOD fields and trace forward — that approach leaves gaps.

**Correct approach:**
1. Start from `WIREMOCK_RESPONSE_FIELDS` (if provided in VERBATIM_CONTRACT) or `RESPONSE_BEAN_FIELDS`
2. For EACH field in the response, determine its source:
   - Field name in `GATEWAY_DTO_FIELDS`? → **In-Scope**, origin = `gateway`, trace to WMOD field
   - Field name NOT in `GATEWAY_DTO_FIELDS`? → **Out-of-Scope**, origin = `external-service`
3. Every response field gets a row — NO blanks in Response Bean or REST Response columns
4. Verified = `VERIFIED` if field is in `WIREMOCK_VERIFIED_FIELDS`, else `—`

**Why:** The WireMock fixture is the REST response contract. It shows exactly what the consumer receives. Starting from WMOD fields misses enrichment fields and leaves Response Bean/REST Response columns blank for fields that go through untraced secondary paths.

### Application Layer Verification (Pre-Section 5, MANDATORY)

Before writing Section 5, consume the `APPLICATION_LAYER_VERIFICATION` section from the discovery summary (if present):

1. **DISABLED fields** (wrapper flag = false): Move to Out-of-Scope table with origin `disabled-in-wrapper`. Note: `DataGroup disabled: <flag>=false in <WrapperClass>`.
2. **COMMENTED_OUT fields** (converter setter commented out): Add `(COMMENTED_OUT)` suffix to REST Response column. If no other population path, move to Out-of-Scope with origin `converter-disabled`.
3. **ALWAYS_NULL fields** (null in all test fixtures): Add `(ALWAYS_NULL in fixtures)` suffix to REST Response column.
4. **EBS_ONLY enrichment** (method in EBS JAR but not in application): Document in Out-of-Scope with note about non-invocation.

If `APPLICATION_LAYER_VERIFICATION` is absent, add warning note: "This field mapping was generated without application layer verification (Step 1.16)."

### Table Format

7-column table with transport-specific and class-specific headers:

| <Transport> Source | Gateway DTO (<DTOClass>) | Response Bean (<BeanClass>) | REST Response (Type) | Origin | Verified | Description |

- Use actual class names in headers (not placeholders)
- First column name varies by transport: mainframe-mq → `Mainframe Source`, soap-stub → `SOAP Source`, oracle-db-direct → `Oracle DB Source`, etc.

### Verified Column Values

- `VERIFIED` — confirmed populated with non-null value in test fixtures
- `ALWAYS_NULL` — exists in bean but always null/empty in all fixtures
- `COMMENTED_OUT` — converter/mapper setter is commented out
- `DISABLED` — DataGroup disabled in wrapper request
- `EBS_ONLY` — enrichment source exists in EBS JAR but not invoked by application
- `—` — no verification data available

### Origin Values (spelled out, no abbreviations)

- `gateway` — from WMOD response field via TDL table
- `gateway → derived` — derived/counted from gateway data
- `derived` — computed locally without direct gateway data
- `full-retrieval-only` — populated only when fullRetrieveRequired=true
- `external-service` — from a different service/API call
- `disabled-in-wrapper` — DataGroup disabled in wrapper request configuration
- `converter-disabled` — converter setter is commented out
- `controller` — set in controller layer
- `request-context` — echoed from request or session
- `error-field` — error message from a non-gateway call
- `unknown` — discovery data genuinely missing

### Enrichment-Layer Fields

Fields NOT from the gateway DTO go in the **Out-of-Scope Fields** sub-table with origin `external-service`. Test: if a field does NOT appear in GATEWAY_DTO_FIELDS from the VERBATIM_CONTRACT, it is NOT a gateway field.

**Common enrichment fields (NOT in Gateway DTOs, MUST be Out-of-Scope):**
- `productName`, `productShortName` — from `ProductGateway` enrichment
- `balance`, `lastNightBalance`, `balanceForFate`, `limits`, `anticipatoryLimits` — from `AccountGateway` enrichment
- `accountHoldersName`, `chosenName` — from `AccountGateway` enrichment
- `accountStatus` — from `AccountGateway` enrichment
- `referStream`, `badDoubtfulIndicator` — from `AccountGateway` enrichment
- `joint`, `jointHolderDetails` — may be from compound DataGroup (check GATEWAY_DTO_FIELDS)

### Verified Column

- If WIREMOCK_VERIFIED_FIELDS is provided in VERBATIM_CONTRACT: set `VERIFIED` for fields in the list, `—` for fields not in the list
- If WIREMOCK_VERIFIED_FIELDS is not provided: set `—` for all and add a Verification Note: "No WireMock fixture data provided — Verified column not populated"

### Table Format Rules

- Datatype in brackets: `fieldName` (Type)
- Mainframe Source column uses **individual WMOD field names** (e.g., `WMOD-BAHO-PDT-TYP-CDE`), NOT WMID parameters
- Gateway DTO column uses getter notation (e.g., `getUkbaProductHoldings()[].classificationCode.code`)
- **Response Bean column MUST show specific field paths** (e.g., `ProductHolding.sortCode`), NOT just the EDO getter method name (e.g., `getUkbaProductDetails()`). Use RESPONSE_BEAN_FIELDS and MAPPER_METHOD_BODIES from discovery data.
- **REST Response column MUST show specific field name and type** (e.g., `sortCode (String)`), NOT vague descriptions (e.g., `via mapper`). Use MAPPER_METHOD_BODIES from discovery data.
- Include TDL table in source column: `WMOD-BAHO-PDT-TYP-CDE (TDLBAHO)`
- Use `—` for unknown/missing fields
- Fields in gateway DTO but NOT mapped to response bean: In-Scope with `—` in Response Bean/REST columns, Origin = `gateway`

### Grouping

- `### In-Scope Fields (gateway + derived)` — origins: gateway, gateway → derived, derived
- `### Out-of-Scope Fields` — origins: full-retrieval-only, external-service, disabled-in-wrapper, converter-disabled, controller, request-context, error-field, unknown

### WMOD Field Fidelity

WMOD fields MUST come EXCLUSIVELY from WMOD_FIELD_INVENTORY in discovery summary. Do NOT add fields not in discovery data. Java Domain Field column MUST use field names from GATEWAY_DTO_FIELDS.

### Response Bean Traceability

For `gateway → derived` fields, show actual target field on response bean (e.g., `holdingCounters (via mapper)`). If a gateway field has no response bean target, use `—` in both columns with origin `gateway`.

### Verification Notes (end of Section 5)

After tables, add `### Verification Notes` listing:
- Fields downgraded from In-Scope to Out-of-Scope due to verification
- DataGroups disabled in wrapper
- Enrichment methods in EBS but not in application
- Converter fields commented out

### Rules

- Every field from response bean class MUST appear
- Do NOT use "Needs verification" — use explicit origin + `—`
- Do NOT use abbreviated codes

---

## Section 6: Backend Mapping Variants

---

#### Variant A: Mainframe Table Mappings (transport: `mainframe-mq`)

**Scope:** Covers the mainframe side — what happens after the Gateway dispatches to the mainframe. Do NOT repeat MQ queue names, timeout, JMS config, or gateway config keys here.

**Variant A mandatory sub-sections (mainframe-mq):** When the transport is `mainframe-mq`,
Section 6 MUST include ALL 9 of the following sub-sections in order. Do NOT omit any.

1. **Transaction Registry** — Table: `Property | Value | Confidence`. MUST include ALL of the following rows:
   - Transaction Class (fully qualified name)
   - CICS Programme Code (with `getProgramCode()` value)
   - CICS Version Code (with `getVersionCode()` value)
   - Composed Name (e.g., `TCSQCU` = T + systemCode + versionCode + programCode)
   - Messaging Name (from `getName()`, e.g., `TDLQCU` = "TDL" + versionCode + programCode)
   - Hierarchy (e.g., `CustomerAllRetrieveTransaction extends CustomerTransaction extends DatastreamTransaction`)
   - Property Key (from application.properties)
   - TRANSACTION_NAME (from application.properties value, include CI variant if different, e.g., `CUS_ALL_RETRIEVE_VO (CI variant: CUS_ALL_RETRIEVE_VN)`)
   - Source JAR
   - ROP/RIP (or "Not extracted" if source JAR was used)
   Every row MUST have a Confidence value.

   **Secondary Transaction (mixed-path scenarios):** If the discovery summary includes a
   `SECONDARY_TRANSACTION_CLASS`, add a sub-section after the primary Transaction Registry
   table titled **"Secondary Transaction (used by <which calls>):"** with a second table
   showing the secondary Transaction's Class, CICS codes, Messaging Name, Property Key,
   and TRANSACTION_NAME. Reference Section 4's Request Variations table for which calls
   use which Transaction.

2. **Gateway Calls** — Table: `Gateway Class | Method | Transaction Class | Purpose`.
   MUST list ALL methods from the Gateway class that are visible in the source JAR, not just the in-scope ones. Include BOTH in-scope calls (with distinct method overload signatures, e.g.,
   `findByPrimaryKey(UserContext, CustomerPk, ExtendedRequest)` vs
   `findByPrimaryKey(UserContext, CustomerPk, CustomerRequest)`)
   AND out-of-scope calls (e.g., `findAdditionalProductHoldings`, `findByOldPrimaryKey`) with their actual caller noted. Mark out-of-scope methods clearly.

3. **DataGroup Chain** — Compact table showing ONLY code-path DataGroups:
   `DataGroup | WMID Activation Field | TDL Table | Call | Notes`
   Add a note: "Transaction supports N additional DataGroups (not requested by this code path)."
   Do NOT list the full 46+ DataGroups with WMID/TDL — that creates duplication.

   **DATAGROUP NAME FIDELITY (critical — do NOT invent names):** DataGroup enum names in this table MUST come EXCLUSIVELY from `CODE_PATH_DATAGROUPS` in the discovery summary. Copy them character-for-character. Do NOT rename, paraphrase, or infer alternative names. The number of rows MUST equal the number of entries in `CODE_PATH_DATAGROUPS`, and each row's TDL table MUST match the corresponding entry in `CODE_PATH_TDL_TABLES`.

4. **WMID Request Field Inventory** — Table columns MUST be exactly: `WMID Field | Source | TDL Table | Notes`.
   Do NOT change column headers (e.g., do NOT use "Value Set" instead of "Source").

   This table MUST have exactly ONE row per entry in `CODE_PATH_DATAGROUPS` — matching the DataGroup count. If two DataGroups share the same WMID activation field (e.g., CARD_ACCOUNT_HOLDINGS and CARD_ACCOUNT_JOINT_HOLDERS both use WMID-CAHO-PRM), list BOTH rows with a note about the shared WMID. The Source column MUST show `CustomerDataGroup.<ENUM_NAME>`.

   Include compound/subsidiary WMID parameters that are implicitly activated alongside the primary code-path DataGroups. For example, if `UKBA_PRODUCT_HOLDINGS` activates both `WMID-BAHO-PRM` AND `WMID-BAJT-PRM` (for UKBA_JOINT_CUSTOMERS as a compound), list BOTH in the WMID inventory.

   Do NOT include transaction-level control fields (WMID-NUM-PRI-RQST-PRMS, WMID-PRI-RQST-TYP, WMID-NUM-RQST-PRMS). These are infrastructure parameters, not DataGroup activation fields.

   **SCOPING RULE:** This table MUST list ONLY the WMID fields corresponding to `CODE_PATH_DATAGROUPS`. Do NOT list WMID fields for `CAPABILITY_DATAGROUPS` here. Add a callout note after the table:

   > **Transaction capability reference:** The `<TransactionClass>` supports <N> WMID fields in total (see DataGroup Chain above). The full-retrieval code path (`<FullRetrievalMethod>`) uses a different doService call to request the broader set.

5. **WMOD Response Field Inventory** — One table per TDL table. 3 columns MANDATORY:
   `WMOD Field | Java Domain Field | Description`
   Each WMOD field MUST be listed **individually** with its specific name (e.g., `WMOD-BAHO-ACC-NUM`, NOT 'BAHO holding array fields'). Do NOT use generic or grouped rows.
   The Java Domain Field column MUST show the **specific getter path** (e.g.,
   `getUkbaProductHoldings()[].accountKey.accountNumber`, NOT `getUkbaProductHoldings()[].getAccountKey()`). Do NOT omit this column.
   Section 6.5 MUST NOT include -PRM status fields (e.g., `WMOD-BAHO-PRM`). These are DataGroupStatus indicators, not data-carrying response fields.
   Skip infrastructure fields (-HDR, -RTR, -ERR-CDE, -PRM, -CNT, -TMR status).

   **WMOD FIELD FIDELITY (critical — do NOT invent WMOD names):** The WMOD fields listed in
   Section 6.5 MUST come EXCLUSIVELY from the WMOD_FIELD_INVENTORY in the discovery summary.
   Do NOT add WMOD fields that are not present in the discovery data, even if the Gateway DTO
   class has fields that seem like they should have WMOD mappings. The extraction script reads
   actual `getField("WMOD-...")` calls from the Transaction source — if a DTO field has no
   corresponding WMOD extraction, it means:
   - The field is set by a different mechanism (derived, computed, from a different DataGroup)
   - The field doesn't exist on this specific DTO version
   If the discovery data lists 11 WMOD fields for BAHO, Section 6.5 MUST show exactly 11 WMOD
   fields for BAHO — no more.

   **Non-standard WMOD prefixes:** WMOD field names do NOT always match their DataGroup prefix.
   For example, CARD_ACCOUNT_HOLDINGS (CAHO) uses `WMOD-CRD-*`, `WMOD-PMY-*`, and `WMOD-CRSD-*`
   prefixes — NOT `WMOD-CAHO-*`. Use the EXACT field names from the discovery data. Do NOT
   "normalize" them to match the DataGroup prefix convention.

   **Java Domain Field fidelity:** The Java Domain Field column MUST use field names from the
   GATEWAY_DTO_FIELDS in the discovery summary. Cross-reference each WMOD `getField()` call
   against the corresponding `set*()` call in the extraction output to determine the correct
   DTO field path. For example:
   - `getField("WMOD-CRD-ACC-NUM", fi)` → `setCardAccountNumber(...)` → `cardAccountNumber`
   - `getField("WMOD-PDT-CLS-CDE", fi)` → `Classification.find(...)` → `classificationCode.code`
   Do NOT map WMOD fields to DTO fields that don't exist on the actual class. If
   `UkbaProductHoldingData` has 8 declared fields, do NOT add fields like `balance`, `productName`,
   or `accountShortName` that don't appear in the GATEWAY_DTO_FIELDS.

6. **TDL Tables Accessed** — Table: `TDL Table | Access Type | Path | Description`.
   List the code-path TDL tables (Path=counter). Access Type: Read / Read (array) / Write.

   **SCOPING RULE:** This table MUST list ONLY the TDL tables from `CODE_PATH_TDL_TABLES` as primary rows (Path = `counter`). If `CAPABILITY_TDL_TABLES` are known, add them in a separate group below the primary rows with Path = `full-retrieval` and a note: "Accessed by full-retrieval path only — not by this service's counter-path doService calls."

   **WRITE SERVICES:** If `WRITE_TABLES` is present in the discovery summary, list each write table with Access Type = `Write` or `Insert`. For write-only services (no TDL read), the Quick Reference `**TDL Tables:**` row should be replaced with `**Write Tables:**` listing the target tables and key columns.

   **ORCHESTRATION SERVICES:** If `ORCHESTRATION_SUB_SERVICES` is present in the discovery summary, list each sub-service's TDL tables with Access Type = `Read (via sub-service)` and Path = `via <SubServiceName>`. The Quick Reference `**TDL Tables:**` row should read `**TDL Tables (via sub-services):** TABLE (DataGroup, via SubServiceName)` — enumerating each table with its originating sub-service, NOT just "TDL in sub-services".

7. **Command Chain** — Compact text tree:
   `Command → Gateway.method() → Transaction (CICS code) → DataGroup → WMID → TDL`
   If the discovery summary includes a Command class from an alternate code path (e.g.,
   a full-retrieval path that also calls `findByPrimaryKey` via a Command), include it
   as a separate chain. Do NOT dismiss it as "not involved" — document all Command paths
   that use the same gateway method, even if they are not on the primary counter path.
   If no Command class is involved in ANY code path, state: "No EBS Command class involved."

8. **MQ Configuration** — Table: `Property | Value | Confidence`.
   Include: Property Key, Send Queue, Reply Queue, Timeout.

9. **Verification Confidence** — Bullet list with per-item confidence:
   Transaction class/CICS code, Messaging name, DataGroup chain, WMOD inventory,
   doService call chains, Command chain, MQ configuration.
   Values: `verified-from-source`, `verified-from-RIP`, `inferred-from-convention`.

**Removed (was duplication in OLD version):**
- Full 46+ DataGroup tree with WMID→TDL for every capability DataGroup
- Separate "Command Class" one-liner (data in Command Chain)
- Separate "Mainframe Program Codes" table (data in Transaction Registry)

---

#### Variant B: SOAP Service Mappings (transport: `soap-stub` or `soap-eao`)

**StubConnector / EAO Class:** Full qualified name.

**SOAP Endpoint:** URL from `services.properties` or `application.properties`.

**SOAP Operations:**
| Operation | Purpose | Request Type | Response Type |

**Backend System:** Name of the external system.

**Configuration Keys:**
| Property Key | Value/Pattern | Purpose |

Reference: See `soap_eao_patterns.md` for detection and extraction details.

---

#### Variant C: Database Mappings (transport: `oracle-db-direct` or `db2-reference`)

**Gateway Class:** Full qualified name.
**Database Type:** Oracle | DB2

**Tables Accessed:**
| Table Name | Access Pattern | Content | Notes |

**JNDI Datasource:** Datasource name.
**Replacement Target:** Static Data Hub API
**Existing Partial Migration:** Note any existing ODS REST calls.

Reference: See `hybrid_service_patterns.md` for detection and extraction details.

---

#### Variant D: CMOD Document Mappings (transport: `cmod-odwek`)

**EAO Class:** Full qualified name.
**ODWEK Path:** HTTP POST path.

**Document Types:**
| Document Type | Description | Search Criteria |

**CMOD Server Configuration:**
| Property Key | Value/Pattern | Purpose |

Reference: See `cmod_odwek_patterns.md` for detection and extraction details.

---

#### Variant E: Hybrid Service Mappings (transport: `tcv-hybrid`)

**Dual-Path Architecture:**
| Aspect | Legacy Path | REST Path |
|--------|------------|-----------|
| Trigger | Feature flag OFF | Feature flag ON |
| Transport | MQ/SOAP via EBS | REST via connector |

**Feature Flag:** Name and configuration location.
**Legacy Path Details:** Document as per the appropriate variant.
**REST Path Details:** Connector name, target API endpoint.

**ConnectorGateway Classes (if applicable):**
| Gateway Class | Purpose |

**TCVM Data Model (if applicable):** Package names and key types.

Reference: See `hybrid_service_patterns.md` for detection and extraction details.

---

#### Variant F: SCV Integration Mappings (transport: `scv`)

**SCV Endpoint:** URL.
**Model Classes:**
| Class | Package | Purpose |

**Data Flow:**
```
Service -> SCV SOAP Client -> SingleCustomerView endpoint -> Card-specific data
```

**Feature Flag:** `scv_enabled` (if applicable).
**Card Data Scope:** What card-specific data is accessed.

Reference: See `hybrid_service_patterns.md` for detection and extraction details.

---

#### Variant G: REST API Connection (transport: `already-api-rest` or `already-api-direct-http`)

**Connector Name:** Resolved constant from doService call.
**Target API Endpoint:** If known from configuration.

**Note:** This service already uses a modern REST API connection. It is **out of scope** for the MTS migration pipeline.

---

#### Variant H: Data Source (transport: `reference-data-only` or `framework`)

State: "This service does not directly access mainframe TDL tables." and note the actual data source.

#### Variant I: SOAP Web Service Mappings (transport: `soap-webservice`)

Sub-sections:
1. **Web Service Identity** — Table: `Property | Value | Confidence`. Include: Web Service ID, Backend System, SOAP Endpoint, EGS Gateway class, Routing Condition (e.g., `belongsToILP()`).
2. **Request/Response Mapping** — Table: `SOAP Element | Gateway DTO Field | Description`. Map EGS gateway method parameters and return types to SOAP request/response elements.
3. **Dependencies** — EBS/EGS JARs used.
4. **Verification Confidence** — Per-item confidence.

#### Variant J: ITSU/Oracle Mappings (transport: `itsu-oracle`)

Sub-sections:
1. **Data Access Identity** — Table: `Property | Value | Confidence`. Include: EBS JAR, Data Access Class, Oracle Tables (if extractable), JNDI Datasource.
2. **Data Origin** — Describe whether data is read from Oracle directly via JDBC or from ITSU session context.
3. **Verification Confidence** — Per-item confidence.

#### Variant K: ALS Backend Mappings (transport: `als-backend`)

Sub-sections:
1. **ALS Transaction Identity** — Table: `Property | Value | Confidence`. Include: ALS Program Name, Transaction Class, parent class hierarchy (e.g., `LoansBalanceEnquiryTransaction → LoansTransaction → DatastreamTransaction`).
2. **ALS Input DAG Fields** — Table: `DAG Field | Source Value | Description`. List all `addField("AMWKWI00-*")` calls from the Transaction constructor with their source values.
3. **ALS Output DAG Fields** — Table: `DAG Field | DTO Setter | Java Type | Description`. List all `getField("AMWKMD00-*")` calls from `parseResponse()` with their DTO setter mappings.
4. **Dependencies** — EBS/EGS JARs used.
5. **Verification Confidence** — Per-item confidence.
