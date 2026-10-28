# Validator: foundation-library-validator

**Purpose**: Validate that Databricks Foundation library is correctly imported and its APIs are used with the correct signatures in generated driver and transform notebooks.

**Severity**: HALT — generation stops until foundation library usage is corrected. Incorrect API calls cause runtime failures in Databricks cluster execution.

**Platform**: Databricks only

---

## Validation Logic

### Check 1 — Required Imports and %run Statements

**Driver notebook** must contain these foundation imports:
```python
from databricks_foundation.core.date_control import DateControl
from databricks_foundation.logger.audit_logger import AuditLogger
```

**Transform notebook** must load shared utilities via `%run` (Databricks notebook import mechanism), each in its own cell:
```python
# MAGIC %run {utilities_run_prefix}/utilities/source_reader

# COMMAND ----------

# MAGIC %run {utilities_run_prefix}/utilities/target_writer
```
Where `utilities_run_prefix` is `../..` (standard layout) or `../../..` (multi-source-system layout).

**Rules:**
1. Driver must import `DateControl` from `databricks_foundation.core.date_control`
2. Driver must import `AuditLogger` from `databricks_foundation.logger.audit_logger`
3. Transform must contain a `# MAGIC %run` line whose path ends with `/utilities/source_reader` (provides `SourceReader` class)
4. Transform must contain a `# MAGIC %run` line whose path ends with `/utilities/target_writer` (provides `TargetWriter` class)
5. `SourceReader` and `TargetWriter` must NOT be imported via `from`/`import` statements (they are injected by `%run`)
6. BLOCK if any required import/`%run` is missing

**Anti-patterns (BLOCK):**
```python
# ❌ Wrong — SourceReader comes from %run, not import
from databricks_foundation.io.source_reader import SourceReader

# ❌ Missing %run — SourceReader will be undefined
class my_transform:
    def __init__(self, spark, config, curr_bus_dt, audit=None):
        self.reader = SourceReader(...)  # NameError at runtime!
```

### Check 2 — Correct API Usage

**DateControl** (in driver):
```python
# Instantiation
dc = DateControl(spark)

# Business date retrieval — required parameters
dates = dc.get_business_dates(
    date_control_table=date_ctrl_table,
    process_name=process_name,
)

# Date control insert — required parameters
dc.insert_date_control_if_missing(
    table_nm=date_ctrl_table,
    tenancy_name=tenancy_name,
    process_name=process_name,
    data_product_type=dp_type,
    process_frequency=process_freq,
    curr_date=date.today(),
)

# Date control update on success
dc.update_date_control(table_nm=date_ctrl_table, process_name=process_name)
```

**AuditLogger** (in driver):
```python
# Instantiation — requires spark and audit_table_fqn
audit = AuditLogger(spark, audit_table_fqn=audit_table_fqn)
```

**SourceReader** (in transform):
```python
# Instantiation — required parameters
self.reader = SourceReader(
    spark       = spark,
    config      = config,
    operation   = self.operation,
    curr_bus_dt = curr_bus_dt,
)

# Read all source tables
self.source_data = self.reader.read_source_data()
```

**TargetWriter** (in transform):
```python
# Instantiation — required parameters
self.writer = TargetWriter(
    spark            = spark,
    config           = config,
    operation        = self.operation,
    table_type       = self.table_type,
    curr_bus_dt      = curr_bus_dt,
    primary_key_cols = config["cdc"]["primary_key_cols"],
    audit            = audit,
    cdc_exclude_cols = config["cdc"].get("exclude_cols", []),
)

# Write output
self.writer.write(transformed_df)
```

**Rules:**
1. `DateControl` must be instantiated with `spark` as first positional argument
2. `dc.get_business_dates()` must receive `date_control_table` and `process_name` keyword arguments
3. `AuditLogger` must receive `spark` and `audit_table_fqn` arguments
4. `SourceReader` must receive `spark`, `config`, `operation`, `curr_bus_dt`
5. `TargetWriter` must receive `spark`, `config`, `operation`, `table_type`, `curr_bus_dt`, `primary_key_cols`, `audit`
6. BLOCK if required parameters are missing from any foundation API call

### Check 3 — Error Handling

**Driver** must wrap transform execution in structured error handling:

```python
try:
    # ... transform instantiation and execution ...
    transform.run()
    # ... date control update ...
except Exception as exc:
    logger.exception("Driver failed | process=%s | error=%s", process_name, exc)
    raise
```

**Rules:**
1. Driver must have a `try/except` block wrapping `transform.run()` execution
2. The `except` block must call `logger.exception()` (not just `logger.error()` — exception captures traceback)
3. The `except` block must `raise` (re-raise the exception — don't swallow it)
4. Transform class must NOT have bare `except: pass` patterns that swallow errors silently
5. BLOCK if error handling structure is missing or swallows exceptions

**Anti-patterns (BLOCK):**
```python
# ❌ Swallows exception — pipeline appears successful when it failed
try:
    transform.run()
except Exception:
    pass

# ❌ Logs but doesn't re-raise — DABs job shows success despite failure
try:
    transform.run()
except Exception as exc:
    logger.error("Failed: %s", exc)
    # Missing: raise
```

### Check 4 — Utility File Existence (Target Verification)

Verify that the files referenced by `# MAGIC %run` statements in transform notebooks actually exist in the output directory. This catches cases where transforms were generated but the utility files were never copied.

**Pre-condition:** Platform is Databricks and at least one transform file exists.

**Rules:**
1. If any transform file contains a `# MAGIC %run` line ending with `/utilities/source_reader` (any depth prefix) → verify `generated/databricks/src/Notebooks/utilities/source_reader.py` exists
2. If any transform file contains a `# MAGIC %run` line ending with `/utilities/target_writer` (any depth prefix) → verify `generated/databricks/src/Notebooks/utilities/target_writer.py` exists
3. Each file must:
   - Exist (non-zero size)
   - Start with `# Databricks notebook source` (valid notebook format)
   - Contain the expected class definition (`class SourceReader` / `class TargetWriter`)
4. BLOCK if either referenced utility file is missing or malformed

**Anti-patterns (BLOCK):**
```
# ❌ source_reader.py missing — SourceReader undefined at runtime
generated/databricks/src/Notebooks/utilities/source_reader.py — FILE NOT FOUND

# ❌ target_writer.py empty — TargetWriter undefined at runtime
generated/databricks/src/Notebooks/utilities/target_writer.py — 0 bytes
```

**Fix guidance:**
```
Run /gen-transform (STEP 0.55) or /gen-bundle (STEP 6) to copy utility files from:
  ${CLAUDE_PLUGIN_ROOT}/templates/databricks/generic_components/source_reader.py
  ${CLAUDE_PLUGIN_ROOT}/templates/databricks/generic_components/target_writer.py
```

---

## Pass Condition

Driver imports `DateControl` and `AuditLogger` from foundation library. Transform loads utilities via `# MAGIC %run .../utilities/source_reader` and `target_writer` (each in its own cell, path depth varies by layout). All foundation APIs called with correct required parameters. Error handling present with `logger.exception()` and `raise`. Utility target files exist when referenced by transforms (Check 4).

## Fail Action

HALT. Output:
```
❌ Foundation library validation failed:

  [CHECK 1] Missing required import/utility:
    File: {filename}
    Missing: {import_or_run_statement}
    Fix: Add the required import. SourceReader/TargetWriter must use # MAGIC %run, not import.

  [CHECK 2] Incorrect API usage:
    File: {filename}, Line {n}
    Call: {api_call}
    Missing parameter(s): {param_list}
    Fix: Add required parameters. See template: templates/databricks/driver.template.py

  [CHECK 3] Error handling violation:
    File: {filename}, Line {n}
    Issue: {description}
    Fix: Wrap transform.run() in try/except with logger.exception() and raise.

  [CHECK 4] Utility file missing:
    Referenced by: {transform_file} (# MAGIC %run .../utilities/{utility_name})
    Expected at: generated/databricks/src/Notebooks/utilities/{utility_name}.py
    Status: {NOT FOUND | EMPTY | MISSING CLASS}
    Fix: Run /gen-transform (STEP 0.55) or /gen-bundle (STEP 6) to copy utility files.
```
