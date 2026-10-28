# MCA2 Call Patterns

MCA2 repos use `MisClient.callService()` and `BEMClient.callService()` instead of MCA1's `serviceDelegate.doService()`. The backend (EBS services, EDOs, JARs, mainframe transactions) is identical — only the client wrapper differs.

## Detection Markers

| Marker | Framework |
|--------|-----------|
| `ServiceDelegate` or `serviceDelegate` or `serviceManager` imports + `doService(` calls | MCA1 |
| `MisClient` or `BEMClient` imports + `callService(` calls | MCA2 |
| `@EnableMisServiceClient` or `@EnableBemServiceClient` annotation | MCA2 |
| Both MCA1 and MCA2 markers present | HYBRID |

## MCA2 MIS Call Pattern

```java
// 1. Config class — service registration (@Bean):
@Bean
public MisClient<EmployeeService> misEmployeeClient(MisServiceLocator serviceLocator,
                                                     ClientResponseHandler handler) {
    EmployeeService service = serviceLocator.findService("ExecutionContextEmployeeService", EmployeeService.class);
    return new MisClient<>(service, handler);
}

// 2. Usage — service call:
RetrieveServiceAccessDetailsByEmployeeIdResponseEdo response = employeeService
    .callService(svc -> svc.retrieveServiceAccessDetailsByEmployeeId(userContextEdo))
    .reduce();   // .reduce() is optional — .mapResponse() or direct ServiceCallResponse also valid
```

## MCA2 BEM Call Pattern

```java
// Same pattern but with BEMClient wrapping SOAP stubs:
BEMClient<NotificationService> bemClient = new BEMClient<>(soapService, handler);
bemClient.callService(svc -> svc.retrieveNotifications(ctx, request));
```

## Resolution Chain (MCA2 → same output as MCA1)

| Step | How to find it | Maps to |
|------|---------------|---------|
| EBS Service interface | `MisClient<ServiceInterface>` generic type parameter | Same as MCA1 SERVICE_NAME target |
| MTS Service name string | `serviceLocator.findService("name", Class)` in config | Same as MCA1 SERVICE_NAME value |
| Method name | Lambda body: `svc.methodName(...)` | Same as MCA1 method string |
| EBS JAR | Service interface import package | Same convention as MCA1 |
| Request/Response EDOs | Lambda method parameters + return type | Same EDO classes |

## Real Example (from mca-eps-strategicidentify)

**3 MIS client beans configured:**

| MisClient Type | findService Name | Methods |
|---------------|-----------------|---------|
| `MisClient<EmployeeService>` | `"ExecutionContextEmployeeService"` | `retrieveServiceAccessDetailsByEmployeeId` |
| `MisClient<CardsMaintenanceServiceStubConnector>` | `"CardsMaintenanceServiceStubConnector"` | `addMemo` |
| `MisClient<LifecycleService>` | `"AuditLifecycle"` | audit event methods |

## Discovery Steps for MCA2

### M2.1 — Find all callService calls
```
Grep src/main/java/ for ".callService(" (exclude test/, fake/)
```

### M2.2 — Resolve MisClient/BEMClient type
From call site variable, trace to field/parameter declaration → `MisClient<ServiceInterface>`.
The generic type IS the EBS service interface.

### M2.3 — Resolve method name from lambda
Parse lambda body: `svc -> svc.retrieveServiceAccessDetailsByEmployeeId(ctx)` → method = `retrieveServiceAccessDetailsByEmployeeId`

### M2.4 — Resolve MTS service name string
Search config classes (`@Bean` methods) for `serviceLocator.findService("name", ServiceInterface.class)`.
The string is the MTS service name (equivalent to MCA1 SERVICE_NAME constant).

### M2.5 — Map to EBS JAR
From the service interface import: `com.barclays.services.executioncontext.employee.service.EmployeeService` → `ebs_execctxemployee` (same convention as MCA1).
