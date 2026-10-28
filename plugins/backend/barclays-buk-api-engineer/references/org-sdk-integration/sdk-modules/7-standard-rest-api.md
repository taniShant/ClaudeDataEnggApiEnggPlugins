# API SDK Module 7: Standard REST API

## Overview

Prescriptive framework that brings together all other SDK modules and pre-configures them for standard REST APIs. Single dependency providing logging, payload, common, restclient, and health. Allows teams to focus on business requirements without boilerplate code.

**Gradle Dependency:**
```gradle
com.barclays.api:bap-bld-lib-restapi:{version}
```

This JAR has transitive dependencies on all other SDK modules and contains default SDK implementations.

---

## What's Included

### Core Modules (Transitive Dependencies)
- `bap-bld-lib-logging` — logging framework
- `bap-bld-lib-common` — common interfaces and utilities
- `bap-bld-lib-payload` — request/response handling
- `bap-bld-lib-restclient` — downstream REST calls
- `bap-bld-lib-health` — health checks

### Optional Modules (Add Separately)
- `bap-bld-lib-request-validator` — spec validation
- `bap-bld-lib-mesh-connector` — service mesh integration

---

## Default Configuration

### 1. Servlet Mapping
- Default servlet mapping set to `/`

### 2. Content Negotiation
- Content negotiation set to `application/json`

### 3. Exception Handling
- Exception handler resolver configured
- All exceptions return Barclays standard response structure

### 4. Date Serialization
- Date serializers configured for Java 21 time types:
  - LocalDate: `yyyy-MM-dd`
  - LocalTime: `hh:mm:ss`
  - LocalDateTime: `yyyy-MM-dd'T'HH:mm:ss.SSS`

---

## Default Filters

All filters are registered and active by default:

1. **ExceptionFilter**
   - Handles exceptions thrown from other filters
   - Ensures errors returned in standard format

2. **PerformanceLoggingFilter**
   - Logs request/response timing
   - Assigned unique ID for tracing

3. **RequestResponseLoggingFilter**
   - Logs full request details (URL, headers, body)
   - Logs full response details (status, headers, body)

4. **MandatoryHeaderValidationFilter** *(with InternalApiInitializer)*
   - Validates `Correlation-ID` header presence
   - Rejects requests without this header

5. **InternalApiLoggingContextFilter** *(with InternalApiInitializer)*
   - Adds `Correlation-ID` to MDC for logging context

---

## Integration Points in Spring Boot Project

### 1. Application Entry Point

**`{AppName}Application.java`**
```java
package {base-package};

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class MyApplication {
    public static void main(String[] args) {
        SpringApplication.run(MyApplication.class, args);
    }
}
```

### 2. API Initializer Configuration

For internal APIs requiring `Correlation-ID`:

```java
package {base-package}.config;

import com.barclays.api.bap.bld.lib.restapi.initializer.InternalApiInitializer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class ApiInitializerConfiguration {
    
    @Bean
    public InternalApiInitializer internalApiInitializer() {
        return new InternalApiInitializer();
    }
}
```

**Adds automatically:**
- `MandatoryHeaderValidationFilter`
- `InternalApiLoggingContextFilter`

### 3. Custom Filter Registration

Add custom filters after SDK filters:

```java
package {base-package}.config;

import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.Ordered;
import java.io.IOException;
import jakarta.servlet.Filter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;

@Configuration
public class FilterConfiguration {
    
    @Bean
    public FilterRegistrationBean<MyCustomFilter> myCustomFilter() {
        FilterRegistrationBean<MyCustomFilter> registrationBean = 
            new FilterRegistrationBean<>();
        registrationBean.setFilter(new MyCustomFilter());
        registrationBean.setOrder(Ordered.HIGHEST_PRECEDENCE + 55);
        return registrationBean;
    }
    
    public static class MyCustomFilter implements Filter {
        @Override
        public void doFilter(ServletRequest request, ServletResponse response, 
                           FilterChain chain) throws IOException, ServletException {
            // Custom filter logic
            chain.doFilter(request, response);
        }
    }
}
```

### 4. Filter Precedence

| Range | Usage |
|---|---|
| `HIGHEST_PRECEDENCE` | Reserved for SDK exception-handling filter |
| `HIGHEST_PRECEDENCE + 1 to 50` | Security/auth filters (execute before SDK filters) |
| `50 to 100` | SDK filters |
| `100 to LOWEST_PRECEDENCE` | Custom application filters |

---

## Exception Handling

### Global Exception Handler

Provided by SDK via `@RestControllerAdvice`:

```java
package {base-package}.exception;

import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import com.barclays.api.bap.bld.lib.payload.response.RestResponse;
import com.barclays.api.bap.bld.lib.common.Response;

@RestControllerAdvice
public class GlobalExceptionHandler {
    
    @ExceptionHandler(ApiRequestException.class)
    public Response handleApiRequestException(ApiRequestException e) {
        return RestResponse.assemble()
            .withStatus(ResponseHttpStatus.BAD_REQUEST)
            .withErrors(e.getErrors())
            .build();
    }
    
    @ExceptionHandler(ApiResourceNotFoundException.class)
    public Response handleResourceNotFound(ApiResourceNotFoundException e) {
        return RestResponse.assemble()
            .withStatus(ResponseHttpStatus.NOT_FOUND)
            .withErrors(e.getErrors())
            .build();
    }
}
```

### Controller-Level Exception Handling

```java
@RestController
@RequestMapping("/api/persons")
public class PersonController {
    
    @GetMapping("/{id}")
    public Response getPerson(@PathVariable String id) {
        // ... business logic
    }
    
    @ExceptionHandler(PersonNotFoundException.class)
    public Response handlePersonNotFound(PersonNotFoundException e) {
        Message error = new Message("PERSON_NOT_FOUND", e.getMessage());
        return RestResponse.assemble()
            .withStatus(ResponseHttpStatus.NOT_FOUND)
            .withErrors(Collections.singletonList(error))
            .build();
    }
}
```

---

## Configuration Files

### application.yml

```yaml
spring:
  application:
    name: my-api
  jpa:
    hibernate:
      ddl-auto: validate
    show-sql: false
  datasource:
    url: jdbc:postgresql://localhost:5432/mydb
    username: user
    password: password

management:
  endpoint:
    health:
      enabled: true
      show-details: always

logging:
  level:
    root: ERROR
    com.myapp: INFO
  path: /var/log/app

api:
  core:
    request:
      auto-headers: X-Scenario,Correlation-ID,clientId,Authorization
    healthcheck:
      urls: USER_SERVICE_http://user-service:8080/api

http:
  connectionTimeout: 180000
  connectionRequestTimeout: 180000
```

### application-dev.yml

```yaml
spring:
  datasource:
    url: jdbc:h2:mem:testdb
    driver-class-name: org.h2.Driver
    username: sa
  h2:
    console:
      enabled: true

logging:
  level:
    root: DEBUG
    org.springframework.web: DEBUG
```

### application-prod.yml

```yaml
spring:
  datasource:
    url: jdbc:postgresql://${DB_HOST}:5432/${DB_NAME}
    username: ${DB_USER}
    password: ${DB_PASSWORD}

logging:
  level:
    root: ERROR
```

---

## RestClient Utility

### Injection and Usage

```java
@Component
public class MyService {
    
    private final CoreRestApiClient restApiClient;
    
    public MyService(CoreRestApiClient restApiClient) {
        this.restApiClient = restApiClient;
    }
    
    public Response callDownstreamApi(String resourceId, Map<String, List<String>> headers) {
        URI uri = URI.create("http://downstream-api/resource/" + resourceId);
        return restApiClient.makeRequest(
            RestClientHttpMethod.GET,
            uri,
            headers
        );
    }
}
```

### Custom RestClient Configuration

```java
package {base-package}.config;

import com.barclays.api.bap.bld.lib.restclient.builder.CoreRestClientBuilder;
import com.barclays.api.bap.bld.lib.restclient.RestApiClient;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RestClientConfiguration {
    
    @Bean(name = "customRestClient")
    public RestApiClient customRestClient(CoreRestClientBuilder builder) {
        return builder
            .setConnectionTimeout(10000)
            .setConnectionRequestTimeout(5000)
            .setSocketTcpNoDelay(true)
            .build();
    }
}
```

---

## SDK Version Information

SDK version printed on startup:
- Console output
- `co-app.log` file

---

## Code Generation Template

### Complete Application Structure

```
{app-name}/
├── src/main/java/{base-package}/
│   ├── {AppName}Application.java
│   ├── config/
│   │   ├── ApiInitializerConfiguration.java
│   │   ├── RestClientConfiguration.java
│   │   ├── FilterConfiguration.java
│   │   └── LoggingConfiguration.java
│   ├── controller/
│   │   ├── {Resource}Controller.java
│   ├── service/
│   │   ├── {Resource}Service.java
│   │   └── impl/
│   │       └── {Resource}ServiceImpl.java
│   ├── gateway/
│   │   ├── {Producer}Gateway.java
│   │   └── impl/
│   │       └── {Producer}GatewayImpl.java
│   ├── model/
│   │   ├── request/
│   │   ├── response/
│   │   ├── client/
│   │   └── entity/
│   ├── repository/
│   │   └── {Entity}Repository.java
│   └── exception/
│       ├── GlobalExceptionHandler.java
│       └── {Domain}Exception.java
├── src/main/resources/
│   ├── application.yml
│   ├── application-dev.yml
│   ├── application-prod.yml
│   └── log4j2.xml
└── build.gradle
```

---

## Integration Checklist

- [ ] `com.barclays.api:bap-bld-lib-restapi:{version}` added to build.gradle
- [ ] Application class created with `@SpringBootApplication`
- [ ] `InternalApiInitializer` bean configured if Correlation-ID required
- [ ] `application.yml` configured with logging levels and health checks
- [ ] Filters registered for custom logic
- [ ] Exception handlers configured
- [ ] RestClient injected in gateways/services
- [ ] Content negotiation set to `application/json`
- [ ] Date serialization formats verified
- [ ] Health endpoints accessible
- [ ] Logging to `co-app.log`, `co-perf.log`, etc. verified
- [ ] All controllers return `Response` via `RestResponse.assemble()`
- [ ] Standard headers (Correlation-ID, etc.) validated
