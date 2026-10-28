# org-sdk-integration Skill — Complete Implementation Guide

Comprehensive guide for the org-sdk-integration umbrella skill that integrates all 7 organization API SDK modules into Spring Boot 3 projects.

---

## Overview

The **org-sdk-integration** skill extends `spec-to-springboot` to automate integration of the complete organization API SDK into generated projects.

**Key Features:**
- Orchestrates 7 independent module sub-skills (no blocking dependencies)
- Sequential integration with user-selectable modules
- Generates production-ready Spring Boot 3 / Java 21 projects
- Merges SDK patterns into controllers, services, gateways, configuration, and tests
- Produces downloadable ZIP with complete integration

---

## Architecture

### Umbrella Skill
- **File:** `org-sdk-integration/SKILL.md`
- **Role:** Orchestrates the 7 module sub-skills sequentially
- **Inputs:** API specs + optional SDK JAR + user preferences
- **Outputs:** ZIP with fully integrated Spring Boot project

### 7 Module Sub-Skills
Each module has its own sub-skill (to be implemented):

| ID | Module | Sub-Skill | Reference File |
|---|---|---|---|
| 1 | Logging Framework | `logging-framework-integration/SKILL.md` | `1-logging-framework.md` |
| 2 | Common Functionalities | `common-functionalities-integration/SKILL.md` | `2-common-functionalities.md` |
| 3 | Payload Structure | `payload-structure-integration/SKILL.md` | `3-payload-structure.md` |
| 4 | RestClient | `rest-client-integration/SKILL.md` | `4-rest-client.md` |
| 5 | Health Checks | `health-check-integration/SKILL.md` | `5-health.md` |
| 6 | Request Validator | `request-validator-integration/SKILL.md` | `6-request-validator.md` |
| 7 | Standard REST API | `standard-rest-api-integration/SKILL.md` | `7-standard-rest-api.md` |

### Reference Files
Located in `references/sdk-modules/`:
- Individual module specifications (1-7.md files)
- Integration summary (`INTEGRATION-SUMMARY.md`)
- Sub-skill template (`MODULE-SUBSKILL-TEMPLATE.md`)

---

## File Structure

```
C:\Users\G01186773\Claude\code-generator\
├── references/
│   └── sdk-modules/
│       ├── 1-logging-framework.md
│       ├── 2-common-functionalities.md
│       ├── 3-payload-structure.md
│       ├── 4-rest-client.md
│       ├── 5-health.md
│       ├── 6-request-validator.md
│       ├── 7-standard-rest-api.md
│       └── INTEGRATION-SUMMARY.md
├── org-sdk-integration/
│   ├── SKILL.md                          ← Main orchestration skill
│   ├── MODULE-SUBSKILL-TEMPLATE.md       ← Template for all 7 sub-skills
│   └── README.md                          ← This file
```

---

## How It Works

### User Perspective

1. **User uploads** API spec files (OAS/RAML) + optional SDK JAR
2. **User invokes** `spec-to-springboot` skill
3. Base Spring Boot project generated
4. **User invokes** `org-sdk-integration` skill to add SDK
5. **System asks** which modules to integrate (or defaults to all 7)
6. **System generates** integration code for selected modules
7. **System delivers** ZIP with fully integrated project

### Technical Flow

```
User Request
    ↓
org-sdk-integration/SKILL.md
    ├─→ Read module selection from user
    ├─→ Call Module 7 sub-skill (Standard REST API)
    ├─→ Call Module 1 sub-skill (Logging)
    ├─→ Call Module 2 sub-skill (Common)
    ├─→ Call Module 4 sub-skill (RestClient)
    ├─→ Call Module 3 sub-skill (Payload)
    ├─→ Call Module 5 sub-skill (Health)
    ├─→ Call Module 6 sub-skill (Validator) [optional]
    ├─→ Merge all returned files
    ├─→ Assemble final ZIP
    └─→ Deliver to user
```

---

## 7 Modules Explained

### Module 1: Logging Framework
- **Purpose:** Comprehensive logging with filters
- **Outputs:** LoggingConfiguration.java, logging setup in application.yml
- **Key Artifacts:** co-app.log, co-perf.log, co-event.log, co-ECrime.log
- **Reference:** `1-logging-framework.md`

### Module 2: Common Functionalities
- **Purpose:** Shared request/response interfaces and handlers
- **Outputs:** RestClientConfiguration.java, bean definitions
- **Key Classes:** Request, Response, RequestHandler, ResponseHandler
- **Reference:** `2-common-functionalities.md`

### Module 3: Payload Structure
- **Purpose:** Barclays standard request/response implementation
- **Outputs:** RestResponse builder, Message, Resource, DTOs
- **Key Pattern:** `RestResponse.assemble().withStatus(...).withData(...).build()`
- **Reference:** `3-payload-structure.md`

### Module 4: RestClient
- **Purpose:** Downstream API calls with request/response handling
- **Outputs:** Gateway interfaces and implementations
- **Key Class:** CoreRestApiClient, RestClientHttpMethod
- **Reference:** `4-rest-client.md`

### Module 5: Health Checks
- **Purpose:** API health monitoring and metrics
- **Outputs:** HealthConfiguration.java, health endpoints
- **Key Endpoints:** `/health`, `/healthcheck`
- **Reference:** `5-health.md`

### Module 6: Request Validator
- **Purpose:** OAS/RAML spec validation
- **Outputs:** Validator configuration, request validation filter
- **Key Feature:** Validates requests against spec constraints
- **Reference:** `6-request-validator.md`

### Module 7: Standard REST API
- **Purpose:** Orchestrates all modules, provides entry point
- **Outputs:** Application.java, ApiInitializer, exception handlers
- **Key Class:** InternalApiInitializer, GlobalExceptionHandler
- **Reference:** `7-standard-rest-api.md`

---

## Key Design Decisions

### 1. Sequential vs Parallel Execution
**Decision:** Sequential (non-blocking)
- Each module is independent
- Called in recommended order (7→1→2→4→3→5→6)
- Order is convenience, not requirement

### 2. Module Independence
**Decision:** No blocking dependencies
- All modules work independently
- Can be selected/deselected individually
- Merge happens at umbrella level

### 3. Configuration Merging
**Decision:** Non-destructive merge
- All modules contribute to application.yml
- build.gradle dependencies merged with org template
- No file overwrites, only additions

### 4. File Organization
**Decision:** Standard Spring Boot structure
- Controllers in `controller/`
- Services in `service/impl/`
- Gateways in `gateway/impl/`
- Models in `model/{request,response,client,entity}/`
- Configuration in `config/`

### 5. Test Generation
**Decision:** Every class gets a test
- Controller → ControllerTest.java (@WebMvcTest)
- Service → ServiceImplTest.java (@ExtendWith(MockitoExtension.class))
- Gateway → GatewayImplTest.java (@ExtendWith(MockitoExtension.class) + @Mock RestApiClient)

---

## Integration Points by Class Type

### Controllers
```java
@RestController
public class {Resource}Controller {
    private final {Resource}Service service;
    
    @GetMapping("/{id}")
    public Response get{Resource}(@PathVariable String id, InternalRequestContext context) {
        return service.get{Resource}(id, context.getCorrelationId());
    }
}
```
**Modules:** 3 (Payload), 7 (Standard API)

### Services
```java
@Service
public class {Resource}ServiceImpl implements {Resource}Service {
    private final {Producer}Gateway gateway;
    
    @Override
    public Response get{Resource}(String id, String correlationId) {
        return gateway.fetch{Resource}(id, createHeaders(correlationId));
    }
}
```
**Modules:** 3 (Payload), 4 (RestClient)

### Gateways
```java
@Component
public class {Producer}GatewayImpl implements {Producer}Gateway {
    private final CoreRestApiClient restApiClient;
    
    @Override
    public Response fetch{Resource}(String id, Map<String, List<String>> headers) {
        URI uri = URI.create(baseUrl + "/resource/" + id);
        return restApiClient.makeRequest(RestClientHttpMethod.GET, uri, headers);
    }
}
```
**Modules:** 2 (Common), 4 (RestClient)

### Configuration
```java
@Configuration
public class {Module}Configuration {
    @Bean
    public {BeanType} {beanName}() {
        // Module-specific bean
    }
}
```
**Modules:** 1, 2, 5, 7

---

## Generated Project Structure

After org-sdk-integration completes:

```
{app-name}-sdk-integrated/
├── build.gradle
│   ├── plugins: springboot, java
│   └── dependencies: restapi (includes 1-5), optionally validator
├── settings.gradle
├── gradle/wrapper/
├── src/main/java/{base-package}/
│   ├── {AppName}Application.java [Module 7]
│   ├── config/
│   │   ├── ApiInitializerConfiguration.java [Module 7]
│   │   ├── LoggingConfiguration.java [Module 1]
│   │   ├── RestClientConfiguration.java [Module 2]
│   │   ├── FilterConfiguration.java [Module 7]
│   │   └── HealthConfiguration.java [Module 5]
│   ├── controller/
│   │   └── {Resource}Controller.java [Module 3]
│   ├── service/
│   │   ├── {Resource}Service.java [Module 3]
│   │   └── impl/
│   │       └── {Resource}ServiceImpl.java [Module 3]
│   ├── gateway/
│   │   ├── {Producer}Gateway.java [Module 4]
│   │   └── impl/
│   │       └── {Producer}GatewayImpl.java [Module 4]
│   ├── model/
│   │   ├── request/{Schema}.java [Module 3]
│   │   ├── response/{Schema}.java [Module 3]
│   │   ├── client/{Schema}.java [Module 4]
│   │   └── entity/{Entity}.java [Module 3]
│   ├── repository/
│   │   └── {Entity}Repository.java [Module 3]
│   └── exception/
│       ├── GlobalExceptionHandler.java [Module 3, 7]
│       └── {Domain}Exception.java [Module 3]
├── src/test/java/{base-package}/
│   ├── controller/{Resource}ControllerTest.java
│   ├── service/impl/{Resource}ServiceImplTest.java
│   └── gateway/impl/{Producer}GatewayImplTest.java
├── src/main/resources/
│   ├── application.yml [All modules]
│   ├── application-dev.yml [1, 6]
│   ├── application-prod.yml [1]
│   └── log4j2.xml [1, optional]
└── README.md [Updated with SDK integration info]
```

---

## Module Sub-Skill Implementation Requirements

Each of the 7 module sub-skills must:

1. **Read reference file** from `references/sdk-modules/{id}-{name}.md`
2. **Parse integration patterns** from reference
3. **Accept context** from umbrella (basePackage, appName, etc.)
4. **Generate classes** based on module specification
5. **Generate tests** for all generated classes
6. **Return bundle** with files, YAML updates, Gradle updates
7. **Handle errors** gracefully with status codes

**Template provided:** `MODULE-SUBSKILL-TEMPLATE.md` (reusable pattern for all 7)

---

## Next Steps (TODO)

### Immediate (Week 1)
- [ ] Validate all 7 reference files (1-7.md)
- [ ] Test INTEGRATION-SUMMARY.md for completeness
- [ ] Validate MODULE-SUBSKILL-TEMPLATE.md pattern

### Short-term (Week 2)
- [ ] Create 7 sub-skill SKILL.md files using template:
  - [ ] `logging-framework-integration/SKILL.md`
  - [ ] `common-functionalities-integration/SKILL.md`
  - [ ] `payload-structure-integration/SKILL.md`
  - [ ] `rest-client-integration/SKILL.md`
  - [ ] `health-check-integration/SKILL.md`
  - [ ] `request-validator-integration/SKILL.md`
  - [ ] `standard-rest-api-integration/SKILL.md`

### Medium-term (Week 3-4)
- [ ] Implement code generation templates in each sub-skill
- [ ] Implement YAML merging logic in umbrella
- [ ] Implement Gradle merging logic in umbrella
- [ ] Test end-to-end orchestration
- [ ] Test ZIP assembly and delivery

### Validation (Week 5)
- [ ] Generate sample projects with all 7 modules
- [ ] Generate projects with selected modules
- [ ] Test project compilation: `./gradlew build`
- [ ] Test project execution: `./gradlew bootRun`
- [ ] Verify health endpoints: `/health`, `/healthcheck`
- [ ] Verify logging output in files
- [ ] Verify gateway calls to producers

---

## Key Files Summary

| File | Purpose | Status |
|---|---|---|
| `SKILL.md` | Umbrella orchestration skill | ✓ Complete |
| `MODULE-SUBSKILL-TEMPLATE.md` | Template for 7 sub-skills | ✓ Complete |
| `references/sdk-modules/1-*.md` | Module 1 reference | ✓ Complete |
| `references/sdk-modules/2-*.md` | Module 2 reference | ✓ Complete |
| `references/sdk-modules/3-*.md` | Module 3 reference | ✓ Complete |
| `references/sdk-modules/4-*.md` | Module 4 reference | ✓ Complete |
| `references/sdk-modules/5-*.md` | Module 5 reference | ✓ Complete |
| `references/sdk-modules/6-*.md` | Module 6 reference | ✓ Complete |
| `references/sdk-modules/7-*.md` | Module 7 reference | ✓ Complete |
| `references/sdk-modules/INTEGRATION-SUMMARY.md` | Integration overview | ✓ Complete |
| 7 × `sub-skill/SKILL.md` | Individual module skills | ⏳ TODO |

---

## Support

For questions about:
- **Module specifications:** See `references/sdk-modules/{id}-{name}.md`
- **Sub-skill implementation:** See `MODULE-SUBSKILL-TEMPLATE.md`
- **Orchestration flow:** See `SKILL.md`
- **Complete integration:** See `INTEGRATION-SUMMARY.md`

---

## Version History

| Date | Version | Status |
|---|---|---|
| 2026-05-23 | 1.0 | Initial release |

---

## Appendix: Module Dependencies Graph

```
Module 7: Standard REST API
    ├── brings together all others
    ├── provides Application.java
    └── provides default configuration

Module 1: Logging Framework
    └── independent (no dependencies)

Module 2: Common Functionalities
    └── independent (no dependencies)

Module 3: Payload Structure
    └── depends on concepts from Common (2)

Module 4: RestClient
    ├── depends on concepts from Common (2)
    └── uses Payload (3) for Response handling

Module 5: Health Checks
    └── independent (no dependencies)

Module 6: Request Validator
    └── independent (no dependencies)
```

**Key Point:** All modules are functionally independent. The dependency graph above shows conceptual relationships, not blocking dependencies. All can be called in any order.
