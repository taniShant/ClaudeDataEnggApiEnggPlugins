# Discovery Steps 1.10-1.13: Mainframe Data Extraction

These steps are referenced from `mts-discovery-agent.md` and contain the full instructions for Transaction class extraction, DataGroup-WMID mapping, Command class extraction, and WMOD field extraction. Steps use source JARs as primary and compiled JAR fallback depending on `COMPILED_JAR_FALLBACK` level.

---

### Step 1.10 — Extract Transaction classes from EGS JARs

**Primary (source JARs):** For each EGS source JAR (`jar_type: source`), use Python to list Transaction classes and extract identity methods (`getProgramCode`, `getVersionCode`, `getName`, `class.*extends`).

**Compiled JAR fallback** (for artifacts with `jar_type: compiled` and `COMPILED_JAR_FALLBACK != NONE`):

Apply the 3-tier extraction from `compiled_jar_extraction.md`:

- **Tier 1 (constant pool):** Use `scan_compiled_jar(jar_path, class_filter='Transaction')` to extract class hierarchy (`super_class`), all string constants, and method/field refs. Identify program/version code candidates using the short-string heuristic.
- **Tier 3 (javap):** If `JAVAP_PATH != NOT_AVAILABLE`, run `javap -c -p` on each Transaction `.class` and use `parse_identity_methods()` to extract exact `getProgramCode()` and `getVersionCode()` return values.

```bash
<PYTHON_CMD> -c "
import zipfile, struct, os, glob
home = os.environ.get('USERPROFILE', os.path.expanduser('~'))
BASE = os.path.join(home, '.gradle', 'caches', 'modules-2', 'files-2.1', '')
# [Insert constant pool parser from compiled_jar_extraction.md]
# For each compiled EGS JAR, scan for Transaction classes
jar = '<compiled-egs-jar>'
results = scan_compiled_jar(jar, class_filter='Transaction')
for r in results:
    print(f\"CLASS: {r['class_name']}\")
    print(f\"SUPER: {r['super_class']}\")
    wmids = [s for s in r['strings'] if 'WMID-' in s and '-PRM' in s]
    print(f\"WMID_STRINGS: {wmids}\")
    codes = [s for s in r['strings'] if len(s) <= 3 and s.isalpha() and s.isupper()]
    print(f\"CODE_CANDIDATES: {codes}\")
"
```

Build a Transaction Registry with: Class, JAR path, JAR type (`source`/`compiled`), Program Code, Version Code, Composed Name, Service Description, class hierarchy. For compiled JARs, note the extraction tier used and confidence level.

### Step 1.11 — Extract DataGroup-to-WMID mappings

**Primary (source JARs):** For each Transaction class from Step 1.10 (`jar_type: source`), extract `addField("WMID.*PRM"` calls with surrounding context. Capture each `request.isRequested(CustomerDataGroup.XXX)` to `addField("WMID-YYY-PRM"` pair. Pay attention to compound OR conditions.

**Compiled JAR fallback** (for artifacts with `jar_type: compiled` and `COMPILED_JAR_FALLBACK != NONE`):

Apply the 3-tier extraction from `compiled_jar_extraction.md`:

- **Tier 1 (constant pool):** Already extracted in Step 1.10. The WMID-\*-PRM strings from the constant pool give the complete list of WMID parameters used by each Transaction class. However, Tier 1 **cannot** determine which DataGroup condition gates each WMID.
- **Tier 2 (ROP/RIP):** Use `extract_rop_rip(jar_path)` to parse `riprop/*.ROP` files from the compiled EGS JAR. ROP entries provide the **definitive** WMID parameter list. Cross-validate against Tier 1 strings.

```bash
<PYTHON_CMD> -c "
import zipfile, re
jar = '<compiled-egs-jar>'
# [Insert ROP/RIP parser from compiled_jar_extraction.md]
result = extract_rop_rip(jar)
print(f'ROP files: {result[\"rop_files\"]}')
print(f'WMID params: {result[\"rop_entries\"]}')
"
```

- **Tier 3 (javap):** If `JAVAP_PATH != NOT_AVAILABLE`, run `javap -c -p` on each Transaction `.class` and use `parse_javap_constructor()` to extract exact DataGroup→WMID conditional mappings from bytecode patterns (`getstatic CustomerDataGroup.<ENUM>` → `ldc "WMID-*-PRM"` → `invokevirtual addField`).

```bash
<PYTHON_CMD> -c "
import zipfile, subprocess, tempfile, os, re
jar = '<compiled-egs-jar>'
javap = '<JAVAP_PATH>'
# [Insert javap constructor parser from compiled_jar_extraction.md]
# Extract Transaction .class, run javap, parse constructor
"
```

**If javap is not available:** Record all WMID parameters from Tier 1/Tier 2 without DataGroup attribution. Note in output: `"DataGroup-to-WMID conditional mapping not available (no javap). WMID list is complete."` Set confidence to `partial-from-bytecode`.

Cross-validate Tier 1+2+3 results against each other and against the WMID-TDL Quick Reference in `mts-discovery-agent.md` to resolve TDL table names from WMID parameters.

### Step 1.12 — Extract Command class gateway calls

**Primary (source JARs):** For each EBS source JAR (`jar_type: source`), use Python to extract Command classes. Look for:
- `new CustomerRequest(new CustomerDataGroup[] { ... })` — which DataGroups the Command requests
- `gateway.findByPrimaryKey(...)` — which gateway method is called
- `gateway.findPfsDataByCustomerId(...)` — PFS-specific calls

**Compiled JAR fallback** (for artifacts with `jar_type: compiled` and `COMPILED_JAR_FALLBACK != NONE`):

Apply Tier 1 from `compiled_jar_extraction.md`:

- **Tier 1 (constant pool):** Use `scan_compiled_jar(jar_path, class_filter='Command')` to extract:
  - `field_refs` containing `CustomerDataGroup.<ENUM>` — identifies which DataGroups the Command requests
  - `method_refs` containing `gateway.findByPrimaryKey` or `gateway.findPfsDataByCustomerId` — identifies gateway method calls

```bash
<PYTHON_CMD> -c "
import zipfile, struct, os
jar = '<compiled-ebs-jar>'
# [Insert constant pool parser from compiled_jar_extraction.md]
results = scan_compiled_jar(jar, class_filter='Command')
for r in results:
    print(f\"COMMAND: {r['class_name']}\")
    dg_refs = [f for f in r['field_refs'] if 'CustomerDataGroup' in f]
    gw_refs = [m for m in r['method_refs'] if 'Gateway' in m or 'findByPrimaryKey' in m]
    print(f\"DATAGROUPS: {dg_refs}\")
    print(f\"GATEWAY_CALLS: {gw_refs}\")
"
```

Tier 1 provides exact DataGroup enum references and gateway method references from the constant pool — no heuristics needed for Command class extraction.

### Step 1.13 — Extract WMOD response field inventory

**Primary (source JARs):** For each Transaction class (`jar_type: source`), extract WMOD response fields (`getField`/`getIntField` calls containing `WMOD`).

**Compiled JAR fallback** (for artifacts with `jar_type: compiled` and `COMPILED_JAR_FALLBACK != NONE`):

Apply the 3-tier extraction from `compiled_jar_extraction.md`:

- **Tier 1 (constant pool):** Already extracted in Step 1.10. Filter strings matching `WMOD-*` from the constant pool — these are all WMOD field names referenced by the Transaction class.
- **Tier 2 (RIP):** Use `extract_rop_rip(jar_path)` to parse `riprop/*.RIP` files. RIP entries provide the **definitive** WMOD field list **with data types and lengths**. This is more detailed than either source JAR or Tier 1 extraction.

```bash
<PYTHON_CMD> -c "
import zipfile, re
jar = '<compiled-egs-jar>'
# [Insert ROP/RIP parser from compiled_jar_extraction.md]
result = extract_rop_rip(jar)
print(f'RIP files: {result[\"rip_files\"]}')
for entry in result['rip_entries']:
    print(f\"  {entry['field']}  {entry['type']}({entry['length']})\")
"
```

When both Tier 1 and Tier 2 are available, prefer Tier 2 (RIP) as it includes data types. Cross-validate: every WMOD field in Tier 1 should appear in Tier 2.

Summarise by DataGroup section: count of fields + key data-carrying field names. Skip infrastructure fields (`-PRM`, `-CNT`, `-TMR`).

---

### Step 1.15 — Build doService-to-Command Correlation Map

For each doService call (and each direct-gateway call) from Step 1.1, build a pre-correlated chain entry:

1. **SERVICE_NAME → EBS artifact:** Match the SERVICE_NAME (resolved in Step 1.2) to an EBS artifact using the import package (e.g., `com.barclays.ebs.custpersonal.*` → `ebs_custpersonal`). Refer to the SERVICE_NAME-to-EBS-Artifact mapping in `ebs_egs_conventions.md`.
2. **operationCode → Command class:** Convert operationCode to PascalCase + "Command" (e.g., `retrievePersonalCustomerFullDetails` → `RetrievePersonalCustomerFullDetailsCommand`). Confirm from Step 1.12 Command class list.
3. **Command → Gateway.method():** From the Command class extracted in Step 1.12, identify the gateway method called (e.g., `gateway.findByPrimaryKey(...)`).
4. **Gateway → Transaction class:** From the gateway method, match to the Transaction class extracted in Step 1.10 (e.g., `CustomerGateway.findByPrimaryKey` → `QueryCustomerTransaction`).
5. **Transaction → DataGroups, WMID params, TDL tables:** From Step 1.11, extract the DataGroups requested by this Command, their WMID parameters, and resolved TDL table names.

Output as `## SECTION: DOSERVICE_CORRELATION_MAP` with one entry per (ServiceName, operationCode) pair. Each entry contains:
- Service Name / Operation Code / EBS Artifact / Command Class (FQN)
- Gateway Class / Gateway Method / Transaction Class / CICS Code (from Transaction's getProgramCode)
- DataGroups Requested / WMID Fields / TDL Tables
- ROP/RIP Available / Confidence: `verified-from-source` | `verified-from-bytecode` | `verified-from-rop-rip` | `partial-from-bytecode` | `inferred-from-convention`

---

### Step 1.16 — Application Layer Verification

This step verifies whether the mainframe data documented in Steps 1.10-1.15 is actually consumed by the application layer. It catches cases where the EGS Transaction supports a DataGroup/field but the application's wrappers, converters, or mappers do not use it.

**Why this step exists:** EBS/EGS JARs document what the mainframe CAN return. But the application may: (a) disable DataGroups in the wrapper, (b) comment out field setters in converters, (c) never populate REST response fields. Without this step, the service doc will overclaim field coverage, leading to false-positive gaps in API compatibility analyses.

**1.16a — Wrapper DataGroup Flags:**

For each ServiceWrapper class identified in call chains (Step 1.8):

```
Grep pattern: "set\w+Required\s*\(" in <PROJECT_PATH>/src/main/java/**/wrapper/*Wrapper.java
```

For each match, record:
- Wrapper class name
- Request-building method name
- Flag name (e.g., `setUkbaJointHoldingsRequired`)
- Value (`true` or `false`)
- Affected DataGroup / TDL table

If a flag is `false`, all WMOD fields from the corresponding TDL table should be marked as `DISABLED` in the output.

**1.16b — Converter Commented-Out Fields:**

For ODS-to-EDO converters in the project:

```
Grep pattern: "//\s*(edo|target|dest)\.(set\w+)" in <PROJECT_PATH>/src/main/java/**/converters/*.java
                                                 and <PROJECT_PATH>/src/main/java/**/ods/converters/*.java
```

For each commented-out setter:
- Converter class name and line number
- Field name (from setter name, e.g., `setJointHolderDetails` → `jointHolderDetails`)
- Mark as `COMMENTED_OUT`

**1.16c — Example Response Fixture Nullity Check:**

Locate example response data:

```
Glob: <PROJECT_PATH>/src/main/java/**/constants/*ExampleControllerResponses*.java
Glob: <PROJECT_PATH>/src/test/resources/__files/<service-endpoint-path>/*.json
```

For each REST response bean field (from the response DTO identified in the call chain), search for the field name in the example responses. Record:
- Field name
- Source file
- Value found (`null`, `[]`, populated value, or not found)
- Status: `POPULATED` | `ALWAYS_NULL` | `ALWAYS_EMPTY` | `NOT_FOUND`

Fields that are `ALWAYS_NULL` or `ALWAYS_EMPTY` across ALL fixtures indicate the field is structurally present but never populated — downstream API compatibility analyses should treat it as NOT_NEEDED.

**1.16d — Enrichment Method Existence:**

For each enrichment method documented in Command chains (Step 1.12 — e.g., `populateBondProductDetails`, `populateMiscellaneousProductDetails`, `populateDebitCardHoldingsDetails`):

```
Grep pattern: "methodName" in <PROJECT_PATH>/src/main/java/**/*.java
```

Record:
- Method name
- Found in EBS JAR? (from Step 1.12 extraction)
- Found in application codebase? (from this grep)
- If found in application, does it populate any REST response bean field?
- Status: `EXISTS` | `EBS_ONLY` | `NOT_FOUND`

Methods that are `EBS_ONLY` mean the enrichment logic exists in the compiled EBS JAR but is not invoked or consumed by the application's service layer.

**Output:** Record all findings in `## SECTION: APPLICATION_LAYER_VERIFICATION`.

**Confidence assignment for correlation map entries** (see `compiled_jar_extraction.md` for full rules):
- `verified-from-source` — all data extracted from source JARs
- `verified-from-bytecode` — data extracted from compiled JAR with constant pool + javap confirmation
- `verified-from-rop-rip` — WMID/WMOD data cross-validated against ROP/RIP files
- `partial-from-bytecode` — data from constant pool only (no javap); DataGroup-to-WMID conditional mappings unavailable
- `inferred-from-convention` — derived from naming patterns only

For direct-gateway calls (Pattern 6), populate Gateway Class and Method directly from the call site. Transaction/Command fields are N/A.
