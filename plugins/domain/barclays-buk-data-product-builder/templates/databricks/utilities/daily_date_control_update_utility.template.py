# Databricks notebook source
# DBTITLE 1,Date Control Update
from databricks_foundation.core.date_control import DateControl

dc = DateControl(spark)

dbutils.widgets.text("catalog", "{{target_catalog}}")
dbutils.widgets.text("schema", "{{target_schema}}")

CATALOG = dbutils.widgets.get("catalog").strip()
SCHEMA = dbutils.widgets.get("schema").strip()

TABLE_NM_FQN = f"{CATALOG}.{SCHEMA}.date_control"
PROCESS_NAME = "{{target_schema}}_{{table_name}}"

result = dc.update_date_control(
    table_nm=TABLE_NM_FQN,
    process_name=PROCESS_NAME
)

print("Update result:", result)
