# === BLOCK: taskgroup_databricks_selfcontained ===

def databricks_job_group(
    name: str,
    task_cfg: dict,
    dag: DAG,
):
    """
    Creates one Databricks TaskGroup.

    Task order inside group:
      1. calculate_business_dates
      2. run_databricks_job
    """

    process_name = task_cfg.get("process_name")
    target_table_name = task_cfg.get("target_table_name")
    job_name = task_cfg.get("job_name")

    if not process_name:
        raise AirflowException(f"process_name is missing for task: {name}")

    if not target_table_name:
        raise AirflowException(f"target_table_name is missing for task: {name}")

    if not job_name:
        raise AirflowException(f"job_name is missing for task: {name}")

    static_notebook_params = task_cfg.get("notebook_params", {}) or {}

    with TaskGroup(
        group_id=f"{name}_group",
        dag=dag,
    ) as group:

        calculate_dates = PythonOperator(
            task_id="calculate_business_dates",
            python_callable=calculate_business_dates,
            op_kwargs={
                "process_name": process_name,
                "target_table_name": target_table_name,
            },
            dag=dag,
            **_TASK_RETRY_KW,
        )

        # Build dynamic params only for parameters the job accepts.
        # job_accepted_params: {job_param_name -> xcom_key}
        # e.g. {"business_date": "curr_bus_dt"} for standard driver
        dynamic_notebook_params = {}
        job_accepted_params = task_cfg.get("job_accepted_params") or {"business_date": "curr_bus_dt"}
        for param_name, xcom_key in job_accepted_params.items():
            dynamic_notebook_params[param_name] = (
                "{{ ti.xcom_pull(task_ids='"
                + name + "_group.calculate_business_dates"
                + "', key='" + xcom_key + "') }}"
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

        calculate_dates >> run_databricks_job

    return group

# === END BLOCK ===
