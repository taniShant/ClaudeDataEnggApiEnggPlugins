---
name: {module-id}-integration
description: >
  Sub-skill orchestrated by org-sdk-integration umbrella. Generates {module-name} integration code
  and configuration for Spring Boot projects. Called sequentially with other 6 module sub-skills.
  Produces module-specific classes, configuration files, and test templates ready to integrate
  with other modules.
---

# {Module Name} Integration Sub-Skill

This template defines the pattern for all 7 module sub-skills used by `org-sdk-integration`.

---

## Inheritance Model

```
org-sdk-integration (umbrella)
    ├── calls sequentially (not parallel)
    └── module-integration (this pattern x7)
            ├── reads reference file
            ├── generates module-specific classes
            ├── generates configuration
            ├── generates tests
            └── returns file bundle to umbrella
```

Each module sub-skill is **independent** and does not block others.

---

## Module Sub-Skill Responsibilities

### 1. Accept Context from Umbrella

Receive from `org-sdk-integration`:

```json
{
  "selectedModules": [1, 2, 3, 4, 5, 7],
  "basePackage": "com.example.app",
  "appName": "my-api",
  "dbLayer": true,
  "producerApis": ["user-service", "payment-service"],
  "secureFields": ["creditCard", "ssn", "password"],
  "healthCheckUrls": ["http://user-service:8080/api", "http://payment-service:8080/api"],
  "specFiles": { "consumer": "api-spec.yaml", "producers": ["user-api.yaml", "payment-api.yaml"] },
  "sdkVersion": "3.2.1"
}
```

---

### 2. Read Module Reference File

Each sub-skill reads its reference file from `references/sdk-modules/`:

**Module 1:** `1-logging-framework.md`
**Module 2:** `2-common-functionalities.md`
**Module 3:** `3-payload-structure.md`
**Module 4:** `4-rest-client.md`
**Module 5:** `5-health.md`
**Module 6:** `6-request-validator.md`
**Module 7:** `7-standard-rest-api.md`

---

### 3. Generate Module-Specific Files

Each sub-skill generates and returns:

#### **Configuration Classes**
- `{Module}Configuration.java` — Spring `@Configuration` beans

#### **Business Logic Classes**
- Controllers, Services, Gateways, Models, Repositories (varies by module)

#### **Test Classes**
- `{Class}Test.java` — JUnit 5 with Mockito

#### **Configuration Files**
- Updates to `application.yml`, `application-dev.yml`, `application-prod.yml`
- Updates to `build.gradle`

---

## Module Sub-Skill Execution Pattern

### Pseudo-Code for Each Sub-Skill

```
FUNCTION {module}-integration(context):
    
    1. READ reference file:
       ref = READ(references/sdk-modules/{module-id}-{name}.md)
    
    2. PARSE reference for:
       - Integration points
       - Configuration templates
       - Code generation patterns
    
    3. EXTRACT from context:
       - base_package
       - app_name
       - producer_apis (if applicable)
       - spec_files (if applicable)
       - secure_fields (if applicable)
    
    4. GENERATE module-specific classes:
       FOR EACH generated_class IN module.classes:
           template = GET_TEMPLATE(generated_class)
           code = RENDER(template, context)
           WRITE(src/main/java/{base_package}/{path}/{class}.java, code)
    
    5. GENERATE tests:
       FOR EACH test_class IN module.tests:
           template = GET_TEMPLATE(test_class)
           test_code = RENDER(template, context)
           WRITE(src/test/java/{base_package}/{path}/{class}Test.java, test_code)
    
    6. UPDATE configuration files:
       yaml = MERGE(application.yml, module.yaml_config)
       WRITE(src/main/resources/application.yml, yaml)
    
    7. UPDATE build.gradle:
       gradle = MERGE(build.gradle, module.gradle_deps)
       WRITE(build.gradle, gradle)
    
    8. RETURN bundle:
       RETURN {
           generated_files: [list of .java and .yml files],
           file_paths: {class_name: file_path},
           dependencies: [gradle_dependencies],
           configuration: {merged_yaml},
           status: "success"
       }
```

---

## Example: Module 1 (Logging) Sub-Skill

### Files Generated

```
src/main/java/{base-package}/config/LoggingConfiguration.java
src/main/java/{base-package}/logging/SecureFieldsConfig.java (if needed)
src/test/java/{base-package}/config/LoggingConfigurationTest.java
```

### application.yml Updates

```yaml
logging:
  level:
    root: ERROR
    {base-package}: INFO
  path: /var/log/{app-name}
```

### build.gradle Updates

```gradle
dependencies {
    // Implicit via restapi:
    // implementation 'com.barclays.api:bap-bld-lib-logging:{version}'
}
```

### Returned Bundle

```json
{
    "status": "success",
    "generated_files": [
        "src/main/java/com/example/app/config/LoggingConfiguration.java",
        "src/test/java/com/example/app/config/LoggingConfigurationTest.java"
    ],
    "yaml_updates": {
        "logging": {
            "level": { "root": "ERROR", "com.example.app": "INFO" },
            "path": "/var/log/my-api"
        }
    }
}
```

---

## Example: Module 4 (RestClient) Sub-Skill

### Files Generated

For each producer API:

```
src/main/java/{base-package}/gateway/{ProducerName}Gateway.java
src/main/java/{base-package}/gateway/impl/{ProducerName}GatewayImpl.java
src/test/java/{base-package}/gateway/impl/{ProducerName}GatewayImplTest.java
src/main/java/{base-package}/model/client/{ProducerSchema}.java
```

### application.yml Updates

```yaml
{producer-name}:
  api:
    baseUrl: http://producer-service:8080/api

# Or env-variable based:
# api:
#   producers:
#     user-service:
#       baseUrl: ${USER_SERVICE_BASE_URL:http://localhost:8090}
#     payment-service:
#       baseUrl: ${PAYMENT_SERVICE_BASE_URL:http://localhost:8091}
```

### build.gradle Updates

```gradle
dependencies {
    // Implicit via restapi:
    // implementation 'com.barclays.api:bap-bld-lib-restclient:{version}'
}
```

---

## Integration Flow (Orchestrated by Umbrella)

```
1. Umbrella asks user for module selection and context
2. Umbrella calls Module 7 sub-skill → returns app entry point files
3. Umbrella calls Module 1 sub-skill → returns logging config files
4. Umbrella calls Module 2 sub-skill → returns RestClient beans
5. Umbrella calls Module 4 sub-skill → returns gateway files
6. Umbrella calls Module 3 sub-skill → returns controller/service files
7. Umbrella calls Module 5 sub-skill → returns health config
8. Umbrella calls Module 6 sub-skill → returns validator config (if selected)
9. Umbrella MERGES all returned files
10. Umbrella ASSEMBLES final ZIP
```

---

## Return Contract for Each Sub-Skill

Every module sub-skill returns:

```json
{
    "status": "success|error",
    "moduleName": "string",
    "moduleId": "integer",
    "generatedFiles": [
        {
            "path": "src/main/java/{base-package}/{path}/{ClassName}.java",
            "type": "class|test|config",
            "content": "Java source code as string"
        }
    ],
    "configurationUpdates": {
        "application.yml": { yaml_object },
        "application-dev.yml": { yaml_object },
        "application-prod.yml": { yaml_object }
    },
    "buildGradleUpdates": {
        "dependencies": ["string list of gradle coordinates"],
        "plugins": ["plugin declarations"],
        "configurations": "custom gradle blocks as string"
    },
    "dependencies": [
        "com.barclays.api:bap-bld-lib-logging:{version}"
    ],
    "generationNotes": "Human-readable summary of what was generated"
}
```

---

## Key Design Principles

### 1. Independence
- Each module sub-skill works independently
- No module blocks another
- Can be called in any order (though recommended order exists)

### 2. Non-Destructive Merging
- Sub-skills return configurations to merge, not overwrite
- Umbrella merges all YAML and Gradle files intelligently
- No file is deleted or replaced

### 3. Context Passing
- All context flows from umbrella to sub-skills
- Sub-skills don't need to know about other modules
- Umbrella handles orchestration

### 4. Test Generation
- Every generated class has a corresponding test
- Tests are generated but can be enhanced by teams
- Follows spec-to-springboot test patterns

### 5. Documentation
- Each sub-skill generates code with minimal comments
- Reference files provide external documentation
- README generated by umbrella summarizes all modules

---

## Module Sub-Skill Checklist

For each new module sub-skill implementation:

- [ ] Reference file exists in `references/sdk-modules/{id}-{name}.md`
- [ ] Sub-skill reads reference file completely
- [ ] Sub-skill generates all required classes from reference
- [ ] Configuration classes created as `@Configuration` beans
- [ ] Test classes generated with `@ExtendWith(MockitoExtension.class)`
- [ ] application.yml sections included in return bundle
- [ ] build.gradle dependencies included in return bundle
- [ ] Return contract followed (status, generatedFiles, etc.)
- [ ] Error handling for invalid context
- [ ] Logging in sub-skill execution (for debugging)
- [ ] Documentation updated in org-sdk-integration/SKILL.md

---

## Next Steps

1. **Create 7 sub-skill files** using this pattern:
   - `logging-framework-integration/SKILL.md`
   - `common-functionalities-integration/SKILL.md`
   - `payload-structure-integration/SKILL.md`
   - `rest-client-integration/SKILL.md`
   - `health-check-integration/SKILL.md`
   - `request-validator-integration/SKILL.md`
   - `standard-rest-api-integration/SKILL.md`

2. **Each sub-skill inherits this structure** and customizes for its module

3. **Umbrella orchestrates all 7** per org-sdk-integration/SKILL.md workflow

4. **Reference files** already created in `references/sdk-modules/`
