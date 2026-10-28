# Validator: config-transform-alias-validator

**Purpose**: Verify that source table aliases in the generated config file match those referenced in the generated transform code. Catches misalignment where the config defines aliases the transform doesn't use, or the transform references aliases not in the config — both cause runtime failures.

**Severity**: BLOCK if transform references alias not in config. WARNING if config defines alias never referenced in transform.

**Platform**: Glue + Databricks

---

## Prerequisites

- Generated config file exists:
  - Glue: `generated/glue/wrapper/{db}_{table}_config.json`
  - Databricks: `generated/databricks/src/Notebooks/{day0|day1}/{target_schema}_{table}/{target_schema}_{table}_config.yml`
  - Multi-source-system Glue: `generated/glue/wrapper/{db}_{table}_{source_system}_config.json`
  - Multi-source-system Databricks: `generated/databricks/src/Notebooks/{day0|day1}/{source_system}/{target_schema}_{table}/{target_schema}_{table}_config.yml`
- Generated transform file(s) exist:
  - Glue: `generated/glue/transforms/{db}_{table}_transform_{load_type}.py`
  - Databricks: `generated/databricks/src/Notebooks/{day0|day1}/{target_schema}_{table}/{target_schema}_{table}_transform.py`
  - Multi-source-system Glue: `generated/glue/transforms/{db}_{table}_{source_system}_transform_{load_type}.py`
  - Multi-source-system Databricks: `generated/databricks/src/Notebooks/{day0|day1}/{source_system}/{target_schema}_{table}/{target_schema}_{table}_transform.py`
- `session/session_state.json` exists (platform determined)

---

## Invocation

- **Primary**: Called by `/validate` Batch 4 (Consistency batch)
- **Gate**: `/push` refuses if any BLOCKING alias mismatch exists

---

## Checks

### Check 1 — Transform References Alias Not In Config (BLOCKING)

For each source alias referenced in the transform's `prepare_sources()` method:

1. Extract alias names from `self.source_data['alias_name']` or `self.reader.read_source_data('alias_name', ...)` patterns
2. Extract alias names from config:
   - **Glue**: Keys under `source.non-transactional` and `source.transactional` in config JSON
   - **Databricks**: Keys under `source_tables` in config YAML, or source alias keys in the config structure
3. **BLOCK** if the transform references an alias that does NOT exist in the config

This indicates the transform expects a source table that will not be read at runtime — causing a `KeyError` or `AnalysisException`.

**Error format:**
```
❌ Transform references alias 'wm_append_data' (line 47) but this alias is NOT defined
   in the config file. The SourceReader will fail at runtime.
   Fix: Add 'wm_append_data' to the config source definitions, or correct the alias name in the transform.
```

### Check 2 — Config Defines Alias Never Referenced In Transform (WARNING)

For each source alias defined in the config:

1. Verify the alias name appears somewhere in the transform code
2. **WARN** (do not block) if a config alias is never referenced

This indicates wasted I/O — a source table is read but never used. Non-blocking because the data is simply discarded, not corrupted.

**Error format:**
```
⚠️ Config defines alias 'lookup_rates' but this alias is never referenced in the transform code.
   This source will be read at runtime but its data is unused.
   Fix: Remove the unused source from config, or verify the transform uses it.
```

### Check 3 — Rolling Deletion Predicate Column References (ADVISORY)

**When**: `rolling_deletion.predicate` is present in the generated config.

The `rolling_deletion` predicate may reference columns that exist in the target table (e.g., `dw_bus_dt`, `dw_upd_lod_tmp`, `status`). These columns should be present in the target table's DDL/Mesh schema. This check is advisory — the predicate is a raw SQL expression and may reference computed values or functions that cannot be statically validated.

1. Extract column-like identifiers from `rolling_deletion.predicate` (tokens matching `[a-z_][a-z0-9_]*` that are not SQL keywords)
2. Cross-reference against target table schema (mesh JSON or DDL columns)
3. **ADVISORY** if any extracted identifier is not found in the target schema — it may be a function, alias, or computed value

**Error format:**
```
ℹ️ Rolling deletion predicate references '{identifier}' which is not in the target table schema.
   This may be valid (SQL function, computed expression) — manual review recommended.
```

---

## Known Exceptions (NOT flagged as violations)

| Category | Examples | Reason |
|----------|----------|--------|
| **CDC-only sources** | Sources used exclusively by `run_cdc()` for change detection | These may not appear in the transform `.py` but are consumed by the CDC layer |
| **Config filter-only sources** | Sources that exist only to apply config-level filters | Reader applies filters before the transform sees data |

**Key distinction**: Check 1 (BLOCKING) has no exceptions — if the transform code references an alias, it MUST exist in config. Check 2 (WARNING) may have false positives for CDC-only or filter-only sources.

---

## Integration Points

| Integration | When | Behavior |
|---|---|---|
| `/validate` Batch 4 | During full validation suite (Consistency batch) | Run validator → report findings |
| `/push` gate | Before push/commit | Refuse if any BLOCKING alias mismatch exists |

---

## Session State Fields

| Field | Type | Set By | Values |
|---|---|---|---|
| `config_transform_alias_result` | string | /validate Batch 4 | `"passed"`, `"failed"`, `"skipped"` |

---

## Pass Condition

All source aliases in the transform are defined in the config. Zero BLOCKING violations. WARNING violations (unused config aliases) are surfaced but do not block.
