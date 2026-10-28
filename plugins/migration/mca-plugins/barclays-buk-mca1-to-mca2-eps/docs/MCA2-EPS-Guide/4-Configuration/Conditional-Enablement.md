# Conditional Enablement: Feature Toggles via Properties

## Executive Summary

**Conditional Enablement** uses Spring's `@ConditionalOnProperty` to provide feature toggles, allowing applications to selectively enable/disable frameworks at runtime via properties without code changes. This enables:
- Development vs. production configurations
- A/B testing of new features
- Gradual rollout strategies
- Emergency disable of problematic features

---

## Conditional Beans Pattern

### Core Mechanism

```java
@Bean
@ConditionalOnProperty(
    name = "mca.security.oauth.enabled",
    havingValue = "true"
)
public OAuthValidatorFilter oauthFilter() {
    return new OAuthValidatorFilter();
}

// Behavior:
// If property is true  → Bean is created and registered
// If property is false → Bean is NOT created
// If property missing  → Bean is NOT created (default)
```

### Property Matching Variations

```java
// Exact value match
@ConditionalOnProperty(
    name = "feature.flag",
    havingValue = "enabled"
)

// Default to true if missing
@ConditionalOnProperty(
    name = "feature.flag",
    havingValue = "true",
    matchIfMissing = true
)

// Match if property exists (any value)
@ConditionalOnProperty(
    name = "feature.flag"  // No havingValue
)

// Prefix + name (cleaner namespace)
@ConditionalOnProperty(
    prefix = "mca.security",
    name = "oauth.enabled",
    havingValue = "true"
)
```

---

## MCA2 Feature Toggles

### Core Features (Typically Always On)

```properties
# Core EPS features - usually not toggled
mca.eps.enabled=true
mca.eps.context.enabled=true
mca.eps.logging.enabled=true
mca.eps.response.handling.enabled=true
mca.eps.exception.handling.enabled=true
```

### Optional Security Features

```java
// OAuth2/JWT validation (conditional)
@Bean
@ConditionalOnProperty(
    name = "mca.security.oauth.enabled",
    havingValue = "true"
)
public FilterRegistrationBean<OAuthValidatorFilter>
    oauthValidatorFilterRegistration() {

    FilterRegistrationBean<OAuthValidatorFilter> bean =
        new FilterRegistrationBean<>(new OAuthValidatorFilter());

    bean.setOrder(4);
    bean.addUrlPatterns("/api/*");

    return bean;
}

// Application configuration
# Disable OAuth for local development
mca.security.oauth.enabled=false

# Enable OAuth in production
mca.security.oauth.enabled=true
```

### DDoS Prevention Toggle

```java
// DDoS prevention (optional)
@Bean
@ConditionalOnProperty(
    name = "mca.security.ddos.enabled",
    havingValue = "true"
)
public FilterRegistrationBean<DdosFilter>
    ddosFilterRegistration(DdosPreventor ddosPreventor) {

    FilterRegistrationBean<DdosFilter> bean =
        new FilterRegistrationBean<>(new DdosFilter(ddosPreventor));

    bean.setOrder(5);
    bean.addUrlPatterns("/api/*");

    return bean;
}

// Configuration
mca.security.ddos.enabled=true
mca.security.ddos.rate-limit=1000
```

### Request Validation Toggle

```java
// Input validation (optional)
@Bean
@ConditionalOnProperty(
    name = "mca.validation.enabled",
    havingValue = "true"
)
public FilterRegistrationBean<ValidationFilter>
    validationFilterRegistration() {

    FilterRegistrationBean<ValidationFilter> bean =
        new FilterRegistrationBean<>(new ValidationFilter());

    bean.setOrder(6);
    bean.addUrlPatterns("/api/*");

    return bean;
}

# application.properties
mca.validation.enabled=true
```

### Data Masking Toggle

```java
// Data masking (optional)
@Bean
@ConditionalOnProperty(
    name = "mca.masking.enabled",
    havingValue = "true"
)
public MaskingService maskingService(MaskingProperties props) {
    return new MaskingService(props);
}

# Enable masking in production, disable in dev
mca.masking.enabled=true
mca.masking.patterns.credit-card=^([0-9]{4}).*([0-9]{4})$
```

### Logging Level Control

```java
// Dynamic logging (optional)
@Bean
@ConditionalOnProperty(
    name = "mca.logging.dynamic-level.enabled",
    havingValue = "true"
)
public FilterRegistrationBean<DynamicLoggingFilter>
    dynamicLoggingFilterRegistration() {

    FilterRegistrationBean<DynamicLoggingFilter> bean =
        new FilterRegistrationBean<>(new DynamicLoggingFilter());

    bean.setOrder(7);
    bean.addUrlPatterns("/*");

    return bean;
}

# Enable dynamic log level adjustment
mca.logging.dynamic-level.enabled=true
```

---

## Environment-Specific Configurations

### Development Profile

```properties
# application-dev.properties
spring.profiles.active=dev

# Core (always on)
mca.eps.enabled=true

# Security disabled for ease of development
mca.security.oauth.enabled=false
mca.security.ddos.enabled=false

# Validation enabled for development
mca.validation.enabled=true

# No masking for local debugging
mca.masking.enabled=false

# Verbose logging
logging.level.com.barclays.global.mca=DEBUG
mca.logging.dynamic-level.enabled=false
```

### Test Profile

```properties
# application-test.properties
spring.profiles.active=test

# Minimal configuration for speed
mca.eps.enabled=true

# Security disabled in tests
mca.security.oauth.enabled=false
mca.security.ddos.enabled=false

# Validation enabled
mca.validation.enabled=true

# Masking enabled (test masking logic)
mca.masking.enabled=true

# Quiet logging
logging.level.com.barclays.global.mca=WARN
```

### Production Profile

```properties
# application-prod.properties
spring.profiles.active=prod

# Core enabled
mca.eps.enabled=true

# Security fully enabled
mca.security.oauth.enabled=true
mca.security.oauth.issuer=https://prod-auth.example.com
mca.security.ddos.enabled=true
mca.security.ddos.rate-limit=5000

# Validation enabled
mca.validation.enabled=true

# Masking enabled
mca.masking.enabled=true
mca.masking.patterns.credit-card=^([0-9]{4}).*([0-9]{4})$
mca.masking.patterns.email=^[^@]+@(.+)$

# Structured logging
logging.level.com.barclays.global.mca=INFO
logging.config=classpath:log4j2-prod.xml
```

---

> **Note:** Context storage backends (mca-context-store-rdb, mca-context-store-mongo, mca-context-store-ehcache) are part of the Secure Proxy module, not the core EPS framework. See the Secure Proxy documentation for context store selection and configuration.

---

## Property Validation

### Constraints for Feature Flags

```java
@Configuration
@ConfigurationProperties(prefix = "mca")
@Validated
@Data
public class MCAProperties {

    @Data
    public static class Security {
        // OAuth flag
        @NotNull
        private Boolean oauthEnabled = false;

        @Email
        private String oauthIssuer;

        // DDoS flag
        @NotNull
        private Boolean ddosEnabled = false;

        @Min(1)
        @Max(100000)
        private Long ddosRateLimit = 1000L;
    }

    @Data
    public static class Validation {
        @NotNull
        private Boolean enabled = true;

        @NotEmpty
        private List<String> excludedPaths = new ArrayList<>();
    }

    @Data
    public static class Masking {
        @NotNull
        private Boolean enabled = false;

        @NotEmpty
        private Map<String, String> patterns = new HashMap<>();
    }
}

// Validation happens at startup
// Invalid configurations fail fast
```

---

## Runtime Feature Toggling

### Dynamic Property Updates (Advanced)

```java
// Not supported natively in Spring Boot
// Workaround: Reload configuration from external source

@Component
public class FeatureToggleService {

    @Autowired
    private Environment environment;

    public boolean isOAuthEnabled() {
        String enabled = environment.getProperty("mca.security.oauth.enabled");
        return "true".equalsIgnoreCase(enabled);
    }

    public boolean isDdosPreventionEnabled() {
        return environment.getProperty(
            "mca.security.ddos.enabled",
            Boolean.class,
            false
        );
    }

    // Usage in code
    @GetMapping("/api/data")
    public ResponseEntity<Data> getData() {
        if (isOAuthEnabled()) {
            // OAuth validation already happened in filter
            // This is just for additional runtime checks
        }
        return ResponseEntity.ok(data);
    }
}

// Note: Filter beans are created at startup
// Can't toggle filters at runtime without advanced setup
// Use @ConditionalOnProperty for startup-time toggles
```

---

## Advanced: Feature Flags with Spring Cloud Config

### Centralized Configuration

```java
// Connect to Spring Cloud Config Server for centralized config
@Configuration
@PropertySource("classpath:application-config-server.properties")
public class ConfigServerProperties {
    // Properties loaded from remote config server
}

# bootstrap.yml (loaded before application.yml)
spring:
  cloud:
    config:
      uri: http://config-server:8888
      profile: prod
      name: card-control-api
```

### Feature Toggle Service (with Config Server)

```java
@Component
public class RemoteFeatureToggleService {

    @Autowired
    private ConfigClient configClient;

    @Autowired
    private Environment environment;

    public boolean isFeatureEnabled(String featureName) {
        // Query Config Server for current status
        String value = environment.getProperty(
            "features." + featureName + ".enabled"
        );
        return "true".equalsIgnoreCase(value);
    }

    // Refresh configuration from server
    @PostMapping("/refresh")
    public void refreshConfiguration() {
        configClient.refresh();
        // Beans with @RefreshScope are updated
    }
}

// Beans that can be refreshed at runtime
@Component
@RefreshScope
public class RefreshableFeatureService {
    @Value("${mca.security.oauth.enabled}")
    private boolean oauthEnabled;

    // This bean is recreated when /refresh is called
}
```

---

## Testing with Conditional Properties

### Test with Feature Disabled

```java
@SpringBootTest
@TestPropertySource(properties = {
    "mca.security.oauth.enabled=false",
    "mca.security.ddos.enabled=false"
})
public class LocalDevelopmentTest {

    @Autowired
    private ApplicationContext context;

    @Test
    public void oauthFilterShouldNotBeRegistered() {
        // OAuthValidatorFilter should NOT be in context
        assertThat(
            context.containsBean("oauthValidatorFilter")
        ).isFalse();
    }
}
```

### Test with Feature Enabled

```java
@SpringBootTest
@TestPropertySource(properties = {
    "mca.security.oauth.enabled=true",
    "mca.security.oauth.issuer=https://test-auth.example.com"
})
public class SecurityEnabledTest {

    @Autowired
    private ApplicationContext context;

    @Autowired(required = false)
    private OAuthValidatorFilter oauthFilter;

    @Test
    public void oauthFilterShouldBeRegistered() {
        assertThat(oauthFilter).isNotNull();
    }
}
```

---

## Common Patterns

### Pattern 1: Core Always On, Optionals Off by Default

```properties
# Core features always enabled
mca.eps.enabled=true
mca.eps.context.enabled=true
mca.eps.logging.enabled=true

# Optional features off by default
mca.security.oauth.enabled=false
mca.security.ddos.enabled=false
mca.validation.enabled=false
```

### Pattern 2: Production Fully Enabled

```properties
# All features enabled in production
mca.eps.enabled=true
mca.security.oauth.enabled=true
mca.security.ddos.enabled=true
mca.validation.enabled=true
mca.masking.enabled=true
```

### Pattern 3: Gradual Rollout

```properties
# Week 1: New feature disabled
feature.new-payment-flow.enabled=false

# Week 2: 10% enabled (load balancing)
feature.new-payment-flow.enabled=true
feature.new-payment-flow.traffic-percentage=10

# Week 3: 50% enabled
feature.new-payment-flow.traffic-percentage=50

# Week 4: 100% enabled
feature.new-payment-flow.traffic-percentage=100
```

---

## Anti-Patterns: What NOT To Do

### ❌ Anti-Pattern 1: Logic in Code

```java
// BAD - Feature logic mixed with code
public class PaymentService {
    public void processPayment() {
        if (System.getenv("USE_NEW_LOGIC").equals("true")) {
            // New logic
        } else {
            // Old logic
        }
    }
}

// Problem: Can't toggle without redeployment, mixes concerns
```

### ✅ Correct Approach

```java
// GOOD - Use @ConditionalOnProperty
@Bean
@ConditionalOnProperty(name = "payment.new-logic.enabled", havingValue = "true")
public PaymentProcessor newPaymentProcessor() {
    return new NewPaymentProcessor();
}

@Bean
@ConditionalOnProperty(name = "payment.new-logic.enabled", havingValue = "false", matchIfMissing = true)
public PaymentProcessor legacyPaymentProcessor() {
    return new LegacyPaymentProcessor();
}
```

### ❌ Anti-Pattern 2: Invalid Property Values

```properties
# BAD - Unclear values
feature.enabled=on
security.oauth=yes
validation=1

# Problem: Inconsistent values, easy to mistake
```

### ✅ Correct Approach

```properties
# GOOD - Boolean values
feature.enabled=true
security.oauth.enabled=true
validation.enabled=false
```

---

## Next Steps

1. **Define feature flags** — Which features to toggle?
2. **Add @ConditionalOnProperty** — Condition bean creation
3. **Create profile-specific properties** — Dev/test/prod configs
4. **Test with @TestPropertySource** — Verify toggling works
5. **Document all toggles** — List available features

---

## Quick Reference: Conditional Enablement

```
@ConditionalOnProperty Variations:

1. Exact match required
   @ConditionalOnProperty(name = "feature", havingValue = "true")

2. Default if missing
   @ConditionalOnProperty(name = "feature", havingValue = "true", matchIfMissing = true)

3. Property exists (any value)
   @ConditionalOnProperty(name = "feature")

4. Prefix for cleaner namespace
   @ConditionalOnProperty(prefix = "mca.security", name = "oauth.enabled", havingValue = "true")

Activation:
   application.properties:  feature=true
   Command line:            --feature=true
   Environment variable:    FEATURE=true
   JVM property:           -Dfeature=true
```

**Conditional Enablement provides flexible feature control without code changes.**
