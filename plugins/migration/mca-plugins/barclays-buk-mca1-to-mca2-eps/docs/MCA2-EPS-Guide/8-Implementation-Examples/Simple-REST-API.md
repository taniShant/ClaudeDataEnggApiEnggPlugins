# Simple REST API: Step-by-Step Implementation

## Executive Summary

Complete, runnable example of minimal REST API using MCA2 EPS framework. Includes all code files, build configuration, and verification steps. Estimated setup time: 2-3 hours.

---

## Project Structure

```
simple-rest-api/
├── build.gradle
├── settings.gradle
├── src/
│   ├── main/
│   │   ├── java/com/example/order/
│   │   │   ├── SimpleRestApiApplication.java
│   │   │   ├── controller/
│   │   │   │   └── OrderController.java
│   │   │   ├── service/
│   │   │   │   └── OrderService.java
│   │   │   ├── domain/
│   │   │   │   ├── Order.java
│   │   │   │   ├── CreateOrderRequest.java
│   │   │   │   └── OrderResponse.java
│   │   │   └── exception/
│   │   │       └── OrderNotFoundException.java
│   │   └── resources/
│   │       ├── application.properties
│   │       ├── application-dev.properties
│   │       └── logback-spring.xml
│   └── test/
│       └── java/com/example/order/
│           └── OrderControllerTest.java
└── README.md
```

---

## Step 1: Create Build Configuration

### build.gradle

```gradle
plugins {
  id "java"
  id "org.springframework.boot" version "3.5.10"
  id "io.spring.dependency-management" version "1.1.6"
}

group = "com.example"
version = "1.0.0"
sourceCompatibility = "21"

repositories {
  mavenCentral()
  maven {
    url "https://repo.barclays.global.com/repo/"  // Your repo URL
  }
}

dependencies {
  // Spring Boot
  implementation "org.springframework.boot:spring-boot-starter-web"
  implementation "org.springframework.boot:spring-boot-starter-data-jpa"
  implementation "org.springframework.boot:spring-boot-starter-actuator"

  // Database
  runtimeOnly "org.postgresql:postgresql:16.0"
  implementation "org.flywaydb:flyway-core"

  // MCA2 EPS Framework
  implementation "com.barclays.global.mca:mca-java-common-bom:2.3.0"
  implementation "com.barclays.global.mca:mca-context"
  implementation "com.barclays.global.mca:mca-context-utils"
  implementation "com.barclays.global.mca:mca-filter-core"
  implementation "com.barclays.global.mca:mca-eps-core"
  implementation "com.barclays.global.mca:mca-exception-handling-core"
  implementation "com.barclays.global.mca:mca-response-handling-core"
  implementation "com.barclays.global.mca:mca-logging-config-logback"

  // Logging & Monitoring
  implementation "org.springframework.boot:spring-boot-starter-logging"

  // Testing
  testImplementation "org.springframework.boot:spring-boot-starter-test"
  testImplementation "org.mockito:mockito-core"
  testRuntimeOnly "com.h2database:h2"
}

test {
  useJUnitPlatform()
}
```

---

## Step 2: Create Domain Models

### Order.java

```java
package com.example.order.domain;

import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "orders")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Order {
  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private String id;

  @Column(nullable = false)
  private String customerId;

  @Column(nullable = false)
  private BigDecimal amount;

  @Enumerated(EnumType.STRING)
  @Builder.Default
  private OrderStatus status = OrderStatus.PENDING;

  @Column(name = "created_at")
  @Builder.Default
  private LocalDateTime createdAt = LocalDateTime.now();

  @Column(name = "updated_at")
  private LocalDateTime updatedAt;
}

enum OrderStatus {
  PENDING, CONFIRMED, COMPLETED, CANCELLED
}
```

### CreateOrderRequest.java

```java
package com.example.order.domain;

import lombok.Data;
import jakarta.validation.constraints.*;
import java.math.BigDecimal;

@Data
public class CreateOrderRequest {
  @NotBlank(message = "Customer ID required")
  private String customerId;

  @NotNull(message = "Amount required")
  @Positive(message = "Amount must be positive")
  private BigDecimal amount;

  @NotBlank(message = "Description required")
  @Size(min = 3, max = 500)
  private String description;
}
```

### OrderResponse.java

```java
package com.example.order.domain;

import lombok.AllArgsConstructor;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@AllArgsConstructor
public class OrderResponse {
  private String id;
  private String customerId;
  private BigDecimal amount;
  private String status;
  private LocalDateTime createdAt;

  public static OrderResponse from(Order order) {
    return new OrderResponse(
      order.getId(),
      order.getCustomerId(),
      order.getAmount(),
      order.getStatus().toString(),
      order.getCreatedAt()
    );
  }
}
```

### OrderNotFoundException.java

```java
package com.example.order.exception;

import com.barclays.global.mca.libs.core.exceptions.NotFoundException;

public class OrderNotFoundException extends NotFoundException {
  public OrderNotFoundException(String orderId) {
    super("Order not found: " + orderId);
  }
}
```

---

## Step 3: Create Service Layer

### OrderService.java

```java
package com.example.order.service;

import com.example.order.domain.*;
import com.example.order.exception.OrderNotFoundException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;

@Service
@Slf4j
@Transactional
public class OrderService {

  private final OrderRepository repository;

  @Autowired
  public OrderService(OrderRepository repository) {
    this.repository = repository;
  }

  public Order createOrder(CreateOrderRequest request) {
    logger.info("Creating order for customer: {}", request.getCustomerId());

    Order order = Order.builder()
      .customerId(request.getCustomerId())
      .amount(request.getAmount())
      .status(OrderStatus.PENDING)
      .build();

    Order saved = repository.save(order);
    logger.info("Order created: {} for customer: {}", saved.getId(), request.getCustomerId());

    return saved;
  }

  @Transactional(readOnly = true)
  public Order getOrder(String orderId) {
    logger.debug("Fetching order: {}", orderId);

    return repository.findById(orderId)
      .orElseThrow(() -> new OrderNotFoundException(orderId));
  }

  @Transactional(readOnly = true)
  public List<Order> getCustomerOrders(String customerId) {
    logger.debug("Fetching orders for customer: {}", customerId);
    return repository.findByCustomerId(customerId);
  }

  public Order confirmOrder(String orderId) {
    logger.info("Confirming order: {}", orderId);

    Order order = getOrder(orderId);
    order.setStatus(OrderStatus.CONFIRMED);
    order.setUpdatedAt(java.time.LocalDateTime.now());

    return repository.save(order);
  }
}
```

### OrderRepository.java

```java
package com.example.order.service;

import com.example.order.domain.Order;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface OrderRepository extends JpaRepository<Order, String> {
  List<Order> findByCustomerId(String customerId);
}
```

---

## Step 4: Create Controller

### OrderController.java

```java
package com.example.order.controller;

import com.barclays.global.mca.libs.context.data.CustomerContext;
import com.barclays.global.mca.libs.context.data.annotations.IOLContext;
import com.barclays.global.mca.libs.response.Response;
import com.barclays.global.mca.libs.response.assembler.ResponseAssembler;
import com.barclays.global.mca.libs.core.exceptions.RequestException;
import com.example.order.domain.*;
import com.example.order.service.OrderService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import jakarta.validation.Valid;
import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/orders")
@Slf4j
public class OrderController {

  private final OrderService orderService;

  @Autowired
  public OrderController(OrderService orderService) {
    this.orderService = orderService;
  }

  /**
   * Create a new order
   * POST /api/orders
   */
  @PostMapping
  public ResponseEntity<Response<OrderResponse>> createOrder(
    @Valid @RequestBody CreateOrderRequest request,
    @IOLContext CustomerContext context
  ) {
    try {
      logger.info("Creating order for customer: {}", request.getCustomerId());

      // Validate customer ID from context matches request
      if (context != null && !context.getCustomerId().equals(request.getCustomerId())) {
        logger.warn("Customer ID mismatch: context={}, request={}",
          context.getCustomerId(), request.getCustomerId());
        throw new RequestException("Customer ID mismatch");
      }

      Order order = orderService.createOrder(request);

      return ResponseEntity.ok(
        Response.assemble()
          .status("SUCCESS")
          .data(OrderResponse.from(order))
          .build()
      );

    } catch (RequestException e) {
      logger.error("Invalid request", e);
      return ResponseEntity.badRequest()
        .body(Response.assemble()
          .status("VALIDATION_ERROR")
          .error(e.getMessage())
          .build()
        );
    }
  }

  /**
   * Get order by ID
   * GET /api/orders/{id}
   */
  @GetMapping("/{id}")
  public ResponseEntity<Response<OrderResponse>> getOrder(
    @PathVariable String id
  ) {
    logger.debug("Fetching order: {}", id);

    Order order = orderService.getOrder(id);

    return ResponseEntity.ok(
      Response.assemble()
        .status("SUCCESS")
        .data(OrderResponse.from(order))
        .build()
    );
  }

  /**
   * Get customer's orders
   * GET /api/customers/{customerId}/orders
   */
  @GetMapping("/customer/{customerId}")
  public ResponseEntity<Response<List<OrderResponse>>> getCustomerOrders(
    @PathVariable String customerId
  ) {
    logger.debug("Fetching orders for customer: {}", customerId);

    List<Order> orders = orderService.getCustomerOrders(customerId);
    List<OrderResponse> responses = orders.stream()
      .map(OrderResponse::from)
      .collect(Collectors.toList());

    return ResponseEntity.ok(
      Response.assemble()
        .status("SUCCESS")
        .data(responses)
        .build()
    );
  }

  /**
   * Confirm order
   * PUT /api/orders/{id}/confirm
   */
  @PutMapping("/{id}/confirm")
  public ResponseEntity<Response<OrderResponse>> confirmOrder(
    @PathVariable String id
  ) {
    logger.info("Confirming order: {}", id);

    Order order = orderService.confirmOrder(id);

    return ResponseEntity.ok(
      Response.assemble()
        .status("SUCCESS")
        .data(OrderResponse.from(order))
        .build()
    );
  }

  /**
   * Global exception handler
   */
  @ExceptionHandler(Exception.class)
  public ResponseEntity<Response<?>> handleException(Exception e) {
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

---

## Step 5: Configure Application

### SimpleRestApiApplication.java

```java
package com.example.order;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import com.barclays.global.mca.libs.eps.config.EnableExperienceAPI;

@SpringBootApplication
@EnableExperienceAPI                    // Enable EPS framework
public class SimpleRestApiApplication {

  public static void main(String[] args) {
    SpringApplication.run(SimpleRestApiApplication.class, args);
  }
}
```

### application.properties

```properties
# Application
spring.application.name=simple-rest-api
server.port=8080

# Database
spring.datasource.url=jdbc:postgresql://localhost:5432/order_db
spring.datasource.username=postgres
spring.datasource.password=postgres
spring.datasource.hikari.maximum-pool-size=10
spring.datasource.hikari.minimum-idle=2

# JPA
spring.jpa.hibernate.ddl-auto=validate
spring.jpa.show-sql=false
spring.jpa.properties.hibernate.dialect=org.hibernate.dialect.PostgreSQLDialect

# Flyway
spring.flyway.enabled=true
spring.flyway.locations=classpath:db/migration

# EPS Configuration
mca.eps.enabled=true

# Logging
logging.level.root=WARN
logging.level.com.barclays.global.mca=INFO
logging.level.com.example.order=DEBUG
logging.pattern.console=%d{ISO8601} [%X{correlationId}] %5p %logger{36} - %msg%n
```

### application-dev.properties

```properties
# Development profile
server.port=8080
spring.datasource.url=jdbc:postgresql://localhost:5432/order_db_dev
spring.jpa.show-sql=true
logging.level.com.barclays.global.mca=DEBUG
logging.level.com.example.order=DEBUG
```

---

## Step 6: Create Database Migration

### db/migration/V1__Create_orders_table.sql

```sql
CREATE TABLE orders (
  id UUID PRIMARY KEY,
  customer_id VARCHAR(255) NOT NULL,
  amount DECIMAL(19, 2) NOT NULL,
  status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP,
  CONSTRAINT amount_positive CHECK (amount > 0)
);

CREATE INDEX idx_customer_id ON orders(customer_id);
CREATE INDEX idx_status ON orders(status);
CREATE INDEX idx_created_at ON orders(created_at DESC);
```

---

## Step 7: Create Tests

### OrderControllerTest.java

```java
package com.example.order;

import com.example.order.domain.CreateOrderRequest;
import com.example.order.domain.OrderResponse;
import com.barclays.global.mca.libs.response.Response;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.test.context.ActiveProfiles;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class OrderControllerTest {

  @Autowired
  private TestRestTemplate restTemplate;

  @Test
  void shouldCreateOrder() {
    CreateOrderRequest request = new CreateOrderRequest();
    request.setCustomerId("customer-123");
    request.setAmount(BigDecimal.valueOf(99.99));
    request.setDescription("Test order");

    ResponseEntity<Response<OrderResponse>> response = restTemplate.postForEntity(
      "/api/orders",
      request,
      Response.class
    );

    assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
    assertThat(response.getBody().getStatus()).isEqualTo("SUCCESS");
  }

  @Test
  void shouldReturnErrorForInvalidAmount() {
    CreateOrderRequest request = new CreateOrderRequest();
    request.setCustomerId("customer-123");
    request.setAmount(BigDecimal.valueOf(-10)); // Invalid
    request.setDescription("Test order");

    ResponseEntity<Response<OrderResponse>> response = restTemplate.postForEntity(
      "/api/orders",
      request,
      Response.class
    );

    assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
  }

  @Test
  void shouldPropagateCorrelationId() {
    HttpHeaders headers = new HttpHeaders();
    headers.set("Correlation-ID", "test-correlation-123");

    ResponseEntity<String> response = restTemplate.exchange(
      "/api/orders/nonexistent",
      org.springframework.http.HttpMethod.GET,
      new org.springframework.http.HttpEntity<>(headers),
      String.class
    );

    // Correlation ID should be in response headers
    assertThat(response.getHeaders().getFirst("Correlation-ID"))
      .isEqualTo("test-correlation-123");
  }
}
```

---

## Step 8: Run & Verify

### Build

```bash
./gradlew clean build
```

### Start PostgreSQL

```bash
docker run -d \
  -e POSTGRES_DB=order_db \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:16
```

### Run Application

```bash
./gradlew bootRun
```

### Test Endpoints

**Create Order:**
```bash
curl -X POST http://localhost:8080/api/orders \
  -H "Content-Type: application/json" \
  -H "X-CustomerContext: {\"customerId\":\"customer-123\"}" \
  -d '{
    "customerId": "customer-123",
    "amount": 99.99,
    "description": "Test order"
  }' | jq
```

**Get Order:**
```bash
curl http://localhost:8080/api/orders/{id} | jq
```

**Check Correlation ID:**
```bash
curl -v http://localhost:8080/api/orders/test | grep -i "correlation-id"
```

---

## Key Learnings

✅ **What Works:**
- Simple REST API with minimal dependencies
- Automatic correlation ID propagation
- Exception handling with proper response envelope
- Context injection via @IOLContext annotation
- Logging with correlation IDs in MDC

⚠️ **Common Pitfalls:**
- Forgetting @EnableExperienceAPI → framework not initialized
- Incorrect exception types → response envelope breaks
- Missing OrderRepository → cannot persist data
- No HTTP headers for context → context is null

---

## Next Steps

1. Add more endpoints following the same pattern
2. Implement service-to-service calls with RestClientFactory
3. Add data masking for sensitive fields
4. Deploy to production with proper configuration profiles

**Simple REST API provides foundation for MCA2 EPS adoption.**

