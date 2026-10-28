# Standard BUK Call Flow Patterns

Eleven call flow patterns exist across BUK projects, covering all EBS/EGS-based transport types.

## Pattern 1: Direct Mainframe-MQ (e.g., GCR Application Data, most simple projects)

```
REST Client
  -> Controller (@PostMapping)
    -> Servlet Filters (UserContext -> CustomerContext -> AccountContext -> ConfigContext -> SecureContext)
      -> Service.method(request)
        -> Helper class
          -> serviceManager.doService(SERVICE_NAME, "methodName", requestEdo)
            -> EBS ImplClass.method(requestEdo)
              -> CommandClass.doExecute()
                -> Gateway.method() [EGS -> mainframe TDL tables]
```

## Pattern 2: ODS Failover Wrapper (e.g., FullServe BUK, projects with ODS)

```
REST Client
  -> Controller (@PostMapping)
    -> ServiceWrapper.method(params)           [optional ODS failover wrapper]
      -> odsHelper.executeTransaction(...)     [optional ODS wrapping]
        -> serviceDelegate.doService(SERVICE_NAME, "methodName", request)
          -> EBS ImplClass.method(request)
            -> CommandClass.doExecute()
              -> Gateway.method() [EGS -> mainframe TDL tables]
```

## Pattern 3: SOAP Stub (Fraud Desktop and similar)

```
REST Client
  -> Controller (@PostMapping)
    -> Service.method(request)
      -> serviceDelegate.doService(XxxStubConnector.SERVICE_NAME, "soapOperation", params, false)
        -> StubConnector.invoke()
          -> AXIS2 SOAP Client
            -> External SOAP Service (e.g., Fraud Desktop)
```

## Pattern 4: CMOD/ODWEK (Document retrieval)

```
REST Client
  -> Controller (@PostMapping)
    -> Service.method(request)
      -> CmodEao.retrieveDocument(criteria)
        -> HTTP POST
          -> ODWEK Server (/CC-ODWEK/... or /RP-ODWEK-WAR/...)
            -> IBM CMOD Document Store
```

## Pattern 5: TCV Hybrid (Dual-path with feature flag)

```
REST Client
  -> Controller (@PostMapping)
    -> Service.method(request)
      -> if (featureFlag.isEnabled("TCV_API_ENABLED"))
        |-> REST path: serviceManager.doService(CONNECTOR, EXECUTE_API, request)
        |     -> REST API call (already migrated path)
        |
        |-> else: Legacy path: serviceDelegate.doService(SERVICE_NAME, "method", request)
              -> EBS/EGS -> MQ -> mainframe (or SOAP stub)
```

## Pattern 6: SCV (SOAP to SingleCustomerView)

```
REST Client
  -> Controller (@PostMapping)
    -> CustomerHoldingsServiceImpl.method(request)
      -> SCV SOAP Client
        -> SOAP/HTTP POST
          -> SingleCustomerView endpoint
            -> Card-specific data (card accounts, thumbnails, availability)
```

## Pattern 7: Already-API REST (out of scope)

```
REST Client
  -> Controller (@PostMapping)
    -> Service.method(request)
      -> serviceManager.doService(CONNECTOR, RestApiUtils.EXECUTE_API, requestMap)
        -> REST Connector
          -> REST API (already modern)
```

## Pattern 8: Direct HTTP (out of scope)

```
REST Client
  -> Controller (@PostMapping)
    -> Service.method(request)
      -> CloseableHttpClient / RestTemplate
        -> HTTP/HTTPS
          -> External REST API (no EBS involvement)
```

## Pattern 9: SOAP Web Service (non-CICS backend, e.g., ILP/Hogan mortgages)

```
REST Client
  -> Controller (@PostMapping)
    -> ServiceImpl.method(request)
      -> serviceDelegate.doService(SERVICE_NAME, "method", request)
        -> EBS Command.doExecute()
          -> EGS Gateway.method()
            -> ProxyServiceWrapper / ServiceAssembler
              -> SOAP Web Service (e.g., X61563 ILP Account Details)
                -> Backend System (ILP / Hogan)
```

## Pattern 10: ITSU/Oracle (execution context, employee data)

```
REST Client
  -> Controller (@PostMapping)
    -> ServiceImpl.method(request)
      -> serviceDelegate.doService(SERVICE_NAME, "method", request)
        -> EBS ImplClass.method(request)
          -> Helper / DAO class
            -> JDBC / DataSource
              -> Oracle Database (ITSU managed)
```

## Pattern 11: ALS Backend (loans, lending)

```
REST Client
  -> Controller (@PostMapping)
    -> ServiceImpl.method(request)
      -> serviceDelegate.doService(SERVICE_NAME, "method", request)
        -> EBS Command.doExecute()
          -> LoansGateway / LendingGateway.method()
            -> ALS Transaction
              -> ALS Backend System (Advanced Lending System)
```

---

## Identifying Which Pattern

| Indicator | Pattern |
|-----------|---------|
| `serviceManager.doService(...)` with standard EBS constants, no ODS helper | Pattern 1: Direct Mainframe-MQ |
| `serviceDelegate.doService(...)`, ODS helper classes, FullServe-style | Pattern 2: ODS Failover |
| `*StubConnector.SERVICE_NAME` in doService, AXIS2 dependencies | Pattern 3: SOAP Stub |
| `com.barclays.gs.cmod.*` imports, ODWEK config | Pattern 4: CMOD/ODWEK |
| Feature flag check + dual doService paths (REST and legacy) | Pattern 5: TCV Hybrid |
| `com.barclays.scv.*` imports, `SingleCustomerView` endpoint | Pattern 6: SCV |
| `RestApiUtils.EXECUTE_API` or `REST_SERVICE_EXECUTE` as method arg | Pattern 7: Already-API REST |
| `CloseableHttpClient` / `RestTemplate` without EBS | Pattern 8: Direct HTTP |
| EGS JAR with `*ProxyServiceWrapper` / `*ServiceAssembler` / `*WebService*` | Pattern 9: SOAP Web Service |
| EBS JAR group = `executioncontext`, Helper/DAO with JDBC/Oracle | Pattern 10: ITSU/Oracle |
| EBS JAR group = `loans`/`lending`, ALS Transaction classes extending `DatastreamTransaction`, DAG field patterns (`AMWKWI00-*`, `AMWKMD00-*`) | Pattern 11: ALS Backend |
