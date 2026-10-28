---
description: "Conditional STTM extension for crypto transformation patterns — loaded when crypto_aspect is not None to define detokenize/unprotect patterns with DE name requirements and verbose metadata labels."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-28
---

# Crypto Transformation Patterns (Extension)

> **Loaded conditionally** — only when `classification.crypto_aspect != "None"`.

## 11. Crypto — Detokenize (unprotect)

**Detection:** `unprotect` UDF in SQL expression OR crypto config with direction=detokenize.

**Template Output:**
- Business Logic: `cloud_api_udf_{{DE}}_unprotect({{source_column}})`
- Transformation Type: `Derived`
- Additional Context: "Detokenize using Protegrity DE: {{DE}}"
- Source Column: The encrypted source column

**CRITICAL:** DE name must NEVER be inferred. Must be explicitly provided.

**Example:**
- Business Logic: `cloud_api_udf_UK_TOK_SORTCOD_L0R0_NUM_DE_unprotect(sort_code_encrypted)`
- Additional Context: "Detokenize using Protegrity DE: UK_TOK_SORTCOD_L0R0_NUM_DE"

**Verbose metadata labels (always emit alongside the UDF expression):**
```
Value: cloud_api_udf_UK_TOK_SORTCOD_L0R0_NUM_DE_unprotect(src.sort_code_encrypted)
Crypto Operation: DETOKENIZE
Crypto DE: UK_TOK_SORTCOD_L0R0_NUM_DE
Crypto Source Column: src.sort_code_encrypted
```

---

## 12. Crypto — Tokenize (protect)

**Detection:** `protect` UDF in SQL expression OR crypto config with direction=tokenize.

**Template Output:**
- Business Logic: `cloud_api_udf_{{DE}}_protect({{source_column}})`
- Transformation Type: `Derived`
- Additional Context: "Tokenize using Protegrity DE: {{DE}}; source is clear text"
- Source Column: The clear-text source column

**Example:**
- Business Logic: `cloud_api_udf_UK_TOK_NI_NUM_L0R0_ID_DE_protect(ni_number_clear)`
- Additional Context: "Tokenize using Protegrity DE: UK_TOK_NI_NUM_L0R0_ID_DE; source is clear text"

**Verbose metadata labels:**
```
Value: cloud_api_udf_UK_TOK_NI_NUM_L0R0_ID_DE_protect(src.ni_number_clear)
Crypto Operation: TOKENIZE
Crypto DE: UK_TOK_NI_NUM_L0R0_ID_DE
Crypto Source Column: src.ni_number_clear
```

---

## 13. Crypto — Detokenize + Re-tokenize (Both)

**Detection:** Nested protect(unprotect(...)) OR crypto config with direction=both.

**CRITICAL:** Nesting order is: unprotect INSIDE, protect OUTSIDE. Source DE ≠ Target DE.

**Template Output:**
- Business Logic: `cloud_api_udf_{{TARGET_DE}}_protect(cloud_api_udf_{{SOURCE_DE}}_unprotect({{source_column}}))`
- Transformation Type: `Derived`
- Additional Context: "Detokenize source DE ({{SOURCE_DE}}) then re-tokenize with target DE ({{TARGET_DE}})"

**Example:**
- Business Logic: `cloud_api_udf_UK_TOK_ACCT_L2R1_NUM_DE_protect(cloud_api_udf_UK_TOK_ACCT_L0R0_NUM_DE_unprotect(acct_num_encrypted))`
- Additional Context: "Detokenize source DE (UK_TOK_ACCT_L0R0_NUM_DE) then re-tokenize with target DE (UK_TOK_ACCT_L2R1_NUM_DE)"

**Verbose metadata labels:**
```
Value: cloud_api_udf_UK_TOK_ACCT_L2R1_NUM_DE_protect(cloud_api_udf_UK_TOK_ACCT_L0R0_NUM_DE_unprotect(src.acct_num_encrypted))
Crypto Operation: BOTH
Crypto Source DE: UK_TOK_ACCT_L0R0_NUM_DE
Crypto Target DE: UK_TOK_ACCT_L2R1_NUM_DE
Crypto Source Column: src.acct_num_encrypted
```
