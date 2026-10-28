# OAS3 Specification Migration Guide (MCA1 to MCA2)

## Overview

MCA2 applications require an OpenAPI 3.0.2 specification that serves as both documentation and a runtime validation layer. During migration, the agent must either:

1. **Migrate an existing MCA1 OAS spec** to MCA2 format, OR
2. **Generate a new MCA2 OAS spec** from the migrated controllers when no spec exists

The OAS spec is validated at runtime by `mca-eps-core` when `core.default.oas.enabled=true`.

## Target Directory Structure

```
oas/
├── openapi.yaml                    # Main OAS 3.0.2 specification
├── common-libraries/               # Shared MCA2 components (DO NOT MODIFY)
│   ├── components/
│   │   ├── mca-iol-headers.yaml    # MCA2 IOL context headers (X-UserContext, etc.)
│   │   ├── headers.yaml            # Standard HTTP headers (Correlation-ID, etc.)
│   │   ├── response-types.yaml     # ErrorResponseType + ErrorType schemas
│   │   └── responses.yaml          # Standard error responses (400-503)
│   ├── examples/
│   │   ├── example-error-400-bad-request.json
│   │   ├── example-error-401.json
│   │   ├── example-error-403.json
│   │   ├── example-error-404.json
│   │   ├── example-error-429.json
│   │   ├── example-error-500.json
│   │   └── example-error-503.json
│   └── security/
│       └── security-schemes.yaml
├── components/                     # Project-specific components (GENERATE)
│   ├── models.yaml                 # Request/response schemas from Java DTOs
│   ├── content-models.yaml         # Response<T> wrapper models
│   ├── requests.yaml               # Request body definitions
│   └── responses.yaml              # Success response definitions
└── examples/                       # Request/response JSON examples (GENERATE)
    ├── <OperationName>Request.json
    └── <OperationName>Response.json
```

## MCA1 vs MCA2 OAS Differences

### Header Migration

| MCA1 Header | MCA2 Header | Format Change |
|---|---|---|
| `UserContextHeader` (comma-delimited) | `X-UserContext` (structured JSON object) | Flat string -> typed object with UID, BUID, EID, channel, etc. |
| `AccountContextHeader` (JSON string) | `X-AccountContext` (structured JSON object) | String -> typed object with displayName, number, sortCode, etc. |
| `AccountListHeader` (JSON string) | `X-AccountList` (structured JSON object) | String -> typed object with accounts array |
| `CustomerContextHeader` (JSON string) | `X-CustomerContext` (structured JSON object) | String -> typed object with identifiers, details |
| `SecureContextHeader` (JSON string) | `X-SecureContext` (string) | Similar |
| `ConfigDataHeader` | (removed) | Config now in application.properties |
| `PreferenceContextHeader` | (removed) | Handled differently in MCA2 |
| `LanguageHeader` | `X-LocaleContext` | Simple string -> JSON object with lang |
| `ThirdPartyContextHeader` | `X-CallerContext` | Renamed with structured schema |
| (not present) | `X-AID` | New - Application ID header |
| (not present) | `X-SystemContext` | New - Session/Process/Tagging IDs |
| (not present) | `X-ProcessContext` | New - Business process key-value pairs |
| (not present) | `X-DeviceContext` | New - Device information |
| (not present) | `X-CaseContext` | New - Case identifiers |

### Error Response Model Migration

**MCA1: `EpsResponseBean` + `EpsMessageBean`**
```yaml
EpsResponseBean:
  properties:
    fatalError: boolean
    messages:
      items:
        EpsMessageBean:
          properties:
            code: string          # e.g., "000000"
            text: string          # Human-readable
            type: enum [F,E,W,I,S]
            lineNumber: integer
            exceptionCode: string
            buildVersion: string
            appName: string
            correlationId: string
```

**MCA2: `ErrorResponseType` + `ErrorType`**
```yaml
ErrorResponseType:
  properties:
    errors:
      items:
        ErrorType:
          required: [id, code, title]
          properties:
            id: string            # Request-specific ID
            code: string          # e.g., "ACCOUNT_NUMBER_NOT_FOUND"
            title: string         # Short description
            detail: string        # Low-level troubleshooting
            severity: enum [S,I,W,E]
            meta: object          # Extensible metadata
```

### Standard Error Responses

| MCA1 | MCA2 |
|---|---|
| 400 BadRequest | 400 BadRequest |
| 401 Unauthorized | 401 Unauthorized |
| (not standard) | 403 Forbidden |
| 404 NotFound | 404 NotFound |
| (not standard) | 429 TooManyRequests |
| 500 InternalServerError | 500 InternalServerError |
| (not standard) | 503 ServiceUnavailable |

### Model Naming Convention

| MCA1 | MCA2 |
|---|---|
| `GenericAuditRequestBean` | `AuditRequest` (drop `Bean` suffix) |
| `AuditResponseBean` | `AuditResponse` (drop `Bean` suffix) |
| Content model reuses `*Bean` name | Content model uses `Get*Response` / `Update*Response` |

### Security Scheme

Both use `InternalTiaaRopcAuth` via `OAuthHeader`. The definition is identical in both `mca-headers.yaml` (MCA1) and `mca-iol-headers.yaml` (MCA2).

### Response Wrapper Pattern

**MCA1:** Response beans may include `fatalError` + `messages` fields alongside business data.

**MCA2:** Responses wrapped in `Response<T>` with a `data` property containing the business object:
```yaml
GetResourceResponse:
  type: object
  properties:
    data:
      $ref: './models.yaml#/ResourceResponse'
```

## Step-by-Step: Migrate Existing MCA1 OAS

When the source MCA1 project has an `oas/` directory:

### 1. Copy common-libraries
Replace the MCA1 `common-libraries/` directory with the MCA2 version. The MCA2 common-libraries are available as a template at:
`reference/oas-template/common-libraries/`

### 2. Update openapi.yaml

| Section | MCA1 | MCA2 |
|---|---|---|
| `info.title` | Keep (update if app renamed) | Same |
| `servers[0].url` | `http://localhost:9998/eps{name}` | `http://localhost:9998/{mca2-name}` |
| `components.securitySchemes` | `$ref: './common-libraries/components/mca-headers.yaml#/...'` | `$ref: './common-libraries/components/mca-iol-headers.yaml#/...'` |
| `components.schemas` | (often empty) | Add IOL schema refs: UserContext, AccountContext, CustomerContext, etc. |
| `components.parameters` | `UserContextHeader`, `AccountContextHeader` | `X-SystemContext`, `X-UserContext`, `X-AID` |
| `components.responses` | 400, 401, 404, 500 | 400, 401, 403, 404, 429, 500, 503 |
| `paths.*.parameters` | MCA1 headers (`UserContextHeader`, `AccountContextHeader`, etc.) | MCA2 headers (`Correlation-ID`, `X-AID`, `X-SystemContext`, `X-UserContext`) |

### 3. Migrate components/models.yaml
- Remove `Bean` suffix from all model names
- Update model schemas if DTOs changed during code migration
- Add `additionalProperties: false` where not present
- Ensure all string properties have `pattern`, `minLength`, `maxLength`

### 4. Migrate components/content-models.yaml
- Rename to match MCA2 convention: `Get*Response`, `Update*Response`, `Create*Response`
- Ensure each wraps the model in a `data` property

### 5. Migrate components/requests.yaml
- Update `$ref` paths to point to renamed models
- Update examples path

### 6. Migrate components/responses.yaml
- Update `$ref` paths to point to renamed content-models
- Add error responses (403, 429, 503) referencing common-libraries

### 7. Update/create examples/
- Ensure response examples follow the `{ "data": { ... } }` wrapper pattern
- Create any missing examples

## Step-by-Step: Generate New MCA2 OAS

When the source MCA1 project has NO `oas/` directory:

### 1. Create oas/ directory structure
Copy the full template from `reference/oas-template/`.

### 2. Analyze migrated controllers
For each controller class, extract:
- `@RequestMapping` base path
- Each `@GetMapping`/`@PostMapping`/`@PutMapping`/`@DeleteMapping` with:
  - HTTP method
  - Path
  - `@RequestBody` type (for request schema)
  - Return type `Response<T>` (for response schema)
  - `operationId` derived from method name

### 3. Generate openapi.yaml
- Set `info.title` from `spring.application.name`
- Set `servers[0].url` from context path
- Define a `tag` for each controller or endpoint group
- For each endpoint, create a `paths` entry with:
  - Standard MCA2 IOL header parameters (Correlation-ID, X-AID, X-SystemContext, X-UserContext)
  - Request body reference (for POST/PUT)
  - Success response reference
  - Standard error response references (400, 401, 403, 404, 429, 500, 503)

### 4. Generate components/models.yaml
For each request/response DTO:
- Map Java types to OAS types:
  - `String` -> `type: string` with pattern/length constraints
  - `Integer`/`int` -> `type: integer` with min/max
  - `Long`/`long` -> `type: integer, format: int64`
  - `Boolean`/`boolean` -> `type: boolean`
  - `List<T>` -> `type: array, items: { $ref: T }`
  - `Map<String, Object>` -> `type: object, additionalProperties: true`
  - `BigDecimal` -> `type: number, format: double`
  - `LocalDate` -> `type: string, format: date`
  - `LocalDateTime` -> `type: string, format: date-time`
- Add `required` array for fields annotated with `@NotNull`/`@NotBlank`
- Add `pattern` from `@Pattern` annotations or derive sensible defaults
- Add `example` values from test data or sensible defaults

### 5. Generate components/content-models.yaml
For each response model, create a wrapper:
```yaml
Get{Resource}Response:
  type: object
  nullable: false
  deprecated: false
  properties:
    data:
      $ref: './models.yaml#/{ResourceResponse}'
```

### 6. Generate components/requests.yaml
For each POST/PUT endpoint:
```yaml
{OperationName}Request:
  description: {description}
  required: true
  content:
    application/json:
      schema:
        $ref: './models.yaml#/{RequestModel}'
      examples:
        {exampleName}:
          $ref: '../examples/{OperationName}Request.json'
```

### 7. Generate components/responses.yaml
For each endpoint:
```yaml
{OperationName}Response:
  description: Success response
  content:
    application/json:
      schema:
        $ref: './content-models.yaml#/{ContentModel}'
      examples:
        successResponse:
          $ref: '../examples/{OperationName}Response.json'
```

### 8. Generate examples/
Create JSON examples for each request and response, using realistic test data:
```json
{
  "value": {
    "data": {
      "field1": "example_value",
      "field2": 12345
    }
  }
}
```

## build.gradle Integration

Add OAS files to the runtime classpath for validation:

```gradle
bootRun {
    classpath += files("${projectDir}/oas/")
    jvmArgs = [
        "-Dspring.profiles.active=dev",
        // ... other args
    ]
}
```

## application.properties for OAS Validation

Add to `application-dev.properties` (or environment-specific):
```properties
core.default.oas.enabled=true
core.default.oas.blockingMode=true
core.default.oas.ignoreMissingSchema=false
core.default.oas.path=classpath:openapi.yaml
```

## Validation Checklist

After OAS generation/migration:
- [ ] `openapi.yaml` uses version `3.0.2`
- [ ] All `$ref` paths in common-libraries point to `mca-iol-headers.yaml` (not `mca-headers.yaml`)
- [ ] All path parameters use MCA2 IOL headers (X-UserContext, X-AID, X-SystemContext)
- [ ] No MCA1 header references remain (UserContextHeader, AccountContextHeader, etc.)
- [ ] Error responses include 400, 401, 403, 404, 429, 500, 503
- [ ] All response content-models wrap data in `data` property
- [ ] Model names do not have `Bean` suffix
- [ ] Every request/response has a valid JSON example
- [ ] `components.schemas` includes IOL context type references
- [ ] Every endpoint has an `operationId`
- [ ] OAS validation passes when app starts with `core.default.oas.enabled=true`
