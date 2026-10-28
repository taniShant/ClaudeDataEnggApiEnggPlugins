---
description: "Provenance tracking rules for every STTM row field — defines evidence source, confidence scoring (0.0–1.0), derivation method, artefact source, and precedence rules applied on conflicts."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-28
---

# Provenance Tracking Instructions

## Purpose
Every field in every STTM row must carry provenance metadata documenting:
- Where the value came from (evidence source)
- How confident we are (0.0–1.0)
- What method was used to derive it
- Which artifact provided the evidence
- Which precedence rule was applied if conflicts existed

## Provenance Methods

| Method | Description | Confidence Range |
|--------|-------------|-----------------|
| provided | Value comes directly from an input artifact (e.g., target template) without modification | 0.95–1.0 |
| extracted | Value derived from parsing SQL/PySpark/DDL code | 0.85–0.99 |
| inferred | Value deduced from metadata/profiling patterns | 0.5–0.8 |
| user_supplied | Value explicitly given by user in guided mode or interview | 0.95–1.0 |
| rule_generated | Value produced by plugin rules (audit columns, system columns, active flag) | 1.0 |

## Confidence Scoring

| Confidence | Meaning | Action |
|-----------|---------|--------|
| 0.95–1.0 | Certain — direct evidence, no ambiguity | Accept |
| 0.8–0.94 | High — strong evidence with minor uncertainty | Accept with note |
| 0.7–0.79 | Acceptable — evidence supports but not definitive | Accept (at threshold) |
| 0.5–0.69 | Low — some evidence but significant uncertainty | Route to guided mode |
| Below 0.5 | Very low — minimal or conflicting evidence | Route to guided mode (blocker) |

**Threshold:** 0.7 (configurable in precedence.yaml)

## Artifact References

Format: `{source_type}:{artifact_path}:{location}`

Examples:
- `sql:input/code/transform.sql:line_42`
- `template:input/target_schema.xlsx:column_C`
- `metadata:input/source_metadata/column_metadata.json:table.column`
- `interview:config/interview_questionnaire.yaml:question_1.1`
- `config:config/audit_columns.yaml:scd2.dw_lod_tmp`

## Per-Field Provenance JSON Format

```json
{
  "target_column": "column_name",
  "fields": {
    "source_database": {
      "value": "e_ilp_db",
      "provenance": {
        "source_of_evidence": "sql",
        "artifact": "input/code/transform.sql:line_1",
        "confidence": 0.99,
        "method": "extracted",
        "precedence_applied": "level_2 (SQL AST)"
      }
    },
    "business_logic": {
      "value": "CAST(balance_amt AS DECIMAL(18,2))",
      "provenance": {
        "source_of_evidence": "sql",
        "artifact": "input/code/transform.sql:line_2",
        "confidence": 0.95,
        "method": "extracted",
        "reasoning": "CAST expression found in SELECT item"
      }
    },
    "additional_context": {
      "value": "Source stored as FLOAT; precision cast required",
      "provenance": {
        "source_of_evidence": "ai_assisted",
        "confidence": 0.8,
        "method": "inferred",
        "reasoning": "Source datatype FLOAT differs from target DECIMAL"
      }
    }
  }
}
```

## Conflict Resolution in Provenance

When multiple sources provide conflicting evidence for the same field:

1. Apply precedence hierarchy (see precedence.yaml):
   - Level 1 (Template/DDL) > Level 2 (SQL/Requirements) > Level 3 (Metadata) > Level 4 (Supporting) > Level 5 (Profiling)
2. Record the winning source AND the losing source in provenance
3. If same-level conflict → route to guided mode, record both options
4. Log: which precedence was applied and why

```json
{
  "field": "source_column",
  "value": "account_id",
  "provenance": {
    "source_of_evidence": "sql",
    "artifact": "input/code/transform.sql:line_1",
    "confidence": 0.95,
    "method": "extracted",
    "precedence_applied": "sql (level 2) wins over source_data_dictionary (level 4)",
    "conflict_noted": {
      "alternative_value": "acct_num",
      "alternative_source": "source_data_dictionary:input/source_dictionary/data_dictionary.json:row_5",
      "reason_rejected": "Current SQL uses account_id; data dictionary may be stale"
    }
  }
}
```

## Fields That Require Provenance

ALL 16 mapping columns in every row must have provenance. Additionally:
- Source Volumetrics values
- Scenario classification decision
- Interview answers (how each was resolved)

## Output File

Provenance metadata is written to the provenance JSON file (e.g., `output/{prefix}_provenance.json` — path determined by the output naming convention) in the format:
```json
{
  "rows": [
    { "target_column": "...", "fields": { ... } }
  ],
  "_meta": {
    "generated_at": "ISO8601",
    "template_version": "1.0",
    "classification": {"data_product_type": "FDP", "table_type": "NonTransactional_SCD2", "crypto_aspect": "None"},
    "validation": { "pass": 0, "warning": 0, "blocker": 0 },
    "confidence_summary": { "high": 0, "medium": 0, "low": 0 },
    "questions": [],
    "interview": {
      "answered": 0,
      "auto_resolved": 0,
      "deferred_to_guided": 0,
      "responses": []
    }
  }
}
```
