# Databricks notebook source
# COMMAND ----------
from pyspark.sql import SparkSession, DataFrame

from databricks_foundation.core.generic_tableIO_utils import tableIOUtils
from databricks_foundation.transformations.cdc import run_cdc

_CDC_AUDIT_COLS = frozenset({
    "eff_start_date",
    "eff_end_date",
    "active",
    "dw_bus_dt",
    "dw_lod_tmp",
    "dw_upd_lod_tmp",
})


class TargetWriter:
    """
    Writes transformed data to an Iceberg target table.
    Thin wrapper around databricks_foundation functions — delegates all
    heavy lifting (SCD2 merge, audit column injection, overwrite/append).
    """

    def __init__(self, spark: SparkSession, config: dict, operation: str,
                 table_type: str, curr_bus_dt: str, primary_key_cols: list,
                 audit=None, cdc_exclude_cols: list = None,
                 partition_col: str = None):
        """
        Args:
            spark:            Active SparkSession
            config:           Pipeline config dict (from config.yml)
            operation:        "day0" | "day1" | "bau"
            table_type:       "NonTransactional" | "Transactional"
            curr_bus_dt:      Current business date (ISO string YYYY-MM-DD)
            primary_key_cols: Primary key column names (for CDC)
            audit:            AuditLogger instance or None
            cdc_exclude_cols: Optional columns to exclude from CDC change detection.
                              Standard audit columns (eff_start_date, eff_end_date,
                              active, dw_bus_dt, dw_lod_tmp, dw_upd_lod_tmp) and
                              primary key columns are always excluded automatically.
            partition_col:    Partition column override (default: inferred)
        """
        self.spark = spark
        self.config = config
        self.operation = operation.strip().lower()
        self.table_type = table_type.strip()
        self.curr_bus_dt = curr_bus_dt
        self.primary_key_cols = primary_key_cols
        self.audit = audit
        self.cdc_exclude_cols = cdc_exclude_cols or []
        self.op = tableIOUtils(spark)

        target = config["target"]
        self.target_table = f"{target['catalog']}.{target['schema']}.{target['table']}"
        self.process_name = config["pipeline"]["process_name"]

        # SCD type flags
        self._is_scd1 = self.table_type == "NonTransactional_SCD1"
        self._is_non_transactional = self.table_type.startswith("NonTransactional")

    def _derive_check_cols(self, df: DataFrame) -> list:
        """
        Derive CDC/SCD check columns at runtime:
        all DataFrame columns minus PK, audit, and pipeline-specific exclusions.
        SCD1: excludes only dw_lod_tmp, dw_upd_lod_tmp, dw_bus_dt (no eff_start/end/active)
        SCD2: excludes full _CDC_AUDIT_COLS set
        """
        if self._is_scd1:
            excluded = (
                set(self.primary_key_cols)
                | {"dw_lod_tmp", "dw_upd_lod_tmp", "dw_bus_dt"}
                | set(self.cdc_exclude_cols)
            )
        else:
            excluded = set(self.primary_key_cols) | _CDC_AUDIT_COLS | set(self.cdc_exclude_cols)
        return [c for c in df.columns if c not in excluded]

    def write_parquet(self, df: DataFrame, path: str, mode: str = "overwrite",
                      partition_by: list = None, compression: str = "snappy") -> None:
        """Write DataFrame to parquet file(s) at target Volume or external location.

        Args:
            df:           Transformed Spark DataFrame.
            path:         Volume path or external location.
            mode:         'overwrite' (Day0 — full replace) or 'append' (Day1 — add partitions).
            partition_by: Columns to partition output by (e.g., ['dw_bus_dt']).
            compression:  Parquet compression codec. Default 'snappy'.
        """
        writer = df.write.mode(mode).option("compression", compression)
        if partition_by:
            writer = writer.partitionBy(*partition_by)
        writer.parquet(path)

    def write(self, df: DataFrame) -> None:
        """Dispatch to correct write strategy based on table_type + operation.

        After the write strategy completes, rolling deletion is executed if
        configured (Transactional and SCD1 only — see _rolling_delete).
        """
        # File target dispatch — when target_io is present, write parquet instead of table
        target_io = self.config.get('target_io')
        if target_io:
            self.write_parquet(
                df, target_io['path'],
                mode=target_io.get('write_mode', 'overwrite'),
                partition_by=target_io.get('partition_by', []),
                compression=target_io.get('compression', 'snappy'),
            )
            return  # Skip rolling_delete — not applicable to file targets

        if self.operation == "day0":
            self._write_day0(df)
        elif self._is_non_transactional:
            if self._is_scd1:
                self._write_scd1_upsert(df)
            else:
                self._write_cdc(df)
        else:
            self._write_append(df)

        # Rolling deletion — prune old data after successful write
        # (Transactional + SCD1 only; no-op for SCD2 and when config absent)
        self._rolling_delete()

    def _write_day0(self, df: DataFrame) -> None:
        """
        Full overwrite. Transform has already derived ALL audit columns.
        Works for both NonTransactional and Transactional Day0.
        """
        self.op.write_iceberg_table_overwrite(
            df=df,
            table=self.target_table,
            process_name=self.process_name,
            business_date=self.curr_bus_dt,
            audit=self.audit,
        )

    def _write_cdc(self, df: DataFrame) -> None:
        """
        SCD2 CDC merge for NonTransactional Day1/BAU.
        Foundation library handles: change detection, expire, insert, audit columns.
        check_cols derived at runtime: all columns minus PK, audit, and exclude_cols.
        """
        cdc_cfg = self.config.get("cdc", {})
        run_cdc(
            spark=self.spark,
            source_df=df,
            target_table=self.target_table,
            unique_keys=self.primary_key_cols,
            check_cols=self._derive_check_cols(df),
            curr_bus_dt=self.curr_bus_dt,
            high_ended_date=cdc_cfg.get("high_ended_date", "3499-12-31"),
            process_name=self.process_name,
            audit=self.audit,
            broadcast_source=cdc_cfg.get("broadcast_source", False),
            validate_unique_keys=cdc_cfg.get("validate_unique_keys", False),
            duplicates_ts_col=cdc_cfg.get("duplicates_ts_col"),
            dedup_order=cdc_cfg.get("dedup_order", "desc"),
            snapshot_mode=cdc_cfg.get("snapshot_mode", False),
        )

    def _write_scd1_upsert(self, df: DataFrame) -> None:
        """
        SCD1 UPSERT for NonTransactional_SCD1 Day1/BAU.

        Single-phase Iceberg MERGE via Spark SQL:
          WHEN MATCHED AND hash differs → UPDATE all business columns + dw_upd_lod_tmp
          WHEN NOT MATCHED → INSERT all business columns + dw_lod_tmp + dw_upd_lod_tmp

        Foundation library has no SCD1 function — implemented directly with spark.sql().
        Records are overwritten in place — no history maintained.
        """
        from pyspark.sql import functions as F
        from pyspark.sql.window import Window

        # Dedup source on PKs
        pk_window = Window.partitionBy(*self.primary_key_cols).orderBy(F.lit(1))
        df_deduped = (
            df.withColumn('_rn', F.row_number().over(pk_window))
            .filter(F.col('_rn') == 1)
            .drop('_rn')
        )

        df_deduped.cache()
        src_count = df_deduped.count()

        if src_count == 0:
            df_deduped.unpersist()
            return

        view_name = f"_src_{self.config['target']['table']}"
        df_deduped.createOrReplaceTempView(view_name)

        # Build MERGE SQL
        check_cols = self._derive_check_cols(df_deduped)
        biz_cols = [c for c in df_deduped.columns if c not in {"dw_lod_tmp", "dw_upd_lod_tmp"}]

        pk_join = ' AND '.join(f's.{c} = t.{c}' for c in self.primary_key_cols)

        # Hash for change detection
        cast_parts = ', '.join(f"CAST({{alias}}.{c} AS STRING)" for c in check_cols)
        src_hash = f"SHA2(CONCAT_WS('|', {cast_parts.format(alias='s')}), 256)"
        tgt_hash = f"SHA2(CONCAT_WS('|', {cast_parts.format(alias='t')}), 256)"

        update_set = ', '.join(f't.{c} = s.{c}' for c in biz_cols)
        update_set += ', t.dw_upd_lod_tmp = current_timestamp()'

        insert_cols = ', '.join(biz_cols + ['dw_lod_tmp', 'dw_upd_lod_tmp'])
        insert_vals = ', '.join(f's.{c}' for c in biz_cols)
        insert_vals += ', current_timestamp(), current_timestamp()'

        merge_sql = f"""
            MERGE INTO {self.target_table} t
            USING (SELECT *, {src_hash} AS _src_hash FROM {view_name}) s
            ON {pk_join}
            WHEN MATCHED AND {tgt_hash} != s._src_hash
            THEN UPDATE SET {update_set}
            WHEN NOT MATCHED
            THEN INSERT ({insert_cols}) VALUES ({insert_vals})
        """

        self.spark.sql(merge_sql)
        df_deduped.unpersist()

    def _write_append(self, df: DataFrame) -> None:
        """
        Partition append for Transactional Day1/BAU.
        Foundation library injects dw_lod_tmp.
        """
        self.op.write_iceberg_table_append(
            df=df,
            table=self.target_table,
            process_name=self.process_name,
            business_date=self.curr_bus_dt,
            audit=self.audit,
        )

    def _rolling_delete(self) -> None:
        """
        Delete rows matching the rolling_deletion predicate after a successful write.

        Applicable to Transactional and NonTransactional_SCD1 tables only.
        SCD2 tables are excluded — they maintain history via soft-expire
        (active='0') and must never have rows physically deleted by this writer.

        No-op when:
          - table_type is NonTransactional_SCD2
          - rolling_deletion config section is absent
          - rolling_deletion.enabled is False

        The predicate is a raw SQL WHERE clause with {current_business_date}
        as the only template variable (interpolated to ISO date string).

        Config example (YAML):
            rolling_deletion:
              enabled: true
              predicate: "dw_bus_dt < DATE_SUB(CAST('{current_business_date}' AS DATE), 90)"

        Iceberg DELETE with a partition-column predicate prunes to exact data
        files — no full table scan is required.  The operation is idempotent:
        re-running with the same business date deletes the same (or no) rows.
        """
        if self.table_type == "NonTransactional_SCD2":
            return

        rd_cfg = self.config.get("rolling_deletion", {})
        if not rd_cfg.get("enabled", False):
            return

        predicate = rd_cfg["predicate"].format(
            current_business_date=self.curr_bus_dt
        )
        delete_sql = f"DELETE FROM {self.target_table} WHERE {predicate}"

        self.spark.sql(delete_sql)
