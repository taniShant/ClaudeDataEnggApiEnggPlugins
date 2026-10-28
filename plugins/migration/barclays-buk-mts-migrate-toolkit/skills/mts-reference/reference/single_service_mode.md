# Single-Service Mode

**Pre-flight:** Phase 0 runs before this mode and provides `PLATFORM`, `PYTHON_CMD`, `GRADLE_WRAPPER`, `GRADLE_CACHE_STATUS`, `SOURCE_JARS_FOUND`, `COMPILED_JARS_FOUND`, `JAVAP_PATH`, `COMPILED_JAR_FALLBACK`, `MIS_REPO_PATH`, and `MIS_REPO_STATUS`. Use `<PYTHON_CMD>` for all Python invocations.

**Extraction priority order for JAR-scanning steps (S.7a-S.7e):**
1. **MIS source repo** — if `MIS_REPO_PATH` is set and Transaction class is found in `<MIS_REPO_PATH>/src/main/java/`. See `mis_source_extraction.md`. Confidence: `verified-from-mis-source`.
2. **Source JAR** — if `jar_type: source` for the artifact.
3. **Compiled JAR fallback** — if `jar_type: compiled`. See `compiled_jar_extraction.md`.

**Skip rules for JAR-scanning steps (S.4, S.7a-pre, S.7a-S.7e):**
- `MIS_REPO_PATH` is set → prefer MIS source extraction. Only fall through to JAR steps if Transaction class NOT found in MIS source.
- `GRADLE_CACHE_STATUS=EMPTY` AND `MIS_REPO_PATH` not set → Skip all JAR steps. Record in warnings.
- `SOURCE_JARS_FOUND=0` AND `COMPILED_JAR_FALLBACK=NONE` AND `MIS_REPO_PATH` not set → Skip all JAR steps. Record in warnings.
- `SOURCE_JARS_FOUND=0` AND `COMPILED_JAR_FALLBACK != NONE` → Run JAR steps using **compiled JAR fallback** (see `compiled_jar_extraction.md`).
- `SOURCE_JARS_FOUND > 0` → Use source JARs as primary. For any artifact missing a source JAR, fall back to compiled JAR if available.

When a specific service/method name is provided, run a focused discovery scoped to that one service only.

## Path Handling (CRITICAL for multi-project support)

All file paths in the steps below (e.g., `src/main/java/`, `build.gradle`) are RELATIVE to
`PROJECT_PATH`. When executing ANY Grep, Glob, or Read, prefix with PROJECT_PATH.

- "Grep src/main/java/" → `Grep <PROJECT_PATH>/src/main/java/`
- "Read build.gradle" → `Read <PROJECT_PATH>/build.gradle`
- "Glob src/test/resources/" → `Glob <PROJECT_PATH>/src/test/resources/`

**Never use bare relative paths.** The orchestrator sets PROJECT_PATH from the user's argument or current working directory.

## Step S.1 — Find the target doService call

Grep `<PROJECT_PATH>/src/main/java/` for the method name provided by the user. Look for:
- `doService(` calls where the method argument matches the target name (string literal or constant)
- Constants files where the target name is defined as a string constant, then find where that constant is used in a `doService(` call
- **Pattern 3 (variable method):** If the target method name is NOT found as a direct argument to `doService`, it may be passed through a multiplexer method. Search for the method name as a string constant or literal anywhere in the codebase, then trace whether that value is passed as an argument to a method that internally calls `doService` with a variable method parameter. See `doservice_patterns.md` Pattern 3 for the full algorithm.

Also check for MCA2 patterns:
- `callService(` calls where the lambda body contains the target method name (e.g., `svc -> svc.targetMethod(...)`)

Capture: file path, line number, surrounding context (10 lines), the service name constant, and the method name constant.

## Step S.2 — Resolve service and method names

Resolve the SERVICE_NAME constant and method name constant to their actual string values (same approach as full mode Steps 1.2, 1.3, and 1.3b).

## Step S.3 — Read build.gradle for EBS/EGS dependencies

Grep `<PROJECT_PATH>/build.gradle` for `ebs_|egs_`. Also check `<PROJECT_PATH>/gradle/dependencies-references.gradle`.

## Step S.4 — Locate source JARs and compiled JARs in Gradle cache

**Skip this step if `GRADLE_CACHE_STATUS=EMPTY`.** Record in warnings.

**First pass — source JARs:**

For each EBS/EGS dependency, use Python (cross-platform, not blocked by Bash sandbox):
```bash
<PYTHON_CMD> "${CLAUDE_PLUGIN_ROOT}/scripts/jar_find_sources.py" <artifact-name>
```

**Second pass — compiled JARs (for artifacts without source JARs):**

If `COMPILED_JAR_FALLBACK != NONE`, also locate compiled JARs:
```bash
<PYTHON_CMD> "${CLAUDE_PLUGIN_ROOT}/scripts/jar_find_compiled.py" <artifact-name>
```

**Important — NOT_MAPPED artifacts still need JAR search:**

When `MIS_REPO_STATUS=NOT_MAPPED` for the target service's EGS JAR (e.g., `egs_mortgages`, `egs_bonds`, `egs_loans`), do NOT skip the JAR search. The first and second passes above (`jar_find_sources.py` and `jar_find_compiled.py`) search the Gradle cache by artifact name and will find the JAR if the project has been built locally. Run them for ALL EBS/EGS dependencies listed in `build.gradle`, including those without MIS repo mappings.

If `jar_find_sources.py` reports no match for a specific artifact, also try common name variations:
- Underscore to dash: `egs_mortgages` → `egs-mortgages`
- With version suffix: `egs_mortgages-07.0005.001`
- Group path variant: `com.barclays.gs/egs_mortgages`

If no source or compiled JAR is found after all attempts, record a warning: `"EGS JAR '<name>' not found in Gradle cache or MIS source. Run './gradlew dependencies' to populate the cache, then re-run."` The per-service doc agent will produce a partial document with notes about missing data.

**Annotate each artifact** with `jar_type: source` or `jar_type: compiled`. Steps S.7a-S.7e use this annotation to choose the extraction approach.

## Step S.5 — Trace call chain for this service only

From the doService call site:
- Identify the containing method and class
- Grep `<PROJECT_PATH>/src/main/java/` for callers up until reaching a controller method with a REST annotation
- Record ALL paths — the doService may be reachable from multiple endpoints

**Multi-endpoint enforcement:** After finding the first controller entry point, also:
1. Search the SAME controller class for OTHER methods that call the same service class
2. Search for ALL `@PostMapping`, `@GetMapping`, `@RequestMapping` methods in the controller
   that invoke service methods leading to the same doService call
3. If the doService is inside a shared method (e.g., `retrieveHoldingPointers`), trace ALL
   callers of that shared method — they may lead to different controller endpoints

**Alternate code paths:** Also trace indirect paths through the service class:
1. If the service class has a Command pattern (e.g., `FindCustomerProductHoldingsCommand`),
   trace the command's `doExecute()` method to see if it calls the same gateway method
2. Record these as alternate code paths even if they use different Request types or DataGroups

## Step S.6 — Check for WireMock test data

```
Glob <PROJECT_PATH>/src/test/resources/__files/**/*
Glob <PROJECT_PATH>/src/test/resources/mappings/**/*
```

**Search strategy (BROAD — do NOT match only exact service name):**
1. First, identify the domain directory: look for folders matching the service domain keyword (e.g., `productholdings/`, `customer/`, `membership/`)
2. List ALL JSON files in that directory
3. Look for files containing the service or domain keyword (e.g., `customer_product_holdings`, `find_customer`, `product_holdings_current`)
4. If found: **READ the JSON content** of the most representative fixture (prefer `*_current.json`, `*_all_holdings.json`, or the largest file)
5. Extract ALL non-null field paths from the JSON as `WIREMOCK_RESPONSE_FIELDS` — this becomes the COMPLETE response field inventory for Section 5

**Example:** For `CustomerHoldingsService.findCustomerProductHoldings`:
- Domain directory: `src/test/resources/__files/productholdings/`
- Best fixture: `customer_product_holdings_current.json` or `customer_product_holdings_all_holdings.json`
- Extract: `ukbaProductDetails[].accountKey.sortCode`, `ukbaProductDetails[].productId`, etc.

**Why this matters:** The WireMock fixture IS the REST response contract. Section 5 enumerates ALL fields from this fixture, then traces each backward to its source (WMOD field, enrichment, or derived). This prevents blank columns.

## Step S.7 — Transport-specific data extraction (conditional)

First, classify the service's transport type using the deterministic algorithm from `service_categories.md` (same as discovery agent Step 1.17). Then run the extraction sub-step matching the transport type.

**Skip data extraction** if the service is `reference-data-only`, `framework`, or `already-api-*`.

### S.7a-e — Mainframe data extraction (transport: `mainframe-mq`)

Only run for services whose EBS JAR has a corresponding EGS ODS MF JAR.

**Skip S.7a-S.7e if `GRADLE_CACHE_STATUS=EMPTY`.** Record in warnings.

**S.7a-pre** — Resolve Gateway method to Transaction class:

Before extracting Transaction identity, determine WHICH Transaction class the gateway
uses for the traced code path. A single gateway method name (e.g., `findByPrimaryKey`)
often has MULTIPLE overloads that route to DIFFERENT Transaction classes based on the
request parameter type.

1. **Extract the Gateway class source** from the EGS JAR:
   Search for the Gateway class name (from S.2) in the EGS source JAR. Read the full
   source and identify ALL overloads of the target method.

2. **Extract the EAO implementation class** from the EGS JAR:
   The EAO class (e.g., `CustomerEao`) implements the Gateway interface and contains
   the Transaction instantiation logic. Search for `Eao.java` files in the EGS JAR
   that match the service domain. Read the EAO source and find the target method
   implementations.

3. **Map each gateway overload to its Transaction class:**
   In the EAO, each overload creates a specific Transaction via
   `<TransactionClass>.newTransaction(...)`. Record the mapping:
   - `findByPrimaryKey(UserContext, Key, CustomerRequest)` → creates `<TransactionA>`
   - `findByPrimaryKey(UserContext, Key, ExtendedRequest)` → creates `<TransactionB>`

4. **Cross-reference with the code path from S.5:**
   From S.5's call chain, identify the actual Request types created for each doService
   call. Check which `new CustomerRequest(...)` or `new ExtendedRequest(...)` calls
   are made. Map each call to the corresponding Transaction class.

5. **Select the primary Transaction class:**
   - If ALL calls in the code path use the same Request type → use that Transaction
   - If calls use DIFFERENT Request types (mixed path) → select the Transaction that
     handles the MOST code-path DataGroups. For the `findByPrimaryKey` counter path,
     `CustomerAllRetrieveTransaction` handles all 4 DataGroups (BAHO, MAHO, CAHO, BARH)
     while `CustomerExtendedRetrieveTransaction` only handles BAHO and MAHO.
   - Record BOTH Transaction classes and note which calls use which, but extract
     WMID/WMOD data from the PRIMARY Transaction only.

6. **Store the resolution** for use in S.7a-S.7e:
   ```
   PRIMARY_TRANSACTION_CLASS=<ClassName>
   PRIMARY_TRANSACTION_OVERLOAD=<signature>
   SECONDARY_TRANSACTION_CLASS=<ClassName> (if mixed path)
   SECONDARY_TRANSACTION_OVERLOAD=<signature>
   ```

**S.7a** — Extract Transaction class identity from EGS JAR:

Using the `PRIMARY_TRANSACTION_CLASS` from S.7a-pre, extract its identity methods.
Do NOT scan all Transaction.java files — only extract the resolved class.

**If `MIS_REPO_PATH` is set (highest priority — try first):**

Find the Transaction class file by name:
```bash
find <MIS_REPO_PATH>/src/main/java/ -name "<PRIMARY_TRANSACTION_CLASS>.java" 2>/dev/null
```
Store the result as `MIS_TRANSACTION_FILE_PATH`.
If found, Read `MIS_TRANSACTION_FILE_PATH` and extract `getProgramCode()`, `getVersionCode()`, `getName()`, and class hierarchy.
Tag all data: `verified-from-mis-source`. Skip the JAR extraction steps below for this class.
If NOT found in MIS source, fall through to source JAR or compiled JAR extraction.

**If `jar_type: source`** (primary — unchanged):
```bash
<PYTHON_CMD> "${CLAUDE_PLUGIN_ROOT}/scripts/jar_extract_transaction_identity.py" <egs-sources-jar> <PRIMARY_TRANSACTION_CLASS>
```
Extract identity methods (`getProgramCode`, `getVersionCode`, `getName`, `class.*extends`).

If S.7a-pre identified a `SECONDARY_TRANSACTION_CLASS` (mixed path), also extract its identity methods using the same approach but label them as secondary.

**If `jar_type: compiled`** (fallback — see `compiled_jar_extraction.md`):

- **Tier 1 (constant pool):** Use `scan_compiled_jar(jar_path, class_filter='Transaction')` to extract class hierarchy, all WMID/WMOD strings, method refs, and program/version code candidates (short-string heuristic).
- **Tier 3 (javap):** If `JAVAP_PATH != NOT_AVAILABLE`, run `javap -c -p` on the Transaction `.class` and use `parse_identity_methods()` for exact `getProgramCode()`/`getVersionCode()` values.

```bash
<PYTHON_CMD> "${CLAUDE_PLUGIN_ROOT}/scripts/jar_extract_transaction_compiled.py" <compiled-egs-jar>
```

**S.7b** — Extract DataGroup-WMID-TDL chain from Transaction class constructor:

**If `MIS_REPO_PATH` is set (highest priority — try first):**

If `MIS_TRANSACTION_FILE_PATH` was set in S.7a, grep WMID and TDL fields from it directly:
```bash
grep -oE '"WMID-[A-Z0-9-]+"' <MIS_TRANSACTION_FILE_PATH> | sort -u
grep -oE '"TDL[A-Z0-9]+"' <MIS_TRANSACTION_FILE_PATH> | sort -u
```
Also grep for DataGroup enum references and `addField` conditional blocks in the same file.
Tag all data: `verified-from-mis-source`. Skip JAR extraction below for this class.

**If `jar_type: source`** (primary — unchanged):
```bash
<PYTHON_CMD> "${CLAUDE_PLUGIN_ROOT}/scripts/jar_extract_wmid_chain.py" <sources-jar> <PRIMARY_TRANSACTION_CLASS>
```

**If `jar_type: compiled`** (fallback — see `compiled_jar_extraction.md`):

- **Tier 1 (constant pool):** WMID-\*-PRM strings already extracted in S.7a. Provides the complete WMID list but **cannot** determine DataGroup-to-WMID conditional attribution.
- **Tier 2 (ROP):** Use `extract_rop_rip(jar_path)` to parse `riprop/*.ROP` files — provides **definitive** WMID parameter list.
- **Tier 3 (javap):** If `JAVAP_PATH != NOT_AVAILABLE`, use `parse_javap_constructor()` to extract exact `getstatic CustomerDataGroup.<ENUM>` → `ldc "WMID-*-PRM"` → `invokevirtual addField` bytecode patterns for conditional DataGroup→WMID mappings.

**If javap is not available:** Record all WMID parameters without DataGroup attribution. Note: `"DataGroup-to-WMID conditional mapping not available (no javap). WMID list is complete."` Confidence = `partial-from-bytecode`.

Resolve TDL table names using WMID naming convention (`WMID-XXXX-PRM` -> `TDLXXXX`).

**Compound/subsidiary WMID parameters:** When extracting WMID fields from the Transaction constructor, include compound/subsidiary activation parameters. For example, if `UKBA_PRODUCT_HOLDINGS` activates both `WMID-BAHO-PRM` AND `WMID-BAJT-PRM` (for UKBA_JOINT_CUSTOMERS as a compound), list BOTH in the WMID inventory. Look for cases where a single `addField` block sets multiple WMID-\*-PRM fields, or where one DataGroup's activation conditionally sets additional PRM fields for subsidiary DataGroups.

**S.7b-scope** — Cross-reference against actual code path:

After extracting ALL DataGroups from the Transaction class (the full capability set), cross-reference them against the DataGroups actually passed in the code path traced in Step S.5.

1. From Step S.5's call chain, identify the specific `CustomerDataGroup[]` arrays passed to each `doService` / gateway call. These are the **code-path DataGroups**.
2. Mark each DataGroup from S.7b as either:
   - `code-path` — appears in the actual call chain from S.5
   - `capability-only` — exists in the Transaction class but is NOT sent by the traced code path
3. Derive `CODE_PATH_TDL_TABLES` = only the TDL tables corresponding to `code-path` DataGroups.
4. Derive `CAPABILITY_TDL_TABLES` = all remaining TDL tables (from `capability-only` DataGroups).

This distinction is critical: Quick Reference and Request Field Inventory use ONLY `code-path` items. Section 6 DataGroup Chain shows the full capability but labels each group.

**S.7c** — Extract Command class gateway calls from EBS JAR:

**If `MIS_REPO_PATH` is set (highest priority — try first):**

Find Command class files by name:
```bash
find <MIS_REPO_PATH>/src/main/java/ -name "*Command*.java" 2>/dev/null
```
Read any Command class whose name matches the service being documented.
Grep for DataGroup enum usage and gateway method calls directly from the source.
Tag: `verified-from-mis-source`. Skip JAR extraction below.

**If `jar_type: source`** (primary — unchanged):
```bash
<PYTHON_CMD> "${CLAUDE_PLUGIN_ROOT}/scripts/jar_extract_command_calls.py" <ebs-sources-jar>
```

**If `jar_type: compiled`** (fallback — see `compiled_jar_extraction.md`):

- **Tier 1 (constant pool):** Use `scan_compiled_jar(jar_path, class_filter='Command')` to extract `CustomerDataGroup.<ENUM>` field refs (DataGroups requested) and `gateway.findByPrimaryKey` / `gateway.findPfsDataByCustomerId` method refs (gateway calls). These are exact from the constant pool.

```bash
<PYTHON_CMD> "${CLAUDE_PLUGIN_ROOT}/scripts/jar_extract_command_compiled.py" <compiled-ebs-jar>
```

**S.7c-orch** — Detect and trace orchestration sub-services:

After extracting the Command class, check if it contains `doService(` calls to OTHER services
(i.e., the Command itself orchestrates sub-services rather than directly calling a gateway).

1. **Detect:** Grep the Command class source for `doService(`, `serviceManager.doService(`,
   or `serviceDelegate.doService(` calls. If found, this is an **orchestration service**.
2. **For each sub-service call found:**
   - Extract the sub-service SERVICE_NAME and method name arguments
   - Check if a service doc already exists at `docs/mts/service-doc-<SubService>-<method>.md`
   - If it exists: extract the TDL tables from its Quick Reference section
   - If it doesn't exist: note the sub-service as "undocumented — TDL tables not yet known"
3. **Compile `ORCHESTRATION_SUB_SERVICES`** in the discovery summary:
   ```
   ORCHESTRATION_SUB_SERVICES:
     <SubServiceName>.<method>:
       TDL_TABLES: [<tables from sub-service doc or from extraction>]
       SOURCE: "from existing service doc" | "undocumented"
     <SubServiceName2>.<method>:
       ...
   ```
4. **Aggregate for Quick Reference:** The per-service doc agent uses `ORCHESTRATION_SUB_SERVICES`
   to populate `**TDL Tables (via sub-services):** TABLE (DataGroup, via SubServiceName)` in
   the Quick Reference. This replaces the uninformative "TDL in sub-services" placeholder.

**S.7d** — Extract WMOD response fields from Transaction class:

For each TDL table, extract ALL individual WMOD field names from `parseResponse()` and `parseArrayResponse()` methods. Use the pattern `getField.*WMOD|getIntField.*WMOD|getDateField.*WMOD|getLongField.*WMOD`. Each `getField("WMOD-XXXX-YYYY")` call becomes one row in the WMOD inventory. Do NOT group fields as 'holding array fields' — list each individually.

**If `MIS_REPO_PATH` is set (highest priority — try first):**

If `MIS_TRANSACTION_FILE_PATH` was set in S.7a, grep WMOD fields from it directly:
```bash
grep -oE '"WMOD-[A-Z0-9-]+"' <MIS_TRANSACTION_FILE_PATH> | sort -u
```
Group by containing method (e.g. `selectUkbaProductHoldings`, `selectCardAccountHoldings`) for TDL table attribution.
Tag: `verified-from-mis-source`. Skip JAR extraction below.

**If `jar_type: source`** (primary — unchanged):
```bash
<PYTHON_CMD> "${CLAUDE_PLUGIN_ROOT}/scripts/jar_extract_wmod_fields.py" <sources-jar> <PRIMARY_TRANSACTION_CLASS>
```

**Per-method grouping:** When extracting WMOD fields, group them by their containing method
(e.g., `selectUkbaProductHoldings`, `selectCardAccountHoldings`, `selectBarclayBankCardHoldings`,
`selectMiscellaneousProductHoldings`). Include the `set*()` calls alongside each `getField()`
call to provide the DTO field mapping. This grouping helps the per-service doc agent:
1. Know exactly which WMOD fields belong to which TDL table
2. Map each WMOD field to its correct DTO setter
3. Detect non-standard WMOD prefixes (e.g., `WMOD-CRD-*` in a CAHO method)

Format in the discovery summary:
```
WMOD_FIELD_INVENTORY:
  TDLBAHO (from selectUkbaProductHoldings, 11 fields):
    WMOD-BAHO-LCK-TKN → setLockToken()
    WMOD-BAHO-SRT-CDE → setAccountKey(AccountPk(sortCode, ...))
    WMOD-CUS-ACC-NUM → setAccountKey(AccountPk(..., accountNumber))
    ...
  TDLCAHO (from selectCardAccountHoldings, 9 fields):
    WMOD-CRD-ACC-NUM → setCardAccountNumber()
    ...
```

**If `jar_type: compiled`** (fallback — see `compiled_jar_extraction.md`):

- **Tier 1 (constant pool):** WMOD-\* strings already extracted in S.7a. Provides the complete list of WMOD field names.
- **Tier 2 (RIP):** Use `extract_rop_rip(jar_path)` to parse `riprop/*.RIP` files — provides **definitive** WMOD field list **with data types and lengths**. Prefer Tier 2 when available.

```bash
<PYTHON_CMD> "${CLAUDE_PLUGIN_ROOT}/scripts/jar_extract_wmod_rip.py" <compiled-egs-jar>
```

**S.7d-post** — Extract Gateway DTO class field declarations:

When `jar_type: source` and the Transaction class's `parseResponse()`/`parseArrayResponse()` methods populate Gateway DTO classes (e.g., `UkbaProductHoldingData`), extract their field declarations and getter signatures. This produces `GATEWAY_DTO_FIELDS` used by the per-service doc agent for field-name fidelity.

```bash
<PYTHON_CMD> "${CLAUDE_PLUGIN_ROOT}/scripts/jar_extract_dto_fields.py" <egs-sources-jar> <PRIMARY_TRANSACTION_CLASS>
```

The script discovers DTO class names by scanning for `new <Name>Data(` and `<Name>Data <var> =` patterns in the Transaction source, then extracts `private/protected/public` field declarations and `public get*()` getter signatures from each DTO class found in the JAR.

**S.7e** — Correlate TRANSACTION_NAME:
```bash
grep "TRANSACTION_NAME" <PROJECT_PATH>/src/main/resources/application.properties
```

**S.7e-write** — Extract write/insert table targets (for write services):

If the service method name contains `add`, `insert`, `create`, `write`, `update`, `delete`, or
the gateway method name contains `insert`, `update`, `delete`, `write`, `save`, `store`:

1. **From EGS source JAR or MIS source:** Find the gateway method implementation (e.g.,
   `AuditGateway.insertAuditEvents()`). Look for SQL patterns (`INSERT INTO`, `UPDATE`, `MERGE`),
   table name string literals, or Transaction class write methods (`putField`, `addField` for write WMIDs).
2. **From EBS source JAR:** Read the Command class (e.g., `AddAuditCommand`) and check what data it maps to the gateway call. Note the request-to-gateway field mapping.
3. **From Confluence (if available):** Search for the service's sAPI Confluence page (e.g., `auditevents-sapi`) which typically documents the target table schema.

Document under `WRITE_TABLES` in the discovery summary:
```
WRITE_TABLES:
  <TABLE_NAME> (write target — <column1>, <column2>, ...)
  <TABLE_NAME2> (write target — <column1>, <column2>, ...)
```

The per-service doc agent uses `WRITE_TABLES` to populate a `**Write Tables:**` row in Quick Reference (Section 1) instead of `**TDL Tables:**` for read services. If a service both reads AND writes, document both.

### S.7f-S.7m — Non-mainframe transport extraction

For non-mainframe transports (soap-stub, oracle-db-direct, db2-reference, cmod-odwek, tcv-hybrid, soap-webservice, scv, itsu-oracle, als-backend), follow the extraction sub-steps in `transport-extraction-steps.md`.

---

## Step S.7n — Migration Complexity Extraction

After all transport-specific extraction is complete (S.7a-m), extract migration complexity indicators. These populate Section 9 of the per-service doc.

### S.7n-1: Business Logic Complexity

- If MIS_REPO_PATH is set: find all `*Helper*.java`, `*Validator*.java`, `*Util*.java` in the MIS source repo for this service's EBS/EGS JARs
- Count total lines of non-test Java in Helper/Command classes
- Count conditional branches (`if`/`else`, `switch`, ternary `?:`)
- Classify:
  - **LOW**: <200 lines, <10 branches
  - **MEDIUM**: 200-1000 lines, 10-50 branches
  - **HIGH**: >1000 lines or >50 branches
- If MIS_REPO_PATH not set: report `"Data not available — MIS source not cloned"`

### S.7n-2: Sub-Service Call Detection

- From the call chain traced in S.5, list ALL distinct gateway/service calls (not just the primary gateway)
- Include: secondary gateways (AccountGateway, ProductGateway), external services (DPAAS, ReferenceService, ODSSwitchGateway)
- Count distinct sub-service calls

### S.7n-3: Security Pattern Detection

- Grep the traced call chain files for:
  - `"DPAAS"` OR `"DataProtection"` OR `"tokenize"` OR `"tokenise"`
  - `"IDV"` OR `"IdentityVerification"` OR `"Verification"`
  - `"encrypt"` OR `"decrypt"` OR `"mask"`
  - `"TIAA"` OR `"OAuth"` OR `"AccessToken"`
- Record: pattern name + class where found
- If none found: `"None detected"`

### S.7n-4: ODS Switch State Detection

- Grep `application.properties` for the service's TRANSACTION_NAME and look for adjacent ODS switch configuration
- Grep the EAO class (from MIS repo or source JAR) for:
  - `"ODSSwitchGateway"` OR `"switchValue"` OR `"ODSMainframeSwitchValue"`
- If found: extract current switch modes from the EAO logic
- Record: switch value (`O`/`M`/`U`/`B`) or `"No ODS switch detected"`
  - O = ODS only, M = Mainframe only, U = ODS with MF fallback, B = Both (parallel)

### S.7n-5: Batch Pattern Detection

- Check the Command class (from S.5 call chain) for:
  - Array iteration (for/while loops over request arrays)
  - Batch size constants (`MAX_*`, `BATCH_SIZE`)
  - Partial-failure handling (error count aggregation)
- Check the EAO class for:
  - `sliceArray()` or similar batch-splitting logic
  - Concurrent transaction submission patterns
- Record: `batch=true/false` + detail

### S.7n-6: Error Response Code Count

- If MIS_REPO_PATH is set: find `*Response.java` or `*ResponseCode.java` in the EBS/EGS source for this service
- Count distinct response code constants
- Classify severity categories (success, warning, error, fatal)
- Record: total count + category breakdown
- If not found: `"Data not available"`

### S.7n-7: Write Complexity Classification (write services only)

- If IS_WRITE=true, check the Update/Insert Transaction class for:
  - Status-based filtering (`DIRTY`/`NEW`/`DELETED`/`CLEAN`)
  - Ordering constraints (sort by relationship type, etc.)
  - Multi-table writes (multiple `append*()` methods)
- Classify:
  - **SIMPLE**: 1 table, no filtering
  - **COMPLEX**: multi-table or status filtering or ordering
- If IS_WRITE=false: `"N/A"`

### S.7n-8: Secondary Backend Detection

- Check EGS gateway dependencies and config for secondary data sources beyond the primary transport (e.g., Teradata DW alongside mainframe-mq)
- Known patterns to detect:
  - `"com.teradata.jdbc.TeraDataSource"` → Teradata data warehouse
  - `"DataProtectionService"` / `"DPAAS"` → already captured in S.7n-3
  - `"ODSSwitchGateway"` → already captured in S.7n-4
- Record: secondary_backend name + connection details
- Does NOT change primary transport classification — this is a marker only

### S.7n output format

Pass to the discovery summary (Step S.8) as:
```
MIGRATION_COMPLEXITY:
  business_logic: <LOW|MEDIUM|HIGH> (<line count>, <class names>)
  sub_service_calls: <count> (<list of gateways/services called>)
  security_patterns: [<list>] or "None detected"
  ods_switch_state: <O|M|U|B> or "No ODS switch detected"
  batch_pattern: <true|false> (<detail>)
  error_code_count: <count> (<breakdown>) or "Data not available"
  write_complexity: <SIMPLE|COMPLEX|N/A> (<detail>)
  secondary_backends: [<list>] or "None"
```

---

## Step S.8 — Compile focused discovery summary

**VERBATIM_CONTRACT block (MANDATORY):**

Before compiling the rest of the summary, assemble this exact block by copying values directly from the extraction outputs. Do NOT paraphrase or re-derive these values:

```
VERBATIM_CONTRACT:
  TITLE: "<SERVICE_NAME>.<doServiceMethod>"
  TRANSACTION_NAME: "<from application.properties TRANSACTION_NAME= line>"
  CICS_CODE: "<from getProgramCode() + getVersionCode() in Transaction source, composed>"
  MESSAGING_NAME: "<from Transaction.getName() or TDL+version+program>"
  PROPERTY_KEY: "<from application.properties property prefix>"
  SEND_QUEUE: "<from application.properties JMS_SEND_QUEUE_NAME= line>"
  REPLY_QUEUE: "<from application.properties JMS_CONSUME_QUEUE_NAME= line>"
  TIMEOUT: "<from application.properties TIMEOUT= line>"
  EBS_DEPENDENCIES: ["<groupId:artifactId:version>", ...]
  EGS_DEPENDENCIES: ["<groupId:artifactId:version>", ...]
  CODE_PATH_DATAGROUPS: ["<exact enum names from Command source, comma-separated>"]
  CODE_PATH_TDL_TABLES: ["<TDL table name per DataGroup, derived from WMID naming: WMID-XXXX-PRM → TDLXXXX>"]
  CODE_PATH_WMID_FIELDS: ["<WMID-XXXX-PRM per DataGroup>"]
  GATEWAY_DTO_FIELDS:
    <DTOClassName>: [<field1>, <field2>, ...]
    <DTOClassName2>: [<field1>, <field2>, ...]
  WIREMOCK_VERIFIED_FIELDS: [<field paths that are non-null in WireMock response JSON>]
  WRITE_TABLES: ["<table_name> (<column1>, <column2>, ...)", ...] # Only for write services (from S.7e-write). Omit for read-only services.
  ORCHESTRATION_SUB_SERVICES: # Only for orchestration services (from S.7c-orch). Omit for direct gateway services.
    <SubService.method>: { TDL_TABLES: [...], SOURCE: "..." }
    ...
  SECONDARY_TRANSACTION_CLASS: "<from S.7a-pre step 6, if mixed path detected. Omit if single transaction.>"
  SECONDARY_CICS_CODE: "<from S.7a secondary extraction. Omit if single transaction.>"
  SECONDARY_CALLS: "<which doService calls use the secondary, e.g. 'Calls 1-2 (ExtendedRequest)'>"
```

**MANDATORY data collection for VERBATIM_CONTRACT:**

- **EBS/EGS dependencies:** list ALL JARs whose classes appear in the traced call chain (from S.5 and S.7c). Include secondary gateway JARs (e.g., `egs_product` if `ProductGateway` is called by the Command).

- **CODE_PATH_TDL_TABLES:** derive EACH table name from the WMID field name using the standard convention: `WMID-XXXX-PRM` → `TDLXXXX`. Example: `WMID-CAJH-PRM` → `TDLCAJH`, `WMID-APDH-PRM` → `TDLAPDH`. Do NOT invent non-standard abbreviations.

- **GATEWAY_DTO_FIELDS:** from S.7d-post, list the EXACT private field declarations per Gateway DTO class (e.g., `UkbaProductHoldingData: [accountKey, productKey, classificationCode, endDate, takenOutDate, mandateType, legalEntityIdentifier, tradingEntityIdentifier]`). The per-service doc agent uses this to determine which fields are In-Scope (gateway) vs Out-of-Scope (enrichment from secondary calls).

- **WIREMOCK_VERIFIED_FIELDS:** from S.6, if WireMock response JSON files are found, READ the JSON content and list all field paths that have non-null values. Example: `[ukbaProductDetails[].accountKey.sortCode, ukbaProductDetails[].productId, ...]`. The per-service doc agent uses this for the Verified column (`VERIFIED` vs `—`).

- **RESPONSE_BEAN_FIELDS and MAPPER_METHOD_BODIES** (from the Performance Optimisation section): these are MANDATORY, not optional. Read the mapper/assembler classes during S.5 and embed the field-level mapping (e.g., `sortCode → ProductHolding.sortCode`, `accountKey.accountNumber → ProductHolding.accountNumber`). The per-service doc agent uses these for Section 5 columns 3 and 4.

Read ALL values directly from `application.properties`, EBS Command source, EGS Transaction source, mapper classes, and WireMock fixtures — do NOT guess or infer.

The per-service doc agent MUST copy VERBATIM_CONTRACT values into the output and use GATEWAY_DTO_FIELDS, WIREMOCK_VERIFIED_FIELDS, and RESPONSE_BEAN_FIELD_MAP for Section 5 accuracy.

Create a structured summary containing:
- The single doService call with: service name (resolved), method name (resolved), file:line, request DTO, response DTO, containing class, category
- EBS/EGS dependencies with source JAR availability
- Full call chain(s) for this service
- WireMock test data paths (if found)
- Transaction Registry data for this service (from S.7a, if applicable)
- DataGroup-WMID-TDL chain (from S.7b, if applicable)
- Command chain (from S.7c, if applicable)
- Secondary Transaction identity (from S.7a-pre and S.7a, if mixed path detected)
- All alternate code paths discovered in S.5 (entry points, Request types, DataGroups per path)
- WMOD response field inventory (from S.7d, if applicable)
- WMOD field counts per TDL table (e.g., "TDLBAHO: 11 fields, TDLCAHO: 9 fields, TDLBARH: 21 fields") — the per-service doc agent MUST match these exact counts in Section 6.5
- Gateway DTO class field declarations (from S.7d-post, if applicable)
- TRANSACTION_NAME correlation (from S.7e, if applicable)
- Confidence indicators per item (see `compiled_jar_extraction.md` for confidence levels: `verified-from-mis-source`, `verified-from-source`, `verified-from-bytecode`, `verified-from-rop-rip`, `partial-from-bytecode`, `inferred-from-convention`)

**CRITICAL — Scope-separated DataGroup/TDL data (from S.7b-scope):**

The discovery summary MUST clearly separate code-path vs capability data using these labels:

```
CODE_PATH_DATAGROUPS: [list of DataGroups actually sent by the traced code path]
CODE_PATH_TDL_TABLES: [list of TDL tables for code-path DataGroups only]
CODE_PATH_WMID_FIELDS: [list of WMID fields for code-path DataGroups only]

CAPABILITY_DATAGROUPS: [list of ALL remaining DataGroups from Transaction class]
CAPABILITY_TDL_TABLES: [list of ALL remaining TDL tables]
```

**DATAGROUP/TDL NAME FIDELITY (critical — do NOT rename or paraphrase):**
DataGroup enum names and TDL table names in `CODE_PATH_DATAGROUPS` and `CODE_PATH_TDL_TABLES` MUST be copied CHARACTER-FOR-CHARACTER from the `jar_extract_command_calls.py` output (or from the Command class source). Do NOT paraphrase, abbreviate, or "improve" the names. The downstream per-service doc agent copies these verbatim into Sections 1, 6.3, 6.4, and 6.6.

Example (correct): `UKBA_JOINT_CUSTOMERS` (exact enum from `CustomerDataGroup`)
Example (WRONG): `UKBA_JOINT_HOLDINGS`, `JOINT_CUSTOMERS`, `UkbaJointCustomers`

The number of entries in `CODE_PATH_TDL_TABLES` MUST equal the number of entries in `CODE_PATH_DATAGROUPS`. If a DataGroup's TDL table name cannot be extracted (e.g., compiled-only JAR), derive it from WMID naming convention (`WMID-XXXX-PRM` → `TDLXXXX`) and note confidence as `inferred-from-convention`. Never drop a TDL table because WMOD extraction was incomplete.

The per-service doc agent uses `CODE_PATH_*` for Quick Reference and Request Field Inventory, and shows `CAPABILITY_*` only in Section 6 DataGroup Chain with clear labelling. The api-replacement-match pipeline reads Quick Reference and uses `CODE_PATH_*` for scoring — if capability-only items leak into Quick Reference, match scores are inflated.

## Step S.9 — Generate per-service doc

```bash
mkdir -p docs/mts
```

Launch **one** agent using the Task tool:

| Agent | subagent_type | Agent Instructions | Output File |
|-------|---------------|-------------------|-------------|
| Per-Service Doc | `general-purpose` | `${CLAUDE_PLUGIN_ROOT}/agents/mts-per-service-doc-agent.md` | `docs/mts/service-doc-<ServiceName>-<method>.md` |

**IMPORTANT:** Custom agent names (e.g., `mts-per-service-doc-agent`) are NOT valid `subagent_type` values. Always use `general-purpose` and embed the agent instructions in the prompt.

The agent prompt must include:
1. A preamble: "You are the MTS Per-Service Documentation Agent. Follow the instructions in `${CLAUDE_PLUGIN_ROOT}/agents/mts-per-service-doc-agent.md` — read that file first."
2. The project path
3. The focused discovery summary from Step S.8 (include ALL extracted data — this avoids the agent re-reading files)
4. The output file path to write
5. **Performance:** Also read the controller class, response bean class, and any mapper/assembler classes during discovery (Steps S.5-S.8) and include their key field lists in the discovery summary. Include `GATEWAY_DTO_FIELDS` from S.7d-post when available — this provides the actual Gateway DTO class field declarations that prevent the agent from guessing getter paths. This prevents the agent from needing to re-read those files.

## Step S.10 — Report

After the agent completes:
1. Confirm the file exists
2. Report to the user:
   ```
   MTS single-service documentation complete:
   - docs/mts/service-doc-<ServiceName>-<method>.md

   [Any warnings about missing source JARs or unresolved items]
   ```
3. Ask if they want to document another service.

---

## Performance Optimisation

The per-service doc agent is the main bottleneck. To minimise its tool calls and runtime:

1. **Pre-read response chain classes during discovery and embed VERBATIM field definitions.** During Steps S.5 / Phase 1, read these source files and include their **exact field declarations** (copy-pasted from Read output) in the discovery summary — NOT summarised field lists:
   - The controller class: include the method signature and return type
   - The REST response bean class: include the **complete list of field declarations** exactly as they appear in the source (e.g., `private Map<HoldingsMenuType, Integer> holdingCounters;`)
   - Any intermediate DTO classes (e.g., `HoldingCounters`, `HoldingsMenuType`): include their field declarations verbatim
   - Any mapper/assembler classes: include the relevant mapping method bodies showing exactly how fields are set
   - Gateway DTO classes from the EGS JAR (from S.7d-post): include field declarations and getter signatures for all `*Data` classes populated by `parseResponse()`/`parseArrayResponse()`
   - The service method showing exactly how many doService calls are made and with what parameters

   **CRITICAL:** The agent must produce sample request/response JSON and field mapping tables using ONLY fields that exist in the pre-embedded class definitions. Summarised or paraphrased field names cause the agent to hallucinate fields that don't exist on the actual DTOs, which breaks the downstream `/api-replacement-match` pipeline.

   This prevents the agent from needing to re-read 5-10 files while maintaining content accuracy.

2. **Embed agent instructions directly in the prompt** rather than telling the agent to read the instructions file. Copy the Required Sections template and Rules into the prompt so the agent doesn't waste a tool call reading the `.md` file.

3. **Maximise parallel tool calls.** During discovery, run as many Grep/Bash/Read calls in the same message as possible. Independent lookups (resolve SERVICE_NAME, find source JARs, trace call chain, check WireMock) should all be parallel.

4. **Use `model: <AGENT_MODEL>`** for per-service doc agents — pass the model selected by the user at the start of the run.

---

## Error Handling

- **Missing source JAR:** Mark affected entries as "Needs verification" and continue. Never block on a missing JAR.
- **Failed agent:** Report which output file is incomplete. The other files are still valid.
- **No doService calls found:** Report "No doService calls found in src/main/java/" and skip Phases 2-3. Still produce `architecture-overview.md` with available configuration data.
- **Unresolvable SERVICE_NAME constant:** Record as `"<ClassName>.SERVICE_NAME (unresolved)"` and continue.
- **No REST endpoints found:** Note in architecture overview; code journeys will start from the first caller found.
- **No WireMock test data:** Build sample request/response JSON from DTO field names and reasonable placeholder values.
- **Incomplete discovery:** If discovery agent returned `INCOMPLETE_STEPS`, include the missing step info in agent prompts and note it in the final report.
