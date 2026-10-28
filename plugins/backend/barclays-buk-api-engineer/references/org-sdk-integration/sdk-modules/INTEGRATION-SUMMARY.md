# API SDK V3 Integration Summary

Complete reference for integrating all 7 API SDK modules into generated Spring Boot projects.

---

## Module Dependency Graph

```
Standard REST API (7)
    ├── Logging Framework (1)
    ├── Common Functionalities (2)
    │   ├── RestClient (4)
    │   │   ├── Payload Structure (3)
    │   │   └── Common (2)
    ├── Payload Structure (3)
    ├── Health (5)
    └── Request Validator (6) [Optional]
```

**Note:** All 7 modules are INDEPENDENT (no blocking dependencies). No module waits for another.

---

## Files to Generate Per Module

| Module | Reference File | Config File | Classes to Generate |
|---|---|---|---|
| 1. Logging | `1-logging-framework.md` | `LoggingConfiguration.java` | Logger configuration |
| 2. Common | `2-common-functionalities.md` | `RestClientConfiguration.java` | RestClient beans |
| 3. Payload | `3-payload-structure.md` | Controllers, Services | Response builders |
| 4. RestClient | `4-rest-client.md` | Gateway interfaces/impls | Gateway pattern |
| 5. Health | `5-health.md` | `HealthConfiguration.java` | Health beans |
| 6. Validator | `6-request-validator.md` | None | Enable in properties |
| 7. Standard API | `7-standard-rest-api.md` | Application class | App entry point |

---

## Integration Points by Generated Class Type

### Controllers
- Use `@RestController` (not `@Controller`)
- Inject RequestContext (e.g., InternalRequestContext)
- Return `Response` via `RestResponse.assemble()`
- Inject Services only
- Pass request headers to services

**Modules involved:** 3 (Payload), 7 (Standard API)

### Services
- Inject Gateways only
- Pass headers from controller
- Return `Response` from gateways
- Can perform business validation

**Modules involved:** 3 (Payload), 4 (RestClient), 7 (Standard API)

### Gateways
- One per producer spec
- Inject `CoreRestApiClient`
- Use `RestClientHttpMethod` enum
- Pass `Map<String, List<String>>` headers
- Return `Response`

**Modules involved:** 2 (Common), 4 (RestClient), 7 (Standard API)

### Models (Entities)
- Use Lombok `@Data` + `@Builder`
- Add JSR validation annotations
- Immutable DTOs can use Java Records

**Modules involved:** 3 (Payload)

### Configuration Classes
- `LoggingConfiguration` — logging
- `RestClientConfiguration` — RestClient beans
- `ApiInitializerConfiguration` — InternalApiInitializer
- `FilterConfiguration` — custom filters
- `HealthConfiguration` — health checks (optional)

**Modules involved:** 1, 2, 5, 7

### Exception Handlers
- `@RestControllerAdvice` for global handling
- Return `RestResponse` with errors
- Handle `ApiRequestException`, `ApiResourceNotFoundException`, etc.

**Modules involved:** 3 (Payload), 7 (Standard API)

### build.gradle
- Include `com.barclays.api:bap-bld-lib-restapi:{version}`
- Optional: `com.barclays.api:bap-bld-lib-request-validator:{version}`

---

## Configuration Files Required

### application.yml (Base)
```yaml
spring:
  application:
    name: {app-name}
  datasource:
    url: jdbc:postgresql://localhost:5432/{db-name}
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
  path: /var/log/app

api:
  core:
    request:
      auto-headers: X-Scenario,Correlation-ID,clientId,Authorization
    healthcheck:
      urls: PRODUCER1_http://producer1:8080/api,PRODUCER2_http://producer2:8080/api

http:
  connectionTimeout: 180000
  connectionRequestTimeout: 180000
```

### application-dev.yml
- Logging level: DEBUG
- Database: H2 or local PostgreSQL
- Disable validator if included

### application-prod.yml
- Logging level: ERROR
- Database: Production PostgreSQL
- Health check URLs for production services

---

## Step-by-Step Integration Workflow

### Step 1: Dependency Addition
- Add `bap-bld-lib-restapi:{version}` to build.gradle
- Optionally add `bap-bld-lib-request-validator:{version}`

### Step 2: Core Configuration (Module 7)
- Create `{AppName}Application.java` with `@SpringBootApplication`

### Step 3: API Initialization (Module 7 + 1)
- Create `ApiInitializerConfiguration` with `InternalApiInitializer` bean
- Configure logging in `application.yml`

### Step 4: RestClient Setup (Module 2 + 4)
- Create `RestClientConfiguration` with bean
- Define gateway interfaces per producer spec

### Step 5: Controller/Service/Gateway (Modules 3, 4)
- Generate controllers returning `RestResponse`
- Generate services calling gateways
- Generate gateways calling `CoreRestApiClient`

### Step 6: Models (Module 3)
- Generate entities with Lombok
- Generate DTOs with validation
- Generate resource wrappers

### Step 7: Exception Handling (Module 3 + 7)
- Create `GlobalExceptionHandler` with `@RestControllerAdvice`
- Add custom exception classes

### Step 8: Health & Logging (Modules 1, 5)
- Configure health checks in `application.yml`
- Verify logging output in files

### Step 9: Validation (Module 6 - Optional)
- Add validator dependency if needed
- Enable in `application-dev.yml`
- Configure spec path

### Step 10: Filter Registration (Module 7)
- Create `FilterConfiguration` if custom filters needed
- Maintain filter precedence order

---

## Key Integration Rules

### Headers
- Always pass as `Map<String, List<String>>`
- Default auto-headers: `X-Scenario`, `Correlation-ID`, `clientId`, `Authorization`
- Configurable via `api.core.request.auto-headers`

### Response Structure
```json
{
  "data": {},        // Success
  "meta": {},        // Optional
  "errors": []       // Errors only
}
```

### Logging
- Root logger level: ERROR (configurable)
- Performance logs: `co-perf.log`
- Request/response: `co-app.log`
- Events: `co-event.log`
- ECrime: `co-ECrime.log`

### Filters Order
1. Exception filter (HIGHEST_PRECEDENCE)
2. Security filters (HIGHEST_PRECEDENCE + 1 to 50)
3. SDK filters (50 to 100)
4. Custom filters (100+)

### Date/Time Formats
- LocalDate: `yyyy-MM-dd`
- LocalTime: `hh:mm:ss`
- LocalDateTime: `yyyy-MM-dd'T'HH:mm:ss.SSS`

### Endpoints
- Health: `GET /health`
- Health check: `GET /healthcheck`
- API endpoints: User-defined

---

## Quick Reference: Module Responsibilities

| Module | Provides | Configuration |
|---|---|---|
| 1. Logging | Loggers, appenders, filters | `application.yml` logging section |
| 2. Common | Request/Response interfaces | RestClient beans |
| 3. Payload | RestResponse, Message, Resource | ResponseBuilder pattern |
| 4. RestClient | CoreRestApiClient bean | HTTP pooling properties |
| 5. Health | Health endpoints, metrics | management section, health properties |
| 6. Validator | Request validation filter | `requestValidation.*` properties |
| 7. Standard API | Entry point, default config | Spring Boot defaults |

---

## Output Checklist for SDK Integration

- [ ] All 7 module reference files read and understood
- [ ] build.gradle includes `bap-bld-lib-restapi`
- [ ] Application class created with `@SpringBootApplication`
- [ ] ApiInitializer bean configured
- [ ] RestClient bean configured
- [ ] Controllers inject RequestContext and return Response
- [ ] Services inject Gateways
- [ ] Gateways inject CoreRestApiClient and use RestClientHttpMethod
- [ ] Models use Lombok or Java Records
- [ ] Exception handlers return RestResponse
- [ ] Configuration files (base, dev, prod) created
- [ ] Logging paths and levels configured
- [ ] Health check endpoints accessible
- [ ] Request/response structure matches Barclays standard
- [ ] Headers passed as Map<String, List<String>>
- [ ] Auto-headers configured for downstream calls
- [ ] Filter precedence respected
- [ ] Test suite validates SDK integration
