# === SKELETON: databricks_cron ===
# Platform: Databricks | Schedule: cron
# Placeholders: {{DAG_ID}}, {{DAG_DESCRIPTION}}, {{START_DATE_YEAR/MONTH/DAY}},
#   {{SCHEDULE_CRON}}, {{CATCHUP}}, {{DATABRICKS_CONN_ID}}, {{TAGS}},
#   {{DAG_OWNER}}, {{TASKS_CONFIG}}, {{SKIP_BANK_HOLIDAYS}}, {{ITSI_ENV_VAR}}
# Conditional blocks: imports_sensors, imports_dynamodb, conf_helpers, holiday_check,
#   bank_holidays_data, dynamodb_sensor, cross_deployment_sensor, external_dag_functions,
#   dag_wiring_with_deps
# === END SKELETON HEADER ===

# --- GENERATED DAG (environment-agnostic) ---

# === BLOCK: imports_core ===
# === BLOCK: imports_databricks ===
# === BLOCK: imports_sensors (if external deps) ===
# === BLOCK: imports_dynamodb (if dynamodb deps) ===


# =============================================================================
# DAG CONFIG
# =============================================================================

DAG_ID = "{{DAG_ID}}"

DAG_DESCRIPTION = "{{DAG_DESCRIPTION}}"

START_DATE = pendulum.datetime({{START_DATE_YEAR}}, {{START_DATE_MONTH}}, {{START_DATE_DAY}}, tz="Europe/London")

SCHEDULE_CRON = "{{SCHEDULE_CRON}}"

CATCHUP = {{CATCHUP}}

MAX_ACTIVE_RUNS = 1

LOCAL_TZ = pendulum.timezone("Europe/London")

DATABRICKS_CONN_ID = "{{DATABRICKS_CONN_ID}}"

TAGS = {{TAGS}}

SKIP_BANK_HOLIDAYS = {{SKIP_BANK_HOLIDAYS}}

# =============================================================================
# RUNTIME ENVIRONMENT
# =============================================================================

ENV = os.environ.get("ENV")
ITSI = os.environ.get("{{ITSI_ENV_VAR}}")

# =============================================================================
# AWS CONFIG
# =============================================================================

AWS_CFG = {
    # Base layer (e_* databases) — raw/GCPR AWS account (auto-derived from ITSI)
    "conn_id_ddb_base": f"{ITSI}-aws-raw-ddb-read",
    "dynamodb_table_base": "datalake_exe_status",

    # FDP/CDP/BDP layer (DDA databases) — DDA AWS account
    # Platform-provided during Airflow setup; format: {ITSI}-aws-dda-dtx-{layer}-{tenancy_short}
    "conn_id_ddb_dda": "{{DDA_DDB_CONN_ID}}",
    "dynamodb_table_dda": "data_domain_execution_status",
}

# =============================================================================
# DEPENDENCY SENSOR CONFIG
# =============================================================================
# Adjust these values to control how long and how often sensors retry
# before giving up on upstream dependencies.

SENSOR_CFG = {
    # ExternalTaskSensor — upstream DAGs on same Airflow deployment
    "dag_sensor_poke_interval_seconds": 900,       # How often to check (15 minutes)
    "dag_sensor_timeout_seconds": 86400,            # Max wait time (24 hours)

    # DynamoDBEntrySensor — GCPR check for non-Airflow sources
    "dynamodb_poke_interval_seconds": 3600,         # How often to check (1 hour)
    "dynamodb_timeout_seconds": 86400,              # Max wait time (24 hours)

    # CrossDeploymentDagSensor — upstream DAGs on different Airflow deployment
    "cross_deployment_poke_interval_seconds": 300,  # How often to check (5 minutes)
    "cross_deployment_timeout_seconds": 3600,       # Max wait time (1 hour)
}

# === BLOCK: bank_holidays_data (if skip_bank_holidays=true) ===

DEFAULT_ARGS = {
    "owner": "{{DAG_OWNER}}",
    "depends_on_past": {{DEPENDS_ON_PAST}},
    "wait_for_downstream": {{WAIT_FOR_DOWNSTREAM}},
    "retries": 0,
    "retry_delay": timedelta(minutes=20),
}


# =============================================================================
# TASK CONFIG
# =============================================================================

TASKS_CONFIG = {{TASKS_CONFIG}}


# =============================================================================
# LOGGING
# =============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(DAG_ID)

_TASK_RETRY_KW = {
    "retries": int(DEFAULT_ARGS.get("retries", 0)),
    "retry_delay": DEFAULT_ARGS.get("retry_delay", timedelta(minutes=0)),
}


# === BLOCK: conf_helpers (if external deps) ===
# === BLOCK: date_control ===
# === BLOCK: holiday_check (if skip_bank_holidays=true) ===
# === BLOCK: external_dag_functions (if dag_sensor or cross_deployment deps) ===
# === BLOCK: dynamodb_sensor (if dynamodb deps) ===
# === BLOCK: cross_deployment_sensor (if cross_deployment deps) ===
# === BLOCK: taskgroup_databricks ===


# =============================================================================
# DAG DEFINITION
# =============================================================================

with DAG(
    dag_id=DAG_ID,
    description=DAG_DESCRIPTION,
    schedule_interval=SCHEDULE_CRON,
    start_date=START_DATE,
    catchup=CATCHUP,
    max_active_runs=MAX_ACTIVE_RUNS,
    default_args=DEFAULT_ARGS,
    tags=TAGS,
) as dag:

    created_tasks = {}

    # -------------------------------------------------------------------------
    # Holiday Skip (if enabled)
    # -------------------------------------------------------------------------

    if SKIP_BANK_HOLIDAYS:
        check_not_holiday = ShortCircuitOperator(
            task_id="check_not_bank_holiday",
            python_callable=_is_bank_holiday,
            ignore_downstream_trigger_rules=False,
            dag=dag,
            **_TASK_RETRY_KW,
        )
    else:
        check_not_holiday = EmptyOperator(task_id="check_not_bank_holiday", dag=dag)

    # -------------------------------------------------------------------------
    # Date Calculation (INDEPENDENT - outside TaskGroup)
    # -------------------------------------------------------------------------

    _calculate_dates_configs = []
    for task_name, task_cfg in TASKS_CONFIG.items():
        _calculate_dates_configs.append({
            "process_name": task_cfg.get("process_name"),
            "target_table_name": task_cfg.get("target_table_name"),
        })

    if _calculate_dates_configs:
        _first_config = _calculate_dates_configs[0]
    else:
        raise AirflowException("TASKS_CONFIG is empty; at least one task required")

    calculate_dates = PythonOperator(
        task_id="calculate_business_dates",
        python_callable=calculate_business_dates,
        op_kwargs={
            "process_name": _first_config["process_name"],
            "target_table_name": _first_config["target_table_name"],
        },
        dag=dag,
        **_TASK_RETRY_KW,
    )

    # -------------------------------------------------------------------------
    # Create Databricks TaskGroups (job execution only)
    # -------------------------------------------------------------------------

    for task_name, task_cfg in TASKS_CONFIG.items():
        current_group = databricks_job_group(
            name=task_name,
            task_cfg=task_cfg,
            dag=dag,
        )

        created_tasks[task_name] = current_group

    # -------------------------------------------------------------------------
    # Wire internal task dependencies, if any
    # -------------------------------------------------------------------------

    for task_name, task_cfg in TASKS_CONFIG.items():
        current_group = created_tasks.get(task_name)

        if not current_group:
            continue

        for upstream_task_name in (task_cfg or {}).get("task_dependency", []):
            upstream_group = created_tasks.get(upstream_task_name)

            if upstream_group:
                upstream_group >> current_group

    # -------------------------------------------------------------------------
    # Wire external DAG dependencies (if any)
    # === BLOCK: dag_wiring_with_deps (if external deps) ===
    # -------------------------------------------------------------------------

    # --- If NO external deps, wire simple chain: ---
    # check_not_holiday >> calculate_dates >> current_group
    # --- (The agent uses the appropriate wiring based on dag_spec) ---
