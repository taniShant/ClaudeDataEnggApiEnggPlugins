# === BLOCK: glue_helpers ===

def _coerce_json(obj):
    """Coerce Lambda response to JSON dict."""
    if obj is None:
        return {}
    if isinstance(obj, (bytes, bytearray)):
        try:
            obj = obj.decode("utf-8")
        except Exception:
            try:
                obj = obj.decode("latin-1")
            except Exception:
                return {}
    if isinstance(obj, str):
        try:
            return json.loads(obj)
        except Exception:
            return {}
    if isinstance(obj, (dict, list)):
        return obj
    return {}


def _build_lambda_payload(business_date_task_id: str) -> str:
    """
    Build Lambda payload as a JSON string with Jinja template for business_date.
    The payload contains: bucket, environment, business_date, key, cr.
    """
    payload = {
        "bucket": S3_BUCKET,
        "environment": ENV,
        "business_date": "{{ ti.xcom_pull(task_ids='" + business_date_task_id + "', key='business_date') }}",
        "key": DTXOG_CONFIG_KEY,
        "cr": CHANGE_REQUEST_NO,
    }
    return json.dumps(payload)


def extract_stepfunction_execution_arn(task_id: str, **context) -> str:
    """
    Construct SFN execution ARN from Lambda response and push to XCom.

    Accepts either:
      A) body contains {"sm_name": "<arn>", "sm_execution_name": "<name>"}
      B) body contains {"executionArn": "<full-arn>"}
    """
    raw = context["ti"].xcom_pull(task_ids=task_id)
    logger.info("Lambda xcom response (raw): %r", raw)

    response = raw
    parsed_body = None

    if isinstance(response, str):
        try:
            response = json.loads(response)
        except Exception:
            parsed_body = _coerce_json(response)

    if parsed_body is None:
        if isinstance(response, dict):
            if "body" in response:
                parsed_body = _coerce_json(response["body"])
            elif "Payload" in response:
                payload_obj = response["Payload"]
                try:
                    payload_bytes = (
                        payload_obj.read() if hasattr(payload_obj, "read") else payload_obj
                    )
                except Exception:
                    payload_bytes = payload_obj
                parsed_body = _coerce_json(payload_bytes)
            else:
                parsed_body = _coerce_json(response)
        else:
            parsed_body = _coerce_json(response)

    if not isinstance(parsed_body, dict):
        raise AirflowException(
            f"Unexpected Lambda response body type: {type(parsed_body)}"
        )

    if "executionArn" in parsed_body:
        execution_arn = parsed_body["executionArn"]
    else:
        if "sm_name" not in parsed_body or "sm_execution_name" not in parsed_body:
            raise AirflowException(
                f"Lambda response missing required keys. Body: {parsed_body}"
            )

        sm_arn = parsed_body["sm_name"]
        execution_name = parsed_body["sm_execution_name"]

        arn_parts = sm_arn.split(":")
        region = arn_parts[3]
        account = arn_parts[4]
        state_machine_name = arn_parts[-1]

        execution_arn = (
            f"arn:aws:states:{region}:{account}:execution:"
            f"{state_machine_name}:{execution_name}"
        )

    context["ti"].xcom_push(key="execution_arn", value=execution_arn)
    return execution_arn

# === END BLOCK ===
