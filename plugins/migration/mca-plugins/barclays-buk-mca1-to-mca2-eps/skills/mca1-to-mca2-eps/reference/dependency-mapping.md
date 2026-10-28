# MCA1 to MCA2 Dependency Mapping

## BOM

| MCA1 | MCA2 |
|---|---|
| `com.barclays.eps:mca-dependencies:{MCA1_BOM}` | `com.barclays.global.mca:mca-dependencies:{MCA2_BOM}` |

## Core Framework

| MCA1 Dependency | MCA2 Replacement | Notes |
|---|---|---|
| `com.barclays.eps:scp-eps-core-comm:{MCA1_BOM}` | `com.barclays.global.mca:mca-eps-core` (from BOM) | Core EPS framework. Also provides `@EnableExperienceAPI`. |
| - | `com.barclays.global.mca:mca-context` (from BOM) | Context propagation |
| - | `com.barclays.global.mca:mca-context-utils` (from BOM) | Context utilities |
| - | `com.barclays.global.mca:mca-spring-context-utils` (from BOM) | Spring context utilities |
| - | `com.barclays.global.mca:mca-exception-handling-core` (from BOM) | Exception handling |
| - | `com.barclays.global.mca:mca-exception-handling-spring` (from BOM) | Spring exception handling |
| - | `com.barclays.global.mca:mca-response-handling-core` (from BOM) | Response assembly |
| `com.barclays.eps:scp-eps-libs-audit` | `com.barclays.mca:mca-eps-libs-audit:{MCA2_AUDIT_LIB}` | Audit libraries |

## Filters

| MCA1 Dependency | MCA2 Replacement | Notes |
|---|---|---|
| `com.barclays.eps:scp-eps-libs-filters` | `com.barclays.global.mca:mca-filter-core` (from BOM) | Auto-configured via @EnableExperienceAPI |
| - | `com.barclays.global.mca:mca-filter-contexts` | Context filter support |

## Logging

| MCA1 Dependency | MCA2 Replacement | Notes |
|---|---|---|
| `com.barclays.global.mca:mca-logging-spy:{MCA1_LOGGING_SPY}` | `com.barclays.global.mca:mca-logging-config-logback` (from BOM) | Logback-based logging |
| `com.barclays.mca:is-fwork-slf4j:5.2.004` | (removed) | No longer needed |
| `com.barclays.mca:is-logging-slf4j:5.1.002` | (removed) | No longer needed |

## Service Dispatch

| MCA1 Dependency | MCA2 Replacement | Notes |
|---|---|---|
| `com.barclays.global.mca:mca-service-locator:{MCA1_SERVICE_LOCATOR}` | `com.barclays.global.mca:mca-mis-client` (from BOM) | **Option 3 only (tech debt):** MIS service client via `MisClient`. Requires `@EnableMisServiceClient`. Mark call sites with `@MCA2-TECH-DEBT-MIS`. Add only if user chooses Option 3 for any doService call. |
| - | `com.barclays.global.mca:mca-service-client-starter` (from BOM) | Service client auto-configuration |

## REST Clients

| MCA1 Dependency | MCA2 Replacement | Notes |
|---|---|---|
| (ServiceManager.doService) | `com.barclays.global.mca:mca-service-client-starter` (from BOM) | Provides REST client infrastructure. **Note:** `mca-rest-client` does NOT exist — use `mca-service-client-starter`. |

## Security / Properties

| MCA1 Dependency | MCA2 Replacement | Notes |
|---|---|---|
| - | `com.barclays.global.mca:mca-jceks-spring-properties-processor` | JCEKS keystore properties |

## Optional / Commonly Needed

| Dependency | Notes |
|---|---|
| `com.barclays.global.mca:mca-tiaaas-client` | TIAAAS authentication client. Commonly needed for apps that call backend APIs requiring TIAAAS tokens. Used in the mca-eps-audit reference project. |
| `org.ehcache:ehcache:3.6.1` | EHCache for caching reference/preload data. Common addition for apps with reference data lookups (e.g., preloadScreen endpoints). |

## Testing

| MCA1 Dependency | MCA2 Replacement | Notes |
|---|---|---|
| `com.barclays.eps:scp-eps-test-common` | `org.mockito:mockito-core:{MOCKITO_VERSION}` (resolved from Nexus) | Mockito for mocking |
| - | `org.mockito:mockito-junit-jupiter:{MOCKITO_VERSION}` (resolved from Nexus) | JUnit 5 integration |

## Removed (transitively pulls MCA1)

| Dependency | Reason | Replacement |
|---|---|---|
| `com.barclays.eps:scp-eps-libs-customer:5.0.013` | Transitively pulls `scp-eps-core-comm` which conflicts with MCA2. Contains `UserBean`, `CodedValueBean`, `CodeDecodeBean`, `EpsResponseBean`, `ServiceManager`, `DataInterface`, `ReferenceDataHelper`, `RestConnectorRequestBean`, `RestConnectorResponseBean`, `EpsServiceHelper`, `EpsApplicationException`, `MessageBeanHelper`, `GenericAuditService`, `ReferenceDataService`, `AuditRequestBean` | Create local stubs in `migration/stubs/` package with TODO markers for MCA2 replacement |

### Class-level mapping (scp-eps-libs-customer)

| MCA1 Class (com.barclays.scp.eps.common.*) | Strategy | MCA2 Target |
|---|---|---|
| `beans.UserBean` | Local stub | `IOLSchema` / `UserContext` from `RequestContextProvider.getIOLContext()` |
| `beans.CodedValueBean` | Local stub | Domain-specific, no direct MCA2 equivalent |
| `beans.CodeDecodeBean` | Local stub | Domain-specific, no direct MCA2 equivalent |
| `beans.EpsResponseBean` | **Graduate stub → delete** | Plain POJO (no base class). Remove `extends EpsResponseBean`, add `implements Serializable` if needed. `Response<T>` at controller boundary only. |
| `beans.audit.AuditRequestBean` | Local stub | Check `mca-eps-libs-audit:{MCA2_AUDIT_LIB}` (resolved from Nexus) |
| `utils.ServiceManager` | Local stub | `RestClient.callRest()` via `mca-service-client-starter` (Option 1/2) or `MisClient` via `mca-mis-client` (Option 3 tech debt) |
| `utils.EpsServiceHelper` | Local stub | `RequestContextProvider.getIOLContext()` |
| `utils.DataInterface` | Local stub | Domain-specific, no direct MCA2 equivalent |
| `utils.ReferenceDataHelper` | Local stub | Domain-specific, no direct MCA2 equivalent |
| `exceptionhandling.exceptions.EpsApplicationException` | **Graduate stub → delete** | `ApplicationException` (`com.barclays.global.mca.libs.core.exceptions`). Use `ApplicationException(Message.create(code, title))` or `ApplicationException(Message, Throwable)`. For MisClient catch blocks, use `findCause()` pattern (see Pitfall 19). |
| `exceptionhandling.utils.MessageBeanHelper` | **Graduate stub → delete** | Throw `ApplicationException(Message.create(code, title))` directly. Framework `ExceptionControllerAdvice` auto-maps to error responses. |
| `restconnector.beans.RestConnectorRequestBean` | Local stub | MCA2 `RestClient` request pattern |
| `restconnector.beans.RestConnectorResponseBean` | Local stub | MCA2 `RestClient` response pattern |
| `services.GenericAuditService` | Local stub | Check `mca-eps-libs-audit:{MCA2_AUDIT_LIB}` (resolved from Nexus) |
| `services.ReferenceDataService` | Local stub | Check `mca-eps-libs-audit:{MCA2_AUDIT_LIB}` (resolved from Nexus) |

## Unchanged Dependencies

These dependencies are NOT changed during migration:
- All EBS/EDO service interfaces (ebs_*, service_fwork, etc.) — **keep** if any `ServiceManager.doService()` call uses Option 3 (MisClient); otherwise remove
- Database drivers (ojdbc7, db2jcc4)
- IBM MQ (mq-jms-spring-boot-starter)
- XML processing (JDOM, XStream, Xerces)
- Apache Commons (commons-lang3, commons-io)
- Jackson JSON (jackson-core, jackson-databind)
- OWASP ESAPI
- Spring Boot starters (web, actuator, test)
- ~~scp-eps-libs-customer~~ -> REMOVED (transitively pulls scp-eps-core-comm; see "Removed" section above)
- ~~scp-eps-libs-audit~~ -> now `mca-eps-libs-audit:{MCA2_AUDIT_LIB}` (resolved from Nexus) (see Core Framework table)
