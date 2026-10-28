# Exception Classes Reference: Complete Hierarchy

## Executive Summary

Complete reference for MCA2 exception hierarchy including HTTP status mappings, use cases, and code examples. Use this when implementing error handling and designing error responses.

---

## Exception Hierarchy

```
java.lang.Exception
│
└─ GenericException (base - com.barclays.global.mca.libs.core.exceptions)
   │
   ├─ ApplicationException (200 OK - application-level error)
   ├─ RequestException (400 Bad Request - client error)
   ├─ NotFoundException (404 Not Found - resource not found)
   ├─ AuthorizationException (403 Forbidden - permission denied)
   └─ ServerException (500 Internal Server Error - server error)
```

---

## BASE EXCEPTION CLASS

### GenericException

**Package:** `com.barclays.global.mca.libs.core.exceptions`

**Inheritance:** `extends java.lang.RuntimeException`

**Purpose:** Base class for all MCA2 exceptions with HTTP status mapping

**Key Constructors:**
```java
public GenericException(String message)
public GenericException(String message, Throwable cause)
public GenericException(String message, ErrorCode errorCode)
public GenericException(String message, ErrorCode errorCode, Throwable cause)
```

**Key Methods:**
```java
public ResponseHttpStatus getResponseHttpStatus()  // HTTP status
public ErrorCode getErrorCode()                     // Error code enum
public String getErrorMessage()                     // Error message
public Map<String, String> getDetails()            // Additional details
public void addDetail(String key, String value)    // Add detail
```

**Example:**
```java
try {
  validateOrder(order);
} catch (Exception e) {
  throw new GenericException("Order validation failed", e);
}
```

---

## CONCRETE EXCEPTION TYPES

### 1. ApplicationException

**HTTP Status:** 200 OK (with error status in body)

**Use When:** Application-level error, not client fault or server fault

**Scenarios:**
- Business logic constraint violation
- Policy restriction
- Account status preventing operation
- Insufficient funds
- Duplicate record exists
- Operation not allowed in current state

**Constructors:**
```java
public ApplicationException(String message)
public ApplicationException(String message, ErrorCode code)
public ApplicationException(String message, ErrorCode code, Throwable cause)
```

**Example:**
```java
if (account.getBalance().compareTo(requestAmount) < 0) {
  throw new ApplicationException(
    "Insufficient funds",
    ErrorCode.INSUFFICIENT_BALANCE
  );
}

// Response:
// HTTP 200 OK
// {
//   "status": "APPLICATION_ERROR",
//   "error": "Insufficient funds",
//   "errorCode": "INSUFFICIENT_BALANCE"
// }
```

**Common Error Codes:**
```
INSUFFICIENT_BALANCE - Account has insufficient funds
DUPLICATE_RECORD - Record already exists
INVALID_STATE - Operation not allowed in current state
POLICY_VIOLATION - Violates business policy
LIMIT_EXCEEDED - Amount/count exceeds configured limit
```

---

### 2. RequestException

**HTTP Status:** 400 Bad Request

**Use When:** Client provided invalid request data

**Scenarios:**
- Missing required field
- Invalid data format
- Value out of range
- Constraint violation (unique, min/max)
- Malformed JSON/XML
- Invalid enumeration value
- Null/empty required parameter

**Constructors:**
```java
public RequestException(String message)
public RequestException(String message, ErrorCode code)
public RequestException(String message, Throwable cause)
```

**Example:**
```java
if (request.getAmount() == null || request.getAmount().signum() <= 0) {
  throw new RequestException(
    "Amount must be positive",
    ErrorCode.VALIDATION_ERROR
  );
}

// Response:
// HTTP 400 Bad Request
// {
//   "status": "ERROR",
//   "error": "Amount must be positive",
//   "errorCode": "VALIDATION_ERROR"
// }
```

**Common Error Codes:**
```
VALIDATION_ERROR - Request validation failed
MISSING_REQUIRED_FIELD - Required field is missing
INVALID_FORMAT - Data format is invalid
INVALID_ENUM_VALUE - Enumeration value not recognized
DUPLICATE_KEY - Unique constraint violation
CONSTRAINT_VIOLATION - Generic constraint violation
```

---

### 3. NotFoundException

**HTTP Status:** 404 Not Found

**Use When:** Requested resource does not exist

**Scenarios:**
- User/customer not found
- Order/account not found
- Transaction not found
- File/document not found
- Endpoint not found
- Configuration not found

**Constructors:**
```java
public NotFoundException(String message)
public NotFoundException(String message, ErrorCode code)
public NotFoundException(String resource, String identifier)
```

**Example:**
```java
Order order = orderRepository.findById(orderId).orElse(null);
if (order == null) {
  throw new NotFoundException("Order not found: " + orderId);
}

// Response:
// HTTP 404 Not Found
// {
//   "status": "ERROR",
//   "error": "Order not found: order-123",
//   "errorCode": "RESOURCE_NOT_FOUND"
// }
```

**Common Error Codes:**
```
RESOURCE_NOT_FOUND - Requested resource not found
USER_NOT_FOUND - User does not exist
ORDER_NOT_FOUND - Order does not exist
ACCOUNT_NOT_FOUND - Account does not exist
ENDPOINT_NOT_FOUND - API endpoint not found
```

---

### 4. AuthorizationException

**HTTP Status:** 403 Forbidden

**Use When:** User lacks permission for operation

**Scenarios:**
- User role insufficient
- Permission denied
- Cross-customer access attempt
- Tenant isolation violation
- Feature not enabled for this tier
- IP address not whitelisted
- Time-based restriction (business hours only)

**Constructors:**
```java
public AuthorizationException(String message)
public AuthorizationException(String message, ErrorCode code)
public AuthorizationException(String message, String requiredPermission)
```

**Example:**
```java
if (!user.hasPermission("ORDER_CREATE")) {
  throw new AuthorizationException(
    "User does not have permission to create orders",
    ErrorCode.PERMISSION_DENIED
  );
}

// Response:
// HTTP 403 Forbidden
// {
//   "status": "ERROR",
//   "error": "User does not have permission to create orders",
//   "errorCode": "PERMISSION_DENIED"
// }
```

**Common Error Codes:**
```
PERMISSION_DENIED - User lacks required permission
INSUFFICIENT_PRIVILEGE - Insufficient privilege level
CROSS_CUSTOMER_ACCESS - Attempting to access another customer's data
FEATURE_NOT_ENABLED - Feature not enabled for this tier
IP_NOT_WHITELISTED - IP address not in whitelist
```

---

### 5. ServerException

**HTTP Status:** 500 Internal Server Error

**Use When:** Server-side error occurred

**Scenarios:**
- Database connection failure
- External service unavailable
- Configuration missing/invalid
- File I/O error
- Unexpected runtime error
- Out of memory
- Transaction commit failed
- Unexpected null value

**Constructors:**
```java
public ServerException(String message)
public ServerException(String message, Throwable cause)
public ServerException(String message, ErrorCode code, Throwable cause)
```

**Example:**
```java
try {
  return databaseService.saveOrder(order);
} catch (SQLException e) {
  logger.error("Database error saving order", e);
  throw new ServerException(
    "Failed to save order",
    ErrorCode.DATABASE_ERROR,
    e
  );
}

// Response:
// HTTP 500 Internal Server Error
// {
//   "status": "ERROR",
//   "error": "Failed to save order",
//   "errorCode": "DATABASE_ERROR"
// }
```

**Common Error Codes:**
```
DATABASE_ERROR - Database operation failed
SERVICE_UNAVAILABLE - External service unavailable
CONFIGURATION_ERROR - Configuration is invalid/missing
FILE_IO_ERROR - File I/O operation failed
TIMEOUT - Operation timed out
OUT_OF_MEMORY - Server out of memory
INTERNAL_ERROR - Generic internal server error
```

---

## ErrorCode Enumeration

### Definition

```java
public enum ErrorCode {
  // Validation errors (4xx)
  VALIDATION_ERROR("VAL001"),
  MISSING_REQUIRED_FIELD("VAL002"),
  INVALID_FORMAT("VAL003"),
  INVALID_ENUM_VALUE("VAL004"),
  DUPLICATE_KEY("VAL005"),
  CONSTRAINT_VIOLATION("VAL006"),

  // Authorization errors (403)
  PERMISSION_DENIED("AUTH001"),
  INSUFFICIENT_PRIVILEGE("AUTH002"),
  CROSS_CUSTOMER_ACCESS("AUTH003"),
  FEATURE_NOT_ENABLED("AUTH004"),
  IP_NOT_WHITELISTED("AUTH005"),

  // Not found errors (404)
  RESOURCE_NOT_FOUND("NOT001"),
  USER_NOT_FOUND("NOT002"),
  ORDER_NOT_FOUND("NOT003"),
  ACCOUNT_NOT_FOUND("NOT004"),

  // Application errors (200)
  INSUFFICIENT_BALANCE("APP001"),
  DUPLICATE_RECORD("APP002"),
  INVALID_STATE("APP003"),
  POLICY_VIOLATION("APP004"),
  LIMIT_EXCEEDED("APP005"),

  // Server errors (500)
  DATABASE_ERROR("SRV001"),
  SERVICE_UNAVAILABLE("SRV002"),
  CONFIGURATION_ERROR("SRV003"),
  FILE_IO_ERROR("SRV004"),
  TIMEOUT("SRV005"),
  OUT_OF_MEMORY("SRV006"),
  INTERNAL_ERROR("SRV999");

  private final String code;
}
```

---

## ResponseHttpStatus Mapping

### HTTP Status Code Mapping

| Exception Type | HTTP Status | Status Code | When to Use |
|----------------|------------|-------------|------------|
| ApplicationException | 200 | OK | Business logic constraint |
| RequestException | 400 | Bad Request | Invalid client input |
| NotFoundException | 404 | Not Found | Resource doesn't exist |
| AuthorizationException | 403 | Forbidden | Permission denied |
| ServerException | 500 | Internal Server Error | Server-side error |

### Response Body Format

```json
{
  "status": "ERROR",           // or SUCCESS, APPLICATION_ERROR
  "error": "error message",    // Human-readable error
  "errorCode": "CODE123",      // Machine-readable error code
  "timestamp": "2026-02-26T10:15:23.456Z",
  "correlationId": "550e8400-e29b-41d4-a716-446655440000",
  "details": {
    "field": "amount",         // Optional: which field failed
    "value": "-100",           // Optional: what value failed
    "constraint": "positive"   // Optional: what constraint violated
  }
}
```

---

## Exception Handling Patterns

### Pattern 1: Controller-Level Handling

```java
@RestController
@RequestMapping("/api/orders")
public class OrderController {

  @PostMapping
  public ResponseEntity<Response<?>> createOrder(
    @RequestBody CreateOrderRequest request
  ) {
    try {
      Order order = orderService.create(request);
      return ResponseEntity.ok(
        Response.assemble()
          .status("SUCCESS")
          .data(order)
          .build()
      );
    } catch (RequestException e) {
      return ResponseEntity.badRequest()
        .body(Response.assemble()
          .status("ERROR")
          .error(e.getMessage())
          .build()
        );
    } catch (AuthorizationException e) {
      return ResponseEntity.status(403)
        .body(Response.assemble()
          .status("ERROR")
          .error(e.getMessage())
          .build()
        );
    } catch (ServerException e) {
      logger.error("Server error", e);
      return ResponseEntity.status(500)
        .body(Response.assemble()
          .status("ERROR")
          .error("Internal server error")
          .build()
        );
    }
  }
}
```

### Pattern 2: Global Exception Handler

```java
@RestControllerAdvice
@Slf4j
public class GlobalExceptionHandler {

  @ExceptionHandler(RequestException.class)
  public ResponseEntity<Response<?>> handleRequestException(RequestException e) {
    logger.warn("Request validation failed: {}", e.getMessage());
    return ResponseEntity.badRequest()
      .body(Response.assemble()
        .status("ERROR")
        .error(e.getMessage())
        .errorCode(e.getErrorCode().toString())
        .build()
      );
  }

  @ExceptionHandler(NotFoundException.class)
  public ResponseEntity<Response<?>> handleNotFoundException(NotFoundException e) {
    logger.warn("Resource not found: {}", e.getMessage());
    return ResponseEntity.notFound().build();
  }

  @ExceptionHandler(AuthorizationException.class)
  public ResponseEntity<Response<?>> handleAuthorizationException(AuthorizationException e) {
    logger.warn("Authorization failed: {}", e.getMessage());
    return ResponseEntity.status(403)
      .body(Response.assemble()
        .status("ERROR")
        .error(e.getMessage())
        .build()
      );
  }

  @ExceptionHandler(ServerException.class)
  public ResponseEntity<Response<?>> handleServerException(ServerException e) {
    logger.error("Server error", e);
    return ResponseEntity.status(500)
      .body(Response.assemble()
        .status("ERROR")
        .error("Internal server error")
        .build()
      );
  }

  @ExceptionHandler(Exception.class)
  public ResponseEntity<Response<?>> handleUnexpected(Exception e) {
    logger.error("Unexpected error", e);
    return ResponseEntity.status(500)
      .body(Response.assemble()
        .status("ERROR")
        .error("Internal server error")
        .build()
      );
  }
}
```

### Pattern 3: Service Layer

```java
@Service
public class OrderService {

  public Order createOrder(CreateOrderRequest request) {
    // Validation errors (RequestException)
    if (request.getAmount() == null || request.getAmount().signum() <= 0) {
      throw new RequestException(
        "Amount must be positive",
        ErrorCode.VALIDATION_ERROR
      );
    }

    // Authorization errors (AuthorizationException)
    if (!hasPermission("ORDER_CREATE")) {
      throw new AuthorizationException(
        "User does not have permission to create orders",
        ErrorCode.PERMISSION_DENIED
      );
    }

    // Application errors (ApplicationException)
    if (customer.getBalance().compareTo(request.getAmount()) < 0) {
      throw new ApplicationException(
        "Insufficient balance",
        ErrorCode.INSUFFICIENT_BALANCE
      );
    }

    // Server errors (ServerException)
    try {
      return orderRepository.save(order);
    } catch (SQLException e) {
      throw new ServerException(
        "Failed to save order",
        ErrorCode.DATABASE_ERROR,
        e
      );
    }
  }
}
```

---

## Decision Tree: Which Exception to Throw

```
Is it client's fault?
├─ YES: Missing/invalid data?
│  └─ YES → RequestException (400)
│  └─ NO ──→ AuthorizationException (403)
├─ NO: Is it resource not found?
│  └─ YES → NotFoundException (404)
├─ NO: Is it application constraint?
│  └─ YES → ApplicationException (200)
└─ NO: Server error
   └─ YES → ServerException (500)
```

---

## Exception Logging Best Practices

```java
// Good: Include context
logger.error("Failed to create order for customer: {} (amount: {})",
  customerId, amount, e);

// Good: Include correlation ID (automatic via MDC)
logger.error("Order creation failed", e);

// Bad: Too verbose
logger.error("An error occurred during processing", e);

// Bad: Exposing sensitive data
logger.error("Failed to authenticate user: password={}", password, e);
```

---

## Response Examples

### 400 Bad Request (RequestException)
```json
{
  "status": "ERROR",
  "error": "Amount must be positive",
  "errorCode": "VALIDATION_ERROR",
  "details": {
    "field": "amount",
    "value": "-100"
  }
}
```

### 403 Forbidden (AuthorizationException)
```json
{
  "status": "ERROR",
  "error": "User does not have permission",
  "errorCode": "PERMISSION_DENIED"
}
```

### 404 Not Found (NotFoundException)
```json
{
  "status": "ERROR",
  "error": "Order not found: ORD-123"
}
```

### 200 OK Application Error (ApplicationException)
```json
{
  "status": "APPLICATION_ERROR",
  "error": "Insufficient balance",
  "errorCode": "INSUFFICIENT_BALANCE",
  "details": {
    "currentBalance": 500.00,
    "requestedAmount": 1000.00,
    "shortfall": 500.00
  }
}
```

### 500 Internal Server Error (ServerException)
```json
{
  "status": "ERROR",
  "error": "Internal server error",
  "correlationId": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## Testing Exception Handling

```java
@Test
void shouldThrowRequestExceptionForNegativeAmount() {
  assertThrows(RequestException.class, () -> {
    orderService.create(requestWithAmount(-100));
  });
}

@Test
void shouldThrowNotFoundExceptionForMissingOrder() {
  assertThrows(NotFoundException.class, () -> {
    orderService.getOrder("nonexistent-id");
  });
}

@Test
void shouldThrowAuthorizationExceptionForInsufficientPermission() {
  assertThrows(AuthorizationException.class, () -> {
    orderService.deleteOrder(orderId);  // User lacks DELETE permission
  });
}

@Test
void shouldThrowApplicationExceptionForInsufficientBalance() {
  assertThrows(ApplicationException.class, () -> {
    orderService.create(largeOrder);  // Customer lacks funds
  });
}

@Test
void shouldThrowServerExceptionOnDatabaseError() {
  when(repository.save(any())).thenThrow(SQLException.class);

  assertThrows(ServerException.class, () -> {
    orderService.create(validOrder);
  });
}
```

---

## Quick Reference: When to Throw What

| Scenario | Exception | HTTP | Code |
|----------|-----------|------|------|
| Invalid input | RequestException | 400 | VALIDATION_ERROR |
| Missing permission | AuthorizationException | 403 | PERMISSION_DENIED |
| Resource missing | NotFoundException | 404 | RESOURCE_NOT_FOUND |
| Insufficient balance | ApplicationException | 200 | INSUFFICIENT_BALANCE |
| Database error | ServerException | 500 | DATABASE_ERROR |

**Exception Classes Reference provides authoritative error handling guide.**

