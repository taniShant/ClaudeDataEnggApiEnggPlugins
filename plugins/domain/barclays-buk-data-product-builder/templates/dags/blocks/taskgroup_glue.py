# === BLOCK: taskgroup_glue ===

SFN_POKE = 60
SFN_TIMEOUT = 3600
GLUE_POKE = 60
GLUE_TIMEOUT = 7200
GLUE_DETAILS_POKE = 30
GLUE_DETAILS_TIMEOUT = 1800


def glue_lambda_sfn_group(name: str, dag: DAG):
    """
    Creates one Glue orchestration TaskGroup.

    Task order inside group:
      1. calculate_business_date
      2. invoke_lambda
      3. extract_arn (SFN execution ARN from Lambda response)
      4. extract_glue_details (GlueJobDetailsSensor polls SFN history)
      5. glue_job_status (GlueJobSensor monitors the Glue job)
      6. stepfunction_status (StepFunctionExecutionSensor monitors SFN completion)
    """

    with TaskGroup(group_id=f"{name}_group", dag=dag) as group:

        calc_biz_date = PythonOperator(
            task_id="calculate_business_date",
            python_callable=calculate_business_date,
            dag=dag,
            **_TASK_RETRY_KW,
        )

        invoke_lambda = LambdaInvokeFunctionOperator(
            task_id="invoke_lambda",
            function_name=LAMBDA_FUNCTION_NAME,
            aws_conn_id=AWS_CONN_ID,
            payload=_build_lambda_payload(f"{name}_group.calculate_business_date"),
            invocation_type="RequestResponse",
            dag=dag,
            trigger_rule=TriggerRule.ALL_SUCCESS,
            **_TASK_RETRY_KW,
        )

        extract_execution_arn = PythonOperator(
            task_id="extract_arn",
            python_callable=extract_stepfunction_execution_arn,
            op_kwargs={"task_id": f"{name}_group.invoke_lambda"},
            dag=dag,
            **_TASK_RETRY_KW,
        )

        extract_glue_details = GlueJobDetailsSensor(
            task_id="extract_glue_details",
            aws_conn_id=AWS_CONN_ID,
            upstream_task_id="extract_arn",
            mode="reschedule",
            poke_interval=GLUE_DETAILS_POKE,
            timeout=GLUE_DETAILS_TIMEOUT,
            dag=dag,
            **_TASK_RETRY_KW,
        )

        monitor_glue_job = GlueJobSensor(
            task_id="glue_job_status",
            job_name=(
                "{{ ti.xcom_pull(task_ids='"
                + f"{name}_group.extract_glue_details"
                + "', key='glue_job_name') }}"
            ),
            run_id=(
                "{{ ti.xcom_pull(task_ids='"
                + f"{name}_group.extract_glue_details"
                + "', key='glue_run_id') }}"
            ),
            aws_conn_id=AWS_CONN_ID,
            verbose=True,
            poke_interval=GLUE_POKE,
            timeout=GLUE_TIMEOUT,
            mode="reschedule",
            dag=dag,
            **_TASK_RETRY_KW,
        )

        stepfunction_status = StepFunctionExecutionSensor(
            task_id="stepfunction_status",
            execution_arn=(
                "{{ ti.xcom_pull(task_ids='"
                + f"{name}_group.extract_arn"
                + "', key='execution_arn') }}"
            ),
            aws_conn_id=AWS_CONN_ID,
            poke_interval=SFN_POKE,
            timeout=SFN_TIMEOUT,
            dag=dag,
            **_TASK_RETRY_KW,
        )

        (
            calc_biz_date
            >> invoke_lambda
            >> extract_execution_arn
            >> extract_glue_details
            >> monitor_glue_job
            >> stepfunction_status
        )

    return group

# === END BLOCK ===
