# Validator: python-import-validator

**Purpose**: Validate that traditional Python `import`/`from ... import` statements in Databricks notebooks use correct PySpark patterns and do not include wrong-platform libraries (AWS Glue, boto3).

**Severity**: HALT for disallowed platform imports; Flag for style anti-patterns — disallowed imports stop generation; style issues are advisory.

**Platform**: Glue + Databricks

**Scope Note**: This validator checks only `import` and `from ... import` statements. It does NOT validate `# MAGIC %run` statements — those are covered by `foundation-library-validator`.

---

## Validation Logic

### Check 1 — Disallowed Platform Imports (HALT)

Databricks notebooks must NOT import AWS/Glue-specific libraries. These indicate wrong-platform code generation.

**Blocked import patterns:**
| Import Pattern | Reason |
|---|---|
| `import boto3` / `from boto3` | AWS SDK — not applicable in Databricks |
| `import awsglue` / `from awsglue` | AWS Glue library — wrong platform |
| `from awsglue.context import GlueContext` | Glue-specific context |
| `from awsglue.job import Job` | Glue job wrapper |
| `from awsglue.transforms import *` | Glue transforms |
| `from generic_components.reader import` | DTX Glue framework reader |
| `from generic_components.writer import` | DTX Glue framework writer |
| `from generic_components.date_control import` | DTX Glue framework date control |
| `from generic_components.helpers import` | DTX Glue framework helpers |

**Rules:**
1. Scan all `.py` files under `generated/databricks/`
2. For each `import` or `from ... import` line, check against blocked patterns
3. HALT if any blocked import is found — indicates platform confusion in generation
4. No exceptions — these libraries are never valid in Databricks notebooks

**Anti-patterns (HALT):**
```python
# ❌ AWS Glue library in Databricks notebook
from awsglue.context import GlueContext
from awsglue.job import Job

# ❌ DTX framework (Glue-specific) in Databricks notebook
from generic_components.reader import glue_read_table
from generic_components.writer import glue_write_table

# ❌ boto3 in Databricks (use dbutils.secrets for credentials)
import boto3
```

### Check 2 — Valid PySpark Import Syntax (Flag)

Flag import patterns that deviate from Databricks best practices. These don't block generation but should be corrected before deployment.

**Allowed import patterns:**

| Category | Allowed Patterns |
|---|---|
| PySpark Core | `from pyspark.sql import DataFrame, SparkSession` |
| PySpark Functions | `import pyspark.sql.functions as F` |
| PySpark Types | `from pyspark.sql.types import StructType, StructField, StringType, ...` *(conditional)* |
| PySpark Window | `from pyspark.sql.window import Window` *(conditional)* |
| Standard Library | `import os`, `import sys`, `import logging`, `import yaml`, `from datetime import date, datetime` *(datetime conditional)* |
| Foundation | `from databricks_foundation.*` |
| Databricks Utils | `from databricks.sdk import *` (rare, advanced use) |

**Flagged patterns (WARNING — non-blocking):**

| Pattern | Issue | Suggestion |
|---|---|---|
| `from pyspark.sql.functions import *` | Wildcard pollutes namespace | Use `import pyspark.sql.functions as F` |
| `from pyspark.sql.functions import col, lit, when, ...` | Individual imports clutter | Use `as F` alias pattern |
| `import pyspark` (bare, without submodule) | Overly broad | Import specific submodules |
| `import pandas as pd` | Prefer PySpark-native for scale | Flag unless used for small reference data only |
| `__import__('...')` | Dynamic import is non-idiomatic | Use standard `from ... import` in the import block |

**Note on conditional imports**: Window, Types, and datetime imports are CONDITIONAL — present only when the generated transformation logic uses the imported symbols (populated via the `additional_imports` whitelist mechanism). The validator must NOT flag their absence as an error; only flag their presence when unused (lint warning, non-blocking).

**Rules:**
1. Scan all `import` / `from ... import` lines in generated `.py` files
2. Flag patterns from the warning table above
3. These are NON-BLOCKING — output as advisory warnings
4. `pandas` is flagged, not blocked, because small-scale reference lookups may justify it

### Check 3 — Dead Import Detection (WARNING)

Verify that conditional imports from the `additional_imports` whitelist are actually used in the file body. Dead imports indicate template composition left behind unused conditional blocks.

**Severity**: WARNING (non-blocking — advisory for code quality)

**Conditional imports to check:**

| Import Statement | Symbols to Search For |
|---|---|
| `from pyspark.sql.window import Window` | `Window.` or `Window(` |
| `from pyspark.sql.types import StructType, StructField, ...` | `StructType`, `StructField`, or any type class name |
| `from datetime import date, datetime` | `date(` or `datetime(` (Python constructors, NOT `F.current_date()`) |

**Algorithm:**

1. For each transform `.py` file in `generated/databricks/src/Notebooks/{day0,day1}/`:
   - Scan for conditional import lines (from the 3 patterns above)
   - For each found conditional import:
     - Extract the imported symbols
     - Search the rest of the file body (excluding the import line itself) for word-boundary usage of those symbols
     - If ZERO symbols from that import are used → flag as dead import
2. Report all dead imports found

**Rules:**
1. Use word-boundary matching to avoid false positives (e.g., `date` inside `update_date_control` is NOT a usage of `from datetime import date`)
2. Comments containing the symbol name do NOT count as usage
3. String literals containing the symbol name do NOT count as usage
4. Only flag imports from the conditional whitelist — standard imports (os, sys, logging, yaml, pyspark.sql.functions) are always valid

**Report format:**
```
⚠️ Dead import detected (unused conditional import):
   File: {filename}
   Import: "{import_statement}"
   Symbols checked: {symbol_list}
   None found in file body. This import can be removed.
```

---

## Pass Condition

No disallowed platform imports found. All `import` statements resolve to valid PySpark, standard library, or Databricks Foundation modules. (Style warnings may be present but do not affect pass status.)

## Fail Action

**For Check 1 (HALT):**
```
❌ Disallowed platform import detected:

  File: {filename}, Line {n}
  Import: "{import_statement}"
  Reason: {reason} — this library is not available in Databricks
  Fix: Remove this import. Use Databricks equivalents:
    - boto3 → dbutils.secrets.get() for credentials
    - awsglue → SparkSession (native in Databricks)
    - generic_components → SourceReader/TargetWriter via %run
```

**For Check 2 (Flag — advisory):**
```
⚠️ Import style warning:

  File: {filename}, Line {n}
  Import: "{import_statement}"
  Suggestion: {suggestion}
```
