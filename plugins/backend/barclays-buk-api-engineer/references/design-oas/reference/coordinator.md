# OAS Assembly & Guardrail Checks

This file contains the root `openapi.yaml` assembly template and pre-write guardrail checks.
Referenced by SKILL.md Step 8.

---

## Root openapi.yaml Template

Assemble the root spec using this structure:

```yaml
openapi: '3.0.3'   # ALWAYS quote this value — never write openapi: 3.0.3 without quotes
info:
  title: '<from api-config.yaml title, or derive from source: document title / h1 heading cleaned of internal suffixes, or resource noun from endpoint path + "API" — never write placeholder>'
  description: |
    - **API Type:** <from config api_type, or derive from security scheme — InternalTiaaUsRopcAuth → "Internal", any other scheme → "External". Never write placeholder.>
    - **API Risk Classification:** <from config risk_classification, or default to "MEDIUM">
    - **API Owner (business):** <from config business_owner, or "# placeholder — update before publishing">
    - **API Owner (technical):** <from config technical_owner, or "# placeholder — update before publishing">
    - **API Designer:** <from config designer, or "# placeholder — update before publishing">
    - **API Overview:** <from config overview, or derive from source_summary: one sentence describing what the API does — never write a placeholder>
  contact:
    name: '<from config contact_name, or "# placeholder — update before publishing">'
    email: '<from config contact_email, or "# placeholder — update before publishing">'
  version: '<see version derivation rule below>'
externalDocs:  # OMIT this block entirely unless a real Confluence page URL was provided as --input
  # Rules: (1) only write this block when --input contains a Confluence URL
  # (2) url must be the exact Confluence URL from the input — never guess or use base URL only
  # (3) NEVER write https://confluence.barcapint.com alone (base URL without page path)
  description: 'API Documentation'
  url: '<exact confluence page URL from --input>'
servers:
  - url: /<version-from-path>   # EXTEND mode: copy from existing OAS verbatim — never recalculate
    description: '<from config title, or copy from info.title>'
security:
  - InternalTiaaUsRopcAuth: []
tags:
  - name: '<resource noun from endpoint path — e.g. "accounts", "payments">'
    description: '<one-line description of the resource, derived from input>'
components:
  securitySchemes:
    InternalTiaaUsRopcAuth:
      $ref: './common-libraries/security/security-schemes.yaml#/InternalTiaaUsRopcAuth'
  responses:
    InternalServerError:
      $ref: './common-libraries/components/responses.yaml#/InternalServerError'
    Forbidden:
      $ref: './common-libraries/components/responses.yaml#/Forbidden'
    NotFound:
      $ref: './common-libraries/components/responses.yaml#/NotFound'
    BadRequest:
      $ref: './common-libraries/components/responses.yaml#/BadRequest'
    Unauthorized:
      $ref: './common-libraries/components/responses.yaml#/Unauthorized'
    TooManyRequests:
      $ref: './common-libraries/components/responses.yaml#/TooManyRequests'
    ServiceUnavailable:
      $ref: './common-libraries/components/responses.yaml#/ServiceUnavailable'
paths:
  # Path key = resource path WITHOUT version prefix (version is in servers.url)
  # e.g. LLD says POST /v1/accounts → servers.url=/v1, path key=/accounts
  <assembled from endpoint contracts + component $refs>
```

### Metadata Rules (apply before writing any info field)

**Never infer metadata from the input document.** If a value is not explicitly provided in `--config` (api-config.yaml), write the literal placeholder string `# placeholder — update before publishing`. Do not guess owner emails, risk classifications, team names, or contact details from context.

| Field | Where it goes in openapi.yaml | Source of truth | When no config |
|-------|-------------------------------|----------------|----------------|
| `title` | `info.title` | `api-config.yaml` → `title` | Derive from source: h1/title heading cleaned of internal codes and suffixes, or resource noun + "API". Never write placeholder. |
| `contact.name` | `info.contact.name` | `api-config.yaml` → `contact_name` | `# placeholder — update before publishing` |
| `contact.email` | `info.contact.email` | `api-config.yaml` → `contact_email` | `# placeholder — update before publishing` — **never write any @email.com value, even `api-support@barclays.com` or `api-team@example.com`** |
| API Type | `info.description` bullet point | `api-config.yaml` → `api_type` | Accepted: `Internal`, `External`. Derive from security scheme: InternalTiaaUsRopcAuth → `Internal`; any other → `External`. Never write placeholder. |
| API Risk Classification | `info.description` bullet point | `api-config.yaml` → `risk_classification` | Default: `MEDIUM`. Accepted values: `LOW`, `MEDIUM`, `HIGH`. |
| API Owner (business) | `info.description` bullet point | `api-config.yaml` → `business_owner` | `# placeholder — update before publishing` |
| API Owner (technical) | `info.description` bullet point | `api-config.yaml` → `technical_owner` | `# placeholder — update before publishing` |
| API Designer | `info.description` bullet point | `api-config.yaml` → `designer` | `# placeholder — update before publishing` |
| API Overview | `info.description` bullet point | `api-config.yaml` → `overview` | Derive from source: one sentence describing what the API does. Never write placeholder — this is always derivable. |


**`openapi:` must always be quoted.** Write `openapi: '3.0.3'` — never `openapi: 3.0.3`. Some validators reject the unquoted form.

**Tags rule — only resource tags, never internal codes.** Tags must:
- Use the resource noun from the endpoint path (e.g. `/v1/accounts` → tag `accounts`)
- Have a `description` derived from the input
- Never include internal system codes, product codes, lifecycle labels, or any identifier not explicitly named as a tag in the input document. If you are not sure whether something is a valid tag → do not add it.

---

### Version Derivation Rule (Mandatory — BAN rejects non-conforming versions)

BAN requires `info.version` in `vMAJOR.MINOR` format (e.g. `v1.0`, `v2.1`). Apply this derivation in order:

1. **From `api-config.yaml` `version` field** → normalise to `vMAJOR.MINOR`:
   - `"v1.0"` → use as-is ✅
   - `"1.0"` → prepend `v` → `"v1.0"` ✅
   - `"1"` → treat as major only → `"v1.0"` ✅
   - `"v1.0.3"` → strip patch → `"v1.0"` ✅

2. **From the API path prefix** (when no config version set):
   - `/v1/...` → `"v1.0"`
   - `/v2/...` → `"v2.0"`
   - `/v1.1/...` → `"v1.1"`

3. **Default fallback** → `"v1.0"`

**Validation check (always apply before writing):** `info.version` must match `^v[0-9]+\.[0-9]+$`. If it does not, apply the normalisation above. Never write a version that fails this regex — BAN flags it as a CRITICAL.

---

### Server URL and Path Key — MUST NOT duplicate the version prefix

The version prefix belongs in `servers[0].url` only. The `paths:` key must contain the resource path **without** the version prefix.

| LLD endpoint | `servers.url` | `paths` key | ❌ Wrong |
|---|---|---|---|
| `POST /v1/accounts` | `/v1` | `/accounts` | ~~`/v1/accounts`~~ |
| `GET /v2/payments/{id}` | `/v2` | `/payments/{id}` | ~~`/v2/payments/{id}`~~ |

**Rule:** Strip the version segment (`/v1`, `/v2` etc.) from the beginning of every path before writing it as a `paths:` key. The effective URL a consumer calls is `servers.url` + `paths key` — if both contain `/v1`, the consumer would call `/v1/v1/accounts`.

**EXTEND mode:** Copy `servers[0].url` verbatim from the existing OAS — never recalculate.

---

### Parameter Header Rules

**Always add** to every operation (these are Barclays mandatory):
```yaml
- $ref: './common-libraries/components/headers.yaml#/Correlation-ID'
- $ref: './common-libraries/components/headers.yaml#/Authorization'
```

**Add only if mentioned in the input document.** Scan all input sources for any of these names or known aliases:

| Standard header | Recognised aliases (case-insensitive) |
|----------------|--------------------------------------|
| `channelId` | `channel-id`, `channel_id`, `channelIdentifier`, `channel identifier`, `Channel-ID` |
| `deviceId` | `device-id`, `device_id`, `deviceIdentifier`, `device identifier`, `Device-ID` |
| `businessId` | `business-id`, `business_id`, `businessIdentifier`, `business identifier`, `Business-ID` |
| `sourceSortCode` | `source-sort-code`, `source_sort_code`, `sourcesortcode`, `sort code header`, `Source-Sort-Code` |

If **any** alias is found in the input → add the standard `$ref`:
```yaml
- $ref: './common-libraries/components/headers.yaml#/channelId'   # (and/or others found)
```

If **none** are found → do not add. Never auto-add just because the header exists in the template.

If the input describes a header that sounds similar but does not match any alias — flag it as a Red Flag and ask the user whether it maps to a standard header or is a custom one requiring `type-common-headers.yaml`.

**`type-common-headers.yaml` — API-specific custom headers only**

Generate `components/common/type-common-headers.yaml` **only** when the input document defines headers that are not already in `common-libraries/components/headers.yaml`. Examples: a domain-specific routing header, a custom business context header unique to this API.

- If no custom headers exist in the input → do NOT create this file
- If custom headers are found → define them in this file and reference as `$ref: './components/common/type-common-headers.yaml#/{headerName}'`
- Never use this file to duplicate any header that already exists in `common-libraries/components/headers.yaml`

---

### Mandatory Response Block — copy this exactly for every operation

The 7 standard error responses are NOT optional. Do not generate responses from scratch — start from this block and add domain-specific codes (422, 502, 504 etc.) only if mentioned in the source:

```yaml
      responses:
        '{success_code}':       # 200, 201, 202, or 204 — from source
          ...                   # success schema
        '400':
          $ref: '#/components/responses/BadRequest'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '403':
          $ref: '#/components/responses/Forbidden'
        '404':
          $ref: '#/components/responses/NotFound'
        '429':
          $ref: '#/components/responses/TooManyRequests'
        '500':
          $ref: '#/components/responses/InternalServerError'
        '503':
          $ref: '#/components/responses/ServiceUnavailable'
```

All 7 must be present on every operation. Missing any of them will fail BAN. Do not deviate from this structure — never replace `$ref: '#/components/responses/...'` with direct file refs.

---

### Path Item Structure

Every path item must have BOTH `summary` and `description` at the path level (not just operation level):

```yaml
paths:
  /accounts:    # NOT /v1/accounts — strip version prefix, it lives in servers.url
    summary: 'Account Operations'
    description: 'Operations for managing credit card accounts'
    post:
      summary: 'Open a new account'
      operationId: 'openAccount'
      ...
```

### Extend Mode Assembly

**Preserve verbatim from existing OAS — never recalculate these:**
- `servers[*].url` — copy exactly as-is (e.g. `/` stays `/`, `/v1` stays `/v1`)
- `info.version` — keep as-is unless `--config` explicitly overrides
- `security` — keep as-is (only change if input source explicitly specifies a different scheme)

**Case 1 — Endpoint is NEW (not in existing spec):**
- Append new path to existing openapi.yaml
- Generate and write new component files
- Never touch existing component files

**Case 2 — Endpoint EXISTS in existing spec:**
Input is the source of truth. Apply full replacement at the property level:

```
For each property in the input-parsed schema:
  If property exists in existing → replace with input version  (UPDATED)
  If property is new in input    → add it                      (ADDED)

For each property in the existing component file:
  If property is NOT in the input → remove it                  (REMOVED)
```

Tell user before writing:
`"Merging {METHOD} {path} — {N} fields updated, {M} fields added, {K} fields removed."`

Record in generation report under `## Merge Changes`:
- **Updated**: field name + what changed (e.g. `pattern`, `maxLength`, `description`)
- **Added**: new field names
- **Removed**: deleted field names — so the change is auditable

Write the merged component files. Preserve all other endpoints and components untouched.

**Case 3 — `--endpoints` not specified (append-only default):**
- For `openapi.yaml`: start from the existing spec content, append any new paths found in input. Copy existing paths verbatim — do NOT re-apply CISO defaults or regenerate existing content.
- For component files: copy all existing component files unchanged. Only generate new component files for genuinely new endpoints.
- For `common-libraries/`: copy from existing OAS unchanged.

---

## Pre-Write Guardrail Checks (G7–G14)

Apply these checks to the assembled spec BEFORE writing files. These prevent Barclays
portal submission failures.

### G7 — Sensitive field names in `required:` arrays

Scan all schema `required:` arrays for these field names:
`accountNumber`, `sortCode`, `cardNumber`, `pan`, `cvv`, `pin`, `password`, `secret`, `address`

**Do NOT automatically remove them.** The correct action depends on the business context:

| Scenario | Action |
|----------|--------|
| Field can be made optional | Remove from `required:`, add to description: `"Sensitive field — must be provided but omitted from required array per CISO data-leakage rules"` |
| Field is genuinely required and cannot be optional | Keep in `required:`, get CSO sign-off, document as known exception |

**Always raise as a Red Flag in the generation report:**
`"file:fieldName — sensitive field name in required array. Verify with CSO: make optional or obtain data-leakage exception."`

Do not silently mutate the required array — flag for human decision.

### G8 — `format: email` usage

Scan all schema properties. If any property has `format: email`, remove the `format:` line.
Replace with `type: string` + `minLength` + `maxLength` + CSO-approved email pattern from `rules.md` String Properties section.
Do NOT leave the field as `type: string` with `maxLength` only — that violates the CISO pattern requirement.

### G9 — Missing CISO schema properties

Every object must have: `deprecated: false`, `nullable: false`, `additionalProperties: false`
Every string **without `enum`** must have: `minLength` and `maxLength`
Every string **with `enum`** must have: enum values only — do NOT add `minLength`, `maxLength`, or `pattern`
Every integer must have: `minimum` and `maximum`

If any are missing — add them per the CISO rules in rules.md.

### G10 — Path items missing summary/description

Every path item (the path key, not the operation) must have `summary:` and `description:`.

### G11 — POST 201 missing Location header

G11 applies ONLY to POST endpoints returning 201. It does NOT apply to 200, 202, or 204 responses.

Every POST endpoint with a 201 response must include a `Location` header.
Header schema must include `deprecated: false` and `nullable: false`:

```yaml
'201':
  headers:
    Location:
      description: 'URL of the newly created resource'
      schema:
        type: string
        deprecated: false
        nullable: false
        minLength: 1
        maxLength: 250
        pattern: '^/v[0-9]{1,2}/[a-zA-Z0-9/_-]{1,240}$'  # canonical — see rules.md. Supports /v1/, /v2/. Not /v1.1/ (use header versioning for minor versions).
      example: '/v1/accounts/b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22'
```

### G12 — Inline responses missing examples

Standard responses (400, 401, 403, 404, 429, 500, 503) are defined in `components.responses` and use `$ref` — they do not need `examples:`.

Any response NOT in that standard set that uses an inline schema must have an `examples:` block. This includes: 202, 409, 422, 502, 504, and any other non-standard code.

Exempt from `examples:` requirement: responses with no body (204, 304) — they have no `content` block at all.

Non-standard responses (409, 422, 502, 504) **must only be generated if explicitly mentioned in the input document.** Do not add them by default.

When explicitly required by the input, use an inline example with the correct business-specific code — do NOT reuse a standard error example file (e.g. `example-error-400-bad-request.json`) as the `code` field will be wrong:

```yaml
'409':
  description: '<from input>'
  headers:
    Cache-Control:
      $ref: './common-libraries/components/headers.yaml#/Cache-Control'
  content:
    application/json:
      schema:
        $ref: './common-libraries/components/response-types.yaml#/ErrorResponseType'
      examples:
        ConflictError:
          value:
            title: '<from input>'
            code: 'CONFLICT'
            message: '<from input>'
```

Apply same pattern for 422 (`UNPROCESSABLE_ENTITY`), 502 (`BAD_GATEWAY`), 504 (`GATEWAY_TIMEOUT`) — derive code and description from input.

---

### G14 — Enum fields must not have minLength, maxLength, or pattern

Scan all generated schema properties. If a property has `enum`, remove `minLength`, `maxLength`, and `pattern` if they are present alongside it. Enum is the sole constraint — having both confuses BAN's `type-string` rule and causes CRITICAL failures.

**Auto-fix:** For any property with `enum` AND (`minLength` OR `maxLength` OR `pattern`) → remove all three. The enum values themselves provide the full constraint set.

---

### G13 — Path key contains verb segment (BAN `resources-verb` rule)

Scan every `paths:` key before writing. A path key must not contain a verb segment.

**Verb words that must not appear as path segments:** `create`, `update`, `delete`, `get`, `fetch`, `retrieve`, `add`, `remove`, `submit`, `send`, `process`, `validate`, `check`, `search`, `find`, `list`, `open`, `close`, `cancel`, `activate`, `deactivate`, `freeze`, `unfreeze`, `apply`, `approve`, `reject`, `accept`, `decline`

**Auto-fix rule:**
- If the LAST segment is a verb AND the HTTP method already expresses that intent (e.g. `POST /v1/applications/create` → POST expresses create) → remove the verb segment: `/v1/applications/create` → `/v1/applications`
- After removing the verb segment, re-derive the `operationId` from the corrected path
- Log the fix in the generation report REST Standards Check table

**Do not wait for BAN to catch this.** G13 runs as a pre-write guardrail — the same as G8–G12 — so the generated spec never contains a verb path segment.
