import json
import logging
import os

import boto3

from app.common.api import is_valid_run_id, json_response, problem_response, trace_id_from_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
dynamodb = boto3.client("dynamodb")
ARTIFACTS_BUCKET = os.environ["ARTIFACTS_BUCKET"]
TABLE_NAME = os.environ.get("TABLE_NAME")


def _list_keys(prefix: str) -> list[str]:
    keys: list[str] = []
    token = None
    while True:
        kwargs = {"Bucket": ARTIFACTS_BUCKET, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        res = s3.list_objects_v2(**kwargs)
        for obj in res.get("Contents", []):
            keys.append(obj["Key"])
        if not res.get("IsTruncated"):
            break
        token = res.get("NextContinuationToken")
    return sorted(keys)


def _run_exists(run_id: str) -> bool:
    res = s3.list_objects_v2(
        Bucket=ARTIFACTS_BUCKET, Prefix=f"runs/{run_id}/config.json", MaxKeys=1
    )
    return bool(res.get("Contents"))


def _b(item: dict, key: str) -> bool | None:
    if key not in item:
        return None
    return item[key].get("BOOL")


def _ls(item: dict, key: str) -> list[str]:
    values = item.get(key, {}).get("L", [])
    return [entry.get("S", "") for entry in values if entry.get("S")]


def _load_run_item(run_id: str) -> dict | None:
    if not TABLE_NAME:
        return None
    res = dynamodb.get_item(
        TableName=TABLE_NAME,
        Key={"run_id": {"S": run_id}},
        ConsistentRead=True,
    )
    item = res.get("Item")
    if not item or item.get("kind", {}).get("S") == "IDEMPOTENCY":
        return None
    return item


def _lineage_body(item: dict | None) -> dict | None:
    if not item:
        return None
    parent_run_id = item.get("parent_run_id", {}).get("S")
    if not parent_run_id:
        return None
    return {"parent_run_id": parent_run_id}


def _repair_body(item: dict | None) -> dict | None:
    if not item:
        return None

    repair_phase = item.get("repair_phase", {}).get("S")
    repair_scope = item.get("repair_scope", {}).get("S")
    repair_mode = item.get("repair_mode", {}).get("S")
    rebuild_downstream = _b(item, "rebuild_downstream")
    source_invalid_keys = _ls(item, "source_invalid_keys")

    if (
        repair_phase is None
        and repair_scope is None
        and repair_mode is None
        and rebuild_downstream is None
        and not source_invalid_keys
    ):
        return None

    return {
        "phase": repair_phase,
        "scope": repair_scope,
        "mode": repair_mode,
        "rebuild_downstream": rebuild_downstream,
        "source_invalid_keys": source_invalid_keys,
    }


def handler(event, _context):
    trace_id = trace_id_from_event(event)
    step = "GET_RUN_ARTIFACTS"
    run_id_value = (event.get("pathParameters") or {}).get("run_id")
    run_id = run_id_value if isinstance(run_id_value, str) else None

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

    assert run_id is not None

    logger.info(json.dumps({"trace_id": trace_id, "step": step, "run_id": run_id}))
    if not _run_exists(run_id):
        return problem_response(
            status_code=404,
            code="RUN_NOT_FOUND",
            message="run_id not found",
            category="validation",
            retryable=False,
            step=step,
            trace_id=trace_id,
        )

    base = f"runs/{run_id}/"
    item = _load_run_item(run_id)
    body = {
        "run_id": run_id,
        "reports": _list_keys(base + "reports/"),
        "normalized": _list_keys(base + "normalized/"),
        "invalid": _list_keys(base + "invalid/"),
        "lineage": _lineage_body(item),
        "repair": _repair_body(item),
    }
    return json_response(200, body, trace_id)
