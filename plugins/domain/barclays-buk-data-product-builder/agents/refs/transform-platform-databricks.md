---
description: "Databricks-specific TargetWriter and run_cdc integration — covers the dispatch model (Day0, Day1 NonTransactional, Day1 Transactional branches) and the class-based pattern for Databricks transforms."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-07-08
---

# TargetWriter / run_cdc Usage (Databricks Platform)

This reference defines the TargetWriter and run_cdc integration pattern for Databricks transforms.

## Dispatch Model

The transform class does NOT call `run_cdc` directly. `TargetWriter.write(transformed_df)` dispatches internally:
- Day0: TargetWriter calls `tableIOUtils` for full Iceberg overwrite
- Day1 NonTransactional: TargetWriter invokes `run_cdc()` for SCD2 merge
- Day1 Transactional: TargetWriter invokes `tableIOUtils` append

## Class-Based Pattern

Class name: `{target_schema}_{table_name}_transform`

```python
class {{target_schema}}_{{table_name}}_transform:
    def __init__(self, spark: SparkSession, config: dict, curr_bus_dt: str, audit=None):
        self.spark       = spark
        self.config      = config
        self.curr_bus_dt = curr_bus_dt
        self.audit       = audit
        self.operation   = config["pipeline"]["load_type"].lower()
        self.table_type  = config["pipeline"]["table_type"]

        # Source reads via SourceReader (wraps spark.table for FQN resolution)
        # source_catalog from config.yml used for FQN: {source_catalog}.{source_schema}.{table}
        self.reader = SourceReader(
            spark       = spark,
            config      = config,
            operation   = self.operation,
            curr_bus_dt = curr_bus_dt,
        )

        # Writes via TargetWriter (wraps tableIOUtils; dispatches to run_cdc for Day1 NonTransactional)
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

    def prepare_sources(self) -> None:
        self.source_data = self.reader.read_source_data()
        # Named attrs: self.{alias} = self.source_data['{alias}']

    def transformation(self) -> DataFrame:
        # Business logic here — reads from self.{alias} (NOT hf.read_table)
        # For ad-hoc source reads: spark.table("{source_catalog}.{schema}.{table}").filter(...)
        ...
        return transformed_df

    def load(self, transformed_df: DataFrame) -> None:
        self.writer.write(transformed_df)

    def run(self) -> None:
        self.prepare_sources()
        transformed_df = self.transformation()
        self.load(transformed_df)
```

## run_cdc Internal Parameters

For reference — invoked internally by TargetWriter, NOT by transform class. TargetWriter derives `check_cols` at runtime from DataFrame columns minus PK, audit, and `exclude_cols`:

```python
run_cdc(
    spark=spark,
    source_df=source_df,
    target_table="{catalog}.{schema}.{target_table}",
    unique_keys={primary_key_columns},
    check_cols=self._derive_check_cols(df),  # derived at runtime
    curr_bus_dt=curr_bus_dt,
    high_ended_date="3499-12-31",
    process_name=process_name,
    audit=audit_logger,
    broadcast_source=cdc_cfg.get("broadcast_source", False),
    validate_unique_keys=cdc_cfg.get("validate_unique_keys", False),  # default false; true when mapping specifies validate_unique_keys:true
    duplicates_ts_col=cdc_cfg.get("duplicates_ts_col"),               # optional — only present when specified in mapping or domain knowledge
    dedup_order=cdc_cfg.get("dedup_order", "desc"),                   # optional — only present when duplicates_ts_col is specified
    snapshot_mode=cdc_cfg.get("snapshot_mode", False),
)
```

## Source Table FQN Resolution

The `source_catalog` parameter from `config.yml` is used to construct the fully qualified name for source table reads. SourceReader resolves `{source_catalog}.{source_schema}.{source_table}` from the config sources section. For any ad-hoc reads outside SourceReader, use `spark.table("{source_catalog}.{schema}.{table}").filter(...)` — never `hf.read_table(table=..., filter_condition=...)`.

## Rolling Deletion — `_rolling_delete()`

```
_rolling_delete() → None
    Post-write deletion of rows matching config['rolling_deletion']['predicate'].
    Called automatically at the end of write(). No-op for SCD2 tables or when config absent.
    Interpolates {current_business_date} from self.curr_bus_dt.
    Applicable to: Transactional, NonTransactional_SCD1.
```

The transform does not call `_rolling_delete()` — it is invoked internally by `TargetWriter.write()` after the main write strategy completes. Config structure:

```yaml
rolling_deletion:
  enabled: true
  predicate: "dw_bus_dt < CAST('{current_business_date}' AS DATE) - INTERVAL 90 DAY"
```

---

> **Note**: The constructor signatures and method APIs shown above are illustrative summaries. The **authoritative source** is the actual utility code at `${CLAUDE_PLUGIN_ROOT}/templates/databricks/generic_components/source_reader.py` and `target_writer.py`. Read those files in the GATHER phase (STEP 0.55) for exact signatures, return types, and available methods.
