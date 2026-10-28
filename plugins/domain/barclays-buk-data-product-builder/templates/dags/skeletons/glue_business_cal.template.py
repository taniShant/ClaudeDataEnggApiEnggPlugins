# === SKELETON: glue_business_cal ===
# Platform: Glue | Schedule: business_calendar
# Placeholders: {{DAG_ID}}, {{DAG_DESCRIPTION}}, {{START_DATE_YEAR/MONTH/DAY}},
#   {{SCHEDULE_HOUR}}, {{SCHEDULE_MINUTE}}, {{HOLIDAY_LIST}},
#   {{CATCHUP}}, {{DAG_OWNER}}, {{TAGS}},
#   {{LAMBDA_FUNCTION_NAME}}, {{S3_BUCKET_PATTERN}}, {{DTXOG_CONFIG_KEY}},
#   {{CHANGE_REQUEST_NO}}, {{CSM_NAME}}, {{ITSI_ENV_VAR}},
#   {{SOURCES_DB_TABLE_DETAILS}}, {{EXTERNAL_DAG_IDS}}
# Conditional blocks: imports_sensors, imports_dynamodb, conf_helpers,
#   dynamodb_sensor, external_dag_functions, dag_wiring_glue
# === END SKELETON HEADER ===

# --- GENERATED DAG (environment-agnostic) ---

# === BLOCK: imports_core ===
# === BLOCK: imports_glue ===
# === BLOCK: imports_sensors (if external deps) ===
# === BLOCK: imports_dynamodb (if dynamodb deps) ===
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

TAGS = {{TAGS}}

DEFAULT_ARGS = {
    "owner": "{{DAG_OWNER}}",
    "depends_on_past": False,
    "wait_for_downstream": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=20),
}


# =============================================================================
# GLUE DTX CONFIG
# =============================================================================

LAMBDA_FUNCTION_NAME = "{{LAMBDA_FUNCTION_NAME}}"

S3_BUCKET_PATTERN = "{{S3_BUCKET_PATTERN}}"

DTXOG_CONFIG_KEY = "{{DTXOG_CONFIG_KEY}}"

CHANGE_REQUEST_NO = "{{CHANGE_REQUEST_NO}}"

CSM_NAME = "{{CSM_NAME}}"

ITSI_ENV_VAR = "{{ITSI_ENV_VAR}}"


# =============================================================================
# AWS CONFIG
# =============================================================================

AWS_CFG = {
    "conn_id_ddb_read": f"{ITSI}-aws-raw-ddb-read",
    "dynamodb_table_base": "datalake_exe_status",
    "dynamodb_table_dda": "data_domain_execution_status",
}


# =============================================================================
# SOURCES CONFIG (DynamoDB GCPR checks)
# =============================================================================

SOURCES_DB_TABLE_DETAILS = {{SOURCES_DB_TABLE_DETAILS}}

# =============================================================================
# EXTERNAL CONFIG (ExternalTaskSensor)
# =============================================================================

EXTERNAL_DAG_IDS = {{EXTERNAL_DAG_IDS}}


# =============================================================================
# RUNTIME ENVIRONMENT
# =============================================================================

ENV = os.environ.get("ENV")
AWS_ACCOUNT_ID = os.environ.get("BUK_DDA_AWS_ACCOUNT_ID")
ITSI = os.environ.get(ITSI_ENV_VAR)
AWS_CONN_ID = f"{ITSI}-aws-dda-dtx-{CSM_NAME}"
DDB_CONN_ID = f"{ITSI}-aws-raw-ddb-read"

S3_BUCKET = S3_BUCKET_PATTERN.format(ENV=ENV, AWS_ACCOUNT_ID=AWS_ACCOUNT_ID)


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
# === BLOCK: dynamodb_sensor (if dynamodb deps) ===
# === BLOCK: external_dag_functions (if dag_sensor deps) ===
# === BLOCK: glue_job_sensor ===
# === BLOCK: glue_helpers ===
# === BLOCK: taskgroup_glue ===


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

    # -------------------------------------------------------------------------
    # Create Glue TaskGroup
    # -------------------------------------------------------------------------

    glue_task_group = glue_lambda_sfn_group(name="glue_dtx", dag=dag)

    # -------------------------------------------------------------------------
    # Wire dependencies (if any)
    # === BLOCK: dag_wiring_glue (if SOURCES_DB_TABLE_DETAILS or EXTERNAL_DAG_IDS non-empty) ===
    # -------------------------------------------------------------------------
