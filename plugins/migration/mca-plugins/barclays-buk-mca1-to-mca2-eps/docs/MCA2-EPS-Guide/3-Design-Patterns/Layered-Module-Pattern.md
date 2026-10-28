# Layered Module Pattern: API→Core→Starter Separation

## Executive Summary

The **Layered Module Pattern** organizes MCA2 libraries into three tiers: **API** (contracts), **Core** (implementations), and **Starter** (auto-configuration). This separation ensures clean architecture, enables partial adoption, and supports both direct usage and Spring Boot integration.

**Pattern Definition:**
> "Separate interface definitions (API) from implementations (Core) from configuration (Starter) to maximize flexibility and minimize coupling."

**MCA2 Application:**
- **API Modules** (e.g., `router-api`, `secure-proxy-api`) — Define interfaces/contracts
- **Core Modules** (e.g., `router-http`, `secure-proxy-core`) — Implement contracts
- **Starter Modules** (e.g., `service-client-starter`, `placeholder-starter`) — Provide Spring Boot auto-config

---

## Three-Tier Module Structure

```
┌──────────────────────────────────────────────────┐
│ STARTER TIER (Spring Boot Integration)           │
│ Provides: Auto-configuration, property binding   │
│ Examples: service-client-starter,                │
│           placeholder-starter,                   │
│           *-spring-boot-starter                  │
│                                                  │
│ Responsibility:                                  │
│ • @EnableConfigurationProperties               │
│ • Spring Boot auto-configs                       │
│ • Default bean instances                        │
│ • Property validation                           │
│                                                  │
│ Dependencies: ↓ Core tier                        │
│              ↓ API tier                          │
│              ↓ Spring Boot                       │
└──────────────────────────────────────────────────┘
         ▲
         │ depends on
         │
┌──────────────────────────────────────────────────┐
│ CORE TIER (Implementations)                      │
│ Provides: Business logic implementations         │
│ Examples: router-http, secure-proxy-core,       │
│           filter-core, response-handling-core    │
│                                                  │
│ Responsibility:                                  │
│ • Implement API interfaces                      │
│ • Business logic                                │
│ • Complex algorithms                            │
│ • Configuration classes                         │
│                                                  │
│ Dependencies: ↓ API tier                         │
│              ↓ Foundation utilities              │
│              ↓ Spring framework                  │
└──────────────────────────────────────────────────┘
         ▲
         │ depends on
         │
┌──────────────────────────────────────────────────┐
│ API TIER (Contracts/Interfaces)                 │
│ Provides: Interfaces, abstract classes, enums    │
│ Examples: router-api, secure-proxy-api,         │
│           exception-handling-core (interfaces),  │
│           response-handling-core (interfaces)    │
│                                                  │
│ Responsibility:                                  │
│ • Define contracts via interfaces               │
│ • Data transfer objects (DTOs)                  │
│ • Enumerations                                  │
│ • Exceptions                                    │
│ • NO implementation logic                       │
│                                                  │
│ Dependencies: ↓ Foundation only                  │
│              ↓ Java standard library             │
└──────────────────────────────────────────────────┘
```

---

## Three-Tier Principles

### Principle 1: Unidirectional Dependencies

```
Starter tier can import Core tier
Core tier can import API tier
API tier imports ONLY foundation

    ↓ imports ↓
Starter → Core → API → Foundation
    ✗
(No backward imports allowed)
```

### Principle 2: API Independence

API modules have **no Spring Boot dependencies**:
- Can be used in non-Spring applications
- Interfaces remain stable
- Pure Java code (no @Bean, @Configuration)

### Principle 3: Core Completeness

Core modules implement all API interfaces:
- Never force consumers to implement interfaces
- Handle all complexity internally
- Optional advanced configurations only

### Principle 4: Starter Simplicity

Starter modules only handle auto-configuration:
- No business logic (that's in Core)
- Minimal property definitions
- Default bean factory methods only

---

## Example 1: Service Client Framework

### API Tier: Contracts

**Module:** (conceptual, actually in service-client)

```java
// service-client-api/src/main/java/.../RestClientFactory.java

package com.barclays.global.mca.restclient.api;

/**
 * Factory for creating REST clients
 * Abstraction for different HTTP client implementations
 */
public interface RestClientFactory {

    /**
     * Create REST client for service
     */
    RestClient createClient(String serviceName);

    /**
     * Get client configuration
     */
    RestClientConfig getConfig(String serviceName);
}

/**
 * REST Client abstraction
 */
public interface RestClient {
    <T> T get(String path, Class<T> responseType);
    <T> T post(String path, Object body, Class<T> responseType);
    // ... other methods
}

// Enums
public enum RestClientType {
    SYNC,
    ASYNC,
    REACTIVE
}
```

### Core Tier: Implementation

**Module:** service-client

```java
// service-client/src/main/java/.../RestClientFactoryImpl.java

package com.barclays.global.mca.restclient;

@Service
public class RestClientFactoryImpl implements RestClientFactory {

    @Autowired
    private RestTemplateFactory restTemplateFactory;

    @Autowired
    private ServiceRegistry serviceRegistry;

    @Override
    public RestClient createClient(String serviceName) {
        // Complex implementation logic
        ServiceEndpoint endpoint = serviceRegistry.lookup(serviceName);
        RestTemplate template = restTemplateFactory.create(endpoint);

        return new RestClientImpl(
            template,
            endpoint,
            new RetryPolicy(),
            new CircuitBreaker()
        );
    }

    @Override
    public RestClientConfig getConfig(String serviceName) {
        // More complex logic
        // Read from various sources, merge configs
        return mergeConfigurations(serviceName);
    }
}

@Service
public class RestClientImpl implements RestClient {

    private RestTemplate template;
    private ServiceEndpoint endpoint;
    private RetryPolicy retryPolicy;
    private CircuitBreaker circuitBreaker;

    @Override
    public <T> T get(String path, Class<T> responseType) {
        // Complex implementation:
        // - URL building
        // - Header injection
        // - Circuit breaker pattern
        // - Retry logic
        // - Error handling
        // - Correlation ID propagation
    }

    // ... other methods
}
```

### Starter Tier: Auto-Configuration

**Module:** service-client-starter

```java
// service-client-starter/src/main/java/.../ServiceClientAutoConfiguration.java

@Configuration
@EnableConfigurationProperties(ServiceClientProperties.class)
@ConditionalOnClass(RestTemplate.class)
public class ServiceClientAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean(RestTemplateFactory.class)
    public RestTemplateFactory restTemplateFactory(
        ServiceClientProperties props
    ) {
        return new RestTemplateFactoryImpl(props);
    }

    @Bean
    @ConditionalOnMissingBean(RestClientFactory.class)
    public RestClientFactory restClientFactory(
        RestTemplateFactory templateFactory,
        ServiceRegistry registry
    ) {
        return new RestClientFactoryImpl(templateFactory, registry);
    }

    @Bean
    @ConditionalOnMissingBean
    public ServiceRegistry serviceRegistry(
        ServiceClientProperties props
    ) {
        return new ServiceRegistryImpl(props);
    }
}

// Configuration properties
@ConfigurationProperties(prefix = "rest-client")
@Data
public class ServiceClientProperties {
    private int connectionTimeout = 5000;
    private int readTimeout = 10000;
    private int maxRetries = 3;
    private Map<String, ServiceProperties> services;
}
```

### Starter META-INF Registration

```
META-INF/spring/
└── org.springframework.boot.autoconfigure.AutoConfiguration.imports

Content:
com.barclays.global.mca.restclient.config.ServiceClientAutoConfiguration
```

### Usage Flow

```
Application developer
    │
    ├─ Dependency: spring-boot-starter-*service-client-starter*
    │
    ├─ Spring Boot auto-discovers:
    │   ServiceClientAutoConfiguration
    │
    ├─ Auto-configuration instantiates:
    │   ├─ RestTemplateFactory (from Core tier)
    │   ├─ RestClientFactory (from Core tier)
    │   └─ ServiceRegistry (from Core tier)
    │
    ├─ Application injects:
    │   @Autowired
    │   RestClientFactory clientFactory;
    │
    └─ Uses factory to create clients:
        RestClient client = clientFactory.createClient("mission-service");
```

---

## Example 2: Exception Handling Framework

### API Tier: Exception Contracts

**Module:** exception-handling-core (API portion)

```java
// Hierarchy definition
public abstract class GenericException extends Exception {
    abstract int getHttpStatusCode();
}

public class NotFoundException extends GenericException {
    @Override int getHttpStatusCode() { return 404; }
}

public class ApplicationException extends GenericException {
    @Override int getHttpStatusCode() { return 200; }
}

// No implementations, just interface/contract
```

### Core Tier: Exception Handling

**Module:** exception-handling-core (Core portion)

```java
// Response mapping
public class ResponseHttpStatus {
    public static int getStatusCode(Throwable ex) {
        if (ex instanceof ApplicationException) {
            return 200;
        } else if (ex instanceof NotFoundException) {
            return 404;
        } else if (ex instanceof AuthorizationException) {
            return 403;
        }
        // ... more mappings
        return 500;
    }
}

// Exception handler
@ControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(GenericException.class)
    public ResponseEntity<Response<?>> handleException(GenericException ex) {
        // Complex exception handling logic
    }
}
```

### Starter Tier: Auto-Configuration

**Module:** exception-handling-spring

```java
@Configuration
@ConditionalOnWebApplication
public class ExceptionHandlingAutoConfiguration {

    @Bean
    public GlobalExceptionHandler globalExceptionHandler() {
        return new GlobalExceptionHandler();
    }

    // Register with Spring
}
```

---

## Dependency Validation: Enforcing Layering

### Valid Dependencies

```
✓ Application imports from Starter
✓ Application imports from Core
✓ Application imports from API
✓ Application imports from Foundation

✓ Starter imports from Core
✓ Starter imports from API
✓ Starter imports from Spring Boot

✓ Core imports from API
✓ Core imports from Foundation
✓ Core imports from Spring framework

✓ API imports only from Foundation
✓ API imports only from Java standard library
```

### Invalid Dependencies (Anti-Patterns)

```
✗ API imports from Spring Boot
✗ API imports from Core
✗ Core imports from Starter
✗ Starter imports from Application code
✗ Circular dependencies (any direction)
```

### Enforce with Build System

```gradle
// gradle-enforce-dependencies.gradle

// Define dependencies that violate layering
failOnDependencyViolations = [
    // Starter → Core is OK
    // Core → API is OK
    // API → Spring (BAD)
    'api.*:org.springframework.*',
    // Core → Starter (BAD)
    'core.*:.*-starter',
]
```

---

## Partial Adoption: Using API+Core Without Starter

```java
// For non-Spring Boot applications

// Import Core tier directly
import com.barclays.global.mca.restclient.RestClientFactoryImpl;
import com.barclays.global.mca.restclient.api.RestClientFactory;

// Manually instantiate
RestTemplateFactory templateFactory = new RestTemplateFactoryImpl();
ServiceRegistry registry = new ServiceRegistryImpl();
RestClientFactory clientFactory = new RestClientFactoryImpl(
    templateFactory,
    registry
);

// Use just like Spring Boot version
RestClient client = clientFactory.createClient("mission-service");
```

---

## Three-Tier Benefits

| Benefit | How Achieved |
|---------|-------------|
| **Clean Architecture** | Clear separation of concerns |
| **Flexibility** | Use API+Core without Starter |
| **Testability** | Easy to mock interfaces |
| **Stability** | API tier rarely changes |
| **Spring Integration** | Optional Spring Boot layer |
| **Partial Adoption** | Can use without full framework |
| **Clear Dependencies** | Unidirectional graph |

---

## Anti-Patterns: What NOT To Do

### ❌ Anti-Pattern 1: Mixing Tiers

```java
// BAD - Core logic in Starter
@Configuration
public class BadStarter {
    @Bean
    public Mask<String> masker() {
        // ❌ Complex implementation logic in Starter
        // Should be in Core tier
    }
}

// Problem: Can't use Core without Spring Boot
```

### ✅ Correct Approach

```java
// GOOD - Core logic separate, Starter just wires it
// Core tier
public class StringMasker implements Mask<String> {
    // Complex implementation
}

// Starter tier
@Configuration
public class MaskingAutoConfiguration {
    @Bean
    public Mask<String> masker(MaskingProperties props) {
        // Just instantiates and wires - no logic
        return new StringMasker(props.getPatterns());
    }
}
```

### ❌ Anti-Pattern 2: API Tier Dependencies

```java
// BAD - API importing from Core
package com.barclays.global.mca.api;

import com.barclays.global.mca.core.RestClientImpl;  // ❌

public interface RestClientFactory {
    // Can't define contracts that depend on implementations
}

// Problem: Creates circular dependency risk
```

### ✅ Correct Approach

```java
// GOOD - API independent, no Core dependencies
package com.barclays.global.mca.api;

public interface RestClientFactory {
    RestClient createClient(String serviceName);  // Uses interface only
}

public interface RestClient {
    <T> T get(String path, Class<T> type);  // Uses interface only
}

// No imports from .core package
```

### ❌ Anti-Pattern 3: Circular Dependencies

```java
// BAD - Circular dependency between modules
// service-client-api imports from service-client-core
// service-client-core imports from service-client-api ✓ (OK)
// service-client-core imports from service-client-starter (❌ circular!)
// service-client-starter imports from service-client-api

// Problem: Can't build without circular dependency solver
```

### ✅ Correct Approach

```java
// GOOD - Strict unidirectional dependency graph
// Starter → Core → API → Foundation
// No cycles possible with this structure
```

---

## Migration: Adopting Layered Module Pattern

### Step 1: Extract API Tier

```gradle
// Before: Single module
dependencies {
    implementation project(':service-client')
}

// After: Separate API module
dependencies {
    implementation project(':service-client-api')
    implementation project(':service-client')  // imports api
}
```

### Step 2: Move Interfaces to API

```
// Before
service-client/src/main/java/.../RestClientFactory.java
service-client/src/main/java/.../RestClientImpl.java

// After
service-client-api/src/main/java/.../RestClientFactory.java
service-client/src/main/java/.../RestClientImpl.java
```

### Step 3: Create Starter

```gradle
// New module
dependencies {
    implementation project(':service-client')  // imports core
    implementation project(':service-client-api')
    implementation 'org.springframework.boot:spring-boot-starter'
}
```

### Step 4: Register Auto-Configuration

```
// META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports
com.barclays.global.mca.restclient.config.ServiceClientAutoConfiguration
```

---

## Next Steps

1. **Identify API contracts** - What interfaces/contracts?
2. **Extract API module** - Create separate API JAR
3. **Move implementations** - Keep Core tier focused
4. **Create Starter module** - Add Spring Boot auto-config
5. **Register auto-configs** - META-INF configuration
6. **Validate dependencies** - Enforce unidirectional graph

---

## Quick Reference: Layered Module Pattern

```
┌─────────────────────────────┐
│ Starter (Auto-Config)       │
│ • @EnableConfigurationProperties
│ • Spring Boot auto-configs   │
│ • Default bean factories     │
└─────────────────────────────┘
         ↑ imports
┌─────────────────────────────┐
│ Core (Implementations)       │
│ • Business logic             │
│ • Algorithm implementations  │
│ • Configuration classes      │
└─────────────────────────────┘
         ↑ imports
┌─────────────────────────────┐
│ API (Interfaces)             │
│ • Contract definitions       │
│ • Data transfer objects      │
│ • Exception hierarchies      │
└─────────────────────────────┘
```

**Layered Module Pattern enables clean architecture, flexibility, and partial adoption.**
