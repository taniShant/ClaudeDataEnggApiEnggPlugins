# Hybrid Service Patterns

Multiple non-MQ integration patterns that use EBS/EGS JARs but access backends via SOAP, JDBC, REST, or dual-path routing.

---

## Pattern: `tcv-hybrid`

### Detection (fullserve-buk)

- `LifecycleService.SERVICE_NAME` in doService calls
- `TCV_API_ENABLED` feature flag check
- Dual-path branching: legacy MQ path vs new REST path

### Detection (scp-eps-customerdetails)

- `ConnectorGateway` classes with `SERVICE_NAME` pattern (e.g., `AccountManagementConnectorGateway.SERVICE_NAME`)
- TCVM endpoint configuration: `tcv-sit.bem.barclays.intranet:8840/tcvm`
- Data model: `uk.co.barclays.www.rbb.tcvm.*` packages
- Feature flags: `INSTANT_LENDING_APP`, `SIL`

### ConnectorGateway Classes (customerdetails)

| Gateway | Purpose |
|---------|---------|
| `AccountManagementConnectorGateway` | Account details via TCVM |
| `CustomerContactsConnectorGateway` | Contact/address details |
| `CustomerInformationServiceConnectorGateway` | Customer retrieval |
| `PBAConnectorGateway` | PIN validation |

### TCVM Data Model (customerdetails)

Subpackages under `uk.co.barclays.www.rbb.tcvm.*`:
- `SCVT` -- Single Customer View Types
- `Common` -- Shared types
- `CustomerContacts` -- Contact/address types
- `CustomerInformation` -- Customer data types
- `PBA` -- PIN Block Authentication types
- `RefData` -- Reference data types

### Dual-Path Architecture

```
ServiceImpl.method(request)
  -> if (featureFlag.isEnabled("TCV_API_ENABLED"))
    -> REST path: serviceManager.doService(CONNECTOR, RestApiUtils.EXECUTE_API, request)
      -> REST API call (already migrated)
  -> else
    -> Legacy path: serviceDelegate.doService(SERVICE_NAME, "method", request)
      -> EBS/EGS -> MQ -> mainframe
```

Example from customerdetails `BankDetailsServiceImpl.doBankWizardCheck()`:
```
if (getInstantLendingFlag())
  -> REST: serviceManager.doService(SEARCH_BANK_DETAILS, REST_SERVICE_EXECUTE, ...)
else
  -> SOAP: CommonServiceManagementStubConnector.SERVICE_NAME
```

### Status

Already partially migrated -- REST path exists alongside legacy path. Migration involves:
1. Verifying REST path feature parity
2. Enabling feature flag for all environments
3. Removing legacy path code

---

## Pattern: `tcv-gateway` (customerdetails-only)

Variant of tcv-hybrid where the ConnectorGateway routes directly to TCVM without a feature flag.

### Detection

- `ConnectorGateway.SERVICE_NAME` pattern in doService calls
- No feature flag branching
- TCVM endpoint in configuration

---

## Pattern: `scv`

### Detection

- Import of `com.barclays.scv.*` classes
- `SingleCustomerView` endpoint reference
- SCV-specific JARs in dependencies
- `scv_enabled` feature flag

### Implementation

- Class: `com.barclays.scv.common.service.CustomerHoldingsServiceImpl`
- Endpoint: `https://adp12.rfs.barclays.co.uk:443/scvbcard-jn/cardservices-ws/services/SingleCustomerView`
- Data model: `uk.co.barclays.www.grb.scvt.internal.*` (`PPResponseType`, `ProductProcessorResponseType`)

### Call Flow

```
ServiceImpl.method(request)
  -> if (scv_enabled)
    -> SCV SOAP Client
      -> SOAP/HTTP POST
        -> SingleCustomerView endpoint
          -> Card-specific data (card account details, card thumbnails, service availability)
```

### Data Scope

SCV is used specifically for card-related data:
- Card account details
- Card thumbnails
- Service availability flags

### Replacement API Target

ODS/domain APIs for card data. Search Confluence for card-specific ODS APIs.

---

## Pattern: `oracle-db-direct`

### Detection

- `CommonUtilityGateway` class usage
- `ReferenceData.populateData()` calls
- JDBC datasource to Oracle reference database (`MCAFS_USER`)
- No EGS ODS MF JAR involvement

### Current State (fullserve-buk)

- **Central service:** `StaticDataServiceImpl.java`
- **Purpose:** Product codes, coded values, IDV levels, MOPTRE menu option configurations
- **Database:** Oracle reference database via JDBC (`MCAFS_USER` datasource)
- **Access pattern:** `ReferenceData.populateData()` with SQL queries

### Reference Tables

| Table | Content |
|-------|---------|
| `XREF` | Cross-reference lookup (rule class -> code -> description) |
| `MRDT` | Master reference data table |
| `PROJ_SWTCH` | Project switches / feature flags |
| `MOPTRE` | Menu option tree configuration |
| `ti_tukprod` | Product definitions |

### Call Flow

```
StaticDataServiceImpl.method()
  -> CommonUtilityGateway.method() OR ReferenceData.populateData()
    -> JDBC Connection (MCAFS_USER datasource)
      -> Oracle Reference Database
        -> XREF / MRDT / PROJ_SWTCH / MOPTRE / ti_tukprod tables
```

### Existing Partial Migration

`ODSReferenceService.java` already calls ODS via REST for some reference data:
- Endpoint: `/referenceData/xref/{ruleClass}`
- This covers a subset of XREF lookups

### Replacement API Target

**Static Data Hub API**
- URL: `https://sdh-ui-22845.pr1.apaas4.barclays.intranet/sdh/dashboard`
- No existing Static Data Hub references in the fullserve-buk codebase -- this would be a new integration
- **API match hint:** Search Confluence for "Static Data Hub" API documentation when matching oracle-db-direct services

---

## Pattern: `db2-reference`

### Detection

- `ProductGateway.findByPrimaryKey()` calls
- JDBC datasource to DB2
- Product-specific gateway without EGS ODS MF Transaction class

### Call Flow

```
ServiceImpl.method()
  -> ProductGateway.findByPrimaryKey(productId)
    -> JDBC Connection
      -> DB2 Database
        -> Product tables (ti_tukprod etc.)
```

### Replacement API Target

**Static Data Hub API** (same as oracle-db-direct)
- URL: `https://sdh-ui-22845.pr1.apaas4.barclays.intranet/sdh/dashboard`
- **API match hint:** Search Confluence for "Static Data Hub" API documentation when matching db2-reference services
