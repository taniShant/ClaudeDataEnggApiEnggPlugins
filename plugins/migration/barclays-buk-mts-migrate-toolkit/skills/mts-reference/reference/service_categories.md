# Service Categories

Each discovered service integration is classified into one of 15 categories using a deterministic classification algorithm. The category determines documentation depth, Section 9 template variant, and replacement API target.

## EBS/EGS JAR-based Categories (IN SCOPE for migration)

| # | Category | Transport | Detection Rule | Replacement API Target | Analysis Depth |
|---|----------|-----------|---------------|----------------------|----------------|
| 1 | `mainframe-mq` | IBM MQ -> CICS | EGS ODS MF JAR exists in dependencies | ODS APIs (sodscustenq, sodsaccountsenq, etc.) | Full: command class, DataGroups, TDL mapping |
| 2 | `oracle-db-direct` | JDBC -> Oracle | `CommonUtilityGateway` / `ReferenceData.populateData()` usage | Static Data Hub API | Light: gateway class, tables, JNDI datasource |
| 3 | `db2-reference` | JDBC -> DB2 | `ProductGateway.findByPrimaryKey()` usage | Static Data Hub API | Light: gateway class, tables, JNDI datasource |
| 4 | `soap-stub` | AXIS2 SOAP | `*StubConnector` import + `serviceDelegate.doService()` | ODS/domain APIs | Medium: StubConnector, SOAP operations, request/response |
| 5 | `soap-eao` | SOAP | `*SoapBindingStub` / `*Eao` + `?wsdl` config | ODS/domain APIs | Medium: EAO class, SOAP endpoint, operations |
| 6 | `cmod-odwek` | HTTP POST | `com.barclays.gs.cmod.*` import | CMOD/ODWEK replacement APIs (search Confluence) | Medium: EAO class, ODWEK path, document types |
| 7 | `tcv-hybrid` | Dual-path MQ+REST | `LifecycleService.SERVICE_NAME` + `TCV_API_ENABLED` flag | Already partially migrated (REST path exists) | Medium: dual paths, feature flag |
| 8 | `scv` | SOAP | `com.barclays.scv.*` import + SCV JARs | ODS/domain APIs | Medium: SCV endpoint, model classes |
| 9 | `soap-webservice` | SOAP (non-CICS) | EGS JAR with `*ProxyServiceWrapper` / `*ServiceAssembler` / `*WebService*` class (no ODS MF Transaction pattern) | Domain-specific APIs (ILP, Hogan, etc.) | Medium: gateway class, SOAP service ID, backend system |
| 10 | `itsu-oracle` | JDBC (ITSU/Oracle) | EBS JAR group = `executioncontext` or `*Helper` class accessing Oracle/JDBC directly via ITSU framework | ITSU replacement / Oracle migration | Light: data access class, Oracle tables, JNDI datasource |
| 11 | `als-backend` | ALS proprietary | EBS JAR group = `loans` or `lending` with ALS-specific Transaction/Gateway classes (no ODS MF pattern) | ALS replacement APIs (domain-specific) | Medium: ALS gateway, transaction class, ALS tables |

## Already-API Categories (OUT OF SCOPE for migration pipeline)

| # | Category | Transport | Detection Rule | Notes |
|---|----------|-----------|---------------|-------|
| 12 | `already-api-rest` | REST | `serviceManager.doService(*, EXECUTE_API, *)` pattern | ~88 services. Discover for inventory, exclude from pipeline. |
| 13 | `already-api-direct-http` | HTTP | `CloseableHttpClient` / direct `RestTemplate` (no EBS) | Direct HTTP calls. Inventory only. |

## Auxiliary Categories

| # | Category | Detection Rule | Analysis Depth |
|---|----------|---------------|----------------|
| 14 | `reference-data-only` | Name heuristics: Reference/Config/Common/CodedValue | Config-only: document from properties/XML |
| 15 | `framework` | Name heuristics: Audit/Context/Security | Config-only: document from properties/XML |

---

## Deterministic Classification Algorithm

Apply these rules **in order** — use the FIRST rule that matches. This ensures deterministic, reproducible classification.

| Priority | Condition | Category |
|----------|-----------|----------|
| 1 | `serviceManager.doService(*, EXECUTE_API, *)` or `serviceManager.doService(*, RestApiUtils.EXECUTE_API, *)` | `already-api-rest` |
| 2 | `CloseableHttpClient` or direct `RestTemplate` usage (no EBS JAR involvement) | `already-api-direct-http` |
| 3 | `*StubConnector` import AND `serviceDelegate.doService()` call | `soap-stub` |
| 4 | `com.barclays.gs.cmod.*` import | `cmod-odwek` |
| 5 | `com.barclays.scv.*` import AND SCV JARs in dependencies | `scv` |
| 6 | `LifecycleService.SERVICE_NAME` AND `TCV_API_ENABLED` feature flag | `tcv-hybrid` |
| 7 | `*SoapBindingStub` or `*Eao` import AND `?wsdl` config in properties | `soap-eao` |
| 7.5 | EGS JAR exists AND EGS gateway class contains `*ProxyServiceWrapper`, `*ServiceAssembler`, or `*WebService*` (i.e., SOAP call to non-CICS backend) AND no ODS MF Transaction `getProgramCode()`/`getVersionCode()` pattern | `soap-webservice` |
| 8 | EGS ODS MF JAR exists in `build.gradle` for this service's domain | `mainframe-mq` |
| 8.5 | EBS JAR group contains `executioncontext` OR gateway/helper class uses JDBC/Oracle directly via ITSU framework (no EGS ODS MF JAR) | `itsu-oracle` |
| 8.6 | EBS JAR group contains `loans` or `lending` (e.g., `ebs_loansenquiry`) AND no EGS ODS MF JAR | `als-backend` |
| 9 | `ProductGateway.findByPrimaryKey()` call | `db2-reference` |
| 10 | `CommonUtilityGateway` or `ReferenceData.populateData()` usage | `oracle-db-direct` |
| 11 | Service name contains `Reference`, `Config`, `CodedValue`, `Common` | `reference-data-only` |
| 12 | Service name contains `Audit`, `Context`, `Security` | `framework` |

**Fallback:** If no rule matches, classify as `mainframe-mq` and flag for manual review. If EGS JAR source is available, verify by checking for Transaction class `getProgramCode()` — its absence suggests `soap-webservice` may be a better classification.

---

## Classification Heuristics (supplementary)

These heuristics supplement the deterministic algorithm when rule priority is ambiguous:

- Services whose EGS gateway uses `ProxyServiceWrapper` or `ServiceAssembler` patterns are typically **soap-webservice** (ILP, Hogan, or other non-CICS SOAP backends)
- Services whose EBS JAR group is `executioncontext` (e.g., `ebs_execctxemployee`) are typically **itsu-oracle** — they read from ITSU/Oracle, not mainframe
- Services whose EBS JAR group is `loans` or `lending` (e.g., `ebs_loansenquiry`) without a matching EGS ODS MF JAR are typically **als-backend**
- Services whose names contain `Customer`, `Account`, `Product`, `Sale`, `Application` are typically **mainframe-mq**
- Services whose names contain `Reference`, `Config`, `CodedValue`, `Common` are typically **reference-data-only**
- Services whose names contain `Audit`, `Context`, `Security` are typically **framework**
- When in doubt, check whether the service's EBS JAR has a corresponding EGS ODS MF JAR (e.g., `ebs_saleenquiry` -> `egs_odsmfsale`)
- For `already-api-rest`, look for `RestApiUtils.EXECUTE_API` or `REST_SERVICE_EXECUTE` as the method argument in `doService()`

---

## Confidence Levels

Each extracted data item receives a confidence tag indicating the reliability of the extraction method used. Downstream agents (per-service doc, api-replacement-match) use these tags to decide whether to add "Needs verification" markers.

| Level | Tag | Condition | Downstream Impact |
|-------|-----|-----------|-------------------|
| Highest | `verified-from-source` | Extracted from `-sources.jar` Java source code | No warnings. Full DataGroup-to-WMID conditional attribution available. |
| High | `verified-from-bytecode` | Extracted from compiled JAR — constant pool (Tier 1) confirmed by `javap` disassembly (Tier 3) | No warnings. DataGroup-to-WMID conditional attribution available from bytecode patterns. |
| High | `verified-from-rop-rip` | WMID/WMOD data cross-validated against ROP/RIP files (Tier 2) from compiled EGS JARs | No warnings. ROP/RIP files are authoritative for WMID parameter and WMOD field lists. |
| Medium | `partial-from-bytecode` | Constant pool extraction only (Tier 1), no `javap` available | Mark with note: "Extracted from compiled JAR. DataGroup-to-WMID conditional attribution not available." WMID/WMOD lists are complete but cannot determine which DataGroup gates each WMID. |
| Low | `inferred-from-convention` | Derived from naming patterns and reference tables only | Existing "Needs verification" markers. Data may be incomplete or incorrect. |

### Confidence Propagation

- The **discovery agent** assigns confidence per data item during Steps 1.10-1.15 (full mode) or S.7a-S.7e (single-service mode).
- The **correlation map** (`DOSERVICE_CORRELATION_MAP`) carries an aggregate confidence per entry: the lowest confidence of any constituent data item.
- The **per-service doc agent** displays the confidence tag in Section 6 (DataGroup Chain) and adds appropriate notes for `partial-from-bytecode` items.
- The **api-replacement-match** pipeline uses confidence to weight match scores: `verified-from-source` and `verified-from-bytecode` get full weight; `partial-from-bytecode` gets 0.8x; `inferred-from-convention` gets 0.5x.
