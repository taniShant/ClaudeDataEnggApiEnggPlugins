# === BLOCK: date_control ===
def calculate_business_dates(
    process_name: str,
    target_table_name: str,
    **context,
):
    """
    Calculates date-control values for this DAG instance.

    Final rule:
      curr_bus_dt = Airflow/Astronomer logical_date

    This is because, in the current Astronomer setup, the logical_date already
    represents the intended business date.

    Example:
      Actual run date = 2026-07-03
      logical_date    = 2026-07-02
      curr_bus_dt     = 2026-07-02

    Manual override:
      If the DAG is triggered with:

      {
        "curr_bus_dt": "2026-05-15"
      }

      then curr_bus_dt will be taken from dag_run.conf instead of logical_date.

    Note:
      prev_bus_dt and next_bus_dt are intentionally NOT computed here.
      The Databricks driver / Glue wrapper handles any offset logic
      internally via the date_control table. If a future job requires
      prev/next dates, compute them in the driver notebook using curr_bus_dt.
    """

    dag_run = context.get("dag_run")
    dag_conf = dag_run.conf if dag_run and dag_run.conf else {}

    override_curr_bus_dt = dag_conf.get("curr_bus_dt")

    if override_curr_bus_dt:
        try:
            curr_date = datetime.strptime(
                override_curr_bus_dt,
                "%Y-%m-%d",
            ).date()
        except ValueError:
            raise AirflowException(
                f"Invalid curr_bus_dt override: {override_curr_bus_dt}. "
                "Expected format YYYY-MM-DD."
            )

        logger.info(
            "Using overridden curr_bus_dt from dag_run.conf: %s",
            override_curr_bus_dt,
        )

    else:
        logical_date = context["logical_date"].in_timezone(LOCAL_TZ).date()

        # Final agreed rule:
        # logical_date already represents intended business date.
        curr_date = logical_date

        logger.info(
            "No override provided. Using logical_date as curr_bus_dt: %s",
            curr_date,
        )

    curr_bus_dt = str(curr_date)

    ti = context["ti"]

    ti.xcom_push(key="process_name", value=process_name)
    ti.xcom_push(key="target_table_name", value=target_table_name)
    ti.xcom_push(key="curr_bus_dt", value=curr_bus_dt)

    logger.info("Resolved date-control values:")
    logger.info("process_name=%s", process_name)
    logger.info("target_table_name=%s", target_table_name)
    logger.info("curr_bus_dt=%s", curr_bus_dt)

    return {
        "process_name": process_name,
        "target_table_name": target_table_name,
        "curr_bus_dt": curr_bus_dt,
    }
# === END BLOCK ===
