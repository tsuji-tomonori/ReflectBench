import importlib
import json
import os
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError


@pytest.fixture(scope="module")
def mod():
    os.environ.setdefault("AWS_DEFAULT_REGION", "ap-southeast-2")
    os.environ.setdefault("TABLE_NAME", "run_control_table")
    os.environ.setdefault("ARTIFACTS_BUCKET", "dummy-bucket")
    os.environ.setdefault(
        "ORCHESTRATOR_ARN",
        "arn:aws:lambda:ap-southeast-2:123:function:orchestrator_durable_fn:live",
    )
    return importlib.import_module("app.start_run.handler")


def _event(body: dict) -> dict:
    return {"body": json.dumps(body)}


def test_returns_400_when_constraints_invalid(mod):
    res = mod.handler(_event({"loops": 9, "full_cross": True}), None)
    assert res["statusCode"] == 400


def test_returns_400_when_body_is_not_object(mod):
    res = mod.handler({"body": "[]"}, None)
    assert res["statusCode"] == 400


def test_returns_existing_run_id_on_idempotent_retry(mod):
    body = {
        "loops": 10,
        "full_cross": True,
        "idempotency_key": "k1",
    }

    with patch.object(
        mod,
        "_load_idempotency",
        return_value={
            "request_hash": {"S": mod._request_hash(body)},
            "linked_run_id": {"S": "123e4567-e89b-42d3-a456-426614174000"},
        },
    ):
        res = mod.handler(_event(body), None)

    payload = json.loads(res["body"])
    assert res["statusCode"] == 202
    assert payload["run_id"] == "123e4567-e89b-42d3-a456-426614174000"
    assert payload["phase"] == "STUDY1"
    assert payload["step"] == "STUDY1_ENUMERATE"
    assert payload["execution_name"] == "123e4567-e89b-42d3-a456-426614174000"


def test_returns_409_when_same_key_different_payload(mod):
    body = {
        "loops": 10,
        "full_cross": True,
        "idempotency_key": "k1",
        "poll_interval_sec": 120,
    }

    with patch.object(
        mod,
        "_load_idempotency",
        return_value={
            "linked_run_id": {"S": "123e4567-e89b-42d3-a456-426614174000"},
            "request_hash": {"S": "different-hash"},
        },
    ):
        res = mod.handler(_event(body), None)

    assert res["statusCode"] == 409


def test_returns_202_when_new_run_created(mod):
    with (
        patch.object(mod, "_load_idempotency", return_value=None),
        patch.object(mod.s3, "put_object", return_value={}),
        patch.object(mod.dynamodb, "transact_write_items", return_value={}),
        patch.object(
            mod.lambda_client,
            "invoke",
            return_value={
                "StatusCode": 202,
                "DurableExecutionArn": (
                    "arn:aws:lambda:ap-southeast-2:123:durable-execution/"
                    "orchestrator_durable_fn/live/run-1"
                ),
            },
        ) as invoke,
        patch.object(mod.projection, "save_execution_metadata") as save_execution,
        patch.object(mod.cloudwatch, "put_metric_data", return_value={}) as put_metric,
    ):
        res = mod.handler(_event({"loops": 10, "full_cross": True}), None)

    body = json.loads(res["body"])
    assert res["statusCode"] == 202
    assert body["phase"] == "STUDY1"
    assert body["step"] == "STUDY1_ENUMERATE"
    assert body["durable_execution_arn"].endswith("/run-1")
    assert invoke.call_args.kwargs["DurableExecutionName"] == body["run_id"]
    save_execution.assert_called_once()
    metric = put_metric.call_args.kwargs["MetricData"][0]
    assert metric["MetricName"] == "RunStarted"


def test_returns_202_when_durable_execution_already_started(mod):
    error = ClientError(
        {
            "Error": {
                "Code": "DurableExecutionAlreadyStartedException",
                "Message": "duplicate execution name",
            }
        },
        "Invoke",
    )

    with (
        patch.object(mod, "_load_idempotency", return_value=None),
        patch.object(mod.s3, "put_object", return_value={}),
        patch.object(mod.dynamodb, "transact_write_items", return_value={}),
        patch.object(mod.lambda_client, "invoke", side_effect=error),
        patch.object(mod.projection, "save_execution_metadata") as save_execution,
    ):
        res = mod.handler(_event({"loops": 10, "full_cross": True}), None)

    body = json.loads(res["body"])
    assert res["statusCode"] == 202
    assert body["state"] == "QUEUED"
    save_execution.assert_called_once()
