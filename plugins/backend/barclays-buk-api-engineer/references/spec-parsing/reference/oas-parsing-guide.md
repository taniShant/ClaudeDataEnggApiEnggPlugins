---
title: OpenAPI 3.x Parsing Guide
description: Authoritative rules for parsing OpenAPI 3.0/3.1 specifications and extracting semantic models
---

# OpenAPI 3.x Parsing Guide

## Overview

This guide defines how to parse OpenAPI 3.x (3.0.x and 3.1.x) specifications and extract semantic models for code generation.

---

## Table of Contents

1. [Format Detection](#format-detection)
2. [Root-Level Structure](#root-level-structure)
3. [Info Object Parsing](#info-object-parsing)
4. [Paths Object Parsing](#paths-object-parsing)
5. [Schema/Components Parsing](#schemacomponents-parsing)
6. [Security Parsing](#security-parsing)
7. [Semantic Model Extraction](#semantic-model-extraction)
8. [Type Mapping](#type-mapping)

---

## Format Detection

**Rule 1.1**: Identify OpenAPI file by header

```yaml
# OpenAPI 3.0.x
openapi: 3.0.0
openapi: 3.0.1
openapi: 3.0.2
openapi: 3.0.3

# OpenAPI 3.1.x
openapi: 3.1.0
openapi: 3.1.1
```

**Rule 1.2**: Alternative detection (if header missing)

Look for:
- `paths:` (OAS specific)
- `components:` (OAS 3.x specific)
- `servers:` (OAS specific structure)

---

## Root-Level Structure

```yaml
openapi: 3.0.3
info:
  title: API Title
  version: 1.0.0
  description: API description
servers:
  - url: https://api.example.com/v1
    description: Production
  - url: https://staging-api.example.com/v1
    description: Staging
paths:
  /resources:
    get:
      summary: List resources
      operationId: listResources
      ...
components:
  schemas:
    Resource:
      type: object
      ...
  securitySchemes:
    bearerAuth:
      type: http
      ...
```

**Rule 2.1**: Extract base path from `servers[0].url`

```
https://api.example.com/v1 → base_path = /v1
```

**Rule 2.2**: If no servers, default base path is `/`

---

## Info Object Parsing

**Rule 3.1**: Extract API metadata

```yaml
info:
  title: User Management API       # → title
  version: 1.2.3                   # → version
  description: Manage users        # → description (optional)
  contact:
    name: Support Team
    url: https://support.example.com
    email: support@example.com
```

Extract:
- `title` → API name
- `version` → API version
- `description` → API description (optional)

---

## Paths Object Parsing

**Rule 4.1**: Extract endpoints from `paths`

```yaml
paths:
  /users:                    # → path
    get:                     # → method (GET)
      operationId: listUsers # → operation_id
      summary: List all users
      description: Retrieve list of all users
      parameters: [...]      # → parameters
      requestBody: [...]     # → request_body
      responses: [...]       # → responses
      security: [...]        # → security
```

**Rule 4.2**: Path parameters (in curly braces)

```yaml
/users/{id}:           # → path = /users/{id}
  get:
    parameters:
      - name: id       # → parameter name
        in: path       # → location (path, query, header, cookie)
        required: true # → required
        schema:
          type: integer
          format: int32
          minimum: 1
          maximum: 2147483647
```

Extract parameters:
- `name` → parameter name
- `in` → location (path, query, header, cookie)
- `required` → boolean
- `schema` → type, constraints, format

**Rule 4.3**: Query parameters

```yaml
/users:
  get:
    parameters:
      - name: limit
        in: query
        required: false
        schema:
          type: integer
          default: 10
          minimum: 1
          maximum: 100
      - name: offset
        in: query
        required: false
        schema:
          type: integer
          default: 0
      - name: search
        in: query
        required: false
        schema:
          type: string
          maxLength: 100
```

**Rule 4.4**: Request body parsing

```yaml
requestBody:
  required: true           # → required
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/CreateUserRequest'  # → schema_ref
```

Extract:
- `required` → boolean
- `content.application/json.schema.$ref` → schema reference

**Rule 4.5**: Response parsing

```yaml
responses:
  '200':                   # → status_code = 200
    description: Success
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/User'  # → schema_ref
  '400':
    description: Bad request
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/ErrorResponse'
  '401':
    description: Unauthorized
  '500':
    description: Server error
```

Extract per response:
- Status code (from key: '200', '400', etc.)
- Description
- Schema reference (if body present)

**Rule 4.6**: Security requirements

```yaml
security:
  - bearerAuth: []  # → security = ["bearerAuth"]
  - apiKey: []
```

Extract array of security scheme names.

---

## Schema/Components Parsing

**Rule 5.1**: Locate schemas in `components.schemas`

```yaml
components:
  schemas:
    User:                              # → schema name
      type: object                     # → type
      description: User object
      required:                        # → required fields
        - id
        - email
      properties:                      # → fields
        id:
          type: integer
          format: int64
        email:
          type: string
          format: email
        name:
          type: string
          nullable: true               # → nullable
        status:
          type: string
          enum: [active, inactive]     # → enum
```

**Rule 5.2**: Extract field information

For each property:

```
{
  "name": "email",
  "type": "string",
  "format": "email",
  "required": true (if in required array),
  "nullable": false,
  "constraints": {
    "minLength": 5,
    "maxLength": 100,
    "pattern": "email regex",
    "enum": ["value1", "value2"],
    "minimum": 0,
    "maximum": 100,
    "minItems": 1,
    "maxItems": 10
  }
}
```

**Rule 5.3**: Array types

```yaml
addresses:
  type: array
  items:
    $ref: '#/components/schemas/Address'
  minItems: 0
  maxItems: 10
```

Extract:
- Element type from `items`
- Array constraints: `minItems`, `maxItems`

**Rule 5.4**: Nested objects

```yaml
UserWithProfile:
  type: object
  properties:
    id:
      type: integer
    profile:
      type: object               # → Inline object (create named schema or inline)
      properties:
        bio:
          type: string
        avatar:
          type: string
```

Options:
1. Inline: Keep as nested object in model
2. Extract: Create separate schema and reference

**Recommendation**: Extract as separate schema for reusability

**Rule 5.5**: Enums

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

**Rule 5.6**: Inheritance (allOf)

```yaml
ExtendedUser:
  allOf:
    - $ref: '#/components/schemas/User'
    - type: object
      properties:
        department:
          type: string
```

Flatten: Combine base and extended properties

---

## Security Parsing

**Rule 6.1**: Locate security schemes in `components.securitySchemes`

```yaml
components:
  securitySchemes:
    bearerAuth:                    # → scheme name
      type: http                   # → type
      scheme: bearer               # → scheme value
      bearerFormat: JWT            # → bearer format
    apiKey:
      type: apiKey
      in: header
      name: X-API-Key
    oauth2:
      type: oauth2
      flows:
        authorizationCode:
          authorizationUrl: https://example.com/oauth/authorize
          tokenUrl: https://example.com/oauth/token
          scopes:
            read: Read access
            write: Write access
```

Extract per scheme:
- `name` → scheme name
- `type` → http, apiKey, oauth2, openIdConnect
- `scheme` → bearer, basic, etc. (for http type)
- `bearerFormat` → JWT, etc.

---

## Semantic Model Extraction

### Output Structure

```json
{
  "spec_type": "OAS3",
  "format_version": "3.0.3",
  "title": "API Title",
  "version": "1.0.0",
  "base_path": "/api/v1",
  "endpoints": [
    {
      "path": "/users",
      "method": "GET",
      "operation_id": "listUsers",
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
    },
    {
      "path": "/users",
      "method": "POST",
      "operation_id": "createUser",
      "path_params": [],
      "query_params": [],
      "request_body": {
        "schema_ref": "CreateUserRequest",
        "required": true
      },
      "responses": [
        {
          "status_code": 201,
          "description": "User created",
          "schema_ref": "User"
        },
        {
          "status_code": 400,
          "description": "Bad request",
          "schema_ref": "ErrorResponse"
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
          "constraints": { "format": "email" }
        }
      ]
    }
  ],
  "security_schemes": [
    {
      "name": "bearerAuth",
      "type": "http",
      "scheme": "bearer",
      "bearer_format": "JWT"
    }
  ],
  "error_shapes": [
    {
      "status_code": 400,
      "schema_ref": "ErrorResponse"
    },
    {
      "status_code": 500,
      "schema_ref": "ErrorResponse"
    }
  ]
}
```

---

## Type Mapping

### OpenAPI Type → Java Type

| OAS Type | Format | Constraints | Java Type |
|----------|--------|-------------|-----------|
| string | - | - | String |
| string | email | - | String (with @Email) |
| string | uuid | - | UUID |
| string | date | - | LocalDate |
| string | date-time | - | LocalDateTime |
| string | byte | - | byte[] |
| string | binary | - | byte[] |
| string | - | enum | Enum |
| number | - | - | BigDecimal |
| number | float | - | Float |
| number | double | - | Double |
| integer | - | - | Integer |
| integer | int32 | - | Integer |
| integer | int64 | - | Long |
| integer | - | - | Integer |
| boolean | - | - | Boolean |
| array | - | - | List<ElementType> |
| object | - | - | Custom POJO |
| null | - | - | null |

### Validation Constraints Mapping

| OAS Constraint | Java Annotation |
|----------------|-----------------|
| required: true | @NotNull |
| maxLength | @Size(max=...) |
| minLength | @Size(min=...) |
| maximum | @Max(...) |
| minimum | @Min(...) |
| exclusiveMaximum | Custom validator |
| exclusiveMinimum | Custom validator |
| pattern | @Pattern(...) |
| enum | Use Java enum |
| items.minItems | @Size(min=...) on collection |
| items.maxItems | @Size(max=...) on collection |
| format: email | @Email |
| nullable: true | @Nullable (optional field) |

---

## Extraction Checklist

Before returning semantic model:

- [ ] All endpoints extracted (paths section)
- [ ] All methods captured (GET, POST, PUT, PATCH, DELETE)
- [ ] All parameters extracted (path, query, header)
- [ ] All request bodies captured
- [ ] All responses with status codes captured
- [ ] All schemas extracted (components.schemas)
- [ ] All fields with types extracted
- [ ] All constraints captured
- [ ] Security schemes identified
- [ ] Error response shapes mapped
- [ ] No circular schema references
- [ ] All schema references valid

---

## Common Issues & Resolution

**Issue**: Schema references not found
- **Cause**: Reference points to non-existent schema
- **Fix**: Validate all `$ref` point to existing schemas

**Issue**: Missing required fields in response
- **Cause**: Response schema incomplete in spec
- **Fix**: Warn user, mark as incomplete

**Issue**: Circular schema references
- **Cause**: Schema A references B, B references A
- **Fix**: Break circular reference with interface or polymorphism

**Issue**: Missing operationId
- **Cause**: Endpoint doesn't specify operationId
- **Fix**: Generate from method + path (e.g., GET /users → getUsers)

---

**Version**: 1.0.0  
**Authority**: Organization OpenAPI parsing standard
