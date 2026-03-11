import datetime
import hashlib
import json
import logging
import os
import uuid

import boto3
from botocore.exceptions import ClientError
from pydantic import ValidationError

from app.common.api import is_valid_run_id, json_response, problem_response, trace_id_from_event
from app.common.models import RepairRunCreateRequest
from app.orchestrator import projection

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.client("dynamodb")
s3 = boto3.client("s3")
lambda_client = boto3.client("lambda")
cloudwatch = boto3.client("cloudwatch")

TABLE_NAME = os.environ["TABLE_NAME"]
ARTIFACTS_BUCKET = os.environ["ARTIFACTS_BUCKET"]
ORCHESTRATOR_ARN = os.environ["ORCHESTRATOR_ARN"]
METRIC_NAMESPACE = os.environ.get("METRIC_NAMESPACE", "ReflectBench/Run")
TERMINAL_STATES = {"SUCCEEDED", "FAILED", "PARTIAL", "CANCELLED"}


def _now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat()


def _request_hash(parent_run_id: str, payload: RepairRunCreateRequest | dict) -> str:
    request: RepairRunCreateRequest
    if isinstance(payload, dict):
        request = RepairRunCreateRequest.model_validate(payload)
    else:
        request = payload
    stable = {
        "parent_run_id": parent_run_id,
        "phase": request.phase,
        "scope": request.scope,
        "mode": request.mode,
        "models": sorted(request.models or []),
        "record_ids": sorted(request.record_ids or []),
        "rebuild_downstream": request.rebuild_downstream,
    }
    text = json.dumps(stable, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_run_item(run_id: str) -> dict | None:
    res = dynamodb.get_item(
        TableName=TABLE_NAME,
        Key={"run_id": {"S": run_id}},
        ConsistentRead=True,
    )
    item = res.get("Item")
    if not item or item.get("kind", {}).get("S") == "IDEMPOTENCY":
        return None
    return item


def _load_parent_config(run_id: str) -> dict:
    res = s3.get_object(Bucket=ARTIFACTS_BUCKET, Key=f"runs/{run_id}/config.json")
    return json.loads(res["Body"].read().decode("utf-8"))


def _s3_list(prefix: str) -> list[str]:
    keys: list[str] = []
    token: str | None = None
    while True:
        kwargs: dict = {"Bucket": ARTIFACTS_BUCKET, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        res = s3.list_objects_v2(**kwargs)
        for obj in res.get("Contents", []):
            keys.append(obj["Key"])
        if not res.get("IsTruncated"):
            break
        token = res.get("NextContinuationToken")
    return sorted(keys)


def _s3_get_jsonl(key: str) -> list[dict]:
    res = s3.get_object(Bucket=ARTIFACTS_BUCKET, Key=key)
    raw = res["Body"].read().decode("utf-8")
    rows: list[dict] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parsed = json.loads(line)
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def _s3_put_json(key: str, payload: dict) -> None:
    s3.put_object(
        Bucket=ARTIFACTS_BUCKET,
        Key=key,
        Body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )


def _s3_put_jsonl(key: str, rows: list[dict]) -> None:
    body = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n"
    s3.put_object(
        Bucket=ARTIFACTS_BUCKET,
        Key=key,
        Body=body.encode("utf-8"),
        ContentType="application/jsonl",
    )


def _load_manifest_index(run_id: str, phase: str) -> dict[str, dict]:
    manifest_keys = [
        key for key in _s3_list(f"runs/{run_id}/manifests/{phase}/") if key.endswith(".jsonl")
    ]
    indexed: dict[str, dict] = {}
    for key in manifest_keys:
        for row in _s3_get_jsonl(key):
            record_id = row.get("record_id")
            if isinstance(record_id, str) and record_id:
                indexed[record_id] = row
    return indexed


def _fallback_invalid_output(record_id: str, reason: str) -> dict:
    return {
        "recordId": record_id,
        "error": {
            "errorMessage": reason,
        },
    }


def _parse_invalid_output(record_id: str, invalid_row: dict) -> dict:
    raw_text = invalid_row.get("raw_text")
    if not isinstance(raw_text, str) or not raw_text.strip():
        return _fallback_invalid_output(record_id, str(invalid_row.get("reason", "invalid raw_text")))
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        return _fallback_invalid_output(record_id, str(invalid_row.get("reason", "invalid raw_text")))
    if not isinstance(parsed, dict):
        return _fallback_invalid_output(record_id, str(invalid_row.get("reason", "invalid raw_text")))
    return parsed


def _build_seed_rows(parent_run_id: str, request: RepairRunCreateRequest) -> tuple[list[dict], list[str]]:
    model_filter = set(request.models or [])
    record_filter = set(request.record_ids or [])
    manifest_index = _load_manifest_index(parent_run_id, request.phase)
    invalid_keys = [
        key for key in _s3_list(f"runs/{parent_run_id}/invalid/{request.phase}/") if key.endswith(".jsonl")
    ]

    seed_rows: list[dict] = []
    source_invalid_keys: list[str] = []
    seen_record_ids: set[str] = set()
    for key in invalid_keys:
        rows = _s3_get_jsonl(key)
        matched_in_key = False
        for invalid_row in rows:
            record_id = invalid_row.get("record_id")
            model_id = invalid_row.get("model")
            if not isinstance(record_id, str) or not record_id:
                continue
            if record_id in seen_record_ids:
                continue
            if model_filter and model_id not in model_filter:
                continue
            if record_filter and record_id not in record_filter:
                continue
            manifest_row = manifest_index.get(record_id)
            if manifest_row is None:
                raise ValueError(f"parent manifest row is missing for record_id={record_id}")
            seed_rows.append(
                {
                    "record_id": record_id,
                    "model_id": manifest_row["model_id"],
                    "source_invalid_key": key,
                    "manifest_row": manifest_row,
                    "invalid_output": _parse_invalid_output(record_id, invalid_row),
                }
            )
            source_invalid_keys.append(key)
            seen_record_ids.add(record_id)
            matched_in_key = True
        if matched_in_key:
            continue
    return seed_rows, list(dict.fromkeys(source_invalid_keys))


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
    return items


def _find_duplicate_repair(parent_run_id: str, request_hash: str) -> str | None:
    for item in _scan_runs():
        if item.get("parent_run_id", {}).get("S") != parent_run_id:
            continue
        if item.get("request_hash", {}).get("S") != request_hash:
            continue
        run_id = item.get("run_id", {}).get("S")
        if isinstance(run_id, str) and run_id:
            return run_id
    return None


def _accepted_body(
    *,
    run_id: str,
    parent_run_id: str,
    accepted_at: str,
    execution_name: str,
    mode: str,
    scope: str,
    phase: str,
    rebuild_downstream: bool,
    source_invalid_keys: list[str],
    durable_execution_arn: str | None = None,
) -> dict:
    return {
        "run_id": run_id,
        "accepted_at": accepted_at,
        "phase": "STUDY1",
        "step": "STUDY1_ENUMERATE",
        "state": "QUEUED",
        "execution_name": execution_name,
        "durable_execution_arn": durable_execution_arn,
        "lineage": {
            "parent_run_id": parent_run_id,
        },
        "repair": {
            "phase": phase,
            "scope": scope,
            "mode": mode,
            "rebuild_downstream": rebuild_downstream,
            "source_invalid_keys": source_invalid_keys,
        },
    }


def _emit_repair_started_metric(run_id: str, trace_id: str) -> None:
    try:
        cloudwatch.put_metric_data(
            Namespace=METRIC_NAMESPACE,
            MetricData=[
                {
                    "MetricName": "RepairRunStarted",
                    "Unit": "Count",
                    "Value": 1.0,
                    "Dimensions": [{"Name": "RunId", "Value": run_id}],
                }
            ],
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            json.dumps(
                {
                    "trace_id": trace_id,
                    "step": "POST_RUN_REPAIRS",
                    "run_id": run_id,
                    "message": f"failed to publish RepairRunStarted metric: {exc}",
                },
                ensure_ascii=False,
            )
        )


def handler(event, _context):
    trace_id = trace_id_from_event(event)
    step = "POST_RUN_REPAIRS"
    parent_run_id = (event.get("pathParameters") or {}).get("run_id")

    if not is_valid_run_id(parent_run_id):
        return problem_response(
            status_code=400,
            code="INVALID_RUN_ID",
            message="run_id format is invalid",
            category="validation",
            retryable=False,
            step=step,
            trace_id=trace_id,
        )

    logger.info(
        json.dumps(
            {
                "trace_id": trace_id,
                "step": step,
                "parent_run_id": parent_run_id,
                "message": "request_received",
            }
        )
    )

    try:
        parsed = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return problem_response(
            status_code=400,
            code="INVALID_JSON",
            message="body must be valid JSON",
            category="validation",
            retryable=False,
            step=step,
            trace_id=trace_id,
        )

    if not isinstance(parsed, dict):
        return problem_response(
            status_code=400,
            code="INVALID_BODY_TYPE",
            message="body must be JSON object",
            category="validation",
            retryable=False,
            step=step,
            trace_id=trace_id,
        )

    try:
        request = RepairRunCreateRequest.model_validate(parsed)
    except ValidationError as exc:
        return problem_response(
            status_code=400,
            code="INVALID_REQUEST",
            message="request validation failed",
            category="validation",
            retryable=False,
            step=step,
            trace_id=trace_id,
            extra={"detail": json.loads(exc.json())},
        )

    assert parent_run_id is not None

    parent_item = _load_run_item(parent_run_id)
    if parent_item is None:
        return problem_response(
            status_code=404,
            code="RUN_NOT_FOUND",
            message="run_id not found",
            category="validation",
            retryable=False,
            step=step,
            trace_id=trace_id,
        )

    parent_state = parent_item.get("state", {}).get("S")
    if parent_state not in TERMINAL_STATES:
        return problem_response(
            status_code=409,
            code="PARENT_RUN_NOT_TERMINAL",
            message="parent run must be in terminal state",
            category="validation",
            retryable=False,
            step=step,
            trace_id=trace_id,
        )

    try:
        parent_config = _load_parent_config(parent_run_id)
    except Exception:  # noqa: BLE001
        logger.exception("failed to load parent config")
        return problem_response(
            status_code=500,
            code="LOAD_PARENT_CONFIG_FAILED",
            message="failed to load parent run config",
            category="internal",
            retryable=False,
            step=step,
            trace_id=trace_id,
        )

    request_hash = _request_hash(parent_run_id, request)
    duplicate_run_id = _find_duplicate_repair(parent_run_id, request_hash)
    if duplicate_run_id:
        return problem_response(
            status_code=409,
            code="REPAIR_ALREADY_EXISTS",
            message="duplicate repair request already exists",
            category="validation",
            retryable=False,
            step=step,
            trace_id=trace_id,
            extra={"duplicate_run_id": duplicate_run_id},
        )

    try:
        seed_rows, source_invalid_keys = _build_seed_rows(parent_run_id, request)
    except ValueError as exc:
        return problem_response(
            status_code=400,
            code="INVALID_REPAIR_TARGET",
            message=str(exc),
            category="validation",
            retryable=False,
            step=step,
            trace_id=trace_id,
        )

    if not seed_rows:
        return problem_response(
            status_code=409,
            code="NO_REPAIR_TARGETS",
            message="no invalid records matched the requested repair scope",
            category="validation",
            retryable=False,
            step=step,
            trace_id=trace_id,
        )

    accepted_at = _now_iso()
    run_id = str(uuid.uuid4())
    execution_name = run_id
    config_key = f"runs/{run_id}/config.json"
    seed_key = f"runs/{run_id}/repair/seed.jsonl"
    repair_config = {
        **parent_config,
        "run_id": run_id,
        "created_at": accepted_at,
        "parent_run_id": parent_run_id,
        "repair_phase": request.phase,
        "repair_scope": request.scope,
        "repair_mode": request.mode,
        "repair_models": request.models or [],
        "repair_record_ids": request.record_ids or [],
        "rebuild_downstream": request.rebuild_downstream,
        "source_invalid_keys": source_invalid_keys,
        "repair_seed_key": seed_key,
    }

    try:
        _s3_put_json(config_key, repair_config)
        _s3_put_jsonl(seed_key, seed_rows)

        run_item = projection.build_run_item(
            run_id=run_id,
            accepted_at=accepted_at,
            request_hash=request_hash,
            config_s3_key=config_key,
            execution_name=execution_name,
            parent_run_id=parent_run_id,
            repair_phase=request.phase,
            repair_scope=request.scope,
            repair_mode=request.mode,
            rebuild_downstream=request.rebuild_downstream,
            source_invalid_keys=source_invalid_keys,
        )
        dynamodb.put_item(
            TableName=TABLE_NAME,
            Item=run_item,
            ConditionExpression="attribute_not_exists(run_id)",
        )

        invoke_response = lambda_client.invoke(
            FunctionName=ORCHESTRATOR_ARN,
            InvocationType="Event",
            DurableExecutionName=execution_name,
            Payload=json.dumps({"run_id": run_id, "trace_id": trace_id}).encode("utf-8"),
        )
        durable_execution_arn = invoke_response.get("DurableExecutionArn")
        projection.save_execution_metadata(
            run_id=run_id,
            execution_name=execution_name,
            durable_execution_arn=durable_execution_arn,
        )
        _emit_repair_started_metric(run_id, trace_id)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "DurableExecutionAlreadyStartedException":
            projection.save_execution_metadata(
                run_id=run_id,
                execution_name=execution_name,
                durable_execution_arn=None,
            )
            return json_response(
                202,
                _accepted_body(
                    run_id=run_id,
                    parent_run_id=parent_run_id,
                    accepted_at=accepted_at,
                    execution_name=execution_name,
                    phase=request.phase,
                    scope=request.scope,
                    mode=request.mode,
                    rebuild_downstream=request.rebuild_downstream,
                    source_invalid_keys=source_invalid_keys,
                ),
                trace_id,
            )

        logger.exception("repair run start failed")
        return problem_response(
            status_code=500,
            code="START_REPAIR_FAILED",
            message="failed to start repair run",
            category="internal",
            retryable=False,
            step=step,
            trace_id=trace_id,
        )

    logger.info(
        json.dumps(
            {
                "trace_id": trace_id,
                "step": step,
                "run_id": run_id,
                "parent_run_id": parent_run_id,
                "message": "repair_run_accepted",
            }
        )
    )
    return json_response(
        202,
        _accepted_body(
            run_id=run_id,
            parent_run_id=parent_run_id,
            accepted_at=accepted_at,
            execution_name=execution_name,
            phase=request.phase,
            scope=request.scope,
            mode=request.mode,
            rebuild_downstream=request.rebuild_downstream,
            source_invalid_keys=source_invalid_keys,
            durable_execution_arn=durable_execution_arn if "durable_execution_arn" in locals() else None,
        ),
        trace_id,
    )
