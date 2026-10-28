---
title: Project Refinement Scenarios Guide
description: Common refinement patterns with before/after examples and state management details
type: advanced
---

# Project Refinement Scenarios - Advanced Guide

## Overview

This guide documents common project refinement scenarios with step-by-step walkthroughs, before/after code examples, and state management implications.

---

## Scenario 1: Add Authentication (JWT)

### Context
Generated project has public endpoints. Need to add JWT authentication to secure them.

### Refinement Steps

**Step 1: Check Current State**
```bash
refine --project-root ./order-service --validate
```

Output: Project state shows 0 security schemes, all endpoints public.

**Step 2: Add Security Scheme to Spec**

Update `order-api.yaml`:
```yaml
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: JWT authentication

security:
  - bearerAuth: []
```

**Step 3: Update Spec in Project**
```bash
refine --project-root ./order-service --spec-update ./order-api.yaml
```

Refinement-agent will:
1. Detect security scheme added
2. Regenerate SecurityConfig.java (if not already present)
3. Add @PreAuthorize annotations to controller methods
4. Update tests with JWT token generation
5. Update application.yml with JWT configuration

**Generated Files Updated**:
- `src/main/java/com/example/config/SecurityConfig.java` (NEW/UPDATED)
- `src/main/java/com/example/controller/*Controller.java` (ANNOTATIONS ADDED)
- `src/test/java/com/example/controller/*ControllerTest.java` (JWT MOCK ADDED)
- `src/main/resources/application.yml` (JWT CONFIG ADDED)
- `.claude/api-engineer-state.json` (SECURITY SCHEMES UPDATED)

**State File Changes**:
```json
{
  "security_schemes": [
    {
      "name": "bearerAuth",
      "type": "http",
      "scheme": "bearer"
    }
  ],
  "endpoints_secured": true,
  "last_refinement": "2026-06-13T10:30:00Z",
  "last_refinement_type": "SPEC_UPDATE"
}
```

**Post-Refinement Verification**:
```bash
./gradlew compileJava     # Verify compilation
./gradlew test            # Verify tests run
./gradlew bootRun         # Verify startup
```

---

## Scenario 2: Add New Resource

### Context
Generated project has User resource. Need to add Product resource with similar patterns.

### Refinement Steps

**Step 1: Add Resource to Spec**

Update `order-api.yaml`:
```yaml
paths:
  /products:
    get:
      operationId: listProducts
      tags: [Product]
      responses:
        200:
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Product'
    post:
      operationId: createProduct
      tags: [Product]
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateProductRequest'
      responses:
        201:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Product'

  /products/{id}:
    get:
      operationId: getProduct
      tags: [Product]
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        200:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Product'
        404:
          description: Product not found

components:
  schemas:
    Product:
      type: object
      properties:
        id:
          type: string
          format: uuid
        name:
          type: string
        price:
          type: number
          minimum: 0
        createdAt:
          type: string
          format: date-time
      required: [id, name, price, createdAt]

    CreateProductRequest:
      type: object
      properties:
        name:
          type: string
        price:
          type: number
          minimum: 0
      required: [name, price]
```

**Step 2: Update Spec in Project**
```bash
refine --project-root ./order-service --spec-update ./order-api.yaml
```

Refinement-agent will:
1. Detect new /products endpoints
2. Create ProductController.java with GET, POST methods
3. Create ProductService interface and implementation
4. Create Product and CreateProductRequest models
5. Create ProductControllerTest.java
6. Create ProductServiceImplTest.java
7. Update application.yml if needed
8. Update state file with new endpoints

**Generated Files**:
- `src/main/java/com/example/controller/ProductController.java` (NEW)
- `src/main/java/com/example/service/ProductService.java` (NEW INTERFACE)
- `src/main/java/com/example/service/impl/ProductServiceImpl.java` (NEW)
- `src/main/java/com/example/model/response/Product.java` (NEW)
- `src/main/java/com/example/model/request/CreateProductRequest.java` (NEW)
- `src/test/java/com/example/controller/ProductControllerTest.java` (NEW)
- `src/test/java/com/example/service/ProductServiceImplTest.java` (NEW)
- `.claude/api-engineer-state.json` (UPDATED)

**Controller Code Generated**:
```java
import com.barclays.api.bap.bld.lib.common.response.Response;
import com.barclays.api.bap.bld.lib.logging.LogFactory;
import com.barclays.api.bap.bld.lib.logging.Logger;
import com.barclays.api.bap.bld.lib.payload.response.ResponseHttpStatus;
import com.barclays.api.bap.bld.lib.payload.response.RestResponse;

@RestController
@RequestMapping("/products")
@RequiredArgsConstructor
public class ProductController {
    private final ProductService productService;
    private static final Logger LOGGER = LogFactory.getLogger(ProductController.class);

    @GetMapping
    public Response listProducts() {
        return RestResponse
                    .assemble()
                    .build(ResponseHttpStatus.OK, 
                          productService.listProducts());
    }

    @PostMapping
    public ResponseEntity<Product> createProduct(@RequestBody CreateProductRequest request) {
        return RestResponse
                    .assemble()
                    .build(ResponseHttpStatus.CREATED, 
                          productService.createProduct(request));
    }

    @GetMapping("/{id}")
    public ResponseEntity<Product> getProduct(@PathVariable String id) {
        return RestResponse
                    .assemble()
                    .build(ResponseHttpStatus.OK, 
                          productService.getProduct(id));
    }
}
```

**State File Changes**:
```json
{
  "endpoints": [
    {"path": "/users", "method": "GET"},
    {"path": "/users", "method": "POST"},
    {"path": "/users/{id}", "method": "GET"},
    {"path": "/products", "method": "GET"},           // NEW
    {"path": "/products", "method": "POST"},          // NEW
    {"path": "/products/{id}", "method": "GET"}       // NEW
  ],
  "schemas": [
    "User", "CreateUserRequest",
    "Product", "CreateProductRequest"                 // NEW
  ],
  "refinements": [
    {
      "timestamp": "2026-06-13T10:45:00Z",
      "type": "SPEC_UPDATE",
      "description": "Added Product resource",
      "affected_files": [
        "ProductController.java",
        "ProductService.java",
        "ProductServiceImpl.java",
        "Product.java",
        "CreateProductRequest.java"
      ]
    }
  ]
}
```

---

## Scenario 3: Integrate New Producer API

### Context
Generated project calls Order Processing Service. Now need to add Payment Service for payment processing.

### Refinement Steps

**Step 1: Obtain Payment Service Spec**

Payment service spec file: `payment-service-api.yaml`
```yaml
openapi: 3.0.3
info:
  title: Payment Service
  version: 1.0.0
servers:
  - url: https://payment-api.internal.example.com

paths:
  /payments:
    post:
      operationId: createPayment
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/PaymentRequest'
      responses:
        201:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Payment'
        400:
          description: Invalid payment request
        500:
          description: Payment processing error

  /payments/{id}:
    get:
      operationId: getPayment
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        200:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Payment'
        404:
          description: Payment not found

components:
  schemas:
    PaymentRequest:
      type: object
      properties:
        orderId:
          type: string
        amount:
          type: number
          minimum: 0
        currency:
          type: string
        method:
          type: string
          enum: [card, bank_transfer, wallet]
      required: [orderId, amount, currency, method]

    Payment:
      type: object
      properties:
        id:
          type: string
          format: uuid
        orderId:
          type: string
        amount:
          type: number
        currency:
          type: string
        status:
          type: string
          enum: [pending, approved, rejected, refunded]
        createdAt:
          type: string
          format: date-time
      required: [id, orderId, amount, currency, status, createdAt]
```

**Step 2: Add Producer Spec Reference**
```bash
refine --project-root ./order-service --add-producer ./payment-service-api.yaml
```

Refinement-agent will:
1. Parse payment service spec
2. Create PaymentGateway interface with methods for each endpoint
3. Create PaymentGatewayImpl with RestClient calls
4. Create client models (PaymentRequest, Payment)
5. Update RestClientConfiguration with PaymentService bean
6. Create PaymentGatewayImplTest
7. Update OrderServiceImpl to inject PaymentGateway
8. Update state file with producer reference

**Generated Files**:
- `src/main/java/com/example/gateway/PaymentGateway.java` (NEW INTERFACE)
- `src/main/java/com/example/gateway/impl/PaymentGatewayImpl.java` (NEW)
- `src/main/java/com/example/model/client/PaymentRequest.java` (NEW)
- `src/main/java/com/example/model/client/Payment.java` (NEW)
- `src/main/java/com/example/config/RestClientConfiguration.java` (UPDATED)
- `src/test/java/com/example/gateway/PaymentGatewayImplTest.java` (NEW)
- `.claude/api-engineer-state.json` (UPDATED)

**PaymentGateway Interface Generated**:
```java
public interface PaymentGateway {
    Payment createPayment(PaymentRequest request);
    Payment getPayment(String id);
}
```

**PaymentGatewayImpl Generated**:
```java
import com.barclays.api.bap.bld.lib.logging.LogFactory;
import com.barclays.api.bap.bld.lib.logging.Logger;
import com.barclays.api.bap.bld.lib.logging.PerfEvent;
import com.barclays.api.bap.bld.lib.logging.PerfLogger;
import com.barclays.api.bap.bld.lib.restclient.RestApiClient;
import org.springframework.web.util.UriComponentsBuilder;

@Component
@RequiredArgsConstructor
public class PaymentGatewayImpl implements PaymentGateway {
    private final RestApiClient restApiClient;
    private static final Logger LOGGER = LogFactory.getLogger(PaymentGatewayImpl.class);
    private static final PerfLogger PERFORMANCE_LOGGER = LogFactory.getPerfLogger(PaymentGatewayImpl.class);
    
    private static final String PAYMENT_SERVICE_BASE_URL = "${payment.service.baseUrl}";

    @Override
    public Payment createPayment(PaymentRequest request, Map<String, String> headers) {
        UriComponentsBuilder uriBuilder = UriComponentsBuilder
                .fromUriString(PAYMENT_SERVICE_BASE_URL + "/payments");
        URI uri = uriBuilder.build().toUri();

        return restApiClient
                    .call(HttpMethod.POST, uri, request, httpHeaders, Payment.class)
                    .getBody();
    }

    @Override
    public Payment getPayment(String id) {
      UriComponentsBuilder uriBuilder = UriComponentsBuilder
                .fromUriString(PAYMENT_SERVICE_BASE_URL + "/payments/{id}");
        URI uri = uriBuilder.build().toUri();

        return restApiClient
                    .call(HttpMethod.GET, uri, httpHeaders, Payment.class)
                    .getBody();
    }
}
```

**RestClientConfiguration Updated**:
```java
@Configuration
public class RestClientConfiguration {
    
    @Bean
    public RestClient paymentServiceRestClient(
            @Value("${payment.service.baseUrl}") String baseUrl) {
        return RestClient.builder()
            .baseUrl(baseUrl)
            .build();
    }
}
```

**application.yml Updated**:
```yaml
payment:
  service:
    baseUrl: https://payment-api.internal.example.com
```

**State File Changes**:
```json
{
  "producer_specs": [
    {
      "name": "Order Processing Service",
      "file": "order-processing-api.yaml",
      "baseUrl": "https://order-api.internal.example.com",
      "gateway": "OrderProcessingGateway"
    },
    {
      "name": "Payment Service",
      "file": "payment-service-api.yaml",
      "baseUrl": "https://payment-api.internal.example.com",
      "gateway": "PaymentGateway"
    }
  ],
  "refinements": [
    {
      "timestamp": "2026-06-13T11:00:00Z",
      "type": "ADD_PRODUCER",
      "description": "Added Payment Service integration",
      "affected_files": [
        "PaymentGateway.java",
        "PaymentGatewayImpl.java",
        "PaymentRequest.java",
        "Payment.java",
        "RestClientConfiguration.java"
      ]
    }
  ]
}
```

---

## Scenario 4: Update Data Model

### Context
Generated project has User model. Requirements changed: need to add phone field and change email to be optional.

### Refinement Steps

**Step 1: Update Consumer Spec**

Update `order-api.yaml` User schema:
```yaml
User:
  type: object
  properties:
    id:
      type: string
      format: uuid
    name:
      type: string
    email:
      type: string
      format: email
      nullable: true              # Now optional
    phone:
      type: string                # NEW field
      pattern: '^\+?[\d\s\-()]+$'
    createdAt:
      type: string
      format: date-time
  required: [id, name, createdAt]  # email removed, phone not required
```

**Step 2: Update Model in Project**
```bash
refine --project-root ./order-service --update-model User
```

Refinement-agent will:
1. Detect schema changed (User)
2. Regenerate User.java response model
3. Update validation annotations
4. Update tests that reference User
5. Preserve any custom methods in User class

**User.java Before**:
```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class User {
    @NotNull
    private UUID id;
    
    @NotNull
    @NotBlank
    private String name;
    
    @NotNull
    @Email
    private String email;
    
    @NotNull
    private LocalDateTime createdAt;
}
```

**User.java After**:
```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class User {
    @NotNull
    private UUID id;
    
    @NotNull
    @NotBlank
    private String name;
    
    @Nullable
    @Email
    private String email;              // Now optional
    
    @Pattern(regexp = "^\\+?[\\d\\s\\-()]+$")
    private String phone;              // NEW field
    
    @NotNull
    private LocalDateTime createdAt;
}
```

**Updated Test**:
```java
@Test
void testUserWithoutOptionalFields() {
    User user = User.builder()
        .id(UUID.randomUUID())
        .name("John Doe")
        .createdAt(LocalDateTime.now())
        // email not set (now nullable)
        // phone not set (not required)
        .build();
    
    assertNotNull(user.getName());
    assertNull(user.getEmail());
    assertNull(user.getPhone());
}
```

**State File Changes**:
```json
{
  "schemas": {
    "User": {
      "fields": [
        {
          "name": "id",
          "type": "UUID",
          "required": true,
          "nullable": false
        },
        {
          "name": "name",
          "type": "String",
          "required": true,
          "nullable": false
        },
        {
          "name": "email",
          "type": "String",
          "required": false,
          "nullable": true,
          "updated_at": "2026-06-13T11:15:00Z"
        },
        {
          "name": "phone",
          "type": "String",
          "required": false,
          "nullable": true,
          "added_at": "2026-06-13T11:15:00Z"
        },
        {
          "name": "createdAt",
          "type": "LocalDateTime",
          "required": true,
          "nullable": false
        }
      ]
    }
  }
}
```

---

## Scenario 5: Add Single Endpoint (Fine-Grained)

### Context
Product resource exists. Need to add new endpoint: GET /products/search?query=...

### Refinement Steps

**Step 1: Add Endpoint to Spec**

Update `order-api.yaml`:
```yaml
/products/search:
  get:
    operationId: searchProducts
    tags: [Product]
    parameters:
      - name: query
        in: query
        required: true
        schema:
          type: string
          minLength: 1
          maxLength: 100
      - name: limit
        in: query
        required: false
        schema:
          type: integer
          minimum: 1
          maximum: 100
          default: 20
    responses:
      200:
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: '#/components/schemas/Product'
```

**Step 2: Add Endpoint Manually**
```bash
refine --project-root ./order-service --add-endpoint "/products/search" GET
```

Refinement-agent will:
1. Parse endpoint specification
2. Add method to ProductController
3. Add method to ProductService interface
4. Add implementation to ProductServiceImpl
5. Add test case to ProductControllerTest
6. Update state file

**ProductController Updated**:
```java
import com.barclays.api.bap.bld.lib.common.response.Response;
import com.barclays.api.bap.bld.lib.payload.response.ResponseHttpStatus;
import com.barclays.api.bap.bld.lib.payload.response.RestResponse;

@GetMapping("/search")
public Response searchProducts(
        @RequestParam String query,
        @RequestParam(defaultValue = "20") Integer limit) {
    return RestResponse
              .assemble()
              .build(ResponseHttpStatus.OK, 
                  productService.searchProducts(query, limit));
}
```

**ProductService Interface Updated**:
```java
public interface ProductService {
    List<Product> listProducts();
    Product createProduct(CreateProductRequest request);
    Product getProduct(String id);
    List<Product> searchProducts(String query, Integer limit);  // NEW
}
```

**ProductServiceImpl Updated**:
```java
@Override
public List<Product> searchProducts(String query, Integer limit) {
    // TODO: Implement search logic
    return Collections.emptyList();
}
```

**ProductControllerTest Updated**:
```java
@Test
void testSearchProducts() {
    List<Product> expected = List.of(
        new Product(UUID.randomUUID(), "Product 1", ...),
        new Product(UUID.randomUUID(), "Product 2", ...)
    );
    
    when(productService.searchProducts("test", 20))
        .thenReturn(expected);
    
    mockMvc.perform(get("/products/search")
            .param("query", "test")
            .param("limit", "20"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$", hasSize(2)));
}
```

**State File Changes**:
```json
{
  "endpoints": [
    {"path": "/products", "method": "GET"},
    {"path": "/products", "method": "POST"},
    {"path": "/products/{id}", "method": "GET"},
    {"path": "/products/search", "method": "GET"}    // NEW
  ],
  "refinements": [
    {
      "timestamp": "2026-06-13T11:30:00Z",
      "type": "ADD_ENDPOINT",
      "description": "Added GET /products/search",
      "affected_files": [
        "ProductController.java",
        "ProductService.java",
        "ProductServiceImpl.java",
        "ProductControllerTest.java"
      ],
      "status": "applied"
    }
  ]
}
```

---

## Scenario 6: Add Data Layer (Database)

### Context
Generated project has no database layer. Need to add JPA entity persistence.

### Refinement Steps

**Step 1: Update Configuration**

Update project state or config to indicate database layer needed:
```bash
refine --project-project-root ./order-service --enable-database
```

Or manually update `.claude/api-engineer-config.yml`:
```yaml
database_layer: true
```

Refinement-agent will:
1. Generate JPA entities for all models
2. Generate Repository interfaces (JpaRepository)
3. Update ServiceImpl to use repositories
4. Update application.yml with database configuration
5. Add Spring Data JPA dependencies to build.gradle

**Generated Entity**:
```java
@Entity
@Table(name = "users")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class UserEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private UUID id;
    
    @Column(nullable = false)
    private String name;
    
    @Column(nullable = true, unique = true)
    private String email;
    
    @Column(nullable = true)
    private String phone;
    
    @CreatedDate
    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;
}
```

**Generated Repository**:
```java
public interface UserRepository extends JpaRepository<UserEntity, UUID> {
    Optional<UserEntity> findByEmail(String email);
    List<UserEntity> findByNameContaining(String name);
}
```

**Updated application.yml**:
```yaml
spring:
  datasource:
    url: jdbc:h2:mem:testdb
    driverClassName: org.h2.Driver
  jpa:
    database-platform: org.hibernate.dialect.H2Dialect
    hibernate:
      ddl-auto: create-drop
    show-sql: false
    properties:
      hibernate.format_sql: true

---
spring:
  config:
    activate:
      on-profile: prod
  datasource:
    url: jdbc:postgresql://localhost:5432/order-service
    username: ${DB_USER}
    password: ${DB_PASSWORD}
    driverClassName: org.postgresql.Driver
  jpa:
    database-platform: org.hibernate.dialect.PostgreSQL10Dialect
    hibernate:
      ddl-auto: validate
```

---

## State File Management During Refinement

### Before Refinement
```json
{
  "consumer_spec": "order-api.yaml",
  "producer_specs": [],
  "endpoints": 3,
  "schemas": 2,
  "database_layer": false,
  "sdk_integration": false,
  "refinements": []
}
```

### During Refinement
- Agent loads state file
- Agent detects changes needed
- Agent generates affected files
- Agent verifies no breakage (compilation check)
- Agent updates state atomically

### After Refinement
```json
{
  "consumer_spec": "order-api.yaml",
  "producer_specs": ["payment-service-api.yaml"],
  "endpoints": 6,
  "schemas": 4,
  "database_layer": true,
  "sdk_integration": false,
  "last_refinement": "2026-06-13T11:30:00Z",
  "last_refinement_type": "SPEC_UPDATE",
  "refinements": [
    {
      "timestamp": "2026-06-13T10:45:00Z",
      "type": "SPEC_UPDATE",
      "description": "Added Product resource",
      "status": "applied"
    },
    {
      "timestamp": "2026-06-13T11:00:00Z",
      "type": "ADD_PRODUCER",
      "description": "Added Payment Service integration",
      "status": "applied"
    },
    {
      "timestamp": "2026-06-13T11:30:00Z",
      "type": "SPEC_UPDATE",
      "description": "Added database layer",
      "status": "applied"
    }
  ]
}
```

---

## Rollback Patterns

### Automatic Rollback Triggers

1. **Compilation Error**
   - Run `./gradlew compileJava` after changes
   - If FAILS: rollback all changes, report error
   - If PASSES: continue

2. **Type Conflict**
   - Reference to non-existent schema
   - Method signature mismatch
   - Automatic rollback, report conflict

3. **Test Failure**
   - If `--validate true` and tests fail
   - Rollback all changes
   - Report which tests failed

### Manual Rollback

If refinement applied but caused issues:

```bash
# Git-based rollback (if Git tracking enabled)
git checkout HEAD -- src/main/java/com/example/

# Or restore from backup
cp -r .backup/before-refinement/* .
```

---

**Version**: 1.0.0  
**Authority**: Advanced refinement patterns guide  
**Last Updated**: 2026-06-13
