# === BLOCK: dynamodb_sensor ===

class DynamoDBEntrySensor(BaseSensorOperator):
    """
    Sensor that checks DynamoDB for GCPR execution status of source table.
    Uses Airflow's DynamoDBHook for secure connection management.
    """

    template_fields = ('db_name', 'table_name', 'business_date_task_id')

    @apply_defaults
    def __init__(
        self,
        db_name: str,
        table_name: str,
        business_date_task_id: str = None,
        dynamodb_conn_id: str = None,
        dynamodb_table_name: str = None,
        source_layer: str = "base",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.db_name = db_name
        self.table_name = table_name
        self.business_date_task_id = business_date_task_id
        self.source_layer = source_layer

        # Determine correct DynamoDB connection ID and table based on source layer.
        # Base layer (e_* databases) uses a different AWS account than FDP/CDP (DDA).
        if source_layer == "base" and db_name.startswith("e_"):
            self.dynamodb_conn_id = dynamodb_conn_id or AWS_CFG["conn_id_ddb_base"]
            self.dynamodb_table_name = dynamodb_table_name or AWS_CFG["dynamodb_table_base"]
        else:
            self.dynamodb_conn_id = dynamodb_conn_id or AWS_CFG["conn_id_ddb_dda"]
            self.dynamodb_table_name = dynamodb_table_name or AWS_CFG["dynamodb_table_dda"]

    def poke(self, context) -> bool:
        ti = context["ti"]

        # Determine the task ID that pushed business_date to XCom
        if self.business_date_task_id:
            extract_task_id = self.business_date_task_id
        else:
            raise AirflowException(
                "DynamoDBEntrySensor requires explicit business_date_task_id "
                "(date calculation is now at DAG level, not in TaskGroup)"
            )

        # Retrieve business_date from XCom (format: YYYYMMDD)
        # dag_id is set explicitly to bypass TaskGroup auto-scoping —
        # without it, Airflow prefixes the caller's group_id to task_ids,
        # which fails when the date calc task is at DAG level.
        business_date = ti.xcom_pull(
            key="curr_bus_dt",
            task_ids=extract_task_id,
            dag_id=context["dag"].dag_id,
        )
        if not business_date:
            logger.warning(f"Business date not yet available from '{extract_task_id}'. Will retry.")
            return False

        # Remove dashes for DynamoDB key: YYYY-MM-DD → YYYYMMDD
        business_date_nodash = business_date.replace("-", "")
        entry_key = f"{self.db_name}|{self.table_name}|{business_date_nodash}"

        logger.info(
            "DynamoDB GCPR check — "
            "DynamoDB table: %s | Connection ID: %s | Source layer: %s",
            self.dynamodb_table_name,
            self.dynamodb_conn_id,
            self.source_layer,
        )
        logger.info(
            "Query: EntryKey=%s | Filter: ExecutionState=GCPR AND Execution_Status=Success",
            entry_key,
        )

        # Use Airflow's DynamoDBHook for secure connection management
        dynamodb_hook = DynamoDBHook(aws_conn_id=self.dynamodb_conn_id)
        dynamodb = dynamodb_hook.get_conn()
        table = dynamodb.Table(self.dynamodb_table_name)

        try:
            response = table.query(
                KeyConditionExpression=Key("EntryKey").eq(entry_key),
                FilterExpression=Attr("ExecutionState").eq("GCPR") & Attr("Execution_Status").eq("Success"),
                ScanIndexForward=False,
                Limit=1,
            )

            count = response.get("Count", 0)

            # Log found entries
            for item in response.get("Items", [])[:3]:
                logger.info(
                    "Found GCPR entry: %s | Status=%s | State=%s | Timestamp=%s",
                    item.get("EntryKey"),
                    item.get("Execution_Status"),
                    item.get("ExecutionState"),
                    item.get("Execution_Timestamp"),
                )

            if count > 0:
                logger.info(f"SUCCESS: Found {count} GCPR 'Success' entries for {entry_key}")
                return True
            else:
                logger.info(f"No GCPR 'Success' entries for {entry_key}. Will retry.")
                return False

        except Exception as e:
            logger.error(f"Error querying DynamoDB: {e}")
            raise AirflowException(f"DynamoDB query failed for {entry_key}: {str(e)}")

# === END BLOCK ===
