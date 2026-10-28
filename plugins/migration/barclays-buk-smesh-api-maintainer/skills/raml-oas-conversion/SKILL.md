---
name: raml-oas-conversion
description: Complete guide for converting RAML 1.0 specifications to OpenAPI 3.0.3 for Barclays Internal API projects.
owner: Barclays AI (barclaysai@barclays.com)
version: 1.0.0
license: Proprietary. For Barclays internal use only.
color: blue
user-invocable: false
source: barclays-claude-code-plugins/plugins/sdk3-migration/skills/raml_oas_conversion/SKILL.md
owner: Barclays AI (barclaysai@barclays.com)
review-trigger: When SDK3 BOM versions change or new migration patterns are identified
status: Full
---

# RAML to OpenAPI Specification Conversion Guide

## Overview

This guide helps convert Barclays Internal API specifications from RAML 1.0 to OpenAPI 3.0.3. OpenAPI is the industry standard for API specifications and provides better tooling support, SDK3 compatibility, and auto-generated documentation.

**Key Benefits:**
- **Industry Standard**: OpenAPI is more widely adopted and supported
- **Better Tooling**: Swagger UI, Postman, code generators
- **SDK3 Compatibility**: Native support in Barclays SDK3 with `barclaysApiGenerate` task
- **Interactive Documentation**: Auto-generated API documentation

## Related Documentation

- [Conversion Patterns Reference](conversion-patterns.md) - Detailed mapping patterns for all RAML constructs, including type constraints, reference resolution, example extraction, and RAML constraint preservation policy
- [Validation Guide](validation-guide.md) - Comprehensive validation and testing procedures, including HTTP validator integration, anomaly analysis, auto-fix rules, and validation fix loop

## Validation Scripts

The following scripts are used by the `/raml-to-oas` command for automated validation:

- **`oas-validator.py`** - HTTP client for the Barclays OAS Validator endpoint (`oasvalidator.barclays.intranet`). Creates ZIP of OAS files, sends for validation, returns JSON with severity-categorized issues. Located at `scripts/oas-validator.py` in the plugin directory (resolved via `$SCRIPT_DIR` set in command Step 0).
- **`analyze_oas_anomalies.py`** - Local constraint anomaly analyzer. Checks string properties (maxLength+minLength+pattern/enum), numeric bounds, and regex E-02-02 compliance. Outputs `openapi-anomalies.md`. Located at `scripts/analyze_oas_anomalies.py` in the plugin directory (resolved via `$SCRIPT_DIR`).

## Quick Start

### Command Usage

Use the `/raml-to-oas` command to convert RAML specifications:

```bash
/raml-to-oas [RAML_PATH] [--output OAS_PATH] [--template TEMPLATE_PATH] [--api-owner-business NAME:EMAIL] [--api-owner-technical NAME:EMAIL] [--validate-only]
```

**Parameters:**
- `RAML_PATH` - Path to RAML folder (default: auto-detect `src/main/resources/raml` or `./raml`)
- `--output` - Output path for OAS (default: `src/main/resources/oas`)
- `--template` - Path to OAS template (default: cached at `{PROJECT_ROOT}/.claude/cache/oas-template/oas`)
- `--api-owner-business` - Business owner in format `"Name:email"` (optional, extracted from doc-api.md)
- `--api-owner-technical` - Technical owner in format `"Name:email"` (optional, extracted from doc-api.md)
- `--validate-only` - Only validate existing OAS (default: `false`)

**Examples:**
```bash
# Basic conversion with API owners
/raml-to-oas ./raml --api-owner-business "John Doe:john.doe@barclays.com" --api-owner-technical "Jane Smith:jane.smith@barclays.com"

# Full example
/raml-to-oas ./src/main/resources/raml --output ./src/main/resources/oas --api-owner-business "Pradeep, Radhika:radhika.pradeep@barclays.com" --api-owner-technical "Kachare, Ashwini:ashwini.chaitanyakachare@barclays.com"
```

### OAS Template

The Barclays OAS template is automatically cloned and cached:

- **Repository**: `git@app.gitlab.barcapint.com:barclays/B2B-API-Interfaces/oas-template.git`
- **Cache location**: `{PROJECT_ROOT}/.claude/cache/oas-template/`
- **Provides**: `common-libraries/` directory with standard headers, error responses, security schemes, and error examples
- The template is cloned once and reused for subsequent conversions

### Metadata Extraction from doc-api.md

The command automatically reads `{RAML_PATH}/docs/doc-api.md` to extract API metadata:
- API Type, Risk Classification, Business Owner, Tech Owner, Overview
- CLI parameters (`--api-owner-business`, `--api-owner-technical`) override doc-api.md values
- See [conversion-patterns.md](conversion-patterns.md#metadata-extraction-from-doc-apimd) for field mapping details

### RAML Constraint Preservation Policy

During conversion and subsequent validation fixes, RAML constraints take absolute precedence:
- If RAML defines `enum` -> keep `enum` ONLY (do NOT add `pattern`)
- If RAML defines `pattern` -> keep `pattern` ONLY
- Never derive constraints from RAML `examples`
- See [conversion-patterns.md](conversion-patterns.md#raml-constraint-preservation-policy) for full policy

## Folder Structure (Canonical Reference)

All other skill files reference this section as the single source of truth for folder layout.

**RAML Structure (Typical):**
```
raml/
├── api.raml                      # Root RAML file
├── types/                        # Data type definitions
│   ├── type-*.raml
├── traits/                       # Reusable traits (headers, responses)
│   ├── trait-*.raml
├── libs/                         # Resource libraries
│   ├── libs-*.raml
├── common-libraries/             # Shared components
│   ├── types/
│   ├── security-schemes/
│   └── traits/
└── examples/                     # JSON examples
    └── example-*.json
```

**OpenAPI Structure (Barclays Template - MUST FOLLOW):**
```
oas/
├── openapi.yaml                           # Root OpenAPI file
├── common-libraries/                      # Shared components (DO NOT MODIFY)
│   ├── components/
│   │   ├── headers.yaml                   # Standard HTTP headers
│   │   ├── responses.yaml                 # Standard error responses
│   │   └── response-types.yaml            # Error response types
│   ├── examples/
│   │   ├── example-error-400.json         # Bad Request
│   │   ├── example-error-401.json         # Unauthorized
│   │   ├── example-error-403.json         # Forbidden
│   │   ├── example-error-404.json         # Not Found
│   │   ├── example-error-429.json         # Too Many Requests
│   │   ├── example-error-500.json         # Internal Server Error
│   │   └── example-error-503.json         # Service Unavailable
│   └── security/
│       └── security-schemes.yaml          # OAuth2 security scheme
├── components/
│   ├── parameters.yaml                    # All path/query parameters
│   ├── common/                            # Shared schemas across endpoints
│   │   ├── schema-Guid.yaml
│   │   └── schema-*.yaml
│   └── {endpointName}/                    # Endpoint-specific folder
│       ├── request-body/                  # Request schemas
│       │   └── schema-*.yaml
│       ├── response-body/                 # Response schemas
│       │   └── schema-*.yaml
│       ├── request-{EndpointName}Request.yaml   # Request definition
│       └── response-{EndpointName}Response.yaml # Response definition
└── examples/                              # API-specific JSON examples
    └── *.json
```

**Key Rules:**
- `common-libraries/` contains standard files - copy from template, do not modify
- Each endpoint gets its own folder under `components/`
- Separate `request-body/` and `response-body/` subfolders
- NO `types/` or `libs/` folders in OAS structure
- Parameters go in `components/parameters.yaml`, not inline

## Core Conversion Mappings

| RAML Concept | OpenAPI Equivalent | Barclays Template Location |
|--------------|-------------------|---------------------------|
| **Root File** | `api.raml` -> `openapi.yaml` | `oas/openapi.yaml` |
| **Traits (headers)** | `parameters` references | `common-libraries/components/headers.yaml` |
| **Traits (query/path)** | `parameters` in components | `components/parameters.yaml` |
| **Types** | `schemas` in endpoint folders | `components/{endpoint}/response-body/` |
| **Common Types** | Shared schemas | `components/common/` |
| **Security Schemes** | `securitySchemes` reference | `common-libraries/security/` |
| **Error Responses** | Common responses | `common-libraries/components/responses.yaml` |
| **Examples** | `externalValue` or `value` | `examples/` or `common-libraries/examples/` |

For detailed type mappings, header rules, and conversion patterns, see [conversion-patterns.md](conversion-patterns.md).

## File Naming Conventions

| Component | File Name Pattern | Location |
|-----------|------------------|----------|
| Root file | `openapi.yaml` | `oas/` |
| Parameters | `parameters.yaml` | `components/` |
| Common schema | `schema-{Name}.yaml` | `components/common/` |
| Response definition | `response-{Endpoint}Response.yaml` | `components/{endpoint}/` |
| Request definition | `request-{Endpoint}Request.yaml` | `components/{endpoint}/` |
| Response body schema | `schema-{Name}.yaml` | `components/{endpoint}/response-body/` |
| Request body schema | `schema-{Name}.yaml` | `components/{endpoint}/request-body/` |
| Error examples | `example-error-{code}.json` | `common-libraries/examples/` |
| API examples | `{descriptive-name}.json` | `examples/` |

## Integration with SDK3

### Update gradle.properties

```properties
# RAML (old)
# JAR_FILE=src/main/resources/raml/api.raml

# OpenAPI (new)
JAR_FILE=src/main/resources/oas/openapi.yaml
```

### Run Code Generation

```bash
$GRADLE_CMD barclaysApiGenerate
```

Use Glob tool with pattern `build/generated/sources/src/main/java/**/*.java` to verify generated sources exist.

```bash
$GRADLE_CMD compileJava
```

## Conversion Strategy

### Phase 1: Setup Structure
1. Copy common-libraries folder from OAS template
2. Create components folder structure
3. Create examples folder
4. Copy example JSON files from RAML

### Phase 2: Convert Components
1. Create components/parameters.yaml with all path/query parameters
2. Create components/common/ with shared schemas
3. Create endpoint folders with request-body/ and response-body/
4. Convert RAML types to schema files

### Phase 3: Create Response/Request Definitions
1. Create response-{Endpoint}Response.yaml for each endpoint
2. Create request-{Endpoint}Request.yaml for POST/PUT endpoints
3. Include proper headers (Cache-Control, Content-Type, Correlation-ID-Response)
4. Reference schemas from response-body/ or request-body/

### Phase 4: Create openapi.yaml
1. Use template format for info section
2. Add externalDocs
3. Configure empty server URL
4. Add security scheme reference
5. Define all paths with $ref to response/request files
6. Add all error response references from common-libraries

### Phase 5: Validation
1. Run: `npx swagger-cli validate openapi.yaml`
2. Fix any errors
3. Test with SDK3 barclaysApiGenerate
4. Verify generated code compiles

For detailed validation procedures, see [validation-guide.md](validation-guide.md).

## Best Practices

1. **Copy Template First**: Start by copying common-libraries from OAS template
2. **Do Not Modify common-libraries**: These are standard files for all APIs
3. **Use References**: Never inline schemas or responses
4. **Validate Often**: Run validation after each major change
5. **Follow Naming**: Use exact naming conventions from template
6. **Include All Error Responses**: All 7 standard error responses for each endpoint
7. **Response Headers**: Always include Cache-Control, Content-Type, Correlation-ID
8. **Test with SDK3**: Ensure barclaysApiGenerate works before finalizing

## Additional Resources

- OpenAPI Specification: https://spec.openapis.org/oas/v3.0.3
- Swagger Editor: https://editor.swagger.io/
- Barclays OAS Template: `{PROJECT_ROOT}/.claude/cache/oas-template/oas`
- Barclays SDK3 Documentation: Internal Confluence

## Agent Self-Check

Before executing, verify:
- [ ] All required inputs are present
- [ ] Skill documentation has been loaded
- [ ] Scope boundary is understood — no out-of-scope changes
- [ ] Iron Rules (No Assumptions, Version Source of Truth) acknowledged
- [ ] Output format understood
