# JMock to Mockito Test Migration Guide

## Framework Replacement

| JMock | Mockito |
|---|---|
| `extends GenericTestCase` | `@ExtendWith(MockitoExtension.class)` |
| `import com.barclays.scp.eps.testcase.GenericTestCase` | `import org.mockito.junit.jupiter.MockitoExtension` |
| `this.mock(Foo.class)` | `@Mock Foo foo` (field annotation) |
| `JUnit4Mockery` | DELETE entirely |
| `ClassImposteriser.INSTANCE` | DELETE (Mockito mocks concrete classes natively) |
| `this.getUserBean()` | `TestSupport.createTestUserBean()` |

## Expectation Translation

### Simple Return Value
```java
// JMock
mock.expects(once()).method("getValue").will(returnValue("result"));

// Mockito
when(mock.getValue()).thenReturn("result");
```

### With Arguments
```java
// JMock
mock.expects(once()).method("process").with(eq("input")).will(returnValue(output));

// Mockito
when(mock.process("input")).thenReturn(output);
```

### Any Arguments
```java
// JMock
mock.expects(once()).method("process").withAnyArguments().will(returnValue(output));

// Mockito
when(mock.process(any())).thenReturn(output);
```

### Multiple calls
```java
// JMock
mock.expects(atLeastOnce()).method("getStatus").will(returnValue("OK"));

// Mockito
when(mock.getStatus()).thenReturn("OK");  // Mockito returns same value by default for all calls
```

### Void Methods
```java
// JMock
mock.expects(once()).method("save").with(ANYTHING);

// Mockito
// No setup needed - Mockito void methods do nothing by default
// Verify after: verify(mock).save(any());
```

### Exception Throwing
```java
// JMock
mock.expects(once()).method("process").will(throwException(new RuntimeException()));

// Mockito
when(mock.process(any())).thenThrow(new RuntimeException());
```

## TestSupport Utility

Replace `GenericTestCase.getUserBean()` with a static utility:

```java
package com.barclays.scp.eps.audit.test;

import com.barclays.scp.eps.common.beans.UserBean;

public class TestSupport {
    public static UserBean createTestUserBean() {
        // Construct UserBean programmatically
        // Match the structure from the original GenericTestCase
        UserBean userBean = new UserBean();
        // Set required fields...
        return userBean;
    }
}
```

## MockedStatic Patterns for MCA1 Static Utilities

MCA1 apps use several static utility classes that trigger `ServiceLocator` or `PropertyLocatorLDAPImpl` static initializers requiring a Spring `ApplicationContext`. In unit tests (no Spring context), these cause `ExceptionInInitializerError` or cascading `NoClassDefFoundError`. The fix is `MockedStatic` (Mockito 4.x+).

### Pattern: MockedStatic in setUp/tearDown (class-wide)

Use when many tests in a class hit the same static call.

```java
@ExtendWith(MockitoExtension.class)
public class TestMyService {
    private MockedStatic<EpsServiceHelper> epsServiceHelperMock;
    private MockedStatic<DateFactory> dateFactoryMock;
    private MockedStatic<LocalityInfo> localityInfoMock;

    @BeforeEach
    public void setUp() {
        // ... create service under test ...

        UserBean userBean = TestSupport.getUserBean();
        epsServiceHelperMock = Mockito.mockStatic(EpsServiceHelper.class);
        epsServiceHelperMock.when(EpsServiceHelper::getUserBean).thenReturn(userBean);

        dateFactoryMock = Mockito.mockStatic(DateFactory.class);
        dateFactoryMock.when(DateFactory::getDate).thenReturn(new Date());

        localityInfoMock = Mockito.mockStatic(LocalityInfo.class);
        localityInfoMock.when(LocalityInfo::getLocality).thenReturn("UK");
    }

    @AfterEach
    public void tearDown() {
        localityInfoMock.close();   // close in reverse order
        dateFactoryMock.close();
        epsServiceHelperMock.close();
    }
}
```

### Pattern: try-with-resources (per-test)

Use when only a few tests in a class need the static mock.

```java
@Test
public void testValidateStaffIds() {
    try (MockedStatic<LocalityInfo> localityMock =
            Mockito.mockStatic(LocalityInfo.class)) {
        localityMock.when(LocalityInfo::getLocality).thenReturn("UK");

        // test body
        auditHelper.validateStaffIdsInLDAPBed(auditSearch, userBean);
    }
}
```

### Pattern: Uninstrumentable classes (spy + doReturn)

Some MCA1 classes (e.g., `ReferenceData`) have static initializers that fail **before** Mockito can instrument the class, causing `MockitoException: Cannot instrument class ... because it or one of its supertypes could not be initialized`. For these, mock at the caller level using `spy()`:

```java
@Test
public void testRetrieveDecodeValue() {
    // ReferenceData cannot be mocked with MockedStatic —
    // its static initializer fails before Mockito can intercept.
    AuditHelper spyHelper = Mockito.spy(auditHelper);
    Mockito.doReturn(null).when(spyHelper).retrieveDecodeValue(any(), any());

    String result = spyHelper.retrieveDecodeValue(null, null);
    assertTrue(result == null);
}
```

### Static classes requiring mocking

| Class | Trigger | Root Cause | MockedStatic works? |
|---|---|---|---|
| `EpsServiceHelper` | `getUserBean()` | ThreadLocal (stub) | Yes |
| `DateFactory` | `getDate()` | `WorkingDate.<clinit>` → `ServiceLocator` | Yes |
| `LocalityInfo` | `getLocality()` | `PropertyLocatorLDAPImpl` → `ApplicationContext` | Yes |
| `ReferenceData` | `getDecoder()` | `<clinit>` → `ServiceLocator` | **No** — use spy + doReturn |

### EpsApplicationException.ErrorDto in tests

After removing `EpsMessageBean`, tests that set up `errorDtosList` on `EpsApplicationException` must use the stub's `ErrorDto` inner class:

```java
// Before (MCA1 with EpsMessageBean)
List<EpsMessageBean> messageBeans = new ArrayList<>();
EpsMessageBean bean = new EpsMessageBean();
bean.setCode("553210");
messageBeans.add(bean);
epsApplicationException.setErrorDtosList(messageBeans);

// After (stub ErrorDto)
EpsApplicationException.ErrorDto errorDto = new EpsApplicationException.ErrorDto();
errorDto.setCode("553210");
List<EpsApplicationException.ErrorDto> errorDtos = new ArrayList<>();
errorDtos.add(errorDto);
epsApplicationException.setErrorDtosList(errorDtos);
```

### JUnit platform version alignment

After upgrading to Spring Boot 3.3+ with JUnit Jupiter 5.12, tests may fail with:

```
OutputDirectoryProvider not available
```

Fix by adding to `build.gradle`:
```gradle
testRuntimeOnly 'org.junit.platform:junit-platform-launcher'
```

## Migration Order

1. **AuditStub.java** - Shared fixture (may reference GenericTestCase)
2. **Bean tests** - Simple getter/setter tests (TestAuditSearch, etc.)
3. **Filter tests** - TestCrossScriptingFilter, TestRequestWrapper
4. **Helper tests** - AuditXMLHelperTest, TestAuditHelper
5. **Config tests** - TestAppConfig, TestDataSourceConfig
6. **Controller tests** - TestAuditControllerImpl
7. **Service tests** - TestAuditServiceImpl, TestLaunchSearchScreenServiceImpl, etc.
8. **Complex tests** - TestExecuteAuditSearchServiceImpl (largest)
