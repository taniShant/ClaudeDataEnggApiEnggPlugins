# === BLOCK: external_dag_functions ===
def _latest_external_run_same_day(
    ds_str: str,
    external_dag_id: str,
):
    """
    Finds the latest execution_date of the external DAG within the same logical day
    as this DAG run's ds value.

    Since curr_bus_dt = logical_date in this implementation, external dependency
    is aligned to the same logical date.

    IMPORTANT: Must ALWAYS return a datetime (never bool/None).
    ExternalTaskSensor passes the return value into dttm_filter and calls
    .isoformat() on it — returning False/None causes AttributeError.

    Returns:
      - execution_date of the latest matching run if found
      - start-of-day datetime if no matching run exists yet
        (sensor will find no run in allowed_states and retry on next poke)
    """

    if not ds_str:
        logger.warning("No 'ds' in context; cannot resolve external execution_date.")
        # Return epoch as safe fallback — sensor will find no matching run and retry
        return pendulum.datetime(1970, 1, 1, tz=LOCAL_TZ)

    target_date = datetime.strptime(ds_str, "%Y-%m-%d").date()

    start = pendulum.datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        0,
        0,
        0,
        tz=LOCAL_TZ,
    )

    end = start.add(days=1)

    runs = DagRun.find(dag_id=external_dag_id)

    runs_on_date = [
        run
        for run in runs
        if start <= run.execution_date < end
    ]

    if not runs_on_date:
        logger.info(
            "No runs found for external DAG '%s' on target_date=%s. "
            "Returning start-of-day so sensor retries on next poke.",
            external_dag_id,
            target_date,
        )
        return start

    chosen = max(runs_on_date, key=lambda run: run.execution_date)

    logger.info(
        "Resolved external execution_date for DAG '%s': %s",
        external_dag_id,
        chosen.execution_date,
    )

    return chosen.execution_date


def _execution_date_fn_factory(external_dag_id: str):
    """
    Adapter used by ExternalTaskSensor.execution_date_fn.
    Must return a datetime — see _latest_external_run_same_day docstring.
    """

    return lambda dt, **context: _latest_external_run_same_day(
        context.get("ds"),
        external_dag_id,
    )


def _normalise_external_tasks(ext_tasks):
    """
    Converts upstream_dag_task into a clean list.

    Supports:
      upstream_dag_task: None
      upstream_dag_task: task_a
      upstream_dag_task:
        - task_a
        - task_b
    """

    if ext_tasks is None:
        return [None]

    if isinstance(ext_tasks, list):
        return ext_tasks or [None]

    return [ext_tasks]
# === END BLOCK ===
