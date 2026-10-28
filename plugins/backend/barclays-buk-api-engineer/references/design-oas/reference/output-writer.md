# Output Writer

You receive the assembled OAS content and write it to disk in the correct split-file structure.

## Barclays Portal Path Item Rules — every path must have summary AND description

Every path item block (the path key itself, not the operation) must have both `summary:` and
`description:` fields. Missing these causes `path-item-summary` and `path-item-description`
portal errors.

```yaml
paths:
  /accounts:    # version prefix stripped — /v1 lives in servers.url
    summary: 'Account Opening Operations'         # REQUIRED — path-item level
    description: 'Operations for opening new credit card accounts'  # REQUIRED
    post:
      summary: 'Open a new credit card account'   # operation-level summary
      ...
```

## 201 Responses Must Include Location Header

Every POST endpoint that returns 201 must include a `Location` header pointing to the new resource.
Header schema must include `deprecated: false` and `nullable: false`:

```yaml
'201':
  headers:
    Cache-Control:
      $ref: './common-libraries/components/headers.yaml#/Cache-Control'
    Location:
      description: 'URL of the newly created resource'
      schema:
        type: string
        deprecated: false
        nullable: false
        minLength: 1
        maxLength: 250
        pattern: '^/v[0-9]{1,2}/[a-zA-Z0-9/_-]{1,240}$'  # supports /v1/, /v2/ etc.
      example: '/v1/accounts/b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22'
```

## Inline Response Schemas Must Have Examples

Any response that uses an inline schema (not a `$ref` to `#/components/responses/`) must include
an `examples:` block. This applies to non-standard responses like 409, 422, 502, 504.
Missing this causes `oas3-example-tag-validation` portal errors:

```yaml
'409':
  description: 'Conflict'
  content:
    application/json:
      schema:
        $ref: './common-libraries/components/response-types.yaml#/ErrorResponseType'
      examples:
        ConflictError:
          value:
            errors:
              - id: '9709-4675-2456-7801'
                code: 'CONFLICT'
                title: 'The resource already exists or conflicts with existing data.'
```

## Inline Parameter Schemas — strings need minLength/maxLength/pattern

Any inline header or path parameter schema of type string must also have `minLength`, `maxLength`,
and `pattern`. Example for a UUID path parameter:

```yaml
schema:
  type: string
  minLength: 36
  maxLength: 36
  pattern: '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
```

---

## File Sourcing Rules (EXTEND mode vs GREENFIELD)

**EXTEND mode (spec-path provided to update-oas) — output must be a complete standalone OAS:**

The output directory is new, so ALL files must be present. Source each file as follows:

| File | Source | Reason |
|------|--------|--------|
| `openapi.yaml` | **Regenerate** — existing paths + merged/new endpoint | Must reflect all changes |
| `components/{resource}/type-{Op}*.yaml` for merged/new endpoint | **Regenerate from input** | Input is source of truth |
| `components/{resource}/type-{Op}*.yaml` for untouched endpoints | **Copy from existing spec** | Unchanged — no regeneration |
| `common-libraries/components/headers.yaml` | **Copy from existing spec** | Headers now live in common-libraries; never regenerate |
| `common-libraries/` (all files) | **Copy from existing spec using file copy — do not regenerate or rewrite from reference templates** | Preserves exact existing content including NOTICE comments and formatting |
| `examples/example-{operationId}-*.json` for merged/new endpoint | **Regenerate** | May have changed fields |
| `examples/` for untouched endpoints | **Copy from existing spec** | Unchanged |

**Method change (same path, different HTTP method in existing spec):**

| File | Action |
|------|--------|
| `openapi.yaml` | Remove old method operation, add new method operation |
| Old method component files (e.g. `type-PostAccounts*.yaml`) | Do NOT delete — copy to output as-is, flag as `ORPHANED` in generation report |
| New method component files (e.g. `type-GetAccounts*.yaml`) | Regenerate from input |

Orphaned files are flagged in the report so the developer can decide to delete them manually after review. Never silently delete existing component files.

**GREENFIELD mode (no existing spec) — generate everything fresh from templates.**

---

## Directory Structure to Create

```
{output-dir}/
├── openapi.yaml
├── generation-report.md
├── examples/
│   ├── example-{operationId}-request.json
│   └── example-{operationId}-response.json
├── components/
│   └── {resource}/
│       ├── type-{OperationId}RequestType.yaml
│       ├── type-{OperationId}RequestData.yaml
│       ├── type-{OperationId}ResponseType.yaml
│       └── type-{OperationId}ResponseData.yaml   ← only when response has a data wrapper with fields
└── common-libraries/
    ├── security/
    │   └── security-schemes.yaml
    ├── components/
    │   ├── headers.yaml
    │   ├── responses.yaml
    │   └── response-types.yaml
    └── examples/
        ├── example-error-400-bad-request.json
        ├── example-error-401.json
        ├── example-error-403.json
        ├── example-error-404.json
        ├── example-error-429.json
        ├── example-error-500.json
        └── example-error-503.json
```

## Single-File Mode (`--output-format single`)

Write ONLY `openapi.yaml` with all content inlined (no `$ref` to external files).
Still write `generation-report.md`.

## Extend Mode Rules

For each file to write:
1. Check if the file exists at the target path
2. **If it exists AND the endpoint was named in `--endpoints`** → overwrite with merged content (input is source of truth — see merge algorithm in component_builder.md)
3. **If it exists AND the endpoint was NOT named in `--endpoints`** → skip, use existing $ref path in openapi.yaml
4. If it does not exist → create it

## Example File Format — `value:` Wrapper Required

**ALL example JSON files** (both endpoint examples and error examples) MUST be wrapped in a
top-level `value:` key. BAN validator (`oas3-valid-schema-example`) rejects flat JSON objects.

```json
{
  "value": {
    "field1": "...",
    "field2": "..."
  }
}
```

Only add nested structure (e.g. a `data` property) in the example if the source document explicitly defines it. Never impose structural patterns not mentioned in the source.

**Null field rule:** Never write `null` for a field that has `type: string`, `type: integer`, or
`type: number` in its schema. BAN's `oas3-valid-media-example` rule rejects `null` for typed
properties. Instead:
- Optional string field → use a realistic placeholder value (e.g. `"user@example.com"`, `"Acme Ltd"`)
- Optional object field → omit the field entirely from the example rather than setting it to `null`
- Optional array field → use an empty array `[]` or a minimal 1-item array

Apply this rule to all fields in endpoint request/response examples AND inline YAML `value:` blocks
inside `openapi.yaml` (e.g. 422 inline examples).

## Error Example Files

**Standard error examples** (always present, identical across all APIs) → write to `common-libraries/examples/`:

```
common-libraries/examples/example-error-400-bad-request.json
common-libraries/examples/example-error-401.json
common-libraries/examples/example-error-403.json
common-libraries/examples/example-error-404.json
common-libraries/examples/example-error-429.json
common-libraries/examples/example-error-500.json
common-libraries/examples/example-error-503.json
```

**API-specific error examples** (domain error codes from `domain_rules.extra_responses`, e.g. 422, 502, 504) → do NOT write to `common-libraries/`. Define them as **inline `value:` blocks** directly inside the path operation in `openapi.yaml`. They are unique to this API and do not belong in shared libraries.

```yaml
# In openapi.yaml — correct placement for API-specific errors
paths:
  /{resource}:    # version prefix stripped — /v1 lives in servers.url
    post:
      responses:
        '422':
          description: '{description from domain_rules.extra_responses}'
          content:
            application/json:
              schema:
                $ref: './common-libraries/components/response-types.yaml#/ErrorResponseType'
              examples:
                DomainError:
                  value:
                    errors:
                      - id: '9709-4675-2456-7801'
                        code: '{error_code from domain_rules.extra_responses}'
                        title: '{Human-readable description of the error.}'
```

All error examples must use the `value:` wrapper.
The `title` field must match `^[a-zA-Z0-9\s"=,.']{1,250}$` — use full stops, no em dashes (`—`) or other special characters.

Each error example file must use this shape (with `value:` wrapper):
```json
{
  "value": {
    "errors": [
      {
        "id": "9709-4675-2456-7801",
        "code": "BAD_REQUEST",
        "title": "The request could not be understood by the server due to malformed syntax."
      }
    ]
  }
}
```

| File | `code` | `title` |
|------|--------|---------|
| `example-error-400-bad-request.json` | `"BAD_REQUEST"` | `"The request could not be understood by the server due to malformed syntax."` |
| `example-error-401.json` | `"UNAUTHORIZED"` | `"The user could not be authenticated for this request."` |
| `example-error-403.json` | `"FORBIDDEN"` | `"The user is not permitted to access the requested operation."` |
| `example-error-404.json` | `"NOT_FOUND"` | `"Server has not found a resource with that URI."` |
| `example-error-429.json` | `"TOO_MANY_REQUESTS"` | `"Too many requests. Rate limit exceeded."` |
| `example-error-500.json` | `"INTERNAL_SERVER_ERROR"` | `"Server encountered an error processing request."` |
| `example-error-503.json` | `"SERVICE_UNAVAILABLE"` | `"Service temporarily unavailable, try again later."` |

## Generation Report

Write `generation-report.md` with:
```markdown
# OAS Generation Report

Generated: {ISO timestamp}
Mode: {GREENFIELD|EXTEND}
Output format: {split|single}
OAS version: 3.0.3

## Sources Used
{list of input files/URLs used}

## Field Provenance
{For each schema object generated, list which section/table/paragraph of the source document defined the field. If a field cannot be traced to a specific section of the source, it must NOT be in the schema. Format:}

| Schema | Field | Source section |
|--------|-------|---------------|
| {SchemaName} | {fieldName} | {e.g. "Section 4.2 Field Constraints table" or "Confluence page table row 3"} |

If no fields could be traced to the source → write: "No field definitions found in source. Request schema is empty — populate via api-config.yaml or add field details to the source document."

## Endpoints Generated
{list of method + path + operationId}

## Files Written
{list of file paths relative to output-dir}

## Merge Changes
{EXTEND mode only — omit this entire section (including this header) in GREENFIELD mode or when no existing endpoints were merged.}

| Endpoint | Field | Change |
|----------|-------|--------|
| `POST /v1/accounts/open` | `emailAddress.pattern` | UPDATED — old: `^...` new: `^...` |
| `POST /v1/accounts/open` | `mobileNumber` | ADDED |
| `POST /v1/accounts/open` | `legacyField` | REMOVED — was in existing OAS, not in input |

## Guardrails Triggered
{list or "None"}

## Red Flags
{Things Claude inferred or could not confirm from the source. Each needs human sign-off before portal submission. Format: `file:field — description`. Write "None" only if ALL checks pass.}

Red flags are NOT validation errors — those are caught by Pass 1/2/3. Red flags are ambiguous inferences:

| # | Flag when... | Why human review needed |
|---|-------------|------------------------|
| 1 | `externalDocs.url` is a placeholder or missing | Must be a real Confluence URL before portal submission |
| 2 | Any `info` description field (API Type, Risk Classification, Business Owner, Technical Owner) is placeholder or absent | Required metadata for portal registration |
| 3 | `maxLength` was inferred (has `# not specified — verify` comment) | Source did not specify — value may be wrong for the business domain |
| 4 | `pattern` was inferred (not from design doc) | Regex may be too broad or too narrow — verify against real data in integration testing |
| 5 | Field type was inferred (has `# inferred type` comment) | Source was ambiguous — confirm type is correct |
| 6 | `maximum`/`minimum` was inferred (has `# not specified — verify` comment) | Numeric bounds may not match business rules |
| 7 | Sensitive field name found in `required:` array (`accountNumber`, `sortCode`, `cardNumber`, `pan`, `cvv`, `pin`, `password`, `secret`, `address`) | BAN `data-leakage` rule — designer must decide: make optional OR obtain CSO exception |

## Skipped
{list of skipped endpoints with reason, or "None"}

## REST Standards Check
| Original | Fixed | Rule |
|----------|-------|------|
| POST /v1/accounts/createAccount | POST /v1/accounts | No verbs in path |
{or "All endpoints comply with REST standards."}

## Config Applied
{list of domain_rules from api-config.yaml applied, or "None (no --config provided)"}

## Validation Results

### Pass 1 — Syntax + $ref Resolution
Status: {PASSED|FAILED}
Errors: {count or 0}

### Pass 2 — Anomaly Analysis
Anomalies found: {count}
Auto-fixed: {count}
Remaining: {count}
Report: openapi-anomalies.md

### Pass 3 — BAN (Barclays API Network) Validator
Service: https://barclays-api-network-26915.pr2.apaas4.barclays.intranet
Status: {PASSED|FAILED|FAILED — auth error|SKIPPED — requests not installed}
Iterations: {count}

#### Auto-Fixed (CRITICAL — severity 0)
| Issue code | File | Line | Fix applied |
|------------|------|------|-------------|
{rows or "None"}

#### Fixed by User Choice (HIGH — severity 1)
| Issue code | File | Line | Fix applied |
|------------|------|------|-------------|
{rows or "None"}

#### Skipped by User (HIGH — severity 1, kept as-is)
| Issue code | File | Line | Message |
|------------|------|------|---------|
{rows or "None"}

#### Known Exceptions (CRITICAL/HIGH — CSO-approved, intentionally not fixed)
| Issue code | Severity | File | Reason |
|------------|----------|------|--------|
{rows or "None"}

#### Remaining for Manual Review (MEDIUM/LOW — severity 2–3 only)
| Issue code | Severity | File | Message |
|------------|----------|------|---------|
{rows or "None"}
```

## PII Check Before Writing

Before writing any example file, scan for PII patterns:
- Email addresses matching `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` (not `@example.com`) → replace with `user@example.com`
- UK phone numbers matching `07[0-9]{9}` → replace with `07700000000`
- UK postcodes matching `\b[A-Z]{1,2}[0-9]{1,2} ?[0-9][A-Z]{2}\b` → replace with `EC11BB` (no space, ≤ 7 chars)
- Sort codes matching `\b[0-9]{2}-[0-9]{2}-[0-9]{2}\b` (must have dashes, word boundary) → replace with `12-34-56`
- 8-digit bank account numbers: only replace when the containing field name matches `accountNumber`, `acctNum`, `accountNo`, `bankAccount`, or similar — do NOT replace all 8-digit numbers (would corrupt transaction IDs, dates, reference numbers)
- Dates of birth (context-aware: field named dob/dateOfBirth) → replace with `1990-01-01`

Log each replacement in the generation report under "Guardrails Triggered".
