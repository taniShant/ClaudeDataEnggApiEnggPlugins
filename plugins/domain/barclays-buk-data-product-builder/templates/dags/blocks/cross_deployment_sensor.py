# === BLOCK: cross_deployment_sensor ===

class CrossDeploymentDagSensor(BaseSensorOperator):
    """Polls external Astronomer deployment via REST API for DAG completion."""

    def __init__(self, tenancy_name, external_dag_id, api_token_env_var,
                 deployment_url_pattern, upstream_task=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenancy_name = tenancy_name
        self.external_dag_id = external_dag_id
        self.api_token_env_var = api_token_env_var
        self.deployment_url_pattern = deployment_url_pattern
        self.upstream_task = upstream_task

    def poke(self, context):
        logical_date = context.get("ds")
        api_token = os.getenv(self.api_token_env_var)
        if not api_token:
            raise AirflowException(f"API token not found: {self.api_token_env_var}")

        deployment_url = self.deployment_url_pattern.format(tenancy=self.tenancy_name)
        headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}

        target_date = datetime.strptime(logical_date, "%Y-%m-%d").date()
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = start_dt + timedelta(days=1)

        url = f"{deployment_url}/api/v1/dags/{self.external_dag_id}/dagRuns"
        params = {
            "execution_date_gte": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "execution_date_lte": end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "order_by": "-execution_date",
            "limit": 10,
        }

        self.log.info(f"Checking cross-deployment: {self.tenancy_name}/{self.external_dag_id} on {logical_date}")

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            dag_runs = response.json().get("dag_runs", [])

            if not dag_runs:
                self.log.info(f"No runs found for {self.external_dag_id} on {logical_date}. Retrying.")
                return False

            latest_state = dag_runs[0].get("state")
            if latest_state == "success":
                self.log.info(f"Cross-deployment dependency satisfied: {self.external_dag_id} = success")
                return True
            else:
                self.log.info(f"{self.external_dag_id} state={latest_state}. Retrying.")
                return False

        except requests.exceptions.RequestException as e:
            self.log.warning(f"API call failed: {e}. Retrying.")
            return False

# === END BLOCK ===
