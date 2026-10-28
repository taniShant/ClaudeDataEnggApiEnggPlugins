---
name: org-sdk-integration
description: >
  Extends spec-to-springboot skill to integrate organization API SDK (all 7 modules) into generated
  Spring Boot projects. When user supplies SDK JAR or requests SDK integration, orchestrates module
  sub-skills to inject SDK patterns into controllers, services, gateways, configuration, and test files.
  Supports sequential or user-selected module integration. Produces production-ready Spring Boot 3 / Java 21
  project with complete SDK wiring.
  Use this skill when: SDK JAR uploaded, user requests "integrate SDK", "add logging framework",
  "configure RestClient", "add health checks", or any SDK module mentioned.
---

> **Source:** Barclays BUK organisation API SDK documentation and SDK3 module integration guide.
> **Owner:** BUK
> **Review trigger:** On SDK module major/minor version release or new SDK module added to the catalogue.
> **Status:** Reviewed

# org-sdk-integration Skill

Extends the `spec-to-springboot` skill to integrate all 7 organization API SDK modules into generated Spring Boot projects.

This umbrella skill orchestrates 7 independent module sub-skills, each handling one discrete concern:
1. Logging Framework
2. Common Functionalities
3. Payload Structure
4. RestClient
5. Health Checks
6. Request Validator
7. Standard REST API

## Quick Start

Integrate SDK modules into a generated Spring Boot project:

1. Ensure base project is already generated (spec-to-springboot complete)
2. Invoke with: `barclays-buk-api-engineer:org-sdk-integration`
3. Modules are applied in order: Logging → Common → Payload → RestClient → Health → Validator → REST API
4. Each module adds configuration, beans, and imports to existing files

---

## Prerequisite: spec-to-springboot Skill

This skill **extends** spec-to-springboot and requires:
1. API specification files (OAS 3.x or RAML 1.0) already uploaded
2. Base Spring Boot 3 / Java 21 project already generated
3. Org SDK JAR file uploaded (optional, for module-specific patterns)

If you have **only** the SDK JAR without a spec, contact the code generator team.

---

## Reference Files — Read These First

| File | When to read |
|---|---|
| `../../references/org-sdk-integration/sdk-modules/1-logging-framework.md` | Before generating logging config |
| `../../references/org-sdk-integration/sdk-modules/2-common-functionalities.md` | Before generating RestClient config |
| `../../references/org-sdk-integration/sdk-modules/3-payload-structure.md` | Before generating controllers/services |
| `../../references/org-sdk-integration/sdk-modules/4-rest-client.md` | Before generating gateways |
| `../../references/org-sdk-integration/sdk-modules/5-health.md` | Before generating health config |
| `../../references/org-sdk-integration/sdk-modules/6-request-validator.md` | Before generating validator config |
| `../../references/org-sdk-integration/sdk-modules/7-standard-rest-api.md` | Before generating main application |
| `../../references/org-sdk-integration/sdk-modules/INTEGRATION-SUMMARY.md` | For complete integration overview |

Always read all reference files to understand the 7-module integration pattern.

---

## Execution Workflow

### STEP 1 — Detect & Load SDK JAR (Optional)

1. Check if user uploaded Org SDK JAR file
2. If present:
   - Extract JAR contents
   - Identify SDK version from manifest
   - Extract module JARs and classes
   - Map modules to their features
3. If absent:
   - Use default SDK configuration (Gradle dependencies)
   - Continue with module integration

---

### STEP 2 — Module Selection Checkpoint

Ask user which modules to integrate:

```
The org-sdk-integration skill supports 7 modules:

1. ✓ Logging Framework (required) — adds logging config
2. ✓ Common Functionalities (required) — adds RestClient beans
3. ✓ Payload Structure (required) — response builders
4. ✓ RestClient (required) — gateway patterns
5. ✓ Health Checks (optional) — health endpoints
6. ? Request Validator (optional) — spec validation
7. ✓ Standard REST API (required) — application entry point

Which modules would you like to integrate?
(Default: all 7)

Options:
- "all" — integrate all 7 modules
- "required" — integrate 1,2,3,4,7 only
- "custom" — select specific modules (list: 1,3,5,6)
```

Wait for user choice before proceeding.

---

### STEP 3 — Pre-Integration Clarification

Before generating SDK-integrated code, ask:

```
I need a few details for SDK module configuration:

1. **Org SDK JAR version** (if JAR was uploaded)
   - Example: com.barclays.api:bap-bld-lib-restapi:3.2.1

2. **Producer APIs** to integrate via RestClient (for RestClient module)
   - Example: "user-service, payment-service, notification-service"
   - Or: "none" if consumer-only

3. **Secure logging fields** (for Logging module)
   - Example: "creditCard, ssn, password" (or "default" to use Authorization header only)

4. **Health check endpoints** (for Health module)
   - Example: "http://user-service:8080/api, http://payment-service:8080/api"
   - Or: "none" if no downstream health checks needed

5. **Enable Request Validator?** (module 6, optional)
   - OAS spec path: src/main/resources/openapi/openapi.yaml
   - RAML spec path: src/main/raml/api.raml
   - Or: "no" to skip validator

6. **Custom filter precedence** (for Standard REST API module)
   - Leave default or specify custom filter order?

Wait for all answers before proceeding.
```

---

### STEP 4 — Read Module Reference Files

Based on selected modules, read the corresponding reference files from `references/org-sdk-integration/sdk-modules/`:

- **Module 1 selected** → read `1-logging-framework.md`
- **Module 2 selected** → read `2-common-functionalities.md`
- **Module 3 selected** → read `3-payload-structure.md`
- **Module 4 selected** → read `4-rest-client.md`
- **Module 5 selected** → read `5-health.md`
- **Module 6 selected** → read `6-request-validator.md`
- **Module 7 selected** → read `7-standard-rest-api.md`
- **Always read** → `INTEGRATION-SUMMARY.md`

---

### STEP 5 — Orchestrate Module Sub-Skills (Sequential, Independent)

Since all 7 modules are **independent** (no blocking dependencies), call module sub-skills:

```
Call each selected module sub-skill in sequence:

For each module M in [selected modules]:
  1. Invoke {module-M}-integration sub-skill
  2. Pass context from Step 3 (producer APIs, secure fields, etc.)
  3. Collect generated files:
     - Configuration classes
     - Code patterns (controllers, services, gateways, models)
     - Test files
     - Updated build.gradle
     - Updated application.yml / -dev / -prod
  4. Merge into project structure
```

**Module Order (recommended, but not blocking):**
1. Module 7 (Standard REST API) — application entry point
2. Module 1 (Logging) — logging configuration
3. Module 2 (Common) — RestClient beans
4. Module 4 (RestClient) — gateway patterns
5. Module 3 (Payload) — controllers, services, response builders
6. Module 5 (Health) — health endpoints
7. Module 6 (Validator) — validation filters (if selected)

---

### STEP 6 — Merge Generated Files

Combine outputs from all module sub-skills:

**Package Structure After Merge:**
```
{app-name}/
├── build.gradle (merged: SDK dependencies, plugins)
├── settings.gradle
├── src/main/java/{base-package}/
│   ├── {AppName}Application.java (Module 7)
│   ├── config/
│   │   ├── ApiInitializerConfiguration.java (Module 7)
│   │   ├── LoggingConfiguration.java (Module 1)
│   │   ├── RestClientConfiguration.java (Module 2)
│   │   ├── FilterConfiguration.java (Module 7)
│   │   └── HealthConfiguration.java (Module 5)
│   ├── controller/
│   │   ├── {Resource}Controller.java (Module 3)
│   │   └── {Resource}ControllerTest.java
│   ├── service/
│   │   ├── {Resource}Service.java (Module 3)
│   │   ├── impl/
│   │   │   └── {Resource}ServiceImpl.java (Module 3)
│   │   └── impl/
│   │       └── {Resource}ServiceImplTest.java
│   ├── gateway/
│   │   ├── {Producer}Gateway.java (Module 4)
│   │   ├── impl/
│   │   │   └── {Producer}GatewayImpl.java (Module 4)
│   │   └── impl/
│   │       └── {Producer}GatewayImplTest.java
│   ├── model/
│   │   ├── request/ (Module 3)
│   │   ├── response/ (Module 3)
│   │   ├── client/ (Module 4)
│   │   └── entity/ (Module 3)
│   ├── repository/ (Module 3, if DB layer)
│   ├── exception/
│   │   ├── GlobalExceptionHandler.java (Module 3, 7)
│   │   └── {Domain}Exception.java (Module 3)
│   └── logging/ (Module 1)
│       └── LoggerFactory usage examples
├── src/main/resources/
│   ├── application.yml (merged: all modules)
│   ├── application-dev.yml (Module 1, 6)
│   ├── application-prod.yml (Module 1)
│   └── log4j2.xml (Module 1, if custom)
└── README.md (updated with SDK integration)
```

**Merge Rules:**
- `build.gradle`: Add all SDK module dependencies from modules 1-7; preserve org template
- `application.yml`: Merge logging, health, http pooling, api.core sections from all modules
- Controllers: Return `Response` via `RestResponse.assemble()` (Module 3)
- Services: Inject gateways (Module 4)
- Gateways: Use `CoreRestApiClient` (Module 2, 4)
- Exception handlers: Handle SDK exceptions + custom (Module 3, 7)
- Tests: Generated per module spec

---

### STEP 7 — Generate Cross-Module Integration Files

Create files that coordinate all modules:

#### 7a. Updated build.gradle

```gradle
plugins {
    id 'java'
    id 'org.springframework.boot' version '3.3.0'
}

dependencies {
    // SDK Core (Module 7)
    implementation 'com.barclays.api:bap-bld-lib-restapi:{version}'
    
    // Implicit (via restapi transitive):
    // - Module 1: bap-bld-lib-logging
    // - Module 2: bap-bld-lib-common
    // - Module 3: bap-bld-lib-payload
    // - Module 4: bap-bld-lib-restclient
    // - Module 5: bap-bld-lib-health
    
    // Optional modules (if selected):
    // - Module 6: request-validator
    // implementation 'com.barclays.api:bap-bld-lib-request-validator:{version}'
}
```

#### 7b. Updated application.yml

```yaml
spring:
  application:
    name: {app-name}
  datasource:
    url: jdbc:postgresql://localhost:5432/{db-name}
    username: user
    password: password

# Module 1: Logging
logging:
  level:
    root: ERROR
  path: /var/log/app

# Module 5: Health
management:
  endpoint:
    health:
      enabled: true
      show-details: always

# Module 2 + 4: RestClient
api:
  core:
    request:
      auto-headers: X-Scenario,Correlation-ID,clientId,Authorization
    healthcheck:
      urls: {producer-apis}

# Module 4: HTTP Pooling
http:
  connectionTimeout: 180000
  connectionRequestTimeout: 180000

# Module 6: Request Validator (if selected)
# requestValidation:
#   isRequired: true
#   specPath: src/main/resources/openapi/openapi.yaml
```

#### 7c. Integration Checklist README

Add to generated README.md:

```markdown
## API SDK Integration

This project integrates 7 organization API SDK modules:

1. ✓ Logging Framework — `co-app.log`, `co-perf.log`, etc.
2. ✓ Common Functionalities — RestClient bean configuration
3. ✓ Payload Structure — Response builders and DTOs
4. ✓ RestClient — Gateway patterns for downstream APIs
5. ✓ Health Checks — `/health` and `/healthcheck` endpoints
6. ✗ Request Validator — (not integrated)
7. ✓ Standard REST API — Application entry point

### Verification Checklist

- [ ] Application starts: `./gradlew bootRun`
- [ ] Health check responds: `curl http://localhost:8080/healthcheck`
- [ ] Logging files created in `/var/log/app/`
- [ ] RestClient calls work to downstream APIs
- [ ] Controllers return Barclays standard Response structure
- [ ] Correlation-ID header propagated through logs
- [ ] All tests pass: `./gradlew test`
```

---

### STEP 8 — Assemble ZIP

Create final ZIP with all integrated files:

```python
import zipfile, os

zip_path = f"/mnt/user-data/outputs/{app_name}-sdk-integrated.zip"
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(f"/home/claude/{app_name}"):
        for file in files:
            abs_path = os.path.join(root, file)
            arc_path = os.path.relpath(abs_path, f"/home/claude/{app_name}")
            zf.write(abs_path, arc_path)
```

---

### STEP 9 — Iterative Refinement

When user requests changes to SDK integration:

1. **Identify scope** — which modules affected?
   - New producer API → Module 4 (RestClient) affected
   - Add health checks → Module 5 (Health) affected
   - Change logging → Module 1 (Logging) affected
   - New validator rules → Module 6 (Validator) affected
2. **Re-invoke affected module sub-skill(s)**
3. **Regenerate only affected files**
4. **Reassemble full ZIP**

---

## Module Sub-Skills (7 Total)

Each module has its own sub-skill handling module-specific generation:

1. **logging-framework-integration**
   - Generates LoggingConfiguration.java
   - Updates application.yml with logging config
   - Adds SecureFields bean if needed

2. **common-functionalities-integration**
   - Generates RestClientConfiguration.java
   - Creates RestClient bean
   - Configures request/response handlers

3. **payload-structure-integration**
   - Generates controller methods returning RestResponse
   - Generates DTOs (request/response/client models)
   - Generates response building patterns

4. **rest-client-integration**
   - Generates gateway interfaces per producer spec
   - Generates gateway implementations
   - Generates gateway tests

5. **health-check-integration**
   - Generates HealthConfiguration.java
   - Updates application.yml for health endpoints
   - Configures downstream API health checks

6. **request-validator-integration**
   - Enables RequestValidationFilter
   - Configures spec path in properties
   - Generates validator tests

7. **standard-rest-api-integration**
   - Generates Application.java entry point
   - Generates ApiInitializerConfiguration
   - Generates default exception handlers

---

## Output Checklist

Before delivering ZIP, verify:

- [ ] All selected modules integrated (check each .java file exists)
- [ ] build.gradle includes all SDK dependencies
- [ ] application.yml contains sections from all modules
- [ ] Application starts without errors: `./gradlew bootRun`
- [ ] Controllers inject services correctly
- [ ] Services inject gateways correctly
- [ ] Gateways use CoreRestApiClient correctly
- [ ] All responses built with RestResponse.assemble()
- [ ] Logging configured (check co-app.log exists)
- [ ] Health endpoints accessible
- [ ] Headers passed as Map<String, List<String>>
- [ ] Auto-headers configured for downstream calls
- [ ] Exception handlers return RestResponse
- [ ] Tests exist for all endpoints
- [ ] README updated with integration details
- [ ] ZIP contains project folder as root

---

## Related Skills

- **spec-to-springboot** — Base skill (prerequisite)
- **logging-framework-integration** — Module 1 sub-skill
- **common-functionalities-integration** — Module 2 sub-skill
- **payload-structure-integration** — Module 3 sub-skill
- **rest-client-integration** — Module 4 sub-skill
- **health-check-integration** — Module 5 sub-skill
- **request-validator-integration** — Module 6 sub-skill
- **standard-rest-api-integration** — Module 7 sub-skill

---

## Trigger Conditions

Invoke this skill when:

- User uploads SDK JAR and wants integration
- User requests "integrate SDK modules"
- User mentions specific module (logging, health, validator, etc.)
- User says "add SDK to the generated project"
- User uploads both spec files AND SDK JAR
- User requests "enable health checks", "configure logging", "add RestClient gateway", etc.

**Always use after spec-to-springboot generates base project.**

## Source Attribution

**Primary sources:**
- Barclays organisation API SDK documentation — 7 module descriptions, JAR coordinates, and wiring instructions
- `sdk-integration-guide/SKILL.md` — production patterns for `LogFactory`, `PerfLogger`, `RequestContext`, `RestClient`, and SDK initializer beans
- BUK API Engineering team knowledge — module selection rules (mandatory vs. optional), `InternalApiInitializer` vs. `ExternalApiInitializer` decision criteria

**Training knowledge applied:**
- Spring Boot `@Configuration` / `@Bean` wiring patterns for SDK module registration
- Java 21 / Spring Boot 3 constructor injection patterns applied during SDK integration
- Sequential vs. parallel module integration strategy selection based on project state

**Known limitations:**
- Module catalogue is fixed to the 7 modules known at skill review date; newly released SDK modules will not appear until the skill is updated
- SDK JAR coordinates (group ID, artifact ID, version) must be verified from the actual JAR or Nexus before use — this skill documents the expected coordinates, not a live registry
- Integration assumes the project was generated by `spec-to-springboot` or `barclays-buk-api-engineer:project-generation-agent`; manually structured projects may require adaptation

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] Are all 7 mandatory SDK modules integrated (logging, common, payload, restclient, health, validator, standard-rest-api)?
- [ ] Is the SDK initializer bean (InternalApiInitializer or ExternalApiInitializer) declared in ApplicationConfig?
- [ ] Are SDK module dependencies added to build.gradle and not duplicated in daf-dependencies.gradle?
- [ ] Is the mesh token interceptor (ServiceMeshRequestInterceptor) wired via the SDK configuration?
- [ ] Does the post-SDK compliance scan return VERDICT APPROVED before generation is marked complete?
