# Configuration Best Practices: Production Deployment

## Executive Summary

Guidelines for configuring MCA2 EPS applications in development, staging, and production environments. Covers property management, secrets handling, profile-specific configs, and environment-specific tuning.

---

## Configuration Hierarchy

### Property Resolution Order (Highest to Lowest Priority)

```
1. System Properties      (java -Dproperty=value)
   └─ Command-line override

2. Environment Variables  (export PROPERTY=value)
   └─ Deployment-time override

3. application.properties  (profile-specific)
   ├─ application-prod.properties
   ├─ application-staging.properties
   └─ application-dev.properties

4. application.properties  (base)
   └─ Default values

5. Spring Boot Defaults
   └─ Framework defaults
```

### Implementation Example

```properties
# application.properties (base - development defaults)
spring.application.name=order-service
server.port=8080
mca.eps.enabled=true

# application-dev.properties (development profile)
server.port=8080
logging.level.com.barclays.global.mca=DEBUG
mca.service.client.enabled=false

# application-staging.properties (staging profile)
server.port=8080
logging.level.com.barclays.global.mca=INFO
mca.service.client.enabled=true
spring.datasource.hikari.maximum-pool-size=10

# application-prod.properties (production profile)
server.port=8080
logging.level.com.barclays.global.mca=WARN
mca.service.client.enabled=true
spring.datasource.hikari.maximum-pool-size=25
```

---

## Configuration Patterns

### Pattern 1: Environment-Specific Application Properties

**Structure:**
```
src/main/resources/
├─ application.properties          (base defaults)
├─ application-dev.properties      (development)
├─ application-staging.properties  (staging)
├─ application-prod.properties     (production)
└─ application-local.properties    (developer machine)
```

**Activation:**
```bash
# Development (local machine)
java -Dspring.profiles.active=dev -jar app.jar

# Staging
java -Dspring.profiles.active=staging -jar app.jar

# Production
java -Dspring.profiles.active=prod -jar app.jar

# Multiple profiles (if needed)
java -Dspring.profiles.active=prod,metrics -jar app.jar
```

**Benefits:**
- ✅ Clear separation of environment configs
- ✅ Easy to review production settings
- ✅ Prevents accidental use of dev defaults in production
- ✅ IDE autocomplete support

### Pattern 2: Secrets Management (JCEKS Keystores)

**Setup:**
```bash
# Create JCEKS keystore with encrypted secrets
keytool -genseckey -v \
  -keystore secrets.jceks \
  -storetype JCEKS \
  -storepass keystorepass \
  -keyalg AES \
  -keysize 256 \
  -alias database.password \
  -keypass keypass \
  -validity 365
```

**Application Configuration:**
```properties
# application-prod.properties
spring.datasource.password={JCEKS}secrets.jceks:database.password:keystorepass

# Alternatively, use environment variable
spring.datasource.password=${DB_PASSWORD}
```

**Benefits:**
- ✅ Secrets never stored in plain text
- ✅ Keystore can be restricted to specific server
- ✅ Easy rotation of credentials

### Pattern 3: Environment Variables for Secrets

**Production Deployment:**
```bash
#!/bin/bash
# Deploy script

export SPRING_DATASOURCE_PASSWORD=${DB_PASSWORD}
export SPRING_DATASOURCE_USERNAME=${DB_USER}
export SPRING_REDIS_PASSWORD=${REDIS_PASSWORD}
export MCA_OAUTH_CLIENT_SECRET=${OAUTH_SECRET}

java -Dspring.profiles.active=prod \
  -jar order-service.jar
```

**Benefits:**
- ✅ Secrets never in code or properties files
- ✅ Managed by deployment system (Kubernetes secrets, Vault, etc.)
- ✅ Easy audit trail of who has access

---

## EPS-Specific Configuration

### Core EPS Properties

```properties
# ===== CORE EPS CONFIGURATION =====
mca.eps.enabled=true

# ===== FILTER CHAIN =====
mca.filter.correlation-id.enabled=true
mca.filter.exception.enabled=true
mca.filter.disable-session.enabled=true
mca.filter.multiread-request.enabled=true

# Optional filters
mca.filter.oauth-validator.enabled=true
mca.filter.ddos-prevention.enabled=false    # Enable only in high-traffic envs
core.default.oas.enabled=false
mca.filter.request-whitelisting.enabled=false

# Filter behavior
mca.filter.exception.detailed-error-messages=false  # Never true in prod!
mca.filter.correlation-id.header=Correlation-ID
mca.filter.context.header-prefix=X-

# ===== DATA MASKING =====
mca.masking.enabled=true
masking.patterns.credit-card=\d{4}(?:\d(?=.\d{3}))
masking.patterns.email=(?<=.{1}).(?=[^@]*@)
masking.patterns.phone=(?<=.{1}).(?=[^-]*-[^-]*$)
masking.patterns.ssn=(?<=.{2}).(?=[^-]*-[^-]*$)

# ===== LOGGING CONFIGURATION =====
logging.level.root=WARN
logging.level.com.barclays.global.mca=INFO
logging.level.com.barclays.global.mca.libs.filter=DEBUG

# Correlation ID in logs
logging.pattern.console=%d{ISO8601} [%X{correlationId}] %5p %logger{36} - %msg%n
logging.pattern.file=%d{ISO8601} [%X{correlationId}] %5p %logger{36} - %msg%n
```

### Profile-Specific EPS Configuration

**development:**
```properties
# application-dev.properties
mca.filter.exception.detailed-error-messages=true
logging.level.com.barclays.global.mca=DEBUG
mca.masking.enabled=false               # See unmasked data for debugging
mca.filter.ddos-prevention.enabled=false
```

**staging:**
```properties
# application-staging.properties
mca.filter.exception.detailed-error-messages=true  # For testing
logging.level.com.barclays.global.mca=INFO
mca.masking.enabled=true
mca.filter.ddos-prevention.enabled=true  # Test DDoS protection
```

**production:**
```properties
# application-prod.properties
mca.filter.exception.detailed-error-messages=false  # Hide internals
logging.level.com.barclays.global.mca=WARN
mca.masking.enabled=true                # Always mask in production
mca.filter.ddos-prevention.enabled=true
mca.filter.request-whitelisting.enabled=true
```

---

> **Note:** Context store backend selection (RDB, MongoDB, EHCache) is part of the **Secure Proxy** module, not EPS. If your application uses Secure Proxy for session management, refer to the Secure Proxy documentation for context store configuration.

---

## Logging Configuration

### Production Logging Setup

```properties
# application-prod.properties
logging.config=classpath:logback-spring.xml

# Log levels
logging.level.root=WARN
logging.level.com.barclays.global.mca=INFO
logging.level.com.barclays.global.mca.libs.filter=DEBUG
logging.level.org.springframework.web=WARN
logging.level.org.springframework.security=WARN
logging.level.org.springframework.data=WARN

# Async logging for performance
logging.async.queue-size=512
logging.async.shutdown-wait-time=10000

# File output
logging.file.name=/var/log/order-service/application.log
logging.file.max-size=100MB
logging.file.max-history=14
```

**logback-spring.xml (Production):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <springProperty name="LOG_FILE" source="logging.file.name" defaultValue="/tmp/spring.log"/>

  <!-- Async appender for performance -->
  <appender name="ASYNC_FILE" class="ch.qos.logback.classic.AsyncAppender">
    <queueSize>512</queueSize>
    <discardingThreshold>0</discardingThreshold>

    <appender-ref ref="FILE"/>
  </appender>

  <!-- File appender with rolling policy -->
  <appender name="FILE" class="ch.qos.logback.core.rolling.RollingFileAppender">
    <file>${LOG_FILE}</file>

    <encoder>
      <pattern>%d{ISO8601} [%X{correlationId}] %5p %logger{36} - %msg%n</pattern>
    </encoder>

    <rollingPolicy class="ch.qos.logback.core.rolling.SizeAndTimeBasedRollingPolicy">
      <fileNamePattern>${LOG_FILE}.%d{yyyy-MM-dd}.%i.gz</fileNamePattern>
      <maxFileSize>100MB</maxFileSize>
      <maxHistory>14</maxHistory>
      <totalSizeCap>2GB</totalSizeCap>
    </rollingPolicy>
  </appender>

  <root level="WARN">
    <appender-ref ref="ASYNC_FILE"/>
  </root>
</configuration>
```

---

---

## Security Configuration

### Production Security Best Practices

```properties
# application-prod.properties

# HTTP Security
server.ssl.enabled=true
server.ssl.key-store=classpath:keystore.jks
server.ssl.key-store-password=${KEYSTORE_PASSWORD}
server.ssl.key-store-type=JKS

# Security headers
server.compression.enabled=true
server.servlet.session.cookie.secure=true
server.servlet.session.cookie.http-only=true
server.servlet.session.cookie.same-site=strict

# CORS (if needed)
spring.web.cors.allowed-origins=https://api.example.com
spring.web.cors.allowed-methods=GET,POST,PUT,DELETE
spring.web.cors.allow-credentials=true

# OAuth Configuration
mca.security.oauth.enabled=true
mca.security.oauth.provider-url=https://auth.example.com
mca.security.oauth.client-id=${OAUTH_CLIENT_ID}
mca.security.oauth.client-secret=${OAUTH_CLIENT_SECRET}
mca.security.oauth.scope=profile,email
```

---

## Monitoring & Observability

### Metrics Configuration

```properties
# application-prod.properties
management.endpoints.web.exposure.include=health,metrics,prometheus
management.endpoint.health.show-details=when-authorized
management.metrics.enabled=true

# Export to Prometheus
management.metrics.export.prometheus.enabled=true
```

### Health Check Configuration

```java
// CustomHealthIndicator.java
@Component
public class DatabaseHealthIndicator implements HealthIndicator {

  @Autowired
  private DataSource dataSource;

  @Override
  public Health health() {
    try {
      dataSource.getConnection().isValid(5);
      return Health.up().build();
    } catch (Exception e) {
      return Health.down()
        .withDetail("error", e.getMessage())
        .build();
    }
  }
}
```

---

## Configuration Validation Checklist

### Before Deploying to Production

```
✓ Database connectivity verified
✓ Connection pooling configured
✓ SSL certificates valid
✓ Secrets are NOT in properties files
✓ Logging levels appropriate
✓ Masking patterns configured
✓ Security filters enabled
✓ DDoS prevention configured (if high-traffic)
✓ Health checks working
✓ Metrics endpoint accessible
✓ No debug logging in production
✓ Correlation IDs in all logs
✓ Exception details not exposed
✓ All optional features documented
```

---

## Next Steps

1. **Create Profiles** — Set up dev, staging, prod configurations
3. **Secure Secrets** — Move sensitive data to environment variables
4. **Test Locally** — Verify configuration loading with profiles
5. **Deploy & Monitor** — Validate production configuration in staging

**Configuration Best Practices enable reliable production deployments.**

