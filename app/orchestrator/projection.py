import datetime
import os

import boto3

dynamodb = boto3.client("dynamodb")
TABLE_NAME = os.environ["TABLE_NAME"]

TOTAL_STEPS = 18


def _now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat()


def _progress_map(completed_steps: int) -> dict:
    completed = max(0, min(completed_steps, TOTAL_STEPS))
    percent = int((completed / TOTAL_STEPS) * 100)
    return {
        "M": {
            "completed_steps": {"N": str(completed)},
            "total_steps": {"N": str(TOTAL_STEPS)},
            "percent": {"N": str(percent)},
        }
    }


def build_run_item(
    *,
    run_id: str,
    accepted_at: str,
    request_hash: str,
    config_s3_key: str,
    execution_name: str,
    parent_run_id: str | None = None,
    repair_phase: str | None = None,
    repair_scope: str | None = None,
    repair_mode: str | None = None,
    rebuild_downstream: bool | None = None,
    source_invalid_keys: list[str] | None = None,
) -> dict:
    item = {
        "run_id": {"S": run_id},
        "phase": {"S": "STUDY1"},
        "step": {"S": "STUDY1_ENUMERATE"},
        "state": {"S": "QUEUED"},
        "retry_count": {"N": "0"},
        "progress": _progress_map(0),
        "request_hash": {"S": request_hash},
        "config_s3_key": {"S": config_s3_key},
        "execution_name": {"S": execution_name},
        "created_at": {"S": accepted_at},
        "updated_at": {"S": accepted_at},
    }
    if parent_run_id:
        item["parent_run_id"] = {"S": parent_run_id}
    if repair_phase:
        item["repair_phase"] = {"S": repair_phase}
    if repair_scope:
        item["repair_scope"] = {"S": repair_scope}
    if repair_mode:
        item["repair_mode"] = {"S": repair_mode}
    if rebuild_downstream is not None:
        item["rebuild_downstream"] = {"BOOL": rebuild_downstream}
    if source_invalid_keys is not None:
        item["source_invalid_keys"] = {"L": [{"S": key} for key in source_invalid_keys]}
    return item


def save_execution_metadata(
    *,
    run_id: str,
    execution_name: str,
    durable_execution_arn: str | None,
) -> None:
    expr = "SET execution_name = :execution_name, updated_at = :updated_at"
    values: dict[str, dict] = {
        ":execution_name": {"S": execution_name},
        ":updated_at": {"S": _now_iso()},
    }
    if durable_execution_arn:
        expr += ", durable_execution_arn = :durable_execution_arn"
        values[":durable_execution_arn"] = {"S": durable_execution_arn}

    dynamodb.update_item(
        TableName=TABLE_NAME,
        Key={"run_id": {"S": run_id}},
        UpdateExpression=expr,
        ExpressionAttributeValues=values,
    )


def mark_running(
    *,
    run_id: str,
    phase: str,
    step: str,
    completed_steps: int,
    retry_count: int = 0,
) -> None:
    now = _now_iso()
    dynamodb.update_item(
        TableName=TABLE_NAME,
        Key={"run_id": {"S": run_id}},
        UpdateExpression=(
            "SET phase = :phase, step = :step, #state = :state, progress = :progress, "
            "retry_count = :retry_count, updated_at = :updated_at, "
            "started_at = if_not_exists(started_at, :updated_at)"
        ),
        ExpressionAttributeNames={"#state": "state"},
        ExpressionAttributeValues={
            ":phase": {"S": phase},
            ":step": {"S": step},
            ":state": {"S": "RUNNING"},
            ":progress": _progress_map(completed_steps),
            ":retry_count": {"N": str(retry_count)},
            ":updated_at": {"S": now},
        },
    )


def finalize(
    *,
    run_id: str,
    state: str,
    phase: str,
    step: str,
    retry_count: int,
    last_error: dict | None = None,
    artifact_index_key: str | None = None,
) -> None:
    now = _now_iso()
    expr = (
        "SET phase = :phase, step = :step, #state = :state, progress = :progress, "
        "retry_count = :retry_count, finished_at = :finished_at, updated_at = :updated_at"
    )
    values: dict[str, dict] = {
        ":phase": {"S": phase},
        ":step": {"S": step},
        ":state": {"S": state},
        ":progress": _progress_map(TOTAL_STEPS),
        ":retry_count": {"N": str(retry_count)},
        ":finished_at": {"S": now},
        ":updated_at": {"S": now},
    }
    if last_error is not None:
        expr += ", last_error = :last_error"
        values[":last_error"] = {
            "M": {
                "step": {"S": str(last_error.get("step", step))},
                "reason": {"S": str(last_error.get("reason", "unknown"))[:500]},
                "retryable": {"BOOL": bool(last_error.get("retryable", False))},
                "category": {"S": str(last_error.get("category", "internal"))},
                "trace_id": {"S": str(last_error.get("trace_id", ""))},
            }
        }
    if artifact_index_key:
        expr += ", artifact_index_key = :artifact_index_key"
        values[":artifact_index_key"] = {"S": artifact_index_key}

    dynamodb.update_item(
        TableName=TABLE_NAME,
        Key={"run_id": {"S": run_id}},
        UpdateExpression=expr,
        ExpressionAttributeNames={"#state": "state"},
        ExpressionAttributeValues=values,
    )
