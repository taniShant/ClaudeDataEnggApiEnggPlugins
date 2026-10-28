# MIS Source Extraction Reference

When `MIS_REPO_PATH` is set (from Step 0.2c), extract TDL tables, WMID/WMOD fields, and
DataGroup chains directly from Java source files instead of compiled JAR fallback.

Confidence tag for all data extracted this way: **`verified-from-mis-source`**

---

## 1. Locate the right source files

The MIS repo contains many classes. Target these types for the service being documented:

| What you need | File name pattern | Example |
|---------------|------------------|---------|
| TDL tables | `*Transaction.java` | `CustomerAllRetrieveTransaction.java` |
| WMID request fields | `*Transaction.java` (constructor / `buildRequest()`) | `addField("WMID-CUS-IDR", ...)` |
| WMOD response fields | `*Transaction.java` (`parseResponse()`) | `getField("WMOD-BAHO-SRT-CDE")` |
| DataGroup chain | `*DataGroup.java` or `*Command.java` | `CustomerDataGroup.java` |
| Transaction name | `*Transaction.java` (class constant or `getName()`) | `"CUS_ALL_RETRIEVE_VO"` |
| CICS programme code | `*Transaction.java` (`getProgramCode()`) | `"TDLQCU"` |

### Find the Transaction class for a service

```bash
# Find Transaction class by name (fastest — use when class name is known)
find <MIS_REPO_PATH>/src/main/java/ -name "<PRIMARY_TRANSACTION_CLASS>.java" 2>/dev/null

# Or search by known CICS code (portable grep)
grep -r --include="*.java" -rl "TDLQCU\|TDLCCU" <MIS_REPO_PATH>/src/main/java/ 2>/dev/null

# Or search by DataGroup name
grep -r --include="*.java" -rl "CustomerDataGroup\|LimitsDataGroup\|BusinessUnitEmployeeDataGroup" \
    <MIS_REPO_PATH>/src/main/java/ 2>/dev/null
```

---

## 2. Extract TDL table names

TDL table names appear as:
- CICS programme codes (e.g. `"TDLQCU"`, `"TDLCCU"`, `"TCRAREMZ"`)
- String constants in `getProgramCode()` or `getName()` methods
- Javadoc comments referencing `TDL[A-Z]{4,}` or `TCR[A-Z]{4,}`

```bash
# Extract all TDL-pattern strings from Transaction files (portable — works on macOS bash)
grep -r --include="*.java" -oE '"TDL[A-Z0-9]{3,}"' <MIS_REPO_PATH>/src/main/java/ 2>/dev/null | sort -u
grep -r --include="*.java" -oE '"TCR[A-Z0-9]{3,}"' <MIS_REPO_PATH>/src/main/java/ 2>/dev/null | sort -u

# Broader search including Javadoc and comments
grep -r --include="*.java" -ohE '\bTDL[A-Z0-9]{3,}\b' <MIS_REPO_PATH>/src/main/java/ 2>/dev/null | sort -u
grep -r --include="*.java" -ohE '\bTCR[A-Z0-9]{3,}\b' <MIS_REPO_PATH>/src/main/java/ 2>/dev/null | sort -u
```

Focus results on the specific Transaction class file for the service being documented.

---

## 3. Extract WMID request fields

WMID fields appear in `buildRequest()`, constructors, or `addField()` calls:

```bash
grep -oE '"WMID-[A-Z0-9-]+"' <MIS_REPO_PATH>/src/main/java/<TransactionClass>.java 2>/dev/null | sort -u
```

---

## 4. Extract WMOD response fields

WMOD fields appear in `parseResponse()` or `getField()` calls:

```bash
grep -oE '"WMOD-[A-Z0-9-]+"' <MIS_REPO_PATH>/src/main/java/<TransactionClass>.java 2>/dev/null | sort -u
```

---

## 5. Extract DataGroup chain

DataGroup enums appear in Command classes or DataGroup Java files:

```bash
# Find DataGroup enum file and extract enum values
find <MIS_REPO_PATH>/src/main/java/ -name "*DataGroup*.java" 2>/dev/null | \
    xargs grep -oE '[A-Z_]{3,}[[:space:]]*(,|;|\))' 2>/dev/null

# Or find DataGroup usage in Command classes (portable)
grep -r --include="*.java" -oE 'DataGroup\.\w+' <MIS_REPO_PATH>/src/main/java/ 2>/dev/null | sort -u
```

---

## 6. Useful bash helpers (use via Bash tool)

```bash
SRC="<MIS_REPO_PATH>/src/main/java"

# All Transaction class names
find "$SRC" -name "*Transaction*.java" | sed 's|.*/||'

# TDL tables in a specific file
grep -ohE '\bTDL[A-Z0-9]{3,}\b' "$SRC/path/to/File.java" | sort -u

# WMID fields in a specific file  
grep -oE '"WMID-[A-Z0-9-]+"' "$SRC/path/to/File.java" | sort -u

# WMOD fields in a specific file
grep -oE '"WMOD-[A-Z0-9-]+"' "$SRC/path/to/File.java" | sort -u

# Full DataGroup list from DataGroup enum file
grep -E '^\s+[A-Z_]+' "$SRC/path/to/XxxDataGroup.java"
```

---

## 7. Confidence and fallback

- Data extracted from MIS source: tag `verified-from-mis-source`
- If MIS source file not found for the specific Transaction class: fall through to compiled JAR extraction
- If MIS repo clone failed: fall through to compiled JAR extraction
- Do NOT mix confidence levels in the same field — use the highest applicable

## 8. Known repo → service mapping

| MIS repo | Services whose Transaction classes live here |
|----------|---------------------------------------------|
| `gateways/egs-odsmf-customer` | CustomerUpdateService, ScreeningEnquiryService, BusinessUnitService, CustomerEnquiryService (limits), CustomerHoldingsService, PersonalCustomerService, NonPersonalCustomerService, CustomerLocateService, CustomerGateway (EGS), ProductGateway (EGS) |
| `gateways/egs-odsmf-member` | MembershipEnquiryService, MembershipProcessEnquiry |
| `gateways/egs-odsmf-ukba` | UKBA account-level services |
| `services/customer-personal` | PersonalCustomerService (EBS command layer) |
| `services/customer-locate` | CustomerLocateService (EBS command layer) |
| `services/membership-enquiry` | MembershipEnquiryService (EBS command layer) |
| `services/membership-process-enquiry` | MembershipProcessEnquiry (EBS command layer) |
| `services/customerprocess-enquiry` | CustomerHoldingsService (EBS command layer) |
