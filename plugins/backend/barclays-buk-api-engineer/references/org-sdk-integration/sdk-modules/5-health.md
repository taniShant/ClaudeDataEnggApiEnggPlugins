# API SDK Module 5: Health Check

## Overview

Framework for checking API health with Spring Boot Actuator integration. Provides health check controllers and metrics collection for downstream APIs and data sources.

**Gradle Dependency:**
```gradle
com.barclays.api:bap-bld-lib-health:{version}
```

If using the prescriptive framework (`bap-bld-lib-restapi`), this dependency is already included.

---

## Key Features

### 1. Spring Boot Health Endpoint

Default endpoint enabled automatically:

```
GET /health
```

Requires configuration in `application.yml`:
```yaml
management:
  endpoint:
    health:
      enabled: true
      show-details: always
```

---

### 2. Health Check Controller

Default utility endpoint:

```
GET /healthcheck
```

**Response Example:**
```json
{
  "data": {
    "status": "normal",
    "metrics": {
      "heap.committed": 834666496,
      "heap.init": 1073741824,
      "heap.used": 318103688,
      "heap": 15248916480,
      "mem": 881672640,
      "mem.free": 516562808,
      "threads.peak": 26,
      "threads.daemon": 22,
      "threads": 24
    }
  }
}
```

**Status Values:**
- `normal` — All metrics within thresholds
- `error` — One or more metrics exceed thresholds

---

### 3. Health Status Calculation

Status is `error` if any condition is true:
- CPU usage `>= 90%`
- Memory usage `>= 90%`
- Thread count `>= configured threads`

**Override Thresholds in `application.properties`:**
```properties
health.cpu.usage.max=90
health.mem.usage.max=90
health.thread.max=50
```

If `health.thread.max` is not configured, thread count is **not** used in status calculation.

---

## Integration Points in Spring Boot Project

### 1. Health Endpoint Configuration

**application.yml**
```yaml
management:
  endpoint:
    health:
      enabled: true
      show-details: always  # Show detailed health info
  endpoints:
    web:
      exposure:
        include: health,info  # Expose health endpoint
```

### 2. Downstream API Health Checks

Configure health checks for producer APIs:

**application.properties**
```properties
api.core.healthcheck.urls=USER_SERVICE_http://user-service:8080/api,PAYMENT_SERVICE_http://payment-service:8080/api
```

**Format:**
```
NAME_http://hostname:port/basepath
```

Separate multiple URLs with commas. Do **not** include `/health`.

### 3. Metrics Thresholds Configuration

**application.yml**
```yaml
health:
  cpu:
    usage:
      max: 85  # Override default 90%
  mem:
    usage:
      max: 80  # Override default 90%
  thread:
    max: 100  # Max thread count
```

### 4. Health Check in Tests

Example integration test:

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public class HealthCheckTest {
    
    @Autowired
    private TestRestTemplate restTemplate;
    
    @Test
    public void testHealthEndpoint() {
        ResponseEntity<Map> response = restTemplate.getForEntity("/health", Map.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
    }
    
    @Test
    public void testHealthCheckEndpoint() {
        ResponseEntity<Map> response = restTemplate.getForEntity("/healthcheck", Map.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        
        Map data = (Map) response.getBody().get("data");
        assertThat(data.get("status")).isIn("normal", "error");
        assertThat(data.get("metrics")).isNotNull();
    }
}
```

### 5. Load Balancer Integration

For use with load balancers and HA proxy servers:

```
GET /healthcheck
```

Load balancers can poll this endpoint to determine if server is up/running.

---

## Monitoring and Observability

### Accessing Health Metrics

Controllers can inject `HealthEndpoint` or similar to access metrics:

```java
@RestController
public class StatusController {
    
    @Autowired(required = false)
    private HealthEndpoint healthEndpoint;
    
    @GetMapping("/api/status")
    public Response getStatus() {
        // Use health metrics for custom logic
        return RestResponse.assemble()
            .withStatus(ResponseHttpStatus.OK)
            .withData("status", "running")
            .build();
    }
}
```

### Memory and Thread Monitoring

Example custom health check:

```java
@Component
public class CustomHealthIndicator extends AbstractHealthIndicator {
    
    @Override
    protected void doHealthCheck(Health.Builder builder) {
        MemoryMXBean memoryMXBean = ManagementFactory.getMemoryMXBean();
        long used = memoryMXBean.getHeapMemoryUsage().getUsed();
        long max = memoryMXBean.getHeapMemoryUsage().getMax();
        double percentage = (used * 100.0) / max;
        
        if (percentage > 90) {
            builder.down().withDetail("heapUsage", percentage + "%");
        } else {
            builder.up().withDetail("heapUsage", percentage + "%");
        }
    }
}
```

---

## Code Generation Template

### Health Configuration Class

```java
package {base-package}.config;

import org.springframework.boot.actuate.health.HealthEndpoint;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.boot.actuate.autoconfigure.health.HealthEndpointProperties;

@Configuration
public class HealthConfiguration {
    
    @Bean
    public HealthEndpoint healthEndpoint(HealthEndpointProperties properties) {
        // Custom health endpoint configuration if needed
        return new HealthEndpoint(null);  // Placeholder
    }
}
```

---

## Endpoints Summary

| Endpoint | Purpose | Status Codes |
|---|---|---|
| `GET /health` | Spring Boot health with details | 200 (UP), 503 (DOWN) |
| `GET /healthcheck` | Custom health with metrics | 200 |

---

## Health Response Schema

```json
{
  "data": {
    "status": "normal|error",
    "metrics": {
      "heap.committed": number,
      "heap.init": number,
      "heap.used": number,
      "heap": number,
      "mem": number,
      "mem.free": number,
      "threads.peak": number,
      "threads.daemon": number,
      "threads": number
    }
  }
}
```

---

## Integration Checklist

- [ ] `com.barclays.api:bap-bld-lib-health` dependency added
- [ ] Health endpoints enabled in `application.yml`
- [ ] `management.endpoint.health.show-details` set to `always`
- [ ] Downstream API URLs configured in `api.core.healthcheck.urls`
- [ ] Health thresholds configured (`health.cpu.usage.max`, `health.mem.usage.max`, `health.thread.max`)
- [ ] `/health` endpoint accessible and responding
- [ ] `/healthcheck` endpoint accessible and responding with metrics
- [ ] Load balancer configured to poll `/healthcheck`
- [ ] Custom health indicators created if needed for specific components
- [ ] Health monitoring integrated into observability/monitoring system
