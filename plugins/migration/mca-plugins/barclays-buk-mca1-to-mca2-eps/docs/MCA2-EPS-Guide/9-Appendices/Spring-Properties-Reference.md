# Spring Properties Reference: Configuration Catalog

## Executive Summary

Complete reference for 100+ MCA2 EPS configuration properties across development, staging, and production environments. Use this when configuring applications.

---

## Property Organization

### Categories

```
mca.eps.* - Core EPS framework
mca.filter.* - Filter chain configuration
mca.service.client.* - Service client configuration
mca.proxy.* - Secure proxy settings
mca.masking.* - Data masking patterns
mca.security.* - Security configuration
spring.datasource.* - Database configuration
logging.* - Logging configuration
```

---

## CORE EPS PROPERTIES

### Framework Enablement

```properties
# Framework activation
mca.eps.enabled=true
# Default: true (required for framework)
# Options: true, false
# Purpose: Master switch for entire EPS framework
```

## FILTER CHAIN PROPERTIES

### Core Filters (Always Enabled)

```properties
# Correlation ID Filter (Order 0)
mca.filter.correlation-id.enabled=true
# Default: true (cannot be disabled)
mca.filter.correlation-id.header=Correlation-ID
# Header name for correlation ID
mca.filter.correlation-id.generate-if-missing=true
# Generate UUID if not present in request

# Exception Filter (Order 1)
mca.filter.exception.enabled=true
# Default: true (cannot be disabled)
mca.filter.exception.detailed-error-messages=false
# CRITICAL: Never true in production!
mca.filter.exception.include-stacktrace=false
mca.filter.exception.log-level=ERROR
# ERROR or WARN

# Disable Session Filter (Order 2)
mca.filter.disable-session.enabled=true
# Default: true (cannot be disabled)
mca.filter.disable-session.allow-jsessionid=false
# Prevent JSESSIONID cookie creation

# MultiRead Request Filter (Order 3)
mca.filter.multiread-request.enabled=true
# Default: true (cannot be disabled)
mca.filter.multiread-request.max-size=1MB
# Maximum request body size to buffer
```

### Optional Filters (Conditional)

```properties
# Context Filter (Order 4)
mca.filter.context.enabled=true
# Default: true (recommended)
mca.filter.context.header-prefix=X-
# Prefix for context headers
mca.filter.context.validate-schema=true
# Validate context schema integrity
mca.filter.context.strict-mode=false
# Strict validation (true = fail on errors)

# OAuth Validator Filter (Order 5)
mca.filter.oauth-validator.enabled=false
# Default: false (disabled)
mca.filter.oauth-validator.provider-url=https://auth-provider/oauth2
# OAuth provider URL
mca.filter.oauth-validator.cache-ttl=3600
# Token cache lifetime (seconds)
mca.filter.oauth-validator.scope-required=api
# Required OAuth scope

# DDoS Prevention Filter (Order 6)
mca.filter.ddos-prevention.enabled=false
# Default: false (disabled)
mca.filter.ddos-prevention.requests-per-second=100
# Rate limit threshold
mca.filter.ddos-prevention.window-size=60
# Time window (seconds)
mca.filter.ddos-prevention.block-duration=300
# Block duration (seconds) after limit exceeded
mca.filter.ddos-prevention.redis-enabled=true
# Use Redis for distributed rate limiting
mca.filter.ddos-prevention.whitelist=10.0.0.0/8
# IP whitelist (comma-separated CIDR ranges)

# ValidationFilter (OAS) — For configuration, see the OAS VALIDATION PROPERTIES section below.
# The correct property prefix is core.default.oas.*, not mca.filter.validation.*

# Request Whitelisting Filter (Order 8)
mca.filter.request-whitelisting.enabled=false
# Default: false (disabled)
mca.filter.request-whitelisting.allowed-paths=/api/.*,/health,/metrics
# Regex patterns for allowed paths
mca.filter.request-whitelisting.allowed-methods=GET,POST,PUT,DELETE
# Allowed HTTP methods
```

---

## OAS VALIDATION PROPERTIES

### OpenAPI Specification (OAS) Request Validation

The OAS validation system validates incoming HTTP requests against an OpenAPI specification using the Atlassian `swagger-request-validator-spring-webmvc` library. The validation filter runs at order 300 within the filter chain.

```properties
# OAS Validation Toggle
core.default.oas.enabled=false
# Default: false
# Purpose: Master switch for OAS request validation
# Set to true to activate request validation against the OpenAPI spec

# Path to OpenAPI Specification
core.default.oas.path=classpath:oas/openapi.yaml
# Default: (none, required when enabled)
# Spring Resource path to the OpenAPI YAML or JSON file
# Supports classpath:, file:, and URL resource locations

# OAS Version
core.default.oas.version=1.0.0
# Default: (none)
# Version string for the OpenAPI specification

# Ignore Missing Schema
core.default.oas.ignore-missing-schema=false
# Default: false
# When true, requests to paths not defined in the OAS are allowed through
# When false, requests to undefined paths produce a validation error

# Blocking Mode
core.default.oas.blockingMode=false
# Default: false
# false = reporting-only mode (logs validation errors but does not reject requests)
# true = blocking mode (rejects requests that fail validation with an error response)
# RECOMMENDATION: Use false in dev/test for observability; use true in production for enforcement

# Excluded Headers
core.default.oas.excludedHeaders=X-Internal-Header
# Default: (none)
# Comma-separated list of HTTP headers to exclude from OAS validation
# Useful for internal/infrastructure headers not defined in the OpenAPI spec

# Always Validate
core.default.oas.alwaysValidate=false
# Default: false
# When true, validates every request regardless of other conditions
# When false, validation may be skipped based on path exclusions or other criteria

# Validation Filter Path Exclusions
core.default.validation-filter.exclude.paths=/actuator/**,/process/**
# Default: /actuator/**,/process/**
# Comma-separated Ant-style path patterns to exclude from OAS validation
# Requests matching these patterns bypass the validation filter entirely
```

### Environment-Specific Recommendations

```properties
# Development (application-dev.properties)
core.default.oas.enabled=true
core.default.oas.blockingMode=false
# Report-only: log validation errors without blocking requests
# Helps developers see spec violations without disrupting workflow

# Staging (application-staging.properties)
core.default.oas.enabled=true
core.default.oas.blockingMode=true
# Blocking mode: enforce spec compliance before production

# Production (application-prod.properties)
core.default.oas.enabled=true
core.default.oas.blockingMode=true
core.default.oas.ignore-missing-schema=false
# Full enforcement: reject non-compliant requests
```

### Example YAML Configuration

```yaml
core:
  default:
    oas:
      enabled: true
      blockingMode: true
      path: classpath:oas/openapi.yaml
      version: 1.0.0
      ignore-missing-schema: false
      excludedHeaders: X-Internal-Header
      alwaysValidate: false
    validation-filter:
      exclude:
        paths: /actuator/**,/process/**
```

---

## PROCESS SYSTEM PROPERTIES

> **Note:** These are Secure Proxy properties that configure the process bootstrap, chaining, and routing endpoints used by the MCA process system. They define the URL mappings for process lifecycle operations and the default IOL contexts propagated during process execution.

```properties
# Process Bootstrap Endpoint
secure-proxy.default.urlmappings.bootstrap=/launchProcess
# URL mapping for launching a new process instance
# The client POSTs to this endpoint with a launchId to start a journey

# Process Chaining Endpoint
secure-proxy.default.urlmappings.chaining=/chainProcess
# URL mapping for chaining from one process to another (parent-child)
# Used when a journey needs to invoke a sub-process

# Router Endpoint
secure-proxy.default.urlmappings.router=/router/*
# URL mapping for the secure proxy router
# All process endpoint requests are routed through this path

# Default IOL Contexts
secure-proxy.default.contexts=SystemContext,UserContext,CallerContext,LocaleContext,AID,Correlation-ID
# Comma-separated list of IOL context types propagated by default during process execution
# These contexts are automatically included in requests to backend endpoints defined in process.json
```

### Process System Configuration Notes

- The `bootstrap` mapping is the entry point for all MCA journeys. A client sends a `launchId` to this endpoint, and `BootstrapService` resolves it to a process.json definition via `ProcessDiscovery`.
- The `chaining` mapping supports multi-step journeys where one process launches another as a child process.
- The `router` mapping handles all subsequent endpoint calls defined in the process.json, routing them to the correct backend services.
- The `contexts` list defines which IOL context types are propagated by default; individual endpoints in process.json can specify additional context requirements.
- Process definition files are loaded from `processes/{processName}_v{versionNumber}.json` on the classpath by `ClasspathResourceProcessService`.

---

## SERVICE CLIENT PROPERTIES

```properties
# Service Client Configuration
mca.service.client.enabled=true
# Default: true (required for service-to-service calls)

mca.service.client.connect-timeout=5000
# Connection timeout (milliseconds)
# Recommended: 5000-10000

mca.service.client.read-timeout=10000
# Read timeout (milliseconds)
# Recommended: 10000-30000

mca.service.client.max-retries=3
# Maximum retry attempts for failed requests

mca.service.client.retry-delay=1000
# Initial retry delay (milliseconds)

mca.service.client.backoff-multiplier=2.0
# Exponential backoff multiplier

mca.service.client.max-backoff=30000
# Maximum backoff (milliseconds)

mca.service.client.connection-pool-size=100
# HTTP connection pool size

mca.service.client.max-idle-time=60000
# Connection idle timeout (milliseconds)
```

---

## SECURE PROXY PROPERTIES

> **Note:** Context storage (ContextStore, context-store-rdb, context-store-mongo, context-store-ehcache) is part of the Secure Proxy module, not EPS core. Context store properties (`context.store.*`) should be configured as part of your Secure Proxy setup.

```properties
# Proxy Configuration
mca.proxy.enabled=true
# Enable secure proxy integration

mca.proxy.trusted-headers=X-UserContext,X-CustomerContext,X-Forwarded-For
# Comma-separated list of trusted headers from proxy

mca.proxy.session-store=rdb
# Session storage backend (rdb, mongo, redis)

mca.proxy.session-timeout=3600
# Session timeout (seconds)

mca.proxy.validate-session=true
# Validate session on each request

mca.proxy.forward-headers=true
# Forward authentication headers to downstream services

# Context Store Configuration (Secure Proxy feature)
context.store.type=rdb
# Options: rdb | mongo | ehcache
# rdb: PostgreSQL/Oracle/MySQL (persistent, ACID)
# mongo: MongoDB (scalable, flexible)
# ehcache: In-memory (fast, single instance)

context.store.rdb.datasource=primary-db
context.store.rdb.pool-size=25

context.store.mongo.database=context_db
context.store.mongo.uri=mongodb://localhost:27017

context.store.cache.ttl-minutes=30
context.store.cache.max-entries=100000
```

---

## DATA MASKING PROPERTIES

```properties
# Masking Configuration
mca.masking.enabled=true
# Enable data masking in logs

mca.masking.log-masked-values=false
# Log which values were masked (false for security)

mca.masking.max-mask-length=50
# Maximum masked value length to log

# Masking Patterns (Regex)
masking.patterns.credit-card=\d{4}(?:\d(?=.\d{3}))
# Credit card masking pattern
masking.patterns.email=(?<=.{1}).(?=[^@]*@)
# Email masking pattern
masking.patterns.phone=(?<=.{2}).(?=[^-]*-)
# Phone number masking pattern
masking.patterns.ssn=(?<=.{2}).(?=[^-]*-)
# SSN masking pattern
masking.patterns.account-number=(?<=.{2}).(?=[^-]*$)
# Account number masking pattern
masking.patterns.custom-field=[a-zA-Z0-9]{8,}
# Custom field masking pattern
```

---

## SECURITY PROPERTIES

```properties
# OAuth Configuration
mca.security.oauth.enabled=true
mca.security.oauth.provider-url=https://auth-provider/oauth2
mca.security.oauth.client-id=${OAUTH_CLIENT_ID}
mca.security.oauth.client-secret=${OAUTH_CLIENT_SECRET}
mca.security.oauth.scope=profile,email

# DDoS Prevention
mca.security.ddos.enabled=true
mca.security.ddos.requests-per-minute=6000
mca.security.ddos.block-duration=300

# SSL/TLS
server.ssl.enabled=true
server.ssl.key-store=classpath:keystore.jks
server.ssl.key-store-password=${KEYSTORE_PASSWORD}
server.ssl.key-store-type=JKS
```

---

## LOGGING PROPERTIES

```properties
# Root Logging Level
logging.level.root=WARN
# Options: TRACE, DEBUG, INFO, WARN, ERROR, FATAL

# Framework Logging
logging.level.com.barclays.global.mca=INFO
# MCA2 framework logging level

# Application Logging
logging.level.com.example.app=DEBUG
# Application-specific logging level

# Specific Module Logging
logging.level.com.barclays.global.mca.libs.filter=DEBUG
# Filter chain debugging
logging.level.com.barclays.global.mca.libs.context=INFO
# Context system logging
logging.level.com.barclays.global.mca.libs.security=INFO
# Security logging

# Async Logging
logging.async.queue-size=512
# Async logging queue size
logging.async.shutdown-wait-time=10000
# Shutdown wait time (milliseconds)

# File Logging
logging.file.name=/var/log/app/application.log
# Log file path
logging.file.max-size=100MB
# Maximum file size before rotation
logging.file.max-history=14
# Number of archive files to keep

# Logging Patterns
logging.pattern.console=%d{ISO8601} [%X{correlationId}] %5p %logger{36} - %msg%n
# Console output pattern (includes correlation ID)
logging.pattern.file=%d{ISO8601} [%X{correlationId}] %5p %logger{36} - %msg%n
# File output pattern (includes correlation ID)
```

---

## DATABASE PROPERTIES

```properties
# Database Connection
spring.datasource.url=jdbc:postgresql://localhost:5432/app_db
# JDBC connection URL

spring.datasource.username=postgres
# Database username

spring.datasource.password=password
# Database password (use environment variable in production!)

spring.datasource.driver-class-name=org.postgresql.Driver
# JDBC driver class

# Connection Pool (HikariCP)
spring.datasource.hikari.maximum-pool-size=25
# Maximum connections
# Recommended: (CPU_cores × 2) + 1

spring.datasource.hikari.minimum-idle=5
# Minimum idle connections

spring.datasource.hikari.connection-timeout=30000
# Connection timeout (milliseconds)

spring.datasource.hikari.idle-timeout=600000
# Idle timeout (milliseconds)

spring.datasource.hikari.max-lifetime=1800000
# Maximum connection lifetime (milliseconds)

spring.datasource.hikari.leak-detection-threshold=60000
# Connection leak detection (milliseconds)

# JPA/Hibernate
spring.jpa.hibernate.ddl-auto=validate
# Options: create, create-drop, update, validate, none
# Recommended: validate (never auto-create in production)

spring.jpa.show-sql=false
# Show SQL queries in logs (false for production)

spring.jpa.properties.hibernate.dialect=org.hibernate.dialect.PostgreSQLDialect
# Hibernate SQL dialect

# Flyway Database Migration
spring.flyway.enabled=true
# Enable Flyway migrations

spring.flyway.locations=classpath:db/migration
# Migration scripts location

spring.flyway.baseline-on-migrate=true
# Baseline on first migration
```

---

## MONGODB PROPERTIES

```properties
# MongoDB Connection
spring.data.mongodb.uri=mongodb://user:pass@host:27017/database
# MongoDB connection URI

spring.data.mongodb.database=context_db
# Database name

# MongoDB Auto-Index Creation
spring.data.mongodb.auto-index-creation=true
# Create indexes automatically (set to false in production for manual management)
```

---

## SPRING BOOT PROPERTIES

```properties
# Application Name
spring.application.name=my-app
# Application identifier for logging/monitoring

# Server Configuration
server.port=8080
# HTTP port

server.servlet.context-path=/
# Context path for all endpoints

# Actuator (Health/Metrics)
management.endpoints.web.exposure.include=health,metrics,prometheus
# Exposed actuator endpoints

management.endpoint.health.show-details=when-authorized
# Health endpoint detail level

management.metrics.enabled=true
# Enable metrics collection

management.metrics.export.prometheus.enabled=true
# Prometheus metrics export

# Compression
server.compression.enabled=true
# Compress responses

server.compression.min-response-size=1024
# Minimum size to compress (bytes)

# Session Configuration
server.servlet.session.cookie.secure=true
# Only send session cookie over HTTPS

server.servlet.session.cookie.http-only=true
# Prevent JavaScript access to session cookie

server.servlet.session.cookie.same-site=strict
# Same-site cookie policy
```

---

## MONITORING PROPERTIES

```properties
# Health Checks
management.endpoint.health.enabled=true
management.endpoint.health.show-details=when-authorized
# Show detailed health information

# Metrics
management.metrics.tags.application=${spring.application.name}
management.metrics.tags.environment=${spring.profiles.active}
# Metrics tags for filtering

# Prometheus Export
management.metrics.export.prometheus.enabled=true
management.endpoints.web.exposure.include=prometheus
# Expose Prometheus endpoint
```

---

## ENVIRONMENT-SPECIFIC PROFILES

### Development (application-dev.properties)

```properties
server.port=8080
context.ttl-seconds=600
spring.jpa.show-sql=true
logging.level.root=DEBUG
logging.level.com.barclays.global.mca=DEBUG
mca.filter.exception.detailed-error-messages=true
mca.masking.enabled=false
mca.filter.ddos-prevention.enabled=false
```

### Staging (application-staging.properties)

```properties
server.port=8080
context.ttl-seconds=1800
spring.jpa.show-sql=false
logging.level.root=INFO
logging.level.com.barclays.global.mca=INFO
mca.filter.exception.detailed-error-messages=true
mca.masking.enabled=true
mca.filter.ddos-prevention.enabled=true
```

### Production (application-prod.properties)

```properties
server.port=8080
context.ttl-seconds=3600
spring.jpa.show-sql=false
logging.level.root=WARN
logging.level.com.barclays.global.mca=WARN
mca.filter.exception.detailed-error-messages=false
mca.filter.exception.include-stacktrace=false
mca.masking.enabled=true
mca.filter.ddos-prevention.enabled=true
mca.filter.request-whitelisting.enabled=true
server.ssl.enabled=true
```

---

## Property Override Precedence (Highest to Lowest)

```
1. System Properties (-Dproperty=value)
2. Environment Variables (export PROPERTY=value)
3. application-{profile}.properties (e.g., application-prod.properties)
4. application.properties (default)
5. Spring Boot Defaults
```

---

## Using Environment Variables

```bash
# Set in shell
export SPRING_DATASOURCE_PASSWORD=secretpassword
export MCA_MASKING_ENABLED=true
export LOGGING_LEVEL_COM_BARCLAYS_GLOBAL_MCA=DEBUG

# Or in .env file
SPRING_DATASOURCE_USERNAME=postgres
SPRING_DATASOURCE_PASSWORD=${DB_PASSWORD}
SPRING_DATASOURCE_URL=jdbc:postgresql://${DB_HOST}:5432/${DB_NAME}
```

### Property Conversion Examples

```
application.properties → Environment Variable
─────────────────────────────────────────────
spring.datasource.url → SPRING_DATASOURCE_URL
mca.filter.ddos-prevention.enabled → MCA_FILTER_DDOS-PREVENTION_ENABLED
logging.level.root → LOGGING_LEVEL_ROOT
```

---

## Configuration Validation Checklist

```
✓ mca.eps.enabled=true (REQUIRED)
✓ spring.datasource credentials configured
✓ logging.level appropriate for environment
✓ mca.filter.exception.detailed-error-messages=false in production
✓ mca.masking.enabled=true for sensitive data
✓ mca.filter.ddos-prevention.enabled=true in production
✓ SSL/TLS configured for production
✓ No secrets in application.properties files
✓ Correlation ID in logging pattern
```

---

## Common Configuration Errors

### Error 1: Connection Pool Exhausted

```
Exception: Cannot get a connection, pool error
Solution: Increase connection pool:
  spring.datasource.hikari.maximum-pool-size=50
```

### Error 2: Context Not Available in Controller

```
@IOLContext CustomerContext context shows null
Solution: Verify:
  mca.filter.context.enabled=true
  X-CustomerContext header present in request
  @IOLContext annotation used in controller
```

### Error 3: Detailed Error Messages in Production

```
Security Issue: Stack traces exposed in responses
Solution: Set in application-prod.properties:
  mca.filter.exception.detailed-error-messages=false
  mca.filter.exception.include-stacktrace=false
```

---

## Quick Reference: Essential Properties

```properties
# MINIMUM REQUIRED
mca.eps.enabled=true
spring.datasource.url=jdbc:postgresql://localhost:5432/db
spring.datasource.username=postgres
spring.datasource.password=password

# RECOMMENDED
logging.pattern.console=%d{ISO8601} [%X{correlationId}] %5p %msg%n
mca.masking.enabled=true
logging.level.com.barclays.global.mca=INFO

# PRODUCTION
mca.filter.exception.detailed-error-messages=false
mca.filter.ddos-prevention.enabled=true
mca.filter.request-whitelisting.enabled=true
spring.datasource.hikari.maximum-pool-size=25
logging.file.name=/var/log/app/application.log
```

**Spring Properties Reference provides authoritative configuration guide.**

