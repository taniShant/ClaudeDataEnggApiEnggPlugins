---
description: "Rules for handling Protegrity Data Element (DE) crypto columns — extraction failure behaviour, detokenize→transform→tokenize UDF patterns, and DE name resolution via regex matching."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-03
---

# Crypto Refusal Protocol (Universal)

> Applies to ALL agents that handle Protegrity DE (Data Element) crypto columns.

## When DE Extraction Fails

If the crypto DE name cannot be extracted from the mapping column's crypto metadata:

1. Set `extraction_failed: true` on the column's crypto_flags
2. Do **NOT** emit a placeholder DE name (e.g., `{{de_name}}`)
3. Do **NOT** generate UDF calls with missing DE names
4. Log the extraction failure with the column name and raw crypto metadata
5. Continue processing non-crypto columns normally

## UDF Pattern Rules

- Crypto UDFs MUST use `spark.sql()` syntax — NOT DataFrame API
- Transformation flow: **detokenize → transform → tokenize** (3-step, never 2-step)
- DE name extraction regex: Use the pattern from `database-naming-standards` skill (DE Naming Pattern section)

## Validation

Validators must check:
- No `extraction_failed: true` columns have generated UDF calls
- All UDF calls reference a valid DE name matching the DE naming pattern
- No placeholder DE names remain in generated code
