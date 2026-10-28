# SOAP EAO Patterns

Two SOAP-based integration patterns exist in BUK applications, both using EBS/EGS JARs and requiring replacement with modern APIs.

---

## Pattern: `soap-stub`

### Detection

- Import of `*StubConnector` class (e.g., `FraudDesktopStubConnector`, `CommonServiceManagementStubConnector`)
- Call pattern: `serviceDelegate.doService(XxxStubConnector.SERVICE_NAME, "method", params, false)`
- AXIS2 class hierarchy in dependency JARs
- `services.properties` binding with connector-to-endpoint mapping

### Class Hierarchy

```
StubConnector (abstract)
  -> FraudDesktopStubConnector
  -> CommonServiceManagementStubConnector
  -> AddressSearchStubConnector
  -> ...
```

Each StubConnector registers a `SERVICE_NAME` constant and maps to an AXIS2 SOAP endpoint configured via Spring XML or properties files.

### Call Flow

```
ServiceImpl.method()
  -> serviceDelegate.doService(XxxStubConnector.SERVICE_NAME, "soapOperation", requestParams, false)
    -> StubConnector.invoke()
      -> AXIS2 Client
        -> SOAP Endpoint (external service)
```

### Known StubConnector Services (fullserve-buk)

Approximately 18 services related to Fraud Desktop:
- `FraudDesktopStubConnector` -- Fraud Desktop SOAP services
- `CommonServiceManagementStubConnector` -- Common service management operations
- Additional StubConnectors discovered per project (grep for `extends StubConnector` or `implements.*StubConnector`)

### Configuration

- **Endpoint binding:** `services.properties` maps `SERVICE_NAME` to SOAP endpoint URL
- **WSDL location:** Typically in Spring XML config or `application.properties` as `*.wsdl.url` or `*.endpoint.url`
- **Timeout/retry:** Configured per connector in properties

### Extraction Steps for Discovery Agent

1. Grep for `StubConnector` imports in `src/main/java/`
2. For each StubConnector class, resolve `SERVICE_NAME` constant
3. Grep `services.properties` for the resolved service name to find endpoint URL
4. Extract SOAP operation names from the `doService()` method argument
5. Identify request/response types from the call site parameters

---

## Pattern: `soap-eao`

### Detection

- Import of `*SoapBindingStub` or `*Eao` classes (e.g., `LoansSoapBindingStub`, `IdvEao`, `ServiceNowEao`)
- `?wsdl` configuration in properties files
- Direct EAO method invocation (no `doService()` wrapper in some cases)

### Call Flow

```
ServiceImpl.method()
  -> EaoClass.soapMethod(request)
    -> SoapBindingStub.invoke()
      -> SOAP/HTTP
        -> External SOAP Service
```

Or via doService:

```
ServiceImpl.method()
  -> serviceDelegate.doService(EaoService.SERVICE_NAME, "method", request)
    -> EaoImpl.method(request)
      -> SoapBindingStub.invoke()
        -> SOAP/HTTP
          -> External SOAP Service
```

### Known EAO Services

- **Loans:** `LoansSoapBindingStub` -- loan product enquiry/management
- **IDV (Identity Verification):** `IdvEao` -- identity verification checks
- **ServiceNow:** `ServiceNowEao` -- incident/ticket creation

### Configuration

- **WSDL URL:** `external.services.*.wsdl.url` or `*.endpoint.address` in `application.properties`
- **Credentials:** Service-specific auth configuration
- **Timeout:** Per-EAO timeout settings

### Extraction Steps for Discovery Agent

1. Grep for `SoapBindingStub` and `*Eao` imports in `src/main/java/`
2. Check if they are invoked via `doService()` or directly
3. Grep properties files for `?wsdl` or `wsdl.url` entries
4. Extract SOAP operation names from method calls
5. Identify the backend system each EAO connects to

---

## Replacement API Targets

Both `soap-stub` and `soap-eao` services should be matched against:
- **ODS APIs** for services accessing customer/account data
- **Domain-specific APIs** for services like Fraud Desktop, IDV, ServiceNow
- Search Confluence by domain noun + operation semantics (e.g., "Fraud Desktop API", "IDV verification API")
