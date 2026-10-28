# SOAP/Axis 1.4 Test Migration Reference

## Overview

This document covers migration patterns for projects that use Apache Axis 1.4 SOAP web services. These projects have JAX-RPC generated code with specific testing constraints around exception types and mock setup.

**When to use this reference:** Any project with `javax.xml.rpc`, `org.apache.axis`, or WSDL-generated service classes.

---

## 1. Architecture of Axis 1.4 SOAP Clients

### Typical Class Hierarchy

```
javax.xml.rpc.Service (interface)
  └── PinViewRequestRetrieveXService (generated)
        └── PinViewRequestRetrieveXServiceLocator (impl)

java.rmi.Remote (interface)
  └── PinViewRequestRetrieveX (generated port interface)
        └── PinViewRequestRetrieveXSoapBindingStub (impl)
```

### Typical Client Pattern

```java
@Component
public class MyClient {
    @Autowired
    private MyHelper helper;

    private MyPort port;

    public MyResponse doWork(MyRequest request) throws RemoteException {
        setProxyClient();                    // Step 1: Get SOAP port
        try {
            return port.call(request);       // Step 2: Call SOAP service
        } catch (UseCaseException ex) {
            throw new ApiRequestException(...)  // Convert to API exception
        } catch (RemoteException ex) {
            throw new ApiServerException(...)   // Convert to API exception
        }
    }

    public void setProxyClient() throws ServerException {
        try {
            port = helper.getService().getPort(new URL(endPoint));
        } catch (ServiceException e) {
            throw new ServerException("Error in setProxyClient()");
        } catch (MalformedURLException e) {
            throw new ServerException("Malformed URL");
        }
    }
}
```

---

## 2. Exception Type Rules

### Rule 1: Interface Throws Clause is Enforced by Mockito

Mockito 5.x validates that mocked exceptions are declared in the method's `throws` clause.

```java
// JAX-RPC Service interface
public interface MyService extends javax.xml.rpc.Service {
    MyPort getMyPort() throws javax.xml.rpc.ServiceException;
    //                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    //                       ONLY ServiceException is valid for willThrow()
}

// Remote interface
public interface MyPort extends java.rmi.Remote {
    MyResponse call(MyRequest req)
        throws java.rmi.RemoteException, UseCaseException;
    //       ^^^^^^^^^^^^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^
    //       Both are valid for willThrow()
}
```

### Rule 2: Exception Conversion Chain

| Mock Throws | Implementation Catches | Implementation Rethrows | assertThrows Expects |
|-------------|----------------------|------------------------|---------------------|
| `UseCaseException` | `catch (UseCaseException)` | `ApiRequestException` | `ApiRequestException.class` |
| `RemoteException` | `catch (RemoteException)` | `ApiServerException` | `ApiServerException.class` |
| `ServiceException` | `catch (ServiceException)` in `setProxyClient()` | `ServerException` | `ServerException.class` |

### Rule 3: setProxyClient() Exceptions Bypass Main Try-Catch

```java
public MyResponse doWork(MyRequest request) throws RemoteException {
    setProxyClient();   // ← ServerException propagates directly (NOT caught below)
    try {
        // ...
    } catch (UseCaseException ex) {   // ← Does NOT catch ServerException
        throw new ApiRequestException(...);
    } catch (RemoteException ex) {    // ← ServerException IS a RemoteException subclass
        throw new ApiServerException(...);  // But setProxyClient is BEFORE try block
    }
}
```

**Important:** Even though `ServerException extends RemoteException`, the `setProxyClient()` call is BEFORE the try-catch block, so the exception propagates without being caught.

---

## 3. Test Migration Patterns

### Pattern 1: Service Locator Tests

```java
// Test that service locator can create a port
@Test
public void getPortTest() throws Exception {
    PinViewRequestRetrieveX port = serviceLocator.getPinViewRequestRetrieveX();
    Assertions.assertNotNull(port);
}

// Test that invalid arguments throw ServiceException
@Test
public void getPortNegativeTest() {
    Assertions.assertThrows(ServiceException.class, () -> {
        serviceLocator.getPort(null);
    });
}
```

### Pattern 2: SOAP Binding Stub Tests

```java
// Test that calling without endpoint throws RemoteException
@Test
public void createCallNegativeTest() {
    Assertions.assertThrows(RemoteException.class, () -> {
        stub.rtrv(request);  // No endpoint set → RemoteException
    });
}

// Test with endpoint set (still fails due to no server)
@Test
public void createCallTest() {
    Assertions.assertThrows(RemoteException.class, () -> {
        stub._setProperty(Stub.ENDPOINT_ADDRESS_PROPERTY, ENDPOINT_URL);
        stub.rtrv(request);
    });
}
```

### Pattern 3: Client Mock Tests - Success Path

```java
@Test
public void getDataSuccessTest() throws Exception {
    // Set up mock chain
    given(helper.getService()).willReturn(mockService);
    given(mockService.getPort(any())).willReturn(mockPort);
    given(mockPort.call(any())).willReturn(mockResponse);

    // Call and verify
    MyResponse response = client.doWork(request);
    assertEquals(expected, response.getData());
}
```

### Pattern 4: Client Mock Tests - UseCaseException Path

```java
@Test
public void useCaseExceptionTest() throws Exception {
    // Set up mock chain - UseCaseException from port
    given(helper.getService()).willReturn(mockService);
    given(mockService.getPort(any())).willReturn(mockPort);
    given(mockPort.call(any())).willThrow(new UseCaseException());

    // Implementation catches UseCaseException → throws ApiRequestException
    Assertions.assertThrows(ApiRequestException.class, () -> {
        client.doWork(request);
    });
}
```

### Pattern 5: Client Mock Tests - RemoteException Path

```java
@Test
public void remoteExceptionTest() throws Exception {
    // Set up mock chain - RemoteException from port
    given(helper.getService()).willReturn(mockService);
    given(mockService.getPort(any())).willReturn(mockPort);
    given(mockPort.call(any())).willThrow(new RemoteException("test"));

    // Implementation catches RemoteException → throws ApiServerException
    Assertions.assertThrows(ApiServerException.class, () -> {
        client.doWork(request);
    });
}
```

### Pattern 6: Client Mock Tests - setProxyClient ServiceException Path

```java
@Test
public void setProxyClientServiceExceptionTest() throws Exception {
    // Mock the service to throw ServiceException when getting port
    given(helper.getService()).willReturn(mockService);
    given(mockService.getPort(any()))
        .willThrow(new ServiceException("test"));

    // setProxyClient catches ServiceException → throws ServerException
    // ServerException propagates BEFORE main try-catch block
    Assertions.assertThrows(ServerException.class, () -> {
        client.doWork(request);
    });
}
```

---

## 4. Common Mistakes and Fixes

### Mistake 1: Mocking ServiceException on Remote Interface

```java
// ❌ WRONG - Remote interface only declares RemoteException + UseCaseException
given(port.call(any())).willThrow(new ServiceException("test"));
// → MockitoException: Checked exception is invalid for this method!

// ✅ FIX - Use RemoteException
given(port.call(any())).willThrow(new RemoteException("test"));
```

### Mistake 2: Mocking RemoteException on Service Interface

```java
// ❌ WRONG - Service interface only declares ServiceException
given(service.getPort(any())).willThrow(new RemoteException("test"));
// → MockitoException: Checked exception is invalid for this method!

// ✅ FIX - Use ServiceException
given(service.getPort(any())).willThrow(new ServiceException("test"));
```

### Mistake 3: Expecting ApiServerException from setProxyClient

```java
// ❌ WRONG - setProxyClient throws ServerException, not ApiServerException
Assertions.assertThrows(ApiServerException.class, () -> {
    client.doWork(request);  // When setProxyClient fails
});

// ✅ FIX - Expect ServerException
Assertions.assertThrows(ServerException.class, () -> {
    client.doWork(request);
});
```

### Mistake 4: Chaining Mocks Without Intermediate Setup

```java
// ❌ WRONG - helper.getService() returns null mock
given(helper.getService().getPort(any()))
    .willThrow(new ServiceException("test"));

// ✅ FIX - Set up intermediate mock
given(helper.getService()).willReturn(mockService);
given(mockService.getPort(any()))
    .willThrow(new ServiceException("test"));
```

### Mistake 5: Missing Import After Changing Exception Type

```java
// After changing from ApiServerException to ServerException:
import java.rmi.ServerException;  // ← Don't forget this!

// After changing to ServiceException:
import javax.xml.rpc.ServiceException;  // ← Don't forget this!
```

---

## 5. Diagnostic Workflow

When a SOAP test fails after migration, follow this workflow:

```
1. READ the error message
   ├── MockitoException "Checked exception is invalid"
   │   → Go to Step 2A
   ├── AssertionFailedError "expected X but was Y"
   │   → Go to Step 2B
   └── Other error
       → Go to Step 2C

2A. MockitoException:
    1. Find the willThrow() line
    2. Find the method being mocked
    3. Find the interface that declares that method
    4. Read the throws clause
    5. Change willThrow to use a declared exception

2B. Wrong Exception Type:
    1. Note expected vs actual exception
    2. Read the implementation method being tested
    3. Trace: what does mock throw → what does catch block do → what gets rethrown
    4. Change assertThrows to use the actually-thrown type

2C. Other:
    1. Read the full stack trace
    2. Check if mock setup is correct
    3. Check if intermediate mocks are set up for chained calls
```

---

## 6. Required Dependencies

SOAP/Axis tests need these imports available:

```java
import java.rmi.RemoteException;
import java.rmi.ServerException;
import javax.xml.rpc.ServiceException;
import javax.xml.rpc.Stub;
import org.apache.axis.AxisFault;
import org.apache.axis.client.Call;
```

Ensure `axis` dependency is present in `build.gradle`:
```gradle
implementation 'axis:axis:1.4'
implementation 'javax.xml.rpc:javax.xml.rpc-api:1.1.2'
```

**Note:** `javax.xml.rpc` does NOT migrate to `jakarta.xml.rpc` - there is no Jakarta equivalent. Keep the javax package for JAX-RPC/Axis 1.4.

---

## 7. Checklist for SOAP Test Migration

- [ ] Identify all SOAP test classes (search for `ServiceException`, `RemoteException`, `Stub`, `AxisFault`)
- [ ] For each test class, identify the interfaces being mocked
- [ ] Read each interface's throws clauses
- [ ] Verify all `willThrow()` exceptions match interface declarations
- [ ] Trace exception conversion chains in implementation code
- [ ] Verify all `assertThrows()` exception types match what implementation actually throws
- [ ] Set up intermediate mocks for chained calls
- [ ] Add missing imports (ServerException, ServiceException)
- [ ] Run tests per-class to verify: `$GRADLE_CMD test --tests "*.MyTest" -x barclaysApiGenerate`

---

**Document Version:** 1.0
**Date:** 2026-02-17
**Related:** [Test Migration Specification](test_migration_specification.md), [Lessons Learned - DebitcardPins](../lessons_learnt/debitcardpins_iapi.md)
