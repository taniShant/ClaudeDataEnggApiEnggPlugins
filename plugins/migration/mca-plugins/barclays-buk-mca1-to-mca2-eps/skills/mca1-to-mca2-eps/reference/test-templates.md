# MCA2 Test Templates

Pre-built templates for common test patterns after MCA1 to MCA2 migration. The agent fills in project-specific details (class names, method names, mock returns) rather than writing from scratch.

---

## Template 1: Controller Test (MockMvc)

```java
package {PACKAGE}.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.barclays.global.mca.libs.response.Response;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.bean.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest({CONTROLLER_CLASS}.class)
class {CONTROLLER_CLASS}Test {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private {SERVICE_CLASS} service;

    @Test
    void shouldReturnSuccessResponse() throws Exception {
        // Arrange
        {RESPONSE_TYPE} responseData = new {RESPONSE_TYPE}();
        // TODO: populate responseData fields
        when(service.{METHOD_NAME}(any())).thenReturn(responseData);

        // Act & Assert
        mockMvc.perform(post("{ENDPOINT_PATH}")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"key\": \"value\"}"))  // TODO: replace with actual request body
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data").exists());
    }

    @Test
    void shouldReturnErrorOnServiceFailure() throws Exception {
        // Arrange
        when(service.{METHOD_NAME}(any()))
                .thenThrow(new RuntimeException("Service error"));

        // Act & Assert
        mockMvc.perform(post("{ENDPOINT_PATH}")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"key\": \"value\"}"))
                .andExpect(status().isInternalServerError());
    }
}
```

---

## Template 2: Service Test (Mockito, happy + error)

```java
package {PACKAGE}.service.impl;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

import com.barclays.global.mca.libs.context.IOLSchema;
import com.barclays.global.mca.libs.context.RequestContextProvider;
import com.barclays.global.mca.libs.core.exceptions.ApplicationException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;

@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
class {SERVICE_CLASS}Test {

    @Mock
    private RequestContextProvider contextProvider;

    @Mock
    private IOLSchema iolSchema;

    // TODO: add other mocks (RestClient, helper classes, etc.)

    private {SERVICE_CLASS} service;

    @BeforeEach
    void setUp() {
        when(contextProvider.getIOLContext()).thenReturn(iolSchema);
        // TODO: set up IOL sub-contexts if needed
        // when(iolSchema.getUserContext()).thenReturn(mockUserContext);

        service = new {SERVICE_CLASS}(contextProvider /* , other deps */);
    }

    @Test
    void shouldProcessSuccessfully() {
        // Arrange
        // TODO: set up mock returns for dependencies

        // Act
        var result = service.{METHOD_NAME}(/* args */);

        // Assert
        assertNotNull(result);
        // TODO: assert specific fields
    }

    @Test
    void shouldThrowApplicationExceptionOnError() {
        // Arrange
        // TODO: mock dependency to simulate error

        // Act & Assert
        assertThrows(ApplicationException.class, () -> {
            service.{METHOD_NAME}(/* args */);
        });
    }
}
```

---

## Template 3: Service Test with findCause (MisClient error path)

Use this template when the service calls MisClient and has `catch (Exception) + findCause()` blocks.

```java
@Test
void shouldHandleWrappedCheckedException() {
    // MisClient.reduce() wraps checked exceptions in RuntimeException
    // Simulate: RuntimeException → ServiceInvalidException (checked)
    {CHECKED_EXCEPTION_CLASS} checkedException =
            new {CHECKED_EXCEPTION_CLASS}("{ERROR_CODE}", "{ERROR_MSG}");

    // TODO: mock the call site that triggers the exception
    when(/* dependency call */).thenThrow(new RuntimeException(checkedException));

    // Act & Assert — expect the service to translate and re-throw
    ApplicationException thrown = assertThrows(ApplicationException.class, () -> {
        service.{METHOD_NAME}(/* args */);
    });
    assertEquals("{ERROR_CODE}", thrown.getMessage().getCode());
}

@Test
void shouldRethrowUnexpectedExceptions() {
    // Simulate unexpected RuntimeException (not a wrapped checked exception)
    when(/* dependency call */).thenThrow(new RuntimeException("unexpected"));

    // Act & Assert
    assertThrows(RuntimeException.class, () -> {
        service.{METHOD_NAME}(/* args */);
    });
}
```

---

## Template 4: Large Helper/Utility Targeted Test

For helpers with 1,000+ lines, test the most-used public methods rather than full coverage. Focus on methods called by services (highest ROI).

```java
package {PACKAGE}.common.helper;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;

@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
class {HELPER_CLASS}Test {

    private {HELPER_CLASS} helper;

    // Static mocks for MCA1 utility classes
    private MockedStatic<DateFactory> dateFactoryMock;
    private MockedStatic<LocalityInfo> localityInfoMock;

    @BeforeEach
    void setUp() {
        dateFactoryMock = Mockito.mockStatic(DateFactory.class);
        dateFactoryMock.when(DateFactory::getDate).thenReturn(new java.util.Date());

        localityInfoMock = Mockito.mockStatic(LocalityInfo.class);
        localityInfoMock.when(LocalityInfo::getLocality).thenReturn("UK");

        helper = new {HELPER_CLASS}(/* constructor args */);
    }

    @org.junit.jupiter.api.AfterEach
    void tearDown() {
        localityInfoMock.close();
        dateFactoryMock.close();
    }

    // --- Target the most-used public methods ---

    @Test
    void shouldPopulateRequestDto() {
        // TODO: test the primary data-assembly method
        var result = helper.{POPULATE_METHOD}(/* args */);
        assertNotNull(result);
    }

    @Test
    void shouldPopulateRequestDtoWithNullInput() {
        // Null-safety test
        var result = helper.{POPULATE_METHOD}(null);
        assertNotNull(result);  // or assertThrows if expected
    }

    @Test
    void shouldValidateInput() {
        // TODO: test validation method with valid input
    }

    @Test
    void shouldRejectInvalidInput() {
        // TODO: test validation method with invalid input
        assertThrows(ApplicationException.class, () -> {
            helper.{VALIDATE_METHOD}(/* invalid args */);
        });
    }

    // --- ReferenceData: cannot use MockedStatic, use spy ---

    @Test
    void shouldHandleReferenceDataLookup() {
        {HELPER_CLASS} spyHelper = Mockito.spy(helper);
        doReturn("DECODED_VALUE").when(spyHelper).retrieveDecodeValue(any(), any());

        String result = spyHelper.retrieveDecodeValue("TABLE", "CODE");
        assertEquals("DECODED_VALUE", result);
    }
}
```

---

## Template 5: ApplicationConfig Context Test

```java
package {PACKAGE}.config;

import static org.junit.jupiter.api.Assertions.assertNotNull;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.ApplicationContext;

@SpringBootTest
class ApplicationConfigTest {

    @Autowired
    private ApplicationContext context;

    @Test
    void contextLoads() {
        assertNotNull(context);
    }

    @Test
    void beansAreRegistered() {
        // TODO: verify key beans are present
        // assertNotNull(context.getBean({SERVICE_CLASS}.class));
        // assertNotNull(context.getBean({CONTROLLER_CLASS}.class));
    }
}
```

---

## Template 6: POJO Bean Test (batch getter/setter)

For beans used in REST responses/requests. Low effort, moderate coverage gain.

```java
package {PACKAGE}.beans;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

class {BEAN_CLASS}Test {

    @Test
    void shouldGetAndSetAllFields() {
        {BEAN_CLASS} bean = new {BEAN_CLASS}();

        // TODO: for each field, set and assert
        // bean.setFieldName("value");
        // assertEquals("value", bean.getFieldName());
    }

    @Test
    void shouldHandleNullFields() {
        {BEAN_CLASS} bean = new {BEAN_CLASS}();
        // All fields should be null/default initially
        // assertNull(bean.getFieldName());
    }
}
```

---

## Template 7: MockData Utility

Shared test data factory used across all test classes.

```java
package {PACKAGE}.test;

import com.barclays.global.mca.libs.context.IOLSchema;
import com.barclays.global.mca.libs.context.data.Channel;
import com.barclays.global.mca.libs.context.data.UserContext;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

public class MockData {

    public static IOLSchema createMockIOLSchema() {
        IOLSchema iolSchema = mock(IOLSchema.class);
        UserContext userContext = mock(UserContext.class);
        Channel channel = mock(Channel.class);

        when(iolSchema.getUserContext()).thenReturn(userContext);
        when(userContext.getChannel()).thenReturn(channel);
        // TODO: add project-specific user context fields
        // when(userContext.getUserId()).thenReturn("TESTUSER");
        // when(userContext.getStaffId()).thenReturn("12345");

        return iolSchema;
    }

    // TODO: add factory methods for project-specific test data
    // public static {REQUEST_DTO} createSampleRequest() { ... }
    // public static {RESPONSE_DTO} createSampleResponse() { ... }
}
```

---

## Usage Guide for Agent

When generating tests for a migrated project:

1. **Read this file first** — pick the matching template per class type
2. **Replace placeholders** — `{PACKAGE}`, `{SERVICE_CLASS}`, `{METHOD_NAME}`, etc.
3. **Fill in TODOs** — mock returns, assertions, and test data specific to the project
4. **Write ALL tests in one batch** before running `./gradlew test` — do not iterate per file
5. **Use `analyze-coverage-gaps.sh`** after the first run to identify remaining gaps
