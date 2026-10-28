import logging
import re
from datetime import date

logger = logging.getLogger(__name__)

# Error substrings that indicate an Iceberg metadata issue on a Glue/Hive table read.
# When any of these are present in the exception message, glue_read_table is retried
# with glue_read_icb_table and the row-level filter is applied post-read via .filter().
_ICEBERG_ERROR_SIGNALS = (
    'iceberg',
    'metadatafilenotfound',
    'nosuchkeyexception',
    'no such file or directory',
    'table not found in iceberg',
    'failed to open input stream',
)

# Standard BUK CDAO date columns that must be CAST to DATE before comparison in filter
# expressions. Pipeline-specific additions can be supplied via config['date_columns'].
_DATE_COLUMNS = frozenset({
    'eff_start_date',
    'eff_end_date',
    'dw_bus_dt',
})


class SourceReader:
    """
    Reads source data for a single Glue pipeline execution.

    Instantiated once per transform run; the same object is used for all source reads:

        reader = SourceReader(
            spark                 = spark,
            glue_read_table       = glue_read_table,
            glue_read_icb_table   = glue_read_icb_table,
            config                = config,
            param                 = param,
            current_business_date = current_business_date,
        )

        source_data = reader.read_source_data()          # Glue/Iceberg catalogue tables
        ref_df      = reader.read_csv('s3://bucket/ref/lookup.csv')  # S3 CSV reference file

    Public methods
    --------------
    read_source_data() -> dict
        Read all source tables declared in config['source'] and return a dict of DataFrames
        keyed by source table alias.

    read_csv(s3_path, ...) -> DataFrame
        Read a delimited flat file from an S3 location and return a Spark DataFrame.

    Supports both config layouts:
      - Single data flow (2-level):  source → table_type → alias → table_cfg
      - Multiple data flow (3-level):  source → source_system → table_type → alias → table_cfg
    Detection is automatic based on whether first-level keys are known table_type values.
    """

    # Recognised table_type keys. Any first-level key under config['source'] that is NOT
    # in this set is treated as a source_system grouping (multiple-data-flow config).
    _TABLE_TYPES = frozenset({
        'non-transactional',
        'non-transactional-scd1',
        'transactional',
    })

    def __init__(
        self,
        spark,
        glue_read_table,
        glue_read_icb_table,
        config: dict,
        param: list,
        current_business_date: date,
    ):
        """
        Args:
            spark:                  Active SparkSession.
            glue_read_table:        DTX-BYOC built-in; reads Glue/Hive table → DataFrame.
                                    Signature: glue_read_table(<db>.<table>, partitions_filter=None)
            glue_read_icb_table:    DTX-BYOC built-in; reads Iceberg table → DataFrame.
                                    Signature: glue_read_icb_table(<db>.<table>)
            config:                 Pipeline config dict loaded from config.json at runtime.
            param:                  Parsed param list from Glue job argument.
                                    param[0] = operation (day0 | day1 | bau)
                                    param[1] = table_type (NonTransactional_SCD2 | NonTransactional_SCD1 | Transactional)
            current_business_date:  Business date as a datetime.date object.
        """
        self.spark                = spark
        self.glue_read_table      = glue_read_table
        self.glue_read_icb_table  = glue_read_icb_table
        self.config               = config
        self.param                = param
        self.current_business_date = current_business_date
        self.operation            = param[0].strip().lower()
        # Catch-up mode override (set by wrapper when business_date lags system_date).
        # SourceReader uses this for filter resolution; TargetWriter uses self.operation.
        self._effective_operation  = config.get('_source_operation_override', self.operation)

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _is_iceberg_error(exc: Exception) -> bool:
        msg = str(exc).lower()
        return any(signal in msg for signal in _ICEBERG_ERROR_SIGNALS)

    def _apply_date_casts(self, filter_expr: str) -> str:
        """
        Rewrite date column comparisons to use CAST(col AS DATE) for type-safe evaluation.

        Transforms:
            <date_col> <op> '<YYYY-MM-DD>'
        into:
            CAST(<date_col> AS DATE) <op> CAST('<YYYY-MM-DD>' AS DATE)

        Date columns in scope:
          - Standard set (_DATE_COLUMNS): eff_start_date, eff_end_date, dw_bus_dt.
          - Pipeline-specific additions: config['date_columns'] list (optional).

        Operators handled: <=  >=  !=  <>  <  >  =

        Idempotent: columns already inside CAST(...) are skipped via a (?<!\()
        negative lookbehind — the opening paren of CAST( immediately precedes the
        column name, so the pattern does not match a second time.

        '1=1' and any expression that does not contain a date column reference are
        returned unchanged.
        """
        date_cols = _DATE_COLUMNS | set(self.config.get('date_columns', []))
        if not date_cols:
            return filter_expr

        # longest names first to avoid partial matches on shared substrings
        col_alts = '|'.join(re.escape(c) for c in sorted(date_cols, key=len, reverse=True))

        pattern = re.compile(
            r'(?<!\()'                        # not already inside CAST(
            r'\b(' + col_alts + r')\b'        # date column name
            r'\s*(<=|>=|!=|<>|<|>|=)\s*'      # comparison operator
            r"'(\d{4}-\d{2}-\d{2})'",         # ISO date literal
            re.IGNORECASE,
        )

        def _cast(m):
            col, op, date_val = m.group(1), m.group(2), m.group(3)
            return f"CAST({col} AS DATE) {op} CAST('{date_val}' AS DATE)"

        return pattern.sub(_cast, filter_expr)

    def _resolve_filter(self, table_type: str, table_alias: str, source_system: str = None):
        """
        Return the formatted filter expression for the given table type and alias.

        Filter resolution rules (three cases):
          1. Alias key NOT present in config section → default filter applied.
          2. Alias key IS present in config section  → that filter used exclusively;
             default is NOT merged. If you need both, write the combined expression
             explicitly in the alias entry.
          3. Alias key present with value '1=1'      → overrides default and results
             in no effective row restriction (passed to glue_read_table as-is;
             Glue silently ignores non-partition predicates).

        Key check uses `in` (not Python truthiness) so that a key that IS present
        in the config always wins over the default, regardless of its value.

        After resolving the expression, {current_business_date} is substituted and
        _apply_date_casts rewrites any date column comparisons to use CAST(col AS DATE).

        Supports both filter layouts:
          Single data flow: filters.<op>.<table_type>.<alias|default>
          Multiple data flow:  filters.<op>.<source_system>.<table_type>.<alias|default>

        Args:
            table_type:    e.g. 'non-transactional', 'transactional'
            table_alias:   source table alias key
            source_system: source system name (None for single-data-flow configs)
        """
        # Use _effective_operation for filter lookup (catch_up_mode override when active).
        # bau shares the same filter section as day1.
        op_key     = 'day1' if self._effective_operation == 'bau' else self._effective_operation
        op_filters = self.config.get('filters', {}).get(op_key, {})

        # Multiple data flow: filters → op → source_system → table_type → alias
        # Single data flow: filters → op → table_type → alias
        if source_system:
            op_filters = op_filters.get(source_system, {})

        section = op_filters.get(table_type, {})

        # key-presence check — not truthiness — so an explicit alias entry always wins
        expr = section[table_alias] if table_alias in section else section.get('default')
        if expr:
            formatted = expr.replace('{current_business_date}', self.current_business_date.isoformat())
            return self._apply_date_casts(formatted)
        return None

    def _read_single_table(self, table_ref: str, partitions_filter, columns: list):
        """
        Read one source table, falling back to glue_read_icb_table on Iceberg metadata errors.

        Both paths (glue_read_table and glue_read_icb_table) read the full table first,
        then apply partitions_filter as a post-read .filter() clause:
          - None   → .filter() skipped entirely — all rows returned.
          - '1=1'  → df.filter('1=1') applied — all rows returned (no-op predicate).
          - real   → df.filter(expr) applied — rows matching the expression returned.

        The filter is ALWAYS forwarded as resolved — never suppressed or rewritten here.

        - Column pruning (.select) applied after filter on both paths.
        """
        try:
            df = self.glue_read_table(table_ref)
            if partitions_filter:
                df = df.filter(partitions_filter)
            logger.info("glue_read_table succeeded for '%s' | filter: %s", table_ref, partitions_filter)
        except Exception as exc:
            if self._is_iceberg_error(exc):
                logger.warning(
                    "glue_read_table failed with Iceberg metadata error for '%s' — "
                    "retrying with glue_read_icb_table. Original error: %s",
                    table_ref, exc,
                )
                df = self.glue_read_icb_table(table_ref)
                if partitions_filter:
                    df = df.filter(partitions_filter)
                logger.info("glue_read_icb_table succeeded for '%s'", table_ref)
            else:
                raise

        if columns:
            df = df.select(columns)

        return df

    # ── Public methods ────────────────────────────────────────────────────────

    def read_source_data(self) -> dict:
        """
        Read all source tables defined in config and return as a dictionary of DataFrames.

        Fully generic — driven entirely by config contents:
          - Any number of source tables under non-transactional and transactional sections.
          - Any number of columns per table (empty list = read all columns; no column pruning applied).
          - Any number of filter entries per operation/table-type section; table-specific filter
            entries override 'default' for that alias only; remaining tables use 'default'.

        Partition filtering and column pruning are applied upfront for each table:
          - non-transactional: partition filter = active = '1'  (day1/bau)
                               partition filter = eff_start_date range (day0)
          - transactional:     partition filter = dw_bus_dt = '{current_business_date}'  (day1/bau)
                               partition filter = dw_bus_dt range  (day0)
        Filter expressions are sourced from config['filters'] and formatted with current_business_date.

        If glue_read_table raises an Iceberg metadata error the read is retried transparently
        with glue_read_icb_table; the filter is then applied as a post-read DataFrame .filter().

        Supports both config layouts automatically:
          - Single data flow: source → table_type → alias → table_cfg
          - Multiple data flow:  source → source_system → table_type → alias → table_cfg

        Returns:
            source_data (dict): keyed by source table alias → Spark DataFrame.
        """
        source_cfg  = self.config.get('source', {})
        source_data = {}

        for key, value in source_cfg.items():
            if not value:
                continue

            if key in self._TABLE_TYPES:
                # Single data flow layout: key is table_type directly
                self._read_tables_for_type(key, value, source_data, source_system=None)
            elif key == 'file':
                continue  # File sources handled separately below
            else:
                # Multiple data flow layout: key is source_system, value contains table_type dicts
                for table_type, tables in value.items():
                    if not tables:
                        continue
                    self._read_tables_for_type(table_type, tables, source_data, source_system=key)

        # File-based sources (parquet): source → file → alias → file_cfg
        s3_bucket = self.config.get('s3_bucket', '')
        for alias, file_cfg in source_cfg.get('file', {}).items():
            # Relative path → full S3 URI (same as staging path resolution)
            s3_path = f"s3://{s3_bucket}/{file_cfg['path']}"
            columns = file_cfg.get('columns', [])
            filter_expr = file_cfg.get('filter')

            logger.info(
                "Reading file source '%s' | path=%s | columns=%s",
                alias, s3_path, columns,
            )

            source_data[alias] = self.read_parquet(s3_path, columns, filter_expr)

        logger.info("read_source_data complete — %d source table(s) loaded", len(source_data))
        return source_data

    def _read_tables_for_type(self, table_type: str, tables: dict, source_data: dict, source_system: str = None):
        """
        Read all tables under a single table_type section into source_data.

        Args:
            table_type:    'non-transactional', 'non-transactional-scd1', or 'transactional'
            tables:        Dict of alias → table_cfg
            source_data:   Accumulator dict to populate (alias → DataFrame)
            source_system: Source system name (None for single-data-flow configs)
        """
        for alias, table_cfg in tables.items():
            table_ref         = table_cfg['table']
            columns           = table_cfg.get('columns', [])
            partitions_filter = self._resolve_filter(table_type, alias, source_system)

            logger.info(
                "Reading '%s' | type=%s | source_system=%s | operation=%s | filter=%s | columns=%s",
                table_ref, table_type, source_system or 'default', self.operation, partitions_filter, columns,
            )

            source_data[alias] = self._read_single_table(table_ref, partitions_filter, columns)

    def read_csv(
        self,
        s3_path: str,
        header: bool = True,
        delimiter: str = ',',
        infer_schema: bool = True,
        columns: list = None,
    ):
        """
        Read a delimited flat file from an S3 location and return a Spark DataFrame.

        Intended for reference/lookup files stored in S3 that are not catalogue tables
        (e.g. static code mappings, threshold files, external reference data).

        Args:
            s3_path:      Full S3 URI to the CSV file or directory prefix.
                          Examples:
                            's3://my-bucket/ref/country_codes.csv'
                            's3://my-bucket/ref/thresholds/'  (reads all files in prefix)
            header:       Treat the first row as a column header. Default True.
            delimiter:    Column separator character. Default ',' (comma).
                          Use '|' for pipe-delimited, '\\t' for tab-delimited files.
            infer_schema: Infer column data types from the file content. Default True.
                          Set False when schema is known — avoids an extra full-file scan
                          and returns all columns as StringType instead.
            columns:      Optional list of column names to retain after the read.
                          None or empty list = return all columns.

        Returns:
            Spark DataFrame.
        """
        logger.info(
            "Reading CSV | path='%s' | header=%s | delimiter='%s' | infer_schema=%s",
            s3_path, header, delimiter, infer_schema,
        )

        df = (
            self.spark.read
            .option('header', str(header).lower())
            .option('sep', delimiter)
            .option('inferSchema', str(infer_schema).lower())
            .csv(s3_path)
        )

        if columns:
            df = df.select(columns)

        logger.info(
            "CSV read complete | path='%s' | rows(approx): unpersisted | schema: %s",
            s3_path, df.schema.simpleString(),
        )
        return df

    def read_parquet(
        self,
        s3_path: str,
        columns: list = None,
        filter_condition: str = None,
    ):
        """
        Read parquet file(s) from an S3 location and return a Spark DataFrame.

        Intended for file-based data sources stored in S3 as parquet format
        (e.g. shared datasets, file-based feeds from upstream systems).

        Args:
            s3_path:          Full S3 URI to the parquet file or directory prefix.
                              Examples:
                                's3://my-bucket/raw/customer_events/'
                                's3://my-bucket/ref/product_data/'
            columns:          Optional list of column names to retain after the read.
                              None or empty list = return all columns.
            filter_condition: Optional Spark SQL filter expression applied post-read.

        Returns:
            Spark DataFrame.
        """
        logger.info(
            "Reading parquet | path='%s' | filter=%s",
            s3_path, filter_condition,
        )

        df = self.spark.read.parquet(s3_path)

        if filter_condition:
            df = df.filter(filter_condition)
        if columns:
            df = df.select(columns)

        logger.info(
            "Parquet read complete | path='%s' | schema: %s",
            s3_path, df.schema.simpleString(),
        )
        return df
