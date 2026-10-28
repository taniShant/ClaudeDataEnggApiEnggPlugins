# === BLOCK: date_control_adhoc ===
def calculate_business_dates(
    process_name: str,
    target_table_name: str,
    **context,
):
    """
    For adhoc runs, curr_bus_dt MUST be provided via dag_run.conf.
    If not provided, falls back to logical_date.

    Note:
      prev_bus_dt and next_bus_dt are intentionally NOT computed here.
      The Databricks driver / Glue wrapper handles any offset logic
      internally via the date_control table.
    """

    dag_run = context.get("dag_run")
    dag_conf = dag_run.conf if dag_run and dag_run.conf else {}

    override_curr_bus_dt = dag_conf.get("curr_bus_dt")

    if override_curr_bus_dt:
        try:
            curr_date = datetime.strptime(override_curr_bus_dt, "%Y-%m-%d").date()
        except ValueError:
            raise AirflowException(
                f"Invalid curr_bus_dt: {override_curr_bus_dt}. Expected YYYY-MM-DD."
            )
        logger.info("Using overridden curr_bus_dt: %s", override_curr_bus_dt)
    else:
        curr_date = context["logical_date"].in_timezone(LOCAL_TZ).date()
        logger.info("No override. Using logical_date as curr_bus_dt: %s", curr_date)

    ti = context["ti"]
    ti.xcom_push(key="process_name", value=process_name)
    ti.xcom_push(key="target_table_name", value=target_table_name)
    ti.xcom_push(key="curr_bus_dt", value=str(curr_date))

    return {
        "process_name": process_name,
        "target_table_name": target_table_name,
        "curr_bus_dt": str(curr_date),
    }
# === END BLOCK ===
