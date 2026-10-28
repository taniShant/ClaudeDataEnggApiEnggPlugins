# Exception Hierarchy & HTTP Status Mapping

## Executive Summary

The **Exception Hierarchy** provides a structured, type-safe way to represent errors in MCA2 applications, enabling automatic mapping to HTTP status codes and standardized error responses. All exceptions inherit from `GenericException`, establishing a clear exception handling contract across all services.

**Key Characteristics:**
- **5 exception types** mapping to distinct HTTP status code ranges
- **Automatic HTTP status mapping** via ResponseHttpStatus
- **Structured error responses** via Response<T> envelopes
- **Type-safe exception handling** for better IDE support
- **Clear error semantics** for API consumers

---

## Exception Hierarchy Structure

```
java.lang.Exception
    └── GenericException (Abstract)
        ├── ApplicationException (Business logic errors, 200 status)
        ├── ServerException (500+ errors)
        ├── RequestException (4xx errors)
        ├── NotFoundException (404)
        └── AuthorizationException (403)
```

---

## Exception Classes

### Location

**Module:** `mca-libraries/exception-handling-core`
**Package:** `com.barclays.global.mca.libs.core.exceptions`
**Files:**
```
exception-handling-core/src/main/java/
└── com/barclays/global/mca/libs/core/exceptions/
    ├── GenericException.java (abstract)
    ├── ApplicationException.java
    ├── ServerException.java
    ├── RequestException.java
    ├── NotFoundException.java
    └── AuthorizationException.java
```

---

### 1. GenericException (Abstract Base)

**Purpose:** Base class for all MCA2 exceptions

**Characteristics:**
- Abstract class - cannot instantiate directly
- Defines common exception contract
- Provides error code and message

**Code:**
```java
public abstract class GenericException extends Exception {

    private String errorCode;           // Machine-readable error code
    private String errorMessage;        // Human-readable message
    private int httpStatusCode;         // HTTP status to return
    private Map<String, Object> details;// Additional error context

    public GenericException(String errorCode, String message) {
        super(message);
        this.errorCode = errorCode;
        this.errorMessage = message;
    }

    public GenericException(
        String errorCode,
        String message,
        Throwable cause
    ) {
        super(message, cause);
        this.errorCode = errorCode;
        this.errorMessage = message;
    }

    public String getErrorCode() {
        return errorCode;
    }

    public abstract int getHttpStatusCode();

    // Used by ExceptionFilter to build Response<T>
    public Message toMessage() {
        return new Message(
            errorCode,
            errorMessage,
            Severity.ERROR
        );
    }
}
```

**Usage Pattern:**
```java
// Never throw GenericException directly - it's abstract
// Always throw a specific subclass

// ✅ Correct
throw new NotFoundException("CUSTOMER_NOT_FOUND",
    "Customer with ID 12345 not found");

// ❌ Wrong
throw new GenericException("ERROR", "Something went wrong");
```

---

### 2. ApplicationException (200-level Success Cases)

**Purpose:** Represent business logic errors that don't prevent response

**HTTP Status:** 200 OK (request succeeded, but with business error)

**Use Cases:**
- Business validation errors (credit limit exceeded, account frozen)
- Processing warnings (partial success)
- Known business constraints violated
- Recoverable errors

**Code:**
```java
public class ApplicationException extends GenericException {

    public ApplicationException(String errorCode, String message) {
        super(errorCode, message);
    }

    public ApplicationException(
        String errorCode,
        String message,
        Throwable cause
    ) {
        super(errorCode, message, cause);
    }

    @Override
    public int getHttpStatusCode() {
        return 200;  // OK - application completed, but with business error
    }
}
```

**Examples:**

```java
// Example 1: Credit limit exceeded
if (transferAmount > creditLimit) {
    throw new ApplicationException(
        "CREDIT_LIMIT_EXCEEDED",
        "Transfer amount " + transferAmount + " exceeds credit limit " + creditLimit
    );
}

// Example 2: Account frozen
if (account.isFrozen()) {
    throw new ApplicationException(
        "ACCOUNT_FROZEN",
        "Account is currently frozen and cannot process transactions"
    );
}

// Example 3: Insufficient funds (business logic, not a server error)
if (balance < withdrawAmount) {
    throw new ApplicationException(
        "INSUFFICIENT_FUNDS",
        "Available balance " + balance + " is less than requested withdrawal"
    );
}
```

**Response Example:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "data": null,
  "messages": [
    {
      "code": "CREDIT_LIMIT_EXCEEDED",
      "message": "Transfer amount 50000 exceeds credit limit 40000",
      "severity": "ERROR"
    }
  ],
  "status": "ERROR",
  "statusCode": "200"
}
```

---

### 3. RequestException (400-level Client Errors)

**Purpose:** Represent client request errors (invalid input, malformed data)

**HTTP Status:** 400 Bad Request (client sent bad data)

**Use Cases:**
- Invalid input parameters
- Malformed JSON/XML
- Missing required fields
- Type conversion errors
- Constraint violations (too long string, invalid format)

**Code:**
```java
public class RequestException extends GenericException {

    public RequestException(String errorCode, String message) {
        super(errorCode, message);
    }

    public RequestException(
        String errorCode,
        String message,
        Throwable cause
    ) {
        super(errorCode, message, cause);
    }

    @Override
    public int getHttpStatusCode() {
        return 400;  // Bad Request
    }
}
```

**Examples:**

```java
// Example 1: Invalid input format
if (!amount.matches("^[0-9]+\\.[0-9]{2}$")) {
    throw new RequestException(
        "INVALID_AMOUNT_FORMAT",
        "Amount must be in format: 1234.56"
    );
}

// Example 2: Missing required field
if (request.getCardNumber() == null || request.getCardNumber().isEmpty()) {
    throw new RequestException(
        "MISSING_CARD_NUMBER",
        "Card number is required"
    );
}

// Example 3: String too long
if (description.length() > 500) {
    throw new RequestException(
        "DESCRIPTION_TOO_LONG",
        "Description cannot exceed 500 characters (received: " + description.length() + ")"
    );
}

// Example 4: Invalid enum value
if (!Arrays.asList("LOCK", "UNLOCK", "REPLACE")
        .contains(request.getAction())) {
    throw new RequestException(
        "INVALID_ACTION",
        "Action must be one of: LOCK, UNLOCK, REPLACE"
    );
}
```

**Response Example:**
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "data": null,
  "messages": [
    {
      "code": "INVALID_AMOUNT_FORMAT",
      "message": "Amount must be in format: 1234.56",
      "severity": "ERROR"
    }
  ],
  "status": "ERROR",
  "statusCode": "400"
}
```

---

### 4. NotFoundException (404 Client Error)

**Purpose:** Represent requested resource doesn't exist

**HTTP Status:** 404 Not Found (resource doesn't exist)

**Use Cases:**
- Customer/account not found
- Card doesn't exist
- Transaction not found
- Endpoint doesn't exist

**Code:**
```java
public class NotFoundException extends GenericException {

    private String resourceType;        // What resource was not found
    private String resourceId;          // Which ID was not found

    public NotFoundException(String errorCode, String message) {
        super(errorCode, message);
    }

    public NotFoundException(
        String errorCode,
        String message,
        String resourceType,
        String resourceId
    ) {
        super(errorCode, message);
        this.resourceType = resourceType;
        this.resourceId = resourceId;
    }

    @Override
    public int getHttpStatusCode() {
        return 404;  // Not Found
    }

    public String getResourceType() {
        return resourceType;
    }

    public String getResourceId() {
        return resourceId;
    }
}
```

**Examples:**

```java
// Example 1: Customer not found
Optional<Customer> customer = customerRepository.findById(customerId);
if (customer.isEmpty()) {
    throw new NotFoundException(
        "CUSTOMER_NOT_FOUND",
        "Customer with ID " + customerId + " not found",
        "Customer",
        customerId
    );
}

// Example 2: Card not found
Card card = cardRepository.findById(cardId);
if (card == null) {
    throw new NotFoundException(
        "CARD_NOT_FOUND",
        "Card with ID " + cardId + " not found",
        "Card",
        cardId
    );
}

// Example 3: Transaction not found
Optional<Transaction> transaction = transactionRepository.findById(transactionId);
if (!transaction.isPresent()) {
    throw new NotFoundException(
        "TRANSACTION_NOT_FOUND",
        "Transaction " + transactionId + " does not exist"
    );
}
```

**Response Example:**
```http
HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "data": null,
  "messages": [
    {
      "code": "CUSTOMER_NOT_FOUND",
      "message": "Customer with ID 12345 not found",
      "severity": "ERROR"
    }
  ],
  "status": "ERROR",
  "statusCode": "404"
}
```

---

### 5. AuthorizationException (403 Client Error)

**Purpose:** Represent access denied / insufficient permissions

**HTTP Status:** 403 Forbidden (client authenticated but not authorized)

**Use Cases:**
- User lacks required permissions
- Customer accessing another customer's data
- Insufficient role level
- Operation not allowed for this user

**Code:**
```java
public class AuthorizationException extends GenericException {

    private String requiredPermission;   // What permission was needed
    private String attemptedAction;      // What action was attempted
    private String resourceId;           // What resource was accessed

    public AuthorizationException(String errorCode, String message) {
        super(errorCode, message);
    }

    public AuthorizationException(
        String errorCode,
        String message,
        String requiredPermission,
        String attemptedAction,
        String resourceId
    ) {
        super(errorCode, message);
        this.requiredPermission = requiredPermission;
        this.attemptedAction = attemptedAction;
        this.resourceId = resourceId;
    }

    @Override
    public int getHttpStatusCode() {
        return 403;  // Forbidden
    }

    public String getRequiredPermission() {
        return requiredPermission;
    }

    public String getAttemptedAction() {
        return attemptedAction;
    }
}
```

**Examples:**

```java
// Example 1: Missing required permission
UserContext user = WebUtils.getUserContext();
if (!user.getPermissions().contains("card:lock")) {
    throw new AuthorizationException(
        "INSUFFICIENT_PERMISSION",
        "User " + user.getUserId() + " lacks permission card:lock",
        "card:lock",
        "LOCK_CARD",
        cardId
    );
}

// Example 2: Accessing other customer's data
CustomerContext currentCustomer = WebUtils.getCustomerContext();
if (!currentCustomer.getCustomer().getCustomerId().equals(targetCustomerId)) {
    throw new AuthorizationException(
        "UNAUTHORIZED_CUSTOMER_ACCESS",
        "Cannot access customer " + targetCustomerId,
        "customer:read",
        "GET_CUSTOMER",
        targetCustomerId
    );
}

// Example 3: Insufficient role level
if (user.getRoles().stream()
        .noneMatch(role -> Arrays.asList("ADMIN", "MANAGER").contains(role))) {
    throw new AuthorizationException(
        "ADMIN_ROLE_REQUIRED",
        "This operation requires ADMIN or MANAGER role"
    );
}
```

**Response Example:**
```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "data": null,
  "messages": [
    {
      "code": "INSUFFICIENT_PERMISSION",
      "message": "User U123 lacks permission card:lock",
      "severity": "ERROR"
    }
  ],
  "status": "ERROR",
  "statusCode": "403"
}
```

---

### 6. ServerException (500+ Server Errors)

**Purpose:** Represent unexpected server-side errors

**HTTP Status:** 500 Internal Server Error (server error, client request was valid)

**Use Cases:**
- Database connection errors
- External service failures
- Unexpected runtime errors
- Configuration errors
- Resource exhaustion

**Code:**
```java
public class ServerException extends GenericException {

    private String systemComponent;      // Which component failed
    private LocalDateTime failureTime;   // When it failed

    public ServerException(String errorCode, String message) {
        super(errorCode, message);
        this.failureTime = LocalDateTime.now();
    }

    public ServerException(
        String errorCode,
        String message,
        Throwable cause
    ) {
        super(errorCode, message, cause);
        this.failureTime = LocalDateTime.now();
    }

    public ServerException(
        String errorCode,
        String message,
        String systemComponent,
        Throwable cause
    ) {
        super(errorCode, message, cause);
        this.systemComponent = systemComponent;
        this.failureTime = LocalDateTime.now();
    }

    @Override
    public int getHttpStatusCode() {
        return 500;  // Internal Server Error
    }

    public String getSystemComponent() {
        return systemComponent;
    }
}
```

**Examples:**

```java
// Example 1: Database error
try {
    customer = customerRepository.findById(customerId).orElseThrow();
} catch (DataAccessException ex) {
    throw new ServerException(
        "DATABASE_ERROR",
        "Failed to retrieve customer data",
        "CUSTOMER_DB",
        ex
    );
}

// Example 2: External service failure
try {
    response = restTemplate.getForObject(missionServiceUrl, Data.class);
} catch (RestClientException ex) {
    throw new ServerException(
        "EXTERNAL_SERVICE_FAILED",
        "Failed to call Mission service",
        "MISSION_SERVICE",
        ex
    );
}

// Example 3: Configuration error
if (apiKey == null || apiKey.isEmpty()) {
    throw new ServerException(
        "MISSING_CONFIGURATION",
        "Payment service API key not configured"
    );
}

// Example 4: Resource exhaustion
if (memoryUsage > 90) {
    throw new ServerException(
        "OUT_OF_MEMORY",
        "Server has insufficient memory to process request"
    );
}
```

**Response Example:**
```http
HTTP/1.1 500 Internal Server Error
Content-Type: application/json

{
  "data": null,
  "messages": [
    {
      "code": "DATABASE_ERROR",
      "message": "Failed to retrieve customer data",
      "severity": "ERROR"
    }
  ],
  "status": "ERROR",
  "statusCode": "500"
}
```

---

## HTTP Status Mapping

### ResponseHttpStatus Class

**Location:** `mca-response-handling-core/src/main/java/.../response/constants/ResponseHttpStatus.java`

**Purpose:** Map exception types to HTTP status codes

**Code:**
```java
public class ResponseHttpStatus {

    public static int getStatusCode(Throwable ex) {
        if (ex instanceof ApplicationException) {
            return 200;
        } else if (ex instanceof NotFoundException) {
            return 404;
        } else if (ex instanceof AuthorizationException) {
            return 403;
        } else if (ex instanceof RequestException) {
            return 400;
        } else if (ex instanceof ServerException) {
            return 500;
        } else if (ex instanceof GenericException) {
            return 500;  // Fallback
        } else {
            return 500;  // Unexpected exception
        }
    }

    public static String getStatusMessage(int statusCode) {
        return switch (statusCode) {
            case 200 -> "OK";
            case 400 -> "Bad Request";
            case 403 -> "Forbidden";
            case 404 -> "Not Found";
            case 500 -> "Internal Server Error";
            default -> "Unknown";
        };
    }
}
```

### Status Code Matrix

| Exception | HTTP Status | Meaning | Client Action |
|-----------|-------------|---------|----------------|
| ApplicationException | 200 OK | Business logic error | Retry with valid business data |
| RequestException | 400 Bad Request | Invalid input | Fix request and retry |
| AuthorizationException | 403 Forbidden | Insufficient permissions | Contact admin, use different account |
| NotFoundException | 404 Not Found | Resource doesn't exist | Verify resource ID, check if deleted |
| ServerException | 500 Internal Error | Server error | Retry later, contact support |

---

## Exception Handling in ExceptionFilter

### How ExceptionFilter Handles Exceptions

**Location:** `mca-filter-core/src/main/java/.../filters/ExceptionFilter.java`

```java
public class ExceptionFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {

        try {
            filterChain.doFilter(request, response);
        } catch (Exception ex) {

            // Get HTTP status code
            int statusCode = ResponseHttpStatus.getStatusCode(ex);

            // Build error response
            Response<?> errorResponse;
            if (ex instanceof GenericException) {
                errorResponse = Response.assemble()
                    .error(List.of(((GenericException) ex).toMessage()))
                    .withStatusCode(statusCode);
            } else {
                // Unexpected exception
                errorResponse = Response.assemble()
                    .error(List.of(
                        new Message(
                            "INTERNAL_ERROR",
                            ex.getMessage(),
                            Severity.ERROR
                        )
                    ))
                    .withStatusCode(500);
            }

            // Set response
            response.setStatus(statusCode);
            response.setContentType("application/json");
            response.getWriter().write(
                objectMapper.writeValueAsString(errorResponse)
            );

            // Log exception
            logger.error(
                "Exception in request {}: {}",
                CorrelationIdContext.get(),
                ex.getMessage(),
                ex
            );
        }
    }
}
```

---

## Best Practices: Throwing Exceptions

### ✅ Good Exception Usage

```java
// 1. Use specific exception types
if (!account.exists()) {
    throw new NotFoundException(
        "ACCOUNT_NOT_FOUND",
        "Account " + accountId + " does not exist"
    );
}

// 2. Provide context in error messages
throw new RequestException(
    "INVALID_AMOUNT",
    "Amount must be between 0.01 and 1000000.00. Received: " + amount
);

// 3. Include cause chain for debugging
try {
    response = service.callExternalApi();
} catch (IOException ex) {
    throw new ServerException(
        "API_CALL_FAILED",
        "External API call failed",
        "EXTERNAL_SERVICE",
        ex
    );
}

// 4. Use appropriate exception type for domain
if (userHasNoPermission) {
    throw new AuthorizationException(...);  // Not RequestException
}
```

### ❌ Bad Exception Usage

```java
// 1. Generic exceptions
throw new Exception("Error!");  // ❌ Too generic

// 2. Vague error messages
throw new RequestException("ERROR", "Invalid input");  // ❌ No details

// 3. Swallowing exceptions
try {
    doSomething();
} catch (Exception ex) {
    // ❌ Silent failure
}

// 4. Wrong exception type
if (resource not found) {
    throw new RequestException(...);  // ❌ Should be NotFoundException
}

// 5. Leaking implementation details
throw new ServerException(
    "ERROR",
    "NullPointerException in line 42 of CardService"  // ❌ Implementation detail
);
```

---

## Custom Exception Types

### Extending the Hierarchy

```java
// Application-specific exception
public class InsufficientFundsException extends ApplicationException {

    private BigDecimal requiredAmount;
    private BigDecimal availableAmount;

    public InsufficientFundsException(
        BigDecimal required,
        BigDecimal available
    ) {
        super(
            "INSUFFICIENT_FUNDS",
            "Insufficient funds. Required: " + required
                + ", Available: " + available
        );
        this.requiredAmount = required;
        this.availableAmount = available;
    }

    public BigDecimal getShortfall() {
        return requiredAmount.subtract(availableAmount);
    }
}

// Usage
if (balance.compareTo(withdrawAmount) < 0) {
    throw new InsufficientFundsException(withdrawAmount, balance);
}
```

---

## Exception Logging

### Log Levels

```java
// ERROR (for actual errors)
logger.error("Request failed: {}", ex.getMessage(), ex);

// WARN (for recoverable business errors)
if (ex instanceof ApplicationException) {
    logger.warn("Business rule violation: {}", ex.getMessage());
}

// DEBUG (for detailed diagnostics)
logger.debug("Exception details: code={}, message={}",
    ((GenericException) ex).getErrorCode(),
    ex.getMessage());
```

### Correlation ID in Logs

```java
// Always include correlation ID
String correlationId = CorrelationIdContext.get();
logger.error(
    "[{}] Exception occurred: {}",
    correlationId,
    ex.getMessage(),
    ex
);

// Output:
// [550e8400-e29b-41d4-a716-446655440000] Exception occurred: Customer not found
```

---

## Complete Exception Code Reference

### Throwing Exceptions by Scenario

```java
// ✅ Resource not found
throw new NotFoundException("CARD_NOT_FOUND",
    "Card ID " + cardId + " not found");

// ✅ Invalid input
throw new RequestException("INVALID_AMOUNT",
    "Amount must be > 0");

// ✅ Access denied
throw new AuthorizationException("NO_PERMISSION",
    "Cannot access other customer's data");

// ✅ Business rule violated
throw new ApplicationException("ACCOUNT_FROZEN",
    "This account is frozen");

// ✅ Server error with cause
try {
    db.query(...);
} catch (SQLException ex) {
    throw new ServerException("DB_ERROR",
        "Database query failed", "DATABASE", ex);
}
```

---

## Next Steps

1. **Understand the 5 exception types** and their HTTP status mappings
2. **Review ResponseHttpStatus** mapping logic
3. **Study ExceptionFilter** exception handling
4. **Create custom exceptions** for your application
5. **Use appropriate exception types** in your business logic
6. **Log with correlation IDs** for traceability

---

## Quick Reference: Exception Hierarchy

| Exception | HTTP | Use For | Example |
|-----------|------|---------|---------|
| **ApplicationException** | 200 | Business errors | "Credit limit exceeded" |
| **RequestException** | 400 | Invalid input | "Email format invalid" |
| **AuthorizationException** | 403 | Access denied | "Insufficient permissions" |
| **NotFoundException** | 404 | Resource missing | "Customer not found" |
| **ServerException** | 500 | Server errors | "Database connection failed" |

**Exception Hierarchy enables consistent error handling and HTTP status mapping across all MCA2 services.**
