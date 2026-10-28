# Spring Boot (Java) — OTel Conventions

## Detection Patterns

A repo is Spring Boot if ANY of these are true:
- `pom.xml` exists with `spring-boot-starter-*` dependencies
- `build.gradle` or `build.gradle.kts` exists with `org.springframework.boot` plugin
- `src/main/resources/application.yml` or `application.properties` exists with `spring.*` keys

**Build tool detection:**
- `pom.xml` at root → Maven
- `build.gradle` or `build.gradle.kts` at root → Gradle
- Both present → check which has Spring Boot config (prefer Gradle if both do)

**Application type indicators:**
- HTTP API: `spring-boot-starter-web` or `spring-boot-starter-webflux` dependency
- Kafka consumer: `spring-kafka` dependency

## OTel SDK Dependencies

Add these to `pom.xml` or `build.gradle` (names only — let BOM/parent manage versions):

| Artifact | Purpose |
|----------|---------|
| `io.opentelemetry:opentelemetry-sdk` | Core OTel SDK |
| `io.opentelemetry:opentelemetry-exporter-otlp` | OTLP exporter for Collector |
| `io.opentelemetry.instrumentation:opentelemetry-logback-appender` | Logback → OTel bridge |
| `io.opentelemetry.instrumentation:opentelemetry-spring-boot-starter` | Auto-instrumentation for Spring |

For Kafka context propagation:
| `io.opentelemetry.instrumentation:opentelemetry-kafka-clients` | Kafka header propagation |

## Structured Logging Configuration

### Logback (default for Spring Boot)

Create or update `src/main/resources/logback-spring.xml`:

```xml
<configuration>
  <appender name="OTEL" class="io.opentelemetry.instrumentation.logback.appender.v1_0.OpenTelemetryAppender">
    <captureExperimentalAttributes>true</captureExperimentalAttributes>
    <captureKeyValuePairAttributes>true</captureKeyValuePairAttributes>
  </appender>

  <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
    <encoder class="net.logstash.logback.encoder.LogstashEncoder">
      <includeMdcKeyName>trace_id</includeMdcKeyName>
      <includeMdcKeyName>span_id</includeMdcKeyName>
    </encoder>
  </appender>

  <root level="INFO">
    <appender-ref ref="CONSOLE" />
    <appender-ref ref="OTEL" />
  </root>
</configuration>
```

### Application properties

```yaml
otel:
  exporter:
    otlp:
      endpoint: ${OTEL_EXPORTER_OTLP_ENDPOINT:}
  resource:
    attributes:
      service.name: ${OTEL_SERVICE_NAME:${spring.application.name}}
      service.version: ${BUILD_VERSION:unknown}
      deployment.environment: ${ENVIRONMENT:local}
```

**Key:** The endpoint defaults to EMPTY (not localhost:4317). When empty, the OTLP exporter is effectively disabled — no export, no connection attempts, no memory pressure. The app runs purely on stdout logging. Set the env var only when a Collector is available.

### Graceful degradation configuration

```yaml
otel:
  bsp:
    max-queue-size: 512
    max-export-batch-size: 128
    export-timeout: 5000
    schedule-delay: 5000
  blrp:
    max-queue-size: 512
    max-export-batch-size: 128
    export-timeout: 5000
    schedule-delay: 5000
```

These settings ensure:
- Queue stays bounded (512 records max — ~2MB heap at worst)
- Export timeout is short (5s — don't block threads waiting for a dead Collector)
- If queue fills, new records are dropped (logs still appear on stdout via CONSOLE appender)
- No memory leak, no thread exhaustion, no app degradation

## Correlation IDs (MDC)

The OTel Java agent or SDK automatically injects `trace_id` and `span_id` into the SLF4J MDC when using `opentelemetry-spring-boot-starter`. No manual code needed.

**Verification:** After setup, every log statement emitted during an HTTP request with a `traceparent` header will include `trace_id` and `span_id` in the MDC.

If NOT using the starter (manual setup), register an MDC-injecting filter:

```java
import io.opentelemetry.api.trace.Span;
import org.slf4j.MDC;
import jakarta.servlet.Filter;

public class TraceContextFilter implements Filter {
    @Override
    public void doFilter(ServletRequest req, ServletResponse res, FilterChain chain) {
        Span span = Span.current();
        MDC.put("trace_id", span.getSpanContext().getTraceId());
        MDC.put("span_id", span.getSpanContext().getSpanId());
        try {
            chain.doFilter(req, res);
        } finally {
            MDC.remove("trace_id");
            MDC.remove("span_id");
        }
    }
}
```

## Bridge Pattern (Existing Logging)

If the repo already has Logback configured (custom appenders, Splunk forwarders):
1. Keep the existing appender — do NOT remove it
2. Add the OTel appender alongside it (both in `<root>`)
3. Existing log destinations continue working unchanged
4. OTel becomes an additional export path

## Context Propagation

### HTTP (W3C Trace Context)

`opentelemetry-spring-boot-starter` automatically:
- Extracts `traceparent` from inbound requests
- Injects `traceparent` into outbound RestTemplate/WebClient calls

No manual code required when using the starter.

### Kafka

With `opentelemetry-kafka-clients`:
- Consumer: automatically extracts trace context from Kafka message headers
- Producer: automatically injects trace context into Kafka message headers

For Spring Kafka, register the interceptors:

```yaml
spring:
  kafka:
    consumer:
      properties:
        interceptor.classes: io.opentelemetry.instrumentation.kafkaclients.TracingConsumerInterceptor
    producer:
      properties:
        interceptor.classes: io.opentelemetry.instrumentation.kafkaclients.TracingProducerInterceptor
```

## Common Detection Indicators (for Review Agent)

| Indicator | Means |
|-----------|-------|
| `logback.xml` or `logback-spring.xml` exists | Logback in use |
| `log4j2.xml` or `log4j2-spring.xml` exists | Log4j2 in use (need different bridge) |
| `LogstashEncoder` in logback config | Already structured JSON (ECS likely) |
| `opentelemetry` in pom.xml/build.gradle | OTel already partially adopted |
| `micrometer` dependency present | Metrics may already exist |
| `spring-cloud-sleuth` dependency | Legacy tracing — should migrate to OTel |
