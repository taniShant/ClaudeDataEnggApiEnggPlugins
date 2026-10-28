import logging
from datetime import date

import pyspark.sql.functions as F
from pyspark.sql import DataFrame
from pyspark.storage import StorageLevel

logger = logging.getLogger(__name__)

# ── BUK CDAO standard column names ───────────────────────────────────────────
# These are organisation-wide standards enforced by the Mesh JSON / DDL.
# They must not vary per pipeline — writer code uses these directly.

_EFF_START_COL  = 'eff_start_date'
_EFF_END_COL    = 'eff_end_date'
_ACTIVE_COL     = 'active'
_DW_LOAD_TS_COL = 'dw_lod_tmp'
_DW_UPD_TS_COL  = 'dw_upd_lod_tmp'

# SCD2 sentinel end-date — open-ended active record marker
_MAX_DATE = '3499-12-31'

# Writer-owned columns excluded from CDC change detection.
# None of these represent a business-attribute change — they are lifecycle,
# partition, or load-audit columns that the writer manages itself.
# Pipeline-specific exclusions are supplied via cdc_exclude_cols constructor arg.
_CDC_AUDIT_COLS = frozenset({
    _EFF_START_COL,   # SCD2 lifecycle — writer-owned
    _EFF_END_COL,     # SCD2 lifecycle — writer-owned
    _ACTIVE_COL,      # SCD2 lifecycle — writer-owned
    'dw_bus_dt',      # business-date partition column
    _DW_LOAD_TS_COL,  # load timestamp — writer-owned
    _DW_UPD_TS_COL,   # update-load timestamp — writer-owned
})


class TargetWriter:
    """
    Writes transformed data to an Iceberg target table for a single Glue pipeline execution.

    Instantiated once per transform run; the same object is used for the single target write:

        writer = TargetWriter(
            spark                 = spark,
            config                = config,
            param                 = param,
            current_business_date = current_business_date,
            primary_key_cols      = ['customer_id', 'account_id'],
            partition_col         = 'dw_bus_dt',       # Transactional
            cdc_exclude_cols      = ['batch_id', 'source_file_name'],  # optional; one or more pipeline-specific cols
            snapshot_mode         = True,              # True = full snapshot; False = delta feed (default)
        )

        writer.write(transformed_df)

    Write dispatch
    --------------
    Non-Transactional + day0      → full Iceberg atomic overwrite (idempotent rebuild)
    Non-Transactional + day1/bau  → SCD2 CDC two-phase merge (expire + insert)
    Transactional     + any       → dynamic Iceberg partition overwrite (idempotent)

    Writer-owned columns (injected; must NOT be present in the incoming DataFrame)
    -------------------------------------------------------------------------------
    Non-Transactional target tables require all five columns below.
    Transactional target tables require dw_lod_tmp only.

        eff_start_date   — SCD2 effective start date of the record version
        eff_end_date     — SCD2 effective end date (3499-12-31 = still active)
        active           — SCD2 flag: '1' = current record, '0' = expired record (string)
        dw_lod_tmp       — timestamp when the record was first loaded into the table
                           (set on INSERT; never updated once written)
        dw_upd_lod_tmp   — timestamp when the record was last touched by the pipeline
                           (set on INSERT; also refreshed when a record is expired in
                           Phase 1 of the CDC merge)

    Column names are BUK CDAO organisation-wide standards defined as module-level
    constants (_EFF_START_COL, _EFF_END_COL, _ACTIVE_COL, _DW_LOAD_TS_COL,
    _DW_UPD_TS_COL).  They are not constructor parameters — overriding them at the
    writer level would produce a broken pipeline because the Mesh JSON / DDL enforces
    the same names.

    Idempotency guarantees
    ----------------------
    day0 Non-Transactional : Iceberg overwrite(F.lit(True)) — atomic full-table replace.
    day1/bau Non-Transactional: Phase 2 INSERT uses NOT EXISTS (... WHERE active='1') so
        re-running the same business date is a no-op for already-inserted records.
    Transactional : overwritePartitions() replaces exactly the affected partition(s)
        — re-running the same dw_bus_dt produces the same result.

    Public methods
    --------------
    write(df) → None
        Dispatch to the correct write strategy based on table_type and operation.
    """

    def __init__(
        self,
        spark,
        config: dict,
        param: list,
        current_business_date: date,
        primary_key_cols: list,
        partition_col: str = 'dw_bus_dt',
        cdc_exclude_cols: list = None,
        snapshot_mode: bool = False,
    ):
        """
        Args:
            spark:                  Active SparkSession.
            config:                 Pipeline config dict loaded from config.json at runtime.
            param:                  Parsed param list from Glue job argument.
                                    param[0] = operation   (day0 | day1 | bau)
                                    param[1] = table_type  (NonTransactional_SCD2 | NonTransactional_SCD1 | Transactional)
            current_business_date:  Business date as a datetime.date object.
            primary_key_cols:       Non-empty list of column name(s) that form the natural key
                                    of the entity.  Used in the SCD2 join predicate and
                                    deduplication guard.
            partition_col:          Partition column name on the Iceberg table.
                                    Default 'dw_bus_dt' (standard Transactional partition).
                                    Not used for Non-Transactional tables.
            cdc_exclude_cols:       Optional list of pipeline-specific column names to exclude
                                    from CDC change detection in addition to the automatic
                                    exclusions.  Use this for columns that change on every run
                                    but do not represent a meaningful business change
                                    (e.g. 'batch_id', 'source_file_name').
                                    Standard BUK CDAO audit columns (eff_start_date,
                                    eff_end_date, active, dw_bus_dt, dw_lod_tmp,
                                    dw_upd_lod_tmp) are always excluded automatically via
                                    _CDC_AUDIT_COLS — no need to list them here.
                                    Primary key columns are also always excluded.
            snapshot_mode:          If True, source DataFrame represents a full snapshot of
                                    all active entities. Active target rows whose PK is absent
                                    from source will be expired (Phase 0). If False (default),
                                    source is a delta feed — absence from source means unchanged.
        """
        if not primary_key_cols:
            raise ValueError("primary_key_cols must be a non-empty list")

        self.spark                 = spark
        self.config                = config
        self.param                 = param
        self.current_business_date = current_business_date
        self.primary_key_cols      = primary_key_cols
        self.partition_col         = partition_col
        self.cdc_exclude_cols      = set(cdc_exclude_cols or [])
        self.snapshot_mode         = snapshot_mode
        self.operation             = param[0].strip().lower()
        self.table_type            = param[1].strip() if len(param) > 1 else ''

        # SCD type flags — derived from table_type for dispatch convenience
        # Session convention values: NonTransactional_SCD2 | NonTransactional_SCD1 | Transactional
        self._is_scd1 = self.table_type == 'NonTransactional_SCD1'
        self._is_non_transactional = self.table_type.startswith('NonTransactional')

    # ── Private helpers ───────────────────────────────────────────────────────

    @property
    def _target_fqn(self) -> str:
        """Fully-qualified Iceberg table name: glue_catalog.<database>.<tablename>."""
        return f"glue_catalog.{self.config['database']}.{self.config['tablename']}"

    def _biz_cols(self, df: DataFrame) -> list:
        """
        Business columns from df with all writer-owned columns removed.

        Table type determines which columns are writer-owned:
            SCD2:          eff_start_date, eff_end_date, active, dw_lod_tmp, dw_upd_lod_tmp
            SCD1:          dw_lod_tmp, dw_upd_lod_tmp (no eff_start/end/active — they don't exist)
            Transactional: dw_lod_tmp only (dw_bus_dt is transform-derived, not writer-owned)

        Result is used to build the INSERT column list and SELECT projection in
        the MERGE — writer-owned columns are appended as literals afterward.
        """
        if self.table_type == 'Transactional':
            writer_cols = {_DW_LOAD_TS_COL}
        elif self._is_scd1:
            writer_cols = {_DW_LOAD_TS_COL, _DW_UPD_TS_COL}
        else:
            writer_cols = {
                _EFF_START_COL, _EFF_END_COL, _ACTIVE_COL,
                _DW_LOAD_TS_COL, _DW_UPD_TS_COL,
            }
        return [c for c in df.columns if c not in writer_cols]

    def _non_pk_biz_cols(self, df: DataFrame) -> list:
        """
        Columns eligible for CDC/SCD change detection — three exclusion layers applied:

          1. Primary key columns  — used for the join predicate, not for change value.
          2. Standard BUK CDAO audit columns:
               SCD2:          eff_start_date, eff_end_date, active, dw_bus_dt, dw_lod_tmp, dw_upd_lod_tmp
               SCD1:          dw_lod_tmp, dw_upd_lod_tmp, dw_bus_dt (no eff_start/end/active)
               Transactional: dw_lod_tmp, partition_col (part of join predicate)
          3. Pipeline-specific exclusions (cdc_exclude_cols constructor arg):
               Any column whose change does not represent a meaningful business update
               (e.g. batch_id, source_file_name).

        Columns already stripped by _biz_cols() are absent from the input; the exclusion
        set acts as a belt-and-braces guard for the standard column names.
        """
        if self.table_type == 'Transactional':
            excluded = (
                set(self.primary_key_cols)
                | {_DW_LOAD_TS_COL, self.partition_col}
                | self.cdc_exclude_cols
            )
        elif self._is_scd1:
            excluded = (
                set(self.primary_key_cols)
                | {_DW_LOAD_TS_COL, _DW_UPD_TS_COL, 'dw_bus_dt'}
                | self.cdc_exclude_cols
            )
        else:
            excluded = set(self.primary_key_cols) | _CDC_AUDIT_COLS | self.cdc_exclude_cols
        return [c for c in self._biz_cols(df) if c not in excluded]

    def _pk_join_sql(self, src_alias: str = 's', tgt_alias: str = 't') -> str:
        """SQL join predicate on all primary key columns (AND-joined)."""
        return ' AND '.join(
            f'{src_alias}.{c} = {tgt_alias}.{c}' for c in self.primary_key_cols
        )

    def _hash_sql(self, df: DataFrame, alias: str) -> str:
        """
        SHA2-256 hash over the CDC-eligible columns (_non_pk_biz_cols).

        SHA2(CONCAT_WS('|', CAST(col1 AS STRING), CAST(col2 AS STRING), ...), 256)

        Columns excluded from the hash (see _non_pk_biz_cols for full rules):
          - Primary key columns
          - Standard audit columns: eff_start_date, eff_end_date, active, dw_bus_dt,
            dw_lod_tmp, dw_upd_lod_tmp
          - Pipeline-specific extras supplied via cdc_exclude_cols

        Used to detect row-level business changes without requiring a stored hash
        column in the target schema.  Both source and target expressions are computed
        inline within the MERGE SQL statement.
        """
        cols = self._non_pk_biz_cols(df)
        if not cols:
            # All columns are PKs — hash over PKs to avoid empty CONCAT_WS
            cols = self.primary_key_cols
        cast_parts = ', '.join(f"CAST({alias}.{c} AS STRING)" for c in cols)
        return f"SHA2(CONCAT_WS('|', {cast_parts}), 256)"

    @staticmethod
    def _temp_view_name(table_name: str) -> str:
        return f"_src_{table_name}"

    def _add_writer_cols(self, df: DataFrame) -> DataFrame:
        """
        Append all writer-owned audit columns to the incoming DataFrame.

        Used for Non-Transactional day0 overwrite.  The same values are expressed
        as SQL literals in Phase 2 INSERT for the CDC merge path.

            eff_start_date  = current_business_date
            eff_end_date    = 3499-12-31
            active          = '1'
            dw_lod_tmp      = current_timestamp()
            dw_upd_lod_tmp  = current_timestamp()
        """
        return (
            df
            .withColumn(_EFF_START_COL,  F.to_date(F.lit(self.current_business_date.isoformat())))
            .withColumn(_EFF_END_COL,    F.to_date(F.lit(_MAX_DATE)))
            .withColumn(_ACTIVE_COL,     F.lit('1').cast('string'))
            .withColumn(_DW_LOAD_TS_COL, F.current_timestamp())
            .withColumn(_DW_UPD_TS_COL,  F.current_timestamp())
        )

    # ── Write strategies ──────────────────────────────────────────────────────

    def _write_non_transactional_day0(self, df: DataFrame) -> None:
        """
        Full atomic Iceberg overwrite for Non-Transactional day0 loads.

        Day 0 transform is responsible for ALL audit columns (eff_start_date, eff_end_date,
        active, dw_lod_tmp, dw_upd_lod_tmp). Writer does NOT inject any audit columns —
        it writes the DataFrame as-is in a single Iceberg atomic operation.

        Idempotent: re-running with the same DataFrame produces the same target state.
        """
        target = self._target_fqn
        logger.info("day0 Non-Transactional full overwrite → %s", target)

        view_name = self._temp_view_name(self.config['tablename'])
        df.createOrReplaceTempView(view_name)
        self.spark.sql(f"INSERT OVERWRITE TABLE {target} SELECT * FROM {view_name}")

        logger.info("day0 Non-Transactional overwrite complete → %s", target)

    def _write_scd1_upsert(self, df: DataFrame) -> None:
        """
        SCD1 UPSERT for NonTransactional_SCD1 day1/bau loads.

        Single-phase Iceberg MERGE:
          WHEN MATCHED AND hash differs → UPDATE all business columns + dw_upd_lod_tmp
          WHEN NOT MATCHED → INSERT all business columns + dw_lod_tmp + dw_upd_lod_tmp

        Records are overwritten in place — no history maintained.
        No eff_start_date, eff_end_date, or active columns involved.
        No snapshot_mode — full-snapshot sources use Day0 overwrite instead.

        Reads primary_key_cols and exclude_cols from config["cdc"] section.

        Idempotency: hash-based change detection means re-running same data triggers
        no UPDATE. INSERT of already-existing PK is caught by WHEN MATCHED path.
        """
        target = self._target_fqn
        logger.info("SCD1 UPSERT → %s (operation=%s)", target, self.operation)

        # ── Dedup source on PKs (keep first occurrence) ──────────────────────
        from pyspark.sql.window import Window

        pk_window = Window.partitionBy(*self.primary_key_cols).orderBy(F.lit(1))
        df_deduped = (
            df.withColumn('_rn', F.row_number().over(pk_window))
            .filter(F.col('_rn') == 1)
            .drop('_rn')
        )

        # ── Cache and create temp view ───────────────────────────────────────
        df_deduped.cache()
        src_count = df_deduped.count()
        logger.info("SCD1 source rows (deduped): %d", src_count)

        if src_count == 0:
            logger.info("SCD1 UPSERT — empty source, nothing to write")
            df_deduped.unpersist()
            return

        view_name = self._temp_view_name(self.config['tablename'])
        df_deduped.createOrReplaceTempView(view_name)

        # ── Build MERGE SQL ──────────────────────────────────────────────────
        biz_cols = self._biz_cols(df_deduped)
        pk_join = self._pk_join_sql('s', 't')
        src_hash = self._hash_sql(df_deduped, 's')
        tgt_hash = self._hash_sql(df_deduped, 't')

        # UPDATE SET clause — all business columns + dw_upd_lod_tmp
        update_set = ', '.join(f't.{c} = s.{c}' for c in biz_cols)
        update_set += f', t.{_DW_UPD_TS_COL} = current_timestamp()'

        # INSERT columns and values
        insert_cols = ', '.join(biz_cols + [_DW_LOAD_TS_COL, _DW_UPD_TS_COL])
        insert_vals = ', '.join(f's.{c}' for c in biz_cols)
        insert_vals += ', current_timestamp(), current_timestamp()'

        merge_sql = f"""
            MERGE INTO {target} t
            USING (SELECT *, {src_hash} AS _src_hash FROM {view_name}) s
            ON {pk_join}
            WHEN MATCHED AND {tgt_hash} != s._src_hash
            THEN UPDATE SET {update_set}
            WHEN NOT MATCHED
            THEN INSERT ({insert_cols}) VALUES ({insert_vals})
        """

        logger.info("Executing SCD1 MERGE SQL")
        self.spark.sql(merge_sql)

        # ── Cleanup ──────────────────────────────────────────────────────────
        df_deduped.unpersist()
        logger.info("SCD1 UPSERT complete → %s", target)

    def _write_cdc_merge(self, df: DataFrame) -> None:
        """
        SCD2 CDC merge for Non-Transactional day1/bau loads.

        Phase 0 — Expire missing records (snapshot_mode only)
        -----------------------------------------------------
        When snapshot_mode=True, the source DataFrame is a full snapshot of all
        active entities. Active target rows whose PK has no match in source are
        expired: eff_end_date = current_business_date, active = 0.
        Skipped entirely when snapshot_mode=False (delta feed).

        Phase 1 — Expire changed active records
        ----------------------------------------
        For every source row whose hash differs from the matching active target row,
        set eff_end_date = current_business_date, active = 0, and
        dw_upd_lod_tmp = current_timestamp() on the target record.

        Phase 2 — Insert new and changed records
        -----------------------------------------
        Insert source rows where no active matching record exists in the target.
        eff_start_date = current_business_date (same value used as eff_end_date
        on the expired predecessor record for the same PK).
        The NOT EXISTS guard makes Phase 2 idempotent: re-running the same
        business date is a no-op for records already inserted.

        Change detection uses SHA2(CONCAT_WS) over CDC-eligible columns only:
        primary keys, standard audit columns (eff_start_date, eff_end_date, active,
        dw_bus_dt, dw_lod_tmp, dw_upd_lod_tmp), and any cdc_exclude_cols are all
        excluded from the hash.  No persistent hash column is required in the target
        schema.

        Best-practice notes
        -------------------
        - Source DataFrame is deduplicated on PKs before the merge to prevent
          ambiguous MERGE behaviour when the source contains duplicates.
        - DataFrame is cached (MEMORY_AND_DISK) and materialised with count()
          before being used in both SQL phases to avoid double-evaluation.
        - unpersist() is called in a finally block to release cache regardless
          of success or failure.
        - A named Spark temp view is used to reference the source DataFrame
          inside MERGE/INSERT SQL statements.
        """
        target     = self._target_fqn
        table_name = self.config['tablename']
        view_name  = self._temp_view_name(table_name)
        biz_cols   = self._biz_cols(df)
        cbd        = self.current_business_date.isoformat()

        logger.info("CDC merge → %s | operation=%s | pk=%s | snapshot_mode=%s", target, self.operation, self.primary_key_cols, self.snapshot_mode)

        # Deduplicate on PKs — last row wins (arbitrary; prevents MERGE ambiguity)
        df_deduped = df.dropDuplicates(self.primary_key_cols)

        # Cache and materialise before two SQL phases
        df_deduped.persist(StorageLevel.MEMORY_AND_DISK)
        row_count = df_deduped.count()
        logger.info("Source materialised: %d rows (after PK deduplication)", row_count)

        df_deduped.createOrReplaceTempView(view_name)

        try:
            # ── Phase 0: expire active target rows missing from source (snapshot only)
            if self.snapshot_mode:
                pk_cols_sql = ', '.join(self.primary_key_cols)
                pk_join_p0  = self._pk_join_sql()

                phase0_sql = f"""
                    MERGE INTO {target} t
                    USING (
                        SELECT DISTINCT {pk_cols_sql}
                        FROM {view_name}
                    ) s
                    ON {pk_join_p0}
                    WHEN NOT MATCHED BY SOURCE
                    AND t.{_ACTIVE_COL} = '1'
                    THEN UPDATE SET
                        t.{_EFF_END_COL}  = CAST('{cbd}' AS DATE),
                        t.{_ACTIVE_COL}   = '0',
                        t.{_DW_UPD_TS_COL} = current_timestamp()
                """
                logger.info("Phase 0: expire records missing from source (snapshot_mode)")
                self.spark.sql(phase0_sql)
                logger.info("Phase 0 complete")

            # ── Phase 1: expire changed active records ────────────────────────
            src_hash_expr = self._hash_sql(df, alias='s')
            tgt_hash_expr = self._hash_sql(df, alias='t')
            pk_join       = self._pk_join_sql()

            phase1_sql = f"""
                MERGE INTO {target} t
                USING (
                    SELECT *, {src_hash_expr} AS _src_hash
                    FROM {view_name}
                ) s
                ON {pk_join}
                AND t.{_ACTIVE_COL} = '1'
                WHEN MATCHED
                AND {tgt_hash_expr} != s._src_hash
                THEN UPDATE SET
                    t.{_EFF_END_COL}  = CAST('{cbd}' AS DATE),
                    t.{_ACTIVE_COL}   = '0',
                    t.{_DW_UPD_TS_COL} = current_timestamp()
            """
            logger.info("Phase 1: expire changed records")
            self.spark.sql(phase1_sql)
            logger.info("Phase 1 complete")

            # ── Phase 2: insert new and changed records ───────────────────────
            # Column list for INSERT — business cols + all writer-owned audit cols
            insert_cols = biz_cols + [
                _EFF_START_COL,
                _EFF_END_COL,
                _ACTIVE_COL,
                _DW_LOAD_TS_COL,
                _DW_UPD_TS_COL,
            ]
            col_list_sql   = ', '.join(insert_cols)
            select_src_sql = ', '.join(f's.{c}' for c in biz_cols)
            pk_join_exists = self._pk_join_sql(src_alias='s', tgt_alias='t')

            phase2_sql = f"""
                INSERT INTO {target} ({col_list_sql})
                SELECT
                    {select_src_sql},
                    CAST('{cbd}'       AS DATE) AS {_EFF_START_COL},
                    CAST('{_MAX_DATE}' AS DATE) AS {_EFF_END_COL},
                    '1'                          AS {_ACTIVE_COL},
                    current_timestamp()         AS {_DW_LOAD_TS_COL},
                    current_timestamp()         AS {_DW_UPD_TS_COL}
                FROM {view_name} s
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM {target} t
                    WHERE {pk_join_exists}
                    AND t.{_ACTIVE_COL} = '1'
                )
            """
            logger.info("Phase 2: insert new/changed records")
            self.spark.sql(phase2_sql)
            logger.info("Phase 2 complete")

        finally:
            df_deduped.unpersist()
            logger.info("Source cache released")

        logger.info("CDC merge complete → %s", target)

    def _write_transactional(self, df: DataFrame) -> None:
        """
        Write strategy for Transactional tables.

        Day 0 — INSERT OVERWRITE (full partition rebuild)
        -------------------------------------------------
        Transform has already derived ALL audit columns (partition_col, dw_lod_tmp).
        Writer does NOT inject dw_lod_tmp — writes DataFrame as-is via INSERT OVERWRITE.
        Dynamic partition overwrite mode (set in wrapper Spark config) replaces only
        the partition(s) present in df, leaving all other partitions untouched.
        Fully idempotent: re-running with the same data produces the same target state.

        Day 1/BAU — PK + partition_col MERGE (idempotent upsert)
        --------------------------------------------------------
        MERGE on primary_key_cols + partition_col ensures same PK can exist across
        multiple partitions (typical for event/fact tables where PK is event_id per day).
        Hash-based change detection (SHA2 over non-PK business columns) avoids
        unnecessary UPDATEs when re-running identical data — true no-op on re-run.
        Writer injects dw_lod_tmp = current_timestamp() for both UPDATE and INSERT.
        Source is deduped on PK + partition_col before MERGE (keeps first occurrence).

        The partition column (resolved from mapping/config via self.partition_col)
        must be present in df.
        """
        target = self._target_fqn
        logger.info(
            "Transactional write → %s | partition_col=%s | operation=%s",
            target, self.partition_col, self.operation,
        )

        if self.partition_col not in df.columns:
            raise ValueError(
                f"Partition column '{self.partition_col}' not found in DataFrame. "
                f"Available columns: {df.columns}"
            )

        if self.operation == 'day0':
            self._write_transactional_day0(df)
        else:
            self._write_transactional_merge(df)

    def _write_transactional_day0(self, df: DataFrame) -> None:
        """Day 0: INSERT OVERWRITE — full partition rebuild, no audit column injection."""
        target = self._target_fqn

        df.persist(StorageLevel.MEMORY_AND_DISK)
        row_count = df.count()
        logger.info("Transactional day0 materialised: %d rows", row_count)

        view_name = self._temp_view_name(self.config['tablename'])
        try:
            df.createOrReplaceTempView(view_name)
            self.spark.sql(f"INSERT OVERWRITE TABLE {target} SELECT * FROM {view_name}")
        finally:
            df.unpersist()
            logger.info("Transactional day0 cache released")

        logger.info("Transactional day0 INSERT OVERWRITE complete → %s", target)

    def _write_transactional_merge(self, df: DataFrame) -> None:
        """
        Day 1/BAU: PK + partition_col MERGE — idempotent upsert with hash change detection.

        MERGE INTO target t
        USING source s
        ON t.pk = s.pk AND t.{partition_col} = s.{partition_col}
        WHEN MATCHED AND hash differs → UPDATE business cols + dw_lod_tmp
        WHEN NOT MATCHED → INSERT all business cols + dw_lod_tmp
        """
        target = self._target_fqn
        logger.info("Transactional MERGE → %s (operation=%s)", target, self.operation)

        # ── Dedup source on PK + partition_col (keep first occurrence) ───────
        from pyspark.sql.window import Window

        dedup_cols = list(self.primary_key_cols) + [self.partition_col]
        pk_window = Window.partitionBy(*dedup_cols).orderBy(F.lit(1))
        df_deduped = (
            df.withColumn('_rn', F.row_number().over(pk_window))
            .filter(F.col('_rn') == 1)
            .drop('_rn')
        )

        # ── Cache and create temp view ───────────────────────────────────────
        df_deduped.cache()
        src_count = df_deduped.count()
        logger.info("Transactional source rows (deduped): %d", src_count)

        if src_count == 0:
            logger.info("Transactional MERGE — empty source, nothing to write")
            df_deduped.unpersist()
            return

        view_name = self._temp_view_name(self.config['tablename'])
        df_deduped.createOrReplaceTempView(view_name)

        # ── Build MERGE SQL ──────────────────────────────────────────────────
        biz_cols = self._biz_cols(df_deduped)
        pk_join = self._pk_join_sql('s', 't')
        partition_join = f"t.{self.partition_col} = s.{self.partition_col}"
        src_hash = self._hash_sql(df_deduped, 's')
        tgt_hash = self._hash_sql(df_deduped, 't')

        # UPDATE SET clause — all business columns + dw_lod_tmp
        update_set = ', '.join(f't.{c} = s.{c}' for c in biz_cols)
        update_set += f', t.{_DW_LOAD_TS_COL} = current_timestamp()'

        # INSERT columns and values
        insert_cols = ', '.join(biz_cols + [_DW_LOAD_TS_COL])
        insert_vals = ', '.join(f's.{c}' for c in biz_cols)
        insert_vals += ', current_timestamp()'

        merge_sql = f"""
            MERGE INTO {target} t
            USING (SELECT *, {src_hash} AS _src_hash FROM {view_name}) s
            ON {pk_join} AND {partition_join}
            WHEN MATCHED AND {tgt_hash} != s._src_hash
            THEN UPDATE SET {update_set}
            WHEN NOT MATCHED
            THEN INSERT ({insert_cols}) VALUES ({insert_vals})
        """

        logger.info("Executing Transactional MERGE SQL")
        self.spark.sql(merge_sql)

        # ── Cleanup ──────────────────────────────────────────────────────────
        df_deduped.unpersist()
        logger.info("Transactional MERGE complete → %s", target)

    # ── Rolling deletion ─────────────────────────────────────────────────────

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

        Config example:
            "rolling_deletion": {
                "enabled": true,
                "predicate": "dw_bus_dt < DATE_SUB(CAST('{current_business_date}' AS DATE), 90)"
            }

        Iceberg DELETE with a partition-column predicate prunes to exact data
        files — no full table scan is required.  The operation is idempotent:
        re-running with the same business date deletes the same (or no) rows.
        """
        if self.table_type == 'NonTransactional_SCD2':
            return

        rd_cfg = self.config.get('rolling_deletion', {})
        if not rd_cfg.get('enabled', False):
            return

        predicate = rd_cfg['predicate'].format(
            current_business_date=self.current_business_date.isoformat()
        )
        target = self._target_fqn
        delete_sql = f"DELETE FROM {target} WHERE {predicate}"

        logger.info("Rolling deletion → %s | predicate: %s", target, predicate)
        self.spark.sql(delete_sql)
        logger.info("Rolling deletion complete → %s", target)

    def write_parquet(self, df, s3_path: str, mode: str = "overwrite",
                      partition_by: list = None, compression: str = "snappy") -> None:
        """Write DataFrame to parquet file(s) at S3 location.

        Args:
            df:           Transformed Spark DataFrame.
            s3_path:      Full S3 URI (bucket already prepended by caller).
            mode:         'overwrite' or 'append'.
            partition_by: Columns to partition output by.
            compression:  Parquet compression codec. Default 'snappy'.
        """
        logger.info(
            "Writing parquet | path='%s' | mode=%s | partition_by=%s",
            s3_path, mode, partition_by,
        )

        writer = df.write.mode(mode).option("compression", compression)
        if partition_by:
            writer = writer.partitionBy(*partition_by)
        writer.parquet(s3_path)

        logger.info("Parquet write complete | path='%s'", s3_path)

    # ── Public method ─────────────────────────────────────────────────────────

    def write(self, df: DataFrame) -> None:
        """
        Write transformed data to the Iceberg target table.

        Dispatch logic
        --------------
        table_type              operation       strategy
        ─────────────────────── ─────────────── ────────────────────────────────────
        NonTransactional_SCD2   day0            Full atomic Iceberg overwrite
        NonTransactional_SCD2   day1 | bau      SCD2 CDC two-phase merge
        NonTransactional_SCD1   day0            Full atomic Iceberg overwrite
        NonTransactional_SCD1   day1 | bau      SCD1 UPSERT (single-phase MERGE)
        Transactional           day0            INSERT OVERWRITE (partition rebuild)
        Transactional           day1 | bau      PK + partition MERGE (idempotent upsert)

        After the write strategy completes, rolling deletion is executed if
        configured (Transactional and SCD1 only — see _rolling_delete).

        Args:
            df: Transformed Spark DataFrame.
                Day 0: Must include ALL audit columns (transform derives them).
                       TargetWriter writes as-is without injecting audit columns.
                Day 1/BAU: Must NOT include audit columns (eff_start_date,
                       eff_end_date, active, dw_lod_tmp, dw_upd_lod_tmp) —
                       TargetWriter derives and injects them via CDC merge.
                Must include the partition column for Transactional tables.
        """
        if df is None:
            raise ValueError("DataFrame passed to TargetWriter.write() is None")

        # File target dispatch — when target_io is present, write parquet instead of table
        target_io = self.config.get('target_io')
        if target_io:
            s3_bucket = self.config.get('s3_bucket', '')
            s3_path = f"s3://{s3_bucket}/{target_io['path']}"
            self.write_parquet(
                df, s3_path,
                mode=target_io.get('write_mode', 'overwrite'),
                partition_by=target_io.get('partition_by', []),
                compression=target_io.get('compression', 'snappy'),
            )
            return  # Skip rolling_delete — not applicable to file targets

        table_type = self.table_type
        operation  = self.operation

        logger.info(
            "TargetWriter.write() | table=%s | table_type=%s | operation=%s",
            self._target_fqn, table_type, operation,
        )

        if table_type == 'Transactional':
            self._write_transactional(df)

        elif self._is_non_transactional:
            if operation == 'day0':
                self._write_non_transactional_day0(df)
            elif operation in ('day1', 'bau'):
                if self._is_scd1:
                    self._write_scd1_upsert(df)
                else:
                    self._write_cdc_merge(df)
            else:
                raise ValueError(
                    f"Unrecognised operation '{operation}' for Non-Transactional table. "
                    f"Expected: day0 | day1 | bau"
                )

        else:
            raise ValueError(
                f"Unrecognised table_type '{table_type}'. "
                f"Expected: Transactional | NonTransactional_SCD2 | NonTransactional_SCD1"
            )

        # Rolling deletion — prune old data after successful write
        # (Transactional + SCD1 only; no-op for SCD2 and when config absent)
        self._rolling_delete()
