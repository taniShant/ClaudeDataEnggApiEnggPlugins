# Validator: cdc-presence-assertion-validator

**Purpose**: Deterministically assert that config.json contains a `"cdc"` section with non-empty `primary_key_cols` when the target table is NonTransactional (SCD1 or SCD2). This is a pure conditional check — no LLM judgment required. Catches LLM attention failures where the generator omits conditional template sections.

**Severity**: BLOCK if NonTransactional table config lacks CDC section.

**Platform**: Glue + Databricks

---

## Prerequisites

- Generated config file exists (`generated/glue/wrapper/*_config.json` or `generated/databricks/src/Notebooks/*/config.yml`)
- `session/intent_identification.json` exists with `table_type` resolved per target table
- `session/mapping_parsed.json` exists with `key_column` flags identifying primary keys

---

## Invocation

- **Primary**: Called inline by `/gen-config` STEP FINAL (runs immediately after config file generation)
- **Secondary**: Called by `/validate` Batch 4 (consistency validation suite)
- **Gate**: `/push` refuses if `session_state.cdc_assertion_result != "passed"`

---

## Logic (Deterministic — No LLM)

```
FOR each target table in session:
  table_type = intent_identification[table].table_type
  config_file = locate config file for this table

  IF table_type == "NonTransactional_SCD2":
    ASSERT config_file contains "cdc" key (JSON) or "cdc:" section (YAML)
    ASSERT config["cdc"]["primary_key_cols"] is a non-empty array
    ASSERT each entry in primary_key_cols exists in mapping_parsed target columns or is a known audit column

    IF any assertion fails:
      BLOCK — report specific missing element

  ELSE IF table_type == "NonTransactional_SCD1":
    ASSERT config_file contains "cdc" key (JSON) or "cdc:" section (YAML)
    ASSERT config["cdc"]["primary_key_cols"] is a non-empty array
    ASSERT each entry in primary_key_cols exists in mapping_parsed target columns or is a known audit column
    ASSERT config["cdc"] does NOT contain "high_ended_date" key
    ASSERT config["cdc"] does NOT contain "snapshot_mode" key
    ASSERT config["cdc"] contains ONLY "primary_key_cols" + "exclude_cols" (no other keys)
    ASSERT mesh/DDL does NOT contain columns: eff_start_date, eff_end_date, active
    ASSERT partition column != "active"

    IF any assertion fails:
      BLOCK — report specific failing element with SCD1-specific guidance

  ELSE IF table_type == "Transactional":
    IF config_file contains "cdc" key:
      WARN — CDC section present for Transactional table (unusual but not blocking)

  ELSE:
    SKIP — unknown table_type (let other validators handle)
```

---

## Checks

### Check 1 — CDC Section Presence (BLOCKING for NonTransactional_SCD1 and NonTransactional_SCD2)

Read config file → check for `"cdc"` key at root level.

**BLOCK** if:
- `table_type == "NonTransactional_SCD1"` or `"NonTransactional_SCD2"` AND `"cdc"` key is missing from config
- `table_type == "NonTransactional_SCD1"` or `"NonTransactional_SCD2"` AND `"cdc"` key exists but is `null` or empty object `{}`

**Error format:**
```
❌ CDC section missing in config for {table_type} table '{table_name}'
   table_type: {table_type} (from intent_identification.json)
   Expected: "cdc" section with primary_key_cols populated
   Found: "cdc" key absent from config file
   Fix: Re-run /gen-config — ensure CDC block is included for NonTransactional tables
```

### Check 2 — Primary Key Cols Non-Empty (BLOCKING for NonTransactional_SCD1 and NonTransactional_SCD2)

Read `config["cdc"]["primary_key_cols"]` → verify it is a non-empty array.

**BLOCK** if:
- `primary_key_cols` is `[]` (empty array) AND mapping has columns with `key_column: true`
- `primary_key_cols` is missing from the CDC object

**Error format:**
```
❌ CDC primary_key_cols is empty for {table_type} table '{table_name}'
   Mapping specifies key columns: [{list of columns with key_column: true}]
   Config cdc.primary_key_cols: []
   Fix: Populate primary_key_cols from mapping key_column flags
```

### Check 3 — Primary Key Column Validity (WARNING)

For each column name in `config["cdc"]["primary_key_cols"]`:
1. Verify it exists in `mapping_parsed.json` → `columns[].target_column_name` for this table

**WARN** (non-blocking) if a CDC primary key column does not exist in the mapping target column list. This may indicate a typo or hallucinated column name.

### Check 4 — Transactional Table CDC Absence (WARNING)

If `table_type == "Transactional"` AND config contains a `"cdc"` section:
- **WARN** — CDC section is unusual for Transactional tables (append-only, no SCD2)
- Not blocking — some edge cases may legitimately have CDC for Transactional tables

### Check 5 — SCD1 CDC Section Contains Only Allowed Keys (BLOCKING for NonTransactional_SCD1)

If `table_type == "NonTransactional_SCD1"`, read `config["cdc"]` and enumerate all keys present.

**BLOCK** if:
- `config["cdc"]` contains `"high_ended_date"` key — SCD1 does not use high-end dating
- `config["cdc"]` contains `"snapshot_mode"` key — SCD1 does not use snapshot mode
- `config["cdc"]` contains any key other than `"primary_key_cols"` and `"exclude_cols"`

**Error format:**
```
❌ SCD1 CDC section contains disallowed key '{key}' for table '{table_name}'
   table_type: NonTransactional_SCD1 (from intent_identification.json)
   Allowed CDC keys for SCD1: primary_key_cols, exclude_cols
   Found disallowed key: {key}
   Fix: Remove '{key}' from cdc section — SCD1 uses simple upsert, not SCD2 temporal logic
```

### Check 6 — SCD1 Mesh/DDL Must Not Contain Temporal Columns (BLOCKING for NonTransactional_SCD1)

If `table_type == "NonTransactional_SCD1"`, read the corresponding mesh JSON or DDL file.

**BLOCK** if:
- Mesh/DDL contains column `eff_start_date`
- Mesh/DDL contains column `eff_end_date`
- Mesh/DDL contains column `active`

**Error format:**
```
❌ SCD1 mesh/DDL contains SCD2 temporal column '{col}' for table '{table_name}'
   table_type: NonTransactional_SCD1 (from intent_identification.json)
   SCD1 audit columns: dw_lod_tmp, dw_upd_lod_tmp only
   Found SCD2 column: {col}
   Fix: Remove '{col}' from mesh/DDL — SCD1 tables do not track temporal history
```

### Check 7 — SCD1 Partition Must Not Be "active" (BLOCKING for NonTransactional_SCD1)

If `table_type == "NonTransactional_SCD1"`, read `intent_identification.json` → `partition_key_columns` for this table.

**BLOCK** if:
- `partition_key_columns` contains `"active"` — SCD1 tables have no `active` column

**Error format:**
```
❌ SCD1 table '{table_name}' is partitioned by 'active' which does not exist for SCD1
   table_type: NonTransactional_SCD1 (from intent_identification.json)
   SCD1 tables have no 'active' column — cannot partition by it
   Fix: Change partition to a valid business column or remove partitioning
```

### Check 8 — Rolling Deletion Must Not Be Present on SCD2 Tables (BLOCKING for NonTransactional_SCD2)

If `table_type == "NonTransactional_SCD2"`, read the generated config file and check for a `rolling_deletion` section.

**BLOCK** if:
- `table_type == "NonTransactional_SCD2"` AND config contains a `rolling_deletion` section (regardless of `enabled` value)

SCD2 tables maintain full history via soft-expire (`active='0'`) — physical deletion would destroy the audit trail and break downstream consumers that query historical state.

**Pass**: `rolling_deletion` section absent (or `table_type` is NOT `NonTransactional_SCD2`)
**Fail**: `rolling_deletion` section present AND `table_type` is `NonTransactional_SCD2`

**Error format:**
```
❌ Rolling deletion present in config for SCD2 table '{table_name}'
   table_type: NonTransactional_SCD2 (from intent_identification.json)
   SCD2 maintains full history via soft-expire (active='0') — physical deletion is forbidden
   Found: rolling_deletion section in config
   Fix: Remove the rolling_deletion section from config — SCD2 tables must never physically delete historical records
```

---

## Known Exceptions (NOT flagged)

| Scenario | Reason |
|----------|--------|
| NonTransactional_SCD2 table with `snapshot_mode: true` and empty `exclude_cols` | Snapshot mode with no exclusions is valid |
| `exclude_cols` being empty | Empty exclude list is valid (all columns participate in CDC comparison) |
| `validate_unique_keys` being `false` or absent | Default is `false`; absence falls back to TargetWriter default. Only emitted when explicitly set via mapping Additional Context or domain knowledge |
| `duplicates_ts_col` being absent | Optional field — only emitted when specified in mapping Additional Context (`duplicates_ts_col:<col>`) or domain knowledge. Absence means no intraday dedup |
| `dedup_order` being absent | Optional field — only emitted when `duplicates_ts_col` is specified. Absence falls back to TargetWriter default (`"desc"`) |
| NonTransactional_SCD1 table with only `primary_key_cols` + `exclude_cols` in CDC | SCD1 minimal CDC section is by design |

---

## Integration Points

| Integration | When | Behavior |
|---|---|---|
| `/gen-config` STEP FINAL | After config file generation | Run assertion → BLOCK if NonTransactional_SCD1 or NonTransactional_SCD2 without CDC |
| `/validate` Batch 4 | During consistency validation | Run assertion → report findings |
| `/push` gate | Before push/commit | Refuse if `cdc_assertion_result != "passed"` |

---

## Session State Fields

| Field | Type | Set By | Values |
|---|---|---|---|
| `cdc_assertion_result` | string | STEP FINAL | `"passed"`, `"failed"`, `"skipped_transactional"`, `"passed_scd1"` |
| `cdc_assertion_failures` | array\|null | STEP FINAL | Array of assertion failure objects, or null if passed |

---

## Pass Condition

Every NonTransactional_SCD1 and NonTransactional_SCD2 target table has a config with a populated CDC section containing non-empty `primary_key_cols`. Every entry in `primary_key_cols` traces to a valid target column. For NonTransactional_SCD1 tables, the CDC section contains ONLY `primary_key_cols` + `exclude_cols` (no `high_ended_date`, `snapshot_mode`, or other SCD2-specific keys), and the mesh/DDL does not contain `eff_start_date`, `eff_end_date`, or `active` columns. No NonTransactional_SCD2 table has a `rolling_deletion` section in its config.
