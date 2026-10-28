# Validator: contract-reconciliation-validator

**Purpose**: Verify that generated Glue artefacts (wrapper, transform, config) respect the runtime API contracts of the generic components (`reader.py`, `writer.py`, `date_control.py`). Catches cross-artefact mismatches that compile successfully but crash or produce wrong results at runtime.

**Severity**: BLOCK on contract violations (runtime data correctness).

**Platform**: Glue only. Databricks has equivalent coverage via `foundation-library-validator` and `databricks-validation-agent` rules R6/R12/R19.

---

## Prerequisites

- At least one wrapper generated (`generated/glue/wrapper/{db}_{table}_wrapper.py`)
- At least one transform generated (`generated/glue/transforms/{db}_{table}_transform_day*.py`)
- Config generated (`generated/glue/wrapper/{db}_{table}_config.json`)
- Generic component templates accessible at `${CLAUDE_PLUGIN_ROOT}/templates/glue/generic_components/`
- `session/mapping_parsed.json` exists
- `session/intent_identification.json` exists

---

## Invocation

- **Primary**: Called inline by `/gen-wrapper` STEP FINAL.1 (runs after syntax check)
- **Secondary**: Called by `/validate` Batch 4 (runs as part of full validation suite)
- **Gate**: `/push` refuses if `session_state.contract_reconciliation_result != "passed"`

---

## Boundary Map

This validator covers 12 of 13 runtime contract boundaries between generic components and generated artefacts. Boundary B12 (config filter keys → SourceReader) is covered by the existing `transform-config-contract.md`.

| # | Boundary | Check |
|---|----------|-------|
| B1 | Wrapper → `retrieve_date()` return shape | C1 |
| B2 | Wrapper → `date_control(config)` required keys | C7 |
| B3 | `_DateControlLogic` → `int(config[])` empty string | C2 |
| B4 | Transform → `SourceReader()` constructor kwargs | C5 |
| B5 | Transform → `TargetWriter()` constructor kwargs | C5 |
| B6 | Writer `_add_audit_columns` active type | C3 |
| B7 | Writer SQL MERGE active literal type | C3 |
| B8 | Day1 Non-Tx output → Writer expectation (no audit cols) | C4 |
| B9 | Day0 output → Writer expectation (all audit cols present) | C4 |
| B10 | Wrapper `common_args` → Transform constructor kwargs | C5 |
| B11 | Config `cdc.primary_key_cols` → Writer requirement | C6 |
| B13 | Config `date_control` section completeness | C7 |

---

## Checks

### Check C1 — API Return Shape (BLOCKING)

Verify that call sites in the generated wrapper correctly unpack the return value of `date_control.retrieve_date()`.

**Method:**
1. Read `date_control.py` → locate `def retrieve_date(self)` → count comma-separated items in the `return` statement (expected: 3-tuple)
2. Read generated wrapper `.py` → locate assignment from `dc.retrieve_date()` or `date_control(...).retrieve_date()`
3. Count LHS variables: if single variable (no tuple unpacking), flag as violation

**BLOCK** if the generated wrapper assigns `retrieve_date()` to a single variable instead of unpacking the 3-tuple.

**Error format:**
```
❌ Contract violation C1: retrieve_date() returns 3-tuple but wrapper assigns to single variable (line 99)
   Expected: _prev, current_business_date, _next = dc.retrieve_date()
   Found:    current_business_date = dc.retrieve_date()
```

### Check C2 — Config Value Safety (BLOCKING)

Verify that config values consumed by `int()` or `float()` in generic component constructors are non-empty when the config's frequency requires them.

**Method:**
1. Read generated config JSON → extract `date_control.frequency`
2. Read generated config JSON → extract `date_control.workday_number_monthly` and `date_control.workday_number_weekly`
3. If `frequency` is `once_a_month` and `workday_number_monthly` is `""` or missing → BLOCK
4. If `frequency` is `weekly_once` and `workday_number_weekly` is `""` or missing → BLOCK
5. For other frequencies (`daily`, `working_days`, `alternate_days`, `tue_to_sat`), empty values are acceptable (guarded by code)

**BLOCK** if a frequency-required workday_number field is empty or missing.

**Error format:**
```
❌ Contract violation C2: frequency='once_a_month' but workday_number_monthly='' in config
   date_control.py will crash: int('') → ValueError
   Fix: Set workday_number_monthly to a valid integer (1-based day of month)
```

### Check C3 — Audit Column Type Alignment (BLOCKING)

Verify that `active` column literals are consistent across writer SQL MERGE statements and transform `F.lit()` calls.

**Method:**
1. Read `writer.py` → extract literal values compared to `{_ACTIVE_COL}` in SQL MERGE (e.g., `= '1'`, `= '0'`)
2. Read generated transform `.py` → extract `F.lit()` values for the `active` column (via `.alias('active')` or `.withColumn('active', ...)` context)
3. Compare: both must use the same type (string `'1'`/`'0'` or integer `1`/`0`)

**BLOCK** if transform uses integer `F.lit(1)` but writer SQL expects `= '1'` (string), or vice versa.

**Error format:**
```
❌ Contract violation C3: active column type mismatch
   Writer SQL MERGE uses: active = '1' (string comparison)
   Transform uses: F.lit(1).cast('int') (integer)
   Fix: Use F.lit('1').cast('string') in transform to match writer
```

### Check C4 — Day0/Day1 Audit Column Contract (BLOCKING)

Verify that the generated transform's output DataFrame contains the correct set of audit columns for its operation type and table type.

**Method:**
1. Read `session/intent_identification.json` → determine `table_type` and `load_type` for each target table
2. For each generated **Day1 Non-Transactional** transform:
   - Scan the final output (`.select()` or returned DataFrame) for audit column names: `eff_start_date`, `eff_end_date`, `active`, `dw_lod_tmp`, `dw_upd_lod_tmp`
   - **BLOCK** if any of `eff_start_date`, `eff_end_date`, `active` are present — TargetWriter derives these via CDC merge; including them causes column collision
   - `dw_lod_tmp`, `dw_upd_lod_tmp` should NOT be present either (writer handles), but only WARN (non-blocking) since some pipelines set them pre-write
3. For each generated **Day0 Non-Transactional** transform:
   - Scan the final output for all five audit columns
   - **BLOCK** if any of the five are missing — Day0 writer writes the DataFrame as-is without injecting audit columns
4. For each generated **Day0/Day1 Transactional** transform:
   - Verify `dw_bus_dt` is present in the output (TargetWriter uses it as partition column)
   - `dw_lod_tmp` should be present for Day0 (writer writes as-is)
   - **BLOCK** if `dw_bus_dt` is missing

**Error format:**
```
❌ Contract violation C4: Day1 NonTransactional_SCD2 transform includes audit columns
   Found in final .select(): eff_start_date, eff_end_date, active
   Writer derives these via CDC merge — including them causes column collision
   Fix: Remove eff_start_date, eff_end_date, active from Day1 transform output
```

### Check C5 — Constructor Signature Alignment (BLOCKING)

Verify that generated code passes the correct keyword arguments to generic component constructors.

**Method:**
1. Read `reader.py` → extract `SourceReader.__init__` required kwargs: `spark`, `glue_read_table`, `glue_read_icb_table`, `config`, `param`, `current_business_date`
2. Read `writer.py` → extract `TargetWriter.__init__` required kwargs: `spark`, `config`, `param`, `current_business_date`, `primary_key_cols` (+ optional: `partition_col`, `cdc_exclude_cols`, `snapshot_mode`)
3. Read transform template → extract constructor kwargs: `spark`, `config`, `param`, `current_business_date`, `glue_read_table`, `glue_read_icb_table`
4. For each generated transform `.py`:
   - Extract kwargs in `SourceReader(...)` call → verify all required kwargs present
   - Extract kwargs in `TargetWriter(...)` call → verify all required kwargs present
5. For each generated wrapper `.py`:
   - Extract kwargs in `common_args` dict or transform constructor call → verify match

**BLOCK** if any required keyword argument is missing or misspelled.

**Error format:**
```
❌ Contract violation C5: TargetWriter() missing required kwarg 'primary_key_cols'
   Location: fdp_uk_mortgage_db_account_wm_transform_day0.py (line 77)
   TargetWriter.__init__ requires: spark, config, param, current_business_date, primary_key_cols
   Fix: Add primary_key_cols=config.get("cdc", {}).get("primary_key_cols", []) to TargetWriter()
```

### Check C6 — Config CDC → Writer Contract (BLOCKING)

Verify that config's CDC section provides valid primary key columns that exist in the transform output.

**Method:**
1. Read generated config JSON → extract `cdc.primary_key_cols`
2. **BLOCK** if `primary_key_cols` is empty or missing (TargetWriter raises `ValueError` at line 136-137)
3. Read generated transform `.py` → extract final output column names from `.select()` or `.alias()` calls
4. For each column in `primary_key_cols`: verify it appears in the transform output column set
5. **BLOCK** if any PK column is absent from the transform output

**Error format:**
```
❌ Contract violation C6: cdc.primary_key_cols contains 'account_id' but transform output does not
   Config: cdc.primary_key_cols = ["account_id", "effective_date"]
   Transform output columns: [customer_id, account_type, balance, ...]
   Fix: Ensure transform includes all primary key columns in final .select()
```

### Check C7 — Config date_control Completeness (BLOCKING)

Verify that the generated config's `date_control` section contains all keys required by `date_control.__init__` and `_DateControlLogic.__init__`.

**Method:**
1. Read generated config JSON → extract `date_control` section
2. Required keys: `filename`, `file_path`, `frequency`, `backup_filename`, `run_on_weekends`, `run_on_bank_holidays`, `workday_number_monthly`, `workday_number_weekly`
3. **BLOCK** if any required key is missing from the config

**Error format:**
```
❌ Contract violation C7: date_control section missing required key 'backup_filename'
   Required keys: filename, file_path, frequency, backup_filename, run_on_weekends,
                  run_on_bank_holidays, workday_number_monthly, workday_number_weekly
   Fix: Add 'backup_filename' to config.json date_control section
```

### Check C8 — Rolling Deletion API Contract (WARNING)

**When**: `rolling_deletion` section present in generated config.

Validate the contract between config and TargetWriter:

**Method:**
1. Config provides `rolling_deletion.predicate` (string) and `rolling_deletion.enabled` (boolean)
2. `TargetWriter._rolling_delete()` reads `config.get('rolling_deletion', {})` and checks `enabled`
3. TargetWriter interpolates `{current_business_date}` in the predicate using `self.current_business_date.isoformat()` (Glue) or `self.curr_bus_dt` (Databricks)
4. The DELETE statement is: `DELETE FROM {target_table} WHERE {interpolated_predicate}`
5. `_rolling_delete()` is called at the end of `write()` — after the main write strategy succeeds
6. For SCD2 tables, `_rolling_delete()` returns immediately without executing any SQL

**WARN** if:
- Config contains `rolling_deletion` section but the generated wrapper/transform does not pass `config` to `TargetWriter` (contract cannot be fulfilled)
- `rolling_deletion.predicate` contains `{current_business_date}` but the TargetWriter constructor does not receive `current_business_date` kwarg (interpolation will fail)

**Error format:**
```
⚠️ Contract violation C8: rolling_deletion API contract mismatch
   Config provides rolling_deletion section but TargetWriter may not fulfil the contract
   {specific mismatch description}
   Fix: Ensure TargetWriter receives config with rolling_deletion and has access to current_business_date for predicate interpolation
```

---

## Known Exceptions (NOT flagged as violations)

| Category | Examples | Reason |
|----------|----------|--------|
| **Day0 audit columns in Non-Tx transforms** | `eff_start_date`, `eff_end_date`, `active`, `dw_lod_tmp`, `dw_upd_lod_tmp` | Required — Day0 writer writes DataFrame as-is |
| **Day1 `dw_bus_dt` in Transactional transforms** | `dw_bus_dt` column present | Required — used as partition column by TargetWriter |
| **Empty workday_number for DAILY frequency** | `workday_number_monthly: ""` | Acceptable — field not used for daily scheduling |
| **Optional TargetWriter kwargs** | `partition_col`, `cdc_exclude_cols`, `snapshot_mode` absent | These have defaults in the constructor |

---

## Self-Heal Retry Logic

When violations are found during `/gen-wrapper` STEP FINAL.1:

1. **First attempt**: Re-invoke the responsible agent (wrapper agent for C1/C5/C7; transform agent for C3/C4/C5/C6) with:
   - Violation list (specific files, lines, expected vs actual)
   - Fix guidance from the error format above
   - Relevant config/mapping excerpt
2. **Second attempt**: Same as above if violations persist.
3. **After 2 retries**: Mark affected files as `DRAFT_UNVALIDATED`. Set `session_state.contract_reconciliation_result = "failed"`.

The retry agent gets a **fresh context** containing:
- Violation list (~200 tokens)
- Affected file(s) to fix (read from disk)
- Generic component constructor signatures (reference)

---

## Integration Points

| Integration | When | Behavior |
|---|---|---|
| `/gen-wrapper` STEP FINAL.1 | After syntax check passes | Run all 8 checks → self-heal retry if violations |
| `/validate` Batch 4 | During full validation suite | Run all 8 checks → report findings (no retry here) |
| `/push` gate | Before push/commit | Refuse if `contract_reconciliation_result != "passed"` |

---

## Session State Fields

| Field | Type | Set By | Values |
|---|---|---|---|
| `contract_reconciliation_result` | string | STEP FINAL.1 | `"passed"`, `"failed"`, `"skipped"` |
| `contract_reconciliation_violations` | array\|null | STEP FINAL.1 | Array of violation objects, or null if passed |
| `contract_reconciliation_retries` | number | STEP FINAL.1 | 0, 1, or 2 |

---

## Pass Condition

All 8 checks pass across all generated wrapper, transform, and config files for the session. Zero violations for all target tables.
