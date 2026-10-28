# API SDK Module 3: Payload Structure

## Overview

Default implementation for Request, Response, associated handlers, and exception handling. Provides concrete classes based on interfaces from Common module. Implements Barclays standard request/response structure.

**Gradle Dependency:**
```gradle
implementation 'com.barclays.api:bap-bld-lib-payload:{version}'
```

If using the prescriptive framework (`bap-bld-lib-restapi`), this dependency is already included.

---

## Response Structure

All API responses follow Barclays standard structure with three sections:

```json
{
  "data": {},           // Success payload (Object/Array)
  "meta": {},           // Optional metadata
  "errors": []          // Error messages (array)
}
```

**Note:** `data` and `errors` are mutually exclusive.

---

## Successful Response Examples

### Single Resource Response

```json
{
  "data": {
    "id": "12345",
    "type": "persons",
    "attributes": {
      "fName": "Barclays",
      "lName": "Radbroke",
      "email": "barclays.radbroke@example.com"
    }
  },
  "meta": {
    "recordCount": 1,
    "timestamp": "2026-02-19T10:30:00.000"
  }
}
```

### Collection Response

```json
{
  "data": [
    {
      "id": "12345",
      "type": "persons",
      "attributes": { "fName": "Barclays", "lName": "Radbroke" }
    }
  ],
  "meta": {
    "recordCount": 1,
    "totalRecords": 150,
    "page": 1,
    "pageSize": 2
  }
}
```

---

## Error Response Examples

### Single Error
```json
{
  "errors": [
    {
      "code": "RESOURCE_NOT_FOUND",
      "message": "The requested person with ID 12345 was not found",
      "field": "id",
      "severity": "ERROR"
    }
  ],
  "meta": {
    "correlationId": "abc-123-def-456"
  }
}
```

### Validation Errors
```json
{
  "errors": [
    {
      "code": "VALIDATION_ERROR",
      "message": "First name is required",
      "field": "fName",
      "severity": "ERROR"
    }
  ],
  "meta": {
    "correlationId": "xyz-789-uvw-012"
  }
}
```

---

## Integration Points in Spring Boot Project

### 1. Request Context Injection

Create custom context objects extending `RequestContext`:

```java
package {base-package}.model.request;

import com.barclays.api.bap.bld.lib.payload.request.RequestContext;
import org.springframework.web.context.request.WebRequest;

public class InternalRequestContext extends RequestContext {
    
    public InternalRequestContext(WebRequest request) {
        super(request);
    }
    
    public String getCorrelationId() {
        return get("Correlation-ID");
    }
    
    public String getClientId() {
        return get("x-client-id");
    }
}
```

**Usage in Controller:**
```java
@GetMapping("/resource/{id}")
public Response getResource(@PathVariable String id, InternalRequestContext context) {
    String correlationId = context.getCorrelationId();
    // ... business logic
}
```

### 2. Building Success Responses

```java
@GetMapping("/persons/{id}")
public Response getPerson(@PathVariable String id) {
    Person person = personService.findById(id);
    Resource<Person> resource = new Resource<>(id, "persons", person);
    
    Map<String, Object> meta = new HashMap<>();
    meta.put("recordCount", 1);
    
    return RestResponse.assemble()
        .withStatus(ResponseHttpStatus.OK)
        .withData(resource)
        .withMeta(meta)
        .build();
}
```

### 3. Building Error Responses

```java
@PostMapping("/persons")
public Response createPerson(@RequestBody Request request) {
    try {
        Person person = request.getData(Person.class);
        // ... validation
    } catch (ValidationException e) {
        Message error = new Message("VALIDATION_ERROR", e.getMessage());
        
        return RestResponse.assemble()
            .withStatus(ResponseHttpStatus.BAD_REQUEST)
            .withErrors(Collections.singletonList(error))
            .build();
    }
}
```

### 4. Building Empty Responses

For DELETE operations returning no content:

```java
@DeleteMapping("/persons/{id}")
public Response deletePerson(@PathVariable String id) {
    personService.delete(id);
    return RestResponse.empty(ResponseHttpStatus.NO_CONTENT);
}
```

### 5. Request Body Handling

```java
@PostMapping("/resourceRequest")
public Response getResponse(@RequestBody Request request) {
    // Extract data as specific type
    Resource<Person> resource = request.getData(Resource.class);
    Person person = resource.getAttributes(Person.class);
    
    // Extract metadata
    Map<String, Object> requestMeta = request.getMeta();
    
    return RestResponse.assemble()
        .withStatus(ResponseHttpStatus.OK)
        .withData(resource)
        .build();
}
```

### 6. Data Type Handling

```java
// Single object
Person person = response.getData(Person.class);

// Generic collections
List<Person> persons = response.getData(new TypeReference<List<Person>>() {});

// Resource wrapper
Resource<Person> resource = response.getData(Resource.class);
Person person = resource.getAttributes(Person.class);

// Metadata
Map<String, Object> meta = response.getMeta();
Integer recordCount = (Integer) meta.get("recordCount");

// Errors
List<Message> errors = response.getErrors();
String errorCode = errors.get(0).getCode();
```

---

## Java Time Serializers

Supported date/time formats for responses:

| Type | Format | Example |
|---|---|---|
| LocalDate | `yyyy-MM-dd` | `2026-02-19` |
| LocalTime | `hh:mm:ss` | `10:30:00` |
| LocalDateTime | `yyyy-MM-dd'T'HH:mm:ss.SSS` | `2026-02-19T10:30:00.000` |

---

## Request Auto-Header Forwarding

Default headers automatically forwarded to downstream calls:
- `X-Scenario`
- `Correlation-ID`
- `clientId`
- `Authorization`

Configure override in `application.yml`:
```yaml
api:
  core:
    request:
      auto-headers: Header1,Header2,Header3
```

---

## RequestHandlerImpl

Default implementation of `RequestHandler`:
- Converts header `Map<String, List<String>>` to `HttpHeaders`
- Copies auto-headers from upstream to downstream if required
- Integrates with logging framework for request tracking

---

## ResponseHandlerImpl

Default implementation of `ResponseHandler`:
- Transforms `ResponseEntity` into Barclays standard `Response` (RestResponse)
- Handles error responses
- Parses JSON response body

---

## Code Generation Templates

### RestResponse Assembly Pattern

```java
// Success response with metadata
RestResponse.assemble()
    .withStatus(ResponseHttpStatus.OK)
    .withData(resourceObject)
    .withMeta(metadataMap)
    .build()

// Error response
RestResponse.assemble()
    .withStatus(ResponseHttpStatus.BAD_REQUEST)
    .withErrors(errorMessageList)
    .build()

// Empty response
RestResponse.empty(ResponseHttpStatus.NO_CONTENT)
```

---

## Response Headers

Response headers include:
- **Correlation-ID** — echoed from request for request tracing
- **Standard HTTP headers** — Content-Type, Cache-Control, Security headers

---

## Integration Checklist

- [ ] `com.barclays.api:bap-bld-lib-payload` dependency added
- [ ] Custom `RequestContext` classes created if needed
- [ ] All controller methods return `Response` via `RestResponse.assemble()`
- [ ] Request/response structures follow Barclays standard
- [ ] Java time serialization configured for date/time fields
- [ ] Auto-headers configured for downstream calls
- [ ] Error responses built with proper error structure
- [ ] Empty responses used for non-data operations (DELETE, 204)
- [ ] Correlation-ID properly echoed in responses
