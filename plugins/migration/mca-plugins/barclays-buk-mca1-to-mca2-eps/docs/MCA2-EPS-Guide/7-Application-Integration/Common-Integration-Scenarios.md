# Common Integration Scenarios: Decision Matrix

## Executive Summary

Quick reference for identifying which MCA2 EPS frameworks to use for common integration scenarios. Includes decision trees, module selection guides, and configuration examples for typical use cases.

---

## Scenario Selection Matrix

### Quick Decision Guide

| Scenario | Use Case | Primary Frameworks | Notes |
|----------|----------|------------------|-------|
| **REST API** | Simple HTTP API | context, filter-core, eps-core | Minimal, ~5 min setup |
| **Microservice** | Service in a mesh | filter-core, context, service-client | Need service discovery |
| **Behind Proxy** | Service behind secure proxy | filter-core, secure-proxy | Session management |
| **Multi-tenant** | Multiple customers | context, filter-core, masking | Customer isolation |
| **Event-driven** | Async processing | filter-core, exception-handling | Event propagation |
| **Batch Job** | Scheduled processing | context, logging-aspects, exception-handling | No HTTP layer |
| **Legacy Integration** | Integrate with MCA1 | bem-client, mis-client, context | Compatibility layer |

---

## Scenario 1: REST API (Simple)

### Use When
- Standalone REST service
- No service-to-service calls
- Simple logging requirements
- Single environment deployment

### Technology Stack
```gradle
// build.gradle
dependencies {
  implementation "org.springframework.boot:spring-boot-starter-web"
  implementation "com.barclays.global.mca:mca-context"
  implementation "com.barclays.global.mca:mca-filter-core"
  implementation "com.barclays.global.mca:mca-eps-core"
  implementation "com.barclays.global.mca:mca-logging-config-logback"
}
```

### Application Setup
```java
@SpringBootApplication
@EnableExperienceAPI
public class SimpleApiApp { }
```

### Controller Pattern
```java
@RestController
@RequestMapping("/api/items")
public class ItemController {

  @PostMapping
  public ResponseEntity<Response<ItemResponse>> createItem(
    @RequestBody CreateItemRequest request
  ) {
    Item item = itemService.create(request);
    return ResponseEntity.ok(
      Response.assemble()
        .data(new ItemResponse(item))
        .build()
    );
  }

  @ExceptionHandler(ItemNotFoundException.class)
  public ResponseEntity<Response<?>> handleNotFound(ItemNotFoundException e) {
    return ResponseEntity.notFound().build();
  }
}
```

### Configuration
```properties
mca.eps.enabled=true
logging.level.root=INFO
```

### Implementation Time
⏱️ **~2-3 hours** including testing

---

## Scenario 2: Microservice Architecture

### Use When
- Multiple interdependent services
- Service-to-service communication
- Shared context across services
- API gateway or service mesh

### Technology Stack
```gradle
// build.gradle
dependencies {
  implementation "org.springframework.boot:spring-boot-starter-web"
  implementation "com.barclays.global.mca:mca-context"
  implementation "com.barclays.global.mca:mca-filter-core"
  implementation "com.barclays.global.mca:mca-service-client-starter"
  implementation "com.barclays.global.mca:mca-logging-config-logback"
  implementation "io.github.resilience4j:resilience4j-spring-boot3"
}
```

### Service Communication Pattern
```java
// OrderService (calling InventoryService)
@Service
public class OrderService {

  private final RestClientFactory clientFactory;

  @Autowired
  public OrderService(RestClientFactory clientFactory) {
    this.clientFactory = clientFactory;
  }

  public OrderResult processOrder(CreateOrderRequest request) {
    // Context automatically propagated
    RestTemplate client = clientFactory.createRestTemplate();

    InventoryResponse inventory = client.postForObject(
      "http://inventory-service/api/inventory/reserve",
      new ReserveRequest(request.getItemId(), request.getQuantity()),
      InventoryResponse.class
    );

    // Context automatically included in X-* headers
  }
}
```

### Service Discovery
```properties
# Using Consul
spring.cloud.consul.enabled=true
spring.cloud.consul.host=consul.internal
spring.cloud.consul.port=8500
spring.cloud.service-registry.auto-registration.enabled=true

# Service endpoints
spring.application.name=order-service
```

### Configuration
```properties
mca.eps.enabled=true
mca.service.client.enabled=true

# Circuit breaker for resilience
resilience4j.circuitbreaker.instances.default.failure-rate-threshold=50
resilience4j.circuitbreaker.instances.default.wait-duration-in-open-state=10000
```

### Implementation Time
⏱️ **~4-6 hours** including service discovery setup

---

## Scenario 3: Behind Secure Proxy

### Use When
- Service behind API gateway/secure proxy
- External authentication (OAuth, mTLS)
- Session management needed
- Request forwarding/routing

### Technology Stack
```gradle
// build.gradle
dependencies {
  implementation "com.barclays.global.mca:mca-secure-proxy-core"
  implementation "com.barclays.global.mca:mca-service-client-starter"
}
```

> **Note:** Context storage (RDB, MongoDB, EHCache backends) is managed by the Secure Proxy module. See the Secure Proxy documentation for context store backend selection and configuration.

### Application Setup
```java
@SpringBootApplication
@EnableExperienceAPI
@EnableSecureProxy
@EnableServiceClient
public class ProxiedServiceApp { }
```

### Proxy Configuration
```properties
# Proxy settings
mca.proxy.enabled=true
mca.proxy.trusted-headers=X-UserContext,X-CustomerContext,X-Forwarded-For
mca.proxy.session-timeout=3600

# Context propagation
mca.filter.context.enabled=true
```

### Request Handler
```java
@RestController
@RequestMapping("/api/accounts")
public class AccountController {

  @GetMapping("/{id}")
  public ResponseEntity<Response<Account>> getAccount(
    @PathVariable String id,
    @IOLContext CustomerContext context,  // Context injected from headers
    HttpServletRequest request
  ) {
    // Context already validated by ProxySessionFilter
    Account account = accountService.get(id, context);
    return ResponseEntity.ok(
      Response.assemble()
        .data(account)
        .build()
    );
  }
}
```

### Implementation Time
⏱️ **~5-7 hours** including proxy integration

---

## Scenario 4: Multi-Tenant SaaS

### Use When
- Multiple independent customers
- Customer data isolation required
- Scalability important
- Shared infrastructure

### Technology Stack
```gradle
// build.gradle
dependencies {
  implementation "com.barclays.global.mca:mca-context"
  implementation "com.barclays.global.mca:mca-filter-core"
  implementation "com.barclays.global.mca:mca-masking"
  implementation "org.springframework.data:spring-data-mongodb"
}
```

### Tenant Isolation Pattern
```java
@Component
@Order(0)  // Execute first
public class TenantContextFilter extends OncePerRequestFilter {

  @Override
  protected void doFilterInternal(
    HttpServletRequest request,
    HttpServletResponse response,
    FilterChain chain
  ) throws ServletException, IOException {
    String customerId = extractTenantId(request);

    try {
      // Parse tenant context from header and set in scope
      IOLSchema schema = parseTenantContext(customerId);
      WebUtils.setIOLSchemaInScope(schema);

      // Downstream services use tenant context
      chain.doFilter(request, response);
    } finally {
      WebUtils.removeIOLSchemaFromScope();
    }
  }

  private String extractTenantId(HttpServletRequest request) {
    String context = request.getHeader("X-CustomerContext");
    return context != null ? context : getThreadLocalTenant();
  }
}
```

### Data Repository
```java
@Repository
public class CustomerDataRepository {

  private final MongoTemplate mongoTemplate;

  public List<Order> findOrdersByCustomer(String customerId) {
    Query query = Query.query(
      Criteria.where("customerId").is(customerId)
    );
    return mongoTemplate.find(query, Order.class);
  }
}
```

### Configuration
```properties
# Multi-tenant setup
mca.eps.enabled=true
mca.multi-tenant.enabled=true
spring.data.mongodb.uri=mongodb://localhost/saas_db
mca.masking.enabled=true
```

### Implementation Time
⏱️ **~8-10 hours** including isolation validation

---

## Scenario 5: Event-Driven Processing

### Use When
- Asynchronous operations important
- Loose coupling required
- Multiple subscribers
- Order guarantee needed

### Technology Stack
```gradle
// build.gradle
dependencies {
  implementation "com.barclays.global.mca:mca-context"
  implementation "org.springframework.boot:spring-boot-starter-amqp"
  // OR
  // implementation "org.springframework.kafka:spring-kafka"
}
```

### Event Publisher
```java
@Service
public class OrderService {

  private final ApplicationEventPublisher eventPublisher;
  private final OrderRepository repository;

  @Transactional
  public Order createOrder(CreateOrderRequest request) {
    Order order = repository.save(new Order(request));

    // Publish event with correlation context
    OrderCreatedEvent event = new OrderCreatedEvent(
      order.getId(),
      request.getCustomerId(),
      MDC.get("correlationId")  // Preserve for tracing
    );
    eventPublisher.publishEvent(event);

    return order;
  }
}
```

### Event Subscriber
```java
@Service
@Slf4j
public class NotificationService {

  @EventListener
  @Transactional
  public void onOrderCreated(OrderCreatedEvent event) {
    try {
      logger.info("Sending notification for order: {}", event.getOrderId());
      emailService.send(event.getCustomerId());
    } catch (Exception e) {
      logger.error("Failed to send notification", e);
      throw new NotificationException("Send failed");
    }
  }
}
```

### Message Queue Configuration
```properties
# RabbitMQ
spring.rabbitmq.host=rabbitmq.internal
spring.rabbitmq.port=5672
spring.rabbitmq.username=${RABBITMQ_USER}
spring.rabbitmq.password=${RABBITMQ_PASSWORD}

# Kafka
# spring.kafka.bootstrap-servers=kafka.internal:9092
```

### Implementation Time
⏱️ **~6-8 hours** including message queue setup

---

## Scenario 6: Batch Processing

### Use When
- Scheduled jobs
- Large data processing
- No HTTP request context
- Bulk operations needed

### Application Setup
```java
@SpringBootApplication
@EnableExperienceAPI
public class BatchProcessorApp { }
```

### Batch Job Implementation
```java
@Component
public class DailyReportingJob {

  private final ReportService reportService;

  @Scheduled(cron = "0 0 * * * *")  // Daily at midnight
  @Transactional
  public void generateDailyReports() {
    String batchId = UUID.randomUUID().toString();
    MDC.put("batchId", batchId);
    MDC.put("correlationId", batchId);

    try {
      List<Customer> customers = customerRepository.findAll();

      for (Customer customer : customers) {
        try {
          // Set customer context for each iteration
          IOLSchema schema = createContextForCustomer(customer);
          WebUtils.setIOLSchemaInScope(schema);

          reportService.generateReport(customer);

        } catch (ReportGenerationException e) {
          logger.warn("Failed to generate report for customer: {}", customer.getId(), e);
        } finally {
          WebUtils.removeIOLSchemaFromScope();
        }
      }
    } finally {
      MDC.clear();
    }
  }

  private IOLSchema createContextForCustomer(Customer customer) {
    IOLSchema schema = new IOLSchema();
    CustomerContext ctx = new CustomerContext();
    ctx.setCustomerId(customer.getId());
    ctx.setCustomerName(customer.getName());
    schema.setContext("customer", ctx);
    return schema;
  }
}
```

### Configuration
```properties
mca.eps.enabled=true
logging.level.com.barclays.global.mca=DEBUG

# Spring Scheduler
spring.task.scheduling.pool.size=5
spring.task.scheduling.thread-name-prefix=batch-
```

### Implementation Time
⏱️ **~3-4 hours** including scheduling setup

---

## Scenario 7: Legacy Integration (MCA1 Compatibility)

### Use When
- Migrating from MCA1 to MCA2
- Need to call MCA1 services
- Transitional architecture
- Gradual migration over multiple quarters

### Adapter Layer
```gradle
// build.gradle
dependencies {
  // MCA2 libraries
  implementation "com.barclays.global.mca:mca-context"
  implementation "com.barclays.global.mca:mca-filter-core"

  // Legacy MCA1 compatibility
  implementation "com.barclays.global.mca:bem-client"
  implementation "com.barclays.global.mca:mis-client"
}
```

### Context Translation
```java
@Component
public class MCA1ContextAdapter {

  public void translateToMCA1(IOLSchema mca2Context, Map<String, String> mca1Headers) {
    CustomerContext customer = mca2Context.getContext("customer");
    if (customer != null) {
      mca1Headers.put("X-BEM-CUSTOMER", customer.getCustomerId());
      mca1Headers.put("X-BEM-NAME", customer.getCustomerName());
    }

    UserContext user = mca2Context.getContext("user");
    if (user != null) {
      mca1Headers.put("X-BEM-USER", user.getUserId());
    }
  }

  public IOLSchema translateFromMCA1(Map<String, String> mca1Headers) {
    IOLSchema schema = new IOLSchema();

    CustomerContext customer = new CustomerContext();
    customer.setCustomerId(mca1Headers.get("X-BEM-CUSTOMER"));
    customer.setCustomerName(mca1Headers.get("X-BEM-NAME"));
    schema.setContext("customer", customer);

    UserContext user = new UserContext();
    user.setUserId(mca1Headers.get("X-BEM-USER"));
    schema.setContext("user", user);

    return schema;
  }
}
```

### Implementation Time
⏱️ **~8-12 hours** including comprehensive testing

---

## Decision Tree: Which Scenario Fits?

```
Start
  │
  ├─ Is this a new application?
  │  ├─ YES → Simple REST API? → Scenario 1
  │  │
  │  └─ Part of a larger system?
  │     ├─ Multiple services? → Scenario 2 (Microservices)
  │     ├─ Behind API gateway? → Scenario 3 (Secure Proxy)
  │     ├─ Multiple customers? → Scenario 4 (Multi-tenant)
  │     ├─ Async processing? → Scenario 5 (Event-driven)
  │     └─ Background jobs? → Scenario 6 (Batch)
  │
  └─ Is this migrating from MCA1?
     ├─ YES → Need compatibility? → Scenario 7 (Legacy)
     └─ Phase migration plan needed
```

---

## Quick Start: Choose Your Scenario

1. **Identify needs:** Which scenario matches your use case?
2. **Review stack:** Use provided Gradle dependencies
3. **Set up application:** Copy-paste from examples
4. **Configure:** Use provided properties templates
5. **Test:** Verify context and correlation ID propagation

**Common Integration Scenarios provide proven implementation patterns.**

