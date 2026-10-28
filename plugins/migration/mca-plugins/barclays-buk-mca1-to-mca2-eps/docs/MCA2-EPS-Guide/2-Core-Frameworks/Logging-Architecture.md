# Logging Architecture: AspectJ Weaving, Multi-Backend Support, and Masking

## Executive Summary

The **Logging Architecture** implements cross-cutting concern handling via AspectJ compile-time weaving, enabling transparent logging, data masking, and performance monitoring without modifying application code. It supports multiple backends (Log4j, Logback) with JSON output for log aggregation platforms.

**Key Characteristics:**
- **AspectJ compile-time weaving** (not runtime reflection)
- **Zero-code logging** - no logging calls needed in application code
- **Multi-backend support** (Log4j, Logback with JSON variants)
- **Automatic data masking** (credit cards, emails, sensitive data)
- **Performance monitoring** integration
- **Correlation ID propagation** through logs

---

## Logging Stack Architecture

```
┌──────────────────────────────────────────────────┐
│ Application Code (No explicit logging calls)     │
│ public void transferMoney(String cardNumber)     │
│ { ... business logic ... }                       │
└──────────────────┬───────────────────────────────┘
                   │
                   ↓ (Woven at compile time)
┌──────────────────────────────────────────────────┐
│ Weaved Bytecode (with logging aspect)            │
│ • Intercepts method entry/exit                   │
│ • Logs parameters (masked)                       │
│ • Logs return value (masked)                     │
│ • Records execution time                        │
│ • Adds correlation ID                            │
└──────────────────┬───────────────────────────────┘
                   │
                   ↓
┌──────────────────────────────────────────────────┐
│ SLF4J Facade (Logging Abstraction)               │
│ • Logger logger = LoggerFactory.getLogger(...)   │
│ • logger.info(), logger.debug(), etc.           │
└──────────────────┬───────────────────────────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
         ↓                   ↓
┌─────────────────────┐ ┌─────────────────────┐
│ Log4j 2 Backend     │ │ Logback Backend     │
│ ✅ Async logging   │ │ ✅ Async logging    │
│ ✅ Performance     │ │ ✅ Performance      │
│ ✅ JSON output     │ │ ✅ JSON output      │
└─────────────────────┘ └─────────────────────┘
         │                   │
         ↓                   ↓
    ┌────────────────────────────┐
    │ Output Appenders           │
    ├────────────────────────────┤
    │ • Console (stdout)         │
    │ • Rolling File             │
    │ • Syslog                   │
    │ • Kafka                    │
    │ • Network socket           │
    └────────────────────────────┘
         │
         ↓
┌────────────────────────────────┐
│ Log Aggregation Services       │
│ • ELK Stack (Elasticsearch)    │
│ • Splunk                       │
│ • CloudWatch                   │
│ • Stackdriver                  │
└────────────────────────────────┘
```

---

## AspectJ Compile-Time Weaving

### Module: mca-logging-aspects

**Location:** `mca-libraries/logging-aspects/src/main/java/com/barclays/global/mca/aspecting/`

**Purpose:** Intercept SLF4J logging calls at compile time

### Why Compile-Time Weaving?

| Aspect | Compile-Time | Runtime |
|--------|--------------|---------|
| **Performance** | ✅ Zero runtime overhead | ❌ Reflection overhead |
| **Predictability** | ✅ Deterministic | ❌ JIT compilation |
| **Memory** | ✅ No runtime framework | ❌ Loads AspectJ weaver |
| **Debugging** | ✅ Easier stack traces | ❌ Harder to trace |
| **Compatibility** | ✅ Works everywhere | ❌ Some frameworks conflict |
| **Build Time** | ❌ Slightly longer | ✅ No impact |

### Compile-Time Weaving Process

**Step 1: Build-time Configuration (Gradle)**

```gradle
// build.gradle
plugins {
    id 'java'
}

ext {
    aspectjVersion = '1.9.25.1'
}

configurations {
    aspectjWeaver
}

dependencies {
    aspectjWeaver "org.aspectj:aspectjweaver:${aspectjVersion}"

    // Application also needs compile-time weaving compiler
    implementation "org.aspectj:aspectjrt:${aspectjVersion}"
}

// Gradle handles aspectj compilation automatically
// (via aspectj-gradle-plugin or similar)
```

**Step 2: Source Code (No AspectJ code visible)**

```java
// User's service class - looks normal
@Service
public class CardService {
    private static final Logger logger =
        LoggerFactory.getLogger(CardService.class);

    public void lockCard(String cardId) {
        logger.info("Locking card: {}", cardId);
        // ... business logic ...
    }
}
```

**Step 3: Compile-Time Weaving**

```
javac CardService.java
    ↓
CardService.class (normal bytecode)
    ↓
AspectJ Weaver (aspectj-maven-plugin / gradle)
    ↓
CardService.class (enhanced bytecode with aspects woven in)
    ↓
.jar file (packaged)
    ↓
Runtime (uses woven bytecode)
```

**Step 4: Runtime Execution (With Woven Aspects)**

```
CardService.lockCard() called
    ↓
[Woven] Before advice executes
    ├─ Extract parameters: cardId = "CARD123"
    ├─ Mask if sensitive: cardId = "****123"
    ├─ Log: "Entering CardService.lockCard(****123)"
    ├─ Record start time
    └─ Inject correlation ID
    ↓
Original business logic executes
    ↓
[Woven] After advice executes
    ├─ Record end time
    ├─ Calculate duration
    ├─ Log: "Exiting CardService.lockCard() - took 45ms"
    └─ Log result
```

---

## Logging Aspects: Features

### Automatic Logging Interception

```java
// mca-logging-aspects provides these aspects:

@Aspect
public class LoggingAspect {

    // 1. Method entry/exit logging
    @Around("execution(* com.barclays.global.mca..*(..))")
    public Object logMethodCall(ProceedingJoinPoint jp) {
        String methodName = jp.getSignature().getName();
        Object[] args = jp.getArgs();

        // Log entry with masked parameters
        logger.info("Entering: {} with args: {}",
            methodName,
            maskParameters(args));

        try {
            Object result = jp.proceed();

            // Log exit with masked result
            logger.info("Exiting: {} returning: {}",
                methodName,
                maskValue(result));

            return result;
        } catch (Throwable ex) {
            // Log exception
            logger.error("Exception in {}: {}",
                methodName,
                ex.getMessage(),
                ex);
            throw ex;
        }
    }

    // 2. Performance monitoring
    @Around("execution(* com.barclays.global.mca..*(..))")
    public Object measurePerformance(ProceedingJoinPoint jp)
        throws Throwable {

        long startTime = System.nanoTime();
        try {
            return jp.proceed();
        } finally {
            long duration = (System.nanoTime() - startTime) / 1_000_000;
            if (duration > 1000) {  // Log if > 1 second
                logger.warn("Slow method: {} took {}ms",
                    jp.getSignature().getName(),
                    duration);
            }
        }
    }
}
```

### Data Masking Integration

**Connected to mca-masking module:**

```java
// Automatic masking of sensitive values
Object[] args = { "4111111111111111", "user@example.com", "secret123" };

// Masked output
// args: ["****1111", "user@***", "***"]
```

---

## Multi-Backend Support

### Backend Selection

Choose **exactly one** logging backend:

#### **Option 1: Log4j 2 (Async, High Performance)**

**Module:** `mca-logging-config-log4j`

**Advantages:**
- Async logging (doesn't block on I/O)
- High throughput (100k+ events/sec)
- Rich feature set
- Flexible routing

**Gradle:**
```gradle
runtimeOnly 'com.barclays.global.mca:mca-logging-config-log4j'
// NOT: mca-logging-config-logback
```

**Configuration (log4j2.xml):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Configuration packages="org.apache.logging.log4j.core">

    <!-- Appenders -->
    <Appenders>
        <!-- Console output -->
        <Console name="Console" target="SYSTEM_OUT">
            <PatternLayout pattern="%d{ISO8601} [%t] %-5p %c{1} - %m%n"/>
        </Console>

        <!-- Async file appender (better performance) -->
        <RollingFile name="RollingFile"
            fileName="logs/application.log"
            filePattern="logs/application-%d{yyyy-MM-dd}-%i.log.gz"
            immediateFlush="false">
            <PatternLayout pattern="%d{ISO8601} [%t] %-5p %c - %m%n"/>
            <Policies>
                <TimeBasedTriggeringPolicy interval="1" modulate="true"/>
                <SizeBasedTriggeringPolicy size="100MB"/>
            </Policies>
        </RollingFile>
    </Appenders>

    <!-- Loggers -->
    <Loggers>
        <Root level="INFO">
            <AppenderRef ref="Console"/>
            <AppenderRef ref="RollingFile"/>
        </Root>

        <!-- Package-specific levels -->
        <Logger name="com.barclays.global.mca" level="DEBUG"/>
    </Loggers>
</Configuration>
```

#### **Option 2: Logback (Spring Boot Default)**

**Module:** `mca-logging-config-logback`

**Advantages:**
- Spring Boot default
- Well-integrated
- Simpler configuration
- Reasonable performance

**Gradle:**
```gradle
runtimeOnly 'com.barclays.global.mca:mca-logging-config-logback'
// NOT: mca-logging-config-log4j
```

**Configuration (logback.xml):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>

    <!-- Appenders -->
    <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
            <pattern>%d{ISO8601} [%thread] %-5level %logger{36} - %msg%n</pattern>
        </encoder>
    </appender>

    <appender name="FILE" class="ch.qos.logback.core.rolling.RollingFileAppender">
        <file>logs/application.log</file>
        <encoder>
            <pattern>%d{ISO8601} [%thread] %-5level %logger - %msg%n</pattern>
        </encoder>
        <rollingPolicy class="ch.qos.logback.core.rolling.TimeBasedRollingPolicy">
            <fileNamePattern>logs/application-%d{yyyy-MM-dd}-%i.log.gz</fileNamePattern>
            <maxHistory>30</maxHistory>
        </rollingPolicy>
    </appender>

    <!-- Loggers -->
    <root level="INFO">
        <appender-ref ref="CONSOLE"/>
        <appender-ref ref="FILE"/>
    </root>

    <logger name="com.barclays.global.mca" level="DEBUG"/>
</configuration>
```

---

### JSON Logging Backend (For Log Aggregation)

For integration with ELK, Splunk, or other log aggregation platforms:

#### **Option 1: Log4j 2 with JSON Layout**

**Module:** `mca-logging-config-log4j-json`

```xml
<!-- log4j2-json.xml -->
<Configuration packages="org.apache.logging.log4j.core">
    <Appenders>
        <RollingFile name="RollingFile"
            fileName="logs/application.log"
            filePattern="logs/application-%d{yyyy-MM-dd}-%i.log.gz">
            <!-- JSON Layout -->
            <JsonLayout complete="false" compact="true"
                eventEol="true"/>
        </RollingFile>
    </Appenders>

    <Loggers>
        <Root level="INFO">
            <AppenderRef ref="RollingFile"/>
        </Root>
    </Loggers>
</Configuration>
```

**Output (JSON):**
```json
{
  "instant": {
    "epochSecond": 1677408000,
    "nanoOfSecond": 123456789
  },
  "thread": "http-nio-8080-exec-1",
  "level": "INFO",
  "loggerName": "com.barclays.global.mca.CardService",
  "message": "Entering: lockCard with args: [****1111]",
  "threadId": 42,
  "threadPriority": 5
}
```

#### **Option 2: Logback with JSON Encoder**

**Module:** `mca-logging-config-logback-json`

Uses Logstash encoder for JSON formatting:

```xml
<!-- logback-json.xml -->
<configuration>
    <appender name="JSON" class="ch.qos.logback.core.rolling.RollingFileAppender">
        <file>logs/application.log</file>
        <encoder class="net.logstash.logback.encoder.LogstashEncoder"/>
        <rollingPolicy class="ch.qos.logback.core.rolling.TimeBasedRollingPolicy">
            <fileNamePattern>logs/application-%d{yyyy-MM-dd}-%i.log.gz</fileNamePattern>
        </rollingPolicy>
    </appender>

    <root level="INFO">
        <appender-ref ref="JSON"/>
    </root>
</configuration>
```

**Output (JSON):**
```json
{
  "@timestamp": "2025-02-26T12:00:00.123Z",
  "@version": 1,
  "message": "Entering: lockCard with args: [****1111]",
  "logger_name": "com.barclays.global.mca.CardService",
  "thread_name": "http-nio-8080-exec-1",
  "level": "INFO",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## Data Masking: Sensitive Data Protection

### Module: mca-masking

**Location:** `mca-masking/src/main/java/com/barclays/global/mca/masking/`

**Purpose:** Automatically redact sensitive values from logs and responses

### Masking Strategy Pattern

```java
public interface Mask<T> {
    /**
     * Mask sensitive value
     * @param value Value to mask
     * @return Masked value
     */
    T mask(T value);
}

// Implementations
public class StringMasker implements Mask<String> {
    @Override
    public String mask(String value) {
        if (value == null || value.length() < 4) {
            return "****";
        }
        return value.substring(0, 4) + "****";
    }
}

public class JsonStringMasker implements Mask<String> {
    @Override
    public String mask(String jsonValue) {
        // Parse JSON, mask fields, return masked JSON
    }
}
```

### Automatic Masking Patterns

Configured in `application.properties`:

```properties
# Credit card masking (keep last 4 digits)
masking.patterns.credit-card=^([0-9]{4})\\s?[0-9X]{4}\\s?[0-9X]{4}\\s?([0-9]{4})$
masking.pattern.credit-card.replacement=$1****$2

# Email masking
masking.patterns.email=^(.{2})(.*)(@.*)$
masking.pattern.email.replacement=$1****$3

# Phone masking
masking.patterns.phone=^(\\d{3})(\\d{3})(\\d{4})$
masking.pattern.phone.replacement=$1-***-$3

# Account number masking
masking.patterns.account=^(.{4})(.*)$
masking.pattern.account.replacement=$1****

# CRLF injection prevention
masking.crlf-injection.enabled=true
masking.crlf-injection.replacement=_
```

### Masking Annotations

```java
// Method parameter masking
public void transferMoney(
    @Masked String cardNumber,
    @Masked String email
) {
    logger.info("Transfer from {} to {}", cardNumber, email);
    // Output: Transfer from ****1111 to user@***
}

// Field masking in request/response
@Data
public class TransferRequest {
    @Masked
    private String cardNumber;

    @Masked
    private String email;
}
```

### Masking Implementation

```java
// In AspectJ aspect
Object[] args = jp.getArgs();
String[] paramNames = getParameterNames(jp);

for (int i = 0; i < args.length; i++) {
    // Check if parameter has @Masked annotation
    if (hasAnnotation(paramNames[i], Masked.class)) {
        args[i] = maskFactory.mask(args[i]);
    }
}

logger.info("Entering {} with args: {}",
    jp.getSignature().getName(),
    args);
```

---

## Correlation ID Propagation

### ThreadLocal Context Management

```java
// CorrelationIdContext maintains correlation ID in thread-local
public class CorrelationIdContext {

    private static final ThreadLocal<String> HOLDER =
        new ThreadLocal<>();

    public static void set(String correlationId) {
        HOLDER.set(correlationId);
    }

    public static String get() {
        return HOLDER.get();
    }

    public static void clear() {
        HOLDER.remove();
    }
}
```

### Correlation ID in Logs

**MDC (Mapped Diagnostic Context) Integration:**

```java
// Log4j MDC (Mapped Diagnostic Context)
MDC.put("correlationId", CorrelationIdContext.get());

// Configure in log4j2.xml
<PatternLayout pattern="%d %X{correlationId} %m%n"/>

// Output:
// 2025-02-26T12:00:00 550e8400-e29b-41d4-a716-446655440000 Entering: lockCard
```

**Logback integration similar:**

```xml
<configuration>
    <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
            <!-- Include MDC correlation ID -->
            <pattern>%d %X{correlationId} %m%n</pattern>
        </encoder>
    </appender>
</configuration>
```

---

## Performance Monitoring Integration

### Performance Logging via Aspects

```java
// Automatic performance tracking
@Aspect
public class PerformanceAspect {

    @Around("execution(* com.barclays.global.mca..*(..))")
    public Object measureAndLog(ProceedingJoinPoint jp)
        throws Throwable {

        long startTime = System.nanoTime();
        String methodName = jp.getSignature().getName();

        try {
            return jp.proceed();
        } finally {
            long duration = (System.nanoTime() - startTime) / 1_000_000;

            if (duration > 1000) {  // Warn if > 1 second
                logger.warn("PERF: {} took {}ms",
                    methodName,
                    duration);
            } else {
                logger.debug("PERF: {} took {}ms",
                    methodName,
                    duration);
            }
        }
    }
}
```

### Performance Annotation

```java
@PerfLogRecordedOperation
@PerfLogParam(value = "cardId", index = 0)
public void lockCard(String cardId, LockReason reason) {
    // Automatically logs method name, parameters, duration
}
```

---

## Logging Configuration: Reference

### Application Properties

```properties
# Log level configuration
logging.level.root=INFO
logging.level.com.barclays.global.mca=DEBUG
logging.level.org.springframework.web=DEBUG

# Log output
logging.file.name=logs/application.log
logging.file.max-size=10MB
logging.file.max-history=30

# Backend selection (only ONE of these)
# logging.config=classpath:log4j2.xml      # Use Log4j 2
# logging.config=classpath:logback.xml     # Use Logback

# JSON output (if using JSON backend)
logging.structured=true

# Pattern (if not using JSON)
logging.pattern.console=%d{ISO8601} [%thread] %-5level %logger{36} - %msg%n
logging.pattern.file=%d{ISO8601} [%thread] %-5level %logger - %msg%n

# Masking patterns
masking.enabled=true
masking.patterns.credit-card=^([0-9]{4}).*([0-9]{4})$
masking.patterns.email=^.*@.*$

# Performance logging
perf.logging.enabled=true
perf.logging.threshold-ms=1000  # Log if > 1 second
```

---

## Module Selection: Logging Stack

| Component | Module | Purpose | Choose |
|-----------|--------|---------|--------|
| **Aspects** | mca-logging-aspects | AspectJ compile-time weaving | ✅ Required |
| **Backend** | mca-logging-config-log4j | Log4j 2 async logging | Pick ONE |
| | mca-logging-config-logback | Logback (Spring default) | Pick ONE |
| **JSON** | mca-logging-config-log4j-json | JSON output for Log4j | Optional |
| | mca-logging-config-logback-json | JSON output for Logback | Optional |
| **Masking** | mca-masking | Data redaction | ✅ Required |
| **Dynamic** | mca-logging-config-dynamic | Dynamic log level control | ✅ Recommended |
| **Testing** | mca-logging-config-test | Test support | For tests |
| **Performance** | mca-logging-performance | Performance metrics | Optional |

---

## Complete Logging Setup Example

### Minimal Setup (Console + File)

```gradle
// build.gradle
dependencies {
    implementation 'com.barclays.global.mca:mca-logging-aspects'
    implementation 'com.barclays.global.mca:mca-masking'

    runtimeOnly 'com.barclays.global.mca:mca-logging-config-logback'
}
```

**Output:**
```
2025-02-26T12:00:00.123 [http-nio-8080-exec-1] INFO  CardService - Entering: lockCard with args: [****1111]
2025-02-26T12:00:00.145 [http-nio-8080-exec-1] DEBUG CardService - Processing...
2025-02-26T12:00:00.234 [http-nio-8080-exec-1] INFO  CardService - Exiting: lockCard() returning: {status=SUCCESS}
```

### Production Setup (Async Log4j + JSON + Masking)

```gradle
// build.gradle
dependencies {
    implementation 'com.barclays.global.mca:mca-logging-aspects'
    implementation 'com.barclays.global.mca:mca-masking'

    runtimeOnly 'com.barclays.global.mca:mca-logging-config-log4j-json'
    runtimeOnly 'com.barclays.global.mca:mca-logging-config-dynamic'
}
```

**Output (JSON):**
```json
{"instant":{"epochSecond":1677408000,"nanoOfSecond":123456789},"thread":"http-nio-8080-exec-1","level":"INFO","loggerName":"com.barclays.global.mca.CardService","message":"Entering: lockCard with args: [****1111]"}
```

---

## Troubleshooting

### Issue: No Logging Output

**Solution:**
- Verify logging-config-* dependency is included
- Check logging.level.* properties
- Verify log file permissions
- Check AspectJ weaving is enabled

### Issue: Performance Logging Not Working

**Solution:**
- Verify mca-logging-performance is included
- Check @PerfLogRecordedOperation annotation
- Verify perf.logging.enabled=true

### Issue: Masking Not Working

**Solution:**
- Verify mca-masking is included
- Check masking.patterns.* configuration
- Verify @Masked annotations applied
- Check masking.enabled=true

---

## Quick Reference: Logging Stack

```
Application Code
    ↓ (AspectJ weaves logging aspects at compile time)
    ↓
SLF4J Facade
    ├─ Log4j 2 (Async, high-throughput) OR
    └─ Logback (Spring default)
    ↓
    ├─ Console Appender (immediate)
    ├─ File Appender (rolling)
    ├─ JSON Output (structured)
    └─ Additional Appenders (Syslog, Kafka, etc.)
    ↓
Data Masking
    ├─ Credit cards → ****1111
    ├─ Emails → user@***
    ├─ Phones → ***-***-4567
    └─ CRLF injection prevention
    ↓
Correlation ID Context
    ├─ ThreadLocal management
    ├─ MDC integration
    └─ Propagated through logs
    ↓
Log Aggregation
    ├─ ELK (Elasticsearch, Logstash, Kibana)
    ├─ Splunk
    ├─ CloudWatch
    └─ Datadog
```

**Logging Architecture provides enterprise-grade observability with zero-code implementation.**
