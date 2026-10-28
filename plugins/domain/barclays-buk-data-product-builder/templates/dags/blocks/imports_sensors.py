# === BLOCK: imports_sensors ===
# External dependency sensor imports — include when dag_sensor, cross_deployment, or dynamodb deps exist
from airflow.models import DagRun
from airflow.operators.python import ShortCircuitOperator
from airflow.sensors.base import BaseSensorOperator
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.utils.decorators import apply_defaults
import requests
# === END BLOCK ===
