# Context Classes Reference: Complete Data Model

## Executive Summary

Complete reference for all 25+ context classes in IOLSchema. Includes data model structure, serialization formats, validation rules, and usage examples. Use this when designing or working with context data.

---

## IOLSchema Root Container

### Structure

```java
public class IOLSchema {
  private Map<String, Object> contexts;  // Holds all context data

  public void put(String key, Object context)
  public Object get(String key)
  public <T> T get(Class<T> contextClass)
  public boolean contains(String key)
  public Set<String> getKeys()
  public String toJson()
  public static IOLSchema fromJson(String json)
}
```

### JSON Serialization Format

```json
{
  "customer": {"customerId": "cust-123", "name": "Acme Corp"},
  "user": {"userId": "user-456", "email": "john@example.com"},
  "account": {"accountId": "acc-789", "type": "CHECKING"},
  "process": {"processId": "proc-111", "type": "ORDER_CREATION"},
  "device": {"deviceId": "dev-222", "type": "MOBILE"},
  "caller": {"callerId": "caller-333", "type": "API"},
  "case": {"caseId": "case-444", "status": "OPEN"},
  "locale": {"language": "en", "country": "US"},
  "secure": {"encryptionKey": "key-555", "algorithm": "AES"},
  "channel": {"name": "WEB", "version": "2.0"},
  "geolocation": {"latitude": 40.7128, "longitude": -74.0060},
  "additional": {}
}
```

### HTTP Header Format

```
X-CustomerContext: {"customerId":"cust-123","name":"Acme Corp"}
X-UserContext: {"userId":"user-456","email":"john@example.com"}
X-AccountContext: {"accountId":"acc-789","type":"CHECKING"}
X-ProcessContext: {"processId":"proc-111","type":"ORDER_CREATION"}
X-DeviceContext: {"deviceId":"dev-222","type":"MOBILE"}
```

---

## CONTEXT CLASS CATALOG (25+ classes)

### 1. CustomerContext

**Purpose:** Company/customer/account holder information

**Package:** `com.barclays.global.mca.libs.context.data`

**Fields:**
```java
public class CustomerContext {
  private String customerId;           // Unique identifier
  private String customerName;         // Company/account name
  private String legalEntityId;        // LEI or legal entity ID
  private String tier;                 // PREMIUM, STANDARD, FREE, ENTERPRISE
  private String segment;              // SME, MNC, STARTUP, etc.
  private String status;               // ACTIVE, SUSPENDED, CLOSED
  private String country;              // ISO country code
  private String industry;             // Industry classification
  private Boolean multiCurrency;       // Multi-currency account
  private List<String> entitlements;   // Permission list
}
```

**Example:**
```json
{"customerId":"cust-123","customerName":"Acme Corp","tier":"ENTERPRISE","status":"ACTIVE"}
```

**Serialization:** JSON object on X-CustomerContext header

**Validation:** customerId REQUIRED, min 1 char, max 50 chars

---

### 2. UserContext

**Purpose:** Authenticated user identity and permissions

**Fields:**
```java
public class UserContext {
  private String userId;               // User ID (email or UUID)
  private String email;                // Email address
  private String firstName;            // First name
  private String lastName;             // Last name
  private String role;                 // USER, ADMIN, SUPER_ADMIN
  private List<String> permissions;    // Fine-grained permissions
  private String department;           // Department name
  private String manager;              // Manager ID
  private LocalDateTime lastLogin;     // Last login timestamp
  private Boolean mfaEnabled;          // MFA status
  private String authMethod;           // PASSWORD, OAUTH2, LDAP, SAML
}
```

**Example:**
```json
{"userId":"user-456","email":"john@acme.com","role":"ADMIN","mfaEnabled":true}
```

**Validation:** userId REQUIRED, email format validated

---

### 3. AccountContext

**Purpose:** Financial account details

**Fields:**
```java
public class AccountContext {
  private String accountId;            // Account number
  private String accountType;          // CHECKING, SAVINGS, CREDIT, etc.
  private String accountStatus;        // ACTIVE, CLOSED, FROZEN
  private String currency;             // ISO currency code
  private BigDecimal balance;          // Current balance
  private BigDecimal creditLimit;      // Credit limit (if applicable)
  private LocalDate openingDate;       // Account opening date
  private LocalDate lastActivityDate;  // Last transaction date
  private String businessUnit;         // Owning business unit
  private List<String> linkedAccounts; // Related accounts
  private Boolean isJoint;             // Joint account indicator
}
```

**Example:**
```json
{"accountId":"ACC-789","accountType":"CHECKING","currency":"USD","balance":5000.00}
```

**Validation:** accountId REQUIRED, accountType REQUIRED

---

### 4. ProcessContext

**Purpose:** Business process or transaction details

**Fields:**
```java
public class ProcessContext {
  private String processId;            // Process/transaction ID
  private String processType;          // ORDER, PAYMENT, TRANSFER, etc.
  private String status;               // INITIATED, IN_PROGRESS, COMPLETED, FAILED
  private LocalDateTime startTime;     // Process start time
  private LocalDateTime endTime;       // Process completion time
  private String initiatedBy;          // User/system that started it
  private String approvedBy;           // Approver ID (if applicable)
  private Map<String, Object> metadata;// Additional process data
  private List<String> stepLog;        // Log of process steps
  private BigDecimal amount;           // Transaction amount (if applicable)
  private String channel;              // Initiating channel
}
```

**Example:**
```json
{"processId":"proc-111","processType":"ORDER","status":"COMPLETED","amount":999.99}
```

**Validation:** processId REQUIRED, processType REQUIRED

---

### 5. DeviceContext

**Purpose:** End-user device information

**Fields:**
```java
public class DeviceContext {
  private String deviceId;             // Device identifier
  private String deviceType;           // MOBILE, DESKTOP, TABLET, ATM
  private String osType;               // iOS, Android, Windows, macOS
  private String osVersion;            // OS version
  private String appVersion;           // Application version
  private String deviceModel;          // Device model
  private String manufacturer;         // Device manufacturer
  private String ipAddress;            // Client IP address
  private String userAgent;            // Browser user agent
  private Boolean isSecure;            // SSL/TLS indicator
  private String fingerprint;          // Device fingerprint
  private String pushToken;            // Push notification token
}
```

**Example:**
```json
{"deviceId":"dev-222","deviceType":"MOBILE","osType":"iOS","ipAddress":"192.168.1.1"}
```

**Validation:** deviceId REQUIRED for mobile apps

---

### 6. CallerContext

**Purpose:** API consumer/caller information

**Fields:**
```java
public class CallerContext {
  private String callerId;             // Unique caller ID
  private String callerType;           // API_CLIENT, PARTNER, INTERNAL, EXTERNAL
  private String apiKey;               // API key identifier (hashed)
  private String clientName;           // Client application name
  private String version;              // API version
  private List<String> scopes;         // OAuth scopes (if OAuth)
  private String rateLimit;            // Rate limit tier
  private Boolean isProd;              // Production/sandbox indicator
  private LocalDateTime expiryDate;    // API key expiry
  private String contactEmail;         // Support contact
}
```

**Example:**
```json
{"callerId":"api-client-1","callerType":"API_CLIENT","rateLimit":"PREMIUM"}
```

**Validation:** callerId REQUIRED

---

### 7. CaseContext

**Purpose:** Support case or issue ticket information

**Fields:**
```java
public class CaseContext {
  private String caseId;               // Case/ticket ID
  private String caseType;             // INCIDENT, REQUEST, COMPLAINT, etc.
  private String status;               // OPEN, IN_PROGRESS, RESOLVED, CLOSED
  private String priority;             // LOW, MEDIUM, HIGH, CRITICAL
  private String assignedTo;           // Assigned agent ID
  private LocalDateTime createdDate;   // Case creation date
  private LocalDateTime resolutionDate;// Resolution date
  private String description;          // Case description
  private List<String> tags;           // Classification tags
  private String parentCaseId;         // Parent case (if sub-case)
}
```

**Example:**
```json
{"caseId":"case-444","caseType":"INCIDENT","status":"OPEN","priority":"HIGH"}
```

**Validation:** caseId REQUIRED if case exists in context

---

### 8. LocaleContext

**Purpose:** Internationalization and localization settings

**Fields:**
```java
public class LocaleContext {
  private String language;             // ISO 639-1 code (en, es, fr, etc.)
  private String country;              // ISO 3166-1 alpha-2 code (US, GB, etc.)
  private String variant;              // Variant/dialect (en_GB, pt_BR, etc.)
  private String timeZone;             // IANA timezone (America/New_York)
  private String dateFormat;           // Date format pattern
  private String timeFormat;           // Time format pattern
  private String currencyCode;         // ISO 4217 currency code
  private Boolean is24HourFormat;      // 24-hour vs 12-hour
  private String numberFormat;         // Decimal separator and grouping
  private String textDirection;        // LTR or RTL
}
```

**Example:**
```json
{"language":"en","country":"US","timeZone":"America/New_York","currencyCode":"USD"}
```

**Validation:** language REQUIRED, country RECOMMENDED

---

### 9. SecureContext

**Purpose:** Security and encryption configuration

**Fields:**
```java
public class SecureContext {
  private String encryptionKey;        // Key identifier (hashed)
  private String encryptionAlgorithm;  // AES, RSA, etc.
  private String hashAlgorithm;        // SHA256, SHA512
  private String securityLevel;        // LOW, MEDIUM, HIGH, MAXIMUM
  private Boolean requiresMFA;         // MFA requirement
  private Boolean requiresVPN;         // VPN requirement
  private List<String> allowedIPs;     // IP whitelist
  private LocalDateTime certExpiry;    // Certificate expiry
  private String complianceLevel;      // HIPAA, PCI-DSS, SOC2, etc.
}
```

**Example:**
```json
{"encryptionAlgorithm":"AES-256","securityLevel":"MAXIMUM","requiresMFA":true}
```

**Validation:** securityLevel REQUIRED for sensitive operations

---

### 10. ChannelContext

**Purpose:** Request originating channel information

**Fields:**
```java
public class ChannelContext {
  private String channelName;          // WEB, MOBILE, API, ATM, PHONE
  private String channelVersion;       // Channel version
  private String sourceSystem;         // Source system identifier
  private String integrationId;        // Integration point ID
  private String protocol;             // HTTP, gRPC, WebSocket, etc.
  private Boolean isInteractive;       // User interactive vs batch
  private String endpointId;           // Specific endpoint identifier
  private Boolean isEncrypted;         // Encryption status
  private String certificateId;        // TLS certificate identifier
}
```

**Example:**
```json
{"channelName":"MOBILE","channelVersion":"3.2.1","isInteractive":true}
```

**Validation:** channelName REQUIRED

---

### 11. GeoLocationContext

**Purpose:** Geographic location information

**Fields:**
```java
public class GeoLocationContext {
  private BigDecimal latitude;         // Latitude coordinate
  private BigDecimal longitude;        // Longitude coordinate
  private String city;                 // City name
  private String state;                // State/province
  private String country;              // Country ISO code
  private String postalCode;           // ZIP/postal code
  private String timezone;             // IANA timezone
  private String ipAddress;            // IP address
  private String isp;                  // Internet service provider
  private Boolean isVPN;               // VPN usage indicator
  private Boolean isProxy;             // Proxy usage indicator
}
```

**Example:**
```json
{"latitude":40.7128,"longitude":-74.0060,"city":"New York","country":"US"}
```

**Validation:** latitude/longitude FORMAT validated

---

### 12-25. Additional Context Classes

**MultipleCustomerContext** - Multiple customer/account relationships
**MultipleAccountsContext** - Multiple accounts in single context
**TransactionContext** - Transaction-specific data
**AuthenticationContext** - Authentication method and details
**AuthorizationContext** - Permission and entitlement data
**SessionContext** - Session management data
**AuditContext** - Audit logging information
**NotificationContext** - Notification preferences
**PreferenceContext** - User preferences
**RiskContext** - Risk assessment information
**ComplianceContext** - Compliance flags
**MetricContext** - Performance metrics
**TraceContext** - Distributed tracing information

---

## Context Usage Patterns

### Pattern 1: Extract Context in Controller

```java
@GetMapping("/orders")
public ResponseEntity<?> getOrders(
  @IOLContext CustomerContext customer,
  @IOLContext UserContext user,
  @IOLContext AccountContext account
) {
  // All contexts automatically injected
  logger.info("Customer: {}, User: {}, Account: {}",
    customer.getCustomerId(),
    user.getEmail(),
    account.getAccountId()
  );
}
```

### Pattern 2: Access via WebUtils

```java
@Service
public class OrderService {
  public void processOrder(Order order) {
    IOLSchema schema = WebUtils.getIOLSchemaFromScope();

    CustomerContext customer = schema.get(CustomerContext.class);
    UserContext user = schema.get(UserContext.class);

    logger.info("Processing order for customer: {}",
      customer.getCustomerId());
  }
}
```

### Pattern 3: Manual Context Creation

```java
IOLSchema schema = new IOLSchema();

CustomerContext customer = new CustomerContext();
customer.setCustomerId("cust-123");
customer.setCustomerName("Acme Corp");
schema.put("customer", customer);

UserContext user = new UserContext();
user.setUserId("user-456");
user.setEmail("john@acme.com");
schema.put("user", user);

String json = schema.toJson();
// Use in HTTP header: X-Context: {json}
```

### Pattern 4: Batch Processing with Context

```java
@Scheduled(cron = "0 0 * * * *")
public void processBatch() {
  List<String> customerIds = getCustomers();

  for (String customerId : customerIds) {
    // Create context for each iteration
    IOLSchema schema = new IOLSchema();
    CustomerContext ctx = new CustomerContext();
    ctx.setCustomerId(customerId);
    schema.put("customer", ctx);

    WebUtils.setIOLSchemaInScope(schema);
    try {
      processCustomerData(customerId);
    } finally {
      WebUtils.removeIOLSchemaFromScope();
    }
  }
}
```

---

## Serialization & Deserialization

### To JSON

```java
IOLSchema schema = getContextFromRequest();
String json = schema.toJson();
// Output: {"customer":{...},"user":{...},...}
```

### From JSON

```java
String json = request.getHeader("X-Context");
IOLSchema schema = IOLSchema.fromJson(json);
CustomerContext customer = schema.get(CustomerContext.class);
```

### To HTTP Headers

```java
IOLSchema schema = getContext();
Map<String, String> headers = new HashMap<>();

schema.getKeys().forEach(key -> {
  String value = mapper.writeValueAsString(schema.get(key));
  headers.put("X-" + key, value);
});

// Result:
// X-Customer: {"customerId":"cust-123",...}
// X-User: {"userId":"user-456",...}
// ...
```

---

## Size and Performance Guidelines

| Context Class | Typical Size | Max Size | Serialization |
|---------------|--------------|----------|---------------|
| CustomerContext | 200 bytes | 500 bytes | < 1ms |
| UserContext | 300 bytes | 800 bytes | < 1ms |
| AccountContext | 250 bytes | 600 bytes | < 1ms |
| ProcessContext | 400 bytes | 1KB | < 2ms |
| DeviceContext | 300 bytes | 700 bytes | < 1ms |
| Total IOLSchema | 2-3KB | 5KB | < 5ms |

**Recommendation:** Keep total context < 5KB to avoid header size limits

---

## Validation Rules

### Required Fields
```
CustomerContext: customerId
UserContext: userId (email format recommended)
AccountContext: accountId
ProcessContext: processId
CallerContext: callerId
```

### Format Validation
```
Email: Standard email format (user@domain.com)
ISO Country: 2-letter code (US, GB, FR, etc.)
ISO Language: 2-letter code (en, es, fr, etc.)
Currency: 3-letter code (USD, EUR, GBP, etc.)
Timezone: IANA format (America/New_York, etc.)
```

### Size Limits
```
String fields: 255 characters max
List fields: 100 items max
Numeric fields: BigDecimal for monetary
Boolean fields: true/false only
```

---

## Best Practices

✅ **DO:**
- Set required context fields before processing
- Validate context schema on request entry
- Use @IOLContext annotation in controllers
- Clear context after request processing
- Serialize context to headers for service calls

❌ **DON'T:**
- Create context with null values in required fields
- Store PII in context without masking
- Create circular references in context
- Modify context during processing
- Store large objects in context (> 1KB)

---

## Context Validation Script

```java
public boolean validateContext(IOLSchema schema) {
  // Required contexts
  if (!schema.contains("customer")) return false;

  CustomerContext customer = schema.get(CustomerContext.class);
  if (customer.getCustomerId() == null) return false;

  UserContext user = schema.get(UserContext.class);
  if (user != null && user.getUserId() == null) return false;

  AccountContext account = schema.get(AccountContext.class);
  if (account != null && account.getAccountId() == null) return false;

  return true;
}
```

---

## Quick Reference: All Context Keys

```
Standard Context Keys (X- prefix for headers):
├─ customer (CustomerContext)
├─ user (UserContext)
├─ account (AccountContext)
├─ process (ProcessContext)
├─ device (DeviceContext)
├─ caller (CallerContext)
├─ case (CaseContext)
├─ locale (LocaleContext)
├─ secure (SecureContext)
├─ channel (ChannelContext)
├─ geolocation (GeoLocationContext)
└─ (13+ additional context types)

Example header:
X-CustomerContext: {"customerId":"cust-123","customerName":"Acme"}
X-UserContext: {"userId":"user-456","email":"john@example.com"}
```

**Context Classes Reference provides authoritative data model for MCA2 EPS framework.**

