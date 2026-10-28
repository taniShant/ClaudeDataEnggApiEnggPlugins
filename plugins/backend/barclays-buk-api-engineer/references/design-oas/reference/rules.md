# Generation Rules — CISO, Deterministic Output, Token Optimization

Read this file ONCE before Step 7 (Build Components). These rules govern all schema
generation, file output, and optimization behaviour.

---

## Barclays CISO Schema Rules (Mandatory)

Apply to **every schema object and property**. Missing any causes portal failures.

### Object Types

```yaml
type: object
deprecated: false
nullable: false
additionalProperties: false
```

### String Properties

Two cases — BAN treats them differently:

**With `enum`** — enum is the sole constraint. Do NOT add `minLength`, `maxLength`, or `pattern`:
```yaml
type: string
enum:
  - 'Y'
  - 'N'
```

**`deprecated` and `nullable` apply to object schemas and boolean fields only** — do NOT add them to string, integer, number, or array leaf properties. Only object wrappers (type: object) need `deprecated: false`, `nullable: false`, `additionalProperties: false`.

**Without `enum`** — must have `minLength` + `maxLength` + `pattern`:
- Specified in source → use exactly
- Not specified → `minLength: 1`, `maxLength: 250`, `pattern: '^[a-zA-Z0-9 .,_-]{1,250}$'`, add `# not specified — verify`
- Date: `minLength: 10`, `maxLength: 10`, `format: date`, `pattern: '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'`
- DateTime (with timezone): `minLength: 20`, `maxLength: 30`, `format: date-time`, `pattern: '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[a-zA-Z0-9.+-]{0,10}$'`
- DateTime (no timezone / RAML datetime-only): `minLength: 19`, `maxLength: 19`, `format: date-time`, `pattern: '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}$'`
- Time only (RAML time-only): `minLength: 8`, `maxLength: 8`, `format: time`, `pattern: '^[0-9]{2}:[0-9]{2}:[0-9]{2}$'`
- UUID: `minLength: 36`, `maxLength: 36`, `format: uuid`, `pattern: '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'`
- Email: use the CSO-approved pattern (RFC 5321/5322 exemption applies — `%`, `?`, `~`, `+` are permitted in local-part). **This exact string is also hardcoded in `analyze_oas_anomalies.py` `_CSO_APPROVED_PATTERNS` — update both if CSO revises the pattern:**
  ```
  ^(?=.{1,256}$)^([a-zA-Z0-9.!#$%&'*+\/=?^_`~-]{1,64})@(([a-zA-Z0-9-]{1,180}(\.[a-zA-Z0-9-]{1,62}){1,9}))$
  ```
- HTTPS URL: use the CSO-approved pattern:
  ```
  ^(https:\/\/)(([0-9a-zA-Z-]{2,24}\.[a-zA-Z\/]{2,12})|([0-9a-zA-Z-]{2,24}\.[0-9a-zA-Z-]{1,3}\.[a-zA-Z\/]{2,12})|([0-9a-zA-Z]{1,4}\.[0-9a-zA-Z-]{2,24}\.[0-9a-zA-Z-]{1,3}\.[a-zA-Z\/]{2,12})|([0-9a-zA-Z]{2,4}\.[0-9a-zA-Z-]{1,24}\.[a-zA-Z\/]{2,12}))$
  ```

### Boolean Properties

Must have `deprecated: false` and `nullable: false`. No other constraints required.
```yaml
type: boolean
deprecated: false
nullable: false
description: '<description>'
example: true
```

### Array Properties

Must have `minItems` + `maxItems`. The `items` schema must follow the same CISO rules as any other schema.
```yaml
type: array
minItems: 0
maxItems: 100  # from design doc; 100 + comment if not specified
items:
  # If array of objects:
  $ref: './type-{Op}ItemData.yaml#{ObjectName}'
  # If array of strings (inline):
  type: string
  minLength: 1
  maxLength: 100
  pattern: '^[a-zA-Z0-9 .,_-]{1,100}$'
description: '<description>'
```

### Integer/Number Properties

Must have `minimum` + `maximum`:
- Specified → use exactly
- Not specified → `minimum: 0`, `maximum: 999999`, add `# not specified — verify`

### Sensitive Fields in `required:` arrays

`accountNumber`, `sortCode`, `cardNumber`, `pan`, `cvv`, `pin`, `password`, `secret`, `address`

Generate the spec faithfully from the source — if the LLD marks these as mandatory, include them in `required[]`. Do NOT remove them automatically.

Log a **warning** in `generation-report.md`:
> ⚠️ Warning: `{fieldName}` is in `required[]` — BAN may flag this as a HIGH data-leakage violation. To suppress: add to `domain_rules.required_exclusions` in `api-config.yaml` (if the designer has decided to make it optional), or obtain a CSO data-leakage exception to keep it required.

The designer resolves this at verify-oas time when BAN presents it as a HIGH issue.

### Regex Rules

Regex policy: **https://confluence.barcapint.com/spaces/ASC/pages/596524483/REGEX+Examples+and+Patterns**

| Rule | Detail |
|------|--------|
| Must start with `^`, end with `$` | All patterns |
| Never use `.*` or `.+` | Dangerous wildcards — match anything |
| Never use bare `.` outside `[]` | Matches any char — escape as `\.` or put inside `[]` |
| Never use `+` or `*` outside `[]` | Greedy — use `{n,m}` instead |
| Never use `{n,}` with no upper bound | Always specify a maximum |
| Never use `[\S]`, `[\W]`, `[\D]` | Match too broadly — use lowercase `\s`, `\w`, `\d` in negative context |
| Forbidden literals inside `[]`: `< > \| % : ; ? ~` | Unsafe characters — require CSO exemption |
| Forbidden ranges: `[A-z]`, `[Z-a]`, `[A-a]` | Pass unsafe chars in ASCII 90–97 |
| Never use symbol ranges: `[ -/]` | Allows unsafe symbol characters |
| Hyphen in `[]` must be at END or START only | `[a-z.',-]` ✅ (hyphen last) or `[-a-z.',]` ✅ (hyphen first). Never `[a-z\-']` or `[a-z-']` mid-class — scanners interpret `\-'` as a range from `\` to `'` (includes unsafe chars). Rule: **write hyphen as the last character before `]`** |
| Avoid positive lookahead `(?=...)` | Use `{n,m}` instead |
| Avoid ReDoS patterns: `(X+)+`, `([...]+)*` | Catastrophic backtracking risk |
| Use `{n,m}` for all length constraints | e.g. `{1,10}` not `+` or `*` |
| Email/URL: use CSO-approved patterns | See String Properties section above — RFC exemptions apply |

### Known BAN Exceptions (do NOT auto-fix these)

These BAN findings are expected and must be documented in the generation report as known CSO exceptions — **never auto-fix them**:

| BAN Issue | Field / Pattern | Reason | Action |
|-----------|----------------|--------|--------|
| E-02-02 — forbidden chars `% ? ~ +` in character class | **Email fields only** — field name contains `email` or `emailAddress` AND the character class in the pattern includes `%`, `?`, `~`, or `+` | RFC 5321/5322 CSO exemption — these chars are valid in email local-part. Confluence page ASC/596524483 explicitly grants this exemption. | Record in report: "Known exception — RFC 5321/5322 email pattern, CSO exemption applies." |
| E-02-02 — any other field | Any non-email field | NOT a known exception — apply the normal Step 11 fix (add missing constraint). Do NOT skip because the error code is E-02-02. | Auto-fix normally. |

**How to suppress auto-fix for a known exception:**
When BAN flags one of the above, skip the auto-fix and instead add an entry to the generation report under `#### Remaining for Manual Review` with label `KNOWN-EXCEPTION` and the reason above. Do not iterate on it.

---

### Canonical Patterns for Common Field Types

**Priority rule:** If the input document (LLD, RAML, Excel, design doc) explicitly defines a pattern for a field, use that pattern verbatim — do NOT replace it with a canonical one. The canonical patterns below are applied **only when the source provides no pattern for the field**.

The one exception: if the source-defined pattern has a hyphen placement issue (`\-` inside a character class), correct the placement to end-of-class while preserving all character content. This is a regex safety fix, not a business logic change.

Use these patterns when the input document describes a field type but gives no pattern:

| Field type | Pattern | Notes |
|-----------|---------|-------|
| Name (first/last/middle) — letters, spaces, hyphens, apostrophes | `'^[a-zA-Z .''-]{1,N}$'` | Hyphen at end of class. N from source. |
| Address line (houseName, street, locality, townOrCity) | `'^[a-zA-Z0-9 .',-]{1,N}$'` | Allows alphanumeric + space + period + apostrophe + comma + hyphen (all at end). |
| Postcode (no spaces, UK format) | `'^[a-zA-Z0-9]{2,8}$'` | AOS strips spaces before write. No hyphen needed. |
| Sort code (digits only, no dashes) | `'^[0-9]{6}$'` | Exactly 6 digits. |
| Sort code (with dashes `NN-NN-NN`) | `'^[0-9]{2}-[0-9]{2}-[0-9]{2}$'` | Hyphen is a literal at a fixed position — not in a character class. |
| Phone number (digits only) | `'^[0-9]{6,15}$'` | No spaces or separators. |
| Country code (ISO 3-letter) | `'^[A-Z]{3}$'` | Uppercase only. |
| Currency amount (sign + digits + decimal) | `'^[+-][0-9]{1,N}\.[0-9]{2}$'` | Sign, integer part, mandatory 2 decimal places. |
| Generic alphanumeric free-text | `'^[a-zA-Z0-9 .,_-]{1,N}$'` | Hyphen at END of class. N from source. |

**Hyphen placement rule (applies to ALL patterns above):**
When including a hyphen as a literal character in a character class `[...]`, always place it as the **last character** before the closing `]`. Never write `[abc-xyz]` (range), `[\-xyz]` (escaped mid-class — scanner ambiguous), or `[abc-]` at any position other than end.

✅ Correct: `[a-zA-Z0-9 .',-]` — hyphen is last, unambiguous literal
❌ Wrong: `[a-zA-Z0-9 .\-']` — `\-'` is ambiguous range
❌ Wrong: `[a-zA-Z0-9 .-']` — `.-'` is a range from `.` to `'` (ASCII 46–39, invalid)

---

### Location Header Pattern (canonical — use this in all files)

```yaml
pattern: '^/v[0-9]{1,2}/[a-zA-Z0-9/_-]{1,240}$'
```
Supports `/v1/`, `/v2/` etc. Does NOT support `/v1.1/` (minor versions must use path prefix or header versioning, not dot notation).

---

### Other Forbidden Patterns

- No `format: email` — use `type: string` with the CSO-approved email pattern
- No placeholder URLs in `externalDocs.url` — use a real Confluence URL or omit `externalDocs` entirely
- No empty string examples — use a realistic non-empty value (e.g. `'Jr'` not `''`)
- Postcode examples ≤ 7 chars, no space — use `EC11BB`
- Error `title` field — must match `^[a-zA-Z0-9\s"=,.']{1,250}$`

---

---

## Field-Level Parsing Rules (apply at Step 4 — affects both schema and example)

These rules apply to ANY design document regardless of domain. They govern both the schema
constraints built in Step 7 and the example values written in Step 9.

### Rule F1 — Nested required arrays are never skipped

**Signal:** A nested or conditional object whose fields are described as "Mandatory", "Required",
or "Cond. Mandatory" in the source document.

**Schema:** Always build a `required:` array for the nested object using those fields — even if the
parent object itself is optional or conditional. Never leave `required:` empty just because the
parent is conditional.

**Example:** Include all required sub-fields in the example with realistic values.

---

### Rule F2 — "Same constraints as [object]" inherits everything

**Signal:** Phrases like "same as current address fields", "same structure as X", "same transforms
as rows N-M", or "same constraints apply".

**Schema:** Copy the referenced object's `required:` array AND all field constraints
(minLength, maxLength, pattern, enum) verbatim. Do not leave the inheriting object empty or with
weaker constraints.

**Example:** Use the same example values as the referenced object (adjusted for context, e.g.
different street name but same format).

---

### Rule F3 — "Exactly N characters" sets minLength == maxLength

**Signal:** Phrases like "exactly N chars", "exactly N digits", "fixed N-byte field", "N chars
exactly", or when `minLength == maxLength` is implied (e.g. a date field "YYYY-MM-DD" is always
10 chars, a postcode stripped of spaces is always 6-8 chars).

**Schema:** Set both `minLength` and `maxLength` to N. Do NOT use a range like `minLength: 1,
maxLength: N` when the source clearly states the value is always exactly N characters.

**Example:** The example value must be exactly N characters long. If it is not, fix it.

---

### Rule F4 — Single allowed value uses literal pattern, not character class

**Signal:** A non-enum string field where the source document states only one value is valid
(e.g. "value must be X", "always Y", "write 'Z' if condition; space otherwise — but Z is the
only non-space value accepted").

**Schema:** Use `pattern: '^X$'` (literal string anchor). Do NOT use `'^[X]$'` (single-character
character class) — a character class `[X]` is functionally equivalent but semantically misleading
and confuses tooling. Reserve `enum` for fields where multiple distinct values are valid.

**Example:** The example value must be exactly that literal (e.g. `"B"`, `"V"`, `"N"`).

---

### Rule F5 — Optional fields in examples use placeholder values, never null

**Signal:** Any optional or conditional field in the source document.

**Schema:** No change — optional fields are absent from `required:`.

**Example:** Never write `null` for a field that has `type: string`, `type: integer`, or
`type: number`. Instead:
- If the source provides a concrete value or fixed allowed set → use it (e.g. `"B"`, `"V"`, `"GBR"`)
- If the source provides a format/pattern → construct a realistic placeholder (`"user@example.com"`,
  `"07700000000"`, `"EC11BB"`)
- If the field is an optional object or array → omit it entirely from the example rather than
  writing `null` or `[]`

This applies to ALL example files (endpoint request/response JSON) AND inline `value:` blocks
inside `openapi.yaml`.

---

## Deterministic Output Rules

The skill must produce identical output for identical input. No randomness, no LLM-style variation.

### YAML Field Ordering (always this exact order within a schema property)

```
type → format → deprecated → nullable → additionalProperties →
properties → required → items →
minLength → maxLength → minimum → maximum → minItems → maxItems →
pattern → enum → description → example
```
Note: `required` appears after `properties` (matching reference OAS convention and avoiding unnecessary diffs in EXTEND mode).

### File Naming (rule-based, never LLM-chosen)

File names use **PascalCase** operationId (first letter uppercased). Schema names inside the file also use **PascalCase**.

| Component | File name pattern | Schema name inside file |
|-----------|------------------|------------------------|
| Request type | `type-{PascalCaseOperationId}RequestType.yaml` | `{PascalCaseOperationId}RequestType` |
| Request data | `type-{PascalCaseOperationId}RequestData.yaml` | `{PascalCaseOperationId}RequestData` |
| Response type | `type-{PascalCaseOperationId}ResponseType.yaml` | `{PascalCaseOperationId}ResponseType` |
| Response data | `type-{PascalCaseOperationId}ResponseData.yaml` | `{PascalCaseOperationId}ResponseData` |
| Request example | `example-{camelCaseOperationId}-request.json` | — |
| Response example | `example-{camelCaseOperationId}-response.json` | — |

Note: component YAML files use PascalCase prefix; example JSON files keep camelCase operationId.

**Concrete example** — operationId `openAccount`:

| File | Schema name |
|------|------------|
| `type-OpenAccountRequestType.yaml` | `OpenAccountRequestType` |
| `type-OpenAccountRequestData.yaml` | `OpenAccountRequestData` |
| `type-OpenAccountResponseType.yaml` | `OpenAccountResponseType` |
| `type-OpenAccountResponseData.yaml` | `OpenAccountResponseData` |
| `example-openAccount-request.json` | — |
| `example-openAccount-response.json` | — |

Never omit the `type-` prefix on component files.

### Type Schema Naming (rule-based, never LLM-chosen)

Schema names inside YAML files must follow this exact PascalCase formula:

| File | Schema name inside file |
|------|------------------------|
| `type-{OperationId}RequestType.yaml` | `{OperationId}RequestType` |
| `type-{OperationId}RequestData.yaml` | `{OperationId}RequestData` |
| `type-{OperationId}ResponseType.yaml` | `{OperationId}ResponseType` |
| `type-{OperationId}ResponseData.yaml` | `{OperationId}ResponseData` |

Where `{OperationId}` is the PascalCase form of the operationId (first letter uppercased).
Example: operationId `openAccount` → schema name `OpenAccountRequestType`.

Never vary the suffix. Never use `Wrapper`, `Envelope`, `Payload`, `Body`, or any other synonym.

### Property Ordering within a Schema (always source-document order)

Properties must be written in the order they appear in the source document — not alphabetical, not LLM-reordered. This ensures diffs between runs are minimal and reviewable.

- If source order is ambiguous (e.g. multiple sources): use the order from the highest-priority source (Step 3 priority order)
- `required:` array: always alphabetical

### operationId (deterministic derivation)

`{verb}{PascalCasePath}` — path params become `By{ParamName}`. Never deviate. Never synonym-ize.

**Path key used for derivation is the resource path AFTER stripping the version prefix (which lives in servers.url).**

- `POST /v1/accounts` → servers.url=`/v1`, path key=`/accounts` → `postAccounts` (plural — use the exact resource noun from the path key)
- `POST /v1/accounts/open` → path key=`/accounts/open` → `openAccount` (compound path — verb is derived from the last segment)
- `GET /v1/accounts/{accountId}` → `getAccountsByAccountId`
- `DELETE /v1/cards/{cardId}/blocks/{blockId}` → `deleteCardsBlocksByCardIdAndBlockId`

**Singular vs plural:** The operationId inherits the exact form of the path segment — if the path uses `accounts` (plural), the operationId uses `Accounts` (plural). Never normalise plural to singular or vice versa.

### Description Content — Never Expose Downstream Internals

Descriptions in the generated OAS are **consumer-facing**. They must never expose internal implementation details that a consuming team should not know.

**NEVER include in any description, summary, or example value:**

| Forbidden content | Examples |
|------------------|---------|
| Internal system names | any downstream system name, legacy platform name, mainframe module code |
| Internal field/column names | any internal field code, column name, or variable name used in downstream systems |
| Byte offsets or fixed-width positions | "bytes N-M", "offset N", "position N-M" |
| Internal technical mappings | "maps to field X", "written to field X if Y" |
| Database column names | "stored in column X", "joins on field Y" |
| Internal queue / topic names | any MQ, Kafka, or messaging topic name |
| Transformation logic | padding logic, formatting functions, internal derivation rules |

**Write descriptions from the consumer's perspective only:**

| Type | ❌ WRONG (internal) | ✅ CORRECT (consumer-facing) |
|------|--------------------|-----------------------------|
| Identifier field | "Maps to internal field X as prefix+lpad(N,'0')" | "Unique application identifier used as the idempotency key." |
| Text field | "Written to internal field bytes N-M. Space-padded if absent." | "Broker intermediary name and address." |
| Date field | "Used to derive internal flag if date is within N days" | "Date the applicant signed the Terms and Conditions." |

**Rule:** If a description answers "how does it work internally?", remove it. If it answers "what is it and why does the consumer provide it?", keep it.

---

### Description Derivation (mechanical — no LLM prose)

Descriptions must be derived mechanically to ensure identical output across runs. Never generate free-form prose.

**Schema-level description** (on the type object itself):

| Schema suffix | Template |
|--------------|---------|
| `RequestType` | `Request envelope for {operationId}.` |
| `RequestData` | `Request data for {operationId}.` |
| `ResponseType` | `Response envelope for {operationId}.` |
| `ResponseData` | `Response data for {operationId}.` |

Example: `OpenAccountRequestData` → `description: Request data for openAccount.`

**Property-level description** — two rules in priority order:

1. **If the source document has an explicit description for this field** → use it verbatim (trim whitespace, keep as single line)
2. **If no description in source** → derive from field name:
   - Split camelCase on capital letters: `grossAnnualIncome` → `gross Annual Income`
   - Lowercase all: `gross annual income`
   - Capitalise first letter + add period: `Gross annual income.`

Examples:
| Field name | Derived description |
|-----------|-------------------|
| `firstName` | `First name.` |
| `dateOfBirth` | `Date of birth.` |
| `grossAnnualIncome` | `Gross annual income.` |
| `nationalityCode` | `Nationality code.` |
| `barclaysStaffIndicator` | `Barclays staff indicator.` |
| `btAffordabilityCreditLimit` | `Bt affordability credit limit.` |

This rule applies to ALL property descriptions in component YAML files. Never write multi-sentence descriptions, never add business context, never vary the format.

### Auto-Fix Constants (never vary)

Two contexts apply — values differ by context:

**Step 7 (Schema generation — field not specified in source):**

Values are intentionally conservative — they represent a *valid input default* that should
be verified against real business rules. Always add the `# not specified — verify` comment.

| Missing | Value | Comment added |
|---------|-------|---------------|
| `minLength` | `1` | `# not specified — verify` |
| `maxLength` | `250` | `# not specified — verify` |
| `minimum` | `0` | `# not specified — verify` |
| `maximum` | `999999` | `# not specified — verify` |

**Step 11 (Anomaly fix — validator reports constraint missing after generation):**

Values are intentionally permissive — they are a *fallback patch* for constraints missed
at Step 7. They satisfy BAN without breaking valid data. No comment added (silent fix).
Step 11 should rarely trigger — if it does, it means Step 7 missed a field.

**Enum exemption** (see rules.md String Properties): fields with `enum` need NO other
constraints. Skip ALL Step 11 fixes for enum fields.

**Pattern-derived maxLength (apply BEFORE fallback):** If `maxLength` is missing but the field already has a `pattern` with an exact-length quantifier (e.g. `^[0-9]{6}$`, `^[0-9]{8}$`), or a `minLength` that already constrains the field to exactly N chars, derive `maxLength: N` from that constraint instead of using the fallback `10000`. Examples:
- `pattern: "^[0-9]{6}$"` → `maxLength: 6`
- `pattern: "^[0-9]{8}$"` → `maxLength: 8`
- `minLength: 4` on a fixed-format field → `maxLength: 4`

| Missing | Applies to | Value |
|---------|-----------|-------|
| `minLength` | non-enum strings only | `0` |
| `maxLength` | non-enum strings only | `10000` (unless pattern-derived — see above) |
| `pattern` | non-enum strings only | `"^[a-zA-Z0-9 .,_-]{0,10000}$"` |
| `minimum` | integers/numbers | `0` |
| `maximum` | integers/numbers | `2147483647` |
| `minItems` | arrays | `0` |
| `maxItems` | arrays | `100` |

### Reproducibility Verification

Include SHA-256 hash of `openapi.yaml` in `generation-report.md` (GREENFIELD mode only — hash is non-deterministic in EXTEND mode due to pre-existing file state):

```bash
PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || echo python)
$PYTHON -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "<output-dir>/openapi.yaml"
```

```markdown
## Reproducibility
SHA-256 (openapi.yaml): {hash}
Note: hash is only stable for GREENFIELD runs with identical input and --config file.
```

---

## Token Optimization Rules

1. **Read reference files ONCE in Step 1.** Do not re-read in later steps.
2. **Read each prompt file ONCE** when first needed. Never re-read the same file.
3. **For `--dry-run`:** skip reading reference OAS files (Step 1) only. Still execute Steps 2–6 to parse inputs and derive the file tree. Print the file tree and stop — do not write files or run validation.
4. **For single-endpoint generation:** skip reading error example JSON files from disk (they are not needed for content). Still write them to output using the hardcoded values in `output_writer.md` error table.
5. **Do NOT echo large YAML/JSON blocks to the user.** Summarise: "Generated type-OpenAccountRequestType.yaml (12 fields)."
6. **Batch file writes.** Assemble all content in memory, write once per file.
7. **Skip Steps 11–12 if Step 10 fails.** No point validating a broken spec.
