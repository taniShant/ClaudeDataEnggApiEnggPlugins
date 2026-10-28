# === SKELETON: glue_adhoc ===
# Platform: Glue | Schedule: adhoc (manual trigger only)
# Placeholders: {{DAG_ID}}, {{DAG_DESCRIPTION}}, {{START_DATE_YEAR/MONTH/DAY}},
#   {{DAG_OWNER}}, {{TAGS}},
#   {{LAMBDA_FUNCTION_NAME}}, {{S3_BUCKET_PATTERN}}, {{DTXOG_CONFIG_KEY}},
#   {{CHANGE_REQUEST_NO}}, {{CSM_NAME}}, {{ITSI_ENV_VAR}}
# No conditional blocks — adhoc DAGs have no scheduling or external dependencies.
# === END SKELETON HEADER ===

# --- GENERATED DAG (environment-agnostic) ---

# === BLOCK: imports_core ===
# === BLOCK: imports_glue ===


# =============================================================================
# DAG CONFIG
# =============================================================================

DAG_ID = "{{DAG_ID}}"

DAG_DESCRIPTION = "{{DAG_DESCRIPTION}}"

START_DATE = pendulum.datetime({{START_DATE_YEAR}}, {{START_DATE_MONTH}}, {{START_DATE_DAY}}, tz="Europe/London")

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
# RUNTIME ENVIRONMENT
# =============================================================================

ENV = os.environ.get("ENV")
AWS_ACCOUNT_ID = os.environ.get("BUK_DDA_AWS_ACCOUNT_ID")
ITSI = os.environ.get(ITSI_ENV_VAR)
AWS_CONN_ID = f"{ITSI}-aws-dda-dtx-{CSM_NAME}"

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


# === BLOCK: date_control_adhoc ===
# === BLOCK: glue_job_sensor ===
# === BLOCK: glue_helpers ===
# === BLOCK: taskgroup_glue ===


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

    # -------------------------------------------------------------------------
    # Create Glue TaskGroup
    # -------------------------------------------------------------------------

    glue_task_group = glue_lambda_sfn_group(name="glue_dtx", dag=dag)
