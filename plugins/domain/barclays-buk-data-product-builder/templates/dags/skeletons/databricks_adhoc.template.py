# === SKELETON: databricks_adhoc ===
# Platform: Databricks | Schedule: adhoc (manual trigger only)
# Placeholders: {{DAG_ID}}, {{DAG_DESCRIPTION}}, {{START_DATE_YEAR/MONTH/DAY}},
#   {{DATABRICKS_CONN_ID}}, {{TAGS}}, {{DAG_OWNER}}, {{TASKS_CONFIG}}
# No conditional blocks — adhoc DAGs have no scheduling or external dependencies.
# === END SKELETON HEADER ===

# --- GENERATED DAG (environment-agnostic) ---

# === BLOCK: imports_core ===
# === BLOCK: imports_databricks ===


# =============================================================================
# DAG CONFIG
# =============================================================================

DAG_ID = "{{DAG_ID}}"

DAG_DESCRIPTION = "{{DAG_DESCRIPTION}}"

START_DATE = pendulum.datetime({{START_DATE_YEAR}}, {{START_DATE_MONTH}}, {{START_DATE_DAY}}, tz="Europe/London")

MAX_ACTIVE_RUNS = 1

LOCAL_TZ = pendulum.timezone("Europe/London")

DATABRICKS_CONN_ID = "{{DATABRICKS_CONN_ID}}"

TAGS = {{TAGS}}

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


# === BLOCK: date_control_adhoc ===
# === BLOCK: taskgroup_databricks_selfcontained ===


# =============================================================================
# DAG DEFINITION
# =============================================================================

with DAG(
    dag_id=DAG_ID,
    description=DAG_DESCRIPTION,
    schedule=None,
    start_date=START_DATE,
    catchup=False,
    max_active_runs=MAX_ACTIVE_RUNS,
    default_args=DEFAULT_ARGS,
    tags=TAGS,
) as dag:

    created_tasks = {}

    for task_name, task_cfg in TASKS_CONFIG.items():
        current_group = databricks_job_group(
            name=task_name,
            task_cfg=task_cfg,
            dag=dag,
        )
        created_tasks[task_name] = current_group

    # Wire internal task dependencies
    for task_name, task_cfg in TASKS_CONFIG.items():
        current_group = created_tasks.get(task_name)
        if not current_group:
            continue
        for upstream_task_name in (task_cfg or {}).get("task_dependency", []):
            upstream_group = created_tasks.get(upstream_task_name)
            if upstream_group:
                upstream_group >> current_group
