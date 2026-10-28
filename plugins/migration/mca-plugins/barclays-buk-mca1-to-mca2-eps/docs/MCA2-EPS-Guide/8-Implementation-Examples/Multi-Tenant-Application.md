# Multi-Tenant Application: Scaling Across Customers

## Executive Summary

Complete multi-tenant SaaS application with customer isolation, dynamic data routing, and per-tenant configuration. Demonstrates scalable architecture for serving multiple customers from single application.

> **Note:** Context storage backends (RDB, MongoDB, EHCache) are part of the **Secure Proxy** module, not EPS. This example focuses on multi-tenant patterns using core EPS features (context propagation, filtering, data masking). If your multi-tenant application also requires Secure Proxy session management, refer to the Secure Proxy documentation for context store configuration.

---

## Architecture

```
Request with X-CustomerContext header
    ↓
[TenantContextFilter] (Order: 1)
    ├─ Extract customer ID from context
    ├─ Load customer config
    └─ Route to correct tenant database
    ↓
[ContextFilter] (Order: 2)
    └─ Propagate context through request
    ↓
[AuthorizationFilter] (Order: 3)
    └─ Verify tenant authorization
    ↓
[Service Layer]
    └─ Execute in tenant context
    ↓
Response with tenant data
```

---

## Dependency Configuration

### build.gradle

```gradle
plugins {
  id "java"
  id "org.springframework.boot" version "3.5.10"
  id "io.spring.dependency-management" version "1.1.6"
}

dependencies {
  implementation "org.springframework.boot:spring-boot-starter-web"
  implementation "org.springframework.boot:spring-boot-starter-data-mongodb"
  implementation "org.springframework.boot:spring-boot-starter-data-jpa"

  // MCA2 Multi-tenant
  implementation "com.barclays.global.mca:mca-context"
  implementation "com.barclays.global.mca:mca-filter-core"
  implementation "com.barclays.global.mca:mca-masking"
  implementation "com.barclays.global.mca:mca-logging-config-logback"

  // Tenant data routing
  implementation "org.springframework.cloud:spring-cloud-starter-loadbalancer"
  implementation "org.springframework.boot:spring-boot-starter-jdbc"

  // For multi-datasource routing
  implementation "org.liquibase:liquibase-core"

  testImplementation "org.springframework.boot:spring-boot-starter-test"
  testImplementation "de.flapdoodle.embed:de.flapdoodle.embed.mongo"
}
```

---

## Domain Models

### Tenant Configuration

```java
package com.example.tenant;

import org.springframework.data.mongodb.core.mapping.Document;
import lombok.Data;

@Document(collection = "tenant_config")
@Data
public class TenantConfig {
  private String customerId;
  private String customerName;
  private String databaseUrl;      // Tenant's private database
  private String databasePassword;
  private Boolean active;
  private Long createdAt;
  private String billingTier;      // Premium, Standard, Free
}
```

### Tenant Context

```java
package com.example.tenant;

import lombok.Data;
import java.util.Map;

@Data
public class TenantContextData {
  private String customerId;
  private String customerName;
  private String databaseKey;
  private Map<String, Object> metadata;
}
```

### Multi-Tenant User

```java
package com.example.user.domain;

import jakarta.persistence.*;
import lombok.Data;

@Entity
@Table(name = "users")
@Data
public class User {
  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private String id;

  @Column(nullable = false)
  private String tenantId;  // Partitioned by tenant

  @Column(nullable = false, unique = true)
  private String email;

  private String name;
  private String role;
}
```

---

## Tenant Context Filter

### TenantContextFilter.java

```java
package com.example.tenant.filter;

import com.barclays.global.mca.libs.context.data.IOLSchema;
import com.barclays.global.mca.libs.context.webutil.WebUtils;
import com.barclays.global.mca.libs.filter.core.OncePerRequestFilter;
import com.example.tenant.TenantConfig;
import com.example.tenant.TenantContextData;
import com.example.tenant.service.TenantConfigService;
import com.example.tenant.datasource.TenantDataSourceManager;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;

@Component
@Slf4j
public class TenantContextFilter extends OncePerRequestFilter {

  private final TenantConfigService tenantConfigService;
  private final TenantDataSourceManager dataSourceManager;

  @Autowired
  public TenantContextFilter(
    TenantConfigService tenantConfigService,
    TenantDataSourceManager dataSourceManager
  ) {
    this.tenantConfigService = tenantConfigService;
    this.dataSourceManager = dataSourceManager;
  }

  @Override
  protected void doFilterInternal(
    HttpServletRequest request,
    HttpServletResponse response,
    FilterChain chain
  ) throws ServletException, IOException {
    try {
      // Extract customer context from header
      String contextHeader = request.getHeader("X-CustomerContext");

      if (contextHeader != null) {
        // Parse JSON context
        TenantContextData tenantContext = parseTenantContext(contextHeader);

        // Load tenant configuration from MongoDB
        TenantConfig tenantConfig = tenantConfigService.getTenantConfig(
          tenantContext.getCustomerId()
        );

        if (tenantConfig == null || !tenantConfig.getActive()) {
          logger.warn("Tenant not found or inactive: {}",
            tenantContext.getCustomerId());
          response.setStatus(403);
          response.getWriter().write("Tenant not found");
          return;
        }

        // Set tenant data source (routes to correct database)
        dataSourceManager.setCurrentTenant(tenantConfig.getDatabaseKey());

        logger.debug("Tenant context loaded: {} (db: {})",
          tenantContext.getCustomerId(),
          tenantConfig.getDatabaseKey()
        );

        // Create IOLSchema with tenant info
        IOLSchema schema = new IOLSchema();
        schema.put("tenantId", tenantContext.getCustomerId());
        schema.put("tenantName", tenantContext.getCustomerName());
        schema.put("databaseKey", tenantConfig.getDatabaseKey());

        // Set in request scope (available to entire request)
        WebUtils.setIOLSchemaInScope(schema);
      }

      chain.doFilter(request, response);

    } finally {
      // Clean up tenant context
      dataSourceManager.clearCurrentTenant();
      WebUtils.removeIOLSchemaFromScope();
    }
  }

  private TenantContextData parseTenantContext(String contextHeader) {
    // Parse JSON: {"customerId": "tenant-123", "customerName": "Acme Corp"}
    // Implementation using Jackson ObjectMapper
    // Simplified for brevity
    TenantContextData data = new TenantContextData();
    // Parse logic here
    return data;
  }

  @Override
  protected boolean shouldNotFilter(HttpServletRequest request) throws ServletException {
    String path = request.getRequestURI();
    return path.startsWith("/health") || path.startsWith("/public");
  }
}
```

---

## Multi-Datasource Routing

### TenantDataSourceManager.java

```java
package com.example.tenant.datasource;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import java.util.HashMap;
import java.util.Map;

@Component
@Slf4j
public class TenantDataSourceManager {

  private static final ThreadLocal<String> CURRENT_TENANT = new ThreadLocal<>();
  private final Map<String, javax.sql.DataSource> tenantDataSources = new HashMap<>();

  public void setCurrentTenant(String tenantDatabaseKey) {
    CURRENT_TENANT.set(tenantDatabaseKey);
    logger.debug("Current tenant set to: {}", tenantDatabaseKey);
  }

  public String getCurrentTenant() {
    return CURRENT_TENANT.get();
  }

  public void clearCurrentTenant() {
    CURRENT_TENANT.remove();
  }

  public javax.sql.DataSource getDataSource(String key) {
    String tenant = getCurrentTenant();
    if (tenant == null) {
      throw new IllegalStateException("No tenant context set");
    }

    javax.sql.DataSource ds = tenantDataSources.get(tenant);
    if (ds == null) {
      throw new IllegalStateException(
        "DataSource not configured for tenant: " + tenant
      );
    }

    return ds;
  }
}
```

### TenantAwareDataSource.java

```java
package com.example.tenant.datasource;

import lombok.extern.slf4j.Slf4j;
import org.springframework.jdbc.datasource.AbstractDataSource;
import java.sql.Connection;

@Slf4j
public class TenantAwareDataSource extends AbstractDataSource {

  private final TenantDataSourceManager manager;

  public TenantAwareDataSource(TenantDataSourceManager manager) {
    this.manager = manager;
  }

  @Override
  public Connection getConnection() {
    String tenant = manager.getCurrentTenant();
    if (tenant == null) {
      throw new IllegalStateException("No tenant context");
    }

    logger.debug("Getting connection for tenant: {}", tenant);

    javax.sql.DataSource dataSource = manager.getDataSource(tenant);
    try {
      return dataSource.getConnection();
    } catch (Exception e) {
      logger.error("Failed to get connection for tenant: {}", tenant, e);
      throw new RuntimeException(e);
    }
  }

  @Override
  public Connection getConnection(String username, String password) {
    throw new UnsupportedOperationException();
  }
}
```

---

## Service Layer

### TenantConfigService.java

```java
package com.example.tenant.service;

import com.example.tenant.TenantConfig;
import com.example.tenant.repository.TenantConfigRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

@Service
@Slf4j
public class TenantConfigService {

  private final TenantConfigRepository repository;

  @Autowired
  public TenantConfigService(TenantConfigRepository repository) {
    this.repository = repository;
  }

  @Cacheable(value = "tenant_config", key = "#customerId", ttl = 3600)
  public TenantConfig getTenantConfig(String customerId) {
    logger.debug("Loading tenant config for: {}", customerId);

    TenantConfig config = repository.findByCustomerId(customerId);

    if (config != null) {
      logger.info("Tenant config loaded: {} (active: {})",
        customerId, config.getActive());
    } else {
      logger.warn("No tenant config found for: {}", customerId);
    }

    return config;
  }
}
```

### UserService.java (Tenant-Aware)

```java
package com.example.user.service;

import com.barclays.global.mca.libs.context.webutil.WebUtils;
import com.example.user.domain.User;
import com.example.user.repository.UserRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Slf4j
@Transactional
public class UserService {

  private final UserRepository repository;

  @Autowired
  public UserService(UserRepository repository) {
    this.repository = repository;
  }

  public User createUser(User user) {
    // Get current tenant from context
    String tenantId = (String) WebUtils.getIOLContext("tenantId");

    if (tenantId == null) {
      throw new IllegalStateException("No tenant context");
    }

    user.setTenantId(tenantId);

    logger.info("Creating user for tenant: {}", tenantId);

    return repository.save(user);
  }

  public User findByEmail(String email) {
    // Query only current tenant's data
    String tenantId = (String) WebUtils.getIOLContext("tenantId");

    return repository.findByTenantIdAndEmail(tenantId, email);
  }
}
```

---

## Controller

### UserController.java (Multi-Tenant)

```java
package com.example.user.controller;

import com.barclays.global.mca.libs.response.Response;
import com.example.user.domain.User;
import com.example.user.service.UserService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/users")
@Slf4j
public class UserController {

  private final UserService userService;

  @Autowired
  public UserController(UserService userService) {
    this.userService = userService;
  }

  @PostMapping
  public ResponseEntity<Response<User>> createUser(
    @RequestBody User user
  ) {
    logger.info("Creating user: {}", user.getEmail());

    User created = userService.createUser(user);

    return ResponseEntity.ok(
      Response.assemble()
        .status("SUCCESS")
        .data(created)
        .build()
    );
  }

  @GetMapping("/by-email/{email}")
  public ResponseEntity<Response<User>> getUserByEmail(
    @PathVariable String email
  ) {
    logger.debug("Fetching user by email: {}", email);

    User user = userService.findByEmail(email);

    if (user == null) {
      return ResponseEntity.notFound().build();
    }

    return ResponseEntity.ok(
      Response.assemble()
        .status("SUCCESS")
        .data(user)
        .build()
    );
  }
}
```

---

## Application Configuration

### MultiTenantApplication.java

```java
package com.example;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cache.annotation.EnableCaching;
import com.barclays.global.mca.libs.eps.config.EnableExperienceAPI;
import com.barclays.global.mca.libs.masking.config.EnableMasking;

@SpringBootApplication
@EnableCaching
@EnableExperienceAPI
@EnableMasking                         // Data masking
public class MultiTenantApplication {

  public static void main(String[] args) {
    SpringApplication.run(MultiTenantApplication.class, args);
  }
}
```

### application.properties

```properties
# Application
spring.application.name=multi-tenant-saas
server.port=8080

# MongoDB for tenant config
spring.data.mongodb.uri=mongodb://mongo:27017/saas_db
spring.data.mongodb.auto-index-creation=true

# Tenant-specific databases (example: PostgreSQL per tenant)
# Configured dynamically via TenantDataSourceManager

# Data Masking
mca.masking.enabled=true
masking.patterns.email=(?<=.{1}).(?=[^@]*@)
masking.patterns.phone=(?<=.{2}).(?=[^-]*-)

# Logging
logging.level.root=WARN
logging.level.com.barclays.global.mca=INFO
logging.level.com.example=DEBUG
logging.pattern.console=%d{ISO8601} [%X{correlationId}] [%X{tenantId}] %5p %msg%n
```

---

## Testing

### MultiTenantTest.java

```java
package com.example;

import com.example.user.domain.User;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.test.context.ActiveProfiles;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class MultiTenantTest {

  @Autowired
  private TestRestTemplate restTemplate;

  @Test
  void shouldIsolateTenantData() {
    // Create user for Tenant A
    HttpHeaders headersA = new HttpHeaders();
    headersA.set("X-CustomerContext",
      "{\"customerId\": \"tenant-a\", \"customerName\": \"Acme Corp\"}");

    User userA = new User();
    userA.setEmail("john@acme.com");
    userA.setName("John Doe");

    ResponseEntity<User> responseA = restTemplate.exchange(
      "/api/users",
      org.springframework.http.HttpMethod.POST,
      new HttpEntity<>(userA, headersA),
      User.class
    );

    assertThat(responseA.getStatusCode()).isEqualTo(HttpStatus.OK);

    // Create user for Tenant B
    HttpHeaders headersB = new HttpHeaders();
    headersB.set("X-CustomerContext",
      "{\"customerId\": \"tenant-b\", \"customerName\": \"Beta Inc\"}");

    User userB = new User();
    userB.setEmail("jane@beta.com");
    userB.setName("Jane Smith");

    ResponseEntity<User> responseB = restTemplate.exchange(
      "/api/users",
      org.springframework.http.HttpMethod.POST,
      new HttpEntity<>(userB, headersB),
      User.class
    );

    assertThat(responseB.getStatusCode()).isEqualTo(HttpStatus.OK);

    // Verify Tenant A cannot see Tenant B's user
    ResponseEntity<User> getTenantBUser = restTemplate.exchange(
      "/api/users/by-email/jane@beta.com",
      org.springframework.http.HttpMethod.GET,
      new HttpEntity<>(headersA),  // Using Tenant A's context
      User.class
    );

    // Should not find user (from different tenant)
    assertThat(getTenantBUser.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
  }
}
```

---

## Deployment

### docker-compose.yml

```yaml
version: '3.8'
services:
  mongo:
    image: mongo:7
    environment:
      MONGO_INITDB_DATABASE: saas_db
    ports:
      - "27017:27017"

  tenant-postgres-a:
    image: postgres:16
    environment:
      POSTGRES_DB: tenant_a_db
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"

  tenant-postgres-b:
    image: postgres:16
    environment:
      POSTGRES_DB: tenant_b_db
      POSTGRES_PASSWORD: password
    ports:
      - "5433:5432"

  saas-app:
    build: .
    environment:
      SPRING_PROFILES_ACTIVE: prod
      SPRING_DATA_MONGODB_URI: mongodb://mongo:27017/saas_db
    ports:
      - "8080:8080"
    depends_on:
      - mongo
      - tenant-postgres-a
      - tenant-postgres-b
```

---

## Key Patterns

✅ **Tenant Isolation** - Separate databases per tenant
✅ **Dynamic Routing** - ThreadLocal-based datasource selection
✅ **Context Propagation** - Tenant ID in all requests
✅ **Data Masking** - Sensitive data masked in logs
✅ **Query Filtering** - Automatic tenant filtering in repositories

**Multi-Tenant Application demonstrates enterprise SaaS patterns.**

