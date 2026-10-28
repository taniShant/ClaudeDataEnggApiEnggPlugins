# === BLOCK: taskgroup_databricks ===

def databricks_job_group(
    name: str,
    task_cfg: dict,
    dag: DAG,
):
    """
    Creates one Databricks TaskGroup (job execution only).

    Date calculation is handled separately at DAG level to avoid
    unnecessary dependency sensor re-runs if date calc fails.

    Task order inside group:
      1. run_databricks_job
    """

    job_name = task_cfg.get("job_name")

    if not job_name:
        raise AirflowException(f"job_name is missing for task: {name}")

    static_notebook_params = task_cfg.get("notebook_params", {}) or {}

    with TaskGroup(
        group_id=f"{name}_group",
        dag=dag,
    ) as group:

        # Build dynamic params only for parameters the job accepts.
        # job_accepted_params: {job_param_name -> xcom_key}
        # e.g. {"business_date": "curr_bus_dt"} for standard driver
        dynamic_notebook_params = {}
        job_accepted_params = task_cfg.get("job_accepted_params") or {"business_date": "curr_bus_dt"}
        for param_name, xcom_key in job_accepted_params.items():
            dynamic_notebook_params[param_name] = (
                "{{ ti.xcom_pull(task_ids='calculate_business_dates', key='"
                + xcom_key
                + "') }}"
            )

        notebook_params = {
            **static_notebook_params,
            **dynamic_notebook_params,
        }

        run_databricks_job = DatabricksRunNowOperator(
            task_id="run_databricks_job",
            databricks_conn_id=DATABRICKS_CONN_ID,
            job_name=job_name,
            notebook_params=notebook_params,
            dag=dag,
            trigger_rule=TriggerRule.ALL_SUCCESS,
            **_TASK_RETRY_KW,
        )

    return group

# === END BLOCK ===
