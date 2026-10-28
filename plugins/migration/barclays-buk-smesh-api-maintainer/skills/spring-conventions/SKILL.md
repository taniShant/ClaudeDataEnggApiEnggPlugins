---
name: spring-conventions
description: Spring best practices for Barclays iAPI projects. Constructor injection refactoring, Lombok integration, bean disambiguation, configuration class organization, and scoped bean handling. Can be applied standalone or as part of SDK3 migration.
owner: Barclays AI (barclaysai@barclays.com)
version: 1.0.0
license: Proprietary. For Barclays internal use only.
user-invocable: false
source: barclays-claude-code-plugins/plugins/sdk3-migration/skills/spring_conventions/SKILL.md
owner: Barclays AI (barclaysai@barclays.com)
review-trigger: When SDK3 BOM versions change or new migration patterns are identified
status: Full
---

# Spring Conventions & Best Practices

> See CLAUDE.md for cross-platform execution rules and tool preferences.

> **Automation Note:** When used during SDK3 migration (Phase 0.5), this skill runs fully autonomously. All refactoring is applied, compiled, tested, and committed without user interaction.
## Quick Start

Spring Boot 3 conventions applied during SDK3 migration.

```java
// Constructor injection (preferred over field injection)
@Service
public class MyService {
    private final MyRepository repo;
    
    public MyService(MyRepository repo) { // Spring autowires automatically
        this.repo = repo;
    }
}
```


## Overview

This skill covers Spring best practices applicable to any Barclays iAPI project. It can be used:
- **During SDK3 migration** as an optional phase (between Phase 0 and Phase 1)
- **Standalone** on any Spring Boot project to improve code quality

## 1. Constructor Injection

All field-based and setter-based `@Autowired` injections must be converted to constructor injection with `final` fields.

### Field Injection → Constructor Injection

```java
// BEFORE
@Service
public class PaymentService {
    @Autowired
    private PaymentGateway gateway;

    @Autowired
    private PaymentRepository repository;
}

// AFTER
@Service
public class PaymentService {
    private final PaymentGateway gateway;
    private final PaymentRepository repository;

    public PaymentService(PaymentGateway gateway, PaymentRepository repository) {
        this.gateway = gateway;
        this.repository = repository;
    }
}
```

### Setter Injection → Constructor Injection

```java
// BEFORE
@Service
public class PaymentService {
    private PaymentValidator validator;

    @Autowired
    public void setValidator(PaymentValidator validator) {
        this.validator = validator;
    }
}

// AFTER
@Service
public class PaymentService {
    private final PaymentValidator validator;

    public PaymentService(PaymentValidator validator) {
        this.validator = validator;
    }
}
```

### What NOT to Convert

| Pattern | Action |
|---------|--------|
| `@Value("${...}")` fields | Keep as-is. Do NOT move to constructor. |
| `static final Logger` | Keep as-is. Static fields are not dependencies. |
| `@Scheduled` methods | Keep as-is. Not injection-related. |
| `@Autowired` on a constructor (already correct) | Keep as-is. Already best practice. |

---

## 2. Lombok Integration

Apply `@RequiredArgsConstructor` to replace boilerplate constructors when eligible.

### Eligibility Criteria

A class is eligible for `@RequiredArgsConstructor` when ALL of these are true:
- All injected fields are `final`
- Constructor only assigns fields (no custom logic)
- Class has a single constructor
- Class is **NOT** annotated with `@Configuration` (Lombok conflicts with Spring CGLIB proxies)
- Class does **NOT** extend a parent class that has constructor arguments

```java
// BEFORE
@Service
public class PaymentService {
    private final PaymentGateway gateway;
    private final PaymentRepository repository;

    public PaymentService(PaymentGateway gateway, PaymentRepository repository) {
        this.gateway = gateway;
        this.repository = repository;
    }
}

// AFTER
@Service
@RequiredArgsConstructor
public class PaymentService {
    private final PaymentGateway gateway;
    private final PaymentRepository repository;
}
```

### When NOT to Use

**`@Configuration` classes** - Lombok-generated constructors can break Spring CGLIB proxies:
```java
// BAD
@Configuration
@RequiredArgsConstructor
public class DatabaseConfig { ... }

// GOOD - manual constructor
@Configuration
public class DatabaseConfig {
    private final DataSourceProperties properties;

    public DatabaseConfig(DataSourceProperties properties) {
        this.properties = properties;
    }
}
```

**Classes with inheritance** - Lombok cannot generate `super()` calls:
```java
// BAD - missing super() call
@RequiredArgsConstructor
public class PaymentServiceImpl extends BaseService {
    private final PaymentGateway gateway;
}

// GOOD - manual constructor with super()
public class PaymentServiceImpl extends BaseService {
    private final PaymentGateway gateway;

    public PaymentServiceImpl(BaseConfig config, PaymentGateway gateway) {
        super(config);
        this.gateway = gateway;
    }
}
```

**Prerequisite:** Lombok must be in `build.gradle`:
```gradle
compileOnly 'org.projectlombok:lombok'
annotationProcessor 'org.projectlombok:lombok'
```

---

## 3. Bean Disambiguation

### `@Primary` and `@Qualifier`

When multiple beans of the same type exist, add `@Primary` to the default and `@Qualifier` to distinguish them:

```java
// Configuration
@Configuration
public class HttpClientConfig {
    @Bean
    @Primary
    @Qualifier("internal")
    public RestTemplate internalRestTemplate() { ... }

    @Bean
    @Qualifier("external")
    public RestTemplate externalRestTemplate() { ... }
}

// Injection
@Service
public class PaymentService {
    private final RestTemplate restTemplate;

    public PaymentService(@Qualifier("external") RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }
}
```

### Collection Injection (Do NOT Qualify)

When a `List<T>` or `Set<T>` parameter intentionally collects all beans of that type, do NOT add `@Primary` or `@Qualifier`:

```java
// CORRECT - intentionally collecting all RestTemplate beans
@Service
public class RestTemplateManager {
    private final List<RestTemplate> allTemplates;

    public RestTemplateManager(List<RestTemplate> allTemplates) {
        this.allTemplates = allTemplates;
    }
}
```

### Generic Type Disambiguation

When multiple beans share a generic type (e.g., `List<String>`), use `@Qualifier` on both the bean definition and injection point:

```java
@Configuration
public class ListConfig {
    @Bean
    @Qualifier("allowedCountries")
    public List<String> allowedCountries() {
        return Arrays.asList("US", "UK", "CA");
    }

    @Bean
    @Qualifier("blockedCountries")
    public List<String> blockedCountries() {
        return Arrays.asList("XX", "YY");
    }
}

@Service
public class CountryService {
    private final List<String> allowedCountries;

    public CountryService(@Qualifier("allowedCountries") List<String> allowedCountries) {
        this.allowedCountries = allowedCountries;
    }
}
```

---

## 4. Configuration Class Organization

### Simplify Application.java

Move all `@Bean` definitions out of `Application.java` into themed `@Configuration` classes. Application.java should contain only startup logic.

```java
// BEFORE - bloated Application.java
@SpringBootApplication
public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }

    @Bean
    public RestTemplate restTemplate() { ... }

    @Bean
    public ObjectMapper objectMapper() { ... }

    @Bean
    public ExecutorService executorService() { ... }
}

// AFTER - Application.java
@SpringBootApplication
public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}

// NEW - HttpClientConfig.java
@Configuration
public class HttpClientConfig {
    @Bean
    public RestTemplate restTemplate() { ... }
}

// NEW - JacksonConfig.java
@Configuration
public class JacksonConfig {
    @Bean
    public ObjectMapper objectMapper() { ... }
}

// NEW - ExecutorConfig.java
@Configuration
public class ExecutorConfig {
    @Bean
    public ExecutorService executorService() { ... }
}
```

### Recommended Groupings

| Config Class | Beans |
|---|---|
| `HttpClientConfig` | REST clients, RestTemplate, connection pooling |
| `JacksonConfig` | ObjectMapper, serialization settings |
| `ExecutorConfig` | Thread pools, async executors |
| `SecurityConfig` | Security beans |
| `DatabaseConfig` | DataSource, JPA, transaction managers |

---

## 5. Component Scanning

Replace overly broad `@ComponentScan` with specific package paths:

```java
// BAD - scans entire com.barclays package tree
@SpringBootApplication
@ComponentScan(basePackages = "com.barclays")
public class Application { ... }

// GOOD - specific packages
@SpringBootApplication
@ComponentScan(basePackages = {
    "com.barclays.api.payment.service",
    "com.barclays.api.payment.controller",
    "com.barclays.api.payment.config"
})
public class Application { ... }
```

To exclude specific classes, use `excludeFilters`:
```java
@ComponentScan(
    basePackages = "com.barclays.api.payment",
    excludeFilters = @ComponentScan.Filter(
        type = FilterType.REGEX,
        pattern = "com\\.barclays\\.api\\.payment\\.legacy\\..*"
    )
)
```

---

## 6. Scoped Beans

Request/session scoped beans injected into singletons **must** have `proxyMode` set, otherwise the singleton caches the first request's bean forever.

```java
// BAD - stale data
@Component
@Scope("request")
public class RequestContext { ... }

// GOOD - proxy ensures fresh instance per request
@Component
@Scope(value = "request", proxyMode = ScopedProxyMode.TARGET_CLASS)
public class RequestContext { ... }
```

---

## 7. Circular Dependencies

When converting to constructor injection, circular dependencies surface at startup.

**Fix:** Add `@Lazy` to the less critical side of the dependency:

```java
public PaymentService(
        PaymentGateway gateway,
        @Lazy PaymentValidator validator) {
    this.gateway = gateway;
    this.validator = validator;
}
```

Use `@Lazy` sparingly. If a class has many circular dependencies, it likely needs a design review.

---

## 8. Optional Dependencies

When a dependency may be absent in certain profiles:

```java
public PaymentService(
        PaymentGateway gateway,
        @Autowired(required = false) OptionalService optionalService) {
    this.gateway = gateway;
    this.optionalService = optionalService; // may be null
}
```

---

## 9. High Dependency Count (>5)

A constructor with more than 5 parameters suggests the class has too many responsibilities. Prefer splitting the class. If splitting is not feasible in the current scope, proceed but flag it for a future refactor.

---

## 10. Test Class Patterns

### Spring Boot Tests

```java
// BEFORE
@SpringBootTest
public class PaymentServiceTest {
    @Autowired
    private PaymentService paymentService;

    @MockBean
    private PaymentGateway gateway;
}

// AFTER
@SpringBootTest
public class PaymentServiceTest {
    private final PaymentService paymentService;

    @MockitoBean
    private PaymentGateway gateway;

    @Autowired
    public PaymentServiceTest(PaymentService paymentService) {
        this.paymentService = paymentService;
    }
}
```

### Unit Tests with @InjectMocks

Replace `@InjectMocks` with explicit construction:

```java
// BEFORE
public class PaymentServiceUnitTest {
    @InjectMocks
    private PaymentService paymentService;

    @Mock
    private PaymentGateway gateway;

    @Mock
    private PaymentRepository repository;

    @Before
    public void setup() {
        MockitoAnnotations.initMocks(this);
    }
}

// AFTER
public class PaymentServiceUnitTest {
    private PaymentService paymentService;

    @Mock
    private PaymentGateway gateway;

    @Mock
    private PaymentRepository repository;

    @BeforeEach
    public void setup() {
        MockitoAnnotations.openMocks(this);
        paymentService = new PaymentService(gateway, repository);
    }
}
```

---

## Execution Workflow

### Discovery

Search for all patterns that need attention:

```
1. @Autowired on fields (grep for @Autowired followed by private/protected)
2. @Autowired on setters (grep for @Autowired followed by public void set)
3. Broad @ComponentScan (grep for @ComponentScan)
4. @Scope without proxyMode (grep for @Scope("request") or @Scope("session"))
5. @Bean definitions in Application.java
6. Multiple beans of same return type
```

### Refactoring Order

1. Convert field/setter injection → constructor injection (production code)
2. Apply Lombok `@RequiredArgsConstructor` where eligible
3. Reorganize configuration classes
4. Add `@Qualifier` / `@Primary` where needed
5. Fix scoped beans
6. Optimize component scanning
7. Convert test class injection
8. Compile check: `$GRADLE_CMD compileJava compileTestJava`
9. Run tests: `$GRADLE_CMD test`

### Validation

After all changes:

Use Grep tool to find remaining `@Autowired` annotations in `src/` and verify none are field/setter injections (exclude constructor injection patterns and `@Autowired(required` patterns).

```bash
# Build must pass
$GRADLE_CMD clean build -x integrationTest
```

---

**Skill Version:** 2.0.0

## Agent Self-Check

Before executing, verify:
- [ ] All required inputs are present
- [ ] Skill documentation has been loaded
- [ ] Scope boundary is understood — no out-of-scope changes
- [ ] Iron Rules (No Assumptions, Version Source of Truth) acknowledged
- [ ] Output format understood
