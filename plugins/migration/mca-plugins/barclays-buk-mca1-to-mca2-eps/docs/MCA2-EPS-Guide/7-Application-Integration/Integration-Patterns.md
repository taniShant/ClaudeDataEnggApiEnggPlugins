# Integration Patterns: MCA2 EPS Best Practices

## Executive Summary

Common patterns for integrating MCA2 EPS frameworks into consuming applications. Covers REST APIs, microservices, configuration strategies, and anti-patterns to avoid. Based on reference application implementations and production experience.

---

## Pattern 1: Minimal REST API with EPS

### Use Case
Simple REST API requiring only logging, basic context, and exception handling. No advanced features needed.

### Architecture
```
HTTP Request
    ↓
[CorrelationIdFilter] - Set correlation ID
    ↓
[ExceptionFilter] - Catch exceptions
    ↓
[Controller] - Handle request
    ↓
[Response.assemble().build()]
    ↓
HTTP Response with correlation ID
```

### Application Configuration

```java
// Application.java
@SpringBootApplication
@EnableExperienceAPI
public class SimpleRestApplication {
  public static void main(String[] args) {
    SpringApplication.run(SimpleRestApplication.class);
  }
}
```

```properties
# application.properties
spring.application.name=simple-rest-api
server.port=8080

# EPS Configuration
mca.eps.enabled=true

# Logging
logging.level.root=INFO
logging.level.com.barclays.global.mca=DEBUG
```

### Implementation Example

```java
// OrderController.java
@RestController
@RequestMapping("/api/orders")
@Slf4j
public class OrderController {

  @PostMapping
  public ResponseEntity<Response<OrderResponse>> createOrder(
    @RequestBody CreateOrderRequest request,
    HttpServletRequest httpRequest
  ) {
    try {
      logger.info("Creating order for customer: {}", request.getCustomerId());

      // Business logic
      Order order = orderService.createOrder(request);

      // Response assembly
      OrderResponse response = new OrderResponse(
        order.getId(),
        order.getStatus()
      );

      return ResponseEntity.ok(
        Response.assemble()
          .status("SUCCESS")
          .data(response)
          .build()
      );

    } catch (OrderValidationException e) {
      logger.warn("Order validation failed", e);
      return ResponseEntity.badRequest()
        .body(Response.assemble()
          .status("VALIDATION_ERROR")
          .error(e.getMessage())
          .build()
        );
    } catch (Exception e) {
      logger.error("Unexpected error creating order", e);
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

### Key Benefits
- ✅ Minimal configuration needed
- ✅ Automatic correlation ID propagation
- ✅ Centralized exception handling
- ✅ Standard response format
- ✅ Basic request logging

### Anti-Patterns to Avoid
```java
// ❌ DON'T: Return raw data without envelope
@PostMapping
public OrderResponse createOrder(@RequestBody CreateOrderRequest req) {
  return orderService.createOrder(req); // Missing Response<> wrapper
}

// ❌ DON'T: Manual exception handling
try {
  orderService.createOrder(req);
} catch (Exception e) {
  e.printStackTrace(); // Manual logging, no correlation
  return new ResponseEntity("Error", 500);
}

// ❌ DON'T: Missing @EnableExperienceAPI
@SpringBootApplication // Missing EPS framework enablement
public class SimpleRestApplication { }
```

---

## Pattern 2: Microservice with Secure Proxy

### Use Case
Microservice protected behind secure proxy, needs session management, request forwarding, and downstream service calls.

### Architecture
```
Request (from Proxy)
    ↓
[ProxySessionFilter] - Validate proxy session
    ↓
[ContextFilter] - Propagate context from headers
    ↓
[ExceptionFilter] - Handle errors
    ↓
[ServiceController] - Call downstream services
    ↓
[ServiceClient] - Propagate context to upstream services
    ↓
Response with context
```

### Application Configuration

```java
// Application.java
@SpringBootApplication
@EnableExperienceAPI
@EnableSecureProxy          // Proxy authentication (includes context storage)
@EnableMaskingService       // Mask sensitive data in logs
@EnableServiceClient        // REST client with context propagation
public class ProxiedMicroserviceApp {
  public static void main(String[] args) {
    SpringApplication.run(ProxiedMicroserviceApp.class);
  }
}
```

```properties
# application.properties
spring.application.name=secured-microservice
server.port=8080

# EPS Configuration
mca.eps.enabled=true

# Secure Proxy Configuration
mca.security.proxy.enabled=true
mca.security.proxy.trusted-headers=X-UserContext,X-CustomerContext

# Service Client Configuration
mca.service.client.enabled=true
mca.service.client.connect-timeout=5000
mca.service.client.read-timeout=10000

# Data Masking
mca.masking.enabled=true
masking.patterns.credit-card=\d{4}(?:\d(?=.\d{3}))
masking.patterns.email=(?<=.{1}).(?=[^@]*@)

# Logging
logging.level.root=WARN
logging.level.com.barclays.global.mca=INFO
logging.level.com.example.microservice=DEBUG
```

### Implementation Example

```java
// AccountServiceController.java
@RestController
@RequestMapping("/api/accounts")
@Slf4j
public class AccountServiceController {

  private final RestClientFactory clientFactory;
  private final AccountService accountService;

  @Autowired
  public AccountServiceController(
    RestClientFactory clientFactory,
    AccountService accountService
  ) {
    this.clientFactory = clientFactory;
    this.accountService = accountService;
  }

  @GetMapping("/{accountId}/balance")
  public ResponseEntity<Response<BalanceResponse>> getBalance(
    @PathVariable String accountId,
    @IOLContext CustomerContext context
  ) {
    try {
      logger.info("Getting balance for account: {}", accountId);

      // Call downstream service with context propagation
      RestTemplate restTemplate = clientFactory.createRestTemplate();
      BalanceData balance = restTemplate.getForObject(
        "http://billing-service/api/balance/" + accountId,
        BalanceData.class
        // Context automatically propagated via HTTP headers
      );

      BalanceResponse response = new BalanceResponse(
        balance.getAmount(),
        balance.getCurrency()
      );

      return ResponseEntity.ok(
        Response.assemble()
          .data(response)
          .build()
      );

    } catch (ServiceUnavailableException e) {
      logger.error("Downstream service unavailable", e);
      throw new ServerException("Billing service temporarily unavailable");
    }
  }
}

// AccountService.java
@Service
@Slf4j
public class AccountService {

  private final RestClientFactory clientFactory;
  private final MaskingService maskingService;

  @Autowired
  public AccountService(
    RestClientFactory clientFactory,
    MaskingService maskingService
  ) {
    this.clientFactory = clientFactory;
    this.maskingService = maskingService;
  }

  public AccountDetails getAccountDetails(String accountId) {
    // Service client automatically propagates context
    RestTemplate client = clientFactory.createRestTemplate();

    try {
      return client.getForObject(
        "http://core-service/api/accounts/" + accountId,
        AccountDetails.class
      );
    } catch (HttpClientErrorException.NotFound e) {
      logger.warn("Account not found: {}", accountId);
      throw new NotFoundException("Account not found: " + accountId);
    } catch (Exception e) {
      logger.error("Error retrieving account details", e);
      throw new ServerException("Failed to retrieve account");
    }
  }
}
```

### Key Benefits
- ✅ Automatic context propagation between services
- ✅ Secure service-to-service communication
- ✅ Data masking in logs
- ✅ Resilient service calls (circuit breaking)

### Anti-Patterns to Avoid
```java
// ❌ DON'T: Manual context propagation
HttpHeaders headers = new HttpHeaders();
headers.set("Correlation-ID", correlationId);
// This is error-prone; RestClientFactory handles it automatically

// ❌ DON'T: Call services without RestClientFactory
new RestTemplate().getForObject(...); // Missing context propagation

// ❌ DON'T: Missing @EnableSecureProxy
// ProxiedMicroserviceApp without @EnableSecureProxy breaks proxy integration
```

---

## Pattern 3: Multi-Tenant Application

### Use Case
Application serving multiple customers with isolated contexts and data, requiring dynamic context selection.

### Architecture
```
Request with X-CustomerContext
    ↓
[TenantFilter] - Extract customer ID
    ↓
[TenantAwareDataSource] - Route to customer database
    ↓
[BusinessLogic] - Execute in tenant context
    ↓
Response
```

### Application Configuration

```java
// Application.java
@SpringBootApplication
@EnableExperienceAPI
@EnableMaskingService
public class MultiTenantApp {
  public static void main(String[] args) {
    SpringApplication.run(MultiTenantApp.class);
  }
}
```

```properties
# application.properties
mca.eps.enabled=true

# Multi-tenant configuration
mca.multi-tenant.enabled=true
mca.multi-tenant.header=X-CustomerContext
```

### Implementation Example

```java
// TenantContext.java - Extends base context
@Data
public class TenantContext {
  private String customerId;
  private String customerName;
  private List<String> entitlements;
  private String dataSourceKey; // Route to correct database
}

// TenantFilter.java - Extract tenant and set context from headers
@Component
public class TenantFilter extends OncePerRequestFilter {

  @Override
  protected void doFilterInternal(
    HttpServletRequest request,
    HttpServletResponse response,
    FilterChain filterChain
  ) throws ServletException, IOException {
    try {
      String customerContext = request.getHeader("X-CustomerContext");

      if (customerContext != null) {
        // Parse customer context from header and set in scope
        IOLSchema schema = parseContextFromHeader(customerContext);
        WebUtils.setIOLSchemaInScope(schema);

        logger.debug("Tenant context loaded: {}", customerContext);
      }

      filterChain.doFilter(request, response);

    } finally {
      // Cleanup
      WebUtils.removeIOLSchemaFromScope();
    }
  }
}

// AccountRepository.java - Tenant-aware data access
@Repository
@Slf4j
public class AccountRepository {

  @Autowired
  private TenantDataSourceManager dataSourceManager;

  public Account findById(String accountId) {
    // Get current tenant context
    TenantContext tenantCtx =
      (TenantContext) WebUtils.getIOLContext("TenantContext");

    // Route to tenant's database
    DataSource tenantDs = dataSourceManager.getDataSource(
      tenantCtx.getDataSourceKey()
    );

    return executeQuery(tenantDs, accountId);
  }
}
```

### Key Benefits
- ✅ Automatic tenant isolation
- ✅ Per-tenant data routing
- ✅ Context per tenant managed independently
- ✅ No manual tenant ID passing

---

## Pattern 4: Event-Driven Architecture

### Use Case
Application publishing and consuming domain events, requiring reliable event propagation with context.

### Architecture
```
OrderService
    ↓
[Publishes OrderCreatedEvent]
    ↓
EventPublisher (includes CorrelationId)
    ↓
┌─────────┬──────────┬──────────┐
│         │          │          │
├─────────┴──────────┴──────────┤
│ Event Queue (RabbitMQ/Kafka) │
└─────────┬──────────┬──────────┘
          │          │
    [InventoryService] [NotificationService]
          ↓          ↓
    [Consume Event with Context]
```

### Implementation Example

```java
// Domain Event
@Data
public class OrderCreatedEvent extends DomainEvent {
  private String orderId;
  private String customerId;
  private BigDecimal amount;
  private String correlationId; // Propagate correlation
}

// OrderService - Publisher
@Service
@Slf4j
public class OrderService {

  private final ApplicationEventPublisher eventPublisher;

  @Autowired
  public OrderService(ApplicationEventPublisher eventPublisher) {
    this.eventPublisher = eventPublisher;
  }

  public Order createOrder(CreateOrderRequest request) {
    Order order = new Order(request);
    order.setStatus(OrderStatus.CREATED);

    // Save order
    orderRepository.save(order);

    // Publish event with current correlation ID
    OrderCreatedEvent event = new OrderCreatedEvent();
    event.setOrderId(order.getId());
    event.setCustomerId(request.getCustomerId());
    event.setAmount(request.getAmount());
    event.setCorrelationId(
      MDC.get("correlationId") // Automatic propagation
    );

    eventPublisher.publishEvent(event);

    return order;
  }
}

// InventoryService - Consumer
@Service
@Slf4j
public class InventoryService {

  private final InventoryRepository repository;

  @EventListener
  @Transactional
  public void onOrderCreated(OrderCreatedEvent event) {
    try {
      logger.info("Processing order event: {}", event.getOrderId());

      // Use event context to route to correct inventory system
      Inventory inventory = repository.findByCustomerId(
        event.getCustomerId()
      );

      inventory.decrementStock(event.getOrderId());
      repository.save(inventory);

    } catch (Exception e) {
      logger.error("Error processing order event: {}", event.getOrderId(), e);
      // Publish OrderProcessingFailedEvent
      throw new InventoryException("Failed to reserve inventory");
    }
  }
}
```

### Key Benefits
- ✅ Loose coupling between services
- ✅ Context automatically propagated through events
- ✅ Audit trail via events
- ✅ Scalable via message queues
- ✅ Correlation tracking across services

---

## Pattern 5: Batch Processing with EPS

### Use Case
Batch job needing context propagation, logging, and exception handling across multiple iterations.

### Implementation Example

```java
// BatchProcessor.java
@Component
@Slf4j
public class BatchProcessor {

  private final AccountService accountService;
  private final ResponseAssembler<BatchResult> assembler;

  @Autowired
  public BatchProcessor(
    AccountService accountService,
    ResponseAssembler<BatchResult> assembler
  ) {
    this.accountService = accountService;
    this.assembler = assembler;
  }

  @Scheduled(cron = "0 0 * * * *") // Hourly
  public void processBatch() {
    String batchId = UUID.randomUUID().toString();
    MDC.put("batchId", batchId);
    MDC.put("correlationId", batchId);

    try {
      logger.info("Starting batch processing");

      List<Account> accounts = accountService.getAllAccounts();
      BatchResult result = new BatchResult(accounts.size());

      int successCount = 0;
      int failureCount = 0;

      for (Account account : accounts) {
        try {
          // Set context for each account
          IOLSchema schema = createContextForAccount(account);
          WebUtils.setIOLSchemaInScope(schema);

          // Process account
          accountService.processAccount(account);
          successCount++;

        } catch (ProcessingException e) {
          logger.warn("Failed to process account: {}", account.getId(), e);
          failureCount++;
          result.addError(account.getId(), e.getMessage());

        } finally {
          WebUtils.removeIOLSchemaFromScope();
        }
      }

      result.setSuccessCount(successCount);
      result.setFailureCount(failureCount);

      logger.info("Batch completed: {} succeeded, {} failed",
        successCount, failureCount);

      // Send result notification
      notifyBatchCompletion(result);

    } catch (Exception e) {
      logger.error("Batch processing failed", e);
      throw new ServerException("Batch processing failed: " + e.getMessage());
    } finally {
      MDC.clear();
    }
  }

  private IOLSchema createContextForAccount(Account account) {
    IOLSchema schema = new IOLSchema();
    // Populate with account context
    return schema;
  }
}
```

### Key Benefits
- ✅ Batch correlation ID tracking
- ✅ Per-item context management
- ✅ Error handling per iteration
- ✅ Comprehensive logging
- ✅ Result aggregation

---

## Common Anti-Patterns

### Anti-Pattern 1: Missing Response Envelope
```java
// ❌ WRONG
@GetMapping("/users/{id}")
public User getUser(@PathVariable String id) {
  return userService.getUser(id); // Bare object response
}

// ✅ CORRECT
@GetMapping("/users/{id}")
public ResponseEntity<Response<User>> getUser(@PathVariable String id) {
  User user = userService.getUser(id);
  return ResponseEntity.ok(
    Response.assemble()
      .data(user)
      .build()
  );
}
```

### Anti-Pattern 2: Ignoring Exception Hierarchy
```java
// ❌ WRONG
@PostMapping("/accounts")
public Account createAccount(@RequestBody CreateAccountRequest req) {
  if (req.getBalance() < 0) {
    throw new IllegalArgumentException("Invalid balance");
  }
}

// ✅ CORRECT
@PostMapping("/accounts")
public ResponseEntity<Response<Account>> createAccount(
  @RequestBody CreateAccountRequest req
) {
  if (req.getBalance() < 0) {
    throw new RequestException(
      "Invalid balance",
      ErrorCode.VALIDATION_ERROR
    );
  }
}
```

### Anti-Pattern 3: No Context Management
```java
// ❌ WRONG - Context lost in async operations
@GetMapping("/reports/{id}")
public CompletableFuture<Report> generateReport(@PathVariable String id) {
  return CompletableFuture.supplyAsync(() -> {
    // Context no longer available here!
    return reportService.generate(id);
  });
}

// ✅ CORRECT - Preserve context
@GetMapping("/reports/{id}")
public CompletableFuture<Report> generateReport(@PathVariable String id) {
  IOLSchema context = WebUtils.getIOLSchemaFromScope();

  return CompletableFuture.supplyAsync(() -> {
    WebUtils.setIOLSchemaInScope(context);
    try {
      return reportService.generate(id);
    } finally {
      WebUtils.removeIOLSchemaFromScope();
    }
  });
}
```

---

## Next Steps

1. **Choose Pattern** — Select integration pattern matching your use case
2. **Follow Configuration** — Use provided application properties as template
3. **Implement Services** — Follow code examples in your domain
4. **Test Thoroughly** — Verify context and correlation ID propagation
5. **Monitor Production** — Track correlation IDs through logs

**Integration Patterns provide proven approaches for MCA2 EPS adoption.**

