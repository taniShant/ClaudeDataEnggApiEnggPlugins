---
description: End-to-end structural consistency validator for NonTransactional_SCD1 tables
---

**Platform**: Glue + Databricks

# SCD1 Structural Validator

Validates that all generated artefacts are internally consistent for NonTransactional_SCD1 table_type. Ensures intent, config, mesh/DDL, transform, and writer are aligned to SCD1 semantics (simple upsert — no temporal tracking).

**Invoked by:** `/validate` Batch 2 Part C (SCD1 structural validation)

**Gate:** `/push` refuses if `session_state.scd1_structural_result != "passed"` for any NonTransactional_SCD1 table.

---

## Prerequisites

- `session/intent_identification.json` exists with `table_type == "NonTransactional_SCD1"` for at least one target table
- Generated artefacts exist for the target table (config, mesh/DDL, transform, writer dispatch)
- `session/mapping_parsed.json` exists with column definitions

---

## Checks

### CHECK 1 — Intent Consistency

Read `session/intent_identification.json` for each target table where `table_type == "NonTransactional_SCD1"`:

| Assertion | Expected | BLOCK if violated |
|-----------|----------|-------------------|
| `table_type` | `"NonTransactional_SCD1"` | N/A (entry condition) |
| `eff_date_source` | `"none"` | Yes — SCD1 has no effective dating |
| `partition_key_columns` | Does NOT contain `"active"` | Yes — SCD1 has no active column |

**Error format:**
```
❌ CHECK 1 FAILED — Intent inconsistency for SCD1 table '{table_name}'
   {assertion}: expected {expected}, found {actual}
   Fix: Re-run /identify-intent — ensure SCD1 intent does not reference temporal/active fields
```

---

### CHECK 2 — Config Consistency

Read config file (`generated/glue/wrapper/*_config.json` or `generated/databricks/src/Notebooks/*/config.yml`):

| Assertion | Expected | BLOCK if violated |
|-----------|----------|-------------------|
| `cdc` section exists | Yes | Yes — SCD1 still requires CDC for primary keys |
| `cdc` contains ONLY `primary_key_cols` + `exclude_cols` | No other keys | Yes |
| `cdc` does NOT contain `high_ended_date` | Absent | Yes |
| `cdc` does NOT contain `snapshot_mode` | Absent | Yes |
| Source tables placement (Glue) | Under `"non-transactional-scd1"` key | Yes |
| Source tables placement (Databricks) | Under `"non_transactional_scd1"` key | Yes |
| Default filter for SCD1 sources | `"1=1"` (no active filter) | Yes |

**Error format:**
```
❌ CHECK 2 FAILED — Config inconsistency for SCD1 table '{table_name}'
   {assertion}: expected {expected}, found {actual}
   Fix: Re-run /gen-config — ensure SCD1 config uses minimal CDC section without SCD2 keys
```

---

### CHECK 3 — Mesh/DDL Consistency

Read mesh JSON (`generated/glue/mesh/*_mesh.json`) or DDL (`generated/databricks/src/Notebooks/utilities/*_table_creation_utility.py`):

| Assertion | Expected | BLOCK if violated |
|-----------|----------|-------------------|
| Audit columns present | `dw_lod_tmp`, `dw_upd_lod_tmp` only | Yes |
| `eff_start_date` absent | Not in schema | Yes |
| `eff_end_date` absent | Not in schema | Yes |
| `active` absent | Not in schema | Yes |
| Partition column | NOT `"active"` | Yes |

**Error format:**
```
❌ CHECK 3 FAILED — Mesh/DDL inconsistency for SCD1 table '{table_name}'
   Found SCD2 column '{col}' in target schema — SCD1 does not use temporal tracking
   Fix: Re-run /gen-mesh or /gen-ddl — remove eff_start_date, eff_end_date, active from schema
```

---

### CHECK 4 — Transform Consistency

Read `*_transform_day0.py` and `*_transform_day1.py` (or BAU equivalent):

**Day0 assertions:**

| Assertion | Expected | BLOCK if violated |
|-----------|----------|-------------------|
| Derives `dw_lod_tmp` | Yes | Yes |
| Derives `dw_upd_lod_tmp` | Yes | Yes |
| Does NOT derive `eff_start_date` | Absent | Yes |
| Does NOT derive `eff_end_date` | Absent | Yes |
| Does NOT derive `active` | Absent | Yes |
| No temporal stitching logic | Absent | Yes |
| No CDC expire+insert pattern | Absent | Yes |

**Day1/BAU assertions:**

| Assertion | Expected | BLOCK if violated |
|-----------|----------|-------------------|
| Outputs business columns only | No audit column derivation | Yes |
| No temporal stitching logic | Absent | Yes |
| No CDC expire+insert pattern | Absent | Yes |
| No `active = '1'` filter on SCD1 sources | Absent (unless source is SCD2) | Yes |

**Error format:**
```
❌ CHECK 4 FAILED — Transform inconsistency for SCD1 table '{table_name}'
   {description of violation}
   Fix: Re-run /gen-transform — ensure SCD1 transform derives only dw_lod_tmp + dw_upd_lod_tmp (day0) and no audit columns (day1)
```

---

### CHECK 5 — Writer Dispatch

Read writer invocation in transform `load()` method or driver file:

| Assertion | Expected | BLOCK if violated |
|-----------|----------|-------------------|
| Day1/BAU `write()` dispatches to | `_write_scd1_upsert()` | Yes |
| Does NOT dispatch to | `_write_cdc_merge()` | Yes |
| MERGE SQL uses | UPDATE + INSERT (simple upsert) | Yes |
| MERGE SQL does NOT reference | `eff_start_date`, `eff_end_date`, `active` | Yes |
| MERGE SQL does NOT use | expire+insert pattern (INSERT new + UPDATE old with active=0) | Yes |

**Error format:**
```
❌ CHECK 5 FAILED — Writer dispatch inconsistency for SCD1 table '{table_name}'
   Writer dispatches to {actual_method} instead of _write_scd1_upsert()
   Fix: Ensure TargetWriter routes NonTransactional_SCD1 tables to _write_scd1_upsert() which performs simple MERGE (UPDATE existing + INSERT new)
```

---

### CHECK 6 — Rolling Deletion Configuration (if present)

**When**: `rolling_deletion` section exists in generated config AND `table_type` is `NonTransactional_SCD1`
**Severity**: WARNING

| Assertion | Expected | BLOCK if violated |
|-----------|----------|-------------------|
| `rolling_deletion.enabled` | Boolean (`true` or `false`) | No (WARNING) |
| `rolling_deletion.predicate` | Non-empty string | No (WARNING) |
| Predicate does NOT reference `eff_start_date` | Absent | No (WARNING — SCD1 tables do not have this column) |
| Predicate does NOT reference `eff_end_date` | Absent | No (WARNING — SCD1 tables do not have this column) |
| Predicate does NOT reference `active` | Absent | No (WARNING — SCD1 tables do not have this column) |
| If predicate contains `{current_business_date}` | Appears in valid SQL context (inside CAST or string literal) | No (WARNING) |

If `rolling_deletion` is absent for an SCD1 table, this is acceptable — rolling deletion is optional.

**Error format:**
```
⚠️ CHECK 6 WARNING — Rolling deletion configuration issue for SCD1 table '{table_name}'
   {assertion}: expected {expected}, found {actual}
   Fix: Correct the rolling_deletion section — ensure predicate is valid SQL for an SCD1 table (no SCD2-only columns)
```

---

## Outcome

- **ALL checks pass** → `scd1_structural_result = "passed"` — VALID
- **ANY check fails** → `scd1_structural_result = "failed"` — report specific failure with:
  - Which CHECK number failed
  - The specific assertion that was violated
  - The expected vs actual values
  - Remediation command to re-generate the offending artefact

---

## Session State Fields

| Field | Type | Set By | Values |
|---|---|---|---|
| `scd1_structural_result` | string | This validator | `"passed"`, `"failed"`, `"skipped_not_scd1"` |
| `scd1_structural_failures` | array\|null | This validator | Array of check failure objects, or null if passed |

---

## Integration Points

| Integration | When | Behavior |
|---|---|---|
| `/validate` Batch 2 Part C | During structural validation | Run all 6 checks → report findings |
| `/push` gate | Before push/commit | Refuse if `scd1_structural_result != "passed"` for any SCD1 table |
| `/review` Phase 3.6 | During code review | Cross-references these checks for review findings |

---

## Relationship to Other Validators

| Validator | Relationship |
|-----------|-------------|
| `cdc-presence-assertion-validator` | Checks 5-7 overlap with this validator's CHECK 2 — both enforce SCD1 CDC constraints; this validator is the authoritative end-to-end check |
| `template-landmark-preservation-validator` | Validates template structure is preserved; this validator validates SCD1 semantic correctness |
| `dtxog-structure-validator` | Independent — DTXOG structure is table_type-agnostic |
