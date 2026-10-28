# Validator: source-table-type-consistency-validator

**Purpose**: Validate that config.json source groupings (`non-transactional` / `transactional`) match the source table type classifications in `session/source_table_metadata.json`, and that filter expressions are appropriate for each source's type.

**Severity**: BLOCK on type/filter mismatch or unresolved source type.

**Platform**: Glue + Databricks

---

## Prerequisites

- `session/source_table_metadata.json` exists and is populated (`/classify-sources` completed)
- Generated `config.json` exists for the target table

---

## Checks

### Check 1 — Metadata File Exists

`session/source_table_metadata.json` must exist and contain entries for all mapping sources with supported prefixes. If absent, BLOCK — source classification was not completed.

### Check 2 — Source Grouping Matches Classification

For each source table alias in `config.json`, detect config layout first:

**Layout detection**: If first-level keys under `source` are known table_type values (`non-transactional`, `non-transactional-scd1`, `transactional`) → single-data-flow layout. Otherwise → multiple-data-flow layout (keys are source_system names containing table_type dicts).

**Single-data-flow layout** — validate directly:

| config.json section | Expected source_table_metadata.source_table_type |
|---|---|
| `source.non-transactional.{alias}` | `NonTransactional` |
| `source.non-transactional-scd1.{alias}` | `NonTransactional` |
| `source.transactional.{alias}` | `Transactional` |

**Multiple-data-flow layout** — unwrap source_system level first, then validate:

| config.json section | Expected source_table_metadata.source_table_type |
|---|---|
| `source.{source_system}.non-transactional.{alias}` | `NonTransactional` |
| `source.{source_system}.non-transactional-scd1.{alias}` | `NonTransactional` |
| `source.{source_system}.transactional.{alias}` | `Transactional` |

**BLOCK** if:
- A source classified as `NonTransactional` appears under a `transactional` section
- A source classified as `Transactional` appears under a `non-transactional` or `non-transactional-scd1` section
- A source classified as `Unknown` appears under any section — this should not occur (`/classify-sources` must resolve all source types before generation proceeds; re-run if encountered)

**WARNING** if:
- A source with `classification_source: "domain_knowledge"` or `"mapping_document"` has a type mismatch — emit WARNING (not BLOCK) because lower-priority confidence is inherently lower

### Check 3 — Filter Expression Type Consistency

Resolve filters using the same layout-aware path as Check 2:
- **Single-data-flow**: `filters.{op}.{table_type}.{alias|default}`
- **Multiple-data-flow**: `filters.{op}.{source_system}.{table_type}.{alias|default}`

For each source under a `non-transactional` or `non-transactional-scd1` section:
- Its resolved filter must NOT use `dw_bus_dt` as the primary filter column
- Expected filter patterns: `eff_start_date`, `active`, `1=1`, or custom alias filter

For each source under a `transactional` section:
- Its resolved filter must NOT use `eff_start_date` or `active` as the primary filter column
- Expected filter patterns: `dw_bus_dt`, or custom alias filter

**BLOCK** if filter uses wrong type's standard columns.

### Check 4 — All Sources Accounted For

Every unique `source_db.source_table` pair from `mapping_parsed.json` (excluding skip_tables and UNSUPPORTED_DB_PREFIX) must have a corresponding entry in `source_table_metadata.json`. Use lowercase keys for lookup.

**BLOCK** if any source is missing from metadata (indicates incomplete source classification).

### Check 5 — Low-Confidence Classification Awareness

For each source with `classification_source` NOT IN (`"source_volumetrics"`):
- Log an informational WARNING listing lower-confidence classified sources:
  ```
  ⚠️ {N} source table(s) classified via lower-priority source:
     - {db.table1} → {type} (source: {classification_source}, confidence: {confidence})
     - {db.table2} → {type} (source: {classification_source}, confidence: {confidence})
  
  Consider adding explicit table_type to Source Volumetrics tab for authoritative classification.
  ```

**Never BLOCK** on lower-priority classification alone — it is a valid operation.

> Note: `source_volumetrics`-classified tables are treated as authoritative (HIGH confidence,
> analyst-declared). They do NOT trigger this awareness warning.

---

## Pass Condition

All 4 checks pass. All sources correctly grouped by their classified type with appropriate filters.

## Fail Action

**BLOCK** (type/filter mismatch):
```
❌ Source table type consistency violation:
   Source 'e_ilp_db.events_log' classified as Transactional (HIGH confidence, H0b)
   but placed under source.non-transactional in config.json.
   
   This will cause incorrect filter application at runtime
   (eff_start_date filter applied to a Transactional table that uses dw_bus_dt).
   
   Fix: Move source to source.transactional in config.json and ensure
   filters.*.transactional.default is set.
```

**BLOCK** (unresolved source type):
```
⛔ Source 'fdp_uk_mortgage_db.MRTG_REF_SRC_DECODE' has no classification in source_table_metadata.json.
   /classify-sources must resolve all source table types before generation.
   Provide via source_table_metadata.json or re-run /classify-sources.
```

---

## Notes

- This validator runs as part of `/validate` (Step 10)
- It depends on `session/source_table_metadata.json` existing — if source classification failed completely, this validator cannot run (reports BLOCK for missing metadata)
- All source tables must be classified as NonTransactional or Transactional before generation — `/classify-sources` HALTs and asks the user if classification is ambiguous
- Lower-priority classified sources (`classification_source` NOT IN ("source_volumetrics")) generate WARNING only, never BLOCK for type mismatches — confidence is inherently lower
- Volumetrics-classified sources (`classification_source` = "source_volumetrics") are authoritative (HIGH confidence) — same BLOCK behaviour as other HIGH-confidence sources
- The validator does NOT modify config.json — it only reports violations for the user to fix
