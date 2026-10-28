# Validator: Template Landmark Preservation

**Purpose**: Verify that template rendering preserved all structural markers — the generated file must retain the skeleton defined by the source template. Catches cases where an agent generates from prose description instead of rendering the template.

**Severity**: DRAFT_UNVALIDATED if any landmark missing. Output is rejected and agent must re-run with explicit error pointing to the divergence.

**Platform**: Glue + Databricks

**Trigger**: After every `/gen-*` command completes, for each generated file.

---

## Design Principle

Each template defines structural "landmarks" — function signatures, required keys, import patterns, SQL clauses — that MUST survive rendering. If a landmark is missing, the file was likely generated from description rather than the template.

This validator does NOT check:
- Placeholder resolution (handled by `placeholder-completeness-validator`)
- Schema validity (handled by file-type-specific validators)
- Code correctness (handled by `code-review-agent`)

It ONLY checks: "Did the output come from the template?"

---

## Landmark Definitions (per file type)

### wrapper.py (Glue)

Template source: `${CLAUDE_PLUGIN_ROOT}/templates/glue/wrapper_py_per_table.template.py`

| # | Landmark (substring or pattern) | Rationale |
|---|---|---|
| 1 | `def main(env, business_date, param):` | Template function signature |
| 2 | `from generic_components.date_control import` | Required import from template |
| 3 | `operation = param.split(',')[0].strip()` | Param parsing — template-defined logic |
| 4 | `dc.update_date_control()` | Date control update on success |
| 5 | `_transform_day` (regex: `from .+_transform_day[01] import`) | Transform class import |
| 6 | `transform.run()` | Transform invocation |
| 7 | `_catch_up_threshold` (regex: `_catch_up_threshold\s*=\s*config.get`) | Catch-up threshold detection |
| 8 | `_source_operation_override` | Catch-up mode signal emission |

**Pass**: All 8 landmarks present. **Fail**: Any missing.

### config.json (Glue — single or multiple data flow)

Template source: `${CLAUDE_PLUGIN_ROOT}/templates/glue/config_single_data_flow.template.json` or `${CLAUDE_PLUGIN_ROOT}/templates/glue/config_multiple_data_flow.template.json`

| # | Landmark (JSON key existence) | Rationale |
|---|---|---|
| 1 | Top-level key `"database"` | Template-defined structure |
| 2 | Top-level key `"tablename"` | Template-defined structure |
| 3 | Top-level key `"source"` | Source grouping structure |
| 4 | Nested key `"source"` → `"non-transactional"` or `"transactional"` | Type classification structure |
| 5 | Top-level key `"filters"` | Filter structure |
| 6 | Top-level key `"file_locations"` with nested `"staging"` | File location structure |
| 7 | Top-level key `"date_control"` with nested `"filename"` | Date control structure |
| 8 | Top-level key `"cdc"` with nested `"primary_key_cols"` | CDC configuration structure |

**Pass**: All 8 landmarks present. **Fail**: Any missing.

### mesh.json (Glue)

Template source: `${CLAUDE_PLUGIN_ROOT}/templates/glue/mesh_json.template.json`

| # | Landmark (JSON key/value) | Rationale |
|---|---|---|
| 1 | `"owner"` with nested `"itbs": "BSN0004626"` | Hardcoded ITBS from template |
| 2 | `"owner"."groups"` array with exactly 4 entries | BTB maint + orig, RTB maint + orig |
| 3 | `"storageMediumLinks"[0]."storageMediumDefinition": "aws_data_catalog"` | Template constant |
| 4 | `"aspects"[0]."schema"."schemaType": "FLATTENED"` | Template constant |
| 5 | `"aspects"[0]."storageMediumProperties"."consumption"` array with entry named `"baselocation"` | Template structure |
| 6 | `"environmentProperties"` array with entry named `"s3_bucket"` | Template structure |
| 7 | `"labels"` array with entry named `"businessdate"` | Template constant |
| 8 | `"versionPolicy": "NO_CONSTRAINT"` | Template constant |

**Pass**: All 8 landmarks present. **Fail**: Any missing.

### transform_day0.py / transform_day1.py (Glue)

Template source: `${CLAUDE_PLUGIN_ROOT}/templates/glue/transform_day0.template.py` / `${CLAUDE_PLUGIN_ROOT}/templates/glue/transform_day1.template.py`

| # | Landmark (substring or pattern) | Rationale |
|---|---|---|
| 1 | `class ` + `_transform_day` (regex: `class .+_transform_day[01]`) | Template class name pattern |
| 2 | `def __init__(self` | Constructor signature |
| 3 | `def run(self` | Entry point method |
| 4 | `from generic_components.reader import SourceReader` | Template import |
| 5 | `from generic_components.writer import TargetWriter` | Template import |

**Pass**: All 5 landmarks present. **Fail**: Any missing.

### transform.py (Databricks — day0 or day1)

Template source: `${CLAUDE_PLUGIN_ROOT}/templates/databricks/transform_day0.template.py` or `transform_day1.template.py`

| # | Landmark (substring or pattern) | Rationale |
|---|---|---|
| 1 | `# Databricks notebook source` | Notebook format header |
| 2 | `class {{target_schema}}_{{table_name}}_transform` | Class-based transform pattern |
| 3 | `def prepare_sources(self)` | Source reading method |
| 4 | `def transformation(self)` | Transform method signature |
| 5 | `def run(self)` | Orchestration method |
| 6 | `self.reader = SourceReader(` | Config-driven reader instantiation |
| 7 | `self.writer = TargetWriter(` | Config-driven writer instantiation |

**Pass**: All 5 landmarks present. **Fail**: Any missing.

### driver.py (Databricks)

Template source: `${CLAUDE_PLUGIN_ROOT}/templates/databricks/driver.template.py`

| # | Landmark (substring or pattern) | Rationale |
|---|---|---|
| 1 | `dbutils.widgets.text("environment"` | Environment widget — DABs deployment target |
| 2 | `dbutils.widgets.text("business_date"` | Business date widget — Airflow override |
| 3 | `# MAGIC %run ./` (regex: `# MAGIC %run \./.*_transform`) | Transform class loaded via notebook %run, not import |
| 4 | `from databricks_foundation.core.date_control import DateControl` | Foundation library import (full submodule path) |
| 5 | `DateControl` | Date control initialization and usage |
| 6 | `transform.run()` | Transform execution invocation |
| 7 | `_catch_up_threshold` (regex: `_catch_up_threshold\s*=\s*config.get`) | Catch-up threshold detection |
| 8 | `_source_operation_override` | Catch-up mode signal emission |

**Pass**: All 8 landmarks present. **Fail**: Any missing.

### table_creation_utility.py — DDL Section (Databricks)

Template source: `${CLAUDE_PLUGIN_ROOT}/templates/databricks/iceberg_ddl.template.sql` (DDL embedded in `table_creation_utility.template.py`)

| # | Landmark (substring, case-insensitive) | Rationale |
|---|---|---|
| 1 | `CREATE TABLE IF NOT EXISTS` | Template DDL pattern (at least one per target table) |
| 2 | `USING iceberg` | Iceberg format clause |
| 3 | `PARTITIONED BY` | Partition clause |
| 4 | `ddl_statements` | Accumulator list variable |

**Pass**: All 4 landmarks present. **Fail**: Any missing.

> **Note**: DDL is embedded in `generated/databricks/src/Notebooks/utilities/{target_schema}_table_creation_utility.py`. No standalone `.sql` files are generated.

### dtxog.json (Glue)

Template source: `${CLAUDE_PLUGIN_ROOT}/templates/glue/dtxog_config_byoc*.template.json`

| # | Landmark (JSON key) | Rationale |
|---|---|---|
| 1 | Top-level key `"metadata"` | Template structure |
| 2 | Top-level key `"services"` (sibling of metadata) | Service flag block |
| 3 | Top-level key `"dtxog-byoc"` | BYOC config block |
| 4 | `"dtxog-byoc"."app_details"."env"` with `"dev"`, `"uat"`, `"prd"` | Environment config |
| 5 | `"sparkConf"` nested under `glue_args.xtra-args` | Spark configuration string |
| 6 | `"byoc"."wrapper-file"` in each env | Wrapper file S3 paths |
| 7 | `"byoc"."package-cnfg"` in each env | Config.json S3 path |

**Pass**: All 7 landmarks present. **Fail**: Any missing.

---

## Execution Logic

```
FOR each generated_file in generated/:
  1. Identify file type from extension + naming pattern
  2. Load landmark definitions for that file type (table above)
  3. FOR each landmark:
     - Check if substring/regex/key exists in file content
     - If missing → record in failures[]
  4. IF failures is empty → PASS (mark VALIDATED for this check)
  5. IF failures is non-empty:
     - Mark artefact as DRAFT_UNVALIDATED
     - Emit error with:
       - File name
       - Missing landmarks (list)
       - Template source path (for re-read)
       - Instruction: "Re-run generation with STEP 0.5 template read enforced"
```

---

## Fail Action

When landmarks are missing:

```
LANDMARK VALIDATION FAILED for: {filename}

Missing structural markers:
  - [{landmark_number}] "{landmark_description}" — NOT FOUND

This indicates the file was generated from description/memory instead of the template.

Expected template source: {template_path}

ACTION REQUIRED:
  1. Agent MUST re-read the template file (STEP 0.5)
  2. Re-generate the file by substituting placeholders into the template
  3. Do NOT invent structure — the template defines the skeleton

Status: DRAFT_UNVALIDATED (blocked until landmarks pass)
```

---

## Integration

Invoked by `hooks/post-generate-validate.hook.md` after schema validation (Step 1b).

**Routing table entry:**

| Generated File Pattern | Validator | Severity |
|---|---|---|
| `generated/glue/wrapper/*_wrapper.py` | template-landmark-preservation-validator (wrapper.py) | DRAFT_UNVALIDATED |
| `generated/glue/wrapper/*_config.json` | template-landmark-preservation-validator (config.json) | DRAFT_UNVALIDATED |
| `generated/glue/mesh/*_mesh.json` | template-landmark-preservation-validator (mesh.json) | DRAFT_UNVALIDATED |
| `generated/glue/transforms/*_transform_day0.py`, `*_transform_day1.py` | template-landmark-preservation-validator (transform) | DRAFT_UNVALIDATED |
| `generated/databricks/src/Notebooks/{day0\|day1}/{target_schema}_{table}/*_transform.py` | template-landmark-preservation-validator (transform-dbx) | DRAFT_UNVALIDATED |
| `generated/databricks/src/Notebooks/{day0\|day1}/{target_schema}_{table}/*_driver.py` | template-landmark-preservation-validator (driver) | DRAFT_UNVALIDATED |
| `generated/databricks/src/Notebooks/{day0\|day1}/{target_schema}_{table}/*_config.yml` | template-landmark-preservation-validator (config.yml) | DRAFT_UNVALIDATED |
| `generated/databricks/src/Notebooks/utilities/{target_schema}_table_creation_utility.py` | template-landmark-preservation-validator (DDL utility) | DRAFT_UNVALIDATED |
| `generated/glue/dtxog/*_dtxog.json` | template-landmark-preservation-validator (dtxog) | DRAFT_UNVALIDATED |
