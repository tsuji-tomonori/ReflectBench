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
    return importlib.import_module("app.repair_run.handler")


def _event(run_id: str, body: dict) -> dict:
    return {
        "pathParameters": {"run_id": run_id},
        "body": json.dumps(body),
    }


def test_returns_404_when_parent_run_missing(mod):
    with patch.object(mod, "_load_run_item", return_value=None):
        res = mod.handler(
            _event(
                "123e4567-e89b-42d3-a456-426614174000",
                {"phase": "study1", "scope": "invalid_only", "mode": "rerun"},
            ),
            None,
        )

    assert res["statusCode"] == 404


def test_returns_409_when_parent_run_is_not_terminal(mod):
    with patch.object(mod, "_load_run_item", return_value={"state": {"S": "RUNNING"}}):
        res = mod.handler(
            _event(
                "123e4567-e89b-42d3-a456-426614174000",
                {"phase": "study1", "scope": "invalid_only", "mode": "rerun"},
            ),
            None,
        )

    assert res["statusCode"] == 409


def test_returns_409_when_duplicate_repair_exists(mod):
    with (
        patch.object(mod, "_load_run_item", return_value={"state": {"S": "PARTIAL"}}),
        patch.object(mod, "_load_parent_config", return_value={"models": ["apac.amazon.nova-micro-v1:0"]}),
        patch.object(
            mod,
            "_find_duplicate_repair",
            return_value="123e4567-e89b-42d3-a456-426614174010",
        ),
    ):
        res = mod.handler(
            _event(
                "123e4567-e89b-42d3-a456-426614174000",
                {"phase": "study1", "scope": "invalid_only", "mode": "rerun"},
            ),
            None,
        )

    body = json.loads(res["body"])
    assert res["statusCode"] == 409
    assert body["duplicate_run_id"] == "123e4567-e89b-42d3-a456-426614174010"


def test_returns_409_when_no_invalid_targets_match(mod):
    with (
        patch.object(mod, "_load_run_item", return_value={"state": {"S": "PARTIAL"}}),
        patch.object(mod, "_load_parent_config", return_value={"models": ["apac.amazon.nova-micro-v1:0"]}),
        patch.object(mod, "_find_duplicate_repair", return_value=None),
        patch.object(mod, "_build_seed_rows", return_value=([], [])),
    ):
        res = mod.handler(
            _event(
                "123e4567-e89b-42d3-a456-426614174000",
                {"phase": "study1", "scope": "invalid_only", "mode": "renormalize"},
            ),
            None,
        )

    assert res["statusCode"] == 409


def test_returns_202_when_new_repair_run_created(mod):
    seed_rows = [
        {
            "record_id": "rec-1",
            "model_id": "apac.amazon.nova-micro-v1:0",
            "source_invalid_key": "runs/parent/invalid/study1/model-a/invalid.jsonl",
            "manifest_row": {
                "record_id": "rec-1",
                "run_id": "123e4567-e89b-42d3-a456-426614174000",
                "phase": "study1",
                "model_id": "apac.amazon.nova-micro-v1:0",
                "temperature": 0.9,
                "prompt_type": "FACTUAL",
                "target": "x",
                "loop_index": 0,
            },
            "invalid_output": {"recordId": "rec-1", "error": {"errorMessage": "parse failed"}},
        }
    ]
    source_invalid_keys = ["runs/parent/invalid/study1/model-a/invalid.jsonl"]

    with (
        patch.object(mod, "_load_run_item", return_value={"state": {"S": "PARTIAL"}}),
        patch.object(
            mod,
            "_load_parent_config",
            return_value={
                "models": ["apac.amazon.nova-micro-v1:0"],
                "loops": 10,
                "full_cross": True,
                "shard_size": 500,
                "poll_interval_sec": 180,
                "editor_model": "apac.amazon.nova-micro-v1:0",
            },
        ),
        patch.object(mod, "_find_duplicate_repair", return_value=None),
        patch.object(mod, "_build_seed_rows", return_value=(seed_rows, source_invalid_keys)),
        patch.object(mod.s3, "put_object", return_value={}) as put_object,
        patch.object(mod.projection, "build_run_item", return_value={"run_id": {"S": "child"}}) as build_item,
        patch.object(mod.dynamodb, "put_item", return_value={}),
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
        res = mod.handler(
            _event(
                "123e4567-e89b-42d3-a456-426614174000",
                {
                    "phase": "study1",
                    "scope": "invalid_only",
                    "mode": "rerun",
                    "rebuild_downstream": True,
                },
            ),
            None,
        )

    body = json.loads(res["body"])
    assert res["statusCode"] == 202
    assert body["lineage"] == {
        "parent_run_id": "123e4567-e89b-42d3-a456-426614174000",
    }
    assert body["repair"]["mode"] == "rerun"
    assert body["repair"]["source_invalid_keys"] == source_invalid_keys
    assert put_object.call_count == 2
    assert invoke.call_args.kwargs["DurableExecutionName"] == body["run_id"]
    assert build_item.call_args.kwargs["parent_run_id"] == "123e4567-e89b-42d3-a456-426614174000"
    assert build_item.call_args.kwargs["repair_mode"] == "rerun"
    save_execution.assert_called_once()
    metric = put_metric.call_args.kwargs["MetricData"][0]
    assert metric["MetricName"] == "RepairRunStarted"


def test_returns_202_when_durable_execution_is_already_started(mod):
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
        patch.object(mod, "_load_run_item", return_value={"state": {"S": "PARTIAL"}}),
        patch.object(
            mod,
            "_load_parent_config",
            return_value={
                "models": ["apac.amazon.nova-micro-v1:0"],
                "loops": 10,
                "full_cross": True,
                "shard_size": 500,
                "poll_interval_sec": 180,
                "editor_model": "apac.amazon.nova-micro-v1:0",
            },
        ),
        patch.object(mod, "_find_duplicate_repair", return_value=None),
        patch.object(
            mod,
            "_build_seed_rows",
            return_value=(
                [
                    {
                        "record_id": "rec-1",
                        "model_id": "apac.amazon.nova-micro-v1:0",
                        "source_invalid_key": "runs/parent/invalid/study1/model-a/invalid.jsonl",
                        "manifest_row": {"record_id": "rec-1", "model_id": "apac.amazon.nova-micro-v1:0"},
                        "invalid_output": {"recordId": "rec-1"},
                    }
                ],
                ["runs/parent/invalid/study1/model-a/invalid.jsonl"],
            ),
        ),
        patch.object(mod.s3, "put_object", return_value={}),
        patch.object(mod.projection, "build_run_item", return_value={"run_id": {"S": "child"}}),
        patch.object(mod.dynamodb, "put_item", return_value={}),
        patch.object(mod.lambda_client, "invoke", side_effect=error),
        patch.object(mod.projection, "save_execution_metadata") as save_execution,
    ):
        res = mod.handler(
            _event(
                "123e4567-e89b-42d3-a456-426614174000",
                {"phase": "study1", "scope": "invalid_only", "mode": "rerun"},
            ),
            None,
        )

    assert res["statusCode"] == 202
    save_execution.assert_called_once()
