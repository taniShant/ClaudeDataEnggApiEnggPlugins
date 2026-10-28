---
description: "Cross-artefact boundary definitions preventing redundant code — specifies what SourceReader already handles (table reads, filtering, column pruning, Iceberg fallback, CSV/Parquet reads) so transforms don't duplicate it."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-07-08
---

# Component Responsibility Boundaries (Cross-Artefact Awareness)

**PURPOSE**: Prevent redundant, conflicting, or functionally incorrect code by understanding what each co-existing component already handles. The transform MUST NOT duplicate logic owned by other components. Read these boundaries BEFORE generating any transformation code.

## What SourceReader (reader.py) Already Handles — DO NOT Duplicate

| Responsibility | Detail | Transform MUST NOT |
|---|---|---|
| Source table reads | Reads all tables from `config['source']` by alias | Re-read source tables via `spark.read` or `glue_read_table` directly |
| Source filtering (partition + business) | Resolves ALL filters from `config['filters'][operation][table_type]` — both standard defaults (active='1', dw_bus_dt=date, eff_start_date<=date) AND alias-specific business filters (e.g., `status NOT IN (...)`) | Apply ANY filter that is declared in config — check the filter manifest (`session/generated_configs/{table}_filters.json`) before generating `.filter()` calls. Only post-join/cross-source/derived-column filters belong in transform. |
| Date column CASTs in filters | Auto-rewrites date comparisons to `CAST(col AS DATE)` | Duplicate date CASTs on filter predicates already handled by reader |
| Column pruning on read | Selects only `config['source'][type][alias]['columns']` if specified | Re-select source columns that reader already pruned |
| Iceberg fallback | Retries with `glue_read_icb_table` on Iceberg metadata errors | Implement Iceberg fallback logic in transform |
| S3 CSV reads | `reader.read_csv(path)` for reference/lookup files | Read S3 CSV files directly via `spark.read.csv()` |
| Parquet file reads | `reader.read_parquet(path)` for file-based sources declared in config `source.file` section | Read parquet files directly via `spark.read.parquet()` |

**Transform accesses sources via**: `self.source_data = self.reader.read_source_data()` → dict keyed by alias. Each value is a pre-filtered, column-pruned DataFrame ready for business logic.

> **Authoritative API**: Read `${CLAUDE_PLUGIN_ROOT}/templates/{platform}/generic_components/source_reader.py` (or `reader.py` for Glue) in GATHER phase for exact constructor signature and public methods.

## What TargetWriter (writer.py) Already Handles — DO NOT Duplicate

| Responsibility | Detail | Transform MUST NOT |
|---|---|---|
| SCD2 CDC merge (Day 1 NonTransactional) | Three-phase merge: Phase 0 expire missing (snapshot_mode only) → Phase 1 expire changed → Phase 2 insert new/changed | Implement MERGE INTO or expire/insert logic |
| Snapshot mode expiry (Phase 0) | When `snapshot_mode=true`, expires active target rows whose PK is absent from source (absence = deletion at source) | Implement missing-record detection or expiry logic |
| Audit column injection (Day 1) | Derives eff_start_date, eff_end_date, active, dw_lod_tmp, dw_upd_lod_tmp | Include audit columns in Day 1 transform output |
| dw_lod_tmp injection (Day 1 Transactional) | Appends `dw_lod_tmp = current_timestamp()` before write | Derive dw_lod_tmp in Day 1 Transactional transforms |
| Change detection hash | SHA2(CONCAT_WS) over CDC-eligible columns (excludes PK, audit cols, cdc_exclude_cols) | Implement hash comparison logic |
| PK deduplication before merge | `dropDuplicates(primary_key_cols)` on source before CDC | Deduplicate on PKs before calling `writer.write()` (unless domain knowledge requires custom dedup ORDER BY) |
| Target FQN resolution | `config['database'] + '.' + config['tablename']` | Hardcode target table names |
| Write dispatch | Routes to overwrite/merge/partition-overwrite by table_type + operation | Implement write mode selection logic |
| Parquet file writes | `writer.write_parquet(df, path, mode, partition_by, compression)` for file targets declared in config `target_io` section. Dispatched automatically by `write()` when `target_io` is present. | Write parquet files directly via `df.write.parquet()` |

> **Authoritative API**: Read `${CLAUDE_PLUGIN_ROOT}/templates/{platform}/generic_components/target_writer.py` (or `writer.py` for Glue) in GATHER phase for exact constructor signature and public methods.

**Transform's Day 0 responsibility (NonTransactional)**: Generate a UNIFIED
  transformation that produces all columns (business + audit) together:
  - Business columns: logic from mapping transformation_logic
  - eff_start_date, eff_end_date: logic from domain knowledge temporal_stitching
    section or mapping transformation_logic (team-specific pattern — may be
    structurally inseparable from business column derivation in patterns C/D)
  - active: ALWAYS '1' if eff_end_date='3499-12-31', '0' otherwise (universal)
  - dw_lod_tmp, dw_upd_lod_tmp: always current_timestamp()
  Writer writes Day 0 DataFrame as-is (no injection).

**Transform's Day 0 responsibility (Transactional)**: unchanged — derive dw_bus_dt + dw_lod_tmp. Writer writes as-is.

**Transform's Day 1 responsibility**: unchanged — output ONLY business columns (+ dw_bus_dt for Transactional partition). Writer handles all audit columns and CDC logic.

**Domain Knowledge Override Exception**: If `domain_knowledge_text` contains explicit, unambiguous instructions to override TargetWriter's default CDC or write-to-target behaviour (e.g., custom merge logic, custom write strategy, non-standard SCD implementation), those instructions take precedence. In that case, the transform MAY implement custom write/CDC logic directly instead of delegating to `writer.write()`. This is signalled via `custom_write_strategy` in `intent_identification.json`. Only applies when domain knowledge EXPLICITLY asks for it — never infer.

## What Wrapper (wrapper.py) Already Handles — DO NOT Duplicate

| Responsibility | Detail | Transform MUST NOT |
|---|---|---|
| Config loading | `json.load(open('config.json'))` | Load config.json or reference file paths |
| Param parsing | Splits comma-delimited param string → operation, table_type, start_date, end_date | Parse raw param string (transform receives pre-parsed `param` list) |
| s3_bucket injection | Sets `config['s3_bucket']` and `config['date_control']['file_path']` from Glue runtime arg | Reference s3_bucket directly |
| Date control | `dc.retrieve_date()` → current_business_date; `dc.update_date_control()` on success | Implement date control retrieval or advancement |
| Operation dispatch | Selects day0 or day1 class based on `operation` | Implement operation routing logic |
| SparkSession creation | Builds SparkSession with all required configs (Iceberg, AQE, compression, etc.) | Create SparkSession or set SparkConf |
| Error handling & logging | Top-level try/except with logger | Implement top-level error handling (transform raises; wrapper catches) |

## What Driver (driver.py — Databricks) Already Handles — DO NOT Duplicate

| Responsibility | Detail | Transform MUST NOT |
|---|---|---|
| SparkSession & widgets | Retrieves runtime parameters via `dbutils.widgets` | Reference `dbutils` or create SparkSession |
| DateControl initialisation | `dc.insert_date_control_if_missing()` + `dc.get_business_dates()` → curr_bus_dt | Implement date control logic |
| Source reading orchestration | Instantiates transform class, calls `transform.run()` which delegates to SourceReader | Duplicate source reading in driver (it delegates to transform's class) |
| Write dispatch (Day 0 vs BAU) | `tableIOUtils.write_iceberg_table_overwrite()` for Day 0; `run_cdc()` for NonTransactional BAU; `tableIOUtils.write_iceberg_table_append()` for Transactional BAU (via TargetWriter) | Implement write mode selection or call write functions |
| Audit logging | `AuditLogger(spark, audit_table_fqn)` | Implement audit logging |
| Foundation library imports | `from databricks_foundation.core.date_control import DateControl`, `from databricks_foundation.logger.audit_logger import AuditLogger`, `from databricks_foundation.core.generic_tableIO_utils import tableIOUtils`, `from databricks_foundation.transformations.cdc import run_cdc` | Import foundation utilities (driver owns these) |
| Date control advancement | `dc.update_date_control()` on success only | Advance date control |

**Databricks transform class**: `{target_schema}_{table_name}_transform` with `__init__`, `prepare_sources`, `transformation`, `load`, `run`. Driver instantiates the class and calls `transform.run()` — transform handles all data logic internally via SourceReader/TargetWriter.

## Source Audit Columns — Exclude from Business Logic

The following columns may exist in source tables but are ETL/audit metadata — they MUST NOT be treated as business columns in transformation logic:

| Column | Origin | Treatment |
|---|---|---|
| `source_extract_timestamp` | BASE layer ETL audit | Exclude from CDC hash (pass via `cdc_exclude_cols`); do NOT transform or derive |
| `batch_id` | BASE layer ETL batch identifier | Exclude from CDC hash (pass via `cdc_exclude_cols`); do NOT transform or derive |
| `dw_lod_tmp` (in source) | Source load timestamp | NOT a target business column; ignore unless mapping explicitly references it |
| `dw_upd_lod_tmp` (in source) | Source update timestamp | Same as above |

These are passed through to the target if present in mapping column_mappings, but MUST be listed in `cdc_exclude_cols` when instantiating TargetWriter (extracted from domain knowledge per Phase 2.5 Step B).

## Multi-Source-System Ownership Boundaries

When multiple source systems feed one target table (`source_systems` is non-empty, declared via `source_system` key in Column K):

- **Generation pipeline** (`/gen-config`, `/gen-transform`) owns the source_system splitting decision — it determines how many artifacts to generate and what sources each contains
- **Runtime components** (SourceReader, TargetWriter, Driver/Wrapper) are source_system-agnostic — they process whatever the config tells them. Each per-source-system config is a standard flat single-flow config.
- **Rolling deletion**: Each source_system job's TargetWriter executes `_rolling_delete()` independently. The deletion predicate applies to the shared target table and is idempotent — multiple executions of the same predicate are safe. The rolling_deletion predicate MUST be source-system-agnostic (no source_system-specific column references) to ensure idempotency across concurrent jobs.
- **Audit logging**: Shared audit_log table. Concurrent independent source_system jobs write separate audit rows with distinct `process_name` values. No contention risk (append-only table).
- **DateControl**: Each source_system has its own `process_name` entry, enabling independent business date advancement and failure isolation.

## Summary: What Transform IS Responsible For

1. **Business logic ONLY**: joins, filters, aggregations, derivations, column renames/casts
2. **Day 0 audit columns**: derive eff_start_date, eff_end_date, active, dw_lod_tmp, dw_upd_lod_tmp (NonTransactional) or dw_bus_dt, dw_lod_tmp (Transactional)
3. **Source DataFrame access**: via `self.source_data['alias']` (pre-read by SourceReader). Access is transparent regardless of whether the source is a table or file — SourceReader resolves file-based sources (from config `source.file` section) identically to table sources.
4. **TargetWriter instantiation**: with correct `primary_key_cols`, `partition_col`, `cdc_exclude_cols` from intent + domain knowledge
5. **Calling `self.writer.write(df)`**: pass the final transformed DataFrame; writer handles write strategy
6. **Domain knowledge business rules**: date CASTs on source quirks, broadcast hints, dedup guards, NULL handling
7. **Crypto UDFs**: via `spark.sql()` only — detokenize in source read SQL, tokenize before final write SQL
