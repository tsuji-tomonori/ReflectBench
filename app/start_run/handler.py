import datetime
import hashlib
import json
import os
import uuid

import boto3

dynamodb = boto3.client("dynamodb")
s3 = boto3.client("s3")
lambda_client = boto3.client("lambda")

TABLE_NAME = os.environ["TABLE_NAME"]
TABLE_GSI_NAME = os.environ.get("TABLE_GSI_NAME", "idempotency_key_index")
ARTIFACTS_BUCKET = os.environ["ARTIFACTS_BUCKET"]
ORCHESTRATOR_ARN = os.environ["ORCHESTRATOR_ARN"]


def _json_response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def _now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat()


def _request_hash(payload: dict) -> str:
    stable = {
        "loops": payload.get("loops"),
        "full_cross": payload.get("full_cross"),
        "shard_size": payload.get("shard_size", 500),
        "poll_interval_sec": payload.get("poll_interval_sec", 180),
        "editor_model": payload.get("editor_model", "apac.amazon.nova-micro-v1:0"),
    }
    text = json.dumps(stable, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _validate(payload: dict) -> tuple[bool, str]:
    if payload.get("loops") != 10:
        return False, "loops must be 10"
    if payload.get("full_cross") is not True:
        return False, "full_cross must be true"
    return True, ""


def _query_by_idempotency_key(idempotency_key: str) -> dict | None:
    result = dynamodb.query(
        TableName=TABLE_NAME,
        IndexName=TABLE_GSI_NAME,
        KeyConditionExpression="idempotency_key = :k",
        ExpressionAttributeValues={":k": {"S": idempotency_key}},
        Limit=1,
    )
    items = result.get("Items", [])
    return items[0] if items else None


def handler(event, _context):
    body_text = event.get("body") or "{}"
    payload = json.loads(body_text)

    ok, reason = _validate(payload)
    if not ok:
        return _json_response(400, {"error": reason})

    accepted_at = _now_iso()
    request_hash = _request_hash(payload)
    idempotency_key = payload.get("idempotency_key")

    if idempotency_key:
        existing = _query_by_idempotency_key(idempotency_key)
        if existing:
            if existing.get("request_hash", {}).get("S") == request_hash:
                run_id = existing["run_id"]["S"]
                return _json_response(
                    202,
                    {
                        "run_id": run_id,
                        "accepted_at": accepted_at,
                        "initial_phase": "STUDY1_ENUMERATE",
                        "state": "QUEUED",
                    },
                )
            return _json_response(
                409,
                {"error": "idempotency_key conflict with different payload"},
            )

    run_id = str(uuid.uuid4())
    config_key = f"runs/{run_id}/config.json"

    run_config = {
        "run_id": run_id,
        "region": "ap-southeast-2",
        "models": [
            "apac.amazon.nova-micro-v1:0",
            "google.gemma-3-12b-it",
            "mistral.ministral-3-8b-instruct",
            "qwen.qwen3-32b-v1:0",
        ],
        "loops": 10,
        "full_cross": True,
        "shard_size": payload.get("shard_size", 500),
        "poll_interval_sec": payload.get("poll_interval_sec", 180),
        "created_at": accepted_at,
    }
    s3.put_object(
        Bucket=ARTIFACTS_BUCKET,
        Key=config_key,
        Body=json.dumps(run_config, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )

    item = {
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
        "crea},
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
    }
    if idempotency_key:
        item["idempotency_key"] = {"S": idempotency_key}

    try:
        dynamodb.put_item(
            TableName=TABLE_NAME,
            Item=item,
            ConditionExpression="attribute_not_exists(run_id)",
        )
    except dynamodb.exceptions.ConditionalCheckFailedException:
        if idempotency_key:
            existing = _get_item_by_run_id(run_id)
            if existing and existing.get("request_hash", {}).get("S") == request_hash:
                return _json_response(
                    202,
                    {
                        "run_id": run_id,
                        "accepted_at": accepted_at,
                        "initial_phase": "STUDY1_ENUMERATE",
                        "state": existing.get("state", {}).get("S", "QUEUED"),
                    },
                )
            return _json_response(
                409,
                {"error": "idempotency_key conflict with different payload"},
            )
        raise

    lambda_client.invoke(
        FunctionName=ORCHESTRATOR_ARN,
        InvocationType="Event",
        Payload=json.dumps({"run_id": run_id}).encode("utf-8"),
    )

    return _json_response(
        202,
        {
            "run_id": run_id,
            "accepted_at": accepted_at,
            "initial_phase": "STUDY1_ENUMERATE",
            "state": "QUEUED",
        },
    )
