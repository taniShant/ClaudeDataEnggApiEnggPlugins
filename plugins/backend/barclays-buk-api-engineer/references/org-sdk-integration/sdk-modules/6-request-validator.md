# API SDK Module 6: Request Validator

## Overview

Intercepts and validates incoming request payloads, headers, query params, URI params against constraints specified in RAML or OAS specifications.

**Gradle Dependency:**
```gradle
com.barclays.api:bap-bld-lib-request-validator:{version}
```

---

## Features

### 1. Spec Validation (Standalone)

Run as standalone executable jar to validate specifications:

```bash
java -jar bap-bld-lib-request-validator-<version>FAT-boot.jar <path-to-spec-file>
```

**Example:**
```bash
java -jar bap-bld-lib-request-validator-1.0.003FAT-boot.jar src/main/resources/openapi/openapi.yaml
```

**Exit Codes:**
- No exception = Spec is valid
- Exception = Spec has errors

**Example Error Output:**
```
com.barclays.api.bap.bld.lib.request.validator.exception.OASInitializationException: 
[ErrorMessage(code=INTERNAL_RAML_ERROR, detail=attribute pathss is unexpected),
 ErrorMessage(code=INTERNAL_RAML_ERROR, detail=attribute paths is missing)]
```

---

### 2. Local Request Validation

Enable validation filter for local development and testing:

**Enable in `application.properties`:**
```properties
requestValidation.isRequired=true
```

---

## Integration Points in Spring Boot Project

### 1. For OAS (OpenAPI) Specifications

**Local Development:**
```properties
requestValidation.isRequired=true
requestValidation.specPath=src/main/resources/openapi/openapi.yaml
```

**Deployed in API Zone:**
```properties
requestValidation.isRequired=true
requestValidation.specPath=/api/config/openapi.zip
```

### 2. For RAML Specifications

**Local Development:**
```properties
requestValidation.isRequired=true
requestValidation.isSwaggerValidation=false
requestValidation.isSpecOnClasspath=true
requestValidation.specPath=src/main/raml/api.raml
```

**Deployed in API Zone:**
```properties
requestValidation.isRequired=true
requestValidation.isSwaggerValidation=false
requestValidation.isSpecOnClasspath=false
requestValidation.specPath=/api/config/raml.zip
```

### 3. Default Property Values

| Property | RAML Default | Swagger Default |
|---|---|---|
| `requestValidation.isSpecOnClasspath` | false | N/A |
| `requestValidation.isSwaggerValidation` | false | true |

### 4. Validation Filter Registration

The validator is registered as a servlet filter and automatically intercepts requests:

```java
// Automatic via RequestValidationFilter
// No manual registration needed if property is enabled
```

---

## Validation Strategy

### Recommended Approach (POJO with JSR Validation)

Generate POJO objects with JSR validation annotations from OAS specification:

```java
public record CreatePersonRequest(
    @NotNull @Size(min = 1) String firstName,
    @NotNull @Size(min = 1) String lastName,
    @Email String email
) {}
```

**Advantages:**
- Less CPU usage
- Better API performance
- Validation errors caught early in request handling

**Controller Usage:**
```java
@PostMapping("/persons")
public Response createPerson(@Valid @RequestBody CreatePersonRequest request) {
    // Spring automatically validates request
    // Invalid requests return 400 BAD_REQUEST
}
```

### Alternative Approach (Inline Validator)

Include validator JAR and validate programmatically:

```properties
requestValidation.isRequired=true
requestValidation.specPath=src/main/resources/openapi/openapi.yaml
```

**Note:** This approach uses more CPU. Recommend using for local testing only.

---

## Local vs Deployed Behavior

### Local Development (with validator)
- Requests validated against spec
- Invalid requests return error response
- Useful for testing compliance to OAS/RAML

### Deployed in API Zone (without validator)
- Validation performed by API Zone platform (Vinz)
- Teams **not responsible** for downstream request validation
- Teams **remain responsible** for business-level validation
- Re-validating same data is wasteful

---

## Configuration Examples

### Example 1: OAS Local Validation

**`application.yml`**
```yaml
requestValidation:
  isRequired: true
  specPath: src/main/resources/openapi/openapi.yaml
```

### Example 2: RAML Local Validation

**`application.properties`**
```properties
requestValidation.isRequired=true
requestValidation.isSwaggerValidation=false
requestValidation.isSpecOnClasspath=true
requestValidation.specPath=src/main/raml/api.raml
```

### Example 3: Production Deployment

**`application.properties`**
```properties
requestValidation.isRequired=false
# or disable validator in production:
# requestValidation.isRequired=true
# requestValidation.specPath=/api/config/openapi.zip
```

---

## Integration Points in Spring Boot Project

### 1. Dependency Configuration

**build.gradle**
```gradle
dependencies {
    // Include only for local development/testing
    implementation("com.barclays.api:bap-bld-lib-request-validator:{version}")
}
```

### 2. Conditional Dependency (Optional)

Exclude from release builds:

**build.gradle**
```gradle
dependencies {
    if (project.hasProperty('buildType') && buildType == 'local') {
        implementation("com.barclays.api:bap-bld-lib-request-validator:{version}")
    }
}
```

### 3. Request Body Validation

Spring validation integrated:

```java
@RestController
@RequestMapping("/api/persons")
public class PersonController {
    
    @PostMapping
    public Response createPerson(@Valid @RequestBody Request request) {
        // Validator automatically checks request against spec
        // If invalid: returns 400 BAD_REQUEST with validation errors
        
        Person person = request.getData(Person.class);
        return personService.create(person);
    }
    
    @PutMapping("/{id}")
    public Response updatePerson(
        @PathVariable String id,
        @Valid @RequestBody Request request) {
        // Validates against spec constraints
    }
}
```

### 4. Exception Handling for Validation Errors

Handled by SDK `GlobalExceptionHandler`:

```json
{
  "errors": [
    {
      "code": "VALIDATION_ERROR",
      "message": "Field 'firstName' is required",
      "field": "firstName",
      "severity": "ERROR"
    }
  ],
  "meta": {
    "correlationId": "abc-123"
  }
}
```

---

## Validation Scope

### Validated Elements
- Request body JSON/XML
- Query parameters
- URI path parameters
- Request headers
- Content-Type and Accept headers

### Where Validation Occurs
- **Locally:** When `requestValidation.isRequired=true`
- **API Zone:** Platform validates on entry to API Zone only
- **Downstream:** Not validated by platform; teams responsible for business logic validation

---

## Code Generation Template

### Configuration Class

```java
package {base-package}.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "requestValidation")
public class RequestValidationConfig {
    private boolean isRequired;
    private String specPath;
    private boolean isSwaggerValidation;
    private boolean isSpecOnClasspath;
    
    // Getters and setters
}
```

---

## Best Practices

1. **Local Development:** Always enable validator (`requestValidation.isRequired=true`)
2. **Release Builds:** Consider disabling to reduce JAR size and dependencies
3. **POJO Validation:** Prefer generating POJO classes with JSR annotations
4. **Error Handling:** Rely on SDK's GlobalExceptionHandler for validation errors
5. **Spec Management:** Keep spec files in classpath (`src/main/resources/`)
6. **Testing:** Test with validator enabled to catch spec compliance issues early

---

## Integration Checklist

- [ ] `com.barclays.api:bap-bld-lib-request-validator` dependency added (or conditionally for local builds)
- [ ] Spec file (OAS/RAML) placed in project
- [ ] `requestValidation.isRequired=true` for local development
- [ ] `requestValidation.specPath` configured correctly
- [ ] For RAML: `requestValidation.isSwaggerValidation=false`
- [ ] For local: `requestValidation.isSpecOnClasspath=true`
- [ ] Spec validated independently via FAT jar
- [ ] JSR validation annotations on POJOs if using POJO approach
- [ ] `@Valid` annotation on request body parameters in controllers
- [ ] Validation errors handled by GlobalExceptionHandler
- [ ] Validator disabled or spec removed for production deployment
