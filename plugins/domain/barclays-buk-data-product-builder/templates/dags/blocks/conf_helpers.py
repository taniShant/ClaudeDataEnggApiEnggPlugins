# === BLOCK: conf_helpers ===
def _get_bool_from_dag_conf(
    key: str,
    default: bool,
    **context,
) -> bool:
    """
    Reads boolean-like values from dag_run.conf.

    Supports:
      true / false
      "true" / "false"
      "yes" / "no"
      "1" / "0"
    """

    dag_run = context.get("dag_run")
    dag_conf = dag_run.conf if dag_run and dag_run.conf else {}

    value = dag_conf.get(key, default)

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "y", "1"}

    return bool(value)


def _should_wait_for_external_dependency(**context):
    """
    Returns a truthy string when external dependency should be checked.
    Returns an empty string when dependencies are explicitly skipped.

    The return value is stored as XCom return_value — using plain English
    so operators can read and understand the decision in the Airflow UI.
    """

    skip_dependencies = _get_bool_from_dag_conf(
        key="skip_dependencies",
        default=False,
        **context,
    )

    should_wait = not skip_dependencies

    logger.info(
        "skip_dependencies=%s, should_wait_for_external_dependency=%s",
        skip_dependencies,
        should_wait,
    )

    if should_wait:
        return "Waiting for external dependency to complete"
    else:
        return ""


def _should_skip_external_dependency(**context):
    """
    Complementary branch used to bypass external dependency checks.

    Returns a truthy string when dependencies should be skipped,
    or an empty string when they should be waited on.
    """

    skip_dependencies = _get_bool_from_dag_conf(
        key="skip_dependencies",
        default=False,
        **context,
    )

    if skip_dependencies:
        logger.info("Skipping external dependency check (skip_dependencies=true)")
        return "Skipping external dependency (skip_dependencies=true in dag_run.conf)"
    else:
        return ""
# === END BLOCK ===
