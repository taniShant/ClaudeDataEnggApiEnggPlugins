# Discovery Agent Output Format

Your final response MUST contain ALL of these sections, delimited by `## SECTION:` headers. If running low on context, return what you have with a `## SECTION: INCOMPLETE_STEPS` section listing which steps were not completed.

```
## SECTION: DISCOVERY_METADATA
- Project path: <path>
- Total doService calls: <N>
- EBS/EGS dependency count: <N>
- Source JARs available: <N> of <total>
- Steps completed: 1.1 through 1.<last completed>

## SECTION: DOSERVICE_CALLS

**KEY: Each entry MUST be a unique (Service Name, Method Name) pair.** Multiple doService calls to the same service with DIFFERENT method names are SEPARATE entries — they map to different Command classes, Transactions, and TDL tables. Do NOT collapse them into one entry.

**Pattern 3 (variable) entries:** When a multiplexer method routes multiple (service, method) combinations through a single doService call (see doservice_patterns.md Pattern 3), emit one entry per unique pair discovered through caller tracing.

For each call:
- Service Name (resolved): <string>
- Method Name (resolved): <string>
- Pattern: doService | direct-gateway | variable-traced | callService
- Framework: MCA1 | MCA2_MIS | MCA2_BEM (set by Step 0.5 + Step 1.1)
- File: <path>:<line>
- Request DTO: <class>
- Response DTO: <class>
- Containing Class: <class>
- Multiplexer Method: <method name if Pattern 3, else N/A>
- Transport: mainframe-mq | oracle-db-direct | db2-reference | soap-stub | soap-eao | cmod-odwek | tcv-hybrid | scv | soap-webservice | itsu-oracle | als-backend | already-api-rest | already-api-direct-http | reference-data-only | framework

## SECTION: CONFIG_SUMMARY
- Filter chain (ordered)
- Datasource configuration
- MQ configuration
- Key Spring XML/Java config beans

## SECTION: REST_ENDPOINTS
For each endpoint:
- HTTP Method + Path
- Controller Class
- Handler Method

## SECTION: CALL_CHAINS
For each doService call:
- Full chain from REST endpoint to doService with file:line references
- Multiple paths if reachable from multiple endpoints

## SECTION: EBS_DEPENDENCIES
For each dependency:
- Artifact name
- Group ID
- Version
- Jar Type (EBS / EGS / EGS ODS MF / EBS Common)
- Source JAR path (or "not available")
- Compiled JAR path (or "not available")
- jar_type: source | compiled (indicates which JAR was used for extraction)

## SECTION: WIREMOCK_DATA
- List of __files/ paths
- List of mappings/ paths

## SECTION: TRANSACTION_REGISTRY
For each Transaction class found:
- Class name
- Source JAR
- Program Code (from getProgramCode())
- Version Code (from getVersionCode())
- Composed Name (from getName(), e.g., TDLQCU)
- Class hierarchy chain
- Service description

## SECTION: DATAGROUP_WMID_TDL_CHAINS
For each Transaction class:
- Per-DataGroup mapping table:
  | DataGroup Enum | WMID Parameter | TDL Table | Compound? |
- Note any compound OR conditions

## SECTION: COMMAND_CHAINS
For each Command class:
- Command class name (FQN)
- Gateway.method() called
- DataGroups requested (list)
- Transaction class used
- WMID flags set
- TDL tables accessed

## SECTION: DOSERVICE_CORRELATION_MAP
For each doService call (keyed by Service Name + Operation Code):
- Service Name: <string>
- Operation Code: <string>
- EBS Artifact: <artifact name>
- Command Class: <FQN>
- Gateway Class: <class name>
- Gateway Method: <method name>
- Transaction Class: <class name>
- CICS Code: <program code from Transaction>
- DataGroups Requested: <list>
- WMID Fields: <list>
- TDL Tables: <list>
- ROP/RIP Available: true | false
- Confidence: verified-from-source | verified-from-bytecode | verified-from-rop-rip | partial-from-bytecode | inferred-from-convention

## SECTION: WMOD_FIELD_INVENTORY
For each Transaction class:
- Per-DataGroup-section summary:
  | DataGroup Section | Field Count | Key Fields | Access Method |

## SECTION: TRANSACTION_NAME_CORRELATION
| Property Key | Messaging Name | Transaction Class | CICS Code | ROP/RIP Available |

## SECTION: CONFIDENCE_INDICATORS
For each major data item, state one of:
- `verified-from-source`: extracted from `-sources.jar` Java source code
- `verified-from-bytecode`: extracted from compiled JAR — constant pool + javap confirmation
- `verified-from-rop-rip`: WMID/WMOD data cross-validated against ROP/RIP files from compiled EGS JARs
- `partial-from-bytecode`: constant pool extraction only, no javap available (DataGroup-to-WMID conditional mapping unavailable)
- `inferred-from-convention`: derived from naming patterns/reference tables

## SECTION: TRANSPORT_CLASSIFICATION
For each service, the deterministic classification result:
- Service Name: <string>
- Transport: <category from Step 1.17>
- Detection Rule Matched: <which priority rule triggered>
- Replacement API Target: <target from service_categories.md>

## SECTION: SOAP_STUB_REGISTRY
For each soap-stub service (from Step 1.18):
- StubConnector Class: <class name>
- SERVICE_NAME: <resolved constant>
- SOAP Endpoint URL: <from services.properties>
- SOAP Operations: <list of methods>
- Request Types: <class names>
- Response Types: <class names>

## SECTION: DATABASE_DIRECT_REGISTRY
For each oracle-db-direct / db2-reference service (from Step 1.19):
- Gateway Class: <class name>
- Gateway Method: <method name>
- Database Type: Oracle | DB2
- Tables Accessed: <list of table names>
- JNDI Datasource: <datasource name>
- Replacement Target: Static Data Hub API

## SECTION: HYBRID_SERVICE_REGISTRY
For each tcv-hybrid / scv service (from Step 1.21):
- Service Name: <string>
- Transport: tcv-hybrid | scv
- Feature Flag: <flag name, if applicable>
- Legacy Path: <description of MQ/SOAP path>
- REST Path: <description of REST path, if applicable>
- ConnectorGateway Classes: <list, if applicable>
- Endpoint: <TCVM or SCV endpoint>
- Model Packages: <data model packages>

## SECTION: ALREADY_API_INVENTORY
For each already-api-rest / already-api-direct-http service (from Step 1.22):
- Service Name: <string>
- Connector Name: <resolved constant>
- Transport: already-api-rest | already-api-direct-http
- Note: Inventory only — excluded from migration pipeline

## SECTION: CMOD_ODWEK_REGISTRY
For each cmod-odwek service (from Step 1.20):
- Service Name: <string>
- EAO Class: <class name>
- ODWEK Path: <path>
- Document Types: <list>
- Server Config: <config details>

## SECTION: SOAP_WEBSERVICE_REGISTRY
For each soap-webservice service (from Step 1.23):
- Service Name: <string>
- EGS Gateway: <GatewayClass.method()>
- Web Service ID: <e.g., X61563>
- Backend System: <e.g., ILP / Hogan>
- SOAP Endpoint: <URL or config key>
- Routing Condition: <e.g., belongsToILP()>

## SECTION: ITSU_ORACLE_REGISTRY
For each itsu-oracle service (from Step 1.24):
- Service Name: <string>
- EBS JAR: <artifact>
- Data Access Class: <class name>
- Oracle Tables: <list, or "via ITSU framework — not directly extractable">
- JNDI Datasource: <datasource name>

## SECTION: ALS_BACKEND_REGISTRY
For each als-backend service (from Step 1.25):
- Service Name: <string>
- EBS JAR: <artifact>
- ALS Gateway: <class name>
- ALS Transaction Class: <class name>
- ALS Tables: <list, or "proprietary — not extractable from source">

## SECTION: WRITE_TABLES
For each write/insert service (from Step 1.26):
- Service Name: <string>
- Write Tables:
  - <TABLE_NAME> (write target — <column1>, <column2>, ...)

## SECTION: ORCHESTRATION_SUB_SERVICES
For each orchestration service (from Step 1.27):
- Parent Service: <ServiceName.method>
- Sub-Services:
  - <SubServiceName.method>: TDL_TABLES=[...], SOURCE=<from doc | undocumented>

## SECTION: APPLICATION_LAYER_VERIFICATION
For each doService call, verification findings from Step 1.16:

### Wrapper DataGroup Flags
For each ServiceWrapper class:
- Wrapper Class: <class name>
- Method: <request-building method name>
- Flags:
  | DataGroup Flag | Value | Effect |
  Example: | setUkbaJointHoldingsRequired | false | TDLBAJT fields DISABLED |

### Converter Commented-Out Fields
For each converter with commented-out setters:
- Converter Class: <class name>
- Commented-Out Fields:
  | Line | Commented Setter | Target Field |
  Example: | 32 | //edo.setJointHolderDetails() | jointHolderDetails |

### Example Response Field Nullity
For each REST response field checked:
  | Field Name | Fixture Source | Value Found | Status |
  Status values: POPULATED | ALWAYS_NULL | ALWAYS_EMPTY | NOT_FOUND
  Example: | jointHolders | BUKExampleControllerResponses.java | null | ALWAYS_NULL |

### Enrichment Method Existence
For each enrichment method referenced in Command chains:
  | Method Name | In EBS JAR? | In Application Code? | Status |
  Status values: EXISTS | EBS_ONLY | NOT_FOUND
  Example: | populateBondProductDetails | Yes | No | EBS_ONLY |

## SECTION: INCOMPLETE_STEPS (only if applicable)
List any steps that could not be completed, with the reason.
```
