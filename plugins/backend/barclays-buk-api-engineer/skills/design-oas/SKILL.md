---
name: design-oas
description: >
  Generates a Barclays-compliant OpenAPI 3.0.3 spec from any input — design docs,
  RAML, Confluence, JSON, Excel, or free text. Covers the 9-step generation pipeline
  (Analysis → Planning → Generation). Validation is handled separately by verify-oas.
color: blue
---

> **Source:** Barclays OAS Template, CISO Schema Policy, BAN Portal Rules
> **Owner:** BUK API Engineering
> **Review trigger:** On CISO rule changes, BAN validator updates, or OAS template revision
> **Status:** Reviewed

## Source Attribution

**Primary sources:**
- Barclays OAS template (official Barclays OpenAPI 3.0.3 template — `templates/oas/common-libraries/`)
- CISO Schema Policy (`reference/rules.md` — minLength, maxLength, pattern, enum exemption, additionalProperties rules)
- BAN portal validation rules (`reference/ban-validator-guide.md` — CRITICAL/HIGH fix table sourced from BAN validator behaviour)
- Barclays CISO regex policy (https://confluence.barcapint.com/spaces/ASC/pages/596524483/REGEX+Examples+and+Patterns)
- OpenAPI 3.0.3 specification (https://spec.openapis.org/oas/v3.0.3)

**Domain knowledge applied:**
- Barclays API Naming Standard (operationId camelCase, resource plural nouns, no verbs in paths)
- Barclays iAPI project structure patterns (split-file OAS, component naming convention)

**Known limitations:**
- BAN Known Exceptions list (`reference/rules.md`) may be incomplete — new exceptions should be added as discovered
- Regex policy sourced from Confluence; if ASC page is updated, `reference/rules.md` and `analyze_oas_anomalies.py` must be updated in sync
- Example generation for PII fields is sanitised but field type inference remains probabilistic when source is free text

# Skill: Design OAS — OpenAPI 3.0.3 Generation Pipeline

## When to Use This Skill

Use this skill when:
- Generating a new OpenAPI 3.0.3 specification from any input source
- Extending an existing OAS spec with new or modified endpoints
- Need to understand CISO schema rules, regex policy, or Barclays OAS structure

**Related:**
- `barclays-buk-api-engineer:barclays-api-standards` — pre-generation standards check (naming, structure)
- `barclays-buk-standards:api-design` — DAF-specific API design patterns

## Quick Start

Generate an OAS spec from a design document:

1. Invoke `/barclays-buk-api-engineer:design-oas --input <source> --output <dir>`
2. The agent loads reference templates, parses inputs, extracts endpoints
3. Components are built applying CISO rules from `reference/rules.md`
4. Files are written to the output directory
5. `verify-oas` auto-chains to validate portal-readiness

---

## Input Auto-Detection

| Input | Detected as |
|-------|-------------|
| `.md` / `.txt` / `.docx` | Design document |
| Folder with `api.raml` | RAML spec |
| `.json` | JSON examples |
| `.xlsx` / `.xls` | Excel endpoint list |
| URL with `confluence` | Confluence page |
| Quoted string (no extension, no path separator) | Free text |

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `CONFLUENCE_TOKEN` | Required for Confluence input |
| `CONFLUENCE_BASE_URL` | Optional — default: `https://confluence.barcapint.com` |
| `BAN_USERNAME` / `BAN_PASSWORD` | For verify-oas Pass 3 on Mac/Linux (Windows uses Kerberos) |

---

## What This Skill Produces

```
<output-dir>/
├── openapi.yaml                    ← Root spec (OpenAPI 3.0.3)
├── generation-report.md            ← Sources, changes, red flags, validation results
├── components/
│   ├── common/type-common-headers.yaml   ← only if input defines API-specific custom headers
│   └── {resource}/
│       ├── type-{Op}RequestType.yaml
│       ├── type-{Op}RequestData.yaml
│       ├── type-{Op}ResponseType.yaml
│       └── type-{Op}ResponseData.yaml
├── common-libraries/               ← Copied from templates/oas/
│   ├── security/security-schemes.yaml
│   ├── components/{headers,responses,response-types}.yaml
│   └── examples/example-error-{code}.json
└── examples/
    ├── example-{operationId}-request.json
    └── example-{operationId}-response.json
```

---

## Execution Pipeline (9 Steps, 3 Phases)

Execute all 9 steps in order. Announce each phase before its first step.

| Phase | Steps | Announce |
|-------|-------|---------|
| 1/3 — Analysis | 1–3 | `[Phase 1/3 — Analysis]` |
| 2/3 — Planning | 4–6 | `[Phase 2/3 — Planning]` |
| 3/3 — Generation | 7–9 | `[Phase 3/3 — Generation]` |

---

### Step 1 — Load Reference OAS Templates

Resolve template files via Glob:
```
Glob(pattern="**/barclays-buk-api-engineer/templates/oas/**")
```

Read these files (read ONCE — do not re-read in later steps):
- `common-libraries/security/security-schemes.yaml`
- `common-libraries/components/headers.yaml`, `responses.yaml`, `response-types.yaml`

Load the reference openapi.yaml to understand overall spec structure only:
```
Glob(pattern="**/barclays-buk-api-engineer/references/design-oas/reference/examples/openapi.yaml")
```

**Do NOT load the component YAML or example JSON files** from the reference/examples/ directory — they are from a specific older API and do not represent the general pattern. All generation rules are in `reference/rules.md`, `reference/component-builder.md`, `reference/coordinator.md`, and `reference/output-writer.md`. Those are authoritative. The example files are kept for historical reference only.

If not found → warn: "Reference files not found — using built-in CISO rules only."

Tell user: "Reference OAS loaded from templates."

---

### Step 2 — Collect Inputs

**⚠ PHASE GATE:** If `phase=generate` AND `confirmed_fields` is provided → **SKIP this step entirely.** Do NOT read input sources. The field inventory is already confirmed. Jump to Step 3.

Parse all `--input` values. Auto-detect format per table above.

**Targeted reading — design documents and LLDs:**
Before reading the full source, scan its headings or table of contents. Then read in this priority order:

1. **Field definition sections first (authoritative source):** Read sections named "Field Constraints", "Field Definitions", "Data Dictionary", "Request Fields", "Response Fields", "API Contract > Field Constraints", or equivalent. These are the ONLY authoritative source for field names, types, and constraints. Extract ALL fields from these tables exactly as written.
2. **Examples sections second (for example file generation only):** Sections named "Examples", "Request Example", "Response Example". Read these ONLY to generate example JSON files — do NOT use example values to infer field names or constraints. Example JSON is illustrative, not exhaustive.
3. **Skip entirely:** Architecture diagrams, sequence diagrams, protocol details, implementation steps, message build/byte-mapping tables, idempotency logic, deployment notes.

**Critical:** Never infer field names from example JSON. The field constraint table is the truth. If an example shows 5 fields but the constraint table has 91, generate all 91.

If no field definition section is found → STOP. Report: `"No field definition section found in source. Add a field constraints / data dictionary section to the document."` Do NOT read the full document.

**Validation:**
- At least one `--input` required
- `--endpoints` is optional for ALL input types — if omitted, auto-extract from input (Step 5)
- Confluence input requires `CONFLUENCE_TOKEN` — warn and continue with other inputs if missing (AP-7)

**Confluence fetch:**
```bash
PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || echo python)

# Extract page ID
PAGE_ID=$($PYTHON -c "
import re, sys
url = sys.argv[1]
m = re.search(r'/pages/(\d+)', url) or re.search(r'pageId=(\d+)', url)
print(m.group(1) if m else sys.exit(1))
" "$INPUT_URL")

# Fetch page
CONF_BASE="${CONFLUENCE_BASE_URL:-https://confluence.barcapint.com}"
HTTP_CODE=$(curl -sk --max-time 30 -o /tmp/confluence_response.json -w "%{http_code}" \
  -H "Authorization: Bearer $CONFLUENCE_TOKEN" -H "Accept: application/json" \
  "$CONF_BASE/rest/api/content/$PAGE_ID?expand=body.storage")

# Extract text
cat /tmp/confluence_response.json | $PYTHON -c "
import json,sys,re,html
d=json.load(sys.stdin)
t=re.sub(r'<[^>]+>',' ',d.get('body',{}).get('storage',{}).get('value',''))
print(re.sub(r'\s+',' ',html.unescape(t)).strip())
"
```

Tell user: "Inputs collected — {N} sources: {list}."

---

### Step 3 — Parse Additional Context + Load Existing OAS

**Priority order (highest first):**
1. `--config` API metadata (via `domain_rules` and `endpoints` field)
2. RAML-sourced values
3. Other content sources
4. Inferred values (always flagged `# inferred — verify`)

**If extending an existing OAS (update-oas mode):**
Read `reference/extend-mode.md` now — apply safety check, load existing spec, prepare for merge.
Tell user: "Existing spec loaded — new endpoints will be appended, named existing endpoints will be merged (input wins)."

---

### Step 4 — Parse All Content Sources

**⚠ PHASE GATE:** If `phase=generate` AND `confirmed_fields` is provided → **SKIP this step entirely.** Use `confirmed_fields` directly as the field inventory. Jump to Step 5.

Produce unified field inventory (internal — do not show to user):
```json
{ "fields": [...], "schemas": {...}, "validation_rules": [...], "business_context": "..." }
```

For per-format parsing rules, read `reference/content-parser.md`.

Rules for all formats:
1. Do NOT invent fields not in sources
2. PII fields → `pii: true`; sanitise examples (email→`user@example.com`, phone→`07700000000`, postcode→`EC11BB`)
3. `domain_rules` from `--config` overrides any parsed/inferred values for named fields

---

### Step 5 — Extract Endpoints

Priority order (highest first — stop at first match):

1. **`api-config.yaml` `endpoints` field** — use exactly as listed, skip all extraction. This is the recommended approach for deterministic output across runs.
2. **`--endpoints` flag** — use as specified; if RAML also present, use as filter
3. **RAML (no endpoints specified)** — auto-extract from RAML resource hierarchy
4. **Design doc / Confluence / JSON / Excel / text (no endpoints specified)** — scan input for HTTP method + path patterns. If multiple candidates found, present them and ask which to generate. If exactly one found, proceed without asking. If none found, ask user.

**Always apply:** 400/401/403/404/429/500/503 on every endpoint; operationId = `{verb}{PascalCasePath}`; GET/DELETE/HEAD → no request body

**When `--endpoints` flag is provided and REST standards correction results in an ambiguous path (e.g. `/create` → `/` after verb removal):**
Do NOT fall back to input source extraction. Instead STOP and report:
`"Invalid endpoint after REST standards correction: '{original}' → path becomes ambiguous after removing verb '{verb}'. Provide a resource noun path e.g. POST /v1/accounts instead of POST /v1/create."`

**Non-determinism warning:** When endpoints are extracted from free-text sources (option 4), the same document may yield different paths on different runs if the language is ambiguous. Use `api-config.yaml` `endpoints` or `--endpoints` to eliminate this variation.

For extraction rules, read `reference/endpoint-extractor.md`.

---

### Step 5.5 — REST Standards Check

Auto-fix path violations.

| Rule | Auto-fix |
|------|---------|
| Verb in path (`createAccount`, `deletePayment`) | Remove verb, adjust HTTP method |
| Incorrect method (`POST /delete/{id}`) | Correct to `DELETE /{id}` |
| Uppercase path | Lowercase |
| Trailing slash | Remove |
| Singular resource name | Pluralise — except uncountable nouns |
| >3 nesting levels | Warn only |

Recalculate operationId for any fixed path.
Tell user: "REST check — {N} violations, {M} auto-fixed."

---

### Step 5.8 — Source Content Verification (MANDATORY before generating any files)

After completing Steps 4 and 5, BEFORE writing any component files, display this summary to the user:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOURCE CONTENT EXTRACTED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Source:    {input URL or file}
Endpoint:  {METHOD /path}

Fields found in source ({N} total):
  {field1} — {source section, e.g. "Section 4.2 table row 3"}
  {field2} — {source section}
  ... (list ALL fields extracted, with the specific section/table/paragraph they came from)

Fields NOT found — empty schema will be generated:
  {If no fields were found, state this explicitly}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Do you want to proceed with generation using these fields?
❯ 1. Yes — generate schema from these fields
  2. No — stop, I will review the source and re-run
```

**Wait for user confirmation before proceeding to Step 6.**

If zero fields were extracted from the source, do NOT generate a schema from memory or training knowledge. Instead display:
```
No field definitions found in source. Generation stopped.
The source document does not contain field-level constraints or a data dictionary.
Options:
  1. Add field definitions to the source document, or
  2. Provide an api-config.yaml with domain_rules.field_patterns, or
  3. Use a different --input source that contains field definitions.
```
And STOP — do not proceed.

---

### Step 6 — Ambiguity Check

- Missing operationId → derive
- Missing summary → derive from operationId
- No fields found for endpoint → ask user to describe or skip
- RAML-sourced endpoints → no ambiguity check needed (values are explicit)

**Endpoint confirmation (always, unless endpoints came from `api-config.yaml` or `--endpoints` flag):**

When endpoints were extracted from free-text sources (design doc, Confluence, Excel, plain text), always confirm with the user before proceeding — even if only one endpoint was found. This prevents non-deterministic naming between runs.

Ask:
```
Extracted endpoint(s) from input:
  POST /v1/accounts  →  operationId: postAccounts
  (files: type-postAccountsRequestType.yaml, type-postAccountsRequestData.yaml, ...)

Is this correct?

❯ 1. Yes — proceed with these endpoints
  2. Change — type the correct endpoint(s) (e.g. POST /v1/accounts/open)
```

If user types a correction → use their value, re-derive operationId from the corrected path.

Tell user:
- If `--dry-run`: "Dry-run — {N} endpoint(s) would be generated: {list}. No files will be written."
- Otherwise: "Ready to generate {N} endpoint(s): {list}. Output: `{output-dir}`."

---

### Step 7 — Build Components

Read `reference/rules.md` — CISO rules, deterministic output, auto-fix constants. Apply to ALL schemas.
Read `reference/component-builder.md` — schema file templates and merge algorithm.

---

### Step 8 — Assemble openapi.yaml

Assemble root spec from endpoint contracts and component `$ref`s.
Apply pre-write guardrail checks G7–G14.
Read `reference/coordinator.md` for assembly template, header rules, and guardrails.

**`info` block (MANDATORY — write before any path or component):**
Use the metadata table in `reference/coordinator.md` to populate every field. The `info.description` MUST contain the BAN metadata bullet-point block:
```yaml
info:
  description: |
    - **API Type:** <from api-config.yaml api_type, or derive from security scheme: InternalTiaaUsRopcAuth → Internal, other → External>
    - **API Risk Classification:** <from config risk_classification, or default to "MEDIUM">
    - **API Owner (business):** <from config, or "# placeholder — update before publishing">
    - **API Owner (technical):** <from config, or "# placeholder — update before publishing">
    - **API Designer:** <from config, or "# placeholder — update before publishing">
    - **API Overview:** <one-line description of what this API does — derived from input source summary>
```
Never write a plain `description: some text` without the bullet-point block. BAN validates `API Type` — it cannot be a placeholder.

**Header injection rule (apply before writing `parameters:`):**
- `Correlation-ID` and `Authorization` — always add to every operation (mandatory).
- `channelId`, `deviceId`, `businessId`, `sourceSortCode` — add **only** if the input document explicitly mentions them. Check input sources (LLD, design doc, RAML, `api-config.yaml` `operational_headers`) for these names. If not found in any input → do not add.
- Standard header `$ref`s point to `./common-libraries/components/headers.yaml#/{headerName}`.
- `components/common/type-common-headers.yaml` is generated **only** when the input document defines API-specific custom headers that are not in `common-libraries/components/headers.yaml`. If no custom headers exist in the input, do not create this file.

**Inline parameter schema check (G9 extension):** After assembling `openapi.yaml`, scan all `parameters[*].schema` entries under every path operation. Apply the same CISO string/integer/number rules from `rules.md` to these inline schemas.

---

### Step 9 — Write Files

If `--dry-run` → print file tree only, write nothing.
Read `reference/output-writer.md` for directory structure, file sourcing, PII scan, and report template.

**Template copying (GREENFIELD mode) — CRITICAL RULE:**

The files in `common-libraries/` are **official Barclays OAS templates**. BAN validates their exact content — any deviation (different descriptions, missing headers, reordered fields) causes CRITICAL failures.

**Exact procedure — use Bash cp, NOT Read+Write:**

1. Resolve the template directory:
   ```bash
   TEMPLATE_DIR=$(find "$HOME/.claude/plugins/cache" -path "*barclays-buk-api-engineer*" -name "security-schemes.yaml" 2>/dev/null | grep "templates/oas/common-libraries" | sort -V | tail -1 | xargs dirname | xargs dirname | xargs dirname)
   echo "TEMPLATE_DIR: $TEMPLATE_DIR"
   ```
2. Copy the entire common-libraries directory using Bash — this copies bytes exactly without any model involvement:
   ```bash
   cp -r "$TEMPLATE_DIR/common-libraries" "{output_dir}/common-libraries"
   ```
3. Verify the copy succeeded:
   ```bash
   ls "{output_dir}/common-libraries/components/" && echo "COPY_OK"
   ```

**Why Bash cp, not Read+Write:** The model regenerates content token-by-token when using Write, even when Read content is in context. This causes pattern reformatting, extra escape sequences, and missing entries. A shell copy is byte-identical and involves no model content generation.

Files that must NEVER be generated (only Read→Write copied):
- `common-libraries/components/headers.yaml` — contains Correlation-ID, Authorization, channelId, deviceId, businessId, sourceSortCode, Cache-Control. All 7 entries must be present.
- `common-libraries/components/responses.yaml` — standard error $refs are BAN-validated
- `common-libraries/components/response-types.yaml` — ErrorResponseType schema is BAN-validated
- `common-libraries/security/security-schemes.yaml` — InternalTiaaUsRopcAuth scheme is BAN-validated
- `common-libraries/examples/example-error-*.json` — standard error payloads

Always write `generation-report.md` last.

---

## Reference File Map

Read each file ONCE at the step indicated. Never re-read.

| File | Read at | Contains |
|------|---------|---------|
| `reference/rules.md` | Step 7 | CISO rules, regex policy, auto-fix constants, known BAN exceptions |
| `reference/component-builder.md` | Step 7 | Schema templates, merge algorithm |
| `reference/coordinator.md` | Step 8 | openapi.yaml template, guardrails G7–G14 |
| `reference/output-writer.md` | Step 9 | File sourcing, directory structure, PII scan, report template |
| `reference/extend-mode.md` | Step 3 | Extend/merge logic (used by update-oas) |
| `reference/ban-validator-guide.md` | verify-oas | BAN auth, CRITICAL/HIGH/MEDIUM fix flows |
| `reference/content-parser.md` | Step 4 | Per-format field extraction rules |
| `reference/endpoint-extractor.md` | Step 5 | Endpoint contract extraction rules |

**Path resolution:** All references use Glob-based discovery:
```
Glob(pattern="**/barclays-buk-api-engineer/references/design-oas/reference/{filename}")
```

---

## `api-config.yaml` Schema

All fields optional — used with `--config` flag. Combines API metadata and domain-specific generation rules in one file. This is the single source of project-level configuration for anything that applies across all runs.

```yaml
# ── API Metadata ──────────────────────────────────────────────
title: '<API title>'
version: '<v1.0>'
api_type: '<Internal | External>'
risk_classification: '<LIMITED | RESTRICTED | HIGH | CRITICAL>'
business_owner: '<business-owner@barclays.com>'
technical_owner: '<tech-owner@barclays.com>'
designer: '<Designer Name>'
overview: '<Brief description of the API purpose>'
contact_name: '<Team Name>'
contact_email: '<team@barclays.com>'
confluence_url: '<https://confluence.barcapint.com/...>'

# ── Endpoints (optional but recommended for deterministic output) ──────────
# Explicitly list endpoints to generate. When present, the agent skips
# endpoint extraction from input sources entirely — no LLM interpretation,
# no variation between runs. Omit to auto-extract from input.
endpoints:
  - "POST /v1/accounts"
  # - "GET /v1/accounts/{accountId}"
  # - "DELETE /v1/accounts/{accountId}"

# ── Domain Rules ──────────────────────────────────────────────
# Applied by design-oas-agent during Step 7 (component generation).
# Rules here override CISO defaults for named fields only.
# Omit this section entirely if no domain-specific rules apply.
domain_rules:

  # Override the default pattern/min/max for specific field names.
  # Keyed by field name (exact match). Applied wherever that field name appears.
  field_patterns:
    postcode:
      pattern: '^[a-zA-Z0-9]{5,8}$'   # no spaces — downstream strips before storing
      minLength: 5
      maxLength: 8
    expiryDate:
      pattern: '^[0-9]{4}$'            # MMYY — always exactly 4 digits
      minLength: 4
      maxLength: 4

  # Fields the designer has explicitly decided to exclude from required[].
  # Use when BAN flags a data-leakage HIGH warning and the designer decides
  # to make the field optional rather than obtain a CSO exception.
  # Agent omits these from required[] and adds a comment explaining why.
  required_exclusions:
    - mobileNumber
    - cardNumber
    - address
    - emailAddress

  # Operational request headers beyond the mandatory Correlation-ID and Authorization.
  # These are added ONLY to endpoints where the input document mentions them.
  # Use this list to explicitly declare which optional headers this API uses,
  # overriding the default "input-mention required" detection.
  operational_headers:
    - channelId
    - deviceId
    - businessId
    - sourceSortCode

  # Domain-specific non-standard HTTP response codes and their named error codes.
  # These are added to every endpoint's responses block alongside the 7 standard errors.
  # Value is used as the example error code in the response body.
  extra_responses:
    422:
      description: 'Unprocessable Entity'
      error_code: 'DOMAIN_REJECTED'      # replace with actual downstream error code
    502:
      description: 'Bad Gateway'
      error_code: 'UPSTREAM_UNAVAILABLE'
    504:
      description: 'Gateway Timeout'
      error_code: 'UPSTREAM_TIMEOUT'
```

### How domain_rules are applied

| Rule | Applied at | Behaviour |
|------|-----------|-----------|
| `field_patterns` | Step 7 — component generation | Overrides CISO default pattern/min/max for that field name wherever it appears |
| `required_exclusions` | Step 7 — required[] assembly | Field is never added to required[], comment added explaining why |
| `operational_headers` | Step 8 — openapi.yaml assembly | Explicit list of optional headers to add. When present, overrides input-mention detection. All $refs point to `./common-libraries/components/headers.yaml` |
| `extra_responses` | Step 8 — openapi.yaml assembly | Additional response codes added to every endpoint alongside standard 7 |

### Priority order (highest first)

1. `domain_rules.field_patterns` from api-config.yaml
2. Values extracted from input sources
3. CISO auto-fix defaults (from rules.md)

---

## Validation (handled by verify-oas)

After generation completes, the `design-oas` command auto-chains to `verify-oas` which runs:
- **Pass 1:** Syntax validation (`openapi-spec-validator`)
- **Pass 2:** CISO anomaly analysis (`analyze_oas_anomalies.py`)
- **Pass 3:** BAN portal submission (`ban_validator.py`)

Scripts are resolved via:
```
Glob(pattern="**/barclays-buk-api-engineer/scripts/analyze_oas_anomalies.py")
Glob(pattern="**/barclays-buk-api-engineer/scripts/ban_validator.py")
```

Use `--skip-verify` to bypass, or invoke `verify-oas` independently later.

---

## Agent Self-Check

Before marking generation complete, verify:

- [ ] Every non-enum string property has `minLength`, `maxLength`, AND `pattern`
- [ ] Every enum field has ONLY `enum` — no minLength, maxLength, or pattern alongside it
- [ ] Every integer/number has `minimum` and `maximum`
- [ ] Every object schema has `additionalProperties: false`, `deprecated: false`, `nullable: false`
- [ ] Every array has `minItems` and `maxItems`
- [ ] All endpoints include 7 standard error responses (400, 401, 403, 404, 429, 500, 503)
- [ ] No `format: email` appears anywhere — CSO-approved regex pattern used instead
- [ ] All examples contain sanitised PII only (no real emails, phones, postcodes)
- [ ] operationId is camelCase and matches the `{verb}{PascalCasePath}` pattern
- [ ] No verbs appear in URL paths (use HTTP method instead)
- [ ] Correlation-ID header is present on every endpoint
- [ ] No verb segment in any paths: key (G13) — path key ends with a noun, not an action word
- [ ] No enum field has minLength, maxLength, or pattern alongside it (G14) — enum is the sole constraint
- [ ] `generation-report.md` documents all sources, inferred values, and Red Flags
