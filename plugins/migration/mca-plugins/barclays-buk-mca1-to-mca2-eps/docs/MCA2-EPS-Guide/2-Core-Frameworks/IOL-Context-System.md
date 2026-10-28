# IOL Context System: Distributed Request Context

## Executive Summary

The **IOL (Interoperability Language) Context System** is the central data model for distributed request context propagation in MCA2, enabling microservices to share user, customer, account, and business context across service boundaries via HTTP headers. It implements the **Data Transfer Object (DTO)** pattern for request context representation.

**Key Characteristics:**
- **25+ context classes** representing IOL schema (user, customer, account, process, device, etc.)
- **HTTP header propagation** (X-UserContext, X-CustomerContext, etc.)
- **Request-scoped lifecycle** via Spring request scope
- **Serialization/deserialization** utilities for JSON encoding
- **Validation framework** for context integrity

---

## IOL Schema: Core Data Model

### Root Context Container: IOLSchema

**Location:** `mca-libraries/context/src/main/java/com/barclays/global/mca/libs/context/data/IOLSchema.java`

**Purpose:** Container for all context types propagated through a request

**Structure:**

```java
public class IOLSchema {

    // Identity Contexts
    private UserContext user;
    private CustomerContext customer;
    private AccountContext account;

    // Business Contexts
    private ProcessContext process;
    private DeviceContext device;
    private CaseContext case_;
    private CallerContext caller;

    // Configuration Contexts
    private Channel channel;
    private LocaleContext locale;
    private SecureContext secure;

    // Collections (Multiple values)
    private MultipleCustomerContext multipleCustomers;
    private MultipleAccountsContext multipleAccounts;

    // Additional
    private Map<String, Object> additionalProperties;

    // Metadata
    @JsonIgnore
    private transient Long expiresAt;  // Session expiration
    @JsonIgnore
    private transient String sessionId;  // Distributed session ID

    // Serialization helpers
    public String toJson() { ... }
    public static IOLSchema fromJson(String json) { ... }
}
```

**25+ Context Types Overview:**

```
IOLSchema Container
├── User Identity (3 classes)
│   ├── UserContext
│   ├── Identifier
│   └── TokenIdentifier
├── Customer/Account (4 classes)
│   ├── CustomerContext
│   ├── Customer (value object)
│   ├── AccountContext
│   └── Account (value object)
├── Business Process (3 classes)
│   ├── ProcessContext
│   ├── CaseContext
│   └── CallerContext
├── Device/Channel (3 classes)
│   ├── DeviceContext
│   ├── Channel
│   └── LocaleContext
├── Security (1 class)
│   └── SecureContext
├── Collections (2 classes)
│   ├── MultipleCustomerContext (multiple customer selection)
│   └── MultipleAccountsContext (multiple account selection)
├── Geographic (1 class)
│   └── GeoLocation
└── Additional (5+ classes)
    ├── Token information
    ├── Authorization scopes
    ├── Client metadata
    └── Custom extensions
```

---

## Individual Context Types: Details

### User Identity Contexts

#### **UserContext**

**Purpose:** Current user identity and authentication information

**Fields:**
```java
public class UserContext {
    private String userId;                    // Unique user ID
    private String username;                  // Display username
    private String email;                     // User email
    private List<String> roles;              // User roles (ADMIN, USER, etc.)
    private List<String> permissions;         // Granular permissions
    private String authenticationMethod;      // PASSWORD, SSO, MFA, etc.
    private Long authenticatedAt;            // Timestamp
    private boolean mfaVerified;             // MFA status
    private String locale;                   // User locale preference
    private Map<String, Object> attributes;   // Additional user attributes
}
```

**Usage:**
```java
@IOLContext
public ResponseEntity<Data> getMyData(IOLSchema context) {
    UserContext user = context.getUser();
    String userId = user.getUserId();
    List<String> roles = user.getRoles();
    // Use in business logic
}
```

**HTTP Header Example:**
```
X-UserContext: {"userId":"U12345","username":"john.doe","roles":["USER","ADMIN"]}
```

#### **Identifier & TokenIdentifier**

**Purpose:** Represent various identifier types and token information

**Identifier (flexible ID representation):**
```java
public class Identifier {
    private String type;      // Enum: UUID, EMAIL, PHONE, NATIONAL_ID, etc.
    private String value;     // The actual ID value
    private String status;    // ACTIVE, INACTIVE, EXPIRED
    private Long validFrom;   // Valid period start
    private Long validTo;     // Valid period end
    private String source;    // Where this ID comes from
}
```

**TokenIdentifier (for OAuth/JWT):**
```java
public class TokenIdentifier {
    private String tokenType;   // JWT, BEARER, etc.
    private String issuer;      // https://auth.example.com
    private String audience;    // api.example.com
    private List<String> scopes;  // oauth2 scopes
    private Long issuedAt;      // Token issue time
    private Long expiresAt;     // Token expiration
}
```

---

### Customer & Account Contexts

#### **CustomerContext**

**Purpose:** Customer information and account associations

**Fields:**
```java
public class CustomerContext {
    private Customer customer;                 // Customer data
    private List<String> associatedAccounts;  // Account IDs
    private String primaryAccount;            // Primary account ID
    private String segment;                   // Customer segment
    private String status;                    // ACTIVE, INACTIVE, VIP, etc.
    private LocalDateTime onboardingDate;     // Customer onboarding date
    private Map<String, Object> customData;   // Extensible attributes
}
```

**Customer DTO:**
```java
public class Customer {
    private String customerId;
    private String name;
    private String companyName;
    private LocalDateTime createdDate;
    private String preferredLanguage;
    private String riskProfile;
}
```

**Usage:**
```java
@IOLContext
public ResponseEntity<List<Transaction>> getCustomerTransactions(
    IOLSchema context
) {
    CustomerContext customer = context.getCustomer();
    String customerId = customer.getCustomer().getCustomerId();
    List<String> accounts = customer.getAssociatedAccounts();
    // Query transactions for this customer
}
```

#### **AccountContext**

**Purpose:** Account information and holdings

**Fields:**
```java
public class AccountContext {
    private Account account;                  // Account details
    private String accountId;                 // Account number
    private String accountType;               // CHECKING, SAVINGS, CREDIT_CARD, etc.
    private BigDecimal balance;               // Current balance
    private String currency;                  // Account currency
    private String status;                    // ACTIVE, FROZEN, CLOSED
    private LocalDateTime openedDate;         // Account opening date
    private Map<String, Object> holdings;     // Account holdings/investments
}
```

**Account DTO:**
```java
public class Account {
    private String accountId;
    private String accountHolder;
    private String branch;
    private String sortCode;
}
```

---

### Business Process Contexts

#### **ProcessContext**

**Purpose:** Workflow/process state propagation

**Fields:**
```java
public class ProcessContext {
    private String processId;                 // Unique process ID
    private String processType;               // LOAN_APPLICATION, CARD_REQUEST, etc.
    private String status;                    // PENDING, APPROVED, REJECTED, etc.
    private String currentStep;               // Which step in workflow
    private List<String> completedSteps;      // Workflow history
    private Map<String, Object> processData;  // Process-specific data
    private LocalDateTime initiatedAt;        // Process start time
    private String initiatedBy;               // User who started process
}
```

#### **CaseContext**

**Purpose:** Support case / incident tracking

**Fields:**
```java
public class CaseContext {
    private String caseId;                    // Case/incident ID
    private String caseType;                  // COMPLAINT, INQUIRY, INCIDENT
    private String priority;                  // HIGH, MEDIUM, LOW
    private String status;                    // OPEN, IN_PROGRESS, RESOLVED, CLOSED
    private String assignedTo;                // Support agent user ID
    private LocalDateTime createdAt;
    private List<String> tags;                // Case categorization
}
```

#### **CallerContext**

**Purpose:** Who initiated the request (user or system)

**Fields:**
```java
public class CallerContext {
    private String callerId;                  // Caller ID
    private String callerType;                // USER, SYSTEM, API_KEY, BATCH_JOB
    private String callerName;                // Display name
    private String callingSystem;             // System name if SYSTEM caller
    private String ipAddress;                 // Caller IP address
    private String userAgent;                 // Browser user agent if applicable
}
```

---

### Device & Configuration Contexts

#### **DeviceContext**

**Purpose:** Client device fingerprinting and identification

**Fields:**
```java
public class DeviceContext {
    private String deviceId;                  // Device fingerprint
    private String deviceType;                // MOBILE, DESKTOP, TABLET, API_CLIENT
    private String osType;                    // iOS, Android, Windows, etc.
    private String browserType;               // Chrome, Safari, Firefox, etc.
    private String deviceModel;               // iPhone 13, etc.
    private boolean isTrustedDevice;          // Previously authenticated?
    private LocalDateTime lastUsedAt;
    private String location;                  // Geolocation
}
```

#### **Channel**

**Purpose:** Communication channel (web, mobile, IVR, etc.)

**Fields:**
```java
public class Channel {
    private String channelId;                 // Channel identifier
    private String channelType;               // WEB, MOBILE, IVR, BRANCH, PARTNER_API
    private String channelName;               // Display name
    private String proposition;               // Business proposition (CARDS, PAYMENTS, etc.)
    private String version;                   // Channel version
}
```

#### **LocaleContext**

**Purpose:** Localization and regional preferences

**Fields:**
```java
public class LocaleContext {
    private String locale;                    // en_GB, fr_FR, es_ES, etc.
    private String language;                  // en, fr, es
    private String country;                   // GB, FR, ES
    private String timezone;                  // Europe/London
    private String dateFormat;                // dd/MM/yyyy
    private String currency;                  // GBP, EUR, USD
}
```

#### **SecureContext**

**Purpose:** Security-related context

**Fields:**
```java
public class SecureContext {
    private boolean encryptionRequired;       // Should response be encrypted?
    private String securityLevel;             // LOW, MEDIUM, HIGH, CRITICAL
    private List<String> allowedIpRanges;    // Whitelist IPs
    private boolean mfaRequired;              // MFA needed for sensitive operations?
    private String dataClassification;        // PUBLIC, INTERNAL, CONFIDENTIAL, SECRET
}
```

---

### Multiple Entity Contexts

#### **MultipleCustomerContext**

**Purpose:** Support multi-customer selection (corporate accounts)

**Fields:**
```java
public class MultipleCustomerContext {
    private List<Customer> customers;         // All accessible customers
    private String selectedCustomerId;        // Currently selected
    private String selectionType;             // PRIMARY, DELEGATED, CORPORATE
    private boolean allowCrossCustomer;       // Can access other customers' data?
}
```

#### **MultipleAccountsContext**

**Purpose:** Support multi-account selection

**Fields:**
```java
public class MultipleAccountsContext {
    private List<Account> accounts;           // All accessible accounts
    private String selectedAccountId;         // Currently selected
    private String accountAccessType;         // OWN, DELEGATED, CORPORATE
}
```

---

## Context Propagation: HTTP Headers to Request Scope

### Header-Based Propagation

**Each context type is propagated via an HTTP header:**

```
X-UserContext:              {JSON representation of UserContext}
X-CustomerContext:          {JSON representation of CustomerContext}
X-AccountContext:           {JSON representation of AccountContext}
X-ProcessContext:           {JSON representation of ProcessContext}
X-DeviceContext:            {JSON representation of DeviceContext}
X-CaseContext:              {JSON representation of CaseContext}
X-CallerContext:            {JSON representation of CallerContext}
X-Channel:                  {JSON representation of Channel}
X-LocaleContext:            {JSON representation of LocaleContext}
X-SecureContext:            {JSON representation of SecureContext}
X-MultipleCustomerContext:  {JSON representation of MultipleCustomerContext}
X-MultipleAccountsContext:  {JSON representation of MultipleAccountsContext}
Correlation-ID:           550e8400-e29b-41d4-a716-446655440000
```

### Complete Request Example

```http
POST /api/card-control/lock HTTP/1.1
Host: api.example.com
Content-Type: application/json
Correlation-ID: 550e8400-e29b-41d4-a716-446655440000

X-UserContext: {
  "userId": "U12345",
  "username": "john.doe",
  "email": "john.doe@example.com",
  "roles": ["USER", "CUSTOMER"],
  "permissions": ["card:lock", "card:unlock"],
  "authenticationMethod": "PASSWORD",
  "mfaVerified": true,
  "locale": "en_GB"
}

X-CustomerContext: {
  "customer": {
    "customerId": "C98765",
    "name": "John Doe",
    "companyName": "Acme Corp"
  },
  "associatedAccounts": ["ACC001", "ACC002", "ACC003"],
  "primaryAccount": "ACC001",
  "segment": "PREMIUM",
  "status": "ACTIVE"
}

X-AccountContext: {
  "accountId": "ACC001",
  "accountType": "CHECKING",
  "balance": 50000.00,
  "currency": "GBP",
  "status": "ACTIVE"
}

X-DeviceContext: {
  "deviceId": "device-abc123",
  "deviceType": "MOBILE",
  "osType": "iOS",
  "browserType": "Safari",
  "isTrustedDevice": true,
  "location": "London"
}

X-Channel: {
  "channelId": "ch001",
  "channelType": "MOBILE",
  "channelName": "Mobile Banking App",
  "proposition": "CARDS",
  "version": "5.0"
}

Correlation-ID: 550e8400-e29b-41d4-a716-446655440000

{
  "cardId": "CARD123",
  "reason": "CARD_LOST"
}
```

---

## Context Propagation Flow

### Step-by-Step Propagation

```
1. Client/Browser prepares request
   ├─ Reads IOL context from local storage
   ├─ Serializes to JSON
   └─ Adds X-* headers

2. HTTP Request travels across network
   └─ Headers preserved by proxies/load balancers

3. Receiving service (MCA2 app)
   ├─ HTTP Request arrives at Servlet
   └─ Enters filter chain

4. ContextFilter (in filter-core)
   ├─ Extract all X-* headers
   ├─ Deserialize from JSON
   ├─ Build IOLSchema object
   ├─ Validate schema (IOLContextValidator)
   └─ Pass to next step

5. Request Scope Storage (via WebUtils)
   └─ WebUtils.setIOLSchemaInScope(iolSchema)
       └─ Stores in RequestContextHolder
           └─ Available via thread-local throughout request

6. Spring Argument Resolver (Layer 3)
   ├─ Detects @IOLContext annotation
   ├─ Calls IOLContextHandlerMethodArgumentResolver.resolveArgument()
   ├─ Retrieves from request scope via WebUtils.getIOLSchema()
   └─ Injects into controller method parameter

7. Controller/Handler Method
   ├─ Receives IOLSchema parameter
   ├─ Access context data: context.getUser(), context.getCustomer()
   ├─ Pass context to services
   └─ Services access via WebUtils.getIOLSchema()

8. Service Layer
   └─ May propagate to downstream services via HTTP headers

9. Response Processing
   ├─ Response interceptor may add context info
   └─ Response returned to client
```

### Code Flow Diagram

```
Client Request (with X-* headers)
         ↓
ContextFilter.doFilterInternal()
         ↓
IOLSchema iolSchema = parse(request.getHeaders())
         ↓
IOLContextValidator.validateContext(iolSchema)
         ↓
WebUtils.setIOLSchemaInScope(iolSchema)
    [RequestContextHolder.currentRequestAttributes()
     .setAttribute("iolSchema", iolSchema)]
         ↓
@IOLContext Annotation Handler
    IOLContextHandlerMethodArgumentResolver.resolveArgument()
         ↓
public ResponseEntity<?> handler(
    @IOLContext IOLSchema context  ← Injected from request scope
) { ... }
         ↓
Services Access via:
    WebUtils.getIOLSchema()  ← Retrieves from RequestContextHolder
    context.getUser()        ← Access specific context type
```

---

> **Note:** Context storage backends (mca-context-store-rdb, mca-context-store-mongo, mca-context-store-ehcache) are part of the Secure Proxy module, not the core EPS framework. For details on distributed context session storage, refer to the Secure Proxy documentation.

---

## Context Serialization & Deserialization

### JSON Serialization (mca-context-utils)

**Location:** `mca-context-utils/src/main/java/.../serialization/`

**IOLSchema → JSON:**

```java
// Automatic via Jackson annotations
IOLSchema context = new IOLSchema()
    .setUser(new UserContext().setUserId("U123"))
    .setCustomer(new CustomerContext().setCustomerId("C456"));

// Serialize to JSON
ObjectMapper mapper = new ObjectMapper();
String json = mapper.writeValueAsString(context);

// Output:
// {
//   "user": {"userId": "U123"},
//   "customer": {"customerId": "C456"},
//   ...
// }
```

**JSON → IOLSchema:**

```java
// Deserialize from HTTP header
String headerValue = request.getHeader("X-UserContext");
UserContext user = mapper.readValue(headerValue, UserContext.class);

// Or full IOLSchema
String fullJson = request.getHeader("X-IOLSchema");
IOLSchema context = mapper.readValue(fullJson, IOLSchema.class);
```

### Custom Serialization Example

```java
// Custom serializer for Date formatting
@JsonSerialize(using = CustomDateSerializer.class)
private LocalDateTime createdAt;

public class CustomDateSerializer
    extends StdSerializer<LocalDateTime> {

    @Override
    public void serialize(
        LocalDateTime value,
        JsonGenerator gen,
        SerializerProvider provider
    ) throws IOException {
        gen.writeString(
            value.format(DateTimeFormatter.ISO_INSTANT)
        );
    }
}
```

---

## Context Validation: IOLContextValidator

### Validation Framework

**Location:** `mca-context/src/main/java/.../exception/IOLSchemaValidationException.java`

**Purpose:** Validate context schema integrity

**Validations Performed:**

```java
public class IOLContextValidator {

    public void validateContext(IOLSchema context)
        throws IOLSchemaValidationException {

        // 1. Check required fields
        if (context.getUser() == null) {
            throw new IOLSchemaValidationException(
                "UserContext is required"
            );
        }

        // 2. Validate user fields
        if (context.getUser().getUserId() == null
            || context.getUser().getUserId().isEmpty()) {
            throw new IOLSchemaValidationException(
                "User ID cannot be empty"
            );
        }

        // 3. Check referential integrity
        if (context.getCustomer() != null
            && context.getAccount() != null) {

            // Account must be in customer's associated accounts
            if (!context.getCustomer()
                .getAssociatedAccounts()
                .contains(context.getAccount().getAccountId())) {

                throw new IOLSchemaValidationException(
                    "Account not associated with customer"
                );
            }
        }

        // 4. Check context state consistency
        if (context.getMultipleCustomers() != null) {
            // Selected customer must be in list
            if (!context.getMultipleCustomers()
                .getCustomers()
                .stream()
                .map(Customer::getCustomerId)
                .collect(Collectors.toSet())
                .contains(context.getMultipleCustomers()
                    .getSelectedCustomerId())) {

                throw new IOLSchemaValidationException(
                    "Selected customer not in accessible customers"
                );
            }
        }

        // 5. Timestamp validation
        if (context.getUser().getAuthenticatedAt() != null) {
            long ageInMinutes =
                Duration.between(
                    Instant.ofEpochMilli(
                        context.getUser().getAuthenticatedAt()
                    ),
                    Instant.now()
                ).toMinutes();

            if (ageInMinutes > 480) {  // 8 hours
                throw new IOLSchemaValidationException(
                    "Authentication too old: " + ageInMinutes + " minutes"
                );
            }
        }
    }
}
```

---

## Request-Scoped Access: WebUtils

### Getting Context from Request Scope

**Location:** `mca-web-utils/src/main/java/.../WebUtils.java`

**Storing Context:**
```java
// In ContextFilter
IOLSchema context = parseFromHeaders(request);
WebUtils.setIOLSchemaInScope(context);
```

**Retrieving Context:**
```java
// In service layer (no @IOLContext parameter needed)
IOLSchema context = WebUtils.getIOLSchema();
UserContext user = context.getUser();
String userId = user.getUserId();

// Or access specific context type
CustomerContext customer = WebUtils.getCustomerContext();
```

**Implementation:**
```java
public class WebUtils {

    private static final ThreadLocal<IOLSchema> IOL_HOLDER =
        new ThreadLocal<>();

    public static void setIOLSchemaInScope(IOLSchema schema) {
        IOL_HOLDER.set(schema);
    }

    public static IOLSchema getIOLSchema() {
        IOLSchema schema = IOL_HOLDER.get();
        if (schema == null) {
            throw new IllegalStateException(
                "No IOLSchema in current request scope"
            );
        }
        return schema;
    }

    public static UserContext getUserContext() {
        return getIOLSchema().getUser();
    }

    public static CustomerContext getCustomerContext() {
        return getIOLSchema().getCustomer();
    }

    // ... more convenience methods

    public static void clear() {
        IOL_HOLDER.remove();
    }
}
```

---

## Using Context in Applications

### Pattern 1: @IOLContext Injection (Recommended)

```java
@RestController
@RequestMapping("/api/cards")
public class CardController {

    @GetMapping("/{cardId}")
    public ResponseEntity<CardDetails> getCard(
        @IOLContext IOLSchema context,  // ← Injected by resolver
        @PathVariable String cardId
    ) {
        // Direct access to context
        UserContext user = context.getUser();
        CustomerContext customer = context.getCustomer();

        // Query cards for this customer
        CardDetails card = cardService.getCard(
            customer.getCustomer().getCustomerId(),
            cardId
        );

        return Response.assemble().build(card);
    }

    @PostMapping("/{cardId}/lock")
    public ResponseEntity<LockResult> lockCard(
        @IOLContext IOLSchema context,
        @PathVariable String cardId,
        @RequestBody LockRequest request
    ) {
        LockResult result = cardService.lockCard(
            context.getUser().getUserId(),
            context.getCustomer().getCustomer().getCustomerId(),
            cardId,
            request.getReason()
        );

        return Response.assemble().build(result);
    }
}
```

### Pattern 2: WebUtils Access in Services

```java
@Service
public class CardService {

    public CardDetails getCard(String customerId, String cardId) {
        // Access context from request scope
        IOLSchema context = WebUtils.getIOLSchema();
        UserContext user = context.getUser();

        // Verify access
        if (!hasAccessToCustomer(user, customerId)) {
            throw new AuthorizationException(
                "Not authorized to access customer data"
            );
        }

        // Business logic
        return cardRepository.findById(cardId);
    }

    private boolean hasAccessToCustomer(
        UserContext user,
        String customerId
    ) {
        // Check permissions
        return user.getPermissions()
            .contains("card:read")
            && context.getCustomer()
                .getCustomer()
                .getCustomerId()
                .equals(customerId);
    }
}
```

### Pattern 3: Context Propagation to Downstream Services

```java
@Service
public class OrderService {

    public Order createOrder(OrderRequest request) {
        // Get current context
        IOLSchema context = WebUtils.getIOLSchema();

        // Create HTTP headers for downstream call
        HttpHeaders headers = new HttpHeaders();
        headers.set("X-UserContext",
            objectMapper.writeValueAsString(context.getUser()));
        headers.set("X-CustomerContext",
            objectMapper.writeValueAsString(context.getCustomer()));
        headers.set("Correlation-ID",
            CorrelationIdContext.get());

        // Call downstream service with context propagation
        RestTemplate restTemplate = new RestTemplate();
        Order order = restTemplate.postForObject(
            "http://order-service/api/orders",
            new HttpEntity<>(request, headers),
            Order.class
        );

        return order;
    }
}
```

---

## Context Lifecycle: Cleanup

### Request-Scoped Cleanup

**Location:** `ContextFilter` (mca-filter-core)

**Cleanup Pattern:**
```java
public class ContextFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {

        IOLSchema context = parseFromHeaders(request);

        try {
            WebUtils.setIOLSchemaInScope(context);
            filterChain.doFilter(request, response);
        } finally {
            // CLEANUP: Clear thread-local
            WebUtils.clear();
            CorrelationIdContext.clear();
        }
    }
}
```

**Why Cleanup is Critical:**
- Thread pools reuse threads
- Leaked thread-locals cause memory leaks
- Can cause context bleed between requests in thread pools
- Spring Cloud Sleuth and other frameworks rely on this

---

## Context System: Complete Code Reference

### Key Classes Location

```
mca-libraries/context/src/main/java/
com/barclays/global/mca/libs/context/data/
├── IOLSchema.java (root container - 25+ fields)
├── UserContext.java
├── CustomerContext.java
├── Customer.java
├── AccountContext.java
├── Account.java
├── ProcessContext.java
├── DeviceContext.java
├── CaseContext.java
├── CallerContext.java
├── Channel.java
├── LocaleContext.java
├── SecureContext.java
├── Identifier.java
├── TokenIdentifier.java
├── MultipleCustomerContext.java
├── MultipleAccountsContext.java
└── GeoLocation.java

mca-context-utils/src/main/java/
com/barclays/global/mca/libs/context/utils/
└── [Serialization/validation utilities]
```

### Auto-Configuration Location

```
mca-eps-core/src/main/java/
com/barclays/global/mca/libs/eps/
├── config/
│   └── ExperienceAPIConfig.java (registers ContextFilter, ArgumentResolver)
├── annotations/
│   └── @IOLContext
└── interceptors/
    └── IOLContextHandlerMethodArgumentResolver.java
```

---

## Troubleshooting Context Issues

### Issue: @IOLContext Parameter is Null

**Causes:**
- ContextFilter didn't run
- WebUtils.setIOLSchemaInScope() not called
- Context parsing failed silently

**Solution:**
```java
// Verify ContextFilter is enabled
@EnableExperienceAPI  // Must be present

// Add logging to verify filter execution
logger.debug("ContextFilter executed, context: {}",
    WebUtils.getIOLSchema());
```

### Issue: HTTP Headers Not Propagating to Downstream

**Causes:**
- HTTP headers not set in RestTemplate calls
- Downstream service expects different header names
- Proxy/load balancer stripping headers

**Solution:**
```java
// Explicitly propagate headers
HttpHeaders headers = new HttpHeaders();
headers.set("X-UserContext",
    objectMapper.writeValueAsString(context.getUser()));

restTemplate.postForObject(url,
    new HttpEntity<>(body, headers),
    Response.class);
```

### Issue: Context Validation Fails

**Causes:**
- Required field is null
- Account not in customer's associated accounts
- Authentication too old

**Solution:**
```java
// Catch validation exception
try {
    iolValidator.validateContext(context);
} catch (IOLSchemaValidationException ex) {
    logger.error("Context validation failed: {}",
        ex.getMessage());
    // Return 400 Bad Request
}
```

---

## Next Steps

1. **Understand IOLSchema Structure:** Study the 25+ context classes
2. **Review Context Propagation:** Trace HTTP header flow
3. **Use @IOLContext:** Inject in your controllers
4. **Propagate to Services:** Pass context to downstream calls
5. **Test Validation:** Verify context integrity checks

---

## Quick Reference: Context System Summary

| Component | Purpose | Location |
|-----------|---------|----------|
| **IOLSchema** | Root context container | mca-context |
| **25+ Context Types** | User, Customer, Account, Process, etc. | mca-context |
| **ContextFilter** | Extract context from headers | mca-filter-core |
| **WebUtils** | Request-scoped access | mca-web-utils |
| **@IOLContext** | Spring argument injection | mca-eps-core |
| **Serialization** | JSON encoding/decoding | mca-context-utils |
| **Validation** | Schema integrity checks | mca-context |

**Context System is the central data model enabling distributed request processing in MCA2.**
