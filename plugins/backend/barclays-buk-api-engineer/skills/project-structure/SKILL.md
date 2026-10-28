---
name: project-structure
description: Standard folder layout, Java package naming conventions, and file organization for generated Spring Boot projects
color: yellow
---

> **Source:** Barclays BUK DAF service structure conventions and hexagonal architecture standards.
> **Owner:** BUK
> **Review trigger:** On changes to the DAF template repository structure or hexagonal architecture standards.
> **Status:** Reviewed

# Skill: Project Structure

## Quick Start

Reference the project structure when generating or modifying files:

1. **Package placement:** Use the hexagonal architecture diagram below to determine which package a class belongs in
2. **Import rules:** Controllers import only from `service/` interfaces; Services import only from `gateway/` interfaces
3. **Naming:** Use the naming convention table to name new files correctly

---

## Hexagonal Architecture

This plugin generates code using the **Ports and Adapters** (hexagonal) pattern. Every package has a named role. Understanding these roles prevents agents from accidentally coupling layers that must stay independent.

```
┌────────────────────────────────────────────────────────────────┐
│  INBOUND ADAPTERS         controller/                         │
│    REST endpoints. Know only service interfaces. Never        │
│    import from gateway/ or repository/.                       │
├────────────────────────────────────────────────────────────────┤
│  INBOUND PORTS            service/                            │
│    Service interfaces. The contract between controllers and   │
│    the application layer. Framework types (Request,           │
│    RestResponse) used deliberately — pragmatic SDK3 tradeoff. │
├────────────────────────────────────────────────────────────────┤
│  APPLICATION LAYER        service/impl/  service/{f}/mapper/  │
│    Business logic. Depends on outbound ports only — never     │
│    on gateway/impl/ or any concrete adapter class.            │
│    Mapper classes: field mapping only, no business decisions. │
├────────────────────────────────────────────────────────────────┤
│  OUTBOUND PORTS           gateway/   repository/              │
│    Gateway interfaces + JPA repository interfaces. Defined    │
│    here so the application layer can depend on them without   │
│    knowing about HTTP or database details.                    │
├────────────────────────────────────────────────────────────────┤
│  OUTBOUND ADAPTERS        gateway/impl/                       │
│    GatewayImpl classes. Call RestApiClient/RestTemplate.      │
│    Know about HTTP status codes and headers. Never referenced │
│    directly by the application layer.                         │
└────────────────────────────────────────────────────────────────┘
```

### Dependency Rules — Non-Negotiable

| From | May depend on | FORBIDDEN |
|---|---|---|
| `controller/` | `service/` interfaces | `gateway/`, `gateway/impl/`, `repository/` |
| `service/impl/` | `service/`, `gateway/`, `repository/` interfaces | `gateway/impl/`, `new XxxGatewayImpl(...)` |
| `gateway/impl/` | External HTTP/DB | `service/`, `controller/` |
| `model/`, `dto/` | Nothing (pure POJOs) | Spring, JPA, jakarta.validation |

**Enforcement:** The `daf-validation-agent` Red Flag #20 and `project-generation-agent` Phase 5b both check these rules. Any violation is a hard gate failure.

---

## When to Use This Skill

Use this skill when:
- Understanding the generated project folder layout
- Following Java package naming conventions
- Organizing files by layer (controller, service, gateway, model)
- Extending generated projects

## Generation Strategy

### Phase 1: Gradle Infrastructure (COPIED from templates/)
The plugin copies 7 bare minimum Gradle files from `templates/` directory to ensure consistency with Barclays standards:
- `settings.gradle` (substitution: {ARTIFACT_ID})
- `gradle.properties` (substitutions: {VERSION}, {ARTIFACT_ID}, {IMPLEMENTATION_TITLE})
- `build.gradle` (copied verbatim)
- `buildSrc/build.gradle` (copied verbatim)
- `config/checkstyle.xml` (copied verbatim)
- `gradle/common/mutation.gradle` (substitutions: {basePackage}, {AppName}Application)
- `gradle/wrapper/gradle-wrapper.properties` (copied verbatim)

Then generates Gradle wrapper scripts (gradlew, gradlew.bat) via `gradle wrapper --gradle-version 8.13`.

### Phase 2+: Application Code Generation
All application source code, tests, configuration, and CI/CD files are generated from semantic model.

### Standard Project Layout

```
my-service/
├── build.gradle                    # Gradle build configuration
├── settings.gradle                 # Gradle settings
├── gradle.properties               # Build properties
├── gradlew / gradlew.bat          # Gradle wrapper
├── README.md                       # Project documentation
│
├── .gradle/                        # Gradle cache (git ignored)
├── build/                          # Build output (git ignored)
├── .idea/                          # IntelliJ IDE config (git ignored)
│
├── config/
│   └── checkstyle.xml             # Organization code style rules
│
├── buildSrc/
│   └── build.gradle               # Build source configuration
│
├── gradle/
│   ├── wrapper/
│   │   ├── gradle-wrapper.jar
│   │   ├── gradle-wrapper.properties
│   └── common/
│       └── mutation.gradle
│
├── src/
│   ├── main/
│   │   ├── java/com/example/api/
│   │   │   ├── MyServiceApplication.java          # @SpringBootApplication entry point
│   │   │   │
│   │   │   ├── config/
│   │   │   │   ├── SecurityConfig.java            # Security setup
│   │   │   │   ├── RestClientConfig.java          # REST client beans
│   │   │   │   ├── ApiInitializerConfiguration.java  # SDK init
│   │   │   │   └── DatabaseConfig.java            # JPA config (if DB)
│   │   │   │
│   │   │   ├── controller/
│   │   │   │   ├── UserController.java            # REST endpoints
│   │   │   │   ├── ProductController.java
│   │   │   │   └── GlobalExceptionHandler.java    # Exception handling
│   │   │   │
│   │   │   ├── service/
│   │   │   │   ├── UserService.java               # Service interface
│   │   │   │   ├── ProductService.java
│   │   │   │   └── impl/
│   │   │   │       ├── UserServiceImpl.java        # Service implementation
│   │   │   │       └── ProductServiceImpl.java
│   │   │   │
│   │   │   ├── gateway/
│   │   │   │   ├── PaymentGateway.java            # Producer API interface
│   │   │   │   ├── InventoryGateway.java
│   │   │   │   └── impl/
│   │   │   │       ├── PaymentGatewayImpl.java
│   │   │   │       └── InventoryGatewayImpl.java
│   │   │   │
│   │   │   ├── model/
│   │   │   │   ├── request/
│   │   │   │   │   ├── CreateUserRequest.java
│   │   │   │   │   └── UpdateUserRequest.java
│   │   │   │   ├── response/
│   │   │   │   │   ├── UserResponse.java
│   │   │   │   │   └── ProductResponse.java
│   │   │   │   ├── client/
│   │   │   │   │   ├── PaymentRequest.java       # Downstream API models
│   │   │   │   │   └── PaymentResponse.java
│   │   │   │   └── entity/
│   │   │   │       ├── UserEntity.java           # JPA entities (if DB)
│   │   │   │       └── ProductEntity.java
│   │   │   │
│   │   │   ├── repository/
│   │   │   │   ├── UserRepository.java           # JPA repositories (if DB)
│   │   │   │   └── ProductRepository.java
│   │   │   │
│   │   │   └── exception/
│   │   │       ├── UserNotFoundException.java
│   │   │       ├── InvalidInputException.java
│   │   │       └── ExternalServiceException.java
│   │   │
│   │   └── resources/
│   │       ├── application.yml                  # Spring config (base)
│   │       ├── application-dev.yml              # Dev profile
│   │       ├── application-prod.yml             # Prod profile
│   │       └── oas/                             # OpenAPI specs
│   │           └── api.yaml
│   │
│   └── test/
│       ├── java/com/example/api/
│       │   ├── controller/
│       │   │   └── UserControllerTest.java      # @WebMvcTest
│       │   ├── service/
│       │   │   └── UserServiceImplTest.java     # @ExtendWith(MockitoExtension)
│       │   └── gateway/
│       │       └── PaymentGatewayImplTest.java  # @ExtendWith(MockitoExtension) + @Mock RestApiClient
│       │
│       └── resources/
│           ├── application-test.yml             # Test config
│           └── fixtures/
│               ├── user-fixture.json
│               └── payment-response.json
```

## Core Concepts

### Package Naming Convention

Base: `com.example.api` (from --package argument)

| Layer | Package | Example |
|-------|---------|---------|
| **Controllers** | `{base}.controller` | `com.example.api.controller` |
| **Services** | `{base}.service` | `com.example.api.service` |
| **Service Impl** | `{base}.service.impl` | `com.example.api.service.impl` |
| **Gateways** | `{base}.gateway` | `com.example.api.gateway` |
| **Gateway Impl** | `{base}.gateway.impl` | `com.example.api.gateway.impl` |
| **Models** | `{base}.model.*` | `com.example.api.model.request` |
| **Repositories** | `{base}.repository` | `com.example.api.repository` |
| **Entities** | `{base}.model.entity` | `com.example.api.model.entity` |
| **Configuration** | `{base}.config` | `com.example.api.config` |
| **Exceptions** | `{base}.exception` | `com.example.api.exception` |

### Class Naming Convention

| Component | Pattern | Example |
|-----------|---------|---------|
| **Controller** | `{Resource}Controller` | `UserController` |
| **Service Interface** | `{Resource}Service` | `UserService` |
| **Service Impl** | `{Resource}ServiceImpl` | `UserServiceImpl` |
| **Gateway Interface** | `{Producer}Gateway` | `PaymentGateway` |
| **Gateway Impl** | `{Producer}GatewayImpl` | `PaymentGatewayImpl` |
| **Request Model** | `{Action}{Resource}Request` or `{Resource}Request` | `CreateUserRequest` |
| **Response Model** | `{Resource}Response` | `UserResponse` |
| **Entity** | `{Resource}Entity` | `UserEntity` |
| **Repository** | `{Resource}Repository` | `UserRepository` |
| **Exception** | `{Issue}Exception` | `UserNotFoundException` |

### File Organization Rules

**By Layer:**
- Controllers group REST endpoints by resource
- Services implement business logic per resource
- Gateways call downstream APIs
- Models separated by direction (request/response/client)

**By Resource:**
- User-related: UserController, UserService, UserServiceImpl, UserRepository
- Product-related: ProductController, ProductService, ProductServiceImpl, ProductRepository
- Separate gateways for each downstream API: PaymentGateway, InventoryGateway

### Spring Boot Application Entry Point

```java
@SpringBootApplication
public class MyServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(MyServiceApplication.class, args);
    }
}
```

Class name: `{ArtifactName}Application` (from --artifact argument)

### Configuration Files

**application.yml** (base config):
```yaml
spring:
  application:
    name: my-service
  jpa:
    hibernate:
      ddl-auto: validate
server:
  port: 8080
```

**application-dev.yml** (development):
```yaml
spring:
  datasource:
    url: jdbc:h2:mem:testdb
```

**application-prod.yml** (production):
```yaml
spring:
  datasource:
    url: jdbc:postgresql://prod-db:5432/myservice
```

### Test File Organization

- Controller tests: `src/test/java/.../controller/...ControllerTest.java`
- Service tests: `src/test/java/.../service/...ServiceImplTest.java`
- Gateway tests: `src/test/java/.../gateway/...GatewayImplTest.java`
- Test resources (fixtures, configs): `src/test/resources/`

## Example: Generated Project Structure

For artifact `order-service` with package `com.acme.order` and 2 endpoints (3 controllers), expected structure:

```
order-service/
├── src/main/java/com/acme/order/
│   ├── OrderApplication.java                    (15 lines)
│   ├── controller/
│   │   ├── OrderController.java                 (50 lines)
│   │   ├── PaymentController.java               (40 lines)
│   │   └── GlobalExceptionHandler.java          (60 lines)
│   ├── service/
│   │   ├── OrderService.java                    (10 lines)
│   │   ├── PaymentService.java                  (8 lines)
│   │   └── impl/
│   │       ├── OrderServiceImpl.java             (40 lines)
│   │       └── PaymentServiceImpl.java           (35 lines)
│   ├── gateway/
│   │   ├── ExternalPaymentGateway.java          (12 lines)
│   │   └── impl/
│   │       └── ExternalPaymentGatewayImpl.java   (80 lines)
│   ├── model/
│   │   ├── request/
│   │   │   ├── CreateOrderRequest.java          (15 lines)
│   │   │   └── ProcessPaymentRequest.java       (12 lines)
│   │   ├── response/
│   │   │   ├── OrderResponse.java               (18 lines)
│   │   │   └── PaymentResponse.java             (15 lines)
│   │   ├── client/
│   │   │   └── ExternalPaymentResponse.java     (20 lines)
│   │   └── entity/
│   │       └── OrderEntity.java                 (25 lines, if DB layer)
│   ├── repository/
│   │   └── OrderRepository.java                 (5 lines, if DB layer)
│   ├── exception/
│   │   ├── OrderNotFoundException.java          (8 lines)
│   │   ├── PaymentFailedException.java          (8 lines)
│   │   └── InvalidOrderException.java           (8 lines)
│   └── config/
│       └── ApplicationConfig.java               (30 lines - SDK3 initialization + SecureFields)
├── src/test/java/com/acme/order/
│   ├── controller/
│   │   ├── OrderControllerTest.java             (80 lines)
│   │   └── PaymentControllerTest.java           (75 lines)
│   ├── service/
│   │   ├── OrderServiceImplTest.java            (65 lines)
│   │   └── PaymentServiceImplTest.java          (60 lines)
│   └── gateway/
│       └── ExternalPaymentGatewayImplTest.java  (90 lines)
├── src/main/resources/
│   ├── application.properties                   (15 lines)
│   ├── application-dev.properties               (10 lines)
│   └── application-prod.properties              (10 lines)
├── gradle/
│   ├── wrapper/
│   │   ├── gradle-wrapper.jar                   (~68 KB)
│   │   └── gradle-wrapper.properties            (5 lines)
│   └── common/
│       └── mutation.gradle                      (40 lines)
├── buildSrc/
│   └── build.gradle                             (20 lines)
├── config/
│   └── checkstyle.xml                           (180 lines)
├── build.gradle                                 (150 lines)
├── gradle.properties                            (23 lines)
├── settings.gradle                              (1 line)
├── .gitlab-ci.yml                               (56 lines)
├── project_metadata.yml                         (11 lines)
├── .gitlab-ci.yml                               (56 lines)
├── gradlew                                      (executable)
├── gradlew.bat                                  (executable)
├── README.md                                    (40 lines)
├── .gitignore                                   (30 lines)
└── .claude/
    └── api-engineer-state.json                  (state tracking)
```

**Expected File Counts:**
- Source files: 14-16 (Application + 2-3 controllers + 2-4 services + 1-2 gateways + models + config + exception handler)
- Test files: 5-6 (2-3 controller tests + 2-3 service tests + 1-2 gateway tests)
- Gradle files (Phase 1 COPIED): 7 core files + 2 generated wrappers = 9 total (settings.gradle, gradle.properties, build.gradle, buildSrc/build.gradle, mutation.gradle, checkstyle.xml, gradle-wrapper.properties, gradlew, gradlew.bat)
- CI/CD + Config files (Phase 6b GENERATED): 2 files (.gitlab-ci.yml, project_metadata.yml)
- Application config/resources (Phase 3 GENERATED): 4 files (application.yml, application-dev.yml, application-prod.yml, .gitignore)
- Documentation (Phase 7 GENERATED): 1 file (README.md)
- State tracking: 1 file (.claude/api-engineer-state.json)

## Reference Documentation

- **folder-layout.md**: Detailed folder structure
- **package-naming-conventions.md**: Java package rules
- **file-organization.md**: File organization strategies

## Advanced Topics

- **structure-validation.md**: Validating project structure

## Lessons Learned

- **project-organization.md**: Best practices from real projects

---

See `references/project-structure/` (reference/ and advanced/ subdirectories) for detailed documentation.

## Source Attribution

**Primary sources:**
- Barclays DAF service structure conventions — feature-based sub-packaging (`service/{feature}/`, `gateway/{feature}/`) as used in production DAF services
- DAF template repository directory layout — authoritative source of the generated project skeleton
- Hexagonal architecture (Ports and Adapters) pattern — layer naming and dependency rule applied to the controller/service/gateway stack

**Training knowledge applied:**
- Hexagonal architecture principles: inbound adapters (controllers), domain (services), outbound adapters (gateways/repositories)
- Java package naming conventions: `com.barclays.api.{domain}.controller`, `service.{feature}.impl`, etc.
- Maven Standard Directory Layout adapted for Gradle multi-source-set projects (`src/main`, `src/test`, `src/integrationTest`)

**Known limitations:**
- Package naming conventions reflect the DAF template as of the last review; manually created services may have diverged
- The hexagonal layer diagram shows the intended dependency direction — the `daf-compliance-fixer-agent` and `daf-validation-agent` enforce these rules at generation time, not this skill
- `src/integrationTest` source set requires the SDK3 `bap-bld-lib-kotlin-int-test-gradle-plugin`; projects without this plugin will not have this directory active

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] Does the generated project follow the feature-based sub-package structure (service/{feature}/impl/, gateway/{feature}/)?
- [ ] Are controller classes in controller/ and only importing from service interfaces (never gateway/ or repository/)?
- [ ] Are service implementations in service/{feature}/impl/ and only importing gateway interfaces (never *GatewayImpl)?
- [ ] Are gateway implementations in gateway/{feature}/ and the only classes using RestApiClient or HTTP clients?
- [ ] Does the project directory structure match the canonical layout defined in this skill?
- [ ] Are all test packages mirroring the corresponding source package structure?
