# === BLOCK: holiday_check ===
def _is_bank_holiday(**context):
    """
    Check if logical_date is a bank holiday.
    Returns a truthy string if NOT a holiday (proceed),
    or an empty string if it IS a holiday (ShortCircuit skips downstream).

    The return value is stored as XCom return_value — using plain English
    so operators can read and understand the decision in the Airflow UI.
    """
    logical_date = context["logical_date"].in_timezone(LOCAL_TZ)
    date_str = logical_date.strftime("%Y-%m-%d")
    is_holiday = date_str in UK_BANK_HOLIDAYS

    if is_holiday:
        logger.info("Holiday check: %s IS a bank holiday — skipping DAG run", date_str)
        return ""
    else:
        logger.info("Holiday check: %s is not a bank holiday — proceeding", date_str)
        return f"{date_str} is not a bank holiday — proceeding"
# === END BLOCK ===
