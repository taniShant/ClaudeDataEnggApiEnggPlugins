# Validator: crypto-indicator-detector

**Purpose**: Scan transformation logic column for explicit crypto signals; extract Protegrity data element names; set crypto flags per column with extraction metadata.

**Severity**: Non-blocking (extraction failures handled at crypto assembly via refusal, not at parse).

**Platform**: Glue + Databricks

---

## Scope

Scans **transformation logic / business logic column ONLY** — no other sources (domain knowledge PII notes, column names).

## Detection Algorithm (3-Step Approach)

Applied to each row's `Business Logic/Transformation Logic` cell.

### Step 1 — UDF Pattern (Primary)

**Regex**: `cloud_api_udf_([A-Z0-9_]+)_(un)?protect\(`

- Match found → `is_crypto = true`, `extraction_source = "udf_pattern"`
- Capture group 1 → `de_name` (Protegrity Data Element name)
- If `_unprotect` → `operation = "detokenize"`
- If `_protect` (without `un`) → `operation = "tokenize"`
- Validate `de_name` against pattern: `(UK|US|APAC)_TOK_<func>_L<d+>R<d+>_<type>_DE`
  - Valid types: UNC, ALN, DEC, NUM, CC, EML, DT
  - If validation fails → `extraction_failed = true`

**Example**: 
```
cloud_api_udf_UK_TOK_ACCT_L0R0_NUM_DE_unprotect(account_number)
→ de_name = "UK_TOK_ACCT_L0R0_NUM_DE", operation = "detokenize"
```

### Step 2 — Protegrity Data Element Reference (Secondary — only if Step 1 not matched)

**Conditions** (all must be present, case-insensitive):
- Text contains "protegrity" AND
- Text contains "data element" AND
- Text contains "tokenize" or "detokenize"

**Regex for DE name**: `(UK|US|APAC)_TOK_([A-Z0-9]+)_(L\d+R\d+)_(UNC|ALN|DEC|NUM|CC|EML|DT)_DE`

- Match found → `is_crypto = true`, `extraction_source = "protegrity_element"`
- Extracted text → `de_name`
- If "detokenize" (case-insensitive) → `operation = "detokenize"`
- If "tokenize" (case-insensitive) → `operation = "tokenize"`
- If both → HALT: ask user which operation is intended for this column. Set `extraction_ambiguous = true`.
- Validate `de_name` as above; if invalid → `extraction_failed = true`

**Example**:
```
"Detokenize source column using Protegrity data element UK_TOK_ACCT_L0R0_NUM_DE"
→ de_name = "UK_TOK_ACCT_L0R0_NUM_DE", operation = "detokenize"
```

### Step 3 — Keyword Scan (Tertiary — only if Steps 1 & 2 not matched)

**Keywords** (case-insensitive): `tokenize`, `detokenize`, `unprotect`, `protect`

- Match found → `is_crypto = true`, `extraction_source = "keyword"`
- `de_name = null` (no pattern match)
- `extraction_failed = true` (keyword only — refusal will trigger at crypto assembly)
- If text contains "detokenize" → `operation = "detokenize"`
- If text contains "tokenize" or "protect" → `operation = "tokenize"`
- If both present → `operation = "tokenize"`, `extraction_ambiguous = true`

**Example**:
```
"Apply tokenization to the output"
→ is_crypto = true, de_name = null, extraction_failed = true
```

## NOT Crypto Triggers (Ignored)

- External sensitivity tags on source columns — source column flagged as sensitive externally but mapped as-is does NOT trigger crypto
- PII column notes in domain knowledge MD — supplementary documentation; does NOT trigger crypto
- Column name patterns or data types alone (e.g., column named `sort_code`, datatype `varchar`)

## Per-Column Crypto Flags Output

```json
{
  "column_name": {
    "is_crypto": true,
    "operation": "detokenize|tokenize",
    "de_name": "UK_TOK_ACCT_L0R0_NUM_DE",
    "extraction_source": "udf_pattern|protegrity_element|keyword",
    "extraction_failed": false,
    "extraction_ambiguous": false
  }
}
```

## Validation Rules

1. **DE name format**: `(UK|US|APAC)_TOK_<abbreviation>_L<\d+>R<\d+>_<type>_DE`
   - Region: UK, US, APAC
   - Type: TOK (fixed)
   - Abbreviation: 2-4 characters (e.g., NM, ACCT, CARD, FT, FTGEN2, PWD, etc.)
   - Behavior: L{digits}R{digits} (e.g., L0R0, L6R4, L0R4)
   - Data type: UNC, ALN, DEC, NUM, CC, EML, DT
   - Suffix: _DE (fixed)

2. **Extraction success**: 
   - Step 1 or 2 → validated DE name → `extraction_failed = false`
   - Step 3 keyword-only → no DE name → `extraction_failed = true`
   - Invalid DE format → `extraction_failed = true`

3. **Ambiguity flagging**:
   - Both "tokenize" and "detokenize" present → `extraction_ambiguous = true`, HALT and ask user for clarification (do NOT default to either operation)

## Pass Condition

All rows processed; crypto_flags populated per column.

## Fail Action

None — validator is non-blocking. Extraction failures are caught at crypto assembly (STEP 06) and trigger REFUSAL, not validation failure.

## Notes

- Single column can have multiple tokenize/detokenize operations (e.g., source detokenize + output tokenize) — each handled separately by transform generator
- DE names are organisation-specific; never guessed or assumed from column name
- Protegrity DE pattern allows region flexibility (UK, US, APAC) for multi-region deployments
- Performance note: Protegrity FTGEN2_UNC data elements have documented performance bottlenecks for strings >1000 chars
