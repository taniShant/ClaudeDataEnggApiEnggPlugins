# Content Parser — Step 4 Reference

Rules for extracting a structured field inventory from all content source formats.
Referenced by SKILL.md Step 4.

---

## Output Shape

Produce this JSON structure internally (do not show to user):

```json
{
  "fields": [
    {
      "name": "product.applicationType",
      "type": "string",
      "format": null,
      "minLength": null,
      "maxLength": 3,
      "pattern": null,
      "required": true,
      "description": "Determines BIN range and account format",
      "enum": ["010", "020", "080"],
      "example": "010",
      "pii": false,
      "source": "raml types/type-product.raml"
    }
  ],
  "schemas": {
    "ProductInfo": {
      "fields": ["product.applicationType", "product.productNumber"]
    }
  },
  "validation_rules": [
    {
      "field": "product.applicationType",
      "rule": "Must be one of: 010, 020, 080",
      "error_code": "AOS-VAL-001"
    }
  ],
  "business_context": "One paragraph summarising what this API does."
}
```

---

## Per-Format Parsing Rules

### RAML Folder (contains `api.raml`)

- Read `api.raml` → extract title, version, baseUri, resource hierarchy
- Read `types/*.raml` → extract all type definitions with exact constraints
- Read `traits/` → extract headers, parameters
- Read `examples/` → note JSON files for copying

**RAML constraint preservation:**
- `enum` defined → keep enum ONLY, do NOT add pattern
- `pattern` defined → keep pattern ONLY, do NOT add enum
- Both defined → keep both exactly
- Neither → apply CISO rules later (Step 7)
- NEVER derive constraints from RAML `examples`

**Type mapping:**
- `date-only` → `type: string`, `format: date`, use Date pattern from `rules.md`
- `datetime` → `type: string`, `format: date-time`, use DateTime pattern from `rules.md` (includes timezone offset)
- `datetime-only` → `type: string`, `format: date-time`, pattern without timezone: `'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}$'`, `minLength: 19`, `maxLength: 19`
- `time-only` → `type: string`, `format: time`, pattern: `'^[0-9]{2}:[0-9]{2}:[0-9]{2}$'`, `minLength: 8`, `maxLength: 8`
- `integer` → preserve `minimum`/`maximum`
- `number` → preserve bounds
- Nested objects → separate entries with dot notation (`parent.child`)

**No inference markers** — RAML values are explicit. Do not add `# inferred — verify`.

---

### Design Document (.md / .txt / .docx / .wiki)

- Extract field names, types, constraints from tables, lists, and prose
- Look for sections with field descriptions, data dictionaries, validation rules
- Flag inferred values: `"inferred type: string — verify"` in description

**Constraint Translation — Field Layout Tables:**

When a field table has length, format, or allowed-values columns, translate as follows:

| Source expression | OAS constraint |
|---|---|
| `Length: N` or `Bytes: N` (string field) | `maxLength: N` |
| `Length: N` (numeric field) | `type: integer` — no maxLength unless zero-padded |
| `Format: DDMMYYYY` | `type: string`, `pattern: "^[0-9]{8}$"`, `minLength: 8`, `maxLength: 8` |
| `Format: YYYYMMDD` | `type: string`, `pattern: "^[0-9]{8}$"`, `minLength: 8`, `maxLength: 8` |
| `Format: MMYY` | `type: string`, `pattern: "^[0-9]{4}$"`, `minLength: 4`, `maxLength: 4` |
| Allowed values `A / B / C` or `A, B, C` | `enum: [A, B, C]` — omit minLength/maxLength/pattern |
| `Mandatory` or `Required` | `required: true` |
| `Optional` | `required: false` |
| `Conditional` | `required: false`, add `# conditional — verify` |
| Array with `max N entries` or `occurs N times` | `maxItems: N`, `minItems: 0` |
| `Numeric` type, no explicit length | `type: integer` |
| `Alpha` type, length N | `type: string`, `maxLength: N` |
| `Alphanumeric` type, length N | `type: string`, `maxLength: N` |

Only translate constraints **explicitly stated** in the source. If the LLD does not give a length or format for a field, do NOT invent one — leave the constraint absent and let CISO defaults apply at Step 7.

---

### JSON File (.json)

- Treat as request/response example
- Infer types from values: string→string, number→integer, boolean→boolean, object→object, array→array
- Extract field names from keys, nested paths with dot notation
- Flag all as inferred

---

### Excel File (.xlsx / .xls)

- Look for columns: Field, Name, Type, Required, Description, Min, Max, Pattern, Enum, Example
- Column names are case-insensitive; match by best effort
- If columns look like endpoints (Method, Path, Summary) → treat as endpoint list for Step 5

---

### Confluence URL

- Fetch content (see SKILL.md Step 2 for curl command)
- After HTML stripping, parse as design document (same rules as .md)

---

### Free-Form Text

- Parse as unstructured field descriptions
- Everything is inferred — flag accordingly

---

## Common Rules (All Formats)

1. **No invention — the strictest rule:** Do NOT create fields not present in ANY source. This applies to ALL context:
   - Do NOT use fields from other APIs processed earlier in this session
   - Do NOT use fields from training knowledge about similar-sounding APIs
   - Do NOT infer fields from an API's name or domain — the API name never implies what fields exist. Only fields explicitly defined in the source document may appear in the schema.
   - **If the source document contains no field definitions**: generate an EMPTY request schema (`properties: {}`) and flag in Red Flags: `"No field definitions found in source — request schema is empty. Add field details to the source document or use api-config.yaml."` Do NOT fill in fields from memory.
   - A field present in at least one source is not invented — include it with a conflict note if sources disagree on its presence. "Not present in any source" means absent from ALL inputs.
2. **PII detection:** name, address, postcode, DOB, email, phone, sort code, account number, NI number → `pii: true`
3. **PII sanitisation:** email→`user@example.com`, phone→`07700000000`, DOB→`1990-01-01`, postcode→`EC11BB`, sort code→`12-34-56`, account number→`12345678`
4. **Priority order (highest to lowest):** `--config` (via `domain_rules`) > RAML > other content sources > inferred. RAML wins over design docs/JSON/Excel/Confluence for the same field.
5. **Conflict resolution:** If two non-RAML sources disagree:
   - **Type conflict** (`string` vs `integer`) → use `string` (safer), add `# type conflict — verify`
   - **Constraint conflict** (`maxLength: 50` vs `maxLength: 100`) → use more restrictive value, add `# constraint conflict — verify`
   - **Required conflict** → `required: false`, add `# required conflict — verify`
   - **Field existence conflict** (field in one source, absent in another) → include the field, add `# field existence conflict — verify`
