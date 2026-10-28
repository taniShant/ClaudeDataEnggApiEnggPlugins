# MCA1 to MCA2 Migration Mappings (Behavior-Preservation Strategy)

## Strategy

This document uses the **behavior-preservation** migration strategy: all MCA1 **framework** patterns
are replaced with MCA2 equivalents, while all **business logic** (validation, mapping, computation,
business rules, data assembly) is preserved with `@MCA2-*` markers. No logic is silently dropped.

---

## Quick Reference

| MCA1 Pattern | MCA2 Replacement | Preserve? |
|---|---|---|
| `scp-eps-core-comm` | `mca-eps-core` + transitive deps (context, exception, response) | Framework — replace |
| `mca-dependencies:6.2.x` BOM | `mca-dependencies:{MCA2_BOM}` (default: 2.3.021) | Framework — replace |
| `@EnableSpringServiceLocator` | `@EnableExperienceAPI` | Framework — replace |
| `@ImportResource(xml)` | `@Configuration` + `@Bean` | Framework — replace |
| `extends EpsServiceAbstractController` | Plain `@RestController` + constructor DI | Framework — replace |
| `extends EpsAbstractService` | Plain Spring bean + constructor DI | Framework — replace |
| `ServiceManager.doService()` | `restClient.callRest()` (framework) or `APIServiceManager` wrapper or `MisClient` (tech debt, DEC-016) | Framework — replace dispatch; **preserve request/response logic around it**. Per-call choice: ask user for each call site. |
| `EpsServiceHelper.getUserBean(request)` | `RequestContextProvider.getIOLContext()` + `IOLContextAdapter` (for stubs) | Framework — replace; **preserve business logic that reads user/customer/account fields** |
| `scp-eps-libs-filters` / `FilterRegistrationBean` ×7 | Auto-configured by `@EnableExperienceAPI` | Framework — replace |
| `MCAMQAutoConfiguration` | Standard `mq-jms-spring-boot-starter` | Framework — replace |
| `mca-logging-spy` + `is-fwork-slf4j` | `mca-logging-config-logback` | Framework — replace |
| `LogHelper.error(Class, method, msg)` | SLF4J `logger.error(msg, ex)` | Framework — replace |
| `scp-eps-test-common` (GenericTestCase) | JUnit 5 + Mockito 5 | Framework — replace |
| `EpsApplicationException` | `ApplicationException(Message)` from `mca-exception-handling-core`. Graduate stub → real MCA2 type. Catch blocks use `findCause()` pattern for checked exceptions wrapped by MisClient. | Framework — replace; **graduate stub to `ApplicationException`; preserve error code inspection logic** |
| `EpsResponseBean` | Plain POJO (no base class). `Response<T>` at controller boundary only. Add `implements Serializable` if original was serializable. Graduate stub → delete. | Framework — replace; **graduate stub: remove `extends EpsResponseBean`, beans become plain POJOs** |
| `MessageBeanHelper` | `ApplicationException(Message.create(code, title))` thrown directly. Graduate stub → delete. | Framework — replace; **graduate stub: throw `ApplicationException(Message)` instead of populating error DTOs** |
| `XML bean config (<bean id="...">)` | `@Configuration` + `@Bean(name="...")` | Framework — replace |
| `external.services.*` properties | Direct service URL properties or YAML `services.rest-clients.*` | Framework — replace |
| `com.barclays.scp.eps.*` packages | `com.barclays.mca.eps.*` (optional — ask user) | Framework — replace if user opts in; keep existing if user defers |
| `EpsResponseBean` (OAS) | `ErrorResponseType` + `Response<T>` (OAS) | Framework — replace |
| `process.json "type": "mca1"` | Remove `type` field (default MCA2 routing) | Framework — replace |
| **All validation logic** | Preserve in service layer | **YES — mark @MCA2-VALIDATION** |
| **All mapper logic** | Preserve in service layer | **YES — mark @MCA2-MAPPING** |
| **All helper logic** | Preserve in service layer | **YES — mark @MCA2-PRESENTATION** |
| **All business rules** | Preserve in service layer | **YES — mark @MCA2-REVIEW-BUSINESS-RULE** |
| **All data assembly** | Preserve in service layer | **YES — mark @MCA2-REVIEW-DATA-ASSEMBLY** |
| **All DB access logic** | Preserve + mark for API creation | **YES — mark @MCA2-REVIEW-DB-ACCESS** |

---

## Dependency Mapping

### BOM

| MCA1 | MCA2 |
|---|---|
| `com.barclays.eps:mca-dependencies:{MCA1_BOM}` (default: 6.2.008) | `com.barclays.global.mca:mca-dependencies:{MCA2_BOM}` (default: 2.3.021) |

### Core Framework

| MCA1 Dependency | MCA2 Replacement | Notes |
|---|---|---|
| `com.barclays.eps:scp-eps-core-comm:{MCA1_BOM}` (default: 6.2.008) | `com.barclays.global.mca:mca-eps-core` (from BOM) | Core EPS framework. Provides `@EnableExperienceAPI`. Transitively provides context, exception, response modules (DEC-019). |
| `com.barclays.eps:scp-eps-libs-audit` | `com.barclays.mca:mca-eps-libs-audit:{MCA2_AUDIT_LIB}` (default: 2.0.009) | Audit libraries. Note different group ID. |

### Filters

| MCA1 Dependency | MCA2 Replacement | Notes |
|---|---|---|
| `com.barclays.eps:scp-eps-libs-filters` | `com.barclays.global.mca:mca-filter-core` (from BOM) | Auto-configured via `@EnableExperienceAPI`. `mca-filter-contexts` removed after 1.0.003 (DEC-018). |

### Logging

| MCA1 Dependency | MCA2 Replacement | Notes |
|---|---|---|
| `com.barclays.global.mca:mca-logging-spy:{MCA1_LOGGING_SPY}` (default: 0.1.340) | `com.barclays.global.mca:mca-logging-config-logback` (from BOM) | Logback-based logging |
| `com.barclays.mca:is-fwork-slf4j:5.2.004` | (removed) | No longer needed |
| `com.barclays.mca:is-logging-slf4j:5.1.002` | (removed) | No longer needed |

### Service Dispatch

| MCA1 Dependency | MCA2 Replacement | Notes |
|---|---|---|
| `com.barclays.global.mca:mca-service-locator:{MCA1_SERVICE_LOCATOR}` (default: 1.0.109) | (removed) | Eliminated entirely (DEC-016) |
| `ServiceManager.doService()` | `com.barclays.global.mca:mca-service-client-starter` (from BOM) | Provides `RestClient.callRest()` (framework pattern). `APIServiceManager` is optional team-level wrapper. |
| `ServiceManager.doService()` (MIS calls) | `com.barclays.global.mca:mca-mis-client` (from BOM) | **Option 3 (tech debt):** Preserves MIS call via `MisClient`. Requires `@EnableMisServiceClient` on Application class. Mark with `@MCA2-TECH-DEBT-MIS`. |

### Security / Properties

| MCA1 Dependency | MCA2 Replacement | Notes |
|---|---|---|
| — | `com.barclays.global.mca:mca-jceks-spring-properties-processor` | JCEKS keystore properties |

### Testing

| MCA1 Dependency | MCA2 Replacement | Notes |
|---|---|---|
| `com.barclays.eps:scp-eps-test-common` | `org.mockito:mockito-core:{MOCKITO_VERSION}` (default: 5.14.2) | Mockito for mocking |
| — | `org.mockito:mockito-junit-jupiter:{MOCKITO_VERSION}` (default: 5.14.2) | JUnit 5 integration |

### Removed (Transitively Pulls MCA1)

| Dependency | Reason | Replacement |
|---|---|---|
| `com.barclays.eps:scp-eps-libs-customer:5.0.013` | Transitively pulls `scp-eps-core-comm`. Contains `UserBean`, `CustomerBean`, `AccountBean`, `EpsResponseBean`, `ServiceManager`, `EpsServiceHelper`, `EpsApplicationException`, `MessageBeanHelper`, etc. | Create local stubs in `migration/stubs/` package. See `migration-stubs.md`. |

### Minimal build.gradle Dependencies (DEC-019)

Per `mca-api-template`, only 4 core MCA2 libs are declared explicitly. All others come transitively:

```gradle
implementation platform("com.barclays.global.mca:mca-dependencies:{MCA2_BOM}")  // default: 2.3.021
implementation "com.barclays.global.mca:mca-eps-core"
implementation "com.barclays.global.mca:mca-logging-config-logback"
implementation "com.barclays.global.mca:mca-service-client-starter"
implementation "com.barclays.global.mca:mca-response-handling-core"

// Project-specific (add as needed):
// implementation "com.barclays.mca:mca-eps-libs-audit:{MCA2_AUDIT_LIB}"  // default: 2.0.009
// implementation "com.barclays.global.mca:mca-jceks-spring-properties-processor"
// implementation "com.barclays.global.mca:mca-mis-client"   // Only if Option 3 MisClient tech debt chosen (DEC-016)
// implementation "org.ehcache:ehcache:3.6.1"   // Only if caching (DEC-024)

testImplementation "org.mockito:mockito-core:{MOCKITO_VERSION}"  // default: 5.14.2
testImplementation "org.mockito:mockito-junit-jupiter:{MOCKITO_VERSION}"  // default: 5.14.2
```

### Unchanged Dependencies

- All EBS/EDO service interfaces (ebs_*, service_fwork, etc.) — **REMOVE** (DEC-020, GAP-020), **unless** any `ServiceManager.doService()` call uses Option 3 (MisClient), in which case **keep** the EBS/EDO JARs required by MisClient
- Database drivers (ojdbc7, db2jcc4) — **REMOVE** (zero DB connections in MCA2)
- IBM MQ (`mq-jms-spring-boot-starter`) — keep if project uses MQ
- XML processing (JDOM, XStream, Xerces) — remove if only used by EBS
- Apache Commons (commons-lang3, commons-io) — keep if business logic uses them
- Jackson JSON (jackson-core, jackson-databind) — keep
- Spring Boot starters (web, actuator, test) — keep

---

## Pattern 1: Application Bootstrap

### MCA1 (Before)
```java
@SpringBootApplication
@ImportResource({"classpath:/app-config.xml"})
@Import({MCAMQAutoConfiguration.class, DataSourceConfig.class, AppConfig.class})
@EnableSpringServiceLocator
public class SpringBootWebApplication {
    public static void main(String[] args) {
        SpringApplication.run(SpringBootWebApplication.class, args);
    }
}
```

### MCA2 (After)
```java
@SpringBootApplication
@EnableExperienceAPI
@EnableMisServiceClient   // Add only if Option 3 MisClient tech debt chosen for any doService call
@Import({ApplicationConfig.class})
public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}
```

**Changes:**
- Remove `@ImportResource` (no XML configs)
- Remove `@EnableSpringServiceLocator` — eliminated entirely (DEC-016)
- Remove `MCAMQAutoConfiguration.class` and `DataSourceConfig.class` from `@Import`
- Add `@EnableExperienceAPI` (from `com.barclays.global.mca.libs.eps.EnableExperienceAPI`)
- Import only `ApplicationConfig.class` (DEC-022: `RestClientsConfig` consolidated into `ApplicationConfig`)
- Rename class to `Application` (convention)

---

## Pattern 2: Configuration (XML to Java)

### MCA1 (Before)
```xml
<beans>
    <import resource="classpath:eps-common-config.xml" />
    <bean id="myService" class="com.example.MyServiceImpl" />
</beans>
```

### MCA2 (After)
```java
@Configuration
public class ApplicationConfig {
    @Bean(name = "myService")
    public MyServiceImpl myService(RequestContextProvider contextProvider,
                                    BaeUtilityMapper mapper) {
        return new MyServiceImpl(contextProvider, mapper);
    }
}
```

**Changes:**
- Delete ALL XML config files
- Create single `ApplicationConfig.java` with all `@Bean` definitions (DEC-022)
- Preserve bean names: `@Bean(name = "originalXmlBeanId")`
- Remove `DataSourceConfig` entirely — zero DB connections in MCA2

---

## Pattern 3: Controllers

### MCA1 (Before)
```java
@RestController
@RequestMapping(value = "/api/v1")
public class MyControllerImpl extends EpsServiceAbstractController implements MyController {
    @Resource(name = "MyService")
    private MyService myService;

    @PostMapping("/action")
    public ResponseBean doAction(HttpServletRequest request, @RequestBody RequestBean req) {
        return myService.doAction(request, req);
    }
}
```

### MCA2 (After — behavior-preservation)
```java
@RestController
@RequestMapping(value = "/api")
public class MyController {
    private final MyService myService;

    public MyController(MyService myService) {
        this.myService = myService;
    }

    @PostMapping("/action")
    public Response<ResponseBean> doAction(@RequestBody RequestBean req) {
        ResponseBean result = myService.doAction(req);
        return Response.<ResponseBean>assemble().build(result);
    }
}
```

**Changes (framework):**
- Remove `extends EpsServiceAbstractController`
- Remove `implements` controller interface — controller interfaces are not needed in MCA2
- Rename class from `*ControllerImpl` to `*Controller` (no interface, no `Impl` suffix needed)
- Delete the controller interface class (`MyController.java` interface) — it is MCA1 boilerplate
- Constructor injection replaces `@Resource` setter injection
- Remove `HttpServletRequest` parameter
- Return `Response<T>` via `Response.<T>assemble().build(data)` (DEC-017, DEC-020)
- Domain beans are plain POJOs — no `extends EpsResponseBean` (DEC-020)

**Preserved (behavior):**
- All endpoint paths and HTTP methods
- Request/response contracts (same field names)

---

## Pattern 4: Services (Behavior-Preservation)

### MCA1 (Before)
```java
public class MyServiceImpl extends EpsAbstractService implements MyService {
    public ResponseBean doAction(HttpServletRequest request, RequestBean req) {
        UserBean user = EpsServiceHelper.getUserBean(request);
        // ... validation logic, business rules, mapping ...
        ResponseDto response = (ResponseDto) this.serviceManager.doService(
            ServiceName.NAME, "methodName", requestDto, userBean);
        // ... response formatting, error handling ...
        return mapResponse(response);
    }
}
```

### MCA2 (After — behavior-preservation)
```java
public class MyServiceImpl implements MyService {
    private final RequestContextProvider contextProvider;
    private final APIServiceManager apiServiceManager;
    private final MyRestClientBean restClientBean;
    private final MyUtilityMapper mapper;

    public MyServiceImpl(RequestContextProvider contextProvider,
                         APIServiceManager apiServiceManager,
                         MyRestClientBean restClientBean,
                         MyUtilityMapper mapper) { /* constructor injection */ }

    public ResponseBean doAction(RequestBean req) {
        IOLSchema iolContext = contextProvider.getIOLContext();
        // @MCA2-VALIDATION — preserved from MCA1 ValidateServiceImpl
        validateRequest(req, iolContext);
        // Framework replacement: ServiceManager.doService() -> restClient.callRest()
        RestConnectorRequest request = mapper.buildRequest(iolContext, req);
        Object response = apiServiceManager.callRestApiPOST(
            restClientBean.getRestClient(), request, Object.class);
        // @MCA2-MAPPING — preserved from MCA1 ResponseMapper
        return mapResponse(response);
    }
}
```

### MCA2 (After — Option 3: MisClient tech debt, per-call choice)
```java
public class MyServiceImpl implements MyService {
    private final RequestContextProvider contextProvider;
    private final MisClient<com.barclays.services.backend.BackendService> misBackendClient;
    private final MisUserContextProvider misUserContextProvider;
    private final MyUtilityMapper mapper;

    public MyServiceImpl(RequestContextProvider contextProvider,
                         MisClient<com.barclays.services.backend.BackendService> misBackendClient,
                         MisUserContextProvider misUserContextProvider,
                         MyUtilityMapper mapper) { /* constructor injection */ }

    public ResponseBean doAction(RequestBean req) {
        IOLSchema iolContext = contextProvider.getIOLContext();
        // @MCA2-VALIDATION — preserved from MCA1 ValidateServiceImpl
        validateRequest(req, iolContext);
        // @MCA2-TECH-DEBT-MIS — MisClient typed call replacing MCA1 ServiceManager.doService().
        // Uplift to RestClient.callRest() at a later stage.
        RequestDto requestDto = mapper.buildRequest(iolContext, req);
        com.barclays.is.user.UserContext userContext = misUserContextProvider.createUserContext();
        ResponseDto response = misBackendClient.callService(
                svc -> svc.methodName(userContext, requestDto)).reduce();
        // @MCA2-MAPPING — preserved from MCA1 ResponseMapper
        return mapResponse(response);
    }
}
```

**Changes (framework):**
- Remove `extends EpsAbstractService`
- Replace `EpsServiceHelper.getUserBean(request)` with `contextProvider.getIOLContext()`
- Replace `ServiceManager.doService()` with `restClient.callRest()` / `APIServiceManager`
- **Option 3 (per-call):** Replace `ServiceManager.doService()` with typed `MisClient<ServiceInterface>.callService()` + `MisUserContextProvider` — mark `@MCA2-TECH-DEBT-MIS`
- Remove `HttpServletRequest` from method signatures
- Constructor injection for all dependencies

**Preserved (behavior):**
- **ALL validation logic** — mark with `// @MCA2-VALIDATION`
- **ALL mapping logic** — mark with `// @MCA2-MAPPING`
- **ALL business rules** — mark with `// @MCA2-REVIEW-BUSINESS-RULE`
- **ALL data assembly** — mark with `// @MCA2-REVIEW-DATA-ASSEMBLY`
- **ALL helper logic** — mark with `// @MCA2-PRESENTATION`

---

## Pattern 5: Context Propagation

### MCA1 (Before)
```java
UserBean user = EpsServiceHelper.getUserBean(request);
CustomerBean customer = EpsServiceHelper.getCustomerBean(request);
AccountBean account = EpsServiceHelper.getAccountBean(request);
```

### MCA2 (After — behavior-preservation)

**Option A: Direct IOLSchema access (for new/thin logic)**
```java
IOLSchema iolContext = contextProvider.getIOLContext();
// Use iolContext.getUserContext(), iolContext.getCustomerContext(), etc.
```

**Option B: IOLContextAdapter + stubs (for preserved business logic)**
```java
IOLSchema iolContext = contextProvider.getIOLContext();
UserBean userBean = IOLContextAdapter.extractUserBean(iolContext);
CustomerBean customerBean = IOLContextAdapter.extractCustomerBean(iolContext);
AccountBean accountBean = IOLContextAdapter.extractAccountBean(iolContext);
// Preserved business logic continues to use userBean.getUserId(), etc.
```

**Option C: MisUserContextProvider (for MIS call sites using Option 3 MisClient)**
```java
// Auto-configured by @EnableMisServiceClient — inject via constructor
private final MisUserContextProvider misUserContextProvider;

// For EBS services that take com.barclays.is.user.UserContext:
com.barclays.is.user.UserContext userContext = misUserContextProvider.createUserContext();
responseDto = misAuditClient.callService(svc -> svc.method(userContext, requestDto)).reduce();

// For EBS services that take com.barclays.edo.v1.UserContextEdo:
com.barclays.edo.v1.UserContextEdo userContextEdo = misUserContextProvider.createUserContextEdo();
responseDto = misEmployeeClient.callService(svc -> svc.method(userContextEdo, requestDto)).reduce();
```

**Note:** `MisUserContextProvider` creates `UserContext`/`UserContextEdo` directly from IOLSchema. It replaces the need for `IOLContextAdapter` at MIS call sites. `IOLContextAdapter` is still needed for business logic that reads `UserBean` fields (e.g., `userBean.getUsingParty().getEmployeeIdAsString()`).

**Context field mapping:**

| MCA1 Accessor | MCA2 Accessor | Notes |
|---|---|---|
| `userBean.getUsingParty().getName()` | `iolSchema.getUserContext().getUserId()` | Or `IOLContextAdapter.extractUserBean().getUserId()` |
| `userBean.getChannel().getId()` | `iolSchema.getUserContext().getChannel().getChn()` | Or via adapter |
| `userBean.getCorrelationId()` | `contextProvider.getCorrelationId()` / `iolSchema.getCorid()` | |
| `userBean.getLocation().getDeviceId()` | `iolSchema.getUserContext().getDvid()` | |
| `customerBean.getCustomerId()` | `iolSchema.getCustomerContext().getIdentifiers()` | |
| `accountBean.getSortCode()` | `iolSchema.getAccountContext().getAccount()` fields | |

---

## Pattern 6: Service Dispatch

### MCA1 (Before)
```java
getServiceManager().doService("backendService", "method", params);
```

### MCA2 (After — framework pattern, DEC-016)
```java
// Framework-level: RestClient.callRest() from mca-service-client-starter
restClient.callRest(rt -> rt.exchange(url, HttpMethod.POST, httpEntity, ResponseType.class, params))
    .handleError(e -> { throw e; })
    .reduce();
```

### MCA2 (After — optional team-level APIServiceManager wrapper)
```java
// Team-level wrapper (optional, not framework)
apiServiceManager.callRestApiPOST(restClientBean.getRestClient(), request, ResponseType.class);
```

### MCA2 (After — Option 3: MisClient tech debt, for MIS backend service calls)
```java
// Bean configuration in ApplicationConfig:
@Bean
public MisClient<com.barclays.services.audit.AuditService> misAuditClient(
        MisServiceLocator misServiceLocator, DefaultMisClientResponseHandler handler) {
    com.barclays.services.audit.AuditService svc =
            misServiceLocator.findService("CentralAuditServiceEBS", com.barclays.services.audit.AuditService.class);
    return new MisClient<>(svc, handler);
}

// Call pattern — typed callService() with UserContext from MisUserContextProvider:
// @MCA2-TECH-DEBT-MIS — MisClient typed call replacing MCA1 ServiceManager.doService()
com.barclays.is.user.UserContext userContext = misUserContextProvider.createUserContext();
ResponseDto result = misAuditClient.callService(
        svc -> svc.method(userContext, requestDto)).reduce();
```

### MCA2 (After — REST API calls via RestClient.callRest())
```java
// For ServiceManager.doService() calls that targeted REST APIs (e.g., executeApi pattern):
// RestClient beans auto-configured from application.properties services.rest-clients.*
// @MCA2-TECH-DEBT-REST — RestClient.callRest() replacing MCA1 ServiceManager.doService() REST connector
ResponseType result = odsRefDataRestClient.callRest(rt ->
        rt.exchange(serviceUrl, HttpMethod.POST, httpEntity, ResponseType.class)
).reduce();
```

**Key points (DEC-016):**
- `RestClient.callRest()` is the **framework** replacement for REST API calls
- `APIServiceManager` is an **optional team-level wrapper**
- **Option 3 (tech debt):** Typed `MisClient<ServiceInterface>` from `mca-mis-client` preserves MIS dispatch semantics. Requires `@EnableMisServiceClient` on Application class and `mca-mis-client` dependency. Mark every call site with `@MCA2-TECH-DEBT-MIS`.
- **Distinguish MIS vs REST:** `ServiceManager.doService()` calls to MIS backend services (EBS interfaces) → use typed `MisClient<>`. REST connector calls (service names like `*API`, method `executeApi`, `RestConnectorRequestBean`) → use `RestClient.callRest()` with `@MCA2-TECH-DEBT-REST` marker.
- Per-call choice: each `ServiceManager.doService()` call site can independently use Option 1, 2, or 3
- Named `RestClient` qualifier beans configured via properties `services.rest-clients.*`
- `EBSGatewayLocator` / `ServiceLocator` eliminated entirely
- If a typed MisClient service interface extends `ErrorMessageSupplier`, `getErrorMessage()` can be called directly on that client — no separate bean needed

---

## Pattern 7: Exception Handling

### MCA1 (Before)
```java
throw new EpsApplicationException(errorCode);
// Handled by EpsServiceAbstractController @ExceptionHandler
```

### MCA2 (After — DEC-020, DEC-021)
```java
// For REST call failures:
try {
    result = apiServiceManager.callRestApiPOST(...);
} catch (RestCallErrorException e) {
    mapper.handleServiceException(e);  // translates to NotFoundException / RuntimeException
}

// Framework exceptions (auto-handled by ExceptionControllerAdvice):
throw new NotFoundException(Message.create("NOT_FOUND", "Record not found"));  // -> 404
throw new RequestException(Message.create("BAD_REQUEST", "Invalid input"));    // -> 400

// Direct replacement for EpsApplicationException (graduated stub):
throw new ApplicationException(Message.create("ERROR_CODE", "Error description"));       // -> 500
throw new ApplicationException(Message.create("ERROR_CODE", "Error description"), cause); // with cause
```

### MCA2 (After — MisClient checked exception handling with findCause pattern)
```java
// MisClient.reduce() wraps checked exceptions (e.g., NoRecordsFoundException,
// ServiceInvalidException) in unchecked wrappers. You CANNOT catch them directly.
// Use the findCause() pattern to walk the exception cause chain:

try {
    ResponseDto result = misClient.callService(
            svc -> svc.method(userContext, requestDto)).reduce();
    // ... process result ...
} catch (Exception exception) {
    NoRecordsFoundException nrfe = findCause(exception, NoRecordsFoundException.class);
    if (nrfe != null) {
        if ("818216".equals(nrfe.getCode())) {
            String message = getNoRecordsFoundFailedMessage();
            throw new ApplicationException(
                Message.create(nrfe.getCode(),
                    message != null && !message.isEmpty() ? message : "No records found"));
        }
        throw new ApplicationException(
            Message.create(nrfe.getCode(), nrfe.getMessage()), nrfe);
    }
    throw exception instanceof RuntimeException
        ? (RuntimeException) exception : new RuntimeException(exception);
}

// findCause() utility method — add to any class that needs cause-chain walking:
@SuppressWarnings("unchecked")
private static <T extends Throwable> T findCause(Throwable t, Class<T> type) {
    while (t != null) {
        if (type.isInstance(t)) return (T) t;
        t = t.getCause();
    }
    return null;
}
```

**Key points:**
- `ExceptionControllerAdvice` auto-configured by `@EnableExperienceAPI` (DEC-021)
- No custom `GlobalExceptionHandler` needed
- `EpsMessageBean` is MCA1 framework — use `Message` from `mca-exception-handling-core` (DEC-020)
- **Stub graduation:** `EpsApplicationException` → `ApplicationException(Message)`. `EpsResponseBean` → plain POJO. `MessageBeanHelper` → throw `ApplicationException(Message)` directly. Delete these stubs after graduation.
- **MisClient exception wrapping:** `MisClient.reduce()` wraps checked exceptions in unchecked wrappers. Use `catch (Exception)` + `findCause()` to locate specific checked exceptions in the cause chain. Do NOT use `catch (CheckedException)` — it won't compile because `reduce()` doesn't declare checked exceptions.

### ApplicationException API (com.barclays.global.mca.libs.core.exceptions)
```java
// Constructors:
new ApplicationException(Message message)
new ApplicationException(List<Message> messages)
new ApplicationException(Message message, Throwable cause)
// Inherited from GenericException:
getMessages()       // List<Message>
getFirstMessage()   // Message
```

### Message API (com.barclays.global.mca.libs.core.response.entity)
```java
// Factory methods:
Message.create(String code, String title)
Message.create(String code, String title, String detail)
// Constructor:
new Message(String code, String title, String detail, Severity severity)
// Fields: id, code, title, detail, severity
```

---

## Pattern 8: Response Handling

### MCA1 (Before)
```java
return auditResults;  // Raw bean extends EpsResponseBean, wrapped by controller
```

### MCA2 (After — DEC-017, DEC-020)
```java
// Controller returns Response<T>:
return Response.<AuditResults>assemble().build(results);

// Domain beans are plain POJOs — NO extends EpsResponseBean
// EpsResponseBean.fatalError / EpsMessageBean.messages are MCA1 framework — removed
```

**Stub graduation (recommended):** Remove `extends EpsResponseBean` from all domain beans — they become plain POJOs. If the original bean was `Serializable` (via `EpsResponseBean`), add `implements Serializable` directly. Error messages are conveyed via `ApplicationException(Message)` thrown from the service layer, which the `ExceptionControllerAdvice` auto-maps to error responses.

**Behavior-preservation (fallback):** If business logic heavily calls `response.setMessages()` or `response.addMessage()` and the code is too complex to refactor in the migration pass, keep stub `EpsResponseBean` temporarily. Plan to graduate the stub in a follow-up pass.

---

## Pattern 9: Logging

### MCA1 (Before)
```java
LogHelper.error(MyClass.class, "methodName", "Error message:" + ex);
```

### MCA2 (After)
```java
private static final Logger logger = LoggerFactory.getLogger(MyClass.class);
logger.error("Error message", ex);
```

---

## Pattern 10: Filter Chain

### MCA1 (Before)
```java
@Bean public FilterRegistrationBean registerAuthenticationFilter() { /* OAuthValidatorFilter */ }
@Bean public FilterRegistrationBean registerUserContextFilter() { /* UserContextFilter */ }
// ... 5 more framework filters
```

### MCA2 (After)
All 7 framework filters auto-configured by `@EnableExperienceAPI`. Remove ALL `FilterRegistrationBean`
declarations for framework filters. Keep app-owned filters (e.g., `CrossScriptingFilter`).

---

## Pattern 11: Package Renaming (Optional — ask user)

**Ask the user** whether to rename packages. This is optional and can be deferred.

- **Option A: Rename now** — rename all `com.barclays.scp.eps.*` to `com.barclays.mca.eps.*`
- **Option B: Keep existing** — keep `com.barclays.scp.eps.*` package names; defer rename to a later stage

If Option A is chosen:

| MCA1 Package | MCA2 Package |
|---|---|
| `com.barclays.scp.eps.*` | `com.barclays.mca.eps.*` |
| `com.barclays.scp.eps.audit.*` | `com.barclays.mca.eps.audit.*` |
| `com.barclays.scp.eps.bae.*` | `com.barclays.mca.eps.bae.*` |

If Option B is chosen, no package renaming is performed. The existing `com.barclays.scp.eps.*` packages are kept as-is. This does not affect framework migration correctness — MCA2 framework classes use `com.barclays.global.mca.*` packages regardless.

---

## Pattern 12: Testing

### MCA1 (Before)
```java
public class TestMyService extends GenericTestCase {
    Mock mockServiceManager;
    // JMock syntax: expects().method().will(returnValue())
}
```

### MCA2 (After)
```java
@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
class TestMyService {
    @Mock private APIServiceManager apiServiceManager;
    @Mock private RequestContextProvider contextProvider;
    @InjectMocks private MyServiceImpl service;

    @Test void testAction() {
        when(contextProvider.getIOLContext()).thenReturn(mockIol);
        // ... Mockito syntax
    }
}
```

**Static mock patterns (behavior-preservation):**

| Static Class | Strategy |
|---|---|
| `DateFactory` | `MockedStatic<DateFactory>` |
| `LocalityInfo` | `MockedStatic<LocalityInfo>` |
| `EpsServiceHelper` | `MockedStatic<EpsServiceHelper>` |
| `ReferenceData` | Cannot use `MockedStatic` — use `spy()` + `doReturn()` on caller |

### Migration Stub Tests (required for coverage)

Migration stubs in `migration/stubs/` must have their own test classes to maintain code coverage. Without these, coverage drops significantly because stubs can contain substantial code (e.g., `IOLContextAdapter`, `ReferenceDataServiceImpl`).

**POJO stubs** (e.g., `UserBean`, `CodedValueBean`, `CodeDecodeBean`, `RestConnectorRequestBean`, `RestConnectorResponseBean`):
```java
class TestUserBean {
    @Test void testDefaultConstructorInitializesInnerObjects() {
        UserBean userBean = new UserBean();
        assertNotNull(userBean.getUsingParty());
        assertNotNull(userBean.getLocation());
        assertNotNull(userBean.getChannel());
    }
    @Test void testSettersAndGetters() { /* exercise all fields */ }
    @Test void testUsingPartyEmployeeIdAsString() {
        UserBean.UsingParty usingParty = new UserBean.UsingParty();
        usingParty.setEmployeeId(6100171L);
        assertEquals("6100171", usingParty.getEmployeeIdAsString());
    }
}
```

**IOLContextAdapter** (most important — contains real mapping logic):
```java
@ExtendWith(MockitoExtension.class)
class TestIOLContextAdapter {
    @Mock private IOLSchema iolSchema;
    @Mock private UserContext userContext;
    @Mock private com.barclays.global.mca.libs.context.data.Channel channel;

    @Test void testToUserBeanFullContext() { /* all fields populated */ }
    @Test void testToUserBeanNullIol() { /* returns default UserBean */ }
    @Test void testToUserBeanNullUserContext() { /* returns default UserBean */ }
    @Test void testToUserBeanNonNumericEID() { /* parseLong returns 0 */ }
    @Test void testToUserBeanShortBUID() { /* BUID too short — defaults remain */ }
    @Test void testToUserBeanNonNumericBUID() { /* NumberFormatException caught */ }
    @Test void testToUserBeanNonNumericChannel() { /* parseInt returns 0 */ }
    @Test void testToUserBeanNullChannel() { /* channel defaults remain */ }
}
```

**Stubs with static API dependencies** (e.g., `ReferenceDataServiceImpl`):
```java
class TestReferenceDataServiceImpl {
    @Disabled("ReferenceData static initializer requires Spring ApplicationContext")
    @Test void testGetCodeDecodeBeans() { /* ... */ }
    // All methods @Disabled — ensures coverage intent documented
}
```

**Interface stubs** (`DataInterface`, `ReferenceDataHelper`, `ReferenceDataService`): No tests needed.

### Coverage Regression and Recovery (Pitfall 21)

Migration inherently drops code coverage below the `codeCoverageTask.ccLmit` threshold (typically 70%). This is expected — new stubs, new exception handling paths, @Disabled tests, and new ApplicationConfig all add untested instructions.

**Existing classes also need test updates:**
- Classes with **changed catch blocks** (e.g., `catch (Exception)` + `findCause()` replacing `catch (EpsApplicationException)`) need new error-path tests
- Classes with **changed constructors** (removed `MessageBeanHelper` parameter) need updated test setups
- **POJO beans** used in REST request/response flows need getter/setter tests
- **Large helper/utility classes** (1,000+ lines) are the dominant coverage drag — a single 1,800-line helper at 33% coverage can account for 74% of all missed instructions

**Coverage verification steps:**
```bash
# 1. Generate JaCoCo report (may fail codeCoverageTask — report still generated)
./gradlew test jacocoTestReport

# 2. Read CSV for per-class instruction counts
cat build/reports/jacoco/test/jacocoTestReport.csv

# 3. Calculate: SUM(INSTRUCTION_COVERED) / SUM(INSTRUCTION_MISSED + INSTRUCTION_COVERED) × 100

# 4. If below threshold, write more tests (see priority below) and repeat

# 5. Final validation — must pass codeCoverageTask gate
./gradlew clean build
```

**Recovery priority (highest ROI first):**
1. Large helper classes (10-20% gain per class)
2. Re-enable @Disabled tests with `MockedStatic` (3-8% gain)
3. Service impls with new exception handling (3-5% gain)
4. ApplicationConfig `@SpringBootTest` (1-3% gain)
5. POJO bean getter/setter tests (1-2% gain)

---

## Part I Amendment: Typed vs. Untyped Return Types

### Decision Criteria

| Criterion | Use Typed Wrappers | Use `Object` Pass-Through |
|---|---|---|
| Endpoint count | Few (< 10) | Many (10+) |
| Service inspects/transforms data | Yes — needs type safety | No — pure pass-through |
| Preserved business logic accesses response fields | Yes — typed access needed | No |
| OpenAPI documentation at this layer | Yes | No — downstream owns contract |

### Pattern 4a: Object Pass-Through (Pilot 2 Pattern)
```java
// Service interface
public interface AccountBalanceService {
    Object getHistoricBalance(Map<String, Object> requestBody);
}

// Controller
@PostMapping("/historicBalance")
public ResponseEntity<Object> getHistoricBalance(@RequestBody Map<String, Object> requestBody) {
    return ResponseEntity.ok(accountBalanceService.getHistoricBalance(requestBody));
}
```

### Pattern 4b: JsonNode Alternative
```java
Object result = apiServiceManager.callRestApiPOST(restClient, request, JsonNode.class);
```

**Default:** Use typed wrappers when preserved logic accesses response fields.
**Alternative:** Use `Object` for pure pass-through with many endpoints.

---

## Part J Amendment: Multi-Domain Project Structure

### Architecture
```
N Controllers -> N Services -> 1 shared APIServiceManager / RestClient
                             -> 1 shared UtilityMapper
                             -> 1 shared RestClientBean
```

### Package Structure
```
com.barclays.mca.eps.<project>/
    config/
        Application.java
        ApplicationConfig.java          # All beans
    controller/
            AccountBalanceController.java
            AccountSummaryController.java
    service/
        AccountBalanceService.java
        AccountSummaryService.java
    service/impl/
        AccountBalanceServiceImpl.java
        AccountSummaryServiceImpl.java
    mapper/
        BaeUtilityMapper.java           # Shared
    beans/
        BaeRestClientBean.java          # Shared
        RestConnectorRequest.java       # Shared
    migration/stubs/                    # Behavior-preservation stubs
```

### Migration Rules
- **Single-domain (< 3 services):** 1 Controller + 1 Service
- **Multi-domain (3+ services):** 1 Controller + 1 Service per domain, shared infrastructure
- All beans registered in single `ApplicationConfig`

---

## Part K Amendment: Caching Decision Tree

```
Does MCA1 source already implement caching?
├── YES → Carry forward as EHCache. Mark @MCA2-TEAM-ENHANCEMENT.
└── NO → Does project have shared reference/preload data?
    ├── YES (dropdowns, rule codes, config) → Consider adding EHCache (team decision).
    └── NO (all data is customer-specific/transactional) → Do NOT add caching.
```

**Do NOT cache:** per-customer balances, transaction data, real-time queries.
**Consider caching:** reference dropdowns, rule codes, slowly-changing lookups.
**Classification:** Team-level enhancement (DEC-024), not a migration requirement.

---

## Part L Amendment: Void / Fire-and-Forget Pattern

### When to Use
- Audit event writes
- Session/transient data cleanup
- Notification triggers
- Any side-effect-only operation

### Service Pattern
```java
public void auditPrint(Map<String, Object> requestBody) {
    IOLSchema iolContext = contextProvider.getIOLContext();
    RestConnectorRequest request = mapper.buildPostRequest(iolContext, Constants.AUDIT_API);
    request.setData(requestBody);
    try {
        apiServiceManager.callRestApiPOST(restClientBean.getRestClient(), request, Object.class);
    } catch (RestCallErrorException e) {
        mapper.handleServiceException(e);
    }
}
```

### Controller Pattern
```java
@PostMapping("/auditPrint")
public ResponseEntity<Void> auditPrint(@RequestBody Map<String, Object> requestBody) {
    service.auditPrint(requestBody);
    return ResponseEntity.ok().build();
}
```

---

## Part M Amendment: Minimum Test Matrix

### Required Test Files Per Project

| Test Category | Required Files | What to Test |
|---|---|---|
| **Controller tests** | 1 per controller | Happy path (200 OK + delegation). Error path (400/500). Use MockMvc. |
| **Service tests** | 1 per service impl | Happy path (REST delegation). Error path (`RestCallErrorException` handling). |
| **UtilityMapper test** | 1 per project | `buildHeadersFromIOL()` with valid/null IOL. `handleServiceException()` with 404/other. |
| **ApplicationConfig test** | 1 per project | Verify all beans created (Spring context loads). |
| **Mock data utility** | 1 per project (`MockData.java`) | Shared factory methods for test objects. |
| **Infrastructure tests** | 1 per `APIServiceManager` (if used) | GET + POST dispatch, error handling, URL construction. |

### Minimum Test Count Formula

```
Minimum test files = (N controllers × 1) + (N services × 1) + 3 (mapper + config + MockData)
                   + 1 per APIServiceManager (if used)
```

**Examples:**
- Pilot 1 (audit, 1 controller + 5 services): 1 + 5 + 3 = **9 test files minimum**
- Pilot 2 (BAE, 6 controllers + 6 services): 6 + 6 + 3 = **15 test files minimum**

### Minimum Test Methods Per File

| Test File Type | Min Happy-Path Tests | Min Error-Path Tests |
|---|---|---|
| Controller test | 1 per endpoint | 1 per endpoint |
| Service test | 1 per method | 1 per method |
| Mapper test | 3 (valid, null context, null sub-fields) | 2 (404 cause, non-404 cause) |
| Config test | 1 (context loads) | 0 |

---

## DEC Corrections Summary

| DEC | Correction | Impact |
|---|---|---|
| DEC-016 | `RestClient.callRest()` is framework (Option 1); `APIServiceManager` is team-level wrapper (Option 2); `MisClient` is tech debt MIS preservation (Option 3, requires `@EnableMisServiceClient`). Per-call choice. | Service dispatch pattern |
| DEC-017 | Controllers return `Response<T>` per `mca-api-template` | Response handling |
| DEC-018 | `mca-filter-contexts` removed after 1.0.003 — do not include | Dependencies |
| DEC-019 | Only 4 core libs declared; rest are transitive from `mca-eps-core` | Dependencies |
| DEC-020 | `EpsResponseBean` is MCA1 framework — no MCA2 translation; domain beans are plain POJOs | Response model |
| DEC-021 | `GlobalExceptionHandler` is team-level — not needed; framework auto-configures `ExceptionControllerAdvice` | Exception handling |
| DEC-022 | `RestClientsConfig` consolidated into `ApplicationConfig`; import only `ApplicationConfig` | Bootstrap |
| DEC-023 | Service consolidation is feature-team decision; preserve N-services by default | Service structure |
| DEC-024 | EHCache caching is team-level enhancement; apply only if MCA1 had caching | Caching |

---

## Application Properties

### Remove
```properties
spring.main.allow-circular-references=true
external.properties.MCA_FILTERS_EXCLUDE_PATH=/actuator/info
spring.main.allow-bean-definition-overriding=true
# All external.services.* properties
```

### Add
```properties
mca.eps.enabled=true
core.default.log-request-duration.enabled=true
core.default.log-request-duration.application-type=EPS
core.rest-template.socket-factory.dynamic-ssl.enabled=true
eps.validation.ignore-missing-schema=false
eps.iolschema.validation.enabled=true
eps.context.filter.exclude.paths=/actuator/**,/static/**
security.basic.enabled=false
management.security.enabled=false
core.default.oauth-filter.enabled=false
core.default.oauth-filter.exclude.paths=/actuator/**
logging.level.root=INFO
logging.level.com.barclays.global.mca=DEBUG
```

### RestClient Auto-Configuration (services.rest-clients.*)

Named `RestClient` beans are auto-configured from `services.rest-clients.*` properties by `RestClientBeanFactoryProcessor` in `mca-service-client-starter`. Each entry creates a named `RestClient` bean injectable via `@Qualifier`.

```properties
# Each key creates a named RestClient bean: @Qualifier("odsRefDataAPI") RestClient
services.rest-clients.odsRefDataAPI.root-uri=${ODS_REF_DATA_API_URL:http://localhost:8081}
services.rest-clients.odsRefDataAPI.connect-timeout=10000
services.rest-clients.odsRefDataAPI.read-timeout=30000
services.rest-clients.odsRefDataAPI.correlation-id-enabled=true
services.rest-clients.odsRefDataAPI.perf-log-enabled=true

services.rest-clients.colleagueeligibilityapi.root-uri=${COLLEAGUE_ELIGIBILITY_API_URL:http://localhost:8082}
services.rest-clients.colleagueeligibilityapi.connect-timeout=10000
services.rest-clients.colleagueeligibilityapi.read-timeout=30000
services.rest-clients.colleagueeligibilityapi.correlation-id-enabled=true
services.rest-clients.colleagueeligibilityapi.perf-log-enabled=true
```

**Injection pattern:**
```java
@Bean(name = "auditHelper")
public AuditHelper auditHelper(
        @Qualifier("odsRefDataAPI") RestClient odsRefDataRestClient,
        @Qualifier("colleagueeligibilityapi") RestClient colleagueEligibilityRestClient) {
    return new AuditHelper(..., odsRefDataRestClient, colleagueEligibilityRestClient);
}
```

**Mapping from MCA1:** Each `external.services.<name>.implementationClass = ...RestConnectorServiceImpl` with an `executeApi` method corresponds to one named RestClient. The `root-uri` replaces the endpoint URL previously resolved via MIS service locator.

---

## Correct MCA2 Package Names (Verified from JARs)

**IMPORTANT:** Use these exact package names. The MCA2 framework classes are NOT in the packages you might guess from the artifact names. These have been verified by inspecting the actual JAR contents in the gradle cache.

| Class | Correct Package |
|---|---|
| `MisClient` | `com.barclays.global.mca.extension.libs.services.mis.MisClient` |
| `EnableMisServiceClient` | `com.barclays.global.mca.extension.libs.services.mis.EnableMisServiceClient` |
| `MisServiceLocator` | `com.barclays.global.mca.extension.libs.services.mis.locator.MisServiceLocator` |
| `DefaultMisClientResponseHandler` | `com.barclays.global.mca.extension.libs.services.mis.handlers.DefaultMisClientResponseHandler` |
| `MisUserContextProvider` | `com.barclays.global.mca.extension.libs.services.mis.providers.MisUserContextProvider` |
| `RequestContextProvider` | `com.barclays.global.mca.libs.context.providers.RequestContextProvider` |
| `IOLSchema` | `com.barclays.global.mca.libs.context.data.IOLSchema` |
| `UserContext` (IOL) | `com.barclays.global.mca.libs.context.data.UserContext` |
| `Response` | `com.barclays.global.mca.libs.core.response.entity.Response` |
| `EnableExperienceAPI` | `com.barclays.global.mca.libs.eps.EnableExperienceAPI` |
| `RestClient` | `com.barclays.global.mca.rest.RestClient` |
| `ServiceCallResponse` | `com.barclays.global.mca.service.ServiceCallResponse` |
| `ApplicationException` | `com.barclays.global.mca.libs.core.exceptions.ApplicationException` |
| `GenericException` | `com.barclays.global.mca.libs.core.exceptions.GenericException` |
| `Message` | `com.barclays.global.mca.libs.core.response.entity.Message` |
| `NotFoundException` | `com.barclays.global.mca.libs.core.exceptions.NotFoundException` |
| `RequestException` | `com.barclays.global.mca.libs.core.exceptions.RequestException` |

### Change
```properties
spring.application.name=scp-eps-<name>  -->  spring.application.name=mca-eps-<name>
```

---

## Pattern 13: Process.json (Journey Definition)

### Overview

MCA2 uses `process.json` files as the single source of truth for journey definitions. In MCA2, these files:
- Must be located at `src/main/resources/processes/{processName}.json` (loaded by `ClasspathResourceProcessService`)
- Use the MCA2 field schema (see `docs/MCA2-EPS-Guide/2-Core-Frameworks/Process-System.md` for full spec)
- Reference the OAS spec via `apiDefinition.oas`

### Detection

```bash
# Find existing process/journey JSON files
find src/main/resources -name "*.json" -not -path "*/test/*" 2>/dev/null

# Check for MCA1 markers
grep -rn '"type".*:.*"mca1"\|"mcaType"\|"mca2ui"\|"fragmentFileContentRequested"\|"context"\s*:' src/main/resources/ --include="*.json"

# Check location — MCA2 requires processes/ subdirectory
ls src/main/resources/processes/ 2>/dev/null
```

### MCA1 (Before)

```json
// Location: src/main/resources/{name}.json  (root of resources — WRONG for MCA2)
{
  "process": {
    "id": "epsaudit/process/audit",
    "metaDataPresent": "true",
    "fragmentFileContentRequested": "false",
    "uiModuleName": "audit",
    "mcaType": "mca2",
    "mca2ui": "true",
    "endpoints": {
      "preload": {
        "uri": "/epsaudit/audit/v1/preloadScreen?cc=true",
        "method": "GET",
        "context": [
          "UserContext",
          "CustomerContext",
          "ConfigContext"
        ]
      }
    },
    "tasks": [
      {
        "id": "1",
        "name": "preloadScreen",
        "events": [...]
      }
    ]
  }
}
```

### MCA2 (After)

```json
// Location: src/main/resources/processes/{name}.json  (processes/ subdirectory — REQUIRED)
{
  "process": {
    "id": "{name}_v1",
    "uiModuleName": "{uiModule}",
    "metaDataPresent": "true",
    "endpoints": {
      "preload": {
        "uri": "/epsaudit/audit/v1/preloadScreen",
        "method": "GET",
        "contexts": [
          "UserContext",
          "CustomerContext",
          "ConfigContext"
        ]
      }
    },
    "tasks": [
      {
        "id": "AUD001",
        "name": "Audit Search Criteria Page",
        "events": [...]
      }
    ],
    "apiDefinition": {
      "oas": {
        "path": "oas/openapi.yaml",
        "version": "1.0.0",
        "oasEnabled": "true"
      }
    }
  }
}
```

### Migration Steps

1. **Move file**: `src/main/resources/{name}.json` → `src/main/resources/processes/{name}.json`
   - MCA2 `ClasspathResourceProcessService` only discovers process files in the `processes/` subdirectory
   - Delete the old file from root resources

2. **Update process ID**: Change from path-style (`epsaudit/process/audit`) to MCA2 format (`{name}_v{version}`, e.g., `audit_v1`)

3. **Remove MCA1 shim fields** (these are MCA1→MCA2 transition flags, not part of native MCA2 format):
   - Remove `"mcaType": "mca2"` — not a standard MCA2 field
   - Remove `"mca2ui": "true"` — not a standard MCA2 field
   - Remove `"fragmentFileContentRequested": "false"` — MCA1 field, not used in MCA2

4. **Rename `"context"` → `"contexts"`** (plural) on all endpoints:
   - MCA1 used `"context": [...]` (singular)
   - MCA2 spec uses `"contexts": [...]` (plural) — see Process-System.md field reference

5. **Remove `?cc=true`** from all endpoint URIs:
   - MCA1 appended `?cc=true` to signal context-chaining to the MCA1 proxy
   - MCA2 handles context injection via the `"contexts"` array on each endpoint — the query parameter is not needed

6. **Use semantic task IDs**: Change numeric IDs (`"1"`, `"2"`, `"3"`) to meaningful screen codes (e.g., `AUD001`, `AUD002`)
   - Update all `"task-id"` references in event transitions to match

7. **Add missing endpoints**: Ensure all controller endpoints are represented in the endpoints map

8. **Add `apiDefinition` block** referencing the OAS spec:
   ```json
   "apiDefinition": {
     "oas": {
       "path": "oas/openapi.yaml",
       "version": "1.0.0",
       "oasEnabled": "true"
     }
   }
   ```

9. **Remove `"type": "mca1"`** from any endpoint that has it — MCA2 endpoints do not set this flag

### Verification

```bash
# Verify file is in correct location
ls src/main/resources/processes/*.json

# Verify no MCA1 markers remain
grep -rn '"mcaType"\|"mca2ui"\|"fragmentFileContentRequested"\|"type".*"mca1"\|"cc=true"' src/main/resources/processes/ --include="*.json"

# Verify contexts (plural) is used, not context (singular)
# This should return matches (correct):
grep -rn '"contexts"' src/main/resources/processes/ --include="*.json"
# This should return zero matches (incorrect MCA1 form):
grep -rn '"context"\s*:' src/main/resources/processes/ --include="*.json"

# Verify old file is deleted
test ! -f src/main/resources/{name}.json && echo "CLEAN" || echo "OLD FILE STILL EXISTS"
```
