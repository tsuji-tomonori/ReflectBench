import base64
import json
import logging
import os
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

from app.common.api import json_response, problem_response, trace_id_from_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.client("dynamodb")
s3 = boto3.client("s3")

TABLE_NAME = os.environ["TABLE_NAME"]
ARTIFACTS_BUCKET = os.environ["ARTIFACTS_BUCKET"]

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


def _n(item: dict, key: str, default: int = 0) -> int:
    if key not in item:
        return default
    return int(item[key]["N"])


def _s(item: dict, key: str) -> str | None:
    if key not in item:
        return None
    return item[key].get("S")


def _parse_limit(raw: str | None) -> int:
    if raw is None or raw == "":
        return DEFAULT_LIMIT
    limit = int(raw)
    if limit < 1 or limit > MAX_LIMIT:
        raise ValueError("limit must be between 1 and 100")
    return limit


def _encode_token(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode("utf-8")).decode("ascii")


def _decode_token(token: str | None) -> int:
    if token is None or token == "":
        return 0
    try:
        decoded = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        offset = int(decoded)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("next_token is invalid") from exc
    if offset < 0:
        raise ValueError("next_token is invalid")
    return offset


def _to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _scan_runs() -> list[dict]:
    items: list[dict] = []
    start_key = None
    while True:
        kwargs = {"TableName": TABLE_NAME, "ConsistentRead": True}
        if start_key is not None:
            kwargs["ExclusiveStartKey"] = start_key
        res = dynamodb.scan(**kwargs)
        for item in res.get("Items", []):
            if item.get("kind", {}).get("S") == "IDEMPOTENCY":
                continue
            items.append(item)
        start_key = res.get("LastEvaluatedKey")
        if start_key is None:
            break
    items.sort(
        key=lambda item: (_s(item, "created_at") or "", _s(item, "run_id") or ""),
        reverse=True,
    )
    return items


def _summary_from_keys(keys: list[str]) -> dict:
    latest_key = keys[-1] if keys else None
    return {
        "count": len(keys),
        "latest_key": latest_key,
        "latest_modified_at": None,
    }


def _list_prefix_summary(prefix: str) -> dict:
    count = 0
    latest_key = None
    latest_modified = None
    token = None
    while True:
        kwargs = {"Bucket": ARTIFACTS_BUCKET, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        res = s3.list_objects_v2(**kwargs)
        for obj in res.get("Contents", []):
            count += 1
            modified = obj.get("LastModified")
            if latest_modified is None or (
                isinstance(modified, datetime) and modified > latest_modified
            ):
                latest_modified = modified
                latest_key = obj.get("Key")
        if not res.get("IsTruncated"):
            break
        token = res.get("NextContinuationToken")
    return {
        "count": count,
        "latest_key": latest_key,
        "latest_modified_at": _to_iso(latest_modified),
    }


def _object_exists(key: str | None) -> bool:
    if not key:
        return False
    try:
        s3.head_object(Bucket=ARTIFACTS_BUCKET, Key=key)
        return True
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise


def _load_artifact_index(key: str | None) -> dict | None:
    if not key:
        return None
    try:
        res = s3.get_object(Bucket=ARTIFACTS_BUCKET, Key=key)
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code in {"404", "NoSuchKey", "NotFound"}:
            return None
        raise
    body = res["Body"].read().decode("utf-8")
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        return None
    return parsed


def _build_s3_status(item: dict) -> dict:
    run_id = _s(item, "run_id")
    assert run_id is not None

    config_key = _s(item, "config_s3_key") or f"runs/{run_id}/config.json"
    artifact_index_key = _s(item, "artifact_index_key")
    artifact_index = _load_artifact_index(artifact_index_key)

    if artifact_index is not None:
        reports = _summary_from_keys(list(artifact_index.get("reports", [])))
        normalized = _summary_from_keys(list(artifact_index.get("normalized", [])))
        invalid = _summary_from_keys(list(artifact_index.get("invalid", [])))
    else:
        base = f"runs/{run_id}/"
        reports = _list_prefix_summary(base + "reports/")
        normalized = _list_prefix_summary(base + "normalized/")
        invalid = _list_prefix_summary(base + "invalid/")

    batch_output = _list_prefix_summary(f"runs/{run_id}/batch-output/")
    return {
        "config_exists": _object_exists(config_key),
        "artifact_index_exists": artifact_index is not None,
        "reports": reports,
        "normalized": normalized,
        "invalid": invalid,
        "batch_output": batch_output,
    }


def _build_run(item: dict) -> dict:
    progress = item.get("progress", {}).get("M", {})
    return {
        "run_id": _s(item, "run_id"),
        "phase": _s(item, "phase") or "UNKNOWN",
        "step": _s(item, "step"),
        "state": _s(item, "state") or "UNKNOWN",
        "progress": {
            "completed_steps": _n(progress, "completed_steps"),
            "total_steps": _n(progress, "total_steps", 18),
            "percent": _n(progress, "percent"),
        },
        "created_at": _s(item, "created_at"),
        "updated_at": _s(item, "updated_at"),
        "started_at": _s(item, "started_at"),
        "finished_at": _s(item, "finished_at"),
        "execution_name": _s(item, "execution_name"),
        "durable_execution_arn": _s(item, "durable_execution_arn"),
        "s3_status": _build_s3_status(item),
    }


def handler(event, _context):
    trace_id = trace_id_from_event(event)
    step = "LIST_RUNS"
    params = event.get("queryStringParameters") or {}

    try:
        limit = _parse_limit(params.get("limit"))
        offset = _decode_token(params.get("next_token"))
    except ValueError as exc:
        return problem_response(
            status_code=400,
            code="INVALID_QUERY",
            message=str(exc),
            category="validation",
            retryable=False,
            step=step,
            trace_id=trace_id,
        )

    logger.info(json.dumps({"trace_id": trace_id, "step": step, "limit": limit, "offset": offset}))

    items = _scan_runs()
    page = items[offset : offset + limit]
    next_offset = offset + len(page)
    next_token = _encode_token(next_offset) if next_offset < len(items) else None

    body = {
        "runs": [_build_run(item) for item in page],
        "returned_count": len(page),
        "total_count": len(items),
        "next_token": next_token,
    }
    return json_response(200, body, trace_id)
