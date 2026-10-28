# Databricks notebook source
# DBTITLE 1,Parameters
dbutils.widgets.text("catalog", "{{target_catalog}}")
dbutils.widgets.text("schema", "{{target_schema}}")

CATALOG = dbutils.widgets.get("catalog").strip()
SCHEMA = dbutils.widgets.get("schema").strip()

if not CATALOG or not SCHEMA:
    raise ValueError("catalog and schema parameters must be provided and non-empty")

print(f"Deploying tables to: {CATALOG}.{SCHEMA}")

# COMMAND ----------

# DBTITLE 1,Catalog/Schema Validation
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

# COMMAND ----------

# DBTITLE 1,DDL Statements
ddl_statements = [
{{generated_ddl_list}},
f"""
CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.date_control (
  tenancy_name STRING COMMENT 'Tenancy name',
  process_frequency STRING COMMENT 'How often the process runs',
  data_product_type STRING COMMENT 'Type of product',
  prev_date DATE COMMENT 'Previous business date',
  curr_date DATE COMMENT 'Current business date',
  next_date DATE COMMENT 'Next business date',
  dw_load_tmp TIMESTAMP COMMENT 'Load timestamp',
  process_name STRING COMMENT 'Partition column'
)
USING iceberg
PARTITIONED BY (process_name)
""",
f"""
CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.audit_log (
  audit_id STRING,
  catalog_name STRING,
  schema_name STRING,
  table_name STRING,
  process_name STRING,
  business_date STRING,
  run_timestamp TIMESTAMP,
  rows_inserted BIGINT,
  rows_updated BIGINT,
  rows_deleted BIGINT,
  rows_unchanged BIGINT,
  status STRING,
  message STRING
)
USING iceberg
PARTITIONED BY (process_name)
"""
]

# COMMAND ----------

# DBTITLE 1,Execute DDL
for i, ddl in enumerate(ddl_statements, start=1):
    print(f"Executing DDL {i}/{len(ddl_statements)} ...")
    spark.sql(ddl)

print("DDL execution complete.")
