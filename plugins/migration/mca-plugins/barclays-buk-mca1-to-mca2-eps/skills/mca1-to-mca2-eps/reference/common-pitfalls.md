# Common Pitfalls (Extended) — Behavior-Preservation Strategy

This file contains additional migration pitfalls (11-18) beyond the top 10 in SKILL.md.

## Pitfall 11: Missing @MCA2-* markers
Every block of preserved logic needs a marker. Missing markers make it impossible for the team to review and plan future refactoring. Run `grep -r "@MCA2-" src/main/` to verify coverage matches the number of preserved methods.

## Pitfall 12: scp-eps-libs-customer transitively pulls scp-eps-core-comm
Even after removing `scp-eps-core-comm` directly, keeping `scp-eps-libs-customer` re-introduces it via transitive dependencies. Must remove it AND create local stubs for its types. See `reference/migration-stubs.md`.

## Pitfall 13: Static class initializer failures in tests
MCA1 utility classes (`DateFactory`, `LocalityInfo`, `ReferenceData`) trigger `ServiceLocator` or `PropertyLocatorLDAPImpl` static initializers that require a Spring `ApplicationContext`. In unit tests (no Spring context), these cause `ExceptionInInitializerError` or cascading `NoClassDefFoundError`. Fix with `MockedStatic<DateFactory>` and `MockedStatic<LocalityInfo>`. Exception: `ReferenceData` cannot be mocked with `MockedStatic` — use `Mockito.spy()` + `doReturn()` on the calling method. See `reference/test-migration-guide.md`.

## Pitfall 14: EpsResponseBean, EpsApplicationException, MessageBeanHelper — graduate stubs to MCA2 types

These three MCA1 stubs have direct MCA2 replacements and should be **graduated** (deleted) rather than kept permanently:

| Stub | MCA2 Replacement | Graduation Steps |
|---|---|---|
| `EpsResponseBean` | Plain POJO (no base class) | Remove `extends EpsResponseBean` from all domain beans. Add `implements Serializable` if the original was serializable. Controllers return `Response<T>`. |
| `EpsApplicationException` | `ApplicationException` (`com.barclays.global.mca.libs.core.exceptions`) | Replace `throw new EpsApplicationException(...)` with `throw new ApplicationException(Message.create(code, title))`. Replace `catch (EpsApplicationException)` with cause-chain walking (see Pitfall 19). |
| `MessageBeanHelper` | `ApplicationException(Message)` thrown directly | Remove `MessageBeanHelper` field/constructor param. Replace error DTO population with `throw new ApplicationException(Message.create(code, title))`. The framework `ExceptionControllerAdvice` auto-maps exceptions to error responses. |

**When to graduate:** During or immediately after the initial migration pass. These stubs add no value since MCA2 provides direct equivalents.

**Fallback:** If business logic heavily calls `response.getMessages()`/`addMessage()` and is too intertwined to refactor, keep the stub temporarily and plan graduation in a follow-up pass.

## Pitfall 15: mca-filter-contexts does not exist
Removed from the MCA2 framework after version 1.0.003 (DEC-018). Do not include it in build.gradle. `mca-filter-core` is a transitive dependency from `mca-eps-core` — no explicit declaration needed.

## Troubleshooting

### Build fails after Phase 2 (dependency resolution)
**Error:** `Could not resolve com.barclays.global.mca:mca-eps-core`
**Cause:** Wrong group ID or missing BOM.
**Solution:** Read `reference/dependency-mapping.md` and use exact coordinates. Ensure `mca-dependencies:{MCA2_BOM}` (resolved from Nexus; default: 2.3.021) BOM is declared.

### Tests fail with ExceptionInInitializerError
**Error:** `java.lang.ExceptionInInitializerError` in `ServiceLocator` or `PropertyLocatorLDAPImpl`
**Cause:** MCA1 static initializers require Spring ApplicationContext not present in unit tests.
**Solution:** Add `MockedStatic<DateFactory>` and `MockedStatic<LocalityInfo>`. See `reference/test-migration-guide.md`.

### Build fails with OutputDirectoryProvider not available
**Error:** `OutputDirectoryProvider not available` during test execution
**Cause:** JUnit platform version mismatch after Spring Boot 3.3+ upgrade.
**Solution:** Add `testRuntimeOnly 'org.junit.platform:junit-platform-launcher'` to build.gradle.

### Application fails to start — circular dependency
**Error:** `The dependencies of some of the beans in the application context form a cycle`
**Cause:** MCA1 used `allow-circular-references=true`. MCA2 uses constructor injection which exposes cycles.
**Solution:** Break the cycle by extracting a shared dependency into its own `@Bean` method, or use `@Lazy` on one constructor parameter.

## Pitfall 16: Missing @EnableMisServiceClient for Option 3 MisClient

If any `ServiceManager.doService()` call site uses Option 3 (MisClient), the Application class **must** have `@EnableMisServiceClient` and `mca-mis-client` must be in build.gradle. Without these, the `MisClient` bean will not be registered and the application will fail at startup with a `NoSuchBeanDefinitionException`.

**Fix:** Add `@EnableMisServiceClient` to Application.java and `implementation "com.barclays.global.mca:mca-mis-client"` to build.gradle.

## Pitfall 17: Lambda effectively-final variables in MisClient callService()

When converting `ServiceManager.doService(name, method, requestDto, userBean)` to `misClient.callService(svc -> svc.method(uc, requestDto)).reduce()`, the `requestDto` variable must be **effectively final** (assigned exactly once). If the original MCA1 code declares `requestDto = null` and then assigns it inside a conditional block, the lambda will fail to compile.

**Symptom:** `local variables referenced from a lambda expression must be final or effectively final`

**Fix:** Declare the variable with `final` at the point of assignment, or restructure so it is assigned exactly once:
```java
// WRONG — not effectively final:
GetOnlineAuditDataRequestDto requestDto = null;
requestDto = helper.populateRequestDto(params);  // second assignment
misClient.callService(svc -> svc.method(uc, requestDto)).reduce();  // compile error

// CORRECT — effectively final:
final GetOnlineAuditDataRequestDto requestDto = helper.populateRequestDto(params);
misClient.callService(svc -> svc.method(uc, requestDto)).reduce();  // OK
```

## Pitfall 18: @SpringBootApplication scanBasePackages when Application class is in a sub-package

If the `SpringBootWebApplication` (or `Application`) class is in a sub-package like `com.barclays.scp.eps.audit.config`, Spring Boot's default component scan will only scan that sub-package and below. Controllers, services, and components in sibling packages (e.g., `com.barclays.scp.eps.audit.controller`) will NOT be found.

**Symptom:** `404 Not Found` for all endpoints, or `NoSuchBeanDefinitionException` for services/controllers.

**Fix:** Add `scanBasePackages` to `@SpringBootApplication`:
```java
@SpringBootApplication(scanBasePackages = "com.barclays.scp.eps.audit")
@EnableExperienceAPI
public class SpringBootWebApplication { ... }
```

### MCA2 filters not activating
**Error:** `@IOLContext` returns null, context filters not running
**Cause:** Missing `@EnableExperienceAPI` on the main Application class.
**Solution:** Add `@EnableExperienceAPI` annotation. This activates all MCA2 EPS filters, context resolution, exception handling, and response assembly.

## Pitfall 19: MisClient.reduce() wraps checked exceptions — cannot catch directly

`MisClient.callService(svc -> svc.method(uc, dto)).reduce()` wraps checked exceptions (e.g., `NoRecordsFoundException`, `ServiceInvalidException`) from the EBS service in unchecked exception wrappers. You **cannot** use `catch (NoRecordsFoundException nrfe)` because `reduce()` doesn't declare checked exceptions — the compiler rejects it with `exception is never thrown in body of corresponding try statement`.

**Symptom:** `error: exception NoRecordsFoundException is never thrown in body of corresponding try statement`

**Fix:** Use `catch (Exception exception)` and walk the cause chain with `findCause()`:
```java
} catch (Exception exception) {
    NoRecordsFoundException nrfe = findCause(exception, NoRecordsFoundException.class);
    if (nrfe != null) {
        // Handle the specific checked exception
        throw new ApplicationException(
            Message.create(nrfe.getCode(), nrfe.getMessage()), nrfe);
    }
    // Re-throw anything else
    throw exception instanceof RuntimeException
        ? (RuntimeException) exception : new RuntimeException(exception);
}

@SuppressWarnings("unchecked")
private static <T extends Throwable> T findCause(Throwable t, Class<T> type) {
    while (t != null) {
        if (type.isInstance(t)) return (T) t;
        t = t.getCause();
    }
    return null;
}
```

**Note:** In MCA1, checked exceptions were wrapped in `EpsApplicationException`. In MCA2 with MisClient, they are wrapped differently by `reduce()`. The `findCause()` pattern handles both cases.

## Pitfall 20: Mockito rejects checked exceptions from methods that don't declare them

When testing MisClient-wrapped code, Mockito validates that `when(...).thenThrow(exception)` is compatible with the mocked method's throws clause. If you try to throw a checked exception (e.g., `ServiceInvalidException`) from a method that doesn't declare it (e.g., `helper.validateSearchCriteria()`), Mockito throws:

**Symptom:** `org.mockito.exceptions.base.MockitoException: Checked exception is invalid for this method!`

**Fix:** Wrap the checked exception in a `RuntimeException` (simulating what MisClient.reduce() does):
```java
// WRONG — Mockito rejects:
when(helper.validateSearchCriteria(any(), any()))
    .thenThrow(new ServiceInvalidException("error"));

// CORRECT — wrap in RuntimeException:
when(helper.validateSearchCriteria(any(), any()))
    .thenThrow(new RuntimeException(new ServiceInvalidException("error")));
// Then in the test assertion, expect RuntimeException (or whatever the catch block re-throws)
```

## Pitfall 21: Coverage regression during migration — codeCoverageTask gate failure

Migration inherently drops code coverage from pre-migration levels (often 80-95%) to well below the `codeCoverageTask.ccLmit` threshold (typically 70%). This happens because:

**Causes of coverage regression:**
1. **New stub classes** — `IOLContextAdapter`, POJO stubs, static-API stubs add instruction count without tests
2. **New code paths from exception handling** — `findCause()` patterns, new catch blocks for `ApplicationException`, cause-chain walking add branches that aren't covered by existing tests
3. **@Disabled tests** — Tests disabled due to static initializer issues (Pitfall 13) remove coverage for those code paths. Each @Disabled test on a service class can drop coverage by several percentage points
4. **New ApplicationConfig** — A Spring `@Configuration` class with multiple `@Bean` methods has 0% coverage without a `@SpringBootTest`
5. **Changed constructors** — Migration changes constructor signatures (removing `MessageBeanHelper`, adding `RequestContextProvider`), so existing test setups break or test different paths
6. **Large helper classes dominate metrics** — A single 1,800-line helper class at 33% coverage can account for 74% of all missed instructions, making it the dominant blocker

**Symptom:** `./gradlew clean build` fails with:
```
Incremental Code Coverage rate is: 42.86%, the current set limit is 70%
```

**The `codeCoverageTask` gate:** The DevOps plugin configures `codeCoverageTask.ccLmit = 70` (or similar). This runs after `test` and fails the build if JaCoCo instruction coverage is below the threshold. The JaCoCo report itself is still generated — only the coverage gate fails.

**Coverage recovery strategy (highest ROI first):**

| Priority | Target | Typical Coverage Gain | Approach |
|---|---|---|---|
| 1 | Large helper/utility classes (1,000+ lines) | 10-20% overall | Write targeted tests for most-used methods. These classes have the highest instruction count and dominate the denominator. |
| 2 | Re-enable @Disabled tests | 3-8% overall | Use `MockedStatic<DateFactory>` and `MockedStatic<LocalityInfo>` to bypass static initializers. Exception: `ReferenceData` cannot use MockedStatic. |
| 3 | Service impls with new exception handling | 3-5% overall | Add error-path tests for new `catch (Exception)` + `findCause()` blocks and `ApplicationException` throws. |
| 4 | ApplicationConfig | 1-3% overall | Write `@SpringBootTest(classes = SpringBootWebApplication.class)` context-loads test. |
| 5 | POJO bean tests | 1-2% overall | Test getters/setters for all beans. Low effort per test but many beans needed. |

**Diagnostic commands:**
```bash
# Generate JaCoCo report (may fail codeCoverageTask — report still generated)
./gradlew test jacocoTestReport

# Read CSV for per-class analysis
cat build/reports/jacoco/test/jacocoTestReport.csv

# Calculate overall instruction coverage
# Sum INSTRUCTION_COVERED / (INSTRUCTION_MISSED + INSTRUCTION_COVERED) × 100
```

**Fix:** Write tests following the priority order above until `./gradlew clean build` passes the `codeCoverageTask` gate. Focus on the largest uncovered classes first — a single well-tested helper class can swing overall coverage by 15-20 percentage points.
