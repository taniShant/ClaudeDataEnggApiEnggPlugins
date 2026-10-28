# RAML to OpenAPI Conversion Patterns Reference

Detailed conversion patterns for all RAML 1.0 constructs to OpenAPI 3.0.3 equivalents, following the Barclays OAS template structure.

For folder structure, see [SKILL.md](SKILL.md). For validation procedures, see [validation-guide.md](validation-guide.md).

## Table of Contents

1. [Root File Structure](#root-file-structure)
2. [Headers (Request vs Response)](#headers-request-vs-response)
3. [Parameters](#parameters)
4. [Response Definitions](#response-definitions)
5. [Request Body Definitions](#request-body-definitions)
6. [Data Types with Constraints](#data-types-with-constraints)
7. [Reference Resolution](#reference-resolution)
8. [Example Extraction](#example-extraction)
9. [Endpoint/Path Generation](#endpointpath-generation)
10. [Root OpenAPI Assembly](#root-openapi-assembly)
11. [RAML Constraint Preservation Policy](#raml-constraint-preservation-policy)
12. [Security Schemes](#security-schemes)
13. [Error Responses](#error-responses)
14. [Examples](#examples)

---

## Root File Structure

### Basic Structure Mapping

**RAML api.raml:**
```yaml
#%RAML 1.0
title: Offer Enquiry API
version: v1.4
baseUri: https://api.barclays.com
mediaType: application/json
```

**OpenAPI openapi.yaml (Barclays Format):**
```yaml
openapi: "3.0.3"
info:
  title: "Offer Enquiry Domain Service API"
  version: "v1.6"
  description: |
    - **API Type:** Internal
    - **API Risk Classification:** Limited
    - **API Owner (business):** [Pradeep, Radhika](radhika.pradeep@barclays.com)
    - **API Owner (technical):** [Kachare, Ashwini](ashwini.chaitanyakachare@barclays.com)
    - **Overview:**
      An API that allows applications to perform enquiries against the Barclaycard systems
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
  - name: getAccountOffers
    description: "Get all available offers for account"
security:
  - InternalTiaaUsRopcAuth: []
components:
  securitySchemes:
    InternalTiaaUsRopcAuth:
      $ref: './common-libraries/security/security-schemes.yaml#/InternalTiaaUsRopcAuth'
paths:
  /accounts/{accountId}/offers:
    summary: "Get account offers"
    description: "Endpoint to retrieve all available offers for an account"
    get:
      summary: "Get all available offers for account"
      operationId: "getAccountOffers"
      description: "Get all available offers for account"
      parameters:
        - $ref: './common-libraries/components/headers.yaml#/Authorization'
        - $ref: './common-libraries/components/headers.yaml#/Correlation-ID'
        - $ref: './common-libraries/components/headers.yaml#/Channel-ID'
        - $ref: './common-libraries/components/headers.yaml#/Agent-ID'
        - $ref: './common-libraries/components/headers.yaml#/Business-Unit-ID'
        - $ref: './components/parameters.yaml#/AccountId'
      tags:
        - getAccountOffers
      responses:
        "200":
          $ref: './components/getAccountOffers/response-GetAccountOffersResponse.yaml#/GetAccountOffersResponse'
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

**Required Info Fields:**
- `title`: API name in quotes
- `version`: Format "v1.X" (e.g., "v1.6")
- `description`: Markdown format with API Type, Risk Classification, Owners, Overview
- `contact`: EMMAPI@barclays.com
- `externalDocs`: EMM API Design Documentation Page
- `servers`: Empty URL string

---

## Headers (Request vs Response)

### CRITICAL DIFFERENCE

**Request Headers** - Have `name` and `in` properties:
```yaml
# In common-libraries/components/headers.yaml
Correlation-ID:
  name: "Correlation-ID"
  in: header
  description: "Unique call chain identifier"
  required: true
  schema:
    type: string
    pattern: ^[a-zA-Z0-9-+/=_]{16,64}$

Authorization:
  name: "Authorization"
  in: header
  required: true
  description: "Bearer TIAA Token"
  schema:
    type: string

Channel-ID:
  name: "Channel-ID"
  in: header
  required: true
  description: "Initiating channel identifier"
  schema:
    type: string

Agent-ID:
  name: "Agent-ID"
  in: header
  required: false
  description: "Unique identifier for the calling agent or user"
  schema:
    type: string
```

**Response Headers** - NO `name` or `in` properties:
```yaml
# In common-libraries/components/headers.yaml
Cache-Control:
  description: "GIS mandatory response header"
  schema:
    type: string
    default: no-cache, no-store, must-revalidate

Content-Type:
  description: "Response content type"
  schema:
    type: string
    enum:
      - "application/json"

# Response version for Correlation-ID
Correlation-ID-Response:
  description: "Correlation ID in response"
  schema:
    type: string
    pattern: ^[a-zA-Z0-9-+/=_]{16,64}$
```

### Using Headers in Responses

**CORRECT:**
```yaml
GetAccountOffersResponse:
  description: "Successful response"
  headers:
    Cache-Control:
      $ref: '../../common-libraries/components/headers.yaml#/Cache-Control'
    Content-Type:
      $ref: '../../common-libraries/components/headers.yaml#/Content-Type'
    Correlation-ID:
      $ref: '../../common-libraries/components/headers.yaml#/Correlation-ID-Response'
```

**WRONG - Will cause validation error:**
```yaml
headers:
  Correlation-ID:
    $ref: '../../common-libraries/components/headers.yaml#/Correlation-ID'  # Has name/in!
```

**Error message if wrong:**
```
headers/Correlation-ID must NOT have additional properties
```

---

## Parameters

### Path Parameters

**RAML:**
```yaml
/accounts/{accountId}/offers:
  uriParameters:
    accountId:
      type: string
      pattern: ^[0-9]{8,16}$
      required: true
```

**OpenAPI components/parameters.yaml:**
```yaml
AccountId:
  name: accountId
  in: path
  required: true
  description: "The unique account identifier"
  schema:
    type: string
    pattern: ^[0-9]{8,16}$
    minLength: 8
    maxLength: 16
```

### Query Parameters

**RAML:**
```yaml
queryParameters:
  offerType:
    type: string
    enum: [BALANCE_TRANSFER, MONEY_TRANSFER]
    required: false
  includeIneligible:
    type: boolean
    default: false
```

**OpenAPI components/parameters.yaml:**
```yaml
OfferTypeQuery:
  name: offerType
  in: query
  required: false
  description: "Filter by offer type"
  schema:
    type: string
    enum:
      - BALANCE_TRANSFER
      - MONEY_TRANSFER

IncludeIneligibleQuery:
  name: includeIneligible
  in: query
  required: false
  description: "Include ineligible offers"
  schema:
    type: boolean
    default: false
```

### Using Parameters in Paths

**openapi.yaml:**
```yaml
paths:
  /accounts/{accountId}/offers:
    get:
      parameters:
        # Headers from common-libraries
        - $ref: './common-libraries/components/headers.yaml#/Authorization'
        - $ref: './common-libraries/components/headers.yaml#/Correlation-ID'
        - $ref: './common-libraries/components/headers.yaml#/Channel-ID'
        - $ref: './common-libraries/components/headers.yaml#/Agent-ID'
        - $ref: './common-libraries/components/headers.yaml#/Business-Unit-ID'
        # Path/Query params from components/parameters.yaml
        - $ref: './components/parameters.yaml#/AccountId'
        - $ref: './components/parameters.yaml#/OfferTypeQuery'
        - $ref: './components/parameters.yaml#/IncludeIneligibleQuery'
```

---

## Response Definitions

### Response File Structure

**File: components/{endpoint}/response-{Endpoint}Response.yaml**

```yaml
GetAccountOffersResponse:
  description: "Successful response for Get Account Offers"
  headers:
    Cache-Control:
      $ref: '../../common-libraries/components/headers.yaml#/Cache-Control'
    Content-Type:
      $ref: '../../common-libraries/components/headers.yaml#/Content-Type'
    Correlation-ID:
      $ref: '../../common-libraries/components/headers.yaml#/Correlation-ID-Response'
  content:
    application/json:
      schema:
        $ref: "./response-body/schema-AccountOffersData.yaml#/AccountOffersResponseData"
      examples:
        responseExample:
          summary: "success response example"
          externalValue: "../../examples/offers_example.json"
```

### Response Body Schema Structure

**File: components/{endpoint}/response-body/schema-{Name}.yaml**

```yaml
AccountOffersResponseData:
  type: object
  description: "Response data for account offers"
  properties:
    data:
      type: array
      items:
        $ref: '../../common/schema-AccountOffer.yaml#/AccountOfferType'
```

### Multiple Examples in Response

```yaml
ValidateTransferResponse:
  description: "Successful validation response"
  headers:
    Cache-Control:
      $ref: '../../common-libraries/components/headers.yaml#/Cache-Control'
    Content-Type:
      $ref: '../../common-libraries/components/headers.yaml#/Content-Type'
    Correlation-ID:
      $ref: '../../common-libraries/components/headers.yaml#/Correlation-ID-Response'
  content:
    application/json:
      schema:
        $ref: "./response-body/schema-ValidateOfferResponse.yaml#/ValidateOfferResponseType"
      examples:
        moneyTransfer:
          summary: "Money Transfer validation response"
          externalValue: "../../examples/validate-mt-offer-response.json"
        balanceTransfer:
          summary: "Balance Transfer validation response"
          externalValue: "../../examples/validate-bt-offer-response.json"
```

---

## Request Body Definitions

### Request File Structure

**File: components/{endpoint}/request-{Endpoint}Request.yaml**

```yaml
ValidateTransferRequest:
  description: "Request body for Validate Transfer"
  required: true
  content:
    application/json:
      schema:
        $ref: "./request-body/schema-ValidateOfferRequest.yaml#/ValidateOfferRequestType"
      examples:
        moneyTransfer:
          summary: "Money Transfer request"
          externalValue: "../../examples/money-transfer-request.json"
        balanceTransfer:
          summary: "Balance Transfer request"
          externalValue: "../../examples/balance-transfer-request.json"
```

### Request Body Schema Structure

**File: components/{endpoint}/request-body/schema-{Name}.yaml**

```yaml
ValidateOfferRequestType:
  type: object
  required:
    - externalAccount
  properties:
    externalAccount:
      $ref: '../../common/schema-ExternalAccount.yaml#/ExternalAccountType'
    transferAmount:
      $ref: '../../common/schema-MonetaryAmount.yaml#/MonetaryAmountType'
```

---

## Data Types with Constraints

### Complete Type Conversion Rules

Each RAML type must be converted with all applicable constraints. These rules derive from the Barclays OAS validator requirements and ensure E-02-02 compliance.

#### String Properties

| RAML Constraint | OAS Equivalent | Notes |
|----------------|----------------|-------|
| `type: string` | `type: string` | Direct mapping |
| `minLength` | `minLength` | Direct mapping. Add `0` if absent in RAML and no enum defined |
| `maxLength` | `maxLength` | Direct mapping. Add context-appropriate value if absent (default: 10000) |
| `pattern` | `pattern` | Direct mapping. Must comply with E-02-02 (see Regex section) |
| `enum` | `enum` | Direct mapping. If RAML has enum, do NOT add pattern |
| `format` | `format` | e.g., `date`, `date-time`, `email`, `uri` |
| `example` | `example` | Single value (see Example Extraction) |
| `examples` | `example` | Extract first value from named map |
| `default` | `default` | Direct mapping |

**Fallback pattern** (when RAML defines neither `enum` nor `pattern`): `"^[\\s\\S]*$"`

#### Integer Properties

| RAML Constraint | OAS Equivalent | Notes |
|----------------|----------------|-------|
| `type: integer` | `type: integer` | Direct mapping |
| `minimum` | `minimum` | Direct mapping. Add `0` if absent |
| `maximum` | `maximum` | Direct mapping. Add `2147483647` (int32 max) if absent |
| `format` | `format` | `int32` or `int64` |
| `example` | `example` | Numeric value |
| `examples` | `example` | Extract first value |

#### Number Properties

| RAML Constraint | OAS Equivalent | Notes |
|----------------|----------------|-------|
| `type: number` | `type: number` | Direct mapping |
| `minimum` | `minimum` | Direct mapping. Add `0` if absent |
| `maximum` | `maximum` | Direct mapping. Context-appropriate value if absent |
| `format` | `format` | `float`, `double` |
| `multipleOf` | `multipleOf` | Direct mapping |
| `example` | `example` | Numeric value |

#### Boolean Properties

| RAML Constraint | OAS Equivalent | Notes |
|----------------|----------------|-------|
| `type: boolean` | `type: boolean` | Direct mapping |
| `example` | `example` | `true` or `false` |
| `default` | `default` | Direct mapping |

#### Date Type Conversions

| RAML Type | OAS Type | OAS Format | Example |
|-----------|----------|------------|---------|
| `date-only` | `string` | `date` | `"2026-01-15"` |
| `datetime` | `string` | `date-time` | `"2026-01-15T10:30:00Z"` |
| `time-only` | `string` | `time` | `"10:30:00"` |
| `datetime-only` | `string` | `date-time` | No timezone |

Add `minLength`, `maxLength`, and `pattern` for date strings:
- `date-only`: `minLength: 10`, `maxLength: 10`, `pattern: "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"`
- `datetime`: `minLength: 20`, `maxLength: 30`, `pattern: "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[A-Za-z0-9+.-]*$"`
- `time-only`: `minLength: 8`, `maxLength: 12`, `pattern: "^[0-9]{2}:[0-9]{2}:[0-9]{2}[0-9.]*$"`

#### Array Properties

| RAML Constraint | OAS Equivalent | Notes |
|----------------|----------------|-------|
| `type: array` | `type: array` | Direct mapping |
| `items` | `items` | Recursive type reference or inline |
| `minItems` | `minItems` | Direct mapping. Add `0` if absent |
| `maxItems` | `maxItems` | Direct mapping. Add `100` (detail) or `1000` (top-level) if absent |
| `uniqueItems` | `uniqueItems` | Direct mapping |

#### Object Properties

| RAML Construct | OAS Equivalent | Notes |
|----------------|----------------|-------|
| `type: object` | `type: object` | Direct mapping |
| `properties` | `properties` | Recursive conversion |
| `required: true` (on property) | `required: [prop]` at schema level | RAML puts required on each prop; OAS lists at schema level |
| `additionalProperties` | `additionalProperties` | Default to `false` for strict schemas |
| `nullable` | `nullable` | Default to `false` |

### Simple Types Mapping (Quick Reference)

| RAML Type | OpenAPI Type | Notes |
|-----------|--------------|-------|
| `string` | `string` | Direct mapping |
| `number` | `number` | Direct mapping |
| `integer` | `integer` | Direct mapping |
| `boolean` | `boolean` | Direct mapping |
| `date-only` | `string` + `format: date` | Add format |
| `datetime` | `string` + `format: date-time` | Add format |
| `time-only` | `string` + `format: time` | Add format |
| `file` | `string` + `format: binary` | Add format |

### Required Fields Pattern

**RAML:**
```yaml
#%RAML 1.0 DataType
properties:
  accountId:
    type: string
    required: true
  balance:
    type: number
    required: false
```

**OpenAPI:**
```yaml
type: object
required:
  - accountId          # Required at schema level, NOT in property
properties:
  accountId:
    type: string
    description: "Account identifier"
  balance:
    type: number
    description: "Account balance"
```

### Enum Types

**RAML:**
```yaml
#%RAML 1.0 DataType
type: string
enum: [BALANCE_TRANSFER, MONEY_TRANSFER, SPEND_AND_GET]
```

**OpenAPI (in components/common/schema-OfferEnums.yaml):**
```yaml
OfferTypeEnum:
  type: string
  description: "Type of offer"
  enum:
    - BALANCE_TRANSFER
    - MONEY_TRANSFER
    - SPEND_AND_GET
```

### Array Types

**RAML:**
```yaml
type: array
items:
  type: Offer
minItems: 0
maxItems: 100
```

**OpenAPI:**
```yaml
type: array
items:
  $ref: './schema-Offer.yaml#/OfferType'
minItems: 0
maxItems: 100
```

### Nested Objects

**RAML:**
```yaml
properties:
  monetaryAmount:
    type: object
    properties:
      value:
        type: number
      currency:
        type: string
```

**OpenAPI (separate file - components/common/schema-MonetaryAmount.yaml):**
```yaml
MonetaryAmountType:
  type: object
  description: "Monetary amount with currency"
  properties:
    value:
      type: number
      description: "Amount value"
      minimum: 0
      maximum: 999999999999.99
    currency:
      type: string
      description: "Currency code"
      pattern: "^[A-Z]{3}$"
      minLength: 3
      maxLength: 3
```

---

## Reference Resolution

### When to Extract vs Inline

| Scenario | Action | Reference Pattern |
|----------|--------|-------------------|
| Named RAML type (standalone `.raml` file) | Extract to separate YAML file | `$ref: '../../common/schema-{Name}.yaml#/{Name}Type'` |
| Nested object with 2+ properties | Extract to separate file | `$ref: './response-body/schema-{Name}.yaml#/{Name}Type'` |
| Simple type (string, integer, boolean with no sub-properties) | Inline in parent schema | No `$ref` needed |
| RAML `!include` directive | Resolve and extract | Follow the include, create schema file |
| Shared across endpoints | Place in `components/common/` | `$ref: '../../common/schema-{Name}.yaml#/{Name}Type'` |
| Endpoint-specific | Place in `components/{endpoint}/` | `$ref: './response-body/schema-{Name}.yaml#/{Name}Type'` |

### Relative Path Derivation

From `components/{endpoint}/response-{Endpoint}Response.yaml`:
- To common schema: `../../common/schema-{Name}.yaml#/{Name}Type`
- To response body schema: `./response-body/schema-{Name}.yaml#/{Name}Type`

From `components/{endpoint}/response-body/schema-{Name}.yaml`:
- To common schema: `../../common/schema-{Name}.yaml#/{Name}Type`
- To sibling schema: `./schema-{OtherName}.yaml#/{OtherName}Type`

From `openapi.yaml`:
- To response definition: `./components/{endpoint}/response-{Endpoint}Response.yaml#/{Endpoint}Response`
- To request definition: `./components/{endpoint}/request-{Endpoint}Request.yaml#/{Endpoint}Request`
- To parameter: `./components/parameters.yaml#/{ParameterName}`
- To header: `./common-libraries/components/headers.yaml#/{HeaderName}`
- To error response: `./common-libraries/components/responses.yaml#/{ErrorName}`
- To security: `./common-libraries/security/security-schemes.yaml#/InternalTiaaUsRopcAuth`

### File Naming Convention for Extracted Types

- RAML type `type-customerDetails.raml` -> `schema-CustomerDetails.yaml` containing `CustomerDetailsType`
- RAML type `type-payment-request.raml` -> `schema-PaymentRequest.yaml` containing `PaymentRequestType`
- Name mapping: strip `type-` prefix, PascalCase the remainder, append `Type` suffix for the schema key

---

## Example Extraction

### RAML to OAS Example Mapping

RAML uses `examples:` (plural) as a named map. OAS uses `example:` (singular) with a single value.

**RAML (named examples map):**
```yaml
paymentScheme:
  type: string
  examples:
    FPSScheme: F
    InternalPayment: O
    CHAPS: C
```

**OAS (first value extracted):**
```yaml
paymentScheme:
  type: string
  example: "F"
```

### Rules

1. If RAML has `example:` (singular) -> use directly as OAS `example:`
2. If RAML has `examples:` (plural named map) -> extract the **first value** from the map
3. If RAML has neither -> omit `example:` from OAS (do NOT fabricate)
4. JSON example files from RAML `examples/` folder -> copy to OAS `examples/` folder, reference via `externalValue`

### External Value References

```yaml
examples:
  responseExample:
    summary: "success response example"
    externalValue: "../../examples/offers_example.json"
```

---

## Endpoint/Path Generation

### Resource URI to OAS Path

| RAML Resource | OAS Path |
|--------------|----------|
| `/accounts/{accountId}/offers` | `/accounts/{accountId}/offers` |
| `/standingOrders/{stoId}` | `/standingOrders/{stoId}` |
| `/standingOrders/queries` | `/standingOrders/queries` |

### URI Parameters to Path Parameters

RAML `uriParameters` -> OAS path parameters in `components/parameters.yaml`:

```yaml
# RAML
/accounts/{accountId}:
  uriParameters:
    accountId:
      type: string
      pattern: ^[0-9]{8,16}$

# OAS components/parameters.yaml
AccountId:
  name: accountId
  in: path
  required: true
  description: "The unique account identifier"
  schema:
    type: string
    pattern: "^[0-9]{8,16}$"
    minLength: 8
    maxLength: 16
```

### Method to Operation Mapping

| RAML Method | OAS Operation | operationId Pattern |
|-------------|---------------|---------------------|
| `get` on `/accounts/{id}/offers` | `get` operation | `getAccountOffers` |
| `post` on `/standingOrders` | `post` operation | `createStandingOrder` |
| `post` on `/standingOrders/queries` | `post` operation | `queryStandingOrders` |
| `delete` on `/standingOrders/{stoId}` | `delete` operation | `deleteStandingOrder` |
| `patch` on `/standingOrders/{stoId}` | `patch` operation | `updateStandingOrder` |
| `put` on `/resource/{id}` | `put` operation | `replaceResource` |

**operationId** = `{verb}{ResourceName}` in camelCase.

### Request Body Extraction

For `POST`, `PUT`, `PATCH` methods:
- Extract request body from RAML `body:` section
- Create `request-{Endpoint}Request.yaml`
- Reference the request body schema from `request-body/` subfolder

### Response Body Extraction

For all methods:
- Extract success response from RAML `responses:` section (typically `200` or `201`)
- Create `response-{Endpoint}Response.yaml` with headers and content
- Filter standard error codes (400, 401, 403, 404, 429, 500, 503) - these reference `common-libraries`

### Common Headers in Every Operation

Every operation MUST include these header parameters:
```yaml
parameters:
  - $ref: './common-libraries/components/headers.yaml#/Authorization'
  - $ref: './common-libraries/components/headers.yaml#/Correlation-ID'
  - $ref: './common-libraries/components/headers.yaml#/Channel-ID'
  - $ref: './common-libraries/components/headers.yaml#/Agent-ID'
  - $ref: './common-libraries/components/headers.yaml#/Business-Unit-ID'
```

---

## Root OpenAPI Assembly

### Info Object

```yaml
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
```

### Contact/License by API Type

| API Type | Contact Email | Security Scheme | License |
|----------|--------------|-----------------|---------|
| INTERNAL | `EMMAPI@barclays.com` | `InternalTiaaUsRopcAuth` | `Barclays Internal Use Only` |
| EXTERNAL | `EMMAPI@barclays.com` | Per API requirements | `Barclays API License` |
| SYSTEM | `EMMAPI@barclays.com` | System-specific | `Barclays Internal Use Only` |

### Server URL

Always empty string:
```yaml
servers:
  - url: ""
    description: "Empty server URL dictated by OAS"
```

### External Documentation

```yaml
externalDocs:
  description: "EMM API Design Documentation Page"
  url: "https://confluence.barcapint.com/display/EMMAPIS/API+Project+Pages+Catalogue"
```

### Metadata Extraction from doc-api.md

Read `{RAML_PATH}/docs/doc-api.md` to populate the info section:

| doc-api.md Field | Maps To | Transformation |
|-----------------|---------|----------------|
| "API Type: Internal Process API" | `info.description` API Type | "Internal Process API" -> `Internal` |
| "API Risk Classification: Minor" | `info.description` Risk | "Minor" -> `Low`, "Major" -> `Critical`, "Limited" -> `Limited` |
| "Business Owner: Name (email)" | `info.description` API Owner (business) | `[Name](email)` |
| "Tech Owner: Name (email)" | `info.description` API Owner (technical) | `[Name](email)` |
| "Currently it serves: ..." | `info.description` Overview | Verbatim text |

---

## RAML Constraint Preservation Policy

This is the HIGHEST PRIORITY rule during conversion and subsequent validation fixes.

### Core Rules

1. **If RAML defines `enum`** -> Keep `enum` ONLY. Do NOT add `pattern`.
2. **If RAML defines `pattern`** -> Keep `pattern` ONLY. Do NOT add `enum`.
3. **If RAML defines both** -> Keep both exactly as defined.
4. **If RAML defines neither** -> Only then may you add `pattern` if the validator requires it.
5. **Never derive constraints from `examples`** -> Examples are documentation, not constraints.
6. **Never modify constraint values** to accommodate validator quirks.

### Verification Before Fixing

Before fixing any validation error on a property:
1. Check the original RAML source for that property
2. Compare RAML constraint with OAS constraint
3. Only add missing constraints if they don't exist in RAML

### Example: Correct Handling

**Original RAML:**
```yaml
customerSegmentType:
  type: string
  enum: [A, B, P, S]
  minLength: 1
  maxLength: 1
```

**Correct OAS** (preserves RAML enum):
```yaml
customerSegmentType:
  type: string
  enum:
  - A
  - B
  - P
  - S
  minLength: 1
  maxLength: 1
```

**WRONG** (adding pattern when RAML doesn't have it):
```yaml
customerSegmentType:
  type: string
  pattern: ^[ABPS]$  # WRONG: RAML doesn't define pattern
  enum:
  - A
  - B
  - P
  - S
```

---

## Security Schemes

### OAuth 2.0 (Barclays Standard)

**File: common-libraries/security/security-schemes.yaml**

```yaml
InternalTiaaUsRopcAuth:
  type: oauth2
  description: "OAuth2.0 Resource Owner Password Credentials (ROPC) Grant authentication"
  flows:
    password:
      tokenUrl: 'https://api.barclays.com/oauth2/token'
      scopes:
        read: 'read only'
        write: 'write only'
```

### Using Security in openapi.yaml

```yaml
# Global security (applies to all endpoints)
security:
  - InternalTiaaUsRopcAuth: []

# Reference the scheme
components:
  securitySchemes:
    InternalTiaaUsRopcAuth:
      $ref: './common-libraries/security/security-schemes.yaml#/InternalTiaaUsRopcAuth'
```

Do NOT add per-endpoint security. Use global security only.

---

## Error Responses

### Standard Error Response Codes

| Code | Key | Description |
|------|-----|-------------|
| 400 | `BadRequest` | Invalid request |
| 401 | `Unauthorized` | Authentication required |
| 403 | `Forbidden` | Access denied |
| 404 | `NotFound` | Resource not found |
| 429 | `TooManyRequests` | Rate limit exceeded (**NOT 426!**) |
| 500 | `InternalServerError` | Server error |
| 503 | `ServiceUnavailable` | Service temporarily unavailable |

### Error Response Reference Pattern

**In openapi.yaml paths:**
```yaml
responses:
  "200":
    $ref: './components/endpoint/response-EndpointResponse.yaml#/EndpointResponse'
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

### Error Response Structure (responses.yaml)

```yaml
BadRequest:
  description: "Bad Request - Invalid input"
  headers:
    Cache-Control:
      $ref: './headers.yaml#/Cache-Control'
  content:
    application/json:
      schema:
        $ref: './response-types.yaml#/ErrorResponseType'
      examples:
        example-error-400:
          value:
            $ref: '../examples/example-error-400.json'
```

### Error Response Type (response-types.yaml)

```yaml
ErrorResponseType:
  type: object
  additionalProperties: false
  properties:
    meta:
      type: object
      additionalProperties: true
    errors:
      type: array
      minItems: 0
      maxItems: 50
      items:
        $ref: '#/ErrorType'

ErrorType:
  type: object
  required:
    - id
    - code
    - title
  properties:
    id:
      type: string
      description: "Error identifier"
      example: "9709-4675-2456-7801"
    code:
      type: string
      description: "Error code"
      example: "BAD_REQUEST"
    title:
      type: string
      description: "Short error description"
    detail:
      type: string
      description: "Detailed error message"
    meta:
      type: object
      additionalProperties: true
```

---

## Examples

### External File Examples

```yaml
examples:
  responseExample:
    summary: "success response example"
    externalValue: "../../examples/offers_example.json"
```

### Multiple Examples

```yaml
examples:
  moneyTransfer:
    summary: "Money Transfer example"
    externalValue: "../../examples/money-transfer.json"
  balanceTransfer:
    summary: "Balance Transfer example"
    externalValue: "../../examples/balance-transfer.json"
```

### Error Example JSON Format

**example-error-400.json:**
```json
{
  "errors": [{
    "id": "9709-4675-2456-7801",
    "code": "BAD_REQUEST",
    "title": "The request was invalid",
    "detail": "Request body contains invalid fields."
  }]
}
```

---

## Quick Reference: File Locations

| Component | Location |
|-----------|----------|
| Root file | `oas/openapi.yaml` |
| Headers | `common-libraries/components/headers.yaml` |
| Error responses | `common-libraries/components/responses.yaml` |
| Security | `common-libraries/security/security-schemes.yaml` |
| Parameters | `components/parameters.yaml` |
| Common schemas | `components/common/` |
| Endpoint responses | `components/{endpoint}/response-*.yaml` |
| Endpoint requests | `components/{endpoint}/request-*.yaml` |
| Response body schemas | `components/{endpoint}/response-body/` |
| Request body schemas | `components/{endpoint}/request-body/` |

---

## application.properties Migration (RAML to OAS)

After generating the OAS, update `src/main/resources/application.properties` to replace SDK2 RAML validation properties with SDK3 OAS equivalents.

**SDK2 RAML properties (remove):**
```properties
ramlRequestValidation.isRamlOnClasspath=false
ramlRequestValidation.ramlPath=/api/config/raml.zip
```

**SDK3 OAS properties (add):**
```properties
api.spec.validation.enabled=false
api.spec.location=oas/openapi.yaml
```

Also add to `src/test/resources/application.properties` (or create it if absent):
```properties
api.spec.validation.enabled=false
api.spec.location=oas/openapi.yaml
```

**Why `api.spec.validation.enabled=false`:** The `bap-bld-lib-request-validator` performs OAS-based request validation. In unit tests there is no real HTTP server context, so validation must be disabled to prevent Spring Boot startup failures.

**Why `DISABLE_OAS_GENERATION=true` in `gradle.properties`:** When OAS files are pre-committed and code generation is not needed at build time, add this to `gradle.properties` to prevent the `barclaysApiGenerate` task from throwing a `NullPointerException` (it requires a `root.spec.url` property that is not present in most projects).
