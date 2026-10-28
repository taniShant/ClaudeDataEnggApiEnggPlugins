# EPS Configuration Reference: Complete Property Guide

## Executive Summary

Complete reference of all configuration properties for the MCA2 EPS framework, organized by subsystem. Use this as a lookup table for all configurable aspects of the framework.

---

## Core EPS Framework Properties

### Context System Configuration

```properties
# Context enablement
mca.eps.context.enabled=true

# Context time-to-live (seconds)
# 28800 = 8 hours
mca.eps.context.ttl-seconds=28800

# Context validation
mca.eps.context.validation.enabled=true

# Maximum context size (bytes)
# Prevents memory exhaustion from huge contexts
mca.eps.context.max-size-bytes=1048576

# Context compression (if using remote storage)
mca.eps.context.compression.enabled=false
```

### Filter Chain Configuration

```properties
# Core filters enablement
mca.eps.filter.enabled=true

# Individual filter toggles
mca.eps.filter.correlation-id.enabled=true
mca.eps.filter.exception.enabled=true
mca.eps.filter.disable-session.enabled=true
mca.eps.filter.multiread.enabled=true

# Correlation ID
mca.eps.filter.correlation-id.header-name=Correlation-ID
mca.eps.filter.correlation-id.generate-if-missing=true

# Exception filter
mca.eps.filter.exception.stack-trace-enabled=false
mca.eps.filter.exception.detailed-error-messages=false

# Multi-read request
mca.eps.filter.multiread.max-buffer-size=1048576

# Filter exclusions
mca.eps.filter.excluded-paths[0]=/actuator/**
mca.eps.filter.excluded-paths[1]=/health
mca.eps.filter.excluded-paths[2]=/swagger-ui.html
```

### Response & Exception Handling

```properties
# Response envelope configuration
mca.eps.response.include-null-fields=false
mca.eps.response.include-timestamps=true
mca.eps.response.wrap-errors-in-data=false

# Exception mapping
mca.eps.exception.include-stack-trace=false
mca.eps.exception.include-cause=false
```

---

## Security Configuration

### OAuth2 / JWT Configuration

```properties
# OAuth validation toggle
mca.security.oauth.enabled=false

# JWT configuration
mca.security.oauth.jwt.issuer=https://auth.example.com
mca.security.oauth.jwt.audience=api.example.com
mca.security.oauth.jwt.algorithms=RS256

# Token validation
mca.security.oauth.token.validate-exp=true
mca.security.oauth.token.validate-aud=true
mca.security.oauth.token.validate-iss=true
mca.security.oauth.token.clock-skew-seconds=60

# JWKS endpoint (for public key lookup)
mca.security.oauth.jwks-uri=https://auth.example.com/.well-known/jwks.json
mca.security.oauth.jwks-cache-ttl-seconds=3600

# Token claims
mca.security.oauth.token-claim-user-id=sub
mca.security.oauth.token-claim-scope=scope
```

### DDoS Prevention

```properties
# DDoS prevention toggle
mca.security.ddos.enabled=false

# Rate limiting
mca.security.ddos.requests-per-minute=1000
mca.security.ddos.requests-per-hour=50000

# Block duration (seconds)
mca.security.ddos.block-duration-seconds=60

# Strategy
# Values: default-allow-all, channel-based, ip-based
mca.security.ddos.strategy=channel-based

# Per-channel limits
mca.security.ddos.limits.MOBILE=5000
mca.security.ddos.limits.WEB=3000
```

### Request Validation

```properties
# Request validation toggle
mca.validation.enabled=false

# Validation strategy
# Values: openapi, json-schema, custom
mca.validation.strategy=openapi

# Fail fast vs. collect all errors
mca.validation.fail-fast=false

# Excluded paths (no validation)
mca.validation.excluded-paths[0]=/health
mca.validation.excluded-paths[1]=/metrics
```

### Request Whitelisting

```properties
# Whitelist toggle
mca.security.request-whitelist.enabled=false

# Whitelist mode
# Values: blacklist, whitelist
mca.security.request-whitelist.mode=whitelist

# Whitelisted paths
mca.security.request-whitelist.paths[0]=/api/public/**
mca.security.request-whitelist.paths[1]=/api/cards/**

# Blacklisted paths
mca.security.request-whitelist.blacklist[0]=/api/admin/**
mca.security.request-whitelist.blacklist[1]=/api/internal/**
```

---

## Data Masking Configuration

```properties
# Masking toggle
mca.masking.enabled=false

# Masking strategy
# Values: string-masker, json-string-masker
mca.masking.strategy=json-string-masker

# CRLF injection prevention
mca.masking.crlf-injection.enabled=true
mca.masking.crlf-injection.replacement=_

# Masking patterns (regex with replacement)
mca.masking.patterns.credit-card=^([0-9]{4}).*([0-9]{4})$
mca.masking.patterns.credit-card-replacement=$1****$2

mca.masking.patterns.email=^(.{2})(.*)(@.*)$
mca.masking.patterns.email-replacement=$1****$3

mca.masking.patterns.phone=^(\\d{3})(\\d{3})(\\d{4})$
mca.masking.patterns.phone-replacement=$1-***-$3

mca.masking.patterns.account=^(.{4})(.*)$
mca.masking.patterns.account-replacement=$1****

# Custom patterns
mca.masking.patterns.ssn=^(\\d{3})-(\\d{2})(\\d{4})$
mca.masking.patterns.ssn-replacement=$1-**-$3
```

---

## Logging Configuration

### Core Logging

```properties
# Root log level
logging.level.root=INFO

# MCA libraries
logging.level.com.barclays.global.mca=DEBUG
logging.level.com.barclays.global.mca.libs.eps=INFO
logging.level.com.barclays.global.mca.libs.context=DEBUG
logging.level.com.barclays.global.mca.libs.filters=DEBUG

# Spring framework (usually quieter)
logging.level.org.springframework=WARN
logging.level.org.springframework.web=DEBUG
logging.level.org.springframework.security=INFO

# Third-party libraries
logging.level.com.mongodb=WARN
logging.level.org.hibernate=WARN
```

### Logging Backend Selection

```properties
# Log4j 2
logging.config=classpath:log4j2.xml

# Logback (Spring Boot default)
# logging.config=classpath:logback.xml

# JSON logging (if using JSON variants)
# logging.config=classpath:log4j2-json.xml
```

### Async Logging

```properties
# Enable async logging (improves performance)
mca.logging.async.enabled=true

# Queue size for async appender
mca.logging.async.queue-size=10000

# Discard policy when queue full
# Values: block, discard-oldest, discard-all
mca.logging.async.discard-policy=discard-oldest
```

### Performance Logging

```properties
# Performance logging toggle
mca.logging.performance.enabled=true

# Threshold for logging slow operations (milliseconds)
mca.logging.performance.threshold-ms=1000

# Log level for slow operations
# Values: INFO, WARN, ERROR
mca.logging.performance.log-level=WARN

# Excluded packages (don't log performance)
mca.logging.performance.excluded-packages[0]=org.springframework
mca.logging.performance.excluded-packages[1]=com.mongodb
```

### Dynamic Logging

```properties
# Dynamic log level toggle
mca.logging.dynamic-level.enabled=false

# Allow header-based log level adjustment
mca.logging.dynamic-level.header-name=X-Log-Level
mca.logging.dynamic-level.header-package=X-Log-Package

# Default duration for dynamic level change (seconds)
mca.logging.dynamic-level.duration-seconds=300
```

---

> **Note:** Context storage backends (mca-context-store-rdb, mca-context-store-mongo, mca-context-store-ehcache) are part of the Secure Proxy module, not the core EPS framework. See the Secure Proxy documentation for context store backend selection and configuration properties.

---

## OAS Validation Configuration

The OAS (OpenAPI Specification) validation system validates incoming HTTP requests against an OpenAPI spec file. It uses the Atlassian `swagger-request-validator-spring-webmvc` library and is provided by the `mca-libraries/oas-validation` module. The validation filter runs at filter order 300.

### Enabling OAS Validation

Set `core.default.oas.enabled` to `true` and provide the path to your OpenAPI specification file. When disabled, an `EmptyOasProvider` (no-op) is used and no validation occurs.

### All Properties

```properties
# Enable or disable OAS validation (default: false)
core.default.oas.enabled=false

# Spring Resource path to the OpenAPI YAML or JSON specification
# Supports classpath:, file:, and URL resource locations
core.default.oas.path=classpath:oas/openapi.yaml

# OAS version identifier
core.default.oas.version=1.0.0

# Ignore requests to paths not defined in the OAS (default: false)
# true: allow requests to undefined paths without validation errors
# false: produce a validation error for undefined paths
core.default.oas.ignore-missing-schema=false

# Blocking mode toggle (default: false)
# false: reporting-only mode -- validation errors are logged but requests are not rejected
# true: blocking mode -- requests that fail validation are rejected with an error response
core.default.oas.blockingMode=false

# HTTP headers to exclude from OAS validation (comma-separated)
# Useful for internal/infrastructure headers not in the OpenAPI spec
core.default.oas.excludedHeaders=X-Internal-Header

# Always validate every request regardless of other conditions (default: false)
core.default.oas.alwaysValidate=false

# Ant-style path patterns to exclude from the validation filter (comma-separated)
# Default: /actuator/**,/process/**
core.default.validation-filter.exclude.paths=/actuator/**,/process/**
```

### Blocking Mode vs Reporting-Only Mode

| Mode | Property Value | Behavior |
|------|---------------|----------|
| **Reporting-only** | `core.default.oas.blockingMode=false` | Validation errors are logged but requests proceed normally. Use this in development to observe violations without blocking work. |
| **Blocking** | `core.default.oas.blockingMode=true` | Requests that fail validation are rejected with an error response. Use this in staging and production to enforce API contract compliance. |

### Excluded Headers

Headers listed in `core.default.oas.excludedHeaders` are stripped from the validation check. This is useful for internal or infrastructure headers (such as tracing or routing headers) that are not defined in the OpenAPI specification and would otherwise cause spurious validation failures.

### Example: application.properties

```properties
##################################
# OAS Validation
##################################
core.default.oas.enabled=true
core.default.oas.blockingMode=true
core.default.oas.path=classpath:oas/openapi.yaml
core.default.oas.version=1.0.0
core.default.oas.ignore-missing-schema=false
core.default.oas.excludedHeaders=X-Internal-Header,X-Trace-Id
core.default.oas.alwaysValidate=false
core.default.validation-filter.exclude.paths=/actuator/**,/process/**
```

### Example: application.yml

```yaml
core:
  default:
    oas:
      enabled: true
      blockingMode: true
      path: classpath:oas/openapi.yaml
      version: 1.0.0
      ignore-missing-schema: false
      excludedHeaders: X-Internal-Header,X-Trace-Id
      alwaysValidate: false
    validation-filter:
      exclude:
        paths: /actuator/**,/process/**
```

### Environment-Specific Recommendations

| Environment | `enabled` | `blockingMode` | Rationale |
|-------------|-----------|----------------|-----------|
| **Development** | `true` | `false` | Observe spec violations in logs without disrupting developer workflow |
| **Staging** | `true` | `true` | Enforce API contract compliance before production |
| **Production** | `true` | `true` | Full enforcement; reject non-compliant requests |

---

## Property Placeholder Resolution

```properties
# Placeholder resolver chain
mca.placeholder.chain.order[0]=jceks
mca.placeholder.chain.order[1]=vault
mca.placeholder.chain.order[2]=standard

# JCEKS keystore
mca.placeholder.jceks.enabled=false
mca.placeholder.jceks.keystore-path=${KEYSTORE_PATH}
mca.placeholder.jceks.keystore-password=${KEYSTORE_PASSWORD}

# HashiCorp Vault
mca.placeholder.vault.enabled=false
mca.placeholder.vault.uri=https://vault.example.com:8200
mca.placeholder.vault.token=${VAULT_TOKEN}
mca.placeholder.vault.path=secret/data/mca
mca.placeholder.vault.namespace=admin
```

---

## Service Client Configuration

```properties
# Service client
rest-client.connection-timeout=5000
rest-client.read-timeout=10000
rest-client.max-retries=3
rest-client.retry-delay-ms=1000

# Per-service configuration
rest-client.services.mission-service.url=http://mission-service:8080
rest-client.services.mission-service.timeout=5000
rest-client.services.mission-service.max-retries=3

rest-client.services.user-service.url=http://user-service:8080
rest-client.services.user-service.timeout=10000
```

---

## Filter Ordering Reference

```properties
# Filter execution order
mca.eps.filter.order.correlation-id=0
mca.eps.filter.order.exception=1
mca.eps.filter.order.disable-session=2
mca.eps.filter.order.multiread=3
mca.eps.filter.order.oauth-validator=4
mca.eps.filter.order.ddos=5
mca.eps.filter.order.validation=6
mca.eps.filter.order.request-whitelist=7
mca.eps.filter.order.dynamic-logging=8
mca.eps.filter.order.perf-log-exclusion=9
mca.eps.filter.order.custom-filter=10
```

---

## Complete application.properties Example

```properties
##################################
# Spring Boot Core
##################################
spring.application.name=card-control-api
server.port=8080
spring.profiles.active=prod

##################################
# EPS Framework
##################################
mca.eps.enabled=true
mca.eps.context.enabled=true
mca.eps.context.ttl-seconds=28800

##################################
# Filter Chain
##################################
mca.eps.filter.enabled=true
mca.eps.filter.correlation-id.enabled=true
mca.eps.filter.exception.enabled=true
mca.eps.filter.disable-session.enabled=true
mca.eps.filter.multiread.enabled=true
mca.eps.filter.excluded-paths[0]=/actuator/**
mca.eps.filter.excluded-paths[1]=/health

##################################
# Security
##################################
mca.security.oauth.enabled=true
mca.security.oauth.jwt.issuer=https://auth.example.com
mca.security.oauth.jwt.audience=api.example.com
mca.security.ddos.enabled=true
mca.security.ddos.requests-per-minute=5000

##################################
# Validation
##################################
mca.validation.enabled=true
mca.validation.strategy=openapi

##################################
# Masking
##################################
mca.masking.enabled=true
mca.masking.patterns.credit-card=^([0-9]{4}).*([0-9]{4})$
mca.masking.patterns.credit-card-replacement=$1****$2
mca.masking.patterns.email=^(.{2})(.*)(@.*)$
mca.masking.patterns.email-replacement=$1****$3

##################################
# Logging
##################################
logging.level.root=INFO
logging.level.com.barclays.global.mca=INFO
logging.level.org.springframework.web=WARN
logging.config=classpath:log4j2-prod.xml

##################################
# Performance
##################################
mca.logging.performance.enabled=true
mca.logging.performance.threshold-ms=1000

##################################
# Service Clients
##################################
rest-client.connection-timeout=5000
rest-client.read-timeout=10000
rest-client.services.mission-service.url=http://mission-service:8080
```

---

## Environment Variables & Externalization

### Using Environment Variables

```bash
# Pass as environment variables
export DB_USERNAME=dbuser
export DB_PASSWORD=dbpass
export SPRING_PROFILES_ACTIVE=prod
export VAULT_TOKEN=s.abcdefgh12345

# Or in docker-compose.yml
environment:
  - DB_USERNAME=dbuser
  - DB_PASSWORD=dbpass
  - SPRING_PROFILES_ACTIVE=prod
```

### Using System Properties

```bash
# Pass as JVM properties
java -jar app.jar \
  -Dspring.datasource.url=jdbc:postgresql://db:5432/iol_contexts \
  -Dspring.profiles.active=prod \
  -Dmca.security.oauth.enabled=true
```

### Using application-<profile>.properties

```
application.properties          (default)
application-dev.properties      (dev profile)
application-test.properties     (test profile)
application-prod.properties     (prod profile)
```

---

## Configuration Precedence (Highest to Lowest)

1. Command line arguments (`--key=value`)
2. System properties (`-Dkey=value`)
3. Environment variables (uppercase, underscore-separated)
4. application-<profile>.properties (profile-specific)
5. application.properties (default)
6. Hardcoded defaults in @ConfigurationProperties

---

## Next Steps

1. **Copy template** — Start with Complete application.properties Example
2. **Customize for environment** — Dev/test/prod
3. **Use externalization** — Environment variables for secrets
4. **Validate configuration** — Spring Boot starts and validates all properties
5. **Reference this guide** — When adding new feature toggles

---

## Quick Reference: Most Important Properties

```properties
# Application
spring.application.name=card-control-api
spring.profiles.active=prod

# Core EPS
mca.eps.enabled=true

# Security
mca.security.oauth.enabled=true
mca.security.oauth.jwt.issuer=https://auth.example.com

# Logging
logging.level.com.barclays.global.mca=INFO
logging.config=classpath:log4j2-prod.xml

# Masking
mca.masking.enabled=true
mca.masking.patterns.credit-card=^([0-9]{4}).*([0-9]{4})$
```

**Configuration Reference provides complete property lookup for all EPS framework aspects.**
