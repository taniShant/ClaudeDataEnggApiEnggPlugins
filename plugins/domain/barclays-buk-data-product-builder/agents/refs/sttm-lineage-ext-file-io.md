---
description: "Conditional STTM extension for file-based source lineage — loaded when file_read_detected is true to handle parquet and CSV source attribution with logical name resolution patterns."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
last_reviewed: 2026-09-24
---

# File I/O Lineage Extension

> **Loaded conditionally** — only when `file_read_detected == true` in code_prescan.

**PURPOSE**: Handle lineage extraction for parquet file-based sources. Loaded conditionally when `file_read_detected == true` in code_prescan.

## File Source Detection Patterns

Detect these PySpark patterns as file source reads:

| Pattern | Example |
|---|---|
| Direct parquet read | `df = spark.read.parquet("s3://bucket/path/")` |
| Format-based read | `df = spark.read.format("parquet").load("s3://bucket/path/")` |
| With options | `df = spark.read.option("mergeSchema", "true").parquet("path")` |

## Logical Name Resolution

For each detected file read, derive a logical name:

1. **From session state** (preferred): If `source_io.sources[].storage_path` matches the detected path, use `source_io.sources[].logical_name` (basename derived from the absolute path in mapping Column H)
2. **From variable assignment**: If code assigns `customer_events = spark.read.parquet(...)`, use the variable name `customer_events`
3. **From path basename**: Extract the last path segment (e.g., `s3://bucket/raw/customer_events/` → `customer_events`)

## Column Resolution

- **Parquet files embed schema**: Column names and types can be inferred from the file metadata at runtime
- **From code context**: If the code subsequently selects columns (`.select("col1", "col2")`), use those as the known column list
- **From explicit schema**: If `input/source_metadata/{logical_name}_schema.json` exists, use that as the authoritative column list
- **Fallback**: Mark `schema_mode=inferred` — columns will be validated at code generation time, not during STTM generation

## Lineage Output

File sources are added to the standard lineage outputs using their logical name:

- `tables_referenced[]`: Include `{logical_name}` (not the storage path)
- `lineage[]`: Column lineage entries use `{logical_name}.{column}` as source reference
- `joins_detected[]`: File sources use their logical name as table alias in join entries

## Metadata Recording

For each file source, record in lineage metadata:

```json
{
  "file_sources": {
    "customer_events": {
      "storage_path": "s3://bucket/raw/customer_events/",
      "format": "parquet",
      "schema_mode": "inferred",
      "detected_columns": ["event_id", "customer_id", "event_date"]
    }
  }
}
```
