---
description: Convert RAML 1.0 specification to OpenAPI 3.0.3 following Barclays OAS template structure with native conversion, HTTP validation, and automated fix loop
argument-hint: [RAML_PATH] [--output OAS_PATH] [--template TEMPLATE_PATH] [--api-owner-business NAME:EMAIL] [--api-owner-technical NAME:EMAIL] [--validate-only]
---

## AUTOMATION MODE (NON-NEGOTIABLE)
This command runs FULLY AUTOMATED from start to finish. NO user input required.
- NEVER use AskUserQuestion tool
- NEVER wait for user confirmation between steps
- Make autonomous decisions using the `raml_oas_conversion` skill patterns
- If validation fails, attempt to fix automatically before reporting

## RAML Constraint Preservation Policy (HIGHEST PRIORITY)

**ALWAYS STRICTLY ADHERE TO RAML CONSTRAINTS** throughout every step of this pipeline.

1. **RAML Fidelity First**
   - If RAML defines `enum` -> Keep `enum` ONLY (do not add `pattern`)
   - If RAML defines `pattern` -> Keep `pattern` ONLY (do not add `enum`)
   - If RAML defines both -> Keep both exactly as defined
   - If RAML defines neither -> Only then may you add `pattern` if needed

2. **Never Modify RAML-Defined Constraints**
   - Do NOT add `pattern` if RAML only has `enum`
   - Do NOT add `enum` if RAML only has `pattern`
   - Do NOT derive constraints from RAML `examples` (examples are documentation, not constraints)

3. **Validator Issues vs RAML Fidelity**
   - RAML fidelity takes absolute precedence over validator quirks
   - If validator fails on valid RAML constraints, document the limitation in `openapi-anomalies.md`

4. **Verification**: Before fixing any validation error, ALWAYS check the original RAML source for that property.

---

# RAML to OpenAPI Conversion Command

Convert RAML 1.0 API specifications to OpenAPI 3.0.3 format following the Barclays OAS template structure. Uses **native Claude conversion** (no external JAR or tools) with full validation and automated fix loop.

## Usage

```bash
/raml-to-oas [RAML_PATH] [--output OAS_PATH] [--template TEMPLATE_PATH] [--api-owner-business NAME:EMAIL] [--api-owner-technical NAME:EMAIL] [--validate-only]
```

## Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `RAML_PATH` | Path to RAML folder | Auto-detect: `src/main/resources/raml` or `./raml` |
| `--output` | Output path for OAS | `src/main/resources/oas` |
| `--template` | Path to OAS template | `{PROJECT_ROOT}/.claude/cache/oas-template/oas` |
| `--api-owner-business` | Business owner (`Name:email`) | Extracted from doc-api.md or `[Name](email)` |
| `--api-owner-technical` | Technical owner (`Name:email`) | Extracted from doc-api.md or `[Name](email)` |
| `--validate-only` | Only validate existing OAS | `false` |

---

## Step 0: Parse Arguments

1. Parse command-line arguments from the user invocation
2. **Auto-detect RAML directory**:
   - Check `src/main/resources/raml` (preferred)
   - Fallback: `./raml` or current directory if it contains `api.raml`
3. Set `OUTPUT_OAS` to `--output` or default `src/main/resources/oas`
4. Set `PROJECT_ROOT` to the project root directory (parent of `src/` or current working directory)
5. **Locate plugin scripts** — set `SCRIPT_DIR` by running:
   ```bash
   if [ -f "{PROJECT_ROOT}/.claude/scripts/analyze_oas_anomalies.py" ]; then
     SCRIPT_DIR="{PROJECT_ROOT}/.claude/scripts"
   else
     SCRIPT_DIR=$(find ~/.claude/plugins/cache -path "*/sdk3-migration/*/scripts" -type d 2>/dev/null | sort -r | head -1)
   fi
   ```
   If `SCRIPT_DIR` is empty after this, warn the user that the plugin scripts could not be found and anomaly analysis / HTTP validation will be skipped.

If `--validate-only` is set, skip to Step 6.

---

## Step 1: Extract Metadata from doc-api.md

Read `{RAML_PATH}/docs/doc-api.md` using the Read tool. Extract the following metadata:

| Field | Extraction Rule | Default |
|-------|----------------|---------|
| **API Type** | From "API Type:" section. Map: "Internal Process API" -> `INTERNAL`, "External" -> `EXTERNAL`, "System" -> `SYSTEM` | `INTERNAL` |
| **Risk Classification** | From "API Risk Classification:" section. Map: "Minor" -> `LOW`, "Major" -> `CRITICAL`, "Limited" -> `LIMITED` | `LIMITED` |
| **Business Owner** | From "Business Owner:" section (name and email) | From `--api-owner-business` or `[Name](email)` |
| **Tech Owner** | From "Tech Owner:" section (name and email) | From `--api-owner-technical` or `[Name](email)` |
| **API Overview** | From "Currently it serves:" or "Overview" section | Derive from API title |

**Parameter Parsing** (if provided via CLI args):
- Input: `--api-owner-business "John Doe:john.doe@barclays.com"`
- Parse: Split on first `:` to get name and email
- Output for description: `[John Doe](john.doe@barclays.com)`

CLI parameters override doc-api.md extractions.

---

## Step 2: Clone/Use Cached OAS Template

The OAS template provides `common-libraries/` which is required for all conversions.

**Repository**: `git@app.gitlab.barcapint.com:barclays/B2B-API-Interfaces/oas-template.git`

```bash
TEMPLATE_CACHE_DIR="{PROJECT_ROOT}/.claude/cache/oas-template"

if [ -d "$TEMPLATE_CACHE_DIR/oas/common-libraries" ]; then
  echo "Using cached OAS template: $TEMPLATE_CACHE_DIR/oas"
  TEMPLATE_LOCATION="$TEMPLATE_CACHE_DIR/oas"
else
  echo "Cloning OAS template from GitLab..."
  mkdir -p "$TEMPLATE_CACHE_DIR"
  git clone --branch master --single-branch \
    git@app.gitlab.barcapint.com:barclays/B2B-API-Interfaces/oas-template.git \
    "$TEMPLATE_CACHE_DIR"

  if [ -d "$TEMPLATE_CACHE_DIR/oas/common-libraries" ]; then
    TEMPLATE_LOCATION="$TEMPLATE_CACHE_DIR/oas"
  else
    echo "ERROR: Failed to clone OAS template. Conversion cannot proceed."
    exit 1
  fi
fi
```

---

## Step 3: Setup Output Structure

Create the OAS output directory tree:

```
{OUTPUT_OAS}/
├── openapi.yaml
├── common-libraries/          <- Copy from template
│   ├── components/
│   │   ├── headers.yaml
│   │   ├── responses.yaml
│   │   └── response-types.yaml
│   ├── examples/
│   │   └── example-error-*.json
│   └── security/
│       └── security-schemes.yaml
├── components/
│   ├── parameters.yaml
│   ├── common/
│   └── {endpointName}/
│       ├── request-body/
│       └── response-body/
└── examples/
```

**Steps**:
1. Create `{OUTPUT_OAS}` directory and all subdirectories
2. Copy `common-libraries/` from template
3. Copy example JSON files from RAML `examples/` to `{OUTPUT_OAS}/examples/`
4. Create empty `components/parameters.yaml` and endpoint folders

---

## Step 4: Convert RAML to OAS (NATIVE - NO EXTERNAL TOOLS)

This step performs the actual conversion by reading RAML files and generating OpenAPI YAML files using Claude's understanding of both specifications. All conversion rules are encoded in the `raml_oas_conversion` skill's [conversion-patterns.md](../skills/raml_oas_conversion/conversion-patterns.md).

### 4.1 Read and Parse RAML

1. Read `api.raml` to understand:
   - API title, version, baseUri, mediaType
   - Resource hierarchy (endpoints, methods, URI parameters)
   - Trait references (headers, common parameters)
   - Type references (`!include` directives)
   - Security schemes

2. Read each `.raml` file in `types/` directory to understand data type definitions

3. Read `traits/` files for reusable header and parameter definitions

### 4.2 Generate Component Schema YAML Files

For each RAML type, generate an OAS schema file:

- **Placement**: `components/common/schema-{Name}.yaml` for shared types, `components/{endpoint}/response-body/schema-{Name}.yaml` for endpoint-specific response types, `components/{endpoint}/request-body/schema-{Name}.yaml` for request types
- **Apply conversion rules from `conversion-patterns.md`**:
  - String: `minLength`, `maxLength`, `pattern`, `enum`, `format`, `example`
  - Integer: `minimum`, `maximum`, `format` (int32/int64), `example`
  - Number: `minimum`, `maximum`, `format`, `multipleOf`, `example`
  - Boolean: `example`, `description`
  - Date types: `date-only` -> `string` + `format: date`, `datetime` -> `string` + `format: date-time`, `time-only` -> `string` + `format: time`
  - Array: `minItems`, `maxItems`, `items` (recursive), `uniqueItems`
  - Object: `properties` (recursive), `required[]`, `additionalProperties: false`, `nullable: false`
- **Nested object types** -> separate YAML files with `$ref`
- **Relative path**: `../../common/schema-{Name}.yaml#/{Name}Type`
- **Inline simple types** (string, integer, boolean with no sub-properties); extract objects to component files

### 4.3 Generate parameters.yaml

Create `components/parameters.yaml` with:
- All URI parameters from resource paths -> path parameters
- All query parameters -> query parameters
- Format: `{ParameterName}` with `name`, `in`, `required`, `description`, `schema`

### 4.4 Generate Request/Response Definition Files

For each endpoint:
- `components/{endpoint}/response-{Endpoint}Response.yaml` with headers (Cache-Control, Content-Type, Correlation-ID-Response) and content schema reference
- `components/{endpoint}/request-{Endpoint}Request.yaml` for POST/PUT/PATCH endpoints with content schema reference
- Filter standard error codes (400, 401, 403, 404, 429, 500, 503) - these come from `common-libraries`

### 4.5 Generate openapi.yaml

Assemble the root OpenAPI file:

```yaml
openapi: "3.0.3"
info:
  title: "{API_TITLE}"
  version: "{API_VERSION}"
  description: |
    - **API Type:** {API_TYPE}
    - **API Risk Classification:** {RISK}
    - **API Owner (business):** [{BUSINESS_OWNER_NAME}]({BUSINESS_OWNER_EMAIL})
    - **API Owner (technical):** [{TECH_OWNER_NAME}]({TECH_OWNER_EMAIL})
    - **Overview:**
      {OVERVIEW}
  contact:
    email: "EMMAPI@barclays.com"
    name: "EMM API"
    url: 'https://confluence.barcapint.com/display/EMMAPIS/EMM+API+Inventory'
externalDocs:
  description: "EMM API Design Documentation Page"
  url: "https://confluence.barcapint.com/display/EMMAPIS/API+Project+Pages+Catalogue"
servers:
  - url: ""
    description: "Empty server URL dictated by OAS"
tags:
  - name: {operationId}
    description: "{operation description}"
security:
  - InternalTiaaUsRopcAuth: []
components:
  securitySchemes:
    InternalTiaaUsRopcAuth:
      $ref: './common-libraries/security/security-schemes.yaml#/InternalTiaaUsRopcAuth'
paths:
  {path}:
    {method}:
      summary: "{summary}"
      operationId: "{operationId}"
      description: "{description}"
      parameters:
        - $ref: './common-libraries/components/headers.yaml#/Authorization'
        - $ref: './common-libraries/components/headers.yaml#/Correlation-ID'
        - $ref: './common-libraries/components/headers.yaml#/Channel-ID'
        - $ref: './common-libraries/components/headers.yaml#/Agent-ID'
        - $ref: './common-libraries/components/headers.yaml#/Business-Unit-ID'
        - $ref: './components/parameters.yaml#/{ParameterName}'
      tags:
        - {operationId}
      responses:
        "{successCode}":
          $ref: './components/{endpoint}/response-{Endpoint}Response.yaml#/{Endpoint}Response'
        "400":
          $ref: './common-libraries/components/responses.yaml#/BadRequest'
        "401":
          $ref: './common-libraries/components/responses.yaml#/Unauthorized'
        "403":
          $ref: './common-libraries/components/responses.yaml#/Forbidden'
        "404":
          $ref: './common-libraries/components/responses.yaml#/NotFound'
        "429":
          $ref: './common-libraries/components/responses.yaml#/TooManyRequests'
        "500":
          $ref: './common-libraries/components/responses.yaml#/InternalServerError'
        "503":
          $ref: './common-libraries/components/responses.yaml#/ServiceUnavailable'
```

**Contact/License by API Type**:
- **INTERNAL**: `EMMAPI@barclays.com`, security: `InternalTiaaUsRopcAuth`
- **EXTERNAL**: different security/license as applicable
- **SYSTEM**: system-specific configuration

**Operation ID derivation**: `{method}{ResourceName}` in camelCase (e.g., `getAccountOffers`, `createStandingOrder`, `deleteStandingOrder`)

### 4.6 Extract Examples

- RAML `examples:` (plural named map) -> OAS `example:` (singular, first value from the map)
- JSON example files: copy to `examples/` folder, reference via `externalValue` with relative path

---

## Step 5: Post-Process

### 5.1 Apply RAML Constraint Preservation Policy

For every generated schema property, verify against the original RAML source:
- If RAML defines `enum` -> ensure only `enum` is present (no spurious `pattern`)
- If RAML defines `pattern` -> ensure only `pattern` is present (no spurious `enum`)
- Never derive constraints from examples

### 5.2 Resolve ALL TODO Placeholders

Search for any remaining `TODO` strings in generated files and resolve them:

| TODO Context | Resolution |
|-------------|------------|
| Contact info | Use `EMMAPI@barclays.com` or extract from doc-api.md |
| License | `Barclays Internal Use Only` for internal APIs, empty for unknown |
| ExternalDocs | EMM API Design Documentation Page URL |
| Servers | Empty string `""` |
| Tags | Derive from operation names |
| Operation IDs | `{method}` + resource name in camelCase |
| Summaries/descriptions | Derive from RAML descriptions or operation name |
| URLs | Use empty string `""` when no valid URL is determinable |

**Verification**: `grep -rn 'TODO' {OUTPUT_OAS}/ --include="*.yaml"` should return nothing.

### 5.3 Fix Known Issues

1. **Forbidden chars in patterns**: Remove `<`, `>`, `:`, `;`, `|`, `%`, `~` from regex character classes
2. **Location header**: Add `Location` header reference to all 201 Created responses (E-01-01)
3. **Location header pattern**: Fix pattern in `common-libraries/components/headers.yaml` to use path-only pattern `"^[A-Za-z0-9/.#@&=+,()_-]{1,492}$"` (no `:` for `https://`)
4. **Invalid type "double"**: Change to `type: "number"` with `format: "double"` or `type: "integer"` with `format: "int32"`
5. **Clean up RAML artifacts**: Remove any `types/`, `traits/`, `libs/`, `security-schemes/` folders from OAS output

---

## Step 6: Anomaly Analysis and Auto-Fix

### 6.1 Run Anomaly Analysis

```bash
python3 "$SCRIPT_DIR/analyze_oas_anomalies.py" {OUTPUT_OAS}
```

This analyzes all YAML files for:
- String properties without complete constraints (`maxLength` + `minLength` + `pattern`/`enum`)
- Numeric properties without `minimum`/`maximum`
- Regex patterns that violate E-02-02 (missing anchors, forbidden chars, wildcards)

Output: `openapi-anomalies.md` in project root.

### 6.2 Auto-Fix Anomalies

**Before fixing any property, check the original RAML source first.**

| Anomaly Type | Fix (only if RAML doesn't define the constraint) |
|-------------|--------------------------------------------------|
| String missing `minLength` | Add `minLength: 0` |
| String missing `maxLength` | Add `maxLength: 10000` (or context-appropriate value) |
| String missing `pattern` (and no `enum`) | Add `pattern: "^[\\s\\S]*$"` |
| Integer missing `minimum` | Add `minimum: 0` |
| Integer missing `maximum` | Add `maximum: 2147483647` (int32 max) |
| Number missing bounds | Add `minimum: 0`, `maximum` based on context |
| Array missing `minItems` | Add `minItems: 0` |
| Array missing `maxItems` | Add `maxItems: 100` (detail arrays) or `maxItems: 1000` (top-level) |
| Regex missing `^` anchor | Add `^` at beginning |
| Regex missing `$` anchor | Add `$` at end |
| Regex contains `.*` or `.+` | Replace with bounded quantifier `{1,N}` |
| Regex contains forbidden chars | Remove from character classes |

**Universal fallback pattern**: `"^[\\s\\S]*$"` (compliant with E-02-02: starts with `^`, ends with `$`, no `.*`/`.+`, uses character class)

---

## Step 7: Barclays HTTP Validation Loop

### 7.1 Run HTTP Validator

```bash
python3 "$SCRIPT_DIR/oas-validator.py" \
  {OUTPUT_OAS}/openapi.yaml \
  --all-files \
  --format json \
  -o validator-response.json
```

**Script**: `$SCRIPT_DIR/oas-validator.py`
**Endpoint**: `https://oasvalidator.barclays.intranet/v1.0/open-apis/validate`
**Features**: Creates ZIP of all OAS files, sends to endpoint, retries 3 times with 2s delay, SSL verification bypassed.

### 7.2 Parse Response

The validator returns a nested JSON structure. Issues are at `data.issues`, NOT `results`.

```json
{
  "data": {
    "info": { "title": "...", "version": "...", "timestamp": "..." },
    "issues": [
      {
        "code": "E-01-01",
        "message": "Location header missing",
        "path": ["paths", "/resource", "post", "responses", "201"],
        "severity": 0,
        "source": "openapi.yaml",
        "range": { "start": {"line": 195}, "end": {"line": 201} }
      }
    ]
  }
}
```

**Severity Levels**: 0=CRITICAL (must fix), 1=HIGH (should fix), 2=MEDIUM (optional), 3=LOW (optional)

### 7.3 Validation Fix Loop

```
LOOP (max 10 iterations):
  1. Run oas-validator.py -> parse JSON
  2. Count severity 0 issues
  3. IF severity_0_count == 0: EXIT LOOP (success)
  4. ELSE: Batch fix ALL severity 0 issues, then re-validate

EXIT when severity_0_count == 0
```

**Batch fixes**: Group by file to minimize reads/writes. Apply ALL fixes before re-validating.

### 7.4 Common E-Code Fixes

| Code | Issue | Fix |
|------|-------|-----|
| E-01-01 | Location header missing on 201 | Add `Location: $ref: "./common-libraries/components/headers.yaml#/Location"` |
| E-02-02 | Regex pattern non-compliant | Add `^`/`$` anchors, remove `.*`/`.+`, remove forbidden chars |
| type-array | Missing minItems/maxItems | Add `minItems: 0`, `maxItems: 100` |
| type-string | Missing constraints | Add `minLength`, `maxLength`, `pattern` (check RAML first) |
| type-number | Missing bounds | Add `minimum`, `maximum` |

---

## Step 8: Generate CONVERSION_REPORT.md

After all fixes and validation, generate `{OUTPUT_OAS}/CONVERSION_REPORT.md`:

```markdown
# RAML to OAS Conversion Report

## Summary
- **RAML Source**: {RAML_PATH}
- **OAS Output**: {OUTPUT_OAS}
- **Conversion Date**: {timestamp}

## Endpoints Converted
| Path | Methods | Operation IDs |
|------|---------|--------------|
| /path | GET, POST | getResource, createResource |

## Schemas Generated
- Component schemas: {count}
- Common schemas: {count}
- Parameter definitions: {count}

## Examples Extracted
- {count} example files copied from RAML

## Validation Results
- **Anomaly Analysis**: {anomaly_count} issues found, {fixed_count} auto-fixed
- **HTTP Validation Iterations**: {iteration_count}
- **Final Status**: PASSED/FAILED
- **Severity 0 Issues**: 0 (all resolved)
- **Remaining Non-Critical Issues**: {count} (severity 1+)

## Fixes Applied
- String constraints added: {count}
- Numeric bounds added: {count}
- Regex patterns fixed: {count}
- Location headers added: {count}
- TODO placeholders resolved: {count}
```

Update `openapi-anomalies.md` with final validation results and iteration details.

---

## Step 9: SDK3 Integration (if applicable)

If the project has `gradle.properties`:

1. Update `JAR_FILE` path:
   ```properties
   JAR_FILE=src/main/resources/oas/openapi.yaml
   ```

2. Switch request validation from RAML to OpenAPI in `application.properties` / `application.yaml` (check `src/main/resources/` and `src/test/resources/`):

   **Comment out RAML validation properties:**
   ```properties
   #ramlRequestValidation.isSwaggerValidation=true
   #ramlRequestValidation.ramlPath=src/main/resources/raml.zip
   ```

   **Add OpenAPI validation properties:**
   ```properties
   requestValidation.specPath=/oas/openapi.yaml
   requestValidation.isRequired=true
   ```

   Search all `application*.properties` and `application*.yaml` files across `src/main/resources/` and `src/test/resources/` for any `ramlRequestValidation` keys and apply the same switch.

3. Run compilation and tests:
   ```bash
   $GRADLE_CMD compileJava
   $GRADLE_CMD test
   ```

   If tests fail due to the validation switch, check:
   - The `specPath` value matches the actual OAS location relative to the classpath root
   - Test-specific property overrides in `src/test/resources/application*.properties` are also updated
   - Mock configurations that reference RAML paths are updated to OAS paths

---

## Skills Used

This command uses the following skills:
- `raml_oas_conversion` - Main conversion guide, patterns, and validation procedures (Skill tool: `sdk3-migration:raml_oas_conversion`)
  - [SKILL.md](../skills/raml_oas_conversion/SKILL.md) - Overview and folder structure
  - [conversion-patterns.md](../skills/raml_oas_conversion/conversion-patterns.md) - Type mappings and conversion rules
  - [validation-guide.md](../skills/raml_oas_conversion/validation-guide.md) - Validation and fix loop procedures

## Validation Scripts

Scripts are located automatically via `$SCRIPT_DIR` (set in Step 0.5). Resolution order:
1. `{PROJECT_ROOT}/.claude/scripts/` — project-local override
2. `~/.claude/plugins/cache/barclays-claude-code-plugins/sdk3-migration/<version>/scripts/` — plugin installation

- `oas-validator.py` - HTTP client for Barclays OAS Validator endpoint
- `analyze_oas_anomalies.py` - Local constraint anomaly analyzer

## Validation Checklist

After conversion, verify:
- [ ] Folder structure matches Barclays OAS template
- [ ] No `types/` or `libs/` folders in OAS
- [ ] Response headers use `Correlation-ID-Response`
- [ ] Error responses include all 7 standard codes (400, 401, 403, 404, 429, 500, 503)
- [ ] All 201 responses have Location header (E-01-01)
- [ ] All regex patterns compliant with E-02-02
- [ ] All string properties have complete constraints
- [ ] `python3 "$SCRIPT_DIR/oas-validator.py"` passes with 0 severity 0 issues
- [ ] No TODO placeholders remain
- [ ] SDK3 `barclaysApiGenerate` works (if applicable)

## Troubleshooting

### "requests library required"
Install: `pip3 install requests`

### "Connection error" to validator
Check network connectivity to `oasvalidator.barclays.intranet`. Retry logic handles transient failures.

### Response headers validation error
Use `Correlation-ID-Response` (not `Correlation-ID`) in response headers. Response headers must NOT have `name` or `in` properties.

### Invalid status code 426
Use 429 for TooManyRequests, not 426.

### Absolute paths in example references
If present, fix with: replace `./examples//Users/.../` with `./examples/`

### Invalid type "double"
OpenAPI 3.0 has no `type: double`. Use `type: "number"` with `format: "double"` or `type: "integer"` with `format: "int32"`.

### E-02-02 regex violations
Patterns must start with `^`, should end with `$`, must not use `.*`/`.+`, must not contain forbidden chars in character classes (`<`, `>`, `:`, `;`, `|`, `%`, `~`).

---

**Command Version:** 3.0.0
