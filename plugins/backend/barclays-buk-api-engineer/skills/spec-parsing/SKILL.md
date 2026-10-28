---
name: spec-parsing
description: Comprehensive guide for parsing OpenAPI 3.x specifications and extracting semantic models for code generation. Only OpenAPI 3.x is supported.
color: blue
---

> **Source:** OpenAPI 3.x specification standard (OAS 3.0.3/3.1.0) and Barclays BUK spec parsing conventions.
> **Owner:** BUK
> **Review trigger:** On OpenAPI specification standard major version update or changes to Barclays spec conventions.
> **Status:** Reviewed

# Skill: Specification Parsing

## When to Use This Skill

Use this skill when:
- Parsing OpenAPI 3.x (JSON/YAML) specifications
- Extracting endpoints, models, security schemes from OAS specs
- Validating specification structure before code generation

**Note:** Only OpenAPI 3.x is supported. RAML specifications are rejected.

## Quick Start

### Validating Format

1. **OpenAPI 3.x** (SUPPORTED): File contains `openapi: "3.x"` or `openapi: 3.x` — proceed
2. **RAML 1.0** (NOT SUPPORTED): File starts with `#%RAML 1.0` — reject with error message

### Extracting Semantic Model

From the specification, extract:
- **Endpoints**: path, method, operationId, parameters, request body, responses
- **Schemas**: name, type, fields, constraints, nullable
- **Security**: schemes and requirements
- **Errors**: error status codes and response schemas

### Type Mapping

Map specification types to Java types:
- `string` → `String`
- `string (uuid)` → `UUID`
- `string (date)` → `LocalDate`
- `string (date-time)` → `LocalDateTime`
- `integer` → `Integer`
- `integer (int64)` → `Long`
- `number` → `BigDecimal`
- `boolean` → `Boolean`
- `array` → `List<T>`
- `object` → Custom POJO

## Core Concepts

### OpenAPI 3.x Structure

```yaml
openapi: 3.0.3
info:
  title: API Title
  version: 1.0.0
paths:
  /endpoint:
    get:
      operationId: getOperation
      parameters:
        - name: id
          in: query
          schema:
            type: integer
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Response'
components:
  schemas:
    Response:
      type: object
      properties:
        id:
          type: integer
      required:
        - id
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
```

### Semantic Model

The extracted model contains:

```json
{
  "spec_type": "OAS3",
  "title": "API name",
  "version": "1.0.0",
  "base_path": "/api/v1",
  "endpoints": [
    {
      "path": "/users",
      "method": "POST",
      "operation_id": "createUser",
      "parameters": [],
      "request_body": { "schema_ref": "User" },
      "responses": [
        { "status_code": 201, "schema_ref": "User" }
      ],
      "security": ["bearerAuth"]
    }
  ],
  "schemas": [
    {
      "name": "User",
      "fields": [
        {
          "name": "id",
          "type": "integer",
          "required": true,
          "nullable": false
        }
      ]
    }
  ]
}
```

## Reference Documentation

- **oas-parsing-guide.md**: Detailed OpenAPI 3.x parsing rules
- **semantic-model-schema.md**: Complete semantic model structure
- **format-detection.md**: Format detection and validation

## Advanced Topics

- **validation-patterns.md**: Specification validation rules
- **anomaly-detection.md**: Common specification mistakes

## Lessons Learned

- **oas3-common-pitfalls.md**: Common mistakes in OpenAPI specs

---

See `references/spec-parsing/` (reference/ and advanced/ subdirectories) for detailed documentation.

## Source Attribution

**Primary sources:**
- OpenAPI 3.0.3 specification — https://spec.openapis.org/oas/v3.0.3 — field names, object structures, `$ref` resolution rules
- OpenAPI 3.1.0 specification — https://spec.openapis.org/oas/v3.1.0 — JSON Schema alignment changes
- Barclays BUK spec parsing conventions — `API Type:` field in `info.description`, `x-` extension handling, tag naming rules

**Training knowledge applied:**
- YAML and JSON parsing: multi-document files, anchor/alias resolution, block scalar styles
- OAS `$ref` pointer syntax and cross-file reference resolution
- Semantic model extraction: endpoint grouping by tag, schema flattening, `allOf`/`oneOf`/`anyOf` normalisation

**Known limitations:**
- Only OpenAPI 3.x is supported; RAML 1.0 specifications are explicitly rejected
- `$ref` resolution is limited to local files; remote HTTP `$ref` URLs are not fetched
- `allOf`/`oneOf`/`anyOf` compositions are noted but not fully merged into a flat schema — consuming agents must handle composite schema types
- OpenAPI 3.1 JSON Schema extensions (e.g., `unevaluatedProperties`) are parsed as-is but not interpreted beyond field extraction

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] Does the parsed output include all endpoints (path, method, operationId, parameters, request body, responses)?
- [ ] Are all $ref schema references resolved and inline before returning the semantic model?
- [ ] Is the spec type confirmed as OpenAPI 3.x (RAML rejected with an explicit error)?
- [ ] Are all response status codes extracted per endpoint (not just 200 — include 400, 404, 500, etc.)?
- [ ] Does the MACHINE_READABLE_ANALYSIS include both the endpoint list AND the schema/model list?
- [ ] Are security scheme definitions extracted and included in the semantic model?
