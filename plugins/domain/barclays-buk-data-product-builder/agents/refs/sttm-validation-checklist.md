---
description: "Summary of 102 STTM validation rules — covers schema validations, mapping-content validations, business rule validations, and provenance validations with rule IDs and severity levels."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-28
---

> **Authoritative source:** The complete set of 102 validation rules is defined in
> `${CLAUDE_PLUGIN_ROOT}/configs/sttm/validation_rules.yaml`. This checklist is a
> summary reference; the YAML is the source of truth for check IDs, severity, and logic.

# Validation Checklist

Execute every check below in order. Classify each as: PASS, WARNING, or BLOCKER.

## Schema Validations

- [ ] **S1** [BLOCKER] Target column name is valid snake_case: lowercase, underscores only, no leading digits. Pattern: ^[a-z][a-z0-9_]*$
- [ ] **S2** [BLOCKER] Target datatype is valid: string, int, bigint, decimal(p,s), date, timestamp, boolean, float, double
- [ ] **S3** [BLOCKER] Null flag is exactly "Y" or "N"
- [ ] **S4** [WARNING] Key Column is "Y", "N", or blank
- [ ] **S5** [WARNING] Transformation Type is: Direct, Derived, Lookup, Direct - Type Cast, or blank
- [ ] **S6** [WARNING] Target Table Type is: scd2, scd1, transactional, or blank
- [ ] **S7** [WARNING] Default Value (if present) is compatible with target datatype

## Mapping-Content Validations

- [ ] **M1** [BLOCKER] Every target column has exactly one mapping row
- [ ] **M2** [BLOCKER] No unmapped target columns remain unexplained
- [ ] **M3** [BLOCKER] Source Database populated for non-system/non-derived columns
- [ ] **M4** [BLOCKER] Source Table Name populated for non-system/non-derived columns
- [ ] **M5** [BLOCKER] Source Column Name populated for non-system/non-derived columns
- [ ] **M6** [BLOCKER] Business Logic non-empty for every row
- [ ] **M7** [WARNING] Additional Context non-empty for every row
- [ ] **M8** [BLOCKER] Target Table Description on first row only per table (populated on first row; empty on subsequent rows)
- [ ] **M9** [BLOCKER] Target Column Description populated for every row
- [ ] **M10** [BLOCKER] PK columns (Key Column = Y) have Null Flag = N
- [ ] **M11** [WARNING] At least one column per table has Key Column = Y
- [ ] **M12** [WARNING] Source column exists in declared source table (if metadata available)
- [ ] **M13** [WARNING] Source table exists in declared source database (if metadata available)
- [ ] **M14** [WARNING] Default Value present when COALESCE detected in Business Logic
- [ ] **M15** [BLOCKER] Multi-table mappings use structured compact newline-separated format with unique table aliases
- [ ] **M16** [BLOCKER] Structured format uses alias.column = alias.column on BOTH sides of Join ON conditions
- [ ] **M17** [BLOCKER] Join N Type is exactly LEFT, INNER, RIGHT, or FULL

## Scenario-Specific Validations

- [ ] **SC1** [BLOCKER] SCD2: has eff_start_date, eff_end_date, active columns
- [ ] **SC2** [BLOCKER] SCD2: eff_end_date references configured high-end date
- [ ] **SC3** [BLOCKER] SCD2: active flag derives from eff_end_date comparison
- [ ] **SC4** [WARNING] SCD2: eff_start_date has real source column (not system-generated)
- [ ] **SC5** [WARNING] Transactional: does NOT have eff_start/end/active columns
- [ ] **SC6** [BLOCKER] Crypto: valid DE name in expression
- [ ] **SC7** [BLOCKER] Crypto: UDF naming = cloud_api_udf_{DE}_{protect|unprotect}
- [ ] **SC8** [BLOCKER] Crypto Both: source DE ≠ target DE
- [ ] **SC9** [BLOCKER] Multi-source: all source references fully qualified
- [ ] **SC10** [WARNING] Multi-source: LEFT JOIN columns have Null Flag = Y
- [ ] **SC11** [WARNING] Aggregated: PARTITION BY clause present

## Artifact-Consistency Validations

- [ ] **A1** [WARNING] SQL-derived mappings align with declared target columns
- [ ] **A3** [WARNING] Profiling null% does not contradict null flag
- [ ] **A4** [WARNING] User instructions do not silently override authoritative metadata
- [ ] **A5** [WARNING] Columns renamed between artifacts detected and mapped
- [ ] **A6** [WARNING] Code-derived source columns exist in declared source schema

## Output-Format Validations

- [ ] **F1** [BLOCKER] All 16 template columns present
- [ ] **F2** [BLOCKER] Column order matches template spec (A–P)
- [ ] **F3** [BLOCKER] No extra columns beyond 16
- [ ] **F4** [WARNING] System columns use (system)/(derived) markers
- [ ] **F5** [WARNING] Audit columns present for table type
- [ ] **F6** [BLOCKER] Output on correct scenario sheet
- [ ] **F7** [WARNING] Source Volumetrics populated for all source tables
- [ ] **F8** [WARNING] Source Volumetrics Primary Key populated
- [ ] **F9** [WARNING] Tab colors match spec
- [ ] **F10** [BLOCKER] Row 1 headers exactly match template (case-sensitive)
- [ ] **F11** [BLOCKER] Row 2 contains instruction text (not overwritten)

## Output Format

```json
{
  "validation_results": {
    "total_checks": 102,
    "pass": 0,
    "warning": 0,
    "blocker": 0,
    "results": [
      {
        "id": "S1",
        "category": "schema",
        "severity": "blocker",
        "status": "pass|warning|blocker",
        "message": "description of issue if not pass",
        "affected_rows": [],
        "fix_suggestion": ""
      }
    ]
  }
}
```
