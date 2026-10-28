# Databricks notebook source
# DBTITLE 1,Parameters
import re

dbutils.widgets.text("catalog", "{{target_catalog}}")
dbutils.widgets.text("schema", "{{target_schema}}")

CATALOG = dbutils.widgets.get("catalog").strip()
SCHEMA = dbutils.widgets.get("schema").strip()

if not CATALOG or not SCHEMA:
    raise ValueError("catalog and schema parameters must be provided and non-empty")

print(f"Deploying volumes to: {CATALOG}.{SCHEMA}")

# COMMAND ----------

# DBTITLE 1,Catalog/Schema Validation
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

# COMMAND ----------

# DBTITLE 1,Volume Definitions
# Define volumes as requested. Add or remove entries as needed.
ddl_statements = [
{{volume_ddl_statements}}
]

# COMMAND ----------

# DBTITLE 1,Execute DDL
for i, ddl in enumerate(ddl_statements, start=1):
    VOLUME_NAME = re.search(rf'{re.escape(CATALOG)}\.{re.escape(SCHEMA)}\.(\w+)', ddl)
    VOLUME_NAME = VOLUME_NAME.group(1)
    print(f"Executing DDL {i}/{len(ddl_statements)} ...")
    spark.sql(ddl)
    print(f"Volume {CATALOG}.{SCHEMA}.{VOLUME_NAME} created successfully.")
