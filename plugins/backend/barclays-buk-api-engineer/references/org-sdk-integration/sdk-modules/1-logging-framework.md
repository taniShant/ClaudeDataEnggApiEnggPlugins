# API SDK Module 1: Logging Framework

## Overview

Provides comprehensive logging implementation for APIs with filters for default behavior. This module can be used independently without relying on other SDK modules.

**Gradle Dependency:**
```gradle
com.barclays.api:bap-bld-lib-logging:{version}
```

If using the prescriptive framework (`bap-bld-lib-restapi`), this dependency is already included.

---

## Key Features

### Loggers
- **Root Logger** — logs all application messages (default level: ERROR)
- **Perf Logger** — logs performance events
- **Event Logger** — logs application events
- **ECrime Logger** — logs ECrime events

### Appenders
- **App Log Appender** → `co-app.log`
- **Perf Log Appender** → `co-perf.log`
- **Event Log Appender** → `co-event.log`
- **ECrime Log Appender** → `co-ECrime.log`
- **Console Appender** (not enabled by default)

### Logging Pattern
```
[%d{yyyy-MM-dd HH:mm:ss.SSS}] [${hostName}] [%level] [%c][%X] - %msg%n
```

---

## Filters (Registered by SDK RestAPI module)

1. **InternalApiLoggingContextFilter** — adds `correlation-id` header to logging context
2. **LoggingContextFilter** — sets logging context properties
3. **PerformanceLoggingFilter** — logs request processing performance
4. **RequestResponseLoggingFilter** — logs incoming requests and outgoing responses

---

## Integration Points in Spring Boot Project

### 1. Configuration

Add logging configuration in `application.yml`:

```yaml
logging:
  level:
    root: ERROR  # Override default level
    org.springframework.web: DEBUG  # Specific package logging
  path: /home/user/logs  # Override log file location
```

### 2. MDC (Mapped Diagnostic Context)

Set custom MDC values in application code:

```java
org.slf4j.MDC.put("myKey", "myValue");
```

The logging pattern `[%X]` prints all MDC values.

### 3. Secure Logging Configuration

Create a `@Configuration` bean to mask sensitive fields:

```java
@Configuration
public class MyConfigurator {
    @Bean
    public SecureFields getSecureFields() {
        SecureFields secureFields = new SecureFields();
        secureFields.addMaskSecureField("data", "*");
        secureFields.addNoLogSecureField("dob");
        secureFields.addObfuscateSecureField("name", "*", "[a-z]{2}");
        return secureFields;
    }
}
```

**Note:** `Authorization` header is masked by default.

### 4. Code Generation Template

**LoggingConfiguration.java**
```java
package {base-package}.config;

import com.barclays.api.web.beans.SecureFields;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class LoggingConfiguration {
    
    @Bean
    public SecureFields getSecureFields() {
        SecureFields secureFields = new SecureFields();
        // Add secure field configurations based on spec
        return secureFields;
    }
}
```

### 5. Usage in Controllers/Services

Inject SLF4J Logger:

```java
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@RestController
public class MyController {
    private static final Logger logger = LoggerFactory.getLogger(MyController.class);
    
    @GetMapping("/endpoint")
    public Response getEndpoint() {
        logger.info("Processing endpoint request");
        // ... business logic
        logger.error("Error occurred", exception);
    }
}
```

---

## Performance Logging

Automatically logs request/response timing via `PerformanceLoggingFilter`:

```
[2024-05-07 22:40:53.623] [BDSPUKL20871867] [INFO] [PERF.com.barclays.api.bap.bld.lib.logging.filters.PerformanceLoggingFilter] [{Correlation-ID=Test}]- ac3c0df327b54e329c40411480993d78 S GET /users
[2024-05-07 22:40:54.208] [BDSPUKL20871867] [INFO] [PERF.com.barclays.api.bap.bld.lib.logging.filters.PerformanceLoggingFilter] [{Correlation-ID=Test}]- ac3c0df327b54e329c40411480993d78 E GET /users
```

- `S` = Start, `E` = End
- Unique ID links request and response logs

---

## Custom log4j2.xml

Teams can customize `log4j2.xml` if they don't want the default provided by the SDK.

Place in `src/main/resources/log4j2.xml`.

---

## Integration Checklist

- [ ] `com.barclays.api:bap-bld-lib-logging` dependency added (or included via restapi)
- [ ] Logging levels configured in `application.yml`
- [ ] Sensitive fields configured via `SecureFields` bean if needed
- [ ] Logger instances created in controllers/services using `LoggerFactory`
- [ ] Custom `log4j2.xml` provided if required (optional)
- [ ] Correlation-ID logging verified in logs
