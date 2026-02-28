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
        res = mod.handler({"pathParameters": {"run_id": "missing"}}, None)
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
        res = mod.handler({"pathParameters": {"run_id": "run-1"}}, None)

    body = json.loads(res["body"])
    assert res["statusCode"] == 200
    assert body["run_id"] == "run-1"
    assert body["state"] == "RUNNING"
    assert body["progress"]["percent"] == 20
