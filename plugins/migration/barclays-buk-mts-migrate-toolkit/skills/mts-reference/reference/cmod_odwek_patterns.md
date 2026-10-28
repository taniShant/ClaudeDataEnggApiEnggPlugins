# CMOD/ODWEK Patterns

CMOD (Content Manager OnDemand) integration via ODWEK (OnDemand Web Enablement Kit) HTTP POST. These services retrieve archived documents (statements, correspondence, summaries) from IBM CMOD.

**Note:** CMOD/ODWEK services are NOT present in fullserve-buk. They are found in other BUK repos (e.g., correspondence, statements repositories). This reference is included for completeness of the transport classification system.

---

## Detection

- Import of `com.barclays.gs.cmod.*` classes
- ODWEK server configuration properties (`postHost`, `postPort`, `postPath`)
- EAO classes extending CMOD base classes

---

## EAO Classes

| EAO Class | Purpose |
|-----------|---------|
| `CmodEao` | Base CMOD access class |
| `CmodGenericEao` | Generic CMOD document retrieval |
| `CustomerCorrespondenceEao` | Customer correspondence documents |
| `SharedServicesEao` | Shared services documents |
| `AnnualSummariesEao` | Annual statement summaries |
| `RegularPaymentsEao` | Regular payment documents |

---

## ODWEK Paths

| Path | Purpose |
|------|---------|
| `/CC-ODWEK/cc_content_response.do` | Customer Correspondence content retrieval |
| `/RP-ODWEK-WAR/rp_content_response.do` | Regular Payments content retrieval |

---

## Call Flow

```
ServiceImpl.method()
  -> CmodEao.retrieveDocument(criteria)
    -> HTTP POST to ODWEK server
      -> /CC-ODWEK/cc_content_response.do (or /RP-ODWEK-WAR/...)
        -> IBM CMOD Server
          -> Archived Document Store
```

---

## Configuration

- **ODWEK server:** `cmod.postHost`, `cmod.postPort`, `cmod.postPath` in properties
- **Document types:** Configured per EAO -- statements, correspondence, summaries, regular payments
- **Search criteria:** Customer ID, date range, document type, account number

---

## Extraction Steps for Discovery Agent

1. Grep for `com.barclays.gs.cmod` imports in `src/main/java/`
2. Identify CMOD EAO classes used
3. Grep properties for `cmod.` or `odwek` configuration keys
4. Extract ODWEK paths from configuration or hardcoded constants
5. Identify document types handled by each EAO

---

## Replacement API Target

**API match hint:** Search Confluence for CMOD/ODWEK replacement API pages. Keywords to search:
- "CMOD replacement API"
- "ODWEK migration"
- "Document retrieval API"
- "Content Manager OnDemand API"

No known replacement API URL exists in the codebase -- Confluence search is required to identify the target API.
