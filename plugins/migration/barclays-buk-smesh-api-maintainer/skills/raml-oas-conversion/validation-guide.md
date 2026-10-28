# RAML to OpenAPI Validation Guide

Comprehensive validation procedures to ensure your RAML to OpenAPI conversion is complete, correct, and compliant with the Barclays OAS template.

For folder structure, see [SKILL.md](SKILL.md). For detailed conversion patterns, see [conversion-patterns.md](conversion-patterns.md).

## Table of Contents

1. [Validation Workflow](#validation-workflow)
2. [Template Compliance Validation](#template-compliance-validation)
3. [Structural Validation](#structural-validation)
4. [Schema Validation](#schema-validation)
5. [Reference Validation](#reference-validation)
6. [SDK3 Integration Validation](#sdk3-integration-validation)
7. [Automated Validation Tools](#automated-validation-tools)
8. [HTTP Validator Integration](#http-validator-integration)
9. [Anomaly Analysis](#anomaly-analysis)
10. [Auto-Fix Rules](#auto-fix-rules)
11. [Validation Fix Loop](#validation-fix-loop)
12. [TODO Resolution Rules](#todo-resolution-rules)
13. [Common Validation Errors and Fixes](#common-validation-errors-and-fixes)
14. [Pre-Deployment Checklist](#pre-deployment-checklist)

---

## Validation Workflow

### Phase 1: Template Compliance
Verify folder structure matches Barclays OAS template (see [SKILL.md](SKILL.md) for canonical structure).

### Phase 2: Syntax Validation
Run automated tools to verify OpenAPI syntax.

### Phase 3: Structural Validation
Ensure all RAML components are converted and all required openapi.yaml fields are present.

### Phase 4: Reference Validation
Verify all $ref links resolve correctly.

### Phase 5: Anomaly Analysis
Run local constraint analyzer to detect missing constraints.

### Phase 6: HTTP Validator
Run Barclays HTTP validator and fix loop to resolve all severity 0 issues.

### Phase 7: SDK3 Integration
Test with barclaysApiGenerate task.

---

## Template Compliance Validation

### Template Compliance Checklist

- [ ] Folder structure matches [SKILL.md](SKILL.md) canonical layout
- [ ] **NO** `types/` folder exists in OAS
- [ ] **NO** `libs/` folder exists in OAS
- [ ] `common-libraries/` folder exists and contains standard files
- [ ] Each endpoint has its own folder under `components/`
- [ ] Each endpoint folder has `request-body/` and `response-body/` subfolders
- [ ] `components/parameters.yaml` exists with all parameters
- [ ] `examples/` folder contains API-specific examples
- [ ] Error examples use correct naming: `example-error-{code}.json`

### Validation Steps

Use Glob tool to check for incorrect folders (should return no results):
- `oas/types/**` -- should NOT exist
- `oas/libs/**` -- should NOT exist

Use Glob tool to verify required structure exists:
- `oas/common-libraries/components/*`
- `oas/common-libraries/examples/*`
- `oas/common-libraries/security/*`
- `oas/components/*`

---

## Structural Validation

### openapi.yaml Required Fields

Verify all required fields are present:

```yaml
openapi: "3.0.3"
info:
  title: "API Name"                    # Required
  version: "v1.6"                      # Required, format: "v1.X"
  description: |                       # Required, markdown format
    - **API Type:** Internal
    - **API Risk Classification:** Limited
    - **API Owner (business):** [Name](email)     # From --api-owner-business command parameter
    - **API Owner (technical):** [Name](email)    # From --api-owner-technical command parameter
    - **Overview:**
      Description
  contact:                             # Required
    email: "EMMAPI@barclays.com"
    name: "EMM API"
    url: 'https://confluence.barcapint.com/...'
externalDocs:                          # Required
  description: "EMM API Design Documentation Page"
  url: "https://confluence.barcapint.com/..."
servers:                               # Required
  - url: ""
    description: "Empty server URL dictated by OAS"
security:                              # Required
  - InternalTiaaUsRopcAuth: []
```

### openapi.yaml Structural Checklist

- [ ] `openapi: "3.0.3"` (with quotes)
- [ ] `info.version` format is `"v1.X"` (e.g., "v1.6")
- [ ] `info.description` uses markdown bullet format
- [ ] `info.description` includes API Owner (business) from `--api-owner-business` parameter
- [ ] `info.description` includes API Owner (technical) from `--api-owner-technical` parameter
- [ ] API Owner format is `[Name](email)` (markdown link syntax)
- [ ] `info.contact` includes email, name, url
- [ ] `externalDocs` is present
- [ ] `servers[0].url` is empty string `""`
- [ ] `security` uses `InternalTiaaUsRopcAuth: []`
- [ ] `tags` defined for all endpoints
- [ ] Each path has `summary`, `description`, `operationId`, `tags`

---

## Schema Validation

### Required Fields Pattern

Verify required fields are at schema level, not property level:

```yaml
# WRONG
properties:
  accountId:
    type: string
    required: true      # WRONG - required in property

# CORRECT
type: object
required:
  - accountId           # CORRECT - required at schema level
properties:
  accountId:
    type: string
```

### Schema Validation Checklist

- [ ] No `required: true` inside properties
- [ ] Required fields in `required` array at schema level
- [ ] RAML date types converted to string with format (see [conversion-patterns.md](conversion-patterns.md#data-types-with-constraints) for type mappings)
- [ ] Arrays have `items` defined
- [ ] Constraints preserved (minLength, maxLength, pattern, etc.)

---

## Reference Validation

### Reference Patterns

```yaml
# Parameter references
$ref: './components/parameters.yaml#/AccountId'

# Response references
$ref: './common-libraries/components/responses.yaml#/BadRequest'

# Header references (request - used in parameters)
$ref: './common-libraries/components/headers.yaml#/Authorization'

# Header references (response - used in response headers)
$ref: './common-libraries/components/headers.yaml#/Cache-Control'
$ref: './common-libraries/components/headers.yaml#/Correlation-ID-Response'
```

### Reference Validation Checklist

- [ ] All `$ref` paths are correct relative paths
- [ ] Referenced files exist
- [ ] Referenced schemas/properties exist in files
- [ ] No circular references
- [ ] Error responses reference `common-libraries/components/responses.yaml`
- [ ] Parameters reference `components/parameters.yaml`
- [ ] Headers reference `common-libraries/components/headers.yaml`

### Validation Command

```bash
# Validate all references
npx swagger-cli validate oas/openapi.yaml

# Bundle to check all refs resolve
npx swagger-cli bundle oas/openapi.yaml -o bundled.yaml
```

---

## SDK3 Integration Validation

### Gradle Configuration

Verify gradle.properties:
```properties
JAR_FILE=src/main/resources/oas/openapi.yaml
```

### Code Generation Test

```bash
$GRADLE_CMD clean barclaysApiGenerate
```

Check the exit code -- it should be 0 (success).

Use Glob tool with pattern `build/generated/sources/src/main/java/**/*.java` to verify files were generated.

### Compilation Test

```bash
$GRADLE_CMD compileJava

$GRADLE_CMD test -x barclaysApiGenerate
```

### SDK3 Validation Checklist

- [ ] `gradle.properties` points to `openapi.yaml`
- [ ] `barclaysApiGenerate` succeeds
- [ ] Generated code compiles without errors
- [ ] Tests pass with generated code

---

## Automated Validation Tools

### swagger-cli

**Installation:**
```bash
npm install -g @apidevtools/swagger-cli
```

**Validation:**
```bash
# Validate syntax and references
npx swagger-cli validate oas/openapi.yaml

# Expected output:
# oas/openapi.yaml is valid

# Bundle for debugging
npx swagger-cli bundle oas/openapi.yaml -o bundled.yaml
```

### Swagger Editor (Online)

1. Go to https://editor.swagger.io/
2. File > Import file > select bundled.yaml
3. Check right panel for errors

### Quick Validation Steps

**Step 1: Template structure check**
- Use Glob tool to check `oas/types/**` and `oas/libs/**` -- these should return NO results

**Step 2: Required folders**
- Use Glob tool to verify each required folder has content:
  - `oas/common-libraries/components/*`
  - `oas/common-libraries/examples/*`
  - `oas/common-libraries/security/*`
  - `oas/components/*`
  - `oas/examples/*`

**Step 3: Header validation**
- Use Grep tool to search for `Correlation-ID-Response` in `oas/common-libraries/components/headers.yaml` -- must be found
- Use Grep tool to search for `Correlation-ID-Response` across `oas/components/` -- should find references in all response files

**Step 4: swagger-cli validation**
- Run: `npx swagger-cli validate oas/openapi.yaml`

---

## HTTP Validator Integration

### Script Location

**Script**: `$SCRIPT_DIR/oas-validator.py` (resolved in command Step 0)
**Endpoint**: `https://oasvalidator.barclays.intranet/v1.0/open-apis/validate`

### Invocation

```bash
python3 "$SCRIPT_DIR/oas-validator.py" {OAS_PATH}/openapi.yaml --all-files --format json
```

**Options:**
- `--all-files`: Include all referenced files (creates ZIP of the entire OAS directory)
- `--format json`: Return machine-parseable JSON
- `-o FILE`: Write response to file instead of stdout

### How It Works

1. Reads the specified OAS file and resolves relative paths
2. Creates a temporary ZIP file containing `openapi.yaml` and all referenced files
3. Sends the ZIP to `https://oasvalidator.barclays.intranet/v1.0/open-apis/validate` via POST
4. Retries up to 3 times with 2-second delay on failure
5. SSL verification is bypassed (internal certificate)
6. Returns JSON response with validation results

### Response Structure

The validator returns a nested JSON structure. Issues are at `data.issues`, **NOT** `results`:

```json
{
  "data": {
    "info": {
      "title": "API Name",
      "version": "v1.0",
      "timestamp": "2026-01-15T10:30:00Z"
    },
    "issues": [
      {
        "code": "E-01-01",
        "message": "Location header missing in 201 response",
        "path": ["paths", "/resource", "post", "responses", "201"],
        "severity": 0,
        "source": "openapi.yaml",
        "range": {
          "start": {"line": 195, "character": 0},
          "end": {"line": 201, "character": 0}
        }
      }
    ]
  }
}
```

### Severity Levels

| Level | Name | Action |
|-------|------|--------|
| 0 | CRITICAL | **Must fix** - blocks deployment |
| 1 | HIGH | Should fix - may cause issues |
| 2 | MEDIUM | Optional - best practice recommendations |
| 3 | LOW | Optional - minor improvements |

### Prerequisites

- Python 3.6+
- `requests` library: `pip3 install requests`
- Network access to `oasvalidator.barclays.intranet`

---

## Anomaly Analysis

### Script Location

**Script**: `$SCRIPT_DIR/analyze_oas_anomalies.py` (resolved in command Step 0)

### Invocation

```bash
python3 "$SCRIPT_DIR/analyze_oas_anomalies.py" {OAS_DIR}
```

### What It Checks

1. **String properties**: Must have `maxLength` + `minLength` + (`pattern` or `enum`)
2. **Numeric properties**: Must have `minimum` + `maximum`
3. **Array properties**: Must have `minItems` + `maxItems`
4. **Regex patterns**: Must comply with E-02-02:
   - Must start with `^`
   - Should end with `$`
   - No `.*` or `.+` wildcards
   - No forbidden chars in character classes: `<`, `>`, `:`, `;`, `|`, `%`, `~`

### Report Output

Generates `openapi-anomalies.md` in the project root with:
- Summary of all anomalies found
- Per-file breakdown
- Severity categorization
- Recommended fixes

### Integration with Fix Loop

Run anomaly analysis **before** the HTTP validator:
1. Anomaly analysis detects constraint gaps
2. Auto-fix applies missing constraints
3. HTTP validator then validates the complete specification
4. This order minimizes HTTP validator iterations

---

## Auto-Fix Rules

### String Fixes

**Before fixing, check the original RAML source.**

| Missing Constraint | Fix (if RAML doesn't define) | Condition |
|-------------------|------------------------------|-----------|
| `minLength` | Add `minLength: 0` | Only if no `enum` |
| `maxLength` | Add `maxLength: 10000` (or context value) | Only if no `enum` |
| `pattern` | Add `pattern: "^[\\s\\S]*$"` | Only if no `enum` AND RAML has no pattern |

### Numeric Fixes

| Missing Constraint | Fix |
|-------------------|-----|
| `minimum` | Add `minimum: 0` |
| `maximum` (integer) | Add `maximum: 2147483647` (int32 max) |
| `maximum` (number) | Add context-appropriate value |

### Array Fixes

| Missing Constraint | Fix |
|-------------------|-----|
| `minItems` | Add `minItems: 0` |
| `maxItems` (detail array) | Add `maxItems: 100` |
| `maxItems` (top-level array) | Add `maxItems: 1000` |

### Regex E-02-02 Compliance Fixes

| Issue | Fix |
|-------|-----|
| Missing `^` at start | Add `^` prefix |
| Missing `$` at end | Add `$` suffix |
| Contains `.*` | Replace with `[\\s\\S]*` or bounded `{0,N}` |
| Contains `.+` | Replace with `[\\s\\S]+` or bounded `{1,N}` |
| Forbidden chars in `[]` | Remove `<`, `>`, `:`, `;`, `\|`, `%`, `~` from character classes |

**Universal fallback pattern**: `"^[\\s\\S]*$"` -- compliant with all E-02-02 rules.

### RAML Constraint Preservation During Fixes

**Always check RAML first:**
- If RAML has `enum` -> do NOT add `pattern`, even if validator suggests it
- If RAML has `pattern` -> keep the RAML pattern, only add anchors if missing
- If RAML has both `enum` and `pattern` -> keep both as-is
- If RAML has neither -> apply auto-fix rules above

---

## Validation Fix Loop

### Loop Algorithm

```
iteration = 0
MAX_ITERATIONS = 10

WHILE iteration < MAX_ITERATIONS:
  1. Run: python3 "$SCRIPT_DIR/oas-validator.py" {OAS_PATH}/openapi.yaml --all-files --format json
  2. Parse JSON response
  3. Extract issues from data.issues
  4. Count severity 0 issues -> severity_0_count
  5. IF severity_0_count == 0:
       LOG "All severity 0 issues resolved after {iteration} iterations"
       BREAK
  6. ELSE:
       Group issues by source file
       For each file:
         Read file content
         Apply batch fixes for ALL severity 0 issues in that file
         Write fixed content
       iteration += 1

IF iteration == MAX_ITERATIONS AND severity_0_count > 0:
  LOG "WARNING: {severity_0_count} severity 0 issues remain after {MAX_ITERATIONS} iterations"
  Document remaining issues in openapi-anomalies.md
```

### Batch Fix Strategy

Group fixes by file to minimize I/O:
1. Collect all severity 0 issues for a given file
2. Read the file once
3. Apply all fixes in memory
4. Write the file once

### Common E-Code Fixes

| Code | Issue | Fix |
|------|-------|-----|
| E-01-01 | Location header missing on 201 response | Add `Location` header reference to the 201 response definition |
| E-02-02 | Regex pattern non-compliant | Add `^`/`$` anchors, remove `.*`/`.+`, remove forbidden chars |
| E-03-xx | Missing string constraints | Add `minLength`, `maxLength`, `pattern` (check RAML first) |
| E-04-xx | Missing numeric bounds | Add `minimum`, `maximum` |
| E-05-xx | Missing array bounds | Add `minItems`, `maxItems` |

### E-01-01: Location Header Fix

For 201 Created responses, add Location header:

```yaml
# In the response definition file (e.g., response-CreateResourceResponse.yaml)
CreateResourceResponse:
  description: "Resource created successfully"
  headers:
    Cache-Control:
      $ref: '../../common-libraries/components/headers.yaml#/Cache-Control'
    Content-Type:
      $ref: '../../common-libraries/components/headers.yaml#/Content-Type'
    Correlation-ID:
      $ref: '../../common-libraries/components/headers.yaml#/Correlation-ID-Response'
    Location:
      $ref: '../../common-libraries/components/headers.yaml#/Location'
```

If `Location` header doesn't exist in `common-libraries/components/headers.yaml`, add it:
```yaml
Location:
  description: "URI of the newly created resource"
  schema:
    type: string
    pattern: "^[A-Za-z0-9/.#@&=+,()_-]{1,492}$"
    minLength: 1
    maxLength: 492
```

### E-02-02: Regex Pattern Fix

```yaml
# BEFORE (non-compliant)
pattern: [a-zA-Z0-9]*

# AFTER (compliant)
pattern: "^[a-zA-Z0-9]*$"
```

For patterns with forbidden characters:
```yaml
# BEFORE
pattern: "^[a-zA-Z0-9<>:;|%~]*$"

# AFTER (forbidden chars removed)
pattern: "^[a-zA-Z0-9]*$"
```

---

## TODO Resolution Rules

When generating OAS files, certain fields may initially contain TODO placeholders. All TODOs must be resolved before validation.

### Resolution Table

| TODO Context | Resolution Rule |
|-------------|----------------|
| `info.contact.email` | `EMMAPI@barclays.com` or extract from doc-api.md |
| `info.contact.name` | `EMM API` |
| `info.contact.url` | `https://confluence.barcapint.com/display/EMMAPIS/EMM+API+Inventory` |
| `info.license` | `Barclays Internal Use Only` for internal APIs, empty for unknown |
| `externalDocs.description` | `EMM API Design Documentation Page` |
| `externalDocs.url` | `https://confluence.barcapint.com/display/EMMAPIS/API+Project+Pages+Catalogue` |
| `servers[0].url` | Empty string `""` |
| `servers[0].description` | `Empty server URL dictated by OAS` |
| `tags[].name` | Derive from operation names (e.g., `getAccountOffers`) |
| `tags[].description` | Derive from RAML description or operation name |
| Operation `operationId` | `{method}{ResourceName}` in camelCase |
| Operation `summary` | Derive from RAML description or resource name |
| Operation `description` | Derive from RAML description or summary |
| Any URL field | Use empty string `""` when no valid URL is determinable |

### Verification

After TODO resolution:
```bash
grep -rn 'TODO' {OAS_DIR}/ --include="*.yaml"
```
This should return **zero** results.

---

## Common Validation Errors and Fixes

### Error 1: Response Headers with name/in

**Error:**
```
headers/Correlation-ID must NOT have additional properties
```

**Cause:** Using request header `Correlation-ID` (which has `name`/`in` properties) in a response context.

**Fix:** Use `Correlation-ID-Response` instead (see [conversion-patterns.md](conversion-patterns.md#headers-request-vs-response) for the full header rules):
```yaml
headers:
  Correlation-ID:
    $ref: '../../common-libraries/components/headers.yaml#/Correlation-ID-Response'
```

### Error 2: Unresolved $ref

**Error:**
```
Could not resolve reference: ./types/type-missing.yaml
```

**Fix:**
- Verify file exists at the path
- Check file extension is `.yaml`
- Verify path is correct relative to referencing file
- There is no `types/` folder in OAS -- schemas live under `components/`

### Error 3: Invalid HTTP Status Code

**Error:**
```
Response code '426' is not a valid status code
```

**Fix:** Use 429 for Too Many Requests, NOT 426. (426 = Upgrade Required, which is wrong.)

### Error 4: Missing operationId

**Warning:**
```
Operation should have operationId
```

**Fix:**
```yaml
get:
  operationId: "getAccountOffers"
  summary: "Get all offers"
```

### Error 5: Missing Required Fields in Info

**Fix:** Ensure all required fields are present:
- `title`
- `version` (format "v1.X")
- `description` (markdown format with API owners)
- `contact` (email, name, url)

### Error 6: Wrong Folder Structure

**Error:** Files not found during validation.

**Fix:**
- Remove `types/` folder if exists
- Remove `libs/` folder if exists
- Move schemas to `components/common/` or `components/{endpoint}/`
- See [SKILL.md](SKILL.md) for the correct folder structure

### Error 7: Invalid type "double"

**Error:**
```
type "double" is not a valid type
```

**Fix:** OpenAPI 3.0 has no `type: double`. Use:
- `type: "number"` with `format: "double"`, or
- `type: "integer"` with `format: "int32"`

### Error 8: Absolute paths in example references

**Error:** `externalValue` contains absolute filesystem path.

**Fix:** Replace absolute paths with relative paths from the referencing file:
```yaml
# WRONG
externalValue: "/Users/developer/project/examples/response.json"

# CORRECT
externalValue: "../../examples/response.json"
```

---

## Pre-Deployment Checklist

### Template Compliance
- [ ] Folder structure matches [SKILL.md](SKILL.md) canonical layout
- [ ] `common-libraries/` contains standard files
- [ ] No `types/` or `libs/` folders
- [ ] Each endpoint has own folder with request-body/response-body

### openapi.yaml
- [ ] Version is "v1.6" or appropriate version
- [ ] Description uses markdown bullet format with API owners
- [ ] Contact details are correct
- [ ] externalDocs is present
- [ ] Server URL is empty string
- [ ] Security uses InternalTiaaUsRopcAuth
- [ ] Tags defined for all endpoints
- [ ] All responses use $ref (not inline)
- [ ] All error responses from common-libraries

### Headers
- [ ] Response headers use Correlation-ID-Response (not Correlation-ID)
- [ ] Response headers include Cache-Control, Content-Type
- [ ] No response header has `name` or `in` properties
- [ ] 201 responses have Location header

### Error Responses
- [ ] All endpoints have 400, 401, 403, 404, 429, 500, 503
- [ ] Error code is 429 (not 426) for TooManyRequests
- [ ] Error responses reference common-libraries/components/responses.yaml

### Constraints
- [ ] All string properties have `minLength` + `maxLength` + (`pattern` or `enum`)
- [ ] All integer properties have `minimum` + `maximum`
- [ ] All array properties have `minItems` + `maxItems`
- [ ] All regex patterns comply with E-02-02
- [ ] RAML constraints are preserved faithfully

### TODO Resolution
- [ ] No TODO placeholders remain in any YAML file
- [ ] All contact info filled in
- [ ] All URLs are valid or empty string

### Validation Tools
- [ ] `npx swagger-cli validate openapi.yaml` passes
- [ ] `python3 "$SCRIPT_DIR/analyze_oas_anomalies.py"` reports zero issues
- [ ] `python3 "$SCRIPT_DIR/oas-validator.py"` reports zero severity 0 issues
- [ ] No errors in Swagger Editor

### SDK3 Integration
- [ ] `gradle.properties` points to openapi.yaml
- [ ] `$GRADLE_CMD barclaysApiGenerate` succeeds
- [ ] `$GRADLE_CMD compileJava` succeeds
- [ ] `$GRADLE_CMD test` passes
