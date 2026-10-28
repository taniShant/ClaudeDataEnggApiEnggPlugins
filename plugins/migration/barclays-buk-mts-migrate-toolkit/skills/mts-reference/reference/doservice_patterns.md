# doService Call Patterns

Six patterns to look for when discovering doService calls and related integration points:

## Pattern 1: Constant

```java
doService(SomeService.SERVICE_NAME, "methodName", request)
```
Resolve `SERVICE_NAME` from the imported interface.

## Pattern 2: String Literal

```java
doService("ServiceName", "methodName", request)
```
Value is inline, no resolution needed.

## Pattern 3: Variable (method name, service name, or both)

Either the method name, the service name, or BOTH are variables/parameters — not string literals or class constants.

```java
// 3a: Variable method name only (service is a constant)
doService(LocateCustomerService.SERVICE_NAME, callingMethod, serviceParamList)

// 3b: Variable service name AND method name (both are parameters)
doService(callingService, callingMethod, serviceParamList)

// 3c: Variable method name passed from caller
doService(CustomerUpdateService.SERVICE_NAME, methodName, setParam)
```

**Resolution algorithm for Pattern 3:**

1. **Identify the containing method** — the method that contains the `doService` call with the variable argument(s).
2. **Find ALL callers** of that containing method across the entire `src/main/java/` tree.
3. **For each caller**, extract the concrete value passed for the variable argument:
   - If the caller passes a string literal: `"locateByCustomerId"` → record directly
   - If the caller passes a class constant: `IdentifyCustomerConstants.IDENTIFY_BY_CUSTOMER_ID` → resolve the constant value
   - If the caller passes another variable: recurse — trace THAT caller too
4. **Emit one DOSERVICE_CALL entry per unique (service_name, method_name) pair** found through caller tracing.
5. **Log**: `[INFO] Pattern 3 variable method: {containingMethod} called from {N} callers with {M} distinct method values`

**Real-world example (from scp-eps-idv):**
```java
// Multiplexer method with BOTH variable service and method:
private Object callLocateCustomerEBS(String callingService, String callingMethod, ...) {
    return serviceManager.doService(callingService, callingMethod, serviceParamList);
}

// Callers pass 10+ different (service, method) combinations:
callLocateCustomerEBS(CustomerLocateService.SERVICE_NAME, "locateByCustomerId", ...)
callLocateCustomerEBS(CustomerLocateService.SERVICE_NAME, IDENTIFY_BY_POSTCODE_SURNAME, ...)
callLocateCustomerEBS(MortgageService.SERVICE_NAME, "findCustomers", ...)
```
Each unique (service, method) pair is a SEPARATE mainframe operation with its own Command, Transaction, and TDL tables.

## Pattern 4: ServiceManager / ServiceDelegate / ServiceProvider

```java
// All of these are equivalent — different field names for the same dispatch mechanism:
serviceManager.doService(...)    // Common in IDV, BFA repos
serviceDelegate.doService(...)   // Common in FullServe repos
serviceProvider.getXxxService().doService(...)  // Service provider pattern
```
The field name varies by project. Grep for ALL variants: `doService(` catches them all regardless of the object name.

## Pattern 5: Already-API REST

```java
serviceManager.doService(CONNECTOR, RestApiUtils.EXECUTE_API, requestMap)
```
Identifies services that are **already migrated** to REST APIs. The `EXECUTE_API` (or `REST_SERVICE_EXECUTE`) constant as the method argument indicates the doService call routes to a REST connector, not an EBS/MQ path.

- Tag as `already-api-rest` category
- Discover for inventory but **exclude from migration pipeline**
- ~88 services follow this pattern in fullserve-buk

## Pattern 6: Direct Gateway (no doService)

```java
ProductGateway.findByPrimaryKey(productId)
ReferenceData.populateData(connection, sql, params)
CommonUtilityGateway.method(args)
```
Direct gateway/utility calls that bypass the `doService()` pattern entirely. These access databases (Oracle, DB2) directly via JDBC without MQ or EBS command classes.

- Not found by grepping for `doService(` — requires separate detection
- Grep for `findByPrimaryKey`, `populateData`, `CommonUtilityGateway` in `src/main/java/`
- Classify as `oracle-db-direct` or `db2-reference` per service_categories.md algorithm

## Resolution Strategy

1. For **constants**: Read the import statement for the class containing the constant, then grep the project source AND Gradle cache JARs for the constant value.
2. For **variables**: Trace the method's callers to find where concrete string values are passed.
3. For **delegates**: Treat identically to serviceManager patterns but search for `serviceDelegate.doService(` instead.
4. For **already-API REST**: Resolve the CONNECTOR constant to identify the REST service name. No further mainframe extraction needed.
5. For **direct gateway calls**: Identify the gateway class and method, trace the JDBC datasource, and identify the target database tables.

## EBS Framework Dispatch Mechanism

The EBS framework routes doService calls through a reflection-based dispatch chain:

```
serviceManager.doService(SERVICE_NAME, operationCode, params)
  → EBS framework lookup by SERVICE_NAME
    → Java reflection: ServiceInterface.operationCode(params)
      → ServiceBaseImpl.operationCode(params)
        → new PascalCase(operationCode)Command(...)
          → Command.execute() → Gateway → Transaction → mainframe
```

**Key mapping rules:**
- The `operationCode` string is the method name on the EBS service interface.
- The Command class is: `PascalCase(operationCode)` + `"Command"`.
  - Example: `retrievePersonalCustomerFullDetails` → `RetrievePersonalCustomerFullDetailsCommand`
- The Command class lives in the EBS JAR corresponding to the SERVICE_NAME.
- The Gateway class is domain-specific (e.g., `CustomerGateway`, `UkbaGateway`).
- The Transaction class lives in the EGS ODS MF JAR and contains the WMID-to-TDL mappings.

**Resolution chain for discovery:**
```
SERVICE_NAME → import package → EBS artifact name
operationCode → PascalCase + "Command" → Command class in EBS JAR
Command.execute() → Gateway.method() → Transaction class in EGS ODS MF JAR
Transaction → DataGroups → WMID parameters → TDL tables
```
