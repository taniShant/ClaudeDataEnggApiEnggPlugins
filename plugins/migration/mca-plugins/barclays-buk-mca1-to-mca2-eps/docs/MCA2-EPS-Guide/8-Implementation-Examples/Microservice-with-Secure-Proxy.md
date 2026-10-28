# Microservice with Secure Proxy: Advanced Integration

## Executive Summary

Complete microservice example protected behind secure proxy, with service-to-service communication, context propagation, and data masking. Demonstrates advanced MCA2 EPS patterns.

---

## Architecture Overview

```
API Gateway / Secure Proxy
    ↓
[ProxySessionFilter] - Validate proxy session
    ↓
[ContextFilter] - Propagate context
    ↓
OrderService (this microservice)
    ├─ InventoryService (downstream call with RestClientFactory)
    └─ NotificationService (downstream call with RestClientFactory)
```

---

## Step 1: Build Configuration

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
  maven { url "https://repo.barclays.global.com/repo/" }
}

dependencyManagement {
  imports {
    mavenBom "com.barclays.global.mca:mca-java-common-bom:2.3.0"
  }
}

dependencies {
  // Spring Boot
  implementation "org.springframework.boot:spring-boot-starter-web"
  implementation "org.springframework.boot:spring-boot-starter-data-jpa"
  implementation "org.springframework.boot:spring-boot-starter-actuator"
  implementation "org.springframework.cloud:spring-cloud-starter-consul-discovery"
  implementation "org.springframework.cloud:spring-cloud-starter-loadbalancer"

  // MCA2 EPS - Advanced Features
  implementation "com.barclays.global.mca:mca-context"
  implementation "com.barclays.global.mca:mca-filter-core"
  implementation "com.barclays.global.mca:mca-eps-core"
  implementation "com.barclays.global.mca:mca-secure-proxy-core"
  implementation "com.barclays.global.mca:mca-service-client-starter"
  implementation "com.barclays.global.mca:mca-masking"

  // Resilience
  implementation "io.github.resilience4j:resilience4j-spring-boot3:2.1.0"
  implementation "io.github.resilience4j:resilience4j-circuitbreaker:2.1.0"

  // Database
  runtimeOnly "org.postgresql:postgresql:16.0"
  implementation "org.flywaydb:flyway-core"

  // Logging
  implementation "com.barclays.global.mca:mca-logging-config-logback"

  // Testing
  testImplementation "org.springframework.boot:spring-boot-starter-test"
  testImplementation "com.github.tomakehurst:wiremock-jre8:2.35.0"
  testRuntimeOnly "com.h2database:h2"
}
```

---

## Step 2: Domain Models

### Order.java (Enhanced)

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

  private String inventoryReservationId;
  private String notificationId;

  @Column(name = "created_at")
  @Builder.Default
  private LocalDateTime createdAt = LocalDateTime.now();

  @Column(name = "updated_at")
  private LocalDateTime updatedAt;
}
```

### External Service DTOs

```java
// InventoryReserveRequest.java
@Data
public class InventoryReserveRequest {
  private String itemId;
  private Integer quantity;
  private String orderId;
}

// InventoryReserveResponse.java
@Data
public class InventoryReserveResponse {
  private String reservationId;
  private Boolean success;
  private String message;
}

// NotificationRequest.java
@Data
public class NotificationRequest {
  @Masked(pattern = MaskingPattern.EMAIL)
  private String customerEmail;

  private String orderId;
  private BigDecimal amount;
  private String status;
}
```

---

## Step 3: Service Layer with Downstream Calls

### OrderService.java (Enhanced)

```java
package com.example.order.service;

import com.barclays.global.mca.libs.service.client.RestClientFactory;
import com.barclays.global.mca.libs.core.exceptions.ServerException;
import com.example.order.domain.*;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;

@Service
@Slf4j
@Transactional
public class OrderService {

  private final OrderRepository repository;
  private final RestClientFactory clientFactory;

  @Autowired
  public OrderService(
    OrderRepository repository,
    RestClientFactory clientFactory
  ) {
    this.repository = repository;
    this.clientFactory = clientFactory;
  }

  @CircuitBreaker(
    name = "orderCreation",
    fallbackMethod = "createOrderFallback"
  )
  public Order createOrder(CreateOrderRequest request) {
    logger.info("Creating order for customer: {}", request.getCustomerId());

    // 1. Create order
    Order order = Order.builder()
      .customerId(request.getCustomerId())
      .amount(request.getAmount())
      .status(OrderStatus.PENDING)
      .build();

    Order saved = repository.save(order);
    logger.info("Order created: {}", saved.getId());

    // 2. Reserve inventory (downstream service call)
    try {
      reserveInventory(saved);
      order.setStatus(OrderStatus.RESERVED);
    } catch (Exception e) {
      logger.error("Inventory reservation failed", e);
      order.setStatus(OrderStatus.FAILED);
      throw new ServerException("Failed to reserve inventory: " + e.getMessage());
    }

    // 3. Send notification (downstream service call)
    try {
      sendNotification(saved);
    } catch (Exception e) {
      logger.warn("Notification failed (non-critical)", e);
      // Don't fail order if notification fails
    }

    return repository.save(order);
  }

  @CircuitBreaker(
    name = "inventoryReserve",
    fallbackMethod = "reserveInventoryFallback"
  )
  private void reserveInventory(Order order) {
    logger.debug("Reserving inventory for order: {}", order.getId());

    RestTemplate client = clientFactory.createRestTemplate();
    // Context automatically propagated in headers

    InventoryReserveRequest request = new InventoryReserveRequest();
    request.setItemId(order.getId());
    request.setQuantity(1);
    request.setOrderId(order.getId());

    try {
      InventoryReserveResponse response = client.postForObject(
        "http://inventory-service/api/inventory/reserve",
        request,
        InventoryReserveResponse.class
      );

      if (response != null && response.getSuccess()) {
        order.setInventoryReservationId(response.getReservationId());
        logger.info("Inventory reserved: {}", response.getReservationId());
      } else {
        throw new ServerException("Inventory reservation failed");
      }
    } catch (Exception e) {
      logger.error("Inventory service error", e);
      throw new ServerException("Inventory service unavailable: " + e.getMessage());
    }
  }

  public void reserveInventoryFallback(Order order, Exception e) {
    logger.warn("Inventory service circuit breaker open, using fallback", e);
    // Could implement fallback logic or rethrow
    throw new ServerException("Inventory service temporarily unavailable");
  }

  private void sendNotification(Order order) {
    logger.debug("Sending notification for order: {}", order.getId());

    RestTemplate client = clientFactory.createRestTemplate();

    NotificationRequest request = new NotificationRequest();
    request.setOrderId(order.getId());
    request.setAmount(order.getAmount());
    request.setStatus(order.getStatus().toString());
    // Email will be masked in logs automatically

    try {
      client.postForObject(
        "http://notification-service/api/notifications/send",
        request,
        Void.class
      );

      logger.info("Notification sent for order: {}", order.getId());
    } catch (Exception e) {
      logger.warn("Failed to send notification", e);
      // Non-critical, don't fail order
    }
  }

  public Order getOrder(String orderId) {
    return repository.findById(orderId)
      .orElseThrow(() -> new OrderNotFoundException(orderId));
  }
}
```

---

## Step 4: Controller with Secure Proxy

### OrderController.java (Secure)

```java
package com.example.order.controller;

import com.barclays.global.mca.libs.context.data.CustomerContext;
import com.barclays.global.mca.libs.context.data.annotations.IOLContext;
import com.barclays.global.mca.libs.response.Response;
import com.barclays.global.mca.libs.core.exceptions.AuthorizationException;
import com.example.order.domain.*;
import com.example.order.service.OrderService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import jakarta.validation.Valid;

@RestController
@RequestMapping("/api/orders")
@Slf4j
public class OrderController {

  private final OrderService orderService;

  @Autowired
  public OrderController(OrderService orderService) {
    this.orderService = orderService;
  }

  @PostMapping
  public ResponseEntity<Response<OrderResponse>> createOrder(
    @Valid @RequestBody CreateOrderRequest request,
    @IOLContext CustomerContext context
  ) {
    try {
      // Validate context is present (ensures proxy authenticated)
      if (context == null) {
        throw new AuthorizationException("Authentication required");
      }

      logger.info("Creating order for customer: {}", context.getCustomerId());

      // Verify customer in request matches context
      if (!context.getCustomerId().equals(request.getCustomerId())) {
        throw new AuthorizationException(
          "Customer ID mismatch: " + request.getCustomerId()
        );
      }

      Order order = orderService.createOrder(request);

      return ResponseEntity.ok(
        Response.assemble()
          .status("SUCCESS")
          .data(OrderResponse.from(order))
          .build()
      );

    } catch (AuthorizationException e) {
      logger.warn("Authorization failed", e);
      return ResponseEntity.status(403)
        .body(Response.assemble()
          .status("UNAUTHORIZED")
          .error(e.getMessage())
          .build()
        );
    }
  }

  @GetMapping("/{id}")
  public ResponseEntity<Response<OrderResponse>> getOrder(
    @PathVariable String id,
    @IOLContext CustomerContext context
  ) {
    if (context == null) {
      throw new AuthorizationException("Authentication required");
    }

    Order order = orderService.getOrder(id);

    // Verify customer can view this order
    if (!context.getCustomerId().equals(order.getCustomerId())) {
      throw new AuthorizationException(
        "Cannot access order: " + id
      );
    }

    return ResponseEntity.ok(
      Response.assemble()
        .status("SUCCESS")
        .data(OrderResponse.from(order))
        .build()
    );
  }
}
```

---

## Step 5: Configuration

### SimpleOrderServiceApplication.java

```java
package com.example.order;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.cloud.loadbalancer.annotation.LoadBalancerClient;
import com.barclays.global.mca.libs.eps.config.EnableExperienceAPI;
import com.barclays.global.mca.libs.secure.proxy.config.EnableSecureProxy;
import com.barclays.global.mca.libs.service.client.config.EnableServiceClient;

@SpringBootApplication
@EnableDiscoveryClient
@LoadBalancerClient(name = "order-service")
@EnableExperienceAPI                    // Core EPS
@EnableSecureProxy                      // Proxy authentication (includes context storage)
@EnableServiceClient                    // Service-to-service calls
public class SimpleOrderServiceApplication {

  public static void main(String[] args) {
    SpringApplication.run(SimpleOrderServiceApplication.class, args);
  }
}
```

### application.properties

```properties
# Application
spring.application.name=order-service
server.port=8080

# Service Discovery (Consul)
spring.cloud.consul.enabled=true
spring.cloud.consul.host=consul.internal
spring.cloud.consul.port=8500
spring.cloud.service-registry.auto-registration.enabled=true
spring.cloud.consul.health-check-interval=10s

# Database
spring.datasource.url=jdbc:postgresql://db.internal:5432/order_service_db
spring.datasource.username=${DB_USER}
spring.datasource.password=${DB_PASSWORD}
spring.datasource.hikari.maximum-pool-size=25
spring.datasource.hikari.leak-detection-threshold=60000

# JPA
spring.jpa.hibernate.ddl-auto=validate

# EPS Configuration
mca.eps.enabled=true

# Secure Proxy
mca.proxy.enabled=true
mca.proxy.trusted-headers=X-UserContext,X-CustomerContext,X-Forwarded-For

# Service Client Configuration
mca.service.client.enabled=true
mca.service.client.connect-timeout=5000
mca.service.client.read-timeout=10000

# Data Masking
mca.masking.enabled=true
masking.patterns.email=(?<=.{1}).(?=[^@]*@)
masking.patterns.credit-card=\d{4}(?:\d(?=.\d{3}))

# Circuit Breaker
resilience4j.circuitbreaker.instances.orderCreation.failure-rate-threshold=50
resilience4j.circuitbreaker.instances.orderCreation.wait-duration-in-open-state=10000
resilience4j.circuitbreaker.instances.inventoryReserve.failure-rate-threshold=50
resilience4j.circuitbreaker.instances.inventoryReserve.wait-duration-in-open-state=10000

# Logging
logging.level.root=WARN
logging.level.com.barclays.global.mca=INFO
logging.level.com.example.order=DEBUG
logging.pattern.console=%d{ISO8601} [%X{correlationId}] %5p %logger{36} - %msg%n
```

### application-prod.properties

```properties
server.port=8080
mca.filter.exception.detailed-error-messages=false
logging.level.root=WARN
logging.level.com.barclays.global.mca=WARN
mca.masking.enabled=true
mca.filter.ddos-prevention.enabled=true
```

---

## Step 6: Service Discovery Registration

### ServiceRegistrationConfig.java

```java
package com.example.order.config;

import org.springframework.boot.actuate.health.Health;
import org.springframework.cloud.consul.discovery.ConsulDiscoveryProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class ServiceRegistrationConfig {

  @Bean
  public ConsulDiscoveryProperties consulDiscoveryProperties() {
    ConsulDiscoveryProperties properties = new ConsulDiscoveryProperties();
    properties.setHealthCheckPath("/actuator/health");
    properties.setHealthCheckInterval("10s");
    return properties;
  }
}
```

---

## Step 7: Testing with WireMock

### OrderServiceTest.java

```java
package com.example.order;

import com.github.tomakehurst.wiremock.client.WireMock;
import com.github.tomakehurst.wiremock.junit5.WireMockExtension;
import com.example.order.domain.CreateOrderRequest;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.RegisterExtension;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.test.context.ActiveProfiles;

import java.math.BigDecimal;

import static com.github.tomakehurst.wiremock.client.WireMock.*;
import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class OrderServiceTest {

  @RegisterExtension
  static WireMockExtension wireMock = WireMockExtension.newInstance()
    .port(8081)
    .build();

  @Autowired
  private TestRestTemplate restTemplate;

  @Test
  void shouldCreateOrderAndCallInventoryService() {
    // Mock inventory service
    wireMock.stubFor(post(urlEqualTo("/api/inventory/reserve"))
      .willReturn(ok()
        .withJsonBody(json(
          "{ \"reservationId\": \"res-123\", \"success\": true }"
        ))
      )
    );

    // Mock notification service
    wireMock.stubFor(post(urlEqualTo("/api/notifications/send"))
      .willReturn(ok())
    );

    CreateOrderRequest request = new CreateOrderRequest();
    request.setCustomerId("customer-123");
    request.setAmount(BigDecimal.valueOf(99.99));
    request.setDescription("Test order");

    HttpHeaders headers = new HttpHeaders();
    headers.set("X-CustomerContext", "{\"customerId\":\"customer-123\"}");

    ResponseEntity<String> response = restTemplate.postForEntity(
      "/api/orders",
      request,
      String.class
    );

    assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);

    // Verify downstream calls were made
    wireMock.verify(postRequestedFor(urlEqualTo("/api/inventory/reserve")));
    wireMock.verify(postRequestedFor(urlEqualTo("/api/notifications/send")));
  }

  @Test
  void shouldReturn403WithoutContext() {
    CreateOrderRequest request = new CreateOrderRequest();
    request.setCustomerId("customer-123");
    request.setAmount(BigDecimal.valueOf(99.99));
    request.setDescription("Test order");

    ResponseEntity<String> response = restTemplate.postForEntity(
      "/api/orders",
      request,
      String.class
    );

    assertThat(response.getStatusCode()).isEqualTo(HttpStatus.FORBIDDEN);
  }
}
```

---

## Step 8: Deployment

### docker-compose.yml

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: order_service_db
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - db_data:/var/lib/postgresql/data

  consul:
    image: consul:latest
    ports:
      - "8500:8500"
      - "8600:8600/udp"
    command: agent -server -ui -bootstrap-expect=1 -client=0.0.0.0

  order-service:
    build: .
    environment:
      SPRING_PROFILES_ACTIVE: prod
      DB_USER: postgres
      DB_PASSWORD: postgres
      SPRING_DATASOURCE_URL: jdbc:postgresql://postgres:5432/order_service_db
      SPRING_CLOUD_CONSUL_HOST: consul
    ports:
      - "8080:8080"
    depends_on:
      - postgres
      - consul

volumes:
  db_data:
```

---

## Run & Verify

```bash
# Start infrastructure
docker-compose up -d

# Build and run
./gradlew bootRun

# Test with context (simulating proxy)
curl -X POST http://localhost:8080/api/orders \
  -H "Content-Type: application/json" \
  -H "X-CustomerContext: {\"customerId\":\"customer-123\"}" \
  -d '{
    "customerId": "customer-123",
    "amount": 99.99,
    "description": "Test order"
  }' | jq

# Verify service registration
curl http://localhost:8500/v1/catalog/service/order-service | jq
```

---

## Key Patterns Demonstrated

✅ **Service Discovery** - Consul integration
✅ **Context Propagation** - Automatic header injection
✅ **Secure Proxy** - Authentication via context
✅ **Downstream Calls** - RestClientFactory usage
✅ **Circuit Breaker** - Resilience4j for fault tolerance
✅ **Data Masking** - Email/credit card masking in logs
✅ **Correlation Tracking** - Across service boundaries

**Microservice with Secure Proxy demonstrates production-grade patterns.**

