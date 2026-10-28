---
name: barclays-api-standards
description: Barclays API standards for validating OpenAPI 3.x specifications. Covers OAS structure, data types, field constraints, resource naming, HTTP verbs, response codes, content, error responses, headers, pagination, and API naming. Use when validating any OAS spec against Barclays internal standards.
color: red
---

> **Source:** Barclays OpenAPI Specification Standard, API Coding Standard, API Naming Standard
> **Owner:** BUK
> **Review trigger:** On any Barclays API standards document revision
> **Status:** Reviewed

# Skill: Barclays API Standards — Complete Reference

## When to Use This Skill

Use this skill when:
- Validating an OpenAPI 3.x specification against Barclays standards
- Checking compliance with Barclays naming, coding, and OAS structure rules
- Generating a standards compliance report for an API spec

**Sources:** Barclays OpenAPI Specification Standard, Barclays API Coding Standard, Barclays API Naming Standard

## Quick Start

Validate an OpenAPI spec against Barclays standards:

1. Load the spec file: `Read openapi.yaml`
2. Check each section below against the spec
3. Report violations in this format:
   ```
   [SEVERITY] Standard X.Y — Description
   File: openapi.yaml:lineNumber
   Fix: What to change
   ```

---

## Standard 1: OAS Specification Structure (from Barclays OpenAPI Specification Standard)

### 1.1 OAS Version & Format

- **MUST** use OpenAPI 3.x (recommended: v3.1.1 as of 2025, minimum v3.0.2)
- **MUST** be written in YAML (not JSON — JSON requires explicit API Tech Domain approval)
- Root document **MUST** be named `openapi.yaml`
- Documentation **MUST** be written in CommonMark markdown

### 1.2 Root OpenAPI Object — Mandatory Fields

| Field | Barclays Requirement |
|---|---|
| `openapi` | REQUIRED — must be semantic version matching OAS spec used (e.g. "3.0.2") |
| `info` | REQUIRED |
| `servers` | REQUIRED — may be empty array during development; must list all environments once deployed |
| `paths` | REQUIRED |
| `components` | REQUIRED |
| `security` | REQUIRED — list of security mechanisms for the whole API |
| `tags` | REQUIRED — must include: (a) resource names in camelCase, (b) TC number e.g. "tc31", (c) lifecycle phase prefixed with "lifecycle:" e.g. "lifecycle:live" |
| `externalDocs` | REQUIRED — link to confluence/sharepoint for internal APIs; public portal for external APIs |
| Specification Extensions | FORBIDDEN at all levels |
| `servers` at operation level | NOT USED — servers object only at API root level |

### 1.3 Info Object — Mandatory Fields

| Field | Barclays Requirement |
|---|---|
| `title` | REQUIRED — must match API naming standard (≤50 chars, Title Case) |
| `description` | REQUIRED — must describe resources, operations, security, constraints |
| `termsOfService` | REQUIRED for external APIs only |
| `contact.name` | REQUIRED |
| `contact.url` | REQUIRED for external APIs; recommended for internal |
| `contact.email` | REQUIRED |
| `license.name` | REQUIRED for external APIs |
| `license.url` | REQUIRED for external APIs |
| `version` | REQUIRED |

### 1.4 Operation Object — Mandatory Fields

| Field | Barclays Requirement |
|---|---|
| `summary` | REQUIRED — short summary of what the operation does |
| `description` | SHOULD — recommended but not mandatory |
| `operationId` | REQUIRED — MUST follow **camelCase** naming |
| `security` | REQUIRED — declare security for every operation |
| `deprecated` | REQUIRED — default false |
| `responses` | REQUIRED — at least one response |
| `servers` at operation level | NOT USED |

### 1.5 Path Item Object

| Field | Barclays Requirement |
|---|---|
| `summary` | REQUIRED |
| `description` | SHOULD |

At least one HTTP method (get, put, post, delete, patch, head, options, trace) **MUST** be defined per path.

### 1.6 Parameter Object — Mandatory Fields

| Field | Barclays Requirement |
|---|---|
| `name` | REQUIRED |
| `in` | REQUIRED — `query`, `header`, `path`, or `cookie` |
| `description` | REQUIRED |
| `required` | REQUIRED (path params must be `true`) |
| `deprecated` | REQUIRED |
| `allowEmptyValue` | REQUIRED |
| `content` property | **FORBIDDEN** — use `schema` instead (security risk) |

**Approved parameter serialisation styles:**

| Location | Style | Explode | Approved For |
|---|---|---|---|
| `query` | `form` | `true` | strings, arrays, objects |
| `query` | `form` | `false` | strings, arrays (not objects) |
| `query` | `spaceDelimited` | `true`/`false` | arrays only |
| `query` | `pipeDelimited` | `true`/`false` | arrays only |
| `path` | `simple` | `false` | strings only |
| `header` | `simple` | `true`/`false` | strings, arrays |
| `cookie` | `form` | `true` | empty, strings only |
| `cookie` | `form` | `false` | all types |

### 1.7 Request Body Object

| Field | Barclays Requirement |
|---|---|
| `description` | REQUIRED |
| `content` | REQUIRED |
| `required` | REQUIRED |
| At least one of `example` or `examples` | REQUIRED |

### 1.8 Response Object

| Field | Barclays Requirement |
|---|---|
| `description` | REQUIRED |
| `content` | REQUIRED |

### 1.9 Components Object

- Component keys **MUST** match `^[a-zA-Z][a-zA-Z0-9]+$` (e.g. `UserType` ✅, `user-type` ❌, `UserType3` ✅)
- XML responses/requests **FORBIDDEN** unless explicitly approved by API Tech Domain

### 1.10 Links

- Links **MUST** refer to operations **within the same API specification** — not to external APIs

### 1.11 External Documentation Object

| Field | Barclays Requirement |
|---|---|
| `description` | REQUIRED |
| `url` | REQUIRED |

### 1.12 Tags Object

| Field | Barclays Requirement |
|---|---|
| `name` | REQUIRED — tag names must be **camelCase** |
| `description` | OPTIONAL |

---

## Standard 2: Data Types & Field Constraints (from Barclays OpenAPI Specification Standard)

### 2.1 Approved Type+Format Combinations ONLY

Use ONLY these combinations (others require explicit API Tech Domain approval):

| Use Case | `type` | `format` |
|---|---|---|
| 32-bit integer | `integer` | `int32` |
| 64-bit integer | `integer` | `int64` |
| Float | `number` | `float` |
| Double | `number` | `double` |
| String | `string` | _(none)_ |
| Base64 | `string` | `byte` |
| Binary | `string` | `binary` |
| Boolean | `boolean` | _(none)_ |
| Date | `string` | `date` |
| Date-time | `string` | `date-time` |
| Password | `string` | `password` |

### 2.2 Mandatory Field Constraints

**For ALL schema properties:**
- `description` **MUST** be present on every property

**For string properties:**
- Either (`minLength` AND/OR `maxLength`) OR `pattern` **MUST** be present
- If `pattern` is used, it MUST follow GIS standards for regular expressions

**For numeric properties:**
- `minimum` **MUST** be specified
- `maximum` **MUST** be specified

**For array properties:**
- `minItems` **MUST** be specified
- `maxItems` **MUST** be specified
- `items` **MUST** be specified

**For any property:**
- `nullable` **MUST** be specified (default: false)
- `example` **MUST** be specified
- `deprecated` **MUST** be specified (default: false)

### 2.3 Discriminator (when using polymorphism)

- `mapping` field in discriminator **MUST** be present when discriminator is used
- `discriminator` is only legal with `oneOf`, `anyOf`, or `allOf`

---

## Standard 3: Resource Naming Standard (from Barclays API Coding Standard)

### 3.1 Resource Name Rules

| Rule | Requirement |
|---|---|
| Plural nouns | **MUST** use plural nouns (e.g. `/customers`, `/accounts` — NOT `/customer`, `/account`) |
| No verbs | **MUST NOT** use verbs or verb+noun combos (e.g. NOT `/updateCustomerRecords`, NOT `/getAccount`) |
| Consistent case | **MUST** use ONE case style throughout entire API |
| Snake_case | **AVOID** — use camelCase, PascalCase, or kebab-case instead |
| No mixing | **MUST NOT** mix case styles within the same API |
| Cross-domain | **SHOULD** use same case across all APIs in same domain |
| Character set | Must match `[a-zA-Z0-9_-]` (RFC3986) |

**Approved case styles:**
- `camelCase` — e.g. `telephoneNumbers` ✅ APPROVED
- `PascalCase` — e.g. `TelephoneNumbers` ✅ APPROVED
- `kebab-case` — e.g. `telephone-numbers` ✅ APPROVED
- `snake_case` — e.g. `telephone_numbers` ⚠ AVOID

---

## Standard 4: HTTP Verbs Standard (from Barclays API Coding Standard)

### 4.1 Collection Resources (paths without `{id}` at end)

| Method | Allowed | Meaning |
|---|---|---|
| GET | ✅ | List items |
| HEAD | ✅ | List (no body) |
| POST | ✅ | Create new item |
| PUT | ✅ | Bulk replace |
| PATCH | ✅ | Bulk partial update |
| DELETE | ✅ | Delete all |

### 4.2 Item Resources (paths ending with `{id}` or specific identifier)

| Method | Allowed | Meaning |
|---|---|---|
| GET | ✅ | Retrieve item |
| HEAD | ✅ | Retrieve (no body) |
| PUT | ✅ | Replace item |
| PATCH | ✅ | Partial update |
| DELETE | ✅ | Delete item |
| POST | ❌ **MUST NOT** | POST must not be implemented on a specific item |

---

## Standard 5: HTTP Response Codes Standard (from Barclays API Coding Standard)

### 5.1 Response Code Ranges — Use Correctly

| Range | Meaning |
|---|---|
| 1xx | Request received, processing in progress |
| 2xx | Request processed successfully |
| 3xx | Client must take further action |
| 4xx | Client request error |
| 5xx | Server error processing the request |

### 5.2 Rules

- **MUST NOT** return 200 with an error code in the response body
- Every operation **MUST** have at least one 2xx response defined
- **MUST** align to standard codes below; avoid obscure codes

### 5.3 Approved Response Codes

```
200 - OK
201 - Created
202 - Accepted (async processing)
204 - No Content
304 - Not Modified
400 - Bad Request
401 - Unauthorised
403 - Forbidden
404 - Not Found
405 - Method Not Allowed
406 - Not Acceptable
429 - Too Many Requests
500 - Internal Server Error
502 - Bad Gateway
503 - Service Unavailable
```

### 5.4 Expected Response Codes by Method

| Method | Expected Success Code |
|---|---|
| POST | 201 (or 200) |
| GET | 200 |
| PUT | 200 |
| PATCH | 200 |
| DELETE | 204 (or 200) |

---

## Standard 6: API Content Standard (from Barclays API Coding Standard)

### 6.1 Content Type Rules

- Content type **SHOULD** always be `application/json` or `application/vnd.api+json`
- `application/xml` only where strong business reason exists AND only IN ADDITION to JSON
- Binary data: use most appropriate MIME type (e.g. `application/pdf`)

### 6.2 Request/Response Structure

- A JSON **object MUST** be at root of every request/response
- Top-level keys MUST include at least one of: `data`, `errors`, `meta`
- `data` and `errors` **MUST NOT** coexist in same document
- Collections **MUST** be represented as an array even if single item or empty

### 6.3 JSON Naming

- JSON property names **MUST** be **camelCase** (e.g. `accountId`, `firstName`)

### 6.4 Date/Time Formats

| Type | Format | Example |
|---|---|---|
| Date only | `yyyy-mm-dd` (RFC3339 full-date) | `2026-07-07` |
| Time only | `hh:mm:ss[.ff...]` (RFC3339 partial-time) | `14:30:00` |
| Date-time | RFC3339 date-time | `1996-12-19T16:39:57-08:00` |

- Industry standard codes **MUST** be used where available (e.g. ISO currency codes)

---

## Standard 7: Error Response Standard (from Barclays API Coding Standard)

### 7.1 Error Structure Rules

- Error objects **MUST** be returned as an **array** keyed by `errors` at the top level
- Example:
  ```json
  {
    "errors": [
      {
        "id": "9709-4675-2456-7801",
        "code": "LENGTH_VALIDATION_ERROR",
        "title": "Value is too short",
        "detail": "First name must contain at least three characters."
      }
    ]
  }
  ```

### 7.2 Error Object Keys (all SHOULD be present)

| Key | Description |
|---|---|
| `id` | Unique identifier for this occurrence |
| `code` | Application-specific error code (string) |
| `title` | Short human-readable summary — MUST NOT change between occurrences |
| `detail` | Human-readable explanation specific to this occurrence |
| `meta` | Non-standard meta-information object |

---

## Standard 8: HTTP Headers Standard (from Barclays API Coding Standard)

### 8.1 Request Headers

| Header | Type | Requirement |
|---|---|---|
| `Correlation-ID` | Internal API | **MANDATORY** — UUID format per RFC4122 (e.g. `f81d4fae-7dec-11d0-a765-00a0c91e6bf6`) |
| `Channel-ID` | Internal API | OPTIONAL — format: `[A-Za-z0-9-_]{3,20}` |
| `Agent-ID` | Internal API | OPTIONAL (proposed) — format: `[A-Z][0-9]{8}` |

### 8.2 Response Headers

| Header | Requirement |
|---|---|
| `Content-Type` | MUST be present when response includes a body |
| `Location` | MUST be present for 201 Created responses pointing to newly created resource |
| `Cache-Control` | SHOULD be `no-cache, no-store, must-revalidate` for non-cacheable responses |

---

## Standard 9: Pagination Standard (from Barclays API Coding Standard)

### 9.1 Pagination Rules

- Endpoints returning collections **SHOULD** use pagination for large result sets
- When used, **MUST** implement exactly one of three styles

### 9.2 Pagination Styles

**Page-based (RECOMMENDED):**
```
GET /v1/accounts/{accountId}/transactions?page=1&size=10
```
- `page[size]` — number of objects to return (ordinal, minimum 1)
- `page[number]` — which page (ordinal, starts at **1**)

**Offset-based:**
```
GET /v1/accounts/{accountId}/transactions?offset=0&limit=10
```
- `page[limit]` — number of objects
- `page[offset]` — which object to return first (starts at **0**)

**Cursor-based:**
```
GET /v1/accounts/{accountId}/transactions?cursor=36993426599129130&count=10
```
- `page[count]` — number of objects
- `page[cursor]` — pointer to first object (e.g. last record id)

### 9.3 Pagination Requirements

- `meta.totalPages` **SHOULD** be included in paginated responses
- Maximum values **MUST** be enforced on all pagination parameters
- Services **MUST** provide bounded time periods on paged queries of dynamic result sets
- **MUST NOT** offer paging on unbounded highly dynamic result sets

---

## Standard 10: API Naming Standard (from Barclays API Naming Standard)

### 10.1 Required Name Format

```
{Domain} {Capability} [Command | Query | Notification | Feed | Management] {xAPI | gAPI | API}
```

**Qualifiers (optional but use when helpful):**

| Qualifier | Use When |
|---|---|
| `Command` | Create, update, or delete only (no reads) |
| `Query` | Read only |
| `Notification` | Async messaging / notifications |
| `Feed` | Data feed to another bounded context |
| `Management` | Mix of CRUD + async |

**Suffix (mandatory, one of):**

| Suffix | Meaning |
|---|---|
| `xAPI` | Experience layer API (customer-facing) |
| `gAPI` | Gateway API (fronts external third-party connection) |
| `API` | Domain/internal API |

### 10.2 API Title Rules

| Rule | Requirement |
|---|---|
| Case | **MUST** use Title Case (first letter of each word capitalised) |
| "Barclays" | **SHOULD NOT** include the word Barclays |
| "External", "Internal", "Process" | **MUST NOT** include these words |
| Consumer names (e.g. Salesforce, Appian) | **MUST NOT** be included |
| Project names (e.g. kite, Athena) | **MUST NOT** be included |
| Maximum length | **MUST NOT** exceed 50 characters |
| Consistency | **MUST** be identical across all specs, docs, portals, service management records |
| Descriptiveness | **SHOULD** clearly describe what the API does |

### 10.3 Exemptions

- Industry/regulator-provided APIs (Open Banking, PSD2): externally provided names SHOULD be used
- DR instances are exempt from naming rules (Active/Active deployment)

---

## Validation Output Format

When performing validation, produce a report in this JSON structure:

```json
{
  "spec_file": "path/to/openapi.yaml",
  "overall_status": "PASS | WARN | FAIL",
  "standards_checked": [
    "Barclays OAS Specification Standard",
    "Barclays API Coding Standard",
    "Barclays API Naming Standard"
  ],
  "summary": {
    "total_checks": 0,
    "passed": 0,
    "warnings": 0,
    "errors": 0
  },
  "categories": {
    "oas_structure": { "status": "PASS|WARN|FAIL", "errors": [], "warnings": [] },
    "data_types": { "status": "PASS|WARN|FAIL", "errors": [], "warnings": [] },
    "resource_naming": { "status": "PASS|WARN|FAIL", "errors": [], "warnings": [] },
    "http_verbs": { "status": "PASS|WARN|FAIL", "errors": [], "warnings": [] },
    "response_codes": { "status": "PASS|WARN|FAIL", "errors": [], "warnings": [] },
    "content_standards": { "status": "PASS|WARN|FAIL", "errors": [], "warnings": [] },
    "error_responses": { "status": "PASS|WARN|FAIL", "errors": [], "warnings": [] },
    "http_headers": { "status": "PASS|WARN|FAIL", "errors": [], "warnings": [] },
    "pagination": { "status": "PASS|WARN|FAIL", "errors": [], "warnings": [] },
    "api_naming": { "status": "PASS|WARN|FAIL", "errors": [], "warnings": [] }
  },
  "errors": [
    {
      "category": "oas_structure",
      "standard": "Barclays OAS Specification Standard §1.3",
      "severity": "ERROR",
      "location": "info.contact",
      "message": "info.contact is required by Barclays standards",
      "rule": "Contact information must be provided for all APIs"
    }
  ],
  "warnings": [
    {
      "category": "oas_structure",
      "standard": "Barclays OAS Specification Standard §1.2",
      "severity": "WARN",
      "location": "info.description",
      "message": "info.description does not mention security mechanism",
      "rule": "Description should describe security mechanism and constraints"
    }
  ],
  "recommendations": [
    "Add Correlation-ID as a required header parameter to all internal API operations",
    "Add minimum/maximum constraints to all numeric properties"
  ]
}
```

**Overall Status Rules:**
- `FAIL` — one or more MUST/REQUIRED violations found
- `WARN` — only SHOULD/RECOMMENDED violations found, no MUST violations
- `PASS` — all checked rules pass

---

## Quick Checklist for Agents

Use this checklist when validating a spec. Each item maps to a standard above.

**ERRORS (MUST/REQUIRED violations — report as errors):**
- [ ] OAS version is 3.x
- [ ] Written in YAML
- [ ] Root file named `openapi.yaml`
- [ ] `info.title` present
- [ ] `info.description` present
- [ ] `info.contact.name` present
- [ ] `info.contact.email` present
- [ ] `info.version` present
- [ ] `tags` present with resource names, TC number, lifecycle phase
- [ ] `externalDocs` present
- [ ] `security` defined at root level
- [ ] Every operation has `summary`
- [ ] Every operation has `operationId` in **camelCase**
- [ ] Every operation has `security` defined
- [ ] Every operation has at least one 2xx response
- [ ] Every schema property has `description`
- [ ] String properties have length constraints or pattern
- [ ] Numeric properties have `minimum` and `maximum`
- [ ] Array properties have `minItems`, `maxItems`, `items`
- [ ] Every property has `nullable` specified
- [ ] Every property has `example`
- [ ] Every property has `deprecated`
- [ ] Component keys match `^[a-zA-Z][a-zA-Z0-9]+$`
- [ ] Resource paths use plural nouns
- [ ] Resource paths do not use verbs
- [ ] Case is consistent across all resource paths
- [ ] POST not defined on item paths (paths ending with `/{id}`)
- [ ] `Correlation-ID` header defined in parameters/components for internal APIs
- [ ] API title ≤ 50 characters
- [ ] API title uses Title Case
- [ ] No Specification Extensions used

**WARNINGS (SHOULD violations — report as warnings):**
- [ ] `info.description` covers security and constraints
- [ ] Every operation has `description` (SHOULD)
- [ ] snake_case used in resource names (AVOID)
- [ ] `meta.totalPages` included in paginated responses
- [ ] `Location` header defined for 201 responses
- [ ] `Cache-Control` header defined for non-cacheable responses
- [ ] API title does not contain "Barclays"
- [ ] API title does not contain "External"/"Internal"/"Process"
- [ ] JSON property names are camelCase
- [ ] Date fields use `string/date` format
- [ ] DateTime fields use `string/date-time` format

---

## Source Attribution

**Primary sources:**
- Barclays OpenAPI Specification Standard (internal document, BUK API Engineering) — §1 OAS structure rules, §2 data type and field constraint rules
- Barclays API Coding Standard (internal document, BUK API Engineering) — §3 resource naming, §4 HTTP verbs, §5 response codes, §6 content standards, §8 HTTP headers, §9 pagination
- Barclays API Naming Standard (internal document, BUK API Engineering) — §10 title format, domain/capability segment rules, `xAPI`/`gAPI`/`API` suffix convention

**Training knowledge applied:**
- OpenAPI 3.x specification — standard field names, `components/schemas` key format rules, `operationId` camelCase convention
- HTTP semantics — correct use of 200/201/204/400/401/403/404/500 status codes
- Pagination patterns — page-based, offset-based, cursor-based parameter naming

**Known limitations:**
- Standards content reflects the versions reviewed at skill creation date; Barclays may revise the underlying standard documents without updating this skill — always check with the API Tech Domain team for the latest version
- The §5 response code approved list and §10 naming rules in this skill are derived from available documentation; edge cases not covered in the source documents are handled by conservative defaults
- External API requirements (`info.termsOfService`, `info.license`) are documented but their exact Barclays-approved values are not enumerated here

---

## Agent Self-Check

- [ ] I have cross-referenced every rule in this skill against the named Barclays standard document section (§1–§10) before applying it
- [ ] I have not invented rule content — every MUST/REQUIRED/SHOULD is traceable to a named standard section
- [ ] I have reported standard section references (e.g., `[oas_structure §1.3]`) alongside each error or warning in my output
- [ ] I have flagged when the `barclays-buk-standards:api-design` skill is a placeholder and standards checks were skipped
- [ ] I have not applied `external`-only rules (e.g., `info.termsOfService`, `info.license`) when `API_TYPE` is `internal`
- [ ] I have produced both the human-readable summary and the machine-readable JSON report as required by the Output Format section
- [ ] I have not modified the spec file — my role is read-only validation only
