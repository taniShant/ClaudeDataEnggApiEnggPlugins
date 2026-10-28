---
description: "Universal prohibitions that prevent all agents from fabricating column names, infrastructure values, method signatures, or table logic — the foundational anti-hallucination layer loaded by every agent."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-07-08
---

# Anti-Hallucination Core Rules (Universal)

> These rules apply to ALL agents and commands in the plugin. Individual specs add context-specific constraints on top of these.

## Universal Prohibitions

1. **NEVER invent source column names** — Use ONLY names from `mapping_parsed.json`
2. **NEVER invent target column/table names** — Use ONLY names from `mapping_parsed.json`
3. **NEVER invent infrastructure values** — S3 bucket names, AWS account IDs, ITSI codes, secret names, catalog names must come from skills (tenancy, aws, standards, ops) or explicit user input
4. **NEVER invent method/function signatures** — Use ONLY APIs defined in the source files read during GATHER phase (SourceReader, TargetWriter, foundation library)
5. **NEVER fabricate transformation logic** — Generate ONLY from mapping document content (transformation_logic, structured_transformation, column_mappings)
6. **NEVER cross-contaminate tables** — Each target table's context is isolated; do NOT reference columns, logic, or patterns from other tables
7. **NEVER mix platforms** — If `session_state.platform == "glue"`, generate ONLY Glue patterns. If `"databricks"`, generate ONLY Databricks patterns.

## Allowed Config Sections

The following are the canonical top-level sections in a generated pipeline config (`config.json` / `config.yml`). Do NOT invent sections outside this list.

| Section | Required | Applies To | Notes |
|---|---|---|---|
| `source` | Yes | All | Source table definitions (transactional / non-transactional) |
| `target` | Yes | All | Target table, schema, catalog |
| `filters` | Yes | All | Day0 / Day1 / catch_up_mode filter predicates |
| `cdc` | Conditional | NonTransactional (SCD1, SCD2) | Primary key cols, exclude cols; SCD2 adds snapshot_mode, high_ended_date |
| `date_control` | Conditional | Glue only | Workday logic, backup filename |
| `environments` | Conditional | Databricks only | Multi-env catalog resolution |
| `source_catalogs` | Conditional | Databricks only | Per-environment source catalog overrides |
| `rolling_deletion` | Optional | Transactional, NonTransactional_SCD1 (NOT SCD2) | Post-write data lifecycle deletion. Sub-fields: `enabled` (bool), `predicate` (SQL WHERE clause). TargetWriter._rolling_delete() executes the predicate after each successful write. NOT applicable to SCD2. |

## When Uncertain

- If a value cannot be derived from authoritative sources → use `{{placeholder}}` (non-blocking) or HALT (blocking)
- If a column is referenced in transformation_logic but not found in source metadata → emit warning comment, use mapping name (mapping is authoritative)
- If infrastructure value is needed but skill doesn't provide it → HALT with "provide via domain knowledge or intent_overrides"
