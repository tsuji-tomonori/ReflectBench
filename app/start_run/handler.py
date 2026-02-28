import datetime
import hashlib
import json
import logging
import os
import uuid

import boto3
from botocore.exceptions import ClientError
from pydantic import ValidationError

from app.common.api import json_response, problem_response, trace_id_from_event
from app.common.models import DEFAULT_MODELS, RunCreateRequest

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.client("dynamodb")
s3 = boto3.client("s3")
lambda_client = boto3.client("lambda")
cloudwatch = boto3.client("cloudwatch")

TABLE_NAME = os.environ["TABLE_NAME"]
ARTIFACTS_BUCKET = os.environ["ARTIFACTS_BUCKET"]
ORCHESTRATOR_ARN = os.environ["ORCHESTRATOR_ARN"]
EDITOR_MODEL = "apac.amazon.nova-micro-v1:0"
METRIC_NAMESPACE = os.environ.get("METRIC_NAMESPACE", "ReflectBench/Run")


def _now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat()


def _request_hash(payload: RunCreateRequest | dict) -> str:
    if isinstance(payload, dict):
        payload = RunCreateRequest.model_validate(payload)
    stable = {
        "loops": payload.loops,
        "full_cross": payload.full_cross,
        "shard_size": payload.shard_size,
        "poll_interval_sec": payload.poll_interval_sec,
        "editor_model": payload.editor_model,
    }
    text = json.dumps(stable, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _idempotency_pk(idempotency_key: str) -> str:
    return f"idempotency#{idempotency_key}"


def _load_idempotency(idempotency_key: str) -> dict | None:
    res = dynamodb.get_item(
        TableName=TABLE_NAME,
        Key={"run_id": {"S": _idempotency_pk(idempotency_key)}},
        ConsistentRead=True,
    )
    return res.get("Item")


def _accepted_body(run_id: str, accepted_at: str, phase: str, state: str) -> dict:
    return {
        "run_id": run_id,
        "accepted_at": accepted_at,
        "initial_phase": phase,
        "state": state,
    }


def _emit_run_started_metric(run_id: str, trace_id: str) -> None:
    try:
        cloudwatch.put_metric_data(
            Namespace=METRIC_NAMESPACE,
            MetricData=[
                {
                    "MetricName": "RunStarted",
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
                    "step": "POST_RUNS",
                    "run_id": run_id,
                    "message": f"failed to publish RunStarted metric: {exc}",
                },
                ensure_ascii=False,
            )
        )


def handler(event, _context):
    trace_id = trace_id_from_event(event)
    step = "POST_RUNS"
    logger.info(json.dumps({"trace_id": trace_id, "step": step, "message": "request_received"}))

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
        request = RunCreateRequest.model_validate(parsed)
    except ValidationError as exc:
        return problem_response(
            status_code=400,
            code="INVALID_REQUEST",
            message="request validation failed",
            category="validation",
            retryable=False,
            step=step,
            trace_id=trace_id,
            extra={"detail": exc.errors()},
        )

    accepted_at = _now_iso()
    request_hash = _request_hash(request)

    if request.idempotency_key:
        existing = _load_idempotency(request.idempotency_key)
        if existing:
            existing_hash = existing.get("request_hash", {}).get("S")
            existing_run_id = existing.get("linked_run_id", {}).get("S")
            if existing_hash == request_hash and existing_run_id:
                logger.info(
                    json.dumps(
                        {
                            "trace_id": trace_id,
                            "step": step,
                            "message": "idempotent_replay",
                            "run_id": existing_run_id,
                        }
                    )
                )
                return json_response(
                    202,
                    _accepted_body(existing_run_id, accepted_at, "STUDY1_ENUMERATE", "QUEUED"),
                    trace_id,
                )

            return problem_response(
                status_code=409,
                code="IDEMPOTENCY_CONFLICT",
                message="idempotency_key conflict with different payload",
                category="validation",
                retryable=False,
                step=step,
                trace_id=trace_id,
            )

    run_id = str(uuid.uuid4())
    config_key = f"runs/{run_id}/config.json"
    run_config = {
        "run_id": run_id,
        "region": "ap-southeast-2",
        "models": DEFAULT_MODELS,
        "loops": 10,
        "full_cross": True,
        "shard_size": request.shard_size,
        "poll_interval_sec": request.poll_interval_sec,
        "editor_model": EDITOR_MODEL,
        "created_at": accepted_at,
    }

    try:
        s3.put_object(
            Bucket=ARTIFACTS_BUCKET,
            Key=config_key,
            Body=json.dumps(run_config, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )

        run_item = {
            "run_id": {"S": run_id},
            "phase": {"S": "STUDY1_ENUMERATE"},
            "state": {"S": "QUEUED"},
            "retry_count": {"N": "0"},
            "progress": {
                "M": {
                    "completed_steps": {"N": "0"},
                    "total_steps": {"N": "10"},
                    "percent": {"N": "0"},
                }
            },
            "request_hash": {"S": request_hash},
            "config_s3_key": {"S": config_key},
            "created_at": {"S": accepted_at},
            "updated_at": {"S": accepted_at},
            "orchestration_state": {
                "S": json.dumps(
                    {"cursor": 0, "phase_counts": {}, "invalid_counts": {}}, ensure_ascii=False
                )
            },
        }

        transact_items = [
            {
                "Put": {
                    "TableName": TABLE_NAME,
                    "Item": run_item,
                    "ConditionExpression": "attribute_not_exists(run_id)",
                }
            }
        ]

        if request.idempotency_key:
            transact_items.append(
                {
                    "Put": {
                        "TableName": TABLE_NAME,
                        "Item": {
                            "run_id": {"S": _idempotency_pk(request.idempotency_key)},
                            "kind": {"S": "IDEMPOTENCY"},
                            "idempotency_key": {"S": request.idempotency_key},
                            "request_hash": {"S": request_hash},
                            "linked_run_id": {"S": run_id},
                            "created_at": {"S": accepted_at},
                        },
                        "ConditionExpression": "attribute_not_exists(run_id)",
                    }
                }
            )

        dynamodb.transact_write_items(TransactItems=transact_items)

        lambda_client.invoke(
            FunctionName=ORCHESTRATOR_ARN,
            InvocationType="Event",
            Payload=json.dumps({"run_id": run_id, "trace_id": trace_id}).encode("utf-8"),
        )
        _emit_run_started_metric(run_id, trace_id)
    except ClientError as exc:
        if (
            exc.response.get("Error", {}).get("Code") == "TransactionCanceledException"
            and request.idempotency_key
        ):
            existing = _load_idempotency(request.idempotency_key)
            if existing and existing.get("request_hash", {}).get("S") == request_hash:
                linked = existing.get("linked_run_id", {}).get("S")
                if linked:
                    return json_response(
                        202,
                        _accepted_body(linked, accepted_at, "STUDY1_ENUMERATE", "QUEUED"),
                        trace_id,
                    )
            return problem_response(
                status_code=409,
                code="IDEMPOTENCY_CONFLICT",
                message="idempotency_key conflict with different payload",
                category="validation",
                retryable=False,
                step=step,
                trace_id=trace_id,
            )

        logger.exception("start_run failed")
        return problem_response(
            status_code=500,
            code="START_RUN_FAILED",
            message="failed to start run",
            category="internal",
            retryable=False,
            step=step,
            trace_id=trace_id,
        )

    logger.info(
        json.dumps(
            {"trace_id": trace_id, "step": step, "message": "run_accepted", "run_id": run_id}
        )
    )
    return json_response(
        202, _accepted_body(run_id, accepted_at, "STUDY1_ENUMERATE", "QUEUED"), trace_id
    )
