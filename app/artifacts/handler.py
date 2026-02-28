import json
import logging
import os

import boto3

from app.common.api import is_valid_run_id, json_response, problem_response, trace_id_from_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
ARTIFACTS_BUCKET = os.environ["ARTIFACTS_BUCKET"]


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


def handler(event, _context):
    trace_id = trace_id_from_event(event)
    step = "GET_RUN_ARTIFACTS"
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
    body = {
        "run_id": run_id,
        "reports": _list_keys(base + "reports/"),
        "normalized": _list_keys(base + "normalized/"),
        "invalid": _list_keys(base + "invalid/"),
    }
    return json_response(200, body, trace_id)
