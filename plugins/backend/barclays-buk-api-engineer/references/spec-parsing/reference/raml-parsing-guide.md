---
title: RAML 1.0 Parsing Guide (DEPRECATED)
description: DEPRECATED — RAML 1.0 support has been removed. Only OpenAPI 3.x is supported. This file is retained for historical reference only.
---

> **⚠ DEPRECATED:** RAML support has been removed from the api-engineer plugin.
> Only OpenAPI 3.x (OAS) specifications are accepted.
> If you have a RAML specification, convert it to OpenAPI 3.x before using this plugin.
> This file is no longer loaded by any agent or skill.

# RAML 1.0 Parsing Guide

## Overview

This guide defines how to parse RAML 1.0 specifications and extract semantic models for code generation.

---

## Table of Contents

1. [Format Detection](#format-detection)
2. [Root-Level Structure](#root-level-structure)
3. [API Object Parsing](#api-object-parsing)
4. [Resources & Methods](#resources--methods)
5. [Types Object Parsing](#types-object-parsing)
6. [Security Schemes](#security-schemes)
7. [Semantic Model Extraction](#semantic-model-extraction)
8. [Type Mapping](#type-mapping)

---

## Format Detection

**Rule 1.1**: Identify RAML file by header

```yaml
#%RAML 1.0
title: API Title
version: 1.0.0
```

**Rule 1.2**: RAML files must start with `#%RAML 1.0`

- First line is always `#%RAML 1.0`
- If missing or different version → Not RAML 1.0

**Rule 1.3**: Alternative detection (if checking multiple files)

Look for:
- `#%RAML` header
- `baseUri:` (RAML specific)
- `resources:` or `/` path definitions
- `types:` section

---

## Root-Level Structure

```yaml
#%RAML 1.0
title: User Management API              # → title
version: 1.2.3                          # → version
baseUri: https://api.example.com/v1     # → base_path
description: API for managing users     # → description

protocols: [HTTPS]                      # → protocols
mediaType: application/json             # → default media type

documentation:
  - title: Getting Started
    content: |
      Quick start guide...

baseUriParameters:
  version:
    type: string
    required: true

types:                                  # → schemas
  User:
    type: object
    ...

securitySchemes:                        # → security
  bearerAuth:
    type: OAuth 2.0
    ...

resources:                              # → endpoints
  /users:
    get:
      ...
```

**Rule 2.1**: Extract base path from `baseUri`

```
https://api.example.com/v1 → base_path = /v1
https://api.example.com → base_path = /
```

**Rule 2.2**: Extract API metadata

- `title` → API name
- `version` → API version
- `description` → API description (optional)
- `baseUri` → base path

---

## API Object Parsing

**Rule 3.1**: Root-level properties

```yaml
#%RAML 1.0
title: API Title                # Required
version: 1.0.0                  # Required
baseUri: https://api.../v1      # Required (or in resource)
description: Description        # Optional
protocols: [HTTPS, HTTP]        # Optional (default: scheme in baseUri)
mediaType: application/json     # Optional (default: application/json)
```

Extract:
- `title` → API title
- `version` → API version
- `baseUri` → Base path/URL
- `description` → API description
- `protocols` → List of protocols (HTTP, HTTPS)
- `mediaType` → Default media type

---

## Resources & Methods

**Rule 4.1**: Resources define endpoints

```yaml
resources:
  /users:                       # → path = /users
    displayName: Users          # Human-readable name
    description: User collection
    
    get:                        # → method = GET
      displayName: List Users
      description: Get all users
      queryParameters:          # → query parameters
        limit:
          type: integer
          required: false
          default: 10
        offset:
          type: integer
          required: false
          default: 0
      responses:
        200:                    # → response status 200
          body:
            application/json:
              type: UserList    # → schema reference
        400:                    # → response status 400
          body:
            application/json:
              type: ErrorResponse
    
    /{id}:                      # → path = /users/{id}
      displayName: User by ID
      uriParameters:            # → path parameters
        id:
          type: string
          required: true
          pattern: '^\d+$'
      
      get:                      # → method = GET
        displayName: Get User
        responses:
          200:
            body:
              application/json:
                type: User
          404:
            body:
              application/json:
                type: ErrorResponse
      
      put:                      # → method = PUT
        displayName: Update User
        body:
          application/json:
            type: UpdateUserRequest
        responses:
          200:
            body:
              application/json:
                type: User
      
      delete:                   # → method = DELETE
        displayName: Delete User
        responses:
          204:                  # No content response
          404:
            body:
              application/json:
                type: ErrorResponse
    
    post:                       # → method = POST
      displayName: Create User
      body:
        application/json:
          type: CreateUserRequest
      responses:
        201:                    # Created response
          body:
            application/json:
              type: User
        400:
          body:
            application/json:
              type: ErrorResponse
```

**Rule 4.2**: Path parameters in resources

```yaml
/users/{id}:
  uriParameters:
    id:
      type: string
      required: true            # Always required for URI parameters
      description: User ID
      pattern: '^\d+$'
      example: "12345"
```

Extract per parameter:
- `name` → parameter name (from `{name}`)
- `type` → type (string, integer, etc.)
- `required` → always true for URI parameters
- `description` → description
- `pattern` → regex validation (optional)
- `example` → example value (optional)

**Rule 4.3**: Query parameters

```yaml
get:
  queryParameters:
    limit:
      type: integer
      required: false
      default: 10
      minimum: 1
      maximum: 100
      description: Max results per page
    search:
      type: string
      required: false
      minLength: 3
      maxLength: 100
```

Extract per parameter:
- `name` → parameter name
- `type` → type (string, integer, etc.)
- `required` → boolean
- `default` → default value (optional)
- `description` → description (optional)
- Constraints: `minimum`, `maximum`, `minLength`, `maxLength`, `pattern`, `enum`

**Rule 4.4**: Request body

```yaml
post:
  body:
    application/json:
      type: CreateUserRequest    # → schema reference
```

Extract:
- `type` reference → schema to use for request body
- `required` → if body is required (default: true)

**Rule 4.5**: Response codes

```yaml
responses:
  200:                          # → status code 200
    description: Success
    body:
      application/json:
        type: UserList          # → schema reference
  201:                          # → status code 201
    description: Created
    body:
      application/json:
        type: User
  400:                          # → status code 400
    description: Bad request
    body:
      application/json:
        type: ErrorResponse
  404:                          # → status code 404
    description: Not found
  500:                          # → status code 500
    description: Server error
```

Extract per response:
- Status code (200, 201, 400, 404, 500, etc.)
- Description
- Schema reference (if body present)

**Rule 4.6**: Security requirements

```yaml
get:
  securedBy: [bearerAuth]       # → security = ["bearerAuth"]
  
post:
  securedBy: [bearerAuth, apiKey]
```

Extract array of security scheme names.

---

## Types Object Parsing

**Rule 5.1**: Locate types in `types` section

```yaml
types:
  User:                                 # → schema name
    type: object                        # → type
    displayName: User
    description: User object
    properties:                         # → fields
      id:
        type: integer
        required: true
      email:
        type: string
        required: true
        pattern: '.*@.*'
      name:
        type: string
        required: false
      status:
        type: string
        enum: [active, inactive]
```

**Rule 5.2**: Extract field information

For each property:

```
{
  "name": "email",
  "type": "string",
  "required": true (if in required array or marked required),
  "nullable": false,
  "constraints": {
    "minLength": 5,
    "maxLength": 100,
    "pattern": "email regex",
    "enum": ["value1", "value2"],
    "minimum": 0,
    "maximum": 100,
    "items": { for arrays }
  }
}
```

**Rule 5.3**: Array types

```yaml
addresses:
  type: array
  items:
    type: Address             # → Reference to Address type
  minItems: 0
  maxItems: 10
```

Extract:
- Element type from `items`
- Array constraints: `minItems`, `maxItems`

**Rule 5.4**: String constraints

```yaml
name:
  type: string
  minLength: 1
  maxLength: 100
  pattern: '^[a-zA-Z\s]+$'
  enum: [active, inactive, pending]
```

**Rule 5.5**: Numeric constraints

```yaml
age:
  type: integer
  minimum: 0
  maximum: 150
  multipleOf: 1

price:
  type: number
  minimum: 0
  maximum: 999999.99
  multipleOf: 0.01
```

**Rule 5.6**: Type inheritance (using `type` reference)

```yaml
ExtendedUser:
  type: User                   # → Inherit from User
  properties:
    department:               # → Additional properties
      type: string
```

Flatten: Combine base and extended properties

**Rule 5.7**: Enums

```yaml
Status:
  type: string
  enum: [active, inactive, pending]
```

Generate Java enum:

```java
public enum Status {
    ACTIVE,
    INACTIVE,
    PENDING
}
```

---

## Security Schemes

**Rule 6.1**: Locate security schemes in `securitySchemes`

```yaml
securitySchemes:
  bearerAuth:                   # → scheme name
    type: OAuth 2.0             # → type
    describedBy:
      headers:
        Authorization:
          description: Bearer token
          type: string
          pattern: '^Bearer .+$'
      responses:
        401:
          description: Unauthorized
  
  apiKey:
    type: API Key
    describedBy:
      headers:
        X-API-Key:
          type: string
      responses:
        401:
          description: Unauthorized
  
  basicAuth:
    type: Basic Authentication
    describedBy:
      responses:
        401:
          description: Unauthorized
```

Extract per scheme:
- `name` → scheme name
- `type` → OAuth 2.0, API Key, Basic Authentication, Digest Authentication
- `describedBy.headers` → Required headers

---

## Semantic Model Extraction

### Output Structure

```json
{
  "spec_type": "RAML1",
  "format_version": "1.0",
  "title": "API Title",
  "version": "1.0.0",
  "base_path": "/api/v1",
  "endpoints": [
    {
      "path": "/users",
      "method": "GET",
      "operation_id": "getUsers",
      "summary": "List all users",
      "path_params": [],
      "query_params": [
        {
          "name": "limit",
          "type": "integer",
          "required": false,
          "constraints": { "minimum": 1, "maximum": 100 }
        }
      ],
      "request_body": null,
      "responses": [
        {
          "status_code": 200,
          "description": "Success",
          "schema_ref": "UserList"
        }
      ],
      "security": ["bearerAuth"]
    }
  ],
  "schemas": [
    {
      "name": "User",
      "type": "object",
      "fields": [
        {
          "name": "id",
          "type": "integer",
          "required": true,
          "nullable": false,
          "constraints": {}
        },
        {
          "name": "email",
          "type": "string",
          "required": true,
          "nullable": false,
          "constraints": { "pattern": "email" }
        }
      ]
    }
  ],
  "security_schemes": [
    {
      "name": "bearerAuth",
      "type": "OAuth 2.0"
    }
  ],
  "error_shapes": [
    {
      "status_code": 400,
      "schema_ref": "ErrorResponse"
    }
  ]
}
```

---

## Type Mapping

### RAML Type → Java Type

| RAML Type | Java Type | Notes |
|-----------|-----------|-------|
| string | String | Standard string |
| string (email) | String | With @Email |
| string (uuid) | UUID | Import java.util.UUID |
| string (date-only) | LocalDate | ISO 8601 date |
| string (datetime) | LocalDateTime | ISO 8601 datetime |
| string (time-only) | LocalTime | ISO 8601 time |
| integer | Integer | 32-bit |
| integer (int64) | Long | 64-bit |
| number | BigDecimal | Decimal numbers |
| boolean | Boolean | true/false |
| array | List<ElementType> | Collections |
| object | Custom POJO | Model class |

---

## Extraction Checklist

Before returning semantic model:

- [ ] All resources extracted (resources section)
- [ ] All methods captured (GET, POST, PUT, DELETE, PATCH)
- [ ] All URI parameters extracted
- [ ] All query parameters extracted
- [ ] All request bodies captured
- [ ] All responses with status codes captured
- [ ] All types extracted (types section)
- [ ] All fields with types extracted
- [ ] All constraints captured
- [ ] Security schemes identified
- [ ] Error response shapes mapped
- [ ] No circular type references
- [ ] All type references valid

---

## Common Issues & Resolution

**Issue**: Type references not found
- **Cause**: Reference points to non-existent type
- **Fix**: Validate all type references exist in types section

**Issue**: Missing required fields
- **Cause**: Type definition incomplete
- **Fix**: Warn user, mark as incomplete

**Issue**: Circular type references
- **Cause**: Type A references B, B references A
- **Fix**: Break circular reference with base type or interface

**Issue**: Ambiguous response type
- **Cause**: Multiple media types in response
- **Fix**: Use first media type (typically application/json) or generate union

**Issue**: Missing operationId
- **Cause**: Not automatically generated in RAML
- **Fix**: Generate from method + path (GET /users → getUsers)

---

## RAML vs OAS Differences

| Aspect | RAML | OAS |
|--------|------|-----|
| Header | `#%RAML 1.0` | `openapi: 3.x.x` |
| Endpoints | `resources` section | `paths` section |
| Schemas | `types` section | `components.schemas` |
| Parameters | `uriParameters`, `queryParameters` | `parameters` |
| Security | `securitySchemes`, `securedBy` | `components.securitySchemes`, `security` |
| Root | Has `baseUri` | Has `servers` |
| Type Inheritance | Via `type:` reference | Via `allOf` |

---

**Version**: 1.0.0  
**Authority**: Organization RAML parsing standard
