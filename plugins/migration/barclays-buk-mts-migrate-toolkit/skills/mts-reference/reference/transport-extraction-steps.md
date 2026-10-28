# Non-Mainframe Transport Extraction Steps

These sub-steps are referenced from `single_service_mode.md` Step S.7 for non-mainframe transports. Run the sub-step matching the classified transport type.

### S.7f — SOAP stub extraction (transport: `soap-stub`)

- Resolve StubConnector `SERVICE_NAME` constant
- Grep `services.properties` for endpoint URL
- Extract SOAP operations from doService method arguments
- Identify request/response types from call site parameters

### S.7g — Database direct extraction (transport: `oracle-db-direct` or `db2-reference`)

- Identify gateway class (`CommonUtilityGateway`, `ProductGateway`)
- Grep for table name references (XREF, MRDT, PROJ_SWTCH, ti_tukprod, MOPTRE)
- Identify JNDI datasource from `DataSourceConfig.java` or properties
- Note database type (Oracle vs DB2)

### S.7h — CMOD/ODWEK extraction (transport: `cmod-odwek`)

- Identify CMOD EAO classes
- Extract ODWEK server config from properties
- Identify ODWEK paths and document types

### S.7i — TCV hybrid extraction (transport: `tcv-hybrid`)

- Identify feature flag name (`TCV_API_ENABLED`, etc.)
- Extract both code paths: REST path and legacy path
- For legacy path, apply the appropriate sub-step (S.7a-e for MQ, S.7f for SOAP)
- Note ConnectorGateway classes and TCVM data model if applicable

### S.7j — SOAP web service extraction (transport: `soap-webservice`)

- Identify EGS gateway class and method (e.g., `MortgagesGateway.retrieveAccountDetails()`)
- Extract the `*ProxyServiceWrapper` or `*ServiceAssembler` class from EGS source JAR
- From the proxy/assembler, extract: web service ID (e.g., `X61563`), SOAP endpoint URL, WSDL namespace
- Identify the backend system (ILP, Hogan, etc.) from class names and config
- Note: soap-webservice services have NO CICS code, NO DataGroup activation, NO TDL tables
- Extract request/response field mappings from the gateway method parameters and return types
- Check for routing conditions (e.g., `belongsToILP()`) that gate when this path is taken vs an alternative

### S.7k — SCV extraction (transport: `scv`)

- Identify SCV endpoint URL
- Extract `com.barclays.scv.*` model classes
- Note `scv_enabled` flag
- Identify card-specific data accessed

### S.7l — ITSU/Oracle extraction (transport: `itsu-oracle`)

- Identify the EBS JAR (e.g., `ebs_execctxemployee`)
- Extract the EBS source JAR and find the data access class (e.g., `ServiceAccessDetailsHelper.java`, `*Helper.java`, `*Dao.java`)
- Check if it calls Oracle/JDBC methods directly (`getConnection`, `PreparedStatement`, `ResultSet`, `DataSource`)
- If yes, extract: Oracle table names (from SQL strings or table name constants), JNDI datasource name
- Document under `**Oracle Tables (ITSU):**` in Quick Reference
- If the class delegates to ITSU framework classes (not direct JDBC), note: "Data accessed via ITSU framework — table names not directly extractable from EBS source. Check ITSU configuration for table mappings."
- Note: ITSU services do NOT use CICS, MQ, DataGroups, or TDL tables

### S.7m — ALS backend extraction (transport: `als-backend`)

- Identify the EBS JAR (e.g., `ebs_loansenquiry`) and EGS JAR (e.g., `egs_loans`) — both located in S.4
- Read the ALS Transaction class from the EGS source JAR (e.g., `LoansBalanceEnquiryTransaction.java`). ALS Transaction classes extend `LoansTransaction` → `DatastreamTransaction`.

**Extract ALS program name:**
- Find `appendLoansMessageDetails("<PROGRAM>", ...)` in the Transaction constructor — first argument is the ALS CICS program name (e.g., `AMPCRTM1`)

**Extract ALS input DAG fields:**
- Grep the Transaction constructor for `addField("AM*")` calls. ALS uses DAG-based field layout with prefix `AMWKWI00-*` for input working storage.
- Record each field: `addField("AMWKWI00-RT-ACCT-NUM", value)` → input field `RT-ACCT-NUM` from DAG `AMWKWI00`

**Extract ALS output DAG fields:**
- Find the `parseResponse()` method in the Transaction class
- Grep for `getField("AM*")` calls. ALS output fields typically use prefix `AMWKMD00-*` for output message data.
- Record each field with its DTO setter: `getField("AMWKMD00-BAL-AMT")` → `setBalance()` → output field `BAL-AMT` from DAG `AMWKMD00`

**Compile ALS_DAG_FIELDS in the discovery summary:**
```
ALS_DAG_FIELDS:
  PROGRAM: <ALS program name>
  TRANSACTION_CLASS: <class name>
  INPUT_DAG: AMWKWI00
    AMWKWI00-RT-ACCT-NUM → account number (sortCode + accountNumber)
    AMWKWI00-TR-EFF-DATE → balance date
    AMWKWI00-USER-BU-ID → business unit ID
  OUTPUT_DAG: AMWKMD00
    AMWKMD00-<field> → <DTO setter> (from parseResponse)
    ...
```

- Document under `**ALS DAG Fields:**` in Quick Reference (not TDL Tables)
- Note: ALS services use a proprietary datastream protocol (DatastreamTransaction), NOT CS mainframe MQ/CICS and NOT WMID/WMOD patterns
