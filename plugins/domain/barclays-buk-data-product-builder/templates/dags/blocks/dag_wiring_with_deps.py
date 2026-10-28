# === BLOCK: dag_wiring_with_deps ===
# External dependency wiring — injected into DAG definition when any external deps exist.
# Contains DynamoDB GCPR, Cross-Deployment, and ExternalTaskSensor wiring loops.
# This block is included INSIDE the `with DAG(...) as dag:` context, after TaskGroup creation.
# Requires: conf_helpers block (for _should_wait/skip), sensor blocks as needed.
#
# The agent inserts this block into the skeleton's DAG definition section.
# The skeleton handles: created_tasks dict, task iteration, internal dependency wiring.
# This block handles: external dependency wiring per task.

    for task_name, task_cfg in TASKS_CONFIG.items():
        current_group = created_tasks.get(task_name)

        if not current_group:
            continue

        upstream_external = (task_cfg or {}).get("upstream_dag", {}) or {}

        proceed_joins = []

        for ext_dag_id, ext_cfg in upstream_external.items():
            if not ext_dag_id or str(ext_dag_id).lower() == "none":
                continue

            dep_type = (ext_cfg or {}).get("type", "dag_sensor")

            # ── DynamoDB GCPR check (upstream NOT on Airflow) ──
            if dep_type == "dynamodb":
                db_name = (ext_cfg or {}).get("database", "")
                tbl_name = (ext_cfg or {}).get("table", "")
                safe_name = f"{db_name}_{tbl_name}".replace(".", "_")

                with TaskGroup(
                    group_id=f"wait_for_{task_name}_dynamodb_{safe_name}",
                    dag=dag,
                ) as wait_group:

                    check_wait_condition = ShortCircuitOperator(
                        task_id="check_wait_condition",
                        python_callable=_should_wait_for_external_dependency,
                        ignore_downstream_trigger_rules=False,
                        dag=dag,
                        **_TASK_RETRY_KW,
                    )

                    # Determine source layer: base layer = e_* prefix, otherwise DDA
                    source_layer = "base" if db_name.startswith("e_") else "dda"

                    dynamodb_conn_id = AWS_CFG["conn_id_ddb_base"] if source_layer == "base" else AWS_CFG["conn_id_ddb_dda"]

                    check_dynamodb = DynamoDBEntrySensor(
                        task_id="check_dynamodb_gcpr",
                        db_name=db_name,
                        table_name=tbl_name,
                        business_date_task_id="calculate_business_dates",
                        dynamodb_conn_id=dynamodb_conn_id,
                        source_layer=source_layer,
                        mode="reschedule",
                        poke_interval=SENSOR_CFG["dynamodb_poke_interval_seconds"],
                        timeout=SENSOR_CFG["dynamodb_timeout_seconds"],
                        dag=dag,
                    )

                    upstream_ready = EmptyOperator(task_id="upstream_ready", dag=dag)
                    check_wait_condition >> check_dynamodb >> upstream_ready

                    check_skip_condition = ShortCircuitOperator(
                        task_id="check_skip_condition",
                        python_callable=_should_skip_external_dependency,
                        ignore_downstream_trigger_rules=False,
                        dag=dag,
                        **_TASK_RETRY_KW,
                    )
                    skip_upstream_wait = EmptyOperator(task_id="skip_upstream_wait", dag=dag)
                    check_skip_condition >> skip_upstream_wait

                    dependency_clear_to_proceed = EmptyOperator(
                        task_id="dependency_clear_to_proceed",
                        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
                        dag=dag,
                    )
                    upstream_ready >> dependency_clear_to_proceed
                    skip_upstream_wait >> dependency_clear_to_proceed

                proceed_joins.append(dependency_clear_to_proceed)

            # ── Cross-deployment sensor (upstream on DIFFERENT Astronomer) ──
            elif dep_type == "cross_deployment":
                tenancy_nm = (ext_cfg or {}).get("tenancy_name", "")
                api_token_var = (ext_cfg or {}).get("api_token_env_var", "")
                dep_url = (ext_cfg or {}).get("deployment_url_pattern",
                    "https://deployments.buk-dev-emea-astro.barcapint.com/{tenancy}/airflow")
                upstream_task_id = (ext_cfg or {}).get("upstream_dag_task")

                with TaskGroup(
                    group_id=f"wait_for_{task_name}_xdep_{ext_dag_id}",
                    dag=dag,
                ) as wait_group:

                    check_wait_condition = ShortCircuitOperator(
                        task_id="check_wait_condition",
                        python_callable=_should_wait_for_external_dependency,
                        ignore_downstream_trigger_rules=False,
                        dag=dag,
                        **_TASK_RETRY_KW,
                    )

                    await_cross_dep = CrossDeploymentDagSensor(
                        task_id="await_cross_deployment",
                        tenancy_name=tenancy_nm,
                        external_dag_id=ext_dag_id,
                        api_token_env_var=api_token_var,
                        deployment_url_pattern=dep_url,
                        upstream_task=upstream_task_id,
                        poke_interval=SENSOR_CFG["cross_deployment_poke_interval_seconds"],
                        timeout=SENSOR_CFG["cross_deployment_timeout_seconds"],
                        mode="poke",
                        dag=dag,
                    )

                    upstream_ready = EmptyOperator(task_id="upstream_ready", dag=dag)
                    check_wait_condition >> await_cross_dep >> upstream_ready

                    check_skip_condition = ShortCircuitOperator(
                        task_id="check_skip_condition",
                        python_callable=_should_skip_external_dependency,
                        ignore_downstream_trigger_rules=False,
                        dag=dag,
                        **_TASK_RETRY_KW,
                    )
                    skip_upstream_wait = EmptyOperator(task_id="skip_upstream_wait", dag=dag)
                    check_skip_condition >> skip_upstream_wait

                    dependency_clear_to_proceed = EmptyOperator(
                        task_id="dependency_clear_to_proceed",
                        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
                        dag=dag,
                    )
                    upstream_ready >> dependency_clear_to_proceed
                    skip_upstream_wait >> dependency_clear_to_proceed

                proceed_joins.append(dependency_clear_to_proceed)

            # ── DAG sensor (upstream on SAME Astronomer deployment) ──
            else:
                ext_tasks = _normalise_external_tasks(
                    (ext_cfg or {}).get("upstream_dag_task")
                )

                for ext_task in ext_tasks:
                    safe_ext_task_name = ext_task or "dag"

                    with TaskGroup(
                        group_id=f"wait_for_{task_name}_{ext_dag_id}_{safe_ext_task_name}",
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
                            external_task_id=ext_task,
                            allowed_states=["success"],
                            failed_states=["failed"],
                            mode="reschedule",
                            poke_interval=SENSOR_CFG["dag_sensor_poke_interval_seconds"],
                            timeout=SENSOR_CFG["dag_sensor_timeout_seconds"],
                            check_existence=False,
                            execution_date_fn=_execution_date_fn_factory(ext_dag_id),
                            dag=dag,
                            **_TASK_RETRY_KW,
                        )

                        upstream_ready = EmptyOperator(task_id="upstream_ready", dag=dag)
                        check_wait_condition >> await_upstream_completion >> upstream_ready

                        check_skip_condition = ShortCircuitOperator(
                            task_id="check_skip_condition",
                            python_callable=_should_skip_external_dependency,
                            ignore_downstream_trigger_rules=False,
                            dag=dag,
                            **_TASK_RETRY_KW,
                        )
                        skip_upstream_wait = EmptyOperator(task_id="skip_upstream_wait", dag=dag)
                        check_skip_condition >> skip_upstream_wait

                        dependency_clear_to_proceed = EmptyOperator(
                            task_id="dependency_clear_to_proceed",
                            trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
                            dag=dag,
                        )
                        upstream_ready >> dependency_clear_to_proceed
                        skip_upstream_wait >> dependency_clear_to_proceed

                    proceed_joins.append(dependency_clear_to_proceed)

        if proceed_joins:
            for proceed_join in proceed_joins:
                check_not_holiday >> calculate_dates >> proceed_join >> current_group
        else:
            check_not_holiday >> calculate_dates >> current_group
# === END BLOCK ===
