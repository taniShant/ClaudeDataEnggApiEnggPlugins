# Mainframe Programs

## Two Transaction Identifiers

Every mainframe-touching EGS service has **two** distinct identifiers:

| Identifier | Example | Purpose | Where It Lives |
|---|---|---|---|
| **Messaging Transaction Name** | `CUS_ALL_RETRIEVE_VO` | Operational name used by `FormattingHandlerImpl` to load ROP/RIP message format files and route MQ messages to IMS | `application.properties` → `external.services.<service>.TRANSACTION_NAME` |
| **CICS Programme Code** | `TDLQCU` | Legacy IMS programme code sent inside the message to identify the target CICS program on the mainframe | `getName()` in the concrete transaction class (in EGS source JAR) |

### Messaging Transaction Name

This is the name `FormattingHandlerImpl` (in `egs_fwork`) uses at runtime to:
1. Locate the ROP/RIP files that define the binary message format (filename = this name)
2. Route the MQ message to the correct IMS transaction

It is configured in `application.properties` under the key `external.services.<service-key>.TRANSACTION_NAME`.

### CICS Programme Code

This is the value returned by `getName()` on the concrete transaction class. It ultimately extends `MainframeTransaction` (in `egs_fwork` JAR, package `com.barclays.gs.framework.gateway`), which declares `getName()` as abstract.

**The hierarchy:** `MainframeTransaction` (abstract) → `DatastreamTransaction` (abstract) → system-specific parent (e.g., `CustomerTransaction`, `UkbaTransaction`) → concrete transaction class.

**Different systems implement `getName()` differently:**

#### Customer System (via `CustomerTransaction`)

`CustomerTransaction` (in `egs_customer` JAR, package `com.barclays.gs.customer.gateway`) implements `getName()` by composing it from three abstract methods:

```
protected String getName() {
    return "T" + getSystemCode() + getVersionCode() + getProgramCode();
}
protected String getSystemCode() { return "DL"; }
protected abstract String getProgramCode();
protected abstract String getVersionCode();
```

Each concrete transaction class implements `getProgramCode()` and `getVersionCode()`. The resulting name follows the pattern `TDL` + versionCode + programCode.

**Note:** The version code can differ between JAR versions (e.g., `CustomerAllRetrieveTransaction` may return version `"Q"` in one JAR version and `"N"` in another, producing `TDLQCU` or `TDLNCU`). Always verify from the actual source JAR in the project's Gradle cache.

#### Other Systems (e.g., UKBA, Membership)

Other systems may hardcode the transaction name directly. For example, `MultiAccountEnquiryTransactionV3` (in `egs_odsmfukba` JAR) defines:
```
private final static String NAME = "TGJ3MA";
protected String getName() { return NAME; }
```

## Class Hierarchy Detail

The Transaction class hierarchy provides a layered architecture where each level adds specific behaviour:

### Hierarchy Levels

```
MainframeTransaction (egs_fwork)
  └── DatastreamTransaction (egs_fwork)
        ├── CustomerTransaction (egs_customer)
        │     ├── CustomerAllRetrieveTransaction
        │     ├── CustomerRetrieveTransaction
        │     ├── CustomerUpdateTransaction
        │     └── ... (other customer transactions)
        ├── UkbaTransaction (egs_odsmfukba)
        │     ├── MultiAccountEnquiryTransactionV3
        │     └── ... (other UKBA transactions)
        └── SaleTransaction (egs_salecommon / egs_saleenquiry)
              ├── SaleRetrieveTransaction
              └── ... (other sale transactions)
```

### Key Methods at Each Level

| Level | Class | Key Methods | Purpose |
|-------|-------|-------------|---------|
| **1** | `MainframeTransaction` | `getName()` (abstract), `buildRequest()`, `parseResponse()`, `addField()`, `getField()`, `getIntField()` | Base contract: defines how to build request messages and parse response messages |
| **2** | `DatastreamTransaction` | `buildDatastream()`, `parseDatastream()`, field accessor helpers | Adds datastream-specific binary format handling (ROP/RIP file loading) |
| **3** | `CustomerTransaction` | `getName()` (composed), `getSystemCode()`, `getProgramCode()` (abstract), `getVersionCode()` (abstract) | Implements `getName()` as `T` + systemCode + versionCode + programCode |
| **4** | Concrete (e.g., `CustomerAllRetrieveTransaction`) | `getProgramCode()`, `getVersionCode()`, constructor (WMID flag setup) | Defines actual CICS code and which DataGroups map to which WMID flags |

### Constructor Pattern (Concrete Transaction Classes)

The constructor of each concrete Transaction class is where the DataGroup→WMID mapping is defined. This is the **primary extraction target** for Phase 1 Step 1.11:

```
public CustomerAllRetrieveTransaction(CustomerRequest request) {
    // For each DataGroup or compound condition:
    if (request.isRequested(CustomerDataGroup.SOME_GROUP)) {
        addField("WMID-XXXX-PRM", "Y");
    }
    // ... repeated for each supported DataGroup
}
```

## parseResponse() Pattern

After the mainframe returns data, the Transaction's `parseResponse()` method (or its equivalent at the `DatastreamTransaction` level) reads WMOD fields from the binary response message.

### How WMOD Fields Are Read

Response fields follow the `WMOD-*` naming convention (Write MODe — output from mainframe):

```
// Simple field access
String value = getField("WMOD-CUST-NAM");

// Integer field access
int count = getIntField("WMOD-BAHO-CNT");

// Array field access using FieldIndex
for (int i = 0; i < count; i++) {
    FieldIndex idx = new FieldIndex(i);
    String sortCode = getField("WMOD-BAHO-SRT-CDE", idx);
    String accountNum = getField("WMOD-BAHO-ACC-NUM", idx);
}
```

### Status Check Pattern

Every response is first checked for errors before data extraction:

1. **Header-level error:** `getField("WMOD-HDR-RTR-ERR-CDE")` — non-zero indicates transaction failure
2. **Per-DataGroup status:** `getField("WMOD-XXXX-PRM")` — each DataGroup has a status field in the response confirming whether that segment was successfully retrieved
3. **Too-many-rows indicators:** `getField("WMOD-XXXX-TMR")` — signals truncated data for array-type DataGroups

### FieldIndex for Array Data

DataGroups that return multiple rows (e.g., `BANK_ACCOUNT_HOLDING` returns multiple accounts) use `FieldIndex` to iterate:

- The count field (`WMOD-XXXX-CNT`) indicates how many rows were returned
- Each row's fields are accessed by passing a `FieldIndex(i)` to `getField()`
- The maximum number of rows is defined in the RIP file

## WMOD Field Conventions

### Naming Pattern

WMOD field names follow the pattern: `WMOD-[entity]-[field]-[type]`

| Segment | Meaning | Examples |
|---------|---------|----------|
| `WMOD-` | Fixed prefix — Write MODe (output from mainframe) | All response fields |
| `[entity]` | 3-4 char entity code matching the TDL table suffix | `CUST` (customer), `BAHO` (bank account holding), `INCM` (income) |
| `[field]` | Field name abbreviation | `NAM` (name), `SRT-CDE` (sort code), `ACC-NUM` (account number) |
| `[type]` | Optional type suffix | `CNT` (count), `PRM` (parameter/status), `TMR` (too many rows) |

### Common Field Types

| Suffix | Purpose | Example |
|--------|---------|---------|
| `-PRM` | Status parameter (Y/N — was this DataGroup successfully returned?) | `WMOD-BAHO-PRM` |
| `-CNT` | Count of array items returned | `WMOD-BAHO-CNT` |
| `-TMR` | Too-many-rows flag (data was truncated) | `WMOD-BAHO-TMR` |
| `-CDE` | Code value | `WMOD-CUST-TYP-CDE` |
| `-NAM` | Name field | `WMOD-CUST-NAM` |
| `-NUM` | Number field | `WMOD-BAHO-ACC-NUM` |
| `-DTE` | Date field | `WMOD-CUEM-STR-DTE` |
| `-AMT` | Amount field | `WMOD-INCM-AMT` |
| `-IND` | Indicator (flag) field | `WMOD-CUST-DCD-IND` |

### Array Access Pattern

```
// Read count
int holdingCount = getIntField("WMOD-BAHO-CNT");

// Iterate with FieldIndex
for (int i = 0; i < holdingCount; i++) {
    FieldIndex fi = new FieldIndex(i);
    String sortCode  = getField("WMOD-BAHO-SRT-CDE", fi);
    String accountNo = getField("WMOD-BAHO-ACC-NUM", fi);
    String status    = getField("WMOD-BAHO-STS-CDE", fi);
}
```

> **For Phase 1 Step 1.13:** When extracting WMOD fields from Transaction source, focus on data-carrying fields (those used to populate response beans). Skip infrastructure fields (`-PRM`, `-CNT`, `-TMR`) in the inventory — they follow standard patterns and don't need per-service documentation.

## ROP/RIP Files

ROP (Request Output Parameters) and RIP (Request Input Parameters) files define the **binary message format** for mainframe transactions. They live inside EGS JARs in the `riprop/` directory.

### Location and naming

- **Path inside JAR:** `riprop/<MESSAGING_TRANSACTION_NAME>.ROP` and `riprop/<MESSAGING_TRANSACTION_NAME>.RIP`
- **Example:** `egs_customer-X.Y.Z.jar` → `riprop/CUS_ALL_RETRIEVE_VO.ROP`
- The filename matches the **Messaging Transaction Name** (not the CICS programme code)

### Content structure

- **ROP file (output — request to mainframe):** Contains `WMID-*-PRM` field definitions — these are the input parameters sent to the mainframe. Each `WMID-*-PRM` field maps to a DataGroup that targets a specific TDL table. This is the **definitive source** for which TDL tables a transaction accesses.
- **RIP file (input — response from mainframe):** Contains `WMOD-*` field definitions — these are the output fields returned from the mainframe.

### Why ROP files matter

The `WMID-*-PRM` parameters in the ROP file are more reliable than inferring TDL table access from Java source code alone. They represent the actual binary message contract with the mainframe and list every DataGroup the transaction can request.

## How the Agent Resolves Each Identifier

### Messaging Transaction Name
Grep for `TRANSACTION_NAME` in `application.properties` matching the service name:
```bash
grep "TRANSACTION_NAME" config/application.properties
```
This is typically already read during Phase 1 config discovery.

### CICS Programme Code
Read `getName()` (and `getProgramCode()` / `getVersionCode()` for Customer system) from the transaction class in the source JAR:
```bash
# Preferred: from source JAR
unzip -p <sources-jar> "**/*Transaction.java" 2>/dev/null | grep -A5 "getName\|getProgramCode\|getVersionCode"

# Fallback: from compiled JAR
javap -c -p <compiled-jar-entry> | grep -A5 "getName"
```

### ROP/RIP WMID Parameters
Extract the ROP file from the EGS JAR and grep for WMID parameters:
```bash
unzip -p <egs-jar> "riprop/<TRANSACTION_NAME>.ROP" 2>/dev/null | grep "WMID-.*-PRM"
```
Use the results to confirm or supplement DataGroup → TDL mappings found in source code.