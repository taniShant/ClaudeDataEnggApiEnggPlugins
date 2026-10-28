# Validator: excel-column-validator

**Purpose**: Verify all 12 required Excel column headers are present (with case-insensitive + semantic variant matching) and detect up to 4 optional enrichment columns.

**Severity**: HALT — generation stops until all 12 required headers are resolved.

**Platform**: Glue + Databricks

---

## Required Headers (canonical names + semantic variants)

| # | Canonical Header | Semantic Variants | Required |
|---|---|---|---|
| 1 | `Target Database` | `target db`, `target_database` | YES |
| 2 | `Target Table` | — | YES |
| 3 | `Target Column Name` | — | YES |
| 4 | `Target Column Definition/Description` | `target column desc`, `target_column_definition`, `target_column_description` | YES |
| 5 | `Target Column Datatype` | — | YES |
| 6 | `Target Column Null Flag` | — | YES |
| 7 | `Source database/Source DB` | `source db`, `source_database`, `source database`, `source_db` | YES |
| 8 | `Source Table Name` | — | YES |
| 9 | `Source Column Name` | — | YES |
| 10 | `Business Logic/Transformation Logic` | `business logic`, `transformation`, `transformation_logic`, `transform logic` | YES |
| 11 | `Additional Context` | — | YES |
| 12 | `Target Table description` | `target table desc`, `table_description`, `table description` | YES |

## Optional Enrichment Headers

| # | Canonical Header | Semantic Variants | Purpose |
|---|---|---|---|
| 13 | `Transformation Type` | `transformation_type`, `transform type` | Classifies transformation: Direct / Derived / Lookup / Direct - Type Cast |
| 14 | `Default Value` | `default_value`, `default` | Fallback value when logic yields NULL |
| 15 | `Target Table Type` | `target_table_type`, `table type`, `target table type` | Declares table type: NonTransactional_SCD2 / NonTransactional_SCD1 / Transactional |
| 16 | `Key Column` | `key_column`, `key col`, `primary key`, `pk` | Marks primary/business key columns: Y/N |

---

## Validation Logic

1. Read the Excel file header row and normalize all headers to lowercase + underscore-to-space conversion
2. **Required headers (1-12):**
   - For each canonical header, attempt match in order: exact lowercase → semantic variant
   - If match found: record canonical name (not user input)
3. **Optional headers (13-16):**
   - After required validation, scan remaining unmatched headers against optional canonical names + semantic variants
   - If match found: record in `optional_columns_detected[]` with canonical name
   - If not found: no error (columns are optional)
4. If all 12 required matched → PASS (proceed to row extraction)
5. If any required header missing after semantic matching → HALT

## Pass Condition

All 12 required canonical headers matched (either exactly or via semantic variant). Optional headers enhance parsing but do not gate it.

## Fail Action

HALT. Output:
```
❌ Excel validation failed — missing required column headers (after semantic matching):
  - {canonical_name_1} (expected variants: {variants})
  - {canonical_name_2} (expected variants: {variants})

Please add these headers to the mapping Excel and re-run /parse-mapping.
```

Do NOT proceed with row extraction. Do NOT output partial `mapping_parsed.json`.

## Optional Header Detection Output

When optional columns are detected, log and store:
```
✓ Optional enrichment columns detected: [Transformation Type, Key Column, Target Table Type]
  → These will enhance intent resolution and transform generation.
```

Store in session state: `optional_mapping_columns = ["Transformation Type", "Key Column", "Target Table Type"]`

---

## Notes

- Column order does not matter — any order is valid as long as all 12 required are present
- Leading/trailing whitespace in header cells is stripped before comparison
- Headers normalized to lowercase + underscore-to-space for matching
- Semantic variant matching allows flexibility in naming (e.g., "source db" accepted as `Source database/Source DB`)
- Canonical names stored in parsed output for consistent downstream processing
- Original header text preserved in audit log for traceability
- Columns beyond the 12 required + 4 optional that do not match any known header are ignored (not an error)
- Sheet name: validate first non-empty sheet; if multiple sheets, check the first one; warn if multiple sheets present
