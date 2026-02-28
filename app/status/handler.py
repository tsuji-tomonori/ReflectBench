import json
import logging
import os

import boto3

from app.common.api import is_valid_run_id, json_response, problem_response, trace_id_from_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.client("dynamodb")
TABLE_NAME = os.environ["TABLE_NAME"]


def _n(item: dict, key: str, default: int = 0) -> int:
    if key not in item:
        return default
    return int(item[key]["N"])


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
        "state": item.get("state", {}).get("S", "UNKNOWN"),
        "progress": {
            "completed_steps": _n(progress, "completed_steps"),
            "total_steps": _n(progress, "total_steps", 10),
            "percent": _n(progress, "percent"),
        },
        "retry_count": _n(item, "retry_count"),
        "last_error": None,
        "started_at": item.get("started_at", {}).get("S"),
        "finished_at": item.get("finished_at", {}).get("S"),
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

    return json_response(200, body, trace_id)
