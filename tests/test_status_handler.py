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
            "phase": {"S": "STUDY1_ENUMERATE"},
            "state": {"S": "RUNNING"},
            "retry_count": {"N": "1"},
            "progress": {
                "M": {
                    "completed_steps": {"N": "2"},
                    "total_steps": {"N": "10"},
                    "percent": {"N": "20"},
                }
            },
        }
    }
    with patch.object(mod.dynamodb, "get_item", return_value=db_item):
        res = mod.handler(
            {"pathParameters": {"run_id": "123e4567-e89b-42d3-a456-426614174000"}},
            None,
        )

    body = json.loads(res["body"])
    assert res["statusCode"] == 200
    assert body["run_id"] == "123e4567-e89b-42d3-a456-426614174000"
    assert body["state"] == "RUNNING"
    assert body["progress"]["percent"] == 20


def test_returns_retry_count_and_last_error(mod):
    db_item = {
        "Item": {
            "run_id": {"S": "123e4567-e89b-42d3-a456-426614174001"},
            "phase": {"S": "REPORT"},
            "state": {"S": "FAILED"},
            "retry_count": {"N": "2"},
            "last_error": {
                "M": {
                    "step": {"S": "STUDY1_BATCH_POLL"},
                    "reason": {"S": "[timeout] poll max attempts"},
                    "retryable": {"BOOL": True},
                }
            },
        }
    }
    with patch.object(mod.dynamodb, "get_item", return_value=db_item):
        res = mod.handler(
            {"pathParameters": {"run_id": "123e4567-e89b-42d3-a456-426614174001"}},
            None,
        )

    body = json.loads(res["body"])
    assert res["statusCode"] == 200
    assert body["retry_count"] == 2
    assert body["last_error"] == {
        "step": "STUDY1_BATCH_POLL",
        "reason": "[timeout] poll max attempts",
        "retryable": True,
        "category": None,
        "trace_id": None,
    }
