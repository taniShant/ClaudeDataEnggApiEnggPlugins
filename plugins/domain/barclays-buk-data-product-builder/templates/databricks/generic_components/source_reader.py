# Databricks notebook source
# COMMAND ----------
from pyspark.sql import SparkSession, DataFrame


class SourceReader:
    """
    Reads source data for a single Databricks pipeline execution.
    Config-driven — iterates source entries and applies appropriate filters.
    Uses spark.table() directly (no tableIOUtils dependency for reads).

    Supports both config layouts automatically:
      - Single data flow (2-level):  source → table_type → alias → table_cfg
      - Multiple data flow (3-level):  source → source_system → table_type → alias → table_cfg
    Detection is automatic based on whether first-level keys are known table_type values.
    """

    # Recognised table_type keys. Any first-level key under config['source'] that is NOT
    # in this set is treated as a source_system grouping (multiple-data-flow config).
    _TABLE_TYPES = frozenset({
        'non_transactional',
        'non_transactional_scd1',
        'transactional',
    })

    def __init__(self, spark: SparkSession, config: dict, operation: str, curr_bus_dt: str):
        """
        Args:
            spark:        Active SparkSession
            config:       Pipeline config dict (loaded from config.yml)
            operation:    "day0" | "day1" | "bau"
            curr_bus_dt:  Current business date as ISO string (YYYY-MM-DD)
        """
        self.spark = spark
        self.config = config
        self.operation = operation.strip().lower()
        # Catch-up mode override (set by driver when business_date lags system_date).
        # SourceReader uses this for filter resolution; TargetWriter is unaffected
        # (its write strategy comes from config["pipeline"]["load_type"], not _effective_operation).
        self._effective_operation = config.get("_source_operation_override", self.operation)
        self.curr_bus_dt = curr_bus_dt

    def _resolve_filter(self, table_type: str, table_alias: str, source_system: str = None):
        """
        Resolve filter for a given table type and alias from config.

        3-case logic:
          1. Alias key absent → use 'default' filter
          2. Alias key present → use that filter exclusively (default NOT merged)
          3. Alias key = '1=1' → no restriction

        Supports both filter layouts:
          Single data flow: filters.<op>.<table_type>.<alias|default>
          Multiple data flow:  filters.<op>.<source_system>.<table_type>.<alias|default>

        Args:
            table_type:    e.g. 'non_transactional', 'transactional'
            table_alias:   source table alias key
            source_system: source system name (None for single-data-flow configs)
        """
        # Use _effective_operation for filter lookup (catch_up_mode override when active).
        # bau shares the same filter section as day1.
        op_key = "day1" if self._effective_operation == "bau" else self._effective_operation
        op_filters = self.config.get("filters", {}).get(op_key, {})

        # Multiple data flow: filters → op → source_system → table_type → alias
        if source_system:
            op_filters = op_filters.get(source_system, {})

        section = op_filters.get(table_type, {})

        expr = section[table_alias] if table_alias in section else section.get("default")
        if expr:
            return expr.replace("{current_business_date}", self.curr_bus_dt)
        return None

    def _resolve_table_fqn(self, table_cfg: dict) -> str:
        """
        Resolve fully-qualified table name from config entry.

        Supports two modes:
          1. catalog_key mode (multi-env): table_cfg has 'catalog_key' and 'table'
             (schema.table). Catalog resolved from config['source_catalogs'][key].
          2. Legacy mode: table_cfg['table'] already contains full FQN
             (catalog.schema.table).
        """
        catalog_key = table_cfg.get("catalog_key")
        table_path = table_cfg["table"]

        if catalog_key:
            # Multi-env mode — resolve catalog from source_catalogs mapping
            source_catalogs = self.config.get("source_catalogs", {})
            catalog = source_catalogs.get(catalog_key)
            if not catalog:
                raise ValueError(
                    f"Catalog key '{catalog_key}' not found in source_catalogs. "
                    f"Available keys: {list(source_catalogs.keys())}"
                )
            return f"{catalog}.{table_path}"

        # Legacy mode — table already has full FQN
        return table_path

    def read_source_data(self) -> dict:
        """
        Read all source tables from config['source'] with appropriate filters.
        Returns dict keyed by source table alias → DataFrame.

        Supports both config layouts automatically:
          - Single data flow: source → table_type → alias → table_cfg
          - Multiple data flow:  source → source_system → table_type → alias → table_cfg

        Also supports both table reference modes:
          - Legacy configs (table has full catalog.schema.table FQN)
          - Multi-env configs (table has schema.table, catalog resolved via catalog_key)
        """
        source_cfg = self.config.get("source", {})
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
        for alias, file_cfg in source_cfg.get('file', {}).items():
            path = file_cfg['path']
            columns = file_cfg.get('columns', [])
            filter_expr = file_cfg.get('filter')
            source_data[alias] = self.read_parquet(path, columns, filter_expr)

        return source_data

    def _read_tables_for_type(self, table_type: str, tables: dict, source_data: dict, source_system: str = None):
        """
        Read all tables under a single table_type section into source_data.

        Args:
            table_type:    'non_transactional' or 'transactional'
            tables:        Dict of alias → table_cfg
            source_data:   Accumulator dict to populate (alias → DataFrame)
            source_system: Source system name (None for single-data-flow configs)
        """
        for alias, table_cfg in tables.items():
            table_fqn = self._resolve_table_fqn(table_cfg)
            columns = table_cfg.get("columns", [])
            filter_expr = self._resolve_filter(table_type, alias, source_system)

            df = self.spark.table(table_fqn)
            if filter_expr:
                df = df.filter(filter_expr)
            if columns:
                df = df.select(columns)

            source_data[alias] = df

    def read_table(self, table_fqn: str, filter_condition: str = None, columns: list = None) -> DataFrame:
        """Read a single Unity Catalog table (ad-hoc, not from config)."""
        df = self.spark.table(table_fqn)
        if filter_condition:
            df = df.filter(filter_condition)
        if columns:
            df = df.select(columns)
        return df

    def read_csv(self, path: str, header: bool = True, delimiter: str = ",",
                 infer_schema: bool = True, columns: list = None) -> DataFrame:
        """Read CSV/delimited file from Volumes or external location."""
        df = (
            self.spark.read
            .option("header", str(header).lower())
            .option("delimiter", delimiter)
            .option("inferSchema", str(infer_schema).lower())
            .csv(path)
        )
        if columns:
            df = df.select(columns)
        return df

    def read_parquet(self, path: str, columns: list = None,
                     filter_condition: str = None) -> DataFrame:
        """Read parquet file(s) from Volumes or external location.

        Args:
            path:             Volume path or external location.
                              Examples:
                                '/Volumes/catalog/schema/volume/customer_events/'
                                'abfss://container@account.dfs.core.windows.net/path/'
            columns:          Optional list of column names to retain after the read.
                              None or empty list = return all columns.
            filter_condition: Optional Spark SQL filter expression applied post-read.

        Returns:
            Spark DataFrame.
        """
        df = self.spark.read.parquet(path)
        if filter_condition:
            df = df.filter(filter_condition)
        if columns:
            df = df.select(columns)
        return df
