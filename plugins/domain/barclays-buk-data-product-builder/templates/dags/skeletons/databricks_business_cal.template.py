# === SKELETON: databricks_business_cal ===
# Platform: Databricks | Schedule: business_calendar
# Placeholders: {{DAG_ID}}, {{DAG_DESCRIPTION}}, {{START_DATE_YEAR/MONTH/DAY}},
#   {{SCHEDULE_HOUR}}, {{SCHEDULE_MINUTE}}, {{HOLIDAY_LIST}},
#   {{CATCHUP}}, {{DATABRICKS_CONN_ID}}, {{TAGS}}, {{DAG_OWNER}}, {{TASKS_CONFIG}}
# Conditional blocks: imports_sensors, conf_helpers, external_dag_functions,
#   dag_wiring_with_deps (for ExternalTaskSensor deps only)
# === END SKELETON HEADER ===

# --- GENERATED DAG (environment-agnostic) ---

# === BLOCK: imports_core ===
# === BLOCK: imports_databricks ===
# === BLOCK: imports_sensors (if dag_sensor deps) ===
# === BLOCK: imports_timetable ===


# =============================================================================
# DAG CONFIG
# =============================================================================

DAG_ID = "{{DAG_ID}}"

DAG_DESCRIPTION = "{{DAG_DESCRIPTION}}"

START_DATE = pendulum.datetime({{START_DATE_YEAR}}, {{START_DATE_MONTH}}, {{START_DATE_DAY}}, tz="Europe/London")

CATCHUP = {{CATCHUP}}

MAX_ACTIVE_RUNS = 1

LOCAL_TZ = pendulum.timezone("Europe/London")

DATABRICKS_CONN_ID = "{{DATABRICKS_CONN_ID}}"

TAGS = {{TAGS}}

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
# === BLOCK: external_dag_functions (if dag_sensor or cross_deployment deps) ===
# === BLOCK: taskgroup_databricks_selfcontained ===


# =============================================================================
# DAG DEFINITION
# =============================================================================

with DAG(
    dag_id=DAG_ID,
    description=DAG_DESCRIPTION,
    schedule=timetable,
    start_date=START_DATE,
    catchup=CATCHUP,
    max_active_runs=MAX_ACTIVE_RUNS,
    default_args=DEFAULT_ARGS,
    tags=TAGS,
) as dag:

    created_tasks = {}

    # -------------------------------------------------------------------------
    # Create Databricks TaskGroups (date calc + job execution inside group)
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
    # === BLOCK: dag_wiring_with_deps (if external deps — adapted for business_cal) ===
    # -------------------------------------------------------------------------
