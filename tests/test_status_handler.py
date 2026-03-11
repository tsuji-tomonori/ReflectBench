import importlib
import json
import os
from unittest.mock import patch

import pytest


@pytest.fixture(scope="module")
def mod():
    os.environ.setdefault("AWS_DEFAULT_REGION", "ap-southeast-2")
    os.environ.setdefault("TABLE_NAME", "run_control_table")
    return importlib.import_module("app.status.handler")


def test_returns_404_for_unknown_run(mod):
    with patch.object(mod.dynamodb, "get_item", return_value={}):
        res = mod.handler(
            {"pathParameters": {"run_id": "123e4567-e89b-42d3-a456-426614174000"}},
            None,
        )
    assert res["statusCode"] == 404


def test_returns_status_payload_from_dynamodb(mod):
    db_item = {
        "Item": {
            "run_id": {"S": "run-1"},
            "phase": {"S": "STUDY1"},
            "step": {"S": "STUDY1_WAIT"},
            "state": {"S": "RUNNING"},
            "retry_count": {"N": "1"},
            "execution_name": {"S": "run-1"},
            "durable_execution_arn": {
                "S": (
                    "arn:aws:lambda:ap-southeast-2:123:durable-execution/"
                    "orchestrator_durable_fn/live/run-1"
                )
            },
            "progress": {
                "M": {
                    "completed_steps": {"N": "2"},
                    "total_steps": {"N": "18"},
                    "percent": {"N": "11"},
                }
            },
        }
    }
    with (
        patch.object(mod.dynamodb, "get_item", return_value=db_item),
        patch.object(mod, "_enrich_from_durable_execution") as enrich,
    ):
        res = mod.handler(
            {"pathParameters": {"run_id": "123e4567-e89b-42d3-a456-426614174000"}},
            None,
        )

    body = json.loads(res["body"])
    assert res["statusCode"] == 200
    assert body["run_id"] == "123e4567-e89b-42d3-a456-426614174000"
    assert body["phase"] == "STUDY1"
    assert body["step"] == "STUDY1_WAIT"
    assert body["state"] == "RUNNING"
    assert body["progress"]["percent"] == 11
    assert body["execution_name"] == "run-1"
    enrich.assert_called_once()


def test_returns_retry_count_and_last_error(mod):
    db_item = {
        "Item": {
            "run_id": {"S": "123e4567-e89b-42d3-a456-426614174001"},
            "phase": {"S": "REPORT"},
            "step": {"S": "FINALIZE"},
            "state": {"S": "FAILED"},
            "retry_count": {"N": "2"},
            "last_error": {
                "M": {
                    "step": {"S": "STUDY1_WAIT"},
                    "reason": {"S": "[timeout] poll max attempts"},
                    "retryable": {"BOOL": True},
                }
            },
        }
    }
    with (
        patch.object(mod.dynamodb, "get_item", return_value=db_item),
        patch.object(mod, "_enrich_from_durable_execution"),
    ):
        res = mod.handler(
            {"pathParameters": {"run_id": "123e4567-e89b-42d3-a456-426614174001"}},
            None,
        )

    body = json.loads(res["body"])
    assert res["statusCode"] == 200
    assert body["retry_count"] == 2
    assert body["last_error"] == {
        "step": "STUDY1_WAIT",
        "reason": "[timeout] poll max attempts",
        "retryable": True,
        "category": None,
        "trace_id": None,
    }


def test_returns_lineage_and_repair_metadata(mod):
    db_item = {
        "Item": {
            "run_id": {"S": "123e4567-e89b-42d3-a456-426614174010"},
            "phase": {"S": "REPORT"},
            "step": {"S": "FINALIZE"},
            "state": {"S": "SUCCEEDED"},
            "parent_run_id": {"S": "123e4567-e89b-42d3-a456-426614174000"},
            "repair_phase": {"S": "study1"},
            "repair_scope": {"S": "invalid_only"},
            "repair_mode": {"S": "rerun"},
            "rebuild_downstream": {"BOOL": True},
            "source_invalid_keys": {
                "L": [
                    {
                        "S": (
                            "runs/123e4567-e89b-42d3-a456-426614174000/"
                            "invalid/study1/model-a/invalid.jsonl"
                        )
                    }
                ]
            },
        }
    }
    with (
        patch.object(mod.dynamodb, "get_item", return_value=db_item),
        patch.object(mod, "_enrich_from_durable_execution"),
    ):
        res = mod.handler(
            {"pathParameters": {"run_id": "123e4567-e89b-42d3-a456-426614174010"}},
            None,
        )

    body = json.loads(res["body"])
    assert res["statusCode"] == 200
    assert body["lineage"] == {
        "parent_run_id": "123e4567-e89b-42d3-a456-426614174000",
    }
    assert body["repair"] == {
        "phase": "study1",
        "scope": "invalid_only",
        "mode": "rerun",
        "rebuild_downstream": True,
        "source_invalid_keys": [
            "runs/123e4567-e89b-42d3-a456-426614174000/invalid/study1/model-a/invalid.jsonl"
        ],
    }


def test_enriches_status_from_durable_execution(mod):
    item = {
        "durable_execution_arn": {
            "S": (
                "arn:aws:lambda:ap-southeast-2:123:durable-execution/"
                "orchestrator_durable_fn/live/run-2"
            )
        },
        "execution_name": {"S": "run-2"},
    }
    body = {"run_id": "123e4567-e89b-42d3-a456-426614174002", "state": "RUNNING"}

    with patch.object(
        mod.lambda_client,
        "get_durable_execution",
        create=True,
        return_value={
            "DurableExecutionArn": item["durable_execution_arn"]["S"],
            "DurableExecutionName": "run-2",
            "Status": "SUCCEEDED",
            "FunctionArn": (
                "arn:aws:lambda:ap-southeast-2:123:function:"
                "orchestrator_durable_fn:live"
            ),
            "Version": "3",
        },
    ):
        mod._enrich_from_durable_execution(item, body)

    assert body["state"] == "SUCCEEDED"
    assert body["durable_execution"]["name"] == "run-2"
    assert body["durable_execution"]["version"] == "3"


def test_terminal_dynamodb_state_is_not_overridden_by_durable_status(mod):
    item = {
        "durable_execution_arn": {
            "S": (
                "arn:aws:lambda:ap-southeast-2:123:durable-execution/"
                "orchestrator_durable_fn/live/run-3"
            )
        },
        "execution_name": {"S": "run-3"},
    }
    body = {"run_id": "123e4567-e89b-42d3-a456-426614174003", "state": "FAILED"}

    with patch.object(
        mod.lambda_client,
        "get_durable_execution",
        create=True,
        return_value={
            "DurableExecutionArn": item["durable_execution_arn"]["S"],
            "DurableExecutionName": "run-3",
            "Status": "SUCCEEDED",
            "FunctionArn": (
                "arn:aws:lambda:ap-southeast-2:123:function:"
                "orchestrator_durable_fn:live"
            ),
            "Version": "3",
        },
    ):
        mod._enrich_from_durable_execution(item, body)

    assert body["state"] == "FAILED"
    assert body["durable_execution"]["status"] == "SUCCEEDED"
