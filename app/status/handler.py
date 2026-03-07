import json
import logging
import os

import boto3

from app.common.api import is_valid_run_id, json_response, problem_response, trace_id_from_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.client("dynamodb")
lambda_client = boto3.client("lambda")
TABLE_NAME = os.environ["TABLE_NAME"]


def _n(item: dict, key: str, default: int = 0) -> int:
    if key not in item:
        return default
    return int(item[key]["N"])


def _enrich_from_durable_execution(item: dict, body: dict) -> None:
    durable_execution_arn = item.get("durable_execution_arn", {}).get("S")
    if not durable_execution_arn:
        return

    get_durable_execution = getattr(lambda_client, "get_durable_execution", None)
    if not callable(get_durable_execution):
        return

    try:
        durable = get_durable_execution(DurableExecutionArn=durable_execution_arn)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            json.dumps(
                {
                    "step": "GET_RUN_STATUS",
                    "run_id": body["run_id"],
                    "message": f"durable execution enrichment failed: {exc}",
                }
            )
        )
        return

    body["durable_execution"] = {
        "arn": durable.get("DurableExecutionArn") or durable_execution_arn,
        "name": durable.get("DurableExecutionName")
        or item.get("execution_name", {}).get("S"),
        "status": durable.get("Status"),
        "function_arn": durable.get("FunctionArn"),
        "version": durable.get("Version"),
    }

    durable_status = durable.get("Status")
    if durable_status in {"RUNNING", "SUCCEEDED", "FAILED", "TIMED_OUT"}:
        body["state"] = durable_status


def handler(event, _context):
    trace_id = trace_id_from_event(event)
    step = "GET_RUN_STATUS"
    run_id = (event.get("pathParameters") or {}).get("run_id")

    if not is_valid_run_id(run_id):
        return problem_response(
            status_code=400,
            code="INVALID_RUN_ID",
            message="run_id format is invalid",
            category="validation",
            retryable=False,
            step=step,
            trace_id=trace_id,
        )

    logger.info(json.dumps({"trace_id": trace_id, "step": step, "run_id": run_id}))
    res = dynamodb.get_item(
        TableName=TABLE_NAME, Key={"run_id": {"S": run_id}}, ConsistentRead=True
    )
    item = res.get("Item")
    if not item or item.get("kind", {}).get("S") == "IDEMPOTENCY":
        return problem_response(
            status_code=404,
            code="RUN_NOT_FOUND",
            message="run_id not found",
            category="validation",
            retryable=False,
            step=step,
            trace_id=trace_id,
        )

    progress = item.get("progress", {}).get("M", {})
    body = {
        "run_id": run_id,
        "phase": item.get("phase", {}).get("S", "UNKNOWN"),
        "step": item.get("step", {}).get("S"),
        "state": item.get("state", {}).get("S", "UNKNOWN"),
        "progress": {
            "completed_steps": _n(progress, "completed_steps"),
            "total_steps": _n(progress, "total_steps", 18),
            "percent": _n(progress, "percent"),
        },
        "retry_count": _n(item, "retry_count"),
        "last_error": None,
        "started_at": item.get("started_at", {}).get("S"),
        "finished_at": item.get("finished_at", {}).get("S"),
        "execution_name": item.get("execution_name", {}).get("S"),
        "durable_execution_arn": item.get("durable_execution_arn", {}).get("S"),
        "artifact_index_key": item.get("artifact_index_key", {}).get("S"),
    }

    if "last_error" in item and "M" in item["last_error"]:
        err = item["last_error"]["M"]
        body["last_error"] = {
            "step": err.get("step", {}).get("S"),
            "reason": err.get("reason", {}).get("S"),
            "retryable": err.get("retryable", {}).get("BOOL", False),
            "category": err.get("category", {}).get("S"),
            "trace_id": err.get("trace_id", {}).get("S"),
        }

    _enrich_from_durable_execution(item, body)

    return json_response(200, body, trace_id)
