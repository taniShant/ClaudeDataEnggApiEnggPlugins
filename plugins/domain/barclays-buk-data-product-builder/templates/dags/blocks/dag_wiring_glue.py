# === BLOCK: dag_wiring_glue ===
# Glue-specific external dependency wiring — injected into DAG definition
# when SOURCES_DB_TABLE_DETAILS or EXTERNAL_DAG_IDS are non-empty.
# This block sits INSIDE the `with DAG(...) as dag:` context, after glue_task_group creation.
# Requires: dynamodb_sensor block (if SOURCES_DB_TABLE_DETAILS), conf_helpers + external_dag_functions (if EXTERNAL_DAG_IDS)

    # -------------------------------------------------------------------------
    # DynamoDB GCPR sensors (for sources not on Airflow)
    # -------------------------------------------------------------------------

    dynamodb_sensors = []

    if SOURCES_DB_TABLE_DETAILS:
        for source in SOURCES_DB_TABLE_DETAILS:
            db_name = source["database"]
            tbl_name = source["table"]

            sensor = DynamoDBEntrySensor(
                task_id=f"check_{db_name}_{tbl_name}",
                db_name=db_name,
                table_name=tbl_name,
                business_date_task_id="glue_dtx_group.calculate_business_date",
                dynamodb_conn_id=DDB_CONN_ID,
                dag=dag,
                **_TASK_RETRY_KW,
            )
            dynamodb_sensors.append(sensor)

    # -------------------------------------------------------------------------
    # External DAG dependencies (with skip-absorbing gate)
    # -------------------------------------------------------------------------

    proceed_joins = []

    for ext_dag_id in EXTERNAL_DAG_IDS:
        if not ext_dag_id or str(ext_dag_id).lower() == "none":
            continue

        with TaskGroup(
            group_id=f"wait_for_{ext_dag_id}",
            dag=dag,
        ) as wait_group:

            check_wait_condition = ShortCircuitOperator(
                task_id="check_wait_condition",
                python_callable=_should_wait_for_external_dependency,
                ignore_downstream_trigger_rules=False,
                dag=dag,
                **_TASK_RETRY_KW,
            )

            await_upstream_completion = ExternalTaskSensor(
                task_id="await_upstream_completion",
                external_dag_id=ext_dag_id,
                external_task_id=None,
                allowed_states=["success"],
                failed_states=["failed"],
                mode="reschedule",
                timeout=20 * 60,
                poke_interval=120,
                check_existence=True,
                execution_date_fn=_execution_date_fn_factory(ext_dag_id),
                dag=dag,
                **_TASK_RETRY_KW,
            )

            upstream_ready = EmptyOperator(
                task_id="upstream_ready",
                dag=dag,
            )

            check_wait_condition >> await_upstream_completion >> upstream_ready

            check_skip_condition = ShortCircuitOperator(
                task_id="check_skip_condition",
                python_callable=_should_skip_external_dependency,
                ignore_downstream_trigger_rules=False,
                dag=dag,
                **_TASK_RETRY_KW,
            )

            skip_upstream_wait = EmptyOperator(
                task_id="skip_upstream_wait",
                dag=dag,
            )

            check_skip_condition >> skip_upstream_wait

            dependency_clear_to_proceed = EmptyOperator(
                task_id="dependency_clear_to_proceed",
                trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
                dag=dag,
            )

            upstream_ready >> dependency_clear_to_proceed
            skip_upstream_wait >> dependency_clear_to_proceed

        proceed_joins.append(dependency_clear_to_proceed)

    # -------------------------------------------------------------------------
    # Wire dependencies to Glue TaskGroup
    # -------------------------------------------------------------------------

    # DynamoDB sensors feed into the Glue group
    for sensor in dynamodb_sensors:
        sensor >> glue_task_group

    # External DAG gates feed into the Glue group
    for proceed_join in proceed_joins:
        proceed_join >> glue_task_group
# === END BLOCK ===
