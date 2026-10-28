# Enable Annotation Pattern: Conditional Feature Activation

## Executive Summary

The **Enable Annotation Pattern** uses Spring's `@EnableConfigurationProperties` and `@ConditionalOnProperty` to provide fine-grained, opt-in feature activation. Applications explicitly enable frameworks via annotations (`@EnableExperienceAPI`, `@EnableMasking`), making dependencies explicit and preventing accidental framework activation.

**Pattern Definition:**
> "Enable pattern provides annotated entry points that conditionally register Spring auto-configurations based on properties and classpath conditions."

**MCA2 Application:**
- **Enable Annotations:** @EnableExperienceAPI, @EnableSecureProxy, @EnableMasking, @EnableRouter, etc.
- **Configuration Class:** ExperienceAPIConfig, MaskingConfig, etc.
- **Conditional Beans:** @ConditionalOnProperty, @ConditionalOnClass
- **Property-Driven:** Configured via application.properties

---

## Core Enable Annotations in MCA2

### 1. @EnableExperienceAPI (Core EPS)

**Purpose:** Activate core EPS framework

**Module:** mca-eps-core

```java
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Import({ExperienceAPIConfig.class})  // Imports auto-config
public @interface EnableExperienceAPI {
    // Marker annotation - no properties
}

// Usage in application
@SpringBootApplication
@EnableExperienceAPI  // Enables core EPS
public class CardControlApplication {
    public static void main(String[] args) {
        SpringApplication.run(CardControlApplication.class, args);
    }
}

// Result: Automatically imports and configures
// - Filter chain (CorrelationId, Exception, etc.)
// - Context system (ContextFilter, argument resolver)
// - Response handling
// - Exception mapping
```

### 2. Optional Feature Enable Annotations

```java
@SpringBootApplication
@EnableExperienceAPI
@EnableMasking            // Optional: data redaction
@EnableSecureProxy         // Optional: secure proxy
@EnableRouter              // Optional: routing
@EnableMisServiceClient   // Optional: MIS integration
@EnableReferenceData      // Optional: reference data
public class Application { }
```

---

## Enable Pattern Implementation

### How Enable Annotations Work

```
1. Developer writes: @EnableExperienceAPI
   │
   ├─ Spring processes @Import(ExperienceAPIConfig.class)
   │
   ├─ Loads ExperienceAPIConfig class
   │
   ├─ Scans for @Bean methods
   │
   ├─ Evaluates @ConditionalOn* annotations
   │
   ├─ Creates bean instances conditionally
   │
   └─ Result: Framework is configured

Example: ExperienceAPIConfig
   @Configuration
   public class ExperienceAPIConfig {

       @Bean
       public FilterRegistrationBean<CorrelationIdFilter> correlationId() {
           return new FilterRegistrationBean<>(new CorrelationIdFilter());
       }

       @Bean
       public IOLContextHandlerMethodArgumentResolver contextResolver() {
           return new IOLContextHandlerMethodArgumentResolver();
       }

       // ... more beans
   }

2. Spring creates instances:
   ├─ CorrelationIdFilter bean
   ├─ ExceptionFilter bean
   ├─ IOLContextHandlerMethodArgumentResolver bean
   └─ All other configured beans

3. Beans are wired into application:
   ├─ Filters registered with DispatcherServlet
   ├─ Argument resolver registered with Spring MVC
   └─ Framework is fully initialized
```

### Configuration Class Pattern

```java
@Configuration
public class ExperienceAPIConfig {

    // Core filter beans
    @Bean
    public FilterRegistrationBean<CorrelationIdFilter>
        correlationIdFilterRegistration() {

        FilterRegistrationBean<CorrelationIdFilter> bean =
            new FilterRegistrationBean<>(new CorrelationIdFilter());

        bean.setOrder(0);
        bean.addUrlPatterns("/*");

        return bean;
    }

    // Argument resolver for @IOLContext
    @Bean
    public HandlerMethodArgumentResolver
        iolContextHandlerMethodArgumentResolver() {

        return new IOLContextHandlerMethodArgumentResolver();
    }

    // Response interceptor
    @Bean
    public ResponseInterceptor apiResponseInterceptor() {
        return new ResponseInterceptor();
    }

    // More beans...
}

// Activation via annotation
@SpringBootApplication
@EnableExperienceAPI  // Imports ExperienceAPIConfig
public class Application { }
```

---

## Conditional Beans: @ConditionalOn* Annotations

### Pattern: Conditional on Property

```java
// Register masking strategy only if property is set
@Configuration
@ConditionalOnProperty(
    name = "masking.enabled",
    havingValue = "true"
)
public class MaskingConfig {

    @Bean
    public Mask<String> stringMasker(MaskingProperties props) {
        return new StringMasker(props.getPatterns());
    }
}

// Application properties
# application.properties
masking.enabled=true
masking.strategy=string
```

### Pattern: Conditional on Missing Bean

```java
// Register default if not already provided
@Configuration
public class DefaultMaskingConfig {

    @Bean
    @ConditionalOnMissingBean(Mask.class)
    public Mask<String> defaultMasker() {
        // Fallback to StringMasker if no masker configured
        return new StringMasker(Collections.emptyList());
    }
}

// Application can override:
@Configuration
public class CustomMaskingConfig {

    @Bean
    public Mask<String> masker() {
        return new JsonStringMasker(...);  // Custom implementation
    }
}
```

### Pattern: Conditional on Classpath

```java
// Register OAuth validator only if JWT library is on classpath
@Configuration
@ConditionalOnClass(name = "org.springframework.security.oauth2.jwt.JwtDecoder")
public class OAuthValidatorAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public OAuthValidatorFilter oauthValidatorFilter(...) {
        return new OAuthValidatorFilter(...);
    }
}

// Only activates if:
// 1. Spring Security OAuth2 library is in build.gradle
// 2. JwtDecoder class is available on classpath
// 3. No other OAuthValidatorFilter bean already exists
```

---

## Enable Pattern: Configuration Properties

### Property-Driven Configuration

```properties
# Core EPS Framework
context.validation.enabled=true

# Filter configuration
filter.correlationid.enabled=true
filter.correlationid.header.name=Correlation-ID

filter.exception.enabled=true
filter.exception.stack-trace-enabled=false

filter.disable-session.enabled=true

# Conditional filter toggles
oauth.validation.enabled=true
oauth.jwt.issuer=https://auth.example.com
oauth.jwt.audience=api.example.com

ddos.prevention.enabled=false
ddos.requests-per-minute=1000

# Masking
masking.enabled=true
masking.patterns.credit-card=^([0-9]{4}).*([0-9]{4})$

# Logging
logging.level.com.barclays.global.mca=DEBUG
logging.config=classpath:log4j2.xml
```

---

## Enable Pattern Benefits

| Benefit | How Achieved |
|---------|-------------|
| **Explicit Dependencies** | Must annotate to enable frameworks |
| **No Surprises** | Clearly see what's activated |
| **Flexible** | Choose implementations at config time |
| **Testable** | Easy to enable/disable for testing |
| **Optional Features** | Choose which frameworks to use |
| **Multi-Environment** | Different configs per environment |

---

## Complete Example: Multi-Tier Application

### Development Configuration

```properties
# dev.properties
oauth.validation.enabled=false
masking.enabled=false
logging.level.com.barclays.global.mca=DEBUG
```

```java
// Application
@SpringBootApplication
@EnableExperienceAPI
public class DevApplication { }
```

### Production Configuration

```properties
# prod.properties
oauth.validation.enabled=true
oauth.jwt.issuer=https://prod-auth.example.com
masking.enabled=true
masking.patterns.credit-card=...
logging.level.com.barclays.global.mca=INFO
logging.config=classpath:log4j2-prod.xml
```

```java
// Application (same code)
@SpringBootApplication
@EnableExperienceAPI
@EnableMasking                   // Masking for production
public class ProdApplication { }
```

---

## Enable Pattern Anti-Patterns

### ❌ Anti-Pattern 1: Missing Enable Annotation

```java
// BAD - No explicit enable
@SpringBootApplication
public class Application { }

// Problem: Framework not configured, context system doesn't work
```

### ✅ Correct Approach

```java
// GOOD - Explicitly enable framework
@SpringBootApplication
@EnableExperienceAPI
@EnableMasking
public class Application { }
```

### ❌ Anti-Pattern 2: Hard-Coded Configuration

```java
// BAD - Configuration in code
@Configuration
public class AppConfig {
    @Bean
    public Mask<String> masker() {
        if (System.getProperty("env").equals("prod")) {
            return new JsonStringMasker();
        } else {
            return new StringMasker();
        }
    }
}

// Problem: Configuration mixed with code, no external control
```

### ✅ Correct Approach

```java
// GOOD - Configuration in properties
@Configuration
@ConditionalOnProperty(name = "masking.strategy", havingValue = "json")
public class JsonMaskingConfig {
    @Bean
    public Mask<String> masker(...) {
        return new JsonStringMasker(...);
    }
}

# application.properties
masking.strategy=json
```

---

## Testing with Enable Annotations

### Test Configuration

```java
@SpringBootTest
@TestPropertySource(properties = {
    "oauth.validation.enabled=false",
    "masking.enabled=true",
    "masking.strategy=string"
})
public class CardServiceTest {

    @Autowired
    private Mask<String> masker;

    @Autowired
    private CardService cardService;

    @Test
    public void testLockCard() {
        // OAuth disabled for simpler testing
        // Masking still enabled for validation
    }
}
```

---

## Next Steps

1. **Enable Core Framework:** @EnableExperienceAPI
2. **Enable Features:** @EnableMasking, @EnableSecureProxy (as needed)
3. **Configure Properties:** Set feature toggles in application.properties
4. **Test Configuration:** Use @TestPropertySource for test configs
5. **Document Dependencies:** List all @Enable* annotations

---

## Quick Reference: Enable Annotations

| Annotation | Module | Purpose |
|-----------|--------|---------|
| **@EnableExperienceAPI** | mca-eps-core | Core EPS framework |
| **@EnableSecureProxy** | mca-secure-proxy-core | Secure proxy service |
| **@EnableRouter** | mca-router-http | HTTP routing |
| **@EnableMasking** | mca-masking | Data masking |
| **@EnableMisServiceClient** | mca-mis-client | MIS backend service client |

**Enable Annotation Pattern provides explicit, flexible, property-driven framework activation.**
