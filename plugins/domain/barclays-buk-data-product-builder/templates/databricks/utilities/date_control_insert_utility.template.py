# Databricks notebook source
# DBTITLE 1,Parameters
from databricks_foundation.core.date_control import DateControl
from datetime import datetime

dc = DateControl(spark)

dbutils.widgets.text("catalog", "{{target_catalog}}")
dbutils.widgets.text("schema", "{{target_schema}}")
dbutils.widgets.text("business_date", "")

CATALOG = dbutils.widgets.get("catalog").strip()
SCHEMA = dbutils.widgets.get("schema").strip()
business_date_str = dbutils.widgets.get("business_date").strip()

if not business_date_str:
    raise ValueError("business_date parameter must be provided (format: YYYY-MM-DD)")

CURR_DATE = datetime.strptime(business_date_str, "%Y-%m-%d").date()
TABLE_NM_FQN = f"{CATALOG}.{SCHEMA}.date_control"

# COMMAND ----------

# DBTITLE 1,Process Definitions
# Each entry represents a target table process requiring date control seeding.
# When a new target table is added, append its entry here.
processes = [
{{generated_process_list}}
]

# COMMAND ----------

# DBTITLE 1,Insert Date Control
for process in processes:
    result = dc.insert_date_control_if_missing(
        table_nm=TABLE_NM_FQN,
        tenancy_name=process["tenancy_name"],
        process_name=process["process_name"],
        data_product_type=process["data_product_type"],
        process_frequency=process["process_frequency"],
        curr_date=CURR_DATE
    )
    print(f"[{process['process_name']}] Insert result: {result}")
