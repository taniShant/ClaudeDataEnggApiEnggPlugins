# === BLOCK: glue_job_sensor ===

class GlueJobDetailsSensor(BaseSensorOperator):
    """
    Poll Step Functions execution history to extract Glue JobName and JobRunId.
    Pushes glue_job_name and glue_run_id to XCom.
    """

    template_fields = ("upstream_task_id",)

    def __init__(
        self,
        aws_conn_id: str,
        upstream_task_id: str,
        mode: str = "reschedule",
        poke_interval: int = 30,
        timeout: int = 1800,
        **kwargs,
    ):
        super().__init__(mode=mode, poke_interval=poke_interval, timeout=timeout, **kwargs)
        self.aws_conn_id = aws_conn_id
        self.upstream_task_id = upstream_task_id

    def poke(self, context) -> bool:
        current_task = context["task"]
        group_id = current_task.task_group.group_id if current_task.task_group else None
        extract_arn_task_id = (
            f"{group_id}.{self.upstream_task_id}" if group_id else self.upstream_task_id
        )

        execution_arn = context["ti"].xcom_pull(
            task_ids=extract_arn_task_id, key="execution_arn"
        )
        if not execution_arn:
            self.log.info(
                "No execution ARN from %s; will retry", extract_arn_task_id
            )
            return False

        sf_hook = StepFunctionHook(aws_conn_id=self.aws_conn_id)
        sf_client = sf_hook.get_conn()
        self.log.info("Polling SFN execution history for %s", execution_arn)

        try:
            response = sf_client.get_execution_history(
                executionArn=execution_arn, maxResults=1000, reverseOrder=False
            )
            events = response.get("events", [])
            self.log.info("Retrieved %d events from execution history", len(events))
            job_name, run_id = self._extract_glue_details(events)

            if job_name and run_id:
                context["ti"].xcom_push(key="glue_job_name", value=job_name)
                context["ti"].xcom_push(key="glue_run_id", value=run_id)
                self.log.info(
                    "Extracted Glue details: job=%s run_id=%s", job_name, run_id
                )
                return True

            self.log.info("Glue details not found yet; will poke again.")
            return False

        except Exception as e:
            self.log.warning(
                "Transient error reading SFN history: %s; will poke again.", e
            )
            return False

    def _extract_glue_details(self, events):
        job_name, run_id = None, None
        for event in events:
            etype = event.get("type")

            if etype == "TaskScheduled":
                details = event.get("taskScheduledEventDetails", {})
                if (
                    details.get("resourceType") == "glue"
                    and "startJobRun" in details.get("resource", "")
                ):
                    try:
                        params = json.loads(details.get("parameters", "{}"))
                        job_name = params.get("JobName", job_name)
                    except json.JSONDecodeError:
                        continue

            elif etype == "TaskSubmitted" and job_name:
                details = event.get("taskSubmittedEventDetails", {})
                try:
                    output = json.loads(details.get("output", "{}"))
                    run_id = (
                        output.get("JobRunId") or output.get("jobRunId") or run_id
                    )
                    if job_name and run_id:
                        break
                except json.JSONDecodeError:
                    continue

            elif etype == "TaskSucceeded":
                details = event.get("taskSucceededEventDetails", {})
                try:
                    output = json.loads(details.get("output", "{}"))
                    potential_run_id = output.get("JobRunId") or output.get("jobRunId")
                    potential_job_name = output.get("JobName") or output.get("jobName")
                    if potential_job_name and potential_run_id:
                        job_name, run_id = potential_job_name, potential_run_id
                        break
                except json.JSONDecodeError:
                    continue

        return job_name, run_id

# === END BLOCK ===
