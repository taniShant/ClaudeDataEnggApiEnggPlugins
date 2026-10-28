# Spring Boot 3 Integration: Auto-Configuration & Property Binding

## Executive Summary

MCA2 leverages **Spring Boot 3's auto-configuration mechanism** to automatically detect and register EPS framework components. Applications simply add `@EnableExperienceAPI` annotation, and the framework initializes with sensible defaults, customizable via `application.properties` or `application.yml`.

**Key Concepts:**
- **Auto-Configuration Registration** — Via `META-INF/spring/*.imports` files
- **Property Binding** — Via `@ConfigurationProperties` and `@Value`
- **Conditional Beans** — Via `@ConditionalOn*` annotations
- **Environment Post-Processors** — For early environment setup

---

## Spring Boot 3 Auto-Configuration Registration

### Registration Mechanism (Spring Boot 3.x)

Spring Boot 3 uses **import mechanism** instead of deprecated `spring.factories`:

**Location:** `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`

```
# file: META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports
com.barclays.global.mca.libs.eps.config.ExperienceAPIConfig
com.barclays.global.mca.libs.filter.config.CoreFilterConfig
com.barclays.global.mca.libs.logging.config.LoggingAutoConfiguration
com.barclays.global.mca.libs.response.config.ResponseHandlingAutoConfiguration
com.barclays.global.mca.libs.exception.config.ExceptionHandlingAutoConfiguration
com.barclays.global.mca.context.config.ContextAutoConfiguration
```

### Optional Post-Processors

**Location:** `META-INF/spring/org.springframework.boot.EnvironmentPostProcessor.imports`

```
# Post-processors run early to modify environment
com.barclays.global.mca.libs.context.processor.ContextPropertyPostProcessor
com.barclays.global.mca.libs.filter.processor.FilterPropertyPostProcessor
```

### Auto-Discovery Flow

```
1. Spring Boot starts
   │
   ├─ Scans classpath for org.springframework.boot.autoconfigure.AutoConfiguration.imports
   │
   ├─ Reads registration files
   │
   ├─ Loads configuration classes:
   │   ├─ ExperienceAPIConfig
   │   ├─ CoreFilterConfig
   │   ├─ LoggingAutoConfiguration
   │   └─ ...
   │
   ├─ For each configuration class:
   │   ├─ Evaluate @ConditionalOn* annotations
   │   ├─ If conditions match: load class
   │   ├─ Scan for @Bean methods
   │   ├─ Create bean instances
   │   └─ Register with ApplicationContext
   │
   └─ Result: EPS framework fully initialized
```

---

## Property Binding: @ConfigurationProperties

### Pattern: Binding Properties to Objects

```java
// Define configuration properties class
@Configuration
@ConfigurationProperties(prefix = "mca.eps")
@Data
public class EpsConfigurationProperties {

    // application.properties: mca.eps.enabled=true
    private boolean enabled = true;

    // application.properties: mca.eps.context-ttl-seconds=28800
    private long contextTtlSeconds = 28800;

    // Nested properties
    // application.properties: mca.eps.logging.level=DEBUG
    private LoggingProperties logging;

    // Collections
    // application.properties: mca.eps.excluded-paths[0]=/health
    private List<String> excludedPaths = new ArrayList<>();

    // Maps
    // application.properties: mca.eps.headers.X-Custom-Header=value
    private Map<String, String> headers = new HashMap<>();

    @Data
    public static class LoggingProperties {
        private String level = "INFO";
        private boolean asyncEnabled = true;
        private int queueSize = 10000;
    }
}

// Enable property binding
@Configuration
@EnableConfigurationProperties(EpsConfigurationProperties.class)
public class EpsConfigAutoConfiguration {

    @Bean
    public EpsConfigurationProperties epsConfigProperties() {
        return new EpsConfigurationProperties();
    }
}
```

### Property File Formats

**application.properties (Traditional)**

```properties
# Core EPS
mca.eps.enabled=true
mca.eps.context-ttl-seconds=28800

# Logging
mca.eps.logging.level=DEBUG
mca.eps.logging.async-enabled=true
mca.eps.logging.queue-size=10000

# Lists
mca.eps.excluded-paths[0]=/health
mca.eps.excluded-paths[1]=/metrics
mca.eps.excluded-paths[2]=/swagger-ui

# Maps
mca.eps.headers.X-Custom-Header=value
mca.eps.headers.X-Another=another-value
```

**application.yml (YAML)**

```yaml
mca:
  eps:
    enabled: true
    context-ttl-seconds: 28800
    logging:
      level: DEBUG
      async-enabled: true
      queue-size: 10000
    excluded-paths:
      - /health
      - /metrics
      - /swagger-ui
    headers:
      X-Custom-Header: value
      X-Another: another-value
```

### Property Validation

```java
@Configuration
@ConfigurationProperties(prefix = "mca.eps")
@Validated  // Enable validation
@Data
public class ValidatedEpsProperties {

    @Min(1)
    @Max(86400)
    private long contextTtlSeconds = 28800;  // Between 1 and 86400

    @Pattern(regexp = "INFO|DEBUG|WARN|ERROR")
    private String logLevel = "INFO";  // Enum-like validation

    @Email
    private String notificationEmail;

    // Nested validation
    private LoggingProperties logging;

    @Data
    public static class LoggingProperties {
        @Min(1000)
        @Max(1000000)
        private int queueSize = 10000;

        @NotNull
        private String format;
    }
}
```

---

## Spring Boot 3 Auto-Configuration Best Practices

### Configuration Class Pattern

```java
@Configuration
@ConditionalOnClass(IOLSchema.class)  // Only if context is on classpath
@ConditionalOnProperty(
    name = "mca.eps.enabled",
    havingValue = "true",
    matchIfMissing = true  // Default to true if not specified
)
@EnableConfigurationProperties(EpsProperties.class)
public class ExperienceAPIAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public ContextFilter contextFilter(ObjectMapper mapper) {
        return new ContextFilter(mapper);
    }

    @Bean
    @ConditionalOnMissingBean
    public FilterRegistrationBean<CorrelationIdFilter>
        correlationIdFilterRegistration() {

        FilterRegistrationBean<CorrelationIdFilter> bean =
            new FilterRegistrationBean<>(new CorrelationIdFilter());

        bean.setOrder(0);
        bean.addUrlPatterns("/*");

        return bean;
    }

    @Bean
    @ConditionalOnProperty(name = "mca.eps.masking.enabled", havingValue = "true")
    public MaskingService maskingService(MaskingProperties props) {
        return new MaskingService(props);
    }
}
```

### Configuration Ordering

```java
// Order matters - some configs depend on others

// Step 1: Early configuration (order = -100)
@Configuration
@Order(-100)
public class EarlyEpsConfiguration { }

// Step 2: Core configuration (default order = 0)
@Configuration
public class CoreEpsConfiguration { }

// Step 3: Late configuration (order = 100)
@Configuration
@Order(100)
public class LateEpsConfiguration { }
```

---

## Conditional Annotations: @ConditionalOn*

### @ConditionalOnProperty

```java
// Register bean only if property matches
@Bean
@ConditionalOnProperty(
    name = "mca.security.oauth.enabled",
    havingValue = "true"
)
public OAuthValidatorFilter oauthFilter() {
    return new OAuthValidatorFilter();
}

// Alternative: prefix + name
@ConditionalOnProperty(
    prefix = "mca.security",
    name = "oauth.enabled",
    havingValue = "true"
)
```

### @ConditionalOnMissingBean

```java
// Register only if not already defined
@Bean
@ConditionalOnMissingBean(MaskingService.class)
public MaskingService defaultMaskingService() {
    // Only instantiated if no other MaskingService bean exists
    return new DefaultMaskingService();
}

// Application can override:
@Configuration
public class ApplicationConfig {
    @Bean
    public MaskingService maskingService() {
        return new CustomMaskingService();  // Takes precedence
    }
}
```

### @ConditionalOnClass / @ConditionalOnMissingClass

```java
// Register only if class is on classpath
@Configuration
@ConditionalOnClass(name = "com.fasterxml.jackson.databind.ObjectMapper")
public class JsonMaskingAutoConfiguration {
    // Only loaded if Jackson library is in dependencies
}

// Register only if class is NOT on classpath
@Configuration
@ConditionalOnMissingClass("com.fasterxml.jackson.databind.ObjectMapper")
public class DefaultMaskingAutoConfiguration {
    // Fallback if Jackson not available
}
```

### Combining Conditions (AND logic)

```java
// All conditions must be true
@Bean
@ConditionalOnClass(Cache.class)
@ConditionalOnProperty(name = "caching.enabled", havingValue = "true")
@ConditionalOnMissingBean(CacheManager.class)
public CacheManager cacheManager() {
    // Only created if ALL conditions are true
}
```

---

## Environment Post-Processors

### Early Property Modification

```java
// Post-processor runs BEFORE configuration classes are loaded
public class MCAEnvironmentPostProcessor
    implements EnvironmentPostProcessor {

    @Override
    public void postProcessEnvironment(
        ConfigurableEnvironment environment,
        SpringApplication application
    ) {
        // Add default properties before configs are loaded
        Map<String, Object> defaults = new HashMap<>();
        defaults.put("mca.eps.enabled", "true");
        defaults.put("mca.logging.level", "INFO");

        PropertySource<?> propertySource =
            new MapPropertySource("mca-defaults", defaults);

        environment.getPropertySources().addLast(propertySource);
    }
}

// Register in META-INF
# META-INF/spring/org.springframework.boot.EnvironmentPostProcessor.imports
com.barclays.global.mca.libs.config.MCAEnvironmentPostProcessor
```

---

## Configuration Profiles

### Environment-Specific Configurations

```java
// Dev configuration
@Configuration
@Profile("dev")
public class DevEpsConfiguration {

    @Bean
    public LoggingService devLogging() {
        return new ConsoleLoggingService();  // Console output
    }
}

// Production configuration
@Configuration
@Profile("prod")
public class ProdEpsConfiguration {

    @Bean
    public LoggingService prodLogging(...) {
        return new JsonStructuredLoggingService();  // JSON for aggregation
    }
}
```

### Profile-Specific Properties

```properties
# application.properties (defaults)
mca.eps.enabled=true

# application-dev.properties (dev profile)
logging.level=DEBUG

# application-prod.properties (prod profile)
logging.level=INFO
logging.format=json
```

### Activating Profiles

```bash
# Command line
java -jar app.jar --spring.profiles.active=prod

# Environment variable
export SPRING_PROFILES_ACTIVE=prod
java -jar app.jar

# application.properties
spring.profiles.active=prod
```

---

## Metadata for IDE Support

### Configuration Metadata

**File:** `META-INF/spring-configuration-metadata.json`

```json
{
  "groups": [
    {
      "name": "mca.eps",
      "type": "com.barclays.global.mca.libs.eps.config.EpsProperties",
      "description": "MCA EPS Framework configuration"
    }
  ],
  "properties": [
    {
      "name": "mca.eps.enabled",
      "type": "java.lang.Boolean",
      "description": "Enable EPS framework",
      "defaultValue": true
    },
    {
      "name": "mca.eps.context-ttl-seconds",
      "type": "java.lang.Long",
      "description": "Context time-to-live in seconds",
      "defaultValue": 28800
    }
  ]
}
```

### IDE Integration

With metadata file, IDEs provide:
- ✅ Auto-completion for properties
- ✅ Documentation on hover
- ✅ Validation of allowed values
- ✅ Type checking

---

## Application Setup Examples

### Minimal Application

```java
@SpringBootApplication
@EnableExperienceAPI
public class MinimalApplication {
    public static void main(String[] args) {
        SpringApplication.run(MinimalApplication.class, args);
    }
}

// application.properties
spring.application.name=card-control-api
server.port=8080

# Automatic defaults kick in:
# mca.eps.enabled=true
# logging.level=INFO
```

### Production Application (Logging + Security)

```java
@SpringBootApplication
@EnableExperienceAPI
@EnableSecureProxy
@EnableMasking
public class ProductionApplication {
    public static void main(String[] args) {
        SpringApplication.run(ProductionApplication.class, args);
    }
}

// application-prod.properties
spring.application.name=card-control-api
spring.profiles.active=prod
server.port=8080

# EPS Configuration
mca.eps.enabled=true
mca.eps.context-ttl-seconds=28800
mca.eps.masking.enabled=true

# Logging
logging.config=classpath:log4j2-prod.xml
logging.level.com.barclays.global.mca=INFO
logging.level.org.springframework.web=WARN

# Security
oauth.validation.enabled=true
oauth.jwt.issuer=https://auth.example.com
oauth.jwt.audience=api.example.com

# Masking patterns
masking.patterns.credit-card=^([0-9]{4}).*([0-9]{4})$
masking.patterns.email=^[^@]+@(.+)$
```

---

## Troubleshooting Auto-Configuration

### Issue: Configuration Class Not Loaded

**Check:**
1. Is class registered in `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`?
2. Are @ConditionalOn* conditions met?
3. Is the jar on classpath?

```bash
# Debug auto-configuration
java -jar app.jar --debug | grep ExperienceAPIAutoConfiguration

# Check if loaded:
# "Matched: ExperienceAPIConfig (...)
# "Did not match: SomeOtherConfig (..."
```

### Issue: Properties Not Being Read

**Check:**
1. Is `@ConfigurationProperties` on the class?
2. Is `@EnableConfigurationProperties` on configuration?
3. Property name matches prefix + property name?
4. Format correct (kebab-case in properties, camelCase in code)?

```properties
# application.properties uses kebab-case
mca.eps.context-ttl-seconds=28800

# Maps to camelCase field
@ConfigurationProperties(prefix = "mca.eps")
public class EpsProperties {
    private long contextTtlSeconds;  // camelCase
}
```

### Issue: Wrong Bean Being Injected

**Check:**
1. Multiple beans of same type?
2. Use `@ConditionalOnMissingBean` to prevent duplicates?
3. Use `@Primary` to designate preferred bean?

```java
@Bean
@Primary  // This bean takes precedence
public MaskingService primaryMaskingService() {
    return new JsonStringMasker();
}

@Bean
public MaskingService secondaryMaskingService() {
    return new StringMasker();
}
```

---

## Next Steps

1. **Add @EnableExperienceAPI** — Enable core framework
2. **Configure application.properties** — Customize EPS settings
3. **Verify bean creation** — Check Spring Boot debug output
4. **Set profiles** — Use dev/prod configurations
5. **Add metadata** — Provide IDE support

---

## Quick Reference: Spring Boot 3 Integration

```
Auto-Configuration Registration
    META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports
                    ↓
                Configuration Classes Loaded
                    ↓
                @ConditionalOn* Evaluated
                    ↓
                Matched Configurations
                    ↓
                @Bean Methods Executed
                    ↓
                Properties Bound via @ConfigurationProperties
                    ↓
                Beans Registered in ApplicationContext
                    ↓
                Framework Initialized
```

**Spring Boot 3 auto-configuration provides seamless framework integration with zero configuration required.**
